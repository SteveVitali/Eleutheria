#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
#
# run_france.sh — the SECOND jurisdiction, end to end (P24.6, JURIS.2 / GL-JURIS-01).
#
# Templated from run_okc.sh — but the second jurisdiction is the design's proof,
# not a copy (D7): France — commune de Gex, département de l'Ain, vidéoprotection —
# exercises the P18.1 adapter framework with shapes OKC does not have:
# authorization by published arrêté préfectoral (not a contract), procurement by
# DECP national open data (not municipal portals), records regime fr.cada (never
# us.foia), and the FR-GDPR publication gate (the officer name is withheld where
# the US dossier publishes it).
#
# *** NO GREEN SOURCES FOR THE NEW JURISDICTION (HG-03/HG-04 are operator gates). ***
# There is NO live fetch. Every connector runs in `--mode shadow` over a committed
# fixture under network isolation; the France slice claims are loaded by
# `sig-ops seed --jurisdiction france`. `madada` is recorded REFUSED at the loader
# gate (compact_status=not_contacted) — that is the gate working, honestly
# recorded, not a failure. Per-source gate state is HG-03-pending with the exact
# command to run once a source is green (docs/tickets/DEFERRALS.md D-JURIS.2-*).
#
# Usage:
#   sh docs/build/tools/run_france.sh            # up, run, leave the stack up
#   SIG_FRANCE_TEARDOWN=1 sh docs/build/tools/run_france.sh   # ... then tear it down
#
# Staging endpoints default to local (HG-12); override via SIG_STAGING_*.

set -u

REPO_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
cd "$REPO_ROOT"
export PYTHONPATH="${PYTHONPATH:-}:$REPO_ROOT/tests"

JURISDICTION="france"
DSN="${SIG_STAGING_DSN:-postgresql://sig:sig@127.0.0.1:5432/sig}"
API_URL="${SIG_STAGING_API_URL:-http://127.0.0.1:8000}"
export SIG_STAGING_DSN="$DSN"
export SIG_STAGING_API_URL="$API_URL"

EXPORT_DIR="$REPO_ROOT/exports/out/$JURISDICTION"
DATE="$(date +%Y-%m-%d)"
ACCEPTANCE_OUT="$REPO_ROOT/docs/build/reports/france/acceptance_${DATE}.json"
CONNECTOR_LOG="$REPO_ROOT/docs/build/reports/france/connector_runs_${DATE}.txt"
mkdir -p "$REPO_ROOT/docs/build/reports/france"

say() { printf '\n=== %s ===\n' "$1"; }

# --- 1. stand the stack up (+ seed the France slice) --------------------------
say "1/8  sig-ops up + seed (PG spine + API; France slice loaded)"
uv run sig-ops up --jurisdiction "$JURISDICTION" --no-static --seed || {
  echo "sig-ops up failed — is Docker running?"; exit 1;
}

# --- 2. connector runs in SHADOW mode (no green sources; recorded) ------------
say "2/8  connector runs (--mode shadow; NOT live — HG-03 pending)"
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
# The arrêté corpus (prefectoral_orders → LegalInstrument, ODbL compartment).
run_shadow "raa_prefectures" \
  "$REPO_ROOT/tests/connectors/fixtures/france/raa_prefectures.json" \
  "records" "application/json"
# The DECP national open-data marchés (→ Contract; accord-cadre → piggyback).
run_shadow "decp_fr" \
  "$REPO_ROOT/tests/connectors/fixtures/france/decp_marches.json" \
  "bulk_csv" "application/json"
# The CADA records register — REFUSED at the loader gate (compact_status=
# not_contacted): recorded as honest gate evidence, not a failure.
run_shadow "madada" \
  "$REPO_ROOT/tests/connectors/fixtures/france/madada_records.json" \
  "records" "application/json"

# --- 3. entity resolution match ----------------------------------------------
say "3/8  sig-resolution match --jurisdiction france"
uv run sig-resolution match --dsn "$DSN" --jurisdiction "$JURISDICTION" || \
  echo "  (resolution match: no candidates or nothing to match — recorded)"

# --- 4. reconcile resolve (the arrêté surface + registered predicates) --------
say "4/8  reconcile resolve --jurisdiction france"
uv run python -m reconcile resolve --dsn "$DSN" --jurisdiction "$JURISDICTION" || \
  echo "  (reconcile resolve returned non-zero — recorded)"
echo "  note: the §11.14 legal-instrument predicates are out of the resolver"
echo "        ruleset — 'predicate not in resolver ruleset — skipped' is the"
echo "        honest recorded behaviour, not a failure (ADR-079)."

# --- 5. annotation rebuild (P21.2 shrunk → compute-on-read) -------------------
say "5/8  sig-db annotations rebuild — SKIPPED (P21.2 shrunk to compute-on-read)"
echo "  Annotations are computed on read (ADR-059, A5/HG-14); no rebuild step exists."

# --- 6. build the jurisdiction export (ODbL compartment + CC-BY + dossier) ----
say "6/8  sig-exports build --jurisdiction france"
rm -rf "$EXPORT_DIR"
uv run sig-exports build --jurisdiction "$JURISDICTION" --out "$EXPORT_DIR" || {
  echo "sig-exports build failed"; exit 1;
}
echo "  DECP content is ABSENT from the export: rights UNDETERMINED → the gate"
echo "  fails closed (recorded as a dossier gap). ODbL compartment stays separate."

# --- 6b. the commune's OSM device layer is NOT imported — render the honest ---
#         EMPTY tile set so /map shows zero devices (never a fabricated layer,
#         never a missing artifact). OKC's export carries a real devices
#         GeoJSON from its OSM slice; France's posture is 'not yet imported'
#         (FR-10 records the OSM carrier blocked on HG-03).
if [ ! -f "$EXPORT_DIR/web/tiles/sig-infrastructure.pmtiles" ]; then
  EMPTY_GEOJSON="$REPO_ROOT/docs/build/reports/france/devices_empty.geojson"
  mkdir -p "$EXPORT_DIR/web/tiles"
  printf '%s\n' '{"type":"FeatureCollection","features":[]}' > "$EMPTY_GEOJSON"
  uv run sig-exports tiles \
    --in "$EMPTY_GEOJSON" \
    --out "$EXPORT_DIR/web/tiles/sig-infrastructure.pmtiles" \
    --license ODbL-1.0 || { echo "empty tile render failed"; exit 1; }
  echo "  no OSM device layer imported for the commune — empty tile set rendered"
  echo "  (the map honestly shows zero devices; FR-10 records the carrier blocked)"
fi

# --- 7. build the static site FROM the export (SIG_DATA_SOURCE=export) --------
say "7/8  web build from the export (SIG_DATA_SOURCE=export)"
if command -v npm >/dev/null 2>&1 && [ -d "$REPO_ROOT/web/node_modules" ]; then
  SIG_DATA_SOURCE=export SIG_EXPORT_DIR="$EXPORT_DIR" \
    npm --prefix "$REPO_ROOT/web" run build || { echo "web build (export) failed"; exit 1; }
  echo "  policy.publication runs over the export at build; the FR-GDPR gate"
  echo "  WITHHOLDS the signing-officer name where the US dossier publishes it."
else
  echo "  (npm/web/node_modules unavailable; web build skipped — run \`npm --prefix web ci\`)"
fi

# --- 8. acceptance: France's own queries FR-1..FR-10 against the running API ---
say "8/8  acceptance queries (france) against SIG_STAGING_API_URL"
uv run python -m acceptance.live_api_france \
  --api-url "$API_URL" --export-dir "$EXPORT_DIR" --out "$ACCEPTANCE_OUT" || \
  echo "  (a fixture-subset query failed — see $ACCEPTANCE_OUT)"

say "status"
uv run sig-ops status || true
echo
echo "acceptance report:  $ACCEPTANCE_OUT"
echo "export dir:         $EXPORT_DIR"
echo "connector runs:     $CONNECTOR_LOG"

if [ "${SIG_FRANCE_TEARDOWN:-0}" = "1" ]; then
  say "teardown (SIG_FRANCE_TEARDOWN=1)"
  uv run sig-ops down || true
else
  echo
  echo "The stack is still UP. Tear it down with: uv run sig-ops down"
fi
