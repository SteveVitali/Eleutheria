# ADR-008: SKOS for published controlled vocabularies

- **Status:** Accepted
- **Date:** 2026-08-26
- **Phase:** P00.2
- **Requirement ids:** SIG-ONT-008
- **Spec:** docs/2_canonical_design_spec.md §20

## Context

Published vocabularies need stable identifiers, multilingual labels, and interoperability with the wider linked-data ecosystem.

## Decision

Publish controlled vocabularies as SKOS concept schemes.

## Consequences

Standard, widely-consumed vocabulary format; supports adoption. Requires SKOS export from the LinkML source.

## Alternatives considered

Bespoke enums (poor interoperability); OWL classes for vocabularies (overweight).

## Revisit trigger

SKOS proves insufficient for a required vocabulary relationship, or adoption data shows consumers need a different format.
