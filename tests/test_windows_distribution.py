"""Deterministic source and archive contracts; no native EXE is made here."""
from hashlib import sha256
from io import BytesIO
import importlib.util
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from zipfile import ZIP_DEFLATED, ZipFile


ROOT = Path(__file__).resolve().parents[1]


def load_tool(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


source_tool = load_tool("kervan_source", "tools/release/make_kervan_windows_rc_source.py")
exe_tool = load_tool("kervan_exe_inspector", "tools/windows/inspect_rc.py")
portable_tool = load_tool("kervan_portable_inspector", "tools/windows/inspect_portable.py")


class FakeArchive:
    def __init__(self, entries):
        self.entries = entries
        self.toc = {name: None for name in entries}

    def extract(self, name):
        return self.entries[name]


class WindowsDistributionTests(unittest.TestCase):
    def test_powershell_51_ascii_copyright_comparison(self):
        from metadata import COPYRIGHT
        script = (ROOT / "tools/windows/package_rc.ps1").read_bytes()
        # Windows PowerShell 5.1 may decode a BOM-less script with an ANSI code
        # page, so both source text and expected metadata are ASCII-only.
        self.assertEqual(COPYRIGHT, "Copyright (c) 2026 MacallanTheRoot")
        self.assertTrue(script.isascii())
        self.assertIn(b"$expectedCopyright = 'Copyright (c) 2026 MacallanTheRoot'", script)
        self.assertIn(b"$properties.LegalCopyright -ne $expectedCopyright", script)

    def test_source_archive_is_stable_and_has_input_hashes(self):
        inputs = list(source_tool.source_files())
        payload = source_tool.archive_bytes(inputs)
        self.assertEqual(payload, source_tool.archive_bytes(inputs))
        with ZipFile(BytesIO(payload)) as archive:
            self.assertIsNone(archive.testzip())
            names = archive.namelist()
            self.assertEqual(len(names), len(inputs) + 1)
            self.assertIn(f"{source_tool.NAME}/tools/windows/build_rc.ps1", names)
            self.assertIn(f"{source_tool.NAME}/tools/release/update_manifest.py", names)
            self.assertIn(f"{source_tool.NAME}/requirements-windows-rc.txt", names)
            self.assertIn(f"{source_tool.NAME}/src/utils/updates.py", names)
            self.assertIn(f"{source_tool.NAME}/src/utils/update_install.py", names)
            self.assertIn(f"{source_tool.NAME}/tests/test_updates.py", names)
            self.assertIn(f"{source_tool.NAME}/tests/test_update_install.py", names)
            self.assertIn(f"{source_tool.NAME}/assets/kervan-camel.ico", names)
            self.assertIn(f"{source_tool.NAME}/bin/x86_64/WinDivert64.sys", names)
            manifest = archive.read(f"{source_tool.NAME}/{source_tool.INPUT_MANIFEST}").decode("ascii")
            for line in manifest.splitlines():
                digest, relative = line.split("  ", 1)
                self.assertEqual(sha256(archive.read(f"{source_tool.NAME}/{relative}")).hexdigest(), digest)
            self.assertEqual(len(manifest.splitlines()), len(inputs))

    def test_frozen_engine_and_notice_members_match_source(self):
        entries = {name: path.read_bytes() for name, path in exe_tool.required_members().items()}
        entries.update({f"PySide6\\{name}": b"test Qt fixture"
                        for name in ("Qt6Core.dll", "Qt6Gui.dll", "Qt6Widgets.dll")})
        self.assertEqual(exe_tool.validate_archive(FakeArchive(entries)), len(entries))
        entries["bin\\x86_64\\WinDivert.dll"] += b"tampered"
        with self.assertRaisesRegex(ValueError, "differs from source"):
            exe_tool.validate_archive(FakeArchive(entries))
        entries["assets\\icon.png"] = b"legacy"
        with self.assertRaisesRegex(ValueError, "Legacy shield"):
            exe_tool.validate_archive(FakeArchive(entries))

    def test_portable_contents_and_readme_links(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fixture.zip"
            exe = Path(directory) / "fixture.exe"
            exe.write_bytes(b"fixture only; not a Windows EXE")
            files = set(portable_tool.REQUIRED) - {"Kervan-DPI.exe"}
            files.update(path.relative_to(ROOT).as_posix()
                         for path in (ROOT / "docs").rglob("*.md"))
            with ZipFile(path, "w", ZIP_DEFLATED) as archive:
                archive.writestr("fixture/Kervan-DPI.exe", exe.read_bytes())
                for relative in sorted(files):
                    archive.write(ROOT / relative, "fixture/" + relative)
            self.assertEqual(portable_tool.validate_zip(path, exe), len(files) + 1)
            exe.write_bytes(b"changed")
            with self.assertRaisesRegex(ValueError, "differs from native build"):
                portable_tool.validate_zip(path, exe)

    def test_engine_staging_hashes_and_safe_interpreter_selection(self):
        inventory = (ROOT / "docs/release/windows-engine-inputs.md").read_text(encoding="utf-8")
        for arch, names in (("x86", ("goodbyedpi.exe", "WinDivert.dll",
                                     "WinDivert32.sys", "WinDivert64.sys")),
                            ("x86_64", ("goodbyedpi.exe", "WinDivert.dll",
                                        "WinDivert64.sys"))):
            digest = sha256()
            for name in names:
                digest.update(name.encode("ascii"))
                payload = (ROOT / "bin" / arch / name).read_bytes()
                digest.update(payload)
                self.assertIn(sha256(payload).hexdigest(), inventory)
            self.assertIn(digest.hexdigest(), inventory)
        native = (ROOT / "tools/windows/build_rc.ps1").read_text(encoding="utf-8")
        batch = (ROOT / "build.bat").read_text(encoding="utf-8")
        self.assertIn("py -3.13", native)
        self.assertIn("Existing .venv, build or dist paths were left untouched", native)
        self.assertIn("sys.version_info[:2] == (3,13)", batch)
        self.assertNotIn("py -3 -m venv", native)

    def test_powershell_version_argument_reaches_python_intact(self):
        native = (ROOT / "tools/windows/build_rc.ps1").read_text(encoding="utf-8")
        package = (ROOT / "tools/windows/package_rc.ps1").read_text(encoding="utf-8")
        match = re.search(r'^\$version = & py -3\.13 -c "([^"]+)"$', native, re.MULTILINE)
        self.assertIsNotNone(match)
        program = match.group(1)
        self.assertEqual(program, "from src.metadata import VERSION; print(VERSION)")
        self.assertIn(f'-c "{program}"', package)
        shell = shutil.which("powershell.exe" if os.name == "nt" else "pwsh")
        if shell:
            interpreter = "py -3.13" if os.name == "nt" else f"'{sys.executable}'"
            completed = subprocess.run(
                [shell, "-NoProfile", "-NonInteractive", "-Command",
                 f'& {interpreter} -c "{program}"'],
                cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertEqual(completed.stdout.strip(), source_tool.VERSION)


if __name__ == "__main__":
    unittest.main()
