"""Small UI-facing snapshot; service state is never inferred from widgets."""
from dataclasses import dataclass, field
from enum import Enum


DNS_PROVIDERS = {
    "Turkey DNSRedir": ("77.88.8.8", "1253"),
    "Yandex (Standard)": ("77.88.8.8", "1253"),
    "Google": ("8.8.8.8", "53"),
    "Cloudflare": ("1.1.1.1", "53"),
    "OpenDNS": ("208.67.222.222", "53"),
}


class Phase(Enum):
    INACTIVE = "inactive"
    STARTING = "starting"
    ACTIVE = "active"
    STOPPING = "stopping"
    ERROR = "error"
    SHUTTING_DOWN = "shutting_down"


@dataclass
class AppState:
    platform: str
    phase: Phase = Phase.INACTIVE
    dns_provider: str = "Turkey DNSRedir"
    startup_enabled: bool = False
    theme: str = "System"
    spoofdpi_mode: str = "Normal"
    linux_engine: str = "SpoofDPI — Proxy"
    zapret_strategy: str = "TLS split (research)"
    zapret_status: str = ""
    activity_expanded: bool = False
    messages: list[str] = field(default_factory=list)
    error: str = ""
    automatic_updates: bool = False
    update_status: str = "idle"
    update_message: str = ""
    update_release: object = None

    @property
    def active(self):
        return self.phase == Phase.ACTIVE

    @property
    def heading(self):
        if self.platform == "linux" and self.linux_engine == "Zapret2 — Transparent (Experimental)":
            return "Transparent Mode Unavailable"
        prefix = "Protection" if self.platform == "windows" else "Local Proxy"
        return f"{prefix} {'Active' if self.active else 'Inactive'}"

    @property
    def detail(self):
        if self.platform == "linux" and self.linux_engine == "Zapret2 — Transparent (Experimental)":
            return self.zapret_status or "Native approval and a privileged helper are required."
        if self.phase == Phase.STARTING:
            return "Starting GoodbyeDPI…" if self.platform == "windows" else "Starting local proxy…"
        if self.phase == Phase.STOPPING:
            return "Stopping GoodbyeDPI…" if self.platform == "windows" else "Stopping local proxy…"
        if self.phase == Phase.ERROR:
            return self.error
        if self.platform == "windows":
            return ("GoodbyeDPI is running. DNS selection is locked while active." if self.active else
                    "GoodbyeDPI is ready. Select Enable to start protection.")
        return ("Applications must use 127.0.0.1:8080 to use this proxy." if self.active else
                "SpoofDPI is ready. Applications need to use the local proxy.")

    @property
    def backend_label(self):
        if self.platform == "windows":
            return "GoodbyeDPI · DNS redirection"
        return ("Zapret2 · transparent (experimental)" if
                self.linux_engine == "Zapret2 — Transparent (Experimental)" else
                "SpoofDPI · local HTTP proxy")
