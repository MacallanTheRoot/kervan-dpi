"""Generate Android launcher icons from the approved Kervan camel mark.

Source: site/assets/kervan-camel.png (256 px RGBA, same mark as the desktop
Windows Fix04 header). Never upscales the source beyond 256 px.
Run from repo root: python3 mobile/android/tools/generate_icons.py
"""
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "site/assets/kervan-camel.png"
RES = ROOT / "mobile/android/app/src/main/res"
DENSITIES = {"mdpi": 1, "hdpi": 1.5, "xhdpi": 2, "xxhdpi": 3, "xxxhdpi": 4}

camel = Image.open(SRC).convert("RGBA")
camel = camel.crop(camel.getbbox())

def fit(size_px):
    im = camel.copy()
    im.thumbnail((size_px, size_px), Image.LANCZOS)
    return im

for name, scale in DENSITIES.items():
    # Adaptive foreground: 108dp canvas, mark inside the 66dp safe zone (~58dp).
    canvas = int(108 * scale)
    fg = Image.new("RGBA", (canvas, canvas), (0, 0, 0, 0))
    mark = fit(int(58 * scale))
    fg.alpha_composite(mark, ((canvas - mark.width) // 2, (canvas - mark.height) // 2))
    out = RES / f"mipmap-{name}"
    out.mkdir(parents=True, exist_ok=True)
    fg.save(out / "ic_launcher_foreground.png")
    # Legacy square icon (48dp) on white.
    legacy = int(48 * scale)
    sq = Image.new("RGBA", (legacy, legacy), (255, 255, 255, 255))
    mark = fit(int(38 * scale))
    sq.alpha_composite(mark, ((legacy - mark.width) // 2, (legacy - mark.height) // 2))
    sq.save(out / "ic_launcher.png")

nodpi = RES / "drawable-nodpi"
nodpi.mkdir(parents=True, exist_ok=True)
camel.save(nodpi / "kervan_camel.png")
print("icons written to", RES)
