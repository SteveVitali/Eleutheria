# ADR-108 — Read-API connection pool and the bounded `/v1/search` contract

- **Status:** Accepted
- **Phase / ticket:** Phase 31 / P31.1 (`docs/tickets/P31.1__api-db-resilience-and-bounded-search.md`) — Round 9 `HARDEN.1`; the ticket this ADR is owned by and lands with (the design's placeholder `ADR-R9-API`).
- **Date:** 2026-09-24
- **Related:** §37 (the read API; SIG-API-001 hand-written versioned contract, SIG-API-012 prohibited surfaces), ADR-059 (`PgReadStore` over the spine), ADR-081 (Cloud SQL + Cloud Run hosting), **ADR-107** (Cloud SQL `db-custom-1-3840`, `max_connections = 100`; §5 recorded the missing reconnect), ADR-103 (heavy DB work runs next to the DB); deferrals **D-P30.4-1** (sig-api does not reconnect after a DB restart) and **D-P30.4-2** (`/v1/search` unbounded); backlog home **BL-057**.

## Context

Two failures of the public read API were observed live during P30.4 (ADR-107 §5, `runs/P30.4.md`):

1. **No reconnect.** `PgReadStore` opened ONE `psycopg` connection per process in `__init__` and used it for
   every request. When the `sig-pg` tier change restarted Cloud SQL, every DB-backed endpoint returned 500
   (`psycopg.OperationalError: server closed the connection unexpectedly`) until the Cloud Run instances were
   recycled by hand. Any Cloud SQL maintenance window would do the same, with nobody touching the system.
2. **Unbounded search.** `search` ran `entity_identifier.value ILIKE '%q%'` with no LIMIT, then two more queries
   per hit (label, sources). The hosted spine has 247,065 identifiers; `q=flock` matches **134,346** entities and
   `q=camera` 230,334, so one request issued hundreds of thousands of round trips and ran past the 300 s Cloud Run
   request timeout. The only index on `entity_identifier` is its `(entity_id, scheme, value)` primary key.

## Decision

1. **A small, self-healing connection pool.** `PgReadStore` reads through a `psycopg_pool.ConnectionPool`
   (new runtime dependency `psycopg-pool`, LGPL-3.0 like `psycopg`). Every new connection re-applies
   `SET ROLE <read role>` (`configure`), so the RLS ceiling survives reconnects. Each public read method checks
   out one connection for its duration (`_pooled`, re-entrant for nested reads). A read whose connection **died**
   (the connection is `closed`/`broken`: a Cloud SQL restart, maintenance, `pg_terminate_backend`) calls
   `ConnectionPool.check()` — every idle connection tested at once, the dead ones replaced — and is **retried
   once** on a fresh connection. Nothing else is retried: not a statement timeout, not a pool timeout, not an
   error on a live connection (out of memory, a lock error), so a heavy read never runs twice. Every connection
   carries `application_name = sig-api`, so operators can find (and, for a drill, terminate) exactly the API's
   backends in `pg_stat_activity`. The pool opens in the background: a DB that is down at startup yields 503s
   until it returns, never a crash loop.

   **Not the pool's own checkout check (`check=`).** It was the first design and was rolled live
   (`sig-api-00005-nem`). The approved hosted drill terminated all five pooled backends at once, and the next
   request got a **503 after the full 10 s pool timeout** (every later request was 200): `psycopg_pool` walks the
   dead idle connections one at a time with a 1 s, 2 s, 4 s backoff between failed checks. A database restart
   kills every idle connection together, so that is exactly the case that matters. Purge-then-retry serves the
   same case in well under a second (real-PG regression test with five killed backends, which fails under the
   `check=` design).
2. **Pool sizing against the connection budget.** Defaults: `min 1`, `max 5`, checkout timeout 10 s, connect
   timeout 5 s. Per instance that is 5 pooled connections plus at most one dedicated compute connection (the
   annotation/shaping pass, opened and closed per compute). It is deliberately not pooled: the compute runs under
   the annotation lock for seconds and must never compete with request reads for a pool slot. The annotation and
   shaping surfaces also take that lock BEFORE checking out a pooled connection, so requests queued on the lock
   hold no connection and cannot drain the pool (a real-PG test stalls the compute and keeps plain reads fast).
   With Cloud Run `max-instances = 2`: **2 × (5 + 1) = 12** of `max_connections = 100` (3 reserved for superusers,
   ~4 held by `cloudsqladmin`), leaving ~80 for the ingest, materialize, export and probe jobs and operator
   sessions. During a revision roll old and new instances briefly overlap (4 × 6 = 24), still well inside the
   budget. Measured after the roll: 17 backends in total, 5 of them `sig-api`. The invariant for any change is
   `(POOL_MAX + 1) × max-instances` well inside the budget; the knobs are per-deploy env (`SIG_API_POOL_MIN`,
   `SIG_API_POOL_MAX`, `SIG_API_POOL_TIMEOUT_S`, `SIG_API_SEARCH_TIMEOUT_MS`), never a code change.
3. **A store that cannot answer is a 503, not a 500.** Pool exhaustion, a DB that stays unreachable after the
   retry, and a connection lost twice raise `StoreUnavailable`; the app maps it to **503** with `Retry-After: 5`.
4. **`GET /health`** (not under `/v1`, not an as-of envelope, `Cache-Control: no-store`): 200 when a pooled
   connection answers `SELECT 1` within 3 s, else 503; the body carries the backend and the pool counters
   (`pool_min/max/size/available`, `requests_waiting`) so pool usage is observable without a heavy query. It uses
   the request pool, so a saturated instance can also answer 503; it must therefore **never** be wired as a Cloud
   Run liveness probe (that would restart healthy-but-busy instances). The path is `/health`, **not `/healthz`**: Cloud Run reserves some paths ending in `z`, and `/healthz` never reaches the
   container (verified live: the Google front end answers `/healthz` with its own 404 page). It is a service
   readiness signal, not a device-liveness signal (SIG-API-012). `probe-hosted` gains a `sig-api-health` target.
5. **The bounded search contract** (additive to the §37.3 `/search` response):
   - a query must contain a run of **3 letters or digits** (the trigram length: `pg_trgm` extracts trigrams per
     alphanumeric word, so `ab`, `a-b` or `a b` yields none and would scan the whole index) → otherwise **422**;
     an empty query stays a 200 with no results (unchanged). Exact short identifiers stay reachable through
     `/id/{type}/{id}`;
   - page size `limit`: default **50**, max **200** (`limit` outside 1…200 is a 422);
   - **keyset pagination**: results are ordered by `entity_id`; the response adds `limit` and `next_cursor` (the last
     `entity_id` served, `null` when complete); the next page is `?cursor=<next_cursor>`; a cursor the store could
     not have issued is a 422. Keyset, not offset: a deep page costs the same as the first. No total count (counting
     134k matches is the unbounded work this removes);
   - the query text matches literally (`%`, `_` and `\` are escaped; they were wildcards before);
   - labels and sources are fetched **set-based** for the page: a constant four statements per page (statement
     timeout, match, labels, sources) whatever the page size;
   - a **5 s statement timeout per statement** (`SIG_API_SEARCH_TIMEOUT_MS`), transaction-local
     (`set_config(..., true)`), so it never leaks onto the pooled connection. The match is the only statement whose
     cost depends on the spine; labels and sources are primary-key lookups over at most `limit` ids.
     (`transaction_timeout` was rejected: exceeding it terminates the session, i.e. kills a pooled connection.) A
     search that exceeds the timeout is a 503 ("use a more specific query") with no `Retry-After`: repeating the
     same query will not help;
   - `API_VERSION` stays `1.0.0`: the response shape changes additively only. The two narrowings (a 1–2 character
     or punctuation-only query is now a 422; `%`/`_` match literally) are input bounds the ticket requires, not a
     shape change, and a client that sent such a query previously triggered the unbounded scan being removed.
6. **The index.** A new sqitch change `entity_identifier_value_trgm` creates `pg_trgm` (a trusted contrib extension;
   listed in `pg_available_extensions` on `sig-pg`) and a GIN trigram index on `entity_identifier.value`,
   **`CREATE INDEX CONCURRENTLY`** in a **non-transactional** change, so the build never blocks ingest `INSERT`s.
   The deploy itself fails on an `INVALID` leftover of an interrupted build (`IF NOT EXISTS` would otherwise skip
   it), and the verify checks `indisvalid`. Hosted (2026-09-24): built in ~14 s, **17 MB** (the database is
   4.38 GB of the 15 GB disk). The match statement is an `IN (subquery)` that lets the planner choose between the
   trigram bitmap scan and an `entity_id`-ordered walk that stops after `LIMIT` rows. Hosted `EXPLAIN ANALYZE`:
   `okc` (3 matches) and a no-match term use `entity_identifier_value_trgm_idx` (0.5 ms, 0.1 ms); `flock` (134k
   matches) walks `entity_pkey` and stops at 51 rows (190 ms page 1, 7 ms on a late cursor); `camera` 201 rows in
   28 ms.

## Consequences

- A Cloud SQL restart (maintenance, tier change, failover) no longer needs a manual `sig-api` recycle: the first
  request after the database returns gets a fresh connection. ADR-107's "after any `sig-pg` restart, redeploy
  sig-api on its digest" runbook step becomes a fallback, not a requirement. Hosted evidence so far: the approved
  drill on the first image recovered with no redeploy (one 503 after 10 s, then 200s); the fast path of the
  served image is proven on real PG only, and its hosted proof waits for the next restart or a second approved
  drill (D-P30.4-1 stays PARTIAL until then).
- While the database is down, DB-backed endpoints answer 503 (bounded by the 10 s checkout timeout) instead of 500.
- Measured live after the roll (`sig-api-00008-qir`): `/v1/search?q=flock` median 390 ms (5 pages of 50, ordered,
  no duplicates), `q=camera&limit=200` median 368 ms, `q=okc` 236 ms; 80 mixed concurrent requests (8 workers)
  all 200, with `/health` showing the pool at most 5 connections and at most 2 requests waiting.
- `/v1/contradiction` and `/v1/task` are unchanged at ~10 s each (the P25.10 spine watermark counts every claim
  on every request, under the annotation lock), and concurrent calls queue behind one another; that cost
  predates this ADR and is recorded as D-P31.1-1.
- `/v1/search` is bounded in rows, statements and time. A client that relied on getting every match in one
  response now pages with `next_cursor`; the old fields are unchanged, so the change is additive.
- A search with no run of 3 letters or digits is refused; exact short identifiers are still reachable through
  `/id/{type}/{id}`.
- New ingest rows go into the GIN index's pending list until autovacuum merges them; `gin_pending_list_limit`
  (4 MB) bounds the extra scan cost.
- `psycopg-pool` joins the runtime dependency set (licence gate: LGPL, allowed).

## Alternatives considered

- **A reconnect-on-`OperationalError` wrapper around the single connection.** Smaller, but it keeps one connection
  per process serialising every request (psycopg connections are locked per statement), and it still serves a dead
  connection once per restart. Rejected for the pool, which the ticket names first.
- **The pool's checkout check (`check=ConnectionPool.check_connection`).** Rolled live first and measured: a 503
  after 10 s on the first request once every pooled connection had died (Decision 1). Replaced by
  purge-then-retry.
- **Offset pagination.** Simpler URLs, but deep pages cost O(offset) and shift under concurrent inserts. Rejected.
- **A btree `text_pattern_ops` index.** Serves only anchored `LIKE 'q%'`; search is a substring match. Rejected.
- **Full-text search (`tsvector`).** Identifiers such as `traffic_camera:camreg_jmh_us:jmh_us_mpd_flock:1` are not
  natural-language text; the tokenizer would split them unpredictably. Rejected for trigram substring matching.
- **A total-count field.** Counting a broad term is the unbounded work being removed. Rejected; `next_cursor` says
  whether more exists.
- **`/healthz`.** Reserved by Cloud Run (see Decision 4). Rejected for `/health`.

## Revisit trigger

Revisit if any of these happens:

- Cloud Run `max-instances` or the Cloud SQL tier changes, so `(POOL_MAX + 1) × max-instances` must be re-checked
  against `max_connections`;
- `/health` or `probe-hosted` records `requests_waiting > 0` or a pool-timeout 503 under normal traffic;
- `/v1/search` p95 exceeds ~2 s, or the statement timeout fires on real queries;
- the search surface needs ranking, fuzzy matching, or search over claim values rather than identifiers;
- a caching layer, CDN or rate limiting is put in front of the API (out of scope for P31.1).
