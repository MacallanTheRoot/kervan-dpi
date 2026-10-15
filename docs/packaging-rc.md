# Phase 5 packaging validation

> Historical RC1 record. Its version and Windows icon/build descriptions do not describe the current Kervan DPI Windows candidate. See the [current Windows build guide](release/windows-build.md) and [Linux development guide](linux-development.md).

The current candidate is `1.0.1rc1`. The repository already has a
`v1.0.0` tag; this candidate does not create a release or tag. Identity is
defined in `src/metadata.py`. Debian maps `rc` to `~rc` so an eventual
final version sorts after the candidate. The desktop entry has no application
version field: its standardized `Version` key describes the desktop-entry
format, not this application's version.

## Artifact architecture

- Linux: PyInstaller onedir from `packaging/linux/goodbyedpi-turkey.spec`.
  The manual installer places it under `/opt/goodbyedpi-turkey`, links
  `/usr/local/bin/goodbyedpi-turkey`, and installs the desktop entry and
  hicolor PNG. `DESTDIR` supports rootless staging. The installer marks
  its own /opt tree and refuses an unrecognized tree or launcher. Its
  uninstaller preserves per-user XDG configuration and SpoofDPI.
- Debian/Kali: `packaging/debian/build_deb.sh` stages that same tree and
  creates `goodbyedpi-turkey_1.0.1~rc1_amd64.deb` without sudo.
  Debian packages use `/usr/bin` for their launcher. Remove a package
  installation with `apt remove goodbyedpi-turkey`.
- Windows: `packaging/windows/goodbyedpi-turkey.spec` produces one GUI
  executable, with the original app mark as a multi-resolution ICO, version
  metadata, PNG assets and the existing x86/x86_64 GoodbyeDPI/WinDivert
  trees. `build.bat` invokes that spec. It uses the current self-relaunch
  `ShellExecuteW("runas")` path and a non-elevating manifest. Startup
  arguments, including `--minimized`, are forwarded.
- Linux SpoofDPI v0.12.0 remains external. It is not bundled, downloaded,
  or declared as an apt dependency. The app gives an actionable missing
  executable error and remains inactive. It never changes system proxy
  settings.

The Linux bundle is tied to the shared-library baseline of the machine
that built it. Build on the oldest Debian/Kali generation intended for
distribution and validate on each target generation before release.

## TIFF warning

PyInstaller 6.16.0's standard PySide6.QtGui hook calls
`add_qt6_dependencies()`, which collects the Qt imageformats plugin set
before the spec can filter `libqtiff.so` from `Analysis.binaries`.
Binary dependency scanning therefore warns that the host lacks
`libtiff.so.5`, even though the final bundle excludes `libqtiff.so`.
The hook offers no plugin-specific `hooksconfig` option. Overriding the
standard QtGui hook would duplicate upstream hook behavior, so the
warning is retained and documented. PNG icon, xcb, Wayland, offscreen,
portal, and TLS support remain in the bundle. Do not install a TIFF
stack solely to silence this warning.

## Validation levels

A. Kali tests cover Linux runtime, Qt behavior, Windows argument/resource
   logic, and packaged output inspection.
B. `.github/workflows/ci.yml` defines Ubuntu and Windows tests/builds
   and uploads CI artifacts. It does not publish a release. A workflow
   definition is not evidence that CI has run successfully.
C. Native interactive Windows validation is still required. Check:

1. Onefile EXE launches and shows its icon/version.
2. One UAC prompt appears when not elevated; no repeated prompt.
3. GoodbyeDPI starts and the UI reports **Protection Active**.
4. Browsing works, then **Disable** stops GoodbyeDPI.
5. X hides to tray; left-click restores the same window; right-click
   exposes **Show** and **Quit**.
6. **Quit** from an active state reaps `goodbyedpi.exe`, releases
   WinDivert, closes streams/reader/Job Object, and emits no `_MEI`
   cleanup warning.
7. Repeat Quit when inactive and after unexpected child exit.
8. `--minimized` and the startup shortcut start hidden and preserve
   the UAC arguments.
9. Light, Dark and System themes work.
10. Review keyboard access and layout at 100%, 125%, 150% and 200%
    display scaling.

The opt-in `--self-test` harness runs only when
`GOODBYEDPI_PACKAGED_SMOKE=1` is also set. It is bounded, uses a
temporary-config-friendly path, does not change persistent proxy settings,
and is included only in the Linux test bundle. The Windows spec excludes it.
