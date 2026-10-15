#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
#
# ops/gcp/wave-b.sh — Wave-B activation driver (P36.12 / I8 §7.2–7.8; OM-19/OM-20).
#
#   ./wave-b.sh --check                      # (default) plan-only: prints the
#                                            # ordered leg plan + the gate-inputs
#                                            # template; needs NO ADC, opens NO
#                                            # network, exits 0.
#   ./wave-b.sh --apply --leg L3 --inputs <gate-inputs.json>
#                                            # production write: runs
#                                            # `sig-ops wave-b-gate` on the
#                                            # recorded inputs — the input's
#                                            # "action" decides the phase:
#                                            #   action=admit → gate, then run the
#                                            #     leg's mutation steps;
#                                            #   action=close → gate the leg's
#                                            #     recorded evidence, then mark it
#                                            #     green. Executes ONLY on a go —
#                                            # inside 2026-10-26→11-05 14:00–20:00Z — future-ok: scheduled: the contract window,
#                                            # under the recorded verbatim
#                                            # ING-GO-B (GATE-G4 §3), one manual
#                                            # run at a time, never overlapping
#                                            # sig-materialize, the peel-on fire
#                                            # or a G2 slot.
#
# The eleven legs, in order (a missed leg is reported, never silently skipped):
#   L0  — pre-state capture + AR-2 backup + `sig-ops roll-jobs --record` on one
#         pinned digest (ADR-111) + `scheduled-ops.sh --apply --paused` for the
#         seven r11-* batch jobs + the OPERATOR-RUN hosted `vocab_*`
#         registration of enforcement_count (sqitch deploy
#         vocab_enforcement_count — named, never executed by this script) + the
#         complete flip-list hand-off (OP-26).
#   L1–L8 — family days ACQ-08…ACQ-15 (one family per day; ACQ-11 + ACQ-15 may
#         share): the day's flips recorded → manual first runs one source at a
#         time → per-source I8 §7.7 verification → +0 re-runs. Widen targets
#         run as single-source executions on their existing jobs (the next
#         scheduled fire is then a +0); the six registered ccops_* rows
#         execute on the documents-family job.
#   L9  — the Flock transparency-portal probe (P36.74, WV-10): one polite
#         request per committed portal (917), stop-and-record on any challenge;
#         every outcome lands in the sig.probe-run/1 record.
#   L10 — sig-materialize → coverage-delta vs the pre-wave snapshot → resume
#         the seven paused triggers; each batch's next fire is computed and
#         recorded at resume (the four pre-11-20 fires carry FEA-15
#         dispositions — surfaced, never silently accepted).
#
# doj_ctas_awards (AP-T2-093) is NOT tribal and stays deferred under
# D-R11-LATER-09; the ADR-185 tribal S8 lane landed at P35.11 (Wave A) — neither
# is in this driver's step set. No source's ingestion_permitted is flipped by
# this script (HG-03 is the operator's, OP-26): the flips arrive as recorded
# gate inputs, never as code. The hosted vocab_* registration is an
# operator-run step named here, never executed by this script.
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
    *) _log "usage: $(basename "$0") [--check] | --apply --leg L0|…|L10 --inputs <json>" >&2; exit 64 ;;
  esac
done

# The leg → run_set declarations (kept byte-identical to ops/src/ops/wave_b.py
# LEG_SCOPE — the gate is the authority; this map names the execution jobs).
L1_GATED="dot_511_de dot_511_vt dot_511_wv dot_511_mi camreg_ne_lincoln_traffic_cameras camreg_omaha_ne_parks_cameras camreg_hyattsville_md_cctv_camera_2024 dot_511_nc"
L1_WIDEN="camreg_denver_co camreg_seattle_wa"
L2_GATED="camreg_fdot_flock camreg_pueblo_co_flock camreg_rocky_mount_nc_lpr_cameras camreg_shelbyville_tn_flock_cameras camreg_temecula_ca_flock_wfl1 camreg_marble_falls_tx_flock_locations camreg_va_prince_william_county camreg_milford_ct_flocklprcam camreg_elgin_il_lpr_cameras camreg_south_fulton_ga_lpr_cameras camreg_va_pittsylvania_county_stationary camreg_alabaster_al_lpr_cameras camreg_thomasville_ga_flock_location camreg_leon_county_fl_overwatch_viewer camreg_ga_peachtree_corners_flock_camera"
L3_GATED="camreg_dc_ddot_ate camreg_montgomery_md_ate camreg_nyc_mta_bus_lane_ate camreg_tacoma_wa_ate camreg_howard_md_school_zone_ate camreg_lakeland_fl_red_light camreg_suffolk_ny_red_light camreg_medford_or_ate camreg_ctdot_speed_safety"
L3_WIDEN="camreg_chicago_il"
L4_GATED="procportal_cook_il_awards procportal_wa_des_contract_sales camreg_dc_ovsjg_camera_rebate"
L5_GATED="statrep_mn_bca statrep_va_rga statrep_wa_ago_alpr_registry statrep_va_vsp_alpr statrep_va_vscc_alpr statrep_ne_crime_commission_alpr statrep_vt_dps_alpr statrep_md_dls_mandated_reports statrep_il_isp_alpr statrep_austin_tx_auditor"
L6_GATED="statrep_me_dps_uav statrep_hi_judiciary_interception statrep_wa_watech_frt statrep_co_frt_accountability statrep_de_diac statrep_wa_wtsc_ate statrep_detroit_mi_frt_weekly statrep_us_dhs_privacy_compliance statrep_fl_flhsmv_red_light statrep_pa_wzssc statrep_md_msp_css statrep_mn_court_interception legis_us_dhs_sorn_plate_data statrep_seattle_wa_sdot_ate statrep_il_icjia_drone statrep_seattle_wa_oig"
L7_GATED="ccops_columbia_mo ccops_st_louis_mo ccops_dayton_oh ccops_anchorage_ak ccops_austin_tx policy_orange_county_ca_sheriff policy_pasadena_ca_pd policy_st_cloud_mn_isd742 policy_onslow_nc_schools policy_pflugerville_tx_isd policy_whitesboro_ny_csd policy_bangor_me_pd policy_houston_tx_hpd policy_albuquerque_nm_apd policy_little_rock_ar_pd legis_ca_gov_code_53166"
L7_HOSTED="ccops_berkeley ccops_davis ccops_boston ccops_baltimore ccops_nashville ccops_grand_rapids"
L8_GATED="agenda_haskell_ar_council agenda_des_moines_ia_council agenda_jasper_sc_council grant_al_adeca_psn grant_ca_bscc_ort grant_fl_senate_lfir grant_nj_oag_bwc grant_ok_dac_jag_lle grant_tx_txdmv_mvcpa legis_gu_governor procportal_davie_fl_purchasing procportal_forsyth_nc_purchasing"
L8_WIDEN="openstates"
L9_GATED="flock_transparency_portals"
BATCHES="r11-layers-01 r11-layers-02 r11-ate-01 r11-procurement-01 r11-disclosures-01 r11-disclosures-02 r11-documents-01"

# source → the job its manual execution rides (batch members: the family
# batch job; widen/hosted: the declared host job).
_job_for() {
  case "$1" in
    dot_511_de|dot_511_vt|dot_511_wv|dot_511_mi|camreg_ne_lincoln_traffic_cameras|camreg_omaha_ne_parks_cameras|camreg_hyattsville_md_cctv_camera_2024|dot_511_nc)
      printf 'sig-ingest-r11-layers-01' ;;
    camreg_fdot_flock|camreg_pueblo_co_flock|camreg_rocky_mount_nc_lpr_cameras|camreg_shelbyville_tn_flock_cameras|camreg_temecula_ca_flock_wfl1|camreg_marble_falls_tx_flock_locations|camreg_va_prince_william_county|camreg_milford_ct_flocklprcam|camreg_elgin_il_lpr_cameras|camreg_south_fulton_ga_lpr_cameras|camreg_va_pittsylvania_county_stationary|camreg_alabaster_al_lpr_cameras|camreg_thomasville_ga_flock_location|camreg_leon_county_fl_overwatch_viewer|camreg_ga_peachtree_corners_flock_camera)
      printf 'sig-ingest-r11-layers-02' ;;
    camreg_dc_ddot_ate|camreg_montgomery_md_ate|camreg_nyc_mta_bus_lane_ate|camreg_tacoma_wa_ate|camreg_howard_md_school_zone_ate|camreg_lakeland_fl_red_light|camreg_suffolk_ny_red_light|camreg_medford_or_ate|camreg_ctdot_speed_safety)
      printf 'sig-ingest-r11-ate-01' ;;
    procportal_cook_il_awards|procportal_wa_des_contract_sales|camreg_dc_ovsjg_camera_rebate)
      printf 'sig-ingest-r11-procurement-01' ;;
    statrep_me_dps_uav|statrep_hi_judiciary_interception|statrep_wa_watech_frt|statrep_co_frt_accountability|statrep_de_diac|statrep_wa_wtsc_ate|statrep_detroit_mi_frt_weekly|statrep_us_dhs_privacy_compliance|statrep_fl_flhsmv_red_light|statrep_pa_wzssc|statrep_md_msp_css|statrep_mn_court_interception|legis_us_dhs_sorn_plate_data|statrep_seattle_wa_sdot_ate|statrep_il_icjia_drone|statrep_seattle_wa_oig)
      printf 'sig-ingest-r11-disclosures-02' ;;
    statrep_mn_bca|statrep_va_rga|statrep_wa_ago_alpr_registry|statrep_va_vsp_alpr|statrep_va_vscc_alpr|statrep_ne_crime_commission_alpr|statrep_vt_dps_alpr|statrep_md_dls_mandated_reports|statrep_il_isp_alpr|statrep_austin_tx_auditor)
      printf 'sig-ingest-r11-disclosures-01' ;;
    ccops_columbia_mo|ccops_st_louis_mo|ccops_dayton_oh|ccops_anchorage_ak|ccops_austin_tx|policy_orange_county_ca_sheriff|policy_pasadena_ca_pd|policy_st_cloud_mn_isd742|policy_onslow_nc_schools|policy_pflugerville_tx_isd|policy_whitesboro_ny_csd|policy_bangor_me_pd|policy_houston_tx_hpd|policy_albuquerque_nm_apd|policy_little_rock_ar_pd|legis_ca_gov_code_53166|agenda_haskell_ar_council|agenda_des_moines_ia_council|agenda_jasper_sc_council|grant_al_adeca_psn|grant_ca_bscc_ort|grant_fl_senate_lfir|grant_nj_oag_bwc|grant_ok_dac_jag_lle|grant_tx_txdmv_mvcpa|legis_gu_governor|procportal_davie_fl_purchasing|procportal_forsyth_nc_purchasing)
      printf 'sig-ingest-r11-documents-01' ;;
    camreg_denver_co|camreg_chicago_il) printf 'sig-ingest-camreg-batch-02' ;;
    camreg_seattle_wa) printf 'sig-ingest-camreg-batch-06' ;;
    openstates) printf 'sig-ingest-openstates' ;;
    ccops_berkeley|ccops_davis|ccops_boston|ccops_baltimore|ccops_nashville|ccops_grand_rapids|flock_transparency_portals)
      printf 'sig-ingest-r11-documents-01' ;;
    *) _log "ERROR: no declared execution job for $1 — undeclared, never run" >&2; return 64 ;;
  esac
}

_run_set() {  # _run_set <inputs-json> — the gate-verified run_set, one id per line
  uv run python -c 'import json,sys
d = json.load(open(sys.argv[1], encoding="utf-8"))
print("\n".join(str(x) for x in (d.get("run_set") or [])))' "$1"
}

_gate() {  # _gate <inputs-json> — exit 42 propagates a recorded no-go
  uv run sig-ops wave-b-gate --inputs "$1"
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

banner "Wave-B activation (P36.12; 2026-10-26→11-05 14:00–20:00Z)"  # future-ok: scheduled: the contract window

if [ "${SIG_GCP_MODE}" = "check" ]; then
  _log "PLAN ONLY — no ADC required, no network opened."
  uv run sig-ops wave-b-plan
  cat <<'EOF'

Gate inputs (recorded JSON — capture each field, never the wall clock):
  {
    "action": "admit",                     // or "close"
    "leg": "L1",
    "completed": [{"leg": "L0", "day": "2026-10-26"}],
    "held_reports": {},                    // {leg: report-ref} for queued legs
    "now": "<date -u>",
    "go": {"verbatim": "<ING-GO-B verbatim (GATE DECISIONS)>", "recorded_at": "<date -u>"},
    "run_set": ["<the leg's declared set — see ops/src/ops/wave_b.py LEG_SCOPE>"],
    "flips": {"L1": {"executed": ["<gated ids the operator flipped>"], "confirmed": "<OP-26 record ref>"}},
    "materialize_active": false,
    "g2_slot_active": false,
    "release_cut_active": false,
    "peel_fire_cleared": true,             // required on 2026-10-29
    "active_manual_run": null,
    "prestate": {"captured": true, "cadence_check_ok": true, "path": "<prestate dir>"},   // L0
    "backup": {"status": "SUCCESSFUL", "id": "<backup id>"},                               // L0
    "roll": {"image_digest": "sha256:<64 hex>", "before_after_recorded": true},            // L0 close
    "jobs_created": {"r11-layers-01": {"created": true, "paused": true}, "…": "…"},         // L0 close
    "vocab": {"enforcement_count": {"registered": true, "verified": true}},                 // L0 close + L3
    "flip_list": ["<all 96 flag-row source ids>"], "flip_handoff": {"list_ref": "<ref>"},   // L0 close
    "runs": {"<sid>": {"outcome": "ok", "claims_added": 0, "captures": 0}},                // family close
    "empty_run_notes": {},                 // {sid: reason} for zero-claim first runs
    "plus0": {"<sid>": {"claims_added": 0}},                                                // family close
    "changed_count": {"recorded": true, "value": 0},                                        // family close
    "probe_run": {"version": "sig.probe-run/1", "inventory": {"portal_count": 917},
                  "results": [{"portal": "<slug>", "result": "served|refused|deferred|not_attempted",
                               "refusal_kind": "<kind — refused/deferred rows>"}],
                  "checks": {"coverage": {"verdict": "pass", "attempted": <int>},
                             "served": {"count": <int>}, "refusals": {"count": <int>, "deferred": <int>}}},  // L9 close
    "materialize": {"ran": true, "at": "<date -u>"},                                        // L10 close
    "coverage_delta": {"recorded": true, "ref": "<ref>"},                                   // L10 close
    "triggers_resumed": {"sig-sched-r11-layers-01": true, "…": "…"},                        // L10 close
    "next_fires": {"r11-layers-01": "2026-11-16T07:17:00Z", "…": "…"},                      // L10 close
    "early_fire_dispositions": {"r11-layers-01": "<FEA-15 disposition>", "…": "…"}          // L10 close
  }

A missed leg is reported, never silently skipped. The re-run prompt:
  implement-spec spec=docs/tickets/290_P36.12__wave-b-activation.md live_verification=true
EOF
  exit 0
fi

# --- apply ---------------------------------------------------------------------
require_project
require_adc
[ -n "${LEG}" ] || { _log "--apply needs --leg L0|…|L10" >&2; exit 64; }
[ -n "${INPUTS}" ] || { _log "--apply needs --inputs <recorded gate inputs JSON>" >&2; exit 64; }

_log "gate: sig-ops wave-b-gate --inputs ${INPUTS} (leg ${LEG})"
rc=0
_gate "${INPUTS}" || rc=$?
if [ "${rc}" -ne 0 ]; then
  _log "wave-b.sh: NO-GO (exit ${rc}) — the leg queues; a missed leg is reported, never silently skipped."
  exit "${rc}"
fi

ACTION="$(uv run python -c 'import json,sys; print(json.load(open(sys.argv[1])).get("action"))' "${INPUTS}")"
if [ "${ACTION}" = "close" ]; then
  _log "wave-b.sh: leg ${LEG} close gated green — record the leg report under docs/build/runs/P36.12.md"
  exit 0
fi

case "${LEG}" in
  L0)
    _log "-- L0.1 OM-14 pre-state: job + trigger JSON, sources.toml sha, cadence --check"
    for job in sig-ingest-r11-layers-01 sig-ingest-camreg-batch-02 sig-ingest-openstates sig-materialize; do
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
    _log "-- L0.4 create the seven r11-* batch jobs + triggers PAUSED (R6)"
    run "${_here}/scheduled-ops.sh" --apply --paused
    _log "-- L0.5 OPERATOR-RUN hosted step (named, never executed by this script):"
    _log "     sqitch deploy vocab_enforcement_count — INSERT-only: enforcement_count"
    _log "     into vocab_predicate — then sqitch verify. The ATE family emits"
    _log "     nothing before this lands (P36.6 / P35.14a closed sink)."
    _log "-- L0.6 flip-list hand-off: docs/build/reports/WAVE_B_FLIP_LIST.md — the"
    _log "     operator's OP-26 execution; this script never flips a source (HG-03)."
    ;;
  L1|L2|L3|L4|L5|L6|L7|L8|L9)
    mapfile -t RUN_SET < <(_run_set "${INPUTS}")
    if [ "${#RUN_SET[@]}" -eq 0 ]; then
      _log "wave-b.sh: empty run_set for ${LEG} — refused, never silently skipped" >&2; exit 64
    fi
    for sid in "${RUN_SET[@]}"; do
      _manual_run "${sid}"
    done
    if [ "${LEG}" != "L9" ]; then
      for sid in "${RUN_SET[@]}"; do
        _rerun "${sid}"
      done
    else
      _log "-- L9: the probe run is a single pass — no +0 re-probe (the sig.probe-run/1"
      _log "   record is the evidence; expected yield ≈ 0 is a recorded outcome)"
    fi
    _log "-- record: run rows, per-source §7.7 verifications, changed_count,"
    _log "   +0 diffs, flip confirmations → docs/build/runs/P36.12.md"
    ;;
  L10)
    _log "-- L10.1 sig-materialize — after the last first run, outside ingest runs"
    run gcloud run jobs execute sig-materialize \
      --region "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}" --wait
    _log "-- L10.2 coverage delta vs the pre-wave snapshot (P35.6, I8 §7.7) —"
    _log "   `sig-ops coverage-delta` with the recorded baseline/plan refs from the"
    _log "   run record (SIG_COVERAGE_DELTA_ARGS, e.g. '--baseline <snapshot> --plan"
    _log "   <ref>'); never a fabricated baseline"
    run uv run sig-ops coverage-delta ${SIG_COVERAGE_DELTA_ARGS:---help}
    _log "-- L10.3 resume the seven paused triggers; compute + record each next fire"
    for b in ${BATCHES}; do
      run gcloud scheduler jobs resume "sig-sched-${b}" \
        --location "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}"
      run gcloud scheduler jobs describe "sig-sched-${b}" \
        --location "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}" \
        --format='value(schedule,state)'
    done
    _log "-- record: materialize log, coverage delta, next-fires + FEA-15"
    _log "   dispositions for the four pre-11-20 fires → docs/build/runs/P36.12.md"
    ;;
  *) _log "unknown leg ${LEG} — the wave admits L0…L10 only" >&2; exit 64 ;;
esac

_log "wave-b.sh: leg ${LEG} admit-phase steps executed — collect the close evidence and re-gate with action=close"
