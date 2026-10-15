# Third-party notices (Windows RC source inventory)

The repository's MIT `LICENSE` covers the GUI code and existing project shield icon. Rights for the new Kervan DPI camel artwork must be documented before its distribution. This license does not replace licenses for bundled components.

| Component | Distribution | License and source |
| --- | --- | --- |
| GoodbyeDPI v0.2.3rc3 executables (`bin/x86`, `bin/x86_64`) | Windows source package and EXE | Apache License 2.0; `bin/licenses/LICENSE-goodbyedpi.txt`; [upstream](https://github.com/ValdikSS/GoodbyeDPI). |
| WinDivert v2.2.0 DLLs and drivers | Windows source package and EXE | LGPL 3.0 option; `bin/licenses/LICENSE-windivert.txt`; [upstream](https://github.com/basil00/WinDivert). |
| NetBSD `getline` and `uthash`, incorporated by the Windows engine | Windows engine | Existing notices in `bin/licenses/LICENSE-getline.txt` and `bin/licenses/LICENSE-uthash.txt`. |
| PySide6 Essentials, Shiboken6 and Qt 6 libraries/plugins | Frozen Linux and Windows applications | Community packages declare LGPL 3.0, GPL 2.0 or GPL 3.0 options. This project intends the LGPL 3.0 option. License texts are in `packaging/licenses/`; see [Qt for Python licensing](https://doc.qt.io/qtforpython-6/) and [component licenses](https://doc.qt.io/qtforpython-6/licenses.html). |
| PyInstaller bootloader | Frozen Linux and Windows applications | [PyInstaller bootloader exception and license](https://pyinstaller.org/en/stable/license.html). PyInstaller is a build tool; its bootloader is included in frozen output. |
| `cryptography` 46.0.7 and resolved `cffi`/`pycparser` | Update signature verification dependency; final Windows bundle must be inspected | `cryptography`: Apache-2.0 or BSD-3-Clause; `cffi`: MIT-0; `pycparser`: BSD-3-Clause. Record actual Windows wheels and corresponding source before publication. |

SpoofDPI is **not** bundled or downloaded. Linux users install it separately.

For Qt/PySide6 source availability and a practical modified-library rebuild
path, see [Qt LGPL compliance](docs/qt-lgpl-compliance.md). The prior RC1
release assets included version-matched Qt/PySide6, WinDivert and GoodbyeDPI
sources and the application build source. The 1.0.1rc2 candidate must
separately verify and provide corresponding sources before publication.
The LGPL permits reverse engineering for debugging library modifications.
