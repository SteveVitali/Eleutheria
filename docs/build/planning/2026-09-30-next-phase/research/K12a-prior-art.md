# K12a — Prior art for explorable knowledge-graph products

- **Row:** K12a (Stream K, research) · **Written:** 2026-09-30 (research window 2026-09-30T21:30:36Z – 21:38:10Z,
  `date -u` stamps taken immediately before each request batch)
- **Worktree HEAD at write time:** `fc1c8aed` (branch `claude/next-phase-planning`)
- **Feeds:** K0 (interactive-architecture decision), K1 (map), K2 (graph + entity pages), K3 (search), K5/K6 (dossier
  sources and embedded visualisations), K9/K10 (source table and pages), K13 (UX synthesis).
- **Extends, does not repeat, J2.** `research/J2-prior-art.md` already covers source pages, record provenance, downloads,
  releases, ingestion logs and metadata standards (its PC-1…PC-11). This note cites J2 by pattern id where it applies and
  adds the map, graph, search, entity-page and interactivity/accessibility dimensions.
- **Query log (P15):** `data/query_log_K12a.csv` has **102 logged requests**: 92 WebFetch, 3 curl and 7 WebSearch. 91
  kept at least one hit. **8 were GETs of the live site** (Q001–Q008). Every `[Qnnn]` below resolves to a URL fetched
  under that id (§11). Search-engine summaries were used only as leads and are never cited. **11 requests returned
  nothing usable**: JS shells, a bot wall, navigation-only content, or redirects (§10). That count is itself evidence for
  §6. Thousands separators inside CSV `notes` are written as `;` so the fields stay unquoted.
- **Evidence classes (P1):**
  - §1 is `live-read` plus `code` (`web/lighthouserc.json`, `web/package.json`).
  - §§2–6 facts are `live-read` (fetched 2026-09-30).
  - Sizing (§8), cost arithmetic and the K0 implications (§9) are **`inference`** and labelled.
- **Status vocabulary (P5):** nothing here is engineered or verified for SIG. These are design inputs only.
- **P16:** no request carried the operator's identity. The curl GETs used curl's default User-Agent. No service that
  requires a contact string (the Nominatim and OSM tile policies [Q011], [Q017]) was called.

---

## 0. Summary

**What best-in-class products do (live-read):**

1. **No public knowledge-graph product we could read shows a "global graph" of 10⁵–10⁶ nodes.**
   - The public explorers show three things: typed relationship *tables* on entity pages (OpenSanctions [Q024], ICIJ
     [Q069], OpenCorporates [Q067]), *bounded* neighbourhood graphs (ICIJ's per-node graph [Q069]), and *curated,
     annotated* maps (LittleSis Oligrapher [Q027]).
   - Unbounded exploration sits behind sign-up with node caps. Neo4j Bloom shows 100–10,000 nodes [Q073]; the
     OpenScreening graph (OpenSanctions + Linkurious) needs a sign-up [Q028]; Aleph diagrams are private [Q029].
   - Renderer ceilings sit well below SIG's graph size:
     - sigma.js targets "thousands of nodes and edges" [Q031];
     - Cytoscape.js WebGL runs ~3,200 nodes / 68,000 edges at 10 FPS on an M1 [Q038];
     - cosmos.gl reaches "hundreds of thousands" of nodes but needs WebGL 2 and has iOS/Android gaps [Q033].
2. **Entity pages are the backbone of graph UX.** They put every value next to its sources and counts
   ("89 statements · 28 datasets"), give typed "Linked from / Linked to" tables and a data-sources list [Q024], state
   how current the data is [Q069], [Q068], keep contradictory values visible with a rank and a reason [Q066], and use
   persistent IDs that redirect on merge [Q080].
3. **Search is typed and faceted, and server-rendered in the strongest exemplars.**
   - OpenSanctions returns schema-typed results with Topics / Data sources / Countries facets and a "Data current as of"
     line, rendered on the server [Q070].
   - Atlas of Surveillance serves a sortable server-rendered table of 15,135 rows with a CSV download [Q064].
   - Wikidata's typeahead disambiguates with *label + description* ("Flock Safety — American video surveillance
     company") [Q095].
   - Static client indexes scale to about 10⁴ pages (Pagefind, <300 kB payload per search on 10,000 pages [Q048]). One
     practitioner reports crashes at 250k–300k pages [Q054].
4. **Maps have a free, self-hostable, attribution-only route.**
   - Protomaps publishes a planet PMTiles basemap: ODbL data, CC0 styles, BSD-3 code, ~120 GB for z0–15 [Q009],
     [Q018].
   - It is served from object storage by HTTP range requests [Q021]. Cloudflare R2 charges no egress and $0.015/GB-month
     for storage [Q089].
   - Hosted alternatives: OpenFreeMap is free with no SLA [Q010]; the Stadia and MapTiler free tiers are
     **non-commercial** and capped [Q012], [Q013].
   - Place search: Nominatim forbids client-side autocomplete and caps use at 1 req/s [Q017]. A static gazetteer such as
     GeoNames (CC BY 4.0; cities15000 is 3.2 MB zipped [Q020]) or a self-hosted Photon (~95 GB, ≥64 GB RAM [Q094]) are
     the alternatives.
5. **JS-heavy peers are invisible to non-JS readers.** DeFlock, alpr.watch, Eyes on Flock, Surveillance Watch, Aleph and
   Reasonator all returned empty shells or titles to our fetcher [Q063], [Q060], [Q061], [Q062], [Q044], [Q036].
   - Against that: Atlas of Surveillance keeps a server-rendered search as "the most comprehensive data" beside its
     JS-only ArcGIS map [Q097], [Q064].
   - GOV.UK requires content sites to work HTML-only and advises against SPAs [Q074]. Google recommends server-side or
     pre-rendering because "not all bots can run JavaScript" [Q077].
   - In WebAIM Million 2026, Astro-built home pages averaged 9.0 detected errors against a 56.1 average (−84%;
     correlation only) [Q078].

**Direction for K0 (inference, §9):** the evidence favours **option (c) built as (b)**:
- static, printable, citable entity, source and dossier pages rendered server-side, with typed tables as the
  equivalent of every visual;
- progressively enhanced islands under per-template JS budgets;
- app-like explore surfaces (`/map/`, `/network/`, `/search/`, a source explorer) whose state lives in the URL and which
  keep a no-JS equivalent.

A full SPA (d) is contradicted by every accessibility, crawlability and citation source read.

---

## 1. SIG today (live-read, 8 GETs; plus `code`)

| Surface | Observation | Evidence |
|---|---|---|
| Home | Qualified counts: 55 jurisdictions with dossiers, 178 sources tracked for freshness, 223,901 resolved sites (from 232,625 records); "SIG never publishes a total". The fetcher reads tier-0 claims as **242,320**. `/network/`'s raw HTML shows a tier distribution of 2,245,390 untiered + 2,690 W1 + 175,114 W3 = **2,423,194** claims, and J2 recorded "2,423,200". The home figure is **unverified** here (the fetcher may have dropped a digit); this goes to C/J1. | [Q001], [Q006] |
| `/map/` | Attribution "© OpenStreetMap contributors (ODbL)" and "served from self-hosted static vector tiles", "no hard dependency on a third-party tile CDN". The raw HTML references **12 per-licence `*-sites.pmtiles` overlays** and **no basemap style or tile URL** (local scan). The page is **3,460,837 bytes** of HTML (uncompressed; curl sent no `Accept-Encoding`) holding **1,504 `<tr>` rows** of H3-binned tables. The page calls these tables "the equivalent, not a fallback". | [Q002], [Q005] |
| `/network/` | "defaults to an **ego network** around one entity — never a global graph". **131 unique node ids, all UUIDs** (one hub of degree 130 plus 130 leaves). 415 `<li>` edge/path list items make up the no-JS surface. | [Q003], [Q006] |
| `/search/` | The interactive filter covers "the first 500 of 232625 mapped sites"; without JS the page offers browse links. | [Q004], [Q007] |
| Dossier `/dossier/az/` | No agency or vendor names and no entity links. The source appears as the registry id `camreg_azdot_az`. Print/PDF and JSON are offered, plus a ruleset-pinned permalink. | [Q008] |
| Island budgets (`code`) | `web/lighthouserc.json`: `/map/` MapLibre+PMTiles ≈ **1.79 MB raw script** at the P32.15 baseline (incl. a 507 KB worker), ceiling 2.0 MB script / 2.3 MB total. `/network/` ≈ 230 KB raw (ceiling 400/450 KB). `/search/` ≈ 228 KB raw (ceiling 400/450 KB). Every other public page: script **0**, total ≤ 153,600 B. `web/package.json` pins `maplibre-gl` 6.9.0 and `pmtiles` 4.5.0. | `code` |

*Inference:*
- The live `/map/` HTML document alone (3.46 MB uncompressed) is larger than the 2.3 MB total ceiling. That ceiling is
  asserted against the fixture `dist` in CI, not against production data. The compressed transfer size was not
  measured. C2 owns the verdict.
- The operator's "no map layer" complaint (U-003.1) matches the missing basemap. The "UUIDs are meaningless" complaint
  (U-003.2) matches the 131 UUID labels.

---

## 2. Maps

### 2.1 Exemplars

| Product | What users can do | Stack / posture | No-JS / a11y | Evidence |
|---|---|---|---|---|
| **DeFlock** (peer) | ALPR map from OSM; place search | Vue3 + Vuetify + **MapLibre GL** (Leaflet being phased out). OSM via Overpass. Points and vector tiles in **Cloudflare R2**. **Nominatim** for geocoding. MIT. | The site is a JS shell to a non-JS reader | [Q065], [Q063] |
| **Atlas of Surveillance** (peer) | Map of police tech; legend toggles; zoom | **Esri ArcGIS**, with a warning that it "will serve content from arcgis.com, a third-party host, which may restrict access for users on Tor or users with third-party cookies blocked" | "requires use of Javascript"; points users to the text search "for the most comprehensive data" | [Q097], [Q058] |
| **US National Park Service (NPMap)** | Park web maps | Next NPMap "will be based on MapLibre" | A map description is required (it acts as alt text). Tab order is preserved. A toggleable **tabular view** and data downloads are planned. Colour is never the only cue. | [Q023] |
| **Wikidata Query Service** | Any query → a "Map" view (OSM) among table, timeline, graph and other views; iframe embeds | Views over one result set | Table is the default view | [Q101] |
| **SIG today** | 8 layer toggles; coverage hatching | MapLibre + 12 per-licence PMTiles overlays, **no basemap** | Tables are declared the equivalent | [Q002], [Q005] |

### 2.2 Map patterns (MAP-n; inference built on the reads cited)

- **MAP-1 Basemap under the data, with attribution in a map corner.** OSM guidance allows "any corner" and a collapse
  to an "(i)" button, provided the licence stays findable. Static images need the same attribution [Q081].
- **MAP-2 Density at low zoom, points at street zoom.** Two proven routes:
  - build-time clustering into the tiles with tippecanoe (`--cluster-distance`, `--cluster-densest-as-needed` →
    `"clustered": true`, `--accumulate-attribute` for sums, `-o *.pmtiles`) [Q082];
  - client-side clustering with supercluster (MapLibre GeoJSON `cluster`, `clusterRadius` default 50,
    `getClusterExpansionZoom`; supercluster demos 6 M points) [Q015], [Q016].

  SIG already tiles its points, so the tippecanoe route fits without shipping 225k points to the client (§8).
- **MAP-3 Place search.** Jump to a place by name. Autocomplete needs a source whose policy allows it (§2.4).
- **MAP-4 A tabular equivalent of every layer.** SIG [Q002], NPS [Q023] and the WAI "long description / data table"
  guidance for maps [Q043] all call for it. Paginate or link it; don't inline 1,504 rows (inference from Q005).
- **MAP-5 Popups that link out.** Each feature links to its entity page, source page and evidence (ties to J2 PC-3).
- **MAP-6 Keyboard operation.** MapLibre's `KeyboardHandler` gives +/− zoom, arrow-key pans of 100 px and
  Shift+arrow rotate/pitch [Q092]. It does not make features focusable. Feature-level keyboard access needs the table
  equivalent (MAP-4) or a layer such as Data Navigator (§6).
- **MAP-7 Third-party exposure is a design choice.** AoS warns its users about ArcGIS [Q097]. A self-hosted basemap
  keeps SIG's existing "no hard dependency on a third-party tile CDN" posture [Q002].

### 2.3 Basemap providers (numbers as read)

| Option | Cost | Limits | Licence / attribution | SLA / risk | Evidence |
|---|---|---|---|---|---|
| **Protomaps planet PMTiles, self-hosted** | Storage and requests only (see R2 row) | None beyond own hosting. Planet ≈ **120 GB for z0–15**; "each additional zoom level roughly doubles the size"; `pmtiles extract` for regions; daily builds | Tiles ODbL ("Protomaps © OpenStreetMap"); styles CC0; code BSD-3; fonts/sprites in `basemaps-assets` | Own ops. Deploy = bucket + optional serverless decode + CDN; cache hits "100 millisconds or less" vs "multi-second" from a single-region bucket; Cloudflare "$5 (USD)" baseline | [Q009], [Q014], [Q018], [Q021] |
| **Cloudflare R2** (storage for the above) | $0.015/GB-month; Class A $4.50/M; Class B $0.36/M; free tier 10 GB, 1 M A, 10 M B per month | — | — | **Egress free** | [Q089] |
| **OpenFreeMap public instance** | Free; "no limits on the number of map views or requests"; no keys, no cookies | — | "OpenFreeMap © OpenMapTiles Data from OpenStreetMap"; MIT | Donation-funded; "I don't offer SLA guarantees". Weekly planet. Self-hostable (~300 M hard-linked files, avg 450 B) | [Q010], [Q090] |
| **OSM Foundation raster tiles** | Free | No bulk or prefetch; heavy use may be blocked "without notice"; identifying User-Agent required (P16 tension for server-side use) | ODbL attribution | "no SLA or guarantee" | [Q011] |
| **Stadia Maps** | Free 200k credits/month (**"Commercial use not allowed"**, no overage); $20 → 1 M; $80 → 7.5 M; $250 → 25 M | 1 credit per vector/raster tile; 20 per static map; 20 per geocode | Attribution per legal terms (not detailed on the pricing page) | Commercial SLA on paid tiers | [Q012] |
| **MapTiler Cloud** | Free 5k sessions + 100k requests/month, **non-commercial**, service pauses at the cap; Flex $30 → 25k sessions, 500k requests | Overage $2.50 per 1k sessions | MapTiler logo required on free | 99.9% SLA only on Custom | [Q013] |

### 2.4 Place search and geocoding

| Option | Typeahead allowed? | Numbers | Licence | Evidence |
|---|---|---|---|---|
| Nominatim (OSMF public) | **No:** "you must not implement such a service on the client side" | "absolute maximum of 1 request per second"; must cache; identifying UA/Referer | ODbL attribution | [Q017] |
| Photon public demo | Yes (search-as-you-type) | "Extensive usage will be throttled or completely banned"; no availability guarantee | Apache-2.0 | [Q019], [Q094] |
| Photon self-hosted | Yes, with typo tolerance and bbox/tag filters | Planet DB "about 95GB" (2026, +~10%/yr); "At least 64GB RAM"; weekly dumps incl. country extracts | Apache-2.0 | [Q094] |
| Stadia / MapTiler geocoding | Yes | Stadia 20 credits per request; MapTiler free 1k search sessions/month | Commercial terms | [Q012], [Q013] |
| **Static gazetteer** (GeoNames) | Yes, client-side over a small list | cities15000.zip 3.2 MB; cities500.zip 13 MB; admin1 148 KB; admin2 2.3 MB; allCountries 402 MB; refreshed daily | **CC BY 4.0** | [Q020] |

*Inference:* for SIG the natural place list is SIG's own jurisdiction hierarchy (country → state → county/city, K4)
plus a GeoNames subset for "fly to" place names. Both can be shipped as a small static typeahead index (§4.3, §8). A
full geocoder is only needed for street addresses. That need is weak for SIG's personas and carries Part VIII questions
about address lookups.

---

## 3. Graph and network exploration

### 3.1 Exemplars

| Product | What users can do | Scale (as read) | Graph vs tables | Access / no-JS | Evidence |
|---|---|---|---|---|---|
| **OpenSanctions** entity page | Read every property value with source counts ("89 statements · 28 datasets"); follow **Family members**, **Associations**, **Positions held**, **Linked from**, **Linked to** tables; list data sources | Entity page for Q7747 cites 26+ datasets | **Tables only. No graph visualisation on the page.** A graph exists via the partner tool OpenScreening (Linkurious; free sign-up) | Server-rendered | [Q024], [Q028] |
| **ICIJ Offshore Leaks** node page | Fields; **Connections** tables (Officer / Intermediary with Role, From, To, *Data From*); embedded graph | Per-node neighbourhood | **Tables + JS graph** | Tables are semantic HTML; graph shows a spinner without JS; data-currency note ("current through 2015") | [Q069] |
| **LittleSis** | Profiles and relationships; curated **Oligrapher** maps with click-through **annotations ("story mode")**, drag layouts, embeds | ">1.6 million relationships between over 400 thousand people and organizations" | Curated maps, not a global graph | Site returned an Anubis proof-of-work "Access Denied" to our fetcher; GPL-3.0 code | [Q100], [Q027], [Q026] |
| **OCCRP Aleph / Aleph Pro** | Users *build* network diagrams inside investigations (add entities and links); private or shared | 24,000+ users (search lead only; not cited) | User-built diagrams | Landing page empty to our fetcher; Aleph Pro hosted; free for nonprofit journalism, at-cost for public-interest groups; public instance stays free | [Q029], [Q044], [Q051] |
| **Wikidata / WDQS / Scholia / Reasonator** | Query → table/map/timeline/tree/**graph** views with iframe embeds; Scholia composes profile pages from SPARQL panels | WDQS hard 60 s query deadline; 60 s processing per 60 s per client; 5 parallel queries per IP | Query-bounded views | Reasonator is a JS shell to our fetcher | [Q101], [Q037], [Q030], [Q036] |
| **OpenCorporates** | Company page lists subsidiaries (38), control statements (25+) and branches | — | Lists | Many fields login-gated; disclaimer "it is not the primary source" | [Q067] |
| **Linkurious / Neo4j Bloom** (investigator tools) | Search, **expand**, filter panel, **timeline**, node/edge grouping, geographic map, lasso | Bloom displays "100 to 10,000 unique nodes"; query response capped at 10,000 records "in combination with the limitation of the client resources" | Canvas of a working set | Commercial, behind login | [Q041], [Q073] |
| **Kumu / Graph Commons** (authoring) | Build, filter, cluster and embed maps; exports (GraphML, Cypher, CSV) | "no hard limit" but a "practical limit"; Canvas "slower, but supports more varied decorations" vs WebGL "faster, but supports less visual variety" | Author-curated graphs | Free public projects; Kumu private $9–20 per project per month | [Q102], [Q040], [Q039] |

### 3.2 Graph patterns (GRA-n; inference built on §3.1)

- **GRA-1 Entity page first.** Relationships are typed tables. Each row carries the counterparty's human label, role,
  dates, *source ("Data From")* and a status badge. Every graph is a *view* of these rows, never the only surface
  [Q024], [Q069].
- **GRA-2 Bounded neighbourhood graph on the entity page.** 1–2 hops, typed and filterable. This is ICIJ's pattern, and
  SIG's ego view already does it, but with UUID labels [Q069], [Q003].
- **GRA-3 Curated "story" graphs.** Hand-arranged, annotated maps for recurring questions, e.g. "who can search Texas
  ALPR data". LittleSis's Oligrapher shows the value [Q027]; for SIG these would be generated from the spine and
  reviewed, never hand-asserted (inference).
- **GRA-4 Working-set explorer with expansion and caps.** Search → add → expand → filter → timeline, capped the way
  Bloom caps a scene (≤10,000 nodes) [Q073], [Q041].
- **GRA-5 Aggregated overview graphs.** Stand-ins for the "global graph" (inference). Nodes are *types × jurisdictions*
  or communities (graphology `communities-louvain` [Q034]), not raw entities. They drill down to GRA-2.
- **GRA-6 Path questions.** "How is agency A connected to vendor V?" answered with graphology `shortest-path` [Q034]
  over a bounded subgraph, rendered as a list of hops with sources (inference).
- **GRA-7 Human-readable labels everywhere.** Label plus a disambiguating description, as in Wikidata typeahead
  ("Flock Safety — American video surveillance company") [Q095] and OpenSanctions results ("Company · Trade risk ·
  Poland") [Q070]. Raw ids stay in the URL and an "identifiers" block.

### 3.3 Graph libraries (numbers as read)

| Library | Renderer | Stated scale | Licence | Caveats | Evidence |
|---|---|---|---|---|---|
| sigma.js + graphology | WebGL | "graphs of thousands of nodes and edges"; for "a few hundreds" d3 is "a best fit" | MIT | Algorithms in graphology (FA2 layout, Louvain, shortest path, metrics) | [Q031], [Q034] |
| Cytoscape.js | Canvas; **experimental WebGL** (3.31) | ~1,200 n / 16,000 e: canvas ~20 FPS → WebGL 100+ FPS; ~3,200 n / 68,000 e: 3 → 10 FPS (M1 MacBook Pro, Chrome) | MIT | WebGL mode: no dashed edges or gradients, triangle arrows only, centre labels only | [Q038], [Q032] |
| cosmos.gl | GPU (layout and render in shaders) | "hundreds of thousands of points and links on modern hardware" | MIT | WebGL 2 required; iOS ≥15.4 lost `EXT_float_blend`; some Android devices unsupported | [Q033] |
| Oligrapher | React/Redux | Curated maps | GPL-3.0 | Copyleft (inference: check compatibility with SIG's Apache-2.0 web package before reuse) | [Q027] |
| Data Navigator | Semantic-HTML overlay | Any structure (lists, trees, networks, spatial) | MIT | An accessibility layer, not a renderer | [Q042] |

*Inference, applicability:* SIG's graph (on the order of 10⁵–10⁶ entities) is 1–3 orders of magnitude beyond every
labelled, interactive renderer read here. A node-link view of the whole spine would also be unreadable on phones, where
cosmos.gl has known gaps [Q033]. "Laying bare all we know" (U-003.2) is best met by GRA-1 + GRA-2 + GRA-5 + GRA-6,
with overview graphs kept to at most a few thousand nodes so sigma.js can label them.

---

## 4. Search over knowledge graphs

### 4.1 Exemplars

| Product | Result model | Facets / filters | Rendering | Evidence |
|---|---|---|---|---|
| OpenSanctions `/search/` | Schema-typed results ("PersonDebarred · United States"); name, classification, country | **Topics, Data sources, Countries**, each with counts; paging | Server-rendered; "Data current as of 2026-09-30"; "sourced from our API service" | [Q070] |
| OpenSanctions API | `/search`, `/match`, `/entities/<id>` | — | API key required; **free keys for public-interest work**; pay-as-you-go otherwise; self-hostable (`yente`) | [Q046] |
| Atlas of Surveillance `/search` | Rows: Agency, City, County, State, Technology, Vendor, plus links and "more info" | Location text box and 13 technology checkboxes | **Server-rendered sortable table**, "1 - 100 of 15135", 152 pages, **CSV download** | [Q064] |
| Wikidata typeahead | id + label + **description** + match type | — | API JSON | [Q095] |
| Datasette | Table rows | `?_facet=column`, array and date facets, default 30 values, **stable `toggle_url`s**, the same facets on `.json`; suggested facets must compute "in under 50ms" | Server-rendered + JSON parity | [Q087] |

### 4.2 Search patterns (SRC-n; inference)

- **SRC-1 One box, typed results.** Each result shows its type, a disambiguating description, jurisdiction and a
  support/tier badge, grouped or faceted by type (entity, place, source, dossier, document, contract, policy)
  [Q070], [Q095].
- **SRC-2 Facets as URLs.** Every facet state is a linkable, citable URL with a JSON twin (Datasette [Q087]). This
  replaces client-only filter state.
- **SRC-3 Place-aware matching.** A query that names a place ("Canberra"; C2 found 0 results) resolves to the
  jurisdiction and offers "things in/near X". This needs the gazetteer from §2.4.
- **SRC-4 Typo and substring tolerance.** FTS5 has **no fuzzy matching**. Its trigram tokenizer gives substring and
  indexed `LIKE`/`GLOB` matching for ≥3 characters, bm25 column weights and prefix indexes [Q053]. Fuzziness needs
  another engine (MiniSearch/Orama client-side [Q093], [Q050]; Typesense/Meilisearch server-side [Q099], [Q057]) or a
  spelling-suggestion layer (not researched here).
- **SRC-5 Accessible typeahead that enhances a plain form.** Follow the ARIA APG combobox (`role=combobox`,
  `aria-expanded`, `aria-controls`, `aria-activedescendant`, `aria-autocomplete`; Down/Escape/Enter) [Q086]. GOV.UK
  `accessible-autocomplete` enhances a `<select>` in place (`enhanceSelectElement`) [Q096]. The no-JS path is a `GET`
  form that returns a server-rendered or pre-rendered result page.

### 4.3 Search technologies (numbers as read)

| Technology | Where it runs | Scale / size facts | Fuzzy | Facets | Cost / licence | Evidence |
|---|---|---|---|---|---|---|
| **Pagefind** | Static, post-build index of HTML, chunked, fetched on demand | "10,000 page site with a total network payload under 300kB … closer to 100kB" for most; one practitioner report: crashed at ~300k pages, best 250k, abandoned for custom JSON (2025) | Not stated | `data-pagefind-filter`; multisite `mergeIndex` + `indexWeight` + `mergeFilter` | Open source; static hosting | [Q048], [Q054], [Q083], [Q084] |
| **Orama** | Browser, server, edge | "less than 2kb" (the engine, not an index); full-text, vector, hybrid, geosearch | Yes | Yes | Apache-2.0 | [Q050] |
| **MiniSearch** | Browser or Node, in memory | "Memory-efficient index … mobile browsers"; `toJSON`/`loadJSON` | Yes (edit distance) + prefix + auto-suggest | Filtering | MIT | [Q093] |
| **Static SQLite over HTTP range** (sql.js-httpvfs) | Browser WASM → static file | 670 MiB DB (8 M rows); indexed lookup ~1 kB; complex query 10–20 GETs / 130–270 KiB; **FTS over 8 MB ≈ 70 KiB fetched** | Via FTS tokenizers only | SQL | Static hosting | [Q055] |
| **SQLite FTS5 over an API** (SIG's landed P32.14 path) | Server | bm25 with column weights; trigram substring; prefix indexes | No | SQL `GROUP BY` | Existing infra | [Q053] |
| **Typesense** | Server (in-memory C++) | RAM "2X-3X" the searchable data; ≥2 vCPU; 2.2 M records → 104 qps at 11 ms on 4 vCPU; 28 M records → 46 qps at 28 ms | Yes | Yes, plus geo | **GPL-3.0**; Typesense Cloud billed hourly | [Q056], [Q099] |
| **Meilisearch** | Server | Cloud usage plan $30/mo (100K docs, 50K searches); resource plan $23/mo (0.5 vCPU, 1 GB) | Yes | Yes | Community Edition MIT, self-host free | [Q057] |

---

## 5. Entity and detail pages

### 5.1 Exemplars and patterns (ENT-n)

| Pattern | Exemplar (what it does) | Evidence |
|---|---|---|
| **ENT-1 Values with their sources** | Each property lists every value with language tags, per-value dataset links and "N statements · M datasets"; processing tags "raw / inferred / patch" | OpenSanctions [Q024] (J2 PC-3 covers the provenance panel) |
| **ENT-2 Contradictions kept, ranked, explained** | Preferred / normal / deprecated ranks; "reason for deprecated rank (P2241)"; "All statements, including deprecated ones, must be verifiable"; default ("truthy") views show the best rank, and deprecated values stay queryable | Wikidata [Q066] |
| **ENT-3 Typed relationship tables** | "Linked from / Linked to", family, associations; Connections with Role, From, To, *Data From* | OpenSanctions [Q024]; ICIJ [Q069] |
| **ENT-4 History as a per-period table with originals** | "Tax Filings and Audits by Year" with PDF and XML originals per year; "About This Data" with an update date | ProPublica Nonprofit Explorer [Q068] |
| **ENT-5 Currency and primacy disclaimers** | "current through 2015"; "it is not the primary source, and the company registry should always be referred to" | ICIJ [Q069]; OpenCorporates [Q067] |
| **ENT-6 Persistent ids, redirect on merge** | "item IDs are designated as persistent identifiers … merged items should be redirected. Never reuse" | Wikidata [Q080]; contrast OpenSanctions ids that may change on de-duplication (J2 Q016) |
| **ENT-7 Visual + static fallback + bundle** | Static PNG of the chart in the page; ZIP with CSV + JSON metadata + README; API URLs; cite block; "Last updated … Next expected update" | Our World in Data [Q079] |
| **ENT-8 Profile composed of query panels** | Scholia's author/org/topic pages built from SPARQL panels (graphs + tables) | [Q030] |
| **ENT-9 Gating harms verification** | OpenCorporates hides "Last update from source" and officers behind login | [Q067] |

*Inference:* SIG's resolution envelopes map onto ENT-6. A merged entity's old URL should redirect (never 404) so that
citations survive re-resolution. SIG's "contradiction kept visible" rule maps onto ENT-2 without adopting Wikidata's
community-judgement semantics: the ranks would be SIG's recorded belief under a pinned ruleset.

### 5.2 Source and dataset pages (brief; J2 PC-1…PC-7 is authoritative)

What this row adds to J2:
- OWID-style bundles that ship data, metadata and a README together [Q079].
- ProPublica-style per-period originals [Q068].
- Datasette-style browsable tables with URL facets and JSON parity for a source's records [Q087].

Kaggle dataset versioning could not be assessed (JS shell, [Q091]). Transitland and OpenSanctions (J2 §2.1, §2.5)
remain the version-history exemplars.

---

## 6. Interactivity vs accessibility, printability, crawlability and citation stability

### 6.1 Facts read

| Topic | Fact | Evidence |
|---|---|---|
| Why JS fails | "temporary network errors", "ad blockers", CDN downtime, DNS failures, browser bugs, "corporate firewalls", mobile-network content changes | GOV.UK [Q074] |
| What must work without JS | "content-based websites" must work HTML-only; JS may enhance (e.g. "an autocomplete could enhance a < select > element"); avoid SPAs where page loads are "handled by JavaScript, rather than the browser" | GOV.UK [Q074] |
| Crawlers | "server-side or pre-rendering is still a great idea … not all bots can run JavaScript"; links must be `<a href>`; SPAs risk soft 404s | Google [Q077] |
| Accessibility at web scale | 2026: "95.9% of home pages had detected WCAG 2 failures", "56.1 errors per page". Framework table: Astro 5,472 pages, 9.0 errors (−84.0%); Next.js 40.9; React 43.5; Vue 64.6; jQuery 64.9; caveat: errors "cannot always be attributed to that technology" | WebAIM [Q076], [Q078] |
| JS budgets | P75 device Galaxy A51, 7.2 Mbps / 94 ms RTT. **Markup-heavy** site, 3 s: **75 KiB** compressed JS, 1.4 MiB total (5 s: 100 KiB JS). **JS-heavy** site, 3 s: **365 KiB** JS, 730 KiB total (5 s: 650 KiB) | Infrequently [Q085] |
| Island architecture | Astro strips JS by default; `client:load` / `client:idle` / `client:visible`; `server:defer` server islands render dynamic parts separately | Astro [Q075] |
| Complex images | Maps, diagrams and charts need a short description plus a long description; a data table is an accepted long description | W3C WAI [Q043] |
| Accessible navigation of networks | A keyboard/screen-reader overlay in semantic HTML over any visual (MIT) | Data Navigator [Q042] |
| Map a11y practice | Description required; tab order; tabular view; not colour alone; low-vision basemap | NPS [Q023] |
| Print/static | Static PNG in the page; static maps need attribution (one instance per document suffices) | OWID [Q079]; OSMF [Q081] |
| Invisible to non-JS readers | DeFlock, alpr.watch, Eyes on Flock, Surveillance Watch, Aleph and Reasonator returned shells or titles; LittleSis sat behind a proof-of-work bot wall | [Q063], [Q060], [Q061], [Q062], [Q044], [Q036], [Q026] |
| Citation-stable interactive state | Datasette facet URLs and `toggle_url`; WDQS view embeds | [Q087], [Q101] |

### 6.2 Lessons (A11Y-n; inference anchored in §6.1)

- **A11Y-1** The *record* (entity, source, dossier, search-result pages) must be complete in server-rendered HTML.
  Visuals are enhancements with a table-shaped long description [Q043], [Q074], [Q077].
- **A11Y-2** Every interactive state that users will cite (map viewport and filters, graph focus and hops, search query
  and facets) must be encoded in the URL and reproducible without JS as a static or server-rendered result [Q087].
- **A11Y-3** Our fetcher behaves like many archivers, link unfurlers and LLM agents. The peers that are JS shells were
  unreadable to it. SIG's citation promise (belief-pinned permalinks) depends on being readable (§6.1).
- **A11Y-4** Budgets should be set per template and measured compressed on a P75 device. A content page with an
  embedded island (dossier map) needs a markup-heavy budget (≤75–100 KiB JS). An explore surface fits a JS-heavy budget
  (≤365–650 KiB JS) [Q085]. SIG's `/map/` baseline of 1.79 MB raw script needs its compressed size measured against
  that (K1).
- **A11Y-5** Keyboard support in the map library is not feature access. MapLibre pans and zooms by keyboard [Q092], but
  features are reachable only through the table equivalent or an overlay such as Data Navigator [Q042].
- **A11Y-6** Load third-party assets only with disclosure. AoS explicitly warns about ArcGIS [Q097]; self-hosting
  removes the question [Q002].

---

## 7. Peers: civic and surveillance-transparency UX

| Peer | What users can do | JS posture (to a non-JS reader) | Map / search stack | Lesson for SIG | Evidence |
|---|---|---|---|---|---|
| Atlas of Surveillance (EFF) | Search by city, county, state, agency or vendor; 13 technology filters; sortable table; CSV; per-record links; ArcGIS map | Search is server-rendered; map needs JS and a third party | ArcGIS; server table | Keep the table as the complete surface; SIG can beat it on per-claim provenance (J2) and on a self-hosted map | [Q064], [Q097], [Q058] |
| DeFlock | Crowdsourced ALPR map from OSM | Shell | MapLibre, R2 tiles, Nominatim | Same stack family as SIG. Nominatim's no-autocomplete policy constrains place search [Q017]. J2 records the OSM "unverified cameras" trust problem | [Q065], [Q063] |
| alpr.watch | Map; agenda keyword scanning ("flock", "license plate reader", "alpr"); **email alerts by ZIP + radius** | JS-dependent; counts empty without JS | Not stated | An alerts/subscription pattern for K7 `/watch` (radius-based) | [Q060] |
| Eyes on Flock | "Aggregating Flock Safety Transparency Portal Data" | Title only | — | Not assessable | [Q061] |
| Surveillance Watch | Surveillance-industry map/graph (per title) | Title only | — | Not assessable. A graph-first peer that non-JS readers cannot read | [Q062] |

---

## 8. SIG-scale sizing (inference; arithmetic shown, inputs cited)

| Quantity | Estimate | Basis |
|---|---|---|
| Map points | 223,901 resolved sites (232,625 records) | [Q001], [Q004] |
| Points as a client GeoJSON download | ≈ 225k × ~150 B ≈ **34 MB** uncompressed (assumed ~150 B per feature) → not viable for client clustering on phones; keep server/build-time tiling (tippecanoe → PMTiles) | [Q082] |
| Basemap planet z0–15 | ≈ 120 GB. Using "each zoom ~doubles": z0–14 ≈ 60 GB, z0–13 ≈ 30 GB, z0–12 ≈ 15 GB (rough) | [Q009] |
| Basemap storage cost on R2 | 120 GB × $0.015 ≈ **$1.80/month**; egress $0; reads $0.36 per M beyond 10 M per month (a CDN in front reduces billed reads) | [Q089] |
| Stadia free tier in sessions | 200k credits at 1 credit per tile ÷ ~50–150 tiles per session (assumed) ≈ 1,300–4,000 sessions/month, **non-commercial only** | [Q012] |
| Typeahead name index | 10⁵ entities × ~60 B (label, type, jurisdiction, id) ≈ 6 MB; 10⁶ ≈ 60 MB uncompressed. Too big to preload → shard by prefix (a few KB per shard) or serve from FTS5 | assumption; cf. Pagefind chunking [Q048] |
| Page-per-entity static search | 10⁵–10⁶ pages is at or above the one reported Pagefind failure zone (250k–300k) → shard with `mergeIndex` per type or compartment, or don't use Pagefind for entities | [Q054], [Q084] |
| Static SQLite FTS | Plausible: 670 MiB DB queried with ~70 KiB per FTS query in the demo. WASM runtime size not measured | [Q055] |
| Hosted/self-hosted engine RAM | If searchable text is ~200 B per entity: 10⁶ → 200 MB → 400–600 MB RAM (Typesense 2–3×) → a small VM | [Q056] |
| Graph views | Ego view today: 131 nodes. Labelled interactive views: stay ≤ ~1–3k nodes (sigma "thousands"; Cytoscape canvas ~20 FPS at 1,200 n / 16,000 e); ≤10k unlabelled (Bloom cap); 10⁵+ only GPU and not on all phones | [Q006], [Q031], [Q038], [Q073], [Q033] |

---

## 9. Implications for SIG's K0 architecture decision

K0 decides. The options are those listed in META_PLAN §6 K0. Evidence is cited; judgements are `inference`.

### Option (a) — keep the static core, make the islands richer

- **For:**
  - Least change: Astro islands already exist [Q075] and SIG's budgets and tests exist (`code`).
  - The WebAIM correlation favours Astro-style sites [Q078].
  - Crawlable and printable by construction [Q077].
- **Against:**
  - Entity pages, source pages and dossier maps (U-003.2/.5/.6/.10) would each have to stay zero-JS or become new
    named exceptions; the rule list keeps growing.
  - An embedded dossier map (K6) breaks the zero-script rule on a content page.
- **Fit:** meets U-003.1/.3 and parts of .2. Leaves U-003.6 (embedded visualisations) awkward.

### Option (b) — progressive enhancement everywhere, with documented per-template JS budgets and no-JS fallbacks

- **For:**
  - GOV.UK's model: HTML first, JS enhances [Q074].
  - Budgets can be set from P75 data, e.g. markup-heavy ≤75–100 KiB JS on content templates with an island [Q085].
  - Every visual keeps a table long description [Q043], [Q023].
  - Typeahead enhances a GET form [Q096], [Q086].
  - Lets a dossier or entity page carry a small `client:visible` map or neighbourhood island [Q075].
- **Against:**
  - Needs per-template budget enforcement and an accessibility test for each island.
  - MapLibre's weight (1.79 MB raw at baseline, `code`) cannot fit a content-page budget. Embedded maps need a lighter
    path: a static pre-rendered image with a "open interactive map" link (OWID-style [Q079]), or a lighter renderer
    (Leaflet ~42 KB [Q071]; needs a raster or vector adapter, not researched).

### Option (c) — app-like explore surfaces beside static, printable dossiers and entity pages

- **For:**
  - Matches what the exemplars do. Static or server-rendered entity pages with tables [Q024], [Q069], [Q068] sit next
    to separate interactive tools: ICIJ's graph, Aleph and OpenScreening explorers [Q029], [Q028], AoS's map beside its
    table [Q097], [Q064].
  - Explore surfaces can use the JS-heavy budget (≤365–650 KiB JS [Q085]) and WebGL graph and map libraries
    [Q031], [Q038].
- **Against:**
  - Two UX modes to maintain.
  - Explore state must still be URL-addressable and citable [Q087], or the tools become the non-citable "shell"
    pattern [Q063], [Q062].

### Option (d) — full SPA

- **Against:** GOV.UK advises against SPAs for content [Q074]. Google warns about bots and soft 404s [Q077]. Every JS
  shell in §6.1 was unreadable to our fetcher. Citation stability and print would have to be rebuilt.
- **For:** a single framework and rich transitions; nothing in the evidence needs this.
- **Fit:** poor for SIG's design-centre persona (a printable, sourced dossier; U-001).

### Evidence-weighted leaning (inference)

**(c) implemented with (b)'s rules:**
1. Every record page is server-rendered and complete without JS.
2. Visuals on record pages are budgeted `client:visible` islands with static fallbacks.
3. `/map/`, `/network/` (to become an "explore" surface), `/search/` and a source explorer are app-like islands under
   JS-heavy budgets, with URL state and no-JS equivalents.
4. Nothing is an SPA.

### Cross-cutting decisions K0 should make explicitly (each with the evidence that bears on it)

1. **Basemap:** self-host Protomaps PMTiles (licence and privacy fit, ~$2/month storage at planet scale on R2, own ops)
   [Q009], [Q018], [Q089] vs OpenFreeMap public (free, no SLA, third-party requests) [Q010] vs Stadia/MapTiler (free
   tiers are non-commercial and capped) [Q012], [Q013]. Also decide whether z-range or regional extracts cut the
   120 GB.
2. **Point density:** build-time clustering in tiles (tippecanoe) [Q082] vs client supercluster [Q016]. §8 argues for
   build-time.
3. **Place search:** a static gazetteer (SIG jurisdictions + GeoNames CC BY 4.0) [Q020] vs a self-hosted Photon
   (~95 GB, ≥64 GB RAM) [Q094]. Public Nominatim is ruled out for typeahead [Q017].
4. **Search engine:**
   - extend the landed FTS5-over-API (trigram + bm25; no fuzzy) [Q053];
   - add a static prefix-sharded typeahead (MiniSearch/Orama) [Q093], [Q050];
   - or a self-hosted Typesense/Meilisearch (GPL-3.0 vs MIT; RAM 2–3× data) [Q099], [Q056], [Q057].

   Pagefind fits the ~10³–10⁴ *content* pages (dossiers, sources, methodology) [Q048]. It does not fit 10⁵–10⁶ entity
   pages without sharding [Q054].
5. **Graph:** the "global graph" becomes a *set of* aggregated overview graphs (≤ a few thousand nodes, sigma.js)
   plus entity-page neighbourhoods plus path queries [Q031], [Q034], [Q073]. A GPU whole-graph view (cosmos.gl) could
   only ever be an optional desktop extra [Q033].
6. **Accessibility contract:** a table long description for every visual [Q043], a URL for every state [Q087], a
   keyboard overlay where tables are not enough [Q042], and APG combobox semantics for typeahead [Q086].
7. **Labels and ids:** human label + description on every node, row and result [Q095], [Q070]. Persistent ids with
   redirects on merge [Q080].
8. **Budgets:** compressed per-template budgets measured on production-like data, not only the fixture `dist` (§1
   inference) [Q085].

### Open questions handed on (not answered here)

- **K1:** the compressed transfer size of `/map/` and its island today; which zooms of the basemap to host; a
  static-image renderer for print (not researched).
- **K2:** SIG's real node and edge counts per edge type (the ego view shows only the sharing graph), and whether
  vendor↔agency or sharing overview graphs fit in ~3k nodes.
- **K3:** the fuzzy-match strategy on top of FTS5; the size of the typeahead index per compartment; licence-compartment
  separation inside one search box (ODbL, §42.3).
- **K0/K13:** whether Oligrapher-style curated "story" graphs (GRA-3) are in scope, and who reviews them (P4).

---

## 10. Limitations

- WebFetch returns a model's summary of the page. Quotes are as the fetcher reported them; a few (e.g. WebAIM's
  framework table [Q078]) were confirmed with a second, narrower prompt. The home-page tier-0 count (§1) is flagged as
  possibly mis-read.
- The Pagefind scale ceiling rests on **one practitioner report** [Q054]. It is a risk signal, not a benchmark.
- No hands-on benchmarks were run. Graph FPS figures are the vendor's own (M1 laptop) [Q038]. Compressed JS sizes of
  SIG's islands were not measured (only the raw baselines in `code`).
- INACCESSIBLE or not followed:
  - JS shells or empty pages: LittleSis site [Q026] (Anubis), Reasonator [Q036], Aleph [Q044], the OpenSanctions API
    docs [Q045], DeFlock [Q063], Eyes on Flock [Q061], Surveillance Watch [Q062], Kaggle [Q091].
  - Redirects or partial content: OpenAlex (redirect not followed) [Q088]; the Orama docs page (navigation only) [Q049];
    the Cytoscape performance section (partial) [Q032].
- Not researched: server-side static map rendering for print; Leaflet vector adapters; Typesense Cloud prices; the
  Wikidata item-page UI (J2 covers its reference model).
- The sizing in §8 uses stated assumptions (bytes per feature and per entry, tiles per session) and must be replaced by
  measurements in K1/K2/K3.

---

## 11. References (query id → URL; full log in `data/query_log_K12a.csv`)

| id | URL |
|---|---|
| Q001 | https://surveillancegraph.org/ |
| Q002 | https://surveillancegraph.org/map/ |
| Q003 | https://surveillancegraph.org/network/ |
| Q004 | https://surveillancegraph.org/search/ |
| Q005 | https://surveillancegraph.org/map/ (curl, raw HTML) |
| Q006 | https://surveillancegraph.org/network/ (curl, raw HTML) |
| Q007 | https://surveillancegraph.org/search/ (curl, raw HTML) |
| Q008 | https://surveillancegraph.org/dossier/az/ |
| Q009 | https://docs.protomaps.com/basemaps/downloads |
| Q010 | https://openfreemap.org/ |
| Q011 | https://operations.osmfoundation.org/policies/tiles/ |
| Q012 | https://stadiamaps.com/pricing/ |
| Q013 | https://www.maptiler.com/cloud/pricing/ |
| Q014 | https://docs.protomaps.com/deploy/ |
| Q015 | https://maplibre.org/maplibre-gl-js/docs/examples/create-and-style-clusters/ |
| Q016 | https://github.com/mapbox/supercluster |
| Q017 | https://operations.osmfoundation.org/policies/nominatim/ |
| Q018 | https://github.com/protomaps/basemaps |
| Q019 | https://photon.komoot.io/ |
| Q020 | https://download.geonames.org/export/dump/ |
| Q021 | https://docs.protomaps.com/pmtiles/ |
| Q022 | WebSearch: "MapLibre GL JS accessibility keyboard screen reader map WCAG" (lead only) |
| Q023 | https://www.nps.gov/maps/web/accessibility |
| Q024 | https://www.opensanctions.org/entities/Q7747/ |
| Q025 | WebSearch: OpenSanctions network graph explorer (lead only) |
| Q026 | https://littlesis.org/org/12-Goldman_Sachs_Group (INACCESSIBLE) |
| Q027 | https://github.com/public-accountability/oligrapher |
| Q028 | https://www.openownership.org/en/news/connecting-beneficial-ownership-peps-and-sanctions-data-with-openscreening/ |
| Q029 | https://docs.aleph.occrp.org/users/investigations/network-diagrams/ |
| Q030 | https://scholia.toolforge.org/ |
| Q031 | https://www.sigmajs.org/ |
| Q032 | https://js.cytoscape.org/#performance |
| Q033 | https://github.com/cosmograph-org/cosmos |
| Q034 | https://graphology.github.io/ |
| Q035 | WebSearch: Cytoscape.js WebGL renderer preview (lead only) |
| Q036 | https://reasonator.toolforge.org/?q=Q42 (JS shell) |
| Q037 | https://www.mediawiki.org/wiki/Wikidata_Query_Service/User_Manual |
| Q038 | https://blog.js.cytoscape.org/2025/01/13/webgl-preview/ |
| Q039 | https://graphcommons.com/ |
| Q040 | https://kumu.io/pricing |
| Q041 | https://doc.linkurious.com/user-manual/latest/ |
| Q042 | https://dig.cmu.edu/data-navigator/ |
| Q043 | https://www.w3.org/WAI/tutorials/images/complex/ |
| Q044 | https://aleph.occrp.org/ (empty to fetcher) |
| Q045 | https://api.opensanctions.org/ (JS shell) |
| Q046 | https://www.opensanctions.org/docs/api/ |
| Q047 | WebSearch: OCCRP Aleph Pro (lead only) |
| Q048 | https://pagefind.app/ |
| Q049 | https://docs.orama.com/docs/orama-js (navigation only) |
| Q050 | https://github.com/oramasearch/orama |
| Q051 | https://www.occrp.org/en/announcement/aleph-pro-frequently-asked-questions-on-the-future-of-occrps-investigative-data-platform |
| Q052 | WebSearch: Pagefind large site limits (lead only) |
| Q053 | https://www.sqlite.org/fts5.html |
| Q054 | https://discourse.gohugo.io/t/scaling-pagefind-to-over-1-million-pages/56109 |
| Q055 | https://phiresky.github.io/blog/2021/hosting-sqlite-databases-on-github-pages/ |
| Q056 | https://typesense.org/docs/guide/system-requirements.html |
| Q057 | https://www.meilisearch.com/pricing |
| Q058 | https://atlasofsurveillance.org/ |
| Q059 | https://deflock.me/ (301 → deflock.org) |
| Q060 | https://alpr.watch/ |
| Q061 | https://eyesonflock.com/ (title only) |
| Q062 | https://www.surveillancewatch.io/ (title only) |
| Q063 | https://deflock.org/ (JS shell) |
| Q064 | https://atlasofsurveillance.org/search |
| Q065 | https://github.com/FoggedLens/deflock |
| Q066 | https://www.wikidata.org/wiki/Help:Ranking |
| Q067 | https://opencorporates.com/companies/gb/00102498 |
| Q068 | https://projects.propublica.org/nonprofits/organizations/131624100 |
| Q069 | https://offshoreleaks.icij.org/nodes/10000001 |
| Q070 | https://www.opensanctions.org/search/?q=flock |
| Q071 | https://leafletjs.com/ |
| Q072 | WebSearch: Neo4j Bloom scene node limit (lead only) |
| Q073 | https://neo4j.com/blog/developer/fetching-large-amount-data-neo4j-reactive-driver-the-bloom-case/ |
| Q074 | https://www.gov.uk/service-manual/technology/using-progressive-enhancement |
| Q075 | https://docs.astro.build/en/concepts/islands/ |
| Q076 | https://webaim.org/projects/million/ |
| Q077 | https://developers.google.com/search/docs/crawling-indexing/javascript/javascript-seo-basics |
| Q078 | https://webaim.org/projects/million/ (framework table, second prompt) |
| Q079 | https://ourworldindata.org/grapher/life-expectancy |
| Q080 | https://www.wikidata.org/wiki/Help:Merge |
| Q081 | https://osmfoundation.org/wiki/Licence/Attribution_Guidelines |
| Q082 | https://github.com/felt/tippecanoe |
| Q083 | https://pagefind.app/docs/filtering/ |
| Q084 | https://pagefind.app/docs/multisite/ |
| Q085 | https://infrequently.org/2024/01/performance-inequality-gap-2024/ |
| Q086 | https://www.w3.org/WAI/ARIA/apg/patterns/combobox/ |
| Q087 | https://docs.datasette.io/en/stable/facets.html |
| Q088 | https://docs.openalex.org/how-to-use-the-api/get-lists-of-entities/autocomplete-entities (301, not followed) |
| Q089 | https://developers.cloudflare.com/r2/pricing/ |
| Q090 | https://github.com/hyperknot/openfreemap |
| Q091 | https://www.kaggle.com/docs/datasets (title only) |
| Q092 | https://maplibre.org/maplibre-gl-js/docs/API/classes/KeyboardHandler/ |
| Q093 | https://github.com/lucaong/minisearch |
| Q094 | https://github.com/komoot/photon |
| Q095 | https://www.wikidata.org/w/api.php?action=wbsearchentities&search=Flock%20Safety&language=en&format=json&limit=5 |
| Q096 | https://github.com/alphagov/accessible-autocomplete |
| Q097 | https://atlasofsurveillance.org/atlas |
| Q098 | WebSearch: Kumu performance large maps (lead only) |
| Q099 | https://github.com/typesense/typesense |
| Q100 | https://github.com/public-accountability/littlesis-rails |
| Q101 | https://www.wikidata.org/wiki/Wikidata:SPARQL_query_service/Wikidata_Query_Help/Result_Views |
| Q102 | https://docs.kumu.io/frequently-asked-questions/how-much-data-can-kumu-handle |
