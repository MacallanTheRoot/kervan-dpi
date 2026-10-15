"""Strict offline nft JSON inventory and guarded plan construction.

This module neither reads the host ruleset nor applies a transaction. A
generation passed by a collector is an observation, not a kernel CAS token.
Only the currently modelled JSON expression subset can prove ownership.
"""

from dataclasses import dataclass
import hashlib
import json

from .zapret2_nft_plan import (CHAIN, FAMILY, MARK, QUEUE, TABLE, CollisionError,
                               Inventory, Transaction, expected_table, setup_plan,
                               teardown_plan, OWNER_PATTERN)

MAX_JSON = 1_000_000
FAMILIES = frozenset(("inet", "ip", "ip6", "arp", "bridge", "netdev"))
STATEMENTS = frozenset(("match", "queue", "counter", "accept", "drop",
                        "return", "mangle", "jump", "goto", "log", "limit"))


class InventoryUncertain(CollisionError):
    """A snapshot cannot establish ownership or global collision freedom."""


@dataclass(frozen=True)
class TableRecord:
    family: str
    name: str
    handle: int


@dataclass(frozen=True)
class ChainRecord:
    family: str
    table: str
    name: str
    handle: int
    kind: str | None
    hook: str | None
    priority: int | None
    policy: str | None


@dataclass(frozen=True)
class RuleRecord:
    family: str
    table: str
    chain: str
    handle: int
    expression: tuple
    comment: str | None


@dataclass(frozen=True)
class NftSnapshot:
    generation: int
    tables: tuple[TableRecord, ...]
    chains: tuple[ChainRecord, ...]
    rules: tuple[RuleRecord, ...]
    queues: tuple[tuple[int, int, RuleRecord], ...]
    marks: tuple[RuleRecord, ...]

    def fingerprint(self):
        # A local equality witness only. This digest is not a kernel token.
        value = repr((self.tables, self.chains, self.rules,
                      self.queues, self.marks)).encode("utf-8")
        return hashlib.sha256(value).hexdigest()


@dataclass(frozen=True)
class GuardedPlan:
    action: str
    owner: str
    observed_generation: int
    observed_fingerprint: str
    transaction: Transaction


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise InventoryUncertain("Duplicate nft JSON key")
        result[key] = value
    return result


def _positive(value):
    if type(value) is not int or value <= 0:
        raise InventoryUncertain("Invalid nft object handle")
    return value


def _name(value):
    if not isinstance(value, str) or not value or len(value) > 255:
        raise InventoryUncertain("Invalid nft object name")
    return value


def _family(value):
    if not isinstance(value, str) or value not in FAMILIES:
        raise InventoryUncertain("Unknown nft family")
    return value


def _fields(value, required, optional=()):
    if not isinstance(value, dict) or not set(required) <= value.keys() or \
            set(value) - set(required) - set(optional):
        raise InventoryUncertain("Incomplete or unfamiliar nft object")


def _walk(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk(child)


def _claims(rule):
    queues = []
    marked = False
    for statement in rule.expression:
        if not isinstance(statement, dict) or len(statement) != 1 or \
                next(iter(statement)) not in STATEMENTS:
            raise InventoryUncertain("Unsupported nft rule statement")
        for node in _walk(statement):
            if "queue" in node:
                queue = node["queue"]
                _fields(queue, ("num",), ("flags",))
                number = queue["num"]
                if type(number) is int:
                    first = last = number
                elif isinstance(number, dict) and set(number) == {"range"} and \
                        isinstance(number["range"], list) and len(number["range"]) == 2:
                    first, last = number["range"]
                else:
                    raise InventoryUncertain("Dynamic nft queue allocation")
                if (type(first) is not int or type(last) is not int or
                        not 0 <= first <= last <= 65535):
                    raise InventoryUncertain("Invalid nft queue allocation")
                flags = queue.get("flags", [])
                if isinstance(flags, str):
                    flags = [flags]
                if (not isinstance(flags, list) or
                        any(not isinstance(flag, str) for flag in flags) or
                        len(flags) != len(set(flags)) or
                        set(flags) - {"bypass", "fanout"}):
                    raise InventoryUncertain("Unknown nft queue flags")
                queues.append((first, last, rule))
            for kind in ("meta", "ct"):
                if kind in node and isinstance(node[kind], dict) and \
                        node[kind].get("key") == "mark":
                    marked = True
    return queues, marked


def parse_nft_json(document, *, generation):
    """Parse a complete synthetic/captured `nft -j -a list ruleset` document.

    `generation` must be supplied separately by a trusted collector. JSON
    itself does not make the read and a later write conditionally atomic.
    """
    if type(generation) is not int or generation < 0:
        raise InventoryUncertain("Missing generation observation")
    if isinstance(document, (str, bytes)):
        if len(document) > MAX_JSON:
            raise InventoryUncertain("Oversized nft inventory")
        try:
            document = json.loads(document, object_pairs_hook=_pairs)
        except (ValueError, UnicodeError) as exc:
            raise InventoryUncertain("Malformed nft JSON") from exc
    _fields(document, ("nftables",))
    rows = document["nftables"]
    if not isinstance(rows, list) or not rows or len(rows) > 10000:
        raise InventoryUncertain("Incomplete nft ruleset")
    _fields(rows[0], ("metainfo",))
    _fields(rows[0]["metainfo"], ("version", "release_name", "json_schema_version"))
    if (not isinstance(rows[0]["metainfo"]["version"], str) or
            not rows[0]["metainfo"]["version"] or
            not isinstance(rows[0]["metainfo"]["release_name"], str) or
            rows[0]["metainfo"]["json_schema_version"] != 1 or
            type(rows[0]["metainfo"]["json_schema_version"]) is not int):
        raise InventoryUncertain("Invalid nft JSON schema metadata")
    tables, chains, rules = [], [], []
    table_keys, chain_keys, rule_keys = set(), set(), set()
    for row in rows[1:]:
        if not isinstance(row, dict) or len(row) != 1:
            raise InventoryUncertain("Unknown nft ruleset element")
        kind, value = next(iter(row.items()))
        if kind == "table":
            _fields(value, ("family", "name", "handle"), ("flags",))
            if value.get("flags", []) not in ([], None):
                raise InventoryUncertain("Unknown nft table flags")
            record = TableRecord(_family(value["family"]), _name(value["name"]),
                                 _positive(value["handle"]))
            key = (record.family, record.name)
            if key in table_keys:
                raise InventoryUncertain("Duplicate nft table")
            table_keys.add(key)
            tables.append(record)
        elif kind == "chain":
            _fields(value, ("family", "table", "name", "handle"),
                    ("type", "hook", "prio", "policy"))
            priority = value.get("prio")
            if priority is not None and type(priority) is not int:
                raise InventoryUncertain("Unknown nft chain priority")
            base_fields = (value.get("type"), value.get("hook"), priority,
                           value.get("policy"))
            if (any(item is not None for item in base_fields) and
                    (not all(item is not None for item in base_fields) or
                     not isinstance(base_fields[0], str) or
                     not isinstance(base_fields[1], str) or
                     base_fields[3] not in ("accept", "drop"))):
                raise InventoryUncertain("Incomplete nft base chain")
            record = ChainRecord(_family(value["family"]), _name(value["table"]),
                                 _name(value["name"]), _positive(value["handle"]),
                                 value.get("type"), value.get("hook"), priority,
                                 value.get("policy"))
            key = (record.family, record.table, record.name)
            if key in chain_keys:
                raise InventoryUncertain("Duplicate nft chain")
            chain_keys.add(key)
            chains.append(record)
        elif kind == "rule":
            _fields(value, ("family", "table", "chain", "handle", "expr"),
                    ("comment",))
            if not isinstance(value["expr"], list) or not value["expr"]:
                raise InventoryUncertain("Missing nft rule expression")
            comment = value.get("comment")
            if comment is not None and not isinstance(comment, str):
                raise InventoryUncertain("Invalid nft rule comment")
            record = RuleRecord(_family(value["family"]), _name(value["table"]),
                                _name(value["chain"]), _positive(value["handle"]),
                                tuple(value["expr"]), comment)
            key = (record.family, record.table, record.chain, record.handle)
            if key in rule_keys:
                raise InventoryUncertain("Duplicate nft rule handle")
            rule_keys.add(key)
            rules.append(record)
        else:
            # Sets, maps, flowtables and xt compatibility statements need
            # separate analysis before global collision freedom is claimed.
            raise InventoryUncertain("Unsupported nft ruleset element")
    if any((chain.family, chain.table) not in table_keys for chain in chains) or \
            any((rule.family, rule.table, rule.chain) not in chain_keys for rule in rules):
        raise InventoryUncertain("Dangling nft chain or rule")
    queues, marks = [], []
    for rule in rules:
        claims, marked = _claims(rule)
        queues.extend(claims)
        if marked:
            marks.append(rule)
    return NftSnapshot(generation, tuple(tables), tuple(chains), tuple(rules),
                       tuple(queues), tuple(marks))


def expected_expression(family):
    """Provisional nft JSON shape of the fixed CLI rule; native capture pending."""
    if family not in ("ipv4", "ipv6"):
        raise ValueError("Invalid packet family")
    return (
        {"match": {"op": "==", "left": {"meta": {"key": "nfproto"}}, "right": family}},
        {"match": {"op": "==", "left": {"binop": {
            "op": "&", "left": {"meta": {"key": "mark"}}, "right": MARK}},
            "right": 0}},
        {"match": {"op": "==", "left": {"payload": {
            "protocol": "tcp", "field": "dport"}}, "right": 443}},
        {"match": {"op": "==", "left": {"ct": {
            "key": "packets", "dir": "original"}}, "right": {"range": [1, 12]}}},
        {"queue": {"num": QUEUE, "flags": ["bypass"]}},
    )


def _owned(snapshot, owner):
    target = [table for table in snapshot.tables if
              (table.family, table.name) == (FAMILY, TABLE)]
    if not target:
        return False
    if len(target) != 1 or not OWNER_PATTERN.fullmatch(owner):
        raise CollisionError("Owned nft table identity is invalid")
    chains = [chain for chain in snapshot.chains if
              (chain.family, chain.table) == (FAMILY, TABLE)]
    rules = [rule for rule in snapshot.rules if
             (rule.family, rule.table) == (FAMILY, TABLE)]
    if (len(chains) != 1 or chains[0].name != CHAIN or
            (chains[0].kind, chains[0].hook, chains[0].priority,
             chains[0].policy) != ("filter", "postrouting", 101, "accept") or
            len(rules) != 2 or any(rule.chain != CHAIN or rule.comment != owner
                                   for rule in rules) or
            {json.dumps(rule.expression, sort_keys=True) for rule in rules} !=
            {json.dumps(expected_expression(family), sort_keys=True)
             for family in ("ipv4", "ipv6")}):
        raise CollisionError("Nft table ownership is not proven")
    return True


def _planner_inventory(snapshot, owner):
    if (not isinstance(snapshot, NftSnapshot) or not isinstance(owner, str) or
            not OWNER_PATTERN.fullmatch(owner)):
        raise CollisionError("Untrusted nft snapshot or owner")
    owned = _owned(snapshot, owner)
    if any(table.family == FAMILY and table.name == TABLE for table in snapshot.tables) \
            and not owned:
        raise CollisionError("Foreign nft table collision")
    owned_rules = {(rule.family, rule.table, rule.chain, rule.handle)
                   for rule in snapshot.rules if
                   (rule.family, rule.table) == (FAMILY, TABLE)} if owned else set()
    for first, last, rule in snapshot.queues:
        if first <= QUEUE <= last and (rule.family, rule.table, rule.chain,
                                      rule.handle) not in owned_rules:
            raise CollisionError("Foreign NFQUEUE allocation")
    if any((rule.family, rule.table, rule.chain, rule.handle) not in owned_rules
           for rule in snapshot.marks):
        # The offline parser cannot in general prove which mark bits a
        # foreign expression reads or writes; this is deliberately strict.
        raise InventoryUncertain("Foreign mark use may overlap")
    return Inventory(snapshot.generation,
                     expected_table(owner) if owned else None)


def build_setup(snapshot, owner):
    inventory = _planner_inventory(snapshot, owner)
    transaction = setup_plan(inventory, owner)
    return GuardedPlan("setup", owner, snapshot.generation,
                       snapshot.fingerprint(), transaction)


def build_teardown(snapshot, owner):
    inventory = _planner_inventory(snapshot, owner)
    transaction = teardown_plan(inventory, owner)
    return GuardedPlan("teardown", owner, snapshot.generation,
                       snapshot.fingerprint(), transaction)


def verify_before_submit(plan, fresh_snapshot):
    """Reject observable staleness; this is not a conditional kernel commit."""
    if not isinstance(plan, GuardedPlan) or not isinstance(fresh_snapshot, NftSnapshot):
        raise ValueError("Invalid guarded nft plan")
    if (fresh_snapshot.generation != plan.observed_generation or
            fresh_snapshot.fingerprint() != plan.observed_fingerprint):
        raise CollisionError("Nft inventory changed after planning")
    regenerated = (build_setup(fresh_snapshot, plan.owner) if plan.action == "setup"
                   else build_teardown(fresh_snapshot, plan.owner) if
                   plan.action == "teardown" else None)
    if regenerated != plan:
        raise CollisionError("Nft plan differs from fixed template")
    return plan.transaction


def verify_after_submit(plan, fresh_snapshot):
    """Accept observed final state only; unknown/partial outcomes need recovery."""
    if not isinstance(plan, GuardedPlan) or not isinstance(fresh_snapshot, NftSnapshot):
        raise ValueError("Invalid guarded nft plan")
    inventory = _planner_inventory(fresh_snapshot, plan.owner)
    if plan.action == "setup" and inventory.table != expected_table(plan.owner):
        raise CollisionError("Nft setup outcome is not owned")
    if plan.action == "teardown" and inventory.table is not None:
        raise CollisionError("Nft teardown outcome is incomplete")
    if plan.action not in ("setup", "teardown"):
        raise ValueError("Invalid nft action")
    return True
