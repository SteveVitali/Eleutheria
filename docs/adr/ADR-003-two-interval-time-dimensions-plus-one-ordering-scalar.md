# ADR-003: Two interval time dimensions plus one ordering scalar

- **Status:** Accepted
- **Date:** 2026-08-26
- **Phase:** P00.2
- **Requirement ids:** SIG-TIME-001
- **Spec:** docs/2_canonical_design_spec.md §9

## Context

Surveillance facts have both a real-world validity interval and a belief/record interval, and events need a total order for reproducibility.

## Decision

Model valid-time and belief-time as two intervals, plus one monotonic ordering scalar for deterministic replay.

## Consequences

Bitemporal queries ('what did we believe on date X about period Y') are expressible; replays are deterministic. Adds temporal-property test burden.

## Alternatives considered

Single timestamp (cannot distinguish validity from belief); event-sourcing only (loses interval semantics).

## Revisit trigger

A third independent time dimension proves necessary, or bitemporal modelling is shown to be unusable by contributors in practice.
