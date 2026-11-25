/* Host tests for the Kervan engine (Linux/macOS). No root, no real TUN. */
#include "kervan_engine.h"

#include <arpa/inet.h>
#include <dirent.h>
#include <netinet/in.h>
#include <pthread.h>
#include <stdatomic.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/time.h>
#include <unistd.h>

static int failures;
#define CHECK(cond) do { if (!(cond)) { fprintf(stderr, "FAIL %s:%d: %s\n", __FILE__, __LINE__, #cond); failures++; } } while (0)

static atomic_int protect_calls;
static atomic_int protect_result; /* value returned by the fake protect */
static atomic_int echo_bytes;

static int fake_protect(void *user, int fd) { (void)user; (void)fd; atomic_fetch_add(&protect_calls, 1); return atomic_load(&protect_result); }
static void quiet_log(void *u, kv_log_level_t l, const char *m) { (void)u; if (l >= KV_LOG_WARN) fprintf(stderr, "  [engine] %s\n", m); }

static int count_fds(void)
{
    int n = 0;
    DIR *d = opendir("/proc/self/fd");
    if (!d) d = opendir("/dev/fd");
    if (!d) return -1;
    while (readdir(d)) n++;
    closedir(d);
    return n;
}

/* ---- tiny TCP echo server ---- */
static int echo_listen_fd;
static uint16_t echo_port;
static void *echo_main(void *arg)
{
    (void)arg;
    for (;;) {
        int c = accept(echo_listen_fd, NULL, NULL);
        if (c < 0) return NULL;
        char buf[256];
        ssize_t n;
        while ((n = recv(c, buf, sizeof(buf), 0)) > 0) {
            atomic_fetch_add(&echo_bytes, (int)n);
            send(c, buf, (size_t)n, 0);
        }
        close(c);
    }
}
static void start_echo(void)
{
    echo_listen_fd = socket(AF_INET, SOCK_STREAM, 0);
    struct sockaddr_in a = { .sin_family = AF_INET, .sin_addr.s_addr = htonl(INADDR_LOOPBACK) };
    bind(echo_listen_fd, (struct sockaddr *)&a, sizeof(a));
    listen(echo_listen_fd, 8);
    socklen_t l = sizeof(a);
    getsockname(echo_listen_fd, (struct sockaddr *)&a, &l);
    echo_port = ntohs(a.sin_port);
    pthread_t t;
    pthread_create(&t, NULL, echo_main, NULL);
    pthread_detach(t);
}

static uint16_t free_port(void)
{
    int s = socket(AF_INET, SOCK_STREAM, 0);
    struct sockaddr_in a = { .sin_family = AF_INET, .sin_addr.s_addr = htonl(INADDR_LOOPBACK) };
    bind(s, (struct sockaddr *)&a, sizeof(a));
    socklen_t l = sizeof(a);
    getsockname(s, (struct sockaddr *)&a, &l);
    close(s);
    return ntohs(a.sin_port);
}

/* SOCKS5 CONNECT to 127.0.0.1:echo_port through the engine, send "ping".
 * Returns 1 if "ping" echoed back, 0 if the proxy refused/closed. */
static int socks_roundtrip(uint16_t socks_port)
{
    int s = socket(AF_INET, SOCK_STREAM, 0);
    struct timeval tv = { .tv_sec = 3 };
    setsockopt(s, SOL_SOCKET, SO_RCVTIMEO, &tv, sizeof(tv));
    struct sockaddr_in a = { .sin_family = AF_INET, .sin_port = htons(socks_port), .sin_addr.s_addr = htonl(INADDR_LOOPBACK) };
    int ok = 0;
    if (connect(s, (struct sockaddr *)&a, sizeof(a)) == 0) {
        unsigned char hello[] = { 5, 1, 0 }, rep[16];
        send(s, hello, sizeof(hello), 0);
        if (recv(s, rep, 2, MSG_WAITALL) == 2 && rep[0] == 5 && rep[1] == 0) {
            unsigned char req[10] = { 5, 1, 0, 1, 127, 0, 0, 1, (unsigned char)(echo_port >> 8), (unsigned char)echo_port };
            send(s, req, sizeof(req), 0);
            if (recv(s, rep, 10, MSG_WAITALL) == 10 && rep[1] == 0) {
                send(s, "ping", 4, 0);
                char back[4];
                ok = recv(s, back, 4, MSG_WAITALL) == 4 && memcmp(back, "ping", 4) == 0;
            }
        }
    }
    close(s);
    return ok;
}

static kv_engine_config_t base_config(uint16_t port, const char *dir)
{
    kv_engine_config_t c = { 0 };
    c.struct_size = sizeof(c);
    c.tun_fd = -1;
    c.tun_mtu = 1500;
    c.socks_port = port;
    c.runtime_dir = dir;
    c.desync_args = "";
    c.enable_udp = 1;
    /* Protect exists only on Linux/Android; elsewhere run unprotected (iOS). */
    c.require_protect = kv_engine_supports_protect();
    c.protect_cb = kv_engine_supports_protect() ? fake_protect : NULL;
    c.log_cb = quiet_log;
    return c;
}

int main(void)
{
    char dir[] = "/tmp/kvtestXXXXXX";
    if (!mkdtemp(dir)) { perror("mkdtemp"); return 2; }
    start_echo();
    CHECK(kv_engine_abi_version() == KV_ENGINE_ABI_VERSION);

    kv_engine_t *e = NULL;
    CHECK(kv_engine_create(&e) == KV_OK);
    kv_engine_t *e2 = NULL;
    CHECK(kv_engine_create(&e2) == KV_ERR_BUSY); /* single instance */

    /* invalid: protect required but missing */
    kv_engine_config_t bad = base_config(free_port(), dir);
    bad.require_protect = 1;
    bad.protect_cb = NULL;
    CHECK(kv_engine_start(e, &bad) == KV_ERR_INVALID_ARG);
    CHECK(kv_engine_state(e) == KV_STATE_STOPPED);
    if (!kv_engine_supports_protect()) {
        /* no protect support: refuse instead of starting half-configured */
        bad = base_config(free_port(), dir);
        bad.protect_cb = fake_protect;
        CHECK(kv_engine_start(e, &bad) == KV_ERR_INVALID_ARG);
        CHECK(kv_engine_state(e) == KV_STATE_STOPPED);
    }

    /* invalid desync argument -> proxy start error, never RUNNING */
    bad = base_config(free_port(), dir);
    bad.desync_args = "--definitely-not-an-option";
    CHECK(kv_engine_start(e, &bad) == KV_ERR_PROXY_START);
    CHECK(kv_engine_state(e) == KV_STATE_STOPPED);

    int fds_before = count_fds();

    /* 1. proxy path works and every outbound socket was protected */
    atomic_store(&protect_result, 0);
    atomic_store(&protect_calls, 0);
    uint16_t port = free_port();
    kv_engine_config_t c = base_config(port, dir);
    c.desync_args = "-d1 -s1+s -r1+s"; /* Android PoC default strategy */
    CHECK(kv_engine_start(e, &c) == KV_OK);
    CHECK(kv_engine_state(e) == KV_STATE_RUNNING);
    CHECK(kv_engine_start(e, &c) == KV_ERR_BUSY);
    CHECK(socks_roundtrip(port) == 1);
    if (kv_engine_supports_protect()) {
        CHECK(atomic_load(&protect_calls) >= 1);

        /* 2. fail closed: protect refuses -> connection dropped, no data reaches target */
        atomic_store(&protect_result, -1);
        int calls_before = atomic_load(&protect_calls);
        int bytes_before = atomic_load(&echo_bytes);
        CHECK(socks_roundtrip(port) == 0);
        CHECK(atomic_load(&protect_calls) > calls_before);
        CHECK(atomic_load(&echo_bytes) == bytes_before);
    }

    /* 3. stop is idempotent and releases the port */
    CHECK(kv_engine_stop(e) == KV_OK);
    CHECK(kv_engine_stop(e) == KV_OK);
    CHECK(kv_engine_state(e) == KV_STATE_STOPPED);
    CHECK(socks_roundtrip(port) == 0);

    /* 4. restart (ByeDPI global params must reset) and repeated cycles do not leak fds */
    atomic_store(&protect_result, 0);
    for (int i = 0; i < 5; i++) {
        c = base_config(free_port(), dir);
        CHECK(kv_engine_start(e, &c) == KV_OK);
        CHECK(socks_roundtrip(c.socks_port) == 1);
        CHECK(kv_engine_stop(e) == KV_OK);
    }
    CHECK(count_fds() == fds_before);

    /* 5. tunnel lifecycle with a packet socketpair standing in for TUN */
    int sp[2];
    CHECK(socketpair(AF_UNIX, SOCK_DGRAM, 0, sp) == 0);
    c = base_config(free_port(), dir);
    c.tun_fd = sp[0];
    kv_status_t st = kv_engine_start(e, &c);
    CHECK(st == KV_OK);
    CHECK(kv_engine_state(e) == KV_STATE_RUNNING);
    CHECK(kv_engine_stop(e) == KV_OK);
    CHECK(kv_engine_state(e) == KV_STATE_STOPPED);
    /* tun fd is owned by the adapter: still open after stop */
    CHECK(write(sp[1], "x", 1) == 1);
    close(sp[0]);
    close(sp[1]);
    /* tunnel restart in the same process */
    CHECK(socketpair(AF_UNIX, SOCK_DGRAM, 0, sp) == 0);
    c = base_config(free_port(), dir);
    c.tun_fd = sp[0];
    CHECK(kv_engine_start(e, &c) == KV_OK);
    CHECK(kv_engine_stop(e) == KV_OK);
    close(sp[0]);
    close(sp[1]);

    kv_engine_destroy(e);
    CHECK(kv_engine_create(&e2) == KV_OK);
    kv_engine_destroy(e2);
    rmdir(dir);

    if (failures) {
        fprintf(stderr, "%d check(s) failed\n", failures);
        return 1;
    }
    printf("kv_engine_test: all checks passed\n");
    return 0;
}
