# ADR-007: LinkML as the single ontology source of truth

- **Status:** Accepted
- **Date:** 2026-08-26
- **Phase:** P00.2
- **Requirement ids:** SIG-ONT-001
- **Spec:** docs/2_canonical_design_spec.md §20

## Context

The schema, vocabularies, and generated artifacts must have one authoritative definition to avoid drift across code, DDL, and docs.

## Decision

Define the ontology in LinkML as the single source of truth; generate downstream artifacts (DDL fragments, docs, validators) from it.

## Consequences

One edit point; generated artifacts are gated to match a fresh generation (SIG-ENG-016). Adds a LinkML toolchain dependency.

## Alternatives considered

Hand-maintained DDL plus separate docs (guaranteed drift); OWL-first (heavier than needed for this data).

## Revisit trigger

LinkML tooling becomes unmaintained, or generation cannot express a modelling need the domain requires.
