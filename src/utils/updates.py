"""Bounded, read-only GitHub release discovery; no downloaded code is executed."""
from dataclasses import dataclass
import json
import re
import threading
import time
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler

from metadata import VERSION

REPOSITORY = "MacallanTheRoot/GoodbyeDPI-Turkey-GUI"
API_URL = f"https://api.github.com/repos/{REPOSITORY}/releases?per_page=30"
RELEASE_ROOT = f"https://github.com/{REPOSITORY}/releases/"
CHECK_INTERVAL = 24 * 60 * 60
MAX_RESPONSE = 2 * 1024 * 1024
_VERSION = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)(?:[.-]?(a|b|rc)(\d+))?$", re.I)


@dataclass(frozen=True)
class Version:
    major: int
    minor: int
    patch: int
    kind: str = ""
    serial: int = 0

    @classmethod
    def parse(cls, value):
        if not isinstance(value, str):
            raise ValueError("Unsupported version")
        match = _VERSION.fullmatch(value)
        if not match:
            raise ValueError("Unsupported version")
        major, minor, patch, kind, serial = match.groups()
        return cls(int(major), int(minor), int(patch), (kind or "").lower(), int(serial or 0))

    @property
    def preview(self):
        return bool(self.kind)

    @property
    def canonical(self):
        return f"{self.major}.{self.minor}.{self.patch}" + (f"{self.kind}{self.serial}" if self.kind else "")

    def sort_key(self):
        return (self.major, self.minor, self.patch,
                {"a": 0, "b": 1, "rc": 2, "": 3}[self.kind], self.serial)

    def __lt__(self, other):
        return self.sort_key() < other.sort_key()


@dataclass(frozen=True)
class Release:
    version: str
    tag: str
    notes_url: str
    asset_url: str
    asset_name: str
    manifest_url: str = ""
    signature_url: str = ""


@dataclass(frozen=True)
class CheckResult:
    status: str
    release: Release | None = None
    message: str = ""
    retry_after: int | None = None


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        raise ValueError("Unexpected GitHub API redirect")


def safe_release_url(url, tag=None, asset=None):
    """Only exact repository release pages or their named release assets."""
    try:
        parts = urlsplit(url)
        if parts.scheme != "https" or parts.netloc != "github.com" or parts.query or parts.fragment:
            return False
        if tag is None:
            return bool(re.fullmatch(re.escape(f"/{REPOSITORY}/releases/tag/") + r"[A-Za-z0-9._-]+", parts.path))
        base = f"/{REPOSITORY}/releases/"
        if asset is None:
            return parts.path == base + "tag/" + quote(tag, safe="")
        return parts.path == base + "download/" + quote(tag, safe="") + "/" + quote(asset, safe="")
    except (TypeError, ValueError, AttributeError):
        return False


def _fetch_api(url, timeout):
    if url != API_URL:
        raise ValueError("Unexpected API URL")
    request = Request(url, headers={"Accept": "application/vnd.github+json",
                                    "User-Agent": "Kervan-DPI-update-checker"})
    opener = build_opener(_NoRedirect)
    try:
        with opener.open(request, timeout=timeout) as response:
            data = response.read(MAX_RESPONSE + 1)
            if len(data) > MAX_RESPONSE:
                raise ValueError("Release response too large")
            return response.status, dict(response.headers), data
    except HTTPError as exc:
        return exc.code, dict(exc.headers), b""


def _retry_seconds(headers, now):
    normalized = {str(k).lower(): str(v) for k, v in headers.items()}
    try:
        retry = int(normalized.get("retry-after", "0"))
        reset = int(normalized.get("x-ratelimit-reset", "0")) - int(now)
        return min(86400, max(0, retry, reset)) or None
    except ValueError:
        return None


class UpdateChecker:
    def __init__(self, fetch=_fetch_api, clock=time.time):
        self.fetch = fetch
        self.clock = clock

    def check(self, current=VERSION, cancel=None):
        current_version = Version.parse(current)
        cancel = cancel or threading.Event()
        for attempt in range(2):
            if cancel.is_set():
                return CheckResult("cancelled")
            try:
                status, headers, payload = self.fetch(API_URL, 5)
            except (OSError, URLError, TimeoutError) as exc:
                if attempt == 0 and not cancel.wait(0.4):
                    continue
                return CheckResult("offline", message="Cannot reach GitHub Releases")
            except ValueError:
                return CheckResult("error", message="Invalid release response")
            if status in (403, 429):
                return CheckResult("rate_limited", message="GitHub request limit reached",
                                   retry_after=_retry_seconds(headers, self.clock()))
            if status == 404:
                return CheckResult("error", message="Release endpoint unavailable")
            if status in (502, 503, 504) and attempt == 0 and not cancel.wait(0.4):
                continue
            if status != 200:
                return CheckResult("error", message=f"GitHub returned HTTP {status}")
            if len(payload) > MAX_RESPONSE:
                return CheckResult("error", message="Release response too large")
            try:
                releases = json.loads(payload)
                if not isinstance(releases, list):
                    raise ValueError("Expected a release list")
            except (ValueError, UnicodeDecodeError):
                return CheckResult("error", message="Malformed release response")
            if cancel.is_set():
                return CheckResult("cancelled")
            return self._select(releases, current_version)
        return CheckResult("error", message="Release service unavailable")

    @staticmethod
    def _select(releases, current):
        candidates = []
        for item in releases[:30]:
            if (not isinstance(item, dict) or item.get("draft") is not False
                    or type(item.get("prerelease")) is not bool
                    or not isinstance(item.get("published_at"), str)
                    or not item["published_at"]):
                continue
            try:
                version = Version.parse(item.get("tag_name"))
            except ValueError:
                continue
            if version.preview != (item.get("prerelease") is True):
                continue
            if version.preview:
                continue
            tag = item["tag_name"]
            notes = item.get("html_url")
            if not safe_release_url(notes, tag):
                continue
            candidates.append((version, tag, notes, item.get("assets")))
        if not candidates:
            return CheckResult("current")
        version, tag, notes, assets = max(candidates, key=lambda row: row[0].sort_key())
        if not current < version:
            return CheckResult("current")
        if not isinstance(assets, list):
            return CheckResult("unavailable", message="New release has no compatible Windows asset")
        expected = ("Kervan-DPI.exe", f"Kervan-DPI-{version.canonical}-windows-portable.zip")
        for name in expected:
            for asset in assets:
                if (isinstance(asset, dict) and asset.get("name") == name
                        and asset.get("state") == "uploaded"
                        and type(asset.get("size")) is int and 0 < asset["size"] <= 300 * 1024 * 1024
                        and safe_release_url(asset.get("browser_download_url"), tag, name)):
                    manifest_name = f"Kervan-DPI-{version.canonical}-update-manifest.json"
                    signature_name = manifest_name + ".sig"
                    urls = {}
                    for extra in assets:
                        if not isinstance(extra, dict):
                            continue
                        extra_name = extra.get("name")
                        extra_url = extra.get("browser_download_url")
                        if (extra_name in (manifest_name, signature_name)
                                and extra.get("state") == "uploaded"
                                and type(extra.get("size")) is int
                                and 0 < extra["size"] <= 65536
                                and safe_release_url(extra_url, tag, extra_name)):
                            urls[extra_name] = extra_url
                    return CheckResult("available", Release(
                        version.canonical, tag, notes, asset["browser_download_url"], name,
                        urls.get(manifest_name, ""), urls.get(signature_name, "")))
        return CheckResult("unavailable", message="New release has no compatible Windows asset")
