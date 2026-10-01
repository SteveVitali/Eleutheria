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
#             logged for the record; the deploy then re-declares the gcsfuse
#             volume (<project>-sig-web → /mnt/sig-web), unauthenticated access,
#             and the recorded ingress. Settings this script does not own
#             (scaling, concurrency, env) are left at the live values — a deploy
#             updates only what the flags name.
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
  # Reproduce the P30.3 hand-made shape: the gcsfuse volume is re-declared
  # (remove+add is the repo's idempotent volume convention, scheduled-ops.sh) so a
  # roll can never strand a stale mount definition; ingress + auth match the
  # LB→NEG + run.app reachability the live service has. Scaling/env the script
  # does not own are left at the live values.
  run gcloud run deploy "${SIG_WEB_SERVICE}" \
    --image "${pinned}" --region "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}" \
    --port 8080 \
    --ingress all --allow-unauthenticated \
    --remove-volume-mount "${MOUNT}" --remove-volume "${VOLUME_NAME}" \
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
