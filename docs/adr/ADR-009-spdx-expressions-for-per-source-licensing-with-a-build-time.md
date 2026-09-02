# ADR-009: SPDX expressions for per-source licensing, with a build-time compatibility gate

- **Status:** Accepted
- **Date:** 2026-08-26
- **Phase:** P00.2
- **Requirement ids:** SIG-LIC-001, SIG-LIC-010, SIG-LIC-004a
- **Spec:** docs/2_canonical_design_spec.md §42

## Context

Every source carries distinct rights; incompatible licence regimes must never be silently merged into one export.

## Decision

Record each source's licence as an SPDX expression (with `LicenseRef-SIG-*` for bespoke terms) in a rights record, and compute export licences from constituent rights with a compatibility gate that fails the build on incompatibility. Compartments are data (`policy/data/licenses.toml`), not code.

## Consequences

Cross-compartment merges fail in CI; adding a new share-alike source is a data row. `redistributable` stays a separately-reviewed boolean, never derived from the string.

## Alternatives considered

A single project-wide licence (legally wrong for federated data); deriving redistributability from the licence string (SIG-LIC-003 forbids it).

## Revisit trigger

SPDX cannot express a licence SIG must ingest, or the compartment model needs a regime the data schema cannot represent.
