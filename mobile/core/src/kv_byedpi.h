/* Thin wrapper over vendored ByeDPI (process-global state, single instance). */
#ifndef KV_BYEDPI_H
#define KV_BYEDPI_H

/* Parse argv (argv[0] is ignored) after restoring pristine defaults.
 * Returns a bound, listening socket fd on success, -1 on failure. */
int kv_byedpi_prepare(int argc, char **argv);
/* Runs the event loop on the fd from prepare(); returns when shut down. */
int kv_byedpi_run(int listen_fd);
/* Thread-safe: makes kv_byedpi_run() return. */
void kv_byedpi_shutdown(void);
/* Frees parsed parameters. Call after kv_byedpi_run() returned. */
void kv_byedpi_cleanup(void);
/* Undo a successful prepare() when run() will never be called. */
void kv_byedpi_abort(int listen_fd);

#endif
