# Rights-review packet — `muckrock` (MuckRock records API)

> Facts (quoted terms + retrieval date) are separated from judgement (the Decision
> line). This packet asserts no legal conclusion (defining standard §3.1). Reading the
> terms page is permitted research, not ingestion; no source *content* was fetched.
> Drafted 2026-09-15 in the B rights-review pass (the packet did not exist before).

- **Source id:** `muckrock`
- **Homepage:** https://www.muckrock.com/api/
- **Terms URL(s) fetched:** https://www.muckrock.com/api/ — retrieved 2026-09-15
- **robots.txt:** honor — API-mode access per ADR-083 (host `www.muckrock.com`, prefix `/api`,
  on the allow-list; `counsel_reviewed = false`).

## Terms (verbatim)

> Fetched from https://www.muckrock.com/api/ on 2026-09-15 (the API documentation page —
> permitted research, not record content):
>
> "The MuckRock API, or application programming interface, provides a way to access
> MuckRock data programmatically."
>
> "All endpoints aside from the users and organizations endpoints are subject to an
> overall 15 requests/minute rate limit, with bursts of up to 100 requests allowed
> before rate limiting starts."
>
> "All requests to the MuckRock API must use an identifiable user agent in the headers
> that uniquely identifies your automation and includes a real point of contact …
> Requests made using browser user agents are strictly forbidden."
>
> "Authentication is done using MuckRock Accounts access tokens. To retrieve your first
> access token, you must authenticate using username and password with a POST to
> https://accounts.muckrock.com/api/token/ … The access token is valid for 5 minutes …
> POST the refresh token … to https://accounts.muckrock.com/api/refresh/."
>
> The API serves FOIA **request metadata** (requests, communications, files, agencies,
> jurisdictions) and **released government records**. MuckRock's editorial policy
> (muckrock.com/news/editorial-policy/) states some published assets are Creative
> Commons; the underlying released records are U.S. government public-records
> disclosures — their posture follows the issuing agency/jurisdiction, recorded
> per document, not a single site licence.

## SPDX candidate

`UNDETERMINED` (per-document for released records; the request/agency metadata listing
is MuckRock's own index data under its API ToS — a `LicenseRef-` expression or
accepted-set amendment is a reviewer/counsel decision, not guessed here).

## redistributable analysis

Separately reviewed (SIG-LIC-003). Request/agency metadata is reference-grade index data;
released-document contents carry the issuing jurisdiction's records posture (US public
records are generally not copyright-restricted, but state/municipal posture varies).
→ registry `redistributable` set per the reviewer decision; the safe default is
metadata-only redistribution.

## derivative_permitted analysis

Aggregate/derived claims (agency records-availability, request outcomes, response
latency) carry no linking hazard at REFERENCE posture (SIG-INGEST-048b).

## ODbL compartment implications

Not OSM-derived.

## Custody posture recommendation

**REFERENCE** — store request/agency metadata + citations; re-host released documents
only per-document under their own posture. The JWT refresh flow is P25.2 code work;
the staged refresh token is a credential input, not a rights basis.

## Decision

- [x] permit ingestion — reviewer: maintainer (delegated), operator-approved 2026-09-15 (B pass)
- SPDX to record: `LicenseRef-MuckRock-API-ToS`   rights_reviewed_by (role, never a name): maintainer (delegated)   rights_reviewed_on: 2026-09-15
- Recorded `redistributable = false` / `derivative_permitted = false`: ingestion (REFERENCE
  capture, metadata + citations) is permitted under the API ToS; the export gate fails
  closed on the non-registered expression until the per-document records posture is
  resolved (PARTIAL counsel, HG-02).

## Counsel-needed flag

**PARTIAL — SIG-LIC-009:** the metadata-listing licence expression and the
per-document released-records posture warrant review; the API ToS itself is clear
(rate limits, identifiable UA, token auth — all honoured by design).
