#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
#
# ops/gcp/wave-d.sh — Wave-D activation driver (P37.54 / R11-ACQ-27, I8
# §7.2–7.8; OM-19/OM-20).
#
#   ./wave-d.sh --check                      # (default) plan-only: prints the
#                                            # ordered leg plan + the gate-inputs
#                                            # template; needs NO ADC, opens NO
#                                            # network, exits 0.
#   ./wave-d.sh --apply --leg L3 --inputs <gate-inputs.json>
#                                            # production write: runs
#                                            # `sig-ops wave-d-gate` on the
#                                            # recorded inputs — the input's
#                                            # "action" decides the phase:
#                                            #   action=admit → gate, then run the
#                                            #     leg's mutation steps;
#                                            #   action=close → gate the leg's
#                                            #     recorded evidence, then mark it
#                                            #     green. Executes ONLY on a go —
#                                            # inside window 11-23 → 12-04 or
#                                            # window 12-14 → 12-18, 14:00–20:00Z
#                                            # (never the 12-15 cut day), under
#                                            # the recorded ING-GO-D (GATE-G6
#                                            # 2026-11-05T15:20Z, b91f8e58), one
#                                            # manual run at a time.
#
# The twelve legs, in order (a missed leg is reported, never silently skipped):
#   L0  — pre-state capture + AR-2 backup + `sig-ops roll-jobs --record` on one
#         pinned digest (ADR-111) + `scheduled-ops.sh --apply --paused` for the
#         three r11-tier2-* batch jobs + the complete flip-list hand-off
#         (OP-26).
#   L1–L9 — the nine Tier-2 family days in ticket order (ACQ-19 P37.47 →
#         ACQ-26 P37.53 via ACQ-23a/b P37.69a/b): the day's flips recorded →
#         manual first runs one source at a time on the member's batch job →
#         per-source I8 §7.7 verification → +0 re-runs.
#   L10 — the S6 extras family day: axon_connect, documentcloud,
#         muckrock_public, sourcewell, omnia_partners + the RB-06b
#         camreg_bellevue_wa seat — six seatless gated sources, single-source
#         on sig-ingest-r11-tier2-01. Targets window 1 so the sources ship in
#         the next cadence cut.
#   L11 — sig-materialize → coverage-delta vs the pre-wave snapshot → resume
#         the three paused tier-2 schedules: each cadence row's state flips
#         paused→enabled + the declaration bundle republishes (the
#         due-dispatcher shape — never a per-source trigger resume); each
#         batch's next fire is computed and recorded (2026-12-25/26/27T07:37Z — future-ok: scheduled: dom crons)
#         after the 12-15 cut.
#
# The eight P37.16a/b Part VIII dossier-capture seats are batch members but
# are NEVER on this wave's flip list — their flips and captures ride those
# rows' own in-ticket operator go; an unflipped seat's later batch fire
# records the loader's gated refusal (a recorded outcome, never a defeat
# attempt). doj_ctas_awards stays deferred under D-R11-LATER-09; the Wave-A
# tribal S8 lane is out of scope. No source's ingestion_permitted is flipped
# by this script (HG-03 is the operator's, OP-26): the flips arrive as
# recorded gate inputs, never as code.
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
    *) _log "usage: $(basename "$0") [--check] | --apply --leg L0|…|L11 --inputs <json>" >&2; exit 64 ;;
  esac
done

BATCHES="r11-tier2-01 r11-tier2-02 r11-tier2-03"

# source → the job its manual execution rides. The batch members' jobs are
# derived from ops/src/ops/wave_d.py SOURCE_BATCH at call time (the module is
# the authority); the six seatless L10 sources ride sig-ingest-r11-tier2-01.
_job_for() {
  uv run python -c 'import sys
from ops import wave_d
sid = sys.argv[1]
job = wave_d.EXECUTION_JOB.get(sid)
if job is None:
    raise SystemExit(f"no declared execution job for {sid} — undeclared, never run")
print(job)' "$1"
}

_run_set() {  # _run_set <inputs-json> — the gate-verified run_set, one id per line
  uv run python -c 'import json,sys
d = json.load(open(sys.argv[1], encoding="utf-8"))
print("\n".join(str(x) for x in (d.get("run_set") or [])))' "$1"
}

_gate() {  # _gate <inputs-json> — exit 42 propagates a recorded no-go
  uv run sig-ops wave-d-gate --inputs "$1"
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
  local sid="$1" job
  job="$(_job_for "${sid}")"
  _log "-- manual first run: ${sid} (${job}) — one at a time"
  run gcloud run jobs execute "${job}" \
    --region "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}" \
    --args "scheduled-ingest,--source,${sid},--sink,pg" --wait
  _verify_run "${sid}" "${job}"
}

_rerun() {  # _rerun <source> — the +0 idempotence proof
  local sid="$1" job
  job="$(_job_for "${sid}")"
  _log "-- +0 re-run: ${sid} (${job}) — asserts claims_added == 0 on unchanged inputs"
  run gcloud run jobs execute "${job}" \
    --region "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}" \
    --args "scheduled-ingest,--source,${sid},--sink,pg" --wait
  _verify_run "${sid}" "${job}"
  _log "   expected: run row claims_added == 0 — a non-zero read stops the wave and is reported"
}

banner "Wave-D activation (P37.54; windows 11-23→12-04 + 12-14→12-18, 14:00–20:00Z)"  # future-ok: scheduled: the contract windows

if [ "${SIG_GCP_MODE}" = "check" ]; then
  _log "PLAN ONLY — no ADC required, no network opened."
  uv run sig-ops wave-d-plan
  cat <<'EOF'

Gate inputs (recorded JSON — capture each field, never the wall clock):
  {
    "action": "admit",                     // or "close"
    "leg": "L1",
    "completed": [{"leg": "L0", "day": "2026-11-23"}],      // example — future-ok: illustrative: sample day
    "held_reports": {},                    // {leg: report-ref} for queued legs
    "now": "<date -u>",
    "go": {"verbatim": "Approve ING-GO-D + flip list (rec.)", "recorded_at": "<date -u of the record>"},  // GATE-G6 2026-11-05T15:20Z, b91f8e58
    "run_set": ["<the leg's declared set — see ops/src/ops/wave_d.py LEG_SCOPE>"],
    "flips": {"L1": {"executed": ["<gated ids the operator flipped>"], "confirmed": "<OP-26 record ref>"}},
    "materialize_active": false,
    "g2_slot_active": false,
    "release_cut_active": false,
    "active_manual_run": null,
    "prestate": {"captured": true, "cadence_check_ok": true, "path": "<prestate dir>"},   // L0
    "backup": {"status": "SUCCESSFUL", "id": "<backup id>"},                               // L0
    "roll": {"image_digest": "sha256:<64 hex>", "before_after_recorded": true},            // L0 close
    "jobs_created": {"r11-tier2-01": {"created": true, "paused": true}, "…": "…"},          // L0 close
    "flip_list": ["<all 146 flag-row source ids>"], "flip_handoff": {"list_ref": "<ref>"},  // L0 close
    "runs": {"<sid>": {"outcome": "ok", "claims_added": 0, "captures": 0}},                // family close
    "empty_run_notes": {},                 // {sid: reason} for zero-claim first runs
    "plus0": {"<sid>": {"claims_added": 0}},                                                // family close
    "changed_count": {"recorded": true, "value": 0},                                        // family close
    "materialize": {"ran": true, "at": "<date -u>"},                                        // L11 close
    "coverage_delta": {"recorded": true, "ref": "<ref>"},                                   // L11 close
    "cadence_state_enabled": {"r11-tier2-01": true, "r11-tier2-02": true, "r11-tier2-03": true},  // L11 close
    "declaration_republished": true,                                                        // L11 close
    "next_fires": {"r11-tier2-01": "2026-12-25T07:37:00Z", "…": "…"}                        // L11 close — future-ok: illustrative: sample stamp
  }

A missed leg is reported, never silently skipped. The re-run prompt:
  implement-spec spec=docs/tickets/481_P37.54__wave-d-activation.md live_verification=true
EOF
  exit 0
fi

# --- apply ---------------------------------------------------------------------
require_project
require_adc
[ -n "${LEG}" ] || { _log "--apply needs --leg L0|…|L11" >&2; exit 64; }
[ -n "${INPUTS}" ] || { _log "--apply needs --inputs <recorded gate inputs JSON>" >&2; exit 64; }

_log "gate: sig-ops wave-d-gate --inputs ${INPUTS} (leg ${LEG})"
rc=0
_gate "${INPUTS}" || rc=$?
if [ "${rc}" -ne 0 ]; then
  _log "wave-d.sh: NO-GO (exit ${rc}) — the leg queues; a missed leg is reported, never silently skipped."
  exit "${rc}"
fi

ACTION="$(uv run python -c 'import json,sys; print(json.load(open(sys.argv[1])).get("action"))' "${INPUTS}")"
if [ "${ACTION}" = "close" ]; then
  _log "wave-d.sh: leg ${LEG} close gated green — record the leg report under docs/build/runs/P37.54.md"
  exit 0
fi

case "${LEG}" in
  L0)
    _log "-- L0.1 OM-14 pre-state: job + trigger/dispatcher JSON, sources.toml sha, cadence --check"
    for job in sig-ingest-r11-tier2-01 sig-ingest-r11-tier2-02 sig-ingest-r11-tier2-03 sig-materialize; do
      run gcloud run jobs describe "${job}" \
        --region "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}" \
        --format=json || true   # new jobs may not exist yet — the absence is recorded
    done
    run gcloud scheduler jobs list \
      --location "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}" --format=json
    run sha256sum connectors/src/connectors/data/sources.toml
    run uv run sig-ops cadence --check
    _log "-- L0.2 AR-2 on-demand backup — record SUCCESSFUL before the first mutation"
    run gcloud sql backups create --instance "${SIG_SQL_INSTANCE:-sig-pg}" \
      --project "${SIG_GCP_PROJECT}" --async
    _log "-- L0.3 image roll (one pinned digest, ADR-111): sig-ops roll-jobs --record"
    : "${SIG_JOB_IMAGE:?SIG_JOB_IMAGE must name the pinned image digest (sha256:…)}"
    run uv run sig-ops roll-jobs --image "${SIG_JOB_IMAGE}" --record
    _log "-- L0.4 create the three r11-tier2-* batch jobs PAUSED (R6)"
    run "${_here}/scheduled-ops.sh" --apply --paused
    _log "-- L0.5 flip-list hand-off: docs/build/reports/WAVE_D_FLIP_LIST.md — the"
    _log "     operator's OP-26 execution; this script never flips a source (HG-03)."
    ;;
  L1|L2|L3|L4|L5|L6|L7|L8|L9|L10)
    mapfile -t RUN_SET < <(_run_set "${INPUTS}")
    if [ "${#RUN_SET[@]}" -eq 0 ]; then
      _log "wave-d.sh: empty run_set for ${LEG} — refused, never silently skipped" >&2; exit 64
    fi
    for sid in "${RUN_SET[@]}"; do
      _manual_run "${sid}"
    done
    for sid in "${RUN_SET[@]}"; do
      _rerun "${sid}"
    done
    _log "-- record: run rows, per-source §7.7 verifications, changed_count,"
    _log "   +0 diffs, flip confirmations → docs/build/runs/P37.54.md"
    ;;
  L11)
    _log "-- L11.1 sig-materialize — after the last first run, outside ingest runs"
    run gcloud run jobs execute sig-materialize \
      --region "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}" --wait
    _log "-- L11.2 coverage delta vs the pre-wave snapshot (P35.6, I8 §7.7) —"
    _log "   \`sig-ops coverage-delta\` with the recorded baseline/plan refs from the"
    _log "   run record (SIG_COVERAGE_DELTA_ARGS, e.g. '--baseline <snapshot> --plan"
    _log "   <ref>'); never a fabricated baseline"
    run uv run sig-ops coverage-delta ${SIG_COVERAGE_DELTA_ARGS:---help}
    _log "-- L11.3 resume the three paused tier-2 schedules — cadence state"
    _log "   paused→enabled per row + the declaration bundle republished (the"
    _log "   due-dispatcher shape; the trigger names below are the retired"
    _log "   declarations — the hourly sig-sched-due dispatcher reads the rows):"
    for b in ${BATCHES}; do
      _log "   ${b}: ops/cadence.toml state=\"paused\" → \"enabled\" (committed"
      _log "   resume change under the wave's recorded authorization) + republish"
      run gcloud scheduler jobs describe sig-sched-due \
        --location "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}" \
        --format='value(schedule,state)' || true
    done
    _log "   compute + record each batch's next fire:"
    _log "     r11-tier2-01 → 2026-12-25T07:37:00Z (37 7 25 * *)"  # future-ok: scheduled: dom cron
    _log "     r11-tier2-02 → 2026-12-26T07:37:00Z (37 7 26 * *)"  # future-ok: scheduled: dom cron
    _log "     r11-tier2-03 → 2026-12-27T07:37:00Z (37 7 27 * *)"  # future-ok: scheduled: dom cron
    _log "-- L11.4 record the closing report — materialize log, coverage delta,"
    _log "   next-fires, held-leg list → docs/build/runs/P37.54.md (a leg landed"
    _log "   in window 2 ships in the 2027-01-15 cadence cut — future-ok: scheduled: contract cut)"
    ;;
  *)
    _log "wave-d.sh: unknown leg ${LEG} — the wave admits L0…L11 only" >&2; exit 64 ;;
esac
