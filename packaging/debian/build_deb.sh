#!/usr/bin/env bash
set -euo pipefail
repo_dir="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$repo_dir"
case "$(uname -m)" in
  x86_64|amd64) ;;
  *) echo "Debian packages currently support amd64 only." >&2; exit 1 ;;
esac
if ! command -v dpkg-deb >/dev/null; then
  echo "dpkg-deb is required." >&2; exit 1
fi
if [[ ! -x .venv/bin/python || ! -x dist/goodbyedpi-turkey/goodbyedpi-turkey ]]; then
  echo "Build the Linux onedir bundle first." >&2; exit 1
fi
version="$(.venv/bin/python -c 'import sys; sys.path.insert(0, "src"); from metadata import DEBIAN_VERSION; print(DEBIAN_VERSION)')"
maintainer="$(.venv/bin/python -c 'import sys; sys.path.insert(0, "src"); from metadata import MAINTAINER; print(MAINTAINER)')"
stage="$(mktemp -d)"
trap 'rm -rf -- "$stage"' EXIT
chmod 755 "$stage"
DESTDIR="$stage" packaging/linux/install.sh
install -d -m 755 "$stage/usr/bin"
mv "$stage/usr/local/bin/goodbyedpi-turkey" "$stage/usr/bin/goodbyedpi-turkey"
rmdir "$stage/usr/local/bin" "$stage/usr/local"
install -d -m 755 "$stage/DEBIAN"
installed_size="$(du -sk "$stage/opt" "$stage/usr" | awk '{sum += $1} END {print sum}')"
cat > "$stage/DEBIAN/control" <<CONTROL
Package: goodbyedpi-turkey
Version: $version
Architecture: amd64
Maintainer: $maintainer
Section: net
Priority: optional
Installed-Size: $installed_size
Depends: libc6, libstdc++6
Homepage: https://github.com/MacallanTheRoot/GoodbyeDPI-Turkey-GUI
Description: Kervan DPI desktop controller for DPI-related access restrictions
 On Linux, this GUI controls an independently installed SpoofDPI v0.12.0
 local HTTP proxy on 127.0.0.1:8080. It does not configure the system proxy.
 SpoofDPI is not bundled or installed by this package.
CONTROL
chmod 644 "$stage/DEBIAN/control"
mkdir -p dist
artifact="dist/goodbyedpi-turkey_${version}_amd64.deb"
dpkg-deb --build --root-owner-group "$stage" "$artifact"
echo "$artifact"
