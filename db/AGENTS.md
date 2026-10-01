# AGENTS.md — `db/` (the physical claim spine)

## Purpose

Owns the **physical schema** of the canonical store: **PostgreSQL 18 + PostGIS** (ADR-001) — the
L0–L3 claim/evidence/resolution spine (§16), Appendix C entity tables, append-only enforcement, the
resolution non-overlap exclusion constraint, and sensitivity-tier row-level security. Established by
ticket **P02.1**. Nearest-file-wins: this file adds to the root `AGENTS.md`; see `db/README.md` for
the full narrative.

## Key Files

| File | Lines | Purpose |
|---|---|---|
| `db/src/db/claim_sink.py` | ~920 | `PgClaimSink` — insert-only, chunk-batched writes to the claim spine (ADR-110) |
| `db/src/db/identity_guard.py` | ~130 | `resolve_identities` — one entity per identity-bearing `(scheme, value)` via `entity_identity_key` (ADR-110) |
| `db/src/db/sink_bench.py` | ~240 | `sig-db sink-bench` — claims/min + round trips per claim for a sink pass |
| `db/src/db/analytics.py` | ~n/a | DuckDB analytics commands over parquet (a separate engine) |
| `db/sqitch.plan` | — | the ordered sqitch migration plan (deploy/revert/verify per change) |

## Build & Test

- **DB tests need Docker.** They run against `postgis/postgis:18-3.6` via testcontainers
  (`tests/db/conftest.py`). Run them with **`make test-db`** (from repo root), which sets
  `SIG_REQUIRE_DB_TESTS=1` so a missing daemon **fails loudly** rather than skipping. `make check`
  does **not** include them.
- CLI: `uv run python -m db --help` (`sig-db`) — includes the DuckDB analytics commands
  (`db/src/db/analytics.py`).

## Code Conventions

- Schema changes are **new** sqitch changes (deploy/revert/verify + a `db/sqitch.plan` entry), never
  in-place edits of a deployed change.
- All spine writes go through `PgClaimSink`; there is no `UPDATE`/`DELETE` path in `db/`.

## Critical Gotchas

1. **Migrations are sqitch (SIG-STORE-041) — the schema is never hand-edited in place.** Every change
   ships `deploy/`, `revert/`, `verify/` scripts and is listed in dependency order in `db/sqitch.plan`.
   Changes after P02.1 are **new** sqitch changes; dropping/retyping a claim column requires an ADR
   and a migration claim-set (SIG-STORE-042), not an in-place edit.
2. **Append-only.** The claim spine is append-only; corrections are new rows, not updates. Don't add
   `UPDATE`/`DELETE` paths against claim tables (`PgClaimSink` is insert-only by design).
3. **Entities for identity-bearing identifiers are minted only through the guard.** Call
   `db.identity_guard.resolve_identities` inside a transaction. Never check `entity_identifier`, then
   insert an entity: two writers race, and the spine cannot delete the duplicate (ADR-110).
   `us.state`-style attribute schemes are not identity keys and are not guarded. A new guarded scheme
   ships with a sqitch backfill of its existing identifiers (ADR-110 (d); `partner_org_identity_key` for
   the P31.5 partner-organisation schemes, ADR-112).
4. **Entity-ref objects come only from a record's `object_ref`** (`record_object_ref`, wired by
   `connectors.sinks.make_claim_sink`). The sink never mints a `person` object (Part VIII); the identity
   decision for partner organisations lives in `resolution.partner_identity`, not in `db`.
5. **Analytics run on DuckDB** (`analytics.py`) over parquet — a separate engine from the PG spine;
   don't conflate the two stores.

## Terminology

- **Claim spine** — the append-only PG18+PostGIS L0–L3 store this package defines.
- **RLS** — PostgreSQL row-level security, applied per sensitivity tier at the view layer.

## Do

- Add schema changes as new sqitch changes with deploy/revert/verify + a `db/sqitch.plan` entry.
- Run `make test-db` (with Docker) after any schema or `PgClaimSink` change.

## Don't

- Don't hand-edit deployed schema or bypass the append-only / RLS constraints.
- Don't write `UPDATE`/`DELETE` against claim tables or conflate the DuckDB analytics store with PG.
