# Rights-review packet — `dhs_fusion_center_assessments` (DHS National Network of Fusion Centers)

> Facts (the standing legal basis + retrieval date) are separated from judgement (the
> Decision line). This packet asserts no legal conclusion (§3.1). No source content was fetched
> in this run — the verbatim terms-page capture (SIG-LIC-002) is part of the deferred live half
> (D-R7.3-BREADTH); this packet records the review basis.

- **Source id:** `dhs_fusion_center_assessments`
- **Homepage:** https://www.dhs.gov/fusion-center-locations-and-contact-information
- **Terms URL:** https://www.dhs.gov/foia — retrieved 2026-09-23 (documented posture, not yet captured)
- **Class:** fusion-center governance (accountability/governance) — the DHS annual Fusion Center
  Assessment / National Network of Fusion Centers reports the governance/maturity of each named
  fusion center. Complements the existing `dhs_fusion_centers` roster with the governance layer.

## Basis (the standing legal fact)

DHS is a U.S. federal government department; its assessment reports are works of the United States
Government, not subject to copyright in the U.S. under **17 U.S.C. §105** (public domain).

## SPDX candidate

`CC0-1.0` — U.S.-federal public-domain work (per-source PD packet wins over the GL-GATE-07 US default).

## redistributable analysis

Separately reviewed (SIG-LIC-003): no copyright restriction; `redistributable = true`,
`derivative_permitted = true`.

## Relationship weighting

Each assessment resolves onto a fusion-center entity already registered via `dhs_fusion_centers` — a
governance finding attached to an existing node (deepens the resolved graph, §14.7), not a new pile.

## Decision

Flip `ingestion_permitted = true` under **GL-GATE-07 / HG-03** (2026-09-23), reviewer
`maintainer (delegated)`, `CC0-1.0`. Live fetch + terms capture + dedup deferred (**D-R7.3-BREADTH**).
