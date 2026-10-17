# RIGHTS_REVIEW_INDEX — every registered source's rights/compact/custody/gate state (P21.1)

One row per registered source (SIG-LIC-001, SIG-INGEST-023/038). **Rights state**, **compact status**, and **custody posture** are read from `connectors/src/connectors/data/sources.toml`; **gate** and **flip-ready** are computed by `connectors.review` / `connectors.loader`. A **packet** column links the rights-review packet for the 27 sources on the critical path (`docs/build/reports/rights/<id>.md`); the rest are P22+ backlog. `⭐` marks the OKC minimum set (critical-path step 4). Counts are reproduced from `uv run sig-connectors validate` — do not hand-edit; regenerate.

## Counts (from `sig-connectors validate`)

```
registered sources: 588
  rights UNDETERMINED (export gate fails closed): 345
  ingestion_permitted=true: 236
  loadable now (permitted + compact + custody): 236
  flip-ready (rights + compact + custody, flag false): 3
```

**Gate skipped this run (HG-03/HG-04 = SKIP):** nothing was flipped, so `loadable now: 0`. The 18 flip-ready sources are unblockable by an operator flip + recorded review metadata; the 6 OKC rows + `usaspending` + `deflock` + `civicclerk` are UNDETERMINED pending review. See `docs/build/reports/STAGE0_OUTREACH_RECORD.md` for the compact/outreach state.

## OKC minimum set (critical-path step 4)

`⭐` `deflock_repo`, `ok_statute`, `okc_council`, `okc_procurement`, `okcpd_policy`, `osm_overpass` — government records (R1/R2) + the ODbL/community OSM route. News rows (`journalrecord`, `oklahoman`) are LINK-posture candidates (link out, never re-host).

## All sources

| ⭐ | source id | rights (SPDX) | compact | custody | flip-ready | gate | packet |
|---|---|---|---|---|---|---|---|
|  | `aclu_cell_site_simulators` | UNDETERMINED | not_contacted | REFERENCE |  | REFUSED | — (P22+ backlog) |
|  | `aclu_flock_toolkit` | UNDETERMINED | not_contacted | REFERENCE |  | REFUSED | — (P22+ backlog) |
|  | `agency_audit_export` | CC0-1.0 | public_terms_only | MIRROR |  | LOADABLE | [docs/build/rights/agency_audit_export.md](rights/agency_audit_export.md) |
|  | `agenda_az_maricopa_county_board_of` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `agenda_bexar_county_tx_agenda_center` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `agenda_des_moines_ia_council` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `agenda_durham_nc_agenda_center` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `agenda_frisco_tx_onbase_agenda_online` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `agenda_haskell_ar_council` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `agenda_hialeah_fl_agenda_center` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `agenda_jasper_sc_council` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `agenda_jersey_city_nj_digital_agenda` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `agenda_nd_fargo_city_commission_agendas` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `agenda_savannah_ga_2023_05_25` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `agenda_tampa_fl_onbase_agenda_online` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `agenda_tx_dallas_county_commissioners` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `agenda_us_agency_fusus_real` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `alpr_abuse_library` | UNDETERMINED | not_contacted | REFERENCE |  | REFUSED | — (P22+ backlog) |
|  | `alpr_accountability_atlas` | UNDETERMINED | not_contacted | REFERENCE |  | REFUSED | — (P22+ backlog) |
|  | `alpr_watch` | UNDETERMINED | not_contacted | REFERENCE |  | REFUSED | — (P22+ backlog) |
|  | `alpr_watch_code` | UNDETERMINED | not_contacted | REFERENCE |  | REFUSED | — (P22+ backlog) |
|  | `alpr_watch_dashboard` | UNDETERMINED | not_contacted | REFERENCE |  | REFUSED | — (P22+ backlog) |
|  | `alpr_watch_foia_method` | UNDETERMINED | not_contacted | REFERENCE |  | REFUSED | — (P22+ backlog) |
|  | `amsterdam_camerakaart` | UNDETERMINED | public_terms_only | REFERENCE |  | REFUSED | [docs/build/rights/amsterdam_camerakaart.md](rights/amsterdam_camerakaart.md) |
|  | `aspi_mapping_chinas_tech_giants` | LicenseRef-DerivedFacts-Citations | public_terms_only | DERIVE |  | LOADABLE | [docs/build/rights/aspi_mapping_chinas_tech_giants.md](rights/aspi_mapping_chinas_tech_giants.md) |
|  | `atlas_about` | UNDETERMINED | public_terms_only | REFERENCE |  | REFUSED | — (P22+ backlog) |
|  | `atlas_data_library` | UNDETERMINED | public_terms_only | LINK |  | REFUSED | — (P22+ backlog) |
|  | `atlas_methodology` | UNDETERMINED | public_terms_only | REFERENCE |  | REFUSED | — (P22+ backlog) |
|  | `austria_vidreg` | UNDETERMINED | public_terms_only | REFERENCE |  | REFUSED | [docs/build/rights/austria_vidreg.md](rights/austria_vidreg.md) |
|  | `axon_community_connect` | UNDETERMINED | public_terms_only | REFERENCE |  | REFUSED | — (P22+ backlog) |
|  | `bidnet_direct` | UNDETERMINED | not_contacted | LINK |  | REFUSED | [docs/build/rights/bidnet_direct.md](rights/bidnet_direct.md) |
|  | `boarddocs` | UNDETERMINED | not_contacted | LINK |  | REFUSED | — (P22+ backlog) |
|  | `bonfire` | UNDETERMINED | not_contacted | LINK |  | REFUSED | [docs/build/rights/bonfire.md](rights/bonfire.md) |
|  | `buyboard` | UNDETERMINED | public_terms_only | LINK |  | REFUSED | — (P22+ backlog) |
|  | `ca_sharing_visualization` | UNDETERMINED | public_terms_only | LINK |  | REFUSED | — (P22+ backlog) |
|  | `ca_state_auditor` | UNDETERMINED | not_contacted | REFERENCE |  | REFUSED | [docs/build/rights/ca_state_auditor.md](rights/ca_state_auditor.md) |
|  | `camreg_achd_id` | LicenseRef-PublicRecord-FactualCompilation | public_terms_only | MIRROR |  | LOADABLE | — (P22+ backlog) |
|  | `camreg_act_au` | CC-BY-4.0 | public_terms_only | MIRROR |  | LOADABLE | [docs/build/rights/camreg_act_au.md](rights/camreg_act_au.md) |
|  | `camreg_alabaster_al_lpr_cameras` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `camreg_amber_kh` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | — (P22+ backlog) |
|  | `camreg_apram_pt` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | — (P22+ backlog) |
|  | `camreg_arc_1975641302` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | — (P22+ backlog) |
|  | `camreg_arlington_va` | LicenseRef-PublicRecord-FactualCompilation | public_terms_only | MIRROR |  | LOADABLE | — (P22+ backlog) |
|  | `camreg_au_ckan_package_search` | UNDETERMINED | public_terms_only | MIRROR |  | REFUSED | — (P22+ backlog) |
|  | `camreg_au_nsw_sydney_street_safety` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `camreg_au_qld_towns_cctv_camera_register` | UNDETERMINED | public_terms_only | MIRROR |  | REFUSED | — (P22+ backlog) |
|  | `camreg_au_tas_emergency_closed_circuit` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `camreg_au_tas_hobar_security_camera` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `camreg_au_vic_ballarat_cctv_cameras` | UNDETERMINED | public_terms_only | MIRROR |  | REFUSED | — (P22+ backlog) |
|  | `camreg_au_vic_geelong_closed_circuit` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `camreg_au_wa_perth_security_cameras` | UNDETERMINED | public_terms_only | MIRROR |  | REFUSED | — (P22+ backlog) |
|  | `camreg_austin_tx` | CC0-1.0 | public_terms_only | MIRROR |  | LOADABLE | [docs/build/rights/camreg_austin_tx.md](rights/camreg_austin_tx.md) |
|  | `camreg_avctransport` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | — (P22+ backlog) |
|  | `camreg_az_mesa_city_of_expenditures` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `camreg_azdot_az` | LicenseRef-PublicRecord-FactualCompilation | public_terms_only | MIRROR |  | LOADABLE | — (P22+ backlog) |
|  | `camreg_baltimore_atves_md` | LicenseRef-PublicRecord-FactualCompilation | public_terms_only | MIRROR |  | LOADABLE | — (P22+ backlog) |
|  | `camreg_baltimore_md` | CC-BY-3.0 | public_terms_only | MIRROR |  | LOADABLE | [docs/build/rights/camreg_baltimore_md.md](rights/camreg_baltimore_md.md) |
|  | `camreg_bangla_bd` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | — (P22+ backlog) |
|  | `camreg_batonrouge_la` | CC0-1.0 | public_terms_only | MIRROR |  | LOADABLE | [docs/build/rights/camreg_batonrouge_la.md](rights/camreg_batonrouge_la.md) |
|  | `camreg_bedford_gb` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | — (P22+ backlog) |
|  | `camreg_bellevue_wa` | UNDETERMINED | not_contacted | MIRROR |  | REFUSED | — (P22+ backlog) |
|  | `camreg_bettendorf_ia` | LicenseRef-PublicRecord-FactualCompilation | public_terms_only | MIRROR |  | LOADABLE | — (P22+ backlog) |
|  | `camreg_bloomington_il_drone_flights` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `camreg_bouhan_jp` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | — (P22+ backlog) |
|  | `camreg_brea_ca` | LicenseRef-PublicRecord-FactualCompilation | public_terms_only | MIRROR |  | LOADABLE | — (P22+ backlog) |
|  | `camreg_ca_monterey_park_flock_camera` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `camreg_caledon_on` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | — (P22+ backlog) |
|  | `camreg_calgary_ab` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | — (P22+ backlog) |
|  | `camreg_caloes_ca` | LicenseRef-PublicRecord-FactualCompilation | public_terms_only | MIRROR |  | LOADABLE | — (P22+ backlog) |
|  | `camreg_camberwell_au` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | — (P22+ backlog) |
|  | `camreg_camilo_schools` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | — (P22+ backlog) |
|  | `camreg_carver_mn` | LicenseRef-PublicRecord-FactualCompilation | public_terms_only | MIRROR |  | LOADABLE | — (P22+ backlog) |
|  | `camreg_chattanooga_tn` | LicenseRef-PublicRecord-FactualCompilation | public_terms_only | MIRROR |  | LOADABLE | — (P22+ backlog) |
|  | `camreg_chicago_il` | LicenseRef-PublicRecord-FactualCompilation | public_terms_only | MIRROR |  | LOADABLE | — (P22+ backlog) |
|  | `camreg_colgis` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | — (P22+ backlog) |
|  | `camreg_cotgeo` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | — (P22+ backlog) |
|  | `camreg_ctdot_speed_safety` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `camreg_cwarcgis` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | — (P22+ backlog) |
|  | `camreg_dc_ddot_ate` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `camreg_dc_dot_dc` | LicenseRef-PublicRecord-FactualCompilation | public_terms_only | MIRROR |  | LOADABLE | — (P22+ backlog) |
|  | `camreg_dc_ovsjg_camera_rebate` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `camreg_de_delaware_checkbook_expenditure` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `camreg_denver_co` | LicenseRef-PublicRecord-FactualCompilation | public_terms_only | MIRROR |  | LOADABLE | — (P22+ backlog) |
|  | `camreg_detroit_mi_project_green_light` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `camreg_donegal_ie` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | — (P22+ backlog) |
|  | `camreg_dover_gb` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | — (P22+ backlog) |
|  | `camreg_dubuque_ia` | LicenseRef-PublicRecord-FactualCompilation | public_terms_only | MIRROR |  | LOADABLE | — (P22+ backlog) |
|  | `camreg_durham_gb` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | — (P22+ backlog) |
|  | `camreg_eastdun_gb` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | — (P22+ backlog) |
|  | `camreg_ebrgis_la` | LicenseRef-PublicRecord-FactualCompilation | public_terms_only | MIRROR |  | LOADABLE | — (P22+ backlog) |
|  | `camreg_edmonton_ab` | UNDETERMINED | not_contacted | MIRROR |  | REFUSED | — (P22+ backlog) |
|  | `camreg_elgin_il_lpr_cameras` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `camreg_es_md_madrid_c_maras_de` | UNDETERMINED | public_terms_only | MIRROR |  | REFUSED | — (P22+ backlog) |
|  | `camreg_esri_dash` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | — (P22+ backlog) |
|  | `camreg_esriukpolice_gb` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | — (P22+ backlog) |
|  | `camreg_essex_gb` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | — (P22+ backlog) |
|  | `camreg_eu_eea_data_europa_search_api` | UNDETERMINED | public_terms_only | MIRROR |  | REFUSED | — (P22+ backlog) |
|  | `camreg_fdot_flock` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `camreg_firemedic` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | — (P22+ backlog) |
|  | `camreg_fl511_fl` | LicenseRef-PublicRecord-FactualCompilation | public_terms_only | MIRROR |  | LOADABLE | — (P22+ backlog) |
|  | `camreg_fl_broward_county_us_palm_beach` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `camreg_forwardalliance` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | — (P22+ backlog) |
|  | `camreg_fr_92_grand_paris_seine_ouest_vid` | UNDETERMINED | public_terms_only | MIRROR |  | REFUSED | — (P22+ backlog) |
|  | `camreg_friendswood_tx` | LicenseRef-PublicRecord-FactualCompilation | public_terms_only | MIRROR |  | LOADABLE | — (P22+ backlog) |
|  | `camreg_ga_brookhaven_flock_camera` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `camreg_ga_flock_cameras_asof` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `camreg_ga_peachtree_corners_flock_camera` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `camreg_ga_savannah_flock_camera` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `camreg_gainesville_fl` | LicenseRef-PublicRecord-FactualCompilation | public_terms_only | MIRROR |  | LOADABLE | — (P22+ backlog) |
|  | `camreg_gastonia_nc_flock_condor_cameras` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `camreg_gb_eng_barnet_cctv_camera` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `camreg_gb_eng_barnet_cctv_traffic` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `camreg_gb_eng_brist_cctv_cameras` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `camreg_gb_eng_ipswich_cctv_camera` | UNDETERMINED | public_terms_only | MIRROR |  | REFUSED | — (P22+ backlog) |
|  | `camreg_gb_eng_leice_cctv_cameras` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `camreg_gb_eng_mansf_cctv_cameras` | UNDETERMINED | public_terms_only | MIRROR |  | REFUSED | — (P22+ backlog) |
|  | `camreg_gb_eng_north_cctv_cameras` | UNDETERMINED | public_terms_only | MIRROR |  | REFUSED | — (P22+ backlog) |
|  | `camreg_gb_eng_runny_cctv_cameras` | UNDETERMINED | public_terms_only | MIRROR |  | REFUSED | — (P22+ backlog) |
|  | `camreg_gb_eng_south_skdc_cctv` | UNDETERMINED | public_terms_only | MIRROR |  | REFUSED | — (P22+ backlog) |
|  | `camreg_gb_eng_traff_trafford_cctv` | UNDETERMINED | public_terms_only | MIRROR |  | REFUSED | — (P22+ backlog) |
|  | `camreg_gb_sct_clackmannanshire_cctv` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `camreg_gb_sct_edinburgh_public_cctv` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `camreg_gedling_gb` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | — (P22+ backlog) |
|  | `camreg_gistel_be` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | — (P22+ backlog) |
|  | `camreg_glasgow_gb` | OGL-UK-3.0 | public_terms_only | MIRROR |  | LOADABLE | [docs/build/rights/camreg_glasgow_gb.md](rights/camreg_glasgow_gb.md) |
|  | `camreg_gmh_emc_ga` | LicenseRef-PublicRecord-FactualCompilation | public_terms_only | MIRROR |  | LOADABLE | — (P22+ backlog) |
|  | `camreg_goldcoast_au` | CC-BY-4.0 | public_terms_only | MIRROR |  | LOADABLE | [docs/build/rights/camreg_goldcoast_au.md](rights/camreg_goldcoast_au.md) |
|  | `camreg_guildford_gb` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | — (P22+ backlog) |
|  | `camreg_hk_hk` | UNDETERMINED | not_contacted | MIRROR |  | REFUSED | — (P22+ backlog) |
|  | `camreg_honolulu_hi` | LicenseRef-PublicRecord-FactualCompilation | public_terms_only | MIRROR |  | LOADABLE | — (P22+ backlog) |
|  | `camreg_howard_md_school_zone_ate` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `camreg_hyattsville_md_cctv_camera_2024` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `camreg_ie_d_dublin_traffic_poles_with` | UNDETERMINED | public_terms_only | MIRROR |  | REFUSED | — (P22+ backlog) |
|  | `camreg_il_chicago_violence_reduction` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `camreg_indonesia_id` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | — (P22+ backlog) |
|  | `camreg_infocemosa` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | — (P22+ backlog) |
|  | `camreg_infraestructura` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | — (P22+ backlog) |
|  | `camreg_ira` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | — (P22+ backlog) |
|  | `camreg_it_me_messina_videosorveglianza` | UNDETERMINED | public_terms_only | MIRROR |  | REFUSED | — (P22+ backlog) |
|  | `camreg_jcfd3_or` | LicenseRef-PublicRecord-FactualCompilation | public_terms_only | MIRROR |  | LOADABLE | — (P22+ backlog) |
|  | `camreg_jeffersonville_in_flock` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `camreg_jmh_us` | LicenseRef-PublicRecord-FactualCompilation | public_terms_only | MIRROR |  | LOADABLE | — (P22+ backlog) |
|  | `camreg_kcmo_mo` | LicenseRef-PublicRecord-FactualCompilation | public_terms_only | MIRROR |  | LOADABLE | — (P22+ backlog) |
|  | `camreg_keizer_or` | LicenseRef-PublicRecord-FactualCompilation | public_terms_only | MIRROR |  | LOADABLE | — (P22+ backlog) |
|  | `camreg_kirkland_wa` | LicenseRef-PublicRecord-FactualCompilation | public_terms_only | MIRROR |  | LOADABLE | — (P22+ backlog) |
|  | `camreg_la_east_baton_rouge_parish_flock` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `camreg_la_new_orleans_eye_on` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `camreg_lakeland_fl_red_light` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `camreg_lambeth_gb` | OGL-UK-3.0 | public_terms_only | MIRROR |  | LOADABLE | [docs/build/rights/camreg_lambeth_gb.md](rights/camreg_lambeth_gb.md) |
|  | `camreg_lawrence_ks` | LicenseRef-PublicRecord-FactualCompilation | public_terms_only | MIRROR |  | LOADABLE | — (P22+ backlog) |
|  | `camreg_leon_county_fl_overwatch_viewer` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `camreg_leon_fl` | LicenseRef-PublicRecord-FactualCompilation | public_terms_only | MIRROR |  | LOADABLE | — (P22+ backlog) |
|  | `camreg_lexington_ky` | LicenseRef-PublicRecord-FactualCompilation | public_terms_only | MIRROR |  | LOADABLE | — (P22+ backlog) |
|  | `camreg_lisburn_gb` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | — (P22+ backlog) |
|  | `camreg_lojic_ky` | LicenseRef-PublicRecord-FactualCompilation | public_terms_only | MIRROR |  | LOADABLE | — (P22+ backlog) |
|  | `camreg_lpd_flock` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | — (P22+ backlog) |
|  | `camreg_ma_massachusetts_capital` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `camreg_manhattan_ks` | LicenseRef-PublicRecord-FactualCompilation | public_terms_only | MIRROR |  | LOADABLE | — (P22+ backlog) |
|  | `camreg_marble_falls_tx_flock_locations` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `camreg_mark43` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | — (P22+ backlog) |
|  | `camreg_massdot_ma` | LicenseRef-PublicRecord-FactualCompilation | public_terms_only | MIRROR |  | LOADABLE | — (P22+ backlog) |
|  | `camreg_mbrc_au` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | — (P22+ backlog) |
|  | `camreg_mctx_tx` | LicenseRef-PublicRecord-FactualCompilation | public_terms_only | MIRROR |  | LOADABLE | — (P22+ backlog) |
|  | `camreg_md_opendata` | LicenseRef-PublicRecord-FactualCompilation | public_terms_only | MIRROR |  | LOADABLE | — (P22+ backlog) |
|  | `camreg_medford_or_ate` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `camreg_medford_or_drone_deployments_fs` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `camreg_mi_detroit_dpd_shotspotter` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `camreg_milford_ct_flocklprcam` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `camreg_mndot_mn` | LicenseRef-PublicRecord-FactualCompilation | public_terms_only | MIRROR |  | LOADABLE | — (P22+ backlog) |
|  | `camreg_monmap_mn` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | — (P22+ backlog) |
|  | `camreg_montgomery_md_ate` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `camreg_mueller_de` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | — (P22+ backlog) |
|  | `camreg_nashville_tn` | LicenseRef-PublicRecord-FactualCompilation | public_terms_only | MIRROR |  | LOADABLE | — (P22+ backlog) |
|  | `camreg_ne_lincoln_traffic_cameras` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `camreg_nitro` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | — (P22+ backlog) |
|  | `camreg_nj_new_jersey_yourmoney` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `camreg_nola_la` | CC0-1.0 | public_terms_only | MIRROR |  | LOADABLE | [docs/build/rights/camreg_nola_la.md](rights/camreg_nola_la.md) |
|  | `camreg_nola_safety_la` | LicenseRef-PublicRecord-FactualCompilation | public_terms_only | MIRROR |  | LOADABLE | — (P22+ backlog) |
|  | `camreg_northayrshire_gb` | OGL-UK-3.0 | public_terms_only | MIRROR |  | LOADABLE | [docs/build/rights/camreg_northayrshire_gb.md](rights/camreg_northayrshire_gb.md) |
|  | `camreg_nottingham_gb` | OGL-UK-3.0 | public_terms_only | MIRROR |  | LOADABLE | [docs/build/rights/camreg_nottingham_gb.md](rights/camreg_nottingham_gb.md) |
|  | `camreg_nv_las_vegas_us_clark_county` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `camreg_nyc_mta_bus_lane_ate` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `camreg_nzta_nz` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | — (P22+ backlog) |
|  | `camreg_oakland_ca_shotspotter_2013_2015` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `camreg_oem_camera` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | — (P22+ backlog) |
|  | `camreg_omaha_ne_parks_cameras` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `camreg_oosgis_nl` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | — (P22+ backlog) |
|  | `camreg_osm_surveillance` | ODbL-1.0 | public_terms_only | MIRROR |  | LOADABLE | — (P22+ backlog) |
|  | `camreg_ottawa_on` | LicenseRef-Ottawa-ODL-2.0 | public_terms_only | MIRROR |  | LOADABLE | [docs/build/rights/camreg_ottawa_on.md](rights/camreg_ottawa_on.md) |
|  | `camreg_palmdesert_ca` | LicenseRef-PublicRecord-FactualCompilation | public_terms_only | MIRROR |  | LOADABLE | — (P22+ backlog) |
|  | `camreg_peel_on` | LicenseRef-Peel-ODL-1.0 | public_terms_only | MIRROR |  | LOADABLE | [docs/build/rights/camreg_peel_on.md](rights/camreg_peel_on.md) |
|  | `camreg_penndot_pa` | LicenseRef-PublicRecord-FactualCompilation | public_terms_only | MIRROR |  | LOADABLE | — (P22+ backlog) |
|  | `camreg_peoria_il_drone_usage` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `camreg_pgcounty_md` | LicenseRef-PublicRecord-FactualCompilation | public_terms_only | MIRROR |  | LOADABLE | — (P22+ backlog) |
|  | `camreg_pipeline_sec` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | — (P22+ backlog) |
|  | `camreg_plymouth_gb` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | — (P22+ backlog) |
|  | `camreg_polyu_hk` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | — (P22+ backlog) |
|  | `camreg_portland_or` | LicenseRef-PublicRecord-FactualCompilation | public_terms_only | MIRROR |  | LOADABLE | — (P22+ backlog) |
|  | `camreg_pt_11_lisboa_sistema_de` | UNDETERMINED | public_terms_only | MIRROR |  | REFUSED | — (P22+ backlog) |
|  | `camreg_pueblo_co_flock` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `camreg_puertogaitan_co` | CC-BY-SA-4.0 | public_terms_only | MIRROR |  | LOADABLE | [docs/build/rights/camreg_puertogaitan_co.md](rights/camreg_puertogaitan_co.md) |
|  | `camreg_qldc_au` | UNDETERMINED | not_contacted | MIRROR |  | REFUSED | — (P22+ backlog) |
|  | `camreg_raleigh_nc` | LicenseRef-PublicRecord-FactualCompilation | public_terms_only | MIRROR |  | LOADABLE | — (P22+ backlog) |
|  | `camreg_ramallah_ps` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | — (P22+ backlog) |
|  | `camreg_redmond_wa` | LicenseRef-PublicRecord-FactualCompilation | public_terms_only | MIRROR |  | LOADABLE | — (P22+ backlog) |
|  | `camreg_riyadh_sa` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | — (P22+ backlog) |
|  | `camreg_rochester_ny` | ODbL-1.0 | public_terms_only | MIRROR |  | LOADABLE | [docs/build/rights/camreg_rochester_ny.md](rights/camreg_rochester_ny.md) |
|  | `camreg_rocky_mount_nc_lpr_cameras` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `camreg_salisbury_nc` | LicenseRef-PublicRecord-FactualCompilation | public_terms_only | MIRROR |  | LOADABLE | — (P22+ backlog) |
|  | `camreg_santa_fe_nm_park_cameras` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `camreg_sarasota_fl` | LicenseRef-PublicRecord-FactualCompilation | public_terms_only | MIRROR |  | LOADABLE | — (P22+ backlog) |
|  | `camreg_seattle_wa` | LicenseRef-PublicRecord-FactualCompilation | public_terms_only | MIRROR |  | LOADABLE | — (P22+ backlog) |
|  | `camreg_sensenet` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | — (P22+ backlog) |
|  | `camreg_sheffield_gb` | OGL-UK-3.0 | public_terms_only | MIRROR |  | LOADABLE | [docs/build/rights/camreg_sheffield_gb.md](rights/camreg_sheffield_gb.md) |
|  | `camreg_shelbyville_tn_flock_cameras` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `camreg_si_048_ko_evje_videonadzor_na` | UNDETERMINED | public_terms_only | MIRROR |  | REFUSED | — (P22+ backlog) |
|  | `camreg_siouxfalls_sd` | CC-BY-4.0 | public_terms_only | MIRROR |  | LOADABLE | [docs/build/rights/camreg_siouxfalls_sd.md](rights/camreg_siouxfalls_sd.md) |
|  | `camreg_smart_sky` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | — (P22+ backlog) |
|  | `camreg_south_fulton_ga_lpr_cameras` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `camreg_squan` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | — (P22+ backlog) |
|  | `camreg_stalbert_ab` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | — (P22+ backlog) |
|  | `camreg_stanford_us` | LicenseRef-PublicRecord-FactualCompilation | public_terms_only | MIRROR |  | LOADABLE | — (P22+ backlog) |
|  | `camreg_suffolk_ny_red_light` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `camreg_surrey_bc` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | — (P22+ backlog) |
|  | `camreg_tacoma_wa_ate` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `camreg_temecula_ca_flock_wfl1` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `camreg_thailand_th` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | — (P22+ backlog) |
|  | `camreg_thomasville_ga_flock_location` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `camreg_toronto_on` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | — (P22+ backlog) |
|  | `camreg_townofws` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | — (P22+ backlog) |
|  | `camreg_trafficops_ca` | LicenseRef-PublicRecord-FactualCompilation | public_terms_only | MIRROR |  | LOADABLE | — (P22+ backlog) |
|  | `camreg_tribal_all_leaders_directory` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `camreg_trpa_us` | LicenseRef-PublicRecord-FactualCompilation | public_terms_only | MIRROR |  | LOADABLE | — (P22+ backlog) |
|  | `camreg_tulane_la` | LicenseRef-PublicRecord-FactualCompilation | public_terms_only | MIRROR |  | LOADABLE | — (P22+ backlog) |
|  | `camreg_txdot_rep_tx` | LicenseRef-PublicRecord-FactualCompilation | public_terms_only | MIRROR |  | LOADABLE | — (P22+ backlog) |
|  | `camreg_ua_18_korosten` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `camreg_uchicago` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | — (P22+ backlog) |
|  | `camreg_ucsd` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | — (P22+ backlog) |
|  | `camreg_ukm_my` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | — (P22+ backlog) |
|  | `camreg_umbc_md` | LicenseRef-PublicRecord-FactualCompilation | public_terms_only | MIRROR |  | LOADABLE | — (P22+ backlog) |
|  | `camreg_und_001` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | — (P22+ backlog) |
|  | `camreg_und_002` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | — (P22+ backlog) |
|  | `camreg_und_003` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | — (P22+ backlog) |
|  | `camreg_und_004` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | — (P22+ backlog) |
|  | `camreg_und_005` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | — (P22+ backlog) |
|  | `camreg_und_006` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | — (P22+ backlog) |
|  | `camreg_und_007` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | — (P22+ backlog) |
|  | `camreg_und_008` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | — (P22+ backlog) |
|  | `camreg_und_009` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | — (P22+ backlog) |
|  | `camreg_und_010` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | — (P22+ backlog) |
|  | `camreg_und_011` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | — (P22+ backlog) |
|  | `camreg_und_012` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | — (P22+ backlog) |
|  | `camreg_und_013` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | — (P22+ backlog) |
|  | `camreg_und_014` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | — (P22+ backlog) |
|  | `camreg_und_015` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | — (P22+ backlog) |
|  | `camreg_und_016` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | — (P22+ backlog) |
|  | `camreg_und_017` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | — (P22+ backlog) |
|  | `camreg_und_018` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | — (P22+ backlog) |
|  | `camreg_und_019` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | — (P22+ backlog) |
|  | `camreg_und_020` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | — (P22+ backlog) |
|  | `camreg_und_021` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | — (P22+ backlog) |
|  | `camreg_und_022` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | — (P22+ backlog) |
|  | `camreg_und_023` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | — (P22+ backlog) |
|  | `camreg_und_024` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | — (P22+ backlog) |
|  | `camreg_und_025` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | — (P22+ backlog) |
|  | `camreg_und_026` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | — (P22+ backlog) |
|  | `camreg_und_027` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | — (P22+ backlog) |
|  | `camreg_und_028` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | — (P22+ backlog) |
|  | `camreg_und_029` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | — (P22+ backlog) |
|  | `camreg_univmb_mb` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | — (P22+ backlog) |
|  | `camreg_uofmd_md` | LicenseRef-PublicRecord-FactualCompilation | public_terms_only | MIRROR |  | LOADABLE | — (P22+ backlog) |
|  | `camreg_us_agency_drone_flight` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `camreg_us_agency_published_flock` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `camreg_us_ate_camera_location_and_per` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `camreg_us_body_worn_camera` | UNDETERMINED | public_terms_only | MIRROR |  | REFUSED | — (P22+ backlog) |
|  | `camreg_us_municipal_contract_expenditure` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `camreg_us_nces_school_survey_on_crime` | UNDETERMINED | public_terms_only | MIRROR |  | REFUSED | — (P22+ backlog) |
|  | `camreg_us_ny_001` | LicenseRef-PublicRecord-FactualCompilation | public_terms_only | MIRROR |  | LOADABLE | — (P22+ backlog) |
|  | `camreg_us_ny_002` | LicenseRef-PublicRecord-FactualCompilation | public_terms_only | MIRROR |  | LOADABLE | — (P22+ backlog) |
|  | `camreg_us_socrata_hosted_vendor` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `camreg_va_pittsylvania_county_stationary` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `camreg_va_prince_william_county` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `camreg_vancouver_bc` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | — (P22+ backlog) |
|  | `camreg_wa_washington_state_open` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `camreg_washington_dc` | CC-BY-4.0 | public_terms_only | MIRROR |  | LOADABLE | [docs/build/rights/camreg_washington_dc.md](rights/camreg_washington_dc.md) |
|  | `camreg_webappfme` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | — (P22+ backlog) |
|  | `camreg_wellington_nz` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | — (P22+ backlog) |
|  | `camreg_wim_camera` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | — (P22+ backlog) |
|  | `camreg_winnipeg_mb` | OGL-Canada-2.0 | public_terms_only | MIRROR |  | LOADABLE | [docs/build/rights/camreg_winnipeg_mb.md](rights/camreg_winnipeg_mb.md) |
|  | `camreg_yline` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | — (P22+ backlog) |
|  | `camreg_york_gb` | OGL-UK-3.0 | public_terms_only | MIRROR |  | LOADABLE | [docs/build/rights/camreg_york_gb.md](rights/camreg_york_gb.md) |
|  | `camreg_york_on` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | — (P22+ backlog) |
|  | `camreg_yorku` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | — (P22+ backlog) |
|  | `carnegie_ai_gsi` | LicenseRef-DerivedFacts-Citations | public_terms_only | DERIVE |  | LOADABLE | [docs/build/rights/carnegie_ai_gsi.md](rights/carnegie_ai_gsi.md) |
|  | `ccops_anchorage_ak` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `ccops_austin_tx` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `ccops_baltimore` | UNDETERMINED | public_terms_only | REFERENCE |  | REFUSED | [docs/build/rights/ccops_baltimore.md](rights/ccops_baltimore.md) |
|  | `ccops_berkeley` | UNDETERMINED | public_terms_only | REFERENCE |  | REFUSED | [docs/build/rights/ccops_berkeley.md](rights/ccops_berkeley.md) |
|  | `ccops_boston` | UNDETERMINED | public_terms_only | REFERENCE |  | REFUSED | [docs/build/rights/ccops_boston.md](rights/ccops_boston.md) |
|  | `ccops_ca_calistoga_police_department` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `ccops_ca_pinole_police_department` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `ccops_ca_san_diego_privacy_advisory` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `ccops_ca_san_diego_sunshine_act_goods` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `ccops_cambridge` | LicenseRef-PublicRecord-FactualCompilation | public_terms_only | REFERENCE |  | LOADABLE | [docs/build/rights/ccops_cambridge.md](rights/ccops_cambridge.md) |
|  | `ccops_columbia_mo` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `ccops_davis` | UNDETERMINED | public_terms_only | REFERENCE |  | REFUSED | [docs/build/rights/ccops_davis.md](rights/ccops_davis.md) |
|  | `ccops_dayton_oh` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `ccops_gb_eng_barnet_traffic_cctv` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `ccops_grand_rapids` | UNDETERMINED | public_terms_only | REFERENCE |  | REFUSED | [docs/build/rights/ccops_grand_rapids.md](rights/ccops_grand_rapids.md) |
|  | `ccops_hi_honolulu_police_department` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `ccops_il_chicago_oig_shotspotter` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `ccops_iso_au_privacy_commissioner` | UNDETERMINED | public_terms_only | MIRROR |  | REFUSED | — (P22+ backlog) |
|  | `ccops_it_tn_trento_provvedimento_dell_11` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `ccops_mi_wayne_county_commission` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `ccops_mn_dayton_police_department` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `ccops_mo_st_louis_fy21_spi_shotspotter` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `ccops_nashville` | UNDETERMINED | public_terms_only | REFERENCE |  | REFUSED | [docs/build/rights/ccops_nashville.md](rights/ccops_nashville.md) |
|  | `ccops_nc_charlotte_mecklenburg_police` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `ccops_nc_elizabeth_city_police` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `ccops_ny_new_york_nyc_comptroller` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `ccops_nyc_post` | LicenseRef-DerivedFacts-Citations | public_terms_only | REFERENCE |  | LOADABLE | [docs/build/rights/ccops_nyc_post.md](rights/ccops_nyc_post.md) |
|  | `ccops_oakland` | LicenseRef-PublicRecord-FactualCompilation | public_terms_only | REFERENCE |  | LOADABLE | [docs/build/rights/ccops_oakland.md](rights/ccops_oakland.md) |
|  | `ccops_oh_cincinnati_police_department` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `ccops_ok_oklahoma_city_okc_flock_council` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `ccops_ok_tulsa_flock_policies` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `ccops_ordinance_disclosures` | UNDETERMINED | public_terms_only | MIRROR |  | REFUSED | — (P22+ backlog) |
|  | `ccops_ri_narragansett_police_camera` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `ccops_san_diego_ca` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `ccops_san_francisco_bay_ca` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `ccops_san_jose_ca` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `ccops_santa_clara_county_ca` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `ccops_seattle` | LicenseRef-DerivedFacts-Citations | public_terms_only | REFERENCE |  | LOADABLE | [docs/build/rights/ccops_seattle.md](rights/ccops_seattle.md) |
|  | `ccops_sf` | LicenseRef-DerivedFacts-Citations | public_terms_only | REFERENCE |  | LOADABLE | [docs/build/rights/ccops_sf.md](rights/ccops_sf.md) |
|  | `ccops_si_085_novo_mesto_evidenca_o` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `ccops_somerville` | LicenseRef-PublicRecord-FactualCompilation | public_terms_only | REFERENCE |  | LOADABLE | [docs/build/rights/ccops_somerville.md](rights/ccops_somerville.md) |
|  | `ccops_st_louis_mo` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `census_gazetteer_tiger` | CC0-1.0 | public_terms_only | MIRROR | yes | flip-ready | [docs/build/rights/census_gazetteer_tiger.md](rights/census_gazetteer_tiger.md) |
|  | `census_geocoder` | UNDETERMINED | public_terms_only | REFERENCE |  | REFUSED | — (P22+ backlog) |
|  | `civicclerk` | CC0-1.0 | public_terms_only | REFERENCE |  | LOADABLE | [docs/build/rights/civicclerk.md](rights/civicclerk.md) |
|  | `civicplus` | UNDETERMINED | not_contacted | LINK |  | REFUSED | — (P22+ backlog) |
|  | `congress_gov` | CC0-1.0 | public_terms_only | REFERENCE |  | LOADABLE | [docs/build/rights/congress_gov.md](rights/congress_gov.md) |
|  | `courtlistener_recap` | UNDETERMINED | public_terms_only | REFERENCE |  | REFUSED | [docs/build/rights/courtlistener_recap.md](rights/courtlistener_recap.md) |
|  | `declarationcamera_be` | LicenseRef-DerivedFacts-Citations | public_terms_only | DERIVE |  | LOADABLE | [docs/build/rights/declarationcamera_be.md](rights/declarationcamera_be.md) |
|  | `decp_fr` | etalab-2.0 | public_terms_only | REFERENCE |  | LOADABLE | [docs/build/rights/decp_fr.md](rights/decp_fr.md) |
|  | `deflock` | UNDETERMINED | not_contacted | REFERENCE |  | REFUSED | [docs/build/rights/deflock.md](rights/deflock.md) |
|  | `deflock_app_repo` | AGPL-3.0 | public_terms_only | REFERENCE |  | LOADABLE | [docs/build/rights/deflock_app_repo.md](rights/deflock_app_repo.md) |
| ⭐ | `deflock_repo` | MIT | public_terms_only | REFERENCE |  | LOADABLE | [docs/build/rights/deflock_repo.md](rights/deflock_repo.md) |
|  | `demandstar` | UNDETERMINED | not_contacted | LINK |  | REFUSED | [docs/build/rights/demandstar.md](rights/demandstar.md) |
|  | `denmark_politi_cctv` | UNDETERMINED | public_terms_only | REFERENCE |  | REFUSED | [docs/build/rights/denmark_politi_cctv.md](rights/denmark_politi_cctv.md) |
|  | `dhs_fusion_center_assessments` | CC0-1.0 | public_terms_only | MIRROR |  | LOADABLE | — (P22+ backlog) |
|  | `dhs_fusion_centers` | UNDETERMINED | public_terms_only | REFERENCE |  | REFUSED | — (P22+ backlog) |
|  | `dhs_oig_reports` | CC0-1.0 | public_terms_only | MIRROR |  | LOADABLE | — (P22+ backlog) |
|  | `documentcloud` | UNDETERMINED | public_terms_only | REFERENCE |  | REFUSED | [docs/build/rights/documentcloud.md](rights/documentcloud.md) |
|  | `dossier_okc` | UNDETERMINED | not_contacted | REFERENCE |  | REFUSED | — (P22+ backlog) |
|  | `dossier_san_diego` | UNDETERMINED | not_contacted | REFERENCE |  | REFUSED | — (P22+ backlog) |
|  | `dossier_tulsa` | UNDETERMINED | not_contacted | REFERENCE |  | REFUSED | — (P22+ backlog) |
|  | `dot_511_al` | LicenseRef-PublicRecord-FactualCompilation | public_terms_only | MIRROR |  | LOADABLE | — (P22+ backlog) |
|  | `dot_511_dc` | CC0-1.0 | public_terms_only | MIRROR |  | LOADABLE | [docs/build/rights/dot_511_dc.md](rights/dot_511_dc.md) |
|  | `dot_511_de` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `dot_511_ga` | LicenseRef-PublicRecord-FactualCompilation | public_terms_only | MIRROR |  | LOADABLE | — (P22+ backlog) |
|  | `dot_511_gb` | UNDETERMINED | public_terms_only | MIRROR |  | REFUSED | — (P22+ backlog) |
|  | `dot_511_ia` | CC-BY-4.0 | public_terms_only | MIRROR |  | LOADABLE | [docs/build/rights/dot_511_ia.md](rights/dot_511_ia.md) |
|  | `dot_511_id` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `dot_511_il` | CC-BY-SA-2.0 | public_terms_only | MIRROR |  | LOADABLE | [docs/build/rights/dot_511_il.md](rights/dot_511_il.md) |
|  | `dot_511_ky` | CC0-1.0 | public_terms_only | MIRROR |  | LOADABLE | [docs/build/rights/dot_511_ky.md](rights/dot_511_ky.md) |
|  | `dot_511_la` | LicenseRef-PublicRecord-FactualCompilation | public_terms_only | MIRROR |  | LOADABLE | — (P22+ backlog) |
|  | `dot_511_md` | LicenseRef-PublicRecord-FactualCompilation | public_terms_only | MIRROR |  | LOADABLE | — (P22+ backlog) |
|  | `dot_511_mi` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `dot_511_mo` | CC0-1.0 | public_terms_only | MIRROR |  | LOADABLE | [docs/build/rights/dot_511_mo.md](rights/dot_511_mo.md) |
|  | `dot_511_nc` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `dot_511_nm` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `dot_511_nv` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `dot_511_or` | CC0-1.0 | public_terms_only | MIRROR |  | LOADABLE | [docs/build/rights/dot_511_or.md](rights/dot_511_or.md) |
|  | `dot_511_tx` | UNDETERMINED | not_contacted | MIRROR |  | REFUSED | — (P22+ backlog) |
|  | `dot_511_ut` | CC0-1.0 | public_terms_only | MIRROR |  | LOADABLE | [docs/build/rights/dot_511_ut.md](rights/dot_511_ut.md) |
|  | `dot_511_vt` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `dot_511_wa` | CC0-1.0 | public_terms_only | MIRROR |  | LOADABLE | [docs/build/rights/dot_511_wa.md](rights/dot_511_wa.md) |
|  | `dot_511_wv` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `drivers_against_flock` | UNDETERMINED | not_contacted | LINK |  | REFUSED | — (P22+ backlog) |
|  | `eff_atlas_of_surveillance` | CC-BY-4.0 | public_terms_only | MIRROR |  | LOADABLE | [docs/build/rights/eff_atlas_of_surveillance.md](rights/eff_atlas_of_surveillance.md) |
|  | `eff_copyright` | UNDETERMINED | public_terms_only | REFERENCE |  | REFUSED | — (P22+ backlog) |
|  | `eff_data_driven` | CC-BY-4.0 | public_terms_only | MIRROR |  | LOADABLE | [docs/build/rights/eff_data_driven.md](rights/eff_data_driven.md) |
|  | `eff_street_level_surveillance` | UNDETERMINED | public_terms_only | REFERENCE |  | REFUSED | — (P22+ backlog) |
|  | `equalis_group` | UNDETERMINED | public_terms_only | LINK |  | REFUSED | — (P22+ backlog) |
|  | `escribe` | CC0-1.0 | public_terms_only | REFERENCE |  | LOADABLE | [docs/build/rights/escribe.md](rights/escribe.md) |
|  | `eyes_off_cedar_rapids` | UNDETERMINED | not_contacted | LINK |  | REFUSED | — (P22+ backlog) |
|  | `eyes_off_eugene` | CC0-1.0 | not_contacted | REFERENCE |  | REFUSED | — (P22+ backlog) |
|  | `eyes_on_flock` | CC-BY-SA-4.0 | public_terms_only | MIRROR |  | LOADABLE | [docs/build/rights/eyes_on_flock.md](rights/eyes_on_flock.md) |
|  | `eyes_on_flock_description` | UNDETERMINED | public_terms_only | LINK |  | REFUSED | — (P22+ backlog) |
|  | `faa_drone_waivers` | UNDETERMINED | public_terms_only | REFERENCE |  | REFUSED | — (P22+ backlog) |
|  | `facial_recognition_world_map` | LicenseRef-DerivedFacts-Citations | public_terms_only | DERIVE |  | LOADABLE | [docs/build/rights/facial_recognition_world_map.md](rights/facial_recognition_world_map.md) |
|  | `fbi_cde_agency_registry` | CC0-1.0 | public_terms_only | REFERENCE |  | LOADABLE | [docs/build/rights/fbi_cde_agency_registry.md](rights/fbi_cde_agency_registry.md) |
|  | `fema_hsgp_allocations` | CC0-1.0 | public_terms_only | MIRROR |  | LOADABLE | — (P22+ backlog) |
|  | `flock_ajith_fyi` | UNDETERMINED | not_contacted | LINK |  | REFUSED | — (P22+ backlog) |
|  | `flock_api_terms` | UNDETERMINED | public_terms_only | REFERENCE |  | REFUSED | — (P22+ backlog) |
|  | `flock_finder` | MIT | public_terms_only | REFERENCE |  | LOADABLE | [docs/build/rights/flock_finder.md](rights/flock_finder.md) |
|  | `flock_transparency_portals` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `flock_you` | UNDETERMINED | not_contacted | REFERENCE |  | REFUSED | — (P22+ backlog) |
|  | `flockhopper3_deflock_data` | UNDETERMINED | not_contacted | LINK |  | REFUSED | — (P22+ backlog) |
|  | `flockreporter` | UNDETERMINED | no_response | LINK |  | REFUSED | — (P22+ backlog) |
|  | `foiaxpress` | UNDETERMINED | not_contacted | LINK |  | REFUSED | — (P22+ backlog) |
|  | `footnote4a` | UNDETERMINED | not_contacted | LINK |  | REFUSED | — (P22+ backlog) |
|  | `future_statutory_disclosure_2027` | UNDETERMINED | not_contacted | MIRROR |  | REFUSED | — (P22+ backlog) |
|  | `future_statutory_disclosure_al` | UNDETERMINED | not_contacted | MIRROR |  | REFUSED | — (P22+ backlog) |
|  | `future_statutory_disclosure_ar` | UNDETERMINED | not_contacted | MIRROR |  | REFUSED | — (P22+ backlog) |
|  | `future_statutory_disclosure_mn` | UNDETERMINED | not_contacted | MIRROR |  | REFUSED | — (P22+ backlog) |
|  | `future_statutory_disclosure_nm` | UNDETERMINED | not_contacted | MIRROR |  | REFUSED | — (P22+ backlog) |
|  | `future_statutory_disclosure_ut` | UNDETERMINED | not_contacted | MIRROR |  | REFUSED | — (P22+ backlog) |
|  | `future_statutory_disclosure_va` | UNDETERMINED | not_contacted | MIRROR |  | REFUSED | — (P22+ backlog) |
|  | `gao_surveillance_reports` | CC0-1.0 | public_terms_only | MIRROR |  | LOADABLE | — (P22+ backlog) |
|  | `gleif` | CC0-1.0 | public_terms_only | MIRROR |  | LOADABLE | [docs/build/rights/gleif.md](rights/gleif.md) |
|  | `govqa` | UNDETERMINED | not_contacted | LINK |  | REFUSED | — (P22+ backlog) |
|  | `govspend` | UNDETERMINED | public_terms_only | LINK |  | REFUSED | — (P22+ backlog) |
|  | `granicus` | UNDETERMINED | not_contacted | LINK |  | REFUSED | — (P22+ backlog) |
|  | `grant_al_adeca_psn` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `grant_ca_bscc_ort` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `grant_fl_senate_lfir` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `grant_il_illinois_gata_csfa` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `grant_ma_massachusetts_law_enforcement` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `grant_nj_oag_bwc` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `grant_oh_ohio_criminal_justice` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `grant_ok_dac_jag_lle` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `grant_ok_safe_oklahoma_grant` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `grant_tx_txdmv_mvcpa` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `grant_us_doj_cops_technology` | UNDETERMINED | public_terms_only | MIRROR |  | REFUSED | — (P22+ backlog) |
|  | `gsa` | UNDETERMINED | public_terms_only | LINK |  | REFUSED | — (P22+ backlog) |
|  | `guardian_flock_cameras` | UNDETERMINED | public_terms_only | LINK |  | REFUSED | — (P22+ backlog) |
|  | `have_i_been_flocked` | UNDETERMINED | not_contacted | REFERENCE |  | REFUSED | — (P22+ backlog) |
|  | `hgacbuy` | UNDETERMINED | public_terms_only | LINK |  | REFUSED | — (P22+ backlog) |
|  | `hibf_audit_log_guide` | UNDETERMINED | not_contacted | REFERENCE |  | REFUSED | — (P22+ backlog) |
|  | `hibf_methodology` | UNDETERMINED | not_contacted | REFERENCE |  | REFUSED | — (P22+ backlog) |
|  | `internet_archive_wayback` | UNDETERMINED | public_terms_only | REFERENCE |  | REFUSED | — (P22+ backlog) |
|  | `iqm2` | UNDETERMINED | not_contacted | LINK |  | REFUSED | — (P22+ backlog) |
| · | `journalrecord` | UNDETERMINED | public_terms_only | LINK |  | REFUSED | [docs/build/rights/journalrecord.md](rights/journalrecord.md) |
|  | `justfoia` | UNDETERMINED | not_contacted | LINK |  | REFUSED | — (P22+ backlog) |
|  | `la_city_clerk_cfms` | UNDETERMINED | not_contacted | LINK |  | REFUSED | — (P22+ backlog) |
|  | `la_quadrature_du_net` | UNDETERMINED | not_contacted | LINK |  | REFUSED | — (P22+ backlog) |
|  | `leaic_crosswalk` | UNDETERMINED | public_terms_only | MIRROR |  | REFUSED | — (P22+ backlog) |
|  | `legis_ca_gov_code_53166` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `legis_gu_governor` | UNDETERMINED | public_terms_only | MIRROR |  | REFUSED | — (P22+ backlog) |
|  | `legis_ie_rs_general_scheme` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `legis_pr_pc0489_ley_del` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `legis_pr_pc0560_plan_de` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `legis_pr_rc0740_investigaci_sobre` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `legis_pr_rc0787_resoluci_de` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `legis_pr_rcs0198_resoluci_conjunta` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `legis_pr_rs0604_resoluci_del` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `legis_pr_sistema_nico_de` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `legis_tribal_tohono_oodham_notice` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `legis_us_dhs_sorn_plate_data` | UNDETERMINED | public_terms_only | MIRROR |  | REFUSED | — (P22+ backlog) |
|  | `legis_us_federal_register_api` | UNDETERMINED | public_terms_only | MIRROR |  | REFUSED | — (P22+ backlog) |
|  | `legis_vi_legislature_virgin_islands` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `legistar` | CC0-1.0 | public_terms_only | REFERENCE |  | LOADABLE | [docs/build/rights/legistar.md](rights/legistar.md) |
|  | `madada` | LicenseRef-DerivedFacts-Citations | public_terms_only | DERIVE |  | LOADABLE | [docs/build/rights/madada.md](rights/madada.md) |
|  | `monahan_grounding_the_flock` | UNDETERMINED | public_terms_only | LINK |  | REFUSED | — (P22+ backlog) |
|  | `muckrock` | LicenseRef-MuckRock-API-ToS | public_terms_only | REFERENCE |  | LOADABLE | [docs/build/rights/muckrock.md](rights/muckrock.md) |
|  | `naspo_valuepoint` | UNDETERMINED | public_terms_only | LINK |  | REFUSED | — (P22+ backlog) |
|  | `natural_earth_10m` | CC0-1.0 | public_terms_only | MIRROR | yes | flip-ready | [docs/build/rights/natural_earth_10m.md](rights/natural_earth_10m.md) |
|  | `nces_ipeds_ntd_cms` | UNDETERMINED | public_terms_only | MIRROR |  | REFUSED | — (P22+ backlog) |
|  | `nextrequest` | UNDETERMINED | public_terms_only | REFERENCE |  | REFUSED | — (P22+ backlog) |
|  | `novusagenda` | UNDETERMINED | not_contacted | LINK |  | REFUSED | — (P22+ backlog) |
|  | `ok_dac_uved` | UNDETERMINED | not_contacted | REFERENCE |  | REFUSED | [docs/build/rights/ok_dac_uved.md](rights/ok_dac_uved.md) |
|  | `ok_omes_contracts` | UNDETERMINED | not_contacted | REFERENCE |  | REFUSED | [docs/build/rights/ok_omes_contracts.md](rights/ok_omes_contracts.md) |
| ⭐ | `ok_statute` | CC0-1.0 | public_terms_only | REFERENCE |  | LOADABLE | [docs/build/rights/ok_statute.md](rights/ok_statute.md) |
| ⭐ | `okc_council` | CC0-1.0 | public_terms_only | REFERENCE |  | LOADABLE | [docs/build/rights/okc_council.md](rights/okc_council.md) |
| ⭐ | `okc_procurement` | CC0-1.0 | public_terms_only | REFERENCE |  | LOADABLE | [docs/build/rights/okc_procurement.md](rights/okc_procurement.md) |
| ⭐ | `okcpd_policy` | CC0-1.0 | public_terms_only | REFERENCE |  | LOADABLE | [docs/build/rights/okcpd_policy.md](rights/okcpd_policy.md) |
| · | `oklahoman` | UNDETERMINED | public_terms_only | LINK |  | REFUSED | [docs/build/rights/oklahoman.md](rights/oklahoman.md) |
|  | `omnia_partners` | UNDETERMINED | public_terms_only | LINK |  | REFUSED | — (P22+ backlog) |
|  | `opengov_procurement` | UNDETERMINED | not_contacted | LINK |  | REFUSED | [docs/build/rights/opengov_procurement.md](rights/opengov_procurement.md) |
|  | `openstates` | CC0-1.0 | public_terms_only | REFERENCE |  | LOADABLE | [docs/build/rights/openstates.md](rights/openstates.md) |
|  | `osm_automated_edits_coc` | ODbL-1.0 | public_terms_only | REFERENCE |  | LOADABLE | [docs/build/rights/osm_automated_edits_coc.md](rights/osm_automated_edits_coc.md) |
|  | `osm_copyright` | ODbL-1.0 | public_terms_only | REFERENCE |  | LOADABLE | [docs/build/rights/osm_copyright.md](rights/osm_copyright.md) |
|  | `osm_element_history` | ODbL-1.0 | public_terms_only | REFERENCE |  | LOADABLE | [docs/build/rights/osm_element_history.md](rights/osm_element_history.md) |
| ⭐ | `osm_overpass` | ODbL-1.0 | public_terms_only | REFERENCE |  | LOADABLE | [docs/build/rights/osm_overpass.md](rights/osm_overpass.md) |
|  | `osm_replication` | ODbL-1.0 | public_terms_only | REFERENCE |  | LOADABLE | [docs/build/rights/osm_replication.md](rights/osm_replication.md) |
|  | `osm_surveillance_tagging` | ODbL-1.0 | public_terms_only | REFERENCE |  | LOADABLE | [docs/build/rights/osm_surveillance_tagging.md](rights/osm_surveillance_tagging.md) |
|  | `osm_taginfo` | ODbL-1.0 | public_terms_only | REFERENCE |  | LOADABLE | [docs/build/rights/osm_taginfo.md](rights/osm_taginfo.md) |
|  | `osmf_licence_guidelines` | ODbL-1.0 | public_terms_only | REFERENCE |  | LOADABLE | [docs/build/rights/osmf_licence_guidelines.md](rights/osmf_licence_guidelines.md) |
|  | `panopti_ca` | MIT | not_contacted | REFERENCE |  | REFUSED | — (P22+ backlog) |
|  | `panopticity` | UNDETERMINED | not_contacted | LINK |  | REFUSED | — (P22+ backlog) |
|  | `pathways_acoustic_drone_location` | LicenseRef-DerivedFacts-Citations | public_terms_only | DERIVE |  | LOADABLE | [docs/build/rights/pathways_acoustic_drone_location.md](rights/pathways_acoustic_drone_location.md) |
|  | `pathways_fr_css_forensics` | LicenseRef-DerivedFacts-Citations | public_terms_only | DERIVE |  | LOADABLE | [docs/build/rights/pathways_fr_css_forensics.md](rights/pathways_fr_css_forensics.md) |
|  | `pathways_rtcc_federation` | LicenseRef-DerivedFacts-Citations | public_terms_only | DERIVE |  | LOADABLE | [docs/build/rights/pathways_rtcc_federation.md](rights/pathways_rtcc_federation.md) |
|  | `periscope_s2g` | UNDETERMINED | not_contacted | LINK |  | REFUSED | [docs/build/rights/periscope_s2g.md](rights/periscope_s2g.md) |
|  | `planetbids` | UNDETERMINED | not_contacted | LINK |  | REFUSED | [docs/build/rights/planetbids.md](rights/planetbids.md) |
|  | `policy_albuquerque_nm_apd` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `policy_anaheim_ca_pd_policy_manual` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `policy_bangor_me_pd` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `policy_chicago_il_oemc_link_your` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `policy_houston_tx_hpd` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `policy_lafayette_in_camera_registration` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `policy_little_rock_ar_pd` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `policy_maricopa_county_az_mcso_policies` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `policy_norman_ok_alpr_policy_amendment` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `policy_ok_oklahoma_dac_uved` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `policy_onslow_nc_schools` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `policy_orange_county_ca_sheriff` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `policy_pasadena_ca_pd` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `policy_pflugerville_tx_isd` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `policy_st_cloud_mn_isd742` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `policy_us_private_camera_registry` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `policy_whitesboro_ny_csd` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `policy_zionsville_in_camera_registry` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `powerdms_public_portals` | UNDETERMINED | not_contacted | LINK |  | REFUSED | [docs/build/rights/powerdms_public_portals.md](rights/powerdms_public_portals.md) |
|  | `primegov` | CC0-1.0 | public_terms_only | REFERENCE |  | LOADABLE | [docs/build/rights/primegov.md](rights/primegov.md) |
|  | `private_eyes` | MIT | not_contacted | REFERENCE |  | REFUSED | — (P22+ backlog) |
|  | `procportal_austin_tx` | CC0-1.0 | public_terms_only | MIRROR |  | LOADABLE | [docs/build/rights/procportal_austin_tx.md](rights/procportal_austin_tx.md) |
|  | `procportal_chicago_il` | UNDETERMINED | not_contacted | LINK |  | REFUSED | [docs/build/rights/procportal_chicago_il.md](rights/procportal_chicago_il.md) |
|  | `procportal_cook_il_awards` | UNDETERMINED | public_terms_only | MIRROR |  | REFUSED | — (P22+ backlog) |
|  | `procportal_davie_fl_purchasing` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `procportal_fl_florida_buy_cooperative` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `procportal_forsyth_nc_purchasing` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `procportal_kcmo_mo` | CC0-1.0 | public_terms_only | MIRROR |  | LOADABLE | [docs/build/rights/procportal_kcmo_mo.md](rights/procportal_kcmo_mo.md) |
|  | `procportal_ny_northeastern_regional` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `procportal_nyc_ny` | CC0-1.0 | public_terms_only | MIRROR |  | LOADABLE | [docs/build/rights/procportal_nyc_ny.md](rights/procportal_nyc_ny.md) |
|  | `procportal_ok_oklahoma_omes_statewide` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `procportal_pr_consulta_del_registro` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `procportal_sf_ca` | CC0-1.0 | public_terms_only | MIRROR |  | LOADABLE | [docs/build/rights/procportal_sf_ca.md](rights/procportal_sf_ca.md) |
|  | `procportal_tx_texas_dir_cooperative` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `procportal_us_naspo_valuepoint_portfolio` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `procportal_wa_des_contract_sales` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `procportal_wa_wsipc_rfp_24` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `publicpurchase` | UNDETERMINED | not_contacted | LINK |  | REFUSED | [docs/build/rights/publicpurchase.md](rights/publicpurchase.md) |
|  | `r_flocksurveillance` | UNDETERMINED | public_terms_only | LINK |  | REFUSED | — (P22+ backlog) |
|  | `raa_prefectures` | ODbL-1.0 | public_terms_only | REFERENCE |  | LOADABLE | [docs/build/rights/raa_prefectures.md](rights/raa_prefectures.md) |
|  | `ringmast4r_flock` | UNDETERMINED | not_contacted | LINK |  | REFUSED | — (P22+ backlog) |
|  | `rotterdam_cameraregister` | UNDETERMINED | public_terms_only | REFERENCE |  | REFUSED | [docs/build/rights/rotterdam_cameraregister.md](rights/rotterdam_cameraregister.md) |
|  | `sam_gov` | CC0-1.0 | public_terms_only | REFERENCE |  | LOADABLE | [docs/build/rights/sam_gov.md](rights/sam_gov.md) |
|  | `sm_alpr` | AGPL-3.0 | not_contacted | REFERENCE |  | REFUSED | — (P22+ backlog) |
|  | `sourcewell` | UNDETERMINED | public_terms_only | REFERENCE |  | REFUSED | — (P22+ backlog) |
|  | `sous_surveillance_osm_import` | ODbL-1.0 | public_terms_only | REFERENCE |  | LOADABLE | [docs/build/rights/sous_surveillance_osm_import.md](rights/sous_surveillance_osm_import.md) |
|  | `state_alpr_statute_inventory` | LicenseRef-DerivedFacts-Citations | public_terms_only | DERIVE | yes | flip-ready | [docs/build/rights/state_alpr_statute_inventory.md](rights/state_alpr_statute_inventory.md) |
|  | `state_alpr_statute_inventory_2026` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `statrep_austin_tx_auditor` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `statrep_ca_california_auditor_alpr` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `statrep_ca_special_parliament_use` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `statrep_co_frt_accountability` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `statrep_de_diac` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `statrep_detroit_mi_frt_weekly` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `statrep_fl_flhsmv_red_light` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `statrep_fr_cnil_utilisation_de` | UNDETERMINED | public_terms_only | MIRROR |  | REFUSED | — (P22+ backlog) |
|  | `statrep_gb_enforcement_action` | UNDETERMINED | public_terms_only | MIRROR |  | REFUSED | — (P22+ backlog) |
|  | `statrep_gb_eng_seven_cctv_june_2026` | UNDETERMINED | public_terms_only | MIRROR |  | REFUSED | — (P22+ backlog) |
|  | `statrep_gb_sct_joint_assurance_review` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `statrep_gb_uk_algorithmic_transparency` | UNDETERMINED | public_terms_only | MIRROR |  | REFUSED | — (P22+ backlog) |
|  | `statrep_hi_judiciary_interception` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `statrep_il_icjia_drone` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `statrep_il_isp_alpr` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `statrep_md_dls_mandated_reports` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `statrep_md_msp_css` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `statrep_me_dps_uav` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `statrep_mn_bca` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `statrep_mn_court_interception` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `statrep_ne_crime_commission_alpr` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `statrep_new_york_ny_nyc_doi_oig` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `statrep_pa_wzssc` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `statrep_seattle_wa_oig` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `statrep_seattle_wa_sdot_ate` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `statrep_tx_ca_nm_ri_fl_il_eff_red_flag` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `statrep_tx_south_padre_island_faa` | UNDETERMINED | public_terms_only | MIRROR |  | REFUSED | — (P22+ backlog) |
|  | `statrep_us_2024_federal_agency` | UNDETERMINED | public_terms_only | MIRROR |  | REFUSED | — (P22+ backlog) |
|  | `statrep_us_dhs_ai_use` | UNDETERMINED | public_terms_only | MIRROR |  | REFUSED | — (P22+ backlog) |
|  | `statrep_us_dhs_privacy_compliance` | UNDETERMINED | public_terms_only | MIRROR |  | REFUSED | — (P22+ backlog) |
|  | `statrep_us_ice_287_monthly` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `statrep_us_ice_287_participating` | UNDETERMINED | public_terms_only | MIRROR |  | REFUSED | — (P22+ backlog) |
|  | `statrep_us_upturn_mass_extraction_2020` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `statrep_us_wiretap_summary_tables` | UNDETERMINED | public_terms_only | MIRROR |  | REFUSED | — (P22+ backlog) |
|  | `statrep_va_rga` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `statrep_va_vscc_alpr` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `statrep_va_vsp_alpr` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `statrep_vt_dps_alpr` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `statrep_vt_vermont_law_enforcement` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `statrep_wa_ago_alpr_registry` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `statrep_wa_watech_frt` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (P22+ backlog) |
|  | `statrep_wa_wtsc_ate` | UNDETERMINED | public_terms_only | MIRROR |  | REFUSED | — (P22+ backlog) |
|  | `surveillance_under_surveillance` | UNDETERMINED | not_contacted | REFERENCE |  | REFUSED | — (P22+ backlog) |
|  | `swagit` | UNDETERMINED | not_contacted | LINK |  | REFUSED | [docs/build/rights/swagit.md](rights/swagit.md) |
|  | `technocarte_update` | UNDETERMINED | not_contacted | LINK |  | REFUSED | — (P22+ backlog) |
|  | `technopolice` | UNDETERMINED | not_contacted | REFERENCE |  | REFUSED | — (P22+ backlog) |
|  | `technopolice_forum` | UNDETERMINED | not_contacted | LINK |  | REFUSED | — (P22+ backlog) |
|  | `ted_eu` | CC-BY-4.0 | public_terms_only | REFERENCE |  | LOADABLE | [docs/build/rights/ted_eu.md](rights/ted_eu.md) |
|  | `tips_usa` | UNDETERMINED | public_terms_only | LINK |  | REFUSED | — (P22+ backlog) |
|  | `uk_surveillance_camera_commissioner` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | DERIVE |  | LOADABLE | — (P22+ backlog) |
|  | `usaspending` | CC0-1.0 | public_terms_only | REFERENCE |  | LOADABLE | [docs/build/rights/usaspending.md](rights/usaspending.md) |
|  | `wigle` | UNDETERMINED | public_terms_only | LINK |  | REFUSED | — (P22+ backlog) |
|  | `wikidata_sparql` | CC0-1.0 | public_terms_only | REFERENCE |  | LOADABLE | [docs/build/rights/wikidata_sparql.md](rights/wikidata_sparql.md) |
|  | `wired_shotspotter_leak` | UNDETERMINED | public_terms_only | LINK |  | REFUSED | — (P22+ backlog) |

_Packets present: 114 (excludes `_TEMPLATE.md`)._ Regenerate: `python .agents/scratch/tools/gen_rights_index.py`.
