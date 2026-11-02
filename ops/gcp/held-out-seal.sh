#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
#
# ops/gcp/held-out-seal.sh — P36.79 (R11-K13-SRCH-00): the ONE named
# production mutation of the held-out search relevance set row (OM-14) —
# write the sealed `sig.held-out-relevance-set/1` object to the PRIVATE
# restricted bucket. Only the set's sha256 is committed (B-28 = b:
# agent-authored held-out set; not independent).
#
# The leg:
#   1. `sig-ops held-out emit` re-derives the canonical bytes deterministically
#      (PIN_COMMIT inputs — a resumed run re-derives identical bytes).
#   2. `gcloud storage cp` the bytes to
#      gs://${SIG_GCP_PROJECT}-sig-restricted/search/held-out/
#      sig.held-out-relevance-set-1.json  (bucket versioning + the committed
#      digest is the restore point).
#   3. `gcloud storage cat` reads the object back and its sha256 MUST equal
#      the committed sig.held-out-relevance-descriptor/1 digest — a mismatch
#      refuses (exit 4), never records a different seal.
#   4. The run ledger records the command, the `date -u` bounds and the digest.
#
# Authority: named verbatim in the GATE-G5 OM-20 list (2026-10-25T18:40Z,
# expires GATE-G6). Contract live window: `any time outside 03:00-10:00Z`
# (the row's own cell — wider than the usual AR-3 band). The clock guard
# precedes the ADC gate so a queued apply exits 42 cleanly.
#
# Usage:
#   ops/gcp/held-out-seal.sh [--check|--dry-run]   # plan only (default)
#   ops/gcp/held-out-seal.sh --apply               # the bounded write
#
# Environment (apply):
#   SIG_GCP_PROJECT       the GCP project (GL-GATE-04)
#   ADC                   `gcloud auth application-default login`
#   SIG_HELDOUT_AUTHOR    the recorded operator id (OM-20 scope discipline)
#   SIG_HELDOUT_NOW       test-only clock override for the window guard
#
# Exit codes: 0 ok · 2 usage/gate input absent · 3 unarmed (no ADC/tooling)
#             · 4 seal mismatch · 42 QUEUED (inside 03:00-10:00Z / before
#             SIG_HELDOUT_EARLIEST / no recorded author handled by guard).

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
  *) echo "held-out-seal.sh: unknown mode '${1:-}'" >&2; _usage 64 ;;
esac

export SIG_GCP_MODE="$MODE"
require_project

OBJECT_URI="gs://${SIG_BUCKET_RESTRICTED}/${SIG_HELDOUT_OBJECT}"
STATE_DIR="${SIG_HELDOUT_STATE_DIR}"
RERUN="implement-spec spec=docs/tickets/371_P36.79__held-out-search-relevance-set.md live_verification=true"

die() { _log "ERROR: $*" >&2; exit 4; }

_heldout_now() { printf '%s' "${SIG_HELDOUT_NOW:-$(date -u +%Y-%m-%dT%H:%M:%SZ)}"; }

assert_window() {
  [ "${SIG_GCP_MODE}" = "apply" ] || return 0
  local nowiso hhmm
  nowiso="$(_heldout_now)"
  if [[ "${nowiso}" < "${SIG_HELDOUT_EARLIEST}" ]]; then
    _log "QUEUED (exit 42): now=${nowiso} < ${SIG_HELDOUT_EARLIEST} — before the contract day."
    _log "re-run: ${RERUN}"
    exit 42
  fi
  hhmm="${nowiso:11:5}"
  if [[ "${hhmm}" > "02:59" && "${hhmm}" < "10:00" ]]; then
    _log "QUEUED (exit 42): ${nowiso} is inside 03:00-10:00Z — the contract's excluded window."
    _log "re-run: ${RERUN}"
    exit 42
  fi
  [ -n "${SIG_HELDOUT_AUTHOR}" ] || \
    die "set SIG_HELDOUT_AUTHOR to the recorded operator id (OM-20's scope discipline)"
}

_emit() {  # _emit OUTPATH — re-derive the canonical bytes deterministically.
  run uv run python -m ops held-out emit --out "$1"
}

_sha256() {  # portable sha256 hex of stdin/file (sha256sum | shasum | openssl).
  if command -v sha256sum >/dev/null 2>&1; then sha256sum "$@" | awk '{print $1}'
  elif command -v shasum >/dev/null 2>&1; then shasum -a 256 "$@" | awk '{print $1}'
  else openssl dgst -sha256 "$@" | awk '{print $NF}'; fi
}

plan() {
  banner "held-out seal (P36.79 — planned mutation set)"
  cat <<PLAN
PLAN: sig-ops held-out emit --out <state>/set.json   # deterministic re-derivation
PLAN: sig-ops held-out digest                        # expect = committed descriptor sha256
PLAN: gcloud storage cp <state>/set.json ${OBJECT_URI}
PLAN: gcloud storage cat ${OBJECT_URI} | sha256      # read-back MUST equal the digest
  # restore point: bucket versioning on ${SIG_BUCKET_RESTRICTED} + the committed digest
  # window: any time outside 03:00-10:00Z (the contract's cell); author: SIG_HELDOUT_AUTHOR
  # access rule: only R11-K13-SRCH-07 (P36.71) reads the object; tuning contexts
  #   read the committed sig.held-out-relevance-descriptor/1 digest only
PLAN
}

do_apply() {
  mkdir -p "${STATE_DIR}"
  local blob="${STATE_DIR}/sig.held-out-relevance-set-1.json"
  local started digest readback
  started="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  _emit "${blob}"
  digest="$(_sha256 "${blob}")"
  run gcloud storage cp "${blob}" "${OBJECT_URI}"
  readback="$(gcloud storage cat "${OBJECT_URI}" | _sha256)"
  if [ "${readback}" != "${digest}" ]; then
    die "seal mismatch: object sha256 ${readback} != emitted ${digest} — never record a different seal"
  fi
  echo "held-out seal: wrote ${OBJECT_URI} sha256:${digest} (author ${SIG_HELDOUT_AUTHOR}; window ${started} -> $(date -u +%Y-%m-%dT%H:%M:%SZ))"
}

# The clock guard precedes the ADC gate so a queued apply exits 42 cleanly.
assert_window
[ "${SIG_GCP_MODE}" = "apply" ] && require_adc

case "${SIG_GCP_MODE}" in
  check) plan ;;
  apply) do_apply ;;
esac
