# ADR-025: Temporal invariants as pipeline data-quality checks; as-of as SQL functions

- **Status:** Accepted
- **Date:** 2026-08-27
- **Phase:** P02.3
- **Requirement ids:** SIG-TIME-007, SIG-TIME-008, SIG-TIME-009, SIG-TIME-013, SIG-TIME-014
- **Spec:** docs/2_canonical_design_spec.md §9.4, §9.6

## Context

SIG-TIME-013 requires the eight temporal invariants TI-1..TI-8 be enforced as
database constraints **or** as pipeline data-quality checks that fail the run —
never as application conventions. Some are already physical from P02.1: a
`tstzrange` structurally guarantees `lower <= upper` (TI-1/TI-2 for the range
columns), the `resolution_no_overlap` GiST EXCLUDE covers same-predicate L3
overlap, and `claim_observed_not_future` covers TI-5. But several (TI-3/TI-4
cross-layer ordering with skew tolerance, TI-6 across mutually-exclusive
predicates, TI-7 supersedes-chain acyclicity, TI-8 temporal anchoring) are not
naturally single-row CHECK constraints. Separately, §9.4 requires a two-axis
as-of read contract that every read path shares.

## Decision

Enforce TI-1..TI-8 as pure, deterministic **pipeline data-quality checks**
(`db.invariants`) that a connector runs over the claims/resolutions it is about to
assert and that fail the run on any violation (SIG-ENG-017), complementing the
physical constraints P02.1 already provides. Ship the as-of contract as the
`claim_as_of` / `resolution_as_of` **SQL functions** (the shared, DB-level filter
over `valid_period` and `sys_period`), with a matching Python predicate builder
(`db.temporal.AsOf`) for callers assembling ad-hoc queries. Add one additive,
back-compatible `temporally_unanchored` flag (+ reason) to `claim` for TI-8.

## Consequences

Invariants are testable as fast, deterministic property tests (no live DB needed)
and run in the pipeline where they protect production data; the as-of filter has
one authoritative definition shared by API, export, and UI. TI-6/TI-7 are batch
checks, so they see only the batch handed to them — a full-graph audit remains a
separate nightly job.

## Alternatives considered

All-invariants-as-DB-constraints (TI-6/TI-7/TI-8 need triggers or cross-row state
that are costly and hard to test); as-of as application-only query building (no
shared DB-level contract; every surface re-implements the filter and can drift).

## Revisit trigger

A batch check proves insufficient against production data (e.g. a cross-batch
supersedes cycle slips through), or the as-of filter needs pushdown the SQL
functions cannot express.
