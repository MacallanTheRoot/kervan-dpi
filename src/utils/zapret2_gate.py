"""Pre-exec barrier for the fixed kervan-nfqws2@.service template.

This process is started by PID 1 inside the unit cgroup. It cannot exec the
engine until a root helper transfers three verified descriptors through its
private runtime socket. No client-selected path or command is accepted.
"""

import array
import hashlib
import json
import os
import re
import socket
import stat
import sys

from .zapret2 import QUEUE, STRATEGIES
from .zapret2_trust import ARTIFACTS, PINNED_SHA256, VerifiedRelease


def _write_state(directory, state):
    temporary = ".state-" + str(os.getpid())
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL |
                 os.O_NOFOLLOW | os.O_CLOEXEC, 0o600, dir_fd=directory)
    try:
        os.write(fd, (state + "\n").encode("ascii"))
        os.fsync(fd)
    finally:
        os.close(fd)
    os.replace(temporary, "state", src_dir_fd=directory, dst_dir_fd=directory)
    os.fsync(directory)


def _check_descriptors(descriptors, *, trusted_uid=0, hashes=PINNED_SHA256):
    if len(descriptors) != len(ARTIFACTS):
        raise ValueError("Gate requires three descriptors")
    for name, descriptor in zip(ARTIFACTS, descriptors):
        info = os.fstat(descriptor)
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != trusted_uid or
                info.st_nlink != 1 or stat.S_IMODE(info.st_mode) !=
                (0o755 if name == "nfqws2" else 0o644)):
            raise PermissionError("Untrusted gate artifact")
        digest = hashlib.sha256()
        os.lseek(descriptor, 0, os.SEEK_SET)
        while chunk := os.read(descriptor, 1024 * 1024):
            digest.update(chunk)
        if digest.hexdigest() != hashes[name]:
            raise ValueError("Gate artifact digest mismatch")
        os.lseek(descriptor, 0, os.SEEK_SET)


def _unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate gate activation field")
        result[key] = value
    return result


def _receive(connection, token, *, trusted_uid=0, hashes=PINNED_SHA256):
    credentials = connection.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12)
    import struct
    _pid, uid, _gid = struct.unpack("3i", credentials)
    if uid != trusted_uid:
        raise PermissionError("Gate accepts only the root helper")
    payload, ancillary, flags, _address = connection.recvmsg(
        512, socket.CMSG_SPACE(len(ARTIFACTS) * array.array("i").itemsize))
    if flags & (socket.MSG_TRUNC | socket.MSG_CTRUNC):
        raise ValueError("Truncated gate activation")
    descriptors = []
    try:
        for level, kind, data in ancillary:
            if level != socket.SOL_SOCKET or kind != socket.SCM_RIGHTS:
                raise ValueError("Unexpected gate control message")
            values = array.array("i")
            values.frombytes(data)
            descriptors.extend(values)
        request = json.loads(payload.decode("ascii"), object_pairs_hook=_unique_pairs)
        if (not isinstance(request, dict) or set(request) != {"token", "strategy"} or
                request["token"] != token or request["strategy"] not in STRATEGIES):
            raise ValueError("Invalid gate activation request")
        _check_descriptors(descriptors, trusted_uid=trusted_uid, hashes=hashes)
        return descriptors, request["strategy"]
    except BaseException:
        for descriptor in descriptors:
            os.close(descriptor)
        raise


def _await_commit(connection):
    connection.sendall(b"PREPARED")
    if connection.recv(16) != b"COMMIT":
        raise ConnectionError("Gate activation was not committed")


def run(instance, *, runtime_root="/run"):
    if os.geteuid() != 0 or not isinstance(instance, str) or not re.fullmatch(
            r"[0-9a-f]{32}", instance):
        raise PermissionError("Invalid privileged gate instance")
    unit = "kervan-nfqws2@" + instance + ".service"
    group = "/kervan.slice/" + unit
    with open("/proc/self/cgroup", "r", encoding="ascii") as stream:
        memberships = stream.read().splitlines()
    if memberships != ["0::" + group]:
        raise RuntimeError("Gate is outside its exact systemd cgroup")
    runtime = os.path.join(runtime_root, "kervan-dpi-gate-" + instance)
    directory = os.open(runtime, os.O_RDONLY | os.O_DIRECTORY |
                        os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        info = os.fstat(directory)
        if info.st_uid != 0 or stat.S_IMODE(info.st_mode) != 0o700:
            raise PermissionError("Untrusted gate runtime directory")
        listener = socket.socket(socket.AF_UNIX, socket.SOCK_SEQPACKET)
        try:
            listener.bind(os.path.join(runtime, "activate.sock"))
            os.chmod(os.path.join(runtime, "activate.sock"), 0o600)
            listener.listen(1)
            _write_state(directory, "waiting")
            connection, _ = listener.accept()
            with connection:
                connection.settimeout(10)
                descriptors, strategy = _receive(connection, "kervan:" + instance)
                try:
                    _await_commit(connection)
                    _write_state(directory, "activated")
                    connection.sendall(b"ACTIVATED")
                except BaseException:
                    for descriptor in descriptors:
                        os.close(descriptor)
                    raise
        finally:
            listener.close()
        for descriptor in descriptors:
            os.set_inheritable(descriptor, True)
        argv = VerifiedRelease(dict(zip(ARTIFACTS, descriptors))).argv(strategy, QUEUE)
        os.execve(argv[0], argv, {"PATH": "/usr/bin:/bin", "LANG": "C"})
    finally:
        os.close(directory)


def main():
    if len(sys.argv) != 2:
        raise SystemExit(2)
    run(sys.argv[1])


if __name__ == "__main__":
    main()
