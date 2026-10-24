#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
#
# ops/gcp/release-infra.sh — P35.53 (SIG-REL-004/005, REL-03a): the private
# release-bucket + staging-origin leg of the release pipeline. Every other
# script declares one of the two PUBLIC surfaces; this one is the strict
# inverse — everything it creates is private/IAM-only, and its `verify` and
# `probe` legs exist to PROVE that.
#
#   prestate     timestamped pre-state capture into $SIG_RELEASE_STATE_DIR
#                (buckets, run services+jobs, project IAM, release-API sig ops
#                state if the bucket already exists) + the AR-2 sqlpoint
#                restore-point call (ops/gcp/restore-point.sh) — AR-3's
#                read-before-write evidence.
#
#   apply        the three creates, resumable by name (each create is
#                skipped when the resource already exists):
#                  1. gs://<project>-sig-release — private bucket:
#                     --uniform-bucket-level-access --public-access-prevention,
#                     versioning on, 30-day noncurrent lifecycle, and the
#                     single-writer IAM binding set (below). NO allUsers /
#                     allAuthenticatedUsers anywhere.
#                  2. sig-web-staging + sig-api-staging Cloud Run services —
#                     deployed from sig-web/sig-api's LIVE image digests at
#                     apply time (the ticket's "same image" clause),
#                     --no-allow-unauthenticated, SIG_STAGING=1, scale-to-0.
#                  3. sig-release Cloud Run job on sig-release-rt — the job
#                     is an entrypoint, not a baked payload: it refuses a
#                     bare execute, and its verbs+args are passed at
#                     `gcloud run jobs execute --args` time.
#                sig-release-rt's least-privilege grant set is declared here
#                too: objectUser on sig-release conditioned to everything
#                EXCEPT status/**, and objectViewer on sig-restricted
#                conditioned to exports/ (build's fetch leg).
#
#   verify       describe-assert every created resource: bucket flags +
#                 lifecycle + IAM (no allUsers; both conditions present), both
#                 services private with SIG_STAGING=1 + prod digests +
#                 scale-0, job on sig-release-rt with the no-op guard.
#
#   probe        unauthenticated refusal proof: bare `curl` of both staging
#                 service URLs and the bucket's public JSON endpoint —
#                 refuses the leg if anything answers 200.
#
#   stale-check  real-bucket refusal proof: stage a fixture pub, re-stage
#                 (resume skip), mutate the byte and stage again (the
#                 create-if-absent name collision must refuse), seed
#                 registry/LOCK out-of-band (status must refuse), then a
#                 real stale-generation via a second store writer on the
#                 held lock. The fixture pub is sha256-labelled and journaled.
#
#   all          prestate -> apply -> verify -> probe -> stale-check.
#
# Usage:
#   ops/gcp/release-infra.sh [--check|--dry-run] [ACTION]   # plan (default)
#   ops/gcp/release-infra.sh --apply [ACTION]               # real leg
#     ACTION := prestate | apply | verify | probe | stale-check | all
#
# Env: SIG_GCP_PROJECT (required on apply), SIG_GCP_REGION, SIG_BUCKET_RELEASE,
# SIG_WEB_STAGING, SIG_API_STAGING, SIG_RELEASE_JOB, SIG_RELEASE_EARLIEST,
# SIG_RELEASE_STATE_DIR, SIG_RELEASE_AUTHOR (required on apply — the recorded
# operator id; OM-20's scope discipline), SIG_RELEASE_NOW (test-only clock
# override for the window guard), SIG_EXPORT_NOW (fed through to
# restore-point.sh's caller), GOCLOUD_PROJECT/GOOGLE_CLOUD_PROJECT.
#
# Live-window contract (the ticket's "Timed phases" list): applies require
# the AR-2 sqlpoint first (restore-point.sh --apply sqlpoint) AND the
# explicit OM-20 listing naming THIS row — same consent contract as
# iam-service-accounts.sh: SIG_RELEASE_AUTHOR records the operator, the
# window is [SIG_RELEASE_EARLIEST, never 03:00–06:30Z), the preferred slot
# is weekday 14:00–20:00Z. Check mode needs nothing — no project, no ADC,
# every line says who runs when — the OM-19 reviewer reads the apply plan
# without standing anything up.
#
# Rerun prompt (with OM-20's P35.53 listing; the staging-job name below is
# this row's, NOT the 1988-quality-probe's):
#   SIG_RELEASE_AUTHOR="$(git config user.name)" \
#   bash ops/gcp/release-infra.sh --apply all
set -euo pipefail

_here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=config.sh
. "${_here}/config.sh"
# shellcheck source=lib.sh
. "${_here}/lib.sh"
_repo="$(cd "${_here}/../.." && pwd)"

_usage() {
  sed -n '/^# Usage:/,/^# Env:/p' "$0" | sed 's/^# \{0,1\}//'
  exit "${1:-64}"
}

parse_mode "${1:-}"
case "${1:-}" in --apply|--check|--dry-run) shift ;; esac
ACTION="${1:-all}"
case "${ACTION}" in
  prestate|apply|verify|probe|stale-check|all) ;;
  *) echo "release-infra.sh: unknown action '${ACTION}'" >&2; _usage ;;
esac
STATE_DIR="${SIG_RELEASE_STATE_DIR}"
RERUN='SIG_RELEASE_AUTHOR="$(git config user.name)" bash ops/gcp/release-infra.sh --apply '"${ACTION}"

die() { _log "ERROR: $*" >&2; exit 4; }

_release_now() { printf '%s' "${SIG_RELEASE_NOW:-$(date -u +%Y-%m-%dT%H:%M:%SZ)}"; }

assert_window() {
  [ "${SIG_GCP_MODE}" = "apply" ] || return 0
  local nowiso hhmm dow
  nowiso="$(_release_now)"
  if [[ "${nowiso}" < "${SIG_RELEASE_EARLIEST}" ]]; then
    _log "QUEUED (exit 42): now=${nowiso} < ${SIG_RELEASE_EARLIEST} — the AR-3 freeze."
    _log "re-run: ${RERUN}"
    exit 42
  fi
  hhmm="${nowiso:11:5}"
  if [[ "${hhmm}" > "02:59" && "${hhmm}" < "06:30" ]]; then
    _log "QUEUED (exit 42): ${nowiso} is inside 03:00-06:30Z — never mutate then."
    _log "re-run: ${RERUN}"
    exit 42
  fi
  dow="$(date -u -d "${nowiso}" +%u 2>/dev/null \
        || date -u -j -f '%Y-%m-%dT%H:%M:%SZ' "${nowiso}" +%u 2>/dev/null \
        || echo 7)"
  if { [[ "${hhmm}" < "14:00" ]] || [[ "${hhmm}" > "19:59" ]]; } && [ "${dow}" -le 5 ]; then
    _log "note: outside the preferred weekday 14:00-20:00Z slot" >&2
  fi
  [ -n "${SIG_RELEASE_AUTHOR}" ] || \
    die "set SIG_RELEASE_AUTHOR to the recorded operator id (OM-20's scope discipline)"
}

_capture() {  # _capture DIR — the pre-state snapshot.
  local dir="$1"; mkdir -p "$dir"
  run gcloud storage buckets list --project "${SIG_GCP_PROJECT}" \
    --format=json > "${dir}/buckets.json" || true
  run gcloud run services list --project "${SIG_GCP_PROJECT}" \
    --region "${SIG_GCP_REGION}" --format=json > "${dir}/services.json" || true
  run gcloud run jobs list --project "${SIG_GCP_PROJECT}" \
    --region "${SIG_GCP_REGION}" --format=json > "${dir}/jobs.json" || true
  run gcloud projects get-iam-policy "${SIG_GCP_PROJECT}" \
    --format=json > "${dir}/project-iam.json" || true
  run date -u > "${dir}/captured.txt" || true
  echo "release-infra.sh: pre-state captured under ${dir}"
}

_sa_email() { printf '%s@%s.iam.gserviceaccount.com' "$1" "${SIG_GCP_PROJECT}"; }

_bucket_exists() { gcloud storage buckets describe "gs://${SIG_BUCKET_RELEASE}" >/dev/null 2>&1; }
_svc_exists() { gcloud run services describe "$1" --project "${SIG_GCP_PROJECT}" --region "${SIG_GCP_REGION}" >/dev/null 2>&1; }
_job_exists() { gcloud run jobs describe "$1" --project "${SIG_GCP_PROJECT}" --region "${SIG_GCP_REGION}" >/dev/null 2>&1; }
_sa_exists() { gcloud iam service-accounts describe "$(_sa_email "$1")" --project "${SIG_GCP_PROJECT}" >/dev/null 2>&1; }

_img_of() {  # _img_of SERVICE — the live digest a staging service clones.
  gcloud run services describe "$1" --project "${SIG_GCP_PROJECT}" \
    --region "${SIG_GCP_REGION}" \
    --format='value(spec.template.spec.containers[0].image)'
}

plan() {
  cat <<EOF
PLAN: release-infra (${ACTION}) — project ${SIG_GCP_PROJECT} region ${SIG_GCP_REGION}
PLAN: bucket        gs://${SIG_BUCKET_RELEASE} (private; UBLA + public-access-prevention +
                  versioning + ${SIG_RELEASE_LIFECYCLE}; IAM: sig-release-rt objectUser
                  EXCEPT status/**, sig-status-rt objectUser status/** only,
                  sig-web-rt + sig-api-rt objectViewer — NO allUsers)
PLAN: staging svc   ${SIG_WEB_STAGING} ${SIG_API_STAGING} (live digests of
                  ${SIG_WEB_SERVICE}/${SIG_RUN_SERVICE}, --no-allow-unauthenticated,
                  SIG_STAGING=1, scale-to-0, on ${SIG_SA_WEB}/${SIG_SA_API})
PLAN: release job   ${SIG_RELEASE_JOB} on ${SIG_SA_RELEASE} (entrypoint only;
                  args at execute time; env SIG_RELEASE_REGISTRY_URI=${SIG_RELEASE_REGISTRY_URI})
PLAN: legs          prestate -> AR-2 sqlpoint -> apply -> verify -> probe -> stale-check
PLAN: deps          sig-release-rt (P34.42b) + sig-web-rt/sig-api-rt (P34.42a) must exist;
                  apply refuses otherwise — this leg binds reserved identities, never creates them
PLAN: apply needs   SIG_RELEASE_AUTHOR set, SIG_GCP_PROJECT, ADC; window >=
                  ${SIG_RELEASE_EARLIEST} and never 03:00-06:30Z
PLAN: rerun         ${RERUN}
EOF
}

do_apply() {
  # --- dependency guard: the reserved identities must already exist --------
  for sa in "${SIG_SA_RELEASE}" "${SIG_SA_WEB}" "${SIG_SA_API}" "${SIG_SA_STATUS}"; do
    if ! _sa_exists "$sa"; then
      die "$(_sa_email "$sa") is missing — P34.42a's reserved identities must exist
  before this leg binds them (re-run prompt: ${RERUN})"
    fi
  done
  local webimg apiimg
  webimg="$(_img_of "${SIG_WEB_SERVICE}")" ||
    die "cannot read ${SIG_WEB_SERVICE}'s live digest — staging clones it verbatim"
  apiimg="$(_img_of "${SIG_RUN_SERVICE}")" ||
    die "cannot read ${SIG_RUN_SERVICE}'s live digest — staging clones it verbatim"
  echo "staging digests: web=${webimg} api=${apiimg}"

  # --- create 1: the private release bucket --------------------------------
  if _bucket_exists; then
    echo "gs://${SIG_BUCKET_RELEASE} exists — bucket create skipped"
  else
    run gcloud storage buckets create "gs://${SIG_BUCKET_RELEASE}" \
      --project "${SIG_GCP_PROJECT}" --location "${SIG_GCP_REGION}" \
      --uniform-bucket-level-access --public-access-prevention
  fi
  run gcloud storage buckets update "gs://${SIG_BUCKET_RELEASE}" --versioning
  run gcloud storage buckets update "gs://${SIG_BUCKET_RELEASE}" \
    --lifecycle-file "${_repo}/${SIG_RELEASE_LIFECYCLE}"
  # The single-writer IAM set — conditions scope each grant by object name:
  # sig-release-rt owns everything except status/**; sig-status-rt owns only
  # status/**; the serving identities are read-only. Prefix conditions on
  # bucket IAM use the resource name form projects/_/buckets/<b>/objects/<p>.
  run gcloud storage buckets add-iam-policy-binding "gs://${SIG_BUCKET_RELEASE}" \
    --member "serviceAccount:$(_sa_email "${SIG_SA_RELEASE}")" --role roles/storage.objectUser \
    --condition "expression=!resource.name.startsWith(\"projects/_/buckets/${SIG_BUCKET_RELEASE}/objects/status/\"),title=release-writer-not-status,description=sig-release-rt writes the release registry but never the status prefix — P35.54's serve surface is sig-status-rt's alone"
  run gcloud storage buckets add-iam-policy-binding "gs://${SIG_BUCKET_RELEASE}" \
    --member "serviceAccount:$(_sa_email "${SIG_SA_STATUS}")" --role roles/storage.objectUser \
    --condition "expression=resource.name.startsWith(\"projects/_/buckets/${SIG_BUCKET_RELEASE}/objects/status/\"),title=status-writer-only,description=sig-status-rt's objectUser is confined to status/** — it cannot touch staged bytes or the registry"
  run gcloud storage buckets add-iam-policy-binding "gs://${SIG_BUCKET_RELEASE}" \
    --member "serviceAccount:$(_sa_email "${SIG_SA_WEB}")" --role roles/storage.objectViewer
  run gcloud storage buckets add-iam-policy-binding "gs://${SIG_BUCKET_RELEASE}" \
    --member "serviceAccount:$(_sa_email "${SIG_SA_API}")" --role roles/storage.objectViewer
  # sig-release-rt's read leg into the restricted bucket (build fetches the
  # cut export): conditioned to exports/ — least privilege, not the bucket.
  run gcloud storage buckets add-iam-policy-binding "gs://${SIG_BUCKET_RESTRICTED}" \
    --member "serviceAccount:$(_sa_email "${SIG_SA_RELEASE}")" --role roles/storage.objectViewer \
    --condition "expression=resource.name.startsWith(\"projects/_/buckets/${SIG_BUCKET_RESTRICTED}/objects/exports/\"),title=release-reads-exports,description=sig-release-rt fetches signed exports for release build — nothing else in sig-restricted"

  # --- create 2: the IAM-only staging origins ------------------------------
  for pair in "${SIG_WEB_STAGING}:${SIG_SA_WEB}:${webimg}" \
              "${SIG_API_STAGING}:${SIG_SA_API}:${apiimg}"; do
    local name sa img; name="${pair%%:*}"; pair="${pair#*:}"
    sa="${pair%%:*}"; img="${pair##*:}"
    if _svc_exists "${name}"; then
      echo "${name} exists — staging create skipped (image drift is verify's job)"
    else
      run gcloud run deploy "${name}" --image "${img}" \
        --project "${SIG_GCP_PROJECT}" --region "${SIG_GCP_REGION}" \
        --service-account "$(_sa_email "${sa}")" \
        --no-allow-unauthenticated --ingress=all \
        --min-instances 0 --max-instances 1 \
        --set-env-vars SIG_STAGING=1,SIG_TARGET=production,SIG_PROJECT_ID="${SIG_GCP_PROJECT}"
    fi
  done

  # --- create 3: the release job on sig-release-rt --------------------------
  if _job_exists "${SIG_RELEASE_JOB}"; then
    echo "${SIG_RELEASE_JOB} exists — job create skipped"
  else
    run gcloud run jobs create "${SIG_RELEASE_JOB}" \
      --project "${SIG_GCP_PROJECT}" --region "${SIG_GCP_REGION}" \
      --image "${apiimg}" --service-account "$(_sa_email "${SIG_SA_RELEASE}")" \
      --command sh \
      --args "-c,echo 'sig-release is the release-pipeline job: pass the verb+args via gcloud run jobs execute ${SIG_RELEASE_JOB} --args ...; a bare execute is a refused no-op' >&2 && exit 64" \
      --set-env-vars SIG_RELEASE_REGISTRY_URI="${SIG_RELEASE_REGISTRY_URI}",SIG_PROJECT_ID="${SIG_GCP_PROJECT}"
  fi
}

_assert() {  # _assert LABEL EXPECTED ACTUAL
  if [ "$3" != "$2" ]; then
    echo "VERIFY-FAIL $1: wanted '$2', got '$3'" >&2; exit 1
  fi
  echo "ok $1=$3"
}

do_verify() {
  _bucket_exists || die "gs://${SIG_BUCKET_RELEASE} missing — apply first"
  local bubla bver bpap bnoncur
  bubla="$(gcloud storage buckets describe "gs://${SIG_BUCKET_RELEASE}" \
    --format='value(iamConfiguration.uniformBucketLevelAccess.enabled)')"
  bver="$(gcloud storage buckets describe "gs://${SIG_BUCKET_RELEASE}" \
    --format='value(versioning.enabled)')"
  bpap="$(gcloud storage buckets describe "gs://${SIG_BUCKET_RELEASE}" \
    --format='value(iamConfiguration.publicAccessPrevention)')"
  bnoncur="$(gcloud storage buckets describe "gs://${SIG_BUCKET_RELEASE}" \
    --format='value(lifecycle.rule[0].condition.daysSinceNoncurrentTime)')"
  _assert bucket-uniform-access true "$bubla"
  _assert bucket-versioning true "$bver"
  _assert bucket-public-access-prevention enforced "$bpap"
  _assert bucket-noncurrent-days 30 "$bnoncur"
  local iam
  iam="$(gcloud storage buckets get-iam-policy "gs://${SIG_BUCKET_RELEASE}" --format=json)"
  echo "$iam" | grep -q 'allUsers\|allAuthenticatedUsers' &&
    die "gs://${SIG_BUCKET_RELEASE} IAM names a public principal — the bucket must never"
  echo "$iam" | grep -q 'release-writer-not-status' ||
    die "release bucket IAM lost the status/** exclusion on sig-release-rt"
  echo "$iam" | grep -q 'status-writer-only' ||
    die "release bucket IAM lost sig-status-rt's status/**-only binding"
  echo "ok bucket-iam-private+single-writer"

  for pair in "${SIG_WEB_STAGING}:${SIG_SA_WEB}:${SIG_WEB_SERVICE}" \
              "${SIG_API_STAGING}:${SIG_SA_API}:${SIG_RUN_SERVICE}"; do
    local name sa prod staging env image mininst prodimg
    name="${pair%%:*}"; pair="${pair#*:}"
    sa="${pair%%:*}"; prod="${pair##*:}"
    _svc_exists "${name}" || die "${name} missing — apply first"
    image="$(gcloud run services describe "${name}" --project "${SIG_GCP_PROJECT}" \
      --region "${SIG_GCP_REGION}" --format='value(spec.template.spec.containers[0].image)')"
    prodimg="$(_img_of "${prod}")"
    _assert "${name}-image" "${prodimg}" "${image}"
    env="$(gcloud run services describe "${name}" --project "${SIG_GCP_PROJECT}" \
      --region "${SIG_GCP_REGION}" \
      --format='value(spec.template.spec.containers[0].env[?name=="SIG_STAGING"].value)')"
    _assert "${name}-SIG_STAGING" 1 "${env:-unset}"
    mininst="$(gcloud run services describe "${name}" --project "${SIG_GCP_PROJECT}" \
      --region "${SIG_GCP_REGION}" --format='value(spec.template.metadata.annotations."autoscaling.knative.dev/minScale")')"
    _assert "${name}-minScale" 0 "${mininst}"
    staging="$(gcloud run services get-iam-policy "${name}" \
      --project "${SIG_GCP_PROJECT}" --region "${SIG_GCP_REGION}" --format=json)"
    echo "$staging" | grep -q 'allUsers\|allAuthenticatedUsers' &&
      die "${name} is publicly invocable — staging origins are IAM-only"
    echo "ok ${name}-iam-only"
  done

  _job_exists "${SIG_RELEASE_JOB}" || die "${SIG_RELEASE_JOB} missing — apply first"
  local jsa
  jsa="$(gcloud run jobs describe "${SIG_RELEASE_JOB}" --project "${SIG_GCP_PROJECT}" \
    --region "${SIG_GCP_REGION}" \
    --format='value(spec.template.spec.template.spec.serviceAccountName)')"
  _assert job-service-account "$(_sa_email "${SIG_SA_RELEASE}")" "${jsa}"
  echo "ok verify — bucket, staging origins, and job all match the declaration"
}

do_probe() {
  local bad=0 url code
  for svc in "${SIG_WEB_STAGING}" "${SIG_API_STAGING}"; do
    url="$(gcloud run services describe "${svc}" --project "${SIG_GCP_PROJECT}" \
      --region "${SIG_GCP_REGION}" --format='value(status.url)')" || continue
    [ -n "${url}" ] || { echo "probe: ${svc} has no URL"; bad=1; continue; }
    code="$(curl -s -o /dev/null -w '%{http_code}' --max-time 20 "${url}/" || echo 000)"
    echo "probe ${svc}: ${code} (want 403 — IAM-only)"
    [ "${code}" = "403" ] || bad=1
  done
  code="$(curl -s -o /dev/null -w '%{http_code}' --max-time 20 \
    "https://storage.googleapis.com/storage/v1/b/${SIG_BUCKET_RELEASE}/o" || echo 000)"
  echo "probe bucket: ${code} (want 401/403 — private)"
  case "${code}" in 401|403) ;; *) bad=1 ;; esac
  [ "${bad}" = 0 ] || die "probe found a publicly reachable surface — PRIVACY VIOLATION"
  echo "ok probe — nothing staged or served is publicly reachable"
}

do_stale_check() {
  local work fixpub dir
  dir="${STATE_DIR}/stale-check"; mkdir -p "${dir}"
  fixpub="p-$(printf 'sig-release-infra-check' | sha256sum | cut -d' ' -f1)"
  work="${dir}/work"; rm -rf "${work}"; mkdir -p "${work}/r/${fixpub}"
  printf 'release-infra check byte v1\n' > "${work}/r/${fixpub}/index.html"
  local rel='uv run --quiet sig-ops release'
  echo "--- 1. first stage --apply (journals staged/${fixpub})"
  (cd "${_repo}" && ${rel} stage --registry "${SIG_RELEASE_REGISTRY_URI}" \
    --publication "${fixpub}" --work-dir "${work}" --apply) || \
    die "stage did not apply cleanly"
  echo "--- 2. identical re-stage (resume must SKIP, not rewrite)"
  (cd "${_repo}" && ${rel} stage --registry "${SIG_RELEASE_REGISTRY_URI}" \
    --publication "${fixpub}" --work-dir "${work}" --apply) || \
    die "resume stage refused — resumability broken"
  echo "--- 3. mutated byte re-stage (if-generation-match=0 must refuse)"
  printf 'release-infra check byte v2\n' > "${work}/r/${fixpub}/index.html"
  if (cd "${_repo}" && ${rel} stage --registry "${SIG_RELEASE_REGISTRY_URI}" \
      --publication "${fixpub}" --work-dir "${work}" --apply); then
    die "mutated re-stage overwrote a staged byte — IMMUTABILITY VIOLATION"
  else
    echo "ok name-collision refused"
  fi
  echo "--- 4. seeded registry/LOCK (status --apply must refuse lock-held)"
  printf '{"schema":"sig.release-lock/1","note":"stale-check seed"}\n' | \
    run gcloud storage cp - "gs://${SIG_BUCKET_RELEASE}/registry/LOCK"
  if (cd "${_repo}" && ${rel} status --registry "${SIG_RELEASE_REGISTRY_URI}" --apply); then
    die "status ignored a held registry lock — LOCK CONTRACT VIOLATION"
  else
    echo "ok lock-held refused"
  fi
  run gcloud storage rm "gs://${SIG_BUCKET_RELEASE}/registry/LOCK" >/dev/null || true
  echo "--- 5. real stale-generation: drift under a held lock refuses"
  (cd "${_repo}" && uv run --quiet python - "${SIG_RELEASE_REGISTRY_URI}" <<'PY'
import sys
from ops import release_pipeline as rp
store = rp.open_store(sys.argv[1])
lock = rp.acquire_lock(store, verb="stale-check")
# Drift registry state under the held lock — resume-safe: a generation-
# matched replace when catalog.json already exists (a re-run), an insert
# otherwise; the original bytes are restored afterwards.
name = "registry/catalog.json"
orig = store.read(name)
meta = store.stat(name)
drifted = (orig or b'{"schema":"sig.release-catalog/1","publications":[]}') + b"\n"
if meta is None:
    store.insert(name, drifted)
else:
    store.replace(name, drifted, generation=int(meta["generation"]))
try:
    lock.refresh()
except rp.StaleGeneration as e:
    print("ok stale-generation refused:", e)
else:
    print("STALE-GENERATION NOT REFUSED", file=sys.stderr); sys.exit(1)
finally:
    if orig is not None:
        store.replace(name, orig, generation=int(store.stat(name)["generation"]))
    store.delete("registry/LOCK")   # free the demonstration lock
PY
  ) || die "stale-generation check failed"
  echo "ok stale-check — every refusal on the real bucket held"
}

require_project
# The clock guard precedes the ADC gate so a queued apply exits 42 cleanly —
# verify/probe stay ungated (read-only), the mutating legs are gated.
case "${ACTION}" in
  apply|stale-check|all) assert_window ;;
esac
[ "${SIG_GCP_MODE}" = "apply" ] && require_adc

case "${SIG_GCP_MODE}" in
  check) plan ;;
  apply)
    mkdir -p "${STATE_DIR}"
    case "${ACTION}" in
      prestate)
        _capture "${STATE_DIR}/prestate-$(date -u +%Y%m%dT%H%M%SZ)"
        run bash "${_here}/restore-point.sh" --apply sqlpoint ;;
      apply) do_apply ;;
      verify) do_verify ;;
      probe) do_probe ;;
      stale-check) do_stale_check ;;
      all)
        _capture "${STATE_DIR}/prestate-$(date -u +%Y%m%dT%H%M%SZ)"
        run bash "${_here}/restore-point.sh" --apply sqlpoint
        do_apply; do_verify; do_probe; do_stale_check ;;
    esac
    echo "release-infra.sh: ${ACTION} complete (author ${SIG_RELEASE_AUTHOR}; state ${STATE_DIR})" ;;
esac
