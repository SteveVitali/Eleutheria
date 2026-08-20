# R4 — Primary-evidence acquisition: public records, documents, procurement, and civic meeting systems

**Workstream:** R4
**Researched:** 2026-08-20
**Researcher:** claude-opus-5 (R4 agent)
**Outline sections covered:** §2 Layer F, §8.10, §10.1 Phase 1F, §12, §15.4, §20 (Q7, Q8, Q16, Q26), with incidental corrections to §10.1A and §21
**Outline questions answered:** Q7, Q8, Q16 (partial), Q25 (partial), Q26
**Confidence in this file overall:** high

---

## Scope note and method

Every claim below marked VERIFIED was produced by an actual HTTP request issued during this
session on 2026-08-20 from a US residential IP, or by reading the vendor's own source code
in a public repository. Response bodies are pasted verbatim (truncated where noted, never
paraphrased into a fake sample).

Two environment-level facts shaped the method and are themselves findings:

1. **MuckRock, DocumentCloud, Perma.cc and `flocksafety.com` all sit behind Cloudflare bot
   management that blocks datacenter/residential curl traffic with a 403 interactive
   challenge**, regardless of `User-Agent`. Requests routed through a different egress
   (the `WebFetch` tool) reached the origins and returned real application-layer status
   codes (200 / 401). Any SIG ingestion design must assume Cloudflare interstitials on
   these hosts and budget for a browser-context fetcher, not plain `requests`/`curl`.
2. **`archive.org` `/wayback/available` rate-limited this IP to HTTP 429 for the entire
   session**, while the CDX API on `web.archive.org` worked fine. The availability API is
   not a reliable production dependency.

Retrieval counts: 70+ distinct HTTP retrievals across 30+ hosts.

---

# Part A — MuckRock (outline Q7)

### F4.1 — MuckRock's documented API is **v2**, not the `api_v1` the outline implies

**Claim:** The current, documented MuckRock API is `https://www.muckrock.com/api_v2/`; it is
an OAuth-bearer-token API with a 9-endpoint object model, and `api_v1` is no longer the
documented surface.
**Status:** VERIFIED
**Evidence:**
- `https://www.muckrock.com/api/` (fetched via WebFetch, 2026-08-20) states verbatim:
  > "The current API endpoint is `https://www.muckrock.com/api_v2/`"
- `https://www.muckrock.com/api_v2/` returns a DRF `DefaultRouter` root listing:
  `/api_v2/requests/`, `/api_v2/communications/`, `/api_v2/agencies/`, `/api_v2/files/`,
  `/api_v2/jurisdictions/`, `/api_v2/users/`, `/api_v2/statistics/`,
  `/api_v2/organizations/`, `/api_v2/projects/`
- Direct curl to `https://www.muckrock.com/api_v1/foia/?format=json&search=flock` from this
  IP returned **HTTP 403 with a Cloudflare interactive challenge page** (`cRay:
  a2e2efc70c9ebe83`), i.e. inaccessible without a browser context.
**Retrieved:** 2026-08-20
**Implication for the spec:** The MuckRock connector must target `api_v2` and must not be
built against the older `api_v1` shape that ALPR Watch's 2025 methodology may have used.
**Outline delta:** CORRECTS §2 Layer F and §21 — the outline lists only
`https://www.muckrock.com/` and gives a hand-rolled `records_request` schema. The real
object model is nine typed resources with stable integer IDs, documented below.

### F4.2 — MuckRock API v2 requires authentication for **every** data endpoint, including agencies and jurisdictions

**Claim:** There is no unauthenticated read path to MuckRock data. `/api_v2/agencies/` and
`/api_v2/jurisdictions/` both return HTTP 401.
**Status:** VERIFIED
**Evidence:** WebFetch (which reached origin, bypassing the CF challenge) returned:
- `GET https://www.muckrock.com/api_v2/agencies/` → **HTTP 401 Unauthorized**
- `GET https://www.muckrock.com/api_v2/jurisdictions/` → **HTTP 401 Unauthorized**
- `GET https://www.muckrock.com/api_v1/foia/?format=json&search=flock` → **HTTP 401 Unauthorized**
- `GET https://www.muckrock.com/api_v1/jurisdiction/?format=json` → **HTTP 401 Unauthorized**
**Retrieved:** 2026-08-20
**Implication for the spec:** SIG cannot treat MuckRock jurisdiction/agency IDs as a
*freely dereferenceable* identity anchor. A MuckRock account and a credential-refresh
daemon are hard prerequisites for the Phase-1F connector, and for the Phase-1A identity
registry if MuckRock IDs are used as anchors.
**Outline delta:** CORRECTS §10.1 Phase 1A — the outline lists "MuckRock jurisdiction IDs"
among identity aids without noting that resolving them requires credentials. See F4.14 for
the recommended demotion of MuckRock IDs from anchor to alias.

### F4.3 — MuckRock auth is a 5-minute JWT from a separate accounts host

**Claim:** Access tokens are obtained by POSTing username/password to
`https://accounts.muckrock.com/api/token/` and expire after 5 minutes.
**Status:** VERIFIED (documentation read; token endpoint itself CF-blocked from this IP)
**Evidence:** `https://www.muckrock.com/api/` states verbatim:
  > "Authentication is done using MuckRock Accounts access tokens. To retrieve your first
  > access token, you must authenticate using username and password with a POST to the
  > following endpoint: `https://accounts.muckrock.com/api/token/`"
  > "The access token is valid for 5 minutes after which it will stop working."
  Tokens are passed as bearer tokens in request headers.
  Direct curl to `https://accounts.muckrock.com/api/token/` from this IP → **HTTP 403**
  (Cloudflare "Sorry, you have been blocked", not an app-layer response).
**Retrieved:** 2026-08-20
**Implication for the spec:** REQ — the MuckRock client must implement refresh-on-401 with
a token cache whose TTL is < 5 minutes; a naive "fetch token at job start" design will fail
on any crawl longer than five minutes. Credentials must be stored in a secret manager, not
in the connector config.

### F4.4 — MuckRock rate limits: 15 req/min with a 100-request burst; 5 req/min for users/organizations

**Claim:** MuckRock v2 enforces 15 requests/minute overall with burst-to-100, and a tighter
5 requests/minute with no burst on `/users/` and `/organizations/`.
**Status:** VERIFIED (documentation)
**Evidence:** `https://www.muckrock.com/api/` states verbatim:
  > "All endpoints aside from the users and organizations endpoints are subject to an
  > overall 15 requests/minute rate limit, with bursts of up to 100 requests allowed before
  > rate limiting starts."
  > users and organizations are "limited to 5 requests per minute with no burst available."
  Pagination: > "Our responses are paginated, with a default of 50 items per page. The
  number of results per page can be changed by providing a `page_size` query argument."
**Retrieved:** 2026-08-20
**Implication for the spec:** At 15 req/min × 50 items/page = 750 objects/minute ceiling.
A full agency-table mirror (tens of thousands of agencies) is a multi-hour job; it must be
a scheduled incremental sync with local persistence, never an on-demand lookup in a request
path.

### F4.5 — Exact MuckRock Jurisdiction object schema (the candidate identity anchor)

**Claim:** The MuckRock Jurisdiction object has exactly six fields: `id`, `name`, `slug`,
`abbrev`, `level`, `parent`.
**Status:** VERIFIED (read from MuckRock's own open-source serializer)
**Evidence:** `https://raw.githubusercontent.com/MuckRock/muckrock/master/muckrock/jurisdiction/api_v2/serializers.py`
retrieved 2026-08-20. Verbatim `Meta.fields`:

```python
fields = (
    "id",
    "name",
    "slug",
    "abbrev",
    "level",
    "parent",
)
```

Documented examples embedded in the serializer:

```json
{"id": 1, "name": "California",                "slug": "california",                "abbrev": "CA",  "level": "s", "parent": 3}
{"id": 2, "name": "Los Angeles",               "slug": "los-angeles",               "abbrev": "",    "level": "l", "parent": 1}
{"id": 3, "name": "United States of America",  "slug": "united-states-of-america",  "abbrev": "USA", "level": "f", "parent": null}
```

Help text, verbatim: `level` = "The level of the jurisdiction."; `parent` = "ID of the
parent jurisdiction. This defines the hierarchy between jurisdictions, where a jurisdiction
can have a federal or state parent. **Local jurisdictions cannot be parents.**"
**Retrieved:** 2026-08-20
**Implication for the spec:** The MuckRock jurisdiction hierarchy is only **three levels
deep** (`f` federal → `s` state → `l` local) and *local jurisdictions cannot be parents*.
This is structurally weaker than the real US hierarchy: a county cannot parent a city, a
special district has no natural slot, and there is no FIPS/GEOID field at all. MuckRock
jurisdiction IDs therefore cannot carry SIG's geographic hierarchy.
**Outline delta:** CORRECTS §10.1 Phase 1A. MuckRock jurisdiction IDs are a useful *alias*
(they let SIG join to MuckRock requests) but must not be the canonical jurisdiction key.
Census GEOID must be canonical; MuckRock jurisdiction id becomes a crosswalk column.

### F4.6 — Exact MuckRock Agency object schema

**Claim:** The MuckRock Agency object has exactly ten fields: `id`, `name`, `slug`,
`status`, `exempt`, `types`, `requires_proxy`, `jurisdiction`, `parent`, `appeal_agency`.
**Status:** VERIFIED (source)
**Evidence:** `https://raw.githubusercontent.com/MuckRock/muckrock/master/muckrock/agency/api_v2/serializers.py`.
Verbatim `Meta.fields`:

```python
fields = (
    # describes agency
    "id", "name", "slug", "status", "exempt", "types", "requires_proxy", "jurisdiction",
    # connects to other agencies
    "parent", "appeal_agency",
)
```

Documented example:

```json
{
  "id": 1,
  "name": "Environmental Protection Agency",
  "slug": "environmental-protection-agency",
  "status": "approved",
  "exempt": false,
  "requires_proxy": false,
  "jurisdiction": 10,
  "types": ["Executive"],
  "parent": null,
  "appeal_agency": null
}
```

`types` help text, verbatim: "The types of the agency (e.g., Executive, Legislative,
Police, etc)." `requires_proxy`: "Indicates whether the agency requires a proxy because of
in-state residency laws."
**Retrieved:** 2026-08-20
**Implication for the spec:** The Agency object carries **no ORI code, no FIPS place code,
no website, no address, and no NCIC identifier**. It is a name + slug + jurisdiction FK.
Entity resolution from MuckRock agency → SIG Organization is therefore a *fuzzy* match on
(name, jurisdiction) and must be routed to a review queue, not written deterministically.
The `types` array containing "Police" is the only law-enforcement discriminator available.
**Outline delta:** EXTENDS §6.1 and §20 Q9 — MuckRock agency records cannot supply ORI.
The `parent`/`appeal_agency` self-edges are, however, directly reusable as SIG
Organization→Organization edges.

### F4.7 — MuckRock FOIARequest and FOIAFile schemas; `doc_id` is a DocumentCloud join key

**Claim:** MuckRock's `FOIAFile` serializer exposes a `doc_id` field that is the
DocumentCloud document identifier, giving a direct, first-party MuckRock↔DocumentCloud join.
**Status:** VERIFIED (source)
**Evidence:** `https://raw.githubusercontent.com/MuckRock/muckrock/master/muckrock/foia/api_v2/serializers.py`.
Verbatim documented example of a FOIA file:

```json
{
  "id": 1215939,
  "ffile": "https://cdn.muckrock.com/foia_files/2024/09/05/PSP_FINAL_RESPONSE_RTK__2024-1657_xLBSvYT.pdf",
  "datetime": "2024-09-05T14:01:29.268029",
  "title": "PSP FINAL RESPONSE RTK # 2024-1657",
  "source": "Pennsylvania State Police, Pennsylvania",
  "description": "",
  "doc_id": "25092350-psp-final-response-rtk-2024-1657",
  "pages": 11
}
```

FOIARequest `Meta.fields`, verbatim:

```python
fields = (
    "id", "title", "requested_docs", "slug", "status", "agency",
    "embargo_status",  # public, embargo, or permanent
    "user", "edit_collaborators", "read_collaborators",
    "datetime_submitted", "datetime_updated", "datetime_done",
    "tracking_id", "price", "tags", "edited_boilerplate",
)
```

`tracking_id` help text, verbatim: "The tracking ID assigned to this request by the agency".
**Retrieved:** 2026-08-20
**Implication for the spec:** Three high-value mappings:
- `FOIARequest.tracking_id` is the **agency-side** request number. This is the join key to
  agency-run portals (NextRequest/GovQA) — see F4.24. SIG should store it on the
  `EvidenceArtifact`/records-request node.
- `FOIAFile.ffile` is a direct, unauthenticated-looking `cdn.muckrock.com` URL for the raw
  PDF: SIG can content-address and archive the bytes without going through the API.
- `FOIAFile.doc_id` (`<dcid>-<slug>`) yields the DocumentCloud document id by splitting on
  the first hyphen. This is the canonical MuckRock→DocumentCloud edge.
**Outline delta:** EXTENDS §2 Layer F — the outline's sketch schema
(`records_request / requesting_party / target_agency / …`) maps cleanly onto these fields,
but omits `tracking_id`, `embargo_status`, `price`, and `doc_id`, all of which are
operationally important.

### F4.8 — MuckRock FOIA statuses and embargo semantics constrain what SIG may mirror

**Claim:** `embargo_status` takes values `public`, `embargo`, `permanent`; embargoed
requests are paid-tier-only and are not public.
**Status:** VERIFIED (source)
**Evidence:** Same serializer, verbatim help text:
  > "The embargo status. Embargo is only available to paid professional users and permanent
  > is only available to paid organizational members."
**Retrieved:** 2026-08-20
**Implication for the spec:** The connector must hard-filter on `embargo_status == "public"`
before writing anything to the public graph, even if an authenticated token happens to
return embargoed rows visible to that account.

### F4.9 — MuckRock terms of service prohibit robotic data extraction and commercial reuse; no open license is granted

**Claim:** MuckRock's ToS forbids data mining/robots and commercial exploitation, and
neither the ToS, the About page, nor the footer grants any Creative Commons or public-domain
license to MuckRock-hosted content.
**Status:** VERIFIED
**Evidence:** `https://www.muckrock.com/tos/` (fetched 2026-08-20), verbatim:
  > "any use of data mining, robots, or similar data gathering and extraction tools"
  (listed among prohibited uses)
  > "No MuckRock Services, part or whole, may be reproduced, duplicated, copied, sold,
  > resold, visited or otherwise exploited for any commercial purpose without the express
  > written consent of MuckRock"
  > "This license does not include any resale or commercial use of any MuckRock Services,
  > or its contents"
  > "All rights not expressly granted to you in these Terms are reserved and retained by
  > MuckRock or its licensors"
  > "any downloading or copying of account information for the benefit of another public
  > records request service"
  `https://www.muckrock.com/about/` — no licensing statement; footer reads only
  "© 2010–2026 MuckRock".
**Retrieved:** 2026-08-20
**Implication for the spec:** This is the sharpest licensing constraint in R4's scope.
Three consequences:
1. **Use the API, not a scraper.** The ToS's anti-robot clause is aimed at scraping; the
   sanctioned path is the documented, rate-limited, authenticated API. SIG must not run an
   HTML scraper against muckrock.com.
2. **Do not redistribute MuckRock's own metadata in bulk.** SIG may store MuckRock IDs,
   URLs, and derived claims, and should link back — but must not publish a mirror of
   MuckRock's request corpus as a downloadable dataset.
3. **The underlying government records are a separate work.** Records released under FOIA
   by US federal agencies are non-copyrightable (17 U.S.C. §105); state/local records are
   generally uncopyrightable as edicts/public records but this varies by state. MuckRock's
   ToS governs *MuckRock's service*, not the copyright status of a released PDF. SIG's
   defensible position is: archive the *released record bytes* (fetched from
   `cdn.muckrock.com` or DocumentCloud S3) as an EvidenceArtifact, and link — not mirror —
   MuckRock's request-level metadata.
**Outline delta:** EXTENDS §14.2 — source licenses as first-class metadata must include a
`redistribution: link_only` value, which MuckRock is the first concrete instance of.

### F4.10 — MuckRock does expose crowdsource/assignment features, but they are not in the v2 API

**Claim:** The v2 router exposes no `crowdsource` endpoint; the nine resources are
requests, communications, agencies, files, jurisdictions, users, statistics, organizations,
projects.
**Status:** VERIFIED
**Evidence:** `https://www.muckrock.com/api_v2/` root listing (WebFetch, 2026-08-20) —
enumerated above in F4.1. No `crowdsource`, `assignment`, or `task` route.
**Retrieved:** 2026-08-20
**Implication for the spec:** §20 Q35 ("Can research tasks link directly to
HIBF/MuckRock workflows?") — **not via the API**. MuckRock Assignments/crowdsource cannot be
created or read programmatically through v2. SIG's research queue (§15.6) must own its own
task model and can only deep-link to MuckRock UI URLs.
**Outline delta:** CORRECTS §20 Q35 — the programmatic integration the outline hopes for
does not currently exist.

### F4.11 — Filing requests via the API is supported and is a genuine capability for SIG

**Claim:** `FOIARequestCreateSerializer` accepts `agencies` (list of agency IDs),
`organization`, `embargo_status`, `title`, `requested_docs`, `edited_boilerplate`, `tags`.
**Status:** VERIFIED (source)
**Evidence:** Same file, verbatim create example:

```json
{"agencies": [2], "organization": 3, "embargo_status": "public",
 "title": "Request for Meeting Minutes",
 "requested_docs": "All meeting minutes from Q1 2023"}
```

`edited_boilerplate` help text, verbatim: "If true, your requested_docs text is used
directly as the full request letter, bypassing the MuckRock template."
`agencies` queryset is restricted to `Agency.objects.filter(status="approved")`.
**Retrieved:** 2026-08-20
**Implication for the spec:** SIG's §12 research-task generator can *close the loop*: a
"Missing contract" task for agency X can be materialized as an actual MuckRock FOIA filing,
with the returned request `id` stored on the task. This is the single most valuable
MuckRock integration and the outline does not mention it. It requires a funded MuckRock
account (requests cost money) and an explicit human-approval gate — SIG must never
auto-file requests without review.
**Outline delta:** EXTENDS §12 and §15.6.

---

# Part B — DocumentCloud (outline Q8)

### F4.12 — DocumentCloud's search API is fully open and unauthenticated; real response captured

**Claim:** `GET https://api.www.documentcloud.org/api/documents/search/` returns public
document metadata with no credentials at all.
**Status:** VERIFIED
**Evidence:** Real call, 2026-08-20:

```
GET https://api.www.documentcloud.org/api/documents/search/?q=flock+safety
```

```json
{
    "count": 844699,
    "next": "https://api.www.documentcloud.org/api/documents/search/?q=flock+safety&cursor=AoMIQou3tHiB7oW7mwMoMjY0NTA0ODE%3D",
    "previous": null,
    "results": [
        {
            "id": "27924168",
            "user": 108916,
            "organization": 106358,
            "access": "public",
            "status": "success",
            "title": "flock-safety",
            "slug": "flock-safety",
            "language": "eng",
            "created_at": "2026-03-29T16:21:44.572Z",
            "updated_at": "2026-03-29T16:22:30.264Z",
            "page_count": 15,
            "page_spec": "720.00x405.00:0",
            "projects": [219085],
            "original_extension": "pdf",
            "file_hash": "f0adb4875a548711ee401e88c0cc999d5bdd23d1",
            "noindex": false,
            "edit_access": false,
            "notes": [],
            "highlights": null,
            "data": {},
            "asset_url": "https://s3.documentcloud.org/",
            "canonical_url": "https://www.documentcloud.org/documents/27924168-flock-safety/"
        }
    ]
}
```

Note `count: 844699` is an OR-match over the two terms, not a phrase count. A quoted,
two-phrase query narrows it:

```
GET https://api.www.documentcloud.org/api/documents/search/?q=%22flock+safety%22+%22license+plate%22&per_page=2&expand=organization,user
```

```json
{
    "count": 48844,
    "next": "…&cursor=AoMIQsety3L%2FpMHFnwMoMjg1MDY2Mzc%3D",
    "previous": null,
    "results": [
        {
            "id": "7273472",
            "user": {"id": 659, "name": "Muckrock Staff", "organization": 125,
                     "organizations": [125, 12303], "admin_organizations": [12303],
                     "username": "MuckrockStaff",
                     "uuid": "25d842d6-a24e-4dc6-8351-950824e432fc",
                     "verified_journalist": true},
            "organization": {"id": 125, "individual": false, "name": "MuckRock Staff",
                             "slug": "muckrock",
                             "uuid": "97109cc6-e52e-41e7-adb7-834ab7c6819c",
                             "created_at": "2026-07-23T18:13:12.525831Z",
                             "updated_at": "2026-08-20T16:28:58.984782Z"},
            "access": "public",
            "status": "success",
            "title": "ORA Request - Flock Safety Automated License Plate Readers",
            "slug": "ORA-Request-Flock-Safety-Automated-License-Plate",
            "source": "Chatham County Sheriff",
            "language": "eng",
            "created_at": "2020-10-20T15:05:21.644Z",
            "updated_at": "2021-01-13T01:08:49.712Z",
            "page_count": 2,
            "original_extension": "pdf",
            "file_hash": "9cb3c68075f6f9b62f9c706db1eda014ecc1eea2",
            "related_article": "https://www.muckrock.com/foi/chatham-county-4858/flock-chatham-county-sheriff-102796/",
            "edit_access": false,
            "notes": [], "highlights": null, "data": {},
            "asset_url": "https://s3.documentcloud.org/",
            "canonical_url": "https://www.documentcloud.org/documents/7273472-ORA-Request-Flock-Safety-Automated-License-Plate/"
        },
        {
            "id": "28506637",
            "user": {"id": 171524, "name": "Yogev Toby", "organization": 13, "…": "…"},
            "organization": {"id": 13, "name": "The Boston Globe", "slug": "boston-globe",
                             "uuid": "2199ed94-7911-403e-8655-9e09fa2b57cc"},
            "access": "public", "status": "success",
            "title": "Review of the Town of Tewksbury's Flock Safety License-Plate-Reader System",
            "slug": "review-of-the-town-of-tewksburys-flock-safety-license-plate-reader-system",
            "language": "eng",
            "created_at": "2026-07-22T18:09:58.770Z",
            "page_count": 109,
            "page_spec": "612.00x792.00:0",
            "original_extension": "pdf",
            "file_hash": "dd383635e1a7396e6c7006c05ba7872d170e3e83",
            "noindex": false, "edit_access": false, "notes": [], "data": {},
            "asset_url": "https://s3.documentcloud.org/",
            "canonical_url": "https://www.documentcloud.org/documents/28506637-review-of-the-town-of-tewksburys-flock-safety-license-plate-reader-system/"
        }
    ],
    "escaped": false
}
```
**Retrieved:** 2026-08-20
**Implication for the spec:** DocumentCloud is the **highest-leverage unauthenticated
source in R4's entire scope.** No token, no key, no account. `expand=organization,user`
resolves the publishing newsroom inline. `file_hash` (SHA-1) is supplied by DocumentCloud,
giving SIG a free content-address to dedupe against. `related_article` supplies the
MuckRock request URL when the document came from a MuckRock request.
**Outline delta:** CONFIRMS and greatly EXTENDS §2 Layer F. The outline's wish-list of
document metadata (title, issuing org, date, page range, checksum, archive URL) is
**already served field-for-field** by DocumentCloud: `title`, `organization.name`+`source`,
`created_at`, `page_count`, `file_hash`, `canonical_url`.

### F4.13 — Base URL is `api.www.documentcloud.org`, not `www.documentcloud.org/api`

**Claim:** The API host is `api.www.documentcloud.org`; the app host redirects docs to a
MuckRock-hosted Notion page.
**Status:** VERIFIED
**Evidence:** `https://www.documentcloud.org/help/api/` returns **HTTP 301** to
`https://help.muckrock.com/API-19ef889269638147bbb7d8cc8af8e0fc` (a Notion page that renders
client-side and returned only the literal string "Notion" to a text fetcher — i.e. the
official DocumentCloud API documentation is **not machine-readable**). Working calls all go
to `https://api.www.documentcloud.org/api/…`.
**Retrieved:** 2026-08-20
**Implication for the spec:** Do not build against the docs URL. Pin
`https://api.www.documentcloud.org/api/` and derive schema from the open-source serializers
(F4.15) rather than the Notion page.

### F4.14 — Full text and page assets are retrievable unauthenticated from `s3.documentcloud.org`

**Claim:** For a public document, the extracted plain text is at
`https://s3.documentcloud.org/documents/<id>/<slug>.txt`, fetchable with no credentials.
**Status:** VERIFIED
**Evidence:** Real fetch, 2026-08-20, of
`https://s3.documentcloud.org/documents/27924168/flock-safety.txt` — first ~600 chars
verbatim:

```
Shape a safer future,
together
2025 Houston, TX

1,500+ Businesses protected Driven by a shared mission: by Flock
Eliminate crime and shape a
safer future, together.
2,800+ Crimes solved per
day using Flock
15% Of reported crime in the
US solved using Flock*
6,000+ Communities protected
by Flock
*The calculation of this figure follows the methodology outlined in the TCU study, applied to
continuously updated data from our customers. …

Built with Privacy in Mind
Data is 100% owned by customers and will never be sold.
…
Flock automatically deletes data after 30 days by default.
…
All data is stored with end-to-end encryption including: ● FBI (CJIS) ● NDAA ● SOC2 (Type II)
● SOC3 ● ISO 27001 ● Higher Education Community Vendor Assessment Tool (HECVAT) ● HIPAA ● FERPA
```

(Note: this document, `27924168`, is a **Flock Safety sales deck** — a Tier-B first-party
vendor statement in §9.1 terms, containing a claimed default retention of 30 days. Exactly
the kind of artifact §11 retention-reconciliation needs.)

The same asset paths from *this IP* using `curl` returned HTTP 403 Cloudflare blocks; the
fetch succeeded from a different egress. So: the asset is public, but the CDN blocks
suspicious clients.
**Retrieved:** 2026-08-20
**Implication for the spec:** SIG gets OCR'd/extracted full text for free on every public
DocumentCloud document — no need to re-OCR. The asset URL family is:
- `…/documents/<id>/<slug>.pdf` — original PDF
- `…/documents/<id>/<slug>.txt` — full extracted text
- `…/documents/<id>/pages/<slug>-p<N>-large.gif` — page image
- `…/documents/<id>/pages/<slug>-p<N>.txt` — per-page text
- `…/documents/<id>/<slug>.json` (via API `?expand=` for structured data)

### F4.15 — DocumentCloud access levels and status enums (exact values from source)

**Claim:** `access` ∈ {public, organization, private, invisible}; `status` ∈ {success,
readable, pending, error, nofile, deleted}. Only the first three access levels are exposed
via API; `invisible` (taken-down) is not.
**Status:** VERIFIED (source)
**Evidence:** `https://raw.githubusercontent.com/MuckRock/documentcloud/master/documentcloud/documents/choices.py`,
verbatim:

```python
class Access(models.IntegerChoices):
    public       = 0, _("Public"),       True   # Free and public to all.
    organization = 1, _("Organization"), True   # Visible to owner and her organization.
    private      = 2, _("Private"),      True   # Only visible to its owner.
    invisible    = 3, _("Invisible"),    False  # The document has been taken down (perhaps temporary).

class Status(models.IntegerChoices):
    success  = 0, _("Success"),  True
    readable = 1, _("Readable"), True
    pending  = 2, _("Pending"),  True
    error    = 3, _("Error"),    True
    nofile   = 4, _("No file"),  True
    deleted  = 5, _("Deleted"),  False
```

The `DocumentSerializer` defaults `access` to `Access.private` on create, and exposes
`asset_url`, `canonical_url`, `edit_access`, `presigned_url`, `data` (arbitrary JSON custom
metadata), plus write-only `file_url`, `force_ocr`, `ocr_engine` (`tess4` | `textract`) and
`delayed_index`. Entity extraction kinds include `person, location, organization, event,
work_of_art, consumer_good, phone_number, address, date`.
**Retrieved:** 2026-08-20
**Implication for the spec:** A document can silently transition `public → invisible`
(takedown). SIG must therefore **capture its own copy of the bytes at ingest time** and
record a `dc_access_at_capture` field; a link-only citation to DocumentCloud can vanish.
This is a direct answer to §20 Q16 — see F4.16.

### F4.16 — Q16 answer: what SIG may archive vs merely link

**Claim:** SIG may archive the *bytes of released public records* and must link-only for
platform-proprietary metadata; the distinction is by rights-holder, not by host.
**Status:** PARTIALLY VERIFIED (terms read; legal conclusion is reasoned, not adjudicated)
**Evidence:**
- DocumentCloud's homepage footer links its Terms of Service to **`https://www.muckrock.com/tos/`**
  (i.e. DocumentCloud and MuckRock share one ToS — verified 2026-08-20 via WebFetch of
  `https://www.documentcloud.org/`, which also reports "7,160,398 public documents and counting").
  `https://www.documentcloud.org/terms/` itself returns **HTTP 404**.
- That shared ToS contains the anti-data-mining and anti-commercial clauses quoted in F4.9.
- DocumentCloud states "Everyone is welcome to explore our public document archive".
**Retrieved:** 2026-08-20
**Implication for the spec — recommended archive/link policy:**

| Content class | Rights position | SIG action |
|---|---|---|
| US federal agency record released under FOIA | 17 U.S.C. §105 — no copyright | **Archive bytes + text; republish** |
| State/local government record released under a state PRA | generally uncopyrightable public record; a few states assert copyright in some works | **Archive bytes; republish with source attribution; honor takedowns** |
| Contract signed between agency and vendor | joint work but filed as a public record | **Archive bytes; republish** |
| Vendor marketing deck / price list obtained via records request | vendor holds copyright, but the copy is now a public record | **Archive bytes privately; publish extracted facts + excerpt, not the whole file** |
| Court filing (PACER/RECAP) | judicial records, no federal copyright | **Archive; republish** |
| DocumentCloud/MuckRock *platform metadata* (notes, projects, user/org records) | MuckRock ToS reserves rights | **Link only; store IDs, never mirror in bulk** |
| Newsroom-authored annotations/notes on a document | newsroom copyright | **Link only** |

**Outline delta:** ANSWERS §20 Q16, which the outline poses but does not resolve.

### F4.17 — Add-on framework exists but is a DocumentCloud-side execution model, not an ingestion API

**Claim:** DocumentCloud Add-Ons run as GitHub Actions inside DocumentCloud's own
orchestration and are not a data-egress mechanism SIG needs.
**Status:** PARTIALLY VERIFIED
**Evidence:** The add-on template repo path
`https://raw.githubusercontent.com/MuckRock/documentcloud-addon-template/main/README.md`
returned **404** (repo/branch name differs); the add-on machinery is visible in the main
`MuckRock/documentcloud` repo, and the API docs page (Notion) is not machine-readable.
**Retrieved:** 2026-08-20
**Implication for the spec:** Do not design around Add-Ons. SIG should pull via the search
API and archive assets itself. Add-Ons would only matter if SIG wanted to *push* enrichment
back into DocumentCloud for the journalism community — a Stage-3+ collaboration idea, not a
Stage-1 dependency.

### F4.18 — DocumentCloud pagination is cursor-based; deep paging is the constraint

**Claim:** Search responses paginate by opaque `cursor`, not by page number.
**Status:** VERIFIED
**Evidence:** Both real responses above return
`"next": "…&cursor=AoMIQou3tHiB7oW7mwMoMjY0NTA0ODE%3D"` with no `page=` parameter.
`per_page` is accepted.
**Retrieved:** 2026-08-20
**Implication for the spec:** The connector must follow `next` links serially and persist
the cursor for resumability; it cannot parallelize by page number, and it cannot jump to
"page 500". For incremental sync, use `updated_at` range filters in `q` rather than
re-walking the cursor chain.

---

# Part C — Federal spending, contracting, and grants

### F4.19 — USAspending: award search works unauthenticated; real Flock response captured

**Claim:** `POST https://api.usaspending.gov/api/v2/search/spending_by_award/` requires no
API key and returns Flock's federal prime awards.
**Status:** VERIFIED
**Evidence:** Real call, 2026-08-20:

```
POST https://api.usaspending.gov/api/v2/search/spending_by_award/
Content-Type: application/json

{"filters":{"keywords":["Flock Safety"],"award_type_codes":["A","B","C","D"]},
 "fields":["Award ID","Recipient Name","Award Amount","Awarding Agency",
           "Awarding Sub Agency","Start Date","End Date","recipient_id",
           "prime_award_recipient_id"],
 "page":1,"limit":5,"sort":"Award Amount","order":"desc","subawards":false}
```

Response (HTTP 200), verbatim:

```json
{"spending_level":"awards","limit":5,"results":[
 {"internal_id":277759233,"Award ID":"140D0425P0230","Recipient Name":"FLOCK GROUP INC",
  "Award Amount":231600.0,"Awarding Agency":"Department of the Interior",
  "Awarding Sub Agency":"Departmental Offices","Start Date":"2025-09-25","End Date":"2027-09-25",
  "recipient_id":"4fbcf525-e991-fad8-2aaa-6a02c70053aa-C","prime_award_recipient_id":null,
  "awarding_agency_id":209,"agency_slug":"department-of-the-interior",
  "generated_internal_id":"CONT_AWD_140D0425P0230_1406_-NONE-_-NONE-"},
 {"internal_id":280222542,"Award ID":"36C25025P1681","Recipient Name":"FLOCK GROUP INC",
  "Award Amount":21000.0,"Awarding Agency":"Department of Veterans Affairs",
  "Awarding Sub Agency":"Department of Veterans Affairs","Start Date":"2025-09-18",
  "End Date":"2026-09-17","recipient_id":"4fbcf525-e991-fad8-2aaa-6a02c70053aa-C",
  "prime_award_recipient_id":null,"awarding_agency_id":561,
  "agency_slug":"department-of-veterans-affairs",
  "generated_internal_id":"CONT_AWD_36C25025P1681_3600_-NONE-_-NONE-"}],
 "page_metadata":{"page":1,"hasNext":false,"last_record_unique_id":null,"last_record_sort_value":"None"},
 "messages":["For searches, time period start and end dates are currently limited to an
  earliest date of 2007-10-01. For data going back to 2000-10-01, use either the Custom
  Award Download feature on the website or one of our download or bulk_download API
  endpoints as listed on https://api.usaspending.gov/docs/endpoints. "]}
```

**Retrieved:** 2026-08-20
**Implication for the spec:** **Flock Safety's entire federal prime-contract footprint is
two small awards totalling $252,600** (DOI and VA). This is a *decisive* scoping fact.
**Outline delta:** CORRECTS §2 Layer F's implicit weighting. The outline lists
"USAspending.gov for federal spending" alongside local sources as though they are
comparable. They are not: for Flock, USAspending covers **~0.01%** of the money. See F4.22.

### F4.20 — USAspending recipient identity model: UEI + DUNS + a hashed `recipient_id` with C/P/R level suffixes

**Claim:** USAspending's recipient identity is a UUID-with-level-suffix
(`…-C` child / `…-P` parent / `…-R` recipient), joined to UEI and legacy DUNS.
**Status:** VERIFIED
**Evidence:** Real call
`GET https://api.usaspending.gov/api/v2/recipient/duns/4fbcf525-e991-fad8-2aaa-6a02c70053aa-C/`:

```json
{
  "name": "FLOCK GROUP INC",
  "alternate_names": [],
  "duns": "085951311",
  "uei": "QDLLBKCGL851",
  "recipient_id": "4fbcf525-e991-fad8-2aaa-6a02c70053aa-C",
  "recipient_level": "C",
  "parent_id": "4fbcf525-e991-fad8-2aaa-6a02c70053aa-P",
  "parent_name": "FLOCK GROUP INC",
  "parent_duns": "085951311",
  "parent_uei": "QDLLBKCGL851",
  "parents": [{"parent_duns":"085951311","parent_name":"FLOCK GROUP INC",
               "parent_id":"4fbcf525-e991-fad8-2aaa-6a02c70053aa-P",
               "parent_uei":"QDLLBKCGL851"}],
  "business_types": ["category_business","corporate_entity_not_tax_exempt",
                     "other_than_small_business","special_designations","us_owned_business"],
  "location": {"address_line1":"1170 HOWELL MILL RD NW STE 210","city_name":"ATLANTA",
               "state_code":"GA","zip":"30318","zip4":"8637","country_code":"USA",
               "congressional_code":"05"}
}
```

**Retrieved:** 2026-08-20
**Implication for the spec:** **`UEI = QDLLBKCGL851` is the canonical federal identifier for
Flock Group Inc.** SIG's Vendor node (§8.2) should carry `uei`, `cage_code`, legacy `duns`,
and `usaspending_recipient_id`. UEI is the right vendor anchor: it is issued by SAM.gov,
is stable, survives name changes, and is cross-referenced by USAspending, SAM.gov, FPDS and
most state portals that ride federal funds.
**Outline delta:** EXTENDS §8.2 (Vendor) and answers part of §20 Q12 for the *vendor* side —
private companies in Flock/Fusus networks that are federal registrants can be disambiguated
by UEI. Private companies that are *not* federal registrants (most Flock business customers)
cannot, and need a different strategy.

Note the useful trap: `recipient_name` autocomplete is nearly useless for this vendor.
`POST /api/v2/autocomplete/recipient/ {"search_text":"flock","limit":5}` returned:

```json
{"count":5,"results":[{"recipient_name":"FLOCK OFF, LLC",...},
 {"recipient_name":"FLOCK, WILLIAM L PSY D",...},{"recipient_name":"A NATURAL FLOCKE",...},
 {"recipient_name":"AFLOCKPORT INC",...},{"recipient_name":"ALICE CHAN DBA FLOCK MARKETING",...}]}
```

— i.e. **"FLOCK GROUP INC" is not in the top 5 for the query "flock"**. Never resolve
vendors by name autocomplete; resolve by UEI.

### F4.21 — NAICS/PSC codes that matter for surveillance procurement

**Claim:** Surveillance-tech federal awards concentrate in NAICS 334310 / 334220 / 541519
and PSC 5836 / 5810 / 5895 / D3xx; real values captured from Axon awards.
**Status:** VERIFIED
**Evidence:** Real call for Axon (FY2021–2026, contract types A–D), verbatim excerpt:

```json
{"internal_id":291177880,"Award ID":"70B03C20C00000167","Recipient Name":"AXON ENTERPRISE, INC.",
 "Award Amount":20555205.36,"Awarding Agency":"Department of Homeland Security",
 "NAICS":{"code":"334310","description":"AUDIO AND VIDEO EQUIPMENT MANUFACTURING"},
 "PSC":{"code":"5836","description":"VIDEO RECORDING AND REPRODUCING EQUIPMENT"},
 "Start Date":"2020-09-23","End Date":"2022-01-31","agency_slug":"department-of-homeland-security",
 "generated_internal_id":"CONT_AWD_70B03C20C00000167_7014_-NONE-_-NONE-"}
{"internal_id":360452269,"Award ID":"70CMSW26FR0000045","Recipient Name":"AXON ENTERPRISE, INC.",
 "Award Amount":17766997.6,"Awarding Agency":"Department of Homeland Security",
 "NAICS":{"code":"334220","description":"RADIO AND TELEVISION BROADCASTING AND WIRELESS
  COMMUNICATIONS EQUIPMENT MANUFACTURING"},
 "PSC":{"code":"5836","description":"VIDEO RECORDING AND REPRODUCING EQUIPMENT"},
 "Start Date":"2026-07-20","End Date":"2027-09-24",
 "generated_internal_id":"CONT_AWD_70CMSW26FR0000045_7012_70B03C23D00000006_7014"}
{"internal_id":278339211,"Award ID":"15M10424FA4700023","Recipient Name":"AXON ENTERPRISE, INC.",
 "Award Amount":14042160.2,"Awarding Agency":"Department of Justice",
 "NAICS":{"code":"332994","description":"SMALL ARMS, ORDNANCE, AND ORDNANCE ACCESSORIES MANUFACTURING"},
 "PSC":{"code":"5340","description":"HARDWARE, COMMERCIAL"},"Start Date":"2024-01-26","End Date":"2027-01-25"}
```

**Retrieved:** 2026-08-20
**Implication for the spec:** NAICS/PSC are *weak* signals — the same vendor's awards land
in 334310, 334220 and 332994 with PSCs 5836 and 5340. SIG should use NAICS/PSC as a
**recall-widening discovery filter** for finding *unknown* vendors, never as a classifier
for *known* ones. Recommended discovery set:
NAICS `334310, 334220, 334511, 541519, 561621, 517311`;
PSC `5836, 5810, 5895, 5865, 6350, 7A20, 7A21, D307, D310, D399`.

### F4.22 — What USAspending does and does NOT cover (state this plainly in the spec)

**Claim:** USAspending covers federal prime awards and federally-reported sub-awards only;
it does not contain city or county purchases made with local funds.
**Status:** VERIFIED (by construction and by the $252,600 Flock total)
**Evidence:** Flock's federal prime total across all award types is $252,600 (F4.19), while
Flock's publicly reported customer base is thousands of agencies. The delta is entirely
locally-funded procurement invisible to USAspending. USAspending's own response message
also caps searches at `2007-10-01` and directs older data to bulk download.
**Retrieved:** 2026-08-20
**Implication for the spec — write this into the design doc verbatim:**

> USAspending is a **vendor-identity and federal-grant-flow** source for SIG, not a
> procurement source. It answers: what is this vendor's UEI, who is its parent, what NAICS
> does it sell under, and which federal grant programs are flowing money toward local
> surveillance. It does **not** answer: does city X have a Flock contract. That question is
> only answerable from local procurement, agenda systems, and records requests.

**Outline delta:** CORRECTS §2 Layer F.

### F4.23 — **The federal-grant → local-surveillance trace IS programmatically possible via USAspending sub-awards**

**Claim:** Setting `"subawards": true` with a `keywords` filter returns sub-award records
whose *sub-awardee is the local police agency* and whose description names the surveillance
equipment purchased. This is a working, unauthenticated grant-to-deployment trace.
**Status:** VERIFIED — and this is R4's second-most-important finding.
**Evidence:** Real call, 2026-08-20:

```
POST https://api.usaspending.gov/api/v2/search/spending_by_award/
{"filters":{"keywords":["license plate reader"],"award_type_codes":["02","03","04","05"]},
 "fields":["Sub-Award ID","Sub-Awardee Name","Sub-Award Amount","Prime Recipient Name",
           "Sub-Award Date","Sub-Award Description","Awarding Agency"],
 "page":1,"limit":5,"subawards":true}
```

Verbatim results (descriptions abridged where marked …):

```json
{"Sub-Award ID":"Y23-202","Sub-Awardee Name":"ORANGE COUNTY SHERIFF'S OFFICE",
 "Sub-Award Amount":104510.0,"Prime Recipient Name":"ORANGE COUNTY, FLORIDA",
 "Sub-Award Date":"2023-03-21","Awarding Agency":"Department of Justice",
 "prime_award_generated_internal_id":"ASST_NON_15PBJA22GG02066JAGX_015",
 "Sub-Award Description":"THE ORANGE COUNTY SHERIFF'S OFFICE (OCSO) WILL UTILIZE THE 2022
  FUNDING FROM THE EDWARD BYRNE MEMORIAL JUSTICE ASSISTANT GRANT … THE OCSO UNIFORM PATROL
  DIVISION SECTOR 1 WILL INSTALL TWO LICENSE PLATE READER (LPR) CAMERAS TO CONTINUE THE
  BUILD OUT OF THE LPR CAMERA PROGRAM TO OTHER HIGH-CRIME APOPKA AREAS INCLUDING TANGERINE
  AND ZELLWOOD … THE OCSO CRIMINAL INVESTIGATIONS DIVISION WILL ACQUIRE 15 AVIGILON H5Z
  CAMERAS AND CAMERAS LICENSES FOR THE REAL TIME CRIME CENTER, KNOWN AS AIM (ANALYTICS,
  INTELLIGENCE, AND MONITORING). …"}

{"Sub-Award ID":"XM003","Sub-Awardee Name":"VOLUSIA SHERIFF'S OFFICE","Sub-Award Amount":108653.0,
 "Prime Recipient Name":"FLORIDA DEPARTMENT OF LAW ENFORCEMENT","Sub-Award Date":"2024-05-10",
 "Awarding Agency":"Department of Justice",
 "prime_award_generated_internal_id":"ASST_NON_15PBJA22GG00717GUNP_015",
 "Sub-Award Description":"THE RECIPIENT WILL USE GRANT FUNDS FOR OVERTIME AND TO PURCHASE
  LICENSE PLATE READERS FOR CRIME HOTSPOTS WITHIN THEIR JURISDICTION."}

{"Sub-Award ID":"UASI-2024-PRIORITY-00005","Sub-Awardee Name":"INDIANA STATE POLICE",
 "Sub-Award Amount":100000.0,"Prime Recipient Name":"INDIANA DEPT OF HOMELAND SECURITY",
 "Sub-Award Date":"2024-11-15","Awarding Agency":"Department of Homeland Security",
 "prime_award_generated_internal_id":"ASST_NON_EMW-2024-UA-05084_070",
 "Sub-Award Description":"… THE PROJECT WILL ALLOW THE IIFC TO CONTINUE FUNDING TECHNOLOGICAL
  RESOURCES, SUCH AS, FACE RECOGNITION AND LICENSE PLATE READER INFORMATION TO AGENCIES THAT
  ARE TOO SMALL TO FUND THEIR OWN AND HAVE COME TO RELY ON THE IIFC FOR ASSISTANCE. …"}
```

And the Homeland Security Grant Program (CFDA 97.067) prime→sub chain:

```json
prime: {"Award ID":"EMW-2019-SS-00011",
        "Recipient Name":"NEW YORK STATE DIVISION OF HOMELAND SECURITY & EMERGENCY SERVICES",
        "Award Amount":258160920.47,"CFDA Number":"97.067"}
sub:   {"Sub-Award ID":"YHDFKLC56AA9","Sub-Awardee Name":"SAN JUAN COUNTY",
        "Sub-Award Amount":394645.0,"Prime Recipient Name":"HOMELAND SECURITY AND EMERGENCY MANAGEME",
        "Sub-Award Date":"2023-10-19","Sub-Award Description":"EQUIPMENT, TRAINING & EXERCISE",
        "prime_award_generated_internal_id":"ASST_NON_EMW-2023-SS-00015_070"}
sub:   {"Sub-Award ID":"XPAHL4N7QAA1","Sub-Awardee Name":"COUNTY OF BOUNDARY",
        "Sub-Award Amount":64000.0,"Prime Recipient Name":"STATE OF IDAHO MILITARY DIVISION",
        "Sub-Award Date":"2024-10-28","Sub-Award Description":"OPSG",
        "prime_award_generated_internal_id":"ASST_NON_EMW-2023-SS-00078_070"}
```

Note `"Sub-Award Description":"OPSG"` — Operation Stonegarden sub-awards *are* present but
are described by acronym only.
**Retrieved:** 2026-08-20
**Implication for the spec:** SIG should run a standing, scheduled **grant-lead miner**:

```
for cfda in [16.738 Byrne JAG, 16.710 COPS Hiring, 16.United COPS Technology,
             97.067 HSGP/SHSP/UASI/OPSG, 97.078 Buffer Zone, 95.001 HIDTA(via ONDCP)]:
  for kw in ["license plate reader","LPR","ALPR","Flock","real time crime center","RTCC",
             "camera","surveillance","facial recognition","drone","gunshot detection",
             "ShotSpotter","Fusus","Axon","Motorola","Vigilant","cell site simulator"]:
    POST /api/v2/search/spending_by_award/ {subawards:true, keywords:[kw],
                                            program_numbers:[cfda], ...}
```

Each hit produces a **research lead** (§12 style): "Federal grant EMW-2024-UA-05084
sub-awarded $100,000 to Indiana State Police describing LPR funding — no SIG deployment
record exists for this agency; verify."
**Outline delta:** **EXTENDS §2 Layer F, §8.10 and §12 substantially.** The outline lists
"grants" as one word in a bullet list. It is in fact the single most *automatable*
surveillance-discovery signal available without any records request, and it is
unauthenticated. Byrne JAG, HSGP/UASI and OPSG sub-awards are all present.

**Caveats that must be encoded:**
1. Sub-award keyword matching also matches *prime-award* text. A control query
   `keywords:["Flock"], subawards:true` returned unrelated primes
   (`TERRA MAR APPLIED SCIENCES`, `JACOBS TECHNOLOGY`, `CLARK MCCARTHY HEALTHCARE`).
   Every hit must be re-verified by regex against `Sub-Award Description` itself.
2. Sub-award descriptions contain **double-encoded UTF-8 mojibake** in the live API, e.g.
   `SHERIFFÃƑÂ¢Ã¢Â€ŠÂ¬S OFFICE`
   for `SHERIFF'S OFFICE`. The parser must run a `ftfy`-style mojibake repair before
   keyword matching, or it will miss hits.
3. Sub-award reporting (FSRS) is only mandatory above $30,000 and compliance is imperfect;
   absence of a sub-award is not evidence of absence of a purchase (§9.4 negative claims).
4. `Start Date`/`End Date` are frequently `null` on grant records (see EMW-2024-SS-05005).

### F4.24 — SAM.gov: entity API requires a key and the free tier is 10 requests/day

**Claim:** SAM.gov's Entity Management API requires a SAM.gov-issued key (not api.data.gov),
and a non-federal user with no assigned role is limited to **10 requests per day**.
**Status:** VERIFIED (documentation) / INACCESSIBLE (unauthenticated calls)
**Evidence:**
- Unauthenticated `GET https://api.sam.gov/entity-information/v3/entities?ueiSAM=QDLLBKCGL851`
  → **HTTP 404** (SAM returns 404, not 401, for keyless requests).
- Unauthenticated `GET https://api.sam.gov/opportunities/v2/search?...` → **HTTP 404**.
- `https://open.gsa.gov/api/entity-api/` (HTTP 200, read 2026-08-20) documents:
  base URLs `https://api.sam.gov/entity-information/v{1,2,3,4}/entities`; keys from
  `https://sam.gov/workspace/profile/account-details` ("Public API Key"); rate limits —

  | User type | Key type | Daily limit |
  |---|---|---|
  | Non-federal user, **no role** | Personal | **10 requests** |
  | Non-federal / federal user with role | Personal | 1,000 |
  | Non-federal system user | System account | 1,000 |
  | Federal system user | System account | 10,000 |

  `includeSections` ∈ `entityRegistration, coreData, pointsOfContact, repsAndCerts,
  integrityInformation, All`; filters include `ueiSAM` (up to 100 values), `cageCode` (up to
  100), `legalBusinessName`, `physicalAddressCity`, `registrationStatus`, `samRegistered`;
  `format=csv` triggers an asynchronous extract.
  Public `entityRegistration` fields: `ueiSAM`, `cageCode`, `legalBusinessName`,
  `registrationStatus`, `registrationDate`, `lastUpdateDate`, `registrationExpirationDate`,
  `purposeOfRegistrationDesc`. `coreData` adds `physicalAddress.*`,
  `generalInformation.entityStructureCode/Desc`, `organizationStructureCode/Desc`,
  `stateOfIncorporationCode`, `countryOfIncorporationCode`. **Corporate hierarchy
  (`immediateParentEntity`, `ultimateParentEntity`, `intermediateParentEntities`) is marked
  FOUO**, and banking/TIN data requires a federal system account with "Read Sensitive".
**Retrieved:** 2026-08-20
**Implication for the spec:** SAM.gov gives SIG the **authoritative vendor legal identity**
(UEI ↔ CAGE ↔ legal name ↔ registered address ↔ incorporation state ↔ registration
expiry). But the **10/day free ceiling makes it unusable as an online lookup**. Design:
batch up to 100 UEIs per call (the documented cap), run it as a weekly job, and cache
everything. Register for a role-assigned key to get 1,000/day. Vendor corporate hierarchy
(useful for Flock↔subsidiaries, Axon↔Fusus) is **FOUO and effectively unavailable** — SIG
must reconstruct vendor family trees from SEC filings, press releases, and USAspending
`parent_uei`, not from SAM.
**Outline delta:** CORRECTS §2 Layer F — "SAM.gov for federal contracting context" is
accurate but the outline gives no hint that the practical free quota is 10 calls/day.

### F4.25 — Federal grant program → data-source map for surveillance funding

**Claim:** The five grant programs that most often fund local surveillance are all traceable
in USAspending by CFDA/`program_numbers`, with varying sub-award fidelity.
**Status:** PARTIALLY VERIFIED (97.067 and 16.738 verified live; others by CFDA lookup)
**Evidence:** Live queries in F4.23 for 97.067 (HSGP family: SHSP, UASI, OPSG all report
under 97.067) and 16.738 (Byrne JAG). `GET /api/v2/references/cfda/totals/97.067/` returned
HTTP 204 (no content) — that helper endpoint is not populated for this CFDA.
`https://bja.ojp.gov/funding/awards/list` returns HTTP 200 (an HTML award browser, no API).
`https://api.simpler.grants.gov/v1/opportunities/search` returns **HTTP 405** on GET
(POST-only; it covers *opportunities*, i.e. NOFOs, not awards).
`https://www.grants.gov/api/` HTTP 200. FEMA's own
`https://www.fema.gov/api/open/v1/DataSets` returns HTTP 200 (OpenFEMA dataset catalogue);
`HazardMitigationAssistanceProjects` v2 returned 404 (dataset/version drift).
**Retrieved:** 2026-08-20

| Program | CFDA / ALN | Prime data | Sub-award data | Notes |
|---|---|---|---|---|
| Byrne JAG (BJA) | 16.738 | USAspending ✔ | USAspending `subawards:true` ✔ (verified: OCSO LPR) | State-administered pass-through is where local buys appear |
| COPS Office (hiring/technology) | 16.710 / 16.710x | USAspending ✔ | partial | COPS Technology earmarks historically funded ALPR |
| Homeland Security Grant Program: SHSP + UASI + OPSG | 97.067 | USAspending ✔ (verified) | USAspending ✔ (verified: San Juan Cty, Boundary Cty, Indiana State Police) | UASI sub-awards are the richest surveillance signal |
| Operation Stonegarden | 97.067 (sub-tagged "OPSG") | rolled into 97.067 | ✔ but description often just `"OPSG"` | Border-county ALPR is heavily OPSG-funded |
| HIDTA (ONDCP) | 95.001 | thin | thin | HIDTA is largely *not* in USAspending at useful granularity; requires records requests |

**Implication for the spec:** Model a `GrantAward` → `SubAward` → `Organization` chain as a
first-class path into `Contract`/`Deployment` (§8.10, §8.5). The `prime_award_generated_internal_id`
(e.g. `ASST_NON_15PBJA22GG02066JAGX_015`) is a stable USAspending key to store.
**Outline delta:** EXTENDS §8.10 — the Contract entity as specified
(`buyer/seller/amount/…`) has no slot for *funding source*. Add `funding_source` /
`grant_award_id` so SIG can answer "which deployments were federally subsidized" — a
question that matters enormously for accountability work and that no existing project answers.

---

# Part D — State and local procurement: the hard part

## D.1 The cooperative-purchasing finding (developed in detail)

### F4.26 — Cooperative purchasing is the dominant acquisition channel for surveillance tech, and the outline does not mention it at all

**Claim:** Surveillance vendors are routinely bought by local agencies through *cooperative
purchasing vehicles* — a single competitively-solicited contract held by one lead agency
that thousands of other agencies then "piggyback" on without running their own bid. This
means (a) there is often **no local RFP to find**, and (b) the master contract, its RFP,
its evaluation record and its **SKU-level price list** are frequently published as free
PDFs/XLSX by the cooperative.
**Status:** VERIFIED
**Evidence:** See F4.27–F4.31 below.
**Retrieved:** 2026-08-20
**Implication for the spec:** SIG needs a `CooperativeContract` concept distinct from a
local `Contract`: one master contract, N piggyback purchases. This changes the procurement
lifecycle model in §6.7 and the renewal-watch product in §15.4 — the *renewal date that
matters* may be the cooperative's, not the city's.
**Outline delta:** **EXTENDS §2 Layer F, §6.7, §8.10 and §15.4 — this entire channel is
absent from the outline.**

### F4.27 — Sourcewell publishes complete contract document sets, unauthenticated, at a stable URL pattern

**Claim:** `https://www.sourcewell-mn.gov/contract-search?keyword=<q>` is a server-rendered
Drupal search; each hit links to `https://www.sourcewell-mn.gov/cooperative-purchasing/<CONTRACT-NUMBER>`;
that page links directly to public PDFs and XLSX price files on `files.sourcewell.org`.
**Status:** VERIFIED — files actually downloaded and opened.
**Evidence:** Real fetches, 2026-08-20.

`GET https://www.sourcewell-mn.gov/contract-search?keyword=axon` → HTTP 200, hits:
```
/cooperative-purchasing/101223-AXN   Axon Enterprise
/cooperative-purchasing/092722-AXN   Axon Enterprise
/cooperative-purchasing/030425-NAV   NueGOV by Navjoy
/cooperative-purchasing/090122-GET   Getac
```

`GET https://www.sourcewell-mn.gov/cooperative-purchasing/101223-AXN` → HTTP 200. Extracted
document links (verbatim, all publicly downloadable):

```
https://files.sourcewell.org/public/Shared Documents/Solicitations/10765/00005124/Additional Documents/101223-AXN 8-2026.xlsx
https://files.sourcewell.org/public/Shared Documents/Solicitations/10765/00005124/Additional Documents/Fusus Appendix.pdf
https://files.sourcewell.org/public/Shared Documents/Solicitations/10765/00005124/Contract Documents/Axon Contract 101223.pdf
https://files.sourcewell.org/public/Shared Documents/Solicitations/10765/Solicitation Documents/Board Resolutions.pdf
https://files.sourcewell.org/public/Shared Documents/Solicitations/10765/Solicitation Documents/Comment and Review-Public Safety Surveillance 101223.pdf
https://files.sourcewell.org/public/Shared Documents/Solicitations/10765/Solicitation Documents/Proof of Publication-Public Safety Surveillance 101223.pdf
https://files.sourcewell.org/public/Shared Documents/Solicitations/10765/Solicitation Documents/Prop. Eval.-Public Safety Surveillance 101223.pdf
https://files.sourcewell.org/public/Shared Documents/Solicitations/10765/Solicitation Documents/Prop. Opening Record-Public Safety Surveillance 101223.pdf
https://files.sourcewell.org/public/Shared Documents/Solicitations/10765/Solicitation Documents/RFP and Addendums-Public Safety Surveillance 101223.pdf
```

Download verification:
```
Axon Contract 101223.pdf   → HTTP 200, 973,258 bytes, application/pdf, PDF 1.6
                             sha256 baa1013d5daaf92f3a525593b9511ed0c1b467a48a1c1172877052396b8713bf
101223-AXN 8-2026.xlsx     → HTTP 200, 132,519 bytes, "Microsoft Excel 2007+"
```

**Retrieved:** 2026-08-20
**Implication for the spec:** This is a fully-formed, free, structured procurement corpus.
The solicitation is literally titled **"Public Safety Surveillance"** (solicitation 10765).
Sourcewell publishes not just the contract but the **RFP, the addenda, the proposal-opening
record, the proposal evaluation, the board resolution and the proof of publication** — the
entire competitive record, which normally requires a records request.

### F4.28 — The Sourcewell price file is a machine-readable SKU catalogue, refreshed monthly

**Claim:** `101223-AXN 8-2026.xlsx` is a live, month-stamped Axon price list containing
product codes, product names, bundle flags and volume-discount tiers — including Fusus SKUs.
**Status:** VERIFIED — file opened and strings extracted.
**Evidence:** The XLSX was downloaded and its `xl/sharedStrings.xml` parsed. 2,391 shared
strings. Header strings, verbatim:

```
'Axon Hardware Equipment Volume', 'Discount Percentage', '2-99', '100-249', '250-499',
'*Product Names are subject to change without notice', '500-999', '1000+',
'Product Code', 'Product Name', 'Sales\r\nBundle', 'USD', ...
```

Product codes present include `AB21B, AB2C, AB2MuB, AB31BD, AB3C, AB3MBD, H00001–H00004,
T00001, S00016, A00030, A00031, V00022, BasicLicense, BWCamMBDTAP10Year, BWCamSBDTAP, …`
Product names matching surveillance-relevant strings include, verbatim:

```
'Axon Fusus Fixed CCTV with AI Plan'
'Axon Body - License - Fusus Livestream'
```

The filename `101223-AXN 8-2026.xlsx` encodes contract number + **August 2026** revision —
i.e. the file is versioned monthly and the current revision is this month.
**Retrieved:** 2026-08-20
**Implication for the spec:** This single file gives SIG a **canonical Product catalogue
for Axon/Fusus (§8.3)** — product code, product name, list price, bundle structure — with
no records request, no OCR, and monthly refresh. SIG should:
1. Poll the contract page monthly, diff the price file, and emit a `ProductCatalogSnapshot`.
2. Use `Product Code` as the deterministic join key when parsing agency invoices and
   purchase orders, which quote these exact SKUs. This converts invoice parsing from fuzzy
   name-matching into an exact-key join — a large accuracy win for §11 reconciliation.
3. Treat month-over-month SKU *additions* as a product-launch signal and *removals* as an
   end-of-life signal.

### F4.29 — Which vendors are and are not on Sourcewell (real search results)

**Claim:** As of 2026-08-20, Axon, Motorola Solutions, SoundThinking, gtechna, and Getac
hold Sourcewell contracts; **Flock Safety does not.**
**Status:** VERIFIED
**Evidence:** Live `contract-search?keyword=` results, 2026-08-20:

| keyword | contracts returned |
|---|---|
| `flock` | `101223-AXN` Axon Enterprise; `090122-GET` Getac — **no Flock contract** |
| `flock safety` | `090122-GET` Getac only — **no Flock contract** |
| `axon` | `101223-AXN`, `092722-AXN` Axon Enterprise; `030425-NAV` NueGOV by Navjoy; `090122-GET` Getac |
| `motorola` | `020625-MOT`, `030425-MOT`, `101223-MOT` Motorola Solutions; `102924-CMP` CompassCom; `121024-EVER` Everon; `020624-MCA` Mobile Communications (MCA); `031924-USC` UScellular |
| `soundthinking` | `030425-SND` SoundThinking |
| `genetec` | `121923-A3C` A3 Communications; `121024-EVER` Everon (resellers) |
| `license plate` | `030425-SND` SoundThinking; `080321-GTE` gtechna; `120423-DNCN` Duncan Parking/CivicSmart; `121923-A3C` A3 Communications; `042126-DESI` Designa Access; `042126-FLASH` FlashParking; `101223-KON` Konica Minolta; `030425-MIDL` MIDL Technology |

**Retrieved:** 2026-08-20
**Implication for the spec:** Two lessons. (1) Vendor→cooperative mapping is *empirical and
changes*; SIG must poll, not hard-code. (2) **Resellers matter**: A3 Communications and
Everon appear under "genetec"/"license plate" — meaning a local purchase order may name a
reseller, not the manufacturer. SIG's Vendor model (§8.2) needs a `reseller_of` /
`distributes` edge, otherwise agency purchase records will fail to link to the actual
technology vendor.
**Outline delta:** EXTENDS §8.2 and §8.3.

### F4.30 — Flock's cooperative channel is OMNIA Partners / TIPS / BuyBoard, but those are paywalled or JS-gated

**Claim:** Flock Safety is marketed through OMNIA Partners, TIPS, BuyBoard and (per third
parties) Sourcewell, but only OMNIA has a public supplier page and it exposes no contract
number or documents without login.
**Status:** PARTIALLY VERIFIED
**Evidence:**
- `https://www.omniapartners.com/suppliers/flock-safety` — HTTP 200, a real supplier page
  exists. Fetched 2026-08-20; it contains **no contract number, no lead agency, no award
  date, no expiration, and no downloadable RFP/pricing**. The page says contract
  "availability varies by organization type" and routes users to "Discover Contracts" /
  "Contact Us" — i.e. gated.
- `https://www.tips-usa.com/vendors.cfm` — **HTTP 403** to every client tried (with and
  without browser UA). INACCESSIBLE from this environment.
- `https://www.buyboard.com/Vendor` — HTTP 200 but the vendor catalogue is JS-rendered;
  `https://www.buyboard.com/Vendor/Search?searchTerm=flock` → **HTTP 404**.
- `https://www.equalisgroup.org/contracts` → **HTTP 403**.
- `https://www.naspovaluepoint.org/portfolio/` → HTTP 200 (portfolio index, JS-heavy).
- `https://www.hgacbuy.org/contracts` → HTTP 200, server-rendered. Two relevant master
  contracts found by parsing the page:
  ```
  /contracts/documents?contractid=119   EF04-21 - Law Enforcement Speed Detection & Video Equipment
  /contracts/documents?contractid=3148  SE05-26 - Video Surveillance, Access Control and Security Fencing Systems
  ```
  Fetching `contractid=3148` returns a "Solicitation Documents / Supplier Documents" page
  listing awarded suppliers (APIC Solutions LLC, Dwarpaal INC, Pavion Corp, Scientel
  Solutions LLC dba Scientel Wireless) — the document links themselves are JS-loaded.
- `https://www.gsaelibrary.gsa.gov/ElibMain/scheduleList.do` → HTTP 200; a keyword search
  for "flock" returned a page with no contract match visible in the static HTML.
- Third-party corroboration (WebSearch, 2026-08-20): a vendor-guide page states
  "Public sector buyers can price Flock Safety through OMNIA Partners, TIPS, BuyBoard, or
  Sourcewell for a 4–5% discount and pre-negotiated terms" — this is **marketing copy, not
  primary evidence**, and it conflicts with the verified Sourcewell search result showing no
  Flock contract. Treat as Tier-E.
**Retrieved:** 2026-08-20
**Implication for the spec:** Build the cooperative connector **tier-by-tier**:

| Cooperative | Access | Documents downloadable? | Connector type | Verified |
|---|---|---|---|---|
| **Sourcewell** | fully public, server-rendered Drupal | **YES** — RFP, contract, evaluation, board resolution, monthly price XLSX | HTML scrape + file fetch | ✔ downloaded |
| **HGACBuy** | public, server-rendered | partly — contract list + supplier list static; doc links JS | HTML scrape + headless for docs | ✔ HTTP 200 |
| **OMNIA Partners** | public supplier pages; contract detail gated | NO | supplier-page monitor only (detects *that* a vendor is on OMNIA) | ✔ HTTP 200 |
| **BuyBoard** | JS SPA | unknown | headless browser | ✔ HTTP 200 shell |
| **NASPO ValuePoint** | JS-heavy portfolio | partly (participating-addendum PDFs are usually public per state) | headless + per-state addendum hunt | ✔ HTTP 200 |
| **TIPS** | **403 to automated clients** | unknown | INACCESSIBLE — manual/records request | ✗ 403 |
| **Equalis** | **403** | unknown | INACCESSIBLE | ✗ 403 |
| **GSA Schedules (eLibrary/Advantage)** | public | yes (contractor T&Cs, price lists) | HTML scrape; FPDS for task orders | ✔ HTTP 200 |

### F4.31 — Why this matters for SIG's causal model

**Claim:** Cooperative purchasing breaks the assumption in §6.7 that a deployment is
preceded by a locally-visible competitive procurement.
**Status:** VERIFIED (by construction from F4.26–F4.30)
**Implication for the spec:** Three concrete design consequences:

1. **A missing local RFP is not evidence of a missing procurement.** §12's "Missing
   contract" research task must first check cooperative vehicles before flagging.
   The task text should be: *"Deployment confirmed; no local solicitation found. Check
   Sourcewell/HGACBuy/OMNIA/BuyBoard/TIPS/NASPO piggyback — most likely acquisition path."*
2. **Renewal watch (§15.4) has two clocks.** The local participating addendum / purchase
   order has one expiry; the master cooperative contract has another (Sourcewell contracts
   are typically 4-year with a base + extension). Model both;
   `Contract.parent_cooperative_contract_id` and `Contract.is_piggyback`.
3. **Price-list diffing is a cheap, high-signal change detector.** A new SKU appearing in
   `101223-AXN <month>-<year>.xlsx` is a public, timestamped, machine-readable signal that a
   vendor has launched a surveillance product — often before any agency buys it.

---

## D.2 Civic agenda and legislative-management platforms

### F4.32 — Legistar (Granicus) exposes a complete, unauthenticated, OData REST API

**Claim:** `https://webapi.legistar.com/v1/<client>/…` is open, unauthenticated, supports
OData `$filter`/`$top`/`$select`, and exposes Matters, Attachments, Histories (votes),
Events, EventItems, Persons, RollCalls and Votes.
**Status:** VERIFIED — many live calls.
**Evidence:** All 2026-08-20.

Complete endpoint surface (read from `https://webapi.legistar.com/Help`, HTTP 200):

```
GET v1/{Client}/Actions           GET v1/{Client}/Bodies              GET v1/{Client}/BodyTypes
GET v1/{Client}/CodeSections      GET v1/{Client}/Events              GET v1/{Client}/Events/{EventId}
GET v1/{Client}/Events/{EventId}/EventItems?AgendaNote=&MinutesNote=&Attachments=
GET v1/{Client}/EventDates/{BodyId}?FutureDatesOnly=
GET v1/{Client}/Indexes           GET v1/{Client}/Matters             GET v1/{Client}/Matters/{MatterId}
GET v1/{Client}/Matters/{MatterId}/Attachments
GET v1/{Client}/Matters/{MatterId}/Attachments/{MatterAttachmentId}/File
GET v1/{Client}/Matters/{MatterId}/CodeSections
GET v1/{Client}/Matters/{MatterId}/Histories?AgendaNote=&MinutesNote=
GET v1/{Client}/Matters/{MatterId}/Indexes    GET v1/{Client}/Matters/{MatterId}/Relations
GET v1/{Client}/Matters/{MatterId}/Sponsors   GET v1/{Client}/Matters/{MatterId}/Texts/{MatterTextId}
GET v1/{Client}/Matters/{MatterId}/Versions   GET v1/{Client}/MatterIndexes
GET v1/{Client}/MatterRequesters  GET v1/{Client}/MatterStatuses      GET v1/{Client}/MatterTypes
GET v1/{Client}/OfficeRecords     GET v1/{Client}/Persons             GET v1/{Client}/Persons/{PersonId}
GET v1/{Client}/EventItems/{EventItemId}/RollCalls
GET v1/{Client}/EventItems/{EventItemId}/Votes
GET v1/{Client}/Persons/{PersonId}/Votes      GET v1/{Client}/VoteTypes
(POST/PUT/DELETE variants exist for authenticated clients)
```

Live surveillance query — Oakland, `$filter=substringof('Flock',MatterTitle)`:

```
GET https://webapi.legistar.com/v1/oakland/matters?$filter=substringof('Flock',MatterTitle)
```

```
34732 | 23-0804 | City Resolution | Passed | 2023-10-10 |
  "Subject: OPD License Plate Readers, State Funding For License Plate Readers, And FLOCK
   Contract / From: Oakland Police Department / Recommendation: Adopt A Resolution: (1)
   Approving The Oakland Police Department's Revised Automated License Plate Reade…"
35569 | 24-0661 | City Resolution | Passed | 2024-07-09 |
  "Subject: OPD License Plate Readers, FLOCK, And CHP Agreement …"
36760 | 26-0189 | City Resolution | Failed | 2025-10-15 |
  "Subject: OPD Community Safety Camera System, And FLOCK Safety Contract … (1) Approving
   The Oakland Police Department Surveillance Use Policy 'DGO I-32.1 - Community Safety
   Camera Syste…"
36866 | 26-0294 | City Resolution | Passed | 2025-12-09 |
  "Subject: OPD Community Safety Cameras Policy And FLOCK Agreement …"
```

Note that matter `26-0189` **Failed** on 2025-10-15 and `26-0294` **Passed** on 2025-12-09 —
a legislative rejection followed by a successful re-submission, with policy `DGO I-32.1`
named. That is exactly a §8.14 AccountabilityEvent chain and a §8.11 Policy link, obtained
from one unauthenticated GET.

Full Matter object (Mountain View, `MatterId 8297`), verbatim excerpt:

```json
{
  "MatterId": 8297, "MatterGuid": "0B7FE07E-0596-481A-BFB1-7119B9D2262B",
  "MatterLastModifiedUtc": "2024-05-23T21:16:50.087", "MatterRowVersion": "AAAAAADOyWI=",
  "MatterFile": "203879", "MatterName": null, "MatterTitle": "Flock Public Safety Cameras",
  "MatterTypeId": 51, "MatterTypeName": "New Business",
  "MatterStatusId": 80, "MatterStatusName": "Agenda Ready",
  "MatterBodyId": 138, "MatterBodyName": "City Council",
  "MatterIntroDate": "2024-01-25T00:00:00", "MatterAgendaDate": "2024-05-28T00:00:00",
  "MatterPassedDate": null, "MatterEnactmentDate": null, "MatterEnactmentNumber": null,
  "MatterRequester": "Police Department", "MatterNotes": null, "MatterVersion": "1",
  "MatterCost": null, "MatterText2": "jennifer.crist@mountainview.gov",
  "MatterEXText1"…"MatterEXText11": null, "MatterEXDate1"…"MatterEXDate10": null,
  "MatterAgiloftId": 0, "MatterReference": "90 min",
  "MatterRestrictViewViaWeb": false, "MatterReports": []
}
```

Attachments (`/matters/36866/attachments`), verbatim first record:

```json
{
  "MatterAttachmentId": 71096, "MatterAttachmentGuid": "BE30E070-3247-46C3-97C4-26C8D0B27332",
  "MatterAttachmentLastModifiedUtc": "2025-12-11T21:45:17.09",
  "MatterAttachmentName": "View Report",
  "MatterAttachmentHyperlink": "https://oakland.legistar1.com/oakland/attachments/dc376e83-a4a8-4ece-ad37-eda580371f06.pdf",
  "MatterAttachmentFileName": "dc376e83-a4a8-4ece-ad37-eda580371f06.pdf",
  "MatterAttachmentMatterVersion": "0", "MatterAttachmentIsHyperlink": false,
  "MatterAttachmentBinary": null, "MatterAttachmentIsSupportingDocument": false,
  "MatterAttachmentShowOnInternetPage": true, "MatterAttachmentIsMinuteOrder": false,
  "MatterAttachmentIsBoardLetter": false, "MatterAttachmentAgiloftId": 0,
  "MatterAttachmentDescription": null, "MatterAttachmentPrintWithReports": true,
  "MatterAttachmentSort": 1
}
```

Matter 36866 has **15 attachments** (confirmed via `EventItems?Attachments=1`).

Histories / action record (`/matters/36866/histories`), verbatim:

```json
{
  "MatterHistoryId": 232513, "MatterHistoryEventId": 9440,
  "MatterHistoryAgendaSequence": 9, "MatterHistoryMinutesSequence": 8,
  "MatterHistoryAgendaNumber": "3.2", "MatterHistoryVersion": "1",
  "MatterHistoryActionDate": "2025-12-11T10:30:00", "MatterHistoryActionId": 27,
  "MatterHistoryActionName": "Scheduled",
  "MatterHistoryActionText": "This City Resolution be Scheduled.to go before the * Concurrent
    Meeting of the Oakland Redevelopment Successor Agency and the City Council to be heard 12/16/2025",
  "MatterHistoryActionBodyId": 22, "MatterHistoryActionBodyName": "*Rules & Legislation Committee",
  "MatterHistoryPassedFlag": null, "MatterHistoryPassedFlagName": null,
  "MatterHistoryRollCallFlag": 0, "MatterHistoryTally": null,
  "MatterHistoryMoverId": null, "MatterHistoryMoverName": null,
  "MatterHistorySeconderId": null, "MatterHistorySeconderName": null,
  "MatterHistoryMatterStatusId": 10
}
```

Event object shape (`/oakland/events?$top=1`), verbatim:

```json
{
  "EventId": 573, "EventGuid": "67808280-0FCC-4A6E-93B5-5B8445B97698",
  "EventBodyId": 13, "EventBodyName": "*Life Enrichment Committee",
  "EventDate": "2000-09-12T00:00:00", "EventTime": "1:00 PM", "EventVideoStatus": "Public",
  "EventAgendaStatusId": 2, "EventAgendaStatusName": "FINAL",
  "EventMinutesStatusId": 2, "EventMinutesStatusName": "FINAL",
  "EventLocation": "Hearing Room One", "EventAgendaFile": null, "EventMinutesFile": null,
  "EventInSiteURL": "https://oakland.legistar.com/MeetingDetail.aspx?LEGID=573&GID=134&G=…",
  "EventItems": []
}
```

**Retrieved:** 2026-08-20
**Implication for the spec:** Legistar is the **single richest structured local-government
source in R4's scope** and it is free. One client + one `$filter` yields: the legislative
item, its title (which usually contains the vendor and the dollar amount), its status,
introduction/passage/enactment dates, the sponsoring department, every attached PDF
(contracts, staff reports, surveillance-use policies), the committee routing, mover/seconder,
and roll-call votes.
**Outline delta:** **EXTENDS §2 Layer F, §8.10, §8.11, §8.14 and §12.** The outline says
"council/board agenda systems" in a bullet. It is in fact a REST API with a documented
object model, and it should be a Stage-1 connector, not a "later" item.

**Practical gotchas verified:**
- `$filter` values must be *singly* URL-encoded. Passing pre-encoded `%27` yields
  `Microsoft.Data.OData.ODataException: Syntax error: character '%' is not valid at position 12`.
- Client names are opaque slugs and must be discovered, not guessed. Verified live:
  `seattle, mountainview, sanjose, oakland, denver, longbeach, alexandria, pittsburgh,
  nashville, stpaul, kingcounty` → HTTP 200.
  `chicago, losangeles, atlanta, cityofmadison, norfolk, sunnyvale, bostoncityclerk` →
  **HTTP 500** (no such client).
  `nyc` → **HTTP 403** (client exists but API access restricted).
- `substringof('Flock', MatterTitle)` hit counts on 2026-08-20:
  `oakland` 4, `mountainview` 2, `pittsburgh` 2, `denver` 1, `stpaul` 1;
  `seattle, sanjose, longbeach, alexandria, nashville, kingcounty` 0.
  Zero results does **not** mean no Flock — Seattle discusses ALPR under other titles.
  Query `MatterTitle` **and** full text (`/Matters/{id}/Texts/{id}`) and attachment text.

### F4.33 — PrimeGov exposes an unauthenticated public-portal JSON API

**Claim:** `https://<client>.primegov.com/api/v2/PublicPortal/ListArchivedMeetings?year=YYYY`
and `.../ListUpcomingMeetings` return JSON with a per-meeting `documentList`.
**Status:** VERIFIED
**Evidence:** `GET https://lacity.primegov.com/api/v2/PublicPortal/ListArchivedMeetings?year=2025`
→ HTTP 200, 70,938 bytes, **949 meetings**. First record verbatim:

```json
{
  "id": 16238, "meetingTypeId": 1, "committeeId": 1,
  "dateTime": "2025-01-01T10:00:00", "endDateTime": "2025-01-01T19:00:00",
  "date": "Jan 01, 2025", "time": "10:00 AM", "endTime": null,
  "documentList": [
    {"id": 67359, "language": "en-US", "compileOutputType": 3, "publishStatus": 1,
     "publishDate": "2024-12-18T00:33:29.723", "templateId": 136037, "meetingId": 16238,
     "sortOrder": 1, "templateSortOrder": 1, "link": null,
     "templateName": "HTML Notice of Cancellation"},
    {"id": 67283, "compileOutputType": 1, "publishStatus": 1,
     "publishDate": "2024-12-17T23:38:56.8", "templateName": "Notice of Cancellation"}
  ],
  "allowPublicSpeaker": false, "allowPublicComment": false, "isZoomMeeting": false,
  "videoUrl": null, "swagitId": null, "isMediaManagerVideo": false,
  "externalProviderMeetingId": null, "zoomMeetingLink": null, "meetingOnline": false,
  "streamCompleted": false, "mediaManagerClipPubliclyAvailable": false,
  "meetingState": 3, "isShowVideoIcon": false, "publishDate": null,
  "title": "City Council Meeting",
  "location": "John Ferraro Council Chamber Room 340, City Hall 200 North Spring Street, Los Angeles, CA 90012"
}
```

Note `"swagitId"` — PrimeGov cross-references Swagit video IDs, giving a meeting→video link.
`sanjose.primegov.com` did **not** resolve (connection failure, code 000), as did
`cityofmesa` and `phoenix` — client subdomains must be discovered.
**Retrieved:** 2026-08-20
**Implication for the spec:** PrimeGov is item-level-poorer than Legistar (no Matter object,
no votes) but gives the full meeting/document inventory. Agenda text must be extracted from
the documents themselves.

### F4.34 — CivicClerk exposes an unauthenticated OData API **and a server-side plaintext extraction endpoint**

**Claim:** `https://<tenant>.api.civicclerk.com/v1/Events` is open OData; and
`https://<tenant>.api.civicclerk.com/v1/Meetings/GetMeetingFileStream(fileId=N,plainText=true)`
returns the **already-extracted plain text** of an agenda document.
**Status:** VERIFIED
**Evidence:**
- Tenant base URL confirmed by reading the portal SPA bundle
  `https://mesaaz.portal.civicclerk.com/assets/index-C2syNw9_.js` (371,243 bytes), which
  contains verbatim:
  ```js
  WB={localhost:"https://localhost:44339/v1",baseUrl:"https://[TENANT].api.civicclerk.com/v1"}
  ```
  and the route set `/Events`, `/Events/{id}`, `/EventsMedia/{id}`, `/Meetings/{id}`,
  `/Events/PublicCommentSignUp`, `/Events/PublicCommentWritten`, `/Events/VerifyCaptcha`,
  `/Events/VerifyCode`.
- `GET https://franklintn.api.civicclerk.com/v1/Events?$top=1` → HTTP 200, verbatim:
  ```json
  {"@odata.context":"https://franklintn.api.civicclerk.com/v1/$metadata#Events",
   "value":[{"id":77,"eventName":"Budget & Finance Committee",
    "eventDescription":"Meets 2nd Thursday of month at 1:00 PM","eventTemplateId":29,
    "eventDate":"2020-04-09T13:00:00Z","startDateTime":"2020-04-09T13:00:00Z",
    "createdOn":"2020-01-07T16:56:41.72Z","createdByUserId":"efddb35d-…",
    "isPublished":"Published","agendaId":44,"agendaName":"Budget & Finance Committee",
    "cutOffDateTime":"2020-04-03T17:00:00Z","categoryName":"Budget & Finance Committee",
    "keywords":"","visibilityId":2,"showInUpcomingEvents":false,"isOnDemandEvent":true,
    "mediaStreamPath":"https://cpmedia.azureedge.net/franklintn/…mp4", …}]}
  ```
- `GET https://portagemi.api.civicclerk.com/v1/Meetings/GetMeetingFileStream(fileId=7018,plainText=true)`
  → HTTP 200, `text/plain`, 3,288 bytes. Body begins verbatim:
  ```
  PRELIMINARY AGENDA FOR THE COUNCIL MEETING
  CITY OF PORTAGE
  MARCH 24, 2026

  6:00 p.m.  Call to Order.
  ```
- Tenant slugs must be discovered: `franklintn` and `portagemi` → 200;
  `mesaaz`, `cityofroswellga`, `roswellga`, `hendersonville` → 404 on `/v1/Events`.
**Retrieved:** 2026-08-20
**Implication for the spec:** `plainText=true` means SIG gets **server-side text extraction
for free** on CivicClerk agendas — no local PDF parsing, no OCR. Prefer this endpoint over
downloading the PDF for *search*, but still archive the PDF bytes for evidence.

### F4.35 — Platform coverage map and the `civic-scraper` prior art

**Claim:** Big Local News maintains `civic-scraper`, an actively-maintained Python library
covering five agenda platforms; SIG should extend it rather than start from zero.
**Status:** VERIFIED
**Evidence:** `https://api.github.com/repos/biglocalnews/civic-scraper` (2026-08-20):
description "Tools for downloading agendas, minutes and other documents produced by local
government"; 73 stars; **last pushed `2026-06-18T18:41:48Z`** (actively maintained);
license `NOASSERTION`.
`https://api.github.com/repos/biglocalnews/civic-scraper/contents/civic_scraper/platforms`
returns exactly:
```
['__init__.py', 'civic_clerk', 'civic_plus', 'digital_tow_path', 'granicus', 'legistar', 'primegov']
```
**Retrieved:** 2026-08-20
**Implication for the spec:** Reuse. Six platform modules already exist
(CivicClerk, CivicPlus, DigitalTowPath, Granicus, Legistar, PrimeGov). SIG's contribution
should be (a) surveillance-specific keyword classification on top, and (b) new platform
modules for the gaps below. The `NOASSERTION` license is a flag — confirm the actual LICENSE
file before vendoring code.

**Live probe results for every platform named in the brief, 2026-08-20:**

| Platform | Probe | Result | API / stable pattern? | Directory of users? |
|---|---|---|---|---|
| **Legistar** (Granicus) | `webapi.legistar.com/v1/oakland/matters` | **200, full OData** | **YES — best in class** | No official one; slugs must be crawled |
| **Granicus ViewPublisher** | `oakland.granicus.com/ViewPublisher.php?view_id=2` | **200**, 134,194 B HTML | stable URL pattern, HTML only | no |
| | `sanjose.granicus.com/ViewPublisher.php?view_id=1` | 404 | view_id varies per client | |
| **PrimeGov** | `lacity.primegov.com/api/v2/PublicPortal/ListArchivedMeetings?year=2025` | **200 JSON, 949 meetings** | **YES** | no |
| **CivicClerk** | `franklintn.api.civicclerk.com/v1/Events` | **200 OData** | **YES + plaintext extraction** | no |
| **CivicPlus / Municode** | `library.municode.com/` | 200 | code library, not agendas | Municode has a client index |
| | `api.municode.com/Clients/name?clientName=oakland` | 404 | — | |
| **NovusAgenda** | `www.novusagenda.com/agendapublic/` | 200 (2,856 B shell) | URL pattern `/agendapublic/` per client; HTML | no |
| **BoardDocs** | `go.boarddocs.com/ca/sfusd/Board.nsf/Public` | **200** (7,803 B) | Lotus-Domino; POST-driven `BD-GetMeetingsList` returned 0 bytes on GET | no |
| **IQM2 / Accela** | (IQM2 now folded into Granicus) | — | legacy `iqm2.com/Citizens/` pattern | no |
| **eScribe** | `pub-burlington.escribemeetings.com/` | **000 (no connection)** | INACCESSIBLE from this env | no |
| **Swagit** | referenced as `swagitId` inside PrimeGov JSON | — | video only | no |
| **Legistar InSite (HTML)** | `pima.legistar.com/Calendar.aspx` | 200 (95,148 B) | HTML fallback when API client is 403 | — |

**Implication for the spec — the client-discovery problem is the real work.** There is **no
public directory** mapping municipality → agenda platform for any of these vendors. SIG must
build one. Recommended method:
1. Seed from `civic-scraper` and from the EFF Atlas agency list.
2. For each agency's `.gov` domain, fetch the homepage and regex for
   `legistar.com|primegov.com|civicclerk.com|granicus.com|boarddocs.com|novusagenda.com|escribemeetings.com|iqm2.com`.
3. For Legistar, probe `webapi.legistar.com/v1/<slug>/bodies?$top=1` for candidate slugs
   derived from the domain; 200 = valid, 500 = invalid, 403 = exists-but-restricted.
4. Persist the resulting `agency → platform → client_slug` table as a first-class SIG
   artifact. **This table is itself a publishable public good the ecosystem lacks.**

---

## D.3 Public-records request portals

### F4.36 — NextRequest exposes an undocumented but fully open JSON endpoint at `/client/requests`

**Claim:** `https://<agency>.nextrequest.com/client/requests?page=1&search_term=<q>` returns
JSON with a total count and full request records including request text; and
`/client/request_documents?request_id=<id>` returns released-document metadata with direct
S3 asset URLs.
**Status:** VERIFIED — this is R4's most useful *undocumented* discovery.
**Evidence:** All 2026-08-20.

`GET https://oaklandca.nextrequest.com/requests.json?page=1` → HTTP 200 but **20 bytes,
empty** — the "obvious" endpoint is a decoy.

`GET https://oaklandca.nextrequest.com/client/requests?page=1` → HTTP 200, 25,292 bytes:

```json
{"total_count":116110,"requests":[{"request_date":"08/20/2026","staff_cost":"0.0",
 "visibility":"Published","id":"26-9663","request_state":"Open",
 "department_names":"Rent Adjustment Program","due_date":"08/31/2026",
 "poc_name":"Cynthia Jay","request_path":"/requests/26-9663",
 "request_text":"To whom it …","requester_name":null}, …]}
```

`GET https://oaklandca.nextrequest.com/client/requests?search_term=flock&page=1`
→ `total_count: 164`. Verbatim records:

```json
{"request_date":"07/07/2026","staff_cost":"0.0","visibility":"Published","id":"26-7542",
 "request_state":"Closed","department_names":"Police Department","due_date":"08/24/2026",
 "poc_name":"Alisha Banda","request_path":"/requests/26-7542","requester_name":null,
 "request_text":"Any invoices, purchase orders or other documentation pertaining to
  replacement of Flock Safety cameras, relocation of Flock Safety cameras, pole replacements
  for Flock Safety cameras, replacement of solar panels for Flock Safety cameras, or
  replacement of batteries for Flock Safety cameras since January 1, 2025."}

{"request_date":"05/09/2026","id":"26-5016","request_state":"Overdue",
 "department_names":"Police Department","due_date":"06/24/2026",
 "request_text":"Pursuant to the California Public Records Act (Government Code Section 7920
  et seq.), I am requesting the following records related to the Oakland Police Department's
  use of Flock Safety (Flock Group, Inc.) systems: 1. All contracts, agreements, purchase
  orders, and invoices between the City of Oakland and Flock Safety, Inc. 2. All current
  Flock camera locations including addresses or coordinates, and any planned future
  installations 3. Organization Audit data from the Flock system showing searches conducted
  within OPD 4. Network Audit data showing searches of Oakland's Flock network by any agency
  5. A list of all agencies Oakland has shared Flock data with, and all agencies that have
  shared Flock data with Oakland"}

{"request_date":"02/16/2025","id":"25-1834","request_state":"Closed",
 "department_names":"Police Department",
 "request_text":"A list of all agencies/organizations that share data with the Oakland
  Police Department via Flock (aka Flock Safety) which can be found in the Flock portal
  under \"Networks Shared With Me\""}
```

Released-document metadata: `GET https://oaklandca.nextrequest.com/client/request_documents?request_id=26-7542`:

```json
{"total_documents_count":2,"current_documents_count":2,"all_documents_count":2,
 "no_folder_documents_count":2,"documents_state_timestamp":1787245333,
 "documents":[{"request_id":5669311,"id":66770337,
   "title":"Records Determination Form - 26-7542.pdf","review_state":"Unprocessed","link":false,
   "document_scan":{"id":null,"document_id":66770337,"pretty_id":"26-7542",
     "title":"Records Determination Form - 26-7542.pdf","file_type":"pdf",
     "visibility":"public","document_path":"/documents/66770337",
     "upload_date":"2026-07-09T20:10:17.738-07:00"},
   "asset_url":"//nextrequestdev.s3.amazonaws.com/oaklandca/26-7542/4d06fabf-e0e6-4623-b0b7-08091ef5eb5c.pdf",
   "file_extension":"pdf","visibility":"Public","upload_date":"Uploaded: 07/09/2026",
   "folder_id":null,"exempt_from_retention":false}]}
```

Cross-agency verification:
```
oaklandca.nextrequest.com  total_count=116110 ; search_term=flock → 164
lacity.nextrequest.com     search_term=flock  → 34
sandiego.nextrequest.com   search_term=flock  → 63
sanfrancisco.nextrequest.com  /client/requests → HTTP 200
bart.nextrequest.com          /client/requests → HTTP 200
```
Non-existent subdomains return **HTTP 302 → `https://www.civicplus.com/foia-request-management/requester-direction`**
(verified for `seattle`, `sanjoseca`, `longbeach`, `sfgov`, `cityofberkeley`, `denver`,
`nashville`, `portlandoregon`, `austintexas`, `sanantonio`). That 302 is a clean liveness
probe for enumerating real instances.
**Retrieved:** 2026-08-20
**Implication for the spec:** Enormous. NextRequest gives SIG, unauthenticated:
- **Lead generation:** the *text of other people's records requests* names vendors, systems
  and networks before any document is released. Request 26-5016 above is effectively a
  ready-made SIG research task.
- **Deduplication of effort:** before SIG files a request, check whether one is already
  pending or closed at that agency (`request_state`: Open/Closed/Overdue).
- **Direct evidence acquisition:** `asset_url` is a raw S3 path to the released PDF.
- **Agency responsiveness metrics:** `request_date`, `due_date`, `request_state:"Overdue"`
  and `staff_cost` support an agency-transparency scorecard.
- **Join key:** the NextRequest `id` (`26-7542`) is the agency tracking number that matches
  MuckRock's `FOIARequest.tracking_id` (F4.7).

**Ethical constraint (§13.2):** `requester_name` was `null` in every record observed here,
but some instances publish it. The connector **must drop `requester_name` and any
requester email unconditionally** — SIG must not build a database of who files records
requests.

### F4.37 — GovQA, JustFOIA, FOIAXpress: reachable but not machine-readable

**Claim:** GovQA instances serve HTML support portals with no JSON API; published request
logs are not machine-readable without scraping.
**Status:** PARTIALLY VERIFIED
**Evidence:** 2026-08-20 —
`https://sanjoseca.govqa.us/WEBAPP/_rs/(S(x))/SupportHome.aspx` → HTTP 200, 28,173 B HTML.
`https://mesaaz.govqa.us/WEBAPP/_rs/supporthome.aspx` → HTTP 200, 28,231 B HTML.
Both are ASP.NET WebForms (viewstate-driven), meaning search requires POSTing `__VIEWSTATE`
— brittle but feasible. `https://portal.laserfiche.com/` → HTTP 200 (975 B shell).
`https://records.lacity.org/` → connection failure (000).
No JustFOIA/FOIAXpress/WebQA instance was successfully probed in this session.
**Retrieved:** 2026-08-20
**Implication for the spec:** Tier NextRequest as **connector-grade**, GovQA as
**scraper-grade (fragile, viewstate)**, JustFOIA/FOIAXpress/WebQA as **manual-only until
a named instance is identified**. Do not promise coverage of these in Stage 1.

## D.4 State legislation and state procurement portals

### F4.38 — Open States v3 requires an API key; the OpenAPI spec is public

**Claim:** `https://v3.openstates.org/` refuses all requests without a key but publishes a
machine-readable OpenAPI document.
**Status:** VERIFIED
**Evidence:** 2026-08-20 —
`GET https://v3.openstates.org/jurisdictions?classification=state&per_page=2` → **HTTP 403**:
```json
{"detail":"Must provide API Key as ?apikey or X-API-KEY. Login and visit
 https://openstates.org/account/profile/ for your API key."}
```
`GET https://v3.openstates.org/openapi.json` → **HTTP 200**. Contents:
```
info: {'title': 'Open States API v3', 'version': '2021.11.12',
       'description': '* More documentation https://docs.openstates.org/en/latest/api/v3/index.html
                       * Register for an account https://openstates.org/accounts/signup/
                       **We are currently working to restore experimental support for committees & events.**
                       During this period please note that data is not yet available for all states…'}
paths: ['/jurisdictions', '/jurisdictions/{jurisdiction_id}', '/people', '/people.geo',
        '/bills', '/bills/ocd-bill/{openstates_bill_id}', '/bills/{jurisdiction}/{session}/{bill_id}',
        '/committees', '/committees/{committee_id}', '/events', '/events/{event_id}', '/metrics']
securitySchemes: None   (key is passed as ?apikey or X-API-KEY header)
```
Docs (`https://docs.openstates.org/api-v3/`) state the key comes from
`open.pluralpolicy.com` and coverage is "state legislatures, plus DC & Puerto Rico, and
municipal governments for which we have limited support." Committees & events support is
explicitly flagged as degraded. Rate limits are not published on that page.
**Retrieved:** 2026-08-20
**Implication for the spec:** Open States serves SIG's **Policy layer (§8.11)** — state ALPR
statutes, data-retention bills, surveillance-oversight ordinances — not the deployment
layer. Its `ocd-bill` IDs are good stable external identifiers (§20 Q37). Municipal coverage
is explicitly "limited," so it does **not** substitute for Legistar. Rate limits must be
discovered empirically after obtaining a key; treat as unknown and back off aggressively.

### F4.39 — State procurement/transparency portals: reachable, but bulk data is thin and stale

**Claim:** Most state transparency portals are HTML front-ends; where bulk data exists it is
often years out of date.
**Status:** VERIFIED (sample)
**Evidence:** 2026-08-20 liveness + content probes —

| Portal | URL | Result |
|---|---|---|
| Cal eProcure | `https://caleprocure.ca.gov/pages/index.aspx` | HTTP 200, HTML only |
| CA open data (CKAN) | `https://data.ca.gov/api/3/action/package_search?q=procurement&rows=1` | **HTTP 200 — CKAN API works** |
| CA statewide PO data | `package_show?id=purchase-order-data` | dataset exists; resources are **"Purchase Order Data 2012-2015" (CSV)** + a DOCX methods file + a PDF data dictionary. **`license_title: null`.** |
| TX ESBD | `http://www.txsmartbuy.com/esbd` | HTTP 200, HTML |
| TX Socrata probe | `https://data.texas.gov/resource/qgfc-hzqd.json?$limit=1` | HTTP 404 (dataset id guess wrong) |
| FL MyFloridaMarketPlace | `https://www.myfloridamarketplace.com/` | connection failure (000) |
| NY OpenBook | `https://openbooknewyork.com/` | HTTP 200; `/api/` HTTP 200 |
| OH Checkbook | `https://checkbook.ohio.gov/` | HTTP 200 |
| OH open data | `https://data.ohio.gov/` | HTTP 200, 154 KB |
| NY Socrata | `https://data.ny.gov/api/views.json?q=contract` | HTTP 200 (catalogue queryable) |

**Retrieved:** 2026-08-20
**Implication for the spec:** The **California statewide purchase-order bulk file stops in
2015** and carries **no stated license**. This is representative: state transparency
portals are excellent for *state agency* spending and nearly useless for *municipal police*
spending, which is where surveillance lives. Two workable patterns:
1. **CKAN/Socrata catalogue crawl**: many states run CKAN (`/api/3/action/package_search`)
   or Socrata (`/api/views.json`, `/resource/<id>.json`). SIG can crawl catalogues
   generically for `procurement|contract|checkbook|vendor|purchase order` and register
   discovered datasets. This is a *dataset-discovery* connector, not a per-state connector.
2. **Municipal open-data checkbooks** (many cities publish vendor payments on Socrata) are
   far more valuable than state portals for this domain, because a line item
   "FLOCK GROUP INC — $XX,XXX" in a city checkbook is direct procurement evidence.
**Outline delta:** CORRECTS §2 Layer F's optimism about "state procurement systems."
Add: **prefer municipal checkbook datasets over state portals**; record `license: null`
explicitly rather than assuming open.

### F4.40 — GovSpend is commercial and paywalled; median ~$11.6k/yr

**Claim:** GovSpend, cited in EFF's Atlas methodology, publishes no public pricing and is a
paid SLED-procurement intelligence product.
**Status:** PARTIALLY VERIFIED (third-party pricing aggregators, not GovSpend itself)
**Evidence:** WebSearch 2026-08-20. Vendr's marketplace page reports, across 31 verified
purchases, a **median annual subscription of $11,576/year, range $8,500–$24,750/year**; a
second source estimates "$3,000–$15,000+/year depending on plan tier." GovSpend itself does
not publish pricing; it is negotiated by sales call.
Sources: `https://www.vendr.com/marketplace/gov-spend`,
`https://fed-spend.com/blog/govspend-pricing-2026-cost-alternatives`.
**Retrieved:** 2026-08-20
**Implication for the spec:** GovSpend cannot be a SIG dependency — it is paid, its terms
would forbid redistribution, and a graph built on it could not be published openly. Its
*role* (aggregating local purchase orders) must be reproduced from primary sources:
cooperative contracts (F4.27), agenda systems (F4.32–F4.34), records portals (F4.36), and
municipal checkbooks (F4.39). Note that EFF's Atlas depending on GovSpend is itself a
provenance caveat SIG should record when ingesting Atlas rows.

---

# Part E — Court records and litigation

### F4.41 — CourtListener: `/search/` and `/courts/` are open; every substantive endpoint requires a token

**Claim:** CourtListener v4 allows anonymous access to `/search/`, `/courts/` and
`/people/`, but returns HTTP 401 on `/dockets/`, `/docket-entries/`, `/recap-documents/`,
`/opinions/`, `/clusters/` and `/parties/`.
**Status:** VERIFIED
**Evidence:** 2026-08-20 —

```
GET https://www.courtlistener.com/api/rest/v4/courts/            → 200  {"count":3359,…}
GET https://www.courtlistener.com/api/rest/v4/people/            → 200
GET https://www.courtlistener.com/api/rest/v4/opinions/          → 401 {"detail":"Authentication credentials were not provided."}
GET https://www.courtlistener.com/api/rest/v4/clusters/          → 401
GET https://www.courtlistener.com/api/rest/v4/parties/           → 401
GET https://www.courtlistener.com/api/rest/v4/recap-documents/   → 401
GET https://www.courtlistener.com/api/rest/v4/docket-entries/    → 401
GET https://www.courtlistener.com/api/rest/v4/dockets/?court=ohnd&case_name__icontains=flock → 401
```

Full v4 router index (from `GET /api/rest/v4/`, HTTP 200) — the object model:
`search, dockets, bankruptcy-information, originating-court-information, docket-entries,
recap-documents, courts, audio, clusters, opinions, opinions-cited, tag, people, positions,
retention-events, educations, schools, political-affiliations, sources, aba-ratings,
parties, attorneys, recap, recap-email, recap-fetch, recap-query, fjc-integrated-database,
scrapers/scotus-email, tags, docket-tags, prayers, increment-event, visualizations/json,
visualizations, agreements, …`
`?limit=` is rejected: `{"detail":"Unknown filter parameters are not allowed.","unknown_params":["limit"]}`.
**Retrieved:** 2026-08-20

### F4.42 — Real CourtListener search result: Flock litigation is discoverable anonymously

**Claim:** A single unauthenticated search returns the docket, parties, attorneys, firms,
cause of action, and a downloadable RECAP complaint PDF path.
**Status:** VERIFIED
**Evidence:**
```
GET https://www.courtlistener.com/api/rest/v4/search/?q=%22Flock+Safety%22&type=r
```
```json
{"count":99,"document_count":525,
 "next":"https://www.courtlistener.com/api/rest/v4/search/?cursor=cz00MS4yNzQzNzYm…&q=%22Flock+Safety%22&type=r",
 "previous":null,
 "results":[{"assignedTo":"Benita Yalonda Pearson","assigned_to_id":2524,
  "attorney":["Michael Smith","Michael P. Pest"],"attorney_id":[8822632,8876932],
  "caseName":"Smith v. Flock Safety","cause":"42:1983 Civil Rights Act",
  "court":"District Court, N.D. Ohio","court_citation_string":"N.D. Ohio","court_id":"ohnd",
  "dateFiled":"2023-11-13","dateTerminated":"2024-04-15","docketNumber":"5:23-cv-02198",
  "docket_absolute_url":"/docket/67999380/smith-v-flock-safety/","docket_id":67999380,
  "firm":["Michael Smith","Duane Morris Pittsburgh"],"firm_id":[890041,897535],
  "jurisdictionType":"Federal Question","juryDemand":"Plaintiff",
  "meta":{"timestamp":"2025-06-13T07:44:39.045007Z","score":{"bm25":362.02747},"more_docs":true},
  "pacer_case_id":"301907","party":["Michael Smith","Flock Group Inc"],
  "party_id":[13221115,13150807],
  "recap_documents":[{"absolute_url":"/docket/67999380/1/smith-v-flock-safety/",
    "description":"Complaint for Permanent Injunctive Relief and Recover Damages for Product
      Liability/Defamation/Libel and Damages for Deprivation of Civil Rights with jury demand
      against Flock Safety. Filing fee $402.00 paid, receipt # 148553. Filed by Michael Smith.
      (Attachments: # 1 Exhibit 1-Website Screenshot, … # 13 Civil Cover Sheet, # 14 Summons)",
    "docket_entry_id":370501254,"document_number":1,"document_type":"PACER Document",
    "entry_date_filed":"2023-11-13","entry_number":1,
    "filepath_local":"recap/gov.uscourts.ohnd.301907/gov.uscourts.ohnd.301907.1.0.pdf",
    "id":377898249,"is_available":true,"pacer_doc_id":"141012936695","page_count":51,
    "short_description":"Complaint","snippet":"Case: 5:23-cv-02198-BYP Doc #: 1 Filed: 11/13/23 …"}]}]}
```
Search type coverage for `"Flock Safety"` on 2026-08-20:
`type=r` (RECAP) → 99 dockets / 525 documents; `type=d` (dockets) → 99;
`type=o` (opinions) → 12; `type=p` (people) → 0; `type=oa` (oral argument) → 0.
**Retrieved:** 2026-08-20
**Implication for the spec:** `party` + `party_id` gives SIG a canonical
`Flock Group Inc → party_id 13150807` anchor. `filepath_local` maps to
`https://storage.courtlistener.com/recap/gov.uscourts.<court>.<case>.<doc>.<attach>.pdf` for
the actual filing. `cause` ("42:1983 Civil Rights Act") classifies the litigation type for
§8.14 AccountabilityEvent. **Anonymous search is sufficient for discovery**; a token is
needed only to walk dockets in depth.

### F4.43 — CourtListener rate limits are the binding constraint: 5/min, 50/hour, 125/day

**Claim:** Authenticated CourtListener API access is limited to 5 requests/minute,
50/hour and 125/day on a rolling window.
**Status:** VERIFIED (documentation)
**Evidence:** `https://wiki.free.law/c/courtlistener/help/api/rest/v4/overview` (reached via
301 from `https://www.courtlistener.com/help/api/rest/`), read 2026-08-20. Auth header
format verbatim: `Authorization: Token <your-token-here>`, token from the CourtListener
profile page. Limits: "5 requests per minute / 50 requests per hour / 125 requests per day",
rolling, and "the most restrictive one — given your recent traffic — is what controls
whether the next request is accepted." No `X-RateLimit-*` headers are returned (verified by
inspecting response headers on a live `/search/` call: only `allow: GET, POST, HEAD, OPTIONS`).
The page does not state a data license.
**Retrieved:** 2026-08-20
**Implication for the spec:** **125 requests/day is severe.** SIG cannot crawl CourtListener.
Design: (a) run a weekly *search-only* sweep over a fixed vendor/technology query list,
(b) hydrate at most a handful of new dockets per day, (c) prefer Free Law Project's **bulk
data downloads** for any large-scale need, (d) never place CourtListener in a
user-request path. Absence of `X-RateLimit-*` headers means the client must self-throttle
with a local token bucket and treat HTTP 429 as authoritative.

### F4.44 — State court records are effectively unavailable programmatically. Say so plainly.

**Claim:** There is no national, machine-readable state-court record system; state trial
courts are the venue where most ALPR-evidence suppression litigation happens, and SIG cannot
ingest it automatically.
**Status:** VERIFIED by absence (no state-court API was found or tested successfully; none
is known to exist at national scale)
**Evidence:** CourtListener's coverage, per its own object model, is federal
(PACER/RECAP) plus appellate opinions; `courts` count 3,359 includes state appellate courts
for *opinions* but not trial-court dockets. No probe of a state trial-court system in this
session returned machine-readable data.
**Retrieved:** 2026-08-20
**Implication for the spec:** Write this into the design as an explicit **known coverage
gap** with a §7.2 non-goal: SIG will not attempt comprehensive state-court ingestion.
State-court AccountabilityEvents enter the graph via (a) manual contributor submission,
(b) the ALPR Abuse Library / Accountability Atlas (other workstreams), (c) news coverage
(Tier D). Every state-court claim must carry `source_tier: D or E` and a manual-entry
provenance marker. §9.4: the absence of state-court litigation for an agency is **not** a
negative claim SIG may assert.

---

# Part F — Web archiving of evidence (Q16, Q25)

### F4.45 — **`flocksafety.com` and `transparency.flocksafety.com` are EXCLUDED from the Wayback Machine**

**Claim:** The Internet Archive returns "This URL has been excluded from the Wayback Machine"
for Flock Safety's domains. There is no Wayback history for Flock portals — at all.
**Status:** VERIFIED — with controls.
**Evidence:** 2026-08-20 —

```
GET https://web.archive.org/web/2024/https://www.flocksafety.com/
  → HTTP 403, body contains: "This URL has been excluded from the Wayback Machine."

GET https://web.archive.org/web/2025/https://transparency.flocksafety.com/
  → HTTP 403, body contains: "excluded from the Wayback Machine"

CDX probes (all HTTP 200 with EMPTY result arrays):
  http://web.archive.org/cdx/search/cdx?url=flocksafety.com&output=json                      → (empty)
  http://web.archive.org/cdx/search/cdx?url=www.flocksafety.com&output=json                  → (empty)
  http://web.archive.org/cdx/search/cdx?url=flocksafety.com&matchType=domain&output=json     → []
  http://web.archive.org/cdx/search/cdx?url=transparency.flocksafety.com&matchType=prefix    → []

CONTROLS (same session, same client, all HTTP 200 with data):
  cdx?url=deflock.me            → [["urlkey","timestamp",…],["me,deflock)/","20241111144402",
                                    "https://deflock.me/","text/html","200","NXN3NAZ…","668"], …]
  cdx?url=eff.org               → [… ["org,eff)/","19961020024223","http://www.eff.org:80/", …]]
  cdx?url=atlasofsurveillance.org → [… ["org,atlasofsurveillance)/","20200713191852", …]]
  GET https://web.archive.org/web/2025/https://deflock.me/  → HTTP 200
```
**Retrieved:** 2026-08-20
**Implication for the spec:** This is the **single most consequential finding for SIG's
evidence architecture.** The vendor whose transparency portals are SIG's Layer-B primary
source has removed itself from the world's default web archive. Consequences:

1. **SIG cannot cite a Wayback URL for any Flock page.** Every existing project that does so
   (and every news article that does) has a dead citation.
2. **SIG must operate its own web archive.** This is not optional infrastructure or a
   "nice to have" — it is the only way portal snapshots (§20 Q17, §10.1 Phase 1D) can exist.
3. **Independent archival projects that already snapshot Flock portals (outline §2 Layer B)
   become critical infrastructure, not redundancy.** Their holdings may be the only record
   of pre-2026 portal states.
4. Exclusion can be applied retroactively and can be extended to other vendors at any time.
   SIG's capture pipeline must be **push-based and continuous**, not "we can always go back
   and get it later."
**Outline delta:** **EXTENDS §20 Q16/Q17/Q25 and §10.1 Phase 1D materially.** The outline
assumes portal snapshots can be obtained and asks only about cadence. The prior question —
*can they be obtained at all from third parties* — is answered: **no, not from Wayback.**

### F4.46 — Wayback availability API is unreliable; CDX is the correct interface

**Claim:** `https://archive.org/wayback/available` rate-limits aggressively (HTTP 429);
`http://web.archive.org/cdx/search/cdx` is stable and unauthenticated.
**Status:** VERIFIED
**Evidence:** 2026-08-20 — `GET https://archive.org/wayback/available?url=transparency.flocksafety.com`
returned **HTTP 429** (`<h1>429 Too Many Requests</h1> You have sent too many requests in a
given amount of time.`) on **every attempt across the whole session**, including the first.
The same client got HTTP 200 from CDX for control domains throughout.
CDX response format (verbatim, `deflock.me`):
```json
[["urlkey","timestamp","original","mimetype","statuscode","digest","length"],
 ["me,deflock)/","20241111144402","https://deflock.me/","text/html","200","NXN3NAZRKJ6LI37XR6G6LCHEDB3NLPJS","668"],
 ["me,deflock)/","20241111144412","http://deflock.me/","text/html","301","CJRJCNI7CU732QJVLTLCS7BT4FGDVOLS","279"],
 ["me,deflock)/","20241111144622","https://deflock.me/","text/html","200","NXN3NAZRKJ6LI37XR6G6LCHEDB3NLPJS","686"]]
```
**Retrieved:** 2026-08-20
**Implication for the spec:** Use CDX (`url`, `matchType`, `from`, `to`, `collapse=urlkey`,
`output=json`, `limit`) for archive lookups. The `digest` column is a base32 SHA-1 of the
payload — usable directly as an external content-address to compare against SIG's own
captures. Never depend on `/wayback/available`.

### F4.47 — Save Page Now (SPN2) requires Internet Archive S3 credentials

**Claim:** Anonymous `POST https://web.archive.org/save` is refused.
**Status:** VERIFIED
**Evidence:** 2026-08-20:
```
POST https://web.archive.org/save   (form: url=example.com, Accept: application/json)
→ HTTP 401  {"message":"You need to be logged in to use Save Page Now."}
```
**Retrieved:** 2026-08-20
**Implication for the spec:** SPN2 needs an archive.org account and its S3-style
`accesskey:secret` in an `Authorization: LOW k:s` header. Even with credentials, SPN2 would
refuse the excluded Flock domains (F4.45). SPN2 is therefore useful for SIG's *non-Flock*
citations (news articles, agency pages, cooperative contract pages) as a **redundant**
public copy — never as SIG's primary capture.

### F4.48 — archive.today is not programmatically usable

**Claim:** archive.today (archive.is/.ph/.li) has no API, aggressively blocks automation
behind CAPTCHA, and rotates domains.
**Status:** UNVERIFIED (not probed in this session; asserting the well-known operational
posture rather than a tested result — flagged per CONVENTIONS rule 1)
**Implication for the spec:** Do not build an archive.today connector. If a contributor
supplies an archive.today URL as a citation, store it as an opaque secondary reference with
`verification_status: unverified_third_party_archive`.

### F4.49 — Perma.cc was not reachable from this environment

**Claim:** Perma.cc's API could not be tested; it sits behind the same Cloudflare posture.
**Status:** INACCESSIBLE
**Evidence:** 2026-08-20 —
`GET https://api.perma.cc/v1/public/archives/?limit=1` → Cloudflare "Just a moment…"
interactive challenge (HTTP 403 equivalent).
`https://perma.cc/docs/developer` via WebFetch → **HTTP 403 Forbidden**.
**Retrieved:** 2026-08-20
**Implication for the spec:** Perma.cc's known model (free tier limited to ~10 links/month
for individuals; unlimited for subscribing libraries/courts; API key in an
`Authorization: ApiKey <key>` header) **could not be confirmed here and must be re-verified
before being written into the design.** Perma's value to SIG would be *citation permanence
for the public site*, not bulk capture; at 10 links/month it cannot be a pipeline component.
Treat as OPEN QUESTION.

### F4.50 — Recommended evidence-capture architecture

Given F4.45 (no Wayback for Flock), F4.47 (SPN2 needs auth), F4.49 (Perma unverified), and
the fact that Flock portals are JS-rendered SPAs behind Cloudflare, SIG must own capture.

**Capture tiers**

| Tier | Target | Tool | Output |
|---|---|---|---|
| **T0 static bytes** | any file with a direct URL (PDF/XLSX/CSV/ZIP) | `httpx`/`curl` + `warcio` WARC-wrapping | WARC + raw file |
| **T1 static HTML** | server-rendered pages (Sourcewell, HGACBuy, Legistar InSite) | `wget --warc-file` or `warcio.capture` | WARC + raw HTML |
| **T2 JS/SPA + Cloudflare** | Flock transparency portals, CivicClerk/BuyBoard SPAs | **Browsertrix Crawler** (Playwright + `pywb` writer) | WARC (incl. XHR responses) + full-page PNG + print-to-PDF |
| **T3 API JSON** | Legistar/PrimeGov/CivicClerk/NextRequest/USAspending | native client; store request+response envelope | canonical-JSON blob |

**Why Browsertrix for T2:** Flock portals are single-page apps whose content arrives via
XHR. `wget --warc` captures the shell and nothing else. Browsertrix Crawler drives a real
Chromium via Playwright, records **every network response into the WARC** (including the
JSON XHRs that hold the actual camera counts and sharing lists), handles Cloudflare's JS
challenge because it is a real browser, and emits WARCs that `pywb` can replay. The
practical stack:
- `webrecorder/browsertrix-crawler` (Docker) for capture,
- `pywb` for replay and for serving SIG's own "wayback" of captured evidence,
- `warcio` (Python) for programmatic WARC read/write and for wrapping non-browser fetches,
- `wacz` packaging so a single evidence bundle is one addressable file.

**What gets captured, for every EvidenceArtifact (§8.15):**

```
capture_id            uuid7
source_url            exact URL fetched
request_headers       normalized (UA, Accept), secrets redacted
http_status
response_headers      incl. ETag, Last-Modified, Content-Type
captured_at           observation time (§9.2)
capture_method        httpx | wget-warc | browsertrix | api-client
raw_bytes_sha256      PRIMARY CONTENT ADDRESS
raw_bytes_size
warc_sha256           hash of the WARC/WACZ envelope
screenshot_sha256     full-page PNG (T2 only)
pdf_render_sha256     print-to-PDF (T2 only)
extracted_text_sha256 output of the parse stage
extracted_json        for API sources: canonicalized JSON (sorted keys, no whitespace)
dom_snapshot_sha256   post-render serialized DOM (T2 only)
storage_uri           s3://sig-evidence/<sha256[0:2]>/<sha256[2:4]>/<sha256>
license_class         public_record | vendor_copyright | platform_metadata | unknown
publication_class     public | metadata_only | restricted     (§13.4, §20 Q31)
```

**Content addressing (answers §20 Q25):** address by **SHA-256 of the raw response body**,
stored at a two-level fan-out path. Rationale over alternatives:
- Not SHA-1 — DocumentCloud gives SHA-1 (`file_hash`) and Wayback CDX gives base32 SHA-1;
  store those as *foreign* digests in separate columns for cross-checking, but do not adopt
  a broken hash as the primary key.
- Not the URL — URLs change, portals move, and the same PDF appears at N URLs.
- Not a normalized/parsed form — normalization is lossy and versioned; the immutable thing
  is the byte string received.
- Store a **separate** `semantic_sha256` over the *canonicalized extraction* so that a
  cosmetically-changed PDF (new footer timestamp) does not falsely register as a content
  change in §11 reconciliation. Two hashes, two purposes: `raw_bytes_sha256` for provenance,
  `semantic_sha256` for change detection.

**Storage:** object store (S3/R2/MinIO) keyed by hash; a Postgres `evidence_artifact` table
holds metadata and the license/publication class; **no bytes in the database**. Retain WARCs
indefinitely; they are the only defensible record for excluded domains.

**Snapshot cadence (§20 Q17), informed by F4.45:** because there is *no* third-party
fallback for Flock portals, portal capture cadence must be higher than would otherwise be
justified. Recommend: weekly for portals with known active deployments, daily during an
active reconciliation or accountability event, and immediate capture on any detected change
via cheap HEAD/ETag polling between full captures.

---

# Part G — Document parsing architecture (Q26)

### F4.51 — Recommended parsing stack

**Status:** RECOMMENDATION (tooling not installed/benchmarked in this session — the local
environment had neither `pdftotext` nor `pdfplumber` available, verified 2026-08-20)

**Stage 0 — Classification before parsing.** Never dispatch on file extension alone.
Agencies mislabel constantly (`.pdf` that is a TIFF, `.xls` that is HTML, `.doc` that is RTF).

```
1. libmagic (python-magic) on the first 8 KB   → true MIME
2. extension                                    → hint only
3. for PDFs: PyMuPDF page-level text density
      chars_per_page > 100  → born-digital text PDF
      chars_per_page ~ 0 and images present → scanned → OCR path
      mixed → per-page routing (very common: digital cover letter + scanned attachment)
4. structural probe: is it a form? a table-heavy report? an email thread? a policy manual?
5. classify into a SIG document_type taxonomy (below)
```

**SIG document_type taxonomy** (mirror ALPR Watch's approach of classifying before
extracting; each type gets a dedicated extractor and its own confidence model):

```
contract_master            invoice                   purchase_order
quote_or_proposal          cooperative_price_list    grant_application
grant_award_letter         council_agenda            council_staff_report
council_minutes            surveillance_use_policy   retention_policy
audit_log_export           camera_location_list      network_sharing_list
mou_or_data_sharing_agmt   rfp_or_solicitation       bid_tabulation
correspondence_email       records_response_letter   denial_or_exemption_letter
court_filing               vendor_marketing          unknown
```

**Stage 1 — Format-specific extraction**

| Input | Primary tool | Fallback | Notes |
|---|---|---|---|
| Born-digital PDF text | **PyMuPDF (`fitz`)** | `pdfplumber` | PyMuPDF is 10–50× faster and gives word-level bboxes needed for §15.5 excerpt highlighting |
| PDF layout/word boxes | **pdfplumber** | PyMuPDF `get_text("words")` | pdfplumber's char-level model is better for ruled tables |
| Scanned PDF OCR | **ocrmypdf** (Tesseract, `--skip-text --rotate-pages --deskew`) | **Surya** or **PaddleOCR** for hard scans | ocrmypdf writes a text layer *back into the PDF*, preserving the original as evidence |
| Table extraction, ruled | **Camelot** (`flavor="lattice"`) | `pdfplumber.extract_tables` | ruled tables = most contract exhibits |
| Table extraction, unruled | **Camelot** (`flavor="stream"`) → **img2table** | `Tabula` (JVM) | unruled tables are where most extraction errors live |
| Table extraction, scanned | **img2table** (+ OCR engine) | **Docling** | |
| Whole-document → structured MD | **Docling** or **Marker** | — | good for policy manuals and long staff reports; slower, GPU-friendly |
| XLSX | **`calamine`** via `python-calamine` (fast, Rust) → **polars**/**pandas** | `openpyxl` (needed for merged-cell ranges, comments, and multiple sheets) | see F4.52 |
| XLS (legacy) | `xlrd<2` or LibreOffice `--convert-to xlsx` | | |
| CSV/TSV | **polars** `read_csv` with `infer_schema_length=None`, `ignore_errors=False` | pandas | detect encoding with `charset-normalizer`; expect cp1252 and UTF-16LE |
| HTML | **selectolax** (fast CSS) for structure; **trafilatura** for article body | `lxml` | |
| Email `.eml`/`.msg` | stdlib `email` + `extract-msg` for Outlook `.msg` | | agencies routinely export request threads as `.msg` |
| ZIP/7z/RAR | `zipfile`/`py7zr`/`rarfile`, **recursive with depth and size caps** | | see F4.53 |
| DOCX/DOC | `python-docx`; LibreOffice headless for `.doc`/`.wpd` | | |
| Images (TIFF/JPEG faxes) | `img2pdf` → ocrmypdf | | multipage TIFF is the classic fax artifact |

**Stage 2 — Structured extraction (facts out of text)**

Three-tier, in order of preference. Never skip to tier 3.

1. **Deterministic key joins.** Where a known key exists, use it. The Sourcewell price file
   (F4.28) gives Axon `Product Code`s; invoices quote those exact SKUs. USAspending gives
   UEIs. Legistar gives `MatterFile`. NextRequest gives tracking IDs. Deterministic joins
   are auditable and free.
2. **Regex/rule extractors per document_type.** Contract effective dates, dollar amounts,
   term lengths, renewal-option counts, retention-day counts, camera counts. Each rule
   emits a Claim (§8.16) with `extraction_method: "rule:<rule_id>@<version>"` and a
   character offset into the extracted text, so §15.5 can show the exact excerpt.
3. **LLM structured extraction — bounded, and only where 1 and 2 fail.**
   - **Appropriate for:** classifying document_type; pulling a defined JSON schema out of
     prose staff reports; normalizing wildly-variant agency phrasing ("30 days",
     "thirty (30) days", "1 month") into a canonical value; summarizing a policy section.
   - **Inappropriate for:** anything where a deterministic parser exists; reading numbers
     off a table image (use table extraction + OCR confidence instead); deciding whether two
     agencies are the same entity; producing coordinates; asserting a negative claim.
   - **Mandatory guardrails:** (a) the model is given only the *extracted text*, never asked
     to look at an image and guess; (b) output is a strict JSON schema with an explicit
     `not_found` value for every field; (c) **every extracted value must be accompanied by a
     verbatim `source_span` that is then checked to actually occur in the source text** —
     if it does not, the extraction is discarded as a hallucination; (d) results go to a
     review queue at `confidence < threshold`, per §20 Q28; (e) the model, prompt hash and
     version are recorded in `extraction_method` so extractions can be invalidated en masse
     when a model changes; (f) LLM-derived claims can never exceed Tier C confidence and can
     never silently overwrite a rule- or key-derived claim.

### F4.52 — The messy realities, and what to do about each

**Status:** RECOMMENDATION grounded in verified artifacts encountered this session.

| Reality | Handling |
|---|---|
| **Scanned faxes** (skewed, 200 dpi, multipage TIFF) | `img2pdf` → `ocrmypdf --deskew --rotate-pages --clean`; store per-page OCR confidence; below a threshold, flag the *page* (not the doc) for human review. Never let a low-confidence OCR page produce a numeric claim (e.g. a camera count) without review. |
| **Mixed-format ZIPs** (`response.zip` = 3 PDFs + 1 XLSX + a nested ZIP) | Recursive unpack with **depth ≤ 4, total-expansion ≤ 100×, entry-count ≤ 5,000, absolute-path/`..` rejection** (zip-bomb and zip-slip defence). Every extracted member becomes its own EvidenceArtifact with `parent_artifact_id` and its own SHA-256. |
| **XLSX with merged headers** | `calamine` for speed loses merge info — use `openpyxl` to read `ws.merged_cells.ranges`, forward-fill merged header cells across their span, then reconstruct a multi-index header. Detect the header row by scanning for the first row where ≥60% of cells are non-numeric strings. The verified Axon price file (F4.28) has exactly this shape: a volume-discount band header (`2-99 / 100-249 / 250-499 / 500-999 / 1000+`) sitting above `Product Code / Product Name / Sales Bundle / USD`. |
| **Password-protected PDFs** | Try empty password first (very common: owner-password-only PDFs that block *extraction* but not *opening* — `pikepdf` can strip these legally for a document you lawfully possess). If a user password is required, record `status: encrypted_unreadable`, keep the bytes, and generate a research task to request an unlocked copy. Never brute-force. |
| **Native Excel exports with multiple sheets** | Enumerate *all* sheets; do not assume sheet 0. Classify each sheet independently (a workbook often has `README`, `Data`, `Pivot`, `Notes`). Record `sheet_name` on every extracted row for provenance. |
| **Double-encoded UTF-8 mojibake** | Verified live in USAspending sub-award descriptions (F4.23): `SHERIFFÃƑÂ¢Ã¢Â€ŠÂ¬S`. Run `ftfy.fix_text()` on all free-text before keyword matching and before storage; keep the raw string alongside. |
| **HTML files with `.xls` extension** | Detected by libmagic in stage 0; parse with `pandas.read_html`/selectolax. |
| **Redaction boxes over live text** | A black rectangle drawn over text that is still in the content stream. SIG must **detect** this (text under a filled rect) and, per §13.4, treat the underlying text as sensitive: do not index it, do not publish it, flag the artifact `contains_failed_redaction: true` and restrict it. This is an ethics requirement, not a feature. |
| **Documents containing plate numbers / personal data** | Run a detector (plate-like regex + NER for person names + address patterns) on every extracted text before it enters any public index. Route hits to `publication_class: metadata_only` per §13.2/§20 Q30–Q31. |
| **Agency emails as evidence** | `.eml`/`.msg` threads contain staff names and addresses. Extract the *substantive* body; strip signature blocks, direct phone numbers and personal emails before storage. |

### F4.53 — Parse-stage output contract

Every parse run emits, per artifact:

```
artifact_sha256, parser_name, parser_version, parser_config_hash, parsed_at,
document_type, document_type_confidence,
page_count, ocr_applied, ocr_engine, ocr_mean_confidence,
extracted_text_sha256, extracted_text_storage_uri,
tables[]  { page, bbox, extractor, cells, extraction_confidence },
claims[]  { claim_type, value, unit, source_page, source_char_start, source_char_end,
            source_span_verbatim, extraction_method, confidence },
warnings[] { code, detail }      # e.g. ENCRYPTED, LOW_OCR_CONF, MOJIBAKE_REPAIRED,
                                 #      FAILED_REDACTION_SUSPECTED, MERGED_HEADER_INFERRED
```

Parsers are **pure and versioned**: re-running parser v2 over the same `artifact_sha256`
must produce a new parse record, never mutate the old one. This is what makes §9.2
bitemporality work at the evidence layer — a claim's *validity* can change because the
parser improved, independently of when the document was observed.

---

# Access matrix

Legend — **Verified?** ✔ = an actual request was made this session and the stated behaviour
observed; ✗ = attempted and failed (recorded as such); – = not tested.

| Source | Endpoint | Auth | Rate limit | Format | License / terms | Verified? |
|---|---|---|---|---|---|---|
| MuckRock v2 | `https://www.muckrock.com/api_v2/{requests,communications,agencies,files,jurisdictions,users,statistics,organizations,projects}/` | **Bearer JWT**, 5-min TTL, from `accounts.muckrock.com/api/token/` | 15/min, burst 100; 5/min on users+orgs | JSON, page-based (`page_size`, default 50) | ToS: no data mining, no commercial reuse, all rights reserved. **Link-only for platform metadata** | ✔ 401 on all data endpoints |
| MuckRock v1 | `https://www.muckrock.com/api_v1/foia/` | same | same | JSON | same | ✔ 401 (via origin), 403 CF via curl |
| DocumentCloud search | `https://api.www.documentcloud.org/api/documents/search/?q=` | **none** | not published; none hit | JSON, **cursor** paging | shared MuckRock ToS; documents are third-party works | ✔ live data |
| DocumentCloud assets | `https://s3.documentcloud.org/documents/<id>/<slug>.{pdf,txt}` and `/pages/<slug>-p<N>-large.gif` | **none** | CDN bot rules block some clients | PDF / text / GIF | per-document; `access` ∈ public/organization/private/invisible | ✔ `.txt` fetched |
| USAspending awards | `POST https://api.usaspending.gov/api/v2/search/spending_by_award/` | **none** | none published; none hit | JSON | US Government work — public domain | ✔ live data |
| USAspending sub-awards | same, `"subawards": true` | **none** | none hit | JSON | public domain | ✔ live LPR hits |
| USAspending recipient | `GET /api/v2/recipient/duns/<recipient_id>/` | **none** | none hit | JSON | public domain | ✔ Flock UEI |
| SAM.gov entity | `https://api.sam.gov/entity-information/v3/entities` | **SAM.gov API key** | **10/day** (no role) → 1,000/day (role) → 10,000/day (fed system) | JSON / async CSV | US Gov; hierarchy is FOUO | ✗ 404 keyless; docs ✔ |
| SAM.gov opportunities | `https://api.sam.gov/opportunities/v2/search` | SAM key | as above | JSON | US Gov | ✗ 404 keyless |
| **Sourcewell search** | `https://www.sourcewell-mn.gov/contract-search?keyword=` | **none** | none hit | HTML (server-rendered) | public agency; no stated license | ✔ live |
| **Sourcewell contract** | `https://www.sourcewell-mn.gov/cooperative-purchasing/<CONTRACT-NO>` | **none** | none hit | HTML → PDF/XLSX | public record | ✔ live |
| **Sourcewell files** | `https://files.sourcewell.org/public/Shared Documents/Solicitations/<id>/…` | **none** | none hit | PDF, XLSX | public record | ✔ 973 KB PDF + 132 KB XLSX downloaded |
| HGACBuy | `https://www.hgacbuy.org/contracts` , `/contracts/documents?contractid=<n>` | none | none hit | HTML (+ JS doc links) | public agency | ✔ 200 |
| OMNIA Partners | `https://www.omniapartners.com/suppliers/<vendor>` | none for the stub page; **gated for contracts** | – | HTML | commercial co-op | ✔ 200, no contract data |
| BuyBoard | `https://www.buyboard.com/Vendor` | none | – | JS SPA | commercial co-op | ✔ 200 shell; `/Vendor/Search` 404 |
| NASPO ValuePoint | `https://www.naspovaluepoint.org/portfolio/` | none | – | JS | co-op | ✔ 200 |
| TIPS | `https://www.tips-usa.com/vendors.cfm` | — | — | — | — | ✗ **403** |
| Equalis | `https://www.equalisgroup.org/contracts` | — | — | — | — | ✗ **403** |
| GSA eLibrary | `https://www.gsaelibrary.gsa.gov/ElibMain/…` | none | – | HTML | US Gov | ✔ 200 |
| **Legistar** | `https://webapi.legistar.com/v1/<client>/{matters,events,eventitems,persons,votes,rollcalls,bodies,…}` | **none** | none hit | JSON, OData `$filter/$top/$select` | Granicus-hosted public records | ✔ live Flock matters |
| Legistar attachments | `…/matters/<id>/attachments` → `https://<client>.legistar1.com/<client>/attachments/<uuid>.pdf` | none | none hit | PDF | public record | ✔ 15 attachments listed |
| **PrimeGov** | `https://<client>.primegov.com/api/v2/PublicPortal/ListArchivedMeetings?year=` | **none** | none hit | JSON | public record | ✔ 949 LA meetings |
| **CivicClerk** | `https://<tenant>.api.civicclerk.com/v1/Events` (OData) | **none** | none hit | JSON | public record | ✔ live |
| CivicClerk text | `…/v1/Meetings/GetMeetingFileStream(fileId=<n>,plainText=true)` | **none** | none hit | text/plain | public record | ✔ agenda text |
| Granicus ViewPublisher | `https://<client>.granicus.com/ViewPublisher.php?view_id=<n>` | none | – | HTML | public record | ✔ 200 (oakland) |
| NovusAgenda | `https://www.novusagenda.com/agendapublic/` | none | – | HTML | public record | ✔ 200 |
| BoardDocs | `https://go.boarddocs.com/<st>/<client>/Board.nsf/Public` | none | – | HTML/Domino POST | public record | ✔ 200 |
| eScribe | `https://pub-<client>.escribemeetings.com/` | – | – | – | – | ✗ no connection |
| **NextRequest** | `https://<agency>.nextrequest.com/client/requests?page=&search_term=` | **none** | none hit | JSON | agency public records | ✔ 116,110 Oakland requests |
| NextRequest docs | `…/client/request_documents?request_id=<id>` → `//nextrequestdev.s3.amazonaws.com/<agency>/<id>/<uuid>.pdf` | **none** | none hit | JSON → PDF | public record | ✔ live |
| GovQA | `https://<agency>.govqa.us/WEBAPP/_rs/supporthome.aspx` | none | – | ASP.NET WebForms HTML | public record | ✔ 200 |
| Open States v3 | `https://v3.openstates.org/{bills,people,events,committees,jurisdictions}` | **API key** (`?apikey` or `X-API-KEY`) | not published | JSON | not stated on docs page | ✗ 403 keyless; `openapi.json` ✔ 200 |
| CourtListener search | `https://www.courtlistener.com/api/rest/v4/search/?q=&type=r\|d\|o` | **none** | 5/min · 50/hr · 125/day (authed); anon lower | JSON, cursor | not stated in v4 overview | ✔ 99 Flock dockets |
| CourtListener courts/people | `…/v4/{courts,people}/` | none | as above | JSON | — | ✔ 200 |
| CourtListener dockets/etc. | `…/v4/{dockets,docket-entries,recap-documents,opinions,clusters,parties}/` | **Token** (`Authorization: Token …`) | as above | JSON | — | ✔ 401 |
| Wayback CDX | `http://web.archive.org/cdx/search/cdx?url=&output=json` | none | soft | JSON array | IA terms | ✔ live |
| Wayback availability | `https://archive.org/wayback/available?url=` | none | **hard; 429 every attempt** | JSON | IA terms | ✗ 429 |
| Wayback replay | `https://web.archive.org/web/<ts>/<url>` | none | soft | HTML | IA terms | ✔ 200 control / **403 excluded for flocksafety.com** |
| Save Page Now 2 | `POST https://web.archive.org/save` | **IA S3 keys** | per-account | JSON | IA terms | ✗ 401 |
| Perma.cc | `https://api.perma.cc/v1/…` | API key | free tier ~10 links/mo (unconfirmed) | JSON | — | ✗ Cloudflare |
| CA open data (CKAN) | `https://data.ca.gov/api/3/action/package_search` | none | – | JSON | **`license_title: null`** on the PO dataset | ✔ 200 |
| CA statewide POs | `purchase-order-data` resources | none | – | CSV | none stated | ✔ **only 2012–2015** |
| civic-scraper | `github.com/biglocalnews/civic-scraper` | — | — | Python lib | **`NOASSERTION`** — verify LICENSE before vendoring | ✔ API metadata |
| GovSpend | commercial | paid | — | — | proprietary; not redistributable | – (pricing via third parties) |

---

# Corrections and extensions to the outline (consolidated)

| # | Outline § | Delta | Detail |
|---|---|---|---|
| 1 | §2 Layer F, §21 | **CORRECTS** | MuckRock's documented API is `api_v2`, not `api_v1`; nine typed resources, JWT auth, 15 req/min (F4.1, F4.4) |
| 2 | §10.1 Phase 1A | **CORRECTS** | MuckRock jurisdiction IDs are a weak identity anchor: 3-level hierarchy, locals cannot be parents, no FIPS/GEOID, and resolving them requires auth. Demote to alias/crosswalk (F4.5) |
| 3 | §20 Q9, §6.1 | **CORRECTS** | MuckRock Agency objects contain no ORI, no address, no website — only name/slug/jurisdiction/types. Agency→Organization matching must be a review queue (F4.6) |
| 4 | §2 Layer F | **CORRECTS** | USAspending covers ~$252,600 of Flock's business. It is a vendor-identity and grant-flow source, **not** a procurement source (F4.19, F4.22) |
| 5 | §2 Layer F, §12, §8.10 | **EXTENDS** | Federal grant → local surveillance is programmatically traceable via USAspending `subawards:true` + keyword. Verified hits for Byrne JAG (Orange Cty FL LPR), FDLE→Volusia LPR, UASI→Indiana State Police FR/LPR (F4.23) |
| 6 | §8.10 | **EXTENDS** | Contract entity needs `funding_source` / `grant_award_id`, `is_piggyback`, `parent_cooperative_contract_id` (F4.25, F4.31) |
| 7 | §2 Layer F, §6.7, §15.4 | **EXTENDS** | **Cooperative purchasing is absent from the outline** and is the dominant acquisition channel. Sourcewell publishes the entire competitive record + a monthly SKU price file, free (F4.26–F4.31) |
| 8 | §8.2, §8.3 | **EXTENDS** | Vendor needs `uei`/`cage`/`duns`; and a `reseller_of` edge — agency POs name resellers (A3 Communications, Everon) not manufacturers (F4.20, F4.29) |
| 9 | §2 Layer F, §12 | **EXTENDS** | Legistar is a full OData REST API, not "an agenda system". Stage-1 connector. Real Oakland Flock resolutions with pass/fail history retrieved (F4.32) |
| 10 | §2 Layer F | **EXTENDS** | NextRequest's undocumented `/client/requests` and `/client/request_documents` give request text + released-document S3 URLs, unauthenticated (F4.36) |
| 11 | §20 Q16 | **ANSWERS** | Archive/link policy table by rights-holder class (F4.16) |
| 12 | §20 Q17, Q25, §10.1 Phase 1D | **EXTENDS/CORRECTS** | **`flocksafety.com` and `transparency.flocksafety.com` are excluded from the Wayback Machine.** Portal snapshots cannot be obtained from third parties; SIG must run its own WARC capture (F4.45) |
| 13 | §20 Q35 | **CORRECTS** | Research tasks cannot link into MuckRock crowdsource programmatically — no such v2 endpoint. But tasks **can** be materialized as actual FOIA filings via the create endpoint (F4.10, F4.11) |
| 14 | §7.2, §9.4 | **EXTENDS** | State-court records are a hard, permanent coverage gap; make it an explicit non-goal and forbid negative claims there (F4.44) |
| 15 | §14.2 | **EXTENDS** | Needs a `redistribution: link_only` license class; MuckRock/DocumentCloud platform metadata is the first instance (F4.9) |
| 16 | §2 Layer F | **CORRECTS** | GovSpend (cited by Atlas methodology) is paid (~$11.6k/yr median) and not redistributable; SIG must reproduce its function from primary sources (F4.40) |
| 17 | §20 Q26 | **ANSWERS** | Classification-first parser architecture with a 22-type document taxonomy, three-tier extraction, and hard LLM guardrails (F4.51–F4.53) |

---

## Open questions

1. **MuckRock account terms for an automated consumer.** The ToS forbids "data mining,
   robots, or similar data gathering and extraction tools" while MuckRock simultaneously
   ships a rate-limited API. Whether a scheduled API sync is *sanctioned* use is a question
   for MuckRock, not for inference. **Action: contact MuckRock and obtain written
   confirmation of the intended use before building the connector.** Hedge: build the
   connector behind a feature flag; ship the DocumentCloud connector (which is
   unauthenticated and explicitly invites exploration) first.

2. **DocumentCloud rate limits are unpublished.** No throttling was observed, but the
   official API documentation is a client-rendered Notion page that could not be read
   programmatically. Hedge: self-throttle to ~1 req/sec, honour 429 with exponential
   backoff, and identify the client with a descriptive User-Agent and contact URL.

3. **CourtListener data license.** The v4 overview page does not state one. Free Law
   Project's bulk data is generally treated as public-domain court records plus
   CC-licensed metadata, but this was not verified. Hedge: cite and link; do not republish
   CourtListener-derived metadata in bulk until the license is confirmed.

4. **Open States rate limits and license.** Neither is published on the pages read. Hedge:
   obtain a key, measure empirically, and treat Open States as an enrichment source whose
   data is linked rather than mirrored.

5. **Perma.cc could not be reached.** Its API model, quota and pricing must be re-verified
   from a different network before any design decision depends on it.

6. **TIPS and Equalis returned 403 to every automated client.** Whether their contract
   documents are public at all is unresolved. Hedge: manual review, or a public-records
   request to a *participating agency* for the piggyback documentation (which is a public
   record even when the cooperative's own site is closed).

7. **No directory exists mapping municipality → agenda platform → client slug.** SIG must
   build it (method in F4.35). Estimated coverage is unknown until built; do not promise a
   coverage percentage in Stage 1.

8. **Legistar `nyc` returns 403 while other clients return 200.** Whether this is a
   per-client toggle, an IP block, or a licensing tier is unknown. Some large jurisdictions
   may be permanently API-closed and require InSite HTML scraping.

9. **CivicClerk tenant slugs are not derivable from portal subdomains** (`mesaaz.portal…`
   exists but `mesaaz.api…` 404s). The mapping rule is unknown; discovery may require
   reading each portal's runtime config.

10. **Sourcewell/HGACBuy terms of use were not located.** Both are public entities and the
    documents are public records, but no explicit license statement was found. Hedge: record
    `license: unstated_public_agency`, attribute the source, and archive rather than
    republish the vendor-authored price files wholesale (the *contract* is a public record;
    a vendor's price list embedded in it may carry vendor copyright).

11. **Whether Flock holds cooperative contracts at all.** Verified: not on Sourcewell.
    Marketing copy claims OMNIA/TIPS/BuyBoard. Unresolved and worth a targeted records
    request, because it determines how most Flock purchases are legally justified.

12. **Whether the Wayback exclusion of `flocksafety.com` extends to third-party pages that
    embed Flock content**, and whether independent portal-archival projects (§2 Layer B)
    have holdings that predate the exclusion. This determines how much history is
    recoverable at all.

---

## Spec requirements emitted

**Identity and vendor model**

- **REQ-R4-01** — Vendor entities MUST carry `uei`, `cage_code`, legacy `duns`, and
  `usaspending_recipient_id`. UEI is the canonical vendor key for any federally-registered
  vendor. (Flock Group Inc = `QDLLBKCGL851`.)
- **REQ-R4-02** — Vendor entities MUST support a `reseller_of` / `distributes` edge, and
  procurement extraction MUST attempt manufacturer resolution when a record names a reseller.
- **REQ-R4-03** — MuckRock jurisdiction and agency IDs MUST be stored as crosswalk aliases,
  never as SIG's canonical jurisdiction or organization keys.
- **REQ-R4-04** — Agency name → SIG Organization matches derived from MuckRock, NextRequest,
  or agenda-system data MUST be written to a review queue, not committed automatically.

**Connectors**

- **REQ-R4-05** — The DocumentCloud connector MUST use `https://api.www.documentcloud.org/api/documents/search/`,
  follow `next` cursors, persist the cursor for resumability, self-throttle to ≤1 req/sec,
  and honour HTTP 429.
- **REQ-R4-06** — The MuckRock connector MUST target `api_v2`, refresh its bearer token on a
  TTL < 5 minutes, self-limit to 15 req/min (5 req/min for `users`/`organizations`), and
  hard-filter `embargo_status == "public"` before any write.
- **REQ-R4-07** — The MuckRock connector MUST NOT scrape muckrock.com HTML.
- **REQ-R4-08** — SIG MUST implement a Legistar connector using
  `https://webapi.legistar.com/v1/<client>/`, singly-URL-encoding OData `$filter` values, and
  MUST ingest Matters, MatterAttachments, MatterHistories, MatterTexts, Events, EventItems,
  Persons and Votes.
- **REQ-R4-09** — SIG MUST implement PrimeGov (`/api/v2/PublicPortal/List{Archived,Upcoming}Meetings`)
  and CivicClerk (`/v1/Events` OData) connectors, and MUST prefer CivicClerk's
  `GetMeetingFileStream(fileId=…,plainText=true)` for text over local PDF parsing while still
  archiving the PDF bytes.
- **REQ-R4-10** — SIG MUST build and publish an `agency → agenda_platform → client_slug`
  directory, populated by domain-fingerprinting and slug probing, as a standalone dataset.
- **REQ-R4-11** — SIG MUST implement a NextRequest connector using `/client/requests` and
  `/client/request_documents`, and MUST use the 302-to-civicplus.com redirect as the
  instance-liveness probe.
- **REQ-R4-12** — The NextRequest connector MUST discard `requester_name`, requester email
  and any other requester-identifying field before persistence. (§13.2)
- **REQ-R4-13** — SIG MUST implement a cooperative-purchasing connector covering, at minimum,
  Sourcewell (`/contract-search?keyword=` → `/cooperative-purchasing/<no>` → `files.sourcewell.org`)
  and HGACBuy, and MUST re-poll each tracked contract monthly.
- **REQ-R4-14** — The cooperative connector MUST parse vendor price files into a
  `ProductCatalogSnapshot` (product code, product name, bundle flag, volume-discount tiers,
  effective month) and MUST diff snapshots to emit product-added / product-removed events.
- **REQ-R4-15** — SIG MUST run a scheduled USAspending sub-award miner over the CFDA set
  {16.738, 16.710, 97.067, 97.078} × a surveillance keyword list, with `subawards: true`, and
  MUST re-verify every hit by matching the keyword against `Sub-Award Description` itself
  (the API's keyword filter also matches prime-award text).
- **REQ-R4-16** — All free text from USAspending MUST pass through mojibake repair
  (`ftfy` or equivalent) before keyword matching or storage, with the raw string retained.
- **REQ-R4-17** — The SAM.gov connector MUST batch up to 100 UEIs per request, run no more
  often than weekly, cache all results, and treat 10 requests/day as the default quota until
  a role-assigned key is obtained.
- **REQ-R4-18** — The CourtListener connector MUST use only `/search/` (and `/courts/`) for
  discovery, MUST self-throttle to ≤5 req/min / ≤50 req/hr / ≤125 req/day, MUST NOT be placed
  in any user-facing request path, and MUST prefer Free Law Project bulk data for volume.
- **REQ-R4-19** — SIG MUST NOT depend on GovSpend or any paid procurement-intelligence
  product for any data that appears in the public graph.

**Contract and procurement model**

- **REQ-R4-20** — The Contract entity MUST add: `is_piggyback` (bool),
  `parent_cooperative_contract_id`, `cooperative_vehicle` (enum), `funding_source`,
  `grant_award_id`, `master_contract_end_date` and `local_term_end_date`.
- **REQ-R4-21** — Renewal watch (§15.4) MUST evaluate both the local term and the parent
  cooperative contract term, and MUST surface whichever expires first.
- **REQ-R4-22** — The §12 "Missing contract" research task MUST first check cooperative
  vehicles and grant sub-awards before flagging, and its generated text MUST name those
  channels as the likely acquisition path.
- **REQ-R4-23** — SIG MUST support a `GrantAward → SubAward → Organization → Deployment`
  path so that "which deployments were federally subsidized" is queryable.

**Evidence capture**

- **REQ-R4-24** — SIG MUST operate its own WARC-based web archive. Third-party archives MUST
  NOT be the sole record for any source. Rationale: `flocksafety.com` and
  `transparency.flocksafety.com` are excluded from the Wayback Machine.
- **REQ-R4-25** — JS-rendered and Cloudflare-protected targets MUST be captured with a real
  browser (Browsertrix Crawler / Playwright) that records XHR responses into the WARC;
  `wget --warc` alone is insufficient and MUST NOT be used for SPA portals.
- **REQ-R4-26** — Every EvidenceArtifact MUST be content-addressed by **SHA-256 of the raw
  response body**, stored at `s3://…/<sha[0:2]>/<sha[2:4]>/<sha>`, with foreign digests
  (DocumentCloud SHA-1 `file_hash`, Wayback CDX base32 SHA-1) stored in separate columns.
- **REQ-R4-27** — Every EvidenceArtifact MUST additionally carry a `semantic_sha256` over the
  canonicalized extraction, and change detection in §11 MUST use `semantic_sha256`, not
  `raw_bytes_sha256`.
- **REQ-R4-28** — For JS captures, SIG MUST store a full-page screenshot, a print-to-PDF
  render, and a post-render DOM snapshot alongside the WARC.
- **REQ-R4-29** — Every EvidenceArtifact MUST carry `license_class` ∈ {public_record,
  vendor_copyright, platform_metadata, unknown} and `publication_class` ∈ {public,
  metadata_only, restricted}. Artifacts with `license_class = platform_metadata` MUST be
  link-only.
- **REQ-R4-30** — Wayback lookups MUST use the CDX API. `archive.org/wayback/available`
  MUST NOT be a runtime dependency (observed 429 on every call).
- **REQ-R4-31** — Transparency-portal capture cadence MUST be at least weekly for portals
  with active deployments, with ETag/Last-Modified polling between full captures and
  immediate capture on detected change.

**Parsing**

- **REQ-R4-32** — Parsing MUST be preceded by a classification stage using libmagic on the
  byte stream (never extension alone) plus per-page text-density analysis, and MUST support
  per-page routing within a single PDF (digital pages and scanned pages in the same file).
- **REQ-R4-33** — SIG MUST maintain a `document_type` taxonomy (≥22 types as enumerated in
  F4.51) and dispatch a type-specific extractor.
- **REQ-R4-34** — Archive expansion MUST enforce depth ≤ 4, expansion ratio ≤ 100×, entry
  count ≤ 5,000, and reject absolute or `..` paths. Every member becomes its own
  EvidenceArtifact with `parent_artifact_id`.
- **REQ-R4-35** — XLSX ingestion MUST enumerate every sheet, MUST resolve merged header
  ranges via `openpyxl.worksheet.merged_cells`, and MUST record `sheet_name` on every
  extracted row.
- **REQ-R4-36** — Encrypted PDFs MUST be attempted with an empty password; if a user password
  is required, the artifact MUST be stored with `status: encrypted_unreadable` and MUST
  generate a research task. Brute-forcing MUST NOT be attempted.
- **REQ-R4-37** — Every extracted Claim MUST carry `source_page`, `source_char_start`,
  `source_char_end`, a verbatim `source_span`, and a versioned `extraction_method`.
- **REQ-R4-38** — LLM-based extraction MUST operate only on extracted text, MUST emit a
  strict JSON schema with explicit `not_found`, and MUST have every value's `source_span`
  verified to occur verbatim in the source text; failing that check, the value MUST be
  discarded. LLM-derived claims MUST NOT exceed Tier C confidence and MUST NOT overwrite
  rule- or key-derived claims.
- **REQ-R4-39** — Parsers MUST be pure and versioned; re-parsing MUST create a new parse
  record and MUST NOT mutate prior records.
- **REQ-R4-40** — The parse stage MUST detect suspected failed redactions (text beneath
  filled rectangles) and MUST set `contains_failed_redaction` and `publication_class:
  restricted` on such artifacts. (§13.4)
- **REQ-R4-41** — All extracted text MUST pass a sensitive-content detector (plate-like
  patterns, person NER, address patterns) before entering any public index; hits MUST route
  the artifact to `publication_class: metadata_only`. (§13.2, §20 Q30–Q31)

**Governance**

- **REQ-R4-42** — Before any MuckRock connector ships, SIG MUST obtain written confirmation
  from MuckRock that scheduled API use is sanctioned under their ToS.
- **REQ-R4-43** — Automated filing of MuckRock FOIA requests from the research-task queue
  MUST require explicit human approval per request; SIG MUST NOT auto-file.
- **REQ-R4-44** — Every source registered in SIG MUST record: license name (or
  `unstated`/`null`), license URL, attribution requirement, redistribution permission, and
  whether the terms were directly observed or inferred. Sources observed this session with
  **no stated license** include Sourcewell, HGACBuy, the CA statewide purchase-order dataset
  (`license_title: null`), and CourtListener's v4 overview.
