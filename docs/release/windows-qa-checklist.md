# Kervan DPI Windows RC native QA checklist

Run this matrix on the **exact final branded native Windows build**, preferably in a disposable Windows 11 x64 profile with an old GoodbyeDPI Turkey installation available for upgrade tests. The earlier 18/18 Windows result belongs to a prebranding build and does not pass this candidate. Record results in the [native report template](windows-native-qa-report-template.md). Do not run this matrix from Kali Linux or against a real profile without its owner's authorization.

Before testing, record the Windows edition/build/architecture, Python 3.13 and tool versions, source ZIP/EXE/portable SHA-256 values, old EXE identity, configuration backup/hash, startup shortcut targets, engine staging directory and WinDivert service/driver state. Use `tools/windows/validate_rc.ps1` for read-only before/after snapshots. A service record alone is not evidence of a leak; inspect the path and state. Do not force-stop or delete a possibly shared service.

| ID | Native scenario and pass condition | Result / evidence |
| --- | --- | --- |
| W01 | First launch: EXE identity/version/icon, UAC flow, window, tray and inactive state; inspect 16/24/32/48/64/128/256 px icons at ordinary and high DPI, light and dark surfaces. | PENDING |
| W02 | Enable and Disable once; inspect `goodbyedpi.exe`, adjacent WinDivert DLL/driver and persistent `%ProgramFiles%\GoodbyeDPI-Turkey\engine\<hash>` image path, then confirm engine process exits. | PENDING |
| W03 | Enable → immediate Quit **10 separate launches**; each time confirm no lingering app/engine process, `_MEI` cleanup warning or loss of ordinary HTTPS. | PENDING |
| W04 | Enable → wait **15 seconds** → Quit **3 separate launches**; make the same cleanup and connectivity checks. | PENDING |
| W05 | Disable → Quit **3 separate launches**; confirm clean exit and ordinary HTTPS. | PENDING |
| W06 | Reopen → Enable after the Quit loops; confirm one functioning engine process, then Disable and Quit. | PENDING |
| W07 | Check Discord connectivity while active; record the exact service/action and result. | PENDING |
| W08 | Check an ordinary HTTPS site while active; record URL, result and baseline. | PENDING |
| W09 | Quit while active and confirm ordinary internet/HTTPS access afterward. | PENDING |
| W10 | Confirm no `_MEI` temporary-directory cleanup warning in each critical Quit case. | PENDING |
| W11 | Confirm no lingering Kervan DPI or GoodbyeDPI process. Record WinDivert service state and driver path without deleting a shared service. | PENDING |
| W12 | Restart and verify configuration persistence, unknown keys and backup hash; inspect old settings before and after without deleting them. | PENDING |
| W13 | Test legacy upgrade and rollback using the [migration plan](windows-migration.md): retained config, old/new EXE coexistence, one startup shortcut and old EXE rollback. | PENDING |
| W14 | Inspect application window, tray, About, notifications if any, file properties, Start Menu/desktop shortcuts if present and legacy startup shortcut target/description. | PENDING |
| W15 | Extract the portable ZIP into a stable user-controlled directory; verify checksum, local docs/licenses, launch, Enable/Disable/Quit and a second launch. | PENDING |
| W16 | Installer upgrade/uninstall: **N/A** for this candidate because no installer or uninstaller is shipped. For portable removal, delete only the selected test EXE/ZIP and verify config, unrelated shortcuts and engine staging remain. | PENDING |
| W17 | Record observed Windows Defender/SmartScreen prompts or detections factually, including product/version and exact artifact hash. Do not suggest bypass or claim code signing. | PENDING |

Also inspect packaged x86/x64 engine resources, Qt plugins, notices, version fields and EXE/ZIP hashes against the Windows checksum manifest. Record every row as PASS, FAIL or N/A with a reason and exact evidence. W01–W15 (except surfaces genuinely absent from the application) and W17 must be resolved before release readiness can become YES. Native networking, upgrade and rollback remain **PENDING** until this matrix is run on Windows. A successful build or static inspection does not satisfy it.

## Update QA for this changed source

Use the [update contract](windows-update.md). Automatic installation remains **BLOCKED** until a production publisher key, trusted after-exit helper and separate native QA exist.

### Fix 04 UI and lifecycle spot checks

Run these on the EXE built from the Fix 04 source archive. Record a screenshot or exact observation for each result.

| ID | Native scenario and pass condition | Result / evidence |
| --- | --- | --- |
| F04-01 | At normal and 125%/150% scaling, Preferences is visible in the upper-right header beside About; click it, close with Close, reopen, then close with Escape. | PENDING |
| F04-02 | The main screen shows status, DNS and activity without an expanded Preferences card; resize to the minimum window size and check for clipped controls. | PENDING |
| F04-03 | In English and Turkish, Updates shows Automatic Updates Off and Check for Updates with no release-channel selector; the disabled automatic switch explains that installation is unavailable. | PENDING |
| F04-04 | With Automatic Updates Off, launch makes no automatic release request. Click Check for Updates and confirm a stable release result, notes link when available, and a usable retry after an error. | PENDING |
| F04-05 | With the engine active, close Preferences, hide and reopen the main window, then Disable and Quit. Confirm no lingering app or engine process and ordinary HTTPS access. | PENDING |

Keep automatic EXE replacement blocked. Record native Windows security results and production signing separately before considering an installer-enabled build.

| ID | Native scenario and pass condition | Result / evidence |
| --- | --- | --- |
| U01 | Off makes no automatic GitHub request at launch; manual Check now works only when clicked. | PENDING |
| U02 | Preferences open and close from the header; Automatic Updates stays Off while gated, legacy modes migrate safely, and manual checking works independently. | PENDING |
| U03 | A newer supported release appears once with a trusted notes link; current/older releases do not claim an update. | PENDING |
| U04 | Offline, 403/429, 404, malformed and missing asset responses show accurate errors; retry remains usable. | PENDING |
| U05 | Quit during a slow check remains responsive and leaves no GUI/process or network worker effect after exit. | PENDING |
| U06 | Final build includes expected update dependency and source tests; EXE, ZIP, checksums and unsigned manifest match provenance. | PENDING |
| U07 | Future production auto-install: signed download, active engine shutdown, replacement, failed restart and rollback in a disposable user-writable location. | BLOCKED |
