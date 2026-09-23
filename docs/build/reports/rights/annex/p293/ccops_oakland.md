# Rights-review packet — `ccops_oakland` (Oakland Privacy Advisory Commission)

> Facts (the standing legal basis + retrieval date) are separated from judgement (the
> Decision line). This packet asserts no legal conclusion (§3.1). No source content was fetched
> in this run — the verbatim terms-page capture (SIG-LIC-002) is part of the deferred live half
> (D-R7.3-BREADTH); this packet records the review basis. The prior-pass host 403 (P26.2 discovery)
> is an ACCESS posture, recorded and never bypassed; the RIGHTS review below is independent.

- **Source id:** `ccops_oakland`
- **Homepage:** https://www.oaklandca.gov/boards-commissions/privacy-advisory-board
- **Terms URL:** https://www.oaklandca.gov/boards-commissions/privacy-advisory-board — retrieved 2026-09-23 (documented posture, not yet captured)
- **Class:** municipal surveillance-oversight ordinance (CCOPS) — Oakland Ordinance 13489 (2018)
  mandates annual surveillance-technology use reports via the Privacy Advisory Commission; one of the
  strongest CCOPS oversight regimes.

## Basis (the standing legal fact)

The ordinance-mandated use policies + PAC annual surveillance reports are **municipal public records**.
SIG extracts the **factual disclosures** they contain — department, technology, vendor, retention,
oversight body — and never re-hosts the expressive PDFs. The **facts** of a factual compilation are
not copyrightable (**Feist Publications v. Rural Telephone**, 499 U.S. 340). This is the GL-GATE-07 US
basis: `LicenseRef-PublicRecord-FactualCompilation`.

## SPDX candidate

`LicenseRef-PublicRecord-FactualCompilation` — the GL-GATE-07 US basis for municipal public records
(`policy/data/licenses.toml`; `public_record` compartment). Recorded under its own expression so the
basis stays visible and cannot silently fold into the permissive CC-BY graph.

## redistributable analysis

Separately reviewed (SIG-LIC-003): the derived facts of a public-record factual compilation are
reusable; `redistributable = true`, `derivative_permitted = true`. The upstream PDFs are never
re-hosted (the derived-facts operational rule the existing CCOPS adapters follow).

## Relationship weighting / mandated ≠ populated

Each disclosure resolves onto an existing operator/department + vendor + deployment entity via the
P28.6 accountability chain. A mandated disclosure that is present-but-empty is recorded as such
(mandated ≠ populated), never as a deployment claim.

## Decision

Flip `ingestion_permitted = true` under **GL-GATE-07 / HG-03** (LEDGER GATE DECISIONS 2026-09-23),
reviewer `maintainer (delegated)`, 2026-09-23, `LicenseRef-PublicRecord-FactualCompilation`. Connector
class `government_mandated_disclosure` (index_page → disclosure_document, no bespoke adapter). Live
fetch + terms capture + dedup into the resolved graph deferred (**D-R7.3-BREADTH**).
