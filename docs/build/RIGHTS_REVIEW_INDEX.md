# RIGHTS_REVIEW_INDEX — every registered source's rights/compact/custody/gate state (P21.1)

One row per registered source (SIG-LIC-001, SIG-INGEST-023/038). **Rights state**, **compact status**, and **custody posture** are read from `connectors/src/connectors/data/sources.toml`; **gate** and **flip-ready** are computed by `connectors.review` / `connectors.loader`. A **packet** column links the rights-review packet for the 27 sources on the critical path (`docs/build/rights/<id>.md`); the rest are P22+ backlog. `⭐` marks the OKC minimum set (critical-path step 4). Counts are reproduced from `uv run sig-connectors validate` — do not hand-edit; regenerate.

## Counts (from `sig-connectors validate`)

```
registered sources: 115
  rights UNDETERMINED (export gate fails closed): 93
  ingestion_permitted=true: 0
  loadable now (permitted + compact + custody): 0
  flip-ready (rights + compact + custody, flag false): 18
```

**Gate skipped this run (HG-03/HG-04 = SKIP):** nothing was flipped, so `loadable now: 0`. The 18 flip-ready sources are unblockable by an operator flip + recorded review metadata; the 6 OKC rows + `usaspending` + `deflock` + `civicclerk` are UNDETERMINED pending review. See `docs/build/STAGE0_OUTREACH_RECORD.md` for the compact/outreach state.

## OKC minimum set (critical-path step 4)

`⭐` `deflock_repo`, `ok_statute`, `okc_council`, `okc_procurement`, `okcpd_policy`, `osm_overpass` — government records (R1/R2) + the ODbL/community OSM route. News rows (`journalrecord`, `oklahoman`) are LINK-posture candidates (link out, never re-host).

## All sources

| ⭐ | source id | rights (SPDX) | compact | custody | flip-ready | gate | packet |
|---|---|---|---|---|---|---|---|
|  | `aclu_cell_site_simulators` | UNDETERMINED | not_contacted | REFERENCE |  | REFUSED | — (P22+ backlog) |
|  | `aclu_flock_toolkit` | UNDETERMINED | not_contacted | REFERENCE |  | REFUSED | — (P22+ backlog) |
|  | `agency_audit_export` | CC0-1.0 | public_terms_only | MIRROR | yes | flip-ready | [docs/build/rights/agency_audit_export.md](rights/agency_audit_export.md) |
|  | `alpr_abuse_library` | UNDETERMINED | not_contacted | REFERENCE |  | REFUSED | — (P22+ backlog) |
|  | `alpr_accountability_atlas` | UNDETERMINED | not_contacted | REFERENCE |  | REFUSED | — (P22+ backlog) |
|  | `alpr_watch` | UNDETERMINED | not_contacted | REFERENCE |  | REFUSED | — (P22+ backlog) |
|  | `alpr_watch_code` | UNDETERMINED | not_contacted | REFERENCE |  | REFUSED | — (P22+ backlog) |
|  | `alpr_watch_dashboard` | UNDETERMINED | not_contacted | REFERENCE |  | REFUSED | — (P22+ backlog) |
|  | `alpr_watch_foia_method` | UNDETERMINED | not_contacted | REFERENCE |  | REFUSED | — (P22+ backlog) |
|  | `aspi_mapping_chinas_tech_giants` | UNDETERMINED | not_contacted | LINK |  | REFUSED | — (P22+ backlog) |
|  | `atlas_about` | UNDETERMINED | public_terms_only | REFERENCE |  | REFUSED | — (P22+ backlog) |
|  | `atlas_data_library` | UNDETERMINED | public_terms_only | LINK |  | REFUSED | — (P22+ backlog) |
|  | `atlas_methodology` | UNDETERMINED | public_terms_only | REFERENCE |  | REFUSED | — (P22+ backlog) |
|  | `axon_community_connect` | UNDETERMINED | public_terms_only | REFERENCE |  | REFUSED | — (P22+ backlog) |
|  | `boarddocs` | UNDETERMINED | not_contacted | LINK |  | REFUSED | — (P22+ backlog) |
|  | `buyboard` | UNDETERMINED | public_terms_only | LINK |  | REFUSED | — (P22+ backlog) |
|  | `ca_sharing_visualization` | UNDETERMINED | public_terms_only | LINK |  | REFUSED | — (P22+ backlog) |
|  | `carnegie_ai_gsi` | UNDETERMINED | not_contacted | LINK |  | REFUSED | — (P22+ backlog) |
|  | `ccops_ordinance_disclosures` | UNDETERMINED | public_terms_only | MIRROR |  | REFUSED | — (P22+ backlog) |
|  | `census_gazetteer_tiger` | UNDETERMINED | public_terms_only | MIRROR |  | REFUSED | — (P22+ backlog) |
|  | `census_geocoder` | UNDETERMINED | public_terms_only | REFERENCE |  | REFUSED | — (P22+ backlog) |
|  | `civicclerk` | UNDETERMINED | public_terms_only | REFERENCE |  | REFUSED | [docs/build/rights/civicclerk.md](rights/civicclerk.md) |
|  | `civicplus` | UNDETERMINED | not_contacted | LINK |  | REFUSED | — (P22+ backlog) |
|  | `courtlistener_recap` | UNDETERMINED | public_terms_only | REFERENCE |  | REFUSED | — (P22+ backlog) |
|  | `declarationcamera_be` | UNDETERMINED | not_contacted | LINK |  | REFUSED | — (P22+ backlog) |
|  | `decp_fr` | UNDETERMINED | public_terms_only | REFERENCE |  | REFUSED | — (P22+ backlog) |
|  | `deflock` | UNDETERMINED | not_contacted | REFERENCE |  | REFUSED | [docs/build/rights/deflock.md](rights/deflock.md) |
|  | `deflock_app_repo` | AGPL-3.0 | public_terms_only | REFERENCE | yes | flip-ready | [docs/build/rights/deflock_app_repo.md](rights/deflock_app_repo.md) |
| ⭐ | `deflock_repo` | MIT | public_terms_only | REFERENCE | yes | flip-ready | [docs/build/rights/deflock_repo.md](rights/deflock_repo.md) |
|  | `dhs_fusion_centers` | UNDETERMINED | public_terms_only | REFERENCE |  | REFUSED | — (P22+ backlog) |
|  | `documentcloud` | UNDETERMINED | public_terms_only | REFERENCE |  | REFUSED | — (P22+ backlog) |
|  | `drivers_against_flock` | UNDETERMINED | not_contacted | LINK |  | REFUSED | — (P22+ backlog) |
|  | `eff_atlas_of_surveillance` | CC-BY-4.0 | public_terms_only | MIRROR | yes | flip-ready | [docs/build/rights/eff_atlas_of_surveillance.md](rights/eff_atlas_of_surveillance.md) |
|  | `eff_copyright` | UNDETERMINED | public_terms_only | REFERENCE |  | REFUSED | — (P22+ backlog) |
|  | `eff_data_driven` | UNDETERMINED | public_terms_only | REFERENCE |  | REFUSED | — (P22+ backlog) |
|  | `eff_street_level_surveillance` | UNDETERMINED | public_terms_only | REFERENCE |  | REFUSED | — (P22+ backlog) |
|  | `equalis_group` | UNDETERMINED | public_terms_only | LINK |  | REFUSED | — (P22+ backlog) |
|  | `escribe` | UNDETERMINED | not_contacted | LINK |  | REFUSED | — (P22+ backlog) |
|  | `eyes_off_cedar_rapids` | UNDETERMINED | not_contacted | LINK |  | REFUSED | — (P22+ backlog) |
|  | `eyes_off_eugene` | CC0-1.0 | not_contacted | REFERENCE |  | REFUSED | — (P22+ backlog) |
|  | `eyes_on_flock` | CC-BY-SA-4.0 | public_terms_only | MIRROR | yes | flip-ready | [docs/build/rights/eyes_on_flock.md](rights/eyes_on_flock.md) |
|  | `eyes_on_flock_description` | UNDETERMINED | public_terms_only | LINK |  | REFUSED | — (P22+ backlog) |
|  | `faa_drone_waivers` | UNDETERMINED | public_terms_only | REFERENCE |  | REFUSED | — (P22+ backlog) |
|  | `facial_recognition_world_map` | UNDETERMINED | not_contacted | LINK |  | REFUSED | — (P22+ backlog) |
|  | `fbi_cde_agency_registry` | UNDETERMINED | public_terms_only | REFERENCE |  | REFUSED | — (P22+ backlog) |
|  | `flock_ajith_fyi` | UNDETERMINED | not_contacted | LINK |  | REFUSED | — (P22+ backlog) |
|  | `flock_api_terms` | UNDETERMINED | public_terms_only | REFERENCE |  | REFUSED | — (P22+ backlog) |
|  | `flock_finder` | MIT | public_terms_only | REFERENCE | yes | flip-ready | [docs/build/rights/flock_finder.md](rights/flock_finder.md) |
|  | `flock_transparency_portals` | UNDETERMINED | public_terms_only | LINK |  | REFUSED | — (P22+ backlog) |
|  | `flock_you` | UNDETERMINED | not_contacted | REFERENCE |  | REFUSED | — (P22+ backlog) |
|  | `flockhopper3_deflock_data` | UNDETERMINED | not_contacted | LINK |  | REFUSED | — (P22+ backlog) |
|  | `flockreporter` | UNDETERMINED | no_response | LINK |  | REFUSED | — (P22+ backlog) |
|  | `foiaxpress` | UNDETERMINED | not_contacted | LINK |  | REFUSED | — (P22+ backlog) |
|  | `footnote4a` | UNDETERMINED | not_contacted | LINK |  | REFUSED | — (P22+ backlog) |
|  | `future_statutory_disclosure_2027` | UNDETERMINED | not_contacted | MIRROR |  | REFUSED | — (P22+ backlog) |
|  | `gleif` | CC0-1.0 | public_terms_only | MIRROR | yes | flip-ready | [docs/build/rights/gleif.md](rights/gleif.md) |
|  | `govqa` | UNDETERMINED | not_contacted | LINK |  | REFUSED | — (P22+ backlog) |
|  | `govspend` | UNDETERMINED | public_terms_only | LINK |  | REFUSED | — (P22+ backlog) |
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
|  | `la_quadrature_du_net` | UNDETERMINED | not_contacted | LINK |  | REFUSED | — (P22+ backlog) |
|  | `leaic_crosswalk` | UNDETERMINED | public_terms_only | MIRROR |  | REFUSED | — (P22+ backlog) |
|  | `legistar` | UNDETERMINED | public_terms_only | REFERENCE |  | REFUSED | — (P22+ backlog) |
|  | `madada` | UNDETERMINED | not_contacted | LINK |  | REFUSED | — (P22+ backlog) |
|  | `monahan_grounding_the_flock` | UNDETERMINED | public_terms_only | LINK |  | REFUSED | — (P22+ backlog) |
|  | `muckrock` | UNDETERMINED | public_terms_only | REFERENCE |  | REFUSED | — (P22+ backlog) |
|  | `naspo_valuepoint` | UNDETERMINED | public_terms_only | LINK |  | REFUSED | — (P22+ backlog) |
|  | `nces_ipeds_ntd_cms` | UNDETERMINED | public_terms_only | MIRROR |  | REFUSED | — (P22+ backlog) |
|  | `nextrequest` | UNDETERMINED | public_terms_only | REFERENCE |  | REFUSED | — (P22+ backlog) |
|  | `novusagenda` | UNDETERMINED | not_contacted | LINK |  | REFUSED | — (P22+ backlog) |
| ⭐ | `ok_statute` | UNDETERMINED | public_terms_only | REFERENCE |  | REFUSED | [docs/build/rights/ok_statute.md](rights/ok_statute.md) |
| ⭐ | `okc_council` | UNDETERMINED | public_terms_only | REFERENCE |  | REFUSED | [docs/build/rights/okc_council.md](rights/okc_council.md) |
| ⭐ | `okc_procurement` | UNDETERMINED | public_terms_only | REFERENCE |  | REFUSED | [docs/build/rights/okc_procurement.md](rights/okc_procurement.md) |
| ⭐ | `okcpd_policy` | UNDETERMINED | public_terms_only | REFERENCE |  | REFUSED | [docs/build/rights/okcpd_policy.md](rights/okcpd_policy.md) |
| · | `oklahoman` | UNDETERMINED | public_terms_only | LINK |  | REFUSED | [docs/build/rights/oklahoman.md](rights/oklahoman.md) |
|  | `omnia_partners` | UNDETERMINED | public_terms_only | LINK |  | REFUSED | — (P22+ backlog) |
|  | `openstates` | UNDETERMINED | public_terms_only | REFERENCE |  | REFUSED | — (P22+ backlog) |
|  | `osm_automated_edits_coc` | ODbL-1.0 | public_terms_only | REFERENCE | yes | flip-ready | [docs/build/rights/osm_automated_edits_coc.md](rights/osm_automated_edits_coc.md) |
|  | `osm_copyright` | ODbL-1.0 | public_terms_only | REFERENCE | yes | flip-ready | [docs/build/rights/osm_copyright.md](rights/osm_copyright.md) |
|  | `osm_element_history` | ODbL-1.0 | public_terms_only | REFERENCE | yes | flip-ready | [docs/build/rights/osm_element_history.md](rights/osm_element_history.md) |
| ⭐ | `osm_overpass` | ODbL-1.0 | public_terms_only | REFERENCE | yes | flip-ready | [docs/build/rights/osm_overpass.md](rights/osm_overpass.md) |
|  | `osm_replication` | ODbL-1.0 | public_terms_only | REFERENCE | yes | flip-ready | [docs/build/rights/osm_replication.md](rights/osm_replication.md) |
|  | `osm_surveillance_tagging` | ODbL-1.0 | public_terms_only | REFERENCE | yes | flip-ready | [docs/build/rights/osm_surveillance_tagging.md](rights/osm_surveillance_tagging.md) |
|  | `osm_taginfo` | ODbL-1.0 | public_terms_only | REFERENCE | yes | flip-ready | [docs/build/rights/osm_taginfo.md](rights/osm_taginfo.md) |
|  | `osmf_licence_guidelines` | ODbL-1.0 | public_terms_only | REFERENCE | yes | flip-ready | [docs/build/rights/osmf_licence_guidelines.md](rights/osmf_licence_guidelines.md) |
|  | `panopti_ca` | MIT | not_contacted | REFERENCE |  | REFUSED | — (P22+ backlog) |
|  | `panopticity` | UNDETERMINED | not_contacted | LINK |  | REFUSED | — (P22+ backlog) |
|  | `primegov` | UNDETERMINED | public_terms_only | REFERENCE |  | REFUSED | — (P22+ backlog) |
|  | `private_eyes` | MIT | not_contacted | REFERENCE |  | REFUSED | — (P22+ backlog) |
|  | `r_flocksurveillance` | UNDETERMINED | public_terms_only | LINK |  | REFUSED | — (P22+ backlog) |
|  | `raa_prefectures` | ODbL-1.0 | public_terms_only | REFERENCE | yes | flip-ready | [docs/build/rights/raa_prefectures.md](rights/raa_prefectures.md) |
|  | `ringmast4r_flock` | UNDETERMINED | not_contacted | LINK |  | REFUSED | — (P22+ backlog) |
|  | `sam_gov` | UNDETERMINED | public_terms_only | REFERENCE |  | REFUSED | — (P22+ backlog) |
|  | `sm_alpr` | AGPL-3.0 | not_contacted | REFERENCE |  | REFUSED | — (P22+ backlog) |
|  | `sourcewell` | UNDETERMINED | public_terms_only | REFERENCE |  | REFUSED | — (P22+ backlog) |
|  | `sous_surveillance_osm_import` | ODbL-1.0 | public_terms_only | REFERENCE | yes | flip-ready | [docs/build/rights/sous_surveillance_osm_import.md](rights/sous_surveillance_osm_import.md) |
|  | `state_alpr_statute_inventory` | UNDETERMINED | public_terms_only | MIRROR |  | REFUSED | — (P22+ backlog) |
|  | `surveillance_under_surveillance` | UNDETERMINED | not_contacted | REFERENCE |  | REFUSED | — (P22+ backlog) |
|  | `technocarte_update` | UNDETERMINED | not_contacted | LINK |  | REFUSED | — (P22+ backlog) |
|  | `technopolice` | UNDETERMINED | not_contacted | REFERENCE |  | REFUSED | — (P22+ backlog) |
|  | `technopolice_forum` | UNDETERMINED | not_contacted | LINK |  | REFUSED | — (P22+ backlog) |
|  | `ted_eu` | UNDETERMINED | public_terms_only | REFERENCE |  | REFUSED | — (P22+ backlog) |
|  | `tips_usa` | UNDETERMINED | public_terms_only | LINK |  | REFUSED | — (P22+ backlog) |
|  | `usaspending` | UNDETERMINED | public_terms_only | REFERENCE |  | REFUSED | [docs/build/rights/usaspending.md](rights/usaspending.md) |
|  | `wigle` | UNDETERMINED | public_terms_only | LINK |  | REFUSED | — (P22+ backlog) |
|  | `wikidata_sparql` | CC0-1.0 | public_terms_only | REFERENCE | yes | flip-ready | [docs/build/rights/wikidata_sparql.md](rights/wikidata_sparql.md) |
|  | `wired_shotspotter_leak` | UNDETERMINED | public_terms_only | LINK |  | REFUSED | — (P22+ backlog) |

_Packets present: 27 (excludes `_TEMPLATE.md`)._ Regenerate: `python .agents/scratch/tools/gen_rights_index.py`.
