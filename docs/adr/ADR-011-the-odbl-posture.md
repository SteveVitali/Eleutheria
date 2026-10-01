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

## Status updates

- **Status:** Qualified by ADR-182 (2026-10-01)
- **Status note (2026-10-01T13:59:14Z, Round-11 T1, unit SEED-12c):** ADR-182 (WV-07; the operator's adopted sentence,
  agent-drafted and adopted at 2026-10-01T04:28:49Z, sha256 `c5a71e9d7fd9…`: *"I waive the counsel-review clauses of
  SIG-LIC-009 and SIG-INGEST-037; rights decisions rest on my recorded determinations, labelled as such."*) leaves
  this ADR's counsel-conditioned revisit clause unable to fire as written — SIG has no counsel (U-013; F3 §5.4,
  NEW-8). The clause: "counsel (SIG-LIC-009) reaches a different regional-cut conclusion". Restated (agent reading,
  labelled): it fires when the operator records a different determination on the regional-cut unit — one of
  SIG-LIC-009's four questions, which stay on the risk register — labelled "the operator's own determination (no
  counsel)" (ADR-167); or when counsel is obtained (LATER-05) or a first legal demand arrives (ADR-182's and ADR-166's
  triggers). The decision and the body above are unchanged (SIG-ENG-003).
