"""Release-candidate contracts that can run without a native Windows host."""
import os
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import main
from metadata import (APP_NAME, DEBIAN_VERSION, DISPLAY_VERSION, LINUX_COMMAND,
                      VERSION, WINDOWS_FILE_VERSION)


class MetadataTests(unittest.TestCase):
    def test_one_prerelease_version_feeds_platform_formats(self):
        self.assertTrue(VERSION.endswith("rc2"))
        self.assertEqual(DEBIAN_VERSION, VERSION.replace("rc", "~rc"))
        self.assertEqual(DISPLAY_VERSION, f"v{VERSION}")
        self.assertEqual(WINDOWS_FILE_VERSION[:3],
                         tuple(map(int, VERSION.split("rc")[0].split("."))))

    def test_desktop_identity_and_launcher(self):
        desktop = (ROOT / "packaging/linux/goodbyedpi-turkey.desktop").read_text(encoding="utf-8")
        self.assertIn(f"Name={APP_NAME}\n", desktop)
        self.assertIn(f"Exec={LINUX_COMMAND}\n", desktop)
        self.assertIn(f"Icon={LINUX_COMMAND}\n", desktop)
        self.assertNotIn(str(ROOT), desktop)

    def test_windows_resources_exist_for_both_architectures(self):
        for arch in ("x86", "x86_64"):
            with self.subTest(arch=arch):
                for name in ("goodbyedpi.exe", "WinDivert.dll"):
                    self.assertTrue((ROOT / "bin" / arch / name).is_file())
        self.assertTrue((ROOT / "bin/x86/WinDivert32.sys").is_file())
        self.assertTrue((ROOT / "bin/x86_64/WinDivert64.sys").is_file())
        spec = (ROOT / "packaging/windows/goodbyedpi-turkey.spec").read_text(encoding="utf-8")
        self.assertIn("(str(project_root / 'bin'), 'bin')", spec)
        self.assertIn("uac_admin=False", spec)
        self.assertIn("console=False", spec)
        self.assertIn("excludes=['packaged_smoke']", spec)

    def test_windows_build_entry_point_uses_the_spec_and_venv(self):
        batch = (ROOT / "build.bat").read_bytes()
        self.assertNotIn(b"\x0b", batch)
        self.assertIn(b".venv\\Scripts\\python.exe", batch)
        self.assertIn(b"packaging\\windows\\goodbyedpi-turkey.spec", batch)


class ElevationTests(unittest.TestCase):
    def test_frozen_elevation_preserves_minimized_argument(self):
        shell = Mock()
        shell.ShellExecuteW.return_value = 42
        with patch.object(main, "os", SimpleNamespace(name="nt", path=os.path)), \
             patch.object(main, "sys", SimpleNamespace(executable=r"C:\app\Kervan-DPI.exe",
                                                       frozen=True)), \
             patch.object(main, "is_admin", return_value=False), \
             patch.object(main.ctypes, "windll", SimpleNamespace(shell32=shell), create=True):
            self.assertEqual(main.main(["Kervan-DPI.exe", "--minimized"]), 0)
        args = shell.ShellExecuteW.call_args.args
        self.assertEqual(args[1], "runas")
        self.assertEqual(args[2], r"C:\app\Kervan-DPI.exe")
        self.assertEqual(args[3], "--minimized")

    def test_smoke_flag_alone_does_not_enter_harness(self):
        app = Mock()
        app.exec.return_value = 0
        smoke = Mock()
        module = SimpleNamespace(PackagedSmoke=smoke)
        with patch.dict(os.environ, {"GOODBYEDPI_PACKAGED_SMOKE": ""}), \
             patch.dict(sys.modules, {"packaged_smoke": module}), \
             patch.object(main, "QApplication", return_value=app), \
             patch.object(main, "QIcon"), \
             patch.object(main, "AppController"), \
             patch.object(main, "MainWindow"):
            self.assertEqual(main.main(["main.py", "--self-test"]), 0)
        smoke.assert_not_called()


if __name__ == "__main__":
    unittest.main()
