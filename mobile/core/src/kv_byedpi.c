/* Compiled together with vendored ByeDPI sources; uses its public globals. */
#include "kv_byedpi.h"

#include <errno.h>
#include <fcntl.h>
#include <getopt.h>
#include <poll.h>
#include <pthread.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <unistd.h>

#include "params.h"
#include "proxy.h"

/* Non-static functions defined in ByeDPI's main.c / proxy.c. */
int parse_args(int argc, char **argv);
int init(void);
void clear_params(char *line, char **argv);
extern int server_fd;

static struct params kv_pristine;
static int kv_pristine_saved;

/* ByeDPI closes the listening fd itself (del_event / error paths). We keep our
 * own dup of it so shutdown() always targets the right socket and can never
 * hit a reused descriptor number. */
static pthread_mutex_t kv_ctl_lock = PTHREAD_MUTEX_INITIALIZER;
static int kv_ctl_fd = -1;

/* Wake pipe for ByeDPI's poll() loop (macOS/iOS). Created in prepare, closed
 * after run() returns; only the proxy thread reads it. */
static int kv_wake[2] = { -1, -1 };
static struct pollfd *kv_pfd;
static nfds_t kv_pfd_cap;

static void kv_close_wake(void)
{
    for (int i = 0; i < 2; i++) {
        if (kv_wake[i] >= 0) {
            close(kv_wake[i]);
            kv_wake[i] = -1;
        }
    }
    free(kv_pfd);
    kv_pfd = NULL;
    kv_pfd_cap = 0;
}

/* poll() plus the wake pipe. When woken, fails with a non-EINTR errno so
 * ByeDPI's loop_event() leaves its loop and start_event_loop() cleans up. */
int kv_byedpi_poll(struct pollfd *fds, nfds_t nfds, int timeout_ms)
{
    if (kv_wake[0] < 0) {
        return poll(fds, nfds, timeout_ms);
    }
    if (kv_pfd_cap < nfds + 1) {
        struct pollfd *p = realloc(kv_pfd, (nfds + 1) * sizeof(*p));
        if (!p) {
            errno = ENOMEM;
            return -1;
        }
        kv_pfd = p;
        kv_pfd_cap = nfds + 1;
    }
    memcpy(kv_pfd, fds, nfds * sizeof(*fds));
    kv_pfd[nfds] = (struct pollfd){ .fd = kv_wake[0], .events = POLLIN };
    int ret = poll(kv_pfd, nfds + 1, timeout_ms);
    if (ret < 0) {
        return ret;
    }
    if (kv_pfd[nfds].revents) {
        errno = ECANCELED;
        return -1;
    }
    for (nfds_t i = 0; i < nfds; i++) {
        fds[i].revents = kv_pfd[i].revents;
    }
    return ret;
}

int kv_byedpi_prepare(int argc, char **argv)
{
    if (!kv_pristine_saved) {
        kv_pristine = params; /* compile-time defaults, no heap pointers yet */
        kv_pristine_saved = 1;
    }
    params = kv_pristine;
    optind = 1;
#if defined(__APPLE__) || defined(__FreeBSD__)
    optreset = 1;
#endif
    if (parse_args(argc, argv) != 0) {
        clear_params(0, 0);
        return -1;
    }
    if (init() < 0) {
        clear_params(0, 0);
        return -1;
    }
    int fd = listen_socket(&params.laddr);
    if (fd < 0) {
        clear_params(0, 0);
        return -1;
    }
    int ctl = dup(fd);
    if (ctl < 0 || pipe(kv_wake) < 0) {
        if (ctl >= 0) close(ctl);
        close(fd);
        clear_params(0, 0);
        return -1;
    }
    for (int i = 0; i < 2; i++) {
        fcntl(kv_wake[i], F_SETFD, FD_CLOEXEC);
        fcntl(kv_wake[i], F_SETFL, fcntl(kv_wake[i], F_GETFL) | O_NONBLOCK);
    }
    pthread_mutex_lock(&kv_ctl_lock);
    kv_ctl_fd = ctl;
    pthread_mutex_unlock(&kv_ctl_lock);
    server_fd = fd;
    return fd;
}

int kv_byedpi_run(int listen_fd)
{
    /* Closes listen_fd and every connection socket before returning. */
    int res = start_event_loop(listen_fd);
    pthread_mutex_lock(&kv_ctl_lock);
    if (kv_ctl_fd >= 0) {
        close(kv_ctl_fd);
        kv_ctl_fd = -1;
    }
    kv_close_wake();
    pthread_mutex_unlock(&kv_ctl_lock);
    return res;
}

void kv_byedpi_shutdown(void)
{
    pthread_mutex_lock(&kv_ctl_lock);
    if (kv_ctl_fd >= 0) {
        /* Linux (epoll loop): accept() then fails, on_accept sets
         * pool->brk and the loop exits. macOS/iOS: shutdown() on a listening
         * socket does nothing, the wake pipe ends the poll() loop instead. */
        shutdown(kv_ctl_fd, SHUT_RDWR);
        if (kv_wake[1] >= 0 && write(kv_wake[1], "x", 1) < 0) {
            /* pipe full: a wake-up is already pending */
        }
    }
    pthread_mutex_unlock(&kv_ctl_lock);
}

void kv_byedpi_cleanup(void)
{
    clear_params(0, 0);
}

void kv_byedpi_abort(int listen_fd)
{
    if (listen_fd >= 0) {
        close(listen_fd);
    }
    pthread_mutex_lock(&kv_ctl_lock);
    if (kv_ctl_fd >= 0) {
        close(kv_ctl_fd);
        kv_ctl_fd = -1;
    }
    kv_close_wake();
    pthread_mutex_unlock(&kv_ctl_lock);
    clear_params(0, 0);
}
