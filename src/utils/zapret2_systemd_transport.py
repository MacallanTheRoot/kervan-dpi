"""Fixed busctl/systemd transport and read-only cgroup inventory.

No method runs at import time. Callers must install the reviewed gate and
unit template before constructing a privileged service around this transport.
"""

import array
import json
import os
import re
import socket
import stat
import subprocess
from pathlib import Path

from .zapret2 import QUEUE, STRATEGIES
from .zapret2_systemd import PREFIX, UNIT
from .zapret2_trust import ARTIFACTS

DEST = "org.freedesktop.systemd1"
MANAGER = "/org/freedesktop/systemd1"
MANAGER_IFACE = DEST + ".Manager"
UNIT_IFACE = DEST + ".Unit"
SERVICE_IFACE = DEST + ".Service"
BUSCTL = "/usr/bin/busctl"
CGROUP_ROOT = Path("/sys/fs/cgroup")
RUN_ROOT = Path("/run")


def _unit(unit):
    if not isinstance(unit, str) or not UNIT.fullmatch(unit):
        raise ValueError("Invalid fixed Kervan unit")
    return unit


def _runtime_path(unit, root=RUN_ROOT):
    _unit(unit)
    return root / ("kervan-dpi-gate-" + unit[len(PREFIX):-len(".service")])


def _trusted_directory(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
    info = os.fstat(fd)
    if info.st_uid != 0 or stat.S_IMODE(info.st_mode) != 0o700:
        os.close(fd)
        raise PermissionError("Untrusted gate runtime directory")
    return fd


def cgroup_is_empty(path, *, root=CGROUP_ROOT):
    """Inspect all descendants on unified cgroup v2; errors fail closed."""
    if (not isinstance(path, str) or not path.startswith("/kervan.slice/") or
            not UNIT.fullmatch(path.removeprefix("/kervan.slice/"))):
        raise ValueError("Invalid Kervan cgroup")
    if not (root / "cgroup.controllers").is_file():
        raise RuntimeError("Unified cgroup v2 is required")
    current = root / path.lstrip("/")
    try:
        directory = os.open(current, os.O_RDONLY | os.O_DIRECTORY |
                            os.O_NOFOLLOW | os.O_CLOEXEC)
    except FileNotFoundError:
        return True
    stack = [directory]
    try:
        while stack:
            fd = stack.pop()
            try:
                for name in ("cgroup.procs", "cgroup.threads"):
                    try:
                        member = os.open(name, os.O_RDONLY | os.O_NOFOLLOW |
                                         os.O_CLOEXEC, dir_fd=fd)
                    except FileNotFoundError:
                        raise RuntimeError("Incomplete cgroup inventory")
                    try:
                        if os.read(member, 1):
                            return False
                    finally:
                        os.close(member)
                for child in os.listdir(fd):
                    try:
                        nested = os.open(child, os.O_RDONLY | os.O_DIRECTORY |
                                         os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=fd)
                    except NotADirectoryError:
                        continue
                    stack.append(nested)
            finally:
                os.close(fd)
        return True
    finally:
        for pending in stack:
            os.close(pending)


class BusctlGateTransport:
    """D-Bus calls are restricted to PID 1 and a fixed systemd unit family."""

    def __init__(self, *, runner=subprocess.run, cgroup_root=CGROUP_ROOT,
                 run_root=RUN_ROOT):
        self.runner = runner
        self.cgroup_root = Path(cgroup_root)
        self.run_root = Path(run_root)

    def _bus(self, *args):
        result = self.runner([BUSCTL, "--system", "--json=short", "--no-pager",
                              *args], text=True, capture_output=True, check=False,
                             timeout=3, env={"PATH": "/usr/bin:/bin", "LANG": "C"})
        if result.returncode:
            raise RuntimeError("systemd D-Bus call failed: " + result.stderr.strip()[:160])
        try:
            reply = json.loads(result.stdout)
        except (ValueError, TypeError) as exc:
            raise RuntimeError("Malformed systemd D-Bus reply") from exc
        if not isinstance(reply, dict):
            raise RuntimeError("Malformed systemd D-Bus reply")
        return reply

    def _call(self, method, signature, *parameters):
        return self._bus("call", DEST, MANAGER, MANAGER_IFACE, method,
                         signature, *parameters)

    def list_units(self, pattern):
        if pattern != PREFIX + "*.service":
            raise ValueError("Invalid systemd inventory pattern")
        reply = self._call("ListUnitsByPatterns", "asas", "0", "1", pattern)
        if reply.get("type") != "a(ssssssouso)":
            raise RuntimeError("Malformed systemd unit inventory")
        rows = reply.get("data")
        if not isinstance(rows, list) or len(rows) != 1 or not isinstance(rows[0], list):
            raise RuntimeError("Malformed systemd unit inventory")
        if any(not isinstance(row, list) or len(row) != 10 or
               not isinstance(row[0], str) or not UNIT.fullmatch(row[0])
               for row in rows[0]):
            raise RuntimeError("Incomplete or foreign systemd unit inventory")
        return [row[0] for row in rows[0]]

    def list_cgroups(self):
        if not (self.cgroup_root / "cgroup.controllers").is_file():
            raise RuntimeError("Unified cgroup v2 is required")
        path = self.cgroup_root / "kervan.slice"
        try:
            directory = os.open(path, os.O_RDONLY | os.O_DIRECTORY |
                                os.O_NOFOLLOW | os.O_CLOEXEC)
        except FileNotFoundError:
            return []
        try:
            names = []
            for name in os.listdir(directory):
                info = os.stat(name, dir_fd=directory, follow_symlinks=False)
                if stat.S_ISDIR(info.st_mode):
                    names.append(name)
                elif UNIT.fullmatch(name):
                    raise RuntimeError("Kervan cgroup entry is not a directory")
            return names
        finally:
            os.close(directory)

    def properties(self, unit):
        _unit(unit)
        try:
            reply = self._call("GetUnit", "s", unit)
        except RuntimeError as exc:
            if "not loaded" in str(exc) or "NoSuchUnit" in str(exc):
                return None
            raise
        if (reply.get("type") != "o" or not isinstance(reply.get("data"), list) or
                len(reply["data"]) != 1 or not isinstance(reply["data"][0], str) or
                not reply["data"][0].startswith("/org/freedesktop/systemd1/unit/")):
            raise RuntimeError("Malformed systemd unit object")
        path = reply["data"][0]
        names = ("Id", "Names", "FragmentPath", "Description", "LoadState",
                 "ActiveState", "ControlGroup", "DropInPaths", "SourcePath",
                 "NeedDaemonReload", "ExecStart")
        properties = {}
        for name in names:
            iface = SERVICE_IFACE if name in ("ControlGroup", "ExecStart") else UNIT_IFACE
            result = self._bus("get-property", DEST, path, iface, name)
            signature = ("as" if name in ("Names", "DropInPaths") else
                         "b" if name == "NeedDaemonReload" else
                         "a(sasbttttuii)" if name == "ExecStart" else "s")
            if result.get("type") != signature:
                raise RuntimeError("Malformed systemd property")
            properties[name] = result.get("data")
        return properties

    def _job(self, method, unit):
        _unit(unit)
        if os.geteuid() != 0:
            raise PermissionError("Only root may change systemd units")
        reply = self._call(method, "ss", unit, "fail")
        if (reply.get("type") != "o" or not isinstance(reply.get("data"), list) or
                len(reply["data"]) != 1):
            raise RuntimeError("Malformed systemd job reply")
        return reply["data"][0]

    def start_unit(self, unit):
        return self._job("StartUnit", unit)

    def stop_unit(self, unit):
        return self._job("StopUnit", unit)

    def job_state(self, path):
        if not isinstance(path, str) or not re.fullmatch(
                r"/org/freedesktop/systemd1/job/[0-9]+", path):
            raise ValueError("Invalid systemd job path")
        try:
            reply = self._bus("get-property", DEST, path, DEST + ".Job", "State")
        except RuntimeError as exc:
            if "Unknown object" in str(exc) or "NoSuchJob" in str(exc):
                return "done"  # Caller must still inspect unit and cgroup.
            raise
        if reply.get("type") != "s" or reply.get("data") not in ("waiting", "running"):
            raise RuntimeError("Unknown systemd job state")
        return "queued" if reply["data"] == "waiting" else "running"

    def cgroup_empty(self, path):
        return cgroup_is_empty(path, root=self.cgroup_root)

    def gate_state(self, unit):
        path = _runtime_path(unit, self.run_root)
        try:
            directory = _trusted_directory(path)
        except FileNotFoundError:
            return "gone"
        try:
            fd = os.open("state", os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC,
                         dir_fd=directory)
            try:
                info = os.fstat(fd)
                if (not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or
                        info.st_nlink != 1 or stat.S_IMODE(info.st_mode) != 0o600):
                    raise PermissionError("Untrusted gate state")
                state = os.read(fd, 32)
            finally:
                os.close(fd)
            if state not in (b"waiting\n", b"activated\n"):
                raise RuntimeError("Invalid gate state")
            return state.decode("ascii").strip()
        finally:
            os.close(directory)

    def gate_activate(self, unit, token, argv, descriptors, timeout):
        _unit(unit)
        if os.geteuid() != 0 or not 0 < timeout <= 10:
            raise PermissionError("Only root may activate a gate")
        descriptors = tuple(descriptors)
        if len(descriptors) != len(ARTIFACTS) or any(
                type(fd) is not int or fd < 0 for fd in descriptors):
            raise ValueError("Invalid verified descriptors")
        binary, library, antidpi = descriptors
        prefix = [f"/proc/self/fd/{binary}", f"--qnum={QUEUE}",
                  f"--lua-init=@/proc/self/fd/{library}",
                  f"--lua-init=@/proc/self/fd/{antidpi}"]
        strategies = [name for name, options in STRATEGIES.items()
                      if argv == prefix + list(options)]
        if len(strategies) != 1:
            raise ValueError("Unapproved gate arguments")
        path = _runtime_path(unit, self.run_root)
        directory = _trusted_directory(path)
        try:
            info = os.stat("activate.sock", dir_fd=directory, follow_symlinks=False)
            if (not stat.S_ISSOCK(info.st_mode) or info.st_uid != 0 or
                    stat.S_IMODE(info.st_mode) != 0o600):
                raise PermissionError("Untrusted gate socket")
            with socket.socket(socket.AF_UNIX, socket.SOCK_SEQPACKET) as connection:
                connection.settimeout(timeout)
                connection.connect(str(path / "activate.sock"))
                payload = json.dumps({"token": token, "strategy": strategies[0]},
                                     separators=(",", ":")).encode("ascii")
                connection.sendmsg([payload], [(socket.SOL_SOCKET, socket.SCM_RIGHTS,
                                                array.array("i", descriptors))])
                if connection.recv(16) != b"PREPARED":
                    raise RuntimeError("Gate did not prepare activation")
                connection.sendall(b"COMMIT")
                if connection.recv(16) != b"ACTIVATED":
                    raise RuntimeError("Gate did not acknowledge activation")
        finally:
            os.close(directory)
