#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
#
# P35.51 (SIG-UI-041, SIG-FIND-005, K0 §4.12.6, ADR-155): the national-fixture
# budget leg — the state every page-type budget row is measured under at real
# scale. CI runs the subcommands as separate steps in the perf job (inside the
# P35.41a reuse gate, so a records-only push never pays for it);
# `npm run check:perf:national` runs the same leg locally (`all`);
# `make ci-local` runs the same path. One subcommand per
# leg so each failure is localised in the log:
#
#   fixture    the deterministic synthetic national fixture — ≥ 232k sites /
#              ≥ 5k agencies / ≥ 400k sharing edges, invented names only
#              (F-173) — into the gitignored web/national/ overlay
#              (scripts/ci/build_national_fixture.py; tests prove the same
#              seed reproduces byte-identical trees).
#   build      `SIG_DATA_SOURCE=national SIG_BUILD_INTERNAL=1 npm run build`
#              — the site over the overlay; a missing or malformed artifact
#              fails LOUD (SIG-UI-036, never a silent fixtures fall-back).
#   budgets    the generalised budget.spec.ts wire measurement over the
#              national build: every discovered route, gzip + brotli, before
#              and after one scripted interaction per surface. The national-
#              scoped measured_gaps bind here (the real-scale document/total
#              and latency overages, recorded and bounded — D-P35.51-3).
#   lighthouse `lhci autorun --config=./lighthouserc.national.json` — the
#              generated national twin's assertMatrix (ratified ceilings warn,
#              recorded regression bounds error).
#   all        every subcommand in CI order.
#
# Working dir for the fixture is the repo's web/national/ (gitignored); the
# leg mutates nothing else and touches no production path.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
NATIONAL_DIR="${SIG_NATIONAL_DIR:-$ROOT/web/national}"

sub="${1:-all}"

fixture() {
    cd "$ROOT"
    uv run python scripts/ci/build_national_fixture.py --out "$NATIONAL_DIR"
}

build() {
    cd "$ROOT/web"
    SIG_DATA_SOURCE=national \
    SIG_NATIONAL_DIR="$NATIONAL_DIR" \
    SIG_BUILD_INTERNAL=1 \
        npm run build
}

budgets() {
    cd "$ROOT/web"
    SIG_DATA_SOURCE=national \
    SIG_NATIONAL_DIR="$NATIONAL_DIR" \
        npx playwright test tests/e2e/budget.spec.ts --project=chromium
}

lighthouse() {
    cd "$ROOT/web"
    npx --no-install lhci autorun --config=./lighthouserc.national.json
}

case "$sub" in
    fixture) fixture ;;
    build) build ;;
    budgets) budgets ;;
    lighthouse) lighthouse ;;
    all)
        fixture
        build
        budgets
        lighthouse
        ;;
    *)
        echo "usage: $0 {fixture|build|budgets|lighthouse|all}" >&2
        exit 2
        ;;
esac
