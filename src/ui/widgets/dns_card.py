from PySide6.QtWidgets import QLabel

from app_state import DNS_PROVIDERS, Phase
from .common import card, CompactComboBox


class DNSCard:
    def __init__(self):
        self.widget, layout = card()
        self.widget.setMinimumHeight(144)
        title = QLabel("DNS & backend")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)
        self.selector = CompactComboBox()
        self.selector.addItems(DNS_PROVIDERS)
        self.selector.setMinimumHeight(42)
        self.selector.setAccessibleName("DNS provider")
        self.selector.setAccessibleDescription("Choose the DNS provider used when the backend next starts")
        layout.addWidget(self.selector)
        self.backend = QLabel()
        self.backend.setObjectName("backend")
        layout.addWidget(self.backend)
        layout.addStretch(1)

    def render(self, state):
        self.selector.blockSignals(True)
        self.selector.setCurrentText(state.dns_provider)
        self.selector.blockSignals(False)
        self.selector.setEnabled(state.phase in (Phase.INACTIVE, Phase.ERROR) and
                                 not (state.platform == "linux" and
                                      state.linux_engine == "Zapret2 — Transparent (Experimental)"))
        self.backend.setText(state.backend_label)
