#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
#
# ops/gcp/ingestion-history.sh — P36.46 (K10 UX10-2): the hosted
# append-only ingestion-history backfill (the OM-20 named mutation; the
# GATE-G5 §4 list names P36.46 verbatim — expires GATE-G6; window AR-3 +
# AR-2; the D-J3-2 [B-19] = yes answer carries: scrubbed run logs publish,
# robots disregard disclosed as host + count).
#
# The leg (INSERT-only, idempotent, evidence-bound):
#   1. cloud-sql-proxy → sig-pg (127.0.0.1:${SIG_PROXY_PORT}).
#   2. `sig-ops backfill-run-reports --role sig_materialize --dry-run`
#      — the plan report over every WORM ops/runs row (linked live /
#      backfill:<basis> / unmatched:<reason> by the P31.2 matcher) plus
#      the 90 repo-pinned live-run records (link_basis=repo_record,
#      clock_basis=git_only).
#   3. the same command without --dry-run — INSERT-only report rows;
#      ON CONFLICT under the backfilled_from unique key makes every
#      re-run +0. Restore point: the appended set's digest list — the
#      reconcile read-back's link_basis counts + the backfilled_from URI
#      set the report prints.
#   4. a second --dry-run is the +0 read-back the run ledger records.
#
# Nothing runs without the AR-3 + AR-2 window: inside 03:00–06:30Z or the
# monthly batch window (day 6 00:00Z → day 13 12:00Z) exits 42 (queued).
#
# Usage:
#   ops/gcp/ingestion-history.sh [--check|--dry-run]   # plan only (default)
#   ops/gcp/ingestion-history.sh --apply               # the report backfill
#
# Environment (apply):
#   SIG_GCP_PROJECT        the GCP project (GL-GATE-04)
#   ADC                    `gcloud auth application-default login`
#   SIG_BACKFILL_DSN       the claim-spine writer DSN able to SET ROLE
#                          sig_materialize (env only — a DSN on argv or
#                          in a file leaks, HG-09)
#   SIG_BACKFILL_AUTHOR    the recorded operator authorisation for THIS leg
#   SIG_OPS_GCS_BUCKET     the restricted bucket holding ops/runs
#   SIG_PROXY_PORT         proxy port (default 5433)
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
  *) echo "ingestion-history.sh: unknown mode '${1:-}'" >&2; exit 64 ;;
esac

export SIG_GCP_MODE="$MODE"
require_project

: "${SIG_PROXY_PORT:=5433}"
: "${SIG_OPS_GCS_BUCKET:=${SIG_OPS_GCS_BUCKET:-}}"
RERUN="implement-spec spec=docs/tickets/389_P36.46__execution-keyed-ingestion-history.md live_verification=true"

_queue() {
  _log "QUEUED (exit 42): $*"
  _log "re-run: ${RERUN}"
  exit 42
}

_window() {
  [ "${MODE}" = "check" ] && return 0
  local now day hm
  now="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
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
  if [ -z "${SIG_BACKFILL_DSN:-}" ]; then
    _queue "SIG_BACKFILL_DSN is unset — the claim-spine writer DSN (env only, HG-09)."
  fi
  if [ -z "${SIG_BACKFILL_AUTHOR:-}" ]; then
    _queue "SIG_BACKFILL_AUTHOR is unset — the recorded operator authorisation."
  fi
  if [ -z "${SIG_OPS_GCS_BUCKET:-}" ]; then
    _queue "SIG_OPS_GCS_BUCKET is unset — the restricted bucket holding ops/runs."
  fi
  _log "author: ${SIG_BACKFILL_AUTHOR} (recorded); bucket: ${SIG_OPS_GCS_BUCKET}"
}

_backfill_cmd() {
  # The DSN travels by env (SIG_STAGING_DSN is the verb's documented
  # fallback) — never on argv (HG-09).
  echo "SIG_STAGING_DSN=\$SIG_BACKFILL_DSN sig-ops backfill-run-reports --role sig_materialize --gcs-bucket ${SIG_OPS_GCS_BUCKET:-<unset>} --repo-records docs/build/reports/live_runs"
}

if [ "${MODE}" = "check" ]; then
  _plan "cloud-sql-proxy ${SIG_GCP_PROJECT}:${SIG_GCP_REGION:-us-central1}:${SIG_SQL_INSTANCE:-sig-pg} --address 127.0.0.1 --port ${SIG_PROXY_PORT}  (background; stopped on exit)"
  _plan "$(_backfill_cmd) --dry-run   # the plan report (matched/unmatched/repo counts)"
  _plan "$(_backfill_cmd)             # the INSERT-only append — +0 under the backfilled_from key"
  _plan "$(_backfill_cmd) --dry-run   # the +0 read-back the run ledger records"
  _plan "restore point: the appended set's digest list — reconcile link_basis counts + the backfilled_from URI set the report prints"
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

export SIG_STAGING_DSN="${SIG_BACKFILL_DSN}"

_log "-- dry plan: sig-ops backfill-run-reports --role sig_materialize --dry-run"
run sig-ops backfill-run-reports --role sig_materialize \
  --gcs-bucket "${SIG_OPS_GCS_BUCKET}" \
  --repo-records docs/build/reports/live_runs --dry-run

_log "-- apply: sig-ops backfill-run-reports --role sig_materialize (INSERT-only, +0 on re-run)"
run sig-ops backfill-run-reports --role sig_materialize \
  --gcs-bucket "${SIG_OPS_GCS_BUCKET}" \
  --repo-records docs/build/reports/live_runs

_log "-- +0 read-back: sig-ops backfill-run-reports --role sig_materialize --dry-run"
run sig-ops backfill-run-reports --role sig_materialize \
  --gcs-bucket "${SIG_OPS_GCS_BUCKET}" \
  --repo-records docs/build/reports/live_runs --dry-run

_log "applied — record the reconcile read-back (link_basis counts) in the run ledger."
