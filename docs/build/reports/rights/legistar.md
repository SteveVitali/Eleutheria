# Rights-review packet — `legistar` (Granicus Legistar InSite API)

> Facts (quoted terms + retrieval date) are separated from judgement (the Decision
> line). This packet asserts no legal conclusion (defining standard §3.1). Reading the
> terms page is permitted research, not ingestion; no source *content* was fetched.

- **Source id:** `legistar`
- **Homepage:** https://webapi.legistar.com/v1/<client>/
- **Terms URL(s):** https://webapi.legistar.com/ — the API host publishes no terms document; it is the documented public read surface behind every InSite tenant portal.
- **robots.txt:** honor — webapi.legistar.com serves no robots.txt; API mode applies (api_allowlist.toml records the basis).

## Terms (verbatim)

> The InSite API serves municipal legislative records (matters, events, histories,
> attachments) — US local-government public records. No licence document is served
> by the API host; the records' rights resolve as municipal public records, the same
> basis as `okc_council` (GL-GATE-06, 2026-09-16). The vendor (Granicus) platform ToS
> governs the ACCESS METHOD, not the record rights.
>
> No vendor terms page was quoted verbatim this pass; the API host serves none. This
> packet records the public-record basis only — no assertion about the licence of
> the platform software itself (defining standard §3.1).

## SPDX candidate

`CC0-1.0`  (accepted expressions per `policy/data/licenses.toml`)

## redistributable analysis

Municipal legislative records are public records — redistributable on the same basis as `okc_council` (GL-GATE-06).  → registry `redistributable = true`.

## derivative_permitted analysis

Public-record derivatives permitted (same basis as `okc_council`).  → registry `derivative_permitted = true`.

## ODbL compartment implications

Not OSM-derived. No ODbL implication.

## Custody posture recommendation

REFERENCE (fetch published matters/events for verified tenant jurisdictions).

## Access note (2026-09-16, live-verified)

`/v1/<tenant>/Matters` and `/v1/<tenant>/Events` answer JSON for `seattle`,
`mesa`, `sanantonio` (recorded in `agenda_tenants.toml`); `chicago` is NOT
provisioned on the shared host (a recorded tenant_api_error, not a bypass).

## Decision

- [x] permit ingestion — reviewer: maintainer (delegated) date: 2026-09-16
- SPDX recorded: `CC0-1.0`   rights_reviewed_by: maintainer (delegated)   rights_reviewed_on: 2026-09-16

## Counsel-needed flag

**NO — municipal public-record rights resolved under GL-GATE-06.**
