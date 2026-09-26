# Rights-review packet — `documentcloud` (DocumentCloud API / api.www.documentcloud.org)

> Facts (quoted terms + retrieval date) are separated from judgement (the Decision
> line). This packet asserts no legal conclusion (defining standard §3.1). Reading the
> terms page is permitted research, not ingestion; no source *content* was fetched
> beyond the anonymous API index probe recorded below.

- **Source id:** `documentcloud`
- **Homepage:** https://api.www.documentcloud.org/api/documents/search/
- **Terms URL(s):** https://www.muckrock.com/tos/ — the MuckRock Foundation Terms &
  Conditions; they expressly govern "MuckRock, FOIA Machine, or DocumentCloud
  ('MuckRock Services')". (documentcloud.org serves no separate ToS document:
  `/terms` and `/tos` answer 404, 2026-09-17.) No API-specific licence grant was
  found published with the API docs this pass.
- **robots.txt:** honor — api.www.documentcloud.org robots.txt is `Disallow: /`
  for crawl mode (P26.2 finding); under ADR-087 that remains a hard refusal —
  the 4xx carve-out does not apply (the host answers a real policy, not 4xx).

## Terms (verbatim, retrieved 2026-09-17)

> "License and Access — Subject to your compliance with these Terms and your
> payment of any applicable fees, MuckRock grants you a limited, non-exclusive,
> non-transferable, non-sublicensable license to access and make use of MuckRock
> Services. This license does not include any resale or commercial use of any
> MuckRock Services, or its contents; any downloading or copying of account
> information for the benefit of another public records request service; any
> derivative use of any MuckRock Service or its contents; or **any use of data
> mining, robots, or similar data gathering and extraction tools**. All rights not
> expressly granted to you in these Terms are reserved and retained by MuckRock or
> its licensors, rights holders, or other content providers."

> "Any content that you may receive from other users of MuckRock Services, is
> provided to you AS IS for your information and **personal use only** and you
> agree not to use, copy, reproduce, distribute, transmit, broadcast, display,
> sell, license or otherwise exploit such content for any purpose, without the
> express written consent of the person who owns the rights to such content."

## SPDX candidate

`UNDETERMINED` — no source-level licence; the access licence expressly excludes
automated extraction, and per-document rights belong to each uploader.

## redistributable analysis

The ToS grants no redistribution right over user content (personal use only;
express written consent of the rights-holder required). → registry
`redistributable = false`.

## derivative_permitted analysis

No derivative use licensed ("any derivative use of any MuckRock Service or its
contents" is excluded from the grant). → registry `derivative_permitted = false`.

## ODbL compartment implications

Not OSM-derived. No ODbL implication.

## Custody posture recommendation

LINK (cite/locator only) until a per-document or per-tenant rights basis is
reviewed — or an affirmative DocumentCloud API grant is produced.

## Access note (2026-09-17, live-verified)

`api.www.documentcloud.org/api/` answers its anonymous endpoint index (HTTP 200);
the targeted document path (`/api/documents/20504557/`) serves keyless — but the
ToS access licence excludes "data mining, robots, or similar data gathering and
extraction tools", and robots.txt disallows crawl mode. Public reachability is
not a licence (§3.1).

## Decision

- [ ] permit ingestion — **declined.** Reviewer: maintainer (delegated), date:
  2026-09-17. The reviewed terms are *affirmatively restrictive* (automated
  extraction expressly excluded; user content personal-use-only) — there is no
  GL-GATE-06-covered basis to flip. `ingestion_permitted` stays `false`.
- SPDX recorded: `UNDETERMINED` — no licence to record.

## Counsel-needed flag

**YES for a flip** — lifting the gate needs an operator/counsel decision
(e.g. a per-document rights review of named documents, or an affirmative
DocumentCloud API licence grant). Tracked under D-SOURCES.2-2.
