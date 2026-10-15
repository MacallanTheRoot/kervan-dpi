from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton

from app_state import Phase
from .common import card


class StatusCard:
    def __init__(self):
        self.widget, layout = card(margins=(20, 20, 20, 8), spacing=0)
        self.widget.setMinimumHeight(176)
        badge_row = QHBoxLayout()
        badge_row.setContentsMargins(0, 0, 0, 0)
        badge_row.setSpacing(8)
        self.dot = QLabel("●")
        self.dot.setObjectName("statusDot")
        self.badge = QLabel("INACTIVE")
        self.badge.setObjectName("badge")
        badge_row.addWidget(self.dot)
        badge_row.addWidget(self.badge)
        badge_row.addStretch(1)
        layout.addLayout(badge_row)
        layout.addSpacing(14)
        self.heading = QLabel()
        self.heading.setObjectName("statusHeading")
        self.heading.setWordWrap(True)
        layout.addWidget(self.heading)
        self.detail = QLabel()
        self.detail.setObjectName("detail")
        self.detail.setWordWrap(True)
        self.detail.setMinimumHeight(20)
        layout.addWidget(self.detail)
        layout.addSpacing(10)
        self.action = QPushButton("Enable")
        self.action.setObjectName("primary")
        self.action.setAccessibleName("Enable local proxy")
        self.action.setFixedWidth(160)
        self.action.setMinimumHeight(44)
        layout.addWidget(self.action)
        layout.addStretch(1)

    def render(self, state):
        phase = state.phase
        status = ("active" if phase == Phase.ACTIVE else "error" if phase == Phase.ERROR else
                  "starting" if phase == Phase.STARTING else "stopping" if phase == Phase.STOPPING else "inactive")
        self.badge.setText(status.upper() if status != "error" else "ERROR")
        for item in (self.dot, self.badge):
            item.setProperty("status", status)
            item.style().unpolish(item)
            item.style().polish(item)
        self.heading.setText(state.heading)
        self.detail.setText(state.detail)
        self.detail.setProperty("error", "true" if phase == Phase.ERROR else "false")
        self.detail.style().unpolish(self.detail)
        self.detail.style().polish(self.detail)
        self.detail.setAccessibleDescription(state.detail)
        self.action.setText("Disable" if phase == Phase.ACTIVE else
                            "Starting…" if phase == Phase.STARTING else
                            "Stopping…" if phase == Phase.STOPPING else "Enable")
        self.action.setObjectName("secondary" if phase == Phase.ACTIVE else "primary")
        self.action.style().unpolish(self.action)
        self.action.style().polish(self.action)
        unavailable = (state.platform == "linux" and
                       state.linux_engine == "Zapret2 — Transparent (Experimental)")
        self.action.setEnabled(phase in (Phase.INACTIVE, Phase.ACTIVE, Phase.ERROR)
                               and not unavailable)
        target = "protection" if state.platform == "windows" else "local proxy"
        self.action.setAccessibleName("Transparent mode unavailable" if unavailable else
                                      f"{'Disable' if phase == Phase.ACTIVE else 'Enable'} {target}")
