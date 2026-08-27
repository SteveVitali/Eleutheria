# ADR-010: DuckDB/Parquet analytics boundary; no raw audit rows anywhere

- **Status:** Accepted
- **Date:** 2026-08-26
- **Phase:** P00.2
- **Requirement ids:** SIG-STORE-010
- **Spec:** docs/2_canonical_design_spec.md §18

## Context

Analytics must not become a back-door that stores or exposes the per-search audit rows the publication policy forbids.

## Decision

Run analytics over a DuckDB/Parquet projection built from aggregates only; no raw audit rows enter the analytics boundary, ever.

## Consequences

Analytics scale cheaply and stay offline-friendly; the de-pseudonymisation hazard (§43.2a) cannot leak through analytics. Requires an aggregation step before projection.

## Alternatives considered

Analytics directly on the OLTP store (contention, and tempts raw-row access); a warehouse ingesting raw rows (violates §43.2a).

## Revisit trigger

Aggregation-only analytics cannot answer a required question, or DuckDB cannot meet analytic scale.
