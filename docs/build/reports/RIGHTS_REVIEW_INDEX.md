# RIGHTS_REVIEW_INDEX — every registered source's rights/compact/custody/gate state

One row per registered source (SIG-LIC-001, SIG-INGEST-023/038). **Rights state**, **compact status**, and **custody posture** are read from `connectors/src/connectors/data/sources.toml`; **gate** and **flip-ready** are computed by `connectors.review` / `connectors.loader`. The **packet** column follows each row's recorded `review_packet` field — a per-source packet or a batch annex (`docs/build/reports/rights/annex/<batch>/<id>.md`); `— (no packet recorded)` marks a row whose review was never recorded in a packet. `⭐` marks the OKC minimum set (critical-path step 4). Counts are reproduced from `uv run sig-connectors validate` — do not hand-edit; regenerate.

## Counts (from `sig-connectors validate`)

```
registered sources: 590
  rights UNDETERMINED (export gate fails closed): 347
  ingestion_permitted=true: 237
  loadable now (permitted + compact + custody): 237
  flip-ready (rights + compact + custody, flag false): 2
```

**Flip state this regeneration (computed):** 237 sources carry a recorded operator flip (`ingestion_permitted=true` — each under a recorded gate disposition, the `FLIPPED <date> (<gate>)` marker in its notes). 2 source(s) are flip-ready — every gate field green except the flag itself, awaiting only the operator's HG-03 line: `census_gazetteer_tiger`, `natural_earth_10m`. 347 rows carry rights `UNDETERMINED` and fail the export gate closed until a reviewer resolves them. See `docs/build/reports/STAGE0_OUTREACH_RECORD.md` for the compact/outreach state.

## OKC minimum set (critical-path step 4)

`⭐` `deflock_repo`, `ok_statute`, `okc_council`, `okc_procurement`, `okcpd_policy`, `osm_overpass` — government records (R1/R2) + the ODbL/community OSM route. News rows (`journalrecord`, `oklahoman`) are LINK-posture candidates (link out, never re-host).

## All sources

| ⭐ | source id | rights (SPDX) | compact | custody | flip-ready | gate | packet |
|---|---|---|---|---|---|---|---|
|  | `aclu_cell_site_simulators` | UNDETERMINED | not_contacted | REFERENCE |  | REFUSED | — (no packet recorded) |
|  | `aclu_flock_toolkit` | UNDETERMINED | not_contacted | REFERENCE |  | REFUSED | — (no packet recorded) |
|  | `agency_audit_export` | CC0-1.0 | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/agency_audit_export.md](rights/agency_audit_export.md) |
|  | `agenda_az_maricopa_county_board_of` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `agenda_bexar_county_tx_agenda_center` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `agenda_des_moines_ia_council` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `agenda_durham_nc_agenda_center` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `agenda_frisco_tx_onbase_agenda_online` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `agenda_haskell_ar_council` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `agenda_hialeah_fl_agenda_center` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `agenda_jasper_sc_council` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `agenda_jersey_city_nj_digital_agenda` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `agenda_nd_fargo_city_commission_agendas` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `agenda_savannah_ga_2023_05_25` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `agenda_tampa_fl_onbase_agenda_online` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `agenda_tx_dallas_county_commissioners` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `agenda_us_agency_fusus_real` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `alpr_abuse_library` | UNDETERMINED | not_contacted | REFERENCE |  | REFUSED | — (no packet recorded) |
|  | `alpr_accountability_atlas` | UNDETERMINED | not_contacted | REFERENCE |  | REFUSED | — (no packet recorded) |
|  | `alpr_watch` | UNDETERMINED | not_contacted | REFERENCE |  | REFUSED | — (no packet recorded) |
|  | `alpr_watch_code` | UNDETERMINED | not_contacted | REFERENCE |  | REFUSED | — (no packet recorded) |
|  | `alpr_watch_dashboard` | UNDETERMINED | not_contacted | REFERENCE |  | REFUSED | — (no packet recorded) |
|  | `alpr_watch_foia_method` | UNDETERMINED | not_contacted | REFERENCE |  | REFUSED | — (no packet recorded) |
|  | `amsterdam_camerakaart` | UNDETERMINED | public_terms_only | REFERENCE |  | REFUSED | [docs/build/reports/rights/amsterdam_camerakaart.md](rights/amsterdam_camerakaart.md) |
|  | `aspi_mapping_chinas_tech_giants` | LicenseRef-DerivedFacts-Citations | public_terms_only | DERIVE |  | LOADABLE | [docs/build/reports/rights/aspi_mapping_chinas_tech_giants.md](rights/aspi_mapping_chinas_tech_giants.md) |
|  | `atlas_about` | UNDETERMINED | public_terms_only | REFERENCE |  | REFUSED | — (no packet recorded) |
|  | `atlas_data_library` | UNDETERMINED | public_terms_only | LINK |  | REFUSED | — (no packet recorded) |
|  | `atlas_methodology` | UNDETERMINED | public_terms_only | REFERENCE |  | REFUSED | — (no packet recorded) |
|  | `austria_vidreg` | UNDETERMINED | public_terms_only | REFERENCE |  | REFUSED | [docs/build/reports/rights/austria_vidreg.md](rights/austria_vidreg.md) |
|  | `axon_community_connect` | UNDETERMINED | public_terms_only | REFERENCE |  | REFUSED | — (no packet recorded) |
|  | `axon_connect` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `bidnet_direct` | UNDETERMINED | not_contacted | LINK |  | REFUSED | [docs/build/reports/rights/bidnet_direct.md](rights/bidnet_direct.md) |
|  | `boarddocs` | UNDETERMINED | not_contacted | LINK |  | REFUSED | — (no packet recorded) |
|  | `bonfire` | UNDETERMINED | not_contacted | LINK |  | REFUSED | [docs/build/reports/rights/bonfire.md](rights/bonfire.md) |
|  | `buyboard` | UNDETERMINED | public_terms_only | LINK |  | REFUSED | — (no packet recorded) |
|  | `ca_sharing_visualization` | UNDETERMINED | public_terms_only | LINK |  | REFUSED | — (no packet recorded) |
|  | `ca_state_auditor` | UNDETERMINED | not_contacted | REFERENCE |  | REFUSED | [docs/build/reports/rights/ca_state_auditor.md](rights/ca_state_auditor.md) |
|  | `camreg_achd_id` | LicenseRef-PublicRecord-FactualCompilation | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/annex/p2616/camreg_achd_id.md](rights/annex/p2616/camreg_achd_id.md) |
|  | `camreg_act_au` | CC-BY-4.0 | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/camreg_act_au.md](rights/camreg_act_au.md) |
|  | `camreg_alabaster_al_lpr_cameras` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `camreg_amber_kh` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/annex/p2616/camreg_amber_kh.md](rights/annex/p2616/camreg_amber_kh.md) |
|  | `camreg_apram_pt` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/annex/p2616/camreg_apram_pt.md](rights/annex/p2616/camreg_apram_pt.md) |
|  | `camreg_arc_1975641302` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/annex/p2616/camreg_arc_1975641302.md](rights/annex/p2616/camreg_arc_1975641302.md) |
|  | `camreg_arlington_va` | LicenseRef-PublicRecord-FactualCompilation | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/annex/p2616/camreg_arlington_va.md](rights/annex/p2616/camreg_arlington_va.md) |
|  | `camreg_au_ckan_package_search` | UNDETERMINED | public_terms_only | MIRROR |  | REFUSED | — (no packet recorded) |
|  | `camreg_au_nsw_sydney_street_safety` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `camreg_au_qld_towns_cctv_camera_register` | UNDETERMINED | public_terms_only | MIRROR |  | REFUSED | — (no packet recorded) |
|  | `camreg_au_tas_emergency_closed_circuit` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `camreg_au_tas_hobar_security_camera` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `camreg_au_vic_ballarat_cctv_cameras` | UNDETERMINED | public_terms_only | MIRROR |  | REFUSED | — (no packet recorded) |
|  | `camreg_au_vic_geelong_closed_circuit` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `camreg_au_wa_perth_security_cameras` | UNDETERMINED | public_terms_only | MIRROR |  | REFUSED | — (no packet recorded) |
|  | `camreg_austin_tx` | CC0-1.0 | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/camreg_austin_tx.md](rights/camreg_austin_tx.md) |
|  | `camreg_avctransport` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/annex/p2616/camreg_avctransport.md](rights/annex/p2616/camreg_avctransport.md) |
|  | `camreg_az_mesa_city_of_expenditures` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `camreg_azdot_az` | LicenseRef-PublicRecord-FactualCompilation | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/annex/p2616/camreg_azdot_az.md](rights/annex/p2616/camreg_azdot_az.md) |
|  | `camreg_baltimore_atves_md` | LicenseRef-PublicRecord-FactualCompilation | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/annex/p2616/camreg_baltimore_atves_md.md](rights/annex/p2616/camreg_baltimore_atves_md.md) |
|  | `camreg_baltimore_md` | CC-BY-3.0 | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/camreg_baltimore_md.md](rights/camreg_baltimore_md.md) |
|  | `camreg_bangla_bd` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/annex/p2616/camreg_bangla_bd.md](rights/annex/p2616/camreg_bangla_bd.md) |
|  | `camreg_batonrouge_la` | CC0-1.0 | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/camreg_batonrouge_la.md](rights/camreg_batonrouge_la.md) |
|  | `camreg_bedford_gb` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/annex/p2616/camreg_bedford_gb.md](rights/annex/p2616/camreg_bedford_gb.md) |
|  | `camreg_bellevue_wa` | UNDETERMINED | not_contacted | MIRROR |  | REFUSED | [docs/build/reports/rights/camreg_bellevue_wa.md](rights/camreg_bellevue_wa.md) |
|  | `camreg_bettendorf_ia` | LicenseRef-PublicRecord-FactualCompilation | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/annex/p2616/camreg_bettendorf_ia.md](rights/annex/p2616/camreg_bettendorf_ia.md) |
|  | `camreg_bloomington_il_drone_flights` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `camreg_bouhan_jp` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/annex/p2616/camreg_bouhan_jp.md](rights/annex/p2616/camreg_bouhan_jp.md) |
|  | `camreg_brea_ca` | LicenseRef-PublicRecord-FactualCompilation | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/annex/p2616/camreg_brea_ca.md](rights/annex/p2616/camreg_brea_ca.md) |
|  | `camreg_ca_monterey_park_flock_camera` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `camreg_caledon_on` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/annex/p2616/camreg_caledon_on.md](rights/annex/p2616/camreg_caledon_on.md) |
|  | `camreg_calgary_ab` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/annex/p2616/camreg_calgary_ab.md](rights/annex/p2616/camreg_calgary_ab.md) |
|  | `camreg_caloes_ca` | LicenseRef-PublicRecord-FactualCompilation | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/annex/p2616/camreg_caloes_ca.md](rights/annex/p2616/camreg_caloes_ca.md) |
|  | `camreg_camberwell_au` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/annex/p2616/camreg_camberwell_au.md](rights/annex/p2616/camreg_camberwell_au.md) |
|  | `camreg_camilo_schools` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/annex/p2616/camreg_camilo_schools.md](rights/annex/p2616/camreg_camilo_schools.md) |
|  | `camreg_carver_mn` | LicenseRef-PublicRecord-FactualCompilation | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/annex/p2616/camreg_carver_mn.md](rights/annex/p2616/camreg_carver_mn.md) |
|  | `camreg_chattanooga_tn` | LicenseRef-PublicRecord-FactualCompilation | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/annex/p2616/camreg_chattanooga_tn.md](rights/annex/p2616/camreg_chattanooga_tn.md) |
|  | `camreg_chicago_il` | LicenseRef-PublicRecord-FactualCompilation | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/annex/p2616/camreg_chicago_il.md](rights/annex/p2616/camreg_chicago_il.md) |
|  | `camreg_colgis` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/annex/p2616/camreg_colgis.md](rights/annex/p2616/camreg_colgis.md) |
|  | `camreg_cotgeo` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/annex/p2616/camreg_cotgeo.md](rights/annex/p2616/camreg_cotgeo.md) |
|  | `camreg_ctdot_speed_safety` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `camreg_cwarcgis` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/annex/p2616/camreg_cwarcgis.md](rights/annex/p2616/camreg_cwarcgis.md) |
|  | `camreg_dc_ddot_ate` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `camreg_dc_dot_dc` | LicenseRef-PublicRecord-FactualCompilation | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/annex/p2616/camreg_dc_dot_dc.md](rights/annex/p2616/camreg_dc_dot_dc.md) |
|  | `camreg_dc_ovsjg_camera_rebate` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `camreg_de_delaware_checkbook_expenditure` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `camreg_denver_co` | LicenseRef-PublicRecord-FactualCompilation | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/annex/p2616/camreg_denver_co.md](rights/annex/p2616/camreg_denver_co.md) |
|  | `camreg_detroit_mi_project_green_light` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `camreg_donegal_ie` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/annex/p2616/camreg_donegal_ie.md](rights/annex/p2616/camreg_donegal_ie.md) |
|  | `camreg_dover_gb` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/annex/p2616/camreg_dover_gb.md](rights/annex/p2616/camreg_dover_gb.md) |
|  | `camreg_dubuque_ia` | LicenseRef-PublicRecord-FactualCompilation | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/annex/p2616/camreg_dubuque_ia.md](rights/annex/p2616/camreg_dubuque_ia.md) |
|  | `camreg_durham_gb` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/annex/p2616/camreg_durham_gb.md](rights/annex/p2616/camreg_durham_gb.md) |
|  | `camreg_eastdun_gb` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/annex/p2616/camreg_eastdun_gb.md](rights/annex/p2616/camreg_eastdun_gb.md) |
|  | `camreg_ebrgis_la` | LicenseRef-PublicRecord-FactualCompilation | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/annex/p2616/camreg_ebrgis_la.md](rights/annex/p2616/camreg_ebrgis_la.md) |
|  | `camreg_edmonton_ab` | UNDETERMINED | not_contacted | MIRROR |  | REFUSED | [docs/build/reports/rights/camreg_edmonton_ab.md](rights/camreg_edmonton_ab.md) |
|  | `camreg_elgin_il_lpr_cameras` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `camreg_es_md_madrid_c_maras_de` | UNDETERMINED | public_terms_only | MIRROR |  | REFUSED | — (no packet recorded) |
|  | `camreg_esri_dash` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/annex/p2616/camreg_esri_dash.md](rights/annex/p2616/camreg_esri_dash.md) |
|  | `camreg_esriukpolice_gb` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/annex/p2616/camreg_esriukpolice_gb.md](rights/annex/p2616/camreg_esriukpolice_gb.md) |
|  | `camreg_essex_gb` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/annex/p2616/camreg_essex_gb.md](rights/annex/p2616/camreg_essex_gb.md) |
|  | `camreg_eu_eea_data_europa_search_api` | UNDETERMINED | public_terms_only | MIRROR |  | REFUSED | — (no packet recorded) |
|  | `camreg_fdot_flock` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `camreg_firemedic` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/annex/p2616/camreg_firemedic.md](rights/annex/p2616/camreg_firemedic.md) |
|  | `camreg_fl511_fl` | LicenseRef-PublicRecord-FactualCompilation | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/annex/p2616/camreg_fl511_fl.md](rights/annex/p2616/camreg_fl511_fl.md) |
|  | `camreg_fl_broward_county_us_palm_beach` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `camreg_forwardalliance` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/annex/p2616/camreg_forwardalliance.md](rights/annex/p2616/camreg_forwardalliance.md) |
|  | `camreg_fr_92_grand_paris_seine_ouest_vid` | UNDETERMINED | public_terms_only | MIRROR |  | REFUSED | — (no packet recorded) |
|  | `camreg_friendswood_tx` | LicenseRef-PublicRecord-FactualCompilation | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/annex/p2616/camreg_friendswood_tx.md](rights/annex/p2616/camreg_friendswood_tx.md) |
|  | `camreg_ga_brookhaven_flock_camera` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `camreg_ga_flock_cameras_asof` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `camreg_ga_peachtree_corners_flock_camera` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `camreg_ga_savannah_flock_camera` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `camreg_gainesville_fl` | LicenseRef-PublicRecord-FactualCompilation | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/annex/p2616/camreg_gainesville_fl.md](rights/annex/p2616/camreg_gainesville_fl.md) |
|  | `camreg_gastonia_nc_flock_condor_cameras` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `camreg_gb_eng_barnet_cctv_camera` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `camreg_gb_eng_barnet_cctv_traffic` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `camreg_gb_eng_brist_cctv_cameras` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `camreg_gb_eng_ipswich_cctv_camera` | UNDETERMINED | public_terms_only | MIRROR |  | REFUSED | — (no packet recorded) |
|  | `camreg_gb_eng_leice_cctv_cameras` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `camreg_gb_eng_mansf_cctv_cameras` | UNDETERMINED | public_terms_only | MIRROR |  | REFUSED | — (no packet recorded) |
|  | `camreg_gb_eng_north_cctv_cameras` | UNDETERMINED | public_terms_only | MIRROR |  | REFUSED | — (no packet recorded) |
|  | `camreg_gb_eng_runny_cctv_cameras` | UNDETERMINED | public_terms_only | MIRROR |  | REFUSED | — (no packet recorded) |
|  | `camreg_gb_eng_south_skdc_cctv` | UNDETERMINED | public_terms_only | MIRROR |  | REFUSED | — (no packet recorded) |
|  | `camreg_gb_eng_traff_trafford_cctv` | UNDETERMINED | public_terms_only | MIRROR |  | REFUSED | — (no packet recorded) |
|  | `camreg_gb_sct_clackmannanshire_cctv` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `camreg_gb_sct_edinburgh_public_cctv` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `camreg_gedling_gb` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/annex/p2616/camreg_gedling_gb.md](rights/annex/p2616/camreg_gedling_gb.md) |
|  | `camreg_gistel_be` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/annex/p2616/camreg_gistel_be.md](rights/annex/p2616/camreg_gistel_be.md) |
|  | `camreg_glasgow_gb` | OGL-UK-3.0 | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/camreg_glasgow_gb.md](rights/camreg_glasgow_gb.md) |
|  | `camreg_gmh_emc_ga` | LicenseRef-PublicRecord-FactualCompilation | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/annex/p2616/camreg_gmh_emc_ga.md](rights/annex/p2616/camreg_gmh_emc_ga.md) |
|  | `camreg_goldcoast_au` | CC-BY-4.0 | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/camreg_goldcoast_au.md](rights/camreg_goldcoast_au.md) |
|  | `camreg_guildford_gb` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/annex/p2616/camreg_guildford_gb.md](rights/annex/p2616/camreg_guildford_gb.md) |
|  | `camreg_hk_hk` | UNDETERMINED | not_contacted | MIRROR |  | REFUSED | [docs/build/reports/rights/camreg_hk_hk.md](rights/camreg_hk_hk.md) |
|  | `camreg_honolulu_hi` | LicenseRef-PublicRecord-FactualCompilation | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/annex/p2616/camreg_honolulu_hi.md](rights/annex/p2616/camreg_honolulu_hi.md) |
|  | `camreg_howard_md_school_zone_ate` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `camreg_hyattsville_md_cctv_camera_2024` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `camreg_ie_d_dublin_traffic_poles_with` | UNDETERMINED | public_terms_only | MIRROR |  | REFUSED | — (no packet recorded) |
|  | `camreg_il_chicago_violence_reduction` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `camreg_indonesia_id` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/annex/p2616/camreg_indonesia_id.md](rights/annex/p2616/camreg_indonesia_id.md) |
|  | `camreg_infocemosa` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/annex/p2616/camreg_infocemosa.md](rights/annex/p2616/camreg_infocemosa.md) |
|  | `camreg_infraestructura` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/annex/p2616/camreg_infraestructura.md](rights/annex/p2616/camreg_infraestructura.md) |
|  | `camreg_ira` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/annex/p2616/camreg_ira.md](rights/annex/p2616/camreg_ira.md) |
|  | `camreg_it_me_messina_videosorveglianza` | UNDETERMINED | public_terms_only | MIRROR |  | REFUSED | — (no packet recorded) |
|  | `camreg_jcfd3_or` | LicenseRef-PublicRecord-FactualCompilation | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/annex/p2616/camreg_jcfd3_or.md](rights/annex/p2616/camreg_jcfd3_or.md) |
|  | `camreg_jeffersonville_in_flock` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `camreg_jmh_us` | LicenseRef-PublicRecord-FactualCompilation | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/annex/p2616/camreg_jmh_us.md](rights/annex/p2616/camreg_jmh_us.md) |
|  | `camreg_kcmo_mo` | LicenseRef-PublicRecord-FactualCompilation | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/annex/p2616/camreg_kcmo_mo.md](rights/annex/p2616/camreg_kcmo_mo.md) |
|  | `camreg_keizer_or` | LicenseRef-PublicRecord-FactualCompilation | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/annex/p2616/camreg_keizer_or.md](rights/annex/p2616/camreg_keizer_or.md) |
|  | `camreg_kirkland_wa` | LicenseRef-PublicRecord-FactualCompilation | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/annex/p2616/camreg_kirkland_wa.md](rights/annex/p2616/camreg_kirkland_wa.md) |
|  | `camreg_la_east_baton_rouge_parish_flock` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `camreg_la_new_orleans_eye_on` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `camreg_lakeland_fl_red_light` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `camreg_lambeth_gb` | OGL-UK-3.0 | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/camreg_lambeth_gb.md](rights/camreg_lambeth_gb.md) |
|  | `camreg_lawrence_ks` | LicenseRef-PublicRecord-FactualCompilation | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/annex/p2616/camreg_lawrence_ks.md](rights/annex/p2616/camreg_lawrence_ks.md) |
|  | `camreg_leon_county_fl_overwatch_viewer` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `camreg_leon_fl` | LicenseRef-PublicRecord-FactualCompilation | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/annex/p2616/camreg_leon_fl.md](rights/annex/p2616/camreg_leon_fl.md) |
|  | `camreg_lexington_ky` | LicenseRef-PublicRecord-FactualCompilation | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/annex/p2616/camreg_lexington_ky.md](rights/annex/p2616/camreg_lexington_ky.md) |
|  | `camreg_lisburn_gb` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/annex/p2616/camreg_lisburn_gb.md](rights/annex/p2616/camreg_lisburn_gb.md) |
|  | `camreg_lojic_ky` | LicenseRef-PublicRecord-FactualCompilation | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/annex/p2616/camreg_lojic_ky.md](rights/annex/p2616/camreg_lojic_ky.md) |
|  | `camreg_lpd_flock` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/annex/p2616/camreg_lpd_flock.md](rights/annex/p2616/camreg_lpd_flock.md) |
|  | `camreg_ma_massachusetts_capital` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `camreg_manhattan_ks` | LicenseRef-PublicRecord-FactualCompilation | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/annex/p2616/camreg_manhattan_ks.md](rights/annex/p2616/camreg_manhattan_ks.md) |
|  | `camreg_marble_falls_tx_flock_locations` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `camreg_mark43` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/annex/p2616/camreg_mark43.md](rights/annex/p2616/camreg_mark43.md) |
|  | `camreg_massdot_ma` | LicenseRef-PublicRecord-FactualCompilation | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/annex/p2616/camreg_massdot_ma.md](rights/annex/p2616/camreg_massdot_ma.md) |
|  | `camreg_mbrc_au` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/annex/p2616/camreg_mbrc_au.md](rights/annex/p2616/camreg_mbrc_au.md) |
|  | `camreg_mctx_tx` | LicenseRef-PublicRecord-FactualCompilation | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/annex/p2616/camreg_mctx_tx.md](rights/annex/p2616/camreg_mctx_tx.md) |
|  | `camreg_md_opendata` | LicenseRef-PublicRecord-FactualCompilation | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/annex/p2616/camreg_md_opendata.md](rights/annex/p2616/camreg_md_opendata.md) |
|  | `camreg_medford_or_ate` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `camreg_medford_or_drone_deployments_fs` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `camreg_mi_detroit_dpd_shotspotter` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `camreg_milford_ct_flocklprcam` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `camreg_mndot_mn` | LicenseRef-PublicRecord-FactualCompilation | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/annex/p2616/camreg_mndot_mn.md](rights/annex/p2616/camreg_mndot_mn.md) |
|  | `camreg_monmap_mn` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/annex/p2616/camreg_monmap_mn.md](rights/annex/p2616/camreg_monmap_mn.md) |
|  | `camreg_montgomery_md_ate` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `camreg_mueller_de` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/annex/p2616/camreg_mueller_de.md](rights/annex/p2616/camreg_mueller_de.md) |
|  | `camreg_nashville_tn` | LicenseRef-PublicRecord-FactualCompilation | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/annex/p2616/camreg_nashville_tn.md](rights/annex/p2616/camreg_nashville_tn.md) |
|  | `camreg_ne_lincoln_traffic_cameras` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `camreg_nitro` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/annex/p2616/camreg_nitro.md](rights/annex/p2616/camreg_nitro.md) |
|  | `camreg_nj_new_jersey_yourmoney` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `camreg_nola_la` | CC0-1.0 | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/camreg_nola_la.md](rights/camreg_nola_la.md) |
|  | `camreg_nola_safety_la` | LicenseRef-PublicRecord-FactualCompilation | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/annex/p2616/camreg_nola_safety_la.md](rights/annex/p2616/camreg_nola_safety_la.md) |
|  | `camreg_northayrshire_gb` | OGL-UK-3.0 | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/camreg_northayrshire_gb.md](rights/camreg_northayrshire_gb.md) |
|  | `camreg_nottingham_gb` | OGL-UK-3.0 | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/camreg_nottingham_gb.md](rights/camreg_nottingham_gb.md) |
|  | `camreg_nv_las_vegas_us_clark_county` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `camreg_nyc_mta_bus_lane_ate` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `camreg_nzta_nz` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/annex/p2616/camreg_nzta_nz.md](rights/annex/p2616/camreg_nzta_nz.md) |
|  | `camreg_oakland_ca_shotspotter_2013_2015` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `camreg_oem_camera` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/annex/p2616/camreg_oem_camera.md](rights/annex/p2616/camreg_oem_camera.md) |
|  | `camreg_omaha_ne_parks_cameras` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `camreg_oosgis_nl` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/annex/p2616/camreg_oosgis_nl.md](rights/annex/p2616/camreg_oosgis_nl.md) |
|  | `camreg_osm_surveillance` | ODbL-1.0 | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/annex/p2616/camreg_osm_surveillance.md](rights/annex/p2616/camreg_osm_surveillance.md) |
|  | `camreg_ottawa_on` | LicenseRef-Ottawa-ODL-2.0 | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/camreg_ottawa_on.md](rights/camreg_ottawa_on.md) |
|  | `camreg_palmdesert_ca` | LicenseRef-PublicRecord-FactualCompilation | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/annex/p2616/camreg_palmdesert_ca.md](rights/annex/p2616/camreg_palmdesert_ca.md) |
|  | `camreg_peel_on` | LicenseRef-Peel-ODL-1.0 | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/camreg_peel_on.md](rights/camreg_peel_on.md) |
|  | `camreg_penndot_pa` | LicenseRef-PublicRecord-FactualCompilation | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/annex/p2616/camreg_penndot_pa.md](rights/annex/p2616/camreg_penndot_pa.md) |
|  | `camreg_peoria_il_drone_usage` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `camreg_pgcounty_md` | LicenseRef-PublicRecord-FactualCompilation | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/annex/p2616/camreg_pgcounty_md.md](rights/annex/p2616/camreg_pgcounty_md.md) |
|  | `camreg_pipeline_sec` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/annex/p2616/camreg_pipeline_sec.md](rights/annex/p2616/camreg_pipeline_sec.md) |
|  | `camreg_plymouth_gb` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/annex/p2616/camreg_plymouth_gb.md](rights/annex/p2616/camreg_plymouth_gb.md) |
|  | `camreg_polyu_hk` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/annex/p2616/camreg_polyu_hk.md](rights/annex/p2616/camreg_polyu_hk.md) |
|  | `camreg_portland_or` | LicenseRef-PublicRecord-FactualCompilation | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/annex/p2616/camreg_portland_or.md](rights/annex/p2616/camreg_portland_or.md) |
|  | `camreg_pt_11_lisboa_sistema_de` | UNDETERMINED | public_terms_only | MIRROR |  | REFUSED | — (no packet recorded) |
|  | `camreg_pueblo_co_flock` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `camreg_puertogaitan_co` | CC-BY-SA-4.0 | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/camreg_puertogaitan_co.md](rights/camreg_puertogaitan_co.md) |
|  | `camreg_qldc_au` | UNDETERMINED | not_contacted | MIRROR |  | REFUSED | [docs/build/reports/rights/camreg_qldc_au.md](rights/camreg_qldc_au.md) |
|  | `camreg_raleigh_nc` | LicenseRef-PublicRecord-FactualCompilation | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/annex/p2616/camreg_raleigh_nc.md](rights/annex/p2616/camreg_raleigh_nc.md) |
|  | `camreg_ramallah_ps` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/annex/p2616/camreg_ramallah_ps.md](rights/annex/p2616/camreg_ramallah_ps.md) |
|  | `camreg_redmond_wa` | LicenseRef-PublicRecord-FactualCompilation | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/annex/p2616/camreg_redmond_wa.md](rights/annex/p2616/camreg_redmond_wa.md) |
|  | `camreg_riyadh_sa` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/annex/p2616/camreg_riyadh_sa.md](rights/annex/p2616/camreg_riyadh_sa.md) |
|  | `camreg_rochester_ny` | ODbL-1.0 | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/camreg_rochester_ny.md](rights/camreg_rochester_ny.md) |
|  | `camreg_rocky_mount_nc_lpr_cameras` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `camreg_salisbury_nc` | LicenseRef-PublicRecord-FactualCompilation | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/annex/p2616/camreg_salisbury_nc.md](rights/annex/p2616/camreg_salisbury_nc.md) |
|  | `camreg_santa_fe_nm_park_cameras` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `camreg_sarasota_fl` | LicenseRef-PublicRecord-FactualCompilation | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/annex/p2616/camreg_sarasota_fl.md](rights/annex/p2616/camreg_sarasota_fl.md) |
|  | `camreg_seattle_wa` | LicenseRef-PublicRecord-FactualCompilation | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/annex/p2616/camreg_seattle_wa.md](rights/annex/p2616/camreg_seattle_wa.md) |
|  | `camreg_sensenet` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/annex/p2616/camreg_sensenet.md](rights/annex/p2616/camreg_sensenet.md) |
|  | `camreg_sheffield_gb` | OGL-UK-3.0 | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/camreg_sheffield_gb.md](rights/camreg_sheffield_gb.md) |
|  | `camreg_shelbyville_tn_flock_cameras` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `camreg_si_048_ko_evje_videonadzor_na` | UNDETERMINED | public_terms_only | MIRROR |  | REFUSED | — (no packet recorded) |
|  | `camreg_siouxfalls_sd` | CC-BY-4.0 | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/camreg_siouxfalls_sd.md](rights/camreg_siouxfalls_sd.md) |
|  | `camreg_smart_sky` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/annex/p2616/camreg_smart_sky.md](rights/annex/p2616/camreg_smart_sky.md) |
|  | `camreg_south_fulton_ga_lpr_cameras` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `camreg_squan` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/annex/p2616/camreg_squan.md](rights/annex/p2616/camreg_squan.md) |
|  | `camreg_stalbert_ab` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/annex/p2616/camreg_stalbert_ab.md](rights/annex/p2616/camreg_stalbert_ab.md) |
|  | `camreg_stanford_us` | LicenseRef-PublicRecord-FactualCompilation | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/annex/p2616/camreg_stanford_us.md](rights/annex/p2616/camreg_stanford_us.md) |
|  | `camreg_suffolk_ny_red_light` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `camreg_surrey_bc` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/annex/p2616/camreg_surrey_bc.md](rights/annex/p2616/camreg_surrey_bc.md) |
|  | `camreg_tacoma_wa_ate` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `camreg_temecula_ca_flock_wfl1` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `camreg_thailand_th` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/annex/p2616/camreg_thailand_th.md](rights/annex/p2616/camreg_thailand_th.md) |
|  | `camreg_thomasville_ga_flock_location` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `camreg_toronto_on` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/annex/p2616/camreg_toronto_on.md](rights/annex/p2616/camreg_toronto_on.md) |
|  | `camreg_townofws` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/annex/p2616/camreg_townofws.md](rights/annex/p2616/camreg_townofws.md) |
|  | `camreg_trafficops_ca` | LicenseRef-PublicRecord-FactualCompilation | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/annex/p2616/camreg_trafficops_ca.md](rights/annex/p2616/camreg_trafficops_ca.md) |
|  | `camreg_tribal_all_leaders_directory` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `camreg_trpa_us` | LicenseRef-PublicRecord-FactualCompilation | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/annex/p2616/camreg_trpa_us.md](rights/annex/p2616/camreg_trpa_us.md) |
|  | `camreg_tulane_la` | LicenseRef-PublicRecord-FactualCompilation | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/annex/p2616/camreg_tulane_la.md](rights/annex/p2616/camreg_tulane_la.md) |
|  | `camreg_txdot_rep_tx` | LicenseRef-PublicRecord-FactualCompilation | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/annex/p2616/camreg_txdot_rep_tx.md](rights/annex/p2616/camreg_txdot_rep_tx.md) |
|  | `camreg_ua_18_korosten` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `camreg_uchicago` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/annex/p2616/camreg_uchicago.md](rights/annex/p2616/camreg_uchicago.md) |
|  | `camreg_ucsd` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/annex/p2616/camreg_ucsd.md](rights/annex/p2616/camreg_ucsd.md) |
|  | `camreg_ukm_my` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/annex/p2616/camreg_ukm_my.md](rights/annex/p2616/camreg_ukm_my.md) |
|  | `camreg_umbc_md` | LicenseRef-PublicRecord-FactualCompilation | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/annex/p2616/camreg_umbc_md.md](rights/annex/p2616/camreg_umbc_md.md) |
|  | `camreg_und_001` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/annex/p2616/camreg_und_001.md](rights/annex/p2616/camreg_und_001.md) |
|  | `camreg_und_002` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/annex/p2616/camreg_und_002.md](rights/annex/p2616/camreg_und_002.md) |
|  | `camreg_und_003` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/annex/p2616/camreg_und_003.md](rights/annex/p2616/camreg_und_003.md) |
|  | `camreg_und_004` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/annex/p2616/camreg_und_004.md](rights/annex/p2616/camreg_und_004.md) |
|  | `camreg_und_005` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/annex/p2616/camreg_und_005.md](rights/annex/p2616/camreg_und_005.md) |
|  | `camreg_und_006` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/annex/p2616/camreg_und_006.md](rights/annex/p2616/camreg_und_006.md) |
|  | `camreg_und_007` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/annex/p2616/camreg_und_007.md](rights/annex/p2616/camreg_und_007.md) |
|  | `camreg_und_008` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/annex/p2616/camreg_und_008.md](rights/annex/p2616/camreg_und_008.md) |
|  | `camreg_und_009` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/annex/p2616/camreg_und_009.md](rights/annex/p2616/camreg_und_009.md) |
|  | `camreg_und_010` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/annex/p2616/camreg_und_010.md](rights/annex/p2616/camreg_und_010.md) |
|  | `camreg_und_011` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/annex/p2616/camreg_und_011.md](rights/annex/p2616/camreg_und_011.md) |
|  | `camreg_und_012` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/annex/p2616/camreg_und_012.md](rights/annex/p2616/camreg_und_012.md) |
|  | `camreg_und_013` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/annex/p2616/camreg_und_013.md](rights/annex/p2616/camreg_und_013.md) |
|  | `camreg_und_014` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/annex/p2616/camreg_und_014.md](rights/annex/p2616/camreg_und_014.md) |
|  | `camreg_und_015` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/annex/p2616/camreg_und_015.md](rights/annex/p2616/camreg_und_015.md) |
|  | `camreg_und_016` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/annex/p2616/camreg_und_016.md](rights/annex/p2616/camreg_und_016.md) |
|  | `camreg_und_017` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/annex/p2616/camreg_und_017.md](rights/annex/p2616/camreg_und_017.md) |
|  | `camreg_und_018` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/annex/p2616/camreg_und_018.md](rights/annex/p2616/camreg_und_018.md) |
|  | `camreg_und_019` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/annex/p2616/camreg_und_019.md](rights/annex/p2616/camreg_und_019.md) |
|  | `camreg_und_020` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/annex/p2616/camreg_und_020.md](rights/annex/p2616/camreg_und_020.md) |
|  | `camreg_und_021` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/annex/p2616/camreg_und_021.md](rights/annex/p2616/camreg_und_021.md) |
|  | `camreg_und_022` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/annex/p2616/camreg_und_022.md](rights/annex/p2616/camreg_und_022.md) |
|  | `camreg_und_023` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/annex/p2616/camreg_und_023.md](rights/annex/p2616/camreg_und_023.md) |
|  | `camreg_und_024` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/annex/p2616/camreg_und_024.md](rights/annex/p2616/camreg_und_024.md) |
|  | `camreg_und_025` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/annex/p2616/camreg_und_025.md](rights/annex/p2616/camreg_und_025.md) |
|  | `camreg_und_026` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/annex/p2616/camreg_und_026.md](rights/annex/p2616/camreg_und_026.md) |
|  | `camreg_und_027` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/annex/p2616/camreg_und_027.md](rights/annex/p2616/camreg_und_027.md) |
|  | `camreg_und_028` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/annex/p2616/camreg_und_028.md](rights/annex/p2616/camreg_und_028.md) |
|  | `camreg_und_029` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/annex/p2616/camreg_und_029.md](rights/annex/p2616/camreg_und_029.md) |
|  | `camreg_univmb_mb` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/annex/p2616/camreg_univmb_mb.md](rights/annex/p2616/camreg_univmb_mb.md) |
|  | `camreg_uofmd_md` | LicenseRef-PublicRecord-FactualCompilation | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/annex/p2616/camreg_uofmd_md.md](rights/annex/p2616/camreg_uofmd_md.md) |
|  | `camreg_us_agency_drone_flight` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `camreg_us_agency_published_flock` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `camreg_us_ate_camera_location_and_per` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `camreg_us_body_worn_camera` | UNDETERMINED | public_terms_only | MIRROR |  | REFUSED | — (no packet recorded) |
|  | `camreg_us_municipal_contract_expenditure` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `camreg_us_nces_school_survey_on_crime` | UNDETERMINED | public_terms_only | MIRROR |  | REFUSED | — (no packet recorded) |
|  | `camreg_us_ny_001` | LicenseRef-PublicRecord-FactualCompilation | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/annex/p2616/camreg_us_ny_001.md](rights/annex/p2616/camreg_us_ny_001.md) |
|  | `camreg_us_ny_002` | LicenseRef-PublicRecord-FactualCompilation | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/annex/p2616/camreg_us_ny_002.md](rights/annex/p2616/camreg_us_ny_002.md) |
|  | `camreg_us_socrata_hosted_vendor` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `camreg_va_pittsylvania_county_stationary` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `camreg_va_prince_william_county` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `camreg_vancouver_bc` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/annex/p2616/camreg_vancouver_bc.md](rights/annex/p2616/camreg_vancouver_bc.md) |
|  | `camreg_wa_washington_state_open` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `camreg_washington_dc` | CC-BY-4.0 | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/camreg_washington_dc.md](rights/camreg_washington_dc.md) |
|  | `camreg_webappfme` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/annex/p2616/camreg_webappfme.md](rights/annex/p2616/camreg_webappfme.md) |
|  | `camreg_wellington_nz` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/annex/p2616/camreg_wellington_nz.md](rights/annex/p2616/camreg_wellington_nz.md) |
|  | `camreg_wim_camera` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/annex/p2616/camreg_wim_camera.md](rights/annex/p2616/camreg_wim_camera.md) |
|  | `camreg_winnipeg_mb` | OGL-Canada-2.0 | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/camreg_winnipeg_mb.md](rights/camreg_winnipeg_mb.md) |
|  | `camreg_yline` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/annex/p2616/camreg_yline.md](rights/annex/p2616/camreg_yline.md) |
|  | `camreg_york_gb` | OGL-UK-3.0 | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/camreg_york_gb.md](rights/camreg_york_gb.md) |
|  | `camreg_york_on` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/annex/p2616/camreg_york_on.md](rights/annex/p2616/camreg_york_on.md) |
|  | `camreg_yorku` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/annex/p2616/camreg_yorku.md](rights/annex/p2616/camreg_yorku.md) |
|  | `carnegie_ai_gsi` | LicenseRef-DerivedFacts-Citations | public_terms_only | DERIVE |  | LOADABLE | [docs/build/reports/rights/carnegie_ai_gsi.md](rights/carnegie_ai_gsi.md) |
|  | `ccops_anchorage_ak` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `ccops_austin_tx` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `ccops_baltimore` | UNDETERMINED | public_terms_only | REFERENCE |  | REFUSED | [docs/build/reports/rights/ccops_baltimore.md](rights/ccops_baltimore.md) |
|  | `ccops_berkeley` | UNDETERMINED | public_terms_only | REFERENCE |  | REFUSED | [docs/build/reports/rights/ccops_berkeley.md](rights/ccops_berkeley.md) |
|  | `ccops_boston` | UNDETERMINED | public_terms_only | REFERENCE |  | REFUSED | [docs/build/reports/rights/ccops_boston.md](rights/ccops_boston.md) |
|  | `ccops_ca_calistoga_police_department` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `ccops_ca_pinole_police_department` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `ccops_ca_san_diego_privacy_advisory` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `ccops_ca_san_diego_sunshine_act_goods` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `ccops_cambridge` | LicenseRef-PublicRecord-FactualCompilation | public_terms_only | REFERENCE |  | LOADABLE | [docs/build/reports/rights/annex/p293/ccops_cambridge.md](rights/annex/p293/ccops_cambridge.md) |
|  | `ccops_columbia_mo` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `ccops_davis` | UNDETERMINED | public_terms_only | REFERENCE |  | REFUSED | [docs/build/reports/rights/ccops_davis.md](rights/ccops_davis.md) |
|  | `ccops_dayton_oh` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `ccops_gb_eng_barnet_traffic_cctv` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `ccops_grand_rapids` | UNDETERMINED | public_terms_only | REFERENCE |  | REFUSED | [docs/build/reports/rights/ccops_grand_rapids.md](rights/ccops_grand_rapids.md) |
|  | `ccops_hi_honolulu_police_department` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `ccops_il_chicago_oig_shotspotter` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `ccops_iso_au_privacy_commissioner` | UNDETERMINED | public_terms_only | MIRROR |  | REFUSED | — (no packet recorded) |
|  | `ccops_it_tn_trento_provvedimento_dell_11` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `ccops_mi_wayne_county_commission` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `ccops_mn_dayton_police_department` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `ccops_mo_st_louis_fy21_spi_shotspotter` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `ccops_nashville` | UNDETERMINED | public_terms_only | REFERENCE |  | REFUSED | [docs/build/reports/rights/ccops_nashville.md](rights/ccops_nashville.md) |
|  | `ccops_nc_charlotte_mecklenburg_police` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `ccops_nc_elizabeth_city_police` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `ccops_ny_new_york_nyc_comptroller` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `ccops_nyc_post` | LicenseRef-DerivedFacts-Citations | public_terms_only | REFERENCE |  | LOADABLE | [docs/build/reports/rights/ccops_nyc_post.md](rights/ccops_nyc_post.md) |
|  | `ccops_oakland` | LicenseRef-PublicRecord-FactualCompilation | public_terms_only | REFERENCE |  | LOADABLE | [docs/build/reports/rights/annex/p293/ccops_oakland.md](rights/annex/p293/ccops_oakland.md) |
|  | `ccops_oh_cincinnati_police_department` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `ccops_ok_oklahoma_city_okc_flock_council` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `ccops_ok_tulsa_flock_policies` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `ccops_ordinance_disclosures` | UNDETERMINED | public_terms_only | MIRROR |  | REFUSED | — (no packet recorded) |
|  | `ccops_ri_narragansett_police_camera` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `ccops_san_diego_ca` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `ccops_san_francisco_bay_ca` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `ccops_san_jose_ca` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `ccops_santa_clara_county_ca` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `ccops_seattle` | LicenseRef-DerivedFacts-Citations | public_terms_only | REFERENCE |  | LOADABLE | [docs/build/reports/rights/ccops_seattle.md](rights/ccops_seattle.md) |
|  | `ccops_sf` | LicenseRef-DerivedFacts-Citations | public_terms_only | REFERENCE |  | LOADABLE | [docs/build/reports/rights/ccops_sf.md](rights/ccops_sf.md) |
|  | `ccops_si_085_novo_mesto_evidenca_o` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `ccops_somerville` | LicenseRef-PublicRecord-FactualCompilation | public_terms_only | REFERENCE |  | LOADABLE | [docs/build/reports/rights/annex/p293/ccops_somerville.md](rights/annex/p293/ccops_somerville.md) |
|  | `ccops_st_louis_mo` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `census_gazetteer_tiger` | CC0-1.0 | public_terms_only | MIRROR | yes | flip-ready | [docs/build/reports/rights/census_gazetteer_tiger.md](rights/census_gazetteer_tiger.md) |
|  | `census_geocoder` | UNDETERMINED | public_terms_only | REFERENCE |  | REFUSED | — (no packet recorded) |
|  | `civicclerk` | CC0-1.0 | public_terms_only | REFERENCE |  | LOADABLE | [docs/build/reports/rights/civicclerk.md](rights/civicclerk.md) |
|  | `civicplus` | UNDETERMINED | not_contacted | LINK |  | REFUSED | — (no packet recorded) |
|  | `congress_gov` | CC0-1.0 | public_terms_only | REFERENCE |  | LOADABLE | [docs/build/reports/rights/congress_gov.md](rights/congress_gov.md) |
|  | `courtlistener_recap` | UNDETERMINED | public_terms_only | REFERENCE |  | REFUSED | [docs/build/reports/rights/courtlistener_recap.md](rights/courtlistener_recap.md) |
|  | `declarationcamera_be` | LicenseRef-DerivedFacts-Citations | public_terms_only | DERIVE |  | LOADABLE | [docs/build/reports/rights/declarationcamera_be.md](rights/declarationcamera_be.md) |
|  | `decp_fr` | etalab-2.0 | public_terms_only | REFERENCE |  | LOADABLE | [docs/build/reports/rights/decp_fr.md](rights/decp_fr.md) |
|  | `deflock` | UNDETERMINED | not_contacted | REFERENCE |  | REFUSED | [docs/build/reports/rights/deflock.md](rights/deflock.md) |
|  | `deflock_app_repo` | AGPL-3.0 | public_terms_only | REFERENCE |  | LOADABLE | [docs/build/reports/rights/deflock_app_repo.md](rights/deflock_app_repo.md) |
| ⭐ | `deflock_repo` | MIT | public_terms_only | REFERENCE |  | LOADABLE | [docs/build/reports/rights/deflock_repo.md](rights/deflock_repo.md) |
|  | `demandstar` | UNDETERMINED | not_contacted | LINK |  | REFUSED | [docs/build/reports/rights/demandstar.md](rights/demandstar.md) |
|  | `denmark_politi_cctv` | UNDETERMINED | public_terms_only | REFERENCE |  | REFUSED | [docs/build/reports/rights/denmark_politi_cctv.md](rights/denmark_politi_cctv.md) |
|  | `dhs_fusion_center_assessments` | CC0-1.0 | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/annex/p293/dhs_fusion_center_assessments.md](rights/annex/p293/dhs_fusion_center_assessments.md) |
|  | `dhs_fusion_centers` | UNDETERMINED | public_terms_only | REFERENCE |  | REFUSED | — (no packet recorded) |
|  | `dhs_oig_reports` | CC0-1.0 | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/annex/p293/dhs_oig_reports.md](rights/annex/p293/dhs_oig_reports.md) |
|  | `documentcloud` | UNDETERMINED | public_terms_only | REFERENCE |  | REFUSED | [docs/build/reports/rights/documentcloud.md](rights/documentcloud.md) |
|  | `dossier_okc` | UNDETERMINED | not_contacted | REFERENCE |  | REFUSED | — (no packet recorded) |
|  | `dossier_san_diego` | UNDETERMINED | not_contacted | REFERENCE |  | REFUSED | — (no packet recorded) |
|  | `dossier_tulsa` | UNDETERMINED | not_contacted | REFERENCE |  | REFUSED | — (no packet recorded) |
|  | `dot_511_al` | LicenseRef-PublicRecord-FactualCompilation | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/annex/p2616/dot_511_al.md](rights/annex/p2616/dot_511_al.md) |
|  | `dot_511_dc` | CC0-1.0 | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/dot_511_dc.md](rights/dot_511_dc.md) |
|  | `dot_511_de` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `dot_511_ga` | LicenseRef-PublicRecord-FactualCompilation | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/annex/p2616/dot_511_ga.md](rights/annex/p2616/dot_511_ga.md) |
|  | `dot_511_gb` | UNDETERMINED | public_terms_only | MIRROR |  | REFUSED | — (no packet recorded) |
|  | `dot_511_ia` | CC-BY-4.0 | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/dot_511_ia.md](rights/dot_511_ia.md) |
|  | `dot_511_id` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `dot_511_il` | CC-BY-SA-2.0 | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/dot_511_il.md](rights/dot_511_il.md) |
|  | `dot_511_ky` | CC0-1.0 | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/dot_511_ky.md](rights/dot_511_ky.md) |
|  | `dot_511_la` | LicenseRef-PublicRecord-FactualCompilation | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/annex/p2616/dot_511_la.md](rights/annex/p2616/dot_511_la.md) |
|  | `dot_511_md` | LicenseRef-PublicRecord-FactualCompilation | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/annex/p2616/dot_511_md.md](rights/annex/p2616/dot_511_md.md) |
|  | `dot_511_mi` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `dot_511_mo` | CC0-1.0 | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/dot_511_mo.md](rights/dot_511_mo.md) |
|  | `dot_511_nc` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `dot_511_nm` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `dot_511_nv` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `dot_511_or` | CC0-1.0 | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/dot_511_or.md](rights/dot_511_or.md) |
|  | `dot_511_tx` | UNDETERMINED | not_contacted | MIRROR |  | REFUSED | [docs/build/reports/rights/dot_511_tx.md](rights/dot_511_tx.md) |
|  | `dot_511_ut` | CC0-1.0 | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/dot_511_ut.md](rights/dot_511_ut.md) |
|  | `dot_511_vt` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `dot_511_wa` | CC0-1.0 | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/dot_511_wa.md](rights/dot_511_wa.md) |
|  | `dot_511_wv` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `drivers_against_flock` | UNDETERMINED | not_contacted | LINK |  | REFUSED | — (no packet recorded) |
|  | `eff_atlas_of_surveillance` | CC-BY-4.0 | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/eff_atlas_of_surveillance.md](rights/eff_atlas_of_surveillance.md) |
|  | `eff_copyright` | UNDETERMINED | public_terms_only | REFERENCE |  | REFUSED | — (no packet recorded) |
|  | `eff_data_driven` | CC-BY-4.0 | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/eff_data_driven.md](rights/eff_data_driven.md) |
|  | `eff_street_level_surveillance` | UNDETERMINED | public_terms_only | REFERENCE |  | REFUSED | — (no packet recorded) |
|  | `equalis_group` | UNDETERMINED | public_terms_only | LINK |  | REFUSED | — (no packet recorded) |
|  | `escribe` | CC0-1.0 | public_terms_only | REFERENCE |  | LOADABLE | [docs/build/reports/rights/escribe.md](rights/escribe.md) |
|  | `eyes_off_cedar_rapids` | UNDETERMINED | not_contacted | LINK |  | REFUSED | — (no packet recorded) |
|  | `eyes_off_eugene` | CC0-1.0 | not_contacted | REFERENCE |  | REFUSED | — (no packet recorded) |
|  | `eyes_on_flock` | CC-BY-SA-4.0 | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/eyes_on_flock.md](rights/eyes_on_flock.md) |
|  | `eyes_on_flock_description` | UNDETERMINED | public_terms_only | LINK |  | REFUSED | — (no packet recorded) |
|  | `faa_drone_waivers` | UNDETERMINED | public_terms_only | REFERENCE |  | REFUSED | — (no packet recorded) |
|  | `facial_recognition_world_map` | LicenseRef-DerivedFacts-Citations | public_terms_only | DERIVE |  | LOADABLE | [docs/build/reports/rights/facial_recognition_world_map.md](rights/facial_recognition_world_map.md) |
|  | `fbi_cde_agency_registry` | CC0-1.0 | public_terms_only | REFERENCE |  | LOADABLE | [docs/build/reports/rights/fbi_cde_agency_registry.md](rights/fbi_cde_agency_registry.md) |
|  | `fema_hsgp_allocations` | CC0-1.0 | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/annex/p293/fema_hsgp_allocations.md](rights/annex/p293/fema_hsgp_allocations.md) |
|  | `flock_ajith_fyi` | UNDETERMINED | not_contacted | LINK |  | REFUSED | — (no packet recorded) |
|  | `flock_api_terms` | UNDETERMINED | public_terms_only | REFERENCE |  | REFUSED | — (no packet recorded) |
|  | `flock_finder` | MIT | public_terms_only | REFERENCE |  | LOADABLE | [docs/build/reports/rights/flock_finder.md](rights/flock_finder.md) |
|  | `flock_transparency_portals` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `flock_you` | UNDETERMINED | not_contacted | REFERENCE |  | REFUSED | — (no packet recorded) |
|  | `flockhopper3_deflock_data` | UNDETERMINED | not_contacted | LINK |  | REFUSED | — (no packet recorded) |
|  | `flockreporter` | UNDETERMINED | no_response | LINK |  | REFUSED | — (no packet recorded) |
|  | `foiaxpress` | UNDETERMINED | not_contacted | LINK |  | REFUSED | — (no packet recorded) |
|  | `footnote4a` | UNDETERMINED | not_contacted | LINK |  | REFUSED | — (no packet recorded) |
|  | `future_statutory_disclosure_2027` | UNDETERMINED | not_contacted | MIRROR |  | REFUSED | — (no packet recorded) |
|  | `future_statutory_disclosure_al` | UNDETERMINED | not_contacted | MIRROR |  | REFUSED | — (no packet recorded) |
|  | `future_statutory_disclosure_ar` | UNDETERMINED | not_contacted | MIRROR |  | REFUSED | — (no packet recorded) |
|  | `future_statutory_disclosure_mn` | UNDETERMINED | not_contacted | MIRROR |  | REFUSED | — (no packet recorded) |
|  | `future_statutory_disclosure_nm` | UNDETERMINED | not_contacted | MIRROR |  | REFUSED | — (no packet recorded) |
|  | `future_statutory_disclosure_ut` | UNDETERMINED | not_contacted | MIRROR |  | REFUSED | — (no packet recorded) |
|  | `future_statutory_disclosure_va` | UNDETERMINED | not_contacted | MIRROR |  | REFUSED | — (no packet recorded) |
|  | `gao_surveillance_reports` | CC0-1.0 | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/annex/p293/gao_surveillance_reports.md](rights/annex/p293/gao_surveillance_reports.md) |
|  | `gleif` | CC0-1.0 | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/gleif.md](rights/gleif.md) |
|  | `govqa` | UNDETERMINED | not_contacted | LINK |  | REFUSED | — (no packet recorded) |
|  | `govspend` | UNDETERMINED | public_terms_only | LINK |  | REFUSED | — (no packet recorded) |
|  | `granicus` | UNDETERMINED | not_contacted | LINK |  | REFUSED | — (no packet recorded) |
|  | `grant_al_adeca_psn` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `grant_ca_bscc_ort` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `grant_fl_senate_lfir` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `grant_il_illinois_gata_csfa` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `grant_ma_massachusetts_law_enforcement` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `grant_nj_oag_bwc` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `grant_oh_ohio_criminal_justice` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `grant_ok_dac_jag_lle` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `grant_ok_safe_oklahoma_grant` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `grant_tx_txdmv_mvcpa` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `grant_us_doj_cops_technology` | UNDETERMINED | public_terms_only | MIRROR |  | REFUSED | — (no packet recorded) |
|  | `gsa` | UNDETERMINED | public_terms_only | LINK |  | REFUSED | — (no packet recorded) |
|  | `guardian_flock_cameras` | UNDETERMINED | public_terms_only | LINK |  | REFUSED | — (no packet recorded) |
|  | `have_i_been_flocked` | UNDETERMINED | not_contacted | REFERENCE |  | REFUSED | — (no packet recorded) |
|  | `hgacbuy` | UNDETERMINED | public_terms_only | LINK |  | REFUSED | — (no packet recorded) |
|  | `hibf_audit_log_guide` | UNDETERMINED | not_contacted | REFERENCE |  | REFUSED | — (no packet recorded) |
|  | `hibf_methodology` | UNDETERMINED | not_contacted | REFERENCE |  | REFUSED | — (no packet recorded) |
|  | `internet_archive_wayback` | UNDETERMINED | public_terms_only | REFERENCE |  | REFUSED | — (no packet recorded) |
|  | `iqm2` | UNDETERMINED | not_contacted | LINK |  | REFUSED | — (no packet recorded) |
| · | `journalrecord` | UNDETERMINED | public_terms_only | LINK |  | REFUSED | [docs/build/reports/rights/journalrecord.md](rights/journalrecord.md) |
|  | `justfoia` | UNDETERMINED | not_contacted | LINK |  | REFUSED | — (no packet recorded) |
|  | `la_city_clerk_cfms` | UNDETERMINED | not_contacted | LINK |  | REFUSED | — (no packet recorded) |
|  | `la_quadrature_du_net` | UNDETERMINED | not_contacted | LINK |  | REFUSED | — (no packet recorded) |
|  | `leaic_crosswalk` | UNDETERMINED | public_terms_only | MIRROR |  | REFUSED | — (no packet recorded) |
|  | `legis_ca_gov_code_53166` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `legis_gu_governor` | UNDETERMINED | public_terms_only | MIRROR |  | REFUSED | — (no packet recorded) |
|  | `legis_ie_rs_general_scheme` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `legis_pr_pc0489_ley_del` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `legis_pr_pc0560_plan_de` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `legis_pr_rc0740_investigaci_sobre` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `legis_pr_rc0787_resoluci_de` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `legis_pr_rcs0198_resoluci_conjunta` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `legis_pr_rs0604_resoluci_del` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `legis_pr_sistema_nico_de` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `legis_tribal_tohono_oodham_notice` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `legis_us_dhs_sorn_plate_data` | UNDETERMINED | public_terms_only | MIRROR |  | REFUSED | — (no packet recorded) |
|  | `legis_us_federal_register_api` | UNDETERMINED | public_terms_only | MIRROR |  | REFUSED | — (no packet recorded) |
|  | `legis_vi_legislature_virgin_islands` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `legistar` | CC0-1.0 | public_terms_only | REFERENCE |  | LOADABLE | [docs/build/reports/rights/legistar.md](rights/legistar.md) |
|  | `madada` | LicenseRef-DerivedFacts-Citations | public_terms_only | DERIVE |  | LOADABLE | [docs/build/reports/rights/madada.md](rights/madada.md) |
|  | `monahan_grounding_the_flock` | UNDETERMINED | public_terms_only | LINK |  | REFUSED | — (no packet recorded) |
|  | `muckrock` | LicenseRef-MuckRock-API-ToS | public_terms_only | REFERENCE |  | LOADABLE | [docs/build/reports/rights/muckrock.md](rights/muckrock.md) |
|  | `muckrock_public` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | [docs/build/reports/rights/muckrock.md](rights/muckrock.md) |
|  | `naspo_valuepoint` | UNDETERMINED | public_terms_only | LINK |  | REFUSED | — (no packet recorded) |
|  | `natural_earth_10m` | CC0-1.0 | public_terms_only | MIRROR | yes | flip-ready | [docs/build/reports/rights/natural_earth_10m.md](rights/natural_earth_10m.md) |
|  | `nces_ipeds_ntd_cms` | UNDETERMINED | public_terms_only | MIRROR |  | REFUSED | — (no packet recorded) |
|  | `nextrequest` | UNDETERMINED | public_terms_only | REFERENCE |  | REFUSED | — (no packet recorded) |
|  | `novusagenda` | UNDETERMINED | not_contacted | LINK |  | REFUSED | — (no packet recorded) |
|  | `ok_dac_uved` | UNDETERMINED | not_contacted | REFERENCE |  | REFUSED | [docs/build/reports/rights/ok_dac_uved.md](rights/ok_dac_uved.md) |
|  | `ok_omes_contracts` | UNDETERMINED | not_contacted | REFERENCE |  | REFUSED | [docs/build/reports/rights/ok_omes_contracts.md](rights/ok_omes_contracts.md) |
| ⭐ | `ok_statute` | CC0-1.0 | public_terms_only | REFERENCE |  | LOADABLE | [docs/build/reports/rights/ok_statute.md](rights/ok_statute.md) |
| ⭐ | `okc_council` | CC0-1.0 | public_terms_only | REFERENCE |  | LOADABLE | [docs/build/reports/rights/okc_council.md](rights/okc_council.md) |
| ⭐ | `okc_procurement` | CC0-1.0 | public_terms_only | REFERENCE |  | LOADABLE | [docs/build/reports/rights/okc_procurement.md](rights/okc_procurement.md) |
| ⭐ | `okcpd_policy` | CC0-1.0 | public_terms_only | REFERENCE |  | LOADABLE | [docs/build/reports/rights/okcpd_policy.md](rights/okcpd_policy.md) |
| · | `oklahoman` | UNDETERMINED | public_terms_only | LINK |  | REFUSED | [docs/build/reports/rights/oklahoman.md](rights/oklahoman.md) |
|  | `omnia_partners` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `opengov_procurement` | UNDETERMINED | not_contacted | LINK |  | REFUSED | [docs/build/reports/rights/opengov_procurement.md](rights/opengov_procurement.md) |
|  | `openstates` | CC0-1.0 | public_terms_only | REFERENCE |  | LOADABLE | [docs/build/reports/rights/openstates.md](rights/openstates.md) |
|  | `osm_automated_edits_coc` | ODbL-1.0 | public_terms_only | REFERENCE |  | LOADABLE | [docs/build/reports/rights/osm_automated_edits_coc.md](rights/osm_automated_edits_coc.md) |
|  | `osm_copyright` | ODbL-1.0 | public_terms_only | REFERENCE |  | LOADABLE | [docs/build/reports/rights/osm_copyright.md](rights/osm_copyright.md) |
|  | `osm_element_history` | ODbL-1.0 | public_terms_only | REFERENCE |  | LOADABLE | [docs/build/reports/rights/osm_element_history.md](rights/osm_element_history.md) |
| ⭐ | `osm_overpass` | ODbL-1.0 | public_terms_only | REFERENCE |  | LOADABLE | [docs/build/reports/rights/osm_overpass.md](rights/osm_overpass.md) |
|  | `osm_replication` | ODbL-1.0 | public_terms_only | REFERENCE |  | LOADABLE | [docs/build/reports/rights/osm_replication.md](rights/osm_replication.md) |
|  | `osm_surveillance_tagging` | ODbL-1.0 | public_terms_only | REFERENCE |  | LOADABLE | [docs/build/reports/rights/osm_surveillance_tagging.md](rights/osm_surveillance_tagging.md) |
|  | `osm_taginfo` | ODbL-1.0 | public_terms_only | REFERENCE |  | LOADABLE | [docs/build/reports/rights/osm_taginfo.md](rights/osm_taginfo.md) |
|  | `osmf_licence_guidelines` | ODbL-1.0 | public_terms_only | REFERENCE |  | LOADABLE | [docs/build/reports/rights/osmf_licence_guidelines.md](rights/osmf_licence_guidelines.md) |
|  | `panopti_ca` | MIT | not_contacted | REFERENCE |  | REFUSED | — (no packet recorded) |
|  | `panopticity` | UNDETERMINED | not_contacted | LINK |  | REFUSED | — (no packet recorded) |
|  | `pathways_acoustic_drone_location` | LicenseRef-DerivedFacts-Citations | public_terms_only | DERIVE |  | LOADABLE | [docs/build/reports/rights/pathways_acoustic_drone_location.md](rights/pathways_acoustic_drone_location.md) |
|  | `pathways_fr_css_forensics` | LicenseRef-DerivedFacts-Citations | public_terms_only | DERIVE |  | LOADABLE | [docs/build/reports/rights/pathways_fr_css_forensics.md](rights/pathways_fr_css_forensics.md) |
|  | `pathways_rtcc_federation` | LicenseRef-DerivedFacts-Citations | public_terms_only | DERIVE |  | LOADABLE | [docs/build/reports/rights/pathways_rtcc_federation.md](rights/pathways_rtcc_federation.md) |
|  | `periscope_s2g` | UNDETERMINED | not_contacted | LINK |  | REFUSED | [docs/build/reports/rights/periscope_s2g.md](rights/periscope_s2g.md) |
|  | `planetbids` | UNDETERMINED | not_contacted | LINK |  | REFUSED | [docs/build/reports/rights/planetbids.md](rights/planetbids.md) |
|  | `policy_albuquerque_nm_apd` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `policy_anaheim_ca_pd_policy_manual` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `policy_bangor_me_pd` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `policy_chicago_il_oemc_link_your` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `policy_houston_tx_hpd` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `policy_lafayette_in_camera_registration` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `policy_little_rock_ar_pd` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `policy_maricopa_county_az_mcso_policies` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `policy_norman_ok_alpr_policy_amendment` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `policy_ok_oklahoma_dac_uved` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `policy_onslow_nc_schools` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `policy_orange_county_ca_sheriff` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `policy_pasadena_ca_pd` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `policy_pflugerville_tx_isd` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `policy_st_cloud_mn_isd742` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `policy_us_private_camera_registry` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `policy_whitesboro_ny_csd` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `policy_zionsville_in_camera_registry` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `powerdms_public_portals` | UNDETERMINED | not_contacted | LINK |  | REFUSED | [docs/build/reports/rights/powerdms_public_portals.md](rights/powerdms_public_portals.md) |
|  | `primegov` | CC0-1.0 | public_terms_only | REFERENCE |  | LOADABLE | [docs/build/reports/rights/primegov.md](rights/primegov.md) |
|  | `private_eyes` | MIT | not_contacted | REFERENCE |  | REFUSED | — (no packet recorded) |
|  | `procportal_austin_tx` | CC0-1.0 | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/procportal_austin_tx.md](rights/procportal_austin_tx.md) |
|  | `procportal_chicago_il` | UNDETERMINED | not_contacted | LINK |  | REFUSED | [docs/build/reports/rights/procportal_chicago_il.md](rights/procportal_chicago_il.md) |
|  | `procportal_cook_il_awards` | UNDETERMINED | public_terms_only | MIRROR |  | REFUSED | — (no packet recorded) |
|  | `procportal_davie_fl_purchasing` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `procportal_fl_florida_buy_cooperative` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `procportal_forsyth_nc_purchasing` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `procportal_kcmo_mo` | CC0-1.0 | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/procportal_kcmo_mo.md](rights/procportal_kcmo_mo.md) |
|  | `procportal_ny_northeastern_regional` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `procportal_nyc_ny` | CC0-1.0 | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/procportal_nyc_ny.md](rights/procportal_nyc_ny.md) |
|  | `procportal_ok_oklahoma_omes_statewide` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `procportal_pr_consulta_del_registro` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `procportal_sf_ca` | CC0-1.0 | public_terms_only | MIRROR |  | LOADABLE | [docs/build/reports/rights/procportal_sf_ca.md](rights/procportal_sf_ca.md) |
|  | `procportal_tx_texas_dir_cooperative` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `procportal_us_naspo_valuepoint_portfolio` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `procportal_wa_des_contract_sales` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `procportal_wa_wsipc_rfp_24` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `publicpurchase` | UNDETERMINED | not_contacted | LINK |  | REFUSED | [docs/build/reports/rights/publicpurchase.md](rights/publicpurchase.md) |
|  | `r_flocksurveillance` | UNDETERMINED | public_terms_only | LINK |  | REFUSED | — (no packet recorded) |
|  | `raa_prefectures` | ODbL-1.0 | public_terms_only | REFERENCE |  | LOADABLE | [docs/build/reports/rights/raa_prefectures.md](rights/raa_prefectures.md) |
|  | `ringmast4r_flock` | UNDETERMINED | not_contacted | LINK |  | REFUSED | — (no packet recorded) |
|  | `rotterdam_cameraregister` | UNDETERMINED | public_terms_only | REFERENCE |  | REFUSED | [docs/build/reports/rights/rotterdam_cameraregister.md](rights/rotterdam_cameraregister.md) |
|  | `sam_gov` | CC0-1.0 | public_terms_only | REFERENCE |  | LOADABLE | [docs/build/reports/rights/sam_gov.md](rights/sam_gov.md) |
|  | `sm_alpr` | AGPL-3.0 | not_contacted | REFERENCE |  | REFUSED | — (no packet recorded) |
|  | `sourcewell` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `sous_surveillance_osm_import` | ODbL-1.0 | public_terms_only | REFERENCE |  | LOADABLE | [docs/build/reports/rights/sous_surveillance_osm_import.md](rights/sous_surveillance_osm_import.md) |
|  | `state_alpr_statute_inventory` | LicenseRef-DerivedFacts-Citations | public_terms_only | DERIVE |  | LOADABLE | [docs/build/reports/rights/state_alpr_statute_inventory.md](rights/state_alpr_statute_inventory.md) |
|  | `state_alpr_statute_inventory_2026` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `statrep_austin_tx_auditor` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `statrep_ca_california_auditor_alpr` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `statrep_ca_special_parliament_use` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `statrep_co_frt_accountability` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `statrep_de_diac` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `statrep_detroit_mi_frt_weekly` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `statrep_fl_flhsmv_red_light` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `statrep_fr_cnil_utilisation_de` | UNDETERMINED | public_terms_only | MIRROR |  | REFUSED | — (no packet recorded) |
|  | `statrep_gb_enforcement_action` | UNDETERMINED | public_terms_only | MIRROR |  | REFUSED | — (no packet recorded) |
|  | `statrep_gb_eng_seven_cctv_june_2026` | UNDETERMINED | public_terms_only | MIRROR |  | REFUSED | — (no packet recorded) |
|  | `statrep_gb_sct_joint_assurance_review` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `statrep_gb_uk_algorithmic_transparency` | UNDETERMINED | public_terms_only | MIRROR |  | REFUSED | — (no packet recorded) |
|  | `statrep_hi_judiciary_interception` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `statrep_il_icjia_drone` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `statrep_il_isp_alpr` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `statrep_md_dls_mandated_reports` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `statrep_md_msp_css` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `statrep_me_dps_uav` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `statrep_mn_bca` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `statrep_mn_court_interception` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `statrep_ne_crime_commission_alpr` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `statrep_new_york_ny_nyc_doi_oig` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `statrep_pa_wzssc` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `statrep_seattle_wa_oig` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `statrep_seattle_wa_sdot_ate` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `statrep_tx_ca_nm_ri_fl_il_eff_red_flag` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `statrep_tx_south_padre_island_faa` | UNDETERMINED | public_terms_only | MIRROR |  | REFUSED | — (no packet recorded) |
|  | `statrep_us_2024_federal_agency` | UNDETERMINED | public_terms_only | MIRROR |  | REFUSED | — (no packet recorded) |
|  | `statrep_us_dhs_ai_use` | UNDETERMINED | public_terms_only | MIRROR |  | REFUSED | — (no packet recorded) |
|  | `statrep_us_dhs_privacy_compliance` | UNDETERMINED | public_terms_only | MIRROR |  | REFUSED | — (no packet recorded) |
|  | `statrep_us_ice_287_monthly` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `statrep_us_ice_287_participating` | UNDETERMINED | public_terms_only | MIRROR |  | REFUSED | — (no packet recorded) |
|  | `statrep_us_upturn_mass_extraction_2020` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `statrep_us_wiretap_summary_tables` | UNDETERMINED | public_terms_only | MIRROR |  | REFUSED | — (no packet recorded) |
|  | `statrep_va_rga` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `statrep_va_vscc_alpr` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `statrep_va_vsp_alpr` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `statrep_vt_dps_alpr` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `statrep_vt_vermont_law_enforcement` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `statrep_wa_ago_alpr_registry` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `statrep_wa_watech_frt` | UNDETERMINED | public_terms_only | DERIVE |  | REFUSED | — (no packet recorded) |
|  | `statrep_wa_wtsc_ate` | UNDETERMINED | public_terms_only | MIRROR |  | REFUSED | — (no packet recorded) |
|  | `surveillance_under_surveillance` | UNDETERMINED | not_contacted | REFERENCE |  | REFUSED | — (no packet recorded) |
|  | `swagit` | UNDETERMINED | not_contacted | LINK |  | REFUSED | [docs/build/reports/rights/swagit.md](rights/swagit.md) |
|  | `technocarte_update` | UNDETERMINED | not_contacted | LINK |  | REFUSED | — (no packet recorded) |
|  | `technopolice` | UNDETERMINED | not_contacted | REFERENCE |  | REFUSED | — (no packet recorded) |
|  | `technopolice_forum` | UNDETERMINED | not_contacted | LINK |  | REFUSED | — (no packet recorded) |
|  | `ted_eu` | CC-BY-4.0 | public_terms_only | REFERENCE |  | LOADABLE | [docs/build/reports/rights/ted_eu.md](rights/ted_eu.md) |
|  | `tips_usa` | UNDETERMINED | public_terms_only | LINK |  | REFUSED | — (no packet recorded) |
|  | `uk_surveillance_camera_commissioner` | LicenseRef-OperatorAccepted-DBRight | public_terms_only | DERIVE |  | LOADABLE | [docs/build/reports/rights/annex/p293/uk_surveillance_camera_commissioner.md](rights/annex/p293/uk_surveillance_camera_commissioner.md) |
|  | `usaspending` | CC0-1.0 | public_terms_only | REFERENCE |  | LOADABLE | [docs/build/reports/rights/usaspending.md](rights/usaspending.md) |
|  | `wigle` | UNDETERMINED | public_terms_only | LINK |  | REFUSED | — (no packet recorded) |
|  | `wikidata_sparql` | CC0-1.0 | public_terms_only | REFERENCE |  | LOADABLE | [docs/build/reports/rights/wikidata_sparql.md](rights/wikidata_sparql.md) |
|  | `wired_shotspotter_leak` | UNDETERMINED | public_terms_only | LINK |  | REFUSED | — (no packet recorded) |

_Packets present: 284 under `docs/build/reports/rights/` (excludes `_TEMPLATE.md`; includes the `annex/` batch packets)._ Regenerate: `python3 docs/build/tools/gen_rights_index.py`.
