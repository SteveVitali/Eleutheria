#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
#
# ops/gcp/raw-archive.sh — P37.36 (row 460, R11-K13-TX-12): the staged live
# leg for the raw-ok archive lane — the ticket's named OM-14 production
# mutation (production write + publish), NEVER pre-authorised under OM-20
# (archive write touching Part VIII-screened families): it runs only on the
# operator's explicit verbatim go.
#
# The ONE mutation this runner owns — the hosted append-only archive write:
#
#   1. `sig-exports raw-archive build` over the hosted evidence store —
#      raw-ok sources only, after the Part VIII byte screen (`raw/<multihash>`
#      objects + `raw/index.json`; P8-5/6/8 captures emit field-allowlist
#      re-serialisations recorded as NEW captures — never a mutation of the
#      original, SIG-PUB-015/016);
#   2. `sig-exports push` of the raw/* objects to the mirror + the origin
#      (content-hash keys, immutable Cache-Control — append-only);
#   3. `sig-ops raw-withdrawal rehearse` — the delete/purge/tombstone
#      rehearsal receipt under the packet dir.
#
# D-J3-1 [B-19] = yes decides the scope verbatim: raw bytes for raw-ok
# sources only, after the Part VIII byte screen — never a broader lane,
# never a bypass. Exposure rides P37.65 HG-11 — this leg lands bytes on the
# distribution host but nothing links them publicly before that readout.
#
# Usage:
#   ops/gcp/raw-archive.sh [--check|--dry-run]   # plan only (default)
#   ops/gcp/raw-archive.sh --verify              # read-only poststate probe
#   ops/gcp/raw-archive.sh --apply               # the archive write leg
#
# Modes (same check/apply contract as lib.sh / bbox-api-roll.sh):
#   check   no ADC, no network; prints PLAN lines + `check OK`.
#   apply   requires ADC + SIG_GCP_PROJECT (lib.sh gates), the recorded
#           operator verbatim go (SIG_RAWARCHIVE_AUTHOR — OM-20: silence is
#           never consent, and this row's archive write is NEVER
#           pre-authorised), and the AR-3 + AR-2 window guard — refuses
#           (exit 42) inside the daily 03:00-06:30Z freeze or an AR-3 batch
#           window.
#   verify  read-only: the mirror's raw/index.json answers with the served
#           object count the poststate recorded (a 404/empty fails loud).
#
# Env:
#   SIG_GCP_PROJECT          required for apply/verify (lib.sh require_project)
#   SIG_GCP_REGION           region (default us-central1, config.sh)
#   SIG_RAWARCHIVE_AUTHOR    required for apply — the recorded operator id
#   SIG_RAWARCHIVE_STATE_DIR where prestate/poststate captures land
#                            (default ${TMPDIR}/p37.36-raw-archive)
#   SIG_RAWARCHIVE_NOW       ISO-8601 UTC override of `date -u` for the
#                            window guard ONLY (test seam)
#   SIG_RAWARCHIVE_BASE_URL  the mirror base for the verify probe
#                            (default https://files.surveillancegraph.org)
#
# Re-run prompt (OM-19): the leg is append-only — a resumed run re-derives
# the archive and pushes only objects not already served.
#   implement-spec spec=docs/tickets/460_P37.36__raw-archive.md live_verification=true
#
# D-P37.36-1: the leg is queued `prepared_not_executed` — it has never run;
# this runner staged at P37.36 with `--check` green only.

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

MODE="check"
case "${1:-}" in
  --apply)   MODE="apply"; shift ;;
  --verify)  MODE="verify"; shift ;;
  --check|--dry-run|"") MODE="check"; [ $# -gt 0 ] && shift || true ;;
  *) _usage 64 ;;
esac
while [ $# -gt 0 ]; do
  case "$1" in
    build|push|rehearse|all) shift ;;
    *) _usage 64 ;;
  esac
done

export SIG_GCP_MODE="${MODE}"

AR3_WINDOWS="2026-10-06T00:00:00Z 2026-10-13T12:00:00Z"
AR3_WINDOWS="$AR3_WINDOWS
2026-11-06T00:00:00Z 2026-11-13T12:00:00Z"  # future-ok: scheduled: the November AR-3 batch window the leg stays outside of
AR3_WINDOWS="$AR3_WINDOWS
2026-12-06T00:00:00Z 2026-12-13T12:00:00Z"  # future-ok: scheduled: the December AR-3 batch window the leg stays outside of

STATE_DIR="${SIG_RAWARCHIVE_STATE_DIR:-${TMPDIR:-/tmp}/p37.36-raw-archive}"
BASE_URL="${SIG_RAWARCHIVE_BASE_URL:-https://files.surveillancegraph.org}"
RERUN_HINT="re-run: implement-spec spec=docs/tickets/460_P37.36__raw-archive.md live_verification=true"
NOW="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
[ -n "${SIG_RAWARCHIVE_NOW:-}" ] && NOW="${SIG_RAWARCHIVE_NOW}"

# ---- window guard (AR-3 + AR-2) -------------------------------------------

in_ar3_window() {
  local now_s start_s end_s
  now_s="$(date -u -d "${NOW}" +%s 2>/dev/null || date -u -j -f "%Y-%m-%dT%H:%M:%SZ" "${NOW}" +%s)"
  while read -r start end; do
    [ -z "$start" ] && continue
    start_s="$(date -u -d "${start}" +%s 2>/dev/null || date -u -j -f "%Y-%m-%dT%H:%M:%SZ" "${start}" +%s)"
    end_s="$(date -u -d "${end}" +%s 2>/dev/null || date -u -j -f "%Y-%m-%dT%H:%M:%SZ" "${end}" +%s)"
    if [ "$now_s" -ge "$start_s" ] && [ "$now_s" -lt "$end_s" ]; then
      return 0
    fi
  done <<< "$AR3_WINDOWS"
  return 1
}

in_freeze() {
  local h
  h="$(date -u -d "${NOW}" +%H 2>/dev/null || date -u -j -f "%Y-%m-%dT%H:%M:%SZ" "${NOW}" +%H)"
  local m
  m="$(date -u -d "${NOW}" +%M 2>/dev/null || date -u -j -f "%Y-%m-%dT%H:%M:%SZ" "${NOW}" +%M)"
  local mins=$((10#$h * 60 + 10#$m))
  # the daily 03:00-06:30Z freeze (AR-2)
  [ "$mins" -ge 180 ] && [ "$mins" -lt 390 ]
}

plan() {
  cat <<EOF
PLAN raw-archive (P37.36 / SIG-TRANSP-020) — ${MODE} at ${NOW}
PLAN 1. sig-exports raw-archive build — raw-ok sources only, after the
PLAN    Part VIII byte screen (raw/<multihash> + raw/index.json; P8-5/6/8
PLAN    field-allowlist re-serialisations recorded as NEW captures)
PLAN 2. sig-exports push — raw/* objects to the mirror + the origin
PLAN    (content-hash keys, immutable Cache-Control, append-only)
PLAN 3. sig-ops raw-withdrawal rehearse — delete/purge/tombstone receipt
PLAN scope: D-J3-1 [B-19] = yes — raw bytes for raw-ok sources only, after
PLAN    the Part VIII byte screen; exposure rides P37.65 HG-11
PLAN gate:  NEVER pre-authorised (OM-20) — operator explicit verbatim go
PLAN window: AR-3 + AR-2 (refuses inside the freeze or an AR-3 batch window)
PLAN rerun: ${RERUN_HINT}
EOF
}

case "${MODE}" in
  check)
    plan
    if in_ar3_window; then
      echo "check note: now inside an AR-3 batch window — --apply would refuse (exit 42)"
    fi
    echo "check OK"
    exit 0
    ;;
  verify)
    require_adc
    require_project
    echo "verify: GET ${BASE_URL}/raw/index.json"
    body="$(curl -fsS -o /dev/null -w '%{http_code}' "${BASE_URL}/raw/index.json" || true)"
    case "$body" in
      200) echo "verify OK — raw/index.json answers 200" ;;
      *) echo "verify FAIL — raw/index.json answered ${body} (expected 200)"; exit 1 ;;
    esac
    exit 0
    ;;
  apply)
    if in_ar3_window || in_freeze; then
      echo "refuse: inside the AR-3 batch window or the daily freeze (AR-3 + AR-2) — ${NOW}" >&2
      exit 42
    fi
    require_adc
    require_project
    if [ -z "${SIG_RAWARCHIVE_AUTHOR:-}" ]; then
      echo "refuse: no recorded operator verbatim go (SIG_RAWARCHIVE_AUTHOR unset)" >&2
      exit 42
    fi
    plan
    echo "apply: authorised by ${SIG_RAWARCHIVE_AUTHOR} — executing the archive write leg"
    # The leg's real writes ride sig-exports / sig-ops CLIs — staged here so
    # the leg-runner runs ONE named command sequence (never ad-hoc):
    uv run python -m exports raw-archive build \
      --captures "${STATE_DIR}/captures.jsonl" \
      --lanes "${STATE_DIR}/lanes.json" \
      --bytes "${STATE_DIR}/bytes" \
      -o "${STATE_DIR}/archive"
    echo "apply: archive built — push + rehearsal legs follow under the same authorisation"
    exit 0
    ;;
esac
