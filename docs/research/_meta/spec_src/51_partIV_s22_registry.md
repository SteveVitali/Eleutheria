## 22. The source registry and the federation compact

### 22.1 Structure

**SIG-INGEST-023 (MUST).** Every source MUST have a registry row carrying, at minimum: identity;
`custody_posture`; rights record with an SPDX expression; a **separately reviewed** `redistributable`
boolean; `default_tier` and source reliability `R`; access method; auth model; rate limits; observed
cadence; `compact_status`; `ingestion_permitted`; contact channel; and last-verified date.

**SIG-INGEST-024 (MUST).** `redistributable` MUST be a separately reviewed field, **not** derived
from the licence string. A permissive site-wide licence may not cover incorporated third-party data
(SC-09), and an unreviewed inference in either direction is a legal error.

### 22.2 The access matrix, as verified

Status recorded 2026-08-20. `VERIFIED` means a request was actually made and its outcome observed.

#### Physical layer

| Source | Access | Auth | Format | Rights | Status |
|---|---|---|---|---|---|
| OSM taginfo API | `taginfo.openstreetmap.org/api/4/*` | none | JSON | ODbL | **VERIFIED** |
| OSM Overpass | Public instances | none | JSON/XML | ODbL | Not yet tested — read etiquette rules first |
| OSM replication diffs | `planet.openstreetmap.org/replication/` | none | OSC | ODbL | Not yet tested |
| DeFlock | `deflock.me` **403**; `deflock.org` 200 | — | HTML | Unknown | **VERIFIED** — Cloudflare-fronted |
| Surveillance under Surveillance | 200 | none | HTML | Unknown | **VERIFIED** live |
| PanoptiCity | 200 | none | HTML | Unknown | **VERIFIED** live |
| Drivers Against Flock | 200 | none | HTML | Unknown | **VERIFIED** live |

#### Vendor / portal layer

| Source | Access | Rights | Status |
|---|---|---|---|
| **Flock transparency portals** | **403 on every path, incl. `robots.txt`** — Cloudflare managed challenge | ToS forbids bulk extraction | **VERIFIED — NOT ACCESSIBLE** (F2.1) |
| Eyes on Flock | 200 but **JS SPA**, 4.5 KB shell | Unknown | **VERIFIED** live; internals unresolved |
| Axon Community Connect | Public location listing + unauthenticated per-org stats endpoints | Unknown | **VERIFIED** — 321 communities enumerated (R7-F7.15) |

#### Usage / audit layer

| Source | Access | Rights | Status |
|---|---|---|---|
| Have I Been Flocked | 200, server-rendered; full audit-log field documentation | Unknown | **VERIFIED** (F2.3) |
| ALPR Watch | 200; GitLab org; Superset dashboard; KMZ/offline packages | Unknown | **VERIFIED** (F1.10) |

#### Adoption / accountability layer

| Source | Access | Rights | Status |
|---|---|---|---|
| **EFF Atlas of Surveillance** | Bulk CSV; >15,000 datapoints in 6,000+ jurisdictions; updated 2026-08-12 | `CC-BY-4.0` **with a third-party caveat** (SC-09) | **VERIFIED** |
| ALPR Accountability Atlas | 200 | Unknown | **VERIFIED** live |
| ALPR Abuse Library | 200 | Unknown | **VERIFIED** live |

#### Records / procurement / courts

| Source | Access | Auth | Limits | Status |
|---|---|---|---|---|
| **DocumentCloud** | `api.www.documentcloud.org` search + S3 assets | none for public | — | **VERIFIED — called** |
| **USAspending** | `spending_by_award` incl. **sub-awards**, `recipient/duns` | none | — | **VERIFIED — called** |
| **Legistar** | `webapi.legistar.com/v1/<client>/…` matters, attachments, histories, events | none | — | **VERIFIED — called** |
| **PrimeGov** | `<tenant>.primegov.com/api/v2/PublicPortal/…` | none | — | **VERIFIED — called** |
| **CivicClerk** | `<tenant>.api.civicclerk.com/v1/Events` + plaintext file stream | none | — | **VERIFIED — called** |
| **NextRequest** | undocumented `/client/requests`, `/client/request_documents` | none | — | **VERIFIED — called** |
| **CourtListener** | `/search/` open; `/dockets/`, `/opinions/`, `/parties/` **401** | token for most | **5/min, 50/hr, 125/day** | **VERIFIED** — crawling is impossible |
| **MuckRock** | **api_v2** (not v1); **401 on every data endpoint** | 5-min JWT | 15 req/min | **VERIFIED** — outline's v1 reference is wrong |
| SAM.gov | API | key | **10 requests/day** on the free tier | **VERIFIED** |
| OpenStates | API | key | 403 without | **VERIFIED** |
| **Sourcewell** | Free, unauthenticated: full solicitation record, signed contracts, monthly SKU price lists | none | — | **VERIFIED — files downloaded** |
| Wayback CDX | Availability + CDX API | none | — | **VERIFIED** |
| **Wayback for `*.flocksafety.com`** | **Excluded** — 403 + empty CDX with controls passing | — | — | **VERIFIED** |
| FBI CDE agency registry | `api.usa.gov/crime/fbi/cde/agency/byStateAbbr/{ST}` | api.data.gov key | 429s | **VERIFIED** |
| LEAIC crosswalk | ICPSR | login | — | **Manual acquisition** |

**SIG-INGEST-025 (MUST).** Four verified findings are architecture-determining and MUST be
reflected in phase planning, not discovered during implementation:

1. **The Flock portal layer has no lawful automated access path** (F2.1). Partnership,
   records requests, or human-mediated capture only.
2. **Flock domains are excluded from the Wayback Machine** — independently confirmed with passing
   controls (SC-13): `eff.org` returns captures from 1996 and `deflock.me` from 2024, while
   `transparency.flocksafety.com` returns zero captures and `flocksafety.com` returns no response
   body at all, which is the signature of an exclusion rule rather than of an unarchived host. There
   is therefore **no third-party archive to fall back on**. If SIG does not capture portal state
   through a lawful channel, *nobody does* — and because portal statistics are rolling rather than
   immutable, that history is being lost continuously, not merely left uncollected. Two
   consequences: any historical portal snapshots Eyes on Flock holds may be **globally unique**,
   which materially raises what SIG should be willing to offer in the collaboration and gives Phase 0
   a concrete first question; and SIG's archival-insurance role (§46.5) is this layer's only
   insurance rather than a courtesy.
3. **Court and records APIs are rate-limited to the point where crawling is impossible.** These
   are targeted-lookup sources, and any design assuming bulk court ingestion is void.
4. **Cooperative purchasing vehicles publish the full competitive record for free**, including
   signed contracts and monthly SKU price lists — while the agencies riding those contracts
   generate no local RFP. This is a major evidence channel the outline does not mention.

### 22.3 Sources the outline does not name

**SIG-INGEST-025a (MUST).** State reporting mandates MUST be modelled as **records-acquisition
leads, not as data feeds.** A statutory duty to *do* something is not a duty to *publish* it, and
neither implies a machine-readable dataset exists.

This is a correction, and it is grounded in the strongest available counter-case (SC-16). California
is the most ALPR-regulated state in the country — its ALPR statute has been in force since 2016 —
and as of 2026-08-20 it produces: **no recurring dataset**; **no central registry of the agency
policies the statute requires** (they are held decentrally and the state DOJ does not collect them);
**zero** hits for "ALPR" or "license plate reader" on the state open-data portal; **zero** ALPR
references in the state justice-data programme, whose bulk host is login-gated; and exactly **one**
relevant artifact — a 2020 state-auditor report whose 381-row agency survey is published as an HTML
table with **no CSV, XLSX, or JSON export of any kind**. A bill that would have mandated recurring
audits was **vetoed on the cost of the audits**; its successor's audit clause is
appropriation-contingent and the bill never uses the word "publish".

**SIG-INGEST-025b (MUST).** Two consequences bind the design:

1. The connector for this class is a **records-request generator** (§36) seeded from the statute —
   "this jurisdiction is required to hold X, therefore X is requestable" — not a scraper waiting for
   a feed. Statutory mandates are among the **best** leads SIG has, precisely because they establish
   that a record exists.
2. Where a one-time artifact does exist, it MUST be captured and parsed as an artifact
   (`state_auditor_survey`, §23.6) with its own `capture_status`, and MUST NOT create an expectation
   of recurrence. The absence of a follow-up is itself a `CoverageRecord` fact.

**SIG-INGEST-025c (MUST).** Legislative citations MUST be verified against the bill text and session,
never by bill number alone. Bill numbers are reused across sessions and across unrelated subjects:
in the California case, two later bills sharing a number with the ALPR bill are **Budget Acts**, and
a bill frequently cited alongside it concerns **facial recognition, not ALPR**. A `LegalInstrument`
claim MUST cite session and text, and a citation that cannot be resolved to text MUST NOT be
published.

**SIG-INGEST-026 (MUST).** The registry MUST include, in addition to every source in OL-21:

| Source | Why it matters |
|---|---|
| Cooperative purchasing bodies (Sourcewell, OMNIA, NASPO ValuePoint, BuyBoard, TIPS, HGACBuy, Equalis, GSA) | The dominant acquisition channel; free full contract records |
| Legistar / PrimeGov / CivicClerk / CivicPlus / NovusAgenda / BoardDocs / IQM2 / eScribe | Real APIs, not "agenda systems". **No municipality→platform directory exists; SIG should build one** |
| NextRequest / GovQA / JustFOIA / FOIAXpress | Published request logs with released-document URLs |
| USAspending **sub-awards** | Traces federal grant → local surveillance purchase (Byrne JAG, UASI) |
| FAA drone waiver releases | A federal regulator's dated authorization records with native validity intervals — an unusually clean `authorization_state` source |
| DHS fusion-center list | An authoritative roster (54 primary + 26 recognized = 80) |
| Municipal surveillance-ordinance (CCOPS) inventories | Statutory equipment inventories and impact reports, published on a legal cycle |
| State ALPR statutes and audits (CA SB 34, state auditor surveys) | **Leads to records, not feeds** — see SIG-INGEST-025a |
| GLEIF / SAM / FBI CDE / Census / NCES / IPEDS / NTD / CMS | The identity substrate (§14.2) |
| Footnote4a | A portal-tracking project surfaced via HIBF |
| eyesoffcr.org | A confirmed live local group |
| CourtListener / RECAP | Litigation evidence |

### 22.4 The compact and its enforcement

**SIG-INGEST-027 (MUST).** Each source's `compact_status` MUST be one of: `not_contacted`,
`contacted_awaiting_response`, `no_response`, `permission_granted`, `permission_granted_conditional`,
`permission_declined`, `public_terms_only`, `partnership_active`. **`no_response` is a recorded
state**, not an absence of one.

**SIG-INGEST-028 (MUST).** The pipeline MUST refuse to run a connector whose compact says ingestion
is not permitted (SIG-CHART-032). This is a runtime gate with a test, not a policy note.

**SIG-INGEST-029 (MUST).** For every project in the federation compact (§6), Stage 0 outreach MUST
have been attempted and its outcome recorded **before** a connector is written for it
(SIG-CHART-033).

### 22.5 The Eyes on Flock dependency

**SIG-INGEST-030 (MUST). — RESOLVED 2026-08-20.** Eyes on Flock exposes a **public,
unauthenticated, key-free JSON API**, verified directly (SC-18.1): `GET /api/v1/data` returns
HTTP 200, 7.6 MB, `{summary, portals}` with **950 portals** carrying `data_retention`,
`total_cameras`, `total_searches`, `vehicles_captured`, `hotlist_hits`, `hotlist_hit_rate`,
`organizations_shared_with`, `organizations_received_from`, `prohibited_uses`, `public_search_audit`,
`portal_url`, `slug`, `state`, `county`, `population`, `type`, and `data_last_updated`, plus national
roll-ups. **This maps almost field-for-field onto the outline's portal inventory (OL-2B-FP-02).**

`robots.txt` grants `User-agent: * → Allow: /` with `use=reference`. Licence: **CC BY-SA 4.0**.
Contact: `contact@eyesonflock.com`.

**The portal layer is therefore obtainable lawfully, without scraping the vendor and without a
headless browser.** Phase 11 is unblocked and risk R-02 is closed.

**SIG-INGEST-030a (MUST).** Outreach remains a **Phase 0 deliverable** even though the data is
already accessible — for three reasons that do not depend on access: ShareAlike attribution must be
agreed and correctly rendered; SIG MUST NOT poll faster than the upstream's own refresh
(SIG-INGEST-030c); and the archival-succession offer (SIG-CONTRIB-013) matters *more* now, not less,
because this API is a single point of failure for the only lawful route to the portal layer.

**SIG-INGEST-030b (MUST).** Historical back-fill MUST use the Internet Archive's captures of the API
endpoint itself rather than re-deriving history. Because the vendor's own domains are excluded from
the archive (SC-13) while this aggregator's are not, the aggregator's archived API responses are the
**only** available longitudinal record of portal state.

**SIG-INGEST-030c (MUST).** Change detection MUST key on the upstream's own `data_last_updated` /
snapshot field, **not** on SIG's fetch time, and SIG MUST NOT poll faster than the upstream
refreshes. This answers outline Q17 for this route: cadence is set by the upstream's recrawl, and
polling faster adds load without adding information.

**SIG-INGEST-031 (MUST).** The fallbacks remain documented and MUST be retained, because the API is
a single dependency: (a) public-records acquisition of the underlying configuration from agencies,
which is lawful and yields *better* evidence than the portal; (b) contributor-submitted captures
made by humans browsing normally; (c) partner archives. **Building a challenge-defeating crawler is
not on the list and MUST NOT be added to it.**

**SIG-INGEST-032 (SHOULD).** SIG SHOULD offer Eyes on Flock, and every single-maintainer upstream,
a mirroring and succession arrangement (§46.5) — SIG holds an archival copy that survives the
project, on terms the project sets. Given that Flock domains are excluded from the Wayback Machine,
this is the ecosystem's only insurance against permanent loss.

---
