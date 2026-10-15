"""Connects platform services to an explicit Qt-facing state."""
import sys
import threading
import time
from datetime import datetime

from PySide6.QtCore import QObject, QTimer, Signal, Slot
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from app_state import AppState, DNS_PROVIDERS, Phase
from metadata import APP_NAME
from utils.updates import CHECK_INTERVAL, CheckResult, UpdateChecker
from utils.update_install import automatic_install_ready
from utils import startup
from utils.config import ConfigManager
from utils.paths import resource_path
from utils.runner import DNSRunner
from utils.zapret2 import DEFAULT_STRATEGY, STRATEGIES, Zapret2Adapter

SPOOFDPI_ENGINE = "SpoofDPI — Proxy"
ZAPRET_ENGINE = "Zapret2 — Transparent (Experimental)"


class AppController(QObject):
    state_changed = Signal(object)
    log_arrived = Signal(str)
    operation_finished = Signal(int, str, bool, str)
    update_finished = Signal(int, object)

    def __init__(self, config=None, runner=None, platform=None, tray_enabled=True):
        super().__init__()
        self.config = config or ConfigManager()
        platform = platform or ("windows" if sys.platform == "win32" else "linux")
        saved_dns = self.config.get("dns_provider")
        saved_theme = self.config.get("theme")
        saved_mode = self.config.get("spoofdpi_mode")
        saved_engine = self.config.get("linux_engine")
        saved_strategy = self.config.get("zapret_strategy")
        try:
            startup_enabled = startup.is_enabled()
        except (OSError, NotImplementedError):
            startup_enabled = False
        self.state = AppState(platform=platform,
                              dns_provider=saved_dns if saved_dns in DNS_PROVIDERS else "Turkey DNSRedir",
                              theme=saved_theme if saved_theme in ("System", "Light", "Dark") else "System",
                              spoofdpi_mode=saved_mode if saved_mode in ("Normal", "Compatibility") else "Normal",
                              linux_engine=saved_engine if platform == "linux" and
                              saved_engine in (SPOOFDPI_ENGINE, ZAPRET_ENGINE) else SPOOFDPI_ENGINE,
                              zapret_strategy=saved_strategy if saved_strategy in STRATEGIES else DEFAULT_STRATEGY,
                              startup_enabled=startup_enabled)
        self.state.automatic_updates = (self.config.get("automatic_updates") is True
                                        and automatic_install_ready())
        self.update_checker = UpdateChecker()
        self._update_cancel = threading.Event()
        self._update_token = 0
        self._update_check_manual = False
        self.update_finished.connect(self._finish_update_check)
        self.runner = runner or DNSRunner(log_callback=self.log)
        self.zapret = Zapret2Adapter()
        self.state.zapret_status = self.zapret.inspect().reason if platform == "linux" else ""
        self.window = None
        self._worker = None
        # The backend call can outlive a failed Quit attempt. A completion
        # signal is queued to Qt, so thread liveness is not its state marker.
        self._operation_done = threading.Event()
        self._operation_done.set()
        self._operation_token = 0
        self._shutting_down = False
        self._shutdown_complete = False
        self.log_arrived.connect(self._append_log)
        self.operation_finished.connect(self._finish_operation)
        self._poll_timer = QTimer(self)
        self._poll_timer.setInterval(1000)
        self._poll_timer.timeout.connect(self.poll_process)
        self._poll_timer.start()
        self.tray_available = tray_enabled and QSystemTrayIcon.isSystemTrayAvailable()
        self.tray = None
        self.tray_menu = None
        if self.tray_available:
            self.tray = QSystemTrayIcon(QIcon(str(resource_path("assets", "kervan-camel.png"))), self)
            self.tray.setToolTip(APP_NAME)
            self.tray_menu = QMenu()
            self.show_action = QAction(f"Show {APP_NAME}", self.tray_menu)
            self.quit_action = QAction(f"Quit {APP_NAME}", self.tray_menu)
            self.show_action.triggered.connect(self.show_window)
            self.quit_action.triggered.connect(self.quit_app)
            self.tray_menu.addAction(self.show_action)
            self.tray_menu.addAction(self.quit_action)
            self.tray.setContextMenu(self.tray_menu)
            self.tray.activated.connect(self._tray_activated)
            self.tray.show()

    def set_window(self, window):
        self.window = window
        self.state_changed.emit(self.state)

    @Slot(QSystemTrayIcon.ActivationReason)
    def _tray_activated(self, reason):
        if reason in (QSystemTrayIcon.ActivationReason.Trigger,
                      QSystemTrayIcon.ActivationReason.DoubleClick):
            self.show_window()

    @Slot()
    def show_window(self):
        if self._shutting_down or self.window is None:
            return
        self.window.showNormal()
        self.window.raise_()
        self.window.activateWindow()

    def hide_window(self):
        if self._shutting_down or self.window is None:
            return
        if self.tray_available:
            self.window.hide()
        else:
            self.quit_app()

    def log(self, message):
        # This signal may be emitted by DNSRunner's output reader thread.
        self.log_arrived.emit(str(message))

    @Slot(str)
    def _append_log(self, message):
        if self._shutting_down:
            return
        line = f"{datetime.now():%H:%M:%S}  {message}"
        self.state.messages.append(line)
        self.state_changed.emit(self.state)

    def _run_operation(self, name, operation):
        if not self._operation_done.is_set():
            raise RuntimeError("An engine operation is still running")
        self._operation_done.clear()
        self._operation_token += 1
        token = self._operation_token
        def work():
            try:
                operation()
                success, error = True, ""
            except Exception as exc:
                success, error = False, str(exc)
            finally:
                # Set this before delivery: the backend operation has ended
                # even if Python has not yet retired the worker thread.
                self._operation_done.set()
            self.operation_finished.emit(token, name, success, error)
        self._worker = threading.Thread(target=work, name=f"engine-{name}")
        try:
            self._worker.start()
        except Exception:
            self._operation_done.set()
            raise

    @Slot()
    def start(self):
        if (self._shutting_down or not self._operation_done.is_set() or
                self.state.phase not in (Phase.INACTIVE, Phase.ERROR)):
            return
        if self.state.platform == "linux" and self.state.linux_engine == ZAPRET_ENGINE:
            self.state.error = self.state.zapret_status
            self.state_changed.emit(self.state)
            return
        name = self.state.dns_provider
        address, port = DNS_PROVIDERS[name]
        self.state.phase = Phase.STARTING
        self.state.error = ""
        self.state_changed.emit(self.state)
        self.log(f"Starting service with {name} ({address}:{port})…")
        mode = self.state.spoofdpi_mode
        if self.state.platform == "linux":
            self._run_operation("start", lambda: self.runner.start(
                dns_addr=address, dns_port=port, spoofdpi_mode=mode))
        else:
            self._run_operation("start", lambda: self.runner.start(dns_addr=address, dns_port=port))

    @Slot()
    def stop(self):
        if (self._shutting_down or not self._operation_done.is_set() or
                self.state.phase != Phase.ACTIVE):
            return
        self.state.phase = Phase.STOPPING
        self.state_changed.emit(self.state)
        self.log("Stopping service…")
        self._run_operation("stop", self.runner.stop)

    @Slot(int, str, bool, str)
    def _finish_operation(self, token, name, success, error):
        if self._shutting_down:
            return
        if token != self._operation_token:
            # A failed bounded Quit invalidates the result but the controls
            # can become available again once its worker has really ended.
            if self._operation_done.is_set():
                self.state_changed.emit(self.state)
            return
        if self.state.phase != (Phase.STARTING if name == "start" else Phase.STOPPING):
            return
        if name == "start":
            self.state.phase = Phase.ACTIVE if success else Phase.ERROR
            if not success:
                self.state.error = error
                self.log(f"Error starting: {error}")
            else:
                self.log("Service active.")
        else:
            if success and self.runner.process is not None:
                success = False
                error = "The engine did not exit. Open Activity for details."
            self.state.phase = Phase.INACTIVE if success else Phase.ERROR
            if not success:
                self.state.error = error
                self.log(f"Error stopping: {error}")
            else:
                self.log("Service stopped.")
        self.state_changed.emit(self.state)

    @Slot()
    def poll_process(self):
        if self._shutting_down or self.state.phase != Phase.ACTIVE:
            return
        process = self.runner.process
        if process is not None and process.poll() is not None:
            self.runner.stop()
            self.state.phase = Phase.ERROR
            self.state.error = "The engine exited. Open Activity for details."
            self.log(self.state.error)
            self.state_changed.emit(self.state)

    def set_dns(self, provider):
        if (not self._operation_done.is_set() or
                self.state.phase not in (Phase.INACTIVE, Phase.ERROR) or
                provider not in DNS_PROVIDERS):
            return
        self.config.save_config("dns_provider", provider)
        self.state.dns_provider = provider
        self.state_changed.emit(self.state)

    def set_theme(self, theme):
        if theme not in ("System", "Light", "Dark"):
            return
        self.config.save_config("theme", theme)
        self.state.theme = theme
        self.state_changed.emit(self.state)

    def set_spoofdpi_mode(self, mode):
        if (self.state.platform != "linux" or
                self.state.phase not in (Phase.INACTIVE, Phase.ERROR) or
                self.runner.process is not None or
                not self._operation_done.is_set() or
                mode not in ("Normal", "Compatibility")):
            return
        self.config.save_config("spoofdpi_mode", mode)
        self.state.spoofdpi_mode = mode
        self.state_changed.emit(self.state)

    def set_linux_engine(self, engine):
        if (self.state.platform != "linux" or engine not in (SPOOFDPI_ENGINE, ZAPRET_ENGINE)
                or self.state.phase not in (Phase.INACTIVE, Phase.ERROR)
                or self.runner.process is not None
                or not self._operation_done.is_set()):
            return
        self.config.save_config("linux_engine", engine)
        self.state.linux_engine = engine
        self.state.error = ""
        self.state.phase = Phase.INACTIVE
        self.state.zapret_status = self.zapret.inspect().reason
        self.state_changed.emit(self.state)

    def set_zapret_strategy(self, strategy):
        if (self.state.platform != "linux" or strategy not in STRATEGIES
                or self.state.phase not in (Phase.INACTIVE, Phase.ERROR)
                or self.runner.process is not None
                or not self._operation_done.is_set()):
            return
        self.config.save_config("zapret_strategy", strategy)
        self.state.zapret_strategy = strategy
        self.state_changed.emit(self.state)

    def set_startup(self, enabled):
        try:
            startup.set_enabled(enabled)
        except Exception as exc:
            self.log(f"Could not change autostart: {exc}")
        else:
            self.state.startup_enabled = enabled
            self.log("Autostart enabled." if enabled else "Autostart disabled.")
        self.state_changed.emit(self.state)

    def set_activity_expanded(self, expanded):
        self.state.activity_expanded = expanded
        self.state_changed.emit(self.state)

    def set_automatic_updates(self, enabled):
        if type(enabled) is not bool or (enabled and not automatic_install_ready()):
            return
        self.config.save_config("automatic_updates", enabled)
        self.state.automatic_updates = enabled
        if not enabled and not self._update_check_manual:
            self._update_cancel.set()
            self._update_token += 1
            self.state.update_status = "idle"
            self.state.update_release = None
            self.state.update_message = ""
        self.state_changed.emit(self.state)

    def check_updates(self, manual=False):
        if self._shutting_down or self.state.update_status == "checking":
            return False
        if not manual:
            if self.state.platform != "windows" or not self.state.automatic_updates or not automatic_install_ready():
                return False
            last = self.config.get("update_last_check")
            if isinstance(last, (int, float)) and 0 <= time.time() - last < CHECK_INTERVAL:
                return False
        self._update_cancel = threading.Event()
        self._update_token += 1
        token, cancel = self._update_token, self._update_cancel
        self._update_check_manual = manual
        self.state.update_status = "checking"
        self.state.update_message = ""
        self.state_changed.emit(self.state)
        def work():
            try:
                result = self.update_checker.check(cancel=cancel)
            except Exception:
                result = CheckResult("error", message="Update check failed")
            if not cancel.is_set():
                self.update_finished.emit(token, result)
        threading.Thread(target=work, name="release-check", daemon=True).start()
        return True

    @Slot(int, object)
    def _finish_update_check(self, token, result):
        if self._shutting_down or token != self._update_token or result.status == "cancelled":
            return
        self._update_check_manual = False
        try:
            self.config.save_config("update_last_check", int(time.time()))
        except OSError:
            pass
        self.state.update_status = result.status
        self.state.update_message = result.message
        self.state.update_release = result.release
        self.state_changed.emit(self.state)

    def dismiss_update(self):
        if self.state.update_status == "available":
            self.state.update_status = "later"
            self.state_changed.emit(self.state)

    @Slot()
    def quit_app(self):
        if self.shutdown():
            QApplication.instance().quit()

    @Slot()
    def shutdown(self):
        if self._shutdown_complete:
            return True
        if self._shutting_down:
            return False
        self._shutting_down = True
        self._update_cancel.set()
        self._update_token += 1
        self._operation_token += 1
        self.state.phase = Phase.SHUTTING_DOWN
        self.state_changed.emit(self.state)
        self._poll_timer.stop()
        if self._worker and self._worker.is_alive() and self._worker is not threading.current_thread():
            self._worker.join(timeout=15)
        if self._worker and self._worker.is_alive():
            self._shutdown_failed("An engine operation is still running. Try Quit again.")
            return False
        try:
            self.runner.close()
        except Exception as exc:
            self._shutdown_failed(f"Could not finish engine cleanup: {exc}")
            return False
        if any(getattr(self.runner, name, None) is not None
               for name in ("process", "output_thread", "job_handle")):
            self._shutdown_failed("The engine still holds resources. Try Quit again.")
            return False
        self._shutdown_complete = True
        if self.tray is not None:
            self.tray.hide()
        return True

    def _shutdown_failed(self, message):
        self._shutting_down = False
        self.state.phase = Phase.ERROR
        self.state.error = message
        self.state_changed.emit(self.state)
        self.log(message)
        self._poll_timer.start()
        if self.window is not None:
            self.show_window()
