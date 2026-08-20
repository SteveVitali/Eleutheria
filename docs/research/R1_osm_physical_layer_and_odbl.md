# R1 — OSM physical layer, DeFlock, and the ODbL constraint

**Workstream:** R1
**Researched:** 2026-08-20
**Researcher:** lead synthesizing agent (reconstructed after the delegated R1 run was terminated
by an account spend limit before it could write its file; all findings below are first-hand
retrievals performed by the lead agent, not recovered from the terminated run)
**Outline sections covered:** §2 Layer A, §2 Layer C, §3, §5.1, §10.1B, §12, §14, §18, §21, §35.2,
§46.6, §20 (Q13, Q14, Q19, Q33)
**Confidence in this file overall:** high — Parts 1–3 rest on measured tag statistics and quoted
licence text; Part 4 (the completion pass, 2026-08-20) executed every query it reports against the
named live endpoint. The DeFlock repository/API gap noted in the original scope note is now closed
(F1.34–F1.37), and one earlier finding (F1.8) is reversed by F1.36.

> **Scope note.** This file is narrower than the original R1 brief. It covers what could be
> verified first-hand after the delegated run was lost: the OSM tag vocabulary with live
> measurements, project liveness, and — at full depth — the ODbL analysis, because the outline
> designates it a first-order architectural constraint (OL-24-06). Items not covered to brief
> depth are listed under **Open questions** and carried into the spec's risk register rather
> than being silently dropped.

---

## Part 1 — The OSM surveillance schema, measured

### F1.1 — The surveillance population is 558,645 elements and is not node-only

**Claim:** `man_made=surveillance` covers 558,645 OSM elements: 557,900 nodes, 716 ways, 29 relations.
**Status:** VERIFIED
**Evidence:** `https://taginfo.openstreetmap.org/api/4/tag/stats?key=man_made&value=surveillance`,
`data_until: 2026-08-20T00:59:51Z`.
**Retrieved:** 2026-08-20
**Implication for the spec:** The physical-asset model MUST NOT key on node id or assume point
geometry. 745 non-node elements is small but nonzero, and a schema that cannot represent them
will silently drop them and will break if remapping shifts the distribution.
**Outline delta:** EXTENDS §2 Layer A — the outline never states the element-type distribution.

### F1.2 — `surveillance:type` has 116 distinct values; ALPR is 144,312

**Claim:** The `surveillance:type` key carries 116 distinct values. Top values: `camera` 371,941
(71.18%); **`ALPR` 144,312 (27.62%)**; `gunshot_detector` 3,250; `guard` 2,003; `camera;radar` 255;
`sensor` 104; `AFR` 67; `camera;guard` 65; `camera;ALPR` 61; `traffic` 49; `ALPR;camera` 42;
`webcam` 37; `PTZ` 36; `flock safety` 29; `SC511` 25.
**Status:** VERIFIED
**Evidence:** `https://taginfo.openstreetmap.org/api/4/key/values?key=surveillance%3Atype&sortname=count&sortorder=desc`
**Retrieved:** 2026-08-20
**Implication for the spec:**
1. **Semicolon multi-values are real** and unordered: `camera;ALPR` and `ALPR;camera` are the same
   fact spelled two ways. The parser MUST split on `;` and treat the result as a set.
2. **Manufacturer leaks into the type field** (`flock safety` as a *type*). Normalization MUST be a
   versioned, inspectable mapping (OL-2C-AW-05), never a hardcoded enum.
3. A 116-value long tail requires an `unmapped_source_value` escape hatch plus a research task.
**Outline delta:** EXTENDS §2 Layer A / OL-2A-OSM-02, which lists tag *categories* but no vocabulary.

### F1.3 — OSM already carries non-camera surveillance today

**Claim:** 3,250 `gunshot_detector` and 67 `AFR` (automated facial recognition) elements exist now.
**Status:** VERIFIED
**Evidence:** Same taginfo query as F1.2.
**Implication for the spec:** The non-ALPR physical layer is available at Stage 1, not Stage 5.
This independently corroborates §4.5 (acoustic sensors must not be forced into a "camera"
abstraction) with a live population rather than a hypothetical.
**Outline delta:** CONFIRMS §4.5 and §4.7; CORRECTS the Stage-5 sequencing implication in §17 —
some non-ALPR physical data is free at Stage 1.

### F1.4 — The `surveillance` key is semantically overloaded

**Claim:** `surveillance=*` has 430 distinct values: `public` 273,978; `outdoor` 127,724;
`traffic` 22,093; `indoor` 12,743; `yes` 3,877; `camera` 3,560; `private` 2,746; `no` 2,496;
`webcam` 1,976; `cctv` 847.
**Status:** VERIFIED
**Evidence:** `https://taginfo.openstreetmap.org/api/4/key/values?key=surveillance`
**Implication for the spec:** By convention `surveillance=*` carries the **zone** and
`surveillance:type=*` the **device kind**, but both keys are polluted by the other's values plus
boolean misuse (`yes`/`no`). The connector MUST apply cross-key normalization reconciling
`surveillance`, `surveillance:type`, `surveillance:zone`, and `camera:type`, and MUST NOT trust
any single key.
**Outline delta:** EXTENDS §2 Layer A.

### F1.5 — Tag co-occurrence on the world's 144,312 mapped ALPRs

**Claim:** Measured co-occurrence (% of ALPR elements): `man_made=surveillance` 99.7%;
`direction` 93.6%; `camera:type` 92.4% (`fixed` 92.0%); `surveillance` 88.3%;
`surveillance:zone` 87.4% (`traffic` 83.4%); `manufacturer` 86.9%; **`manufacturer:wikidata` 83.4%**;
`surveillance=public` 75.5%; `manufacturer=Flock Safety` 73.3%;
`manufacturer:wikidata=Q108485435` 72.5%; `camera:mount` 30.6% (`pole` 22.4%);
**`operator` 19.1%**; `operator:wikidata` 12.3%; `brand` 3.8%; `camera:direction` 3.7%;
`operator:type` 2.9%; `electricity` 2.6%; `source` 1.7%.
**Status:** VERIFIED
**Evidence:** `https://taginfo.openstreetmap.org/api/4/tag/combinations?key=surveillance%3Atype&value=ALPR&sortname=together_count&sortorder=desc`
**Retrieved:** 2026-08-20
**Implication for the spec:** Four consequences, each load-bearing —
1. **The orphaned-device backlog is ~116,800 devices** (80.9% of mapped ALPRs lack `operator`).
   *(Refined by F1.22: measured directly at **110,812** for CONUS, of which only 4,498 also lack any
   vendor tag — the gap is specifically `operator`, not vendor identity.)*
   This is the single largest unit of addressable work in the project and is precisely the value
   SIG adds that no upstream provides.
2. **Wikidata is already the de-facto vendor identity anchor** at 83.4% coverage — higher than
   plain `manufacturer` is machine-normalizable. Adopt QIDs as a first-class crosswalk key.
3. **Derived FOV is broadly computable** (93.6% have `direction`), so the derived layer will be
   nearly as large as the observed layer, making the source/derived separation urgent.
4. **~8% are non-fixed**, so the mobility model has an immediate population.
**Outline delta:** EXTENDS §2 Layer A, §11.2, §12 — the outline asserts orphaned devices are a
problem; this quantifies it at national scale for the first time.

### F1.6 — `manufacturer=Flock Safety` is the most common manufacturer value in all of OSM

**Claim:** 108,100 elements, ahead of every wind-turbine manufacturer (Vestas 34,869; GE 24,431).
`Motorola Solutions` is 6,745. 7,031 distinct manufacturer values exist overall.
**Status:** VERIFIED
**Evidence:** `https://taginfo.openstreetmap.org/api/4/key/values?key=manufacturer`
**Implication for the spec:** (a) The DeFlock/OSM effort is by volume one of the largest
manufacturer-attribution efforts in OSM's history. (b) At 6,745, the mapped layer is **already
multi-vendor** — a Flock-only physical model would discard a measurable existing population on
day one, independently corroborating §4.2 and §22.3.
**Outline delta:** CONFIRMS §2 Layer A and §22.3 with measurement.

### F1.7 — The circulating "336K ALPRs" figure is not corroborated

**Claim:** A secondary source (MapAtlas, "DeFlock Put 336K ALPRs on OpenStreetMap") reports ~336,000;
the measured `surveillance:type=ALPR` count is 144,312.
**Status:** CONTRADICTED
**Evidence:** taginfo (F1.2) vs the blog figure surfaced in search results.
**Implication for the spec:** Do not repeat the 336K figure. The discrepancy may reflect counting
all `man_made=surveillance` (558,645) or a different definition; without a primary source the
figure is unusable. This is a live instance of the outline's own doctrine (OL-4.1-04, OL-24-03).
**Outline delta:** EXTENDS §21 — adds a verification caveat to a circulating community statistic.

---

## Part 2 — Project liveness

### F1.8 — DeFlock's live domain is `deflock.me`; the outline's `deflock.org` is wrong-but-live

> ⚠️ **SUPERSEDED by F1.36 (2026-08-20).** This finding is wrong. `deflock.me` 301-redirects to
> `deflock.org`, which is canonical. The 403 recorded below is a Cloudflare managed challenge that
> fires on HTML paths *before* the redirect; a static-asset path reveals the 301. Retained for the
> audit trail. REQ-R1-14 is superseded by REQ-R1-27.

**Claim:** `https://deflock.me/` returns HTTP 403 to a scripted client (Cloudflare-fronted, i.e.
alive but bot-protected). `https://deflock.org/` returns HTTP 200 with a minimal "DeFlock" body.
EFF's Atlas links to `https://deflock.org/` with the link *text* "DeFlock.me".
**Status:** VERIFIED
**Evidence:** curl HEAD/GET against both, 2026-08-20; `https://atlasofsurveillance.org/pages/about`.
**Implication for the spec:** The source registry MUST carry both domains, record that the
canonical host is Cloudflare-protected, and resolve the canonical one during Stage 0. Any
connector MUST assume browser-like access is required.
**Outline delta:** CORRECTS §21 (OL-21-03), which lists only `deflock.org`.

### F1.9 — Ecosystem liveness sweep

**Claim:** Measured HTTP status, 2026-08-20:

| Project | Status | Note |
|---|---|---|
| eyesonflock.com | 200 (4.5 KB) | JS SPA — raw HTML carries only the title |
| haveibeenflocked.com | 200 (75 KB) | Server-rendered; content in HTML |
| haveibeenflocked.com/about/audit-logs | 200 (74 KB) | Full field documentation present |
| alprwatch.org | 200 | Substantially changed from the outline's description (F1.10) |
| alpratlas.org | 200 (16 KB) | Live |
| library.kansas.watch | 200 (34 KB) | Live |
| driversagainstflock.org | 200 (40 KB) | Live |
| sunders.uber.space | 200 (36 KB) | Live |
| panopticity.fr | 200 (19 KB) | Live |
| technopolice.fr | 200 (73 KB) | Live |
| deflock.me | 403 | Alive, Cloudflare-protected |
| **flockreporter.org** | **000 / connection failure** | **Did not resolve or respond** |
| transparency.flocksafety.com | **403 on every path incl. robots.txt** | Cloudflare managed challenge (F2.1) |

**Status:** VERIFIED

> **Updated by F1.38 (2026-08-20).** FlockReporter is now confirmed decommissioned, not transient:
> no A/AAAA/MX/TXT records exist, and the last Wayback capture is 2026-07-28.

**Implication for the spec:** **FlockReporter did not respond.** The outline treats it as the
directory of the local-group ecosystem (OL-3-02, OL-18-13). A single unreachable fetch is not
proof of death, but the spec MUST NOT assume its availability, MUST verify at Stage 0, and MUST
treat "the ecosystem directory may not exist" as a live risk — which strengthens the case for
SIG maintaining its own local-group registry and for the archival-insurance role (§46.6).
**Outline delta:** CORRECTS §3 and §18 — a named ecosystem dependency is currently unreachable.

### F1.10 — ALPR Watch has materially changed since the outline was written

**Claim:** ALPR Watch today presents primarily as ALPR-avoidance navigation and offline data
packages built on DeFlock, plus a FOIA archive — not principally as the reproducible
FOIA→SQL→Superset pipeline the outline describes. Its site links to: `gitlab.com/alprwatch-org`
(not GitHub), `superset.alprwatch.org/superset/dashboard/columbia-river-gorge-foia/`,
`deflock.me`, `haveibeenflocked.com`, `eyesonflock.com`, `eyesoffcr.org`, offline routing
packages (`/pub/avoidance/alprwatch-avoidance-latest.kmz`), `/flock/suspected-locations`,
and a Liberapay donation link. It explicitly states "The DeFlock project is responsible for most
of the data available."
**Status:** VERIFIED
**Evidence:** `https://alprwatch.org/` retrieved 2026-08-20.
**Implication for the spec:** (a) Code lives on **GitLab**, not GitHub — any connector or
collaboration path must target GitLab. (b) The Superset FOIA dashboard persists, so the pipeline
described in the outline still exists but is now one component among several. (c) ALPR Watch is
also a *routing* project, placing it partly in the same category as Drivers Against Flock — SIG
must not treat these as non-overlapping. (d) `eyesoffcr.org` (Eyes Off Cedar Rapids) is confirmed
live and is a concrete local-group URL.
**Outline delta:** CORRECTS §2 Layer C — the outline's characterization is incomplete and its
implied GitHub location is wrong.

---

## Part 3 — ODbL: the first-order architectural constraint (Q13, Q14)

This is the part of the brief retained at full depth, because the outline designates it a
first-order constraint (OL-24-06) and because getting it wrong is the failure that makes the
dataset unpublishable.

### F1.11 — The licence and the two-database distinction

**Claim:** OSM data is licensed ODbL by the OSMF; documentation is CC BY-SA 2.0. The ODbL
distinguishes **Derivative Databases** (which can trigger share-alike on non-OSM data if
Publicly Used) from **Collective Databases** (where share-alike applies only to the OSM-derived
parts).
**Status:** VERIFIED
**Evidence:** `https://www.openstreetmap.org/copyright`, quoted: *"OpenStreetMap is open data,
licensed under the Open Data Commons Open Database License (ODbL) by the OpenStreetMap Foundation
(OSMF)… You are free to copy, distribute, transmit and adapt our data, as long as you credit
OpenStreetMap and its contributors. If you alter or build upon our data, you may distribute the
result only under the same license."* Collective/Derivative distinction from
`https://wiki.osmfoundation.org/wiki/Licence/Community_Guidelines/Collective_Database_Guideline_Guideline`
(endorsed by the OSMF board 2016-06-17).
**Retrieved:** 2026-08-20

### F1.12 — The Collective Database Guideline's fourth bullet is the one that governs SIG

**Claim:** The guideline states that an OSM and a non-OSM dataset are "independent" — and thus a
Collective Database, not triggering share-alike — when, within a regional cut, any of the
following holds. Quoted verbatim:

> - the non-OSM and OSM datasets do not reference each other; or
> - non-OSM data completely replaces a particular type of geometry or data for a primary feature
>   within a regional cut…; or
> - the non-OSM data adds a particular type of geometry or data for a primary feature that was not
>   already present within a regional cut, and the added feature data includes no OSM data; or
> - **a non-OSM database replaces or adds a property of a primary feature, and uses either all OSM
>   data or no OSM data for that property of that primary feature within the same regional cut**
>   (e.g., the URL property of the amenity=cafe primary feature is replaced by reference, using
>   either all OSM data or no OSM data for the replacement URLs); or
> - a combination of the above.

And critically, on what counts as a reference and what counts as a property:

> Technically a reference between non-OSM and OSM data can be by a database key or any other
> method of identifying a specific OSM or non-OSM element that may be used with a database join.
> Technical implementations that are functionally equivalent to a reference but facilitate
> performance improvements — for example joining two databases together by a key for purposes of
> a production database — are equivalent to a reference.

> "Primary feature" means data from a key value pair, or combination thereof, but not inclusive
> of **properties (e.g. colour, brand, operator, or width)**.

> Two data sets need not be physically separated to qualify as "independent".

**Status:** VERIFIED
**Evidence:** OSMF wiki, Collective Database Guideline, endorsed 2016-06-17.
**Implication for the spec — this is the central legal finding of the workstream:**

SIG's flagship contribution is **operator attribution on `man_made=surveillance` features**.
Map that onto the guideline:

- `man_made=surveillance` is a **primary feature** (a key-value pair).
- **`operator` is explicitly named in the guideline as a *property*, not a primary feature.**
- SIG adds that property **by reference** to OSM element ids — which the guideline expressly
  contemplates ("replaced by reference").
- The first bullet ("do not reference each other") **fails** for SIG, because SIG's whole design
  joins on OSM element ids, and the guideline says a join key *is* a reference.
- The **fourth bullet can succeed** — but only on a condition SIG must engineer for: SIG must use
  **no OSM data** for the operator property within a regional cut. If SIG derives operator
  attribution from contracts, portals, and public records, that condition holds. If SIG derives it
  from OSM tags — or mixes OSM-sourced operator values with its own within the same regional cut —
  the condition **fails** and the layer becomes a Derivative Database.

**Outline delta:** DEEPENS §14.1 substantially. The outline poses Strategies A/B/C abstractly; this
identifies the specific guideline clause that decides the question and the specific engineering
condition (all-or-nothing per property per regional cut) that the outline does not mention.

### F1.13 — The Horizontal Map Layers Guideline cuts the other way, and is decisive

**Claim:** The Horizontal Layers Guideline states share-alike does not attach to a Feature Type
sourced entirely from non-OSM data, **but** expressly lists as an example where you DO need to
share:

> **If you improve data used in the OpenStreetMap layer, such as additions or factual corrections,
> then you need to share those improvements.**

and:

> You add restaurants in one area from non-OpenStreetMap data based on comparison with
> OpenStreetMap data in other layers.
> You add a non-OpenStreetMap cemetery layer that is defined as "all cemeteries not found in the
> OpenStreetMap data layers".

**Status:** VERIFIED
**Evidence:** `https://wiki.osmfoundation.org/wiki/Licence/Community_Guidelines/Horizontal_Map_Layers_-_Guideline`,
endorsed by the OSMF board 2014-06-06.
**Implication for the spec:** SIG's operator attribution **is** "additions or factual corrections"
to data used in the OSM layer. Worse for the Collective-Database argument, SIG's device-attribution
workflow is defined *by comparison with* OSM data (it targets exactly those nodes where OSM lacks
an operator, and it uses OSM geometry for spatial containment) — which is the pattern both of the
"DO need to share" examples describe.

**Therefore the two guidelines point in opposite directions for SIG's exact case, and the
conservative reading wins.** SIG's OSM-linked physical-asset layer, including its
operator-attribution claims, should be treated as a **Derivative Database** and published under
ODbL.

**Outline delta:** DEEPENS §14.1 and CORRECTS its implicit optimism that Strategy A (a "separable
external layer") reliably avoids share-alike. Storing only identifiers does not avoid it: the
guideline says a join key is a reference, physical separation is explicitly *not* sufficient, and
factual improvements to OSM-layer data must be shared regardless.

### F1.14 — "Substantial" is set very low, so SIG is unambiguously substantial

**Claim:** The OSMF Substantial Guideline (endorsed 2014-06-06) defines *insubstantial* as, in
effect, "village map OK, town map not OK": fewer than 100 Features; or a non-systematic
qualitative selection; or features for an area of up to 1,000 inhabitants. It adds:

> Note also that we regard repeated small extractions as one big extraction!

and the ODbL definition it interprets:

> The repeated and systematic Extraction or Re-utilisation of insubstantial parts of the Contents
> may amount to the Extraction or Re-utilisation of a Substantial part of the Contents.

**Status:** VERIFIED
**Evidence:** `https://wiki.osmfoundation.org/wiki/Licence/Community_Guidelines/Substantial_-_Guideline`
**Implication for the spec:** SIG extracts ~144,312 ALPR features nationally, systematically, and
repeatedly (incremental updates). There is **no plausible argument that SIG's extraction is
insubstantial**, and the "repeated small extractions" clause forecloses the workaround of frequent
small pulls. Any architecture premised on staying under the substantiality threshold is void.
**Outline delta:** EXTENDS §14.1 — the outline does not address substantiality at all.

### F1.15 — Produced Works let the *presentation* layer escape, but not the data

**Claim:** The Produced Work Guideline (endorsed 2014-06-06) states:

> If the published result of your project is intended for the extraction of the original data,
> then it is a database and not a Produced Work. Otherwise it is a Produced Work.
> … We can clearly define things that are USUALLY Produced Works: .PNG, JPG, .PDF, SVG images and
> any raster image; a map in a physically printed work. Database dumps are usually not Produced
> Works, e.g. a Planet dump.

> However, if you publish a produced work, the underlying database has to be published as well…
> according to section 4.6 of ODbL.

**Status:** VERIFIED
**Implication for the spec:** SIG's rendered map images, PDF dossiers, and printed outputs are
Produced Works and may carry SIG's own licence — **but only if the underlying database is also
published**, which §4.6 requires. SIG's bulk exports, API responses that return extractable data,
PMTiles vector tiles, and GeoJSON downloads are **not** Produced Works; they are database
distribution. A vector tile archive is intended for data extraction and must be treated as data.
**Outline delta:** EXTENDS §14 and §15.2 — the outline does not distinguish the map image from the
tile archive, and the distinction determines the licence of SIG's primary map surface.

### F1.16 — Recommendation: adopt Strategy B, and treat it as mission-aligned

**Claim:** Of the outline's three strategies, **Strategy B** is correct and implementable.
**Status:** VERIFIED as a reasoned recommendation (not legal advice)
**Recommendation:**

| Layer | Licence | Reasoning |
|---|---|---|
| OSM-linked physical assets + operator/lifecycle attribution on them | **ODbL-1.0**, physically separate table and separate export file | F1.13: factual improvements to OSM-layer data must be shared; F1.14: extraction is substantial |
| SIG-original graph (organizations, deployments, contracts, policies, claims, resolutions, usage aggregates, accountability events) | **CC-BY-4.0** | No OSM content; independent evidence base |
| Rendered maps, PDF dossiers, static images | SIG's own licence as **Produced Works**, with the underlying DB published per §4.6 | F1.15 |
| Vector tiles / GeoJSON / bulk data | **ODbL** where they carry OSM-derived features | F1.15 — intended for extraction, therefore data |
| Ontology and vocabularies | **CC0-1.0** | A vocabulary succeeds only by adoption |

**Why Strategy A fails:** storing "only identifiers" does not avoid share-alike. The guideline
holds that a join key is a reference, that physical separation is not sufficient for independence,
and that factual improvements to OSM-layer data must be shared. Strategy A rests on an intuition
the guidelines specifically reject.

**Why Strategy C is unnecessary:** licensing the *entire* graph ODbL would impose share-alike on
SIG's contract, policy, and accountability data, which contains no OSM content, and would
needlessly restrict downstream reuse by newsrooms and researchers — undercutting Goal 8.

**Why this is mission-aligned rather than a cost:** SIG's stated purpose is to improve the
upstream commons (P5, OL-22.6-01). ODbL share-alike on the device layer *requires* SIG to give
its operator attributions back in a form OSM contributors can use. That is the outcome the project
wants anyway. The licence is enforcing the federation compact.

> **Amended by F1.29 (2026-08-20).** The CC-BY-4.0 recommendation in the table above is correct for
> *downstream publication* but obstructs *upstream contribution*: OSM's own compatibility table rates
> CC-BY-4.0 as requiring an additional waiver, and the Import Guidelines forbid the contributor
> claiming any additional copyright. The subset SIG contributes to OSM must be dual-licensed under an
> ODbL-compatible instrument. See REQ-R1-26.

**Residual items requiring actual counsel** (flagged, not resolved here):
1. Whether SIG's API responses returning device-linked claims constitute distribution of a
   Derivative Database triggering §4.4b, or a Produced Work.
2. Whether jurisdiction geometry sourced from OSM boundary relations "uses OSM data" for the
   operator property under the fourth bullet, contaminating an otherwise-clean attribution.
3. Whether the regional-cut unit for SIG should be state, county, or jurisdiction.
4. The EU sui generis database right for the international phase.

**Outline delta:** DEEPENS §14.1 with a decision, the reasoning, and the residual legal questions
the outline correctly says require counsel.

---

# Part 4 — Completion pass (2026-08-20)

*Completes the items listed under Open questions after the original run was terminated. Findings
continue the F1.x numbering from F1.17.*

**Researcher (this pass):** delegated completion agent
**Method:** every query, fetch and count below was executed live against the named endpoint on
2026-08-20 between 20:55Z and 21:20Z. Literal queries and literal responses are reproduced.

---

## Part 4A — Overpass API, tested live (resolves Open question 3)

### F1.17 — Overpass is anonymous, POST-based, and stamps ODbL attribution into every response

**Claim:** `https://overpass-api.de/api/interpreter` accepts unauthenticated `POST` with the query
in a `data` form field, and every response — JSON, XML, and even error pages — carries an embedded
ODbL attribution string. A *browser* User-Agent is rejected with `406 Not Acceptable`.
**Status:** VERIFIED
**Evidence:** Live, 2026-08-20.

```bash
curl -sS -A 'SIG-research/0.1' --data-urlencode "data@query.ql" \
     'https://overpass-api.de/api/interpreter'
```

Every successful response contains:

```json
"osm3s": {
  "timestamp_osm_base": "2026-08-20T20:54:20Z",
  "timestamp_areas_base": "2026-08-19T23:50:49Z",
  "copyright": "The data included in this document is from www.openstreetmap.org. The data is made available under ODbL."
}
```

The identical run with `-A 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36
(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36'` returned:

```
HTTP 406 Not Acceptable — Apache/2.4.68 (Debian) Server at overpass-api.de Port 443
```

**Retrieved:** 2026-08-20
**Implication for the spec:** (a) The connector MUST send a descriptive, non-browser User-Agent
identifying SIG and a contact address; spoofing a browser UA is both blocked here and explicitly
prohibited by the OSMF policy (F1.18). (b) `timestamp_osm_base` is the authoritative data-vintage
stamp and MUST be persisted on every ingest batch as the provenance watermark — it is the only
field that says how stale the answer is. (c) `timestamp_areas_base` lags `timestamp_osm_base` (here
by ~21 hours), so **area-based queries are staler than bbox-based queries**; boundary-driven
extraction inherits that lag. (d) The ODbL notice is machine-readable and MUST be captured into the
rights record rather than re-asserted by hand.
**Outline delta:** EXTENDS §5.1 — the outline does not mention the two-clock staleness model or the
UA constraint.

### F1.18 — The real Overpass quotas, and the exact meaning of 429 vs 504

**Claim:** Overpass publishes hard numeric guidance and two distinct rejection codes; the OSMF API
Usage Policy separately forbids using the *editing* API for reads at all.
**Status:** VERIFIED
**Evidence 1 — live status endpoint**, `https://overpass-api.de/api/status`, 2026-08-20T20:55:19Z:

```
Connected as: 2906930931
Current time: 2026-08-20T20:55:19Z
Announced endpoint: gall.openstreetmap.de/
Rate limit: 2
2 slots available now.
Currently running queries (pid, space limit, time limit, start time):
```

**Evidence 2 — `https://dev.overpass-api.de/overpass-doc/en/preface/commons.html`**, quoted verbatim:

> As a broad guideline to stay within safety margins, users are expected to send a maximum of about
> 10000 requests per day and keep their download volume below about 1 GB per day.

> Examples of problematic behaviour:
> - Tens of thousands of times a day sending the same request (from the same address)
> - Asking for individual OSM elements one by one millions of times.
> - Stiching bounding boxes to scrape the full data of the complete world.
> - Setting up an app for more than just OSM mappers and relying on the public instances as backend.

> In the first case, the querying script needs to be fixed. In the cases 2 and 3, one better ought
> use a planet dump instead of the Overpass API. In the last cast, only running your own instance
> sustainably serves your mission.

> Every execution of a request occupies one of the slots available to the user, in particular for
> the full actual execution time plus a cool down time. … During moments of low load the cool down
> time is just a fraction of the execution time, during moments of high load the cool down time can
> be a multiple of the execution time.

> Requests stay enqueued up to 15 seconds on the server if not yet a slot is available to them.

> **Requests that are denied due to the rate limit are answered with the HTTP status code 429.**

> If no maximum run time is declared then a default limit of 180 seconds applies. For the maximum
> memory usage, the default value is 512 MiB.

> The server admits a request if and only if it is going to use in both criteria at most half of the
> remaining available resources. For the maximum accepted memory usage the value is currently 12 GiB.

> **Requests that have been denied due to this resource mismatch are answered with an HTTP status
> code 504.**

> There are currently two distinct servers that both can be reached by overpass-api.de. … The current
> individual server names are gall.openstreetmap.de and lambert.openstreetmap.de. **These servers both
> maintain their rate limiting independently from each other.**

**Evidence 3 — OSMF API Usage Policy**, `https://operations.osmfoundation.org/policies/api/`, quoted:

> The editing API is provided in order to edit the map data, **not for read-only purposes or
> projects**. Clients may be blocked without notice if they are affecting the service level for
> others or causing data corruption.

> Large or frequent data users must use the download service "planet.osm" or other alternatives
> described below.

> **Valid User-Agent identifying application and version. Faking another app's User-Agent WILL get
> you blocked.** … **Maximum of 2 download threads.**

> Overpass API - This is an API provided for read only purposes. It is part of the OpenStreetMap
> ecosystem, but not as "core" as the main editing API covered by this policy. They are however
> subject to limitations and policies of their own.

**Retrieved:** 2026-08-20
**Implication for the spec:** Five hard connector requirements. (1) SIG MUST budget ≤10,000
Overpass requests/day and ≤1 GB/day, and MUST meter both. (2) SIG MUST treat **429 and 504 as
semantically different**: 429 = back off on time (slot exhaustion); 504 = the *query* was too big,
so retry only after shrinking the bbox or lowering `[maxsize:]` — retrying a 504 unchanged is
useless. Observed live: an unbounded worldwide query returned 504 on three consecutive attempts at
9.5 s / 11.3 s / 12.5 s, i.e. it was refused long before its declared timeout. (3) The DNS
round-robin over two independently rate-limited servers means client-side slot accounting is
unreliable; SIG MUST poll `/api/status` rather than model the quota locally. (4) The doc's third
"problematic behaviour" bullet — *"Stiching bounding boxes to scrape the full data of the complete
world"* — names precisely the naive design for SIG's global phase and directs it to a planet dump.
(5) SIG MUST NOT read bulk data from `api.openstreetmap.org`; the editing API is off-limits for
read-only projects, which restricts it to per-element history/changeset lookups (F1.22).
**Outline delta:** EXTENDS §5.1 and §10.1B — the outline treats Overpass as a generic source with no
quota model; these are the numbers the connector must be built against.

### F1.19 — Every documented public Overpass mirror was down; DeFlock runs its own instance

**Claim:** On 2026-08-20 all three alternate public endpoints named in the brief failed, while
DeFlock operates its own unadvertised public planet instance at `overpass.deflock.org`.
**Status:** VERIFIED
**Evidence:** Identical query (`node[man_made=surveillance][surveillance:type=ALPR]` over an
Atlanta bbox, `out count`) POSTed to each endpoint, 2026-08-20 20:56–21:08Z:

| Endpoint | Result |
|---|---|
| `https://overpass-api.de/api/interpreter` | **HTTP 200**, `total: 124` |
| `https://overpass.kumi.systems/api/interpreter` | **HTTP 502**, `content-length: 0`, `server: Caddy` |
| `https://overpass.private.coffee/api/interpreter` | **HTTP 500** `Internal Server Error` (502 on a second query) |
| `https://overpass.osm.jp/api/interpreter` | **TLS failure** — `certificate has expired` |
| `https://overpass.deflock.org/api/interpreter` | **HTTP 200**, `total: 124`, **0.19 s** |

`https://overpass.deflock.org/api/status` returned:

```
Connected as: 2886860801
Current time: 2026-08-20T21:08:36Z
Announced endpoint: none
Rate limit: 0
Currently running queries (pid, space limit, time limit, start time):
2075713	536870912	45	2026-08-20T21:08:35Z
…8 concurrent queries…
```

`Rate limit: 0` means slot-based rate limiting is disabled on that instance. Its data was
1 minute behind (`timestamp_osm_base 2026-08-20T21:07:29Z`) versus overpass-api.de. However it sits
behind Cloudflare with a **hard 60-second proxy ceiling**: both a CONUS-wide and a worldwide count
returned `HTTP 504 error code: 504` at exactly `60.04 s` and `60.06 s`.
**Retrieved:** 2026-08-20
**Implication for the spec:** (a) The connector's endpoint list MUST be configuration, health-checked
before each run, with automatic failover — **a hardcoded mirror list is a liveness bug**, since the
canonical instance was the *only* generic one working today. (b) `overpass.deflock.org` is a genuine
capacity resource and a concrete federation asset, but it is third-party infrastructure SIG has no
agreement to use; SIG MUST ask before depending on it and MUST NOT treat it as free capacity. Its
60 s ceiling makes it suitable only for many small queries. (c) The combination — public mirrors
unreliable, canonical instance quota-limited, partner instance capped at 60 s — means SIG's
national extraction cannot rest on any single Overpass endpoint (F1.21).
**Outline delta:** CORRECTS §5.1 — the outline (and this workstream's own brief) assume
kumi.systems / private.coffee are usable fallbacks. Today they are not.

### F1.20 — The three required queries, executed, with real output

**Claim:** Counting, `out meta` retrieval, and bbox-limited incremental fetch all work as designed.
**Status:** VERIFIED
**Retrieved:** 2026-08-20

**(a) State-level count.** Query:

```
[out:json][timeout:180];
area["ISO3166-2"="US-GA"]["admin_level"="4"]->.a;
(
  node["man_made"="surveillance"]["surveillance:type"~"ALPR"](area.a);
);
out count;
```

Response (`overpass-api.de`, `timestamp_osm_base 2026-08-20T20:54:20Z`):

```json
{"type":"count","id":0,"tags":{"nodes":"9381","ways":"0","relations":"0","areas":"0","total":"9381"}}
```

**Georgia: 9,381 ALPR nodes, 0 ways, 0 relations.**

**(b) Retrieval with full metadata.** Query:

```
[out:json][timeout:60];
node["man_made"="surveillance"]["surveillance:type"="ALPR"](33.74,-84.42,33.79,-84.36);
out meta;
```

124 elements, 60,098 bytes. A verbatim element:

```json
{
  "type": "node", "id": 5059352113,
  "lat": 33.7815621, "lon": -84.3841495,
  "timestamp": "2026-01-25T03:46:15Z",
  "version": 2,
  "changeset": 177668050,
  "user": "monohedron",
  "uid": 23397456,
  "tags": {
    "camera:mount": "traffic_signals", "camera:type": "fixed", "direction": "165",
    "man_made": "surveillance", "manufacturer": "Flock Safety",
    "manufacturer:wikidata": "Q108485435", "surveillance:type": "ALPR"
  }
}
```

`out meta` therefore yields **`version`, `timestamp`, `changeset`, `user`, and `uid`** on every
element — everything the provenance model needs except the changeset's own tags. Across those 124
nodes: 119 at v1, 5 at v2; **101 distinct changesets for 124 nodes**.

**(c) Bbox-limited incremental fetch.** Query:

```
[out:json][timeout:120];
node["man_made"="surveillance"]["surveillance:type"~"ALPR"]
  (changed:"2026-08-13T00:00:00Z","2026-08-20T00:00:00Z")
  (30.0,-85.7,35.1,-80.7);
out meta;
```

**388 elements** changed in that 7-day window over the Georgia / South Carolina / north-Florida
bbox — 326 created (v1) and 62 modified (v2+, up to v7) — across **383 distinct changesets**.
Sample element: node 11153438755, v7, changeset 187490415, `2026-08-15T14:03:40Z`, user
`Halfdeaf007`.

**Implication for the spec:** (1) `(changed:"<from>","<to>")` is the correct incremental primitive
and it returns both creations and modifications in one pass — SIG does **not** need minutely diffs
for its update loop. (2) **It does not return deletions.** A node deleted from OSM simply stops
appearing; the connector MUST detect disappearance by diffing the id set of a full regional
re-fetch against the last snapshot, on a slower cadence than the incremental loop. This is a real
gap: for a surveillance dataset, *removal* is one of the most editorially significant events.
(3) The 383-changesets-per-388-elements ratio confirms the dominant editor writes **one changeset
per device** (F1.34), so changeset-level provenance is effectively element-level here — cheap and
precise, but it also means changeset lookups scale 1:1 with elements, which the batch endpoint in
F1.22 exists to absorb.
**Outline delta:** EXTENDS §5.1 and §10.1B; CORRECTS the implicit assumption that an incremental
Overpass fetch is sufficient to maintain a mirror — deletions need a separate mechanism.

### F1.21 — National-scale extraction: tiling for freshness, PBF for bulk — with measured numbers

**Claim:** A single unbounded or CONUS-wide Overpass query is unreliable; an adaptive bbox tiling
strategy works and is what the incumbent ecosystem already does; planet/Geofabrik PBF plus
`osmium tags-filter` is the correct bulk path.
**Status:** VERIFIED
**Evidence — measured, 2026-08-20:**

*Unbounded worldwide* (`node["surveillance:type"~"ALPR"]; out count;` with `[timeout:900]
[maxsize:2000000000]`) — **HTTP 504 on 6 of 6 attempts** across both endpoints (9.5 s, 11.3 s,
12.5 s, 16.1 s on overpass-api.de; 60.06 s on overpass.deflock.org).

*Single CONUS bbox* (`(24.0,-125.0,49.5,-66.5)`, `[timeout:600]`) — 504, 504, then **HTTP 200 in
133.6 s**:

```json
{"type":"count","id":0,"tags":{"nodes":"134162","ways":"0","relations":"0","total":"134162"}}
```

*Same area, 4×4 adaptive-style tile grid against `overpass.deflock.org`* — 16 requests, **134,191
total in 61.5 s**, no failures. Per-tile counts ranged 0 (Pacific ocean cell) to 28,184
(37–43.5 N, 95.5–80.75 W). The 29-element delta versus the single-query answer is shared-edge
double counting plus churn between the two runs, i.e. the two methods agree to 0.02 %.

**So: CONUS holds 134,162 of the world's 144,312 mapped ALPRs — 93.0 %.**

*Corroboration from the incumbent implementation.* `flockhopper3/deflock-data`'s
`data/cameras/tiled-fetch.mjs` opens with:

> Instead of one national Overpass query (which now returns ~107K elements / ~54MB and times out
> unreliably at deflock.org's ~60s proxy ceiling), this covers the US with a grid of bounding boxes,
> splitting any box holding more than SPLIT_THRESHOLD cameras into quadrants first, so every
> individual request stays small (seconds, not minutes).

Its constants: `SPLIT_THRESHOLD = 5_000`, `MIN_TILE_SPAN = 0.05` deg, `TILE_CONCURRENCY = 5`,
`TILE_RETRIES = 3`, `TILE_FETCH_TOLERANCE = 0.10`, `RAW_MIN_TOTAL = 50_000`. It **count-probes each
tile first** (`out count;`, sub-second) to decide whether to split, then fetches leaves.

*Bulk path sizes, measured by HTTP HEAD:*

| File | Bytes | `Last-Modified` |
|---|---|---|
| `https://planet.openstreetmap.org/pbf/planet-latest.osm.pbf` → `planet-260817.osm.pbf` | 94,393,027,107 (**87.9 GiB**) | 2026-08-20 16:58:38 GMT |
| `https://download.geofabrik.de/north-america/us-latest.osm.pbf` | 12,093,487,336 (**11.3 GiB**) | 2026-08-20 00:35:13 GMT |
| `https://download.geofabrik.de/north-america/us/georgia-latest.osm.pbf` | 355,224,708 (**339 MiB**) | 2026-08-20 00:32:05 GMT |

Geofabrik's US page states the data is ODbL, "© OpenStreetMap contributors".
`osmium tags-filter` documentation confirmed at `https://docs.osmcode.org/osmium/latest/osmium-tags-filter.html`,
including that `-R/--omit-referenced` is **required** for history files.

**Concrete commands the spec should adopt:**

```bash
# --- Bulk cold start / periodic full reconciliation (US) ---
curl -L -o us-latest.osm.pbf https://download.geofabrik.de/north-america/us-latest.osm.pbf
osmium tags-filter -R -o alpr-us.osm.pbf us-latest.osm.pbf \
  n/man_made=surveillance w/man_made=surveillance r/man_made=surveillance
osmium export --add-unique-id=type_id -f geojsonseq -o alpr-us.geojsonseq alpr-us.osm.pbf

# --- Worldwide (avoids the "stitching bboxes to scrape the world" prohibition) ---
osmium tags-filter -R -o surveillance-planet.osm.pbf planet-260817.osm.pbf \
  n/man_made=surveillance w/man_made=surveillance r/man_made=surveillance

# --- Full history, for the retrospective lifecycle backfill (one-off) ---
osmium tags-filter -R -o surveillance-history.osh.pbf history-latest.osh.pbf \
  n/man_made=surveillance w/man_made=surveillance r/man_made=surveillance

# --- Incremental loop (per region, hourly/daily) ---
#     see F1.20(c); one (changed:) query per tile, plus a slower full re-fetch for deletions
```

**Implication for the spec — the extraction policy:**

| Job | Mechanism | Why |
|---|---|---|
| Cold start / full reconciliation / deletion detection | **Geofabrik or planet PBF + `osmium tags-filter`** | Overpass doc explicitly directs bulk users here; 11.3 GiB US extract filters to a few MB |
| Incremental update (minutes–hours) | **Overpass `(changed:…)` per tile** | Small, cheap, within quota |
| Ad-hoc regional queries, UI-driven lookups | **Overpass bbox** | Sub-second |
| Worldwide single query | **Never** | Refused 6/6; explicitly named as problematic behaviour |

Filter on **`man_made=surveillance`, not on `surveillance:type=ALPR`** — the broader filter is
barely more expensive and captures the 71 % of the population that is non-ALPR (F1.2) plus
mis-tagged devices, which a narrow filter would silently drop.
**Outline delta:** CORRECTS §5.1 and §10.1B. The outline treats Overpass as the OSM ingestion
mechanism; it is only correct for the *incremental* path. The bulk path must be PBF, and the
adaptive-tiling requirement (count-probe, split, per-tile integrity tolerance) is a substantive
piece of connector design the outline does not anticipate.

### F1.22 — The orphaned-operator backlog, measured directly rather than derived

**Claim:** 110,812 of the 134,162 CONUS ALPR nodes (**82.6 %**) carry no `operator` tag — but only
**4,498** (3.4 %) carry no vendor signal of any kind.
**Status:** VERIFIED
**Evidence:** 4×4 tiled `out count;` over CONUS against `overpass.deflock.org`, run twice
independently (72 s and 73 s), identical results both times:

```
node["surveillance:type"~"ALPR"]["operator"!~"."](<tile bbox>);            → 110,812
node["surveillance:type"~"ALPR"]["operator"!~"."]["manufacturer"!~"."]["brand"!~"."](…) → 4,498
```

**Retrieved:** 2026-08-20
**Implication for the spec — this sharpens F1.5's headline number and changes what the work queue
*is*:** F1.5 inferred "~116,800 orphaned devices" from taginfo percentages worldwide. Measured
directly for CONUS the figure is **110,812**, and the decomposition is the important part:

- **~106,314 devices (79 % of all CONUS ALPRs) have a vendor but no operator.** The mapped layer
  already knows *what brand of camera it is*; what it does not know is *which agency runs it*.
- Only 4,498 have neither. Vendor identification is essentially a solved problem in OSM; **operator
  attribution is the open one.**

This is the single most consequential measurement in the workstream for scoping, because it says
SIG's contribution is not "identify these cameras" — the community already did that — but
"attribute them to an accountable public body", which is exactly what contracts, FOIA responses and
procurement records supply and what no upstream project currently does. It also means the
MapRoulette challenge in F1.31 has a well-defined, machine-generatable task population of ~110.8 K,
and that `manufacturer`/`brand` is available as a *disambiguation input* on 96 % of those tasks.
**Outline delta:** CORRECTS §2 Layer A and F1.5 of this file — replaces a derived estimate
(~116,800) with a measured CONUS count (110,812) and adds the vendor-vs-operator decomposition,
which the outline does not draw.

---

## Part 4B — Element history, tested (resolves Open question 5, answers Q19)

### F1.23 — The OSM element-history and batch-changeset endpoints work and are sufficient

**Claim:** `/api/0.6/<type>/<id>/history.json` returns the complete version chain with per-version
tags, geometry, user and changeset; and `/api/0.6/changesets.json?changesets=<csv>` resolves up to
50 changesets — including their `created_by` and `comment` tags — in one request.
**Status:** VERIFIED
**Evidence — literal response**, `https://api.openstreetmap.org/api/0.6/node/5059352113/history.json`,
2026-08-20 (reformatted for reading; content verbatim):

```json
{"version":"0.6","generator":"openstreetmap-cgimap 2.1.0 (39120 spike-08.openstreetmap.org)",
 "copyright":"OpenStreetMap and contributors",
 "attribution":"http://www.openstreetmap.org/copyright",
 "license":"http://opendatacommons.org/licenses/odbl/1-0/",
 "elements":[
  {"type":"node","id":5059352113,"lat":33.7816646,"lon":-84.3841422,
   "timestamp":"2017-08-26T01:49:50Z","version":1,"changeset":51448275,
   "user":"StackKorora","uid":3009398,
   "tags":{"man_made":"surveillance"}},
  {"type":"node","id":5059352113,"lat":33.7815621,"lon":-84.3841495,
   "timestamp":"2026-01-25T03:46:15Z","version":2,"changeset":177668050,
   "user":"monohedron","uid":23397456,
   "tags":{"camera:mount":"traffic_signals","camera:type":"fixed","direction":"165",
           "man_made":"surveillance","manufacturer":"Flock Safety",
           "manufacturer:wikidata":"Q108485435","surveillance:type":"ALPR"}}
]}
```

That single response is also a perfect illustration of the lifecycle problem: the node was mapped in
**2017** as a bare `man_made=surveillance`, and only in **2026** was it *reclassified* as a
Flock ALPR. **The device's tag history is not the device's deployment history** — v2 is a mapping
event, not an installation event.

**Batch changeset resolution**, verified over the 101 distinct changesets from F1.20(b) in three
requests of ≤50 ids:

```
https://api.openstreetmap.org/api/0.6/changesets.json?changesets=<id>,<id>,…
```

Each returned object carries `created_at`, `closed_at`, `changes_count`, bbox, `uid`, `user`, and
the full `tags` map including `created_by` and `comment`.

**Retrieved:** 2026-08-20
**Implication for the spec:** (a) History is **50 : 1 cheaper in requests** via the batch changeset
endpoint than per-element polling, which is what makes the fetch-on-demand design affordable.
(b) Note the OSMF policy tension (F1.18): this *is* the editing API, and it is "not for read-only
purposes". Per-element and batched-changeset lookups at human scale are the accepted use; a
systematic crawl of 110 K histories is not. SIG MUST rate-limit these lookups hard and MUST NOT use
them for bulk backfill — for that, the full-history planet file (`history-latest.osh.pbf` +
`osmium tags-filter -R`) is the sanctioned path (F1.21).
**Outline delta:** EXTENDS §10.1B; CORRECTS the outline's implicit treatment of tag history as
device history.

### F1.24 — ohsome works, is free, and deliberately withholds contributor identity

**Claim:** The ohsome API serves full OSM element history planet-wide without authentication, but
its responses expose `@changesetId` and **no `user` or `uid`**.
**Status:** VERIFIED
**Evidence 1 — `https://api.ohsome.org/v1/metadata`**, 2026-08-20:

```json
{"attribution":{"url":"https://ohsome.org/copyrights","text":"© OpenStreetMap contributors"},
 "apiVersion":"1.10.4","timeout":600.0,
 "extractRegion":{"spatialExtent":{"type":"Polygon","coordinates":[[[-180,-90],[180,-90],[180,90],[-180,90],[-180,-90]]]},
 "temporalExtent":{"fromTimestamp":"2007-10-08T00:00:00Z","toTimestamp":"2026-07-27T09:00Z"},
 "replicationSequenceNumber":121586}}
```

Full planet, history back to 2007-10-08, **but only current to 2026-07-27T09:00Z — a 24-day lag.**
Requesting a window past that boundary is a hard error, not a truncation:

```json
{"status":404,"message":"The given time parameter is not completely within the timeframe
 (2007-10-08T00:00:00Z to 2026-07-27T09:00Z) of the underlying osh-data."}
```

**Evidence 2 — `POST https://api.ohsome.org/v1/elementsFullHistory/geometry`** with
`bboxes=-84.42,33.74,-84.36,33.79`, `filter=man_made=surveillance and surveillance:type=ALPR and
type:node`, `time=2024-01-01,2026-07-01`, `properties=metadata,tags` → HTTP 200, 96 version
intervals. Verbatim feature properties:

```json
{"@changesetId":162041876,"@osmId":"node/12551051880","@osmType":"node",
 "@validFrom":"2025-02-02T11:27:52Z","@validTo":"2026-07-01T00:00:00Z","@version":1,
 "direction":"245","man_made":"surveillance","operator":"Flock Safety",
 "operator:wikidata":"Q108485435","surveillance":"traffic","surveillance:type":"ALPR",
 "surveillance:zone":"traffic"}
```

**Evidence 3 — `POST /v1/contributions/geometry`** (same filter, `time=2026-01-01,2026-07-01`) →
HTTP 200, 45 contributions, each carrying `@contributionChangesetId`, `@creation`, `@timestamp`,
`@version`, plus the full tag set.

The complete property key set on both endpoints is
`@changesetId, @osmId, @osmType, @validFrom, @validTo, @version` (+ `@creation`,
`@contributionChangesetId`, `@timestamp` on contributions). **There is no `user`, no `uid`.**
**Retrieved:** 2026-08-20
**Implication for the spec:** ohsome gives SIG *validity intervals* — `@validFrom`/`@validTo` per
version — which is exactly the temporal primitive a lifecycle model needs, and gets it planet-wide
without SIG hosting a history database. Three constraints follow. (1) The **24-day lag** means
ohsome can never serve the live layer; it is a *backfill and analysis* source only, and the spec
MUST NOT wire it into the freshness path. (2) The **absent contributor identity** is a deliberate
privacy property (and a helpful one — see F1.25); resolving *who* made a change requires a second
call to the OSM changeset API keyed on `@changesetId`. SIG's design should treat that second hop as
optional and rarely taken. (3) Attribution "© OpenStreetMap contributors" per
`https://ohsome.org/copyrights` MUST be recorded in the rights registry alongside the OSM entry.
**Outline delta:** EXTENDS §10.1B — the outline names ohsome as a candidate without establishing
that it is planet-wide, free, lagged, or identity-free. All four matter.

### F1.25 — OSMCha's API requires authentication; the augmented-diff service does not

**Claim:** `osmcha.org/api/v1/*` returns 401 without credentials; `adiffs.osmcha.org` is open.
**Status:** PARTIALLY VERIFIED (open endpoints confirmed; authenticated behaviour untested)
**Evidence:** 2026-08-20 —
`https://osmcha.org/api/v1/changesets/?created_by=DeFlock` → `HTTP 401
{"detail":"Authentication credentials were not provided."}`;
`https://osmcha.org/api/v1/` and `/api/v1/docs` → `HTTP 404`;
`https://adiffs.osmcha.org/` → `HTTP 200` ("augmented diff service for OpenStreetMap changesets").
The OSMF API Usage Policy independently lists `https://adiffs.osmcha.org/` as a sanctioned
alternative provider and notes OSMCha is "a Charter Project of OpenStreetMap US".
**Retrieved:** 2026-08-20
**Implication for the spec:** OSMCha is a **monitoring** dependency, not an ingestion one, and it
needs an OSM OAuth token. Treat it as optional Stage-2+ tooling for watching edits to
SIG-tracked elements (e.g. mass deletions of ALPR nodes), with the credential recorded in the
source registry. It MUST NOT sit on the ingestion critical path, since a 401 there would be a
silent data gap. `adiffs.osmcha.org` is the credential-free fallback for changeset-level diffs.
**Outline delta:** EXTENDS §10.1B and §46 — adds an authentication requirement the outline omits.

### F1.26 — Q19 ANSWERED: store `(type, id, version, changeset, timestamp)`; never replicate history

**Claim:** R1's proposed "store element id + version, fetch history on demand" design is **correct
and now verified**, but it is under-specified in three ways that would break it in practice.
**Status:** VERIFIED (design confirmed against live behaviour of all three history sources)
**Evidence:** F1.20(b), F1.23, F1.24 — all executed.

**The answer.** SIG stores, per linked OSM element, exactly five fields, all delivered free by
`out meta` in the ordinary ingest query (F1.20b), so history costs **zero extra requests** at
steady state:

| Field | Source | Role |
|---|---|---|
| `osm_type` (node/way/relation) | `out meta` | Composite key part — REQ-R1-01; ids are only unique *within* a type |
| `osm_id` | `out meta` | Composite key part |
| `osm_version` | `out meta` | **Staleness token** — the thing that makes every downstream guarantee checkable |
| `osm_changeset` | `out meta` | Provenance handle; resolves to `created_by`/`comment` via the batch endpoint (F1.23) |
| `osm_timestamp` | `out meta` | Last-edit clock, for ordering against SIG's own evidence |

Everything else is fetched on demand and cached with a TTL: the version chain from
`/api/0.6/<type>/<id>/history.json`, the editor identity from the batch changeset endpoint, and
bulk temporal analysis from ohsome.

**The three corrections to the proposal as written:**

1. **`version` alone is not a key — `(type, id)` is, and `version` is a *staleness token*.**
   R1's phrasing "element id + version" invites a schema keyed on id. Node 5,059,352,113 and way
   5,059,352,113 are different objects. And the version's job is not identity but *invalidation*:
   every SIG claim attached to an OSM element MUST record the version it was asserted against, so
   that when re-ingest sees a higher version the claim is automatically flagged for
   revalidation rather than silently inherited. This is the mechanism that stops SIG asserting
   "operator = City of X" about a node whose geometry was moved 400 m or whose tags were rewritten.

2. **Do not store contributor identity by default.** `out meta` hands SIG `user` and `uid` on every
   element — and SIG should *drop both at ingest*, keeping only `changeset`. Three reasons, in
   order of weight: (a) these are pseudonymous identities of people mapping surveillance
   infrastructure, sometimes under their real names, and a queryable SIG table of "who mapped which
   police camera" is a re-identification and targeting surface that OSM itself does not publish in
   aggregate form; (b) ohsome — a mature OSM-ecosystem history service — independently reached the
   same conclusion and omits identity entirely (F1.24), which is strong precedent; (c) SIG's
   analytical needs are served by `created_by` and `comment` at the *changeset* level, which are
   tool and intent metadata, not personal data. Where a human investigation genuinely needs the
   editor, it is one on-demand call away and that call is auditable. This is a privacy requirement,
   not a storage optimisation.

3. **Deletions are not covered by any of the three sources' incremental paths** (F1.20c). The
   lifecycle model MUST get element disappearance from a periodic full regional re-fetch (PBF or
   tiled Overpass) diffed against the prior snapshot, and MUST distinguish *"deleted from OSM"*
   (a mapping event) from *"device removed from the street"* (a world event). Conflating them would
   let a mapper's cleanup edit masquerade as a decommissioning — a false accountability signal,
   which for this project is the worst class of error.

**Why not replicate the history DB:** the full-history planet is ~90+ GiB compressed before
expansion (F1.21 measures the *current* planet at 87.9 GiB), while SIG's linked population is
~134 K US elements whose entire version chains are a few thousand HTTP calls or one
`osmium tags-filter -R` pass over a file SIG downloads once. Replication buys nothing and adds a
permanent synchronisation liability.
**Implication for the spec:** REQ-R1-16 through REQ-R1-19 below.
**Outline delta:** RESOLVES §20 Q19. CORRECTS the outline's framing, which treats Q19 as a
storage-cost question; the binding constraints are actually *identity* (composite key), *privacy*
(drop `user`/`uid`), and *deletion semantics* — none of which are storage-cost issues.

---

## Part 4C — The write-back constraint, read (resolves Open question 4, answers Q33)

### F1.27 — The Automated Edits Code of Conduct: what actually binds SIG

**Claim:** The CoC is a policy with enforcement teeth, its scope explicitly covers Overpass-driven
scripted edits, and it imposes documentation, consultation, tagging and opt-out duties.
**Status:** VERIFIED
**Evidence:** `https://wiki.openstreetmap.org/wiki/Automated_Edits_code_of_conduct` (fetched raw
wikitext, 13,871 bytes). `https://wiki.openstreetmap.org/wiki/Mechanical_Edit_Policy` exists only
as `#REDIRECT [[Automated Edits code of conduct]]` — there is no separate mechanical-edit policy.
Quoted verbatim:

> The **Automated Edits code of conduct** must be followed at all times when performing Automated
> edits to the OpenStreetMap database. These rules apply both to people using bots, scripts used or
> created to import new data and to make other systematic edits to the database by other means
> **without consideration of each change**.

> Ignoring this policy will be treated as **vandalism** and will be responded to as such if it
> persists.

On scope — the bullet that names SIG's exact pattern:

> - use of find-and-replace functionality using a standard editor such as JOSM **or finding using
>   services such as Overpass API and changing without reviewing each object individually**;
> - manually changing tags without adequate review;

> Even if you are going to change tagging of a large number of objects systematically and don't
> think that it is an automated edit which falls under this code of conduct, it is still a good idea
> to discuss your changes in advance.

Under *Problematic usage*:

> Using a tool to assert a policy, or your own interpretation of policy, when there may be
> justifiable reasons for other interpretations… It is particularly an issue where a person, or
> small group of people work up a coding policy and then used automated processes to assert this
> within the database without consulting appropriately.

Under *Other approaches* — the escape hatch the CoC itself recommends:

> **As an alternative to automated edits, consider submitting proposed issue to quality assurance
> tools like Keep Right or osmose where problematic data can be offered for review by someone with
> time and local knowledge to consider the change more carefully.**

Under *Document and discuss your plans*:

> You should normally document your proposed edit at an English-language wiki page named
> `Automated edits/username`… Your documentation should state:
> - Who is making the change (preferably your real name and how to contact you, ideally e-mail address)
> - Your motivation for making the change and why it is important
> - A detailed description of the algorithm you will use to decide which objects are changed how
> - Information about any consultation that you have conducted…
> - When the change was made, or how frequently it is going to be repeated
> - **Information on how to "opt out"**

> Your plan should be added to Category:Automated edits log and then be discussed on a suitable
> platform run by OSM(F)… **either** the OpenStreetMap Community Forums; **or** talk…; **or** if
> your edit affects only one country or territory, then standard communication methods for the
> territory affected…

> Note that any later modification or extension to the scope of changes you propose to make should
> also be discussed in the same way and **requires new community approval. It is not possible to get
> blanket approval** for some unspecific "I am fixing misspelled tags".

Under *Execute with caution*:

> - Execute only a small number of edits with a new bot at beginning before proceeding with larger edits.
> - Ensure that you only update based on the current dataset. **Ensure that you will never
>   accidentally overwriting something that has been just modified by someone else by using a earlier
>   planet file.**
> - Ensure that you keep all data you need in case you have to revert your change when something goes awry.
> - Plan your changesets sensibly. **If your bot creates one changeset for each edit, that becomes
>   extremely hard to read for people. Such a practice would also be considered gaming the system if
>   done by a human**… Changes grouped into small regions are easiest to digest…
> - Make sure that there is some way of identifying that a certain change has been made by your
>   script. You could create a special user account for the script, or you could add a "source",
>   created_by", or "note" tag or something.
> - A "comment" tag to the changeset that describes the changes made… **You must also add the tag
>   `mechanical=yes` (or `bot=yes`). You must link to the wiki page or user page documenting your
>   changes from changeset**, for example using `description` changeset tag…
> - **Respect "opt out" requests**, i.e. if someone contacts you and asks you to stop making
>   automated edits to things that they have edited, you must comply with that wish, and you must
>   modify your software or procedure to leave those objects untouched in the future.

And the enforcement clause:

> Your edit may be reverted even if you have followed this policy; this doesn't guarantee your edit
> will be accepted. The **Data Working Group** will investigate and act on issues which cannot be
> resolved… and may either block the account immediately or send out a warning message.

**Retrieved:** 2026-08-20
**Implication for the spec:** The decisive sentence is the scope bullet: *"finding using services
such as Overpass API and changing without reviewing each object individually"*. SIG's proposed
operator backfill — select 110,812 nodes via Overpass, attach an operator derived from contracts —
**is an automated edit under this CoC by definition**, no matter how good the evidence is. Two
consequences the spec must absorb: (a) the CoC's own *Other approaches* section points at
**review-queue tools** as the sanctioned alternative, which is the direct textual warrant for the
MapRoulette design in F1.31; (b) the "one changeset per edit… would be considered gaming the
system" clause means SIG must never emit per-device changesets even in a human-mediated flow — and
note that the incumbent editor currently *does* emit one changeset per device (F1.20c, F1.34),
which is tolerated only because those are genuine per-object human edits.
**Outline delta:** CONFIRMS the outline's caution in §35.2 and supplies the specific binding text;
CORRECTS any reading in which a well-evidenced bulk attribution is exempt because it is "just adding
missing data" — the CoC's trigger is *lack of per-object review*, not data quality.

### F1.28 — The Organised Editing Guidelines: SIG qualifies, and the duties are concrete

**Claim:** The OEG apply to "any edits that involve more than one person… under one or more
sizeable, substantial, coordinated editing initiatives" — which SIG's contribution programme is —
and impose wiki registration, a unique changeset hashtag, a 2-week pre-announcement, and a 2-working-day
response SLA.
**Status:** VERIFIED
**Evidence:** `https://wiki.osmfoundation.org/wiki/Organised_Editing_Guidelines` (raw wikitext,
7,485 bytes), approved by the OSMF Board 2018-11-15. Quoted verbatim:

> The organised editing guidelines apply to any edits that involve more than one person and can be
> grouped under one or more sizeable, substantial, coordinated editing initiatives.

> **They are not a policy**, but following them is the best way to make your organised edit
> successful and receive constructive community feedback.

> Organised edits should have a Wiki page named `[[Organised Editing/Activities/Name of the
> Activity]]`… This page should truthfully describe, where applicable:
> - the coordinating person or organisation
> - a way to contact the organiser
> - **a unique hashtag to be used in the changeset comments**
> - the goal of the activity, explaining also why the goal is being pursued
> - the timeframe for the activity
> - **any non-standard tools and data sources used, and their usage conditions**
> - links where the community can access any non-standard tools or data sources used
> - the accounts of participating persons that wish to be identified…
> - if participants will receive training material or written instructions, a copy of, or link to, these materials
> - plans for a "post-event clean up" to validate edits…
> - after the activity has completed, or at least once a month for ongoing efforts, a description of the results

> All related communications should use channels that are open (no non-OpenStreetMap registration
> required), public, and archived.

> After the Wiki page is set up, the affected OSM communities should be informed through a suitable
> post… **This should be done no less than two weeks before the activity is started.** … An explicit
> go-ahead from the community is not required, and implicit consensus or even silence is enough.
> **Ignoring justified criticism and pressing on regardless can, however, lead to an activity being
> stopped and reverted.**

> **Messages should be answered within two working days while the activity is ongoing**, and
> responses should actually answer any questions and not just say "thank you".

> People looking at individual changesets that are part of a organised mapping activity should be
> able to tell as soon as they look at a changeset. **Changeset comments should include the unique
> hashtag** described on the wiki page… and link to that page.

> **What NOT to do:** Trying to hide activities or make them difficult to follow, for example by
> using many different accounts, selecting misleading user names or changing user names frequently;
> **Contributing very large or very small changesets**; being dishonest in discussions; specifying
> wrong sources.

**Retrieved:** 2026-08-20
**Implication for the spec:** The OEG are *guidelines*, not policy — but the sanction ("stopped and
reverted") is identical to the CoC's, so the practical bindingness is the same. Four requirements
fall out that are cheap to satisfy and expensive to retrofit: an `Organised Editing/Activities/…`
wiki page; a **unique changeset hashtag** (e.g. `#sig-operator-attribution`) present on every edit
SIG's workflow produces; a two-week pre-announcement per affected national community *before* any
tasks go live; and a named human with a 2-working-day response SLA. The "non-standard tools and
data sources used, **and their usage conditions**" bullet also forces SIG to publish the licence of
its operator evidence on that wiki page — which is where F1.29 bites.
**Outline delta:** EXTENDS §35.2 with the specific artefacts and the SLA; the outline references the
OEG but not their content.

### F1.29 — Import Guidelines: SIG may not claim copyright on contributed data, and CC-BY-4.0 is not ODbL-compatible without a waiver

**Claim:** Contributing SIG's operator attributions to OSM requires them to be releasable under
ODbL with no additional restriction — and OSM's own compatibility table rates **CC-BY 4.0 as
requiring an additional waiver**, which directly collides with REQ-R1-08.
**Status:** VERIFIED
**Evidence 1 — `https://wiki.openstreetmap.org/wiki/Import/Guidelines`**, quoted:

> The **Import Guidelines**, along with the Automated Edits code of conduct, shall be followed when
> importing data from external sources… The **Data Working Group** is tasked by the OSMF to detect
> and stop imports that do not comply with these guidelines. Not following these guidelines puts
> your account at risk of being blocked.

> We are only interested in 'free' data. **We must be able to release the data with our
> OpenStreetMap License**… Your data must be compatible with the ODbL.

> **You must not claim an additional copyright for yourself as the importer.** For example, if you
> import public domain data, you must not seek to restrict the use of your imported data. Your
> import account must not refuse any permissions that were given by the original creators of the
> data you're importing.

> Please also note the details of attribution requirement. We can offer *some* attribution:
> - The source can be mentioned on the Contributors page of the wiki
> - Very large scale contributions can be listed on openstreetmap.org/copyright
> - Information about the source will be listed on the import account and changesets…
>
> **If none of these are acceptable attribution for a data source, you cannot proceed with the import.**

> **You must not import the data without local buy-in.**

> After 14 days have passed, and all concerns have been addressed, the import may begin.

> Use an import-only account named "&lt;username&gt;_Import".

> Unlike traditional GIS systems, OpenStreetMap has no concept of layers. **Conflation is required
> to ensure that duplicate data is not added to OSM.**

**Evidence 2 — `https://wiki.openstreetmap.org/wiki/Import/ODbL_Compatibility`**, the row for
CC-BY 4.0, quoted:

> CC-BY 4.0 International | **likely incompatible attribution requirements and other terms;
> additional waivers required for reasonable attribution and unrestricted distribution** |
> problematic in case of future license change if incompatible new license is chosen |
> Read this LWG blog post for their evaluation of CC-BY 4.0 and why an additional agreement
> (see the cover letter and waiver form) is requested.

The referenced waiver is
`https://osmfoundation.org/wiki/Licence/Waiver_and_Permission_Templates/Cover_letter_and_waiver_template_for_CC_BY_4.0`.
All CC-BY-SA versions are rated *"incompatible share-alike and attribution requirements… cannot be
made ODbL compatible"*.

**Retrieved:** 2026-08-20
**Implication for the spec — this modifies F1.16:** F1.16 recommends publishing SIG's original
graph (which is where operator attributions are *derived*) under **CC-BY-4.0**. That is right for
downstream reuse and wrong for upstream contribution, and the two must be reconciled explicitly
rather than left to collide at Stage 3:

- Contributing operator attributions to OSM means those specific facts must be available to OSM
  under ODbL with **no additional restriction and no additional copyright claim by SIG**.
- SIG's blanket CC-BY-4.0 licence would, per OSM's own table, require a waiver.
- Therefore SIG MUST **dual-license the contributed subset**: the operator-attribution facts that
  SIG offers upstream must be additionally released ODbL-1.0-or-public-domain, and SIG MUST execute
  the OSMF CC-BY-4.0 cover-letter-and-waiver for the SIG-originated evidence base, or scope the
  waiver to the contributed field set.
- Note this is *facts about the world* (which agency operates which camera), and facts are thinly
  protected in most jurisdictions — but the Import Guidelines demand a clean licence statement
  regardless, and "it's just facts" is not an answer that gets past the DWG.

Two further hard constraints: the **conflation** requirement means SIG can never add a device that
may already exist (this is why the operator-attribution framing — editing *existing* nodes rather
than adding new ones — is strategically much safer than a device import); and the **14-day
review + local buy-in** requirement composes with the OEG's 2-week pre-announcement into a single
~2-week gate per national community.
**Outline delta:** **CORRECTS §14.1 and F1.16 of this file.** Neither anticipated that SIG's own
outbound licence choice could obstruct the upstream contribution that F1.16 calls "mission-aligned".
The ODbL analysis established what SIG must *share*; this establishes that sharing it *into OSM*
needs a licence instrument SIG does not currently plan to have.

### F1.30 — DeFlock is a manual editor, not a bot — and no ALPR effort is registered as an organised edit

**Claim:** The OSM wiki classifies DeFlock as an interactive editor, so its ~75 % share of ALPR
changesets is manual editing outside the CoC's scope; and no ALPR/DeFlock activity appears in
`Organised Editing/Activities`, though a surveillance-mapping precedent does.
**Status:** VERIFIED
**Evidence:** `https://wiki.openstreetmap.org/wiki/Deflock` (raw), infobox `genre = editor`,
`license = AGPL-3.0`, `platform = Android;iOS`, `web = https://deflock.org`, and the body text:

> **DeFlock** is a mobile OpenStreetMap editor expressly for adding Automatic License Plate Readers
> (ALPRs). The app is available for both iOS and Android.
> Changesets submitted through the app will be tagged `created_by=DeFlock *.*.*`

Its documented supported-manufacturer list is: **Flock Safety, Motorola/Vigilant, Genetec, Leonardo,
Neology, Rekor, Axis Communications, ShotSpotter.**

`https://wiki.openstreetmap.org/wiki/Organised_Editing/Activities` (raw, 82,911 bytes) contains **no
DeFlock or ALPR entry**. It does contain a directly analogous precedent:

> [[Organised Editing/Activities/CCCHH-surveillance|CCCHH surveillance]] — Adding surveillance
> cameras in the inner city of Hamburg, Germany initiated by the the CCCHH. The CCC and local OSM
> communities overlap and stay in close contact. People from both communities collect data and add
> those to OSM together. The goal is to add surveillance cameras of all kinds to enhance the
> "surveillance under surveillance" map.

**Retrieved:** 2026-08-20
**Implication for the spec:** (a) DeFlock's edits are per-object human edits through a purpose-built
editor — they are *not* automated edits, and SIG must not model its own write-back on DeFlock's
volume as if that volume were precedent for bulk contribution. (b) **CCCHH-surveillance is the
precedent to cite**: an activist-adjacent organisation mapping surveillance cameras, registered as
an organised edit, explicitly in contact with the local OSM community. SIG's wiki page should
follow its structure and reference it. (c) The manufacturer list is a ready-made seed for the
vendor normalization mapping required by REQ-R1-02, and `ShotSpotter` appearing in an *ALPR* app's
vendor list is another instance of the vendor/type conflation F1.4 identified.
**Outline delta:** EXTENDS §21 and §35.2 — supplies a concrete, on-point organised-editing precedent
the outline does not know about.

### F1.31 — Q33 ANSWERED: MapRoulette is the right mechanism, and its API supports the whole loop

**Claim:** MapRoulette's v2 API is open, documented, and provides every primitive SIG's write-back
needs — including auto-refreshing task generation, a mandated changeset comment, cooperative tag
fixes, and changeset-level outcome measurement.
**Status:** VERIFIED
**Evidence:** All live, 2026-08-20.

| Endpoint | Result |
|---|---|
| `https://maproulette.org/assets/swagger.json` | **HTTP 200**, 302,427 bytes, 223 paths |
| `https://maproulette.org/api/v2/challenges?limit=2` | **HTTP 200** |
| `https://maproulette.org/api/v2/challenge/11606` | **HTTP 200** |
| `https://maproulette.org/api/v2/docs` | HTTP 400 (not a docs route; swagger.json is the source) |

The fields that matter, from the swagger `Challenge` / `ChallengeGeneral` / `ChallengeCreation` /
`ChallengeExtra` / `Task` definitions:

- `ChallengeCreation.overpassQL` — a challenge can be *defined by an Overpass query*, which
  MapRoulette runs itself. Verified on a live challenge (id 11606, "Add direction to give way -
  France"), whose stored `overpassQL` begins
  `area[name="France métropolitaine"]->.FRM;` …
- `ChallengeCreation.remoteGeoJson` + `ChallengeExtra.updateTasks` — alternatively the challenge
  pulls tasks from a **SIG-hosted GeoJSON URL and re-reads it on a schedule**. This is the important
  one: it lets SIG's evidence pipeline be the task source without SIG ever holding write credentials.
- `ChallengeGeneral.checkinComment` / `checkinSource` — the changeset comment and `source` tag
  applied to every edit made through the challenge. Live example from challenge 11606:
  `checkinComment = "Add tag direction to highway=give_way - France #maproulette"`. **This is the
  OEG hashtag mechanism (F1.28), enforced by the platform rather than by mapper discipline.**
- `ChallengeGeneral.cooperativeType` and `Task.cooperativeWork` — cooperative ("tag fix") tasks,
  where SIG proposes exact tag changes and a human approves or rejects each one.
- `ChallengeExtra.osmIdProperty`, `exportableProperties`, `taskStyles`, `presets` — binds tasks to
  OSM element ids and controls the mapper-facing form.
- `Task.changesetId` and `GET /challenge/{id}/matchChangesets` — **the outcome loop**: SIG can read
  back which OSM changesets its challenge produced, closing provenance without guessing.
- `PUT /challenge/{id}/addTasks`, `PUT /challenge/{id}/rebuild`, `POST /challenge` — programmatic
  lifecycle.

The cooperative tag-change payload, from
`https://raw.githubusercontent.com/maproulette/maproulette-backend/main/docs/tag_changes.md`,
quoted verbatim:

> ```json
> { "osmId":int, "osmType":OSMType, "updates":Map[String, String],
>   "deletes":List[String], "version":Option[Int] }
> ```
> - **version** - Optionally you can set an object version, so this would be what version of the
>   object your changes are based on. **Currently this is not used, however in the future the idea
>   would be that if the version is not the same as the current version we would simply return a
>   conflict** and not even try to upload them.

> This API primarily supports a type of "cooperative" task in which tag changes can be proposed in
> the task, and **a MapRoulette mapper can determine if they are valid or not during task
> completion**. If the proposed tag changes are correct then MapRoulette can submit those changes
> directly to OpenStreetMap without the user having to make edits in JOSM or iD.

**Retrieved:** 2026-08-20
**Implication for the spec:** MapRoulette is the answer to Q33, and the reason is not convenience —
it is that MapRoulette **structurally enforces the per-object human review that the CoC's scope
clause turns on** (F1.27). An edit made through a MapRoulette cooperative task is not an automated
edit, because a person looked at that object and approved that change. SIG therefore moves from
"forbidden bulk edit" to "ordinary human mapping, at scale, with tooling" — the same category
DeFlock's 75 % occupies.

One critical caveat, and the spec must handle it: MapRoulette's tag-change payload accepts
`version` but **does not currently enforce it** ("Currently this is not used"). So MapRoulette will
happily apply a SIG-proposed tag change to an element that has moved on since SIG generated the
task. **SIG MUST perform its own staleness check** — re-read `osm_version` (F1.26) at task-generation
time and expire tasks whose version has advanced — rather than relying on the platform. Without
this, a stale challenge becomes exactly the "overwriting something that has been just modified by
someone else" failure the CoC names.
**Outline delta:** RESOLVES §20 Q33. EXTENDS §35.2 with the specific API surface and the
version-enforcement gap, neither of which the outline anticipates.

### F1.32 — StreetComplete has the mechanism but not the quest; the operator-quest template exists

**Claim:** StreetComplete ships an `AddCameraType` quest that **explicitly excludes ALPRs**, and its
`AddAtmOperator` quest is a directly reusable template for an `operator` quest on surveillance nodes.
**Status:** VERIFIED
**Evidence:** `https://raw.githubusercontent.com/streetcomplete/StreetComplete/master/app/src/commonMain/kotlin/de/westnordost/streetcomplete/quests/camera_type/AddCameraType.kt`:

```kotlin
class AddCameraType : OsmFilterQuestType<CameraType>() {
    override val elementFilter = """
        nodes with
         surveillance:type = camera
         and surveillance ~ public|outdoor|traffic
         and !camera:type
    """
    override val changesetComment = "Specify camera types"
    override val wikiLink = "Tag:surveillance:type"
```

The filter is `surveillance:type = camera` — **ALPR nodes are out of scope by construction.**
The operator-quest pattern, from `AddAtmOperator.kt`:

```kotlin
class AddAtmOperator : OsmFilterQuestType<String>() {
    override val elementFilter = "nodes with amenity = atm and !operator and !name and !brand"
    override val changesetComment = "Specify ATM operator"
    …
    override fun applyAnswerTo(answer: String, tags: Tags, …) { tags["operator"] = answer.trim() }
}
```

Sibling operator quests exist for charging stations and clothing bins, so `!operator` filters are
established StreetComplete practice.
**Retrieved:** 2026-08-20
**Implication for the spec:** StreetComplete is a **complement, not the primary mechanism**, and the
distinction is substantive. SC quests are answered by a person *physically standing at the object*,
which is the right instrument for facts visible on the pole (vendor, mount, direction) and the wrong
one for operator attribution, which is established from contracts and FOIA responses, not from
looking at the camera. An `AddSurveillanceOperator` quest is a plausible upstream contribution SIG
could author (the template is 30 lines), but its answers would be *survey* claims, and SIG must
record them at lower confidence than documentary evidence rather than merging the two. Conversely,
SC is the *better* mechanism than MapRoulette for the 4,498 devices with no vendor signal at all
(F1.22), which do require someone to go and look.
**Outline delta:** EXTENDS §35.2 and §12 — the outline treats StreetComplete as an undifferentiated
alternative; the survey-vs-documentary distinction determines which facts each tool can carry.

### F1.33 — The compliant write-back design, end to end

**Claim:** A design exists that contributes ~110,812 operator attributions without any automated
edit, satisfying the CoC, the OEG, and the Import Guidelines simultaneously.
**Status:** VERIFIED as a reasoned design built on F1.27–F1.32 (not legal advice)

**SIG holds no OSM write credentials at any point.** The pipeline is:

1. **Register the activity.** Create `Organised Editing/Activities/SIG surveillance operator
   attribution` on the OSM wiki, modelled on `Organised Editing/Activities/CCCHH-surveillance`
   (F1.30). It states: coordinating organisation, named contact with a 2-working-day SLA, the unique
   hashtag `#sig-operator-attribution`, goal and motivation, timeframe, the **evidence sources and
   their licences** (F1.29), a link to the open-source task-generation code, the review plan, and
   monthly result reports. Also create `Automated edits/<account>` if any part is ever automated.

2. **Announce and wait.** Post to the OSM Community Forum with the `import` context and to each
   affected national/regional community **at least 14 days** before tasks go live (F1.28, F1.29).
   Announce again for any scope extension — blanket approval is explicitly unavailable (F1.27).

3. **Generate tasks, not edits.** For each device where SIG holds documentary operator evidence,
   emit a GeoJSON feature carrying `osm_type`, `osm_id`, `osm_version` (F1.26), the proposed
   `operator` (and `operator:wikidata` where a QID exists, per REQ-R1-05), and a **citation URL to
   the underlying contract or records response**. Publish it at a stable SIG URL.

4. **Drive MapRoulette from that URL.** Create the challenge with `remoteGeoJson` = the SIG feed and
   `updateTasks = true`, so tasks refresh as SIG's evidence base grows and shrinks. Set
   `cooperativeType` to a tag-fix challenge with `Task.cooperativeWork` carrying the exact
   `{osmId, osmType, updates:{operator:…}, version}` payload (F1.31). Set
   `checkinComment = "Add operator to ALPR — <region> #sig-operator-attribution"` and
   `checkinSource` to the SIG evidence URL, satisfying the OEG hashtag requirement mechanically.
   Scope one challenge **per region**, satisfying the CoC's "changes grouped into small regions".

5. **A human approves every single object.** This is the load-bearing step: it is what keeps the
   whole programme outside the Automated Edits CoC's scope clause (F1.27), and it must never be
   optimised away.

6. **Enforce staleness SIG-side.** Because MapRoulette ignores `version` (F1.31), SIG re-checks
   `osm_version` on every feed regeneration and drops tasks whose element has advanced, so no task
   can overwrite a newer edit.

7. **Close the loop.** Poll `GET /challenge/{id}/matchChangesets` and read `Task.changesetId` to
   record which OSM changesets resulted, feeding SIG's provenance graph and the OEG-required
   monthly report.

8. **Honour opt-outs.** Maintain a suppression list of objects and users who have asked to be left
   alone, applied at feed-generation time (F1.27, mandatory).

**Why not each alternative:** a direct bot is forbidden without approval SIG will not plausibly get
for 110 K objects; a bulk import fails the conflation requirement and the CC-BY-4.0 licence gate
(F1.29) and is the wrong shape anyway, since SIG is editing existing nodes rather than adding new
ones; StreetComplete cannot carry documentary claims (F1.32); and Keep Right / osmose — which the
CoC itself names — are validators for *errors*, not carriers for externally-sourced attribution.
**Implication for the spec:** REQ-R1-20 through REQ-R1-26.
**Outline delta:** RESOLVES §20 Q33 and unblocks risk R-14. REPLACES REQ-R1-13's placeholder
("pending review") with a concrete, reviewed mechanism.

---

## Part 4D — DeFlock, located (resolves Open questions 1, 2, 7)

### F1.34 — The outline's repo citation exists but belongs to a different project

**Claim:** `github.com/flockhopper3/deflock-data` is real — but it is **FlockHopper's** tile
pipeline, not DeFlock's. DeFlock's canonical repositories are under the **FoggedLens** org.
**Status:** VERIFIED (CORRECTS the outline)
**Evidence:** `gh api`, 2026-08-20.

| Repo | Description | Licence | Stars | Homepage | Last push |
|---|---|---|---|---|---|
| **`FoggedLens/deflock`** | "Crowdsourced tool for locating and reporting ALPRs" | **MIT** | 938 | **`https://deflock.org`** | 2026-08-09 |
| **`FoggedLens/deflock-app`** | "A FOSS mobile app for viewing and submitting surveillance cameras with OpenStreetMap" | **AGPL-3.0** | 182 | — | 2026-08-05 |
| `flockhopper3/deflock-data` | "Automated PMTiles pipeline for ALPR camera data" | MIT | 0 | — | 2026-07-28 |
| `flockhopper3/deflock_maps` | "DeFlock Maps — … camera-avoidance routes" | MIT | 4 | — | 2026-07-10 |

`FoggedLens/deflock` structure: `api/`, `cms/`, `scripts/`, `serverless/`, `terraform/`, `webapp/`
(default branch `master`, Vue). `FoggedLens/deflock-app` is Flutter/Dart (default branch `main`).

`gh search repos deflock --limit 50` returned **50 repositories**, of which ~35 are *local chapter*
sites (`deflockchatt`, `deflockmpls`, `DeFlockFairfax`, `deflockutah`, `deflockelpaso`,
`deflocknorthcanton`, `deflockalamo`, `DeflockNC`, `deflock-illinois`, `deflockcolumbus`,
`Central-Sierra-Foothills-DSA/deflockroseville|deflockauburn`, …), plus adjacent tooling
(`USBKayble/deflock-nav`, `vzellweg/deflock-nav`, `KaraZajac/OVERWATCH`,
`zmattmanz/flock-detection`, `resistanceisliberty/panopti.ca` — "A Canadian-centric fork of
DeFlock", `hsandorf/deflockdekalb` — FOIA analysis code).

**Retrieved:** 2026-08-20
**Implication for the spec:** (a) Any DeFlock connector or collaboration must target **FoggedLens**,
and SIG must note that the two DeFlock code homes are under **different licences** (MIT web,
AGPL-3.0 app) — an AGPL dependency has consequences if SIG ever vendors app code. (b) **The
~35 local-chapter repos are a directly harvestable local-group registry**, which is a concrete,
zero-cost substitute for the dead FlockReporter (F1.38) and satisfies REQ-R1-15 far better than
maintaining a hand-curated list. `gh search repos deflock` plus the org-level pattern is the seed.
(c) `panopti.ca` establishes that the DeFlock codebase is already being forked per-country, which
is the shape SIG's international phase should expect.
**Outline delta:** **CORRECTS §21** — the outline cites `flockhopper3/deflock-data` as DeFlock's
repository; it belongs to FlockHopper, a different (routing) project. RESOLVES Open question 1.

### F1.35 — DeFlock's changeset signature is `created_by = "DeFlock <semver>"`, and it is ~75 % of ALPR edits

**Claim:** DeFlock stamps `created_by=DeFlock <version>` on every changeset; in a measured Atlanta
sample it accounts for **76 of 101 changesets (75.2 %)**.
**Status:** VERIFIED — empirically, from source, and from the OSM wiki independently
**Evidence 1 — live changeset API**, 2026-08-20:

```
GET https://api.openstreetmap.org/api/0.6/changeset/187655388.json
→ "tags":{"comment":"Add Flock surveillance node","created_by":"DeFlock 2.11.0"}

GET https://api.openstreetmap.org/api/0.6/changeset/187358989.json
→ "tags":{"comment":"Add Axis Communications surveillance node","created_by":"DeFlock 2.11.0"}

GET https://api.openstreetmap.org/api/0.6/changeset/186824855.json
→ "tags":{"comment":"Add Flock surveillance node","created_by":"DeFlock 2.10.3"}
```

**Evidence 2 — the source that emits it.**
`FoggedLens/deflock-app/lib/dev_config.dart`:

```dart
// Client name for OSM uploads ("created_by" tag)
const String kClientName = 'DeFlock';
// Note: Version is now dynamically retrieved from VersionService
const String kContactEmail = 'admin@stopflock.com';
const String kHomepageUrl = 'https://deflock.org';
```

`FoggedLens/deflock-app/lib/services/uploader.dart`:

```dart
final csXml = '''
  <osm>
    <changeset>
      <tag k="created_by" v="$kClientName ${VersionService().version}"/>
      <tag k="comment" v="$sanitizedComment"/>
    </changeset>
  </osm>''';
```

`pubspec.yaml`: `version: 2.11.0+61` — matching the observed `DeFlock 2.11.0` exactly.

**Evidence 3 — OSM wiki**, `https://wiki.openstreetmap.org/wiki/Deflock`:
> Changesets submitted through the app will be tagged `created_by=DeFlock *.*.*`

**Evidence 4 — measured distribution.** All 101 changesets touching the 124 Atlanta ALPR nodes of
F1.20(b), resolved via `GET /api/0.6/changesets.json?changesets=<csv>` in 3 batched requests:

| `created_by` | n |  | `created_by` | n |
|---|---|---|---|---|
| DeFlock 2.11.0 | 16 | | iD 2.36.0 | 7 |
| DeFlock 2.10.1 | 15 | | iD 2.37.3 | 5 |
| DeFlock 2.10.3 | 11 | | iD 2.30.4 | 5 |
| DeFlock 1.3.2 | 10 | | iD 2.38.0 | 3 |
| DeFlock 2.3.1 | 8 | | iD 2.31.1 | 3 |
| DeFlock 2.10.2 | 6 | | iD 2.32.0 | 1 |
| DeFlock 1.5.1 | 5 | | iD 2.41.2 | 1 |
| DeFlock 2.7.2 | 3 | | | |
| DeFlock 2.7.1, 2.1.3 | 1 each | | | |

**DeFlock-originated: 76 / 101 = 75.2 %. Remainder: iD, 25 / 101 = 24.8 %. Nothing else.**

Observed changeset comments are templated by vendor: `"Add Flock surveillance node"`,
`"Add Genetec surveillance node"`, `"Add Motorola/Vigilant surveillance node"`,
`"Add Axis Communications surveillance node"`.

**Retrieved:** 2026-08-20
**Implication for the spec:** (a) The detection rule is `created_by` matching
`^DeFlock\s+\d+\.\d+\.\d+` — SIG can classify any OSM surveillance edit as DeFlock-originated or
not, which is exactly the attribution primitive Open question 2 asked for. Versions in the wild span
**1.3.2 → 2.11.0**, so the rule must be a prefix/regex match and MUST NOT enumerate versions.
(b) The vendor-templated `comment` string is a **second, independent vendor signal** available from
changeset metadata even when the node's own `manufacturer` tag is absent — useful against the 4,498
vendor-less devices of F1.22. (c) At 75 %, DeFlock is effectively the ALPR layer's editorial
pipeline; SIG's federation posture toward FoggedLens matters more than toward any other project.
(d) `admin@stopflock.com` is the maintainer contact of record for the OEG communication requirement.
**Outline delta:** RESOLVES Open question 2. EXTENDS §21 with a machine-checkable provenance rule.

### F1.36 — `deflock.me` 301-redirects to `deflock.org`; F1.8 had it backwards

**Claim:** `deflock.org` is canonical and returns 200; `deflock.me` is an alias that issues
`301 → https://deflock.org/...`, behind a Cloudflare managed challenge on HTML paths.
**Status:** **CONTRADICTED** — this reverses F1.8 of this file
**Evidence:** 2026-08-20, browser UA:

```
HEAD https://deflock.me/robots.txt   → HTTP/2 301, location: https://deflock.org/robots.txt
HEAD https://deflock.me/favicon.ico  → HTTP/2 301, location: https://deflock.org/favicon.ico
HEAD https://deflock.me/             → HTTP/2 403, cf-mitigated: challenge, server: cloudflare
HEAD https://deflock.me/about        → HTTP/2 403, cf-mitigated: challenge
GET  https://deflock.org/            → HTTP/2 200, text/html, 3,191 bytes
```

Corroborating: `FoggedLens/deflock` declares `homepage = https://deflock.org`;
`deflock-app/lib/dev_config.dart` sets `kHomepageUrl = 'https://deflock.org'`; the OSM wiki infobox
gives `web = https://deflock.org`. The `.me` domain survives as the **app's** namespace — the
Android package is `me.deflock.deflockapp` and the App Store slug is `deflock-me`.
**Retrieved:** 2026-08-20
**Implication for the spec:** F1.8 concluded "DeFlock's live domain is `deflock.me`; the outline's
`deflock.org` is wrong-but-live" and REQ-R1-14 was written on that basis. **The outline was right.**
The earlier finding was an artefact of testing only the `/` path of `deflock.me`, where the
Cloudflare challenge fires *before* the redirect and yields 403. REQ-R1-14 is superseded by
REQ-R1-27. The general lesson is worth keeping in the connector: **a 403 from a Cloudflare-fronted
host is not evidence about that host's role** — probe a static asset path before concluding anything.
**Outline delta:** **CONTRADICTS F1.8 of this file and re-CONFIRMS §21 of the outline.**

### F1.37 — DeFlock exposes no data API; the data *is* OSM, and `/api/` is robots-disallowed

**Claim:** `api.deflock.org` is a live Fastify service with four routes, none of which serve camera
data; DeFlock's camera data has no distribution channel other than OSM itself.
**Status:** VERIFIED
**Evidence:** `FoggedLens/deflock/api/README.md`:

> # DeFlock API
> A Fastify-based API service for DeFlock handling **non-OSM related backend logic**.
> ## Endpoints
> - `/geocode?query=...` — Geocode a location
> - `/sponsors/github` — Get GitHub sponsors
> - `/healthcheck` — Health check

`api/server.ts` route registrations: `/geocode`, `/geocode/multi`, `/sponsors/github`,
`POST /contact/message`. Supporting services are `NominatimClient`, `TurnstileClient`,
`ZammadClient` (ticketing), `GithubClient`, `ZipCodeService` — i.e. geocoding and contact-form
plumbing.

Live probes of `https://api.deflock.org` returned Fastify 404 JSON on `/`, `/health`, `/v1/`,
`/api/`, `/cameras`, `/reports`:
`{"message":"Route GET:/cameras not found","error":"Not Found","statusCode":404}`.

`https://deflock.org/robots.txt` (HTTP 200, 1,916 bytes) states:

```
User-agent: *
Content-Signal: search=yes,ai-train=no,use=reference
Allow: /
…
User-agent: ClaudeBot
Disallow: /
…
User-agent: *
Allow: /
Disallow: /api/
Sitemap: https://deflock.org/sitemap.xml
```

with the preamble *"As a condition of accessing this website, you agree to abide by the following
content signals… ANY RESTRICTIONS EXPRESSED VIA CONTENT SIGNALS ARE EXPRESS RESERVATIONS OF RIGHTS
UNDER ARTICLE 4 OF THE EUROPEAN UNION DIRECTIVE 2019/790."* `https://deflock.org/sitemap.xml`
returns HTTP 200 (1,904 bytes).

The *tile* distribution belongs to FlockHopper, not DeFlock — `flockhopper3/deflock-data`'s README
documents public, key-free PMTiles/TileJSON at `https://tiles.dontgetflocked.com/cameras-us.json`
and GeoJSON at `https://data.dontgetflocked.com/cameras.geojson.gz`, stating **"Anyone can use the
data. No API key, no rate limits beyond Cloudflare's defaults"**, with the source given as
"~117K points, sourced from OpenStreetMap surveillance tagging".

**Retrieved:** 2026-08-20
**Implication for the spec — a simplification the outline does not make:** there is **no DeFlock
data connector to build.** DeFlock is an *editor* that writes to OSM; its dataset is OSM. SIG should
ingest OSM directly (F1.21) and treat DeFlock as an *upstream collaborator and provenance signal*
(F1.35), not a source system. This removes a whole planned integration.
Two constraints remain: (1) `Disallow: /api/` plus the robots preamble means SIG MUST NOT scrape
deflock.org's API surface, and the `ai-train=no` content signal MUST be recorded in the source
registry as a stated usage condition; (2) FlockHopper's tiles are OSM-derived and therefore
**ODbL**, whatever their "anyone can use" phrasing — REQ-R1-10 applies to them, and SIG must not
treat that sentence as a licence grant.
**Outline delta:** **CORRECTS §2 Layer C and §21** — the outline models DeFlock as a data source.
It is not one. RESOLVES Open questions 1 and 7.

---

## Part 4E — Ecosystem liveness, resolved (resolves Open question 6)

### F1.38 — FlockReporter is genuinely dead: DNS records removed, last capture 2026-07-28

**Claim:** `flockreporter.org` retains Cloudflare NS delegation but publishes **no A, AAAA, MX or TXT
record**, so it cannot resolve at all. Its last Wayback capture was a healthy HTTP 200 three weeks
ago.
**Status:** VERIFIED (upgrades F1.9 from "one failed fetch" to a determination)
**Evidence:** 2026-08-20 —

```
$ dig +short flockreporter.org NS
tiffany.ns.cloudflare.com.
owen.ns.cloudflare.com.

$ dig +short flockreporter.org A        → (empty)
$ dig +short flockreporter.org AAAA     → (empty)
$ dig +short flockreporter.org MX       → (empty)
$ dig +short flockreporter.org TXT      → (empty)
$ dig +short www.flockreporter.org A    → (empty)

$ curl -sSI -L https://flockreporter.org/
curl: (6) Could not resolve host: flockreporter.org
```

Wayback: `https://archive.org/wayback/available?url=flockreporter.org` →
`{"closest":{"status":"200","available":true,
"url":"http://web.archive.org/web/20260728225506/https://flockreporter.org/",
"timestamp":"20260728225506"}}`. The CDX index confirms a single recent capture:
`["org,flockreporter)/","20260728225506","https://flockreporter.org/","text/html","200",…,"14798"]`.
**Retrieved:** 2026-08-20
**Implication for the spec:** The domain is registered and delegated but **deliberately unpublished**
— that is a decommissioning or a migration in progress, not a transient outage, and it happened
within the last ~23 days. The outline's treatment of FlockReporter as the ecosystem directory
(OL-3-02, OL-18-13) is now unsupportable. REQ-R1-15 stands and is strengthened, and F1.34 supplies
the replacement: harvest the ~35 `deflock*` local-chapter repositories. The archived capture
(2026-07-28) should be pulled into SIG's archival store before it is the only record —
which is a live demonstration of the §46.6 archival-insurance role, and the spec should cite it as
such.
**Outline delta:** CORRECTS §3 and §18 and CONFIRMS §46.6 with a real instance.

### F1.39 — SunderS and PanoptiCity are OSM *renderers* that write back, not independent datasets

**Claim:** Both `sunders.uber.space` and `panopticity.fr` derive entirely from OSM and route
contributions back into OSM; neither holds an independent data licence or an independent dataset.
**Status:** VERIFIED
**Evidence — `https://sunders.uber.space/` (HTTP 200, 35,615 bytes)**, "Surveillance under
Surveillance", quoted:

> Surveillance under Surveillance uses data from **OpenStreetMap contributors** that is not
> visualized on the regular OpenStreetMap site. If you like to add new cameras or guards or if you
> like to revise existing entries **use your existing OSM account or create a new one**.
> **Our database is updated once an hour.** So it might take a while until your OSM entries are
> visible on the Surveillance under Surveillance map.

It documents the same tag vocabulary R1 measured in F1.2–F1.4 (`man_made=surveillance`,
`surveillance=public|outdoor|indoor`, `surveillance:type=camera|ALPR|guard`, `surveillance:zone`),
renders ALPR as a distinct icon class, and links to `https://www.openstreetmap.org/copyright`.
Mirrors: `https://sunders.hamburg.ccc.de/` and a Tor onion
(`sunders.ahcbagldgzdpa74g2mh74fvk5zjzpfjbvgqin6g3mfuu66tynv2gkiid.onion`). Multilingual
(de/en/es/fr/it/ru). Related code: `https://github.com/khris78/osmcamera`, `https://github.com/unsurv`.
Its CCC lineage matches the `Organised Editing/Activities/CCCHH-surveillance` registration (F1.30).

**Evidence — `https://panopticity.fr/` (HTTP 200, 18,877 bytes)**, quoted:

> This interactive map reveals the scale of mass surveillance worldwide. Each marker represents a
> known camera location and **it's estimated field of view**. … The data used here is from the
> community website **OpenStreetMap**. To contribute to this awesome dataset you need an
> OpenStreetMap account… **Sign in with OpenStreetMap**.

It consumes `https://{a,b,c}.tile.openstreetmap.org` and `https://nominatim.openstreetmap.org`, and
uses Leaflet + `Leaflet-semicircle` for FOV cones.
**Retrieved:** 2026-08-20
**Implication for the spec:** Neither is a *source* for SIG — both are downstream siblings, and
adding them as connectors would double-count OSM. Two things they do supply: (a) **PanoptiCity is
prior art for derived FOV rendering** (REQ-R1-06) and confirms that semicircle-from-`direction` is
the community's established visual convention, which SIG should match rather than invent;
(b) SunderS establishes an hourly OSM-refresh cadence as the ecosystem norm, a useful benchmark for
SIG's own freshness target. Both belong in the source registry as **peer projects with OSM as the
shared substrate**, and both are additional candidates for the federation compact.
**Outline delta:** CORRECTS §2 Layer C — these are peers/renderers, not distinct data sources.

---

## Open questions

*Updated 2026-08-20 by the completion pass. Items 1–7 of the original list are now resolved; see
the resolution table, then the residual list that the spec must still hedge against.*

### Resolved by Part 4

| # | Original open question | Resolution |
|---|---|---|
| 1 | DeFlock's repository, data export, and API were not enumerated | **Resolved** — F1.34, F1.37. Canonical repos are `FoggedLens/deflock` (MIT) and `FoggedLens/deflock-app` (AGPL-3.0). `flockhopper3/deflock-data` exists but is FlockHopper's, not DeFlock's. DeFlock has **no data API**; its data is OSM. |
| 2 | The OSM changeset `created_by` string DeFlock writes was not determined | **Resolved** — F1.35. `created_by = "DeFlock <semver>"`, versions 1.3.2–2.11.0 observed; 75.2 % of sampled ALPR changesets. Detection rule: `^DeFlock\s+\d+\.\d+\.\d+`. |
| 3 | Overpass QL queries were not executed; rate-limit and etiquette rules unread | **Resolved** — F1.17–F1.21. Quotas quoted, 429/504 semantics established, all three required queries executed with real output, extraction strategy determined and cross-validated. |
| 4 | The Automated Edits CoC and Organised Editing Guidelines were not read | **Resolved** — F1.27–F1.29, F1.33. Binding text quoted; compliant write-back design specified; **risk R-14 unblocked**. |
| 5 | ohsome / OSM element-history API behaviour was not tested | **Resolved** — F1.23–F1.26. All three sources tested; **Q19 answered and the proposed design verified with three corrections**. |
| 6 | FlockReporter's status is unresolved | **Resolved** — F1.38. DNS A/AAAA/MX/TXT all absent; last Wayback capture 2026-07-28. Decommissioned, not transient. |
| 7 | Whether `deflock.org` redirects to `deflock.me` or is separate | **Resolved, and the earlier finding reversed** — F1.36. `deflock.me` **301s to** `deflock.org`. F1.8 was wrong. |

### Residual — carried into the spec's risk register (§53)

1. **The four legal questions from F1.16 still require counsel** and are unchanged: (a) whether
   device-linked API responses are Derivative-Database distribution or a Produced Work; (b) whether
   OSM-sourced jurisdiction geometry contaminates the operator property under the Collective
   Database Guideline's fourth bullet; (c) the correct regional-cut unit; (d) EU sui generis rights.
2. **F1.29 opens a fifth:** the licence instrument for contributing SIG's operator attributions
   upstream. OSM rates CC-BY-4.0 as needing an *additional waiver*, so SIG must either execute the
   OSMF cover-letter-and-waiver, dual-license the contributed field set under ODbL/CC0, or restrict
   contributions to facts sourced from public-domain records. **This is not resolved and it gates
   the write-back programme, not just the export.**
3. **No SIG MapRoulette challenge has been created or run.** F1.31–F1.33 verify the API surface and
   specify the design; the *community* half — announcement, reception, and whether US regional
   communities accept a 110 K-task attribution programme — is untested and is the real risk. The
   spec should require a **single-county pilot** before any multi-state challenge.
4. **MapRoulette does not enforce `version` on cooperative tag changes** (F1.31, quoted). SIG's
   own staleness check (REQ-R1-24) is therefore load-bearing and needs a test that actually proves
   it, not just an implementation.
5. **Deletion detection is specified but unmeasured.** F1.20(c) establishes that `(changed:)` omits
   deletions and F1.26 prescribes snapshot diffing; nobody has yet measured how often OSM ALPR nodes
   are deleted, so the required cadence of the reconciliation pass is unknown.
6. **`overpass.deflock.org` is used here without permission.** F1.19 documents it as real capacity
   with no rate limit, but SIG has no agreement to use third-party infrastructure. Ask FoggedLens
   (`admin@stopflock.com`) before any dependency, and do not design around it meanwhile.
7. **The 4,498 vendor-less devices (F1.22) have no identified acquisition path.** StreetComplete-style
   ground survey is the plausible instrument (F1.32) but requires local volunteers SIG does not have.
8. **OSMCha's authenticated API is untested** (F1.25) — only the 401 was observed. If SIG adopts it
   for edit monitoring, the OAuth flow and rate limits need their own verification pass.
9. **ohsome's 24-day lag was observed once** (F1.24). Whether that is typical or an artefact of this
   week's replication state is unknown; the spec should not encode 24 days as a constant.
10. **Non-US coverage is unmeasured.** CONUS is 93.0 % of world ALPRs (F1.21), so the international
    phase rests on a ~10 K-element population whose tagging conventions may differ; nothing here
    tested a non-US regional cut.

## Spec requirements emitted

- **REQ-R1-01** — The OSM connector MUST handle nodes, ways, and relations.
- **REQ-R1-02** — `surveillance:type` and related keys MUST be parsed as semicolon-delimited
  unordered sets, normalized via a versioned inspectable mapping, with an `unmapped_source_value`
  escape hatch and an auto-generated research task for unmapped tail values.
- **REQ-R1-03** — The connector MUST reconcile `surveillance`, `surveillance:type`,
  `surveillance:zone`, and `camera:type` jointly; no single key may be trusted alone.
- **REQ-R1-04** — `operator` absence MUST be a first-class countable state; the orphaned-device
  population (**110,812 measured for CONUS**, F1.22) is a primary work queue, not an exception path.
- **REQ-R1-05** — Wikidata QIDs MUST be a first-class crosswalk identifier for vendors and
  operators, seeded from `manufacturer:wikidata` / `operator:wikidata`.
- **REQ-R1-06** — Derived FOV geometry MUST be physically separate and visually distinct from
  observed geometry (the derived layer will approach the size of the observed layer).
- **REQ-R1-07** — The OSM-linked physical-asset layer, including SIG's operator and lifecycle
  attributions on OSM features, MUST be stored in a separate table and published as a separate
  export file under **ODbL-1.0**.
- **REQ-R1-08** — SIG-original graph data containing no OSM content MUST be published under
  **CC-BY-4.0** as a separate export with its own licence declaration. *(See REQ-R1-26: the subset
  contributed upstream to OSM must additionally be released under an ODbL-compatible instrument.)*
- **REQ-R1-09** — The export pipeline MUST compute a per-export SPDX expression from constituent
  rights records and MUST fail the build if a share-alike input is present in an export whose
  declared licence does not satisfy it.
- **REQ-R1-10** — Vector tiles, GeoJSON, and bulk downloads carrying OSM-derived features MUST be
  treated as database distribution, not as Produced Works.
- **REQ-R1-11** — Every rendering context, including static images and printed dossiers, MUST
  carry OSM attribution and a link to the licence.
- **REQ-R1-12** — No architecture may rely on staying below the ODbL substantiality threshold.
- **REQ-R1-13** — SIG MUST NOT perform direct automated writes to OSM. Contribution-back MUST go
  through a human-mediated suggestion workflow. *(The pending review named in the original wording
  is complete — F1.27–F1.29; the mechanism is specified in REQ-R1-20 … REQ-R1-26.)*
- **REQ-R1-14** — *Superseded by REQ-R1-27.* (Written on F1.8, which F1.36 reverses.)
- **REQ-R1-15** — SIG MUST maintain its own local-group registry rather than depending on
  FlockReporter's availability. It SHOULD be seeded by harvesting the ~35 `deflock*` local-chapter
  repositories on GitHub (F1.34), not hand-curated.

*Added by the completion pass:*

- **REQ-R1-16** — Every OSM-linked record MUST be keyed on the composite
  `(osm_type, osm_id)` and MUST additionally persist `osm_version`, `osm_changeset` and
  `osm_timestamp`, all captured from `out meta` during ordinary ingest. `osm_id` alone MUST NOT be
  used as a key. (F1.26)
- **REQ-R1-17** — Every SIG claim attached to an OSM element MUST record the `osm_version` it was
  asserted against, and re-ingest observing a higher version MUST flag that claim for revalidation
  rather than silently carrying it forward. (F1.26)
- **REQ-R1-18** — The connector MUST discard the OSM `user` and `uid` fields at ingest and MUST NOT
  persist contributor identity. Editor identity, where genuinely required, MUST be fetched on demand
  from the changeset API and the access logged. (F1.26, F1.24)
- **REQ-R1-19** — SIG MUST NOT replicate the OSM history database. Element history MUST be fetched
  on demand from `/api/0.6/<type>/<id>/history.json`, changesets MUST be resolved in batches of ≤50
  via `/api/0.6/changesets.json?changesets=<csv>`, and bulk temporal analysis MUST use ohsome or a
  local `.osh.pbf` pass — never a systematic crawl of the editing API. (F1.23, F1.24, F1.18)
- **REQ-R1-20** — SIG MUST publish an `Organised Editing/Activities/…` page on the OSM wiki before
  any contribution activity, carrying the coordinating organisation, a named contact, a unique
  changeset hashtag, goal, timeframe, tools and **data sources with their licences**, the review
  plan, and monthly result reports. (F1.28)
- **REQ-R1-21** — Every SIG-originated OSM edit MUST carry the unique activity hashtag in its
  changeset comment and a `source` referencing the SIG evidence URL, set via MapRoulette's
  `checkinComment` / `checkinSource` so it is enforced by the platform. (F1.28, F1.31)
- **REQ-R1-22** — SIG MUST announce the activity to each affected national/regional OSM community at
  least **14 days** before tasks go live, on open, public, archived channels, and MUST re-announce
  for any scope extension. A named human MUST respond to community messages within **two working
  days** while the activity is running. (F1.28, F1.29)
- **REQ-R1-23** — Contribution-back MUST be implemented as **MapRoulette cooperative (tag-fix)
  challenges** sourced from a SIG-hosted `remoteGeoJson` feed with `updateTasks` enabled, scoped one
  challenge per region. Every object MUST be approved by a human before any edit is written. SIG MUST
  NOT hold OSM write credentials. (F1.31, F1.33, F1.27)
- **REQ-R1-24** — Because MapRoulette accepts but does not enforce the `version` field, SIG MUST
  re-check `osm_version` on every task-feed regeneration and MUST expire tasks whose element version
  has advanced. This MUST have a regression test. (F1.31)
- **REQ-R1-25** — SIG MUST maintain an opt-out suppression list of OSM objects and users, applied at
  task-feed generation time, and MUST honour opt-out requests without negotiation. (F1.27)
- **REQ-R1-26** — Any fact SIG contributes to OSM MUST be releasable under ODbL with no additional
  copyright claim by SIG. The contributed field set MUST therefore be dual-licensed
  ODbL-1.0-or-CC0, or covered by an executed OSMF CC-BY-4.0 waiver, **before** the first challenge
  goes live. (F1.29)
- **REQ-R1-27** — *(Supersedes REQ-R1-14.)* The source registry MUST record `deflock.org` as the
  canonical DeFlock host and `deflock.me` as a 301 alias, MUST record the Cloudflare managed
  challenge and the `Disallow: /api/` + `ai-train=no` robots directives as stated usage conditions,
  and MUST NOT scrape deflock.org's API surface. Connectors MUST probe a static asset path before
  concluding anything about a Cloudflare-fronted host, since a 403 on `/` is not evidence about the
  host's role. (F1.36, F1.37)
- **REQ-R1-28** — Bulk OSM extraction MUST use planet or Geofabrik `.osm.pbf` plus
  `osmium tags-filter`, filtering on `man_made=surveillance` (not on `surveillance:type=ALPR`).
  Overpass MUST be used only for incremental `(changed:)` fetches and ad-hoc regional queries.
  A single unbounded worldwide Overpass query MUST NOT be issued. (F1.21, F1.18)
- **REQ-R1-29** — The Overpass client MUST send a descriptive non-browser User-Agent identifying SIG
  with a contact address; MUST treat **429** as time-based backoff and **504** as a signal to shrink
  the query; MUST meter itself against ≤10,000 requests/day and ≤1 GB/day; MUST poll `/api/status`
  rather than model quota locally; and MUST read its endpoint list from configuration with a
  pre-run health check and automatic failover. (F1.17, F1.18, F1.19)
- **REQ-R1-30** — National-scale Overpass extraction MUST use adaptive bbox tiling with a
  sub-second `out count;` probe per tile, splitting any tile above a configured density threshold,
  and MUST validate each tile's fetched count against its probed count before accepting the result.
  (F1.21)
- **REQ-R1-31** — Every ingest batch MUST persist the response's `timestamp_osm_base` as its
  provenance watermark, and MUST record that area-based queries carry the older
  `timestamp_areas_base` clock. (F1.17)
- **REQ-R1-32** — Element deletion MUST be detected by diffing a periodic full regional snapshot
  against the prior snapshot, because `(changed:)` does not report deletions. The model MUST
  distinguish *deleted from OSM* (a mapping event) from *removed from the street* (a world event)
  and MUST NOT let the former imply the latter. (F1.20, F1.26)
- **REQ-R1-33** — The provenance model MUST classify OSM edits by `created_by`, with
  `^DeFlock\s+\d+\.\d+\.\d+` identifying DeFlock-originated edits. The rule MUST be a prefix match,
  never an enumeration of versions. Vendor-templated changeset `comment` strings MUST be usable as a
  secondary vendor signal. (F1.35)
- **REQ-R1-34** — DeFlock MUST NOT be modelled as a data source or given a data connector; it is an
  OSM editor and a provenance signal. SIG ingests OSM directly. (F1.37)
- **REQ-R1-35** — The source registry MUST record SunderS (`sunders.uber.space`), PanoptiCity
  (`panopticity.fr`) and FlockHopper (`dontgetflocked.com`) as **OSM-derived peer projects**, not as
  independent sources, and MUST NOT ingest them as separate datasets. FlockHopper's public tiles are
  OSM-derived and therefore ODbL regardless of their "anyone can use the data" phrasing. (F1.39, F1.37)
