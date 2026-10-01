# K13 — UX synthesis: information architecture and product spec

- **Row:** K13 (Stream K, synthesis) · **Written:** 2026-09-30 (work window 23:02:11Z–23:29:27Z, `date -u`)
- **Worktree HEAD at write time:** `a1bc4dad` (branch `claude/next-phase-planning`, clean). Nothing under `web/`, `exports/`
  or `api/` was read for this row beyond what the K rows cite; every `code` claim below is the cited row's.
- **Operator input answered:** U-003.1…U-003.11, U-003.G and U-003.X (via K12a/K12b), U-004, U-005, U-007, within U-008
  (≤ $300/month) and U-011 (no outside contact). Verbatim text: `feedback/OPERATOR_FEEDBACK.md`.
- **Inputs read (P1: nothing cited that was not read):** META_PLAN §3, §6 Stream K and L, §7 and §7.1; `feedback/OPERATOR_FEEDBACK.md`;
  `design/K0` (whole), `K1` §0, §3.5–3.6, §4.1–4.8, §5, §7, §8, §11–15; `K2` §0, §2–§14; `K3` §0, §3, §5–§14; `K4` §0, §3.1, §5–§13;
  `K5` §0, §4–§12; `K6` §0, §3, §5.3–§5.5, §6.3, §9, §12–§18; `K7` §0, §5.1–§5.4, §8–§14; `K8` §0, §4–§13; `K9` §0–§2, §4, §6,
  §10–§15; `K10` §0–§3, §17–§23; `K11` §0, §3, §5, §8–§15; `K14` §0, §2, §3.4–§3.7, §4.3, §4.6–§4.13, §5–§12; `J3` §0, §4.1–§4.3,
  §5, §6.1, §7, §8, §11–§13; `G3` §0, §5.3–§5.4, §11–§12; `G2` §0, step 0, §5, §6; `D3` (whole); `L3` §0, §2, §5, §7, §9, §10
  (landed at `a1bc4dad` during this row); `research/K12a` §0 and headings; `research/L1` §0, §6; `research/L2` summary and §4;
  `research/F5` PKG list; `review/K12b` §1, §2, §7, §8 and `data/k12b_ideas.csv`; `review/REVIEW_SYNTHESIS.md` §0, §6–§9;
  `findings/incoming/K0, K1, K2, K3, K4K5, K6, K7K8K11, K9K10, K12b, K14, L1, L2, L3.csv`.
- **Evidence classes (P1):** everything here is **`inference`** built on the cited rows (their own evidence classes carry
  through). No new measurement, no live read, no browser session was run for this row. Costs are the rows' inferences, added up.
- **Status vocabulary (P5):** nothing here is engineered or verified. It is a design, a requirement draft set and a ticket plan
  for S1/S2/T1/T3. Acceptance journeys are agent walkthroughs at acceptance, never user research (P4).
- **P3/P14/P16:** production was not touched; no secrets; no external request.
- **Writes:** this file, `data/k13_requirements.csv` (51 rows) and `data/k13_tickets.csv` (118 rows) only.

---

## 0. On one page

**What K13 does.** It turns fourteen K-row designs, J3, G3's release model, L3's confidence program and the operator's asks
into **one site**: one navigation, one route registry, one symbol lexicon, one set of shared modules with one owner each, one
URL-state contract, one redirect generator, one ticket list and one capstone test.

**Conflicts reconciled: 32** (§1). The ones that matter most:

| # | conflict | decision |
|---|---|---|
| C-01 | "hollow" and "dashed" meant different things in K1, K2, K6 and K14 | one lexicon: hollow = one source (points/areas only); line pattern = access kind only; currency = muted ink + a date or word; raspberry = disagreement; amber = provisional; hatch = absence |
| C-07/C-08 | circular ownership of the static SVG generators; K0's CSP vs K14's self-styled SVG files | one **static figure kit** (FIG-01a/b); inline SVG styled by page classes; downloadable SVGs under their own no-script policy |
| C-09 | J3 vs K9/K10 source explorer | all **23 K9/K10 changes adopted**; TX-05a/b superseded by UX9-3/UX10-3a/b; `/data-freshness/` 301s to `/sources/` |
| C-10 | K3 search vs K2 entity search (and K1/K4 place search) | **one search stack**: release-pinned FTS5 + static shards serve the header, `/search/`, the map, the dossier index and the explorer |
| C-11 | `sig.workspace-state/2` extended three ways | one parameter registry; `years`→`dated`, `kind=site`→`type=record`, `jurisdiction` filters, `frame`/`bbox` only frame |
| C-12 | islands parse place/source facets and ignore them | W0 visible notice; then a surface × facet conformance harness each T2 ticket must pass |
| C-27/C-28 | K5/K2 overlap with L3 (dedup export, edge backend) | L3 CONF-07b/CONF-06 own the data; K13's QB-01 and K2's GX-02 own the rendering |

**Information architecture (§2).** Six header sections plus a search field — **Places · Explore (Map, Graph, Search,
Disagreements) · Organizations · Watch · Sources & data · About**. Every public route is in K0's page-type registry: **T0**
(records, print, feeds, dispute; 0 script), **T1** (≈ 25 route families; ≤ 20 KiB enhancement), **T2** exactly three
surfaces (`/map/` ≤ 360 KiB, `/explore/` ≤ 120 KiB, `/search/` ≤ 60 KiB), T3 `/curate/**` never published. New route
families: `/sources/**`, `/entity/**`, `/graphs/**`, `/explore/`, `/disagreements/**`, `/changes/**`, `/data/**`,
`/releases/**`, `/status/**`, `/quality/` (L3), `/s/<pub>/**`, `/glossary/`, `/about/**`, `/task/<handle>/`, rebuilt
`/watch/**`, `/evidence/**` and `/research-queue/**`, and dossiers at four levels under `/dossier/<alpha-3>/…`.

**Shared modules (§3), one owner each:** page-type registry (UXK0-1) · budgets + real-sized fixture (UXK0-2) · CSP (UXK0-3) ·
enhancement kit `<sig-table>`/`<sig-typeahead>`/`<sig-cite>`/`<sig-activate>` (UXK0-4) · `sig.workspace-state/2` (UXK0-5) ·
tokens (UXK14-1) · lexicon + glossary (UXK14-4) · chrome (UXK14-2) · component kit (UXK14-3a/b) · labels, slugs and handles
(GX-01) · static figure kit (FIG-01a/b) · `<Figure>` (TX-09) · `<ProvenancePanel>` (TX-08a) · redirect generator (JUR-05) ·
search index and shards (SRCH-01/05) · dossier template (VIZ-02).

**Tickets (§7; `data/k13_tickets.csv`): 118 tickets, ≈ 102.5 fresh-context runs.** The per-row outlines summed to 120 units and
≈ 100.5 runs; K13 merged, superseded or moved to Stage-B T1 **18** units and added **16** tickets for gaps routed to K13 (W0
quick wins, the figure kit, disagreements, quality-basis rendering, change feeds, merged acceptance, capstone).

| wave | purpose | tickets | runs |
|---|---|---:|---:|
| **W0** | honesty quick wins in G2's republishes #1–#2 (data unchanged or re-exported for attribution) | 6 | 4.5 |
| **W1** | foundations (registry, budgets, CSP, kit, tokens, lexicon, figure kit) and UX-owned data-layer prerequisites (labels, placement, tiles, basemap, transparency exports, search index) | 39 | 36.0 |
| **W2** | core surfaces: every U-003 ask gets a working page | 43 | 37.0 |
| **W3** | explore surfaces, overviews, embedded map, watch lane and feeds, real evidence, snapshots, changes, disagreements | 26 | 22.0 |
| **W4** | T1 enhancements, contribution path, capstone, announce readiness | 4 | 3.0 |

External prerequisites (G2 ACT-*, G3 REL-*, F5 PKG-*, L3 CONF-*, I8) are named in the CSV's `depends_on`/`data_prereqs`
columns and are **not** counted here (P9).

**Traceability (§5): complete.** Every ask U-003.1…U-003.11, U-003.G, U-004, U-005 and U-007 maps to a design row, ≥ 1
requirement, ≥ 1 ticket and ≥ 1 capstone journey (§5.1). All 32 K12b ideas are dispositioned: **29 accepted** (22 as proposed, 7
modified) and **3 deferred**; inside accepted ideas, 3 sub-proposals are rejected and 2 deferred (§5.2).

**Could not be reconciled by an agent (§10):** (1) U-003.2's "global graph … lays bare all we know" vs the spec's no-hairball rule
and SIG-IDENT-030 — K13 adopts aggregated overviews and needs the operator's confirmation (D-K13-1); (2) the 969 review-flagged
organisations — without D-K2-1's operator review, entity pages, network labels and organisation search ship with "pending
publication review" (D-K2-1 is the single most blocking decision for U-003.2); (3) whether publishing the de-duplication (L3
CONF-07b) is an announce-readiness criterion (D-K13-4); (4) the DNS move for the zero-egress origin (Q-31).

---

## 1. Reconciled conflicts (one decision each)

| id | conflict (rows) | decision | why | lands in |
|---|---|---|---|---|
| **C-01** | **Symbol meanings.** K1: hollow = single source, dashed look = candidate. K2: dash = historical, hollow = undated. K14: currency strokes (solid → dotted) *and* access kinds (solid/dashed/double) both on lines; dashed logo edge. K6 NEW-2 showed the collision on one dossier page | **One lexicon (UXR-11).** Fill = corroboration by independent lineages (UXR-14); **hollow = exactly one source, on points and areas only**; double ring + ≠ + raspberry = contested; **line pattern = access kind only** (configured solid · stated dashed · observed double); **currency = muted ink + a date or word** ("Historical, recorded 2020-01-28", "undated"), never a pattern and never hollow; Provisional = amber outline + ◔ + word; the hatch = absence only; entity kind = shape. The logo's dashed edge is brand, never a legend symbol | K6's resolution is the only one that keeps one meaning per page when Figure 1 and a network figure sit together; K14's own lexicon already reserves colour and texture this way | UXK14-4, FIG-01a/b, MAP-03a, GX-06b, GX-09a |
| **C-02** | Map technology colour: K1 ≤ 8 categorical colours vs K14 "categorical data = one hue + shape" | **One data hue**; technology by facet, legend with counts, list/panel and the z15 text code (UXR-15). Revisit once F5 PKG-07 typing is live, by a K14 amendment through the palette validator | 77 % of `traffic_camera` rows are mistyped today (L2 NEW-6): a colour key would teach wrong categories; 8 hues would collide with the reserved raspberry/amber/blue | MAP-03a/03b |
| **C-03** | K1 greys **and hatches** cells where a filter cannot apply at the current zoom; K14: the hatch means absence only | Grey/desaturate + the note, **no hatch**; K1's coverage layer keeps the hatch because "no source covers this" *is* absence | one texture, one meaning (SIG-UI-007) | MAP-03b |
| **C-04** | K1 status "provisional (candidate)" vs K14/L3 **Provisional** = produced by a method not independently evaluated | Lifecycle value is **"Candidate"**; "Provisional" stays the amber epistemic label (UXR-12) | same word, two concepts | MAP-01b/03b, UXK14-5 lint |
| **C-05** | K1 says "sites" (tile layer, "sites in view", "N sites"); K4/K14 say "records"; L3 publishes intervals of "listed cameras" | UI says **"records"**; "camera sites"/"listed cameras" only for de-duplicated counts, shown as L3's interval once CONF-07b ships (UXR-13). Internal layer and API names (`sites`) unchanged | no cross-source de-duplication reaches any published row today (L1 NEW-8; dossier counts up to 2.25× inflated, L2) | MAP-03a, JUR-03, QB-01, UXK14-5 |
| **C-06** | "Corroborated (≥ 2 sources)" (K1) vs mirrors count once (K2 H-11, P15) vs independence never declared (L1 NEW-4) | Encoding counts **independent lineages**; until L3 CONF-04/07b the legend reads "2+ source records; republications not yet collapsed" (UXR-14) | otherwise the DeFlock/OSM republishes read as corroboration | MAP-01b, QB-01 |
| **C-07** | **SVG generator ownership** (K6 NEW-3): K1 "MAP-05 owns the renderer, K6 consumes"; K2 cites "K6's generator"; K4 needs "K6 locator"; K5 needs "K6 chart component"; K14 UXK14-8 "data-viz helpers" | **One static figure kit**: FIG-01a (projection, simplification, H3 binning rule `static-12px@1`, outlines, locator, CSP-safe serializer, download renderer) and FIG-01b (bipartite and radial layouts, charts, legends from the lexicon, table twins, print rules). Compositions stay with page owners: national overview MAP-05; dossier map/locator VIZ-01a; dossier networks VIZ-01b; entity ego GX-06b; overviews GX-08a; K5 chart DSRC-02; source runs strip UX10-3a | five rows, one algorithm set; byte-determinism and CSP rules enforced once (UXR-16) | FIG-01a/b |
| **C-08** | **CSP vs self-styled SVG** (K6 NEW-4): K0 `style-src 'self' <hashes>` everywhere; K14 standalone SVGs carry their own `<style>` | Inline figures use classes from the page stylesheet (no `style=""`); **standalone figure files** are served with `default-src 'none'; style-src 'unsafe-inline'; img-src data:; sandbox` + `nosniff` — a script-less document cannot execute, so `unsafe-inline` styles carry no XSS surface there; downloads only for country/admin-1 dossiers (D-K6-5) | keeps K0's strict page CSP and K14's dark-aware downloads | UXK0-3, FIG-01a |
| **C-09** | **J3 source explorer vs K9/K10**: 23 explicit changes (K9 C-1…C-12, K10 C-13…C-23) | **All 23 adopted.** Nested funnel → lifecycle partition (C-1); 3 pre-rendered views, one page each (C-2); asc/desc sort routes (C-3); no "next run" on release pages (C-4); volatility ships now (C-5); last upstream change vs last change in SIG's records (C-6); `one_time_load` + `run_record_missing` (C-7); per-source statements slice (C-8); a `publisher` field (C-9, C-16); lifecycle as column and facet (C-10); `/data-freshness/**` 301 (C-11); one status row component (C-12); execution-keyed history (C-13, C-14); `notes` never rendered + a field publish matrix (C-15); GL-GATE-07 disclosure (C-17); observed robots conduct (C-18); targets (C-19); versions (C-20); assignment basis (C-21); entity browse (C-22); changelog (C-23). Multi-facet filtering: `<sig-table>` on `/sources/` **and** `type=source` facets in `/search/` — neither is a new T2, which satisfies J3's "no fourth island" | K9/K10 are later, measured, and J3-compatible except where J3's premises were wrong (non-nested sets, digest churn) | TX-05a → **UX9-3**; TX-05b → **UX10-3a/b**; funnel → UX9-1; freshness → UX9-2; report shape → UX10-2; slices → UX9-4 |
| **C-10** | **K3 search vs K2 entity search**; also K1 map place search, K4 index search ("lazy 0.2 MB index on focus"), K12b "expose `/v1/search`" | **One search stack (UXR-23/24).** K3 owns the index, engine, API route, results page, shards and `<sig-typeahead>`; K2's explorer "search to node", K1's place box and K4's index form consume the same shards; no separate entity index; no live-spine `/v1/search` on pages; K3's entity links use K2's URL keys | one ranking, one place resolution, one budget (≤ 50 KiB per shard) | SRCH-01…05, MAP-04, JUR-04, GX-09b |
| **C-11** | **`sig.workspace-state/2` extensions**: K1 adds `vendor`, `operator`, `seen`, `status` as common + `bbox`; K2 adds `path`, `currency`, `years`; K3 adds `type`, `within`, `location`, `cursor`; K1 links `/search/?kind=site` | **One parameter registry (UXR-09).** `type` = result type, `kind` = entity type (`kind=site` → `type=record`); `seen` = when SIG observed (belief-side); `dated` replaces K2's `years` for world dates (K14: never conflate them); `jurisdiction` is a filter including descendants, and the map frames on it only when no `at=` is given; `frame=`/`bbox=` frame without filtering and canonicalise to `at=` | three rows, one contract, citable URLs | UXK0-5 |
| **C-12** | **Facets accepted but ignored** (K6 NEW-1): all three islands parse `jurisdiction`, `source`, `location`, `technology` and render the national view | W0: a visible notice on each island + dossier links stop passing ignored facets (UXW0-6). Then a **surface × facet conformance harness** (UXK0-5) that MAP-03a/03b, SRCH-05 and GX-09a/b must pass (UXR-10) | the dossier Explore bar depends on it | UXW0-6, UXK0-5 |
| **C-13** | Place segments: K2 `/graphs/<id>/usa-tx/`, K7 `/watch/place/<key>/`, K8 `/evidence/place/<key>/`, K11 `/research-queue/place/usa/tx/`, handles `T-usa-tx-…` | **Routes use the K4 display path with slashes** (`usa/tx`, `usa/tx/harris-county-48201`); **handles** use the dash-joined token; vendor routes use K2 entity keys (UXR-07) | predictable links; no bare two-letter codes (the ID/MN lesson) | GX-08a, WX-04a, EV-02, RQ-03a |
| **C-14** | Two identifier grammars: K2 entity keys (7-char base32, frozen) vs K11 handles (4-char, extended on collision); K8/K7 reuse K11; K1 panel links `/entity/<id>/` | **One module (GX-01)** with shared slug + hash primitives and the Part VIII screen; both lengths kept for their jobs (URL keys for 10⁴–10⁵ entities; short handles for tasks, campaigns, watch items, artifacts) (UXR-17) | one derivation, one person-name screen | GX-01, GX-03, RQ-01, WX-01, EV-02 |
| **C-15** | Four redirect mechanisms: K2 slug history, K4 slug history + stubs, K9 nginx map, K11 `handles_history` | **One generator** (JUR-05) consuming every history file, emitting one `redirects.conf` for G3 REL-03b plus static stubs (UXR-08) | one include, one crawl check | JUR-05 |
| **C-16** | `/network/`: K0 "redirect or a T1 page"; K2 301 → `/explore/?v=2&overview=access` with content at `/graphs/access/` | **K2's**; the no-JS reader lands on `/explore/`'s static first paint (overview SVG + table) | the graph explorer supersedes the island | GX-09a |
| **C-17** | **Site record link target**: K1 fetches `/r/…json`, K3 links `/r/…`, K12b I-16 proposed `/site/<id>/`; the `/r/` archive stays dark until G2 ACT-24 (C6 PG-7) | Until ACT-24, site links go to the row in `/dossier/<path>/sites/` and the map panel renders tile properties; afterwards, the T0 record. **No `/site/` route** (UXR-18) | never link a 404; no second record page | MAP-03a, MAP-05, SRCH-04 |
| **C-18** | Place-search entry points: K1 `/map/place/` static form; K4 lazy full place index on focus (≈ 0.2 MB gz); K3 shards | **Shards only**; no `/map/place/`; the index form GETs `/search/?type=place` with an nginx first-letter fallback to `/dossier/a-z/<letter>/` while the API is unreachable | K4's full index is at the 200 KiB per-interaction ceiling; shards are ≤ 50 KiB | MAP-04, JUR-04 |
| **C-19** | "Enhanced islands" proposed for watch (K7 §5.4, incl. a map), evidence (K8 §4.5), queue (K11 §5.2), dossier sources (K5 §4.2) and the index (K4 §6) vs K0's three T2 surfaces | **T1 kit elements only** (`<sig-table>`, `<sig-typeahead>` over ≤ 200 KiB shards) in ENH-01; the watch map and K10's source-page map preview are deferred (link `/map/?source=` instead) (UXR-35) | K0 §4.2; budget and test cost | ENH-01 |
| **C-20** | Chart ownership and brushing: K5 "chart island ≈ 10 KB, shared with K6"; K6 "brushing is DSRC-05's" | Static charts in FIG-01b; **brushing deferred**; sort/filter via ENH-01 | no demonstrated need; budget | FIG-01b, ENH-01 |
| **C-21** | JSON-LD: J3 D-J3-7 linked files only (D17: no script element "including JSON-LD"); K0 D-K0-5 classifies it as data | **Linked files only in Round 11** (UXR-32); K0's classification stays for a later ADR note | both satisfied now | TX-10a |
| **C-22** | `/data-freshness/`: J3 keeps the URL; K9 renames to `/sources/` with 301s | **301** (D-K9-3; operator renamed it "Sources"), through JUR-05's generator | one canonical URL | UX9-3, JUR-05 |
| **C-23** | Sources pagination: J3 ≤ 200 rows/page; K9 one page per view | **K9**, with the build-time size check paginating at 200 rows only above 120 KiB | find-in-page is the best no-JS search | UX9-3 |
| **C-24** | **Dossier template ownership**: K4 JUR-03/04 build pages; K5 DSRC-02 adds a section; K6 VIZ-02 composes figures; K7 WX-04a adds "Next decisions"; K11 adds gap links; K14 adds the brief and print | **VIZ-02 owns the one template** (UXR-19); the others deliver sections as components | print, order and budgets need one owner | VIZ-02 |
| **C-25** | `<Figure>` and `<ProvenancePanel>`: J3 TX-09/TX-08a, K5 `figures[]`, K6 `fig-*` ids, K2 edge panel, K8 claim viewer, K1 selection panel, K14 visuals | **One data contract each** (TX-09, TX-08a) and **one visual** (UXK14-3a/b); every surface renders through them (UXR-33/34) | provenance must not read differently on two pages | TX-08a, TX-09, UXK14-3a/b |
| **C-26** | Empty-state copy owned five ways (K7 WX-07, K8 EV-01, K3 §6.4, K6 V-7, K14 §6.4) | One `EmptySurface` (UXK14-3b) + one copy registry (UXK14-11); W0 copy already uses the five-part pattern (UXR-36) | one voice | UXW0-2, UXK14-3b, UXK14-11 |
| **C-27** | **K5 DSRC-04 vs L3 CONF-07b** (both publish co-location/de-duplication fields); L3 §5.2 "K5/K1/K2 render" names no UX owner | CONF-07b owns the **export**; new **QB-01** owns the **rendering** (basis block, intervals, "possible duplicate"); DSRC-04 retired | exactly one owner per half (P9) | QB-01 |
| **C-28** | **K2 GX-02 vs L3 CONF-06**: K2 put L1 NEW-10's edge fix "in the same wave"; L3 owns the backend | CONF-06 = backend (1970 dates, supersession, one classifier); GX-02 = export fields and labels; a 1970 value renders "undated" until CONF-06 lands | L3 §9 exactly-one list | GX-02 |
| **C-29** | Preact migration: K0 UXK0-6 as its own ticket vs K0 R-7 "fold into K1–K3 rewrites" | **Folded**: MAP-03a, SRCH-05, GX-09a; GX-09a (last) removes `@astrojs/react` and adds the bundle-content gate | avoids migrating code that is about to be rewritten | MAP-03a, SRCH-05, GX-09a |
| **C-30** | ADR/spec tickets (K0 UXK0-7, K1 MAP-00, K6 VIZ-00's spec hand-off) vs META_PLAN **T1** (Stage B writes ADRs and `spec_src`) | **Moved to T1** (not Round-11 runs); the AGENTS.md gotcha rewrites ride UXK0-1 because they must change with the code | P10; no double work | T1, UXK0-1 |
| **C-31** | Navigation: K7 "Watch stays in Explore"; J3 "Data & downloads in the global nav"; K9 "Sources"; K14 six sections with the queue under About; L3 `/quality/` under "Trust and method" | **Six sections (UXR-01)**: Watch is top-level (advocate A2 and organizer O2 primary task); Sources & data holds Sources, Evidence, Downloads & API, Releases & changes, Status; About holds How sure is SIG? (`/quality/`) and Open questions; Disagreements sits under Explore. The queue is reached mainly from absence chips and "What we don't know" (UXR-29) | ≤ 6 sections (K14 NEW-9); organizers act from gaps, not from a menu | UXK14-2 |
| **C-32** | Overlapping per-row acceptance tickets (JUR-06, DSRC-06, GX-10, VIZ-05, K7/K8/K11 journeys) each re-crawling and re-promoting | Merged into **ACC-PLACES** (W2) and **ACC-EXPLORE** (W3); MAP-07, SRCH-07 and TX-16 stay separate (distinct live gates); **CAP-01** runs D3's 13 journeys | one crawl per wave, one Class S readout per republish | ACC-*, CAP-01 |

Items K12b routed to K13 (NEW-14, NEW-17, NEW-19, NEW-21) are not conflicts; §5.3 dispositions them.

---

## 2. Information architecture

### 2.1 Navigation (header, ≤ 6 sections + search; UXR-01)

| section | menu items (route) | primary persona / journey | appears when |
|---|---|---|---|
| **Places** | Dossier index `/dossier/` · A–Z `/dossier/a-z/<l>/` · Not yet placed `/dossier/unplaced/` | advocate A1–A4, organizer O1 | always |
| **Explore ▾** | Map `/map/` · Graph explorer `/explore/` (+ static `/graphs/`) · Search `/search/` · Disagreements `/disagreements/` | journalist J2–J3, resident | per route in the release |
| **Organizations** | `/entity/` hub → per-type A–Z → entity pages | journalist J2, organizer O1 | after GX-06a |
| **Watch** | Upcoming decisions `/watch/` · Feeds `/watch/feeds/` | advocate A2, organizer O2 | always (typed empty state until WX-01) |
| **Sources & data ▾** | Sources `/sources/` · Evidence `/evidence/` · Downloads & API `/data/` · Releases & changes `/releases/`, `/changes/` · Status `/status/` | journalist J1/J5, developer | per route in the release |
| **About ▾** | About & how it works `/about/` · How to read SIG `/visual-language/` · Glossary `/glossary/` · Methodology `/methodology/` · How sure is SIG? `/quality/` · Editorial standards · Corrections · Open questions `/research-queue/` · Dispute `/dispute/` | everyone, skeptic | always |
| (search field) | header `<sig-typeahead>` → `/search/` GET | all | always (plain GET without JS) |

Mobile: logo, search icon to `/search/`, and a `<details>` menu with the same sections (no JavaScript). Record pages show
breadcrumbs (Country › State › County › Place, or Organizations › Type › Entity). The footer is the same everywhere: licence
line, "Dispute or correct", About, Releases, Status, Other public resources, "not a census / not advocacy".

### 2.2 Route registry (the site map)

Page types and budgets are K0's (§2.3). "No-JS" is the equivalent the page must link or be. Owners are ticket ids from
`data/k13_tickets.csv`; W = the wave in which the route first ships.

| route | type | no-JS equivalent | data contract (§4) | owner | W |
|---|---|---|---|---|---|
| `/` home | T1 | itself | capability table, ≤ 6 `<Figure>`s, example-question contract | UXK14-6 (W0 copy: UXW0-1) | W0/W2 |
| `/about/`, `/about/how-to-read-a-dossier/` | T1 | itself | operator text; golden dossier | UXK14-6, UXK14-11 | W2 |
| `/glossary/` | T1 | itself | Appendix E + `lexicon.json` | UXK14-4 | W1 |
| `/methodology/`, `/editorial-standards/`, `/visual-language/` ("How to read SIG"), `/style-guide/`, `/coverage-metrics/`, `/corrections/`, `/contribution-back/` | T1 | itself | In-brief boxes; coverage tiles as `<Figure>`s | UXK14-4, TX-09 (W0 copy: UXW0-1) | W0–W2 |
| `/quality/` | T1 | itself | `quality.json` (`sig.quality-report/1`) | **L3 CONF-12** (external) | L3 W4 |
| `/dossier/` + `/dossier/sort/<k>/`, `/dossier/by/<dim>/<v>/`, `/dossier/a-z/<l>/` | T1 | itself | `sig.dossier-index/2` | JUR-04 | W2 |
| `/dossier/<a3>/[<sub>/[<namelsad-slug>-<geoid>/]]` (country, admin-1, county, place) | T1 (T0 print) | itself | per-dossier JSON + `sig.dossier-sources/1` + figures | JUR-03, VIZ-02 | W2 |
| `/dossier/<path>/sources/` (+ sort routes) | T1 | itself | `sig.dossier-sources/1` | DSRC-02 | W2 |
| `/dossier/<path>/sites/` (+ `page/<n>/`) | T1 | itself (also the map's no-JS list) | sites files + placement | MAP-05 | W2 |
| `/dossier/<path>/print/` (country, admin-1 only) | T0 | itself | as dossier | VIZ-02, UXK14-9 | W2 |
| `/dossier/unplaced/` | T1 | itself | placement reasons | JUR-03 | W2 |
| legacy `/dossier/<old>/`, split/correction pages | T0 | itself | `jurisdiction_slug_history.json` | JUR-05 | W2 |
| `/map/` | **T2 map** | static overview SVG + places table + sites lists + API bbox HTML | `sig.map-tiles/2`, `sig.map-dict/1`, basemap PMTiles | MAP-05, MAP-03a/b, MAP-04 | W2 |
| `/entity/` hub, `/entity/<type>/` A–Z | T1 | itself | `sig.entity-label/1` | GX-06a | W2 |
| `/entity/<type>/<slug>--<hash7>/` (+ `relationships/<rel>/<n>/`, `index.json`) | T1 | itself | `sig.entity-page/1` | GX-05a/b, GX-06a/b | W2/W3 |
| `/id/<type>/<uuid>` | redirect | — | `sig.slug-history/1` | GX-03 → JUR-05 | W1/W2 |
| `/graphs/`, `/graphs/<overview>/`, `/graphs/<overview>/<a3>/<sub>/` | T1 | itself | `sig.graph-overview/1` | GX-08a/b | W3 |
| `/explore/` | **T2 graph** | `/graphs/**` + entity pages + hop lists | overview files + entity JSON twins + `sig.graph-components/1` | GX-09a/b | W3 |
| `/network/` | 301 → `/explore/?v=2&overview=access` | `/graphs/access/` | — | GX-09a (W1: GX-02 fixes today's page) | W1/W3 |
| `/search/` | **T2 search** | API `…/search?format=html` (server-rendered) | `sig.release-search-index/2`, shards, `sig.search-results/2` | SRCH-04/05 | W2 |
| `/disagreements/`, `/disagreements/place/<path>/` | T1 | itself | contradiction index + placement disagreements | CX-01 | W3 |
| `/watch/` + `page/<n>/`, `place/<path>/`, `kind/<k>/`, `vendor/<entity-key>/`, `technology/<c>/`, `item/<handle>/`, `history/<path>/`, `feeds/` | T1 | itself | `sig/watch/2` (`sig.watch-item/1`) | WX-04a | W2 |
| `/watch/**.ics`, `.xml`, `.json`, `feeds.opml` | T0 data | — | feeds | WX-04b | W3 |
| `/sources/`, `/sources/runs/`, `/sources/rights/` (+ `sort/<col>/<dir>/`, `by/<dim>/<v>/`) | T1 | itself | `sources.json`/`.csv` (`sig.source-row/1`) | UX9-3 | W2 |
| `/sources/<id>/` + `runs/`, `captures/`, `captures/changes/`, `versions/`, `targets/`, `entities/`, `dossiers/`, `changelog/` | T1 | itself | `sig.source-page/2`, `executions.jsonl`, `versions.json` | UX10-3a/b, UX10-4 | W2/W3 |
| `/data-freshness/**` | 301 → `/sources/…` | — | — | JUR-05 | W2 |
| `/evidence/` + facet routes, `/evidence/artifact/<handle>/`, `…/diff/<a>..<b>/`, `/evidence/claim/<id>/` | T1 | itself | `sig.evidence-artifact/1`, claim views | UXW0-2 (interim), EV-02, EV-03 | W0/W2/W3 |
| `/research-queue/` + `place/<path>/`, `type/<code>/`, `role/<r>/`, `campaign/<handle>/` | T1 | itself | task shards | RQ-03a/b (W0: UXW0-3) | W0/W2 |
| `/task/<handle>/` (`/task/<uuid>/` → 301; `/task/new/**` retired) | T1 | itself | `sig.task-page/1` | RQ-03b | W2 |
| `/data/`, `/data/dictionary/`, `/data/api/` | T1 | itself | data manifest, column registry | TX-10a/b | W2 |
| `/releases/`, `/releases/<pub>/` | T1 | itself | release landing, changelog | G3 REL-03b (index), TX-14 | W3 |
| `/releases/<pub>/data/**` | T0 | itself | integrity manifest | TX-10b | W2 |
| `/changes/` (+ Atom feeds per place and source) | T1 (+ T0 feeds) | itself | `changes/` diffs | CHG-01 | W3 |
| `/status/`, `/status/sources/[<id>/]`, `/status/issues/`, `/status/state.json` | T1, **status clock** (not citable) | itself | status lane files | TX-07, TX-06 | W2 |
| `/r/<pub>/**` records and evidence anchors | T0 | itself | P32.13 records + statements | TX-08a/b (exposed with G2 ACT-24) | W3 exposure |
| `/s/<pub>/**` snapshots of T1/T2 | as source type | as source | same files | TX-13b | W3 |
| `/research-dossier/**`, `/intake/**` | T1 / T0 | — | Round-10 | G2 (dark until step 7) | — |
| `/dispute/`, 404/410/500 | T0 | itself | — | UXW0-4, UXK14-3b | W0/W1 |
| `/curate/**` | T3 | never published | — | ADR-068 | — |

### 2.3 Page types and budgets (K0 §4.3, with K13 additions)

| type | routes | initial JS (gzip) | document | notes K13 adds |
|---|---|---|---|---|
| **T0** record, print, feeds | `/r/**`, `…/print/`, `/dispute/`, feeds, error pages, legacy stubs, API `format=html` | **0** (no `<script>`) | ≤ 150 KiB | standalone figure SVGs: T0 response policy (C-08), ≤ 30 KiB gzip per map (SIG-UI-DV07) |
| **T1** content | everything in §2.2 not T0/T2 | ≤ 20 KiB, never render-blocking; ≤ 40 KiB after an action; ≤ 200 KiB data per interaction | ≤ 150 KiB | a dossier's **activated map box** is measured as T2 map after the click (K6 §5.4); `/status/**` is T1 with the status clock |
| **T2 map** | `/map/` (+ `/s/<pub>/map/`) | ≤ 360 KiB | ≤ 100 KiB | first-view tiles + glyphs ≤ 1.5 MiB; Lighthouse mobile ≥ 0.75 |
| **T2 graph** | `/explore/` | ≤ 120 KiB | ≤ 100 KiB | ≤ 200 KiB per overview/expansion |
| **T2 search** | `/search/` | ≤ 60 KiB | ≤ 100 KiB | header typeahead ≤ 20 KiB as a T1 element |
| T3 | `/curate/**` | ADR-068 | — | never published |

No fourth T2 surface (UXR-35). Every route is classified in `page-types.ts` with owner and data contract (UXR-02).

### 2.4 Cross-linking rules

- **R-1 Figure → evidence in ≤ 2 actions** on every page type, JS on and off (UXR-04): figure → breakdown/record list →
  claim anchor or evidence artifact.
- **R-2 Every mention is a link** to its object's page, labelled by the shared module, or a typed absence; ids only in
  Identifiers / Technical details (UXR-03).
- **R-3 Every page links sideways** (matrix below; UXR-05).
- **R-4 Ground truth leaves the site**: every source and evidence page has an upstream link or a named absence; dossiers and
  About carry "Other public resources" (UXR-06).
- **R-5 Place-scoped pages hand their place to the explore surfaces** with `jurisdiction=`; targets apply it or say they do
  not (UXR-10).
- **R-6 Never link a 404**: a link to a route not in this release degrades to the nearest existing page (K1 "graceful
  dependency"); the link crawl enforces it (K0 §4.12.10).
- **R-7 Every page carries** the release stamp and a cite action (REL-02, TX-13a); citations are path-pinned (`/s/`, `/r/`).
- **R-8 Links are built with `withBase()`** so snapshots stay self-contained (UXR-25).

**Sideways-link matrix** (extends K14 §5.2; "→" = required link or typed absence):

| from | → |
|---|---|
| Dossier | parent/child places · map (`jurisdiction=`) · graph (`jurisdiction=`) · scoped search · its watch page · its open questions · its sources ledger · organizations placed there · disagreements for the place · downloads · print |
| Entity page | places it operates in · relationship counterparties · `/explore/?focus=` · sources · evidence per claim · tasks and watch items on it · "possibly the same" entities |
| Source page | dossiers it contributes to (same numbers as the dossier, SIG-TRANSP-D40) · entities · runs · captures · versions/downloads · upstream homepage and terms |
| Evidence artifact | claims it supports → records/entities/places · source · upstream (lane rule) · tasks it could close · watch items citing it |
| Task / campaign | subject entity · place · evidence so far · suggested sources · records-request draft |
| Watch item | body/vendor/contract entities · place · source document · evidence · related tasks · `.ics` |
| Map panel | record (per UXR-18) · operator/vendor entity · place · sources · evidence · cite this view · dispute |
| Graph node / edge | entity page · edge evidence via `<ProvenancePanel>` (≤ 2 actions) · source |
| Search card | its typed page · map framed on a place · "search within" |
| Any `<Figure>` | definition · artifact pointer · rows (download) |

### 2.5 URL scheme, parameters and redirects

| object | canonical URL | stable key | on change |
|---|---|---|---|
| Place | `/dossier/<alpha-3>/<iso-sub>/<namelsad-slug>-<geoid>/` (K4 §3.1) | the jurisdiction key (`jkey`) | 301 (moved), 300 split page (ID, MN), correction page (BD, NL) |
| Entity | `/entity/<type>/<name-slug>--<hash7>/` (K2 §3.3) | hash of the UUID, frozen | 301 rename/merge/re-type, 300 split, 410 withdrawn; `/id/<type>/<uuid>` → 302 |
| Task, campaign, watch item, artifact | `/task/<T-handle>/`, `/research-queue/campaign/<M-handle>/`, `/watch/item/<W-handle>/`, `/evidence/artifact/<E-handle>/` | UUID; handle = readable key | 301 from every earlier handle; `/task/<uuid>/` → 301 |
| Source | `/sources/<source_id>/` (post-ACT-06 neutral ids) | source id | 301 from renamed ids |
| Claim | `/evidence/claim/<claim_id>/` (latest view); `/r/<pub>/…#claim-<id>` (citable) | claim id | `/evidence/<id>/` → 301 |
| Release views | `/s/<pub>/<path>` (citable), `/` (latest view) | publication id | never changes; withdrawal → 410 tombstone |

**One redirect generator** (JUR-05) reads `jurisdiction_slug_history.json`, `sig.slug-history/1`, every `handles_history`, the
source-id rename list and a fixed legacy list (`/data-freshness/**`, `/network/`, `/evidence/<id>/`, `/task/new/**` → 410) and
emits one `redirects.conf` beside `withdrawn.conf`, `selectors.conf` and `labels.conf` (G3 REL-03b), plus static stubs (UXR-08).

**`sig.workspace-state/2` parameter registry** (UXR-09; K0 §4.5 superset; defaults omitted):

```
common  v=2  release=p-<sha>  view=list|map|graph|table|search
        q=  type=<result type: place|organization|technology|source|document|page|record>
        kind=<entity type>  jurisdiction=<jkey> (filter, incl. descendants)  frame=<jkey> | bbox=w,s,e,n (framing → at)
        technology=  vendor=<entity key>  operator=<entity key>  source=<id>  collection=<compartment>
        location=public-point|no-public-point  status=corroborated|single-source|contested|candidate
        seen=YYYY[-MM]..YYYY[-MM]  (when SIG observed)   dated=YYYY[-MM]..YYYY[-MM] (world date of the fact)
        currency=current|aging|stale|historical|undated   focus=<record or entity key>
        page=  sort=  dir=asc|desc  cursor=<group:cursor>  within=<scope>
map     at=<z>/<lat>/<lon> (rounded to the zoom and never finer than the published tier)  layers=  basemap=0|1
graph   overview=<id>  hops=1|2  edge=<access kind or relation>…  expand=<key>… (≤ 10)  path=<key>~<key>
```

"Cite this view" produces `/s/<pub>/<surface>/?v=2&…` plus the static equivalent; parameterised T2 URLs carry
`noindex,follow` and a canonical; the sitemap lists canonical T0/T1 routes only (UXK0-5).

### 2.6 Landing and onboarding flow (K14 §2.3, §6)

1. **Arrive at `/`** (T1, 0 KiB JS until K3's shards exist, then ≤ 20 KiB): tagline (H1) and the one-sentence statement
   (D-K14-1 with D3 Q5), a place search ("State, county, city, agency or vendor"), three example chips generated from the
   release and emitted only when they resolve (DR-K14-04), and the release stamp.
2. **Start here** — three persona cards (advocate: *"I have a council meeting coming up"*; journalist: *"I'm checking a figure or
   a claim"*; organizer: *"I'm organizing in my area"*) plus "I want the data". Each step links a golden place (D3 §4) or,
   until one exists, the place search.
3. **The record today** — ≤ 6 `<Figure>`s with definitions, "not a census", Provisional where due, and a "Sources ›" link;
   the 126 tiles live on `/coverage-metrics/` (UXW0-1).
4. **What makes SIG different**, **See an example** (only once a joined golden dossier exists), **How to read SIG** (4-item
   key from the lexicon), **Trust and method** (the only full review-status disclosure; links `/quality/`).
5. **Every page thereafter** carries a "How to read this page" key listing only the symbols present, first-use glossary
   popovers, and typed empty states that say what exists nearby and what would close the gap. No overlay tours, no cookies.

---

## 3. Component inventory and shared modules (one owner each)

| component / module | behaviour & data owner | visual owner | consumers |
|---|---|---|---|
| Page-type registry, route discovery, script-policy and no-JS parity specs | UXK0-1 | — | every route |
| Budgets (`sig.page-budgets/1`), generated LHCI, synthetic national fixture | UXK0-2 | — | all tickets |
| CSP / HSTS / Permissions-Policy / figure-SVG policy | UXK0-3 | — | all |
| `<sig-table>`, `<sig-typeahead>` (shell), `<sig-cite>`, `<sig-activate>` | UXK0-4 | UXK14-3a | UX9-3, DSRC-02, MAP-03b, SRCH-05, VIZ-04, ENH-01 |
| `sig.workspace-state/2` library, cite-this-view, facet conformance harness, sitemap/canonical | UXK0-5 | — | MAP-03a, GX-09a, SRCH-05, VIZ-03 |
| Design tokens (light/dark, type, spacing, motion) | UXK14-1 | UXK14-1 | all templates, map style, figure kit |
| **Legend lexicon** `lexicon.json` + `epistemic.ts`, glossary, `<Term>` popovers | UXK14-4 | UXK14-4 | every template, FIG-01, MAP-03a, UXK14-5 lints |
| Header (6 sections + search), footer strip, page-header band, breadcrumbs, stamp render | UXK14-2 (stamp data G3 REL-02; cite TX-13a) | UXK14-2 | all |
| Figure visual, stat row, cards, table visual, chips and badges | TX-09 (data contract) | UXK14-3a | all T1 |
| Contested marker, range, absence chip, callouts, banner, `EmptySurface`, error pages | UXK14-3b | UXK14-3b | all |
| **`<ProvenancePanel>`** | TX-08a | UXK14-3b | T0 records, EV-03, GX-06a/09a, MAP-03a, QB-01 |
| **Labels, slugs, hashes, handles** (`policy` module) | GX-01 (+ GX-03 keys, RQ-01/WX-01/EV-02 templates) | — | exporter, API, shards, tiles, all pages |
| **Static figure kit** (geo; graphs/charts/legends) | FIG-01a, FIG-01b | FIG-01 (classes from tokens/lexicon) | MAP-05, VIZ-01a/b, GX-06b, GX-08a, DSRC-02, UX10-3a, JUR-04 locators |
| Dossier map + locator composition, entity-page map snippet | VIZ-01a | VIZ-02 | dossiers, GX-06b |
| Dossier network figure (bipartite) | VIZ-01b | VIZ-02 | dossiers |
| **Dossier template** | VIZ-02 | VIZ-02 | JUR-03/04, DSRC-02, WX-04a, RQ-03b sections |
| Explore bar (map · graph · search within) | VIZ-03 | UXK14-3a | dossiers, entity pages |
| Map app chrome (controls, legend, In-view list, selection panel); embedded mode | MAP-03a/b; VIZ-04 | UXK14-3a | `/map/`, dossiers |
| Graph explorer chrome (node/edge panels, list twin, path finder) | GX-09a/b | UXK14-3a | `/explore/` |
| Search index, engine, API, results HTML, shards, typeahead data | SRCH-01…05 | UXK14-3a | header, home, `/search/`, map, index, explorer |
| Scoped search forms | SRCH-06 (placed by VIZ-03) | — | dossiers, source pages |
| Sources row component (release and status clocks) | UX9-3 | UXK14-3a | `/sources/**`, `/status/sources/` |
| **Redirect generator** | JUR-05 | — | nginx (G3 REL-03b) |
| Print: council brief, running footer, terms list, QR | UXK14-9 | UXK14-9 | dossiers, entity pages |
| Watch feeds (ics/rss/json/opml) | WX-04b | — | subscribers |
| Change page and feeds | CHG-01 (diffs TX-14) | UXK14-3a | `/changes/` |
| Disagreements list | CX-01 | UXK14-3b | `/disagreements/**`, dossier and entity sections |
| Quality basis block, count intervals, "possible duplicate" | QB-01 (fields: L3 CONF-07b/12) | UXK14-3b | panels, entity/record pages, K5 view |
| Capability table, example-question generator | UXK14-6 | UXK14-6 | home, About |
| Copy lints; visual regression and operator gallery | UXK14-5; UXK14-10 | — | CI |

---

## 4. Data contracts per page type, and the data-layer prerequisites

### 4.1 Files per release, API endpoints and sizes

All release files are bound into descriptor v2 (G3 REL-01), per compartment where they carry licensed facts (ADR-106).
Sizes are the rows' measurements or inferences.

| page type / surface | release files (schema) | size (row) | API (release-pinned) | producer |
|---|---|---|---|---|
| Dossier index | `dossier/index.json` (`sig.dossier-index/2`); jurisdiction registry + boundary pack | ≈ 90 KB HTML for ≈ 150 rows (K4) | `/v1/releases/{pub}/dossiers/{key}` (REL-05) | JUR-01, JUR-04 |
| Dossier (4 levels, ≈ 5.6k pages) | `dossiers/<slug-path>.json`; `dossier_sources/<slug-path>.json` (`sig.dossier-sources/1`) + runs file; figures metadata; `sig.dossier-visuals/1` (**restricted build input, never published**) | sources ≤ 150 KB (US), ≈ 11 MB total; visuals input 50–80 MB; inline map ≤ 25.6 KB gz (GA) (K5, K6) | `…/dossiers/{key}/sources`; optional `…/statements?jurisdiction=` (D-K5-1) | JUR-03, DSRC-01, VIZ-01a/b |
| Dossier sites lists | sites files + placement columns | ≈ 2.3k–5k HTML files (K1) | `/v1/releases/{pub}/compartments/{c}/sites?bbox=`; `…/sites?bbox=&format=html` | MAP-05, MAP-06 |
| Map | `tiles/<comp>-sites.<sha8>.pmtiles` (`sig.map-tiles/2`), `tiles/index.json`, `map/dict.json` (`sig.map-dict/1`), `map/coverage_by_jurisdiction.json`, `tiles/context.pmtiles`, basemap PMTiles (own archive), `map/overview.svg` | overlays 42.5 MB today; basemap ≈ 120 GB planet z0–15 on R2; first view ≈ 0.6–0.9 MiB (K1) | bbox API (above) | MAP-01a/b, MAP-02, MAP-05 |
| Entity pages (E1 ≈ 2.7k, E2 ≈ 3.5k, E3 ≈ 4–6.7k) | `labels/<comp>.jsonl` (`sig.entity-label/1`); `/entity/…/index.json` (`sig.entity-page/1`); `sig.slug-history/1` | labels ≈ 10 MB gz; twin 0.4–30 KB gz; ≈ 26k objects per release (K2) | `/v1/entity` returns the shared label + capped relationships (parity) | GX-01, GX-03, GX-05a/b |
| Graphs / explorer | `graph/<overview>/<comp>.json` (`sig.graph-overview/1`) + `overview.svg`; `sig.graph-components/1` | ≤ 132.5 KB gz at 3k nodes/10k edges (K2) | none | GX-08a/b |
| Search | `r/<pub>/c/<comp>/search_index.sqlite`, `claim_ref.sqlite`, `releases/<pub>/search/catalog.sqlite`, `search/shards/<xx>.json` (`sig.release-search-index/2`) | ≈ 99 MB indexes; shards 815 KB gz, p95 3.4 KB (K3) | `GET /v1/releases/{pub|latest}/search?…&format=html|json` (`sig.search-results/2`) | SRCH-01…03, SRCH-05 |
| Sources table and pages (342) | `sources.json/csv` + Table Schema (`sig.source-row/1`); `sources/<id>/index.json` (`sig.source-page/2`); `executions.jsonl`; `versions.json`; `runs.jsonl`, `captures.jsonl`, `issues.jsonl`; per-source `by-source/<id>/{sites,statements}` | table ≈ 50–90 KiB gz; ≈ 1.5k source pages ×2 renderings, 40–60 MB (K9, K10) | `/v1/releases/{pub}/sources/{id}` (TX-15) | UX9-1/3/4, UX10-1…3, TX-02/03/04/06 |
| Evidence | `evidence.json` (+ `capture_classification`, `source_name`); artifact index (`sig.evidence-artifact/1`); claim views (cap 20k) | 255 artifacts today (K8) | `/v1/claim`, `/v1/evidence` (fixed by TX-08b) | UXW0-2, EV-02/03, TX-08a/b |
| Record provenance | per-compartment `statements` (`sig.statement/1`); record pages `/r/<pub>/…` | release tree 2.0 GB, 475k files (K0) | — | TX-08a |
| Watch | `watch.json` (`sig/watch/2`, `sig.watch-item/1`); per-place JSON; feeds | — | — | WX-01, WX-04a/b |
| Research queue | task shards JSONL.gz ≤ 25 MB each (`sig.task-page/1`), `handles_history` | ≈ 727 task pages + facets (K11) | `/v1/task/{id}` (machine route) | RQ-01…03 |
| Disagreements | contradiction index (from TX-08a statements + placement disagreements) | small | — | CX-01 |
| Changes | `changes/` (added/removed/changed parquet, `CHANGELOG.md`), feeds | per release | `/v1/changes` | TX-14, CHG-01 |
| Status lane (not a release) | `status/state.json`, `status/sources/<id>.json`, `status/issues/`, `status/archive/<date>.json` | 2–5 MB per run (J3) | — | TX-07 |
| Quality | `quality.json` (`sig.quality-report/1`) | — | — | L3 CONF-01/12 |
| Shared | `lexicon.json`, `page-budgets.json`, `release.json` | small | `/health` release fields (REL-02) | UXK14-4, UXK0-2, REL-02 |

**Live-spine `/v1/*`** stays a developer surface labelled "live, not a citation"; no public page reads it (UXR-26).

**Cost roll-up (monthly, inference from the rows' cited unit prices; U-008).**

| item | 10k sessions/month | 100k sessions/month | row |
|---|---|---|---|
| Map assets, tiles, basemap | ≈ $3 (R2) / ≈ $6 (GCS) | ≈ $13 (R2) / ≈ $43 (GCS) | K1 §2.4 |
| Graph explorer + entity pages | ≤ $2 | ≤ $10 | K2 §6.6 |
| Search (1 GiB `sig-api`, queries) | ≈ $3–5 | ≈ $5–7; abuse worst case ≈ $140, bounded by rate limit + $50 alert | K3 §5.7 |
| Dossier figures | < $1 | < $1 | K6 §9.3 |
| Sources downloads/versions (R2) | ≈ $0 | ≈ $0–1 | K9 §7.4 |
| Status lane, staging services | ≈ $0 | ≈ $0 | J3 §7.1, G3 D-G3-10 |
| **UX increment** | **≈ $10–20** | **≈ $30–60 (R2) · ≈ $60–90 (GCS)** | — |

Added to today's ≈ $90–100/month (D3 §4, G1, unverified), the total stays inside $300 at both volumes. No K13 design needs more
than $300; UXR-31 makes the live acceptance tickets measure it.

### 4.2 Data-layer prerequisites each UX feature depends on

"Owner" is the ticket that removes the defect; "interim" is what the surface shows until then (honesty rules, never a
silent gap).

| UX feature | depends on (finding) | owner | interim behaviour | journeys at risk |
|---|---|---|---|---|
| Human-readable labels everywhere (GX-01) | entity typing: every subject typed `deployment` (L1 NEW-5, L2 NEW-8) | F5 **PKG-11** (L3 CP-3) | kind parsed from the connector key | J2, A1 |
| Organisation names, pages, network hub, organisation search | all 969 organisations review-flagged (K2 NEW-1) | **D-K2-1** + G2 **ACT-10** allow tool (50 reviews unlock 96.5 % of edges) | "pending publication review" (UXR-30) | J2, O1 |
| Dated edges and currency (GX-02, GX-07, overviews) | 1970 placeholders, no supersession, two classifiers (L1 NEW-10); 98.8 % of edges undated (L2 NEW-10) | L3 **CONF-06** (backend) + GX-02 (export) | "undated"; "recorded 2020-01-28; the data may be older" | J2, O2 |
| Dossier counts by place (JUR-02b/03) | scheme dropped at the sink (K4 NEW-1); 4.6 % of points > 2 km outside their dossier (L2 NEW-12) | JUR-02a/b + F5 **PKG-06b** (L3 CP-5) | display names on legacy buckets (UXW0-5); no maps before JUR-02b (K6) | A1, O1 |
| "Corroborated / single source", "N camera sites" | no dedup reaches published rows (L1 NEW-8); independence never declared (L1 NEW-4); 13.5 % cross-layer duplicates (L2 NEW-3) | L3 **CONF-03a/b, CONF-04, CONF-07a/b** | "records"; "republications not yet collapsed"; per-dossier single-source share | A2, O1, J1 |
| Technology filter and typed dossiers | 77.4 % of `traffic_camera` mistyped (L2 NEW-6) | F5 **PKG-07** (L3 CP-6) | "not typed yet", never "traffic camera" | A2, O1 |
| "Who runs it" / operator filter | publisher recorded as operator for 74 % (L2 NEW-4; K2 NEW-2) | L3 **CONF-06** | operator shown only when not a publisher string; "Operator not stated" | A2, O1 |
| Dossier network figures, O4/O7 overviews | no agency placed (K6 §1); no organisation ER (L1 NEW-12) | **I8** placement via `lookup@1`; L3 **CONF-13** | typed empty state "no organisations placed here yet" | A2, O1, J2 |
| Access graph at Flock scale (O2) | 474,184 share-list edges not yet claims (I3) | **I8** + D-K2-4 | Data Driven edges only, marked historical | J2 |
| Procurement in supply graphs | no relevance filter (L2 NEW-11; K2 NEW-7) | GX-04 (+ I8 for new sources) | unclassified notices as buyer-page rows only | J2 |
| Watch items | no producer (K7 NEW-1); predicates missing (NEW-2); monthly agenda cadence (NEW-3) | WX-01/02/03; I-stream tenant fixes | cause-class empty state (UXW0-2) | O2, A2 |
| Evidence with real documents | 0 of 2.78 M bindings reach bytes (L2 NEW-5); public tier on actual captures (J3 NEW-2) | G2 **steps 1–2** (ACT-11, ACT-14) + TX-01 (L3 CP-8) | artifacts labelled "run record" (UXW0-2, EV-02) | J1, J3, A4 |
| Disagreements browser | resolver labels every multi-value "uncontested" (L2 NEW-2); 5,278 collided subjects (L2 NEW-1) | L3 **CONF-05**, **CONF-03b** | the 2 recorded contradictions + "coordinate conflicts within one source (identity defects)" as a separate kind | J3 |
| Freshness verdicts, "last upstream change" | SIG insert time ≠ upstream change (L2 NEW-10); inserted > considered for 24 sources (L2 NEW-17) | UX9-2 + F5 PKG-10/12 + CONF-06 | "not evaluable (n)"; no "0 stale" | J1, J5 |
| Change feeds (CHG-01, TX-14) | identical facts re-mint as new claims (L1 NEW-1) | L3 **CONF-03a** | diff noise disclosed as "SIG records changed" | J5 |
| Search for agencies and vendors | no organisation records in the release (K3 NEW-7) | GX-05a (+ D-K2-1) | honest "SIG's release names no record for …" | J2 |
| Attribution lines (map strip, downloads, search groups) | wrong per-row attribution; 630 sharing rows credited to SIG (J1 NEW-2, L2 NEW-14) | G2 **ACT-07** / F5 PKG-08 | interim sources-and-licences page (ACT-06) | J1, O3 |
| Source contribution per dossier | jurisdiction assigned per source, not per point (K10 NEW-8) | JUR-02b | `basis` column shows "declared by source" | A2, J1 |
| Provisional / confidence labels | model-labelled gold set, no negatives (L1 NEW-9, L2 NEW-15) | L3 **CONF-02** (W0), CONF-09/12 | Provisional chip on resolved-site figures | J1 |

---

## 5. Traceability

### 5.1 Operator asks → designs → requirements → tickets → capstone journeys

"Live check" is the U-003 acceptance CAP-01 runs on the promoted release (UXR-27).

| ask | design rows | requirements (k13 + adopted families) | tickets | live check (CAP-01) | journeys |
|---|---|---|---|---|---|
| **U-003.1** map with a real basemap and place context | K1, K0, K6, K14 | UXR-11, 13–15, 18, 23–24; A02 (SIG-UI-DM01–09, SIG-GEO-DM10) | UXW0-6, MAP-01a, MAP-02, MAP-05, MAP-03a/b, MAP-04, MAP-06, MAP-01b, MAP-07, FIG-01a, VIZ-04 | `/map/` draws a self-hosted basemap, every published located record at every zoom (tile verifier = 0 missing), "Oklahoma City" frames the city, a record opens a panel with linked place, source and evidence; no-JS `/map/` ≤ 100 KiB | A1, O1, O3 |
| **U-003.2** readable labels, entity pages, global graph(s), searchable/navigable | K2, K0, K3, L3 | UXR-03, 09, 11, 17, 20, 30, 38; A03 (SIG-UI-D20–D34, SIG-EXPORT-D20/21) | UXW0-6, GX-01…09b, VIZ-01b, ACC-EXPLORE, QB-01 | 0 UUID labels (crawl); Vigilant Solutions (LEARN) and Austin Police Department named with pages; every edge dated or "undated"; `/explore/` overviews O0–O5 navigable; ≤ 2 actions to evidence | J2, J3, O1 |
| **U-003.3** flexible search across the graph | K3, K0, K1, K4 | UXR-23, 24; A04 (SIG-SRCH-D01–D14) | SRCH-01…08, MAP-04, JUR-04 | benchmark dev ≥ 90 % / held-out ≥ 80 % top-3, 0 misleading top hits; "Canberra", "Texas", "ICE", "Vigilant" behave as specified; works with JS off | A1, J2 |
| **U-003.4** dossier list grouped by country | K4 | UXR-07, 08; A05 (SIG-JUR-D01–D12) | UXW0-5, JUR-01…05, ACC-PLACES | `/dossier/` = United States → states, then other countries → subdivisions, then "Not yet placed"; `/dossier/md/` → Maryland; `/dossier/id/` split page | A1, O1 |
| **U-003.5** which sources contributed what, when | K5, J3, K10 | UXR-04, 19, 34; A06 (SIG-DSRC-D01–D09); A10 | DSRC-01…03, TX-08a, TX-09, QB-01, UX10-3b | California: "from 11 sources" → breakdown summing to the figure → source page → last run, with first/last seen | J1, A2 |
| **U-003.6** default map/network visualizations and search on dossiers | K6, K1, K2, K3 | UXR-10, 16, 19; A07 (SIG-UI-DV01–DV12) | FIG-01a/b, VIZ-01a, VIZ-02, VIZ-03, VIZ-01b, VIZ-04, SRCH-06 | every dossier with located records shows Figure 1, prints it, activates the map on click; network figures or typed empty state; scoped search returns only the place's chain | A2, A3, O1 |
| **U-003.7** `/watch` QA | K7 | UXR-36; A08 (SIG-WATCH-D01–D10) | UXW0-2, WX-01…06, WX-04a/b | producer fills `watch.json`; Seattle/Texas place pages and feeds validate (RFC 5545, RSS, JSON Feed); empty states name the cause | O2, A2 |
| **U-003.8** `/evidence` shows nothing | K8, J3 | UXR-33, 36; A09 (SIG-EVUI-D01–D10) | UXW0-2, TX-08a/b, EV-02, EV-03, TX-12 | `/evidence/` lists every publishable artifact with honest binding states; claim viewer lane-aware after G2 steps 1–2 | J1, J3, A4 |
| **U-003.9** sources table: sortable, downloads, versions, metrics, ground truth | K9, J3, J4 | UXR-06, 37; A10 (SIG-TRANSP-D26–D34) | UX9-1…4, TX-02/03/04, TX-10a/b, TX-11, ENH-01 | `/sources/` 342 rows, every column sortable asc/desc without JS, latest extract + version index per published source, homepage and terms links | O3, J1 |
| **U-003.10** per-source detail pages | K10, J3 | UXR-06; A10 (SIG-TRANSP-D35–D43) | UX10-1…4, TX-06, TX-07, TX-12, TX-15 | every source page shows metadata, rights record, conduct, execution-keyed history, captures with hashes, per-file downloads where the lane allows, dossier contribution, changelog | J1, J5 |
| **U-003.11** research queue usable | K11 | UXR-03, 17, 29; A11 (SIG-RQ-D01–D10) | UXW0-3, RQ-01…05, WX-06 | `/task/01a0a720-9b9a-…/` → 301 → `T-usa-ga-acworth-share-pd-…` titled with Acworth Police Department; ≤ 50 cards/page; drafts for records requests | O4, A4 |
| **U-003.G** friendlier, richer, traversable, inspectable | K12a, K12b, K13, K14, L3 | UXR-01–06, 21, 22, 27–29, 35; A12, A13 | UXW0-1/4, UXK0-*, UXK14-*, CX-01, CHG-01, ENH-01, CAP-01/02 | nav ≤ 6 sections; every figure ≤ 2 actions to evidence; sideways links everywhere; disagreements and changes pages live | all 13 |
| **U-004** keep the precise language, definitions, standards | K14 §2.5 | A12 (DR-K14-07/08); UXR-32 | UXK14-4, UXK14-6 | precise sections retained byte-for-byte behind "In brief" (diff guard); glossary published | A2, J3 |
| **U-005** journalists explore with full lineage; less confusing and verbose | K0, K2, K3, J3, K14 | UXR-04, 09, 22, 25, 26, 33, 34, 38; A12 (DR-K14-10/11) | TX-08a/b, TX-09, GX-09a/b, SRCH-05, TX-13a/b, CHG-01, UXK14-4/5 | J1–J5 pass; chrome ≤ 40 visible words; no repeated caveat | J1–J5 |
| **U-007** feature richness; correctness and comprehensiveness; clarity of what SIG is | D3 §3, K14, L3, I-stream | UXR-13, 14, 27, 28, 31; A13 | W1 data-layer tickets + L3 CONF-* + CAP-01/02 | D3 §3(a)–(c) success criteria measured in CAP-01 and L3 CONF-14 | all 13 |

**Coverage check.** Every ask above has ≥ 1 requirement, ≥ 1 ticket and ≥ 1 journey (the CSVs' `operator_asks` columns list all
of U-002, U-003.1…11, U-003.G, U-004…U-008). U-003.X (the agent's own ideas) is answered by §5.2.

### 5.2 K12b ideas (32) — accept, defer or reject

| idea | disposition | reason | ticket(s) |
|---|---|---|---|
| I-01 entity pages | **accept** | backbone of graph UX (K12a); institutions only | GX-05a/b, GX-06a/b |
| I-02 explain this number | **accept** | defining standard | TX-09, DSRC-01, UXK14-3a |
| I-03 find my place | **accept, modified** | shards + registry + city layer; no address geocoding (Part VIII, K1 §4.2); ZIP later (JUR-07) | SRCH-01/05, MAP-04, JUR-01 |
| I-04 who can access what | **accept** | closures with per-hop evidence; Flock scale after I8/D-K2-4 | GX-07, GX-08b |
| I-05 date and currency on every relationship | **accept** | K2 H-2/H-3, UXR-38 | GX-02, GX-05a |
| I-06 one-page council brief | **accept** | design centre (A3) | UXK14-9, VIZ-02 |
| I-07 decision calendar + subscriptions | **accept, modified** | iCal/RSS/JSON Feed/OPML; **email rejected** (no subscriber addresses; RSS-to-email how-to instead) | WX-01…06 |
| I-08 what changed | **accept** | D3 J5 | TX-14, CHG-01, UX10-4 |
| I-09 source pages for every source | **accept** | all 342 registry rows | UX10-3a/b |
| I-10 dossier contribution ledger | **accept** | U-003.5 | DSRC-01/02 |
| I-11 contradiction browser | **accept** | K12b NEW-17; typed kinds kept apart | CX-01 |
| I-12 "what we don't know" per place | **accept** | dossier section with task links | VIZ-02, RQ-03b |
| I-13 tasks as questions + request templates | **accept** | U-003.11; drafts never sent | RQ-01, RQ-03b, RQ-04 |
| I-14 start-here journeys | **accept** | K14 §6.1 | UXK14-6 |
| I-15 cross-jurisdiction comparison | **defer** | coverage reads as density (SIG-UI-018) until JUR-02b placement and L3 CONF-07b intervals exist; revisit trigger: CAP-01 passes | — |
| I-16 map feature pages, cite a point | **accept, modified** | no `/site/<id>/` route; T0 record after ACT-24, sites-list row before (UXR-18); cite via `focus=` snapshot | MAP-03a, MAP-05 |
| I-17 map filters, legend, toggles, clustering | **accept** | K1 §3–§4 | MAP-01a/b, MAP-03a/b |
| I-18 typed graph atlases | **accept** | overviews O1 supply, O3 funding, O5 governance | GX-08a/b |
| I-19 keyboard-first graph navigation | **accept** | WCAG 2.2 AA (K0 §4.9) | GX-09b |
| I-20 embeddable figure cards | **defer** | hotlink egress and context loss; SVG downloads for country/admin-1 cover part; revisit after TX-11 and the announcement | — |
| I-21 citation formats incl. legal | **accept** | `<sig-cite>` formats; pinned URLs | UXK0-4, TX-13a/b |
| I-22 data-quality badges | **accept** | lexicon chips incl. "Not reviewed" and L3's basis block | UXK14-3a, QB-01 |
| I-23 download this view | **accept** | `<sig-table>` client CSV of visible rows; server export for search | UXK0-4, SRCH-08 |
| I-24 peer link-outs with agreement markers | **accept link-outs; defer agreement markers** | neutral "Other public resources" (D3 Q4) now; agreement needs cross-peer identity and declared lineage (CONF-04) | VIZ-02, UXK14-6 |
| I-25 typed KG search | **accept; reject "expose `/v1/search` first"** | K0 I-10; live spine unranked (K3 NEW-6) | SRCH-01…05 |
| I-26 evidence locker | **accept** | U-003.8 | UXW0-2, EV-02, EV-03 |
| I-27 "ask this graph" question pages | **accept examples; defer pages** | generated, tested example questions only (DR-K14-04); per-place answer pages imply completeness | UXK14-6 |
| I-28 entity and place timelines | **accept** | world vs belief time kept apart; sparse dates disclosed | GX-06b, VIZ-02 |
| I-29 Flock portal policy view | **defer as a view; accept as entity claims** | portal claims render on portal entity pages; a dedicated view waits for mirror rights (I1/I3) and aggregate-only screens | GX-05a |
| I-30 coverage-honesty place card | **accept** | index row fields + coverage layer + dossier-scope HWKT | JUR-03/04, MAP-01b, DSRC-02 |
| I-31 funding trail | **accept** | O3 overview + entity relationships, relevance shown | GX-08a, GX-04 |
| I-32 near-me list | **accept, modified** | "my location" stays in the browser (D-K1-7); static per-place lists; no server geolocation | MAP-04, MAP-05 |

Totals by primary disposition: **29 accept** — 22 as proposed (I-01, 02, 04, 05, 06, 08, 09, 10, 11, 12, 13, 14, 17, 18,
19, 21, 22, 23, 26, 28, 30, 31) and 7 modified (I-03, 07, 16, 24, 25, 27, 32) — and **3 defer** (I-15, I-20, I-29). Inside
accepted ideas, **3 sub-proposals are rejected** (I-07 email alerts, I-16's `/site/` route, I-25's `/v1/search` shortcut) and
**2 are deferred** (I-24 agreement markers, I-27 per-place question pages).

### 5.3 Findings routed to K13

| finding | disposition |
|---|---|
| K0 NEW-4 (hand-listed route sweeps) | UXK0-1 (route discovery) — owned |
| K6 NEW-2 (symbol collisions) | C-01, UXR-11, UXK14-4 |
| K6 NEW-3 (circular SVG ownership) | C-07, FIG-01a/b |
| K12b NEW-14 (124 tiles without paths) | UXW0-1 (copy), TX-09 (tiles as `<Figure>`s) |
| K12b NEW-17 (contradictions "kept visible" but invisible) | UXW0-1 (copy), CX-01 |
| K12b NEW-19 (no "what changed") | TX-14, CHG-01 |
| K12b NEW-21 (zero outbound links) | UXR-06; UX10-3a, EV-02, VIZ-02, UXK14-6 |
| K14 NEW-1 (chrome 36 % of words) | UXK14-4, UXK14-5; SIG-UI-044 amendment (D-K14-6) |
| K14 NEW-9 (15-link header) | C-31, UXR-01, UXK14-2 |

---

## 6. Requirements (full text in `data/k13_requirements.csv`)

51 rows: **38 K13 requirements** (UXR-01…UXR-38; 36 MUST, 2 SHOULD) and **13 adoption rows** (UXR-A01…A13) that adopt each
row's own draft family with the K13 amendments, so T1 numbers one coherent set rather than re-reading fifteen documents.

| group | ids |
|---|---|
| Navigation and registry | UXR-01, 02, 35 |
| Linking and ground truth | UXR-03, 04, 05, 06, 29 |
| URLs, state and redirects | UXR-07, 08, 09, 10, 18, 25 |
| Lexicon and vocabulary | UXR-11, 12, 13, 14, 15, 36, 38 |
| Shared modules | UXR-16, 17, 19, 23, 24, 33, 34 |
| New surfaces | UXR-20, 21, 22 |
| Data discipline | UXR-26, 30, 32, 37 |
| Acceptance and cost | UXR-27, 28, 31 |
| Adopted families | A01 K0 SIG-UI-D01–D10 · A02 K1 DM · A03 K2 D20–D34 · A04 K3 SRCH · A05 K4 JUR · A06 K5 DSRC · A07 K6 DV · A08 K7 WATCH · A09 K8 EVUI · A10 J3/K9/K10 TRANSP · A11 K11 RQ · A12 K14 DR-K14 · A13 L3 CONF-D01/D05/D11 |

---

## 7. The unified Round-11 UX ticket list (full list in `data/k13_tickets.csv`)

### 7.1 Waves

- **W0 — honesty quick wins (4.5 runs).** Ride G2 step 0's republish #1 (ACT-06, copy only, release `sig-2026-09-27`
  unchanged) and #2 (ACT-07, the attribution re-export). UXW0-1 (home, dossier, coverage copy), UXW0-2 (watch and evidence
  truth = WX-07 + EV-01), UXW0-3 (queue truth = RQ-00), UXW0-4 (chrome, 404s, sitemap, digit grouping, joined words), UXW0-5
  (display names), UXW0-6 (island honesty, facet notices, dead gap links). Every sentence is operator-confirmed verbatim (G2 §6).
  C6's QW-2/3/4/5 and QW-15 stay inside G2 ACT-06/ACT-08.
- **W1 — foundations and data-layer prerequisites (36 runs).** CI and architecture (UXK0-1…5), design system (UXK14-1/2/3a/3b/4/5),
  the figure kit (FIG-01a/b), the identifier module and graph export (GX-01…04), placement (JUR-01/02a/02b), tiles and basemap
  (MAP-01a/02), transparency exports (TX-01/02/03/04/08a/09/11/13a, UX9-1/2, UX10-1/2), contribution, watch and task exports
  (DSRC-01, WX-01, RQ-01) and the search index (SRCH-01/02). Visible at the next Class S republish: all dots on the map
  (MAP-01a), a labelled and dated `/network/` (GX-02), the new chrome and tokens, citations with release ids.
- **W2 — core surfaces (37 runs).** Every operator ask gets a working page: dossiers at four levels and the grouped index (JUR-03/04/05),
  the map app and its no-JS baseline (MAP-05/03a/03b/04/06), search v2 (SRCH-03…07), entity pages and access (GX-05a/06a/07),
  dossier sources, downloads and the new template (DSRC-02/03, VIZ-01a/02/03), watch pages (WX-04a/05), evidence (TX-08b, EV-02),
  the queue (RQ-02/03a/03b/04), sources and source pages (UX9-3/4, UX10-3a/b, TX-06/07/10a/10b), home/About/brand/print/
  onboarding (UXK14-6/7/9/10/11), and ACC-PLACES.
- **W3 — explore surfaces and activation (22 runs).** Tile properties v2 and map acceptance (MAP-01b/07), entity pages B,
  overviews and the explorer (GX-05b/06b/08a/08b/09a/09b), dossier networks and in-place map (VIZ-01b/04), watch predicates,
  lane and feeds (WX-02/03/04b/06), real evidence and the raw archive (EV-03, TX-12), disagreements (CX-01), quality basis
  (QB-01), snapshots, changes and parity (TX-13b/14/15, CHG-01, UX10-4), result export (SRCH-08), ACC-EXPLORE and TX-16 (HG-11).
- **W4 — polish and announce readiness (3 runs).** ENH-01 (T1 enhancements), RQ-05 (contribution path), CAP-01 (capstone),
  CAP-02 (announce-readiness review and the operator's "beautiful" gallery).

### 7.2 What was merged, superseded or moved (P9)

| per-row unit(s) | now |
|---|---|
| K7 WX-07 + K8 EV-01 | UXW0-2 |
| K11 RQ-00 | UXW0-3 |
| K0 UXK0-6 (Preact) | folded into MAP-03a, SRCH-05, GX-09a |
| K0 UXK0-7, K1 MAP-00, K6 VIZ-00 spec hand-off | Stage-B **T1** (ADRs, `spec_src`); AGENTS.md rewrites in UXK0-1 |
| K6 VIZ-00 contracts/lexicon, K1 MAP-05 renderer core, K14 UXK14-8 | FIG-01a/b, UXK14-4 (MAP-05 keeps the no-JS map page) |
| J3 TX-05a / TX-05b | UX9-3 / UX10-3a+b |
| K5 DSRC-04 | export → L3 CONF-07b; rendering → QB-01 |
| K5 DSRC-05, K9 UX9-3e (+ K4/K7/K8/K11 enhanced filters) | ENH-01 |
| K4 JUR-06 + K5 DSRC-06 (+ K9/K10 ATs, K7/K8/K11 journeys) | ACC-PLACES |
| K2 GX-10 + K6 VIZ-05 | ACC-EXPLORE |
| K14 UXK14-12 | CAP-02 |
| K11 RQ-06 | K7 WX-06 (already merged by K11) |
| K3 SRCH-09, K4 JUR-07 | **deferred** beyond Round 11 (claim-text/entity-scoped search; ZIP lookup) |

New K13 tickets: UXW0-1, 4, 5, 6; FIG-01a/b; CX-01; QB-01; CHG-01; ACC-PLACES; ACC-EXPLORE; ENH-01; CAP-01; CAP-02 (plus the
re-cut UXW0-2/3).

### 7.3 External prerequisites the list depends on (not counted)

G2 ACT-03/05/06/07/10/11/13/14/15/16/17/23/24 · G3 REL-01/02/03b/05/09 and cut → promote · F5 PKG-01/03a/04/06b/07/08/09a/09b/
10/11/12 · L3 CONF-02/03a/03b/04/05/06/07a/07b/12/13/14 · I8 (agency placement, Flock share lists, new-source classification) ·
the operator decisions in §10.

### 7.4 Ordering constraints worth stating

- **JUR-02b/03 before G2 ACT-24**, or the immutable release tree freezes the bare-code collisions (K4 NEW-6).
- **UXK0-1/2 before any new T2 code** (budgets and discovery fail closed); **UXK14-1/3/4 before page tickets**, which consume and
  never restyle (K14 R-5).
- **ACT-07 (attribution) before UX9-3, UX10-3, TX-10b and any download link**; TX-11 + ACT-03 before any bulk link (C6 PG-6).
- **D-K2-1 before GX-05a publishes organisations**; GX-02 can ship non-organisation labels earlier.
- **TX-13b rides ACT-24 (HG-11)**; J4 ("cite durably") cannot pass before it.
- Each republish that adds a route family is **Class S** (G3 §5.4): about six signed readouts over the round (W0 ×2, W1, W2, W3,
  W4) — an operator-load estimate (inference).

---

## 8. Capstone acceptance journeys (D3's 13; CAP-01)

Walked cold from `/` at 390 px and 1440 px on the promoted release, by a fresh-context agent (recorded `agent-verified`) and by the
operator (D3 §2). A journey passes within its budget, with zero wrong-conclusion risk, every fact carrying a source, an as-of date and a
release id.

| id | journey (D3) | path in the new IA | pass (K13 specifics) | tickets | data prerequisites |
|---|---|---|---|---|---|
| **A1** | Type "Oklahoma City" (1 min, ≤ 3 clicks) | `/` hero or header typeahead → place card → the Oklahoma City place dossier `/dossier/usa/ok/<place slug>-<GEOID>/` | named place first, homonyms with parents; the same result from header, home, index and map (UXR-24); no-JS GET works | SRCH-01…05, JUR-01/03/04, UXK14-2/6 | JUR-02b placement |
| **A2** | What is deployed, who runs and approved it, next decision (+3 min) | dossier At a glance → Figure 1 → "Who runs and supplies it" → Next decisions | each answer a sourced value or a typed absence naming what closes it; "records" wording; single-source share visible | VIZ-01a/01b/02, DSRC-02, WX-04a, GX-05a, QB-01 | PKG-07, CONF-06, I8 placement, WX-01/02 |
| **A3** | Print for a council member (+2 min) | dossier → Print | page 1 council brief with locator; map leads page 2; as-of, release id, permalink, licence on every page; greyscale-safe | UXK14-9, VIZ-02, TX-13a, FIG-01a | — |
| **A4** | Know what to bring (+3 min) | brief's "documents to bring" → evidence artifacts; "What we don't know" → task → records-request draft | document list resolves; draft downloadable; "SIG sends nothing" | EV-02, RQ-03b, RQ-04, WX-05 | G2 steps 1–2 (for stored documents) |
| **J1** | Defend a headline figure (5 min) | any `<Figure>` → breakdown → rows download | unit, denominator, "not a census", as-of, release id, Provisional where due; rows in ≤ 3 clicks; ≤ 2 actions to evidence | TX-09, DSRC-01/02, TX-10b, UX9-4, UXK14-3a | ACT-07, CONF-02 |
| **J2** | "Who supplies ALPRs to Texas agencies, and who can access the data?" (10 min) | search "Texas ALPR" → `/dossier/usa/tx/` → Explore → `/explore/?v=2&overview=supply&jurisdiction=iso3166-2:US-TX&technology=alpr`, then `overview=access` | every node named, every edge dated or "undated" with currency and source, evidence ≤ 2 actions, historical never present-tense; same facts JS-off via `/graphs/supply/usa/tx/` and entity pages | GX-01…09b, SRCH-05, VIZ-03 | D-K2-1, GX-04, I8 (Flock, placement), PKG-07, CONF-06 |
| **J3** | Is this figure disputed? (3 min) | contested marker → both sides; `/disagreements/place/usa/tx/` | ≠ marker in raspberry with both sides one click away; typed kinds kept apart | CX-01, UXK14-3b, GX-06b, QB-01 | CONF-05, CONF-03b |
| **J4** | Cite it durably (3 min) | Cite → `/s/<pub>/…` | the pinned URL returns identical bytes after the next release; legacy `?as_of_world=` resolves or answers 404/409 | TX-13a/b, UXK0-5, JUR-05 | G2 ACT-24 (HG-11), G3 REL-09 |
| **J5** | What changed since the last release? (5 min) | `/changes/` → place/source feed | a changes page and feeds per place and source, "SIG learned" vs "world changed" separated | TX-14, CHG-01, UX10-4 | second activated release; CONF-03a |
| **O1** | Who runs what in my county or city? (3 min) | `/dossier/usa/tx/harris-county-48201/` → figures, sites list, organizations | named agencies, technology classes and counts, each sourced or a typed absence | JUR-03, VIZ-02, MAP-05, GX-06a | I8 placement, PKG-07, CONF-06 |
| **O2** | Who decides and when; subscribe (2 min) | dossier Next decisions → `/watch/place/usa/tx/…` → `.ics` | approving body and next date or a typed absence; feed validates and exists even with 0 items | WX-01…06, WX-04a/b | WX-02/03 (agenda cadence) |
| **O3** | A local list without the map (2 min) | `/dossier/<path>/sites/` → "Download this view" | no-JS list with CSV, licence and attribution per compartment | MAP-05, UXK0-4, DSRC-03 | ACT-07 |
| **O4** | Act on a gap (3 min) | absence chip → `/task/<handle>/` | plain-language task, closing condition, request template, where to send results (the operator-named channel) | RQ-01…05, UXK14-3b | D-K11-4 |

---

## 9. Interfaces with G2 step 0, J3, G3 and L3

- **G2 step 0.** W0 rides republish #1 (ACT-06; copy on the 09-27 data) and #2 (ACT-07; attribution re-export). ACT-05's single
  publish path must land first. W0 adds no route family, so it changes no allow-list beyond ACT-06's. The G2 §6 claim rules bind
  all copy: no "one click", no "human-verified", no archive, research dossier or intake form until step 7.
- **J3.** K13 adopts J3's generation architecture, scrub, lanes, withdrawal and status lane unchanged, as amended by K9/K10
  (C-09). TX-08a and TX-09 become the site-wide `<ProvenancePanel>` and `<Figure>` contracts (C-25). TX-13a ships in W1;
  TX-13b with ACT-24.
- **G3.** Every page reads its stamp from REL-02 and cites path-pinned URLs; the redirect generator (JUR-05) feeds REL-03b's
  config generation; new route families make a release Class S; V5 gains the "every historical URL resolves" check and V11 the
  page-type budgets (UXK0-2). New templates use `withBase()` so TX-13b's refactor does not grow (UXR-25).
- **L3.** Owns the data-layer correctness prerequisites (CP-0…CP-10, CONF-01…14); K13 names the surfaces that wait on them (§4.2),
  renders L3's per-record basis and intervals through QB-01, links `/quality/` from About, and uses L3's words ("copy", "possible
  duplicate", "Not reviewed") in the lexicon.

---

## 10. Operator decisions

### 10.1 New decisions from K13

| id | decision | recommendation |
|---|---|---|
| **D-K13-1** | U-003.2 asks for "a global graph or set of graphs … that truly lays bare all that we know". The spec forbids a national hairball (SIG-UI-021/022) and network analytics before the ER gates (SIG-IDENT-030); K0 D-K0-6, K2 D-K2-2 and L3 recommend a **set of aggregated overview graphs** (O0 types … O7 adoption, ≤ 3,000 nodes each) plus entity egos and `/explore/`. Confirm that this satisfies the ask, or ask for more | **Confirm** the set of overviews; revisit when a single view needs > 3,000 labelled nodes (K0 revisit trigger 3) |
| **D-K13-2** | Navigation: six sections; Watch top-level; Open questions and "How sure is SIG?" under About; Disagreements under Explore (C-31) | **Yes** |
| **D-K13-3** | Map technology in one data hue until PKG-07 typing is live (C-02, with D-K14-5) | **Yes** |
| **D-K13-4** | Is publishing the de-duplication (L3 CONF-07b: record counts shown with a "listed cameras" interval) an **announce-readiness criterion**? Today dossier counts are row counts, up to 2.25× inflated (L2) | **Yes**; until then the site says "records", discloses republications and shows single-source shares (UXR-13/14) |
| **D-K13-5** | New route names: `/disagreements/`, `/changes/`, `/entity/` hub; retire `/task/new/**` (410) and never build `/site/` or `/map/place/` | **Yes** |

### 10.2 Existing decisions that block UX work (consolidated; recommendations are the rows')

| decision | blocks | row recommendation |
|---|---|---|
| **D-K2-1** organisation publication (50 reviews unlock 96.5 % of edges) + G2 ACT-10 | entity pages, network hub label, organisation search, dossier networks (U-003.2) | operator batch review + authoritative-registry auto-allow |
| **Q-31 / D-K1-2 / D-K0-4 / D-J3-4** DNS zone to Cloudflare for the zero-egress origin | MAP-02 on R2, TX-11, downloads | R2 with the DNS move; GCS acceptable below ~10k sessions |
| **D-K4-1** (HG-03) boundary sources | JUR-01 and everything placed | yes, after terms capture |
| **D-K14-1 + D3 Q5** landing statements | UXK14-6 | confirm or edit verbatim |
| **D-K14-5 / D-K14-6 / D-K14-9** palette, SIG-UI-044 form, "beautiful" sign-off | UXK14-1/4, CAP-02 | yes |
| **D-K1-1** reverse Round-9 Q8 (basemap) | MAP-02 | yes |
| **D-K3-7** held-out relevance set | SRCH-02/07 | the operator (≈ 30 min) |
| **D-K7-2** watch lane (G3 status class extended to `watch/**`) | WX-03, agenda alerts | the lane |
| **D-K11-1 / D-K11-3 / D-K11-4** campaigns, drafts, reporting channel | RQ-02, RQ-04, RQ-05 | as recommended |
| **D-K2-4** Flock share lists as organisation-level claims | GX-08b O2 at scale | yes, after the P8 screen |
| **D-J3-5** withdraw forbidden-terms sources before explorer and downloads | UX9-3, UX10-3, TX-10b | yes, first wave |
| **D-K5-1**, **D-K6-1…7**, **D-K8-1…4**, **D-K9-1…4**, **D-K10-1…4** | the named tickets | as recommended in each row |
| **Q-L3-1…6** | QB-01, `/quality/` | as recommended by L3 |

---

## 11. Risks

| id | risk | mitigation |
|---|---|---|
| R-1 | The UX ships ahead of the data and looks richer than it is (named graphs over undated, un-deduplicated data) | §4.2 interim behaviours are requirements, not suggestions (UXR-13/14/30/36/38); capability binding (UXR-01, DR-K14-05); CAP-01 checks wrong-conclusion risk |
| R-2 | W1 is large (39 tickets) and serial in places (JUR-01 → 02a → 02b → DSRC-01 → JUR-03) | parallel lanes: CI/kit, transparency exports, identifiers, placement, search; GX-02 and MAP-01a give visible wins early |
| R-3 | Shared modules become bottlenecks (lexicon, figure kit, identifier module) | they land in W1 with fixtures; page tickets consume them; changes need a ticket that updates every consumer's test |
| R-4 | Build time grows (≈ 5.6k dossiers, ≈ 26k entity objects, snapshots doubling the Astro build) | K4/K2/K6 measure per ticket; G3 incremental upload; thresholds (D-K4-3) |
| R-5 | Operator load: ~6 Class S readouts, many verbatim-copy confirmations and D-K2-1 reviews | batch copy approvals per republish; the readout generator (REL-06); the 50-review D-K2-1 batch first |
| R-6 | Lexicon changes ripple into maps, figures and copy | one file, generated consumers, a lexicon test; changes only through UXK14-4's successor |
| R-7 | Facet conformance breaks when a surface adds a parameter | UXR-10 matrix in CI fails closed |
| R-8 | Organisation withholding leaves Organizations empty at launch | nav capability binding hides the section; D-K2-1 surfaced as the top blocking decision |

---

## 12. Limits and method

- K13 is a synthesis: no measurement, no browser session, no live read. Every number is the cited row's, with that row's evidence
  class. Costs are added inferences.
- L3 landed during this row (commit `a1bc4dad`); its tickets were read and reconciled (C-27, C-28, §4.2, QB-01), but S1 still has to
  confirm exactly-one ownership across all streams (P9).
- Run counts use the rows' sizing convention (S ≈ half a fresh-context run, M ≈ one run); the per-row totals were re-added by K13 and
  may differ slightly from the rows' own summaries (e.g. K2's "≈ 12.5 runs").
- The capstone journeys are agent walkthroughs plus the operator's own walkthrough; they are not user research (P4). No independent
  human evaluation is assumed (U-008).
- Ticket ids are provisional; T3 assigns manifest rows 201+.
