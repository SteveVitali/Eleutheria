<!--
  docs/build/reports/SOURCE_LIVE_OPS_MATRIX.md — the "nothing unscoped" artifact.
  Every registered source (121, from connectors/src/connectors/data/sources.toml)
  is assigned a live-operationalization disposition + an owning P25 ticket, so the
  downstream live-fetch work for ALL data sources is scoped (operator request,
  2026-09-15). Grounded in the registry inventory (`sig-connectors validate` +
  CONNECTOR_FOR_SOURCE). Determinations applied: ADR-083 (API-vs-crawl carve-out),
  HG-11 interim, credentials available (data.gov / MuckRock / Zenodo).
-->
# Source live-operationalization coverage matrix (all 121 sources)

**Inventory (2026-09-16, post-P25.7):** 121 registered sources ·
`ingestion_permitted=true` cohort grown by the P25.x flips (validate: 25) ·
**24 mapped** to a connector class (`state_alpr_statute_inventory` joined the
mapped set via the `state_statute_seed` connector — P25.7) · **97 unmapped**
(51 REFERENCE, 38 LINK, 7 MIRROR, 9 promote→their class ticket — citation/
reference rows, mostly UNDETERMINED rights). Every row below names the P25
ticket that owns its live-op work.

## A. Connector-backed classes (24 sources) — live-fetch work

| class (n) | sources | conduct (ADR-083) | creds | gate | owning ticket |
|---|---|---|---|---|---|
| okc documents (3) | `okc_procurement`, `okcpd_policy`, `ok_statute` | CRAWL (gov PDFs/HTML) | none | green ✅ | **P25.1** (live doc parser + content-drift) |
| agenda / procurement portal (1) | `okc_council` (CivicClerk) | API allow-list (tenant host) | none | green ✅ | **P25.1** (CivicClerk tenant verify) |
| osm physical (2) | `osm_overpass`, `osm_element_history` | API allow-list (`overpass-api.de`) | none | green ✅ | **P25.3** |
| deflock (1) | `deflock_repo` (MIT) | CRAWL/repo (robots-clean) | none | green ✅ | **P25.3** |
| atlas (1) | `eff_atlas_of_surveillance` | API/CRAWL per ToS | none | HG-03 | **P25.3** |
| records (1) | `muckrock` | API allow-list (`www.muckrock.com`) + **Cloud Run egress** (Cloudflare 403s local/residential IPs; GCP datacenter egress is clean — job `sig-ingest-muckrock`) + **recurring cadence** (Cloud Scheduler `sig-sched-muckrock`, `0 6 1 * *`, ENABLED — `ops/gcp/schedule.sh`, P25.7) | **SIG_MUCKROCK_REFRESH ✅** | green ✅ — LIVE landed 6 claims (request 136412) | **P25.2** (+P25.7 cadence) |
| procurement (1) | `usaspending` | API allow-list (`api.usaspending.gov`) | none | HG-03 | **P25.2** |
| data-driven (1) | `eff_data_driven` | API allow-list (data.gov) | **SIG_DATA_GOV_KEY ✅** | HG-03/04 | **P25.4** |
| coarse-international (3) | `aspi_mapping_chinas_tech_giants`, `carnegie_ai_gsi`, `facial_recognition_world_map` | **LIVE curated-adapter extraction** (P25.4 d2): `carnegie_ai_gsi` parses the GSI page's embedded JS dataset chunk (strict 75-entry shape; bounded `dataset_chunk` discovery) → 660 typed country/vendor claims; `facial_recognition_world_map` parses the linked Google Sheet's six reviewed gviz sheets → 202 country-status claims (duplicate-Egypt conflict preserved); `aspi` stays WAF-403 on local + Cloud Run egress → recorded `access_restricted` disappearance, never defeated (egress re-probed **P25.7** — `aspi-egress-probe` still 403, the recorded block is the disposition) | some data.gov | FLIPPED on counsel approval (HG-02, 2026-09-15), derived-facts basis | **P25.4** — adapter run 2026-09-16 (`reports/live_runs/2026-09-16_*`) |
| france/belgium (4) | `raa_prefectures` ✅ flipped (ODbL-1.0) + **LIVE resource-index run** (index CSV parsed strictly; 8 bounded `instrument_document` targets resolved to real arrêté PDFs — every prefecture host's robots.txt unretrievable → 8 recorded per-document politeness refusals, never bypassed); `decp_fr` ✅ flipped+LIVE — **dataset-API indirection (P25.7)**: the timestamped static pin is gone; the resource URL resolves through `www.data.gouv.fr /api/1/datasets/…` at run time, a removed/renamed resource is a recorded `link_rotted` disappearance, never a stale-URL fallback (9,495 rows → 7,234 spine claims on the 2026-09-16 re-run); `madada` ✅ FLIPPED + **LIVE feed extraction** (52 rows: 25 `fr.cada` records-request contexts + artifacts; request text never retained); `declarationcamera_be` FLIPPED on counsel approval (HG-02) but stays NoLiveTargets — the register sits behind Belgian eID (HG-04 owed; boundary re-recorded P25.7) | API allow-list (`data.gouv.fr`) | `*.gouv.fr` prefecture hosts robots-unretrievable → recorded refusals | green for the resolved two; LO 2.0 counsel flag retained | **P25.5** — extraction run 2026-09-16 (+P25.7 indirection) (`reports/live_runs/2026-09-16_*.json`) |
| pathways / Stage-5 (3) | `pathways_rtcc_federation`, `pathways_fr_css_forensics`, `pathways_acoustic_drone_location` | **LIVE document→claim extraction** (P25.5): real EFF pages captured; genre re-derived from bytes (`vendor_disclosure`/`policy_document`); reviewed-term `technology` claims emitted with byte/page locators (rtcc 2 claims; drones 1; face-recognition page yields artifact-only — the reviewed literal is absent from its bytes, no claim fabricated) | none | FLIPPED on derived-facts basis (ADR-085) | **P25.5** — extraction run 2026-09-16 |
| CCOPS (3) | `ccops_seattle`, `ccops_nyc_post`, `ccops_sf` | **LIVE index→document extraction** (P25.5): `ccops_nyc_post` fetched the index + 6 bounded `post-final/*.pdf` filings → 94 rows (technology/legal-authority/field-state claims w/ page locators, field_state answered/present_but_empty/absent, procured≠deployed enforced); `ccops_seattle` index parsed → ordinance claims + 4 linked filings all 404 → recorded `link_rotted` disappearances; `ccops_sf` refuses honestly — sf.gov robots.txt unretrievable (SIG-INGEST-012); **P25.7 Cloud Run egress probe** (`ccops-sf-egress-probe`) shows `www.sf.gov` answering both robots.txt and the index page with `202 text/html` — an interstitial challenge, not usable robots content — the refusal is confirmed from the hosted vantage | none | FLIPPED on mandated-disclosure basis (ADR-085) | **P25.5** — extraction run 2026-09-16 (+P25.7 egress confirmation, + BL-054 expansion) |
| NCSL statute seed (1) | `state_alpr_statute_inventory` | **one-time packaged seed** (`state_statute_seed` connector + `seeds.toml` + `sig-connectors load-seed`, P25.7) — the asset runs through the same connector pipeline over the static transport; the source row stays `ingestion_permitted=false` (a controlled seed, not a feed, never a live fetch) | none | source row closed; seed loaded under the seed registry | **P25.7** — **108 claims in the hosted spine, `as_of = 2022-02-03` preserved** (16 states / 17 NCSL rows / 21 statute-year instruments) |

## B. Unmapped sources (97) — triage disposition — **RESOLVED 2026-09-15**

Every one of the 97 now carries exactly one recorded disposition in
`connectors/src/connectors/data/live_dispositions.toml`, and the CI check
(`tests/connectors/test_live_dispositions.py`) enforces
`mapped ∪ dispositions == 121` — a newly-registered source with neither a
connector map entry nor a disposition row **fails the build**.
(`state_alpr_statute_inventory` left this set in P25.7: the packaged-seed
connector `state_statute_seed` owns it, so the source is now connector-mapped
and its `mirror` row was removed.)

| disposition | count | meaning |
|---|---|---|
| `link_only` | 38 | a stable citation locator; SIG links, never ingests as a feed. |
| `reference` | 43 | context/provenance rows (accountability libraries, toolkits, geocoder + taginfo substrates). |
| `mirror` | 7 | archived copies; fetched (if ever) from the archive, not the origin. |
| `promote` | 9 | a real API/feed → a genuine future live connector (HG-03 flip still required). |

**Promoted (9):** `civicclerk`, `legistar`, `primegov`, `sam_gov`,
`courtlistener_recap`, `documentcloud`, `openstates` → **P25.2** (records/
procurement/agenda-tenant classes); `eyes_on_flock` → **P25.3** (physical layer);
`fbi_cde_agency_registry` → **P25.4** (data.gov-keyed ORI9 substrate — needs a
substrate connector; flipped 2026-09-15). `documentcloud` shares the muckrock
Cloudflare-WAF finding.

## C. Cross-cutting (not per-source)

| item | owning ticket | status |
|---|---|---|
| the ADR-083 carve-out **implementation** (`policy.crawler` allow-list + `PoliteFetcher` wiring + test) | **P25.1** | **LANDED** (api_allowlist.toml + PoliteFetcher conduct decisions + POST seam) |
| the `data/live_targets.toml` rows for every live-connector source | its class ticket | landed for all 6 live-able sources (osm_overpass, osm_element_history, eff_atlas, usaspending, eff_data_driven, muckrock) |
| POST body support in the shared fetch seam (USAspending subawards) | **P25.2** | **LANDED** — 540 sub-award claims committed live |
| MuckRock JWT-refresh wiring | **P25.2** | **LANDED** — fetch honestly WAF-blocked (Cloudflare 403 → recorded disappearance) |
| Data Driven real-artifact adapter (EFF zip → release manifest) | **P25.4** | **LANDED** — 200 agency aggregates live |
| `decp_fr` dataset-API resource indirection (no more timestamped static pin) | **P25.7** | **LANDED** — resource URL resolves via `www.data.gouv.fr /api/1/datasets/…`; a removed resource is a recorded `link_rotted` disappearance |
| `LicenseRef-DerivedFacts-Citations` export-compartment disposition | **P25.7** | **RECORDED EXCLUSION** (`export_disposition=excluded`, `exclusion=counsel_pending`) — the export gate fails closed by decision, not silence; HG-02 counsel ruling still owed |
| MuckRock recurring cadence | **P25.7** | **LANDED + APPLIED** — Cloud Scheduler `sig-sched-muckrock` (`0 6 1 * *`, ENABLED) → `sig-ingest-muckrock`; targeted lookup only |
| HG-07 Zenodo (sandbox) deposit + object-store push + SWH | **P21.5 re-run** (`D-P21.5-1`) — **Zenodo token now available** | **sandbox deposit DONE** (10.5072/zenodo.603732); object-store push + SWH remain |
| Go-public (public buckets + Cloud Run unauth + DNS + `v0.2.0`) | operator (HG-11 second reviewer + HG-02 counsel) | blocked |

## D. Ownership summary

- **P25.1** — conduct carve-out impl + live document parser/content-drift + CivicClerk.
- **P25.2** — records (MuckRock, creds-ready) + procurement (USAspending).
- **P25.3** — OSM/DeFlock/atlas physical layer.
- **P25.4** — data-driven + coarse-international (data.gov creds-ready).
- **P25.5** — Stage-5 pathways + France/Belgium + CCOPS expansion (design/counsel-gated).
- **P25.6** — unmapped-source triage (the 98) → LINK/REFERENCE/MIRROR/promote, with the completeness assertion.
- **P25.7** — live-ops hardening: DECP dataset-API indirection, derived-facts licence exclusion, Cloud Run egress probes (aspi/ccops_sf), the NCSL seed load, and the MuckRock recurring cadence.
- **P21.5 re-run** — Zenodo/SWH deposits (creds now available), not a new ticket.
