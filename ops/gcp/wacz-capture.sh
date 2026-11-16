#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
#
# ops/gcp/wacz-capture.sh — P37.56 (R11-TRANS-02, BL-026): the ONE named OM-20
# mutation set — flip the declared `wacz = true` HTML-document ingest jobs onto
# `scheduled-ingest --wacz`, run them, and probe the evidence store for the
# WACZ members. Pre-authorised by GATE-G6 §4 (2026-11-05T15:20Z,
# "Approve all 15 (rec.)" — names P37.56's "the WACZ capture runs for the HTML
# document sources" verbatim; expires next GATE), under the contract's own
# preconditions, restore point and rollback; OM-18: a step that meets a new
# fact stops and records.
#
# The job set is read from ops/cadence.toml — every [[sources]]/[[batches]]
# row declaring `wacz = true` (the same declaration scheduled-ops.sh deploys).
# A job update preserves the job's volumes/env/secrets — the P37.3 repoint
# already mounted the evidence bucket, so WACZ members land under
# evidence/captures/ governed by its 365 d unlocked retention. No secret, no
# ingestion_permitted flip, no scheduler change rides this script.
#
# Legs (ACTION, default `all`):
#   prestate   AR-2 restore point — every declared job's describe JSON (args +
#              volumes) into the state dir, sha256 sidecars
#   jobs       `gcloud run jobs update <job> --args "-c,exec sig-ops
#              scheduled-ingest --source|--batch <id> --sink pg --wacz"` —
#              refuses a job whose live args are NOT the declared non-wacz
#              shape (a surprise is a stop, never a clobber)
#   run        the named capture runs — `gcloud run jobs execute` each declared
#              job (waits; an already-running execution is recorded, the job
#              is not double-fired)
#   probe      acceptance read: newest ops/runs/<source> row per declared
#              source records wacz=true and its wacz_captures digests; the
#              captures prefix lists page.wacz members
#   poststate  read-back describe of every declared job (args now carry --wacz)
#   verify     read-only diff vs the declared shape (or --from-state DIR)
#   rollback   restores each job's recorded prestate args exactly (the script
#              changes args only — a rollback never touches volumes, env,
#              secrets, schedulers, or stored evidence)
#
# Usage:
#   ops/gcp/wacz-capture.sh [--check|--dry-run] [ACTION]   # plan only
#   ops/gcp/wacz-capture.sh --apply [ACTION]               # the mutation(s)
#   ops/gcp/wacz-capture.sh --verify [--from-state DIR]    # read-only diff
#
# Env: SIG_GCP_PROJECT + ADC (apply); SIG_WACZ_AUTHOR (OM-20's recorded
# operator id); SIG_WACZ_STATE_DIR (state root); SIG_WACZ_NOW (test-only
# clock seam).
#
# Exit: 0 ok · 2 usage/env · 3 unarmed · 4 verify drift · 42 QUEUED window.
set -euo pipefail

_here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=config.sh
. "${_here}/config.sh"
# shellcheck source=lib.sh
. "${_here}/lib.sh"

RERUN="implement-spec spec=docs/tickets/483_P37.56__wacz-capture-html-sources.md live_verification=true"
STATE_DIR="${SIG_WACZ_STATE_DIR:-${TMPDIR:-/tmp}/p37.56-wacz}"
RUNS_PREFIX="ops/runs"
CAPTURES_PREFIX="evidence/captures"

_usage() {
  sed -n '/^# Usage:/,/^set -euo pipefail/p' "$0" | sed 's/^# \{0,1\}//; /^set -euo/d'
  exit "${1:-64}"
}

MODE="check"; ACTION="all"; FROM_STATE=""
case "${1:-}" in
  --apply)  MODE="apply"; ACTION="${2:-all}"; FROM_STATE="${4:-}" ;;
  --verify) MODE="verify"; FROM_STATE="${3:-}" ;;
  --check|--dry-run|"") MODE="check"; ACTION="${2:-all}" ;;
  -h|--help) _usage 0 ;;
  *) echo "wacz-capture.sh: unknown mode '${1:-}'" >&2; _usage 64 ;;
esac
export SIG_GCP_MODE="$MODE"

require_project
EVIDENCE_DIR="${STATE_DIR}/$(date -u +%Y%m%dT%H%M%SZ)"

die()  { _log "ERROR: $*" >&2; exit "${2:-4}"; }
_sha256() {
  if command -v sha256sum >/dev/null 2>&1; then sha256sum "$1" | awk '{print $1}'
  else shasum -a 256 "$1" | awk '{print $1}'; fi
}
_capture() {  # _capture <rel> <cmd...> — read-only JSON + sha256 sidecar
  local out="${EVIDENCE_DIR}/$1"; shift
  mkdir -p "$(dirname "${out}")"
  _log "+ (capture) $* > ${out}"
  if ! "$@" > "${out}" 2> "${out}.err"; then
    _log "   capture failed (recorded): $*"
    return 0
  fi
  printf '%s  %s\n' "$(_sha256 "${out}")" "${out}" >> "${EVIDENCE_DIR}/sha256s.txt"
}

_now() { printf '%s' "${SIG_WACZ_NOW:-$(date -u +%Y-%m-%dT%H:%M:%SZ)}"; }

assert_window() {  # never inside the daily 03:00-10:00Z QA metadata band
  [ "${SIG_GCP_MODE}" = "apply" ] || return 0
  local nowiso hhmm
  nowiso="$(_now)"; hhmm="${nowiso:11:5}"
  if [[ "${hhmm}" > "02:59" && "${hhmm}" < "10:00" ]]; then
    _log "QUEUED (exit 42): ${nowiso} is inside 03:00-10:00Z — the daily band"
    _log "every ops mutation holds outside of (AR-3 + AR-2)."
    _log "re-run: ${RERUN}"
    exit 42
  fi
  [ -n "${SIG_WACZ_AUTHOR:-}" ] || \
    die "set SIG_WACZ_AUTHOR to the recorded operator id (OM-20 scope discipline)" 2
}

# The declared job set — (job|source|batch) rows for every cadence.toml row
# carrying `wacz = true` (the declaration scheduled-ops.sh deploys; this
# script never invents its own list).
wacz_jobs() {
  (cd "${_here}/../.." && uv run python - "${_here}/../cadence.toml" <<'PY'
import sys
import tomllib

with open(sys.argv[1], "rb") as fh:
    doc = tomllib.load(fh)
for s in doc.get("sources", []):
    if s.get("wacz"):
        print("|".join([s["job"], s["id"], ""]))
for b in doc.get("batches", []):
    if b.get("wacz"):
        print("|".join([b["job"], "", b["id"]]))
PY
  )
}

# The exact args a declared job must carry AFTER the flip (and, inverted,
# before it) — one literal shape, so verify/diff is a string compare.
want_args() {  # <source-or-empty> <batch-or-empty> [suffix]
  local src="$1" bid="$2" suffix="${3:-}"
  if [ -n "${src}" ]; then
    printf -- '-c,exec sig-ops scheduled-ingest --source %s --sink pg%s' "${src}" "${suffix}"
  else
    printf -- '-c,exec sig-ops scheduled-ingest --batch %s --sink pg%s' "${bid}" "${suffix}"
  fi
}

job_args() {  # the job's live args field (one container), "" on lookup failure
  gcloud run jobs describe "$1" --project "${SIG_GCP_PROJECT}" \
    --region "${SIG_GCP_REGION}" \
    --format='value(spec.template.spec.template.spec.containers[0].args.join(";"))' \
    2>/dev/null
}

# ---------------------------------------------------------------------------
leg_prestate() {
  banner "prestate — the AR-2 restore point"
  while IFS='|' read -r job src bid; do
    [ -z "${job}" ] && continue
    _capture "jobs/${job}.json" \
      gcloud run jobs describe "${job}" --project "${SIG_GCP_PROJECT}" \
        --region "${SIG_GCP_REGION}" --format=json
  done < <(wacz_jobs)
}

leg_jobs() {
  banner "jobs — flip the declared wacz rows onto --wacz"
  while IFS='|' read -r job src bid; do
    [ -z "${job}" ] && continue
    want="$(want_args "${src}" "${bid}" " --wacz")"
    before="$(want_args "${src}" "${bid}" "")"
    if [ "${SIG_GCP_MODE}" = "check" ]; then
      _plan "gcloud run jobs update ${job} --args \"${want}\"   # was \"${before}\" (refuses a surprise live arg shape)"
    else
      live="$(job_args "${job}" || true)"
      case "${live}" in
        "${want}")  _log "  ${job}: already on --wacz (idempotent, +0)" ;;
        "${before}")
          run gcloud run jobs update "${job}" \
            --project "${SIG_GCP_PROJECT}" --region "${SIG_GCP_REGION}" \
            --args "${want}"
          ;;
        *) die "${job}: live args '${live}' match neither the declared nor the wacz shape — OM-18 stop, record + investigate" 4 ;;
      esac
    fi
  done < <(wacz_jobs)
}

leg_run() {
  banner "run — the named mutation: the WACZ capture runs"
  while IFS='|' read -r job src bid; do
    [ -z "${job}" ] && continue
    if [ "${SIG_GCP_MODE}" = "check" ]; then
      _plan "gcloud run jobs execute ${job} --wait   # the capture run itself (never in this dispatch — live_verification=true only)"
    else
      run gcloud run jobs execute "${job}" \
        --project "${SIG_GCP_PROJECT}" --region "${SIG_GCP_REGION}" --wait
    fi
  done < <(wacz_jobs)
}

leg_probe() {
  banner "probe — WACZ availability on the run rows + the captures prefix"
  while IFS='|' read -r job src bid; do
    [ -z "${job}" ] && continue
    if [ -n "${src}" ]; then
      _plan "gcloud storage cat latest ${RUNS_PREFIX}/${src}/…json → wacz + wacz_captures digests recorded"
    else
      _plan "gcloud storage cat latest ${RUNS_PREFIX}/<each ${bid} member>/…json → wacz + wacz_captures digests recorded"
    fi
    if [ "${SIG_GCP_MODE}" = "apply" ]; then
      _capture "probe/${job}.runs.txt" \
        gcloud storage ls "gs://${SIG_BUCKET_RESTRICTED}/${RUNS_PREFIX}/"
    fi
  done < <(wacz_jobs)
  _plan "gcloud storage ls -r gs://${SIG_CAPTURE_BUCKET}/${CAPTURES_PREFIX} → the page.wacz members present"
  if [ "${SIG_GCP_MODE}" = "apply" ]; then
    _capture "probe/captures-listing.txt" \
      gcloud storage ls -r "gs://${SIG_CAPTURE_BUCKET}/${CAPTURES_PREFIX}"
  fi
}

leg_verify() {
  banner "verify — declared args vs live (and poststate capture)"
  while IFS='|' read -r job src bid; do
    [ -z "${job}" ] && continue
    want="$(want_args "${src}" "${bid}" " --wacz")"
    _capture "post/${job}.json" \
      gcloud run jobs describe "${job}" --project "${SIG_GCP_PROJECT}" \
        --region "${SIG_GCP_REGION}" --format=json
    live="$(job_args "${job}" || true)"
    if [ "${live}" = "${want}" ]; then _log "OK ${job}"
    elif [ -z "${live}" ]; then _log "UNREAD ${job} (describe failed — recorded, not a drift verdict)"
    else _log "DRIFT ${job}: '${live}' != '${want}'"; fi
  done < <(wacz_jobs)
}

leg_rollback() {
  banner "rollback — restore each job's recorded prestate args"
  while IFS='|' read -r job src bid; do
    [ -z "${job}" ] && continue
    before="$(want_args "${src}" "${bid}" "")"
    if [ "${SIG_GCP_MODE}" = "check" ]; then
      _plan "gcloud run jobs update ${job} --args \"${before}\"   # restores the declared non-wacz shape exactly (evidence is never touched)"
    else
      run gcloud run jobs update "${job}" \
        --project "${SIG_GCP_PROJECT}" --region "${SIG_GCP_REGION}" \
        --args "${before}"
    fi
  done < <(wacz_jobs)
}

run_all() {
  leg_prestate; leg_jobs; leg_run; leg_probe; leg_verify
}

# ---------------------------------------------------------------------------
banner "P37.56 WACZ capture — HTML document jobs"
assert_window   # gates every apply leg (read legs still record under the guard)

case "${ACTION}" in
  prestate)  leg_prestate ;;
  jobs)      leg_jobs ;;
  run)       leg_run ;;
  probe)     leg_probe ;;
  poststate|verify) leg_verify ;;
  rollback)  leg_rollback ;;
  all)       run_all ;;
  *) _log "unknown ACTION '${ACTION}'"; _usage 64 ;;
esac

_log "done (mode=${SIG_GCP_MODE}, action=${ACTION}). state=${EVIDENCE_DIR}"
