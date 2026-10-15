"""Explicit, offline preparation for a future Windows config-directory rename.

The running application does not call this module. Its legacy config path stays
active until a Windows-native upgrade and rollback procedure is approved.
"""

import json
import os
import stat
import tempfile
import time
from pathlib import Path


class MigrationError(Exception):
    """Migration stopped without replacing either user's configuration."""


def _check_directory(path):
    for item in (path, *path.parents):
        try:
            info = item.lstat()
        except FileNotFoundError:
            continue
        if (not stat.S_ISDIR(info.st_mode) or
                getattr(info, "st_file_attributes", 0) &
                getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)):
            raise MigrationError(f"Refusing linked or non-directory path: {item}")


def _check_file(path):
    # Publication uses a same-directory hard link, then unlinks its temporary
    # name. A second instance may briefly observe two links during that window.
    for attempt in range(10):
        try:
            info = path.lstat()
        except FileNotFoundError:
            return False
        if info.st_nlink == 1 or attempt == 9:
            break
        time.sleep(0.01)
    if (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or
            getattr(info, "st_file_attributes", 0) &
            getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)):
        raise MigrationError(f"Refusing linked or non-regular file: {path}")
    return True


def _stage_bytes(directory, content):
    descriptor, temporary = tempfile.mkstemp(prefix=".kervan-config-", dir=directory)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
    except Exception:
        Path(temporary).unlink(missing_ok=True)
        raise
    return Path(temporary)


def prepare_config_copy(legacy_file: Path, target_file: Path) -> str:
    """Copy valid JSON to a new location, retaining the old file and a backup.

    Returns ``copied``, ``already_copied`` or ``coexisting``. The target is
    never merged or overwritten, including when another process creates it.
    Paths must be explicit absolute ``config.json`` paths. This function has
    no platform-dependent defaults and is never invoked at application start.
    """
    legacy_file, target_file = Path(legacy_file), Path(target_file)
    if (not legacy_file.is_absolute() or not target_file.is_absolute() or
            ".." in legacy_file.parts or ".." in target_file.parts or
            legacy_file.name != "config.json" or target_file.name != "config.json" or
            legacy_file == target_file):
        raise MigrationError("Expected distinct absolute config.json paths")
    _check_directory(legacy_file.parent)
    _check_directory(target_file.parent)
    if not _check_file(legacy_file):
        raise MigrationError(f"Legacy configuration is missing: {legacy_file}")
    target_exists = _check_file(target_file)
    try:
        original = legacy_file.read_bytes()
        if not isinstance(json.loads(original.decode("utf-8")), dict):
            raise MigrationError("Legacy configuration must contain a JSON object")
        if target_exists:
            return ("already_copied" if target_file.read_bytes() == original
                    else "coexisting")
        target_file.parent.mkdir(parents=True, exist_ok=True)
        _check_directory(target_file.parent)
        backup = target_file.with_name("config.json.legacy-backup")
        backup_exists = _check_file(backup)
        if backup_exists:
            if backup.read_bytes() != original:
                raise MigrationError("Existing backup differs from legacy configuration")
        else:
            backup_temporary = _stage_bytes(target_file.parent, original)
            try:
                try:
                    # Publish the fully written backup in one operation.
                    os.link(backup_temporary, backup)
                except FileExistsError:
                    if not _check_file(backup) or backup.read_bytes() != original:
                        raise MigrationError("Concurrent backup differs from legacy configuration")
            finally:
                backup_temporary.unlink(missing_ok=True)
        temporary = _stage_bytes(target_file.parent, original)
        try:
            # Same-directory hard link creates the target atomically and fails
            # if another process created it; os.replace would erase that file.
            os.link(temporary, target_file)
        except FileExistsError:
            _check_file(target_file)
            return ("already_copied" if target_file.read_bytes() == original
                    else "coexisting")
        finally:
            Path(temporary).unlink(missing_ok=True)
        return "copied"
    except (OSError, UnicodeError, ValueError) as exc:
        raise MigrationError(f"Config copy failed: {exc}") from exc
