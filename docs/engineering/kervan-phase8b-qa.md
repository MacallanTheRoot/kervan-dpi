# Kervan Phase 8B engineering QA (2026-10-12)

This record covers source validation only. It does not authorize a package
rename, automatic configuration migration, installation or release. The Kervan
Master Blueprint files are outside this work.

## Qt operation lifetime

Qt delivers worker completion signals on the UI thread after the backend call
returns. The emitting Python thread may still report `is_alive()` during that
delivery. Blocking Stop on thread liveness therefore caused intermittent
false rejection. The operation completion event now marks when the backend
call has actually ended; Start, Stop and Linux engine settings use that event.
The phase and operation token still control UI transitions and reject stale
signals. Quit still joins the worker before calling `runner.close()`, preserving
the Windows Job Object and Linux SpoofDPI cleanup sequence.

A bounded Quit can fail while a worker continues to run. Previously it reset
the phase to Error, which let a new Start replace the worker reference. The
event now prevents this overlap. The UI disables backend controls while the
worker remains busy and refreshes them when the invalidated completion arrives.
Tests cover blocked Start during failed Quit, rapid Start/Stop/Start, signal
delivery before thread retirement and stale Start/Stop completions.

## Inactive Windows config copy

`prepare_config_copy()` remains opt-in and is not called by the application.
It now rejects reparse-point attributes and non-regular files, publishes a
fully written backup by exclusive hard link, and uses a separate inode for the
target. Both are staged with mode 0600 where POSIX modes apply. Failed staging
can leave a complete backup for retry but cannot publish a partial backup or
target. Existing targets remain untouched. Concurrent same-content calls
converge to one target; conflicting backup or target data is refused or reported.

This is **not ready for automatic Windows activation**. [Microsoft documents
same-volume NTFS hard links](https://learn.microsoft.com/en-us/windows/win32/fileio/hard-links-and-junctions),
while [filesystem support differs](https://learn.microsoft.com/en-us/windows/win32/fileio/filesystem-functionality-comparison);
FAT/network/cloud-backed APPDATA locations may reject them.
Windows ACL inheritance and UAC identity must be tested natively. Path checks
use `lstat` and reparse attributes, but an attacker able to replace a parent
directory or source between the check and open/link can still race the helper.
A Windows-native handle-based design (using
[`FILE_FLAG_OPEN_REPARSE_POINT`](https://learn.microsoft.com/en-us/windows/win32/fileio/reparse-point-operations)
where appropriate and checking file identity) or a trusted-directory guarantee is
needed before activation. The old file remains the rollback source. Never
delete or merge either file automatically. An existing target is returned as
`already_copied` or `coexisting` without retroactively creating a backup.

## Future Debian identity transition

The current `goodbyedpi-turkey` package, launcher, `/opt` tree, desktop ID,
icon ID and autostart ID remain stable. A future `kervan` package should first
take ownership of **the same paths**. Its control data needs versioned
`Breaks`/`Replaces: goodbyedpi-turkey (<< transition-version)` for overlapping
files, with a transitional `goodbyedpi-turkey` package depending on `kervan`
if the update channel can deliver it. Keep one desktop file and the existing
launcher as a compatibility alias. Decide package/version relationships and
whether `Conflicts` is necessary only after real dpkg upgrade tests. A new
`kervan.desktop` or `kervan.png` at this step would create duplicate menu/icon
identities and is deferred. User XDG config and autostart remain outside dpkg.

An isolated root simulation extracted the Phase 8A2 deb, checked package
metadata and version ordering over `1.0.1~rc2`, checked the launcher target,
desktop and icon IDs, modeled ownership transfer on the same paths, then
removed those paths and re-extracted the old package for rollback. User config
and one autostart entry survived; there was one menu entry. A manual install
marker in `/opt/goodbyedpi-turkey` was detected as a collision. A real future
package must refuse or explicitly reconcile that manual tree **before** dpkg
overwrites unowned files; `/usr/local/bin/goodbyedpi-turkey` can also shadow
`/usr/bin/goodbyedpi-turkey`. The simulation does not prove dpkg maintainer
script behavior, repository upgrades, actual removal/purge semantics or
coexistence on an installed machine. Test those in disposable VM roots when a
candidate `kervan` package exists. No installed package was changed.

## Asset approval checklist

1. Approve an editable master mark and license/assignment documents, including
   font and third-party component rights. Record provenance and file hashes.
2. Review legibility at 16 px, grayscale, contrast, light/dark panels and
   high-DPI scaling; reject imagery implying encryption or system-wide VPN.
3. Export transparent PNG sizes for Qt header/window/tray and hicolor, a
   scalable Linux SVG, and a multi-size Windows ICO through 256 px.
4. Inspect the approved design on native KDE trays/menus and native Windows
   Explorer, taskbar and UAC; verify one desktop entry and the old icon ID
   during the technical identity transition.
5. Prepare separate site/social and Android/iOS exports only when those
   surfaces have their own design and publication approval.

The full export specifications and integration points are in
`docs/branding/kervan-brand-asset-requirements.md`. Existing shield assets remain in
use until visual approval.
