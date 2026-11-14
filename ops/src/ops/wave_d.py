# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P37.54 Wave-D activation — the leg plan and the ``sig.wave-d-gate/1``
go/no-go checker (ticket 481, R11-ACQ-27, I8 §7.2–7.8, OM-19/OM-20).

Wave D is the Round-11 Tier-2 ingestion wave — "as ACQ-16, for the Tier-2
families that landed" — plus the S6 seatless sources (Axon Connect,
DocumentCloud/MuckRock, Sourcewell/OMNIA) and the RB-06b seat. The
contract's two windows (future-ok: scheduled: contract windows):

* **window 1** — 2026-11-23 → 2026-12-04, 14:00–20:00Z — future-ok: scheduled: contract window.
  L0 opens and the family days run one per day. The S6 extras
  family day targets this window so its sources ship in the next cadence
  cut.
* **window 2** — 2026-12-14 → 2026-12-18, 14:00–20:00Z — future-ok: scheduled: contract window:
  the recovery window — a leg held in the first window (flips not
  executed, a failed verify) runs here and is reported, never silently
  skipped (OM-19); sources whose legs land in this window ship in the
  2027-01-15 cadence cut (future-ok: scheduled: contract cut), not the
  12-15 cut. The 12-15 release-cut day
  inside this window is excluded (no leg runs it). L11 closes the wave.

The twelve legs, in order:

* **L0 — wave opening** (window 1): OM-14 pre-state capture (job/trigger
  JSON, ``sources.toml`` sha256, ``cadence --check`` green) → AR-2
  on-demand backup verified ``SUCCESSFUL`` → ``sig-ops roll-jobs
  --record`` on one pinned digest → ``scheduled-ops.sh --apply --paused``
  creates the three ``r11-tier2-*`` batch jobs paused → the complete
  operator-facing flip list handed to the operator (the OP-26 execution
  is recorded, never performed here).
* **L1–L9 — the nine Tier-2 family days** in ticket order (ACQ-19
  P37.47, ACQ-20 P37.48, ACQ-21 P37.49, ACQ-22 P37.50, ACQ-23a P37.69a,
  ACQ-23b P37.69b, ACQ-24 P37.51, ACQ-25 P37.52, ACQ-26 P37.53): the
  day's flips recorded → manual first runs one source at a time on the
  member's batch job → per-source I8 §7.7 verification → ``+0`` re-runs.
* **L10 — the S6 extras family day** (P36.76/77/78 + RB-06b):
  ``axon_connect``, ``documentcloud``, ``muckrock_public``,
  ``sourcewell``, ``omnia_partners``, ``camreg_bellevue_wa`` — six
  seatless gated sources run single-source on ``sig-ingest-r11-tier2-01``.
* **L11 — closing**: ``sig-materialize`` → coverage delta vs the
  pre-wave snapshot → resume the three paused tier-2 schedules
  (cadence ``state`` paused→enabled + declaration republish — the
  due-dispatcher shape, never a per-source trigger resume) → each
  batch's next fire recorded (2026-12-25/26/27T07:37Z — future-ok: scheduled: dom crons)
  after the 12-15 cut; second-window sources ship 2027-01-15 — future-ok: scheduled: contract cut.

This module judges **recorded inputs** — it never reads live state
itself; the driver (``ops/gcp/wave-d.sh``) captures the inputs and this
module refuses (exit 42) unless every criterion holds. A refused leg
queues with its re-run prompt — a missed leg is reported, never
silently skipped (OM-19). The gate runs twice per leg: ``action=admit``
before the leg's first mutation and ``action=close`` before the leg is
recorded green.

Criteria (each refuse-on-fail):

* ``go`` — the recorded ING-GO-D answer, byte-equal to the GATE-G6
  GATE DECISIONS selection ``"Approve ING-GO-D + flip list (rec.)"``
  (2026-11-05T15:20Z, operator-signed commit ``b91f8e58``); silence is
  never consent.
* ``window`` — the supplied ``now`` inside either window's span and
  inside the 14:00–20:00Z daily band, never on the 12-15 release-cut
  day; evaluated on the supplied instant, never the wall clock.
* ``exclusions`` — no ``sig-materialize``/G2 slot/release-cut active.
* ``order`` — ``completed`` {leg, day} records cover every earlier leg
  (green or held-reported); completed days are admissible window dates
  and non-decreasing in leg order; the leg is not already green.
* ``pacing`` — one family leg per day (L0's opening and L11's closing
  may share a family day; no two family legs share).
* ``scope`` — ``run_set`` == the leg's declared set exactly; the
  P37.16a/b Part VIII dossier-capture seats (context, their own rows'
  gating), ``doj_ctas_awards`` and the Wave-A tribal S8 lane are never
  in this wave.
* ``flips`` — every gated source in the leg recorded in the operator's
  executed OP-26 flips + the family confirmation present.
* ``serialize`` — one manual run at a time, across waves.
* ``prestate`` / ``backup`` — L0 only.
* ``roll`` / ``jobs`` / ``handoff`` — L0 close.
* ``runs`` / ``plus0`` / ``evidence`` — family-leg close.
* ``closing`` / ``coverage`` / ``resume`` — L11 close.

Exit codes: ``0`` = go · ``42`` = no-go (queued) · ``2`` = usage.
"""

from __future__ import annotations

import datetime as _dt
import json
import re
import sys
from dataclasses import dataclass, field
from typing import Any

SCHEMA = "sig.wave-d-gate/1"
PLAN_SCHEMA = "sig.wave-d-plan/1"
WAVE = "D"

#: The two contract windows (future-ok: scheduled: contract windows) —
#: "window 11-23 -> 12-04" and "window 12-14 -> 12-18", each day inside
#: the 14:00–20:00Z band; end instants exclusive. The second window is
#: the OM-19 recovery window: sources whose legs land there ship in the
#: 2027-01-15 cadence cut (future-ok: scheduled: contract cut), never the
#: 12-15 cut.
WINDOWS: tuple[tuple[str, str, _dt.date, _dt.date], ...] = (
    (
        "2026-11-23T14:00:00Z",  # future-ok: scheduled: window 11-23 -> 12-04 open
        "2026-12-04T20:00:00Z",  # future-ok: scheduled: window 11-23 -> 12-04 end (exclusive)
        _dt.date(2026, 11, 23),  # future-ok: scheduled: window-1 dates
        _dt.date(2026, 12, 4),  # future-ok: scheduled: window-1 dates
    ),
    (
        "2026-12-14T14:00:00Z",  # future-ok: scheduled: window 12-14 -> 12-18 open
        "2026-12-18T20:00:00Z",  # future-ok: scheduled: window 12-14 -> 12-18 end (exclusive)
        _dt.date(2026, 12, 14),  # future-ok: scheduled: window-2 dates
        _dt.date(2026, 12, 18),  # future-ok: scheduled: window-2 dates
    ),
)
WINDOW_START_HH = 14
WINDOW_END_HH = 20

#: The 12-15 14:00Z release cut lands inside the second window's dates —
#: a leg never runs it, and no completed day may record it.
CUT_DAY = _dt.date(2026, 12, 15)  # future-ok: scheduled: the 12-15 G3 cut day

#: The twelve legs, in order. A leg admits only when every earlier leg
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
    "L11",
)

#: The recorded ING-GO-D answer — the GATE-G6 GATE DECISIONS selection
#: verbatim (2026-11-05T15:20Z, operator-signed commit ``b91f8e58``; the
#: gate requires byte-equality, never a paraphrase).
GO_VERBATIM = "Approve ING-GO-D + flip list (rec.)"
GO_SOURCE = "GATE-G6 2026-11-05T15:20Z (operator-signed commit b91f8e58)"

#: The three new paused Wave-D batch rows (ops/cadence.toml; jobs created
#: by ``scheduled-ops.sh --apply --paused`` at L0). Under the dispatcher
#: shape (P35.1c) the cadence ``state`` row is the due-set pause — the
#: resume at L11 flips ``state`` paused→enabled + republishes the
#: declaration; next fires are computed at contract time.
BATCHES: dict[str, dict[str, str]] = {
    "r11-tier2-01": {
        "job": "sig-ingest-r11-tier2-01",
        "scheduler": "sig-sched-r11-tier2-01",
        "cron": "37 7 25 * *",
        "next_fire": "2026-12-25T07:37:00Z",  # future-ok: scheduled: dom-25 cron
    },
    "r11-tier2-02": {
        "job": "sig-ingest-r11-tier2-02",
        "scheduler": "sig-sched-r11-tier2-02",
        "cron": "37 7 26 * *",
        "next_fire": "2026-12-26T07:37:00Z",  # future-ok: scheduled: dom-26 cron
    },
    "r11-tier2-03": {
        "job": "sig-ingest-r11-tier2-03",
        "scheduler": "sig-sched-r11-tier2-03",
        "cron": "37 7 27 * *",
        "next_fire": "2026-12-27T07:37:00Z",  # future-ok: scheduled: dom-27 cron
    },
}

#: The seatless execution host — the six gated sources that carry no
#: batch seat (the five S6 sources + the RB-06b Bellevue seat) run
#: single-source manual executions on the wave's first batch job, the
#: same mechanism Wave B used for its seatless ccops_* rows.
SEATLESS_JOB = "sig-ingest-r11-tier2-01"

#: Declared per-leg scope — the landed registry/cadence truth
#: (P37.47…P37.53 + P37.69a/b + the S6 tickets). ``gated`` = rows on the
#: operator's OP-26 flip list (``ingestion_permitted=false`` until
#: executed); every gated member runs on its batch's job.
LEG_SCOPE: dict[str, dict[str, tuple[str, ...]]] = {
    "L1": {  # ACQ-19 (P37.47) — Tier-2 reuse wave; 30 gated seats
        "gated": (
            "camreg_ca_monterey_park_flock_camera",
            "camreg_fl_broward_county_us_palm_beach",
            "camreg_jeffersonville_in_flock",
            "camreg_nv_las_vegas_us_clark_county",
            "camreg_santa_fe_nm_park_cameras",
            "ccops_berkeley",
            "ccops_boston",
            "ccops_hi_honolulu_police_department",
            "ccops_il_chicago_oig_shotspotter",
            "ccops_mi_wayne_county_commission",
            "ccops_mo_st_louis_fy21_spi_shotspotter",
            "ccops_nc_charlotte_mecklenburg_police",
            "ccops_nc_elizabeth_city_police",
            "ccops_ny_new_york_nyc_comptroller",
            "ccops_san_francisco_bay_ca",
            "ccops_san_jose_ca",
            "ccops_santa_clara_county_ca",
            "dhs_fusion_centers",
            "dot_511_id",
            "dot_511_nm",
            "dot_511_nv",
            "grant_ok_safe_oklahoma_grant",
            "grant_us_doj_cops_technology",
            "legis_vi_legislature_virgin_islands",
            "policy_anaheim_ca_pd_policy_manual",
            "policy_maricopa_county_az_mcso_policies",
            "policy_norman_ok_alpr_policy_amendment",
            "statrep_new_york_ny_nyc_doi_oig",
            "statrep_tx_ca_nm_ri_fl_il_eff_red_flag",
            "statrep_us_upturn_mass_extraction_2020",
        ),
    },
    "L2": {  # ACQ-20 (P37.48) — aggregate lanes; 13 gated seats
        "gated": (
            "camreg_az_mesa_city_of_expenditures",
            "camreg_de_delaware_checkbook_expenditure",
            "camreg_il_chicago_payments",
            "camreg_il_chicago_violence_reduction",
            "camreg_mi_detroit_dpd_shotspotter",
            "camreg_nj_new_jersey_yourmoney",
            "camreg_oakland_ca_shotspotter_2013_2015",
            "camreg_us_ate_camera_location_and_per",
            "camreg_us_body_worn_camera",
            "camreg_us_municipal_contract_expenditure",
            "camreg_us_socrata_hosted_vendor",
            "camreg_wa_washington_state_open",
            "procportal_tx_texas_dir_cooperative",
        ),
    },
    "L3": {  # ACQ-21 (P37.49) — federal datasets; 8 gated seats
        "gated": (
            "camreg_us_nces_school_survey_on_crime",
            "legis_us_federal_register_api",
            "statrep_tx_south_padre_island_faa",
            "statrep_us_2024_federal_agency",
            "statrep_us_dhs_ai_use",
            "statrep_us_ice_287_monthly",
            "statrep_us_ice_287_participating",
            "statrep_us_wiretap_summary_tables",
        ),
    },
    "L4": {  # ACQ-22 (P37.50) — agenda platforms v2; 10 gated seats
        "gated": (
            "agenda_az_maricopa_county_board_of",
            "agenda_bexar_county_tx_agenda_center",
            "agenda_durham_nc_agenda_center",
            "agenda_frisco_tx_onbase_agenda_online",
            "agenda_hialeah_fl_agenda_center",
            "agenda_jersey_city_nj_digital_agenda",
            "agenda_nd_fargo_city_commission_agendas",
            "agenda_savannah_ga_2023_05_25",
            "agenda_tampa_fl_onbase_agenda_online",
            "agenda_tx_dallas_county_commissioners",
        ),
    },
    "L5": {  # ACQ-23a (P37.69a) — international open-data; 36 gated seats
        "gated": (
            "camreg_au_ckan_package_search",
            "camreg_au_nsw_sydney_street_safety",
            "camreg_au_qld_towns_cctv_camera_register",
            "camreg_au_tas_emergency_closed_circuit",
            "camreg_au_tas_hobar_security_camera",
            "camreg_au_vic_ballarat_cctv_cameras",
            "camreg_au_vic_geelong_closed_circuit",
            "camreg_au_wa_perth_security_cameras",
            "camreg_es_md_madrid_c_maras_de",
            "camreg_eu_eea_data_europa_search_api",
            "camreg_fr_92_grand_paris_seine_ouest_vid",
            "camreg_gb_eng_barnet_cctv_camera",
            "camreg_gb_eng_barnet_cctv_traffic",
            "camreg_gb_eng_brist_cctv_cameras",
            "camreg_gb_eng_leice_cctv_cameras",
            "camreg_gb_eng_mansf_cctv_cameras",
            "camreg_gb_eng_north_cctv_cameras",
            "camreg_gb_eng_traff_trafford_cctv",
            "camreg_gb_sct_edinburgh_public_cctv",
            "camreg_ie_d_dublin_traffic_poles_with",
            "camreg_it_me_messina_videosorveglianza",
            "camreg_pt_11_lisboa_sistema_de",
            "camreg_si_048_ko_evje_videonadzor_na",
            "camreg_ua_18_korosten",
            "ccops_gb_eng_barnet_traffic_cctv",
            "ccops_iso_au_privacy_commissioner",
            "ccops_it_tn_trento_provvedimento_dell_11",
            "ccops_si_085_novo_mesto_evidenca_o",
            "dot_511_gb",
            "legis_ie_rs_general_scheme",
            "statrep_ca_special_parliament_use",
            "statrep_fr_cnil_utilisation_de",
            "statrep_gb_enforcement_action",
            "statrep_gb_eng_seven_cctv_june_2026",
            "statrep_gb_sct_joint_assurance_review",
            "statrep_gb_uk_algorithmic_transparency",
        ),
    },
    "L6": {  # ACQ-23b (P37.69b) — OGC WFS; 4 gated seats (Ipswich
        # enumerated — its endpoint preflight is D-P37.69b-1, whose owner
        # names this wave's flip-window census)
        "gated": (
            "camreg_gb_eng_ipswich_cctv_camera",
            "camreg_gb_eng_runny_cctv_cameras",
            "camreg_gb_eng_south_skdc_cctv",
            "camreg_gb_sct_clackmannanshire_cctv",
        ),
    },
    "L7": {  # ACQ-24 (P37.51) — Puerto Rico SUTRA/OCPR; 8 gated seats
        "gated": (
            "legis_pr_pc0489_ley_del",
            "legis_pr_pc0560_plan_de",
            "legis_pr_rc0740_investigaci_sobre",
            "legis_pr_rc0787_resoluci_de",
            "legis_pr_rcs0198_resoluci_conjunta",
            "legis_pr_rs0604_resoluci_del",
            "legis_pr_sistema_nico_de",
            "procportal_pr_consulta_del_registro",
        ),
    },
    "L8": {  # ACQ-25 (P37.52) — document-list pages; 8 gated seats
        "gated": (
            "camreg_ma_massachusetts_capital",
            "grant_il_illinois_gata_csfa",
            "grant_ma_massachusetts_law_enforcement",
            "grant_oh_ohio_criminal_justice",
            "procportal_fl_florida_buy_cooperative",
            "procportal_ny_northeastern_regional",
            "procportal_us_naspo_valuepoint_portfolio",
            "procportal_wa_wsipc_rfp_24",
        ),
    },
    "L9": {  # ACQ-26 (P37.53) — programme-level lane; 23 gated seats
        "gated": (
            "agenda_us_agency_fusus_real",
            "camreg_bloomington_il_drone_flights",
            "camreg_detroit_mi_project_green_light",
            "camreg_ga_brookhaven_flock_camera",
            "camreg_ga_flock_cameras_asof",
            "camreg_ga_savannah_flock_camera",
            "camreg_gastonia_nc_flock_condor_cameras",
            "camreg_la_east_baton_rouge_parish_flock",
            "camreg_la_new_orleans_eye_on",
            "camreg_medford_or_drone_deployments_fs",
            "camreg_peoria_il_drone_usage",
            "camreg_us_agency_drone_flight",
            "camreg_us_agency_published_flock",
            "ccops_ca_calistoga_police_department",
            "ccops_ca_pinole_police_department",
            "ccops_mn_dayton_police_department",
            "ccops_oh_cincinnati_police_department",
            "ccops_ri_narragansett_police_camera",
            "policy_chicago_il_oemc_link_your",
            "policy_lafayette_in_camera_registration",
            "policy_us_private_camera_registry",
            "policy_zionsville_in_camera_registry",
            "statrep_vt_vermont_law_enforcement",
        ),
    },
    "L10": {  # S6 extras (P36.76 Axon Connect, P36.77 DocumentCloud/
        # MuckRock, P36.78 Sourcewell/OMNIA) + the RB-06b seat — six
        # seatless gated sources, single-source on the wave's first job.
        "gated": (
            "axon_connect",
            "documentcloud",
            "muckrock_public",
            "sourcewell",
            "omnia_partners",
            "camreg_bellevue_wa",
        ),
    },
}

#: Legs that run ingestion families (one-family-per-day applies; L0
#: opens and L11 closes — they may share a calendar day with a family).
FAMILY_LEGS: tuple[str, ...] = (
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

#: The tier-2 batch each gated member runs on (source → batch id; the
#: L10 seatless six ride SEATLESS_JOB instead — see EXECUTION_JOB).
SOURCE_BATCH: dict[str, str] = {
    "camreg_ca_monterey_park_flock_camera": "r11-tier2-01",
    "camreg_fl_broward_county_us_palm_beach": "r11-tier2-01",
    "camreg_jeffersonville_in_flock": "r11-tier2-01",
    "camreg_nv_las_vegas_us_clark_county": "r11-tier2-01",
    "camreg_santa_fe_nm_park_cameras": "r11-tier2-01",
    "dhs_fusion_centers": "r11-tier2-01",
    "dot_511_nm": "r11-tier2-01",
    "camreg_az_mesa_city_of_expenditures": "r11-tier2-01",
    "camreg_de_delaware_checkbook_expenditure": "r11-tier2-01",
    "camreg_mi_detroit_dpd_shotspotter": "r11-tier2-01",
    "camreg_nj_new_jersey_yourmoney": "r11-tier2-01",
    "camreg_us_municipal_contract_expenditure": "r11-tier2-01",
    "camreg_us_socrata_hosted_vendor": "r11-tier2-01",
    "camreg_wa_washington_state_open": "r11-tier2-01",
    "procportal_tx_texas_dir_cooperative": "r11-tier2-01",
    "camreg_us_nces_school_survey_on_crime": "r11-tier2-01",
    "legis_us_federal_register_api": "r11-tier2-01",
    "statrep_us_2024_federal_agency": "r11-tier2-01",
    "statrep_us_dhs_ai_use": "r11-tier2-01",
    "statrep_us_ice_287_participating": "r11-tier2-01",
    "statrep_us_wiretap_summary_tables": "r11-tier2-01",
    "agenda_durham_nc_agenda_center": "r11-tier2-01",
    "agenda_frisco_tx_onbase_agenda_online": "r11-tier2-01",
    "agenda_hialeah_fl_agenda_center": "r11-tier2-01",
    "agenda_jersey_city_nj_digital_agenda": "r11-tier2-01",
    "agenda_nd_fargo_city_commission_agendas": "r11-tier2-01",
    "agenda_savannah_ga_2023_05_25": "r11-tier2-01",
    "agenda_tampa_fl_onbase_agenda_online": "r11-tier2-01",
    "camreg_ma_massachusetts_capital": "r11-tier2-01",
    "procportal_fl_florida_buy_cooperative": "r11-tier2-01",
    "procportal_ny_northeastern_regional": "r11-tier2-01",
    "procportal_us_naspo_valuepoint_portfolio": "r11-tier2-01",
    "procportal_wa_wsipc_rfp_24": "r11-tier2-01",
    "statrep_vt_vermont_law_enforcement": "r11-tier2-01",
    "camreg_detroit_mi_project_green_light": "r11-tier2-01",
    "camreg_ga_brookhaven_flock_camera": "r11-tier2-01",
    "camreg_ga_flock_cameras_asof": "r11-tier2-01",
    "camreg_ga_savannah_flock_camera": "r11-tier2-01",
    "camreg_gastonia_nc_flock_condor_cameras": "r11-tier2-01",
    "camreg_la_east_baton_rouge_parish_flock": "r11-tier2-01",
    "procportal_pr_consulta_del_registro": "r11-tier2-01",
    "ccops_gb_eng_barnet_traffic_cctv": "r11-tier2-01",
    "dot_511_id": "r11-tier2-02",
    "dot_511_nv": "r11-tier2-02",
    "legis_vi_legislature_virgin_islands": "r11-tier2-02",
    "ccops_hi_honolulu_police_department": "r11-tier2-02",
    "ccops_mi_wayne_county_commission": "r11-tier2-02",
    "camreg_oakland_ca_shotspotter_2013_2015": "r11-tier2-02",
    "camreg_us_ate_camera_location_and_per": "r11-tier2-02",
    "camreg_us_body_worn_camera": "r11-tier2-02",
    "statrep_tx_south_padre_island_faa": "r11-tier2-02",
    "legis_pr_pc0489_ley_del": "r11-tier2-02",
    "legis_pr_pc0560_plan_de": "r11-tier2-02",
    "legis_pr_rc0740_investigaci_sobre": "r11-tier2-02",
    "legis_pr_rc0787_resoluci_de": "r11-tier2-02",
    "legis_pr_rcs0198_resoluci_conjunta": "r11-tier2-02",
    "legis_pr_rs0604_resoluci_del": "r11-tier2-02",
    "legis_pr_sistema_nico_de": "r11-tier2-02",
    "grant_il_illinois_gata_csfa": "r11-tier2-02",
    "grant_ma_massachusetts_law_enforcement": "r11-tier2-02",
    "grant_oh_ohio_criminal_justice": "r11-tier2-02",
    "agenda_us_agency_fusus_real": "r11-tier2-02",
    "camreg_bloomington_il_drone_flights": "r11-tier2-02",
    "camreg_medford_or_drone_deployments_fs": "r11-tier2-02",
    "camreg_peoria_il_drone_usage": "r11-tier2-02",
    "camreg_us_agency_drone_flight": "r11-tier2-02",
    "camreg_us_agency_published_flock": "r11-tier2-02",
    "camreg_au_ckan_package_search": "r11-tier2-02",
    "camreg_au_nsw_sydney_street_safety": "r11-tier2-02",
    "camreg_au_qld_towns_cctv_camera_register": "r11-tier2-02",
    "camreg_au_tas_emergency_closed_circuit": "r11-tier2-02",
    "camreg_au_tas_hobar_security_camera": "r11-tier2-02",
    "camreg_au_vic_ballarat_cctv_cameras": "r11-tier2-02",
    "camreg_au_vic_geelong_closed_circuit": "r11-tier2-02",
    "camreg_au_wa_perth_security_cameras": "r11-tier2-02",
    "camreg_eu_eea_data_europa_search_api": "r11-tier2-02",
    "camreg_gb_eng_barnet_cctv_camera": "r11-tier2-02",
    "camreg_gb_eng_barnet_cctv_traffic": "r11-tier2-02",
    "camreg_gb_eng_brist_cctv_cameras": "r11-tier2-02",
    "camreg_gb_eng_leice_cctv_cameras": "r11-tier2-02",
    "camreg_gb_eng_mansf_cctv_cameras": "r11-tier2-02",
    "camreg_gb_eng_north_cctv_cameras": "r11-tier2-02",
    "camreg_gb_eng_traff_trafford_cctv": "r11-tier2-02",
    "camreg_gb_sct_edinburgh_public_cctv": "r11-tier2-02",
    "camreg_ie_d_dublin_traffic_poles_with": "r11-tier2-02",
    "ccops_iso_au_privacy_commissioner": "r11-tier2-02",
    "dot_511_gb": "r11-tier2-02",
    "statrep_ca_special_parliament_use": "r11-tier2-02",
    "statrep_fr_cnil_utilisation_de": "r11-tier2-02",
    "statrep_gb_enforcement_action": "r11-tier2-02",
    "ccops_berkeley": "r11-tier2-03",
    "ccops_boston": "r11-tier2-03",
    "ccops_il_chicago_oig_shotspotter": "r11-tier2-03",
    "ccops_mo_st_louis_fy21_spi_shotspotter": "r11-tier2-03",
    "ccops_nc_charlotte_mecklenburg_police": "r11-tier2-03",
    "ccops_nc_elizabeth_city_police": "r11-tier2-03",
    "ccops_ny_new_york_nyc_comptroller": "r11-tier2-03",
    "ccops_san_francisco_bay_ca": "r11-tier2-03",
    "ccops_san_jose_ca": "r11-tier2-03",
    "ccops_santa_clara_county_ca": "r11-tier2-03",
    "grant_ok_safe_oklahoma_grant": "r11-tier2-03",
    "grant_us_doj_cops_technology": "r11-tier2-03",
    "policy_anaheim_ca_pd_policy_manual": "r11-tier2-03",
    "policy_maricopa_county_az_mcso_policies": "r11-tier2-03",
    "policy_norman_ok_alpr_policy_amendment": "r11-tier2-03",
    "statrep_new_york_ny_nyc_doi_oig": "r11-tier2-03",
    "statrep_tx_ca_nm_ri_fl_il_eff_red_flag": "r11-tier2-03",
    "statrep_us_upturn_mass_extraction_2020": "r11-tier2-03",
    "camreg_il_chicago_payments": "r11-tier2-03",
    "camreg_il_chicago_violence_reduction": "r11-tier2-03",
    "statrep_us_ice_287_monthly": "r11-tier2-03",
    "agenda_az_maricopa_county_board_of": "r11-tier2-03",
    "agenda_bexar_county_tx_agenda_center": "r11-tier2-03",
    "agenda_tx_dallas_county_commissioners": "r11-tier2-03",
    "camreg_la_new_orleans_eye_on": "r11-tier2-03",
    "ccops_ca_calistoga_police_department": "r11-tier2-03",
    "ccops_ca_pinole_police_department": "r11-tier2-03",
    "ccops_mn_dayton_police_department": "r11-tier2-03",
    "ccops_oh_cincinnati_police_department": "r11-tier2-03",
    "ccops_ri_narragansett_police_camera": "r11-tier2-03",
    "policy_chicago_il_oemc_link_your": "r11-tier2-03",
    "policy_lafayette_in_camera_registration": "r11-tier2-03",
    "policy_us_private_camera_registry": "r11-tier2-03",
    "policy_zionsville_in_camera_registry": "r11-tier2-03",
    "camreg_es_md_madrid_c_maras_de": "r11-tier2-03",
    "camreg_si_048_ko_evje_videonadzor_na": "r11-tier2-03",
    "camreg_fr_92_grand_paris_seine_ouest_vid": "r11-tier2-03",
    "camreg_it_me_messina_videosorveglianza": "r11-tier2-03",
    "camreg_pt_11_lisboa_sistema_de": "r11-tier2-03",
    "camreg_ua_18_korosten": "r11-tier2-03",
    "ccops_it_tn_trento_provvedimento_dell_11": "r11-tier2-03",
    "ccops_si_085_novo_mesto_evidenca_o": "r11-tier2-03",
    "legis_ie_rs_general_scheme": "r11-tier2-03",
    "statrep_gb_eng_seven_cctv_june_2026": "r11-tier2-03",
    "statrep_gb_sct_joint_assurance_review": "r11-tier2-03",
    "statrep_gb_uk_algorithmic_transparency": "r11-tier2-03",
    "camreg_gb_eng_ipswich_cctv_camera": "r11-tier2-03",
    "camreg_gb_eng_runny_cctv_cameras": "r11-tier2-03",
    "camreg_gb_eng_south_skdc_cctv": "r11-tier2-03",
    "camreg_gb_sct_clackmannanshire_cctv": "r11-tier2-03",
}

#: Execution job per source (batch members → their batch's job; the six
#: L10 seatless sources → SEATLESS_JOB). Every gated source resolves.
EXECUTION_JOB: dict[str, str] = {
    **{sid: BATCHES[b]["job"] for sid, b in SOURCE_BATCH.items()},
    **{sid: SEATLESS_JOB for sid in LEG_SCOPE["L10"]["gated"]},
}

#: Never in this wave — each recorded, none implicit:
#: * the eight Part VIII dossier-capture seats (P37.16a/b) — batch
#:   members whose flips and captures ride those rows' own in-ticket
#:   operator go; never this wave's OP-26 scope. An unflipped seat's
#:   later batch fire records the loader's gated refusal — a recorded
#:   outcome, never a defeat attempt.
#: * ``doj_ctas_awards`` (AP-T2-093 — not tribal) stays deferred under
#:   ``D-R11-LATER-09``.
#: * the ADR-185 tribal S8 lane landed at P35.11 (Wave A).
DOSSIER_SEATS: tuple[str, ...] = (
    "ccops_ca_san_diego_privacy_advisory",
    "ccops_ca_san_diego_sunshine_act_goods",
    "ccops_ok_oklahoma_city_okc_flock_council",
    "ccops_ok_tulsa_flock_policies",
    "ccops_san_diego_ca",
    "policy_ok_oklahoma_dac_uved",
    "procportal_ok_oklahoma_omes_statewide",
    "statrep_ca_california_auditor_alpr",
)

NEVER_SOURCES: frozenset[str] = frozenset(
    {
        "doj_ctas_awards",
        "camreg_tribal_all_leaders_directory",
        "legis_tribal_tohono_oodham_notice",
        *DOSSIER_SEATS,
    }
)

#: The complete operator flip list = every gated source across the
#: family legs (the flag rows the OP-26 execution names; the dossier
#: seats are context rows on the list, never flag rows).
FLIP_SOURCES: tuple[str, ...] = tuple(sid for leg in FAMILY_LEGS for sid in LEG_SCOPE[leg]["gated"])

#: Re-run prompt recorded on every refusal.
RERUN = (
    "implement-spec "
    "spec=docs/tickets/481_P37.54__wave-d-activation.md "
    "live_verification=true (scope: the queued Wave-D legs only — each leg "
    "needs the recorded ING-GO-D (GATE-G6 b91f8e58), its window, its own "
    "gate inputs and its family's executed OP-26 flips; the flip list is "
    "the operator's, never this row's)"
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
                "windows": [
                    {
                        "start": w[0],
                        "end": w[1],
                        "first_day": w[2].isoformat(),
                        "last_day": w[3].isoformat(),
                    }
                    for w in WINDOWS
                ],
                "window_band_hh": [WINDOW_START_HH, WINDOW_END_HH],
                "cut_day": CUT_DAY.isoformat(),
                "legs": list(LEGS),
                "family_legs": list(FAMILY_LEGS),
                "batches": {k: dict(v) for k, v in BATCHES.items()},
                "seatless_job": SEATLESS_JOB,
                "dossier_seats": list(DOSSIER_SEATS),
                "flip_source_count": len(FLIP_SOURCES),
                "never_sources": sorted(NEVER_SOURCES),
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


def _admissible_day(d: _dt.date) -> bool:
    """A completed leg day inside either window's dates, never the cut day."""
    if d == CUT_DAY:
        return False
    return any(w[2] <= d <= w[3] for w in WINDOWS)


def _window_of(now: _dt.datetime) -> int | None:
    """The window index (0|1) the instant falls inside, else None."""
    for i, w in enumerate(WINDOWS):
        if _iso(w[0]) <= now < _iso(w[1]):
            return i
    return None


def _completed_entries(inputs: dict) -> tuple[list[tuple[str, _dt.date]], list[str]]:
    """Validate the ``completed`` record list — returns (entries, errors)."""
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
        if not _admissible_day(d):
            errors.append(
                f"{where}: day {d.isoformat()} is not an admissible window "
                "date (inside 11-23→12-04 or 12-14→12-18, never the 12-15 "
                "cut day — future-ok: scheduled: contract windows)"
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
                f"leg {leg!r} is not one of {LEGS} — the wave admits L0…L11 only",
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

    # -- window (either span, the 14–20Z band, never the cut day) -------------------
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
        w = _window_of(now)
        band = WINDOW_START_HH <= now.hour < WINDOW_END_HH
        cut = now.date() == CUT_DAY
        inside = w is not None and not cut
        criteria.append(
            Criterion(
                "window",
                band and inside,
                f"now {now.isoformat()} — 14:00-20:00Z band={band} "
                f"in-window={inside} (window={None if w is None else w + 1}; "
                f"cut_day={cut}; windows 11-23→12-04 and 12-14→12-18 — "
                "future-ok: scheduled: contract windows)",
                now.isoformat(),
            )
        )

    # -- pacing (days non-decreasing; one family leg per day) ------------------------
    day_errors: list[str] = list(order_errors)
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
        if len(ls) > 1:
            day_errors.append(
                f"{day_iso} hosts family legs {sorted(ls)} — one family per "
                "day (L0's opening and L11's closing may share; no two "
                "family legs do)"
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
                "leg days in order; family legs one-per-day — a leg held in "
                "window 1 runs in window 2 and its sources ship in the "
                "2027-01-15 cadence cut (future-ok: scheduled: contract cut)",
            )
        )

    # -- go (ING-GO-D — the recorded GATE-G6 answer, byte-exact) ----------------------
    go = inputs.get("go")
    if not isinstance(go, dict) or not str(go.get("verbatim") or "").strip():
        criteria.append(
            Criterion(
                "go",
                False,
                "no recorded ING-GO-D answer — the wave is an in-ticket "
                "pause without it (silence is never consent; a re-entry "
                "re-collects the go verbatim)",
            )
        )
    elif go.get("verbatim") != GO_VERBATIM:
        criteria.append(
            Criterion(
                "go",
                False,
                "the recorded go is not the verbatim ING-GO-D answer — GATE "
                "DECISIONS carries it byte-exact ("
                f"{GO_SOURCE}); a paraphrase is a refusal",
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
                    f"ING-GO-D recorded verbatim {recorded.isoformat()} ({GO_SOURCE}; byte-exact)",
                    recorded.isoformat(),
                )
            )

    # -- exclusions (materialize / G2 slot / cut day) ---------------------------------
    materialize = bool(inputs.get("materialize_active"))
    g2 = bool(inputs.get("g2_slot_active"))
    cut = bool(inputs.get("release_cut_active"))
    ex_bad = []
    if materialize:
        ex_bad.append("sig-materialize active")
    if g2:
        ex_bad.append("a G2 step 1–3 slot is active")
    if cut:
        ex_bad.append("a release-cut day is recorded")
    criteria.append(
        Criterion(
            "exclusions",
            not ex_bad,
            (
                f"materialize_active={materialize} g2_slot_active={g2} release_cut_active={cut}"
                if not ex_bad
                else "; ".join(ex_bad)
            ),
        )
    )

    # -- scope (run_set == the leg's declared set, exactly) ----------------------------
    run_set = _source_ids(inputs.get("run_set", []), "run_set")
    never = [s for s in run_set if s in NEVER_SOURCES]
    dossier = [s for s in run_set if s in DOSSIER_SEATS]
    if leg == "L0":
        expected: set[str] = set()
    elif leg == "L11":
        expected = set(BATCHES)
    elif leg in LEG_SCOPE:
        expected = set(LEG_SCOPE[leg]["gated"])
    else:
        expected = set()
        for s in run_set:
            if s not in NEVER_SOURCES:
                never.append(s)
    dup = [s for s in run_set if run_set.count(s) > 1]
    missing_s = sorted(expected - set(run_set))
    extra_s = sorted(set(run_set) - expected)
    if never:
        detail = (
            f"{sorted(set(never))} in run_set — never in Wave D: "
            "doj_ctas_awards stays deferred under D-R11-LATER-09 and the "
            "tribal S8 lane landed at P35.11 (Wave A)"
        )
        if dossier:
            detail += (
                f"; {sorted(set(dossier))} are P37.16a/b Part VIII "
                "dossier-capture seats — their flips and captures ride "
                "those rows' own in-ticket operator go, never this wave's "
                "OP-26 list"
            )
        criteria.append(Criterion("scope", False, detail, never))
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
        gated = set(LEG_SCOPE[leg]["gated"])
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
                criteria.append(
                    Criterion(
                        "flips",
                        True,
                        f"{len(gated)} gated sources recorded flipped + the "
                        "family confirmation present",
                        sorted(executed),
                    )
                )

    # -- serialize (one manual run at a time) -------------------------------------------
    active = inputs.get("active_manual_run") or None
    criteria.append(
        Criterion(
            "serialize",
            active is None,
            f"active_manual_run={active!r} — one manual run at a time, across waves",
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
                    else "the image roll is not recorded on one pinned digest "
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
                    "the three r11-tier2-* batch jobs recorded created --paused"
                    if not bad
                    else f"{bad} not recorded created-paused — "
                    "scheduled-ops.sh --apply --paused creates all three "
                    "before any resume (R6)"
                ),
                bad,
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
                    "dossier-seat context) handed to the operator "
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
    if leg in FAMILY_LEGS:
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
                    "recorded with its reason (incl. a recorded quarantine "
                    "outcome), never silently accepted",
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

    # -- L11: the closing records -----------------------------------------------------------
    if leg == "L11":
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
        enabled = inputs.get("cadence_state_enabled") or {}
        not_enabled = [b for b in BATCHES if enabled.get(b) is not True]
        repub = bool(inputs.get("declaration_republished"))
        next_fires = inputs.get("next_fires") or {}
        fire_bad = [b for b, spec in BATCHES.items() if next_fires.get(b) != spec["next_fire"]]
        closing_bad = []
        if not_enabled:
            closing_bad.append(
                f"cadence rows not enabled: {not_enabled} — the resume flips "
                "each batch's state paused→enabled (the due dispatcher "
                "skips paused rows; P35.1c)"
            )
        if not repub:
            closing_bad.append(
                "declaration_republished not recorded — the cadence "
                "declaration bundle republish lands with the resume"
            )
        if fire_bad:
            closing_bad.append(
                f"next-fire values missing or wrong for {fire_bad} — each "
                "batch's next fire is computed and recorded at resume"
            )
        criteria.append(
            Criterion(
                "resume",
                not closing_bad,
                (
                    "all three tier-2 cadence rows enabled + the declaration "
                    "republished; next-fires recorded "
                    "2026-12-25/26/27T07:37Z (future-ok: scheduled: dom crons) "
                    "— after the 12-15 cut"
                    if not closing_bad
                    else "; ".join(closing_bad)
                ),
                {
                    "not_enabled": not_enabled,
                    "fire_bad": fire_bad,
                    "declaration_republished": repub,
                },
            )
        )


def leg_plan() -> list[dict[str, Any]]:
    """The deterministic Wave-D step plan (``sig.wave-d-plan/1`` content)."""
    steps: list[dict[str, Any]] = []

    def step(leg: str, i: int, kind: str, text: str, **extra: Any) -> None:
        steps.append({"leg": leg, "seq": i, "kind": kind, "step": text, **extra})

    # -- L0 — the wave opening -------------------------------------------------------
    step(
        "L0",
        1,
        "prestate",
        "capture pre-state: per-source job + trigger/dispatcher JSON, "
        "sources.toml sha256, `sig-ops cadence --check` green (OM-14)",
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
        "scheduled-ops.sh --apply --paused — create the three r11-tier2-* "
        "batch jobs paused on the rolled digest (R6)",
        batches=sorted(BATCHES),
        mutation=True,
    )
    step(
        "L0",
        5,
        "handoff",
        f"hand the complete flip list ({len(FLIP_SOURCES)} flag rows + "
        "the eight dossier-seat context rows, "
        "docs/build/reports/WAVE_D_FLIP_LIST.md) to the operator — the "
        "OP-26 execution is recorded, never performed by this row",
        mutation=False,
    )

    # -- L1–L10 — the family days -------------------------------------------------------
    family_names = {
        "L1": "ACQ-19 (P37.47 Tier-2 reuse)",
        "L2": "ACQ-20 (P37.48 aggregate lanes)",
        "L3": "ACQ-21 (P37.49 federal datasets)",
        "L4": "ACQ-22 (P37.50 agenda platforms v2)",
        "L5": "ACQ-23a (P37.69a international open-data)",
        "L6": "ACQ-23b (P37.69b OGC WFS)",
        "L7": "ACQ-24 (P37.51 Puerto Rico)",
        "L8": "ACQ-25 (P37.52 document-list pages)",
        "L9": "ACQ-26 (P37.53 programme-level lane)",
        "L10": "S6 extras (P36.76 Axon Connect · P36.77 DocumentCloud/"
        "MuckRock · P36.78 Sourcewell/OMNIA + RB-06b)",
    }
    for leg in FAMILY_LEGS:
        i = 0
        step(
            leg,
            (i := i + 1),
            "flips",
            f"record the family's OP-26 flips for {leg} "
            f"({family_names[leg]}) — every gated source confirmed "
            "executed before the first run (HG-03 is the operator's); a "
            "leg whose flips are absent stays queued, reported",
            mutation=False,
        )
        for sid in LEG_SCOPE[leg]["gated"]:
            job = EXECUTION_JOB[sid]
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
                "recorded, I8 §7.7 per-source checks (review-status, "
                "shadow diff 0, technology + jurisdiction keyed) — "
                "before the next source starts",
                source=sid,
                mutation=False,
            )
        for sid in LEG_SCOPE[leg]["gated"]:
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
            f"record the {leg} family-day report: run rows, "
            "changed_count, per-source §7.7 verifications, +0 diffs — a "
            "missed leg is reported, never silently skipped",
            mutation=False,
        )

    # -- L11 — closing ----------------------------------------------------------------------
    step(
        "L11",
        1,
        "materialize",
        "run sig-materialize manually — after the last first run, outside ingest runs",
        mutation=True,
    )
    step(
        "L11",
        2,
        "coverage",
        "run the coverage-delta tool (P35.6, I8 §7.7) against the "
        "pre-wave snapshot; record the delta",
        mutation=False,
    )
    step(
        "L11",
        3,
        "resume",
        "resume the three paused tier-2 schedules: each cadence row's "
        "state flips paused→enabled + the declaration bundle republishes "
        "(the due-dispatcher shape — never a per-source trigger resume); "
        "compute + record each batch's next fire "
        "(2026-12-25/26/27T07:37Z — future-ok: scheduled: dom crons)",
        batches=sorted(BATCHES),
        mutation=True,
    )
    step(
        "L11",
        4,
        "record",
        "record the closing report: materialize log, coverage delta, "
        "next-fires, held-leg list — a leg landed in window 2 ships in "
        "the 2027-01-15 cadence cut (future-ok: scheduled: contract cut); "
        "a held leg stays queued and is reported (OM-19)",
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
        prog="sig-ops wave-d-gate",
        description=(
            "P37.54 Wave-D leg gate (sig.wave-d-gate/1): judges a recorded "
            "inputs JSON — refuses the leg (exit 42) unless the verbatim "
            "ING-GO-D answer, the two-window instant, the leg order + "
            "family-day pacing, the declared scope, the OP-26 flip "
            "records, the exclusions, serialisation and the leg's "
            "prerequisites/evidence all hold."
        ),
    )
    ap.add_argument("--inputs", required=True, help="the recorded inputs JSON")
    ap.add_argument("--out", default=None, help="also write the verdict JSON here")
    args = ap.parse_args(argv)

    try:
        inputs = load_inputs(args.inputs)
        verdict = evaluate(inputs)
    except WaveGateError as exc:
        print(f"sig-ops wave-d-gate: REFUSED — {exc}", file=sys.stderr)
        return 2

    record = verdict.to_record()
    text = json.dumps(record, indent=2, sort_keys=True)
    print(text)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(text + "\n")
        print(f"sig-ops wave-d-gate: -> {args.out}", file=sys.stderr)
    if verdict.decision != "go":
        print(
            "sig-ops wave-d-gate: NO-GO — the leg refuses; queued with its "
            "re-run prompt (see record).",
            file=sys.stderr,
        )
        return 42
    return 0


def plan_main(argv: list[str] | None = None) -> int:
    import argparse

    ap = argparse.ArgumentParser(
        prog="sig-ops wave-d-plan",
        description=(
            "P37.54 Wave-D step plan (sig.wave-d-plan/1): the deterministic "
            "ordered steps for L0…L11 — plan-only output, never a mutation."
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
                    "windows": [{"start": w[0], "end": w[1]} for w in WINDOWS],
                    "steps": steps,
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0
    print(
        f"Wave {WAVE} activation plan — windows {WINDOWS[0][0]} → "
        f"{WINDOWS[0][1]} and {WINDOWS[1][0]} → {WINDOWS[1][1]} "
        "(ING-GO-D, one manual run at a time, one family per day)"
    )
    for s in steps:
        mark = " (mutation)" if s.get("mutation") else ""
        op = " [OPERATOR]" if s.get("operator") else ""
        print(f"  {s['leg']}.{s['seq']:>2}  {s['step']}{mark}{op}")
    return 0


__all__ = [
    "BATCHES",
    "CUT_DAY",
    "Criterion",
    "DOSSIER_SEATS",
    "EXECUTION_JOB",
    "FAMILY_LEGS",
    "FLIP_SOURCES",
    "GO_SOURCE",
    "GO_VERBATIM",
    "LEGS",
    "LEG_SCOPE",
    "NEVER_SOURCES",
    "PLAN_SCHEMA",
    "RERUN",
    "SCHEMA",
    "SEATLESS_JOB",
    "SOURCE_BATCH",
    "Verdict",
    "WINDOWS",
    "WaveGateError",
    "evaluate",
    "gate_main",
    "leg_plan",
    "plan_main",
]
