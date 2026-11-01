#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
#
# ops/gcp/status-publish.sh — P36.43 (TX-07): the 6-hourly `sig-status-publish`
# Cloud Run job + its Cloud Scheduler trigger (the OM-20 named mutation; the
# GATE-G5 §4 list names P36.43 verbatim — expires GATE-G6; window AR-3 + AR-2).
#
# The leg (J3 §7.1):
#   1. `gcloud run jobs deploy sig-status-publish` — the pinned-digest image
#      (P31.4/ADR-111: never :latest), least-privilege identity (ACT-13:
#      read-only on the v_transparency_* views + the scheduler list; no
#      spine write, no release tree).
#   2. `gcloud scheduler jobs create http sig-sched-status-publish`
#      `--schedule '12 */6 * * *'` (every 6 h — D-J3-11) invoking the job.
#   3. IAM invoker binding for the scheduler SA on the job.
#   4. cadence.toml gains the status row IN THE SAME RE-RUN COMMIT so
#      live-diff's undeclared-trigger report stays clean.
#   Restore point: delete the trigger, then the job (definition removal).
#
# Nothing runs without the AR-3 + AR-2 window: inside 03:00–06:30Z or the
# monthly batch window (day 6 00:00Z → day 13 12:00Z) exits 42 (queued).
#
# Usage:
#   ops/gcp/status-publish.sh [--check|--dry-run]   # plan only (default)
#   ops/gcp/status-publish.sh --apply               # the job + trigger create
#
# Environment (apply):
#   SIG_GCP_PROJECT        the GCP project (GL-GATE-04)
#   ADC                    `gcloud auth application-default login`
#   SIG_JOB_IMAGE          the pinned image ref (a sha tag or @sha256: digest —
#                          `:latest`/untagged refused)
#   SIG_STATUS_AUTHOR      the recorded operator authorisation for THIS leg
#   SIG_RUN_REGION         the Cloud Run region (default us-central1)
#   SIG_STATUS_SA_EMAIL    the job's least-privilege identity
#   SIG_SCHEDULER_SA_EMAIL the scheduler invoker identity
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
  *) echo "status-publish.sh: unknown mode '${1:-}'" >&2; exit 64 ;;
esac

export SIG_GCP_MODE="$MODE"
require_project

: "${SIG_RUN_REGION:=us-central1}"
: "${SIG_STATUS_JOB:=sig-status-publish}"
: "${SIG_STATUS_SCHED:=sig-sched-status-publish}"
RERUN="implement-spec spec=docs/tickets/386_P36.43__status-lane.md live_verification=true"

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
  if [ -z "${SIG_JOB_IMAGE:-}" ]; then
    _queue "SIG_JOB_IMAGE is unset — the pinned image ref (never :latest, P31.4)."
  fi
  case "${SIG_JOB_IMAGE}" in
    *:latest|*[@:]sha256:*) ;;
    *:*) _queue "SIG_JOB_IMAGE=${SIG_JOB_IMAGE} is a mutable tag — deploy by @sha256: digest." ;;
    *) _queue "SIG_JOB_IMAGE=${SIG_JOB_IMAGE} carries no tag/digest." ;;
  esac
  if [ -z "${SIG_STATUS_AUTHOR:-}" ]; then
    _queue "SIG_STATUS_AUTHOR is unset — the recorded operator authorisation."
  fi
  if [ -z "${SIG_STATUS_SA_EMAIL:-}" ]; then
    _queue "SIG_STATUS_SA_EMAIL is unset — the job's least-privilege identity."
  fi
  if [ -z "${SIG_SCHEDULER_SA_EMAIL:-}" ]; then
    _queue "SIG_SCHEDULER_SA_EMAIL is unset — the scheduler invoker identity."
  fi
  _log "author: ${SIG_STATUS_AUTHOR} (recorded); image: ${SIG_JOB_IMAGE}"
}

_deploy_cmd() {
  echo "gcloud run jobs deploy ${SIG_STATUS_JOB} --image ${SIG_JOB_IMAGE:-<unset>} --region ${SIG_RUN_REGION} --service-account ${SIG_STATUS_SA_EMAIL:-<unset>} --no-allow-unauthenticated --set-env-vars SIG_STATUS_BUCKET=${SIG_GCP_PROJECT:-<project>}-sig-web,SIG_OPS_CADENCE=ops/cadence.toml,SIG_OPS_DECLARED_GCS=gs://${SIG_GCP_PROJECT:-<project>}-sig-restricted/ops/declared/live-diff.json --args status-publish,--apply"
}

_sched_cmd() {
  echo "gcloud scheduler jobs create http ${SIG_STATUS_SCHED} --schedule '12 */6 * * *' --time-zone=Etc/UTC --uri https://${SIG_RUN_REGION}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${SIG_GCP_PROJECT:-<project>}/jobs/${SIG_STATUS_JOB}:run --http-method=POST --oauth-service-account-email=${SIG_SCHEDULER_SA_EMAIL:-<unset>}   # every 6h — D-J3-11"
}

if [ "${MODE}" = "check" ]; then
  _plan "$(_deploy_cmd)          # the Cloud Run job (least-privilege, read-only views)"
  _plan "$(_sched_cmd)           # the 6-hourly trigger"
  _plan "gcloud run jobs add-iam-policy-binding ${SIG_STATUS_JOB} --region ${SIG_RUN_REGION} --member 'serviceAccount:${SIG_SCHEDULER_SA_EMAIL:-<unset>}' --role roles/run.invoker"
  _plan "commit ops/cadence.toml's status row in the SAME re-run commit — the undeclared-trigger report stays clean"
  _plan "restore point: gcloud scheduler jobs delete ${SIG_STATUS_SCHED} && gcloud run jobs delete ${SIG_STATUS_JOB} (definition removal)"
  _log "prepared_not_executed — OM-19 queue; re-run: ${RERUN}"
  exit 0
fi

_window
_env

run gcloud run jobs deploy "${SIG_STATUS_JOB}" \
  --image "${SIG_JOB_IMAGE}" --region "${SIG_RUN_REGION}" \
  --service-account "${SIG_STATUS_SA_EMAIL}" --no-allow-unauthenticated \
  --set-env-vars "SIG_STATUS_BUCKET=${SIG_GCP_PROJECT}-sig-web,SIG_OPS_CADENCE=ops/cadence.toml,SIG_OPS_DECLARED_GCS=gs://${SIG_GCP_PROJECT}-sig-restricted/ops/declared/live-diff.json" \
  --args "status-publish,--apply"

run gcloud scheduler jobs create http "${SIG_STATUS_SCHED}" \
  --schedule '12 */6 * * *' --time-zone=Etc/UTC \
  --uri "https://${SIG_RUN_REGION}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${SIG_GCP_PROJECT}/jobs/${SIG_STATUS_JOB}:run" \
  --http-method=POST --oauth-service-account-email="${SIG_SCHEDULER_SA_EMAIL}"

run gcloud run jobs add-iam-policy-binding "${SIG_STATUS_JOB}" \
  --region "${SIG_RUN_REGION}" \
  --member "serviceAccount:${SIG_SCHEDULER_SA_EMAIL}" --role roles/run.invoker

_log "applied — record the cadence.toml status row in the same commit."
