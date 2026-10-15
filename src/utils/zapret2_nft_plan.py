"""Pure nftables ownership and transaction planning; never invokes nft."""

from dataclasses import dataclass
import re

from .zapret2 import QUEUE

FAMILY = "inet"
TABLE = "kervan_dpi"
CHAIN = "outgoing"
MARK = 0x40000000
OWNER_PATTERN = re.compile(r"kervan:[0-9a-f]{32}\Z")


@dataclass(frozen=True)
class Rule:
    family: str
    queue: int
    mark_guard: int
    owner: str
    bypass: bool = True
    protocol: str = "tcp"
    destination_port: int = 443
    original_packets: str = "1-12"


@dataclass(frozen=True)
class OwnedTable:
    family: str
    name: str
    chain: tuple
    rules: tuple[Rule, ...]


@dataclass(frozen=True)
class Inventory:
    """Complete snapshot supplied by a future privileged, read-only collector."""

    generation: int
    table: OwnedTable | None
    queue_claims: tuple[tuple[int, int, str], ...] = ()
    mark_claims: tuple[tuple[int, str], ...] = ()
    complete: bool = True


@dataclass(frozen=True)
class Transaction:
    expected_generation: int
    expected_table: OwnedTable | None
    commands: tuple[str, ...]
    expected_after: OwnedTable | None


class CollisionError(RuntimeError):
    pass


def expected_table(owner):
    if not isinstance(owner, str) or not OWNER_PATTERN.fullmatch(owner):
        raise ValueError("Invalid ownership identity")
    return OwnedTable(FAMILY, TABLE, (CHAIN, "filter", "postrouting", 101),
                      tuple(Rule(family, QUEUE, MARK, owner) for family in ("ipv4", "ipv6")))


def _check_inventory(inventory, owner, *, allowing_owned=False):
    if (not isinstance(inventory, Inventory) or inventory.complete is not True or
            not isinstance(inventory.generation, int) or
            isinstance(inventory.generation, bool) or inventory.generation < 0):
        raise CollisionError("Incomplete firewall inventory")
    wanted = expected_table(owner)
    if inventory.table is not None and (not allowing_owned or inventory.table != wanted):
        raise CollisionError("Table exists or ownership cannot be proven")
    for first, last, claimant in inventory.queue_claims:
        if (not isinstance(first, int) or not isinstance(last, int) or
                isinstance(first, bool) or isinstance(last, bool) or
                not 0 <= first <= last <= 65535 or not isinstance(claimant, str)):
            raise CollisionError("Invalid queue inventory")
        if first <= QUEUE <= last and claimant != owner:
            raise CollisionError("NFQUEUE number is claimed")
    for mask, claimant in inventory.mark_claims:
        if (not isinstance(mask, int) or isinstance(mask, bool) or
                not 0 <= mask <= 0xffffffff or not isinstance(claimant, str)):
            raise CollisionError("Invalid mark inventory")
        if mask & MARK and claimant != owner:
            raise CollisionError("Firewall mark overlaps")
    return wanted


def setup_plan(inventory, owner):
    wanted = _check_inventory(inventory, owner)
    # CREATE refuses an intervening same-name table/chain. It does not make
    # the preceding inventory read a kernel compare-and-swap operation.
    lines = [f"create table inet {TABLE}",
             f"create chain inet {TABLE} {CHAIN} {{ type filter hook postrouting priority 101; }}"]
    for family in ("ipv4", "ipv6"):
        lines.append(f"add rule inet {TABLE} {CHAIN} meta nfproto {family} "
                     f"meta mark and 0x{MARK:08x} == 0 tcp dport 443 "
                     f"ct original packets 1-12 queue num {QUEUE} bypass "
                     f'comment "{owner}"')
    return Transaction(inventory.generation, None, tuple(lines), wanted)


def teardown_plan(inventory, owner):
    wanted = _check_inventory(inventory, owner, allowing_owned=True)
    if inventory.table is None:
        return Transaction(inventory.generation, None, (), None)
    return Transaction(inventory.generation, wanted,
                       (f"delete table inet {TABLE}",), None)
