import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from app_controller import AppController
from utils import startup
from utils.config import ConfigManager
from utils.detector import get_arch
from utils.paths import config_dir, resource_path, resource_root
from utils.runner import DNSRunner, build_linux_command, find_spoof_dpi


class ConfigTests(unittest.TestCase):
    def test_old_config_defaults_to_normal_and_mode_persists(self):
        with tempfile.TemporaryDirectory() as root:
            folder = Path(root)
            (folder / "config.json").write_text('{"dns_provider": "Google"}')
            manager = ConfigManager(folder)
            self.assertEqual(manager.get("spoofdpi_mode"), "Normal")
            manager.save_config("spoofdpi_mode", "Compatibility")
            self.assertEqual(ConfigManager(folder).get("spoofdpi_mode"), "Compatibility")
            self.assertEqual(ConfigManager(folder).get("dns_provider"), "Google")

    def test_malformed_config_uses_defaults(self):
        with tempfile.TemporaryDirectory() as root:
            folder = Path(root)
            (folder / "config.json").write_text("{broken", encoding="utf-8")
            self.assertEqual(ConfigManager(folder).get("dns_provider"), "Turkey DNSRedir")

    def test_save_retains_unknown_keys(self):
        with tempfile.TemporaryDirectory() as root:
            folder = Path(root)
            (folder / "config.json").write_text('{"future": {"enabled": true}, "dns_provider": "Google"}')
            manager = ConfigManager(folder)
            manager.save_config("dns_provider", "Cloudflare")
            data = json.loads((folder / "config.json").read_text(encoding="utf-8"))
            self.assertEqual(data["future"], {"enabled": True})
            self.assertEqual(data["dns_provider"], "Cloudflare")
            self.assertFalse(list(folder.glob("*.tmp")))

    def test_legacy_migration_never_replaces_destination(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            legacy = root / "legacy.json"
            legacy.write_text('{"dns_provider": "Google", "future": 4}')
            folder = root / "config"
            with patch("utils.config.config_dir", return_value=folder), \
                 patch("utils.config.resource_path", return_value=legacy):
                self.assertEqual(ConfigManager().get("dns_provider"), "Google")
                self.assertTrue(legacy.exists())
                (folder / "config.json").write_text('{"dns_provider":"Cloudflare"}')
                self.assertEqual(ConfigManager().get("dns_provider"), "Cloudflare")

    def test_unsupported_config_os_is_explicit(self):
        with self.assertRaises(NotImplementedError):
            config_dir("darwin", {}, "/tmp")


class AutostartTests(unittest.TestCase):
    def test_windows_legacy_shortcut_remains_single_entry(self):
        with tempfile.TemporaryDirectory() as root, patch("utils.startup.subprocess.run") as run:
            env = {"APPDATA": root}
            folder = Path(root) / "Microsoft/Windows/Start Menu/Programs/Startup"
            folder.mkdir(parents=True)
            legacy = folder / "GoodbyeDPI-Turkey GUI.lnk"
            legacy.write_text("old target")
            self.assertEqual(startup.startup_path("win32", env, root), legacy)
            self.assertTrue(startup.is_enabled("win32", env, root))
            startup.set_enabled(True, "win32", env, root)
            self.assertIn(str(legacy), run.call_args.args[0][3])
            self.assertFalse((folder / "Kervan DPI.lnk").exists())

    def test_windows_shortcut_uses_powershell_and_minimized(self):
        with tempfile.TemporaryDirectory() as root, \
             patch("utils.startup.subprocess.run") as run, \
             patch.object(sys, "frozen", False, create=True):
            env = {"APPDATA": root}
            startup.set_enabled(True, "win32", env, root)
            script = run.call_args.args[0]
            self.assertEqual(script[:3], ["powershell", "-NoProfile", "-Command"])
            self.assertIn("--minimized", script[3])
            self.assertEqual(startup.startup_path("win32", env, root).parent,
                             Path(root) / "Microsoft/Windows/Start Menu/Programs/Startup")

    def test_linux_entry_from_source_and_disable(self):
        with tempfile.TemporaryDirectory() as root, \
             patch.object(sys, "frozen", False, create=True):
            env = {"XDG_CONFIG_HOME": root}
            startup.set_enabled(True, "linux", env, root)
            path = startup.startup_path("linux", env, root)
            self.assertTrue(startup.is_enabled("linux", env, root))
            content = path.read_text(encoding="utf-8")
            self.assertIn("Exec=", content)
            self.assertIn("main.py", content)
            self.assertIn("--minimized", content)
            startup.set_enabled(False, "linux", env, root)
            self.assertFalse(startup.is_enabled("linux", env, root))

    def test_linux_installed_launcher(self):
        with tempfile.TemporaryDirectory() as root, \
             patch.object(sys, "frozen", True, create=True), \
             patch.object(sys, "executable", "/opt/goodbyedpi-turkey/goodbyedpi-turkey"):
            startup.set_enabled(True, "linux", {"XDG_CONFIG_HOME": root}, root)
            self.assertIn('/opt/goodbyedpi-turkey/goodbyedpi-turkey" --minimized',
                          (Path(root) / "autostart/goodbyedpi-turkey.desktop").read_text(encoding="utf-8"))

    def test_debian_frozen_autostart_uses_running_executable(self):
        with tempfile.TemporaryDirectory() as root, \
             patch.object(sys, "frozen", True, create=True), \
             patch.object(sys, "executable", "/usr/bin/goodbyedpi-turkey"):
            startup.set_enabled(True, "linux", {"XDG_CONFIG_HOME": root}, root)
            entry = (Path(root) / "autostart/goodbyedpi-turkey.desktop").read_text(encoding="utf-8")
            self.assertIn('Exec="/usr/bin/goodbyedpi-turkey" --minimized', entry)

    def test_unsupported_autostart_os_is_explicit(self):
        with self.assertRaises(NotImplementedError):
            startup.startup_path("darwin", {}, "/tmp")


class ResourceAndArchitectureTests(unittest.TestCase):
    def test_source_and_installed_frozen_resources(self):
        with patch.object(sys, "frozen", False, create=True):
            self.assertTrue(resource_path("assets", "icon.png").exists())
        with patch.object(sys, "frozen", True, create=True), \
             patch.object(sys, "_MEIPASS", "/opt/goodbyedpi-turkey/_internal", create=True):
            self.assertEqual(resource_root(), Path("/opt/goodbyedpi-turkey/_internal"))

    def test_supported_and_unsupported_architectures(self):
        self.assertEqual(get_arch("windows", "i386"), "x86")
        self.assertEqual(get_arch("windows", "AMD64"), "x86_64")
        self.assertEqual(get_arch("linux", "amd64"), "x86_64")
        with self.assertRaises(NotImplementedError):
            get_arch("linux", "aarch64")


class SpoofDPITests(unittest.TestCase):
    def test_linux_modes_have_exact_arguments(self):
        normal = ["/usr/bin/spoofdpi", "-addr", "127.0.0.1", "-dns-addr", "77.88.8.8",
                  "-dns-port", "1253", "-port", "8080", "-system-proxy=false"]
        self.assertEqual(build_linux_command("/usr/bin/spoofdpi", "77.88.8.8", "1253"), normal)
        self.assertEqual(build_linux_command("/usr/bin/spoofdpi", "77.88.8.8", "1253",
                                             "Compatibility"), normal + ["-window-size", "4"])
        with self.assertRaises(ValueError):
            build_linux_command("/usr/bin/spoofdpi", "77.88.8.8", "1253", "invalid")

    def test_occupied_proxy_port_does_not_launch_or_claim_process(self):
        occupied = MagicMock()
        occupied.__enter__.return_value = occupied
        occupied.connect_ex.return_value = 0
        runner = object.__new__(DNSRunner)
        runner.process = None
        with patch("utils.runner.find_spoof_dpi", return_value="/usr/bin/spoofdpi"), \
             patch("utils.runner.socket.socket", return_value=occupied), \
             patch("utils.runner.subprocess.Popen") as popen:
            with self.assertRaisesRegex(OSError, "Port 8080 is already in use"):
                runner._start_linux("8.8.8.8", "53")
        popen.assert_not_called()
        self.assertIsNone(runner.process)

    def test_spoofdpi_path_branch_precedes_user_fallback(self):
        with patch("utils.runner.shutil.which", side_effect=lambda name: "/home/user/go/bin/spoofdpi" if name == "spoofdpi" else None), \
             patch("utils.runner.os.path.isfile", return_value=True), \
             patch("utils.runner.os.access", return_value=True):
            self.assertEqual(find_spoof_dpi(), "/home/user/go/bin/spoofdpi")

    def test_linux_command_uses_supported_v012_flags(self):
        process = Mock()
        process.poll.return_value = None
        process.stdout = None
        socket_first = MagicMock()
        socket_first.connect_ex.return_value = 1
        socket_second = MagicMock()
        socket_second.connect_ex.return_value = 0
        for item in (socket_first, socket_second):
            item.__enter__ = Mock(return_value=item)
            item.__exit__ = Mock(return_value=False)
        runner = object.__new__(DNSRunner)
        runner.process = None
        with patch("utils.runner.find_spoof_dpi", return_value="/usr/bin/spoof-dpi"), \
             patch("utils.runner.socket.socket", side_effect=[socket_first, socket_second]), \
             patch("utils.runner.subprocess.Popen", return_value=process) as popen:
            runner._start_linux("1.1.1.1", "53")
        args = popen.call_args.args[0]
        self.assertEqual(args, ["/usr/bin/spoof-dpi", "-addr", "127.0.0.1",
                                "-dns-addr", "1.1.1.1", "-dns-port", "53",
                                "-port", "8080", "-system-proxy=false"])
        self.assertNotIn("-enable-doh", args)

    def test_early_engine_exit_fails_start(self):
        process = Mock()
        process.poll.return_value = 1
        process.stdout.read.return_value = b"bind failed"
        socket_probe = MagicMock()
        socket_probe.connect_ex.return_value = 1
        socket_probe.__enter__ = Mock(return_value=socket_probe)
        socket_probe.__exit__ = Mock(return_value=False)
        runner = object.__new__(DNSRunner)
        runner.process = None
        runner.log_callback = Mock()
        runner.stop = Mock()
        with patch("utils.runner.find_spoof_dpi", return_value="/usr/bin/spoof-dpi"), \
             patch("utils.runner.socket.socket", return_value=socket_probe), \
             patch("utils.runner.subprocess.Popen", return_value=process):
            with self.assertRaisesRegex(RuntimeError, "exited before"):
                runner._start_linux("8.8.8.8", "53")
        runner.stop.assert_called_once_with()
        runner.log_callback.assert_called_once_with("bind failed")

    def test_path_is_first_discovery_choice(self):
        with patch("utils.runner.shutil.which", side_effect=lambda name: "/tmp/spoof-dpi" if name == "spoof-dpi" else None), \
             patch("utils.runner.os.path.isfile", return_value=True), \
             patch("utils.runner.os.access", return_value=True):
            self.assertEqual(find_spoof_dpi(), "/tmp/spoof-dpi")

    def test_local_and_system_fallback_order(self):
        with tempfile.TemporaryDirectory() as root, \
             patch("utils.runner.shutil.which", return_value=None), \
             patch("utils.runner.Path.home", return_value=Path(root)):
            user = Path(root) / ".spoof-dpi/bin/spoof-dpi"
            user.parent.mkdir(parents=True)
            user.write_text("binary")
            user.chmod(0o755)
            self.assertEqual(find_spoof_dpi(), str(user))
            user.unlink()
            with patch("utils.runner.os.path.isfile", side_effect=lambda path: path == "/usr/local/bin/spoof-dpi"), \
                 patch("utils.runner.os.access", return_value=True):
                self.assertEqual(find_spoof_dpi(), "/usr/local/bin/spoof-dpi")

    def test_missing_executable_raises_actionable_error(self):
        with patch("utils.runner.shutil.which", return_value=None), \
             patch("utils.runner.os.path.isfile", return_value=False):
            with self.assertRaisesRegex(FileNotFoundError, "SpoofDPI not found"):
                find_spoof_dpi()


if __name__ == "__main__":
    unittest.main()
