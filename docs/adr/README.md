# Architecture Decision Records (Appendix F)

Every architectural decision is recorded here under a consistent template
(context, decision, status, consequences, alternatives considered, and a
**revisit trigger**). An ADR with no revisit trigger is incomplete
(SIG-STORE-007); `tests/unit/test_policy_adrs.py` enforces this mechanically.

Decisions are immutable: a change is a **new ADR** (SIG-ENG-003), never an edit
of a landed one.

## Index

| ADR | Decision |
|---|---|
| ADR-001 | PostgreSQL 18 + PostGIS as the canonical store; everything else a projection |
| ADR-002 | Append-only claim table; entity tables hold identity only |
| ADR-003 | Two interval time dimensions + one ordering scalar |
| ADR-004 | EDTF for uncertain dates |
| ADR-005 | Resolution as a stored decision record, not a view |
| ADR-006 | OCFL 1.1 evidence store on object storage with governance-mode Object Lock |
| ADR-007 | LinkML as the single ontology source of truth |
| ADR-008 | SKOS for published controlled vocabularies |
| ADR-009 | SPDX expressions for per-source licensing, with a build-time compatibility gate |
| ADR-010 | DuckDB/Parquet analytics boundary; no raw audit rows anywhere |
| ADR-011 | The ODbL posture (§42.3) — OSM-derived assets in a separate compartment |
| ADR-012 | Sensitivity tiers enforced by RLS, applied at the view layer |
| ADR-013 | uv as the workspace and lockfile tool |
| ADR-014 | Astro for the public web surface |
| ADR-015 | AWS S3 evidence store + CloudFront for bulk-export delivery (reconciling §38.5 egress) |
| ADR-016 | Dagster OSS for orchestration, kept reversible |
| ADR-017 | FastAPI for the read API |
| ADR-018 | MapLibre GL for the web map |
| ADR-019 | pytest + Hypothesis for testing |
| ADR-020 | GitHub Actions for CI |
| ADR-021 | Source registry as seeded data, with a runtime ingestion gate in `connectors` (P00.4) |
| ADR-022 | Defer physical partitioning of `claim` to preserve the `claim_id` FK contract (P02.1) |
| ADR-023 | An `evidence/` package + content-addressed blob dedup for the capture row (P02.2) |
| ADR-024 | A pinned, deterministic, in-repo EDTF envelope derivation (P02.3) |
| ADR-025 | Temporal invariants as pipeline data-quality checks; as-of as SQL functions (P02.3) |
| ADR-026 | The eight-stage connector framework: fetch-only egress + socket-level network-isolated replay (P04.1) |
| ADR-027 | The `osm` connector: versioned tag vocabulary, `(type,id,version)` keying, ODbL landing (P04.2) |
| ADR-028 | The `atlas` connector: family-level `deployment_exists`, agency-id keying, category-retirement-not-a-world-change (P04.3) |
| ADR-029 | Splink 4 on DuckDB for the probabilistic ER tiers 4–5, as a fully-specified deterministic model (P05.1) |
| ADR-030 | Review queue + LLM-extraction scaffolding as a library plus CLI (P05.2) |
| ADR-031 | A minimal count-reconciliation seed + the three missing count predicates, for the vertical slice (P06.1) |
| ADR-032 | A minimal slice dossier renderer with a print-CSS PDF path, ahead of the production surface (P06.1) |
| ADR-033 | The layered document-parsing stack as the parser interface every connector extracts through (P07.1) |
| ADR-034 | The `records` connector: targeted-lookup posture, MuckRock api_v2 + short-lived JWT, and the `no_responsive_records` → coverage bridge (P07.2) |

ADR-001…012 are the §15.5 decision set; ADR-013…020 are the stack ADRs. The
egress question of §38.5 is resolved for the whole project in ADR-015. ADR-021 is
the P00.4 source-registry decision; ADR-022 is the P02.1 claim-spine partitioning
decision; ADR-023 is the P02.2 evidence-store package + blob-dedup decision;
ADR-024 and ADR-025 are the P02.3 temporal-semantics decisions (the EDTF envelope
function, and the invariant/as-of enforcement surfaces). ADR-026 is the P04.1
connector-framework decision (the eight-stage contract, fetch-only egress, and
socket-level network-isolated replay). ADR-027 is the P04.2 `osm`-connector
decision (the versioned tag vocabulary, `(type,id,version)` keying,
history-derived `first_observed`, snapshot-diff deletion, and ODbL landing).
ADR-028 is the P04.3 `atlas`-connector decision (family-level `deployment_exists`,
agency-id keying with a surrogate fallback, and category-retirement-as-vocabulary
event). ADR-029 is the P05.1 probabilistic-ER decision (Splink 4 on DuckDB as a
fully-specified, deterministic, versioned-as-data model for cascade tiers 4–5, with
sized blocking, the gold set + frozen holdout, and the §14.7 quality gates).
ADR-030 is the P05.2 review-queue + LLM-extraction decision (the boundary as a
library plus CLI). ADR-031 and ADR-032 are the P06.1 vertical-slice decisions: a
minimal count-reconciliation seed plus the three missing §29.1 count predicates
(ahead of the Phase-8 engine), and a minimal §39.2 dossier renderer with a
print-CSS PDF path (ahead of the P15.2 production surface). ADR-033 is the P07.1
layered-parsing-stack decision (the §24 parser interface every connector extracts
through: the seven-layer cheapest-sufficient enum, byte/zip-manifest classification
with per-member archive handling, the six-kind locator schema, the `raw_value`
contract, the versioned reversible reason-code mapping, and the fixtures + canary
parser-drift defences — no new heavy dependency and no DDL). ADR-034 is the P07.2
`records`-connector decision (MuckRock/NextRequest/DocumentCloud as a targeted-lookup
client that cannot be configured into a crawler; MuckRock api_v2 with a five-minute
JWT that refreshes early and on a 401 and rides an additive per-request `headers`
seam on the shared fetcher; the `no_responsive_records` → `NO_EVIDENCE_FOUND`
coverage bridge reusing `db.absence`; the predicate allowlist and candidate-only
party keying; released documents captured as `EvidenceArtifact` rows and classified
through the P07.1 parser, with the extraction engines still deferred).
