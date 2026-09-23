# STAGE0_OUTREACH_RECORD — federation-compact Stage-0 outreach (P21.1, SIG-CONTRIB-012/012a/013)

One row per **federation-compact project** — the 19 of spec §6 (the compact table) / §35.1 ("all nineteen federation-compact projects", §52). Stage-0 outreach MUST be attempted and its outcome recorded **before** any connector is written for a project (SIG-CONTRIB-012, SIG-CHART-033); the outcome vocabulary is the closed `compact_status` enum (SIG-INGEST-027).

## Gate status — HG-04 = SKIP (no outreach performed this run)

**No Stage-0 outreach has been performed by this ticket.** This file is the RECORD FORMAT (template), seeded from the registry's current `compact_status`. Every `date_sent` is `—` and every `outcome` is the registry-recorded posture: `not_contacted` or `public_terms_only` (public terms suffice for lawful use today), plus the pre-existing `no_response` for **FlockReporter** — a state already recorded in the registry (the directory's DNS ceased between 2026-07-28 and 2026-08-20, SIG-INGEST-039b), NOT new outreach invented here. No `permission_granted` / `partnership_active` / `permission_declined` is asserted anywhere, because none was obtained (defining standard §3.1 — no synthetic certainty; append-only P1–P3 — a real outreach event is added as a new dated row, never by rewriting this seed). Contact channels are ORGANISATIONAL public addresses only — no personal names (Part VIII §0.7).

The archival-succession offer (SIG-CONTRIB-013, RISK-P0-17/20) and, where a project has publicly asked for help (SIG-CONTRIB-012a), the opening offer, are carried in the outreach letter template: `docs/governance/stage0-outreach-letter.md`.

## Record

| # | project | contact channel (public org address only) | date_sent | outcome | governs (sources.toml ids) |
|---|---|---|---|---|---|
| 1 | OpenStreetMap / OSMF | https://osmfoundation.org/wiki/Contact (OSMF, public) | — | public_terms_only | `osm_surveillance_tagging`, `osm_copyright`, `osmf_licence_guidelines`, `osm_taginfo`, `osm_overpass`, `osm_replication`, `osm_element_history`, `osm_automated_edits_coc`, `sous_surveillance_osm_import` |
| 2 | DeFlock (FoggedLens) | https://github.com/FoggedLens/deflock/issues (project issue tracker, public) | — | public_terms_only | `deflock`, `deflock_repo`, `deflock_app_repo` |
| 3 | Eyes on Flock | contact@eyesonflock.com (organisational address, registry-recorded) | — | public_terms_only | `eyes_on_flock`, `eyes_on_flock_description` |
| 4 | Have I Been Flocked | https://haveibeenflocked.com/about (project contact page, public) | — | not_contacted | `have_i_been_flocked`, `hibf_methodology`, `hibf_audit_log_guide` |
| 5 | ALPR Watch | https://alprwatch.org/ (project site, public) | — | not_contacted | `alpr_watch`, `alpr_watch_foia_method`, `alpr_watch_code`, `alpr_watch_dashboard` |
| 6 | EFF — Atlas of Surveillance | https://www.eff.org/about/contact (EFF, public) | — | public_terms_only | `eff_atlas_of_surveillance`, `atlas_methodology`, `atlas_about`, `atlas_data_library`, `eff_copyright`, `eff_street_level_surveillance` |
| 7 | EFF — Data Driven | https://www.eff.org/about/contact (EFF, public) | — | public_terms_only | `eff_data_driven` |
| 8 | ALPR Accountability Atlas | https://alpratlas.org/ (project site, public) | — | not_contacted | `alpr_accountability_atlas` |
| 9 | ALPR Abuse Library / Kansas Watch | https://library.kansas.watch/ (project site, public) | — | not_contacted | `alpr_abuse_library` |
| 10 | MuckRock | info@muckrock.com (organisational address, public) | — | public_terms_only | `muckrock` |
| 11 | DocumentCloud | https://www.documentcloud.org/help/ (project contact page, public) | — | public_terms_only | `documentcloud` |
| 12 | Drivers Against Flock | https://driversagainstflock.org/ (project site, public) | — | not_contacted | `drivers_against_flock` |
| 13 | Flock Finder | https://github.com/simeononsecurity/flock-finder/issues (issue tracker, public) | — | public_terms_only | `flock_finder` |
| 14 | Flock-You | https://github.com/rjmoggach/flock-you (project repo, public) | — | not_contacted | `flock_you` |
| 15 | FlockReporter | flockreporter.org (DNS ceased 2026-07-28 .. 2026-08-20; SIG-INGEST-039b) | — | no_response | `flockreporter` |
| 16 | Local DeFlock / Eyes Off groups | per-group public sites (connectors/.../data/local_groups.toml) | — | not_contacted | `eyes_off_cedar_rapids`, `eyes_off_eugene` |
| 17 | Technopolice / La Quadrature du Net | https://www.laquadrature.net/en/contact/ (LQDN, public) | — | not_contacted | `technopolice`, `technopolice_forum`, `technocarte_update`, `la_quadrature_du_net` |
| 18 | Surveillance under Surveillance | https://sunders.uber.space/ (project site, public) | — | not_contacted | `surveillance_under_surveillance` |
| 19 | PanoptiCity | https://panopticity.fr/ (project site, public) | — | not_contacted | `panopticity` |

_19 project rows. Regenerate: `python .agents/scratch/tools/gen_stage0_record.py`. Consistency test: `tests/connectors/test_stage0_outreach.py`._
