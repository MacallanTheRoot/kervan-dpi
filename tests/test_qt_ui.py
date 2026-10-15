"""Qt UI behavior and thread boundary tests, runnable without a display server."""
import os
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from PySide6.QtCore import QThread
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QComboBox, QLabel, QSystemTrayIcon, QWidget
from shiboken6 import delete

from app_controller import AppController
from app_state import Phase
from metadata import APP_NAME, APP_SLOGAN, COPYRIGHT, LEGACY_APP_NAME, ORGANIZATION
from ui.theme import resolve_theme
from ui.views.main_window import MainWindow
from utils.config import ConfigManager


class QtUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.config = ConfigManager(Path(self.folder.name))
        self.runner = Mock()
        self.runner.process = None
        self.runner.output_thread = None
        self.runner.job_handle = None
        self.controller = AppController(config=self.config, runner=self.runner,
                                        platform="linux", tray_enabled=False)
        self.window = MainWindow(self.controller)
        self.controller.set_window(self.window)
        self.app.processEvents()

    def tearDown(self):
        self.controller.shutdown()
        delete(self.window)
        delete(self.controller)
        self.folder.cleanup()

    def wait_for(self, predicate, timeout=2):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            self.app.processEvents()
            if predicate():
                return
            time.sleep(0.005)
        self.fail("Qt signal was not delivered")

    def test_one_window_and_initial_linux_wording(self):
        self.assertEqual(self.window.windowTitle(), APP_NAME)
        self.assertEqual(self.window.header.findChild(QLabel, "title").text(), APP_NAME)
        self.assertEqual(self.window.header.about_button.accessibleName(), f"About {APP_NAME}")
        self.assertEqual(self.window.footer_about_button.accessibleName(), f"About {APP_NAME}")
        self.assertEqual(self.window.status.heading.text(), "Local Proxy Inactive")
        self.assertIn("SpoofDPI", self.window.status.detail.text())
        self.assertEqual(self.window.dns.backend.text(), "SpoofDPI · local HTTP proxy")
        self.assertEqual(self.window.status.action.text(), "Enable")
        self.assertFalse(self.window.activity.log.isVisible())

    def test_preferences_open_close_and_main_screen_is_compact(self):
        self.window.resize(520, 620)
        self.window.show()
        self.app.processEvents()
        self.assertNotIn(self.window.preferences.widget,
                         self.window.centralWidget().findChildren(QWidget))
        self.assertFalse(self.window.preferences_dialog.isVisible())
        self.assertLess(self.window.header.preferences_button.geometry().right(),
                        self.window.header.about_button.geometry().left())
        self.window.header.preferences_button.click()
        self.app.processEvents()
        self.assertTrue(self.window.preferences_dialog.isVisible())
        self.assertTrue(self.window.isVisible())
        self.window.close_preferences_button.click()
        self.app.processEvents()
        self.assertFalse(self.window.preferences_dialog.isVisible())
        self.window.header.preferences_button.click()
        QTest.keyClick(self.window.preferences_dialog, Qt.Key.Key_Escape)
        self.app.processEvents()
        self.assertFalse(self.window.preferences_dialog.isVisible())

    def test_update_settings_have_one_toggle_and_no_legacy_selectors(self):
        self.assertEqual(self.window.preferences.automatic_label.text(),
                         "Otomatik Güncellemeler: Kapalı" if self.window.preferences._tr else
                         "Automatic Updates: Off")
        self.assertEqual(self.window.preferences.check_updates.text(),
                         "Güncellemeleri Denetle" if self.window.preferences._tr else
                         "Check for Updates")
        self.assertFalse(self.window.preferences.automatic_updates.isEnabled())
        self.assertFalse(hasattr(self.window.preferences, "update_mode"))
        self.assertFalse(hasattr(self.window.preferences, "update_channel"))
        names = [combo.accessibleName() for combo in
                 self.window.preferences.widget.findChildren(QComboBox)]
        self.assertNotIn("Update checking mode", names)
        self.assertNotIn("Update release channel", names)

    def test_about_brand_and_backend(self):
        with patch("ui.views.main_window.QMessageBox.about") as about:
            self.window.open_about()
        title, body = about.call_args.args[1:]
        self.assertEqual(title, f"About {APP_NAME}")
        for value in (APP_NAME, APP_SLOGAN, LEGACY_APP_NAME, "SpoofDPI",
                      f"Developed by {ORGANIZATION}", COPYRIGHT):
            self.assertIn(value, body)

    def test_tray_branding_when_available(self):
        with patch.object(QSystemTrayIcon, "isSystemTrayAvailable", return_value=True):
            controller = AppController(config=self.config, runner=self.runner,
                                       platform="linux", tray_enabled=True)
        try:
            self.assertEqual(controller.tray.toolTip(), APP_NAME)
            self.assertEqual(controller.show_action.text(), f"Show {APP_NAME}")
            self.assertEqual(controller.quit_action.text(), f"Quit {APP_NAME}")
        finally:
            controller.shutdown()
            delete(controller)

    def test_transparent_choice_is_persisted_and_cannot_activate(self):
        self.window.preferences.linux_engine.setCurrentText("Zapret2 — Transparent (Experimental)")
        self.app.processEvents()
        self.assertEqual(self.config.get("linux_engine"), "Zapret2 — Transparent (Experimental)")
        self.assertFalse(self.window.status.action.isEnabled())
        self.assertFalse(self.window.dns.selector.isEnabled())
        self.assertFalse(self.window.preferences.mode_row.isVisible())
        self.assertIn("Unavailable", self.window.status.heading.text())
        self.controller.start()
        self.runner.start.assert_not_called()
        self.window.preferences.zapret_strategy.setCurrentText("TLS fake + split (research)")
        self.assertEqual(self.config.get("zapret_strategy"), "TLS fake + split (research)")
        self.window.preferences.linux_engine.setCurrentText("SpoofDPI — Proxy")
        self.assertTrue(self.window.status.action.isEnabled())

    def test_engine_switch_is_locked_during_proxy_operation(self):
        self.controller.state.phase = Phase.ACTIVE
        self.controller.state_changed.emit(self.controller.state)
        self.controller.set_linux_engine("Zapret2 — Transparent (Experimental)")
        self.assertEqual(self.controller.state.linux_engine, "SpoofDPI — Proxy")
        self.assertEqual(sum(isinstance(w, MainWindow) for w in self.app.topLevelWidgets()), 1)

    def test_windows_copy(self):
        self.controller.state.platform = "windows"
        self.controller.state_changed.emit(self.controller.state)
        self.assertEqual(self.window.status.heading.text(), "Protection Inactive")
        self.assertIn("GoodbyeDPI", self.window.status.detail.text())
        self.controller.state.phase = Phase.ACTIVE
        self.controller.state_changed.emit(self.controller.state)
        self.assertEqual(self.window.status.heading.text(), "Protection Active")
        self.assertEqual(self.window.dns.backend.text(), "GoodbyeDPI · DNS redirection")

    def test_enable_disable_and_endpoint(self):
        self.window.status.action.click()
        self.assertIn(self.controller.state.phase, (Phase.STARTING, Phase.ACTIVE))
        self.wait_for(lambda: self.controller.state.phase == Phase.ACTIVE)
        self.runner.start.assert_called_once_with(dns_addr="77.88.8.8", dns_port="1253",
                                                  spoofdpi_mode="Normal")
        self.assertEqual(self.window.status.heading.text(), "Local Proxy Active")
        self.assertIn("127.0.0.1:8080", self.window.status.detail.text())
        self.assertFalse(self.window.dns.selector.isEnabled())
        self.assertFalse(self.window.preferences.spoofdpi_mode.isEnabled())
        self.window.status.action.click()
        self.wait_for(lambda: self.controller.state.phase == Phase.INACTIVE)
        self.runner.stop.assert_called_once()
        self.assertTrue(self.window.dns.selector.isEnabled())
        self.assertTrue(self.window.preferences.spoofdpi_mode.isEnabled())

    def test_compatibility_selection_is_persisted_and_locked_while_running(self):
        selector = self.window.preferences.spoofdpi_mode
        self.assertEqual(selector.currentText(), "Normal")
        selector.setCurrentText("Compatibility")
        self.assertEqual(ConfigManager(Path(self.folder.name)).get("spoofdpi_mode"), "Compatibility")
        self.controller.start()
        self.wait_for(lambda: self.controller.state.phase == Phase.ACTIVE)
        self.runner.start.assert_called_once_with(dns_addr="77.88.8.8", dns_port="1253",
                                                  spoofdpi_mode="Compatibility")
        self.assertFalse(selector.isEnabled())
        self.controller.set_spoofdpi_mode("Normal")
        self.assertEqual(self.controller.state.spoofdpi_mode, "Compatibility")
        self.controller.stop()
        self.wait_for(lambda: self.controller.state.phase == Phase.INACTIVE)
        self.assertTrue(selector.isEnabled())

    def test_windows_has_no_mode_control_or_engine_argument(self):
        self.controller.state.platform = "windows"
        self.controller.state_changed.emit(self.controller.state)
        self.assertTrue(self.window.preferences.mode_row.isHidden())
        self.controller.set_spoofdpi_mode("Compatibility")
        self.assertEqual(self.controller.state.spoofdpi_mode, "Normal")
        self.controller.start()
        self.wait_for(lambda: self.controller.state.phase == Phase.ACTIVE)
        self.runner.start.assert_called_once_with(dns_addr="77.88.8.8", dns_port="1253")

    def test_invalid_saved_mode_falls_back_to_normal(self):
        self.config.save_config("spoofdpi_mode", "bad")
        other = AppController(config=ConfigManager(Path(self.folder.name)), runner=Mock(),
                              platform="linux", tray_enabled=False)
        self.assertEqual(other.state.spoofdpi_mode, "Normal")
        other.shutdown()

    def test_failed_start_stays_error_and_retryable(self):
        self.runner.start.side_effect = FileNotFoundError("SpoofDPI not found")
        self.controller.start()
        self.wait_for(lambda: self.controller.state.phase == Phase.ERROR)
        self.assertEqual(self.window.status.action.text(), "Enable")
        self.assertIn("SpoofDPI not found", self.window.status.detail.text())
        self.assertNotIn("Active", self.window.status.heading.text())

    def test_port_collision_does_not_claim_active(self):
        self.runner.start.side_effect = OSError("Port 8080 is already in use")
        self.controller.start()
        self.wait_for(lambda: self.controller.state.phase == Phase.ERROR)
        self.assertIn("Port 8080", self.window.status.detail.text())

    def test_unreaped_stop_does_not_claim_inactive(self):
        self.controller.state.phase = Phase.ACTIVE
        self.runner.process = Mock()
        self.controller.stop()
        self.wait_for(lambda: self.controller.state.phase == Phase.ERROR)
        self.assertIn("did not exit", self.window.status.detail.text())
        self.assertFalse(self.window.preferences.spoofdpi_mode.isEnabled())
        self.controller.set_spoofdpi_mode("Compatibility")
        self.assertEqual(self.controller.state.spoofdpi_mode, "Normal")

    def test_unreaped_quit_keeps_qt_running_and_allows_retry(self):
        self.runner.process = Mock()
        with patch.object(QApplication, "quit") as quit_qt:
            self.controller.quit_app()
            quit_qt.assert_not_called()
            self.assertEqual(self.controller.state.phase, Phase.ERROR)
            self.assertFalse(self.controller._shutdown_complete)
            self.runner.process = None
            self.controller.quit_app()
            quit_qt.assert_called_once()
        self.runner.close.assert_called()

    def test_windows_immediate_quit_waits_for_start_before_close(self):
        self.controller.state.platform = 'windows'
        entered = threading.Event()
        release = threading.Event()
        order = []

        def slow_start(**kwargs):
            entered.set()
            self.assertTrue(release.wait(2))
            order.append('start finished')

        self.runner.start.side_effect = slow_start
        self.runner.close.side_effect = lambda: order.append('closed')
        self.controller.start()
        self.assertTrue(entered.wait(2))
        self.controller.start()
        self.assertEqual(self.runner.start.call_count, 1)
        timer = threading.Timer(0.02, release.set)
        timer.start()
        try:
            with patch.object(QApplication, 'quit') as quit_qt:
                self.controller.quit_app()
            quit_qt.assert_called_once()
        finally:
            release.set()
            timer.join()
        self.assertEqual(order, ['start finished', 'closed'])
        self.assertTrue(self.controller._shutdown_complete)

    def test_stale_start_signal_cannot_reactivate_after_new_operation(self):
        self.controller.state.platform = 'windows'
        self.controller.state.phase = Phase.STARTING
        self.controller._operation_token = 2
        self.controller._finish_operation(1, 'start', True, '')
        self.assertEqual(self.controller.state.phase, Phase.STARTING)
        self.controller._finish_operation(2, 'start', True, '')
        self.assertEqual(self.controller.state.phase, Phase.ACTIVE)

    def test_failed_quit_cannot_overlap_live_start_or_lose_worker(self):
        entered = threading.Event()
        release = threading.Event()

        def slow_start(**kwargs):
            entered.set()
            self.assertTrue(release.wait(2))

        self.runner.start.side_effect = slow_start
        self.controller.start()
        self.assertTrue(entered.wait(2))
        original_worker = self.controller._worker
        try:
            # Simulate the bounded shutdown wait expiring without waiting 15 s.
            with patch.object(original_worker, 'join', return_value=None):
                self.assertFalse(self.controller.shutdown())
            self.assertEqual(self.controller.state.phase, Phase.ERROR)
            self.assertFalse(self.window.status.action.isEnabled())
            self.assertFalse(self.window.preferences.linux_engine.isEnabled())
            self.controller.start()
            self.controller.set_linux_engine('Zapret2 — Transparent (Experimental)')
            self.assertIs(self.controller._worker, original_worker)
            self.assertEqual(self.runner.start.call_count, 1)
            self.assertEqual(self.controller.state.linux_engine, 'SpoofDPI — Proxy')
        finally:
            release.set()
        self.wait_for(lambda: self.controller._operation_done.is_set() and
                      self.window.status.action.isEnabled())
        # The cancelled completion cannot reactivate the backend.
        self.assertEqual(self.controller.state.phase, Phase.ERROR)
        self.runner.start.side_effect = None
        self.controller.start()
        self.wait_for(lambda: self.controller.state.phase == Phase.ACTIVE)
        self.assertEqual(self.runner.start.call_count, 2)

    def test_rapid_start_stop_start_serializes_backend_calls(self):
        stop_entered = threading.Event()
        stop_release = threading.Event()
        events = []
        self.runner.start.side_effect = lambda **kwargs: events.append('start')

        def slow_stop():
            events.append('stop entered')
            stop_entered.set()
            self.assertTrue(stop_release.wait(2))
            events.append('stop finished')

        self.runner.stop.side_effect = slow_stop
        self.controller.start()
        self.wait_for(lambda: self.controller.state.phase == Phase.ACTIVE)
        self.controller.stop()
        self.assertTrue(stop_entered.wait(2))
        try:
            self.controller.start()
            self.assertEqual(events, ['start', 'stop entered'])
            self.assertEqual(self.controller.state.phase, Phase.STOPPING)
        finally:
            stop_release.set()
        self.wait_for(lambda: self.controller.state.phase == Phase.INACTIVE)
        self.controller.start()
        self.wait_for(lambda: self.controller.state.phase == Phase.ACTIVE)
        self.assertEqual(events, ['start', 'stop entered', 'stop finished', 'start'])

    def test_delivered_completion_allows_stop_before_thread_retirement(self):
        self.controller.start()
        self.wait_for(lambda: self.controller.state.phase == Phase.ACTIVE)
        completed_worker = self.controller._worker
        with patch.object(completed_worker, 'is_alive', return_value=True):
            self.controller.stop()
            self.assertEqual(self.controller.state.phase, Phase.STOPPING)
        self.wait_for(lambda: self.controller.state.phase == Phase.INACTIVE)
        self.runner.stop.assert_called_once()

    def test_stale_stop_completion_cannot_finish_new_start(self):
        self.controller.state.phase = Phase.STARTING
        self.controller._operation_token = 4
        self.controller._finish_operation(3, 'stop', True, '')
        self.assertEqual(self.controller.state.phase, Phase.STARTING)
        self.controller._finish_operation(4, 'start', True, '')
        self.assertEqual(self.controller.state.phase, Phase.ACTIVE)

    def test_dns_load_and_save(self):
        self.config.save_config("dns_provider", "Google")
        self.controller.state.dns_provider = "Google"
        self.controller.state_changed.emit(self.controller.state)
        self.assertEqual(self.window.dns.selector.currentText(), "Google")
        self.window.dns.selector.setCurrentText("Cloudflare")
        self.assertEqual(ConfigManager(Path(self.folder.name)).get("dns_provider"), "Cloudflare")

    def test_startup_toggle(self):
        with patch("app_controller.startup.set_enabled") as set_enabled:
            self.window.preferences.startup.click()
        set_enabled.assert_called_once_with(True)
        self.assertTrue(self.controller.state.startup_enabled)

    def test_theme_persistence_and_modes(self):
        for name in ("Light", "Dark", "System"):
            self.window.preferences.theme.setCurrentText(name)
            self.assertEqual(self.config.get("theme"), name)
            self.assertEqual(self.controller.state.theme, name)
        self.assertIn(resolve_theme("System"), ("Light", "Dark"))
        self.assertEqual(resolve_theme("Light"), "Light")
        self.assertEqual(resolve_theme("Dark"), "Dark")

    def test_activity_expands_and_log_arrives_on_gui_thread(self):
        received = []
        self.controller.state_changed.connect(lambda _: received.append(QThread.currentThread() == self.app.thread()))
        worker = threading.Thread(target=lambda: self.controller.log("reader line"))
        worker.start()
        worker.join()
        self.wait_for(lambda: "reader line" in self.window.activity.log.toPlainText())
        self.assertTrue(all(received))
        self.window.activity.button.click()
        self.assertTrue(self.controller.state.activity_expanded)
        self.assertFalse(self.window.activity.log.isHidden())
        self.window.activity.button.click()
        self.assertFalse(self.controller.state.activity_expanded)

    def test_window_close_and_restore_same_window(self):
        self.controller.tray_available = True
        self.window.show()
        self.window.close()
        self.assertTrue(self.window.isHidden())
        self.controller.show_window()
        self.assertTrue(self.window.isVisible())
        self.assertIs(self.controller.window, self.window)

    def test_tray_primary_and_quit_call_safe_shutdown(self):
        self.controller.tray_available = True
        self.window.hide()
        self.controller._tray_activated(QSystemTrayIcon.ActivationReason.Trigger)
        self.assertTrue(self.window.isVisible())
        with patch.object(self.controller, "shutdown", wraps=self.controller.shutdown) as shutdown:
            self.controller.quit_app()
            self.controller.quit_app()
        self.assertGreaterEqual(shutdown.call_count, 1)
        self.runner.close.assert_called_once()

    def test_accessible_names_and_minimum_size(self):
        self.assertIn("proxy", self.window.status.action.accessibleName())
        self.assertEqual(self.window.dns.selector.accessibleName(), "DNS provider")
        self.assertEqual(self.window.preferences.startup.accessibleName(), "Run on startup")
        self.assertEqual(self.window.minimumWidth(), 520)
        self.assertEqual(self.window.minimumHeight(), 620)

    def test_keyboard_primary_action_and_tab_order(self):
        self.window.show()
        self.window.header.about_button.setFocus()
        next_control = self.window.header.about_button.nextInFocusChain()
        while next_control.focusPolicy() == Qt.FocusPolicy.NoFocus:
            next_control = next_control.nextInFocusChain()
        self.assertIs(next_control, self.window.status.action)
        QTest.keyClick(self.window.status.action, Qt.Key.Key_Space)
        self.wait_for(lambda: self.controller.state.phase == Phase.ACTIVE)
        QTest.keyClick(self.window.status.action, Qt.Key.Key_Space)
        self.wait_for(lambda: self.controller.state.phase == Phase.INACTIVE)

    def test_minimized_semantics_with_tray(self):
        self.controller.tray_available = True
        self.assertTrue(self.window.isHidden())
        self.controller.start()
        self.wait_for(lambda: self.controller.state.phase == Phase.ACTIVE)
        self.assertTrue(self.window.isHidden())
        self.controller.show_window()
        self.assertTrue(self.window.isVisible())


if __name__ == "__main__":
    unittest.main()
