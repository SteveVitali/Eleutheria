# Appendix F — Architecture Decision Record index

**SIG-STORE-006** requires each decision below to be written as an ADR under `docs/adr/`,
using a consistent template: context, decision, status, consequences, alternatives considered, and —
mandatory per SIG-STORE-007 — a **revisit trigger**.

This index is the **repository ADR numbering** and lists **every** `docs/adr/ADR-*.md` by its
repository number, title, and owning phase. Its single source of truth is `docs/adr/README.md`
(SIG-ENG-039): any pull request that adds an ADR MUST add its row here in the same PR, and
`docs/build/tools/check_spec_src.py` asserts the ADR-file set and this table are equal.

> **Numbering note (LD-X04 / LD-D03).** Early drafts of this appendix used a *logical* numbering
> for the eighteen §15.5 + stack decisions that does **not** match the repository ADR numbers. That
> logical scheme is retired: the repository numbering above is canonical. A few historical
> equivalences a reader may meet in older ledgers/PR bodies: logical "ADR-013 (Apache-2.0 code /
> CC-BY data / CC0 ontology, §42.2)" and logical "ADR-016 (Splink)" and logical "ADR-017 (no direct
> automated OSM writes, §35.2)" and logical "ADR-024/025 (the P06.1 count-reconciliation /
> dossier-renderer decisions)" all refer to *design points* now recorded under the repository ADRs
> that own them — e.g. Splink is repository **ADR-029** (P05.1), the no-OSM-writes decision is
> repository **ADR-055** (P16.2, which itself records the spec's Appendix-F "ADR-017"), and the
> P06.1 seeds are repository **ADR-031/032**. When in doubt, cite the repository number.

| ADR | Decision | Phase |
|---|---|---|
| ADR-001 | PostgreSQL 18 + PostGIS as the canonical store; everything else a projection | P00.2 |
| ADR-002 | Append-only claim table; entity tables hold identity only | P00.2 |
| ADR-003 | Two interval time dimensions plus one ordering scalar | P00.2 |
| ADR-004 | EDTF for uncertain dates | P00.2 |
| ADR-005 | Resolution as a stored decision record, not a view | P00.2 |
| ADR-006 | OCFL 1.1 evidence store on object storage with governance-mode Object Lock | P00.2 |
| ADR-007 | LinkML as the single ontology source of truth | P00.2 |
| ADR-008 | SKOS for published controlled vocabularies | P00.2 |
| ADR-009 | SPDX expressions for per-source licensing, with a build-time compatibility gate | P00.2 |
| ADR-010 | DuckDB/Parquet analytics boundary; no raw audit rows anywhere | P00.2 |
| ADR-011 | The ODbL posture: OSM-derived assets in a separate compartment (Strategy B) | P00.2 |
| ADR-012 | Sensitivity tiers enforced by RLS, applied at the view layer | P00.2 |
| ADR-013 | uv as the workspace and lockfile tool | P00.2 |
| ADR-014 | Astro for the public web surface | P00.2 |
| ADR-015 | AWS S3 for the evidence store and CloudFront for bulk-export delivery | P00.2 |
| ADR-016 | Dagster OSS for orchestration, kept reversible | P00.2 |
| ADR-017 | FastAPI for the read API | P00.2 |
| ADR-018 | MapLibre GL for the web map | P00.2 |
| ADR-019 | pytest + Hypothesis for testing | P00.2 |
| ADR-020 | GitHub Actions for CI | P00.2 |
| ADR-021 | Source registry as seeded data, with a runtime ingestion gate in `connectors` | P00.4 |
| ADR-022 | Defer physical partitioning of `claim` to preserve the `claim_id` FK contract | P02.1 |
| ADR-023 | An `evidence/` package, and content-addressed blob dedup for the capture row | P02.2 |
| ADR-024 | A pinned, deterministic, in-repo EDTF envelope derivation | P02.3 |
| ADR-025 | Temporal invariants as pipeline data-quality checks; as-of as SQL functions | P02.3 |
| ADR-026 | The eight-stage connector framework | P04.1 |
| ADR-027 | The `osm` connector | P04.2 |
| ADR-028 | The `atlas` connector | P04.3 |
| ADR-029 | Splink 4 on DuckDB for the probabilistic ER tiers 4–5, as a fully-specified deterministic model | P05.1 |
| ADR-030 | The review queue and the LLM-extraction scaffolding as library + CLI, in `resolution` and `parsing` | P05.2 |
| ADR-031 | A minimal count-reconciliation seed, and the three missing count predicates, for the P06.1 vertical slice | P06.1 |
| ADR-032 | A minimal slice dossier renderer, with a print-CSS PDF path, ahead of the production surface | P06.1 |
| ADR-033 | The layered document-parsing stack as the parser interface every connector extracts through, in `parsing` | P07.1 |
| ADR-034 | The `records` connector | P07.2 |
| ADR-035 | The `procurement` connector | P07.3 |
| ADR-036 | The §29 reconciliation workflows as value-object modules layered on the resolver | P08.2 |
| ADR-037 | The materialized Contradiction entity, its lifecycle, and the byte-identical L3 rebuild | P08.3 |
| ADR-038 | The coverage-metrics layer, its home in `inference`, and the executable capture–recapture prohibition | P09.1 |
| ADR-039 | The research-task engine | P10.1 |
| ADR-040 | The §33.2 detector catalog and the §31 contradiction→task map | P10.2 |
| ADR-041 | The records-request generator | P10.3 |
| ADR-042 | The `flock_portal` connector | P11.1 |
| ADR-043 | The `audit_structural` connector | P11.2 |
| ADR-044 | The usage-analytics boundary | P12.1 |
| ADR-045 | Access-path closure | P12.2 |
| ADR-046 | Policy/LegalInstrument surfaces, the never-merged invariant, and the SIG-EPIS-030 general form | P13.2 |
| ADR-047 | The public read API | P14.1 |
| ADR-048 | Bulk exports | P14.2 |
| ADR-049 | The epistemic visual language and the no-JS, archivable web shell | P15.1 |
| ADR-050 | The production local-dossier surface | P15.2 |
| ADR-051 | The infrastructure map + network explorer (with the static-PMTiles serving contract) | P15.3 |
| ADR-052 | The renewal watch, evidence recommender, and evidence viewer | P15.4 |
| ADR-053 | The research queue, public corrections log, methodology/metrics pages, and the editorial-standards conformance gate | P15.5 |
| ADR-054 | The contributor system | P16.1 |
| ADR-055 | No direct automated OSM writes (the human-mediated suggestion workflow; records the spec's logical "ADR-017", §35.2) | P16.2 |
| ADR-056 | The jurisdiction adapter framework (country-namespaced vocabularies, BCP-47 labels, `canonical_name` scalar) | P18.1 |
| ADR-057 | The France/Belgium (Technopolice) connectors | P18.2 |
| ADR-058 | Tickets and build memory are committed; agent scratch is unified | P19.1 |
| ADR-059 | Capstone spine wiring (`PgClaimSink`, `PgReadStore`, the compute-on-read seam) | P19.4 |
| ADR-060 | The resolver (P08.1) — retro-fitted record | P08.1 (retro-fitted by P19.5) |
| ADR-061 | Capstone gap closure (export gate, jurisdiction-conditional web render, ER over PostgreSQL) | P19.5 |
| ADR-062 | Spec reconciliation after the 46-ticket build (Appendix F/G, applied amendments A1–A8, fold-back ids) | P20.2 |
| ADR-063 | Registry review metadata and the flip rule (the `rights_reviewed_by`/`rights_reviewed_on`/`review_packet` fields, `review-status`, the 27 rights packets, the Stage-0 outreach record) | P21.1 |
| ADR-065 | Live connector wiring (the `HttpxTransport` over `httpx`, the `OcflCaptureStore` adapter, and the gated `sig-connectors run --mode live\|replay\|shadow` CLI that refuses a live fetch — exit 3 — for any non-green source and owns the content-free fetch-record format) | P21.3 |
| ADR-066 | Runtime composition (`sig-ops` + `ops/docker-compose.yml`) and the export-backed web data layer (`web/src/lib/data.ts`, `SIG_DATA_SOURCE=fixtures\|export`); the jurisdiction export emits `web/dossiers.json`; crosses LD-V08 | P21.4 |
