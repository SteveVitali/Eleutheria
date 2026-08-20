# R12 — Community, Ecosystem Coordination, and Research-Task Generation

**Workstream:** R12
**Researched:** 2026-08-20
**Researcher:** claude-opus-5 (agent R12)
**Outline sections covered:** §3 (entire), §12 (entire), §15.6, §17 Stage 0, §18, §21 (community/ecosystem entries), §22.6
**Outline questions answered:** Q33, Q34, Q35, Q36, Q37 (Q37 partially — stable-ID scheme cross-references R4/R6)
**Confidence in this file overall:** high

---

## Scope note and method

This workstream was asked to (A) map the real local-group ecosystem, (B) design the Stage 0
ecosystem-coordination protocol, (C) formalize research-task generation, (D) design
contribution-back mechanics, and (E) design contributor experience and governance.

Method: ~120 live retrievals on 2026-08-20 — DNS/WHOIS checks, `curl` with browser UA, the
Wayback CDX and `id_` replay APIs, the GitHub REST API via authenticated `gh`, the MapRoulette
OpenAPI document, the Discourse `.json` API on community.openstreetmap.org, and a full 51-jurisdiction
scrape of MuckRock's state public-records guides. Reddit (`reddit.com/*.json`) refused every
request from this environment and is recorded as INACCESSIBLE below.

Two structural facts dominate everything in this file and should be read first:

1. **The registry the outline builds §3 on is gone.** `flockreporter.org` has no A record today.
2. **A far larger, better-structured registry appeared in its place** — `deflocktheusa.com/chapters/`,
   listing 85 local groups, 79 of which return HTTP 200 right now.

The ecosystem the outline described nine months ago has roughly 6× more local groups than it
recorded, and its named directory has already died once. Both facts point the same direction:
**SIG's most valuable ecosystem function is not ingestion, it is archival insurance and registry
continuity.** That is developed in F12.14–F12.17.

---

# Part A — The ecosystem, verified


### F12.1 — FlockReporter, the directory the outline cites as the ecosystem registry, is offline

**Claim:** `flockreporter.org` no longer resolves to an IP address; the site the outline names as
the canonical local-group directory is dead as of 2026-08-20, and survives only in the Wayback
Machine's 2026-07-28 capture.

**Status:** VERIFIED

**Evidence:**
- `dig flockreporter.org A` → **no A record**. `dig NS` → `owen.ns.cloudflare.com.`,
  `tiffany.ns.cloudflare.com.` The domain is still registered and still delegated to Cloudflare,
  but publishes no address record. `curl https://flockreporter.org/` → `curl: (6) Could not resolve host`.
  WebFetch → `getaddrinfo ENOTFOUND flockreporter.org`.
- Wayback CDX (`http://web.archive.org/cdx/search/cdx?url=flockreporter.org*&output=json`) returns
  exactly **7 captured URLs**, all timestamped `20260728225506`–`20260728225519`:
  `/`, `/1.png`, `/32x32.png`, `/5.jpg`, `/6.jpg`, `/7.png`, `/tos.html`. There is no earlier capture
  in the index and no capture after 2026-07-28.
- The archived page (`https://web.archive.org/web/20260728225506id_/https://flockreporter.org/`,
  68,799 bytes) contains the full directory reproduced in F12.2, plus site-level statistics
  ("786 Total transparency portals found across departments", "24,133 Cameras reported in these
  portals", "185 million Vehicles tracked in our dataset", "171,013 License plate searches performed",
  "2.3% Hotlist hit rate") and a section titled "Flock tried to silence this information" describing
  December 2025 takedown notices filed by Cyble Inc. on Flock Safety's behalf against transparency sites.
- Contact channels the archived page advertised: Discord `https://discord.gg/m9VsbR6d5z` and
  Matrix `https://matrix.to/#/#deflock:flockreporter.org`. **The Matrix room ID is homeserver-scoped to
  the dead domain and is therefore also unresolvable.**

**Retrieved:** 2026-08-20

**Implication for the spec:** Every external registry SIG depends on must be mirrored at ingestion
time, content-addressed, and re-fetched on a cadence with a `source_reachable` health flag. A single
Wayback capture with seven URLs is all that stands between the ecosystem and total loss of this
registry. SIG must treat "mirror the collaborator" as a first-class, contractual deliverable, not a
side effect (see the succession clause in F12.15).

**Outline delta:** **CONTRADICTS §3 and §21** — the outline states "FlockReporter maintains a directory
of multiple such efforts" and lists `https://flockreporter.org/` in the priority source registry under
"Community ecosystem." That source is dead. It also **CORRECTS §3**: the outline's premise that
FlockReporter is the ecosystem's directory is now false; see F12.2.

---

### F12.2 — The archived FlockReporter directory listed 13 groups; the outline's §3 list is 80% accurate but stale

**Claim:** The 2026-07-28 FlockReporter capture listed 13 local groups plus 4 national tools; of the
13 groups the outline names in §3, one (DeFlock Idaho) was never in the directory, one (Eyes Off
Cedar Rapids) was not in the capture, and one (Live Free VA) has since renamed and redirects.

**Status:** VERIFIED

**Evidence:** Anchor extraction from the archived HTML yielded exactly these group entries:
DeFlock Atlanta (`deflockatlanta.org`, Atlanta GA), DeFlock Birmingham (`deflockbhm.com`, Birmingham AL),
DeFlock Joplin (`deflockjoplin.today`, Joplin MO), DeFlock Lynnwood (`deflocklynnwood.com`, Lynnwood WA),
DeFlock Olympia (`deflockoly.noblogs.org`, Olympia WA), DeFlock Redmond
(`bsky.app/profile/deflock-redmond.bsky.social`, Redmond WA — **a Bluesky profile, not a website**),
DeFlock Tucson (`deflocktucson.com`, Tucson AZ), Eyes Off Colorado (`eyesoffcolorado.org`, Golden CO),
Eyes Off Indiana (`eyesoffindiana.org`, Indianapolis IN), Live Free VA (`livefreeva.org`, Staunton VA),
deflock.vegas (Las Vegas NV) — plus the tools Have I Been Flocked, DeFlock map, **ALPR Pictures
(`alpr.pictures`)**, and Eyes On Flock.
- `https://livefreeva.org/` returns **200 but redirects to `https://www.deflockthevalley.com/`**
  (verified by `curl -w '%{url_effective}'`). Page email: `deflockthevalley@gmail.com`.
- `deflockidaho.org` and `eyesoffcedarrapids.org` → `curl (6) Could not resolve host`. Eyes Off
  Cedar Rapids does exist at **`https://eyesoffcr.org/`** (403 Cloudflare challenge, i.e. live).
  DeFlock Idaho exists as an organizing entity — it filed tort claims against Caldwell and Wilder, ID
  over SB 1180 (Idaho Capital Sun, `https://idahocapitalsun.com/2026/08/06/all-eyes-on-flock-idaho-navigates-surveillance-technology/`)
  — but has **no verifiable independent web presence**; it is not listed in either directory.

**Retrieved:** 2026-08-20

**Implication for the spec:** Local-group identity cannot be keyed on domain. Groups rename
(`livefreeva.org` → `deflockthevalley.com`), live only on social platforms (DeFlock Redmond is a
Bluesky handle), or exist only as legal actors with no site (DeFlock Idaho). The `Organization` node
for a civil-society group needs the same alias/lifecycle machinery §8.1 gives agencies, plus a
`primary_presence_type` ∈ {website, social_profile, subreddit, linktree, none}.

**Outline delta:** **CORRECTS §3** — Live Free VA is now DeFlock the Valley; DeFlock Redmond has no
site; DeFlock Idaho is unverifiable as a publishing group; Eyes Off Cedar Rapids is at `eyesoffcr.org`.
**EXTENDS §3** — adds ALPR Pictures, a CC BY 4.0 photographic evidence source the outline never names (F12.5).

---

### F12.3 — The real ecosystem registry today is `deflocktheusa.com/chapters/`, listing 85 groups

**Claim:** An independent publisher, DeFlock The USA, maintains a national chapter directory of 85
local groups across 50 states plus DC and 4 territories; 79 return HTTP 200, 5 return Cloudflare 403
(live but bot-challenged), 1 is a login-walled Facebook page. This is the most complete public
directory of U.S. ALPR-accountability groups that exists.

**Status:** VERIFIED

**Evidence:** `https://deflocktheusa.com/chapters/` (HTTP 200, 132,953 bytes) — 119 filter chips
totalling all states/territories, and exactly 85 `<a class="tool-card chapter-card">` elements
parsed. Each carries `href`, `data-state`, `tool-type` (status), `tool-name`, `chapter-area`,
`tool-desc`. Full liveness sweep of all 85 URLs on 2026-08-20 (recorded in the table below):
79× 200, 5× 403 (deflocknorfolk.org, deflockchatt.org, eyesoffcr.org, deflockjoplin.today,
uaalpr.org, 14850.com — all Cloudflare challenges, sites confirmed to exist), 1× 400
(facebook.com/UpstateFoodNotBombs). Terms of Use (`https://deflocktheusa.com/terms/`, "Last updated:
July 10, 2026") states: *"The chapters listed in our directory are independent local groups. We
amplify their work; we do not run them, and they do not speak for us."*

**Retrieved:** 2026-08-20

**Implication for the spec:** This is the registry SIG should ingest for Layer-"H" (civil society).
It is HTML-only — no API, no export — so it needs a scraper with a stable card selector, a
per-chapter `last_seen` timestamp, and a churn detector (see task type T22, *organizational
disappearance*). It is also a **single point of failure run by one publisher** and must be mirrored.

**Outline delta:** **EXTENDS §3 massively** — the outline records 13 local groups plus a
generic "local county/city privacy organizations". The verified count is 85 named groups with URLs
plus 2 national campaigns. **EXTENDS §18** — the "Local DeFlock/Eyes Off groups" row of §18's
interaction table should be split into a real registry with per-group terms.

---

### F12.4 — Verified local-group directory (85 groups, checked 2026-08-20)

**Claim:** The following is the verified public directory of U.S. local ALPR-accountability groups.

**Status:** VERIFIED (liveness), PARTIALLY VERIFIED (descriptions are the directory's own text, not
independently confirmed for each group)

**Evidence:** `https://deflocktheusa.com/chapters/` parsed 2026-08-20; HTTP status column is this
agent's own `curl -L -A <browser UA> -m 18` sweep on 2026-08-20.

**Retrieved:** 2026-08-20

| # | Group | Jurisdiction | Dir. status | URL (as listed) | HTTP 2026-08-20 | Resolved URL if different | What it does |
|---|---|---|---|---|---|---|---|
| 1 | DeFlock Atlanta | Atlanta & North Georgia | Active | `https://deflockatlanta.org/` | 200 | — | Grassroots education and organizing across metro Atlanta — FOIA requests for North Georgia, camera identification guides, and community meetings. |
| 2 | DeFlock Wylie | Wylie, Texas | Active | `https://deflock-wylie.com/` | 200 | — | Resident-led, nonpartisan campaign digging into the city’s own audit logs and records to end Wylie’s Flock contract. |
| 3 | DeFlock Tucson | Tucson & Pima County, Arizona | Active | `https://deflocktucson.com/` | 200 | — | A coalition born at the University of Arizona after 62 cameras appeared on campus — now fighting surveillance across Pima County. |
| 4 | DeFlock Birmingham | Birmingham, Alabama | Active | `https://deflockbhm.com/` | 200 | — | “We’re Flocked” — mapping and challenging the camera network across the Magic City. |
| 5 | DeFlock STL | St. Louis, Missouri | Active | `https://deflockstl.com/` | 200 | — | Protecting privacy in the St. Louis area — pressing elected officials to pull the plug on plate readers. |
| 6 | DeFlock Dane | Dane County, Wisconsin | Active | `https://deflockdane.org/` | 200 | — | Maps ALPRs across Dane County, files open-records requests on vendor contracts, and publishes everything they find. |
| 7 | DeFlock SF | San Francisco, California | Active | `https://deflocksf.org/` | 200 | — | Fighting the dragnet in the city where police were caught illegally sharing plate data with federal agencies. |
| 8 | DeFlock OKC | Oklahoma City, Oklahoma | Active | `https://deflockokc.com/` | 200 | — | Working to end mass surveillance in Oklahoma City, camera by camera. |
| 9 | DeFlock Norfolk | Norfolk, Virginia | Active | `https://deflocknorfolk.org/` | 403 (Cloudflare bot challenge; site exists) | — | Organizing in the city where a judge called warrantless Flock tracking a Fourth Amendment search — ground zero of the federal lawsuit. |
| 10 | DeFlock Chatt | Chattanooga, Tennessee | Active | `https://deflockchatt.org/` | 403 (Cloudflare bot challenge; site exists) | — | Surveillance watch for the Chattanooga region. |
| 11 | DeFlock El Paso | El Paso, Texas | Active | `https://deflockelpaso.org/` | 200 | — | The contract got renewed; the fight continues. Border-city organizing where ALPR data and immigration enforcement collide. |
| 12 | Pasadena Privacy (DeFlock Pasadena) | Pasadena, California | Active | `https://deflockpasadena.org/` | 200 | `https://pasadenaprivacy.org/` | Neighborhood-level privacy organizing in the San Gabriel Valley. |
| 13 | DeFlock Burbank | Burbank, California | Active | `https://deflockburbank.org/` | 200 | `https://www.deflockburbank.org/` | Community privacy campaign taking the camera question to Burbank city hall. |
| 14 | DeFlock Monterey | Monterey County, California | Active | `https://deflockmonterey.com/` | 200 | — | Mapping license plate surveillance across Monterey County. |
| 15 | DeFlock Ventura | Ventura County, California | Active | `https://deflockventura.com/` | 200 | — | Ventura County residents pushing back on automated plate readers. |
| 16 | DeFlock Nevada County | Nevada County, California | Active | `https://deflocknc.com/` | 200 | — | “Who is watching?” — rural Sierra foothills residents asking the question their supervisors didn’t. |
| 17 | DeFlock Florida | Statewide, Florida | Active | `https://deflockflorida.com/` | 200 | — | Statewide network tracking Flock deployments across Florida. |
| 18 | DeFlock Georgia | Statewide, Georgia | Active | `https://deflockgeorgia.org/` | 200 | — | Statewide organizing beyond metro Atlanta. |
| 19 | DeFlock DFW | Dallas–Fort Worth, Texas | Organizing | `https://deflockdfw.com/` | 200 | `https://www.deflockdfw.org/` | Metroplex chapter spinning up now — site coming soon. |
| 20 | DeFlock Knoxville | Knoxville, Tennessee | Organizing | `https://deflockknox.com/` | 200 | — | East Tennessee chapter spinning up now — site coming soon. |
| 21 | DeFlock Grand Rapids | Grand Rapids, Michigan | Active | `https://deflockgrandrapids.com/` | 200 | `https://eyesoffgrandrapids.com/` | Working to keep mass surveillance out of Grand Rapids. |
| 22 | DeFlock Illinois | Statewide, Illinois | Active | `https://deflockillinois.com/` | 200 | — | Statewide campaign to stop mass license-plate surveillance across Illinois. |
| 23 | Eyes Off Indiana | Statewide, Indiana | Active | `https://eyesoffindiana.org/` | 200 | — | Indiana’s statewide campaign for clear, enforceable limits on law-enforcement license-plate readers — mapping the state’s ALPR cameras, gathering a public petition, and pressing legislators for privacy-protective standards. Nonpartisan. |
| 24 | Live Free AZ | Arizona | Active | `https://livefreeaz.com/` | 200 | — | Independently run local group listed on the DeFlock project directory (deflock.org). |
| 25 | DeFlock Corona | Corona, California | Active | `https://deflock-corona.org/` | 200 | — | Independently run local group listed on the DeFlock project directory (deflock.org). |
| 26 | DeFlock Elk Grove | Elk Grove, California | Active | `https://deflockelkgrove.org/` | 200 | — | Independently run local group listed on the DeFlock project directory (deflock.org). |
| 27 | DeFlock Rancho Cordova | Rancho Cordova, California | Active | `https://deflockranchocordova.org/` | 200 | — | Independently run local group listed on the DeFlock project directory (deflock.org). |
| 28 | DeFlock Vallejo | Vallejo, California | Active | `https://deflockvallejo.org/` | 200 | — | Independently run local group listed on the DeFlock project directory (deflock.org). |
| 29 | DeFlock Woodland | Woodland, California | Active | `https://deflockwoodland.org/` | 200 | — | Independently run local group listed on the DeFlock project directory (deflock.org). |
| 30 | DeFlock Yuba-Sutter | Yuba-Sutter County, California | Active | `https://deflock-yuba-sutter.org/` | 200 | — | Independently run local group listed on the DeFlock project directory (deflock.org). |
| 31 | Eyes Off Colorado | Golden, Colorado | Active | `https://www.eyesoffcolorado.org/` | 200 | — | Independently run local group listed on the DeFlock project directory (deflock.org). |
| 32 | NoCo Privacy | Colorado | Active | `https://nocoprivacy.org/` | 200 | — | Independently run local group listed on the DeFlock project directory (deflock.org). |
| 33 | DeFlock CT | Connecticut | Active | `https://www.reddit.com/r/deflock_CT/` | 200 | — | Independently run local group listed on the DeFlock project directory (deflock.org). |
| 34 | DeFlock D.C. | Washington, District Of Columbia | Active | `https://www.instagram.com/deflockdc` | 200 | — | Independently run local group listed on the DeFlock project directory (deflock.org). |
| 35 | FLDR Brevard | Brevard County, Florida | Active | `https://www.fldigitalrights.org/brevard/` | 200 | — | Independently run local group listed on the DeFlock project directory (deflock.org). |
| 36 | FLDR Broward | Broward County, Florida | Active | `https://www.fldigitalrights.org/broward` | 200 | — | Independently run local group listed on the DeFlock project directory (deflock.org). |
| 37 | FLDR Jacksonville | Jacksonville, Florida | Active | `https://www.fldigitalrights.org/jacksonville/` | 200 | — | Independently run local group listed on the DeFlock project directory (deflock.org). |
| 38 | FLDR Tampa Bay | Tampa Bay, Florida | Active | `https://www.fldigitalrights.org/tampabay/` | 200 | — | Independently run local group listed on the DeFlock project directory (deflock.org). |
| 39 | Florida Digital Rights Association | Florida | Active | `https://www.fldigitalrights.org/` | 200 | — | Independently run local group listed on the DeFlock project directory (deflock.org). |
| 40 | Miami Tech Enthusiast Club | Miami, Florida | Active | `https://www.miamitech.club/` | 200 | — | Independently run local group listed on the DeFlock project directory (deflock.org). |
| 41 | KSU ALPRs | Kennesaw, Georgia | Active | `https://ksualprs.com/` | 200 | — | Independently run local group listed on the DeFlock project directory (deflock.org). |
| 42 | Northern Georgia CAN | Woodstock, Georgia | Active | `https://www.ngacan.org/` | 200 | — | Independently run local group listed on the DeFlock project directory (deflock.org). |
| 43 | Eyes Off Cedar Rapids | Cedar Rapids, Iowa | Active | `https://eyesoffcr.org/` | 403 (Cloudflare bot challenge; site exists) | — | Independently run local group listed on the DeFlock project directory (deflock.org). |
| 44 | DeFlock Sterling | Sterling, Illinois | Active | `https://deflock-sterling.org/` | 200 | — | Independently run local group listed on the DeFlock project directory (deflock.org). |
| 45 | Get the Flock Out Indivisible HP | Highland Park, Illinois | Active | `https://www.indivisiblehp.com/home` | 200 | — | Independently run local group listed on the DeFlock project directory (deflock.org). |
| 46 | Get the Flock Out Quad Cities | Moline, Illinois | Active | `https://gettheflockoutqc.com/` | 200 | — | Independently run local group listed on the DeFlock project directory (deflock.org). |
| 47 | Shut The Flock Off BloNo | Bloomington-Normal, Illinois | Active | `https://linktr.ee/shuttheflockoffblonomc` | 200 | — | Independently run local group listed on the DeFlock project directory (deflock.org). |
| 48 | StopFlock CU | Urbana-Champaign, Illinois | Active | `https://stopflock.org/` | 200 | — | Independently run local group listed on the DeFlock project directory (deflock.org). |
| 49 | Flock Out of SW IN | Evansville, Indiana | Active | `https://linktr.ee/flockoutofswin` | 200 | — | Independently run local group listed on the DeFlock project directory (deflock.org). |
| 50 | Sunflower Privacy Alliance | Wichita, Kansas | Active | `https://privacyks.org/` | 200 | — | Independently run local group listed on the DeFlock project directory (deflock.org). |
| 51 | Get the Flock Out of Central Louisiana | Louisiana | Active | `https://get-the-flock-out-of-central-louisiana.org/` | 200 | — | Independently run local group listed on the DeFlock project directory (deflock.org). |
| 52 | No Flock NO | New Orleans, Louisiana | Active | `https://no-flock-no.com/` | 200 | — | Independently run local group listed on the DeFlock project directory (deflock.org). |
| 53 | Minnesota Privacy Project | Minnesota | Active | `https://www.mnprivacy.org/` | 200 | — | Independently run local group listed on the DeFlock project directory (deflock.org). |
| 54 | DeFlock Joplin | Joplin, Missouri | Active | `https://deflockjoplin.today/` | 403 (Cloudflare bot challenge; site exists) | — | Independently run local group listed on the DeFlock project directory (deflock.org). |
| 55 | DeFlock U City | University City, Missouri | Active | `https://www.deflockucity.com/` | 200 | — | Independently run local group listed on the DeFlock project directory (deflock.org). |
| 56 | Flock Out SGF | Springfield, Missouri | Active | `https://flockoutsgf.com/` | 200 | — | Independently run local group listed on the DeFlock project directory (deflock.org). |
| 57 | DeFlock North Carolina | North Carolina | Active | `https://www.deflocknc.org/` | 200 | — | Independently run local group listed on the DeFlock project directory (deflock.org). |
| 58 | DeFlock Wilmington | Wilmington, North Carolina | Active | `https://deflockilm.org/` | 200 | — | Independently run local group listed on the DeFlock project directory (deflock.org). |
| 59 | DeFlock Vegas | Las Vegas, Nevada | Active | `https://www.deflock.vegas/` | 200 | — | Independently run local group listed on the DeFlock project directory (deflock.org). |
| 60 | DeFlock Lakewood | Lakewood, Ohio | Active | `https://deflocklakewood.org/` | 200 | — | Independently run local group listed on the DeFlock project directory (deflock.org). |
| 61 | Flock No Cleveland | Cleveland, Ohio | Active | `https://www.flocknocle.com/` | 200 | — | Independently run local group listed on the DeFlock project directory (deflock.org). |
| 62 | UA Transparency | Upper Arlington, Ohio | Active | `https://www.uaalpr.org/` | 403 (Cloudflare bot challenge; site exists) | — | Independently run local group listed on the DeFlock project directory (deflock.org). |
| 63 | DeFlock GSP | Greenville, South Carolina | Active | `https://eyesoffgsp.org/` | 200 | — | Independently run local group listed on the DeFlock project directory (deflock.org). |
| 64 | DeFlock South Carolina | South Carolina | Active | `https://deflocksc.org/` | 200 | — | Independently run local group listed on the DeFlock project directory (deflock.org). |
| 65 | Maryville Privacy | Maryville, Tennessee | Active | `https://www.maryvilleprivacy.org/` | 200 | — | Independently run local group listed on the DeFlock project directory (deflock.org). |
| 66 | Nash Community Safety Network | Nashville, Tennessee | Active | `https://www.instagram.com/nashcommunitysafetynetwork_` | 200 | — | Independently run local group listed on the DeFlock project directory (deflock.org). |
| 67 | DeFlock BCS | Bryan/College Station, Texas | Active | `https://www.deflockbcs.com/` | 200 | — | Independently run local group listed on the DeFlock project directory (deflock.org). |
| 68 | DeFlock Carrollton | Carrollton, Texas | Active | `https://www.deflockcarrolltontx.org/` | 200 | — | Independently run local group listed on the DeFlock project directory (deflock.org). |
| 69 | DeFlock Temple | Temple, Texas | Active | `https://deflocktemple.com/` | 200 | — | Independently run local group listed on the DeFlock project directory (deflock.org). |
| 70 | No ALPRs TX | Austin, Texas | Active | `https://www.noalprs.org/` | 200 | — | Independently run local group listed on the DeFlock project directory (deflock.org). |
| 71 | DeFlock Chesterfield | Chesterfield, Virginia | Active | `https://deflockchesterfieldva.wordpress.com/` | 200 | — | Independently run local group listed on the DeFlock project directory (deflock.org). |
| 72 | DeFlock Fairfax | Fairfax, Virginia | Active | `https://deflockfairfax.com/` | 200 | — | Independently run local group listed on the DeFlock project directory (deflock.org). |
| 73 | DeFlock Harrisonburg | Harrisonburg, Virginia | Active | `https://deflockhburg.org/` | 200 | — | Independently run local group listed on the DeFlock project directory (deflock.org). |
| 74 | DeFlock Loudoun | Loudoun County, Virginia | Active | `https://deflockloudoun.crd.co/` | 200 | — | Independently run local group listed on the DeFlock project directory (deflock.org). |
| 75 | DeFlock Williamsburg | Williamsburg, Virginia | Active | `https://deflockwilliamsburg.com/` | 200 | — | Independently run local group listed on the DeFlock project directory (deflock.org). |
| 76 | DeFlock the Valley | Shenandoah Valley, Virginia | Active | `https://deflockthevalley.com/` | 200 | — | Independently run local group listed on the DeFlock project directory (deflock.org). |
| 77 | Live Free VA | Staunton, Virginia | Active | `https://livefreeva.org/` | 200 | `https://www.deflockthevalley.com/` | Independently run local group listed on the DeFlock project directory (deflock.org). |
| 78 | Richmond DSA | Richmond, Virginia | Active | `https://www.dsarichmond.org/initiative/block-flock/` | 200 | — | Independently run local group listed on the DeFlock project directory (deflock.org). |
| 79 | DeFlock Lynnwood | Lynnwood, Washington | Active | `https://deflocklynnwood.com/` | 200 | — | Independently run local group listed on the DeFlock project directory (deflock.org). |
| 80 | DeFlock Olympia | Olympia, Washington | Active | `https://deflockoly.noblogs.org/` | 200 | — | Independently run local group listed on the DeFlock project directory (deflock.org). |
| 81 | DeFlock Redmond | Redmond, Washington | Active | `https://bsky.app/profile/deflock-redmond.bsky.social` | 200 | — | Independently run local group listed on the DeFlock project directory (deflock.org). |
| 82 | IRTF Cleveland | Cleveland, Ohio | Active | `https://www.irtfcleveland.org/` | 200 | — | Independently run local group listed on the DeFlock project directory (deflock.org). |
| 83 | Shake Off Flock | Cleveland, Ohio | Active | `https://sites.google.com/view/shakeoffflock` | 200 | — | Independently run local group listed on the DeFlock project directory (deflock.org). |
| 84 | Upstate Food Not Bombs | Greenville, South Carolina | Active | `https://www.facebook.com/UpstateFoodNotBombs/` | 400 (login-walled platform) | — | Independently run local group listed on the DeFlock project directory (deflock.org). |
| 85 | Stop Flock in Woodstock | Woodstock, Illinois | Active | `http://stopflockinwoodstock.org/` | 200 | `https://www.stopflockinwoodstock.org/` | Independently run local group listed on the DeFlock project directory (deflock.org). |

**Additional groups found outside the directory** (GitHub search, 2026-08-20, via authenticated `gh api`):

| Group | Jurisdiction | Evidence URL | Why it matters to SIG |
|---|---|---|---|
| DeFlock Boone County | Boone County, IL | `https://github.com/yung-megafone/DeFlock_Boone_County` | "Open-source repository of FOIA requests, responsive records, policy analysis, and findings" — a local group publishing **primary records in git**. |
| DeFlock North Canton | North Canton, OH | `https://github.com/deflocknorthcanton/deflocknorthcanton-site` | Not in the deflocktheusa directory. Site + public records in git. |
| DeFlock Chattanooga | Chattanooga, TN | `https://github.com/chattaccountability/deflockchatt` | "Source and data … Built from open records requests. Part of the Chattanooga Civic Accountability Project." Repo is the data substrate behind the (403-walled) site. |
| FLOCK Resistance | Oconee County, SC | `https://github.com/NoLabelSecurity/FLOCK-Resistance` | "interactive ALPR camera database, FOIA document archive, legislative monitoring". Not in the directory. |
| FlockWatch data | national | `https://github.com/rhowardstone/flockwatch-data` | "99.4M deduplicated ALPR search records released by US law enforcement under public-records law, with full FOIA provenance" — updated 2026-08-20. |
| panopti.ca | Canada | `https://github.com/resistanceisliberty/panopti.ca` | MIT-licensed Canadian DeFlock fork; its maintainer is the one implementing the plausibility warnings recorded in F12.28. |
| The News & Observer `private_eyes` | NC | `https://github.com/mcclatchy-southeast/private_eyes` | MIT-licensed newsroom repo: "Code and data powering The News & Observer's reporting on the growth of ALPRs and Flock Safety." Model for the newsroom interface (F12.12). |

**Implication for the spec:** A material fraction of local groups publish their primary records
**in public git repositories**, not on their websites. The ingestion connector inventory must include
a *GitHub org/repo* connector for civil-society sources, keyed on repo + path + commit SHA. Commit
SHAs are natural content-addressed evidence identifiers and give free bitemporal history — this is
the cheapest high-fidelity local-evidence channel in the whole ecosystem and the outline does not
mention it.

**Outline delta:** **EXTENDS §3, §10 Phase 1F, and §21** — adds a GitHub-hosted local-records layer.

---

### F12.5 — Local and adjacent projects with explicit, machine-usable licences

**Claim:** Three ecosystem projects publish explicit reuse terms; the rest do not, and the difference
determines what SIG may redistribute.

**Status:** VERIFIED

**Evidence:**
- **ALPR Pictures** (`https://alpr.pictures/`, 403 live / read via
  `https://web.archive.org/web/2026/https://alpr.pictures/`): *"© 2025. All work on this site is
  openly licensed via CC BY 4.0."* Also: *"All Pictures are taken from public property, unless
  otherwise noted. Images edited to remove people and licence plates."* and *"Pictures are linked on
  Deflock … click 'view on OSM', then click the link under 'image'."* — i.e. the photos are already
  joined to OSM node IDs. **This is a ready-to-ingest, redistributable field-evidence corpus.**
- **DeFlock** (`https://github.com/FoggedLens/deflock` via `gh api`): licence **MIT**, homepage
  `https://deflock.org`, 937 stars, 27 open issues, `has_issues: true`, `pushed_at 2026-08-09`,
  `archived: false`. MIT covers the *code*; the *data* lives in OSM under ODbL.
- **ALPR Watch** (`https://gitlab.com/alprwatch-org/alprwatch`): **GNU GPL v2.0 or later**, has
  `CONTRIBUTING`, created 2025-09-05, 34 commits.
- **DeFlock The USA** (`https://deflocktheusa.com/terms/`): *"Our original reporting, commentary,
  page text, database enrichments, graphics, and site design are owned by DeFlock The USA … You may
  quote brief excerpts with credit and a link back … Any other reproduction requires our permission."*
  Camera locations: *"originate from OpenStreetMap volunteers as curated by the DeFlock project, and
  are available under the Open Database License (ODbL), © OpenStreetMap contributors. We enrich that
  data with our own research, such as operator names, dates, and addresses."*
  → **Their chapter directory and cancellation tracker are all-rights-reserved. SIG may link and
  quote briefly but may NOT redistribute them without written permission.** This is precisely the
  "ask, don't scrape" case the Stage 0 outreach template must handle.
- **EFF Atlas of Surveillance**: site footer on every page reads **`CC-by`**
  (`https://www.atlasofsurveillance.org/about`, `/collaborate`).
- **ALPR Abuse Library / Kansas Watch** (`https://library.kansas.watch/`): *"All linked articles
  remain the property of their respective publishers."* — an index, not a corpus; footer exposes a
  `JSON` link and a `Submit` form.
- Every other local group site checked (Atlanta, Birmingham, Lynnwood, Olympia, Tucson, Vegas,
  Colorado, Indiana, Dane) publishes **no licence statement of any kind**.

**Retrieved:** 2026-08-20

**Implication for the spec:** Default posture for local-group content is **link-and-cite, do not
redistribute**, with an explicit permission upgrade path. The collaboration ledger (F12.18) must
carry a per-source `license` field whose default value is `unspecified-all-rights-reserved`, and the
pipeline must refuse to emit unlicensed third-party prose into public exports.

**Outline delta:** **EXTENDS §21 / Rule 4 of CONVENTIONS** — the outline treats licensing as a
question for the big datasets; it is *more* acute for the small ones, because they have no terms at all.

---

### F12.6 — Local groups already publish exactly the structured claims SIG's reconciliation engine needs

**Claim:** Several chapters publish per-jurisdiction camera counts, retention values, sharing-network
exports, and contract-lifecycle events in structured or semi-structured form — the same fields §11
tells SIG to reconcile.

**Status:** VERIFIED

**Evidence:**
- **Eyes Off Colorado** (`https://www.eyesoffcolorado.org/`, HTTP 200): publishes *"Surveillance
  Report Cards"* scoring cities 0–100 with two SIG-native fields per city: **ALPR camera count** and
  **data retention**. Verbatim rows captured: Firestone (Weld Cty) C 52/100, cameras "Unknown",
  retention "Unknown"; Boulder D 48/100, 30 cameras, 30 days; Greeley F 19/100, 14 cameras, 30 days;
  Castle Rock D 32/100, 32 cameras, **365 days**; Avon F 11/100, 8 cameras, 30 days; Windsor D 42/100,
  14 cameras, 30 days; Arvada D 45/100, 40 cameras, 30 days; Golden F 7/100, 25 cameras, **365 days**;
  Longmont C 56/100, 15 cameras, 30 days; Denver C 65/100, 113 cameras, 30 days. The page also
  carries a scraped block of **council-member email addresses** for Greeley, Denver, Longmont, Golden.
- **DeFlock Dane** (`https://deflockdane.org/`, HTTP 200): navigation exposes `/alpr-map-dane-county/`,
  `/dane-county-row-permits/` (**right-of-way permits — a physical-deployment evidence source nobody
  else in the ecosystem uses**), `/wisdot-alpr-map/`, `/shared-networks/`, `/records-requests/`,
  `/request-tracker/`, `/reading-room/`, `/wisconsin-axon-contract/`, and a WordPress REST API at
  `/wp-json/wp/v2/`.
- **DeFlock Lynnwood** (`https://deflocklynnwood.com/`, HTTP 200): headline *"VICTORY! On 2.23.26
  Lynnwood City Council voted unanimously to cancel the contract with Flock."* and, critically:
  *"We will monitor the locations of the cameras to ensure they are removed. Upon removal, photos of
  the clean locations will be provided on the map page, **corresponding with updates to the Open
  Street Map database**."* Site sections include `Camera Map`, `Records Requests`, `History`, and
  **`Discrepancies`**.
- **DeFlock The USA Cancellation Tracker** (`https://deflocktheusa.com/cancellations/`, HTTP 200):
  105 documented outcomes, faceted by outcome type — 45 Contract Canceled, 20 Contract Rejected,
  19 Cameras Deactivated, 12 Paused, 8 Cameras Removed, 1 ALPRs Banned — across 28 states, with
  per-row date and reason (e.g. "New Bedford, MA — Paused — Aug 2026 — Misuse"; "Searcy, AR —
  Contract Canceled — Aug 2026"). Reason facets: Privacy Concerns (36), Community Pushback (24),
  Federal Agency Access (17), Data Sharing (11), Community Opposition (8), Flock Bad Business (6),
  Data Security/Access (6), Data Security (5).
- **DeFlock Joplin** (read via `https://web.archive.org/web/2026/https://deflockjoplin.today/`):
  documents a **negative claim with a date** — *"Every Flock contract also has the option to activate
  a transparency portal for free. If JPD has activated this portal, we cannot locate it."* and
  *"our request for this policy has again been ignored in the latest production on 1/09/2026."*

**Retrieved:** 2026-08-20

**Implication for the spec:** (a) DeFlock Lynnwood is doing SIG's *device-lifecycle-to-OSM*
contribution loop by hand today; the OSM contribution design (F12.27–F12.30) must make that path
first-class rather than inventing a new one. (b) Eyes Off Colorado's retention values are directly
consumable by the *conflicting retention* detector (T03) — and Castle Rock/Golden at 365 days versus
a state norm of 30 is exactly the contradiction §6.5 wants surfaced. (c) The Cancellation Tracker is
the ecosystem's de-facto `AccountabilityEvent` feed for deployment terminations, and its six-way
outcome taxonomy (canceled / rejected / deactivated / paused / removed / banned) is **better than the
outline's binary lifecycle** and should be adopted into §8.5. (d) Right-of-way permits are an
untapped, per-jurisdiction, government-primary source for physical device installation.

**Outline delta:** **EXTENDS §8.5, §11.4, §12** — adopt the six-state deployment-termination
taxonomy; add ROW permits to §10 Phase 1F; treat local report cards as Tier C/E claims with the
group as the asserting agent.

---

### F12.7 — Reddit is inaccessible from this environment; r/FlockSurveillance can only be characterized secondhand

**Claim:** All Reddit JSON and HTML endpoints refused this agent's requests; the subreddit's scale
(~422,000 members) is attested only by secondary reporting.

**Status:** INACCESSIBLE

**Evidence:** `https://www.reddit.com/r/FlockSurveillance/about.json`, `/new.json?limit=50&raw_json=1`,
`/r/FlockSurveillance.json?limit=25`, and the specific permalink
`/comments/1rsedl3/building_a_collaborative_alpr_abuse_documentation/.json` all returned **HTTP 403
with a 189,908-byte HTML anti-bot body**, under a Chrome UA, with `Accept: application/json`, with
`--compressed`, and with and without `raw_json=1`. `old.reddit.com/r/FlockSurveillance/about.json`
returned a 302 to a zero-byte body. WebFetch returned `Claude Code is unable to fetch from www.reddit.com`.
Secondary attestation of scale: `https://biztechweekly.com/grassroots-backlash-against-flock-safetys-alpr-surveillance-how-activists-and-reddits-r-flocksurveillance-are-fighting-mass-surveillance-in-the-us/`
("over 422,000 members"); corroborating coverage at `https://futurism.com/future-society/redditors-flock-surveillance-alpr-vandalism-memes`.

**Retrieved:** 2026-08-20

**Implication for the spec:** Do not design any ingestion or coordination path that depends on
anonymous Reddit HTTP access. If SIG needs Reddit signal it must use the authenticated OAuth API
under a registered app with a declared user-agent, and must budget for that being revoked. Reddit
should be a *notification* surface (post task digests, receive tips) rather than a *data* surface.

**Outline delta:** **CORRECTS §21** — the outline cites three `reddit.com` URLs as priority sources.
None are retrievable without authentication. Every fact the outline sources to Reddit is currently
unverifiable by an automated agent and should be re-sourced.

---

### F12.8 — National partner organizations: verified pages, what they want, what they contribute

**Claim:** Seventeen national organizations are plausible SIG partners or consumers; their URLs and
roles are verified below, and their asks/offers are asymmetric enough that SIG needs four distinct
partner interface types, not one.

**Status:** PARTIALLY VERIFIED — every URL and page title below was fetched on 2026-08-20; the
"wants/contributes" columns are this workstream's analysis, not the organizations' statements.

**Evidence:** `curl -L` sweep, 2026-08-20; HTTP status and `<title>` recorded per row.

| Organization | Verified URL (HTTP, title) | What they would want from SIG | What they could contribute |
|---|---|---|---|
| EFF — Street Level Surveillance | `https://sls.eff.org/` (200, "Street Level Surveillance") | Deployment corrections and newly documented agencies for the Atlas; vendor-neutral taxonomy alignment | The Atlas itself (CC-BY), the SLS technology taxonomy, Data Library historical datasets, legal expertise |
| EFF — Atlas of Surveillance | `https://www.atlasofsurveillance.org/collaborate` (200) | New datapoints via `aos@eff.org`; **explicitly NOT camera coordinates** | CC-BY agency×technology seed for §10 Phase 1C; the "Report Back" student-research pipeline |
| ACLU (national) — Get the Flock Out | `https://www.aclu.org/campaigns-initiatives/get-the-flock-out` (200, "Fight Creepy ALPR Cameras") | Local dossiers (§15.1) an organizer can act on in one page; contract-renewal calendars | Organizing toolkit, 50-state affiliate network, litigation records, state-legislative tracking |
| EPIC | `https://epic.org/issues/surveillance-oversight/` (**403 Cloudflare "Just a moment…"**) | Policy-layer data: retention rules, sharing scope, audit findings | FOIA litigation, comment filings, statutory analysis |
| CDT | `https://cdt.org/area-of-focus/security-surveillance/` (**403 Cloudflare**) | Aggregate, de-identified pattern data for policy argument | Federal policy channels, technical standards work |
| Brennan Center | `https://www.brennancenter.org/issues/protect-liberty-security/surveillance` (**404 — link rot; the outline's implied path is wrong**) | Cross-vendor network topology (§6.6) for structural analysis | Legal scholarship, state-legislative surveys |
| S.T.O.P. | `https://www.stopspying.org/` (200) | NY/NJ-focused deployment + sharing evidence | Litigation, model legislation, Know Your Rights and privacy toolkits (`/education`) |
| Oakland Privacy | `https://oaklandprivacy.org/` (200) | CA jurisdiction dossiers; surveillance-ordinance compliance tracking | Deep CA municipal-ordinance history; the CCOPS model; long-running local records archive |
| Secure Justice | `https://www.secure-justice.org/` (200) | Bay Area deployment/contract evidence | Municipal advocacy, records requests |
| Lucy Parsons Labs | `https://lucyparsonslabs.com/` (200, "Against Tech Fatalism") | Bulk primary records and reproducible pipelines | OpenOversight-style tooling, FOIA infrastructure experience |
| Stop LAPD Spying | `https://stoplapdspying.org/` (200) | LA-specific data-sharing and RTCC topology | Community-led research methodology; a strong critique of extractive data practice SIG must internalize |
| MediaJustice | `https://mediajustice.org/` (200) | Community-facing summaries, not raw graphs | Grassroots network, framing, equity review |
| Fight for the Future | `https://www.fightforthefuture.org/actions/flockout/` (200, "FLOCK Out") | Campaign-ready per-city fact sheets and renewal deadlines | Mass-mobilization reach; listed as a national campaign in the DeFlock USA directory |
| Restore The Fourth | `https://restorethe4th.com/` (200) | Fourth-Amendment-relevant claim chains with evidence | Local chapters in many cities; constitutional framing |
| POGO | `https://www.pogo.org/` (**403 Cloudflare**) | Procurement and federal-grant lineage (§6.7) | Federal oversight expertise; contracting-data know-how |
| Institute for Justice | `https://ij.org/` (**403 Cloudflare**) | Case-ready evidence chains for specific plaintiffs | Litigation capacity (they litigate ALPR Fourth Amendment cases) |
| NACDL | `https://www.nacdl.org/` (200) | Per-agency audit-log and configuration evidence for discovery motions | Defense-bar distribution; expertise on evidentiary standards |
| Reporters Committee (RCFP) | `https://www.rcfp.org/` (200); Open Government Guide `https://www.rcfp.org/open-government-guide/` (200); Legal Hotline `https://www.rcfp.org/legal-hotline/` (200, `hotline@rcfp.org`) | Records-request success/failure telemetry per state and agency | **The 51-jurisdiction Open Government Guide** (corrections to `guides@rcfp.org`); a free legal hotline; the Local Legal Initiative |

**Retrieved:** 2026-08-20

**Implication for the spec:** Four distinct partner interfaces are required, not one API:
1. **Dataset exchange** (EFF Atlas, EFF Data Library) — needs a stable export format and a
   correction submission channel.
2. **Dossier consumption** (ACLU, FFTF, Restore The Fourth, MediaJustice) — needs the §15.1 local
   dossier as a rendered, citable, one-page artifact, not a graph query.
3. **Evidence-chain export for legal use** (NACDL, IJ, EPIC, S.T.O.P.) — needs per-claim provenance
   traceable to an archived artifact with a hash, defensible in a filing.
4. **Methodology partnership** (Lucy Parsons Labs, Oakland Privacy, Stop LAPD Spying) — needs
   co-authorship and shared governance, not an API key.

**Outline delta:** **EXTENDS §15.7 and §22.6** — the outline lists "machine-readable API/exports" as
one deliverable; the partner analysis shows the highest-value output for most partners is a
*rendered, citable dossier*, not an API. Also **CORRECTS §21** by flagging Brennan Center link rot
and four Cloudflare-blocked partner sites (EPIC, CDT, POGO, IJ) — SIG's outreach cannot assume
programmatic access to partner sites either.

---

### F12.9 — Newsroom landscape and what a newsroom-facing interface must provide

**Claim:** The newsrooms doing this work are verified live; their needs are narrower and more
specific than "an API," and one of them (McClatchy Southeast) already publishes its ALPR reporting
pipeline as an MIT-licensed repo.

**Status:** VERIFIED (liveness), PARTIALLY VERIFIED (needs analysis is this workstream's)

**Evidence:** 2026-08-20 sweep — `https://www.404media.co/` (200, "404 Media"; founded by Jason
Koebler, Emanuel Maiberg, Samantha Cole, Joseph Cox; site nav exposes **"FOIA Forum"** and
"Contact Us/Tips"); `https://themarkup.org/` (200); `https://www.propublica.org/` (200);
`https://www.wired.com/` (200); `https://www.theguardian.com/us` (200);
`https://illinoisanswers.org/` (200, "Illinois Answers Project"); `https://cardinalnews.org/`
(200, "Cardinal News | Virginia news…"); `https://www.muckrock.com/` (403 Cloudflare to browser UA,
**200 with an identifying UA** — see F12.24); `https://www.documentcloud.org/` (403 Cloudflare).
Newsroom repo: `https://github.com/mcclatchy-southeast/private_eyes` (MIT, updated 2026-08-15).
HIBF's 404 page links out to "404 Media: ICE Camera Network," evidencing an existing citation loop
between the community datasets and this newsroom.

**Retrieved:** 2026-08-20

**Implication for the spec — the newsroom interface must provide, in priority order:**
1. **A citable, frozen snapshot.** A journalist must be able to cite "SIG snapshot `2026-08-20T00:00Z`,
   claim `sig:claim/…`" and have that resolve forever, unchanged, after SIG later revises the claim.
   This is the single hardest requirement and the one most likely to be skipped.
2. **Evidence-first drill-down.** Every number resolves to an archived artifact with a content hash,
   a retrieval date, and the original URL — including when the original URL now 404s.
3. **A "what changed" diff feed** per jurisdiction and per agency, subscribable by email/RSS, because
   the news value is in the delta (new deployment, cancelled contract, retention change).
4. **A contradiction ledger, exposed rather than hidden** — a reporter's story is often *"the city
   says 40, the portal says 75, the contract says 78."* §6.5 makes this a first-class state; the
   newsroom interface is where that pays off.
5. **Export in reporter-native formats**: CSV, GeoJSON, and a DocumentCloud-linkable evidence list.
6. **An embargo-safe query mode** that does not log or publish which jurisdiction a reporter is
   researching. (A public "recently queried agencies" feed would leak investigations in progress.
   This is a real risk and is not in the outline.)
7. **Named-human contact for verification**, because no serious newsroom will publish from an
   anonymous database without someone to call.

**Outline delta:** **EXTENDS §15.7** — adds the frozen-citation requirement, the diff feed, and the
embargo-safe query mode; the outline's export list omits all three.

---

# Part B — Stage 0: the ecosystem coordination protocol

### F12.10 — Verified contact-channel table for every Stage 0 project

**Claim:** Every channel below was fetched or resolved on 2026-08-20. Channels marked
**UNVERIFIED** were named by the outline but could not be confirmed to exist.

**Status:** VERIFIED (each row's evidence URL was retrieved), with per-row exceptions noted

**Evidence / channels:**

| # | Project | Primary contact channel (verified) | Secondary channels | Evidence URL fetched | Notes |
|---|---|---|---|---|---|
| 1 | **DeFlock** (the mapping project) | GitHub issues: `https://github.com/FoggedLens/deflock/issues` — `has_issues: true`, 27 open, labels incl. `help wanted`, `good first issue`, `documentation`, `map` | Homepage `https://deflock.org` (SPA, no email on page); the app repo `FoggedLens/deflock-app` | `gh api repos/FoggedLens/deflock` | MIT licence; last push 2026-08-09; not archived. **No email address is published anywhere on deflock.org.** GitHub issues are the only verified channel. |
| 2 | **Eyes on Flock** | Bluesky `https://bsky.app/profile/eyesonflock.com` | — | `https://eyesonflock.com/` (200, 4,534 bytes) | Homepage is a **JS-only shell**: the full rendered text is one line, "Eyes On Flock - Aggregating Flock Safety Transparency Portal Data." `/about` returns the identical shell. **No email, no repo, no API link is discoverable without executing JS.** Bluesky DM is the only human channel found. |
| 3 | **Have I Been Flocked (HIBF)** | Email `humans@haveibeenflocked.com` | Discord `https://discord.com/invite/aV7v4R3sKT`; Bluesky `https://bsky.app/profile/hibf.bsky.social`; **audit-log submission page** `https://haveibeenflocked.com/about/audit-logs` ("Already obtained audit logs? You can submit them directly") | `https://haveibeenflocked.com/` (200); `https://haveibeenflocked.com/submit` (404 — correct path is under `/about/`) | Footer: *"we are fiscally sponsored by, but editorially independent from, **Alternative Newsweekly Foundation**, a 501(c)3 non-profit."* — **the only ecosystem project with a legal-entity backstop.** |
| 4 | **ALPR Watch** (`alprwatch.org`) | Email `alprwatch@proton.me` | GitLab `https://gitlab.com/alprwatch-org/alprwatch` (GPL-2.0+, has `CONTRIBUTING`); "send us your leads" invitation on homepage | `https://alprwatch.org/` (200); `https://gitlab.com/alprwatch-org/alprwatch` (200) | Their wiki `https://wiki.alprwatch.org/index.php/Main_Page` returned **HTTP 500, `Wikimedia\Rdbms\DBConnectionError`** — down on 2026-08-20. |
| 5 | **alpr.watch** (Louis Rossmann's, *a different project*) | Email-alert signup form on site; Donorbox/Square donate links | — | `https://alpr.watch/` (200, 107,433 bytes) | *"Looking for Louis Rossman's alpr.watch site?"* appears verbatim on `alprwatch.org` — **the two are explicitly distinct.** alpr.watch scans local-government meeting agendas for "flock", "license plate reader", "alpr" and maps upcoming meetings. **The outline conflates these two projects.** |
| 6 | **EFF Atlas of Surveillance** | Email `aos@eff.org` | Volunteer intake form `https://join.eff.org/atlas/`; educator "Report Back" tool | `https://www.atlasofsurveillance.org/collaborate` (200) | Verbatim routing rule: *"Please do not send us the coordinates of individual surveillance cameras or automated license plate readers. You may consider sending that data to DeFlock.me."* |
| 7 | **ALPR Accountability Atlas** | — | — | `https://alpratlas.org/collaborate` → **HTTP 404** (9-byte body, "Not Found") | **No contact channel verified.** The outline's cited root `https://alpratlas.org/` is the only known entry point; a `/collaborate` path does not exist. Outreach must start from whatever contact is embedded in the root page or the data-dictionary CSV (see R-workstream on Layer E). |
| 8 | **ALPR Abuse Library / Kansas Watch** | Email `info@kansas.watch` | Submission form `https://forms.gle/isGYpLcKu9YeFzSm9`; a `JSON` endpoint linked from the footer | `https://library.kansas.watch/` (200, 33,995 bytes) | Footer: *"All linked articles remain the property of their respective publishers."* Site is *"A publicly maintained, editorially reviewed index."* |
| 9 | **FlockReporter** | **DEAD** — Discord `https://discord.gg/m9VsbR6d5z` (archived, unverified whether the invite still resolves); Matrix `#deflock:flockreporter.org` (**unresolvable — homeserver is the dead domain**) | — | `https://web.archive.org/web/20260728225506id_/https://flockreporter.org/` | See F12.1. |
| 10 | **Technopolice** (FR/BE) | Email `contact@technopolice.fr` | Forum `https://forum.technopolice.fr/`; "Fuiter" (leak) intake in site nav | `https://technopolice.fr/` (200, 73,147 bytes; `www.` redirects to apex) | French-language; a coalition ("des associations et collectifs militants") rather than one person. |
| 11 | **DeFlock The USA** (chapter registry) | Email `support@deflocktheusa.com` (subject prefixes `TIP` / `PRESS` documented on the contact page) | Tip form `https://deflocktheusa.com/submit-a-tip/`; Bluesky/Mastodon/X/Instagram/YouTube; corrections page `/corrections/`; editorial standards `/editorial-standards/` | `https://deflocktheusa.com/contact/` (200) | **All-rights-reserved content** (F12.5) — permission is required, not optional. |
| 12 | **MuckRock** | API `https://www.muckrock.com/api_v2/`, token auth at `https://accounts.muckrock.com/api/token/` | Assignments (crowdsourcing) product; `https://www.muckrock.com/place/…` state guides | `https://www.muckrock.com/api/` | Requires *"an identifiable user agent … that uniquely identifies your automation and includes a real point of contact"* (F12.24). |
| 13 | **MapRoulette** | API key header `apiKey`, from `https://maproulette.org/user/profile` | OpenAPI doc `https://maproulette.org/assets/swagger.json` (302,427 bytes, v4.9.5) | `https://maproulette.org/assets/swagger.json` (200) | See F12.29. |
| 14 | **OSM Data Working Group / community** | Community forum `https://community.openstreetmap.org/` (Discourse, `.json` API works unauthenticated) | Per-country forum categories; `talk` mailing list | `https://community.openstreetmap.org/t/unverified-flock-cameras-causing-mass-panic/146534.json` (200, 69,564 bytes) | The mandatory consultation venue for any organised or automated editing (F12.27). |
| 15 | **RCFP** | `guides@rcfp.org` (Open Government Guide corrections); `hotline@rcfp.org` (legal hotline) | `volunteer@rcfp.org` | `https://www.rcfp.org/open-government-guide/`, `https://www.rcfp.org/legal-hotline/` | Verbatim on the guide index: *"See something that needs updating? Please email guides@rcfp.org, so we can fix it!"* |
| 16 | **Local chapters (representative verified emails)** | `DeFlockAtlanta@Proton.me`; `deflockbhm@proton.me`; `deflockoly@proton.me`; `deflocktucson@pm.me`; `info@eyesoffindiana.org` / `press@eyesoffindiana.org` / `walker@eyesoffindiana.org`; `deflockthevalley@gmail.com` | DeFlock Atlanta MuckRock profile `https://www.muckrock.com/accounts/profile/freethemall/`; DeFlock Olympia Linktree `https://linktr.ee/deflockolympia`; DeFlock Tucson Instagram + change.org petition | Per-site HTML scrape, 2026-08-20 | **Note the pattern: 4 of 6 chapter emails are ProtonMail/pm.me.** These are pseudonymous operators. Outreach must not demand legal identity. |

**Retrieved:** 2026-08-20

**Implication for the spec:** Stage 0 outreach cannot be an email merge. Five distinct channel types
exist (GitHub issue, encrypted email, Discord, Bluesky DM, web form), two key projects have **no
usable channel at all** (Eyes on Flock, ALPR Accountability Atlas), and the majority of local-group
operators are pseudonymous. The collaboration ledger must model `contact_channel_type` and support
`no_channel_found` as a terminal state that blocks ingestion rather than defaulting to "scrape anyway."

**Outline delta:** **CORRECTS §17 Stage 0** — the outline's step 1 ("contact / investigate
collaboration interfaces") assumes contactability. Two of the six named projects are not
contactable by any published channel. **CORRECTS §21** — `alprwatch.org` and `alpr.watch` are two
different projects and the outline's description ("Reproducible FOIA normalization") applies to the
former only.

---

### F12.11 — Stage 0 must be a gated, executable pipeline stage, not a preamble

**Claim:** Stage 0 should be implemented as a machine-checked gate: no ingestion adapter may run
against a source whose ledger record lacks `ingestion_permitted: true` or an explicit
`legal_basis` justification.

**Status:** UNVERIFIED (this is design, not a factual claim)

**Implication for the spec:** The Stage 0 state machine, per source:

```
DISCOVERED
  → TRIAGED           (license read? channel found? one-person project?)
  → CONTACTED         (outreach sent; timestamp; channel; message hash)
  → AWAITING_REPLY    (SLA 21 days; then ESCALATE or DEFAULT_POSTURE)
  → NEGOTIATING       (terms under discussion)
  → AGREED            (Data Use Memorandum executed → ingestion_permitted: true)
  | DECLINED          (ingestion_permitted: false, hard block)
  | OPTED_OUT         (explicit "do not scrape" → hard block + link-only mode)
  | NO_CHANNEL        (no contact exists → link-only mode, never bulk copy)
  | DORMANT           (source unreachable N days → succession clause activates)
  → REVIEW (annual)   (re-confirm terms; re-check license URL hash)
```

Two rules make it real:
- **`DEFAULT_POSTURE` on non-reply is link-only.** Silence is not consent. A source in
  `AWAITING_REPLY` past SLA drops to link-and-cite (metadata + URL + retrieval date only), never
  bulk copy.
- **The gate is enforced in code, not policy.** The ingestion runner loads the ledger record before
  the adapter and raises if `ingestion_permitted` is not `true`. This is testable (REQ-R12-06).

**Outline delta:** **EXTENDS §17 Stage 0** — makes an ordering suggestion into an enforced
precondition with a defined default on silence.

---

### F12.12 — The Stage 0 outreach template (usable text)

**Claim:** The following is the actual message SIG should send. It is written to be sendable
unchanged over email, a GitHub issue, or a Discord/Matrix DM.

**Status:** UNVERIFIED (design artifact)

**Implication for the spec:** Ship this as `docs/outreach/TEMPLATE.md` with the bracketed slots
filled from the collaboration ledger, so that outreach is reproducible and auditable.

```text
Subject: Asking permission before we use [PROJECT] data — Surveillance Infrastructure Graph

Hi [NAME / MAINTAINERS],

I'm writing on behalf of the Surveillance Infrastructure Graph (SIG), an open project building a
provenance-tracked, temporally versioned knowledge graph of surveillance infrastructure in the
United States — who deploys what, where, under what contracts and policies, connected to whom, and
according to exactly which evidence.

I'm contacting you BEFORE writing any code that touches [PROJECT], because [PROJECT] is one of the
sources we'd want to federate with, and we would rather have your permission and your terms than
your data.

WHAT WE ARE NOT DOING
  - We are not building a competitor to [PROJECT]. We do not want to replace [SPECIFIC THING THEY DO
    WELL, e.g. "the ALPR map", "the audit-log corpus", "the portal archive"]. We consider that layer
    yours and we will link to it rather than reproduce it.
  - We are not collecting license plates, individual travel histories, or personal data about
    ordinary people. We track institutions.
  - We will not publish anything under your name or imply endorsement.

WHAT WE ARE ASKING FOR (any subset is fine — "no" to all of it is a complete answer)
  1. Data access: is there an export, feed, dump, or API we may use? If scraping is the only option,
     may we, and at what rate? Is there a path you'd prefer instead?
  2. Licence clarity: under what terms may we (a) store, (b) derive from, and (c) redistribute your
     data? If you have no licence today, would you be willing to state one? (Even
     "CC BY 4.0 for the data, all rights reserved for the prose" is enormously helpful.)
  3. Identifier stability: do your record IDs persist across updates? If they change, is there a
     mapping? We want to preserve your IDs in our graph so people can get back to you.
  4. Contribution-back channel: if we find an error, a missing record, or better evidence, how would
     you like to receive it — issue, PR, email, form, or not at all?
  5. Attribution preference: exactly how do you want to be credited in our UI, our exports, and our
     API responses? Please give us the string you want.
  6. Opt-out: if you would rather we did not ingest [PROJECT] at all, say so and we will hard-block
     it in our pipeline. That flag is enforced in code, not in a policy document.

WHAT WE OFFER IN RETURN
  - Corrections upstream first. When our reconciliation finds a discrepancy involving your data, you
    get it before we publish anything derived from it, in whatever format you prefer.
  - Traffic and citation. Every claim sourced from you carries your name and a link, in the UI, in
    every export row, and in every API response.
  - Derived research tasks. Our system generates concrete, evidence-defined research gaps
    ("this agency's portal reports 40 cameras; 27 are mapped; here is the records request that would
    close it"). We will route the ones in your area of interest to you, at no cost and with no
    obligation.
  - Co-authorship on methodology. If we build on your method, you are a named author on the writeup,
    not a footnote.
  - Mirroring and archival as backup. We will keep a content-addressed, dated mirror of your public
    data and, if you want it, hand you a full copy of that mirror at any time, for free, forever.
    If your project ever goes down, we will host a read-only archive of it under your terms and with
    a clear statement that it is an archive, not a continuation — unless you tell us not to. Several
    projects in this ecosystem are one-person efforts. This is meant as insurance for you, not as a
    claim on your work. See the attached succession clause; you set its terms, and you can revoke it.

WHAT WE'LL DO IF WE DON'T HEAR BACK
  Nothing beyond linking to you and citing you. Silence is not consent. We default to link-and-cite:
  we will store your public URL, the date we retrieved it, and metadata, and nothing else.

Our work is at [REPO URL]. Our data-use memorandum template is at [MOU URL]. Our public
collaboration ledger — which will show exactly what we asked you and what you said — is at
[LEDGER URL].

Thank you for the work. It is the reason this project is possible at all.

— [NAME], Surveillance Infrastructure Graph
   [EMAIL] · [SIGNAL/MATRIX] · [PGP FINGERPRINT]
```

**Outline delta:** **EXTENDS §17 Stage 0 step 5** — the outline says "define attribution and
contribution-back mechanisms"; this makes them a negotiated, per-source, recorded artifact.

---

### F12.13 — Route the outreach to the right channel and the right ask

**Claim:** The outreach template needs per-project variants; a generic message will fail with at
least four of the fourteen Stage 0 counterparties.

**Status:** UNVERIFIED (design, grounded in the verified channel facts of F12.10)

| Counterparty | Channel | Opening variant | Specific ask |
|---|---|---|---|
| DeFlock | **GitHub issue**, `help wanted` label, public | Engineer-to-engineer; propose a PR, not a partnership | Confirm the `surveillance:type=ALPR` tag contract; agree an operator-attribution suggestion format (F12.30); ask whether they want SIG's operator inferences as issues or as a feed |
| Eyes on Flock | **Bluesky DM** (only channel) | Short, ≤300 chars, ask for an email | Ask for portal-snapshot access and whether an archive repo exists |
| HIBF | Email + Discord | Warm; they already run a submission pipeline | Ask for export cadence/licence; offer to route SIG's records-request tasks so responses land in their corpus |
| ALPR Watch | Email `alprwatch@proton.me` + GitLab issue | Code-first; their repo has `CONTRIBUTING` | Offer to co-maintain the reason-coding map; note their wiki is 500-ing and offer a mirror |
| EFF Atlas | `aos@eff.org` | Institutional, formal | Ask for the correction-intake format; **respect their "no camera coordinates" rule** by routing coordinate corrections to DeFlock instead |
| ALPR Accountability Atlas | **No channel** | — | Blocked. Link-only until a channel is found. Try the data-dictionary CSV and WHOIS. |
| Kansas Watch | `info@kansas.watch` + Google Form | Editorial-to-editorial | Ask about the footer `JSON` endpoint's terms and stability |
| DeFlock The USA | `support@deflocktheusa.com` | Publisher-to-publisher; **they are all-rights-reserved** | Ask for explicit written permission to mirror the chapter directory and cancellation tracker; offer co-maintenance |
| Local chapters (85) | Per-chapter email, mostly ProtonMail | **Do not mass-mail.** Contact only when SIG has something specific for that jurisdiction | Offer the jurisdiction's task queue and dossier; ask nothing on first contact |
| Technopolice | `contact@technopolice.fr`, in French | Movement-to-movement | Schema alignment for international expansion; do not propose ingesting French data in v1 |

**Implication for the spec:** The ledger stores `outreach_variant` and the rendered message hash so
that "what did we actually say to them" is answerable a year later.

---

### F12.14 — SIG's archival role is the ecosystem's single highest-value contribution, and it is time-critical

**Claim:** The ALPR-accountability ecosystem is structurally fragile — one project has already
vanished, a second's wiki is currently 500-ing, a third is a JS shell with no contact, and most are
one-person efforts with no legal entity — so mirroring is not a nicety but the thing SIG can offer
that no one else is offering.

**Status:** VERIFIED (the fragility evidence), UNVERIFIED (the design response)

**Evidence — the fragility inventory, all observed on 2026-08-20:**
- `flockreporter.org`: **no A record.** Survives as 7 Wayback URLs from a single capture 23 days
  before this research. Its Matrix room died with its domain.
- `wiki.alprwatch.org`: **HTTP 500, `Wikimedia\Rdbms\DBConnectionError`.**
- `eyesonflock.com`: JS-only shell; no email, no repo, no licence discoverable. If the maintainer
  stops paying, there is no one to ask and nothing to inherit.
- `alpratlas.org`: no contact path found; `/collaborate` 404s.
- `livefreeva.org` → `deflockthevalley.com`: rename with a redirect that will eventually lapse.
- Six of 85 chapter sites are behind Cloudflare bot challenges; several chapters exist **only** as a
  Bluesky handle, an Instagram account, a Linktree, or a subreddit — all platform-hostage.
- Only **one** project in the entire ecosystem has a legal-entity backstop: HIBF, *"fiscally sponsored
  by … Alternative Newsweekly Foundation, a 501(c)3."*
- Adversarial pressure is documented: the archived FlockReporter page records that in December 2025
  Flock Safety engaged Cyble Inc. to file takedown notices against transparency sites, and HIBF's own
  materials describe Flock's *Guide to Flock Safety Data for Open Records Laws* advising agencies to
  redact and to negotiate narrowed timeframes (F12.22). **Projects here face active pressure to disappear.**

**Retrieved:** 2026-08-20

**Implication for the spec — SIG's "ecosystem insurance" design:**

1. **Mirror on ingest, always.** Every fetch of a partner source is content-addressed (SHA-256),
   dated, and stored — not as a cache, as an archive of record. This is required by §19 anyway; the
   insurance framing just makes it non-negotiable and makes the retention indefinite.
2. **Three-tier archive per source.** (a) *Raw capture* — bytes as retrieved, private if terms
   require; (b) *Rendered public derivative* — what SIG is licensed to show; (c) *Metadata-only
   stub* — always public: name, URL, licence, last-seen, health status, contact, successor.
   A source that goes dark still leaves a public stub saying it existed, which is what a future
   researcher needs most.
3. **Push to a second archive SIG does not control.** Every capture is also submitted to the Wayback
   Machine via `https://web.archive.org/save/<url>`. SIG must not be the only copy — a project whose
   value is "insurance" cannot itself be a single point of failure. FlockReporter's survival on
   exactly seven Wayback URLs is the proof.
4. **A health monitor with escalation.** Per source: DNS resolution, HTTP status, TLS expiry, content
   hash drift, `robots.txt` change, licence-statement hash change. Three consecutive failures raise
   a **`SOURCE_DORMANT`** task (T22) and notify the maintainer's recorded contact. This would have
   caught `flockreporter.org` and `wiki.alprwatch.org` days after they broke instead of never.
5. **Succession offer, made in advance and in writing.** Every partner agreement includes an
   opt-in clause (F12.15 §7) under which SIG will host a clearly-labelled read-only archive if the
   project goes dark. It must be *opt-in and revocable*, because an uninvited "we'll take over your
   project if you die" is the single most likely way to poison a relationship with a pseudonymous
   volunteer maintainer.
6. **Escrow the operational secrets, not just the data.** Domain registrar, DNS, hosting, and repo
   ownership are what actually kill a project — not data loss. Offer (never require) a dead-man's-switch
   escrow: encrypted credentials held by a neutral third party, released only on the maintainer's
   declared conditions. Pair with a standing offer to pay a partner's domain renewal.
7. **Never continue a dead project under its own name.** An archive is labelled `ARCHIVE — this
   project ended on <date>; SIG hosts this copy under <terms>; SIG is not its continuation.`
   Impersonating a dead accountability project would be worse than losing it.

**Outline delta:** **EXTENDS §22.6 substantially.** The outline measures SIG's success by whether it
"makes other projects stronger" and lists corrections, traffic, and targeted requests. It omits the
strongest form of that: **keeping other projects from disappearing.** On the evidence gathered here,
that is the highest-expected-value thing SIG can do for the ecosystem in year one, and it is
achievable before a single graph node is modelled.

---

### F12.15 — Partner Agreement / Data Use Memorandum (usable text)

**Claim:** The following template covers the six required terms (attribution, redistribution,
cadence, ID stability, revocation, shutdown succession) in language a volunteer maintainer will
actually read.

**Status:** UNVERIFIED (design artifact; not legal advice and explicitly framed as non-binding)

```text
SIG DATA USE MEMORANDUM  ·  v1  ·  [SOURCE NAME] ↔ Surveillance Infrastructure Graph

This is a plain-language statement of how SIG will use [SOURCE]'s public data. It is not a contract
and creates no obligation on [SOURCE]. It exists so that both sides have the same document to point
at, and so that anyone auditing SIG can see what we were told.

0. THE SOURCE
   Name: [SOURCE NAME]        Maintainer / contact: [NAME or PSEUDONYM] <[CHANNEL]>
   Canonical URL(s): [URLS]   Legal entity, if any: [ENTITY or "none — individual volunteer"]
   Pseudonymity: [ ] The maintainer's legal identity is not required, requested, or recorded by SIG.

1. WHAT SIG MAY INGEST
   Datasets/endpoints:            [LIST]
   Method:                        [ ] provided export  [ ] API  [ ] permitted scrape at [RATE]
   Excluded (never ingested):     [LIST — e.g. plate-level records, member lists, unpublished drafts]
   Personal data:                 SIG will not ingest license plates, individual travel histories, or
                                  identifiable persons except public officials acting officially.

2. LICENCE AND REDISTRIBUTION
   Licence asserted by [SOURCE]:  [e.g. CC BY 4.0 / ODbL / GPL-2.0+ / all rights reserved / none]
   Licence statement URL:         [URL]   (SIG stores a hash of this page and re-checks it annually)
   SIG may STORE:                 [ ] yes  [ ] yes, privately only  [ ] no
   SIG may DERIVE claims:         [ ] yes  [ ] yes with review  [ ] no
   SIG may REDISTRIBUTE:          [ ] full  [ ] derived aggregates only  [ ] metadata + link only
   Downstream licence SIG applies to the derived layer: [e.g. CC BY-SA 4.0 / ODbL-compatible split]
   ODbL note: OSM-derived geometry is kept in a logically separate store with its own licence
   boundary; joins are performed at query time so the non-OSM layer does not become a Derivative
   Database. (See workstream R-licensing.)

3. ATTRIBUTION
   Required credit string (verbatim): "[STRING]"
   Where it appears: [x] every UI element showing the claim  [x] every export row (`source_attribution`
   column)  [x] every API response (`sources[].attribution`)  [x] the SIG sources page  [x] any
   publication or slide deck derived from it.
   Link target: [URL]. SIG will not use [SOURCE]'s logo or name to imply endorsement.

4. CADENCE AND LOAD
   Refresh interval:  [e.g. daily / weekly / on-change]
   Rate limit SIG will observe: [N req/min], with `User-Agent: SIG-Ingest/<version> (+<url>; <email>)`
   Conditional requests (ETag / If-Modified-Since): [x] yes
   SIG will back off immediately on 429/503 and will stop entirely on request, same day.

5. IDENTIFIER STABILITY
   [SOURCE] IDs are:  [ ] stable  [ ] stable within a release  [ ] unstable
   SIG preserves upstream IDs verbatim in `external_ids[{scheme, id, retrieved_at}]` and never
   overwrites them. If IDs churn, SIG maintains a crosswalk and publishes it back to [SOURCE].
   SIG's own IDs are stable and resolvable: `https://sig.example/id/<type>/<uuid>` (see Q37, F12.34).

6. CORRECTIONS AND CONTRIBUTION BACK
   When SIG's reconciliation implicates [SOURCE]'s data, SIG will notify [SOURCE] via [CHANNEL]
   [ ] before publishing  [ ] at publication  [ ] not at all (source's choice)
   Preferred correction format: [ ] issue  [ ] PR  [ ] email  [ ] CSV  [ ] form  [ ] none
   SIG will not edit [SOURCE]'s systems directly and holds no credentials to them.

7. SHUTDOWN, DORMANCY, AND SUCCESSION   ← opt-in, revocable at any time, no reason required
   [ ] 7a. MIRROR. SIG keeps a dated, content-addressed mirror of [SOURCE]'s public data.
   [ ] 7b. HANDBACK. On request, at any time, SIG delivers that entire mirror to [SOURCE] in an open
           format, at no cost, no questions asked. This is unconditional and survives any dispute.
   [ ] 7c. DORMANCY MONITOR. SIG monitors [SOURCE]'s availability and notifies [CONTACT] on failure.
           Dormancy threshold: [N] consecutive days unreachable.
   [ ] 7d. ARCHIVE PUBLICATION. If [SOURCE] is dormant beyond the threshold AND [SOURCE] has not
           revoked this clause, SIG may publish a READ-ONLY archive, prominently labelled:
             "ARCHIVE. [SOURCE] ended/became unreachable on [DATE]. This is a preserved copy hosted
              by SIG under the terms [SOURCE] set. SIG is not a continuation of [SOURCE]."
           Archive licence: [as in §2, or a narrower archive-only grant]
           SIG will NOT: use [SOURCE]'s name as an active project, accept contributions in its name,
           solicit donations in its name, or claim its social handles.
   [ ] 7e. NAMED SUCCESSOR. If [SOURCE] designates a successor maintainer, SIG hands the mirror to
           them instead and takes the archive down: successor = [NAME/CONTACT].
   [ ] 7f. CREDENTIAL ESCROW (optional, separate). [SOURCE] may place domain/DNS/repo credentials in
           escrow with [THIRD PARTY], released only on [CONDITIONS]. SIG never holds these directly.
   [ ] 7g. SUNSET. [SOURCE] may specify that on shutdown everything is deleted rather than archived.
           SIG will honour deletion over preservation if [SOURCE] chooses it. Selected: [ ] delete

8. REVOCATION
   [SOURCE] may revoke any part of this memorandum at any time, by any channel, with no reason given.
   On revocation SIG will, within 7 days: set `ingestion_permitted: false` (a code-enforced hard
   block), stop all fetching, remove redistributed content from public exports and the API, and
   publish a dated ledger entry recording the revocation. SIG will retain a private, non-public
   archival copy ONLY if clause 7a was accepted and 7g was not; otherwise it is deleted.
   Claims already published that cite [SOURCE] will be marked `source_withdrawn` rather than silently
   deleted, so the historical record of what SIG asserted remains auditable.

9. NON-COMPETITION COMMITMENT
   SIG will not build or promote a substitute for [SPECIFIC LAYER, e.g. "the ALPR camera map"].
   Where SIG's UI would duplicate [SOURCE]'s function, SIG links out instead. If SIG ever needs to
   build something overlapping, SIG will tell [SOURCE] first and explain why.

10. DISPUTES
   First: a direct conversation on [CHANNEL]. If unresolved: SIG suspends the disputed ingestion for
   the duration of the dispute (suspension is the default, not the last resort). SIG publishes the
   disposition in the collaboration ledger either way.

Signed (informally, by whatever means you like):
   [SOURCE]: ______________________  date ________
   SIG:      ______________________  date ________
```

**Outline delta:** **EXTENDS §17 Stage 0 and §22.6** — no equivalent instrument exists in the outline;
clause 7 in particular operationalizes the archival-insurance idea.

---

### F12.16 — The collaboration status ledger: machine-readable, public, and enforced

**Claim:** Stage 0's output should be a versioned, public, per-source record that the ingestion
pipeline reads at runtime.

**Status:** UNVERIFIED (design artifact)

**Implication for the spec — `collaboration/<source_id>.yaml`, one file per source, in git:**

```yaml
source_id: deflock_the_usa_chapters       # stable, never reused
display_name: "DeFlock The USA — Chapter Directory"
canonical_urls:
  - https://deflocktheusa.com/chapters/
layer: H_civil_society                    # A..G per §2, plus H for civil society
operator_type: individual_publisher       # individual | collective | nonprofit | academic | agency | vendor
legal_entity: null                        # null is itself a risk signal
pseudonymous_maintainer: true

outreach:
  status: AWAITING_REPLY                  # per F12.11 state machine
  channel: {type: email, address: support@deflocktheusa.com}
  variant: publisher_to_publisher
  sent_at: 2026-08-21T00:00:00Z
  message_sha256: "…"
  sla_days: 21
  escalation_path: [bluesky_dm, tip_form]
  history:
    - {at: 2026-08-21T00:00:00Z, event: contacted, note: "initial outreach"}

license:
  name: all-rights-reserved
  statement_url: https://deflocktheusa.com/terms/
  statement_sha256: "…"
  statement_last_checked: 2026-08-20
  attribution_required: true
  attribution_string: null                # to be supplied by the source
  redistribution: prohibited
  derivation: unclear
  seen_directly: true                     # CONVENTIONS rule 4: we read the terms, not inferred them

terms:
  refresh_interval: P7D
  rate_limit_rpm: 6
  user_agent: "SIG-Ingest/0.1 (+https://sig.example; contact@sig.example)"
  robots_txt_respected: true
  conditional_requests: true

id_stability:
  upstream_ids_present: false             # chapter cards have no IDs; SIG must key on URL
  key_strategy: url_normalized
  crosswalk_published_at: null

contribution_back:
  accepts: unknown
  preferred_format: unknown
  notify_before_publish: true

succession:                               # F12.15 clause 7
  mirror: false                           # false until AGREED — no mirroring without permission
  handback_offered: true
  dormancy_monitor: true
  dormancy_threshold_days: 30
  archive_publication_permitted: false
  named_successor: null
  sunset_on_shutdown: false

health:
  last_success_at: 2026-08-20T17:02:00Z
  last_status: 200
  consecutive_failures: 0
  dns_resolves: true
  content_hash_drift_7d: 0.04

# THE GATE. The ingestion runner refuses to execute an adapter unless this is true.
ingestion_permitted: false
ingestion_permitted_reason: "No reply yet; default posture is link-and-cite only."
link_and_cite_permitted: true             # always true for public URLs
```

Enforcement requirements:
- The runner loads the ledger record **before** constructing the adapter and raises
  `IngestionNotPermitted` if `ingestion_permitted != true`. There is no override flag in the
  production path.
- CI fails if any adapter exists without a matching ledger file, or if a ledger file has
  `license.seen_directly: false` while `redistribution: permitted`.
- The ledger is **public**, so a partner can verify what SIG recorded about them without asking.
- Every ledger change is a git commit — the audit trail is free.

**Outline delta:** **EXTENDS §17 Stage 0 steps 2–5** — turns "determine data licenses / identify
APIs / define attribution" into one enforced artifact.

---

# Part C — Research task generation (§12, §15.6)

### F12.17 — A rule specification language for research tasks

**Claim:** Every task type should be a declarative rule with eight mandatory parts, stored as data,
version-stamped, and executed on a schedule — not code scattered through the application.

**Status:** UNVERIFIED (design artifact)

**Implication for the spec — the rule schema (`tasks/rules/<id>.yaml`):**

```yaml
id: T01_missing_physical_devices
version: 3                       # bump invalidates open tasks generated by v<3 (see F12.20)
title: "Portal reports more cameras than are mapped"
category: physical_reconciliation
detector:                        # a query over the graph; must be pure and side-effect free
  language: sql                  # sql | cypher | sparql — one engine, declared
  query: |
    SELECT d.org_id, d.jurisdiction_id,
           p.camera_count AS asserted, m.mapped_count AS observed
    FROM deployment d
    JOIN portal_snapshot_latest p USING (org_id)
    LEFT JOIN mapped_device_count m USING (org_id)
    WHERE p.camera_count - COALESCE(m.mapped_count,0) >= 3
      AND p.snapshot_age_days <= 120
  entity_key: [org_id]           # dedupe key: one open task per key per rule
priority:                        # deterministic function → 0..100
  formula: |
    40
    + 25 * clamp(gap / max(asserted,1), 0, 1)      # relative size of the gap
    + 15 * population_percentile(jurisdiction_id)  # how many people are affected
    + 10 * (1 if renewal_within_days(org_id, 120) else 0)   # actionability window
    + 10 * staleness_factor(latest_evidence_age_days)
  ceiling: 100
required_evidence:               # "what would close this"
  any_of:
    - {type: osm_node, min_count: "{{gap}}", tags_required: [man_made=surveillance, "surveillance:type=ALPR"]}
    - {type: field_photo, min_count: "{{gap}}", must_have: [geotag_or_intersection, date]}
    - {type: public_record, doc_class: [installation_list, invoice, ROW_permit], must_name_locations: true}
    - {type: negative_finding, requires: "documented survey of the corridor with method + date"}
assignee_class: field_mapper     # see F12.19
effort_estimate: {unit: hours, p50: 3, p90: 12, skills: [local_travel, osm_editing]}
geography: {type: jurisdiction, id_field: jurisdiction_id}
completion_test: |               # machine-checkable; a human closes only if this passes
  mapped_count >= asserted - tolerance(asserted)
  OR negative_finding_accepted = true
auto_expire_days: 180
suppress_if:
  - "org has an open task of rule T13 (portal disappeared)"   # don't chase counts on a dead portal
  - "jurisdiction opted out of field tasks"
safety_class: field_work         # desk | field_work | sensitive  → drives the safety banner (F12.32)
routes_to_partner: deflock       # where a completed result should be contributed back
```

Rules for the rule language:
- **Detectors must be pure queries.** They may not call external services; if they need external
  data (e.g. a live portal), that goes through a normal ingestion adapter first. This keeps task
  generation reproducible and re-runnable against a historical snapshot.
- **Priority must be a formula, not a model.** A contributor must be able to read *why* a task is
  ranked where it is. "Explainable confidence" (§9.3) applies to task priority too.
- **`required_evidence` is the contract.** It is what the task promises will close it. If a
  contributor supplies it and the task does not close, that is a bug in the rule.
- **`completion_test` must be machine-checkable** wherever possible, so that closure is not a matter
  of a reviewer's mood.
- **Negative findings are first-class** (per §9.4): "I drove the corridor on 2026-08-20 and found no
  additional cameras" is a valid, storable, closing answer that itself becomes an evidence artifact.

**Outline delta:** **EXTENDS §12** — the outline gives seven prose examples; this makes them
executable, prioritizable, and closable.

---

### F12.18 — Assignee classes

**Claim:** Six assignee classes cover the ecosystem's actual division of labour.

**Status:** UNVERIFIED (design), grounded in the observed behaviour of real groups (F12.6)

| Class | Who they are in practice | Typical tasks | Needs from SIG |
|---|---|---|---|
| `field_mapper` | Someone who will physically go look — DeFlock Lynnwood's removal-verification photos are exactly this | T01, T05, T09, T12, T20 | A map, a checklist, a photo spec, a **safety briefing**, and an OSM/DeFlock hand-off |
| `records_requester` | Files FOIA — DeFlock Dane, DeFlock Joplin, DeFlock Atlanta (MuckRock profile `freethemall`) | T02, T03, T06, T11, T16, T19, T24 | A generated request (F12.25), the state statute, the right custodian, a deadline tracker |
| `document_reviewer` | Reads what came back; MuckRock Assignments' 1,300+ volunteers are the proof this scales | T15, T17, T25, T27 | A PDF viewer, a field-extraction form, an "I'm not sure" button |
| `analyst` | Reconciles, dedupes, resolves entities | T08, T21, T23, T26, T29 | Side-by-side diffs, merge tooling, a "leave it contradictory" option |
| `local_group` | An organization that owns a jurisdiction queue (F12.21) | Any, routed geographically | A jurisdiction dossier, a queue, a digest, contact for the relevant council |
| `journalist` | Wants the story, will do primary work for it | T13, T14, T22, T28 | Frozen citations, embargo-safe queries, a named human to call |

---

### F12.19 — The research task type specification (30 types)

**Claim:** Thirty task types cover the reconciliation surface the graph exposes; the outline's seven
are T01–T07, and T08–T30 are additions this workstream identified.

**Status:** UNVERIFIED (design), with several types directly evidenced by observed ecosystem
behaviour (noted per row)

Legend — **Assignee**: FM field_mapper · RR records_requester · DR document_reviewer · AN analyst ·
LG local_group · JO journalist. **Effort** is p50. **Src**: `§12` = in the outline; `NEW` = added here.

| ID | Task type | Detector (query over the graph) | Priority drivers | Required evidence ("what closes it") | Assignee | Effort | Completion test | Src |
|---|---|---|---|---|---|---|---|---|
| T01 | Missing physical devices | `portal.camera_count − mapped_count ≥ 3` and portal snapshot ≤120d old | gap size ÷ asserted; population; renewal proximity | ≥gap new OSM ALPR nodes, or geotagged photos, or a records list of locations, or an accepted negative survey | FM | 3 h | `mapped ≥ asserted − tol` or negative finding accepted | §12 |
| T02 | Missing contract | deployment exists (Atlas or portal) ∧ no linked `Contract` | deployment size; agency budget; election/renewal calendar | Contract, invoice, PO, or council approval doc, archived + linked | RR | 1 h to file | ≥1 `Contract` node linked with an `EvidenceArtifact` | §12 |
| T03 | Conflicting retention | ≥2 non-superseded claims on `retention_days` for same org with different values | delta magnitude; recency of the newer claim; whether one source is Tier A | Current configuration export, policy doc, or written agency statement, dated | RR | 1 h | One claim marked authoritative with Tier ≤C evidence, or contradiction formally accepted with both sides dated | §12 |
| T04 | Stale evidence | `now − max(evidence_date) > threshold(entity_type)` | how load-bearing the entity is; downstream claim count | Any Tier ≤C artifact dated within the window | RR/DR | 30 m | `max(evidence_date)` within threshold | §12 |
| T05 | Orphaned device | OSM node has `manufacturer` ∧ no `operator` | device density in area; whether neighbours are attributed | Signage photo, records response naming the operator, ROW permit, or agency confirmation | FM/RR | 2 h | `operator` asserted with ≥Tier D evidence | §12 |
| T06 | New sharing node | Org appears in a network/sharing export but is absent from the org registry | how many networks it touches; whether private-sector | Identity resolution: legal name, jurisdiction, ORI or equivalent, with a source | AN | 45 m | Org node exists with `jurisdiction` and ≥1 external ID | §12 |
| T07 | Vendor replacement | Contract terminated ∧ new procurement for a different ALPR vendor in same org within 365d | contract value; whether coverage grew | Both contracts + a `replaced_by` lifecycle edge | AN/RR | 1 h | `replaced_by` edge exists; deployment not marked removed | §12 |
| T08 | **Asymmetric sharing claim** | A asserts sharing with B, but B's own export does not list A (or vice versa) | network centrality of both; recency of each export | Both sides' `SharedNetworks` exports from the same window, or an agency statement resolving it | AN/RR | 2 h | Both directions evidenced from the same period, or the asymmetry recorded as a dated `ConfigurationState` disagreement | NEW |
| T09 | **Portal disappeared** | Portal URL that returned 200 for ≥3 prior snapshots now 404/410/DNS-fails for ≥3 consecutive checks | prior camera count; whether an accountability event preceded it | Archived last-good snapshot + a dated statement or record explaining removal | JO/RR | 1 h | `Portal` marked `ended` with a dated cause, and the last-good snapshot archived | NEW |
| T10 | **Portal appeared with no known deployment** | New portal discovered for an org that has no `Deployment`, no contract, no mapped devices | camera count in the new portal | Contract or council record establishing when the deployment began | RR | 1 h | Deployment node created with a start date backed by evidence | NEW |
| T11 | **Contract expiring within 90 days, no renewal evidence** | `contract.end_date − now ≤ 90d` ∧ no amendment/renewal/RFP evidence after `end_date − 180d` | days remaining (inverse); contract value; whether a local group holds the queue | Renewal, amendment, non-renewal notice, or an agenda item | RR/LG | 45 m | A dated record covering the post-expiry period exists | NEW |
| T12 | **Device inside jurisdiction A attributed to agency B** | node geometry ∈ jurisdiction A ∧ `operator` = agency whose jurisdiction ≠ A ∧ no interlocal agreement on file | whether B is a federal/state agency; count of such nodes | Interlocal/mutual-aid agreement, ROW permit, or corrected operator | AN/RR | 1.5 h | Either an agreement is linked or `operator` is corrected upstream | NEW |
| T13 | **Retention value changed without a policy change** | `retention_days` claim changed ∧ no `Policy` version change in ±60d | delta size; whether it increased | The configuration change record, event log, or policy revision | RR | 1 h | A dated cause is linked, or the change is marked `unexplained` with both snapshots archived | NEW |
| T14 | **Org in a network list has no jurisdiction** | Org node with sharing edges ∧ `jurisdiction_id IS NULL` | edge count; whether it appears in many exports | Jurisdiction assignment with a source (state registry, ORI, incorporation record) | AN | 30 m | `jurisdiction_id` set with evidence | NEW |
| T15 | **Atlas says ALPR; no portal, no contract, no devices** | Atlas datapoint exists ∧ zero corroborating artifacts of any other kind | Atlas source tier; agency size | Any second independent source, or a documented negative finding that the Atlas datapoint is stale | DR/RR | 1 h | ≥2 independent sources, or Atlas claim marked `unconfirmed_since <date>` | NEW |
| T16 | **Grant awarded, no deployment evidence** | Federal/state grant naming surveillance tech ∧ no deployment within 24 months | grant amount; grant program's reporting requirements | Procurement record, deployment record, or the grant's own closeout report | RR | 2 h | Deployment linked, or grant marked `no_deployment_evidence` with the closeout cited | NEW |
| T17 | **Vendor acquisition requires product re-linking** | Vendor A acquired by Vendor B ∧ products still linked to A ∧ contracts post-date the acquisition | number of affected contracts | The acquisition filing/announcement + a product mapping | AN | 3 h | All post-acquisition products carry `succeeds`/`succeeded_by` edges | NEW |
| T18 | **Claim's only support is Tier E/F** | claim has ≥1 source ∧ `max(tier) ∈ {E,F}` | how many downstream claims depend on it; whether it is publicly displayed | Any Tier ≤D corroboration, or demotion of the claim | DR/RR | 45 m | `max(tier) ≤ D`, or claim visibility reduced to `lead` | NEW |
| T19 | **Claim `unverified` longer than N days** | `status='unverified'` ∧ `age > N(entity_type)` | age; display prominence | Verification or explicit expiry | DR | 20 m | Status ∈ {verified, refuted, expired} | NEW |
| T20 | **Evidence URL now 404s (link rot)** | `EvidenceArtifact.url` HTTP ∈ {404,410,DNS fail} on ≥2 consecutive checks ∧ no local archive copy | number of claims depending on it | A re-archived copy (Wayback, local capture) or a replacement source | AN | 20 m | An archived copy with a hash is attached, or the claim is re-sourced | NEW |
| T21 | **Extraction made by an outdated parser** | `extraction.parser_version < current` ∧ parser changelog marks the delta as semantic | number of affected claims; whether values changed on re-run | A re-run extraction diffed against the old one | AN (automatable) | 10 m | `parser_version = current` and diff reviewed | NEW |
| T22 | **Candidate duplicate entities** | pairwise similarity ≥ threshold ∧ not already merged/split-confirmed | how many claims attach to each; whether they share an external ID | A human merge decision with a recorded rationale | AN | 15 m | Pair marked `merged` or `distinct_confirmed` (never left pending) | NEW |
| T23 | **Court case with no docket link** | `Incident.type='litigation'` ∧ no docket/court-record URL | case prominence; whether cited by others | A docket URL (CourtListener/PACER/state) or the complaint PDF | DR/JO | 30 m | Docket or filing linked and archived | NEW |
| T24 | **Incident supported only by secondary sources** | Incident has no Tier A/B artifact | severity; how widely cited | The primary record: police report, complaint, audit finding, agency statement | RR/JO | 2 h | ≥1 Tier A/B artifact attached | NEW |
| T25 | **Source dormant** | Partner source: DNS fail / 5xx / hash-frozen for ≥ threshold days | how many SIG claims depend on it; whether a mirror exists | Confirmation of status from the maintainer, or an archived snapshot + a dated dormancy note | AN/LG | 30 m | Ledger `health` updated; succession clause evaluated (F12.15 §7) | NEW |
| T26 | **Private-sector participant unresolved** | Sharing/network member is a non-government entity with no entity type or parent | whether it is a HOA, hospital, university, mall, or data broker | Incorporation record, property record, or a public statement | AN | 45 m | `org_type` set with evidence; parent linked if applicable | NEW |
| T27 | **Policy adopted but no configuration evidence** | `Policy` exists asserting a limit (e.g. no ICE sharing) ∧ no `ConfigurationState` evidencing compliance | how strong the policy claim is; public salience | A configuration export, audit log, or event log covering the post-policy window | RR | 1.5 h | Post-policy configuration evidence attached, or gap recorded as `compliance_unverified` | NEW |
| T28 | **Coverage discontinuity at a jurisdiction boundary** | device density on one side of a boundary ≫ the other by >5× with comparable road class | population; whether the low side has a portal | Either newly mapped devices, or documentation that the low side has no deployment | FM/LG | 4 h | Density ratio explained by evidence or by an accepted negative survey | NEW |
| T29 | **Camera count contradicts contract line item** | `contract.device_count ≠ portal.camera_count` beyond tolerance ∧ both dated within 180d | delta; contract recency | An amendment, invoice, or agency statement reconciling the two | RR/AN | 1 h | Difference explained by a dated artifact, or contradiction formally recorded | NEW |
| T30 | **Mapped device with no evidence of current operation** | Device last confirmed >18 months ago ∧ jurisdiction has had a cancellation event | whether a cancellation event exists nearby | A dated photo (present or absent), a removal record, or a portal snapshot | FM/LG | 1.5 h | Device lifecycle state updated with a dated observation | NEW |

**Retrieved:** n/a (design). The *inputs* to T03, T09, T11, T25, and T30 are all evidenced by live
ecosystem behaviour recorded in F12.6 and F12.14.

**Implication for the spec:** 30 rules, ~6 assignee classes, one detector engine. T20, T21, T22, and
T25 are **self-maintenance** tasks — the graph generating work on itself — and they are the ones most
likely to be dropped from an MVP and most likely to be regretted. T08 (asymmetric sharing) is the
highest-signal genuinely-new detector: sharing is asserted by configuration on both ends, so
disagreement is either a stale export or a real, dated configuration change, and both are newsworthy.

**Outline delta:** **EXTENDS §12 from 7 to 30 task types**, and **EXTENDS §6.5** by making
contradiction a *closable outcome* ("contradiction formally recorded") rather than only a state.

---

### F12.20 — Task lifecycle, staleness, deduplication, and abuse controls

**Claim:** The lifecycle needs eleven states, not six, because rule versioning and contributor abuse
both create transitions the naive model cannot express.

**Status:** UNVERIFIED (design artifact)

```
                    ┌──────────────► SUPPRESSED (dup / suppress_if matched)
                    │
GENERATED ──► TRIAGED ──► OPEN ──► CLAIMED ──► IN_PROGRESS ──► SUBMITTED ──► IN_REVIEW
                    │        │         │            │                            │
                    │        │         └── released/expired ──┘                  ├──► VERIFIED ──► CLOSED
                    │        │                                                   └──► REJECTED ──► OPEN
                    │        └──► EXPIRED (auto_expire_days elapsed, no claimant)
                    ├──► INVALIDATED (rule version bumped, or the underlying data changed
                    │                 so the detector no longer fires)
                    └──► WONTFIX (jurisdiction opt-out, safety veto, or duplicate of upstream work)

CLOSED ──► REOPENED (new contradicting evidence arrives, or completion_test regresses)
```

Mechanics:
- **Claiming is a soft lock with a TTL.** Default 14 days for desk tasks, 30 for field tasks;
  auto-release on expiry with a warning at 80%. `CLAIMED` never blocks anyone from *also* working —
  it signals intent and prevents duplicated effort; it does not grant exclusivity (this matters for
  F12.21).
- **Deduplication is by `(rule_id, entity_key)`,** enforced at generation. A second firing updates
  the existing task's priority and evidence set rather than creating a sibling.
- **Cross-rule suppression** via `suppress_if`: don't ask someone to count cameras in a portal that
  just vanished; don't ask for a contract renewal in a city that just cancelled.
- **Rule version bumps invalidate, they do not delete.** Tasks generated by v2 of a rule move to
  `INVALIDATED` with a pointer to the v3 successor, so contributor effort is visibly accounted for.
- **Staleness has two clocks:** task age (drives `EXPIRED`) and *underlying evidence* age (drives
  priority). A task can be young and urgent or old and irrelevant; conflating them produces a queue
  nobody trusts.
- **Anti-abuse controls** (these are the ones the outline omits entirely):
  1. **Rate limits per contributor tier** (F12.31) on submissions, with a lower limit for
     `anonymous_submitter`.
  2. **Evidence-required submission.** A `SUBMITTED` transition without an artifact meeting the
     rule's `required_evidence` is rejected by schema, not by a reviewer.
  3. **Plausibility gates before review** — the exact control DeFlock is now designing under pressure
     (F12.28). Geographic plausibility (is this vendor known to operate in this country?), temporal
     plausibility (does this predate the vendor's founding?), and duplicate-geometry checks.
  4. **Adversarial-submission detection.** Two threat models: *deflationary* (an agency or vendor
     submitting false "removed" evidence) and *inflationary* (an activist submitting cameras that
     don't exist — **already happening in OSM per F12.28**). Both are handled the same way: require
     dated, verifiable evidence; hold the claim at lower confidence; never let one submission flip a
     lifecycle state.
  5. **Trust-weighted review depth.** Submissions from `trusted_reviewer` and above are spot-checked;
     everything else is fully reviewed. Review burden must scale sub-linearly or the queue dies.
  6. **Sybil resistance without identity.** No legal-identity requirement (most of this ecosystem is
     pseudonymous — F12.10). Instead: contribution history, rate limits, evidence quality scoring,
     and per-account review of the first N submissions.
  7. **A "this task is dangerous" veto.** Any contributor may flag a task; flagged tasks go
     `WONTFIX` pending review by a maintainer. Cheap, and it prevents SIG from sending someone
     somewhere they shouldn't go.
  8. **Never publish who claimed what, in real time.** A live "user X is field-mapping in Y" feed is
     a targeting tool. Claims are visible in aggregate and after the fact.

**Outline delta:** **EXTENDS §12 and §15.6** — the outline has no lifecycle, no dedup, and no abuse
model; item 4 in particular is now an observed, not hypothetical, problem (F12.28).

---

### F12.21 — Geographic queues (Q36): claiming a jurisdiction without gatekeeping

**Claim:** A local group can "claim" a jurisdiction, and that claim must confer **visibility,
notification, and priority — never exclusivity.**

**Status:** UNVERIFIED (design), answering **Q36**

**Implication for the spec:**

What a jurisdiction claim *does* grant:
1. **A named queue.** `sig.example/q/us/wi/dane-county` — a stable URL the group can put on its own
   site, showing that jurisdiction's open tasks ranked by priority.
2. **Notification rights.** New tasks in the jurisdiction generate a digest to the group's channel.
   This is the actual value: local groups' comparative advantage is *early detection* (§3.2), and a
   digest is how SIG returns the favour.
3. **Priority weighting.** Tasks in a claimed jurisdiction get a small priority bonus, because a
   claimed queue has a higher probability of closure.
4. **Attribution.** The queue page names the group, links to it, and credits closed tasks to it.
5. **First-look window.** A short, bounded head start (default **7 days**) during which new tasks in
   the jurisdiction are shown to the claiming group before entering the global queue. Bounded, small,
   and automatically expiring.
6. **A dossier.** The §15.1 local dossier for that jurisdiction, rendered and citable.

What it explicitly does **not** grant:
- No veto over anyone else's contribution.
- No approval rights over claims about that jurisdiction.
- No ability to hide, delay, or suppress tasks or evidence.
- No exclusivity after the 7-day window.
- No ownership of the data. All of it stays under the project licence.

Anti-gatekeeping mechanisms — the part that actually determines whether this works:
- **Claims are non-exclusive by construction.** Multiple groups may claim the same jurisdiction. The
  queue lists all of them. Overlap is normal, not a conflict; two DeFlock chapters in the same metro
  is a real configuration (Cleveland has three: DeFlock Lakewood, Flock No Cleveland, IRTF Cleveland,
  Shake Off Flock — four, in fact, per F12.4).
- **Claims lapse.** No closed task and no digest engagement for **120 days** → the claim goes dormant
  and the queue reverts to unclaimed, with a notification first. This prevents dead groups from
  squatting on cities.
- **Anyone can always work any task.** The claim never appears in the authorization path. It is a
  routing and notification construct only, and that must be verifiable in the code.
- **No hierarchy between claimants.** SIG does not designate a "lead" group for a jurisdiction.
- **A right of reply, not of review.** A claiming group can attach a dated public annotation to any
  claim in its jurisdiction ("we surveyed this corridor on <date> and disagree"). That annotation is
  evidence, subject to the same standards, and does not block publication.
- **Escalation is to the editorial board (F12.33), not to the claimant.** Disputes between two groups
  in one jurisdiction go to the board, and the default while a dispute is open is *publish both,
  labelled*, not *publish neither*.
- **Sub-jurisdiction granularity.** Claims can be at state, county, municipality, or campus level
  (KSU ALPRs and UA Transparency in F12.4 are campus-scoped). A state claim must not swallow the
  municipal queues inside it — child queues are separately claimable and a parent claim confers no
  rights over children.

**Outline delta:** **ANSWERS Q36 and EXTENDS §3.3** — the outline asks whether local groups *could*
claim queues; the answer is yes, with lapse, non-exclusivity, and a bounded first-look window as the
three load-bearing constraints.

---

### F12.22 — What makes ALPR records requests succeed: HIBF's proven language and denial-tactics table

**Claim:** HIBF publishes proven ALPR request language, an enumeration of the exact record types
worth asking for, a quotation from Flock's own guidance that defeats "we don't know where our audit
logs are," and a tactic-by-tactic response table. This is the highest-value input to SIG's
records-request generator and the outline does not cite it.

**Status:** VERIFIED

**Evidence:** `https://haveibeenflocked.com/about/audit-logs` (HTTP 200, 74,011 bytes), retrieved
2026-08-20. Verbatim extracts:

*The request language:*
> "I am requesting copies of all audit logs, search logs, or usage reports related to your agency's
> use of Flock 'ALPR' systems for the period of [START DATE] through [END DATE]. This includes but is
> not limited to: Records of license plate searches performed by agency personnel; Timestamps of
> searches; User identification information (names, badge numbers, or user IDs); Any associated case
> numbers or investigation references; A list of network share settings (the networks shared with your
> agency and the networks your agency shares out); Event logs or system activity logs, including
> hotlist and network-sharing changes; Screenshots of relevant configuration settings, including
> network-sharing and live-stream access settings. Some of these records may be available as the
> 'Organization Audit' and 'Network Audit' in the Flock software's 'Insights' section. Please provide
> records in their original electronic format (CSV, Excel, or similar) where possible."

*The four record classes (each a distinct SIG evidence type):*
- **Organization Audit Log** — searches by the agency's own operators. Fields: `ID, Name, Org Name,
  Camera Count, Time Frame, License Plate, Reason, Case #, Filters, Search Time, Search Type, Text
  Prompt, Moderation`.
- **Network Audit Log** — searches by *other* agencies via sharing. Same fields, with `Name` and
  `License Plate` redacted to `***`.
- **Portal / Public Audit Log** — "heavily redacted … only user UUIDs (not officer names), search
  dates, camera counts, and reasons." Fields are "Variable (agency-configured)."
- **Network Sharing (`SharedNetworks.csv`)** — *"a configuration export, not a record of searches: it
  shows the sharing relationships in place at the moment the file was generated."* Columns:
  `Organization Name, Networks Shared With Me, Networks I'm Sharing`. **This is the direct source for
  §8.8 `AccessRelationship` edges and for detector T08.**
- **Event Logs** — `Timestamp, User, Event Type, Entity Type, Entity Details, Event Id`, where
  Event Type ∈ {`create`,`update`,`delete`} and Entity Type names "a hotlist entry, a network share,
  a user, a camera, or a live-stream view." **This is the direct source for §8.12 `ConfigurationState`
  transitions and for detector T13.**
- **Configuration Settings** — *"not a file you download — they live on the settings pages of the
  Flock admin dashboard. Agencies typically provide them as screenshots, so ask for them specifically."*

*The unlock for "we don't know where our logs are"* — HIBF quotes Flock Safety's own
*Guide to Flock Safety Data for Open Records Laws* (Sept. 3, 2025):
> "The audit logs can be accessed via your agency's Flock admin dashboard on the 'Insights' tab. …
> Customers may download these logs in the user interface as spreadsheets in 31-day increments."

*And the adversarial context, from the same vendor guide:*
> "Agencies should consider whether to redact license plates, search reasons, and case numbers from
> these logs … Agencies should also consider negotiating a narrowed timeframe and whether they are
> entitled to payment of an upfront fee."

*The denial-response table (HIBF's, reproduced):*

| Agency tactic | HIBF's recommended response |
|---|---|
| Stalling, delays | "Check legally required timelines beforehand and include them in your original request. Follow up regularly." |
| Willful ignorance | "Provide the snippet from Flock's documentation, and refer the agency to Flock for further support." |
| Excessive redaction | "Ask for a specific legal basis for each redaction. Generally, license plates, case numbers, and names of government officials are not exempt … Check what the agency has released before." |
| "Jeopardize ongoing criminal investigation" | "Exemptions … generally apply only to existing investigations, not to anything that could contain information about possible investigations. Ask for the specific legal basis for withholding." |

HIBF also exposes a per-agency **"Fields Seen"** tab showing what that agency has previously
released, *"both direct releases … and indirect ones (records of the agency's searches released by
other agencies)."*

**Retrieved:** 2026-08-20

**Implication for the spec:** The **"Fields Seen"** idea is the single most transferable mechanism
here and SIG should generalize it: for each agency, maintain a **disclosure precedent record** —
which record classes that agency (and its peer agencies, and other agencies under the same statute)
has previously released, redacted, or refused, with dates. The generator then (a) asks for what has
been released before, (b) pre-empts the specific exemption that agency has used before, and (c) cites
the precedent. This converts every SIG-tracked request outcome into an asset for the next requester
— a compounding return that no individual group can build alone. **This is the concrete mechanism
by which SIG "makes other projects stronger" (§22.6).**

**Outline delta:** **EXTENDS §12 and §10 Phase 1F** — the outline never names the six Flock record
classes, and the `SharedNetworks.csv` / Event Log distinction is load-bearing for §8.8 and §8.12.
**EXTENDS §22.6** with the disclosure-precedent mechanism.

---

### F12.23 — Prior art: a local group has already built the records-request generator

**Claim:** DeFlock Dane has a working, statute-grounded public-records drafting tool with escalation
letters — the exact artifact §12 implies SIG should build — and SIG should adopt its structure rather
than reinvent it.

**Status:** VERIFIED

**Evidence:** `https://deflockdane.org/wisconsin-open-records-request-tool/` (HTTP 200, 142,218 bytes).
Verbatim: *"Use this tool to draft a stronger Wisconsin public records request. It is MuckRock-informed:
it helps you narrow the request, name likely record types and custodians, add search terms, and ask
for records in useful formats."* and *"Everything is grounded in Wisconsin's Public Records Law
(Wis. Stat. §§ 19.31-19.39). This tool does not send anything automatically. You copy or download the
text and send it yourself."*

Its input model, captured verbatim:
- **Parties:** requester name/email; *"Agency / Department — Use the specific office most likely to hold the records."*
- **Scope:** date range; request type ∈ {Contracts/Procurement, Policies/Training, Logs/Searches/Audits, Emails/Attachments, Data Sharing/Access, Custom}.
- **Record categories** (multi-select): Contracts, Amendments, Invoices, Purchase orders, Policies, Training materials, Audit logs, Search logs, Access logs, Emails, Attachments, Data sharing agreements, Retention policies, Vendor correspondence.
- **Likely offices / custodians:** Records officer, Chief or command staff, Procurement, IT or system administration, Legal or clerk staff, Vendor manager.
- **Search terms** and **specific identifier** free-text.
- **Delivery/legal preferences:** maximum cost; format ∈ {Email attachment, Native electronic files, PDF, CSV/spreadsheet}; optional clauses = {include attachments to responsive emails, request associated metadata, add non-commercial/public-interest language, ask for segregable non-exempt portions, ask for rolling production, **request preservation of responsive records as of the request date**}.
- **Escalation mode** ("Respond to the agency"): choose from {has not responded/overdue, quoted a fee that seems too high, denied citing an exemption (security/law enforcement), says no records exist, says the request is too broad/burdensome, redacted without justification} → *"Each choice generates a response letter grounded in the specific Wisconsin statute that applies."*

**Retrieved:** 2026-08-20

**Implication for the spec:** SIG's generator should be **this tool, generalized to 51 jurisdictions
and driven by a research gap instead of a form.** Three of its design choices should be copied
outright: (1) **it does not send** — the human sends, which sidesteps the entire question of SIG
filing requests in someone's name; (2) **the preservation clause** as a default option, which is
cheap and protects the record; (3) **the escalation-letter generator**, which is where most requests
actually die and which nobody else automates. SIG's addition is the *gap → request* mapping and the
disclosure-precedent data (F12.22).

**Outline delta:** **EXTENDS §12** — the outline does not contemplate a records-request generator at
all; §12 stops at "Task: find contract/invoice/council approval."

---

### F12.24 — MuckRock is programmatically usable, including request filing, under a UA contract

**Claim:** MuckRock exposes an authenticated v2 API that can file FOIA requests, and its state
public-records guides are scrapable with an identifying user agent — which is how the F12.26 table
was built.

**Status:** VERIFIED

**Evidence:**
- `https://www.muckrock.com/api/` — base `https://www.muckrock.com/api_v2/`; auth via MuckRock
  Accounts tokens from `https://accounts.muckrock.com/api/token/`, access token valid **5 minutes**,
  `Authorization: Bearer <key>`, refresh at `https://accounts.muckrock.com/api/refresh/`. Eight
  object types: **requests, communications, files, agencies, jurisdictions, users, organizations,
  projects**. Filing: authenticated `POST /requests/` with `agencies` (array of IDs), `title`,
  `requested_docs`; **"Filing consumes from your account's request quota; requests without purchased
  allocation become drafts."** Rate limits: **15 req/min with bursts to 100**; users and organizations
  endpoints **5 req/min, no burst**. Terms: *"All API requests require an identifiable user agent in
  the headers that uniquely identifies your automation and includes a real point of contact. Generic
  or browser user agents face blocking."*
- **Confirmed empirically:** `https://www.muckrock.com/` returns **403 Cloudflare** to a Chrome UA
  and **HTTP 200** to `SIG-Research/0.1 (surveillance-infrastructure-graph research; contact: …)`.
  All 51 state guides fetched successfully under that UA at ~1 req/1.2 s.
- **Assignments** (crowdsourcing): *"more than 1,300 volunteers have helped comb through 16,000 pages
  of documents across over a hundred different projects"*; responses reviewable, exportable as CSV,
  with real-time search and flagging; *"creating new Assignments is available to Pro and Organization
  users, and anyone can complete Assignment tasks."*
  (`https://www.muckrock.com/news/archives/2019/apr/17/RJIF-assignments/`)
- ALPR Watch documents using the API in production: *"MuckRock provides an API for getting data from
  their site, so we start by fetching all documents related to FOIA requests … you can retrieve an
  updated version yourself using `python foia.py pull`."*
  (`https://alprwatch.org/news/2025-07-28_flock_foia/`)

**Retrieved:** 2026-08-20

**Implication for the spec:** **SIG should not file requests on contributors' behalf by default.**
The quota is per-account and paid; auto-filing would spend someone's money and put SIG's name on a
legal instrument it cannot follow through on. The correct design is *deep-link handoff*:

```
SIG task T02 (missing contract, Dane County WI)
  → generator renders the request body + statute citation + custodian
  → "File this on MuckRock" button → prefilled MuckRock draft under the CONTRIBUTOR's account
  → SIG records {muckrock_foia_id, filed_at, filed_by_tier} on the task
  → SIG polls GET /requests/{id} + /communications/ for status and files
  → responsive files land in DocumentCloud → SIG ingests as EvidenceArtifact with the FOIA id as provenance
  → completion_test re-evaluates → task closes automatically
```
Only for SIG's *own* institutional account (with its own quota, its own name, and a human approving
each filing) should the `POST /requests/` path be used, and then with a hard rate cap and a public
log. MuckRock Assignments is the right home for T15/T17/T25/T27-class **document-review** tasks that
SIG generates but cannot host at scale.

**Outline delta:** **ANSWERS Q35 and Q7** (partially — redistribution terms belong to the licensing
workstream) and **EXTENDS §18** — the MuckRock row should read "primary evidence substrate **and
task execution surface**."

---

### F12.25 — The records-request generator design

**Claim:** Given a research gap, SIG can emit a ready-to-file request with the right agency, the
right statutory citation, and proven language.

**Status:** UNVERIFIED (design), built on the verified inputs in F12.22–F12.24 and F12.26

**Implication for the spec — the generator's inputs and output:**

```
INPUT   task {rule_id, org_id, jurisdiction_id, gap_description, required_evidence}
LOOKUP  1. jurisdiction → state → FOIA statute row (F12.26): name, citation, deadline, fee rule,
           residency restriction, appeal body
        2. org → custodian: records officer contact, from (a) SIG's own agency contact table,
           (b) MuckRock `GET /agencies/`, (c) the agency website — in that order, with provenance
        3. org → disclosure precedent (F12.22): record classes previously released / redacted /
           refused by THIS agency, then by peer agencies in the same state
        4. rule → record-class template: which of the six Flock record classes (F12.22) the
           required_evidence maps to
OUTPUT  a rendered request containing, in order:
        · addressee + custodian title
        · the statutory invocation, with the state's exact statute name and citation
        · residency assertion where the state restricts it (AL, AR, DE, KY, TN, VA — F12.26)
        · the record-class enumeration, using HIBF's proven language for audit/config classes
        · a date range narrowed to the gap (never "all records, all time")
        · format preference: native electronic, CSV/XLSX
        · the segregability clause, the preservation clause, and the fee cap
        · the statutory response deadline, quoted, with the date it falls on
        · the pre-emption paragraph: if the agency previously invoked exemption X, cite the
          precedent and ask for the specific legal basis in advance
        · the Flock-documentation snippet where the class is audit logs (F12.22)
SIDE    creates a `RecordsRequest` node linked to the task, with a deadline timer that fires
        an escalation task on the statutory date + 1
```

The escalation ladder, generated from the same data (adopting DeFlock Dane's six cases, F12.23):
overdue → fee too high → exemption denial → "no records exist" → "too broad/burdensome" →
unjustified redaction. Each renders a letter citing that state's statute, and — where the state has
one — names the administrative appeal body (Illinois Public Access Counselor, DC Mayor's office,
Texas AG pre-appeal, Connecticut FOI Commission), which is dramatically cheaper than litigation.

**Safety and honesty constraints:**
- The generator **never sends**. It renders text; a human sends it (F12.23).
- It must state plainly that it is not legal advice, mirroring HIBF's disclaimer.
- It must not fabricate a statutory citation. If the jurisdiction row is incomplete, it emits the
  request without the citation and flags the gap, rather than guessing.
- Federal agencies use FOIA (5 U.S.C. § 552) and a different template; the table below is **state**
  law only.

---

### F12.26 — Per-state public-records statute reference table (51 jurisdictions)

**Claim:** The following is a complete 51-jurisdiction reference table of statute name, citation,
initial response deadline, fee rule, and residency restriction, built from MuckRock's state guides.

**Status:** VERIFIED as an accurate transcription of MuckRock's guides; **PARTIALLY VERIFIED** as a
statement of current law — these are MuckRock's summaries, not primary statutory text, and several
guides carry no "last updated" date. Every deadline and fee cell below is a condensation of the
guide's own answer to "How long do they have to respond?" and "…Fees?"

**Evidence:** 51 pages fetched 2026-08-20 from `https://www.muckrock.com/place/united-states-of-america/<state>/`
with `User-Agent: SIG-Research/0.1 (…; contact: …)`, all HTTP 200 (87.7–104.9 KB each). Statute name,
short name, citation, and "Enacted in …" were parsed from the `law__name` / `law__citation` /
`law__summary` elements; deadlines and fees from the "The Details" Q&A block. Citation links (where
the guide provides one) are preserved in the scrape. Cross-check source for corrections:
RCFP Open Government Guide, `https://www.rcfp.org/open-government-guide/` (200), corrections to
`guides@rcfp.org`.

**Retrieved:** 2026-08-20

| State | Statute (name) | Citation | Initial response deadline | Fee rule (abbrev.) | Non-resident may file? |
|---|---|---|---|---|---|
| Alabama † | Alabama Open Records Law (AORL) | `Ala. Code §§ 36-12-40 to -46`, as rewritten by the 2024 amendments | 10 business days to acknowledge; 15 business days to substantive response after acknowledgment; presumed denied at 30 business days or 60 calendar days, whichever is earlier (§ 36-12-44(a)(3)–(5)) | Cost recovery; waiver permitted for "standard" requests needing <8 staff-hours (§ 36-12-44(a)(2)); advance payment required for "time-intensive" requests | **No — Alabama residents only; "reasonable evidence" of residency may be demanded (§§ 36-12-43(b)(3), -44(f))** |
| Alaska | Alaska Public Records Act (PRA) | `AS § 40.25.110 et seq.` | 10 working days (2 AAC 96.325(a)) | Copy cost only; standard unit cost cap | Yes |
| Arizona | Arizona Public Records Law (PRA) | `A.R.S. §§ 39-101 to -161` | None; "promptly" per case law | Permitted; A.R.S. §39-121.02 | Yes |
| Arkansas † | Arkansas Freedom of Information Act (FOIA) | `Ark. Code Ann. §§ 25-19-101 to 25-19-109` | 3 working days | Reproduction only; no search/retrieval fee; waiver/reduction for noncommercial public-interest requests (§ 25-19-105(d)(3)(A)(iv)) | **No — "any citizen of the State of Arkansas" (§ 25-19-105(a)(1)); corporations doing business in-state count** |
| California | California Public Records Act (PRA) | `Cal. Gov't Code, Chapter 3.5 Inspection of Public Records` | 10 days to determine; inspection during business hours (Gov. Code §6253) | Direct cost of duplication only | Yes |
| Colorado † | Colorado Open Records Act (CORA) | `CRS 24-72-200` et seq. | No production deadline, but "reasonable time" is **presumed to be 3 working days**, extendable to 7 only on a written extenuating-circumstances finding delivered inside the 3 days (§ 24-72-203(3)) | $0.25/pg; no e-copy dup fee; research fee after 1st hour; discretionary waiver for public purpose incl. journalism, on computer-output records (§ 24-72-205(4)) | Yes |
| Connecticut | Connecticut Freedom of Information Act (FOIA) | `Conn.Gen.Stat.§1-200 et seq` | 4 days to grant/deny | $0.25/pg state, $0.50/pg other agencies | Yes |
| Delaware † | Delaware Freedom of Information Act (FOIA) | `29 Del. C. § 10001 et seq.` | 15 business days, or a cited reason plus a good-faith estimate (§ 10003(h)(1)) | "Reasonable expense of copying"; agency-set rules; agency policy may provide class-based waivers (§ 10003(m)(2)) | **No — Delaware citizens (incl. corporate citizens) only; Del. Op. Att'y Gen. 96-ib01 holds non-Delaware citizens may not request** |
| District of Columbia | DC Freedom of Information Act (FOIA) | `Code §§ 2-531-539` | 15 business days; appeal 10 business days (D.C. Code §2-532) | Schedule at 1 DCMR §408 | Yes |
| Florida | Florida Sunshine Law (SL) | `Florida Statutes, Title X, Chapter 119` | None; "unreasonable delay" = denial | $0.15/pg 1-sided, $0.20 2-sided, $1 certified; special-service charge | Yes |
| Georgia | Georgia Open Records Act (ORA) | `Georgia Law § 50-18-70` | 3 business days | $0.10/pg; admin/search cost after 1st 15 min | Yes |
| Hawaii | Hawaii Uniform Information Practices Act (UIPA) | `Chapter 92F, Hawaii Revised Statutes` | Formal: 10 business days to notice; informal: "reasonable" | ≥$0.05/pg; $2.50/15 min search; $5.00/15 min review-segregation | Yes |
| Idaho | Idaho Public Records Act (PRA) | `Idaho Code §§ 74-101` | 3 working days (extendable to 10) | Labor cost only if >100 pages or redaction needed | Yes |
| Illinois | Illinois Freedom of Information Act. (FOIA) | `(5 ILCS 140)` | 5 business days (7 enumerated extension grounds) | No fee if agency misses 5-day deadline; first 50 pages free | Yes |
| Indiana | Indiana Access to Public Records Act (APRA) | `Ind.Code Ann. 5-14-3-1 to 10` | 7 days (24 h if in person) | No fees except "reasonable" e-inspection fee (§5-14-3-8) | Yes |
| Iowa | Iowa Open Records Law (ORA) | `Iowa Code Ann. 22.1 to .14` | "Should not exceed" 20 calendar days; ordinarily 10 business days (§22.8(4)(d)) | "Reasonable" reproduction; no statutory search fee | Yes |
| Kansas | The Kansas Open Records Act (ORA) | `Kan.Stat.Ann 45-215 to 225` | 3 business days | Actual employee search + copy cost | Yes |
| Kentucky † | Kentucky Open Records Act (ORA) | `Ky. Rev. Stat. Ann. 61.870 to .884` | 5 business days | Copy cost only for noncommercial; no search fee; **no waiver provision** (94-ORD-90 denied a reporter's waiver) | **No — only Kentucky "residents" as defined at KRS 61.870(10) hold an enforceable right; a non-resident may ask and may be granted records but cannot enforce. The definition includes anyone employed in KY, owning KY property, or acting for a news-gathering organization** |
| Louisiana † | Louisiana Public Records Law (PRL) | `Louisiana Revised Statutes Title 44` | 5 business days to respond (La. R.S. § 44:32) | "Reasonable" duplication; after-hours inspection fee; waiver/reduction for indigent requesters and for public-purpose use (§ 44:32(C)(2)) | Yes — but the requester must be a **person of the age of majority** (§ 44:31), and a 2024 act restricts records **of the Governor's office** to Louisiana residents |
| Maine | Maine Freedom of Access Act (FOAA) | `1 M.R.S §400` | 5 working days to acknowledge; estimate in "reasonable time" | Copies + search time ≤$15/hr (1 M.R.S. §408-A) | Yes |
| Maryland | Maryland Public Information Act (PIA) | `Md. Ann. Code art. GP, § 4-101` | 30 days (per AG guidance) | "Reasonable fees" at actual cost; first 2 hours free | Yes |
| Massachusetts | Massachusetts Public Records Law (PRL) | `Massachusetts General Laws, Part 1, Title X, Chapter 66` | 10 business days (G.L. c.66 §10) | Actual search expense (G.L. c.66 §10(b)) | Yes |
| Michigan † | Michigan Freedom of Information Act (FOIA) | `MCL 15.231 et seq.` | **5 business days** (MCL 15.235(2)), extendable once by 10 business days | Statutory itemized fee schedule (MCL 15.234); public-interest waiver where disclosure "primarily benefit[s] the general public" (MCL 15.234(2)) | Yes |
| Minnesota | Minnesota Government Data Practices Act (MGDPA) | `Minn. Stat. Ann. 13.03` | None fixed; "appropriate and prompt manner" | No charge for in-person inspection; e-search chargeable | Yes |
| Mississippi | Mississippi Public Records Act (PRA) | `Miss. Code Ann. 25-61-1 et seq` | 7 days (+7-day extension) | Agency-set "reasonable written procedure" | Yes |
| Missouri † | The Missouri Sunshine Law | `Chapter 610 of the Revised Statutes of Missouri` | 3 business days | Actual labor for search + copying; public-interest waiver/reduction (§ 610.026.1(1)) | Yes under the Sunshine Law (ch. 610); note the **separate** Public Records Law, § 109.180, is Missouri-citizens-only, so cite ch. 610 |
| Montana | Montana Freedom of Information Act | `Mont.Code Ann. 2-6-1` | None specified; delay not recognized as denial | $0.10/pg statewide; first 30 min search free, then $8.50/hr | Yes |
| Nebraska | Nebraska Public Records Act | `Neb. Rev. Stat. §§ 84-712 - 84-712.09` | 4 business days | Actual cost only; free if requester copies on own equipment | Yes |
| Nevada | Nevada Public Records Act | `N.R.S. 239.010` | 5 business days (NRS 239.0107) | Actual cost; ≤$0.50/pg (NRS 239.052) | Yes |
| New Hampshire † | New Hampshire Right to Know Law (RTK) | `New Hampshire RSA Ch. 91-A` | 5 business days to produce, deny, or give a written time estimate with an itemized cost estimate (RSA 91-A:4, IV(b)) | Reproduction cost only; no waiver provision | Yes — RSA 91-A:4 says "every citizen," but RSA 91-A:7 grants "any person" standing, so "citizen" is not read as limiting |
| New Jersey | New Jersey Open Public Records Act (OPRA) | `NJSA 47:1A-1 et seq.` | 7 business days (14 for commercial/redaction) | $0.05–$0.75/pg tiered; e-copies free except medium | Yes |
| New Mexico | New Mexico Inspection of Public Records Act (IPRA) | `14-2-1 NMSA 1978 et seq.` | 15 days (3 days to acknowledge) | Copy cost only; no search fees | Yes |
| New York | New York Freedom of Information Law (FOIL) | `N.Y. Pub. Off. Law Ch. 47 Art. 6 § 84` | 5 business days to acknowledge; ~20 days to produce | Copy cost; search time chargeable after first 2 hours | Yes |
| North Carolina | North Carolina Public Records Law | `G.S. §132-1` | No statutory deadline | Copy fees only unless "extensive labor" | Yes |
| North Dakota | North Dakota Open Records Law | `N.D.C.C. § 44-04-18 et seq, North Dakota Constitution, Article XI, Section 6` | No statutory limit | Permitted | Yes |
| Ohio | Ohio Open Records Law | `Ohio Rev. Code sec. 149.43 et seq.` | None fixed; "promptly" | Actual cost of materials, not labor | Yes |
| Oklahoma | Oklahoma Open Records Act (ORA) | `OK Title 51, Sections 24A.1-30` | None; "prompt, reasonable access" | Direct materials cost ≤$0.25/pg; search fee for commercial | Yes |
| Oregon | Oregon Public Records Law (OPRL) | `Or. Rev. Stat. Ann. 192.410 to .505` | "Reasonable opportunity"; 5/10/15-day scheme via AG guidance | Actual search+copy cost; estimate required over $25 | Yes |
| Pennsylvania | Pennsylvania Right to Know Act (RTK) | `Pa.Cons.Stat.Ann. Tit. 65, 66..1 to .4` | 5 business days | Duplication only; no review or search fees | Yes |
| Rhode Island | Rhode Island Access to Public Records Act (APRA) | `R.I. Gen. Laws 38-2-1 to -14` | 10 business days (extendable to 30) | ≤$0.15/pg; $15/hr search after first hour | Yes |
| South Carolina † | South Carolina Public Records Law | `S.C. Code Ann. 30-4-10` et seq. | **10 business days** to notify of the determination; **20 business days** if the record is more than 24 months old (§ 30-4-30(C)) | Actual search+redaction cost (§ 30-4-30); public-interest waiver/reduction (§ 30-4-30(B)) | Yes |
| South Dakota | South Dakota Open Records Law (SDORL) | `S.D. Codified Laws Ann. 1-25-1 to -19` | 10 business days | Actual mail/transmittal/reproduction; labor after 1 hour | Yes |
| Tennessee † | Tennessee Public Records Act (TPRA) | `Tenn. Code Ann. § 10-7-501 et seq.` | 7 business days | $0.15/pg b&w, $0.50/pg color; first hour labor free; waiver only under a written policy | **No — Tennessee citizens only. The 2008 study committee recommended removing the citizenship requirement and it was retained** |
| Texas | Texas Public Information Act | `Texas Government Code, Title 5, Subtitle A, Chapter 552, Subchapter A` | "As soon as possible"; 10 business days to seek AG ruling | Copies; labor allowed with description (§552.261) | Yes |
| Utah | Government Records Access and Management Act (GRAMA) | `Utah Government Records Access and Management Act 63G-2-201` | 10 business days (5 for media/expedited) | "Reasonable fee to cover actual cost" (63G-2-203) | Yes |
| Vermont | Vermont Public Records Act (PRA) | `1 V.S.A. Sec. 315-320` | 2 business days (extendable to 10) | Actual copy+search cost; search charged after 30 min | Yes |
| Virginia † | Virginia Freedom of Information Act (FOIA) | `§ 2.2-3700` et seq. | 5 working days, +7 work days on a written impossibility response (§ 2.2-3704(B)) | Actual cost of access, search, duplication (§ 2.2-3704(F)); no statutory waiver provision | **No — "citizens of the Commonwealth" plus media circulating in or broadcasting into Virginia (§ 2.2-3704(A)); upheld in _McBurney v. Young_, 569 U.S. 221 (2013). A Virginia citizen may file on a non-citizen's behalf** |
| Washington | Washington Public Records Act | `Wash. Rev. Code Ann. 42.56.001 to .904` | 5 business days | No search fees; $0.15/pg copy | Yes |
| West Virginia | West Virginia Freedom of Information Act (FOIA) | `W.Va. Code§ 6-9A-1` | 5 days (excl. weekends/holidays) | Reproduction only; no search fee | Yes |
| Wisconsin | Wisconsin Open Records Act (ORA) | `Wis. Stat. Ann. 19.31 to .39` | "As soon as practicable and without delay" (§19.35(4)(a)) | "Actual, necessary and direct cost of reproduction" (§19.35(3)(a)) | Yes |
| Wyoming | Wyoming Public Records Act | `W.S. §16-4-201 through 16-4-205` | No set deadline (7/30-day scheme in practice) | Actual materials cost, not labor | Yes |

† **Cell re-checked against primary statutory text or the RCFP Open Government Guide on 2026-08-20.**
All 51 RCFP state guides (`https://www.rcfp.org/open-government-guide/<state>/`) were fetched, HTTP 200,
and the "1. Status of requester," "B. How long to wait / 1. Statutory … time limits," and
"3. Provisions for fee waivers" sections were read for every jurisdiction. Where the primary text was
directly reachable it was read too: `https://law.lis.virginia.gov/vacode/title2.2/chapter37/section2.2-3704/`,
`https://delcode.delaware.gov/title29/c100/index.html`, `https://gc.nh.gov/rsa/html/VI/91-A/91-A-4.htm`,
`https://www.scstatehouse.gov/code/t30c004.php`,
`https://www.legislature.mi.gov/Laws/MCL?objectName=mcl-15-235` (all 200).

**Nine cells were materially wrong in the MuckRock transcription and are corrected above:**

- **Alabama** — the largest error. MuckRock's guide describes pre-2024 law. The 2024 amendments added a
  real timetable (10 business days to acknowledge, 15 to substantively respond, presumed denial at 30
  business days / 60 calendar days) **an express residency requirement with a proof-of-residency demand right**
  (§§ 36-12-43(b)(3), -44(f)) — where the prior statute said only "every citizen," a limitation the
  Supreme Court noted in passing in *McBurney v. Young*. Alabama now has hard deadlines and an
  enforceable residents-only rule, and the table recorded neither.
- **Michigan** — "none fixed; promptly" is wrong; MCL 15.235(2) has required a response within 5 business
  days since 1996.
- **South Carolina** — the 10/20-day rule was inverted. It is 10 business days for records ≤24 months old
  and **20** for older ones, not "15 (10 if ≤24 months)."
- **Colorado** — "no fixed limit" understates it; § 24-72-203(3) presumes 3 working days and requires a
  *written* extenuating-circumstances finding, delivered inside those 3 days, to reach 7.
- **Delaware, Tennessee** — recorded as unknown (`?`); both are residency-restricted.
- **Louisiana, Missouri, New Hampshire** — recorded as unknown (`?`); none is residency-restricted,
  though Louisiana requires the requester to be of the age of majority and restricts Governor's-office
  records to residents, and Missouri's *other* records statute (§ 109.180) is citizens-only.
- **Kentucky** — "No" is right but blunt: non-residents may request and be granted records, they simply
  cannot enforce, and KRS 61.870(10)'s "resident" definition is broad enough to include anyone employed
  in Kentucky, owning Kentucky property, or acting for a news-gathering organization.

**Summary of the table, as the generator must consume it:**

- **Six jurisdictions restrict who may file: Alabama, Arkansas, Delaware, Kentucky, Tennessee, Virginia.**
  Virginia and Alabama are the sharpest — Virginia's limit was upheld against a Privileges and Immunities
  challenge in *McBurney v. Young*, 569 U.S. 221 (2013), and Alabama lets the custodian demand a driver's
  licence or voter registration. Two of the six have workable escape hatches the generator must know
  about: Virginia expressly permits a citizen to file **on behalf of** a non-citizen, and Kentucky and
  Virginia both count a news-gathering organization or in-state-circulating media outlet as qualified.
  Arkansas and Delaware extend "citizen" to corporations doing business in the state, which is a route for
  an incorporated partner but not for an out-of-state individual. **Alabama and Tennessee have no route at
  all** short of a resident filer, and Alabama is the only one that lets the custodian demand documentary
  proof.
  This is why F12.21's jurisdiction queues matter operationally rather than socially: in six states, a
  records task is not assignable to an arbitrary volunteer, and the queue is the routing mechanism that
  finds someone who can lawfully file.
- **Response deadlines span from 2 business days to indefinite.** The tightest is Vermont (2 business
  days, extendable to 10); the loosest enumerated is Maryland (30 days). **Twelve jurisdictions have no
  enforceable statutory deadline at all** — Arizona, Colorado (a presumption only), Florida, Iowa,
  Minnesota, Montana, North Carolina, North Dakota, Ohio, Oklahoma, Texas, and Wisconsin — where the
  standard is "promptly," "as soon as practicable," or "a reasonable time." For those twelve the
  generator cannot quote a date, and the escalation ladder's first rung ("overdue") has no trigger; it
  must instead cite the reasonableness standard and the case law the state guide names, and the
  `RecordsRequest` deadline timer must be `null`, not a guessed default. Guessing a deadline for Florida
  and then accusing an agency of lateness is the fastest way to burn SIG's credibility with a custodian.
- **Twenty-six jurisdictions have an express fee-waiver or fee-reduction provision reachable by a
  public-interest requester**; 25 have none. Twenty-one have it in statute or binding rule on
  public-interest grounds directly (AK, AR, CT, DC, HI, ID, IL, LA, ME, MD, MA, MI, MO, OK, OR, PA, SC,
  SD, TX, UT, WI); five more have it only conditionally — Colorado (computer-output records only),
  Nevada and Washington (only if the agency has adopted a written policy or rule), Delaware (only if the
  agency's own policy provides, and only class-wide), and Rhode Island (only by court order). Connecticut, Hawaii and Idaho are the three states where the waiver is **mandatory** rather than
  discretionary once the facts are established. Alabama's waiver exists but is keyed to effort (<8 staff-hours), not to public interest.
  The generator should therefore emit the waiver paragraph in 26 jurisdictions with the exact statutory
  hook, and in the other 25 emit a fee **cap** instead — because in a no-waiver state the only working
  cost control is "do not incur charges above $X without contacting me first."
- **Hardest states for ALPR records specifically** — this is a different question from "hardest FOIA
  state," and it is the ranking the task generator's priority formula should use:
  1. **Alabama** — residency-restricted, proof demandable, and a 30-business-day presumed-denial clock
     that starts only after acknowledgment. A denial by silence is structurally cheap for the agency.
  2. **Tennessee and Delaware** — citizens-only with no media or agent carve-out stated, so a national
     volunteer cannot file at all and there is no fee-waiver route.
  3. **Virginia** — residency-restricted, no statutory fee waiver, and § 2.2-3704(F) permits charging for
     *access, search and duplication*, which is the combination that produces the four-figure ALPR
     audit-log estimates that kill requests.
  4. **Kentucky** — no waiver provision at all, confirmed by 94-ORD-90 denying a reporter's waiver, and
     ALPR audit logs are exactly the high-page-count product that a no-waiver rule prices out.
  5. **Florida, Ohio, North Carolina, Iowa, Minnesota, Montana, North Dakota** — no deadline plus, in
     Florida's case, a "special service charge" for extensive IT resources, which is precisely how an
     audit-log export gets billed. Nothing here is refused; it is simply never produced.
  6. **New Mexico** — the only state where the guide reports fee waivers may be *constitutionally*
     unavailable (Anti-Donation Clause, N.M. Const. art. IX, § 14).
  Conversely, the cheapest ALPR-records jurisdictions are Illinois (5 business days, first 50 pages free,
  fees forfeited if the agency misses the deadline, plus a Public Access Counselor), Washington (no search
  fees), Idaho and Hawaii (mandatory public-interest waivers), and Connecticut (mandatory waiver on a
  general-welfare finding plus the FOI Commission as a cheap appeal body).

**Implication for the spec:** The jurisdiction row is not decoration on a rendered letter; it is a
**precondition on task assignment**. Three fields of it are load-bearing and must be modelled as
first-class, testable data rather than as template text:

1. `requester_eligibility ∈ {any, resident_only, resident_or_agent, resident_or_media}` — consumed by the
   task router, which must refuse to route a `records_requester` task in AL, AR, DE, KY, TN or VA to a
   contributor with no declared standing in that state, and must instead offer the local-group queue.
   SIG must **never** generate a letter asserting residency on a requester's behalf; the assertion is the
   requester's and the generator renders it only when the requester has affirmed it.
2. `response_deadline` as a structured `{value, unit ∈ {business_days, calendar_days, working_days},
   basis ∈ {statutory, regulatory, ag_guidance, case_law, none}, extension}` — never a string, and never
   defaulted. `basis: none` disables the overdue rung of the escalation ladder.
3. `fee_waiver` as `{available: bool, mandatory: bool, ground, citation, conditions}` — drives whether
   the letter contains a waiver request or a cost cap.

Every one of the fifty-one rows must additionally carry `verified_against ∈ {muckrock_guide,
rcfp_guide, primary_text}` and `verified_at`, because this file has just demonstrated that a
secondary-summary row can be four years stale on a question (Alabama residency) that determines whether
a request is lawful at all. The FOIA reference table is therefore itself a SIG source with a health
check and a staleness task (T04 applied to the ruleset, not the graph), re-verified annually against RCFP
and on any observed legislative change.

**Outline delta:** **EXTENDS §12 and ANSWERS the operational half of Q35.** The outline contemplates
tasks that say "file a records request" without noticing that in six states the request is void unless
the filer lives there, or that in twelve states there is no deadline to enforce. It also **CORRECTS**
the implicit assumption in §15.6 that a task queue is jurisdiction-agnostic: for the
`records_requester` class it cannot be.

---

# Part D — Contribution back (§22.6, Q33, Q34)

### F12.27 — OSM's Organised Editing Guidelines govern any SIG→OSM contribution, and they are procedural, not permissive

**Claim:** Any SIG-coordinated editing of OpenStreetMap falls inside the OSMF's Organised Editing
Guidelines, which require a named wiki activity page, a changeset hashtag, open/public/archived
communication, a community post at least two weeks before starting, and a two-working-day response SLA
to other contributors — and non-compliance is enforced through reverts of the edits, not through a
permission system.

**Status:** VERIFIED

**Evidence:** `https://osmfoundation.org/wiki/Organised_Editing_Guidelines` (HTTP 200, 44,753 bytes),
"Approved November 2018." Scope: *"apply to any edits that involve more than one person and can be
grouped under one or more sizeable, substantial, coordinated editing initiatives."* Required wiki page
`[[Organised Editing/Activities/Name of the Activity]]` recording *"the coordinating person or
organisation … a way to contact the organiser … a unique hashtag to be used in the changeset comments …
the goal of the activity … the timeframe … any non-standard tools and data sources used, and their usage
conditions … plans for a 'post-event clean up' to validate edits."* Communication: *"All related
communications should use channels that are open (no non-OpenStreetMap registration required), public,
and archived."* Notice: *"This should be done no less than two weeks before the activity is started …
An explicit go-ahead from the community is not required, and implicit consensus or even silence is
enough. Ignoring justified criticism and pressing on regardless can, however, lead to an activity being
stopped and reverted."* Response SLA: *"Messages should be answered within two working days while the
activity is ongoing, and responses should actually answer any questions and not just say 'thank you'."*
The wiki mirror (`https://wiki.openstreetmap.org/wiki/Organised_Editing_Guidelines`, 200, last edited
2026-03-17) adds the DWG's enforcement position: *"The Data Working group will intervene for edits the
community has issues with, and [we] will not intervene for merely not following the guidelines."*

**Retrieved:** 2026-08-20

**Implication for the spec:** SIG's contribution-back path to OSM must be built as a **declared organised
editing activity from day one**, not retrofitted once volume appears. Concretely:

- A wiki activity page under `Organised Editing/Activities/` is a **release artifact**, generated from the
  collaboration ledger (F12.16) so it cannot drift from what SIG actually does.
- Every SIG-originated changeset carries a fixed hashtag (`#sig-alpr`) plus `created_by` identifying the
  tool and version. A changeset without the hashtag is a bug that CI can detect on the edit path.
- The two-week pre-announcement is a **pipeline gate**, mechanically identical to the Stage 0 gate in
  F12.11: the OSM write adapter refuses to run until the ledger records a community-post URL older than
  14 days.
- The two-working-day reply SLA needs a named human, not a bot. SIG must not open an OSM contribution
  path it cannot staff, and the guidelines say so explicitly.
- Silence is consensus **here** — the opposite of SIG's own Stage 0 default (F12.11), where silence means
  link-only. The asymmetry is deliberate and must be documented, because an engineer who learns one rule
  will apply it in the wrong direction.

**Outline delta:** **EXTENDS §22.6 and ANSWERS Q33** — the outline says corrections should flow upstream
but does not name the regime that governs the largest upstream. It also **CORRECTS** an implicit
assumption that upstream contribution is a purely technical integration; it is a governance commitment
with a staffing cost.

---

### F12.28 — The inflationary-vandalism problem SIG must defend against is live in OSM right now, and the ecosystem is patching it in the open

**Claim:** As of 2026-08-17 the OSM community is actively dealing with fabricated Flock ALPR nodes across
Canada, Germany, Poland, the UK and Northern Ireland, is discussing bot-removal, and both DeFlock and its
Canadian fork are shipping plausibility and provenance warnings in response.

**Status:** VERIFIED

**Evidence:** `https://community.openstreetmap.org/t/unverified-flock-cameras-causing-mass-panic/146534.json`
(HTTP 200, 69,701 bytes; topic created 2026-08-17, 20 posts, 376 views). Verbatim, by author:

- `022` (opener): *"some anonymous users have begun adding these 'flock cameras' to various points in
  Canada (despite there being no clear evidence that flock is installing any infrastructure here)."*
- `whb`: *"Several new mappers have also emerged in Germany who have recorded non-existent Flock
  cameras,"* citing changesets 184153334 and 186342300.
- `Mateusz_Konieczny`: *"I see 45 supposed Flock cameras in Poland, many in extra-dubious locations like
  inside shopping mall or on courtyard of apartment building,"* filing `FoggedLens/deflock` issue #142;
  and *"I would rather start autoremoving them with a bot if editor author will not do anything to stop
  clearly bogus edits."*
- `rskedgell`: a UK example on *"a dome camera on a wall next to a convenience store on a pedestrian
  walkway"* (node 13965692101), referencing DeFlock issue #124, and the general fix: *"If they don't fix
  their app so that country-specific tags are restricted to the countries where they apply…"*
- `VictorIE`: a Northern Ireland node *"inside a church"* plus *"a gun-shot detector outside the church —
  about 30 years too late for Northern Ireland."*
- `ResistanceIsLiberty` (maintainer of the panopti.ca fork, F12.4): shipping *"Trimming visible nodes so
  the default view only shows confirmed ALPRs … Adding disclaimers that this is community OSM data, not
  vendor or agency sourced, with info on how to fix or dispute a node … Some basic sanity checks to catch
  the obviously-bogus ones,"* and later a per-node flag that *"they have not been officially rolled out in
  Canada"* plus a pre-submit prompt asking the user *"to provide source info before adding the node."*
- `StopFlock` (DeFlock): *"We will be adding new checks to our internal monitoring tool to draw our
  attention to these almost-certainly-incorrect submissions. (We'd love to have more eyeballs on that
  btw). We will be drawing more attention to the crowdsourced data / OSM explainer on our web map on page
  load. And I am going to look at caching admin_levels and possibly some NSI data to inform a new warning
  popup in the DeFlock mobile app."*

**Retrieved:** 2026-08-20

**Implication for the spec:** Four things, and the second is an offer SIG should accept immediately.

1. **The adversarial-submission threat in F12.20 item 4 is observed, not hypothetical**, and its live form
   is *inflationary* — fabricated devices in countries where the vendor does not operate. SIG's
   plausibility gate must therefore include a **vendor operating-territory check** as a first-class rule:
   a claim that vendor V operates a device in country C, where SIG holds no evidence of V operating in C,
   is held at the lowest confidence and generates a verification task rather than entering the graph.
2. **"We'd love to have more eyeballs on that"** is an explicit, dated, public request for help with
   exactly the detector SIG is building anyway. This is the highest-value Stage 0 opening available and
   it should be the first thing SIG offers DeFlock (F12.13), ahead of any data ask: *SIG runs the
   plausibility checks at graph scale and feeds DeFlock's monitoring tool, for free, with no attribution
   required.*
3. **Provenance display is the community's own remedy.** panopti.ca's fix — say plainly that this is
   community OSM data, not vendor or agency data, and show how to dispute a node — is precisely SIG's
   §9.3 explainable-confidence requirement expressed as UI. SIG must never render an unverified
   community observation with the same visual weight as a records-derived claim, and the ecosystem has
   independently converged on that rule.
4. **SIG must not be the reason a bot revert happens.** `Mateusz_Konieczny`'s stated willingness to
   auto-remove bogus nodes means that any SIG-fed edit which is later judged implausible risks a mass
   revert that damages both SIG and DeFlock. This is the strongest argument for the suggestion-not-write
   posture in F12.29–F12.30.

**Outline delta:** **EXTENDS §12 and §19** — the outline's data-quality discussion assumes error, not
adversarial or panic-driven fabrication. **CORRECTS** the assumption in §3 that community data quality is
a slow-moving background property: it is currently a live incident with international scope.

---

### F12.29 — MapRoulette is a usable, documented delivery vehicle for SIG→OSM suggestions, including tag-level cooperative fixes

**Claim:** MapRoulette's API can create projects, challenges and tasks programmatically, supports
"cooperative" challenges that carry a pre-computed tag change for the mapper to accept or reject, and
authenticates with a simple user API key — making it the correct surface for SIG to hand OSM mappers a
reviewable suggestion instead of writing to OSM directly.

**Status:** VERIFIED

**Evidence:** `https://maproulette.org/assets/swagger.json` (HTTP 200, 302,427 bytes), OpenAPI 3.0.3,
`MapRoulette API` v4.9.5. Relevant paths: `POST /project`, `POST /challenge`,
`POST /challenge/saveOrUpdate`, `PUT /challenge/{id}/addTasks`, `PUT /challenge/{id}/addFileTasks`,
`POST|PUT|GET|DELETE /challenge/{id}/tasks`, `PUT /challenge/{id}/updateTaskPriorities`,
`PUT /challenge/{id}/rebuild`, `GET /challenge/{id}/extract`, `GET /challenge/{id}/matchChangesets`,
`POST /challenges/bulkArchive`. The `Task` schema carries a `cooperativeWork` field and the `Challenge`
schema a `cooperativeType`, with `GET /task/{id}/cooperative/change/{filename}` documented as
*"Retrieve any change XML that is part of this task's cooperative work … which change format was used
(i.e. JOSM, OSMChange, etc)."* Challenge fields include `instruction`, `checkinComment`,
`checkinSource`, `defaultPriority`, `requireConfirmation`, `requireRejectReason` and `limitTags`.
Auth: `apiKey` header, key obtained from `https://maproulette.org/user/profile` (F12.10 row 13).

**Retrieved:** 2026-08-20

**Implication for the spec:** SIG's OSM contribution path is **suggestion-only, by construction**:

```
SIG inference (e.g. probable operator for an orphaned ALPR node)
  → confidence gate: only inferences above the publish threshold, never bare heuristics
  → MapRoulette cooperative task, one per node, carrying:
        · the OSM element id + version SIG saw
        · the proposed tag change as OSMChange
        · the evidence: source name, URL, archived copy hash, retrieval date
        · an explicit "reject" path with `requireRejectReason: true`
  → a human OSM mapper accepts, edits, or rejects under their own account
  → SIG ingests the outcome via GET /challenge/{id}/extract and matchChangesets
  → an accepted change becomes an *observation*, a rejected one becomes negative evidence
```

Four rules make this safe and they should be stated as requirements, not conventions:

- **SIG never holds OSM write credentials.** The edit is always made by a human under their own account.
  This is what keeps an inference from being laundered into OSM as an observation (outline Q33) and it is
  also the only version of this that survives the F12.28 revert threat.
- **`requireRejectReason: true` is mandatory**, because a rejection is the single highest-value signal SIG
  can receive: it is a dated, attributed, human negative finding about a specific inference rule, and it
  is how the attribution scorer gets calibrated at all.
- **The challenge instruction text must show SIG's evidence, not SIG's conclusion.** A mapper deciding
  whether an ALPR belongs to the county sheriff needs the ROW permit link, not a confidence score.
- **Stale-version guard.** A cooperative task references the element version SIG saw; if the element has
  been edited since, the task is rebuilt or withdrawn rather than applied over someone else's work.

MapRoulette is also the correct home for the *field* half of task types T01, T05, T12, T20 and T30
(F12.19): those are geographic, per-node, and already have a mapper community with tooling. SIG generates
them; MapRoulette distributes them; DeFlock's mobile editor closes them.

**Outline delta:** **EXTENDS §12 and §22.6, and ANSWERS Q34** — the outline asks how contributions flow
back without SIG becoming a competing map. The answer is that SIG never edits the map: it publishes
reviewable, evidence-bearing suggestions into the existing mapper workflow and treats the mapper's
decision as the observation.

---

### F12.30 — The contribution-back payload formats and the routing table

**Claim:** "Contribution back" is five different artifacts going to five different places, and collapsing
them into "we'll send corrections" guarantees that most of them never get sent.

**Status:** UNVERIFIED (design), built on the verified channels of F12.10 and the verified terms of F12.5

**Implication for the spec — the routing table.** Every SIG finding type has exactly one upstream owner,
one format, and one channel, recorded in the ledger and enforced at emit time:

| SIG finding | Upstream owner | Format | Channel | Timing |
|---|---|---|---|---|
| Orphaned device now attributable | OSM (via mappers) | MapRoulette cooperative task, one per node | MapRoulette API (F12.29) | Continuous, rate-capped per jurisdiction |
| Device implausible / probably fabricated | DeFlock + OSM community | Flagged list with the plausibility rule that fired | DeFlock GitHub issue + the OSM forum thread | Batched weekly; never a unilateral edit |
| Device confirmed removed (field photo) | OSM (via mappers) + local group | MapRoulette task + photo evidence | MapRoulette; local group's channel | On verification |
| Agency×technology datapoint EFF lacks | EFF Atlas | Atlas correction email in their intake format, **no coordinates** (F12.13) | `aos@eff.org` | Monthly digest |
| Portal discovered / portal died | Eyes on Flock, HIBF | URL + first/last-seen dates + archived snapshot hash | Bluesky DM / `humans@haveibeenflocked.com` | Within 48 h of detection |
| Audit-log or SharedNetworks export obtained | HIBF | The original responsive file, unmodified, plus the FOIA id | HIBF audit-log submission page | On receipt, before SIG parses it |
| Records-request outcome (granted/denied/fee/exemption) | MuckRock + SIG's own precedent store | Structured outcome record | MuckRock request thread; SIG disclosure-precedent table (F12.22) | On disposition |
| Chapter directory churn (group added/renamed/dead) | DeFlock The USA | Diff of the chapter list with evidence per row | `support@deflocktheusa.com` | Weekly |
| Contradiction implicating a partner's own data | The partner named in it | The contradiction record, both sides, before publication | Ledger `contribution_back.preferred_format` | **Before** SIG publishes, per F12.15 §6 |

Three rules govern the whole table:

1. **Upstream first, and early enough to matter.** A contradiction that implicates a partner's published
   number is sent to that partner *before* SIG publishes anything derived from it (F12.15 §6) — with a
   stated, short window, so "notify first" cannot become an indefinite veto. Default: 7 days, and the
   partner may waive it or ask for longer once.
2. **Send the artifact, not the inference.** SIG sends the responsive PDF, the archived snapshot, the ROW
   permit — the thing the partner can verify — and only then SIG's reading of it. A partner who receives
   only conclusions has to trust SIG; a partner who receives the document does not have to.
3. **Never send an inference upstream as a fact.** Every contribution carries its `label: INFERENCE |
   OBSERVATION | RECORD` and, for inferences, the rule id and the evidence that would falsify it. This is
   the same discipline the OSM path enforces structurally (F12.29) applied to the channels that have no
   structure to enforce it.

**The ODbL boundary applies here too.** SIG may contribute *facts SIG holds independently* to OSM, but
must not push OSM-derived geometry back through a path that would make SIG's non-OSM layer a Derivative
Database (F12.5 and the licensing workstream). In practice: SIG suggests **tags** (`operator`,
`operator:type`, `manufacturer`, lifecycle) sourced from records and field evidence, and never suggests
geometry it obtained from OSM in the first place.

**Outline delta:** **EXTENDS §22.6** — the outline's contribution-back is a single undifferentiated
promise; this makes it a routing table with owners, formats, deadlines and a pre-publication obligation.

---

# Part E — Contributor experience and governance (§15.6, §18, Q37)

### F12.31 — Contributor tiers: capability without identity

**Claim:** Five tiers, earned by contribution history rather than by identity verification, are what this
ecosystem's pseudonymity permits and what F12.20's abuse controls require.

**Status:** UNVERIFIED (design), constrained by the observed pseudonymity of the ecosystem (F12.10, F12.14)

| Tier | How it is reached | May do | May not do | Review depth |
|---|---|---|---|---|
| `anonymous_submitter` | No account. A submission form with a captcha. | Submit evidence against an open task; report a bad task; flag a safety concern | Claim a task; see a contributor's history; see field-task coordinates in bulk | 100%, always |
| `contributor` | Account + email or Matrix/Signal handle; no legal name | Claim tasks; submit; comment; subscribe to a jurisdiction digest | Close a task; edit others' submissions | 100% for the first 10 accepted submissions, then sampled |
| `verified_contributor` | 10 accepted submissions, ≥90% acceptance, ≥30 days | Bulk-claim within one jurisdiction; propose entity merges; use the records-request generator's MuckRock hand-off | Close a task they submitted to; resolve a contradiction | Sampled at 25% |
| `trusted_reviewer` | Nominated by two `trusted_reviewer`s or a `local_group`, plus 50 accepted submissions | Close tasks; accept/reject submissions; resolve `Contradiction`s below `BLOCKING`; merge entities | Change the ruleset; pin a resolution; publish a jurisdiction dossier | Spot-check at 5% |
| `maintainer` | Appointed by the editorial board (F12.33), named publicly, term-limited | Ruleset changes; pins; safety vetoes; partner-ledger changes; `WONTFIX` | Act alone on a `BLOCKING` contradiction or a pin over a `W4` claim — both need a second maintainer | All actions logged publicly |

`local_group` (F12.18) is **orthogonal** to this ladder, not a rung on it: a group is an organizational
identity that holds a jurisdiction queue, and its individual members each carry their own tier. A group
never inherits `trusted_reviewer` powers by being a group.

Design constraints that make the ladder honest:

- **No legal-identity requirement anywhere, including `maintainer`.** A pseudonym plus a public track
  record plus term limits is the accountability mechanism. Requiring real names would exclude most of the
  people in F12.4 and would create a target list.
- **Promotion is computed and appealable, demotion is manual and logged.** Automatic promotion prevents
  a gatekeeping clique; manual demotion prevents an automated system from being gamed into removing
  someone.
- **Tier is per-jurisdiction for `verified_contributor` and below.** Ten accepted submissions about Dane
  County does not establish judgement about Maricopa County, and a Sybil that farms an easy jurisdiction
  should not inherit trust everywhere.
- **Tier never gates *reading*.** Everything SIG publishes is public at tier zero. Tiers gate *writing*
  and *closing*, and one read-restriction only: bulk export of field-task coordinates, which is a
  targeting risk (F12.32) rather than a secrecy interest.
- **Every tier can be exercised by an organization on behalf of a member** — a local group can submit for
  a member who does not want an account at all.

**Outline delta:** **EXTENDS §15.6 and §18** — the outline has contributors but no capability model, and
therefore no way to express the review-burden scaling F12.20 item 5 requires.

---

### F12.32 — Safety is a property of the task, and the task must carry it

**Claim:** SIG generates tasks that send named or pseudonymous volunteers to photograph police
surveillance equipment at roadsides, in a period of documented legal and corporate pressure on this
ecosystem; the safety obligations that follow are design requirements, not guidance.

**Status:** UNVERIFIED (design), grounded in the verified adversarial context of F12.14 (Cyble/Flock
takedown notices, December 2025) and the verified field-verification practice of DeFlock Lynnwood (F12.6)

**Implication for the spec.** Every task carries `safety_class ∈ {desk, field_work, sensitive}` (F12.17)
and the class drives behaviour, not just a banner:

- **`field_work` tasks must render a briefing before the task can be claimed**, covering: photograph from
  public property only; do not touch, obstruct or approach the device; you are not required to identify
  yourself or explain yourself; state and local law varies on recording; here is the RCFP legal hotline
  (`hotline@rcfp.org`, verified in F12.8); here is what to do if you are stopped. The briefing text is
  versioned and its version is recorded on the claim, so SIG can prove what a contributor was told.
- **No live claim feed.** Per F12.20 item 8: who is working where is never published in real time, and
  the bulk export of open field-task coordinates is gated at `verified_contributor` and rate-limited.
  A public "currently being surveyed" map is a targeting tool for anyone who wants to find the person
  photographing their cameras.
- **Photo submissions are stripped of EXIF GPS, camera serial, and timestamps beyond date** at ingest,
  before storage, with the original discarded rather than archived privately. The device coordinate comes
  from the mapper's asserted location, not from the photo's metadata. The exception is when a contributor
  explicitly opts in to retain full EXIF for evidentiary purposes on a specific submission.
- **`sensitive` class requires a maintainer's countersignature to publish**, and covers anything naming a
  non-public individual, anything in a jurisdiction with an active dispute, and anything a contributor
  has flagged under the F12.20 item 7 veto.
- **The safety veto is unconditional and untraceable to the flagger.** Any contributor at any tier may
  flag a task as dangerous; the task goes `WONTFIX` pending maintainer review; the flagger's identity is
  not shown to anyone but the reviewing maintainer, and never to the jurisdiction.
- **A jurisdiction may opt out of field tasks** (already an F12.17 `suppress_if` case). The likeliest
  real user of that switch is a local group that knows something SIG does not — an ongoing prosecution, a
  hostile department, a member who has been doxxed — and it must not require them to explain why.
- **SIG never asks anyone to obtain a record by any means other than a lawful public-records request.**
  The task generator has no "get inside" path and must not acquire one.

**Outline delta:** **EXTENDS §12, §15.6 and §18** — the outline generates field tasks without a safety
model; F12.14's takedown evidence makes that omission material rather than theoretical.

---

### F12.33 — Governance: an editorial board with a narrow, published mandate

**Claim:** Disputes in this ecosystem are between volunteer organizations with no shared legal entity, so
governance must be about *publication decisions*, not about membership, and its powers must be
enumerated and small.

**Status:** UNVERIFIED (design), grounded in the observed structure of the ecosystem (F12.4, F12.14: one
501(c)(3)-sponsored project among ~90)

**Implication for the spec.** The editorial board is 3–5 named people (pseudonyms permitted), serving
staggered fixed terms, at least one of whom is not a SIG maintainer, and it does exactly six things:

1. Resolves `BLOCKING` contradictions that a `trusted_reviewer` cannot (§6.5 / R13 §11).
2. Decides publication of `sensitive`-class material (F12.32).
3. Hears disputes between two local groups claiming the same jurisdiction (F12.21) — with the standing
   default that while a dispute is open SIG **publishes both positions, labelled**, and publishes neither
   party's identity claims as fact.
4. Approves ruleset changes that would alter already-published values, and requires the diff report to be
   published with the change.
5. Handles takedown and correction demands from agencies, vendors and individuals — including the
   Cyble/Flock-style notices documented in F12.14 — and publishes a dated transparency record of every
   one received and its disposition, whether or not SIG complied.
6. Appoints and removes maintainers.

It explicitly does **not**: approve individual claims, gate contributions, arbitrate between contributors
and local groups about credit, or decide what SIG researches.

Three procedural commitments do most of the work:

- **Everything the board decides is published, including the dissents**, with the same provenance
  discipline SIG applies to claims. A governance body for a provenance project that keeps unminuted
  decisions is a contradiction in terms.
- **Recusal is mandatory and public** where a board member is a member of an implicated local group.
- **A correction is never a deletion.** Per F12.15 §8, withdrawn material is marked `source_withdrawn`
  and the historical assertion remains auditable. The board may not quietly unpublish.

**Outline delta:** **EXTENDS §18** — the outline names governance as a need without a mandate or a
procedure; this supplies both, deliberately narrow.

---

### F12.34 — Stable, resolvable identifiers (Q37)

**Claim:** SIG's identifiers must be opaque, permanent, resolvable, and de-referenceable to a versioned
record; upstream identifiers are preserved beside them, never in place of them.

**Status:** UNVERIFIED (design), answering **Q37** for the community/ecosystem surface; the storage and
entity-resolution halves belong to R4/R6 and are not restated here

**Implication for the spec.**

```
https://sig.example/id/<type>/<uuid7>            # canonical, opaque, permanent
https://sig.example/id/<type>/<uuid7>?as_of=<ts> # the record as SIG knew it at <ts>
```

- **Opaque, not descriptive.** An id must not encode agency name, state, or vendor, because all three
  change (F12.2: `livefreeva.org` → `deflockthevalley.com`) and a descriptive id that becomes wrong is
  worse than an opaque one that never was right.
- **Never reused, never deleted.** A merged entity's id resolves permanently to a `303`-style redirect
  record naming its successor, with the merge date and rationale. A withdrawn entity resolves to a
  tombstone stating what it was and why it was withdrawn.
- **Upstream ids are preserved verbatim** in `external_ids[{scheme, id, retrieved_at}]` — OSM node id +
  version, MuckRock FOIA id, DocumentCloud id, Atlas datapoint id, ORI, a partner's own key — and SIG
  publishes the crosswalk back to the partner (F12.15 §5). Preserving the partner's id is what makes
  "click through to the people who actually found this" possible, which is the whole of §22.6 in one
  mechanism.
- **Every published number is citable as `(id, as_of)`** — the frozen-citation requirement newsrooms
  named first in F12.9. A citation that silently changes meaning when SIG revises a claim is not a
  citation.
- **Local groups get ids too.** The 85 groups in F12.4 are `Organization` nodes with
  `primary_presence_type` (F12.2) and their own permanent ids, so that a group which loses its domain
  does not lose its identity in the graph — the archival-insurance argument of F12.14 applied to
  identity rather than to data.

**Outline delta:** **ANSWERS Q37** for this workstream's surface and **EXTENDS §15.7** with the
`?as_of=` de-reference, which is what makes the frozen citation real rather than aspirational.

---

## Open questions

1. **Nothing in Stage 0 has been executed.** Every outreach template, SLA, and state transition in
   F12.11–F12.16 is design. Not one message has been sent, no partner has agreed to anything, and the
   21-day reply SLA is a guess. The single largest risk in this workstream is that the ecosystem's
   response rate to a new project asking for permission is unknown and could be near zero. *Hedge:* the
   `DEFAULT_POSTURE` of link-and-cite means SIG functions at reduced capability with zero replies; nothing
   in the pipeline may be built to assume a partner says yes.
2. **DeFlock The USA's chapter directory is all-rights-reserved (F12.5) and is SIG's registry for Layer H.**
   Whether they will grant redistribution permission is unknown, and there is no fallback registry —
   the previous one died (F12.1). *Hedge:* mirror nothing until permission is granted; ingest only
   metadata + URL + last-seen; treat the GitHub-hosted groups (F12.4) as the licence-clean core.
3. **Eyes on Flock cannot be contacted except by Bluesky DM, and ALPR Accountability Atlas cannot be
   contacted at all** (F12.10). Both are in the outline's source registry. If neither replies, SIG has a
   permanently `NO_CHANNEL` source that it may only link to — and Eyes on Flock is the portal aggregator
   whose data would otherwise close the largest operational-coverage gap.
4. **r/FlockSurveillance is entirely uncharacterized.** Every Reddit endpoint 403'd (F12.7). The ~422,000
   membership figure is secondhand from one trade publication. Whether the subreddit is a usable
   notification surface, whether its moderators would tolerate task digests, and whether OAuth API access
   is obtainable for a project like SIG are all unknown. *Hedge:* no ingestion or coordination path may
   depend on Reddit.
5. **MuckRock's filing endpoint was never exercised.** F12.24 verifies the *documentation* of
   `POST /requests/`, the 5-minute token lifetime, and the 15 req/min limit; no token was obtained and no
   request was filed. Unknown: the real cost per filed request for a nonprofit account, whether an
   organization account can create Assignments at acceptable cost, whether the deep-link prefill flow
   described in F12.24 actually exists as a URL contract or requires the API, and how the agency database
   (`GET /agencies/`) covers small municipal police departments — which is the coverage that determines
   whether the generator can name a custodian at all.
6. **The FOIA table is a secondary source with twelve verified cells.** Thirty-nine rows still rest on
   MuckRock's summaries, several of which carry no "last updated" date and one of which (Alabama) was
   demonstrably four years stale on a question that determines whether a request is lawful. Fee schedules
   in particular change by regulation without amending the statute. *Hedge:* `verified_against` /
   `verified_at` per row, an annual re-verification task against RCFP, and a hard rule that the generator
   omits a citation it cannot support rather than guessing (F12.25).
7. **Custodian contact data does not exist as a dataset for most agencies.** The generator's lookup chain
   (F12.25 step 2) has three fallbacks and no measurement of how often any of them succeeds for a
   small-town police department. This is probably the single largest unknown engineering cost in Part C.
8. **The disclosure-precedent store (F12.22) may be un-buildable without HIBF.** The "Fields Seen"
   mechanism is HIBF's; whether they will share it, whether SIG must rebuild it from its own request
   outcomes (which starts empty and compounds slowly), and whether per-agency release history can be
   inferred from MuckRock's public request corpus are all open.
9. **The succession clause has never been offered to anyone (F12.15 §7).** It is designed to be
   reassuring; it could as easily read as a hostile takeover offer to a pseudonymous volunteer who has
   just watched a peer project get takedown notices. *Hedge:* opt-in, revocable, never proposed on first
   contact, and the archive-publication sub-clause defaults to off.
10. **The task rules' priority formulas are uncalibrated.** The constants in F12.17 and the thirty rows of
    F12.19 have never run against a corpus. Effort estimates (p50/p90) are guesses. Until there is closure
    data, the queue's ordering is an assertion, and the design's own principle — that a contributor must
    be able to read *why* a task ranks where it does — is what makes recalibration safe rather than a
    silent model change.
11. **Six chapter sites were never actually read** — they returned Cloudflare 403s and one Facebook login
    wall (F12.3, F12.4) — and 62 of the 85 directory descriptions are the directory's own boilerplate
    rather than the group's self-description. The registry's liveness column is verified; its content
    column is not.
12. **Whether SIG can staff the OSM two-working-day reply SLA** (F12.27). The Organised Editing
    Guidelines require a named human who answers within two working days for the duration of the
    activity. A project that opens that channel and then goes quiet gets its edits reverted and its
    reputation damaged. This is a staffing commitment, not a technical one, and it should gate whether
    the OSM contribution path opens at all.
13. **Whether the plausibility gate should be shared code or shared output** (F12.28). DeFlock asked for
    "more eyeballs" on its monitoring tool. It is not yet clear whether the right offer is SIG running
    checks and sending results, or SIG contributing detectors to DeFlock's repo — the second is more
    generous and less controllable, and the choice should be theirs, not SIG's.

---

## Spec requirements emitted

Each requirement is testable. Where a requirement is a gate, the test is that the pipeline **fails** when
the gate's precondition is absent.

**The ecosystem registry (Layer H)**

- **REQ-R12-01** — SIG MUST model civil-society groups as first-class `Organization` nodes in a `layer: H`
  registry, keyed on a SIG-issued permanent id, with `primary_presence_type ∈ {website, social_profile,
  subreddit, linktree, none}`, alias/lifecycle history, and `last_seen`. Identity MUST NOT be keyed on
  domain. *(F12.2, F12.4, F12.34)*
- **REQ-R12-02** — The chapter-directory connector MUST record, per group, the URL as listed, the resolved
  URL after redirects, the HTTP status, and the check timestamp on every run, and MUST raise a churn event
  when any of the four changes. *(F12.3, F12.4)*
- **REQ-R12-03** — The connector inventory MUST include a **GitHub/GitLab repository connector** for
  civil-society sources, keyed on `(host, org, repo, path, commit_sha)`, treating the commit SHA as the
  content-addressed evidence identifier. *(F12.4)*
- **REQ-R12-04** — Every external source record MUST carry `license.{name, statement_url, statement_sha256,
  statement_last_checked, seen_directly}` with the default value `unspecified-all-rights-reserved`, and the
  export stage MUST fail closed when a public export would contain third-party prose from a source whose
  `redistribution` is not `permitted`. *(F12.5)*

**Stage 0 as an enforced gate**

- **REQ-R12-05** — Stage 0 MUST be implemented as a per-source state machine with the states
  `DISCOVERED → TRIAGED → CONTACTED → AWAITING_REPLY → NEGOTIATING → AGREED` plus the terminal states
  `DECLINED`, `OPTED_OUT`, `NO_CHANNEL`, `DORMANT`, and a recurring `REVIEW`. *(F12.11)*
- **REQ-R12-06** — The ingestion runner MUST load the source's collaboration-ledger record **before**
  constructing the adapter and MUST raise `IngestionNotPermitted` when `ingestion_permitted != true`.
  There MUST be no override flag on the production path. [testable: an adapter with a `false` ledger record
  fails the run] *(F12.11, F12.16)*
- **REQ-R12-07** — Non-reply MUST default to link-and-cite. A source in `AWAITING_REPLY` past its SLA MUST
  drop to metadata + URL + retrieval date only, and MUST NOT be bulk-copied. Silence MUST NOT be recorded
  as consent. *(F12.11)*
- **REQ-R12-08** — Each source MUST have exactly one `collaboration/<source_id>.yaml` file in git carrying
  the fields enumerated in F12.16, and CI MUST fail if (a) an adapter exists with no matching ledger file,
  or (b) a ledger file has `license.seen_directly: false` together with `redistribution: permitted`.
  *(F12.16)*
- **REQ-R12-09** — Outreach MUST be reproducible: the ledger MUST record `outreach_variant`, the rendered
  message's SHA-256, the channel, and the send timestamp, so that "what did we say to them" is answerable
  from the repository alone. *(F12.12, F12.13, F12.16)*
- **REQ-R12-10** — The collaboration ledger MUST be public and every change MUST be a git commit, so that
  a partner can verify SIG's record of them without asking. *(F12.16)*
- **REQ-R12-11** — Revocation MUST take effect within 7 days and MUST set `ingestion_permitted: false`,
  stop fetching, remove redistributed content from exports and API, and publish a dated ledger entry.
  Claims already published that cite the source MUST be marked `source_withdrawn` rather than deleted.
  *(F12.15 §8)*

**Archival insurance and succession**

- **REQ-R12-12** — Every fetch of a partner source MUST be content-addressed (SHA-256), dated, and retained
  indefinitely as an archive of record, not as a cache. *(F12.14)*
- **REQ-R12-13** — Each source MUST have a three-tier archive: raw capture (private if terms require),
  rendered public derivative (only what SIG is licensed to show), and an **always-public metadata stub**
  carrying name, URL, licence, last-seen, health, contact and successor. *(F12.14)*
- **REQ-R12-14** — Every capture MUST also be submitted to an archive SIG does not control
  (`https://web.archive.org/save/<url>`), and failure to do so MUST be recorded, not silently ignored.
  *(F12.14)*
- **REQ-R12-15** — A per-source health monitor MUST check DNS resolution, HTTP status, TLS expiry, content
  hash drift, `robots.txt` change and licence-statement hash change; three consecutive failures MUST raise
  a `SOURCE_DORMANT` task (T25) and notify the source's recorded contact. *(F12.14)*
- **REQ-R12-16** — The succession clause MUST be opt-in per sub-clause (mirror, handback, dormancy monitor,
  archive publication, named successor, credential escrow, sunset), revocable without reason, and
  `archive_publication_permitted` MUST default to `false`. Handback MUST be unconditional and MUST survive
  any dispute. *(F12.15 §7)*
- **REQ-R12-17** — A published archive of a dormant source MUST carry a machine-enforced banner naming it
  an archive, its end date, and the terms it is hosted under, and SIG MUST NOT operate the source's name,
  accept contributions in its name, solicit donations in its name, or claim its handles. *(F12.14, F12.15)*
- **REQ-R12-18** — If a source selected the sunset option, deletion MUST be honoured over preservation.
  *(F12.15 §7g)*

**Partner interfaces**

- **REQ-R12-19** — SIG MUST expose four distinct partner interfaces, not one API: dataset exchange with a
  correction-submission channel; a rendered, citable one-page jurisdiction dossier; a per-claim evidence
  chain traceable to an archived artifact with a hash; and a co-authorship path for methodology partners.
  *(F12.8)*
- **REQ-R12-20** — The newsroom interface MUST provide a frozen, permanently resolvable snapshot citation
  (`(id, as_of)`), evidence-first drill-down to an archived artifact with hash and retrieval date, a
  per-jurisdiction and per-agency "what changed" diff feed, an exposed contradiction ledger, CSV/GeoJSON
  and DocumentCloud-linkable exports, an **embargo-safe query mode that logs and publishes nothing about
  which jurisdiction was queried**, and a named human contact. *(F12.9, F12.34)*
- **REQ-R12-21** — Coordinate-level corrections MUST NOT be routed to EFF's Atlas, whose intake explicitly
  excludes camera coordinates; they MUST be routed to the OSM path instead. *(F12.13, F12.30)*

**Research-task generation**

- **REQ-R12-22** — Every task type MUST be a versioned declarative rule stored as data with the eight
  mandatory parts of F12.17 (`detector`, `priority`, `required_evidence`, `assignee_class`,
  `effort_estimate`, `geography`, `completion_test`, `auto_expire_days`), plus `suppress_if`,
  `safety_class` and `routes_to_partner`. Task-generation logic MUST NOT live in application code.
  *(F12.17)*
- **REQ-R12-23** — Detectors MUST be pure, side-effect-free queries over the graph. A detector MUST NOT
  call an external service, and task generation MUST be re-runnable against a historical snapshot to
  produce the identical task set. [testable: replay against a frozen snapshot] *(F12.17)*
- **REQ-R12-24** — Task priority MUST be a published formula over named inputs, not a learned model, and
  the task page MUST render the formula's terms and their values. *(F12.17)*
- **REQ-R12-25** — `completion_test` MUST be machine-checkable wherever the evidence type permits, and a
  human MUST NOT be able to close a task whose `completion_test` fails without a logged override reason.
  *(F12.17)*
- **REQ-R12-26** — **Negative findings MUST be first-class**: a documented survey with method and date that
  found nothing is a storable `EvidenceArtifact` and a valid closing answer, and MUST NOT be modelled as
  absence of data. *(F12.17, F12.19 T01/T15)*
- **REQ-R12-27** — SIG MUST implement the thirty task types of F12.19, including the four self-maintenance
  types T20 (link rot), T21 (outdated parser), T22 (candidate duplicates) and T25 (source dormant), which
  MUST NOT be deferred out of the first release. *(F12.19)*
- **REQ-R12-28** — The deployment-termination vocabulary MUST admit six outcomes — contract canceled,
  contract rejected, cameras deactivated, paused, cameras removed, ALPRs banned — rather than a binary
  lifecycle. *(F12.6)*
- **REQ-R12-29** — The task lifecycle MUST implement all eleven states of F12.20 including `SUPPRESSED`,
  `INVALIDATED` and `WONTFIX`, and `CLOSED → REOPENED` MUST be reachable when new contradicting evidence
  arrives or `completion_test` regresses. *(F12.20)*
- **REQ-R12-30** — Deduplication MUST be enforced at generation on `(rule_id, entity_key)`: a second firing
  updates the existing task rather than creating a sibling. *(F12.20)*
- **REQ-R12-31** — A rule version bump MUST move affected open tasks to `INVALIDATED` with a pointer to the
  successor rule version. It MUST NOT delete them. *(F12.20)*
- **REQ-R12-32** — Task claiming MUST be a soft lock with a TTL (default 14 days desk / 30 days field) that
  auto-releases with an 80% warning, and the claim MUST NOT appear anywhere in the authorization path.
  [testable: a non-claimant can submit to a claimed task] *(F12.20, F12.21)*
- **REQ-R12-33** — Task staleness MUST use two independent clocks — task age (drives `EXPIRED`) and
  underlying-evidence age (drives priority) — and they MUST NOT be conflated. *(F12.20)*
- **REQ-R12-34** — A `SUBMITTED` transition without an artifact satisfying the rule's `required_evidence`
  MUST be rejected by schema validation, before any human review. *(F12.20)*
- **REQ-R12-35** — Submissions MUST pass geographic, temporal and duplicate-geometry plausibility gates
  before entering review, including a **vendor operating-territory check** that holds at lowest confidence
  any claim placing a vendor's device in a country where SIG has no evidence the vendor operates.
  *(F12.20, F12.28)*
- **REQ-R12-36** — No single submission may flip an entity's lifecycle state. Both adversarial directions —
  false "removed" evidence and fabricated devices — MUST require dated, verifiable evidence and MUST enter
  at reduced confidence. *(F12.20, F12.28)*
- **REQ-R12-37** — Sybil resistance MUST NOT require legal identity. Rate limits, contribution history,
  evidence-quality scoring and per-account review of the first N submissions are the permitted mechanisms.
  *(F12.20, F12.31)*
- **REQ-R12-38** — Any contributor at any tier MUST be able to veto a task as dangerous; the task moves to
  `WONTFIX` pending maintainer review, and the flagger's identity MUST NOT be exposed outside that review.
  *(F12.20, F12.32)*
- **REQ-R12-39** — SIG MUST NOT publish, in real time, who has claimed which task or where field work is in
  progress. Claim data is publishable only in aggregate and after the fact. *(F12.20, F12.32)*

**Geographic queues**

- **REQ-R12-40** — A jurisdiction claim MUST grant only: a stable queue URL, notification rights, a small
  priority bonus, attribution, a bounded first-look window (default 7 days, automatically expiring), and a
  rendered dossier. It MUST NOT grant veto, approval, suppression, exclusivity, or ownership. *(F12.21)*
- **REQ-R12-41** — Jurisdiction claims MUST be non-exclusive: multiple groups may claim one jurisdiction
  and the queue MUST list all of them, with no designated lead. *(F12.21)*
- **REQ-R12-42** — A claim MUST lapse after 120 days with no closed task and no digest engagement, after a
  warning notification. *(F12.21)*
- **REQ-R12-43** — Queues MUST be claimable at state, county, municipal and campus granularity, and a
  parent claim MUST confer no rights over child queues. *(F12.21)*
- **REQ-R12-44** — A claiming group MUST be able to attach a dated public annotation to any claim in its
  jurisdiction; the annotation is evidence subject to the same standards and MUST NOT block publication.
  *(F12.21)*

**Contribution back**

- **REQ-R12-45** — SIG's OSM contributions MUST be conducted as a declared Organised Editing activity: a
  wiki activity page under `Organised Editing/Activities/`, generated from the collaboration ledger; a
  fixed changeset hashtag on every SIG-originated changeset; a community pre-announcement at least 14 days
  before the activity begins; and a named human answering within two working days. The OSM write path MUST
  refuse to run until the ledger records a community-post URL at least 14 days old. *(F12.27)*
- **REQ-R12-46** — SIG MUST NOT hold OpenStreetMap write credentials. All SIG→OSM changes MUST be delivered
  as MapRoulette cooperative tasks carrying the element id and version SIG observed, the proposed change,
  and the evidence (source, URL, archive hash, retrieval date), and applied by a human under their own
  account. [testable: no OSM OAuth token exists in any SIG deployment] *(F12.29)*
- **REQ-R12-47** — Cooperative tasks MUST set `requireRejectReason: true`, and a rejection MUST be stored as
  dated negative evidence against the originating inference rule and fed back into that rule's calibration.
  *(F12.29)*
- **REQ-R12-48** — A cooperative task whose referenced OSM element version has changed since SIG observed it
  MUST be rebuilt or withdrawn, never applied over the newer edit. *(F12.29)*
- **REQ-R12-49** — SIG MUST NOT suggest to OSM any geometry it obtained from OSM; SIG's OSM suggestions are
  limited to attribute tags derived from records, field evidence or SIG-original observation, preserving
  the ODbL boundary. *(F12.5, F12.30)*
- **REQ-R12-50** — Every contribution sent upstream MUST carry an explicit `label ∈ {RECORD, OBSERVATION,
  INFERENCE}`, and for inferences the rule id and the evidence that would falsify it. SIG MUST NOT send an
  inference upstream as a fact. *(F12.30)*
- **REQ-R12-51** — Each finding type MUST have exactly one routed upstream owner, format and channel, stored
  in the ledger, and the emit stage MUST fail on a finding with no route. *(F12.30)*
- **REQ-R12-52** — A contradiction implicating a partner's published data MUST be delivered to that partner
  before SIG publishes anything derived from it, with a bounded default window of 7 days that the partner
  may waive or extend once. The window MUST NOT be open-ended. *(F12.15 §6, F12.30)*
- **REQ-R12-53** — For each agency SIG MUST maintain a **disclosure-precedent record** — record classes
  previously released, redacted or refused by that agency and by peer agencies under the same statute, with
  dates — and the records-request generator MUST consume it. *(F12.22)*

**Contributor tiers, safety, governance**

- **REQ-R12-54** — Contributor capability MUST follow the five tiers of F12.31, earned from contribution
  history; no tier, including `maintainer`, may require legal identity. Promotion MUST be computed and
  appealable; demotion MUST be manual and logged. *(F12.31)*
- **REQ-R12-55** — Tiers MUST gate writing and closing only. All published SIG content MUST be readable at
  tier zero; the single permitted read restriction is bulk export of open field-task coordinates.
  *(F12.31, F12.32)*
- **REQ-R12-56** — Review depth MUST scale with tier (100% → sampled → spot-check) and MUST reset to 100%
  for an account after any rejected submission. *(F12.20, F12.31)*
- **REQ-R12-57** — A `field_work` task MUST NOT be claimable until the contributor has been shown the
  versioned safety briefing, and the briefing version MUST be recorded on the claim. *(F12.32)*
- **REQ-R12-58** — Photo submissions MUST have EXIF GPS, device serial and sub-date timestamps stripped at
  ingest, with the original discarded unless the contributor explicitly opts in per submission. Device
  coordinates MUST come from the contributor's asserted location, never from photo metadata. *(F12.32)*
- **REQ-R12-59** — A jurisdiction MUST be able to opt out of field tasks without stating a reason, and the
  opt-out MUST be enforced by `suppress_if` at generation time. *(F12.17, F12.32)*
- **REQ-R12-60** — SIG MUST NOT generate any task that asks a contributor to obtain a record by any means
  other than a lawful public-records request. *(F12.32)*
- **REQ-R12-61** — The editorial board's mandate MUST be enumerated and limited to the six powers of
  F12.33; its decisions, dissents and recusals MUST be published; and takedown or correction demands MUST
  be logged in a dated public transparency record whether or not SIG complies. *(F12.33)*
- **REQ-R12-62** — Withdrawn or corrected material MUST be marked, never silently unpublished; the
  historical record of what SIG asserted MUST remain auditable. *(F12.15 §8, F12.33)*

**Records-request generator and FOIA reference data**

- **REQ-R12-63** — The records-request generator MUST render text and MUST NOT send. Filing is always
  performed by a human. *(F12.23, F12.24, F12.25)*
- **REQ-R12-64** — MuckRock integration MUST be a deep-link hand-off that opens a prefilled draft under the
  **contributor's** account. SIG MUST NOT file requests from a contributor's account or quota. Filing from
  SIG's own institutional account MUST require per-request human approval, a hard rate cap, and a public
  log. *(F12.24)*
- **REQ-R12-65** — SIG MUST record `{muckrock_foia_id, filed_at, filed_by_tier}` on the originating task,
  poll request status and communications, ingest responsive files as `EvidenceArtifact`s with the FOIA id
  as provenance, and re-evaluate `completion_test` so the task closes automatically. *(F12.24)*
- **REQ-R12-66** — All SIG HTTP clients MUST send an identifying `User-Agent` naming the automation and a
  real contact point; generic or browser user agents MUST NOT be used against partner APIs. [verified
  necessary: muckrock.com returns 403 to a browser UA and 200 to an identifying one] *(F12.24)*
- **REQ-R12-67** — The generated request MUST contain, in order: addressee and custodian title; the state's
  exact statute name and citation; a residency assertion **only where the state restricts it and only when
  the requester has affirmed it**; the record-class enumeration using proven language; a date range
  narrowed to the gap; a native-electronic/CSV format preference; segregability, preservation and fee-cap
  clauses; the statutory deadline quoted with the date it falls on; an exemption pre-emption paragraph
  drawn from the disclosure-precedent record; and, for audit-log classes, the vendor's own documentation
  snippet. *(F12.22, F12.25)*
- **REQ-R12-68** — The generator MUST NOT fabricate a statutory citation. If the jurisdiction row is
  incomplete it MUST emit the request without the citation and flag the gap. *(F12.25)*
- **REQ-R12-69** — The generator MUST produce escalation letters for the six failure modes — overdue, fee
  too high, exemption denial, "no records exist", "too broad/burdensome", unjustified redaction — each
  citing that state's statute and naming the administrative appeal body where one exists. *(F12.23, F12.25)*
- **REQ-R12-70** — Filing a request MUST create a `RecordsRequest` node linked to the task with a deadline
  timer that fires an escalation task on the statutory date + 1. Where the state has no statutory deadline,
  the timer MUST be `null` and the overdue rung MUST be disabled — a deadline MUST NOT be defaulted or
  guessed. *(F12.25, F12.26)*
- **REQ-R12-71** — The FOIA reference table MUST be structured data, not template prose, carrying per
  jurisdiction: `statute_name`, `citation`, `response_deadline{value, unit, basis, extension}`,
  `fee_rule`, `fee_waiver{available, mandatory, ground, citation}`,
  `requester_eligibility ∈ {any, resident_only, resident_or_agent, resident_or_media}`, `appeal_body`,
  `verified_against ∈ {muckrock_guide, rcfp_guide, primary_text}` and `verified_at`. *(F12.26)*
- **REQ-R12-72** — The task router MUST refuse to route a `records_requester` task in a
  `resident_only`-class jurisdiction (currently AL, AR, DE, KY, TN, VA) to a contributor with no declared
  standing in that state, and MUST offer the jurisdiction's local-group queue instead. SIG MUST NOT assert
  residency on a requester's behalf. [testable: routing a Virginia T02 task to a contributor with no
  Virginia standing raises] *(F12.21, F12.26)*
- **REQ-R12-73** — The FOIA reference table MUST itself be a monitored source with an annual
  re-verification task against the RCFP Open Government Guide and a staleness alarm, because a stale row
  can render a generated request unlawful rather than merely ineffective. *(F12.26)*

**Identifiers**

- **REQ-R12-74** — SIG identifiers MUST be opaque, permanent, never reused, and resolvable at
  `https://<host>/id/<type>/<uuid>`, with `?as_of=<ts>` returning the record as SIG knew it at that
  instant. Merged entities MUST resolve to a successor record; withdrawn entities to a tombstone.
  *(F12.34)*
- **REQ-R12-75** — Upstream identifiers MUST be preserved verbatim in `external_ids[{scheme, id,
  retrieved_at}]` and MUST NOT be overwritten; where upstream ids churn, SIG MUST maintain a crosswalk and
  publish it back to the source. *(F12.15 §5, F12.34)*
