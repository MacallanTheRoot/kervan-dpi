"""Brand and opt-in migration contracts; only temporary paths are used."""
import json
import os
import stat
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from metadata import (APP_NAME, APP_SLOGAN, EXECUTABLE_NAME, LEGACY_APP_NAME,
                      LINUX_COMMAND)
from utils.brand_migration import (MigrationError, _check_directory, _check_file,
                                   prepare_config_copy)
from utils.config import ConfigManager
from utils.paths import config_dir
from utils.startup import set_enabled, startup_path


class BrandContractTests(unittest.TestCase):
    def test_display_and_technical_identity(self):
        self.assertEqual((APP_NAME, APP_SLOGAN, LEGACY_APP_NAME),
                         ("Kervan DPI", "Yol Açık, Kervan Yürür.", "GoodbyeDPI Turkey"))
        self.assertEqual((EXECUTABLE_NAME, LINUX_COMMAND),
                         ("Kervan-DPI", "goodbyedpi-turkey"))
        desktop = (ROOT / "packaging/linux/goodbyedpi-turkey.desktop").read_text(encoding="utf-8")
        self.assertIn(f"Name={APP_NAME}\n", desktop)
        self.assertIn("Exec=goodbyedpi-turkey\n", desktop)
        self.assertIn("Icon=goodbyedpi-turkey\n", desktop)
        deb = (ROOT / "packaging/debian/build_deb.sh").read_text(encoding="utf-8")
        self.assertIn("Package: goodbyedpi-turkey", deb)
        windows = (ROOT / "packaging/windows/goodbyedpi-turkey.spec").read_text(encoding="utf-8")
        self.assertIn("StringStruct('ProductName', APP_NAME)", windows)
        self.assertIn("name=EXECUTABLE_NAME", windows)

    def test_legacy_paths_and_single_autostart_entry(self):
        with tempfile.TemporaryDirectory() as root:
            home = Path(root)
            environment = {"XDG_CONFIG_HOME": str(home / "cfg")}
            self.assertEqual(config_dir("linux", environment, home),
                             home / "cfg/goodbyedpi-turkey")
            self.assertEqual(config_dir("win32", {"APPDATA": str(home / "roaming")}, home),
                             home / "roaming/GoodbyeDPI-Turkey")
            expected = startup_path("linux", environment, home)
            set_enabled(True, "linux", environment, home)
            first = expected.read_text(encoding="utf-8")
            set_enabled(True, "linux", environment, home)
            self.assertEqual(expected.read_text(encoding="utf-8"), first)
            self.assertIn("Name=Kervan DPI\n", first)
            self.assertEqual([p.name for p in expected.parent.glob("*.desktop")],
                             ["goodbyedpi-turkey.desktop"])


class ConfigCopyTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        root = Path(self.temporary.name)
        self.old = root / "old/config.json"
        self.new = root / "new/config.json"
        self.old.parent.mkdir()
        self.original = b'{"theme":"Dark","unknown":{"keep":true},"spoofdpi_mode":"Compatibility"}'
        self.old.write_bytes(self.original)

    def tearDown(self):
        self.temporary.cleanup()

    def test_copy_is_idempotent_and_preserves_unknown_settings(self):
        self.assertEqual(prepare_config_copy(self.old, self.new), "copied")
        self.assertEqual(prepare_config_copy(self.old, self.new), "already_copied")
        self.assertEqual(self.new.read_bytes(), self.original)
        self.assertEqual(self.old.read_bytes(), self.original)
        self.assertEqual(self.new.with_name("config.json.legacy-backup").read_bytes(),
                         self.original)
        self.assertTrue(json.loads(self.new.read_text(encoding="utf-8"))["unknown"]["keep"])
        # A later in-place write to the target must not alter the backup.
        self.new.write_bytes(b'changed')
        self.assertEqual(self.new.with_name("config.json.legacy-backup").read_bytes(),
                         self.original)

    def test_existing_different_target_is_left_alone(self):
        self.new.parent.mkdir()
        self.new.write_text('{"theme":"Light","future":1}')
        self.assertEqual(prepare_config_copy(self.old, self.new), "coexisting")
        self.assertEqual(json.loads(self.new.read_text(encoding="utf-8"))["future"], 1)
        self.assertFalse(self.new.with_name("config.json.legacy-backup").exists())

    def test_missing_and_malformed_source_report_failure(self):
        self.old.unlink()
        with self.assertRaisesRegex(MigrationError, "missing"):
            prepare_config_copy(self.old, self.new)
        self.old.write_text("{bad")
        with self.assertRaises(MigrationError):
            prepare_config_copy(self.old, self.new)
        self.assertFalse(self.new.exists())

    def test_permission_error_keeps_legacy_and_reports_failure(self):
        with patch("utils.brand_migration.os.link", side_effect=PermissionError("denied")):
            with self.assertRaisesRegex(MigrationError, "denied"):
                prepare_config_copy(self.old, self.new)
        self.assertFalse(self.new.exists())
        self.assertEqual(self.old.read_bytes(), self.original)
        self.assertEqual(prepare_config_copy(self.old, self.new), "copied")

    def test_interrupted_copy_can_resume_from_backup(self):
        self.new.parent.mkdir()
        self.new.with_name("config.json.legacy-backup").write_bytes(self.original)
        (self.new.parent / ".kervan-config-orphan").write_bytes(b"partial")
        self.assertEqual(prepare_config_copy(self.old, self.new), "copied")
        self.assertEqual(self.new.read_bytes(), self.original)

    def test_mismatched_backup_and_invalid_paths_are_rejected(self):
        self.new.parent.mkdir()
        self.new.with_name("config.json.legacy-backup").write_bytes(b"other")
        with self.assertRaisesRegex(MigrationError, "backup differs"):
            prepare_config_copy(self.old, self.new)
        with self.assertRaisesRegex(MigrationError, "absolute"):
            prepare_config_copy(Path("old/config.json"), self.new)
        with self.assertRaisesRegex(MigrationError, "absolute"):
            prepare_config_copy(self.old, self.new.parent / ".." / "new" / "config.json")
        self.assertFalse(self.new.exists())

    def test_hardlinked_source_and_destination_are_rejected(self):
        sibling = self.old.with_name("hardlink.json")
        os.link(self.old, sibling)
        with self.assertRaisesRegex(MigrationError, "linked"):
            prepare_config_copy(self.old, self.new)
        sibling.unlink()
        self.new.parent.mkdir()
        os.link(self.old, self.new)
        with self.assertRaisesRegex(MigrationError, "linked"):
            prepare_config_copy(self.old, self.new)
        self.assertEqual(self.old.read_bytes(), self.original)

    def test_backup_publish_failure_leaves_no_partial_backup_or_target(self):
        with patch("utils.brand_migration.os.fsync", side_effect=OSError("interrupted")):
            with self.assertRaisesRegex(MigrationError, "interrupted"):
                prepare_config_copy(self.old, self.new)
        self.assertFalse(self.new.exists())
        self.assertFalse(self.new.with_name("config.json.legacy-backup").exists())
        self.assertEqual(self.old.read_bytes(), self.original)
        self.assertEqual(prepare_config_copy(self.old, self.new), "copied")

    def test_target_stage_failure_retains_complete_backup_for_retry(self):
        original_fsync = os.fsync
        count = 0

        def fail_second(descriptor):
            nonlocal count
            count += 1
            if count == 2:
                raise OSError("target interrupted")
            return original_fsync(descriptor)

        with patch("utils.brand_migration.os.fsync", side_effect=fail_second):
            with self.assertRaisesRegex(MigrationError, "target interrupted"):
                prepare_config_copy(self.old, self.new)
        self.assertFalse(self.new.exists())
        self.assertEqual(self.new.with_name("config.json.legacy-backup").read_bytes(),
                         self.original)
        self.assertEqual(prepare_config_copy(self.old, self.new), "copied")

    def test_linked_paths_and_nonregular_files_are_rejected(self):
        self.new.parent.mkdir()
        self.new.mkdir()
        with self.assertRaisesRegex(MigrationError, "non-regular"):
            prepare_config_copy(self.old, self.new)

    def test_symlink_paths_are_rejected_when_supported(self):
        try:
            self.new.parent.symlink_to(self.old.parent, target_is_directory=True)
        except OSError:
            self.skipTest("Creating a directory symlink requires Windows developer privileges")
        with self.assertRaisesRegex(MigrationError, "linked"):
            prepare_config_copy(self.old, self.new)
        self.new.parent.unlink()
        self.new.parent.mkdir()
        self.new.symlink_to(self.old)
        with self.assertRaisesRegex(MigrationError, "linked"):
            prepare_config_copy(self.old, self.new)

    def test_windows_reparse_attributes_are_rejected(self):
        reparse_directory = SimpleNamespace(st_mode=stat.S_IFDIR | 0o755,
                                            st_file_attributes=0x400)
        reparse_file = SimpleNamespace(st_mode=stat.S_IFREG | 0o600,
                                       st_nlink=1, st_file_attributes=0x400)
        with patch.object(Path, "lstat", return_value=reparse_directory):
            with self.assertRaisesRegex(MigrationError, "linked"):
                _check_directory(self.new.parent)
        with patch.object(Path, "lstat", return_value=reparse_file):
            with self.assertRaisesRegex(MigrationError, "linked"):
                _check_file(self.old)

    def test_two_instances_publish_one_identical_target(self):
        results = []
        errors = []
        barrier = threading.Barrier(2)

        def copy():
            try:
                barrier.wait()
                results.append(prepare_config_copy(self.old, self.new))
            except Exception as exc:
                errors.append(exc)

        workers = [threading.Thread(target=copy) for _ in range(2)]
        for worker in workers:
            worker.start()
        for worker in workers:
            worker.join(timeout=2)
        self.assertFalse(errors)
        self.assertCountEqual(results, ["copied", "already_copied"])
        self.assertEqual(self.new.read_bytes(), self.original)
        self.assertEqual(self.new.with_name("config.json.legacy-backup").read_bytes(),
                         self.original)
        if os.name != "nt":
            self.assertEqual(self.new.stat().st_mode & 0o777, 0o600)


class ActiveLegacyConfigTests(unittest.TestCase):
    """Exercise the live shared config path without using a real profile."""

    def test_fresh_profile_and_existing_settings_use_same_legacy_path(self):
        with tempfile.TemporaryDirectory() as root:
            base = Path(root)
            directory = config_dir("win32", {"APPDATA": str(base)}, base)
            self.assertEqual(directory, base / "GoodbyeDPI-Turkey")
            with patch("utils.config.config_dir", return_value=directory), \
                 patch("utils.config.resource_path", return_value=base / "missing.json"):
                self.assertEqual(ConfigManager().get("theme"), "System")
                self.assertFalse(directory.exists())
                directory.mkdir()
                original = b'{"theme":"Dark","future":{"keep":true}}'
                (directory / "config.json").write_bytes(original)
                self.assertEqual(ConfigManager().get("theme"), "Dark")
                self.assertEqual((directory / "config.json").read_bytes(), original)

    def test_active_import_does_not_replace_destination_or_delete_source(self):
        with tempfile.TemporaryDirectory() as root:
            base = Path(root)
            legacy = base / "bundled-config.json"
            legacy.write_text('{"theme":"Dark","future":1}')
            directory = base / "GoodbyeDPI-Turkey"
            with patch("utils.config.config_dir", return_value=directory), \
                 patch("utils.config.resource_path", return_value=legacy):
                self.assertEqual(ConfigManager().get("theme"), "Dark")
                first = (directory / "config.json").read_bytes()
                self.assertEqual(ConfigManager().get("theme"), "Dark")
                self.assertEqual((directory / "config.json").read_bytes(), first)
                (directory / "config.json").write_text('{"theme":"Light","future":2}')
                self.assertEqual(ConfigManager().get("future"), 2)
                self.assertEqual(legacy.read_text(encoding="utf-8"), '{"theme":"Dark","future":1}')

    def test_corrupt_or_inaccessible_legacy_import_leaves_profile_empty(self):
        with tempfile.TemporaryDirectory() as root:
            base = Path(root)
            legacy = base / "bundled-config.json"
            directory = base / "GoodbyeDPI-Turkey"
            legacy.write_text("{broken")
            with patch("utils.config.config_dir", return_value=directory), \
                 patch("utils.config.resource_path", return_value=legacy):
                self.assertEqual(ConfigManager().get("theme"), "System")
                self.assertFalse((directory / "config.json").exists())
                legacy.write_text('{"theme":"Dark"}')
                with patch.object(Path, "read_text", side_effect=PermissionError("denied")):
                    self.assertEqual(ConfigManager().get("theme"), "System")
                self.assertFalse((directory / "config.json").exists())

    def test_rollback_and_portable_removal_keep_personal_data(self):
        with tempfile.TemporaryDirectory() as root:
            base = Path(root)
            directory = base / "GoodbyeDPI-Turkey"
            directory.mkdir()
            config = directory / "config.json"
            original = b'{"theme":"Dark","future":1}'
            config.write_bytes(original)
            candidate = base / "Kervan-DPI.exe"
            candidate.write_bytes(b"disposable test fixture")
            with patch("utils.config.config_dir", return_value=directory), \
                 patch("utils.config.resource_path", return_value=base / "missing.json"):
                self.assertEqual(ConfigManager().get("theme"), "Dark")
                candidate.unlink()  # Portable removal affects only the selected fixture.
                self.assertEqual(ConfigManager().get("theme"), "Dark")
            self.assertEqual(config.read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
