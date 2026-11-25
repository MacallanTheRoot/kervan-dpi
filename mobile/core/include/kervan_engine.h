/*
 * Kervan DPI portable engine — public C ABI.
 *
 * Plain C99. No Android (JNI) or Apple (Foundation/NetworkExtension) types.
 * Platform adapters own the tunnel and hand packets to the core in one of two
 * ways:
 *   fd mode     (Android)  tun_fd = the VpnService TUN descriptor.
 *   packet mode (iOS)      tun_fd = KV_TUN_PACKET_MODE; the adapter feeds
 *               packets from NEPacketTunnelFlow with kv_engine_packet_in() and
 *               receives packets for the system through packet_out_cb. The
 *               core bridges them to the tunnel over a private socketpair, so
 *               no utun descriptor is needed.
 *
 * Data path:  TUN -> hev-socks5-tunnel (lwIP) -> SOCKS5 127.0.0.1:<port>
 *             -> ByeDPI desync proxy -> outbound socket -> network
 * Outbound sockets go through protect_cb when one is given (Android). On iOS
 * sockets opened by the packet tunnel provider do not enter its own tunnel,
 * so the adapter passes no protect_cb (to be confirmed on device).
 *
 * Single instance: both vendored engines keep process-global state, so at most
 * one engine may exist per process. kv_engine_create() enforces this.
 */
#ifndef KERVAN_ENGINE_H
#define KERVAN_ENGINE_H

#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define KV_ENGINE_ABI_VERSION 2

/* tun_fd value that selects packet mode (an enum so Swift imports it). */
enum { KV_TUN_PACKET_MODE = -2 };

typedef enum {
    KV_OK = 0,
    KV_ERR_INVALID_ARG = -1,
    KV_ERR_BUSY = -2,          /* another engine exists or wrong state */
    KV_ERR_NO_MEMORY = -3,
    KV_ERR_PROXY_START = -4,   /* ByeDPI failed to parse args or listen */
    KV_ERR_PROTECT_SETUP = -5, /* protect bridge could not be created */
    KV_ERR_TUNNEL_START = -6,  /* hev-socks5-tunnel exited during startup */
    KV_ERR_TIMEOUT = -7,
    KV_ERR_DROPPED = -8        /* packet_in: tunnel queue full, packet dropped */
} kv_status_t;

typedef enum {
    KV_STATE_STOPPED = 0,
    KV_STATE_STARTING = 1,
    KV_STATE_RUNNING = 2,  /* proxy listening AND tunnel loop alive; NOT bypass proof */
    KV_STATE_STOPPING = 3,
    KV_STATE_FAILED = 4    /* a component died unexpectedly; adapter must tear down */
} kv_state_t;

typedef enum { KV_LOG_DEBUG = 0, KV_LOG_INFO = 1, KV_LOG_WARN = 2, KV_LOG_ERROR = 3 } kv_log_level_t;

/* Return 0 if fd is now exempt from the tunnel (Android: VpnService.protect).
 * Any non-zero result makes the engine drop that connection (fail closed).
 * Called from an engine thread. */
typedef int (*kv_protect_fn)(void *user, int fd);
typedef void (*kv_log_fn)(void *user, kv_log_level_t level, const char *message);
/* Called from an engine thread on every state change. */
typedef void (*kv_state_fn)(void *user, kv_state_t state, kv_status_t reason);
/* Packet mode: one IP packet (no link or AF header) for the system, i.e. for
 * NEPacketTunnelFlow.writePackets. family is 4 or 6. Called from one engine
 * thread; packet is only valid during the call. */
typedef void (*kv_packet_out_fn)(void *user, const uint8_t *packet, size_t len, int family);

typedef struct {
    uint32_t struct_size;        /* sizeof(kv_engine_config_t) */
    int tun_fd;                  /* >=0 fd mode, KV_TUN_PACKET_MODE, -1 proxy only */
    uint32_t tun_mtu;            /* e.g. 1500 */
    uint16_t socks_port;         /* loopback port for the internal SOCKS5 hop */
    const char *runtime_dir;     /* private writable dir for the protect socket */
    const char *desync_args;     /* ByeDPI strategy, space separated, e.g. "-s1 -d1" */
    int enable_udp;              /* relay UDP (DNS, QUIC) through the proxy */
    int require_protect;         /* 1: outbound sockets MUST pass protect_cb */
    kv_protect_fn protect_cb;
    kv_log_fn log_cb;
    kv_state_fn state_cb;
    void *user;
    kv_packet_out_fn packet_out_cb; /* required in packet mode, else ignored */
} kv_engine_config_t;

typedef struct kv_engine kv_engine_t;

uint32_t kv_engine_abi_version(void);
/* 1 if protect_cb is supported (Linux/Android). Elsewhere (macOS/iOS) a
 * config with protect_cb or require_protect is rejected: KV_ERR_INVALID_ARG. */
int kv_engine_supports_protect(void);

kv_status_t kv_engine_create(kv_engine_t **out);
/* Blocks until RUNNING or failure (bounded by an internal timeout). */
kv_status_t kv_engine_start(kv_engine_t *engine, const kv_engine_config_t *config);
/* Idempotent. Blocks until all engine threads joined and engine sockets closed.
 * Does NOT close tun_fd: the platform adapter owns it. */
kv_status_t kv_engine_stop(kv_engine_t *engine);
kv_state_t kv_engine_state(const kv_engine_t *engine);
/* Packet mode: queue one IP packet from the system (NEPacketTunnelFlow
 * readPackets) into the tunnel. Thread-safe, never blocks. Returns
 * KV_ERR_BUSY when not running, KV_ERR_INVALID_ARG for a non-IP packet or one
 * larger than tun_mtu, KV_ERR_DROPPED when the queue is full. */
kv_status_t kv_engine_packet_in(kv_engine_t *engine, const void *packet, size_t len);
/* Stops if needed, then frees. */
void kv_engine_destroy(kv_engine_t *engine);

const char *kv_status_string(kv_status_t status);

#ifdef __cplusplus
}
#endif

#endif /* KERVAN_ENGINE_H */
