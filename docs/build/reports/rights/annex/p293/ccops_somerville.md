# Rights-review packet — `ccops_somerville` (Somerville MA surveillance-oversight ordinance)

> Facts (the standing legal basis + retrieval date) are separated from judgement (the
> Decision line). This packet asserts no legal conclusion (§3.1). No source content was fetched
> in this run — the verbatim terms-page capture (SIG-LIC-002) is part of the deferred live half
> (D-R7.3-BREADTH); this packet records the review basis.

- **Source id:** `ccops_somerville`
- **Homepage:** https://www.somervillema.gov/
- **Terms URL:** https://www.somervillema.gov/ — retrieved 2026-09-23 (documented posture, not yet captured)
- **Class:** municipal surveillance-oversight ordinance (CCOPS) — Somerville MA surveillance-oversight
  disclosures; Somerville was an early US facial-recognition ban; an under-covered oversight jurisdiction.

## Basis (the standing legal fact)

The ordinance-mandated surveillance disclosures are **municipal public records**. SIG extracts the
**factual disclosures** and never re-hosts the PDFs. The **facts** of a factual compilation are not
copyrightable (**Feist**). GL-GATE-07 US basis: `LicenseRef-PublicRecord-FactualCompilation`.

## SPDX candidate

`LicenseRef-PublicRecord-FactualCompilation` (`public_record` compartment; self-relicensable only).

## redistributable analysis

Separately reviewed (SIG-LIC-003): `redistributable = true`, `derivative_permitted = true`; PDFs never
re-hosted.

## Relationship weighting

Each disclosure resolves onto an existing operator/department + vendor + deployment entity via the
P28.6 accountability chain.

## Decision

Flip `ingestion_permitted = true` under **GL-GATE-07 / HG-03** (2026-09-23), reviewer
`maintainer (delegated)`, `LicenseRef-PublicRecord-FactualCompilation`. Connector class
`government_mandated_disclosure` (no bespoke adapter). Live fetch + dedup deferred (**D-R7.3-BREADTH**).
