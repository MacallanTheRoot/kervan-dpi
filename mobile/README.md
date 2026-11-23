# Kervan DPI — mobile

On-device DPI circumvention for Android (first) and iOS (later). No remote server, no VPN service in the commercial sense: the system VPN interface is used only to route the device's traffic into a local engine.

```
apps ──► TUN (VpnService) ──► hev-socks5-tunnel ──► 127.0.0.1 SOCKS5 ──► ByeDPI desync ──► protect()ed socket ──► network
```

| Path | What |
|---|---|
| `core/` | Portable C engine, ABI in `core/include/kervan_engine.h`, host tests in `core/tests/` |
| `android/` | Kotlin + Jetpack Compose app, `VpnService`, JNI shim |
| `ios/` | Not started; see `ios/README.md` |

## Build

```bash
bash mobile/core/third_party/fetch.sh            # pinned upstream sources
# host tests (needs cmake+ninja; the Android SDK's cmake works)
cmake -S mobile/core -B mobile/core/build-host -G Ninja -DKV_BUILD_TESTS=ON
cmake --build mobile/core/build-host && ctest --test-dir mobile/core/build-host --output-on-failure
# Android (JDK 21, Android SDK with platform 36, NDK 29.0.14206865, CMake 3.31.6)
cd mobile/android && ./gradlew :app:testDebugUnitTest :app:assembleDebug
```

## Status

Proof of concept. "Engine active" means traffic flows through the local engine; it is **not** evidence that a blocked site opens. See `.claude/skills/kervan-mobile-native-qa/SKILL.md` for the device test matrix.

Known limitations:
- The internal SOCKS5 hop on `127.0.0.1` has no authentication, so another app on the same device could connect to it while the engine runs.
- DNS goes as plain UDP to `1.1.1.1` / `2606:4700:4700::1111` through the engine. ISP DNS interception is not handled yet.
- Only one engine per process (upstream libraries keep global state).
- The default strategy `-d1 -s1+s -r1+s` is a starting point and has not been checked against any ISP.
