from PySide6.QtCore import Qt, QLocale
from PySide6.QtGui import QPainter, QColor
from PySide6.QtWidgets import QCheckBox, QHBoxLayout, QLabel, QPushButton, QProgressBar, QWidget

from .common import card
from ui.tokens import COLORS
from ui.theme import resolve_theme
from .common import CompactComboBox
from app_state import Phase
from utils.zapret2 import STRATEGIES
from metadata import DISPLAY_VERSION


class Toggle(QCheckBox):
    """Accessible native checkbox with a Figma-sized painted switch."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.theme_choice = "System"
        self.setFixedSize(52, 40)
        self.setAccessibleName("Run on startup")
        self.setAccessibleDescription("Start the application minimized when you sign in")
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def paintEvent(self, event):
        colors = COLORS[resolve_theme(self.theme_choice)]
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(colors["accent/default"] if self.isChecked() else colors["bg/secondary"]))
        painter.drawRoundedRect(0, 5, 52, 30, 15, 15)
        painter.setBrush(QColor(colors["text/on-accent"] if self.isChecked() else colors["status/inactive"]))
        painter.drawEllipse(26 if self.isChecked() else 4, 9, 22, 22)
        if self.hasFocus():
            pen = painter.pen()
            pen.setColor(QColor(colors["focus/ring"]))
            pen.setWidth(2)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(1, 5, 50, 30, 15, 15)


class PreferencesCard:
    def __init__(self):
        self._tr = QLocale.system().name().lower().startswith("tr")
        self.widget, layout = card(margins=(18, 12, 18, 12))
        self.widget.setMinimumHeight(142)
        title = QLabel("Tercihler" if self._tr else "Preferences")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)
        startup_row = QWidget()
        startup_row.setObjectName("row")
        row = QHBoxLayout(startup_row)
        row.setContentsMargins(4, 0, 4, 0)
        row.addWidget(QLabel("Başlangıçta çalıştır" if self._tr else "Run on startup"))
        row.addStretch(1)
        self.startup = Toggle()
        row.addWidget(self.startup)
        layout.addWidget(startup_row)
        appearance_row = QWidget()
        appearance_row.setObjectName("row")
        appearance = QHBoxLayout(appearance_row)
        appearance.setContentsMargins(4, 0, 4, 0)
        appearance.addWidget(QLabel("Görünüm" if self._tr else "Appearance"))
        appearance.addStretch(1)
        self.theme = CompactComboBox()
        self.theme.addItems(("System", "Light", "Dark"))
        self.theme.setAccessibleName("Appearance theme")
        self.theme.setMinimumSize(116, 40)
        appearance.addWidget(self.theme)
        layout.addWidget(appearance_row)
        self.mode_row = QWidget()
        self.mode_row.setObjectName("row")
        mode_layout = QHBoxLayout(self.mode_row)
        mode_layout.setContentsMargins(4, 0, 4, 0)
        mode_layout.addWidget(QLabel("SpoofDPI modu" if self._tr else "SpoofDPI mode"))
        mode_layout.addStretch(1)
        self.spoofdpi_mode = CompactComboBox()
        self.spoofdpi_mode.addItems(("Normal", "Compatibility"))
        self.spoofdpi_mode.setAccessibleName("SpoofDPI mode")
        self.spoofdpi_mode.setAccessibleDescription(
            "Compatibility uses window size 4 when the local proxy next starts")
        self.spoofdpi_mode.setMinimumSize(150, 40)
        mode_layout.addWidget(self.spoofdpi_mode)
        layout.addWidget(self.mode_row)
        self.engine_row = QWidget()
        engine_layout = QHBoxLayout(self.engine_row)
        engine_layout.setContentsMargins(4, 0, 4, 0)
        engine_layout.addWidget(QLabel("Linux motoru" if self._tr else "Linux engine"))
        engine_layout.addStretch(1)
        self.linux_engine = CompactComboBox()
        self.linux_engine.addItems(("SpoofDPI — Proxy", "Zapret2 — Transparent (Experimental)"))
        self.linux_engine.setAccessibleName("Linux engine")
        self.linux_engine.setMinimumSize(225, 40)
        engine_layout.addWidget(self.linux_engine)
        layout.addWidget(self.engine_row)
        self.strategy_row = QWidget()
        strategy_layout = QHBoxLayout(self.strategy_row)
        strategy_layout.setContentsMargins(4, 0, 4, 0)
        strategy_layout.addWidget(QLabel("Araştırma stratejisi" if self._tr else "Research strategy"))
        strategy_layout.addStretch(1)
        self.zapret_strategy = CompactComboBox()
        self.zapret_strategy.addItems(STRATEGIES)
        self.zapret_strategy.setAccessibleName("Zapret2 research strategy")
        self.zapret_strategy.setMinimumSize(225, 40)
        strategy_layout.addWidget(self.zapret_strategy)
        layout.addWidget(self.strategy_row)
        self.zapret_notice = QLabel("Experimental · requires a privileged helper and approved native test")
        self.zapret_notice.setWordWrap(True)
        self.zapret_notice.setAccessibleName("Transparent mode availability")
        layout.addWidget(self.zapret_notice)
        update_title = QLabel("Güncellemeler" if self._tr else "Updates")
        update_title.setObjectName("sectionTitle")
        layout.addWidget(update_title)
        automatic_row = QWidget()
        automatic_layout = QHBoxLayout(automatic_row)
        automatic_layout.setContentsMargins(4, 0, 4, 0)
        self.automatic_label = QLabel()
        automatic_layout.addWidget(self.automatic_label)
        automatic_layout.addStretch(1)
        self.automatic_updates = Toggle()
        self.automatic_updates.setAccessibleName("Automatic Updates")
        self.automatic_updates.setAccessibleDescription(
            "Automatic installation is unavailable until signed Windows updates are ready")
        automatic_layout.addWidget(self.automatic_updates)
        layout.addWidget(automatic_row)
        self.automatic_notice = QLabel("Otomatik yükleme henüz kullanılamıyor." if self._tr else
                                       "Automatic installation is not available yet.")
        self.automatic_notice.setWordWrap(True)
        layout.addWidget(self.automatic_notice)
        self.update_current = QLabel(("Geçerli sürüm: " if self._tr else "Current version: ") + DISPLAY_VERSION)
        layout.addWidget(self.update_current)
        self.update_status = QLabel()
        self.update_status.setWordWrap(True)
        self.update_status.setAccessibleName("Update availability")
        layout.addWidget(self.update_status)
        self.update_progress = QProgressBar()
        self.update_progress.setAccessibleName("Update progress")
        self.update_progress.hide()
        layout.addWidget(self.update_progress)
        update_actions = QWidget()
        actions_layout = QHBoxLayout(update_actions)
        actions_layout.setContentsMargins(0, 0, 0, 0)
        self.check_updates = QPushButton("Güncellemeleri Denetle" if self._tr else "Check for Updates")
        self.open_release = QPushButton("Elle güncelle" if self._tr else "Update manually")
        self.release_notes = QPushButton("Sürüm notları" if self._tr else "Release notes")
        self.later = QPushButton("Daha sonra" if self._tr else "Later")
        for button in (self.check_updates, self.open_release, self.release_notes, self.later):
            actions_layout.addWidget(button)
        layout.addWidget(update_actions)
        layout.addStretch(1)

    def render(self, state):
        self.startup.theme_choice = state.theme
        self.startup.blockSignals(True)
        self.startup.setChecked(state.startup_enabled)
        self.startup.blockSignals(False)
        self.theme.blockSignals(True)
        self.theme.setCurrentText(state.theme)
        self.theme.blockSignals(False)
        linux = state.platform == "linux"
        transparent = linux and state.linux_engine == "Zapret2 — Transparent (Experimental)"
        self.mode_row.setVisible(linux and not transparent)
        self.engine_row.setVisible(linux)
        self.strategy_row.setVisible(transparent)
        self.zapret_notice.setVisible(transparent)
        self.zapret_notice.setText(state.zapret_status)
        self.linux_engine.blockSignals(True)
        self.linux_engine.setCurrentText(state.linux_engine)
        self.linux_engine.blockSignals(False)
        self.linux_engine.setEnabled(state.phase in (Phase.INACTIVE, Phase.ERROR))
        self.zapret_strategy.blockSignals(True)
        self.zapret_strategy.setCurrentText(state.zapret_strategy)
        self.zapret_strategy.blockSignals(False)
        self.zapret_strategy.setEnabled(state.phase in (Phase.INACTIVE, Phase.ERROR))
        self.spoofdpi_mode.blockSignals(True)
        self.spoofdpi_mode.setCurrentText(state.spoofdpi_mode)
        self.spoofdpi_mode.blockSignals(False)
        self.spoofdpi_mode.setEnabled(state.phase in (Phase.INACTIVE, Phase.ERROR))
        from utils.update_install import automatic_install_ready
        self.automatic_updates.theme_choice = state.theme
        self.automatic_updates.blockSignals(True)
        self.automatic_updates.setChecked(state.automatic_updates)
        self.automatic_updates.blockSignals(False)
        self.automatic_updates.setEnabled(automatic_install_ready())
        self.automatic_label.setText(("Otomatik Güncellemeler: " if self._tr else "Automatic Updates: ") +
                                     (("Açık" if self._tr else "On") if state.automatic_updates else
                                      ("Kapalı" if self._tr else "Off")))
        self.automatic_notice.setVisible(not automatic_install_ready())
        status = state.update_status
        if status == "available" and state.update_release:
            message = (("Yeni sürüm: " if self._tr else "New version: ") + state.update_release.version)
        elif status == "checking":
            message = "Denetleniyor…" if self._tr else "Checking…"
        elif status == "current":
            message = "Güncel sürüm." if self._tr else "Up to date."
        elif status == "later":
            message = "Güncelleme ertelendi." if self._tr else "Update deferred."
        elif status in ("offline", "error", "rate_limited", "unavailable"):
            if self._tr:
                message = {"offline": "GitHub Releases'e ulaşılamıyor.",
                           "rate_limited": "GitHub istek sınırına ulaşıldı.",
                           "unavailable": "Yeni sürüm için uyumlu Windows dosyası yok.",
                           "error": "Güncelleme denetimi başarısız."}[status]
            else:
                message = state.update_message or "Update check failed."
        else:
            message = "Güncelleme henüz denetlenmedi." if self._tr else "Updates not checked yet."
        self.update_status.setText(message)
        self.check_updates.setText("Güncellemeleri Denetle" if self._tr else "Check for Updates")
        self.check_updates.setEnabled(status != "checking")
        available = status == "available" and state.update_release is not None
        for button in (self.open_release, self.release_notes, self.later):
            button.setVisible(available)
