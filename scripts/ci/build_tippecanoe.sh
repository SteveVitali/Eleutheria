#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
#
# P35.52 (sig.map-tiles/2, ADR-156): build the PINNED tippecanoe once so the CI
# verifier leg and the nightly real-sized leg can run `sig-exports tiles
# verify` against the production renderer — never the mocked argv test and
# never an unpinned binary. The version + tarball sha256 are READ FROM
# ops/Dockerfile (the one pin source — bump it there and every consumer moves).
#
# Usage: build_tippecanoe.sh <prefix-dir>
#   Builds <prefix-dir>/tippecanoe. When a binary at that path already reports
#   the pinned version (the actions/cache hit) the script is a no-op — the
#   "build once, cache" contract.
set -euo pipefail

PREFIX="${1:?usage: build_tippecanoe.sh <prefix-dir>}"
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
DOCKERFILE="$REPO/ops/Dockerfile"

VERSION="$(sed -n 's/^ARG TIPPECANOE_VERSION=//p' "$DOCKERFILE" | head -1)"
SHA256="$(sed -n 's/^ARG TIPPECANOE_SHA256=//p' "$DOCKERFILE" | head -1)"
if [ -z "$VERSION" ] || [ -z "$SHA256" ]; then
  echo "build_tippecanoe: TIPPECANOE_VERSION/SHA256 pin not found in ops/Dockerfile" >&2
  exit 2
fi

if [ -x "$PREFIX/tippecanoe" ]; then
  # `--version` can exit non-zero on some builds; never let that force a
  # rebuild (pipefail would read the pipeline's failure as a cache miss).
  installed_ver="$("$PREFIX/tippecanoe" --version 2>&1 || true)"
  if printf '%s\n' "$installed_ver" | grep -q "$VERSION"; then
    echo "build_tippecanoe: tippecanoe $VERSION already present at $PREFIX/tippecanoe (cache hit)"
    exit 0
  fi
fi

# Portable checksum/parallel/install shims — macOS (the local `make
# check-tile-verify` path) lacks sha256sum/nproc/install -D.
if command -v sha256sum >/dev/null 2>&1; then
  sha256_check() { echo "${SHA256}  $1" | sha256sum -c -; }
else
  sha256_check() { echo "${SHA256}  $1" | shasum -a 256 -c -; }
fi
if command -v nproc >/dev/null 2>&1; then
  JOBS="$(nproc)"
else
  JOBS="$(getconf _NPROCESSORS_ONLN 2>/dev/null || echo 2)"
fi

for tool in curl tar make; do
  command -v "$tool" >/dev/null 2>&1 || {
    echo "build_tippecanoe: required tool '$tool' not on PATH" >&2
    exit 2
  }
done
if ! command -v cc >/dev/null 2>&1 && ! command -v c++ >/dev/null 2>&1; then
  echo "build_tippecanoe: no C toolchain on PATH (CI installs build-essential;" >&2
  echo "  locally the Xcode CLT / build tools supply it)" >&2
  exit 2
fi

echo "build_tippecanoe: building tippecanoe $VERSION → $PREFIX/tippecanoe"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
curl -fsSL \
  "https://github.com/felt/tippecanoe/archive/refs/tags/${VERSION}.tar.gz" \
  -o "$WORK/tippecanoe.tar.gz"
sha256_check "$WORK/tippecanoe.tar.gz"
tar -xzf "$WORK/tippecanoe.tar.gz" -C "$WORK"
make -C "$WORK/tippecanoe-${VERSION}" -j"$JOBS" tippecanoe
mkdir -p "$PREFIX"
install -m0755 "$WORK/tippecanoe-${VERSION}/tippecanoe" "$PREFIX/tippecanoe"
"$PREFIX/tippecanoe" --version
