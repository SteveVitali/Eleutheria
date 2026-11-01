#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
#
# ops/gcp/release-cadence.sh — P36.44 (REL-07): the release cadence's two
# Cloud Scheduler triggers (the OM-20 named mutations; the GATE-G5 §4 list
# names P36.44 verbatim — expires GATE-G6; window AR-3 + AR-2).
#
# The leg (G3 §7.2 / SIG-REL-011 + SIG-OPS-008 / D-G3-4 [B-9] = yes):
#   1. `gcloud scheduler jobs create http sig-sched-release-cut` —
#      `--schedule '0 14 15-17 * *'` (the three candidate days; the job-side
#      evaluator suppresses every day that is not the first weekday on/after
#      the 15th) invoking the sig-release job with an args override:
#      `sig-ops release-cadence --apply --alert` (evaluate → journal → the
#      max-age alert → `release cut` when the decision is cut; the cut
#      itself refuses inside AR-3 without --emergency).
#   2. `gcloud scheduler jobs create http sig-sched-materialize` —
#      `--schedule '0 8 * * 0'` (G1 §3.6 verbatim: weekly Sundays 08:00 UTC)
#      invoking the existing sig-materialize job on its BAKED args (the
#      materializer step — no override; the materialized views then lag live
#      claims by at most 7 days, SIG-OPS-008).
#   3. cadence.toml gains both rows IN THE SAME RE-RUN COMMIT — the release-
#      cut row + sig-materialize's note updated from "no trigger by design"
#      — so live-diff's undeclared-trigger report stays clean.
#   Restore point: delete the two triggers (definition removal; the jobs
#   themselves are untouched).
#
# Preconditions (checked on --apply): the sig-release + sig-materialize jobs
# exist (D-P35.53-1's sig-release leg may still be queued — an absent target
# job queues this leg too, it is never assumed).
#
# Nothing runs without the AR-3 + AR-2 window: inside 03:00–06:30Z or the
# monthly batch window (day 6 00:00Z → day 13 12:00Z) exits 42 (queued).
#
# Usage:
#   ops/gcp/release-cadence.sh [--check|--dry-run]   # plan only (default)
#   ops/gcp/release-cadence.sh --apply               # the two trigger creates
#
# Environment (apply):
#   SIG_GCP_PROJECT        the GCP project (GL-GATE-04)
#   ADC                    `gcloud auth application-default login`
#   SIG_RUN_REGION         the Cloud Run region (default us-central1)
#   SIG_CADENCE_AUTHOR     the recorded operator authorisation for THIS leg
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
  *) echo "release-cadence.sh: unknown mode '${1:-}'" >&2; exit 64 ;;
esac

export SIG_GCP_MODE="$MODE"
require_project

: "${SIG_RUN_REGION:=us-central1}"
: "${SIG_RELEASE_JOB:=sig-release}"
: "${SIG_MATERIALIZE_JOB:=sig-materialize}"
: "${SIG_CUT_SCHED:=sig-sched-release-cut}"
: "${SIG_MAT_SCHED:=sig-sched-materialize}"
# The re-run prompt this row's contract carries (the ticket filename — the
# contract's own "-scheduler" Run line is the stale T3-skeleton name).
RERUN="implement-spec spec=docs/tickets/387_P36.44__release-cadence-automation.md live_verification=true"

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
  if [ -z "${SIG_CADENCE_AUTHOR:-}" ]; then
    _queue "SIG_CADENCE_AUTHOR is unset — the recorded operator authorisation."
  fi
  if [ -z "${SIG_SCHEDULER_SA_EMAIL:-}" ]; then
    _queue "SIG_SCHEDULER_SA_EMAIL is unset — the scheduler invoker identity."
  fi
  _log "author: ${SIG_CADENCE_AUTHOR} (recorded)"
}

_targets() {
  [ "${MODE}" = "check" ] && return 0
  gcloud run jobs describe "${SIG_RELEASE_JOB}" --region "${SIG_RUN_REGION}" \
    --project "${SIG_GCP_PROJECT}" >/dev/null 2>&1 \
    || _queue "${SIG_RELEASE_JOB} is absent — D-P35.53-1's release-infra leg lands it first."
  gcloud run jobs describe "${SIG_MATERIALIZE_JOB}" --region "${SIG_RUN_REGION}" \
    --project "${SIG_GCP_PROJECT}" >/dev/null 2>&1 \
    || _queue "${SIG_MATERIALIZE_JOB} is absent — materialize.sh's job leg lands it first."
  _log "target jobs present: ${SIG_RELEASE_JOB}, ${SIG_MATERIALIZE_JOB}"
}

_run_uri() {
  echo "https://${SIG_RUN_REGION}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${SIG_GCP_PROJECT:-<project>}/jobs/$1:run"
}

_cut_cmd() {
  echo "gcloud scheduler jobs create http ${SIG_CUT_SCHED} --schedule '0 14 15-17 * *' --time-zone=Etc/UTC --uri $(_run_uri "${SIG_RELEASE_JOB}") --http-method=POST --oauth-service-account-email=${SIG_SCHEDULER_SA_EMAIL:-<unset>} --message-body '{\"overrides\":{\"containerOverrides\":[{\"args\":[\"-c\",\"exec sig-ops release-cadence --apply --alert --registry \${SIG_RELEASE_REGISTRY_URI}\"]}]}}'   # days 15-17 14:00Z — the evaluator suppresses non-first-weekdays"
}

_mat_cmd() {
  echo "gcloud scheduler jobs create http ${SIG_MAT_SCHED} --schedule '0 8 * * 0' --time-zone=Etc/UTC --uri $(_run_uri "${SIG_MATERIALIZE_JOB}") --http-method=POST --oauth-service-account-email=${SIG_SCHEDULER_SA_EMAIL:-<unset>}   # weekly Sundays 08:00 UTC — G1 §3.6; the job's baked args run the materializer step"
}

if [ "${MODE}" = "check" ]; then
  _plan "$(_cut_cmd)"
  _plan "$(_mat_cmd)"
  _plan "commit ops/cadence.toml's release-cut + materialize rows in the SAME re-run commit — live-diff's undeclared-trigger report stays clean (sig-materialize's [[manual_jobs]] note flips off 'no trigger by design')"
  _plan "restore point: gcloud scheduler jobs delete ${SIG_CUT_SCHED} && gcloud scheduler jobs delete ${SIG_MAT_SCHED} (definition removal — the jobs are untouched)"
  _log "prepared_not_executed — OM-19 queue; re-run: ${RERUN}"
  exit 0
fi

_window
_env
_targets

run gcloud scheduler jobs create http "${SIG_CUT_SCHED}" \
  --schedule '0 14 15-17 * *' --time-zone=Etc/UTC \
  --uri "$(_run_uri "${SIG_RELEASE_JOB}")" \
  --http-method=POST --oauth-service-account-email="${SIG_SCHEDULER_SA_EMAIL}" \
  --message-body '{"overrides":{"containerOverrides":[{"args":["-c","exec sig-ops release-cadence --apply --alert --registry ${SIG_RELEASE_REGISTRY_URI}"]}]}}'

run gcloud scheduler jobs create http "${SIG_MAT_SCHED}" \
  --schedule '0 8 * * 0' --time-zone=Etc/UTC \
  --uri "$(_run_uri "${SIG_MATERIALIZE_JOB}")" \
  --http-method=POST --oauth-service-account-email="${SIG_SCHEDULER_SA_EMAIL}"

_log "applied — record both cadence.toml rows in the same commit."
