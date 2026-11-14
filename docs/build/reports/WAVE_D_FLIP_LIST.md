# WAVE_D_FLIP_LIST — the operator-facing Wave-D flip list (P37.54, OP-26)

- **Authority:** ING-GO-D, verbatim (GATE-G6 GATE DECISIONS, recorded
  2026-11-05T15:20Z, operator-signed commit `b91f8e58`): the §3 line
  answered "Approve ING-GO-D + flip list (rec.)" — the wave's legs run
  in their windows under each row's own preconditions, and the §3
  Wave-D HG-03 flip-list line pre-approves the plan-cell's verbatim
  set (N1–N21, ACQ-23a/b, DocumentCloud, Sourcewell/OMNIA, Axon
  Connect, RB-06b, RB-08) for flip when its rights review completes
  — the flips themselves stay operator-executed; ids resolving
  non-clear licences keep their per-source gate.
- **Windows:** `window 11-23 -> 12-04` then `window 12-14 -> 12-18`,
  14:00–20:00Z UTC each day (future-ok: scheduled: contract
  windows) — one family per day; L0 opens and L11 closes and may
  share a day with a family leg; a leg held in the first window
  runs in the second (OM-19 — reported, never silently skipped)
  and its sources ship in the 2027-01-15 cadence cut, never the
  12-15 cut (the 12-15 cut day inside the second window carries
  no leg). Never inside the AR-3 freeze 12-06→12-13, the daily
  03:00–06:30Z band, a cut day, an active `sig-materialize` or a
  G2 slot.
- **What a flip is (OP-26, HG-03):** the operator's own act — a signed
  commit or GATE DECISIONS row naming each source id flipped
  `ingestion_permitted=false → true`. Until it lands every row below
  stays `ingestion_permitted=false`. This document is the assembly,
  never the execution — no agent flips a source.
- **How a leg consumes it:** `ops/gcp/wave-d.sh --apply` admits a
  family leg only when the operator's executed flips for that
  family are recorded in the gate inputs (`flips[leg].executed`
  covers every gated source + `flips[leg].confirmed` names the
  OP-26 record). A leg whose flips are absent stays queued and is
  reported — never silently skipped (OM-19).
- **Flag-row count:** **146** flagged source rows across ten
  family legs (140 tier-2 batch members + 6 seatless gated sources)
  + **8 context rows** (the P37.16a/b Part VIII dossier-capture
  seats — batch members whose flips ride those rows' own gating,
  never this wave's).

## Recorded caveats (read before executing)

- **`payee:` stays unmapped** — P37.53's run ledger records that
  P37.48's `payee:` prefix was never registered in
  `subject_entity_types.toml`; the ACQ-20 payment lanes' `payee:`
  subjects quarantine `unknown_subject_scheme` fail-closed on a
  live emit — a recorded outcome, never a defect; the typing
  decision is that family's, never guessed by this row.
- **Enumerated seats** — D-P37.69a-1/-2 and D-P37.69b-1 name seats
  held `[[enumerated]]` pending endpoint preflights; D-P37.69b-1's
  owner names this wave's flip-window census under ING-GO-D — the
  seats sit in the flag rows below; an enumerated seat's run is a
  recorded bounded outcome, never a fetch of an unevidenced
  endpoint.
- **Ipswich (`camreg_gb_eng_ipswich_cctv_camera`)** stays enumerated
  (WMS-only evidence; `endpoint_preflight_deferred`) — its flip
  rides the same OP-26 line; the connector holds no wired WFS
  target for it, so its run records the seat's posture.

## L1 — ACQ-19 family-day (P37.47 — Tier-2 reuse wave)

| # | flag row (source id) | host job | flipped | executed-at |
|---|---|---|---|---|
| 1 | `camreg_ca_monterey_park_flock_camera` | `sig-ingest-r11-tier2-01` | ☐ | |
| 2 | `camreg_fl_broward_county_us_palm_beach` | `sig-ingest-r11-tier2-01` | ☐ | |
| 3 | `camreg_jeffersonville_in_flock` | `sig-ingest-r11-tier2-01` | ☐ | |
| 4 | `camreg_nv_las_vegas_us_clark_county` | `sig-ingest-r11-tier2-01` | ☐ | |
| 5 | `camreg_santa_fe_nm_park_cameras` | `sig-ingest-r11-tier2-01` | ☐ | |
| 6 | `ccops_berkeley` | `sig-ingest-r11-tier2-03` | ☐ | |
| 7 | `ccops_boston` | `sig-ingest-r11-tier2-03` | ☐ | |
| 8 | `ccops_hi_honolulu_police_department` | `sig-ingest-r11-tier2-02` | ☐ | |
| 9 | `ccops_il_chicago_oig_shotspotter` | `sig-ingest-r11-tier2-03` | ☐ | |
| 10 | `ccops_mi_wayne_county_commission` | `sig-ingest-r11-tier2-02` | ☐ | |
| 11 | `ccops_mo_st_louis_fy21_spi_shotspotter` | `sig-ingest-r11-tier2-03` | ☐ | |
| 12 | `ccops_nc_charlotte_mecklenburg_police` | `sig-ingest-r11-tier2-03` | ☐ | |
| 13 | `ccops_nc_elizabeth_city_police` | `sig-ingest-r11-tier2-03` | ☐ | |
| 14 | `ccops_ny_new_york_nyc_comptroller` | `sig-ingest-r11-tier2-03` | ☐ | |
| 15 | `ccops_san_francisco_bay_ca` | `sig-ingest-r11-tier2-03` | ☐ | |
| 16 | `ccops_san_jose_ca` | `sig-ingest-r11-tier2-03` | ☐ | |
| 17 | `ccops_santa_clara_county_ca` | `sig-ingest-r11-tier2-03` | ☐ | |
| 18 | `dhs_fusion_centers` | `sig-ingest-r11-tier2-01` | ☐ | |
| 19 | `dot_511_id` | `sig-ingest-r11-tier2-02` | ☐ | |
| 20 | `dot_511_nm` | `sig-ingest-r11-tier2-01` | ☐ | |
| 21 | `dot_511_nv` | `sig-ingest-r11-tier2-02` | ☐ | |
| 22 | `grant_ok_safe_oklahoma_grant` | `sig-ingest-r11-tier2-03` | ☐ | |
| 23 | `grant_us_doj_cops_technology` | `sig-ingest-r11-tier2-03` | ☐ | |
| 24 | `legis_vi_legislature_virgin_islands` | `sig-ingest-r11-tier2-02` | ☐ | |
| 25 | `policy_anaheim_ca_pd_policy_manual` | `sig-ingest-r11-tier2-03` | ☐ | |
| 26 | `policy_maricopa_county_az_mcso_policies` | `sig-ingest-r11-tier2-03` | ☐ | |
| 27 | `policy_norman_ok_alpr_policy_amendment` | `sig-ingest-r11-tier2-03` | ☐ | |
| 28 | `statrep_new_york_ny_nyc_doi_oig` | `sig-ingest-r11-tier2-03` | ☐ | |
| 29 | `statrep_tx_ca_nm_ri_fl_il_eff_red_flag` | `sig-ingest-r11-tier2-03` | ☐ | |
| 30 | `statrep_us_upturn_mass_extraction_2020` | `sig-ingest-r11-tier2-03` | ☐ | |

## L2 — ACQ-20 family-day (P37.48 — aggregate lanes)

| # | flag row (source id) | host job | flipped | executed-at |
|---|---|---|---|---|
| 31 | `camreg_az_mesa_city_of_expenditures` | `sig-ingest-r11-tier2-01` | ☐ | |
| 32 | `camreg_de_delaware_checkbook_expenditure` | `sig-ingest-r11-tier2-01` | ☐ | |
| 33 | `camreg_il_chicago_payments` | `sig-ingest-r11-tier2-03` | ☐ | |
| 34 | `camreg_il_chicago_violence_reduction` | `sig-ingest-r11-tier2-03` | ☐ | |
| 35 | `camreg_mi_detroit_dpd_shotspotter` | `sig-ingest-r11-tier2-01` | ☐ | |
| 36 | `camreg_nj_new_jersey_yourmoney` | `sig-ingest-r11-tier2-01` | ☐ | |
| 37 | `camreg_oakland_ca_shotspotter_2013_2015` | `sig-ingest-r11-tier2-02` | ☐ | |
| 38 | `camreg_us_ate_camera_location_and_per` | `sig-ingest-r11-tier2-02` | ☐ | |
| 39 | `camreg_us_body_worn_camera` | `sig-ingest-r11-tier2-02` | ☐ | |
| 40 | `camreg_us_municipal_contract_expenditure` | `sig-ingest-r11-tier2-01` | ☐ | |
| 41 | `camreg_us_socrata_hosted_vendor` | `sig-ingest-r11-tier2-01` | ☐ | |
| 42 | `camreg_wa_washington_state_open` | `sig-ingest-r11-tier2-01` | ☐ | |
| 43 | `procportal_tx_texas_dir_cooperative` | `sig-ingest-r11-tier2-01` | ☐ | |

## L3 — ACQ-21 family-day (P37.49 — federal datasets)

| # | flag row (source id) | host job | flipped | executed-at |
|---|---|---|---|---|
| 44 | `camreg_us_nces_school_survey_on_crime` | `sig-ingest-r11-tier2-01` | ☐ | |
| 45 | `legis_us_federal_register_api` | `sig-ingest-r11-tier2-01` | ☐ | |
| 46 | `statrep_tx_south_padre_island_faa` | `sig-ingest-r11-tier2-02` | ☐ | |
| 47 | `statrep_us_2024_federal_agency` | `sig-ingest-r11-tier2-01` | ☐ | |
| 48 | `statrep_us_dhs_ai_use` | `sig-ingest-r11-tier2-01` | ☐ | |
| 49 | `statrep_us_ice_287_monthly` | `sig-ingest-r11-tier2-03` | ☐ | |
| 50 | `statrep_us_ice_287_participating` | `sig-ingest-r11-tier2-01` | ☐ | |
| 51 | `statrep_us_wiretap_summary_tables` | `sig-ingest-r11-tier2-01` | ☐ | |

## L4 — ACQ-22 family-day (P37.50 — agenda platforms v2)

| # | flag row (source id) | host job | flipped | executed-at |
|---|---|---|---|---|
| 52 | `agenda_az_maricopa_county_board_of` | `sig-ingest-r11-tier2-03` | ☐ | |
| 53 | `agenda_bexar_county_tx_agenda_center` | `sig-ingest-r11-tier2-03` | ☐ | |
| 54 | `agenda_durham_nc_agenda_center` | `sig-ingest-r11-tier2-01` | ☐ | |
| 55 | `agenda_frisco_tx_onbase_agenda_online` | `sig-ingest-r11-tier2-01` | ☐ | |
| 56 | `agenda_hialeah_fl_agenda_center` | `sig-ingest-r11-tier2-01` | ☐ | |
| 57 | `agenda_jersey_city_nj_digital_agenda` | `sig-ingest-r11-tier2-01` | ☐ | |
| 58 | `agenda_nd_fargo_city_commission_agendas` | `sig-ingest-r11-tier2-01` | ☐ | |
| 59 | `agenda_savannah_ga_2023_05_25` | `sig-ingest-r11-tier2-01` | ☐ | |
| 60 | `agenda_tampa_fl_onbase_agenda_online` | `sig-ingest-r11-tier2-01` | ☐ | |
| 61 | `agenda_tx_dallas_county_commissioners` | `sig-ingest-r11-tier2-03` | ☐ | |

## L5 — ACQ-23a family-day (P37.69a — international open-data portals/files; the N1–N21 set)

| # | flag row (source id) | host job | flipped | executed-at |
|---|---|---|---|---|
| 62 | `camreg_au_ckan_package_search` | `sig-ingest-r11-tier2-02` | ☐ | |
| 63 | `camreg_au_nsw_sydney_street_safety` | `sig-ingest-r11-tier2-02` | ☐ | |
| 64 | `camreg_au_qld_towns_cctv_camera_register` | `sig-ingest-r11-tier2-02` | ☐ | |
| 65 | `camreg_au_tas_emergency_closed_circuit` | `sig-ingest-r11-tier2-02` | ☐ | |
| 66 | `camreg_au_tas_hobar_security_camera` | `sig-ingest-r11-tier2-02` | ☐ | |
| 67 | `camreg_au_vic_ballarat_cctv_cameras` | `sig-ingest-r11-tier2-02` | ☐ | |
| 68 | `camreg_au_vic_geelong_closed_circuit` | `sig-ingest-r11-tier2-02` | ☐ | |
| 69 | `camreg_au_wa_perth_security_cameras` | `sig-ingest-r11-tier2-02` | ☐ | |
| 70 | `camreg_es_md_madrid_c_maras_de` | `sig-ingest-r11-tier2-03` | ☐ | |
| 71 | `camreg_eu_eea_data_europa_search_api` | `sig-ingest-r11-tier2-02` | ☐ | |
| 72 | `camreg_fr_92_grand_paris_seine_ouest_vid` | `sig-ingest-r11-tier2-03` | ☐ | |
| 73 | `camreg_gb_eng_barnet_cctv_camera` | `sig-ingest-r11-tier2-02` | ☐ | |
| 74 | `camreg_gb_eng_barnet_cctv_traffic` | `sig-ingest-r11-tier2-02` | ☐ | |
| 75 | `camreg_gb_eng_brist_cctv_cameras` | `sig-ingest-r11-tier2-02` | ☐ | |
| 76 | `camreg_gb_eng_leice_cctv_cameras` | `sig-ingest-r11-tier2-02` | ☐ | |
| 77 | `camreg_gb_eng_mansf_cctv_cameras` | `sig-ingest-r11-tier2-02` | ☐ | |
| 78 | `camreg_gb_eng_north_cctv_cameras` | `sig-ingest-r11-tier2-02` | ☐ | |
| 79 | `camreg_gb_eng_traff_trafford_cctv` | `sig-ingest-r11-tier2-02` | ☐ | |
| 80 | `camreg_gb_sct_edinburgh_public_cctv` | `sig-ingest-r11-tier2-02` | ☐ | |
| 81 | `camreg_ie_d_dublin_traffic_poles_with` | `sig-ingest-r11-tier2-02` | ☐ | |
| 82 | `camreg_it_me_messina_videosorveglianza` | `sig-ingest-r11-tier2-03` | ☐ | |
| 83 | `camreg_pt_11_lisboa_sistema_de` | `sig-ingest-r11-tier2-03` | ☐ | |
| 84 | `camreg_si_048_ko_evje_videonadzor_na` | `sig-ingest-r11-tier2-03` | ☐ | |
| 85 | `camreg_ua_18_korosten` | `sig-ingest-r11-tier2-03` | ☐ | |
| 86 | `ccops_gb_eng_barnet_traffic_cctv` | `sig-ingest-r11-tier2-01` | ☐ | |
| 87 | `ccops_iso_au_privacy_commissioner` | `sig-ingest-r11-tier2-02` | ☐ | |
| 88 | `ccops_it_tn_trento_provvedimento_dell_11` | `sig-ingest-r11-tier2-03` | ☐ | |
| 89 | `ccops_si_085_novo_mesto_evidenca_o` | `sig-ingest-r11-tier2-03` | ☐ | |
| 90 | `dot_511_gb` | `sig-ingest-r11-tier2-02` | ☐ | |
| 91 | `legis_ie_rs_general_scheme` | `sig-ingest-r11-tier2-03` | ☐ | |
| 92 | `statrep_ca_special_parliament_use` | `sig-ingest-r11-tier2-02` | ☐ | |
| 93 | `statrep_fr_cnil_utilisation_de` | `sig-ingest-r11-tier2-02` | ☐ | |
| 94 | `statrep_gb_enforcement_action` | `sig-ingest-r11-tier2-02` | ☐ | |
| 95 | `statrep_gb_eng_seven_cctv_june_2026` | `sig-ingest-r11-tier2-03` | ☐ | |
| 96 | `statrep_gb_sct_joint_assurance_review` | `sig-ingest-r11-tier2-03` | ☐ | |
| 97 | `statrep_gb_uk_algorithmic_transparency` | `sig-ingest-r11-tier2-03` | ☐ | |

## L6 — ACQ-23b family-day (P37.69b — OGC WFS)

| # | flag row (source id) | host job | flipped | executed-at |
|---|---|---|---|---|
| 98 | `camreg_gb_eng_ipswich_cctv_camera` | `sig-ingest-r11-tier2-03` | ☐ | |
| 99 | `camreg_gb_eng_runny_cctv_cameras` | `sig-ingest-r11-tier2-03` | ☐ | |
| 100 | `camreg_gb_eng_south_skdc_cctv` | `sig-ingest-r11-tier2-03` | ☐ | |
| 101 | `camreg_gb_sct_clackmannanshire_cctv` | `sig-ingest-r11-tier2-03` | ☐ | |

## L7 — ACQ-24 family-day (P37.51 — Puerto Rico SUTRA/OCPR; the RB-08 set)

| # | flag row (source id) | host job | flipped | executed-at |
|---|---|---|---|---|
| 102 | `legis_pr_pc0489_ley_del` | `sig-ingest-r11-tier2-02` | ☐ | |
| 103 | `legis_pr_pc0560_plan_de` | `sig-ingest-r11-tier2-02` | ☐ | |
| 104 | `legis_pr_rc0740_investigaci_sobre` | `sig-ingest-r11-tier2-02` | ☐ | |
| 105 | `legis_pr_rc0787_resoluci_de` | `sig-ingest-r11-tier2-02` | ☐ | |
| 106 | `legis_pr_rcs0198_resoluci_conjunta` | `sig-ingest-r11-tier2-02` | ☐ | |
| 107 | `legis_pr_rs0604_resoluci_del` | `sig-ingest-r11-tier2-02` | ☐ | |
| 108 | `legis_pr_sistema_nico_de` | `sig-ingest-r11-tier2-02` | ☐ | |
| 109 | `procportal_pr_consulta_del_registro` | `sig-ingest-r11-tier2-01` | ☐ | |

## L8 — ACQ-25 family-day (P37.52 — document-list pages)

| # | flag row (source id) | host job | flipped | executed-at |
|---|---|---|---|---|
| 110 | `camreg_ma_massachusetts_capital` | `sig-ingest-r11-tier2-01` | ☐ | |
| 111 | `grant_il_illinois_gata_csfa` | `sig-ingest-r11-tier2-02` | ☐ | |
| 112 | `grant_ma_massachusetts_law_enforcement` | `sig-ingest-r11-tier2-02` | ☐ | |
| 113 | `grant_oh_ohio_criminal_justice` | `sig-ingest-r11-tier2-02` | ☐ | |
| 114 | `procportal_fl_florida_buy_cooperative` | `sig-ingest-r11-tier2-01` | ☐ | |
| 115 | `procportal_ny_northeastern_regional` | `sig-ingest-r11-tier2-01` | ☐ | |
| 116 | `procportal_us_naspo_valuepoint_portfolio` | `sig-ingest-r11-tier2-01` | ☐ | |
| 117 | `procportal_wa_wsipc_rfp_24` | `sig-ingest-r11-tier2-01` | ☐ | |

## L9 — ACQ-26 family-day (P37.53 — programme-level lane)

| # | flag row (source id) | host job | flipped | executed-at |
|---|---|---|---|---|
| 118 | `agenda_us_agency_fusus_real` | `sig-ingest-r11-tier2-02` | ☐ | |
| 119 | `camreg_bloomington_il_drone_flights` | `sig-ingest-r11-tier2-02` | ☐ | |
| 120 | `camreg_detroit_mi_project_green_light` | `sig-ingest-r11-tier2-01` | ☐ | |
| 121 | `camreg_ga_brookhaven_flock_camera` | `sig-ingest-r11-tier2-01` | ☐ | |
| 122 | `camreg_ga_flock_cameras_asof` | `sig-ingest-r11-tier2-01` | ☐ | |
| 123 | `camreg_ga_savannah_flock_camera` | `sig-ingest-r11-tier2-01` | ☐ | |
| 124 | `camreg_gastonia_nc_flock_condor_cameras` | `sig-ingest-r11-tier2-01` | ☐ | |
| 125 | `camreg_la_east_baton_rouge_parish_flock` | `sig-ingest-r11-tier2-01` | ☐ | |
| 126 | `camreg_la_new_orleans_eye_on` | `sig-ingest-r11-tier2-03` | ☐ | |
| 127 | `camreg_medford_or_drone_deployments_fs` | `sig-ingest-r11-tier2-02` | ☐ | |
| 128 | `camreg_peoria_il_drone_usage` | `sig-ingest-r11-tier2-02` | ☐ | |
| 129 | `camreg_us_agency_drone_flight` | `sig-ingest-r11-tier2-02` | ☐ | |
| 130 | `camreg_us_agency_published_flock` | `sig-ingest-r11-tier2-02` | ☐ | |
| 131 | `ccops_ca_calistoga_police_department` | `sig-ingest-r11-tier2-03` | ☐ | |
| 132 | `ccops_ca_pinole_police_department` | `sig-ingest-r11-tier2-03` | ☐ | |
| 133 | `ccops_mn_dayton_police_department` | `sig-ingest-r11-tier2-03` | ☐ | |
| 134 | `ccops_oh_cincinnati_police_department` | `sig-ingest-r11-tier2-03` | ☐ | |
| 135 | `ccops_ri_narragansett_police_camera` | `sig-ingest-r11-tier2-03` | ☐ | |
| 136 | `policy_chicago_il_oemc_link_your` | `sig-ingest-r11-tier2-03` | ☐ | |
| 137 | `policy_lafayette_in_camera_registration` | `sig-ingest-r11-tier2-03` | ☐ | |
| 138 | `policy_us_private_camera_registry` | `sig-ingest-r11-tier2-03` | ☐ | |
| 139 | `policy_zionsville_in_camera_registry` | `sig-ingest-r11-tier2-03` | ☐ | |
| 140 | `statrep_vt_vermont_law_enforcement` | `sig-ingest-r11-tier2-01` | ☐ | |

## L10 — S6 extras family-day (P36.76 Axon Connect · P36.77 DocumentCloud/MuckRock · P36.78 Sourcewell/OMNIA + the RB-06b seat)

| # | flag row (source id) | host job | flipped | executed-at |
|---|---|---|---|---|
| 141 | `axon_connect` | `sig-ingest-r11-tier2-01` | ☐ | |
| 142 | `documentcloud` | `sig-ingest-r11-tier2-01` | ☐ | |
| 143 | `muckrock_public` | `sig-ingest-r11-tier2-01` | ☐ | |
| 144 | `sourcewell` | `sig-ingest-r11-tier2-01` | ☐ | |
| 145 | `omnia_partners` | `sig-ingest-r11-tier2-01` | ☐ | |
| 146 | `camreg_bellevue_wa` | `sig-ingest-r11-tier2-01` | ☐ | |

## Context rows — the P37.16a/b Part VIII dossier-capture seats

These eight seats are tier-2 batch members but are **never on this
wave's flip list**: their flips and first captures ride P37.16a/b's
own in-ticket operator go (the Part VIII-screened lane is never
pre-authorised). An unflipped seat's later batch fire records the
loader's gated refusal — a recorded outcome, never a defeat
attempt.

| context seat | batch | notes |
|---|---|---|
| `ccops_ca_san_diego_privacy_advisory` | `r11-tier2-03` | P37.16a/b in-ticket go |
| `ccops_ca_san_diego_sunshine_act_goods` | `r11-tier2-01` | P37.16a/b in-ticket go |
| `ccops_ok_oklahoma_city_okc_flock_council` | `r11-tier2-01` | P37.16a/b in-ticket go |
| `ccops_ok_tulsa_flock_policies` | `r11-tier2-01` | P37.16a/b in-ticket go |
| `ccops_san_diego_ca` | `r11-tier2-01` | P37.16a/b in-ticket go |
| `policy_ok_oklahoma_dac_uved` | `r11-tier2-01` | P37.16a/b in-ticket go |
| `procportal_ok_oklahoma_omes_statewide` | `r11-tier2-01` | P37.16a/b in-ticket go |
| `statrep_ca_california_auditor_alpr` | `r11-tier2-01` | P37.16a/b in-ticket go |

## Never in Wave D

- `doj_ctas_awards` (AP-T2-093 — not tribal) stays deferred under
  `D-R11-LATER-09`; the gate refuses it in any run set.
- `camreg_tribal_all_leaders_directory` + `legis_tribal_tohono_oodham_notice`
  — the ADR-185 tribal S8 lane landed at P35.11 (Wave A); Wave D
  exercises no tribal lane.
- Any source not on this list — the gate refuses an undeclared run set.

## Re-run prompt

`implement-spec spec=docs/tickets/481_P37.54__wave-d-activation.md
live_verification=true` — each leg needs the recorded ING-GO-D
(GATE-G6 `b91f8e58`), its window, its own gate inputs and its
family's executed OP-26 flips; the flip list is the operator's,
never this row's.
