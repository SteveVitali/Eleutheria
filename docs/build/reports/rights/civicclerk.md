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

`CC0-1.0`  (accepted expressions per `policy/data/licenses.toml`)

## redistributable analysis

The RECORDS (agendas/minutes/video indexes) are municipal public records — redistributable on the same basis as `okc_council` (GL-GATE-06, 2026-09-16). The vendor platform ToS constrains the ACCESS METHOD, not the record rights.  → registry `redistributable = true`.

## derivative_permitted analysis

Public-record derivatives permitted (same basis as `okc_council`).  → registry `derivative_permitted = true`.

## ODbL compartment implications

Not OSM-derived. No ODbL implication.

## Custody posture recommendation

REFERENCE (fetch published agendas/minutes for the tenant jurisdiction).

## Access note (2026-09-16, honest)

The v1 API template `{tenant}.api.civicclerk.com/v1` is confirmed from the portal JS, but anonymous reads 404 on every probed tenant and the api host serves no robots.txt — the tenant surface is IdentityServer-gated (the portal obtains a session). A working access path is unresolved (HG-09 class decision); the live target records the posture, nothing is faked.

## Decision

- [x] permit ingestion — reviewer: maintainer (delegated) date: 2026-09-16
- SPDX recorded: `CC0-1.0`   rights_reviewed_by: maintainer (delegated)   rights_reviewed_on: 2026-09-16

## Counsel-needed flag

**NO — public-record rights resolved under GL-GATE-06; the access-path question (IdentityServer session) is HG-09-class engineering, not a rights blocker.**
