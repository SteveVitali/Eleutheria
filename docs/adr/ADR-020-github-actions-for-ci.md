# ADR-020: GitHub Actions for CI

- **Status:** Accepted
- **Date:** 2026-08-26
- **Phase:** P00.2
- **Requirement ids:** SIG-ENG-015, SIG-ENG-016
- **Spec:** docs/2_canonical_design_spec.md §48

## Context

CI must run the same `make` gate humans run, on every PR, with dependency/container scanning and per-release SBOM/signing.

## Decision

Use GitHub Actions as the CI system, invoking the same `make` targets as local development.

## Consequences

Ubiquitous, no extra hosting, matches where the code lives. Couples CI config to GitHub.

## Alternatives considered

Self-hosted CI (operational burden for a small team); another SaaS CI (another account/economics).

## Revisit trigger

The project moves off GitHub, Actions pricing/limits become prohibitive, or a compliance need requires self-hosted runners.
