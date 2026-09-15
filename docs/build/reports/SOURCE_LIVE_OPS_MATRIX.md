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

**Inventory (2026-09-15):** 121 registered sources · 6 `ingestion_permitted=true`
(the OKC critical subset) · 23 mapped to a connector class · 98 unmapped
(51 REFERENCE, 38 LINK, 9 MIRROR — citation/reference rows, mostly UNDETERMINED
rights). Every row below names the P25 ticket that owns its live-op work.

## A. Connector-backed classes (23 sources) — live-fetch work

| class (n) | sources | conduct (ADR-083) | creds | gate | owning ticket |
|---|---|---|---|---|---|
| okc documents (3) | `okc_procurement`, `okcpd_policy`, `ok_statute` | CRAWL (gov PDFs/HTML) | none | green ✅ | **P25.1** (live doc parser + content-drift) |
| agenda / procurement portal (1) | `okc_council` (CivicClerk) | API allow-list (tenant host) | none | green ✅ | **P25.1** (CivicClerk tenant verify) |
| osm physical (2) | `osm_overpass`, `osm_element_history` | API allow-list (`overpass-api.de`) | none | green ✅ | **P25.3** |
| deflock (1) | `deflock_repo` (MIT) | CRAWL/repo (robots-clean) | none | green ✅ | **P25.3** |
| atlas (1) | `eff_atlas_of_surveillance` | API/CRAWL per ToS | none | HG-03 | **P25.3** |
| records (1) | `muckrock` | API allow-list (`www.muckrock.com`) | **SIG_MUCKROCK_TOKEN ✅** | HG-03 | **P25.2** |
| procurement (1) | `usaspending` | API allow-list (`api.usaspending.gov`) | none | HG-03 | **P25.2** |
| data-driven (1) | `eff_data_driven` | API allow-list (data.gov) | **SIG_DATA_GOV_KEY ✅** | HG-03/04 | **P25.4** |
| coarse-international (3) | `aspi_mapping_chinas_tech_giants`, `carnegie_ai_gsi`, `facial_recognition_world_map` | CRAWL/API per source | some data.gov | HG-03/04 | **P25.4** |
| france/belgium (4) | `raa_prefectures`, `decp_fr`, `madada`, `declarationcamera_be` | CRAWL/API per source | none | HG-03/04; LO 2.0 counsel | **P25.5** |
| pathways / Stage-5 (3) | `pathways_rtcc_federation`, `pathways_fr_css_forensics`, `pathways_acoustic_drone_location` | design-gated | none | HG-03/04; Part VIII/counsel | **P25.5** |
| CCOPS (3) | `ccops_seattle`, `ccops_nyc_post`, `ccops_sf` | CRAWL (gov PDFs) | none | HG-03/04 | **P25.5** (+ BL-054 expansion) |

## B. Unmapped sources (98) — triage disposition

These carry **no connector** today. The dominant disposition is *cited, not
fetched* — they are evidence/reference rows, not live-fetch targets.

| disposition | ~count | meaning | owning ticket |
|---|---|---|---|
| **LINK-only (cited, not fetched)** | 38 LINK | a stable citation locator; SIG links to it, never ingests its bytes as a source feed (news, primary-source links). No live connector by design. | **P25.6** (confirm + record the disposition; no fetch) |
| **REFERENCE (background/context)** | 51 REFERENCE | context/reference datasets (accountability libraries, toolkits) cited for provenance; not a structured feed. No live connector unless promoted. | **P25.6** (triage: keep REFERENCE vs promote) |
| **MIRROR (archived copy)** | 9 MIRROR | an archived/mirrored copy of another source; fetched (if ever) from the archive, not the origin. | **P25.6** (archive-fetch policy) |
| **future-connector candidates** | subset w/ `access_method=rest_api/json_api/sparql` | REFERENCE rows that expose a real API (e.g. `rest_api`, `sparql`) — genuine future live connectors. | **P25.6** promotes each to its class ticket (P25.2–P25.5) with an HG-03 flip. |

**Rule:** P25.6 must classify **every** one of the 98 into exactly one of the
above, so no source is left without a disposition (a `check`-style assertion:
mapped ∪ LINK ∪ REFERENCE ∪ MIRROR ∪ promoted == 121).

## C. Cross-cutting (not per-source)

| item | owning ticket | status |
|---|---|---|
| the ADR-083 carve-out **implementation** (`policy.crawler` allow-list + `PoliteFetcher` wiring + test) | **P25.1** | scoped |
| the `data/live_targets.toml` rows for every live-connector source | its class ticket | scoped |
| HG-07 Zenodo (sandbox) deposit + object-store push + SWH | **P21.5 re-run** (`D-P21.5-1`) — **Zenodo token now available** | creds-ready |
| Go-public (public buckets + Cloud Run unauth + DNS + `v0.2.0`) | operator (HG-11 second reviewer + HG-02 counsel) | blocked |

## D. Ownership summary

- **P25.1** — conduct carve-out impl + live document parser/content-drift + CivicClerk.
- **P25.2** — records (MuckRock, creds-ready) + procurement (USAspending).
- **P25.3** — OSM/DeFlock/atlas physical layer.
- **P25.4** — data-driven + coarse-international (data.gov creds-ready).
- **P25.5** — Stage-5 pathways + France/Belgium + CCOPS expansion (design/counsel-gated).
- **P25.6** — unmapped-source triage (the 98) → LINK/REFERENCE/MIRROR/promote, with the completeness assertion.
- **P21.5 re-run** — Zenodo/SWH deposits (creds now available), not a new ticket.
