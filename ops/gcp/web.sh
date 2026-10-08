#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
#
# ops/gcp/web.sh — the FIRST repo-owned `sig-web` deploy path (P31.15 / SURFACE.2,
# ADR-R9-TILES). The live service was set up by hand in P30.3 — stock
# `nginx:1.27-alpine` + a gcsfuse volume on the <project>-sig-web bucket —
# "the bucket sync IS the deploy" (docs/build/runs/P30.3.md). This script rolls
# the service onto the repo-owned image (ops/web/Dockerfile: nginx + compiled
# Brotli + the repo-owned nginx.conf — gzip/brotli text compression, the real
# PMTiles media type, byte-range serving) deployed by PINNED DIGEST via
# `pin_image_digest` (ADR-111), never `:latest`.
#
#   ./web.sh --check [action]   # (default) plan-only: needs NO ADC, opens NO network.
#   ./web.sh --apply <action>   # operator-gated (ADC): applies for real.
#
# Actions (idempotent):
#   image     Cloud Build `sig-web:<git-sha>` from ops/web/ + the repo context
#             (never retags :latest).
#   service   upsert the `sig-web` Cloud Run service on the pinned digest. The
#             hand-made service shape is READ LIVE first (the ticket's contract:
#             "read live and reproduced, not guessed") — the describe output is
#             logged for the record. The live shape P31.16 measured is volume
#             `site` (gcsfuse <project>-sig-web) mounted at
#             /usr/share/nginx/html on port 80, while the repo-owned image
#             serves /mnt/sig-web on 8080 — so the deploy removes every live
#             volume-mount + volume by its LIVE name/path (never a guessed one)
#             and re-declares the gcsfuse volume (<project>-sig-web →
#             /mnt/sig-web) with unauthenticated access and the recorded
#             ingress. Settings this script does not own (scaling, concurrency,
#             env) are left at the live values — a deploy updates only what the
#             flags name.
#   describe  print the live service spec (the read-live record; check mode plans it).
#   all       image → service
#
# P31.15 builds + tests this path; the actual roll is P31.16's (--apply).
set -euo pipefail

_here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=ops/gcp/config.sh
. "${_here}/config.sh"
# shellcheck source=ops/gcp/lib.sh
. "${_here}/lib.sh"

parse_mode "${1:-}"
shift || true
ACTION="${1:-all}"
require_project
# config.sh derived SIG_WEB_SA_EMAIL + SIG_BUCKET_WEB before require_project
# filled the check-mode placeholder — re-derive so PLANs name real resources.
export SIG_WEB_SA_EMAIL="${SIG_SA_WEB}@${SIG_GCP_PROJECT}.iam.gserviceaccount.com"
export SIG_BUCKET_WEB="${SIG_GCP_PROJECT}-sig-web"
require_adc

banner "sig-web repo-owned image + deploy (P31.15 / SURFACE.2)"

_repo="$(cd "${_here}/../.." && pwd)"
_sha="$(git -C "${_repo}" rev-parse --short=12 HEAD 2>/dev/null || echo unknown)"
IMAGE="${SIG_AR_HOST}/${SIG_GCP_PROJECT}/${SIG_AR_REPO}/sig-web:${_sha}"
MOUNT="/mnt/sig-web"
VOLUME_NAME="sig-web"

do_image() {
  _log "-- image: Cloud Build ${IMAGE} from git archive HEAD (never retags :latest)"
  if [ "${SIG_GCP_MODE}" = "check" ]; then
    _plan "git archive --format=tar.gz HEAD > <tmp>/ctx.tgz && gcloud builds submit <tmp>/ctx.tgz --config <tmp>/cloudbuild.yaml   # docker build -f ops/web/Dockerfile -t ${IMAGE}"
    return 0
  fi
  local tmp
  tmp="$(mktemp -d)"
  git -C "${_repo}" archive --format=tar.gz HEAD > "${tmp}/ctx.tgz"
  cat > "${tmp}/cloudbuild.yaml" <<YAML
steps:
- name: gcr.io/cloud-builders/docker
  args: ["build", "-f", "ops/web/Dockerfile", "-t", "${IMAGE}", "."]
images: ["${IMAGE}"]
timeout: 3600s
YAML
  run gcloud builds submit "${tmp}/ctx.tgz" --config "${tmp}/cloudbuild.yaml" \
    --project "${SIG_GCP_PROJECT}" --region "${SIG_GCP_REGION}"
  rm -rf "${tmp}"
}

do_describe() {
  _log "-- describe: the live ${SIG_WEB_SERVICE} service spec (read live, reproduced — never guessed)"
  run gcloud run services describe "${SIG_WEB_SERVICE}" \
    --region "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}" --format yaml
}

do_service() {
  do_describe
  _log "-- service: upsert ${SIG_WEB_SERVICE} on ${IMAGE} (gcsfuse ${SIG_BUCKET_WEB} → ${MOUNT})"
  # P31.4 / ADR-111: the service runs the build's pinned digest, never a movable tag.
  local pinned
  pinned="$(pin_image_digest "${IMAGE}")"
  _log "   pinned: ${pinned}"
  # Reproduce-and-replace the live mount shape — READ LIVE, never guessed. The
  # hand-made P30.3 service mounts the same bucket as volume `site` at
  # /usr/share/nginx/html on port 80; the repo-owned image serves /mnt/sig-web
  # on 8080. Every CURRENT volume-mount and volume is removed by its live
  # path/name, then the target gcsfuse volume + mount are declared — the repo's
  # remove+add idempotent volume convention (scheduled-ops.sh) applied to the
  # shape the service ACTUALLY has, so a roll is clean on first run and on
  # re-roll and can never strand a stale mount definition. Ingress + auth match
  # the LB→NEG + run.app reachability the live service has; scaling/env the
  # script does not own are left at the live values.
  local -a rm_args=()
  if [ "${SIG_GCP_MODE}" = "apply" ]; then
    local spec_json
    spec_json="$(gcloud run services describe "${SIG_WEB_SERVICE}" \
      --region "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}" --format json)"
    local mp vn
    while IFS= read -r mp; do
      [ -n "${mp}" ] && rm_args+=(--remove-volume-mount "${mp}")
    done < <(printf '%s' "${spec_json}" | python3 -c 'import json,sys
s = json.load(sys.stdin)
for c in s["spec"]["template"]["spec"].get("containers", []):
    for m in c.get("volumeMounts", []):
        print(m["mountPath"])')
    while IFS= read -r vn; do
      [ -n "${vn}" ] && rm_args+=(--remove-volume "${vn}")
    done < <(printf '%s' "${spec_json}" | python3 -c 'import json,sys
s = json.load(sys.stdin)
for v in s["spec"]["template"]["spec"].get("volumes", []):
    print(v["name"])')
    _log "   live mounts/volumes to replace: ${rm_args[*]:-none}"
  else
    _plan "remove every live volume-mount + volume by its live path/name (the describe above), then:"
  fi
  # `${rm_args[@]+...}` guards the empty array under bash 3.2 `set -u`.
  # P34.42a / AR-8: sig-web runs as its own identity (sig-web-rt — created by
  # the IAM leg ops/gcp/iam-service-accounts.sh, which must land before any
  # roll that names it).
  run gcloud run deploy "${SIG_WEB_SERVICE}" \
    --image "${pinned}" --region "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}" \
    --service-account "${SIG_WEB_SA_EMAIL}" \
    --port 8080 \
    --ingress all --allow-unauthenticated \
    ${rm_args[@]+"${rm_args[@]}"} \
    --add-volume "name=${VOLUME_NAME},type=cloud-storage,bucket=${SIG_BUCKET_WEB}" \
    --add-volume-mount "volume=${VOLUME_NAME},mount-path=${MOUNT}"
}

case "${ACTION}" in
  image)    do_image ;;
  service)  do_service ;;
  describe) do_describe ;;
  all)
    do_image
    do_service ;;
  *) _log "usage: $(basename "$0") [--check|--apply] [image|service|describe|all]" >&2; exit 64 ;;
esac

_log "web ${ACTION}: check OK (mode=${SIG_GCP_MODE})"
