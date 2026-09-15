#!/bin/sh
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
#
# retro_cli_matrix.sh — the retroactive implement-spec 5.3 CLI matrix (P19.3).
#
# LD-V02 evidence: several tickets (P00.2/P00.4/P01.1/P07.1 and the fixture-only
# stages) shipped plain CLIs (SIG-ENG-013) that no ledger recorded ever being
# driven. This script drives each one once, with a real argument, and records its
# exit code + first line of output — deterministic and Docker-free. It is the
# committed evidence that every stage CLI is invocable. (P19.5 correlates the
# `inference` row to its own work.)
#
# The script itself always exits 0; each command's own exit code is recorded in
# its row (a non-zero row is honest evidence, never hidden).

set -u

REPO_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/../../.." && pwd)
cd "$REPO_ROOT" || exit 1

# Deterministic scratch for the two commands that need a real file argument.
WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT
printf 'The Oklahoma City Police Department operates 90 ALPR cameras.\n' > "$WORK/doc.txt"
# A non-existent queue path -> the review CLI loads an empty queue (rc 0).
QUEUE="$WORK/review_queue.json"

ROWS=0

run_row() {
  # $1 = human label (the command as documented); $2.. = argv to `uv run`
  label=$1
  shift
  # PYTHONHASHSEED=0 so the ontology --check comparison is canonical (LD-X07).
  out=$(PYTHONHASHSEED=0 uv run "$@" 2>&1)
  rc=$?
  first=$(printf '%s\n' "$out" | head -n 1)
  ROWS=$((ROWS + 1))
  printf 'rc=%-3s | %-45s | %s\n' "$rc" "$label" "$first"
}

echo "# retro CLI matrix (P19.3, LD-V02) — one drive per stage CLI"
echo "# repo: $REPO_ROOT"
echo "# format: rc=<exit code> | <command> | <first line of output>"
echo "#--------------------------------------------------------------"

run_row "python -m policy validate"                 python -m policy validate
run_row "python -m policy jurisdiction"             python -m policy jurisdiction
run_row "sig-connectors validate"                   sig-connectors validate
run_row "sig-connectors stages"                     sig-connectors stages
run_row "sig-connectors list-connectors"            sig-connectors list-connectors
run_row "sig-connectors gate --source osm_overpass" sig-connectors gate --source osm_overpass
run_row "sig-connectors export-check"               sig-connectors export-check
run_row "sig-ontology generate --check"             sig-ontology generate --check
run_row "sig-parsing classify <fixture>"            sig-parsing classify "$WORK/doc.txt"
run_row "sig-resolution normalize LAPD"             sig-resolution normalize LAPD
run_row "sig-resolution review list <queue>"        sig-resolution review list "$QUEUE"
run_row "python -m reconcile --help"                python -m reconcile --help
run_row "python -m inference --help"                python -m inference --help
run_row "python -m tasks --help"                    python -m tasks --help
run_row "sig-db analytics assert-schema"            sig-db analytics assert-schema
run_row "sig-exports --help"                        sig-exports --help
run_row "sig-ops --help"                            sig-ops --help

echo "#--------------------------------------------------------------"
echo "rows: $ROWS"
if [ "$ROWS" -lt 14 ]; then
  echo "ERROR: fewer than 14 rows" >&2
  exit 1
fi
echo "retro_cli_matrix OK"
exit 0
