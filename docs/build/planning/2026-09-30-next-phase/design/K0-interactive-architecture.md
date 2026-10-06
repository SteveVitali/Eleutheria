# K0 — Interactive architecture: re-examining the zero-JS constraint

- **Row:** K0 (Stream K, architecture/design) · **Written:** 2026-09-30 (work window 21:45Z–22:10Z, `date -u`)
- **Worktree HEAD at write time:** `665a3696` (branch `claude/next-phase-planning`). `web/`, `AGENTS.md`, `docs/adr/` and the
  generated spec are byte-identical to chain tip `b051732c` (`git diff --stat b051732c HEAD -- web AGENTS.md docs/adr
  docs/2_canonical_design_spec.md` is empty), so every `code` citation below is also a chain-tip citation.
- **Operator input answered:** U-003 ("think and research and reason carefully about perhaps breaking with our no-JS
  constraints"), with U-005 (journalists must "really truly explore the knowledge graph … querying/exploring the data
  interactively, always with full explicit transparent evidence/lineage"), U-007 ("beautiful and useful and intuitive UI/UX …
  query/explore/navigate the knowledge graph interactively in powerful ways") and U-008 (≤ $300/month without an explicit go).
- **Inputs read:** META_PLAN §3 and Stream K; `feedback/OPERATOR_FEEDBACK.md` U-001…U-015; `research/K12a-prior-art.md`
  (primary evidence, cited as K12a [Qnnn]); `research/J2-prior-art.md` (§7 Q1, PC ids); `review/JOURNEYS.md` (C2 §6);
  `review/R10_PREVIEW.md` (C4 §3.6); `review/K12b-explorability.md`; `review/DATA_TRUTH.md`; `design/J3-transparency-design.md`;
  `design/G3-release-model.md`; `design/K9-sources-table.md`, `K11-research-queue.md` (their K0 hooks); `research/G1-ops.md`
  §3.8 and `research/J4-redistribution-matrix.md` (unit prices); `research/I3-alpr-networks.md` (sharing-edge counts);
  `docs/build/reports/p32.15-island-budgets.md`; `web/lighthouserc.json`, `web/astro.config.mjs`, `web/package.json`,
  `web/AGENTS.md`, `web/src/islands/*`, `web/src/pages/{map,network,search}.astro`, `web/src/styles/islands.css`,
  `web/tests/e2e/{pages,islands.spec,budget.spec,island-budgets.json}`; `AGENTS.md` gotcha 6; ADR-068, ADR-091, ADR-097,
  ADR-134; spec SIG-UI-002/013/021/022/035–041/047/049/050, SIG-GEO-012/013, SIG-FIND-002–005.
- **Evidence classes (P1):** `code` (file:line at `665a3696`), `recorded-execution` (commands run for this row, §14),
  `live-read` (two HEAD requests to the live site, 21:50:51Z), citations of other rows by id. Everything about cost,
  future sizes and user behaviour is **`inference`** and labelled.
- **Status vocabulary (P5):** nothing here is engineered or verified. This is a design and a decision proposal; the ADR in
  §6 is a draft that T1 numbers and the operator ratifies (GATE-P).
- **P3/P14/P16:** production was only read (two `curl -sI` HEADs). Library sizes were measured by installing packages into
  the session scratchpad with `npm install --userconfig=/dev/null --ignore-scripts` (no credentials, no identity, no
  tracked file touched). No secrets appear here.
- **Writes:** this file and `findings/incoming/K0.csv` only.

---

## 0. The decision on one page

**Recommendation: option (c) built with option (b)'s rules — "HTML-first page types".** Keep the zero-JS rule where it
earns its keep (the citable record and print), replace the *named-island allow-list* with a *page-type registry* that gives
every public route a JS budget, and let three app-like explore surfaces (map, graph explorer, search) be genuinely
interactive — with URL-encoded state, a server-rendered first paint, and a complete no-JS equivalent.

Why, in five lines:
1. **The evidence says the static pages are the best part of the site, and the JS pages are the worst.** Static content
   pages score Lighthouse 1.0/1.0 with 7–24 KB transferred; every performance and layout-shift failure C2 and C4 recorded,
   and the one abandoned mobile task, is on the three JS islands (§1.3). The static pages' failures are content, labels and
   320 px reflow, not speed. The lesson is *disciplined* JS, not *more* JS everywhere.
2. **Most of what the operator asked for needs no new JS.** Of the eleven U-003 asks, seven are blocked by data, labels
   and information architecture, not by the rule; three need small, budgeted JS; one (the map) already has JS (§1.4).
3. **Exploration does need real interactivity** (U-005/U-007): pan/zoom over a basemap, overview graphs that can be
   navigated, typeahead and faceted search. These fit a "JS-heavy" budget only on dedicated surfaces (K12a §6, [Q085]).
4. **The citable record must stay readable by anything** — councils, archives, crawlers, link unfurlers, LLM agents,
   printers. Every JS-first peer K12a fetched was an empty shell ([Q063], [Q060], [Q061], [Q062], [Q044], [Q036]).
5. **A full SPA buys nothing SIG needs** and loses citation stability, print and archivability (ADR-091 C; K12a §9).

**The rule in one sentence.** *Every public route has a declared page type; the record and print types ship no executable
script; content pages may load small, approved enhancements but must show every fact with JS off; explore surfaces may be
app-like but must encode their state in the URL, paint server-side first, and link to a no-JS equivalent — all inside
per-type budgets measured in CI on real-sized data.*

| type | routes (§4.2) | initial JS (gzip) | Lighthouse mobile | LCP / CLS / TBT | no-JS rule |
|---|---|---|---|---|---|
| **T0 record & print** | `/r/**`, every `…/print/`, `/dispute/`, `/intake/**`, API `format=html`, tombstones | **0** (no `<script>` element) | ≥ 0.95 | ≤ 1.5 s / ≤ 0.02 / 0 | the page *is* the no-JS page |
| **T1 content** | home, dossiers, entity, source, sources table, research queue, watch, evidence, methodology, releases, data, status | **≤ 20 KiB**, none render-blocking; ≤ 40 KiB more only after a user action | ≥ 0.95 | ≤ 1.5 s / ≤ 0.02 / ≤ 50 ms | JS-off text equals JS-on text |
| **T2 map** | `/map/` | **≤ 360 KiB** (today 497 KB) | ≥ 0.75 | ≤ 2.5 s / ≤ 0.05 / ≤ 350 ms | static overview + paginated tables + place form |
| **T2 graph explorer** | `/explore/` (`/network/` redirects) | **≤ 120 KiB** | ≥ 0.90 | ≤ 2.0 s / ≤ 0.05 / ≤ 200 ms | entity pages, relationship tables, static SVG graphs |
| **T2 search** | `/search/` | **≤ 60 KiB** | ≥ 0.95 | ≤ 1.5 s / ≤ 0.02 / ≤ 100 ms | GET form → server-rendered results |
| T3 curation | `/curate/**` (loopback, never published) | ADR-068 unchanged | — | — | — |

**Named dependencies (measured, §2.1):** MapLibre GL 6.9.0 + PMTiles 4.5.0 (≈ 300 KB gzip once the duplicated worker chunk is
removed), `@protomaps/basemaps` 5.7.2 (6.7 KB), Preact 10.29.8 (5.4 KB) replacing React 19 (65.7 KB runtime), sigma 3.0.3 +
graphology 0.26.0 (37.8 KB; 50.4 KB with layout, community and path algorithms), MiniSearch 7.2.0 (5.9 KB). Rejected by
default: cytoscape (141 KB), sql.js (322 KB WASM), Leaflet (a second map stack), third-party tile or geocoding services.

**Data plan (§5):** records, entity pages, 1-hop neighbourhoods, overview graphs, typeahead shards and static map renditions
are **static files per release**; overlay and basemap tiles are **static PMTiles** on a zero-egress host; only full-text
search and "sites in this viewport" need the **release-pinned API** (the landed P32.14 FTS5 path, extended). Incremental
cost ≈ $5–15/month at 10k map sessions, ≈ $25–40 at 100k on GCS or ≈ $5–10 on R2 (inference, §5.3) — inside U-008's $300.

**ADR headline (§6):** *ADR-NNN — HTML-first page types: zero-JS records and print, budgeted enhancement on content pages,
app-like explore surfaces with URL state.* It supersedes the named-island rule of ADR-091 §3–4 and ADR-097 §2–3/§6,
extends ADR-134 to `sig.workspace-state/2`, and leaves ADR-068 unchanged.

---

## 1. The current rule, why it was chosen, and what it cost

### 1.1 The rule as enforced today (`code`)

| layer | where | what it enforces |
|---|---|---|
| Project guidance | `AGENTS.md:116` (gotcha 6); `web/AGENTS.md:40` (gotcha 1) | content pages render with no `<script>`; the named islands are the bounded exceptions |
| Spec | SIG-UI-036 (SHOULD, spec:5940), SIG-UI-037 (MUST, :5946), SIG-UI-047 (MAY, :5959), SIG-UI-050 (MUST, :5971), SIG-UI-041 (MUST, :5990), SIG-FIND-004/005 (:7341/:7343) | zero-JS-by-default framework; core usable without JS; every map has a table and every graph a list; the island set is exactly map/graph/search and a fourth needs a new ADR; "every other public page MUST still ship zero client JavaScript"; per-island budgets; "the no-basemap decision remain[s] in force" |
| Decisions | ADR-091 (DECISION-SPA = B, operator-ratified 2026-09-22), ADR-097 (the three islands, `client:only="react"`), ADR-134 (`sig.workspace-state/1`, measured per-island ceilings), ADR-068 (`/curate/**`) | named set; full SPA rejected; viewport deliberately *not* in the URL (ADR-134 §1 "Not carried") |
| Build | `web/astro.config.mjs` `output: "static"`; client JS only through a greppable `client:*` directive | three directives exist: `map.astro:133`, `network.astro:99`, `search.astro:140` |
| Lighthouse | `web/lighthouserc.json:26-32` | every non-island page: script size **0**, total ≤ 153,600 B, perf ≥ 0.9, a11y 1.0; islands (`:51-54`): a11y 1.0, perf **warn** 0.5; map ceiling 2.0 MB script / 2.3 MB total (`:62-66`), network and search 400/450 KB (`:74-90`) |
| e2e | `web/tests/e2e/islands.spec.ts:13-28`, `pages.ts:117-130` | `expect(html).not.toContain("<script")` on a **hand-listed** set of routes; islands must contain `<script` |
| Wire budgets | `web/tests/e2e/budget.spec.ts`, `island-budgets.json` | map ≤ 600 KB gzip script, network/search ≤ 140 KB gzip script, documents ≤ 150 KiB |

### 1.2 Why zero-JS was chosen

| reason | source | still valid? |
|---|---|---|
| **Archivability.** "SIG pages will be archived, cited in filings, and read from web archives years later"; a zero-JS default makes it structural rather than a discipline that erodes | SIG-UI-036 rationale (spec:5940-5944); ADR-091 context | **Yes** — for the record. Web archives replay JS poorly (inference) |
| **Accessibility.** Core content without JS "is simultaneously an accessibility requirement and an archival one" | SIG-UI-037 | **Yes.** C2: static pages axe-clean and keyboard-clean; WebAIM 2026 correlates Astro sites with 84 % fewer detected errors (correlation only, K12a [Q078]) |
| **Citation stability.** A citation must reproduce after SIG corrects itself | SIG-UI-035, SIG-FIND-001/002; G3 path-pinned releases | **Yes.** Client-rendered state cannot be cited unless it is in the URL and resolvable |
| **The design-center persona** needs "paper, not a URL" | SIG-UI-002, SIG-UI-013 | **Yes.** Printing is the advocate's core task (U-001, U-002) |
| **Performance on real devices.** "A dense evidence page that takes eight seconds to load will not be used at a podium" | SIG-UI-041; K12a [Q085] P75 device (Galaxy A51, 7.2 Mbps) | **Yes.** Markup-heavy pages: ≤ 75–100 KiB JS; JS-heavy apps: ≤ 365–650 KiB |
| **Low-bandwidth and hostile networks.** JS fails through "temporary network errors", "ad blockers", "corporate firewalls" | GOV.UK (K12a [Q074]) | **Yes** |
| **Machine readability.** "Not all bots can run JavaScript"; peers built as JS shells were unreadable to K12a's fetcher | Google (K12a [Q077]); K12a §6.1 | **Yes**, and growing: agents and unfurlers read SIG pages |
| **Security and privacy.** No executable code means no XSS sink and no browser supply chain; no third-party requests means a reader's interests are not leaked | inference; SIG-UI-038 (no hard third-party tile dependency); ADR-134 (no localStorage history, no analytics) | **Yes** — more so for readers of a surveillance-accountability site |
| **Resilience.** Static files on object storage survive the application being offline and can be mirrored | SIG-GEO-012 rationale; §46.5 | **Yes** |

### 1.3 What it cost (evidence)

| cost | evidence | who carries it |
|---|---|---|
| **No basemap.** The map is dots on a grey canvas; residents abandon it | Round-9 Q8 decision (`web/src/lib/map-tiles.ts:14-15`); C2 P6-T1/P6-T2 **fail**; K12b A7; F-100 | resident, advocate, journalist |
| **The no-JS map fallback became a 3.46 MB HTML document** (1,504 table rows, 5,290 gap links, many 404) | K12a §1 [Q005]; C2 §6.2 (271 KB transferred vs a 153,600 B document budget); K12b NEW-7 | mobile users (C2 P12-T2 **fail**) |
| **Island performance and layout shift.** `/map/` mobile perf 0.86, LCP 2.23 s, TBT 352 ms, 816 KB (prod); 0.44 and LCP 8.25 s on fixtures; `/network/` CLS 0.311, `/search/` CLS 0.326 (desktop) | C2 §6.2; C4 §3.6; F-115, F-171 | everyone on the islands |
| **Search is a client filter over a 500-row sample** serialized into the page (`items={INDEX}`, `search.astro:140`); "Canberra" → 0 | K12a §1 [Q004]; C2 P6-T1; F-101 | every persona |
| **The graph is a 131-node UUID star**, capped at 50 nodes / 100 edges (`network.ts:182-183`) | DATA_TRUTH §4.15; F-102; K12b NEW-5 | journalist (U-005) |
| **Sorting and filtering without JS need one pre-rendered route per sort × facet**, so J3 and K9 had to forbid facet × facet products and push multi-facet filtering onto the `/search/` island; K12b found the live freshness sorts are no-ops | J3 G-11, §6.5; K9 §6.1; K12b F-17/NEW-11 | journalist, researcher |
| **Embedded dossier visualizations (U-003.6) are impossible** without a new named island per page, each needing an ADR | SIG-UI-050 "changes this named set only by a new ADR"; K12a §9 option (a) | advocate |
| **The map viewport cannot be shared or cited** (ADR-134 §1 keeps `z/lat/lon` out of the URL); map popups cite the national map, not the point | ADR-134; K12b NEW-6 | journalist, attorney |
| **Enforcement is by hand-listed routes**, so new pages are unchecked by default (this row, NEW-4) | `pages.ts:55,125-130` | the build's truth |

### 1.4 What the rule did *not* cause (honest attribution)

The operator's complaints are mostly about names, context and missing pages. JavaScript fixes few of them.

| ask | main blocker (evidence) | needs new JS? |
|---|---|---|
| U-003.1 map | no basemap (an operator decision, Q8), no place search, popups with UUIDs and no links (K12b F-02), 5,290 dead links | **already JS**; plus a small typeahead |
| U-003.2 graph | labels: the API already names the hub "Vigilant Solutions (LEARN)" but the site shows UUIDs (K12b, S1); **82.8 % of published entities have an empty label** (this row, NEW-1); no entity pages | **yes** for an overview explorer; entity pages and ego graphs need **none** |
| U-003.3 search | a 500-row client sample; no place names; the API's `/v1/search` unused (K12b F-23) | **small** (typeahead); results can be server-rendered |
| U-003.4 dossier grouping | jurisdiction keys and IA (K4) | none |
| U-003.5 source contributions | data routing (K5) | none (tables) |
| U-003.6 embedded visualizations | forbidden on content pages by SIG-UI-050 | **none** if rendered as static SVG; optional activation |
| U-003.7 watch · U-003.8 evidence · U-003.11 queue | empty or unrouted data (K7, K8, K11) | none (K11's filter is optional) |
| U-003.9 sources table | missing columns and rows; no-op sorts (K9) | **small** (≤ 15 KiB table enhancement, K9 §6.2) |
| U-003.10 source pages | not built (K10) | none |

**Conclusion.** The zero-JS rule's real costs are narrow: the combinatorics of no-JS filtering, the ban on embedded
visuals, the ban on sharing a map view, and an allow-list that forces an ADR for every small enhancement. The bigger damage
came from building the three islands against fixture data with no real-size budgets, no reserved layout and no
server-rendered first paint. The new rule must fix both.

---

## 2. Measurements taken for this row

All `recorded-execution` unless marked; commands in §14.

### 2.1 Browser libraries (minified ESM bundle via esbuild 0.28.2 from `web/node_modules`, `gzip -9`, `brotli`)

| library (version, licence) | raw | gzip | brotli | role |
|---|---:|---:|---:|---|
| MapLibre GL 6.9.0 + PMTiles 4.5.0, single bundle (BSD-3) | 1,079,443 | 291,357 | 240,741 | map renderer |
| MapLibre 6.9.0 ESM split: `maplibre-gl.mjs` / `-shared.mjs` / `-worker.mjs` | 585,178 / 513,245 / 19,011 | 147,906 / 146,250 / 6,071 | 124,874 / 120,541 / 5,432 | ≈ **300 KB gzip** if the shared chunk is loaded once |
| `maplibre-gl.css` | 83,195 | 10,490 | — | map CSS |
| PMTiles 4.5.0 alone | 19,065 | 7,439 | 6,671 | range-request tile reader |
| `@protomaps/basemaps` 5.7.2 (BSD-3) | 38,038 | 6,661 | 5,493 | basemap style layers |
| React 19.3 + react-dom client (MIT) | 222,733 | 68,885 | 59,306 | today's island runtime |
| **Preact 10.29.8 + hooks** (MIT) | 12,960 | **5,387** | 4,914 | proposed runtime |
| **sigma 3.0.3 + graphology 0.26.0** (MIT) | 159,021 | **37,807** | 32,926 | WebGL graph renderer |
| + ForceAtlas2, Louvain, shortest path | 206,620 | 50,394 | 43,851 | client algorithms (prefer build-time) |
| graphology + shortest path only | 86,195 | 19,126 | 16,765 | path finding without rendering |
| cytoscape 3.34.3 (MIT) | 443,812 | 141,376 | 119,979 | alternative renderer |
| **MiniSearch 7.2.0** (MIT) | 17,654 | **5,901** | 5,290 | fuzzy/prefix search over a shard |
| Orama 3.1.18 (Apache-2.0) | 64,036 | 21,739 | 18,941 | alternative |
| FlexSearch 0.8.212 (Apache-2.0) | 50,516 | 17,236 | 15,523 | alternative |
| accessible-autocomplete 3.0.2 (MIT) | 55,845 | 19,984 | 18,004 | GOV.UK combobox reference |
| Leaflet 1.9.4 (BSD-2) | 150,337 | 43,435 | 37,956 | second map stack (rejected) |
| supercluster 9.1.0 (ISC) | 9,624 | 4,069 | 3,694 | client clustering (not needed) |
| sql.js 1.14.2 (MIT): `sql-wasm.wasm` + `.js` | 658,410 + 46,535 | 321,811 + 16,705 | 278,737 + 14,803 | static SQLite search (rejected) |

Versions are what the public registry served on 2026-09-30; K-row tickets pin exact versions at implementation time.

### 2.2 Today's built island assets (`web/dist/_astro`, fixtures build of 2026-09-30T13:02 local)

| asset | raw | gzip | brotli | note |
|---|---:|---:|---:|---|
| `MapIsland.dWareG7G.js` | 1,054,335 | 282,041 | 232,144 | MapLibre main + shared + app |
| `maplibre-gl-worker-DsvDs_fr.js` | 506,723 | 143,352 | 118,334 | **worker + a second copy of the shared chunk** (NEW-2) |
| `client.Buyw3Q1S.js` (React runtime) | 212,931 | 65,693 | 56,863 | **≈ 90 %** of the network and search islands' 73 KB gzip script |
| `NetworkIsland` / `SearchIsland` | 6,919 / 5,373 | 2,775 / 1,985 | — | the island code itself is tiny |

All 128 distinctive string literals in the worker file also appear in `MapIsland.*.js` (§14 C7): the shared chunk ships
twice because `MapIsland.tsx:58` imports the worker with Vite's `?worker&url`. Loading MapLibre's own ESM split instead would
cut ≈ 125 KB gzip (≈ 29 %) from the map (inference from the two measurements; K1 verifies in a build).

Each island page also carries 2 inline scripts (4,510 B, Astro's island bootstrap) and 1 inline `<style>`; `/map/` and
`/network/` add one `style=""` attribute each (`dist/{map,network,search}/index.html`). A strict CSP must hash or remove
them (§4.8). Astro 7.2.4 has a built-in
`security.csp` option that hashes inline scripts and styles (`node_modules/astro/dist/core/config/schemas/base.js:244-259`);
it is unset today.

### 2.3 Data payloads (live release `sig-2026-09-27-ce480ab1`, C3's hashed bucket capture)

| quantity | value | consequence |
|---|---|---|
| Published entities | **232,625** distinct (236,994 rows), all `entity_type = deployment` | the public graph today is sites, not agencies or vendors |
| Entities with an **empty label** | **192,536 (82.8 %)**: `osm_physical` 154,483 of 154,705; `public_record` 19,828 of 39,921; `operator_accepted` 12,881 of 21,682; `dot511_ccbysa2` 2,936 of 3,000; `ccby3` 861 of 861; `sig_graph` 1,093 of 4,834 | labels must be *derived* (type · operator · place), never read from `label` alone (NEW-1; K2) |
| Name index over all 232,625 (label, type, jurisdiction, id) | 15.2 MB raw · **4.87 MB gzip** · 3.72 MB brotli | cannot be preloaded |
| Name index over the 40,089 labelled entities | 2.70 MB raw · 880 KB gzip; per compartment 1.2 KB–441 KB gzip | shardable |
| …as 2-character prefix shards (618) | median 416 B, p95 4.9 KB, max 46 KB gzip | **static typeahead is feasible** |
| …as 3-character prefix shards (3,196) | median 134 B, p95 919 B, max 46 KB gzip | one prefix dominates; K3 splits it |
| SQLite FTS5 over the 232,625 records (label, id, source, jurisdiction) | `unicode61` **37.7 MB**; `trigram` **96.6 MB** | fine on a server; too big for clients |
| Overlay tiles (12 per-compartment PMTiles, z0–z14) | **42.5 MB** total; `osm_physical` 27.9 MB | clients fetch only tiles in view |
| Published network (`web/network.json`) | 52,983 B; 131 nodes, 130 edges; `sharing_edges.csv` 174 KB (372 more unclassified claims) | tiny today |
| Sharing edges already ingested but unresolved | **474,184** Flock share-list edges from 917 portals to 6,849 targets (I3 §1, line 92) | a Flock agency's ego averages ≈ 517 partners → aggregation is mandatory |
| Claims | ≈ 2.42 M (C2 §7) | never shipped to a browser; rendered server-side per entity |
| Release tree (P32.13) | 475,112 files, 2.0 GB, ≈ $2.4 in writes per full upload (J3 G-10) | the static-record cost driver |

### 2.4 Graph payloads (synthetic, labelled nodes with positions; JSON, gzip)

| nodes / edges | raw | gzip |
|---|---:|---:|
| 50 / 100 (an ADR-134 ego) | 7,599 | 2,964 |
| 500 / 1,500 | 84,162 | 28,276 |
| 3,000 / 10,000 (an overview graph) | 534,678 | 176,048 |

---

## 3. The options, compared

### 3.1 The four options, concretely for SIG

- **(a) Static core + richer bounded islands.** Today's model: the named set grows (map, graph, search, maybe sources); every
  other page stays at 0 script; each new island needs an ADR.
- **(b) Progressive enhancement everywhere, with per-page JS budgets and mandatory no-JS fallbacks.** Any page may load
  enhancement modules within its budget; the HTML is always complete.
- **(c) Static content pages + app-like explore surfaces.** Record pages stay static and printable; map, graph and search
  become real applications with URL state, a server-rendered first paint and a no-JS equivalent.
- **(d) Full SPA.** One client application with a router; pages are rendered by JavaScript (optionally with SSR).

### 3.2 Comparison

| dimension | (a) static + islands | (b) PE everywhere | (c) static + explore apps | (d) full SPA |
|---|---|---|---|---|
| **Accessibility (WCAG 2.2 AA)** | strong on content; islands need per-island work (today: map features not keyboard-operable, C2 §6.3, K12b NEW-9) | strong if each enhancement is tested JS-on and JS-off; more states to test | strong on content; explore apps need list equivalents for canvas content (MapLibre and sigma are not screen-reader accessible, K12a A11Y-5) | depends entirely on discipline; WebAIM's framework data leans against it (K12a [Q078]) |
| **Printability** | excellent, but no visuals in print | good: static renditions print, enhancements hidden | good: records print with static SVG visuals; explore apps print their static rendition | poor: canvas and client-only views need a rebuilt print path |
| **Crawl, archive, citation (G3)** | excellent | excellent (HTML complete) | excellent for records; explore state citable only via URL + snapshot (§4.5) | poor: shells unreadable (K12a §6.1), soft-404 risk [Q077]; permalinks need SSR |
| **Performance** | best on content; islands unbudgeted in practice | good if budgets bind; risk of death by a thousand modules | content unchanged; explore apps sized as "JS-heavy" (≤ 365 KiB [Q085]) | worst initial load; router + framework on every page |
| **Hosting and cost** | static only | static + optional API | static + tiles + a small release-pinned API for search and viewport lists | static shell + heavy API use, or an SSR server (a new runtime service) |
| **Data freshness** | per release | per release | per release; status lane (J3) for operational metrics | tempts live-spine reads that break citation and API/site parity (G3 REL-05) |
| **Security** | minimal surface | small surface per module | bounded: three apps, allow-listed deps, strict CSP | largest surface; the whole site is executable |
| **Maintenance (agent-built)** | an ever-growing named list and ADR churn | many small modules; needs a component kit | one kit for content + three apps; clear ownership | one framework, but routing, SSR, hydration and state are hard for agents to keep correct |
| **Testability** | simple (script = 0) | needs JS-on/JS-off parity tests on every page | parity tests on content + journey tests on three apps | full browser tests everywhere; no cheap invariant |
| **Fit to U-003/U-005/U-007** | partial: no embedded visuals, awkward filtering | good for content; exploration still needs apps | **best**: exploration where it matters, record where it matters | exploration yes, record no |

### 3.3 Reading the comparison

- **(d) is rejected.** Every source on accessibility, crawlability and citation argues against it (K12a §6, §9), it
  contradicts the operator-ratified ADR-091, and it would move SIG from static files to a runtime service, which §46.5 and
  SIG-GEO-012's rationale reject. Nothing the operator asked for requires it.
- **(a) is too narrow.** It cannot put a map or network on a dossier (U-003.6) without a new island per page, it keeps
  the no-JS filtering combinatorics (J3 G-11), and its allow-list is already failing open (NEW-4).
- **(b) alone is right for content pages but wrong for the explore surfaces.** A map or a graph explorer is not an
  "enhanced page"; its core interaction is inherently scripted. Pretending otherwise produced today's 3.46 MB "fallback".
- **(c) alone risks two products.** Without (b)'s rules, content pages stay frozen and explore apps drift into
  unbudgeted, uncitable shells (K12a §9 "Against").
- **(c) with (b)'s rules** keeps one site with one component kit and one state contract: content pages are complete HTML
  that may be enhanced a little; three surfaces are allowed to be applications, under rules that keep them citable,
  accessible and fast.

---

## 4. Recommendation: the rules

### 4.1 Invariants (binding on every K row and every Round-11 web ticket)

- **I-1 The record is HTML.** Every entity, source, dossier, release, evidence and claim view is complete in server-rendered
  or build-time HTML. That HTML is what is cited, printed, archived and crawled.
- **I-2 Every visual has a static rendition in the same place.** Maps and graphs on record pages are build-time SVG with a
  short description and a table or list long description (K12a [Q043]). JavaScript may enhance that box in place; it never
  replaces an empty box (fixes the CLS root cause, NEW-3).
- **I-3 Every citable state is a URL.** Explore state (release, query, facets, focus, viewport, graph scope) is in the query
  string under `sig.workspace-state/2` (§4.5), and every such URL has a no-JS equivalent (§4.4).
- **I-4 JS is budgeted by page type** (§4.3), measured in CI on real-sized data, and raised only with a measured report and
  an ADR note (extends ADR-134 revisit trigger (d)).
- **I-5 Least power.** Use HTML first, then CSS, then a framework-free custom element, and only then a Preact island (§4.6).
- **I-6 No third-party origins at runtime.** Tiles, glyphs, geocoding and search are served by SIG. A strict CSP enforces
  this (§4.8).
- **I-7 Record and print namespaces (T0) contain no `<script>` element at all.**
- **I-8 WCAG 2.2 AA in both states.** Every page passes with JS on and with JS off; reduced motion is honoured; every
  feature drawn on a canvas is also reachable as a focusable list item (§4.9).
- **I-9 Multi-page, not single-page.** Navigation between pages is a normal page load. There is no client router; ADR-134's
  `history` adapter stays the only history-aware code.
- **I-10 Release-pinned data only.** Explore surfaces read the release they name. Live-spine `/v1/*` routes are never the
  data source of a public page (G3 RM-7, REL-05).

### 4.2 Page types and routes (the registry)

One file, `web/src/lib/page-types.ts`, maps route patterns to types. A build hook fails on any built HTML route that
matches no pattern, so a new page is classified before it ships (fixes NEW-4).

| type | route patterns (initial registry) |
|---|---|
| **T0 record & print** | `/r/**` (P32.13 release records, rendered by `release_pages.py`); `/**/print/`; `/s/<pub>/**/print/`; `/dispute/`; `/intake/**`; API `format=html` pages; 404/410 tombstones; `/releases/<pub>/data/**` listings |
| **T1 content** | `/`; `/dossier/**`; `/entity/**` (latest-view entity pages, K2); `/sources/**` and `/data-freshness/**` (K9/K10); `/research-queue/**`, `/task/**` (K11); `/watch/**` (K7); `/evidence/**` (K8); `/research-dossier/**`; `/releases/`; `/data/**`, `/status/**` (J3); `/methodology/`, `/coverage-metrics/`, `/corrections/`, `/contribution-back/`, `/editorial-standards/`, `/style-guide/`, `/visual-language/`, `/about/**` (K14); the same routes under `/s/<pub>/` and `/v/<pub>/` |
| **T2 explore** | `/map/`; `/explore/` (graph; `/network/` becomes a redirect or a T1 page); `/search/`; the same under `/s/<pub>/` |
| **T3 tools** | `/curate/**` (ADR-068; never published — the publish strip F-02 stays) |

A "source explorer" is **not** a fourth T2 surface: the sources table (T1 with a ≤ 15 KiB enhancement, K9 §6.2) plus
`kind=source` facets in `/search/` cover it.

### 4.3 Budgets per page type

Measured as `budget.spec.ts` measures today (gzip of every `/_astro/` asset the page fetches) plus Lighthouse on a
**real-sized** build. "Initial" = before any user action. KiB = 1,024 B.

| | T0 | T1 | T2 map | T2 graph | T2 search |
|---|---|---|---|---|---|
| Executable JS, initial | **0** | **≤ 20 KiB**, `type=module`, never render-blocking | **≤ 360 KiB** | **≤ 120 KiB** | **≤ 60 KiB** |
| JS after a user action | — | ≤ 40 KiB per enhancement; T2 code only after an explicit "open the interactive view" action | ≤ 60 KiB | ≤ 60 KiB | ≤ 40 KiB |
| HTML document (transferred) | ≤ 150 KiB | ≤ 150 KiB | ≤ 100 KiB | ≤ 100 KiB | ≤ 100 KiB |
| Total initial transfer (excl. tiles/data) | ≤ 150 KiB | ≤ 170 KiB | ≤ 450 KiB | ≤ 250 KiB | ≤ 180 KiB |
| Data per interaction | — | ≤ 200 KiB (e.g. K11's place shard) | first view tiles + glyphs ≤ 1.5 MiB; ≤ 500 KiB per pan/zoom | ≤ 200 KiB per overview or expansion | ≤ 50 KiB per keystroke shard; ≤ 40 KiB per result page |
| Lighthouse mobile performance (error) | ≥ 0.95 | ≥ 0.95 | ≥ 0.75 | ≥ 0.90 | ≥ 0.95 |
| Accessibility score (error) | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 |
| LCP (simulated mobile) | ≤ 1.5 s | ≤ 1.5 s | ≤ 2.5 s | ≤ 2.0 s | ≤ 1.5 s |
| CLS | ≤ 0.02 | ≤ 0.02 | ≤ 0.05 | ≤ 0.05 | ≤ 0.02 |
| TBT (lab proxy for INP) | 0 | ≤ 50 ms | ≤ 350 ms | ≤ 200 ms | ≤ 100 ms |
| Interaction latency (Playwright, 4× CPU throttle) | — | ≤ 100 ms (sort 500 rows) | ≤ 200 ms (open a feature) | ≤ 200 ms (expand) | ≤ 100 ms (keystroke → suggestions) |

**Where the numbers come from.** T0/T1 keep today's 150 KiB document budget (static pages already use 7–24 KB, C2 §6.2).
T1's 20 KiB is a quarter of the markup-heavy 75 KiB budget (K12a [Q085]) and covers K9's ≤ 15 KiB table module. The map
figure is MapLibre's ESM split (≈ 300 KB, §2.1) + PMTiles 7 + Preact 5 + basemap style 7 + ≤ 40 app, about the "JS-heavy"
365 KiB budget, and 28 % below today's 497 KB. The graph figure is sigma + graphology (38–50 KB) + Preact + ≤ 60 app. The
search figure is Preact + MiniSearch (≈ 11 KB) + ≤ 45 app. T2 map performance moves from **warn 0.5** to **error 0.75**
(production measured 0.86 mobile with today's heavier bundle, C2).

### 4.4 The no-JS fallback rule

**Rule.** For every page and every URL state, a reader with JavaScript off must get either (1) the same facts, server-rendered
at that URL, or (2) a visible notice that names what the link encodes and links to the static page(s) that hold the same
facts. Option (2) is allowed only on T2. A `<noscript>` notice is enough; it is not a script. An island never renders into
an empty box above the fallback (NEW-3).

| surface | no-JS equivalent (required) | JS enhancement (allowed) |
|---|---|---|
| Dossier (T1) | full dossier; static SVG map of the jurisdiction (boundary, context, bins/points at published precision, attribution) and static SVG network (linked nodes); tables | sortable tables; "open the interactive map/graph here" (facade loads T2 code on click); scoped typeahead |
| Entity page (T1) | all claims with sources, dates, contradictions; typed relationship tables (K12a ENT-3); static SVG 1-hop graph whose nodes are `<a href>` to entity pages; precomputed "who can access" lists | table sort/filter; hover highlight; "expand in explorer" link |
| Sources table and pages (T1) | pre-rendered sort and single-facet routes (J3/K9); per-source pages with static SVG run charts | ≤ 15 KiB multi-facet filter, instant text filter, "download this view" (K9 §6.2) |
| Research queue (T1) | paginated routes by place, type, role (K11) | place typeahead + multi-select over a ≤ 200 KiB shard (K11 §5) |
| `/map/` (T2) | build-time SVG overview (national bins, jurisdiction indicators, attribution); a place form (GET) resolving to a dossier or a paginated site list; per-jurisdiction site lists (≤ 100 rows per page); an API "sites in this area" HTML list for any `at=` viewport | MapLibre over basemap + overlays; filters; clustering from tiles; a synchronized "features in view" list |
| `/explore/` (T2) | overview graphs as static SVG + adjacency tables; entity pages; precomputed path answers as hop lists with per-hop evidence (SIG-UI-025) | sigma canvas; expand, filter by edge kind, path highlight |
| `/search/` (T2) | `<form method=get>` to the release-pinned API; server-rendered typed results with facets and pagination; browse index when the API is down | typeahead (shards), instant facets, keyboard combobox |

### 4.5 URL-state contract: `sig.workspace-state/2`

A superset of `/1` (ADR-134); every `v=1` link keeps working. Fields at their defaults are omitted.

```
common   v=2 &release=p-<sha256> &view=list|map|graph|table|search
         &collection=<c>… (bare `collection=` = none) &q= &kind= &jurisdiction= &technology= &source= &location=
         &focus=<record_key> &page=<n> &sort=<col> &dir=asc|desc
map      &at=<z>/<lat>/<lon>   z to 0.1; lat/lon rounded to the precision the zoom supports and never finer than the
                                published tier (§19.4); &layers=<id>… &basemap=0|1
graph    &overview=<id> | &focus=<record_key> &hops=1|2 &edge=<kind>… (the three access kinds stay separate, SIG-UI-024)
         &expand=<record_key>… (≤ 10)
search   &type=<entity type>… plus the common facets
```

- **Cite this view** produces the snapshot-pinned form `/s/<pub>/<surface>/?v=2&…` (G3 §5.3, J3 §8.1) plus the static
  equivalent link. A query string never pretends to pin anything on the server (SIG-FIND-002): a T2 page opened with state
  and no JS says so and links the equivalent (§4.4).
- **Crawl hygiene.** Parameterized T2 URLs carry `<meta name="robots" content="noindex,follow">` and a canonical link to the
  base surface; records (T0/T1) are what the sitemap lists (F-118).
- **Precision.** Viewport rounding is a Part VIII-adjacent control: a URL must not carry more location precision than the
  view needs (§19.4). This closes ADR-134 revisit trigger (a) deliberately.

### 4.6 The least-power ladder and the component kit

1. **HTML:** links, GET forms, `<details>`, tables, anchored headings, `popover` + `popovertarget` for legends and
   definitions.
2. **CSS:** `:has()` checkbox filters (for example edge-kind toggles on a static SVG), `:target`, print CSS, cross-document
   view transitions (`@view-transition`, disabled under `prefers-reduced-motion`).
3. **Framework-free custom elements** that upgrade server-rendered markup (T1): `<sig-table>` (sort, filter, "download this
   view"), `<sig-typeahead>` (APG combobox over static shards, K12a SRC-5), `<sig-cite>` (copy citation), `<sig-activate>`
   (a facade that loads T2 code only on click). If the module fails, the markup is unchanged.
4. **Preact islands** (T2 only), SSR-rendered or mounted into a reserved, fixed-size box that already holds the static
   rendition (`client:visible`/`client:idle`; `client:only` is banned on public pages).

### 4.7 Dependency policy

- **Allow-list.** Browser-shipped runtime dependencies are listed in `web/runtime-deps.json`; CI fails on any other package
  in a public bundle. Adding one needs an ADR note with a measured size.
- **Hygiene (keep):** exact pins, ≥ 7 days since publication (ADR-091), OSI licences checked in CI (SIG-UI-039,
  `check:licenses`), `npm ci` from the lockfile.

| decision | package (measured gzip) | use |
|---|---|---|
| **Adopt (keep)** | `maplibre-gl` 6.9.0 + `pmtiles` 4.5.0 (≈ 300 KB with the ESM split) | T2 map |
| **Adopt** | `@protomaps/basemaps` 5.7.2 (6.7 KB) + a self-hosted Protomaps PMTiles basemap (ODbL data, CC0 styles, BSD-3 code, K12a [Q009], [Q018]) | basemap style; K1 chooses zooms and region |
| **Adopt** | `preact` 10.x (5.4 KB) via `@astrojs/preact` | the only island runtime; replaces React (65.7 KB) |
| **Adopt** | `sigma` 3.x + `graphology` (37.8 KB); layout, communities and paths computed at build time in Python where possible | T2 explorer |
| **Adopt** | `minisearch` 7.x (5.9 KB) | fuzzy/prefix matching within a typeahead shard |
| Build-time only | tippecanoe (pinned, ADR-118) with clustering; `pmtiles extract`; Python layout/graph algorithms | tiles, clustering, overview layouts |
| Evaluate if needed | `graphology-shortest-path` (19.1 KB with graphology) for client paths over a bounded subgraph; `accessible-autocomplete` (20.0 KB) as the combobox reference; Orama (21.7 KB) or FlexSearch (17.2 KB) if MiniSearch falls short | K2/K3 |
| **Reject by default** | cytoscape (141 KB, 3.7× sigma); cosmos.gl (WebGL 2, iOS/Android gaps, K12a [Q033]); Leaflet (a second map stack); supercluster for the national layer (clustering belongs in tiles; 225k points ≈ 34 MB GeoJSON, K12a §8); sql.js / sql.js-httpvfs (322 KB WASM); Pagefind for entity pages (reported failure at 250–300k pages, K12a [Q054]); React on public pages | — |
| **Reject at runtime** | third-party tiles or geocoders (Stadia/MapTiler free tiers are non-commercial; OSMF tile and Nominatim policies forbid this use, K12a §2.3–2.4); analytics; web fonts or scripts from CDNs | — |
| Server-side, only on demonstrated need | Typesense (GPL-3.0 — licence review) or Meilisearch (MIT CE) | SIG-UI-040; a new ADR |

### 4.8 CSP, security and privacy

- **Content-Security-Policy on every public response** (none today, F-118): Astro's `security.csp` hashes the island
  bootstrap and inline styles; nginx adds the header-only directives. Target policy:
  - T0: `default-src 'none'; style-src 'self'; img-src 'self' data:; font-src 'self'; form-action 'self';
    base-uri 'none'; frame-ancestors 'none'` (the intake receiver already sends `default-src 'none'`, `api/src/api/intake.py:626`).
  - T1/T2: `default-src 'self'; script-src 'self' <hashes>; style-src 'self' <hashes>; img-src 'self' data: blob:;
    connect-src 'self' <SIG tile origin>; worker-src 'self' blob:; font-src 'self'; object-src 'none'; base-uri 'none';
    form-action 'self'; frame-ancestors 'none'` — no `unsafe-inline`, no `unsafe-eval`. `style=""` attributes move to
    classes (or the ticket records a narrow `style-src-attr` exception).
- **Untrusted labels.** Every label comes from third-party data (OSM tags, portal names). Client code renders text only:
  no `innerHTML`, no `dangerouslySetInnerHTML`, no MapLibre `setHTML`; a CI grep fails on them. Trusted Types is evaluated
  in the CSP ticket (MapLibre compatibility unverified).
- **Privacy.** No analytics, cookies or stored research history (ADR-134 kept). "Near me" uses the place form or an
  explicit geolocation action processed only in the browser; no address geocoding on the server (K12a §2.4 note on Part VIII).
- **Other headers:** `Strict-Transport-Security` (absent today, F-118), `Referrer-Policy` (present), `X-Content-Type-Options`
  (present), `Permissions-Policy` denying everything except `geolocation=(self)` on `/map/`.

### 4.9 Accessibility contract (WCAG 2.2 AA, both states)

- **Text alternatives (1.1.1):** every visual has a short description and a table or list long description (K12a [Q043]).
- **Keyboard (2.1.1/2.1.2):** MapLibre pans and zooms by keyboard but features are not focusable (K12a A11Y-5); the map
  therefore keeps a synchronized "features in view" list (≤ 50 items, each a link or button); the graph keeps a node panel
  listing the selected node's neighbours as buttons. Escape closes popups and returns focus (fails today, C2 §6.3).
- **Dragging movements (2.5.7):** panning a map or a graph must have a single-pointer alternative (pan buttons, click-to-
  centre, or the list).
- **Focus not obscured (2.4.11):** attribution blocks and bottom sheets must not cover focused controls (C2 F-123,
  K12b A7 — the attribution covers the bottom 100 px of the 384 px canvas).
- **Target size (2.5.8):** ≥ 24 × 24 CSS px for map and graph controls.
- **Content on hover or focus (1.4.13):** popups are dismissible, hoverable and persistent.
- **Status messages (4.1.3):** result counts and "selection cleared" notes announce via `role=status` (already done).
- **Reflow (1.4.10):** 320 px without horizontal scroll (fails today, F-116, F-167).
- **Label in name (2.5.3):** fails on every page today (F-116); the component kit fixes it once.
- **Motion:** `prefers-reduced-motion` → no `flyTo`, no animated force layouts (layouts are precomputed), no view
  transitions.
- **Colour (1.4.1, SIG-UI-005):** symbols carry a second channel; map symbols keep ≥ 3:1 contrast against the basemap
  (1.4.11).

### 4.10 The design-center persona and print

The advocate's dossier stays T1 on screen and T0 in print. What changes is that the printed dossier gains visuals: the
build-time SVG map and network print with their captions, attribution (SIG-GEO-013) and the as-of and permalink on every page
(SIG-UI-013). Print CSS hides every enhancement control (`[data-enhancement]`). No canvas is ever printed (a WebGL canvas
prints blank unless its drawing buffer is preserved — inference). A T2 "Print this view" prints the static rendition of the
current state plus the "features in view" list; K1 decides whether that rendition is client-generated or a server list.

### 4.11 Crawling, archiving and citation

T0 and T1 pages are complete for any fetcher, archive or agent. T2 surfaces archive as their first paint plus tables.
The `/s/<pub>/` snapshot includes the content-hashed assets, so a snapshot's T2 page keeps working on SIG's own host. New
citations are path-pinned (G3); explore citations use the snapshot form (§4.5).

### 4.12 Testing and CI gates (concrete changes)

1. **Registry + discovery.** `web/src/lib/page-types.ts`; an `astro:build:done` hook walks `dist/**/*.html` and fails on an
   unclassified route. Every e2e sweep iterates the discovered routes, not a hand list (NEW-4).
2. **`web/tests/e2e/script-policy.spec.ts`** replaces `islands.spec.ts:13-28`. T0: zero `<script` elements. T1: only
   `type="module"` scripts whose `src` is an allow-listed entry, plus hashed Astro bootstrap; `application/ld+json` data
   blocks allowed where J3's D-J3-7 chooses (data, not code; counted in the document budget). All types: no `on*=`
   attributes and no `javascript:` URLs.
3. **`nojs-parity.spec.ts`.** T1: the text of `main` with JS off equals the text with JS on, minus `[data-enhancement]`.
   T2: the named equivalents in §4.4 exist and resolve; a stateful URL opened with JS off shows the notice.
4. **`web/tests/e2e/page-budgets.json`** (`sig.page-budgets/1`) supersedes `island-budgets.json`; `budget.spec.ts` measures
   every type, gzip and brotli, before and after one scripted interaction per surface.
5. **`lighthouserc.json` generated** from the registry and budgets (`web/scripts/gen-lhci.mjs`, with a test that the
   committed file is in sync). URLs cover at least one route per type, including `/releases/`, a research dossier, an entity
   page, `/sources/`, a print page and a T0 record. Performance assertions become **errors** per type.
6. **Real-sized build in CI.** A deterministic synthetic national fixture (≥ 232k sites, ≥ 5k agencies, ≥ 400k sharing
   edges) with **no real agency or vendor names** (F-173), plus G3's V11 on the real release before promotion
   (C4 DR-C4-13, SIG-FIND-005).
7. **Accessibility.** axe (WCAG 2.2 AA) on every discovered route in both Playwright projects and on named interaction
   states (popup open, node focused, combobox expanded); keyboard journeys per T2 surface; a `reducedMotion: 'reduce'`
   project.
8. **CSP.** e2e runs behind the real headers and fails on any `securitypolicyviolation` event.
9. **Print.** `page.pdf` per dossier template: SVG visuals present, attribution present, as-of and permalink on every page.
10. **Links.** A no-JS crawl of `dist` finds 0 broken internal links (F-147; K12b NEW-7's 5,290 dead gap links).
11. **Dependencies.** `check:licenses` + the runtime allow-list + a bundle-content check (no React in public bundles once
    migrated).

---

## 5. Data serving: static files, tiles and a small API

### 5.1 What is served how

| data product | serving | size (measured or inferred) | notes |
|---|---|---|---|
| Record pages + JSON twins (entities, claims, evidence) | static, `r/<pub>/` (P32.13) | 2.0 GB, 475,112 files today | T0; the cost driver (§5.3) |
| Latest-view and snapshot pages (Astro) | static, `v/<pub>/`, `s/<pub>/` | 60–150 MB, 3–5k objects (J3 §8.1, inference) | T1/T2 |
| 1-hop neighbourhood per entity | **embedded in the entity page** and its JSON twin | ≈ 3 KB gzip per 50-node ego (§2.4) | no new objects; expansion fetches the neighbour's JSON twin — no API |
| Large egos (e.g. a Flock agency with ≈ 517 partners) | same, grouped by state and type with counts | ≈ 10–30 KB gzip (inference from §2.4) | SIG-UI-021: aggregated, never a hairball |
| Overview graphs (vendor ↔ agency, sharing by state, funding, governance) | static JSON + static SVG per release | ≤ 176 KB gzip per 3k-node view; ~10–30 views → ≤ 5 MB | layout at build time, deterministic |
| Access-path closures ("who can access what") | static, per entity (in page + twin) | K2 measures | computed at build; per-hop evidence (SIG-UI-025) |
| Typeahead shards (entities, places, sources, dossiers) | static per release **per compartment** (ADR-118 separation) | today ≈ 880 KB gzip over 618 shards (p95 4.9 KB); + a gazetteer (SIG jurisdictions + a GeoNames subset, CC BY 4.0, K12a [Q020]) | derived labels (NEW-1) enlarge it; K3 sizes |
| Static map renditions (per dossier, national overview) | static SVG, build time | ≈ 20–80 KB each × ~60 (inference) | printable, accessible |
| Overlay tiles | static PMTiles, one per compartment (SIG-GEO-012) | 42.5 MB | clustered at build (tippecanoe) |
| Basemap | static PMTiles (Protomaps), its own archive, never merged with SIG data | planet z0–15 ≈ 120 GB; ≈ 60 GB for z0–14 or less for regions (K12a §8, inference) | ODbL attribution in every context (SIG-GEO-013); K1 decides zooms and host |
| **Full-text search** (typed results, facets, trigram substring, exact ids) | **API**, reading the per-release immutable SQLite FTS5 (ADR-133, P32.14) | FTS5 over 232,625 records: 37.7 MB (`unicode61`), 96.6 MB (`trigram`) | HTML + JSON from one endpoint; the no-JS form posts here |
| **Sites in a viewport or area** (the map's list) | **API**, new release-pinned route (bbox, ≤ 100 per page, HTML + JSON) | small | also the no-JS equivalent of any `at=` |
| Operational freshness, run logs | status lane (J3 TX-07) | 2–5 MB per run | two clocks, both labelled (G3 RM-7) |

**Claims are never shipped to the browser.** Entity pages render their claims server-side; bulk statements are downloads
(J3). Client payloads therefore scale with what a view shows, not with the 2.42 M claims.

### 5.2 API needs (all release-pinned; none new except bbox)

1. Extend `/v1/releases/{pub}/compartments/{c}/search` (P32.14): trigram tokenizer, bm25 weights, typed results with
   derived labels, facets with counts, `format=html` for the no-JS form, a cross-compartment result page that keeps licences
   separate per result group.
2. Add `/v1/releases/{pub}/compartments/{c}/sites?bbox=…&page=` (HTML + JSON).
3. Keep live-spine `/v1/*` for developers, labelled "live, not a citation"; public pages never read it (I-10). K12b F-23's
   "surface what the API already serves" is right for *data*, but through release-built pages, not client fetches of live
   routes.
4. When the API is down, T2 search degrades to the typeahead shards and the static browse index (§46.5); the map list
   degrades to the per-jurisdiction static lists.

### 5.3 Cost (monthly; **inference** from cited unit prices)

Unit prices: GCS internet egress ≈ $0.12/GB (J4, secondary source); LB data processed ≈ $0.008/GB (G1 §3.8); R2 egress $0,
storage $0.015/GB-month, reads $0.36 per million beyond 10 M/month (K12a [Q089]); GCS storage ≈ $0.020/GB-month (G1);
`sig-api` min-instances 1 ≈ $7–10/month already paid (G1 §3.8). Assumed first-visit map session ≈ 1.9 MB (≈ 0.4 MB assets +
≤ 1.5 MiB tiles), cached assets thereafter.

| item | 10k map sessions/month | 100k map sessions/month |
|---|---|---|
| Map assets + tiles via GCS + LB | ≈ 19 GB → ≈ $2.4 | ≈ 190 GB → ≈ $24 |
| …via R2 (zero egress) | ≈ $0 (reads inside the free tier) | ≈ $0 (≈ 5 M reads) |
| Basemap storage (planet, z0–15) | R2 ≈ $1.8 · GCS ≈ $2.4 | same |
| Search API | inside the existing instance | + ≈ $1–2 per million queries (30 ms × G1's vCPU prices; request fees not re-read) |
| Extra objects per release (shards, overviews, SVGs: ≈ 3–5k) | ≈ $0.02 per release | same |
| **Incremental total** | **≈ $5–15** | **≈ $25–40 on GCS; ≈ $5–10 on R2** |

Everything stays far inside U-008's $300/month. The cost to watch is not K0's: per-release object writes grow with entity
count (≈ $2.4 per full upload at 475k files; ≈ $10 at 2M files, linear inference) and belong to G3's cadence and to an
incremental-upload design.

### 5.4 Freshness

Explore surfaces are as fresh as the release they name (G3 cadence: monthly plus triggers). That is a feature: what a
journalist explores is what they can cite. Operational metrics that must be fresher live on the status lane with their own
clock (J3 T-7). No public page mixes the two.

---

## 6. ADR draft (agent-drafted; T1 assigns the number)

> **ADR-NNN — HTML-first page types: zero-JS records and print, budgeted enhancement on content pages, app-like explore
> surfaces with URL state**
>
> - **Status:** Proposed (K0, 2026-09-30). Supersedes the named-island rule of **ADR-091 §3–4** and **ADR-097 §2–3 and §6**
>   (the allowance "exactly three" and "every other public page keeps script bytes 0"). Extends **ADR-134**
>   (`sig.workspace-state/2`; viewport in the URL; per-type budgets). Leaves **ADR-068** (`/curate/**`) unchanged.
>   Interacts with the K1 basemap ADR (reversing Round-9 Q8) and G3's release ADRs (snapshot citation).
> - **Related:** SIG-UI-002/013/021/022/035–041/047/049/050, SIG-GEO-012/013, SIG-FIND-002/004/005; U-003, U-005, U-007, U-008.
>
> **Context.** SIG's public surface is zero-JS except three islands. The operator asks for a site where journalists can
> "really truly explore the knowledge graph … interactively, always with full explicit transparent evidence/lineage" (U-005),
> with a real map, a navigable graph and flexible search (U-003). The review record shows the static pages are fast,
> accessible and printable (C2 §6.2, Lighthouse 1.0) while the three islands carry every performance and layout-shift
> failure and the abandoned mobile task (F-115, F-123, F-171); the no-JS map fallback grew to a 3.46 MB page. Most of the operator's asks are blocked by
> labels, data routing and information architecture rather than by the rule; the rule's own costs are no-JS filtering
> combinatorics, no embedded visuals, no shareable map view and an allow-list that needs an ADR per enhancement and fails open
> for new pages. Prior art: content sites must work HTML-only (GOV.UK), bots need server-rendered HTML (Google), JS-first peers
> are unreadable to fetchers, and knowledge-graph products put typed tables on entity pages with bounded graphs beside them
> (K12a).
>
> **Decision.**
> 1. Every public route is classified in a page-type registry (`web/src/lib/page-types.ts`): **T0 record & print**, **T1
>    content**, **T2 explore**, **T3 tools**. An unclassified built route fails the build.
> 2. **T0** pages contain no `<script>` element. **T1** pages render every fact with JS off and may load approved
>    framework-free enhancement elements within ≤ 20 KiB gzip initial JS, never render-blocking; heavy code loads only after an
>    explicit user action. **T2** surfaces — `/map/`, `/explore/`, `/search/` — may be applications within per-surface budgets
>    (map ≤ 360 KiB, graph ≤ 120 KiB, search ≤ 60 KiB gzip initial JS), with a server-rendered first paint in a reserved box
>    and a complete no-JS equivalent (tables, lists, GET forms, static SVG).
> 3. Budgets (JS, document, total, per-interaction data, Lighthouse score, LCP, CLS, TBT) live in `page-budgets.json`, are
>    measured in CI on a real-sized synthetic build and on the real release before promotion, and rise only with a measured
>    report and an amendment to this ADR.
> 4. Every citable interactive state is in the URL under `sig.workspace-state/2` (adds the rounded map viewport, graph scope
>    and table sort); "cite this view" yields the release-snapshot URL; a stateful URL opened without JS says so and links
>    its static equivalent. No client router; ADR-134's adapter stays the only history-aware code.
> 5. Every visualization has a build-time static rendition (SVG + table or list) in the place it appears; JS enhances that
>    box in place. `client:only` is not used on public pages.
> 6. Public islands use **Preact**; React leaves the public bundles. T1 enhancements are framework-free custom elements.
> 7. Browser runtime dependencies are allow-listed (MapLibre GL, PMTiles, Protomaps basemap styles, Preact, sigma, graphology,
>    MiniSearch); anything else needs an amendment with a measured size. OSI licences, exact pins and the ≥ 7-day rule stay.
> 8. No third-party origins at runtime: tiles, basemap, glyphs, gazetteer and search are served by SIG; a strict CSP (hashes,
>    no `unsafe-inline`/`unsafe-eval`) and HSTS are sent on every public response.
> 9. WCAG 2.2 AA holds in both JS states; canvas content is reachable through focusable lists; reduced motion is honoured.
> 10. Explore surfaces read only release-pinned data (static files, PMTiles, release-namespaced API routes); live-spine routes
>     never feed a public page.
>
> **Consequences.** Positive: the operator's explore journeys become possible without giving up the printable, citable,
> archivable record; embedded dossier visuals become legal and print; filtering stops depending on pre-rendered route
> products; enforcement becomes fail-closed. Negative: more code to maintain (a component kit and three apps); JS-on/JS-off
> parity tests on every T1 page; a React → Preact migration; a CSP that constrains inline styles; CI needs a real-sized build
> (longer runs). Neutral: the map's weight falls (≈ 497 → ≤ 360 KiB gzip) once the worker duplication is removed.
>
> **Alternatives considered.** (a) Keep the named-island set and add islands by ADR — rejected: cannot serve embedded
> visuals or multi-facet filtering, and the allow-list fails open. (b) Progressive enhancement everywhere without app
> surfaces — rejected for the map and graph, whose core interaction is scripted. (d) Full SPA — rejected (ADR-091 C;
> archivability, citation, crawlability, print; a runtime service). Also rejected: cytoscape (3.7× the size of sigma);
> client-side SQLite search (322 KB WASM); Pagefind for 10⁵–10⁶ entity pages; third-party tile or geocoding services;
> live-spine data in explore surfaces; a national node-link "hairball" (SIG-UI-021).
>
> **Revisit trigger.** (1) A T2 surface needs more than 1.25× its budget, or misses its Lighthouse floor on the real release
> for two consecutive releases. (2) A requirement needs non-release (live) data on a public page. (3) A graph view needs more
> than ~3,000 labelled nodes, or a renderer that requires WebGL 2 only. (4) Search needs capabilities the API FTS5 path and
> the shards cannot give (measured failure), or search cost exceeds $50/month. (5) A runtime dependency needs
> `unsafe-eval`/`unsafe-inline` or a third-party origin. (6) The operator asks for accounts, personalization or an SPA — a new
> ADR superseding this one and SIG-UI-036/037.

---

## 7. Spec amendments (for T1; agent-drafted text) and guidance rewrites

| id | today (summary) | proposed amendment |
|---|---|---|
| **SIG-UI-036** (SHOULD) | zero-JS-by-default framework with opt-in islands | Keep the rationale. Replace "opt-in interactive islands" with "opt-in enhancement governed by the page-type registry and budgets of §40 (ADR-NNN); record and print pages ship no client JavaScript." |
| **SIG-UI-037** (MUST) | core content usable without JS; map → table, graph → list | Add: "Every visualization MUST have a static rendition and a table or list equivalent in the same place, and the JavaScript-off rendering of a content page MUST contain every fact its JavaScript-on rendering shows." |
| **SIG-UI-038** (MUST) | self-hosted tiles; zero-JS static map is the conforming default | Add the basemap: "The map SHOULD draw a self-hosted OpenStreetMap-derived basemap served as its own PMTiles archive, never merged with SIG compartments, from a SIG-controlled origin." Replace "conforming default" with "the build-time static rendition + tables are the required no-JS equivalent; the interactive renderer is a T2 surface." Pairs with the K1 ADR reversing Q8. |
| **SIG-UI-041** (MUST) | budgets enforced in CI | Add: "Budgets are declared per page type (JS, document, total, per-interaction data, LCP, CLS, TBT, Lighthouse score), measured on a real-sized build in CI and on each release before promotion; an unclassified route fails the build." |
| **SIG-UI-047** (MAY) | interactive map island, realised at P27 | Annotate: superseded by the T2 map surface of ADR-NNN. |
| **SIG-UI-050** (MUST) | exactly three named islands; every other page zero JS; a fourth island needs an ADR | Rewrite: "Every public route MUST be classified as T0 record/print, T1 content, T2 explore or T3 tool. T0 MUST contain no script element. T1 MUST render every fact without JavaScript and MAY load approved enhancement elements within its budget. T2 MUST encode citable state in the URL (`sig.workspace-state/2`), paint a server-rendered first view in a reserved box, and link a complete no-JavaScript equivalent. Adding a T2 surface, a runtime dependency, or raising a budget changes ADR-NNN, never ad hoc." |
| **SIG-UI-021/022** (MUST) | no national hairball; default ego network, "not a global graph" | Keep the ban on a national node-link hairball. Add: "Aggregated overview graphs (entity type × jurisdiction, communities, or matrix/arc views) of at most a few thousand nodes MAY serve as the global entry point; each carries the ER-quality disclosure (SIG-UI-023) and drills down to entity egos." |
| **SIG-UI-039** (MUST) | OSI dependencies checked in CI | Add: "Browser-shipped runtime dependencies MUST be on a CI-checked allow-list." |
| **SIG-UI-040** (SHOULD) | start with Postgres FTS | Amend to the landed design: "Search SHOULD use the release-pinned per-compartment SQLite FTS5 index over the API (ADR-133) plus static per-compartment typeahead shards; a dedicated engine only on measured need." |
| **SIG-UI-013** (MUST) | print path with as-of and permalink per page | Add: "Embedded visualizations print as their static renditions with basemap attribution." |
| **SIG-FIND-004** | "…the no-basemap decision remain[s] in force" | Strike that clause (K1 ADR); add the v2 fields (viewport, graph scope, sort). |
| **SIG-FIND-005** | "150 KiB/zero-script budget … per-island budgets" | Replace with the page-type budgets; keep "real-sized release fixtures … never hidden by testing only demo data". |
| **New SIG-UI-05x (draft)** | — | "Every public response MUST carry a Content-Security-Policy without `unsafe-inline` or `unsafe-eval` and MUST NOT load scripts, styles, fonts, tiles or data from third-party origins." |
| **New SIG-UI-05y (draft)** | — | "Every state a user can cite on an explore surface MUST be reproducible from its URL together with a named release; the page MUST NOT imply that a query string pins data on the server." |

### 7.1 `AGENTS.md` gotcha 6 — replacement text (agent-drafted)

> 6. **Public pages are HTML-first; client JS is budgeted by page type.** Every public route is classified in
>    `web/src/lib/page-types.ts` — an unclassified route fails the build. **T0 record & print** (`/r/**`, every `…/print/`,
>    `/dispute/`, `/intake/**`) ships **no `<script>`**. **T1 content** (dossiers, entities, sources, queue, methodology, …)
>    must show every fact with JS off and may load only approved enhancement elements (≤ 20 KiB gzip initial, never
>    render-blocking). **T2 explore** (`/map/`, `/explore/`, `/search/`) may be app-like but must keep URL state
>    (`sig.workspace-state/2`), a server-rendered first paint in a reserved box, and a no-JS equivalent (tables, lists, GET
>    forms, static SVG), within the per-surface budgets in `web/tests/e2e/page-budgets.json`. `/curate/**` stays ADR-068.
>    `script-policy.spec.ts`, `nojs-parity.spec.ts`, `budget.spec.ts` and the generated `lighthouserc.json` enforce this on
>    every built route. Raising a budget, adding a T2 surface or a browser runtime dependency needs an amendment to ADR-NNN.

### 7.2 `web/AGENTS.md` gotcha 1 — replacement text (agent-drafted)

> 1. **Page types, not islands.** Look up the route's type in `src/lib/page-types.ts` before adding any client code. T0:
>    none. T1: a framework-free custom element from `src/elements/` that upgrades existing markup (≤ 20 KiB gzip initial).
>    T2: a Preact island mounted with `client:visible`/`client:idle` into a reserved box that already holds the static
>    rendition — never `client:only`. Budgets: `tests/e2e/page-budgets.json`. Never render a data label with `innerHTML`.
>    Runtime dependencies: `runtime-deps.json` only.

---

## 8. Guidance each downstream K row must follow

**All K rows.** Classify every new route (§4.2). Put facts in HTML first; JS only by the ladder (§4.6). Every visual gets a
static rendition and a table. Every citable state goes in the URL (§4.5). Labels are derived and human-readable, never raw
UUIDs (82.8 % of published entities have no label, NEW-1). State the monthly cost of anything served (U-008). Name the
page type and budget in each ticket's acceptance.

**K1 — map (T2).**
- Keep MapLibre 6.9 + PMTiles; load MapLibre's ESM split so the shared chunk ships once (NEW-2); target ≤ 360 KiB gzip.
- Basemap: self-hosted Protomaps PMTiles as its own ODbL archive, own attribution, never merged with overlays; choose zooms
  (z0–14 vs z0–15) and region by cost; host on the zero-egress origin shared with J3 TX-11 if the operator picks R2
  (D-K0-4).
- Density at low zoom via tippecanoe clustering in the overlay tiles (K12a MAP-2); no client clustering of 225k points.
- Place search: static gazetteer typeahead (SIG jurisdictions + a GeoNames subset) and a GET form; never Nominatim from the
  client (K12a [Q017]).
- Popups link to feature and entity pages, render text only, close on Escape, and cite the feature (K12b NEW-6).
- A synchronized "features in view" list for keyboard and screen-reader users; single-pointer pan alternative (2.5.7);
  attribution must not cover controls (2.4.11).
- No-JS: build-time SVG overview, paginated per-jurisdiction lists (≤ 100 rows), the API bbox list; the page document
  ≤ 100 KiB (today 3.46 MB).
- `at=` in the URL with precision rounding; "cite this view" → snapshot URL.
- Measure on the real release: first-view tiles ≤ 1.5 MiB, Lighthouse mobile ≥ 0.75.

**K2 — graph and entity pages (T1 entity pages, T2 `/explore/`).**
- Entity pages first (K12a GRA-1, ENT-1…ENT-6): claims with sources, typed relationship tables with dates and sources,
  contradictions kept visible, persistent ids that redirect on merge.
- A static SVG 1-hop graph on each entity page with nodes as links (layout precomputed, deterministic). Zero JS.
- The "global graph" is a set of aggregated overview graphs (≤ ~3,000 nodes each; ≈ 176 KB gzip at 3k/10k) with static
  SVG + adjacency tables; `/explore/` renders them with sigma + graphology (≈ 38–50 KB gzip). Layout, communities and
  access-path closures are computed at build time in Python.
- Large egos (a Flock agency averages ≈ 517 share-list partners, I3) are grouped by state and type; the full list is a table.
- Expansion fetches neighbours' static JSON twins; no API. The three access kinds stay separate (SIG-UI-024); every
  statistic carries the ER-quality note (SIG-UI-023).
- Reduced motion: no animated layout. Keyboard: a node panel with neighbour buttons.

**K3 — search (T2 `/search/`, typeahead also in the site header as a T1 element).**
- One GET form → the release-pinned API FTS5 (add `trigram`, bm25 weights, typed results, facets with counts, `format=html`).
  This is the no-JS path and the JS path.
- Static per-compartment typeahead shards (2–3-character prefixes; today's labelled set p95 4.9 KB gzip, max 46 KB — split
  the outlier); MiniSearch for fuzzy matching inside a shard; APG combobox semantics (K12a SRC-5).
- Place-aware: "Canberra" and "Texas" resolve to jurisdictions and dossiers (C2 P6-T1).
- Keep compartments separate in results (ADR-118; per-group licence line).
- Degrade to shards + browse index when the API is down. No Pagefind for entities; Pagefind or the shards for the ~10³
  content pages is K3's call. Consider a Datasette-style faceted query page with CSV/JSON export of a result (K12a [Q087]) as
  the "query the data" journey (U-005), server-rendered.

**K6 — dossier visualizations (T1 on screen, T0 in print).**
- Build-time SVG map of the jurisdiction (boundary, a light context layer, bins or points at published precision, legend,
  OSM attribution when OSM-derived data is drawn) and a build-time SVG network (agencies, vendors, sharing, with linked
  nodes), each with a table.
- "Explore on the map / in the graph" links carry `jurisdiction=` in `sig.workspace-state/2`; optional in-place activation
  through `<sig-activate>` loads T2 code only on click.
- In-dossier search is a GET form scoped to the jurisdiction (no JS).
- Print: the SVGs print with captions and attribution; as-of and permalink on every page; no enhancement chrome.
- Candidate context layers need a licence check in K1/K6 (a public-domain boundary set or Protomaps extracts).

**K9/K10 — sources table and source pages (T1).**
- The §6.1 no-JS table stays canonical (K9). The ≤ 15 KiB `<sig-table>` enhancement (multi-facet filter, instant text
  filter, column chooser, "download this view") is allowed under T1 — this is the K0 decision K9 §6.2 was waiting for.
- `/sources/**` is named T1 in the registry (answers K9 §6.2's "the ADR must name `/sources/`").
- Per-source run and volume charts are build-time SVG with tables. Downloads are plain links. No new T2 surface.
- JSON-LD: K0 classifies `application/ld+json` as data, not code, so it is technically permitted on T1; whether to inline it
  stays J3's D-J3-7.

**K4, K5, K7, K8, K11, K14.** T1 by default: zero JS unless an element from the kit earns its place (K11's place-filter fits
T1's post-action data budget of ≤ 200 KiB). K14's design system provides the component kit's visual layer and the
reduced-motion and dark-mode tokens; view transitions are CSS-only.

**K13.** Adopt the registry as the site map's backbone: every page template names its type, budget, no-JS equivalent,
data contract and URL-state fields.

---

## 9. Draft requirements (provisional `SIG-UI-D` ids for K13/T1)

| id | requirement | acceptance |
|---|---|---|
| SIG-UI-D01 | Every built public route MUST match exactly one page-type pattern; unmatched routes fail the build. | build hook red on an injected unclassified page |
| SIG-UI-D02 | T0 routes MUST contain no `<script>` element. | `script-policy.spec.ts` over discovered T0 routes |
| SIG-UI-D03 | T1 routes MUST render identical `main` text with and without JavaScript (excluding `[data-enhancement]`). | `nojs-parity.spec.ts` on every T1 route |
| SIG-UI-D04 | Per-type budgets (§4.3) MUST hold on a real-sized synthetic build and on each release before promotion. | `budget.spec.ts`, generated `lighthouserc.json`, G3 V11 |
| SIG-UI-D05 | T2 state MUST round-trip through `sig.workspace-state/2`; Back/Forward restore it; a stateful URL without JS shows a notice and its equivalent. | workspace spec extended; no-JS spec |
| SIG-UI-D06 | Every visualization MUST have a static SVG rendition with a table/list equivalent in the same box; no `client:only` on public pages. | grep gate; CLS ≤ budget |
| SIG-UI-D07 | Canvas-drawn features MUST be reachable as focusable list items; popups close on Escape and return focus; pan has a single-pointer alternative. | keyboard journeys; axe on interaction states |
| SIG-UI-D08 | Every public response MUST carry a strict CSP and HSTS; no third-party runtime origins. | header probe; CSP-violation e2e |
| SIG-UI-D09 | Browser runtime dependencies MUST be on `runtime-deps.json`; public bundles MUST NOT include React after migration. | bundle-content check |
| SIG-UI-D10 | Printed dossiers MUST include their static visualizations with attribution. | `page.pdf` check |

---

## 10. Round-11 ticket outline (for K13/S2 sizing)

| key | ticket | size | depends |
|---|---|---|---|
| UXK0-1 | Page-type registry, route discovery hook, `script-policy.spec.ts`, `nojs-parity.spec.ts` (replaces the hand-listed sweeps) | M | — |
| UXK0-2 | `page-budgets.json`, generated `lighthouserc.json`, generalised `budget.spec.ts`, real-sized synthetic national fixture (no real names) | M | UXK0-1 |
| UXK0-3 | CSP + HSTS + Permissions-Policy: Astro `security.csp`, nginx templates (with G3 REL-03b), inline-style removal, CSP-violation e2e | M | G3 REL-03b |
| UXK0-4 | Enhancement kit: `<sig-table>`, `<sig-typeahead>`, `<sig-cite>`, `<sig-activate>`; print CSS; reduced-motion tokens | M | UXK0-1, K14 |
| UXK0-5 | `sig.workspace-state/2` + "cite this view" (snapshot form) + noindex/canonical rules | M | G3 `/s/<pub>/` |
| UXK0-6 | Preact migration of the three islands, `client:only` → reserved-box mounting, removal of `@astrojs/react` | M (or folded into K1–K3 rewrites) | UXK0-1 |
| UXK0-7 | ADR-NNN + spec_src amendments (§7) + `AGENTS.md`/`web/AGENTS.md` rewrites | S | GATE-P (T1) |

---

## 11. Operator decisions needed

| id | decision | recommendation |
|---|---|---|
| D-K0-1 | Adopt option (c) with (b)'s rules and the page-type rule (ADR-NNN) | **Yes** |
| D-K0-2 | Replace React with Preact on public surfaces | **Yes** (−60 KB gzip per T2 page; same API shape) |
| D-K0-3 | Put the rounded map viewport in URLs (`at=`) | **Yes**, with the precision rule (§4.5) |
| D-K0-4 | Host tiles and basemap on the zero-egress origin (R2) shared with J3 TX-11, or on GCS behind the LB | **R2** once J3 TX-11 exists; GCS acceptable below ~10k sessions/month (≈ $2–3) |
| D-K0-5 | Treat `application/ld+json` blocks as data (allowed on T1), leaving the "whether" to J3 D-J3-7 | **Yes** |
| D-K0-6 | The "global graph" is a set of aggregated overview graphs, not a raw national node-link graph | **Yes** (amends SIG-UI-021/022 wording) |

---

## 12. Risks

| id | risk | mitigation |
|---|---|---|
| R-1 | Budget creep: "just one more module" on T1 | generated budgets; raises need a measured report + ADR amendment |
| R-2 | No-JS equivalents rot because nobody looks at them | parity and no-JS specs over discovered routes; the no-JS project stays in `npm run check` |
| R-3 | Two modes (record vs explore) diverge in labels and numbers | one data seam (ADR-066), one label derivation, G3 V6 number truth on both |
| R-4 | Device support: MapLibre and sigma need WebGL (MapLibre may need WebGL 2 — unverified here) | no-JS equivalents cover failures; K1 verifies and states a browser matrix |
| R-5 | CSP breaks MapLibre or Astro | CSP ticket lands with an e2e violation check before headers go live |
| R-6 | Supply chain in the browser | allow-list, pins, ≥ 7-day rule, licence gate, no third-party origins |
| R-7 | Migration churn (Preact, registry, budgets) during feature work | land UXK0-1/2 first; fold the Preact move into K1–K3 rewrites |
| R-8 | Search depends on the API | shards + browse fallback; `sig-api` already min-instances 1 |
| R-9 | Graph growth (474k sharing edges) outpaces overview design | aggregation by construction; SIG-UI-021; K2 measures after resolution |
| R-10 | Real-sized CI builds are slow | a deterministic synthetic fixture sized once; full-release checks only at promotion |
| R-11 | Fixture data with real names leaks into public views (F-173) | the synthetic fixture uses invented names only |

---

## 13. New findings (`findings/incoming/K0.csv`)

| id | sev | title |
|---|---|---|
| NEW-1 | S2 | 82.8 % of published entities (192,536 of 232,625) have an empty label |
| NEW-2 | S3 | The map island ships MapLibre's shared chunk twice (worker copy ≈ 143 KB gzip) |
| NEW-3 | S2 | All three islands are `client:only` and hydrate into empty boxes above their fallbacks — the root cause of F-115's CLS and F-170's empty no-JS box |
| NEW-4 | S2 | The zero-JS and axe sweeps run over a hand-maintained route list; `/releases/` and `/research-dossier/**` (and every export-only route) are unchecked, so the contract fails open |

---

## 14. Limitations and command log

**Limitations.**
- No hands-on renderer benchmarks were run; frame-rate claims are K12a's vendor figures. Library sizes are minified bundles of
  a minimal import set; real imports differ by a few KB.
- Latency targets (LCP/TBT) are design targets, not measurements; C2/C4 measurements are the baseline.
- Basemap tile weight per session is an assumption (≤ 1.5 MiB budget); K1 must measure it.
- The typeahead measurement uses today's `label` field; derived labels (NEW-1) will enlarge the index.
- Cloud Run request fees and current per-vCPU service prices were not re-read this row; the search-cost line uses G1's unit
  prices and is labelled inference.
- MapLibre's WebGL 2 requirement and Trusted Types compatibility were not verified.
- The ESM-split saving (≈ 125 KB) is inferred from two measurements, not from a rebuilt bundle.

**Commands (all read-only; outputs in the session scratchpad, not durable; results quoted above).** Only C1, C3, C8,
C11 and C12 were individually stamped with `date -u`; the others ran in order between those stamps, so their window is
given, not an instant (P2).

| # | when (`date -u`) | command | result |
|---|---|---|---|
| C1 | 21:45:57Z | `git status`, `git branch --show-current` in the worktree | clean, `claude/next-phase-planning` |
| C2 | between C1 and C3 | `for f in web/dist/_astro/*.js; do wc -c; gzip -9c \| wc -c; brotli -c \| wc -c; done` | §2.2 |
| C3 | 21:50:51Z | `curl -sI -H 'Accept-Encoding: br, gzip' https://surveillancegraph.org/` and `/map/` | 200, `content-encoding: br`, no CSP, no HSTS |
| C4 | between C3 and C8 | duckdb over `docs/build/logs/next-phase/C3/bucket/parquet/*.parquet` (C3's hashed capture; e.g. `osm_physical.parquet` sha256 `860845d7e093…`) | 232,625 entities, 1 entity type |
| C5 | between C3 and C8 | Python: name-index JSON, prefix shards, SQLite FTS5 (`unicode61`, `trigram`) over the 232,625 records | §2.3 |
| C6 | between C3 and C8 | `npm install --userconfig=/dev/null --no-audit --no-fund --ignore-scripts` of the §2.1 packages into the scratchpad; `esbuild --bundle --minify --format=esm --platform=browser`; `gzip -9`; `brotli` | §2.1 |
| C7 | between C3 and C8; re-run at C12 | Python: string-literal overlap between `maplibre-gl-worker-*.js` and `MapIsland.*.js` | 128 of 128 worker literals present in the main chunk |
| C8 | 21:57:10Z | duckdb: `count(distinct entity_id) filter (where label is null or trim(label)='')` + per-compartment breakdown | 192,536 of 232,625 |
| C9 | between C8 and C11 | Python: synthetic graph JSON at 50/100, 500/1,500, 3,000/10,000 | §2.4 |
| C10 | between C8 and C11 | `python3` regex over `dist/{map,network,search,}/index.html` for `<script>`, inline styles | 2 inline scripts (4,510 B) per island page; 0 on `/` |
| C11 | 22:01:16Z | `git diff --stat b051732c HEAD -- web AGENTS.md docs/adr docs/2_canonical_design_spec.md` | empty |
| C12 | 22:07:08Z | re-verification for NEW-2/3/4: `grep 'worker&url'`, the C7 overlap, `grep client:only`, `.sig-island` CSS, `pages.ts` route entries | unchanged: 128/128; three `client:only`; no `/releases/` or `/research-dossier/` in the sweep lists |
