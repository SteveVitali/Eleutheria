#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
#
# ops/gcp/backup.sh — automated backups + the restore drill for the SIG hosted
# home (P24.1 / DEPLOY.1 / GL-DEPLOY-01, ADR-075). Parameterised by
# $SIG_GCP_PROJECT. Under the ADR-075 DECISION (e2-micro compose stack) the
# backup strategy is `pg_dump` (custom format) synced to the PRIVATE GCS backup
# bucket; the Cloud SQL alternative uses managed automated backups instead.
#
#   ./backup.sh --check     # (default) plan-only: no ADC, no network, exit 0.
#   ./backup.sh --apply     # operator-gated: requires ADC; runs the real backup.
#
# The REAL LOCAL restore drill (dump the composed PG -> restore into a fresh DB
# -> assert the claim/evidence graph reproduces) runs over Docker via
# `uv run python -m ops backup-drill` and its test (tests/db/test_restore_drill.py)
# — that is the deterministic proxy for the gate-pending cloud restore.
set -euo pipefail

_here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=ops/gcp/config.sh
. "${_here}/config.sh"
# shellcheck source=ops/gcp/lib.sh
. "${_here}/lib.sh"

parse_mode "${1:-}"
require_project
require_adc

banner "backup + restore drill"

_STAMP='$(date +%Y%m%dT%H%M%SZ)'   # literal in the printed plan; expanded at apply time

# 1. DECISION path: pg_dump the compose PG on the GCE host -> GCS backup bucket.
backup_pg_dump() {
  _log "-- pg_dump backup (DECISION path) --"
  run gcloud compute ssh "${SIG_GCE_INSTANCE}" --zone "${SIG_GCP_ZONE}" \
    --project "${SIG_GCP_PROJECT}" --command \
    "docker compose -p sig exec -T db pg_dump -Fc -U sig sig > /tmp/sig-${_STAMP}.dump"
  run gcloud storage cp "/tmp/sig-${_STAMP}.dump" \
    "gs://${SIG_BUCKET_BACKUPS}/pg/sig-${_STAMP}.dump"
  # The OCFL evidence store is synced write-once alongside the SQL dump.
  run gcloud storage rsync -r "./evidence/store" \
    "gs://${SIG_BUCKET_BACKUPS}/ocfl/"
  _log "note: retention/lifecycle is a bucket rule (e.g. keep 30 daily, 12 monthly)."
}

# 2. ALTERNATIVE: Cloud SQL managed automated backups (documented, not default).
backup_cloud_sql() {
  _log "-- Cloud SQL automated backups (ALTERNATIVE, documented) --"
  _plan "gcloud sql instances patch ${SIG_SQL_INSTANCE} --backup-start-time=03:00 --enable-point-in-time-recovery"
  _log "note: managed daily backups + PITR; restore = gcloud sql backups restore."
}

# 3. The restore drill — documented here, EXECUTED for real locally over Docker.
restore_drill() {
  _log "-- restore drill (real local proxy for the cloud restore) --"
  _plan "download the latest gs://${SIG_BUCKET_BACKUPS}/pg/*.dump"
  _plan "pg_restore into a FRESH database and assert claim/evidence counts reproduce"
  _log "note: run the deterministic local drill NOW with:"
  _log "        uv run python -m ops backup-drill      (real pg_dump/restore over Docker)"
  _log "      the cloud restore (from GCS/Cloud SQL) is gate-pending on ADC (D-DEPLOY.1-1)."
}

backup_pg_dump
backup_cloud_sql
restore_drill

_log ""
if [ "${SIG_GCP_MODE}" = "check" ]; then
  _log "check OK — backup + restore-drill plan printed, no ADC used, no network. Exit 0."
else
  _log "backup complete; run the restore drill to verify."
fi
