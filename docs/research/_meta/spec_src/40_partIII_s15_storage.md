# Part III — Data architecture

## 15. Storage architecture

### 15.1 The decision

**SIG-STORE-001 (MUST).** Canonical storage MUST be **PostgreSQL ≥ 18 with PostGIS ≥ 3.6.3**.
Every other store — graph, RDF, analytics, tiles, search — MUST be a **derived projection** that
can be dropped and rebuilt from canonical data plus the evidence store. *(R6-F1, R6-F3,
REQ-R6-01.)*

This answers OL-Q20 ("relational/PostGIS with graph projections, a property graph, RDF, or
hybrid?") decisively: **hybrid, with a relational core.** It answers OL-Q21 ("which model best
supports claim-level provenance and bitemporal history?") with a qualification that matters:
RDF-star and Wikibase model *provenance* best, and XTDB models *bitemporality* best, but neither
can carry SIG's geospatial, access-control, and constraint requirements. Postgres can carry all
of them and can *emit* the other two as projections. The reverse is not true.

### 15.2 The evaluation

Scored against a weighted scorecard (R6 Part 2). Summary:

| Option | Score | Verdict |
|---|---|---|
| **Hybrid: Postgres+PostGIS canonical + derived projections** | **214** | **Adopted** |
| Postgres-only, no projections | 190 | Rejected: no interoperable RDF/analytics story |
| RDF/triplestore canonical | 142 | Rejected: fails on geospatial and write throughput |
| XTDB v2 canonical | 125 | Rejected: best bitemporal semantics, but no geospatial story, thin ecosystem, single-vendor governance |
| Native labelled property graph | 93 | Rejected: reification bloat; licensing |

**SIG-STORE-002 (MUST).** No component MAY be adopted as canonical if its access control,
backup, or production use requires a commercial or source-available (non-OSI) licence.
*(REQ-R6-04.)* The concrete exclusions, verified rather than assumed:

| Candidate | Disqualifying fact (verified 2026-08) |
|---|---|
| Kuzu | Repository archived 2025-10-10. Not viable. |
| Neo4j Community | GPLv3; RBAC and online backup are Enterprise-only — precisely the features SIG's sensitivity tiers need. |
| Memgraph Community | BUSL-1.1: source-available, not open source. |
| TigerGraph Community | Terms could not be verified. Excluded by SIG-STORE-002's default-deny. |
| Citus | AGPL-3.0; and columnar-in-Postgres is an unstable field (pg_mooncake stalled). |

**SIG-STORE-003 (MUST).** The system MUST start, ingest, resolve, and serve with **zero
non-PostGIS extensions installed**. Apache AGE, `pgvector`, `pg_ivm`, and `h3-pg` are optional
accelerants, never load-bearing. *(REQ-R6-05.)* This is a deliberate hedge: extension
availability on managed Postgres is volatile, and a public-interest project must not be
one hosting-provider decision away from being unable to run.

### 15.3 Why the relational core is not a compromise

The reasoning is worth recording, because "knowledge graph" invites a graph database by reflex.

1. **SIG's write path is not graph-shaped.** It is a high-volume append of typed assertions with
   constraints, temporal ranges, and geometry. That is Postgres's home ground.
2. **Claim-level provenance in an LPG requires reification.** Attaching source, time, method,
   and confidence to an *edge* forces either edge properties (which cannot themselves carry
   provenance) or reifying every edge as a node — at which point the graph database is storing a
   relational model badly. *(R6-F18.)*
3. **Bitemporality in an LPG is application discipline, not a database feature.** *(R6-F19.)*
   SIG's whole thesis rests on temporal correctness; putting it in application code is
   unacceptable.
4. **PG 18 ships the temporal primitives natively**: SQL:2011-style `PERIOD` / `WITHOUT OVERLAPS`
   constraints and `uuidv7()`. *(R6-F2.)*
5. **Row-level security gives per-row sensitivity tiers** (§43.3) without a commercial licence.
   *(R6-F8.)*
6. **PostGIS has no rival.** A project whose physical layer is 558,645 OSM elements cannot treat
   geospatial as an afterthought.
7. **The interoperability need is a *file* problem, not a *server* problem.** Downstream users
   want Parquet, GeoJSON, PMTiles, JSON-LD, and a SQLite bundle. Those are exports, and exports
   are cheap from Postgres.

### 15.4 The projections

**SIG-STORE-004 (MUST).** The following projections MUST be rebuildable from canonical state by
a single documented command, and a CI job MUST rebuild each from scratch and verify it.

| Projection | Technology | Purpose | Rebuild trigger |
|---|---|---|---|
| **Resolution read models** | Postgres materialized tables | Fast entity-with-attributes reads for API/UI | Ruleset or claim change |
| **Analytics** | Hive-partitioned Parquet + DuckDB | High-volume usage aggregates, off the transactional store | Nightly |
| **RDF / JSON-LD** | Named-graph serialization (PROV-O + SIG terms) | Semantic-web interoperability, claim-level provenance interchange | Per release |
| **Map tiles** | PMTiles v3 via tippecanoe | Static public map | Per release |
| **Search index** | Postgres FTS by default; Typesense/Meilisearch optional | Entity and document search | Continuous |
| **Graph query** | Apache AGE (optional) or an exported edge list | Network analytics, Cypher exploration | On demand |
| **Datasette/SQLite bundle** | SQLite export | Offline exploration, archival, teaching | Per release |

**SIG-STORE-005 (MUST).** No projection may be the sole home of any fact. Losing every
projection simultaneously MUST cost only compute, never information.

### 15.5 Architecture Decision Records

**SIG-STORE-006 (MUST).** Each of the following decisions MUST be recorded as an ADR under
`docs/adr/` at Phase 1, using a consistent template (context, decision, status, consequences,
alternatives considered, revisit triggers):

| ADR | Decision |
|---|---|
| ADR-001 | PostgreSQL 18 + PostGIS as canonical store; everything else a projection |
| ADR-002 | Append-only claim table; entity tables hold identity only |
| ADR-003 | Two interval time dimensions + one ordering scalar |
| ADR-004 | EDTF for uncertain dates |
| ADR-005 | Resolution as a stored decision record, not a view |
| ADR-006 | OCFL 1.1 evidence store on object storage with governance-mode Object Lock |
| ADR-007 | LinkML as the single ontology source of truth |
| ADR-008 | SKOS for published controlled vocabularies |
| ADR-009 | SPDX expressions for per-source licensing, with a build-time compatibility gate |
| ADR-010 | DuckDB/Parquet analytics boundary; no raw audit rows anywhere |
| ADR-011 | The ODbL posture (§42.3) |
| ADR-012 | Sensitivity tiers enforced by RLS, applied at the view layer |

**SIG-STORE-007 (MUST).** Every ADR MUST name its **revisit trigger** — the observable condition
under which the decision should be reconsidered. An ADR with no revisit trigger is incomplete.

---
