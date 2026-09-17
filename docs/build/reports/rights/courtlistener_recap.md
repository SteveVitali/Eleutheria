# Rights-review packet — `courtlistener_recap` (CourtListener REST API / RECAP)

> Facts (quoted terms + retrieval date) are separated from judgement (the Decision
> line). This packet asserts no legal conclusion (defining standard §3.1). Reading the
> terms page is permitted research, not ingestion; the only API call made was a
> keyless probe recorded below (401 — no content returned).

- **Source id:** `courtlistener_recap`
- **Homepage:** https://www.courtlistener.com/api/rest/v4/
- **Terms URL(s):** https://free.law/membership/allowed-api-usage (retrieved
  2026-09-17, HTTP 200) — the Free Law Project "Membership-Based API Usage
  Restrictions" that govern CourtListener API access. www.courtlistener.com
  itself answered 403 (CloudFront "Request blocked") from the SIG review
  vantage — the FLP site carries the operative access terms.
- **robots.txt:** honor — www.courtlistener.com/robots.txt answered 403
  (CloudFront request-blocked) from this vantage; under ADR-087 a 4xx means no
  policy exists — but the source's *rights* gate refuses regardless (see
  Decision), and the targeted API path 401s without a credential.

## Terms (verbatim, retrieved 2026-09-17)

> "Membership-based API access is intended for personal, educational, research,
> journalistic, and exploratory use. Solo practitioners and law firms with five
> or fewer attorneys are welcome… Small government use — a researcher at an
> agency, a clerk pulling dockets, a public defender's office — is welcome…
> Small organizations that are pre-revenue and unfunded are welcome…"

> "Membership-based API access **may not be used to build tools for for-profit
> or non-profit organizations, even if those tools aren't sold outside the
> company. We consider internal tooling that supports an organization's
> operation to be commercial use**…"

> "One person, one account. Do not create multiple accounts to expand your
> access. Please don't share API keys across people or organizations."

> "Commercial users should contact our partnerships team to set up an agreement
> that fits the use case."

## SPDX candidate

`UNDETERMINED` for the access layer. The *content* — US court records / RECAP
dockets — is public-record material, but the published access terms gate it
behind a membership agreement that, as written, does not clearly cover SIG's
use (a tool built for an organization) — the commercial/partnership tier is
the terms' own answer for that case.

## redistributable analysis

Court records are public-record material; the API access compact is a separate
question from content rights. Until the compact is resolved, no redistribution
posture is asserted → registry `redistributable` stays unset/false.

## derivative_permitted analysis

Same: not asserted under unresolved access terms.

## ODbL compartment implications

Not OSM-derived. No ODbL implication.

## Custody posture recommendation

LINK until the operator resolves the FLP agreement (membership vs. partnership
tier) and provisions the credential.

## Access note (2026-09-17, live-verified)

`GET /api/rest/v4/dockets/5/` keyless → `401 {"detail":"Authentication
credentials were not provided."}` — the API is credential-gated; the connector
path (targeted docket lookups only, SIG-INGEST-036/037) exists for a future
flip, and the gate refuses live fetches meanwhile.

## Decision

- [ ] permit ingestion — **declined.** Reviewer: maintainer (delegated), date:
  2026-09-17. The content basis is resolvable (public court records), but the
  *access compact* is an operator decision: accepting the FLP membership
  agreement — which as written excludes building tools for organizations — or
  arranging the partnership tier, plus holding the API credential (HG-09
  class). Not GL-GATE-06-coverable. `ingestion_permitted` stays `false`.
- SPDX recorded: `UNDETERMINED` — no licence to record.

## Counsel-needed flag

**YES for a flip** — an operator decision on the FLP agreement tier plus the
credential. Tracked under D-SOURCES.2-2.
