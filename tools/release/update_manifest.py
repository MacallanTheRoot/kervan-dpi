"""Prepare and sign a Windows update manifest with an external Ed25519 key.

The private key is never generated or copied by this tool. Keep it outside the
repository and outside distribution archives. Sign only after native QA.
"""
import argparse
from hashlib import sha256
from pathlib import Path
import sys

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from utils.update_install import MAX_EXE_SIZE, canonical_manifest, verify_manifest
from utils.updates import REPOSITORY, Version


def prepare(exe, version):
    exe = Path(exe)
    if exe.name != "Kervan-DPI.exe" or not exe.is_file():
        raise ValueError("A native Kervan-DPI.exe is required")
    with exe.open("rb") as stream:
        if stream.read(2) != b"MZ":
            raise ValueError("A native Kervan-DPI.exe is required")
    if not 0 < exe.stat().st_size <= MAX_EXE_SIZE:
        raise ValueError("Executable size is outside update limits")
    digest = sha256()
    with exe.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return canonical_manifest({"schema": 1, "repository": REPOSITORY,
                               "version": Version.parse(version).canonical,
                               "asset": exe.name, "size": exe.stat().st_size,
                               "sha256": digest.hexdigest()})


def sign(payload, private_key_pem):
    key = serialization.load_pem_private_key(private_key_pem, password=None)
    if not isinstance(key, Ed25519PrivateKey):
        raise ValueError("An Ed25519 private key is required")
    return key.sign(payload)


def write_new(path, data):
    with Path(path).open("xb") as stream:
        stream.write(data)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    create = commands.add_parser("prepare")
    create.add_argument("--exe", required=True)
    create.add_argument("--version", required=True)
    create.add_argument("--output", required=True)
    signing = commands.add_parser("sign")
    signing.add_argument("--manifest", required=True)
    signing.add_argument("--private-key", required=True)
    signing.add_argument("--output", required=True)
    verifying = commands.add_parser("verify")
    verifying.add_argument("--manifest", required=True)
    verifying.add_argument("--signature", required=True)
    verifying.add_argument("--public-key-hex", required=True)
    verifying.add_argument("--version", required=True)
    args = parser.parse_args()
    if args.command == "prepare":
        write_new(args.output, prepare(args.exe, args.version))
    elif args.command == "sign":
        if Path(args.private_key).resolve().is_relative_to(ROOT):
            raise ValueError("Production private key must stay outside the repository")
        write_new(args.output, sign(Path(args.manifest).read_bytes(),
                                    Path(args.private_key).read_bytes()))
    else:
        verify_manifest(Path(args.manifest).read_bytes(), Path(args.signature).read_bytes(),
                        bytes.fromhex(args.public_key_hex), args.version)
        print("Signed update manifest: PASS")


if __name__ == "__main__":
    main()
