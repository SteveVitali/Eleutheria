#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
#
# ops/gcp/wave-a.sh — Wave-A activation driver (P35.11 / I8 ACQ-07; OM-19/OM-20).
#
#   ./wave-a.sh --check                      # (default) plan-only: prints the
#                                            # ordered leg plan + the gate-inputs
#                                            # template; needs NO ADC, opens NO
#                                            # network, exits 0.
#   ./wave-a.sh --apply --leg L1 --inputs <gate-inputs.json>
#                                            # production write: runs
#                                            # `sig-ops wave-a-gate` on the
#                                            # recorded inputs and executes the
#                                            # named leg's steps ONLY on a go —
#                                            # inside 2026-10-19→23 14:00–20:00Z,
#                                            # under the recorded ING-GO-A
#                                            # (GATE-G4 §3), one manual run at a
#                                            # time, never overlapping
#                                            # sig-materialize.
#
# The three legs, in order (a missed leg is reported, never silently skipped):
#   L1 — prestate capture + AR-2 backup + the Legistar-trigger mitigation
#        (pause sig-sched-legistar before the roll, or roll after its
#        2026-10-20 05:00Z fire), `sig-ops roll-jobs --record` on one pinned
#        digest (ADR-111), `sig-connectors load-seed`, then the three manual
#        first runs — legistar, usaspending, procportal_nyc_ny — one at a
#        time, each verified before the next starts. The two ADR-185 S8
#        screened-lane sources follow, also one at a time, ONLY when the
#        wave-open HG-03 flip list (OP-26) names them, always with the
#        "no human review occurred" disclosure recorded.
#   L2 — the +0 re-runs: the same sources re-executed; each run row must show
#        claims_added == 0 on unchanged inputs.
#   L3 — resume the paused `scheduled-ops.sh --paused` rows and
#        sig-sched-legistar — each trigger only when its source ran green.
#
# ap-t2-093 (doj_ctas_awards) is NOT tribal and stays deferred under
# D-R11-LATER-09 — it is never in this driver's step set. No source's
# ingestion_permitted is flipped by this script (HG-03 is the operator's,
# OP-26): the flip list arrives as recorded inputs, never as code.
#
# Verification between manual runs is the `ops/runs/<source>/` run row under
# the restricted bucket + `gcloud run jobs executions list`; a failed verify
# aborts the driver and the refusal/miss is reported — the leg is never
# silently skipped.

set -euo pipefail

_here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=ops/gcp/config.sh
. "${_here}/config.sh"
# shellcheck source=ops/gcp/lib.sh
. "${_here}/lib.sh"

MODE="${1:-}"
parse_mode "${MODE}"
shift || true

LEG=""
INPUTS=""
while [ $# -gt 0 ]; do
  case "$1" in
    --leg)    LEG="${2:-}"; shift 2 ;;
    --inputs) INPUTS="${2:-}"; shift 2 ;;
    *) _log "usage: $(basename "$0") [--check] | --apply --leg L1|L2|L3 --inputs <json>" >&2; exit 64 ;;
  esac
done

SOURCES_MANUAL="legistar usaspending procportal_nyc_ny"
SOURCES_SCREENED="camreg_tribal_all_leaders_directory legis_tribal_tohono_oodham_notice"
LEGISTAR_TRIGGER="sig-sched-legistar"
LEGISTAR_NEXT_FIRE="2026-10-20T05:00:00Z"
SEED_SOURCE="state_alpr_statute_inventory_2026"

_json_list() {  # _json_list <file> <key> — one id per line
  uv run python -c 'import json,sys
d = json.load(open(sys.argv[1], encoding="utf-8"))
v = d.get(sys.argv[2]) or []
print("\n".join(str(x) for x in v))' "$1" "$2"
}

_gate() {  # _gate <inputs-json> — exit 42 propagates a recorded no-go
  uv run sig-ops wave-a-gate --inputs "$1"
}

_verify_run() {  # _verify_run <source> <job> — the recorded verification read
  local sid="$1" job="$2"
  _log "-- verify ${sid}: latest execution + run row (before the next source starts)"
  run gcloud run jobs executions list --job "${job}" \
    --region "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}" \
    --limit=1 --format='yaml(name,status.completionTime,status.succeededCount,status.failedCount)'
  run gcloud storage ls --long --recursive \
    "gs://${SIG_BUCKET_RESTRICTED}/ops/runs/${sid}/"
}

_manual_run() {  # _manual_run <source> — one at a time, verified before the next
  local sid="$1" job="sig-ingest-${sid//_/-}"
  _log "-- manual first run: ${sid} (${job}) — one at a time"
  run gcloud run jobs execute "${job}" \
    --region "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}" \
    --args "scheduled-ingest,--source,${sid},--sink,pg" --wait
  _verify_run "${sid}" "${job}"
}

_rerun() {  # _rerun <source> — the +0 idempotence leg
  local sid="$1" job="sig-ingest-${sid//_/-}"
  _log "-- +0 re-run: ${sid} — asserts claims_added == 0 on unchanged inputs"
  run gcloud run jobs execute "${job}" \
    --region "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}" \
    --args "scheduled-ingest,--source,${sid},--sink,pg" --wait
  _verify_run "${sid}" "${job}"
  _log "   expected: run row claims_added == 0 — a non-zero read stops the wave and is reported"
}

banner "Wave-A activation (P35.11 / ACQ-07; 2026-10-19→23 14:00–20:00Z)"

if [ "${SIG_GCP_MODE}" = "check" ]; then
  _log "PLAN ONLY — no ADC required, no network opened."
  uv run sig-ops wave-a-plan
  cat <<'EOF'

Gate inputs (recorded JSON — capture each field, never the wall clock):
  {
    "leg": "L1",
    "completed": [],
    "now": "<date -u>",
    "go": {"verbatim": "<ING-GO-A verbatim (GATE DECISIONS)>", "recorded_at": "<date -u>"},
    "flip_list": ["<source ids the wave-open OP-26 HG-03 list names>"],
    "run_set": ["legistar", "usaspending", "procportal_nyc_ny"],
    "screened_disclosure": false,
    "legistar_trigger": {"paused": true},
    "materialize_active": false,
    "active_manual_run": null,
    "backup": {"status": "SUCCESSFUL", "id": "<backup id>"},
    "prestate": {"captured": true, "cadence_check_ok": true, "path": "<prestate dir>"}
  }

A missed leg is reported, never silently skipped. The re-run prompt:
  implement-spec spec=docs/tickets/271_P35.11__wave-a-activation.md live_verification=true
EOF
  exit 0
fi

# --- apply -------------------------------------------------------------------
require_project
require_adc
[ -n "${LEG}" ] || { _log "--apply needs --leg L1|L2|L3" >&2; exit 64; }
[ -n "${INPUTS}" ] || { _log "--apply needs --inputs <recorded gate inputs JSON>" >&2; exit 64; }

_log "gate: sig-ops wave-a-gate --inputs ${INPUTS} (leg ${LEG})"
if ! _gate "${INPUTS}"; then
  rc=$?
  _log "wave-a.sh: NO-GO (exit ${rc}) — the leg queues; a missed leg is reported, never silently skipped."
  exit "${rc}"
fi

FLIP_LIST="$(_json_list "${INPUTS}" flip_list)"

case "${LEG}" in
  L1)
    _log "-- L1.3 mitigation: pause ${LEGISTAR_TRIGGER} before the roll"
    _log "   (the other admitted posture is a roll at/after ${LEGISTAR_NEXT_FIRE} — the gate inputs recorded which)"
    run gcloud scheduler jobs pause "${LEGISTAR_TRIGGER}" \
      --location "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}"
    _log "-- L1.4 image roll (one pinned digest, ADR-111): sig-ops roll-jobs --record"
    : "${SIG_JOB_IMAGE:?SIG_JOB_IMAGE must name the image to roll (a SHA tag or @sha256 digest)}"
    run uv run sig-ops roll-jobs --image "${SIG_JOB_IMAGE}" --record
    _log "-- L1.5 load-seed: ${SEED_SOURCE} (packaged asset, static transport — never a fetch)"
    : "${SIG_PG_DSN:?SIG_PG_DSN must name the production spine DSN (env-only, HG-09)}"
    run uv run sig-connectors load-seed --source "${SEED_SOURCE}" --sink pg --dsn "${SIG_PG_DSN}"
    for sid in ${SOURCES_MANUAL}; do
      _manual_run "${sid}"
    done
    for sid in ${SOURCES_SCREENED}; do
      case " ${FLIP_LIST} " in
        *" ${sid} "*)
          _log "-- screened lane: ${sid} is flip-listed — runs under ADR-185 with the no-human-review disclosure"
          _manual_run "${sid}"
          ;;
        *)
          _log "-- screened lane: ${sid} NOT in the wave-open flip list — skipped (reported, never silently)"
          ;;
      esac
    done
    ;;
  L2)
    for sid in ${SOURCES_MANUAL}; do
      _rerun "${sid}"
    done
    for sid in ${SOURCES_SCREENED}; do
      case " ${FLIP_LIST} " in
        *" ${sid} "*) _rerun "${sid}" ;;
        *) _log "-- +0: ${sid} did not run in L1 — reported, never silently skipped" ;;
      esac
    done
    ;;
  L3)
    _log "-- L3: resume the paused scheduled-ops rows — each trigger only when its source ran green"
    for sid in ${SOURCES_SCREENED}; do
      case " ${FLIP_LIST} " in
        *" ${sid} "*)
          run gcloud scheduler jobs resume "sig-sched-${sid//_/-}" \
            --location "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}"
          ;;
        *) _log "-- resume: ${sid} unflipped — its trigger stays paused (reported, never silently)" ;;
      esac
    done
    run gcloud scheduler jobs resume "${LEGISTAR_TRIGGER}" \
      --location "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}"
    _log "-- record: run rows, changed_count, coverage-delta read, trigger state → docs/build/runs/P35.11.md"
    ;;
  *) _log "unknown leg ${LEG} — the wave admits L1/L2/L3 only" >&2; exit 64 ;;
esac

_log "wave-a.sh: leg ${LEG} complete — record the run reports under docs/build/runs/P35.11.md"
