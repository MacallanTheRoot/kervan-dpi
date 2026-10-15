# Kervan DPI Windows release candidate readiness — prior checkpoint (2026-10-13)

**Historical checkpoint.** The fix01 branded EXE was subsequently built and partially tested on Windows 11, but the changed Nightshift update source still needs native build and complete QA. See the separate `NIGHTSHIFT_STATUS.md` handoff in the working tree.

**Decision: HOLD. No tag, push, GitHub release or stable Windows claim.** The latest Nightshift work was preserved. The prior real Windows 11 lifecycle result (18/18) belongs to an older prebranding build. The final Kervan DPI EXE needs a new Windows build and native QA.

| Gate | Status | Evidence / remaining work |
| --- | --- | --- |
| Text identity | Prepared | `APP_NAME`, About, title, tray, notification labels and Windows version resources use Kervan DPI; native visual review pending. |
| Approved camel icon | **Source export prepared** | `assets/kervan-camel-source.png` matches the user-described blue camel and is hash pinned; transparent PNG/ICO exports and offline size/alpha checks pass. Creator/redistribution-rights evidence and native Windows visual inspection remain pending. |
| README and GitHub presentation | Prepared in STEP 03 | English primary README, linked Turkish guide, current Linux development guide, verified local links and upstream URL audit. No badges, screenshots, branded download asset links or public metadata changes. Final artifact links/hashes await native build. |
| Windows build | **Pending native** | Python 3.13 x64 selection, collision-safe source handoff, captured wheelhouse/provenance, frozen-content inspection and portable verification scripts prepared. No branded Windows EXE has been built or tested in this session. |
| Installer | Not available | Existing project has no Windows installer workflow. Portable EXE/ZIP path is documented. |
| Legacy migration | **Pending native** | Old config/startup/staging IDs preserved; offline opt-in copy tests exist. No automatic migration. Upgrade/rollback/portable removal need native QA. |
| Linux regression | Offline PASS at STEP 05 | The current headless source suite passed **330/330** after Windows branding, packaging and migration tests. Native Linux visual behavior and transparent NFQUEUE remain unverified. Last Nightshift B1 reported 316/316 before these additions. |
| Third-party source/licensing | **Pending** | Existing notices/licenses and checked-in engine hashes inventoried. Confirm matching Qt/PySide6, GoodbyeDPI and WinDivert source/hashes, actual Windows wheel contents and new artwork rights for this exact build. |
| Publication | **Not ready** | Wait for exact branded artifact, checksums, W01–W17 results, approved version and final user approval. |

Release assets to review at the approval gate: native `Kervan-DPI.exe`, portable ZIP, source ZIP, Windows and source SHA-256 manifests, version-matched source/license inventory, completed QA checklist, migration report and finalized release notes. Do not publish or change unrelated Linux releases. Master Blueprint remains untouched.
