# Vendored upstream sources

`fetch.sh` downloads these pinned commits into `third_party/src/` (git-ignored). Nothing is modified; integration happens only in `mobile/core/src/`.

| Component | Commit | License | Role |
|---|---|---|---|
| [hufrea/byedpi](https://github.com/hufrea/byedpi) | `e2684772fbda45f2ff4fc220922a010370534216` | MIT | Local SOCKS5 proxy with TCP/TLS desync (split, disorder, OOB, fake, TLS record) and UDP relay |
| [heiher/hev-socks5-tunnel](https://github.com/heiher/hev-socks5-tunnel) | `fc3f90040b8d4b537341c96538669a9b2e35d514` | MIT | TUN fd → lwIP → SOCKS5 client |
| ↳ hev-socks5-core | `f8c08a64482c22c48a971bde22ce47c113b4d7af` | MIT | SOCKS5 protocol |
| ↳ hev-task-system | `ded55c412b3951bc7decb5cb3b9135701e762998` | MIT | Coroutine scheduler |
| ↳ lwip (hev fork) | `8115cd6150ab32500db3d4d8bd8ad7ec6648534c` | BSD-3-Clause | User-space TCP/IP stack |
| ↳ yaml | `0c82efd10dc67b9e7f159d2c7f5d1dc3c1b5bc11` | MIT | Config parser |

Not used: `hev-socks5-tunnel/third-part/wintun` (Windows only) and `src/hev-jni.c` (we ship our own JNI). [ByeDPIAndroid](https://github.com/dovecoteescapee/ByeDPIAndroid) (GPL-3.0) was read for orientation only; none of its code is included, so the Kervan app code stays MIT.

Before a public release, copy each LICENSE file into the app's open-source notices screen and `THIRD_PARTY_NOTICES.md`.
