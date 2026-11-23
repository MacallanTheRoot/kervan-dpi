/*
 * Kervan DPI engine orchestrator.
 *
 * Threads while running:
 *   protect  - receives outbound socket fds from ByeDPI (SCM_RIGHTS over a
 *              private unix socket) and calls the platform protect callback.
 *              No reply == ByeDPI drops the connection (fail closed).
 *   proxy    - ByeDPI event loop on 127.0.0.1:<socks_port>.
 *   tunnel   - hev-socks5-tunnel reading the platform TUN fd (optional).
 *   packet   - packet mode only: reads tunnel output from the socketpair and
 *              hands each IP packet to packet_out_cb.
 * If proxy or tunnel exits while not stopping, state becomes FAILED and the
 * platform adapter must tear the tunnel down.
 */
#include "kervan_engine.h"

#include <arpa/inet.h>
#include <errno.h>
#include <fcntl.h>
#include <poll.h>
#include <pthread.h>
#include <signal.h>
#include <stdarg.h>
#include <stdatomic.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <sys/un.h>
#include <time.h>
#include <unistd.h>

#include "kv_byedpi.h"

#ifdef KV_WITH_TUNNEL
#include "hev-main.h"
#endif

#define KV_MAX_ARGS 96
#define KV_TUNNEL_GRACE_MS 300
#define KV_PACKET_SOCKBUF (256 * 1024) /* per direction; NE memory is tight */

#ifndef MSG_NOSIGNAL
#define MSG_NOSIGNAL 0 /* Darwin: SIGPIPE is ignored in kv_engine_start */
#endif

/* hev-socks5-tunnel frames TUN I/O the way the host kernel does: BSD/Darwin
 * utun prefixes every packet with a 4-byte address family, Linux TUN (IFF_NO_PI)
 * does not. Keep in sync with HEV_TUNNEL_GENERIC_HEAD in hev-tunnel-*.h. */
#if defined(__APPLE__) || defined(__FreeBSD__) || defined(__NetBSD__)
#define KV_TUN_HEAD 4
#else
#define KV_TUN_HEAD 0
#endif

struct kv_engine {
    pthread_mutex_t lock;          /* serialises start/stop */
    atomic_int state;
    atomic_int stopping;

    kv_engine_config_t cfg;        /* string fields point at copies below */
    char *runtime_dir;
    char *desync_args;

    int protect_listen_fd;
    int wake_pipe[2];
    char protect_path[sizeof(((struct sockaddr_un *)0)->sun_path)];
    pthread_t protect_thr;
    int protect_started;

    int proxy_fd;
    pthread_t proxy_thr;
    int proxy_started;

    char *tunnel_cfg;
    pthread_t tunnel_thr;
    int tunnel_started;
    atomic_int tunnel_exited;
    int tun_fd;                    /* fd hev reads: platform fd or pair end */

    /* packet mode */
    pthread_rwlock_t pkt_lock;     /* guards pkt_fd against close during packet_in */
    int pkt_fd;                    /* our end of the socketpair */
    int pkt_peer_fd;               /* hev's end */
    int pkt_wake[2];
    pthread_t pkt_thr;
    int pkt_started;
    uint8_t *pkt_buf;
};

static atomic_int g_instance_exists;

static void kv_log(struct kv_engine *e, kv_log_level_t lvl, const char *fmt, ...)
{
    if (!e->cfg.log_cb) {
        return;
    }
    char buf[512];
    va_list ap;
    va_start(ap, fmt);
    vsnprintf(buf, sizeof(buf), fmt, ap);
    va_end(ap);
    e->cfg.log_cb(e->cfg.user, lvl, buf);
}

static void set_state(struct kv_engine *e, kv_state_t s, kv_status_t reason)
{
    atomic_store(&e->state, s);
    if (e->cfg.state_cb) {
        e->cfg.state_cb(e->cfg.user, s, reason);
    }
}

/* Called from component threads when they exit on their own. */
static void component_died(struct kv_engine *e, const char *what, kv_status_t reason)
{
    if (atomic_load(&e->stopping)) {
        return;
    }
    int expected = KV_STATE_RUNNING;
    if (atomic_compare_exchange_strong(&e->state, &expected, KV_STATE_FAILED) ||
        (expected = KV_STATE_STARTING,
         atomic_compare_exchange_strong(&e->state, &expected, KV_STATE_FAILED))) {
        kv_log(e, KV_LOG_ERROR, "%s exited unexpectedly", what);
        if (e->cfg.state_cb) {
            e->cfg.state_cb(e->cfg.user, KV_STATE_FAILED, reason);
        }
    }
}

uint32_t kv_engine_abi_version(void) { return KV_ENGINE_ABI_VERSION; }

int kv_engine_supports_protect(void)
{
#ifdef __linux__
    return 1; /* ByeDPI's -P (protect-path) exists only on Linux/Android */
#else
    return 0;
#endif
}

const char *kv_status_string(kv_status_t s)
{
    switch (s) {
    case KV_OK: return "ok";
    case KV_ERR_INVALID_ARG: return "invalid argument";
    case KV_ERR_BUSY: return "engine busy";
    case KV_ERR_NO_MEMORY: return "out of memory";
    case KV_ERR_PROXY_START: return "desync proxy failed to start";
    case KV_ERR_PROTECT_SETUP: return "socket protection bridge failed";
    case KV_ERR_TUNNEL_START: return "tunnel failed to start";
    case KV_ERR_TIMEOUT: return "timeout";
    case KV_ERR_DROPPED: return "packet dropped";
    }
    return "unknown";
}

kv_status_t kv_engine_create(kv_engine_t **out)
{
    if (!out) {
        return KV_ERR_INVALID_ARG;
    }
    int expected = 0;
    if (!atomic_compare_exchange_strong(&g_instance_exists, &expected, 1)) {
        return KV_ERR_BUSY;
    }
    struct kv_engine *e = calloc(1, sizeof(*e));
    if (!e) {
        atomic_store(&g_instance_exists, 0);
        return KV_ERR_NO_MEMORY;
    }
    pthread_mutex_init(&e->lock, NULL);
    pthread_rwlock_init(&e->pkt_lock, NULL);
    atomic_init(&e->state, KV_STATE_STOPPED);
    e->tun_fd = -1;
    e->pkt_fd = e->pkt_peer_fd = -1;
    e->pkt_wake[0] = e->pkt_wake[1] = -1;
    e->protect_listen_fd = -1;
    e->wake_pipe[0] = e->wake_pipe[1] = -1;
    e->proxy_fd = -1;
    *out = e;
    return KV_OK;
}

kv_state_t kv_engine_state(const kv_engine_t *e)
{
    return e ? (kv_state_t)atomic_load(&((kv_engine_t *)e)->state) : KV_STATE_STOPPED;
}

/* ---------- protect bridge ---------- */

static void serve_protect_request(struct kv_engine *e, int conn)
{
    struct timeval tv = { .tv_sec = 1 };
    setsockopt(conn, SOL_SOCKET, SO_RCVTIMEO, &tv, sizeof(tv));
    setsockopt(conn, SOL_SOCKET, SO_SNDTIMEO, &tv, sizeof(tv));

    char data[1];
    char cbuf[CMSG_SPACE(sizeof(int))];
    struct iovec io = { .iov_base = data, .iov_len = sizeof(data) };
    struct msghdr msg = { .msg_iov = &io, .msg_iovlen = 1,
                          .msg_control = cbuf, .msg_controllen = sizeof(cbuf) };
    ssize_t n = recvmsg(conn, &msg, 0);
    if (n <= 0) {
        return;
    }
    int fd = -1;
    for (struct cmsghdr *c = CMSG_FIRSTHDR(&msg); c; c = CMSG_NXTHDR(&msg, c)) {
        if (c->cmsg_level == SOL_SOCKET && c->cmsg_type == SCM_RIGHTS &&
            c->cmsg_len == CMSG_LEN(sizeof(int))) {
            memcpy(&fd, CMSG_DATA(c), sizeof(int));
        }
    }
    if (fd < 0) {
        kv_log(e, KV_LOG_WARN, "protect request without descriptor");
        return;
    }
    int ok = e->cfg.protect_cb(e->cfg.user, fd) == 0;
    close(fd); /* our duplicate; the socket itself stays open in ByeDPI */
    if (ok) {
        send(conn, "1", 1, MSG_NOSIGNAL);
    } else {
        kv_log(e, KV_LOG_WARN, "protect failed; dropping connection");
    }
}

static void *protect_main(void *arg)
{
    struct kv_engine *e = arg;
    struct pollfd p[2] = {
        { .fd = e->protect_listen_fd, .events = POLLIN },
        { .fd = e->wake_pipe[0], .events = POLLIN },
    };
    for (;;) {
        int r = poll(p, 2, -1);
        if (r < 0) {
            if (errno == EINTR) continue;
            break;
        }
        if (p[1].revents) {
            break;
        }
        if (p[0].revents & POLLIN) {
            int conn = accept(e->protect_listen_fd, NULL, NULL);
            if (conn >= 0) {
                serve_protect_request(e, conn);
                close(conn);
            }
        } else if (p[0].revents) {
            break;
        }
    }
    return NULL;
}

static kv_status_t start_protect(struct kv_engine *e)
{
    int n = snprintf(e->protect_path, sizeof(e->protect_path), "%s/kvp-%d.sock",
                     e->runtime_dir, (int)getpid());
    if (n <= 0 || (size_t)n >= sizeof(e->protect_path)) {
        kv_log(e, KV_LOG_ERROR, "runtime_dir too long for a unix socket path");
        return KV_ERR_INVALID_ARG;
    }
    if (pipe(e->wake_pipe) < 0) {
        return KV_ERR_PROTECT_SETUP;
    }
    fcntl(e->wake_pipe[0], F_SETFD, FD_CLOEXEC);
    fcntl(e->wake_pipe[1], F_SETFD, FD_CLOEXEC);
    int fd = socket(AF_UNIX, SOCK_STREAM, 0);
    if (fd < 0) {
        return KV_ERR_PROTECT_SETUP;
    }
    fcntl(fd, F_SETFD, FD_CLOEXEC);
    struct sockaddr_un sa = { .sun_family = AF_UNIX };
    memcpy(sa.sun_path, e->protect_path, strlen(e->protect_path) + 1);
    unlink(e->protect_path);
    if (bind(fd, (struct sockaddr *)&sa, sizeof(sa)) < 0 || listen(fd, 64) < 0) {
        kv_log(e, KV_LOG_ERROR, "protect socket bind/listen failed: %s", strerror(errno));
        close(fd);
        unlink(e->protect_path);
        return KV_ERR_PROTECT_SETUP;
    }
    chmod(e->protect_path, 0600);
    e->protect_listen_fd = fd;
    if (pthread_create(&e->protect_thr, NULL, protect_main, e) != 0) {
        return KV_ERR_PROTECT_SETUP;
    }
    e->protect_started = 1;
    return KV_OK;
}

static void stop_protect(struct kv_engine *e)
{
    if (e->protect_started) {
        if (write(e->wake_pipe[1], "x", 1) < 0) { /* poll also sees close below */ }
        pthread_join(e->protect_thr, NULL);
        e->protect_started = 0;
    }
    if (e->protect_listen_fd >= 0) {
        close(e->protect_listen_fd);
        e->protect_listen_fd = -1;
        unlink(e->protect_path);
    }
    for (int i = 0; i < 2; i++) {
        if (e->wake_pipe[i] >= 0) {
            close(e->wake_pipe[i]);
            e->wake_pipe[i] = -1;
        }
    }
}

/* ---------- proxy ---------- */

static void *proxy_main(void *arg)
{
    struct kv_engine *e = arg;
    int fd = e->proxy_fd;
    kv_byedpi_run(fd);
    component_died(e, "desync proxy", KV_ERR_PROXY_START);
    return NULL;
}

static kv_status_t start_proxy(struct kv_engine *e)
{
    char port[8];
    snprintf(port, sizeof(port), "%u", (unsigned)e->cfg.socks_port);
    char *argv[KV_MAX_ARGS + 1];
    int argc = 0;
    argv[argc++] = "kervan";
    argv[argc++] = "-i";
    argv[argc++] = "127.0.0.1";
    argv[argc++] = "-p";
    argv[argc++] = port;
    if (e->protect_started) {
        argv[argc++] = "-P";
        argv[argc++] = e->protect_path;
    }
    if (!e->cfg.enable_udp) {
        argv[argc++] = "-U";
    }
    for (char *tok = strtok(e->desync_args, " \t\n"); tok; tok = strtok(NULL, " \t\n")) {
        if (argc >= KV_MAX_ARGS) {
            kv_log(e, KV_LOG_ERROR, "too many desync arguments");
            return KV_ERR_INVALID_ARG;
        }
        argv[argc++] = tok;
    }
    argv[argc] = NULL;

    int fd = kv_byedpi_prepare(argc, argv);
    if (fd < 0) {
        kv_log(e, KV_LOG_ERROR, "desync proxy rejected its arguments or could not listen on 127.0.0.1:%s", port);
        return KV_ERR_PROXY_START;
    }
    e->proxy_fd = fd;
    if (pthread_create(&e->proxy_thr, NULL, proxy_main, e) != 0) {
        kv_byedpi_abort(fd);
        e->proxy_fd = -1;
        return KV_ERR_PROXY_START;
    }
    e->proxy_started = 1;
    return KV_OK;
}

static void stop_proxy(struct kv_engine *e)
{
    if (e->proxy_started) {
        kv_byedpi_shutdown();
        pthread_join(e->proxy_thr, NULL);
        kv_byedpi_cleanup();
        e->proxy_started = 0;
        e->proxy_fd = -1;
    }
}

/* ---------- packet bridge (packet mode) ---------- */

static void close_fd(int *fd)
{
    if (*fd >= 0) {
        close(*fd);
        *fd = -1;
    }
}

static void *packet_main(void *arg)
{
    struct kv_engine *e = arg;
    size_t cap = KV_TUN_HEAD + e->cfg.tun_mtu;
    struct pollfd p[2] = {
        { .fd = e->pkt_fd, .events = POLLIN },
        { .fd = e->pkt_wake[0], .events = POLLIN },
    };
    for (;;) {
        int r = poll(p, 2, -1);
        if (r < 0) {
            if (errno == EINTR) continue;
            break;
        }
        if (p[1].revents) {
            return NULL; /* stop requested */
        }
        if (!(p[0].revents & POLLIN)) {
            break;
        }
        ssize_t n = recv(e->pkt_fd, e->pkt_buf, cap, MSG_DONTWAIT);
        if (n < 0) {
            if (errno == EAGAIN || errno == EWOULDBLOCK || errno == EINTR) continue;
            break;
        }
        if (n <= KV_TUN_HEAD) {
            continue;
        }
        const uint8_t *ip = e->pkt_buf + KV_TUN_HEAD;
        int family = ip[0] >> 4;
        if (family == 4 || family == 6) {
            e->cfg.packet_out_cb(e->cfg.user, ip, (size_t)n - KV_TUN_HEAD, family);
        }
    }
    component_died(e, "packet bridge", KV_ERR_TUNNEL_START);
    return NULL;
}

static kv_status_t start_packet_bridge(struct kv_engine *e)
{
    int sv[2];
    if (socketpair(AF_UNIX, SOCK_DGRAM, 0, sv) < 0) {
        kv_log(e, KV_LOG_ERROR, "packet socketpair failed: %s", strerror(errno));
        return KV_ERR_TUNNEL_START;
    }
    /* Darwin's default AF_UNIX datagram limit (2 KiB) is below some MTUs. */
    int sz = KV_PACKET_SOCKBUF;
    for (int i = 0; i < 2; i++) {
        fcntl(sv[i], F_SETFD, FD_CLOEXEC);
        setsockopt(sv[i], SOL_SOCKET, SO_SNDBUF, &sz, sizeof(sz));
        setsockopt(sv[i], SOL_SOCKET, SO_RCVBUF, &sz, sizeof(sz));
#ifdef SO_NOSIGPIPE
        int one = 1;
        setsockopt(sv[i], SOL_SOCKET, SO_NOSIGPIPE, &one, sizeof(one));
#endif
    }
    if (!(e->pkt_buf = malloc(KV_TUN_HEAD + e->cfg.tun_mtu)) || pipe(e->pkt_wake) < 0) {
        close(sv[0]);
        close(sv[1]);
        return KV_ERR_NO_MEMORY;
    }
    fcntl(e->pkt_wake[0], F_SETFD, FD_CLOEXEC);
    fcntl(e->pkt_wake[1], F_SETFD, FD_CLOEXEC);
    fcntl(sv[0], F_SETFL, fcntl(sv[0], F_GETFL) | O_NONBLOCK);
    pthread_rwlock_wrlock(&e->pkt_lock);
    e->pkt_fd = sv[0];
    pthread_rwlock_unlock(&e->pkt_lock);
    e->pkt_peer_fd = sv[1];
    e->tun_fd = sv[1];
    if (pthread_create(&e->pkt_thr, NULL, packet_main, e) != 0) {
        return KV_ERR_TUNNEL_START;
    }
    e->pkt_started = 1;
    return KV_OK;
}

/* Called after the tunnel has stopped, so hev no longer uses pkt_peer_fd. */
static void stop_packet_bridge(struct kv_engine *e)
{
    if (e->pkt_started) {
        if (write(e->pkt_wake[1], "x", 1) < 0) { /* join below still returns */ }
        pthread_join(e->pkt_thr, NULL);
        e->pkt_started = 0;
    }
    pthread_rwlock_wrlock(&e->pkt_lock); /* waits for in-flight packet_in */
    close_fd(&e->pkt_fd);
    pthread_rwlock_unlock(&e->pkt_lock);
    close_fd(&e->pkt_peer_fd);
    close_fd(&e->pkt_wake[0]);
    close_fd(&e->pkt_wake[1]);
    free(e->pkt_buf);
    e->pkt_buf = NULL;
}

kv_status_t kv_engine_packet_in(kv_engine_t *e, const void *packet, size_t len)
{
    if (!e || !packet || len == 0) {
        return KV_ERR_INVALID_ARG;
    }
    int family = ((const uint8_t *)packet)[0] >> 4;
    if (family != 4 && family != 6) {
        return KV_ERR_INVALID_ARG;
    }
    kv_status_t st;
    pthread_rwlock_rdlock(&e->pkt_lock);
    if (e->pkt_fd < 0 || atomic_load(&e->state) != KV_STATE_RUNNING) {
        st = KV_ERR_BUSY;
    } else if (len > e->cfg.tun_mtu) {
        st = KV_ERR_INVALID_ARG;
    } else {
        uint32_t head = htonl(family == 4 ? AF_INET : AF_INET6);
        struct iovec iov[2] = {
            { .iov_base = &head, .iov_len = KV_TUN_HEAD },
            { .iov_base = (void *)packet, .iov_len = len },
        };
        struct msghdr msg = { .msg_iov = KV_TUN_HEAD ? iov : iov + 1,
                              .msg_iovlen = KV_TUN_HEAD ? 2 : 1 };
        ssize_t n = sendmsg(e->pkt_fd, &msg, MSG_DONTWAIT | MSG_NOSIGNAL);
        st = n == (ssize_t)(KV_TUN_HEAD + len) ? KV_OK : KV_ERR_DROPPED;
    }
    pthread_rwlock_unlock(&e->pkt_lock);
    return st;
}

/* ---------- tunnel ---------- */

#ifdef KV_WITH_TUNNEL
static void *tunnel_main(void *arg)
{
    struct kv_engine *e = arg;
    hev_socks5_tunnel_main_from_str((const unsigned char *)e->tunnel_cfg,
                                    (unsigned int)strlen(e->tunnel_cfg), e->tun_fd);
    atomic_store(&e->tunnel_exited, 1);
    component_died(e, "tunnel", KV_ERR_TUNNEL_START);
    return NULL;
}
#endif

static kv_status_t start_tunnel(struct kv_engine *e)
{
    if (e->tun_fd < 0) {
        return KV_OK; /* proxy-only mode */
    }
#ifndef KV_WITH_TUNNEL
    kv_log(e, KV_LOG_ERROR, "built without tunnel support");
    return KV_ERR_TUNNEL_START;
#else
    char buf[512];
    int n = snprintf(buf, sizeof(buf),
                     "tunnel:\n  mtu: %u\n"
                     "socks5:\n  port: %u\n  address: 127.0.0.1\n  udp: 'udp'\n"
                     "misc:\n  log-level: warn\n",
                     (unsigned)e->cfg.tun_mtu, (unsigned)e->cfg.socks_port);
    if (n <= 0 || (size_t)n >= sizeof(buf) || !(e->tunnel_cfg = strdup(buf))) {
        return KV_ERR_NO_MEMORY;
    }
    atomic_store(&e->tunnel_exited, 0);
    if (pthread_create(&e->tunnel_thr, NULL, tunnel_main, e) != 0) {
        return KV_ERR_TUNNEL_START;
    }
    e->tunnel_started = 1;
    /* hev returns quickly on bad config or fd; a live loop keeps running. */
    for (int waited = 0; waited < KV_TUNNEL_GRACE_MS; waited += 20) {
        if (atomic_load(&e->tunnel_exited)) {
            kv_log(e, KV_LOG_ERROR, "tunnel exited during startup");
            return KV_ERR_TUNNEL_START;
        }
        struct timespec ts = { 0, 20 * 1000 * 1000 };
        nanosleep(&ts, NULL);
    }
    return KV_OK;
#endif
}

static void stop_tunnel(struct kv_engine *e)
{
#ifdef KV_WITH_TUNNEL
    if (e->tunnel_started) {
        hev_socks5_tunnel_quit();
        pthread_join(e->tunnel_thr, NULL);
        e->tunnel_started = 0;
    }
#endif
    free(e->tunnel_cfg);
    e->tunnel_cfg = NULL;
}

/* ---------- lifecycle ---------- */

static void teardown_locked(struct kv_engine *e)
{
    atomic_store(&e->stopping, 1);
    /* Tunnel first so no new SOCKS sessions arrive, then proxy, then protect
     * (proxy may still be asking for protection until it exits). */
    stop_tunnel(e);
    stop_packet_bridge(e);
    e->tun_fd = -1;
    stop_proxy(e);
    stop_protect(e);
    free(e->runtime_dir);
    free(e->desync_args);
    e->runtime_dir = e->desync_args = NULL;
    atomic_store(&e->stopping, 0);
}

kv_status_t kv_engine_start(kv_engine_t *e, const kv_engine_config_t *c)
{
    if (!e || !c || c->struct_size < sizeof(kv_engine_config_t) || c->socks_port == 0 ||
        (c->require_protect && !c->protect_cb) || (c->protect_cb && !c->runtime_dir) ||
        ((c->protect_cb || c->require_protect) && !kv_engine_supports_protect()) ||
        (c->tun_fd < -1 && c->tun_fd != KV_TUN_PACKET_MODE) ||
        (c->tun_fd == KV_TUN_PACKET_MODE && !c->packet_out_cb) ||
        (c->tun_fd != -1 && (c->tun_mtu < 576 || c->tun_mtu > 65535))) {
        return KV_ERR_INVALID_ARG;
    }
    pthread_mutex_lock(&e->lock);
    if (atomic_load(&e->state) != KV_STATE_STOPPED) {
        pthread_mutex_unlock(&e->lock);
        return KV_ERR_BUSY;
    }
    e->cfg = *c;
    e->runtime_dir = c->runtime_dir ? strdup(c->runtime_dir) : NULL;
    e->desync_args = strdup(c->desync_args ? c->desync_args : "");
    e->cfg.runtime_dir = e->runtime_dir;
    e->cfg.desync_args = NULL;
    if (!e->desync_args || (c->runtime_dir && !e->runtime_dir)) {
        teardown_locked(e);
        pthread_mutex_unlock(&e->lock);
        return KV_ERR_NO_MEMORY;
    }
#ifdef SIGPIPE
    signal(SIGPIPE, SIG_IGN); /* writes to reset peers must not kill the app */
#endif
    set_state(e, KV_STATE_STARTING, KV_OK);

    kv_status_t st = KV_OK;
    if (c->protect_cb) {
        st = start_protect(e);
    }
    if (st == KV_OK) {
        st = start_proxy(e);
    }
    e->tun_fd = c->tun_fd;
    if (st == KV_OK && c->tun_fd == KV_TUN_PACKET_MODE) {
        st = start_packet_bridge(e);
    }
    if (st == KV_OK) {
        st = start_tunnel(e);
    }
    if (st != KV_OK || atomic_load(&e->state) == KV_STATE_FAILED) {
        if (st == KV_OK) {
            st = KV_ERR_TUNNEL_START;
        }
        teardown_locked(e);
        set_state(e, KV_STATE_STOPPED, st);
        pthread_mutex_unlock(&e->lock);
        return st;
    }
    int expected = KV_STATE_STARTING;
    if (!atomic_compare_exchange_strong(&e->state, &expected, KV_STATE_RUNNING)) {
        teardown_locked(e);
        set_state(e, KV_STATE_STOPPED, KV_ERR_TUNNEL_START);
        pthread_mutex_unlock(&e->lock);
        return KV_ERR_TUNNEL_START;
    }
    if (e->cfg.state_cb) {
        e->cfg.state_cb(e->cfg.user, KV_STATE_RUNNING, KV_OK);
    }
    kv_log(e, KV_LOG_INFO, "engine running (socks 127.0.0.1:%u, tunnel %s, protect %s)",
           (unsigned)c->socks_port,
           c->tun_fd == KV_TUN_PACKET_MODE ? "packet" : c->tun_fd >= 0 ? "fd" : "off",
           e->protect_started ? "on" : "off");
    pthread_mutex_unlock(&e->lock);
    return KV_OK;
}

kv_status_t kv_engine_stop(kv_engine_t *e)
{
    if (!e) {
        return KV_ERR_INVALID_ARG;
    }
    pthread_mutex_lock(&e->lock);
    if (atomic_load(&e->state) == KV_STATE_STOPPED) {
        pthread_mutex_unlock(&e->lock);
        return KV_OK;
    }
    set_state(e, KV_STATE_STOPPING, KV_OK);
    teardown_locked(e);
    set_state(e, KV_STATE_STOPPED, KV_OK);
    pthread_mutex_unlock(&e->lock);
    return KV_OK;
}

void kv_engine_destroy(kv_engine_t *e)
{
    if (!e) {
        return;
    }
    kv_engine_stop(e);
    pthread_mutex_destroy(&e->lock);
    pthread_rwlock_destroy(&e->pkt_lock);
    free(e);
    atomic_store(&g_instance_exists, 0);
}
