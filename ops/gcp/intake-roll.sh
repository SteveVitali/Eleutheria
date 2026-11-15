#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
#
# ops/gcp/intake-roll.sh — P37.59 (row 487, G2-activation step 6 / ACT-23,
# D-P32.16-1): the ticket's ONE named mutation (OM-14) — **the dark
# intake-service deploy (receiver not operating; loopback only, no
# exposure)**. OM-20: pre-authorised — GATE-G6 §4's verbatim-approved list
# names this row ("Approve all 15 (rec.)", 2026-11-05T15:20Z; expiry at the
# round-11 acceptance sitting). This script is staged
# `prepared_not_executed`: the engineering dispatch is
# `live_verification=false` — the apply path runs only under the re-run
# prompt below, inside `dark service only; AR-3 + AR-2`.
#
# The dark deploy (Q-27/OD-08 [B-8] 'Email, no time promises' — intake is
# e-mail-only and dark; the live exposure leg is NOT this row's):
#
#   gcloud run deploy sig-intake \
#     --image <sig-api's serving digest> \
#     --service-account sig-intake-rt@<p>.iam.gserviceaccount.com \
#     --no-allow-unauthenticated --ingress internal \
#     --min-instances 0 --max-instances 2 --port 8080 \
#     --set-env-vars SIG_INTAKE_ENABLED=1,SIG_PG_DB=sig,SIG_CLOUDSQL_CONNECTION=<conn> \
#     --set-secrets SIG_INTAKE_DB_PASSWORD=sig-intake-receiver-password:latest,\
#                  SIG_INTAKE_FORM_SECRET=sig-intake-form-secret:latest,\
#                  SIG_INTAKE_ABUSE_SECRET=sig-intake-abuse-secret:latest \
#     --set-cloudsql-instances <conn> \
#     --command sh --args -c --args "<serve-intake shell>"
#
#   SIG_INTAKE_ENABLED=1 mounts the surface so the service answers the
#   honest `503 receiver_not_operating`; SIG_INTAKE_OPERATIONAL is NEVER
#   set — accepting reports stays the exposure path's flip, gated on
#   [intake].operational + owner + staffed (all operator acts,
#   D-P32.16-1). `--no-allow-unauthenticated` + `internal` ingress admit
#   only GCP-internal paths; the /intake/* URL-map rule in
#   ops/lb_routes.toml stays `enabled = false` — nothing external can
#   reach the service. The image is the serving `sig-api` revision's own
#   digest, read back in prestate (the receiver is the same image —
#   ops/Dockerfile; deploy-by-digest, ADR-111).
#
# Actions:
#   prestate   describe sig-intake (absent = the create's restore point),
#              sig-api's serving image digest, the _Default sink's
#              exclusions → ${STATE_DIR}/pre. READ-ONLY.
#   sa         create sig-intake-rt (idempotent) + its declared bindings:
#              roles/cloudsql.client + secretAccessor on the two
#              service-mounted gate secrets + the receiver password.
#   secrets    assert the three declared Secret Manager names exist —
#              a missing one QUEUES the leg (exit 42): provisioning is the
#              operator's act (D-P32.16-1), never a partial shape.
#   log-exclusions  `gcloud logging sinks update _Default --add-exclusion
#              name=sig-intake-request-logs,filter=<requests-stream>` — drops
#              only the receiver's Cloud Run *request* logs (IP+UA carriers);
#              app stdout/stderr stays logged. Idempotent.
#   deploy     the mutation above (queues via `secrets` when a declared
#              input is absent).
#   poststate  describe the created service → ${STATE_DIR}/post.
#   verify     read-only: describe sig-intake + its IAM policy + the
#              _Default exclusions; assert the declared dark shape
#              (no allUsers invoker, SIG_INTAKE_ENABLED=1, no
#              SIG_INTAKE_OPERATIONAL, internal ingress, sig-intake-rt).
#   rollback   `gcloud run services delete sig-intake` +
#              `sinks update _Default --remove-exclusion` (the create's
#              restore point; the SA and secrets stay — additive, never a
#              posture).
#   all        prestate → sa → secrets → log-exclusions → deploy → poststate.
#
# Usage:
#   ops/gcp/intake-roll.sh [--check|--dry-run] [ACTION]   # plan only (default)
#   ops/gcp/intake-roll.sh --apply [ACTION]               # the mutation(s)
#   ops/gcp/intake-roll.sh --verify                       # read-only
#
# Env: SIG_GCP_PROJECT + ADC (apply/verify); SIG_INTAKE_AUTHOR (the recorded
#   operator id — OM-20 scope discipline, required per apply);
#   SIG_INTAKE_STATE_DIR; SIG_INTAKE_NOW (test-only clock seam).
#
# Exit: 0 ok · 2 usage/env · 3 unarmed/no-ADC · 4 verify drift · 42 QUEUED.
#
# Re-run prompt (OM-19): the deploy is create-once + idempotent — a resumed
# run converges to the declared posture.
#   implement-spec spec=docs/tickets/487_P37.59__intake-operation-dark.md live_verification=true
set -euo pipefail

_here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=config.sh
. "${_here}/config.sh"
# shellcheck source=lib.sh
. "${_here}/lib.sh"

RERUN="implement-spec spec=docs/tickets/487_P37.59__intake-operation-dark.md live_verification=true"
STATE_DIR="${SIG_INTAKE_STATE_DIR:-${TMPDIR:-/tmp}/p37.59-intake}"
EXCL_NAME="sig-intake-request-logs"
EXCL_FILTER='resource.type="cloud_run_revision" AND resource.labels.service_name="sig-intake" AND log_id("run.googleapis.com/requests")'

_usage() {
  sed -n '/^# Usage:/,/^# Env:/p' "$0" | sed 's/^# \{0,1\}//'
  exit "${1:-64}"
}

MODE="check"; ACTION="all"; FROM_STATE=""
case "${1:-}" in
  --apply)  MODE="apply"; ACTION="${2:-all}"; FROM_STATE="${4:-}" ;;
  --verify) MODE="verify"; ACTION="verify"; FROM_STATE="${3:-}" ;;
  --check|--dry-run|"") MODE="check"; ACTION="${2:-all}" ;;
  -h|--help) _usage 0 ;;
  *) echo "intake-roll.sh: unknown mode '${1:-}'" >&2; _usage 64 ;;
esac
export SIG_GCP_MODE="${MODE}"
# Verify is read-only by contract: only the verify leg may run under it.
[ "${MODE}" = "verify" ] && ACTION="verify"

require_project
# The project-resolved names — computed only AFTER require_project so the
# check-mode placeholder renders in the plan too.
CONN="${SIG_GCP_PROJECT}:${SIG_GCP_REGION}:${SIG_SQL_INSTANCE}"
SIG_INTAKE_SA_EMAIL="${SIG_INTAKE_SA}@${SIG_GCP_PROJECT}.iam.gserviceaccount.com"
SECRET_ENV="SIG_INTAKE_DB_PASSWORD=${SIG_SECRET_INTAKE_RECEIVER_PASSWORD}:latest,SIG_INTAKE_FORM_SECRET=${SIG_SECRET_INTAKE_FORM}:latest,SIG_INTAKE_ABUSE_SECRET=${SIG_SECRET_INTAKE_ABUSE}:latest"
ENV_VARS="SIG_INTAKE_ENABLED=1,SIG_PG_DB=${SIG_PG_DB_NAME:-sig},SIG_CLOUDSQL_CONNECTION=${CONN}"
EVIDENCE_DIR="${STATE_DIR}/$(date -u +%Y%m%dT%H%M%SZ)"

die() { _log "ERROR: $*" >&2; exit "${2:-4}"; }
_queued() {
  _log "QUEUED (exit 42): $*" >&2
  _log "re-run: ${RERUN}" >&2
  exit 42
}
_sha256() {
  if command -v sha256sum >/dev/null 2>&1; then sha256sum "$1" | awk '{print $1}'
  else shasum -a 256 "$1" | awk '{print $1}'; fi
}
_capture() {  # _capture <rel> <cmd...> — read-only JSON + sha256 sidecar
  local out="${EVIDENCE_DIR}/$1"; shift
  mkdir -p "$(dirname "${out}")"
  _log "+ (capture) $* > ${out}"
  if ! "$@" > "${out}" 2> "${out}.err"; then
    _log "   capture failed (recorded): $*"
    return 0
  fi
  printf '%s  %s\n' "$(_sha256 "${out}")" "${out}" >> "${EVIDENCE_DIR}/sha256s.txt"
}

_now() { printf '%s' "${SIG_INTAKE_NOW:-$(date -u +%Y-%m-%dT%H:%M:%SZ)}"; }

# AR-3 batch windows (the same declared windows the other legs carry).
AR3_WINDOWS="2026-10-06T00:00:00Z 2026-10-13T12:00:00Z"
AR3_WINDOWS="$AR3_WINDOWS
2026-11-06T00:00:00Z 2026-11-13T12:00:00Z"  # future-ok: scheduled: the November AR-3 batch window the deploy stays outside of
AR3_WINDOWS="$AR3_WINDOWS
2026-12-06T00:00:00Z 2026-12-13T12:00:00Z"  # future-ok: scheduled: the December AR-3 batch window the deploy stays outside of

_epoch() {
  local ts="$1"
  if date -u -j -f '%Y-%m-%dT%H:%M:%SZ' "$ts" +%s >/dev/null 2>&1; then
    date -u -j -f '%Y-%m-%dT%H:%M:%SZ' "$ts" +%s            # macOS
  else
    date -u -d "$ts" +%s                                  # GNU
  fi
}

_in_daily_freeze() {
  local hh mm
  hh="$(printf '%s' "$1" | sed 's/.*T//; s/:.*//')"
  mm="$(printf '%s' "$1" | sed 's/.*T[0-9]*://; s/:.*//')"
  [ "$hh" -gt 3 ] || { [ "$hh" -eq 3 ] && [ "$mm" -ge 0 ]; } || return 1
  { [ "$hh" -lt 6 ] || { [ "$hh" -eq 6 ] && [ "$mm" -lt 30 ]; }; }
}

_in_ar3() {
  local now_e; now_e="$(_epoch "$1")"
  printf '%s\n' "$AR3_WINDOWS" | while read -r start stop; do
    [ -n "${start:-}" ] || continue
    if [ "$(_epoch "$start")" -le "$now_e" ] && [ "$now_e" -lt "$(_epoch "$stop")" ]; then
      echo "inside $start..$stop"
    fi
  done | grep -q '^inside'
}

# `assert_window` — `dark service only; AR-3 + AR-2`: never inside the daily
# 03:00–06:30Z freeze, never inside an AR-3 batch window; the prestate
# describe is the recorded restore point (AR-2's form for a create — the
# rollback is the delete).
assert_window() {
  [ "${SIG_GCP_MODE}" = "apply" ] || return 0
  local now
  now="$(_now)"
  if _in_daily_freeze "$now"; then
    _queued "inside the 03:00-06:30Z AR-3 freeze ($now)"
  fi
  if _in_ar3 "$now"; then
    _queued "inside an AR-3 batch window ($now)"
  fi
  _log "window OK: $(_now) (outside 03:00-06:30Z + the AR-3 batch windows)"
}

# `assert_author` — OM-20 scope discipline: the apply records the operator
# id even under the GATE-G6 §4 pre-authorisation; silence is never consent.
assert_author() {
  [ "${SIG_GCP_MODE}" = "apply" ] || return 0
  if [ -z "${SIG_INTAKE_AUTHOR:-}" ]; then
    _queued "SIG_INTAKE_AUTHOR is unset — the recorded operator id for this leg"
  fi
  _log "author: ${SIG_INTAKE_AUTHOR} (recorded — GATE-G6 §4 'Approve all 15 (rec.)')"
}

_service_image() {  # apply/verify only — the serving sig-api image ref
  gcloud run services describe "${SIG_RUN_SERVICE}" \
    --project "${SIG_GCP_PROJECT}" --region "${SIG_GCP_REGION}" \
    --format='value(spec.template.spec.containers[0].image)' 2>/dev/null || true
}

_describe_intake() {  # "" when absent
  gcloud run services describe "${SIG_INTAKE_SERVICE}" \
    --project "${SIG_GCP_PROJECT}" --region "${SIG_GCP_REGION}" \
    --format json 2>/dev/null || true
}

_secret_exists() {  # $1 = secret name
  gcloud secrets describe "$1" --project "${SIG_GCP_PROJECT}" \
    >/dev/null 2>&1
}

# ---------------------------------------------------------------------------
leg_prestate() {
  banner "prestate — the AR-2 restore point (absent service = create-only)"
  if [ "${SIG_GCP_MODE}" = "check" ]; then
    _plan "gcloud run services describe ${SIG_INTAKE_SERVICE} → pre/service.json (absent = the create's restore point)"
    _plan "gcloud run services describe ${SIG_RUN_SERVICE} → pre/sig-api.json (the deploy's image source — its serving digest)"
    _plan "gcloud logging sinks describe _Default → pre/default-sink.json (the exclusions snapshot)"
    return 0
  fi
  _capture "pre/sig-intake.json" _describe_intake
  _capture "pre/sig-api.json" \
    gcloud run services describe "${SIG_RUN_SERVICE}" \
      --project "${SIG_GCP_PROJECT}" --region "${SIG_GCP_REGION}" --format json
  _capture "pre/default-sink.json" \
    gcloud logging sinks describe _Default --project "${SIG_GCP_PROJECT}" --format json
}

leg_sa() {
  banner "sa — the dedicated least-privilege runtime identity (AR-8)"
  assert_window; assert_author
  if [ "${SIG_GCP_MODE}" = "check" ]; then
    _plan "gcloud iam service-accounts create ${SIG_INTAKE_SA}   (idempotent — skips when present)"
    _plan "gcloud projects add-iam-policy-binding ${SIG_GCP_PROJECT} --member serviceAccount:${SIG_INTAKE_SA_EMAIL} --role roles/cloudsql.client"
    for sec in "${SIG_SECRET_INTAKE_FORM}" "${SIG_SECRET_INTAKE_ABUSE}" "${SIG_SECRET_INTAKE_RECEIVER_PASSWORD}"; do
      _plan "gcloud secrets add-iam-policy-binding ${sec} --member serviceAccount:${SIG_INTAKE_SA_EMAIL} --role roles/secretmanager.secretAccessor   (only when the secret exists — pending until provisioned)"
    done
    return 0
  fi
  if ! gcloud iam service-accounts describe "${SIG_INTAKE_SA_EMAIL}" \
      --project "${SIG_GCP_PROJECT}" >/dev/null 2>&1; then
    run gcloud iam service-accounts create "${SIG_INTAKE_SA}" \
      --display-name "sig intake receiver runtime" \
      --project "${SIG_GCP_PROJECT}"
  else
    _log "   ${SIG_INTAKE_SA} exists (idempotent, +0)"
  fi
  run gcloud projects add-iam-policy-binding "${SIG_GCP_PROJECT}" \
    --member "serviceAccount:${SIG_INTAKE_SA_EMAIL}" \
    --role "roles/cloudsql.client"
  for sec in "${SIG_SECRET_INTAKE_FORM}" "${SIG_SECRET_INTAKE_ABUSE}" "${SIG_SECRET_INTAKE_RECEIVER_PASSWORD}"; do
    if _secret_exists "${sec}"; then
      run gcloud secrets add-iam-policy-binding "${sec}" \
        --project "${SIG_GCP_PROJECT}" \
        --member "serviceAccount:${SIG_INTAKE_SA_EMAIL}" \
        --role "roles/secretmanager.secretAccessor"
    else
      _log "   ${sec}: absent — accessor binding recorded pending (the operator's provisioning act, D-P32.16-1)"
    fi
  done
}

leg_secrets() {
  banner "secrets — the declared Secret Manager inputs (names only, HG-09)"
  local missing=()
  if [ "${SIG_GCP_MODE}" = "check" ]; then
    for sec in "${SIG_SECRET_INTAKE_RECEIVER_PASSWORD}" "${SIG_SECRET_INTAKE_FORM}" "${SIG_SECRET_INTAKE_ABUSE}"; do
      _plan "gcloud secrets describe ${sec}  → exists? (absent → QUEUED, never a partial shape)"
    done
    return 0
  fi
  for sec in "${SIG_SECRET_INTAKE_RECEIVER_PASSWORD}" "${SIG_SECRET_INTAKE_FORM}" "${SIG_SECRET_INTAKE_ABUSE}"; do
    if _secret_exists "${sec}"; then
      _log "   ${sec}: present"
    else
      missing+=("${sec}")
      _log "   ${sec}: ABSENT — the operator's provisioning act (D-P32.16-1)"
    fi
  done
  if [ "${#missing[@]}" -gt 0 ]; then
    _queued "declared secret(s) absent: ${missing[*]} — provision first (stdin version-add, never a file), then re-run"
  fi
}

leg_log_exclusions() {
  banner "log-exclusions — the _Default-sink request-log exclusion (G1 NEW-4)"
  assert_window; assert_author
  if [ "${SIG_GCP_MODE}" = "check" ]; then
    _plan "gcloud logging sinks update _Default --add-exclusion name=${EXCL_NAME},filter='${EXCL_FILTER}'"
    _plan "   (drops ONLY the receiver's Cloud Run request logs — the IP+UA stream; app stdout/stderr stays)"
    _plan "posture: ${SIG_LB_INTAKE_BACKEND} logConfig stays OFF — the backend exists only when the /intake/* rule flips (never this row)"
    return 0
  fi
  # Idempotent: check the sink's current exclusions first.
  local have
  have="$(gcloud logging sinks describe _Default --project "${SIG_GCP_PROJECT}" \
    --format='value(exclusions.map(key).list())' 2>/dev/null || true)"
  case "${have}" in
    *"${EXCL_NAME}"*) _log "   exclusion ${EXCL_NAME} already on _Default (idempotent, +0)" ;;
    *) run gcloud logging sinks update _Default \
        --project "${SIG_GCP_PROJECT}" \
        --add-exclusion "name=${EXCL_NAME},filter=${EXCL_FILTER}" ;;
  esac
  # The declared off posture: if a sig-intake-backend ever exists its log
  # config must be off — refuse (never silently fix) a live one that is on.
  local lblog
  lblog="$(gcloud compute backend-services describe "${SIG_LB_INTAKE_BACKEND}" \
    --global --project "${SIG_GCP_PROJECT}" \
    --format='value(logConfig.enable)' 2>/dev/null || true)"
  case "${lblog}" in
    "")     _log "   ${SIG_LB_INTAKE_BACKEND}: absent (expected — the /intake/* rule is enabled=false)" ;;
    False|false) _log "   ${SIG_LB_INTAKE_BACKEND}: logConfig off (declared posture)" ;;
    *)      die "${SIG_LB_INTAKE_BACKEND} logConfig.enable='${lblog}' — the declared posture is OFF (OM-18 stop)" ;;
  esac
}

leg_deploy() {
  banner "deploy — the named mutation: the dark sig-intake service"
  assert_window; assert_author
  leg_secrets   # a missing declared input queues before any mutation
  if [ "${SIG_GCP_MODE}" = "check" ]; then
    _plan "image = sig-api's serving digest (read back in prestate — deploy-by-digest, ADR-111)"
    _plan "gcloud run deploy ${SIG_INTAKE_SERVICE} --image <digest> --service-account ${SIG_INTAKE_SA_EMAIL} \\"
    _plan "  --no-allow-unauthenticated --ingress internal --min-instances 0 --max-instances 2 --port 8080 \\"
    _plan "  --set-env-vars ${ENV_VARS} \\"
    _plan "  --set-secrets ${SECRET_ENV} \\"
    _plan "  --set-cloudsql-instances ${CONN} \\"
    _plan "  --command sh --args -c --args '<serve-intake shell over env>'"
    _plan "   (SIG_INTAKE_OPERATIONAL is never set — the receiver stays dark;"
    _plan "    the /intake/* URL-map rule stays enabled=false — no exposure)"
    return 0
  fi
  local image
  image="$(_service_image)"
  [ -n "${image}" ] || die "could not read sig-api's serving image — the deploy's image source is absent"
  # shellcheck disable=SC2016
  run gcloud run deploy "${SIG_INTAKE_SERVICE}" \
    --image "${image}" \
    --project "${SIG_GCP_PROJECT}" --region "${SIG_GCP_REGION}" \
    --service-account "${SIG_INTAKE_SA_EMAIL}" \
    --no-allow-unauthenticated --ingress internal \
    --min-instances 0 --max-instances 2 --port 8080 \
    --set-env-vars "${ENV_VARS}" \
    --set-secrets "${SECRET_ENV}" \
    --set-cloudsql-instances "${CONN}" \
    --command sh \
    --args -c \
    --args 'exec sig-api serve-intake --host 0.0.0.0 --port ${PORT:-8080} --dsn "postgresql://sig_intake_receiver_login:${SIG_INTAKE_DB_PASSWORD}@/${SIG_PG_DB}?host=/cloudsql/${SIG_CLOUDSQL_CONNECTION}" --ops-config /app/ops/config.toml'
}

leg_poststate() {
  banner "poststate — the created service's describe"
  if [ "${SIG_GCP_MODE}" = "check" ]; then
    _plan "gcloud run services describe ${SIG_INTAKE_SERVICE} → post/service.json + post/iam-policy.json"
    return 0
  fi
  _capture "post/sig-intake.json" _describe_intake
  _capture "post/iam-policy.json" \
    gcloud run services get-iam-policy "${SIG_INTAKE_SERVICE}" \
      --project "${SIG_GCP_PROJECT}" --region "${SIG_GCP_REGION}" --format json
  _capture "post/default-sink.json" \
    gcloud logging sinks describe _Default --project "${SIG_GCP_PROJECT}" --format json
}

leg_verify() {
  banner "verify — the declared dark shape vs live (read-only)"
  if [ "${SIG_GCP_MODE}" = "check" ]; then
    _plan "read-only: describe ${SIG_INTAKE_SERVICE} + get-iam-policy + sinks describe _Default"
    _plan "assert: no allUsers/allAuthenticatedUsers invoker · SIG_INTAKE_ENABLED=1 ·"
    _plan "        no SIG_INTAKE_OPERATIONAL env · ingress=internal · sa=sig-intake-rt ·"
    _plan "        exclusion ${EXCL_NAME} on _Default"
    return 0
  fi
  local doc
  doc="$(_describe_intake)"
  if [ -z "${doc}" ]; then
    _log "UNREAD: ${SIG_INTAKE_SERVICE} does not exist — the dark deploy is pending (never claimed)"
    _log "verify: not_evaluable"
    return 0
  fi
  local iam sink
  iam="$(gcloud run services get-iam-policy "${SIG_INTAKE_SERVICE}" \
    --project "${SIG_GCP_PROJECT}" --region "${SIG_GCP_REGION}" --format json 2>/dev/null || true)"
  sink="$(gcloud logging sinks describe _Default \
    --project "${SIG_GCP_PROJECT}" --format json 2>/dev/null || true)"
  SIG_VERIFY_DOC="${doc}" SIG_VERIFY_IAM="${iam}" SIG_VERIFY_SINK="${sink}" \
    python3 - "${EXCL_NAME}" <<'PY'
import json, os, sys
doc = json.loads(os.environ.get("SIG_VERIFY_DOC") or "{}")
iam = json.loads(os.environ.get("SIG_VERIFY_IAM") or "{}")
sink = json.loads(os.environ.get("SIG_VERIFY_SINK") or "{}")
excl_name = sys.argv[1]
tmpl = doc.get("spec", {}).get("template", {}).get("spec", {})
cont = (tmpl.get("containers") or [{}])[0]
env = {e.get("name"): e.get("value", e.get("valueSource", {})) for e in cont.get("env", [])}
problems = []
if doc.get("spec", {}).get("ingress") != "INGRESS_TRAFFIC_INTERNAL":
    problems.append(f"ingress={doc.get('spec', {}).get('ingress')} != internal")
for b in iam.get("bindings", []):
    if b.get("role") == "roles/run.invoker":
        pub = [m for m in b.get("members", []) if m.startswith("all")]
        if pub:
            problems.append(f"public invoker members {pub}")
if env.get("SIG_INTAKE_ENABLED") != "1":
    problems.append("SIG_INTAKE_ENABLED != 1")
if "SIG_INTAKE_OPERATIONAL" in env:
    problems.append("SIG_INTAKE_OPERATIONAL is set — the dark posture forbids it")
sa = tmpl.get("serviceAccountName", "")
if not sa.startswith("sig-intake-rt@"):
    problems.append(f"serviceAccountName={sa} != sig-intake-rt@…")
for name, label in (("SIG_INTAKE_DB_PASSWORD", "receiver credential"),
                    ("SIG_INTAKE_FORM_SECRET", "form secret"),
                    ("SIG_INTAKE_ABUSE_SECRET", "abuse secret")):
    if name not in env:
        problems.append(f"{name} ({label}) not mounted")
excl_names = [e.get("name") for e in sink.get("exclusions", [])]
if excl_name not in excl_names:
    problems.append(f"_Default exclusions {excl_names} lack {excl_name}")
for p in problems:
    print(f"DRIFT: {p}")
if not problems:
    print("verify: the declared dark shape holds")
sys.exit(4 if problems else 0)
PY
}

leg_rollback() {
  banner "rollback — the create's restore point (delete + remove-exclusion)"
  if [ "${SIG_GCP_MODE}" = "check" ]; then
    _plan "gcloud run services delete ${SIG_INTAKE_SERVICE} --quiet   (the create's restore point)"
    _plan "gcloud logging sinks update _Default --remove-exclusion name=${EXCL_NAME}"
    _plan "   (the SA + secrets + accessor bindings stay — additive, never a posture)"
    return 0
  fi
  run gcloud run services delete "${SIG_INTAKE_SERVICE}" \
    --project "${SIG_GCP_PROJECT}" --region "${SIG_GCP_REGION}" --quiet
  run gcloud logging sinks update _Default \
    --project "${SIG_GCP_PROJECT}" --remove-exclusion "name=${EXCL_NAME}"
}

run_all() {
  # `secrets` rides inside `deploy` — it is the deploy's own input gate (a
  # standalone `secrets` action exists for the operator's read).
  leg_prestate; leg_sa; leg_log_exclusions; leg_deploy; leg_poststate
}

# ---------------------------------------------------------------------------
banner "P37.59 — the dark sig-intake receiver (${ACTION}; mode=${MODE})"
case "${ACTION}" in
  prestate)        leg_prestate ;;
  sa)              leg_sa ;;
  secrets)         leg_secrets ;;
  log-exclusions)  leg_log_exclusions ;;
  deploy)          leg_deploy ;;
  poststate)       leg_poststate ;;
  verify)          leg_verify ;;
  rollback)        leg_rollback ;;
  all)             run_all ;;
  *) _usage 64 ;;
esac
_log "intake-roll ${ACTION}: check OK (mode=${SIG_GCP_MODE})"
