# WAVE_B_FLIP_LIST — the operator-facing Wave-B flip list (P36.12, OP-26)

- **Authority:** ING-GO-B, verbatim (GATE DECISIONS, recorded
  2026-10-15T15:26Z): *"ING-GO-B: go — Wave B legs ACQ-08…ACQ-15 + the
  Flock probe may run inside the 2026-10-26→11-05 window; I execute the
  flips per OP-26"*
- **Window:** 2026-10-26 → 2026-11-05, 14:00–20:00Z (future-ok:
  scheduled: contract window) — one family per day (ACQ-11 + ACQ-15 may
  share); never with the peel-on first fire 10-29T12:00Z, a G2 step 1–3
  slot, an active `sig-materialize`, or a cut day.
- **What a flip is (OP-26, HG-03):** the operator's own act — a signed
  commit or GATE DECISIONS row naming each source id flipped
  `ingestion_permitted=false → true`. Until it lands every row below
  stays `ingestion_permitted=false`. This document is the assembly,
  never the execution — no agent flips a source.
- **How a leg consumes it:** `ops/gcp/wave-b.sh --apply` admits a family
  leg only when the operator's executed flips for that family are
  recorded in the gate inputs (`flips[leg].executed` covers every gated
  source + `flips[leg].confirmed` names the OP-26 record). A leg whose
  flips are absent stays queued and is reported — never silently skipped
  (OM-19). A held leg runs when its flips land, inside the window.
- **Flag-row count:** **96** flagged source rows across nine legs (90
  new Wave-B rows incl. the probe + 6 already-registered `ccops_*`
  rows) + **6 widen targets** riding already-permitted sources (context
  rows — no flag) + **1** target consolidation (`deldot_red_light`)
  riding the flagged `dot_511_de`'s run.
- **The six registered `ccops_*` rows** (berkeley, davis, boston,
  baltimore, nashville, grand_rapids) are already registered from P26.2
  discovery — they carry no batch seat; their Wave-B executions run as
  single-source manual runs on the documents-family job. The P36.10
  contract places them on this flip list explicitly.

## L1 — ACQ-08 family-day (P36.4; batch `r11-layers-01`)

| # | flag row (source id) | host job | notes | flipped | executed-at |
|---|---|---|---|---|---|
| 1 | `dot_511_de` | `sig-ingest-r11-layers-01` | DelDOT layer 26 + consolidated `deldot_red_light` target (P36.6) in the same run | ☐ | |
| 2 | `dot_511_vt` | `sig-ingest-r11-layers-01` | VTrans CCTV rows only (NETWORK_ADDRESS excluded) | ☐ | |
| 3 | `dot_511_wv` | `sig-ingest-r11-layers-01` | WVDOH CCTV group layer (shares the flip with the ACQ-19 placeholder layer) | ☐ | |
| 4 | `dot_511_mi` | `sig-ingest-r11-layers-01` | MDOT layer, stale-snapshot recorded | ☐ | |
| 5 | `dot_511_nc` | `sig-ingest-r11-layers-01` | NCDOT state-origin layer (mirror lineage recorded) | ☐ | |
| 6 | `camreg_ne_lincoln_traffic_cameras` | `sig-ingest-r11-layers-01` | Lincoln NE layer | ☐ | |
| 7 | `camreg_omaha_ne_parks_cameras` | `sig-ingest-r11-layers-01` | Omaha parks layer | ☐ | |
| 8 | `camreg_hyattsville_md_cctv_camera_2024` | `sig-ingest-r11-layers-01` | Hyattsville CCTV 2024 | ☐ | |

Context (no flag — rides existing GL-GATE-07 flips; single-source manual
executions on the existing jobs so the next scheduled fire is a `+0`):

| widen target | host source / job | leg notes |
|---|---|---|
| `police_halo_cameras_denver_police_department` | `camreg_denver_co` on `sig-ingest-camreg-batch-02` | Denver HALO — same publisher/licence as the flipped ALPR layer |
| `seattle_police_department_cctv_pilot_areas` | `camreg_seattle_wa` on `sig-ingest-camreg-batch-06` | SPD CCTV pilot areas — same ArcGIS org as the flipped SDOT layers |
| `deldot_red_light` | `dot_511_de` (flagged above) | P36.6 consolidation — rides the `dot_511_de` flip in the same run |

## L2 — ACQ-09 family-day (P36.5; batch `r11-layers-02`)

| # | flag row | host job | notes | flipped | executed-at |
|---|---|---|---|---|---|
| 9 | `camreg_fdot_flock` | `sig-ingest-r11-layers-02` | FDOT consolidated — inventory + removal-status in one run (I8 §5.2) | ☐ | |
| 10 | `camreg_pueblo_co_flock` | `sig-ingest-r11-layers-02` | | ☐ | |
| 11 | `camreg_rocky_mount_nc_lpr_cameras` | `sig-ingest-r11-layers-02` | | ☐ | |
| 12 | `camreg_shelbyville_tn_flock_cameras` | `sig-ingest-r11-layers-02` | | ☐ | |
| 13 | `camreg_temecula_ca_flock_wfl1` | `sig-ingest-r11-layers-02` | | ☐ | |
| 14 | `camreg_marble_falls_tx_flock_locations` | `sig-ingest-r11-layers-02` | | ☐ | |
| 15 | `camreg_va_prince_william_county` | `sig-ingest-r11-layers-02` | | ☐ | |
| 16 | `camreg_milford_ct_flocklprcam` | `sig-ingest-r11-layers-02` | | ☐ | |
| 17 | `camreg_elgin_il_lpr_cameras` | `sig-ingest-r11-layers-02` | | ☐ | |
| 18 | `camreg_south_fulton_ga_lpr_cameras` | `sig-ingest-r11-layers-02` | | ☐ | |
| 19 | `camreg_va_pittsylvania_county_stationary` | `sig-ingest-r11-layers-02` | | ☐ | |
| 20 | `camreg_alabaster_al_lpr_cameras` | `sig-ingest-r11-layers-02` | | ☐ | |
| 21 | `camreg_thomasville_ga_flock_location` | `sig-ingest-r11-layers-02` | | ☐ | |
| 22 | `camreg_leon_county_fl_overwatch_viewer` | `sig-ingest-r11-layers-02` | | ☐ | |
| 23 | `camreg_ga_peachtree_corners_flock_camera` | `sig-ingest-r11-layers-02` | | ☐ | |

## L3 — ACQ-10 family-day (P36.6; batch `r11-ate-01`)

`enforcement_count` must be registered in hosted `vocab_*` (the L0
`vocab_enforcement_count` step) **before** this leg's first emit —
P35.14a's closed sink quarantines an unregistered predicate.

| # | flag row | host job | notes | flipped | executed-at |
|---|---|---|---|---|---|
| 24 | `camreg_dc_ddot_ate` | `sig-ingest-r11-ate-01` | DC ASC sites + violations-by-month — the licence-mismatch FALLBACK (`dot_511_dc` widen failed: CC-BY-4.0 items vs CC0-1.0 row) | ☐ | |
| 25 | `camreg_montgomery_md_ate` | `sig-ingest-r11-ate-01` | three targets in one run (2 site×quarter aggregates + 2024 site layer) | ☐ | |
| 26 | `camreg_nyc_mta_bus_lane_ate` | `sig-ingest-r11-ate-01` | | ☐ | |
| 27 | `camreg_tacoma_wa_ate` | `sig-ingest-r11-ate-01` | | ☐ | |
| 28 | `camreg_howard_md_school_zone_ate` | `sig-ingest-r11-ate-01` | | ☐ | |
| 29 | `camreg_lakeland_fl_red_light` | `sig-ingest-r11-ate-01` | | ☐ | |
| 30 | `camreg_suffolk_ny_red_light` | `sig-ingest-r11-ate-01` | | ☐ | |
| 31 | `camreg_medford_or_ate` | `sig-ingest-r11-ate-01` | | ☐ | |
| 32 | `camreg_ctdot_speed_safety` | `sig-ingest-r11-ate-01` | | ☐ | |

Context (no flag — rides the existing `camreg_chicago_il` flip on
`sig-ingest-camreg-batch-02`; ≈73k-claim first run, the wave's largest):

| widen target | host source / job | leg notes |
|---|---|---|
| `chicago_speed_violations_monthly` | `camreg_chicago_il` on `sig-ingest-camreg-batch-02` | aggregate camera×month only — `address` is a denied field (F-330) |
| `chicago_redlight_violations_monthly` | `camreg_chicago_il` on `sig-ingest-camreg-batch-02` | aggregate camera×month only — same denied-field posture |

## L4 — ACQ-11 family-day (P36.7; batch `r11-procurement-01`)

| # | flag row | host job | notes | flipped | executed-at |
|---|---|---|---|---|---|
| 33 | `procportal_cook_il_awards` | `sig-ingest-r11-procurement-01` | Cook County awards | ☐ | |
| 34 | `procportal_wa_des_contract_sales` | `sig-ingest-r11-procurement-01` | WA DES contract sales — public-entity customers only | ☐ | |
| 35 | `camreg_dc_ovsjg_camera_rebate` | `sig-ingest-r11-procurement-01` | DC OVSJG rebate counts — programme-level PSA×MONTH_YEAR aggregates only | ☐ | |

## L5 — ACQ-12 family-day (P36.8; batch `r11-disclosures-01`)

| # | flag row | host job | notes | flipped | executed-at |
|---|---|---|---|---|---|
| 36 | `statrep_mn_bca` | `sig-ingest-r11-disclosures-01` | MN BCA (carries the MN UAV family) | ☐ | |
| 37 | `statrep_va_rga` | `sig-ingest-r11-disclosures-01` | VA RGA | ☐ | |
| 38 | `statrep_wa_ago_alpr_registry` | `sig-ingest-r11-disclosures-01` | WA AGO registry — feeds `sharing_partner` edges at L10 | ☐ | |
| 39 | `statrep_va_vsp_alpr` | `sig-ingest-r11-disclosures-01` | VA VSP | ☐ | |
| 40 | `statrep_va_vscc_alpr` | `sig-ingest-r11-disclosures-01` | VA VSCC | ☐ | |
| 41 | `statrep_ne_crime_commission_alpr` | `sig-ingest-r11-disclosures-01` | NE Crime Commission | ☐ | |
| 42 | `statrep_vt_dps_alpr` | `sig-ingest-r11-disclosures-01` | VT DPS | ☐ | |
| 43 | `statrep_md_dls_mandated_reports` | `sig-ingest-r11-disclosures-01` | MD DLS mandated reports | ☐ | |
| 44 | `statrep_il_isp_alpr` | `sig-ingest-r11-disclosures-01` | IL ISP | ☐ | |
| 45 | `statrep_austin_tx_auditor` | `sig-ingest-r11-disclosures-01` | Austin auditor | ☐ | |

## L6 — ACQ-13a+13b family-day (P36.9a+P36.9b; batch `r11-disclosures-02`)

| # | flag row | host job | notes | flipped | executed-at |
|---|---|---|---|---|---|
| 46 | `statrep_me_dps_uav` | `sig-ingest-r11-disclosures-02` | | ☐ | |
| 47 | `statrep_hi_judiciary_interception` | `sig-ingest-r11-disclosures-02` | | ☐ | |
| 48 | `statrep_wa_watech_frt` | `sig-ingest-r11-disclosures-02` | | ☐ | |
| 49 | `statrep_co_frt_accountability` | `sig-ingest-r11-disclosures-02` | (absorbs the Arvada FRT candidate) | ☐ | |
| 50 | `statrep_de_diac` | `sig-ingest-r11-disclosures-02` | | ☐ | |
| 51 | `statrep_wa_wtsc_ate` | `sig-ingest-r11-disclosures-02` | (absorbs the WA ATS index) | ☐ | |
| 52 | `statrep_detroit_mi_frt_weekly` | `sig-ingest-r11-disclosures-02` | | ☐ | |
| 53 | `statrep_us_dhs_privacy_compliance` | `sig-ingest-r11-disclosures-02` | (five consolidated DHS targets) | ☐ | |
| 54 | `statrep_fl_flhsmv_red_light` | `sig-ingest-r11-disclosures-02` | | ☐ | |
| 55 | `statrep_pa_wzssc` | `sig-ingest-r11-disclosures-02` | | ☐ | |
| 56 | `statrep_md_msp_css` | `sig-ingest-r11-disclosures-02` | | ☐ | |
| 57 | `statrep_mn_court_interception` | `sig-ingest-r11-disclosures-02` | | ☐ | |
| 58 | `legis_us_dhs_sorn_plate_data` | `sig-ingest-r11-disclosures-02` | SORN — index_only/legislative posture | ☐ | |
| 59 | `statrep_seattle_wa_sdot_ate` | `sig-ingest-r11-disclosures-02` | | ☐ | |
| 60 | `statrep_il_icjia_drone` | `sig-ingest-r11-disclosures-02` | | ☐ | |
| 61 | `statrep_seattle_wa_oig` | `sig-ingest-r11-disclosures-02` | | ☐ | |

## L7 — ACQ-14 family-day (P36.10; batch `r11-documents-01` + six registered rows)

| # | flag row | host job | notes | flipped | executed-at |
|---|---|---|---|---|---|
| 62 | `ccops_columbia_mo` | `sig-ingest-r11-documents-01` | new CCOPS row | ☐ | |
| 63 | `ccops_st_louis_mo` | `sig-ingest-r11-documents-01` | new CCOPS row | ☐ | |
| 64 | `ccops_dayton_oh` | `sig-ingest-r11-documents-01` | new CCOPS row | ☐ | |
| 65 | `ccops_anchorage_ak` | `sig-ingest-r11-documents-01` | new CCOPS row | ☐ | |
| 66 | `ccops_austin_tx` | `sig-ingest-r11-documents-01` | new CCOPS row | ☐ | |
| 67 | `policy_orange_county_ca_sheriff` | `sig-ingest-r11-documents-01` | agency-policy seat | ☐ | |
| 68 | `policy_pasadena_ca_pd` | `sig-ingest-r11-documents-01` | agency-policy seat | ☐ | |
| 69 | `policy_st_cloud_mn_isd742` | `sig-ingest-r11-documents-01` | district self-disclosure | ☐ | |
| 70 | `policy_onslow_nc_schools` | `sig-ingest-r11-documents-01` | district self-disclosure | ☐ | |
| 71 | `policy_pflugerville_tx_isd` | `sig-ingest-r11-documents-01` | district self-disclosure | ☐ | |
| 72 | `policy_whitesboro_ny_csd` | `sig-ingest-r11-documents-01` | district self-disclosure | ☐ | |
| 73 | `policy_bangor_me_pd` | `sig-ingest-r11-documents-01` | agency-policy seat | ☐ | |
| 74 | `policy_houston_tx_hpd` | `sig-ingest-r11-documents-01` | agency-policy seat | ☐ | |
| 75 | `policy_albuquerque_nm_apd` | `sig-ingest-r11-documents-01` | agency-policy seat | ☐ | |
| 76 | `policy_little_rock_ar_pd` | `sig-ingest-r11-documents-01` | agency-policy seat | ☐ | |
| 77 | `legis_ca_gov_code_53166` | `sig-ingest-r11-documents-01` | agency-policy seat (statute) | ☐ | |
| 78 | `ccops_berkeley` | `sig-ingest-r11-documents-01` | **already registered** (P26.2); single-source on the family job | ☐ | |
| 79 | `ccops_davis` | `sig-ingest-r11-documents-01` | already registered; host 403 posture recorded — a challenge is a recorded refusal, never a defeat attempt | ☐ | |
| 80 | `ccops_boston` | `sig-ingest-r11-documents-01` | already registered | ☐ | |
| 81 | `ccops_baltimore` | `sig-ingest-r11-documents-01` | already registered | ☐ | |
| 82 | `ccops_nashville` | `sig-ingest-r11-documents-01` | already registered | ☐ | |
| 83 | `ccops_grand_rapids` | `sig-ingest-r11-documents-01` | already registered | ☐ | |

## L8 — ACQ-15 family-day (P36.11; batch `r11-documents-01`)

| # | flag row | host job | notes | flipped | executed-at |
|---|---|---|---|---|---|
| 84 | `agenda_haskell_ar_council` | `sig-ingest-r11-documents-01` | | ☐ | |
| 85 | `agenda_des_moines_ia_council` | `sig-ingest-r11-documents-01` | | ☐ | |
| 86 | `agenda_jasper_sc_council` | `sig-ingest-r11-documents-01` | | ☐ | |
| 87 | `grant_al_adeca_psn` | `sig-ingest-r11-documents-01` | | ☐ | |
| 88 | `grant_ca_bscc_ort` | `sig-ingest-r11-documents-01` | | ☐ | |
| 89 | `grant_fl_senate_lfir` | `sig-ingest-r11-documents-01` | | ☐ | |
| 90 | `grant_nj_oag_bwc` | `sig-ingest-r11-documents-01` | | ☐ | |
| 91 | `grant_ok_dac_jag_lle` | `sig-ingest-r11-documents-01` | | ☐ | |
| 92 | `grant_tx_txdmv_mvcpa` | `sig-ingest-r11-documents-01` | | ☐ | |
| 93 | `legis_gu_governor` | `sig-ingest-r11-documents-01` | Guam legislation page | ☐ | |
| 94 | `procportal_davie_fl_purchasing` | `sig-ingest-r11-documents-01` | | ☐ | |
| 95 | `procportal_forsyth_nc_purchasing` | `sig-ingest-r11-documents-01` | | ☐ | |

Context (no flag — rides the existing `openstates` flip on
`sig-ingest-openstates`; the next scheduled fire is then a `+0`):

| widen target | host source / job | leg notes |
|---|---|---|
| `az_hb2574_2024` | `openstates` on `sig-ingest-openstates` | pinned bill query (P36.11 reviewed) |
| `ny_s7037_2025_2026` | `openstates` on `sig-ingest-openstates` | pinned bill query (P36.11 reviewed) |

## L9 — Flock transparency-portal probe (P36.74, WV-10)

| # | flag row | host job | notes | flipped | executed-at |
|---|---|---|---|---|---|
| 96 | `flock_transparency_portals` | `sig-ingest-r11-documents-01` | the probe row — WV-10/ADR-188 probe-only posture; one polite GET per committed portal (917, snapshot 2026-09-23T10:15:16.751Z), stop-and-record on any challenge; `sig.probe-run/1` records every outcome | ☐ | |

## Never in Wave B

- `doj_ctas_awards` (AP-T2-093 — not tribal) stays deferred under
  `D-R11-LATER-09`; the gate refuses it in any run set.
- `camreg_tribal_all_leaders_directory` + `legis_tribal_tohono_oodham_notice`
  — the ADR-185 S8 screened lane landed at P35.11 (Wave A); Wave B
  exercises no tribal lane (`AP-T2-093` is the only tribal-adjacent
  candidate and it is deferred, not tribal).
- Any source not on this list — the gate refuses an undeclared run set.

## Deferrals recorded at hand-off (owed, unmet — ADR-171)

- `D-R11-LATER-04` — the Stage-0 outreach set
  (`SIG-CHART-033`, `SIG-INGEST-029`, `SIG-INGEST-030a`,
  `SIG-CONTRIB-012`, `SIG-CONTRIB-012a`, `SIG-CONTRIB-013`,
  `SIG-GOV-024`) stays **owed and unmet at launch** (trigger: "the
  operator authorises outside contact"); no outside contact is made by
  the wave — probing a published endpoint is a fetch, never contact.
- `D-R11-LATER-09` — Tier-2/later acquisition incl. `doj_ctas_awards`.
- `D-R11-OSMUID-1` — handed to P37.1; no OSM connector change here.
