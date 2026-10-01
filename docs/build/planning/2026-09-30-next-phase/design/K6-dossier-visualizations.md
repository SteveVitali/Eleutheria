# K6 — Dossier embedded visualizations (operator ask U-003.6)

- **Row:** K6 (Stream K, design) · **Written:** 2026-09-30, work window 22:39Z–23:01Z (`date -u`)
- **Worktree HEAD at write time:** `3d1384c0` (branch `claude/next-phase-planning`). `git diff --stat b051732c HEAD -- web
  exports` is empty, so every `code` citation below is also a chain-tip citation.
- **Operator ask, verbatim (U-003.6):** *"individual jurisdiction dossier pages should probably also include by default some
  sort of network and/or map-based visualization(s) for interactive exploration and perhaps also search"* (from U-003,
  2026-09-30T21:28:52Z). The general ask (U-003.G) applies too: *"richer, more interactive, searchable, traversable,
  inspectable … so that as much about what the data says, where we got it from, etc. is as laid bare as possible"*.
- **Binding inputs (composed, not redone):** `design/K0-interactive-architecture.md` (dossiers are **T1 content**: ≤ 20 KiB
  initial JS, never render-blocking; T2 code only after an explicit "open the interactive view" action; I-2 every visual has a
  static rendition + table in the same place; §4.4 dossier row; §4.10 print; §8 K6 guidance); `design/K1-map.md` (the T2 map,
  `sig.map-tiles/2`, symbols §3.5, URL state §4.8, the static renderer MAP-05 "shared with K6"); `design/K2-graph-and-entities.md`
  (labels, entity pages, overviews O0–O7, honesty rules H-1…H-13, GX-06b ego SVG, per-state `/graphs/<id>/<state>/`);
  `design/K3-search.md` (§6.7 scoped search, SRCH-06); `design/K4-dossier-index.md` (keys, placement, levels, URLs, boundary
  pack, locator hook in JUR-04); `design/K5-dossier-sources.md` (`sig.dossier-sources/1`, "Where this comes from", per-figure
  provenance); `design/K14-visual-and-onboarding.md` (tokens, Record template, data-viz conventions §4.7, print §4.11,
  UXK14-8/9); `design/D3-product-direction.md` (journeys A1–A4, J1–J5, O1–O4). META_PLAN §3 (P1–P16) and U-008 (≤ $300/month).
- **Design centre:** spec §39 SIG-UI-002 (the local advocate), SIG-UI-010 (the twelve sections, in order), SIG-UI-011/012,
  SIG-UI-013 (print/PDF, as-of and permalink on every page), SIG-UI-014/014a/014b/015, SIG-UI-016–025 (map and network rules)
  (`docs/2_canonical_design_spec.md:5728-5850`, read).
- **Code read:** `web/src/pages/dossier/{[slug].astro,[slug]/print.astro,index.astro}`, `web/src/components/{DossierSection,
  IncompletenessBanner,ViewSwitch}.astro`, `web/src/lib/{dossier,workspace-state}.ts`, `web/src/islands/{Map,Network,Search}Island.tsx`
  (grep), `web/src/styles/epistemic.css:504-548`, `exports/src/exports/spine_export.py:1265-1560`,
  `web/node_modules/maplibre-gl` 6.9.0 typings (installed, untracked).
- **Evidence classes (P1):** `code` (file:line at `3d1384c0`); `recorded-execution` (measurements run for this row, §2, §19);
  `release` (C3's sha-verified capture of `sig-2026-09-27-ce480ab1` under `docs/build/logs/next-phase/C3/`); citations of other
  rows by id. Every cost, future size and user-behaviour statement is **`inference`** and says so.
- **Status (P5):** nothing here is engineered. This is a design, draft requirements and a ticket outline for K13/S2.
- **P3 / P14 / P16:** production was not touched. Two public-domain files were downloaded from `www2.census.gov` (Census
  Cartographic Boundary 2025 500k, state and county; 22:45:53Z–22:45:54Z; curl's default User-Agent; no operator identity)
  into the session scratchpad, the same files K4 used. No secret appears here.
- **Writes:** this file and `findings/incoming/K6.csv` only.

---

## 0. The design on one page

**What exists today.** A dossier is a zero-JS page of twelve headings, one count per heading and a print link. It has no
map, no network and no search, and it links nowhere on the map, the network or `/search/` (`web/src/pages/dossier/[slug].astro:64-68`
offers only "Print / PDF" and "JSON"). "Where the hardware is" is one row, *"Publishable subjects in this jurisdiction: N"*
(`exports/src/exports/spine_export.py:1488-1494`). No published network node carries a place, so no relationship can be
placed on any dossier today (§1).

**What we build: every dossier, at every level, carries by default** (all T1, zero JS to read, print and cite):

| where (SIG-UI-010 order kept) | what | interaction |
|---|---|---|
| **At a glance** | the stat row and next decision (K14/K7), a **locator** (the place inside its parent), and **Figure 1, the jurisdiction map**: boundary, child outlines, published records binned (or points for small places), hollow = single source, the "no published point" box and the coverage statement, all at build time as inline SVG. Under it the **Explore bar**: *Explore on the map · See connections · Search within {place}* | zero-JS drill-down (click a county → its dossier); **"Explore this map here"** loads the K1 map app into the same box on click (desktop); on phones the same control opens `/map/` framed on the place |
| **What is deployed** | **Figure 2, "Who runs and supplies it"**: operators and buyers placed here ↔ their recorded vendors (K2 O1/O4 slice) | nodes are links; CSS-only toggles; "Open in the explorer" with `jurisdiction=` |
| **Cost and expiry** | **Figure 3, "Who funds it"** (K2 O3 slice), only when ≥ 1 funding edge exists | as above |
| **Who else can see the data** | **Figure 4, "Who can search this data"** (K2 O2 slice), the three access kinds separate and toggleable without JS (SIG-UI-024) | as above |
| **Where the hardware is** | the places table (the map's long description), the sites-list link (K1 MAP-05), declared-vs-located counts (K4) | links; `<sig-table>` sort |
| **Policy** | **Figure 5, "Which rules apply"** (K2 O5 slice), only when ≥ 1 instrument applies | as above |
| **Timeline · What we don't know · How we know this** | K2/K7/K5 content; K5's "Where this comes from" and over-time chart; the gap grid | links; per-figure "from N sources" anchors (K5 §5) |

Figure ids are fixed (`fig-map`, `fig-supply`, `fig-funding`, `fig-access`, `fig-policy`). Figure numbers follow page
order, and a conditional figure that is absent is skipped in the numbering.

**Load strategy against K0's budgets (decided, §5.3).** The dossier stays **T1**: initial JS ≈ 5–10 KiB (`<sig-activate>`,
the `<sig-typeahead>` shell; inference), inside the 20 KiB budget. The map app (≈ 345 KiB, K1 §6.1) loads **only after the
reader presses "Explore this map here"**, into the reserved box that already shows the static map, and is then budgeted as
T2 inside that box. **Rejected:** loading it automatically on scroll or visibility (it would make every dossier a T2 page;
K0 §4.3 forbids T2 code before an explicit action), and an in-page graph explorer (at ≤ 40 nodes the static figure already
shows everything; expansion belongs to `/explore/`).

**Print (§8).** Page 1 is K14's council brief with the **locator**. Figure 1 opens page 2. Network figures print beside
their sections. Every figure prints as its static SVG with a caption: what it shows, "not a census", the release and as-of,
source count, licence lines and the figure's permalink. No canvas and no control ever prints. Figures never split across
pages. The running footer (UXK14-9) carries the as-of and permalink on every page.

**Sizes, measured on the real release (§2).** The map inlined as SVG: California 40.2 KB raw / **11.4 KB gzip** / 8.9 KB
brotli (210 areas, 58 county outlines). Median US state 35.7 KB raw / 9.4 KB gzip. The largest state map is Georgia, 89.5 KB
raw / **25.6 KB gzip** / 19.4 KB brotli. The US country map is 71.0 KB raw / 19.9 KB gzip. County maps measured 10.3–34.9 KB raw / 2.2–8.0 KB gzip
(Los Angeles, Oklahoma and Harris counties).
A 40-node network figure is ≈ 14–15 KB raw / ≈ 2–5 KB gzip. Drawing points instead of areas would be 193 KB raw for Harris
County's 5,032 records, which is why areas are the default. Everything fits K0's 150 KiB document budget. The per-dossier
build input is ≈ 3–150 KB, and ≈ 50–80 MB per release in total (inference). The incremental cost is under $1 a month apart
from the map sessions K1 already costs.

**Tickets (§14): VIZ-00…VIZ-05, 7 tickets, ≈ 5 runs.** VIZ-00 contracts (S) → VIZ-01a map and locator geometry (M) →
VIZ-02 components and composition (M) → VIZ-03 Explore bar and scoped search (S) → VIZ-01b network slices (S) → VIZ-04
in-place map (M) → VIZ-05 acceptance (S, live). The map path depends on K4 JUR-02b/03 and K1 MAP-05. The network path
depends on K2 GX-01/05a/08a and on I8 placing agencies. Search depends on K3 SRCH-04/06. The look depends on K14
UXK14-1/3/8/9.

**New findings (§18, `findings/incoming/K6.csv`):** NEW-1 (S2): all three islands ignore the `jurisdiction`, `source`,
`location` and `technology` facets they parse, so a place-scoped link silently shows the national view. NEW-2 (S3):
"hollow" and "dashed" each carry two meanings across K1, K2 and K14, which would collide on one dossier page. NEW-3 (S3):
four rows each name another row as owner of the static SVG generators. NEW-4 (S3): K0's strict CSP and K14's styled
standalone SVGs conflict, and nobody owns the rule.

---

## 1. Ground truth: what a dossier shows today

| # | fact | evidence |
|---|---|---|
| G1 | The dossier is static and zero-JS. It renders the twelve SIG-UI-010 sections in order, validated at build (`validateDossier`), the incompleteness banner and "what we don't know" twice. | `web/src/pages/dossier/[slug].astro:6-13, 30-35, 53-82`; `web/src/lib/dossier.ts:40-53` (`code`) |
| G2 | The only outbound actions are "Print / PDF version" and "JSON (API form)". There is no link to `/map/`, `/network/` or `/search/` for the place, and dossiers do not use the `ViewSwitch` component the islands use. | `[slug].astro:64-68`; `web/src/components/ViewSwitch.astro` (`code`) |
| G3 | "Where the hardware is" has exactly one row: the count "Publishable subjects in this jurisdiction". "What is deployed" has one observation count. "How we know this" has a comma-joined list of source ids. | `exports/src/exports/spine_export.py:1477-1501` (`code`); `C3/bucket/web/dossiers.json`: section 7 = `{"rows":[{"label":"Publishable subjects in this jurisdiction","value":556}]}` (`release`) |
| G4 | Dossier JSON today: 55 dossiers, median 1,555 B, max 3,762 B (`unresolved`). | Python over `C3/bucket/web/dossiers.json` (129,470 B), between 22:47:43Z and 22:48:59Z (`recorded-execution`) |
| G5 | No relationship can be placed on a dossier: `network.json` nodes carry only `{id, label, type}` (131 nodes, `label` = `id`). Edges carry no date and no source. | `C3/bucket/web/network.json` (`release`); K2 §1.1 |
| G6 | The print route chunks sections **three per sheet-block** (`SECTIONS_PER_PAGE = 3`). The footer is a block at the end of each chunk, not a running footer. `@page` has no margin boxes. C2 found that page 1 has no as-of or permalink and that there are orphan pages (C2 NEW-6, TH-10). | `web/src/pages/dossier/[slug]/print.astro:29-44, 91-97`; `web/src/styles/epistemic.css:525-548` (`code`); `review/JOURNEYS.md:400-406` |
| G7 | `sig.workspace-state/1` already defines a repeated `jurisdiction` facet, plus `source`, `technology` and `location`. It parses and serializes them, but **no island applies them**. The map applies `collection`, `focus` and `release`; the network applies `focus` and `release`; search applies `q`, `kind` and `focus`. A `?v=1&jurisdiction=…` link renders the unfiltered view and raises no "issue" note (**NEW-1**). | `web/src/lib/workspace-state.ts:17-25, 60-66, 86-89, 188-192, 217-221`; `web/src/islands/MapIsland.tsx:191-200, 458, 485, 612-614`; `NetworkIsland.tsx:79-85`; `SearchIsland.tsx:71-117`; `grep -rn 'state\.(jurisdiction|source|location|technology)' web/src` → 0 consumers (`code`) |
| G8 | MapLibre 6.9.0 (the pinned renderer) exposes the `cooperativeGestures` option, which K6's embedded mode needs so that a page scroll is not captured by the map. | `web/node_modules/maplibre-gl/package.json:4`; `dist/maplibre-gl.d.ts:9218, 11949, 12121` (`code`, installed package) |

**What that means.** U-003.6 is not blocked by the zero-JS rule. K0 §1.4 already classes it "none if rendered as static
SVG; optional activation". It is blocked by three things:
- dossiers have no geometry or relationships to draw (K4 and K2 bring them);
- no component draws a figure;
- the URL facets that would connect a dossier to the explore surfaces are ignored (G7).

---

## 2. Measurements (`recorded-execution`, 22:45:53Z–22:54:24Z; scripts and hashes in §19)

**Method.** The inputs were the release's 227,335 geolocated entities, de-duplicated by `entity_id`, from C3's hashed
parquet capture, plus the Census CB 2025 500k state and county polygons. The scripts did the following:
- ran an even-odd point-in-polygon test (numpy);
- projected to Web Mercator and fitted a **720 px wide** figure (max 520 px tall), the width of K14's 8-column main column;
- simplified outlines with Douglas–Peucker at 0.5 px (child outlines at 0.6 px) and dropped sub-pixel islands;
- binned records into H3 cells (h3 4.5.0), drawing each cell as a disc of radius ∝ √n, hollow when one source;
- wrote SVG text and compressed it with `gzip -9` and `brotli -q 11`.

**Validation.** The point-in-polygon counts reproduce K4's placement exactly: California **28,334**, Oklahoma **1,705**,
Harris County **5,032**.

### 2.1 Selected dossiers

"K1 band" is K1's interactive table (z0–4 → res 3; z5–6 → 4; z7–8 → 5; z9 → 6; points from z10). The "static rule" is the
finest H3 resolution whose average cell diameter (2 × H3's average edge length) is ≥ 12 px at the figure's zoom (§5.1). Sizes are raw / gzip / brotli in
bytes.

| dossier (framing zoom) | records | K1 band: areas · size | **static rule: areas · size** | points instead | outline / child outlines raw |
|---|---:|---|---|---|---|
| California, state (z4.9) | 28,334 | res 3: 45 areas · 32,210 / 9,935 / 7,835 | **res 4: 210 areas (66 single-source) · 40,243 / 11,361 / 8,920** | — | 4,278 / 25,326 (58 counties) |
| Texas, state (z4.8) | 21,611 | res 3: 65 · 57,860 / 17,980 / 13,577 | **res 4: 323 (189) · 70,474 / 20,094 / 15,162** | — | 10,404 / 43,868 (254 counties) |
| Oklahoma, state (z5.9) | 1,705 | res 4: 51 · 27,759 / 8,209 / 6,369 | **res 5: 110 (110, all single-source) · 30,639 / 8,715 / 6,709** | — | 3,999 / 20,858 |
| Rhode Island, state (z8.2) | 353 | res 5: 16 · 15,835 / 3,870 / 2,955 | **res 7: 103 (103) · 20,079 / 4,527 / 3,467** | 353 points: 20,428 / 5,088 / 3,932 (no counties) | 7,087 / 7,551 |
| Harris County, TX (z8.8) | 5,032 | res 5: 24 · 8,272 / 3,363 / 2,387 | **res 7: 568 (382) · 34,886 / 7,969 / 5,817** | **193,043 / 31,158 / 24,638** | 6,715 / — |
| Los Angeles County, CA (z7.2) | 4,153 | res 5: 42 · 4,830 / 1,788 / 1,377 | **res 6: 155 (75) · 10,329 / 2,745 / 2,083** | 155,871 / 21,642 / 17,638 | 2,403 / — |
| Oklahoma County, OK (z9.7) | 566 | res 6: 41 · 2,512 / 815 / 652 | **res 8: 242 (242) · 12,327 / 2,247 / 1,776** | 21,347 / 3,431 / 2,913 | 132 / — |
| District of Columbia (z10.4) | 1,665 | (points from z10) 62,559 / 9,474 / 7,833 | **res 8 under the 1,000-point cap: 204 · 11,059 / 2,445 / 1,908** | 62,559 / 9,474 / 7,833 | — |
| United States, lower 48, state borders (z3.1) | 199,640 | res 3: 612 (262) · **71,027 / 19,932 / 14,808** | (res 3 is also the static rule) | — | 40,845 (48 states + DC) |

### 2.2 All 56 US state-equivalents (static rule, with county outlines)

| | min | median | max |
|---|---:|---:|---:|
| raw bytes | 2,462 | 35,670 | **89,540 (GA: 479 areas, 159 counties)** |
| gzip | 863 | 9,369 | **25,608 (GA)** |
| brotli | 697 | 7,305 | 19,418 (GA) |
| without county outlines, gzip | 522 | 3,741 | 9,469 (DC, points) |
| areas drawn | 0 | 186 | 1,665 (DC as points; 204 areas under the cap) |

- Next largest after GA: VA 72.9 KB raw / 22.4 KB gzip; KY 71.2 / 22.3; LA 72.4 / 22.1; TX 70.4 / 20.0.
- **16 of 56** state-equivalents would draw **every** area hollow (single source). Oklahoma is one of them. This is K4
  R-K4-2 made visible: the figure itself must say "one source".
- GU, AS and MP have **0** published located records. They get the typed empty map (§5.1), never a blank frame.
- **County outlines are most of a state map's bytes** (TX 43.9 KB of 70.5 KB raw). They also carry the drill-down links,
  so they are kept, with a size cap (§5.1).

### 2.3 Locator thumbnail (160 px)

- California within the lower-48 states: 7,702 B raw / 2,782 gzip / 2,293 brotli inline.
- The shared parent layer (48 states + DC) is 7,277 B raw / 2,568 gzip. The child path alone is 250 B raw / 145 gzip.
- So the **dossier index** (K4 JUR-04, ≈ 150 rows) should inline one parent `<symbol>` plus one child path per row:
  ≈ 2.6 KB + ≈ 150 × 0.15–0.6 KB gzip (inference from the one child measured). Embedding 150 full locators would add
  ≈ 400 KB.

### 2.4 Network figure (synthetic; real labels compress less)

| nodes / edges | raw | gzip | brotli |
|---|---:|---:|---:|
| 12 / 10 | 4,113 | 1,017 | 809 |
| 40 / 60 | 13,901 | 2,179 | 1,750 |
| 40 / 80 | 15,072 | 2,235 | 1,815 |

These were built as a two-column layout with `<a href>` per node, 38-character labels and edges grouped by class. The
synthetic labels repeat words, so real sizes are estimated at **≈ 3–5 KB gzip** for a 40-node figure (inference; K2 §15
gives ± 30 % for real labels).

---

## 3. Principles (binding on every VIZ ticket)

- **V-1 The figure is the record.** Every dossier visual is build-time SVG in the page, complete with JavaScript off, and
  identical in print (K0 I-1, I-2, §4.10). JavaScript may replace what is inside the box only after a click, and never
  empties it.
- **V-2 Same numbers everywhere.**
  - The counts a figure encodes equal the dossier's K5 `figures[]` values.
  - For the same framing they equal the interactive map's summed cells (K1 R-4).
  - A parity test enforces both (SIG-UI-DV10).
- **V-3 Coverage travels with the points** (SIG-UI-017/018):
  - hollow means one source;
  - every map states where SIG has looked;
  - every map states how many records have no published point (SIG-UI-020);
  - no map ever reads as a census.
- **V-4 Precision is never improved by drawing** (spec §19.4; Part VIII):
  - points only for tier-0 records and only where the framing zoom is ≥ 10 (K1's point zoom);
  - tier-1/2 records are never drawn finer than published;
  - tier-3 records are only counted in the "no published point" box.
- **V-5 Aggregate, never rank.**
  - A network figure stays within its node cap by **grouping** (by place, kind or state), never by picking the "most
    connected".
  - Captions are descriptive: counts, not importance (K2 G-4, SIG-UI-021/023, D-K2-2).
- **V-6 Words on every edge** (K2 H-1…H-13):
  - relation in words, date or "undated", currency, and sources;
  - historical edges are never phrased in the present tense;
  - degree-only facts are sentences, not edges.
- **V-7 No empty frames.** A figure with nothing evidenced is not drawn. The section shows K14's typed empty state (what is
  missing, why, what is nearby, what would close it).
- **V-8 One legend lexicon per page.** A symbol means one thing on the map and on the network of the same page (NEW-2).
- **V-9 Produced works, licence-true.**
  - The drawn map is a produced work. It carries every drawn compartment's licence line in its caption, and in its
    standalone file.
  - No per-area numbers are published as data. The accessible table is at place level, where dossier figures already sit.
  - This keeps ADR-106 §4 (no licence-mixed public database; K1 §3.2).
- **V-10 State lives in the explore surfaces, not in the dossier URL.**
  - The dossier never writes to `history` (K0 I-9).
  - "Open full map", "Open in the explorer" and "Cite this view" hand `sig.workspace-state/2` to `/map/`, `/explore/` or the
    snapshot URL.

---

## 4. Page composition

### 4.1 Section by section (SIG-UI-010 order unchanged; `validateDossier` keeps passing)

| # | section | visual (K6) | data (owner) | rendered only when |
|---:|---|---|---|---|
| 1 | At a glance | stat row (≤ 6 `<Figure>`s, K14/J3) · next decision (K7) · **locator** · **Fig. 1 map** · **Explore bar** + scoped search | K4 row fields, K5 `figures[]`, `sig.dossier-visuals/1` (§9) | always (typed empty map for 0 located records) |
| 2 | What is deployed | **Fig. 2 "Who runs and supplies it"** (operators and buyers ↔ vendors) + relationship table | K2 O1/O4 relations, K4 placement | ≥ 1 evidenced operator or supply edge |
| 3 | Cost and expiry | **Fig. 3 "Who funds it"** + termination block (SIG-UI-014a) | K2 O3; K7 dates | ≥ 1 funding edge |
| 4 | Who else can see the data | **Fig. 4 "Who can search this data"** (three access kinds separate) + degree-only sentences | K2 O2, GX-07 closures | ≥ 1 access edge or degree fact |
| 5–6 | Configuration and retention · Usage | none (text and values; K2 claims) | K2 | — |
| 7 | Where the hardware is | **Places table** (Fig. 1's long description) · link to the sites list · declared-vs-located · "no published point" counts | K4, K1 MAP-05 | always |
| 8 | Policy | **Fig. 5 "Which rules apply"** + legal regime block | K2 O5 | ≥ 1 instrument placed |
| 9 | Accountability events | none (list) | K2 events | — |
| 10 | Timeline | K14's dated list (world vs belief time); undated items listed apart | K2 timeline, K7 watch, K5 first seen | ≥ 1 dated item, else typed empty |
| 11 | What we don't know | **gap grid**: evidence types × status using K14 absence chips (HTML table, not SVG) | K4 "evidence types" field, gaps | always (SIG-UI-011) |
| 12 | How we know this | K5 "Where this comes from" + K5 over-time chart (UXK14-8) | `sig.dossier-sources/1` | always |

**Why the map sits in "At a glance" and not in "Where the hardware is":**
- It is the one visual every persona uses first: the resident asks "is there anything near me", the advocate orients a
  council member, and the journalist checks spread and single-source areas.
- The operator asked for it "by default".
- Section 7, seventh of twelve, is several screens down.

Section 7 keeps the facts: the places table, the site list and the placement disagreements. It points back to Figure 1
through an anchor, so nothing is drawn twice.

### 4.2 Wireframes (T1 Record template, K14 §4.5)

**Desktop (≥ 64 rem): main 8 columns + aside 4 columns.**

```
┌ header band: breadcrumbs  United States › Texas › Harris County ──────────────────────────────────────────┐
│ H1 Harris County, Texas   [locator 160px]   one-sentence summary · release stamp · Cite · Print · Download │
└───────────────────────────────────────────────────────────────────────────────────────────────────────────┘
 main (8 col)                                                         aside (4 col, sticky)
 1 At a glance                                                        On this page
   [stat row: records 5,032 · sources 3 · single-source 67% · …]     Where this comes from (K5 summary)
   Next decision: … (or typed absence)                                Other public resources (D3 Q4)
   ┌ Figure 1 ─ reserved box 16:10 ──────────────────────────────┐
   │  static SVG map (boundary, 568 areas, hollow = 1 source)    │
   │  [Explore this map here]  (desktop: loads the map in place) │
   └─────────────────────────────────────────────────────────────┘
   caption: what it shows · not a census · N with no published point · release/as-of · licences · [Cite figure]
   Explore: [Explore on the map ↗] [See connections ↗] [Search within Harris County: ______ (Search)]
 2 What is deployed        Figure 2 (two-column network, ≤ 40 nodes) + relationship table (first 50, "all N →")
 3 Cost and expiry         Figure 3 (if any) · termination block
 4 Who else can see…       [x] configured [x] declared [x] observed  [ ] include historical   ← CSS-only toggles
                           Figure 4 + table + "Shared with N agencies — partners not named" sentences
 5–6 …
 7 Where the hardware is   Places table (county/places, records, located %, sources, 1-source share) · Sites list → (MAP-05)
 8 Policy                  Figure 5 (if any) · legal regime
 9–12 …                    timeline list · gap grid · Where this comes from (K5)
```

**Mobile (< 40 rem): one column.**
- The locator sits beside the H1.
- Figure 1 is full width, 358 px at 390. The same SVG scales by `viewBox`, strokes keep their width
  (`vector-effect: non-scaling-stroke`) and the smallest disc stays ≥ 2 px (§5.1).
- "Explore this map" is a **link to `/map/?v=2&jurisdiction=…`**. There is no in-place map, because touch panning inside a
  scrolling page traps the reader.
- Network figures switch to their narrow variant (§6.4), and the table is always visible below.
- The Explore bar wraps into three full-width buttons, each ≥ 44 × 44 px.

### 4.3 Per level

| level (K4) | map framing and children | networks | notes |
|---|---|---|---|
| country (`/dossier/usa/`) | the country with admin-1 outlines; the US uses K1's overview variant (Albers + AK/HI/PR insets) | **no node-link figure.** A thumbnail of K2's `/graphs/<id>/` overview SVG (external `<img>`, lazy) + the "relationships by state" table + link | K2 G-2: no national hairball |
| admin-1 (`/dossier/usa/tx/`) | state, county outlines as drill-down links | Figs 2–5 at ≤ 40 nodes (anchors grouped by county when over the cap); link to K2's `/graphs/<id>/<state>/` | the largest pages (GA, TX, CA) |
| county | county, place outlines when K4's place layer is in the pack (else none) | Figs 2–5 | most counties frame at z7–9 → areas |
| place (≥ 10 records, D-K4-3) | place; points when z ≥ 10 and ≤ 1,000 tier-0 records, else areas | Figs 2–5 | small towns → points |
| non-US admin-1 / country | Natural Earth outlines; no children in Round 11 (K4 §4.3) | as data allows | conservative publication profile (D-K4-7) |
| `/dossier/unplaced/` | **no map** (not a place, K4-P4) | none | a QA map of "outside all boundaries" points is later |

---

## 5. The embedded map

### 5.1 The static figure (Figure 1)

**Geometry (exporter, deterministic; one snapshot).**
- **Projection:** Web Mercator, fitted to the jurisdiction's bounds with 8 px padding, so the static figure and the
  activated map frame the same view. The one exception is the US country view (K1's Albers + insets); there the map
  visibly re-frames on activation.
- **Layers, bottom to top:**
  1. child outlines (counties or places), light ink, with the coverage hatch on children that no source covers once K1's
     `coverage_by_jurisdiction.json` rule exists (D-K1-4). Until then the legend reads "Where SIG has looked: rule pending
     — hollow areas rest on one source";
  2. the jurisdiction outline;
  3. records.
- **Binning rule (SIG-UI-DV02):**
  - **Points** only when the framing zoom is ≥ 10 **and** the place has ≤ 1,000 tier-0 records.
  - Otherwise **H3 areas** at the finest resolution whose average cell diameter is ≥ 12 px at the figure's zoom (§2.1).
  - Tier-1/2 records never bin finer than their published precision. Tier-3 records are never drawn.
  - The disc radius is ∝ √n, from 2 to 12 viewBox units. A disc is **hollow when one source**, filled when ≥ 2; the
    ≥ 3-sources half-tone follows K1 §3.5.
- **Why not K1's band table?** At a state's framing zoom it draws California as 45 discs about 66 px across (inference from
  H3 res 3's average edge at z4.9), and hides the difference between the Bay Area and Los Angeles. The static rule draws 210 (§2.1). D-K6-4 asks K1 to tune its band to
  the same ≥ 12 px rule (K1 marks the table as "a parameter"), so the two agree on activation (K1 R-4).
- **Records not drawn here are counted, never dropped** (SIG-UI-020; K4-P3):
  - "N records placed by their declared place have no published point";
  - "N records declared here are located elsewhere (see *Florida*)";
  - "N records withheld as conflicting coordinates".

  All three sit in a hatched legend box, with links.

**Markup (Astro component, tokens; K14 §4.3, §4.7).**
- `<figure id="fig-map">` → `<svg viewBox="0 0 720 H" width="720" height="H" role="img" aria-labelledby>` → `<title>` +
  generated `<desc>` ("Map of Texas. 21,611 published records from N sources in 323 areas about 25 km across; 189 areas
  rest on one source. The table 'Places in Texas' below lists the same records by county.").
- **DOM economy:** areas and points are drawn as **one `<path>` per symbol class** (filled, hollow, half-tone) using arc
  segments, not one element per disc. A map is then ≤ 60 SVG elements whatever its size, which protects TBT and DOM size.
  Child outlines are one path.
- **Drill-down:** each child with records is an `<a href="/dossier/…/">` shape in a pointer-only layer (`tabindex="-1"`,
  `aria-hidden="true"`). The places table directly below is the keyboard and screen-reader path to the same links, and is
  the figure's long description (`aria-describedby`).
- **Theming:** colours come from site CSS classes and variables (`--data-seq-*`, `--ink-*`), never from `style=""` or an
  inline `<style>` (K0 §4.8 CSP). Dark mode follows the OS setting (K14 §4.10). Print forces the light tokens.
- **Size cap (build-time):** ≤ 30 KiB gzip per inline map (the measured maximum is 25.6 KB for GA). Over the cap, the
  builder drops child outlines to 1.0 px tolerance, then coarsens one resolution, and records which rule it applied in
  the figure metadata.

**Caption (agent-drafted template; K14 CP rules):**
> **Figure 1. Where SIG's published records are in {place}.** Each disc is an area about {d} km across; its size shows how
> many records SIG holds there; a hollow disc rests on a single source. Not a census: counts show what SIG's {n} sources
> publish, not every device. {k} records have no published point (listed in *Where the hardware is*). Release {label},
> data as of {date}. Map data: {licence lines of every drawn compartment}. Boundaries: {US Census Bureau 2025 | Natural
> Earth}. [Cite this figure] [Download figure (SVG)]*

\*The download is country and admin-1 only (D-K6-5).

### 5.2 Links from the figure

| link | target | exists when |
|---|---|---|
| Explore on the map | `/map/?v=2&jurisdiction=<jkey>` (K1 frames on the registry bbox) | K1 MAP-03a applies `jurisdiction` (NEW-1). Until then the link goes to `/map/` with a visible note "the map does not yet frame places; see the sites list" |
| All {N} sites, 100 per page | `/dossier/<path>/sites/` (K1 MAP-05) | MAP-05 |
| a child on the map | the child dossier | JUR-03 page thresholds (D-K4-3) |
| Cite this figure | `/s/<pub>/dossier/<path>/#fig-map` (G3/J3 TX-13a) | G3 snapshot; otherwise J3 §8.1's fallback text |
| from {n} sources | `…/sources/#fig-map` (K5 §5 breakdown) | DSRC-02 |

### 5.3 Load strategy against K0's budgets (the decision)

| option | initial JS on the dossier | what the reader gets by default | print, archive | verdict |
|---|---|---|---|---|
| (A) static only, links out | 0 | static map, networks and drill-down; interaction on `/map/`, `/explore/`, `/search/` | complete | **the no-JS and mobile path** of (B) |
| **(B) static + click-to-activate in place** | ≈ 5–10 KiB (`<sig-activate>` ≈ 1.5 KiB + the typeahead shell; inference) | (A), plus a live map in the same box after one click on desktop | complete: the static SVG stays in the DOM and prints | **adopt** |
| (C) static + auto-load on visibility (`client:visible`/`idle`) | ≈ 345 KiB as soon as Figure 1 scrolls into view | a live map without a click | the canvas never prints, so the SVG must still be kept | **reject.** Every dossier becomes T2-weight. It contradicts K0 §4.3 ("T2 code only after an explicit action") and K0's reason for keeping the record T1 (the advocate on a phone at a podium, SIG-UI-041). Tile requests start for readers who only wanted the text |
| (D) make dossiers T2 surfaces | ≤ 360 KiB | an app | the record stops being HTML-first | **reject** (K0 I-1, D-K0-1) |
| (E) in-page graph explorer (sigma) | 0 before a click, ≈ 120 KiB after | pan and zoom of ≤ 40 nodes | — | **reject for Round 11.** The static figure already shows every node and edge within the cap. Expansion, paths and filters beyond it are `/explore/`'s job (K2 §5.3). This saves a second in-page app |

**Justification for the embedded explore component (the map only).**
1. It costs nothing until asked for: 0 KiB of T2 code initially, and the dossier keeps T1's Lighthouse ≥ 0.95 and CLS ≤ 0.02.
2. It answers U-003.6 literally: "interactive exploration" on the dossier page itself, beside the narrative and tables
   that explain it. Navigating away loses that context.
3. It is not a second app. It is the K1 app in an `embedded` mode (§5.4).
4. It keeps the static figure as the first paint and the print rendition (K0 I-2, NEW-3's CLS fix).

### 5.4 In-place activation ("Explore this map here"; desktop only)

- **Markup without JS:** `<a class="sig-activate" href="/map/?v=2&jurisdiction=<jkey>">Explore on the interactive map</a>`.
  `<sig-activate>` upgrades it to a `<button aria-controls="fig-map" aria-expanded="false">` only when
  `matchMedia('(min-width: 64rem) and (pointer: fine)')` matches. On phones and tablets the link simply navigates.
- **On click:**
  1. `import()` the K1 map module (the same hashed chunks `/map/` uses, so it is cached across pages);
  2. mount into the **same fixed-aspect box**, with the SVG left underneath until the first `idle` render, then
     `aria-hidden` (never removed, so it still prints);
  3. frame the registry bbox, draw the jurisdiction outline from `context.pmtiles` (K1), and use `cooperativeGestures:
     true` so the page scrolls unless the reader uses Ctrl/⌘ + scroll or two fingers (G8);
  4. move focus to the map region's heading.
- **Embedded mode, a subset of K1 §4:**
  - basemap and overlays, legend, and a **filters row** (technology, status, source);
  - the "Sites in view" list and table **below** the canvas, not in a side panel (it is the keyboard and screen-reader
    path, K1 §4.6);
  - the selection panel, with K1's graceful links;
  - "Open full map" (hands over all state) and "Cite this view" (the `/s/<pub>/map/?v=2&…` snapshot);
  - "Close interactive map", which restores the static figure and returns focus to the button;
  - no place search, and no "my location" (`Permissions-Policy` keeps geolocation to `/map/` only, K0 §4.8).
- **No URL writes on the dossier** (V-10). Back and Forward behave as for any static page.
- **Budget after activation:** the box is measured as **T2 map**:
  - ≤ 360 KiB gzip JS (K1 targets ≈ 345);
  - first-view tiles and glyphs ≤ 1.5 MiB (K1 measured ≈ 0.6–0.9 MiB);
  - ≤ 200 ms from selection to panel at 4× CPU throttle;
  - axe clean in the activated state.
- **CSP:** unchanged from K0's T1/T2 policy, which already lists the tile origin in `connect-src` and `worker-src 'self'
  blob:`.
- **Failure:** if WebGL, the tiles or the import fail, the box keeps the static figure and shows "The interactive map could
  not load; the figure and the places table show the same records" (`role=status`).

### 5.5 Source-filtered views (K5 hand-off)

Each source row in K5's table gets a "Show on the map" control:
- **with JS, on desktop:** it activates Figure 1 in place with `source=<id>`. K1 applies an exact filter from z10 and an
  approximate one below it, and says so (K1 §4.3 honesty rule);
- **otherwise:** it links to the K3 results page `…/search?type=record&jurisdiction=<jkey>&source=<id>&format=html` (the
  no-JS list of that source's records here, K3 SRCH-04), plus `/map/?v=2&jurisdiction=…&source=…`.

---

## 6. The embedded networks

### 6.1 Families and placement

| figure | family (K2 overview) | anchors (placed in the dossier) | counterparties | section |
|---|---|---|---|---|
| Fig. 2 | operators (O4) + supply (O1) | agencies and operators whose K4 placement chain contains the dossier key; operator nodes carry "operates N cameras" as an attribute, never N camera nodes | vendors (the GX-04 relevance rule; H-13); OSM `manufacturer` tags as one group, "mapped by volunteers" | What is deployed |
| Fig. 3 | funding (O3) | recipients placed here | funders | Cost and expiry |
| Fig. 4 | access (O2) | agencies placed here | partners, grouped by state and kind beyond the cap; "Shared with N agencies — partners not named" as sentences (H-4, SIG-INGEST-043c) | Who else can see the data |
| Fig. 5 | governance (O5) | instruments, bills and ordinances whose jurisdiction chain contains the key | the technologies and bodies they govern | Policy |

**"Active in the jurisdiction" (definition, SIG-UI-DV03).**
- An entity is an **anchor** when its `place_jkey` (`sig.entity-label/1`, K2 §6.1) lies in the dossier's key chain.
- It is a **counterparty** when it has an evidenced edge to an anchor.
- Placement comes from K4 (points, declared places, `lookup@1` for agencies). A name match alone never places an entity
  (K2 J-1: "Texas membership needs a recorded placement, not a name guess").
- "OpenStreetMap contributors" is a source, not an operator (H-12, K2 NEW-2). It is excluded from Fig. 2 until that
  modelling error is fixed.

### 6.2 Size limits (aggregation only; V-5)

- **≤ 40 drawn nodes and ≤ 120 drawn edges per figure.** At most 24 rows of 20 px, so the figure is ≤ 520 px tall
  (720 × ≤ 520 viewBox).
- **Anchors ≤ 24.** Beyond that, anchors are grouped by child jurisdiction ("Harris County — 14 agencies"). Each group node
  links to that child dossier's figure (`…/harris-county-48201/#fig-supply`).
- **Counterparties ≤ 16.** Beyond that, they are grouped by kind × state ("38 other suppliers in 9 states"). Each group
  links to K2's per-state page `/graphs/<id>/<state>/` or the full table.
- **Order within a column is alphabetical.** No count or centrality order is used (D-K2-2).
- Labels are cut at 38 characters on a word boundary with "…" (K2 L-4). The full label is in `aria-label` and in the table.
- The **country** level draws no node-link figure (§4.3).

### 6.3 Layout and encoding

- **Two columns:**
  - anchors ("In {place}") on the left, counterparties on the right;
  - edges are cubic curves between them;
  - the layout is computed at render time from sorted lists, so it is deterministic with no physics;
  - a two-column bipartite reads better than a radial ego when the centre is a *place* rather than an entity, and it
    prints legibly at half a page.
- **Shapes** follow K14 §4.7 (agency ●, vendor ■, policy or contract ▭, source ⬟). Entity kind is never shown by colour.
- **Edge encoding (resolved with NEW-2; confirmed at D-K6-7):**
  - *line pattern = access kind* (configured solid · declared dashed · observed double), as SIG-UI-024 and K14 require;
  - *currency = ink weight and a word*: current edges use the normal ink; historical and undated edges use the muted ink,
    and their table rows and `aria-label`s say "historical (recorded 2020-01-28)" or "undated";
  - no second dash pattern for currency, and **"hollow" is not used in network figures**, because on this page hollow
    already means "one source" (Figure 1).
- **Two layouts per figure:** wide (720) and **narrow** (360 viewBox, labels ≤ 20 characters, anchors above
  counterparties). A container query shows one (`@container (max-width: 40rem)`). The narrow variant costs ≈ +2–4 KB gzip
  (inference from §2.4).
- **DOM:** one `<path>` per edge class (kind × currency ≤ 9 classes). Nodes are `<a>` elements with `aria-label` "{label},
  {kind}, {n} relationships in this figure". Edges are `aria-hidden`.

### 6.4 Zero-JS interaction

- **Access-kind toggles** (Fig. 4): checkboxes in a `<fieldset>` with the legend "Show access kinds", plus "Include
  historical and undated". CSS `figure:has(#k-declared:not(:checked)) .e.dec { display: none }` needs no script. Browsers
  without `:has()` show every edge, which is the safe default. Print shows every edge and hides the controls.
- **Nodes are links** to entity pages (K2 GX-06). Group nodes link to child dossiers or `/graphs/…`.
- **Skip link** "Skip figure — go to the relationship table", because up to 40 tab stops is a lot.

### 6.5 The table twin (the figure's long description)

- One row per anchor–counterparty relationship, with K2 H-2's columns: counterparty (linked), relation in words, direction,
  access kind, date and date kind (or "undated"), currency (text), support, sources (linked), and an evidence link.
- The table shows 50 rows, then "all N →" to K2's `/graphs/<id>/<state>/` (states) or the anchor's entity page
  (county/place). Every row reaches its J3 provenance panel in ≤ 2 actions (SIG-UI-D34).
- `<sig-table>` sorting is optional (K0 §4.6; loads after the first header click).

### 6.6 Expansion to `/explore/`

"Open in the explorer" links to `/explore/?v=2&overview=<supply|access|funding|governance>&jurisdiction=<jkey>` (K2 §5.3
filters; K0 §4.5). K2's `path`, `currency` and `years` fields carry through when set. Each node's own "Explore from here"
lives on its entity page (`focus=<key>&hops=1`), not in the figure, to keep the figure a static image of links.

### 6.7 Empty and thin states (V-7; K14 §6.4 copy pattern, agent-drafted)

> **No connections recorded for {place} yet.** SIG's release places no agency or operator in {place} with a recorded
> supplier. *Why:* agencies are placed only from recorded locations or registry names, and procurement is linked to places
> only where a notice names both sides. *Nearby:* {parent}'s figure (link) · the national supply overview (link). *What
> would change this:* {K11 task link} · I8's procurement sources. *Kind:* not researched.

**Today, every dossier shows this state** (G5). The figures appear as K2 GX-05a and I8's placement land.

---

## 7. In-dossier search and the source-contribution explorer

### 7.1 Scoped search (K3 §6.7; SRCH-06 owns the form and route)

- **No-JS:** `<form method="get" action="/v1/releases/<pub>/search">` with hidden `format=html` and `jurisdiction=<jkey>`
  (descendants via `jurisdiction_chain`), a radio "In {place} | Everywhere", and the release pinned to the dossier's. The
  field reads "Search within {place}". Results are K3's typed cards grouped by licence (SRCH-04).
- **Enhancement:** the header's `<sig-typeahead>` gains a `scope="<jkey>"` attribute that filters suggestions to places
  and organisations whose chain contains the key. The code is the same (no new JS). MiniSearch and the shard load on focus,
  which is post-action (K3 §6.2). This needs a `jc` (jurisdiction chain) field on place and organisation entries in K3's
  catalog shards (≈ +15 B per entry, inference). That is an interface request to SRCH-05.
- **Degraded:** when the API is down, the form's target errors. The dossier's own tables, the sites list and the map still
  answer the place questions (K3 §5.5).

### 7.2 K5 integration

- K5's "Where this comes from" stays in section 12. Every K6 figure is a K5 **material figure**, and DSRC-01 emits entries
  for them:
  - `figures[]` gains `fig-map` (records drawn, by source), `fig-supply`, `fig-access`, `fig-funding` and `fig-policy`
    (edge counts, by source);
  - each has a "from N sources" link in its caption (K5 §5).
- The source table's "Show on the map" is §5.5. The over-time chart is K5's static SVG, drawn by UXK14-8.
- **K6 creates no chart island.** K5 DSRC-05's optional brushing stays DSRC-05's, within K0's post-action ≤ 40 KiB
  (NEW-3).
- The map legend's per-compartment licence lines come from the same registry rendering as K5's download attribution
  (PKG-08), so the two never disagree.

---

## 8. Print: the council-meeting persona (SIG-UI-002, SIG-UI-013; K14 §4.11, UXK14-9)

**One component, two print paths.** The T0 `/print/` route (country and admin-1, K4 §5.3) and `@media print` on T1 dossier
pages (county and place) render the **same** figure components. Neither prints a canvas or a control.

| printed page | content |
|---|---|
| 1 — council brief (K14) | place name + **locator** (1.6 in) · what is recorded and what is unknown at a glance · next decision date or its typed absence · the documents to bring · QR to the pinned permalink |
| 2 | **Figure 1** (≤ ½ page, `break-before: page`), caption, the "no published point" box, then section 2 with Figure 2 |
| following | sections in SIG-UI-010 order; each network figure ≤ ½ page, kept with its section heading (`break-inside: avoid`; `break-after: avoid` on the heading); tables print in full up to 200 rows, then "N more at {URL}" (K2 §4.2) |
| every page | the running footer: place · as-of · release · permalink · licence · page n of m (UXK14-9; fixes C2 NEW-6) |

**Figure rules in print:**
- captions print in full, with the figure's own permalink (`…#fig-map`), so a single photocopied page is still citable;
- the light tokens are forced;
- hollow and filled discs, and solid, dashed and double lines, stay distinguishable in greyscale (a PyMuPDF raster check);
- pointer-only drill-down links print as plain shapes;
- toggles print in their "all shown" state;
- no figure is split across pages;
- the figure scales from its 720-unit viewBox to the 6.5 in text width.

**Why the map is not on page 1.** K14's page 1 is the advocate's two-minute read: what is known, what is unknown and when
it is decided. A map would take half of it. The locator gives orientation at a sixth of the space, and the full map leads
page 2.

---

## 9. Data contracts and sizes

### 9.1 `sig.dossier-visuals/1` — build input (restricted), one per dossier

Produced by the exporter in the export's single snapshot. It is consumed by Astro and **not published**: the per-area
geometry across compartments would be a licence-mixed derived dataset (V-9; K1 §3.2; ADR-106 §4).

```jsonc
{
  "schema": "sig.dossier-visuals/1",
  "release": {"label": "…", "publication_id": "p-…", "as_of_world": "…"},
  "jurisdiction": {"jkey": "iso3166-2:US-TX", "slug_path": "usa/tx", "level": "state_province", "chain": ["iso3166-1:US"]},
  "map": {
    "viewbox": [720, 520], "zoom": 4.8, "projection": "webmercator", "boundary_vintage": "census.cb.2025.500k",
    "outline_d": "M…Z", "children": [{"jkey": "us.census.geoid.county:48201", "href": "/dossier/usa/tx/harris-county-48201/", "d": "M…Z", "coverage": "covered|not_covered|rule_pending"}],
    "mode": "areas|points", "h3_res": 4, "rule": "static-12px@1", "cap_actions": [],
    "symbols": {"filled": "M…", "hollow": "M…", "halftone": "M…"},              // one path per class (§5.1)
    "not_drawn": {"declared_no_point": 0, "located_elsewhere": [{"jkey": "…", "records": 0}], "conflicting": 0, "tier3": 0},
    "compartments_drawn": ["osm_physical", "public_record", "…"],             // → caption licence lines
    "desc": {"records": 21611, "sources": 4, "areas": 323, "single_source_areas": 189, "area_km": 25}
  },
  "locator": {"parent_symbol": "us48", "child_d": "M…Z", "viewbox": [160, 101]},
  "networks": [{
    "figure_id": "fig-supply", "family": "supply+operators",
    "anchors": [{"key": "…", "label": "…", "kind": "agency", "href": "/entity/…", "attr": "operates 1,705 cameras"}],
    "counterparties": [{"key": "…", "label": "…", "kind": "vendor", "href": "/entity/…"}],
    "groups": [{"label": "38 other suppliers in 9 states", "href": "/graphs/supply/usa-tx/", "members": 38}],
    "edges": [{"a": 0, "c": 3, "relation": "bought from", "access_kind": null, "currency": "historical", "date": "2020-01-28", "date_kind": "recorded"}],
    "table_rows": 412, "table_href": "/graphs/supply/usa-tx/"
  }],
  "timeline_items": 0
}
```

### 9.2 Public artifacts

- **The dossier JSON twin** gains `figures[]` metadata: id, caption, `desc` counts, links, rule applied. That is ≈ 1–3 KB.
  It carries no geometry.
- **K5's `figures[]`** carries the per-source breakdowns (§7.2).
- **Standalone SVG files** are for country and admin-1 dossiers only (≈ 340 dossiers × ≤ 5 figures, ≈ 1.7k objects). Each
  has its own attribution text inside and its own `prefers-color-scheme` block. Serving them needs the CSP rule in NEW-4.
- **The index locator sprite** (K4 JUR-04) is one inline `<symbol>` per parent plus one path per row.

### 9.3 Sizes

| item | largest (measured) | small (measured) | whole release (inference) |
|---|---|---|---|
| inline map SVG | GA 89.5 KB raw / 25.6 KB gz / 19.4 KB br; US 71.0 / 19.9 / 14.8; CA 40.2 / 11.4 / 8.9; TX 70.5 / 20.1 / 15.2 | RI 20.1 / 4.5; LA County 10.3 / 2.7; OK County 12.3 / 2.2; DC 11.1 / 2.4 | ≈ 5.6k dossiers (K4) × median ≈ 10–20 KB raw ≈ 60–110 MB raw of HTML, ≈ 15–30 MB compressed |
| locator (inline) | 7.7 KB raw / 2.8 KB gz | same order | — |
| network figures (up to 4, wide + narrow) | ≈ 4 × (15 + 8) KB raw ≈ 90 KB raw, ≈ 4 × 5 KB ≈ 20 KB gz (inference, §2.4) | 0 today (G5) | — |
| `sig.dossier-visuals/1` (restricted) | TX ≈ 70 KB of map geometry + ≈ 70 KB of network rows after I8 ≈ **≈ 150 KB**; US ≈ 75 KB (networks by reference) | ≈ 3–15 KB | ≈ **50–80 MB** per release |
| a whole dossier page, worst case (GA/TX): HTML + map + locator + 4 figures + tables | ≈ 60–80 KB brotli transferred (inference) | ≈ 10–20 KB | within T1's ≤ 150 KiB (K0 §4.3) |

**Cost (inference from K0 §5.3 unit prices):**
- storage: +≈ 50–80 MB restricted input and +≈ 15–30 MB compressed HTML per retained release, ≈ $0.002/month;
- per-release writes: +≈ 1.7k SVG objects, ≈ $0.01;
- in-place map activations are K1 map sessions (≈ $3 per 10k on R2, K1 §2.4).

**Total incremental: under $1/month plus K1's map-session cost**, well inside U-008.

**Build time (inference):** geometry for ≈ 5.6k dossiers adds ≈ 1–3 minutes. The measurement script placed and rendered all
56 states with county outlines in 24 s, in pure numpy. Astro rendering of the SVG strings is measured in VIZ-02 against K4's
+10–30 min estimate for the pages themselves.

---

## 10. Performance targets (SIG-UI-DV07; measured in CI on UXK0-2's real-sized fixture and on the release before promotion, G3 V11)

| metric | dossier (T1, before any action) | after "Explore this map here" (box = T2 map) |
|---|---|---|
| initial JS (gzip) | **≤ 20 KiB** (plan ≈ 5–10) | — |
| JS after the action | typeahead + MiniSearch ≤ 40 KiB; `<sig-table>` ≤ 15 KiB | ≤ 360 KiB (K1 ≈ 345) |
| document, transferred | **≤ 150 KiB** (worst measured page ≈ 60–80 KB br, inference) | unchanged |
| inline map SVG | ≤ 30 KiB gzip each; ≤ 60 SVG elements | — |
| data per interaction | typeahead shard ≤ 50 KiB | first-view tiles + glyphs ≤ 1.5 MiB; ≤ 500 KiB per pan or zoom |
| LCP (simulated mobile) | ≤ 1.5 s (the H1 or stat row, not the map) | — |
| CLS | ≤ 0.02 (SVG `width`/`height` reserve the box; activation happens inside a fixed-aspect box) | ≤ 0.05 |
| TBT | ≤ 50 ms | ≤ 350 ms |
| Lighthouse mobile | ≥ 0.95 perf · 1.0 a11y | the /map/ run covers the app; a Playwright journey measures the embedded mode |
| interaction latency (4× CPU) | CSS toggles: no script | activation → first render ≤ 2.5 s on a desktop profile; selection ≤ 200 ms |

The LHCI matrix gains the US, GA, TX and CA dossiers, one county, one small place (points) and one `/print/` page.

---

## 11. Accessibility contract (WCAG 2.2 AA, JS off and on; K0 §4.9)

- **Text alternatives (1.1.1).**
  - Map: `role="img"` with a data-generated `<title>` and `<desc>`, and a long description in the places table (same
    counts; parity-tested).
  - Networks: every node is a named link; the relationship table is the long description.
  - Locator: `alt` = "Location of {place} within {parent}".
- **Keyboard (2.1.1).**
  - The map's drill-down layer is pointer-only by design (`tabindex="-1"`, `aria-hidden`); the table offers every link.
  - Network nodes are tabbable in reading order, after a skip link.
  - The activated map follows K1 §4.7: arrows pan, Enter moves to the "Sites in view" list, Escape closes the selection,
    and "Close interactive map" returns focus to the button.
- **2.5.7 dragging:** the activated map keeps K1's pan pad; `cooperativeGestures` never blocks the pad or the keyboard.
- **1.4.1 colour:** hollow vs filled, line pattern, shape and text carry every meaning; colour is the second channel (V-8).
- **1.4.3 / 1.4.11 contrast:** discs ≥ 3:1 against the page in both themes; outlines are decorative (≥ 3:1 where they carry
  links).
- **1.4.10 reflow:** the SVG is `width:100%; height:auto`. The narrow network variant applies at ≤ 40 rem. Tables scroll
  inside labelled containers. There is no page-level horizontal scroll at 320 px.
- **1.4.13 hover content:** none on static figures (no tooltips). The activated map follows K1.
- **2.4.11 focus not obscured:** the embedded map has no overlays over controls; attribution is a strip under the canvas
  (K1 D7).
- **2.3.3 motion:** there is nothing to animate in static figures. The activated map uses `jumpTo` under reduced motion
  (K14 NEW-10).
- **4.1.3 status:** activation success and failure are announced through `role=status`.
- **Tests:** axe on every dossier template in both Playwright projects, and on the activated state; a keyboard journey;
  the no-JS parity spec (K0 UXK0-1) proves the text of `main` is unchanged, excluding `[data-enhancement]`.

---

## 12. Draft requirements (provisional `SIG-UI-DVnn`; K13/T1 number or fold them) and acceptance tests

| id | requirement (draft spec text) | acceptance test |
|---|---|---|
| SIG-UI-DV01 | Every dossier with ≥ 1 located record MUST show, in "At a glance", a build-time static map of its jurisdiction: outline, child outlines where there are ≥ 2 children, binned or point records, the single-source encoding, the "no published point" counts and the coverage statement. A caption MUST state release, as-of, source count, "not a census" and every drawn compartment's licence line. A place-level table with equal counts MUST follow in the same page. A dossier with 0 located records MUST show the typed empty state, not a blank map. | build test: the figure is present on every dossier template; Σ table counts = figure `desc.records` = K5 `fig-map` value; GU/AS/MP render the empty state |
| SIG-UI-DV02 | Static maps MUST draw points only for tier-0 records where the framing zoom is ≥ 10 and there are ≤ 1,000 records. Otherwise they MUST draw H3 areas at the finest resolution whose average diameter is ≥ 12 px at the figure width, never finer than a record's published precision. Tier-3 records MUST NOT be drawn. | unit tests over fixtures (tiers 0–3, DC-like dense place, small town); a verifier: no drawn coordinate finer than its tier |
| SIG-UI-DV03 | A dossier network figure MUST draw only evidenced edges between anchors placed in the jurisdiction (K4 placement) and their counterparties. It MUST have ≤ 40 nodes, reached by grouping only (no ranking). Every node MUST link. The three access kinds MUST be visually distinct and independently hideable without JavaScript. Every edge MUST carry K2 H-2's fields in its table row. A figure with no evidenced edge MUST NOT be drawn. | fixture with 60 anchors → grouped; no "top"/"most" copy (lint); `:has()` toggles work with JS off; table ↔ figure edge parity |
| SIG-UI-DV04 | Every dossier MUST link the map, the graph explorer and scoped search for its jurisdiction using `sig.workspace-state/2`. A target that cannot apply a facet it receives MUST say so visibly rather than show unfiltered results as filtered. | e2e: `/map/?v=2&jurisdiction=<k>` frames the place or shows the notice; same for `/explore/`, `/search/` (NEW-1) |
| SIG-UI-DV05 | Dossier pages MUST NOT load T2 code before an explicit reader action. In-place activation MUST reuse the static figure's reserved box, keep the static figure in the DOM for print, write no browser history, and hand state to `/map/` for "Open full map" and "Cite this view". | budget spec: 0 T2 bytes before the click; CLS ≤ 0.02 across activation; `history.length` unchanged; the cite URL is the snapshot form |
| SIG-UI-DV06 | Every dossier MUST carry a zero-JS GET search scoped to its jurisdiction and descendants, pinned to its release. | no-JS e2e: a query returns only records whose chain contains the key |
| SIG-UI-DV07 | Dossiers MUST meet T1 budgets (§10) on the largest real dossiers (US, GA, TX, CA) and a small one. Each inline map MUST be ≤ 30 KiB gzip and ≤ 60 SVG elements. | `budget.spec.ts` + generated LHCI entries |
| SIG-UI-DV08 | Printed dossiers MUST include every figure as its static rendition with its caption, attribution, as-of and figure permalink. No figure may split across pages, no control or canvas may print, and symbols MUST stay distinguishable in greyscale. The map MUST lead page 2 after the council brief, with the locator on page 1. | `page.pdf` + PyMuPDF: figures present, footer on every page, no split figure, greyscale raster check |
| SIG-UI-DV09 | Dossier figures MUST meet WCAG 2.2 AA with JS on and off: text alternatives, table equivalents with equal values, a keyboard path to every link, skip links for network figures, 320 px reflow and dark-mode tokens. | axe (both projects + activated state); keyboard journey; reflow at 320 px |
| SIG-UI-DV10 | A static figure's counts MUST equal the dossier's K5 figure values and the interactive map's summed cells for the same framing and release. | parity test over 50 dossiers incl. GA/TX/CA/DC |
| SIG-UI-DV11 | Within one page, each symbol and line pattern MUST have one meaning, drawn from the single legend lexicon. | lexicon unit test; template grep for ad-hoc symbol classes |
| SIG-UI-DV12 | Static figures are produced works. They MUST NOT expose per-area numeric data (no data attributes, no per-area titles), and the dossier-visuals build input MUST NOT be published. | built-HTML grep: no `data-n`/per-area `<title>`; release manifest: no `dossier_visuals` path |

**Spec interactions (for T1, via `spec_src`):**
- **SIG-UI-010:** annotate "the dossier's figures sit in the sections they illustrate (map in at-a-glance; networks in
  deployed/cost/access/policy)".
- **SIG-UI-013:** K0 already adds "embedded visualizations print as their static renditions with basemap attribution". Add
  "each with its figure permalink".
- **SIG-UI-019/020:** confirm that they apply to static figures.
- **SIG-UI-021/022:** the dossier figure is a jurisdiction-scoped, capped bipartite view, consistent with "no hairball".

---

## 13. Acceptance journeys (agent walkthroughs at acceptance, never user research: P4/P5)

| id | persona (D3) | journey | pass |
|---|---|---|---|
| VJ-1 | advocate, Oklahoma City (A1–A3) | `/dossier/` → United States → Oklahoma → Oklahoma City (K4) → read Figure 1 → Print | the map shows every area hollow, and the caption says "1 source" and names it (a community map, K5); page 1 has the locator and brief; page 2 leads with the map; every page has as-of + permalink; greyscale-readable |
| VJ-2 | resident, 390 px, no JS | a county dossier → Figure 1 → a place outline tap → the place dossier → "All N sites" | the map is visible without JS; drill-down works by pointer and via the table by keyboard; the sites list opens (MAP-05) |
| VJ-3 | journalist, Texas (J2) | `/dossier/usa/tx/` → Fig. 4 → untick "declared" → follow an agency node → its entity page → back → "Open in the explorer" → cite | toggles work with JS off; every edge row dated or "undated"; historical never present tense; the explorer opens with `overview=access&jurisdiction=iso3166-2:US-TX`; the cite is the snapshot URL |
| VJ-4 | organizer, Harris County (O1, O3) | search within Harris County "Flock" → a result → back → "Explore this map here" (desktop) → filter source → Cite this view → "Open full map" | results limited to Harris's chain; the map loads only after the click and frames the county; the cite and full map reproduce filters and view |
| VJ-5 | journalist (J1) | California → "from 11 sources" beside Figure 1 → K5 breakdown → "Show on the map" for the ODbL layer | the breakdown sums to the figure; the source filter applies with its zoom-honesty note |
| VJ-6 | keyboard + screen reader | VJ-3 and VJ-4 with keyboard only | skip links; tables as long descriptions; Escape and close return focus; axe clean in each state |

---

## 14. Round-11 ticket outline

Sizes follow J3/K1/K4: **S** ≈ half a fresh-context run, **M** one run. "Live" = a production stage needing an operator go.

| # | key | ticket | size | scope (one line) | depends (K0 / K1 / K2 / K3 / K4 / K5 / K14 / other) | live / gate |
|---:|---|---|---|---|---|---|
| 1 | **VIZ-00** | Contracts and lexicon | S | `sig.dossier-visuals/1` schema; the figure-metadata twin block; figure ids registered with K5 `figures[]`; the single legend lexicon resolving NEW-2 (with UXK14-8); the NEW-4 CSP rule for SVG files proposed to UXK0-3; the SIG-UI-DVnn set handed to T1 | GATE-P; K0 ADR (T1); D-K6-1…7 | — |
| 2 | **VIZ-01a** | Map and locator geometry (exporter) | M | per-dossier projection, fit, simplification, static binning rule, points cap, tier guards, "not drawn" counts, child links and coverage flags, locator geometry + index sprite data, size caps with recorded fallbacks; determinism; size and time report on the real release (US, GA, TX, CA, DC, a small place) | **K4 JUR-01/02b/03** (keys, boundary pack, placement, pages); **K1 MAP-05** (renderer core: projection + simplify, shared; if MAP-05 has not landed, VIZ-01a builds the core in `exports/static_map.py` and MAP-05 consumes it, one owner recorded at T3); MAP-01b `coverage_by_jurisdiction.json` (soft: legend says "rule pending") | rides the next release |
| 3 | **VIZ-02** | Figure components and dossier composition | M | Astro `<DossierMap>`, `<Locator>`, `<DossierNetwork>` (wide + narrow, CSS toggles, skip link), captions, legends, table twins, typed empty states; placement in `[slug]` and `/print/` (§4, §8); print CSS for figures; dark tokens; index locator sprite handed to JUR-04 | VIZ-01a; **K14 UXK14-1** (tokens), **UXK14-3** (Figure, table, empty state), **UXK14-8** (legend and line helpers), **UXK14-9** (running footer, council brief page 1); **K0 UXK0-1** (registry, parity spec); K4 JUR-03/04 (routes); K5 DSRC-02 (section 12); J3 TX-13a (cite) | via release |
| 4 | **VIZ-03** | Explore bar and scoped search | S | the three links with `sig.workspace-state/2`; the scoped GET form; `scope=` on `<sig-typeahead>`; the fallback notes while targets ignore facets (NEW-1); the K5 "Show on the map" control | VIZ-02; **K3 SRCH-04/06** (+ `jc` in shards via SRCH-05); **K0 UXK0-4/5**; K1 MAP-03a, K2 GX-09a, K3 SRCH-05 honouring `jurisdiction` (else notes) | via release |
| 5 | **VIZ-01b** | Network slices | S | anchors via K4 placement, counterparties, the grouping rule, H-rules and relevance filter, table rows, empty-state reasons; `fig-*` breakdowns to K5 | **K2 GX-01, GX-04, GX-05a** (+ GX-07 for access, GX-08a for per-state links); K4 `lookup@1` placement of agencies (I8); L1 NEW-10 dates | rides the next release |
| 6 | **VIZ-04** | In-place map activation | M | `<sig-activate>` wiring; K1 app `embedded` mode (framing, `cooperativeGestures`, list below, filters row, no URL writes, open-full/cite, close/focus, failure notice); desktop-only matching; budgets and axe in the activated state; print keeps the SVG | **K1 MAP-03a/03b** (app, filters, list), MAP-02 (basemap, `context.pmtiles`); **K0 UXK0-4** (`<sig-activate>`), UXK0-3 (CSP), UXK0-6 (Preact) | via release |
| 7 | **VIZ-05** | Acceptance | S | real-release build; SIG-UI-DV01…12 tests; LHCI and budget entries (§10); PDF checks; parity (DV10); VJ-1…6 as labelled agent walkthroughs; readout for K13 | all above in scope; G3 cut → promote (Class S) | **live**: op go |

**Order and parallelism:**
- VIZ-00 → VIZ-01a (after JUR-02b/03) → VIZ-02 (maps live, networks show their typed empty state) → VIZ-03.
- Then VIZ-01b, when GX-05a and agency placement land; this lights the networks up without touching the page code.
- Then VIZ-04, after MAP-03b. VIZ-05 closes.
- Total ≈ 0.5 + 1 + 1 + 0.5 + 0.5 + 1 + 0.5 = **≈ 5 runs**.

**No pre-K4 slice.** Drawing maps on today's 55 bare-code buckets would draw Idaho and Indonesia on one page (F-44/F-317).
The map wave follows JUR-02b.

**Exactly-one ownership (P9; resolves NEW-3):**

| item | owner |
|---|---|
| static renderer core (projection, simplification, H3 binning, context outlines) | **K1 MAP-05**; if VIZ-01a lands first, it builds the core and MAP-05 consumes it (T3 records which) |
| dossier map composition, locator, the index locator sprite data, the entity-page map snippet component (K2 §4.2 row 10) | **K6 VIZ-01a/02** |
| entity ego SVG and overview SVGs | K2 GX-06b / GX-08 |
| dossier network figure (bipartite variant) | **K6 VIZ-01b/02** |
| static charts, legends, line and support helpers | K14 UXK14-8 |
| chart brushing on the K5 explorer | K5 DSRC-05 |
| scoped search form and route | K3 SRCH-06 (K6 places it) |
| sites list pages | K1 MAP-05 |
| `<sig-activate>` element | K0 UXK0-4 |
| embedded mode of the map app | **K6 VIZ-04** |
| running footer, council brief page 1 | K14 UXK14-9 |

---

## 15. Operator decisions needed

| id | decision | recommendation |
|---|---|---|
| **D-K6-1** | Default composition: the map in "At a glance", network figures in their sections, scoped search in the Explore bar, all static and printable | **Yes** |
| **D-K6-2** | The interactive map loads in place **only on click**, on desktop; phones navigate to `/map/`; no automatic loading on scroll | **Yes** (keeps dossiers T1; K0 §4.3) |
| D-K6-3 | Network figures are static (≤ 40 nodes, grouping only, no ranking); no in-page graph explorer; expansion in `/explore/` | **Yes** |
| D-K6-4 | Static binning rule (areas ≥ 12 px across; points only at z ≥ 10 and ≤ 1,000 records), and ask K1 to tune its band table to the same rule | **Yes** |
| D-K6-5 | "Download figure (SVG)" only for country and admin-1 dossiers in Round 11 | **Yes** (≈ 1.7k objects vs ≈ 28k) |
| D-K6-6 | Print: locator on page 1 (council brief); the map leads page 2 | **Yes** |
| D-K6-7 | One legend lexicon: hollow = one source (map); line pattern = access kind; currency = muted ink + words; no "hollow" in network figures (NEW-2) | **Yes** (with D-K14-5) |

---

## 16. Risks

| id | risk | mitigation |
|---|---|---|
| R-1 | Maps read as density or a census (13–16 state maps are all single-source) | hollow discs, "not a census", coverage statement bound to the figure (V-3), K5 source share beside it |
| R-2 | Network figures read as accusation (guilt by association) | relation in words, dates, currency, sources on every row; no ranking; typed absence (K2 R-1) |
| R-3 | Static and interactive disagree | the same cells and rule; DV10 parity test; D-K6-4 |
| R-4 | Page weight creeps on GA and TX | caps with recorded fallbacks; real-size CI; one path per class |
| R-5 | Build time and object growth | restricted build input; SVG downloads only at the top levels |
| R-6 | Part VIII: precision leaks through static points | tier guards, verifier, points only for tier 0 at z ≥ 10 |
| R-7 | Licence mixing through figure data | no per-area data; build input unpublished; caption licence lines (V-9) |
| R-8 | Networks stay empty at launch (no agencies placed today, G5) | honest empty state naming why and what closes it; VIZ-01b decoupled from page code |
| R-9 | The embedded map captures page scrolling or focus | `cooperativeGestures`; desktop only; close button; focus contract |
| R-10 | `:has()` missing in old browsers | everything shown by default (safe); the table lists all edges |
| R-11 | Records declared here but located elsewhere "vanish" from the map | the legend box counts and links them (K4-P3) |
| R-12 | Targets ignore `jurisdiction=` (NEW-1) and a dossier link silently shows the nation | DV04 notice; VIZ-03 falls back to static equivalents until MAP-03a, GX-09a and SRCH-05 apply the facet |

---

## 17. Interfaces

| row | K6 needs | K6 gives |
|---|---|---|
| K0 | T1/T2 budgets, `<sig-activate>`, `<sig-table>`, `sig.workspace-state/2`, the registry, parity and budget specs, CSP | a dossier template that proves T1 + in-place T2; the NEW-4 CSP rule for SVG files |
| K1 | the app's `embedded` mode hooks, MAP-05 renderer core, `context.pmtiles`, sites lists, `coverage_by_jurisdiction.json`, `jurisdiction`/`source` facets applied | the ≥ 12 px band proposal (D-K6-4); a dossier entry point to the map |
| K2 | GX-01 labels, GX-04 relevance, GX-05a relations, GX-07 access facts, `/graphs/<id>/<state>/` pages, `/explore/` honouring `jurisdiction` | the entity-page map snippet component; the bipartite place figure |
| K3 | SRCH-04 HTML results, SRCH-06 form, `jc` on shard entries, `scope=` on `<sig-typeahead>` | the placement of scoped search on every dossier |
| K4 | keys, chains, placement, boundary pack, page thresholds, routes, `lookup@1` | the locator and index sprite for JUR-04; drill-down links between levels |
| K5 | `figures[]` entries for `fig-*`; "Where this comes from"; licence lines | the figure ids; "Show on the map" per source row |
| K7 | next decision for "At a glance"; watch items for the timeline | — |
| K14 | tokens, Figure, table, empty states, UXK14-8 helpers, UXK14-9 print | the legend lexicon input (NEW-2) |
| G3 / J3 | `/s/<pub>/` snapshot cite, TX-13a, stamp, V11 budgets on the release | figure permalinks |
| I8 | agency placement and procurement routing (network content) | — |
| K13 | — | the dossier template, requirements, tickets |

---

## 18. New findings (`findings/incoming/K6.csv`)

| id | sev | title |
|---|---|---|
| NEW-1 | S2 | `sig.workspace-state/1` parses and round-trips the `jurisdiction`, `source`, `location` and `technology` facets, but none of the three islands applies them. A place-scoped link (`/map/?v=1&jurisdiction=TX`) silently renders the unfiltered view with no issue note, so the dossier → map/graph/search links K4 and K6 plan cannot rely on today's islands |
| NEW-2 | S3 | Symbol meanings collide across K rows: K2 marks historical edges with a dash and undated with hollow; K14 reserves dashed for declared access and dotted for historical; K1 uses hollow for single-source sites. A dossier carrying Figure 1 and a network figure would give "hollow" and "dashed" two meanings on one page |
| NEW-3 | S3 | Ownership of the static SVG generators is circular. K1 says MAP-05 owns the static map renderer ("K6 consumes"). K2 GX-06b and §4.2 cite "K6's generator". K4 JUR-04 depends on "K6 (locator)". K5 DSRC-05 depends on a "K6 chart component" that no row defines |
| NEW-4 | S3 | K0's target CSP (`style-src 'self' <hashes>`, no `unsafe-inline`, "on every public response") would block the inline `<style>` block that K14 §4.7 prescribes for standalone SVG images (their own `prefers-color-scheme` rules) whenever such a file is opened directly. No row owns the header rule for `.svg` responses |

---

## 19. Limitations and command log

**Limitations.**
- Map sizes come from Web Mercator renderings with this row's own simplifier and a synthetic markup close to the proposed
  one. The real component differs by a few percent (path-per-class encoding was not built). County outlines use the
  generalised CB 500k files, not TIGER (placement uses TIGER, K4), so a few coastal points may differ (validation matched
  K4 exactly for CA, OK and Harris).
- The US map was measured for the lower 48 in Web Mercator. K1's Albers + insets variant will differ (inference: similar
  order).
- Network sizes are synthetic. No release data places any relationship today (G5), so no real dossier network could be
  measured.
- Place-level (city) maps were not measured: the Census place file was not downloaded. The DC and Oklahoma County cases
  bracket them.
- Browser behaviour for CSP headers on SVG images (NEW-4) and `:has()` toggles in print were not tested. MapLibre's
  `cooperativeGestures` is confirmed in the typings, not in a running page.
- Latency and Lighthouse figures are targets, not measurements. No browser was used in this row.
- No human reviewed anything here (P4).

**Commands (read-only; outputs in the session scratchpad `k6/`, not durable; results quoted above).**

| # | when (`date -u`) | command | result |
|---|---|---|---|
| C1 | 22:39:16Z | `git branch --show-current`; `ls` of the planning dirs | `claude/next-phase-planning` |
| C2 | 22:40Z–22:44Z | reads of META_PLAN §3/§8.2/K rows, K0, K1, K2, K3, K4, K5, K14, D3, spec §39 (`sed -n 5720,5860p`), dossier code, exporter `spine_export.py:1265-1560` | §1 |
| C3 | between C1 and C4; re-run and stamped 22:53:49Z | `grep -n 'state\.' web/src/islands/*.tsx`; `grep -rn 'state\.(technology|jurisdiction|source|location)' web/src` | 0 consumers (NEW-1) |
| C4 | 22:45:53Z–22:45:54Z | `curl -s -o … https://www2.census.gov/geo/tiger/GENZ2025/shp/cb_2025_us_{state,county}_500k.zip` | 200, 3,245,373 B (sha256 `9cbfe171…`) and 11,758,981 B (`aa976c00…`) |
| C5 | 22:46:48Z–22:47:43Z | `measure_maps.py` (duckdb 1.5.5 over C3's parquet capture, dedup by `entity_id` → 227,335 points; numpy PIP; h3 4.5.0; gzip -9; brotli -q 11) | §2.1; `map_sizes.json` sha256 `4f102f1b…` |
| C6 | 22:49:14Z–22:49:38Z | `measure_all.py` (all 56 state-equivalents; US lower 48) | §2.2; `all_states.json` sha256 `6433225c…` |
| C7 | 22:48:59Z | `measure_net.py` (synthetic two-column network SVGs) | §2.4 |
| C8 | between 22:47:43Z and 22:48:59Z | Python over `C3/bucket/web/{dossiers,network}.json` | G4, G5 |
| C9 | 22:54:24Z (DC); the typings `grep` ran between 22:54:24Z and 22:59:28Z | `measure_dc2.py` (DC under the points cap); `grep` for `cooperativeGestures` in the installed MapLibre typings | DC 204 areas, 11,059 / 2,445 / 1,908 B; G8 |
| C10 | first pass between C4 and C6; final pass 23:00:03Z | `grep` of `findings/FINDINGS.csv` + `incoming/*.csv` for workspace/jurisdiction-facet, dossier↔map, print-footer, hollow/dashed/dotted, CSP+SVG and generator-ownership items | NEW-1…4 not present; the print footer is C2 NEW-6 (not re-raised) |

Script hashes (sha256): `measure_maps.py` `bcf6ef57…`, `measure_all.py` `aad221df…`, `measure_net.py` `549b4816…`.

Work window closed **2026-09-30T23:01:19Z** (`date -u`, stamped at write-out).
