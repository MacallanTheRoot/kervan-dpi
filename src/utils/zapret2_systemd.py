"""Constrained systemd supervisor protocol for the packaged NFQUEUE gate.

The transport is an explicit privileged D-Bus and gate-channel boundary. This
module deliberately has no implicit host transport or process killing path.
The packaged gate must block engine exec until activate() supplies verified
descriptors. StartUnit alone is not a reservation primitive.
"""

import re
import threading
import time
import uuid

from .zapret2_journal import boot_id as current_boot_id
from .zapret2_nft_plan import OWNER_PATTERN
from .zapret2_process import SupervisorSnapshot


TEMPLATE = "/usr/lib/systemd/system/kervan-nfqws2@.service"
UNIT = re.compile(r"kervan-nfqws2@[0-9a-f]{32}\.service\Z")
PREFIX = "kervan-nfqws2@"


class SystemdGateManager:
    """Map only fixed units to systemd D-Bus and a root-only activation gate.

    transport methods: list_units(pattern), properties(unit), start_unit(unit),
    stop_unit(unit), job_state(path), cgroup_empty(path), gate_state(unit),
    gate_activate(unit, token, argv, descriptors, timeout). All reads must be
    authoritative; missing evidence is an error, not proof of absence.
    """

    def __init__(self, transport, boot_id, *, clock=time.monotonic,
                 pause=time.sleep, boot_reader=current_boot_id):
        uuid.UUID(boot_id)
        self.transport = transport
        self.boot_id = boot_id
        self.clock = clock
        self.pause = pause
        self.boot_reader = boot_reader
        self._mutation_lock = threading.Lock()

    def _check_boot(self):
        if self.boot_reader() != self.boot_id:
            raise RuntimeError("System boot identity changed")

    @staticmethod
    def _validate(unit, token):
        if (not isinstance(token, str) or not OWNER_PATTERN.fullmatch(token) or
                not isinstance(unit, str) or not UNIT.fullmatch(unit) or
                unit != PREFIX + token.split(":", 1)[1] + ".service"):
            raise ValueError("Foreign or malformed Kervan unit")

    def list_units(self):
        self._check_boot()
        units = self.transport.list_units(PREFIX + "*.service")
        cgroups = self.transport.list_cgroups()
        if not isinstance(units, (list, tuple)) or any(
                not isinstance(unit, str) or not UNIT.fullmatch(unit)
                for unit in units) or len(units) != len(set(units)):
            raise RuntimeError("Incomplete or foreign systemd inventory")
        if not isinstance(cgroups, (list, tuple)) or any(
                not isinstance(unit, str) or not UNIT.fullmatch(unit)
                for unit in cgroups):
            raise RuntimeError("Incomplete or foreign Kervan cgroup inventory")
        if set(cgroups) - set(units):
            raise RuntimeError("Orphan Kervan cgroup without a systemd unit")
        live = []
        for unit in units:
            snapshot = self.snapshot(unit)
            if snapshot is not None and snapshot.state in ("reserved", "active"):
                live.append(unit)
        return tuple(live)

    def snapshot(self, unit):
        self._check_boot()
        if not isinstance(unit, str) or not UNIT.fullmatch(unit):
            raise ValueError("Foreign or malformed Kervan unit")
        props = self.transport.properties(unit)
        if props is None:
            if not self.transport.cgroup_empty("/kervan.slice/" + unit):
                raise RuntimeError("Unknown cgroup for missing unit")
            return None
        if not isinstance(props, dict):
            raise RuntimeError("Incomplete systemd unit properties")
        token = "kervan:" + unit[len(PREFIX):-len(".service")]
        expected_group = "/kervan.slice/" + unit
        command = props.get("ExecStart")
        if (props.get("Id") != unit or props.get("Names") != [unit] or
                props.get("FragmentPath") != TEMPLATE or
                props.get("Description") != "Kervan NFQUEUE gate " + token or
                props.get("LoadState") != "loaded" or
                props.get("DropInPaths") != [] or
                props.get("SourcePath") != "" or
                props.get("NeedDaemonReload") is not False or
                not isinstance(command, list) or len(command) != 1 or
                not isinstance(command[0], list) or len(command[0]) < 3 or
                command[0][:3] != ["/usr/libexec/kervan-dpi-gate",
                                  ["/usr/libexec/kervan-dpi-gate",
                                   unit[len(PREFIX):-len(".service")]], False]):
            raise RuntimeError("Foreign systemd unit collision")
        gate = self.transport.gate_state(unit)
        active = props.get("ActiveState")
        if gate not in ("waiting", "activated", "gone"):
            raise RuntimeError("Unknown gate state")
        if (active == "active" and props.get("ControlGroup") != expected_group or
                active in ("inactive", "failed") and
                props.get("ControlGroup") not in (expected_group, "")):
            raise RuntimeError("Foreign systemd cgroup path")
        if active == "active" and gate == "waiting":
            if self.transport.cgroup_empty(expected_group):
                raise RuntimeError("Gate cgroup has no tasks")
            state, reaped = "reserved", False
        elif active == "active" and gate == "activated":
            if self.transport.cgroup_empty(expected_group):
                raise RuntimeError("Engine cgroup has no tasks")
            state, reaped = "active", False
        elif active in ("inactive", "failed") and gate == "gone":
            if not self.transport.cgroup_empty(expected_group):
                raise RuntimeError("Exited unit retains cgroup tasks")
            state, reaped = "exited", True
        else:
            raise RuntimeError("Inconsistent systemd and gate state")
        return SupervisorSnapshot(token, self.boot_id, unit, expected_group,
                                  state, reaped)

    def _wait_job(self, path, deadline):
        if not isinstance(path, str) or not path.startswith(
                "/org/freedesktop/systemd1/job/"):
            raise RuntimeError("Invalid systemd job path")
        while True:
            result = self.transport.job_state(path)
            if result == "done":
                if self.clock() >= deadline:
                    raise TimeoutError("Systemd job exceeded deadline")
                return
            if result not in ("queued", "running"):
                raise RuntimeError("Systemd job failed or disappeared")
            if self.clock() >= deadline:
                raise TimeoutError("Systemd job timed out")
            self.pause(min(0.02, max(0, deadline - self.clock())))

    def _wait_reserved(self, unit, deadline):
        while True:
            try:
                snapshot = self.snapshot(unit)
            except RuntimeError as exc:
                if str(exc) != "Inconsistent systemd and gate state":
                    raise
                snapshot = None
            if snapshot is not None and snapshot.state == "reserved":
                if self.clock() >= deadline:
                    raise TimeoutError("Gate reached barrier after deadline")
                return
            if self.clock() >= deadline:
                raise TimeoutError("Gate did not reach pre-exec barrier")
            self.pause(min(0.02, max(0, deadline - self.clock())))

    def reserve(self, unit, token, timeout):
        self._validate(unit, token)
        if not 0 < timeout <= 10:
            raise ValueError("Invalid reservation timeout")
        if not self._mutation_lock.acquire(timeout=timeout):
            raise TimeoutError("Concurrent supervisor operation timed out")
        try:
            deadline = self.clock() + timeout
            if self.snapshot(unit) is not None:
                raise RuntimeError("Gate unit already exists")
            self._wait_job(self.transport.start_unit(unit), deadline)
            self._wait_reserved(unit, deadline)
        finally:
            self._mutation_lock.release()

    def activate(self, unit, token, argv, descriptors, timeout):
        self._validate(unit, token)
        if not 0 < timeout <= 10:
            raise ValueError("Invalid activation timeout")
        if not self._mutation_lock.acquire(timeout=timeout):
            raise TimeoutError("Concurrent supervisor operation timed out")
        try:
            deadline = self.clock() + timeout
            before = self.snapshot(unit)
            if before is None or before.state != "reserved":
                raise RuntimeError("Gate reservation cannot be proven")
            remaining = deadline - self.clock()
            if remaining <= 0:
                raise TimeoutError("Gate activation timed out")
            self.transport.gate_activate(unit, token, argv, descriptors, remaining)
            after = self.snapshot(unit)
            if self.clock() >= deadline:
                raise TimeoutError("Engine activation exceeded deadline")
            if after is None or after.state != "active":
                raise RuntimeError("Engine activation not verified")
        finally:
            self._mutation_lock.release()

    def stop_cgroup(self, unit, token, timeout):
        self._validate(unit, token)
        if not 0 < timeout <= 10:
            raise ValueError("Invalid stop timeout")
        if not self._mutation_lock.acquire(timeout=timeout):
            raise TimeoutError("Concurrent supervisor operation timed out")
        try:
            deadline = self.clock() + timeout
            before = self.snapshot(unit)
            if before is None or before.token != token:
                raise RuntimeError("Stop ownership cannot be proven")
            if before.state in ("reserved", "active"):
                self._wait_job(self.transport.stop_unit(unit), deadline)
            after = self.snapshot(unit)
            if after is None:
                if not self.transport.cgroup_empty("/kervan.slice/" + unit):
                    raise RuntimeError("Unloaded unit retains cgroup tasks")
            elif after.state != "exited" or not after.reaped:
                raise TimeoutError("Entire unit cgroup was not reaped")
            if self.clock() >= deadline:
                raise TimeoutError("Cgroup cleanup exceeded stop deadline")
        finally:
            self._mutation_lock.release()
