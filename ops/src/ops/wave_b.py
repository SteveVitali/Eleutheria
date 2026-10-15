# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P36.12 Wave-B activation — the leg plan and the ``sig.wave-b-gate/1`` go/no-go
checker (ticket 290, I8 §7.2–7.8, OM-19/OM-20).

Wave B is the Round-11 Tier-1 ingestion wave: **eleven legs in order**
inside the contract window 2026-10-26 → 2026-11-05 14:00–20:00Z
(future-ok: scheduled: contract window) under the recorded ING-GO-B
(GATE-G4 §3 — "Window + flips at open"; the verbatim go recorded
2026-10-15T15:26Z in GATE DECISIONS):

* **L0 — wave opening.** OM-14 pre-state capture (job/trigger JSON,
  ``sources.toml`` sha256, ``cadence --check`` green) → AR-2 on-demand
  backup verified ``SUCCESSFUL`` → ``sig-ops roll-jobs --record`` on one
  pinned digest (before/after recorded) → ``scheduled-ops.sh --apply
  --paused`` creates the seven new ``r11-*`` batch jobs paused → the
  hosted ``vocab_*`` registration of ``enforcement_count`` (P36.6's
  recorded wave prerequisite — before the first ATE-family live emit, or
  P35.14a's closed sink quarantines it; an operator-run INSERT-only
  migration step, never executed by the driver) → the complete
  operator-facing flip list handed to the operator for the OP-26
  execution (the row records the hand-off; the flips are never its act).
* **L1–L8 — family days** (ACQ-08…ACQ-15, one family per day — ACQ-11 +
  ACQ-15 may share a day): the day's flips recorded executed → manual
  first runs one source at a time (batch members on the family batch job,
  widen targets as single-source executions on their existing jobs, the
  six already-registered ``ccops_*`` rows on the documents-family job) →
  per-source I8 §7.7 verification → ``+0`` re-run proving zero new claims
  on unchanged input.
* **L9 — Flock transparency-portal probe** (P36.74, WV-10): the
  probe-only run over the committed 917-portal set — one polite request
  per portal under the project UA, stop-and-record on any challenge;
  every portal's outcome lands in the ``sig.probe-run/1`` record
  (served|refused + kind). Expected yield ≈ 0 is a recorded outcome.
* **L10 — closing.** ``sig-materialize`` manually after the last first
  run and outside ingest runs → the coverage-delta tool (P35.6, I8 §7.7)
  against the pre-wave snapshot → resume the seven paused schedules;
  each batch's next-fire is computed and recorded at resume against the
  FEA-15 note (the four crons firing 11-16…11-19 land inside Wave C's
  11-16→11-20 pause window and are surfaced, never silently accepted).

This module judges **recorded inputs** — it never reads live state
itself; the driver (``ops/gcp/wave-b.sh``) captures the inputs and this
module refuses (exit 42) unless every criterion holds. A refused leg
queues with its re-run prompt — a missed leg is reported, never
silently skipped (OM-19). The gate runs twice per leg: ``action=admit``
before the leg's first mutation and ``action=close`` before the leg is
recorded green — close re-judges admission and then the leg's recorded
evidence (run rows, ``+0`` re-runs, changed counts, the probe record,
materialize/next-fire records).

Criteria (each one refuse-on-fail; never a soft warn):

* ``go`` — the ING-GO-B verbatim recorded with a ``date -u`` timestamp,
  **byte-equal** to the verbatim in GATE DECISIONS (silence is never
  consent; ING-GO-B is a one-shot authorisation — a re-entry re-collects
  it verbatim).
* ``window`` — the supplied ``now`` inside 2026-10-26 → 2026-11-05
  14:00–20:00Z UTC (future-ok: scheduled: window) — evaluated on the
  *supplied* instant, never the wall clock. The Wave-B window carries no
  weekday restriction (unlike Wave A's Mon–Fri span).
* ``exclusions`` — no ``sig-materialize`` or G2 step 1–3 slot active, no
  release-cut day, and on 2026-10-29 the peel-on first fire
  (10-29T12:00Z; future-ok: scheduled: fire) recorded cleared before the
  leg.
* ``order`` — ``completed`` is a list of ``{leg, day}`` records: every
  earlier leg is green or held-reported (``held_reports``); completed
  days are window dates, non-decreasing in leg order; family legs hold
  one day each except the {L4,L8} pair may share (ACQ-11 + ACQ-15); the
  requested leg is not already green. A missed leg refuses, never skips.
* ``scope`` — ``run_set`` equals the leg's declared set exactly: batch
  members + widen executions + (L7) the six registered ``ccops_*`` rows;
  L0's run set is empty; L10's is the seven paused schedulers. The
  tribal-screened and deferred rows are never in scope
  (``doj_ctas_awards`` / ``D-R11-LATER-09``; the Wave-A S8 lane).
* ``flips`` — every gated source in the leg's run set is recorded in the
  operator's OP-26 flips for that family (``flips[leg].executed``) and
  the family's per-confirmation field is non-empty
  (``flips[leg].confirmed``); widen executions ride their existing flip
  and need no flag. A leg whose flips are absent stays queued.
* ``serialize`` — no ``sig-materialize`` active and no other manual run
  in flight (one manual run at a time, across waves).
* ``prestate`` / ``backup`` — L0 only: the OM-14 capture and the AR-2
  ``SUCCESSFUL`` read recorded.
* ``roll`` / ``jobs`` / ``vocab`` / ``handoff`` — L0 close only: the
  pinned-digest roll with before/after recorded; the seven batch jobs
  created paused; ``enforcement_count`` registered+verified in hosted
  ``vocab_*``; the complete flip list (all 96 flagged rows) handed off.
* ``vocab_gate`` — L3 admit: ``enforcement_count`` registered+verified
  before the first ATE-family live emit (re-checked here even though L0
  recorded it — a held L0 cannot wave the prerequisite past).
* ``runs`` / ``plus0`` / ``evidence`` — family-leg close: every run-set
  source has an ``ok`` run row with recorded claims/captures (a zero-claim
  first run carries a recorded reason in ``empty_run_notes``), every run
  source has a ``+0`` re-run showing ``claims_added == 0``, and the leg's
  ``changed_count`` is recorded.
* ``probe`` — L9 close: the ``sig.probe-run/1`` record covers all 917
  committed portals, served + refused reconcile, every refusal carries a
  kind; served = 0 is an honest recorded outcome, never a refusal reason.
* ``closing`` — L10 close: ``sig-materialize`` recorded run, the coverage
  delta recorded, all seven triggers resumed, the computed next-fires
  match the declared values, and every pre-11-20 fire carries a recorded
  FEA-15 disposition.

Exit codes from the CLI: ``0`` = go · ``42`` = no-go (queued — the leg
refuses, never proceeds on a missing or failed input) · ``2`` = usage.
"""

from __future__ import annotations

import datetime as _dt
import json
import re
import sys
from dataclasses import dataclass, field
from typing import Any

SCHEMA = "sig.wave-b-gate/1"
PLAN_SCHEMA = "sig.wave-b-plan/1"
WAVE = "B"

#: Contract: window 2026-10-26 → 2026-11-05 (future-ok: scheduled:
#: window), each day 14:00–20:00Z. No weekday restriction (the span is
#: eleven days; the one-family-per-day rule, not a weekday filter,
#: paces the wave).
WINDOW_START = "2026-10-26T14:00:00Z"  # future-ok: scheduled: the contract's window (OM-19)
WINDOW_END = "2026-11-05T20:00:00Z"  # future-ok: scheduled: exclusive end (OM-19)
WINDOW_START_HH = 14
WINDOW_END_HH = 20
WINDOW_FIRST_DATE = _dt.date(2026, 10, 26)  # future-ok: scheduled: window dates
WINDOW_LAST_DATE = _dt.date(2026, 11, 5)  # future-ok: scheduled: window dates

#: The eleven legs, in order. A leg admits only when every earlier leg
#: is recorded green or held-reported — a missed leg is reported, never
#: silently skipped (OM-19).
LEGS: tuple[str, ...] = (
    "L0",
    "L1",
    "L2",
    "L3",
    "L4",
    "L5",
    "L6",
    "L7",
    "L8",
    "L9",
    "L10",
)

#: The recorded ING-GO-B verbatim (GATE DECISIONS, 2026-10-15T15:26Z —
#: operator message; the gate requires byte-equality, never a paraphrase).
GO_VERBATIM = (
    "ING-GO-B: go — Wave B legs ACQ-08…ACQ-15 + the Flock probe may run "
    "inside the 2026-10-26→11-05 window; I execute the flips per OP-26"
)

#: The seven new paused batch jobs (ops/cadence.toml; created by
#: ``scheduled-ops.sh --apply --paused`` at L0, resumed at L10). Each
#: entry: batch id → (job, scheduler, cron, next fire after a resume
#: inside the window — computed at contract time, recorded at L10).
BATCHES: dict[str, dict[str, str]] = {
    "r11-layers-01": {
        "job": "sig-ingest-r11-layers-01",
        "scheduler": "sig-sched-r11-layers-01",
        "cron": "17 7 16 * *",
        "next_fire": "2026-11-16T07:17:00Z",  # future-ok: scheduled: dom cron
    },
    "r11-layers-02": {
        "job": "sig-ingest-r11-layers-02",
        "scheduler": "sig-sched-r11-layers-02",
        "cron": "17 7 17 * *",
        "next_fire": "2026-11-17T07:17:00Z",  # future-ok: scheduled: dom cron
    },
    "r11-ate-01": {
        "job": "sig-ingest-r11-ate-01",
        "scheduler": "sig-sched-r11-ate-01",
        "cron": "17 7 18 * *",
        "next_fire": "2026-11-18T07:17:00Z",  # future-ok: scheduled: dom cron
    },
    "r11-procurement-01": {
        "job": "sig-ingest-r11-procurement-01",
        "scheduler": "sig-sched-r11-procurement-01",
        "cron": "17 7 19 * *",
        "next_fire": "2026-11-19T07:17:00Z",  # future-ok: scheduled: dom cron
    },
    "r11-disclosures-01": {
        "job": "sig-ingest-r11-disclosures-01",
        "scheduler": "sig-sched-r11-disclosures-01",
        "cron": "27 7 21 * *",
        "next_fire": "2026-11-21T07:27:00Z",  # future-ok: scheduled: dom cron
    },
    "r11-disclosures-02": {
        "job": "sig-ingest-r11-disclosures-02",
        "scheduler": "sig-sched-r11-disclosures-02",
        "cron": "27 7 22 * *",
        "next_fire": "2026-11-22T07:27:00Z",  # future-ok: scheduled: dom cron
    },
    "r11-documents-01": {
        "job": "sig-ingest-r11-documents-01",
        "scheduler": "sig-sched-r11-documents-01",
        "cron": "27 7 23 * *",
        "next_fire": "2026-11-23T07:27:00Z",  # future-ok: scheduled: dom cron
    },
}

#: FEA-15 — the contract requires new monthly batch crons to fire after
#: 11-20. The four dom-16…19 crons land inside Wave C's 11-16→11-20
#: pause window; each early fire is surfaced in the run ledger (recorded
#: disposition), never silently accepted.
FEA15_CUTOVER = "2026-11-20T00:00:00Z"  # future-ok: scheduled: after 11-20
EARLY_FIRE_BATCHES: tuple[str, ...] = (
    "r11-layers-01",
    "r11-layers-02",
    "r11-ate-01",
    "r11-procurement-01",
)

#: The peel-on first fire (camreg_peel_on, ``sig-sched-camreg-peel-on``)
#: lands once in-window at 2026-10-29T12:00Z (future-ok: scheduled:
#: fire). A leg that day records the fire cleared before it runs — a
#: scheduled fire never overlaps a manual first run.
PEEL_DAY = _dt.date(2026, 10, 29)  # future-ok: scheduled: the peel-on fire day
PEEL_FIRE = "2026-10-29T12:00:00Z"  # future-ok: scheduled: the fire instant

#: Declared per-leg scope — the landed registry/cadence truth (P36.4–
#: P36.11 + P36.74): ``gated`` = rows on the operator's OP-26 flip list
#: (``ingestion_permitted=false`` until executed); ``hosted`` = the six
#: already-registered ccops_* rows — also gated, also on the flip list,
#: but carrying no batch seat (they execute single-source on the
#: documents-family job); ``widen`` = already-permitted sources whose new
#: Wave-B targets run as single-source manual executions on their
#: existing jobs (no flag — their next scheduled fire is then a ``+0``).
LEG_SCOPE: dict[str, dict[str, tuple[str, ...]]] = {
    "L1": {  # ACQ-08 (P36.4) — r11-layers-01
        "gated": (
            "dot_511_de",
            "dot_511_vt",
            "dot_511_wv",
            "dot_511_mi",
            "camreg_ne_lincoln_traffic_cameras",
            "camreg_omaha_ne_parks_cameras",
            "camreg_hyattsville_md_cctv_camera_2024",
            "dot_511_nc",
        ),
        "hosted": (),
        # widen hosts — already permitted (P26.16, GL-GATE-07): Denver's
        # HALO layer + Seattle's CCTV pilot areas ride their existing
        # camreg-batch seats; dot_511_de's deldot_red_light target (P36.6
        # consolidation) rides the dot_511_de run in the same leg.
        "widen": ("camreg_denver_co", "camreg_seattle_wa"),
    },
    "L2": {  # ACQ-09 (P36.5) — r11-layers-02
        "gated": (
            "camreg_fdot_flock",
            "camreg_pueblo_co_flock",
            "camreg_rocky_mount_nc_lpr_cameras",
            "camreg_shelbyville_tn_flock_cameras",
            "camreg_temecula_ca_flock_wfl1",
            "camreg_marble_falls_tx_flock_locations",
            "camreg_va_prince_william_county",
            "camreg_milford_ct_flocklprcam",
            "camreg_elgin_il_lpr_cameras",
            "camreg_south_fulton_ga_lpr_cameras",
            "camreg_va_pittsylvania_county_stationary",
            "camreg_alabaster_al_lpr_cameras",
            "camreg_thomasville_ga_flock_location",
            "camreg_leon_county_fl_overwatch_viewer",
            "camreg_ga_peachtree_corners_flock_camera",
        ),
        "hosted": (),
        "widen": (),
    },
    "L3": {  # ACQ-10 (P36.6) — r11-ate-01
        "gated": (
            "camreg_dc_ddot_ate",
            "camreg_montgomery_md_ate",
            "camreg_nyc_mta_bus_lane_ate",
            "camreg_tacoma_wa_ate",
            "camreg_howard_md_school_zone_ate",
            "camreg_lakeland_fl_red_light",
            "camreg_suffolk_ny_red_light",
            "camreg_medford_or_ate",
            "camreg_ctdot_speed_safety",
        ),
        "hosted": (),
        # The two Chicago socrata_aggregate targets ride the
        # already-flipped camreg_chicago_il on camreg-batch-02. The plan's
        # dot_511_dc widen FAILED the licence match (CC-BY-4.0 items vs a
        # CC0-1.0 row) — the DC ASC pair landed on the gated
        # camreg_dc_ddot_ate fallback instead, so sig-ingest-dot-511-dc
        # carries no Wave-B execution.
        "widen": ("camreg_chicago_il",),
    },
    "L4": {  # ACQ-11 (P36.7) — r11-procurement-01
        "gated": (
            "procportal_cook_il_awards",
            "procportal_wa_des_contract_sales",
            "camreg_dc_ovsjg_camera_rebate",
        ),
        "hosted": (),
        "widen": (),
    },
    "L5": {  # ACQ-12 (P36.8) — r11-disclosures-01
        "gated": (
            "statrep_mn_bca",
            "statrep_va_rga",
            "statrep_wa_ago_alpr_registry",
            "statrep_va_vsp_alpr",
            "statrep_va_vscc_alpr",
            "statrep_ne_crime_commission_alpr",
            "statrep_vt_dps_alpr",
            "statrep_md_dls_mandated_reports",
            "statrep_il_isp_alpr",
            "statrep_austin_tx_auditor",
        ),
        "hosted": (),
        "widen": (),
    },
    "L6": {  # ACQ-13a+13b (P36.9a+P36.9b) — r11-disclosures-02
        "gated": (
            "statrep_me_dps_uav",
            "statrep_hi_judiciary_interception",
            "statrep_wa_watech_frt",
            "statrep_co_frt_accountability",
            "statrep_de_diac",
            "statrep_wa_wtsc_ate",
            "statrep_detroit_mi_frt_weekly",
            "statrep_us_dhs_privacy_compliance",
            "statrep_fl_flhsmv_red_light",
            "statrep_pa_wzssc",
            "statrep_md_msp_css",
            "statrep_mn_court_interception",
            "legis_us_dhs_sorn_plate_data",
            "statrep_seattle_wa_sdot_ate",
            "statrep_il_icjia_drone",
            "statrep_seattle_wa_oig",
        ),
        "hosted": (),
        "widen": (),
    },
    "L7": {  # ACQ-14 (P36.10) — r11-documents-01 subset + six registered rows
        "gated": (
            "ccops_columbia_mo",
            "ccops_st_louis_mo",
            "ccops_dayton_oh",
            "ccops_anchorage_ak",
            "ccops_austin_tx",
            "policy_orange_county_ca_sheriff",
            "policy_pasadena_ca_pd",
            "policy_st_cloud_mn_isd742",
            "policy_onslow_nc_schools",
            "policy_pflugerville_tx_isd",
            "policy_whitesboro_ny_csd",
            "policy_bangor_me_pd",
            "policy_houston_tx_hpd",
            "policy_albuquerque_nm_apd",
            "policy_little_rock_ar_pd",
            "legis_ca_gov_code_53166",
        ),
        "hosted": (
            "ccops_berkeley",
            "ccops_davis",
            "ccops_boston",
            "ccops_baltimore",
            "ccops_nashville",
            "ccops_grand_rapids",
        ),
        "widen": (),
    },
    "L8": {  # ACQ-15 (P36.11) — r11-documents-01 subset
        "gated": (
            "agenda_haskell_ar_council",
            "agenda_des_moines_ia_council",
            "agenda_jasper_sc_council",
            "grant_al_adeca_psn",
            "grant_ca_bscc_ort",
            "grant_fl_senate_lfir",
            "grant_nj_oag_bwc",
            "grant_ok_dac_jag_lle",
            "grant_tx_txdmv_mvcpa",
            "legis_gu_governor",
            "procportal_davie_fl_purchasing",
            "procportal_forsyth_nc_purchasing",
        ),
        "hosted": (),
        # The two pinned bill queries (az_hb2574_2024, ny_s7037_2025_2026)
        # ride the already-flipped openstates row on sig-ingest-openstates.
        "widen": ("openstates",),
    },
    "L9": {  # P36.74 — the Flock transparency-portal probe (WV-10)
        "gated": ("flock_transparency_portals",),
        "hosted": (),
        "widen": (),
    },
}

#: Legs that run ingestion families (one-family-per-day applies; L0
#: opens and L10 closes — they may share a calendar day with a family).
FAMILY_LEGS: tuple[str, ...] = ("L1", "L2", "L3", "L4", "L5", "L6", "L7", "L8", "L9")

#: The contract's one exception to one-family-per-day: ACQ-11 (L4) and
#: ACQ-15 (L8) may share a day.
SHARED_DAY_PAIR: frozenset[str] = frozenset({"L4", "L8"})

#: The single-source host job for each widen execution + the hosted
#: ccops rows (the documents-family job hosts the seatless six).
EXECUTION_JOB: dict[str, str] = {
    "camreg_denver_co": "sig-ingest-camreg-batch-02",
    "camreg_seattle_wa": "sig-ingest-camreg-batch-06",
    "camreg_chicago_il": "sig-ingest-camreg-batch-02",
    "openstates": "sig-ingest-openstates",
    "ccops_berkeley": "sig-ingest-r11-documents-01",
    "ccops_davis": "sig-ingest-r11-documents-01",
    "ccops_boston": "sig-ingest-r11-documents-01",
    "ccops_baltimore": "sig-ingest-r11-documents-01",
    "ccops_nashville": "sig-ingest-r11-documents-01",
    "ccops_grand_rapids": "sig-ingest-r11-documents-01",
    "flock_transparency_portals": "sig-ingest-r11-documents-01",
}

#: The batch each gated member runs on (source → batch id → job).
SOURCE_BATCH: dict[str, str] = {
    sid: batch
    for batch, legs in {
        "r11-layers-01": ("L1",),
        "r11-layers-02": ("L2",),
        "r11-ate-01": ("L3",),
        "r11-procurement-01": ("L4",),
        "r11-disclosures-01": ("L5",),
        "r11-disclosures-02": ("L6",),
        "r11-documents-01": ("L7", "L8"),
    }.items()
    for leg in legs
    for sid in LEG_SCOPE[leg]["gated"]
}

#: Never in this wave: AP-T2-093 (doj_ctas_awards — not tribal, deferred
#: under D-R11-LATER-09) and the ADR-185 tribal S8 screened lane, which
#: landed at P35.11/Wave A and is re-run by no Wave-B leg.
NEVER_SOURCES: frozenset[str] = frozenset(
    {
        "doj_ctas_awards",
        "camreg_tribal_all_leaders_directory",
        "legis_tribal_tohono_oodham_notice",
    }
)

#: The complete operator flip list = every gated + hosted source across
#: the family legs (the 96 flagged rows the OP-26 execution names;
#: widen targets ride existing flips and appear on the list as recorded
#: context, never as flag rows).
FLIP_SOURCES: tuple[str, ...] = tuple(
    sid for leg in FAMILY_LEGS for sid in LEG_SCOPE[leg]["gated"] + LEG_SCOPE[leg]["hosted"]
)

#: The committed probe inventory (P36.74): 917 known portals, Eyes on
#: Flock snapshot 2026-09-23T10:15:16.751Z — no new discovery.
PROBE_SOURCE = "flock_transparency_portals"
PROBE_INVENTORY = 917

#: The hosted vocabulary prerequisite (P36.6): ``enforcement_count``
#: must exist in ``vocab_predicate`` before the first ATE-family live
#: emit (L3), or P35.14a's closed sink quarantines it. Registration is
#: the L0 operator-run migration step — INSERT-only, Sqitch change
#: ``vocab_enforcement_count``.
VOCAB_PREDICATE = "enforcement_count"
VOCAB_CHANGE = "vocab_enforcement_count"

#: Re-run prompt recorded on every refusal (the leg is never abandoned —
#: it queues with its verbatim line). ING-GO-B is a one-shot
#: authorisation: a re-entry re-collects the operator go verbatim.
RERUN = (
    "implement-spec "
    "spec=docs/tickets/290_P36.12__wave-b-activation.md "
    "live_verification=true (scope: the queued Wave-B legs only — each leg "
    "needs the recorded ING-GO-B, the window, its own gate inputs and its "
    "family's executed OP-26 flips; the flip list is the operator's, "
    "never this row's)"
)


class WaveGateError(ValueError):
    """A malformed wave-gate input (usage failure, exit 2)."""


@dataclass
class Criterion:
    id: str
    ok: bool
    detail: str
    value: Any = None


@dataclass
class Verdict:
    decision: str  # "go" | "no-go"
    leg: str
    action: str
    criteria: list[Criterion] = field(default_factory=list)

    @property
    def refusals(self) -> list[str]:
        return [f"{c.id}: {c.detail}" for c in self.criteria if not c.ok]

    def to_record(self) -> dict:
        return {
            "kind": SCHEMA,
            "wave": WAVE,
            "decision": self.decision,
            "leg": self.leg,
            "action": self.action,
            "criteria": [
                {"id": c.id, "ok": c.ok, "detail": c.detail, "value": c.value}
                for c in self.criteria
            ],
            "refusals": self.refusals,
            "rerun_prompt": None if self.decision == "go" else RERUN,
            "thresholds": {
                "window_start": WINDOW_START,
                "window_end": WINDOW_END,
                "window_band_hh": [WINDOW_START_HH, WINDOW_END_HH],
                "legs": list(LEGS),
                "family_legs": list(FAMILY_LEGS),
                "shared_day_pair": sorted(SHARED_DAY_PAIR),
                "batches": {k: dict(v) for k, v in BATCHES.items()},
                "fea15_cutover": FEA15_CUTOVER,
                "early_fire_batches": list(EARLY_FIRE_BATCHES),
                "peel_fire": PEEL_FIRE,
                "peel_day": PEEL_DAY.isoformat(),
                "flip_source_count": len(FLIP_SOURCES),
                "never_sources": sorted(NEVER_SOURCES),
                "probe_source": PROBE_SOURCE,
                "probe_inventory": PROBE_INVENTORY,
                "vocab_predicate": VOCAB_PREDICATE,
                "vocab_change": VOCAB_CHANGE,
            },
        }


def _iso(text: Any) -> _dt.datetime:
    """Parse an ISO-8601 instant (Z or +offset) — raises WaveGateError."""
    if not isinstance(text, str) or not text.strip():
        raise WaveGateError(f"expected an ISO-8601 instant, got {text!r}")
    t = text.strip()
    try:
        if t.endswith("Z"):
            dt = _dt.datetime.fromisoformat(t[:-1] + "+00:00")
        else:
            dt = _dt.datetime.fromisoformat(t)
    except ValueError as exc:
        raise WaveGateError(f"bad ISO-8601 instant {text!r}: {exc}") from exc
    if dt.tzinfo is None:
        raise WaveGateError(f"instant {text!r} carries no timezone (UTC required)")
    return dt.astimezone(_dt.UTC)


def _day(text: Any, where: str) -> _dt.date:
    """Parse an ISO-8601 *date* (YYYY-MM-DD) — raises WaveGateError."""
    if not isinstance(text, str) or not text.strip():
        raise WaveGateError(f"{where}: expected an ISO-8601 date, got {text!r}")
    try:
        return _dt.date.fromisoformat(text.strip()[:10])
    except ValueError as exc:
        raise WaveGateError(f"{where}: bad ISO-8601 date {text!r}") from exc


def _source_ids(value: Any, name: str) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(v, str) and v.strip() for v in value):
        raise WaveGateError(f"{name}: expected a list of source/trigger ids, got {value!r}")
    return [v.strip() for v in value]


def _declared(leg: str) -> set[str]:
    scope = LEG_SCOPE.get(leg) or {}
    return set(scope.get("gated", ())) | set(scope.get("hosted", ())) | set(scope.get("widen", ()))


def _gated(leg: str) -> set[str]:
    scope = LEG_SCOPE.get(leg) or {}
    return set(scope.get("gated", ())) | set(scope.get("hosted", ()))


def _completed_entries(inputs: dict) -> tuple[list[tuple[str, _dt.date]], list[str]]:
    """Validate the ``completed`` record list — returns (entries, errors).

    Each entry is ``{"leg": "L1", "day": "2026-10-27"}`` — the recorded
    green legs in run order. Malformed entries are usage-shape errors the
    gate reports as refusals (recorded inputs are judged, never trusted).
    """
    entries: list[tuple[str, _dt.date]] = []
    errors: list[str] = []
    raw = inputs.get("completed", [])
    if not isinstance(raw, list):
        return [], [f"completed: expected a list of {{leg, day}} records, got {raw!r}"]
    seen: set[str] = set()
    for i, item in enumerate(raw):
        where = f"completed[{i}]"
        if not isinstance(item, dict):
            errors.append(f"{where}: expected {{leg, day}}, got {item!r}")
            continue
        leg, day = item.get("leg"), item.get("day")
        if leg not in LEGS:
            errors.append(f"{where}: leg {leg!r} is not one of {LEGS}")
            continue
        if leg in seen:
            errors.append(f"{where}: leg {leg!r} recorded green twice")
            continue
        try:
            d = _day(day, where)
        except WaveGateError as exc:
            errors.append(str(exc))
            continue
        if not (WINDOW_FIRST_DATE <= d <= WINDOW_LAST_DATE):
            errors.append(
                f"{where}: day {d.isoformat()} outside the window dates "
                f"{WINDOW_FIRST_DATE.isoformat()}→{WINDOW_LAST_DATE.isoformat()}"
            )
            continue
        seen.add(leg)
        entries.append((leg, d))
    return entries, errors


def _held(inputs: dict) -> tuple[set[str], list[str]]:
    """Validate ``held_reports`` — {leg: report-ref}; returns (legs, errors)."""
    raw = inputs.get("held_reports", {})
    if not isinstance(raw, dict):
        return set(), [f"held_reports: expected a {{leg: report-ref}} object, got {raw!r}"]
    legs: set[str] = set()
    errors: list[str] = []
    for leg, ref in raw.items():
        if leg not in LEGS:
            errors.append(f"held_reports: leg {leg!r} is not one of {LEGS}")
            continue
        if not isinstance(ref, str) or not ref.strip():
            errors.append(
                f"held_reports[{leg!r}]: a held leg needs a non-empty report ref "
                "(held = queued AND reported, never silently skipped)"
            )
            continue
        legs.add(leg)
    return legs, errors


def evaluate(inputs: dict) -> Verdict:
    """Judge the recorded inputs — every criterion must hold for a ``go``."""
    if not isinstance(inputs, dict):
        raise WaveGateError("the wave-gate input must be a JSON object")
    action = inputs.get("action")
    if action not in ("admit", "close"):
        raise WaveGateError(
            f"action {action!r} — expected 'admit' (before the leg's first "
            "mutation) or 'close' (before the leg is recorded green)"
        )
    criteria: list[Criterion] = []

    # -- leg + order --------------------------------------------------------------
    leg = inputs.get("leg")
    entries, order_errors = _completed_entries(inputs)
    held, held_errors = _held(inputs)
    done = {lid for lid, _ in entries} | held
    both = {lid for lid, _ in entries} & held
    if both:
        order_errors.append(
            f"{sorted(both)} recorded both green and held — a leg is one or the other"
        )
    if not isinstance(leg, str) or leg not in LEGS:
        criteria.append(
            Criterion(
                "order",
                False,
                f"leg {leg!r} is not one of {LEGS} — the wave admits L0…L10 only",
            )
        )
        leg = leg if isinstance(leg, str) else "?"
    else:
        missing = [lid for lid in LEGS[: LEGS.index(leg)] if lid not in done]
        already = leg in {lid for lid, _ in entries}
        if already:
            criteria.append(
                Criterion(
                    "order",
                    False,
                    f"{leg} is already recorded green — a leg runs once; a "
                    "re-entry re-collects the operator go verbatim",
                )
            )
        elif missing:
            criteria.append(
                Criterion(
                    "order",
                    False,
                    f"{missing} neither green nor held-reported — {leg} admits "
                    "only after every earlier leg is green or held (a missed "
                    "leg is reported, never silently skipped)",
                    missing,
                )
            )
        elif order_errors or held_errors:
            criteria.append(Criterion("order", False, "; ".join(order_errors + held_errors)))
        else:
            criteria.append(
                Criterion(
                    "order",
                    True,
                    f"{leg} is next in order (green={sorted(lid for lid, _ in entries)}, "
                    f"held={sorted(held)})",
                )
            )

    # -- family-day pacing ----------------------------------------------------------
    # Days of completed entries non-decreasing in leg order; family legs
    # hold one day each except {L4, L8} may share; the requested family
    # leg's day counts too.
    now: _dt.datetime | None = None
    if inputs.get("now") is None:
        criteria.append(
            Criterion(
                "window",
                False,
                "no 'now' instant supplied — the gate evaluates a recorded "
                "instant, never the wall clock",
            )
        )
    else:
        now = _iso(inputs.get("now"))
        start, end = _iso(WINDOW_START), _iso(WINDOW_END)
        band = WINDOW_START_HH <= now.hour < WINDOW_END_HH
        inside = start <= now < end
        criteria.append(
            Criterion(
                "window",
                band and inside,
                f"now {now.isoformat()} — 14:00-20:00Z band={band} "
                f"in-window={inside} (the Wave-B window carries no weekday "
                "restriction — one family per day paces it)",
                now.isoformat(),
            )
        )

    day_errors: list[str] = list(order_errors)  # entry validation already ran
    ordered = sorted(entries, key=lambda e: LEGS.index(e[0]))
    for prev, nxt in zip(ordered, ordered[1:], strict=False):
        if nxt[1] < prev[1]:
            day_errors.append(
                f"{nxt[0]} day {nxt[1].isoformat()} precedes {prev[0]} day "
                f"{prev[1].isoformat()} — leg days never run backwards"
            )
    day_map: dict[str, list[str]] = {}
    for lid, d in ordered:
        if lid in FAMILY_LEGS:
            day_map.setdefault(d.isoformat(), []).append(lid)
    if now is not None and leg in FAMILY_LEGS:
        day_map.setdefault(now.date().isoformat(), []).append(leg)
    for day_iso, ls in sorted(day_map.items()):
        if len(ls) > 1 and set(ls) != SHARED_DAY_PAIR:
            day_errors.append(
                f"{day_iso} hosts family legs {sorted(ls)} — one family per day "
                "(only ACQ-11 + ACQ-15 may share: L4 + L8)"
            )
    if leg in FAMILY_LEGS and now is not None:
        earlier_days = [d for lid, d in ordered if LEGS.index(lid) < LEGS.index(leg)]
        if earlier_days and now.date() < max(earlier_days):
            day_errors.append(
                f"{leg} day {now.date().isoformat()} precedes an earlier leg's "
                f"day {max(earlier_days).isoformat()} — leg days never run backwards"
            )
    if day_errors:
        criteria.append(Criterion("pacing", False, "; ".join(day_errors)))
    else:
        criteria.append(
            Criterion(
                "pacing",
                True,
                "leg days in order; family legs one-per-day "
                "(L4+L8 share permitted) — one-family-per-day holds",
            )
        )

    # -- go (ING-GO-B — the only authority, byte-exact) --------------------------------
    go = inputs.get("go")
    if not isinstance(go, dict) or not str(go.get("verbatim") or "").strip():
        criteria.append(
            Criterion(
                "go",
                False,
                "no recorded ING-GO-B verbatim — the wave is an in-ticket "
                "pause without it (silence is never consent; a re-entry "
                "re-collects the go verbatim)",
            )
        )
    elif go.get("verbatim") != GO_VERBATIM:
        criteria.append(
            Criterion(
                "go",
                False,
                "the recorded go is not the verbatim ING-GO-B — GATE DECISIONS "
                "carries it byte-exact; a paraphrase is a refusal (silence is "
                "never consent)",
            )
        )
    else:
        try:
            recorded = _iso(go.get("recorded_at"))
        except WaveGateError as exc:
            criteria.append(Criterion("go", False, f"go recorded_at: {exc}"))
        else:
            criteria.append(
                Criterion(
                    "go",
                    True,
                    f"ING-GO-B verbatim recorded {recorded.isoformat()} "
                    "(GATE DECISIONS; OM-18; byte-exact)",
                    recorded.isoformat(),
                )
            )

    # -- exclusions (peel-on fire, G2 slot, cut day, materialize) -----------------------
    materialize = bool(inputs.get("materialize_active"))
    g2 = bool(inputs.get("g2_slot_active"))
    cut = bool(inputs.get("release_cut_active"))
    peel_needed = now is not None and now.date() == PEEL_DAY
    peel_ok = bool(inputs.get("peel_fire_cleared")) if peel_needed else True
    ex_bad = []
    if materialize:
        ex_bad.append("sig-materialize active")
    if g2:
        ex_bad.append("a G2 step 1–3 slot is active")
    if cut:
        ex_bad.append("a release-cut day is recorded")
    if peel_needed and not peel_ok:
        ex_bad.append(
            f"the peel-on first fire {PEEL_FIRE} is not recorded cleared "
            "(future-ok: scheduled: fire — a scheduled fire never overlaps "
            "a manual first run)"
        )
    criteria.append(
        Criterion(
            "exclusions",
            not ex_bad,
            (
                f"materialize_active={materialize} g2_slot_active={g2} "
                f"release_cut_active={cut} peel_cleared(needed={peel_needed})={peel_ok}"
                if not ex_bad
                else "; ".join(ex_bad)
            ),
        )
    )

    # -- scope (run_set == the leg's declared set, exactly) ----------------------------
    run_set = _source_ids(inputs.get("run_set", []), "run_set")
    never = [s for s in run_set if s in NEVER_SOURCES]
    if leg == "L0":
        expected: set[str] = set()
    elif leg == "L10":
        expected = {b["scheduler"] for b in BATCHES.values()}
    elif leg in LEG_SCOPE:
        expected = _declared(leg)
    else:
        expected = set()
        for s in run_set:
            if s not in NEVER_SOURCES:
                never.append(s)  # unknown leg scope — nothing is admitted
    dup = [s for s in run_set if run_set.count(s) > 1]
    missing_s = sorted(expected - set(run_set))
    extra_s = sorted(set(run_set) - expected)
    if never:
        criteria.append(
            Criterion(
                "scope",
                False,
                f"{sorted(set(never))} in run_set — never in Wave B: "
                "doj_ctas_awards stays deferred under D-R11-LATER-09 and the "
                "tribal S8 lane landed at P35.11 (Wave A)",
                never,
            )
        )
    elif dup or missing_s or extra_s:
        criteria.append(
            Criterion(
                "scope",
                False,
                f"run_set ≠ the declared {leg} set — missing={missing_s} "
                f"extra={extra_s} duplicates={sorted(set(dup))} (a leg runs its "
                "whole family or queues; nothing undeclared runs)",
                {"missing": missing_s, "extra": extra_s, "duplicates": sorted(set(dup))},
            )
        )
    else:
        criteria.append(
            Criterion(
                "scope",
                True,
                f"run_set == the declared {leg} set ({len(run_set)} entries)",
                run_set,
            )
        )

    # -- flips (the operator's OP-26 execution, per family) ---------------------------
    if leg in FAMILY_LEGS:
        flips = (inputs.get("flips") or {}).get(leg)
        gated = _gated(leg)
        if not isinstance(flips, dict):
            criteria.append(
                Criterion(
                    "flips",
                    False,
                    f"no flips record for {leg} — the family's OP-26 flip "
                    "execution is a prerequisite; a leg whose flip is absent "
                    "stays queued and is reported, never silently skipped",
                )
            )
        else:
            executed = set(_source_ids(flips.get("executed", []), f"flips[{leg}].executed"))
            unflipped = sorted(gated - executed)
            confirmed = bool(str(flips.get("confirmed") or "").strip())
            if unflipped:
                criteria.append(
                    Criterion(
                        "flips",
                        False,
                        f"{unflipped} not in the recorded OP-26 flips for {leg} — "
                        "a gated source never runs unflipped (HG-03); the leg "
                        "stays queued, reported",
                        unflipped,
                    )
                )
            elif not confirmed:
                criteria.append(
                    Criterion(
                        "flips",
                        False,
                        f"the {leg} flips are recorded executed but the family's "
                        "per-confirmation field is empty — the operator's "
                        "confirmation is recorded, never assumed",
                    )
                )
            else:
                widen_note = (
                    f"; widen hosts {sorted(set(LEG_SCOPE[leg]['widen']))} ride "
                    "existing flips (no flag)"
                    if LEG_SCOPE[leg]["widen"]
                    else ""
                )
                criteria.append(
                    Criterion(
                        "flips",
                        True,
                        f"{len(gated)} gated sources recorded flipped + the "
                        f"family confirmation present{widen_note}",
                        sorted(executed),
                    )
                )

    # -- serialize (one manual run at a time) -------------------------------------------
    active = inputs.get("active_manual_run") or None
    ok = active is None
    criteria.append(
        Criterion(
            "serialize",
            ok,
            f"active_manual_run={active!r} — one manual run at a time, "
            "across waves (the P35.11 edge is SEQUENCE-only)",
            active,
        )
    )

    # -- L0 prerequisites: OM-14 pre-state + AR-2 backup ---------------------------------
    if leg == "L0":
        prestate = inputs.get("prestate")
        if not isinstance(prestate, dict):
            criteria.append(Criterion("prestate", False, "no pre-state capture supplied"))
        else:
            captured = prestate.get("captured") is True and prestate.get("cadence_check_ok") is True
            criteria.append(
                Criterion(
                    "prestate",
                    captured,
                    (
                        "pre-state capture recorded (job/trigger JSON, "
                        "sources.toml sha, cadence --check green)"
                        if captured
                        else "the OM-14 pre-state capture (job/trigger JSON, "
                        "sources.toml sha, green cadence --check) is not "
                        "recorded — capture before the first mutation"
                    ),
                    prestate.get("path"),
                )
            )
        backup = inputs.get("backup")
        if not isinstance(backup, dict):
            criteria.append(Criterion("backup", False, "no AR-2 backup read supplied"))
        else:
            status = backup.get("status")
            criteria.append(
                Criterion(
                    "backup",
                    status == "SUCCESSFUL",
                    (
                        f"AR-2 on-demand backup {backup.get('id')!r} SUCCESSFUL"
                        if status == "SUCCESSFUL"
                        else f"newest sig-pg backup {status!r} — a failed "
                        "restore point stops the leg before the first mutation"
                    ),
                    status,
                )
            )

    # -- L3 admission: the hosted vocab_* prerequisite ------------------------------------
    if leg == "L3":
        vocab = (inputs.get("vocab") or {}).get(VOCAB_PREDICATE) or {}
        reg = vocab.get("registered") is True
        ver = vocab.get("verified") is True
        criteria.append(
            Criterion(
                "vocab_gate",
                reg and ver,
                (
                    f"{VOCAB_PREDICATE} registered+verified in hosted vocab_* "
                    "— the ATE family may emit"
                    if reg and ver
                    else f"{VOCAB_PREDICATE} not registered+verified in hosted "
                    "vocab_* (registered={reg} verified={ver}) — P35.14a's "
                    "closed sink would quarantine the first ATE emit; the L0 "
                    "registration step lands first"
                ),
                {"registered": reg, "verified": ver},
            )
        )

    if action == "close":
        _close_criteria(leg, inputs, criteria)

    decision = "go" if all(c.ok for c in criteria) else "no-go"
    return Verdict(decision=decision, leg=leg, action=action, criteria=criteria)


def _close_criteria(leg: str, inputs: dict, criteria: list[Criterion]) -> None:
    """The leg-close evidence checks — re-judged on top of admission."""

    # -- L0 closing records ----------------------------------------------------------
    if leg == "L0":
        roll = inputs.get("roll") or {}
        digest = str(roll.get("image_digest") or "")
        pinned = bool(re.fullmatch(r"sha256:[0-9a-f]{64}", digest))
        before_after = roll.get("before_after_recorded") is True
        criteria.append(
            Criterion(
                "roll",
                pinned and before_after,
                (
                    f"roll-jobs --record on {digest[:19]}… with before/after recorded"
                    if pinned and before_after
                    else f"the image roll is not recorded on one pinned digest "
                    f"(pinned={pinned} before_after={before_after}) — one "
                    "digest, every job (ADR-111)"
                ),
                {"image_digest": digest, "before_after": before_after},
            )
        )
        jobs = inputs.get("jobs_created") or {}
        bad = [
            b
            for b in BATCHES
            if not (
                isinstance(jobs.get(b), dict)
                and jobs[b].get("created") is True
                and jobs[b].get("paused") is True
            )
        ]
        criteria.append(
            Criterion(
                "jobs",
                not bad,
                (
                    "the seven r11-* batch jobs recorded created --paused"
                    if not bad
                    else f"{bad} not recorded created-paused — "
                    "scheduled-ops.sh --apply --paused creates all seven "
                    "before any resume (R6)"
                ),
                bad,
            )
        )
        vocab = (inputs.get("vocab") or {}).get(VOCAB_PREDICATE) or {}
        reg = vocab.get("registered") is True
        ver = vocab.get("verified") is True
        criteria.append(
            Criterion(
                "vocab",
                reg and ver,
                (
                    f"{VOCAB_PREDICATE} registered+verified in hosted vocab_* "
                    f"({VOCAB_CHANGE}; the operator-run INSERT-only step)"
                    if reg and ver
                    else f"{VOCAB_PREDICATE} registration not recorded "
                    f"(registered={reg} verified={ver}) — the operator-run "
                    f"{VOCAB_CHANGE} migration lands before L0 closes"
                ),
                {"registered": reg, "verified": ver},
            )
        )
        handoff = inputs.get("flip_handoff") or {}
        flip_list = set(_source_ids(inputs.get("flip_list", []), "flip_list"))
        ref = str(handoff.get("list_ref") or "")
        complete = flip_list == set(FLIP_SOURCES)
        missing = sorted(set(FLIP_SOURCES) - flip_list)
        extra = sorted(flip_list - set(FLIP_SOURCES))
        criteria.append(
            Criterion(
                "handoff",
                bool(ref) and complete,
                (
                    f"the complete flip list ({len(FLIP_SOURCES)} flag rows + "
                    "widen-target context) handed to the operator "
                    f"({ref}) — OP-26 owns the execution"
                    if bool(ref) and complete
                    else f"the recorded flip list is incomplete/missing "
                    f"(list_ref={ref!r} missing={missing[:5]}… extra={extra[:5]}…)"
                    " — the wave never opens on a partial list"
                ),
                {"list_ref": ref, "missing": missing, "extra": extra},
            )
        )
        return

    # -- family-leg closing evidence -----------------------------------------------------
    # L1–L8 only: L9's evidence is the sig.probe-run/1 record below — there
    # is no +0 re-probe (WV-10: one polite request per portal; the record
    # is the evidence).
    if leg in FAMILY_LEGS and leg != "L9":
        run_set = _source_ids(inputs.get("run_set", []), "run_set")
        runs = inputs.get("runs") or {}
        empty_notes = inputs.get("empty_run_notes") or {}
        run_bad = []
        zeros = []
        for sid in run_set:
            row = runs.get(sid)
            if not isinstance(row, dict) or row.get("outcome") != "ok":
                run_bad.append(sid)
                continue
            added = row.get("claims_added")
            if not isinstance(added, int) or added < 0:
                run_bad.append(sid)
            elif added == 0 and not str(empty_notes.get(sid) or "").strip():
                zeros.append(sid)
        if run_bad:
            criteria.append(
                Criterion(
                    "runs",
                    False,
                    f"{run_bad} lack an ok run row with recorded claims_added — "
                    "every first run lands a recorded report (SIG-ENG-042); a "
                    "failed or absent run keeps the leg queued",
                    run_bad,
                )
            )
        elif zeros:
            criteria.append(
                Criterion(
                    "runs",
                    False,
                    f"{zeros} ran ok with claims_added == 0 but carry no "
                    "empty_run_notes reason — a zero-claim first run is "
                    "recorded with its reason, never silently accepted",
                    zeros,
                )
            )
        else:
            criteria.append(
                Criterion(
                    "runs",
                    True,
                    f"all {len(run_set)} run rows ok with recorded claims_added/captures",
                )
            )
        plus0 = inputs.get("plus0") or {}
        p_bad = [
            sid
            for sid in run_set
            if not isinstance(plus0.get(sid), dict) or plus0[sid].get("claims_added") != 0
        ]
        criteria.append(
            Criterion(
                "plus0",
                not p_bad,
                (
                    f"+0 re-runs recorded for all {len(run_set)} sources "
                    "(claims_added == 0 on unchanged input)"
                    if not p_bad
                    else f"{p_bad} lack a +0 re-run showing claims_added == 0 — "
                    "idempotence is proven per source before the leg closes"
                ),
                p_bad,
            )
        )
        cc = inputs.get("changed_count") or {}
        criteria.append(
            Criterion(
                "evidence",
                cc.get("recorded") is True,
                (
                    "the leg's changed_count read is recorded"
                    if cc.get("recorded") is True
                    else "changed_count not recorded — the leg report carries "
                    "the count delta, never a blank"
                ),
                cc,
            )
        )

    # -- L9: the probe-run record ---------------------------------------------------------
    # The gate binds the real sig.probe-run/1 record shape
    # (connectors.flock_portal_probe.probe_run_record): version, the
    # committed inventory count, the results table — every portal's
    # outcome lands (served|refused|deferred|not_attempted; refusals carry
    # kinds) — and the checks block reconciles with it. Expected yield ≈ 0
    # is an honest recorded outcome, never a refusal reason.
    if leg == "L9":
        probe = inputs.get("probe_run") or {}
        results = probe.get("results")
        checks = probe.get("checks") or {}
        probe_bad: list[str] = []
        if probe.get("version") != "sig.probe-run/1":
            probe_bad.append(f"version {probe.get('version')!r} ≠ sig.probe-run/1")
        inv_count = (probe.get("inventory") or {}).get("portal_count")
        if inv_count != PROBE_INVENTORY:
            probe_bad.append(
                f"inventory.portal_count {inv_count!r} ≠ the committed "
                f"inventory {PROBE_INVENTORY} — the run covered the known set"
            )
        counts: dict[str, int] = {}
        if not isinstance(results, list):
            probe_bad.append("results missing — every portal's outcome lands")
        else:
            if len(results) != PROBE_INVENTORY:
                probe_bad.append(
                    f"results holds {len(results)} rows ≠ {PROBE_INVENTORY} — "
                    "no portal is dropped from the record"
                )
            for i, row in enumerate(results):
                if not isinstance(row, dict):
                    probe_bad.append(f"results[{i}] not a row")
                    continue
                res = row.get("result")
                if res not in ("served", "refused", "deferred", "not_attempted"):
                    probe_bad.append(f"results[{i}].result {res!r} unknown")
                    continue
                counts[res] = counts.get(res, 0) + 1
                if (
                    res in ("refused", "deferred")
                    and not str(row.get("refusal_kind") or "").strip()
                ):
                    probe_bad.append(
                        f"results[{i}] ({row.get('portal')!r}) {res} without a "
                        "refusal_kind — every refusal carries a kind"
                    )
        served = checks.get("served", {}).get("count")
        refused = checks.get("refusals", {}).get("count")
        deferred = checks.get("refusals", {}).get("deferred")
        attempted = checks.get("coverage", {}).get("attempted")
        if not probe_bad:
            if served != counts.get("served", 0):
                probe_bad.append(
                    f"checks.served.count {served!r} ≠ served results {counts.get('served', 0)}"
                )
            if refused != counts.get("refused", 0):
                probe_bad.append(
                    f"checks.refusals.count {refused!r} ≠ refused results "
                    f"{counts.get('refused', 0)}"
                )
            if deferred != counts.get("deferred", 0):
                probe_bad.append(
                    f"checks.refusals.deferred {deferred!r} ≠ deferred results "
                    f"{counts.get('deferred', 0)}"
                )
            if isinstance(attempted, int) and attempted != counts.get("served", 0) + counts.get(
                "refused", 0
            ):
                probe_bad.append(
                    f"checks.coverage.attempted {attempted!r} ≠ served+refused "
                    "results — the ledger must reconcile"
                )
            if checks.get("coverage", {}).get("verdict") != "pass":
                probe_bad.append(
                    "checks.coverage.verdict is not 'pass' — the connector's "
                    "own fail-loud coverage check must be green (every fetch "
                    "landed a ledger outcome)"
                )
        criteria.append(
            Criterion(
                "probe",
                not probe_bad,
                (
                    f"sig.probe-run/1 covers all {PROBE_INVENTORY} portals "
                    f"(served={counts.get('served', 0)} "
                    f"refused={counts.get('refused', 0)} "
                    f"deferred={counts.get('deferred', 0)} "
                    f"not_attempted={counts.get('not_attempted', 0)}; expected "
                    "yield ≈ 0 is an honest recorded outcome)"
                    if not probe_bad
                    else "; ".join(probe_bad)
                ),
                counts,
            )
        )

    # -- L10: the closing records -----------------------------------------------------------
    if leg == "L10":
        mat = inputs.get("materialize") or {}
        criteria.append(
            Criterion(
                "closing",
                mat.get("ran") is True and bool(str(mat.get("at") or "").strip()),
                (
                    f"sig-materialize recorded run at {mat.get('at')!r} — after "
                    "the last first run, outside ingest runs"
                    if mat.get("ran") is True
                    else "sig-materialize not recorded run — the close waits"
                ),
                mat,
            )
        )
        delta = inputs.get("coverage_delta") or {}
        criteria.append(
            Criterion(
                "coverage",
                delta.get("recorded") is True,
                (
                    "the coverage-delta tool's read against the pre-wave "
                    "snapshot is recorded (P35.6, I8 §7.7)"
                    if delta.get("recorded") is True
                    else "coverage delta not recorded — the wave closes on a blank read never"
                ),
                delta,
            )
        )
        resumed = inputs.get("triggers_resumed") or {}
        not_resumed = [
            b["scheduler"] for b in BATCHES.values() if resumed.get(b["scheduler"]) is not True
        ]
        next_fires = inputs.get("next_fires") or {}
        fire_bad = [b for b, spec in BATCHES.items() if next_fires.get(b) != spec["next_fire"]]
        dispos = inputs.get("early_fire_dispositions") or {}
        dispo_bad = [b for b in EARLY_FIRE_BATCHES if not str(dispos.get(b) or "").strip()]
        closing_bad = []
        if not_resumed:
            closing_bad.append(f"triggers not resumed: {not_resumed}")
        if fire_bad:
            closing_bad.append(
                f"next-fire values missing or wrong for {fire_bad} — each "
                "batch's next fire is computed and recorded at resume "
                "(FEA-15)"
            )
        if dispo_bad:
            closing_bad.append(
                f"early fires without a recorded disposition: {dispo_bad} — "
                "fires before 11-20 land inside Wave C's pause window and are "
                "surfaced, never silently accepted"
            )
        criteria.append(
            Criterion(
                "resume",
                not closing_bad,
                (
                    "all seven triggers resumed; next-fires recorded "
                    "11-16…11-23; the four pre-11-20 fires carry FEA-15 "
                    "dispositions"
                    if not closing_bad
                    else "; ".join(closing_bad)
                ),
                {
                    "not_resumed": not_resumed,
                    "fire_bad": fire_bad,
                    "dispo_bad": dispo_bad,
                },
            )
        )


def leg_plan() -> list[dict[str, Any]]:
    """The deterministic Wave-B step plan (``sig.wave-b-plan/1`` content).

    Every step is an admission-gated unit: the driver gates the leg
    (``admit``), runs the steps in order — verifying between manual runs —
    then gates the leg close (``close``) before the next leg. Check mode
    prints this plan; apply executes it — a missed leg or a failed
    verification stops the driver and the refusal is recorded.
    """
    steps: list[dict[str, Any]] = []

    def step(leg: str, i: int, kind: str, text: str, **extra: Any) -> None:
        steps.append({"leg": leg, "seq": i, "kind": kind, "step": text, **extra})

    # -- L0 — the wave opening -------------------------------------------------------
    step(
        "L0",
        1,
        "prestate",
        "capture pre-state: per-source job + trigger JSON, sources.toml "
        "sha256, `sig-ops cadence --check` green (OM-14)",
        mutation=False,
    )
    step(
        "L0",
        2,
        "backup",
        "AR-2: on-demand Cloud SQL backup; record SUCCESSFUL before the first mutation",
        mutation=False,
    )
    step(
        "L0",
        3,
        "roll",
        "sig-ops roll-jobs --image <pinned sha256 digest> --record — one "
        "digest, every job; before/after recorded (ADR-111)",
        mutation=True,
    )
    step(
        "L0",
        4,
        "jobs",
        "scheduled-ops.sh --apply --paused — create the seven r11-* batch "
        "jobs + triggers paused on the rolled digest (R6)",
        batches=sorted(BATCHES),
        mutation=True,
    )
    step(
        "L0",
        5,
        "vocab",
        f"OPERATOR-RUN hosted step — sqitch deploy {VOCAB_CHANGE} "
        f"(INSERT-only: {VOCAB_PREDICATE} into vocab_predicate) then verify; "
        "never executed by this script or an agent",
        mutation=True,
        operator=True,
    )
    step(
        "L0",
        6,
        "handoff",
        f"hand the complete flip list ({len(FLIP_SOURCES)} flag rows + "
        "widen-target context, docs/build/reports/WAVE_B_FLIP_LIST.md) to "
        "the operator — the OP-26 execution is recorded, never performed "
        "by this row",
        mutation=False,
    )

    # -- L1–L8 — the family days ------------------------------------------------------
    for leg in FAMILY_LEGS[:8]:
        i = 0
        step(
            leg,
            (i := i + 1),
            "flips",
            f"record the family's OP-26 flips for {leg} — every gated source "
            "confirmed executed before the first run (HG-03 is the "
            "operator's); a leg whose flips are absent stays queued, reported",
            mutation=False,
        )
        for sid in LEG_SCOPE[leg]["gated"] + LEG_SCOPE[leg]["hosted"]:
            job = BATCHES.get(SOURCE_BATCH.get(sid, ""), {}).get("job", EXECUTION_JOB.get(sid, "?"))
            step(
                leg,
                (i := i + 1),
                "manual",
                f"manual first run: gcloud run jobs execute {job} "
                f"--args=scheduled-ingest,--source,{sid},--sink,pg --wait",
                source=sid,
                job=job,
                mutation=True,
            )
            step(
                leg,
                (i := i + 1),
                "verify",
                f"verify {sid}: run row ok, captures landed bytes, claims "
                "recorded, I8 §7.7 per-source checks (review-status, shadow "
                "diff 0, technology + jurisdiction keyed) — before the next "
                "source starts",
                source=sid,
                mutation=False,
            )
        for sid in LEG_SCOPE[leg]["widen"]:
            job = EXECUTION_JOB[sid]
            step(
                leg,
                (i := i + 1),
                "widen",
                f"widen-target execution (rides the existing flip — no "
                f"flag): gcloud run jobs execute {job} "
                f"--args=scheduled-ingest,--source,{sid},--sink,pg --wait; "
                "the next scheduled fire is then a +0",
                source=sid,
                job=job,
                mutation=True,
            )
            step(
                leg,
                (i := i + 1),
                "verify",
                f"verify {sid}: run row ok, the new targets' claims landed, "
                "existing targets unchanged",
                source=sid,
                mutation=False,
            )
        for sid in LEG_SCOPE[leg]["gated"] + LEG_SCOPE[leg]["hosted"] + LEG_SCOPE[leg]["widen"]:
            step(
                leg,
                (i := i + 1),
                "rerun",
                f"+0 re-run {sid}: re-execute the same job; assert "
                "claims_added == 0 on unchanged inputs",
                source=sid,
                mutation=True,
                expect="claims_added==0",
            )
        step(
            leg,
            (i := i + 1),
            "record",
            f"record the {leg} family-day report: run rows, changed_count, "
            "per-source §7.7 verifications, +0 diffs — a missed leg is "
            "reported, never silently skipped",
            mutation=False,
        )

    # -- L9 — the Flock probe ------------------------------------------------------------
    step(
        "L9",
        1,
        "flips",
        "record flock_transparency_portals' OP-26 flip — the probe row is "
        "the family's single flag (WV-10/ADR-188 probe-only posture is "
        "carried by the connector, never widened by the run)",
        mutation=False,
    )
    step(
        "L9",
        2,
        "manual",
        f"probe run: gcloud run jobs execute "
        f"{EXECUTION_JOB[PROBE_SOURCE]} "
        f"--args=scheduled-ingest,--source,{PROBE_SOURCE},--sink,pg --wait "
        "— one polite request per committed portal (917), stop-and-record "
        "on any challenge",
        source=PROBE_SOURCE,
        job=EXECUTION_JOB[PROBE_SOURCE],
        mutation=True,
    )
    step(
        "L9",
        3,
        "record",
        "land the sig.probe-run/1 record: every portal served|refused + "
        "refusal kind; expected yield ≈ 0 is a recorded outcome, never a "
        "failure",
        mutation=False,
    )

    # -- L10 — closing ---------------------------------------------------------------------
    step(
        "L10",
        1,
        "materialize",
        "run sig-materialize manually — after the last first run, outside "
        "ingest runs; reconcile's sharing-edge build where WA AGO/statute "
        "claims add sharing_partner",
        mutation=True,
    )
    step(
        "L10",
        2,
        "coverage",
        "run the coverage-delta tool (P35.6, I8 §7.7) against the pre-wave "
        "snapshot; record the delta",
        mutation=False,
    )
    step(
        "L10",
        3,
        "resume",
        "resume the seven paused r11-* triggers; compute + record each "
        "batch's next fire at resume — the four pre-11-20 fires "
        "(11-16…11-19) carry FEA-15 dispositions, surfaced never silently",
        batches=sorted(BATCHES),
        mutation=True,
    )
    step(
        "L10",
        4,
        "record",
        "record the closing report: materialize log, coverage delta, "
        "next-fires + dispositions, held-leg list — a held leg stays "
        "queued and is reported (OM-19)",
        mutation=False,
    )
    return steps


def load_inputs(path: str) -> dict:
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except OSError as exc:
        raise WaveGateError(f"cannot read inputs {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise WaveGateError(f"bad JSON in {path}: {exc}") from exc


def gate_main(argv: list[str] | None = None) -> int:
    import argparse

    ap = argparse.ArgumentParser(
        prog="sig-ops wave-b-gate",
        description=(
            "P36.12 Wave-B leg gate (sig.wave-b-gate/1): judges a recorded "
            "inputs JSON — refuses the leg (exit 42) unless the verbatim "
            "ING-GO-B, the window, the leg order + family-day pacing, the "
            "declared scope, the OP-26 flip records, the exclusions, "
            "serialisation and the leg's prerequisites/evidence all hold."
        ),
    )
    ap.add_argument("--inputs", required=True, help="the recorded inputs JSON")
    ap.add_argument("--out", default=None, help="also write the verdict JSON here")
    args = ap.parse_args(argv)

    try:
        inputs = load_inputs(args.inputs)
        verdict = evaluate(inputs)
    except WaveGateError as exc:
        print(f"sig-ops wave-b-gate: REFUSED — {exc}", file=sys.stderr)
        return 2

    record = verdict.to_record()
    text = json.dumps(record, indent=2, sort_keys=True)
    print(text)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(text + "\n")
        print(f"sig-ops wave-b-gate: -> {args.out}", file=sys.stderr)
    if verdict.decision != "go":
        print(
            "sig-ops wave-b-gate: NO-GO — the leg refuses; queued with its "
            "re-run prompt (see record).",
            file=sys.stderr,
        )
        return 42
    return 0


def plan_main(argv: list[str] | None = None) -> int:
    import argparse

    ap = argparse.ArgumentParser(
        prog="sig-ops wave-b-plan",
        description=(
            "P36.12 Wave-B step plan (sig.wave-b-plan/1): the deterministic "
            "ordered steps for L0…L10 — plan-only output, never a mutation."
        ),
    )
    ap.add_argument("--json", action="store_true", help="emit the JSON record")
    args = ap.parse_args(argv)
    steps = leg_plan()
    if args.json:
        print(
            json.dumps(
                {
                    "kind": PLAN_SCHEMA,
                    "wave": WAVE,
                    "window": [WINDOW_START, WINDOW_END],
                    "steps": steps,
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0
    print(
        f"Wave {WAVE} activation plan — window {WINDOW_START} → {WINDOW_END} "
        "(ING-GO-B, one manual run at a time, one family per day)"
    )
    for s in steps:
        mark = " (mutation)" if s.get("mutation") else ""
        op = " [OPERATOR]" if s.get("operator") else ""
        print(f"  {s['leg']}.{s['seq']:>2}  {s['step']}{mark}{op}")
    return 0


__all__ = [
    "BATCHES",
    "Criterion",
    "EARLY_FIRE_BATCHES",
    "EXECUTION_JOB",
    "FAMILY_LEGS",
    "FEA15_CUTOVER",
    "FLIP_SOURCES",
    "GO_VERBATIM",
    "LEGS",
    "LEG_SCOPE",
    "NEVER_SOURCES",
    "PEEL_DAY",
    "PEEL_FIRE",
    "PLAN_SCHEMA",
    "PROBE_INVENTORY",
    "PROBE_SOURCE",
    "SCHEMA",
    "SHARED_DAY_PAIR",
    "SOURCE_BATCH",
    "VOCAB_CHANGE",
    "VOCAB_PREDICATE",
    "Verdict",
    "WINDOW_END",
    "WINDOW_START",
    "WaveGateError",
    "evaluate",
    "gate_main",
    "leg_plan",
    "plan_main",
]
