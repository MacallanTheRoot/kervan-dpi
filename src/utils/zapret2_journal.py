"""Durable, root-owned ownership journal for the privileged mechanism.

The caller must hold the service-wide lock while using this store.  The
directory is opened without following symlinks and every update is fsynced
before it is made visible.  No user-controlled path is accepted in a record.
"""

import json
import fcntl
import os
import stat
import time
import uuid
from dataclasses import replace
from pathlib import Path

from .zapret2_helper import JournalEntry
from .zapret2_nft_plan import OWNER_PATTERN

PHASES = frozenset(("starting", "running", "stopping"))
MAX_RECORD = 4096


def _unique_pairs(pairs):
    record = {}
    for key, value in pairs:
        if key in record:
            raise ValueError("Duplicate ownership journal field")
        record[key] = value
    return record


def boot_id():
    value = Path("/proc/sys/kernel/random/boot_id").read_text(encoding="ascii").strip()
    return str(uuid.UUID(value))


class DurableJournal:
    """Atomic journal; state_dir must be a precreated trusted directory."""

    def __init__(self, state_dir="/var/lib/kervan-dpi", *, trusted_uid=0,
                 current_boot_id=None, trust_boundary="/"):
        self.state_dir = Path(state_dir)
        boundary = Path(trust_boundary)
        if not self.state_dir.is_absolute() or not boundary.is_absolute():
            raise ValueError("Journal directory must be absolute")
        try:
            parts = self.state_dir.relative_to(boundary).parts
        except ValueError as exc:
            raise ValueError("Journal escapes trusted boundary") from exc
        if not parts or any(part in (".", "..") for part in parts):
            raise ValueError("Invalid journal directory")
        self.trusted_uid = trusted_uid
        self.boot = current_boot_id or boot_id()
        descriptor = os.open(boundary, os.O_RDONLY | os.O_DIRECTORY |
                             os.O_NOFOLLOW | os.O_CLOEXEC)
        try:
            base = os.fstat(descriptor)
            if base.st_uid != trusted_uid or base.st_mode & 0o022:
                raise PermissionError("Untrusted journal boundary")
            for part in parts:
                child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW |
                                os.O_CLOEXEC, dir_fd=descriptor)
                os.close(descriptor)
                descriptor = child
                info = os.fstat(descriptor)
                if info.st_uid != trusted_uid or info.st_mode & 0o022:
                    raise PermissionError("Untrusted journal directory ancestor")
            info = os.fstat(descriptor)
            if info.st_uid != trusted_uid or stat.S_IMODE(info.st_mode) != 0o700:
                raise PermissionError("Journal directory must be trusted and mode 0700")
            self._directory = descriptor
        except BaseException:
            os.close(descriptor)
            raise

    def close(self):
        if self._directory is not None:
            os.close(self._directory)
            self._directory = None

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    def _validate(self, record):
        if (not isinstance(record, dict) or set(record) !=
                {"owner", "phase", "process_token", "boot_id"} or
                not isinstance(record["owner"], str) or
                not OWNER_PATTERN.fullmatch(record["owner"]) or
                not isinstance(record["phase"], str) or
                record["phase"] not in PHASES or
                not isinstance(record["boot_id"], str) or
                not isinstance(record["process_token"], (str, type(None))) or
                (isinstance(record["process_token"], str) and
                 (not record["process_token"] or len(record["process_token"]) > 256))):
            raise ValueError("Invalid ownership journal")
        try:
            uuid.UUID(record["boot_id"])
        except (ValueError, AttributeError) as exc:
            raise ValueError("Invalid journal boot identity") from exc
        if record["phase"] == "running" and record["process_token"] is None:
            raise ValueError("Running journal lacks child identity")
        return JournalEntry(**record)

    def read(self):
        try:
            fd = os.open("journal.json", os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC,
                         dir_fd=self._directory)
        except FileNotFoundError:
            return None
        try:
            info = os.fstat(fd)
            if (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or
                    info.st_uid != self.trusted_uid or
                    stat.S_IMODE(info.st_mode) != 0o600 or info.st_size > MAX_RECORD):
                raise PermissionError("Untrusted journal inode")
            data = os.read(fd, MAX_RECORD + 1)
            if len(data) > MAX_RECORD:
                raise ValueError("Oversized journal")
            return self._validate(json.loads(data, object_pairs_hook=_unique_pairs))
        finally:
            os.close(fd)

    def write(self, entry):
        if not isinstance(entry, JournalEntry):
            raise TypeError("Expected JournalEntry")
        if entry.boot_id is not None and entry.boot_id != self.boot:
            raise ValueError("Cannot write a journal from another boot")
        entry = replace(entry, boot_id=self.boot)
        record = {"owner": entry.owner, "phase": entry.phase,
                  "process_token": entry.process_token, "boot_id": entry.boot_id}
        self._validate(record)
        self.read()  # Reject a substituted or malformed existing record.
        payload = json.dumps(record, sort_keys=True, separators=(",", ":")).encode("ascii")
        name = ".journal-" + uuid.uuid4().hex
        fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
                     0o600, dir_fd=self._directory)
        try:
            with os.fdopen(fd, "wb", closefd=False) as stream:
                stream.write(payload)
                stream.flush()
            os.fsync(fd)
            os.replace(name, "journal.json", src_dir_fd=self._directory,
                       dst_dir_fd=self._directory)
            os.fsync(self._directory)
        finally:
            os.close(fd)
            try:
                os.unlink(name, dir_fd=self._directory)
            except FileNotFoundError:
                pass

    def clear(self):
        # Refuse to remove a substituted or malformed record.
        if self.read() is None:
            return
        os.unlink("journal.json", dir_fd=self._directory)
        os.fsync(self._directory)


class ServiceLock:
    """Cross-process, lifetime lock on an inode that is never unlinked."""

    def __init__(self, journal, *, timeout=3):
        if not 0 < timeout <= 30:
            raise ValueError("Invalid lock timeout")
        self.journal = journal
        self.timeout = timeout
        self.fd = None

    def __enter__(self):
        fd = os.open("service.lock", os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW |
                     os.O_CLOEXEC, 0o600, dir_fd=self.journal._directory)
        try:
            info = os.fstat(fd)
            if (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or
                    info.st_uid != self.journal.trusted_uid or
                    stat.S_IMODE(info.st_mode) != 0o600):
                raise PermissionError("Untrusted service lock inode")
            deadline = time.monotonic() + self.timeout
            while True:
                try:
                    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except BlockingIOError:
                    if time.monotonic() >= deadline:
                        raise TimeoutError("Helper service is already running")
                    time.sleep(0.02)
            self.fd = fd
            return self
        except BaseException:
            os.close(fd)
            raise

    def __exit__(self, *_):
        fcntl.flock(self.fd, fcntl.LOCK_UN)
        os.close(self.fd)
        self.fd = None
