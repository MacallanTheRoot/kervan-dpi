"""Offline release discovery and settings regression fixtures."""
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import Mock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from PySide6.QtWidgets import QApplication
from shiboken6 import delete
from app_controller import AppController
from ui.views.main_window import MainWindow
from ui.widgets.app_header import AppHeader
from ui.widgets.preferences_card import PreferencesCard
from utils.config import ConfigManager
from utils.updates import API_URL, CheckResult, UpdateChecker, Version, safe_release_url


def release(tag, prerelease=False, asset=True, draft=False):
    canonical = Version.parse(tag).canonical
    name = f"Kervan-DPI-{canonical}-windows-portable.zip"
    return {"tag_name": tag, "draft": draft, "prerelease": prerelease,
            "published_at": "2026-10-13T00:00:00Z",
            "html_url": f"https://github.com/MacallanTheRoot/GoodbyeDPI-Turkey-GUI/releases/tag/{tag}",
            "assets": ([{"name": name, "state": "uploaded", "size": 123456,
                         "browser_download_url": f"https://github.com/MacallanTheRoot/GoodbyeDPI-Turkey-GUI/releases/download/{tag}/{name}"}]
                       if asset else [])}


class DiscoveryTests(unittest.TestCase):
    def check(self, releases, current="1.0.1rc2"):
        fetch = Mock(return_value=(200, {}, json.dumps(releases).encode()))
        result = UpdateChecker(fetch=fetch).check(current)
        fetch.assert_called_once_with(API_URL, 5)
        return result

    def test_stable_release_is_newer_than_rc_and_rc_is_ignored(self):
        self.assertLess(Version.parse("v1.0.1-rc2"), Version.parse("1.0.1"))
        self.assertLess(Version.parse("1.0.1a1"), Version.parse("1.0.1b1"))
        self.assertLess(Version.parse("1.0.1b1"), Version.parse("1.0.1rc1"))
        self.assertEqual(Version.parse("v1.0.1-rc2").canonical, "1.0.1rc2")
        with self.assertRaises(ValueError):
            Version.parse("1.0.1+unknown")
        rows = [release("v1.0.1-rc3", True), release("v1.0.1")]
        self.assertEqual(self.check(rows).release.version, "1.0.1")
        self.assertEqual(self.check([rows[0]]).status, "current")
        self.assertEqual(self.check([release("v1.0.1-rc1", True)]).status, "current")
        self.assertEqual(self.check([release("v1.0.1-rc2", True)]).status, "current")
        self.assertEqual(self.check([release("v1.0.2-rc1", True)]).status, "current")
        mislabeled_rc = release("v1.0.2-rc1", False)
        mislabeled_stable = release("v1.0.2", True)
        self.assertEqual(self.check([mislabeled_rc, mislabeled_stable]).status, "current")

    def test_unavailable_unsupported_draft_and_untrusted_urls(self):
        self.assertEqual(self.check([release("v1.0.2", asset=False)]).status, "unavailable")
        self.assertEqual(self.check([release("v1.0.2", draft=True)]).status, "current")
        unsupported = release("v1.0.2")
        unsupported["tag_name"] = "v1.0.2+arbitrary"
        self.assertEqual(self.check([unsupported]).status, "current")
        item = release("v1.0.2")
        item["assets"][0]["browser_download_url"] = "https://evil.example/Kervan-DPI.exe"
        self.assertEqual(self.check([item]).status, "unavailable")
        item = release("v1.0.2")
        item["html_url"] = "https://github.com/other/repo/releases/tag/v1.0.2"
        self.assertEqual(self.check([item]).status, "current")
        self.assertFalse(safe_release_url("https://github.com.evil.example/x"))
        self.assertFalse(safe_release_url("http://github.com/MacallanTheRoot/GoodbyeDPI-Turkey-GUI/releases/tag/v1.0.2"))

    def test_http_malformed_offline_rate_limit_and_cancel(self):
        for status, expected in ((403, "rate_limited"), (404, "error"), (429, "rate_limited")):
            result = UpdateChecker(fetch=lambda *_: (status, {"Retry-After": "60"}, b""), clock=lambda: 100).check()
            self.assertEqual(result.status, expected)
        self.assertEqual(UpdateChecker(fetch=lambda *_: (200, {}, b"{" )).check().status, "error")
        self.assertEqual(UpdateChecker(fetch=lambda *_: (200, {}, b"{}") ).check().status, "error")
        self.assertEqual(UpdateChecker(fetch=lambda *_: (_ for _ in ()).throw(OSError("offline"))).check().status, "offline")
        stop = threading.Event(); stop.set()
        fetch = Mock()
        self.assertEqual(UpdateChecker(fetch=fetch).check(cancel=stop).status, "cancelled")
        fetch.assert_not_called()


class UpdateUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.config = ConfigManager(Path(self.temp.name))
        self.runner = Mock(process=None, output_thread=None, job_handle=None)
        self.controller = AppController(config=self.config, runner=self.runner, platform="windows", tray_enabled=False)
        # QLocale.system() follows the host OS; pin English for shared UI
        # assertions and test Turkish explicitly below.
        locale = Mock()
        locale.name.return_value = "en_US"
        with patch("ui.widgets.preferences_card.QLocale.system", return_value=locale):
            self.window = MainWindow(self.controller)
        self.controller.set_window(self.window)
        self.app.processEvents()

    def tearDown(self):
        self.controller.shutdown()
        delete(self.window)
        delete(self.controller)
        self.temp.cleanup()

    def wait_for(self, predicate):
        end = time.monotonic() + 2
        while time.monotonic() < end:
            self.app.processEvents()
            if predicate():
                return
            time.sleep(.005)
        self.fail("Timed out waiting for update UI")

    def test_automatic_install_is_gated_and_manual_check_is_independent(self):
        self.config.save_config("legacy_unknown", {"keep": True})
        self.assertFalse(self.controller.state.automatic_updates)
        self.assertFalse(self.window.preferences.automatic_updates.isEnabled())
        self.controller.set_automatic_updates(True)
        self.assertFalse(self.controller.state.automatic_updates)
        self.controller.set_automatic_updates(False)
        self.assertFalse(ConfigManager(Path(self.temp.name)).get("automatic_updates"))
        self.assertEqual(ConfigManager(Path(self.temp.name)).get("legacy_unknown"), {"keep": True})
        self.controller.update_checker = Mock()
        self.assertFalse(self.controller.check_updates())
        self.controller.update_checker.check.assert_not_called()
        self.assertEqual(self.controller.state.update_status, "idle")
        self.assertEqual(self.window.preferences.automatic_label.text(), "Automatic Updates: Off")
        self.assertIn("not available", self.window.preferences.automatic_notice.text())
        self.controller.update_checker = Mock(check=Mock(return_value=CheckResult("current")))
        self.window.preferences.check_updates.click()
        self.wait_for(lambda: self.controller.state.update_status == "current")
        self.controller.update_checker.check.assert_called_once()

    def test_old_modes_migrate_to_off_without_losing_other_settings(self):
        for mode in ("Off", "Notify", "Automatic", "unknown"):
            with self.subTest(mode=mode):
                with open(self.config.config_file, "w", encoding="utf-8") as stream:
                    json.dump({"update_mode": mode, "update_channel": "Preview",
                               "theme": "Dark", "other": 7}, stream)
                migrated = ConfigManager(Path(self.temp.name))
                self.assertFalse(migrated.get("automatic_updates"))
                self.assertEqual(migrated.get("theme"), "Dark")
                migrated.save_config("automatic_updates", False)
                saved = json.loads(self.config.config_file.read_text(encoding="utf-8"))
                self.assertNotIn("update_mode", saved)
                self.assertNotIn("update_channel", saved)
                self.assertEqual(saved["other"], 7)
        self.config.config_file.write_text('{"automatic_updates": true}', encoding="utf-8")
        stored = ConfigManager(Path(self.temp.name))
        controller = AppController(config=stored, runner=Mock(process=None, output_thread=None,
                                   job_handle=None), platform="windows", tray_enabled=False)
        try:
            self.assertFalse(controller.state.automatic_updates)
            self.assertFalse(controller.check_updates())
        finally:
            controller.shutdown()
            delete(controller)
        self.config.config_file.write_text('{"automatic_updates": 1}', encoding="utf-8")
        self.assertFalse(ConfigManager(Path(self.temp.name)).get("automatic_updates"))

    def test_async_result_later_error_and_throttle(self):
        item = release("v1.0.2")
        result = UpdateChecker(fetch=lambda *_: (200, {}, json.dumps([item]).encode())).check()
        self.controller.update_checker = Mock(check=Mock(return_value=result))
        self.assertTrue(self.controller.check_updates(manual=True))
        self.wait_for(lambda: self.controller.state.update_status == "available")
        self.assertIn("1.0.2", self.window.preferences.update_status.text())
        self.assertFalse(self.window.preferences.open_release.isHidden())
        self.controller.dismiss_update()
        self.assertEqual(self.controller.state.update_status, "later")
        self.assertFalse(self.controller.check_updates())  # 24-hour throttle
        self.controller.update_checker = Mock(check=Mock(return_value=CheckResult("rate_limited", message="GitHub request limit reached")))
        self.assertTrue(self.controller.check_updates(manual=True))
        self.wait_for(lambda: self.controller.state.update_status == "rate_limited")
        self.assertEqual(self.controller.state.update_message, "GitHub request limit reached")
        self.assertIn("GitHub request limit", self.window.preferences.update_status.text())
        self.assertEqual(self.window.preferences.check_updates.text(), "Check for Updates")
        self.assertFalse(self.controller.check_updates())  # error is throttled too
        self.assertEqual(self.controller.update_checker.check.call_count, 1)

    def test_turkish_async_error_and_manual_check_label(self):
        locale = Mock()
        locale.name.return_value = "tr_TR"
        with patch("ui.widgets.preferences_card.QLocale.system", return_value=locale):
            card = PreferencesCard()
        with patch("ui.widgets.app_header.QLocale.system", return_value=locale):
            header = AppHeader()
        try:
            self.assertEqual(header.preferences_button.text(), "⚙  Tercihler")
            self.assertEqual(header.about_button.text(), "Hakkında")
            self.assertEqual(card.automatic_label.text(), "")
            card.render(self.controller.state)
            self.assertEqual(card.automatic_label.text(), "Otomatik Güncellemeler: Kapalı")
            self.controller.update_checker = Mock(check=Mock(return_value=CheckResult(
                "rate_limited", message="GitHub request limit reached")))
            self.assertTrue(self.controller.check_updates(manual=True))
            self.wait_for(lambda: self.controller.state.update_status == "rate_limited")
            card.render(self.controller.state)
            self.assertEqual(card.check_updates.text(), "Güncellemeleri Denetle")
            self.assertEqual(card.update_status.text(), "GitHub istek sınırına ulaşıldı.")
            self.assertEqual(self.controller.state.update_message, "GitHub request limit reached")
            self.assertFalse(self.controller.check_updates())
            self.controller.update_checker.check.assert_called_once()
        finally:
            delete(header)
            delete(card.widget)

    def test_manual_check_survives_off_and_close_ignores_late_result(self):
        gate = threading.Event()
        self.controller.update_checker = Mock(check=Mock(side_effect=lambda **_: (gate.wait(1), CheckResult("available"))[1]))
        self.controller.check_updates(manual=True)
        self.controller.set_automatic_updates(False)
        gate.set()
        self.wait_for(lambda: self.controller.state.update_status == "available")
        gate.clear()
        self.controller.check_updates(manual=True)
        self.controller.shutdown()
        self.app.processEvents()
        self.assertTrue(self.controller._shutting_down)
        self.assertNotEqual(self.controller.state.update_status, "available")


if __name__ == "__main__":
    unittest.main()
