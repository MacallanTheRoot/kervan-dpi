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
| `project.yml` | XcodeGen spec; signing settings come from `ios-signed.yml` |

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

The unsigned build is green (run 45241078722). `.github/workflows/ios-signed.yml` turns it into a **development-signed IPA** for registered devices. It starts on a push that changes that file on `ios/first-cloud-build`, then waits for the reviewer of the `ios-signing` environment, which holds its five secrets. Signing proves only that iOS will accept the install. It does not prove that the VPN works, that bypass works, or that Apple would distribute the app.

What signing needs:

| Item | Value |
|---|---|
| App IDs (explicit) | `dev.kervan.dpi`, `dev.kervan.dpi.tunnel`, both with **Network Extensions** enabled |
| Entitlement (both targets) | `com.apple.developer.networking.networkextension = [packet-tunnel-provider]` |
| App Groups, Keychain sharing, Personal VPN | not used; do not enable them |
| Certificate | one **Apple Development** certificate (private key stays on your Linux machine and in the .p12) |
| Profiles | two **iOS App Development** profiles, one per App ID, each containing that certificate and the iPhone |
| Device | iPhone UDID registered; iOS 17.0 or newer; Developer Mode on |

A paid Individual account can do all of this: the packet tunnel value of Network Extensions is self-service for paid teams. A free Personal Team cannot. If the portal says `dev.kervan.dpi` is already taken, the identifiers must change in `project.yml` and `Shared/TunnelIdentity.swift` together (`check_project.py` enforces the match).

Steps. Keep every file under a private folder **outside** the repository, for example `~/kervan-signing` (`chmod 700`).

1. iPhone UDID: `sudo apt install libimobiledevice-utils ideviceinstaller usbmuxd`. Connect the phone, tap Trust, run `idevicepair pair` and then `idevice_id -l`. Add the UDID at developer.apple.com → Certificates, IDs & Profiles → Devices.
2. Identifiers → `+` → App IDs → App → explicit `dev.kervan.dpi` → tick **Network Extensions**. Repeat for `dev.kervan.dpi.tunnel`.
3. Certificate, on Linux:
   ```
   openssl genrsa -out kervan-dev.key 2048
   openssl req -new -key kervan-dev.key -out kervan-dev.csr -subj "/CN=Kervan DPI Dev"
   ```
   Certificates → `+` → **Apple Development** → upload `kervan-dev.csr` → download `development.cer`. Then:
   ```
   openssl x509 -inform DER -in development.cer -out kervan-dev.pem
   openssl pkcs12 -export -legacy -inkey kervan-dev.key -in kervan-dev.pem -out kervan-dev.p12
   ```
   `-legacy` matters: macOS `security import` rejects the OpenSSL 3 default .p12 encryption.
4. Profiles → `+` → **iOS App Development** → App ID `dev.kervan.dpi` → the certificate → the iPhone. Download it. Repeat for `dev.kervan.dpi.tunnel`.
5. Secrets: needs your approval. Create the `ios-signing` environment (Settings → Environments; optionally add yourself as a required reviewer). Values are read from files or stdin, so they never reach shell history:
   ```
   gh secret set IOS_DEV_P12_BASE64 --env ios-signing < <(base64 -w0 kervan-dev.p12)
   gh secret set IOS_DEV_P12_PASSWORD --env ios-signing          # prompts
   gh secret set IOS_APP_PROFILE_BASE64 --env ios-signing < <(base64 -w0 <app>.mobileprovision)
   gh secret set IOS_TUNNEL_PROFILE_BASE64 --env ios-signing < <(base64 -w0 <tunnel>.mobileprovision)
   gh secret set IOS_IPA_PASSPHRASE --env ios-signing            # prompts
   ```
6. Run: push a change to `ios-signed.yml` on `ios/first-cloud-build`, then approve the waiting deployment in the Actions tab. (`gh workflow run` needs the file on `main`.) The job checks that each profile matches its App ID and carries packet-tunnel-provider, signs, verifies the signatures and entitlements, and uploads the IPA **encrypted** (1-day retention). The embedded profile contains your name and the UDID, and this repository is public.
7. Install:
   ```
   gh run download <run-id> -n kervan-dpi-ios-dev-ipa-encrypted
   openssl enc -d -aes-256-cbc -pbkdf2 -iter 200000 -in KervanDPI.ipa.enc -out KervanDPI.ipa
   idevicedevmodectl reveal      # then Settings → Privacy & Security → Developer Mode → On, reboot
   ideviceinstaller -i KervanDPI.ipa
   idevicesyslog | grep -i kervan
   ```

The certificate and profiles are valid for one year. Adding another device means regenerating both profiles.

TestFlight is the alternative to steps 1, 6 and 7. It needs a Distribution certificate, App Store profiles and an App Store Connect API key. Builds for internal testers skip Beta App Review; external testers need it, and guideline 5.4 applies there.

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
