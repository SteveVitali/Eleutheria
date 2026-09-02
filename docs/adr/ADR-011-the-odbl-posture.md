# ADR-011: The ODbL posture: OSM-derived assets in a separate compartment (Strategy B)

- **Status:** Accepted
- **Date:** 2026-08-26
- **Phase:** P00.2
- **Requirement ids:** SIG-LIC-006, SIG-LIC-004a
- **Spec:** docs/2_canonical_design_spec.md §42.3

## Context

SIG's device attribution is defined by comparison with OSM and uses OSM geometry, so the conservative reading of the OSM guidelines triggers ODbL share-alike; the two relevant guidelines point in opposite directions.

## Decision

Adopt Strategy B: publish the OSM-derived physical-asset layer under ODbL-1.0 as a physically separate table and export file, keeping the SIG-original graph under CC-BY-4.0.

## Consequences

The licence enforces the federation compact (giving operator attributions back to OSM). ODbL and the CC-BY graph never merge. Requires per-compartment export files.

## Alternatives considered

Strategy A ('store only identifiers' — a join key is still a reference; unsafe); Strategy C (share-alike on everything — needlessly restricts non-OSM data).

## Revisit trigger

OSMF issues definitive guidance that changes the substantiality or collective-database analysis, or counsel (SIG-LIC-009) reaches a different regional-cut conclusion.
