# Kervan DPI — iOS

Status: **sources written, not built.** The development host is Linux, with no Xcode and no Swift toolchain. Nothing under this folder has been compiled or run. The shared C path it relies on (packet mode) is tested on Linux. See "Evidence" below.

## Shape

```
SwiftUI app (KervanDPI)                     Packet Tunnel extension (KervanTunnel)
  NETunnelProviderManager  ── start/stop ─▶   PacketTunnelProvider
  status + HTTPS access check                   packetFlow.readPackets ─▶ kv_engine_packet_in()
                                                 packet_out_cb ─▶ packetFlow.writePackets
                                               KervanEngine.swift (C ABI wrapper)
                                               KervanCore.xcframework = mobile/core (same as Android)
```

- **No utun fd.** The core's *packet mode* (`tun_fd = KV_TUN_PACKET_MODE`) bridges `NEPacketTunnelFlow` to hev-socks5-tunnel over a private `socketpair`. It adds and strips the 4-byte Darwin utun family header that hev expects on Apple. The undocumented "scan fds for the utun socket" trick is not used.
- **No protect callback** (`require_protect = 0`). Sockets opened by the provider are expected to bypass its own tunnel. Apple's docs do not state this, so it must be confirmed on device (test 3 below).
- **Fail closed.** Engine `FAILED` → stop the engine → `cancelTunnelWithError`. `startTunnel` returns only after the engine reports `RUNNING`, so iOS "Connected" means "engine serving" and never "bypass works".
- Default strategy `-d1 -s1+s -r1+s` and Cloudflare DNS, the same as Android defaults. There is no settings screen on iOS yet.

## Files

| Path | Purpose |
|---|---|
| `scripts/build-core.sh` | CMake → `build/KervanCore.xcframework` (iphoneos arm64, simulator arm64+x86_64). `--test` also runs the C tests natively on macOS, which exercises the Darwin framing path. |
| `KervanCore/module.modulemap` | `import KervanCore` |
| `KervanTunnel/` | `PacketTunnelProvider`, `KervanEngine`, `EngineError`, Info.plist, entitlements |
| `KervanDPI/` | SwiftUI app, `TunnelController`, `AccessCheck`, assets (camel, accent #315FA7) |
| `Shared/TunnelIdentity.swift` | Bundle IDs and defaults, in both targets |
| `project.yml` | XcodeGen spec; set `DEVELOPMENT_TEAM` |

## Build without a Mac (GitHub Actions)

`.github/workflows/ios.yml` runs on a GitHub `macos-15` runner. Its steps:

1. `scripts/check_project.py`: static checks. These also run on Linux.
2. `fetch.sh`, then `build-core.sh --test`: C tests on macOS, which cover the Darwin framing path. This step also builds the xcframework.
3. `xcodegen generate`.
4. Unsigned `xcodebuild` for the Simulator and for a generic iOS device (`CODE_SIGNING_ALLOWED=NO`).
5. Compiler errors and warnings go to the job summary. The full logs are uploaded as the `ios-build-logs` artifact.

The workflow runs automatically on pushes that touch `mobile/core`, `mobile/ios` or the workflow file. It can also be started by hand from the Actions tab ("Run workflow") or with `gh workflow run ios.yml --ref <branch>`. The repository is public, so standard macOS runners cost nothing.

**A green run only means the code compiles and links.** It says nothing about whether the VPN works, whether bypass works, or whether Apple will approve the app. The output is unsigned and cannot be installed on a phone.

Local checks on Linux:

- `python3 mobile/ios/scripts/check_project.py` (needs PyYAML).
- Project generation, verified 2026-11-23: build XcodeGen 2.48.0 in the `swift:6.1-noble` Docker image, then run `USER=ci xcodegen generate` in a copy of `mobile/ios`. It writes `KervanDPI.xcodeproj`: both targets, the shared `KervanDPI` scheme, the extension embedded in the app, the xcframework and NetworkExtension linked into the extension, and no plist or entitlements file copied as a resource.

## Build on a Mac

```
cd mobile/core/third_party && ./fetch.sh
cd ../../ios && scripts/build-core.sh --test
brew install xcodegen && xcodegen generate && open KervanDPI.xcodeproj
```

Signing needs an Apple Developer team. The App IDs `dev.kervan.dpi` and `dev.kervan.dpi.tunnel` both need the Network Extension capability (packet tunnel). A free Personal Team cannot use the Network Extension entitlement.

## From unsigned build to iPhone, without a Mac

Not set up yet. Each step needs the owner's action or approval.

1. **Apple Developer Program** membership. The owner has a paid **Individual** membership, which is enough for development and ad-hoc signing with the Network Extension (packet tunnel) capability. A free Personal Team cannot sign that entitlement. **App Store distribution is blocked for an Individual account.** Guideline 5.4, verbatim: "Apps offering VPN services must utilize the NEVPNManager API and may only be offered by developers enrolled as an organization." It also says non-compliant apps are "blocked from installing via alternative distribution". Whether TestFlight external testing counts as "offering" falls under the same review and is not confirmed.
2. Create the App IDs `dev.kervan.dpi` and `dev.kervan.dpi.tunnel` in the developer portal, both with the **Network Extensions** capability. The packet tunnel value is self-service; no special request is needed.
3. Register the iPhone's UDID. On Linux: `sudo apt install libimobiledevice-utils`, then `idevice_id -l`.
4. Create an Apple Distribution (or Development) certificate. The CSR can be generated with `openssl`. Then create an **ad-hoc** provisioning profile per target.
5. Store the .p12, its password and both profiles as GitHub Actions secrets. Then add a separate, manually triggered signed job (`xcodebuild archive` + `-exportArchive`, ad-hoc). That job has not been written: it needs credentials, and credentials need your approval.
6. Install from Linux with `ideviceinstaller -i KervanDPI.ipa`. Read the extension logs with `idevicesyslog | grep dev.kervan.dpi`.

TestFlight is the alternative to steps 3–6. It needs an App Store Connect upload (an API key secret). Builds for internal testers skip Beta App Review; external testers need it.

Fallbacks that were considered: **Expo EAS Build** only builds Expo/React Native projects, so using it would mean wrapping or rewriting the native app. It adds nothing here beyond managing credentials. **Codemagic** and **Bitrise** build native Xcode projects directly. They are a reasonable second option if GitHub's macOS runners become unsuitable.

## Device test plan (iPhone 14 Pro)

1. Turn on → iOS prompts to add a VPN configuration → status shows "Engine running".
2. Check → `discord.com: HTTP 200` on Wi-Fi and on cellular. Then repeat with an empty strategy to show the desync is what makes the difference (A/B/A, as on Android).
3. Loop check: Console.app, subsystem `dev.kervan.dpi.tunnel`, should show no repeating connection storm. Traffic should keep flowing for 5 minutes.
4. Turn off → the VPN icon disappears and normal browsing still works.
5. Repeat Turn on/off 5 times. Then turn the VPN off from iOS Settings while it is running.
6. Memory: watch the extension in Xcode's Debug navigator during a video stream. It must stay well below the extension's memory limit. Apple does not publish the limit; developer reports put it around 50 MB.
7. Report QUIC/UDP 443 and IPv6 behaviour separately. They are not tested on any platform yet.

## Distribution feasibility (read before investing further)

Apple **TN3120**, "Expected use cases for Network Extension packet tunnel providers" (revised 2025-07-22), lists as unsupported:

- "Do not use a packet tunnel provider to host a network listener or proxy server." Our engine hosts the ByeDPI SOCKS5 listener on 127.0.0.1 inside the extension.
- "Traffic that is claimed by a NEPacketTunnelProvider is meant to be sent through the tunnel connection and not be routed through another interface via a proxy." We terminate TCP on the device and send it out of the physical interface.
- "Do not use a packet tunnel provider to intercept all DNS traffic on the system." Our DNS settings use `matchDomains = [""]`.

TN3120 calls these "unsupported", not "prohibited". Even so, App Review can cite it, and Apple will not help with the edge cases. App Store guideline 5.4 also requires VPN apps to be offered by an organization developer account and to declare what data they collect. **Technical feasibility is likely (hev and ByeDPI already support Apple). App Store approval is uncertain.** Development, ad-hoc and TestFlight internal builds do not depend on App Review.

The only design Apple supports for this traffic is a remote server, which conflicts with the project rule "no remote VPN dependency". Removing the loopback SOCKS listener (an in-process lwIP → desync hop) would address the "listener" point but not the "proxy elsewhere" point.
