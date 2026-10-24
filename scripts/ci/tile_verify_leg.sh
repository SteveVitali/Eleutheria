#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
#
# P35.52 (sig.map-tiles/2, ADR-156, F-104/F-414; K1-map §15 NEW-5): the tile
# verifier leg — ONE source of the commands the CI web job and the nightly
# real-sized leg share (SIG-ENG-046: same commands locally and in CI).
#
#   tile_verify_leg.sh fixture   build the deterministic 50k synthetic fixture
#   tile_verify_leg.sh national  build the national-sized bundle (nightly)
#   tile_verify_leg.sh verify    run `sig-exports tiles verify` over the fixture
#
# With the pinned tippecanoe on PATH the fixture archives are rendered BY
# tippecanoe, so the verify leg exercises the real renderer and its parity
# check against the pure-Python replay is non-vacuous (the check records
# `vacuous` honestly when the shipped archive was itself pure-Python).
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
OUT="${SIG_TILE_FIXTURE_OUT:-$REPO/.cache/tile-fixture}"

case "${1:?usage: tile_verify_leg.sh fixture|national|verify}" in
  fixture)
    # tippecanoe opens many temp files at scale — the ops image raises the fd
    # ceiling; do the same so the leg matches the production invocation.
    ulimit -n 16384 2>/dev/null || true
    uv run python "$REPO/scripts/ci/build_tile_fixture.py" --out "$OUT"
    ;;
  national)
    ulimit -n 16384 2>/dev/null || true
    uv run python "$REPO/scripts/ci/build_national_fixture.py" --out "$OUT"
    ;;
  verify)
    uv run sig-exports tiles verify --in "$OUT"
    ;;
esac
