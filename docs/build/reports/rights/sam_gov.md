# Rights-review packet — `sam_gov` (SAM.gov public APIs)

> Facts (quoted terms + retrieval date) are separated from judgement (the Decision
> line). This packet asserts no legal conclusion (defining standard §3.1). Reading the
> terms page is permitted research, not ingestion; no source *content* was fetched.

- **Source id:** `sam_gov`
- **Homepage:** https://api.sam.gov/
- **Terms URL(s):** https://open.gsa.gov/api/sam-opportunities/ — GSA's documented public API surface (opportunities v2).
- **robots.txt:** honor — api.sam.gov is an API endpoint, not a crawl surface; API mode applies (api_allowlist.toml records the basis).

## Terms (verbatim)

> SAM.gov is a US federal government system operated by the General Services
> Administration. Federal government works are public domain (17 U.S.C. §105) —
> the same basis recorded for `usaspending` (GL-GATE-06, 2026-09-16). The
> opportunities API is GSA's documented public API for federal procurement
> notices.
>
> No verbatim licence text is served by api.sam.gov; the public-domain basis is
> statutory (17 U.S.C. §105). This packet records that basis only (§3.1).

## SPDX candidate

`CC0-1.0`  (accepted expressions per `policy/data/licenses.toml`)

## redistributable analysis

US federal government data — public domain; redistributable (same basis as `usaspending`, GL-GATE-06).  → registry `redistributable = true`.

## derivative_permitted analysis

Public-domain derivatives permitted (same basis as `usaspending`).  → registry `derivative_permitted = true`.

## ODbL compartment implications

Not OSM-derived. No ODbL implication.

## Custody posture recommendation

REFERENCE (bounded opportunity searches + entity lookups over the documented API).

## Access note (2026-09-16, honest)

The opportunities API requires a free registered key — resolved from
`$SIG_SAM_GOV_KEY` at fetch time (HG-09; env only, never committed). Keyless the
API answers 404 — a recorded disappearance, not an error to work around. The key
is an access credential; it does not change the rights basis.

## Decision

- [x] permit ingestion — reviewer: maintainer (delegated) date: 2026-09-16
- SPDX recorded: `CC0-1.0`   rights_reviewed_by: maintainer (delegated)   rights_reviewed_on: 2026-09-16

## Counsel-needed flag

**NO — federal public-domain rights resolved under GL-GATE-06.**
