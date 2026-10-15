"""Export the approved blue camel PNG as transparent Qt and Windows icons.

The original RGB artwork has a dark navy background. The fixed chroma mask
removes only that background; the camel pixels and proportions are retained.
The input hash prevents an unrelated image from silently becoming the logo.
"""
import argparse
import hashlib
import shutil
import struct
from pathlib import Path

from PySide6.QtCore import QBuffer, QByteArray, QIODevice, Qt
from PySide6.QtGui import QImage


ROOT = Path(__file__).resolve().parents[1]
SIZES = (16, 24, 32, 48, 64, 128, 256)
SOURCE_SHA256 = "ee6ebe53c70be47126777e836485ef36e525cb994d6a384f199018a4368835d5"
SOURCE_NAME = "kervan-camel-source.png"
BACKGROUND_RGB = (6, 14, 39)


def approved_source(path: Path) -> QImage:
    if not path.is_file() or path.is_symlink():
        raise ValueError("Approved source must be a regular, non-linked PNG")
    if hashlib.sha256(path.read_bytes()).hexdigest() != SOURCE_SHA256:
        raise ValueError("Source hash differs from the approved blue camel artwork")
    image = QImage(str(path))
    if image.isNull() or (image.width(), image.height()) != (1254, 1254):
        raise ValueError("Approved camel source must be the 1254x1254 PNG")
    return image.convertToFormat(QImage.Format.Format_RGBA8888)


def isolate_camel(source: QImage) -> QImage:
    """Recover an alpha edge from green-red chroma; keep full geometry."""
    image = source.copy()
    pixels = image.bits()
    width = image.width()
    min_x, min_y, max_x, max_y = width, image.height(), -1, -1
    for y in range(image.height()):
        for x in range(width):
            i = (y * width + x) * 4
            red, green, blue = pixels[i], pixels[i + 1], pixels[i + 2]
            chroma = green - red
            alpha = 0 if chroma <= 12 else (255 if chroma >= 65 else
                                          round((chroma - 12) * 255 / 53))
            if alpha == 0:
                pixels[i:i + 4] = b"\x00\x00\x00\x00"
                continue
            if alpha < 255:
                for channel, matte in enumerate(BACKGROUND_RGB):
                    value = round((pixels[i + channel] * 255 - matte * (255 - alpha)) / alpha)
                    pixels[i + channel] = max(0, min(255, value))
            pixels[i + 3] = alpha
            if alpha >= 16:
                min_x, min_y = min(min_x, x), min(min_y, y)
                max_x, max_y = max(max_x, x), max(max_y, y)
    if max_x < min_x or max_y < min_y:
        raise ValueError("No camel silhouette found in approved source")

    # Center the complete silhouette in a square with 8% padding on each side.
    span = max(max_x - min_x + 1, max_y - min_y + 1)
    padding = round(span * 0.08)
    side = span + 2 * padding
    canvas = QImage(side, side, QImage.Format.Format_RGBA8888)
    canvas.fill(Qt.GlobalColor.transparent)
    output = canvas.bits()
    left = (side - (max_x - min_x + 1)) // 2
    top = (side - (max_y - min_y + 1)) // 2
    for y in range(min_y, max_y + 1):
        start = (y * width + min_x) * 4
        end = start + (max_x - min_x + 1) * 4
        dest = ((top + y - min_y) * side + left) * 4
        output[dest:dest + end - start] = pixels[start:end]
    return canvas


def _axis_samples(source_size: int, target_size: int):
    """Map pixel centers with exact integer fractions and clamped edges."""
    denominator = 2 * target_size
    for coordinate in range(target_size):
        numerator = (2 * coordinate + 1) * source_size - target_size
        first, fraction = divmod(numerator, denominator)
        if first < 0:
            yield 0, 0, denominator, 0
        elif first >= source_size - 1:
            yield source_size - 1, source_size - 1, denominator, 0
        else:
            yield first, first + 1, denominator - fraction, fraction


def scale_rgba(image: QImage, size: int) -> QImage:
    """Bilinear scaling in premultiplied alpha with platform independent rounding."""
    source = image.convertToFormat(QImage.Format.Format_RGBA8888)
    width, height = source.width(), source.height()
    if width != height:
        raise ValueError("Camel icon canvas must be square")
    pixels = source.bits()
    result = QImage(size, size, QImage.Format.Format_RGBA8888)
    target = result.bits()
    samples = list(_axis_samples(width, size))
    divisor = (2 * size) ** 2
    for y, (y0, y1, wy0, wy1) in enumerate(samples):
        for x, (x0, x1, wx0, wx1) in enumerate(samples):
            corners = ((y0, x0, wy0 * wx0), (y0, x1, wy0 * wx1),
                       (y1, x0, wy1 * wx0), (y1, x1, wy1 * wx1))
            alpha_sum = 0
            color_sums = [0, 0, 0]
            for sy, sx, weight in corners:
                index = (sy * width + sx) * 4
                alpha = pixels[index + 3]
                weighted_alpha = weight * alpha
                alpha_sum += weighted_alpha
                for channel in range(3):
                    color_sums[channel] += weighted_alpha * pixels[index + channel]
            dest = (y * size + x) * 4
            target[dest + 3] = (alpha_sum + divisor // 2) // divisor
            for channel in range(3):
                target[dest + channel] = ((color_sums[channel] + alpha_sum // 2)
                                          // alpha_sum) if alpha_sum else 0
    return result


def png_bytes(image: QImage, size: int) -> bytes:
    scaled = scale_rgba(image, size)
    data = QByteArray()
    buffer = QBuffer(data)
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    if not scaled.save(buffer, "PNG"):
        raise RuntimeError(f"Cannot encode {size}px icon")
    return bytes(data)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="the approved Minimalist Mavi Deve İkonu.png")
    args = parser.parse_args()
    source_path = args.source.expanduser().absolute()
    image = isolate_camel(approved_source(source_path))
    assets = ROOT / "assets"
    master = assets / SOURCE_NAME
    if source_path != master:
        shutil.copyfile(source_path, master)
    (assets / "kervan-camel.png").write_bytes(png_bytes(image, 256))
    frames = [(size, png_bytes(image, size)) for size in SIZES]
    offset = 6 + 16 * len(frames)
    with (assets / "kervan-camel.ico").open("wb") as target:
        target.write(struct.pack("<HHH", 0, 1, len(frames)))
        for size, blob in frames:
            target.write(struct.pack("<BBBBHHII", size if size < 256 else 0,
                                     size if size < 256 else 0, 0, 0, 1, 32,
                                     len(blob), offset))
            offset += len(blob)
        for _, blob in frames:
            target.write(blob)
    for path in (master, assets / "kervan-camel.png", assets / "kervan-camel.ico"):
        print(f"{path.relative_to(ROOT)}  SHA-256 {hashlib.sha256(path.read_bytes()).hexdigest()}")
    print("Inspect the 16/24/32/48/64/128/256 px frames on native Windows before release.")


if __name__ == "__main__":
    main()
