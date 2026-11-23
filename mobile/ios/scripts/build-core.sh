#!/usr/bin/env bash
# Builds mobile/core (Kervan engine + ByeDPI + hev-socks5-tunnel) into
# mobile/ios/build/KervanCore.xcframework for iPhone and the simulator.
#
#   scripts/build-core.sh          build the xcframework
#   scripts/build-core.sh --test   also run the host C tests natively on macOS
#                                  (exercises the Darwin utun framing path)
#
# Requires macOS with Xcode command line tools and CMake >= 3.22.
# Run mobile/core/third_party/fetch.sh first.
set -euo pipefail

if [[ "$(uname -s)" != Darwin ]]; then
  echo "build-core.sh: needs macOS with Xcode (found $(uname -s))" >&2
  exit 1
fi

HERE="$(cd "$(dirname "$0")/.." && pwd)"
CORE="$HERE/../core"
OUT="$HERE/build"
MIN_IOS=17.0
LIBS=(libkervan_core.a libkv_byedpi.a libkv_hev.a libkv_lwip.a libkv_yaml.a libkv_hev_task_system.a)

if [[ "${1:-}" == --test ]]; then
  cmake -S "$CORE" -B "$OUT/host-test" -DKV_BUILD_TESTS=ON -DCMAKE_BUILD_TYPE=Debug \
    -DCMAKE_C_FLAGS="-fsanitize=address,undefined -fno-omit-frame-pointer"
  cmake --build "$OUT/host-test"
  (cd "$OUT/host-test" && ctest --output-on-failure)
fi

build_slice() { # sdk archs
  local sdk=$1 archs=$2 dir="$OUT/$1"
  cmake -S "$CORE" -B "$dir" \
    -DCMAKE_SYSTEM_NAME=iOS \
    -DCMAKE_OSX_SYSROOT="$sdk" \
    -DCMAKE_OSX_ARCHITECTURES="$archs" \
    -DCMAKE_OSX_DEPLOYMENT_TARGET=$MIN_IOS \
    -DCMAKE_BUILD_TYPE=Release \
    -DKV_BUILD_TESTS=OFF
  cmake --build "$dir" --config Release
  local inputs=()
  for l in "${LIBS[@]}"; do inputs+=("$dir/$l"); done
  libtool -static -o "$dir/libkervan.a" "${inputs[@]}"
}

build_slice iphoneos "arm64"
build_slice iphonesimulator "arm64;x86_64"

HEADERS="$OUT/headers"
rm -rf "$HEADERS" "$OUT/KervanCore.xcframework"
mkdir -p "$HEADERS"
cp "$CORE/include/kervan_engine.h" "$HERE/KervanCore/module.modulemap" "$HEADERS/"

xcodebuild -create-xcframework \
  -library "$OUT/iphoneos/libkervan.a" -headers "$HEADERS" \
  -library "$OUT/iphonesimulator/libkervan.a" -headers "$HEADERS" \
  -output "$OUT/KervanCore.xcframework"

echo "Built $OUT/KervanCore.xcframework"
