<!--
SPDX-License-Identifier: Apache-2.0
Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-->
# `db/` — the physical claim spine

This package owns the **physical schema** of the canonical store (PostgreSQL 18 +
PostGIS, ADR-001): the L0–L3 claim/evidence/resolution spine of §16, the domain
entity tables of Appendix C, append-only enforcement, the resolution non-overlap
exclusion constraint, and the sensitivity-tier row-level security. It was
established by ticket **P02.1**.

## Migrations are sqitch (SIG-STORE-041)

Physical migrations are managed with [sqitch](https://sqitch.org). Every change
ships a `deploy/`, `revert/`, and `verify/` script and is listed, in dependency
order, in `sqitch.plan`. The schema is **never hand-edited in place**: changes
after P02.1 are new sqitch changes (SIG-STORE-042 — dropping/retyping a `claim`
column requires an ADR and a migration claim-set instead).

```
db/
  sqitch.conf        engine = pg
  sqitch.plan        the ordered change list
  deploy/            forward migrations (CREATE …)
  revert/            reverse migrations (DROP …)
  verify/            post-deploy assertions (object exists / constraint present)
```

## Applying the schema

Deploy against a running Postgres with the sqitch CLI (or its Docker image):

```bash
# with a local sqitch binary:
cd db && sqitch deploy db:pg://user:pw@host:5432/sig

# or with the official image (no local Perl needed; digest-pinned, ADR-196):
docker run --rm -e PGPASSWORD=pw -v "$PWD/db":/repo -w /repo \
  sqitch/sqitch@sha256:f247ab0e0b66e9c2d09a400864f7314358893f5cf209cddcc4f213f7d5bfe4d3 \
  deploy db:pg://user@host:5432/sig
```

## Rebuilding the projections (SIG-STORE-004/005, §15.4)

Every projection is derived state: no projection is the sole home of a fact, so
dropping every projection costs compute, never information. The canonical store
is L0–L2 (evidence, claims, identities) plus the canonical run/decision/rights
records; everything else is rebuilt by re-running its documented command over
the unchanged spine. `tests/db/test_projection_rebuild.py` is the CI
rebuild-and-verify (SIG-STORE-004): over a seeded spine it runs each command,
snapshots, drops **all** derived rows, re-runs, and asserts canonical equality
(minted surrogate keys and `clock_timestamp()` stamps excluded, volatile
foreign keys dereferenced); `tests/db/test_layer_direction.py` proves the
drop-and-rebuild posture is also a *privilege* posture (each layer's writer
reaches only its own layer).

**Postgres materialized projections** — `DELETE`-and-rebuild (never
`TRUNCATE … CASCADE`, so a canonical table that references a derived row —
e.g. `review_decision.item_id` — can never be silently emptied). Drop in
child-first order, then re-run the commands in pipeline order:

```bash
DSN=postgresql://…/sig
uv run sig-reconcile materialize                       --dsn "$DSN" --role sig_materialize   # resolution
uv run sig-reconcile materialize-edges                 --dsn "$DSN" --role sig_materialize   # relationship
uv run sig-reconcile materialize-role-edges            --dsn "$DSN" --role sig_materialize   # entity_role
uv run sig-reconcile materialize-contradictions        --dsn "$DSN" --role sig_materialize   # contradiction
uv run sig-inference materialize-coverage              --dsn "$DSN" --role sig_materialize   # coverage_record
uv run sig-inference materialize-accountability-links  --dsn "$DSN" --role sig_materialize   # inference.derived_fact (L4)
uv run sig-resolution camera-sites                     --dsn "$DSN" --role sig_materialize   # camera_site_* + review_item
uv run sig-resolution org-cascade                      --dsn "$DSN" --role sig_materialize   # organization_* + review_item
uv run sig-tasks detect                                --dsn "$DSN" --role sig_materialize   # research_task
```

Derived rows pinned by a canonical human record (a `review_item` under a
`review_decision`/`review_campaign_item`, a claimed `research_task`, a
`camera_site_demotion` consumed by a later run) are history and are not
dropped — the CI test seeds the all-undecided case, where a full drop is a
legal instance of that rule. `claim_lineage`/`source_lineage` are
emitter-written lineage records, not projections; `claim_lineage` is
re-materialized by the declared-lineage leg (`sig-db lineage-rematerialize`),
`source_lineage` by the source-declarations mirror.

**File/artifact projections** (all read-only over the spine — the export path
never writes back):

| §15.4 projection | store | rebuild command |
|---|---|---|
| resolution read models | the PG tables above | the nine commands above |
| analytics (DuckDB + Hive-partitioned Parquet) | §18 store | `db.analytics.write_partitions` (the scheduled aggregate writer); schema gate `uv run sig-db analytics assert-schema` |
| RDF / JSON-LD + PROV-O lineage | export bundle (`catalog.jsonld`, `provenance.jsonld`) | `uv run sig-exports build --from-spine --dsn "$DSN" -o <dir>` |
| map tiles (PMTiles v3) | export bundle | `uv run sig-exports tiles …`; verified by `sig-exports tiles verify` (sig.map-tiles/2) |
| search index (PG FTS / FTS5) | spine index + per-compartment FTS5 artifacts | `uv run sig-exports build --from-spine --dsn "$DSN" -o <dir>` (FTS5 artifacts; immutable cut via `sig-exports release …`) |
| graph query / edge list | export bundle | `uv run sig-exports build --from-spine --dsn "$DSN" -o <dir>` (edge artifacts) |
| Datasette / SQLite bundle | export bundle | `uv run sig-exports build --from-spine --dsn "$DSN" -o <dir>` (SQLite artifacts) |

For the artifact projections "rebuild" *is* re-running the export command:
their determinism is covered by canonical serialization and the export-path
tests (`tests/db/test_spine_export_over_seeded_spine.py`, `tests/exports/`).

## Testing

The claim-spine behaviour (append-only — with the single recorded exception of
`sig_purge_claims`, the operator-only purge function of ADR-189/WV-11 added by
the `operator_purge` sqitch change (P37.71): executable only by the
`sig_purge_operator` role, scoped to SIG-GOV-008 material, leaving a
`purge_tombstone` + `purge_audit` per use; corrections, the exclusion
constraint,
RLS, and the schema-integrity guards) is verified against a **real** PG18+PostGIS
instance — never a mock. The tests (`tests/db/`) use `testcontainers` to launch
the database and apply this sqitch plan to it, so all you need locally is a
running Docker daemon:

```bash
make test-db     # SIG_REQUIRE_DB_TESTS=1; fails loudly if Docker is unreachable
```

Without `SIG_REQUIRE_DB_TESTS`, the DB tests skip when Docker is unavailable so
`make test` still runs the rest of the suite; CI sets the flag so they are
blocking (SIG-STORE-024).
