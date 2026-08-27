# ADR-012: Sensitivity tiers enforced by RLS, applied at the view layer

- **Status:** Accepted
- **Date:** 2026-08-26
- **Phase:** P00.2
- **Requirement ids:** SIG-GEO-008, SIG-SEC-004, SIG-STORE-024
- **Spec:** docs/2_canonical_design_spec.md §19.4, §44.4

## Context

Coordinate precision and record visibility must degrade by sensitivity class without ever leaking full precision through an aggregate or a mis-scoped query.

## Decision

Enforce sensitivity tiers with restrictive row-level security, and apply coordinate-precision transforms at the view layer; full precision is retained only in canonical storage. Export roles run with row security off so a would-be-filtered export fails loudly.

## Consequences

Precision policy is enforced by the database, not by application discipline; RLS policy tests are CI-blocking. Requires careful role design.

## Alternatives considered

Application-layer filtering only (one missed query leaks); blurring after aggregation (leaks precise values through the aggregate, SIG-GEO-010).

## Revisit trigger

Postgres RLS proves inadequate for a required policy, or the view-layer transform cannot meet query-latency budgets.
