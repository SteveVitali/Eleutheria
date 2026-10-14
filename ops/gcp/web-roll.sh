#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
#
# ops/gcp/web-roll.sh — the L1 leg of P34.40: roll `sig-web` by pinned digest
# onto the image carrying the P32.13 nginx (ops/web/nginx.conf: the withdrawal
# include + the /r/, /releases/, /entity/ locations, and the dark
# chrome_*/terms_* fragment includes). The roll itself is
# `ops/gcp/web.sh --apply all`; this script wraps it in the leg's record:
# prestate capture → roll → poststate byte-compare gate.
#
#   ./web-roll.sh --check [action]   # (default) plan-only: NO ADC, NO network.
#   ./web-roll.sh --apply <action>   # windowed + operator ADC.
#
# Actions:
#   prestate   `run services describe sig-web` (revision + image digest) +
#              route-compare captures of every allow-listed route on the
#              canonical origin and the run.app URL. READ-ONLY.
#   roll       `ops/gcp/web.sh --apply all` — build sig-web:<git-sha> via
#              Cloud Build, deploy by pinned digest (ADR-111).
#   poststate  describe again (new revision + digest recorded) + route-compare
#              verify vs the prestate captures — 0 differences or FAIL.
#   rollback   print the recorded rollback: roll sig-web back to the recorded
#              prior image digest (a NEW revision — never a traffic revert,
#              G3 §8.1).
#   all        prestate → roll → poststate (the leg).
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
STATE_DIR="${2:-${SIG_LB_STATE_DIR:-${TMPDIR:-/tmp}/p34.40-l1}}"

_repo="$(cd "${_here}/../.." && pwd)"

RERUN='implement-spec spec=docs/tickets/249_P34.40__serving-topology-dark.md live_verification=true'

_sigops() {
  (cd "${_repo}" && uv run --quiet sig-ops "$@")
}

# `assert_window` — the OM-19/AR-3 clock guard (ISO strings compare
# lexicographically; exit 42 = queued leg). Check mode is never gated —
# a printed plan mutates nothing.
assert_window() {
  [ "${SIG_GCP_MODE}" = "apply" ] || return 0
  local now hour
  now="${SIG_LB_NOW:-$(date -u +%Y-%m-%dT%H:%M:%SZ)}"
  if [[ "${now}" < "${SIG_LB_EARLIEST}" ]]; then
    _log "QUEUED (exit 42): now=${now} < ${SIG_LB_EARLIEST} — the AR-3 freeze."
    _log "re-run: ${RERUN} (scope: L1, the sig-web nginx roll)"
    exit 42
  fi
  hour="${now:11:2}"
  if [[ "${hour}" =~ ^0[3-9]$ ]]; then
    _log "QUEUED (exit 42): ${now} is inside 03:00–10:00Z — never mutate then."
    _log "re-run: ${RERUN} (scope: L1, the sig-web nginx roll)"
    exit 42
  fi
  _log "window OK: ${now} (≥ ${SIG_LB_EARLIEST}, outside 03:00–10:00Z)"
}

_runapp_url() {
  python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["status"]["url"])' \
    "${STATE_DIR}/sig-web-$1.json"
}

do_prestate() {
  _log "-- prestate: sig-web describe + allow-list byte-compare baseline --"
  if [ "${SIG_GCP_MODE}" = "check" ]; then
    _plan "gcloud run services describe ${SIG_WEB_SERVICE} --region ${SIG_GCP_REGION} --format json > ${STATE_DIR}/sig-web-pre.json"
    _plan "sig-ops route-compare capture --base https://${SIG_WEB_DOMAIN} --out ${STATE_DIR}/routes-canonical-pre.json"
    _plan "sig-ops route-compare capture --base <sig-web run.app url> --out ${STATE_DIR}/routes-runapp-pre.json"
    return 0
  fi
  mkdir -p "${STATE_DIR}"
  gcloud run services describe "${SIG_WEB_SERVICE}" --region "${SIG_GCP_REGION}" \
    --project "${SIG_GCP_PROJECT}" --format json > "${STATE_DIR}/sig-web-pre.json"
  python3 -c 'import json,sys
s = json.load(open(sys.argv[1]))
c = s["spec"]["template"]["spec"]["containers"][0]
print("   prior image:", c["image"])
print("   prior revision:", s["status"]["latestReadyRevisionName"])' \
    "${STATE_DIR}/sig-web-pre.json"
  _sigops route-compare capture --base "https://${SIG_WEB_DOMAIN}" \
    --out "${STATE_DIR}/routes-canonical-pre.json"
  _sigops route-compare capture --base "$(_runapp_url pre)" \
    --out "${STATE_DIR}/routes-runapp-pre.json"
  _log "   prestate recorded under ${STATE_DIR} (date -u: $(date -u +%FT%TZ))"
}

do_roll() {
  assert_window
  _log "-- roll: ops/gcp/web.sh --apply all (build :<sha12>, deploy by digest) --"
  if [ "${SIG_GCP_MODE}" = "check" ]; then
    _plan "ops/gcp/web.sh --apply all   # Cloud Build + run deploy --image @sha256:"
    return 0
  fi
  "${_here}/web.sh" --apply all
}

do_poststate() {
  _log "-- poststate: describe + byte-compare verify (0 differences required) --"
  if [ "${SIG_GCP_MODE}" = "check" ]; then
    _plan "gcloud run services describe ${SIG_WEB_SERVICE} --region ${SIG_GCP_REGION} --format json > ${STATE_DIR}/sig-web-post.json"
    _plan "sig-ops route-compare capture --base https://${SIG_WEB_DOMAIN} --out ${STATE_DIR}/routes-canonical-post.json"
    _plan "sig-ops route-compare capture --base <run.app> --out ${STATE_DIR}/routes-runapp-post.json"
    _plan "sig-ops route-compare verify --a routes-canonical-pre.json --b routes-canonical-post.json"
    _plan "sig-ops route-compare verify --a routes-runapp-pre.json --b routes-runapp-post.json"
    return 0
  fi
  gcloud run services describe "${SIG_WEB_SERVICE}" --region "${SIG_GCP_REGION}" \
    --project "${SIG_GCP_PROJECT}" --format json > "${STATE_DIR}/sig-web-post.json"
  python3 -c 'import json,sys
s = json.load(open(sys.argv[1]))
c = s["spec"]["template"]["spec"]["containers"][0]
print("   new image:", c["image"])
print("   new revision:", s["status"]["latestReadyRevisionName"])' \
    "${STATE_DIR}/sig-web-post.json"
  _sigops route-compare capture --base "https://${SIG_WEB_DOMAIN}" \
    --out "${STATE_DIR}/routes-canonical-post.json"
  _sigops route-compare capture --base "$(_runapp_url post)" \
    --out "${STATE_DIR}/routes-runapp-post.json"
  _sigops route-compare verify \
    --a "${STATE_DIR}/routes-canonical-pre.json" \
    --b "${STATE_DIR}/routes-canonical-post.json"
  _sigops route-compare verify \
    --a "${STATE_DIR}/routes-runapp-pre.json" \
    --b "${STATE_DIR}/routes-runapp-post.json"
  _log "poststate OK — ${SIG_WEB_SERVICE} rolled; every allow-listed route byte-identical."
}

do_rollback() {
  _log "-- rollback: roll ${SIG_WEB_SERVICE} back to the recorded prior digest --"
  local prior
  prior="$(python3 -c 'import json,sys
s = json.load(open(sys.argv[1]))
print(s["spec"]["template"]["spec"]["containers"][0]["image"])' \
    "${STATE_DIR}/sig-web-pre.json" 2>/dev/null || true)"
  if [ -z "${prior}" ]; then
    if [ "${SIG_GCP_MODE}" = "check" ]; then
      prior="<image@sha256: recorded in ${STATE_DIR}/sig-web-pre.json>"
    else
      _log "ERROR: no recorded prior digest at ${STATE_DIR}/sig-web-pre.json — cannot print the rollback." >&2
      exit 4
    fi
  fi
  _log "A NEW revision on the recorded prior image (never a traffic revert, G3 §8.1):"
  _log "  gcloud run deploy ${SIG_WEB_SERVICE} --image ${prior} \\"
  _log "    --region ${SIG_GCP_REGION} --project ${SIG_GCP_PROJECT}"
}

require_project
# The clock guard precedes the ADC gate so a queued apply exits 42 cleanly.
case "${ACTION}" in
  roll|all) assert_window ;;
esac
require_adc

banner "P34.40 L1 — sig-web roll by digest onto the P32.13 nginx"

case "${ACTION}" in
  prestate)  do_prestate ;;
  roll)      do_roll ;;
  poststate) do_poststate ;;
  rollback)  do_rollback ;;
  all)
    do_prestate
    do_roll
    do_poststate ;;
  *) _log "usage: $(basename "$0") [--check|--apply] [prestate|roll|poststate|rollback|all] [state-dir]" >&2; exit 64 ;;
esac

_log "web-roll ${ACTION}: done (mode=${SIG_GCP_MODE})"
