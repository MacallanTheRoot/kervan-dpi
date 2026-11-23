/* Compiled together with vendored ByeDPI sources; uses its public globals. */
#include "kv_byedpi.h"

#include <getopt.h>
#include <pthread.h>
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
    if (ctl < 0) {
        close(fd);
        clear_params(0, 0);
        return -1;
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
    pthread_mutex_unlock(&kv_ctl_lock);
    return res;
}

void kv_byedpi_shutdown(void)
{
    pthread_mutex_lock(&kv_ctl_lock);
    if (kv_ctl_fd >= 0) {
        /* accept() then fails, on_accept sets pool->brk and the loop exits. */
        shutdown(kv_ctl_fd, SHUT_RDWR);
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
    pthread_mutex_unlock(&kv_ctl_lock);
    clear_params(0, 0);
}
