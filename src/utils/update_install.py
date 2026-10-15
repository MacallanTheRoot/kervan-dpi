"""Dormant Windows update verification and replacement primitives.

A production publisher key and native helper QA are required before the GUI may
call these primitives to perform an automatic update. No helper is launched here.
"""
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import shutil
import tempfile
import threading
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from metadata import EXECUTABLE_NAME
from utils.updates import REPOSITORY, Release, Version, safe_release_url

# Intentionally absent. The owner must pin a real publisher key through a
# reviewed release process. Test keys must never be copied into this value.
PRODUCTION_PUBLIC_KEY_HEX = ""
MAX_EXE_SIZE = 300 * 1024 * 1024
MAX_MANIFEST_SIZE = 16 * 1024
MAX_SIGNATURE_SIZE = 64
_ALLOWED_CDN = {"release-assets.githubusercontent.com"}
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def production_key_ready():
    return bool(re.fullmatch(r"[0-9a-fA-F]{64}", PRODUCTION_PUBLIC_KEY_HEX))


def automatic_install_ready():
    """Open only after a signed after-exit installer passes native Windows QA."""
    return False


def canonical_manifest(data):
    return (json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n").encode("ascii")


def _unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate manifest key")
        result[key] = value
    return result


def verify_manifest(payload, signature, public_key, expected_version):
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    if not isinstance(payload, bytes) or len(payload) > MAX_MANIFEST_SIZE:
        raise ValueError("Invalid manifest size")
    if not isinstance(signature, bytes) or len(signature) != MAX_SIGNATURE_SIZE:
        raise ValueError("Invalid manifest signature size")
    if not isinstance(public_key, bytes) or len(public_key) != 32:
        raise ValueError("Publisher key is not configured")
    try:
        Ed25519PublicKey.from_public_bytes(public_key).verify(signature, payload)
    except InvalidSignature as exc:
        raise ValueError("Invalid publisher signature") from exc
    try:
        data = json.loads(payload, object_pairs_hook=_unique_pairs)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("Malformed signed manifest") from exc
    if not isinstance(data, dict) or payload != canonical_manifest(data):
        raise ValueError("Noncanonical signed manifest")
    if set(data) != {"schema", "repository", "version", "asset", "size", "sha256"}:
        raise ValueError("Unexpected signed manifest fields")
    if type(data["schema"]) is not int or data["schema"] != 1 or data["repository"] != REPOSITORY:
        raise ValueError("Wrong manifest schema or repository")
    if data["version"] != Version.parse(expected_version).canonical:
        raise ValueError("Wrong manifest version")
    if data["asset"] != EXECUTABLE_NAME + ".exe":
        raise ValueError("Wrong executable asset")
    if type(data["size"]) is not int or not 0 < data["size"] <= MAX_EXE_SIZE:
        raise ValueError("Invalid executable size")
    if not isinstance(data["sha256"], str) or not _SHA256.fullmatch(data["sha256"]):
        raise ValueError("Invalid executable hash")
    return data


class _ReleaseRedirects(HTTPRedirectHandler):
    def __init__(self):
        self.count = 0

    def redirect_request(self, request, fp, code, msg, headers, newurl):
        self.count += 1
        parts = urlsplit(newurl)
        if (self.count > 3 or parts.scheme != "https" or parts.hostname not in _ALLOWED_CDN
                or parts.username or parts.password or parts.port):
            raise ValueError("Untrusted release download redirect")
        return super().redirect_request(request, fp, code, msg, headers, newurl)


def download_release_file(url, release, name, destination, limit, cancel=None):
    if not safe_release_url(url, release.tag, name):
        raise ValueError("Untrusted release asset URL")
    cancel = cancel or threading.Event()
    if cancel.is_set():
        raise InterruptedError("Update cancelled")
    opener = build_opener(_ReleaseRedirects())
    request = Request(url, headers={"User-Agent": "Kervan-DPI-updater"})
    total = 0
    digest = sha256()
    try:
        with opener.open(request, timeout=10) as response, open(destination, "xb") as output:
            if response.status != 200:
                raise OSError(f"Download returned HTTP {response.status}")
            while True:
                if cancel.is_set():
                    raise InterruptedError("Update cancelled")
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > limit:
                    raise ValueError("Release asset exceeds size limit")
                output.write(chunk)
                digest.update(chunk)
            output.flush()
            os.fsync(output.fileno())
    except Exception:
        Path(destination).unlink(missing_ok=True)
        raise
    return total, digest.hexdigest()


def prepare_update(release: Release, target, public_key, download=download_release_file,
                   cancel=None):
    """Stage a signed exact EXE beside the target; caller owns cleanup."""
    if not public_key or len(public_key) != 32:
        raise ValueError("Production publisher key is required")
    if cancel is not None and cancel.is_set():
        raise InterruptedError("Update cancelled")
    target = Path(target)
    if target.name != EXECUTABLE_NAME + ".exe" or target.is_symlink() or not target.is_file():
        raise ValueError("Target is not the running Kervan DPI executable")
    if release.asset_name != target.name or not release.manifest_url or not release.signature_url:
        raise ValueError("Signed standalone EXE assets are unavailable")
    manifest_name = f"Kervan-DPI-{release.version}-update-manifest.json"
    signature_name = manifest_name + ".sig"
    if (Version.parse(release.tag).canonical != release.version
            or not safe_release_url(release.notes_url, release.tag)
            or not safe_release_url(release.asset_url, release.tag, target.name)
            or not safe_release_url(release.manifest_url, release.tag, manifest_name)
            or not safe_release_url(release.signature_url, release.tag, signature_name)):
        raise ValueError("Untrusted signed release URL or version")
    stage = Path(tempfile.mkdtemp(prefix=".kervan-update-", dir=target.parent))
    try:
        manifest_path = stage / manifest_name
        signature_path = stage / signature_name
        exe_path = stage / target.name
        download(release.manifest_url, release, manifest_name, manifest_path, MAX_MANIFEST_SIZE, cancel)
        download(release.signature_url, release, signature_name, signature_path, MAX_SIGNATURE_SIZE, cancel)
        if cancel is not None and cancel.is_set():
            raise InterruptedError("Update cancelled")
        data = verify_manifest(manifest_path.read_bytes(), signature_path.read_bytes(),
                               public_key, release.version)
        size, digest = download(release.asset_url, release, target.name, exe_path, MAX_EXE_SIZE, cancel)
        if cancel is not None and cancel.is_set():
            raise InterruptedError("Update cancelled")
        if size != data["size"] or digest != data["sha256"]:
            raise ValueError("Downloaded EXE does not match signed manifest")
        with exe_path.open("rb") as stream:
            magic = stream.read(2)
        if magic != b"MZ":
            raise ValueError("Downloaded asset is not a Windows executable")
        return stage, exe_path
    except Exception:
        shutil.rmtree(stage)
        raise


class ReplaceOps:
    """Injectable filesystem and process boundary for after-exit replacement."""
    def exited(self):
        raise NotImplementedError

    def restart(self, executable):
        raise NotImplementedError

    def copy(self, source, destination):
        shutil.copy2(source, destination)

    def replace(self, source, destination):
        os.replace(source, destination)


def replace_after_exit(target, staged_exe, expected_sha256, ops):
    """Never call from the running EXE. Keep a rollback copy on success."""
    target, staged_exe = Path(target), Path(staged_exe)
    if (target.name != EXECUTABLE_NAME + ".exe" or target.is_symlink()
            or staged_exe.name != target.name or staged_exe.is_symlink()
            or staged_exe.parent.is_symlink() or not staged_exe.parent.name.startswith(".kervan-update-")
            or staged_exe.parent.parent.resolve() != target.parent.resolve() or not target.is_file()
            or not staged_exe.is_file()):
        raise ValueError("Unsafe update paths")
    if not isinstance(expected_sha256, str) or not _SHA256.fullmatch(expected_sha256):
        raise ValueError("Missing signed executable digest")
    digest = sha256()
    with staged_exe.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    if digest.hexdigest() != expected_sha256:
        raise ValueError("Staged executable changed after verification")
    if not ops.exited():
        raise RuntimeError("Application process is still running")
    backup_fd, backup_name = tempfile.mkstemp(prefix=".kervan-rollback-", suffix=".exe", dir=target.parent)
    os.close(backup_fd)
    backup = Path(backup_name)
    try:
        ops.copy(target, backup)
        ops.replace(staged_exe, target)
        if not ops.restart(target):
            raise RuntimeError("Updated application failed to restart")
        return backup
    except Exception:
        if backup.is_file() and backup.stat().st_size:
            ops.replace(backup, target)
        raise
