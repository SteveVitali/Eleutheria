#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
#
# ops/gcp/search-v2-roll.sh — P36.38 (row 379, R11-K13-SRCH-03): the staged
# production roll enabling the federated v2 search route on `sig-api` — the
# ticket's named OM-14 production mutation, NEVER pre-authorised (OM-20):
# it runs only on the operator's explicit verbatim go.
#
# The ONE mutation this runner owns — on the `sig-api` Cloud Run service:
#
#   gcloud run services update sig-api \
#     --memory 1Gi \
#     --update-env-vars SIG_API_SEARCH_V2=on
#
# `--memory 1Gi` is D-K3-5 [B-30] = yes (512 MiB -> 1 GiB, ≈ +$3/mo) so the
# verified local copies of the sig.release-search-index/2 artifacts fit
# (K3 §5.5); `SIG_API_SEARCH_V2=on` mounts `GET /v1/releases/{pub|latest}/search`
# (api/release_search_v2.py — default `off` mounts nothing, so an image without
# the code is a no-op either way and the flip is rollback-safe). A new
# revision rolls out on the same image — restore point = the prior revision's
# env+memory captured in prestate; rollback = `services update --memory
# <prior> --remove-env-vars SIG_API_SEARCH_V2` (or the prestate verbatim).
#
# Prerequisite (staged, never assumed): the serving revision's image must
# carry the v2 serving code — the roll verifies the env+memory read-back and
# probes `GET /v1/releases/latest/search` for a 200/410/503-not-404 answer;
# on an old image the env is inert and the probe fails loud (never claimed).
#
# Usage:
#   ops/gcp/search-v2-roll.sh [--check|--dry-run]     # plan only (default)
#   ops/gcp/search-v2-roll.sh --verify [--from-state DIR]  # read-only
#   ops/gcp/search-v2-roll.sh --apply                 # the roll
#
# Modes (same check/apply contract as lib.sh / rate-limit-enforcement.sh):
#   check   no ADC, no network; prints PLAN lines + `check OK`.
#   apply   requires ADC + SIG_GCP_PROJECT (lib.sh gates), the recorded
#           operator verbatim go (SIG_SEARCHV2_AUTHOR — OM-20's scope
#           discipline: silence is never consent, and this row's roll is
#           NEVER pre-authorised), and the AR-3 + AR-2 window guard — refuses
#           (exit 42) inside the daily 03:00-06:30Z freeze or an AR-3 batch
#           window. prestate/poststate describes land under the state dir.
#   verify  read-only: describe sig-api, assert SIG_API_SEARCH_V2=on and
#           memory=1Gi, name the serving revision, probe the route.
#
# Env:
#   SIG_GCP_PROJECT          required for apply/verify (lib.sh require_project)
#   SIG_GCP_REGION           region (default us-central1, config.sh)
#   SIG_SEARCHV2_AUTHOR      required for apply — the recorded operator id
#   SIG_SEARCHV2_STATE_DIR   where describe captures land
#                            (default ${TMPDIR}/p36.38-search-v2-roll)
#   SIG_SEARCHV2_NOW         ISO-8601 UTC override of `date -u` for the window
#                            guard ONLY (test seam; the guard echoes both clocks)
#   SIG_SEARCHV2_API_URL     the service's base URL for the verify probe
#                            (default: read back from the service describe)
#
# Re-run prompt (OM-19): the roll is idempotent — a resumed run converges to
# the declared posture and never re-does a landed one.
#   implement-spec spec=docs/tickets/379_P36.38__search-api-serving-v2.md live_verification=true
#
# D-P36.38-1: the roll itself is queued `prepared_not_executed` — it has
# never run; this runner staged at P36.38 with `--check` green only.

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
    prestate|roll|verify|all) ACTION="$1"; shift ;;
    *) _usage 64 ;;
  esac
done

export SIG_GCP_MODE="${MODE}"

# ---- constants --------------------------------------------------------------

AR3_WINDOWS="2026-10-06T00:00:00Z 2026-10-13T12:00:00Z"
AR3_WINDOWS="$AR3_WINDOWS
2026-11-06T00:00:00Z 2026-11-13T12:00:00Z"  # future-ok: scheduled: the November AR-3 batch window the roll stays outside of
AR3_WINDOWS="$AR3_WINDOWS
2026-12-06T00:00:00Z 2026-12-13T12:00:00Z"  # future-ok: scheduled: the December AR-3 batch window the roll stays outside of

STATE_DIR="${SIG_SEARCHV2_STATE_DIR:-${TMPDIR:-/tmp}/p36.38-search-v2-roll}"
[ -n "${FROM_STATE}" ] && STATE_DIR="${FROM_STATE}"
TARGET_MEMORY="${SIG_API_MEMORY:-1Gi}"
RERUN_HINT="re-run: implement-spec spec=docs/tickets/379_P36.38__search-api-serving-v2.md live_verification=true"

_iso_now() {
  if [ -n "${SIG_SEARCHV2_NOW:-}" ]; then printf '%s\n' "${SIG_SEARCHV2_NOW}";
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
# describe is the recorded restore point (AR-2's form for this roll — the
# mutation is a service-config update, not a data write).
assert_window() {
  local leg="$1" now real_now
  now="$(_iso_now)"; real_now="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "window-guard: now=$now (date -u=$real_now) leg=$leg"
  if _in_daily_freeze "$now"; then
    echo "search-v2-roll.sh: REFUSED — inside the 03:00-06:30Z AR-3 freeze ($now)" >&2
    echo "search-v2-roll.sh: ${RERUN_HINT}" >&2
    exit 42
  fi
  if _in_ar3 "$now"; then
    echo "search-v2-roll.sh: REFUSED — inside an AR-3 batch window ($now)" >&2
    echo "search-v2-roll.sh: ${RERUN_HINT}" >&2
    exit 42
  fi
  echo "window-guard: OK"
}

# `assert_author` — OM-20: this roll is NEVER pre-authorised; every apply
# records the operator's explicit verbatim go (the author id). Silence is
# never consent.
assert_author() {
  [ "${SIG_GCP_MODE}" = "apply" ] || return 0
  if [ -z "${SIG_SEARCHV2_AUTHOR:-}" ]; then
    _log "QUEUED (exit 42): SIG_SEARCHV2_AUTHOR is unset — the recorded"
    _log "operator id for this roll (never pre-authorised, OM-20)."
    _log "${RERUN_HINT}"
    exit 42
  fi
  _log "author: ${SIG_SEARCHV2_AUTHOR} (recorded — the verbatim go)"
}

_describe() {  # prints the service json; apply/verify only (real gcloud)
  gcloud run services describe "${SIG_RUN_SERVICE}" \
    --project "${SIG_GCP_PROJECT}" --region "${SIG_GCP_REGION}" --format json
}

_posture_of() {  # $1 = describe json → "env|memory"
  python3 - "$1" <<'PY'
import json, sys
try:
    doc = json.load(open(sys.argv[1]))
except Exception:
    sys.exit(2)
tmpl = doc.get("spec", {}).get("template", {})
tspec = tmpl.get("spec", {})
env = mem = ""
for c in tspec.get("containers", tmpl.get("containers", [])):
    for e in c.get("env", []):
        if e.get("name") == "SIG_API_SEARCH_V2":
            env = str(e.get("value", ""))
    mem = str((c.get("resources", {}).get("limits") or {}).get("memory", mem))
print(f"{env}|{mem}")
PY
}

_url_of() {  # $1 = describe json → the service url
  python3 - "$1" <<'PY'
import json, sys
doc = json.load(open(sys.argv[1]))
print(doc.get("status", {}).get("url", ""))
PY
}

# ---- legs -------------------------------------------------------------------

leg_prestate() {
  _log "-- prestate: capture the current sig-api service spec (restore point) --"
  local dir="${STATE_DIR}/prestate"
  mkdir -p "$dir"
  if [ "${SIG_GCP_MODE}" = "check" ]; then
    _plan "gcloud run services describe ${SIG_RUN_SERVICE} --project <project> --region ${SIG_GCP_REGION} --format json > ${dir}/sig-api.json"
    _plan "record: SIG_API_SEARCH_V2 (absent = off), container memory limit, latestReadyRevisionName — the rollback restore point"
    return 0
  fi
  _describe > "${dir}/sig-api.json"
  local prior; prior="$(_posture_of "${dir}/sig-api.json")"
  _log "prestate: SIG_API_SEARCH_V2=${prior%%|*} memory=${prior##*|} recorded at ${dir}/sig-api.json"
  python3 - "${dir}/sig-api.json" <<'PY'
import json, sys
doc = json.load(open(sys.argv[1]))
rev = (doc.get("status", {}).get("latestReadyRevisionName")
       or doc.get("status", {}).get("latestCreatedRevisionName") or "?")
img = ""
for c in doc.get("spec", {}).get("template", {}).get("spec", {}).get("containers", []):
    img = c.get("image", img)
print(f"prestate: latestReadyRevision={rev} image={img}")
PY
}

leg_roll() {
  _log "-- roll: SIG_API_SEARCH_V2=on + memory ${TARGET_MEMORY} on ${SIG_RUN_SERVICE} --"
  assert_window roll
  assert_author
  run gcloud run services update "${SIG_RUN_SERVICE}" \
    --project "${SIG_GCP_PROJECT}" --region "${SIG_GCP_REGION}" \
    --memory "${TARGET_MEMORY}" \
    --update-env-vars "SIG_API_SEARCH_V2=on"
  _log "rollback: gcloud run services update ${SIG_RUN_SERVICE} --memory <prior> --remove-env-vars SIG_API_SEARCH_V2  (or the prestate spec verbatim)"
}

leg_verify() {
  _log "-- verify: the serving posture reads back on + ${TARGET_MEMORY} --"
  if [ "${SIG_GCP_MODE}" = "check" ]; then
    _plan "gcloud run services describe ${SIG_RUN_SERVICE} --region ${SIG_GCP_REGION} --format json > ${STATE_DIR}/poststate/sig-api.json"
    _plan "assert: env SIG_API_SEARCH_V2=on + memory=${TARGET_MEMORY}; name the serving revision; probe GET /v1/releases/latest/search?q=probe for a served-or-typed answer (never 404-the-route-unmounted)"
    return 0
  fi
  local dir="${STATE_DIR}/poststate"
  mkdir -p "$dir"
  _describe > "${dir}/sig-api.json"
  local now_posture; now_posture="$(_posture_of "${dir}/sig-api.json")"
  if [ "${now_posture%%|*}" != "on" ]; then
    _log "verify FAIL: SIG_API_SEARCH_V2=${now_posture%%|*} != on"
    return 1
  fi
  if [ "${now_posture##*|}" != "${TARGET_MEMORY}" ]; then
    _log "verify FAIL: memory=${now_posture##*|} != ${TARGET_MEMORY}"
    return 1
  fi
  python3 - "${dir}/sig-api.json" <<'PY'
import json, sys
doc = json.load(open(sys.argv[1]))
rev = (doc.get("status", {}).get("latestReadyRevisionName")
       or doc.get("status", {}).get("latestCreatedRevisionName") or "?")
conds = {c.get("type"): c.get("status") for c in doc.get("status", {}).get("conditions", [])}
print(f"verify: serving revision {rev}; conditions={conds}")
PY
  local url="${SIG_SEARCHV2_API_URL:-$(_url_of "${dir}/sig-api.json")}"
  if [ -z "${url}" ]; then
    _log "verify: no service URL readable — the route probe is recorded skipped, never claimed"
    return 0
  fi
  local code
  code="$(curl -sS -o /dev/null -w '%{http_code}' "${url}/v1/releases/latest/search?q=probe" || echo 000)"
  case "${code}" in
    200|410|422|503) _log "verify: probe ${url}/v1/releases/latest/search?q=probe -> ${code} (route mounted)" ;;
    404) _log "verify FAIL: probe answered 404 — the route is not mounted (image without the v2 code, or env inert)"; return 1 ;;
    *)   _log "verify FAIL: probe answered ${code:-<unreachable>}"; return 1 ;;
  esac
}

# ---- main -------------------------------------------------------------------

banner "P36.38 staged v2-search API roll (${SIG_RUN_SERVICE})"

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
  roll)     leg_roll ;;
  verify)   leg_verify ;;
  all)
    leg_prestate
    leg_roll
    leg_verify
    ;;
  *) _usage 64 ;;
esac

if [ "${SIG_GCP_MODE}" = "check" ]; then
  _log "check OK — plan printed, no ADC used, no network touched. The roll is"
  _log "NEVER pre-authorised (OM-20): apply needs ADC + SIG_GCP_PROJECT + the"
  _log "recorded verbatim go (SIG_SEARCHV2_AUTHOR), inside AR-3 + AR-2."
fi
