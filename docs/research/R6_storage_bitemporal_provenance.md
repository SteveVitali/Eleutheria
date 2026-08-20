# R6 — Canonical Storage, Bitemporality, Claim-Level Provenance, and Graph Modeling

**Workstream:** R6
**Researched:** 2026-08-20
**Researcher:** claude-opus-5 (SIG research agent R6)
**Outline sections covered:** §6.3, §6.4, §6.5, §6.7, §8 (whole ontology), §9 (all), §13.3, §13.4, §14.2, §19 (all), §20 (Q17–Q22, Q25, Q30–Q32, Q37)
**Outline questions answered:** Q20, Q21, Q22, Q25 (primary); Q17, Q18, Q19, Q30, Q31, Q32, Q37 (partial, storage-side only)
**Confidence in this file overall:** high

---

## 0. Executive decision (read this if you read nothing else)

**Primary recommendation: Option 4 — Hybrid, with PostgreSQL 18 + PostGIS 3.6 as the single canonical
store, an append-only `claim` table as the only writable fact surface, and everything else (graph, RDF, analytics,
tiles, search) as *derived, rebuildable projections*.**

Concretely:

| Layer | Technology | Role | Rebuildable from canonical? |
|---|---|---|---|
| Canonical | PostgreSQL 18.x + PostGIS 3.6.4 | append-only claims, entities, evidence metadata, resolution decisions | — (this is the source of truth) |
| Evidence bytes | OCFL 1.1 storage root on S3-compatible object storage with Object Lock | immutable, content-addressed source artifacts | — (co-canonical, verified by digest) |
| Graph query | Recursive CTEs + a `edge_current` materialized view; **optionally** Apache AGE 1.8 for openCypher | path/network queries | yes |
| RDF export | Oxigraph 0.5.x (or plain N-Quads dumps) built from claims via named graphs + PROV-O | interoperability, SPARQL for outside researchers | yes |
| Analytics | DuckDB 1.5.x over Parquet (Hive-partitioned), optionally DuckLake 1.0 for snapshots | HIBF-scale usage aggregates | yes |
| Vector name search | `pgvector` 0.8.x inside the canonical DB | entity-resolution candidate generation only | yes |
| Map tiles | `tippecanoe` → PMTiles v3 on static hosting; `martin` only if dynamic tiles are needed | public map | yes |
| Schema authoring | LinkML 1.11.x → SQL DDL + JSON Schema + OWL/SHACL + Pydantic + docs | one schema, many artifacts | — (schema source) |

**Temporal model: three recorded time dimensions, two of them queryable as `AS OF`.**
Valid time (interval, may be EDTF-fuzzy), transaction time (interval, DB-controlled, append-only), and observation
time (instant, source-controlled). Publication time and retrieval time are properties of the *evidence artifact*, not
of the claim, and must not be stored on the claim. See §B.

**Rejected as canonical:** Neo4j (GPLv3 + Enterprise-gated RBAC/backup — see F6.14/F6.15),
Memgraph (BUSL-1.1, not open source — F6.16), Kuzu (repo archived 2025-10-10 — F6.13), XTDB v2 (best-in-class
bitemporality but immature ecosystem, no geospatial, single-vendor — F6.21), pure RDF triplestore (claim-level
provenance is fine, geospatial + write throughput + operational burden are not — F6.24–F6.30).

**The single most important architectural rule:** the `claim` table is append-only and never updated
in place; the "current truth" is a *separately computed, separately versioned* `resolution` table that records **which
claim won and why**. Contradiction is therefore not an error state — it is the normal shape of the data, and the
resolver's output is itself an auditable, reproducible artifact.

---

## Part 1 — Option evaluation findings

### F6.1 — PostgreSQL 18 is current, supported to 2030, and PG 14 goes EOL in Nov 2026

**Claim:** PostgreSQL 18 (18.6 as of Aug 2026) is the current major version, first released 2025-09-25,
EOL 2030-11-14; PostgreSQL 14 reaches EOL 2026-11-12.
**Status:** VERIFIED
**Evidence:** https://www.postgresql.org/support/versioning/ — support table lists 18 (18.6, first release
2025-09-25, final 2030-11-14), 17 (17.11), 16 (16.15), 15 (15.19), 14 (14.24, final release 2026-11-12). Five-year
support window per major.
**Retrieved:** 2026-08-20
**Implication for the spec:** Target PostgreSQL 18 as the minimum. Do not build on 14 — it dies inside
the likely Stage-1 build window. The 18 requirement is not gratuitous: temporal constraints and `uuidv7()` (F6.2) are
both 18-only and both are load-bearing for this design.
**Outline delta:** EXTENDS §20 Q20 — the outline does not name a version floor; the spec must.

---

### F6.2 — PostgreSQL 18 adds native SQL:2011-style temporal constraints and `uuidv7()`

**Claim:** PG18 supports `PRIMARY KEY (... , period WITHOUT OVERLAPS)`, `UNIQUE (... WITHOUT OVERLAPS)`,
and `FOREIGN KEY (..., PERIOD ...)`, plus a built-in `uuidv7()` function producing temporally sortable UUIDs.
**Status:** VERIFIED
**Evidence:** https://www.postgresql.org/docs/18/release-18.html — "Allow the specification of
non-overlapping `PRIMARY KEY`, `UNIQUE`, and foreign key constraints (Paul A. Jungwirth) … This is specified by
`WITHOUT OVERLAPS` for `PRIMARY KEY` and `UNIQUE`, and by `PERIOD` for foreign keys, all applied to the last specified
column." And: "Add `UUID` version 7 generation function `uuidv7()` (Andrey Borodin) … This `UUID` value is temporally
sortable." Also confirmed: asynchronous I/O subsystem (`io_method`), virtual generated columns (now the default),
btree skip scan, OAuth auth, `OLD`/`NEW` in `RETURNING`.
**Retrieved:** 2026-08-20
**Implication for the spec:** (a) Use `tstzrange` + `WITHOUT OVERLAPS` for the *resolution* table
(exactly one resolved value per subject/predicate per instant) — this makes "no overlapping resolved states" a
database invariant rather than application discipline. (b) Do **not** apply `WITHOUT OVERLAPS` to the `claim` table;
overlapping claims are the entire point. (c) Use `uuidv7()` for claim IDs: index locality on an append-only
high-volume table matters, and the embedded millisecond timestamp gives a free, coarse ingestion-order key.
**Outline delta:** EXTENDS §6.3 — the outline asks for temporality as a modelling discipline; PG18 lets
part of it be enforced by constraint. This is new since the outline was written.

---

### F6.3 — PostGIS 3.6.x is current, works with PG 12–18, and 3.7 dev already targets PG 19

**Claim:** PostGIS 3.6.0 released 2025-09-02; 3.6.2 (2026-02-06), 3.6.3 (2026-04-14, security), 3.6.4
(2026-06-08) followed; PostGIS 3.7.0dev builds against PostgreSQL 14–19beta2.
**Status:** VERIFIED
**Evidence:** https://postgis.net/docs/manual-dev/postgis_installation.html — describes "PostGIS 3.7.0dev",
"can be built against PostgreSQL versions 14 - 19beta2". Release cadence corroborated via
https://postgis.net/2026/04/PostGIS-Patch-Releases/ and https://postgis.net/news/ (3.6.2 Feb 2026,
3.6.3 Apr 2026 bugfix+security for 3.2–3.6, 3.6.4 Jun 2026). PostGIS 3.6 requires GEOS 3.8+ (optimized
for GEOS 3.14+) and Proj 6.1+.
**Retrieved:** 2026-08-20
**Implication for the spec:** Pin `PostGIS >= 3.6.3` (the April 2026 release was a *security* release —
older 3.6.x must not be shipped). PostGIS's own release cadence is comfortably ahead of PG majors, so the
Postgres-canonical choice does not create a geospatial lag risk.
**Outline delta:** CONFIRMS §20 Q20's implicit assumption that PostGIS is viable.

---

### F6.4 — `pgvector` 0.8.6 supports PG13+, HNSW/IVFFlat, halfvec/bit/sparsevec

**Claim:** pgvector 0.8.6 is current; supports Postgres 13+; HNSW and IVFFlat indexes; 16,000 dims for
`vector`/`halfvec`, 64,000 for `bit`; indexable dims 2,000 (`vector`), 4,000 (`halfvec`), 64,000 (`bit`).
**Status:** VERIFIED
**Evidence:** https://github.com/pgvector/pgvector — version 0.8.6, "Postgres 13+", index/dimension table
as stated. GitHub API reports license `NOASSERTION` (it is in fact the PostgreSQL License in `LICENSE`; GitHub's
classifier does not recognize it — recorded as a caveat, not a risk).
**Retrieved:** 2026-08-20
**Implication for the spec:** Name embeddings for organization/agency candidate generation live in the
canonical DB, no separate vector service. Use `halfvec(768)` or `halfvec(1024)` with HNSW — well inside the 4,000-dim
indexable limit and half the storage. **Constraint:** embeddings are for *candidate generation into a review queue
only*, never for automatic writes (outline §20 Q28 agrees).
**Outline delta:** CONFIRMS §20 Q28 — vector search stays on the suggestion side of the human-review line.

---

### F6.5 — Apache AGE 1.8.0 claims PG 11–18 but ships per-PG branches and an RC for PG18

**Claim:** Apache AGE is Apache-2.0, current release v1.8.0, README claims support for Postgres 11–18,
but the newest GitHub release artifact is tagged `PG18/v1.8.0-rc0` (2026-07-09) — i.e. PG18 support is
release-candidate quality, not GA.
**Status:** PARTIALLY VERIFIED
**Evidence:** https://github.com/apache/age and https://github.com/apache/age/blob/master/README.md —
"Postgres 11, 12, 13, 14, 15, 16, 17 & 18", "Supporting the latest versions is on AGE roadmap", Apache-2.0, 4.7k
stars. GitHub API `releases/latest` for `apache/age` returns tag `PG18/v1.8.0-rc0` published 2026-07-09; repo pushed
2026-08-20 (actively developed). The per-PG-version release tagging scheme is itself the finding: AGE maintains
parallel branches per Postgres major, and the newest major lands as an RC first.
**Retrieved:** 2026-08-20
**Implication for the spec:** **Do not make Apache AGE load-bearing.** Treat openCypher-in-Postgres as a
*convenience projection* that can be turned off. Two concrete risks: (a) AGE upgrades are coupled to
Postgres major upgrades and historically lag them; (b) AGE stores graph data in its own `ag_catalog` schema — if
claims lived there, a Postgres upgrade could strand canonical data. Keep canonical data in plain relational tables; if
AGE is installed, populate its graph from the resolution view, and be willing to drop the extension entirely.
**Outline delta:** CORRECTS the implicit hope in §20 Q20 that "graph projections" means a graph engine.
For SIG's edge counts (tens of thousands to low millions of sharing edges), a recursive CTE over an indexed `edge`
table outperforms the operational risk of an extension that gates Postgres upgrades.

---

### F6.6 — `pg_ivm` 1.15 supports PG13–18 but cannot maintain views over partitioned tables

**Claim:** pg_ivm (PostgreSQL License, v1.15, 2026-06-30) provides immediate incremental view maintenance
for a restricted SQL subset; base tables must be *simple tables* — partitioned tables, views, matviews and foreign
tables are not allowed as base tables.
**Status:** VERIFIED
**Evidence:** https://github.com/sraoss/pg_ivm — supports PG 13–18; supports inner/outer joins (with
restrictions), `DISTINCT`, `count/sum/avg/min/max`, simple `FROM` subqueries, `EXISTS` in `WHERE`, simple CTEs.
Unsupported: "Window functions, `HAVING`, `ORDER BY`, `LIMIT`/`OFFSET`, `UNION`/`INTERSECT`/`EXCEPT`, `DISTINCT ON`,
`TABLESAMPLE`, `VALUES`, and `FOR UPDATE`/`SHARE`"; also no recursive CTEs, no user-defined aggregates, no aggregates
with outer joins, no logical replication. "Base tables must be simple tables." GitHub API: v1.15, pushed 2026-08-06,
1.47k stars.
**Retrieved:** 2026-08-20
**Implication for the spec:** pg_ivm is **not** suitable for the resolution view. The resolver needs
window functions (`row_number() OVER (PARTITION BY subject, predicate ORDER BY tier, observed_at DESC)`) which pg_ivm
explicitly cannot do, and the `claim` table will be partitioned. Use a plain `MATERIALIZED VIEW ... REFRESH
CONCURRENTLY` or — better — a *resolver job* that writes an actual `resolution` table (see D6.3), because we need to
store *rationale*, not just a value. pg_ivm may still be used for cheap denormalized counters (e.g.
`claim_count_by_subject`) built on unpartitioned tables.
**Outline delta:** CORRECTS the natural reading of §6.5 that resolution can be "just a view". It cannot:
the outline itself demands a stored `rationale`, and a rationale is a *decision record*, not a projection.

---

### F6.7 — `pg_graphql` 1.6.1 exists and is Apache-2.0, but is reflection-driven

**Claim:** `supabase/pg_graphql` v1.6.1 (2026-05-07), Apache-2.0, 3.3k stars, actively maintained.
**Status:** VERIFIED
**Evidence:** GitHub API for `supabase/pg_graphql`: license `Apache-2.0`, latest release `v1.6.1`
published 2026-05-07, pushed 2026-08-03.
**Retrieved:** 2026-08-20
**Implication for the spec:** Available but **not recommended for the public API**. pg_graphql reflects
the physical schema, which would leak the append-only claim layout into a public contract and make schema evolution a
breaking-change generator. SIG's public API should be a hand-written, versioned read API over the *resolution* +
*claim* views (see REQ-R6-24). pg_graphql is fine for internal admin.
**Outline delta:** EXTENDS §15.7 — machine-readable exports must be versioned contracts, not schema mirrors.

---

### F6.8 — PostgreSQL row-level security gives per-row sensitivity tiers with restrictive policies

**Claim:** PG RLS supports permissive (OR-combined) and restrictive (AND-combined) policies, `USING` vs
`WITH CHECK`, `FORCE ROW LEVEL SECURITY` for owners, and `BYPASSRLS`; with RLS enabled and no policy, the default is
deny-all.
**Status:** VERIFIED
**Evidence:** https://www.postgresql.org/docs/18/ddl-rowsecurity.html — default-deny when enabled with no
policies; permissive policies combine with OR, `AS RESTRICTIVE` policies combine with AND; `FORCE ROW LEVEL SECURITY`
subjects the table owner to policies; superusers and `BYPASSRLS` roles skip checks; foreign-key/referential-integrity
checks always bypass RLS; `row_security = off` makes filtered queries error instead of silently returning fewer rows
(important for backups).
**Retrieved:** 2026-08-20
**Implication for the spec:** Implement §13.3/§13.4 coordinate and document sensitivity as **restrictive**
RLS policies keyed on a `sensitivity_tier` column, with the public API role holding no `BYPASSRLS`. Critically: set
`row_security = off` in the dump/export role so that an export which *would* have been silently filtered fails loudly
instead of quietly shipping an incomplete public dataset. Note the FK-bypass caveat: never make `sensitivity_tier`
enforcement depend on a table that is itself the target of an FK from a less-privileged table.
**Outline delta:** EXTENDS §13.3, §13.4 — the outline asks for tiered access but does not name a mechanism.
It also does not flag the silent-filtering hazard, which is a real path to accidentally publishing a dataset that
looks complete and is not.

---

### F6.9 — `periods` (SQL:2016 emulation) is effectively stalled at PG 9.5–15

**Claim:** The `periods` extension (PostgreSQL License, v1.2) implements SQL:2016 periods, `SYSTEM_TIME`
system versioning, `WITHOUT OVERLAPS` keys, temporal FKs, `AS OF`/`FROM..TO`/`BETWEEN` queries and `FOR PORTION OF` —
but documents support only for PostgreSQL 9.5–15.
**Status:** VERIFIED
**Evidence:** https://github.com/xocolatl/periods — "Version 1.2", "PostgreSQL 9.5–15", PostgreSQL
License, 320 stars, 151 commits, README says "pretty much feature complete" while noting many aspects still need work.
**Retrieved:** 2026-08-20
**Implication for the spec:** Do not adopt `periods`. Its two headline features are now (partly) native:
`WITHOUT OVERLAPS` and temporal FKs ship in PG18 (F6.2). The one genuinely useful thing it has that PG18 lacks is `FOR
PORTION OF` (surgically updating a slice of a valid-time interval) — SIG must implement that in application code or a
stored procedure. **`FOR PORTION OF` semantics matter and the spec must define them**: correcting "shared with ICE
from 2024-01 to 2026-03" to "…until 2025-11" is a *close-out correction*, and in an append-only model it is a new
claim plus a superseding resolution, never an UPDATE.
**Outline delta:** EXTENDS §6.3 — the outline's `valid_from`/`valid_to` sketch has no story for partial
interval correction. This is the single most common real-world temporal edit and needs an explicit design.

---

### F6.10 — `temporal_tables` is a trigger-based system-versioning extension, BSD-2, PG 9.2+

**Claim:** `arkhipov/temporal_tables` (BSD 2-clause, v1.2.2) provides system-period temporal tables via
AFTER triggers writing to a history table; application-period support is explicitly not included; documented support
through PG 15.
**Status:** VERIFIED
**Evidence:** https://github.com/arkhipov/temporal_tables — "Distributed under the terms of BSD 2-clause
license"; PostgreSQL 9.2+; Windows build docs mention up to 15; system-period only; custom system time supported for
warehouse loads; 70 commits.
**Retrieved:** 2026-08-20
**Implication for the spec:** Not needed, and recorded so the design does not drift toward it. SIG's
transaction time is not a hidden audit trail bolted onto mutable rows — it is the key structure of the claim table.
Trigger-based shadow-history extensions solve the *opposite* problem.
**Outline delta:** CONFIRMS §19.3 "Time before overwrite" — but the mechanism is append-only design, not
an extension.

---

### F6.11 — Citus is AGPL-3.0; pg_mooncake appears stalled; the "Postgres columnar" field is unstable

**Claim:** As of Aug 2026: `citusdata/citus` is AGPL-3.0 (v14.2.0, 2026-08-06, actively developed);
`Mooncake-Labs/pg_mooncake` (MIT) last released v0.1.2 on 2025-02-12 with the repo last pushed 2026-03-31;
`hydradatabase/hydra` returns 404 from the GitHub API (repository gone or renamed).
**Status:** VERIFIED (for Citus and pg_mooncake) / PARTIALLY VERIFIED (Hydra — absence confirmed, cause not)
**Evidence:** GitHub API `repos/citusdata/citus` → license `AGPL-3.0`, latest `v14.2.0` 2026-08-06,
12.7k stars, pushed 2026-08-20. `repos/Mooncake-Labs/pg_mooncake` → MIT, latest `v0.1.2` 2025-02-12, pushed
2026-03-31, 2.0k stars. `repos/hydradatabase/hydra` → HTTP 404 (no repository).
**Retrieved:** 2026-08-20
**Implication for the spec:** Do **not** put SIG's columnar analytics inside Postgres. The in-Postgres
columnar ecosystem has visible churn (one project 404s, one is ~18 months without a release) and Citus's AGPL-3.0 is a
licensing complication for a project that wants maximum reuse of its outputs. Use DuckDB + Parquet outside the
transactional database (F6.36, D6.9). This is a durability-of-choice argument as much as a technical one: a volunteer
project cannot absorb a dead-extension migration.
**Outline delta:** EXTENDS §20 Q22 — the outline asks *how* to keep aggregates separate; the answer is
"in a different engine entirely, on files, with a documented join key", not "a columnar extension".

---

### F6.12 — Postgres bitemporal patterns are well-trodden; SCD Type 2/4/6 is the same idea under another name

**Claim:** The dimensional-modelling literature's Slowly Changing Dimension Type 2 (new row per change with
start/end validity and a surrogate key) and Type 4 (separate current + history tables) are the warehouse-side
expression of valid-time versioning, and Type 6 hybridizes them.
**Status:** VERIFIED
**Evidence:** https://en.wikipedia.org/wiki/Slowly_changing_dimension — Type 0 (no change), Type 1
(overwrite, history destroyed), Type 2 ("multiple rows per entity using surrogate keys and timestamps… transactions
that reference a particular surrogate key are then permanently bound to the time slices defined by that row"), Type 3
(previous-value column), Type 4 (current + history tables), Type 6 (1+2+3 hybrid). Explicit tradeoff stated: "History
preservation versus query complexity."
**Retrieved:** 2026-08-20
**Implication for the spec:** SIG's `claim` + `resolution` split is structurally SCD Type 4 with a
bitemporal twist: `resolution` is the "current" table (queryable `AS OF` both dimensions), `claim` is the immutable
history. Naming this alignment matters because it means off-the-shelf BI tooling and any data-engineer volunteer will
recognize the shape immediately.
**Outline delta:** CONFIRMS §19.3.

---

### F6.13 — Kuzu is archived; do not adopt it

**Claim:** The `kuzudb/kuzu` repository was archived 2025-10-10 and is read-only; last release 0.11.3; MIT.
**Status:** VERIFIED
**Evidence:** https://github.com/kuzudb/kuzu — "The repository was archived on October 10, 2025, and is now
read-only." Latest release 0.11.3 bundling four extensions (algo, fts, json, vector). The project states prior
releases remain usable and that users should either move to 0.11.3 (which bundles extensions) or run a local extension
server, because the hosted extension server is going away. MIT License. Docs moved to kuzudb.github.io. Banner: "Kuzu
is working on something new!"
**Retrieved:** 2026-08-20
**Implication for the spec:** Remove embedded property graphs from consideration as canonical storage. The
*mechanism* of failure is instructive and should inform SIG's dependency policy: Kuzu's extension
distribution depended on a **vendor-hosted server** that was withdrawn, so even the archived releases degraded. SIG
must prefer dependencies whose full functionality is obtainable from a tarball.
**Outline delta:** CORRECTS §20 Q20 — an embedded MIT property graph was, until Oct 2025, the most
attractive "Option 2" candidate for a small team. It no longer exists as a live option.

---

### F6.14 — Neo4j Community is GPLv3 and the Enterprise features are the ones SIG would need

**Claim:** Neo4j Community Edition source is GPLv3; Enterprise Edition contains additional closed-source
components not in the repository and requires a commercial license; RBAC, multi-database, clustering, and online
backup are Enterprise-only.
**Status:** VERIFIED
**Evidence:** https://github.com/neo4j/neo4j — "Neo4j Community Edition is an open source product licensed
under GPLv3"; "Neo4j Enterprise Edition includes additional closed-source components _not available in this
repository_ and requires a commercial license from Neo4j or one of its affiliates." Current branch shown: version
2026.07 (calendar versioning). Edition split corroborated by
https://neo4j.com/docs/operations-manual/current/introduction/ (via search; the direct `/community-edition/` URL 403s
to automated fetch): Community provides only basic authentication with a single default user; Enterprise provides full
RBAC with permissions by label/relationship type/procedure, LDAP/AD/Kerberos, clustering, and online differential
backups, while Community relies on offline backup.
**Retrieved:** 2026-08-20
**Implication for the spec:** Fatal for canonical use. SIG's §13.3/§13.4 sensitivity tiers *require*
per-row/per-label access control, which is precisely the Enterprise gate. And "online backup is Enterprise" means a
volunteer-run Community deployment must stop the database to back it up — unacceptable for a public service. Postgres
gives RLS and `pg_basebackup`/WAL archiving in the box.
**Outline delta:** CORRECTS §20 Q20's framing of "a property graph" as a single option. The realistic
question is "a property graph *whose access control is behind a commercial license*".

---

### F6.15 — Neo4j's `neo4j/neo4j` GitHub releases feed is stale and must not be used for versioning

**Claim:** The GitHub `releases/latest` endpoint for `neo4j/neo4j` returns `3.2.0-alpha08` (2017-04-11),
which is nine years out of date relative to the 2026.07 branch.
**Status:** VERIFIED
**Evidence:** GitHub API `repos/neo4j/neo4j/releases/latest` → `{"tag_name": "3.2.0-alpha08",
"published_at": "2017-04-11T08:47:47Z"}`, while `repos/neo4j/neo4j` reports `pushed_at 2026-08-07` and the
README/branch shows 2026.07.
**Retrieved:** 2026-08-20
**Implication for the spec:** A methodological note for all SIG ingestion of software-version facts:
**GitHub Releases is not a reliable version oracle** — many projects (Neo4j, Apache Jena, PMTiles, pgvector)
publish no GitHub releases or stale ones. Any SIG connector that harvests "current version" facts must treat the
releases endpoint as one *claim* among several, not as truth. This is a live example of the project's own core thesis:
contradictory sources, resolved by rule, with the rule recorded.
**Outline delta:** EXTENDS §6.5 — a concrete, self-referential instance of contradiction-as-data.

---

### F6.16 — Memgraph Community is BUSL-1.1: source-available, not open source

**Claim:** Memgraph Community Edition is licensed under Business Source License 1.1, which is not an
OSI-approved open-source license; Enterprise features are under a proprietary Memgraph Enterprise License; BSL
converts to Apache 2.0 after the Change Date.
**Status:** VERIFIED
**Evidence:** GitHub API `repos/memgraph/memgraph` → license `NOASSERTION` (GitHub cannot classify BSL),
latest release `v3.12.0` 2026-07-15, pushed 2026-08-20, 4.3k stars. License nature corroborated via
https://github.com/memgraph/memgraph/blob/master/licenses/BSL.txt and https://spdx.org/licenses/BUSL-1.1.html and
https://memgraph.com/legal: MCE under BSL 1.1 (source-available, production use restricted without licensor approval),
MEE under proprietary MEL; BSL converts to Apache 2.0 after the Change Date (typically four years).
**Retrieved:** 2026-08-20
**Implication for the spec:** Excluded by SIG's own §14.3 posture (open code + open data). A project whose
entire value proposition is reusability should not depend on a source-available core with production-use restrictions.
Record the SPDX identifier `BUSL-1.1` in the source/dependency license registry (F6.34) — this is exactly the kind of
license that gets mistaken for open source.
**Outline delta:** EXTENDS §14.3 — the outline discusses *data* licensing; the same discipline must apply to
the *dependency* stack, and SIG should publish a machine-readable dependency license manifest.

---

### F6.17 — TigerGraph Community Edition terms could not be verified

**Claim:** Could not verify TigerGraph Community Edition licensing/limits.
**Status:** INACCESSIBLE
**Evidence:** https://www.tigergraph.com/tigergraph-community-edition/ → HTTP 404.
**Retrieved:** 2026-08-20
**Implication for the spec:** Excluded by default — a closed-core commercial graph database whose free-tier
page 404s is not a substrate for a decade-scale public-interest archive. The burden is on any later proposal to
produce current terms.
**Outline delta:** none.

---

### F6.18 — Property graphs cannot express claim-level provenance without reification bloat

**Claim:** In a labelled property graph (LPG), attaching provenance to an *assertion about a relationship*
requires either (a) putting provenance in relationship properties — which forbids two contradictory assertions of the
same relationship — or (b) reifying every assertion as a node, at which point the graph model provides no advantage
over relational.
**Status:** PARTIALLY VERIFIED (this is a modelling argument grounded in verified facts, not a single citable claim)
**Evidence:** Grounding facts: openCypher/LPG relationships hold a flat property map and there is no
first-class notion of a relationship *about* a relationship (verified indirectly via https://github.com/apache/age
README's Cypher surface and Memgraph/Neo4j docs). Contrast with RDF 1.2 triple terms (F6.25) and Wikibase statements
(F6.22), both of which have explicit statement-level constructs.
**Retrieved:** 2026-08-20
**Implication for the spec:** This kills Option 2 on its merits independent of licensing. SIG's central
requirement (§6.4, §6.5) is *n contradictory assertions of the same subject–predicate*, each with its own source,
method, confidence and time. In an LPG that becomes: `(:Org)-[:CLAIMED_SHARES_WITH]->(:Claim)-[:ABOUT]->(:Org)` plus
`(:Claim)-[:FROM]->(:Evidence)` — i.e. a reified claim node. But a reified claim node in Postgres is just a row, with
better constraints, better temporal support, PostGIS, and RLS. **The graph is the query shape, not the storage
shape.**
**Outline delta:** CORRECTS §20 Q21 — the outline poses "which model best supports claim-level provenance
and bitemporal history" as an open contest. It is not close: LPG is the weakest of the four on both axes.

---

### F6.19 — Bitemporal queries in LPGs are entirely a matter of application discipline

**Claim:** Neither Neo4j, Memgraph, nor Apache AGE provides native `AS OF` / system-versioned time travel;
temporal history in LPGs is modelled by hand (interval properties or state-node chains).
**Status:** PARTIALLY VERIFIED
**Evidence:** Neither https://github.com/neo4j/neo4j, https://github.com/memgraph/memgraph nor
https://github.com/apache/age README/feature listings mention system-time or valid-time query clauses; compare XTDB,
which does (F6.20). Recorded as PARTIALLY VERIFIED because absence-of-feature was inferred from feature listings
rather than from an explicit vendor statement.
**Retrieved:** 2026-08-20
**Implication for the spec:** If a graph engine is used at all, it must be fed from an already-resolved,
already-time-sliced projection ("the graph as of 2026-07-01"), never asked to do temporal reasoning itself. This is a
strong argument for materializing per-snapshot graph projections rather than one live graph.
**Outline delta:** EXTENDS §6.3.

---

### F6.20 — XTDB v2 is genuinely bitemporal with SQL:2011 syntax and MPL-2.0

**Claim:** XTDB v2 exposes `FOR VALID_TIME AS OF`, `FOR SYSTEM_TIME AS OF`, `FOR VALID_TIME ALL`,
`FOR SYSTEM_TIME ALL`, four automatic temporal columns (`_valid_from`, `_valid_to`, `_system_from`, `_system_to`),
backdating via `_valid_from` on INSERT, MPL-2.0 license, Postgres wire compatibility.
**Status:** VERIFIED
**Evidence:** https://docs.xtdb.com/quickstart/sql-overview — the four hidden temporal columns and the
`FOR VALID_TIME`/`FOR SYSTEM_TIME` clauses, including chaining `FOR VALID_TIME ALL FOR SYSTEM_TIME ALL`, and `INSERT
INTO people (_id, name, favorite_color, _valid_from) VALUES (2, 'carol', 'blue', DATE '2023-01-01');`
https://docs.xtdb.com/ — "SQL:2011"-based bitemporality, "retains all history by default", MPL license.
**Retrieved:** 2026-08-20
**Implication for the spec:** XTDB's *semantics* are the target SIG should hit. Even though XTDB is not the
recommended engine, **SIG's SQL views should mimic its clause vocabulary** — a helper function or view naming
convention using `valid_time`/`system_time` and `AS OF`/`ALL` makes the model instantly legible to anyone who knows
SQL:2011, and keeps a future migration to XTDB open.
**Outline delta:** EXTENDS §6.3 — gives the outline's informal `valid_from/valid_to/observed_at` sketch a
standards-anchored vocabulary.

---

### F6.21 — XTDB's release cadence and ecosystem are thin relative to Postgres

**Claim:** `xtdb/xtdb` is MPL-2.0 with 3.0k stars; the newest GitHub release is `v2.1.0` published
2025-12-01; the repo is actively developed (pushed 2026-08-20). It is a single-vendor product (JUXT).
**Status:** VERIFIED
**Evidence:** GitHub API `repos/xtdb/xtdb` → license `MPL-2.0`, stars 3044, `pushed_at 2026-08-20T14:49:56Z`;
`releases/latest` → `v2.1.0`, `published_at 2025-12-01T17:32:59Z`. Description: "An immutable SQL database for
application development, time-travel reporting and data compliance. Developed by @juxt."
**Caveat recorded:** an initial WebFetch summary of the releases page returned internally inconsistent dates
(claiming v2.0.0 GA in June 2024 *after* v2.1.0 in Dec 2023); the GitHub API values above are the ones used. This is
logged because it is exactly the failure mode SIG's own extraction pipeline must guard against — LLM-summarized pages
can invert chronology.
**Retrieved:** 2026-08-20
**Implication for the spec:** Reject as canonical, for four reasons: (1) 3.0k stars vs Postgres's ecosystem
means a near-zero pool of volunteers who already know it; (2) no PostGIS equivalent — SIG is a geospatial project and
XTDB has no serious spatial story; (3) single-vendor governance concentrates project risk; (4) ~8 months between the
last tagged release and today. **But**: XTDB is the right *fallback* if the hand-rolled bitemporal layer proves
unmaintainable, and its Postgres wire compatibility makes that migration less than catastrophic. Record it as the
designated Plan B.
**Outline delta:** EXTENDS §20 Q21.

---

### F6.22 — Wikibase's statement model is the closest existing production analogue to SIG's Claim

**Claim:** Wikibase models facts as Statements = subject + main Snak + qualifier Snaks + References + Rank,
where Snaks come in three kinds (`PropertyValueSnak`, `PropertySomeValueSnak` = "has a value but unknown",
`PropertyNoValueSnak` = "has no value"), and Ranks are preferred / normal / deprecated.
**Status:** VERIFIED
**Evidence:** https://www.mediawiki.org/wiki/Wikibase/DataModel — Items (Q-ids), Properties (P-ids, typed);
Statements contain subject, main Snak, optional qualifier Snaks, References, and a rank; three Snak types with the
examples "Berlin has population 3,499,879", "A circle has no angles" (NoValue), "Ambrose Bierce died on an unknown
date" (SomeValue); Ranks: Preferred ("most current, reliable information used by default"), Normal ("credible but
potentially extensive data (historic records)"), Deprecated ("unreliable or erroneous claims, documented for
transparency") — "allows recording problematic sources while preventing their misuse in applications."
**Retrieved:** 2026-08-20
**Implication for the spec:** Adopt four Wikibase ideas wholesale, without adopting Wikibase:
1. **Rank, not deletion.** SIG's `resolution` decision is a rank assignment; a debunked claim gets `rank = deprecated`
   and stays visible. This directly implements §6.5 and §19.1.
2. **Three-valued snaks.** SIG needs the same distinction: "retention = 30 days", "retention = unknown" (`somevalue`),
   "retention policy does not exist" (`novalue`). The outline's §9.4 "negative claims need special treatment" is
   *exactly* the novalue/somevalue distinction and Wikibase already solved it. **Encode it as a `value_kind` enum on
   the claim, not as a NULL.** NULL cannot distinguish the two.
3. **Qualifiers.** SIG's claims need qualifiers (`point_in_time`, `determination_method`, `stated_scope = statewide`)
   that modify the value without being separate claims.
4. **References as a set.** One claim, N supporting evidence artifacts.
**Outline delta:** EXTENDS §8.16 substantially. The outline's `Claim` has `subject/predicate/value/valid_time/
observed_time/source/extraction_method/confidence/review_status` — it is missing **qualifiers**, missing
**rank**, and it has a single `source` where a set of references is needed. Also §9.4's negative-claim
problem is unsolved in §8.16's field list; `value_kind` solves it.

---

### F6.23 — Nanopublications are a working, deployed claim-level provenance standard

**Claim:** A nanopublication is a small RDF knowledge-graph snippet split into three named graphs —
assertion, provenance, publication info — published as an independent, citable, immutable unit to a decentralized
server network.
**Status:** VERIFIED
**Evidence:** https://nanopub.net/ — "a small knowledge graph snippet with metadata that is treated as an
independent (scientific) publication"; three components: Assertion ("compact, atomic unit of information"), Provenance
("how the assertion was derived"), Publication Info ("creation date, creator attribution, and licensing terms");
RDF-based; "published to decentralized server networks, enabling querying, access, reuse, and linking."
Tooling/commercial steward: https://knowledgepixels.com/ — "small snippets of a knowledge graph that can represent any
topic whatsoever, such as scientific findings, study designs, opinions, and social links"; products include Nanodash.
Network size statistics were **not** obtainable from either page.
**Retrieved:** 2026-08-20
**Implication for the spec:** Adopt the **shape**, not the network. SIG's claim export format should be
three named graphs per claim — `assertion` (the s/p/o + valid time), `provenance` (PROV-O: which activity generated
it, from which evidence, by which agent), `pubinfo` (SIG claim id, ingest run id, license, created at) — because that
is a directly reusable, standards-anchored serialization and it makes each SIG claim independently citable. Publishing
to the actual nanopub network is a **stage-4+ optional** step; the immediate win is the serialization discipline. Note
honestly: network liveness/scale could not be verified, so do not make SIG depend on it.
**Outline delta:** EXTENDS §6.4 and §15.7 — the outline never mentions nanopublications; this is the closest
existing prior art to what §6.4 demands and it supplies a ready-made export format.

---

### F6.24 — PROV-O is a stable 2013 W3C Recommendation with the exact vocabulary SIG needs

**Claim:** PROV-O (W3C Recommendation, 2013-04-30, namespace `http://www.w3.org/ns/prov#`) defines Entity,
Activity, Agent plus `wasGeneratedBy`, `used`, `wasDerivedFrom`, `wasAttributedTo`, `wasAssociatedWith`,
`wasRevisionOf`, and a "qualified" pattern (`prov:Derivation`, `prov:Attribution`, `prov:qualifiedDerivation`,
`prov:qualifiedAttribution`) for attaching extra properties to an influence relation.
**Status:** VERIFIED
**Evidence:** https://www.w3.org/TR/prov-o/ — status "W3C Recommendation issued April 30, 2013"; namespace
`http://www.w3.org/ns/prov#`; Entity = "a physical, digital, conceptual, or other kind of thing with some fixed
aspects"; Activity = "something that occurs over a period of time and acts upon or with entities"; Agent = "something
that bears some form of responsibility"; qualified pattern "allow[s] attachment of supplementary properties describing
the relationship without altering the unqualified assertion."
**Retrieved:** 2026-08-20
**Implication for the spec:** PROV-O is the interoperability target for SIG's provenance export. Mapping in
D6.6. The **qualified pattern is the key affordance**: SIG needs to say not merely "this claim was derived from that
PDF" but "…via extraction method X, by parser version Y, with confidence Z" — that is exactly
`prov:qualifiedDerivation` with a `prov:Derivation` node carrying SIG-specific properties. Being a 2013 Recommendation
is a feature: it will not move under us.
**Outline delta:** EXTENDS §6.4, §8.15, §8.16 — the outline specifies provenance semantically but names no
standard. Without one, SIG's provenance is not interoperable and §14.3's "meaningfully reusable" fails.

---

### F6.25 — PROV-DM gives SIG the time vocabulary and "provenance of provenance" via Bundles

**Claim:** PROV-DM defines generation time, usage time and invalidation time as optional timestamps on
provenance relations, and a Bundle as "a named set of provenance descriptions, and is itself an entity", enabling
provenance-of-provenance. Derivation subtypes include Revision, Quotation and Primary Source.
**Status:** VERIFIED
**Evidence:** https://www.w3.org/TR/prov-dm/ — generation/usage/invalidation times ("optional but enable
precise causal sequencing"); Bundle definition as quoted; Revision = result "contains substantial content from the
original"; Quotation = "the repeat of (some or all of) an entity… by someone who may or may not be its original
author"; Primary Source = derived material traced to "something produced by some agent with direct experience and
knowledge"; Attribution "ascribes entities to agents without requiring explicit activity details."
**Retrieved:** 2026-08-20
**Implication for the spec:** Three direct mappings:
- SIG's Tier A/B/C/… hierarchy (§9.1) maps onto `prov:PrimarySource` vs `prov:Quotation`: Tier A/B evidence is a
  primary source; Tier D investigative reporting *quotes* a primary source. **This makes the outline's tier hierarchy
  machine-readable rather than editorial.**
- `prov:wasRevisionOf` is exactly the link from a corrected claim to the claim it corrects (§B.5).
- `prov:Bundle` is how SIG publishes the resolution decision's own provenance — the resolver's output is a bundle
  whose provenance names the resolver version and ruleset version.
**Outline delta:** EXTENDS §9.1 — converts an informal tier list into PROV-typed relations.

---

### F6.26 — RDF 1.2 triple terms are a Candidate Recommendation (April 2026), not yet a Recommendation

**Claim:** RDF 1.2 Concepts was a Candidate Recommendation Snapshot dated 2026-04-07, not expected to advance
to Recommendation before 2026-05-05; it introduces *triple terms* (a triple used as a term in the object position of
another triple) and *reifiers* linked via `rdf:reifies`.
**Status:** VERIFIED
**Evidence:** https://www.w3.org/TR/rdf12-concepts/ — "Candidate Recommendation Snapshot", 7 April 2026;
"This Candidate Recommendation is not expected to advance to Recommendation any earlier than 05 May 2026"; triple term
= "an RDF triple used as an RDF term within another triple"; reifier = resource linked to a triple term via
`rdf:reifies`, which "may denote a variety of things that are related to the triple term's proposition, such as a
statement or belief that the proposition holds"; "Compared to RDF 1.1, RDF 1.2 introduces the ability to use an RDF
triple as a triple term, in the object position of another triple."
**Retrieved:** 2026-08-20
**Implication for the spec:** RDF-star is *nearly* standard but the SPARQL side lags (F6.27) and
implementations differ. **Do not make triple terms the canonical representation.** Use named graphs + PROV-O for SIG's
RDF export — named graphs have been stable since RDF 1.1 (2014) and are supported by every triplestore. Optionally
emit a triple-term variant as a second export once RDF 1.2 is a Recommendation. Design note that matters: RDF 1.2's
reifier semantics deliberately allow annotating a triple term *without asserting it* — that is precisely SIG's "claim
B says 25 cameras, and we do not believe it" case, so the model is a good long-term fit even if adoption is early.
**Outline delta:** EXTENDS §6.4 — establishes that the standards world is converging on statement-level
annotation, but has not converged yet.

---

### F6.27 — SPARQL 1.2 Query is still only a Working Draft (June 2026)

**Claim:** SPARQL 1.2 Query Language was a W3C Working Draft dated 2026-06-25, adding triple-term support,
a `VERSION` declaration, and triple-term accessor functions.
**Status:** VERIFIED
**Evidence:** https://www.w3.org/TR/sparql12-query/ — "W3C Working Draft", 25 June 2026, from the RDF Star
Working Group; adds triple terms in subject/object positions; `VERSION` directive where "authors _MAY_ announce the
use of the new syntax forms"; version labels including "1.2-basic"; `TRIPLE`, `SUBJECT`, `PREDICATE`, `OBJECT`
functions; backward compatible with SPARQL 1.1 (W3C Rec, March 2013).
**Retrieved:** 2026-08-20
**Implication for the spec:** Confirms F6.26's conclusion. SIG's SPARQL-facing surface (if any) must be
SPARQL 1.1 + named graphs. Anything relying on SPARQL-star is a research artifact, not a product surface.
**Outline delta:** EXTENDS §20 Q20.

---

### F6.28 — Triplestore landscape: Oxigraph viable but slow, Blazegraph dead, QLever fast, GraphDB free-tier opaque, Virtuoso GPL-2.0

**Claim:** As of Aug 2026: Oxigraph 0.5.9 (Apache-2.0/MIT dual, 2026-06-18) self-describes as unoptimized;
`blazegraph/database` is **archived**, last release 2020-02-03, GPL-2.0; QLever v0.6.0 (Apache-2.0, 2026-08-13) is
actively developed and claims trillion-triple scale; GraphDB 11.x offers only Free and Enterprise editions (Standard
discontinued) with unstated free-tier terms; Virtuoso Open Source is GPL-2.0.
**Status:** VERIFIED (Oxigraph, Blazegraph, QLever, Virtuoso) / PARTIALLY VERIFIED (GraphDB terms)
**Evidence:**
- https://github.com/oxigraph/oxigraph — Apache-2.0/MIT, SPARQL 1.1 "nearly fully conformant", "preliminary support
  for 1.2 RDF and SPARQL drafts", RocksDB-backed, and explicitly: "Oxigraph is in heavy development and SPARQL query
  evaluation has not been optimized yet." GitHub API: `v0.5.9` 2026-06-18, 1.8k stars.
- GitHub API `repos/blazegraph/database` → `archived: true`, `pushed_at 2023-04-16`, last release
  `BLAZEGRAPH_2_1_6_RC` 2020-02-03, GPL-2.0. (Wikidata's historical backend — now a dead end.)
- GitHub API `repos/ad-freiburg/qlever` → Apache-2.0, `v0.6.0` 2026-08-13, pushed 2026-08-20, 884 stars, "scales to
  more than a trillion triples". `repos/apache/jena` → Apache-2.0, 1.4k stars, pushed 2026-08-20, **no GitHub
  releases** (Apache dist channels — another instance of F6.15's caveat).
- https://graphdb.ontotext.com/documentation/11.0/ — only "GraphDB Free" and "GraphDB Enterprise (EE)"; "GraphDB
  Standard Edition (SE) is no longer offered but still receives legacy support"; free-tier terms not stated. RDF-star
  support corroborated via https://graphdb.ontotext.com/documentation/11.4/rdf-sparql-star.html: embedded triples are
  a new RDF term type, serialized in non-star formats as `urn:rdf4j:triple:xxx`, and "GraphDB will not explicitly
  assert the referenced statement by an embedded triple" — annotation without assertion, as RDF 1.2 intends.
- https://github.com/openlink/virtuoso-opensource — "GNU General Public License Version 2, dated June 1991";
  commercial edition is a separate product; version not stated in README.
**Retrieved:** 2026-08-20
**Implication for the spec:** If SIG publishes RDF, publish **files** (N-Quads/TriG dumps, gzipped, on static
hosting, with a Zenodo DOI) and let consumers load them into whatever store they like. Optionally run Oxigraph for a
low-traffic public SPARQL endpoint, accepting its performance caveat, because it is the only option here that is
permissively licensed, single-binary, and alive. QLever is the choice if the endpoint ever needs to be fast. **Do not
build on Blazegraph** (archived) or GraphDB Free (unstated terms).
**Outline delta:** CORRECTS §20 Q20's implicit assumption that "RDF" is one option — the triplestore field
has one dead major player, one commercially gated player, and two viable open ones with opposite tradeoffs.

---

### F6.29 — RDF as canonical fails on geospatial and write throughput, not on provenance

**Claim:** RDF/SPARQL has adequate statement-level provenance (named graphs, PROV-O, RDF-star) but no
equivalent to PostGIS's spatial indexing/predicates, and triplestores are poorly suited to high-volume aggregate
ingestion.
**Status:** PARTIALLY VERIFIED (composite argument)
**Evidence:** GeoSPARQL exists but none of the surveyed stores advertise it as a headline feature in the
pages fetched (Oxigraph README, QLever description, GraphDB 11.0 docs index); by contrast PostGIS ships `ST_DWithin`,
GiST/SP-GiST spatial indexes, projections via PROJ, and topology/raster (F6.3). Oxigraph's own README states query
evaluation is unoptimized (F6.28).
**Retrieved:** 2026-08-20
**Implication for the spec:** Option 3 is rejected as canonical and adopted as an **export target**. This is
the right split: SIG gains semantic-web interoperability (§14.3, §18) without paying for it in daily operations. Note
the honest caveat: GeoSPARQL support in specific stores was not exhaustively tested, so this finding is PARTIALLY
VERIFIED — a future pass should test GeoSPARQL in Oxigraph/QLever if an RDF-canonical design is ever revisited.
**Outline delta:** EXTENDS §20 Q20.

---

### F6.30 — Wikibase-as-software is the wrong deployment even though Wikibase-as-model is right

**Claim:** Adopting the Wikibase *data model* (F6.22) does not imply deploying Wikibase.
**Status:** UNVERIFIED (design judgement; no vendor claim tested)
**Evidence:** Reasoning from verified facts only: Wikibase's model is realized as a MediaWiki extension with
a MySQL/MariaDB backend and a separate query-service triplestore, historically Blazegraph — which is now archived
(F6.28). Wikidata's migration away from Blazegraph is a known ongoing effort but was not verified in this pass.
**Retrieved:** 2026-08-20
**Implication for the spec:** Take the model, leave the stack. Additionally: SIG should mint and publish
**Wikidata-compatible mappings** (`P` -style predicate crosswalks and `owl:sameAs`/`skos:exactMatch` links to
Wikidata Q-ids for agencies and vendors) so the two graphs can be joined — this is the cheapest possible version of
§18 "interact with existing projects" and it costs one column.
**Outline delta:** EXTENDS §18, §20 Q37 — stable outward-linkable IDs should include Wikidata Q-ids where
they exist.

---

## Part 2 — The decision scorecard

Scores are 1 (poor) to 5 (excellent) for SIG's specific requirements, not in general. Weight reflects how much the
criterion matters to *this* project given §6.3–§6.5, §13, §14 and a small volunteer team.

| Criterion | Weight | 1. PG+PostGIS | 2. LPG (Neo4j/Memgraph) | 3. RDF/triplestore | 4. **Hybrid (PG canonical + projections)** | 5. XTDB/immutable log |
|---|---|---|---|---|---|---|
| Claim-level provenance ergonomics | 5 | 4 | 2 | 5 | **5** | 3 |
| Bitemporal query ergonomics | 5 | 3 | 1 | 2 | **4** | 5 |
| Geospatial support | 5 | 5 | 2 | 2 | **5** | 1 |
| Contradiction representation | 5 | 4 | 2 | 4 | **5** | 3 |
| Write throughput, high-volume aggregates | 3 | 3 | 2 | 1 | **5** | 3 |
| Operational simplicity, small volunteer team | 5 | 5 | 3 | 3 | **4** | 2 |
| Open-source licensing purity | 4 | 5 | 1 | 4 | **5** | 4 |
| Export / reproducibility | 4 | 4 | 2 | 5 | **5** | 4 |
| Ecosystem / hireable-volunteer tooling | 4 | 5 | 4 | 2 | **5** | 1 |
| Ability to run cheaply (<$50/mo) | 4 | 5 | 2 | 3 | **5** | 2 |
| **Weighted total (max 220)** | | **190** | **93** | **142** | **214** | **125** |

Score notes: **Provenance, PG = 4 not 5** — a claim row with an evidence join table is expressive, but nothing in the
engine *enforces* provenance the way RDF named graphs do; the hybrid scores 5 because the PROV-O export round-trip
continuously audits that every claim carries provenance. **Bitemporal, PG = 3** — PG18 gives constraints but not `AS
OF` syntax; hybrid = 4 because the view layer (D6.5) closes most of the gap. **Contradiction, LPG = 2** — see F6.18;
**RDF = 4** not 5 because SPARQL-star is still a WD (F6.27).
**Licensing, LPG = 1** — GPLv3 with Enterprise-gated RBAC (F6.14) or BUSL-1.1 (F6.16). **Cheap, XTDB = 2** —
JVM, object-store-plus-compute; not a $5 VPS proposition. **Ecosystem, XTDB = 1 / RDF = 2** — the pool of volunteers
who can debug a Postgres query at 2am versus a SPARQL optimizer is not comparable, and for a project premised on
community contribution that is a first-order concern.

### Decision

**Option 4 (Hybrid) wins, with Option 1 as its core.** The recommendation is not "Postgres because it is
familiar" — it is that SIG's requirements decompose cleanly into a *transactional, constrained, geospatial,
access-controlled* problem (where Postgres is strictly best) and an *interoperability + analytics* problem (where
files, not servers, are the right answer). Every non-Postgres component in the stack is a derived artifact that can be
deleted and rebuilt, which is exactly the property a volunteer project needs.

**Failure modes accepted:** (a) bitemporal query ergonomics are hand-rolled — mitigated by the view layer
in D6.5 and by mimicking SQL:2011 vocabulary; (b) very deep graph traversals (6+ hops over millions of edges) will be
slower than a native LPG — accepted, because SIG's sharing-network questions are typically 1–3 hops and the projection
layer can absorb the rest.

---

## Part 3 (Section B) — Bitemporality, done precisely

### D6.1 — The five times, disentangled

The outline (§6.3, §8.15, §8.16, §9.2) uses `valid_from`, `valid_to`, `observed_at`, `retrieved_at`, `date` without
ever defining their relationship. Here are the five distinct times, with the entity each belongs to:

| # | Name | Definition | Belongs to | Cardinality | Controlled by |
|---|---|---|---|---|---|
| T1 | **Valid time** | The interval during which the asserted fact was true *in the world* | Claim | interval, may be open or fuzzy | the asserting source / SIG's interpretation |
| T2 | **Transaction time** (system time) | The interval during which SIG's database held this row as its record | Claim row | interval, `[recorded_at, ∞)` until superseded | the database, never the user |
| T3 | **Observation time** | The instant at which the *source* observed or determined the state it reports | Claim | instant | the source |
| T4 | **Publication time** | The instant the source made its statement public | **EvidenceArtifact** | instant | the publisher |
| T5 | **Retrieval time** | The instant SIG fetched the bytes | **EvidenceArtifact** | instant | SIG's crawler |

**The minimal sufficient set for the claim is {T1, T2, T3}. T4 and T5 belong to evidence and must not be
duplicated onto the claim.** Why each is irreducible:

- **T1 vs T3 is the outline's §9.2 point and it is correct.** "The portal on 2026-08-20 said 25 cameras" is T3 =
  2026-08-20 with T1 unknown-but-including-2026-08-20-at-best. Collapsing them turns an observation into a fact.
- **T2 vs T3 is the distinction the outline *misses*.** T3 is when the world was looked at; T2 is when SIG wrote it
  down. These diverge constantly: a FOIA response received in November 2026 may report a March 2025 configuration.
  Without T2 you cannot answer "what did our published dataset say last month", which means you cannot reproduce a
  citation of your own data. **This is the single most important correction in this file.**
- **T4 vs T3 diverge for reports.** A news article published 2026-05-01 (T4) describing what a councilmember said on
  2026-03-12 (T3). Both matter; they belong to different objects.
- **T5 vs T4 diverge for archives.** A portal page published continuously, fetched by SIG at a moment (T5). T5 is the
  only one that establishes what SIG can prove it saw.

**Is this bitemporal or tritemporal?** Both, and the distinction is worth being pedantic about:
- SIG is **bitemporal in the `AS OF` sense**: exactly two dimensions are *intervals over which rows are superseded*,
  so exactly two dimensions support time-travel queries (T1, T2). This is the SQL:2011 / XTDB model (F6.20) and the
  Snodgrass/Fowler model (F6.12, F6.31).
- SIG is **tritemporal in the record sense**: T3 is a genuine third temporal axis but it is an *instant attribute*,
  not a supersession interval. You never ask "as of observation time X"; you ask "ordered by observation time"
  (resolution) and "filtered by observation time" (staleness detection, §12 "stale evidence" tasks).
- Practical rule: **two interval dimensions, one ordering scalar.** Any design that tries to make T3 a third `AS OF`
  axis produces an 8-way region algebra nobody on a volunteer team will implement correctly.

### D6.2 — Canonical DDL: entities, claims, evidence

```sql
-- ============================================================
-- Enumerations (see D6.14 for why these are tables, not enums)
-- ============================================================

CREATE TABLE vocab_predicate (
  predicate_id     text PRIMARY KEY,              -- e.g. 'active_camera_count'
  vocab_version    text NOT NULL,                 -- e.g. '2026.1'
  value_datatype   text NOT NULL,                 -- 'integer'|'string'|'boolean'|'duration'|'entity_ref'|'geometry'|'edtf'
  cardinality      text NOT NULL DEFAULT 'single',-- 'single'|'multi'
  definition       text NOT NULL,
  skos_concept_iri text,                          -- published SKOS concept
  deprecated_at    timestamptz,
  superseded_by    text REFERENCES vocab_predicate(predicate_id)
);

CREATE TYPE value_kind    AS ENUM ('value', 'somevalue', 'novalue');  -- Wikibase snak kinds, F6.22
CREATE TYPE claim_rank    AS ENUM ('preferred', 'normal', 'deprecated');
CREATE TYPE review_status AS ENUM ('unreviewed', 'accepted', 'disputed', 'rejected', 'superseded');

-- ============================================================
-- Entities: identity only. NO attributes live here.
-- Every attribute of every entity is a claim.
-- ============================================================

CREATE TABLE entity (
  entity_id     uuid PRIMARY KEY DEFAULT uuidv7(),   -- PG18, F6.2
  entity_type   text NOT NULL,   -- Organization|Vendor|Product|Technology|Deployment|
                                 -- PhysicalAsset|DataSystem|Contract|Policy|
                                 -- ConfigurationState|Incident|EvidenceArtifact
  created_at    timestamptz NOT NULL DEFAULT clock_timestamp(),
  -- Identity merges are themselves claims; this column is a cached resolver output.
  merged_into   uuid REFERENCES entity(entity_id),
  CHECK (merged_into IS NULL OR merged_into <> entity_id)
);
```

The rule "entities hold identity, claims hold everything else" is what makes §6.4 work. If
`organization.canonical_name` were a column, it would have one value with one provenance — which is the exact failure
the outline diagnoses. The canonical name is a claim like any other, and the resolver picks the preferred one.

```sql
-- ============================================================
-- Evidence: the artifact, its bytes, its licence, its times
-- ============================================================

CREATE TABLE evidence_artifact (
  evidence_id       uuid PRIMARY KEY DEFAULT uuidv7(),
  -- Content addressing (see Part 5 / Q25)
  content_digest    text NOT NULL,        -- multihash, base32, e.g. 'bciqd...'  (F6.38)
  digest_algorithm  text NOT NULL DEFAULT 'sha2-256',
  byte_length       bigint NOT NULL,
  media_type        text NOT NULL,
  ocfl_object_id    text NOT NULL,        -- OCFL object holding the bytes (F6.37)
  ocfl_version      text NOT NULL,        -- 'v3'
  -- Where it came from
  source_uri        text,                 -- original URL, may be dead
  archived_uri      text,                 -- wayback / WACZ / internal
  publisher_entity  uuid REFERENCES entity(entity_id),
  source_id         text NOT NULL REFERENCES source_registry(source_id),
  -- The evidence's own two times (T4, T5)
  published_at      text,                 -- EDTF string, often imprecise (F6.33)
  retrieved_at      timestamptz NOT NULL, -- T5: exact, always known
  -- Governance (§14.2)
  license_spdx      text,                 -- SPDX expression, F6.34, e.g. 'ODbL-1.0' or 'LicenseRef-SIG-Flock-TOS'
  redistributable   boolean NOT NULL DEFAULT false,
  sensitivity_tier  smallint NOT NULL DEFAULT 0,  -- 0 public .. 3 restricted (§13.4)
  ingest_run_id     uuid NOT NULL REFERENCES ingest_run(run_id),
  UNIQUE (content_digest, source_uri)
);

CREATE INDEX ON evidence_artifact (source_id, retrieved_at DESC);
CREATE INDEX ON evidence_artifact (content_digest);
```

Note `retrieved_at` is `timestamptz` (always exactly known) while `published_at` is EDTF text (frequently "2024" or
"2024-03~"). Forcing a real timestamp on a publication date you do not actually know is precisely the "false
precision" §19.4 forbids.

```sql
-- ============================================================
-- THE CLAIM TABLE. Append-only. Never UPDATEd except sys_period close.
-- ============================================================

CREATE TABLE claim (
  claim_id        uuid PRIMARY KEY DEFAULT uuidv7(),

  -- Subject / predicate / object
  subject_id      uuid NOT NULL REFERENCES entity(entity_id),
  predicate_id    text NOT NULL REFERENCES vocab_predicate(predicate_id),
  object_entity   uuid REFERENCES entity(entity_id),   -- for entity-valued predicates
  value_kind      value_kind NOT NULL DEFAULT 'value',
  value_text      text,           -- canonical string form, always populated for 'value'
  value_num       numeric,        -- populated when datatype is numeric (indexable)
  value_bool      boolean,
  value_geom      geometry(Geometry, 4326),   -- SRID 4326 storage, D6.12
  value_json      jsonb,          -- structured values (e.g. quantity + unit + bounds)

  -- T1: valid time. Two representations, deliberately.
  valid_period    tstzrange NOT NULL DEFAULT tstzrange(NULL, NULL, '[)'),  -- machine-usable envelope
  valid_edtf      text,          -- source-faithful fuzzy expression, e.g. '2024-03~/..'  (F6.33)
  valid_from_kind text NOT NULL DEFAULT 'known',  -- 'known'|'unknown'|'before'|'after'|'approximate'
  valid_to_kind   text NOT NULL DEFAULT 'known',  -- 'known'|'unknown'|'ongoing'|'before'|'after'

  -- T3: observation time (instant; the source's own act of observing)
  observed_at     timestamptz NOT NULL,
  observed_edtf   text,           -- when the source's observation instant is itself fuzzy

  -- T2: transaction time. DB-controlled. Half-open, ends at 'infinity' while current.
  sys_period      tstzrange NOT NULL DEFAULT tstzrange(clock_timestamp(), NULL, '[)'),

  -- Epistemics
  confidence      text NOT NULL,        -- 'confirmed'|'strongly_supported'|'probable'|'unverified'|'contradicted'  (§9.3)
  source_tier     char(1) NOT NULL,     -- 'A'..'F'  (§9.1)
  extraction_method text NOT NULL,      -- 'manual'|'deterministic_parse'|'regex'|'llm_extract'|'osm_import'|...
  extractor_version text NOT NULL,      -- pinned parser/model version, for reproducibility
  rank            claim_rank NOT NULL DEFAULT 'normal',
  review_status   review_status NOT NULL DEFAULT 'unreviewed',

  -- Lineage
  ingest_run_id   uuid NOT NULL REFERENCES ingest_run(run_id),
  revises_claim   uuid REFERENCES claim(claim_id),   -- prov:wasRevisionOf, F6.25
  retraction_of   uuid REFERENCES claim(claim_id),   -- explicit retraction; never a DELETE

  CONSTRAINT claim_value_shape CHECK (
    (value_kind = 'value' AND (value_text IS NOT NULL OR object_entity IS NOT NULL
                               OR value_geom IS NOT NULL OR value_json IS NOT NULL))
    OR (value_kind IN ('somevalue','novalue')
        AND value_text IS NULL AND object_entity IS NULL
        AND value_num IS NULL AND value_bool IS NULL AND value_geom IS NULL)
  ),
  CONSTRAINT claim_observed_not_future CHECK (observed_at <= clock_timestamp() + interval '1 day')
) PARTITION BY RANGE (observed_at);

-- Yearly partitions; observed_at (not sys time) because queries filter on it and
-- historical backfills of old observations should land in old partitions.
CREATE TABLE claim_2026 PARTITION OF claim
  FOR VALUES FROM ('2026-01-01Z') TO ('2027-01-01Z');
-- ... plus claim_pre2020, claim_2020..2025, claim_default

CREATE INDEX ON claim (subject_id, predicate_id, observed_at DESC);
CREATE INDEX ON claim USING gist (valid_period);
CREATE INDEX ON claim USING gist (value_geom) WHERE value_geom IS NOT NULL;
CREATE INDEX ON claim (predicate_id, object_entity) WHERE object_entity IS NOT NULL; -- reverse edges
CREATE INDEX ON claim (ingest_run_id);
```

Deliberate design choices worth defending:

1. **`sys_period` is a range, not a single `recorded_at`.** A claim row is "closed out" (its `sys_period` upper bound
   set) only when SIG *corrects its own record* — e.g. discovering the extractor misread the PDF. It is **not** closed
   when the world changes; a world change is a new claim with a different valid time and both rows stay current in
   transaction time. Conflating these two is the classic bitemporal bug.
2. **`valid_period` and `valid_edtf` coexist.** The range is what indexes and queries use; the EDTF string is what the
   source actually supported. When they disagree (fuzzy source), `valid_*_kind` records why. Losing the EDTF form
   would violate §19.2 "raw before normalized".
3. **Both `value_text` and typed columns.** `value_text` is the always-present canonical form for
   diffing/hashing/export; typed columns exist so `value_num > 20` can use an index.
4. **`extractor_version` is `NOT NULL`.** Reproducibility (§14.3) is impossible if you cannot say which parser
   produced a value. Making it nullable would guarantee it goes unfilled.

```sql
-- Claim ↔ evidence is many-to-many (Wikibase "references", F6.22)
CREATE TABLE claim_evidence (
  claim_id     uuid NOT NULL REFERENCES claim(claim_id),
  evidence_id  uuid NOT NULL REFERENCES evidence_artifact(evidence_id),
  role         text NOT NULL DEFAULT 'supports',   -- 'supports'|'contradicts'|'context'
  locator      jsonb,   -- page number, CSS selector, CSV row, PDF bbox, WARC record id
  PRIMARY KEY (claim_id, evidence_id, role)
);

-- Qualifiers (Wikibase, F6.22): modify a claim's meaning without being separate claims
CREATE TABLE claim_qualifier (
  claim_id      uuid NOT NULL REFERENCES claim(claim_id),
  qualifier_id  text NOT NULL REFERENCES vocab_predicate(predicate_id),
  value_text    text,
  value_num     numeric,
  value_entity  uuid REFERENCES entity(entity_id),
  PRIMARY KEY (claim_id, qualifier_id, value_text)
);
```

`claim_evidence.role = 'contradicts'` is worth highlighting: it lets SIG record "this document is evidence
*against* claim X" without inventing a negative claim. That is a distinct epistemic act from asserting the
opposite and §9.4 needs it.

### D6.3 — The resolution table (contradiction resolved, never collapsed)

```sql
CREATE TABLE resolution (
  resolution_id    uuid PRIMARY KEY DEFAULT uuidv7(),
  subject_id       uuid NOT NULL REFERENCES entity(entity_id),
  predicate_id     text NOT NULL REFERENCES vocab_predicate(predicate_id),

  -- The resolved value, in the same shape as a claim
  value_kind       value_kind NOT NULL,
  value_text       text,
  value_num        numeric,
  value_geom       geometry(Geometry, 4326),
  object_entity    uuid REFERENCES entity(entity_id),

  valid_period     tstzrange NOT NULL,
  sys_period       tstzrange NOT NULL DEFAULT tstzrange(clock_timestamp(), NULL, '[)'),

  -- WHY. This is the part that makes it a decision record, not a view.
  winning_claim    uuid REFERENCES claim(claim_id),
  considered_claims uuid[] NOT NULL,
  contradiction_state text NOT NULL,  -- 'uncontested'|'resolved_conflict'|'unresolved_conflict'|'insufficient'
  rationale_code   text NOT NULL,     -- machine-readable, from vocab_rationale
  rationale_text   text NOT NULL,     -- human sentence, e.g. 'portal is the most recent Tier-B operational source'
  confidence       text NOT NULL,
  resolver_version text NOT NULL,     -- code version
  ruleset_version  text NOT NULL,     -- policy version, separately versioned from code
  decided_by       text NOT NULL,     -- 'auto' | agent/user id  (human overrides are first-class)
  decided_at       timestamptz NOT NULL DEFAULT clock_timestamp(),

  -- PG18: at most one resolved value per subject/predicate at any instant of valid time (F6.2)
  CONSTRAINT resolution_no_overlap
    EXCLUDE USING gist (subject_id WITH =, predicate_id WITH =, valid_period WITH &&)
    WHERE (upper_inf(sys_period))
);
```

Two things this buys that a materialized view cannot:

- **`contradiction_state = 'unresolved_conflict'` is a legitimate, publishable answer.** The outline's §6.5 example
  resolves to 20; but if the portal and the contract disagree and neither is clearly better, SIG publishes *the
  disagreement* with all four claim values attached. This directly generates a §12 research task. **The API must be
  able to return "we do not know, and here is the shape of the not-knowing."**
- **`ruleset_version` separate from `resolver_version`.** When SIG changes its epistemic policy (e.g. "contract
  quantities now outrank portal counts for `contracted_camera_count`"), that is a *policy* change that must be
  attributable and re-runnable independently of code changes. Every resolution row can be regenerated and diffed
  against the stored one; a mismatch means either a bug or a policy drift, and both are worth an alert.

### D6.4 — Correcting a past mistake without destroying the record of having made it

The scenario: on 2026-05-01 SIG's parser misread a contract PDF as "25 cameras"; on 2026-08-20 a human notices it says
225.

```sql
BEGIN;

-- 1. Close the erroneous claim in TRANSACTION time only. Its valid time is untouched:
--    the claim was never true in the world, but it WAS in our database, and that is a fact.
UPDATE claim
   SET sys_period = tstzrange(lower(sys_period), clock_timestamp(), '[)')
 WHERE claim_id = :bad_claim_id
   AND upper_inf(sys_period);

-- 2. Insert the corrected claim, pointing back at what it revises (prov:wasRevisionOf, F6.25).
--    Note observed_at is UNCHANGED: the source observed the world at the original moment.
--    Only OUR reading of the source changed.
INSERT INTO claim (subject_id, predicate_id, value_kind, value_text, value_num,
                   valid_period, observed_at, confidence, source_tier,
                   extraction_method, extractor_version, ingest_run_id, revises_claim,
                   review_status)
SELECT subject_id, predicate_id, 'value', '225', 225,
       valid_period, observed_at, 'confirmed', source_tier,
       'manual', 'human:v1', :run_id, claim_id, 'accepted'
  FROM claim WHERE claim_id = :bad_claim_id;

-- 3. Close the stale resolution row and let the resolver write a new one.
UPDATE resolution
   SET sys_period = tstzrange(lower(sys_period), clock_timestamp(), '[)')
 WHERE subject_id = :subj AND predicate_id = 'contracted_camera_count'
   AND upper_inf(sys_period);

COMMIT;
```

After this, all three questions remain answerable:
- "What is the count?" → 225.
- "What did SIG publish on 2026-06-01?" → 25 (query with `sys_period @> '2026-06-01Z'`).
- "Did SIG ever get this wrong, and how was it fixed?" → the closed claim row, its `sys_period` upper bound, and the
  `revises_claim` edge from the correction.

**The `UPDATE` in step 1 is the only permitted UPDATE on the claim table.** Enforce it:

```sql
CREATE OR REPLACE FUNCTION claim_immutable() RETURNS trigger AS $$
BEGIN
  IF row(NEW.*) IS DISTINCT FROM row(OLD.*) THEN
    IF NEW.claim_id       IS DISTINCT FROM OLD.claim_id
       OR NEW.subject_id  IS DISTINCT FROM OLD.subject_id
       OR NEW.predicate_id IS DISTINCT FROM OLD.predicate_id
       OR NEW.value_text  IS DISTINCT FROM OLD.value_text
       OR NEW.value_num   IS DISTINCT FROM OLD.value_num
       OR NEW.observed_at IS DISTINCT FROM OLD.observed_at
       OR NEW.valid_period IS DISTINCT FROM OLD.valid_period
       OR lower(NEW.sys_period) IS DISTINCT FROM lower(OLD.sys_period) THEN
      RAISE EXCEPTION 'claim rows are immutable; only sys_period upper bound may be set (claim_id=%)', OLD.claim_id;
    END IF;
  END IF;
  RETURN NEW;
END $$ LANGUAGE plpgsql;

CREATE TRIGGER claim_immutable_trg BEFORE UPDATE ON claim
  FOR EACH ROW EXECUTE FUNCTION claim_immutable();

CREATE RULE claim_no_delete AS ON DELETE TO claim DO INSTEAD NOTHING;
```

A takedown (§20 Q32) is therefore never a DELETE. It is a retraction claim plus a `sensitivity_tier` change that RLS
hides — the row remains, so the fact of the takedown is auditable. (Legal erasure obligations, if they ever arise,
require a documented tombstone procedure; flagged as an open question.)

### D6.5 — The four canonical temporal queries

**(a) "What did we believe on date D about the state on date V?"** — the defining bitemporal query.

```sql
CREATE FUNCTION sig_resolution_as_of(p_belief timestamptz, p_valid timestamptz)
RETURNS TABLE (subject_id uuid, predicate_id text, value_text text,
               confidence text, rationale_text text, contradiction_state text)
LANGUAGE sql STABLE AS $$
  SELECT r.subject_id, r.predicate_id, r.value_text,
         r.confidence, r.rationale_text, r.contradiction_state
    FROM resolution r
   WHERE r.sys_period   @> p_belief     -- transaction time: what we held then
     AND r.valid_period @> p_valid;     -- valid time: about the world then
$$;

-- "As we understood things on 1 June 2026, what was true on 1 March 2026?"
SELECT * FROM sig_resolution_as_of('2026-06-01Z', '2026-03-01Z');
```

The two-argument shape is the whole point. `sig_resolution_as_of(now(), now())` is "current truth";
`sig_resolution_as_of(now(), '2025-01-01Z')` is "our best current understanding of the past" — the *correct* default
for historical analysis; and `sig_resolution_as_of('2025-01-01Z', '2025-01-01Z')` is "what we said at the time", which
is what a citation of an old SIG release must reproduce.

**(b) "Show all state transitions of deployment X."**

```sql
SELECT c.observed_at,
       lower(c.valid_period)  AS valid_from,
       upper(c.valid_period)  AS valid_to,
       c.valid_edtf,
       c.value_text           AS lifecycle_status,
       c.source_tier, c.confidence, c.rank,
       e.source_uri, e.retrieved_at
  FROM claim c
  LEFT JOIN claim_evidence ce ON ce.claim_id = c.claim_id AND ce.role = 'supports'
  LEFT JOIN evidence_artifact e ON e.evidence_id = ce.evidence_id
 WHERE c.subject_id  = :deployment_id
   AND c.predicate_id = 'lifecycle_status'      -- §6.7 vocabulary
   AND upper_inf(c.sys_period)                  -- current record only
 ORDER BY lower(c.valid_period) NULLS FIRST, c.observed_at;
```

Note this returns **claims, not resolutions** — for a lifecycle timeline you want every asserted transition including
the contradicted ones, with tier and confidence shown. That is §6.5 operationalized in the UI.

**(c) "What changed between our snapshot on T1 and T2?"** — the release-diff query.

```sql
WITH a AS (SELECT subject_id, predicate_id, value_text
             FROM resolution WHERE sys_period @> :t1 AND valid_period @> :t1),
     b AS (SELECT subject_id, predicate_id, value_text
             FROM resolution WHERE sys_period @> :t2 AND valid_period @> :t2)
SELECT COALESCE(a.subject_id, b.subject_id)     AS subject_id,
       COALESCE(a.predicate_id, b.predicate_id) AS predicate_id,
       a.value_text AS was, b.value_text AS now,
       CASE WHEN a.subject_id IS NULL THEN 'added'
            WHEN b.subject_id IS NULL THEN 'removed'
            ELSE 'changed' END AS change_type
  FROM a FULL OUTER JOIN b USING (subject_id, predicate_id)
 WHERE a.value_text IS DISTINCT FROM b.value_text;
```

This query is the engine behind two product surfaces at once: the public changelog (§15.4 renewal watch) and the "new
sharing node" research task (§12).

**(d) Distinguishing a world-change from a knowledge-change.** Given a value difference between T1 and T2,
which kind is it?

```sql
-- world change: new claim whose valid_period starts after the old one's
-- knowledge change: new claim covering the SAME valid_period, superseding in sys time
SELECT c.claim_id, c.value_text,
       lower(c.valid_period) AS vf, lower(c.sys_period) AS recorded,
       CASE
         WHEN c.revises_claim IS NOT NULL                              THEN 'correction'
         WHEN c.valid_period && (SELECT valid_period FROM claim p WHERE p.claim_id = :prev_claim)
                                                                       THEN 'competing_assertion'
         ELSE 'world_change'
       END AS change_nature
  FROM claim c
 WHERE c.subject_id = :subj AND c.predicate_id = :pred
   AND lower(c.sys_period) BETWEEN :t1 AND :t2;
```

Being able to answer this is what §22.5 means by temporal reconciliation as a differentiator: "Springfield PD's
sharing with ICE ended" and "we learned that Springfield PD's sharing with ICE had already ended" are different news
stories, and no existing project in the outline's ecosystem map can tell them apart.

### D6.5b — Open-ended and unknown time (the EDTF recommendation)

### F6.31 — Snodgrass's canonical properties of transaction time
**Claim:** In the standard temporal-database literature, transaction time is append-only, cannot be changed
after the fact, and is bounded above by "now"; valid time may be arbitrarily set to past or future.
**Status:** UNVERIFIED (source inaccessible)
**Evidence:** Attempted https://www2.cs.arizona.edu/~rts/tdbbook.pdf (Snodgrass, *Developing Time-Oriented
Database Applications in SQL*) — fetch failed with a TLS error: "unable to verify the first certificate". The
properties are corroborated indirectly by XTDB's implementation (F6.20: `_system_from` is database-assigned while
`_valid_from` is user-supplied on INSERT) and by Fowler (F6.32).
**Retrieved:** 2026-08-20
**Implication for the spec:** The design in D6.2 already encodes these properties (`sys_period` lower bound
is `clock_timestamp()` and immutable per the D6.4 trigger; `valid_period` is caller-supplied and may be in the
future). Flagged UNVERIFIED so a later pass can cite the primary text. Fallback: cite ISO/IEC 9075:2011 Part 2 and the
XTDB docs.
**Outline delta:** none.

### F6.32 — Fowler's temporal patterns confirm the two-dimension framing and warn about cost
**Claim:** Fowler distinguishes "actual time" (when it happened) from "record time" (when we learned it),
frames the core query as "what did we think the state was on date X when we recorded it on date Y", and recommends
simplifying where possible (additive-only changes, or current-only modifications).
**Status:** VERIFIED
**Evidence:** https://martinfowler.com/eaaDev/timeNarrative.html — actual vs record time; the payroll example
(rate changed Feb 15, learned Mar 15, payroll run Feb 25 at the old rate); patterns Audit Log, Effectivity, Temporal
Property, Snapshot; "Bi-temporal systems handle both dimensions simultaneously but add complexity"; recommends
workarounds such as storing calculation traces rather than full bitemporality; notes that restricting to additive
changes "dramatically simplifies interfaces and implementation".
**Retrieved:** 2026-08-20
**Implication for the spec:** Fowler's simplification advice is directly applicable and should be adopted:
**SIG's claim table is additive-only**, which is the exact simplification he names. The complexity Fowler
warns about arises when *arbitrary* bitemporal updates are allowed; SIG permits exactly one non-additive operation
(closing `sys_period`), which keeps the implementation tractable for volunteers.
**Outline delta:** CONFIRMS §19.3, and supplies the vocabulary ("actual time"/"record time") the outline lacks.

### F6.33 — EDTF (ISO 8601-2) is the right encoding for fuzzy dates and is implemented

**Claim:** EDTF defines three levels with syntax for uncertain (`?`), approximate (`~`), both (`%`),
unspecified digits (`X`), open/unknown interval endpoints (`..`), and sets (`[]` = one-of, `{}` = all-of), and is
implemented in production libraries.
**Status:** PARTIALLY VERIFIED
**Evidence:** The Library of Congress EDTF pages (https://www.loc.gov/standards/datetime/ and
`.../edtf.html`) both returned **HTTP 403 Forbidden** to automated fetch. Syntax verified instead from an
implementation: https://github.com/ixc/python-edtf — all three levels; Level 1: `1979-08-28~` (approximate), `1984?`
(uncertain), `1979-08-XX`/`1979-XX` (unspecified digits), `1984-06-02?/2004-08-08~` (mixed-qualifier interval),
`Y-12000`, `1979-22` (summer 1979); Level 2: `2004-06~-11` (partial approximation), `1979-XX-28`,
`[..1760-12-03,1762]` (one-of set, open start), `{1667,1668,1670..1672}` (all-of set), `1979-08~/..` (open-ended
interval), `Y-17E7`.
**Retrieved:** 2026-08-20
**Implication for the spec:** Adopt EDTF Level 1 as the required `valid_edtf` / `published_at` encoding, with
Level 2 permitted but not required (Level 2 sets are rarely needed and complicate parsing). Every EDTF value must be
accompanied by a derived `tstzrange` envelope computed by a **pinned, deterministic** EDTF→range function, because the
envelope is what indexes. Store both. **Caveat to record in the spec:** the normative LoC pages are not
machine-fetchable, so SIG should vendor a copy of the EDTF grammar into its own docs rather than depend on a live
403-ing URL.
**Outline delta:** EXTENDS §19.4 "Uncertainty before false precision" — the outline demands uncertainty
handling but proposes no encoding. EDTF is a real standard (ISO 8601-2:2019 incorporates EDTF features) with working
parsers, and it directly answers "sometime before X" (`[..1760-12-03]`), "unknown but ongoing" (`2024-03/..`) and
"approximately 2019" (`2019~`).

**Recommended encoding for the five hard cases the brief names:**

| Case | `valid_edtf` | `valid_period` envelope | `valid_from_kind` / `valid_to_kind` |
|---|---|---|---|
| `valid_from` unknown, ended 2025-06 | `../2025-06-30` | `(,2025-07-01)` | `unknown` / `known` |
| Ongoing, started 2024-03 | `2024-03/..` | `[2024-03-01,)` | `known` / `ongoing` |
| "Sometime before 2023-01-01" | `[..2022-12-31]` | `(,2023-01-01)` | `before` / `unknown` |
| "Around 2019" | `2019~` | `[2018-01-01,2021-01-01)` | `approximate` / `approximate` |
| Fully unknown but asserted true now | `..` (or NULL) | `(,)` | `unknown` / `unknown` |

The envelope-widening rule for `~` (± one year at year precision, ± one month at month precision) must be a
**documented, versioned constant**, because widening rules change resolution outcomes and therefore must be
reproducible. Put it in `ruleset_version`.

**Critical distinction the outline misses:** `valid_to = NULL` is ambiguous between "ongoing" and "unknown"
and SIG must never rely on NULL alone. A camera deployment with `valid_to = NULL` because the portal still lists it is
a live deployment; one with `valid_to = NULL` because the source never said is an unknown. These lead to opposite
research tasks (monitor vs. investigate). `valid_to_kind` disambiguates.

---

## Part 4 (Section C) — Provenance standards and the mapping

### D6.6 — SIG → PROV-O mapping (normative for the RDF export)

| SIG object | PROV class | Key PROV relations |
|---|---|---|
| `evidence_artifact` | `prov:Entity` (+ `prov:PrimarySource` for Tier A/B, `prov:Quotation` for Tier D) | `prov:wasAttributedTo` publisher agent; `prov:generatedAtTime` = T4 published_at |
| `claim` | `prov:Entity` | `prov:wasDerivedFrom` evidence; `prov:wasGeneratedBy` the extraction activity; `prov:wasRevisionOf` the claim it corrects |
| extraction of a claim | `prov:Activity` | `prov:used` evidence; `prov:wasAssociatedWith` the extractor agent; `prov:startedAtTime`/`endedAtTime` |
| `ingest_run` | `prov:Activity` | `prov:used` all inputs; `prov:wasAssociatedWith` the connector agent |
| parser / model / human | `prov:SoftwareAgent` / `prov:Person` / `prov:Organization` | `prov:actedOnBehalfOf` SIG |
| `resolution` row | `prov:Entity` inside a `prov:Bundle` | `prov:wasDerivedFrom` each considered claim; `prov:qualifiedDerivation` carries `sig:rationaleCode` |
| the resolver ruleset | `prov:Plan` | `prov:hadPlan` on the resolution activity's `prov:Association` |
| source observation (T3) | — | `sig:observedAt` (SIG-minted property; PROV has no "the source looked at the world at" concept) |

Two honest gaps, both worth stating in the spec:

1. **PROV has no valid time.** PROV's times (generation, usage, invalidation — F6.25) are all about the *provenance
   record*, i.e. SIG's T2/T5 axis. The world-truth interval T1 has no PROV vocabulary and must be carried by SIG's own
   predicate or by an external time ontology (OWL-Time). Do not try to squeeze valid time into `prov:generatedAtTime`;
   that is a common and corrupting mistake.
2. **PROV has no confidence or rank.** Those come from the Wikibase-derived layer (F6.22). The export therefore uses
   PROV for *lineage* and SIG-minted terms for *epistemics*, which is the correct division.

### D6.7 — The nanopublication-shaped export

Each SIG claim serializes to three named graphs (F6.23):

```trig
@prefix sig:  <https://sig.example/id/> .
@prefix sigp: <https://sig.example/ont/> .
@prefix prov: <http://www.w3.org/ns/prov#> .
@prefix np:   <http://www.nanopub.org/nschema#> .
@prefix dct:  <http://purl.org/dc/terms/> .

sig:claim/018f3c2a-0000-7000-8000-000000000001 {
  sig:claim/018f...01 a np:Nanopublication ;
      np:hasAssertion      sig:claim/018f...01#assertion ;
      np:hasProvenance     sig:claim/018f...01#provenance ;
      np:hasPublicationInfo sig:claim/018f...01#pubinfo .
}

sig:claim/018f...01#assertion {
  sig:deployment/ABC sigp:activeCameraCount 38 .
  sig:deployment/ABC sigp:validDuring       "2026-07-23/.."^^sigp:edtf .
}

sig:claim/018f...01#provenance {
  sig:claim/018f...01#assertion
      prov:wasDerivedFrom   sig:evidence/QmXyz... ;
      prov:wasGeneratedBy   sig:activity/extract-018f... ;
      sigp:observedAt       "2026-07-23T14:02:11Z"^^xsd:dateTime ;
      sigp:sourceTier       "B" ;
      sigp:confidence       sigp:StronglySupported ;
      sigp:extractionMethod sigp:DeterministicParse ;
      sigp:extractorVersion "flock-portal-parser@3.2.1" .
  sig:activity/extract-018f... a prov:Activity ;
      prov:wasAssociatedWith sig:agent/flock-portal-parser ;
      prov:used              sig:evidence/QmXyz... .
}

sig:claim/018f...01#pubinfo {
  sig:claim/018f...01
      dct:created   "2026-07-23T15:00:00Z"^^xsd:dateTime ;  # T2 lower bound
      dct:license   <https://spdx.org/licenses/CC-BY-4.0.html> ;
      sigp:ingestRun sig:run/2026-07-23-flock-portals ;
      prov:wasAttributedTo sig:agent/sig-project .
}
```

Why this specific shape earns its keep: the assertion graph contains **only** the claim's content, so a consumer who
trusts SIG can load assertion graphs alone and get a clean graph; a consumer who does not can load provenance graphs
and filter by tier. And because each claim is its own set of named graphs, a claim is individually citable and
individually retractable — which is what §6.4 actually requires and what a row-with-a-citation cannot do.

### F6.34 — SPDX license expressions are the right encoding for per-source licensing

**Claim:** SPDX license expressions provide a formal grammar — license IDs, `+`, `AND`, `OR`, `WITH`,
`LicenseRef-`, parentheses, with precedence `+ < WITH < AND < OR` — suitable for machine-readable per-source license
metadata.
**Status:** VERIFIED
**Evidence:** https://spdx.github.io/spdx-spec/v2.3/SPDX-license-expressions/ — license IDs matched
case-insensitively; `LicenseRef-[idString]` (optionally `DocumentRef-` prefixed) for licenses not on the list; `+` =
"the current version of the license or any later version"; `OR` disjunctive, `AND` conjunctive, both commutative;
`WITH` for exceptions (`GPL-2.0-or-later WITH Bison-exception-2.2`); operators case-sensitive; whitespace mandatory
around `AND`/`OR`/`WITH`, forbidden before `+`. Page describes SPDX specification 2.3.0. (SPDX 3.x exists; the
*expression grammar* is stable across versions and 2.3 is the most widely tooled — noted as a caveat.)
**Retrieved:** 2026-08-20
**Implication for the spec:** Every row in `source_registry` and every `evidence_artifact` carries a
`license_spdx` expression. Three SIG-specific consequences:
- **`LicenseRef-` handles the common case.** Most surveillance-relevant sources have bespoke terms ("Flock
  transparency portal terms of use", "city open-data portal terms"). Mint `LicenseRef-SIG-<slug>` identifiers, each
  backed by a stored copy of the terms text as an `evidence_artifact` — so the license claim is itself evidenced. This
  is §14.2 done properly.
- **`AND` expresses the ODbL problem.** A derived table combining OSM with something else is `ODbL-1.0 AND
  LicenseRef-SIG-Other`, which is *machine-detectable*: SIG can write a CI check that refuses to publish an export
  whose combined expression contains `ODbL-1.0` unless the export is declared ODbL. That turns §14.1's legal question
  into a testable build gate (it does not answer the legal question — R-legal must — but it makes the answer
  enforceable).
- **Redistribution permission is a separate boolean.** SPDX expresses the license, not SIG's determination of what it
  may do. Keep `redistributable` as a reviewed human judgement with its own provenance.
**Outline delta:** EXTENDS §14.2 — the outline lists license fields as free text; SPDX makes them
computable, which is the difference between a policy and an enforced policy.

### F6.35 — Croissant, Frictionless, and RO-Crate each cover a different export need

**Claim:** Frictionless Data Package v2 (released 2024-06-26) covers tabular exports with schema, licenses,
sources and contributors; RO-Crate 1.2 (Recommendation, 2025-06-04, `w3id.org/ro/crate/1.2`) covers JSON-LD/schema.org
packaging of arbitrary data with provenance; Croissant v1.1.0 (2026-04-16, Apache-2.0, MLCommons) covers ML dataset
metadata.
**Status:** VERIFIED
**Evidence:**
- https://datapackage.org/ — v2 released 2024-06-26; four specs: Data Package, Data Resource, Table Schema, Table
  Dialect. https://specs.frictionlessdata.io/data-package/ (v1, May 2017) shows only `resources` is required, with
  recommended `licenses` (array with Open Definition license id, path, title), `sources` (title + path/email) and
  `contributors` (title + role/email/path/organization); notes license declarations are "not legally binding".
- https://www.researchobject.org/ro-crate/specification/1.2/ — RO-Crate 1.2, published 2025-06-04, status
  "Recommendation", PID `https://w3id.org/ro/crate/1.2`, JSON-LD context at `/1.2/context`, with sections on Root Data
  Entity and Provenance of entities.
- GitHub API `repos/mlcommons/croissant` → Apache-2.0, latest `v1.1.0` 2026-04-16, 885 stars.
**Retrieved:** 2026-08-20
**Implication for the spec:** Use all three, for different artifacts, and do not conflate them:
- **Frictionless Data Package v2** for the tabular public exports (`claims.csv`, `entities.csv`, `resolutions.csv`,
  `sources.csv`) — it gives per-resource Table Schema and per-package `licenses`/`sources`, and it is already what
  WACZ uses internally (F6.36), so one manifest vocabulary covers both.
- **RO-Crate 1.2** for *evidence bundles* — "here is the contract PDF, the parse output, the claims derived from it,
  and the agent that did it", as one JSON-LD crate. This is the natural unit for a journalist or litigant who wants
  one story's worth of receipts.
- **Croissant** only if SIG ever publishes an ML training set (e.g. a labeled camera-image or text-extraction corpus).
  Not needed for Stage 1–3; record it so nobody reinvents it.
**Outline delta:** EXTENDS §14.3 and §15.7 — the outline says "downloadable datasets" and "documented APIs"
without naming packaging standards. Naming them is what makes the outputs *actually* reusable.

### F6.36 — WACZ is the right container for web captures and already uses Frictionless

**Claim:** WACZ 1.1.1 is a ZIP containing `archive/` (WARC files), `indexes/` (CDXJ), `pages/pages.jsonl`,
plus a root `datapackage.json` conforming to the Frictionless Data Package spec (listing every file with path, byte
size and SHA-256) and an optional `datapackage-digest.json` hashing the manifest itself.
**Status:** VERIFIED
**Evidence:** https://specs.webrecorder.net/wacz/1.1.1/ — "a stable version of the WACZ standard and is in
active use by the Webrecorder project"; directory layout as stated; `datapackage.json` "conforming to the Frictionless
Data Package specification" listing "paths, byte sizes, and SHA256 hashes for verification"; `datapackage-digest.json`
"provides a cryptographic hash for the `datapackage.json` file"; enables retrieval "via HTTP range requests without
requiring specialized server infrastructure"; packages rather than replaces WARC.
**Retrieved:** 2026-08-20
**Implication for the spec:** Portal snapshots (§20 Q17/Q18) should be captured as WACZ, not as bare HTML.
Three reasons that matter for this project specifically: (a) transparency portals are JS-heavy and a WACZ capture
preserves the XHR responses that carry the actual data, so a future re-parse can extract fields the original parser
missed; (b) `datapackage-digest.json` gives a single hash covering the whole capture, which is exactly the `checksum`
field §8.15 asks for; (c) WACZ replays from static hosting via range requests, so SIG can serve "here is the page as
we saw it" with no server. **A deleted portal (§20 Q18) is thereby preserved in a form that can still be *re-parsed*,
not merely displayed.**
**Outline delta:** EXTENDS §8.15 and §20 Q18 — the outline's `archived_copy` field is a URL; WACZ makes it a
self-verifying, re-parseable object.

### F6.37 — OCFL 1.1 is purpose-built for SIG's immutable evidence store

**Claim:** OCFL 1.1 (v1.1.1, 2024-11-07) specifies content-addressed, versioned object storage: a storage
root marked `0=ocfl_1.1`, objects marked `0=ocfl_object_1.1`, sequential `v1/v2/v3…` version directories each
containing an `inventory.json` and a `content/` directory, with a manifest mapping digests to content paths (enabling
dedup across versions), a `head` pointer, and an optional `fixity` block. `sha512` (default) or `sha256` are mandated
for content addressing; md5/sha1/blake2b-512 are permitted for legacy fixity only.
**Status:** VERIFIED
**Evidence:** https://ocfl.io/1.1/spec/ — v1.1.1, 7 November 2024; NAMASTE declarations `0=ocfl_object_1.1`
and `0=ocfl_1.1`; "Version directory names MUST be constructed by prepending `v` to the version number. The version
number MUST be taken from the sequence of positive, base-ten integers: 1, 2, 3, etc."; manifest maps digest → content
paths; digest algorithms `sha512` (default) or `sha256` for content-addressing, others "permitted for legacy fixity
information only"; optional `ocfl_layout.json` at the storage root describing the directory hierarchy.
**Retrieved:** 2026-08-20
**Implication for the spec:** Adopt OCFL 1.1 for the evidence store. The decisive properties for SIG:
(a) **rebuild-from-filesystem** — the inventories are sufficient to reconstruct the whole index without the database,
which is the durability property a volunteer archive needs above all others; (b) **versioned objects** — a portal
snapshotted weekly is one object with N versions, deduplicated by digest, which collapses storage for pages that
rarely change; (c) it is a plain directory layout, so it works on S3, on a local disk, or on a donated university
server, with no service to run.
**Note the digest tension:** OCFL mandates sha512/sha256 for content addressing, while BLAKE3 is faster
(F6.39). Resolution: **use `sha512` for the OCFL manifest (spec conformance, non-negotiable) and additionally record a
`blake3` value in the OCFL `fixity` block and in `evidence_artifact` for fast local verification.** OCFL explicitly
supports extra algorithms in `fixity`.
**Outline delta:** EXTENDS §20 Q25 substantially — the outline asks only "how should source snapshots be
content-addressed", which reads as "pick a hash". The real answer is "pick an archival object layout"; the hash is the
easy part.

### F6.38 — Multihash gives self-describing digests; CIDs are optional sugar

**Claim:** A multihash is `<varint hash-function-code><varint digest-length><digest bytes>`, drawn from the
shared multicodec table (0x11 = sha1, 0x12 = sha2-256), using unsigned base-128 varints.
**Status:** PARTIALLY VERIFIED
**Evidence:** https://github.com/multiformats/multihash — format and rationale as stated ("differentiates
outputs from various well-established cryptographic hash functions, addressing size + encoding considerations"), "Most
Significant Bit unsigned varint (also called base-128 varints)", shared multicodec table with `multihash`-tagged
entries. **CIDv1 composition (multibase + version + multicodec + multihash) was NOT verified** — the fetched page does
not describe it, and the CID spec was not separately fetched.
**Retrieved:** 2026-08-20
**Implication for the spec:** Store digests as **multihash, base32-lowercase encoded**, not as a bare hex
string. The reason is agility: a bare `sha256` hex column bakes the algorithm into the data, and when SIG adds BLAKE3
(or when SHA-256 needs succession in 15 years) every consumer breaks. Multihash makes the algorithm part of the value
at a cost of two bytes. **Do not adopt full IPFS CIDs** — CIDs additionally encode a *codec* (dag-pb, raw) which
implies an IPFS-shaped chunking model SIG does not use, and the composition was not verified here. Multihash alone is
the right level.
**Outline delta:** EXTENDS §20 Q25.

### F6.39 — BLAKE3 is actively maintained (1.8.7, Aug 2026) but SHA-256/512 remains the interop choice

**Claim:** BLAKE3 reference implementations (Rust/C) are at 1.8.7, released 2026-08-20, Apache-2.0, 6.4k stars.
**Status:** VERIFIED
**Evidence:** GitHub API `repos/BLAKE3-team/BLAKE3` → license `Apache-2.0`, latest `1.8.7` published
2026-08-20, pushed 2026-08-20, 6380 stars.
**Retrieved:** 2026-08-20
**Implication for the spec:** **Recommendation: SHA-256 as the primary content address; BLAKE3 as an
auxiliary fixity value.** Justification, since the brief asks for a decisive answer: SIG's evidence store is not
throughput-bound (a portal snapshot is kilobytes to low megabytes; even a large FOIA PDF dump hashes in under a second
either way), and the deciding criterion is therefore *verifiability by third parties with no special tooling*.
`sha256sum` is on every machine on earth; `b3sum` is not. OCFL mandates sha256/sha512 anyway (F6.37). BLAKE3's
advantage — multi-GB/s throughput and a Merkle-tree structure enabling incremental/parallel verification — becomes
relevant only if SIG later stores video or full WARC corpora, at which point the `fixity` block already contains the
values needed.
**Outline delta:** EXTENDS §20 Q25 with a decision and a rationale, not just an option list.

### D6.8 — Concrete evidence-store layout

```
s3://sig-evidence/                          # bucket: versioning ON, Object Lock ON (F6.41)
  0=ocfl_1.1                                # NAMASTE storage-root declaration
  ocfl_layout.json                          # {"extension":"0004-hashed-n-tuple-storage-layout", ...}
  ocfl_extensions/
    0004-hashed-n-tuple-storage-layout/config.json
  8f/2a/c1/8f2ac1.../                       # object path = hashed n-tuple of the object id
    0=ocfl_object_1.1
    inventory.json                          # current inventory (== the head version's)
    inventory.json.sha512
    v1/
      inventory.json
      inventory.json.sha512
      content/
        capture.wacz                        # the bytes as retrieved (F6.36)
        headers.json                        # HTTP response headers, incl. Last-Modified/ETag
        retrieval.json                      # T5, fetcher version, request URL, redirect chain
    v2/
      inventory.json
      content/
        capture.wacz                        # only if bytes changed; else deduped via manifest
```

`inventory.json` (abridged, real OCFL shape):

```json
{
  "id": "https://sig.example/evidence/flock-portal/springfield-pd",
  "type": "https://ocfl.io/1.1/spec/#inventory",
  "digestAlgorithm": "sha512",
  "head": "v2",
  "contentDirectory": "content",
  "manifest": {
    "cf83e1357eef...": ["v1/content/capture.wacz"],
    "a3f5b9c210de...": ["v1/content/retrieval.json"],
    "77e0c4a8813b...": ["v2/content/capture.wacz"]
  },
  "versions": {
    "v1": {
      "created": "2026-07-16T03:14:00Z",
      "message": "scheduled weekly capture; ingest_run=018f3c...",
      "user": {"name": "sig-crawler", "address": "https://sig.example/agent/crawler@2.4.1"},
      "state": {"cf83e1357eef...": ["capture.wacz"], "a3f5b9c210de...": ["retrieval.json"]}
    },
    "v2": {
      "created": "2026-07-23T03:14:00Z",
      "message": "scheduled weekly capture; content changed; ingest_run=018f4a...",
      "user": {"name": "sig-crawler", "address": "https://sig.example/agent/crawler@2.4.1"},
      "state": {"77e0c4a8813b...": ["capture.wacz"], "a3f5b9c210de...": ["retrieval.json"]}
    }
  },
  "fixity": {
    "blake3": {"af1d3c...": ["v1/content/capture.wacz"]}
  }
}
```

Design notes:

- **Object id = logical source identity, not a URL.** `evidence/flock-portal/springfield-pd` is stable even when the
  portal's URL changes; the URL lives in `retrieval.json` per version. This is what lets §20 Q18's "deleted portals"
  remain coherent objects with a final version rather than orphaned files.
- **One object per *source stream*, one version per *capture*.** Weekly captures of an unchanged page cost one
  inventory entry and zero content bytes because the digest already exists in the manifest.
- **`retrieval.json` is separate from the capture** so that "we fetched at T5 and got the same bytes" is recordable
  without duplicating the payload.
- The `user.address` field carries the pinned crawler version — reproducibility (§14.3) starts here.

### F6.41 — S3 Object Lock provides real WORM, with a governance/compliance choice SIG must make deliberately

**Claim:** S3 Object Lock requires versioning; offers governance mode (overridable with
`s3:BypassGovernanceRetention`) and compliance mode (not overridable by anyone including the root user, and the
retention period cannot be shortened); plus legal holds with no expiry.
**Status:** VERIFIED
**Evidence:** https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lock-overview.html — "Object Lock
works only in buckets that have S3 Versioning enabled"; compliance mode: "a protected object version can't be
overwritten or deleted by any user, including the root user in your AWS account… The only way to delete an object
under the compliance mode before its retention date expires is to delete the associated AWS account"; governance mode
requires `s3:BypassGovernanceRetention` plus the `x-amz-bypass-governance-retention:true` header; legal holds "remain
in effect until removed" and are independent of retention periods; permanent DELETE of a protected version returns
403, simple DELETE inserts a delete marker.
**Retrieved:** 2026-08-20
**Implication for the spec:** **Use governance mode with a 7-year default retention, plus legal hold on any
object cited in litigation, and explicitly NOT compliance mode.** The reasoning is the awkward one: compliance mode is
undeletable *even by SIG*, which collides head-on with §13.4 (a public record may contain ethically sensitive content)
and §20 Q32 (takedown/correction requests). A takedown that SIG is legally or ethically obliged to honor, on an object
nobody can delete without terminating the AWS account, is an unacceptable position for a volunteer project. Governance
mode gives WORM against accident and malice while leaving a documented, permissioned, auditable break-glass path. Note
also that Object Lock is AWS-specific in detail though several S3-compatible providers implement it — verify per
provider.
**Outline delta:** EXTENDS §13.4 and §20 Q32 — the outline treats archival durability and takedown as
separate concerns; they are in direct tension at the storage layer and the tension must be resolved by an explicit
mode choice.

### F6.42 — Zenodo gives citable dataset DOIs with concept/version semantics and a 50 GB record limit

**Claim:** Zenodo mints a version-specific DOI per record version and a top-level "concept" DOI covering all
versions; the default limit is 50 GB and max 100 files per record, with larger quotas by request.
**Status:** PARTIALLY VERIFIED
**Evidence:** Direct fetches of https://help.zenodo.org/docs/deposit/describe-records/doi/ (404) and
https://help.zenodo.org/docs/deposit/manage-versions/ (returned only the general versioning description: "versioning
is used when you have updated the files of your published record", each version being "a completely separate record
with its own metadata, files, and persistent identifier", ensuring that when citing a version "the files did not
change"). Quota and concept-DOI specifics obtained via search over https://help.zenodo.org/docs/deposit/manage-quota/,
https://about.zenodo.org/policies and https://blog.zenodo.org/2017/05/30/doi-versioning-launched: 50 GB and max 100
files per record by default, one-time increases (100–200 GB) case by case; DOI versioning lets researchers "cite
either specific versions of a record or… via a top-level DOI, all the versions of a record."
**Retrieved:** 2026-08-20
**Implication for the spec:** Publish each quarterly SIG data release to Zenodo as a new version of one
record: the concept DOI is *the* citation for "the SIG dataset", the version DOI is the citation for "the SIG dataset
as of 2026Q3". Combined with `sig_resolution_as_of()` (D6.5 query a), a paper citing the version DOI can have its numbers
reproduced exactly. **Size constraint is real**: a full evidence-bytes dump will exceed 50 GB quickly, so Zenodo
receives the *derived tabular + RDF exports plus the evidence manifest (digests only)*, not the evidence bytes. The
bytes stay in the OCFL store, verifiable against the published manifest.
**Outline delta:** EXTENDS §14.3 "versioned snapshots" — supplies a concrete citable mechanism and flags
that evidence bytes cannot ride along.

### D6.9 — Making an ingestion run reproducible

```sql
CREATE TABLE ingest_run (
  run_id            uuid PRIMARY KEY DEFAULT uuidv7(),
  connector_id      text NOT NULL,
  connector_version text NOT NULL,       -- semver of the connector
  code_commit       text NOT NULL,       -- git sha of the whole repo
  ruleset_version   text NOT NULL,       -- normalization/resolution policy version
  vocab_version     text NOT NULL,       -- controlled-vocabulary version in force
  started_at        timestamptz NOT NULL,
  ended_at          timestamptz,
  input_manifest    jsonb NOT NULL,      -- [{evidence_id, content_digest}] — exactly what was read
  parameters        jsonb NOT NULL,      -- CLI args, date windows, jurisdiction filters
  claims_written    integer,
  outcome           text NOT NULL,       -- 'success'|'partial'|'failed'
  environment       jsonb                -- OS, python/pg versions, locale, TZ
);
```

Reproducibility rules the spec must enforce:

1. **Every claim carries `ingest_run_id`.** Given a run id you can recover the exact inputs (digests), the exact code
   (commit), the exact policy (ruleset + vocab versions), and the exact outputs (claims).
2. **Normalization must be deterministic and locale-independent.** Set `LC_ALL=C` and `TZ=UTC` in the ingestion
   environment and record them in `environment`. Name normalization that depends on the system locale's collation is a
   silently irreproducible step and a real hazard for agency-name matching.
3. **No wall-clock in derived values.** A claim's `observed_at` comes from the source or from `retrieved_at`, never
   from `now()` at parse time; otherwise re-running an ingest over archived bytes produces different claims, and the
   entire reproducibility story collapses.
4. **Re-run equivalence test in CI.** Re-running a pinned connector over pinned evidence digests must produce
   byte-identical claim tuples modulo `claim_id` and `sys_period`. Make this an actual test.

---

## Part 5 (Section D) — The analytics boundary (Q22)

### F6.43 — DuckDB 1.5.5 + DuckLake 1.0 is a credible, cheap, file-based analytics substrate

**Claim:** DuckDB is MIT, v1.5.5 (2026-07-22), 40k stars; DuckLake v1.0 is stable and supported by DuckDB
v1.5.2+, storing metadata in a SQL catalog database and data in Parquet files, with snapshot-based time travel via `AT
(VERSION => n)`.
**Status:** VERIFIED
**Evidence:** GitHub API `repos/duckdb/duckdb` → MIT, latest `v1.5.5` 2026-07-22, 40,465 stars, pushed
2026-08-20. https://ducklake.select/docs/stable/duckdb/introduction — "DuckLake v1.0 supported by DuckDB v1.5.2 and
later"; two components: a metadata catalog database and Parquet files in a directory (with an auto-created `.files`
folder); "tracks every modification (create, insert, update, delete) as separate snapshots"; time travel via `AT
(VERSION => #)`; © 2026 DuckDB Foundation. DuckDB's spatial extension exists but must be explicitly `INSTALL spatial;
LOAD spatial;` (not autoloadable) and provides R-tree indexing and GDAL integration
(https://duckdb.org/docs/current/core_extensions/spatial/overview.html — page is thin; detailed capability list NOT
verified).
**Retrieved:** 2026-08-20
**Implication for the spec:** Adopt DuckDB + Parquet for the aggregate layer. Adopt DuckLake **only if**
snapshot semantics over aggregates are needed (they probably are, for reproducible published statistics) — and note
the pleasing symmetry that DuckLake's catalog can be a *Postgres* database, so SIG runs one database server and zero
extra services. Iceberg/Delta (F6.44) are the alternative but carry catalog and JVM/engine assumptions that a
volunteer project should avoid at this scale.
**Outline delta:** EXTENDS §8.13 and §20 Q22.

### F6.44 — Iceberg and Delta are alive and well but are the wrong scale of answer

**Claim:** Apache Iceberg 1.11.0 (2026-05-20, Apache-2.0, 9.2k stars) and Delta Lake 4.4.0 (2026-08-20,
Apache-2.0, 8.9k stars) are both actively developed.
**Status:** VERIFIED
**Evidence:** GitHub API: `apache/iceberg` → Apache-2.0, `apache-iceberg-1.11.0` 2026-05-20, pushed
2026-08-20; `delta-io/delta` → Apache-2.0, `v4.4.0` 2026-08-20, pushed 2026-08-20.
**Retrieved:** 2026-08-20
**Implication for the spec:** Record as the migration target if SIG's aggregate volume ever exceeds what
DuckDB comfortably handles on one machine (roughly: tens of billions of rows, or genuine multi-writer concurrency).
Neither is warranted at hundreds of millions of rows read by a handful of analysts. Explicitly noting this prevents
the common failure of adopting a lakehouse table format for a dataset that fits in RAM.
**Outline delta:** none.

### F6.45 — ClickHouse is Apache-2.0 and remains the escape hatch for interactive aggregate queries

**Claim:** ClickHouse is Apache-2.0, 49k stars, releasing on a fast cadence (v26.3.20.7-lts on 2026-08-20).
**Status:** VERIFIED
**Evidence:** GitHub API `repos/ClickHouse/ClickHouse` → Apache-2.0, latest `v26.3.20.7-lts` published
2026-08-20, 49,361 stars, pushed 2026-08-20.
**Retrieved:** 2026-08-20
**Implication for the spec:** Not recommended for Stage 1–3 (a ClickHouse server is another daemon to
operate, secure, back up and upgrade). It becomes the right answer only if SIG offers *interactive public* aggregate
exploration over hundreds of millions of rows. Until then, pre-computed Parquet served statically is both cheaper and
more reproducible.
**Outline delta:** EXTENDS §20 Q22.

### D6.10 — The boundary, precisely

**Rule: the graph stores entities, claims and evidence about *structure*; the analytics store holds
*counts*. Nothing crosses except through a declared join key and a claim that summarizes it.**

```
┌────────────────────────── canonical (Postgres) ──────────────────────────┐
│ entity / claim / resolution / evidence_artifact / ingest_run             │
│                                                                          │
│   claim(subject=Deployment ABC,                                          │
│         predicate='monthly_external_search_count',                       │
│         value_num=1432,                                                  │
│         qualifier: period='2026-07',                                     │
│         value_json={"k_threshold":5,"suppressed":false},                 │
│         evidence -> aggregate_partition digest)                          │
└──────────────────────────────────┬───────────────────────────────────────┘
                                   │  join key: (sig_entity_id, period)
┌──────────────────────────────────▼───────────────────────────────────────┐
│ analytics (Parquet on object storage, queried by DuckDB)                 │
│ usage_agg/                                                               │
│   source_id=hibf/period=2026-07/part-0000.parquet                        │
│     columns: searching_org_sig_id, source_org_sig_id, period,            │
│              search_scope, reason_category, search_count,                │
│              distinct_user_count, suppressed_flag, k_threshold,          │
│              ingest_run_id, agg_ruleset_version                          │
└──────────────────────────────────────────────────────────────────────────┘
```

Six boundary rules:

1. **The join key is `sig_entity_id` (a UUID from `entity`), never a name.** Aggregates are keyed on resolved entity
   ids assigned at ingest time. If entity resolution later merges two orgs, the aggregate files are *not* rewritten;
   the `entity.merged_into` pointer makes the join follow the merge. Rewriting history in the analytics layer would
   break every published statistic.
2. **Raw audit rows never enter either store.** §8.13 and §13.2 are explicit. SIG ingests aggregates from HIBF-style
   sources; if only raw is available, aggregation happens in a *quarantined* pipeline whose output is aggregates and
   whose input is deleted on a documented schedule.
3. **Aggregates are evidence, not claims — until summarized.** The Parquet partition is an `evidence_artifact` with a
   digest. A claim is created only when SIG makes an *assertion* about it ("Deployment ABC performed 1,432 external
   searches in 2026-07"). This keeps the claim table small (thousands of summary claims, not millions of rows) while
   preserving §19.1.
4. **The analytics store is append-only by partition** and each partition carries `ingest_run_id` and
   `agg_ruleset_version`, exactly mirroring the canonical store's reproducibility discipline.
5. **Cardinality budget.** Pre-aggregate to (searching_org × source_org × month × search_scope × reason_category).
   With ~20k orgs the theoretical cross-product is astronomical but the realized set is sparse — a few million rows
   per year, which is a few hundred MB of Parquet. **Do not pre-aggregate at daily granularity**: it multiplies rows
   by ~30 for near-zero analytical gain and materially worsens the privacy profile (see D6.11).
6. **One-way flow.** The analytics store never writes to Postgres. Summary claims are written by an explicit,
   reviewable job, not by a database link.

### D6.11 — Privacy implications of aggregate granularity

### F6.46 — Authoritative small-cell thresholds could not be verified from HHS

**Claim:** Could not verify HHS/OCR de-identification guidance on small cell sizes.
**Status:** INACCESSIBLE
**Evidence:** https://www.hhs.gov/hipaa/for-professionals/special-topics/de-identification/index.html →
HTTP 403 Forbidden to automated fetch.
**Retrieved:** 2026-08-20
**Implication for the spec:** SIG's thresholds must be justified on its own reasoning and stated as
policy, not as compliance with an external standard SIG has not verified. A later pass should fetch the guidance
manually (or cite the FCSM disclosure-limitation working paper) before claiming regulatory grounding.
**Outline delta:** none.

The reasoning SIG can stand behind without external citation:

- **The re-identification risk in SIG's aggregates is not about the searching officer — it is about the searched
  person.** A cell like (searching_org = Springfield PD, source_org = Rural County SO, reason_category =
  "immigration", month = 2026-07, count = 1) plus a local news story about one arrest is a near-identification of a
  specific person's exposure. This risk *increases* as granularity increases and as counts decrease.
- **Recommended policy (k = 5, with a documented rationale):**
  - Cells with `search_count` in 1..4 are **suppressed**: published as `count = null`, `suppressed_flag = true`,
    `k_threshold = 5`. Never published as 0 — that is a lie and it breaks §19.4.
  - **Complementary suppression is mandatory.** If exactly one cell in a row is suppressed, the row total reveals it.
    The aggregation job must suppress a second-smallest cell whenever a single suppression would be invertible. This
    is the step naive implementations skip and it is the step that actually matters.
  - Row/column totals are published only when all constituent cells are published or when complementary suppression
    has been applied.
  - The finest published time granularity is **month**. Daily counts are computed internally if needed but never
    published.
  - `reason_category` is published only from a **controlled, coarse vocabulary**; free-text reason strings from audit
    exports are never published, because officers type identifying details into them.
- **Asymmetry rule (this is the ethically important one):** the k-threshold protects *individuals searched*, not
  *institutions searching*. An agency performing 3 searches is not entitled to suppression on the theory that its own
  conduct is sensitive — §13.1 is explicit that SIG observes institutions. So suppression applies to cells whose small
  count could identify a *person*, and the policy should record for each suppression which of the two rationales
  applied. Where a small count reveals only institutional behavior (e.g. "this PD has 2 sharing partners"), publish
  it.
- **Aggregation is not anonymization.** State this plainly in the published docs. SIG publishes aggregates because
  they are *sufficient for accountability*, not because they are provably safe.

---

## Part 6 (Section E) — Geospatial

### D6.12 — SRIDs, indexing, precision

- **Store in EPSG:4326** (`geometry(Geometry, 4326)`). Rationale: it is what OSM, DeFlock, GPS, and every public data
  source emits; storing anything else means every ingest is a reprojection with rounding.
- **Serve tiles in EPSG:3857** via `ST_Transform(geom, 3857)` inside `ST_AsMVT`. Never store 3857 — it distorts
  distance and is meaningless above ~85° latitude, and SIG will eventually have international data (§5).
- **Distance queries must use geography, not degrees.** `ST_DWithin(a.geom::geography, b.geom::geography, 50)` for
  "within 50 metres". A `ST_DWithin` on 4326 geometry takes a *degree* radius, which is the single most common PostGIS
  bug and would silently produce latitude-dependent proximity attribution — fatal for §11.2 device attribution.
- **Index:** `CREATE INDEX ON claim USING gist (value_geom)` for geometry claims; add `CREATE INDEX ON
  physical_asset_current USING gist (geom)` on the projection. For proximity-heavy workloads consider `gist (geom)
  INCLUDE (asset_id)` or SP-GiST for point-only tables.
- **H3 for binning:** use the `h3-pg` extension (F6.47), storing `h3_lat_lng_to_cell(geom, 8)` as a generated column
  for coverage/density aggregation. H3 resolution 8 (~0.7 km² hexes) is the right default for "camera density by
  neighborhood" without being a precise location. **H3 bins double as a privacy primitive** — publishing a
  resolution-7 or -8 cell instead of a point is a principled precision reduction.

### F6.47 — h3-pg moved to the PostGIS org and supports PG 14–18

**Claim:** `zachasme/h3-pg` was archived 2025-12-30 and development moved to `postgis/h3-pg`, which is
Apache-2.0, tracks H3 v4, and CI-tests PostgreSQL 14–18 on Linux and macOS.
**Status:** VERIFIED
**Evidence:** https://github.com/zachasme/h3-pg — "The repository was archived December 30, 2025, and is now
read-only. Development has moved to the official PostGIS repository at `postgis/h3-pg`."
https://github.com/postgis/h3-pg — confirms it is the maintained home; Apache-2.0; H3 v4 (released 2022-08-23) with
camelCase→snake_case function naming; CI covers PostgreSQL 14–18 on Linux and macOS; binaries for Ubuntu 22.04+,
Rocky/EL 8+/Fedora 37+, and Windows via PostGIS Bundle 3.3+; 381 stars, 395 commits, active PRs/issues; developed with
Scandinavian Highlands, maintained under the PostGIS org.
**Retrieved:** 2026-08-20
**Implication for the spec:** H3 v4 in Postgres is viable and now has *better* institutional backing than
before (PostGIS org rather than an individual). Pin `postgis/h3-pg`, not the archived repo — dependency manifests and
install docs that reference `zachasme/h3-pg` will rot.
**Outline delta:** EXTENDS §15.2 — supplies a maintained binning primitive for the infrastructure map.

### D6.13 — Non-point assets: four distinct geometry cases, never conflated

The outline (§8.6) says "Coordinates must not be required for movable assets" but does not say what to store instead.
Four cases, four representations, all as *claims* with distinct predicates:

| Case | Predicate | Geometry | Notes |
|---|---|---|---|
| Fixed device, observed location | `asset_location` | `POINT` | precision per D6.14; provenance = OSM/DeFlock/field observation |
| Mobile asset (e.g. mobile ALPR, trailer) | `asset_operating_area` | `POLYGON`/`MULTIPOLYGON` | the *jurisdiction or beat* it operates in; **no point, ever** |
| Service/coverage area (e.g. RTCC coverage) | `service_area` | `MULTIPOLYGON` | usually a jurisdiction boundary joined from a census/TIGER geometry |
| Unlocated asset (known to exist, location unknown) | `asset_location` with `value_kind='somevalue'` | NULL | **this is why `somevalue` exists** (F6.22) |

**Derived FOV geometry is a separate table and a separate epistemic class.** PanoptiCity-style
field-of-view cones are *inferences* from (point, bearing, lens model, assumed range), not observations:

```sql
CREATE TABLE derived_geometry (
  derived_id      uuid PRIMARY KEY DEFAULT uuidv7(),
  asset_entity    uuid NOT NULL REFERENCES entity(entity_id),
  derivation_kind text NOT NULL,        -- 'fov_cone'|'coverage_estimate'|'road_segment_snap'
  geom            geometry(Geometry, 4326) NOT NULL,
  model_version   text NOT NULL,        -- pinned FOV model
  input_claims    uuid[] NOT NULL,      -- the source claims this was computed from
  assumptions     jsonb NOT NULL,       -- {"range_m":45,"fov_deg":32,"bearing_source":"osm:direction"}
  computed_at     timestamptz NOT NULL DEFAULT clock_timestamp(),
  sys_period      tstzrange NOT NULL DEFAULT tstzrange(clock_timestamp(), NULL, '[)')
);
```

`derived_geometry` is never queried as though it were evidence, is always rendered in a visually distinct style, and
is fully regenerable from `input_claims` + `model_version`. This is §9's fact/inference distinction made structural
rather than editorial. **A FOV cone that someone screenshots and treats as a measured fact is a foreseeable harm; the
schema should make the derived status impossible to lose.**

### D6.14 — Coordinate precision as a privacy control (§13.3)

Five mechanisms, ordered from least to most protective, applied by `sensitivity_tier`:

| Tier | Asset situation | Mechanism | Published precision |
|---|---|---|---|
| 0 | Publicly visible roadside device on public right-of-way | none | full source precision (typically ~1 m) |
| 1 | Device on public infrastructure, not obviously visible | precision reduction | truncate to 4 decimal places (~11 m) |
| 2 | Private-residence candidate; private property | H3 binning | H3 res 8 cell centroid (~0.7 km²) |
| 2 | Mobile asset | area only | operating-area polygon; no point |
| 3 | Confidential facility; safety-flagged | suppression | geometry withheld; existence + jurisdiction published |

Implementation notes that determine whether this actually works:

- **Reduce precision, do not jitter, for tier 1.** Truncation is deterministic, idempotent, and honest (the published
  number is a real prefix of the true one). Random jitter is worse in three ways: it produces a *false* coordinate,
  repeated publications leak the true value through averaging, and it cannot be reproduced in an audit. If jitter is
  ever used, the radius must be published *and* the offset must be derived deterministically from a per-asset secret
  so it never changes between releases.
- **The true geometry stays in the canonical store**, protected by RLS (F6.8); the public API and public exports read
  from a *view* that applies the tier transform. Never store only the degraded value — that destroys SIG's ability to
  correct or reclassify later.
- **The tier is itself a reviewable claim** with provenance ("classified tier 2 because the OSM node is within a
  residential parcel, reviewer X, 2026-08-20"), not an opaque column. §13.3 asks for contextual handling; contextual
  means someone made a judgement, and judgements need attribution.
- **Aggregate-level leakage:** publishing both a suppressed point *and* an exact camera count for a small area can
  re-identify location. The tier transform must be applied before, not after, spatial aggregation.

### F6.48 — PMTiles v3 + tippecanoe is the correct static-first tile stack; martin if dynamic is needed

**Claim:** PMTiles v3 is a single-file tile archive with a 127-byte header and Hilbert-ordered directory
entries designed for HTTP range-request access from static storage; tippecanoe (BSD-2-Clause, felt/tippecanoe, v2.79.0
2025-07-24) generates vector tilesets; martin (Apache-2.0, v1.14.0 2026-08-18) serves PostGIS, MBTiles and PMTiles
dynamically.
**Status:** VERIFIED
**Evidence:**
- https://github.com/protomaps/PMTiles/blob/main/spec/v3/spec.md — 127-byte fixed header, magic "PMTiles", version
  byte `0x03`, eight offset/length fields, tile counts, clustered flag, internal + tile compression fields,
  zoom/position bounds; root directory within the first 16,384 bytes ("The size of the header plus the compressed size
  of the root directory MUST NOT exceed 16384 bytes"); directory entries (TileID via Hilbert curve, Offset, Length,
  RunLength where 0 = leaf directory); delta-encoded varints; compression options none/gzip/brotli/zstd. **License of
  the spec was not stated on the fetched page**; GitHub API for `protomaps/PMTiles` reports license `NOASSERTION` and
  **no GitHub releases**, 3.0k stars, pushed 2026-08-19.
- GitHub API `repos/felt/tippecanoe` → BSD-2-Clause, latest `2.79.0` 2025-07-24, pushed 2026-08-14 (note: the
  canonical tippecanoe is now the `felt` fork, not `mapbox/tippecanoe`).
- GitHub API `repos/maplibre/martin` → Apache-2.0, latest `martin-v1.14.0` 2026-08-18, pushed 2026-08-20, 3.8k stars —
  "Blazing fast and lightweight PostGIS, MBtiles and PMtiles tile server".
- `CrunchyData/pg_tileserv` and `go-spatial/tegola` API lookups were **not completed** (GitHub rate limit exhausted);
  their status is UNVERIFIED here.
**Retrieved:** 2026-08-20
**Implication for the spec:** **Recommended serving stack: `ST_AsMVT`-free.** Generate GeoJSON from the
resolution projection → `tippecanoe` → a single `.pmtiles` file → upload to object storage/CDN → MapLibre reads it by
range request. No tile server, no per-request database load, no scaling story needed, and the tile archive is a
versioned, hashable artifact that can itself be published and cited (which `ST_AsMVT` output cannot). Use `martin`
only for internal/editor views where tiles must reflect uncommitted state. The 16 KB root-directory cap is worth
knowing: at national scale, leaf directories will be used, costing one extra range request per tile fetch — irrelevant
for SIG's traffic.
**Outline delta:** EXTENDS §15.2 — the outline describes a map product without a serving architecture. The
static-first choice is what makes §15.2 affordable indefinitely, and it aligns with §14.3 (the tile archive is a
downloadable dataset, not just a service).

---

## Part 7 (Section F) — Schema versioning, migration, and vocabulary evolution

### F6.49 — Migration tooling: sqitch, dbmate, Atlas, Alembic, Flyway all current

**Claim:** As of Aug 2026: sqitch v1.6.1 (MIT, 2026-01-06); dbmate v2.35.0 (MIT, 2026-08-07); Atlas v1.3.0
(Apache-2.0, 2026-08-02); Alembic rel_1_19_1 (MIT, 2026-08-08); Flyway 13.3.0 (repo Apache-2.0, 2026-08-13,
Redgate-owned with a commercial edition).
**Status:** VERIFIED
**Evidence:** GitHub API: `sqitchers/sqitch` MIT, `v1.6.1` 2026-01-06, pushed 2026-08-02, 3.2k stars;
`amacneil/dbmate` MIT, `v2.35.0` 2026-08-07, pushed 2026-08-19, 7.1k stars; `ariga/atlas` Apache-2.0, `v1.3.0`
2026-08-02, 8.7k stars — "Declarative schema migrations with schema-as-code workflows"; `sqlalchemy/alembic` MIT,
`rel_1_19_1` 2026-08-08, 4.3k stars; `flyway/flyway` Apache-2.0, `flyway-13.3.0` 2026-08-13, 10.0k stars, "Flyway by
Redgate".
**Retrieved:** 2026-08-20
**Implication for the spec:** **Recommend sqitch.** Justification against the alternatives, since the brief
wants a decision: (a) sqitch models migrations as a *dependency DAG with explicit deploy/revert/verify scripts in
plain SQL*, which matches a database whose correctness depends on triggers, exclusion constraints, RLS policies and
partitioning — things ORM-oriented tools express badly; (b) the mandatory `verify` script is a genuine and unusual
safety feature for a volunteer team where the person deploying is often not the person who wrote the migration; (c) it
is plain SQL, so it does not bind SIG to a language runtime (a Python-only shop today may be a Rust/Go shop in three
years); (d) MIT, no commercial edition, no vendor. **Atlas is the credible runner-up** (declarative diffing, excellent
CI integration) and would be the choice if SIG preferred desired-state over imperative migrations — but declarative
diffing tends to generate destructive plans for partitioned, trigger-laden schemas, which is precisely SIG's shape.
Alembic is fine if the whole stack is Python but couples migrations to SQLAlchemy models, which conflicts with LinkML
being the schema source of truth (F6.50). Flyway's Redgate ownership and open-core model is an avoidable dependency.
**Outline delta:** EXTENDS §20 — the outline does not address migration tooling at all.

### F6.50 — LinkML 1.11.1 can generate SQL DDL, JSON Schema, OWL/SHACL, Pydantic and docs from one YAML schema

**Claim:** LinkML (Apache-2.0, v1.11.1 released 2026-05-20, actively developed) is a YAML schema language
with generators for JSON Schema, SHACL, ShEx, OWL, Python/Pydantic, Java, TypeScript, Rust, SQL DDL, SQLAlchemy,
GraphQL, OpenAPI, ProtoBuf, RDF/JSON-LD, SPARQL, Excel/CSV, and documentation/ER diagrams.
**Status:** VERIFIED
**Evidence:** https://linkml.io/linkml/ — "a modeling language allowing developers to author schemas in YAML
that describe data structure", plus a validation framework across JSON/RDF/TSV; generator list as stated; "LinkML is
open source (licensed under the Apache-2.0 license) and community-driven"; ecosystem includes the INCLUDE Data
Coordination Center. GitHub API `repos/linkml/linkml` → Apache-2.0, latest `v1.11.1` 2026-05-20, pushed 2026-08-20,
597 stars.
**Retrieved:** 2026-08-20
**Implication for the spec:** **Adopt LinkML as the single source of truth for the SIG ontology**
(§8's entity types, predicates, value datatypes, enums). One YAML tree generates: the JSON Schema that validates
connector output; the OWL/SHACL that types the RDF export (D6.7); the Pydantic classes the ingestion code uses; the
human-readable ontology docs; and an ER diagram. **Caveat, stated honestly:** the 597-star count means a small
community, so SIG should (a) pin the LinkML version, (b) treat generated SQL DDL as a *starting point* that
hand-written sqitch migrations then refine — LinkML will not generate `tstzrange` exclusion constraints, partitioning,
or RLS policies, and pretending otherwise would be the trap here. The division of labor: **LinkML owns the ontology
(what predicates exist, what they mean, what types they take); sqitch owns the physical schema (how it is stored and
constrained).**
**Outline delta:** EXTENDS §8 and §14.3 — the outline presents the ontology as prose. Prose ontologies drift
from implementations within one release. A LinkML source makes §8 executable and publishable.

### D6.15 — Evolving a controlled vocabulary without invalidating historical claims

The problem: SIG will discover in 2027 that `lifecycle_status = 'active'` should have been split into `'active_full'`
and `'active_pilot'`. Half a million claims already use `'active'`. What happens?

**The answer is versioned vocabularies plus crosswalks, never in-place redefinition.** Five rules:

1. **Vocabulary terms are immutable once published.** A term's IRI and its definition never change. If the definition
   was wrong, the term is *deprecated* and a new one is minted. This mirrors the claim table's own discipline and for
   the same reason.
2. **Every vocabulary release is a version** (`vocab_version = '2026.1'`, `'2027.1'`), published as a SKOS concept
   scheme (F6.51) with a stable IRI per version, archived in the evidence store, and cited by
   `ingest_run.vocab_version` and by every claim through its run.
3. **Deprecation, not deletion:** `vocab_predicate.deprecated_at` and `superseded_by`. Historical claims keep pointing
   at the deprecated term, and they remain *correct* — they were made under that vocabulary.
4. **Crosswalks are SKOS mapping assertions, and they carry the information loss explicitly:**

```sql
CREATE TABLE vocab_crosswalk (
  from_vocab_version text NOT NULL,
  from_term          text NOT NULL,
  to_vocab_version   text NOT NULL,
  to_term            text NOT NULL,
  mapping_relation   text NOT NULL,   -- skos:exactMatch|broadMatch|narrowMatch|closeMatch|relatedMatch
  lossy              boolean NOT NULL,
  note               text,
  PRIMARY KEY (from_vocab_version, from_term, to_vocab_version, to_term)
);
```
  For the split above: `('2026.1','active','2027.1','active_full','skos:narrowMatch', true, 'pre-2027 "active" did not distinguish pilots')`.
  A query written against 2027 vocabulary that needs 2026 data goes through the crosswalk and **inherits the
  `lossy` flag into its result metadata**, so a UI can say "includes 412,000 claims whose pilot status is
  undetermined". Silently mapping lossy terms is how a versioned vocabulary becomes a lie.
5. **Never rewrite historical claims to the new vocabulary.** Rewriting destroys the record of what the source
   actually said under the vocabulary in force at the time — a direct violation of §19.1 and §19.2. If a bulk
   re-classification is genuinely warranted, it is done as *new claims* with `extraction_method =
   'vocabulary_migration'`, `revises_claim` pointing at the originals, and its own ingest run — fully auditable and
   fully revertible.

### F6.51 — SKOS is the right publication format for SIG's controlled vocabularies

**Claim:** SKOS (W3C Recommendation, 2009-08-18, namespace `http://www.w3.org/2004/02/skos/core#`) provides
`Concept`, `ConceptScheme`, `Collection`, `prefLabel`/`altLabel`/`hiddenLabel`, non-transitive `broader`/`narrower`
plus transitive variants, `related`, mapping properties (`exactMatch` transitive, `closeMatch`, `broadMatch`,
`narrowMatch`, `relatedMatch`), `notation`, and documentation properties including `changeNote`, `editorialNote`,
`historyNote`.
**Status:** VERIFIED
**Evidence:** https://www.w3.org/TR/skos-reference/ — W3C Recommendation 18 August 2009; namespace as
stated; "A SKOS concept can be viewed as an idea or notion; a unit of thought"; max one `prefLabel` per language tag;
`broader`/`narrower` are direct links only and deliberately not transitive, with
`broaderTransitive`/`narrowerTransitive` provided separately; `related` symmetric and non-transitive; integrity rule
that associative and hierarchical relations cannot coexist between the same two concepts; `exactMatch` transitive vs
`closeMatch` non-transitive; `notation` for lexical codes;
`definition`/`scopeNote`/`example`/`changeNote`/`editorialNote`/`historyNote`; open-world assumption.
**Retrieved:** 2026-08-20
**Implication for the spec:** Publish SIG's controlled vocabularies (technology capabilities §8.4, lifecycle
states §8.7, incident types §8.14, source tiers §9.1, confidence labels §9.3, reason categories) as SKOS concept
schemes with versioned IRIs. Four concrete payoffs: (a) `skos:historyNote` and `skos:changeNote` are the natural home
for the deprecation narrative in D6.15; (b) `skos:altLabel` and `skos:hiddenLabel` absorb vendor marketing names and
common misspellings, directly feeding entity resolution — `hiddenLabel` is explicitly designed for "misspellings" and
is exactly right for agency-name matching; (c) the mapping properties give the crosswalk table (D6.15) standard
semantics rather than SIG-invented ones; (d) `broadMatch`/`narrowMatch` to EFF Atlas and Wikidata vocabularies make
§18 federation concrete.
**Caution:** heed the integrity rule — do not assert both `broader` and `related` between the same pair, a
common error when a vocabulary is edited by many hands. Validate with SHACL generated from LinkML.
**Outline delta:** EXTENDS §8.4, §9.1, §9.3 — the outline lists vocabulary values inline in prose with no
publication or versioning mechanism.

### D6.16 — Migration discipline summary

- Every schema change is a sqitch change with `deploy`/`revert`/`verify`.
- Changes touching `claim` are **additive only**: new nullable columns, new partitions, new indexes `CONCURRENTLY`.
  Dropping or retyping a `claim` column requires a documented, reviewed data-migration change that writes new claims
  rather than mutating old ones.
- Vocabulary changes are *data* migrations against `vocab_predicate` + `vocab_crosswalk`, versioned independently of
  the DDL. A vocabulary release does not require a schema release and vice versa.
- CI must, on every PR: apply all migrations to an empty database; apply them to a restored anonymized snapshot; run
  `verify`; regenerate LinkML artifacts and fail if the committed artifacts differ (prevents the YAML and the DDL
  silently diverging); run the re-run-equivalence test from D6.9.

---

## Open questions

1. **`FOR PORTION OF` semantics in application code (F6.9).** PG18 has temporal constraints but no `FOR PORTION OF`.
   The exact algorithm for closing out part of a valid-time interval in an append-only model (does it emit one
   superseding claim or two? how does the resolver treat the residue?) needs to be specified and tested before Stage
   1. Hedge: implement as a single stored procedure with an explicit test matrix, and do not let connectors do it ad
   hoc.
2. **Snodgrass primary text unverified (F6.31).** The canonical academic definitions of transaction-time properties
   could not be fetched (TLS failure). The design does not depend on it, but the spec should cite a fetchable
   authority (ISO/IEC 9075-2:2011 §4.16, or the XTDB docs) rather than a URL that fails.
3. **HHS/statistical-disclosure thresholds unverified (F6.46).** The k=5 recommendation in D6.11 is SIG's own policy
   reasoning, not verified compliance with any external guidance. Before publishing aggregates, a pass should verify
   against the FCSM disclosure-limitation literature and state the basis explicitly.
4. **GeoSPARQL support in Oxigraph/QLever untested (F6.29).** If SIG ever wants the RDF export to be spatially
   queryable, this needs testing. Hedge: publish geometry as WKT literals with the GeoSPARQL datatype regardless, so
   the data is ready even if no endpoint indexes it.
5. **CIDv1 composition unverified (F6.38).** Multihash is verified; the full CID spec is not. The recommendation
   avoids CIDs, so this is low-risk, but if IPFS distribution is later desired the CID spec must be read properly.
6. **GraphDB Free edition terms (F6.28).** Not obtainable from the docs site. Only matters if someone proposes
   GraphDB; the burden should be on that proposal.
7. **pg_tileserv and tegola status (F6.48).** GitHub API rate limit prevented verification. The recommendation (static
   PMTiles) does not depend on either, but if a dynamic tile server is later needed, verify both alongside martin.
8. **PMTiles specification license (F6.48).** GitHub reports `NOASSERTION` for `protomaps/PMTiles` and the spec page
   did not state a license. Since SIG would produce PMTiles files rather than redistribute the spec, risk is low, but
   the dependency license manifest needs a real answer.
9. **Legal erasure vs append-only (D6.4/F6.41).** If SIG ever receives a legally binding erasure demand, the
   append-only claim table and WORM evidence store both resist it by design. A tombstone procedure — what is deleted,
   what stub remains, who authorizes it, how it is disclosed — must be designed with legal input, not invented at the
   moment of the demand.
10. **Whether to run a SPARQL endpoint at all.** Oxigraph is honest about being unoptimized (F6.28); QLever is fast
    but heavier. Publishing N-Quads dumps may fully satisfy §14.3 at zero operational cost. Defer until there is a
    demonstrated consumer.
11. **Resolution recomputation cost at scale.** The resolver rewrites `resolution` rows whenever claims or rulesets
    change. At tens of millions of claims the full-recompute time is unknown and needs measurement; if it exceeds a
    maintenance window, an incremental resolver keyed on `(subject_id, predicate_id)` dirty-sets is required.
12. **Nanopublication network liveness (F6.23).** Network size and health could not be verified. Adopting the
    serialization is safe; adopting the network as a dependency is not, until verified.

---

## Spec requirements emitted

**Storage architecture**

- **REQ-R6-01** — Canonical storage MUST be PostgreSQL >= 18 with PostGIS >= 3.6.3. All other stores (graph, RDF,
  analytics, tiles, search indexes) MUST be derived projections that can be dropped and rebuilt from canonical data
  plus the evidence store.
- **REQ-R6-02** — The `claim` table MUST be append-only. An enforcement trigger MUST reject any UPDATE that modifies
  any column other than the upper bound of `sys_period`, and a rule MUST make DELETE a no-op.
- **REQ-R6-03** — Entity tables MUST contain identity only (`entity_id`, `entity_type`, `merged_into`). Every
  attribute of every entity MUST be expressed as a claim.
- **REQ-R6-04** — No component MAY be adopted as canonical if its access control, backup, or production use requires a
  commercial license or a source-available (non-OSI) license. (Excludes Neo4j Enterprise features and Memgraph
  BUSL-1.1.)
- **REQ-R6-05** — Apache AGE, pgvector, pg_ivm and any other extension MUST be optional: the system MUST start,
  ingest, resolve, and serve with zero non-PostGIS extensions installed.
- **REQ-R6-06** — Claim primary keys MUST be UUIDv7 generated by `uuidv7()`.

**Temporal model**

- **REQ-R6-07** — Every claim MUST record three times: valid time (`valid_period` tstzrange + `valid_edtf` +
  `valid_from_kind`/`valid_to_kind`), observation time (`observed_at`), and transaction time (`sys_period`,
  database-assigned). Publication time and retrieval time MUST be stored on `evidence_artifact` and MUST NOT be
  duplicated onto claims.
- **REQ-R6-08** — `sys_period`'s lower bound MUST be database-assigned and immutable; its upper bound MUST be set only
  when SIG corrects its own record, never when the world changes.
- **REQ-R6-09** — The system MUST expose a two-argument as-of function `sig_resolution_as_of(belief_time, valid_time)`
  and all public exports MUST be reproducible via it.
- **REQ-R6-10** — Uncertain, approximate, and open-ended dates MUST be encoded as EDTF Level 1 strings, with a derived
  `tstzrange` envelope produced by a pinned, versioned, deterministic function. The envelope widening rules MUST be
  recorded in `ruleset_version`.
- **REQ-R6-11** — `valid_to IS NULL` MUST NOT be used to mean "ongoing"; `valid_to_kind` MUST distinguish `ongoing`
  from `unknown`, and the API MUST surface the distinction.
- **REQ-R6-12** — Correcting an erroneous claim MUST close the original's `sys_period` and insert a new claim with
  `revises_claim` set. Deleting or overwriting the original is prohibited.

**Claims, contradiction, and resolution**

- **REQ-R6-13** — Claims MUST support three value kinds — `value`, `somevalue` (exists but unknown), `novalue`
  (asserted not to exist) — and NULL MUST NOT be used to express either of the latter two.
- **REQ-R6-14** — Claims MUST support qualifiers (`claim_qualifier`) and a set of evidence references
  (`claim_evidence`) with roles `supports` / `contradicts` / `context`.
- **REQ-R6-15** — Resolution MUST be a stored table, not a view, and MUST record `winning_claim`, `considered_claims`,
  `contradiction_state`, `rationale_code`, `rationale_text`, `confidence`, `resolver_version`, `ruleset_version`, and
  `decided_by`.
- **REQ-R6-16** — `contradiction_state = 'unresolved_conflict'` MUST be a publishable outcome; the API MUST be able to
  return a disagreement with all competing claims rather than forcing a single value.
- **REQ-R6-17** — At most one resolved value per (subject, predicate) MAY be current for any instant of valid time;
  this MUST be enforced by a GiST exclusion constraint, not by application code.
- **REQ-R6-18** — Claims MUST carry `rank` (preferred/normal/deprecated); a discredited claim MUST be ranked
  `deprecated` and retained, never deleted.
- **REQ-R6-19** — `resolver_version` and `ruleset_version` MUST be versioned independently, and any resolution row
  MUST be regenerable from its inputs for verification.

**Provenance, evidence, reproducibility**

- **REQ-R6-20** — Evidence bytes MUST be stored in an OCFL 1.1 storage root, with `sha512` content addressing in the
  inventory and an additional `blake3` value in the `fixity` block.
- **REQ-R6-21** — `evidence_artifact.content_digest` MUST be stored as a multihash (base32-lowercase), not as a bare
  hex digest, so the algorithm is part of the value.
- **REQ-R6-22** — Web captures MUST be stored as WACZ 1.1.1 packages so that captured pages remain re-parseable, not
  merely displayable.
- **REQ-R6-23** — Object storage holding evidence MUST have versioning enabled and Object Lock in **governance** mode
  with a documented default retention; compliance mode MUST NOT be used, so that §13.4/Q32 takedown obligations remain
  satisfiable through a permissioned, audited path.
- **REQ-R6-24** — SIG MUST publish an RDF export in which every claim is serialized as three named graphs (assertion /
  provenance / publication info) using PROV-O for lineage and SIG-minted terms for epistemics. The public read API
  MUST be a hand-written versioned contract, not a schema reflection.
- **REQ-R6-25** — Every claim MUST reference an `ingest_run` recording connector version, code commit, ruleset
  version, vocabulary version, input evidence digests, parameters, and environment.
- **REQ-R6-26** — Re-running a pinned connector over pinned evidence digests MUST produce byte-identical claim tuples
  modulo `claim_id` and `sys_period`; this MUST be enforced by a CI test.
- **REQ-R6-27** — Ingestion MUST run with `LC_ALL=C` and `TZ=UTC`, and MUST NOT use wall-clock time in any derived
  claim value.
- **REQ-R6-28** — Every source and every evidence artifact MUST carry an SPDX license expression, using
  `LicenseRef-SIG-<slug>` for bespoke terms, and the referenced terms text MUST itself be archived as evidence.
  Redistribution permission MUST be a separately reviewed boolean.
- **REQ-R6-29** — The build MUST fail if a published export's combined SPDX expression includes a share-alike license
  (e.g. `ODbL-1.0`) that the export's own declared license does not satisfy.
- **REQ-R6-30** — Tabular public exports MUST ship as a Frictionless Data Package v2; evidence bundles MUST ship as
  RO-Crate 1.2; each quarterly release MUST be deposited to Zenodo, citing the concept DOI for the dataset and the
  version DOI for the release. Evidence bytes MUST NOT be deposited (size limits); the evidence manifest of digests
  MUST be.

**Analytics boundary**

- **REQ-R6-31** — High-volume aggregates MUST live outside PostgreSQL, as Hive-partitioned Parquet queried by DuckDB.
  No columnar Postgres extension may be adopted as canonical.
- **REQ-R6-32** — Aggregate partitions MUST join to the graph only via `sig_entity_id` UUIDs and period, never via
  names, and MUST carry `ingest_run_id` and `agg_ruleset_version`.
- **REQ-R6-33** — Aggregate partitions MUST be registered as evidence artifacts with digests; a claim is created only
  when SIG asserts a summary statement about a partition.
- **REQ-R6-34** — Raw per-search/per-plate audit rows MUST NOT be stored in either the canonical store or the
  published analytics store.
- **REQ-R6-35** — Published aggregate cells with counts 1–4 MUST be suppressed (published as null with
  `suppressed_flag` and `k_threshold`, never as zero), complementary suppression MUST be applied so single
  suppressions are not invertible from totals, and the finest published time granularity MUST be one month.
- **REQ-R6-36** — Suppression MUST record which rationale applied (protecting an individual vs. no suppression
  warranted for institutional conduct); institutional small counts MUST NOT be suppressed merely because they are
  small.

**Geospatial**

- **REQ-R6-37** — Geometry MUST be stored in EPSG:4326 and reprojected only at serving time. Proximity queries MUST
  cast to `geography` (metres); degree-based `ST_DWithin` on 4326 geometry is prohibited.
- **REQ-R6-38** — Mobile assets MUST be represented by an operating-area polygon, and assets of unknown location by a
  `somevalue` location claim; a synthetic point MUST NOT be invented for either.
- **REQ-R6-39** — Derived geometry (FOV cones, coverage estimates, road snapping) MUST live in a separate
  `derived_geometry` table recording `model_version`, `input_claims` and `assumptions`, MUST be regenerable, and MUST
  be visually and structurally distinguishable from observed geometry in every surface.
- **REQ-R6-40** — Public coordinate precision MUST be governed by a per-asset `sensitivity_tier` applied at the view
  layer, using truncation (tier 1), H3 binning (tier 2) or suppression (tier 3). Full precision MUST be retained in
  canonical storage under RLS. Random jitter MUST NOT be used unless the radius is published and the offset is
  deterministic per asset.
- **REQ-R6-41** — The tier transform MUST be applied before spatial aggregation, and the assigned tier MUST itself be
  an attributed, reviewable claim.
- **REQ-R6-42** — The public map MUST be served as static PMTiles v3 generated by tippecanoe from the resolution
  projection; a dynamic tile server MUST NOT be a hard dependency of the public map.

**Access control**

- **REQ-R6-43** — Sensitivity tiers MUST be enforced by PostgreSQL restrictive RLS policies; the public API role MUST
  NOT hold `BYPASSRLS`; and export/dump roles MUST run with `row_security = off` so that a would-be-filtered export
  fails loudly instead of silently publishing an incomplete dataset.

**Schema and vocabulary**

- **REQ-R6-44** — The ontology MUST be authored in LinkML and MUST generate JSON Schema, OWL/SHACL, Python
  dataclasses/Pydantic, and documentation. CI MUST fail if committed generated artifacts differ from a fresh
  generation.
- **REQ-R6-45** — Physical schema migrations MUST be managed with sqitch, with `deploy`, `revert` and `verify` scripts
  for every change; migrations touching `claim` MUST be additive.
- **REQ-R6-46** — Controlled vocabularies MUST be published as versioned SKOS concept schemes with stable per-version
  IRIs, archived in the evidence store.
- **REQ-R6-47** — Vocabulary terms MUST be immutable once published; corrections MUST deprecate and supersede, never
  redefine.
- **REQ-R6-48** — Vocabulary changes MUST be accompanied by crosswalk rows using SKOS mapping relations and an
  explicit `lossy` flag; queries traversing a lossy crosswalk MUST propagate that flag into result metadata.
- **REQ-R6-49** — Historical claims MUST NOT be rewritten to a newer vocabulary. Bulk re-classification, if warranted,
  MUST be performed as new claims with `extraction_method = 'vocabulary_migration'` and `revises_claim` links.
- **REQ-R6-50** — SIG entities MUST carry outward-linkable identifiers where they exist (Wikidata Q-ids, ORI codes,
  GEOIDs) as claims with provenance, to satisfy §18/§20 Q37 federation.
