"""Offline contracts for the approved camel exports and Windows resources."""
import hashlib
import importlib.util
import struct
import sys
import unittest
from pathlib import Path

from PySide6.QtGui import QImage


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from metadata import (APP_NAME, APP_SLOGAN, COPYRIGHT, EXECUTABLE_NAME,
                      ORGANIZATION, VERSION)

spec = importlib.util.spec_from_file_location(
    "generate_kervan_icon", ROOT / "packaging/generate_kervan_icon.py")
icon_tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(icon_tool)


class WindowsBrandingTests(unittest.TestCase):
    def test_approved_source_and_deterministic_runtime_icon(self):
        source = ROOT / "assets/kervan-camel-source.png"
        self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(),
                         icon_tool.SOURCE_SHA256)
        rendered = icon_tool.isolate_camel(icon_tool.approved_source(source))
        regenerated = QImage.fromData(icon_tool.png_bytes(rendered, 256), "PNG")
        saved = QImage(str(ROOT / "assets/kervan-camel.png"))
        regenerated_rgba = regenerated.convertToFormat(QImage.Format.Format_RGBA8888)
        saved_rgba = saved.convertToFormat(QImage.Format.Format_RGBA8888)
        self.assertEqual(bytes(regenerated_rgba.bits()), bytes(saved_rgba.bits()))
        self.assertEqual(rendered.width(), rendered.height())

    def test_ico_frames_are_png_with_alpha_and_padding(self):
        blob = (ROOT / "assets/kervan-camel.ico").read_bytes()
        rendered = icon_tool.isolate_camel(icon_tool.approved_source(
            ROOT / "assets/kervan-camel-source.png"))
        self.assertEqual(struct.unpack_from("<HHH", blob), (0, 1, 7))
        sizes = []
        intervals = []
        for index in range(7):
            width, height, palette, reserved, planes, depth, length, offset = struct.unpack_from(
                "<BBBBHHII", blob, 6 + index * 16)
            size = 256 if width == 0 else width
            self.assertEqual(height, width)
            self.assertEqual((palette, reserved, planes, depth), (0, 0, 1, 32))
            frame = blob[offset:offset + length]
            self.assertTrue(frame.startswith(b"\x89PNG\r\n\x1a\n"))
            image = QImage.fromData(frame, "PNG")
            expected = QImage.fromData(icon_tool.png_bytes(rendered, size), "PNG")
            actual_rgba = image.convertToFormat(QImage.Format.Format_RGBA8888)
            expected_rgba = expected.convertToFormat(QImage.Format.Format_RGBA8888)
            self.assertEqual(bytes(actual_rgba.bits()), bytes(expected_rgba.bits()))
            self.assertEqual((image.width(), image.height()), (size, size))
            self.assertTrue(image.hasAlphaChannel())
            for x, y in ((0, 0), (size - 1, 0), (0, size - 1), (size - 1, size - 1)):
                self.assertEqual(image.pixelColor(x, y).alpha(), 0)
            self.assertTrue(any(image.pixelColor(x, y).alpha() > 200
                                for y in range(size) for x in range(size)))
            sizes.append(size)
            intervals.append((offset, offset + length))
        self.assertEqual(sizes, [16, 24, 32, 48, 64, 128, 256])
        self.assertEqual(intervals[0][0], 6 + 7 * 16)
        self.assertEqual(intervals[-1][1], len(blob))
        self.assertTrue(all(left[1] == right[0]
                            for left, right in zip(intervals, intervals[1:])))

    def test_runtime_icon_keeps_complete_camel_proportions(self):
        icon = QImage(str(ROOT / "assets/kervan-camel.png"))
        self.assertEqual((icon.width(), icon.height()), (256, 256))
        self.assertTrue(icon.hasAlphaChannel())
        visible = [(x, y) for y in range(256) for x in range(256)
                   if icon.pixelColor(x, y).alpha() >= 16]
        left = min(x for x, _ in visible)
        right = max(x for x, _ in visible)
        top = min(y for _, y in visible)
        bottom = max(y for _, y in visible)
        self.assertGreaterEqual(min(left, top, 255 - right, 255 - bottom), 10)
        self.assertLessEqual(max(left, top, 255 - right, 255 - bottom), 45)
        self.assertGreater((bottom - top + 1) / (right - left + 1), 0.78)
        self.assertLess((bottom - top + 1) / (right - left + 1), 0.85)

    def test_windows_and_qt_brand_references(self):
        self.assertEqual((APP_NAME, EXECUTABLE_NAME, APP_SLOGAN),
                         ("Kervan DPI", "Kervan-DPI", "Yol Açık, Kervan Yürür."))
        self.assertEqual(COPYRIGHT, "Copyright (c) 2026 MacallanTheRoot")
        self.assertEqual(ORGANIZATION, "MacallanTheRoot")
        self.assertEqual(VERSION, "1.0.1rc2")
        self.assertTrue(COPYRIGHT.isascii())
        windows_spec = (ROOT / "packaging/windows/goodbyedpi-turkey.spec").read_text(encoding="utf-8")
        for declaration in ("StringStruct('ProductName', APP_NAME)",
                            "StringStruct('FileDescription', APP_NAME)",
                            "StringStruct('InternalName', APP_NAME)",
                            "StringStruct('CompanyName', ORGANIZATION)",
                            "StringStruct('OriginalFilename', EXECUTABLE_NAME + '.exe')",
                            "StringStruct('ProductVersion', VERSION)",
                            "StringStruct('LegalCopyright', COPYRIGHT)",
                            "icon=str(brand_ico)", "uac_admin=False"):
            self.assertIn(declaration, windows_spec)
        self.assertIn("dist\\Kervan-DPI.exe", (ROOT / "build.bat").read_text(encoding="utf-8"))
        workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
        self.assertRegex(workflow, r"(?m)^\s+dist/Kervan-DPI\.exe$")
        self.assertNotIn("path: dist/GoodbyeDPI-Turkey.exe", workflow)
        package = (ROOT / "tools/windows/package_rc.ps1").read_text(encoding="utf-8")
        for field in ("$properties.InternalName", "$properties.OriginalFilename",
                      "$properties.LegalCopyright", "$properties.CompanyName"):
            self.assertIn(field, package)
        for source in ("src/main.py", "src/app_controller.py",
                       "src/ui/views/main_window.py", "src/ui/widgets/app_header.py"):
            self.assertIn('"kervan-camel.png"', (ROOT / source).read_text(encoding="utf-8"))
        self.assertIn("Kervan DPI.lnk", (ROOT / "src/utils/startup.py").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
