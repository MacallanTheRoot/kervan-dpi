"""Uninstalled privileged-helper contract and offline lifecycle coordinator.

All authority and effects are injected. There is no socket listener, polkit
policy, subprocess launcher, nft executor or root entry point in this module.
"""

from dataclasses import dataclass
from threading import RLock
import uuid

from .zapret2 import QUEUE, parse_helper_request
from .zapret2_nft_plan import (CollisionError, Inventory, expected_table,
                               setup_plan, teardown_plan)

PROCESS_TIMEOUT = 3
FIREWALL_TIMEOUT = 3


@dataclass(frozen=True)
class Peer:
    uid: int
    pid: int
    start_time: int
    credentials_verified: bool


@dataclass(frozen=True)
class JournalEntry:
    owner: str
    phase: str
    process_token: object = None
    boot_id: str | None = None


class RecoveryRequired(RuntimeError):
    pass


def _complete_inventory(inventory):
    return (isinstance(inventory, Inventory) and inventory.complete is True and
            type(inventory.generation) is int and inventory.generation >= 0)


class OfflineHelper:
    """Injected ports: authorizer(peer, operation), artifacts.verify(),
    journal.read/write/clear(), firewall.inventory/apply(tx, timeout)/queue_owner(),
    process.reserve/activate/inspect/stop on a trusted supervisor token.

    A production implementation must serialize across helper instances and
    persist journal records atomically under root ownership before effects.
    """

    def __init__(self, authorizer, artifacts, journal, firewall, process):
        self.authorizer = authorizer
        self.artifacts = artifacts
        self.journal = journal
        self.firewall = firewall
        self.process = process
        self._lock = RLock()

    def request(self, payload, peer):
        if (not isinstance(peer, Peer) or not peer.credentials_verified or peer.uid < 0 or
                peer.pid <= 0 or peer.start_time <= 0):
            raise PermissionError("Unverified local peer")
        operation = parse_helper_request(payload)
        if not self.authorizer(peer, operation["operation"]):
            raise PermissionError("Helper action denied")
        return self._dispatch_authorized(operation, peer)

    def _dispatch_authorized(self, operation, peer):
        """Dispatch a request authorized by the kernel-credential IPC boundary."""
        if (not isinstance(peer, Peer) or not peer.credentials_verified or peer.uid < 0 or
                peer.pid <= 0 or peer.start_time <= 0):
            raise PermissionError("Unverified local peer")
        operation = parse_helper_request(operation)
        with self._lock:
            action = operation["operation"]
            if action == "preflight":
                return self._preflight()
            if action == "status":
                return self._status()
            if action == "start":
                return self._start(operation["strategy"])
            if action == "stop":
                return self._recover()
            return self._recover()

    def _preflight(self):
        self.artifacts.verify()
        entry = self.journal.read()
        inventory = self.firewall.inventory()
        if (hasattr(self.process, "unclaimed_units") and
                self.process.unclaimed_units(entry.process_token if entry else None)):
            return {"ready": False, "reason": "unclaimed supervised unit"}
        if entry is not None:
            return {"ready": False, "reason": "existing ownership journal"}
        if inventory.table is not None:
            return {"ready": False, "reason": "table exists without journal"}
        try:
            setup_plan(inventory, "kervan:" + "0" * 32)
        except CollisionError as exc:
            return {"ready": False, "reason": str(exc)}
        if self.firewall.queue_owner(QUEUE) is not None:
            return {"ready": False, "reason": "queue listener collision"}
        return {"ready": True, "reason": "offline preflight passed"}

    def _status(self):
        entry = self.journal.read()
        inventory = self.firewall.inventory()
        if (hasattr(self.process, "unclaimed_units") and
                self.process.unclaimed_units(entry.process_token if entry else None)):
            return {"phase": "recovery_required"}
        if not _complete_inventory(inventory):
            return {"phase": "recovery_required"}
        if entry is None:
            return {"phase": "inactive" if inventory.table is None and
                    self.firewall.queue_owner(QUEUE) is None else "recovery_required"}
        if entry.phase != "running":
            return {"phase": "recovery_required"}
        try:
            teardown_plan(inventory, entry.owner)
        except (CollisionError, ValueError):
            return {"phase": "recovery_required"}
        if (inventory.table is None or
                inventory.table != expected_table(entry.owner) or
                not self.process.owns(entry.process_token) or
                self.firewall.queue_owner(QUEUE) != entry.process_token):
            return {"phase": "recovery_required"}
        return {"phase": "running"}

    def _start(self, strategy):
        if not self._preflight()["ready"]:
            raise RecoveryRequired("Preflight failed or resources already exist")
        owner = "kervan:" + uuid.uuid4().hex
        reserved = hasattr(self.process, "reserve")
        # A reserved supervisor identity is durable before any executable may run.
        token = owner if reserved else None
        entry = JournalEntry(owner, "starting", token)
        self.journal.write(entry)
        try:
            with self.artifacts.open() as release:
                if reserved:
                    self.process.reserve(token, timeout=PROCESS_TIMEOUT)
                    self.process.activate(token, release, strategy,
                                          timeout=PROCESS_TIMEOUT)
                else:
                    token = self.process.launch(release, strategy, timeout=PROCESS_TIMEOUT)
                    self.journal.write(JournalEntry(owner, "starting", token))
            if not self.process.owns(token) or self.firewall.queue_owner(QUEUE) != token:
                raise RecoveryRequired("Queue consumer identity was not proven")
            plan = setup_plan(self.firewall.inventory(), owner)
            self.firewall.apply(plan, timeout=FIREWALL_TIMEOUT)
            if self.firewall.inventory().table != plan.expected_after:
                raise RecoveryRequired("Installed table differs from owned plan")
            # The consumer can disappear while the firewall transaction runs.
            # Do not commit a running journal from the earlier ownership probe.
            if (not self.process.owns(token) or
                    self.firewall.queue_owner(QUEUE) != token):
                raise RecoveryRequired("Queue consumer identity was lost during setup")
            self.journal.write(JournalEntry(owner, "running", token))
            return {"phase": "running"}
        except Exception as exc:
            try:
                if reserved:
                    self._recover()
                else:
                    # Legacy mock path: a live object must be stopped if its
                    # token could not be committed to the journal.
                    if (token is not None and self.journal.read().process_token is None and
                            self.process.owns(token)):
                        self.process.stop(token, timeout=PROCESS_TIMEOUT)
                        if self.process.owns(token):
                            raise RecoveryRequired("Unjournaled child could not be stopped")
                    self._recover()
            except Exception as rollback:
                raise RecoveryRequired(f"Startup failed; rollback incomplete: {rollback}") from exc
            raise

    def _recover(self):
        entry = self.journal.read()
        inventory = self.firewall.inventory()
        if (hasattr(self.process, "unclaimed_units") and
                self.process.unclaimed_units(entry.process_token if entry else None)):
            raise RecoveryRequired("Unclaimed supervised unit blocks cleanup")
        if not _complete_inventory(inventory):
            raise RecoveryRequired("Firewall inventory is incomplete")
        if entry is None:
            if inventory.table is not None or self.firewall.queue_owner(QUEUE) is not None:
                raise RecoveryRequired("Resources exist without an ownership journal")
            return {"phase": "inactive"}
        if hasattr(self.process, "inspect") and entry.process_token is None:
            raise RecoveryRequired("Supervisor token is missing from journal")
        if (entry.boot_id is not None and hasattr(self.journal, "boot") and
                entry.boot_id != self.journal.boot):
            if inventory.table is not None or self.firewall.queue_owner(QUEUE) is not None:
                raise RecoveryRequired("Stale boot journal with active resources")
            if (entry.process_token is not None and hasattr(self.process, "inspect") and
                    self.process.inspect(entry.process_token) != "absent"):
                raise RecoveryRequired("Stale boot supervisor identity is uncertain")
            self.journal.clear()
            return {"phase": "inactive"}
        if self.firewall.queue_owner(QUEUE) not in (None, entry.process_token):
            raise RecoveryRequired("Queue ownership changed")
        if entry.process_token is not None and hasattr(self.process, "inspect"):
            if self.process.inspect(entry.process_token) == "unknown":
                raise RecoveryRequired("Supervisor ownership cannot be proven")
        try:
            plan = teardown_plan(inventory, entry.owner)
        except (CollisionError, ValueError) as exc:
            raise RecoveryRequired(str(exc)) from exc
        self.journal.write(JournalEntry(entry.owner, "stopping", entry.process_token))
        if plan.commands:
            self.firewall.apply(plan, timeout=FIREWALL_TIMEOUT)
            if self.firewall.inventory().table is not None:
                raise RecoveryRequired("Table removal was not verified")
        process_present = (self.process.inspect(entry.process_token) == "owned"
                           if entry.process_token is not None and
                           hasattr(self.process, "inspect") else
                           entry.process_token is not None and
                           self.process.owns(entry.process_token))
        if process_present:
            self.process.stop(entry.process_token, timeout=PROCESS_TIMEOUT)
            if hasattr(self.process, "inspect"):
                if self.process.inspect(entry.process_token) != "absent":
                    raise RecoveryRequired("Consumer exit and reap were not verified")
            elif self.process.owns(entry.process_token):
                raise RecoveryRequired("Consumer termination was not verified")
        if self.firewall.queue_owner(QUEUE) is not None:
            raise RecoveryRequired("Queue is still occupied")
        self.journal.clear()
        return {"phase": "inactive"}

    def watchdog_tick(self):
        """Internal, timer-driven recovery decision; no GUI authority required."""
        with self._lock:
            state = self._status()["phase"]
            if state == "running" or state == "inactive":
                return {"phase": state}
            return self._recover()
