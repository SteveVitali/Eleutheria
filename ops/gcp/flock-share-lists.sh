#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
#
# ops/gcp/flock-share-lists.sh — P36.75 (R11-ACQ-30): the hosted append-only
# `configured_access` claim write (the OM-20 named mutation; the GATE-G5 §4
# list names P36.75 verbatim — expires GATE-G6; window AR-3 + AR-2).
#
# The leg:
#   1. cloud-sql-proxy → sig-pg (127.0.0.1:${SIG_PROXY_PORT}).
#   2. `sig-connectors flock-share-lists --snapshot <mirror.json>
#      [--portal-extraction <page.json> ...] --dsn-env SIG_SHARE_WRITE_DSN`
#      — dry-run: the plan report (units, bindable, pending, set digest).
#   3. the same command with `--apply` — INSERT-only claims via PgClaimSink,
#      bound to the stored captures the inputs re-derive byte-for-byte;
#      restore point = the written claim set's digest list in the report.
#   4. a +0 re-run of the dry plan is the read-back the ledger records.
#
# Nothing runs without the AR-3 + AR-2 window: inside 03:00–06:30Z or the
# monthly batch window (day 6 00:00Z → day 13 12:00Z) exits 42 (queued).
#
# Usage:
#   ops/gcp/flock-share-lists.sh [--check|--dry-run]   # plan only (default)
#   ops/gcp/flock-share-lists.sh --apply               # the claim write
#
# Environment (apply):
#   SIG_GCP_PROJECT        the GCP project (GL-GATE-04)
#   ADC                    `gcloud auth application-default login`
#   SIG_SHARE_WRITE_DSN    the claim-spine writer DSN (env only — a DSN on
#                          argv or in a file leaks)
#   SIG_SHARE_LISTS_AUTHOR the recorded operator authorisation for THIS leg
#   SIG_PROXY_PORT         proxy port (default 5433)
#   SIG_SHARE_SNAPSHOT     staged mirror snapshot path (required)
#   SIG_SHARE_EXTRACTIONS  space-separated sig.flock-portal-page/1 paths (optional)
#   cloud-sql-proxy        on PATH
#
# Exit codes: 0 ok · 2 usage/gate input absent · 3 unarmed · 42 queued.

set -euo pipefail

_here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=config.sh
. "${_here}/config.sh"
# shellcheck source=lib.sh
. "${_here}/lib.sh"

MODE="check"
case "${1:-}" in
  --apply) MODE="apply" ;;
  --check|--dry-run|"") MODE="check" ;;
  -h|--help) sed -n '/^# Usage:/,/^set -euo pipefail/p' "$0" | sed 's/^# \{0,1\}//; /^set -euo/d'; exit 0 ;;
  *) echo "flock-share-lists.sh: unknown mode '${1:-}'" >&2; exit 64 ;;
esac

export SIG_GCP_MODE="$MODE"
require_project

: "${SIG_PROXY_PORT:=5433}"
RERUN="implement-spec spec=docs/tickets/385_P36.75__flock-share-lists-configured-access.md live_verification=true"

_queue() {
  _log "QUEUED (exit 42): $*"
  _log "re-run: ${RERUN}"
  exit 42
}

_window() {
  [ "${MODE}" = "check" ] && return 0
  local now day
  now="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  local hm
  hm="$(date -u +%H:%M)"
  if [ "${hm}" \> "03:00" ] && [ "${hm}" \< "06:30" ]; then
    _queue "${now} is inside 03:00–06:30Z — never mutate then (AR-3 + AR-2)."
  fi
  day="$(date -u +%-d)"
  if [ "${day}" -ge 6 ] && [ "${day}" -le 13 ]; then
    _queue "${now} is inside the monthly batch window (day 6 00:00Z → day 13 12:00Z)."
  fi
  _log "window OK: ${now} (outside 03:00–06:30Z, outside the batch window)"
}

_env() {
  [ "${MODE}" = "check" ] && return 0
  require_adc
  if [ -z "${SIG_SHARE_WRITE_DSN:-}" ]; then
    _queue "SIG_SHARE_WRITE_DSN is unset — the claim-spine writer DSN (env only, HG-09)."
  fi
  if [ -z "${SIG_SHARE_LISTS_AUTHOR:-}" ]; then
    _queue "SIG_SHARE_LISTS_AUTHOR is unset — the recorded operator authorisation."
  fi
  if [ -z "${SIG_SHARE_SNAPSHOT:-}" ]; then
    _queue "SIG_SHARE_SNAPSHOT is unset — the staged mirror snapshot path."
  fi
  if [ ! -f "${SIG_SHARE_SNAPSHOT}" ]; then
    _queue "SIG_SHARE_SNAPSHOT=${SIG_SHARE_SNAPSHOT} is not a readable file."
  fi
  _log "author: ${SIG_SHARE_LISTS_AUTHOR} (recorded); snapshot: ${SIG_SHARE_SNAPSHOT}"
}

_plan_cmd() {
  local args=(flock-share-lists --snapshot "${SIG_SHARE_SNAPSHOT:-<unset>}")
  local x
  for x in ${SIG_SHARE_EXTRACTIONS:-}; do
    args+=(--portal-extraction "$x")
  done
  args+=(--dsn-env SIG_SHARE_WRITE_DSN --code-commit "$(git rev-parse --short HEAD 2>/dev/null || echo unknown)")
  echo "sig-connectors ${args[*]}"
}

if [ "${MODE}" = "check" ]; then
  _plan "cloud-sql-proxy ${SIG_GCP_PROJECT}:${SIG_GCP_REGION:-us-central1}:${SIG_SQL_INSTANCE:-sig-pg} --address 127.0.0.1 --port ${SIG_PROXY_PORT}  (background; stopped on exit)"
  _plan "$(_plan_cmd)          # dry-run plan report"
  _plan "$(_plan_cmd) --apply  # the INSERT-only write (bound to stored captures)"
  _plan "re-run the dry plan — the +0 read-back the ledger records"
  _log "prepared_not_executed — OM-19 queue; re-run: ${RERUN}"
  exit 0
fi

_window
_env
if ! command -v cloud-sql-proxy >/dev/null 2>&1; then
  _queue "cloud-sql-proxy not on PATH — the leg connects through 127.0.0.1:${SIG_PROXY_PORT}."
fi

_proxy_pid=""
trap 'if [ -n "${_proxy_pid}" ]; then kill "${_proxy_pid}" 2>/dev/null || true; fi' EXIT
cloud-sql-proxy "${SIG_GCP_PROJECT}:${SIG_GCP_REGION:-us-central1}:${SIG_SQL_INSTANCE:-sig-pg}" \
  --address 127.0.0.1 --port "${SIG_PROXY_PORT}" --quiet &
_proxy_pid=$!
sleep 3

_args=(flock-share-lists --snapshot "${SIG_SHARE_SNAPSHOT}")
for x in ${SIG_SHARE_EXTRACTIONS:-}; do
  _args+=(--portal-extraction "$x")
done
_args+=(--dsn-env SIG_SHARE_WRITE_DSN --code-commit "$(git rev-parse --short HEAD 2>/dev/null || echo unknown)")

_log "-- dry plan: sig-connectors ${_args[*]}"
uv run python -m connectors "${_args[@]}"
_log "-- apply:   sig-connectors ${_args[*]} --apply"
uv run python -m connectors "${_args[@]}" --apply
_log "-- read-back (+0):"
uv run python -m connectors "${_args[@]}"
