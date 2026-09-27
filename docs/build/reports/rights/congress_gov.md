# Rights-review packet — `congress_gov` (Congress.gov API / Library of Congress)

> Facts (quoted terms + retrieval date) are separated from judgement (the Decision
> line). This packet asserts no legal conclusion (defining standard §3.1). Reading the
> terms page is permitted research, not ingestion; no source *content* was fetched for
> this review beyond the documentation and bounded auth/shape probes recorded in the
> P26.12 run ledger. Drafted 2026-09-18 for P26.12 (SOURCES.11).

- **Source id:** `congress_gov`
- **Homepage:** https://api.congress.gov/ (documentation: https://github.com/LibraryOfCongress/api.congress.gov)
- **Terms URL(s) fetched:** the published API README (Library of Congress, on GitHub) —
  retrieved 2026-09-18; api.data.gov key-signup terms apply to the key itself (HG-09 —
  the same staged `SIG_DATA_GOV_KEY` already reviewed for `fbi_cde_agency_registry`,
  P26.4). Possessing the key is auth, not the rights basis.
- **robots.txt:** honor — API-mode access per ADR-083 (`api.congress.gov` `/v3` on the
  allow-list; `counsel_reviewed = false`).

## Terms (verbatim)

> "The Congress.gov Application Programming Interface (API) provides a method for
> Congress and the public to view, retrieve, and re-use machine-readable data from
> collections available on Congress.gov." — api.congress.gov README, retrieved 2026-09-18

> "The rate limit is set to 5,000 requests per hour." — README, retrieved 2026-09-18

> "By default, the API returns 20 results starting with the first record. The 20 results
> limit can be adjusted up to 250 results. If the limit is adjusted to be greater than
> 250 results, only 250 results will be returned. The offset, or the starting record,
> can also be adjusted to be greater than 0." — README, retrieved 2026-09-18

> "An API key is required for access. Sign up for a key here. Learn more on how you can
> use your API key to access the Congress.gov API on api.data.gov." — README,
> retrieved 2026-09-18

Congress.gov bill/resolution metadata (titles, numbers, chambers, dates, actions) is a
work of the U.S. federal government (Library of Congress, with chamber data delivered
by the House and Senate). U.S. Government works are not subject to domestic copyright
protection (17 U.S.C. §105); the data are in the public domain, served through the
documented public API under its published rate-limit policy. This packet records that
fact; the SPDX expression is a reviewer decision.

## SPDX candidate

`CC0-1.0 candidate (US-PD)` (accepted expressions per `policy/data/licenses.toml`) —
the same disposition as `usaspending` and `fbi_cde_agency_registry`.

## redistributable analysis

U.S. federal public-domain ⇒ freely redistributable; the API's stated purpose is
re-use of the machine-readable data. → registry `redistributable = true` on the
reviewer's flip.

## derivative_permitted analysis

No copyright ⇒ no derivative restriction. Bill-index rows (congress, type, number,
title, chamber, latest action) feed typed `legislative_bill` claims under the reviewed
legislation vocabulary — metadata only, no person-naming predicates.

## ODbL compartment implications

Not OSM-derived. CC0/US-PD relicensable into any compartment.

## Custody posture recommendation

**REFERENCE** — the bill index as reference data; document locators point back to
congress.gov public pages and the API URL. A federal bill is PROPOSED law: records land
as `index_only` evidence links or typed `legislative_bill` claims — never a §11.14
`LegalInstrument`, never asserted as enacted law (§3.1).

## Decision

- [x] permit ingestion — reviewer: maintainer (delegated), operator-approved 2026-09-18 (P26.12)
- SPDX to record: `CC0-1.0`   rights_reviewed_by (role, never a name): maintainer (delegated)   rights_reviewed_on: 2026-09-18

## Counsel-needed flag

**LOW — U.S. federal public-domain works served by a documented public API whose stated
purpose is re-use; the reviewer confirms the SPDX expression (CC0-1.0) per
licenses.toml.**
