/* Force-included into ByeDPI's conev.c (see CMakeLists.txt). Routes its
 * poll() event loop through kv_byedpi_poll() so kv_byedpi_shutdown() can wake
 * it portably. Needed on macOS/iOS: there shutdown() on a listening socket
 * fails with ENOTCONN and wakes nothing, so the loop would never exit.
 * <poll.h> is included first so its declaration of poll() stays untouched. */
#ifndef KV_BYEDPI_POLL_H
#define KV_BYEDPI_POLL_H
#include <poll.h>
int kv_byedpi_poll(struct pollfd *fds, nfds_t nfds, int timeout_ms);
#define poll(fds, nfds, timeout_ms) kv_byedpi_poll(fds, nfds, timeout_ms)
#endif
