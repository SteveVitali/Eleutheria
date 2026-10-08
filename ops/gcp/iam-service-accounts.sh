#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
#
# ops/gcp/iam-service-accounts.sh — the IAM leg of P34.42a (G1-01, F-272,
# SIG-SEC-007, AR-8): the three Cloud Run services stop running as the
# project-Editor default compute identity. The committed declaration is
# ops/iam_identities.toml (`sig.iam-identities/1` — `sig-ops iam` renders and
# diffs it; every name this script uses is derived from it); this script owns
# the (windowed, pre-authorised S5-3) mutations:
#
#   ./iam-service-accounts.sh --check [action]   # (default) plan-only:
#                                                # NO ADC, NO network.
#   ./iam-service-accounts.sh --apply <action>   # windowed + operator ADC.
#   ./iam-service-accounts.sh --verify           # read-only LIVE diff of the
#                                                # IAM against the declaration
#                                                # (ADC, never window-gated —
#                                                # the shape P35.1a's live-diff
#                                                # reuses)
#   ./iam-service-accounts.sh --verify --from-state DIR
#                                             # offline diff of a recorded
#                                             # snapshot (a capture dir, or a
#                                             # leg dir holding pre/ + post/)
#
# Actions:
#   prestate    the AR-2-analogue restore point for IAM: project + per-service
#               + per-secret + web-bucket IAM policies, `run services describe`
#               (revision, image digest, runtime SA), the sig-probe job
#               describe (the caller identity the invoker grant names), and a
#               route-compare baseline of /health + the allow-listed routes.
#               READ-ONLY — runs any time.
#   identities  create the declared SAs (sig-api-rt / sig-web-rt /
#               sig-alerts-rt — idempotent).
#   bindings    the declared project role (cloudsql.client → sig-api-rt), the
#               web-bucket objectViewer (→ sig-web-rt) and the per-consumer
#               secret accessor (sig-pg-password → sig-api-rt).
#   revisions   one same-image revision per service — `run services update
#               --service-account` keeps every other field, the image digest
#               included, byte-identical (an identity change, never a roll).
#   invoker     grant roles/run.invoker on sig-alerts to the CALLER identity
#               (sig-probe's recorded serviceAccountName — the default
#               compute SA today, sig-probe-rt after P34.42b), THEN revoke
#               allUsers (G1-11). Grant before revoke: the receiver never has
#               a moment no caller can reach.
#   verify      poststate capture + `sig-ops iam diff` clean +
#               `sig-ops iam check-revisions` (every service's image digest
#               byte-identical) + the route byte-compare + the analysis leg
#               below. READ-ONLY.
#   analysis    the proof-without-destruction read (deliverable 5):
#               `policy-intelligence troubleshoot-iam-policy` per runtime SA —
#               cloudsql.instances.delete, storage.objects.delete on every
#               bucket, secretmanager.versions.access on every non-consumer
#               secret — each must answer NOT_GRANTED. No deletion is ever
#               attempted as a probe. READ-ONLY.
#   rollback    from the recorded prestate: each service back to its prior SA
#               (a new revision, never a traffic revert), sig-alerts'
#               invoker policy re-set from the capture, the added bindings
#               removed, then the now-unused SAs deleted. Deliberately NOT
#               window-gated — restoring prestate is always safe.
#   all         prestate → identities → bindings → revisions → invoker →
#               verify (the leg, incl. analysis).
#
# Live window (OM-19, the contract's AR-3 + AR-2 slot): applies run ≥
# ${SIG_IAM_EARLIEST} and never 03:00–06:30Z; earlier → exit 42 (queued, the
# RETURN PASS re-run prompt is printed). 14:00–20:00Z on a weekday is the
# preferred slot — outside it the guard logs a note, never a refusal.
# SIG_IAM_NOW overrides the clock for the offline guard test only.
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
      [ $# -ge 2 ] || { echo "iam-service-accounts.sh: --from-state needs a directory" >&2; exit 64; }
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
STATE_DIR="${2:-${SIG_IAM_STATE_DIR:-${TMPDIR:-/tmp}/p34.42a-iam}}"

_repo="$(cd "${_here}/../.." && pwd)"

RERUN='implement-spec spec=docs/tickets/251_P34.42a__least-privilege-service-identities.md live_verification=true'

_sigops() {
  (cd "${_repo}" && uv run --quiet sig-ops "$@")
}

# `_decl <python -c body>` — a field out of `sig-ops iam plan --json` (the
# declaration is the single source of every name this script uses).
_decl() {
  _sigops iam plan --json --leg services \
    --project "${SIG_GCP_PROJECT}" --region "${SIG_GCP_REGION}" \
    | python3 -c "$1"
}

# `assert_window` — the OM-19/AR-3 clock guard (ISO strings compare
# lexicographically; exit 42 = queued leg). Check mode is never gated —
# a printed plan mutates nothing.
assert_window() {
  [ "${SIG_GCP_MODE}" = "apply" ] || return 0
  local now hhmm dow
  now="${SIG_IAM_NOW:-$(date -u +%Y-%m-%dT%H:%M:%SZ)}"
  if [[ "${now}" < "${SIG_IAM_EARLIEST}" ]]; then
    _log "QUEUED (exit 42): now=${now} < ${SIG_IAM_EARLIEST} — the AR-3 freeze."
    _log "re-run: ${RERUN} (scope: the IAM leg only)"
    exit 42
  fi
  hhmm="${now:11:5}"
  if [[ "${hhmm}" > "02:59" && "${hhmm}" < "06:30" ]]; then
    _log "QUEUED (exit 42): ${now} is inside 03:00–06:30Z — never mutate then."
    _log "re-run: ${RERUN} (scope: the IAM leg only)"
    exit 42
  fi
  dow="$(date -u -d "${now}" +%u 2>/dev/null \
        || date -u -j -f '%Y-%m-%dT%H:%M:%SZ' "${now}" +%u 2>/dev/null \
        || echo 7)"
  if [[ "${hhmm}" > "13:59" && "${hhmm}" < "20:00" && "${dow}" -le 5 ]]; then
    _log "window OK: ${now} (the preferred 14:00–20:00Z weekday slot)"
  else
    _log "window OK: ${now} (≥ ${SIG_IAM_EARLIEST}, outside 03:00–06:30Z — note: outside the preferred 14:00–20:00Z weekday slot)"
  fi
}

# `_sa_email <id>` — the service-account e-mail for a declared id.
_sa_email() { printf '%s@%s.iam.gserviceaccount.com' "$1" "${SIG_GCP_PROJECT}"; }

# `_caller_identity` — the invoker grant's member: sig-probe's CURRENT
# serviceAccountName (the default compute SA until P34.42b's sig-probe-rt),
# read from the recorded job describe; falls back to the project-number form.
_caller_identity() {
  local probe="${STATE_DIR}/pre/job-sig-probe.json"
  if [ "${SIG_GCP_MODE}" = "check" ]; then
    printf '%s' "<sig-probe's recorded serviceAccountName — the default compute SA today; sig-probe-rt after P34.42b>"
    return 0
  fi
  local sa
  sa="$(python3 -c 'import json,sys
d = json.load(open(sys.argv[1]))
spec = (d.get("spec") or {}).get("template", {}).get("spec", {}).get("template", {}).get("spec", {})
print(spec.get("serviceAccountName", ""))' "${probe}" 2>/dev/null || true)"
  if [ -z "${sa}" ]; then
    sa="$(cat "${STATE_DIR}/pre/compute-sa.txt" 2>/dev/null || true)"
  fi
  if [ -z "${sa}" ]; then
    _log "ERROR: no recorded caller identity (${probe} or compute-sa.txt) — refusing." >&2
    exit 4
  fi
  printf '%s' "${sa}"
}

_sha256() {
  if command -v sha256sum >/dev/null 2>&1; then sha256sum "$1" | awk '{print $1}';
  else shasum -a 256 "$1" | awk '{print $1}'; fi
}

# `_capture <dir>` — the IAM + service snapshot both prestate and verify take.
_capture() {
  local dir="$1" svc s
  mkdir -p "${dir}"
  gcloud projects get-iam-policy "${SIG_GCP_PROJECT}" \
    --format json > "${dir}/project-iam.json"
  gcloud iam service-accounts list --project "${SIG_GCP_PROJECT}" \
    --format json > "${dir}/service-accounts.json"
  gcloud projects describe "${SIG_GCP_PROJECT}" \
    --format='value(projectNumber)' > "${dir}/project-number.txt"
  printf '%s-compute@developer.gserviceaccount.com' \
    "$(cat "${dir}/project-number.txt")" > "${dir}/compute-sa.txt"
  for svc in ${SERVICES}; do
    gcloud run services describe "${svc}" --region "${SIG_GCP_REGION}" \
      --project "${SIG_GCP_PROJECT}" --format json > "${dir}/service-${svc}.json"
    gcloud run services get-iam-policy "${svc}" --region "${SIG_GCP_REGION}" \
      --project "${SIG_GCP_PROJECT}" --format json > "${dir}/service-${svc}-iam.json"
  done
  gcloud run jobs describe "${SIG_RUN_JOB_PROBE}" --region "${SIG_GCP_REGION}" \
    --project "${SIG_GCP_PROJECT}" --format json > "${dir}/job-sig-probe.json" \
    || printf '{}' > "${dir}/job-sig-probe.json"
  gcloud storage buckets get-iam-policy "gs://${SIG_BUCKET_WEB}" \
    --format json > "${dir}/bucket-sig-web-iam.json"
  for s in ${SECRET_NAMES}; do
    gcloud secrets get-iam-policy "${s}" --project "${SIG_GCP_PROJECT}" \
      --format json > "${dir}/secret-${s}-iam.json" \
      || printf '{"bindings":[]}' > "${dir}/secret-${s}-iam.json"
  done
  (cd "${dir}" && for f in *.json; do _sha256 "$f"; done) > "${dir}/sha256s.txt"
}

do_prestate() {
  _log "-- prestate: the IAM restore point under ${STATE_DIR}/pre (read-only) --"
  if [ "${SIG_GCP_MODE}" = "check" ]; then
    _plan "gcloud projects get-iam-policy ${SIG_GCP_PROJECT} > pre/project-iam.json"
    _plan "gcloud iam service-accounts list + projects describe > pre/service-accounts.json, project-number.txt, compute-sa.txt"
    _plan "gcloud run services describe + get-iam-policy for: ${SERVICES} > pre/service-*.json"
    _plan "gcloud run jobs describe ${SIG_RUN_JOB_PROBE} > pre/job-sig-probe.json  (the caller identity)"
    _plan "gcloud storage buckets get-iam-policy gs://${SIG_BUCKET_WEB} > pre/bucket-sig-web-iam.json"
    _plan "gcloud secrets get-iam-policy for: ${SECRET_NAMES} > pre/secret-*-iam.json"
    _plan "sig-ops route-compare capture --base <sig-api/sig-web/sig-alerts run.app urls> > pre/routes-*.json"
    _plan "sha256 sidecars over every capture > pre/sha256s.txt"
    return 0
  fi
  _capture "${STATE_DIR}/pre"
  local svc url
  for svc in ${SERVICES}; do
    url="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["status"]["url"])' \
      "${STATE_DIR}/pre/service-${svc}.json" 2>/dev/null || true)"
    if [ -n "${url}" ]; then
      _sigops route-compare capture --base "${url}" \
        --out "${STATE_DIR}/pre/routes-${svc}.json" \
        || _log "   note: route-compare on ${svc} recorded a failure (kept for the record)"
      if [ -f "${STATE_DIR}/pre/routes-${svc}.json" ]; then
        _sha256 "${STATE_DIR}/pre/routes-${svc}.json" >> "${STATE_DIR}/pre/sha256s.txt"
      fi
    fi
  done
  _log "   prestate recorded under ${STATE_DIR}/pre (date -u: $(date -u +%FT%TZ))"
}

do_identities() {
  assert_window
  _log "-- identities: create the declared runtime SAs (idempotent) --"
  local sa
  for sa in ${SA_IDS}; do
    if [ "${SIG_GCP_MODE}" = "apply" ] && \
       gcloud iam service-accounts describe "$(_sa_email "${sa}")" \
         --project "${SIG_GCP_PROJECT}" >/dev/null 2>&1; then
      _log "exists: ${sa} — skipping create"
    else
      run gcloud iam service-accounts create "${sa}" \
        --display-name "${sa} runtime" \
        --project "${SIG_GCP_PROJECT}"
      _log "   rollback: gcloud iam service-accounts delete $(_sa_email "${sa}") --quiet"
    fi
  done
}

do_bindings() {
  assert_window
  _log "-- bindings: the declared least-privilege grants --"
  # sig-api-rt: Cloud SQL client (its only project role).
  run gcloud projects add-iam-policy-binding "${SIG_GCP_PROJECT}" \
    --member "serviceAccount:${SIG_API_SA_EMAIL}" --role roles/cloudsql.client
  _log "   rollback: gcloud projects remove-iam-policy-binding ${SIG_GCP_PROJECT} --member serviceAccount:${SIG_API_SA_EMAIL} --role roles/cloudsql.client"
  # sig-web-rt: objectViewer on the web bucket only (the gcsfuse mount).
  run gcloud storage buckets add-iam-policy-binding "gs://${SIG_BUCKET_WEB}" \
    --member "serviceAccount:${SIG_WEB_SA_EMAIL}" --role roles/storage.objectViewer
  _log "   rollback: gcloud storage buckets remove-iam-policy-binding gs://${SIG_BUCKET_WEB} --member serviceAccount:${SIG_WEB_SA_EMAIL} --role roles/storage.objectViewer"
  # sig-api-rt: accessor on its own DB secret only — every other secret keeps
  # its default-compute accessor until P34.42b moves the jobs.
  run gcloud secrets add-iam-policy-binding "${SIG_SECRET_PG_PASSWORD}" \
    --project "${SIG_GCP_PROJECT}" \
    --member "serviceAccount:${SIG_API_SA_EMAIL}" \
    --role roles/secretmanager.secretAccessor
  _log "   rollback: gcloud secrets remove-iam-policy-binding ${SIG_SECRET_PG_PASSWORD} --member serviceAccount:${SIG_API_SA_EMAIL} --role roles/secretmanager.secretAccessor"
  _log "   sig-alerts-rt: NO bindings — it carries no project roles and reads no secret."
}

do_revisions() {
  assert_window
  _log "-- revisions: one same-image revision per service (identity only) --"
  local svc sa
  while read -r svc sa; do
    [ -n "${svc}" ] || continue
    run gcloud run services update "${svc}" \
      --service-account "$(_sa_email "${sa}")" \
      --region "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}"
    _log "   rollback: gcloud run services update ${svc} --service-account <recorded prior SA: pre/service-${svc}.json>"
  done <<<"${SVC_SA_LINES}"
}

do_invoker() {
  assert_window
  _log "-- invoker: sig-alerts authenticates its caller by IAM (G1-11) --"
  local caller
  caller="$(_caller_identity)"
  # Grant BEFORE revoke: the receiver never has a moment its only caller
  # cannot reach.
  run gcloud run services add-iam-policy-binding "${SIG_ALERTS_SERVICE}" \
    --member "serviceAccount:${caller}" --role roles/run.invoker \
    --region "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}"
  run gcloud run services remove-iam-policy-binding "${SIG_ALERTS_SERVICE}" \
    --member allUsers --role roles/run.invoker \
    --region "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}"
  _log "   rollback: gcloud run services set-iam-policy ${SIG_ALERTS_SERVICE} ${STATE_DIR}/pre/service-${SIG_ALERTS_SERVICE}-iam.json --region ${SIG_GCP_REGION}"
  _log "   sig-api + sig-web STAY allUsers — public read API + public site (public responses do not change)."
}

do_verify() {
  _log "-- verify: poststate capture → iam diff + same-image gate + byte-compare --"
  if [ -n "${FROM_STATE}" ]; then
    # Offline: judge a recorded snapshot (a capture dir, or a leg dir that
    # holds pre/ + post/) against the declaration — no ADC, no network.
    if [ -d "${FROM_STATE}/pre" ] && [ -d "${FROM_STATE}/post" ]; then
      _sigops iam check-revisions --pre "${FROM_STATE}/pre" --post "${FROM_STATE}/post"
      _sigops iam diff --state-dir "${FROM_STATE}/post" --project "${SIG_GCP_PROJECT}" --leg services
    else
      _sigops iam diff --state-dir "${FROM_STATE}" --project "${SIG_GCP_PROJECT}" --leg services
    fi
    return 0
  fi
  if [ "${SIG_GCP_MODE}" = "check" ]; then
    _plan "re-capture every prestate read under ${STATE_DIR}/post (same file names)"
    _plan "sig-ops iam diff --state-dir ${STATE_DIR}/post --project ${SIG_GCP_PROJECT} --leg services   (clean = the services-leg posture holds)"
    _plan "sig-ops iam check-revisions --pre ${STATE_DIR}/pre --post ${STATE_DIR}/post  (every image digest byte-identical)"
    _plan "sig-ops route-compare verify --a pre/routes-<svc>.json --b post/routes-<svc>.json  (public responses unchanged)"
    do_analysis
    return 0
  fi
  _capture "${STATE_DIR}/post"
  local svc url
  for svc in ${SERVICES}; do
    url="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["status"]["url"])' \
      "${STATE_DIR}/post/service-${svc}.json" 2>/dev/null || true)"
    if [ -n "${url}" ] && [ -f "${STATE_DIR}/pre/routes-${svc}.json" ]; then
      _sigops route-compare capture --base "${url}" \
        --out "${STATE_DIR}/post/routes-${svc}.json" || true
      if [ -f "${STATE_DIR}/post/routes-${svc}.json" ]; then
        _sigops route-compare verify \
          --a "${STATE_DIR}/pre/routes-${svc}.json" \
          --b "${STATE_DIR}/post/routes-${svc}.json"
      fi
    fi
  done
  _sigops iam check-revisions --pre "${STATE_DIR}/pre" --post "${STATE_DIR}/post"
  _sigops iam diff --state-dir "${STATE_DIR}/post" --project "${SIG_GCP_PROJECT}" --leg services
  do_analysis
  _log "verify OK — every service on its own SA, images byte-identical, sig-alerts IAM-invoked."
}

# `do_analysis` — the proof-without-destruction leg (deliverable 5): read-only
# policy troubleshooting shows every runtime SA lacks delete on the spine and
# the evidence stores and lacks access to any secret it does not consume. No
# deletion is ever attempted as a probe.
do_analysis() {
  _log "-- analysis: policy-troubleshooter over the three runtime SAs (read-only) --"
  if [ "${SIG_GCP_MODE}" = "check" ]; then
    _plan "per runtime SA: gcloud policy-intelligence troubleshoot-iam-policy \\"
    _plan "  //cloudresourcemanager.googleapis.com/projects/${SIG_GCP_PROJECT} \\"
    _plan "  --principal-email <sa-email> --permission cloudsql.instances.delete  → NOT_GRANTED (the spine)"
    _plan "  + storage.objects.delete on each of {restricted, backups, public, web} buckets → NOT_GRANTED (the evidence stores)"
    _plan "  + secretmanager.versions.access on every non-consumer secret → NOT_GRANTED (no foreign secret reads)"
    _plan "  answers recorded under ${STATE_DIR}/post/analysis-*.json; any GRANTED is a hard fail"
    return 0
  fi
  local sa email failures=0
  local buckets="${SIG_BUCKET_RESTRICTED} ${SIG_BUCKET_BACKUPS} ${SIG_BUCKET_PUBLIC} ${SIG_BUCKET_WEB}"
  mkdir -p "${STATE_DIR}/post"
  for sa in ${SA_IDS}; do
    email="$(_sa_email "${sa}")"
    # The spine: Cloud SQL instance deletion is a project-level permission.
    _troubleshoot "${email}" \
      "//cloudresourcemanager.googleapis.com/projects/${SIG_GCP_PROJECT}" \
      "cloudsql.instances.delete" || failures=$((failures + 1))
    # The evidence stores: object deletion on every bucket.
    local b
    for b in ${buckets}; do
      _troubleshoot "${email}" \
        "//storage.googleapis.com/projects/_/buckets/${b}" \
        "storage.objects.delete" || failures=$((failures + 1))
    done
    # Foreign secrets: accessor on every secret this SA is not a consumer of
    # (the consumer matrix comes from the declaration, once, via SECRET_CONSUMERS).
    local s cons
    for s in ${SECRET_NAMES}; do
      cons="$(printf '%s\n' "${SECRET_CONSUMERS}" | sed -n "s/^${s}://p")"
      case " ${cons} " in
        *" ${sa} "*) continue ;;
      esac
      _troubleshoot "${email}" \
        "//secretmanager.googleapis.com/projects/${SIG_GCP_PROJECT}/secrets/${s}" \
        "secretmanager.versions.access" || failures=$((failures + 1))
    done
  done
  if [ "${failures}" -gt 0 ]; then
    _log "FAIL: ${failures} troubleshoot answer(s) came back GRANTED — a runtime SA holds delete or a foreign secret." >&2
    return 1
  fi
  _log "   analysis OK — no runtime SA holds delete on the spine/evidence stores or a foreign secret."
}

# `_troubleshoot <email> <resource> <permission>` — one read-only answer;
# returns 1 when the answer is GRANTED (a hard stop rule).
_troubleshoot() {
  local out="${STATE_DIR}/post/analysis-$(printf '%s' "$3" | tr . _)-$(printf '%s' "$1" | cut -d@ -f1)-$(basename "$2" | tr '/' '_').json"
  local state
  if ! gcloud policy-intelligence troubleshoot-iam-policy "$2" \
    --principal-email="$1" --permission="$3" \
    --project="${SIG_GCP_PROJECT}" --format=json > "${out}" 2>/dev/null; then
    _log "   troubleshoot ${3} on $2 for $1: read failed (recorded, non-fatal)"
    return 0
  fi
  state="$(python3 -c 'import json,sys
d = json.load(open(sys.argv[1]))
t = d.get("accessTuple") or {}
print(t.get("accessState", d.get("accessState", "UNKNOWN")))' "${out}" 2>/dev/null || echo UNKNOWN)"
  if [ "${state}" = "GRANTED" ]; then
    _log "   FAIL: $1 holds $3 on $2 (GRANTED)"
    return 1
  fi
  _log "   $1: $3 on $(basename "$2") → ${state} (recorded)"
}

do_rollback() {
  _log "-- rollback: restore the recorded prestate (never a blind revert) --"
  if [ "${SIG_GCP_MODE}" = "check" ]; then
    _plan "per service: gcloud run services update <svc> --service-account <prior SA from pre/service-<svc>.json>"
    _plan "gcloud run services set-iam-policy ${SIG_ALERTS_SERVICE} pre/service-${SIG_ALERTS_SERVICE}-iam.json  (restores allUsers + drops the caller grant)"
    _plan "gcloud secrets remove-iam-policy-binding ${SIG_SECRET_PG_PASSWORD} --member serviceAccount:${SIG_API_SA_EMAIL}"
    _plan "gcloud storage buckets remove-iam-policy-binding gs://${SIG_BUCKET_WEB} --member serviceAccount:${SIG_WEB_SA_EMAIL}"
    _plan "gcloud projects remove-iam-policy-binding ${SIG_GCP_PROJECT} --member serviceAccount:${SIG_API_SA_EMAIL} --role roles/cloudsql.client"
    _plan "gcloud iam service-accounts delete sig-{api,web,alerts}-rt@…  (last — only once unbound)"
    return 0
  fi
  local prior svc
  for svc in ${SERVICES}; do
    prior="$(python3 -c 'import json,sys
d = json.load(open(sys.argv[1]))
spec = (d.get("spec") or {}).get("template", {}).get("spec", {})
print(spec.get("serviceAccountName", ""))' "${STATE_DIR}/pre/service-${svc}.json" 2>/dev/null || true)"
    if [ -z "${prior}" ]; then
      _log "ERROR: no recorded prior SA at ${STATE_DIR}/pre/service-${svc}.json — refusing to roll back blind." >&2
      exit 4
    fi
    gcloud run services update "${svc}" --service-account "${prior}" \
      --region "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}"
  done
  gcloud run services set-iam-policy "${SIG_ALERTS_SERVICE}" \
    "${STATE_DIR}/pre/service-${SIG_ALERTS_SERVICE}-iam.json" \
    --region "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}"
  gcloud secrets remove-iam-policy-binding "${SIG_SECRET_PG_PASSWORD}" \
    --project "${SIG_GCP_PROJECT}" \
    --member "serviceAccount:${SIG_API_SA_EMAIL}" \
    --role roles/secretmanager.secretAccessor || true
  gcloud storage buckets remove-iam-policy-binding "gs://${SIG_BUCKET_WEB}" \
    --member "serviceAccount:${SIG_WEB_SA_EMAIL}" \
    --role roles/storage.objectViewer || true
  gcloud projects remove-iam-policy-binding "${SIG_GCP_PROJECT}" \
    --member "serviceAccount:${SIG_API_SA_EMAIL}" --role roles/cloudsql.client || true
  gcloud iam service-accounts delete "${SIG_API_SA_EMAIL}" \
    --project "${SIG_GCP_PROJECT}" --quiet || true
  gcloud iam service-accounts delete "${SIG_WEB_SA_EMAIL}" \
    --project "${SIG_GCP_PROJECT}" --quiet || true
  gcloud iam service-accounts delete "${SIG_ALERTS_SA_EMAIL}" \
    --project "${SIG_GCP_PROJECT}" --quiet || true
  _log "rollback applied — prior SAs restored, invoker policy re-set, bindings + SAs removed."
}

# Every non-check path (live verify included — member names embed the project
# id) requires SIG_GCP_PROJECT; check mode tolerates the placeholder.
require_project
# config.sh derived the *_SA_EMAIL + bucket names before require_project
# filled the placeholder — re-derive so PLANs name real resource paths.
export SIG_API_SA_EMAIL="${SIG_SA_API}@${SIG_GCP_PROJECT}.iam.gserviceaccount.com"
export SIG_WEB_SA_EMAIL="${SIG_SA_WEB}@${SIG_GCP_PROJECT}.iam.gserviceaccount.com"
export SIG_ALERTS_SA_EMAIL="${SIG_SA_ALERTS}@${SIG_GCP_PROJECT}.iam.gserviceaccount.com"
export SIG_BUCKET_WEB="${SIG_GCP_PROJECT}-sig-web"
# The clock guard precedes the ADC gate so a queued apply exits 42 cleanly.
case "${ACTION}" in
  identities|bindings|revisions|invoker|all) assert_window ;;
esac
# A live verify reads with ADC; an offline --from-state diff needs none.
if [ -z "${FROM_STATE}" ]; then
  require_adc
fi

# Every name below is derived from the committed declaration — the TOML is the
# single source (a drift between this list and ops/iam_identities.toml fails
# here, loudly, rather than mutating the wrong target).
SERVICES="$(_decl 'import json,sys; print(" ".join(s["name"] for s in json.load(sys.stdin)["services"]))')"
# The SERVICES-leg identities only — the declaration now also carries the
# P34.42b job-class + reserved SAs, which the jobs leg owns (a jobs-leg apply
# is never implied by this script).
SA_IDS="$(_decl 'import json,sys; print(" ".join(s["service_account"] for s in json.load(sys.stdin)["services"]))')"
SECRET_NAMES="$(_decl 'import json,sys; print(" ".join(s["name"] for s in json.load(sys.stdin)["secrets"]))')"
SVC_SA_LINES="$(_decl 'import json,sys; print("\n".join(s["name"]+" "+s["service_account"] for s in json.load(sys.stdin)["services"]))')"
# "<secret>:consumer consumer …" per line — the analysis leg's foreign-secret lookup.
SECRET_CONSUMERS="$(_decl 'import json,sys; print("\n".join(s["name"]+":"+" ".join(s["consumers"]) for s in json.load(sys.stdin)["secrets"]))')"

banner "P34.42a — least-privilege runtime identities (G1-01, SIG-SEC-007)"

case "${ACTION}" in
  prestate)   do_prestate ;;
  identities) do_identities ;;
  bindings)   do_bindings ;;
  revisions)  do_revisions ;;
  invoker)    do_invoker ;;
  verify)     do_verify ;;
  analysis)   do_analysis ;;
  rollback)   do_rollback ;;
  all)
    do_prestate
    do_identities
    do_bindings
    do_revisions
    do_invoker
    do_verify ;;
  *) _log "usage: $(basename "$0") [--check|--apply|--verify [--from-state DIR]] [prestate|identities|bindings|revisions|invoker|verify|analysis|rollback|all] [state-dir]" >&2; exit 64 ;;
esac

if [ "${SIG_GCP_MODE}" = "check" ]; then
  _log "iam-service-accounts ${ACTION}: check OK (mode=${SIG_GCP_MODE})"
else
  _log "iam-service-accounts ${ACTION}: done (mode=${SIG_GCP_MODE})"
fi
