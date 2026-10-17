#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
#
# ops/gcp/export.sh — build the NATIONAL export next to the hosted spine (P30.3 / GO-LIVE.3,
# D-P27.4-1 + D-R6.5-SURFACE, ADR-106). `sig-exports build --from-spine` reads the whole
# materialized spine inside ONE `REPEATABLE READ READ ONLY` snapshot (no write, no
# UPDATE/DELETE); at national scale (~2.3M claims / ~230k camera records) it needs several GB
# of RAM, so — like the P30.2 materializers (ADR-103) — it runs as a Cloud Run job execution
# next to Cloud SQL and writes the bundle into the PRIVATE restricted bucket (a gcsfuse
# volume). The operator then fetches it to `exports/out/national` for the public prepare
# (`sig-ops deploy --target gcp --prepare-only`), which partitions it + proves it clean.
#
#   ./export.sh --check [action]        # (default) plan-only: needs NO ADC, opens NO network.
#   ./export.sh --apply <action>        # operator-gated (ADC): applies for real.
#
# Actions (idempotent, safe to repeat):
#   image     Cloud Build `sig-api:export-<sha>` from `git archive HEAD` (never retags :latest).
#   job       upsert the `sig-export` Cloud Run job on that image (Cloud SQL socket, Secret
#             Manager password, 4 CPU / 16 GiB, restricted bucket mounted at /mnt/restricted).
#   run       execute one export; SIG_EXPORT_AS_OF (default: now, UTC) names the snapshot and
#             the output prefix gs://<restricted>/exports/national/<as-of>/.
#   fetch     copy that prefix down to exports/out/national (SIG_EXPORT_AS_OF required).
#   all       image → job → run (waits).
#
# The DSN is assembled INSIDE the container from $SIG_PG_PASSWORD (Secret Manager) — never on
# a command line here (HG-09). The job connects as `sig` in a READ ONLY session.
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

banner "national export next to the spine (P30.3 / GO-LIVE.3)"

: "${SIG_EXPORT_JOB:=sig-export}"
: "${SIG_EXPORT_AS_OF:=$(date -u +%Y-%m-%dT%H:%M:%SZ)}"
: "${SIG_EXPORT_NOTE:=P30.3 national launch export — settled materialized hosted spine}"
# P35.12 / SIG-REL-001+003 (G3 §3.2/§3.3): the belief instant is now propagated
# (snapshot.as_of_belief / belief_pinned ride the export manifest into the v2
# descriptor); the declared environment defaults to production; SIG_EXPORT_REPLAY
# declares a Class-S rebuild of a historical snapshot (required for an earlier-day
# as-of); SIG_EXPORT_EMERGENCY lifts the AR-3 frozen-window refusal with a
# recorded reason. The §3.3 clock guards (frozen window, host clock, future
# as-of) bind inside `sig-exports build --from-spine` itself — a Cloud Run start
# hours after this stamp is a same-day lag, never a replay claim.
: "${SIG_EXPORT_BELIEF:=}"
: "${SIG_EXPORT_ENVIRONMENT:=production}"
: "${SIG_EXPORT_REPLAY:=}"
: "${SIG_EXPORT_EMERGENCY:=}"
# P35.19 / JUR-02b (placement@1, ADR-092): paths to a staged
# sig.boundary-pack/1 directory + its bound sig.jurisdiction-registry/1 —
# typically under the restricted mount. Both unset → the export runs with no
# placement (byte-identical to the pre-placement posture); exactly one set →
# the CLI refuses (a half-staged placement input is never silently placed).
: "${SIG_EXPORT_BOUNDARY_PACK:=}"
: "${SIG_EXPORT_JURISDICTION_REGISTRY:=}"
: "${SIG_EXPORT_BOUNDARY_SPEC:=}"
_repo="$(cd "${_here}/../.." && pwd)"
_sha="$(git -C "${_repo}" rev-parse --short=12 HEAD 2>/dev/null || echo unknown)"
IMAGE="${SIG_API_IMAGE}:export-${_sha}"
CONN="${SIG_GCP_PROJECT}:${SIG_GCP_REGION}:${SIG_SQL_INSTANCE}"
MOUNT="/mnt/restricted"
PREFIX="exports/national/$(printf %s "${SIG_EXPORT_AS_OF}" | tr -d :)"   # colon-free object prefix
JOB_ENV="SIG_PG_USER=sig,SIG_PG_DB=${SIG_PG_DB_NAME:-sig},SIG_CLOUDSQL_CONNECTION=${CONN}"

# The in-container command (expanded by the container's `sh -c`, NOT here — single quotes
# around the DSN). As-of + note are plain labels, not secrets.
# shellcheck disable=SC2016
DSN='postgresql://${SIG_PG_USER}:${SIG_PG_PASSWORD}@/${SIG_PG_DB}?host=/cloudsql/${SIG_CLOUDSQL_CONNECTION}'
export_cmd() {
  local extra=""
  [ -n "${SIG_EXPORT_BELIEF}" ] && extra="${extra} --belief \"${SIG_EXPORT_BELIEF}\""
  [ -n "${SIG_EXPORT_REPLAY}" ] && extra="${extra} --replay \"${SIG_EXPORT_REPLAY}\""
  [ -n "${SIG_EXPORT_EMERGENCY}" ] && extra="${extra} --emergency \"${SIG_EXPORT_EMERGENCY}\""
  [ -n "${SIG_EXPORT_BOUNDARY_PACK}" ] && extra="${extra} --boundary-pack \"${SIG_EXPORT_BOUNDARY_PACK}\""
  [ -n "${SIG_EXPORT_JURISDICTION_REGISTRY}" ] && extra="${extra} --jurisdiction-registry \"${SIG_EXPORT_JURISDICTION_REGISTRY}\""
  [ -n "${SIG_EXPORT_BOUNDARY_SPEC}" ] && extra="${extra} --boundary-spec \"${SIG_EXPORT_BOUNDARY_SPEC}\""
  printf 'exec python -m exports build --from-spine --dsn "%s" --as-of "%s" --environment "%s" --note "%s" --out "%s/%s"%s' \
    "${DSN}" "${SIG_EXPORT_AS_OF}" "${SIG_EXPORT_ENVIRONMENT}" "${SIG_EXPORT_NOTE}" "${MOUNT}" "${PREFIX}" "${extra}"
}

# SIG_EXPORT_GUARD (config.sh) — P35.1b (G1-NEW-4 keep-list): the job's BAKED
# args are a refusal, not an export — `export.sh run` always overrides args at
# execute time, so a bare `gcloud run jobs execute sig-export` exits 64 instead
# of running a stale --as-of baked at deploy time. fleet-sweep.sh's
# export-guard leg rolls the same string to the live job.

do_image() {
  _log "-- image: Cloud Build ${IMAGE} from git archive HEAD (never retags :latest)"
  if [ "${SIG_GCP_MODE}" = "check" ]; then
    _plan "git archive --format=tar.gz HEAD > <tmp>/ctx.tgz && gcloud builds submit <tmp>/ctx.tgz --config <tmp>/cloudbuild.yaml   # docker build -f ops/Dockerfile -t ${IMAGE}"
    return 0
  fi
  local tmp
  tmp="$(mktemp -d)"
  git -C "${_repo}" archive --format=tar.gz HEAD > "${tmp}/ctx.tgz"
  cat > "${tmp}/cloudbuild.yaml" <<YAML
steps:
- name: gcr.io/cloud-builders/docker
  args: ["build", "-f", "ops/Dockerfile", "-t", "${IMAGE}", "."]
images: ["${IMAGE}"]
timeout: 3600s
YAML
  run gcloud builds submit "${tmp}/ctx.tgz" --config "${tmp}/cloudbuild.yaml" \
    --project "${SIG_GCP_PROJECT}" --region "${SIG_GCP_REGION}"
  rm -rf "${tmp}"
}

do_job() {
  _log "-- job: upsert ${SIG_EXPORT_JOB} on ${IMAGE} (restricted bucket at ${MOUNT}, PRIVATE)"
  # P31.4 / ADR-111: the job runs the build's pinned digest, never a movable tag.
  # P35.1b: the baked args are a REFUSED exit-64 guard, not a baked export —
  # the deployed args previously pinned a stale --as-of at deploy time; the
  # real args arrive from `export.sh run`'s `--args` override at execute time,
  # so a bare/accidental execution is a recorded no-op (the sig-replay-ingest
  # pattern, scheduled-ops.sh). EXPORT_GUARD_ARGS is the single source the
  # sweep's guard-roll leg asserts.
  local pinned
  pinned="$(pin_image_digest "${IMAGE}")"
  _log "   pinned: ${pinned}"
  run gcloud run jobs deploy "${SIG_EXPORT_JOB}" \
    --image "${pinned}" --region "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}" \
    --service-account "${SIG_SA_EXPORT}@${SIG_GCP_PROJECT}.iam.gserviceaccount.com" \
    --command sh --args "-c,${SIG_EXPORT_GUARD}" \
    --tasks 1 --task-timeout 4h --max-retries 0 --cpu 4 --memory 16Gi \
    --execution-environment gen2 \
    --add-volume "name=restricted,type=cloud-storage,bucket=${SIG_BUCKET_RESTRICTED}" \
    --add-volume-mount "volume=restricted,mount-path=${MOUNT}" \
    --set-cloudsql-instances "${CONN}" \
    --set-env-vars "${JOB_ENV}" \
    --set-secrets "SIG_PG_PASSWORD=${SIG_SECRET_PG_PASSWORD}:latest"
}

do_run() {
  local mode="${1:---wait}"
  _log "-- run: export as-of ${SIG_EXPORT_AS_OF} → gs://${SIG_BUCKET_RESTRICTED}/${PREFIX}/"
  run gcloud run jobs execute "${SIG_EXPORT_JOB}" \
    --region "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}" \
    --args "-c,$(export_cmd)" "${mode}"
}

do_fetch() {
  _log "-- fetch: gs://${SIG_BUCKET_RESTRICTED}/${PREFIX}/ → ${SIG_EXPORT_DIR}/national"
  run mkdir -p "${_repo}/${SIG_EXPORT_DIR}/national"
  run gcloud storage rsync -r "gs://${SIG_BUCKET_RESTRICTED}/${PREFIX}" \
    "${_repo}/${SIG_EXPORT_DIR}/national" --project "${SIG_GCP_PROJECT}"
}

case "${ACTION}" in
  image) do_image ;;
  job)   do_job ;;
  run)   do_run ;;
  fetch) do_fetch ;;
  all)
    do_image
    do_job
    do_run --wait ;;
  *) _log "usage: $(basename "$0") [--check|--apply] [image|job|run|fetch|all]" >&2; exit 64 ;;
esac

_log "export ${ACTION}: check OK (mode=${SIG_GCP_MODE})"
