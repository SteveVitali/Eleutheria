# ADR-006: OCFL 1.1 evidence store on object storage with governance-mode Object Lock

- **Status:** Accepted
- **Date:** 2026-08-26
- **Phase:** P00.2
- **Requirement ids:** SIG-EVID-005, SIG-EVID-006, SIG-GOV-009
- **Spec:** docs/2_canonical_design_spec.md §17.3

## Context

Raw source snapshots must be immutable, digest-verifiable, re-parseable years later, and recoverable without SIG's software — while remaining removable for legitimate privacy demands.

## Decision

Store evidence bytes in an OCFL 1.1 root on S3-compatible object storage, one object per source stream, one version per capture, with Object Lock in **governance** mode (never compliance mode).

## Consequences

E1–E6 (§17.1) satisfied by construction; the inventory is recoverable JSON. Governance mode keeps takedown (§45) satisfiable via a permissioned, audited path, at the cost of not being unimpeachable against a hostile demand.

## Alternatives considered

A bespoke content-addressed layout (reinvents OCFL); compliance-mode lock (makes legitimate removal technically impossible).

## Revisit trigger

OCFL is superseded by a better-supported preservation standard, or a legal regime forces reconsideration of governance vs compliance mode.
