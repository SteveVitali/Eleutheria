#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
#
# P34.34b (ACT-16b, C4 NEW-26, DR-C4-13; SIG-FIND-005/041): the CI `web` job's
# export-mode leg, one subcommand per CI step so each step's failure is
# localised in the log. `make check-export-mode` (reachable from
# `make ci-local`) runs the same subcommands.
#
#   produce          from-spine fixture export + immutable release:
#                    PG18+PostGIS container → real db/sqitch.plan → the
#                    licence-safe tests/db seed → run_spine_export → write_to
#                    → build_release + validate_release (its same-origin link
#                    crawl included). NEVER the web-fixture serializer: the
#                    committed-fixture overlay path has no place in this leg
#                    (C4 NEW-26).
#   verify-fail-loud the negative half: an empty export dir MUST fail the
#                    build; success here is the regression. Runs BEFORE the
#                    real build — a build that dies mid-generation can leave
#                    web/dist half-written, and budgets/Lighthouse must
#                    measure exactly the real build's output.
#   build            `SIG_DATA_SOURCE=export SIG_EXPORT_DIR=<export> npm run
#                    build` over the produced export — fails loud on any
#                    missing artifact (SIG-UI-036: never a fixture fall-back).
#   mount-record     copy one real record page out of the release tree to the
#                    stable collect URL `dist/r/_fixture-record/index.html`
#                    (publication/entity ids are content-derived and differ
#                    every run; the bytes are the release-builder's own).
#   budgets          per-island script/total ceilings over the export dist
#                    (web/tests/e2e/island-budgets.json, ADR-134).
#   lighthouse       `lhci autorun --config=lighthouserc.export.json` — the
#                    export-mode budget matrix incl. /releases/,
#                    /research-dossier/ and the archive record.
#   all              every subcommand in CI order.
#
# Working dirs: $RUNNER_TEMP in CI, docs/build/logs/p34-34b/ locally (the one
# gitignored subtree). Subcommands are stateless apart from those dirs.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
WORK="${RUNNER_TEMP:-$ROOT/docs/build/logs/p34-34b}"
EXPORT_DIR="$WORK/sig-export"
RELEASE_DIR="$WORK/sig-release"
EMPTY_DIR="$WORK/sig-export-empty"
DIST="$ROOT/web/dist"
mkdir -p "$WORK"

sub="${1:-all}"

produce() {
    cd "$ROOT"
    uv run python scripts/ci/build_from_spine_fixture_export.py \
        --out "$EXPORT_DIR" \
        --release "$RELEASE_DIR" \
        --json-summary "$WORK/export-fixture-summary.json" \
        | tee "$WORK/export-fixture-summary.log"
}

build() {
    cd "$ROOT/web"
    SIG_DATA_SOURCE=export \
    SIG_EXPORT_DIR="$EXPORT_DIR" \
    SIG_BUILD_INTERNAL=1 \
        npm run build
}

verify_fail_loud() {
    cd "$ROOT/web"
    rm -rf "$EMPTY_DIR"
    mkdir -p "$EMPTY_DIR"
    if SIG_DATA_SOURCE=export SIG_EXPORT_DIR="$EMPTY_DIR" \
        npm run build > "$WORK/empty-export-build.log" 2>&1; then
        echo "::error::export-mode build SUCCEEDED on a missing export — " \
            "the silent fixture fall-back regressed (C4 NEW-26)" >&2
        exit 1
    fi
    if ! grep -q "SIG_DATA_SOURCE=export but" "$WORK/empty-export-build.log"; then
        echo "::error::the export-mode failure did not carry the data.ts " \
            "fail-loud marker — the loud-failure contract changed" >&2
        cat "$WORK/empty-export-build.log" >&2
        exit 1
    fi
    echo "export-mode build fails loud on a missing export, as required:"
    tail -5 "$WORK/empty-export-build.log"
}

mount_record() {
    local record
    # (|| true — a missing release tree must reach the named error below,
    #  not set -e on the find itself)
    record="$(find "$RELEASE_DIR/r" -path '*/entity/*/*/index.html' 2>/dev/null | sort | head -1 || true)"
    if [ -z "$record" ]; then
        echo "::error::the release build emitted no record page — nothing to measure" >&2
        exit 1
    fi
    echo "archive record (the release-builder's own bytes): $record"
    mkdir -p "$DIST/r/_fixture-record"
    cp "$record" "$DIST/r/_fixture-record/index.html"
}

budgets() {
    cd "$ROOT/web"
    node scripts/measure-island-budgets.mjs --out "$WORK/island-budgets-export.md"
    cat "$WORK/island-budgets-export.md"
}

lighthouse() {
    cd "$ROOT/web"
    npx --no-install lhci autorun --config=./lighthouserc.export.json
}

case "$sub" in
    produce) produce ;;
    build) build ;;
    verify-fail-loud) verify_fail_loud ;;
    mount-record) mount_record ;;
    budgets) budgets ;;
    lighthouse) lighthouse ;;
    all)
        produce
        verify_fail_loud
        build
        mount_record
        budgets
        lighthouse
        ;;
    *)
        echo "usage: $0 {produce|build|verify-fail-loud|mount-record|budgets|lighthouse|all}" >&2
        exit 2
        ;;
esac
