#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
#
# ops/gcp/lb-routes.sh — the L2 leg of P34.40 (ACT-17, G3 §4.3 option 3a): a
# serverless NEG + EXTERNAL_MANAGED backend service for sig-api, then a URL-map
# path rule /v1 + /v1/* → it on the apex matcher of ${SIG_LB_URLMAP}. The
# committed declaration is ops/lb_routes.toml (`sig-ops lb-map` renders/diffs
# it); the /intake/* rule in the same file is `enabled = false` and is NEVER
# applied here — no `sig-intake` service exists (P37.59 owns any receiver).
#
#   ./lb-routes.sh --check [action]   # (default) plan-only: NO ADC, NO network.
#   ./lb-routes.sh --apply <action>   # windowed + operator ADC.
#
# Actions:
#   prestate  capture the AR-2-analogue restore point: `url-maps export` +
#             `run services describe` sig-web/sig-api + a route-compare
#             baseline of every allow-listed route on the canonical origin
#             and the run.app URL (P34.40 deliverable 6). READ-ONLY.
#   neg       create the serverless NEG → sig-api (regional, idempotent).
#   backend   create the global backend service + attach the NEG (idempotent).
#   urlmap    export → render (`lb-map render`) → `url-maps import` — the only
#             step that changes a public answer. Idempotent.
#   verify    `lb-map diff` must be clean + /v1/health on the canonical origin
#             must answer with the API's JSON shape (not the web nginx 404).
#   rollback  re-import the recorded prestate export, then delete the unused
#             NEG + backend (the undo path — deliberately NOT window-gated;
#             restoring prestate is always safe).
#   all       prestate → neg → backend → urlmap → verify (the leg).
#
# Live window (OM-19): applies run ≥ ${SIG_LB_EARLIEST} and never 03:00–10:00Z;
# earlier → exit 42 (queued, the RETURN PASS re-run prompt is printed).
# SIG_LB_NOW overrides the clock for the offline guard test only.
set -euo pipefail

_here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=ops/gcp/config.sh
. "${_here}/config.sh"
# shellcheck source=ops/gcp/lib.sh
. "${_here}/lib.sh"

parse_mode "${1:-}"
shift || true
ACTION="${1:-all}"
STATE_DIR="${2:-${SIG_LB_STATE_DIR:-${TMPDIR:-/tmp}/p34.40-l2}}"

_repo="$(cd "${_here}/../.." && pwd)"

RERUN='implement-spec spec=docs/tickets/249_P34.40__serving-topology-dark.md live_verification=true'

# `_sigops <args>` — run the repo CLI. The repo is the run context for the
# ops verbs; uv resolves the workspace from the repo root.
_sigops() {
  (cd "${_repo}" && uv run --quiet sig-ops "$@")
}

# `assert_window` — the OM-19/AR-3 clock guard. ISO strings compare
# lexicographically, so no GNU-date dependency. Exit 42 = queued leg.
# Check mode is never gated — a printed plan mutates nothing.
assert_window() {
  [ "${SIG_GCP_MODE}" = "apply" ] || return 0
  local now hour
  now="${SIG_LB_NOW:-$(date -u +%Y-%m-%dT%H:%M:%SZ)}"
  if [[ "${now}" < "${SIG_LB_EARLIEST}" ]]; then
    _log "QUEUED (exit 42): now=${now} < ${SIG_LB_EARLIEST} — the AR-3 freeze."
    _log "re-run: ${RERUN} (scope: L2, the /v1/* LB step)"
    exit 42
  fi
  hour="${now:11:2}"
  if [[ "${hour}" =~ ^0[3-9]$ ]]; then
    _log "QUEUED (exit 42): ${now} is inside 03:00–10:00Z — never mutate then."
    _log "re-run: ${RERUN} (scope: L2, the /v1/* LB step)"
    exit 42
  fi
  _log "window OK: ${now} (≥ ${SIG_LB_EARLIEST}, outside 03:00–10:00Z)"
}

do_prestate() {
  _log "-- prestate: AR-2-analogue capture into ${STATE_DIR} (read-only) --"
  if [ "${SIG_GCP_MODE}" = "check" ]; then
    _plan "gcloud compute url-maps export ${SIG_LB_URLMAP} --global --destination ${STATE_DIR}/urlmap-pre.yaml"
    _plan "gcloud run services describe ${SIG_WEB_SERVICE} --region ${REGION} --format json > ${STATE_DIR}/sig-web.json"
    _plan "gcloud run services describe ${SIG_RUN_SERVICE} --region ${REGION} --format json > ${STATE_DIR}/sig-api.json"
    _plan "sig-ops route-compare capture --base https://${SIG_WEB_DOMAIN} --out ${STATE_DIR}/routes-canonical-pre.json"
    _plan "sig-ops route-compare capture --base <sig-web run.app url> --out ${STATE_DIR}/routes-runapp-pre.json"
    return 0
  fi
  mkdir -p "${STATE_DIR}"
  gcloud compute url-maps export "${SIG_LB_URLMAP}" --global \
    --destination "${STATE_DIR}/urlmap-pre.yaml" --project "${PROJECT}" --quiet
  gcloud compute url-maps describe "${SIG_LB_URLMAP}" --global \
    --project "${PROJECT}" --format json > "${STATE_DIR}/urlmap-pre.json"
  gcloud run services describe "${SIG_WEB_SERVICE}" --region "${REGION}" \
    --project "${PROJECT}" --format json > "${STATE_DIR}/sig-web.json"
  gcloud run services describe "${SIG_RUN_SERVICE}" --region "${REGION}" \
    --project "${PROJECT}" --format json > "${STATE_DIR}/sig-api.json"
  local runapp
  runapp="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["status"]["url"])' \
    "${STATE_DIR}/sig-web.json")"
  _log "   sig-web run.app: ${runapp}"
  _sigops route-compare capture --base "https://${SIG_WEB_DOMAIN}" \
    --out "${STATE_DIR}/routes-canonical-pre.json"
  _sigops route-compare capture --base "${runapp}" \
    --out "${STATE_DIR}/routes-runapp-pre.json"
  _log "   prestate recorded under ${STATE_DIR} (date -u: $(date -u +%FT%TZ))"
}

do_neg() {
  assert_window
  _log "-- serverless NEG ${SIG_LB_API_NEG} → ${SIG_RUN_SERVICE} (${REGION}) --"
  if [ "${SIG_GCP_MODE}" = "apply" ] && \
     gcloud compute network-endpoint-groups describe "${SIG_LB_API_NEG}" \
       --region "${REGION}" --project "${PROJECT}" >/dev/null 2>&1; then
    _log "exists: ${SIG_LB_API_NEG} — skipping create"
  else
    run gcloud compute network-endpoint-groups create "${SIG_LB_API_NEG}" \
      --region "${REGION}" --network-endpoint-type=serverless \
      --cloud-run-service="${SIG_RUN_SERVICE}" --project "${PROJECT}"
  fi
}

do_backend() {
  assert_window
  _log "-- backend service ${SIG_LB_API_BACKEND} (EXTERNAL_MANAGED) + attach --"
  if [ "${SIG_GCP_MODE}" = "apply" ] && \
     gcloud compute backend-services describe "${SIG_LB_API_BACKEND}" \
       --global --project "${PROJECT}" >/dev/null 2>&1; then
    _log "exists: ${SIG_LB_API_BACKEND} — skipping create"
  else
    run gcloud compute backend-services create "${SIG_LB_API_BACKEND}" \
      --global --load-balancing-scheme=EXTERNAL_MANAGED --project "${PROJECT}"
  fi
  if [ "${SIG_GCP_MODE}" = "apply" ] && \
     gcloud compute backend-services describe "${SIG_LB_API_BACKEND}" --global \
       --project "${PROJECT}" --format='value(backends[].group)' 2>/dev/null \
       | grep -q "${SIG_LB_API_NEG}"; then
    _log "exists: ${SIG_LB_API_NEG} attached — skipping add-backend"
  else
    run gcloud compute backend-services add-backend "${SIG_LB_API_BACKEND}" \
      --global --network-endpoint-group="${SIG_LB_API_NEG}" \
      --network-endpoint-group-region="${REGION}" --project "${PROJECT}"
  fi
}

do_urlmap() {
  assert_window
  _log "-- url-map: export → lb-map render → import (${SIG_LB_URLMAP}) --"
  if [ "${SIG_GCP_MODE}" = "check" ]; then
    _plan "gcloud compute url-maps describe ${SIG_LB_URLMAP} --global --format json > ${STATE_DIR}/urlmap-apply-live.json"
    _plan "sig-ops lb-map render --live ${STATE_DIR}/urlmap-apply-live.json --project ${PROJECT} --out ${STATE_DIR}/urlmap-apply.yaml"
    _plan "gcloud compute url-maps import ${SIG_LB_URLMAP} --global --source ${STATE_DIR}/urlmap-apply.yaml"
    _log "   declaration (lb-map plan):"
    _sigops lb-map plan | sed 's/^/     /' || true
    return 0
  fi
  mkdir -p "${STATE_DIR}"
  gcloud compute url-maps describe "${SIG_LB_URLMAP}" --global \
    --project "${PROJECT}" --format json > "${STATE_DIR}/urlmap-apply-live.json"
  _sigops lb-map render --live "${STATE_DIR}/urlmap-apply-live.json" \
    --project "${PROJECT}" --out "${STATE_DIR}/urlmap-apply.yaml"
  _log "+ gcloud compute url-maps import ${SIG_LB_URLMAP} --global --source ${STATE_DIR}/urlmap-apply.yaml"
  gcloud compute url-maps import "${SIG_LB_URLMAP}" --global \
    --source "${STATE_DIR}/urlmap-apply.yaml" --project "${PROJECT}" --quiet
}

do_verify() {
  _log "-- verify: lb-map diff + /v1/health answer shape on the canonical origin --"
  if [ "${SIG_GCP_MODE}" = "check" ]; then
    _plan "gcloud compute url-maps describe ${SIG_LB_URLMAP} --global --format json > ${STATE_DIR}/urlmap-post.json && sig-ops lb-map diff --live ${STATE_DIR}/urlmap-post.json --project ${PROJECT}"
    _plan "curl -fsS https://${SIG_WEB_DOMAIN}/v1/health — the API's JSON answer, not nginx's 404 page"
    return 0
  fi
  gcloud compute url-maps describe "${SIG_LB_URLMAP}" --global \
    --project "${PROJECT}" --format json > "${STATE_DIR}/urlmap-post.json"
  if ! _sigops lb-map diff --live "${STATE_DIR}/urlmap-post.json" \
       --project "${PROJECT}"; then
    _log "FAIL: the live URL map drifts from ops/lb_routes.toml — see DRIFT lines."
    return 1
  fi
  # /v1/health must be answered BY sig-api (a FastAPI JSON body — the API has
  # no /v1/health route, so today's proof is the API-shaped 404; once the API
  # rolls with a route it answers 200). nginx's 404 is an HTML error page —
  # the discriminant is a JSON-shaped answer.
  local body
  # No -f: the API's 404 JSON body is the discriminant, so capture it.
  body="$(curl -sS --max-time 20 "https://${SIG_WEB_DOMAIN}/v1/health" 2>/dev/null || true)"
  if printf '%s' "${body}" | grep -q '<html'; then
    _log "FAIL: /v1/health answered by the web nginx (HTML 404) — the /v1/* rule is not live."
    return 1
  fi
  _log "   /v1/health canonical answer: ${body:0:200}"
  # The byte-compare gate: every allow-listed route identical to prestate.
  local runapp
  runapp="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["status"]["url"])' \
    "${STATE_DIR}/sig-web.json")"
  _sigops route-compare capture --base "https://${SIG_WEB_DOMAIN}" \
    --out "${STATE_DIR}/routes-canonical-post.json"
  _sigops route-compare capture --base "${runapp}" \
    --out "${STATE_DIR}/routes-runapp-post.json"
  _sigops route-compare verify \
    --a "${STATE_DIR}/routes-canonical-pre.json" \
    --b "${STATE_DIR}/routes-canonical-post.json"
  _sigops route-compare verify \
    --a "${STATE_DIR}/routes-runapp-pre.json" \
    --b "${STATE_DIR}/routes-runapp-post.json"
  _log "verify OK — ${SIG_LB_URLMAP} carries the declared rules; allow-list byte-equal."
}

do_rollback() {
  # The undo path: re-import the recorded prestate export verbatim, then drop
  # the now-unused NEG + backend. Deliberately NOT window-gated — restoring
  # the recorded prestate is always the safe action.
  _log "-- rollback: re-import ${STATE_DIR}/urlmap-pre.yaml; delete NEG+backend --"
  if [ "${SIG_GCP_MODE}" = "check" ]; then
    _plan "gcloud compute url-maps import ${SIG_LB_URLMAP} --global --source ${STATE_DIR}/urlmap-pre.yaml"
    _plan "gcloud compute backend-services delete ${SIG_LB_API_BACKEND} --global --quiet"
    _plan "gcloud compute network-endpoint-groups delete ${SIG_LB_API_NEG} --region ${REGION} --quiet"
    return 0
  fi
  if [ ! -f "${STATE_DIR}/urlmap-pre.yaml" ]; then
    _log "ERROR: no recorded prestate at ${STATE_DIR}/urlmap-pre.yaml — refusing to roll back blind." >&2
    exit 4
  fi
  gcloud compute url-maps import "${SIG_LB_URLMAP}" --global \
    --source "${STATE_DIR}/urlmap-pre.yaml" --project "${PROJECT}" --quiet
  gcloud compute backend-services delete "${SIG_LB_API_BACKEND}" \
    --global --project "${PROJECT}" --quiet || true
  gcloud compute network-endpoint-groups delete "${SIG_LB_API_NEG}" \
    --region "${REGION}" --project "${PROJECT}" --quiet || true
  _log "rollback applied — urlmap restored from prestate; unused NEG+backend deleted."
}

require_project
# The clock guard precedes the ADC gate so a queued apply exits 42 cleanly
# (no credentials needed to know it is too early).
case "${ACTION}" in
  neg|backend|urlmap|all) assert_window ;;
esac
require_adc

REGION="${SIG_GCP_REGION}"
PROJECT="${SIG_GCP_PROJECT}"

banner "P34.40 L2 — /v1/* path rule on ${SIG_LB_URLMAP} (serverless NEG → sig-api)"

case "${ACTION}" in
  prestate) do_prestate ;;
  neg)      do_neg ;;
  backend)  do_backend ;;
  urlmap)   do_urlmap ;;
  verify)   do_verify ;;
  rollback) do_rollback ;;
  all)
    do_prestate
    do_neg
    do_backend
    do_urlmap
    do_verify ;;
  *) _log "usage: $(basename "$0") [--check|--apply] [prestate|neg|backend|urlmap|verify|rollback|all] [state-dir]" >&2; exit 64 ;;
esac

_log "lb-routes ${ACTION}: done (mode=${SIG_GCP_MODE})"
