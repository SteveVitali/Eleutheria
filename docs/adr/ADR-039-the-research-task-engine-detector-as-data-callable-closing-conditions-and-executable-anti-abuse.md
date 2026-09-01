# ADR-039: The research-task engine — detector-as-data, callable closing conditions, and the disposition→data bridge

- **Status:** Accepted
- **Date:** 2026-09-01
- **Phase:** P10.1
- **Requirement ids:** SIG-TASK-001, SIG-TASK-002, SIG-TASK-005, SIG-TASK-006, SIG-TASK-007, SIG-TASK-008, SIG-TASK-009, SIG-TASK-010, SIG-TASK-011, SIG-TASK-012, SIG-TASK-013, SIG-TASK-014
- **Spec:** docs/2_canonical_design_spec.md §33.1 (detector spec language), §33.3 (lifecycle), §33.4 (dispositions), §33.5 (geographic queues), §33.6 (anti-abuse), §33.7 (local-group registry)

## Context

P10.1 is the task-coordination **engine**: the detector specification language, the
lifecycle with auto-invalidation, the disposition vocabulary, geographic queues, the
anti-abuse rules, and SIG's own local-group registry. The concrete detector *catalog*
(§33.2, 34 detectors) is P10.2, and the records-request path that exercises
`resolved_no_evidence_exists` end-to-end is P10.3. Several structural questions had to
be settled against existing precedent.

1. **What makes a `closing_condition` "testable" (SIG-TASK-002)?** A type with no
   testable closing condition MUST NOT register — but a free-text string is not
   testable by the engine, and the whole point of §33 is that the engine can *decide*
   when a task is done.
2. **Where does the engine live, and does it persist?** The `research_task`,
   `coverage_record`, and (absent) local-group tables are relational; §47 gives
   `tasks/` as the package home.
3. **How does `resolved_no_evidence_exists` reliably produce a `CoverageRecord`
   (SIG-TASK-009)?** If it is just one disposition among eight, a caller can record
   "searched, nothing found" without writing the coverage record, and the queue
   quietly fails to shrink.
4. **How are the anti-abuse MUSTs (SIG-TASK-012/013) made verifiable** rather than
   left as prose?

## Decision

1. **Model `detector` and `closing_condition` as callables over subject facts, not
   text.** A `TaskType` carries a `Detector` (a versioned `Callable[[Facts], bool]`)
   and a `closing_condition: Callable[[Facts], bool] | None`. "Testable" is then a
   mechanical property — `has_testable_closing_condition` is `callable(...)` — and
   `TaskTypeRegistry.register` refuses a type whose closing condition is `None`
   (SIG-TASK-002). The same callable detector is what the lifecycle re-evaluates to
   auto-invalidate (SIG-TASK-006): "the detector no longer fires" is
   `not detector.fires(current_facts)`, an executable check.

2. **Put the engine in `tasks/` as pure-Python value objects aligned to the DDL; no
   Postgres persistence and no HTTP here** — continuing the ADR-031/036/037/038
   precedent. `ResearchTask`'s fields track `research_task`
   (`db/deploy/graph_annotations.sql`), but persisting tasks and serving/claiming them
   over an API is a downstream ticket. This ticket owns the *shapes, the state
   machine, and the coordination rules*.

3. **Make `resolved_no_evidence_exists` reachable only through a bridge that writes
   the record.** `ResearchTask.close()` **refuses** the `resolved_no_evidence_exists`
   disposition; the only way to reach it is `dispositions.resolve_no_evidence_exists`,
   which constructs a `searched_not_found` `CoverageRecord` **first** and only then
   closes the task. Because it reuses `inference.coverage.CoverageRecord` (P09.1), the
   `sources_searched`-required invariant (SIG-METRIC-002) is inherited: an anonymous
   negative is rejected *before* the task closes, so the queue never shrinks on an
   unrecorded negative (SIG-TASK-009). `tasks` therefore depends on `sig-inference`.

4. **Encode the anti-abuse MUSTs executably.** Task generation goes through a
   `TaskPool` whose `generate` enforces `(task_type, subject)` duplicate suppression
   (SIG-TASK-007, mirroring the `research_task` UNIQUE) and a per-subject
   `RateLimiter` (SIG-TASK-013). The no-volume-leaderboard prohibition (SIG-TASK-012)
   is a function that **always raises** (`volume_leaderboard`), mirroring ADR-038's
   capture–recapture refusal; recognition is a qualitative value object derived only
   from *verified* contributions, with no score/rank field.

5. **Geographic claims are ordering + visibility, never a gate.** A
   `GeographicClaim` expires (`is_active(now)`), and `any_contributor_may_work(task)`
   takes **no contributor and no claim** — it is `task.is_open` — so there is no code
   path by which a claim can exclude anyone (SIG-TASK-010/011). The claim only affects
   `order_for_group` (a sort, not a filter).

6. **The local-group registry is a self-contained, in-memory store (SIG-TASK-014).**
   No network dependency, so its availability is never contingent on the external
   directory that did not respond (F1.9). No `local_group` DDL is added here (none
   exists in Appendix C); persistence is deferred with the rest of the engine.

## Consequences

The task engine is a set of pure-Python, fully-tested value objects and small state
machines with a single owner of the detector-as-data contract, the lifecycle, the
disposition vocabulary, and the registry. Three MUSTs that are easy to leave as prose
are mechanically gated: an untestable closing condition fails registration, a
no-evidence disposition without named sources fails before closing, and a volume
leaderboard is a failing test. `tasks` now depends on `sig-inference` (hence
transitively on `sig-db`/`sig-reconcile`); this is a one-directional edge (nothing in
`inference` imports `tasks`). Persisting tasks/claims/groups and the contributor-facing
surfaces are explicitly deferred.

## Alternatives considered

- **Free-text `closing_condition` with a "non-empty" check** (rejected: a non-empty
  string is not testable by the engine, so SIG-TASK-006 auto-invalidation and the
  SIG-TASK-002 gate would both degrade to hoping a human wrote something meaningful).
- **`resolved_no_evidence_exists` as an ordinary disposition on `close()`** (rejected:
  it makes SIG-TASK-009 a convention a caller can skip; routing it through a bridge
  that writes the `CoverageRecord` first makes "the queue shrinks only by producing
  data" an invariant).
- **A new top-level `metrics/` or persistence layer now** (rejected: `tasks/` is the
  §47 home and live persistence is the downstream ticket's remit; adding it here
  forks the pure-Python precedent).
- **Adding a `local_group` table + claim table to the DDL** (rejected here: Appendix C
  names none, and the engine's ownership guarantee (SIG-TASK-014) is satisfied by a
  self-contained in-memory registry; a schema is an additive downstream change when
  persistence lands).
- **Re-encoding the coverage shape inside `tasks`** (rejected: `inference.coverage`
  already owns it with the `sources_searched` invariant; a second copy would drift).

## Revisit trigger

Revisit when the engine is persisted (the `research_task` row is written/claimed for
real and a `local_group`/claim schema is added), when P10.2 registers the §33.2
catalog against this DSL (the `Facts` shape the detectors read is pinned to the real
graph-query surface then), when P10.3 exercises `resolve_no_evidence_exists` through a
filed records request, or when the contributor API/UI (claiming, dispositions,
recognition surfaces) lands and needs a wire projection of these objects. Also revisit
if a `local_group` or claim table is added to Appendix C, so the in-memory registry is
aligned to it.
