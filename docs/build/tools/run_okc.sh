#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
#
# run_okc.sh — the first real jurisdiction, end to end (P21.4, ADR-066).
#
# Drives the WHOLE staging path for Oklahoma City as one composed system, not a
# test suite: stand the stack up, ingest, resolve, reconcile, export, build the
# static site FROM the export, and run the acceptance queries against the running
# API. P21.8 reuses this as the template for the next jurisdiction.
#
# *** NO GREEN SOURCES (ticket Notes; HG-03 skipped in P21.3). ***
# There is NO live fetch. Every connector runs in `--mode shadow` over a committed
# fixture under network isolation; the OKC slice claims are loaded by `sig-ops
# seed` (the 299-vs-190 contradiction). This still produces the entire staging path
# — that is the real deliverable — but nothing here is "live". Per-source gate state
# is recorded as HG-03-pending with the exact command to run once a source is green.
#
# Usage:
#   sh docs/build/tools/run_okc.sh            # up, run, leave the stack up
#   SIG_OKC_TEARDOWN=1 sh docs/build/tools/run_okc.sh   # ... then tear it down
#
# Staging endpoints default to local (HG-12); override via SIG_STAGING_*.

set -u

REPO_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
cd "$REPO_ROOT"
export PYTHONPATH="${PYTHONPATH:-}:$REPO_ROOT/tests"

JURISDICTION="okc"
DSN="${SIG_STAGING_DSN:-postgresql://sig:sig@127.0.0.1:5432/sig}"
API_URL="${SIG_STAGING_API_URL:-http://127.0.0.1:8000}"
export SIG_STAGING_DSN="$DSN"
export SIG_STAGING_API_URL="$API_URL"

EXPORT_DIR="$REPO_ROOT/exports/out/$JURISDICTION"
DATE="$(date +%Y-%m-%d)"
ACCEPTANCE_OUT="$REPO_ROOT/docs/build/okc/acceptance_${DATE}.json"
CONNECTOR_LOG="$REPO_ROOT/docs/build/okc/connector_runs_${DATE}.txt"
mkdir -p "$REPO_ROOT/docs/build/okc"

say() { printf '\n=== %s ===\n' "$1"; }

# --- 1. stand the stack up (+ seed the OKC slice) ----------------------------
say "1/8  sig-ops up + seed (PG spine + API; OKC slice loaded)"
uv run sig-ops up --jurisdiction "$JURISDICTION" --no-static --seed || {
  echo "sig-ops up failed — is Docker running?"; exit 1;
}

# --- 2. connector runs in SHADOW mode (no green sources; recorded) -----------
say "2/8  connector runs (--mode shadow; NOT live — HG-03 skipped)"
: > "$CONNECTOR_LOG"
run_shadow() {  # id  fixture  kind  media-type
  local src="$1" fixture="$2" kind="$3" media="$4"
  echo "--- source=$src mode=shadow sink=pg ---" >> "$CONNECTOR_LOG"
  if uv run sig-connectors run --source "$src" --mode shadow --sink pg --dsn "$DSN" \
        --fixture "$fixture" --kind "$kind" --media-type "$media" >> "$CONNECTOR_LOG" 2>&1; then
    echo "  $src: shadow run OK (recorded, not live)"
    echo "STATE: $src shadow OK" >> "$CONNECTOR_LOG"
  else
    echo "  $src: shadow run recorded a blocker (HG-03-pending) — see $CONNECTOR_LOG"
    echo "STATE: $src HG-03-pending — flip green then re-run with --mode live" >> "$CONNECTOR_LOG"
  fi
}
run_shadow "eff_atlas_of_surveillance" \
  "$REPO_ROOT/tests/connectors/fixtures/atlas/adoption_feed.csv" "bulk_csv" "text/csv"
run_shadow "osm_overpass" \
  "$REPO_ROOT/tests/connectors/fixtures/osm/overpass_snapshot.json" "overpass" "application/json"

# --- 3. entity resolution match (P19.5) --------------------------------------
say "3/8  sig-resolution match --jurisdiction okc"
uv run sig-resolution match --dsn "$DSN" --jurisdiction "$JURISDICTION" || \
  echo "  (resolution match: no candidates or nothing to match — recorded)"

# --- 4. reconcile resolve (contradictions visible) ---------------------------
say "4/8  reconcile resolve --jurisdiction okc (299-vs-190 stays visible)"
uv run python -m reconcile resolve --dsn "$DSN" --jurisdiction "$JURISDICTION" || \
  echo "  (reconcile resolve returned non-zero — recorded)"

# --- 5. annotation rebuild (P21.2 shrunk → compute-on-read) ------------------
say "5/8  sig-db annotations rebuild — SKIPPED (P21.2 shrunk to compute-on-read)"
echo "  Annotations are computed on read (ADR-059, A5/HG-14); no rebuild step exists."

# --- 6. build the jurisdiction export (ODbL + CC-BY compartments + dossiers) -
say "6/8  sig-exports build --jurisdiction okc"
rm -rf "$EXPORT_DIR"
uv run sig-exports build --jurisdiction "$JURISDICTION" --out "$EXPORT_DIR" || {
  echo "sig-exports build failed"; exit 1;
}

# --- 7. build the static site FROM the export (SIG_DATA_SOURCE=export) --------
say "7/8  web build from the export (SIG_DATA_SOURCE=export)"
if command -v npm >/dev/null 2>&1 && [ -d "$REPO_ROOT/web/node_modules" ]; then
  SIG_DATA_SOURCE=export SIG_EXPORT_DIR="$EXPORT_DIR" \
    npm --prefix "$REPO_ROOT/web" run build || { echo "web build (export) failed"; exit 1; }
  echo "  policy.publication runs over the export at build; officer-naming gate applied (§0.7)."
else
  echo "  (npm/web/node_modules unavailable; web build skipped — run \`npm --prefix web ci\`)"
fi

# --- 8. acceptance: J-1 + Q-1..Q-13 against the running API -------------------
say "8/8  acceptance queries against SIG_STAGING_API_URL"
uv run python -m acceptance.live_api --api-url "$API_URL" --out "$ACCEPTANCE_OUT" || \
  echo "  (a fixture-subset query failed — see $ACCEPTANCE_OUT)"

say "status"
uv run sig-ops status || true
echo
echo "acceptance report:  $ACCEPTANCE_OUT"
echo "export dir:         $EXPORT_DIR"
echo "connector runs:     $CONNECTOR_LOG"

if [ "${SIG_OKC_TEARDOWN:-0}" = "1" ]; then
  say "teardown (SIG_OKC_TEARDOWN=1)"
  uv run sig-ops down || true
else
  echo
  echo "The stack is still UP. Tear it down with: uv run sig-ops down"
fi
