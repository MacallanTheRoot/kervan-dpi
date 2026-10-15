# Draft release notes — Kervan DPI 1.0.1rc2 Windows RC

The bilingual [Windows release note draft](../releases/kervan-dpi-windows-release-notes.md) is the current publication template. This earlier draft is retained for the release preparation record.

**Draft only. Do not publish until the exact branded build passes native Windows QA and a version is approved.**

Fix 03 identifies the application developer as MacallanTheRoot and uses `Copyright (c) 2026 MacallanTheRoot` in Windows file metadata. The former first-party legal notice and historical credits are retained. File metadata does not establish a code-signing identity. The Fix 02 locale-dependent update test failure is addressed in this source; native Windows verification is pending.

Kervan DPI is the new display brand for the GoodbyeDPI Turkey desktop GUI. Slogan: **Yol Açık, Kervan Yürür.** Windows runs the bundled GoodbyeDPI and WinDivert engine. Linux currently uses a separately installed local SpoofDPI proxy; transparent Zapret2/NFQUEUE is unavailable.

## Candidate assets

- `Kervan-DPI.exe` — onefile Windows x64 candidate; native build pending.
- `Kervan-DPI-1.0.1rc2-windows-portable.zip` — onefile EXE and notices; native build pending.
- `Kervan-DPI-1.0.1rc2-WINDOWS-SHA256SUMS.txt` — pending EXE/ZIP hashes.
- `Kervan-DPI-1.0.1rc2-windows-rc-build-source.zip` and source checksum — local source handoff prepared; not a Windows EXE or published asset. Camel redistribution rights still need evidence.
- Corresponding Qt/PySide6, WinDivert and GoodbyeDPI source provision — review pending.

The EXE is portable. There is no installer and no Kervan DPI code-signing claim. Launch requests UAC when WinDivert requires elevation. Download only from the project release page and compare the published SHA-256 to the downloaded file. The supported Windows version list will be filled from actual native QA results; the previous Windows 11 result applies to an older build.

## Compatibility and limits

Existing `%APPDATA%\GoodbyeDPI-Turkey\config.json`, the legacy Startup shortcut name and `Program Files\GoodbyeDPI-Turkey\engine` remain in place. No automatic settings migration or engine directory deletion occurs. A preexisting autostart shortcut may target the old EXE; see [upgrade and rollback instructions](windows-migration.md). WinDivert can retain a service entry pointing to an older engine directory. Kervan DPI is not a VPN or anonymity service.

## Verification to fill before publication

Record the exact EXE and ZIP SHA-256, Windows build number, tester/date, all [QA cases](windows-qa-checklist.md), WinDivert path, `_MEI` observations, Discord and ordinary HTTPS results, upgrade/rollback/uninstall observations, icon/metadata review, and corresponding third-party source inventory. Any critical failure keeps this draft unpublished.

GUI and upstream attribution/license details: [README](../../README.md), [notices](../../THIRD_PARTY_NOTICES.md), and [dependency inventory](windows-dependencies.md).
