#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
#
# ops/gcp/watch-publish.sh — P37.33 (K7 WX-03, D-K7-2 [B-22] = the lane): the
# daily `sig-watch-publish` Cloud Run job + its Cloud Scheduler trigger (the
# OM-20 named mutation: "the watch-lane job's scheduled production run";
# the GATE-G6 §4 list dated 2026-11-05T15:20Z names P37.33 verbatim,
# operator selection "Approve all 15 (rec.)" — expires GATE-ACCEPT-R11;
# window AR-3 + AR-2).
#
# The leg (K7 §7 — a status-lane step, no new service):
#   1. `gcloud run jobs deploy sig-watch-publish` — the pinned-digest image
#      (P31.4/ADR-111: never :latest), least-privilege identity (ACT-13:
#      read-only on the publishable watch rows + the web bucket's watch/
#      prefix; no spine write, no release tree).
#   2. `gcloud scheduler jobs create http sig-sched-watch-publish`
#      `--schedule '30 7 * * *'` (daily — after the agenda dailies'
#      05:0x fires so the day's items publish the same morning,
#      SIG-WATCH-008 within-24h) invoking the job.
#   3. IAM invoker binding for the scheduler SA on the job.
#   4. ops/cadence.toml's [[maintenance]] watch-publish row flips
#      `state = "enabled"` IN THE SAME RE-RUN COMMIT so live-diff's
#      declared-vs-live report stays clean; the daily ingest cadence
#      (legistar/primegov/civicclerk/escribe → daily, sam_gov →
#      twice-weekly) binds at the declaration-bundle republish
#      (SIG_OPS_DECLARED_GCS).
#   Restore point: pause the trigger ("lane job paused"), then delete the
#   job (definition removal).
#
# Nothing runs without the AR-3 + AR-2 window: inside 03:00–06:30Z or the
# monthly batch window (day 6 00:00Z → day 13 12:00Z) exits 42 (queued).
#
# Usage:
#   ops/gcp/watch-publish.sh [--check|--dry-run]   # plan only (default)
#   ops/gcp/watch-publish.sh --apply               # the job + trigger create
#
# Environment (apply):
#   SIG_GCP_PROJECT        the GCP project (GL-GATE-04)
#   ADC                    `gcloud auth application-default login`
#   SIG_JOB_IMAGE          the pinned image ref (a sha tag or @sha256: digest —
#                          `:latest`/untagged refused)
#   SIG_WATCH_AUTHOR       the recorded operator authorisation for THIS leg
#   SIG_RUN_REGION         the Cloud Run region (default us-central1)
#   SIG_WATCH_SA_EMAIL     the job's least-privilege identity
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
  *) echo "watch-publish.sh: unknown mode '${1:-}'" >&2; exit 64 ;;
esac

export SIG_GCP_MODE="$MODE"
require_project

: "${SIG_RUN_REGION:=us-central1}"
: "${SIG_WATCH_JOB:=sig-watch-publish}"
: "${SIG_WATCH_SCHED:=sig-sched-watch-publish}"
RERUN="implement-spec spec=docs/tickets/457_P37.33__watch-lane-and-cadence.md live_verification=true"

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
  if [ -z "${SIG_WATCH_AUTHOR:-}" ]; then
    _queue "SIG_WATCH_AUTHOR is unset — the recorded operator authorisation."
  fi
  if [ -z "${SIG_WATCH_SA_EMAIL:-}" ]; then
    _queue "SIG_WATCH_SA_EMAIL is unset — the job's least-privilege identity."
  fi
  if [ -z "${SIG_SCHEDULER_SA_EMAIL:-}" ]; then
    _queue "SIG_SCHEDULER_SA_EMAIL is unset — the scheduler invoker identity."
  fi
  _log "author: ${SIG_WATCH_AUTHOR} (recorded); image: ${SIG_JOB_IMAGE}"
}

_deploy_cmd() {
  echo "gcloud run jobs deploy ${SIG_WATCH_JOB} --image ${SIG_JOB_IMAGE:-<unset>} --region ${SIG_RUN_REGION} --service-account ${SIG_WATCH_SA_EMAIL:-<unset>} --no-allow-unauthenticated --set-env-vars SIG_WATCH_BUCKET=${SIG_GCP_PROJECT:-<project>}-sig-web,SIG_OPS_CADENCE=ops/cadence.toml --args watch-publish,--apply"
}

_sched_cmd() {
  echo "gcloud scheduler jobs create http ${SIG_WATCH_SCHED} --schedule '30 7 * * *' --time-zone=Etc/UTC --uri https://${SIG_RUN_REGION}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${SIG_GCP_PROJECT:-<project>}/jobs/${SIG_WATCH_JOB}:run --http-method=POST --oauth-service-account-email=${SIG_SCHEDULER_SA_EMAIL:-<unset>}   # daily — D-K7-2, after the agenda dailies (SIG-WATCH-008 within-24h)"
}

if [ "${MODE}" = "check" ]; then
  _plan "$(_deploy_cmd)          # the Cloud Run job (least-privilege, read-only)"
  _plan "$(_sched_cmd)           # the daily trigger"
  _plan "gcloud run jobs add-iam-policy-binding ${SIG_WATCH_JOB} --region ${SIG_RUN_REGION} --member 'serviceAccount:${SIG_SCHEDULER_SA_EMAIL:-<unset>}' --role roles/run.invoker"
  _plan "flip ops/cadence.toml's [[maintenance]] watch-publish row to state=enabled in the SAME re-run commit; the daily/twice-weekly ingest cadence binds at the declaration-bundle republish (SIG_OPS_DECLARED_GCS)"
  _plan "restore point: pause ${SIG_WATCH_SCHED} ('lane job paused'), then gcloud run jobs delete ${SIG_WATCH_JOB} (definition removal)"
  _log "prepared_not_executed — OM-19 queue; re-run: ${RERUN}"
  exit 0
fi

_window
_env

run gcloud run jobs deploy "${SIG_WATCH_JOB}" \
  --image "${SIG_JOB_IMAGE}" --region "${SIG_RUN_REGION}" \
  --service-account "${SIG_WATCH_SA_EMAIL}" --no-allow-unauthenticated \
  --set-env-vars "SIG_WATCH_BUCKET=${SIG_GCP_PROJECT}-sig-web,SIG_OPS_CADENCE=ops/cadence.toml" \
  --args "watch-publish,--apply"

run gcloud scheduler jobs create http "${SIG_WATCH_SCHED}" \
  --schedule '30 7 * * *' --time-zone=Etc/UTC \
  --uri "https://${SIG_RUN_REGION}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${SIG_GCP_PROJECT}/jobs/${SIG_WATCH_JOB}:run" \
  --http-method=POST --oauth-service-account-email="${SIG_SCHEDULER_SA_EMAIL}"

run gcloud run jobs add-iam-policy-binding "${SIG_WATCH_JOB}" \
  --region "${SIG_RUN_REGION}" \
  --member "serviceAccount:${SIG_SCHEDULER_SA_EMAIL}" --role roles/run.invoker

_log "applied — flip the cadence.toml maintenance row to enabled in the same commit."
