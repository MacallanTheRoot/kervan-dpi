"""Read-only inspection of the exact native PyInstaller Windows candidate.

Run with the build environment's Python after build.bat. This checks archive
members byte for byte; it does not replace Windows lifecycle or icon QA.
"""
import argparse
from hashlib import sha256
from pathlib import Path

from PyInstaller.archive.readers import CArchiveReader


ROOT = Path(__file__).resolve().parents[2]
ENGINE_FILES = (
    "bin/x86/goodbyedpi.exe", "bin/x86/WinDivert.dll",
    "bin/x86/WinDivert32.sys", "bin/x86/WinDivert64.sys",
    "bin/x86_64/goodbyedpi.exe", "bin/x86_64/WinDivert.dll",
    "bin/x86_64/WinDivert64.sys",
)
NOTICE_FILES = (
    "LICENSE", "THIRD_PARTY_NOTICES.md",
    "bin/licenses/LICENSE-getline.txt",
    "bin/licenses/LICENSE-goodbyedpi.txt",
    "bin/licenses/LICENSE-uthash.txt",
    "bin/licenses/LICENSE-windivert.txt",
)


def required_members(root=ROOT):
    paths = ("assets/kervan-camel.png", *ENGINE_FILES, *NOTICE_FILES)
    members = {path.replace("/", "\\"): root / path for path in paths}
    members.update({
        "licenses\\GPL-3.0.txt": root / "packaging/licenses/GPL-3.0.txt",
        "licenses\\LGPL-3.0.txt": root / "packaging/licenses/LGPL-3.0.txt",
    })
    return members


def validate_archive(reader, root=ROOT):
    entries = {name.replace("/", "\\"): name for name in reader.toc}
    if "assets\\icon.png" in entries or "assets\\icon.ico" in entries:
        raise ValueError("Legacy shield icon was bundled in the Kervan candidate")
    for member, source in required_members(root).items():
        if member not in entries:
            raise ValueError(f"Missing frozen resource: {member}")
        if sha256(reader.extract(entries[member])).digest() != sha256(source.read_bytes()).digest():
            raise ValueError(f"Frozen resource differs from source: {member}")
    for qt_name in ("Qt6Core.dll", "Qt6Gui.dll", "Qt6Widgets.dll"):
        if not any(name.endswith("\\" + qt_name) for name in entries):
            raise ValueError(f"Missing frozen Qt library: {qt_name}")
    return len(entries)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("exe", nargs="?", default="dist/Kervan-DPI.exe")
    args = parser.parse_args()
    exe = Path(args.exe)
    if exe.name != "Kervan-DPI.exe" or not exe.is_file():
        parser.error("A native Kervan-DPI.exe file is required")
    with exe.open("rb") as stream:
        if stream.read(2) != b"MZ":
            raise ValueError("Candidate is not a PE executable")
    count = validate_archive(CArchiveReader(str(exe)))
    print(f"Kervan-DPI.exe: {exe.stat().st_size} bytes; SHA-256 {sha256(exe.read_bytes()).hexdigest()}")
    print(f"PyInstaller members: {count}; engine, logo, notices and Qt libraries: PASS")


if __name__ == "__main__":
    main()
