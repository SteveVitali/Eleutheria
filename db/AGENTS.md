# AGENTS.md — `db/` (the physical claim spine)

## Purpose

Owns the **physical schema** of the canonical store: **PostgreSQL 18 + PostGIS** (ADR-001) — the
L0–L3 claim/evidence/resolution spine (§16), Appendix C entity tables, append-only enforcement, the
resolution non-overlap exclusion constraint, and sensitivity-tier row-level security. Established by
ticket **P02.1**. See `db/README.md` for the full narrative.

## Build & Test

- **DB tests need Docker.** They run against `postgis/postgis:18-3.6` via testcontainers
  (`tests/db/conftest.py`). Run them with **`make test-db`** (from repo root), which sets
  `SIG_REQUIRE_DB_TESTS=1` so a missing daemon **fails loudly** rather than skipping. `make check`
  does **not** include them.
- CLI: `uv run python -m db --help` (`sig-db`) — includes the DuckDB analytics commands
  (`db/src/db/analytics.py`).

## Critical gotchas

1. **Migrations are sqitch (SIG-STORE-041) — the schema is never hand-edited in place.** Every change
   ships `deploy/`, `revert/`, `verify/` scripts and is listed in dependency order in `sqitch.plan`.
   Changes after P02.1 are **new** sqitch changes; dropping/retyping a `claim` column requires an ADR
   and a migration claim-set (SIG-STORE-042), not an in-place edit.
2. **Append-only.** The claim spine is append-only; corrections are new rows, not updates. Don't
   write `UPDATE`/`DELETE` paths against claim tables.
3. **Analytics run on DuckDB** (`analytics.py`) over parquet — a separate engine from the PG spine;
   don't conflate the two stores.

## Do / Don't

- **Do** add schema changes as new sqitch changes with deploy/revert/verify + a `sqitch.plan` entry.
- **Don't** hand-edit deployed schema or bypass the append-only / RLS constraints.
