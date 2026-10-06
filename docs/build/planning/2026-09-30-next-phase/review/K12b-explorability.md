# K12b — Agentic browser UX review: interactivity and explorability

> **Agent walkthrough, not user research** (P4/P5). The personas are goals an agent pursued in headless Chrome. Nothing
> here counts toward `D-R10-USERS-1` or any human-evaluation obligation. Time and effort estimates for a human
> visitor are **inference**.

Row **K12b** of `META_PLAN.md` §6 Stream K (R, depends C2). It builds on C2's task verdicts
([`JOURNEYS.md`](JOURNEYS.md), [`../findings/incoming/C2.csv`](../findings/incoming/C2.csv)) and does not repeat them. C2
asked whether a persona could *complete* a scripted task. K12b asks whether a persona can *explore*: follow every
link and control, trace a figure to its source and original document, and answer open-ended questions.

Outputs:

- this note;
- [`../findings/incoming/K12b.csv`](../findings/incoming/K12b.csv): 21 findings, `NEW-1`…`NEW-21`, §8.2 schema;
- [`../data/k12b_ideas.csv`](../data/k12b_ideas.csv): 32 feature ideas.

Evidence is in `docs/build/logs/next-phase/K12b/`, which is gitignored. Every file there is hashed in `SHA256SUMS`
(88 entries; the file's own sha256 is `fe203f91c6c373fcd9d7707e13891171c33e685f84776f06376330c3067cdf18`).

---

## 0. Run facts

| item | value |
|---|---|
| Run window (`date -u`) | 2026-09-30T21:30:33Z → 2026-09-30T21:44:58Z |
| Site / release | `https://surveillancegraph.org`, release `sig-2026-09-27-ce480ab1` (the manifest captured by C2 and C3) |
| Drift guard | `HEAD /` at 21:31:24Z and again at 21:44:58Z both returned `Last-Modified: Sun, 27 Sep 2026 01:33:43 GMT`, ETag `"6ab87277-14f54"`. This matches the C2 baseline, so there was **no drift** and C2's page captures stay valid for this release |
| Browser | Google Chrome (the `chrome` channel), headless, driven by Playwright (`@playwright/test` from the main checkout's `web/node_modules`, read-only). Fresh context per session. Desktop 1440×900; mobile is Playwright `iPhone 14` at 390×844 |
| UA | `<Chrome UA> SIG-planning-K12b-review/1 (read-only)`. It carries no personal identifier (P16) |
| Politeness and budget | **42 page loads** (limit 200), one at a time, at least 3 s apart (checked in `loads.tsv`); **2 HEAD** requests (drift guard); and **8 read-only GETs** to the unlinked API host (`api_log.tsv`) to test whether data the site hides actually exists. No form was submitted, nothing was POSTed, and there was no login. Interaction was limited to client-side clicks, typing into the search island, double-click zoom, keyboard pan and Tab traversal |
| Reuse without re-fetching | C2's DOM and text captures (`C2/html`, `C2/text`) and C3's local copies of release artifacts (`C3/bucket/**`, which C3 sha-verified against the manifest) were read offline. This saved about 60 page loads. Only static-site pages that C2 already captured were reused this way |
| Tools | `K12b/tools/run.mjs` (paced runner that logs every main-frame navigation) plus these scenarios: `map1`, `kbdmap`, `net1`, `netmobile`, `search1`, `dossier1`, `visit`; `api_probe.py` |
| Independence (P6) | Read before the run: META_PLAN §3 and Stream K; `OPERATOR_FEEDBACK.md`; PROTOCOL §2, §3 and §9; JOURNEYS in full; the C2.csv titles; C6 TH-11; the I1 summary (for data dependencies); K12a headings only. No other row's findings file was read |
| Part VIII | Some public source keys look like personal account handles (C2 NEW-2, S0; seen again on `/dossier/ny/`). They are **not reproduced** here or in the CSVs. No person, plate or officer data was seen. Agency and vendor names quoted here (Austin Police Department, Austin Regional Intelligence Center, Vigilant Solutions (LEARN)) are institutions, and they come from SIG's own API |

---

## 1. Headline: the worst exploration failures

1. **The site hides data SIG already holds, so exploring ends in a dead end even where the answer exists.**
   - `/network/` shows 131 UUIDs.
   - SIG's own API names the hub **"Vigilant Solutions (LEARN)"**, and the release's `sharing_edges.csv` carries that
     name in `partner_ref`.
   - One spoke is **"Austin Police Department"**. It shows only as `01a0a720-af12-7946-bfe3-1accab0e34ae`.
   - Site search for "Vigilant", "LEARN" or "Austin Police" returns 0. The API's `/v1/search` finds both.
   - The operator's research-queue example UUID `01a0a720-9b9a-7890-a8ae-99705e6b5368` is the first of these same 130
     agencies.

   (NEW-1, NEW-4, NEW-10, NEW-16)
2. **Nothing on the site dates a relationship.**
   - All 130 "configured access" edges rest on a single 2020-01-28 observation from `eff_data_driven`.
   - The API marks them `currency: HISTORICAL` and `UNRESOLVED`, with the rationale "too weak to assert alone".
   - The page says "Configured access; 1 evidence" with no date, source or currency.
   - A journalist can report present-day sharing from 2020-era records (NEW-2, S1).
3. **Pages contradict each other about what SIG has looked at.** `/dossier/tx/` says data-sharing partners are "Not
   researched — SIG has not looked yet". Meanwhile `/network/` publishes a sharing edge for an agency the API labels
   Austin Police Department, and the export holds a partner-degree claim for the Austin Regional Intelligence Center
   (NEW-3, S1; the TX attribution is inference, see §4).
4. **No figure, edge, point or source leads anywhere outside the site, or even to a detail page inside it.**
   - The site has **zero outbound links**: 86 C2 DOM captures (every route class) and the 33 K12b dossier and visit loads contain no link to a publisher, dataset,
     document, the API or bulk data (NEW-21).
   - `/about/`, `/data/`, `/downloads/`, `/api/`, `/sources/`, `/changes/`, `/feed.xml`, `/entity/…` and a per-source
     URL all return a bare 404.
   - Map popups have no link. Their "Cite this view" cites the national map, not the point (NEW-6).
5. **Promised "clickable gaps" are dead.**
   - `/map/` links **5,290** "⚠ Unresolved" gaps to per-subject task pages. That number equals the release's
     `conflicted_subjects` total across 16 jurisdictions.
   - None of those pages exists: 2 of 2 sampled return 404, and 0 of the 5,290 slugs is among the 78 deployed task
     pages (NEW-7).
6. **Several affordances exist but do nothing.**
   - "Sort by stale entities" and "Sort by volatility" return the identical alphabetical table (NEW-11).
   - The network "explorer" cannot expand: focusing any spoke leaves 2 nodes and 1 edge (NEW-5).
   - Map "Layers" are labels, not toggles (C2 NEW-23).
   - The coverage page says contradictions are "kept visible", but no page shows either of the 2 (NEW-17).
7. **The open-ended questions a journalist or organizer would ask have partial answers in SIG's data, but not on its
   site.** See §4. Over the record:
   - 6,796 buyers, 2,788 sellers and 5,848 amounts;
   - 1,528 Flock transparency portals with stated prohibited uses;
   - 300 bills and 987 response deadlines;
   - 185 agencies with a sharing-partner degree (median 68, maximum 851 partners);
   - 255 captured evidence artifacts, including 3 captures from Austin's procurement portal.

   None of these can be browsed (NEW-4, NEW-13, NEW-14, NEW-15).

---

## 2. What SIG holds versus what a visitor can reach

This table explains why the site feels opaque. It is mostly **a routing and labelling problem over data that already
exists**, and only partly an acquisition problem. Evidence class: `live-read` for counts shown on the site; `code`
(release artifact read offline) and `live-read` (API) where noted.

| held by SIG (evidence) | reachable on the site? | what a visitor sees instead |
|---|---|---|
| Entity labels for the network nodes: hub = "Vigilant Solutions (LEARN)" (organization); spokes such as "Austin Police Department" (`/v1/search`, `/v1/entity`, 21:34Z; `sharing_edges.csv` `partner_ref`) | no | 131 UUIDs, one type label ("agency" or "partner") |
| Per-edge epistemic envelope: support, **currency `HISTORICAL`**, rationale text, observation date 2020-01-28, source `eff_data_driven` (API `/v1/entity/deployment/…af12…`) | support glyph only | "⊕◯◯◯ weakly supported (1 of 4)"; no date, no currency, no source |
| `sharing_partner_degree` claims for 185 agencies: median 68, maximum 851 partners (`sharing_edges.csv`, 370 rows); plus 2 `sharing_restriction` rows | no | nothing |
| 124 predicate populations: `buyer` 6,796, `seller` 2,788, `amount` 5,848, `award_date` 1,051, `funder` 1,279, `recipient` 2,158, `federal_award_id` 1,958, `portal_exists` 1,528, `portal_stated_prohibited_use` 1,458, `configured_retention_days` 1,464, `usage_search_windowed_count` 1,380, `bill_*` 300, `response_deadline` 987, `renewal_options` 195, `sunset_date` 5, `camera_county` 25,802 (home tiles, C2 `R01_home_desktop.txt`) | as "N of N" tiles only | 124 tiles, each ending at itself |
| 255 captured evidence artifacts: 178 camera-registry captures, 33 connector runs, 27 terms pages, 4 portal documents, 3 agenda documents, 2 news articles, 2 bill indexes, 1 official statement. They include `procportal_austin_tx` ×3, `legistar` ×3 and one OKC contract (`web/evidence.json`) | no | "No claims with a full evidence view yet"; `/evidence/<id>/` is 404 |
| About 40 non-registry sources: `eff_data_driven`, `eff_atlas_of_surveillance`, `eyes_on_flock`, `openstates`, `usaspending`, `sam_gov`, `ted_eu`, `legistar`, CCOPS reports, `muckrock`, DHS OIG, GAO and others (`evidence.json` source list; I1 summary) | no | `/data-freshness/` lists only the 178 `camreg_*` sources |
| Upstream dataset URL per row (for example `rights_terms_url` = the data.act.gov.au dataset page on AU-ACT sites; `sig_graph/sites.csv`) | no | source keys only |
| 2 open recorded contradictions (`claimed_device_count`, `use_restriction`), both on one agency subject that the `okcpd_policy` source also describes (API `/v1/contradiction`) | no | "2 open of 2 recorded contradictions … kept visible" as a count |
| A changes feed endpoint (`/v1/changes`, SIG-API-009) | no | nothing. The endpoint returns `events: []` since 2026-08-30, yet its sibling response reports `latest_assertion=2026-09-30T12:03Z` |

---

## 3. Persona exploration narratives

Each attempt below records the path, the dead ends, the missing affordances, what a user would expect, and a
severity. Severities follow PROTOCOL §9. "S1" means a core task or the truth of the record breaks.

### 3.1 Local advocate, council meeting in days (P1, design centre)

**"What did my city (Austin) approve, what's deployed where, and when does it renew?"**

| # | attempt (path) | what happened | missing affordance → expectation | sev |
|---|---|---|---|---|
| A1 | `/search/` → "Austin" | 1 result: `camreg_austin_tx`, linking to the **root** of `/data-freshness/`. "Austin Police" → 0. "Houston" → 0. "Texas" → 0 | Place resolution, agency names, typed results. **Expectation:** "Austin, TX → the Texas dossier (no city page yet) · Austin Police Department (agency) · Austin procurement portal (source)" | S1 (C2 NEW-10; refined by NEW-10) |
| A2 | `/dossier/` → TX | A flat list of 55 codes. "CA" (California) sits directly above "CA-AB…CA-ON" (Canadian provinces), and "CO" (Colorado) above "CO-MET" (Meta, Colombia) | Country grouping, names, counts. **Expectation:** "United States › Texas (3,996 site observations, 4 sources)" | S2 (NEW-18) |
| A3 | `/dossier/tx/` → "What is deployed" | One row: "3994 of 3996 evaluable geolocated site observations". Four source keys, not links. "Who else can see the data", "Configuration and retention" and "Usage" are empty headings | Agencies, technology classes and vendors, each with its source. **Expectation:** "Austin Police Department — ALPR data shared with Vigilant LEARN (2020 records, historical)" | S1 (C2 NEW-5, NEW-15; this row NEW-3) |
| A4 | `/dossier/tx/` → "Data-sharing partners ? Not researched" → task page | The page says a task "has been generated" (a static GET). It names `jurisdiction:tx` and gives no next step | A task that names the question, the agencies and the evidence SIG already has. **Expectation:** "Re-verify: 2020 EFF records show Austin PD configured access to Vigilant LEARN — is it current? File a Texas PIA request (template)" | S1 (NEW-3; C2 NEW-22) |
| A5 | "What did council approve?": `/search/` "council", "agenda", "ordinance", "approve", "procurement", "legistar" | 0 results for each, except "council" → an Iowa road camera on "Council St" | Agenda and procurement records per place. SIG holds 3 Austin procurement-portal captures and `legistar` agenda captures (`evidence.json`) | S2 (NEW-13, NEW-14) |
| A6 | "When does it renew?": `/dossier/tx/` "Cost and expiry" → nav → `/watch/` | Every field is "unknown". The watch has "No contracts on the watch yet". `/watch/tx.ics` and `/watch/tx.xml` are 404 (not linked, so not dead links). No `<link rel=alternate>` feed | A dated decision list. The record holds 987 `response_deadline`, 195 `renewal_options` and 5 `sunset_date` subjects that are never routed to the watch (whether they are relevant is **inference**) | S2 (NEW-15) |
| A7 | "Where exactly are the cameras near this address?": `/map/`, zoomed to Congress Ave and 6th St, Austin, at z15 | A blank grey canvas with about 8 dots. The popup reads `01a0cea0-…`, jurisdiction **"unresolved"**, tier 0, precision `full_precision`, and "Cite this view". No street, no type, no operator, no source, no date. **My first attempt failed silently:** the double-click target fell inside the attribution block, which covers the bottom 100 px of the 384-px canvas, so four frames were byte-identical | Basemap, place search, and a feature page with type, operator, source and dates. **Expectation:** "Traffic camera · City of Austin · source: Austin open data (link) · observed 2026-09-18" | S1 (C2 NEW-9; this row NEW-6, NEW-8) |
| A8 | `/map/` table "Assets without a published point" → "⚠ Unresolved" | 404 (2 of 2 sampled). There are 5,290 such links | A per-subject page showing the competing coordinates (SIG-UI-009) | S2 (NEW-7) |
| A9 | Print the brief (C2 covered the PDF) | Not repeated | A one-page council brief (idea I-06) | — |

**Verdict (inference):** after 10 minutes the advocate knows SIG counts about 4,000 Texas camera observations. They do
not know who operates them, what was approved, or when anything renews. They also cannot find the pieces SIG does
hold: the Austin procurement captures, Austin PD's historical sharing record, and the Austin Regional Intelligence
Center's partner degree. **The most useful change:** named entities and typed absence on the dossier, each linking to
an entity page and its sources.

### 3.2 Investigative journalist (P2, co-primary)

**"Who supplies ALPRs to agencies in Texas and who can search them?"**

- **J1: `/search/` "ALPR", "license plate", "Flock", "Vigilant", "Motorola".**
  - "ALPR", "license plate", "Vigilant" and "Motorola" return 0.
  - "Flock" returns one camera-registry source key (redacted: C3 lists it as handle-like), which links to the root of `/data-freshness/`.
  - There is no technology facet, no vendor entity and no product entity.
  - The record has `ai_surveillance_supplier` 74, `manufacturer` 527 and `products` 2,939, but `vendor` is 0 (home
    tiles).
  - **Missing:** vendor and product entity pages, and a technology filter. **S1** (NEW-10, NEW-14).
- **J2: `/network/`.**
  - The page shows a ring of 130 UUID labels drawn over each other, a literal hairball (shot `a56ed6bd…`).
  - The note underneath says "This is never a national hairball".
  - Selecting Austin PD's UUID reduces the view to 2 nodes and 1 edge ("degree: 1.000"). There is no way to expand
    further, and no search or filter. It takes 160 Tab stops to cross the page.
  - On mobile the page is 63,987 px tall (about 76 screens).
  - **Missing:** names, search, filters, list view with sorting, edge dates. **S1** (NEW-1, NEW-5).
- **J3: "Which agencies share data with ICE-linked systems?"**
  - `/search/` "ICE" returns **2 false hits**: an Iowa rest-area camera ("near Joice") and a UK police source key.
    "Immigration" returns 0.
  - The only sharing hub in the release is Vigilant LEARN. SIG does not evidence which systems are ICE-linked, and this
    review makes no such claim.
  - The substring hits invite a wrong conclusion on a sensitive query. **S2** (NEW-10).
  - **Expectation:** exact-token matching, a zero-result page that says "SIG records no evidenced relationship with
    ICE; here is what that means", and typed access edges with sources.
- **J4: "What is SIG's evidence for this vendor–agency link?"**
  - On `/network/` each edge reads "(Configured access; 1 evidence)". The "1 evidence" is not a link.
  - The same unlinked support line repeats for each of the 130 edges.
  - `/evidence/` is empty, and `/evidence/<artifact_id>/` is 404.
  - `eff_data_driven` appears on no page.
  - Only the API reveals the source and the 2020-01-28 date.
  - **Missing:** an edge detail showing the claim, the source (with a link to the publisher), the capture, the date,
    the currency and the rationale. **S1** (NEW-2, NEW-12, NEW-13).
- **J5: "What changed in the last month?"**
  - There is no changelog, and `/releases/` is 404 (C2).
  - `/corrections/` is empty.
  - The data-freshness page shows `last_content_change` per source (2026-09-18 and 2026-09-19) but no diff and no
    counts.
  - The API's `/v1/changes?since=2026-08-30` returns `events: []`, while `/v1/contradiction` in the same session reports
    spine `claims=2514683 … latest_assertion=2026-09-30T12:03Z`.
  - **Missing:** a "what changed" page per release, source and place, with feeds. **S2** (NEW-19).
- **J6: trace a headline figure.**
  - The home tile "5848 of 5848 subjects with a resolved amount value" has no link.
  - `/coverage-metrics/` has 5 links in `main`, and none of them belongs to a tile.
  - **Missing:** explain-this-number and a link to the rows. **S2** (NEW-14; C2 NEW-7, NEW-17).

**Verdict:** the journalist concludes, wrongly, that SIG has nothing on Texas vendors, sharing or procurement, or
worse, quotes the network as current. **The most useful change:** entity and edge pages carrying date, currency and
source, reachable from a search that knows names.

### 3.3 Organizer (coalition, neighbourhood, contributor)

**"Which sources disagree about my county? What can my group do this month? How does my state compare?"**

- **O1: "Which sources disagree about my county?"**
  - No page is scoped to a county. `camera_county` has 25,802 subjects, so a county facet is feasible for part of the
    record (inference).
  - The dossier shows "Subjects with conflicting coordinate evidence ⚠ Unresolved" (16 jurisdictions; 5,290 subjects;
    `jurisdictions.csv`). The gap link opens a jurisdiction task page that lists neither the subjects nor the sources.
  - The coverage page says "2 open of 2 recorded contradictions … kept visible". No page shows them. Through the API,
    both are about one agency subject that has no dossier.
  - **S2** (NEW-17, NEW-7).
- **O2: `/research-queue/`.**
  - The page is 690 KB and shows 500 of 243,761 tasks. There is no pagination, no per-card link, and one filter option
    ("Unscoped").
  - Decoding the cards: the **first 130 are exactly the 130 network agencies** (`sharing_snapshot_stale`: "a fresh
    configured-access observation … is captured"), 369 are `coverage_hole` with "Geographic scope —", and 1 is
    `conflicting_retention`.
  - These are good, concrete organizing tasks ("is agency X still sharing with Vigilant LEARN?") rendered unreadable.
  - **S2** (NEW-16; C2 NEW-21).
- **O3: compare TX, CA and NY.**
  - The only way is to open 3 dossiers. All three have the same template: 1 count, 3–4 source keys, and 11 "unknown"
    fields.
  - `/dossier/us/` is **not** a national roll-up. It is a 629-site bucket fed by 3 sources.
  - `/dossier/id/` mixes Idaho (`camreg_achd_id`) with Indonesia (`camreg_indonesia_id`).
  - **S2** (NEW-18; I1/C3 collisions).
- **O4: bring data into a spreadsheet.** No page offers CSV. The export bundle is not linked (C2 NEW-8). **S1** (C2).

**Verdict:** the organizer sees that SIG knows where the gaps are but cannot turn them into work. **The most useful
change:** the research queue as human questions, per place, each with a records-request template and an explanation
of how to help.

---

## 4. Open-ended questions: can the site answer them?

`data?`: **yes** = SIG's release or API holds data that at least partly answers the question; **partial** = some data
exists but it needs resolution or routing; **no** = acquisition is needed.

| question | best path found | answer on site | data? | blocking gaps | findings |
|---|---|---|---|---|---|
| Who supplies ALPRs to agencies in Texas and who can search them? | `/search/` → `/network/` | none | partial: 130 agency → Vigilant LEARN configured-access claims (2020, historical); I3: 474,184 Flock share-list edges in the ingested mirror, unresolved; Atlas `vendor` not turned into claims (I1) | names, vendor entities, jurisdiction on agency entities, edge dates | NEW-1, NEW-2, NEW-3, NEW-4 |
| What did my city approve and when does it renew? | `/dossier/tx/` → `/watch/` | "unknown"; empty watch | partial: Austin procurement-portal captures, `legistar` agendas, `award_date` 1,051, `renewal_options` 195, `response_deadline` 987 | routing of agenda and procurement claims to places (I1 NEW-4); a watch fed beyond contract termination fields | NEW-13, NEW-15 |
| Which sources disagree about my county? | dossier gap → task; `/coverage-metrics/` | a count only | yes: 5,290 conflicted subjects; 2 recorded contradictions | a contradiction view; a county facet; per-subject gap pages | NEW-7, NEW-17 |
| What changed in the last month? | none | none | partial: assertion timestamps, `last_content_change`; `/v1/changes` exists but returns empty | a changes surface and feed; release history | NEW-19 |
| Where exactly are the cameras near this address? | `/map/` at z15 | unlabelled dots with no basemap | yes: site labels, coordinates, source, upstream URL per row | basemap, place search, feature pages, jurisdiction assignment for OSM points | NEW-6, NEW-8, NEW-9 (C2 NEW-9) |
| Which agencies share data with ICE-linked systems? | `/search/` "ICE" | 2 false positives | no (not evidenced in the release) | honest zero-result copy, exact matching | NEW-10 |
| What is SIG's evidence for this vendor–agency link? | `/network/` edge | "1 evidence", not a link | yes: claim, source, date, envelope (API) | edge detail and evidence pages; source pages for non-registry sources | NEW-2, NEW-12, NEW-13 |

**Inference, labelled:** the attribution of the "Austin Police Department" entity to Texas rests on the name only. The
API entity has `location: null` and no jurisdiction. The Austin Regional Intelligence Center is a Texas fusion center
by name. That SIG cannot place its own agency entities in a jurisdiction is itself the routing gap I1 NEW-4 describes.

---

## 5. Surface notes for the operator-named areas (what K12b adds to C2)

- **`/map/`** (U-003.1):
  - The canvas is 950×384 on a 1440×900 screen.
  - The attribution overlay takes 100 px of it and intercepts pointer input (NEW-8).
  - The national view shows about 18 dots for "227335 located surveillance records" (shot `f57864e9…`).
  - Only 4 controls exist: zoom in, zoom out, reset north, and attribution. There is no filter, search, legend toggle or
    geocoder (`map1_controls.json`).
  - Popups: see NEW-6.
  - Keyboard: the canvas takes focus and the arrow and +/- keys work, but no feature can be focused or opened. The next
    Tab stops after the canvas are the 5,290 dead gap links (NEW-9, NEW-7).
  - The intro copy says the map "renders as static content with no client JavaScript" (NEW-20).
  - The H3 density table lists cell ids with no place names (inference: unusable without a map).
- **`/network/`** (U-003.2): see §3.2. The graph in the release is a single star, 130 agencies → 1 organization, from 1
  source (`network.json`: 131 nodes, 130 edges, 0 access paths). A "global graph" built today would be small. The big
  graphs (Flock share lists; buyer → seller; funder → recipient) need entity resolution first (data dependency, §7).
- **`/search/`** (U-003.3):
  - The index holds 733 items: 55 dossiers, 500 capped sites (Iowa first) and 178 sources.
  - Matching is case-insensitive substring. "IA" gives 472 results, including Indiana. "ICE" gives false hits.
  - Site hits go to the `/map/` root and source hits to the `/data-freshness/` root.
  - A label seen in a map popup ("Cavalier & Portage", Winnipeg) is not findable.
  - The API's `/v1/search` already returns typed, named entities ("Austin" gives Austin Police Department, the Austin
    Regional Intelligence Center and Austin traffic cameras). A first pass could expose that before building anything
    new (NEW-10).
- **`/dossier/` index and detail** (U-003.4, .5, .6):
  - False hierarchy cues, a US bucket that is not a roll-up, and the ID collision (NEW-18).
  - Detail pages have 9–11 links in `main`: 2–4 gap links, print, JSON, 3 footer links, dispute and cite. **None** goes
    to a source, an entity, the map filtered to the place, or the watch.
  - Every one of 8 sampled dossiers has the same 16 section headings, whatever the content.
- **`/watch/`** (U-003.7):
  - The copy is honest and the decision-date framing is good.
  - It has 0 contracts and 0 jurisdictions. The per-jurisdiction feeds are 404 (not linked). There is no feed
    autodiscovery.
  - `citations.txt` is a placeholder.
  - "Works" in the sense that nothing breaks. It has never had content (NEW-15).
- **`/evidence/`** (U-003.8):
  - The page is empty by construction: it renders `claim_views` (0), not `artifacts` (255).
  - Every artifact's `title` equals its UUID, and every `permalink` is an internal `sig:connector:…` string.
  - So "stuck in the research queue" is not the main cause (inference); the page simply shows the wrong list (NEW-13).
- **`/data-freshness/`** (U-003.9, .10):
  - The table lists only camera registries (NEW-12).
  - Sorts are no-ops (NEW-11).
  - Timestamps are raw ISO with microseconds.
  - No row count, publisher, jurisdiction, technology, upstream link, download or source page.
  - `/data-freshness/camreg_austin_tx/` is 404.
- **`/research-queue/`** (U-003.11): see §3.3 (NEW-16).
- **Elsewhere:**
  - Home and coverage tiles lead nowhere (NEW-14).
  - "Contradictions kept visible" is not true for a visitor (NEW-17).
  - URLs a user would guess all return a bare nginx 404 (C2 NEW-26).

---

## 6. Friction points mapped to the operator's asks

Status column: **C** = confirmed as asked; **R** = confirmed and refined (the fix must be larger or different than the
ask implies); **N** = a new ask surfaced here.

| # | friction (evidence) | ask | status | refinement for the K-row | sev | finding |
|---|---|---|---|---|---|---|
| F-01 | Blank canvas, no place context (Austin z15, Atlanta z13 shots) | U-003.1 | C | — | S1 | C2 NEW-9 |
| F-02 | Popups: UUID label, "unresolved" jurisdiction inside TX and GA, no type, operator, source, date or link; citation not feature-specific | U-003.1 | R | A basemap alone will not make the map answer "what is this, who runs it". It also needs feature pages, jurisdiction assignment for OSM points, and a feature-pinned citation | S2 | NEW-6 |
| F-03 | 5,290 "⚠ Unresolved" links → 404 | U-003.1, .11 | R | Gap links must resolve to real pages (per-subject contradiction view), or not be links | S2 | NEW-7 |
| F-04 | Attribution covers 26% of the desktop canvas and eats clicks; canvas 950×384 | U-003.1 | R | The map layout, not only the basemap: a larger viewport, collapsible attribution | S2 | NEW-8 |
| F-05 | No filters, layer toggles, legend actions or keyboard access to features | U-003.1 | R | Filters (technology, source, operator, licence, date) and a keyboard feature list | S2 | NEW-9; C2 NEW-23 |
| F-06 | Network nodes are UUIDs although the API and export hold names | U-003.2 | R | A label-derivation bug in the exporter or web layer, not missing data: cheap to fix first | S1 | NEW-1 |
| F-07 | Edges lack date, currency and source (2020 historical data shown as current) | U-003.2 | R | "Laying bare all we know" must include **when** and **how weak** | S1 | NEW-2 |
| F-08 | Explorer is a single star; hairball rendering; no expansion, search or filter; 160 Tab stops; 76 mobile screens | U-003.2 | R | A global graph needs resolved data first (Flock share lists, procurement, funding). Build entity and list views before a canvas | S2 | NEW-5 |
| F-09 | 185 agencies' partner degrees and 372 unclassified sharing rows hidden | U-003.2 | R | The "who can access what" view has data today | S2 | NEW-4 |
| F-10 | Substring search: false hits on "ICE", 0 for names SIG holds; results link to page roots; 733-item capped index | U-003.3 | R | Typed entities (the API's `/v1/search` already does this), exact tokens, place aliases (Texas → TX) | S2 | NEW-10 |
| F-11 | CA above CA-AB and CO above CO-MET read as parent and child; the "US" dossier is not a roll-up; ID merges Idaho and Indonesia | U-003.4 | R | The country grouping must also rename or retire the `us` bucket and fix collisions before grouping | S2 | NEW-18 |
| F-12 | Dossier sources are 3–4 keys with no link; non-registry sources never reach a dossier | U-003.5 | R | The contribution explorer must include non-registry claims (sharing, procurement, agenda), which today are not routed to places | S1 | NEW-3; C2 NEW-15 |
| F-13 | Dossier contradicts the network (TX sharing "Not researched") | U-003.5, .6 | N | Absence kind must be computed against **all** claims about entities in the place | S1 | NEW-3 |
| F-14 | Nothing to embed beyond sites; network edges have no jurisdiction | U-003.6 | R | Embedded map and network depend on F-02 and F-06 and on jurisdiction routing | S2 | NEW-3, NEW-6 |
| F-15 | Watch empty; feeds 404; no autodiscovery; forward-dated fields exist but are not routed | U-003.7 | R | "Works" technically; it needs data feeds (procurement deadlines, renewal options, bills, agendas) | S2 | NEW-15 |
| F-16 | Evidence page lists claim views (0), not the 255 artifacts; artifact routes 404; titles are UUIDs | U-003.8 | R | Not mainly the research queue: list artifacts now, then add claim views | S2 | NEW-13 |
| F-17 | Freshness sorts are no-ops; headers not sortable; only camera registries; no upstream links, counts or downloads | U-003.9 | R | Include the about 40 non-registry sources; the upstream URL already exists per export row | S2 | NEW-11, NEW-12 |
| F-18 | No source page (`/data-freshness/<source>/` 404); `eff_data_driven` untraceable | U-003.10 | C | Source pages must cover every source that feeds any claim, not only the freshness list | S2 | NEW-12 |
| F-19 | Queue: UUIDs; 130 network agencies first; 369 coverage holes with no place; 500 of 243,761; no card links | U-003.11 | R | The tasks are meaningful; render them as questions (entity name + predicate + last evidence date) | S2 | NEW-16 |
| F-20 | Zero outbound links site-wide; 124 tiles lead nowhere | U-003.G | R | Every figure and source needs an onward path | S2 | NEW-14, NEW-21 |
| F-21 | No "what changed" surface; API changes feed empty | new (N-1) | N | A changes page and feed per release, source and place | S2 | NEW-19 |
| F-22 | Contradictions claimed "kept visible" but shown nowhere | new (N-2) | N | A contradiction browser (SIG-UI-009) | S2 | NEW-17 |
| F-23 | The site does not use API capabilities that exist (`/v1/entity`, `/v1/search`, `/v1/contradiction`, `/v1/changes`) | new (N-3) | N | K0 and K13 should weigh "surface what the API already serves" as the fastest path | S2 | NEW-1, NEW-10 |
| F-24 | Map intro claims no client JS above a JS map | U-003.1 | C | copy | S3 | NEW-20 |

---

## 7. Feature ideas (agent-generated; full list in `data/k12b_ideas.csv`)

All 32 ideas are grounded in the data table in §2. The **data dependency** column says whether SIG has the data today:

- **have** = it is in the release or the API now;
- **route** = it is in the spine but needs routing or resolution;
- **acquire** = Stream I work is needed.

The **JS dependency** column uses the K0 vocabulary: none (static), island, or app shell. Risks name the Part VIII,
licence and misleading-impression hazards.

**Ranking method (inference):** value to the three co-primary personas; how many U-003 asks it serves; data readiness;
and effort. Ties go to lower JS dependency and lower risk. It is ranked here for K13 to accept, defer or reject; it is
not decided.

| rank | id | idea | persona | value | effort | data | JS | asks |
|---|---|---|---|---|---|---|---|---|
| 1 | I-01 | **Entity pages** (agency, organization/vendor, product, source, site): name, every claim with its envelope (support, currency, rationale), sources, contradictions, history, related entities | all | H | M | have (labels and envelopes in the API); route (jurisdiction on entities) | none | .2 .5 .10 G |
| 2 | I-05 | **Date and currency on every relationship and figure** ("observed 2020-01-28 · historical · EFF Data Driven") | journalist | H | S | have | none | .2 G |
| 3 | I-25 | **Typed knowledge-graph search**: names, places and aliases (Texas → TX), exact tokens, facets, results linking to entity, place and source pages; start by exposing the API's `/v1/search` | all | H | M | have | island | .3 |
| 4 | I-03 | **"Find my place" resolver**: city, county or address → dossier + map view + typed gaps. Self-hosted gazetteer; any geocoding runs client-side, never sent to a third party | advocate, organizer | H | M | have (jurisdictions, `camera_county` 25,802) + a gazetteer | island | .1 .3 .4 |
| 5 | I-02 | **Explain this number**: numerator, denominator, rule, sources and rows behind every figure, with a link to download those rows | journalist | H | S | have (`coverage.json`, `number_trace`) | none | .5 .9 G |
| 6 | I-09 | **Source pages for all about 218 live sources**, including the about 40 non-registry sources: publisher, upstream link, licence, rows contributed per dossier, run history, downloads by rights | journalist, organizer | H | M | have | none | .9 .10 |
| 7 | I-10 | **Dossier "who contributed what, when" ledger**: source × predicate × first/last seen | advocate | H | S | have (site sources); route (non-registry) | none | .5 |
| 8 | I-16 | **Map feature pages and cite-a-point**: popup → `/site/<id>/` with type, operator, source, dates, precision and a feature-pinned citation | advocate, resident | H | M | have | island (popup) + none (page) | .1 |
| 9 | I-13 | **Research tasks as human questions + records-request templates**: "Is Austin PD still sharing with Vigilant LEARN? Last evidence: 2020 EFF records" | organizer | H | M | have (tasks, labels); templates (SIG-TASK-015/016) | none | .11 |
| 10 | I-04 | **"Who can access what"**: agency → configured partners and networks, partner degree, restrictions, each dated; reverse view "who can search agency X's data" | journalist, advocate | H | L | have (632 rows); route (474k Flock share-list edges, I3) | none + island | .2 G |
| 11 | I-06 | **One-page council brief**: place name, known / unknown (typed), next decision date, 5 documents to bring, permalink and QR | advocate | H | M | route (thin today) | none | .6 G |
| 12 | I-12 | **"What we don't know" gap view per place**: typed absence per predicate and technology class, linked to tasks | organizer, advocate | H | S | have | none | .11 G |
| 13 | I-08 | **What changed**: per-release, per-source and per-place diff with RSS | journalist | H | M | route (assertion times; `/v1/changes` empty) | none | G, N-1 |
| 14 | I-07 | **Decision calendar + subscriptions** (iCal/RSS; email later), keyed on decision date, fed by procurement deadlines, renewal options, sunset dates, bills and agendas | advocate, organizer | H | L | route + acquire | none | .7 |
| 15 | I-26 | **Evidence locker**: all 255 artifacts with type, source, capture date, hash, directness, supported claims, original URL (rights permitting), capture diff | attorney, journalist | M | S | have | none | .8 |
| 16 | I-11 | **Contradiction browser**: both sides, sources, dates, per place and entity | journalist, organizer | M | S | have (2 + 5,290 conflicted subjects) | none | G, N-2 |
| 17 | I-23 | **Download this view**: CSV/JSON of exactly the rows shown, with a licence header | journalist, organizer | M | S | have | none | .9 G |
| 18 | I-17 | **Map filters and legend** (technology, source, operator, licence, date), real layer toggles, clustering | resident, advocate | H | M | partial (sparse technology fields) | island | .1 |
| 19 | I-14 | **Guided "start here" journeys** per persona on the home page, replacing the 124 tiles | first-time visitor | M | S | n/a | none | G |
| 20 | I-24 | **Peer link-outs with agreement markers** (Atlas, DeFlock/OSM, Eyes on Flock, MuckRock) per place and agency, with mirror lineage (P15) | journalist | M | M | have (ingested) | none | G, X |

Ideas 21–32 are in the CSV: cross-jurisdiction comparison with CSV; typed graph atlases (procurement buyer → seller,
funding funder → recipient); keyboard-first graph navigation; embeddable static figure cards; citation formats
(including legal); data-quality badges; "ask this graph" canonical-question pages; entity and place timelines; a
Flock-portal policy view (aggregates only); coverage-honesty place cards; funding trail; and a "near me" list that
never sends location to a server.

**Risks that recur across ideas (for K13):**

- **Historical data read as current.** Every relationship view needs I-05 first.
- **Absence read as "no".** Typed absence everywhere (SIG-TIME-012).
- **Coverage read as density** (SIG-UI-018), especially in comparisons and embeds.
- **Share-alike and operator-accepted compartments in downloads and embeds** (J4). So are egress costs of embeds and
  bulk (SIG-EXPORT-008).
- **Part VIII.**
  - Portal audit data must stay aggregate: no officer names, no search reasons.
  - Entity pages exist for institutions only.
  - A handle-like source key must never become a page title (C2 NEW-2).
- **P16-like privacy for users.** Place search and "near me" must not send an address or location to a third party.
  Email alerts need an operator decision on holding subscriber addresses.

---

## 8. Findings filed (`../findings/incoming/K12b.csv`)

| sev | ids |
|---|---|
| S1 (4) | NEW-1 names hidden though held · NEW-2 edges undated / historical shown as current · NEW-3 TX dossier "not researched" vs network evidence · NEW-12 sources behind sharing and evidence untraceable (the about 40 non-registry sources are absent from every page) |
| S2 (16) | NEW-4 hidden degree and restriction claims · NEW-5 explorer cannot explore · NEW-6 popups dead ends / citation not feature-pinned · NEW-7 5,290 gap links 404 · NEW-8 desktop attribution overlay · NEW-9 features not keyboard-operable · NEW-10 substring search false hits / API divergence · NEW-11 freshness sorts no-op · NEW-13 evidence page lists wrong collection · NEW-14 tiles without paths · NEW-15 watch never routed forward-dated data · NEW-16 queue tasks unnamed · NEW-17 contradictions "kept visible" but invisible · NEW-18 dossier index false hierarchy / US bucket · NEW-19 no "what changed" surface; API changes empty · NEW-21 zero outbound links |
| S3 (1) | NEW-20 map intro copy contradicts the JS map |

Routing: K1 (map) NEW-6/7/8/9/20 · K2 (graph and entities) NEW-1/2/4/5 · K3 (search) NEW-10 · K4 (index) NEW-18 · K5
(dossier sources) NEW-3 · K7 (watch) NEW-15 · K8 (evidence) NEW-13 · K9/K10 (sources) NEW-11/12 · K11 (queue) NEW-16 ·
K13 (IA/synthesis) NEW-14/17/19/21.

No S0 was observed in this run. The handle-like source keys seen on `/dossier/ny/` are the known C2 NEW-2 (S0), which
has already been reported. They are not re-filed and not reproduced.

## 9. Evidence manifest (`docs/build/logs/next-phase/K12b/`, gitignored)

- `loads.tsv`: 42 page loads with timestamps.
- `api_log.tsv`: 8 API GETs.
- `drift_end_headers.txt`.
- `interactions.jsonl` (sha256 `fe70d080…113c`): every step of every scenario.
- `shots/`: 29 PNGs. Key shots:
  - network hairball `a56ed6bd…3994`;
  - network on mobile `652f59f4…275c`;
  - Austin z15 `b37517e1…edf5`;
  - Austin popup `18bda723…4095`;
  - Atlanta popup `d652ac8e…1884`;
  - national map `f57864e9…6ec8`;
  - dossier index `a957efa5…f187`;
  - research queue `476cf2e0…94b3`.
- `text/`: 34 page texts.
- `json/`: map controls, TX links, search results, visit rows, and 8 API bodies.
- `tools/`.
- `SHA256SUMS`.

Offline inputs reused (unchanged release, sha256 prefix):

| file | sha256 prefix |
|---|---|
| `C3/bucket/sig_graph/sharing_edges.csv` | `1cb8b7e0…` |
| `C3/bucket/web/network.json` | `556101e6…` |
| `C3/bucket/web/evidence.json` | `3df209d5…` |
| `C3/bucket/sig_graph/freshness.csv` | `f3ee6c8e…` |
| `C3/bucket/sig_graph/jurisdictions.csv` | `183426d6…` |
| `C2/text/R01_home_desktop.txt` | `6763793c…` |
| `C2/text/R19_network_desktop.txt` | `460a2a14…` |
| `C2/html/R11_map_desktop.html` | `7b593b27…` |
| `C2/task_listing.txt` | `d2cc2e24…` |
| C2 openapi capture | `0ad37629…` |

## 10. Limits

- Headless automation cannot judge human perception: legibility, how confusing something is, trust. Those judgements
  are inference.
- Hover-only states were not captured. Mobile was sampled only on `/network/`; C2 covered the mobile map and dossiers.
- The API serves the live spine, not the release (ROUTES X10). API facts show that data *exists*; they are not what the
  release published. Counts from the API were not compared with the release.
- The relevance of `response_deadline`, `renewal_options` and bill records to surveillance decisions in any given place
  was **not verified** (inference in NEW-15, I-07).
- The claim that Austin Police Department is in Texas rests on the entity's name; the entity carries no location (§4).
- K12a's prior-art patterns were not read beyond headings. K13 reconciles the ideas above with K12a §2–§5 and with C6's
  draft requirements.
