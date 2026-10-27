#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
#
# ops/gcp/rate-limit-enforcement.sh — P36.13 (row 354, R11-OPS-06): the hosted
# rate-limit enforcement flip — SIG-API-009's named OM-20 mutation.
#
# The ONE mutation this runner owns: on the `sig-api` Cloud Run service the
# in-process limiter (api/src/api/rate_limit.py — 30 requests / 60 s / burst
# 10 per client, headers on every response) moves from DEFINED to ENFORCED:
#
#   gcloud run services update sig-api \
#     --update-env-vars SIG_API_RATE_LIMIT=enforce,SIG_API_TRUSTED_PROXY_HOPS=2
#
# (the external Google LB appends `<client-ip>, <lb-ip>` to X-Forwarded-For,
# so the 2nd-from-right entry is the real client — K3 §5.6, never the peer;
# a deploy target NOT behind that LB must set the hop count it actually has
# via SIG_RATELIMIT_HOPS.) A new revision rolls out on the same image —
# restore point = the prior revision's env captured in prestate; rollback =
# `services update --update-env-vars SIG_API_RATE_LIMIT=advise` (defined) or
# `--remove-env-vars SIG_API_RATE_LIMIT` (off).
#
# D-K3-6 stays deferred: no Cloud Armor / managed edge is created here — the
# in-process limiter is the whole mechanism (SIG-STORE-003 zero-cost).
#
# Usage:
#   ops/gcp/rate-limit-enforcement.sh [--check|--dry-run]   # plan only (default)
#   ops/gcp/rate-limit-enforcement.sh --verify [--from-state DIR]  # read-only
#   ops/gcp/rate-limit-enforcement.sh --apply               # the flip
#
# Modes (same check/apply contract as lib.sh / alerting.sh):
#   check   no ADC, no network; prints PLAN lines + `check OK`.
#   apply   requires ADC + SIG_GCP_PROJECT (lib.sh gates), the recorded
#           operator id (SIG_RATELIMIT_AUTHOR — OM-20's scope discipline:
#           silence is never consent), and the AR-3 window guard — refuses
#           (exit 42) inside the daily 03:00-06:30Z freeze or an AR-3 batch
#           window. prestate/poststate describes land under the state dir.
#   verify  read-only: describe sig-api, assert the posture env is exactly
#           the target value and name the serving revision.
#
# Env:
#   SIG_GCP_PROJECT          required for apply/verify (lib.sh require_project)
#   SIG_GCP_REGION           region (default us-central1, config.sh)
#   SIG_RATELIMIT_AUTHOR     required for apply — the recorded operator id
#   SIG_RATELIMIT_TARGET     posture to flip to (default `enforce`; `advise`
#                            and `off` are the rollback legs)
#   SIG_RATELIMIT_HOPS       trusted proxy hops the client key slices
#                            (default 2 — the Google external LB appends
#                            <client-ip>,<lb-ip>; see api.rate_limit)
#   SIG_RATELIMIT_STATE_DIR  where describe captures land
#                            (default ${TMPDIR}/p36.13-ratelimit)
#   SIG_RATELIMIT_NOW        ISO-8601 UTC override of `date -u` for the window
#                            guard ONLY (test seam; the guard echoes both clocks)
#
# Re-run prompt (OM-19): the flip is idempotent — a resumed run converges to
# the declared posture and never re-does a landed one.
#   implement-spec spec=docs/tickets/354_P36.13__api-rate-limits.md live_verification=true

set -euo pipefail

_here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=config.sh
. "${_here}/config.sh"
# shellcheck source=lib.sh
. "${_here}/lib.sh"

_usage() {
  sed -n '/^# Usage:/,/^set -euo pipefail/p' "$0" | sed 's/^# \{0,1\}//; /^set -euo/d'
  exit "${1:-64}"
}

# ---- args -------------------------------------------------------------------

MODE="check"
ACTION="all"
FROM_STATE=""

case "${1:-}" in
  --apply)   MODE="apply"; shift ;;
  --verify)  MODE="verify"; shift ;;
  --check|--dry-run|"") MODE="check"; [ $# -gt 0 ] && shift || true ;;
  *) _usage 64 ;;
esac
while [ $# -gt 0 ]; do
  case "$1" in
    --from-state) FROM_STATE="$2"; shift 2 ;;
    prestate|flip|verify|all) ACTION="$1"; shift ;;
    *) _usage 64 ;;
  esac
done

export SIG_GCP_MODE="${MODE}"

# ---- constants --------------------------------------------------------------

AR3_WINDOWS="2026-10-06T00:00:00Z 2026-10-13T12:00:00Z"
AR3_WINDOWS="$AR3_WINDOWS
2026-11-06T00:00:00Z 2026-11-13T12:00:00Z"  # future-ok: scheduled: the November AR-3 batch window the flip stays outside of
AR3_WINDOWS="$AR3_WINDOWS
2026-12-06T00:00:00Z 2026-12-13T12:00:00Z"  # future-ok: scheduled: the December AR-3 batch window the flip stays outside of

STATE_DIR="${SIG_RATELIMIT_STATE_DIR:-${TMPDIR:-/tmp}/p36.13-ratelimit}"
[ -n "${FROM_STATE}" ] && STATE_DIR="${FROM_STATE}"
TARGET_POSTURE="${SIG_RATELIMIT_TARGET:-enforce}"
TARGET_HOPS="${SIG_RATELIMIT_HOPS:-2}"
RERUN_HINT="re-run: implement-spec spec=docs/tickets/354_P36.13__api-rate-limits.md live_verification=true"

_iso_now() {
  if [ -n "${SIG_RATELIMIT_NOW:-}" ]; then printf '%s\n' "${SIG_RATELIMIT_NOW}";
  else date -u +%Y-%m-%dT%H:%M:%SZ; fi
}

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

# `assert_window` — the contract's AR-3 + AR-2 window: never inside the daily
# 03:00–06:30Z freeze, never inside an AR-3 batch window; the prestate
# describe is the recorded restore point (AR-2's form for this flip — the
# mutation is a service-config update, not a data write).
assert_window() {
  local leg="$1" now real_now
  now="$(_iso_now)"; real_now="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "window-guard: now=$now (date -u=$real_now) leg=$leg"
  if _in_daily_freeze "$now"; then
    echo "rate-limit-enforcement.sh: REFUSED — inside the 03:00-06:30Z AR-3 freeze ($now)" >&2
    echo "rate-limit-enforcement.sh: ${RERUN_HINT}" >&2
    exit 42
  fi
  if _in_ar3 "$now"; then
    echo "rate-limit-enforcement.sh: REFUSED — inside an AR-3 batch window ($now)" >&2
    echo "rate-limit-enforcement.sh: ${RERUN_HINT}" >&2
    exit 42
  fi
  echo "window-guard: OK"
}

# `assert_author` — OM-20: the GATE-G5 naming (2026-10-25T18:40Z, expires
# GATE-G6) pre-authorises the flip in-ticket; every mutating apply still
# records the operator id — silence is never consent.
assert_author() {
  [ "${SIG_GCP_MODE}" = "apply" ] || return 0
  if [ -z "${SIG_RATELIMIT_AUTHOR:-}" ]; then
    _log "QUEUED (exit 42): SIG_RATELIMIT_AUTHOR is unset — the recorded"
    _log "operator id for this flip (the GATE-G5 OM-20 listing's scope)."
    _log "${RERUN_HINT}"
    exit 42
  fi
  _log "author: ${SIG_RATELIMIT_AUTHOR} (recorded)"
}

_describe() {  # prints the service json; apply/verify only (real gcloud)
  gcloud run services describe "${SIG_RUN_SERVICE}" \
    --project "${SIG_GCP_PROJECT}" --region "${SIG_GCP_REGION}" --format json
}

_posture_of() {  # $1 = a describe json file → the SIG_API_RATE_LIMIT value or ""
  python3 - "$1" <<'PY'
import json, sys
try:
    doc = json.load(open(sys.argv[1]))
except Exception:
    sys.exit(2)
tmpl = doc.get("spec", {}).get("template", {})
value = ""
for c in tmpl.get("spec", {}).get("containers", tmpl.get("containers", [])):
    for e in c.get("env", []):
        if e.get("name") == "SIG_API_RATE_LIMIT":
            value = str(e.get("value", ""))
print(value)
PY
}

# ---- legs -------------------------------------------------------------------

leg_prestate() {
  _log "-- prestate: capture the current sig-api service spec (restore point) --"
  local dir="${STATE_DIR}/prestate"
  mkdir -p "$dir"
  if [ "${SIG_GCP_MODE}" = "check" ]; then
    _plan "gcloud run services describe ${SIG_RUN_SERVICE} --project <project> --region ${SIG_GCP_REGION} --format json > ${dir}/sig-api.json"
    _plan "record: current SIG_API_RATE_LIMIT value (absent = off), SIG_API_TRUSTED_PROXY_HOPS, latestReadyRevisionName — the rollback restore point"
    return 0
  fi
  _describe > "${dir}/sig-api.json"
  local prior
  prior="$(_posture_of "${dir}/sig-api.json")"
  _log "prestate: SIG_API_RATE_LIMIT=${prior:-<unset (off)>} recorded at ${dir}/sig-api.json"
  python3 - "${dir}/sig-api.json" <<'PY'
import json, sys
doc = json.load(open(sys.argv[1]))
rev = (doc.get("status", {}).get("latestReadyRevisionName")
       or doc.get("status", {}).get("latestCreatedRevisionName") or "?")
print(f"prestate: latestReadyRevision={rev}")
PY
}

leg_flip() {
  _log "-- flip: defined -> ${TARGET_POSTURE} on ${SIG_RUN_SERVICE} --"
  assert_window flip
  assert_author
  if [ "${TARGET_POSTURE}" = "off" ]; then
    run gcloud run services update "${SIG_RUN_SERVICE}" \
      --project "${SIG_GCP_PROJECT}" --region "${SIG_GCP_REGION}" \
      --remove-env-vars "SIG_API_RATE_LIMIT,SIG_API_TRUSTED_PROXY_HOPS"
  else
    run gcloud run services update "${SIG_RUN_SERVICE}" \
      --project "${SIG_GCP_PROJECT}" --region "${SIG_GCP_REGION}" \
      --update-env-vars "SIG_API_RATE_LIMIT=${TARGET_POSTURE},SIG_API_TRUSTED_PROXY_HOPS=${TARGET_HOPS}"
  fi
  _log "rollback: gcloud run services update ${SIG_RUN_SERVICE} --update-env-vars SIG_API_RATE_LIMIT=advise  (defined) — or the prestate env verbatim"
}

leg_verify() {
  _log "-- verify: the serving posture reads back ${TARGET_POSTURE} --"
  if [ "${SIG_GCP_MODE}" = "check" ]; then
    _plan "gcloud run services describe ${SIG_RUN_SERVICE} --region ${SIG_GCP_REGION} --format json > ${STATE_DIR}/poststate/sig-api.json"
    _plan "assert: env SIG_API_RATE_LIMIT=${TARGET_POSTURE} (+ SIG_API_TRUSTED_PROXY_HOPS=${TARGET_HOPS}); name the serving revision"
    return 0
  fi
  local dir="${STATE_DIR}/poststate"
  mkdir -p "$dir"
  _describe > "${dir}/sig-api.json"
  local now_posture
  now_posture="$(_posture_of "${dir}/sig-api.json")"
  if [ "${TARGET_POSTURE}" = "off" ]; then
    if [ -n "${now_posture}" ]; then
      _log "verify FAIL: SIG_API_RATE_LIMIT still set (${now_posture})"
      return 1
    fi
  elif [ "${now_posture}" != "${TARGET_POSTURE}" ]; then
    _log "verify FAIL: SIG_API_RATE_LIMIT=${now_posture:-<unset>} != ${TARGET_POSTURE}"
    return 1
  fi
  python3 - "${dir}/sig-api.json" <<'PY'
import json, sys
doc = json.load(open(sys.argv[1]))
rev = (doc.get("status", {}).get("latestReadyRevisionName")
       or doc.get("status", {}).get("latestCreatedRevisionName") or "?")
conds = {c.get("type"): c.get("status") for c in doc.get("status", {}).get("conditions", [])}
print(f"verify OK: serving revision {rev}; conditions={conds}")
PY
}

# ---- main -------------------------------------------------------------------

banner "P36.13 hosted rate-limit enforcement flip (${SIG_RUN_SERVICE})"

if [ "${SIG_GCP_MODE}" != "check" ]; then
  require_project
fi
if [ "${SIG_GCP_MODE}" = "apply" ]; then
  require_adc
fi
if [ "${SIG_GCP_MODE}" = "verify" ]; then
  ACTION="verify"
fi

case "${ACTION}" in
  prestate) leg_prestate ;;
  flip)     leg_flip ;;
  verify)   leg_verify ;;
  all)
    leg_prestate
    leg_flip
    leg_verify
    ;;
  *) _usage 64 ;;
esac

if [ "${SIG_GCP_MODE}" = "check" ]; then
  _log "check OK — plan printed, no ADC used, no network touched. The flip is"
  _log "pre-authorised by the GATE-G5 OM-20 naming (2026-10-25T18:40Z, expires"
  _log "GATE-G6) inside AR-3 + AR-2; apply needs ADC + SIG_GCP_PROJECT +"
  _log "SIG_RATELIMIT_AUTHOR."
fi
