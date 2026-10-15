"""Single compact window composed from Figma section widgets."""
from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices, QIcon, QKeySequence, QShortcut
from PySide6.QtWidgets import (QApplication, QDialog, QHBoxLayout, QLabel, QMainWindow,
                               QMessageBox, QPushButton, QScrollArea, QVBoxLayout, QWidget)

from app_state import Phase
from metadata import (APP_NAME, APP_SLOGAN, COPYRIGHT, DISPLAY_VERSION,
                      LEGACY_APP_NAME, ORGANIZATION, PROJECT_URL)
from ui.theme import apply_theme
from ui.widgets.activity_panel import ActivityPanel
from ui.widgets.app_header import AppHeader
from ui.widgets.dns_card import DNSCard
from ui.widgets.preferences_card import PreferencesCard
from ui.widgets.status_card import StatusCard
from utils.paths import resource_path

class MainWindow(QMainWindow):
    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.setWindowTitle(APP_NAME)
        self.setWindowIcon(QIcon(str(resource_path("assets", "kervan-camel.png"))))
        self.resize(576, 720)
        self.setMinimumSize(520, 620)
        self._applied_theme = None
        self.quit_shortcut = QShortcut(QKeySequence("Ctrl+Q"), self)
        self.quit_shortcut.activated.connect(controller.quit_app)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        content = QWidget()
        content.setObjectName("content")
        column = QVBoxLayout(content)
        column.setContentsMargins(24, 24, 24, 24)
        column.setSpacing(14)
        self.header = AppHeader()
        self.status = StatusCard()
        self.dns = DNSCard()
        self.preferences = PreferencesCard()
        self.preferences_dialog = QDialog(self)
        self.preferences_dialog.setWindowTitle("Tercihler" if self.preferences._tr else "Preferences")
        self.preferences_dialog.setWindowIcon(self.windowIcon())
        self.preferences_dialog.resize(520, 580)
        self.preferences_dialog.setMinimumSize(420, 400)
        dialog_layout = QVBoxLayout(self.preferences_dialog)
        dialog_layout.setContentsMargins(16, 16, 16, 16)
        dialog_layout.setSpacing(12)
        preferences_scroll = QScrollArea()
        preferences_scroll.setWidgetResizable(True)
        preferences_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        preferences_scroll.setWidget(self.preferences.widget)
        dialog_layout.addWidget(preferences_scroll)
        self.close_preferences_button = QPushButton("Kapat" if self.preferences._tr else "Close")
        self.close_preferences_button.setObjectName("secondary")
        self.close_preferences_button.setMinimumSize(90, 40)
        close_row = QHBoxLayout()
        close_row.addStretch(1)
        close_row.addWidget(self.close_preferences_button)
        dialog_layout.addLayout(close_row)
        self.close_preferences_button.clicked.connect(self.preferences_dialog.reject)
        self.activity = ActivityPanel()
        self.footer = QWidget()
        self.footer.setObjectName("footer")
        footer_row = QHBoxLayout(self.footer)
        footer_row.setContentsMargins(0, 0, 0, 0)
        footer_row.setSpacing(2)
        self.github_button = QPushButton("GitHub")
        self.github_button.setObjectName("link")
        self.github_button.setAccessibleName("Open project on GitHub")
        self.footer_about_button = QPushButton("·  Hakkında" if self.preferences._tr else "·  About")
        self.footer_about_button.setObjectName("link")
        self.footer_about_button.setAccessibleName(f"About {APP_NAME}")
        footer_row.addWidget(self.github_button)
        footer_row.addWidget(self.footer_about_button)
        footer_row.addStretch(1)
        version = QLabel(DISPLAY_VERSION)
        version.setObjectName("footerVersion")
        footer_row.addWidget(version)
        self.footer.setMinimumHeight(24)
        for section in (self.header, self.status.widget, self.dns.widget,
                        self.activity.widget, self.footer):
            column.addWidget(section)
        column.addStretch(1)
        scroll.setWidget(content)
        self.setCentralWidget(scroll)

        self.header.about_button.clicked.connect(self.open_about)
        self.header.preferences_button.clicked.connect(self.open_preferences)
        self.status.action.clicked.connect(self._primary_action)
        self.dns.selector.currentTextChanged.connect(controller.set_dns)
        self.preferences.startup.toggled.connect(controller.set_startup)
        self.preferences.theme.currentTextChanged.connect(controller.set_theme)
        self.preferences.spoofdpi_mode.currentTextChanged.connect(controller.set_spoofdpi_mode)
        self.preferences.linux_engine.currentTextChanged.connect(controller.set_linux_engine)
        self.preferences.zapret_strategy.currentTextChanged.connect(controller.set_zapret_strategy)
        self.preferences.automatic_updates.toggled.connect(controller.set_automatic_updates)
        self.preferences.check_updates.clicked.connect(lambda: controller.check_updates(manual=True))
        self.preferences.open_release.clicked.connect(self._open_update_release)
        self.preferences.release_notes.clicked.connect(self._open_update_release)
        self.preferences.later.clicked.connect(controller.dismiss_update)
        self.activity.button.clicked.connect(self._toggle_activity)
        self.github_button.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(PROJECT_URL)))
        self.footer_about_button.clicked.connect(self.open_about)
        controller.state_changed.connect(self.render)
        QApplication.instance().styleHints().colorSchemeChanged.connect(self._system_theme_changed)
        self.render(controller.state)
        QWidget.setTabOrder(self.header.preferences_button, self.header.about_button)
        QWidget.setTabOrder(self.header.about_button, self.status.action)
        QWidget.setTabOrder(self.status.action, self.dns.selector)
        QWidget.setTabOrder(self.dns.selector, self.activity.button)
        QWidget.setTabOrder(self.activity.button, self.github_button)
        QWidget.setTabOrder(self.github_button, self.footer_about_button)

    def _primary_action(self):
        if self.controller.state.phase == Phase.ACTIVE:
            self.controller.stop()
        else:
            self.controller.start()

    def open_preferences(self):
        self.preferences_dialog.show()
        self.preferences_dialog.raise_()
        self.preferences_dialog.activateWindow()

    def _toggle_activity(self):
        self.controller.set_activity_expanded(not self.controller.state.activity_expanded)

    def _open_update_release(self):
        release = self.controller.state.update_release
        if release is not None and self.controller.state.update_status == "available":
            from utils.updates import safe_release_url
            if safe_release_url(release.notes_url):
                QDesktopServices.openUrl(QUrl(release.notes_url))

    def _system_theme_changed(self, _scheme):
        if self.controller.state.theme == "System":
            apply_theme("System")
            self.preferences.startup.update()

    def render(self, state):
        if state.theme != self._applied_theme:
            apply_theme(state.theme)
            self._applied_theme = state.theme
        self.status.render(state)
        self.status.action.setEnabled(self.status.action.isEnabled() and
                                      self.controller._operation_done.is_set())
        self.dns.selector.setProperty("themeChoice", state.theme)
        self.preferences.theme.setProperty("themeChoice", state.theme)
        self.dns.render(state)
        self.preferences.render(state)
        self.preferences.spoofdpi_mode.setEnabled(
            state.platform == "linux" and state.linux_engine == "SpoofDPI — Proxy"
            and state.phase in (Phase.INACTIVE, Phase.ERROR)
            and self.controller.runner.process is None
            and self.controller._operation_done.is_set())
        self.preferences.linux_engine.setEnabled(
            state.platform == "linux" and state.phase in (Phase.INACTIVE, Phase.ERROR)
            and self.controller.runner.process is None
            and self.controller._operation_done.is_set())
        self.preferences.zapret_strategy.setEnabled(
            state.platform == "linux" and state.phase in (Phase.INACTIVE, Phase.ERROR)
            and self.controller.runner.process is None
            and self.controller._operation_done.is_set())
        self.activity.render(state)
        self.preferences.startup.update()

    def open_about(self):
        backend = self.controller.state.backend_label
        QMessageBox.about(self, f"About {APP_NAME}",
                          f"{APP_NAME} · {DISPLAY_VERSION}\n{APP_SLOGAN}\n\n"
                          f"Developed by {ORGANIZATION}\n{COPYRIGHT}\n\n"
                          f"Formerly {LEGACY_APP_NAME}.\nBackend: {backend}\n\n"
                          f"Project: {PROJECT_URL}")

    def closeEvent(self, event):
        self.preferences_dialog.hide()
        if self.controller._shutting_down:
            event.accept()
        else:
            event.ignore()
            self.controller.hide_window()
