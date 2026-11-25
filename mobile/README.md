# Kervan DPI — mobile

On-device DPI circumvention for Android; the core is shared with the iOS work. No remote server, no VPN service in the commercial sense: the system VPN interface is used only to route the device's traffic into a local engine.

```
apps ──► TUN (VpnService) ──► hev-socks5-tunnel ──► 127.0.0.1 SOCKS5 ──► ByeDPI desync ──► protect()ed socket ──► network
```

| Path | What |
|---|---|
| `core/` | Portable C engine, ABI in `core/include/kervan_engine.h`, host tests in `core/tests/` |
| `android/` | Kotlin + Jetpack Compose app, `VpnService`, JNI shim |

## Build

```bash
bash mobile/core/third_party/fetch.sh            # pinned upstream sources
# host tests (needs cmake+ninja; the Android SDK's cmake works)
cmake -S mobile/core -B mobile/core/build-host -G Ninja -DKV_BUILD_TESTS=ON
cmake --build mobile/core/build-host && ctest --test-dir mobile/core/build-host --output-on-failure
# Android (JDK 21, Android SDK with platform 36, NDK 29.0.14206865, CMake 3.31.6)
cd mobile/android && ./gradlew :app:testDebugUnitTest :app:assembleDebug
```

## Reproduce the release APK

The build path is embedded in the native library, so build at `/tmp/kervan-build` with the tools above:

```bash
git clone --branch android-v0.2.0-beta1 https://github.com/MacallanTheRoot/kervan-dpi /tmp/kervan-build
cd /tmp/kervan-build && bash mobile/core/third_party/fetch.sh
echo "sdk.dir=$ANDROID_HOME" > mobile/android/local.properties
cd mobile/android && ./gradlew --no-daemon --no-build-cache :app:assembleRelease
sha256sum app/build/outputs/apk/release/app-release-unsigned.apk
```

Expected unsigned APK for 0.2.0-beta1: `ab56fda3328e818a4c405c12cf60a85972c5ef08b08c4c2ad50b300e87ea9e22`.
The published APK is this file plus a signature, so its own hash differs.

## Status

Experimental beta (Android 0.2.0-beta1). "Engine active" means traffic flows through the local engine; it is **not** evidence that a blocked site opens.

Known limitations:
- The internal SOCKS5 hop on `127.0.0.1` has no authentication, so another app on the same device could connect to it while the engine runs.
- By default apps are given `1.1.1.1` / `2606:4700:4700::1111` as DNS, through the engine. ISP DNS interception is not handled yet.
- Only one engine per process (upstream libraries keep global state).
- The default strategy `-d1 -s1+s -r1+s` opened one blocked site on one phone, on one mobile and one Wi-Fi network. It may not work on others.
- QUIC/UDP, engine-crash recovery and switching networks while on have not been tested on a device.
