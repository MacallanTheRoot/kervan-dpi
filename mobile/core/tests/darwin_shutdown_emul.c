/* Test-only: emulate XNU, where shutdown() on a listening (unconnected)
 * socket fails with ENOTCONN and wakes nothing. Linked into the
 * *_darwin_emul tests so Linux CI exercises the macOS/iOS stop path. */
#define _GNU_SOURCE
#include <errno.h>
#include <sys/socket.h>
#include <sys/syscall.h>
#include <unistd.h>

int shutdown(int fd, int how)
{
    int listening = 0;
    socklen_t len = sizeof(listening);
    if (getsockopt(fd, SOL_SOCKET, SO_ACCEPTCONN, &listening, &len) == 0 && listening) {
        errno = ENOTCONN;
        return -1;
    }
    return (int)syscall(SYS_shutdown, fd, how);
}
