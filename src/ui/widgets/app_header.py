from PySide6.QtCore import Qt, QLocale
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton

from utils.paths import resource_path
from metadata import APP_NAME, DISPLAY_VERSION


class AppHeader(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("header")
        row = QHBoxLayout(self)
        row.setContentsMargins(4, 0, 4, 0)
        row.setSpacing(12)
        mark = QLabel()
        mark.setPixmap(QPixmap(str(resource_path("assets", "kervan-camel.png"))).scaled(
            36, 36, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        mark.setFixedSize(36, 36)
        mark.setAccessibleName(f"{APP_NAME} app mark")
        row.addWidget(mark)
        titles = QVBoxLayout()
        titles.setContentsMargins(0, 0, 0, 0)
        titles.setSpacing(0)
        title = QLabel(APP_NAME)
        title.setObjectName("title")
        version = QLabel(DISPLAY_VERSION)
        version.setObjectName("version")
        titles.addWidget(title)
        titles.addWidget(version)
        row.addLayout(titles, 1)
        turkish = QLocale.system().name().lower().startswith("tr")
        self.preferences_button = QPushButton("⚙  Tercihler" if turkish else "⚙  Preferences")
        self.preferences_button.setObjectName("link")
        self.preferences_button.setAccessibleName("Tercihler" if turkish else "Preferences")
        self.preferences_button.setMinimumHeight(40)
        row.addWidget(self.preferences_button)
        self.about_button = QPushButton("Hakkında" if turkish else "About")
        self.about_button.setObjectName("link")
        self.about_button.setAccessibleName(f"About {APP_NAME}")
        self.about_button.setMinimumSize(60, 40)
        row.addWidget(self.about_button)
        self.setMinimumHeight(54)
