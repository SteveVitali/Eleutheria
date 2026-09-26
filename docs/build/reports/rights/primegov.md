# Rights-review packet — `primegov` (PrimeGov PublicPortal API)

> Facts (quoted terms + retrieval date) are separated from judgement (the Decision
> line). This packet asserts no legal conclusion (defining standard §3.1). Reading the
> terms page is permitted research, not ingestion; no source *content* was fetched.

- **Source id:** `primegov`
- **Homepage:** https://<tenant>.primegov.com/api/v2/PublicPortal/
- **Terms URL(s):** https://lacity.primegov.com/Portal/MeetingAccessAndMarkup — the tenant's public meeting-access page; no licence document is served.
- **robots.txt:** honor — lacity.primegov.com serves `Disallow: /` for the default agent; every fetch refuses in crawl mode (a recorded politeness_refusal). An API-mode basis (ADR-083) is not yet recorded for the PublicPortal surface.

## Terms (verbatim)

> The PublicPortal API serves municipal meeting records (meetings, agendas,
> supporting documents) — US local-government public records, the same basis as
> `okc_council` (GL-GATE-06, 2026-09-16). The vendor (PrimeGov/Granicus-class)
> platform terms govern the ACCESS METHOD, not the record rights.
>
> No vendor licence document was quoted verbatim this pass; none is served on the
> tenant portal. This packet records the public-record basis only (§3.1).

## SPDX candidate

`CC0-1.0`  (accepted expressions per `policy/data/licenses.toml`)

## redistributable analysis

Municipal meeting records are public records — redistributable on the same basis as `okc_council` (GL-GATE-06).  → registry `redistributable = true`.

## derivative_permitted analysis

Public-record derivatives permitted (same basis as `okc_council`).  → registry `derivative_permitted = true`.

## ODbL compartment implications

Not OSM-derived. No ODbL implication.

## Custody posture recommendation

REFERENCE (fetch published meeting indexes for verified tenant jurisdictions).

## Access note (2026-09-16, live-verified)

`https://lacity.primegov.com/api/v2/PublicPortal/` answers (verified); the same
host's robots.txt is `Disallow: /`, so every fetch in crawl mode is a recorded
politeness_refusal — the refusal stands, it is never worked around.

## Decision

- [x] permit ingestion — reviewer: maintainer (delegated) date: 2026-09-16
- SPDX recorded: `CC0-1.0`   rights_reviewed_by: maintainer (delegated)   rights_reviewed_on: 2026-09-16

## Counsel-needed flag

**NO — municipal public-record rights resolved under GL-GATE-06; the robots posture is an access fact, not a rights blocker.**
