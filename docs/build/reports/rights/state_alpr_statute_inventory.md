# Rights-review packet — state_alpr_statute_inventory (SIG-LIC-001, P27.2)

- **Source id:** `state_alpr_statute_inventory`
- **Homepage:** https://www.ncsl.org/technology-and-communication/automated-license-plate-readers
- **Terms URL(s) fetched:** https://www.ncsl.org/terms-of-use — **re-fetch attempted 2026-09-22;
  NCSL serves a Cloudflare challenge (`403`, "Just a moment…") to non-browser fetches** — the
  live capture row records those challenge bytes honestly (http_status 403). The one-time seed
  ran 2026-09-13 (P24.7 tail; claims already in the spine). The terms record for this packet is
  the NCSL terms-of-use URL above + this documented capture outcome.
- **robots.txt:** `honor` — NCSL robots was honoured; no content fetch is made this pass
  (the seed already ran; this review touches rights only).

## What the seed actually emitted (the thing being licensed)

The `state_statute_seed` claims are **derived facts and citations** extracted from the inventory
page: per-state `jurisdiction`, `instrument_type`, `effective_from`, `external_id` (the statute
citation), `citation`, `as_of`. SIG never re-hosts the NCSL page's prose — the claims are facts
(statute X governs ALPR in state Y, effective Z) plus the citation that lets a reader check the
primary instrument themselves.

## Terms (verbatim)

The NCSL terms-of-use page could not be re-captured this pass (Cloudflare challenge, recorded
above). Facts: NCSL is a **private nonprofit**, not a government body — the
public-record/factual-compilation basis does **not** apply to its page; the statutes it cites
are primary law (unambiguously public), and SIG's claims cite those instruments rather than
re-hosting NCSL's text.

## SPDX candidate

`LicenseRef-DerivedFacts-Citations` — the ADR-085/ADR-086 counsel-resolved basis: SIG emits
derived facts and citations, never re-hosts the upstream expressive content. This is the same
basis the counsel-reviewed document sources (`ccops_*`, `madada`, `pathways_*`, `carnegie_ai_gsi`,
`facial_recognition_world_map`) already publish under.

## redistributable analysis

`true` — for the *derived claims* only. The upstream NCSL page bytes are never redistributed
(custody DERIVE; the seed keeps citations, not page text). Statute citations and
state/instrument/date facts are not copyrightable expression.

## derivative_permitted analysis

`true` — the claims ARE the derivative (derived facts); no upstream bytes are re-hosted, so no
linking/reproduction hazard (SIG-INGEST-048b) arises.

## ODbL compartment implications

Not OSM-derived — no ODbL implications. Ships in the `derived_facts` compartment
(`LicenseRef-DerivedFacts-Citations`).

## Custody posture recommendation

`DERIVE` — SIG holds derived facts + citations; the upstream page is referenced, never mirrored.
(Registry row updated: MIRROR → DERIVE, matching what the seed actually does.)

## Decision

- [x] permit ingestion — reviewer: `maintainer (delegated)` date: 2026-09-22
- SPDX to record: `LicenseRef-DerivedFacts-Citations`   rights_reviewed_by (role, never a name):
  `maintainer (delegated)`   rights_reviewed_on: 2026-09-22
- Gate basis: **HG-03 answered 2026-09-22 ("Approve under GL-GATE-07")** for the audited
  UNDETERMINED buckets; the derived-facts basis is the counsel-cleared pattern (ADR-085/086)
  applied to the one unreviewed tail source.

## Counsel-needed flag

NO-NEW — the derived-facts publication posture is already counsel-resolved (ADR-086). Counsel
(HG-02 proper) remains an operator action under the interim/no-counsel posture (D-LEGAL.1-1);
this packet adds a *source* to an already-cleared basis, it does not create a new legal theory.
