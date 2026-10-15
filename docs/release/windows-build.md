# Kervan DPI 1.0.1rc2 — Windows build and distribution

Status: **Fix 03 source handoff in preparation**. The earlier fix01 branded EXE was built and partially tested on Windows 11; a Fix 02 native test found a locale-dependent test failure. This changed source has not been built or tested there. Build on a real Windows x64 host; Linux output is not a Windows release.

## Inputs and prerequisites

- **Python 3.13 x64** with the Windows `py` launcher, PowerShell, and internet or a reviewed local wheel cache for the Windows RC dependency file `requirements-windows-rc.txt` (shared PySide6/PyInstaller pins plus Windows signing-tool `cryptography==46.0.7` and resolved dependencies). The previous Windows run needed Python 3.13 after Python 3.15 dependency incompatibility. The candidate scripts check 3.13 x64 explicitly; they never use the machine's default Python.
- The approved blue camel PNG with the exact hash in [the artwork record](../branding/kervan-camel-source.md). Run `.venv\Scripts\python.exe packaging\generate_kervan_icon.py assets\kervan-camel-source.png` to recreate the transparent PNG and 16–256 px ICO. Inspect every size, Explorer, taskbar, UAC, tray, About/header and light/dark backgrounds. Do not substitute the old shield. Redistribution-rights evidence remains a publication gate.
- The checked-in GoodbyeDPI and WinDivert binaries for x86 and x64, notices, Qt license texts and corresponding source availability. See the [dependency inventory](windows-dependencies.md) and [exact engine input hashes](windows-engine-inputs.md). The build never replaces these binaries.

## Reproducible source handoff

From this checkout after the artwork is present:

```text
python tools/release/make_kervan_windows_rc_source.py --handoff fix03
```

This creates `dist/Kervan-DPI-1.0.1rc2-windows-rc-build-source-fix03.zip` and `dist/Kervan-DPI-1.0.1rc2-fix03-SOURCE-SHA256SUMS.txt`. The ZIP contains selected application source, Windows regression tests, artwork, unchanged engine binaries, notices, build scripts, QA instructions and `SOURCE-INPUTS-SHA256SUMS.txt`. The archive is deterministic for this source tree and the tool refuses to overwrite a differing existing archive or checksum file. It is a **source handoff**, not a Windows executable. Compare its SHA-256 after transfer and keep it outside the extracted directory.

## Native build

Extract the ZIP into a **fresh directory** on a native Windows x64 host. In that directory, open PowerShell as a normal user and run the prepared build:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File tools\windows\build_rc.ps1
```

Optionally pass `-SourceArchive C:\path\to\Kervan-DPI-1.0.1rc2-windows-rc-build-source-fix03.zip -ExpectedSourceSha256 <digest-from-SOURCE-SHA256SUMS.txt>` to record and verify the transferred archive. The source archive should stay outside the fresh extracted directory. `prepare_windows_native_test.bat` invokes the same script and keeps its console open.

The script refuses an existing `.venv`, `build` or `dist` path; it never removes or overwrites a prior environment. It checks Python 3.13 x64, verifies every extracted source file against the in-archive manifest, downloads Windows wheels to `dist\wheelhouse`, installs only from those captured wheels, records `pip freeze`, runs the included source tests offscreen, invokes `build.bat`, checks the frozen PyInstaller members, and creates the portable ZIP. A failing step stops the build and leaves logs/evidence for inspection. The script records `dist\Kervan-DPI-1.0.1rc2-windows-build.log`, `...-windows-requirements-resolved.txt`, and `...-windows-build-provenance.json` with OS/Python, input, wheel, engine, EXE and ZIP hashes. Retain the wheelhouse and provenance for reproduction; these are not automatically public release assets.

`build.bat` uses the dedicated Windows spec and emits `dist\Kervan-DPI.exe`. It rejects Python versions other than 3.13 x64, mismatched PySide6/PyInstaller pins and an existing EXE. The EXE metadata uses `MacallanTheRoot` for CompanyName and `Copyright (c) 2026 MacallanTheRoot` for LegalCopyright, product/file description `Kervan DPI`, original filename `Kervan-DPI.exe` and source version `1.0.1rc2`. This is file metadata, not an Authenticode publisher signature. The manifest does not request elevation; `src/main.py` uses one `runas` relaunch if needed. The frozen-content inspector compares the packaged EXE, DLL, driver, logo and notices byte for byte with the input tree; it does not exercise WinDivert.

`package_rc.ps1` checks Windows version resources and frozen contents, creates `Kervan-DPI-1.0.1rc2-windows-portable.zip`, verifies ZIP integrity and README links, then writes a SHA-256 manifest for the EXE and ZIP and an unsigned update manifest. It refuses to overwrite an existing package or manifest. There is **no installer workflow** in this repository. The portable ZIP contains the onefile EXE, English and Turkish guides, their linked local documentation and logo, and license notices at the paths referenced by the guides. It is not a system installation. Keep the executable in a stable user-controlled location if using autostart.

The Windows spec still bundles both engine architectures and keeps the Phase 7B persistent `Program Files\GoodbyeDPI-Turkey\engine\<hash>` staging and cleanup logic. The absolute engine EXE path starts beside its WinDivert DLL and driver, without changing the process's working directory or global DLL search path. The staged engine directory and WinDivert service must not be deleted by packaging or uninstall scripts. Perform [native QA](windows-qa-checklist.md) before considering publication. A successful build, CI run or static archive check is **not** network/lifecycle verification.

## Source and license gate

Before a public release, confirm that the Qt/PySide6, GoodbyeDPI and WinDivert source archives and their upstream hashes correspond to the binaries actually bundled. The previous [Qt source/relinking document](../qt-lgpl-compliance.md) describes the RC1 set; it must be checked and updated for this candidate. Carry the complete license inventory with the release. A checksum manifest alone does not prove publisher identity or native QA.

The [portable update contract and production signing procedure](windows-update.md) define release asset names, the detached signature and the automatic-installation blocker. A native build does not create a production signature or enable self-update.
