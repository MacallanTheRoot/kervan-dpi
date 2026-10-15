"""Kernel-credential Unix IPC boundary for a separately installed helper.

The service accepts one bounded request per connection.  It never accepts a
claimed UID, PID, path, command, queue or firewall fragment from JSON.
"""

import json
import os
import select
import socket
import struct
import subprocess
import stat
import time
from concurrent.futures import ThreadPoolExecutor
from threading import BoundedSemaphore

from .zapret2 import parse_helper_request
from .zapret2_helper import Peer

MAX_REQUEST = 2048
MAX_CONNECTIONS = 8
REQUEST_TIMEOUT = 5
ACTION_OBSERVE = "org.kervan.dpi.observe"
ACTION_CONTROL = "org.kervan.dpi.control"


def process_start_time(pid):
    if type(pid) is not int or pid <= 0:
        raise ValueError("Invalid process identifier")
    # /proc/PID/stat's comm field may contain spaces and parentheses.
    with open(f"/proc/{pid}/stat", "r", encoding="ascii") as stream:
        value = stream.read()
    end = value.rfind(") ")
    if end < 0:
        raise ValueError("Malformed process identity")
    return int(value[end + 2:].split()[19])


def peer_pidfd(connection):
    """Pin the original socket peer; pidfd_open(PID) has a reuse window."""
    try:
        value = connection.getsockopt(socket.SOL_SOCKET,
                                      getattr(socket, "SO_PEERPIDFD", 77),
                                      struct.calcsize("i"))
    except OSError:
        return None
    if len(value) != struct.calcsize("i"):
        raise PermissionError("Invalid peer pidfd")
    descriptor = struct.unpack("i", value)[0]
    if descriptor < 0:
        raise PermissionError("Invalid peer pidfd")
    return descriptor


def _unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate request key")
        result[key] = value
    return result


def _read_exact(connection, size, deadline, clock):
    result = bytearray()
    while len(result) < size:
        remaining = deadline - clock()
        if remaining <= 0:
            raise TimeoutError("Helper request read timed out")
        connection.settimeout(remaining)
        chunk = connection.recv(size - len(result))
        if not chunk:
            raise ConnectionError("Truncated helper request")
        result.extend(chunk)
    return bytes(result)


class PkcheckAuthorizer:
    """Polkit check bound to kernel PID, process start time and kernel UID."""

    def __init__(self, runner=subprocess.run, executable="/usr/bin/pkcheck"):
        self.runner = runner
        self.executable = executable

    def __call__(self, peer, operation):
        if (not isinstance(peer, Peer) or peer.credentials_verified is not True or
                type(peer.pid) is not int or peer.pid <= 0 or
                type(peer.uid) is not int or peer.uid < 0 or
                type(peer.start_time) is not int or peer.start_time <= 0):
            return False
        if operation not in ("preflight", "status", "start", "stop", "recover"):
            return False
        action = ACTION_OBSERVE if operation in ("preflight", "status") else ACTION_CONTROL
        argv = [self.executable, "--action-id", action,
                "--process", f"{peer.pid},{peer.start_time},{peer.uid}"]
        if action == ACTION_CONTROL:
            argv.append("--allow-user-interaction")
        try:
            result = self.runner(argv, env={"PATH": "/usr/bin:/bin", "LANG": "C"},
                                 stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                 stderr=subprocess.DEVNULL, timeout=30, check=False)
        except (OSError, subprocess.SubprocessError):
            return False
        return result.returncode == 0


class SocketBoundary:
    """Dispatch on an already accepted Unix stream socket."""

    def __init__(self, helper, authorizer=None, *, authorized_dispatch=None,
                 request_timeout=REQUEST_TIMEOUT, clock=time.monotonic):
        if not 0 < request_timeout <= REQUEST_TIMEOUT:
            raise ValueError("Invalid IPC read timeout")
        self.helper = helper
        self.authorizer = authorizer or PkcheckAuthorizer()
        self.authorized_dispatch = authorized_dispatch
        self.request_timeout = request_timeout
        self.clock = clock

    def serve_connection(self, connection):
        connection.settimeout(self.request_timeout)
        credentials = connection.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED,
                                             struct.calcsize("3i"))
        if len(credentials) != struct.calcsize("3i"):
            raise PermissionError("Incomplete kernel peer credentials")
        pid, uid, _gid = struct.unpack("3i", credentials)
        if pid <= 0 or uid < 0:
            raise PermissionError("Invalid kernel peer credentials")
        pidfd = peer_pidfd(connection)
        try:
            if pidfd is None:
                raise PermissionError("Kernel peer pidfd required for authorization")
            start = process_start_time(pid)
            deadline = self.clock() + self.request_timeout
            size = struct.unpack("!I", _read_exact(connection, 4, deadline,
                                                   self.clock))[0]
            if size < 2 or size > MAX_REQUEST:
                raise ValueError("Invalid helper request size")
            request = json.loads(_read_exact(connection, size, deadline,
                                             self.clock).decode("utf-8"),
                                 object_pairs_hook=_unique_pairs)
            operation = parse_helper_request(request)
            peer = Peer(uid, pid, start, True)
            if not self.authorizer(peer, operation["operation"]):
                raise PermissionError("Polkit action denied")
            if process_start_time(pid) != start:
                raise PermissionError("Peer identity changed during authorization")
            if pidfd is not None:
                poller = select.poll()
                poller.register(pidfd, select.POLLIN | select.POLLHUP | select.POLLERR)
                if poller.poll(0):
                    raise PermissionError("Peer exited during authorization")
            # A peer that has already disconnected cannot authorize effects.
            readable, _, _ = select.select([connection], [], [], 0)
            if readable and connection.recv(1, socket.MSG_PEEK) == b"":
                raise ConnectionError("Peer disconnected before dispatch")
            result = (self.authorized_dispatch(operation, peer)
                      if self.authorized_dispatch is not None else
                      self.helper.request(operation, peer))
            payload = json.dumps({"ok": True, "result": result},
                                 separators=(",", ":")).encode("utf-8")
            connection.sendall(struct.pack("!I", len(payload)) + payload)
            return result
        finally:
            if pidfd is not None:
                os.close(pidfd)


def validate_systemd_listener(listener, *, path="/run/kervan-dpi/helper.sock",
                              trusted_uid=0, trusted_gid=0):
    """Check the inherited listener and its root-controlled filesystem path."""
    parent = os.stat(os.path.dirname(path), follow_symlinks=False)
    info = os.stat(path, follow_symlinks=False)
    if (listener.family != socket.AF_UNIX or
            listener.type & 0xf != socket.SOCK_STREAM or
            listener.getsockopt(socket.SOL_SOCKET, socket.SO_ACCEPTCONN) != 1 or
            listener.getsockname() != path or
            not stat.S_ISDIR(parent.st_mode) or parent.st_uid != trusted_uid or
            parent.st_gid != trusted_gid or stat.S_IMODE(parent.st_mode) != 0o755 or
            not stat.S_ISSOCK(info.st_mode) or info.st_uid != trusted_uid or
            info.st_gid != trusted_gid or stat.S_IMODE(info.st_mode) != 0o666):
        raise PermissionError("Untrusted systemd socket access policy")


def serve_systemd_socket(boundary, *, descriptor=3, max_connections=MAX_CONNECTIONS):
    """Only an explicitly started root service can enter the accept loop."""
    if os.geteuid() != 0 or os.environ.get("LISTEN_PID") != str(os.getpid()) or \
            os.environ.get("LISTEN_FDS") != "1":
        raise PermissionError("Expected one root-owned systemd socket")
    if type(max_connections) is not int or not 1 <= max_connections <= MAX_CONNECTIONS:
        raise ValueError("Invalid connection limit")
    with socket.socket(fileno=os.dup(descriptor)) as listener:
        validate_systemd_listener(listener)
        slots = BoundedSemaphore(max_connections)
        with ThreadPoolExecutor(max_workers=max_connections,
                                thread_name_prefix="kervan-ipc") as workers:
            while True:
                connection, _ = listener.accept()
                if not slots.acquire(blocking=False):
                    connection.close()
                    continue
                workers.submit(_serve_one, boundary, connection, slots)


def _serve_one(boundary, connection, slots):
    try:
        with connection:
            try:
                boundary.serve_connection(connection)
            except (OSError, ValueError, PermissionError, ConnectionError) as exc:
                payload = json.dumps({"ok": False, "error": type(exc).__name__},
                                     separators=(",", ":")).encode("ascii")
                try:
                    connection.sendall(struct.pack("!I", len(payload)) + payload)
                except OSError:
                    pass
    finally:
        slots.release()
