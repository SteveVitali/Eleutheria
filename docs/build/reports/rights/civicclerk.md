# Rights-review packet — `civicclerk` (CivicClerk agenda platform)

> Facts (quoted terms + retrieval date) are separated from judgement (the Decision
> line). This packet asserts no legal conclusion (defining standard §3.1). Reading the
> terms page is permitted research, not ingestion; no source *content* was fetched.

- **Source id:** `civicclerk`
- **Homepage:** https://<tenant>.api.civicclerk.com/v1/Events
- **Terms URL(s):** https://www.civicclerk.com/
- **robots.txt:** honor (per-tenant portal; the OKC tenant is oklahomacityok, agenda_tenants.toml).

## Terms (verbatim)

> UNDETERMINED — no resolved rights block in the registry (SIG-LIC-004; fails the
> export gate closed). CivicClerk is the vendor agenda/meeting platform; okc_council flows through its oklahomacityok tenant. The PUBLISHED RECORDS (agendas/minutes/video) are government public records; the CivicClerk PLATFORM terms of service govern automated access and were not fetched this pass. The reviewer must separate the public-record rights (government) from the vendor ToS (access-method constraint).
>
> Terms were NOT fetched verbatim for this source this pass; the terms_url is
> recorded for the reviewer to fetch and quote before any flip. This packet makes
> no assertion about the licence (defining standard §3.1 — no synthetic certainty).

## SPDX candidate

`UNDETERMINED`  (accepted expressions per `policy/data/licenses.toml`)

## redistributable analysis

Government public records are redistributable; the vendor platform ToS may constrain the ACCESS METHOD (rate/robots), not the record rights. redistributable=false until reviewed.  → registry `redistributable = false`.

## derivative_permitted analysis

Public-record derivatives permitted; confirm the vendor ToS does not forbid bulk automated extraction.  → registry `derivative_permitted = false`.

## ODbL compartment implications

Not OSM-derived. No ODbL implication.

## Custody posture recommendation

REFERENCE (fetch published agendas/minutes for the tenant jurisdiction).

## Decision

- [ ] permit ingestion — reviewer: ____ date: ____
- SPDX to record: `UNDETERMINED`   rights_reviewed_by (role, never a name): ____   rights_reviewed_on: ____

## Counsel-needed flag

**PARTIAL — public-record rights are clear; the vendor ToS automated-access clause needs a read.**
