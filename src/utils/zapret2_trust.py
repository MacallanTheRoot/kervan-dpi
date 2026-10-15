"""Offline model for opening a production, root-controlled Zapret2 release.

No installation is performed here.  The caller supplies independently approved
hashes; a user-owned build manifest is deliberately not accepted as authority.
"""

import hashlib
import ctypes
import fcntl
import json
import os
import stat
import uuid
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType

from .zapret2 import UPSTREAM_REVISION

ARTIFACTS = ("nfqws2", "zapret-lib.lua", "zapret-antidpi.lua")
PRODUCTION_CANDIDATE = Path("/usr/lib/kervan-dpi/candidate")
PRODUCTION_RELEASES = Path("/opt/kervan-dpi/releases")
RELEASE_OWNER_FILE = ".kervan-owner"
RELEASE_OWNER_CONTENT = b"kervan-dpi-transparent-helper:v1\n"
PINNED_SHA256 = MappingProxyType({
    "nfqws2": "7456a00056b70ffc5c42ff88dc3faa190db6faf08777f43c849d6264929c3f90",
    "zapret-lib.lua": "a33b5886603ee8181772798b2708e7ffa08da54cd2df39a965fac3abc5d3af9c",
    "zapret-antidpi.lua": "31c9dd75b0bd55e98e5306293f2be81e9d2ecadcbbf9157394ff37dcff7dc85a",
})


@dataclass(frozen=True)
class ReleasePolicy:
    revision: str
    hashes: dict[str, str]
    trusted_uid: int = 0

    def __post_init__(self):
        object.__setattr__(self, "hashes", MappingProxyType(dict(self.hashes)))

    def validate(self):
        if self.revision != UPSTREAM_REVISION or set(self.hashes) != set(ARTIFACTS):
            raise ValueError("Unapproved release policy")
        if any(not isinstance(value, str) or len(value) != 64 or
               any(char not in "0123456789abcdef" for char in value)
               for value in self.hashes.values()):
            raise ValueError("Invalid independent artifact digest")


PRODUCTION_POLICY = ReleasePolicy(UPSTREAM_REVISION, PINNED_SHA256)


def _unique_pairs(pairs):
    record = {}
    for key, value in pairs:
        if key in record:
            raise ValueError("Duplicate active release field")
        record[key] = value
    return record


class VerifiedRelease:
    """Holds verified file descriptors until an injected launcher consumes them."""

    def __init__(self, descriptors):
        self.descriptors = descriptors

    def close(self):
        for descriptor in self.descriptors.values():
            os.close(descriptor)
        self.descriptors = {}

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    def argv(self, strategy, queue):
        from .zapret2 import STRATEGIES, validate_strategy
        validate_strategy(strategy)
        if not isinstance(queue, int) or isinstance(queue, bool) or not 1 <= queue <= 65535:
            raise ValueError("Invalid queue")
        fd = self.descriptors
        if set(fd) != set(ARTIFACTS):
            raise RuntimeError("Verified descriptors are closed")
        return [f"/proc/self/fd/{fd['nfqws2']}", f"--qnum={queue}",
                f"--lua-init=@/proc/self/fd/{fd['zapret-lib.lua']}",
                f"--lua-init=@/proc/self/fd/{fd['zapret-antidpi.lua']}",
                *STRATEGIES[strategy]]


class InstalledArtifacts:
    """A fixed, separately approved release location for an injected helper."""

    def __init__(self, directory, policy, *, trust_boundary=Path("/")):
        self.directory = directory
        self.policy = policy
        self.trust_boundary = trust_boundary

    def open(self):
        return open_verified_release(self.directory, self.policy,
                                     trust_boundary=self.trust_boundary)

    def verify(self):
        with self.open():
            return True


def _trusted_directory(path, policy, boundary):
    """Traverse every ancestor through descriptors, including the boundary."""
    if not path.is_absolute() or not boundary.is_absolute() or path == boundary:
        raise ValueError("Expected a fixed absolute child path")
    parts = path.relative_to(boundary).parts
    if not parts or any(part in (".", "..") for part in parts):
        raise ValueError("Unsafe trusted path")
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
    fd = os.open(boundary, flags)
    try:
        for part in (None, *parts):
            if part is not None:
                child = os.open(part, flags, dir_fd=fd)
                os.close(fd)
                fd = child
            info = os.fstat(fd)
            if info.st_uid != policy.trusted_uid or info.st_mode & 0o022:
                raise PermissionError("Untrusted directory ancestor")
        return fd
    except BaseException:
        os.close(fd)
        raise


def _rename_noreplace(source, target, directory_fd):
    libc = ctypes.CDLL(None, use_errno=True)
    result = libc.renameat2(directory_fd, source.encode(), directory_fd,
                            target.encode(), 1)  # RENAME_NOREPLACE
    if result != 0:
        error = ctypes.get_errno()
        raise OSError(error, os.strerror(error), target)


def _verify_release_owner(directory_fd, policy):
    """Reject an unrelated or manually prepared /opt release directory."""
    fd = os.open(RELEASE_OWNER_FILE, os.O_RDONLY | os.O_NOFOLLOW |
                 os.O_CLOEXEC, dir_fd=directory_fd)
    try:
        info = os.fstat(fd)
        if (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or
                info.st_uid != policy.trusted_uid or
                stat.S_IMODE(info.st_mode) != 0o600 or
                info.st_size != len(RELEASE_OWNER_CONTENT) or
                os.read(fd, len(RELEASE_OWNER_CONTENT) + 1) != RELEASE_OWNER_CONTENT):
            raise PermissionError("Untrusted release directory ownership marker")
    finally:
        os.close(fd)


class ReleaseInstaller:
    """Publish one independently approved version from fixed trusted paths.

    root/policy overrides are fixture-only; production always uses / and the
    compiled reviewed policy. A package manager must prepare the candidate.
    """

    def __init__(self, *, root=Path("/"), policy=PRODUCTION_POLICY):
        self.root = Path(root)
        self.policy = policy
        if not self.root.is_absolute() or (self.root == Path("/") and
                                            policy is not PRODUCTION_POLICY):
            raise ValueError("Production policy cannot be injected")
        policy.validate()

    def _path(self, production_path):
        return self.root / production_path.relative_to("/")

    def publish(self, version):
        if type(version) is not int or version < 1 or version > 2**31 - 1:
            raise ValueError("Invalid monotonic release version")
        candidate = self._path(PRODUCTION_CANDIDATE)
        releases = self._path(PRODUCTION_RELEASES)
        with open_verified_release(candidate, self.policy,
                                   trust_boundary=self.root) as source:
            parent = _trusted_directory(releases, self.policy, self.root)
            try:
                _verify_release_owner(parent, self.policy)
                lock = os.open(".install.lock", os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW |
                               os.O_CLOEXEC, 0o600, dir_fd=parent)
                try:
                    info = os.fstat(lock)
                    if (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or
                            info.st_uid != self.policy.trusted_uid or
                            stat.S_IMODE(info.st_mode) != 0o600):
                        raise PermissionError("Untrusted installer lock")
                    try:
                        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    except BlockingIOError as exc:
                        raise TimeoutError("Concurrent release installation refused") from exc
                    self._publish_locked(parent, source, version)
                finally:
                    os.close(lock)
            finally:
                os.close(parent)
        return InstalledArtifacts(releases / f"v{version}", self.policy,
                                  trust_boundary=self.root)

    def current(self):
        releases = self._path(PRODUCTION_RELEASES)
        parent = _trusted_directory(releases, self.policy, self.root)
        try:
            _verify_release_owner(parent, self.policy)
            version = self._read_active(parent)
        finally:
            os.close(parent)
        if version is None:
            raise FileNotFoundError("No active trusted release")
        artifacts = InstalledArtifacts(releases / f"v{version}", self.policy,
                                       trust_boundary=self.root)
        artifacts.verify()
        return artifacts

    def rollback(self, version):
        """Explicitly select an older, still verified release; never delete data."""
        if type(version) is not int or not 1 <= version <= 2**31 - 1:
            raise ValueError("Invalid rollback version")
        releases = self._path(PRODUCTION_RELEASES)
        parent = _trusted_directory(releases, self.policy, self.root)
        try:
            _verify_release_owner(parent, self.policy)
            lock = os.open(".install.lock", os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW |
                           os.O_CLOEXEC, 0o600, dir_fd=parent)
            try:
                info = os.fstat(lock)
                if (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or
                        info.st_uid != self.policy.trusted_uid or
                        stat.S_IMODE(info.st_mode) != 0o600):
                    raise PermissionError("Untrusted installer lock")
                try:
                    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                except BlockingIOError as exc:
                    raise TimeoutError("Concurrent release installation refused") from exc
                active = self._read_active(parent)
                if active is None or version >= active:
                    raise ValueError("Rollback requires an older active release")
                for candidate in (active, version):
                    with open_verified_release(releases / f"v{candidate}", self.policy,
                                               trust_boundary=self.root):
                        pass
                self._set_active(parent, version)
            finally:
                os.close(lock)
        finally:
            os.close(parent)
        return InstalledArtifacts(releases / f"v{version}", self.policy,
                                  trust_boundary=self.root)

    def _set_active(self, parent, version):
        payload = json.dumps({"version": version, "revision": self.policy.revision},
                             sort_keys=True, separators=(",", ":")).encode("ascii")
        temporary = ".active-" + uuid.uuid4().hex
        fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL |
                     os.O_NOFOLLOW | os.O_CLOEXEC, 0o600, dir_fd=parent)
        try:
            try:
                view = memoryview(payload)
                while view:
                    view = view[os.write(fd, view):]
                os.fsync(fd)
            finally:
                os.close(fd)
            os.replace(temporary, "active.json", src_dir_fd=parent,
                       dst_dir_fd=parent)
            os.fsync(parent)
        finally:
            try:
                os.unlink(temporary, dir_fd=parent)
            except FileNotFoundError:
                pass

    def _read_active(self, parent):
        try:
            fd = os.open("active.json", os.O_RDONLY | os.O_NOFOLLOW |
                         os.O_CLOEXEC, dir_fd=parent)
        except FileNotFoundError:
            return None
        try:
            info = os.fstat(fd)
            if (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or
                    info.st_uid != self.policy.trusted_uid or
                    stat.S_IMODE(info.st_mode) != 0o600 or info.st_size > 256):
                raise PermissionError("Untrusted active release record")
            record = json.loads(os.read(fd, 257), object_pairs_hook=_unique_pairs)
            if (not isinstance(record, dict) or
                    set(record) != {"version", "revision"} or
                    type(record["version"]) is not int or
                    not 1 <= record["version"] <= 2**31 - 1 or
                    record["revision"] != self.policy.revision):
                raise ValueError("Corrupt active release record")
            return record["version"]
        finally:
            os.close(fd)

    def _publish_locked(self, parent, source, version):
        active = self._read_active(parent)
        if active is not None:
            if version <= active:
                raise ValueError("Automatic downgrade or duplicate activation refused")
            with open_verified_release(self._path(PRODUCTION_RELEASES) / f"v{active}",
                                       self.policy, trust_boundary=self.root):
                pass
        name = f"v{version}"
        stage = ".stage-" + uuid.uuid4().hex
        os.mkdir(stage, 0o700, dir_fd=parent)
        stage_fd = os.open(stage, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                           dir_fd=parent)
        published = False
        try:
            for artifact in ARTIFACTS:
                fd = os.open(artifact, os.O_WRONLY | os.O_CREAT | os.O_EXCL |
                             os.O_NOFOLLOW | os.O_CLOEXEC,
                             0o700 if artifact == "nfqws2" else 0o600,
                             dir_fd=stage_fd)
                try:
                    os.lseek(source.descriptors[artifact], 0, os.SEEK_SET)
                    while chunk := os.read(source.descriptors[artifact], 1024 * 1024):
                        view = memoryview(chunk)
                        while view:
                            view = view[os.write(fd, view):]
                    os.fchmod(fd, 0o755 if artifact == "nfqws2" else 0o644)
                    os.fsync(fd)
                finally:
                    os.close(fd)
            os.fchmod(stage_fd, 0o755)
            os.fsync(stage_fd)
            with open_verified_release(self._path(PRODUCTION_RELEASES) / stage,
                                       self.policy, trust_boundary=self.root):
                pass
            _rename_noreplace(stage, name, parent)
            published = True
            os.fsync(parent)
            self._set_active(parent, version)
        finally:
            os.close(stage_fd)
            if not published:
                for artifact in ARTIFACTS:
                    try:
                        os.unlink(f"{stage}/{artifact}", dir_fd=parent)
                    except FileNotFoundError:
                        pass
                os.rmdir(stage, dir_fd=parent)


def open_verified_release(directory, policy, *, trust_boundary=Path("/")):
    """Open every component with O_NOFOLLOW and verify inode, mode and digest.

    trust_boundary is only for disposable non-root fixtures. Production uses /.
    The release layout is flat; executable and Lua names are fixed.
    """
    policy.validate()
    directory = Path(directory)
    boundary = Path(trust_boundary)
    if not directory.is_absolute() or not boundary.is_absolute() or directory == boundary:
        raise ValueError("Release requires an absolute child directory")
    try:
        parts = directory.relative_to(boundary).parts
    except ValueError as exc:
        raise ValueError("Release escapes trusted boundary") from exc
    if any(part in ("", ".", "..") for part in parts):
        raise ValueError("Unsafe release path")
    directory_flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
    current = os.open(boundary, directory_flags)
    descriptors = {}
    try:
        for part in (None, *parts):
            if part is not None:
                child = os.open(part, directory_flags, dir_fd=current)
                os.close(current)
                current = child
            info = os.fstat(current)
            if info.st_uid != policy.trusted_uid or info.st_mode & 0o022:
                raise PermissionError("Untrusted release directory ownership or mode")
        if set(os.listdir(current)) != set(ARTIFACTS):
            raise ValueError("Release contains missing or unexpected artifacts")
        for name in ARTIFACTS:
            fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=current)
            descriptors[name] = fd
            info = os.fstat(fd)
            if (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or
                    info.st_uid != policy.trusted_uid or
                    stat.S_IMODE(info.st_mode) !=
                    (0o755 if name == "nfqws2" else 0o644)):
                raise PermissionError(f"Untrusted {name} inode")
            digest = hashlib.sha256()
            while chunk := os.read(fd, 1024 * 1024):
                digest.update(chunk)
            if digest.hexdigest() != policy.hashes[name]:
                raise ValueError(f"{name} digest mismatch")
            os.lseek(fd, 0, os.SEEK_SET)
        if os.read(descriptors["nfqws2"], 4) != b"\x7fELF":
            raise ValueError("nfqws2 is not ELF")
        os.lseek(descriptors["nfqws2"], 0, os.SEEK_SET)
        return VerifiedRelease(descriptors)
    except BaseException:
        for fd in descriptors.values():
            os.close(fd)
        raise
    finally:
        os.close(current)
