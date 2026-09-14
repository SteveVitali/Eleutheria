# Rights-review packet — `ccops_nyc_post` (SIG-LIC-001, P24.7 / CCOPS.1)

> Facts (quoted terms + retrieval date) are kept separate from judgement (the reviewer
> decision line). This packet asserts **no** legal conclusion (§3.1). Reading a terms/robots
> page is permitted research, **not** ingestion; source *content* is not fetched. Contact
> channels are organisational addresses only — no personal names (Part VIII §0.7).

- **Source id:** `ccops_nyc_post`
- **Class:** `government_mandated_disclosure` (SIG-INGEST-049) — municipal records statutorily
  published under the POST Act (NYC Admin. Code § 14-189).
- **Homepage:** https://www.nyc.gov/site/nypd/about/about-nypd/policy/post-act.page
- **Terms URL(s) fetched:** not fetched this pass (fixture excerpts a public mandated disclosure
  already cited in the research cache; per-document URLs in
  `tests/connectors/fixtures/ccops/SOURCES.md`)
- **robots.txt:** honor — not evaluated live this pass (no live fetch, HG-03 pending)

## Terms (verbatim)

> Not fetched this pass. The 42 impact & use policies are documents the NYPD is *required by
> local law* to publish (synchronised 2026-02-04 revision). Municipal records posted for public
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
extracted facts (clause topics, field values) are un-copyrightable facts in US practice, but the
packet does not assert that conclusion.

## ODbL compartment implications

Not OSM-derived.

## Custody posture recommendation

REFERENCE (§8.4) — SIG stores derived identifiers + citations and never fetches/stores content
until a rights review + operator flip. Live run refuses (exit 3) while the gate stands.

## Decision

- [ ] permit ingestion — reviewer: ____ date: ____
- SPDX to record: ____   rights_reviewed_by (role, never a name): ____   rights_reviewed_on: ____
- **Status:** rights UNDETERMINED, `ingestion_permitted = false`. HG-03/HG-04 **pending** (P24.7
  ships over committed fixtures; no source flipped, no live fetch performed).

## Counsel-needed flag

PARTIAL — SIG-LIC-009: municipal-record copyright posture (the City of New York's terms for
POST Act publications) warrants review before any flip.
