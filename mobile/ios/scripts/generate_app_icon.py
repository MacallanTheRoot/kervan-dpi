#!/usr/bin/env python3
"""Generate the iOS app icon from the approved Kervan camel mark.

Source: site/assets/kervan-camel.png (256 px RGBA), the same mark the
Android launcher icons use (mobile/android/tools/generate_icons.py).
iOS 17 needs one opaque 1024 px icon. The mark is upscaled to fit it, so it
is softer than a vector original would be; replace it once a 1024 px master
exists. Run from the repo root: python3 mobile/ios/scripts/generate_app_icon.py
"""
import json
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "site/assets/kervan-camel.png"
OUT = ROOT / "mobile/ios/KervanDPI/Assets.xcassets/AppIcon.appiconset"
SIZE = 1024
MARK = 640  # about 62 % of the canvas, inside the rounded-corner mask

camel = Image.open(SRC).convert("RGBA")
camel = camel.crop(camel.getbbox())
scale = MARK / max(camel.size)
mark = camel.resize((round(camel.width * scale), round(camel.height * scale)), Image.LANCZOS)

icon = Image.new("RGBA", (SIZE, SIZE), (255, 255, 255, 255))
icon.alpha_composite(mark, ((SIZE - mark.width) // 2, (SIZE - mark.height) // 2))
OUT.mkdir(parents=True, exist_ok=True)
icon.convert("RGB").save(OUT / "AppIcon-1024.png")  # no alpha channel
(OUT / "Contents.json").write_text(json.dumps({
    "images": [{"filename": "AppIcon-1024.png", "idiom": "universal",
                "platform": "ios", "size": "1024x1024"}],
    "info": {"author": "xcode", "version": 1},
}, indent=2) + "\n")
print(f"wrote {OUT}")
