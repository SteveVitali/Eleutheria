#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
#
# The npm advisory gate driver (P34.2 deliverable 6, SIG-ENG-042) — one command
# line the PR gate (ci.yml `security` job) and `make ci-local` share verbatim.
#
#   npm_audit_gate.sh [--full] [--out DIR]
#
# Default (the per-PR gate): `npm --prefix web audit --omit=dev --json`, judged
# by npm_audit_gate.py at --level high — production deps only, the allow-list
# carries no production entries. `--full` (nightly) additionally runs the
# full-tree audit and hands the gate `--prod-audit` so every `dev-only`
# allow-list entry is cross-checked against the production tree.
#
# `npm audit` exits 1 when findings exist — the GATE judges them (blocked vs
# allowed), so the driver preserves the status and only treats rc>1 (registry
# error, malformed tree) as an audit failure. `--out` defaults to the cwd —
# docs/build/logs locally, the workspace root in CI.
set -euo pipefail

MODE="prod"
OUT="."
while [ $# -gt 0 ]; do
  case "$1" in
    --full) MODE="full"; shift ;;
    --out) OUT="$2"; shift 2 ;;
    *) echo "npm_audit_gate.sh: unknown arg $1" >&2; exit 1 ;;
  esac
done
mkdir -p "$OUT"

rc=0
npm --prefix web audit --omit=dev --json > "$OUT/npm-audit-prod.json" || rc=$?
if [ "$rc" -gt 1 ]; then echo "npm audit (prod) itself failed (rc=$rc)" >&2; exit "$rc"; fi

if [ "$MODE" = "full" ]; then
  rc=0
  npm --prefix web audit --json > "$OUT/npm-audit.json" || rc=$?
  if [ "$rc" -gt 1 ]; then echo "npm audit (full) itself failed (rc=$rc)" >&2; exit "$rc"; fi
  uv run python scripts/ci/npm_audit_gate.py \
    --audit "$OUT/npm-audit.json" --prod-audit "$OUT/npm-audit-prod.json" \
    --level high --json "$OUT/npm-audit-gate.json"
else
  uv run python scripts/ci/npm_audit_gate.py \
    --audit "$OUT/npm-audit-prod.json" --level high --json "$OUT/npm-audit-gate.json"
fi
