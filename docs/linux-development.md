# Linux development and local proxy guide

Linux support is in development. The current GUI can start a **separately installed SpoofDPI v0.12.0 local HTTP proxy** on Debian/Kali amd64. Browsers and other applications must explicitly use `127.0.0.1:8080`; the GUI does not configure their proxy settings. Experimental Zapret2/`nfqws2`/NFQUEUE transparent integration is **unreleased and not verified as a system-wide bypass**. Android and iOS have no downloadable build.

## Build and run

Use the GUI as a normal desktop user. A manual Linux installation requires `sudo`; the proxy itself does not. On the target Debian/Kali generation:

```bash
sudo apt install python3 python3-venv binutils
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python src/main.py
./build_linux.sh
```

For a manual installation, run `sudo packaging/linux/install.sh` after the onedir build, then launch `goodbyedpi-turkey`. For a Debian package, run `packaging/debian/build_deb.sh` after the onedir build and install the resulting `dist/goodbyedpi-turkey_<version>_amd64.deb` with `sudo apt install ./dist/<file>.deb`. The package and manual installer use the existing `goodbyedpi-turkey` command and paths. **Do not mix the two installation methods.** The installer does not fetch SpoofDPI.

The Linux binary bundle inherits its build host's shared-library baseline. Build on the oldest Debian/Kali generation you intend to support and validate on each target. Neither a local build nor a passing headless test suite establishes a public Linux release.

## Separate SpoofDPI engine

The CLI integration targets SpoofDPI v0.12.0. With a suitable Go installation, a user can build that version from its [independent upstream project](https://github.com/xvzc/SpoofDPI):

```bash
go install github.com/xvzc/SpoofDPI/cmd/spoofdpi@v0.12.0
~/go/bin/spoofdpi -help
```

Review upstream source and license before installing. The GUI searches `spoof-dpi` or `spoofdpi` in `PATH`, `~/.spoof-dpi/bin`, `~/go/bin`, `/usr/local/bin`, `/usr/bin`, and `/opt/goodbyedpi-turkey/bin`. If none is executable, **Enable** reports the missing engine. The application does not download or bundle it.

Choose **Normal** or **Compatibility** in the GUI. Compatibility adds `-window-size 4`; the selected DNS address and port are passed as standard DNS parameters, not DoH. Enable starts the local proxy on `127.0.0.1:8080` and rejects an already occupied port. Configure the browser or client to use that HTTP proxy. **Disable** or tray **Quit** stops the process. Use the activity log if startup fails. Desktop tray behavior, especially under Wayland, still needs local visual validation.

## Existing paths and removal

- Manual installation: `/opt/goodbyedpi-turkey/`, `/usr/local/bin/goodbyedpi-turkey`, desktop entry `goodbyedpi-turkey.desktop`, and the existing Linux icon path.
- Debian package: the same onedir application, with a launcher under `/usr/bin` and package identity `goodbyedpi-turkey`.
- Settings: `$XDG_CONFIG_HOME/goodbyedpi-turkey/config.json`, defaulting to `~/.config/goodbyedpi-turkey/config.json`.
- Optional startup: `$XDG_CONFIG_HOME/autostart/goodbyedpi-turkey.desktop`, defaulting to `~/.config/autostart/goodbyedpi-turkey.desktop`.

Remove a Debian installation with `sudo apt remove goodbyedpi-turkey`; remove a manual installation with `sudo packaging/linux/uninstall.sh`. Both preserve user settings and the separately installed SpoofDPI program. The manual installer refuses to overwrite an unrecognized `/opt` tree, and its uninstaller refuses to remove one.

For older packaging details and the Qt TIFF warning, see the [Phase 5 packaging record](packaging-rc.md). For the current experimental transparent work and its unverified native privileged status, see the [Nightshift final report](engineering/phase-7h-nightshift-final-report.md).
