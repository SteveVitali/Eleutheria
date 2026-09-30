# ADR-103 — Hosted Round-6 materialization: a least-privilege materialize role, in-GCP execution, and the hosted-scale deviations

- **Status:** Accepted
- **Phase / ticket:** Phase 30 / P30.2 (`docs/tickets/P30.2__hosted-round6-materialization.md`) — Round 8 `GO-LIVE.2`; the ticket this ADR is owned by and lands with.
- **Date:** 2026-09-24
- **Related:** ADR-005 (resolution is a stored decision), ADR-012 (tier RLS), ADR-081 (read-surface grants), ADR-099 (materialize resolution at scale), ADR-101 (surface reads the materialized graph), ADR-102 (the temporary `db-custom-2-8192` tier this run used); deferrals **D-R6.1-EVAL** (hosted half), **D-R6.2-EDGES**, **D-R6.3-CONTRADICTIONS**, **D-R6.4-COVERAGE**, **D-R6.6-ACCOUNTABILITY**, **D-R7.2-DETECTORS** (closed by P30.2) and the follow-ups **D-P30.2-1 / -2 / -3** this ADR opens; operator gate answer LEDGER GATE DECISIONS 2026-09-23 ("I authorize you to create postgres role under ADC"); backlog home **BL-057**.

## Context

The Round-6 materializers (P28.1–P28.6) and the P29.2 detector were proven only over seeded PG18+PostGIS.
The hosted spine (2,280,784 claims / 246,998 entities at run time) lacked the six Round-6 sqitch changes, and
the tickets framed the blocker as "Cloud SQL `postgres` is not a superuser and cannot assume the read roles".
Inspecting the hosted cluster showed the real shape: every spine table (and the read roles) is **owned by
`sig`**, the login every prior sqitch deploy ran as; `postgres` is neither the owner nor a member of the read
roles, so it can neither `ALTER` the tables nor `GRANT` on them. The P30.1 OSM land also showed the write path
is latency-bound (row-at-a-time round-trips), so a laptop → cloud-sql-proxy run would pay WAN latency per
statement. Finally, the first hosted pass exposed three facts about the real spine that the seeded proofs
could not: every entity is typed `deployment`; no claim carries an `object_entity` (entity-ref) partner; and
the camera-registry predicates that make up almost the whole spine have no row in the resolver's predicate
registry.

## Decision

1. **A dedicated least-privilege role, created as a sqitch change deployed by the schema owner.** The new
   `materialize_role` change creates `sig_materialize` (`NOLOGIN NOBYPASSRLS`, not superuser): READ =
   membership in `sig_read_public` (the ADR-012 tier-0 RLS ceiling binds); WRITE = `INSERT` only on
   `resolution`, `relationship`, `contradiction`, `coverage_record`, `research_task`,
   `inference.derived_fact` and the three resolution FK vocab tables; `UPDATE/DELETE/TRUNCATE` revoked
   everywhere and no write at all on the claim spine; the deploying login is granted membership so it can
   `SET ROLE`. It is deployed **as `sig` (the owner) under operator ADC** over `cloud-sql-proxy --token` — the
   operator authorized the role creation; `postgres` is not the mechanism because it cannot grant on
   `sig`-owned tables. Every materializer connects as `sig` and runs `--role sig_materialize`.
2. **Execute next to the database.** `ops/gcp/materialize.sh` (idempotent, `--check` plan with no ADC)
   deploys the schema, Cloud-Builds a **SHA-tagged** image `sig-api:materialize-<sha>` from `git archive HEAD`
   (never retagging `:latest`, so the API service and the ingest jobs are untouched), upserts a
   `sig-materialize` Cloud Run job (Cloud SQL socket, Secret Manager password, 4 CPU / 16 GiB, 24h timeout,
   no retries) and runs each step as a job execution with an `--args` override. The DSN is assembled inside
   the container; no secret is on a command line or in a file.
3. **Coverage runs with `--no-negative-space` on the hosted spine.** Because every entity is typed
   `deployment`, the P28.4 peer-class rule would treat all 246,993 subjects as one class tracking all 116
   predicates and emit **26,696,184** `not_researched` rows (246,993 × 116 − 1,955,004 claimed pairs, measured
   read-only) — ~12× the spine, dominated by meaningless absences (a traffic camera "not researched" for
   `bill_title`). That would be noise presented as §32.1 negative space. The metrics (provenance completeness +
   116 per-predicate reconciliation ratios) are materialized; the negative space is recorded as a measured
   count and deferred to a peer-class refinement (**D-P30.2-1**).
4. **Fix the coverage overclaim the hosted run exposed (finding COVERAGE-RESOLVED-01).** The P28.4
   reconciliation ratio counted any `resolution` row as "a resolved value", so the OKC 299-vs-190
   `unresolved_conflict` read as "1 of 1 subjects with a resolved `claimed_device_count`". The numerator now
   counts only decisions with a `winning_claim`, and `read_materialized_coverage` returns the **latest**
   append-only measurement per quantity (latest `uuidv7` `coverage_id`), so the superseded 1-of-1 row stays in
   the table as history but no reader surfaces it. Both are test-pinned over real PG.
5. **The detector's records-request jurisdiction is set only when the queue is single-jurisdiction.**
   `sig-tasks detect --jurisdiction` routes every records-oriented task to one state's statute; on a national
   spine that would misroute. P30.2 passes `OK` because the entire queue is the OKC contradiction; the script
   exposes it as an explicit, documented opt-in (`SIG_DETECT_JURISDICTION`). Drafts are never sent
   (D-R7.2-SEND untouched).

## Consequences

- The six Round-6 changes + `materialize_role` are deployed on the hosted spine and every materializer + the
  detector ran there, append-only and idempotent (+0 re-runs), with real counts recorded in
  `docs/build/reports/P30.2_HOSTED_MATERIALIZATION.md`. Nothing was fabricated.
- The honest hosted graph is thin: 8 resolution envelopes, 0 resolved sites of 230,267 observation sites,
  0 relationship edges, 1 contradiction, 117 current coverage metrics, 0 accountability links, 1 research task.
  The public surface therefore keeps the observation-level framing (P28.5 degrades honestly). The three
  input gaps are owned by **D-P30.2-2** (entity-ref claims — no `object_entity` on any hosted claim, so no
  edges and no accountability chain) and **D-P30.2-3** (predicate-registry coverage for the camera-registry
  predicates, so resolution can adjudicate them).
- The materialize role is the durable, re-runnable mechanism for every future hosted materialization; no
  operator console action exists outside the committed sqitch change and script.

## Alternatives considered

- **Create the role as `postgres`.** Not possible for the grants: only the table owner (`sig`) can grant on
  `sig`-owned tables. Transferring ownership to `postgres` would be a far larger change.
- **Run the materializers as `sig` with no role.** Works (the owner bypasses nothing it isn't subject to), but
  gives the run DDL + UPDATE/DELETE capability; the gate asked for least privilege.
- **Materialize the 26.7M negative-space rows anyway.** Rejected: multi-hour row-at-a-time writes, a table
  ~12× the spine, and a surface of absences that do not describe real research gaps.
- **Leave the coverage overclaim for a later ticket.** Rejected: P30.3 publishes these rows; publishing an
  unresolved contradiction as "resolved" violates §3.1 at launch.

## Revisit trigger

Revisit when D-P30.2-1 lands a peer-class refinement (then run coverage with negative space), when
D-P30.2-2 / D-P30.2-3 land (re-run edges / accountability / resolution and expect non-zero counts), if a
second materialize login or a non-`sig` schema owner is introduced, or if the hosted spine is migrated off
Cloud SQL (the role + execution mechanism would need re-deciding).
