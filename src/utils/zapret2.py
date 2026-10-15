"""Offline Zapret2 research adapter. This module never changes the live network."""

import os
import hashlib
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


UPSTREAM_REVISION = "a1adf7b868e65c8a77aab608c8bbd9ec8b30a256"
TABLE = "goodbyedpi_turkey_exp"
QUEUE = 200
STRATEGIES = {
    "TLS split (research)": (
        "--filter-tcp=443", "--filter-l7=tls",
        "--payload=tls_client_hello",
        "--lua-desync=multisplit:pos=1:seqovl=5:seqovl_pattern=0x1603030000",
    ),
    "TLS fake + split (research)": (
        "--filter-tcp=443", "--filter-l7=tls",
        "--payload=tls_client_hello",
        "--lua-desync=fake:blob=fake_default_tls:tcp_md5:tls_mod=rnd,rndsni,dupsid",
        "--lua-desync=multisplit:pos=1:seqovl=5:seqovl_pattern=0x1603030000",
    ),
}
DEFAULT_STRATEGY = next(iter(STRATEGIES))


def validate_strategy(name):
    if not isinstance(name, str) or name not in STRATEGIES:
        raise ValueError("Unsupported Zapret2 strategy")
    return name


def validate_helper_request(operation, strategy=None):
    """Validate the entire narrow request before a future privileged boundary."""
    if operation not in ("preflight", "status", "start", "stop", "recover"):
        raise ValueError("Unsupported privileged operation")
    if operation == "start":
        validate_strategy(strategy)
    elif strategy is not None:
        raise ValueError("Strategy is only valid for start")
    return {"operation": operation, **({"strategy": strategy} if strategy else {})}


def parse_helper_request(payload):
    """Reject extra keys, nested commands and non-canonical JSON values."""
    if not isinstance(payload, dict) or set(payload) - {"operation", "strategy"}:
        raise ValueError("Unexpected helper request fields")
    operation = payload.get("operation")
    strategy = payload.get("strategy")
    if not isinstance(operation, str) or (strategy is not None and not isinstance(strategy, str)):
        raise ValueError("Invalid helper request types")
    if "strategy" in payload and strategy is None:
        raise ValueError("Null strategy is forbidden")
    return validate_helper_request(operation, strategy)


def verify_build_provenance(binary, lua_directory, manifest):
    """Offline integrity check; manifest must come from a separately trusted build."""
    if not isinstance(manifest, dict) or manifest.get("source_revision") != UPSTREAM_REVISION:
        raise ValueError("Source revision mismatch")
    if manifest.get("lua_abi") != "luajit-5.1":
        raise ValueError("Unsupported Lua ABI")
    expected = manifest.get("sha256")
    if not isinstance(expected, dict) or set(expected) != {"nfqws2", "zapret-lib.lua", "zapret-antidpi.lua"}:
        raise ValueError("Incomplete provenance hashes")
    files = {"nfqws2": Path(binary),
             "zapret-lib.lua": Path(lua_directory) / "zapret-lib.lua",
             "zapret-antidpi.lua": Path(lua_directory) / "zapret-antidpi.lua"}
    for name, path in files.items():
        if (path.is_symlink() or any(parent.is_symlink() for parent in path.parents)
                or not path.is_file() or not isinstance(expected[name], str)
                or len(expected[name]) != 64):
            raise ValueError(f"Missing or invalid {name} provenance")
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected[name]:
            raise ValueError(f"{name} checksum mismatch")
    with files["nfqws2"].open("rb") as stream:
        magic = stream.read(4)
    if magic != b"\x7fELF":
        raise ValueError("nfqws2 is not an ELF binary")
    return True


def verify_linkage(readelf_output, ldd_output):
    if "Machine:" not in readelf_output or "Advanced Micro Devices X86-64" not in readelf_output:
        raise ValueError("Unsupported ELF architecture")
    if "libluajit-5.1.so.2" not in readelf_output:
        raise ValueError("Unsupported Lua ABI")
    if "not found" in ldd_output:
        raise ValueError("Missing shared libraries")
    return True


@dataclass(frozen=True)
class Inspection:
    available: bool
    reason: str
    binary: str | None = None
    version: str = ""


class Zapret2Adapter:
    """Validate a pinned engine and prepare plans; activation is deliberately gated."""

    def __init__(self, binary=None, lua_directory=None, manifest=None):
        self.binary = binary
        self.lua_directory = lua_directory
        self.manifest = manifest

    def inspect(self):
        binary = self.binary or shutil.which("nfqws2")
        if not binary or not Path(binary).is_file() or not os.access(binary, os.X_OK):
            return Inspection(False, "nfqws2 is not installed; SpoofDPI remains available.")
        lua = Path(self.lua_directory) if self.lua_directory else None
        if lua is None or not all((lua / name).is_file() for name in
                                   ("zapret-lib.lua", "zapret-antidpi.lua")):
            return Inspection(False, "Matching Zapret2 Lua libraries are missing.", binary)
        if self.manifest is None:
            return Inspection(False, "nfqws2 build provenance is unverified.", binary)
        try:
            verify_build_provenance(binary, lua, self.manifest)
            elf = subprocess.run(["readelf", "-h", "-d", binary], capture_output=True,
                                 text=True, timeout=2, check=True)
            links = subprocess.run(["ldd", binary], capture_output=True,
                                   text=True, timeout=2, check=True)
            verify_linkage(elf.stdout, links.stdout)
        except (ValueError, OSError, subprocess.SubprocessError) as exc:
            return Inspection(False, f"nfqws2 provenance failed: {exc}", binary)
        try:
            result = subprocess.run([binary, "--version"], capture_output=True,
                                    text=True, timeout=2, check=False)
        except (OSError, subprocess.TimeoutExpired) as exc:
            return Inspection(False, f"Could not inspect nfqws2: {exc}", binary)
        version = (result.stdout + result.stderr).strip()
        if result.returncode != 0:
            return Inspection(False, "nfqws2 version probe failed.", binary, version)
        if self.manifest.get("version") != version:
            return Inspection(False, "nfqws2 provenance failed: Version information mismatch",
                              binary, version)
        return Inspection(False, "Privileged helper is not installed or approved.", binary, version)

    def command(self, strategy):
        """Return a fixed argv plan, never a shell string or runnable GUI action."""
        validate_strategy(strategy)
        if not self.binary or not self.lua_directory:
            raise ValueError("Verified nfqws2 binary and Lua directory are required")
        lua = Path(self.lua_directory)
        return [self.binary, f"--qnum={QUEUE}",
                f"--lua-init=@{lua / 'zapret-lib.lua'}",
                f"--lua-init=@{lua / 'zapret-antidpi.lua'}", *STRATEGIES[strategy]]

    def firewall_plan(self, strategy):
        """Return reviewable, fixed nft argv; no caller in the GUI executes this."""
        validate_strategy(strategy)
        return [
            ["nft", "add", "table", "inet", TABLE],
            ["nft", "add", "chain", "inet", TABLE, "post",
             "{ type filter hook postrouting priority 101; }"],
            ["nft", "add", "rule", "inet", TABLE, "post", "meta", "mark", "and",
             "0x40000000", "==", "0", "tcp", "dport", "443", "ct", "original",
             "packets", "1-12", "queue", "num", str(QUEUE), "bypass"],
        ]

    def start(self, strategy):
        validate_strategy(strategy)
        raise RuntimeError("Transparent activation awaits a reviewed privileged helper and native approval.")
