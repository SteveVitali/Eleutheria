# K1 — The map (operator ask U-003.1)

- **Row:** K1 (Stream K, design) · **Written:** 2026-09-30 (work window 22:08Z–22:40Z, `date -u`)
- **Worktree HEAD at write time:** `b6b3d970` (branch `claude/next-phase-planning`). `web/`, `exports/` and `ops/` are
  byte-identical to chain tip `b051732c` (`git diff --stat b051732c HEAD -- web exports ops` is empty), so every `code`
  citation below is also a chain-tip citation.
- **Operator ask, verbatim (U-003.1):** "the current Infrastructure map at "/map" does not even display a map layer so it's just
  a zoomable pane with a bunch of dots on it with no indication of where those dots actually are".
- **Binding inputs:** `design/K0-interactive-architecture.md` (T2 map ≤ 360 KiB gzip initial JS; no-JS rule §4.4; dependency
  allow-list §4.7; `sig.workspace-state/2` §4.5; accessibility contract §4.9; K1 guidance §8). META_PLAN §3 (P1–P16) and
  U-008's ≤ $300/month ceiling.
- **Other inputs read:** META_PLAN Stream K and §7.1; `research/K12a-prior-art.md` §1, §2, §6, §8, §9 (cited as K12a [Qnnn]);
  `review/JOURNEYS.md` (C2: P6, P12, §6.2, §6.3); `review/K12b-explorability.md` §1, §5, A7/A8, F-02/F-04, ideas I-03/I-16/I-17,
  and `findings/incoming/K12b.csv` NEW-6/7/8/9/20; `review/DATA_TRUTH.md` §4.8–4.9; `findings/FINDINGS.csv` F-100, F-114, F-115,
  F-123, F-134, F-155, F-325; `design/K4-dossier-index.md` §3, §4, §5.4, §6, §7, §9; `design/K10-source-pages.md` §3;
  `design/J3-transparency-design.md` (G-11, G-12, TX-10/11/13, D-J3-4); `design/G3-release-model.md` §4.2, §5;
  `research/F5-eng-debt.md` PKG-03/04/06/07/08; `research/G1-ops.md` (traffic, egress, front door); `research/J1-exposure-inventory.md`
  §2. Code: `web/src/islands/MapIsland.tsx`, `web/src/lib/{map,map-tiles,workspace-state}.ts`, `web/src/pages/map.astro`,
  `exports/src/exports/{tiles,formats,analytics,spine_export}.py`, `ops/web/nginx.conf`, `ops/Dockerfile`,
  `tests/exports/test_tiles.py`, `web/tests/e2e/island-budgets.json`, `docs/build/reports/p32.15-island-budgets.md`, ADR-118,
  spec §19.4–19.6, SIG-UI-016…020, SIG-UI-038/047, SIG-FIND-004. `research/L1-*` does not exist yet (skipped, as instructed).
- **Evidence classes (P1):** `code` (file:line at `b6b3d970`); `recorded-execution` (commands run for this row, §15);
  `live-read` (GETs of the live site, the public bucket, and third-party documentation, each stamped). Every cost, future size
  and user-behaviour statement is **`inference`** and labelled.
- **Status vocabulary (P5):** nothing here is engineered. This is a design, a set of draft requirements and a ticket outline;
  the ADR in §10 is agent-drafted for T1 to number and the operator to ratify.
- **P3 / P14 / P16:** production was only read. The 12 live tile archives (42.5 MB) and one public-bucket file were downloaded
  into the session scratchpad and hashed against the release manifest. The Protomaps planet build was read with 7 HTTP range
  requests (headers and directories only). Four asset GETs went to `protomaps.github.io` and one to GitHub raw; two
  documentation pages came from `developers.cloudflare.com`. Every request used curl's default User-Agent and carried no operator
  identity. Headless Chromium rendered the downloaded archives **locally**; no browser load hit the live site. No secrets.
- **Writes:** this file and `findings/incoming/K1.csv` only.

---

## 0. The design on one page

**What is wrong.** Two defects together produce "a zoomable pane with a bunch of dots":

- **There is no basemap** (Round-9 Q8, ADR-118 §Decision 2).
- **Most dots are missing.** The live overlay tiles hold only a thinned sample of the sites below zoom 14. tippecanoe
  2.79.0 runs with its defaults: base zoom = max zoom 14 and drop rate 2.5. So z12 holds **25.6 %** of the 227,335 published
  points, z10 holds **5.7 %** and the national z3 view holds **76 points in the world**. Nothing stands in for the dropped
  points. A local render of the live archives draws **19 of the 203,042 sites** in the US view.

The page tells the reader that national zoom "bins density". That code exists but is never called (§1.1).

**What we build (T2 surface under K0):**

| area | decision |
|---|---|
| Basemap | **Self-hosted Protomaps PMTiles** (OpenStreetMap-derived, ODbL), served from a SIG-controlled origin. It stays its own archive and is never merged with SIG data. **Host (D-K1-2):** R2 on `tiles.surveillancegraph.org` once the DNS zone moves to Cloudflare (the same move J3 TX-11 needs; NEW-5). Otherwise a same-origin GCS backend bucket. Light and dark styles are generated at build. Glyphs are self-hosted (Noto, OFL). No POI sprites. **Fallback:** a SIG-hosted, public-domain boundaries and place-name layer, plus a visible notice. |
| Monthly cost (inference, §2.4) | **R2:** ≈ $2 at 1k sessions/month, ≈ $3 at 10k, ≈ $13 at 100k. **GCS:** ≈ $2, ≈ $6 and ≈ $43. Both are far inside U-008's $300. |
| Overlay tiles | Still one archive per licence compartment, now with **two layers**. `cells` holds H3 count cells for z0–9 (per-compartment counts that the client sums at render). `sites` holds **every** point from z10 (`-r1`, precomputed per-feature zoom ranges, no dropping). A new CI verifier proves count conservation and renderer parity. |
| Honest rendering | Filled symbol = corroborated (≥ 2 sources). Hollow = single source. Double ring = contested. Tier-1 records draw an uncertainty ring. Tier-2 records draw as their published H3 area. Tier-3 records are never drawn; they appear as jurisdiction indicators. Colour always has a second channel. |
| Interaction | Place search (the K4 registry plus a GeoNames subset, as static typeahead shards via K3's `<sig-typeahead>`). Filters: technology, vendor, agency, source, licence, seen-date, status. An HTML legend. A selection panel with links to the record/entity, source, dossier, evidence, cite and dispute pages. A synchronized "sites in view" list that is also the keyboard and screen-reader path. `at=` viewport and all filters in `sig.workspace-state/2`. A desktop side panel and a mobile bottom sheet. |
| No-JS | `/map/` becomes a ≤ 100 KiB page. It holds a build-time SVG overview (bins over state and country outlines), a place form and a table of places. It links per-jurisdiction site lists `/dossier/<path>/sites/` (≤ 100 rows per page). These replace the 3.43 MB, 1,504-row page and its 5,290 dead gap links. |
| Performance | 497 KB → **≈ 345 KiB** gzip initial JS. Load MapLibre as its ESM split, move to Preact, build the style as JSON rather than JS, and keep the app under 40 KiB. The first view measures ≈ 0.6–0.9 MiB of tiles and glyphs (budget 1.5 MiB). Lighthouse mobile ≥ 0.75 on the real release. |
| ADR | The map ADR (§10) reverses Round-9 Q8 and supersedes ADR-118 §Decision 2 (it acts on that ADR's own revisit trigger (a), "costed self-hosted extract"). It extends SIG-GEO-012 with the two-layer, count-conserving tile contract and strikes SIG-FIND-004's "no-basemap decision remain[s] in force". |

**Tickets (§12):** MAP-00 ADR + spec (S) → MAP-01a tile retention and verifier (M) → MAP-02 basemap pipeline and host (M) →
MAP-03a app shell (M) → MAP-03b filters, list, a11y, mobile (M) → MAP-04 place search (S) → MAP-05 no-JS baseline (M) →
MAP-01b tile properties v2 (M) → MAP-06 bbox API (S) → MAP-07 acceptance and republish (S).

---

## 1. What is wrong today (evidence)

### 1.1 The "missing cameras at street zoom" defect — root cause (measured)

**Symptom (C2 F-100 = C2 NEW-9, S1; K12b A7):**

- About 20 dots show for "227335 located records".
- The frame is blank at z10 and z12 on the exact coordinate of a camera that the page's own table lists (I-80 MM 82.5, Iowa).
- Austin at "z15" showed "about 8 dots".
- F-100 left the cause open: "tile content vs rendering … C3 should trace the PMTiles feature counts".

**Trace.** I downloaded the 12 live `web/tiles/<compartment>-sites.pmtiles` archives at 22:10:48–22:11:05Z. All 12 sha256 hashes
equal the manifest of release `sig-2026-09-27-ce480ab1`. I then decoded every directory and tile with a stdlib PMTiles/MVT
reader (§15 C3–C5).

| zoom | unique published points present in tiles (of 227,335) | share |
|---:|---:|---:|
| 0 | 12 | 0.01 % |
| 3 | 76 | 0.03 % |
| 6 | 469 | 0.21 % |
| 9 | 5,572 | 2.45 % |
| 10 | 12,877 | 5.66 % |
| 11 | 27,995 | 12.31 % |
| 12 | 58,134 | 25.57 % |
| 13 | 118,299 | 52.04 % |
| 14 | 227,335 | 100 % |

- Every archive's metadata says `generator: tippecanoe v2.79.0`, `minzoom 0`, `maxzoom 14`.
- Each zoom keeps ≈ 1/2.1–1/2.5 of the next zoom's points. That is tippecanoe's documented default: base zoom = max zoom and
  drop rate 2.5 (K12a [Q082] lists the flags that change it).
- The export calls tippecanoe with none of those flags: `-o -Z 0 -z 14 -l sites --force --attribution`
  (`exports/src/exports/tiles.py:621-639`).
- No cluster count or bin replaces a dropped point.

**Rendering proof (local, `recorded-execution`, 22:17:02Z).**

- **Setup.** MapLibre 6.9.0 and PMTiles 4.5.0 from `web/node_modules`, headless Chromium (SwiftShader) and a 950×384 canvas
  (the live canvas size, K12b NEW-8). The page used the island's exact style: a background plus 12 circle layers
  (`MapIsland.tsx:136-155, 244-259`). A local range server served the downloaded archives.
- **What "drawn" counts.** `queryRenderedFeatures()` unique ids.
- **What "published in view" counts.** The z14 point set inside `getBounds()`.

| view | zoom | drawn | published in view | nearest drawn feature to the target |
|---|---:|---:|---:|---:|
| US national | 3 | **19** | 203,042 | 412 km |
| US (centre KS) | 6 | 5 | 4,327 | 80 km |
| I-80 MM 82.5, IA | 10 | 2 | 48 | 23 km |
| I-80 MM 82.5, IA | 12 | 5 | 14 | 2.2 km (the camera is absent) |
| I-80 MM 82.5, IA | 13 | 3 | 4 | 1 m (present) |
| I-80 MM 82.5, IA | 14 | 2 | 2 | 0 m |
| Austin, Congress Ave / 6th St | 12 | 72 | 436 | 195 m |
| Austin, Congress Ave / 6th St | 14 | 137 | 131 | 23 m |
| Canberra city centre | 12 | 27 | 163 | 642 m |
| Canberra city centre | 14 | 19 | 19 | 179 m |

**Conclusion.** The tiles are the cause, not the renderer.

- A given camera is absent below z13 with probability ≈ 1 − 1/2.5^(14−z). At z12 that is 74 %.
- It is present in every tile from z14. MapLibre overzooms z14 to z15+.
- C2's "about 20 dots" and K12b's "about 18 dots" are the z3 sample (19 in my render).

**Contributing causes:**

1. **The island ignores its own rules.** `renderModeForZoom`, `pointVisibleAtZoom` and `MIN_POINT_ZOOM_BY_TIER`
   (`web/src/lib/map.ts:309-340`) exist, but no file in `web/src/` calls them. The island draws raw circles at every zoom
   (`MapIsland.tsx:244-266`). The page still says "At national zoom (≤ 6) the map bins density" (`map.astro:182-185`).
   H3 bins exist only as a restricted build input (`analytics.py:185-275`) and a 64,128-px SVG strip (F-114).
2. **Nothing tests what production renders.** CI never runs tippecanoe: `test_tiles.py:198` monkeypatches it. The pure-Python
   fallback keeps every point at every zoom but coalesces co-located entities (`tiles.py:56, 326-340`). The committed
   fixtures draw through client GeoJSON clustering instead (`MapIsland.tsx:301-317`). So no test or fixture build can see the
   production thinning (**NEW-2**).
3. **Without a basemap, testers cannot verify where they are.** C2's blank Canberra z12 frame is byte-identical to its Iowa
   frame. The Canberra z12 tile holds 40 features and my render draws 27 there. So that frame was probably not at Canberra
   (*inference*). The attribution block also swallows double-clicks in the bottom 100 px (K12b NEW-8).

### 1.2 Other defects the design must fix

| # | defect | evidence | fixed in |
|---|---|---|---|
| D1 | No basemap, place labels or geocoder | Q8; `map-tiles.ts:14-15, 69-88`; C2 P6-T1/T2, P12-T2 **fail** | §2, §4.2 |
| D2 | Popups are dead ends: UUID title, "unresolved", no type/operator/source/date/link; "Cite this view" cites the national map | K12b NEW-6; `MapIsland.tsx:122-134` | §4.5 |
| D3 | The popup shows "Sensitivity tier 0" from a default: tiles carry no tier (`TILE_RENDER_PROPERTIES` keeps `sensitivity_tier`, rows carry `tier`; 0 of 227,335 tile features carry it) | `tiles.py:645-652`; `MapIsland.tsx:282`; §15 C5 | §3.3 (**NEW-3**) |
| D4 | Layers are inert labels; derived layers are described but absent | F-114 (C2 NEW-23); DATA_TRUTH §4.8 | §3.6, §4.4 |
| D5 | 5,290 "⚠ Unresolved" links → 404 | K12b NEW-7 | §5 |
| D6 | Features are not keyboard-operable; Escape does not close the popup | K12b NEW-9; C2 §6.3 | §4.7 |
| D7 | Attribution overlays 100 of 384 px and eats clicks; mobile lower third | K12b NEW-8; F-123 (C2 NEW-32) | §4.1 |
| D8 | Attribution credits third-party share-alike and OGL data to "SIG contributors" | F-134 (C3 NEW-9) | PKG-08 → §2.3 |
| D9 | 3.43 MB HTML (271 KB transferred), 816 KB total, mobile perf 0.86 / LCP 2.23 s / TBT 352 ms; 497 KB gzip script (fixtures) | F-115; C2 §6.2; `p32.15-island-budgets.md` | §6 |
| D10 | Intro copy says "no client JavaScript" above a JS map | K12b NEW-20 | §5 |
| D11 | 73.1 % of tile features have jurisdiction "unresolved"; 82.4 % have no label; all are `deployment`; no technology field | §15 C5; F-325; K0 NEW-1; K4 | MAP-01b ← JUR-02b, PKG-07, K2 labels |
| D12 | Tiles are overwritten in place under `/tiles/` (`max-age=300`), so a map view cannot be cited against a release | `nginx.conf:104-110`; ADR-118 trigger (d) | §3.1 (G3 serving) |
| D13 | The bundle's `<compartment>/sites.pmtiles` downloads contain **zero tiles**: the GeoJSON sits inside the archive metadata | `formats.py:245-298`; §15 C9 | **NEW-4** → J3 TX-10 |

---

## 2. Basemap

### 2.1 Options

| option | cost (§2.4) | privacy / third-party exposure | licence | ops | verdict |
|---|---|---|---|---|---|
| **A. Protomaps planet build, self-hosted on R2** (`tiles.surveillancegraph.org`) | ≈ $2–13/mo | visitors hit a SIG-controlled hostname; Cloudflare is an infrastructure processor, like Google is today | ODbL tiles, CC0 style, OFL fonts, MIT sprites | needs the DNS zone on Cloudflare (NEW-5); refresh job | **recommended** if D-K1-2 = move DNS |
| **B. Protomaps z0–14 extract on GCS**, same origin via the existing LB backend bucket (`/basemap/`) | ≈ $2–43/mo | same origin; no new vendor; no CORS | same | no DNS change; exposure to denial of wallet → budget alert (G1 QA-10) and optional Cloud Armor | **recommended fallback**; fine below ≈ 30k sessions/month |
| C. OpenFreeMap public instance | $0 | third-party origin sees every viewport; "no SLA" (K12a [Q010]) | ODbL | none | rejected: I-6 (K0) and ADR-118 Q8(c) |
| D. Stadia / MapTiler free tiers | $0 → paid | third party; free tiers are **non-commercial** (K12a [Q012], [Q013]) | per vendor | keys | rejected |
| E. OSMF tiles / Nominatim | $0 | third party; policies forbid this use (K12a [Q011], [Q017]) | ODbL | — | rejected |
| F. Keep no basemap; boundaries only | $0 | none | public domain | small | rejected as the default (U-003.1); **kept as the fallback** (§2.6) |

**Measured basemap facts (`live-read`, 22:14:52–22:15:34Z).**

- Protomaps build `20260930.pmtiles`: **138,478,612,042 B** (138.5 GB), z0–15, basemap schema v4.15.2, 136,127,655 unique
  tile contents.
- Tile weight per first view, summing the directory lengths (gzip, as served) for 512-px tiles:

| view | tiles | bytes |
|---|---:|---:|
| US national, desktop 1440×700, z3 | 8 | 362 KiB |
| US national, mobile 390×600, z3 | 4 | 257 KiB |
| Texas, z6 | 8 | 257 KiB |
| Chicago, z11 | 6 | 252 KiB |
| Austin downtown, z12 | 12 | 618 KiB |
| Austin downtown, desktop, z14 | 12 | 647 KiB |
| Austin downtown, mobile, z14 | 3 | 200 KiB |
| rural Iowa, z12 | 6 | 28 KiB |

- The largest single tile seen is 84 KiB.
- Glyphs: `Noto Sans Regular/0-255.pbf` is 76,044 B raw / 45,956 B gzip; Medium is 77,628 / 46,727. Sprite `light.png` is
  16,174 B; `light.json` is 3,549 B.
- `basemaps-assets` licences: fonts **SIL OFL**; sprites "derived from MIT-licensed tangrams/icons" (README, 22:16:06Z).

### 2.2 Choice and parameters

- **Archive.**
  - R2: the whole planet build, z0–15. At ≈ $1.93/month there is no reason to cut it. MapLibre overzooms z15 for street
    detail.
  - GCS: a `pmtiles extract --maxzoom=14` of the pinned build. Each zoom roughly doubles the size, so ≈ 69 GB (*inference*,
    K12a [Q009]).
  - Pin the build date and b3sum in `basemap.lock.json`: build, schema version, size, b3sum, `@protomaps/basemaps` version,
    `extracted_at`. The style package must match the tile schema (v4 tiles ↔ `@protomaps/basemaps` 5.x; the ticket verifies
    this).
- **Refresh.** Twice a year, or on a MapLibre/basemaps upgrade. It is a manual `sig-ops basemap refresh` with a dry run: fetch,
  verify the b3sum, upload under a new versioned key, flip the style's URL, and keep the previous key for 30 days.
  - On GCS the refresh costs only minutes of compute (ingress is free).
  - On R2, run it outside GCP. Run from GCP, the upload costs ≈ 138.5 GB × $0.12 ≈ $17 per refresh (*inference*,
    J4 unit price).
- **Serving.** PMTiles range reads straight from the object (no Worker).
  - This keeps SIG-GEO-012's "no dynamic tile server as a hard dependency". A Cloudflare Worker that decodes z/x/y for edge
    caching is an optional later step, only if measured tile latency needs it. It is not a dependency: the client can always
    read the archive directly.
  - Headers:
    - CORS `GET, HEAD` from the site origin, allowing the `Range` request header and exposing `Content-Range`, `ETag` and
      `Content-Length`.
    - `Cache-Control: public, max-age=31536000, immutable` on versioned keys.
    - Rate limiting (R2: a free-plan WAF rate rule; GCS: optional Cloud Armor).
    - The CSP `connect-src` adds the tile origin (K0 §4.8).
- **Not merged, not a release input.** The basemap is context, not SIG data. It stays out of descriptor v2. Its build id is
  shown in the map's "About this map" note and recorded in `release.json` as `basemap_build` for honesty. A snapshot view
  therefore reproduces SIG's facts exactly over whatever basemap is current, and the page says so.

### 2.3 Licence and attribution (agent-drafted text)

- **Interactive map, desktop.** An attribution strip **below** the canvas, never over it:
  > Basemap © [OpenStreetMap contributors](https://www.openstreetmap.org/copyright) (ODbL) · [Protomaps](https://protomaps.com) ·
  > Site data: © OpenStreetMap contributors (ODbL); {per-compartment upstream holders from PKG-08, each linked to `/sources/<id>/`} ·
  > Compilation © SIG (CC BY 4.0) · [About this map](#about)
- **Mobile.** A 44×44 "ⓘ Map credits" button opens the same text in the bottom sheet. OSMF permits collapse to an "(i)"
  if the licence stays findable (K12a [Q081]).
- **Credit OSM once.** The ODbL site layer (`osm_physical`) and the basemap share one OSM credit.
- **"About this map" note** (also in print):
  > The basemap is an extract of the Protomaps daily build {date} (OpenStreetMap data, ODbL 1.0), served unmodified except for
  > zoom range by SIG. Its style is CC0, its fonts (Noto Sans) are under the SIL Open Font License. Download the basemap archive
  > (ODbL): {link}.
  - Offering the extract under ODbL satisfies share-alike for a derivative database, if an extract counts as one
    (*inference*; E-stream confirms).
- **Static SVG and print** (§5):
  > Boundaries: U.S. Census Bureau, Natural Earth (public domain). Site data: © OpenStreetMap contributors (ODbL); {holders}. Map
  > rendered by SIG.
  - This satisfies SIG-GEO-013 "in every rendering context".
- **Licence files served next to the assets:** `fonts/OFL.txt`, `LICENSE-sprites` (only if sprites are ever used),
  `LICENSE-style` (CC0), `ODbL-1.0.txt`.

### 2.4 Cost (monthly; **inference** from cited unit prices)

**Unit prices:**
- R2: $0.015/GB-month beyond 10 GB free; Class B $0.36/M beyond 10 M/month; egress $0 (K12a [Q089]).
- GCS: storage ≈ $0.020/GB-month; operations ≈ $0.0004 per 1,000 reads; internet egress ≈ $0.12/GB (J4, secondary); LB
  processing ≈ $0.008/GB (G1 §3.8).

**Assumptions:**
- An engaged session moves ≈ 2 MiB of basemap: the measured first view (0.26–0.65 MiB), glyphs (≈ 0.14 MiB) and about ten pans
  or zooms.
- Overlays add ≈ 0.3 MiB (§6.2) and app assets ≈ 0.4 MiB, the latter on first visit only.
- ≈ 150 tile reads per session.
- Today's traffic is 392–2,321 successful LB requests a day for the whole site and ≈ 0.1 GB/day egress (G1). So 1k map
  sessions/month is today's order of magnitude; 10k and 100k are post-announcement scenarios (U-009).

| item | 1k sessions | 10k | 100k |
|---|---:|---:|---:|
| **A. R2** storage (138.5 GB planet) | $1.93 | $1.93 | $1.93 |
| R2 Class B reads | $0 | $0 (1.5 M) | $1.80 (15 M) |
| overlays + assets via existing GCS/LB (≈ 0.73 MB/session) | $0.09 | $0.94 | $9.40 |
| **A total** | **≈ $2** | **≈ $3** | **≈ $13** |
| **B. GCS** storage (≈ 69 GB z0–14) | $1.38 | $1.38 | $1.38 |
| GCS reads | $0.06 | $0.60 | $6.00 |
| egress + LB (≈ 2.83 MB/session) | $0.36 | $3.62 | $36.2 |
| **B total** | **≈ $2** | **≈ $6** | **≈ $43** |
| optional Cloud Armor rate limit (B only; unit prices not re-read) | +≈ $6–7 | +≈ $6–7 | +≈ $6–7 |

**Denial of wallet.**
- On B, one full scrape of the 69 GB archive costs ≈ $8.8. A scraper doing ten a day would cost ≈ $2,600/month (*inference*).
  B therefore **requires** G1's budget alert, with a kill switch that points the style at the boundaries fallback.
- On A, egress is free and reads cost $0.36/M. Downloading the whole archive in a few large ranges costs cents. Scraping it tile
  by tile is ≈ 136 M reads ≈ $49 (*inference*). A WAF rate rule bounds both.

### 2.5 Style

- **Build, not runtime.** `web/scripts/gen-map-styles.mjs` imports the pinned `@protomaps/basemaps` at build time and emits
  `/map/style-light.json` and `/map/style-dark.json`. The existing `/map/style.json` becomes an alias of light. The style
  package never ships as JS: 6.7 KiB saved (K0 §2.1).
- **Flavours.** A low-chroma light flavour ("grayscale" or "white") and a dark flavour ("black" or "dark"), so SIG's categorical
  data colours carry the meaning. K14 picks the final flavour and tokens. Flavour names are verified against the pinned
  package. Theme follows `prefers-color-scheme` and K14's `data-theme`; switching uses `setStyle(…, {diff: true})`.
- **Layer order:**
  1. basemap fills and lines;
  2. SIG coverage hatch;
  3. SIG cells and points;
  4. basemap labels, with text halo;
  5. the SIG selection highlight.

  Place labels stay legible over dense points. The selected site always sits on top.
- **Content:**
  - Keep: earth, water, muted landcover, roads (casing from z11), admin boundaries, place labels (country, region, locality),
    road labels from z13, water labels.
  - Drop: POIs (so no sprite download), transit and 3-D buildings.
  - Buildings only from z15, at low contrast.
  - Labels in English with the local name as fallback (`lang: "en"`).
- **Contrast (WCAG 1.4.11, SIG-UI-005).** `web/scripts/check-map-contrast.mjs` reads every fill and line colour of both
  generated styles. It asserts ≥ 3:1 between the SIG symbol stroke and every basemap fill, and ≥ 4.5:1 for label text against
  its halo. Symbol strokes use a dark ink (`#1a1a1a`) on light and a light ink (`#f2f2f2`) on dark. The check runs in CI.
- **Reduced motion.** No `flyTo` or `easeTo` (always `jumpTo`), no animated transitions, no pulsing selection.

### 2.6 Fallback when the basemap fails

- **Detection:**
  - a MapLibre `error` event whose `sourceId` is the basemap;
  - or no basemap tile loaded 6 s after `load`;
  - or `basemap=0` in the URL (a user choice for privacy or bandwidth).
- **Behaviour.** Swap to the **context fallback**, `context.pmtiles` on the SIG web origin, never on the basemap host:
  - state, county and country outlines from K4's display boundaries (Census CB 500k, Natural Earth 10m; public domain;
    JUR-01);
  - the K4 registry's internal points with names as labels;
  - z0–10, ≈ 3–6 MB (*inference* from K4 §4.1 sizes).

  Show a `role=status` notice: "The street basemap could not load. Showing boundaries only; every site is still drawn."
- **If the context file also fails:** a plain background plus the notice. The data layers never depend on either base layer.
- **Test:** e2e journey J7 (§9.3).

---

## 3. Data layers and the overlay tile contract v2

### 3.1 Archives, layers, zoom bands

**Archives.** One archive per licence compartment, as SIG-GEO-012 and ADR-118 already require:
`<compartment>-sites.pmtiles`, never merged. Each archive holds two layers.

| layer | zooms | geometry | what it represents |
|---|---|---|---|
| `cells` | z0–9 | point at the H3 cell's mean published position (after the tier transform, SIG-GEO-010) | the count of this compartment's published located records in the cell, plus facet counts |
| `sites` | tier 0 from z10; tier 1 from z11; tier 2 from z12 (as its H3 polygon); tier 3 never | point (tiers 0–1), polygon (tier 2) | one feature per published located record, **none dropped** |

**H3 resolution per band.** z0–4 → res 3; z5–6 → res 4; z7–8 → res 5; z9 → res 6.
- Per-compartment cell features for the live data: 1,511 / 5,028 / 13,691 / 30,973 (§15 C8).
- Cell size on screen is ≈ 12–45 px across the band.
- The band table is a parameter. MAP-03's visual test tunes it.

**The point zoom moves from 7 to 10.** `NATIONAL_ZOOM_MAX = 6` becomes 9, because at z7–9 a region holds 10⁴–10⁵ points: too
dense to read and too heavy to ship. The densest per-compartment z10 tile, after the change, holds **2,348 points**
(`osm_physical` 10/240/423, Houston). At the measured ≈ 40–60 B per point that is ≈ 100–140 KB, under tippecanoe's 500 KB tile
cap (*inference*).

**Retention rule.**
- The exporter writes each feature's zoom range as a `"tippecanoe": {"minzoom", "maxzoom"}` member in the GeoJSON.
- tippecanoe runs with `-r1` (no rate dropping). `--drop-densest-as-needed`, `--drop-fraction-as-needed` and `--coalesce*` are
  **forbidden**.
- An over-size tile makes the export **fail loudly**, never silently thin.
- The pure-Python renderer honours the same ranges. It stops coalescing distinct entities that share a cell (`tiles.py:56`). It
  dedupes only byte-identical features.

**Release-pinned paths.** Under G3, `/tiles/` is served from `v/<pub>/` and `/s/<pub>/tiles/` from the snapshot (G3 §4.2).
- Tile URLs resolve through `withBase()` (G3 NEW-6), so a cited snapshot reads its own tiles.
- File names carry the content hash (`<compartment>-sites.<sha8>.pmtiles`), so nginx can send `immutable`. This fixes D12.

**Growth estimate.** Retaining all points at z10–13 roughly triples point bytes: 42.2 MB today (z14 = 19.2 MB, 45 %) → **≈ 90–110
MB per release** with cells and the §3.3 properties (*inference* from §15 C6). That is negligible for storage and for per-view
transfer.

### 3.2 Why counts are summed in the browser

A cross-compartment count file would be a licence-mixed derived database. ADR-106 §4 files those only as *restricted* build
inputs (`analytics.py:20-35`), and a public PMTiles archive is downloadable by anyone. So each archive carries its own
compartment's cell counts.

On each `sourcedata`/`moveend`, the client:
1. collects the visible `cells` features from the **active** compartments (`querySourceFeatures`, deduplicated by
   `(compartment, h3)`);
2. sums `n` and the facet counts by `h3`;
3. writes one in-memory GeoJSON source.

The drawn map is a produced work, like today's composite, and carries every active compartment's attribution.
- Cost: ≤ a few thousand features per view, a few ms (*inference*), ≈ 2 KiB of code.
- Toggling a compartment or a cell-supported filter re-sums instantly.

### 3.3 Feature properties (`sig.map-tiles/2`)

Short keys keep tiles small. The names are the contract; the export's data dictionary (J3 TX-10a) documents them.

| key | layer | type | source of truth | notes |
|---|---|---|---|---|
| `rk` | sites | string | `sig.published-record/1` record_key `<comp>:<type>:<id>` | links record pages; `focus=` |
| `lb` | sites | string | derived label (K0 NEW-1; K2 rule): name if present, else `<technology> · <operator or source short name> · <place>` | never a UUID |
| `tc` | sites, cells (as `t_<code>`) | int | technology code from `dict.json` (ontology `technology.yaml`); `0` = unclassified | PKG-07 |
| `vd` | sites, cells (as `v_<slot>`) | int | vendor slot (top 8 vendors per release + other + unknown) | vendor from claims (OSM `manufacturer`, portal vendor, contracts); K2 resolution |
| `op` | sites | string | operator/agency derived label (per-compartment string, never pooled across licences) | `oe` = operator entity key when resolved (K2) |
| `sr` | sites | int | source index in `dict.json` (SIG registry metadata, CC-BY-4.0) | cells carry `ns` = distinct sources |
| `j` | sites | string | finest K4 key (`us.census.geoid.place:4805000`) or `unplaced` | the chain is in `dict.json`; JUR-02b |
| `f`, `l` | sites | int `yyyymm` | first and last seen (claim valid time) | date filter |
| `st` | sites, cells (`s1`, `sx`) | int | 0 corroborated (≥ 2 independent sources) · 1 single source · 2 contested (open contradiction on location or type) · 3 provisional (candidate lifecycle) | §3.5 |
| `tr` | sites | int | sensitivity tier 0–2 (**the `tier` column**; fixes D3) | tier 3 never tiled |
| `pm` | sites | int | uncertainty radius in metres (tier-1 truncation; the source-declared accuracy; 0 if none) | §3.4 |
| `co` | sites | int | entities in this compartment sharing the exact coordinate (≥ 1) | DATA_TRUTH §4.9: 23,566 share one |
| `h3`, `n`, `ns` | cells | string, int, int | cell id, record count, distinct sources | coverage proxy (`analytics.py:189-207`) |
| `jp` | cells | string | plurality K4 key in the cell | "places in view" list |

`dict.json` (per release, CC-BY-4.0, ≈ 30–60 KB) holds:
- the source index (id, display name, publisher, licence, compartment, `/sources/<id>/` URL);
- the technology codes (label, colour token, glyph);
- the vendor slots (vendor entity key, label);
- the jurisdiction chain for every `j` key that appears.

Upstream data strings (operator names, labels) stay in their own compartment's tiles, never in the shared dictionary.

### 3.4 Precision, uncertainty and Part VIII

| tier (§19.4) | tile content | rendering | list/panel text |
|---|---|---|---|
| 0 | the point as published | a circle | "Location as published by {source}" (+ "± {pm} m" when `pm > 0`) |
| 1 | truncated coordinates | a circle plus a translucent ring of radius `pm` (drawn when ≥ 4 px). The radius comes from a zoom-exponential expression over the precomputed metres-per-pixel at z20. | "Location truncated to ~{pm} m" |
| 2 | the H3 cell polygon at the published resolution | a hex outline, no point | "Location published as an area (~{area} km²)" |
| 3 | nothing | none. The count joins its jurisdiction's "no published point" indicator (SIG-UI-020) | "Location not published" |

**Today's data.**
- All 227,335 published points are `full_precision`, and the spine export publishes only `sensitivity_tier = 0` claims
  (`spine_export.py:166-228`). So tiers 1–2 are latent.
- The contract still ships them so a future Part VIII tier assignment cannot leak through the tiles.
- **Verifier checks:**
  - every tier-1 feature decodes onto its truncation grid;
  - every tier-2 feature is a polygon;
  - no tier-3 record is in any tile;
  - the cell counts are built from tier-transformed coordinates (SIG-GEO-010).

**URL precision (`at=`).** The decimals follow the zoom: z0–2 → 0, 3–5 → 1, 6–8 → 2, 9–11 → 3, 12–14 → 4, ≥ 15 → 5.
- With a focused tier-1 or tier-2 record, the URL never carries more decimals than its published precision.
- The zoom is written to 0.1.
- This is the K0 §4.5 rule made concrete.

### 3.5 Symbols (status, technology, co-location)

| state | cells (z0–9) | sites (z10+) | second channel |
|---|---|---|---|
| ≥ 3 sources in the cell / corroborated site | solid disc, colour ramp by count | solid disc in the technology colour | fill |
| 2 sources / — | half-tone disc | — | lighter fill |
| 1 source / single-source site | **hollow** grey ring with the count ("1 source" in the list) | **hollow** ring in the technology colour | no fill |
| contested (open contradiction on location or type) | — | solid disc + outer ring (a second circle layer, stroke only, radius + 3) | double ring; "Contested" badge in the list and panel |
| provisional (candidate) | — | hollow ring, dashed look via a two-layer offset | the text says "Candidate" |
| co-located (`co > 1`) | — | a "×n" text badge from z14 | text |

- **Hollow means "only one source says so"** at both levels. That makes the coverage proxy visible, so low coverage never reads
  as low density (SIG-UI-018).
- **Counts:** abbreviated labels (`1.2k`) on cells from z5 when the disc is ≥ 24 px.
- **Size:** disc radius ∝ √n, capped.
- **Technology colours:** ≤ 8 categorical colours plus grey "unclassified". K14 tokens; validated for both themes by the §2.5
  contrast check. From z15, a text code ("ALPR", "CCTV") beside each site uses the already-loaded glyphs. Colour is never the
  only channel: the legend, list and panel repeat it in text.

### 3.6 Coverage and "not looked" (bound to points)

- **SIG-UI-017.** Points and coverage keep a single bound control ("Sites + where SIG has looked").
- **Round 11 coverage layer.** A hatched, desaturated overlay on jurisdictions that **no** source covers for the selected
  technologies. It is drawn from the `context.pmtiles` boundaries and a published `coverage_by_jurisdiction.json`:
  `jkey → {sources[], technologies[], basis}`. This is SIG metadata (CC-BY-4.0), not upstream data.
- **The rule for "covers" is a dependency.** It belongs to C3/L3/K9. Proposed minimal rule: a source covers the jurisdictions
  in its declared scope; global crowdsourced sources (OSM/DeFlock) are listed but do **not** count as "looked"; say so in the
  legend. **D-K1-4.**
- **Layers without data are named, not faked.** The legend lists "Field of view (modelled)", "Service areas" and
  "RTCCs and hubs" under "Not yet available", with a one-line reason. No inert toggle (fixes D4).

---

## 4. Interaction design (T2 `/map/`)

### 4.1 Layout

**Desktop (≥ 960 px).**
- A left panel of 380 px with tabs **Search · Filters · In view · Selected**, a legend at the bottom of the panel, and the map
  filling the rest. The map is `calc(100dvh − header)` tall, minimum 520 px.
- Attribution is a strip under the canvas (fixes D7; 2.4.11).
- Controls sit top-right, each ≥ 32×32 px (2.5.8): zoom ±, a pan pad (single-pointer alternative, 2.5.7), reset north only
  if rotation is enabled (rotation is disabled by default), "my location" (D-K1-7), and a basemap toggle.

**Mobile (< 960 px).**
- A full-bleed map under the header and a **bottom sheet** with three snap points:
  - peek, 88 px: "137 sites in view · Filters (2)";
  - half;
  - full.
- The sheet holds the same tabs. The search field sits at the top of the map.
- Controls are ≥ 44×44. Attribution collapses to "ⓘ".
- The sheet never covers the focused element (2.4.11). The map's padding is set to the sheet's height, so `fitBounds` frames
  above it.

**First paint.** SSR renders the panel, the legend and the static SVG overview (§5) into the reserved map box. MapLibre mounts
into that box on `client:idle` (K0 I-2, no `client:only`). CLS stays ≤ 0.05.

### 4.2 Place search and geocoding

**Where names come from.** Static typeahead shards per release, built by K3's `<sig-typeahead>` pipeline, `kind=place`:
- the **K4 jurisdiction registry**: ≈ 13k keys with names, alternates, level, parent chain, bbox and internal point;
  ≈ 0.2 MB gzip in total;
- plus a **non-US cities subset**, either GeoNames cities15000 (CC BY 4.0, attribution in "About this map") or Natural Earth
  populated places (public domain). **D-K1-5.** Either one fixes "Canberra → 0" (C2 NEW-10).

The shards are 2-character prefixes, each ≤ 50 KiB gzip, fetched on the second keystroke. Matching inside a shard uses
MiniSearch (5.9 KiB, K0 allow-list), shared with K3.

**Results** are typed rows ("Travis County, Texas, United States — county — 1,207 sites"). Choosing one:
1. `fitBounds(bbox)`;
2. sets `jurisdiction=<jkey>` in the URL;
3. offers "Filter to this place" (a facet) as well as "Show this area" (framing).

**Also supported:**
- **Coordinates.** "41.4959, -94.5205" (or with a hemisphere letter) parses locally and jumps. No request is made.
- **ZIP codes.** Later (JUR-07): a server redirect route, no logging.
- **Street addresses: not in Round 11.** No address geocoder (Part VIII; K12a §2.4). This is an explicit non-goal with a revisit
  trigger.
- **"My location"** (D-K1-7). Only after an explicit click. `navigator.geolocation` stays in the browser and the position never
  leaves it. The URL gets only the zoom-rounded `at=`. `Permissions-Policy: geolocation=(self)` is set on `/map/` only
  (K0 §4.8).

**Privacy note (inference).**
- A shard fetch reveals a 2-character prefix to SIG's logs, and never to a third party.
- **The no-JS path** is `<form method="get" action="/map/place/">`. It resolves to a static page: a K4 A–Z directory filtered to
  the prefix, then the dossier or the §5 site list. When K3's API search is wired (F-155, PKG-04), it uses that.

### 4.3 Filters

| filter | values | at z10+ (sites) | at z0–9 (cells) | URL |
|---|---|---|---|---|
| Technology | ontology classes + "unclassified" (counts) | `tc` | `t_<code>` sums | `technology=` (repeated) |
| Vendor | top 8 + "other" + "unknown" (typeahead for the rest) | `vd` | `v_<slot>` sums; non-top vendors → "zoom in or see list" note | `vendor=` (entity key) |
| Agency / operator | typeahead over resolved operator entities (K2) | `oe` | not aggregated: selecting an agency **frames its footprint** (bbox from `dict.json`) and filters sites | `operator=` |
| Source | 178 site sources grouped by publisher, with licence | `sr` | `ns` cannot be sliced per source, so a source filter at z0–9 falls back to that source's compartment cells, labelled "approximate below zoom 10" | `source=` |
| Licence compartment | 12 compartments | layer visibility | layer inclusion in the sum | `collection=` (v1 semantics kept) |
| Seen | month range + "include removed" | `f`, `l` | disabled below z10, with the note "date filtering applies from zoom 10" | `seen=2024-01..2026-09` |
| Status | corroborated · single-source · contested · provisional | `st` | `s1`/`sx` | `status=` |

- **Every filter shows counts:** in-view counts from tiles, and national counts from `dict.json` totals.
- **Honesty rule.** When a filter cannot apply at the current zoom, the cells turn grey and hatched with the note: "Vendor filter
  applies from zoom 10 — N matching sites nationwide are listed in Search." That links `/search/?kind=site&vendor=…` (K3).
  The map never shows unfiltered counts as if they were filtered.

### 4.4 Legend (HTML, not canvas)

The legend is always present: collapsed to one line on mobile, expanded on desktop. It holds:
- the symbol key (§3.5), each with a one-line meaning;
- the technology colours with counts;
- the cell count ramp and "hollow = one source";
- the coverage hatch;
- "Sites with no published point in view: N" (SIG-UI-020, from `dict.json` per-jurisdiction counts);
- "Not yet available" layers (§3.6);
- the basemap and data vintage ("Data: release {label}, as of {date} · Basemap: Protomaps {build}").

It uses `<details>` and `popover` for definitions (K0 least-power ladder).

### 4.5 Selection: popup and panel

**Selecting a site:**
- by click or tap;
- by Enter on a list item;
- from `focus=` in the URL.

**What selection does:**
1. highlights the site;
2. opens the **Selected** tab. On desktop a small anchored popup also appears (title plus "Details →"). On mobile the sheet
   opens to half.
3. The panel renders the tile properties at once. It then fetches the record's JSON twin (`/r/<pub>/c/<comp>/entity/…json`,
   ≤ 5 KB; the existing `recordRoutes`, `workspace-state.ts`) for sources, claims and evidence.

| panel row | content | link target |
|---|---|---|
| Title | derived label (`lb`) · technology | — |
| What | technology (+ "classified from {source-declared \| record}"), vendor, lifecycle | vendor entity page (K2) when resolved |
| Who operates it | operator label or "Operator not stated by any source" | operator entity page (K2) `/entity/<id>/` |
| Where | "{place}, {county}, {state}" from `j`, precision text (§3.4), coordinates at the published precision | dossier `/dossier/<slug-path>/` (K4) |
| Sources | each contributing source, with licence and first/last seen | `/sources/<id>/` (K10) |
| Evidence | per-claim evidence anchors from the record JSON | `/evidence/claim/<id>/` (K8) or `/r/<pub>/…/evidence/…` |
| Status | corroborated / single source / contested ("2 sources disagree about the location — see both") / candidate | the entity page's contradiction section (K2; SIG-UI-009) |
| Actions | Open full record · Cite this site · Report a problem · Show on list | record page; snapshot URL with `focus=` and `at=`; `/dispute/?subject=<rk>`; list tab |

**Rules:**
- Text only (`textContent`). No `setHTML` or `innerHTML` (K0 §4.8).
- Escape closes the panel and returns focus to the invoking control (fixes D6).
- A click that hits several features (co-located or overlapping) opens a chooser listing all of them.
- **Graceful dependency.** If K2, K8 or K10 routes are not yet built, the row shows the data and links the dossier or the
  release record. It never links a 404. The link crawl (§9) enforces this.

### 4.6 "Sites in view" list (the synchronized list view)

The **In view** tab always lists what the canvas shows. It is computed from the tiles, not the API, so it works offline and
fast.

**Below z10, "Places in view":**
- K4 jurisdictions summed from the cells' `jp` with counts ("Houston, TX — 3,113 sites; 1 source: 41 %").
- Each row is a button "Show" that frames the place, plus a link to its dossier and site list.

**From z10, "Sites in view":**
- ≤ 50 rows sorted by distance from the map centre: label, technology, operator, source, status.
- Each row has a "Select" button and an "Open record" link.
- "Show all N in this area" links the API bbox HTML list (MAP-06) or the place's static list.

**Behaviour:**
- **Sync.** The list updates on `moveend`, debounced 300 ms.
- **Hover.** Hovering a row highlights the site. Selecting a site scrolls its row into view.
- **Live region.** `role=status` on the header, debounced 1 s: "Showing Austin, Texas: 137 sites in view."
- **Table view.** A "Table" toggle renders the same rows as a real `<table>` with sortable headers (≤ 50 rows) for screen-reader
  table navigation.
- **"Download this view".** CSV of the in-view rows with licence lines, from K0's `<sig-table>`.

### 4.7 Keyboard and screen-reader contract (WCAG 2.2 AA; K0 §4.9)

**Tab order:**
1. skip link;
2. place search;
3. panel tabs, then the active tab's content;
4. the map region ("Map. Use the In view list for the same information.");
5. map controls;
6. attribution.

**With the canvas focused:**
- Arrows pan (100 px) and `+`/`−` zoom (MapLibre `KeyboardHandler`, K12a [Q092]).
- **Enter** moves focus to the first In view row.
- **Escape** clears the selection.
- Shortcuts act only while the canvas has focus (2.1.4).

**Everywhere:**
- No keyboard trap; the existing no-trap behaviour is kept (C2 §6.3).
- Focus stays visible, with a 3 px ring from K14 tokens.
- Screen-reader users get: the live-region summaries, the In view list/table, the Selected panel as a labelled region, and
  `aria-describedby` pointing to the legend.
- **axe runs on these states:** initial, list open, site selected, filters open, basemap-fallback notice, mobile sheet at
  half. Keyboard journeys J4/J5 (§9.3).

### 4.8 URL state (`sig.workspace-state/2`, map fields)

```
/map/?v=2&release=p-<sha>&view=map&at=<z>/<lat>/<lon>&layers=sites,cells,coverage&basemap=0
      &technology=alpr&vendor=<entity>&operator=<entity>&source=<id>&collection=<comp>&seen=2024-01..2026-09
      &status=contested&jurisdiction=<jkey>&focus=<record_key>
```

**What to add to K0's common set.**
- `vendor`, `operator`, `seen` and `status` become **common** facets, so `/search/` and `/explore/` accept the same links.
- `bbox=w,s,e,n` is accepted as input (K4 §6's dossier links) and canonicalised to `at=` with `replaceState`.
- `jurisdiction=` frames on the registry bbox **and** acts as a facet when "Filter to this place" is chosen. The two states are
  distinct and both linkable.

**History.** Pan and zoom use `replaceState`. Filters, focus and search use `pushState`. Back and Forward restore the state
(ADR-134's adapter).

**Cite this view.**
- Produces `/s/<pub>/map/?v=2&…` plus the static equivalent link (§5), which is the dossier list for `jurisdiction`, or the
  API bbox list.
- Until G3's snapshot build exists, J3 §8.1's fallback text is used.
- Parameterised URLs carry `noindex,follow` and a canonical `/map/` (K0 §4.5).

---

## 5. No-JS baseline (K0 §4.4, T2 rule)

**`/map/` with JavaScript off** is a complete ≤ 100 KiB document. It contains:

1. **Accurate intro copy** (agent-drafted; fixes D10):
   > An interactive map of {N} published sites with a location, drawn over an OpenStreetMap basemap. Without JavaScript this page
   > shows a static overview and lists every place; each place has a full, paginated list of its sites.
2. **Static SVG overview** (build time; `exports/static_map.py` or a web build step, **shared with K6**):
   - an equal-area or Albers view of the US, plus inset panels for the other countries with data (CA, GB, AU, …);
   - state and country outlines from K4's display boundaries;
   - H3 res-3 cells as proportional discs, hollow for single-source;
   - the attribution text inside the SVG and in the caption;
   - `role="img"`, a short `aria-label`, and the table below as its long description.

   About 30–60 KB (*inference*). It is also the first paint of the interactive map.
3. **A place form** (GET → `/map/place/?q=` → static A–Z results → the dossier or site list).
4. **A table of countries and states:**
   - columns: name (a link to the dossier), published located sites, sources, share single-source, sites with no published
     point, and a "sites list" link;
   - ≤ 70 rows, grouped by country;
   - the counts are shown **with** their coverage label, never suppressed. The caption is changed to match, which fixes the
     DATA_TRUTH §4.8 caption/table contradiction (D-K1-4).
5. **A notice when the URL carries state** (`at=`, filters or `focus`), in `<noscript>`:
   > This link encodes a map view ({summary}). Without JavaScript, the same sites are listed at {link to the place list or the
   > bbox list}.
6. **No per-subject gap links.** "Sites whose location is contested: N in {jurisdiction}" links the dossier's contested section
   (K5/K2). This replaces the 5,290 dead `/task/new/…` links (D5).

**Per-jurisdiction site lists** (T1): `/dossier/<slug-path>/sites/` plus `/page/<n>/`.
- One list per K4 key with ≥ 1 located record, at country, admin-1 and county level, plus places per D-K4-3.
- ≤ 100 rows per page: label, technology, operator, source (link), first/last seen, status, precision, coordinates at the
  published precision, and a record link.
- Each page carries its own static locator SVG, the attribution, and "Open on the interactive map" (`jurisdiction=<jkey>`).
- Pagination is by path, so static hosting needs no query strings.
- Size: ≈ 2.3k–5k HTML files per release (*inference*: 227k rows / 100 plus small lists). Negligible against 475k record
  files (K0 §2.3).
- The release-tree lists `/r/<pub>/c/<comp>/jurisdiction/<slug-path>/` (K4 JUR-03) stay the per-compartment T0 records. The
  dossier sites list is the cross-compartment reading view, grouped by compartment with a licence line per group.

**Print.**
- The canvas is never printed.
- "Print this view" prints the In view list, the legend, the attribution, the as-of line and the cite URL.
- A jurisdiction-framed view links its dossier print, which carries the static SVG (K6).

---

## 6. Performance

### 6.1 JavaScript (budget: ≤ 360 KiB gzip initial, K0 §4.3)

| item | today (fixtures, gzip) | target (gzip) | how |
|---|---:|---:|---|
| MapLibre main + shared | 282.8 KB (`MapIsland.*.js`, incl. app) | 294.2 KB (147.9 + 146.3) | import `maplibre-gl.mjs`; serve `maplibre-gl-shared.mjs` and `maplibre-gl-worker.mjs` as hashed static assets; `setWorkerUrl` to the module worker. The shared chunk is fetched once and HTTP-cached for the worker (NEW-2 of K0; confirmed: the worker imports `./maplibre-gl-shared.mjs`, §15 C11) |
| MapLibre worker | 143.6 KB (a second copy of shared) | 6.1 KB | as above |
| React runtime + jsx | 70.4 KB | 5.4 KB | Preact (K0 D-K0-2) |
| PMTiles | (in the island) | 7.4 KB | unchanged |
| Basemap style package | — | **0** | style JSON generated at build (§2.5), fetched as data (≈ 7 KB gz) |
| App code | ≈ 2–5 KB | ≤ 40 KB | panel, filters, list, cell sum, URL state, typeahead hookup (MiniSearch 5.9 KB loads on first search focus: post-action budget) |
| **Total initial** | **496.9 KB** (`p32.15-island-budgets.md`) | **≈ 353 KB ≈ 345 KiB** | ≤ 360 KiB; brotli transfer ≈ 290 KB (*inference* from K0 §2.1 ratios) |

**Loading order:**
- HTML first: the panel, the legend and the SVG are the LCP candidates.
- MapLibre loads on `client:idle` into the reserved box.
- MiniSearch and the shards load on search focus.
- `maplibre-gl.css` (10.5 KB gz) is inlined as a hashed stylesheet.

**Headroom and risk.** The target leaves ≈ 15 KiB of headroom. If the app outgrows it, the first cut is lazy-loading the filter
and table code after first interaction (the post-action budget is ≤ 60 KiB). Raising the budget needs a measured report and an
ADR amendment (K0 I-4).

### 6.2 Tiles and data (budget: first view ≤ 1.5 MiB tiles + glyphs; ≤ 500 KiB per pan/zoom)

| view | basemap (measured §2.1) | glyphs (2 fonts × 1 range, measured) | overlays (measured today, §15 C10) | total |
|---|---:|---:|---:|---:|
| national, desktop | 362 KiB | ≈ 91 KiB | 220 KB (12 × 16 KiB header reads dominate) | ≈ 0.66 MiB |
| national, mobile | 257 KiB | ≈ 91 KiB | ≤ 220 KB | ≈ 0.55 MiB |
| street z14, desktop | 647 KiB | ≈ 91–137 KiB | 30 KB (→ ≈ 60–120 KB after retention; *inference*) | ≈ 0.8–0.9 MiB |

**Overlay header reduction.**
- Each of the 12 archives costs a 16 KiB header and root-directory read before any tile, even where it has no data in view
  (**NEW-6**).
- The fix: add a compartment's source **only when the viewport intersects its bounds**. The bounds come from `dict.json`, taken
  from each archive's header.
- A US first view then needs ≈ 6 of 12 archives, and ≈ 90 KB of header reads are avoided (*inference*).

**Other data:**
- Place shards: ≤ 50 KiB per keystroke.
- `dict.json`: ≈ 30–60 KB, loaded once.
- Record JSON on selection: ≤ 5 KB.

### 6.3 Document and Lighthouse

- The `/map/` document: ≤ 100 KiB transferred (today 271 KB transferred, 3.43 MB raw). The 1,504-row table and 5,290 links
  are removed (§5).
- Lighthouse mobile on the **real release**, errors per K0: performance ≥ 0.75 (goal 0.85), accessibility 1.0, LCP ≤ 2.5 s,
  CLS ≤ 0.05, TBT ≤ 350 ms.
- Playwright at 4× CPU throttle: selection latency ≤ 200 ms; filter toggle → redraw ≤ 200 ms.
- Measured in CI on K0 UXK0-2's real-sized synthetic fixture (≥ 232k sites). The same checks run on the real release before
  promotion (G3 V11).

### 6.4 Browser support

- MapLibre GL 6 needs WebGL, and possibly WebGL 2. K0 R-4 left that unverified. My local render succeeded under SwiftShader;
  the WebGL version was not checked.
- Without WebGL, the page shows the §5 no-JS content plus a notice. MAP-03a states the matrix: last two versions of Chrome,
  Edge, Firefox and Safari; iOS Safari 16+; Android Chrome.

---

## 7. Data contracts the export must produce

| artifact | path (per release) | schema | licence | producer | consumer |
|---|---|---|---|---|---|
| Overlay tiles v2 | `web/tiles/<comp>-sites.<sha8>.pmtiles` | `sig.map-tiles/2` (§3.1, §3.3) | the compartment's one SPDX | `exports/tiles.py` (MAP-01a/b) | island |
| Tile manifest | `web/tiles/index.json` | `{compartment, path, sha256, licence, attribution (PKG-08), bounds, minzoom, maxzoom, counts{points, cells_by_band}, renderer, renderer_version, contract: "sig.map-tiles/2"}` | CC-BY-4.0 | MAP-01a | island, verifier, G3 V-checks |
| Map dictionary | `web/map/dict.json` | `sig.map-dict/1`: sources, technology codes, vendor slots, jurisdiction chains + bboxes for keys in use, per-jurisdiction unplotted counts (tier 3 + no point), national facet totals | CC-BY-4.0 (SIG metadata) | MAP-01b | island, legend, no-JS pages |
| Coverage table | `web/map/coverage_by_jurisdiction.json` | `jkey → {sources[], technologies[], basis, rule_version}` | CC-BY-4.0 | C3/L3 rule (D-K1-4); MAP-01b emits | coverage layer, legend, dossiers |
| Context base | `web/tiles/context.pmtiles` | boundaries (state/county/country) + place points with names, z0–10 | public domain (Census, NE) + CC BY 4.0 (GeoNames names, if chosen) | MAP-02 from JUR-01's pack | fallback base, static SVG |
| Static overview | `web/map/overview.svg` (+ per-jurisdiction locators, shared with K6) | SVG with `<title>`, `<desc>`, attribution | produced work | MAP-05 | `/map/`, dossiers, print |
| Place shards | `web/search/place/<xx>.json` | K3's shard schema, `kind=place` | CC-BY-4.0 (+ GeoNames attribution) | K3 (MAP-04 consumes) | search box |
| Basemap lock | `ops/basemap.lock.json` (repo) + `release.json.basemap_build` | build, schema, size, b3sum, style package version | — | MAP-02 | "About this map" |
| Bbox API | `/v1/releases/{pub}/compartments/{c}/sites?bbox=&page=` (JSON) and `/v1/releases/{pub}/sites?bbox=&page=&format=html` (grouped by compartment) | ≤ 100 rows per page, derived labels | per compartment | MAP-06 (adds an R-tree to the per-release SQLite of ADR-133) | the no-JS `at=` equivalent; "Show all N" |
| Tile verifier report | `reports/tiles_verify.json` in the release candidate | per compartment × zoom: expected vs present counts, conservation, parity, precision/tier checks, max tile bytes | — | `sig-exports tiles verify` | CI, G3 promotion gate |

**The bundle `<comp>/sites.pmtiles` downloads (NEW-4).** Either publish the real tile archive (a byte copy of the web tile) or
drop the format from the bundle and list GeoJSON/Parquet. **Never** ship a zero-tile "PMTiles". This belongs to J3 TX-10
(downloads) and needs a one-line change in `FORMATS`.

---

## 8. What depends on what (interfaces)

| needs | from | used for | if not ready |
|---|---|---|---|
| Page-type registry, budgets, real-sized fixture, CSP | K0 UXK0-1/2/3 | budgets and CI | MAP-03 lands behind the old island budgets, then tightens |
| `sig.workspace-state/2`, Preact | K0 UXK0-5/6 | URL state; runtime | MAP-03 carries the v2 map fields itself |
| Jurisdiction registry, boundaries, placement (`j`, `jp`) | K4 JUR-01/02b/03 | place search, context base, lists, framing | `j = unplaced`; lists by legacy jurisdiction; no county layer |
| Technology column | F5 PKG-07 | `tc`, technology filter/colours | everything "unclassified", with an honest legend |
| Derived labels, entity pages, vendor/operator resolution | K2 | `lb`, `op`/`oe`, `vd` | label fallback rule; operator as text; no vendor filter |
| Per-compartment attribution | F5 PKG-08 | attribution strip | today's (wrong) strings stay flagged, F-134 |
| Record tree `/r/<pub>/` served; snapshot `/s/<pub>/`; path-pinned tiles | G3 REL-03b/09, G2 activation, PKG-03b | record links, cite, immutable tiles | panel shows tile data and links the dossier; cite uses J3 §8.1 fallback |
| `/v1/*` through the web origin | F5 PKG-04 (F-155) | MAP-06 bbox list | "Show all" links the static place list |
| Zero-egress host + DNS zone | J3 TX-11, D-K1-2 (NEW-5) | basemap on R2 | option B (GCS same origin) |
| Typeahead component + shards | K3 | place search | GET form only |
| Source pages, evidence pages | K10, K8 | panel links | link the dossier / record instead |
| Static map renderer | shared with K6 | SVG overview, dossier maps | K1 builds it; K6 reuses it |
| Coverage rule | C3 / L3 / K9 | coverage layer | the layer ships with "rule pending" and only the proxy (hollow = one source) |

---

## 9. Testing

### 9.1 Unit (Vitest / pytest)

- URL state v2 round-trip: `at=` rounding table; the `bbox` → `at` canonicalisation; the `jurisdiction` framing vs facet split;
  unknown values fall back **with** an issue.
- Cell summation: dedupe by `(compartment, h3)`; the sum over active compartments equals the fixture totals; toggling a
  compartment changes the sum exactly.
- The style generator is deterministic from the lock file. The contrast checker passes and fails on crafted palettes.
- Label derivation (K2 rule) never yields a UUID.
- Text-only rendering: a CI grep bans `setHTML`, `innerHTML` and `dangerouslySetInnerHTML` in `web/src/` (K0 §4.8).

### 9.2 Tile integrity (`sig-exports tiles verify`, pytest over fixtures, CI with the **real pinned tippecanoe**)

1. **Count conservation.** For every compartment and zoom z ≤ 9: Σ `n` over cells = the compartment's published located
   records. For z ≥ 10: the `rk` set in tile interiors (buffer duplicates excluded) = the published set for that tier range.
   0 missing, 0 extra.
2. **Renderer parity.** The pure-Python and tippecanoe archives agree on the `rk` set per zoom and on Σ `n` per zoom.
   Byte equality is not required.
3. **Precision and tier.** Checks as in §3.4. No property outside `sig.map-tiles/2`. No claim ids, full-precision coordinates
   or personal data in any tag (§19.4; Part VIII).
4. **Size.** Maximum tile ≤ 500 KB, with a warning at 200 KB. Archive totals are reported.
5. **Metadata.** Licence, attribution and bounds equal `index.json`. The archive's licence equals its compartment's.
6. **CI.** Build tippecanoe 2.79.0 from the Dockerfile's pinned tarball once, cache it, and run 1–5 on a 50k-point synthetic
   fixture (clustered cities, co-located points, all tiers, 3 compartments). Also run on the real-sized fixture (UXK0-2) in the
   nightly job. The existing mocked test (`test_tiles.py:198`) is kept only for argv shape.
7. **Pre-promotion.** G3's verification runs 1–5 on the real release candidate. A failure blocks promotion.

### 9.3 End-to-end journeys (Playwright; real-sized fixture + a small **synthetic** basemap fixture — no committed OSM data)

| id | persona | journey | pass condition |
|---|---|---|---|
| J1 | resident, mobile 390×844 | `/map/` → type "Canberra" → pick → In view → select a site | framed on AU-ACT; basemap labels; ≥ 1 site listed; panel shows technology, operator or "not stated", a linked source and dates; ≤ 4 interactions; Share reproduces the view |
| J2 | journalist, desktop | filter Vendor = {synthetic vendor}, Technology = ALPR; zoom from national to a city; Cite this view; reopen the URL | cells re-sum; points from z10; the reopened URL restores filters, `at` and `focus`; the cite URL is the snapshot form |
| J3 | advocate | a dossier's "Open on map" → the county framed → "Print this view" | framed within bbox tolerance; the print has the list, attribution, as-of and URL; no canvas |
| J4 | keyboard only | Tab to search → "Austin" → Enter → Tab to In view → Enter on a row → Escape | the selection opens; Escape returns focus to the row; no trap; visible focus throughout |
| J5 | screen-reader proxy | read the live region after a zoom; the table view | announcements after moveend; the table has headers and the same rows as the list |
| J6 | street zoom (the §1.1 regression) | a fixture site at z6, 9, 10, 12, 13, 14, 15 | counted in exactly one visible cell at z ≤ 9; drawn and listed at every z ≥ 10 |
| J7 | basemap failure | block the basemap origin | the notice appears; the context base draws; sites are still drawn; no console error loop |
| J8 | no-JS | `/map/?v=2&at=12/30.268/-97.743&technology=alpr` with JS off; `/map/`; a site list page | the notice links the equivalent list; the `/map/` document is ≤ 100 KiB; 0 broken links (crawl) |
| J9 | dark mode | `prefers-color-scheme: dark` | the dark style loads; the contrast check passes; the legend matches |
| J10 | reduced motion | `reducedMotion: 'reduce'` | no animated camera moves; selection has no pulse |

### 9.4 Accessibility, visual, performance, security

- **axe (WCAG 2.2 AA)** on the §4.7 states, in both Playwright projects.
- **Visual regression.** `toHaveScreenshot` on 6 canonical views × light/dark × desktop/mobile over the synthetic basemap.
  SwiftShader is deterministic within a pinned Chromium; tolerance 0.2 %. A failure uploads the diff.
- **Budgets.** `budget.spec.ts` against the §6 table. The generated `lighthouserc.json` covers `/map/` and one site-list page
  (K0 §4.12).
- **CSP.** The e2e runs behind the real headers and fails on any `securitypolicyviolation`, including the tile origin in
  `connect-src` and the worker in `worker-src`.
- **Links.** A no-JS crawl of `dist`, including every site list page, finds 0 broken internal links (fixes D5).

### 9.5 Live verification (MAP-07, operator go)

After the Class S republish:
1. J1, J2, J4 and J6 run against production with ≤ 20 page loads, paced 3 s.
2. Lighthouse mobile runs on `/map/`.
3. `tiles verify` runs on the served archives.
4. The costs of the first 7 days are read from the billing export (G1).

---

## 10. ADR draft (agent-drafted; T1 assigns the number)

> **ADR-NNN — Public map v2: a self-hosted OpenStreetMap basemap, count-conserving per-compartment overlay tiles, and
> release-pinned map state**
>
> - **Status:** Proposed (K1, 2026-09-30). **Reverses** the Round-9 operator decision Q8 ("no basemap", 2026-09-24) at the
>   operator's request (U-003.1, 2026-09-30T21:29:45Z). **Supersedes ADR-118 §Decision 2** (no basemap), acting on its revisit
>   trigger (a) ("revisit ONLY as the costed self-hosted extract follow-up (Q8(b)), never a third-party tile service").
>   **Extends ADR-118 §Decision 1** (per-compartment archives) with a second layer and a retention contract. Consumes ADR-NNN(K0)
>   (T2 page type, `sig.workspace-state/2`). Leaves ADR-106 (compartment separation) unchanged.
> - **Related:** SIG-GEO-008/010/011/012/013, SIG-UI-005/016–020/037/038/047, SIG-FIND-004; U-003.1, U-008; F-100, F-114, F-123,
>   F-134; K12b NEW-6/7/8/9.
>
> **Context.** The public map draws sites over a plain background, so readers cannot tell where they are. Its overlay tiles also
> hold a thinned sample below z14: tippecanoe runs with default dropping, so 25.6 % of sites exist at z12 and 0.03 % at z3. The
> island never draws the density bins the spec and the page promise. Residents abandon the task (C2 P6, P12). The basemap was
> declined in Round 9 to avoid third-party tile services. A self-hosted OpenStreetMap basemap removes that objection at ≈ $2–13
> a month.
>
> **Decision.**
> 1. The public map draws a **self-hosted Protomaps basemap** (OpenStreetMap data, ODbL) as its own archive on a SIG-controlled
>    origin. The host is R2 behind `tiles.surveillancegraph.org` or a same-origin GCS backend bucket (operator decision D-K1-2).
>    The build is pinned in `basemap.lock.json` and refreshed deliberately. It is never merged with SIG data and never a release
>    input. Styles (light/dark) are generated at build; glyphs are self-hosted; no third-party origin is contacted at runtime.
> 2. **Attribution** for the basemap and every compartment appears in every rendering context — interactive, static, print —
>    and never overlays map controls (SIG-GEO-013, WCAG 2.4.11).
> 3. If the basemap fails, the map shows a notice and a SIG-hosted public-domain boundaries layer. The data layers never depend
>    on a base layer.
> 4. Each compartment archive carries `cells` (H3 counts, z0–9) and `sites` (every published located record from its tier's
>    minimum zoom, z10+). Rate-based or density-based dropping is forbidden. An export that cannot fit a tile fails.
>    Cross-compartment totals are summed only in the browser at render time (ADR-106 §4).
> 5. A tile verifier (count conservation, renderer parity, tier/precision, size, metadata) runs in CI with the pinned tippecanoe
>    and blocks release promotion.
> 6. Map tiles are served from release-pinned, content-hashed paths. The viewport (`at=`, zoom-rounded, never finer than the
>    published tier), filters and selection are URL state. "Cite this view" yields the snapshot URL.
>
> **Consequences.**
> - **Positive:** the map answers "where" and "how many" honestly at every zoom. Citations of a view reproduce. The basemap adds
>   ≈ $2–13/month.
> - **Negative:**
>   - a new external data dependency (the Protomaps build), refreshed by hand;
>   - either a DNS move to Cloudflare or denial-of-wallet exposure on GCS;
>   - overlay archives grow ≈ 2.5×;
>   - CI must build tippecanoe.
> - **Neutral:** the pure-Python renderer stays the fixture path but must honour the same contract.
>
> **Alternatives considered.** OpenFreeMap, Stadia, MapTiler and OSMF services were rejected: third-party viewport leakage,
> non-commercial terms, and policies that forbid this use. Client-side clustering of 227k points was rejected (≈ 34 MB GeoJSON,
> K12a §8). A single cross-compartment density archive was rejected (a licence-mixed public database). tippecanoe
> `--cluster-distance` per compartment was rejected: overlapping per-licence bubbles mislead. Keeping no basemap was rejected
> (U-003.1).
>
> **Revisit trigger.**
> 1. Basemap hosting costs more than $25/month, or egress abuse is observed.
> 2. The Protomaps build or its licence terms change.
> 3. A requirement needs address-level geocoding.
> 4. A compartment's densest tile exceeds 200 KB at z10, or the verifier finds any dropped record.
> 5. Counsel, a licensor or the OSMF requires a different attribution or separation.
> 6. MapLibre needs WebGL 2 only, and the no-WebGL share of visitors becomes material.

**Spec amendments (agent-drafted, for T1 via `spec_src`):**

| id | amendment |
|---|---|
| SIG-FIND-004 | Strike "and the no-basemap decision remain[s] in force"; add "map viewport (zoom-rounded), map filters and selection are part of the shared URL state (ADR-NNN)". |
| SIG-UI-038 | Add "The map SHOULD draw a self-hosted OpenStreetMap-derived basemap served as its own archive from a SIG-controlled origin, with a public-domain boundaries fallback" (with K0's rewrite). |
| SIG-GEO-012 | Add "Each compartment archive carries a `sites` layer holding every published located record from its tier's minimum zoom and a `cells` layer of H3 counts below it. No renderer may drop records by rate or density; conservation is verified before promotion." |
| SIG-UI-019 | Annotate: national/regional zoom (≤ 9) renders H3 counts; points from z10 (tier 0), z11 (tier 1), and areas from z12 (tier 2). |
| SIG-UI-018 | Clarify: counts in low-coverage cells stay visible in text with their coverage label; the *visual* encoding is desaturated or hollow (resolves the caption vs table contradiction, DATA_TRUTH §4.8). |
| SIG-GEO-013 | Add "…and never overlays interactive controls". |

---

## 11. Draft requirements and acceptance (provisional `SIG-UI-DM` ids for K13/T1)

| id | requirement | acceptance |
|---|---|---|
| SIG-UI-DM01 | Every published located record MUST be represented at every zoom: in exactly one cell count at z ≤ 9, and as a drawn feature from its tier's minimum zoom. | verifier conservation = 0 missing; J6 |
| SIG-UI-DM02 | The map MUST draw a self-hosted OSM basemap from a SIG-controlled origin, with attribution visible and not overlaying controls; on failure it MUST show a notice and a boundaries base. | CSP e2e (no third-party origins); J7; axe 2.4.11 check |
| SIG-UI-DM03 | Selecting a site MUST show a derived label, technology, operator (or "not stated"), jurisdiction (linked), source(s) (linked, with licence), first/last seen, precision and status, rendered as text only. | J1; grep gate |
| SIG-UI-DM04 | A synchronized, keyboard-operable list of what the map shows (places below z10, sites from z10, ≤ 50 rows) MUST be present; Escape MUST return focus. | J4, J5 |
| SIG-UI-DM05 | Viewport, filters, layers, basemap choice and selection MUST round-trip through `sig.workspace-state/2`; `at=` precision follows §3.4. | J2; unit round-trip |
| SIG-UI-DM06 | Every filter MUST state its count and MUST disclose when it cannot apply at the current zoom. | J2; unit |
| SIG-UI-DM07 | Without JS, `/map/` MUST show the static overview, the place form and the places table, within ≤ 100 KiB, and every jurisdiction with located records MUST have a paginated site list. | J8; crawl |
| SIG-UI-DM08 | The map MUST meet the K0 T2 budgets on the real release (≤ 360 KiB gzip initial JS; first view ≤ 1.5 MiB tiles + glyphs; Lighthouse mobile ≥ 0.75). | budget spec; LHCI; G3 V11 |
| SIG-UI-DM09 | Symbols MUST keep ≥ 3:1 contrast against every basemap fill in both themes, and colour MUST NOT be the only channel. | contrast script; J9 |
| SIG-GEO-DM10 | No tile may contain a record at finer precision than its tier, a tier-3 record, or a property outside `sig.map-tiles/2`. | verifier |

---

## 12. Round-11 ticket outline

Sizes follow J3/K4: **S** ≈ half a fresh-context run, **M** one run, **L** split a/b. "Live" = a production stage that needs an
operator go.

| # | key | ticket | size | depends (K0 / K4 / J3 / G3 / F5 / other) | live / gate |
|---:|---|---|---|---|---|
| 1 | **MAP-00** | ADR (§10) + `spec_src` amendments + `web/AGENTS.md` map notes | S | GATE-P; T1 with K0's ADR | — |
| 2 | **MAP-01a** | Tile retention + verifier: per-feature zoom ranges, `-r1`, `cells` layer (`h3`, `n`, `ns`, `jp`), the `tier` fix (D3), pure-Python parity (no coalescing), `web/tiles/index.json`, `sig-exports tiles verify`, CI tippecanoe build + cached binary, 50k synthetic fixture | M | F5 PKG-03a (export-mode CI build); K0 UXK0-2 (real-sized fixture, nightly) | rides the next release; G3 promotion gate consumes the report |
| 3 | **MAP-02** | Basemap pipeline + host: `basemap.lock.json`; `sig-ops basemap refresh` (dry run, verify, upload, flip, 30-day keep); style generation (light/dark, labels split, no POIs); self-hosted glyphs + licence files; `context.pmtiles` from JUR-01's pack; CORS/Range/cache headers; budget alert + kill switch; CSP `connect-src` | M | D-K1-1/2/3; K4 JUR-01 (context; else ship without and add later); G1 QA-10 (budget alert); J3 TX-11 if R2 (and the DNS move, NEW-5); K0 UXK0-3 | **live**: bucket or DNS change + first upload — op go |
| 4 | **MAP-03a** | App shell (T2, Preact): ESM-split MapLibre, reserved-box SSR with the SVG, desktop/mobile layout, basemap + fallback, cells merge + sites layers + symbols (§3.5), HTML legend, attribution strip, selection panel with graceful links, `at=`/`layers=`/`basemap=`/`focus=` URL state, cite, budgets | M | MAP-01a, MAP-02 (can stub with the synthetic basemap); K0 UXK0-1/5/6; K14 tokens (soft) | via release |
| 5 | **MAP-03b** | Filters (§4.3) with counts and zoom honesty, In view list/table + live region, keyboard contract, mobile sheet, print view, "download this view" | M | MAP-03a; MAP-01b for vendor/technology/date data (filters ship disabled with an explanation until then); K0 UXK0-4 (`<sig-table>`) | via release |
| 6 | **MAP-04** | Place search: registry + cities shards via K3's `<sig-typeahead>`; coordinates parser; `jurisdiction=` framing vs facet; "my location" (if D-K1-7); no-JS `/map/place/` form route | S | K3 (component + shard build); K4 JUR-01; D-K1-5 | via release |
| 7 | **MAP-05** | No-JS baseline: new `/map/` document (≤ 100 KiB), the static map renderer (shared with K6), places table, stateful-URL notice, `/dossier/<path>/sites/` lists, contested-location counts replacing the 5,290 links, link crawl | M | K4 JUR-03 (dossiers at every level) + JUR-04 (hierarchy); K0 UXK0-1; coordinate with K6 | via release |
| 8 | **MAP-01b** | Tile properties v2 + `dict.json` + `coverage_by_jurisdiction.json`: `lb`, `tc`, `vd`, `op`/`oe`, `sr`, `j`, `f`/`l`, `st`, `pm`, `co`; facet counts on cells; content-hashed tile names | M | F5 PKG-07 (technology), K4 JUR-02b (keys), K2 (labels, operator/vendor resolution), PKG-08 (attribution), C3/L3 coverage rule (D-K1-4); G3 REL-03b (hashed paths) | rides the next release |
| 9 | **MAP-06** | Bbox API: per-compartment JSON + cross-compartment grouped HTML, R-tree in the per-release SQLite, ≤ 100 rows per page | S | F5 PKG-04 (`/v1` via the web origin, F-155); G3 REL-05 (release-pinned API) | API roll — op go |
| 10 | **MAP-07** | Acceptance + republish: J1–J10 on the real-sized fixture; `tiles verify` + LHCI on the release candidate; Class S promote; live checks §9.5; 7-day cost read | S | all above; G3 promote; G1 billing export | **live** — op go |

**Order and parallelism.**
- MAP-00 → {MAP-01a ∥ MAP-02} → MAP-03a → {MAP-03b ∥ MAP-04 ∥ MAP-05} → MAP-01b (when PKG-07, JUR-02b and K2 labels have
  landed) → MAP-06 → MAP-07.
- MAP-01a alone fixes the operator-visible "missing dots" defect. It can ship in the first product wave, before the new app:
  the old island then draws all points from z10, though it still lacks cells and a basemap.
- A two-ticket "honest map now" slice (MAP-01a + MAP-02 with a minimal style swap in today's island) is possible if the
  operator wants the basemap before the full rewrite. **D-K1-8.**

**Exactly-one ownership (P9).**
- The static map renderer: MAP-05 (K6 consumes).
- Place shards: K3 (MAP-04 consumes).
- The coverage *rule*: C3/L3; its tile/JSON emission: MAP-01b.
- Per-compartment attribution strings: PKG-08.
- The zero-tile bundle PMTiles (NEW-4): J3 TX-10.
- DNS zone move (NEW-5): G1/J3 TX-11, as an operator action.

---

## 13. Operator decisions needed

| id | decision | recommendation |
|---|---|---|
| **D-K1-1** | Reverse Round-9 Q8: adopt a self-hosted OSM (Protomaps) basemap | **Yes** (U-003.1) |
| **D-K1-2** | Host the basemap on R2 (needs moving the `surveillancegraph.org` DNS zone from Squarespace to Cloudflare's free plan, which J3 TX-11 also needs; ≈ $3/mo at 10k sessions, ≈ $13 at 100k) or on a same-origin GCS bucket (no DNS change; ≈ $6 / ≈ $43; needs the budget alert) | **R2 with the DNS move**, if you are comfortable moving DNS; otherwise GCS now and R2 with TX-11 |
| D-K1-3 | Basemap extent and refresh: planet z0–15 (R2) or z0–14 (GCS); twice-yearly manual refresh | as stated |
| D-K1-4 | Coverage semantics: (a) counts in single-source cells are shown with a "1 source" label, not suppressed; (b) crowdsourced global sources do not count as "SIG has looked" | **Yes** to both |
| D-K1-5 | Non-US place names: GeoNames cities15000 (CC BY 4.0, attribution) or Natural Earth populated places (public domain, fewer names) | **GeoNames** (better recall; attribution is cheap) |
| D-K1-6 | Symbol semantics: filled = corroborated, hollow = single source, double ring = contested; single-source sites shown by default | **Yes** |
| D-K1-7 | "My location" button (browser-only geolocation after a click; never sent to SIG) | **Yes** |
| D-K1-8 | Ship an early "honest map now" slice (MAP-01a + basemap in today's island) before the full app rewrite | **Yes** if the rewrite is more than ~2 weeks away |

---

## 14. Risks

| id | risk | mitigation |
|---|---|---|
| R-1 | The DNS move to Cloudflare disrupts the site or mail | Plan it as its own G1 ops ticket with a pre-copied zone and TTL lowering; or choose option B |
| R-2 | Denial of wallet on GCS (option B) | Budget alert + kill switch to the context base; Cloud Armor rate limit; R2 later |
| R-3 | tippecanoe `-r1` produces over-size tiles as data grows (e.g. 474k Flock-portal sites) | the verifier warns at 200 KB and fails at 500 KB; raise the point zoom per tier or split a compartment's layer by technology, by ADR amendment |
| R-4 | The client cell merge disagrees with the static overview | both read the same `cells`; a unit test compares SVG totals with the summed tiles |
| R-5 | The Protomaps schema or style drifts at refresh | lock file; visual regression on refresh; style generated from a pinned package |
| R-6 | The budget is tight (≈ 15 KiB headroom) | lazy-load filters/table post-action; measure every PR |
| R-7 | The technology, vendor and operator data are not ready (PKG-07, K2) | the UI is honest ("unclassified", "not stated"); filters disabled with a reason; MAP-01b follows the data |
| R-8 | Readers take a basemap label as a SIG claim (e.g. a POI name) | POIs dropped; "About this map" says the basemap is context, not evidence |
| R-9 | Visual tests flake across Chromium versions | pinned Playwright; synthetic basemap; tolerance; re-baseline only by an explicit PR |
| R-10 | Part VIII: a future tier-1/2 assignment leaks through the cells or the URL | tier transform before aggregation; verifier precision checks; `at=` capped by the focused record's tier |

---

## 15. New findings (`findings/incoming/K1.csv`)

| id | sev | title |
|---|---|---|
| NEW-1 | S1 | Root cause of F-100: tippecanoe runs with default dropping (base zoom 14, rate 2.5), so the live tiles hold 0.03 % of sites at z3, 5.7 % at z10 and 25.6 % at z12; nothing replaces them, and the island never draws the bins it promises |
| NEW-2 | S2 | No test can see what production renders: CI never runs tippecanoe (mocked), the pure-Python fallback keeps all points but coalesces co-located entities, and fixtures use client clustering |
| NEW-3 | S3 | Tile property mismatch (`sensitivity_tier` vs `tier`) leaves every tile without a tier; the popup prints "Sensitivity tier 0" from a default, and the tier/zoom rules in `map.ts` are unused |
| NEW-4 | S2 | The bundle's 12 `<compartment>/sites.pmtiles` downloads are zero-tile archives with the GeoJSON stuffed into the metadata |
| NEW-5 | S3 | R2 custom domains need the DNS zone on Cloudflare (free) or a Business-plan CNAME setup; `surveillancegraph.org` DNS is on Squarespace, and J3 D-J3-4/TX-11 and K0 D-K0-4 omit this prerequisite |
| NEW-6 | S3 | Every one of the 12 overlay archives costs a 16 KiB header read on first view, even with no data in view (≈ 192 of 220 KB overlay bytes nationally) |

---

## 16. Limitations and command log

**Limitations.**

- **Basemap weights are directory lengths**, i.e. the compressed tile bytes as stored. Real sessions add HTTP overhead and the
  pmtiles client's leaf-directory reads (not measured). The per-session 2 MiB is an assumption.
- **The local render used SwiftShader.** GPU behaviour, frame rate and WebGL-version needs were not measured.
- **tippecanoe flag semantics** (`-r1`, per-feature zoom ranges) come from K12a [Q082] and the tool's documented defaults. The
  behaviour was inferred from the measured per-zoom counts, not by running tippecanoe here. MAP-01a's CI proves them.
- **The z0–14 extract size (≈ 69 GB)** is an inference from "each zoom roughly doubles". Cloud Armor and Cloud CDN prices were not
  re-read.
- **Growth estimates are inferences:** tile archives after retention, the static SVG, and site-list page counts.
- **Flavour names** and the basemaps-5.x ↔ tiles-v4 pairing are to be verified at MAP-02.
- **H3 cell counts** use the live points at the current tier (all tier 0).
- **Not examined:** the sharing-edge overlay on the map (K2's domain), and a Data Navigator-style overlay (K12a [Q042]). The
  In view list covers keyboard access.

**Commands** (read-only except scratchpad writes; outputs in the session scratchpad, not durable; results quoted above).

| # | when (`date -u`) | command | result |
|---|---|---|---|
| C1 | 22:08:43Z | `git branch --show-current`; `git diff --stat b051732c HEAD -- web exports ops` | `claude/next-phase-planning`; empty diff |
| C2 | 22:10:42Z; 22:10:48–22:11:05Z | `curl -sI` then `curl -s -o` for the 12 `https://surveillancegraph.org/tiles/<c>-sites.pmtiles`; `shasum -a 256` | 200, `accept-ranges: bytes`, `max-age=300`; all 12 hashes equal manifest `sig-2026-09-27-ce480ab1` (e.g. osm_physical `8c8f9a8c…`) |
| C3 | after C2 | Python PMTiles/MVT reader (`pmt.py`): per archive generator, zoom range, features and tiles per zoom | tippecanoe v2.79.0, z0–14; totals per zoom 12…250,067 |
| C4 | after C3 | `probe.py`: features in the tile containing I-80 MM 82.5, Canberra, Austin at z6–z14 | the I-80 camera present only in z13–z14 tiles |
| C5 | after C4 | `props.py`: unique entities per zoom; property distributions | §1.1 table; 227,335 `full_precision`; 0 tier; 166,142 "unresolved"; 187,329 unlabelled |
| C6 | after C5 | stored tile bytes per zoom | 42,239,340 B; z14 19,161,062 B (45 %) |
| C7 | 22:14:52Z–22:15:34Z | `curl` of `build-metadata.protomaps.dev/builds.json`; 7 `curl -r` range reads of `build.protomaps.com/20260930.pmtiles` (header, root, 5 leaf dirs; `basemap_requests.log`) | 138,478,612,042 B, z0–15, v4.15.2; the §2.1 view weights |
| C8 | after C7 | `h3.latlng_to_cell` over the 227,335 points at res 3–6 (the repo's `.venv`, h3 4.5.0) | 1,511 / 5,028 / 13,691 / 30,973 per-compartment cells |
| C9 | 22:23:46Z | `curl` of `storage.googleapis.com/zeta-medley-508121-u7-sig-public/ccby3/sites.pmtiles`; header decode | sha256 `9e9d7403…` = manifest; 0 tiles, min/max zoom 0, 736,021-char GeoJSON in metadata |
| C10 | 22:17:02Z and after | local range server + headless Chromium (Playwright from `web/node_modules`, SwiftShader) over the downloaded archives: `render.mjs`, `render2.mjs`; `expected.py` | §1.1 render table (`render_out.json` sha256 `540e2d94…`); overlay bytes national 220,576 / z12 19,160 / z14 30,141 / z15 23,088 |
| C11 | after C10 | `grep` of `import … from` in `maplibre-gl.mjs` / `maplibre-gl-worker.mjs` | both import `./maplibre-gl-shared.mjs` |
| C12 | 22:16:02Z–22:16:06Z | `curl` of 2 glyph PBFs, the sprite JSON/PNG and the `basemaps-assets` README | §2.1 sizes; OFL fonts, MIT-derived sprites |
| C13 | 22:19:53Z | `dig +short NS surveillancegraph.org` | `nsc1–4.squarespacedns.com` |
| C14 | 22:20:02Z–22:20:06Z | `curl` of Cloudflare docs `r2/buckets/public-buckets/index.md` and `dns/zone-setups/partial-setup/index.md` | "The domain being used must have been added as a zone in the same account as the R2 bucket"; partial setup "only available … on a Business or Enterprise plan" |
| C15 | 22:29:14Z | `curl` status of `https://surveillancegraph.org/r/` and `/map/style.json` | 404 (no `/r/` landing) and 200 |
| C16 | during | `grep` for `renderModeForZoom\|pointVisibleAtZoom\|MIN_POINT_ZOOM_BY_TIER` in `web/src` outside `lib/map.ts` | no hits |
| C17 | 22:35:52Z–22:36:20Z | re-ran C5 (`props.py`) and C10 (`render2.mjs`) to stamp NEW-3 and NEW-6 | identical results: 0 of 227,335 features carry a tier; overlay bytes 220,576 / 19,160 / 30,141 / 23,088 |
