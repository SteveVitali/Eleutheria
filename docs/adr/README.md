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
| ADR-035 | The `procurement` connector: cooperative-piggyback → parent award, USAspending sub-award tracing, the `FundingInstrument` runtime shape, the published agenda-platform tenant registry, and `artifact_type` as an ontology vocabulary (P07.3) |
| ADR-036 | The reconciliation workflows layered on the resolver (P08.2) |
| ADR-037 | The materialized `Contradiction` entity, its lifecycle, and the byte-identical L3 rebuild (P08.3) |
| ADR-038 | The coverage-metrics layer in `inference`, reuse of `db.absence`/currency, and the executable capture–recapture prohibition (P09.1) |
| ADR-039 | The research-task engine: detector/closing-condition as callables, the `resolved_no_evidence_exists`→`CoverageRecord` bridge, and executable anti-abuse (P10.1) |
| ADR-040 | The §33.2 detector catalog (34 registered task types) and the §31 contradiction→task map, cross-checked against `CONTRADICTION_TYPES` (P10.2) |
| ADR-041 | The records-request generator: the 51-jurisdiction records-law table + templates as versioned data, `not_researched` (not `searched_not_found`) for the residency barrier, local-filer routing, measured template success rates, and the consent gate (P10.3) |
| ADR-042 | The `flock_portal` connector: portal claims in their own CC-BY-SA-4.0 compartment (export merge with the CC-BY graph fails the build), change detection + back-fill keyed on the upstream `data_last_updated` snapshot field (never fetch time), a challenge honoured as a refusal, the §29.3 sharing-edge + §29.7 snapshot-diff reconcilers invoked (not forked) with only deterministic edges in the claim stream, and the SIG-INGEST-031 fallbacks retained as named routes (P11.1) |
| ADR-043 | The `audit_structural` connector: agency Flock audit CSVs parsed into **structural aggregates only** (per-search rows read transiently, aggregated, dropped — `assert_no_per_row_output` as the §18.1 schema gate), the audit `Camera Count` as an independent `active_device_count` claim reconciled by P08.2's §29.1 count reconciler (never merged), `SharedNetworks.csv` as directional configured-access edges via P08.2's §29.3 reconciler (blanks negative, `valid_from_kind='unknown'`), `***` redaction as a distinct recorded state (`classify_cell`), the four audit source types as a closed non-interchangeable set, and a new `agency_audit_export` source (not the derived HIBF export, SIG-INGEST-046a) with the schema as versioned data (P11.2) |
| ADR-044 | The usage-analytics boundary (§18): the `db.analytics` substrate over DuckDB-written **Hive-partitioned Parquet** (SIG-STORE-027, no columnar Postgres extension, no `pyarrow`), the bright line as a columnar schema property (`ANALYTICS_COLUMNS` carries UUIDs + period + facts + lineage, **no plate-capable and no name column**, SIG-STORE-025/026), the join enforced structurally to `{searching_org_id, source_org_id, period}` with `ingest_run_id`+`agg_ruleset_version` lineage (a name key is a hard `JoinKeyError`, SIG-STORE-028), partition-as-evidence (each partition content-addressed with the interop multihash and cited by a *summary* claim, SIG-STORE-029), and rationale-driven small-cell suppression in `db.suppression` (institutional-conduct publishes even when small; individual small cells suppress to `null`+`suppressed_flag`+`k_threshold`, never zero; ambiguous → suppress + review task; complementary suppression for non-invertibility; one-month floor; k=5 as SIG's own policy with the stricter partner threshold winning, SIG-STORE-030/031/032/033) (P12.1) |
| ADR-045 | Access-path closure (§30.2) as the `inference.access_paths` value-object module: only `configured_access` and `federates_search_to` compose (`observed_use`/`declared_policy`/query-direction `distributes_list_to` never do, and no hop's §12.2 kind is ever merged, SIG-ONTO-042/SIG-RECON-049), edges normalized into accessor→provider terms, scope may not broaden along a chain and a path's scope is its narrowest hop, every hop must be valid at the as-of time (an expired hop taints the path `historical`; single-snapshot edges always valid, SIG-ONTO-044), confidence is the **path minimum** never the average, a hard `MAX_PATH_HOPS` enumeration cap and a published `SPECULATIVE_HOP_THRESHOLD` beyond which a path is **speculative** and excluded from headline figures (SIG-RECON-050), every hop carries evidence and the full hop list survives into the L4 `Inference` (SIG-RECON-047/048/049); plus tightening `AccessRelationship.automaticity` to **required** (SIG-ONTO-049) (P12.2) |
| ADR-046 | Policy/legal instruments (§§11.13–11.14): the `Policy` / `LegalInstrument` predicate surfaces and the §29.6 divergence reconciler are consumed from P01.1 / P08.2 (no schema change, generation gate untouched), so P13.2 lands as the ticket's acceptance tests (`Policy`/`LegalInstrument` predicate surfaces; `Policy` ≠ `ConfigurationState` never merged at schema **and** resolution layer, SIG-ONTO-034/SIG-RECON-044) plus `connectors.curated_index` — the **general form** of SIG-EPIS-030: a `CuratedSourceIndex` held as an index whose `index_records()` are `index_only` and whose `as_claims()` raises, with the P13.1 `accountability` Abuse Library path refactored to build a `CuratedIndexEntry` (byte-identical row shape, additive) (P13.2) |
| ADR-047 | The public read API (§37): a hand-written, versioned FastAPI contract (OpenAPI generated, never a schema reflection, SIG-API-001) built over a `ReadStore` seam with an in-memory implementation (no in-Python DB fetch layer exists yet). Every material fact leaves only inside a `ResolutionEnvelope` (SIG-API-002) with a coverage statement (SIG-API-003) and — for collections/entities — a computed licence + upstream attribution reusing `policy.licensing` (SIG-API-004); every read echoes the two-axis as-of pair via `db.temporal.AsOf` (SIG-API-005) and cacheability follows belief-pinning (`belief_pinned = not belief_defaulted`; explicit belief → immutable, defaulted → `no-store`, SIG-API-006); belief-time filtering makes a belief-pinned citation reproducible after a correction. `/id/{type}/{uuid}` content-negotiates HTML/JSON-LD/RDF (SIG-API-008); `/changes` reuses `reconcile.snapshot_diff.diff_series` (SIG-API-009). The prohibited-endpoint bar is fail-closed at app construction plus a per-person entity-type guard (SIG-API-012); sealed/restricted captures are served only as their SIG-EVID-009/010 public representation (bytes never), coordinates reduced by `policy.sensitivity.apply_tier`; `assert_public_visibility` refuses `restricted`/`sealed` records to every tier (SIG-API-011); `/export` is index-only (P14.2 owns bulk); GraphQL (SIG-API-010) is deliberately not the only surface (P14.1) |

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
through the P07.1 parser, with the extraction engines still deferred). ADR-035 is the
P07.3 `procurement`-connector decision (cooperative-piggyback contracts that cannot be
recorded without their ridden master award, SIG-ONTO-032; USAspending **sub-awards**
pulled — not only prime awards — and traced to a local deployment via `federal_award_id`,
SIG-ONTO-033; the `FundingInstrument` runtime shape making funder ≠ recipient ≠ purchaser
enforced; the published `data/agenda_tenants.toml` municipality→platform tenant registry
the connector reads its targets from, with discovery negatives retained as `db.absence`
coverage records ahead of P09.1, SIG-METRIC-002a; and `artifact_type` promoted to a
controlled `ArtifactType` ontology enum carrying the SIG-INGEST-047 additions).
