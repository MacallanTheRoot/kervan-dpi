# Kervan DPI

![Kervan DPI blue camel symbol](assets/kervan-camel.png)

**Yol Açık, Kervan Yürür.** · [Türkçe rehber](docs/README.tr.md)

Kervan DPI is an open-source desktop controller for tools that can help with DPI-related access restrictions. On Windows, it manages the bundled [GoodbyeDPI](https://github.com/ValdikSS/GoodbyeDPI) engine and [WinDivert](https://github.com/basil00/WinDivert). On Linux, it can manage a separately installed [SpoofDPI](https://github.com/xvzc/SpoofDPI) local HTTP proxy. The project was previously called **GoodbyeDPI Turkey**; its GitHub address and some configuration paths retain that name for compatibility.

> **Release status:** The Kervan DPI `1.0.1rc2` Windows candidate has **not** been published. The fix01 source was built and partially tested on Windows 11; the updated source here needs a fresh native build and complete QA. See the [release readiness record](docs/release/kervan-dpi-readiness.md).

## Platform status

| Platform | Current capability | Release status |
| --- | --- | --- |
| Windows 11 x64 | Bundled GoodbyeDPI and WinDivert | Fix01 branded EXE had partial real-device validation; the changed candidate needs a fresh build and complete native QA. |
| Other Windows versions | Windows source and build path | No native result for this candidate. |
| Debian/Kali Linux amd64 | Local SpoofDPI HTTP proxy, installed separately | Development stage. Browsers or other clients must explicitly select the proxy. |
| Linux transparent `nfqws2`/NFQUEUE | Experimental integration | Unreleased; no verified system-wide transparent bypass. |
| Android / iOS | Future roadmap | No downloadable application. |

## Features

- Enable/Disable control, DNS selection, status, activity log, system tray, light/dark theme, and optional startup shortcut.
- Windows engine files staged persistently under the existing `GoodbyeDPI-Turkey` engine path, with process cleanup on Quit.
- Linux SpoofDPI Normal and Compatibility proxy modes. Compatibility passes `-window-size 4`; results depend on the network.
- Preferences open from the header. **Automatic Updates** is Off and unavailable until signed installation and native Windows QA are complete. **Check for Updates** works independently and shows official stable releases only; use [manual update instructions](docs/release/windows-update.md).

## Windows download and use

The branded Windows EXE and portable ZIP are **not available yet**. Once a candidate has been built and tested, obtain it and its matching SHA-256 manifest from this project's [GitHub Releases](https://github.com/MacallanTheRoot/GoodbyeDPI-Turkey-GUI/releases). Historical assets there use the former name. Compare the published digest with `Get-FileHash .\Kervan-DPI.exe -Algorithm SHA256` before running the file. There is currently no installer or code-signed Kervan DPI executable.

For a future portable release, extract the ZIP into a folder you control and run `Kervan-DPI.exe`. Windows may ask for administrator permission through UAC because the engine uses WinDivert. Choose a DNS provider and select **Enable**. Select **Disable** to stop the engine. Closing the window hides it in the tray; choose **Show Kervan DPI** to reopen it or **Quit Kervan DPI** to stop an active engine and exit. Native behavior of the final branded EXE still requires verification.

Settings stay at `%APPDATA%\GoodbyeDPI-Turkey\config.json`. A new startup shortcut is named `Kervan DPI.lnk`; an existing `GoodbyeDPI-Turkey GUI.lnk` is retained. Check the shortcut target when upgrading, and consult the [migration and rollback guide](docs/release/windows-migration.md). No brand-related settings path migration or deletion is performed; a fresh profile can import a bundled legacy `config.json` without replacing an existing file.

## Security and limitations

Kervan DPI is not a VPN, anonymity service, or encrypted tunnel. It cannot promise access on every network. Windows uses administrator permission and a packet driver; review the UAC prompt. The branded EXE's icon, version properties, driver path, network behavior, and cleanup still need native verification. The [approved camel artwork record](docs/branding/kervan-camel-source.md) documents the icon export; redistribution rights are still a release gate.

Linux **Enable** starts a local HTTP proxy at `127.0.0.1:8080` only when SpoofDPI is installed. It does not change the system proxy, route, or firewall, and transparent NFQUEUE mode is not available. See the [Linux development and local proxy guide](docs/linux-development.md) and the [Nightshift validation report](docs/engineering/phase-7h-nightshift-final-report.md).

## Troubleshooting

- **UAC denied or Enable fails:** Review the activity log and permissions. Record the result using the [Windows QA checklist](docs/release/windows-qa-checklist.md). Do not delete WinDivert services or engine files without checking ownership.
- **A connection remains blocked:** Select **Disable**, then **Quit Kervan DPI** and retry ordinary HTTPS. Check the chosen DNS provider and any other proxy or filter on the machine. Report a reproducible failure through [GitHub Issues](https://github.com/MacallanTheRoot/GoodbyeDPI-Turkey-GUI/issues).
- **The window disappeared:** Open it from the system tray. Quit from the tray to exit completely.
- **Settings or startup changed:** Check `%APPDATA%\GoodbyeDPI-Turkey\config.json` and the target of the retained startup shortcut. Back up settings before upgrade tests.
- **Linux proxy does not work:** Check the separate SpoofDPI installation, the `127.0.0.1:8080` listener, and the client's proxy setting.

## Build from source

For Windows, use **Python 3.13 x64** with the `py` launcher on a real Windows host. In a fresh checkout with no existing `.venv`, build from the checked-in approved camel source:

```bat
py -3.13 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements-windows-rc.txt
build.bat
```

The expected output is `dist\Kervan-DPI.exe`; `build.bat` rejects unsupported Python versions and existing EXE output. The [Windows build and source-package instructions](docs/release/windows-build.md) describe the isolated RC handoff, checks, and native QA. For Linux development, see the [local proxy guide](docs/linux-development.md); a source test run is `QT_QPA_PLATFORM=offscreen .venv/bin/python -m unittest discover -s tests -q`.

## Contributing, license, and credits

Open an [issue](https://github.com/MacallanTheRoot/GoodbyeDPI-Turkey-GUI/issues) with OS/build, app version, reproduction steps, expected/actual behavior, and relevant redacted log entries. Changes to engine lifecycle or networking should include tests and native validation on the affected platform.

The application code and **original project shield** are covered by the repository's [MIT license](LICENSE). The new camel artwork has a recorded source but its redistribution rights have not yet been established. Bundled components keep their own licenses: see [third-party notices](THIRD_PARTY_NOTICES.md), `bin/licenses/`, `packaging/licenses/`, and the [Qt/PySide6 source and relinking record](docs/qt-lgpl-compliance.md). That Qt record describes the earlier RC1; corresponding sources for this candidate require separate review before publication.

Kervan DPI is developed by [MacallanTheRoot](https://github.com/MacallanTheRoot). Application metadata reads `Copyright (c) 2026 MacallanTheRoot`; it does not establish a code-signing identity. Windows engine integration also draws on [GoodbyeDPI Turkey](https://github.com/cagritaskn/goodbyedpi-turkey), based on [GoodbyeDPI](https://github.com/ValdikSS/GoodbyeDPI) and [WinDivert](https://github.com/basil00/WinDivert). Linux proxy support uses separately installed [SpoofDPI](https://github.com/xvzc/SpoofDPI); experimental transparent work explores [Zapret2](https://github.com/bol-van/zapret2). These are independent upstream projects.
