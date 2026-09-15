# ADR-085 — Municipal-mandated-disclosure + derived-facts basis for CCOPS and pathways flips

- **Status:** Accepted
- **Phase / ticket:** operator determination (2026-09-15), the blocked-source unblock pass; resolved by P25.5's CCOPS + pathways work
- **Date:** 2026-09-15
- **Related:** rights packets `docs/build/reports/rights/{ccops_seattle,ccops_nyc_post,ccops_sf,pathways_rtcc_federation,pathways_fr_css_forensics,pathways_acoustic_drone_location}.md`, HG-02 (counsel flag retained), SIG-LIC-003/004/009, SIG-INGEST-049 (CCOPS dossier field list), §46 (pathways).

## Context

The three CCOPS sources (`ccops_seattle`, `ccops_nyc_post`, `ccops_sf`) ingest
ordinance-*mandated* public disclosures — records that Seattle SMC 14.18, the NYC
POST Act, and SF Chapter 19B respectively *require* city agencies to publish. The
three pathways sources (`pathways_rtcc_federation`, `pathways_fr_css_forensics`,
`pathways_acoustic_drone_location`) ingest SIG-authored fixture records that
paraphrase public procurement/policy/deployment documents, each carrying an upstream
citation. All six were recorded rights UNDETERMINED: municipal works are not
automatically public domain the way federal works are (17 U.S.C. §105 does not reach
states/municipalities), and the pathway fixtures' upstream terms are per-document
mixed.

The defensible basis the operator approved rests on two load-bearing facts of what
these connectors actually do:

1. **The ingestion unit is a derived-facts record, never upstream document bytes.**
   Both connectors emit claims, entities, and citations transcribed/paraphrased by
   SIG. No source document is re-hosted — the disclosure PDF or the upstream page is
   *cited*, not copied. Facts themselves (dates, agency names, equipment counts,
   ordinance citations) are uncopyrightable in US law; what copyright could attach
   to — the expressive text — is precisely what SIG does not redistribute.
2. **Mandated disclosure.** For CCOPS, the underlying records exist *because* a law
   ordered their publication; the connector's re-presentation of the disclosed facts
   tracks the mandate's purpose. For pathways, each fixture cites its upstream
   document by URL so the provenance chain stays intact.

This does **not** resolve the municipal-copyright question for the documents
themselves — it concludes that question does not attach to what SIG ingests, because
SIG never takes the documents' expression.

## Decision (operator determination, 2026-09-15)

Approve flips for `ccops_seattle`, `ccops_nyc_post`, `ccops_sf`,
`pathways_rtcc_federation`, `pathways_fr_css_forensics`, and
`pathways_acoustic_drone_location` on the **derived-facts + mandated-disclosure**
basis:

- `spdx = "LicenseRef-DerivedFacts-Citations"` — a local expression for "SIG-authored
  derived facts over cited public records"; `redistributable = false` (the upstream
  content is never redistributed), `derivative_permitted = true` (our derived
  records are SIG's own), `jurisdiction_unknown = false`, `counsel_reviewed =
  false`.
- **The counsel flag is retained.** HG-02 should confirm the municipal-copyright /
  edicts-of-government reading before CCOPS content reaches a published
  compartment — this ADR records the operator's basis, not counsel's sign-off.
- Live targets are added only where a real supported fetch path exists; sources
  whose upstream is PDF/HTML needing a document adapter stay replay/shadow-only
  until that adapter lands.

## Consequences

- Six previously-gated sources become loadable under a recorded, honest basis —
  with the derived-facts boundary (never re-host upstream bytes) now an ADR-pinned
  invariant, not an informal practice.
- The `LicenseRef-DerivedFacts-Citations` expression is reusable for future
  mandated-disclosure sources (additional CCOPS jurisdictions).
- Counsel review (HG-02) remains outstanding; the flag in `sources.toml` and this
  ADR make that explicit rather than implied.

## Revisit trigger

Revisit if counsel (HG-02) rules the derived-facts boundary insufficient for
municipal records, if a CCOPS/pathways connector is changed to ingest upstream
document bytes (at which point the municipal-copyright question attaches and a
new basis is required), or if a jurisdiction retracts or licenses a mandated
disclosure corpus under express terms.
