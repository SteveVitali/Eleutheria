# Rights-review packet — `ccops_sf` (SIG-LIC-001, P24.7 / CCOPS.1)

> Facts (quoted terms + retrieval date) are kept separate from judgement (the reviewer
> decision line). This packet asserts **no** legal conclusion (§3.1). Reading a terms/robots
> page is permitted research, **not** ingestion; source *content* is not fetched. Contact
> channels are organisational addresses only — no personal names (Part VIII §0.7).

- **Source id:** `ccops_sf`
- **Class:** `government_mandated_disclosure` (SIG-INGEST-049) — municipal records statutorily
  published under SF Administrative Code Chapter 19B.
- **Homepage:** https://www.sf.gov/surveillance-technology-inventory
- **Terms URL(s) fetched:** not fetched this pass (fixture excerpts a public mandated disclosure
  already cited in the research cache; per-document URLs in
  `tests/connectors/fixtures/ccops/SOURCES.md`)
- **robots.txt:** honor — not evaluated live this pass (no live fetch, HG-03 pending)

## Terms (verbatim)

> Not fetched this pass. The biannual inventory reports are documents the City and County of
> San Francisco is *required by ordinance* to publish. Municipal records posted for public
> access are not thereby dedicated to the public domain — copyright posture **not resolved** in
> this packet; per-document terms are recorded per fixture.

## SPDX candidate

`UNDETERMINED` (municipal record; copyright posture unresolved pending review).

## redistributable analysis

Separately reviewed (never derived from SPDX — SIG-LIC-003). Unreviewed → `redistributable = false`;
the export gate fails closed (SIG-LIC-004). SIG holds REFERENCE posture: resolve identifiers
and citations, do not re-host content.

## derivative_permitted analysis

Undetermined pending review. Fixtures are short paraphrased fact carriers, not verbatim re-hosting;
extracted facts (inventory statuses, the compliance metric) are un-copyrightable facts in US
practice, but the packet does not assert that conclusion.

## ODbL compartment implications

Not OSM-derived.

## Custody posture recommendation

REFERENCE (§8.4) — SIG stores derived identifiers + citations and never fetches/stores content
until a rights review + operator flip. Live run refuses (exit 3) while the gate stands.

## Decision

- [x] permit ingestion — reviewer: maintainer (delegated), operator-approved 2026-09-15 (ADR-085)
- SPDX to record: `LicenseRef-DerivedFacts-Citations`   rights_reviewed_by (role, never a name): maintainer (delegated)   rights_reviewed_on: 2026-09-15
- **Status:** FLIPPED 2026-09-15 on the municipal-mandated-disclosure + derived-facts basis (ADR-085): the connector emits derived facts and citations and never re-hosts the ordinance PDFs. Counsel flag retained for HG-02 (municipal-copyright reading of the documents themselves is outstanding — it does not attach to SIG's derived-facts records, but counsel confirms before a published compartment).

## Counsel-needed flag

PARTIAL — SIG-LIC-009: municipal-record copyright posture (the City and County of San
Francisco's terms for Chapter 19B publications) warrants review before any flip.

**HG-02 resolved 2026-09-16 (counsel, operator-reported):** derived facts/citations publishable — dedicated `derived_facts` compartment (ADR-086); `redistributable` flipped to true on the registry record (it gates SIG's emitted claims; upstream bytes are still never re-hosted — architectural, not flag-borne).
