# Third-party notices for 1.0.1rc1

The repository's MIT `LICENSE` covers the GUI code and project icon. It does not replace licenses for bundled components.

| Component | Distribution | License and source |
| --- | --- | --- |
| GoodbyeDPI v0.2.3rc3 executables (`bin/x86`, `bin/x86_64`) | Windows source package and EXE | Apache License 2.0; `bin/licenses/LICENSE-goodbyedpi.txt`; [upstream](https://github.com/ValdikSS/GoodbyeDPI). |
| WinDivert v2.2.0 DLLs and drivers | Windows source package and EXE | LGPL 3.0 option; `bin/licenses/LICENSE-windivert.txt`; [upstream](https://github.com/basil00/WinDivert). |
| NetBSD `getline` and `uthash`, incorporated by the Windows engine | Windows engine | Existing notices in `bin/licenses/LICENSE-getline.txt` and `bin/licenses/LICENSE-uthash.txt`. |
| PySide6 Essentials, Shiboken6 and Qt 6 libraries/plugins | Frozen Linux and Windows applications | Community packages declare LGPL 3.0, GPL 2.0 or GPL 3.0 options. This project intends the LGPL 3.0 option. License texts are in `packaging/licenses/`; see [Qt for Python licensing](https://doc.qt.io/qtforpython-6/) and [component licenses](https://doc.qt.io/qtforpython-6/licenses.html). |
| PyInstaller bootloader | Frozen Linux and Windows applications | [PyInstaller bootloader exception and license](https://pyinstaller.org/en/stable/license.html). PyInstaller is a build tool; its bootloader is included in frozen output. |

SpoofDPI is **not** bundled or downloaded. Linux users install it separately.

For Qt/PySide6 source availability and a practical modified-library rebuild
path, see [Qt LGPL compliance](docs/qt-lgpl-compliance.md). The release assets
include version-matched Qt/PySide6, WinDivert and GoodbyeDPI sources and the application build source.
The LGPL permits reverse engineering for debugging library modifications.

## Android 0.2.0-beta1

The Android APK contains none of the components listed above. It contains these; the full
license texts are in the app (Settings > About > Open-source notices) and in
[`acknowledgements.txt`](mobile/android/app/src/main/res/raw/acknowledgements.txt).

| Component | License | Source |
| --- | --- | --- |
| ByeDPI (with kavl.h) | MIT | [hufrea/byedpi](https://github.com/hufrea/byedpi) `e2684772fbda45f2ff4fc220922a010370534216` |
| hev-socks5-tunnel | MIT | [heiher/hev-socks5-tunnel](https://github.com/heiher/hev-socks5-tunnel) `fc3f90040b8d4b537341c96538669a9b2e35d514` |
| hev-socks5-core | MIT | submodule `f8c08a64482c22c48a971bde22ce47c113b4d7af` |
| hev-task-system | MIT | submodule `ded55c412b3951bc7decb5cb3b9135701e762998` |
| lwIP (hev fork) | BSD 3-Clause | submodule `8115cd6150ab32500db3d4d8bd8ad7ec6648534c` |
| libyaml (hev fork) | MIT | submodule `0c82efd10dc67b9e7f159d2c7f5d1dc3c1b5bc11` |
| AndroidX / Jetpack Compose / Material 3, Kotlin standard library, kotlinx.coroutines, kotlinx.serialization, JetBrains annotations, Guava ListenableFuture, JSpecify | Apache License 2.0 | Versions in `mobile/android/gradle/libs.versions.toml` |

The blue camel image was generated through ChatGPT for this project at the owner's request.
It is not claimed to be MIT licensed, and no exclusivity or trademark registration is claimed.
