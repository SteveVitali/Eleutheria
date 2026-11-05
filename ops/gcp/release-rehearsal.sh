#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
#
# ops/gcp/release-rehearsal.sh — P36.70 (row 417, R11-REL-11): the second-release
# acceptance rehearsal — the OM-14 legs, bounded and reversible:
#
#   1. rollback-to-prior   sig-ops release rollback --to <prior pub|floor>
#   2. rollback-restore    sig-ops release rollback --to <the promoted pub>
#   3. withdraw-deny       sig-ops release withdraw --disposition <deny order>
#   4. withdraw-reinstate  sig-ops release withdraw --disposition <allow order>
#
# each timed and recorded as sig.release-rehearsal/1 under
# registry/rehearsals/ (the measured timings replace G3 §5.2's [est]
# figures — §8.1 ≤10 min, SIG-REL-D13 ≤15 min every-alias).
#
# Authority: D-G3-3 [B-9] = a — the first Class R promotion runs under the
# standing go ONLY while valid (GATE-G5 renewed it verbatim; it expires at
# GATE-G6 or 2026-11-24, whichever first). The rehearsal's precondition —            # future-ok: scheduled: the standing-go expiry
# P36.72b promoted — is the operator's HG-11 act AT the GATE-G6 sitting, so
# the contract's own fallback applies: the leg runs Class S under operator
# sig.operator-authority/1 records (registry/authorities/<name>.json — the
# verbs verify them, never create them).
#
# Contract window (verbatim): "after P36.72b promotes (>= 2026-11-13T12:00Z);        # future-ok: scheduled: the contract window
# weekday 14:00-20:00Z". The clock guard precedes the ADC gate so a queued
# apply exits 42 cleanly.
#
# Usage:
#   ops/gcp/release-rehearsal.sh [--check|--dry-run]   # plan only (default)
#   ops/gcp/release-rehearsal.sh --apply               # the bounded rehearsal
#
# Environment (apply):
#   SIG_GCP_PROJECT          the GCP project (GL-GATE-04)
#   SIG_GCP_REGION           region (default us-central1, config.sh)
#   ADC                      `gcloud auth application-default login`
#   SIG_RELEASE_REGISTRY     the private release bucket (default
#                            gs://${SIG_GCP_PROJECT}-sig-release)
#   SIG_REHEARSAL_AUTHOR     the recorded operator id (OM-20 scope discipline)
#   SIG_REHEARSAL_GO         registry/authorities/<name> go record (rollback legs)
#   SIG_REHEARSAL_AUTHORITY  registry/authorities/<name> takedown record (withdraw legs)
#   SIG_REHEARSAL_ENTITY     low-stakes entity id(s), space-separated (≤4)
#   SIG_REHEARSAL_NOW        test-only clock override for the window guard
#
# Exit codes: 0 ok · 2 usage/gate input absent · 3 unarmed (no ADC/tooling)
#             · 4 a leg refused · 42 QUEUED (outside the window / before
#             SIG_REHEARSAL_EARLIEST / no recorded author / the registry's
#             own rehearsal-blocked verdict).

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
  --apply) MODE="apply" ;;
  --check|--dry-run|"") MODE="check" ;;
  -h|--help) _usage 0 ;;
  *) echo "release-rehearsal.sh: unknown mode '${1:-}'" >&2; _usage 64 ;;
esac

export SIG_GCP_MODE="$MODE"
require_project

STATE_DIR="${SIG_REHEARSAL_STATE_DIR}"
RERUN="implement-spec spec=docs/tickets/417_P36.70__second-release-acceptance.md live_verification=true"

die() { _log "ERROR: $*" >&2; exit 4; }

_rehearsal_now() { printf '%s' "${SIG_REHEARSAL_NOW:-$(date -u +%Y-%m-%dT%H:%M:%SZ)}"; }

_dow() {  # weekday number for an ISO day (1=Mon … 7=Sun)
  if date -u -j -f '%Y-%m-%dT%H:%M:%SZ' "$1" +%u >/dev/null 2>&1; then
    date -u -j -f '%Y-%m-%dT%H:%M:%SZ' "$1" +%u   # macOS
  else
    date -u -d "$1" +%u                          # GNU
  fi
}

assert_window() {
  [ "${SIG_GCP_MODE}" = "apply" ] || return 0
  local nowiso hhmm dow
  nowiso="$(_rehearsal_now)"
  if [[ "${nowiso}" < "${SIG_REHEARSAL_EARLIEST}" ]]; then
    _log "QUEUED (exit 42): now=${nowiso} < ${SIG_REHEARSAL_EARLIEST} — the"
    _log "contract window opens after P36.72b promotes (>= 2026-11-13T12:00Z)."      # future-ok: scheduled: the contract window
    _log "re-run: ${RERUN}"
    exit 42
  fi
  dow="$(_dow "${nowiso}")"
  if [ "${dow}" -gt 5 ]; then
    _log "QUEUED (exit 42): ${nowiso} is a weekend — the contract band is"
    _log "weekday 14:00-20:00Z."
    _log "re-run: ${RERUN}"
    exit 42
  fi
  hhmm="${nowiso:11:5}"
  if [[ "${hhmm}" < "14:00" || "${hhmm}" > "20:00" ]]; then
    _log "QUEUED (exit 42): ${nowiso} is outside the weekday 14:00-20:00Z band."
    _log "re-run: ${RERUN}"
    exit 42
  fi
  [ -n "${SIG_REHEARSAL_AUTHOR}" ] || \
    die "set SIG_REHEARSAL_AUTHOR to the recorded operator id (the Class S scope)"
  [ -n "${SIG_REHEARSAL_GO}" ] || \
    die "set SIG_REHEARSAL_GO to the operator's authorities record name (rollback legs)"
  [ -n "${SIG_REHEARSAL_AUTHORITY}" ] || \
    die "set SIG_REHEARSAL_AUTHORITY to the operator's authorities record name (withdraw legs)"
  [ -n "${SIG_REHEARSAL_ENTITY}" ] || \
    die "set SIG_REHEARSAL_ENTITY to the low-stakes entity id(s) the rehearsal withdraws (≤4)"
}

plan() {
  banner "second-release acceptance rehearsal (P36.70 — planned mutation set)"
  cat <<PLAN
PLAN: sig-ops release-rehearsal plan --registry ${SIG_REHEARSAL_REGISTRY}
PLAN: sig-ops release-rehearsal orders --entity <low-stakes id> --out ${STATE_DIR}/orders
PLAN: sig-ops release-rehearsal run --registry ${SIG_REHEARSAL_REGISTRY} \\
        --deny-order .../rehearsal-deny.json --allow-order .../rehearsal-allow.json \\
        --go \${SIG_REHEARSAL_GO} --authority \${SIG_REHEARSAL_AUTHORITY} --apply --out <record>
  # legs: rollback-to-prior → rollback-restore → withdraw-deny → withdraw-reinstate,
  #   each timed (budgets 600s/900s) + recorded sig.release-rehearsal/1 under
  #   registry/rehearsals/; rolls land prepared_not_executed unless --execute-rolls
  # restore point: rollback-restore re-points latest; the allow order is the
  #   append-only reinstatement (byte-level restore = next release's staging)
  # window: after P36.72b promotes (>= 2026-11-13T12:00Z); weekday 14:00-20:00Z   # future-ok: scheduled: the contract window
  # authority: Class S (the standing go expires at GATE-G6) — SIG_REHEARSAL_GO +
  #   SIG_REHEARSAL_AUTHORITY name the operator's sig.operator-authority/1 records
PLAN
}

do_apply() {
  mkdir -p "${STATE_DIR}/orders"
  local started entity_args="" eid
  started="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  for eid in ${SIG_REHEARSAL_ENTITY}; do
    entity_args="${entity_args} --entity ${eid}"
  done
  # shellcheck disable=SC2086
  run uv run python -m ops release-rehearsal orders ${entity_args} --out "${STATE_DIR}/orders"
  run uv run python -m ops release-rehearsal run \
    --registry "${SIG_REHEARSAL_REGISTRY}" \
    --deny-order "${STATE_DIR}/orders/rehearsal-deny.json" \
    --allow-order "${STATE_DIR}/orders/rehearsal-allow.json" \
    --go "${SIG_REHEARSAL_GO}" \
    --authority "${SIG_REHEARSAL_AUTHORITY}" \
    --out "${STATE_DIR}/sig.release-rehearsal-1.json" \
    --apply
  echo "release-rehearsal: ${SIG_REHEARSAL_REGISTRY} legs recorded (author ${SIG_REHEARSAL_AUTHOR}; window ${started} -> $(date -u +%Y-%m-%dT%H:%M:%SZ))"
}

# The clock guard precedes the ADC gate so a queued apply exits 42 cleanly.
assert_window
[ "${SIG_GCP_MODE}" = "apply" ] && require_adc

case "${SIG_GCP_MODE}" in
  check) plan ;;
  apply) do_apply ;;
esac
