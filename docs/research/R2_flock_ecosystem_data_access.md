# R2 — The Flock ecosystem: what data is actually obtainable

**Workstream:** R2
**Researched:** 2026-08-20
**Researcher:** lead synthesizing agent (reconstructed after the delegated R2 run was terminated
by an account spend limit before writing its file; all findings are first-hand retrievals by the
lead agent)
**Outline sections covered:** §2 Layers B and C, §6, §10.1D, §10.1E, §11, §21, §20 (Q1–Q5, Q15, Q17, Q18)
**Outline questions answered:** Q1, Q2, Q3, Q4, Q5, Q15, Q17, Q18
**Confidence in this file overall:** **high** throughout after the 2026-08-20 completion pass
(Part 5). Every endpoint, licence, and export named below was fetched and parsed first-hand.

> **Scope note (superseded 2026-08-20).** Parts 1–4 were written at reduced scope after the original
> delegated run was terminated by a spend limit, and rated Eyes on Flock "low confidence… not
> reverse-engineered." **Part 5 completes that work and corrects it.** Eyes on Flock was fully
> reverse-engineered; its API, licence, bulk export, historical depth and contact channel are all
> resolved (F2.6–F2.9). Read Part 5 as authoritative wherever it and Parts 1–4 differ; the
> divergences are flagged inline.

---

## Part 1 — The access reality

### F2.1 — Flock transparency portals are behind a Cloudflare managed challenge; even `robots.txt` is 403

**Claim:** Every path on `transparency.flocksafety.com` returns **HTTP 403** with a Cloudflare
interstitial to a well-formed browser-UA HTTP client — including `/robots.txt` and `/sitemap.xml`.
**Status:** VERIFIED
**Evidence:** curl with a Chrome UA, 2026-08-20:

| URL | Status | Body |
|---|---|---|
| `https://transparency.flocksafety.com/robots.txt` | **403** | 5,769 B `text/html` |
| `https://transparency.flocksafety.com/sitemap.xml` | **403** | 5,772 B `text/html` |
| `https://transparency.flocksafety.com/` | **403** | 5,739 B `text/html` |
| `https://transparency.flocksafety.com/hagerstown-md-pd` | **403** | `<title>Just a moment...</title>`, `challenge-platform`, CSP referencing `https://challenges.cloudflare.com` |

**Retrieved:** 2026-08-20
**Implication for the spec — this is the most consequential access finding in the project:**

1. **SIG cannot build the Flock portal layer by ordinary HTTP scraping.** Not "should not" —
   cannot. The bot-management layer blocks a compliant client outright.
2. **`robots.txt` is unreachable**, so SIG cannot even determine the site's stated crawl policy by
   the normal mechanism. The Crawler Conduct Policy must define behaviour for the case where
   robots.txt cannot be retrieved, and the safe default is to treat access as not granted.
3. **Defeating a managed challenge is legally hazardous**, not merely rude. Workstream R8
   independently found that *Reddit v. SerpApi* (S.D.N.Y., 2026-07-31) allowed DMCA §1201
   anti-circumvention claims to proceed against proxy rotation, UA spoofing, and human-mimicking
   scrapers — which is precisely the technique set required here. R8 also found Flock's API and
   Integration Terms (2025-10-13) expressly forbid "extract, scrape, or export data in bulk…
   database-like access to Flock's website or APIs."
4. **Therefore OL-2B-EOF-05 is upgraded from a preference to a near-necessity.** The outline says
   SIG "should not independently build a competing portal-discovery crawler without first
   determining whether Eyes on Flock can expose an API, export, archive, or collaboration
   interface." The access reality is stronger: **collaboration with Eyes on Flock, or another
   party already holding this data, is the only low-risk path to the portal layer.** A SIG-operated
   challenge-solving crawler is out of scope under §46.5 and the Crawler Conduct Policy.
5. **A contingency is required.** If collaboration fails, the fallback is not scraping. It is:
   agency-side acquisition of the same facts through public-records requests (portals are agency
   configuration, and the underlying settings are requestable — see F2.3), plus contributor-
   submitted captures made by humans browsing normally, plus partner archives.

**Outline delta:** CORRECTS §2 Layer B and §10.1D. The outline treats portal capture as a
straightforward scraping-and-snapshotting exercise ("this source demands snapshotting and temporal
preservation"). It is not technically or legally straightforward, and the spec must not plan as
though it were.

### F2.2 — Ecosystem liveness and rendering mode

**Claim:** Measured 2026-08-20:

| Project | Status | Rendering | Consequence for ingestion |
|---|---|---|---|
| `eyesonflock.com` | 200, **4.5 KB** | **JS SPA** — raw HTML contains only `<title>Eyes On Flock - Aggregating Flock Safety Transparency Portal Data</title>` | Cannot be parsed without a headless browser or an underlying API |
| `haveibeenflocked.com` | 200, 75 KB | **Server-rendered**, content in HTML | Parseable directly |
| `haveibeenflocked.com/about/audit-logs` | 200, 74 KB | Server-rendered | Full field documentation extractable (F2.3) |
| `alprwatch.org` | 200 | Server-rendered | Parseable |
| `alpratlas.org` | 200, 16 KB | Server-rendered | Parseable |
| `library.kansas.watch` | 200, 34 KB | Server-rendered | Parseable |

**Status:** VERIFIED
**Implication for the spec:** Eyes on Flock's SPA architecture means even a permitted ingestion
requires either a partner API or headless-browser capture. Its 4.5 KB shell strongly suggests a
JSON API behind it, which is the thing to ask about first in Stage 0 outreach.
**Outline delta:** EXTENDS §2 Layer B.

---

## Part 2 — HIBF: the audit-log schema, captured verbatim

### F2.3 — The three audit-log types and their exact field lists

**Claim:** HIBF documents three distinct search-audit log types with different field sets and
different redaction, plus three non-search record types.
**Status:** VERIFIED
**Evidence:** `https://haveibeenflocked.com/about/audit-logs`, retrieved 2026-08-20. Quoted:

> There are three distinct types of audit logs, each with different levels of detail.

**Organization Audit Log** — *"searches performed by the agency's own operators. This is the most
detailed log type, including operator names, license plates searched, and case numbers. It can be
downloaded directly from the Flock software as a CSV file."*
Fields: `ID, Name, Org Name, Camera Count, Time Frame, License Plate, Reason, Case #, Filters,
Search Time, Search Type, Text Prompt, Moderation`

**Network Audit Log** — *"searches conducted by other agencies that accessed data through network
sharing agreements. For example, when an agency from Texas conducts a nationwide search, they may
appear in the network logs for an agency in Minnesota."* **Operator names and license plates are
redacted with `***`.**
Fields: `ID, Name (redacted), Org Name, Camera Count, Time Frame, License Plate (redacted),
Reason, Case #, Filters, Search Time, Search Type, Text Prompt, Moderation`

**Portal / Public Audit Log** — *"heavily redacted and contain only user UUIDs (not officer names),
search dates, camera counts, and reasons."*
Fields: **Variable (agency-configured)**

**SharedNetworks.csv** — *"A snapshot of which agencies an organization shares its Flock data with,
and which agencies share data back to it. **This is a configuration export, not a record of
searches**: it shows the sharing relationships in place at the moment the file was generated."*
Fields: `Organization Name, Networks Shared With Me, Networks I'm Sharing`
*"Each row is one other organization… A blank cell means no sharing in that direction."*

**Event Logs** — *"A running record of administrative actions… creating or editing hotlists…,
granting or changing network sharing, adding users and roles, renaming cameras, and opening live
camera streams. Where the audit logs record searches, the event log records changes to the system
itself."*
Fields: `Timestamp, User, Event Type, Entity Type, Entity Details, Event Id`
`Event Type` ∈ {`create`, `update`, `delete`}.

**Configuration Settings** — network-sharing rules including whether requests from nearby agencies
are auto-approved and how widely the network is distributed.

**Retrieved:** 2026-08-20
**Implication for the spec:** Several are load-bearing and were not derivable from the outline —

1. **`Camera Count` appears on every search row.** A single audit export therefore carries a
   *time series of the searched organization's camera count*, from a Tier-A source, incidentally.
   This is an independent count predicate for the camera-count reconciliation workflow (§29.1) and
   the outline does not mention it.
2. **Network Audit redaction is `***`, not absence.** The parser MUST distinguish "redacted" from
   "empty" — they are different epistemic states and conflating them corrupts coverage metrics.
3. **Portal audit fields are agency-configured and therefore variable.** No fixed schema can be
   assumed; the parser must be schema-discovering and must record the observed field set per
   capture as data.
4. **`SharedNetworks.csv` is explicitly a configuration snapshot, not usage** — direct
   confirmation of P9 and OL-11.3-02 from the specialist project itself. Its two columns are
   *directional*, and a blank cell is a meaningful negative.
5. **Event logs are a lifecycle-transition goldmine.** `create`/`update`/`delete` against hotlists,
   network shares, users, cameras, and live-stream views give **dated state transitions** — exactly
   what the lifecycle reconciliation workflow (§29.4) needs and what most sources lack. The outline
   lists event logs but does not identify them as the best available transition evidence.

**Outline delta:** CONFIRMS OL-2C-HIBF-02 through OL-2C-HIBF-07 and supplies the exact field lists
the outline only sketched. EXTENDS with the `Camera Count` finding, the redaction-vs-absence
distinction, and the variable portal schema.

### F2.4 — HIBF's analytic surface reveals the report taxonomy SIG must be able to answer

**Claim:** HIBF publishes named reports including: Protected Activity Reports (First Amendment
Report, Profiling Report, Low-Level Offenses Report, Non-Criminal Report, Develop PC Report,
**Immigration Report**, California Out-of-State Queries); Operational Reports (ICE 287(g) Agencies,
Other Searches, FreeForm Report, Scanner Map, Cost Estimates); Analytics Reports (Reason Cloud,
Dropdown Reasons, Statistics Overview, Daily Search Trends, Surveillance Tracking, Account Sharing
Candidates, Training & Test Search Patterns, Spread of Flock); Data Quality Reports (Irregular
Records). It also publishes Police Rosters, Name Resolution, Sources, and a Privacy page, and links
to **Footnote4a**.
**Status:** VERIFIED
**Evidence:** Site navigation extracted from `https://haveibeenflocked.com/about/audit-logs`.
**Implication for the spec:**
1. The researcher acceptance query J-2 asks for agencies with "documented immigration-related
   searches." HIBF already produces an Immigration Report and an ICE 287(g) agency list — so the
   correct SIG posture is to **reference and link**, not to recompute (P5, non-goal N9).
2. **"Account Sharing Candidates" and "Training & Test Search Patterns"** are anomaly detectors.
   They are evidence that HIBF has solved data-quality problems SIG will face, and their existence
   argues for reusing HIBF's conclusions rather than rebuilding detection.
3. **"Reason Cloud" and "Dropdown Reasons"** confirm the outline's point (OL-2C-AW-04) that reason
   fields are messy free text *and* constrained dropdowns depending on configuration — two
   different normalization problems, not one.
4. **Footnote4a** is an ecosystem project the outline does not mention. Stage 0 must investigate it.
**Outline delta:** EXTENDS §2 Layer C and §21 — adds Footnote4a and the report taxonomy.

---

## Part 3 — ALPR Watch

### F2.5 — ALPR Watch's code is on GitLab and its scope has shifted

Covered in full at **R1-F1.10** to avoid duplication. Summary: code at
`https://gitlab.com/alprwatch-org` (not GitHub); the FOIA Superset dashboard persists at
`https://superset.alprwatch.org/superset/dashboard/columbia-river-gorge-foia/`; the project now
also ships ALPR-avoidance routing and offline data packages built on DeFlock data; it states *"The
DeFlock project is responsible for most of the data available."* It links `eyesoffcr.org`
(Eyes Off Cedar Rapids), a confirmed live local group.
**Outline delta:** CORRECTS §2 Layer C.

---

---

## Part 4 — Answers to the outline's mandatory questions in R2's scope

*Updated 2026-08-20 by the Part 5 completion pass. Rows that changed are marked ▲.*

| Q | Question | Answer status |
|---|---|---|
| Q1 ▲ | Does Eyes on Flock expose an API/DB/archive? | **YES — ANSWERED (F2.6, F2.8).** A public, unauthenticated, key-free JSON API: `GET /api/v1/data` (7.6 MB, 950 portals + national summary, MongoDB-backed), `GET /api/audit/{state}/{slug}` (paginated search audits) and **`?download=true`** (CSV bulk export), plus `GET /api/v1/map/{slug}` (PNG) and `POST /api/v1/submit`. No headless browser needed; `robots.txt` allows general crawlers. |
| Q2 ▲ | Can we obtain its historical portal snapshots directly? | **YES — ANSWERED, two ways (F2.8, F2.9).** (a) Its audit exports themselves carry ~9.5 months of accumulated history per portal (Windsor CT: 2025-10-11 → 2026-07-21, 217 distinct days), far beyond Flock's 30-day window. (b) The Internet Archive holds **29 HTTP-200 captures of `/api/v1/data`** spanning 2025-07-24 → 2026-08-17 (657 → 805 → 950 portals), giving a 13-month back-fill at zero cost to the operator. |
| Q3 ▲ | Its reuse/licence terms? | **ANSWERED: CC BY-SA 4.0 (F2.7).** Stated in the site footer, rendered from `assets/index-bsh6x4Ps.js`: *"EyesOnFlock is licensed under CC BY-SA 4.0."* Attribution **and ShareAlike** required. Contact confirmed: `contact@eyesonflock.com`, Bluesky `@eyesonflock.com`. Residual: whether the grant is intended to cover the API payload as well as site content. |
| Q4 ▲ | What exports does HIBF make available, under what licence/cadence? | **ANSWERED (F2.18) — exports yes, licence no.** Undocumented bulk CSV at `GET /api/reports/{type}/download` (verified: 24.9 MB / 26,572 rows / 25 columns; cap raised 10k→100k rows) plus `/api/pd/agency/{id}/download`, `/api/sources/stats` (2 MB), `/api/reports/counts`, `/api/ice-287g`. **But `robots.txt` disallows `/api/` and `/*-records`**, and the exports are *derived* (hashed plates, inferred `best_name` + confidence, redacted reasons) and explicitly *"NOT (excerpts from) the original source files."* **Licence: none anywhere.** Cadence: no promise (*"not a real-time monitoring tool"*); report views rebuild ~daily but `ca-oos-*` is 7 months stale and `/api/health/minimal` read `is_stale: true`. Editorial arm **Footnote4a is CC BY 4.0** (F2.13) — articles only, not the data. |
| Q5 ▲ | What APIs/exports does ALPR Watch publish? | **ANSWERED (F2.19).** 15 public GitLab repos; a documented Swagger/OpenAPI REST API at `/api-doc/openapi.json` (routing-only, GPL-2.0-only) — **correcting F2.5's "no REST API observed"**; and an open, `wget -r`-friendly bulk file archive at `https://alprwatch.org/pub/` including dated snapshots of every Flock legal document. Previously confirmed (F2.5 / R1-F1.10): KMZ avoidance packages, offline data packages, a Superset FOIA dashboard, GitLab repositories; no REST API observed. |
| Q15 ▲ | Licences governing Atlas / HIBF / EoF / ALPR Watch / Accountability Atlas | **LARGELY RESOLVED — see the consolidated table in Part 5F.** Atlas (DeFlock-derived) `CC-BY-4.0` at SC-09; **Eyes on Flock `CC BY-SA 4.0`**; **Footnote4a `CC BY 4.0`**; **ALPR Accountability Atlas — definitively NO LICENCE** (F2.16), reference-only; **HIBF — definitively NO LICENCE** (F2.18); **ALPR Watch — mixed GPL on 4 of 15 repos, no licence on the `/pub/` data tree** (F2.19); **ALPR Abuse Library — none stated** (F2.20). Newly licensed sources added: `eyes-off/eugene-oregon` **CC0-1.0**, `none-below/sm-alpr` **AGPL-3.0**, four projects **MIT**, two with **none**. The portfolio spans copyleft, permissive, public-domain and unlicensed — see REQ-R2-18. |
| Q17 ▲ | Justified portal snapshot cadence | **ANSWERED (F2.9).** Not moot, and not SIG's choice to make freely: Eyes on Flock's own recrawl advances `snapshot_date` roughly **monthly** (2026-08-17 archived response and the 2026-08-20 live response both read `2026-07-22T20:20:01Z` — 29 days stale). SIG MUST key change-detection on `snapshot_date` rather than fetch time, and MUST NOT poll faster than the upstream refresh. Direct portal cadence remains blocked by F2.1/F2.10. |
| Q18 | How to preserve deleted portals and inactive organizations | **ANSWERED** by design (spec §17.6): artifact disappearance is recorded as a dated event with the last capture retained; never a deletion. **Strengthened by F2.15** — negative probes (`flock_status = 404` on 5,011 slugs) show absence is itself storable evidence; see REQ-R2-21. |

---

# Part 5 — Completion pass (2026-08-20)

*Completes the items listed under Open questions after the original run was terminated. Findings
continue the F2.x numbering from F2.6.*

> **Method note.** Every URL below was fetched first-hand with `curl` and a browser UA on
> 2026-08-20. Where a fetch failed, the exact status and body size are recorded. The Eyes on Flock
> SPA was reverse-engineered by downloading and reading its JavaScript bundle; all endpoints named
> here were then called live and their responses parsed.

## Part 5A — Eyes on Flock, reverse-engineered

### F2.6 — Eyes on Flock exposes a public, unauthenticated, undocumented JSON API — the project's single most important open dependency is RESOLVED

**Claim:** `eyesonflock.com` is a Vite/React SPA whose 4.5 KB shell loads one JS bundle that names
its own backend; the backend is a public, key-free JSON API at **`https://eyesonflock.com/api/v1/data`**
returning **7,627,201 bytes** covering **950 portals** plus a national summary.
**Status:** VERIFIED
**Evidence:**

1. `https://eyesonflock.com/` → **200**, 4,533 B, `last-modified: Tue, 05 May 2026 04:19:16 GMT`.
   The shell declares `<script type="module" crossorigin src="/assets/index-bsh6x4Ps.js">`.
2. `https://eyesonflock.com/assets/index-bsh6x4Ps.js` → **200**, 346,733 B. Grepping it yields the
   API base constant and three endpoint templates, verbatim from the minified source:

   ```js
   const Ru="https://eyesonflock.com"
   h = `${Ru}/api/v1/data`
   Me = `${Ru}/api/v1/map/${ie}`
   Me = `${Ru}/api/audit/${u.toLowerCase()}/${o}?page=${Y}&limit=100&sort_by=${ce}&sort_order=${ie}`
   P  = `${Ru}/api/audit/${u.toLowerCase()}/${o}?download=true`
   fetch("/api/v1/submit",{method:"POST", …})
   ```
3. Live calls, 2026-08-20:

| Endpoint | Status | Size | Content-Type |
|---|---|---|---|
| `/api/v1/data` | **200** | 7,627,201 B | `application/json` |
| `/api/audit/{state}/{slug}` | **200** | ~9.9 KB/page | `application/json` |
| `/api/audit/{state}/{slug}?download=true` | **200** | 101,052 B | **`text/csv`** |
| `/api/v1/map/{slug}` | **200** | 1,230,316 B | `image/png` (rendered sharing map) |
| `/api/v1/submit` | POST | — | portal submission intake |
| `/api/v1`, `/api/v1/portals`, `/api/v1/summary`, `/api/v1/history`, `/api/v1/snapshots`, `/api/docs`, `/openapi.json` | **404 / 403** | — | do not exist |

**`/api/v1/data` payload — two top-level keys, `summary` and `portals`.**

`summary` (16 keys): `_id` (a MongoDB `$oid` — the backend is MongoDB), `total_portals_found` 950,
`total_cameras` 28,635, `total_searches` 197,172, `total_hotlist_hits` 7,503,618,
`total_vehicles_captured` 277,509,759, `total_organization_count` 288,128,
`total_receiving_organization_count` 37,690, `total_public_search_audits` 351,
`total_hotlist_hit_rate` 2.7039…, `estimated_total_cameras` 102,210, `estimated_total_networks` 6,634,
`top_search_reasons` (dict of 500), `top_orgs_shared_with` (dict of 1,000),
`top_orgs_received_from` (dict of 1,000), `snapshot_date` `{"$date":"2026-07-22T20:20:01.360Z"}`.

`portals` — 950 records, 20 fields each:
`portal_url, city, county, state, population, type, total_cameras, total_searches, data_retention,
vehicles_captured, hotlist_hits, hotlist_hit_rate, organization_count, organizations_shared_with,
receiving_organization_count, organizations_received_from, prohibited_uses, public_search_audit,
data_last_updated, slug`

Measured null counts over the 950 rows: `county` 832, `receiving_organization_count` 856,
`organization_count` 361, `population` 226, `hotlist_hit_rate` 168, `hotlist_hits` 143,
`total_searches` 127, `city` 118, `total_cameras` 70, `vehicles_captured` 67, `data_retention` 36,
`prohibited_uses` 25. `type` ∈ **{`PD` (832), `SD` (118)}** only. 43 distinct states (CA 198, OH 99,
VA 77, TX 59, NC 45, MN 44, WA 41 …). `data_retention` in days: 30 (760), 21 (109), 365 (24),
90 (6), 7 (3), 15 (3), 1095 (2), 14 (2), 60 (2), 121/180/185 (1 each), null (36).
`public_search_audit` is a **boolean**, true for **351** portals.

**Retrieved:** 2026-08-20
**Implication for the spec — this reverses the project's central planning assumption:**

1. **OL-2B-EOF-05 and REQ-R2-04 are satisfied without negotiation for the read path.** SIG does not
   need a partnership to obtain the portal layer's *aggregate* state; it needs one lawful HTTP GET
   against a documented-by-inspection public endpoint on a site whose `robots.txt` **allows** it
   (F2.13). Outreach remains valuable — for cadence coordination, provenance questions, and
   goodwill — but it is **no longer a blocking dependency for Phase 0 ingestion**.
2. **`data_retention` is a first-class portal field SIG must ingest**, and its distribution is
   evidence in itself: 80% of portals retain 30 days, but 24 retain a full year and two retain
   1,095 days (3 years). Retention is a policy variable, not a constant.
3. **`prohibited_uses` is free text**, e.g. *"Immigration enforcement, traffic enforcement,
   harassment or intimidation, usage based solely on a protected class (i.e. race, sex, religion),
   personal use."* This is agency **policy assertion**, Tier-B at best, and must never be recorded
   as a finding about actual conduct — it is precisely the "policy decision" epistemic class.
4. **Two summary fields are semantic traps.** `estimated_total_networks` is rendered in the UI with
   the label *"Most Networks Used In A Search"* and the description *"Largest number of networks
   used for a single search - found in public search audits"* — it is a **maximum, not an estimate
   of a total**. And `estimated_total_cameras` (102,210) is **never referenced anywhere in the
   bundle**; its derivation is undocumented and unused. SIG MUST NOT ingest either at face value.
5. **`type` has only two values**, so university, transit, airport, DA, and state-agency portals are
   either absent or mis-typed. The taxonomy is not adequate for SIG's organization model.

**Outline delta:** **CORRECTS §2 Layer B, §10.1D and F2.2 of this file.** F2.2 concluded Eyes on
Flock "cannot be parsed without a headless browser or an underlying API" and rated the file's
confidence "low for Eyes on Flock internals, which are behind a JS SPA and were not
reverse-engineered." The SPA is a thin shell over an open API; no headless browser is needed.

### F2.7 — Eyes on Flock is licensed CC BY-SA 4.0, and publishes a working contact channel

**Claim:** The site footer, rendered from the JS bundle, states a licence; three contact routes exist.
**Status:** VERIFIED
**Evidence:** `https://eyesonflock.com/assets/index-bsh6x4Ps.js`, footer component, verbatim:

> `"© ", new Date().getFullYear(), " EyesOnFlock is licensed under", " ",`
> `<a href="https://creativecommons.org/licenses/by-sa/4.0/" …>CC BY-SA 4.0</a>`

and a site-wide disclaimer: *"\* EyesOnFlock is not affiliated with Flock Safety"*.

Contact page (`/contact`), verbatim: *"For inquiries, feedback, or technical assistance, please
contact at:"* — **Email: `contact@eyesonflock.com`**; **Bluesky: `@eyesonflock.com`**
(`https://bsky.app/profile/eyesonflock.com`). An error string in the submit flow independently
confirms the address: *"Error validating portal. If this keeps happening, please send an email to
contact@eyesonflock.com"*. Funding: `https://ko-fi.com/eyesonflock`. SPA routes: `/`, `/counter`,
`/faq`, `/resources`, `/submit`, `/contact`.

Methodology statements recovered verbatim from the bundle:

> "The aggregated stats and table data on the home page of the site are sourced directly from Flock
> customers' Transparency Portals."

> "Data shown is only from departments that have opted to enable their Flock transparency portals.
> Flock cameras are in thousands of cities… If your location is not listed, you can ask your local
> police department to enable their portal."

> "Transparency Portals are a PR tool that Flock provides to customers so both parties can boast
> about their 'transparency' while providing an extremely narrow insight into the data that is being
> collected and abused by law enforcement. Portals are optional for the customer to enable, along
> with the individual fields displayed on them. While individual portals are borderline useless due
> to the lack of data contained on them, they are made moderately powerful when the data is
> aggregated and analyzed."

> "[a department] has specifically redacted this data point on their transparency portal."

**No public source repository exists.** `gh search repos eyesonflock`, `gh search repos "eyes on
flock"`, and `gh search users eyesonflock` all returned **zero** results; `gh search code
"eyesonflock.com"` returned only third parties linking to or consuming the site. Eyes on Flock is
closed-source.

**Retrieved:** 2026-08-20
**Implication for the spec:**
1. **Q3 is ANSWERED: CC BY-SA 4.0.** SIG **may** redistribute and build on Eyes on Flock data,
   **provided** it attributes and — the operative constraint — **ShareAlike**. Any SIG artifact that
   constitutes an adaptation of EoF data must itself be offered under CC BY-SA 4.0 or compatible.
2. **ShareAlike is a licence-compatibility hazard at the composition layer.** SIG plans to merge EoF
   data with sources under CC-BY-4.0 (Atlas at SC-09), CC0 (F2.14), MIT, and AGPL. BY-SA's copyleft
   does not compose freely with a permissive-only downstream promise. **The spec must model licence
   per source and compute the effective licence of every derived artifact**, or segregate BY-SA
   derivatives into a separately-licensed distribution.
3. The licence is asserted **only inside a JavaScript bundle** — there is no `/license` page, no
   LICENSE file, and no machine-readable declaration. SIG should confirm the intended scope
   (site content vs. underlying data) in writing at `contact@eyesonflock.com` and record the reply
   in the compact. This is now a *confirmation* errand, not a blocking unknown.

### F2.8 — Eyes on Flock also publishes a per-portal search-audit API **with a CSV bulk export**, holding ~9.5 months of history — far beyond Flock's 30-day window

**Claim:** An endpoint absent from the outline and from any documentation returns each portal's
public search-audit rows, paginated as JSON or as a single CSV download, retaining data long after
Flock's own rolling window has discarded it.
**Status:** VERIFIED
**Evidence:** `https://eyesonflock.com/api/audit/ct/windsor-ct-pd` → **200**, `application/json`:

```json
{"headers":["id","userId","searchDate","cameraCount","reason","networkCount"],
 "rows":[["a2d00fd6-…","***","2026-07-21T15:56:33.235Z",null,"2026-17126",67], …],
 "pagination":{"page":1,"limit":100,"total_records":1112,"total_pages":12,"has_more":true}}
```

`https://eyesonflock.com/api/audit/ct/windsor-ct-pd?download=true` → **200**, **101,052 B**,
`content-type: text/csv`, `content-disposition: attachment; filename=windsor-ct-pd_audit.csv`.
A second portal (`/api/audit/ca/alameda-ca-pd`) returned the identical 6-column header with
`total_records` 3,542 — the schema is stable across agencies.

Parsing the full Windsor CT CSV (1,112 rows):

- **Temporal span: 2025-10-11 → 2026-07-21 — 217 distinct days across 10 months.**
  Monthly counts: 2025-10 208, 2025-11 222, 2025-12 226, 2026-01 154, 2026-02 120, 2026-03 28,
  2026-04 34, 2026-05 59, 2026-06 44, 2026-07 17.
- **Two incompatible date encodings coexist in one column:** 633 rows ISO-8601 with `Z`
  (`2026-07-21T15:56:33.235Z`), 479 rows space-separated and timezone-naive
  (`2025-10-11 01:06:19.503`).
- **Three distinct `userId` states in one column:** `***` (599), `REDACTED` (210), and **raw
  operator UUIDs (303 rows, un-redacted)** such as `0b670b3a-c26c-402a-9f04-da3268d112d5`.
- `cameraCount` populated on 853/1,112; `networkCount` blank on 822/1,112.
- Reasons are free text with case and abbreviation drift: `Investigation` 79, `Evading` 37,
  `bolo` 36, `Larceny` 27, `larceny` 24, `BOLO` 23, `Omv` 22, `evading` 20.

**Retrieved:** 2026-08-20
**Implication for the spec:**
1. **Q2 is effectively ANSWERED for the audit layer.** Eyes on Flock *is* the historical archive.
   Flock's portals expose ~30 days (F2.12); EoF holds ~10 months per portal and offers it as a
   one-request CSV. SIG should **mirror these exports on a schedule** rather than attempt portal
   capture — subject to the CC BY-SA obligation in F2.7.
2. **REQ-R2-05 must be widened.** The redaction sentinel is not one token but a **set** —
   `***`, `REDACTED`, and empty — and, critically, **some agencies publish raw operator UUIDs**.
   A three-way epistemic distinction (redacted / absent / present) is insufficient; the parser needs
   a sentinel *registry* and must flag un-redacted operator identifiers on ingest.
3. **Pseudonymous operator UUIDs are re-identification-capable and must be governed.** They are
   stable per operator, so a UUID plus a public-records request naming shift assignments can
   de-pseudonymise an individual officer. SIG requires an explicit policy before storing them.
4. **The dual date encoding is capture-era drift inside a single source**, not a source-vs-source
   mismatch. Normalisation must be lossless and must retain the observed raw string.
5. **`cameraCount` on audit rows confirms and extends F2.3's finding** into a second, independently
   downloadable feed.

### F2.9 — 29 Wayback captures of the Eyes on Flock API give SIG a ready-made 13-month longitudinal series with visible schema evolution

**Claim:** The Internet Archive holds the EoF API response itself, repeatedly, from 2025-07-24 to
2026-08-17 — a back-fillable time series that no live endpoint offers.
**Status:** VERIFIED
**Evidence:** `https://web.archive.org/cdx/search/cdx?url=eyesonflock.com/api/v1/data&output=json`
→ 31 captures, **29 with HTTP 200**. Three were downloaded via the `id_` raw-content form
(`https://web.archive.org/web/<ts>id_/https://eyesonflock.com/api/v1/data`; note the bodies are
gzip-encoded and must be decompressed):

| Capture | portals | `total_cameras` | `snapshot_date` | portal fields |
|---|---|---|---|---|
| `20250724204903` | **657** | 19,230 | absent | 16 |
| `20260121021826` | **805** | 24,531 | 2026-01-19 | 18 (`+organizations_shared_with`, `+prohibited_uses`) |
| `20260817212402` | **950** | 28,635 | 2026-07-22 | 20 (`+receiving_organization_count`, `+organizations_received_from`) |

Summary keys grew in step: `_id` and `snapshot_date` appear by Jan 2026;
`total_receiving_organization_count`, `estimated_total_networks` and `top_orgs_received_from` by
Aug 2026. **Every change is additive — no field was removed or renamed across 13 months.**

**Cadence, measured rather than asked:** the 2026-08-17 archived response and the live 2026-08-20
response both carry `snapshot_date` = **2026-07-22T20:20:01Z**. Eyes on Flock's own recrawl is
therefore **roughly monthly, and the live feed was 29 days stale at retrieval**.

**Retrieved:** 2026-08-20
**Implication for the spec:**
1. **Q17 is ANSWERABLE and the answer is: match ~monthly, do not exceed it.** Polling EoF more
   often than its ~30-day recrawl produces byte-identical responses and pure waste. The connector
   MUST key change-detection on the payload's own `snapshot_date`, not on fetch time.
2. **SIG can back-fill 13 months of portal-layer history on day one** from the Archive, at zero load
   on Eyes on Flock. This is the single cheapest high-value ingestion in the project.
3. **`data_last_updated` is per-portal and differs from the global `snapshot_date`** (row-level
   values ranged across 2026-07-22 within a single build), so freshness is a per-record property.
4. The additive-only schema history is evidence that a **schema-discovering, additive-tolerant
   parser** (REQ-R2-06) is the right design, and it supplies a real regression corpus to test it.

---

## Part 5B — The Flock access surface, re-verified and bounded

### F2.10 — F2.1 re-verified, and `flocksafety.com` is confirmed **explicitly excluded** from the Wayback Machine

**Claim:** The 403 wall persists unchanged, and the Internet Archive holds **zero** captures of any
`flocksafety.com` URL because the domain is affirmatively excluded — not merely uncrawled.
**Status:** VERIFIED
**Evidence — (a) the 403, re-measured 2026-08-20:**

| URL | Status | Body |
|---|---|---|
| `https://transparency.flocksafety.com/robots.txt` | **403** | 5,769 B |
| `https://transparency.flocksafety.com/sitemap.xml` | **403** | 5,772 B |
| `https://transparency.flocksafety.com/` | **403** | 5,739 B |
| `https://transparency.flocksafety.com/-el-cajon-pd-ca` | **403** | 5,805 B |
| `https://transparency.flocksafety.com/hagerstown-md-pd` | **403** | 5,808 B, `<title>Just a moment...</title>` |

Byte sizes are within 40 B of the original run's, i.e. the same Cloudflare interstitial. **F2.1 holds.**

**(b) The Wayback exclusion, tested three ways:**

- `http://archive.org/wayback/available?url=transparency.flocksafety.com/hagerstown-md-pd`
  → `{"url": "…", "archived_snapshots": {}}`. Same empty result for
  `transparency.flocksafety.com` and `www.flocksafety.com`.
- CDX API: `https://web.archive.org/cdx/search/cdx?url=transparency.flocksafety.com*&output=json&limit=200`
  → **`[]`** (3 bytes). `…?url=flocksafety.com&matchType=domain&output=json&limit=50` → **`[]`**.
- **Controls run in the same session prove the API works**: `deflock.me` (matchType=domain) returned
  captures from `20241111144402` onward; `eyesonflock.com` returned **859** deduplicated captures.
- **Direct fetch of the replay UI is dispositive.** `https://web.archive.org/web/2025/https://transparency.flocksafety.com/`
  → **HTTP 403**, and the returned page contains verbatim:

  > **"This URL has been excluded from the Wayback Machine."**

**Retrieved:** 2026-08-20
**Implication for the spec:**
1. **R4's report is CONFIRMED independently.** There is no Wayback fallback for the portal layer.
   The 403 wall and the archive exclusion are the same policy expressed twice, and together they
   mean **no third-party general archive of Flock's own surfaces exists**.
2. **This makes F2.8 and F2.9 load-bearing rather than convenient.** Eyes on Flock's accumulated
   audit history and the Archive's captures *of Eyes on Flock* are, as of today, the only
   retrievable historical record of portal state. If Eyes on Flock goes dark, the record is gone.
3. **Therefore SIG must mirror, not merely link.** REQ-R2-10's "link, don't recompute" posture is
   right for *analysis*; it is wrong for *preservation*. A licence-compliant local mirror of
   ecosystem exports is a preservation obligation, and CC BY-SA (F2.7) permits it.
4. Exclusion is requested by the domain holder and is reversible only by them; SIG should not plan
   around it changing.

### F2.11 — There is no public search-audit **CSV URL**: the CSV is a `data:` URI embedded in the rendered portal DOM — and the ~30-day rolling window is confirmed

**Claim:** The outline's premise of a fetchable audit-CSV URL pattern is wrong. The download is a
client-side `data:` URI, retrievable only from the rendered page. The rolling window is 30 days.
**Status:** VERIFIED
**Evidence:** The most mature independent portal archiver, `none-below/sm-alpr`
(`https://github.com/none-below/sm-alpr`, AGPL-3.0, last push 2026-08-20), extracts audit CSVs like
this — from `scripts/flock_transparency.py`, verbatim:

> `"""Extract data-URI CSVs from <a download="*.csv" href="data:..."> tags."""`

with the extractor keying on `download.endswith(".csv") and href.startswith("data:")` and then
`urllib.parse.unquote`-ing the payload. The same file records that Flock has **renamed the embedded
file at least once**, and normalises it:

```python
"public_search_audit.csv": "search_audit.csv",
"public-search-audit.csv": "search_audit.csv",
```
with a comment explaining why: *"…otherwise an agency's diff shows search_audit_csv → null AND
public_search_audit_csv null → rows on the format-flip scrape."* Its portal field map also shows the
portal's own labels: `"Download CSV" → download_csv`, `"Public Search Audit" → search_audit`,
`"Search Audit" → search_audit`.

**The 30-day window, stated by an independent archivist** —
`https://github.com/eyes-off/eugene-oregon`, `FlockAuditLogs/readme.md`, verbatim:

> "This data is pulled from the Flock Transparency Portal. **The portal only contains the last 30
> days of data.** These files are intended to be a complete record of these audits that are
> available to the public for the long-term."
> "**CSV files**: A combination of original records as downloaded from the transparency Portal,
> without alteration"

**Retrieved:** 2026-08-20
**Implication for the spec:**
1. **Open question 4 is RESOLVED, by correction.** There is no URL pattern to discover. Any design
   that assumed `GET <portal>/audit.csv` is void. Obtaining the CSV requires rendering the page —
   which F2.1 and REQ-R2-01 forbid SIG from automating — so **SIG's only compliant routes to audit
   CSVs are the Eyes on Flock export (F2.8), licensed third-party mirrors (F2.14), public-records
   requests, and human contributors.**
2. **The 30-day window plus the exclusion (F2.10) means portal audit data is destroyed by default.**
   Anything not captured by a third party within 30 days is unrecoverable except via FOIA. This
   raises the priority of mirroring existing archives above building new capture.
3. **The embedded-filename flip is a real, dated schema drift** SIG's connector must handle by
   normalising to a canonical name while retaining the observed one.

### F2.12 — Flock's legal surface is narrower than assumed: the anti-scraping clause governs API/integration users, there is no public website terms-of-use, and `www` `robots.txt` is permissive

**Claim:** All four legal artifacts were retrieved. The bulk-extraction prohibition R8 relied on sits
in the **API and Integrations Terms**, whose defined scope is Flock's API and integrations accessed
by or for Flock customers — not anonymous readers of a public portal. No general website terms of
use exists.
**Status:** VERIFIED
**Evidence:** All fetched 2026-08-20 with HTTP 200:

| URL | Status | Size | Dated |
|---|---|---|---|
| `https://www.flocksafety.com/robots.txt` | 200 | 234 B | — |
| `https://www.flocksafety.com/legal/api-integration-terms` | 200 | 139,406 B | "Last updated: October 13, 2025" |
| `https://www.flocksafety.com/legal/terms-of-service` | 200 | 167,534 B | "Last Updated: February 16, 2026" |
| `https://www.flocksafety.com/legal/privacy-policy` | 200 | 151,921 B | "Last Updated: August 1, 2025" |

**Note:** `www.flocksafety.com` is **not** behind the challenge — only `transparency.` is.

`robots.txt`, complete and verbatim:

```
User-agent: *
Disallow: /blog-audiences/
Disallow: /use-case-filters/
Disallow: /g0lnomhfn3mgNjgyMWNjOWVjYzk2NmI3ZjI1MmIzNzJl/
Disallow: /nvhc9u4gxsagNjgyMWNjOWVjYzk2NmI3ZjI1MmIzNzJl/

Sitemap: https://www.flocksafety.com/sitemap.xml
```

**The operative restriction**, API and Integrations Terms §1, verbatim:

> "(viii) extract, scrape, or export data in bulk, or in a manner that replicates database-like
> access to Flock's website or APIs. The API is designed for real-time, on-demand queries within
> integrated applications, not for systematic or automated data harvesting. Circumventing rate
> limits, creating multiple accounts to bypass restrictions, or engaging in any activity intended to
> extract large volumes of data is strictly prohibited. We reserve the right to monitor usage,
> throttle requests, suspend access, or terminate your account if we detect violations of this policy."

**But its scope clause is narrow**, verbatim:

> "This Flock API and Integrations Terms describes your ("You" or "Your") obligations when accessing
> or using the Flock Group, Inc. ("Flock" or "our") application programming interface ("API"…) and
> integrations ("Integrations") (collectively "Implementation"). By accessing this Implementation,
> You… agree to comply with these terms, and **shall only use this Implementation for bona fide law
> enforcement purposes ("Purpose")**."

and "Data" is defined as material *"requested to be sent or received through this Implementation, at
the express instruction of a Flock Customer."*

The Customer Terms and Conditions bind **customers**, and restrict them from making Flock Property
available to third parties or from reverse engineering it — again not a public-visitor instrument.

**No general website terms of use exists.** The `/legal` index lists exactly 17 documents —
`api-integration-terms`, `flock-evidence-policy`, `lpr-policy`, `part91-operational-agreement`,
`privacy-notice`, `privacy-policy`, `product-specific-terms`, `state-required-provisions`,
`terms-and-conditions`, `terms-of-service`, `third-party-terms`, `trademark-notice`, `vendor-baa`,
`vendor-compliance-addendum`, `vendor-dpa`, `vendor-infosec-addendum`,
`vulnerability-disclosure-policy` — and **all of** `/terms`, `/legal/terms-of-use`,
`/legal/website-terms-of-use`, `/legal/acceptable-use`, `/legal/transparency-portal-terms` return
**404**.

**Retrieved:** 2026-08-20
**Implication for the spec:**
1. **REFINES, and partially narrows, R8's framing.** The bulk-extraction clause is real and quoted
   accurately, but it is an **API-terms** obligation whose stated audience is integrators acting for
   Flock customers "for bona fide law enforcement purposes." It is not a browsewrap binding the
   public, and there is no browsewrap to rely on instead. SIG should not assert to third parties
   that scraping a public portal breaches Flock's terms — the accurate statement is that **no
   contractual permission exists either way, and the technical control (F2.1) is the operative bar.**
2. **REQ-R2-01 through REQ-R2-03 are unchanged and remain correct** — they rest on the bot-management
   challenge and the *Reddit v. SerpApi* §1201 exposure, not on the API terms. This finding removes a
   weak leg from the argument, leaving the strong ones.
3. **A `robots.txt`-derived permission for `www.flocksafety.com` does exist and is permissive**, so
   REQ-R2-02's refuse-to-run rule does **not** block ingesting Flock's own corporate pages, pricing,
   product line, and legal documents. The two hostnames must be governed as **separate sources with
   separate crawl policies** — the spec currently conflates them.
4. Three dated legal instruments are now pinned (2025-08-01, 2025-10-13, 2026-02-16) and should be
   snapshotted as evidence, since Flock revises them and links "prior versions" behind a portal.

---

## Part 5C — The ecosystem the outline under-covered

### F2.13 — Footnote4a is Have I Been Flocked's editorial arm, is licensed **CC BY 4.0**, and publishes the master portal directory the outline could not find

**Claim:** Footnote4a is not an independent project; it is HIBF's reporting publication. It states a
licence, offers RSS, and publishes a maintained plain-list of every known Flock transparency portal.
**Status:** VERIFIED
**Evidence:** `https://footnote4a.org/about` → **200**, verbatim:

> "**About Footnote4a** — The footnotes to haveibeenflocked.com. The main site has the data, the
> lookup tool, and the reports. This is where the reporting lives: mass surveillance, government
> contracts, and the public records that pry both open. Any questions, comments, or tips?
> **humans@haveibeenflocked.com**."

> "© 2026 Footnote4a — editorial publication of haveibeenflocked.com. **Articles are published under
> CC BY 4.0 unless otherwise noted.**"

Contact/syndication: `humans@haveibeenflocked.com`, Bluesky **@hibflocked**, an email newsletter, a
donate link ("tax-deductible"), and **six RSS feeds** — all reporting, Investigations, Contract &
Procurement, FOIA & Transparency, Audit Log Analysis, Policy & Legal, Quick Takes.

`https://footnote4a.org/robots.txt` → **200**, verbatim:

```
# robots.txt for Footnote4a
User-agent: *
Allow: /
Disallow: /api/
Disallow: /health
Crawl-delay: 1
Sitemap: https://footnote4a.org/sitemap.xml
```

**The portal directory:** `https://footnote4a.org/news/transparency-portals` → **200**, 163,210 B.
Byline *"by Have I Been Flocked Team"*, published **November 3, 2025**, *"(Updated: May 4, 2026,
10:00 PM UTC)"*. It is a flat list of `https://transparency.flocksafety.com/<slug>/` URLs.
**Parsed: 877 distinct slugs.**

**Cross-validation against the Eyes on Flock API (950 slugs), computed 2026-08-20:**

| | count |
|---|---|
| Eyes on Flock only | **90** |
| Both | **860** |
| Footnote4a only | **17** |
| **Union** | **967** |

Footnote4a-only entries include non-agency artifacts Eyes on Flock filters out: **`demo`,
`flock-safety-le-training`, `flock-safety-marketing`, `florida-le-flock-training`**, plus
`ca-napa-valley-college-campus` and `columbus-regional-airport-authority-oh-pd` — the latter two
being exactly the university/airport organizations absent from EoF's `PD`/`SD`-only taxonomy (F2.6).

**Retrieved:** 2026-08-20
**Implication for the spec:**
1. **Open question 5 is RESOLVED.** A master portal directory does exist — two of them, independently
   maintained — despite `sitemap.xml` being unreachable. SIG's portal registry should be seeded from
   the **union (967)**, with per-slug provenance recording which directories attest to it.
2. **Two-source agreement is a free, immediate quality signal.** 860 slugs corroborated by two
   independent crawlers are Tier-A-ish; the 107 single-source slugs are candidates requiring
   confirmation. This is a concrete instance of the reconciliation workflow SIG needs anyway.
3. **Vendor demo and training portals are in the wild and will contaminate any naive census.**
   `flock-safety-marketing` and `*-le-training` are not deployments. The registry needs an explicit
   `is_agency_deployment` predicate and a rejects list, and camera/search counts drawn from demo
   portals must never enter aggregates.
4. **Footnote4a's CC BY 4.0 is a licence for the *articles*, not necessarily for HIBF's data.** They
   are distinct instruments on distinct properties; do not infer one from the other.
5. **Footnote4a is a Tier-B secondary source with RSS**, i.e. cheaply monitorable. It is also the
   correct citation target for narrative claims, and `humans@haveibeenflocked.com` is the HIBF-family
   contact channel Phase 0 needs.
6. **This CORRECTS F2.4**, which listed Footnote4a as "an ecosystem project the outline does not
   mention" requiring Stage 0 investigation as though it were a separate party. It is HIBF.

### F2.14 — Seven substantive Flock-data projects the outline does not name, four of them created since mid-2025

**Claim:** The ecosystem is materially larger than §2 Layer C describes. Discovered via GitHub code
search on `transparency.flocksafety.com` and `eyesonflock.com`, then verified against the live repos
and sites.
**Status:** VERIFIED
**Evidence:**

| Project | URL | Licence | Created / last push | What it is |
|---|---|---|---|---|
| **`none-below/sm-alpr`** | `https://github.com/none-below/sm-alpr` | **AGPL-3.0** | 2026-03-28 / **2026-08-20** | The most sophisticated portal archiver found. Daily-dated captures per slug; sharing-graph builder; PRA-audit importer; rename detection; scrape diffing. Publishes `sharing_map.html`, `scoreboard.html`, `SMPD_ALPR_Findings.pdf` via GitHub Pages. Repo size ~2.5 GB. |
| **`eyes-off/eugene-oregon`** | `https://github.com/eyes-off/eugene-oregon` | **CC0-1.0** | 2025-08-22 / 2026-01-26 | Long-term archive of Eugene OR search-audit CSVs, explicitly to defeat the 30-day window (F2.11). Part of `eyesoffeugene.org`. |
| **`flock.ajith.fyi`** | `https://flock.ajith.fyi/` | none stated | live | Astro + Leaflet + sql.js. Ships a **65 MB SQLite database** (F2.15). |
| **`simeononsecurity/flock-finder`** | `https://github.com/simeononsecurity/flock-finder` | **MIT** | 2026-07-16 / 2026-08-16 | *"Map Flock Safety ALPR surveillance cameras using WiGLE WiFi data and OUI fingerprinting. Auto-updated daily."* A **wholly different detection modality** — RF/MAC-OUI rather than portals or visual survey. |
| **`resistanceisliberty/panopti.ca`** | `https://panopti.ca/` · `https://maps.panopti.ca/` | **MIT** | 2026-06-08 / **2026-08-20** | *"A Canadian-centric fork of DeFlock."* Bilingual EN/FR; also maps government CCTV; runs a candidate/city-council campaign layer. **Extends coverage beyond the US.** |
| **`mcclatchy-southeast/private_eyes`** | `https://github.com/mcclatchy-southeast/private_eyes` | **MIT** | 2024-04-19 / 2024-05-02 | *"Code and data powering The News & Observer's reporting…"* A newsroom dataset that surveys NC agencies and **flags portal-vs-reality discrepancies** in a controlled column (e.g. `Confirmed by dept.; Portal discrepancy - 1 is a test model`). |
| **`Ringmast4r/FLOCK`** | `https://ringmast4r.github.io/FLOCK` | **none (147 stars)** | 2025-11-14 / 2025-11-15 | *"Surveillance camera network map — 336K+ cameras worldwide with inter-agency data sharing visualization."* Largest claimed camera count in the ecosystem; unmaintained since creation; **no licence**. |

Also live but not examined in depth: `https://alpr.wtf/` (**200**, 800,127 B — a jurisdiction/FOIA
index), `https://dontgetflocked.com/` (**403**, Cloudflare — route planner), `https://noalprs.com`
and `https://eyesoffcr.org` (linked from EoF's resources page and R1-F1.10 respectively).

**Retrieved:** 2026-08-20
**Implication for the spec:**
1. **`none-below/sm-alpr` is the reference implementation of SIG's own snapshot layer, and it is
   AGPL-3.0.** Its capture design — for every slug, a dated `YYYY-MM-DD.txt` (raw DOM text, declared
   *"source of truth"*), `.html`, `.json` (parsed, derived), and `.pdf` (visual archive), plus
   `.content_hashes.json` and `.failed_slugs.json` sidecars — is exactly the four-artifact model the
   outline wants and SIG should adopt it verbatim as REQ-R2-16. **But note its crawler uses Playwright
   headless Chromium with jittered delays, exponential backoff on 403, and an optional Tor proxy —
   which is precisely the technique set REQ-R2-01 forbids SIG from operating.** SIG may adopt the
   *archive format* and consume the *outputs*; it may not adopt the *acquisition method*. AGPL-3.0
   also means any SIG service incorporating its code must offer source.
2. **`eyes-off/eugene-oregon` is CC0** — the only unambiguously unencumbered audit data found. It is
   the correct first ingestion target for the audit connector.
3. **`flock-finder` breaks a modelling assumption.** SIG's schema must not presume camera existence
   is evidenced only by portals, agency records, or human survey; RF/OUI fingerprinting is a fourth,
   independent detection modality with its own error profile, and it needs its own evidence class.
4. **`panopti.ca` extends the domain past the US border**, which the outline's geography does not
   contemplate. Country must be a first-class field, not implied.
5. **`private_eyes` supplies a validated prior**: portal-vs-department discrepancy is a *known,
   documented, newsroom-verified phenomenon* with a worked NC example, and its "test model" note
   independently corroborates F2.13's demo-portal contamination finding.
6. **Two projects with the widest reach have no licence at all** (`Ringmast4r/FLOCK`, 147 stars;
   `flock.ajith.fyi`). Popularity is not permission.

**Outline delta:** **EXTENDS §2 Layer C and §21 substantially.** Four of these post-date mid-2025
and none appears in the outline. REQ-R2-11 is superseded: the Stage-0 investigation list is no longer
"Footnote4a, flock.ajith.fyi, and the California sharing visualization" but the seven above.

### F2.15 — `flock.ajith.fyi` publishes a 65 MB SQLite database containing 350,043 search-audit rows with **9,717 un-redacted operator UUIDs**

**Claim:** A single unauthenticated GET returns a complete relational database of Flock audit data,
including raw operator identifiers, agency sharing edges, and a portal-probe census with negatives.
**Status:** VERIFIED
**Evidence:** The site is Astro; its bundle
(`/_astro/index.astro_astro_type_script_index_0_lang.DJRtG60Z.js`, **200**, 77,950 B) contains
`fetch("/audit_db")` and loads `https://sql.js.org/dist/` — it queries SQLite in the browser via WASM.

`https://flock.ajith.fyi/audit_db` → **200**, **68,313,088 B**, `application/octet-stream`;
`file` reports *"SQLite 3.x database … 16678 pages"*. Opened with `sqlite3`:

| Table | Rows | Columns |
|---|---|---|
| `departments` | **5,506** | `dept_slug, flock_status, name, last_updated, camera_count, vehicles_30_days, searches_30_days, latitude, longitude, state_code` |
| `searches` | **350,043** | `search_dept, search_id, user_id, time, camera_count, reason` |
| `connections` | **21,608** | `connection_id, dept_a, dept_b` |
| `uscities` | 31,254 | (SimpleMaps-style gazetteer) |
| `uscounties` | 3,144 | (gazetteer) |

Measured:
- `flock_status` ∈ {**404: 5,011**, **200: 495**} — a **portal-discovery census that retains its
  negative probes**. Only 459 departments carry a `camera_count`.
- `searches.time` spans **2024-12-28 → 2025-09-14** (260 days) over **184** distinct departments.
- **`user_id` is a raw UUID on all 350,043 rows — zero redaction — across 9,717 distinct operators.**
- `departments.last_updated` spans only 2025-01-28 → 2025-02-02: **the dataset is ~18 months stale.**
- Reasons show the same free-text drift: `Investigation` 12,035, `investigation` 10,241, `inv` 6,983,
  `Daytime search for best result` 6,154, `10851` 5,715, `invest` 5,298, `stolen` 4,016, `GTA` 3,472.
- No `/robots.txt` (404) and no licence statement anywhere on the site.

**Retrieved:** 2026-08-20
**Implication for the spec:**
1. **This is the ecosystem's clearest privacy hazard and SIG must have a written position before
   touching it.** 9,717 stable pseudonymous operator identifiers, joined to timestamps, agencies and
   free-text reasons, are re-identifiable against rosters and shift schedules obtainable by FOIA —
   and HIBF already publishes Police Rosters and Name Resolution (F2.4). SIG must not become the
   join that de-pseudonymises individual officers. **Operator identifiers must be hashed with a
   held-back salt at ingest, and raw values must never be republished**, regardless of the fact that
   a third party has already published them.
2. **Retaining negative probes is a design idea worth copying.** 5,011 confirmed-absent slugs are
   evidence, and `flock_status` is a per-slug dated observation — exactly the "artifact
   disappearance is a dated event" posture of spec §17.6, applied to non-existence.
3. **It is a corroboration source, not a current one.** At ~18 months stale it is useless for
   current state but valuable as an independent 2025 baseline against the EoF Wayback series (F2.9).
4. Un-licensed, un-authored, and unmaintained: treat as INACCESSIBLE for redistribution purposes
   even though it is technically downloadable.

---

## Part 5D — The ALPR Accountability Atlas, captured verbatim (the model SIG adopts)

### F2.16 — The Atlas publishes five downloadable artifacts and a 40-field data dictionary, but its five-way epistemic model is **prose, not an enumerated field** — and it carries **no licence at all**

**Claim:** Every Atlas data asset was downloaded and profiled. Its evidence-typing design is sound
and worth adopting, but the specific column the outline points at (`claim_status`) is uncontrolled
free text, and the project states no licence, no author, and no reply-capable contact.
**Status:** VERIFIED
**Evidence:** `https://alpratlas.org/` → **200**, 16,474 B. It is a single-route SPA: `/about`,
`/methodology`, `/terms`, `/license`, `/legal`, `/privacy`, `/faq`, `/data`, `/docs`, `/sources`,
`/robots.txt`, `/sitemap.xml`, `/humans.txt`, `/.well-known/security.txt` **all return 404**
(9-byte `text/plain` "Not Found"). About and Method are in-page modals. Meta tags declare
`research-model = living-reviewed-index`, `initial-seed-verified-through = 2026-07-21`,
`affiliation = independent-not-endorsed`.

**Downloadable artifacts (all HTTP 200):**

| Artifact | URL | Bytes | Rows/Features |
|---|---|---|---|
| Issue-record CSV | `https://alpratlas.org/data/flock_safety_us_issues.csv` | 303,587 | **280** rows, 40 cols |
| Source-index CSV | `https://alpratlas.org/data/flock_safety_sources.csv` | 31,601 | **88** rows, 10 cols |
| Data dictionary | `https://alpratlas.org/data/flock_safety_data_dictionary.csv` | 3,119 | **40** rows (`field, description`) |
| GeoJSON | `https://alpratlas.org/data/flock_safety_us_issues.geojson` | 676,547 | **280** features, 40 props |
| Research bundle | `https://alpratlas.org/data/flock_safety_research_bundle.zip` | 315,902 | 9 files, 2,067,761 B raw |
| Methodology README | `https://alpratlas.org/data/README_flock_safety_research.md` | 7,080 | — |
| Build script | `https://alpratlas.org/data/build_flock_research.py` | 180,214 | full reproducible generator |
| Quality report | `https://alpratlas.org/data/flock_safety_quality_report.json` | 2,976 | `errors: []`, `warnings: []` |
| Live API | `https://alpratlas.org/api/research?limit=1000` | 531,546 | 280 records, `next_cursor: null` |

`/api/research` `meta`, verbatim: `{"approved_record_count":280,"source_count":88,
"verified_through":"2026-07-21","public_scope":"approved_records_only"}`. CSVs are UTF-8 **with a BOM**.

**Issue-record columns, verbatim in order (40):**
`record_id, event_date_start, event_date_end, date_precision, publication_date, state, city, county,
jurisdiction, agency_or_entity, category, subcategory, headline, summary, claim_status,
flock_connection, legal_case_name, court, docket_or_case_no, case_status, outcome_or_response,
company_or_agency_response, primary_source_id, primary_source_title, primary_source_publisher,
primary_source_url, supporting_source_ids, supporting_source_urls, source_type, evidence_strength,
national_scope, search_count, network_count, device_count, latitude, longitude, geocode_precision,
tags, notes, last_verified`

**Source-index columns, verbatim (10):** `source_id, published_date, title, publisher, url,
source_type, perspective, geographic_scope, notes, last_verified`

The GeoJSON drops `latitude`/`longitude` into `geometry.coordinates` and **adds two derived fields
absent from the CSV**: `category_family`, `event_year`.

**The controlled vocabularies — the decisive finding.**

- **`claim_status` is NOT a closed vocabulary: 50 distinct free-text values across 280 rows, 18 of
  them singletons.** Top values: `Documented audit-log entry` 147, `Reported incident; legal
  liability not necessarily adjudicated` 20, `Reported municipal or agency action` 16, `Documented
  configuration record (no issue found for this setting)` 11, `Criminal charge pending / reported`
  11, `Documented but context ambiguous` 9, `Reported agency action` 7, `Court disposition` 5,
  `Published appellate ruling` 4, … down to singletons like `Stakeholder position`, `Company
  self-report`, `Company policy statement`, `Government audit finding`.
- The five-way model exists **only in UI prose**. Homepage banner, verbatim:
  > "Allegations, findings, court actions, policy decisions, and company statements stay distinct.
  > Points are approximate display locations, never exact cameras or targets."

  Record dialog, verbatim:
  > "This index distinguishes allegations, reported incidents, audit findings, court decisions,
  > policy actions, and stakeholder statements. Check the linked source or docket for changes after
  > July 21, 2026."
- **`evidence_strength` IS closed and well-specified — 3 values:** `High` 253, `Medium` 25, `Low` 2.
  Rubric verbatim from the README:
  > "**High:** court document, government audit/ruling, source spreadsheet or audit logs, detailed
  > documentary investigation, or strongly corroborated local action. **Medium:** credible news or
  > advocacy compilation with clear attribution but limited underlying documentation in the collected
  > set, or a newly raised concern not yet adjudicated. **Low:** company self-report,
  > marketing/impact claim, or contextual policy statement included to preserve counterevidence and
  > stated safeguards. Evidence strength does not mean moral severity, and it is not a prediction of
  > who will win an active lawsuit."
- **`flock_connection` is a separate attribution-confidence axis — 11 values:** `Confirmed Flock`
  258, `Broader ALPR—Flock unconfirmed` 8, `Flock equipment/service used by defendant retailer` 3,
  `Flock and other ALPR vendors` 2, `Flock is a principal vendor in challenged network` 2,
  `Company statement` 2, then singletons incl. `Flock is defendant`.
- **`category_family` (GeoJSON/API only) IS closed — 12 values:** Discrimination / profiling 82,
  Mission creep 45, Protest / First Amendment 30, Personal / insider misuse 25, Immigration / data
  sharing 23, Local action / regulation 23, Wrongful stop / false alert 21, Litigation / court ruling
  19, Security / product / installation 7, Company / stakeholder context 3, Reproductive-health
  surveillance 1, Governance / efficacy debate 1.
- **Uncontrolled drift elsewhere:** `category` 37 values, `subcategory` 94, `date_precision` **45**,
  `geocode_precision` **93**, `perspective` 26, `geographic_scope` 21. **`source_type` uses two
  divergent vocabularies across the two CSVs (39 values vs 53) — which will break any join.**
- `last_verified` is the single value `2026-07-21` on **all 280 records and all 88 sources**.
  `case_status` is empty on 260/280; `court` empty on 261/280. `event_year`: 2021 (1), 2022 (3),
  2023 (9), 2024 (96), 2025 (109), 2026 (62).

**Privacy design, verbatim from the README:**
> "Coordinates are **display points only**… They are not exact camera locations, homes, traffic
> stops, plaintiffs' addresses, or surveillance targets. Exact plate numbers and private target
> identities are excluded."

with `geocode_precision` recording the method per row (`<place> display centroid + deterministic
jitter`; 152 rows are state-level centroids, 10 national).

**Editorial process, verbatim from the README's "Updating the index":**
> "1. Add a source to the source table with publication date, type, perspective, and URL.
> 2. Add or amend an underlying record; do not create a duplicate just because another article
> covered it. 3. Preserve attribution words such as 'alleged,' 'reported,' 'audit found,' or 'court
> held.' 4. Record material agency/company responses and later court dispositions. 5. Re-geocode only
> to a jurisdiction centroid; never publish exact camera or target coordinates in this map.
> 6. Update `last_verified` and rerun validation."

with the record-unit rule *"The record unit is the **underlying event or agency finding**, not the
headline"*, an exclusion rule for *"purely promotional deployment announcements and routine
crime-arrest stories… unless they supplied a necessary counterpoint"*, and a moderation queue
(*"Nothing submitted here is published automatically"*).

**LICENCE: definitively NONE.** No licence, copyright notice, terms of use, attribution requirement,
or citation guidance exists anywhere. There is no `<footer>` element on the site at all (zero
occurrences of "footer" in the HTML, the JS bundles, or the CSS). Every apparent match for "license"
across all downloaded bytes was the phrase "license plate". URLs checked and found absent: the
homepage HTML, all five JS/CSS bundles, the README, the build script, all four CSV/GeoJSON files,
the ZIP interior (no `LICENSE`/`COPYING`), the HTTP response headers (no `Link: rel="license"`), and
the 404s at `/license`, `/licence`, `/LICENSE`, `/LICENSE.txt`, `/legal`, `/terms`, `/privacy`,
`/about`, `/faq`, `/humans.txt`, `/robots.txt`, `/.well-known/security.txt`. The nearest thing to a
reuse statement grants no rights:
> "This tool is designed to support investigation, accountability reporting, legal research, policy
> analysis, and public debate. It should not be used as a substitute for checking the cited source,
> docket, or current law."

**Contact: one anonymous, one-way channel only** — an in-app modal posting to
`POST https://alpratlas.org/api/submissions` (GET returns **405**), labelled *"Send privately"*, with
the warning *"Do not include names, contact information, precise private locations, or anything
confidential. Nothing submitted here is published automatically."* A regex sweep for email addresses
and every major repo/social host across all site assets returned **zero** matches. No named author,
organization, or funder. `gh search repos alpratlas` → 0 results; `gh search code
"flock_safety_us_issues"` → 0 results. **No code repository exists** — though the complete generator
is published as a file.

**Retrieved:** 2026-08-20
**Implication for the spec:**
1. **Adopt the architecture, not the implementation.** The Atlas's real contribution is **two
   orthogonal axes**: `evidence_strength` (how well-documented) and `flock_connection` (how certainly
   attributable to Flock). Keeping them apart is what lets it hold company statements as
   counterevidence at `Low` without laundering them into findings. SIG MUST adopt both axes.
2. **SIG MUST implement the five-way epistemic model as a genuine closed enum**, which the Atlas did
   not. The proof it is achievable is in the same dataset: `evidence_strength` (3) and
   `category_family` (12) are clean, while `claim_status` (50), `date_precision` (45),
   `geocode_precision` (93) and `subcategory` (94) drifted. Design: a closed `claim_status` enum plus
   a free-text `claim_status_detail` column carrying the prose.
3. **Copy the negative controls.** 11 records are explicitly `Documented configuration record (no
   issue found for this setting)` / `Control comparison: immigration hotlist disabled`. A dataset that
   can record the absence of an issue is a dataset that can be trusted about its presence.
4. **Copy the geocode-precision-as-data pattern.** Recording jitter method per row, in a column, is
   directly transferable to SIG's camera-location handling.
5. **The licence gap is disqualifying for redistribution and must not be replicated.** SIG may adopt
   the vocabulary (ideas and facts are not copyrightable) and cite the Atlas, but **must not mirror
   its CSV/GeoJSON** without permission — and the only channel to seek permission is an anonymous
   one-way form with no reply path. Record as **all-rights-reserved by default**.
6. **The "living" claim is not currently borne out** — a single `last_verified` of 2026-07-21 across
   all 368 rows, ~13 months old at retrieval. SIG must record observed freshness, not claimed cadence.

**Outline delta:** **CORRECTS §20 Q15's premise.** The outline treats the Atlas's
allegation/finding/court-action/policy-decision/company-statement labels as an existing controlled
vocabulary SIG can adopt. It is an *editorial principle* expressed in prose over an uncontrolled
column. SIG must build the enum the Atlas describes but did not implement.

### F2.17 — Reddit is login-walled: r/FlockSurveillance is no longer retrievable, by any route tried

**Claim:** Every documented method of reading r/FlockSurveillance programmatically now fails.
**Status:** INACCESSIBLE
**Evidence:** All 2026-08-20:

| Method | Result |
|---|---|
| `https://www.reddit.com/r/FlockSurveillance/comments/1ra26qw/.json` | **403**, 189,908 B of `text/html` |
| `https://www.reddit.com/r/FlockSurveillance/new.json?limit=100` | **403**, 189,908 B |
| `https://old.reddit.com/r/FlockSurveillance/comments/1ra26qw/` | **200** but redirected to `https://old.reddit.com/login/?reason=lor2&dest=…`, `<title>Welcome to Reddit</title>` |
| `https://old.reddit.com/comments/1ra26qw.json` | 200, HTML login interstitial |
| `https://www.reddit.com/svc/shreddit/comments/1ra26qw` | 200, HTML interstitial |
| `https://oauth.reddit.com/…` | **403** |
| `redlib.catsarch.com` | **403** · `redlib.perennialte.ch` **503** · `safereddit.com` 200 but an **Anubis proof-of-work challenge** |
| `http://archive.org/wayback/available?url=reddit.com/r/FlockSurveillance/comments/1ra26qw/` | `{"archived_snapshots": {}}` |
| Same for `…/1slvs6a/` | `{"archived_snapshots": {}}` |

The two posts named in the brief were therefore **not read**. Their content was recovered indirectly:
the Eyes on Flock author post's subject matter is superseded by the first-hand reverse-engineering in
F2.6–F2.9, and the "California sharing visualization" was identified independently via GitHub code
search as **`none-below/sm-alpr`** (F2.14), whose archival design — dated PDF + raw DOM text + HTML +
normalized JSON per slug per day — matches the description in the brief exactly.

**Retrieved:** 2026-08-20
**Implication for the spec:**
1. **Remove Reddit from the source plan as a machine-readable input.** Any ingestion, monitoring, or
   discovery design that assumes `.json` permalinks or `new.json` polling is void as of 2026.
   Discovery of new ecosystem projects must run on GitHub code search, RSS (F2.13), and web search.
2. **Reddit-sourced citations in the outline cannot be verified by SIG and must be re-sourced** to a
   durable artifact (a repo, a site, an archived page) or marked UNVERIFIED.
3. This is a **general availability lesson**: three of this workstream's sources (Flock portals,
   Reddit, Wayback-for-Flock) are gated by anti-bot or auth walls that did not exist when the outline
   was written. The spec's source registry needs an `access_status` field with dated observations.

---

## Part 5E — HIBF, ALPR Watch, and the ALPR Abuse Library: licences, exports, cadence

### F2.18 — Have I Been Flocked states **no licence at all**, but **does** ship an undocumented bulk CSV export — which its own `robots.txt` disallows

**Claim:** HIBF's terms question resolves negatively: there is no licence, no copyright line, and no
reuse grant anywhere on the domain. But it **does** publish real bulk downloads via an undocumented
`/api/` surface — and that surface is exactly what `robots.txt` forbids crawling.
**Status:** VERIFIED

> **Correction.** An earlier draft of this finding asserted "no bulk export exists," inferring it from
> `/data`, `/export` and `/api` all returning 404. That was wrong: the export is one path level
> deeper. The endpoints below were called and their bodies parsed.

**Evidence — all retrieved 2026-08-20.**

**(a) Licence — none, definitively.** The homepage (**200**, 75,606 B) and `/about` (**200**,
56,842 B) share one footer, verbatim and complete — note the absence of any copyright line:

> "Deflock | Eyes on Flock | MuckRock | ACLU: Get the Flock Out | 404 Media: ICE Camera Network |
> ALPR Abuse Library | Donate | @hibflocked | Bluesky | Contact: humans@haveibeenflocked.com |
> HaveIBeenFlocked.com is not affiliated with Flock Safety or any government agency; we are fiscally
> sponsored by, but editorially independent from, Alternative Newsweekly Foundation, a 501(c)3
> non-profit."

`/terms`, `/legal`, `/privacy`, `/faq`, `/about/sources`, `/about/submit` all **404** — the real
paths are `/about/privacy-policy`, `/about/faq`, `/sources`, `/about/submit-audit-logs`. A sweep of
every fetched page for `copyright|©|rights reserved|creative commons|cc-by|terms of use|redistribut|
attribution` returned **zero** hits. `/sitemap.xml` (**200**, 2,171,516 B) enumerates **6,609 URLs**,
of which only 23 are non-agency pages — **there is no `/license`, `/terms`, or `/copyright` route in
the sitemap.** The only `©` on the domain is in `/feed.xml`: `<copyright>© 2026 Footnote4a</copyright>`,
which belongs to the sibling editorial site (F2.13), not to HIBF's data.

The nearest reuse-adjacent statements are scoping disclaimers that grant nothing, from `/about/faq`:

> "**Should you be publishing this information?** This website aggregates and reformats
> already-public information. This information represents a fraction of what's being shared with
> Flock and its government, commercial, and private partners on a daily basis."
> "**Can I request data removal?** This website only displays information from records that are
> already in the public domain. We do not control or access the underlying Flock database."

**(b) The bulk export — real, undocumented, and robots-disallowed.**
`https://haveibeenflocked.com/robots.txt` (**200**, 206 B), verbatim:

```
# robots.txt for Have I Been Flocked?

User-agent: *
Allow: /
Disallow: /api/
Disallow: /word-cloud/
Disallow: /*-records
Disallow: /news/

Crawl-delay: 1

Sitemap: https://haveibeenflocked.com/sitemap.xml
```

Against that, the report pages carry a `Format: [CSV|JSON]` dropdown backed by
**`GET /api/reports/{reportType}/download`**. Verified live:

| Endpoint | Result |
|---|---|
| `/api/reports/first-amendment-records/download` | **200**, **24,899,820 B**, `text/csv`, `content-disposition: attachment; filename="first-amendment-records-2026-08-20.csv"`, **26,573 lines** (26,572 records + header) |
| `/api/pd/agency/{org_id}/download` | **200**, `text/csv`, `filename="agency-4468-2026-08-20.csv"` |
| `/api/reports/immigration-records/download` | **200** headers, body **truncates at 368 B** ending in a literal in-band `# ERROR: download incomplete — please retry` — reproducible |
| `…/download?format=json` | **504** `{"error":"Database query timeout. Please try again."}` |
| `/api/reports/record-irregularities/download`, `/reason-cloud/download`, `/statistics-daily/download` | **404** |
| `/api/reports/counts` | **200**, 1,521 B — per-report `recordCount` + `refreshedAt` for all 18 reports |
| `/api/sources/stats` | **200**, **2,015,825 B** — `{sources:[2,486 objects], updatedAt:"2026-08-19T18:00:34.670Z"}` |
| `/api/ice-287g` | **200**, 710,045 B |
| `/api/health/minimal` | **200**, 333 B |
| `/api/reports/{type}` | paginated, **server caps at 100 rows/request** regardless of `limit`; cursor-based (`?cursor=eyJyIjoxMDB9`); `total` caps at 10,001 |
| `/data`, `/export`, `/download`, `/openapi.json`, `/api/docs` | **404** — no published documentation, no API terms |

**The 25-column export schema**, verbatim from the CSV header:
`id, search_time_utc, name, best_name, best_name_confidence, license_plate_hash, org_name,
org_locality, org_state, reason, case_number, text_prompt, moderation, search_type, object_class,
total_devices_searched, total_networks_searched, start_timeframe_utc, end_timeframe_utc, org_id,
filters, redacted_at, redaction_reasons, redactions, sources`

A real row shows what this means in practice — resolved officer name with a confidence score, a
hashed plate, structured redaction metadata, and an editorial annotation injected into `reason`:

```
d94736da…,,J. Ali,John Alipour,0.77,,DuPage County Forest Preserve IL PD,DuPage County Forest
Preserve,IL,[HIBF Note: See https://footnote4a.org/news/dupage-county-2],,,,,,3118,207,
2025-02-05T20:00:49.000Z,2025-02-05T22:00:49.000Z,6192,Chevrolet White,"2026-05-08T15:09:25.076Z",
["dob","length","lka","name","phone"],{"name":true,"ssn":…
```

**These are explicitly NOT the source records.** From `https://haveibeenflocked.com/news/feature-downloads`
(2025-11-18), verbatim:

> "You can now download data directly from reports and agency views in CSV or JSON format. It is
> important to note that these downloads are **NOT** (excerpts from) the original source files! The
> files are generated from the haveibeenflocked.com database, after they have been processed and
> imported, a process which could introduce errors. … they are not intended to be a substitute for
> original, agency-provided sources."

Stated differences: license-plate **hash** instead of plate; added `best_name` /
`best_name_confidence`; PII redacted from `reason`; redaction results included; per-record source
info included. A later post (`/news/csv-redaction-fix`, 2026-02-27) records that *"the record cap has
been **raised from 10,000 to 100,000 records per download**."* An internal job registry string in the
site bundle confirms the design: `"report-downloads":{title:"Report Downloads",description:
"Pre-generated CSV and JSON files for all report types (uploaded to R2)",category:"internal"}`.

**(c) Cadence — measured, not promised.** From `/about/faq`, verbatim:

> "**How up-to-date is this data?** The data's freshness depends entirely on when we receive audit
> logs from public records requests or transparency portals. There can be a significant delay —
> months or even years — between when a search occurs and when it appears on this website. **This is
> not a real-time monitoring tool.**"

Measured at 21:24 UTC on 2026-08-20, `/api/health/minimal` returned verbatim:

```json
{"status":"healthy","services":{"database":"ok","redis":"ok"},
 "data_processing":{"latest_import":"2026-08-14T01:04:09.325Z",
                    "mv_refresh":"2026-08-13T15:32:29.381Z","is_stale":true},
 "active_import":{"is_importing":true,"count":2761,"oldest_started":"2026-08-01T04:00:03.008Z"}}
```

`/api/reports/counts` shows most materialized views refreshed **the same day** (2026-08-20, ~08:29–08:40
UTC) — so derived reports rebuild roughly daily — with one stark outlier: **`ca-oos-records`
(116,517 records) and `ca-oos-organizations` last refreshed 2026-01-12, seven months stale.** Record
counts: `non-criminal-records` 973,151; `lowlevel-records` 304,047; `profiling-records` 127,105;
`first-amendment-records` 26,572. Agency ingests run a few per week, batched irregularly.

Headline totals at retrieval: **241,961,192 searches, 4,684,253 unique plates, 488,042,923 total
records, 6,581 organizations, 2,486 source files**, most recent search 2026-07-31, least recent
2021-12-01.

`/sources` is client-rendered (curl sees *"Showing 0 sources … Loading source statistics… Last
updated: —"*), backed by `/api/sources/stats`. Its static caption carries a **material data-quality
caveat**, verbatim:

> "Orgs, Names, Plates, and Reasons counts are **approximate (±2% margin) using HyperLogLog**. All
> other values are exact."

The largest single source in that feed is `upload_id: 0`, `filename: "Transparency Portal"`,
`source_url: https://transparency.flocksafety.com/`, **1,317,235 records** — i.e. HIBF ingests portal
data as one synthetic source alongside 2,485 FOIA'd files.

**(d) Provenance and submission terms.** From `/about/faq`, verbatim:

> "The data consists of 'audit logs' tracking searches made within the Flock system. To satisfy
> public oversight requirements, some local governments make these logs available to the public upon
> request, and others publish heavily redacted versions on a Flock-provided 'Transparency portal.'
> This website aggregates audit logs that have been released via open records (FOIA) requests. **The
> dataset is incomplete**; few governments provide easy access to these logs, and the records we
> obtain are often redacted."

From `/about/submit-audit-logs`, verbatim:

> "**Send files 'as-is'** — Send the files exactly as you received them. Do not open and re-save
> them, do not merge spreadsheets, do not delete columns you think are irrelevant, and do not rename
> the files."
> "**Proof the records came from a records request** — Every submission needs something showing the
> files were released by the agency."
> "**What we store about you** — Your email address and the IP address you submit from are stored
> alongside the files… **This is the only part of the site that keeps a raw IP address; everywhere
> else it is hashed.**"
> "**What happens next** — A person reviews every submission by hand. Nothing you upload goes
> straight into the public database… **we'll credit you by the name you give us — or not at all, if
> you leave that blank.**"

**There is no copyright assignment and no licence grant on submitted material** — only tickbox
confirmations that the files came lawfully from an agency and were not altered.

**(e) Fragility and legal exposure.** From `/about/funding`, verbatim:

> "It's **one developer**, driven by community support."  ·  "The site and database currently cost
> around **$80/month** to run."  ·  "**Flock has already tried to take this site down twice. One
> attempt failed, one is pending (as of January 15, 2026).**"

and from `/about/privacy-policy`: *"this site currently runs on Hetzner — **though Flock is trying to
change that**."*

**(f) Contact:** `humans@haveibeenflocked.com`; Bluesky `hibf.bsky.social` / `@hibflocked`; X
`@hibflocked`; a Discord invite (`discord.com/invite/aV7v4R3sKT`) which **resolves to the DeFlock
guild (~9,482 members), not a HIBF-specific server**; Buttondown newsletter; donations via the
Alternative Newsweekly Foundation (the Ko-fi route is retired). Also documented and previously
unnamed: `/about/open-records-guide` (*"drawn from **over 500 completed public records requests**"*),
`/about/redactions`, `/about/duplicate-handling`, `/about/search-anomalies`, `/about/name-resolution`,
`/about/police-rosters`, `/about/search-types`, `/moderation-logs`, `/updates`.

**Retrieved:** 2026-08-20
**Implication for the spec:**
1. **Q4 is ANSWERED on both halves, and they point in opposite directions.** Exports **exist** and are
   substantial; a licence **does not**. Technical availability is not permission. HIBF remains a
   **reference-only** source under REQ-R2-18.
2. **`robots.txt` is the decisive instrument here.** `Disallow: /api/` covers the download endpoints
   and `Disallow: /*-records` covers every report page SIG would want
   (`/immigration-records`, `/first-amendment-records`, `/profiling-records`, `/lowlevel-records`,
   `/non-criminal-records`, `/develop-pc-records`, `/irregular-records`). Under REQ-R2-02's own logic
   this is an **explicit, machine-readable refusal** that SIG must honour — the fact that the files
   download cleanly is irrelevant. A human may click Download; SIG's crawler may not.
3. **The exports are derived, not primary — so ingesting them would be a provenance error even if
   permitted.** Plates are hashed, names are *inferred* with a confidence score, reasons are redacted,
   and editorial annotations are injected into data fields (`[HIBF Note: See …]`). Any SIG pipeline
   consuming these would import HIBF's inferences as if they were agency records. **SIG must go to the
   FOIA route HIBF itself uses**, using `/about/open-records-guide` as prior art.
4. **`best_name_confidence` is a probabilistic identity assertion about a named police officer.**
   Combined with F2.8 and F2.15's operator UUIDs, this completes a re-identification chain that SIG
   must refuse to close. REQ-R2-19 applies with full force.
5. **The ±2% HyperLogLog caveat and the 7-month-stale `ca-oos` views mean freshness and precision are
   per-report properties**, not site properties. Any citation must name the report and its
   `refreshedAt`, both of which `/api/reports/counts` exposes.
6. **Two exports are broken** (`immigration-records` truncates mid-stream with an in-band error
   marker; `?format=json` 504s). Any consumer must validate completeness rather than trusting HTTP
   200 — a general lesson for REQ-R2-16's capture pipeline.
7. **Single maintainer, $80/month, two takedown attempts with one pending, hosting under pressure.**
   The ecosystem's most valuable node is also its most fragile; see REQ-R2-33.

### F2.19 — ALPR Watch runs **15 public GitLab repos, a documented REST API, and an open bulk file archive at `/pub/`** — including dated snapshots of every Flock legal document

**Claim:** ALPR Watch is substantially larger than F2.5 recorded, and it publishes the single most
directly reusable artifact found in this pass: an Apache-indexed public file tree.
**Status:** VERIFIED
**Evidence:** `https://gitlab.com/api/v4/groups/alprwatch-org/projects?per_page=100` → **200**,
**15 public projects**, with licences read via `?license=true`:

| Repo | Licence | Last activity |
|---|---|---|
| `alprwatch` | **GPL-2.0+** | 2026-08-06 |
| `deflock-osm` | **GPL-2.0+** | 2026-02-15 |
| `foia` | **GPL-3.0+** | 2026-06-15 |
| `flock-terms-and-conditions` | **GPL-3.0+** | 2026-08-19 |
| `osm-notes`, `city-council-aggregator`, `overpass-server`, `tile-server`, `osm-changeset-bot`, `osm-cleaning`, `suspected-locations`, `map-sync`, `wardriving`, `overpass`, `directions` | **none** (11 repos) | 2025-09-03 → 2026-08-17 |

**A REST API does exist** — correcting F2.5. `https://alprwatch.org/docs` (**200**) is Swagger UI
loading `https://alprwatch.org/api-doc/openapi.json` (**200**, 6,832 B):
`{"info":{"title":"alprwatch-server","version":"0.3.3","license":{"identifier":"GPL-2.0-only"}}}`.
Paths: `POST /api/v1/directions` (*"Obtain directions for cars which avoids areas known to be
surveilled…"*), `GET /api/v1/health`, `GET /api/v1/status`. **It is a routing API, not a data API** —
the bulk data lives in `/pub/`.

**The bulk archive.** `https://alprwatch.org/pub/` → **200**, an Apache directory index with
subtrees: `avoidance/`, `axon/`, `city-council/`, `extract/`, `flock/`, `motorola/`, `muckrock/`,
`suspected-locations/`. Observed contents include `/pub/flock/audit_logs/`, `/pub/flock/admin_area/`,
`/pub/flock/811/`, `flock_search-2025-07-28.csv.bz2`, `flock_utilities_2025-10-06.csv`,
`flock_neighbor.csv`, `flock-managetickets-2025-09-26.tar.bz2`, and
`/pub/muckrock/muckrock-2025-07-25.tar.bz2`.

**`https://alprwatch.org/pub/flock/website/` is a dated mirror of Flock's legal corpus**, with one
directory per document — `api-integration-terms/`, `flock-evidence-policy/`, `lpr-policy/`,
`part91-operational-agreement/`, `privacy-policy/`, `product-specific-terms/`,
`reinstall-fee-schedule/`, `state-required-provisions/`, `terms-and-conditions/`,
`third-party-terms/` — each holding dated HTML captures. `terms-and-conditions/` currently holds
**7 versions**: `2025-10-15`, `2025-12-19`, `2025-12-28`, `2026-02-16`, `2026-02-23`, `2026-08-17`,
`2026-08-18`, plus a `raw/` subdirectory.

**Third-party corroboration of F2.10**, verbatim from
`https://gitlab.com/alprwatch-org/flock-terms-and-conditions/-/raw/master/README.md`:

> "Contracts with Flock Safety reference online terms and conditions which are subject to change
> without notice. **Their website is not available on various archives (e.g. https://archive.org),
> so we fetch copies and look for changes.**"
> "We store a subset of data in `data/` but you can get the full dataset from alprwatch.org:
> `wget -r -np -nH --cut-dirs=3 -P data https://alprwatch.org/pub/flock/website/`"

**Retrieved:** 2026-08-20
**Implication for the spec:**
1. **Q5 is ANSWERED and F2.5 is CORRECTED twice**: there *is* a REST API (narrow, routing-only,
   GPL-2.0-only) and there *is* a bulk export — an openly indexed, `wget -r`-friendly file tree that
   the maintainers explicitly invite mirroring from.
2. **REQ-R2-24 is largely already done by someone else.** ALPR Watch has been diffing Flock's legal
   documents since at least 2025-10-15 and caught two revisions in August 2026 alone
   (`2026-08-17`, `2026-08-18`) — after the 2026-02-16 version this workstream retrieved live. SIG
   should ingest `/pub/flock/website/` rather than build its own legal-document differ, and should
   note that **Flock's terms changed twice in the last four days**, which materially affects any
   analysis pinned to a single version.
3. **Licensing is mixed and mostly absent**: 4 of 15 repos are GPL-2.0+/3.0+, 11 have no licence, and
   **`/pub/` itself carries no stated licence**. The code is copyleft; the data tree is unlicensed.
   Under REQ-R2-18 the `/pub/` contents are reference-only pending a written grant — worth asking
   for, since the README's own `wget -r` instruction signals mirroring is expected.
4. **`wardriving` and `suspected-locations` are a second RF-detection lineage** alongside
   `flock-finder` (F2.14), reinforcing REQ-R2-16's need for a distinct detection-modality class.

**Extended evidence — the `/pub/` inventory, measured.** The GitLab group (`id 111485752`, created
**2025-07-24**, description *"Keeping track of ALPR and related surveillance technologies deployed
worldwide"*) has **zero subgroups**. Note a metadata trap: the group-level
`/projects?license=true` listing returns `license: null` for **all 15** repos; the licences above
were confirmed by listing each repo's root tree and fetching `LICENSE` raw. **Trust the tree, not the
group listing.** Grepping all 13 available `README.md` files for
`licen[cs]e|copyright|odbl|creative commons|attribution|public domain` returned **zero hits** — no
repo documents a *data* licence. `wardriving` is an **empty repository** (`404 Tree Not Found`).

The `/pub/` tree, with verified `Content-Length` values:

| Artifact | Size | Last-Modified |
|---|---|---|
| `/pub/avoidance/alprwatch-avoidance-latest.kmz` | **41,316,293 B** | 2026-08-19 00:02 |
| `/pub/avoidance/alprwatch-avoidance-alpr-suspected-latest.kmz` | ~13 MB | 2026-08-19 00:01 |
| `/pub/flock/flock_utilities_latest.csv` | **42,912,305 B** | 2025-10-06 |
| `/pub/flock/flock_utilities_mini_latest.csv` | **15,977,816 B** | 2025-10-06 |
| `/pub/flock/811.csv` | **38,733,956 B** | 2025-10-01 |
| `/pub/flock/flock_search-2025-07-28.csv.bz2` | **~778 MB** | 2025-07-28 |
| `/pub/muckrock/muckrock-2025-07-25.tar.bz2` | **3,497,339,113 B (3.3 GB)** | 2025-07-25 |
| `/pub/suspected-locations/suspected-locations-microphone-latest.{csv,garmin-poi.csv,geojson}` | 3.9 / 1.7 / 8.2 MB | 2026-08-19 05:21 |

Cadence is **daily**: `/pub/avoidance/` holds **273 dated KMZ builds**
(`alprwatch-avoidance-YYYYMMDDTHHMMSSZ.kmz`, 2026-01-28 → 2026-08-19, ~00:00 UTC), in two variants
(confirmed-ALPR and `-alpr-suspected-`). `/pub/suspected-locations/` holds **97 dated builds** in
three formats each (`.csv`, `.garmin-poi.csv`, `.geojson`), rebuilt every 1–4 days.
`/pub/flock/website/` holds **16** document subdirectories (adding `vendor-baa/`, `vendor-dpa/`,
`vendor-compliance-addendum/`, `vendor-infosec-addendum/`, `trademark-notice/`,
`vulnerability-disclosure-policy/` to those listed above). `/pub/axon/` exists but is **empty**.
`alprwatch.org` has **no `robots.txt` at all** (404) and no `/about`, `/data`, or `/sitemap.xml`.

The `suspected-locations` README states the method, verbatim:
> "A scraper and ETL pipeline for data sources that suggest where ALPR (automated license plate
> readers) may be installed. We collect **811 locate requests, FOIA releases, and public GIS data**
> so that installations can be mapped and shared."

**Two liveness corrections to F2.5 / R1-F1.10:** `https://wiki.alprwatch.org/` returns **HTTP 500**
(*"Fatal exception of type `Wikimedia\Rdbms\DBConnectionError`"* — the MediaWiki database is down),
and the Superset dashboards (`superset.alprwatch.org/.../muckrock-foia/`,
`/.../columbia-river-gorge-foia/`) are still linked from the homepage but rendered **inside `<s>`
strike-through tags** — presented by the operator as retired. F2.5's statement that the Superset
FOIA dashboard "persists" should be read as no longer current.

**Contact:** `https://alprwatch.org/contact` (**200**, 458 B), verbatim and complete: *"You can find
us at: Gitlab [gitlab.com/alprwatch-org] · Email [**alprwatch@proton.me**]"*. Funding: Liberapay,
plus XMR/ETH/BTC addresses.

**Additional implications:**
5. **The OSM attribution gap is a licence hazard SIG must not inherit.** The group runs `deflock-osm`,
   `osm-notes`, `osm-cleaning`, `osm-changeset-bot` and `overpass`, and its avoidance KMZs and
   suspected-location exports are substantially OSM-derived — yet **no ODbL attribution or
   share-alike notice appears anywhere** on the site or in any repo. If SIG ingests `/pub/` it may
   acquire ODbL share-alike obligations that the upstream publisher has not surfaced. Resolve this
   before ingestion, not after.
6. **The `/pub/` cadence is the ecosystem's fastest** (daily, ~00:00 UTC) and its Flock utility CSVs
   are the most stale (frozen since October 2025) — freshness is per-artifact, not per-source, which
   is the same lesson F2.18 teaches about HIBF's reports.
7. **`811 locate requests` are a detection modality no other project uses** — utility-locate filings
   as a leading indicator of *planned* installation. That is pre-deployment evidence, which SIG's
   lifecycle state machine (§29.4) currently has no state for.


### F2.20 — The ALPR Abuse Library publishes a clean JSON export with a genuinely **closed** 10-term controlled vocabulary and a versioned schema — the better model for SIG's category enum

**Claim:** `library.kansas.watch` is a static site over a single published JSON file whose
vocabulary design is stricter, and therefore more useful to SIG, than the Atlas's.
**Status:** VERIFIED
**Evidence:** `https://library.kansas.watch/` → **200**, 33,995 B, `<title>ALPR Abuse Library —
Kansas Watch</title>`. It is a hand-rolled static page (Google Fonts, template-literal rendering,
no framework, no `generator` meta) that fetches **`https://library.kansas.watch/library.json`** →
**200**, **103,666 B**, `application/json`. `/data.json`, `/api/entries`, `/entries.json`,
`/index.json` all **404**. `library.json` is the whole database.

Structure — three top-level keys, `_meta`, `abuse_categories`, `entries`. `_meta` verbatim:

```json
{"description":"ALPR Abuse Library — curated index of news articles documenting ALPR misuse and civil liberties concerns",
 "maintained_by":"Kansas Watch (kansas.watch)",
 "last_updated":"2026-08-15",
 "schema_version":"1.2",
 "submission_form":"https://forms.gle/isGYpLcKu9YeFzSm9",
 "schema_notes":"v1.2 adds a normalized 'state' field (USPS two-letter code, array of codes for multi-state entries, or null for national/non-state-specific entries) alongside the free-text 'jurisdiction' field. jurisdiction remains the human-readable display string; state is for filtering, aggregation, and the state heatmap."}
```

**90 entries**, each with 12 fields: `id, date_published, publication, submission_type, title, url,
jurisdiction, state, agency, abuse_categories, description, status`. Date range **2019-05-22 →
2026-08-13**; `last_updated` 2026-08-15, i.e. **5 days before retrieval — actively maintained.**

**`abuse_categories` is a declared, closed 10-term enumeration** shipped in the file itself:
`false_arrest, stalking_targeting, data_breach, fusion_center_sharing, dragnet_surveillance,
domestic_abuse_enablement, immigration_enforcement, protest_tracking, unauthorized_access, other`.
Observed use (multi-label, 149 assignments over 90 entries): `unauthorized_access` 40,
`stalking_targeting` 28, `dragnet_surveillance` 17, `immigration_enforcement` 14, `other` 14,
`fusion_center_sharing` 12, `false_arrest` 9, `domestic_abuse_enablement` 8, `data_breach` 5,
`protest_tracking` 2.

**`submission_type` is closed, 4 values:** `news_report` 35, `case_study` 28,
`investigative_article` 26, `opinion_piece` 1. **`status`** is `approved` on all 90 — a moderation
field where only approved records are published. `state` is USPS code, an **array** for the 1
multi-state entry, or **null** for 14 national entries; 26 states + national.

**Editorial process:** *"A publicly maintained, editorially reviewed index of news articles
documenting abuses, misuses, and civil liberties concerns related to Automated License Plate
Readers — with a focus on Flock Safety deployments."* Submissions go through a Google Form
(`https://forms.gle/isGYpLcKu9YeFzSm9`) and are published only at `status: approved`.

**Licence: none stated.** The footer says only: *"Kansas Watch — All linked articles remain the
property of their respective publishers."* Contact: `info@kansas.watch`; funding
`https://ko-fi.com/kansaswatch`; parent site `https://kansas.watch`.

**Retrieved:** 2026-08-20
**Implication for the spec:**
1. **This, not the Atlas, is the model for SIG's category enum.** It does the three things the Atlas
   failed to do: the vocabulary is **closed**, it is **shipped inside the data file** so consumers
   need no out-of-band documentation, and the schema is **versioned with a written migration note**
   (`schema_version: 1.2` + `schema_notes`). SIG MUST adopt all three — see REQ-R2-29.
2. **Multi-label categorisation is the right shape.** 149 labels over 90 entries: incidents are not
   mutually exclusive, and forcing a single category would destroy information.
3. **The `jurisdiction` (display) vs `state` (normalized) split, with `null` meaning national and an
   array meaning multi-state**, is a clean, directly copyable pattern for SIG's geography fields —
   and it is the same problem the Atlas solved worse with a pseudo-state code `US`.
4. **`status` as a first-class published field** makes the moderation boundary explicit in the data
   rather than only in the API's `public_scope` metadata.
5. **Small (90 entries) and unlicensed.** Its value to SIG is the *schema*, not the corpus. Reuse of
   the entries is reference-only under REQ-R2-18; the design is free to copy.

**Extended evidence — the source repository, the full schema, and an affirmative anti-reuse signal.**

The site is served from a public GitHub repo discovered via the parent Substack:
**`https://github.com/kansas-watch/alpr-abuse-library`** (API **200**; created 2026-03-13, last push
**2026-08-15**, 2 stars, 0 forks, the org's only repo, description *"Editorially reviewed index of
news articles documenting ALPR abuse and civil liberties concerns"*). Six files: `README.md`,
`index.html` and `library.json` (both **byte-identical to what is served**), `CONTRIBUTING.md`,
`schema.md`, and `validate_library.py`. **No `LICENSE`/`LICENCE`/`COPYING` file; GitHub API
`license: null`.** The parent site `https://kansas.watch/` is a **Substack** newsletter
(`x-served-by: Substack`, `x-sub: kansaswatch`) by **Drew Cranmer**.

**The entry schema is 16 fields, not 12** — `schema.md` documents four optional fields the 90-entry
sample only partly exercises: `submitted_by` (41/90), `date_added` (27/90), `additional_urls`
(25/90), and **`notes` (8/90)**, which `schema.md` describes as *"Editor notes… **Not shown on the
public site**"* — **yet they are present in the public `library.json`.** `status` is documented as
`approved | pending | rejected`, with *"Only `approved` entries render on the public site."*
Schema history: 1.0 → 1.1 (`headline`→`title`, added `submission_type`) → **1.2** (added `state`).
A commit gate is published: `validate_library.py` *"checks required fields, the abuse-category
vocabulary, valid `state` codes, and duplicate entries."*

**Editorial standards, verbatim from `README.md`:**
> "Every entry must link to a **published news article or official document** · Entries are reviewed
> for accuracy, relevance, and source credibility · Opinion pieces may be included if they cite
> documented incidents · **Submissions implicating ongoing legal proceedings are held pending
> resolution** · This library does not publish unverified social media claims"

**Workflow, verbatim from `CONTRIBUTING.md`:** *"This library uses a **form-in, editor-out** workflow.
You do not need a GitHub account to submit an article."* … *"Submissions land in a private review
queue. The editor will: Verify the article exists and the URL is not paywalled · Confirm the article
documents a real incident, not speculation · Check for duplicate entries · Assign or confirm the
abuse category. **Most submissions are reviewed within 7 days.**"* Rejected outright: *"Unverified
social media posts or screenshots · Submissions without a working URL · Opinion pieces that do not
cite a documented incident · Duplicate entries · **Content that targets private individuals not
acting in a public capacity**."* And from `schema.md`: *"**One entry per case, not per article.**"*

The Google Form's three confirmation tickboxes are the **only** submission terms, verbatim:
> "I confirm that all information provided is accurate to the best of my knowledge." ·
> "**I grant permission for this submission to be reviewed and potentially published in the ALPR
> Abuse Library.**" · "I understand that submission does not guarantee publication."

**The decisive licence signal is `robots.txt`** (`https://library.kansas.watch/robots.txt`, **200**,
1,836 B) — a Cloudflare-managed policy asserting an explicit reservation of rights:

```
User-agent: *
Content-Signal: search=yes,ai-train=no,use=reference
Allow: /
```
followed by `Disallow: /` for **Amazonbot, Applebot-Extended, Bytespider, CCBot, ClaudeBot,
CloudflareBrowserRenderingCrawler, Google-Extended, GPTBot, meta-externalagent**, under the preamble:
*"ANY RESTRICTIONS EXPRESSED VIA CONTENT SIGNALS ARE EXPRESS RESERVATIONS OF RIGHTS UNDER ARTICLE 4
OF THE EUROPEAN UNION DIRECTIVE 2019/790…"*

**A published claim not supported by its own data:** the 2026-08-15 Kansas Watch post says the library
holds *"90 documented cases spanning **more than 30 states**."* The JSON yields **26 distinct USPS
codes** plus 14 `null`/national entries.

Contact: `info@kansas.watch`; GitHub Issues; Ko-fi (`ko-fi.com/kansaswatch`); a related civic arm, the
**Sunflower Privacy Alliance**, *"in the process of establishing a proper 501(c)(4)."*

**Additional implications:**
6. **This is the one source whose operator has affirmatively signalled *against* machine reuse.**
   `ai-train=no`, `use=reference`, and an explicit ClaudeBot block are not an absence of permission —
   they are a stated refusal, backed by an EU DSM Article 4 reservation. SIG MUST cite and link this
   source and MUST NOT ingest it, even though `library.json` is trivially fetchable. This is the
   sharpest available test of whether SIG's crawler policy is real.
7. **The `notes` leak is a concrete failure mode to design against.** A field documented as
   editor-only ships in the public artifact. SIG's publication pipeline needs an explicit
   field-level visibility contract enforced at serialization, not a convention.
8. **"One entry per case, not per article" is the record-unit rule SIG needs**, and it matches the
   Atlas's *"the record unit is the underlying event, not the headline"* (F2.16) — two independent
   projects converging on the same answer is strong evidence it is the right one.
9. **"Submissions implicating ongoing legal proceedings are held pending resolution"** is a
   defensible editorial safeguard SIG should adopt for its own contributor intake.
10. **The states discrepancy is a reminder to compute claims from data**, never to restate a
    publisher's summary figure without checking it.


---

## Part 5F — Licence determinations, consolidated (outline Q15)

The five sources the outline left unresolved, plus the ones this pass added. **"Where checked" is the
exact URL that produced the determination.**

| # | Source | Determination | Where checked | Redistribution |
|---|---|---|---|---|
| 1 | **Eyes on Flock** | **CC BY-SA 4.0** (F2.7) | Footer string in `https://eyesonflock.com/assets/index-bsh6x4Ps.js`; links `https://creativecommons.org/licenses/by-sa/4.0/` | **Permitted with attribution + ShareAlike.** No `/license` page exists; confirm data-vs-content scope with the operator. |
| 2 | **Have I Been Flocked** | **NONE — definitively (F2.18).** No licence, copyright line, or reuse grant anywhere; the 6,609-URL sitemap contains no `/license`, `/terms` or `/copyright` route. Bulk CSV exports **do exist** at `/api/reports/{type}/download`, but `robots.txt` **`Disallow: /api/`** + **`Disallow: /*-records`** is an explicit machine-readable refusal covering both the exports and every report page. | `https://haveibeenflocked.com/`, `/about`, `/about/faq`, `/robots.txt`, `/sitemap.xml`, `/api/reports/counts`, `/api/health/minimal` | **Not permitted — reference-only.** Availability ≠ permission. Cite and link; obtain the same facts by FOIA instead. |
| 3 | **Footnote4a** (HIBF's editorial arm) | **CC BY 4.0** — *"Articles are published under CC BY 4.0 unless otherwise noted."* (F2.13) | `https://footnote4a.org/about` | Permitted with attribution. **Covers articles; does not automatically cover HIBF's data.** |
| 4 | **ALPR Watch** | **Mixed (F2.19).** Code: **GPL-2.0+** (`alprwatch`, `deflock-osm`), **GPL-3.0+** (`foia`, `flock-terms-and-conditions`), **none** on the other 11 of 15 repos. Server API declares **GPL-2.0-only**. **The `/pub/` data tree carries no licence.** | `https://gitlab.com/api/v4/groups/alprwatch-org/projects?license=true`; `https://alprwatch.org/api-doc/openapi.json`; `https://alprwatch.org/pub/` | Code copyleft. Data reference-only pending a written grant — though the project's own README instructs `wget -r` mirroring of `/pub/flock/website/`. **Unresolved ODbL risk:** the KMZ and suspected-location exports are OSM-derived but carry no ODbL attribution or share-alike notice anywhere. |
| 5 | **ALPR Accountability Atlas** | **NONE — definitively.** No licence, copyright notice, terms, or attribution statement anywhere; the site has no `<footer>` element at all (F2.16) | Homepage HTML, 5 JS/CSS bundles, README, build script, 4 data files, ZIP interior, HTTP headers, and 404s at `/license`, `/licence`, `/LICENSE`, `/legal`, `/terms`, `/privacy`, `/humans.txt`, `/.well-known/security.txt` | **Not permitted.** Adopt the vocabulary; cite and link; do not mirror the data. |
| 6 | **ALPR Abuse Library** (`library.kansas.watch`) | **NONE stated, plus an affirmative refusal (F2.20).** Footer says only *"All linked articles remain the property of their respective publishers"*; GitHub `license: null`, no LICENSE file; and `robots.txt` asserts **`Content-Signal: ai-train=no, use=reference`** with `Disallow: /` for ClaudeBot/GPTBot/CCBot/Google-Extended under an EU DSM Art. 4 reservation. | `https://library.kansas.watch/` footer; `/library.json` (`_meta` has no licence key); `/robots.txt`; `https://github.com/kansas-watch/alpr-abuse-library` | **Corpus must NOT be ingested — a stated refusal, not merely an absence.** The **schema** — closed 10-term enum, versioned, shipped in-file — is free to copy and is the model SIG should follow. |
| 7 | **`eyes-off/eugene-oregon`** | **CC0-1.0** — *"made available under the Creative Commons Zero license in order to ensure it remains in the public domain"* (F2.11, F2.14) | `FlockAuditLogs/readme.md` + GitHub licence metadata | **Unrestricted.** Best-licensed audit data found. |
| 8 | **`none-below/sm-alpr`** | **AGPL-3.0** (SPDX headers in-source) | `https://github.com/none-below/sm-alpr` | Code copyleft; network use triggers source offer. |
| 9 | **`mcclatchy-southeast/private_eyes`**, **`resistanceisliberty/panopti.ca`**, **`simeononsecurity/flock-finder`**, **`flockhopperdev/FlockHopper`** | **MIT** | GitHub licence metadata, 2026-08-20 | Permitted with attribution. |
| 10 | **`Ringmast4r/FLOCK`** (147 stars) and **`flock.ajith.fyi`** | **NONE** | GitHub API `license: null`; no statement on the site | **Not permitted.** |

**Cross-cutting implication.** SIG will hold, simultaneously, data under **CC BY-SA 4.0** (copyleft),
**CC BY 4.0**, **CC0**, **MIT**, **AGPL-3.0**, and **no licence at all**. These do not compose into a
single redistributable artifact. The spec MUST therefore (a) record licence per source as a required
field, (b) compute the effective licence of every derived artifact, (c) refuse to emit an artifact
whose inputs' licences are incompatible with its declared output licence, and (d) segregate
unlicensed sources into a *reference-only* class that may be cited and linked but never mirrored.

---

## Open questions

*Replaces the previous list. Items 1–7 of the old list are resolved by Part 5; what remains is
carried to the spec risk register (§53).*

1. **Eyes on Flock's ShareAlike scope.** CC BY-SA 4.0 is asserted in a JS bundle footer, not on a
   `/license` page. Whether it is intended to cover the API payload as well as the site presentation
   is unconfirmed. Ask `contact@eyesonflock.com`; until answered, treat the data as BY-SA and plan
   for copyleft.
2. **How Eyes on Flock obtains portal data despite the Cloudflare wall.** Its capture method is
   unstated and its source is closed. If it uses challenge-solving, SIG's consumption of its output
   is still lawful and within REQ-R2-01, but the provenance chain should be documented honestly in
   the source registry rather than left implicit.
3. **The derivation of `estimated_total_cameras` (102,210).** The field is present in the API and
   referenced nowhere in the client. Its methodology is unknown and it MUST NOT be ingested as a
   count claim until it is.
4. **Whether the `/api/audit/{state}/{slug}` endpoint is intended to be public.** It is undocumented
   and unadvertised, though plainly used by the site's own table. SIG should disclose its use in
   outreach rather than rely on it silently.
5. **Whether the 107 single-source portal slugs (F2.13) are real.** Resolving them requires either a
   human check or a third directory.
6. **Operator-UUID governance.** F2.8 and F2.15 both expose un-redacted operator identifiers. SIG
   needs a written policy — proposed in REQ-R2-19 — reviewed by someone other than the ingest author.
7. **The Atlas's stewardship.** No author, organization, funder, or reply-capable contact exists. If
   it disappears there is no one to ask and nothing to fork. SIG should mirror what it may
   (the vocabulary, the schema, the citations) and treat the dataset itself as ephemeral.
8. **Flock's own product line and 2026 corporate events** — covered by workstream R7.
9. **`alpr.wtf` and `dontgetflocked.com`** — confirmed live (200 / 403 Cloudflare) but not profiled.
10. **Whether any ecosystem project holds pre-2025 portal snapshots.** The earliest evidence found is
    the EoF Wayback capture of 2025-07-24 (F2.9) and `private_eyes`' 2024 NC survey. Portal state
    before mid-2024 may be unrecoverable.
11. **ALPR Watch's ODbL position.** Its OSM-derived exports carry no attribution or share-alike
    notice (F2.19). Whether the obligation travels with `/pub/` must be resolved with the operator
    (`alprwatch@proton.me`) before ingestion — see REQ-R2-40.
12. **Whether HIBF would grant SIG an explicit licence.** Its exports are real and its data is the
    richest in the ecosystem, but `robots.txt` refuses automated access and no licence exists. A
    direct request to `humans@haveibeenflocked.com` is the only path from reference-only to
    ingestible, and is worth making early given the source's fragility.
13. **`wiki.alprwatch.org` (HTTP 500, database down) and the two Superset FOIA dashboards (linked but
    struck through as retired)** — content that R1-F1.10 and F2.5 treated as live is not currently
    reachable, and may hold material nothing else preserves.

## Spec requirements emitted

*REQ-R2-01 … REQ-R2-11 are carried forward unchanged in wording, with two amendments recorded by the
completion pass: **REQ-R2-04** is downgraded from a blocking Phase-0 deliverable to an advisory one
by F2.6 (Eyes on Flock's API is open, so ingestion no longer waits on outreach), and **REQ-R2-11**'s
investigation list is superseded by F2.14. REQ-R2-12 onward are new.*

- **REQ-R2-01** — SIG MUST NOT operate a crawler that defeats a bot-management challenge on any
  source, including Flock transparency portals.
- **REQ-R2-02** — Where `robots.txt` cannot be retrieved, the connector MUST treat crawl permission
  as **not granted** and refuse to run.
- **REQ-R2-03** — The Flock portal layer MUST be sourced by partnership, public-records
  acquisition, or human-mediated contributor capture — never by automated challenge-solving.
- **REQ-R2-04** — Eyes on Flock outreach MUST be a Phase 0 blocking deliverable, and the portal
  connector MUST NOT be scheduled before its outcome is recorded in the compact.
- **REQ-R2-05** — Audit-log parsers MUST distinguish `***` redaction from an empty value as
  separate epistemic states.
- **REQ-R2-06** — The portal/public audit parser MUST be schema-discovering and MUST record the
  observed field set per capture as data.
- **REQ-R2-07** — `Camera Count` observed on audit rows MUST be ingested as an independent count
  claim feeding camera-count reconciliation.
- **REQ-R2-08** — `SharedNetworks.csv` MUST be ingested as **configured access**, never as usage,
  with both directions modelled separately and a blank cell recorded as a meaningful negative.
- **REQ-R2-09** — Flock event logs MUST be ingested as **dated lifecycle transitions** and treated
  as the highest-quality transition evidence available for the deployment state machine.
- **REQ-R2-10** — SIG MUST link to HIBF's existing Immigration, 287(g), and Protected Activity
  reports rather than recomputing them.
- **REQ-R2-11** — Footnote4a, flock.ajith.fyi, and the California sharing visualization MUST be
  investigated during Stage 0 and added to the compact.

- **REQ-R2-12** — The Eyes on Flock connector MUST consume `https://eyesonflock.com/api/v1/data` and
  `https://eyesonflock.com/api/audit/{state}/{slug}?download=true` over ordinary HTTP with an
  identifying User-Agent, MUST NOT render the SPA, and MUST NOT poll more often than the payload's
  own `snapshot_date` advances (measured at ~30 days).
- **REQ-R2-13** — Every artifact derived from Eyes on Flock data MUST carry CC BY-SA 4.0 attribution
  and MUST be checked for ShareAlike compatibility before publication.
- **REQ-R2-14** — SIG MUST back-fill the Eyes on Flock portal series from the Internet Archive's 29
  captures of `/api/v1/data` (2025-07-24 → 2026-08-17) rather than requesting history from the
  operator, and MUST handle gzip-encoded `id_` replay bodies and the documented additive schema
  evolution (16 → 18 → 20 portal fields).
- **REQ-R2-15** — REQ-R2-05 is widened: audit parsers MUST treat redaction sentinels as a
  configurable **set** (observed: `***`, `REDACTED`, empty) and MUST raise a flagged event when an
  operator identifier is present un-redacted.
- **REQ-R2-16** — The snapshot layer MUST persist, per source artifact per capture date, four
  co-located files — raw response text (declared source of truth), original HTML, derived normalized
  JSON, and a rendered visual archive — plus content-hash and failure sidecars, following the
  `none-below/sm-alpr` layout. The *format* is adopted; its Playwright/Tor acquisition method is not.
- **REQ-R2-17** — The portal registry MUST be seeded from the union of the Eyes on Flock (950) and
  Footnote4a (877) directories, MUST record per-slug which directories attest to it, and MUST carry
  an `is_agency_deployment` predicate that excludes vendor demo and training portals (`demo`,
  `flock-safety-marketing`, `flock-safety-le-training`, `florida-le-flock-training`).
- **REQ-R2-18** — Source records MUST carry a `licence` field and a dated `access_status` field, and
  the publication pipeline MUST refuse to emit any artifact whose inputs' licences are incompatible
  with its declared output licence. Sources with no stated licence MUST be assigned a
  **reference-only** class: citable and linkable, never mirrored.
- **REQ-R2-19** — Operator identifiers (Flock `userId` / `user_id` UUIDs) MUST be hashed with a
  held-back salt at ingest, MUST NOT be republished in raw form even where a third party has already
  published them, and MUST NOT be joined against any roster or personnel dataset without an explicit
  recorded authorisation.
- **REQ-R2-20** — SIG MUST implement the allegation / reported-incident / audit-finding /
  court-action / policy-decision / company-statement distinction as a **closed enumeration**, paired
  with a free-text `claim_status_detail` column, and MUST carry the Atlas's two orthogonal axes:
  `evidence_strength` (closed, 3-band) and an attribution-confidence axis equivalent to
  `flock_connection`.
- **REQ-R2-21** — The schema MUST support recording the **absence** of a thing as evidence: negative
  portal probes (`flock_status = 404`), and Atlas-style negative-control records ("no issue found for
  this setting"), MUST be storable as dated observations rather than discarded.
- **REQ-R2-22** — Geographic outputs MUST carry a per-record `geocode_precision` string describing the
  centroid level and jitter method applied, and MUST NOT publish exact camera coordinates derived from
  incident records.
- **REQ-R2-23** — `transparency.flocksafety.com` and `www.flocksafety.com` MUST be modelled as
  **separate sources with separate crawl policies**: the former blocked under REQ-R2-01/02, the latter
  crawlable under its permissive `robots.txt` for corporate, product, and legal-document capture.
- **REQ-R2-24** — Flock's dated legal instruments (API and Integrations Terms 2025-10-13, Customer
  Terms and Conditions 2026-02-16, Privacy Policy 2025-08-01) MUST be snapshotted and re-checked on a
  schedule, since Flock revises them and archives prior versions behind a request flow.
- **REQ-R2-25** — No connector may depend on Reddit. Ecosystem discovery MUST run on GitHub/GitLab
  code search, RSS (Footnote4a's six feeds), and web search; any outline citation resting on a Reddit
  permalink MUST be re-sourced to a durable artifact or marked UNVERIFIED.
- **REQ-R2-26** — Because Flock's portals are excluded from the Wayback Machine and expose only a
  ~30-day audit window, SIG MUST treat licence-compliant local mirroring of ecosystem exports as a
  **preservation obligation**, not an optimisation — REQ-R2-10's link-don't-recompute rule governs
  analysis only.
- **REQ-R2-27** — Free-text `reason` fields MUST be retained verbatim alongside any normalization, and
  normalization MUST be case- and abbreviation-aware (observed collisions: `Investigation` /
  `investigation` / `inv` / `invest` / `INV` / `INVEST`; `BOLO` / `bolo`).
- **REQ-R2-28** — Portal `data_retention` MUST be ingested as a per-agency policy variable (observed
  range 7–1,095 days) and `prohibited_uses` MUST be classified as a **policy assertion**, never as
  evidence of conduct.
- **REQ-R2-29** — SIG's category and claim-status enumerations MUST follow the ALPR Abuse Library
  pattern rather than the Atlas's: the vocabulary MUST be **closed**, MUST be **shipped inside every
  published data file** (not only in external documentation), MUST be **multi-label** where incidents
  are not mutually exclusive, and the file MUST carry a `schema_version` plus a written
  `schema_notes` migration statement on every change.
- **REQ-R2-30** — Geography MUST be modelled as a normalized field (USPS code, an array for
  multi-state, `null` for national) **separate from** a human-readable display string, following
  `library.json` v1.2 — never as a pseudo-state code inside the normalized field.
- **REQ-R2-31** — Have I Been Flocked MUST be treated as **reference-only**, and its bulk exports
  MUST NOT be ingested even though they download cleanly: `robots.txt` disallows `/api/` (the export
  endpoints) and `/*-records` (every report page), which is an explicit machine-readable refusal.
  Independently, the exports are *derived* artifacts — hashed plates, inferred `best_name` with a
  confidence score, redacted reasons, and editorial notes injected into data fields — so ingesting
  them would import HIBF's inferences as agency records. Where SIG needs the underlying facts it MUST
  obtain them by public-records request, using `https://haveibeenflocked.com/about/open-records-guide`
  (built from over 500 completed requests) as prior art.
- **REQ-R2-32** — Any statistic cited from HIBF's Orgs, Names, Plates, or Reasons counts MUST carry a
  **±2% HyperLogLog approximation flag**; these MUST NOT be presented as exact counts.
- **REQ-R2-33** — The risk register MUST record **ecosystem continuity risk** with named mitigations:
  the highest-value node (HIBF) is one developer on ~$80/month who has faced two Flock takedown
  attempts, one still pending as of 2026-01-15, with hosting under pressure. SIG's own legal-threat
  posture MUST be designed before publication, not after.
- **REQ-R2-34** — The Flock legal-document watch (REQ-R2-24) SHOULD be satisfied by ingesting
  `https://alprwatch.org/pub/flock/website/` rather than building a new differ; note that Flock's
  Terms and Conditions changed twice within four days of this retrieval (`2026-08-17`, `2026-08-18`),
  so any analysis pinned to a single version MUST record which version it used.
- **REQ-R2-35** — A source that publishes a working bulk export while disallowing it in `robots.txt`
  MUST be classified **reference-only**; the connector MUST NOT treat successful retrieval as
  permission. `Content-Signal: ai-train=no` and AI-crawler `Disallow` blocks MUST be honoured as
  affirmative refusals, not as silence. (Triggering cases: HIBF `/api/`+`/*-records`; ALPR Abuse
  Library `ai-train=no` + ClaudeBot block.)
- **REQ-R2-36** — Ingestion MUST distinguish **derived** from **primary** artifacts and MUST refuse to
  record a derived artifact's inferred fields as source facts. Specifically: hashed identifiers,
  probabilistic name resolutions carrying a confidence score, redaction-processed free text, and
  publisher annotations injected into data fields (e.g. `[HIBF Note: …]`) MUST each be typed as
  derived and carry their producer's provenance.
- **REQ-R2-37** — Download completeness MUST be validated rather than inferred from HTTP 200:
  connectors MUST check for truncation, in-band error markers (observed: a literal
  `# ERROR: download incomplete — please retry` inside a `200 text/csv` body), and declared-vs-actual
  row counts, and MUST fail the capture rather than persist a partial file.
- **REQ-R2-38** — Freshness MUST be modelled **per artifact**, never per source. Observed spreads
  within a single publisher: HIBF report views refreshed the same day while `ca-oos-*` sat 7 months
  stale; ALPR Watch rebuilding avoidance KMZs daily while its Flock utility CSVs were frozen for 10
  months. Where a publisher exposes a freshness endpoint (`/api/reports/counts`, `/api/health/minimal`,
  a payload `snapshot_date`), the connector MUST record it alongside the capture.
- **REQ-R2-39** — Published data files MUST enforce a **field-level visibility contract at
  serialization**. Editor-only or internal fields MUST be stripped by the writer, not by convention:
  the ALPR Abuse Library documents `notes` as *"Not shown on the public site"* yet ships it in the
  public `library.json`.
- **REQ-R2-40** — Before ingesting any OpenStreetMap-derived artifact, SIG MUST resolve its **ODbL
  share-alike position**. ALPR Watch's avoidance KMZs and suspected-location exports are substantially
  OSM-derived but carry no ODbL attribution anywhere, so the obligation may travel with the data
  regardless of the publisher's silence.
- **REQ-R2-41** — The deployment lifecycle state machine MUST include a **pre-deployment** state
  evidenced by utility-locate (811) filings, permits, and procurement records — ALPR Watch's
  `suspected-locations` pipeline demonstrates that planned installations are observable before any
  camera exists, and the current model has no state for this.
- **REQ-R2-42** — The record unit MUST be **one entry per underlying case or event, not per article**,
  with multiple sources attached to a single record. Two independent projects converged on this rule
  (ALPR Abuse Library `schema.md`; Atlas README). Contributor intake SHOULD also adopt the Library's
  safeguard that submissions implicating ongoing legal proceedings are held pending resolution.
- **REQ-R2-43** — SIG MUST NOT restate a publisher's own summary statistic without recomputing it
  from the underlying data. (Observed: the ALPR Abuse Library's *"more than 30 states"* claim against
  26 distinct state codes in `library.json`.)
