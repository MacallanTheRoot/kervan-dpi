"""Disposable signing, staging and rollback tests; no Windows host changes."""
from hashlib import sha256
import importlib.util
import os
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest.mock import Mock
from urllib.request import Request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from utils.update_install import (PRODUCTION_PUBLIC_KEY_HEX, ReplaceOps, canonical_manifest,
                                  prepare_update, production_key_ready, replace_after_exit,
                                  verify_manifest, _ReleaseRedirects)
from utils.updates import Release

spec = importlib.util.spec_from_file_location("update_manifest_tool", ROOT / "tools/release/update_manifest.py")
manifest_tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(manifest_tool)


class FakeOps(ReplaceOps):
    def __init__(self, *, exited=True, restart=True, deny=False):
        self.exited_value = exited
        self.restart_value = restart
        self.deny = deny
        self.restarts = []

    def exited(self):
        return self.exited_value

    def restart(self, executable):
        self.restarts.append(executable)
        return self.restart_value

    def replace(self, source, destination):
        if self.deny and Path(source).parent.name.startswith(".kervan-update-"):
            raise PermissionError("replacement denied")
        super().replace(source, destination)


class InstallTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.exe = self.root / "Kervan-DPI.exe"
        self.exe.write_bytes(b"MZold")
        self.payload = b"MZnew tested fixture"
        self.key = Ed25519PrivateKey.generate()
        self.public = self.key.public_key().public_bytes(
            serialization.Encoding.Raw, serialization.PublicFormat.Raw)
        self.manifest = canonical_manifest({
            "schema": 1, "repository": "MacallanTheRoot/GoodbyeDPI-Turkey-GUI",
            "version": "1.0.2", "asset": "Kervan-DPI.exe", "size": len(self.payload),
            "sha256": sha256(self.payload).hexdigest()})
        self.signature = self.key.sign(self.manifest)
        base = "https://github.com/MacallanTheRoot/GoodbyeDPI-Turkey-GUI/releases/download/v1.0.2/"
        self.release = Release("1.0.2", "v1.0.2", base.replace("download/v1.0.2/", "tag/v1.0.2"),
                               base + "Kervan-DPI.exe", "Kervan-DPI.exe",
                               base + "Kervan-DPI-1.0.2-update-manifest.json",
                               base + "Kervan-DPI-1.0.2-update-manifest.json.sig")

    def tearDown(self):
        self.temp.cleanup()

    def downloader(self, content):
        def download(url, release, name, destination, limit, cancel):
            data = content[name]
            if len(data) > limit:
                raise ValueError("size limit")
            Path(destination).write_bytes(data)
            return len(data), sha256(data).hexdigest()
        return download

    def content(self):
        return {"Kervan-DPI.exe": self.payload,
                "Kervan-DPI-1.0.2-update-manifest.json": self.manifest,
                "Kervan-DPI-1.0.2-update-manifest.json.sig": self.signature}

    def test_no_production_key_and_test_signature(self):
        self.assertEqual(PRODUCTION_PUBLIC_KEY_HEX, "")
        self.assertFalse(production_key_ready())
        self.assertEqual(verify_manifest(self.manifest, self.signature, self.public, "1.0.2")["sha256"],
                         sha256(self.payload).hexdigest())
        with self.assertRaisesRegex(ValueError, "Invalid publisher signature"):
            verify_manifest(self.manifest + b" ", self.signature, self.public, "1.0.2")
        with self.assertRaisesRegex(ValueError, "Publisher key"):
            verify_manifest(self.manifest, self.signature, b"", "1.0.2")
        with self.assertRaisesRegex(ValueError, "Wrong manifest version"):
            verify_manifest(self.manifest, self.signature, self.public, "1.0.3")

    def test_redirects_fail_closed(self):
        request = Request(self.release.asset_url)
        with self.assertRaisesRegex(ValueError, "Untrusted release download redirect"):
            _ReleaseRedirects().redirect_request(request, None, 302, "", {}, "https://evil.example/file")
        with self.assertRaisesRegex(ValueError, "Untrusted release download redirect"):
            _ReleaseRedirects().redirect_request(request, None, 302, "", {}, "http://release-assets.githubusercontent.com/file")
        allowed = _ReleaseRedirects().redirect_request(
            request, None, 302, "", {}, "https://release-assets.githubusercontent.com/file?token=fake")
        self.assertEqual(allowed.full_url.split("?", 1)[0], "https://release-assets.githubusercontent.com/file")

    def test_manifest_tool_uses_external_private_key_and_refuses_overwrite(self):
        payload = manifest_tool.prepare(self.exe, "v1.0.2")
        self.assertIn(b'"version":"1.0.2"', payload)
        pem = self.key.private_bytes(serialization.Encoding.PEM,
                                     serialization.PrivateFormat.PKCS8,
                                     serialization.NoEncryption())
        signature = manifest_tool.sign(payload, pem)
        verify_manifest(payload, signature, self.public, "1.0.2")
        output = self.root / "manifest.json"
        manifest_tool.write_new(output, payload)
        with self.assertRaises(FileExistsError):
            manifest_tool.write_new(output, payload)

    def test_stage_hash_signature_cancellation_and_cleanup(self):
        stage, staged = prepare_update(self.release, self.exe, self.public,
                                       download=self.downloader(self.content()))
        self.assertEqual(staged.read_bytes(), self.payload)
        self.assertEqual(self.exe.read_bytes(), b"MZold")
        bad = self.content(); bad["Kervan-DPI.exe"] += b"tampered"
        with self.assertRaisesRegex(ValueError, "signed manifest"):
            prepare_update(self.release, self.exe, self.public, download=self.downloader(bad))
        bad = self.content(); bad["Kervan-DPI-1.0.2-update-manifest.json.sig"] = bytes(64)
        with self.assertRaisesRegex(ValueError, "Invalid publisher signature"):
            prepare_update(self.release, self.exe, self.public, download=self.downloader(bad))
        self.assertEqual(len(list(self.root.glob(".kervan-update-*"))), 1)
        cancelled = threading.Event(); cancelled.set()
        with self.assertRaises(InterruptedError):
            prepare_update(self.release, self.exe, self.public,
                           download=self.downloader(self.content()), cancel=cancelled)
        with self.assertRaisesRegex(ValueError, "publisher key"):
            prepare_update(self.release, self.exe, b"", download=self.downloader(self.content()))
        with self.assertRaisesRegex(ValueError, "Signed standalone"):
            prepare_update(Release("1.0.2", "v1.0.2", self.release.notes_url,
                                   self.release.asset_url, "Kervan-DPI.exe"), self.exe,
                           self.public, download=self.downloader(self.content()))
        evil = Release("1.0.2", "v1.0.2", self.release.notes_url,
                       "https://evil.example/Kervan-DPI.exe", "Kervan-DPI.exe",
                       self.release.manifest_url, self.release.signature_url)
        with self.assertRaisesRegex(ValueError, "Untrusted signed release"):
            prepare_update(evil, self.exe, self.public, download=self.downloader(self.content()))

    def test_after_exit_replacement_and_rollback(self):
        stage, staged = prepare_update(self.release, self.exe, self.public,
                                       download=self.downloader(self.content()))
        digest = sha256(self.payload).hexdigest()
        with self.assertRaisesRegex(RuntimeError, "still running"):
            replace_after_exit(self.exe, staged, digest, FakeOps(exited=False))
        self.assertEqual(self.exe.read_bytes(), b"MZold")
        with self.assertRaisesRegex(PermissionError, "replacement denied"):
            replace_after_exit(self.exe, staged, digest, FakeOps(deny=True))
        self.assertEqual(self.exe.read_bytes(), b"MZold")
        with self.assertRaisesRegex(RuntimeError, "failed to restart"):
            replace_after_exit(self.exe, staged, digest, FakeOps(restart=False))
        self.assertEqual(self.exe.read_bytes(), b"MZold")
        staged.write_bytes(self.payload + b"changed")
        with self.assertRaisesRegex(ValueError, "changed after verification"):
            replace_after_exit(self.exe, staged, digest, FakeOps())
        staged.write_bytes(self.payload)
        ops = FakeOps()
        backup = replace_after_exit(self.exe, staged, digest, ops)
        self.assertEqual(self.exe.read_bytes(), self.payload)
        self.assertEqual(backup.read_bytes(), b"MZold")
        self.assertEqual(ops.restarts, [self.exe])


if __name__ == "__main__":
    unittest.main()
