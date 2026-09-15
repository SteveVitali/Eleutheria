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
| records (1) | `muckrock` | API allow-list (`www.muckrock.com`) + **Cloud Run egress** (Cloudflare 403s local/residential IPs; GCP datacenter egress is clean — job `sig-ingest-muckrock`) | **SIG_MUCKROCK_REFRESH ✅** | green ✅ — LIVE landed 6 claims (request 136412) | **P25.2** |
| procurement (1) | `usaspending` | API allow-list (`api.usaspending.gov`) | none | HG-03 | **P25.2** |
| data-driven (1) | `eff_data_driven` | API allow-list (data.gov) | **SIG_DATA_GOV_KEY ✅** | HG-03/04 | **P25.4** |
| coarse-international (3) | `aspi_mapping_chinas_tech_giants`, `carnegie_ai_gsi`, `facial_recognition_world_map` | replay/shadow (committed fixtures) | some data.gov | FLIPPED on counsel approval (HG-02, 2026-09-15), derived-facts basis; live blocked on page adapters (NoLiveTargets) | **P25.4** |
| france/belgium (4) | `raa_prefectures` ✅ flipped (ODbL-1.0), live blocked on a resources→orders adapter; `decp_fr` ✅ flipped+LIVE (9,494 claims from the real DECP monthly file); `madada` + `declarationcamera_be` FLIPPED on counsel approval (HG-02, derived-facts basis) — live still blocked: madada needs an Atom/CSV→records adapter, declarationcamera sits behind Belgian eID (HG-04 owed) | API allow-list (`data.gouv.fr`) | none | green for the resolved two; LO 2.0 counsel flag retained | **P25.5** — per-source France gate (operator 2026-09-15) |
| pathways / Stage-5 (3) | `pathways_rtcc_federation`, `pathways_fr_css_forensics`, `pathways_acoustic_drone_location` | replay/shadow (committed fixtures) | none | FLIPPED on derived-facts basis (ADR-085); live blocked on document adapters | **P25.5** |
| CCOPS (3) | `ccops_seattle`, `ccops_nyc_post`, `ccops_sf` | replay/shadow (committed fixtures) | none | FLIPPED on mandated-disclosure basis (ADR-085); live blocked on PDF/HTML adapters | **P25.5** (+ BL-054 expansion) |

## B. Unmapped sources (98) — triage disposition — **RESOLVED 2026-09-15**

Every one of the 98 now carries exactly one recorded disposition in
`connectors/src/connectors/data/live_dispositions.toml`, and the CI check
(`tests/connectors/test_live_dispositions.py`) enforces
`mapped ∪ dispositions == 121` — a newly-registered source with neither a
connector map entry nor a disposition row **fails the build**.

| disposition | count | meaning |
|---|---|---|
| `link_only` | 38 | a stable citation locator; SIG links, never ingests as a feed. |
| `reference` | 43 | context/provenance rows (accountability libraries, toolkits, geocoder + taginfo substrates). |
| `mirror` | 8 | archived copies; fetched (if ever) from the archive, not the origin. |
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
| HG-07 Zenodo (sandbox) deposit + object-store push + SWH | **P21.5 re-run** (`D-P21.5-1`) — **Zenodo token now available** | **sandbox deposit DONE** (10.5072/zenodo.603732); object-store push + SWH remain |
| Go-public (public buckets + Cloud Run unauth + DNS + `v0.2.0`) | operator (HG-11 second reviewer + HG-02 counsel) | blocked |

## D. Ownership summary

- **P25.1** — conduct carve-out impl + live document parser/content-drift + CivicClerk.
- **P25.2** — records (MuckRock, creds-ready) + procurement (USAspending).
- **P25.3** — OSM/DeFlock/atlas physical layer.
- **P25.4** — data-driven + coarse-international (data.gov creds-ready).
- **P25.5** — Stage-5 pathways + France/Belgium + CCOPS expansion (design/counsel-gated).
- **P25.6** — unmapped-source triage (the 98) → LINK/REFERENCE/MIRROR/promote, with the completeness assertion.
- **P21.5 re-run** — Zenodo/SWH deposits (creds now available), not a new ticket.
