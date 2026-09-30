#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
#
# ops/gcp/materialize.sh — the hosted Round-6 materialization run (P30.2 / GO-LIVE.2,
# ADR-103): deploy the Round-6 sqitch changes + the least-privilege `sig_materialize`
# role, then run every materializer + the P29.2 detector research queue as Cloud Run
# job executions NEXT TO the Cloud SQL spine (the write path is latency-bound — row-at-a-
# time round-trips — so it must not run over a WAN cloud-sql-proxy, P30.1 lesson).
#
#   ./materialize.sh --check [action]   # (default) plan-only: prints every action,
#                                       # needs NO ADC, opens NO network, exits 0.
#   ./materialize.sh --apply <action>   # operator-gated (ADC): applies for real.
#
# Actions (run in this order; each is idempotent and safe to repeat):
#   schema          sqitch deploy db/sqitch.plan to the hosted spine AS THE SCHEMA OWNER
#                   (`sig`) over a running cloud-sql-proxy on 127.0.0.1:$SIG_PROXY_PORT
#                   (the sqitch Docker image; password from Secret Manager into env only).
#                   Lands the six Round-6 changes + `materialize_role` (creates
#                   sig_materialize: READ via sig_read_public, INSERT-only on the
#                   materialized tables, no UPDATE/DELETE, no spine write).
#   image           Cloud Build the image from `git archive HEAD` → tag
#                   `sig-api:materialize-<sha>` (never retags :latest — the API service
#                   and the ingest jobs keep their image).
#   job             upsert the `sig-materialize` Cloud Run job on that image (Cloud SQL
#                   socket, Secret Manager password, 4 CPU / 16 GiB, 24h task timeout,
#                   max-retries 0).
#   run <step>      execute one step as a job execution with an --args override, where
#                   <step> ∈ resolution | edges | contradictions | coverage |
#                   accountability | detect. Every step connects as `sig` and runs
#                   `--role sig_materialize`; the DSN is assembled INSIDE the container
#                   from $SIG_PG_PASSWORD (Secret Manager) — never on a command line here.
#   all             schema → image → job → run each step in dependency order.
#
# SIG_DETECT_JURISDICTION (optional, e.g. OK) routes the detector's records-request DRAFTS to
# that state's records statute. The loop applies it to EVERY records-oriented task, so set it
# only when the whole queue is that jurisdiction's (P30.2: the single queued task is the OKC
# 299-vs-190 contradiction); unset, no draft is made. Drafts are never sent (D-R7.2-SEND).
#
# Coverage runs with --no-negative-space: on the hosted spine every entity is typed
# `deployment`, so the P28.4 peer-class rule would emit ~26.7M `not_researched` rows
# (ADR-103; the refinement is the follow-up D-P30.2-1). Nothing here UPDATEs/DELETEs.
set -euo pipefail

_here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=ops/gcp/config.sh
. "${_here}/config.sh"
# shellcheck source=ops/gcp/lib.sh
. "${_here}/lib.sh"

parse_mode "${1:-}"
shift || true
ACTION="${1:-all}"
STEP="${2:-}"
require_project
require_adc

banner "hosted Round-6 materialization (P30.2 / GO-LIVE.2)"

: "${SIG_MATERIALIZE_JOB:=sig-materialize}"
: "${SIG_MATERIALIZE_ROLE:=sig_materialize}"
: "${SIG_PROXY_PORT:=5433}"
_repo="$(cd "${_here}/../.." && pwd)"
_sha="$(git -C "${_repo}" rev-parse --short=12 HEAD 2>/dev/null || echo unknown)"
IMAGE="${SIG_API_IMAGE}:materialize-${_sha}"
CONN="${SIG_GCP_PROJECT}:${SIG_GCP_REGION}:${SIG_SQL_INSTANCE}"
JOB_ENV="SIG_PG_USER=sig,SIG_PG_DB=${SIG_PG_DB_NAME:-sig},SIG_CLOUDSQL_CONNECTION=${CONN}"

# The in-container DSN (expanded by the container's `sh -c`, NOT here — single quotes).
# shellcheck disable=SC2016
DSN='postgresql://${SIG_PG_USER}:${SIG_PG_PASSWORD}@/${SIG_PG_DB}?host=/cloudsql/${SIG_CLOUDSQL_CONNECTION}'

# step -> the CLI the container execs (every one append-only + idempotent, +0 on re-run).
step_cmd() {
  local role="--role ${SIG_MATERIALIZE_ROLE}"
  case "$1" in
    resolution)     printf 'exec python -m reconcile materialize --dsn "%s" %s' "${DSN}" "${role}" ;;
    edges)          printf 'exec python -m reconcile materialize-edges --dsn "%s" %s' "${DSN}" "${role}" ;;
    contradictions) printf 'exec python -m reconcile materialize-contradictions --dsn "%s" %s' "${DSN}" "${role}" ;;
    coverage)       printf 'exec python -m inference materialize-coverage --dsn "%s" %s --no-negative-space' "${DSN}" "${role}" ;;
    accountability) printf 'exec python -m inference materialize-accountability-links --dsn "%s" %s' "${DSN}" "${role}" ;;
    detect)         printf 'exec python -m tasks detect --dsn "%s" %s%s' "${DSN}" "${role}" \
                      "${SIG_DETECT_JURISDICTION:+ --jurisdiction ${SIG_DETECT_JURISDICTION}}" ;;
    *) _log "ERROR: unknown step '$1' (resolution|edges|contradictions|coverage|accountability|detect)" >&2; exit 64 ;;
  esac
}
STEPS="resolution edges contradictions coverage accountability detect"

do_schema() {
  _log "-- schema: sqitch deploy (as the schema owner, over cloud-sql-proxy :${SIG_PROXY_PORT})"
  if [ "${SIG_GCP_MODE}" = "check" ]; then
    _plan "SQITCH_PASSWORD=\$(gcloud secrets versions access latest --secret=${SIG_SECRET_PG_PASSWORD}) docker run --rm -e SQITCH_PASSWORD -v db:/repo sqitch/sqitch:latest deploy --verify db:pg://sig@host.docker.internal:${SIG_PROXY_PORT}/sig"
    return 0
  fi
  SQITCH_PASSWORD="$(gcloud secrets versions access latest \
    --secret="${SIG_SECRET_PG_PASSWORD}" --project "${SIG_GCP_PROJECT}")"
  export SQITCH_PASSWORD
  run docker run --rm -e SQITCH_PASSWORD -v "${_repo}/db:/repo" -w /repo sqitch/sqitch:latest \
    deploy --verify "db:pg://sig@host.docker.internal:${SIG_PROXY_PORT}/sig"
  unset SQITCH_PASSWORD
}

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
  _log "-- job: upsert ${SIG_MATERIALIZE_JOB} on ${IMAGE}"
  run gcloud run jobs deploy "${SIG_MATERIALIZE_JOB}" \
    --image "${IMAGE}" --region "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}" \
    --command sh --args "-c,$(step_cmd resolution)" \
    --tasks 1 --task-timeout 24h --max-retries 0 --cpu 4 --memory 16Gi \
    --set-cloudsql-instances "${CONN}" \
    --set-env-vars "${JOB_ENV}" \
    --set-secrets "SIG_PG_PASSWORD=${SIG_SECRET_PG_PASSWORD}:latest"
}

do_run() {
  local step="$1" mode="${2:---async}"
  _log "-- run: ${step} as ${SIG_MATERIALIZE_ROLE} (Cloud Run execution next to the DB)"
  run gcloud run jobs execute "${SIG_MATERIALIZE_JOB}" \
    --region "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}" \
    --args "-c,$(step_cmd "${step}")" "${mode}"
}

case "${ACTION}" in
  schema) do_schema ;;
  image)  do_image ;;
  job)    do_job ;;
  run)
    [ -n "${STEP}" ] || { _log "usage: $(basename "$0") --apply run <step>" >&2; exit 64; }
    do_run "${STEP}" ;;
  all)
    do_schema
    do_image
    do_job
    # One at a time, in dependency order, each waiting for the previous to finish
    # (resolution feeds coverage's reconciliation ratios; the detector reads the
    # materialized contradictions/coverage/edges).
    for s in ${STEPS}; do do_run "${s}" --wait; done ;;
  *) _log "usage: $(basename "$0") [--check|--apply] [schema|image|job|run <step>|all]" >&2; exit 64 ;;
esac

_log "materialize ${ACTION}: check OK (mode=${SIG_GCP_MODE})"
