# ADR-040: The §33.2 detector catalog and the §31 contradiction→task map

- **Status:** Accepted
- **Date:** 2026-09-01
- **Phase:** P10.2
- **Requirement ids:** SIG-TASK-003, SIG-TASK-004 (plus the per-row detector/closing-condition ids the catalog realizes)
- **Spec:** docs/2_canonical_design_spec.md §33.2 (the task catalog), §31 (the contradiction detectors this catalog maps to tasks)

## Context

P10.1 (ADR-039) built the task-coordination **engine** — the detector-as-data DSL,
the lifecycle with auto-invalidation, dispositions, geographic queues, anti-abuse. It
deliberately left the concrete catalog to P10.2 (recorded as scaffolded RISK-P10-07).
This ticket owns the **data**: the 34 enumerated task types of §33.2, plus the
SIG-TASK-004 mapping that guarantees every §31 contradiction detector has a route to
resolution. Three questions had to be settled.

1. **What is the count authority for the catalog?** The Part X Phase-10 AC once said
   "32 task types"; §33.2 now enumerates 34 rows, and the ticket reconciles the AC to
   §33.2 as authority.
2. **What does each detector read?** P10.1's `Detector.query`/`closing_condition` are
   `Callable[[Facts], bool]` over `Facts = Mapping[str, object]`. The real materialized
   graph does not yet expose a query surface these can bind to.
3. **What is "a §31 contradiction detector", and how does the SIG-TASK-004 mapping
   avoid drift?** §31 names a nine-member `contradiction_type` vocabulary
   (`reconcile.model.CONTRADICTION_TYPES`); the reconcile workflows (P08.2/P08.3) emit
   members of it. The catalog is coarser than that vocabulary.

## Decision

1. **Register all 34 §33.2 rows against P10.1's DSL as `tasks.catalog`, with §33.2 as
   the count authority.** `CATALOG_SIZE = 34` is asserted by the test suite, not
   assumed. Every row is a `TaskType` with a versioned `Detector` and a **callable**
   `closing_condition`; because `TaskTypeRegistry.register` refuses an untestable
   closing condition (SIG-TASK-002), a successful `build_catalog()` is itself the proof
   that no row is a "research this" placeholder (SIG-TASK-003). A row is designed so its
   detector stops firing exactly when the gap closes, so auto-invalidation (SIG-TASK-006)
   and the closing condition are two views of the same fact.

2. **Detectors read documented in-memory `Facts` keys — the representative query surface,
   not the live graph.** This continues ADR-039's scaffolding boundary (RISK-P10-07):
   the catalog pins each row's *contract* (which facts it reads, when it fires, when it
   closes) with committed positive/negative fixtures, and binding those keys to the real
   materialized-graph projection is a downstream change that does not alter the catalog's
   shape.

3. **Model SIG-TASK-004 as a many-to-one map from the §31 `contradiction_type`
   vocabulary to catalog task slugs (`CONTRADICTION_TASK_MAP`), cross-checked against
   `reconcile.model.CONTRADICTION_TYPES` in tests.** The authoritative "detector" set is
   the nine-member type vocabulary — the stable §31 taxonomy every reconcile detector
   classifies its output as. Because the §33.2 catalog is coarser than that vocabulary,
   the map is **many-to-one**: related contradiction classes share the catalog task that
   resolves them (e.g. `value_disagreement` and `policy_configuration_divergence` both
   route to `conflicting_retention`; `predicate_conflation` and `count_basis_mismatch`
   both route to `missing_physical_devices`). The test asserts the map's keys are exactly
   `CONTRADICTION_TYPES` and every value is a registered catalog slug, so a new
   contradiction type cannot be coined without giving it a task route, and no route can
   point at a non-existent task. The map lives in `tasks` as string literals rather than
   importing `reconcile` at runtime — the cross-check is a test-only import — so no new
   runtime package edge is added.

## Consequences

The engine now has its payload: 34 registered, individually-fixtured task types and a
proven-complete contradiction→task routing. The SIG-TASK-004 MUST ("detection without a
route to resolution is just an alarm") is a failing test if any §31 type is unrouted.
No new runtime dependency is added to `tasks` (the reconcile coupling is test-only). The
catalog's detectors read representative facts, so a green catalog proves the *contract*,
not yet live graph behaviour — the remaining scaffolding is the fact-key→graph binding.

## Alternatives considered

- **Keying SIG-TASK-004 on each reconcile emitting function (the 11 detectors in
  `tests/reconcile/test_detector_task_contract.py`) instead of the type vocabulary**
  (rejected: those functions already emit their own ad-hoc `task_type` slugs and are an
  implementation list that churns; the nine-member `contradiction_type` vocabulary is the
  stable §31 taxonomy and is drift-checkable against a single frozen set).
- **A strictly one-to-one contradiction→task map** (rejected: the §33.2 catalog is
  genuinely coarser than the §31 vocabulary; forcing injectivity would invent task types
  the spec does not enumerate, violating the scope-creep guard).
- **Importing `reconcile.model.CONTRADICTION_TYPES` into the `tasks` runtime** (rejected:
  it adds a package edge for a nine-string set; a test-only cross-check gives the same
  drift protection without the coupling).
- **Binding detectors to the live graph now** (rejected: no graph-query surface exists
  yet; ADR-039 already scoped that as downstream, and representative fixtures pin the
  contract in the meantime).

## Revisit trigger

Revisit when the detectors are bound to the real materialized-graph query surface (the
`Facts` keys become live projections), when §33.2 gains or loses a row (update
`CATALOG_SIZE` and the count-authority assertion), when §31 adds a `contradiction_type`
(the map must gain a route or the test fails), or when a reconcile detector begins
emitting `temporal_impossibility` or `undeclared_copying` (today mapped ahead of any
emitter) and the chosen catalog task proves a poor fit.
