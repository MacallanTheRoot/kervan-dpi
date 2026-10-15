"""Injectable child-launch contract; no default executable process factory."""

import subprocess
from dataclasses import dataclass

from .zapret2 import QUEUE
from .zapret2_nft_plan import OWNER_PATTERN


@dataclass(frozen=True)
class SupervisorSnapshot:
    """Evidence returned by a separately trusted, persistent supervisor."""

    token: str
    boot_id: str
    unit: str
    cgroup: str
    state: str  # reserved, active, exited, absent, or unknown
    reaped: bool


class ReservedProcessPort:
    """Stable ownership contract for an injected systemd/cgroup manager.

    The manager starts only a packaged gate in its unit cgroup. The gate must
    block engine exec until activate transfers verified descriptors. No PID is
    an authority here. Native systemd behavior still needs isolated testing.
    """

    def __init__(self, manager, boot_id):
        self.manager = manager
        self.boot_id = boot_id

    @staticmethod
    def _unit(token):
        if not isinstance(token, str) or not OWNER_PATTERN.fullmatch(token):
            raise ValueError("Invalid supervisor token")
        return "kervan-nfqws2@" + token.split(":", 1)[1] + ".service"

    def _snapshot(self, token):
        unit = self._unit(token)
        snapshot = self.manager.snapshot(unit)
        if snapshot is None:
            return "absent"
        if (not isinstance(snapshot, SupervisorSnapshot) or snapshot.token != token or
                snapshot.unit != unit or snapshot.boot_id != self.boot_id or
                not isinstance(snapshot.cgroup, str) or
                snapshot.cgroup != "/kervan.slice/" + unit or snapshot.state not in
                {"reserved", "active", "exited", "absent"}):
            return "unknown"
        if snapshot.state in {"exited", "absent"} and not snapshot.reaped:
            return "unknown"
        return snapshot.state

    def inspect(self, token):
        state = self._snapshot(token)
        if state == "unknown":
            return "unknown"
        return "owned" if state in {"reserved", "active"} else "absent"

    def unclaimed_units(self, journal_token):
        """Fail closed if any Kervan unit is outside the durable journal."""
        units = self.manager.list_units()
        if not isinstance(units, (tuple, list)):
            raise RuntimeError("Incomplete supervisor inventory")
        expected = self._unit(journal_token) if journal_token is not None else None
        for unit in units:
            if not isinstance(unit, str) or unit != expected:
                return True
            if self._snapshot(journal_token) == "unknown":
                return True
        return False

    def reserve(self, token, timeout):
        self._unit(token)
        if not 0 < timeout <= 10 or self._snapshot(token) != "absent":
            raise RuntimeError("Supervisor reservation unavailable")
        self.manager.reserve(self._unit(token), token, timeout)
        if self._snapshot(token) != "reserved":
            raise RuntimeError("Inert supervisor reservation not verified")

    def activate(self, token, release, strategy, timeout):
        if not 0 < timeout <= 10 or self._snapshot(token) != "reserved":
            raise RuntimeError("Supervisor reservation is not verified")
        argv = release.argv(strategy, QUEUE)
        self.manager.activate(self._unit(token), token, argv,
                              tuple(release.descriptors.values()), timeout)
        if self._snapshot(token) != "active":
            raise RuntimeError("Supervisor activation not verified")

    def owns(self, token):
        return self._snapshot(token) == "active"

    def stop(self, token, timeout):
        state = self._snapshot(token)
        if state == "unknown" or not 0 < timeout <= 10:
            raise RuntimeError("Supervisor ownership cannot be proven")
        if state in {"reserved", "active"}:
            self.manager.stop_cgroup(self._unit(token), token, timeout)
        if self._snapshot(token) not in {"exited", "absent"}:
            raise TimeoutError("Supervised descendants were not reaped")


class BoundedLauncher:
    """A future helper may inject a supervised Popen factory and queue probe.

    The probe must enforce its timeout and bind readiness to this child. PID
    reuse and helper-restart ownership need a production pidfd/cgroup backend.
    """

    def __init__(self, popen_factory, readiness_probe):
        self.popen_factory = popen_factory
        self.readiness_probe = readiness_probe

    def launch(self, release, strategy, timeout):
        if not 0 < timeout <= 10:
            raise ValueError("Invalid startup timeout")
        argv = release.argv(strategy, QUEUE)
        descriptors = tuple(release.descriptors.values())
        process = self.popen_factory(
            argv, executable=argv[0], pass_fds=descriptors,
            env={"PATH": "/usr/bin:/bin", "LANG": "C"}, shell=False,
            close_fds=True, start_new_session=True, stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            if not self.readiness_probe(process, QUEUE, timeout):
                raise TimeoutError("Queue consumer did not become ready")
            if process.poll() is not None:
                raise RuntimeError("Consumer exited during startup")
            return process
        except BaseException:
            self.stop(process, timeout=min(timeout, 3))
            raise

    @staticmethod
    def owns(process):
        return process is not None and process.poll() is None

    @staticmethod
    def stop(process, timeout):
        if not 0 < timeout <= 10:
            raise ValueError("Invalid stop timeout")
        if process.poll() is not None:
            process.wait(timeout=timeout)
            return
        process.terminate()
        try:
            process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=timeout)
