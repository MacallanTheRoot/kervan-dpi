"""Offline, GUI-independent watchdog decisions with no privileged effects.

An eventual root-owned monitor must collect every observation authoritatively
and use the service lock before asking the helper to reconcile. This module
does not start units, kill processes, change nftables or infer traffic health.
"""

from dataclasses import dataclass
import uuid

from .zapret2_helper import JournalEntry
from .zapret2_nft_plan import OWNER_PATTERN

HELPER_STATES = frozenset(("active", "inactive", "failed", "unknown"))
WORKER_STATES = frozenset(("owned", "absent", "unknown"))
CGROUP_STATES = frozenset(("owned", "empty", "unknown"))
NFT_STATES = frozenset(("owned", "absent", "foreign", "unknown"))
QUEUE_STATES = frozenset(("owned", "absent", "foreign", "unknown"))
PRESSURE_STATES = frozenset(("normal", "saturated", "unknown"))


@dataclass(frozen=True)
class WatchdogObservation:
    boot_id: str
    journal: JournalEntry | None
    journal_valid: bool
    helper_state: str
    worker_state: str
    worker_token: str | None
    cgroup_state: str
    cgroup_token: str | None
    nft_state: str
    nft_owner: str | None
    queue_state: str
    queue_token: str | None
    unclaimed_units: bool | None
    expected_generation: int | None
    observed_generation: int | None
    queue_pressure: str = "unknown"
    monitor_available: bool = True


@dataclass(frozen=True)
class WatchdogDecision:
    state: str
    next_step: str
    reason: str
    traffic_restored: str = "unverified"
    dpi_bypass_working: str = "unverified"


def _decision(state, next_step, reason):
    return WatchdogDecision(state, next_step, reason)


def assess(observation):
    """Classify a single complete observation; never perform cleanup.

    `request_helper_reconciliation` is a recommendation to a separately
    authorized root monitor, not an executable instruction or proof of safety.
    A running helper owns the lifetime lock; the monitor must not race it.
    """
    if not isinstance(observation, WatchdogObservation):
        raise TypeError("Watchdog observation required")
    value = observation
    if value.monitor_available is not True:
        return _decision("unavailable", "operator_review", "Independent monitor unavailable")
    if (value.helper_state not in HELPER_STATES or
            value.worker_state not in WORKER_STATES or
            value.cgroup_state not in CGROUP_STATES or
            value.nft_state not in NFT_STATES or
            value.queue_state not in QUEUE_STATES or
            value.queue_pressure not in PRESSURE_STATES):
        return _decision("blocked", "operator_review", "Malformed monitor observation")
    try:
        boot = str(uuid.UUID(value.boot_id))
    except (TypeError, ValueError, AttributeError):
        return _decision("blocked", "operator_review", "Boot identity is unknown")
    if boot != value.boot_id or value.journal_valid is not True:
        return _decision("blocked", "operator_review", "Journal or boot evidence is invalid")
    if value.unclaimed_units is not False:
        return _decision("blocked", "operator_review", "Unclaimed unit inventory")
    if (value.helper_state == "unknown" or value.worker_state == "unknown" or
            value.cgroup_state == "unknown" or
            value.nft_state in ("foreign", "unknown") or
            value.queue_state in ("foreign", "unknown")):
        return _decision("blocked", "operator_review", "Resource ownership is unknown")
    if ((value.worker_state == "owned") != (value.cgroup_state == "owned")):
        return _decision("blocked", "operator_review", "Worker and cgroup disagree")
    if ((value.worker_state == "absent" and value.worker_token is not None) or
            (value.cgroup_state == "empty" and value.cgroup_token is not None) or
            (value.nft_state == "absent" and value.nft_owner is not None)):
        return _decision("blocked", "operator_review", "Absent resource retains an identity")
    if value.queue_state == "owned" and value.worker_state != "owned":
        return _decision("blocked", "operator_review", "Queue listener lacks owned worker")
    if value.queue_pressure == "saturated" and value.queue_state != "owned":
        return _decision("blocked", "operator_review", "Queue pressure is inconsistent")
    if value.queue_pressure == "unknown" and value.queue_state == "owned":
        return _decision("blocked", "operator_review", "Queue pressure is unobserved")

    entry = value.journal
    if entry is None:
        if (value.worker_state != "absent" or value.nft_state != "absent" or
                value.queue_state != "absent" or value.queue_token is not None):
            return _decision("blocked", "operator_review", "Resources exist without journal")
        if value.helper_state == "active":
            return _decision("inactive", "none", "No owned resources")
        return _decision("degraded", "observe_systemd_restart", "Helper is unavailable")

    if (not isinstance(entry, JournalEntry) or
            not isinstance(entry.owner, str) or
            not OWNER_PATTERN.fullmatch(entry.owner) or
            entry.process_token != entry.owner or
            entry.phase not in ("starting", "running", "stopping") or
            not isinstance(entry.boot_id, str)):
        return _decision("blocked", "operator_review", "Journal ownership is invalid")
    if entry.boot_id != boot:
        return _decision("blocked", "operator_review", "Journal belongs to another boot")
    if (type(value.expected_generation) is not int or
            type(value.observed_generation) is not int or
            value.expected_generation < 0 or value.observed_generation < 0 or
            value.expected_generation != value.observed_generation):
        return _decision("blocked", "operator_review", "Generation evidence is missing or stale")
    if value.queue_state == "owned" and value.queue_token != entry.owner:
        return _decision("blocked", "operator_review", "Queue token differs from journal")
    if (value.worker_state == "owned" and value.worker_token != entry.owner or
            value.cgroup_state == "owned" and value.cgroup_token != entry.owner or
            value.nft_state == "owned" and value.nft_owner != entry.owner):
        return _decision("blocked", "operator_review", "Resource token differs from journal")
    if value.queue_state == "absent" and value.queue_token is not None:
        return _decision("blocked", "operator_review", "Queue observation is inconsistent")

    if value.queue_pressure == "saturated":
        return _decision("degraded", "operator_review", "Queue saturation needs native review")
    if (entry.phase == "running" and value.helper_state == "active" and
            value.worker_state == "owned" and value.nft_state == "owned" and
            value.queue_state == "owned"):
        return _decision("healthy", "none", "Owned control-plane resources observed")
    if value.helper_state == "active":
        return _decision("recovery_required", "observe_helper_recovery",
                         "Active helper owns reconciliation")
    return _decision("recovery_required", "request_helper_reconciliation",
                     "Helper restart must reconcile durable state")
