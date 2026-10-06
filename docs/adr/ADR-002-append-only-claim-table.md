# ADR-002: Append-only claim table; entity tables hold identity only

- **Status:** Accepted
- **Date:** 2026-08-26
- **Phase:** P00.2
- **Requirement ids:** SIG-STORE-009, SIG-STORE-020
- **Spec:** docs/2_canonical_design_spec.md §16.1–16.4

## Context

The defining standard forbids silent overwrites (§3.1). A conventional mutable-row model destroys the history a provenance graph exists to keep.

## Decision

Claims are append-only; entity tables carry identity only, never attribute values. Resolved values are a derived view over claims. Corrections are new assertions with `supersedes`.

## Consequences

History is preserved by construction; a query at a prior belief time is reproducible. Costs storage and requires derived-view machinery for 'current value'.

## Alternatives considered

Mutable entity rows with an audit log (the audit log becomes a second, divergent source of truth).

## Revisit trigger

A measured need arises to store a value with no supporting claim, or the derived-value view cannot meet performance budgets even after projection.

## Status updates

- **Status:** Qualified by ADR-189 (2026-10-01)
- **Status note (2026-10-01T07:53:45Z, Round-11 T1, planning orchestrator):** ADR-189 (WV-11, the operator's adopted sentence at
  2026-10-01T06:51:11Z) approves one operator-only, database-enforced purge function as the sole exception to the
  append-only claim table (SIG-STORE-011), limited to material SIG must not hold at all (SIG-GOV-008 scope), leaving a
  tombstone and a public log entry. Every other path stays insert-only; this decision is otherwise unchanged.
