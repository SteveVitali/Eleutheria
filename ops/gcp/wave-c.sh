#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
#
# ops/gcp/wave-c.sh — Wave-C activation driver (P37.2 / I8 §4.3 ACQ-18 + §7.4 +
# §7.7 + §7.8; OM-19/OM-20): the sequenced operation that turns OSM from
# mirror-republisher into the origin of the national ALPR layer.
#
#   ./wave-c.sh --check                      # (default) plan-only: prints the
#                                            # ordered leg plan + the gate-inputs
#                                            # template; needs NO ADC, opens NO
#                                            # network, exits 0.
#   ./wave-c.sh --apply --leg L1 --inputs <gate-inputs.json>
#                                            # production write: runs
#                                            # `sig-ops wave-c-gate` on the
#                                            # recorded inputs — the input's
#                                            # "action" decides the phase:
#                                            #   action=admit → gate, then run the
#                                            #     leg's steps;
#                                            #   action=close → gate the leg's
#                                            #     recorded evidence, then mark it
#                                            #     green. Executes ONLY on a go —
#                                            # inside the contract window
#                                            # 2026-11-16→11-20 (future-ok: scheduled: win; earliest 10-26
#                                            # when P37.1/PKG-07/Q-23 are all
#                                            # recorded landed), never inside
#                                            # AR-3's 03:00–06:30Z never-band,
#                                            # under the recorded verbatim
#                                            # ING-GO-C (GATE-G5 §3), one manual
#                                            # run at a time.
#
# The five legs, in order (a missed leg is reported, never silently skipped):
#   L1  — OM-14 pre-state capture → AR-2 on-demand backup verified SUCCESSFUL →
#         disk pre-grow to 25 GB + autoresize limit confirmed at 40 GB (Q-23's
#         adopted posture; the grow is one-way — a resumed run reads the current
#         state and records a SKIP, never re-grows blindly).
#   L2  — tier bump after the go: the operator's verbatim in-ticket go is a
#         GATE INPUT (asked when the leg is due — this script never asks and
#         never assumes; ING-GO-C is the wave's go, not the tier's) →
#         --tier=db-custom-2-7680 → poll UPDATE → api /health → read-back.
#   L3  — the national run: the Wave-B pause posture recorded (the four
#         early-fire r11 batch rows bound by the declared paused_until — FEA-15)
#         → `scheduled-ops.sh --apply` reconciles the fleet on one pinned digest
#         (sig-ingest-osm-overpass carries P37.1's national-tile code;
#         sig-ingest-camreg-batch-05 carries the committed mirror-retirement
#         diff) and republishes the declaration bundle (the monthly
#         `12 8 24 * *` retarget + the paused_until rows bind at publish —
#         SIG-OPS-005) → the first national fetch MANUAL (US-first ordering,
#         non-US objects kept — S5-4) → the §7.7 verify set → the +0 re-run →
#         the camera-site ER rematerialize → the mirror-retirement record
#         (exactly osm_surveillance_deflock + osm_surveillance_alpr_nationwide
#         out of camreg-batch-05; the four small CCTV republish targets stay;
#         derived_from recorded under PKG-12 ED-49; the next-fire recorded
#         after the retirement — §7.8: below the 95% merge bound the republish
#         targets stay scheduled and the retirement does not close).
#   L4  — the 24 h soak read (read-only — inside the window or the 48 h grace
#         after it; ≥24 h after the recorded run end).
#   L5  — revert: --tier=db-custom-1-3840 → poll UPDATE → api /health → the
#         post-state capture and the closeout record.
#
# Restore points (OM-14): the AR-2 backup before the grow; the committed
# mirror rows under camera_registry_targets.toml [[enumerated]] (re-add under
# [[targets]] to restore); the prior image digest from the roll record; the
# cadence.toml diff reverts the retarget + the paused_until lines. Rollback
# (I8 §7.8): if the ER evidence is below bound, re-point sig-ingest-
# camreg-batch-05 to the previous digest before the 12-10 fire — the
# republish targets stay scheduled.
#
# Verification between steps is the ops/runs/<source>/ run row under the
# restricted bucket + `gcloud run jobs executions list` + the Cloud SQL
# describe read-backs; a failed verify aborts the driver and the refusal/miss
# is reported — the leg is never silently skipped. No source's
# ingestion_permitted is flipped by this script (review-status is READ,
# never written — HG-03 is the operator's). Nothing publishes (HG-11 rides
# P37.65).

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
    *) _log "usage: $(basename "$0") [--check] | --apply --leg L1|…|L5 --inputs <json>" >&2; exit 64 ;;
  esac
done

OSM_JOB="sig-ingest-osm-overpass"
BATCH_JOB="sig-ingest-camreg-batch-05"
EARLY_FIRE_SCHEDS="sig-sched-r11-layers-01 sig-sched-r11-layers-02 sig-sched-r11-ate-01 sig-sched-r11-procurement-01"

_gate() {  # _gate <inputs-json> — exit 42 propagates a recorded no-go
  uv run sig-ops wave-c-gate --inputs "$1"
}

_read() {  # _read <gcloud args…> — a live read (never in check mode)
  gcloud "$@"
}

_wait_op() {
  # $1 op name; polls `sql operations describe` to DONE (<=20 min). Mirrors
  # protect.sh's waiter — a failed op is a leg failure, never smoothed.
  local name="$1" tries=0 body status
  while [ $tries -lt 120 ]; do
    body="$(_read sql operations describe "$name" --project "${SIG_GCP_PROJECT}" --format=json)" || {
      _log "wave-c.sh: op $name describe failed" >&2; return 5; }
    status="$(printf '%s' "$body" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("status",""))')"
    case "$status" in
      DONE)
        _log "op $name: DONE"
        return 0 ;;
      RUNNING|PENDING) sleep 10; tries=$((tries+1)) ;;
      *) _log "wave-c.sh: op $name unexpected status '$status'" >&2; return 5 ;;
    esac
  done
  _log "wave-c.sh: op $name did not finish in 20 min" >&2; return 5
}

_api_health() {
  local url="${SIG_API_HEALTH_URL:-}" code
  if [ -z "$url" ]; then
    url="$(_read run services describe "${SIG_RUN_SERVICE}" --region "${SIG_GCP_REGION}" \
      --project "${SIG_GCP_PROJECT}" --format='value(status.url)' 2>/dev/null || true)"
    [ -n "$url" ] && url="${url}/health"
  fi
  if [ -z "$url" ]; then
    _log "health: no api url resolvable (set SIG_API_HEALTH_URL) — recorded, not blocking"
    return 0
  fi
  code="$(curl -sS -o /dev/null -w '%{http_code}' "$url" || true)"
  _log "health: GET $url -> $code"
  [ "$code" = "200" ]
}

_apply_patch() {
  # _apply_patch <label> <patch args…> — issue the instance patch, poll the op
  # to DONE. In check mode `run` plans; apply mode issues + polls for real.
  local label="$1"; shift
  local op opname
  if [ "${SIG_GCP_MODE}" = "check" ]; then
    _plan "gcloud sql instances patch ${SIG_SQL_INSTANCE} $* --async --project ${SIG_GCP_PROJECT}   # ${label}"
    _plan "  poll 'gcloud sql operations describe <op>' until DONE"
    return 0
  fi
  op="$(gcloud sql instances patch "${SIG_SQL_INSTANCE}" "$@" --async \
        --project "${SIG_GCP_PROJECT}" --format=json)" || {
    _log "wave-c.sh: patch '$label' submit failed" >&2; return 5; }
  opname="$(printf '%s' "$op" | python3 -c 'import json,sys; print(json.load(sys.stdin)["name"])')"
  _log "patch '${label}': issued op $opname"
  _wait_op "$opname"
}

_sql_field() {  # _sql_field <python-expr-over-settings> — read one field
  _read sql instances describe "${SIG_SQL_INSTANCE}" --project "${SIG_GCP_PROJECT}" \
    --format=json | python3 -c "import json,sys; s=json.load(sys.stdin).get('settings',{}); print($1)"
}

banner "Wave-C activation (P37.2; window 2026-11-16→11-20; ING-GO-C)"  # future-ok: scheduled: the contract window

if [ "${SIG_GCP_MODE}" = "check" ]; then
  _log "PLAN ONLY — no ADC required, no network opened."
  uv run sig-ops wave-c-plan
  cat <<'EOF'

Gate inputs (recorded JSON — capture each field, never the wall clock):
  {
    "action": "admit",                     // or "close"
    "leg": "L1",
    "completed": [{"leg": "L1", "day": "2026-11-16"}],      // example — future-ok: illustrative: sample day
    "held_reports": {},                    // {leg: report-ref} for queued legs
    "now": "<date -u>",
    "go": {"verbatim": "Approve ING-GO-C (rec.)", "recorded_at": "2026-10-25T18:40:00Z"},
    "early_landings": {"P37.1": true, "PKG-07": true, "Q-23": true},  // earliest-window path only
    "q23": {"answered": true, "answer": "a"},
    "review_status": {"osm_overpass": "green"},
    "run_set": ["osm_overpass"],           // L3 only; empty on every other leg
    "materialize_active": false,
    "g2_slot_active": false,
    "release_cut_active": false,
    "active_manual_run": null,
    "wave_b_pauses": {"r11-layers-01": {"paused": true}, "r11-layers-02": {"paused": true},
                      "r11-ate-01": {"paused": true}, "r11-procurement-01": {"paused": true}},  // FEA-15
    "prestate": {"captured": true, "cadence_check_ok": true, "path": "<prestate dir>"},          // L1
    "backup": {"status": "SUCCESSFUL", "id": "<backup id>"},                                        // L1
    "disk": {"size_gb": 25, "autoresize_limit_gb": 40, "recorded": true},                           // L1 close
    "tier_go": {"verbatim": "<the operator's in-ticket go>", "recorded_at": "<date -u>"},          // L2
    "tier": {"tier": "db-custom-2-7680", "recorded": true},                                         // L2 close / L5 close = db-custom-1-3840
    "rebuild": {"image_digest": "sha256:<64 hex>", "jobs": ["sig-ingest-osm-overpass",
                "sig-ingest-camreg-batch-05"], "declared_published": true},                          // L3 close
    "retarget": {"cron": "12 8 24 * *", "recorded": true},                                           // L3 close
    "run": {"outcome": "ok", "claims_added": 1, "completed_at": "<date -u>"},                        // L3 close + L4 admit
    "tiles": {"within_tolerance": true},                                                             // L3 close
    "privacy": {"user_uid_captures": 0},                                                             // L3 close
    "plus0": {"claims_added": 0},                                                                    // L3 close
    "er": {"merge_pct": 95.0, "net_new": 0, "lineage_recorded": true},                               // L3 close
    "retire": {"targets_retired": ["osm_surveillance_deflock", "osm_surveillance_alpr_nationwide"],
               "still_scheduled": ["osm_surveillance_cctv_london", "osm_surveillance_thailand",
                                   "osm_surveillance_ucp_amini", "osm_surveillance_ucp_osm"],
               "derived_from_recorded": true, "next_fire": "2026-12-10T03:35:00Z"},                  // L3 close — future-ok: illustrative: sample stamp
    "soak": {"read": true, "instance_ok": true, "no_materialize_overlap": true,
             "record_ref": "<ref>"},                                                                  // L4 close
    "revert": {"post_state_recorded": true}                                                            // L5 close
  }

A missed leg is reported, never silently skipped. The re-run prompt:
  implement-spec spec=docs/tickets/345_P37.2__wave-c-osm-national-alpr-layer.md live_verification=true
EOF
  exit 0
fi

# --- apply ---------------------------------------------------------------------
require_project
require_adc
[ -n "${LEG}" ] || { _log "--apply needs --leg L1|…|L5" >&2; exit 64; }
[ -n "${INPUTS}" ] || { _log "--apply needs --inputs <recorded gate inputs JSON>" >&2; exit 64; }

_log "gate: sig-ops wave-c-gate --inputs ${INPUTS} (leg ${LEG})"
rc=0
_gate "${INPUTS}" || rc=$?
if [ "${rc}" -ne 0 ]; then
  _log "wave-c.sh: NO-GO (exit ${rc}) — the leg queues; a missed leg is reported, never silently skipped."
  exit "${rc}"
fi

ACTION="$(uv run python -c 'import json,sys; print(json.load(open(sys.argv[1])).get("action"))' "${INPUTS}")"
if [ "${ACTION}" = "close" ]; then
  _log "wave-c.sh: leg ${LEG} close gated green — record the leg report under docs/build/runs/P37.2.md"
  exit 0
fi

case "${LEG}" in
  L1)
    _log "-- L1.1 OM-14 pre-state: instance + job/trigger JSON, sources.toml sha, cadence --check"
    run gcloud sql instances describe "${SIG_SQL_INSTANCE}" \
      --project "${SIG_GCP_PROJECT}" --format=json
    for job in "${OSM_JOB}" "${BATCH_JOB}" sig-materialize; do
      run gcloud run jobs describe "${job}" \
        --region "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}" \
        --format=json || true   # record what exists — an absence is recorded, never assumed
    done
    run gcloud scheduler jobs list \
      --location "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}" --format=json
    run sha256sum connectors/src/connectors/data/sources.toml \
      connectors/src/connectors/data/camera_registry_targets.toml ops/cadence.toml
    run uv run sig-ops cadence --check
    _log "-- L1.2 AR-2 on-demand backup — poll to DONE, verify SUCCESSFUL before the first mutation"
    if [ "${SIG_GCP_MODE}" = "apply" ]; then
      op="$(gcloud sql backups create --instance "${SIG_SQL_INSTANCE}" \
            --project "${SIG_GCP_PROJECT}" --async --format=json)" || {
        _log "wave-c.sh: backup create call failed" >&2; exit 5; }
      opname="$(printf '%s' "$op" | python3 -c 'import json,sys; print(json.load(sys.stdin)["name"])')"
      _log "backup: issued op $opname"
      _wait_op "$opname" || { _log "wave-c.sh: AR-2 restore point failed — no instance patch may run (OM-20 void); stopped" >&2; exit 5; }
      gcloud sql backups list --instance "${SIG_SQL_INSTANCE}" \
        --project "${SIG_GCP_PROJECT}" --limit=1 --format=json
      _log "record the newest backup id + status=SUCCESSFUL into the close inputs"
    else
      _plan "gcloud sql backups create --instance ${SIG_SQL_INSTANCE} --async --project ${SIG_GCP_PROJECT}"
      _plan "  poll 'gcloud sql operations describe <op>' until DONE; read newest row → SUCCESSFUL"
    fi
    _log "-- L1.3 disk pre-grow to 25 GB — ONE-WAY: read the current size first,"
    _log "   record SKIP when already ≥25 (a resumed run never re-grows blindly)"
    if [ "${SIG_GCP_MODE}" = "apply" ]; then
      cur="$(_sql_field "s.get('dataDiskSizeGb')")"
      _log "current dataDiskSizeGb=$cur"
      case "${cur}" in
        ''|*[!0-9]*) _log "wave-c.sh: unreadable dataDiskSizeGb '${cur}' — the leg stops before any patch" >&2; exit 5 ;;
      esac
      if [ "${cur}" -lt 25 ]; then
        _apply_patch "disk-pre-grow-25" --storage-size=25 || {
          _log "wave-c.sh: the pre-grow patch failed — the leg stops; the state stays recorded" >&2; exit 5; }
      else
        _log "SKIP: dataDiskSizeGb already ${cur} ≥ 25 — recorded, never re-grown blindly"
      fi
    else
      _plan "read dataDiskSizeGb; patch --storage-size=25 --async only when <25 (else recorded SKIP); poll UPDATE"
    fi
    _log "-- L1.4 autoresize limit — Q-23's adopted posture caps at 40 GB"
    if [ "${SIG_GCP_MODE}" = "apply" ]; then
      lim="$(_sql_field "s.get('storageAutoResizeLimit')")"
      _log "current storageAutoResizeLimit=$lim"
      if [ "${lim:-0}" != "40" ]; then
        _apply_patch "autoresize-limit-40" --storage-auto-increase-limit=40 || {
          _log "wave-c.sh: the autoresize-limit patch failed — the leg stops" >&2; exit 5; }
      else
        _log "SKIP: storageAutoResizeLimit already 40 (B-11's posture) — recorded"
      fi
    else
      _plan "read storageAutoResizeLimit; patch --storage-auto-increase-limit=40 --async only when ≠40; poll UPDATE"
    fi
    _log "-- L1.5 read-back for the close gate: dataDiskSizeGb ≥25, limit ==40 —"
    _log "   collect the close evidence and re-gate with action=close"
    run gcloud sql instances describe "${SIG_SQL_INSTANCE}" \
      --project "${SIG_GCP_PROJECT}" \
      --format='value(settings.dataDiskSizeGb,settings.storageAutoResizeLimit,settings.tier)'
    ;;
  L2)
    _log "-- L2.1 the in-ticket tier go is a GATE INPUT (already judged — this"
    _log "   script never asks and never assumes; ING-GO-C is the wave's go,"
    _log "   never the tier's)"
    _log "-- L2.2 tier bump → db-custom-2-7680 (temporary; L5 reverts). The change"
    _log "   restarts the instance — one 503 class is the recorded risk (I8 §7.4)."
    _apply_patch "tier-bump-2-7680" --tier=db-custom-2-7680 || {
      _log "wave-c.sh: the tier patch failed — the leg stops; record the state" >&2; exit 5; }
    _log "-- L2.3 read-back + api /health"
    run gcloud sql instances describe "${SIG_SQL_INSTANCE}" \
      --project "${SIG_GCP_PROJECT}" --format='value(settings.tier)'
    if [ "${SIG_GCP_MODE}" = "apply" ]; then
      _api_health || { _log "wave-c.sh: api /health not 200 after the bump — investigate before closing" >&2; exit 5; }
    else
      _plan "curl -sS <api>/health -> 200"
    fi
    _log "-- collect the close evidence (tier read-back) and re-gate action=close"
    ;;
  L3)
    _log "-- L3.1 Wave-B pause posture (FEA-15): the four early-fire r11 batch"
    _log "   schedulers — absent under the consolidated dispatcher shape or held"
    _log "   PAUSED; the declared paused_until rows bind the due-set either way."
    for sched in ${EARLY_FIRE_SCHEDS}; do
      run gcloud scheduler jobs describe "${sched}" \
        --location "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}" \
        --format='value(name,schedule,state)' || true   # absent-consolidated is the declared shape — recorded
    done
    _log "-- L3.2 the fleet reconcile on one pinned digest (ADR-111): the osm job"
    _log "   carries P37.1's national-tile code; camreg-batch-05 carries the"
    _log "   committed mirror-retirement diff; the declaration bundle republish"
    _log "   binds the monthly retarget + the paused_until rows (SIG-OPS-005)."
    : "${SIG_JOB_IMAGE:?SIG_JOB_IMAGE must name the pinned image digest (sha256:… or a tag resolved by scheduled-ops.sh)}"
    run "${_here}/scheduled-ops.sh" --apply
    _log "-- L3.3 the first national run — MANUAL, one at a time (P36.12's rule);"
    _log "   US-first ordering, non-US objects kept (S5-4)."
    run gcloud run jobs execute "${OSM_JOB}" \
      --region "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}" \
      --args "scheduled-ingest,--source,osm_overpass,--sink,pg" --wait
    _log "-- L3.4 the §7.7 verify set (recorded reads — the close gate judges them):"
    run gcloud run jobs executions list --job "${OSM_JOB}" \
      --region "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}" \
      --limit=2 --format='yaml(name,status.completionTime,status.succeededCount,status.failedCount)'
    run gcloud storage ls --long --recursive \
      "gs://${SIG_BUCKET_RESTRICTED}/ops/runs/osm_overpass/"
    _log "   run row ok + captures landed bytes; tile totals within ±2% of"
    _log "   discovery and within taginfo's 154,814; zero captures containing"
    _log "   user/uid (SIG-INGEST-045e); claims > 0 — a red verify ABORTS here"
    _log "-- L3.5 the +0 re-run — asserts claims_added == 0 on unchanged input"
    run gcloud run jobs execute "${OSM_JOB}" \
      --region "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}" \
      --args "scheduled-ingest,--source,osm_overpass,--sink,pg" --wait
    run gcloud storage ls --long --recursive \
      "gs://${SIG_BUCKET_RESTRICTED}/ops/runs/osm_overpass/"
    _log "-- L3.6 the camera-site ER rematerialize — after the run verifies,"
    _log "   outside ingest runs; the counts read is the merge evidence"
    run gcloud run jobs execute sig-materialize \
      --region "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}" --wait
    _log "   read: ≥95% of the 132,689 republish rows merged (shared OSM id or"
    _log "   ≤1m); the measured net-new count reported as measured;"
    _log "   infer_lineages recorded republish↔origin one lineage (R5)"
    _log "-- L3.7 the mirror-retirement record — the batch job's deployed image IS"
    _log "   the retirement: verify the digest + the fetch set it carries."
    run gcloud run jobs describe "${BATCH_JOB}" \
      --region "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}" \
      --format='yaml(spec.template.spec.template.spec.containers[0].image)'
    _log "   record: exactly osm_surveillance_deflock + osm_surveillance_"
    _log "   alpr_nationwide out (the committed [[enumerated]] rows are the"
    _log "   restore point); the four CCTV republish targets still scheduled;"
    _log "   derived_from recorded under PKG-12 ED-49; next-fire 2026-12-10"  # future-ok: scheduled: dom cron
    _log "   03:35Z recorded after the retirement — §7.8: below the 95% bound the"
    _log "   republish targets stay scheduled (re-point ${BATCH_JOB} to the"
    _log "   previous digest before the fire) and the retirement does not close"
    _log "-- L3.8 record the leg: run rows, verify set, +0 diff, ER counts, the"
    _log "   retirement record → docs/build/runs/P37.2.md — then action=close"
    ;;
  L4)
    _log "-- L4.1 the 24 h soak read — READ-ONLY, ≥24 h after the recorded run end"
    run gcloud sql instances describe "${SIG_SQL_INSTANCE}" \
      --project "${SIG_GCP_PROJECT}" \
      --format='value(state,settings.tier,settings.dataDiskSizeGb,settings.storageAutoResizeLimit)'
    run gcloud run jobs executions list --job "${OSM_JOB}" \
      --region "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}" \
      --limit=3 --format='yaml(name,status.completionTime,status.succeededCount,status.failedCount)'
    run gcloud run jobs executions list --job sig-materialize \
      --region "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}" \
      --limit=3 --format='yaml(name,status.completionTime,status.succeededCount,status.failedCount)'
    run gcloud storage ls --long --recursive \
      "gs://${SIG_BUCKET_RESTRICTED}/ops/runs/osm_overpass/"
    _log "   record the soak read (instance_ok, no_materialize_overlap,"
    _log "   record_ref) — then action=close"
    ;;
  L5)
    _log "-- L5.1 the revert — the bump is temporary-only (Q-23): --tier=db-custom-1-3840"
    _apply_patch "tier-revert-1-3840" --tier=db-custom-1-3840 || {
      _log "wave-c.sh: the revert patch failed — the leg stops; the bumped tier stays recorded" >&2; exit 5; }
    run gcloud sql instances describe "${SIG_SQL_INSTANCE}" \
      --project "${SIG_GCP_PROJECT}" --format='value(settings.tier)'
    if [ "${SIG_GCP_MODE}" = "apply" ]; then
      _api_health || { _log "wave-c.sh: api /health not 200 after the revert — investigate before closing" >&2; exit 5; }
    else
      _plan "curl -sS <api>/health -> 200"
    fi
    _log "-- L5.2 post-state capture: scheduler posture + the closeout record —"
    _log "   every leg's command, start/end and outcome receipted"
    run gcloud scheduler jobs list \
      --location "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}" \
      --format='value(name,schedule,state)' || true
    _log "   collect the close evidence and re-gate action=close"
    ;;
  *) _log "unknown leg ${LEG} — the wave admits L1…L5 only" >&2; exit 64 ;;
esac

_log "wave-c.sh: leg ${LEG} admit-phase steps executed — collect the close evidence and re-gate with action=close"
