#!/usr/bin/env python3
"""Static consistency checks for the iOS project; runs on Linux, no Xcode.

Catches mistakes that compile but break at runtime, or that would only
surface as an error on a Mac: mismatched bundle IDs, a wrong extension
principal class, missing entitlements, C symbols the Swift code uses but the
engine header does not declare, and KervanCore imported outside the
extension target (only the extension links the xcframework).

    python3 mobile/ios/scripts/check_project.py      exit 1 on any failure
"""
import pathlib
import plistlib
import re
import sys

import yaml

IOS = pathlib.Path(__file__).resolve().parent.parent
HEADER = IOS.parent / "core" / "include" / "kervan_engine.h"
failures = []


def check(ok, message):
    if not ok:
        failures.append(message)


def swift_files(dirs):
    for d in dirs:
        yield from sorted((IOS / d).rglob("*.swift"))


def main():
    spec = yaml.safe_load((IOS / "project.yml").read_text())
    targets = spec["targets"]
    app, ext = targets["KervanDPI"], targets["KervanTunnel"]
    app_settings, ext_settings = app["settings"]["base"], ext["settings"]["base"]

    # Every source dir exists.
    for name, target in targets.items():
        for src in target["sources"]:
            check((IOS / src).is_dir(), f"{name}: source dir {src} missing")

    # Bundle IDs: the extension ID must be prefixed by the app ID (Apple rule),
    # and the Swift constants must match, or startVPNTunnel finds no provider.
    app_id = app_settings["PRODUCT_BUNDLE_IDENTIFIER"]
    ext_id = ext_settings["PRODUCT_BUNDLE_IDENTIFIER"]
    check(ext_id.startswith(app_id + "."), f"extension id {ext_id} not under {app_id}")
    identity = (IOS / "Shared" / "TunnelIdentity.swift").read_text()
    check(f'appBundleID = "{app_id}"' in identity, "TunnelIdentity.appBundleID != project.yml")
    check(f'providerBundleID = "{ext_id}"' in identity, "TunnelIdentity.providerBundleID != project.yml")

    # The app embeds the extension.
    check({"target": "KervanTunnel"} in app.get("dependencies", []), "app does not embed KervanTunnel")

    # Entitlements: both targets need the packet tunnel Network Extension value.
    for name, settings in (("KervanDPI", app_settings), ("KervanTunnel", ext_settings)):
        path = IOS / settings["CODE_SIGN_ENTITLEMENTS"]
        ent = plistlib.loads(path.read_bytes())
        values = ent.get("com.apple.developer.networking.networkextension", [])
        check(values == ["packet-tunnel-provider"], f"{name}: entitlements {values}")

    # Extension Info.plist points at a class that exists.
    info = plistlib.loads((IOS / ext_settings["INFOPLIST_FILE"]).read_bytes())
    nsext = info.get("NSExtension", {})
    check(nsext.get("NSExtensionPointIdentifier") == "com.apple.networkextension.packet-tunnel",
          "wrong NSExtensionPointIdentifier")
    principal = nsext.get("NSExtensionPrincipalClass", "")
    check(principal == "$(PRODUCT_MODULE_NAME).PacketTunnelProvider", f"principal class {principal}")
    ext_sources = "\n".join(p.read_text() for p in swift_files(ext["sources"]))
    check(re.search(r"class PacketTunnelProvider\s*:\s*NEPacketTunnelProvider", ext_sources) is not None,
          "no PacketTunnelProvider: NEPacketTunnelProvider in extension sources")

    # The xcframework is linked into the extension only.
    deps = ext.get("dependencies", [])
    check({"framework": "build/KervanCore.xcframework", "embed": False} in deps,
          "extension does not link build/KervanCore.xcframework")
    for path in swift_files(app["sources"]):
        check("import KervanCore" not in path.read_text(),
              f"{path.relative_to(IOS)} imports KervanCore but the app target does not link it")

    # Module map exposes the real header.
    modmap = (IOS / "KervanCore" / "module.modulemap").read_text()
    check(f'header "{HEADER.name}"' in modmap, "module.modulemap header name mismatch")

    # Every kv_/KV_ identifier used from Swift is declared in the C header.
    header = HEADER.read_text()
    declared = set(re.findall(r"\b(?:kv|KV)_[A-Za-z0-9_]+\b", header))
    used = set(re.findall(r"\b(?:kv|KV)_[A-Za-z0-9_]+\b", ext_sources))
    for ident in sorted(used - declared):
        check(False, f"Swift uses {ident}, not declared in {HEADER.name}")

    # Image assets referenced from SwiftUI exist.
    app_sources = "\n".join(p.read_text() for p in swift_files(app["sources"]))
    for asset in sorted(set(re.findall(r'Image\("([^"]+)"\)', app_sources))):
        check(any((IOS / s).rglob(f"{asset}.imageset") for s in app["sources"]),
              f"image asset {asset} missing")

    # XcodeGen sets ASSETCATALOG_COMPILER_APPICON_NAME=AppIcon for apps; the
    # first macOS build failed without it (run 45225923451).
    icon_sets = [p for s in app["sources"] for p in (IOS / s).rglob("AppIcon.appiconset")]
    check(len(icon_sets) == 1, "app target needs exactly one AppIcon.appiconset")
    for icon_set in icon_sets:
        contents = __import__("json").loads((icon_set / "Contents.json").read_text())
        for image in contents.get("images", []):
            name = image.get("filename")
            check(name is not None and (icon_set / name).is_file(), f"AppIcon image {name} missing")

    # About ships the license text of every engine component at its pinned commit.
    notices = (IOS / "KervanDPI" / "Acknowledgements.txt").read_text()
    third_party = (IOS.parent / "core" / "third_party" / "README.md").read_text()
    for commit in re.findall(r"`([0-9a-f]{40})`", third_party):
        check(commit in notices, f"Acknowledgements.txt lacks pinned commit {commit}")

    if failures:
        for f in failures:
            print("FAIL", f)
        return 1
    print(f"check_project: ok ({len(used)} C identifiers checked)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
