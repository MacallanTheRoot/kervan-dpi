# Kervan DPI Windows RC native QA report template

Copy this file for each candidate. Leave unexecuted scenarios **PENDING**; do not transfer results from an earlier EXE.

## Candidate and environment

| Field | Recorded value |
| --- | --- |
| Tester, date and authorization for real Windows network/profile test | PENDING |
| Windows edition, build and architecture (`winver`, `Get-ComputerInfo`) | PENDING |
| Python, PyInstaller, PySide6 and PowerShell versions | PENDING |
| Source archive filename and SHA-256 | PENDING |
| `Kervan-DPI.exe` filename, size and SHA-256 | PENDING |
| Portable ZIP filename and SHA-256 | PENDING |
| Windows build log and provenance JSON paths | PENDING |
| Previous GoodbyeDPI Turkey EXE/version and path, if present | PENDING |
| Config path, before/after SHA-256 and backup location | PENDING |
| Startup, Start Menu and desktop shortcut before/after targets | PENDING |
| Engine staging path, EXE/DLL/driver hashes and WinDivert service path/state | PENDING |

## Scenario evidence

Use [W01–W17](windows-qa-checklist.md). For repeated cases, record each iteration separately (W03 × 10, W04 × 3, W05 × 3). `validate_rc.ps1` snapshots, process lists and network results belong beside the matching row. Screenshots help for Explorer/UAC/taskbar/tray/icon and Defender/SmartScreen observations; redact personal data before sharing.

| Scenario / iteration | PASS / FAIL / N/A / PENDING | Observed result and exact log or screenshot path |
| --- | --- | --- |
| W01 | PENDING | |
| W02 | PENDING | |
| W03.01 | PENDING | |
| W03.02 | PENDING | |
| W03.03 | PENDING | |
| W03.04 | PENDING | |
| W03.05 | PENDING | |
| W03.06 | PENDING | |
| W03.07 | PENDING | |
| W03.08 | PENDING | |
| W03.09 | PENDING | |
| W03.10 | PENDING | |
| W04.01 | PENDING | |
| W04.02 | PENDING | |
| W04.03 | PENDING | |
| W05.01 | PENDING | |
| W05.02 | PENDING | |
| W05.03 | PENDING | |
| W06 | PENDING | |
| W07 | PENDING | |
| W08 | PENDING | |
| W09 | PENDING | |
| W10 | PENDING | |
| W11 | PENDING | |
| W12 | PENDING | |
| W13 | PENDING | |
| W14 | PENDING | |
| W15 | PENDING | |
| W16 | PENDING | |
| W17 | PENDING | |

## Errors, migration and decision

- Errors, exit codes, log excerpts and reproduction steps: PENDING
- Old settings/unknown keys preserved after candidate, rollback and portable removal: PENDING
- Post-Quit ordinary HTTPS result: PENDING
- WinDivert process/service/path observations and any unrelated users: PENDING
- Remaining blockers and retest artifact hash: PENDING
- Final tester conclusion and explicit user confirmation: PENDING

Do not mark the candidate release ready until the complete native matrix, migration/rollback and licensing gates pass. This report is evidence for a later approval decision; it does not publish anything.

## Update QA evidence

Record U01–U06 from [the update QA matrix](windows-qa-checklist.md), including release API fixture/URL, timestamps, screenshots and config before/after hashes. U07 remains **BLOCKED** until the production signing and helper gates in [the update contract](windows-update.md) are satisfied. Do not convert Kali simulation results into native Windows evidence.
