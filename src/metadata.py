"""Display branding and stable distribution identities."""

APP_NAME = "Kervan DPI"
PARENT_BRAND = "Kervan"
APP_SLOGAN = "Yol Açık, Kervan Yürür."
LEGACY_APP_NAME = "GoodbyeDPI Turkey"
APP_DESCRIPTION = ("Open-source, user-controlled desktop access tool for "
                   "DPI-related network restrictions")
# These technical identifiers remain stable until a separately tested migration.
EXECUTABLE_NAME = "Kervan-DPI"
LINUX_COMMAND = "goodbyedpi-turkey"
DESKTOP_ID = "goodbyedpi-turkey.desktop"
PROJECT_URL = "https://github.com/MacallanTheRoot/GoodbyeDPI-Turkey-GUI"
ORGANIZATION = "MacallanTheRoot"
MAINTAINER = "MacallanTheRoot <hamzaefesahinbas@protonmail.com>"
COPYRIGHT = "Copyright (c) 2026 MacallanTheRoot"

# v1.0.0 is an existing repository tag. Keep this successor explicitly pre-release.
VERSION = "1.0.1rc2"
DISPLAY_VERSION = f"v{VERSION}"
DEBIAN_VERSION = VERSION.replace("rc", "~rc")
WINDOWS_FILE_VERSION = tuple(int(part) for part in VERSION.split("rc")[0].split(".")) + (0,)
