# ADR-044: The usage-analytics boundary — DuckDB/Parquet substrate in `db`, the UUID+period join, partition-as-evidence, and rationale-driven small-cell suppression

- **Status:** Accepted
- **Date:** 2026-09-01
- **Phase:** P12.1
- **Requirement ids:** SIG-ONTO-037; SIG-STORE-025, SIG-STORE-026, SIG-STORE-027, SIG-STORE-028, SIG-STORE-029, SIG-STORE-030, SIG-STORE-031, SIG-STORE-032, SIG-STORE-033; realizes the §11.16 `UsageAggregate` predicate surface (`searching_org`/`source_org`, `period`, `count`, `search_scope`, `reason_category`/`reason_raw_value`, `audit_source_type`, `coverage_period`). Builds on ADR-010 (the boundary decision) and closes ADR-043's RISK-P11-13 handoff.
- **Spec:** docs/2_canonical_design_spec.md §11.16 (`UsageAggregate`); §18.1 (the bright line); §18.2 (the substrate); §18.3 (the join and partition-as-evidence); §18.4 (disclosure control)

## Context

ADR-010 decided the *shape* of the analytics boundary (analytics over a DuckDB/Parquet projection
built from aggregates only). P11.2 (ADR-043) landed the `UsageAggregate` entity and the ingestion
bright-line gate but explicitly deferred the substrate to P12.1 (RISK-P11-13). This ADR records the
decisions taken building it.

The analytics boundary is a **privacy** line, not only a performance one (§18): the audit exports it
projects are per-search logs, so the boundary is exactly where "no searchable database of people's
movements" (Part VIII) is enforced at rest and at query time. Four decisions were forced:

1. **Where the substrate lives.** The `UsageAggregate` store is a second storage engine alongside
   the Postgres claim spine, so it belongs in `db/`, not in a connector or a new package.
2. **How the bright line becomes a schema property** for a *columnar* store, not only for Postgres.
3. **How partitions join to the graph** without reintroducing name-based entity resolution.
4. **How small-cell suppression encodes the institutional-vs-individual distinction** that
   SIG-STORE-032 warns is load-bearing and easy to get backwards.

## Decision

**The substrate is `db.analytics`, over DuckDB-written Hive-partitioned Parquet (SIG-STORE-027).**
High-volume aggregates live outside PostgreSQL; no columnar Postgres extension is adopted as
canonical. DuckDB is the single engine for both the partitioned `COPY` write and the read/join —
no `pyarrow`/`fastparquet` is added (DuckDB writes Parquet natively). Partitions are keyed
`audit_source_type=…/period=…/` so the four non-interchangeable audit types (§23.7) never share a
partition and the month is the coarsest pruning key (§18.4). `duckdb>=1.0.0` becomes a direct
dependency of `sig-db` (it was already resolved transitively via `sig-resolution`/Splink).

**The bright line is a columnar schema property (SIG-STORE-025/026).** `ANALYTICS_COLUMNS` is the
whole published schema; it carries `searching_org_id`/`source_org_id` (UUIDs) + `period` + the
aggregate facts + lineage, and **no plate-capable column and no name column at all**.
`assert_analytics_schema` / `assert_no_name_or_plate_column` are the token-based guards (mirroring
`tests/db/test_schema_integrity.py`'s Postgres-side test) and run in `AnalyticsRow.__post_init__`,
in `write_partitions` before any bytes are written, and as the `sig-db analytics assert-schema`
data-quality gate. This is the analytics-store half of the AC1 "no per-search or per-plate row
anywhere" pair (the canonical-store half is the P02.1 Postgres test).

**The join is UUID + period, enforced structurally (SIG-STORE-028).** There is *no name column to
join on*, and `assert_join_keys` refuses any join key outside `{searching_org_id, source_org_id,
period}` — a name key is a hard `JoinKeyError`, so `build_graph_join_sql` cannot even construct a
name-based query. Every row carries `ingest_run_id` and `agg_ruleset_version` for lineage. A name
join would reintroduce, invisibly and in a layer nobody is watching, exactly the entity-resolution
failure P6 exists to prevent.

**Partitions are evidence; summaries are the only claims (SIG-STORE-029).** Each written partition
is content-addressed with the interop multihash (`evidence.digest.multihash`, SIG-EVID-002) into a
`PartitionArtifact` and registered as an `evidence_artifact` row. A claim crosses the boundary only
as a *summary statement* about a partition ("agency X ran N searches in the month to …") that
**cites the partition digest** (`cites_partition_digest`) as its evidence — keeping the §10.1
provenance chain unbroken. `sig-db` therefore takes a direct dependency on `sig-evidence`; because
`evidence` is a leaf package (no `sig-*` dependencies), this adds no import cycle.

**Small-cell suppression is rationale-driven and never lossy-by-zero (SIG-STORE-030/031/032/033).**
`db.suppression` decides publish/suppress per cell by its §18.4 rationale, not by size alone:
`institutional_conduct` publishes even when small (accountability information — suppressing "three
searches by an agency" would defeat the project's purpose); `protects_individual` suppresses when
small; `contractual` suppresses and must cite a rights record; and the `ambiguous` case — the two
cannot be separated — **defaults to suppress and raises a review task**, per SIG-STORE-032. A
suppressed cell publishes `count = None` with `suppressed_flag` and the `k_threshold` that applied,
**never zero**. **Complementary (secondary) suppression** removes a second cell when a lone
suppressed cell in a published margin would otherwise be recoverable by subtraction; it prefers a
non-institutional cell and, when forced onto an institutional one, raises a review task. The finest
published granularity is one month (`assert_month_granularity`). `k = 5` is SIG's own documented
policy (SIG-STORE-033, R6-F46 — no primary US federal source verified a threshold); a partner
licence's stricter (larger) `k` wins via `effective_k_threshold`.

## Consequences

- The connector-side `usage_aggregate` rows from `connectors.audit_structural` are the boundary's
  input; `project_aggregate` maps a row plus its **resolved** org UUIDs and its suppression verdict
  into an `AnalyticsRow`, deliberately dropping any name field so it cannot cross the boundary.
- The substrate runs entirely in-process (DuckDB + a directory) and is fully tested without
  Postgres or a network — the boundary is self-contained. The Postgres-side "no plate column"
  guard (P02.1) still covers the canonical store; the two together discharge AC1.
- `db` gains two direct dependencies (`duckdb`, `sig-evidence`). `pylock.toml` is unchanged (both
  were already in the resolved set); only `uv.lock`'s dependency graph updates.
- Actual **resolution** of org names → `sig_entity_id` UUIDs is the caller's job (P6 / the
  connector link stage); `db.analytics` never touches the resolver, keeping the layering clean.

## Alternatives considered

- **A columnar Postgres extension** (e.g. a column-store) as the canonical aggregate store —
  rejected by SIG-STORE-027; it tempts raw-row access and couples analytics scale to the OLTP store.
- **Adding `pyarrow`/`fastparquet`** for the Parquet write — unnecessary; DuckDB writes
  Hive-partitioned Parquet natively, so the dependency surface stays smaller.
- **Suppressing purely by count threshold** — rejected: it would suppress institutional
  accountability small counts (SIG-STORE-032) and publish nothing about small agencies, defeating
  the project's purpose. The rationale must drive the decision.
- **Joining partitions to the graph by org name** for convenience — rejected by SIG-STORE-028; it
  reopens the P6 entity-resolution hazard in an unwatched layer.

## Revisit trigger

Revisit if: interactive aggregate latency ever demands ClickHouse (the documented §18.2 escape
hatch, R6-F45); a partner licence requires a suppression model richer than `(rationale, k)` (e.g.
per-cell differential privacy); the `UsageAggregate` predicate surface (§11.16) changes; the
resolver contract for supplying org UUIDs to `project_aggregate` changes; or `agg_ruleset_version`
must bump because the projection rules change (a versioned migration, §20).
