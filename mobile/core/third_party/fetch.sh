#!/usr/bin/env bash
# Fetch pinned upstream sources for the Kervan mobile core.
# Sources land in third_party/src/ (git-ignored). Re-run is idempotent.
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p src

fetch() { # name url commit
    local name=$1 url=$2 commit=$3 dir="src/$1"
    if [ -d "$dir/.git" ] && [ "$(git -C "$dir" rev-parse HEAD)" = "$commit" ]; then
        echo "$name: $commit (cached)"; return
    fi
    rm -rf "$dir"
    git init -q "$dir"
    git -C "$dir" remote add origin "$url"
    git -C "$dir" fetch -q --depth 1 origin "$commit"
    git -C "$dir" checkout -q FETCH_HEAD
    echo "$name: $(git -C "$dir" rev-parse HEAD)"
}

fetch byedpi https://github.com/hufrea/byedpi.git e2684772fbda45f2ff4fc220922a010370534216
fetch hev-socks5-tunnel https://github.com/heiher/hev-socks5-tunnel.git fc3f90040b8d4b537341c96538669a9b2e35d514
# Submodules pinned by the hev-socks5-tunnel commit above.
git -C src/hev-socks5-tunnel submodule update -q --init --recursive --depth 1
git -C src/hev-socks5-tunnel submodule status
