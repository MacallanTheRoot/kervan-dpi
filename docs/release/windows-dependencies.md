# Windows dependency and license inventory — 1.0.1rc2 candidate

| Component | Source in this tree | License / required review |
| --- | --- | --- |
| Kervan DPI Python GUI | `src/`, `LICENSE` | MIT. Existing shield notice does not establish rights to the new camel artwork; record its source and permission separately. |
| GoodbyeDPI v0.2.3rc3 | `bin/x86`, `bin/x86_64` | Apache-2.0 notice in `bin/licenses/LICENSE-goodbyedpi.txt`; verify binaries and corresponding source before publication. |
| WinDivert v2.2.0 | DLLs and drivers in `bin/` | LGPL-3.0 option in `bin/licenses/LICENSE-windivert.txt`; verify source, binary provenance and driver signature. A signed upstream driver is not a signature on Kervan DPI. |
| NetBSD getline and uthash | Incorporated in GoodbyeDPI | Existing notices in `bin/licenses/`. |
| PySide6 Essentials, Shiboken6, Qt 6.10.3 | Installed from pinned requirements and resolved wheels | LGPL/GPL options, with project using LGPL-3.0; texts in `packaging/licenses/`. Verify actual wheel/plugin versions and source/relinking availability. |
| PyInstaller 6.16.0 bootloader | Frozen EXE | Bootloader exception and license described in `THIRD_PARTY_NOTICES.md`. |
| `cryptography` 46.0.7 and resolved `cffi`/`pycparser` | Update signature verification dependency | `cryptography`: Apache-2.0 or BSD-3-Clause; `cffi`: MIT-0; `pycparser`: BSD-3-Clause. Confirm actual Windows wheel set and source before publication. |
| SpoofDPI | **Not** in Windows package | Separately installed Linux engine only. |

The shared `requirements.txt` pins two top-level GUI/build packages. `requirements-windows-rc.txt` adds `cryptography==46.0.7` for Windows RC signing verification and source tests without changing Linux build dependencies. The native 3.13 x64 build script captures the exact resolved wheel files, their SHA-256 hashes, `pip freeze`, engine input hashes, EXE/ZIP hashes and the source-input manifest hash in its local build provenance. [Exact checked-in engine hashes](windows-engine-inputs.md) are recorded separately. [THIRD_PARTY_NOTICES.md](../../THIRD_PARTY_NOTICES.md) and [Qt LGPL instructions](../qt-lgpl-compliance.md) remain part of the source and portable package. This RC1 Qt record must be reviewed against the actual RC2 wheels. Camel artwork rights and version-matched corresponding sources remain publication blockers.
