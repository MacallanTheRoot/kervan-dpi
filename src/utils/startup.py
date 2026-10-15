"""User-level autostart for Windows and freedesktop Linux desktops."""
import os
import subprocess
import sys
from pathlib import Path

from metadata import APP_NAME


def startup_path(platform_name=None, environ=None, home=None):
    platform_name = platform_name or sys.platform
    environ = os.environ if environ is None else environ
    home = Path.home() if home is None else Path(home)
    if platform_name == "win32":
        current, legacy = _windows_shortcut_paths(environ, home)
        return legacy if legacy.exists() else current
    if platform_name != "linux":
        raise NotImplementedError(f"Autostart for {platform_name} is unsupported")
    config_home = Path(environ.get("XDG_CONFIG_HOME") or home / ".config")
    return config_home / "autostart/goodbyedpi-turkey.desktop"


def _windows_shortcut_paths(environ, home):
    appdata = Path(environ.get("APPDATA") or home / "AppData/Roaming")
    folder = appdata / "Microsoft/Windows/Start Menu/Programs/Startup"
    return folder / "Kervan DPI.lnk", folder / "GoodbyeDPI-Turkey GUI.lnk"


def is_enabled(platform_name=None, environ=None, home=None):
    if (platform_name or sys.platform) == "win32":
        environ = os.environ if environ is None else environ
        home = Path.home() if home is None else Path(home)
        return any(path.exists() for path in _windows_shortcut_paths(environ, home))
    return startup_path(platform_name, environ, home).exists()


def _launch_command(platform_name=None):
    platform_name = platform_name or sys.platform
    if getattr(sys, "frozen", False):
        return sys.executable, "--minimized"
    executable = sys.executable
    if platform_name == "win32":
        windowless = executable.replace("python.exe", "pythonw.exe")
        if Path(windowless).exists():
            executable = windowless
    return executable, f'"{Path(__file__).resolve().parents[1] / "main.py"}" --minimized'


def set_enabled(enabled: bool, platform_name=None, environ=None, home=None):
    platform_name = platform_name or sys.platform
    environ = os.environ if environ is None else environ
    home = Path.home() if home is None else Path(home)
    path = startup_path(platform_name, environ, home)
    if not enabled:
        if platform_name == "win32":
            for shortcut in _windows_shortcut_paths(environ, home):
                shortcut.unlink(missing_ok=True)
        else:
            path.unlink(missing_ok=True)
        return
    if platform_name == "win32" and all(
            shortcut.exists() for shortcut in _windows_shortcut_paths(environ, home)):
        raise RuntimeError("Both legacy and Kervan DPI startup shortcuts exist; resolve the duplicate first")
    path.parent.mkdir(parents=True, exist_ok=True)
    executable, arguments = _launch_command(platform_name)
    if platform_name == "win32":
        def quote(value):
            return "'" + str(value).replace("'", "''") + "'"
        script = (
            "$s=(New-Object -ComObject WScript.Shell).CreateShortcut(" + quote(path) + ");"
            "$s.TargetPath=" + quote(executable) + ";"
            "$s.Arguments=" + quote(arguments) + ";"
            "$s.Description=" + quote(APP_NAME) + ";$s.Save()"
        )
        subprocess.run(["powershell", "-NoProfile", "-Command", script], check=True)
    else:
        def desktop_quote(value):
            # Desktop Entry Exec syntax uses double quotes and backslash escapes.
            return '"' + str(value).replace('\\', '\\\\').replace('"', '\\"').replace('$', '\\$').replace('`', '\\`').replace('%', '%%') + '"'
        if getattr(sys, "frozen", False):
            command = desktop_quote(executable)
        else:
            source = Path(__file__).resolve().parents[1] / "main.py"
            command = f"{desktop_quote(executable)} {desktop_quote(source)}"
        path.write_text(
            f"[Desktop Entry]\nType=Application\nName={APP_NAME}\n"
            f"Exec={command} --minimized\nTerminal=false\n"
            "X-GNOME-Autostart-enabled=true\n", encoding="utf-8")
