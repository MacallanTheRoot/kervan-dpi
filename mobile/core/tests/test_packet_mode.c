/* Host tests for packet mode (the iOS NEPacketTunnelFlow path) without iOS:
 * the test plays the role of packetFlow, injecting hand-built IPv4/TCP packets
 * with kv_engine_packet_in() and reading the tunnel's replies from
 * packet_out_cb. A full TCP exchange goes TUN -> lwIP -> SOCKS5 -> ByeDPI
 * (default desync strategy) -> echo server and back. No protect callback,
 * as on iOS. */
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
#include <time.h>
#include <unistd.h>

static int failures;
#define CHECK(cond) do { if (!(cond)) { fprintf(stderr, "FAIL %s:%d: %s\n", __FILE__, __LINE__, #cond); failures++; } } while (0)

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

/* ---- echo server ---- */
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
        while ((n = recv(c, buf, sizeof(buf), 0)) > 0) send(c, buf, (size_t)n, 0);
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

/* ---- fake packetFlow: queue of packets from packet_out_cb ---- */
#define QMAX 64
static pthread_mutex_t qlock = PTHREAD_MUTEX_INITIALIZER;
static pthread_cond_t qcond = PTHREAD_COND_INITIALIZER;
static uint8_t qpkt[QMAX][2048];
static size_t qlen[QMAX];
static int qhead, qcount;
static atomic_int out_bad_family;

static void packet_out(void *user, const uint8_t *p, size_t len, int family)
{
    (void)user;
    if (family != (p[0] >> 4)) atomic_fetch_add(&out_bad_family, 1);
    pthread_mutex_lock(&qlock);
    if (qcount < QMAX && len <= sizeof(qpkt[0])) {
        int i = (qhead + qcount) % QMAX;
        memcpy(qpkt[i], p, len);
        qlen[i] = len;
        qcount++;
        pthread_cond_signal(&qcond);
    }
    pthread_mutex_unlock(&qlock);
}

/* Pop the next packet; 0 on timeout. */
static size_t pop_packet(uint8_t *out, int timeout_ms)
{
    struct timespec ts;
    clock_gettime(CLOCK_REALTIME, &ts);
    ts.tv_sec += timeout_ms / 1000;
    ts.tv_nsec += (long)(timeout_ms % 1000) * 1000000L;
    if (ts.tv_nsec >= 1000000000L) { ts.tv_sec++; ts.tv_nsec -= 1000000000L; }
    size_t n = 0;
    pthread_mutex_lock(&qlock);
    while (qcount == 0 && pthread_cond_timedwait(&qcond, &qlock, &ts) == 0) {}
    if (qcount > 0) {
        n = qlen[qhead];
        memcpy(out, qpkt[qhead], n);
        qhead = (qhead + 1) % QMAX;
        qcount--;
    }
    pthread_mutex_unlock(&qlock);
    return n;
}

/* ---- IPv4/TCP builder ---- */
#define TH_FIN 0x01
#define TH_SYN 0x02
#define TH_RST 0x04
#define TH_PSH 0x08
#define TH_ACK 0x10

static uint32_t csum_add(uint32_t sum, const uint8_t *p, size_t n)
{
    for (size_t i = 0; i + 1 < n; i += 2) sum += (uint32_t)(p[i] << 8 | p[i + 1]);
    if (n & 1) sum += (uint32_t)(p[n - 1] << 8);
    return sum;
}
static uint16_t csum_fold(uint32_t sum)
{
    while (sum >> 16) sum = (sum & 0xffff) + (sum >> 16);
    return (uint16_t)~sum;
}

static const uint8_t CLIENT_IP[4] = { 10, 111, 222, 1 }; /* iOS tunnel address */
static const uint8_t SERVER_IP[4] = { 127, 0, 0, 1 };
#define CLIENT_PORT 40000

static size_t build_tcp(uint8_t *pkt, uint32_t seq, uint32_t ack, uint8_t flags,
                        const void *data, size_t dlen)
{
    uint8_t *ip = pkt, *tcp = pkt + 20;
    size_t tot = 20 + 20 + dlen;
    memset(pkt, 0, 40);
    ip[0] = 0x45;
    ip[2] = (uint8_t)(tot >> 8); ip[3] = (uint8_t)tot;
    ip[8] = 64; ip[9] = IPPROTO_TCP;
    memcpy(ip + 12, CLIENT_IP, 4);
    memcpy(ip + 16, SERVER_IP, 4);
    uint16_t c = csum_fold(csum_add(0, ip, 20));
    ip[10] = (uint8_t)(c >> 8); ip[11] = (uint8_t)c;

    tcp[0] = CLIENT_PORT >> 8; tcp[1] = CLIENT_PORT & 0xff;
    tcp[2] = (uint8_t)(echo_port >> 8); tcp[3] = (uint8_t)echo_port;
    uint32_t nseq = htonl(seq), nack = htonl(ack);
    memcpy(tcp + 4, &nseq, 4);
    memcpy(tcp + 8, &nack, 4);
    tcp[12] = 5 << 4;
    tcp[13] = flags;
    tcp[14] = 0xff; tcp[15] = 0xff; /* window */
    if (dlen) memcpy(tcp + 20, data, dlen);
    uint8_t pseudo[12];
    memcpy(pseudo, CLIENT_IP, 4);
    memcpy(pseudo + 4, SERVER_IP, 4);
    pseudo[8] = 0; pseudo[9] = IPPROTO_TCP;
    pseudo[10] = (uint8_t)((20 + dlen) >> 8); pseudo[11] = (uint8_t)(20 + dlen);
    c = csum_fold(csum_add(csum_add(0, pseudo, 12), tcp, 20 + dlen));
    tcp[16] = (uint8_t)(c >> 8); tcp[17] = (uint8_t)c;
    return tot;
}

struct tcp_view { uint8_t flags; uint32_t seq, ack; const uint8_t *data; size_t dlen; int ok; };

static struct tcp_view parse_tcp(const uint8_t *p, size_t n)
{
    struct tcp_view v = { 0 };
    if (n < 40 || (p[0] >> 4) != 4 || p[9] != IPPROTO_TCP) return v;
    size_t ihl = (size_t)(p[0] & 0xf) * 4;
    const uint8_t *t = p + ihl;
    if (memcmp(p + 12, SERVER_IP, 4) || memcmp(p + 16, CLIENT_IP, 4)) return v;
    if ((t[0] << 8 | t[1]) != echo_port || (t[2] << 8 | t[3]) != CLIENT_PORT) return v;
    size_t thl = (size_t)(t[12] >> 4) * 4;
    size_t tot = (size_t)(p[2] << 8 | p[3]);
    memcpy(&v.seq, t + 4, 4); v.seq = ntohl(v.seq);
    memcpy(&v.ack, t + 8, 4); v.ack = ntohl(v.ack);
    v.flags = t[13];
    v.data = t + thl;
    v.dlen = tot - ihl - thl;
    v.ok = 1;
    return v;
}

/* ---- concurrent packet_in during stop ---- */
static atomic_int hammer_run;
static void *hammer(void *arg)
{
    kv_engine_t *e = arg;
    uint8_t pkt[64];
    size_t n = build_tcp(pkt, 1, 0, TH_SYN, NULL, 0);
    while (atomic_load(&hammer_run)) kv_engine_packet_in(e, pkt, n);
    return NULL;
}

static kv_engine_config_t packet_config(void)
{
    kv_engine_config_t c = { 0 };
    c.struct_size = sizeof(c);
    c.tun_fd = KV_TUN_PACKET_MODE;
    c.tun_mtu = 1500;
    c.socks_port = free_port();
    c.desync_args = "-d1 -s1+s -r1+s"; /* same default strategy as Android */
    c.enable_udp = 1;
    c.require_protect = 0;             /* iOS: no protect callback */
    c.log_cb = quiet_log;
    c.packet_out_cb = packet_out;
    return c;
}

int main(void)
{
    start_echo();
    kv_engine_t *e = NULL;
    CHECK(kv_engine_create(&e) == KV_OK);
    int fds_before = count_fds();

    /* invalid configs */
    kv_engine_config_t c = packet_config();
    c.packet_out_cb = NULL;
    CHECK(kv_engine_start(e, &c) == KV_ERR_INVALID_ARG);
    c = packet_config();
    c.tun_fd = -3;
    CHECK(kv_engine_start(e, &c) == KV_ERR_INVALID_ARG);
    c = packet_config();
    c.tun_mtu = 100;
    CHECK(kv_engine_start(e, &c) == KV_ERR_INVALID_ARG);

    uint8_t pkt[2048], in[2048];
    size_t n = build_tcp(pkt, 1000, 0, TH_SYN, NULL, 0);
    CHECK(kv_engine_packet_in(e, pkt, n) == KV_ERR_BUSY); /* not running: nothing queued */

    /* 1. full TCP exchange through the packet bridge */
    c = packet_config();
    CHECK(kv_engine_start(e, &c) == KV_OK);
    CHECK(kv_engine_state(e) == KV_STATE_RUNNING);

    uint8_t junk[4] = { 0x00, 1, 2, 3 };
    CHECK(kv_engine_packet_in(e, junk, sizeof(junk)) == KV_ERR_INVALID_ARG);
    CHECK(kv_engine_packet_in(e, pkt, 1501) == KV_ERR_INVALID_ARG); /* > mtu */

    uint32_t cseq = 1000;
    CHECK(kv_engine_packet_in(e, pkt, n) == KV_OK);
    struct tcp_view v = { 0 };
    for (int i = 0; i < 5 && !(v.ok && (v.flags & (TH_SYN | TH_ACK)) == (TH_SYN | TH_ACK)); i++) {
        size_t m = pop_packet(in, 2000);
        if (!m) break;
        v = parse_tcp(in, m);
    }
    CHECK(v.ok && (v.flags & (TH_SYN | TH_ACK)) == (TH_SYN | TH_ACK) && v.ack == cseq + 1);
    uint32_t sseq = v.seq + 1;
    cseq += 1;

    n = build_tcp(pkt, cseq, sseq, TH_ACK, NULL, 0);
    CHECK(kv_engine_packet_in(e, pkt, n) == KV_OK);
    const char msg[] = "GET / HTTP/1.1\r\nHost: discord.com\r\n\r\n";
    size_t mlen = sizeof(msg) - 1;
    n = build_tcp(pkt, cseq, sseq, TH_ACK | TH_PSH, msg, mlen);
    CHECK(kv_engine_packet_in(e, pkt, n) == KV_OK);
    cseq += (uint32_t)mlen;

    /* collect echoed bytes (possibly split into several segments) */
    char echoed[256];
    size_t got = 0;
    for (int i = 0; i < 20 && got < mlen; i++) {
        size_t m = pop_packet(in, 3000);
        if (!m) break;
        v = parse_tcp(in, m);
        if (v.ok && v.dlen > 0 && v.seq == sseq && got + v.dlen <= sizeof(echoed)) {
            memcpy(echoed + got, v.data, v.dlen);
            got += v.dlen;
            sseq += (uint32_t)v.dlen;
            n = build_tcp(pkt, cseq, sseq, TH_ACK, NULL, 0);
            kv_engine_packet_in(e, pkt, n);
        }
    }
    CHECK(got == mlen && memcmp(echoed, msg, mlen) == 0);
    CHECK(atomic_load(&out_bad_family) == 0);
    n = build_tcp(pkt, cseq, sseq, TH_RST | TH_ACK, NULL, 0);
    kv_engine_packet_in(e, pkt, n);

    /* 2. stop is idempotent; packet_in after stop is refused */
    CHECK(kv_engine_stop(e) == KV_OK);
    CHECK(kv_engine_stop(e) == KV_OK);
    CHECK(kv_engine_state(e) == KV_STATE_STOPPED);
    n = build_tcp(pkt, 1, 0, TH_SYN, NULL, 0);
    CHECK(kv_engine_packet_in(e, pkt, n) == KV_ERR_BUSY);

    /* 3. repeated start/stop with packets arriving from another thread during
     *    stop (NEPacketTunnelFlow keeps delivering while stopTunnel runs) */
    for (int i = 0; i < 5; i++) {
        c = packet_config();
        CHECK(kv_engine_start(e, &c) == KV_OK);
        atomic_store(&hammer_run, 1);
        pthread_t t;
        pthread_create(&t, NULL, hammer, e);
        struct timespec ts = { 0, 30 * 1000 * 1000 };
        nanosleep(&ts, NULL);
        CHECK(kv_engine_stop(e) == KV_OK);
        atomic_store(&hammer_run, 0);
        pthread_join(t, NULL);
        while (pop_packet(in, 1)) {}
    }
    CHECK(count_fds() == fds_before);

    kv_engine_destroy(e);
    if (failures) {
        fprintf(stderr, "%d check(s) failed\n", failures);
        return 1;
    }
    printf("kv_packet_mode_test: all checks passed\n");
    return 0;
}
