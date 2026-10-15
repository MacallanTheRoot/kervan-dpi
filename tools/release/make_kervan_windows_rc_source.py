"""Create a deterministic, branded Windows RC build-source archive.

This deliberately stops until the approved camel source and exports exist.
It never creates a Windows executable on a non-Windows host.
"""
import argparse
from hashlib import sha256
from io import BytesIO
from pathlib import Path
import re
import sys
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from metadata import VERSION


NAME = f"Kervan-DPI-{VERSION}-windows-rc-build-source"
FILES = (
    "LICENSE", "THIRD_PARTY_NOTICES.md", "README.md", "docs/README.tr.md",
    "docs/linux-development.md",
    "requirements.txt", "requirements-windows-rc.txt",
    ".github/workflows/ci.yml",  # branding regression fixture
    "build.bat", "prepare_windows_native_test.bat",
    "assets/kervan-camel.png", "assets/kervan-camel.ico",
    "assets/icon.png",  # legacy resource-path regression fixture; not bundled in branded EXE
    "bin/x86/goodbyedpi.exe", "bin/x86/WinDivert.dll",
    "bin/x86/WinDivert32.sys", "bin/x86/WinDivert64.sys",
    "bin/x86_64/goodbyedpi.exe", "bin/x86_64/WinDivert.dll",
    "bin/x86_64/WinDivert64.sys",
    "bin/licenses/LICENSE-getline.txt", "bin/licenses/LICENSE-goodbyedpi.txt",
    "bin/licenses/LICENSE-uthash.txt", "bin/licenses/LICENSE-windivert.txt",
    "packaging/licenses/GPL-3.0.txt", "packaging/licenses/LGPL-3.0.txt",
    "packaging/windows/goodbyedpi-turkey.spec",
    "packaging/debian/build_deb.sh",  # identity regression fixture
    "packaging/linux/goodbyedpi-turkey.desktop",
    "packaging/generate_kervan_icon.py",
    "tools/windows/validate_rc.ps1", "tools/windows/package_rc.ps1",
    "tools/windows/build_rc.ps1", "tools/windows/inspect_rc.py",
    "tools/windows/inspect_portable.py",
    "tools/release/make_kervan_windows_rc_source.py",
    "tools/release/update_manifest.py",
    "docs/qt-lgpl-compliance.md", "docs/release/windows-build.md",
    "docs/release/windows-qa-checklist.md", "docs/release/windows-migration.md",
    "docs/release/windows-native-qa-report-template.md",
    "docs/release/kervan-dpi-release-notes.md",
    "docs/releases/kervan-dpi-windows-release-notes.md",
    "docs/release/kervan-dpi-readiness.md",
    "docs/release/windows-dependencies.md",
    "docs/release/windows-engine-inputs.md",
    "docs/release/windows-update.md",
    "docs/branding/kervan-brand-asset-requirements.md",
    "docs/branding/kervan-camel-source.md",
    "docs/packaging-rc.md",
    "docs/engineering/phase-7h-nightshift-final-report.md",
    "docs/engineering/kervan-phase8b-qa.md",
)
TESTS = (
    "test_brand_migration.py", "test_lifecycle.py", "test_packaging.py",
    "test_platform_foundation.py", "test_qt_ui.py", "test_windows_branding.py",
    "test_windows_distribution.py",
    "test_updates.py", "test_update_install.py",
)
INPUT_MANIFEST = "SOURCE-INPUTS-SHA256SUMS.txt"


def source_files():
    artwork = list((ROOT / "assets").glob("kervan-camel-source.*"))
    if len(artwork) != 1:
        raise RuntimeError("Exactly one approved camel source artwork is required")
    paths = [ROOT / name for name in FILES]
    paths += artwork
    paths += sorted((ROOT / "src").rglob("*.py"))
    paths += [ROOT / "tests" / name for name in TESTS]
    for path in sorted(set(paths)):
        if not path.is_file() or path.is_symlink():
            raise RuntimeError(f"Missing or linked package input: {path}")
        yield path, path.relative_to(ROOT)


def archive_bytes(inputs):
    """Serialize source files and their SHA-256 inventory without touching disk."""
    buffer = BytesIO()
    manifest = "".join(
        f"{sha256(path.read_bytes()).hexdigest()}  {relative.as_posix()}\n"
        for path, relative in inputs
    ).encode("ascii")
    with ZipFile(buffer, "w", ZIP_DEFLATED, compresslevel=9) as archive:
        for path, relative in inputs:
            item = ZipInfo(f"{NAME}/{relative.as_posix()}", (1980, 1, 1, 0, 0, 0))
            item.compress_type = ZIP_DEFLATED
            item.external_attr = 0o100644 << 16
            archive.writestr(item, path.read_bytes(), compress_type=ZIP_DEFLATED,
                             compresslevel=9)
        item = ZipInfo(f"{NAME}/{INPUT_MANIFEST}", (1980, 1, 1, 0, 0, 0))
        item.compress_type = ZIP_DEFLATED
        item.external_attr = 0o100644 << 16
        archive.writestr(item, manifest, compress_type=ZIP_DEFLATED,
                         compresslevel=9)
    return buffer.getvalue()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--handoff", default="", help="unique lowercase handoff suffix")
    args = parser.parse_args()
    if args.handoff and not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", args.handoff):
        parser.error("--handoff must contain lowercase letters, digits or hyphens")
    suffix = f"-{args.handoff}" if args.handoff else ""
    inputs = list(source_files())
    payload = archive_bytes(inputs)
    output = ROOT / "dist" / f"{NAME}{suffix}.zip"
    output.parent.mkdir(exist_ok=True)
    if output.exists():
        if output.read_bytes() != payload:
            raise RuntimeError(f"Existing source archive differs; refusing to overwrite: {output}")
    else:
        output.write_bytes(payload)
    with ZipFile(output) as archive:
        if archive.testzip() is not None or len(archive.namelist()) != len(inputs) + 1:
            raise RuntimeError("Source archive failed integrity verification")
        for path, relative in inputs:
            if archive.read(f"{NAME}/{relative.as_posix()}") != path.read_bytes():
                raise RuntimeError(f"Source archive differs from working tree: {relative}")
        manifest = archive.read(f"{NAME}/{INPUT_MANIFEST}").decode("ascii")
        for line in manifest.splitlines():
            digest, relative = line.split("  ", 1)
            if sha256(archive.read(f"{NAME}/{relative}")).hexdigest() != digest:
                raise RuntimeError(f"Source manifest differs: {relative}")
    digest = sha256(output.read_bytes()).hexdigest()
    manifest = ROOT / "dist" / f"Kervan-DPI-{VERSION}{suffix}-SOURCE-SHA256SUMS.txt"
    manifest_text = f"{digest}  {output.name}\n"
    if manifest.exists() and manifest.read_text(encoding="ascii") != manifest_text:
        raise RuntimeError(f"Existing checksum manifest differs; refusing to overwrite: {manifest}")
    if not manifest.exists():
        manifest.write_text(manifest_text, encoding="ascii")
    print(f"{output}\n{output.stat().st_size} bytes\nSHA-256 {digest}\n{len(inputs)} inputs plus manifest")


if __name__ == "__main__":
    main()
