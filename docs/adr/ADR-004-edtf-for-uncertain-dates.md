# ADR-004: EDTF for uncertain dates

- **Status:** Accepted
- **Date:** 2026-08-26
- **Phase:** P00.2
- **Requirement ids:** SIG-TIME-004
- **Spec:** docs/2_canonical_design_spec.md §9.5

## Context

Source dates are frequently partial or uncertain ('summer 2019', '2021?'). Coercing them to exact timestamps manufactures false precision (violating §3.1).

## Decision

Use the Extended Date/Time Format (EDTF) to represent uncertain and partial dates as first-class values.

## Consequences

Uncertainty is preserved, not invented. Requires EDTF parsing/validation and UI affordances.

## Alternatives considered

Nullable exact dates (loses the distinction between unknown and uncertain); free text (unqueryable).

## Revisit trigger

EDTF tooling becomes unmaintained, or a superseding standard is broadly adopted by our data sources.
