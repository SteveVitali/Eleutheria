# ADR-059: Capstone spine wiring — PgClaimSink, PgReadStore, and the compute-on-read seam

- **Status:** Accepted
- **Date:** 2026-09-09
- **Phase:** P19.4
- **Requirement ids:** SIG-API-001, SIG-STORE-024, SIG-INGEST-021, SIG-STORE-011, SIG-STORE-012, SIG-TIME-008, SIG-RECON-006

## Context

The P19.3 composed run drove the whole build as one process graph for the first time and proved that
three runtime seams had never been wired, recording each as an `xfail` keyed to a `LEDGER_DEFERRALS`
id: connector output had never been written to the PostgreSQL claim spine (`LD-F06b`), the public read
API had only ever been served over the in-memory demo store (`LD-F06`), and entity resolution / the
review queue had never round-tripped through PostgreSQL (`LD-F04`). Until these are crossed, "the
system" is a set of value objects in memory, not one database.

Wiring them raises three design questions this ADR settles: (1) **where the connector→PG write path
lives** and how it stays append-only and idempotent given that a connector replay is byte-reproducible
only *modulo* the generated id and transaction time; (2) **how the API reads graph annotations
(contradictions, coverage, tasks)** that are not yet materialised in the `graph_annotations` tables;
and (3) how both respect the append-only, RLS, and publication invariants.

## Decision

1. **`PgClaimSink` lives in `db/` (`db/src/db/claim_sink.py`); `connectors/` selects it through a
   factory.** The physical store and its psycopg driver belong to the `db` package (ADR-001); the
   connector framework must not import psycopg directly. `connectors/src/connectors/sinks.py`
   (`make_claim_sink`) is the seam: `--sink memory` stays the unchanged default and pulls in no driver,
   `--sink pg --dsn …` imports `db.claim_sink.PgClaimSink` behind that branch. The sink writes the full
   L0→L2→L1 path append-only — INSERTs only, no in-place mutation or row removal (a grep test proves it,
   SIG-STORE-011/012) — resolving each claim's evidence to a real `evidence_capture` row and letting the
   database set `recorded_at` (the `sys_period` lower bound). Non-claim connector records (unmapped
   categories, vocabulary events) are skipped, not forced into L1.

2. **Idempotency is a `content_digest` on the claim** (new additive sqitch change
   `claim_content_digest`: a nullable column + a partial `UNIQUE` index + an `append_only_guard` entry).
   The digest is the sha256 over the claim's reproducible payload — every field *except* the two the
   connector reproducibility fingerprint excludes (`claim_id`, `sys_period`; SIG-INGEST-003). The sink
   `INSERT … ON CONFLICT (content_digest) DO NOTHING`, so replaying an identical run inserts each claim
   exactly once (N>0 the first time, 0 the second). A correction is a genuinely different payload → a
   different digest → a new append-only row, never an edit. The column is nullable so every pre-existing
   claim is unaffected and excluded from the partial index (back-compat, SIG-STORE-042).

3. **`PgReadStore` (`api/src/api/store_pg.py`) implements all 16 `ReadStore` methods over PG;
   `create_app(store)` is unchanged.** `sig-api serve --dsn …` selects it. It applies **publication at
   the store boundary** (Part VIII §0.7): reads are filtered to the public sensitivity tier and
   sensitive coordinates are never returned raw (jurisdiction-only). Row-level security stays **enabled**
   — the store never sets `row_security = off` or asks for `BYPASSRLS`; an optional read role
   (`sig_read_public`) makes RLS enforce the same ceiling as defence-in-depth. As-of reads use the
   shared `db.temporal.AsOf` belief predicate (`sys_period @> belief`); the resolver applies world-time,
   so a belief-pinned read reproduces a past answer (SIG-TIME-008). The `ReadStore` Protocol is **not**
   changed.

4. **The graph-annotation surfaces compute-on-read.** `contradictions` / `coverage_for` / `tasks` /
   `task` read the persisted `graph_annotations` rows **if any exist**, else `PgReadStore._compute_on_read()`
   derives them by running `RESOLVE` over each `(subject, predicate)` group of public claims and
   surfacing the emitted contradictions and research tasks (SIG-RECON-057). Contradictions stay
   **visible** (§3.1): a within-predicate disagreement is emitted `UNRESOLVED` with both values retained,
   never collapsed. This seam is deliberately the thing P21.2 replaces when it materialises annotations.

5. **`python -m reconcile resolve --dsn … [--jurisdiction …]`** reads the L1 claims for a jurisdiction
   out of the spine and prints the resolution envelope (contradictions visible) — the read-only CLI
   anchor P21.4's `run_okc.sh` needs. Nothing is persisted (materialising the resolution is P21.2).

6. **ER over PostgreSQL (deliverable 3 / `LD-F04`) is deferred to P19.5** per this ticket's own size
   guard: `PgClaimSink` (1), `PgReadStore` (2), and the `reconcile resolve --dsn` CLI (4) shipped fully
   with tests; the probabilistic-matcher-over-PG, the PG `ReviewQueue` backend + `review_decision`
   table, and `sig-resolution match/review decide --dsn` move to P19.5. `tests/e2e` `LD-F04` therefore
   stays a visible LD-tagged `xfail` (S4), not a fabricated pass; `tests/resolution/test_pg_backend.py`
   lands with P19.5.

## Consequences

- The composed run's `LD-F06b` (S3) and `LD-F06` (S6) `xfail`s flip to passes; `tests/e2e` drops to two
  `xfail`s (`LD-F04` → P19.5, `LD-V08` → P21.4). New tests: `tests/db/test_claim_sink.py`,
  `tests/api/test_store_pg.py`.
- The append-only guard list gains `content_digest`; the `tests/db/test_append_only.py` schema check
  (`guarded == live − {sys_period}`) still holds because the migration inserts the guard row.
- Compute-on-read can diverge from persisted annotations once P21.2 lands (see RISK-P19-07); a PG
  connection is opened per store instance rather than pooled (RISK-P19-08).

## Alternatives considered

- **Put `PgClaimSink` in `connectors/` and import psycopg there.** Rejected: it would give the connector
  package a driver dependency and duplicate the store's knowledge of the schema; the factory keeps the
  driver in `db` (ADR-001) with no import cycle (`connectors` already depends on `sig-db`).
- **Query-before-insert (or a `raw_context` marker) for idempotency instead of a unique index.**
  Rejected: a partial unique index is race-safe and lets a single `ON CONFLICT` do the work, and it
  reuses the spine's own uniqueness mechanism rather than inventing a dedup query.
- **Persist annotations now instead of compute-on-read.** Rejected: materialising `contradiction` /
  `coverage_record` / `research_task` rows from the resolver is P21.2's contract; computing them on read
  wires the API to the live claims immediately without pre-empting that design.

## Revisit trigger

Revisit when **P21.2 materialises the graph annotations**: at that point `_compute_on_read()` must be
replaced by a read of the persisted rows, and the RISK-P19-07 `--recompute` diagnostic + rebuild-equality
test must prove the persisted rows equal the computed ones. Also revisit if a claim's reproducible
payload ever needs a field the current `content_digest` excludes (or must exclude one it includes), or
if the per-request PG connection (RISK-P19-08) becomes a measured bottleneck and a pool is introduced.
