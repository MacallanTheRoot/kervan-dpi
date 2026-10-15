"""Check the native portable ZIP and its locally linked user documentation."""
import argparse
from hashlib import sha256
from pathlib import Path
import posixpath
import re
from urllib.parse import unquote
from zipfile import ZipFile


ROOT = Path(__file__).resolve().parents[2]
REQUIRED = (
    "Kervan-DPI.exe", "README.md", "LICENSE", "THIRD_PARTY_NOTICES.md",
    "assets/kervan-camel.png", "docs/README.tr.md",
    "docs/linux-development.md", "docs/release/windows-build.md",
    "docs/release/windows-migration.md", "docs/qt-lgpl-compliance.md",
    "bin/licenses/LICENSE-goodbyedpi.txt",
    "bin/licenses/LICENSE-windivert.txt",
    "packaging/licenses/GPL-3.0.txt",
    "packaging/licenses/LGPL-3.0.txt",
)


def validate_zip(archive_path, exe_path, root=ROOT):
    archive_path = Path(archive_path)
    exe_path = Path(exe_path)
    prefix = archive_path.stem + "/"
    with ZipFile(archive_path) as archive:
        if archive.testzip() is not None:
            raise ValueError("Portable ZIP failed CRC validation")
        entries = set(archive.namelist())
        for relative in REQUIRED:
            if prefix + relative not in entries:
                raise ValueError(f"Portable ZIP lacks {relative}")
        if sha256(archive.read(prefix + "Kervan-DPI.exe")).digest() != sha256(exe_path.read_bytes()).digest():
            raise ValueError("Portable EXE differs from native build")
        for file in (root / "docs").rglob("*.md"):
            relative = file.relative_to(root).as_posix()
            if prefix + relative not in entries or archive.read(prefix + relative) != file.read_bytes():
                raise ValueError(f"Portable documentation differs or is missing: {relative}")
        for relative in ("README.md", "docs/README.tr.md"):
            document = archive.read(prefix + relative).decode("utf-8")
            for link in re.findall(r"!?\[[^\]]*\]\(([^)]+)\)", document):
                if link.startswith(("https://", "http://", "#", "mailto:")):
                    continue
                target = posixpath.normpath(posixpath.join(
                    posixpath.dirname(relative), unquote(link.split("#", 1)[0])))
                if prefix + target not in entries:
                    raise ValueError(f"Portable README link is missing: {relative} -> {target}")
        return len(entries)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive")
    parser.add_argument("exe", nargs="?", default="dist/Kervan-DPI.exe")
    args = parser.parse_args()
    count = validate_zip(args.archive, args.exe)
    print(f"Portable ZIP: {count} entries; native EXE, notices and README links: PASS")


if __name__ == "__main__":
    main()
