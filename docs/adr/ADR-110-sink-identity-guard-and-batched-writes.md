# ADR-110 — Entity-identity guard, batched claim writes, and the sink's extension points

- **Status:** Accepted
- **Phase / ticket:** Phase 31 / P31.3 (`docs/tickets/P31.3__sink-identity-guard-and-batched-writes.md`) — Round 9 `HARDEN.3`. This is the design's placeholder `ADR-R9-SINK`, and it lands with that ticket.
- **Date:** 2026-09-24
- **Related:** §16 (the append-only claim spine; SIG-STORE-011/012), §14 (identity; SIG-IDENT-020/025/026), ADR-005 (resolution is a stored decision), ADR-059 (`PgClaimSink`, content-digest idempotency), ADR-061 (the PG review queue), ADR-102 (the throughput baseline), ADR-107 (the `db-custom-1-3840` tier, `max_connections=100`), ADR-108 (the P31.1 trigram index and the `CONCURRENTLY` pattern), ADR-109 (one run per execution; chunk rollback hygiene). Deferrals **D-P30.4-3** (ENTITY-RACE-01) and **D-P30.1-1**; backlog home **BL-057**. The owners of the extension points below: P31.4 (ADR-R9-RESUME), P31.5 (ADR-R9-ENTITYREF), P31.7 (ADR-R9-RESIGHT).

## Context

**The race.** `PgClaimSink._entity_for_subject` resolved a connector subject by looking up
`entity_identifier (scheme='sig.connector.subject', value)` and, on a miss, inserting a new `entity` and
its identifier. Nothing made `(scheme, value)` unique. On 2026-09-19 two scheduled executions of
`camreg_camilo_schools` overlapped: the first ran 06:47:14–06:48:06Z and the second started at 06:47:54Z. The
second looked up `camilo_schools_cctv:1` before the first committed, so it minted a second entity. The hosted
read-only check on 2026-09-24 found **3** `(scheme, value)` pairs with two entities each:

- that `sig.connector.subject` pair;
- `us.state OK`;
- `fr.insee 01`.

A plain `UNIQUE (scheme, value)` on `entity_identifier` cannot be built: the historical pairs are still there,
and the spine is append-only, so they are never deleted. Two of the pairs are not races at all. They come from
a second writer, `ops.seed.seed_jurisdiction`, which gives two deliberately near-duplicate seeded agencies the
same jurisdiction identifier. `us.state` and `fr.insee` are **attributes** that many entities legitimately
share, not identity keys.

**The throughput.** The write path was latency-bound: three to five round trips per claim.

- Every claim re-registered the resolution strategy and its predicate, which was uncached.
- Every uncached subject cost a lookup, and `entity_identifier` had no btree on `(scheme, value)`.
- Each claim then cost one INSERT, plus one `claim_evidence` INSERT.

P30.1 measured about 5k claims/min on the hosted spine. A +0 replay was not faster than a land, because every
duplicate still paid the full round trips and the subject lookups. The 2026-10-10 monthly OSM re-ingest (about
1.37M records; P31.4 owns its readiness) is the next big exercise of this path.

## Decision

1. **The guard is a side table, `entity_identity_key`,** added by a new sqitch change.
   - **The key.** There is one row per identity-bearing `(scheme, value)`. Its PRIMARY KEY is the uniqueness
     the database enforces.
   - **The writer** is `db.identity_guard.resolve_identity_batch`, and every guarded writer goes through it.
     It works in five steps:
     1. It reads the keys that already exist. That is one statement, and for a replay it is the only one.
     2. It claims each missing key with `INSERT … ON CONFLICT DO NOTHING`, in one global `(scheme, value)`
        order. A key points at the earliest entity that already carries the identifier (an unguarded writer's
        leftover is **adopted**), or at a fresh `uuidv7()`.
     3. It mints an `entity` only for the keys it won with a fresh id.
     4. It writes the `entity_identifier` row (the read surface).
     5. It reads back the keys it had to claim.
   - **Why it is sound.** Under READ COMMITTED, a second writer's `INSERT` blocks on the first writer's
     uncommitted key. When the first commits, the second's insert does nothing, and its next statement reads
     the winner's key. If the first rolls back, the second inserts.
   - **No orphans.** The key's FK to `entity` is `DEFERRABLE INITIALLY DEFERRED`, so the key is claimed
     *before* its entity exists, inside one transaction. A losing writer therefore never leaves an orphan
     entity.
   - **No deadlocks.** The global key order stops two writers waiting on each other's keys in a cycle.
     Subjects and objects are claimed in the same single pass for the same reason.
   - **Immutable keys.** A trigger refuses UPDATE and DELETE.
   - **Guarded schemes.** `GUARDED_SCHEMES = {sig.connector.subject}`, and the guard refuses any other scheme.
     P31.5 adds its organisation scheme by extending that set and backfilling its identifiers.
     `us.state`-style attribute schemes are deliberately **not** guarded.
2. **The backfill cannot violate the key.** The change keys every existing `sig.connector.subject` value to
   its earliest-created entity (`DISTINCT ON … ORDER BY created_at, entity_id`). Before committing, it asserts
   that every subject identifier is keyed. The later entity of a historical pair keeps its identifier row.
   - **Lock.** `CREATE TABLE … REFERENCES entity` takes SHARE ROW EXCLUSIVE on `entity` until commit, which
     blocks entity INSERTs but not reads. It is deployed with no ingest running. The hosted deploy was
     measured (see Consequences).
3. **A btree on `entity_identifier (scheme, value)`**, in a second, non-transactional change
   (`CREATE INDEX CONCURRENTLY`, as in ADR-108).
   - **The problem it fixes.** The adoption lookup has to find "which entity carries this identifier" for the
     values that are not keyed yet. Measured on 1M identifiers with 10k unkeyed values: 0.7–1.7 s under a
     custom plan, but **19–169 s under a generic plan**. psycopg prepares a statement after its fifth
     execution, so a long land would reach the generic plan.
   - **With the index** both plans take about 0.5–1.2 s.
4. **Every entity writer is guarded.** There are two, and both now resolve through
   `resolve_identity_batch`: `PgClaimSink` (subjects, and objects through the seam below) and
   `ops.seed.seed_jurisdiction` (its agency subjects). The seed's jurisdiction identifiers are attributes, so
   they stay unguarded, and they are attached only to an entity that call minted.
5. **Batched writes.** `_insert_claim` now **stages** each claim. It resolves the per-run prerequisites, which
   are cached and still row-at-a-time because there are only a handful per run: rights, source, the evidence
   chain and the run. At the end of each chunk, `_write_chunk` writes the whole chunk **inside the same chunk
   transaction**:
   - the chunk's new predicates, in one `INSERT … SELECT FROM unnest`, plus the resolution strategy once per
     sink;
   - the subject and object entities, in one guarded pass;
   - the claims, in one `INSERT … SELECT FROM unnest(…) WITH ORDINALITY ORDER BY ord ON CONFLICT
     (content_digest) DO NOTHING RETURNING claim_id, content_digest` per `insert_batch_size` rows (default
     2,000), each followed by one `claim_evidence` INSERT for the rows it inserted.

   Every array travels as `text[]` and is cast in SQL. A float goes `text → float8 → numeric`, the same cast
   psycopg's float8 parameter got, so stored rows are byte-identical.

   The invariants are unchanged:
   - chunked commit and resume (P26.18);
   - content-keyed idempotency across chunk boundaries;
   - a claim lands with all its prerequisite and evidence rows in one transaction;
   - exact counters (a digest repeated inside a chunk is a duplicate, as before);
   - P31.2's rollback hygiene: the id caches are now journaled and undone on rollback, so the cost is
     proportional to the chunk, not the cache;
   - INSERT/SELECT only.

   **Alternatives measured.** psycopg pipeline mode and `executemany` were rejected on shape, not speed. The
   sink's connection contract is `execute` + `transaction` only; `tests/db/test_claim_sink.py` pins it and must
   pass unchanged. Pipeline mode also cannot remove the dependency of the evidence link on the claim id
   `RETURNING` gives back, except as the same multi-row statement. For batch sizes 500, 2,000 and 10,000, the
   write is DB-bound: all three are within run-to-run noise locally, and the round-trip difference (474 / 174 /
   94 per 100k claims) is under 2 s at hosted latency. 2,000 bounds each statement's arrays.
6. **The extension points (the shared decision P31.3 owns).** P31.4, P31.5 and P31.7 extend these; they do
   not redesign them. The behaviour is unchanged until a caller uses them.
   - **(a) Duplicate hook (P31.7).** `on_duplicates(DuplicateBatch)` is called once per chunk that had
     already-present claims, **inside** the chunk transaction. It gets the connection, the run id, and
     `content_digest → claim_id` for the claims that already existed, plus the capture this execution would
     have linked. With no hook, nothing is looked up.
   - **(b) Object seam (P31.5).** `object_resolver(claim) → EntityRef | None`. A returned
     `EntityRef(scheme, value, entity_type)` is resolved through the guard, in the same pass as the subjects,
     and written as `object_entity` with `object_type = 'entity_ref'`. An empty value or a `novalue` claim
     stays a literal. With no resolver every object is a literal, as before.
   - **(c) Per-capture flush (P31.4).** **Each `assert_claims` call is a commit boundary.** Everything handed
     to one call has committed when it returns, in chunks of at most `commit_chunk_size`, all under the
     sink's one run (ADR-109). Calling it once per capture commits per capture.
7. **The historical pairs get recorded decisions, never deletions.**
   - **The tool.** `sig-resolution identity-triage` lists every pair the D-P30.4-3 query returns
     (`GROUP BY scheme, value HAVING count(DISTINCT entity_id) > 1`), with its evidence. `--apply` records the
     committed decision (`resolution/src/resolution/data/identity_duplicate_decisions.json`) through the
     existing decision writer, `PgReviewQueue`: an `er_match` review item carrying the evidence, and an
     appended `review_decision`, where `accept` means same_as and `reject` means distinct (design §3; P31.11
     consumes it). The reviewer is `engineering:P31.3`, delegated by the operator in Q6. Both identifier rows
     stay, so the query still returns the pairs, now each with a decision. A re-run adds +0.
   - **The three decisions, all same_as:**
     - **`camilo_schools_cctv:1` — a race.** One camera, one source; the second entity has 0 claims.
     - **`us.state OK` — deliberate.** The seed's `agency:okc:okcpd-1`/`-2` are one agency, the Oklahoma City
       Police Department ("Dept" vs "Department").
     - **`fr.insee 01` — deliberate.** The seed's `gex-police-municipale-1`/`-2` are one body, the municipal
       police of Gex.
   - **Evidence:** creation times, WORM run rows, claim counts and organisation names are in the data file
     and `docs/build/runs/P31.3.md`.

## Consequences

- **The race is closed for guarded writers.** A real-PG test forces the interleaving: the second writer blocks
  on the uncommitted key, then reuses the first writer's entity, with no orphan. A second real-PG test races
  two whole sinks over 300 new subjects and gets exactly one entity per subject.
  - **Still open until P31.4:** the scheduled `sig-ingest-*` jobs still run pre-P31.3 images. Until P31.4
    rolls them by digest, two *old-image* executions can still race each other. A guarded writer adopts any
    identifier they leave behind rather than duplicating it.
- **Throughput.** Measured locally on PG18+PostGIS (testcontainer, amd64 image under emulation), same
  protocol before and after, 100,000 OSM-shaped claims:
  - **land:** 30.6k → 136.6k claims/min;
  - **+0 replay:** 14.6k → 401.2k claims/min;
  - **round trips per claim:** 4.38 → 0.0017 on the land, 3.13 → 0.0010 on the replay.

  - **Hosted** (`db-custom-1-3840`): a Cloud Run job (`sig-sink-bench`, next to `sig-pg`) did a bounded +0
    replay of the already-landed `camreg_fl511_fl`: 116,048 records, 103,713 claims, all duplicates.
    - The pre-P31.3 sink took **1,513 s and 1,444 s** (4.1k and 4.3k claims/min, 3.09 round trips per claim).
    - The batched sink took **8.9 s, 8.9 s and 8.6 s** (about 700k claims/min, 0.0009 round trips per claim).
    - Every pass inserted +0 and recorded an `ok` completion.
  - **Projected** 2026-10-10 OSM re-ingest on the batched sink: about 10–15 min end to end, against about
    5 h at the measured pre-P31.3 rate. The derivation is in `docs/build/runs/P31.3.md`. The new-claim land
    rate on hosted is not measured, because a land needs real new claims. P31.4's bounded OSM run measures it
    (D-P31.3-1).
- **Hosted schema deploy** (2026-09-24, no ingest running): `entity_identity_key` committed 22:36:58Z, 33 s
  after the deploy started (including the sqitch container start). The backfill keyed 247,060 subject values,
  75 MB with its indexes. The btree built CONCURRENTLY and committed at 22:37:10Z (28 MB, valid).
- **Schema:**
  - two additive changes;
  - `entity_identity_key` holds one row per subject value (about 247k on hosted at deploy);
  - `sig_ingest` gets SELECT and INSERT on it;
  - one more btree on `entity_identifier`.
- **Insert order.** Claims still insert in input order, so `claim_id` order follows input as before. Two
  concurrent sinks inserting the *same* new claims in *different* orders can still deadlock on the digest
  index, exactly as the row-at-a-time path could. Postgres aborts one chunk and the resume path re-runs it.
  Sorting by digest would remove that, at the cost of changing `claim_id` order, so it is not done here.
- **The duplicate query never empties.** Being append-only, it keeps returning decided pairs. The check is
  "every pair has a decision", not "no pairs". Attribute schemes (`us.state`, `fr.insee`) can gain new
  legitimate pairs whenever another entity shares a jurisdiction. Each one then needs a decision, or the check
  must be narrowed (Revisit trigger c).

## Alternatives considered

- **A transaction-scoped advisory lock per `(scheme, value)`** around check-then-insert. It needs no schema,
  but the database does not enforce it: it protects only writers that remember to take it. It also costs one
  shared lock-table slot per new subject per chunk: about 1.1k per 10k-claim OSM chunk, against
  `max_locks_per_transaction × max_connections` = 6,400 on hosted. Rejected.
- **A partial `UNIQUE (scheme, value)` index on `entity_identifier` that excludes the historical duplicates.**
  Its predicate would have to name hosted entity ids, and every `ON CONFLICT` would have to repeat that
  predicate to infer the index. Rejected as fragile.
- **Deleting or merging the historical duplicates.** Forbidden: the spine is append-only (root `AGENTS.md`
  §5, P1–P3).
- **Pipeline mode / `executemany`.** See Decision 5.
- **Distinct instead of same_as for the seed pairs.** The shared jurisdiction identifier is not why they are
  one entity. The recorded names, types and places are.

## Revisit trigger

- (a) P31.4's hosted replay on the rolled image shows the chunk write is no longer DB-bound, or a chunk
  exceeds a Cloud Run task deadline. Then revisit `insert_batch_size` / `commit_chunk_size`, or consider
  `COPY` into a staging table.
- (b) A deadlock on `claim_content_digest` is observed between concurrent sinks. Then sort each chunk by
  digest and accept the change in `claim_id` order.
- (c) The identity-triage check reopens on an attribute scheme (a new `us.state`/`fr.insee` pair). Then narrow
  the acceptance query to `GUARDED_SCHEMES`, in a new ADR, or record the new pair's decision.
- (d) P31.5 adds an organisation scheme to `GUARDED_SCHEMES`. It must ship that scheme's backfill in the same
  change.
