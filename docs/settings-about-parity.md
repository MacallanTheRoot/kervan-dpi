# Settings, connection check and About: platform parity

iOS is the reference (`mobile/ios`). Only iOS has been changed so far. "Found" comes from reading the sources on 2026-11-25, not from running the apps.

## Contract

- Settings > About (Ayarlar > Hakkında).
- Name `Kervan DPI`; slogan `Yol Açık, Kervan Yürür.`
- Developer `MacallanTheRoot`, which opens https://github.com/macallanTheRoot in the system default browser.
- Version and build read from the package, the platform, the repository link, the license, acknowledgements, privacy and diagnostics.
- Each platform writes its own license, privacy and engine text: the engines and data flows differ.
- Connection check: neutral targets with a reply check for each one, redirects refused, normal certificate checks, ephemeral requests. The result records whether Kervan was on. HTTP 200 or "connected" is never shown as bypass.

## Android (`mobile/android`, untracked, so absent from this branch)

Found: an About section in Settings with text and version name. `ConnectivityProbe` defaults to two Discord addresses plus example.com, and counts any HTTP status 100-599 as OK.

- [ ] Commit the sources before changing them
- [ ] Replace the default targets; add target selection and an HTTPS-only custom address
- [ ] Judge the reply, not the status alone; treat redirects, other bodies and certificate errors separately
- [ ] Keep adb-driven probe evidence runs possible with an explicit target
- [ ] About: slogan, developer link, build number, repository, license, privacy, diagnostics
- [ ] Ship the engine license texts (same components as iOS)
- [ ] `values` and `values-tr`

## Windows and Linux desktop

Found: About is a message box in `src/ui/views/main_window.py`, with no Settings > About. On this branch `src/metadata.py` still says `GoodbyeDPI Turkey`; the branch `linux/debian-ubuntu` says `Kervan DPI` with the slogan. `PROJECT_URL` points at the old `GoodbyeDPI-Turkey-GUI` repository on both.

- [ ] Start from the Kervan-branded branch; do not edit this branch's legacy metadata
- [ ] Owner decision: new `PROJECT_URL`. Package, command and config identifiers stay unchanged
- [ ] Replace the message box with About inside Settings; open the developer link with `QDesktopServices.openUrl`
- [ ] Windows: GoodbyeDPI and WinDivert notices; Linux: Zapret2 helper and Qt/PySide6 LGPL notices
- [ ] Privacy text for each: proxy, system or DNS changes really made by that build
- [ ] Connection check, only where a desktop check is wanted

## Before any public release (all mobile)

- [ ] Review the provenance of `hev-rbtree` in hev-task-system: the file names Linux kernel rbtree authors, while the project declares MIT
- [ ] Review lwIP per-file notices (PPP and TLS sources) beyond its LICENSE file
- [ ] iOS: `PrivacyInfo.xcprivacy` declaring UserDefaults (needed for App Store Connect uploads, not for development installs)
- [ ] Turkish localization on iOS (the app is English only today)
