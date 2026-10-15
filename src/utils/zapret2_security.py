"""Uninstalled, offline model of the future privileged Zapret2 boundary.

Only injected ports can perform effects. This module contains no subprocess,
filesystem, netlink, polkit or service activation path.
"""

from dataclasses import dataclass
from threading import RLock

from .zapret2 import QUEUE, TABLE, parse_helper_request

FAMILY = "inet"
MARK = "0x40000000"
OWNER = "goodbyedpi-turkey:zapret2:tcp-v1"

# Review-only nft batch. The future executor must use nft's atomic batch API,
# collision checks and a root-owned, fixed template; GUI input cannot alter it.
TCP_BATCH = (f"add table {FAMILY} {TABLE}\n"
             f"add chain {FAMILY} {TABLE} post {{ type filter hook postrouting priority 101; }}\n"
             f"add rule {FAMILY} {TABLE} post meta mark and {MARK} == 0 "
             f"tcp dport 443 ct original packets 1-12 queue num {QUEUE} bypass "
             f'comment "{OWNER}"\n')


@dataclass(frozen=True)
class TableSnapshot:
    family: str
    name: str
    chains: tuple
    rules: tuple


EXPECTED_TABLE = TableSnapshot(FAMILY, TABLE,
                               (("post", "filter", "postrouting", 101),),
                               (("post", "tcp", 443, QUEUE, "bypass", MARK, OWNER),))


def owns_table(table):
    """Any extra or altered chain/rule makes deletion unsafe."""
    return table == EXPECTED_TABLE


class OfflineBackend:
    """Lifecycle specification using mock ports, deliberately not a live helper.

    firewall: snapshot() -> TableSnapshot|None, queue_owner(queue) -> token|None,
              install_atomic(fixed_batch), delete_exact(EXPECTED_TABLE)
    process:  start(strategy) -> token, owns(token), stop(token, timeout)
    A deployed helper must add authenticated IPC, durable journal and boot recovery.
    """

    def __init__(self, firewall, process):
        self.firewall = firewall
        self.process = process
        self._lock = RLock()
        self._token = None
        self._phase = "inactive"

    def request(self, payload, authorized=False):
        if not authorized:
            raise PermissionError("Privileged helper caller is not authenticated")
        operation = parse_helper_request(payload)
        with self._lock:
            return getattr(self, f"_{operation['operation']}")(operation.get("strategy"))

    def _preflight(self, _):
        table = self.firewall.snapshot()
        queue_owner = self.firewall.queue_owner(QUEUE)
        return {"ready": table is None and queue_owner is None and self._phase == "inactive",
                "table": "absent" if table is None else "owned" if owns_table(table) else "foreign",
                "queue": "free" if queue_owner is None else "occupied"}

    def _status(self, _):
        table = self.firewall.snapshot()
        table_owned = owns_table(table)
        process_owned = self._token is not None and self.process.owns(self._token)
        if self._phase == "running" and (not table_owned or not process_owned or
                                          self.firewall.queue_owner(QUEUE) != self._token):
            self._phase = "recovery_required"
        return {"phase": self._phase, "table_owned": table_owned,
                "process_owned": process_owned}

    def _start(self, strategy):
        if not self._preflight(None)["ready"]:
            raise RuntimeError("Duplicate start or resource collision")
        self._phase = "starting"
        try:
            self._token = self.process.start(strategy)
            if not self.process.owns(self._token) or self.firewall.queue_owner(QUEUE) != self._token:
                raise RuntimeError("Queue consumer ownership not verified")
            self.firewall.install_atomic(TCP_BATCH)
            if not owns_table(self.firewall.snapshot()):
                raise RuntimeError("Firewall ownership not verified")
            self._phase = "running"
            return self._status(None)
        except Exception as exc:
            try:
                self._cleanup()
            except Exception as rollback:
                self._phase = "recovery_required"
                raise RuntimeError(f"Start failed; rollback failed: {rollback}") from exc
            self._phase = "inactive"
            raise

    def _cleanup(self):
        table = self.firewall.snapshot()
        if table is not None:
            if not owns_table(table):
                raise RuntimeError("Foreign or altered table; refusing deletion")
            self.firewall.delete_exact(EXPECTED_TABLE)
            if self.firewall.snapshot() is not None:
                raise RuntimeError("Owned table deletion did not complete")
        if self._token is not None:
            if not self.process.owns(self._token):
                raise RuntimeError("Process identity changed; refusing termination")
            self.process.stop(self._token, timeout=3)
            if self.process.owns(self._token):
                raise TimeoutError("Owned process did not stop")
            self._token = None

    def _stop(self, _):
        if self._phase == "inactive" and self.firewall.snapshot() is None:
            return self._status(None)
        try:
            self._cleanup()
        except Exception:
            self._phase = "recovery_required"
            raise
        self._phase = "inactive"
        return self._status(None)

    def _recover(self, _):
        # A real helper must load a root-owned durable token before this step.
        return self._stop(None)
