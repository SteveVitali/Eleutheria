# Rights-review packet — `pathways_fr_css_forensics` (SIG-LIC-001, P21.1/P21.9)

> Facts (quoted terms + retrieval date) are kept separate from judgement (the reviewer
> decision line). This packet asserts **no** legal conclusion (§3.1). Reading a terms/robots
> page is permitted research, **not** ingestion; source *content* is not fetched. Contact
> channels are organisational addresses only — no personal names (Part VIII §0.7).

- **Source id:** `pathways_fr_css_forensics`
- **Homepage:** https://www.eff.org/pages/atlas-surveillance
- **Terms URL(s) fetched:** not fetched this pass (fixtures excerpt public documents already
  cited in the research cache; per-document URLs in `tests/connectors/fixtures/pathways/SOURCES.md`)
- **robots.txt:** honor — not evaluated live this pass (no live fetch, HG-03 pending)

## Terms (verbatim)

> Not fetched this pass. This source is the P17.2 FR/CSS/forensics pathway family (facial-recognition policies, cell-site-simulator procurement, mobile-device-forensics contracts, and federal authorization court orders). The underlying documents are public agency policies, procurement records, and court orders; their individual terms are per-document and recorded per fixture.

## SPDX candidate

`UNDETERMINED` (per-document; mixed government-record + vendor-disclosure + advocacy).

## redistributable analysis

Separately reviewed (never derived from SPDX — SIG-LIC-003). Unreviewed → `redistributable = false`;
the export gate fails closed (SIG-LIC-004). SIG holds LINK posture: link out, do not re-host.

## derivative_permitted analysis

Undetermined pending review. Fixtures are short paraphrased fact carriers, not verbatim re-hosting.

## ODbL compartment implications

Not OSM-derived.

## Custody posture recommendation

LINK (§8.4) — SIG links out and never fetches/stores source content until a rights review + operator
flip. A content-fetching connector MUST NOT run against it (loader gate refuses; live run exit 3).

## Decision

- [ ] permit ingestion — reviewer: ____ date: ____
- SPDX to record: ____   rights_reviewed_by (role, never a name): ____   rights_reviewed_on: ____
- **Status:** rights UNDETERMINED, `ingestion_permitted = false`. HG-03/HG-04 **pending** (P21.9 ships
  over committed fixtures; no source flipped).

## Counsel-needed flag

PARTIAL — SIG-LIC-009: per-document terms (vendor press releases vs government records vs advocacy)
warrant per-document review before any flip.
