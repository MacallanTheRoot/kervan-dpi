"""Qt application entry point; backend and presentation live in separate modules."""
import ctypes
import os
import subprocess
import sys

from PySide6.QtCore import QTimer
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from app_controller import AppController
from metadata import APP_NAME, ORGANIZATION, VERSION
from ui.views.main_window import MainWindow
from utils.paths import resource_path


def is_admin():
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except (AttributeError, OSError):
        return False


def main(argv=None):
    argv = sys.argv if argv is None else argv
    if os.name == "nt" and not is_admin():
        arguments = argv[1:] if getattr(sys, "frozen", False) else [os.path.abspath(argv[0]), *argv[1:]]
        result = ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, subprocess.list2cmdline(arguments), None, 1)
        if result <= 32:
            raise OSError(f"Elevation was declined or failed ({result})")
        return 0

    app = QApplication(argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName(ORGANIZATION)
    app.setApplicationVersion(VERSION)
    brand_icon = resource_path("assets", "kervan-camel.png")
    if brand_icon.is_file():
        app.setWindowIcon(QIcon(str(brand_icon)))
    app.setQuitOnLastWindowClosed(False)
    controller = AppController()
    window = MainWindow(controller)
    controller.set_window(window)
    app.aboutToQuit.connect(controller.shutdown)
    if "--minimized" in argv:
        QTimer.singleShot(0, controller.start)
        if controller.tray_available:
            controller.log("Launched from startup.")
        else:
            window.show()
            controller.log("System tray unavailable; opened the window instead.")
    else:
        window.show()
    QTimer.singleShot(0, controller.check_updates)
    if "--self-test" in argv and os.environ.get("GOODBYEDPI_PACKAGED_SMOKE") == "1":
        from packaged_smoke import PackagedSmoke
        window._smoke = PackagedSmoke(app, controller, window, "--minimized" in argv)
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
