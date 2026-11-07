#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
#
# ops/gcp/parser-canary.sh — the scheduled parser-canary leg of P37.15
# (BL-025 canary part, SIG-PARSE-007/008; GATE-G6 §4's 11D OM-20 list names
# P37.15 verbatim — the named mutation runs in-ticket under the contract's
# own preconditions, restore point and rollback). The permanent
# `sig-parser-canary` Cloud Run job — the daily fixture-replay canary per
# parser family — plus its `sig-sched-parser-canary` Cloud Scheduler
# trigger.
#
# Declaration: ops/parser_canary.toml (sig.parser-canary/1 — rendered by
# `sig-ops parser-canary job`; this script never hand-copies a name). This
# script owns the (windowed) mutations:
#
#   ./parser-canary.sh --check [action]   # (default) plan-only: NO ADC, NO
#                                         # network — every command printed.
#   ./parser-canary.sh --apply <action>   # windowed + dependency-gated +
#                                         # operator ADC.
#   ./parser-canary.sh --verify           # read-only live diff (ADC, never
#                                         # window-gated)
#   ./parser-canary.sh --verify --from-state DIR
#                                         # offline diff of a recorded snapshot
#
# Actions:
#   prestate   the restore point: `run jobs list`, `scheduler jobs list`,
#              the restricted bucket's versioning state (the probe records
#              are new objects on a versioned bucket), the rendered
#              declaration. READ-ONLY — any time.
#   deps       the live: edges — the sig-quality-probe-rt SA exists
#              (live:P34.42b / the P34.43 exec leg), the sig-scheduler
#              invoker identity exists, bucket versioning is on. Every
#              missing edge is exit 42 — queued, never a partial apply.
#   job        `gcloud run jobs deploy sig-parser-canary` on the rendered
#              argv (digest-pinned image — SIG_PARSER_CANARY_IMAGE resolved
#              like every job's, never :latest) + the scheduler's
#              run.invoker binding.
#   trigger    the scheduler create-or-update to the declared cron —
#              `45 1 1-5,14-31 * *` (01:45Z on days 1–5 and 14–31: never
#              03:00–06:30Z, structurally outside the day-6→13 batch
#              window, trailing the rdc probe's fire).
#   run        the canary run itself: `gcloud run jobs execute
#              sig-parser-canary --wait` — one manual execution that proves
#              the deployed job end-to-end (records land under
#              ops/probes/parser-canary/).
#   verify     poststate capture + `sig-ops parser-canary job
#              verify-describe` / `verify-trigger` against the recorded
#              describes. READ-ONLY.
#   rollback   pause, then delete the trigger and the job by EXACT NAME
#              (name-checked); remove the scheduler's invoker binding.
#              Deliberately NOT window-gated — restoring prestate is always
#              safe. Probe records stay: they are history.
#   all        prestate → deps → job → trigger → verify.
#
# The job needs no capture-fetch leg and no DB: the sealed corpus rides the
# workload image (tests/parser_canary/ is COPYed into /app — the image
# digest pins the corpus version).
#
# Live window (OM-19, the contract's AR-3 + AR-2 slot): applies run ≥
# ${SIG_PARSER_CANARY_EARLIEST}, never 03:00–06:30Z, and never inside the
# monthly batch window (day 6 00:00Z → day 13 12:00Z — the ingest batch
# owns those nights; the leg does not mutate then either). Every refusal
# exits 42 — queued; the RETURN PASS re-run prompt is printed.
# SIG_PARSER_CANARY_NOW overrides the clock for the offline guard test only.
set -euo pipefail

_here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=ops/gcp/config.sh
. "${_here}/config.sh"
# shellcheck source=ops/gcp/lib.sh
. "${_here}/lib.sh"

ACTION="all"
FROM_STATE=""
case "${1:-}" in
  --verify)
    # Read-only: live diff (ADC) — or an offline recorded-snapshot diff with
    # --from-state DIR. Never window-gated; a diff mutates nothing.
    SIG_GCP_MODE="verify"
    ACTION="verify"
    shift
    if [ "${1:-}" = "--from-state" ]; then
      [ $# -ge 2 ] || { echo "parser-canary.sh: --from-state needs a directory" >&2; exit 64; }
      FROM_STATE="$2"; shift 2
    fi
    ;;
  *)
    parse_mode "${1:-}"
    shift || true
    ACTION="${1:-all}"
    ;;
esac
export SIG_GCP_MODE
STATE_DIR="${2:-${SIG_PARSER_CANARY_STATE_DIR}}"

_repo="$(cd "${_here}/../.." && pwd)"

RERUN='implement-spec spec=docs/tickets/437_P37.15__scheduled-parser-canary.md live_verification=true'

_sigops() {
  (cd "${_repo}" && uv run --quiet sig-ops "$@")
}

_sa_email() { printf '%s@%s.iam.gserviceaccount.com' "$1" "${SIG_GCP_PROJECT}"; }

_sha256() {
  if command -v sha256sum >/dev/null 2>&1; then sha256sum "$1" | awk '{print $1}';
  else shasum -a 256 "$1" | awk '{print $1}'; fi
}

# `assert_window` — the OM-19/AR-3 clock guard. Check mode is never gated —
# a printed plan mutates nothing. Every refusal prints the re-run prompt
# and exits 42 (queued).
assert_window() {
  [ "${SIG_GCP_MODE}" = "apply" ] || return 0
  local now hhmm dom
  now="${SIG_PARSER_CANARY_NOW:-$(date -u +%Y-%m-%dT%H:%M:%SZ)}"
  if [[ "${now}" < "${SIG_PARSER_CANARY_EARLIEST}" ]]; then
    _log "QUEUED (exit 42): now=${now} < ${SIG_PARSER_CANARY_EARLIEST} — the AR-3/AR-2 freeze."
    _log "re-run: ${RERUN} (scope: the job creation + trigger + run leg)"
    exit 42
  fi
  hhmm="${now:11:5}"
  if [[ "${hhmm}" > "02:59" && "${hhmm}" < "06:30" ]]; then
    _log "QUEUED (exit 42): ${now} is inside 03:00–06:30Z — never mutate then."
    _log "re-run: ${RERUN} (scope: the job creation + trigger + run leg)"
    exit 42
  fi
  dom="${now:8:2}"
  if [[ "${dom}" > "05" && "${dom}" < "14" ]]; then
    if [[ "${dom}" < "13" || "${hhmm}" < "12:00" ]]; then
      _log "QUEUED (exit 42): ${now} is inside the monthly batch window (day 6 00:00Z → day 13 12:00Z)."
      _log "re-run: ${RERUN} (scope: the job creation + trigger + run leg)"
      exit 42
    fi
  fi
  _log "window OK: ${now} (≥ ${SIG_PARSER_CANARY_EARLIEST}, outside 03:00–06:30Z, outside the batch window)"
}

# `assert_deps` — the live: edges the mutations need (apply only; each
# missing edge exits 42 — queued, not a partial apply).
assert_deps() {
  [ "${SIG_GCP_MODE}" = "apply" ] || return 0
  local missing=0
  if ! gcloud iam service-accounts describe "$(_sa_email "${SIG_SA_QUALITY_PROBE}")" \
      --project "${SIG_GCP_PROJECT}" >/dev/null 2>&1; then
    _log "  missing live edge: ${SIG_SA_QUALITY_PROBE} — created by live:P34.42b (or the P34.43 exec leg)"
    missing=1
  fi
  if ! gcloud iam service-accounts describe "$(_sa_email "${SIG_SA_SCHEDULER}")" \
      --project "${SIG_GCP_PROJECT}" >/dev/null 2>&1; then
    _log "  missing live edge: ${SIG_SA_SCHEDULER} — the P25.7 invoker identity"
    missing=1
  fi
  if ! gcloud secrets describe sig-alert-webhook-token \
      --project "${SIG_GCP_PROJECT}" >/dev/null 2>&1; then
    _log "  missing live edge: secret sig-alert-webhook-token — the recorded-alert caller credential"
    missing=1
  fi
  if [ "${missing}" -gt 0 ]; then
    _log "QUEUED (exit 42): a live edge has not landed — see above."
    _log "re-run: ${RERUN} (scope: the job creation + trigger + run leg)"
    exit 42
  fi
}

# `_capture <dir>` — the leg's prestate/poststate snapshot (read-only).
_capture() {
  local dir="$1"
  mkdir -p "${dir}"
  gcloud run jobs list --region "${SIG_GCP_REGION}" \
    --project "${SIG_GCP_PROJECT}" --format json > "${dir}/run-jobs.json"
  gcloud scheduler jobs list --location "${SIG_GCP_REGION}" \
    --project "${SIG_GCP_PROJECT}" --format json > "${dir}/scheduler-jobs.json" \
    || printf '[]' > "${dir}/scheduler-jobs.json"
  gcloud storage buckets describe "gs://${SIG_BUCKET_RESTRICTED}" \
    --format='value(versioning.enabled)' > "${dir}/bucket-versioning.txt" \
    || printf 'unknown\n' > "${dir}/bucket-versioning.txt"
  _sigops parser-canary job plan > "${dir}/parser-canary-decl.json"
  (cd "${dir}" && for f in *.json; do _sha256 "$f"; done) > "${dir}/sha256s.txt"
}

do_prestate() {
  _log "-- prestate ($(date -u +%FT%TZ)): the leg's restore point under ${STATE_DIR}/pre (read-only) --"
  if [ "${SIG_GCP_MODE}" = "check" ]; then
    _plan "gcloud run jobs list > pre/run-jobs.json"
    _plan "gcloud scheduler jobs list > pre/scheduler-jobs.json"
    _plan "gcloud storage buckets describe gs://${SIG_BUCKET_RESTRICTED} versioning > pre/bucket-versioning.txt"
    _plan "sig-ops parser-canary job plan > pre/parser-canary-decl.json  (the rendered declaration)"
    _plan "sha256 sidecars over every capture > pre/sha256s.txt"
    return 0
  fi
  _capture "${STATE_DIR}/pre"
  local ver; ver="$(cat "${STATE_DIR}/pre/bucket-versioning.txt" 2>/dev/null || true)"
  if [ "${ver}" != "Enabled" ] && [ "${ver}" != "True" ] && [ "${ver}" != "true" ]; then
    _log "ERROR: versioning on gs://${SIG_BUCKET_RESTRICTED} reads '${ver}' — the bucket clause requires it ON before the first probe record. Refusing." >&2
    exit 4
  fi
  _log "   prestate recorded under ${STATE_DIR}/pre (date -u: $(date -u +%FT%TZ)); bucket versioning ${ver}"
}

do_deps() {
  _log "-- deps ($(date -u +%FT%TZ)): the live: edges (${SIG_SA_QUALITY_PROBE}, ${SIG_SA_SCHEDULER}, sig-alert-webhook-token) --"
  if [ "${SIG_GCP_MODE}" = "check" ]; then
    _plan "gcloud iam service-accounts describe $(_sa_email "${SIG_SA_QUALITY_PROBE}")   (live:P34.42b)"
    _plan "gcloud iam service-accounts describe $(_sa_email "${SIG_SA_SCHEDULER}")       (live:P25.7)"
    _plan "gcloud secrets describe sig-alert-webhook-token                              (the recorded-alert credential)"
    _plan "missing edge → exit 42 (queued), never a partial apply"
    return 0
  fi
  assert_deps
  _log "   deps OK — every live edge holds (date -u: $(date -u +%FT%TZ))"
}

do_job() {
  assert_window
  assert_deps
  _log "-- job ($(date -u +%FT%TZ)): deploy ${SIG_PARSER_CANARY_JOB} on ${SIG_SA_QUALITY_PROBE} --"
  local image="${SIG_PARSER_CANARY_IMAGE:-}"
  if [ -z "${image}" ]; then
    if [ "${SIG_GCP_MODE}" = "check" ]; then
      image="${SIG_API_IMAGE}:parser-canary"   # placeholder — printed, never resolved
    else
      _log "ERROR: SIG_PARSER_CANARY_IMAGE must name the workload image (a ${SIG_API_IMAGE}:<tag> — resolved to a digest, never :latest)." >&2
      exit 2
    fi
  fi
  image="$(pin_image_digest "${image}")"
  local alerts_url="${SIG_ALERT_WEBHOOK_URL:-}"
  if [ "${SIG_GCP_MODE}" = "check" ] && [ -z "${alerts_url}" ]; then
    alerts_url="<url-of-${SIG_ALERTS_SERVICE}>"
  elif [ -z "${alerts_url}" ]; then
    alerts_url="$(gcloud run services describe "${SIG_ALERTS_SERVICE}" \
      --region "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}" \
      --format='value(status.url)')"
  fi
  local rendered
  rendered="$(_sigops parser-canary job render \
    --image "${image}" \
    --project "${SIG_GCP_PROJECT}" --region "${SIG_GCP_REGION}" \
    --env "SIG_GCP_PROJECT=${SIG_GCP_PROJECT}" \
    --env "SIG_OPS_GCS_BUCKET=${SIG_BUCKET_RESTRICTED}" \
    --env "SIG_PARSER_CANARY_PROBE_PREFIX=${SIG_PARSER_CANARY_PREFIX}" \
    --env "SIG_PARSER_CANARY_JOB_NAME=${SIG_PARSER_CANARY_JOB}" \
    --env "SIG_PARSER_CANARY_ALERT_KIND=parser-canary" \
    --env "SIG_ALERT_WEBHOOK_URL=${alerts_url}")"
  if [ "${SIG_GCP_MODE}" = "check" ]; then
    printf '%s' "${rendered}" | python3 -c 'import json,sys,shlex
d = json.load(sys.stdin)
for key in ("deploy", "job_invoker"):
    print(" ".join(shlex.quote(a) for a in d[key]))' \
      | while IFS= read -r line; do _plan "${line}"; done
    return 0
  fi
  local -a argv
  mapfile -t argv < <(printf '%s' "${rendered}" | python3 -c 'import json,sys
print("\n".join(json.load(sys.stdin)["deploy"]))')
  run "${argv[@]}"
  mapfile -t argv < <(printf '%s' "${rendered}" | python3 -c 'import json,sys
print("\n".join(json.load(sys.stdin)["job_invoker"]))')
  run "${argv[@]}"
  _log "   rollback: gcloud run jobs delete ${SIG_PARSER_CANARY_JOB} --quiet (name-checked)"
}

do_trigger() {
  assert_window
  assert_deps
  _log "-- trigger ($(date -u +%FT%TZ)): ${SIG_PARSER_CANARY_SCHED} → ${SIG_PARSER_CANARY_JOB} --"
  local uri="https://${SIG_GCP_REGION}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${SIG_GCP_PROJECT}/jobs/${SIG_PARSER_CANARY_JOB}:run"
  local sched_sa; sched_sa="$(_sa_email "${SIG_SA_SCHEDULER}")"
  local schedule
  schedule="$(_sigops parser-canary job plan | python3 -c 'import json,sys; print(json.load(sys.stdin)["scheduler"]["schedule"])')"
  if [ "${SIG_GCP_MODE}" = "check" ]; then
    _plan "gcloud scheduler jobs create http ${SIG_PARSER_CANARY_SCHED} --schedule '${schedule}' --time-zone=Etc/UTC --uri ${uri} --http-method=POST --oauth-service-account-email=${sched_sa}   # (update if already present)"
    return 0
  fi
  if gcloud scheduler jobs describe "${SIG_PARSER_CANARY_SCHED}" \
      --location "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}" >/dev/null 2>&1; then
    run gcloud scheduler jobs update http "${SIG_PARSER_CANARY_SCHED}" \
      --location "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}" \
      --schedule "${schedule}" --time-zone=Etc/UTC --uri "${uri}" \
      --http-method=POST --oauth-service-account-email="${sched_sa}"
  else
    run gcloud scheduler jobs create http "${SIG_PARSER_CANARY_SCHED}" \
      --location "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}" \
      --schedule "${schedule}" --time-zone=Etc/UTC --uri "${uri}" \
      --http-method=POST --oauth-service-account-email="${sched_sa}"
  fi
  _log "   rollback: gcloud scheduler jobs pause + delete ${SIG_PARSER_CANARY_SCHED} (name-checked)"
}

do_run() {
  assert_window
  assert_deps
  _log "-- run ($(date -u +%FT%TZ)): the canary run itself — execute ${SIG_PARSER_CANARY_JOB} --"
  if [ "${SIG_GCP_MODE}" = "check" ]; then
    _plan "gcloud run jobs execute ${SIG_PARSER_CANARY_JOB} --wait   # one manual execution — records land under ${SIG_PARSER_CANARY_PREFIX}"
    return 0
  fi
  run gcloud run jobs execute "${SIG_PARSER_CANARY_JOB}" \
    --region "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}" --wait
  _log "   execution recorded — the probe records under ${SIG_PARSER_CANARY_PREFIX} carry the verdict"
}

do_verify() {
  _log "-- verify: poststate capture → verify-describe + verify-trigger against the declaration --"
  if [ "${SIG_GCP_MODE}" = "check" ]; then
    _plan "re-capture under ${STATE_DIR}/post (same reads as prestate)"
    _plan "gcloud run jobs describe ${SIG_PARSER_CANARY_JOB} --format json > post/job.json"
    _plan "gcloud scheduler jobs describe ${SIG_PARSER_CANARY_SCHED} --format json > post/trigger.json"
    _plan "sig-ops parser-canary job verify-describe --describe post/job.json      (the job posture)"
    _plan "sig-ops parser-canary job verify-trigger --describe post/trigger.json   (the trigger posture)"
    return 0
  fi
  if [ -n "${FROM_STATE}" ]; then
    _sigops parser-canary job verify-describe --describe "${FROM_STATE}/job.json" \
      --project "${SIG_GCP_PROJECT}"
    _sigops parser-canary job verify-trigger --describe "${FROM_STATE}/trigger.json" \
      --project "${SIG_GCP_PROJECT}" --region "${SIG_GCP_REGION}"
    return 0
  fi
  _capture "${STATE_DIR}/post"
  gcloud run jobs describe "${SIG_PARSER_CANARY_JOB}" --region "${SIG_GCP_REGION}" \
    --project "${SIG_GCP_PROJECT}" --format json > "${STATE_DIR}/post/job.json"
  gcloud scheduler jobs describe "${SIG_PARSER_CANARY_SCHED}" --location "${SIG_GCP_REGION}" \
    --project "${SIG_GCP_PROJECT}" --format json > "${STATE_DIR}/post/trigger.json"
  _sigops parser-canary job verify-describe --describe "${STATE_DIR}/post/job.json" \
    --project "${SIG_GCP_PROJECT}"
  _sigops parser-canary job verify-trigger --describe "${STATE_DIR}/post/trigger.json" \
    --project "${SIG_GCP_PROJECT}" --region "${SIG_GCP_REGION}"
  _log "verify OK — job + trigger match the declaration."
}

do_rollback() {
  _log "-- rollback ($(date -u +%FT%TZ)): pause trigger → delete trigger → delete job (name-checked) --"
  if [ "${SIG_GCP_MODE}" = "check" ]; then
    _plan "gcloud scheduler jobs pause ${SIG_PARSER_CANARY_SCHED}"
    _plan "gcloud scheduler jobs delete ${SIG_PARSER_CANARY_SCHED} --quiet"
    _plan "gcloud run jobs remove-iam-policy-binding ${SIG_PARSER_CANARY_JOB} --member sig-scheduler"
    _plan "gcloud run jobs delete ${SIG_PARSER_CANARY_JOB} --quiet"
    _plan "probe records under ${SIG_PARSER_CANARY_PREFIX} STAY — they are history"
    return 0
  fi
  gcloud scheduler jobs pause "${SIG_PARSER_CANARY_SCHED}" \
    --location "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}" || true
  _log "   paused ${SIG_PARSER_CANARY_SCHED}"
  gcloud scheduler jobs delete "${SIG_PARSER_CANARY_SCHED}" \
    --location "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}" --quiet || true
  _log "   deleted ${SIG_PARSER_CANARY_SCHED}"
  gcloud run jobs remove-iam-policy-binding "${SIG_PARSER_CANARY_JOB}" \
    --region "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}" \
    --member="serviceAccount:$(_sa_email "${SIG_SA_SCHEDULER}")" \
    --role=roles/run.invoker || true
  gcloud run jobs delete "${SIG_PARSER_CANARY_JOB}" \
    --region "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}" --quiet || true
  _log "   deleted ${SIG_PARSER_CANARY_JOB}"
  _log "rollback applied — trigger + job deleted by name; probe records kept (they are history)."
}

# Every non-check path (live verify included — member names embed the project
# id) requires SIG_GCP_PROJECT; check mode tolerates the placeholder.
require_project
# The clock guard precedes the ADC gate so a queued apply exits 42 cleanly.
# `deps` is read-only (it names which live edge is missing) — never gated.
case "${ACTION}" in
  job|trigger|run|all) assert_window ;;
esac
# A live verify reads with ADC; an offline --from-state diff needs none.
if [ -z "${FROM_STATE}" ] && [ "${SIG_GCP_MODE}" != "check" ]; then
  require_adc
fi

banner "P37.15 — the scheduled sig-parser-canary job (BL-025 canary part; GATE-G6 §4)"

case "${ACTION}" in
  prestate)       do_prestate ;;
  deps)           do_deps ;;
  job)            do_job ;;
  trigger)        do_trigger ;;
  run)            do_run ;;
  verify)         do_verify ;;
  rollback)       do_rollback ;;
  all)
    do_prestate
    do_deps
    do_job
    do_trigger
    do_run
    do_verify
    ;;
  *) _log "unknown action: ${ACTION} (prestate|deps|job|trigger|run|verify|rollback|all)" >&2; exit 64 ;;
esac

_log "parser-canary ${ACTION}: ${SIG_GCP_MODE} OK (mode=${SIG_GCP_MODE})"
[ "${SIG_GCP_MODE}" = "check" ] && _log "check OK"
