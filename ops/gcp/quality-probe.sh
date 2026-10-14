#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
#
# ops/gcp/quality-probe.sh — the quality-probe leg of P34.44b (SIG-CONF-006/007,
# ADR-154/205; pre-authorised S5-3/OM-20 "Both + list + P34.45", the "nightly
# quality job" line). The permanent `sig-quality-probe` Cloud Run job — the
# nightly spine-probe (M) checks on the `sig_audit` login — plus its
# `sig-sched-quality-probe` Cloud Scheduler trigger, and the read-only L2
# baseline run over the P34.43 execution host.
#
# Declaration: ops/quality_probe.toml (sig.quality-probe/1 — rendered by
# `sig-ops quality job`; this script never hand-copies a name). This script
# owns the (windowed) mutations:
#
#   ./quality-probe.sh --check [action]   # (default) plan-only: NO ADC, NO
#                                         # network — every command printed.
#   ./quality-probe.sh --apply <action>   # windowed + dependency-gated +
#                                         # operator ADC.
#   ./quality-probe.sh --verify           # read-only live diff (ADC, never
#                                         # window-gated)
#   ./quality-probe.sh --verify --from-state DIR
#                                         # offline diff of a recorded snapshot
#
# Actions:
#   prestate   the restore point: `run jobs list`, `scheduler jobs list`,
#              the restricted bucket's versioning state (AR-2's bucket clause
#              — the probe records are new objects on a versioned bucket),
#              the rendered declaration. READ-ONLY — any time.
#   deps       the live: edges — the sig-quality-probe-rt SA exists
#              (live:P34.42b / the P34.43 exec leg), the `sig_audit` login
#              exists on the Cloud SQL instance (live:P34.43), the two
#              secrets exist, bucket versioning is on. Every missing edge is
#              exit 42 — queued, never a partial apply.
#   job        `gcloud run jobs deploy sig-quality-probe` on the rendered
#              argv (digest-pinned image — SIG_QUALITY_IMAGE resolved like
#              every job's, never :latest) + the scheduler's run.invoker
#              binding on the job.
#   trigger    the scheduler create-or-update to the declared cron —
#              `0 1 1-5,14-31 * *` (01:00Z on days 1–5 and 14–31: never
#              03:00–06:30Z, structurally outside the day-6→13 batch window).
#   alerts-binding
#              the declared alert-path grants: run.invoker on sig-alerts for
#              the runtime identity + the sig-alert-webhook-token secret
#              accessor (both are also declared in ops/iam_identities.toml —
#              this step is idempotent).
#   baseline   the read-only L2 baseline run: a `sig-exec-quality-baseline-
#              <stamp>` one-off on the P34.43 host, whose container runs
#              `sig-ops quality baseline` — every M check over the hosted
#              spine through `sig_audit` (read-only session, 60 s statement
#              timeout) and every R check over the current public release
#              files (SIG_BASELINE_RELEASE_PREFIX, fetched read-only and
#              bounded). The sig.quality-baseline/1 record lands under
#              ops/probes/quality-baseline/; the leg prints the counts
#              summary to commit under docs/build/reports/quality/ and the
#              `sig-exports quality apply-baselines` follow-up.
#   verify     poststate capture + `sig-ops quality job verify-describe` /
#              `verify-trigger` against the recorded describes. READ-ONLY.
#   rollback   pause, then delete the trigger and the job by EXACT NAME
#              (name-checked); remove the leg's IAM bindings. Deliberately
#              NOT window-gated — restoring prestate is always safe. Probe
#              records stay: they are history.
#   all        prestate → deps → job → trigger → alerts-binding → verify.
#
# Live window (OM-19, the contract's AR-3 + AR-2 slot): applies run ≥
# ${SIG_QUALITY_EARLIEST}, never 03:00–06:30Z, and never inside the monthly
# batch window (day 6 00:00Z → day 13 12:00Z — the ingest batch owns those
# nights; the leg does not mutate then either). Every refusal exits 42 —
# queued; the RETURN PASS re-run prompt is printed. SIG_QUALITY_NOW
# overrides the clock for the offline guard test only.
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
      [ $# -ge 2 ] || { echo "quality-probe.sh: --from-state needs a directory" >&2; exit 64; }
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
STATE_DIR="${2:-${SIG_QUALITY_STATE_DIR}}"

_repo="$(cd "${_here}/../.." && pwd)"

RERUN='implement-spec spec=docs/tickets/256_P34.44b__quality-baseline-run-and-nightly-probe.md live_verification=true'

_sigops() {
  (cd "${_repo}" && uv run --quiet sig-ops "$@")
}

_sa_email() { printf '%s@%s.iam.gserviceaccount.com' "$1" "${SIG_GCP_PROJECT}"; }

_sha256() {
  if command -v sha256sum >/dev/null 2>&1; then sha256sum "$1" | awk '{print $1}';
  else shasum -a 256 "$1" | awk '{print $1}'; fi
}

# `assert_window` — the OM-19/AR-3 clock guard. Check mode is never gated — a
# printed plan mutates nothing. Every refusal prints the re-run prompt and
# exits 42 (queued).
assert_window() {
  [ "${SIG_GCP_MODE}" = "apply" ] || return 0
  local now hhmm dom
  now="${SIG_QUALITY_NOW:-$(date -u +%Y-%m-%dT%H:%M:%SZ)}"
  if [[ "${now}" < "${SIG_QUALITY_EARLIEST}" ]]; then
    _log "QUEUED (exit 42): now=${now} < ${SIG_QUALITY_EARLIEST} — the AR-3/AR-2 freeze."
    _log "re-run: ${RERUN} (scope: the baseline run and job creation leg)"
    exit 42
  fi
  hhmm="${now:11:5}"
  if [[ "${hhmm}" > "02:59" && "${hhmm}" < "06:30" ]]; then
    _log "QUEUED (exit 42): ${now} is inside 03:00–06:30Z — never mutate then."
    _log "re-run: ${RERUN} (scope: the baseline run and job creation leg)"
    exit 42
  fi
  dom="${now:8:2}"
  if [[ "${dom}" > "05" && "${dom}" < "14" ]]; then
    if [[ "${dom}" < "13" || "${hhmm}" < "12:00" ]]; then
      _log "QUEUED (exit 42): ${now} is inside the monthly batch window (day 6 00:00Z → day 13 12:00Z)."
      _log "re-run: ${RERUN} (scope: the baseline run and job creation leg)"
      exit 42
    fi
  fi
  _log "window OK: ${now} (≥ ${SIG_QUALITY_EARLIEST}, outside 03:00–06:30Z, outside the batch window)"
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
  if ! gcloud sql users list --instance "${SIG_SQL_INSTANCE}" \
      --project "${SIG_GCP_PROJECT}" --format='value(name)' 2>/dev/null \
      | grep -qx "${SIG_DB_ROLE_AUDIT}"; then
    _log "  missing live edge: the ${SIG_DB_ROLE_AUDIT} login — created by live:P34.43 (db-logins.sh)"
    missing=1
  fi
  local s
  for s in ${SIG_SECRET_AUDIT_PASSWORD} ${SIG_SECRET_ALERT_HOOK}; do
    if ! gcloud secrets describe "${s}" --project "${SIG_GCP_PROJECT}" >/dev/null 2>&1; then
      _log "  missing live edge: secret ${s} does not exist yet"
      missing=1
    fi
  done
  if [ "${missing}" -gt 0 ]; then
    _log "QUEUED (exit 42): a live edge has not landed — see above."
    _log "re-run: ${RERUN} (scope: the baseline run and job creation leg)"
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
  # AR-2's bucket clause: versioning on the restricted bucket BEFORE the
  # first probe record is written — recorded for the gate.
  gcloud storage buckets describe "gs://${SIG_BUCKET_RESTRICTED}" \
    --format='value(versioning.enabled)' > "${dir}/bucket-versioning.txt" \
    || printf 'unknown\n' > "${dir}/bucket-versioning.txt"
  gcloud storage buckets get-iam-policy "gs://${SIG_BUCKET_RESTRICTED}" \
    --format json > "${dir}/bucket-iam.json" \
    || printf '{"bindings":[]}' > "${dir}/bucket-iam.json"
  _sigops quality job plan > "${dir}/quality-probe-decl.json"
  (cd "${dir}" && for f in *.json; do _sha256 "$f"; done) > "${dir}/sha256s.txt"
}

do_prestate() {
  _log "-- prestate ($(date -u +%FT%TZ)): the leg's restore point under ${STATE_DIR}/pre (read-only) --"
  if [ "${SIG_GCP_MODE}" = "check" ]; then
    _plan "gcloud run jobs list > pre/run-jobs.json"
    _plan "gcloud scheduler jobs list > pre/scheduler-jobs.json"
    _plan "gcloud storage buckets describe gs://${SIG_BUCKET_RESTRICTED} versioning > pre/bucket-versioning.txt  (AR-2's bucket clause)"
    _plan "gcloud storage buckets get-iam-policy gs://${SIG_BUCKET_RESTRICTED} > pre/bucket-iam.json"
    _plan "sig-ops quality job plan > pre/quality-probe-decl.json  (the rendered declaration)"
    _plan "sha256 sidecars over every capture > pre/sha256s.txt"
    return 0
  fi
  _capture "${STATE_DIR}/pre"
  local ver; ver="$(cat "${STATE_DIR}/pre/bucket-versioning.txt" 2>/dev/null || true)"
  if [ "${ver}" != "Enabled" ] && [ "${ver}" != "True" ] && [ "${ver}" != "true" ]; then
    _log "ERROR: versioning on gs://${SIG_BUCKET_RESTRICTED} reads '${ver}' — AR-2's bucket clause requires it ON before the first probe record. Refusing." >&2
    exit 4
  fi
  _log "   prestate recorded under ${STATE_DIR}/pre (date -u: $(date -u +%FT%TZ)); bucket versioning ${ver}"
}

do_deps() {
  _log "-- deps ($(date -u +%FT%TZ)): the live: edges (P34.42b's SA, P34.43's sig_audit, the two secrets) --"
  if [ "${SIG_GCP_MODE}" = "check" ]; then
    _plan "gcloud iam service-accounts describe $(_sa_email "${SIG_SA_QUALITY_PROBE}")   (live:P34.42b)"
    _plan "gcloud sql users list --instance ${SIG_SQL_INSTANCE} | grep ^${SIG_DB_ROLE_AUDIT}\$   (live:P34.43)"
    _plan "gcloud secrets describe ${SIG_SECRET_AUDIT_PASSWORD} + ${SIG_SECRET_ALERT_HOOK}"
    _plan "missing edge → exit 42 (queued), never a partial apply"
    return 0
  fi
  assert_deps
  _log "   deps OK — every live edge holds (date -u: $(date -u +%FT%TZ))"
}

do_job() {
  assert_window
  assert_deps
  _log "-- job ($(date -u +%FT%TZ)): deploy ${SIG_QUALITY_JOB} on ${SIG_SA_QUALITY_PROBE} --"
  local image="${SIG_QUALITY_IMAGE:-}"
  if [ -z "${image}" ]; then
    if [ "${SIG_GCP_MODE}" = "check" ]; then
      image="${SIG_API_IMAGE}:quality-probe"   # placeholder — printed, never resolved
    else
      _log "ERROR: SIG_QUALITY_IMAGE must name the workload image (a ${SIG_API_IMAGE}:<tag> — resolved to a digest, never :latest)." >&2
      exit 2
    fi
  fi
  image="$(pin_image_digest "${image}")"
  local conn="${SIG_GCP_PROJECT}:${SIG_GCP_REGION}:${SIG_SQL_INSTANCE}"
  local alerts_url="${SIG_ALERT_WEBHOOK_URL:-}"
  if [ "${SIG_GCP_MODE}" = "check" ] && [ -z "${alerts_url}" ]; then
    alerts_url="<url-of-${SIG_ALERTS_SERVICE}>"
  elif [ -z "${alerts_url}" ]; then
    alerts_url="$(gcloud run services describe "${SIG_ALERTS_SERVICE}" \
      --region "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}" \
      --format='value(status.url)')"
  fi
  # The rendered argv — the declaration drives every flag. Each argv
  # element is emitted on its own line (the declaration refuses elements
  # carrying commas/newlines), so the array expansion is exact — `--args`
  # keeps its space-bearing `sh -c` string as ONE element.
  local rendered
  rendered="$(_sigops quality job render \
    --image "${image}" \
    --project "${SIG_GCP_PROJECT}" --region "${SIG_GCP_REGION}" \
    --env "SIG_GCP_PROJECT=${SIG_GCP_PROJECT}" \
    --env "SIG_OPS_GCS_BUCKET=${SIG_BUCKET_RESTRICTED}" \
    --env "SIG_CLOUDSQL_CONNECTION=${conn}" \
    --env "SIG_PG_DB=${SIG_PG_DB_NAME:-sig}" \
    --env "SIG_QUALITY_PROBE_PREFIX=${SIG_QUALITY_PREFIX}" \
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
  _log "   rollback: gcloud run jobs delete ${SIG_QUALITY_JOB} --quiet (name-checked)"
}

do_trigger() {
  assert_window
  assert_deps
  _log "-- trigger ($(date -u +%FT%TZ)): ${SIG_QUALITY_SCHED} → ${SIG_QUALITY_JOB} --"
  local uri="https://${SIG_GCP_REGION}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${SIG_GCP_PROJECT}/jobs/${SIG_QUALITY_JOB}:run"
  local sched_sa; sched_sa="$(_sa_email "${SIG_SA_SCHEDULER}")"
  local schedule
  schedule="$(_sigops quality job plan | python3 -c 'import json,sys; print(json.load(sys.stdin)["scheduler"]["schedule"])')"
  if [ "${SIG_GCP_MODE}" = "check" ]; then
    _plan "gcloud scheduler jobs create http ${SIG_QUALITY_SCHED} --schedule '${schedule}' --time-zone=Etc/UTC --uri ${uri} --http-method=POST --oauth-service-account-email=${sched_sa}   # (update if already present)"
    return 0
  fi
  if gcloud scheduler jobs describe "${SIG_QUALITY_SCHED}" \
      --location "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}" >/dev/null 2>&1; then
    run gcloud scheduler jobs update http "${SIG_QUALITY_SCHED}" \
      --location "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}" \
      --schedule "${schedule}" --time-zone=Etc/UTC --uri "${uri}" \
      --http-method=POST --oauth-service-account-email="${sched_sa}"
  else
    run gcloud scheduler jobs create http "${SIG_QUALITY_SCHED}" \
      --location "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}" \
      --schedule "${schedule}" --time-zone=Etc/UTC --uri "${uri}" \
      --http-method=POST --oauth-service-account-email="${sched_sa}"
  fi
  _log "   rollback: gcloud scheduler jobs pause + delete ${SIG_QUALITY_SCHED} (name-checked)"
}

do_alerts_binding() {
  assert_window
  assert_deps
  _log "-- alerts-binding ($(date -u +%FT%TZ)): the declared alert-path grants for ${SIG_SA_QUALITY_PROBE} --"
  # Both are declared end-state in ops/iam_identities.toml (the sig-alerts
  # `leg = "jobs"` invoker rule + the sig-alert-webhook-token consumer) —
  # idempotent grants here keep the job alerting even when the jobs leg has
  # not re-run since this row landed.
  run gcloud run services add-iam-policy-binding "${SIG_ALERTS_SERVICE}" \
    --region "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}" \
    --member="serviceAccount:$(_sa_email "${SIG_SA_QUALITY_PROBE}")" \
    --role=roles/run.invoker
  run gcloud secrets add-iam-policy-binding "${SIG_SECRET_ALERT_HOOK}" \
    --project "${SIG_GCP_PROJECT}" \
    --member="serviceAccount:$(_sa_email "${SIG_SA_QUALITY_PROBE}")" \
    --role=roles/secretmanager.secretAccessor
  _log "   rollback: the two remove-iam-policy-binding calls (name-checked members)"
}

do_baseline() {
  assert_window
  assert_deps
  _log "-- baseline ($(date -u +%FT%TZ)): the read-only L2 baseline run over the exec host --"
  if [ -z "${SIG_BASELINE_RELEASE_PREFIX}" ]; then
    _log "ERROR: SIG_BASELINE_RELEASE_PREFIX must name the current public release's objects (gs://<bucket>/<prefix>/) — the R placement scans those files." >&2
    exit 2
  fi
  local image="${SIG_QUALITY_IMAGE:-}"
  if [ -z "${image}" ]; then
    if [ "${SIG_GCP_MODE}" = "check" ]; then
      image="${SIG_API_IMAGE}:quality-baseline"   # placeholder — printed, never resolved
    else
      _log "ERROR: SIG_QUALITY_IMAGE must name the workload image (a ${SIG_API_IMAGE}:<tag> — resolved to a digest, never :latest)." >&2
      exit 2
    fi
  fi
  image="$(pin_image_digest "${image}")"
  local conn="${SIG_GCP_PROJECT}:${SIG_GCP_REGION}:${SIG_SQL_INSTANCE}"
  if [ "${SIG_GCP_MODE}" = "check" ]; then
    _sigops exec-host render --purpose quality-baseline --image "${image}" \
      --project "${SIG_GCP_PROJECT}" --region "${SIG_GCP_REGION}" \
      --secret-env SIG_AUDIT_PASSWORD \
      --env "SIG_EXEC_BUCKET=${SIG_EXEC_BUCKET}" \
      --env "SIG_CLOUDSQL_CONNECTION=${conn}" \
      --env "SIG_PG_DB=${SIG_PG_DB_NAME:-sig}" \
      --env "SIG_BASELINE_RELEASE_PREFIX=${SIG_BASELINE_RELEASE_PREFIX:-<gs://…/release>}" \
      --env "SIG_OPS_GCS_BUCKET=${SIG_BUCKET_RESTRICTED}" \
      --arg=-c --arg "exec sig-ops quality baseline --emit"
    return 0
  fi
  mkdir -p "${STATE_DIR}"
  local logf="${STATE_DIR}/baseline-$(date -u +%Y%m%dT%H%M%SZ).log"
  _log "   running sig-exec-quality-baseline-<stamp> (log → ${logf})"
  if ! _sigops exec-host run --purpose quality-baseline --image "${image}" \
      --project "${SIG_GCP_PROJECT}" --region "${SIG_GCP_REGION}" \
      --secret-env SIG_AUDIT_PASSWORD \
      --env "SIG_EXEC_BUCKET=${SIG_EXEC_BUCKET}" \
      --env "SIG_CLOUDSQL_CONNECTION=${conn}" \
      --env "SIG_PG_DB=${SIG_PG_DB_NAME:-sig}" \
      --env "SIG_BASELINE_RELEASE_PREFIX=${SIG_BASELINE_RELEASE_PREFIX}" \
      --env "SIG_OPS_GCS_BUCKET=${SIG_BUCKET_RESTRICTED}" \
      --arg=-c --arg "exec sig-ops quality baseline --emit" \
      >"${logf}" 2>&1; then
    _log "ERROR: the baseline run failed — ${logf} has the output; the cleanup still ran (name-checked delete)." >&2
    exit 4
  fi
  _log "   baseline OK — the sig.quality-baseline/1 record landed under ${SIG_BASELINE_PREFIX}"
  _log "   follow-up: commit the counts summary under docs/build/reports/quality/ (date -u),"
  _log "   then: sig-exports quality apply-baselines --report <record> --date \$(date -u +%F) --write"
}

do_verify() {
  _log "-- verify: poststate capture → verify-describe + verify-trigger against the declaration --"
  if [ "${SIG_GCP_MODE}" = "check" ]; then
    _plan "re-capture under ${STATE_DIR}/post (same reads as prestate)"
    _plan "gcloud run jobs describe ${SIG_QUALITY_JOB} --format json > post/job.json"
    _plan "gcloud scheduler jobs describe ${SIG_QUALITY_SCHED} --format json > post/trigger.json"
    _plan "sig-ops quality job verify-describe --describe post/job.json      (the job posture)"
    _plan "sig-ops quality job verify-trigger --describe post/trigger.json   (the trigger posture)"
    return 0
  fi
  if [ -n "${FROM_STATE}" ]; then
    _sigops quality job verify-describe --describe "${FROM_STATE}/job.json" \
      --project "${SIG_GCP_PROJECT}"
    _sigops quality job verify-trigger --describe "${FROM_STATE}/trigger.json" \
      --project "${SIG_GCP_PROJECT}" --region "${SIG_GCP_REGION}"
    return 0
  fi
  _capture "${STATE_DIR}/post"
  gcloud run jobs describe "${SIG_QUALITY_JOB}" --region "${SIG_GCP_REGION}" \
    --project "${SIG_GCP_PROJECT}" --format json > "${STATE_DIR}/post/job.json"
  gcloud scheduler jobs describe "${SIG_QUALITY_SCHED}" --location "${SIG_GCP_REGION}" \
    --project "${SIG_GCP_PROJECT}" --format json > "${STATE_DIR}/post/trigger.json"
  _sigops quality job verify-describe --describe "${STATE_DIR}/post/job.json" \
    --project "${SIG_GCP_PROJECT}"
  _sigops quality job verify-trigger --describe "${STATE_DIR}/post/trigger.json" \
    --project "${SIG_GCP_PROJECT}" --region "${SIG_GCP_REGION}"
  _log "verify OK — job + trigger match the declaration."
}

do_rollback() {
  _log "-- rollback ($(date -u +%FT%TZ)): pause trigger → delete trigger → delete job (name-checked) --"
  if [ "${SIG_GCP_MODE}" = "check" ]; then
    _plan "gcloud scheduler jobs pause ${SIG_QUALITY_SCHED}"
    _plan "gcloud scheduler jobs delete ${SIG_QUALITY_SCHED} --quiet"
    _plan "gcloud run jobs remove-iam-policy-binding ${SIG_QUALITY_JOB} --member sig-scheduler"
    _plan "gcloud run jobs delete ${SIG_QUALITY_JOB} --quiet"
    _plan "remove the leg's alert-path bindings (sig-alerts invoker + webhook-token accessor)"
    _plan "probe records under ops/probes/ STAY — they are history"
    return 0
  fi
  # Name-checked unwind — exactly the names the declaration carries.
  gcloud scheduler jobs pause "${SIG_QUALITY_SCHED}" \
    --location "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}" || true
  _log "   paused ${SIG_QUALITY_SCHED}"
  gcloud scheduler jobs delete "${SIG_QUALITY_SCHED}" \
    --location "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}" --quiet || true
  _log "   deleted ${SIG_QUALITY_SCHED}"
  gcloud run jobs remove-iam-policy-binding "${SIG_QUALITY_JOB}" \
    --region "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}" \
    --member="serviceAccount:$(_sa_email "${SIG_SA_SCHEDULER}")" \
    --role=roles/run.invoker || true
  gcloud run jobs delete "${SIG_QUALITY_JOB}" \
    --region "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}" --quiet || true
  _log "   deleted ${SIG_QUALITY_JOB}"
  gcloud run services remove-iam-policy-binding "${SIG_ALERTS_SERVICE}" \
    --region "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}" \
    --member="serviceAccount:$(_sa_email "${SIG_SA_QUALITY_PROBE}")" \
    --role=roles/run.invoker || true
  gcloud secrets remove-iam-policy-binding "${SIG_SECRET_ALERT_HOOK}" \
    --project "${SIG_GCP_PROJECT}" \
    --member="serviceAccount:$(_sa_email "${SIG_SA_QUALITY_PROBE}")" \
    --role=roles/secretmanager.secretAccessor || true
  _log "rollback applied — trigger + job deleted by name; probe records kept (they are history)."
}

# Every non-check path (live verify included — member names embed the project
# id) requires SIG_GCP_PROJECT; check mode tolerates the placeholder.
require_project
# The clock guard precedes the ADC gate so a queued apply exits 42 cleanly.
# `deps` is read-only (it names which live edge is missing) — never gated.
case "${ACTION}" in
  job|trigger|alerts-binding|baseline|all) assert_window ;;
esac
# A live verify reads with ADC; an offline --from-state diff needs none.
if [ -z "${FROM_STATE}" ] && [ "${SIG_GCP_MODE}" != "check" ]; then
  require_adc
fi

banner "P34.44b — the nightly sig-quality-probe job + the L2 baseline leg (SIG-CONF-006/007)"

case "${ACTION}" in
  prestate)       do_prestate ;;
  deps)           do_deps ;;
  job)            do_job ;;
  trigger)        do_trigger ;;
  alerts-binding) do_alerts_binding ;;
  baseline)       do_baseline ;;
  verify)         do_verify ;;
  rollback)       do_rollback ;;
  all)
    do_prestate
    do_deps
    do_job
    do_trigger
    do_alerts_binding
    do_verify
    ;;
  *) echo "quality-probe.sh: unknown action ${ACTION} (prestate|deps|job|trigger|alerts-binding|baseline|verify|rollback|all)" >&2; exit 64 ;;
esac

if [ "${SIG_GCP_MODE}" = "check" ]; then
  _log "quality-probe ${ACTION}: check OK (mode=${SIG_GCP_MODE})"
else
  _log "-- done (${ACTION}, mode ${SIG_GCP_MODE})"
fi
