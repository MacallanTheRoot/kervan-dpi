# Windows portable update contract (1.0.1rc2 development)

The application checks only official stable releases from `MacallanTheRoot/GoodbyeDPI-Turkey-GUI`; drafts and prereleases, including RCs, are ignored. **Automatic Updates** means automatic installation and defaults to **Off**. The toggle is unavailable until signed installation and native Windows QA are complete, so startup makes no update request. **Check for Updates** is an independent, asynchronous one-time request. No account, machine identifier, telemetry, or update analytics are sent. The local config records only the last check timestamp and preferences. GitHub receives an ordinary unauthenticated API request when the user checks.

Release discovery is not proof of publisher identity. The UI shows only releases with supported version tags, the exact repository release page, and an uploaded `Kervan-DPI.exe` or `Kervan-DPI-<canonical-version>-windows-portable.zip` asset. A newer release without a compatible Windows asset is reported as unavailable. **Update manually** opens the validated release page; the user chooses and verifies the file. The UI does not run a downloaded executable.

## Production asset contract

For release version `1.0.2` (tag `v1.0.2`), prepare these assets after a native Windows build and QA:

- `Kervan-DPI.exe` — unchanged standalone onefile executable.
- `Kervan-DPI-1.0.2-windows-portable.zip` — same EXE plus docs/licenses.
- `Kervan-DPI-1.0.2-WINDOWS-SHA256SUMS.txt` — EXE and ZIP digests.
- `Kervan-DPI-1.0.2-update-manifest.json` — canonical JSON describing **only** the EXE.
- `Kervan-DPI-1.0.2-update-manifest.json.sig` — raw 64-byte Ed25519 signature over the exact JSON bytes.
- Release notes and retained local build provenance, resolved dependencies, wheelhouse hashes, source archive hash and QA report.

The manifest has exactly `schema` (integer `1`), `repository` (`MacallanTheRoot/GoodbyeDPI-Turkey-GUI`), `version` (canonical version), `asset` (`Kervan-DPI.exe`), `size` (positive byte count) and `sha256` (lowercase digest). It is serialized with sorted keys, compact separators, ASCII escapes and one trailing LF. The detached signature covers the exact bytes. `package_rc.ps1` prepares the **unsigned** manifest and refuses any existing output. It does not sign on a build machine automatically.

## Owner production signing procedure

1. Establish and document a production Ed25519 publisher identity using an approved offline key management process. Keep the private PEM outside this repository, build/source ZIPs, wheelhouse, app config and release uploads. Back it up securely. Do not use a generated test fixture or another project's key.
2. Record the corresponding **raw 32-byte public key** as 64 hex characters. Review its fingerprint and intended ownership out of band. Replace the empty `PRODUCTION_PUBLIC_KEY_HEX` pin in `src/utils/update_install.py` only in a reviewed source change. A public key alone is not an authorization to enable auto-install.
3. Build from the verified source ZIP on native Windows 11 x64 with Python 3.13. Complete the Windows QA matrix, including update and rollback tests. Confirm the final EXE bytes and manifest hash are unchanged afterward.
4. Sign the manifest with `.venv\Scripts\python.exe tools\release\update_manifest.py sign --manifest dist\Kervan-DPI-1.0.2-update-manifest.json --private-key X:\secure\publisher-ed25519.pem --output dist\Kervan-DPI-1.0.2-update-manifest.json.sig`. The tool refuses to overwrite an existing signature.
5. Independently verify with `update_manifest.py verify --manifest ... --signature ... --public-key-hex <reviewed-raw-public-key-hex> --version 1.0.2`, then compare the signed manifest's EXE digest to `Get-FileHash` and record the result in QA provenance.
6. Upload assets only after release review and explicit publication authorization. The release checker never treats a GitHub release alone as an update signature.

## Automatic installation gate

**BLOCKED.** No production public key is pinned, and no native Windows after-exit helper has been built or tested. The GUI shows a disabled Off toggle and never calls the dormant staging/replacement primitives. Legacy Off, Notify, Automatic and channel settings migrate to Off because none represented verified installation. `update_install.py` contains bounded HTTPS download, controlled redirects to `release-assets.githubusercontent.com`, Ed25519 validation, exact EXE hash/size checks, and an after-exit replacement/rollback seam tested with local doubles. These simulations do **not** establish reliable Windows replacement, process exit, UAC behavior, antivirus interaction, or WinDivert cleanup. Do not enable automatic installation until a trusted helper can be packaged, launched from local trusted code after `AppController.shutdown()` succeeds, restricted to the running `Kervan-DPI.exe` path, and tested end to end on native Windows. A helper must preserve the rollback copy and user config, handle locked files and failed restart, and clean only its own staging directory. Protected destinations must fail with an actionable error, without silent elevation or arbitrary file replacement.

## Native update QA additions

Test Off (zero automatic API requests), explicit Check for Updates, stable-over-RC version ordering, exclusion of drafts/prereleases, rate limit/offline/malformed responses, app Quit during an active check, and one notification per discovered release. Verify manual release links remain in the exact repository. Once a production pin and helper exist, test valid signed update, corrupt EXE, missing/invalid signature, wrong version/repository, malicious URL/redirect, cancellation, interrupted download, disk full, locked/denied destination, active GoodbyeDPI engine during Quit, failed restart, rollback, preserved config/startup shortcut, and ordinary HTTPS after exit. Record actual EXE hashes and processes. Do not call Linux test doubles a Windows pass.
