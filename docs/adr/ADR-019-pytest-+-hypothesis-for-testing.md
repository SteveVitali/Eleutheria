# ADR-019: pytest + Hypothesis for testing

- **Status:** Accepted
- **Date:** 2026-08-26
- **Phase:** P00.2
- **Requirement ids:** SIG-ENG-015, SIG-ENG-016
- **Spec:** docs/2_canonical_design_spec.md §48

## Context

The test taxonomy requires randomized temporal-property tests alongside conventional unit/integration tests.

## Decision

Standardize on pytest as the runner and Hypothesis for property-based tests (e.g. temporal invariants, deterministic transforms).

## Consequences

One runner; property tests catch edge cases table-driven tests miss. Hypothesis adds a dev dependency and some flakiness discipline (seed control).

## Alternatives considered

unittest only (no property testing); a separate property-test framework (fragmentation).

## Revisit trigger

Hypothesis maintenance/licence changes, or property tests prove net-negative in maintenance for this codebase.
