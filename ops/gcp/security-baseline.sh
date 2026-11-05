#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
#
# ops/gcp/security-baseline.sh — the P37.4a named OM-20 mutation (SIG-SEC-006,
# ADR-231): the security-baseline production writes — scan/SBOM/cosign wiring
# into the deploy path.
#
#   prestate   timestamped captures: enabled services, KMS keyrings/keys,
#              live digests of sig-api/sig-web/sig-release (sha256-sidecarred) +
#              the AR-2 restore-point call (ops/gcp/restore-point.sh).
#   apis       enable containeranalysis/containerscanning/ondemandscanning +
#              cloudkms on the project.
#   kms        create the sig-release keyring + sig-image-sign asymmetric
#              signing key (EC P-256, HSM — key material never leaves GCP).
#   sign       resolve the live digests of sig-api/sig-web/sig-release and
#              cosign sign --key $SIG_COSIGN_KEY_URI each + verify; records
#              sig.image-signature/1 under $SIG_SECB_STATE_DIR and uploads to
#              gs://<release-bucket>/ops/security/.
#   probe      the acceptance leg: cosign verify finds ≥1 signature per
#              deployed digest + the scanning API answers a describe.
#   verify     describe-assert every created resource.
#   rollback   prints the restore: remove future signature objects is never a
#              delete — the leg's writes are additive (API enables, a KMS key
#              version, signature objects); rollback = un-arm the deploy hook
#              (SIG_SECB_SIGNING=0) + disable the key version.
#   all        prestate → apis → kms → sign → probe → verify.
#
# Usage:
#   ops/gcp/security-baseline.sh [--check|--dry-run] [ACTION]   # plan (default)
#   ops/gcp/security-baseline.sh --apply [ACTION]               # real leg
#     ACTION := prestate | apis | kms | sign | probe | verify | rollback | all
#
# Env: SIG_GCP_PROJECT (required on apply), SIG_GCP_REGION, SIG_KMS_LOCATION,
# SIG_KMS_RING, SIG_KMS_KEY, SIG_COSIGN_KEY_URI (derived in config.sh),
# SIG_SECB_STATE_DIR, SIG_SECB_AUTHOR (required on apply — the recorded
# operator id, OM-20 scope discipline), SIG_SECB_SIGNING (=1 arms the
# deploy-path hook), SIG_SECB_NOW (test-only clock override).
#
# Live window (the ticket's `AR-3 + AR-2` cell): applies never run inside
# 03:00–10:00Z — exit 42 QUEUED; SIG_SECB_AUTHOR records the operator.
# Check mode needs nothing: no project, no ADC — every line says what runs.
#
# Rerun prompt (GATE-G6 §4 names P37.4a verbatim, expiry GATE-ACCEPT-R11):
#   SIG_SECB_AUTHOR="$(git config user.name)" \
#   bash ops/gcp/security-baseline.sh --apply all
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
  prestate|apis|kms|sign|probe|verify|rollback|all) ;;
  *) echo "security-baseline.sh: unknown action '${ACTION}'" >&2; _usage ;;
esac
STATE_DIR="${SIG_SECB_STATE_DIR}"
RERUN='SIG_SECB_AUTHOR="$(git config user.name)" bash ops/gcp/security-baseline.sh --apply '"${ACTION}"

die() { _log "ERROR: $*" >&2; exit 4; }

_secb_now() { printf '%s' "${SIG_SECB_NOW:-$(date -u +%Y-%m-%dT%H:%M:%SZ)}"; }

assert_window() {
  [ "${SIG_GCP_MODE}" = "apply" ] || return 0
  local nowiso hhmm
  nowiso="$(_secb_now)"
  hhmm="${nowiso:11:5}"
  if [[ "${hhmm}" > "02:59" && "${hhmm}" < "10:00" ]]; then
    _log "QUEUED (exit 42): ${nowiso} is inside 03:00-10:00Z — never mutate then (AR-3)."
    _log "re-run: ${RERUN}"
    exit 42
  fi
  if [ -z "${SIG_SECB_AUTHOR}" ]; then
    _log "ERROR: set SIG_SECB_AUTHOR to the recorded operator id (OM-20's scope discipline)" >&2
    exit 2
  fi
}

_sha_sidecar() {  # _sha_sidecar FILE — write FILE.sha256 with the file's digest
  [ -f "$1" ] && (cd "$(dirname "$1")" && shasum -a 256 "$(basename "$1")" > "$1.sha256") || true
}

_live_digest() {  # _live_digest KIND NAME — describe a service|job → its image ref
  local kind="$1" name="$2"
  if [ "${kind}" = "service" ]; then
    gcloud run services describe "${name}" --project "${SIG_GCP_PROJECT}" \
      --region "${SIG_GCP_REGION}" \
      --format='value(spec.template.spec.containers[0].image)'
  else
    gcloud run jobs describe "${name}" --project "${SIG_GCP_PROJECT}" \
      --region "${SIG_GCP_REGION}" \
      --format='value(spec.template.spec.template.spec.containers[0].image)'
  fi
}

_deployed_digests() {  # the digest refs this leg signs (service + job images)
  local d
  for pair in "service:${SIG_RUN_SERVICE}" "service:${SIG_WEB_SERVICE}" "job:${SIG_RELEASE_JOB}"; do
    d="$(_live_digest "${pair%%:*}" "${pair##*:}" 2>/dev/null || true)"
    [ -n "${d}" ] && printf '%s\n' "${d}"
  done
}

plan() {
  cat <<EOF
PLAN: security-baseline (${ACTION}) — project ${SIG_GCP_PROJECT} region ${SIG_GCP_REGION}
PLAN: apis        enable containeranalysis/containerscanning/ondemandscanning/cloudkms
PLAN: kms         keyring ${SIG_KMS_RING} @ ${SIG_KMS_LOCATION}, key ${SIG_KMS_KEY_NAME}
                  (asymmetric-signing ec-sign-p256-sha256, protection hsm —
                  key material never leaves GCP; verify via the public key)
PLAN: sign        cosign sign --yes --key ${SIG_COSIGN_KEY_URI} <digest>
                  for every deployed digest (sig-api, sig-web, ${SIG_RELEASE_JOB})
                  then cosign verify; record sig.image-signature/1 →
                  ${SIG_SECB_RECORD_PREFIX}<ts>.json on the release bucket
PLAN: deploy wiring  lib.sh security_sign_image — web.sh signs every digest it
                  deploys while SIG_SECB_SIGNING=1 (unarmed prints the pending commands)
PLAN: sbom        sbom.cdx.json (CycloneDX 1.5 over pylock.toml) ships in every
                  export, covered by SHA256SUMS + the pipeline signature, bound
                  into releases/<pub>/data/ — SBOM and signature per release
PLAN: probe       cosign verify finds ≥1 signature per deployed digest (MUST hold)
PLAN: legs        prestate -> AR-2 -> apis -> kms -> sign -> probe -> verify
PLAN: apply needs SIG_SECB_AUTHOR, SIG_GCP_PROJECT, ADC, cosign on PATH;
                  window: never 03:00-10:00Z
PLAN: rerun       ${RERUN}
EOF
}

do_prestate() {
  _log "-- prestate: enabled APIs + KMS + live digests --"
  if [ "${SIG_GCP_MODE}" = "check" ]; then
    _plan "gcloud services list --enabled > ${STATE_DIR}/services.json"
    _plan "gcloud kms keyrings list --location ${SIG_KMS_LOCATION} > ${STATE_DIR}/keyrings.json"
    _plan "describe sig-api/sig-web/${SIG_RELEASE_JOB} image digests > ${STATE_DIR}/digests.json"
    _plan "ops/gcp/restore-point.sh --apply sqlpoint   # AR-2"
    return 0
  fi
  mkdir -p "${STATE_DIR}"
  run gcloud services list --enabled --project "${SIG_GCP_PROJECT}" \
    --format=json > "${STATE_DIR}/services.json" || true
  run gcloud kms keyrings list --project "${SIG_GCP_PROJECT}" \
    --location "${SIG_KMS_LOCATION}" --format=json > "${STATE_DIR}/keyrings.json" || true
  _deployed_digests > "${STATE_DIR}/digests.txt" || true
  _sha_sidecar "${STATE_DIR}/services.json"
  _sha_sidecar "${STATE_DIR}/digests.txt"
  bash "${_here}/restore-point.sh" --apply sqlpoint || \
    _log "note: restore-point sqlpoint unavailable — prestate still recorded"
}

do_apis() {
  _log "-- apis: scanning + KMS APIs on ${SIG_GCP_PROJECT} --"
  local api
  for api in containeranalysis.googleapis.com containerscanning.googleapis.com \
             ondemandscanning.googleapis.com cloudkms.googleapis.com; do
    run gcloud services enable "${api}" --project "${SIG_GCP_PROJECT}"
  done
}

do_kms() {
  _log "-- kms: ${SIG_KMS_RING} @ ${SIG_KMS_LOCATION} + ${SIG_KMS_KEY_NAME} --"
  run gcloud kms keyrings create "${SIG_KMS_RING}" \
    --project "${SIG_GCP_PROJECT}" --location "${SIG_KMS_LOCATION}"
  run gcloud kms keys create "${SIG_KMS_KEY_NAME}" \
    --project "${SIG_GCP_PROJECT}" --location "${SIG_KMS_LOCATION}" \
    --keyring "${SIG_KMS_RING}" --purpose asymmetric-signing \
    --default-algorithm ec-sign-p256-sha256 --protection-level hsm
  if [ "${SIG_GCP_MODE}" = "check" ]; then
    _plan "cosign public-key --key ${SIG_COSIGN_KEY_URI} > ${STATE_DIR}/sig-image-sign.pub"
  else
    mkdir -p "${STATE_DIR}"
    cosign public-key --key "${SIG_COSIGN_KEY_URI}" > "${STATE_DIR}/sig-image-sign.pub"
    _sha_sidecar "${STATE_DIR}/sig-image-sign.pub"
  fi
}

do_sign() {
  _log "-- sign: cosign every deployed digest + record --"
  if [ "${SIG_GCP_MODE}" = "check" ]; then
    _plan "for d in \$(deployed digests): cosign sign --yes --key ${SIG_COSIGN_KEY_URI} \$d && cosign verify ..."
    _plan "gcloud storage cp sig.image-signature-*.json gs://${SIG_BUCKET_RELEASE}/${SIG_SECB_RECORD_PREFIX}"
    return 0
  fi
  command -v cosign >/dev/null 2>&1 || die "cosign not on PATH — sign needs the cosign binary"
  local ts digest out
  ts="$(date -u +%Y%m%dT%H%M%SZ)"
  while IFS= read -r digest; do
    [ -z "${digest}" ] && continue
    run cosign sign --yes --key "${SIG_COSIGN_KEY_URI}" "${digest}"
    run cosign verify --key "${SIG_COSIGN_KEY_URI}" "${digest}" \
      --insecure-ignore-tlog --insecure-ignore-sct
    out="${STATE_DIR}/sig.image-signature-${ts}-$(printf '%s' "${digest}" | sha256sum | cut -c1-12).json"
    (cd "${_repo}" && uv run --quiet sig-ops security-baseline sign \
      --image "${digest}" --project "${SIG_GCP_PROJECT}" \
      --key-uri "${SIG_COSIGN_KEY_URI}" --record "${out}" --apply) || \
      _log "note: record emit skipped for ${digest}"
    _sha_sidecar "${out}"
    run gcloud storage cp "${out}" \
      "gs://${SIG_BUCKET_RELEASE}/${SIG_SECB_RECORD_PREFIX}"
  done < "${STATE_DIR}/digests.txt"
}

do_probe() {
  _log "-- probe: ≥1 signature per deployed digest + scanning API live --"
  if [ "${SIG_GCP_MODE}" = "check" ]; then
    _plan "cosign verify --key ${SIG_COSIGN_KEY_URI} <digest>  # per digest, MUST find ≥1 signature"
    _plan "gcloud services list --enabled | grep containerscanning"
    return 0
  fi
  local digest bad=0
  while IFS= read -r digest; do
    [ -z "${digest}" ] && continue
    if cosign verify --key "${SIG_COSIGN_KEY_URI}" "${digest}" \
        --insecure-ignore-tlog --insecure-ignore-sct >/dev/null 2>&1; then
      _log "ok signature ${digest}"
    else
      _log "PROBE-FAIL: no signature for ${digest}"
      bad=1
    fi
  done < "${STATE_DIR}/digests.txt"
  gcloud services list --enabled --project "${SIG_GCP_PROJECT}" \
    --format='value(config.name)' | grep -q containerscanning.googleapis.com || \
    { _log "PROBE-FAIL: containerscanning API not enabled"; bad=1; }
  [ "${bad}" = 0 ] || die "probe found unsigned digests or a missing API"
  _log "ok probe — every deployed digest carries a baseline signature"
}

do_verify() {
  _log "-- verify: APIs + key + signature objects --"
  run gcloud kms keys describe "${SIG_KMS_KEY_NAME}" \
    --project "${SIG_GCP_PROJECT}" --location "${SIG_KMS_LOCATION}" \
    --keyring "${SIG_KMS_RING}" --format='value(primary.state,purpose)'
  run gcloud services list --enabled --project "${SIG_GCP_PROJECT}" \
    --filter='config.name:(containeranalysis OR containerscanning OR cloudkms)' \
    --format='value(config.name)'
  _log "verify: sig.image-signature/1 records under ${STATE_DIR} + gs://${SIG_BUCKET_RELEASE}/${SIG_SECB_RECORD_PREFIX}"
}

do_rollback() {
  _log "-- rollback (printed; the leg's writes are additive — never deleted) --"
  _log "  un-arm the deploy hook: export SIG_SECB_SIGNING=0"
  _log "  disable the key version: gcloud kms keys versions disable 1 \\"
  _log "    --key ${SIG_KMS_KEY_NAME} --keyring ${SIG_KMS_RING} --location ${SIG_KMS_LOCATION}"
  _log "  signature objects stay — append-only attestation history (P1-P3)"
}

require_project
case "${ACTION}" in
  apis|kms|sign|all) assert_window ;;
esac
require_adc

banner "P37.4a — security baseline: scan + SBOM + cosign (ADR-231)"

case "${ACTION}" in
  prestate)  do_prestate ;;
  apis)      do_apis ;;
  kms)       do_kms ;;
  sign)      do_sign ;;
  probe)     do_probe ;;
  verify)    do_verify ;;
  rollback)  do_rollback ;;
  all)
    plan
    do_prestate
    do_apis
    do_kms
    do_sign
    do_probe
    do_verify ;;
esac

_log "security-baseline ${ACTION}: done (mode=${SIG_GCP_MODE})"
