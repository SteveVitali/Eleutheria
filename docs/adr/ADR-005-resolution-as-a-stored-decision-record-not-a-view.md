# ADR-005: Resolution as a stored decision record, not a view

- **Status:** Accepted
- **Date:** 2026-08-26
- **Phase:** P00.2
- **Requirement ids:** SIG-STORE-018, SIG-IDENT-028
- **Spec:** docs/2_canonical_design_spec.md §14.6–14.8

## Context

Entity resolution must be re-runnable and auditable without silently moving claims between entities.

## Decision

Store each resolution as an explicit, versioned decision record (a `same_as` assertion with a ruleset version), not as an implicit view computed on read.

## Consequences

Re-clustering produces new assertions with a new ruleset version; prior clustering is preserved and diffable. Requires a decision-record schema and rebuild path.

## Alternatives considered

Compute clusters as a materialized view (non-auditable, destroys prior state on refresh).

## Revisit trigger

Resolution volume makes stored decisions impractical, or a provably-auditable view mechanism becomes available.
