<!-- SPDX-License-Identifier: CC-BY-4.0 -->
<!-- Copyright (C) 2026 The SIG project. Documentation is CC-BY-4.0; see LICENSE and §42. -->

# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

Post-`0.1.0` changes land here first, each entry naming its ticket and
requirement ids (G3 §9.4, SIG-REL-014). At each tag the heading becomes
`## [0.N.0] — tagged by the operator (see git show v0.N.0)` — the tag object
carries the true date, so no date is typed here — and the section ends with
"Production releases built from this range: …". A PR touching the
public-behaviour path set (`web/src/pages/**`, `web/src/layouts/**`,
`api/src/api/{routes,app,models}.py`,
`exports/src/exports/{release*,spine_export,manifest}.py`,
`ops/public_routes.toml`, `ops/disclosures.toml`, `policy/**`,
`ontology/src/**`) must add an entry here or carry a
`Changelog: none (<reason>)` commit trailer — the `docs` CI job enforces it
(`docs/build/tools/changelog_gate.py`).

### Added

### Added

- **The `/map/` T2 app shell (K1 MAP-03a) over the P36.36 no-JS baseline** (P36.37 / row 378; SIG-UI-065, SIG-UI-095, SIG-UI-097, SIG-UI-101, SIG-UI-102, SIG-UI-103, SIG-UI-104, SIG-UI-106, SIG-UI-107; UXR-13 records wording; UXR-18/SIG-UI-068 link targets) — the island migrated to Preact (no React reaches the `/map/` bundle), MapLibre ships as the K1 ESM split (`web/public/map/vendor/` via `scripts/prepare-map-vendor.mjs` — the shared chunk fetched once), the app carries a side panel (In view · Filters · Selected), a one-data-hue legend with the K13 status channels, the SIG-UI-101 selection panel (links emitted only when they resolve), the synchronized in-view list (places below z10, ≤50 records from z10, keyboard contract: Enter → list, Escape → clear), facet counts with the honest cannot-apply disclosure (seen-date greys below z10, no hatch), `sig.workspace-state/2` round-trips for `at=`/`layers`/`basemap`/`focus`/filters, and the K1 §2.6 basemap → boundaries → plain-background fallback chain with the loud notice; `runtime-deps.json` + `check:runtime-deps` gate the browser runtime allow-list. The committed basemap styles needed two generator fixes — `layers()` now receives the `namedFlavor` object (bare flavour names emitted `null` colours) and the emitted layers' source id is repointed `protomaps` → `basemap`.
- **The no-JS map baseline + per-dossier sites lists: `/dossier/<path>/sites/` pages, the interim `…#<key>` site-record link target, and the K1 §5 `/map/` restructure** (P36.36 / row 377; SIG-UI-068, SIG-UI-105; cited SIG-UI-039/040/042/063) — `web/src/lib/sites.ts` resolves every record to its deepest published dossier (nearest published ancestor, unresolved honestly counted) and derives the model the routes and the `/map/` places table share; the sites lists paginate ≤100 rows by path (`sites/`, `sites/page/<n>/`) with a compartment-grouped cross-licence reading view, per-row anchors, published-precision coordinates only, and a `#`-comment-licenced `sites/index.csv`; `/map/` now carries the static national overview figure (the committed FIG-01a fixture sheet — export builds ship `<export>/web/map/overview.svg` or an honest absence block), the GET place form (`/search/?type=place` + A–Z fallback) and the ≤70-row places table (located / sources / single-source share / no-point / site-list link) while the opt-in island is unchanged; `page-types.ts` classifies the sites family T1 under `sig.dossier-sites/1`.

- **Migration + the ONE redirect generator: `sig.redirects-conf/1`, jurisdiction/entity/handle/fixed-legacy rules, static stubs incl. `/id/<type>/<uuid>`, and the D-K4-8 corrections entries** (P36.35 / row 376; SIG-UI-058, SIG-JUR-009, SIG-JUR-012) — `web/src/lib/redirects.ts` derives one rule table from every URL history (`sig.jurisdiction-slug-history/1`, `sig.slug-history/1` via `resolveEntityRequest`, `*_handles_history`, the declared fixed legacy list gated on the emitted-route set); `astro.config.mjs` `sigRedirects` emits `dist/redirects.conf` and fails the build if a historical slug resolves to nothing; `moved` dossier stubs carry a zero-JS meta refresh, split/corrected pages serve in place `noindex`; `/id/<type>/<uuid>` fallback stubs render per status; `/corrections/` renders the three migration-class entries derived from the history (wording pending verbatim confirmation, `copy-batches/batch-04.md`); `ops/public_routes.toml` allow-lists `id` + `redirects.conf`; a second redirect-writing path fails the unit lint.

- **Grouped dossier index + navigation: `sig.dossier-index/2`, sort/facet/A–Z routes, and the K4 §5.2 row model** (P36.34 / row 375; SIG-UI-057, SIG-JUR-001…008/010/011, D-K4-3 [B-44] carried verbatim) — `web/src/lib/dossier-index.ts` `groupIndex`/`sortIndex`/`facetIndex`/`azGroups`/`publicationRegime` + `INDEX_FIELD_DEFINITIONS` + `indexFigureSpecs`; `DossierIndexRow.astro` renders the ten K4 fields; `dossier/index.astro` rewritten with the place-search GET form; new routes `dossier/sort/[key]`, `dossier/by/[dim]/[value]`, `dossier/a-z/**`; committed fixture corpus + index sprite.

- **Basemap pipeline + host posture: `sig.basemap-lock/1`, generated light/dark/context styles, self-hosted glyphs, `sig-ops basemap`, and the queued R2 create** (P36.33 / row 374; K1 MAP-02 §2, SIG-UI-100, ADR-229; implements ADR-156 §Decision 6 — D-K1-1 'yes', Q-31/D-K1-2 [A-3] = a R2-after-OP-09, D-K1-3 [B-22] carried verbatim) — `ops/basemap.lock.json` pins the measured reference build `20260930.pmtiles` (138.5 GB, z0–15, schema 4.15.2) + the `@protomaps/basemaps` 5.7.2 v4↔5.x pairing + glyph/context/host/serving/refresh/cost blocks; `web/scripts/gen-map-styles.mjs` emits committed `style-light/dark/context.json` (grayscale/black flavours, drops `address_label`/`roads_shields`/`roads_oneway`, strips every `icon-image`, buildings ≥ z15, road labels ≥ z13, `lang: en`, no sprite sheet); Noto Sans Regular+Italic glyphs committed same-origin under `/map/fonts/` with a `sig.basemap-glyphs/1` manifest + `OFL.txt`; `sig-ops basemap` carries `check | glyphs fetch|verify | context-build | refresh | host | kill-switch`; CSP `connect-src` admits `https://tiles.surveillancegraph.org` (K0 §4.8); the OM-20-named R2 create (`sig-basemap` + CORS/Range/immutable) is `prepared_not_executed` (D-P36.33-1 — no hosted creds, OP-09 absent) with the packet under `docs/build/reports/p36.33-basemap-host/`; `ops/basemap.alert.json` (`sig.basemap-alert/1`) declares the usage thresholds + two-level kill switch.

- **Search query engine v2 + benchmark harness: the `sig.search-results/2`
  contract and `sig.search-benchmark/1` reports** (P36.32 / row 373; K3
  SRCH-02 §4.2/§7/§9, K13 §7 W1; serves SIG-SRCH-003/004/005/006 region
  and the SIG-SRCH-011…013 surface; `D-K3-7 [B-28]` answered 'Separate
  agent, labelled' carried verbatim) — `exports/src/exports/
  search_query_v2.py` is the serving half of the §4.2 pipeline over the
  /2 indexes: tier-0 identifier resolution, case-sensitive acronym
  aliases (never word-matched, word-hits collapsed — SIG-SRCH-005),
  exact-name place resolution with records-held homonym ordering
  (SIG-SRCH-004), weighted catalog text × type prior, per-compartment
  tiered record pages (name phrase → all-words-in-name → place/source
  words) with per-group cursors and exact counts, stated-only spelling
  suggestions, facets with counts, and the carried-over withdrawal
  barrier, deadline and 100 KiB wire bound. `search_benchmark.py` runs
  dev/release/held-out modes; the held-out set is verified only via the
  committed descriptor sha256 and every metric surface carries the
  `agent-authored held-out set; not independent` estimand label (TS-20).
  `sig-exports search-benchmark` exposes the release + held-out legs.

- **Search index v2 builder: `sig.release-search-index/2` artifacts —
  a compact per-compartment record index, `claim_ref`, the release
  catalog index and `search_aliases.toml`** (P36.31 / row 372; K3
  SRCH-01, K13 §7 W1; serves SIG-UI-073, SIG-UI-074, SIG-SRCH-004,
  SIG-SRCH-005, SIG-SRCH-011) — `exports/src/exports/search_index_v2.py`
  builds the deterministic, release-pinned v2 indexes: a contentless
  weighted FTS5 record index per compartment (marked interim derived
  names, K4 place text, registry source names, two filter indexes), a
  `claim BLOB(16)` claim→record table, and one catalog index for every
  entry type (places from JUR-01's registry or the key-map interim,
  sources with facet fields, the technology vocabulary, K2 entities as
  present, K8 documents, content pages; prefix-2/3 FTS + trigram +
  exact-names + alias tables). `release.py` emits them additively beside
  the unchanged v1 artifacts, all integrity-listed;
  `verify_search_index` stream-hashes and refuses drifted artifacts
  before any read-only open. The alias registry seeds 11 reviewed rows;
  a case-sensitive acronym is never reachable through normalized
  word-lookup (SIG-SRCH-005). SRCH-03 (P36.38) flips serving.

- **Procurement relevance rule: the `sig.procurement-relevance/1`
  verdict artifact — one classification over every notice-family
  entity, the D-K2-5 exclusion posture and the H-13 buyer-page
  label** (P36.30 / row 370; K2 GX-04/H-13, K13 §7 W1 GX-04;
  `D-K2-5 [B-22] = as recommended: exclude unclassified
  procurement` — the answered plan decision, carried verbatim;
  serves SIG-UI-039/040, SIG-ENG-042) —
  `policy/src/policy/procurement_relevance.py` is the ONE
  classification every surface reads: a notice is
  `surveillance_related` on a `matched_keyword` claim or a
  product/CPV/NAICS value matching the connectors' committed
  reviewed vocabulary (the agenda verbatim-scan terms, the TED
  sweep keyword patterns and acquisition-term literals, the
  verified CPV code set — read as data, sha256-bound; the NAICS
  slot is declared and honestly empty today); everything else is
  `not_classified` — never silently dropped, excluded from the
  surveillance surfaces and surfaced only as a buyer-page row
  labelled `not classified as surveillance-related` (K2 H-13).
  `build_spine_export` emits `web/procurement_relevance.json`
  (schema + publication binding + vocabulary evidence + counts,
  SIG licence, web compartment) over a new
  `notice_relevance_facts` query; `web/src/lib/procurement-relevance.ts`
  mirrors the row types and the exclusion/buyer-row semantics
  (`surveillanceNotices`, `buyerNoticeRows`, `noticeRowLabel`)
  and `getProcurementRelevance` loads it build-time.
- **Entity URL keys and slug history: the `sig.slug-history/1`
  append-only record, frozen-hash collision extension, the `/id/`
  redirect semantics and the export artifact the redirect generator
  reads** (P36.29 / row 369; K2 §3.3/§6.5, K13 §7 W1 GX-03, ADR-227;
  SIG-UI-067/109/111/112/113, SIG-EVUI-010 — owner; serves SIG-UI-039/
  040, SIG-ENG-042) — `policy/src/policy/slug_history.py` is the history
  half of the one identifier module (`merge_history` carries prior rows
  verbatim and appends `renamed`/`merged`/`split`/`withdrawn` terminal
  rows; `freeze_hashes` applies the foreign-uuid collision extension in
  deterministic order without ever rewriting an issued hash;
  `check_unique_labels` makes SIG-UI-111 an export refusal;
  `resolve_request` is the single redirect vocabulary — `/entity/` hash
  authoritative 200/301/300/410, `/id/<type>/<uuid>` 302/301/300/410).
  `build_spine_export` emits `web/entity_slug_history.json`
  (`sig.slug-history/1`) and takes `previous_entity_history` as the
  release-chain binding; `web/src/lib/entity-history.ts` mirrors the
  resolver and `getEntitySlugHistory` loads it build-time. Person
  entities emit nothing under any path (SIG-UI-112).
- **Static figure kit — graphs, charts and legends: deterministic
  bipartite and radial layouts, four chart emitters, lexicon-generated
  legends and table twins** (P36.28 / row 368; K6 §6.2/§6.3, K13 §7 W1
  C-07 FIG-01b, K14 §4/UXK14-8, K5 DSRC-02 chart-component audit;
  ADR-226 extends ADR-157; SIG-UI-125 — owner; serves SIG-UI-061/066/
  131/133/134/039/040, SIG-ENG-042) — `exports/src/exports/figures/`
  gains `graph_model.py` (`sig.figure-kit-graph/1` +
  `sig.figure-kit-chart/1` plain-data specs), `layout.py` (closed-form
  deterministic two-column bipartite and radial ego placement — no
  iterative solver, no PRNG, no third-party layout dependency; the GPL
  `igraph` wheel is never imported), `legend.py` (legends generated
  from `lexicon.json` listing only the encodings the figure actually
  emitted, in lexicon order, failing closed on unbound tokens),
  `network_figure.py` (bipartite dossier networks + radial ego figures;
  node/column/ego caps degrade by spec-declared `group_by` grouping —
  group nodes carry labels and member ids in the table twin — and
  refuse rather than silently prune), and `chart.py` (bar, strip,
  stacked-bar and timeline only — other kinds refuse named). Every
  figure ships `role="img"`/`<title>`/`<desc>` accessibility,
  compound-path-per-edge-class edges, `table_columns`/`table_rows`
  twins, and wide + narrow variants; print keeps figures unsplit and
  greyscale-safe. `sig-exports figure` gains `network|ego|chart` +
  `--out-narrow`.
- **Static figure kit — geography: one deterministic Python renderer for
  every build-time map figure** (P36.27 / row 367; K6 NEW-3, D-K6-4;
  ADR-157; SIG-UI-066/094/123/124/131/134 — owner; serves SIG-UI-039/040,
  SIG-ENG-042) — `exports/src/exports/figures/` is the single home for
  projection and fit, geometry simplification, the `static-12px@1`
  binning rule, H3 areas vs tier-0 points behind fail-closed tier and
  precision guards, jurisdiction and child outlines with links, locator
  and index-sprite data, and honest typed not-drawn counts. Output is
  byte-deterministic, CSP-safe SVG — no `<script>`, no `on*` attributes,
  no external references — with `<title>`/`<desc>`/`role="img"`/
  `aria-labelledby` accessibility and classes plus colour variables
  bound to the shared lexicon and design tokens, never a forked palette.
  A standalone document mode carries light/dark token variables for
  P36.19's dedicated SVG response policy. `sig-exports figure
  map|locator|sprite` is the build-time CLI; figure classes land in
  `web/src/styles/epistemic.css` with a vocabulary/parity test.
- **Print v2 — the council-brief page 1, running head and foot on every
  logical page, a terms-used list, a QR back to the pinned permalink,
  and declared print figures under the figure contract** (P36.26 /
  row 366; K14 UXK14-9; SIG-UI-098/130/155 — owner; serves SIG-UI-039/040,
  SIG-ENG-042) — `web/src/lib/print.ts` composes the document:
  `sig.print-figure/1` declarations (map/extent/trend/axis kinds) render
  on their own no-split page and unknowns print as named absences, never
  silent omissions; the brief carries the at-a-glance counts inside new
  `glance-recorded`/`glance-unknown` figure regions so the material-number
  gate keeps every count evidence-linked. `web/src/lib/qr.ts` is a
  dependency-free byte-mode QR encoder (EC-M, versions 1–10, Reed–Solomon
  + interleaving) emitting SVG path data at build time. Print components
  (`CouncilBrief`, `PrintChrome`, `PrintFigure`, `PrintTerms`) plus
  `web/src/styles/print.css` give every page place/doc-kind chrome, the
  as-of pair, permalink, licence-if-bound, `Page n/N` and the P35.42 cite
  sentence — still T0, zero `<script>`, greyscale-safe by border/label,
  never colour alone.
- **Brand — the K14 node-link mark, the favicon set, per-page-type
  social cards generated at build time, and per-type meta
  descriptions** (P36.25 / row 365; K13 UXK14-7 + K14 §4.12/DR-K14-20;
  SIG-UI-154 — owner; serves SIG-UI-039/040, SIG-ENG-042; `D-K14-2
  [B-22] = yes` carried verbatim) — `web/src/lib/brand.ts`
  (`sig.brand-mark/1` + `sig.social-card/1`) declares the mark once —
  three nodes, two solid edges, one dashed edge in a single ink, no
  badge, no epistemic hue; the dashed edge is brand, never a legend
  symbol. `LogoMark.astro` renders it in `currentColor` beside the
  wordmark; `public/favicon.svg` carries it byte-pinned to the one
  renderer. The `sig-brand-assets` build hook emits `favicon-32.png`,
  `apple-touch-icon.png`, `brand/logo.svg` and
  `social/card-{t0,t1,t2}.png` (1200×630, "Data as of" from the same
  data layer the pages read) at `astro:build:done` via Astro's own
  `sharp` dependency — zero new packages, zero added JavaScript.
  `BaseLayout` and the standalone print head emit the favicon links
  and the full OG/Twitter `summary_large_image` block on every public
  route (T3 shares none), and `defaultDescription` gains the T0/T2
  per-type forms beside the MD-01 T1 form. `ops/public_routes.toml`
  allow-lists the four new emitted top-level entries.
- **Copy lints in CI — the K13 vocabulary rules run as a build gate over
  every discovered route, report-mode until each surface's ticket flips
  its routes to enforce** (P36.24 / row 364; K13 UXK14-5 + K14 UXK14-5;
  SIG-UI-063/144/153 — owner; serves DR-C6-28, DR-K14-10/11/19,
  SIG-UI-053/062/145) — `web/scripts/check-copy-lints.mjs` reads
  `dist/page-types.json` (the P35.50 route manifest, so no built route
  escapes the corpus) and sweeps each route's `<main>` + `<footer>` for
  UUIDs/snake_case keys/raw enums/requirement ids in prose (DR-C6-28),
  repeated 8+-word sentences (SIG-UI-144), visible-by-default chrome
  over 40 words (SIG-UI-145's rendered count), words joined at element
  boundaries and ungrouped 5+-digit runs (SIG-UI-153), a bare "unknown",
  "camera sites"/"listed cameras" outside the `data-sig-count="dedup"`
  interval contract and the reverse (SIG-UI-063), Candidate/Provisional
  collapses (SIG-UI-062), and the lexicon's multi-word banned phrasings;
  the CP-8 readability report prints advisories that never fail.
  `web/scripts/copy-lint-enforce.json` (`sig.copy-lint-enforce/1`) is the
  report→enforce map — every route defaults to `report`; a surface's
  ticket flips its page-type-registry pattern to `enforce` as it fixes
  its own copy. Wired into `npm run check` as `check:copy` after
  `check:lexicon`; `tests/unit/copy-lints.test.ts` proves the verdict
  both ways over planted fixture dist trees (17 legs).
- **Component kit B — the K14 epistemic visual layer: the contested
  marker's two agreement levels with a both-sides link, the labelled
  contradiction range, the actionable absence chip, the provenance
  panel's Astro shell, typed callouts, and typed empty surfaces by
  contract** (P36.23 / row 363; K13 UXK14-3b; cites SIG-UI-039/040,
  SIG-ENG-042, SIG-UI-083/086/151) — `ContestedMarker` now renders
  `CONTESTED` vs `IRRECONCILABLE` (same ≠ glyph, different label +
  frame) and `href` makes the marker one click from the both-sides
  list (J3 — wired on `/evidence/[id]/`); `ContradictionRange` names
  its agreement level and labels one dot per claim;
  `AbsenceChip.astro` wraps the ONE shared `sig-absence-hatch` texture
  (SIG-UI-007) with the kind symbol + lexicon label, a UA-native
  meaning popover and the "Help find it ›" action (a plain GET link
  to the research queue or a real `/task/<handle>/`, never a mock
  generated-task page) — `/map/` mounts it on every unlocated record;
  `ProvenancePanelShell.astro` is the Astro shell over the single
  `sig.provenance-panel/1` renderer (`ProvenancePanel.tsx` keeps sole
  emitter status — SIG-UI-083); `lib/callouts.ts` `sig.callout/1` +
  `Callout.astro` add the closed note · caution · known_issue
  vocabulary that fails closed on an unknown kind (SIG-ENG-042);
  `EmptyState.astro` accepts a typed `parts` contract so the
  non-absence cause classes mount (SIG-UI-086); the internal
  `/component-kit/` harness grows kit-B fixture sections exercising
  every component over honest data. New public sentences ride
  `batch-03.md` (`CK-61`…`CK-64`, sha256-pinned `pending`).
- **Component kit A — the K14 visual layer: stat row, six-kind card
  family, `<sig-table>` visual shell, support/field/status chips,
  directness/access/licence/mirror badges, universal five-part typed
  empty states, and the branded 500 page completing the error set**
  (P36.22 / row 362; K13 UXK14-3a; SIG-UI-054/083/084/086/151 —
  owner; cites SIG-UI-039/040, SIG-ENG-042) — `web/src/lib/`
  `badges.ts` (`sig.badge/1`), `cards.ts` (`sig.card/1`) and
  `errors.ts` (`sig.error-page/1`) are the fail-closed contracts the
  nine new `web/src/components/` renderers (`Badge`, `StatusChip`,
  `SupportChip`, `FieldChips`, `StatFigure`, `StatRow`, `Card`,
  `DataTable`, `ErrorState`) draw from; every kit numeral renders
  inside the one `<Figure>` contract (SIG-UI-084) so evidence stays
  ≤ 2 actions away (SIG-UI-054), and `sig.provenance-panel/1` stays
  the only panel (SIG-UI-083). All 22 empty surfaces now carry the
  typed five-part state with a named `cause` class — pipeline causes
  never route to the research queue and `filtered_none` /
  `not_redistributable` / `degraded` render no absence hatch
  (SIG-UI-086). `/500/` joins 403/404/410 under `sig.error-page/1`
  with the search · home · status recovery trio, emitted flat as
  `/500.html` (the 404 convention) for the error_page mapping (SIG-UI-151).
  `lexicon.json` gains §10.5's D2–D5 directness states; an internal
  `/component-kit/` harness (`SIG_BUILD_INTERNAL`, T1, never
  published) exercises every component over fixtures.
- **The `sig.workspace-state/2` contract — one parameter registry driving
  T2 URL state, "cite this view" snapshot links, and a surface × facet
  conformance rule** (P36.21 / row 361; UXR-09/UXR-10;
  SIG-UI-052/059/060/093 — owner; ADR-225; cites SIG-UI-039/040,
  SIG-ENG-042, ADR-134, ADR-155) — `web/src/lib/workspace-state/`
  registers every supported parameter (`sig.workspace-state-registry/1`)
  with its type, cardinality, default, vocabulary, legacy aliases and
  per-surface application; an unregistered or unsupported parameter is
  refused loudly, never silently dropped. `v=1` links keep resolving
  identically while new links mint `v=2`; `bbox`/`frame` fold into the
  canonical `at=` frame, `kind=site`→`type=record`, `US-OK`→
  `iso3166-2:US-OK`, `view=network`→`graph` and `location=any`→absent
  all land with visible normalisation receipts. Every T2 surface
  (`/map/`, `/network/`, `/search/`) partitions the registry into
  applied-or-visibly-named: a parameter it does not apply earns a
  `role="status"` facet notice instead of silently appearing to work.
  "Cite this view" mints release-pinned `/s/<pub>/<surface>/?v=2&…`
  links as copyable text; T2 documents carry `noindex,follow` plus the
  base canonical, and the sitemap lists registry-derived canonical
  T0/T1 routes only.
- **The T1 enhancement kit — five framework-free custom elements that
  upgrade server-rendered HTML, emitted as `/_kit/sig-*.js` module
  entries and admitted only on T1 pages** (P36.20 / row 360; UXK0-4;
  SIG-UI-085/089/090/091 — owner; ADR-224; cites SIG-UI-039/040,
  SIG-ENG-042, ADR-155, ADR-223) — a `sigEnhancementKit` build hook
  bundles each `src/elements/sig-*.ts` into a stable-name
  `/_kit/sig-<name>.js` module that `tests/e2e/t1-module-entries.json`
  allow-lists verbatim and the strict CSP's `script-src 'self'` admits
  without a new directive. `BaseLayout` gates the shared cite disclosure
  upgrades on the page-type registry — only full-chrome T1 pages load
  `sig-details` (fragment + print handling), `sig-cite` (plain/APA/
  Chicago/legal restatement from the block's own `data-cite-*` fields)
  and `sig-copy` (a copy action beside the permalink) — while
  `/sources/` mounts `<sig-table>` (sort with `aria-sort`, text filter,
  licence/credit facet chips, column chooser, URL view state, and a
  "download this view" CSV whose `#` provenance lines restate the
  licences of the visible rows) and the internal `/enhancement-kit/`
  harness mounts `<sig-typeahead>` (an APG combobox over static
  `sig.typeahead-shard/1` fixtures — never a live-spine read — over a
  plain GET form that keeps working without JS). Every element injects
  only `[data-enhancement]` chrome, so JS-on `main` text minus those
  subtrees equals the JS-off page, print shows the same facts, and a
  module that never loads leaves the markup untouched.
- **Release classifier, standing go, and Class-S readout generator —
  `sig-ops release classify` consumes a completed V14/V15 verification
  suite's emitted evidence and returns a journaled `class_r` only when
  every §7.3 R-column condition is proven; any trigger or unevaluable
  check returns `class_s`** (P35.60 / row 337; SIG-REL-012 +
  SIG-CONF-010 — owner; ADR-221; cites D-G3-3/B-9) —
  `ops/src/ops/release_classify.py` never re-measures: it maps every
  R-column condition to one verdict row (`r` / `trigger` /
  `unevaluable`) and fail-closes to `class_s` on a missing or malformed
  suite input, a V14 anomaly, a ratchet regression, a new source, a
  Part VIII screen change, a code/route/allow-list/public-surface/
  version/schema/disclosure delta, or a waiver. The standing-go leg
  (B-9) validates an operator-adopted `sig.promotion-approval/1` — never
  implied adoption — for scope, revocation, voiding, code-commit scope
  and expiry (an in-flight release classified while the go was still
  valid may promote), and appends an immutable `sig.standing-go-void/1`
  marker on a ratchet regression, Part VIII screen change or new
  source; the adopted record itself is never edited. A `class_s`
  result emits an agent-drafted `sig.release-readout/1` pair under
  `registry/readouts/` whose signature slot stays empty (no proxy
  operator signature) and whose notice rides the existing alerts seam
  without committing an operator address; rollback, clear-latest and
  withdrawal keep their recorded operator go with no readout.
  `exports/src/exports/release_fingerprint.py` adds the deterministic
  template fingerprint stamped into release metadata for V14's
  template delta. `sig-ops release promote` consumes the journaled
  class and approval metadata rather than re-classifying. The
  operator-adoption prerequisite (the standing-go text and the first
  signed Class-S readout) is filed as `D-P35.60-1`; no classification
  was applied, no notice sent, and no signature produced by this
  change.
- **Verification suite B + the pre-authorised post-promote automatic
  rollback — `sig-ops release verify` now runs the full V1–V15 gate and
  a failed post-promotion check restores the previous serving
  generation itself** (P35.58 / row 335; SIG-REL-007 — this row's half;
  serves SIG-CONF-007's V15 hook and SIG-OPS-011's probe targets; cites
  D-G3-8/B-9, ADR-154, SIG-REL-010, SIG-REL-013) —
  `ops/src/ops/release_verify.py` adds V6 number truth (every
  `data-artifact` figure element must be figure-manifest-listed, resolve
  under the release's artifact space and recompute to the rendered
  value, with the artifact as-of matching `as_of_world`), V7 API parity
  (the §6.4 table: `release_publish_verify.api_parity_check` over the
  staged half verbatim plus served-half canonical-JSON slice equality,
  `/` and `/health` naming the release, live-spine routes carrying their
  basis label — no API surface is a `skip`, which blocks), V8
  attribution sanity (no empty required attribution, `LICENCES.json`
  per compartment, map pages naming upstream holders, no bare-id or
  handle-shaped source render), V9 jurisdiction–coordinate sanity (no
  null-island/out-of-range points, the `covers` oracle catching axis
  swaps, out-of-boundary points withheld or disclosed, dossier rollup
  counts recomputed), V10 withdrawal barrier (the expected deny set
  re-derived over a throwaway registry mirror and diffed against the
  served `withdrawn.conf`, every alias — or all-new plus a deterministic
  20-sample in P — probed for `410` + its own `sig.tombstone/1` body,
  `X-SIG-Conf-Gen` equal to the recorded generation), V14 diff sanity
  (the six deltas vs the current latest emitted as measured evidence —
  the §7.3 bounds fail, the classifier stays its own row), the V15 hook
  (`sig.quality-report/1` handed to `exports.quality.run_release_gate`
  verbatim — verdict, enforce, not-evaluable, ratchet and the
  `class_s` signal ride the evidence; the hook is hosted, never
  re-implemented), and P1 (`/releases/latest.json` = `/release.json`
  pub, release age < 35 days, served `X-SIG-Conf-Gen` = recorded gen,
  cadence declarations present). `ops/cadence.toml` declares the
  `sig-release-pointer`/`sig-release-age`/`sig-conf-gen` targets plus an
  unpromoted-route absence target, each with cadence + trigger;
  `probe_hosted` dispatches them and an unreachable origin records a
  red probe, never a crash. `release promote`'s post-check failure path
  is the D-G3-8/B-9 pre-authorised one: `failed` journaled, the lock
  released, then `release_reversal.verb_rollback` to the prior latest
  (or `verb_clear_latest` on a first release) writing a **new immutable
  conf generation**, a recorded `release-auto-rollback` alert fired, and
  an append-only `registry/incidents/` note + `incident` journal event
  naming the failed checks, the generations, the authority, the rollback
  outcome and the alert — the promote still raises `post-check-failed`,
  a refused rollback records verbatim, and a crash-resumed promote
  restores the failed generation's recorded `previous`. Fixture and
  composed proof only: no hosted, staging or public leg ran in this
  row — the suite's first live invocation and a real post-promote
  rollback are the release rows' legs.
- **Verification suite A — `sig-ops release verify --mode S|P` running the
  V1–V5 + V11–V13 release gate with durable JSON result evidence** (P35.56 /
  row 334; SIG-REL-007 `Also:` — the V6–V10 + V14 + auto-rollback half is
  P35.58's) — `ops/src/ops/release_verify.py` adds the suite: V1 integrity
  (`validate_release` complete; descriptor digest recomputes to the pub id;
  every <1 MiB integrity-manifest artifact fetched over HTTP and
  sha256-matched plus a stratified 2 % sample of larger/record files, capped
  at 200 in P mode), V2 identity and clock (descriptor v2,
  `environment=production`, pushed/clean 40-hex commit, no `0.0.0`, the §3.3
  clock rules, label uniqueness, `as_of_world` monotonicity — unevaluable
  legs land honest `skip`s), V3 allow-list and absence (`public_routes.toml`
  route-set diff, content assertions, denied-route probes answering 404),
  V4 stamp and manifest (every HTML page carries exactly one matching
  `sig-release` meta + `describedby` link + visible stamp block, and
  `X-SIG-Release` rides every response — P-mode compares against
  `latest.json`), V5 link crawl and §5.3 containment (every same-origin
  href → 200 or a declared 410; `s/<pub>/` links stay in-prefix bar the
  declared exceptions), V11 zero-JS/budgets/accessibility (the committed
  `page-budgets.json` ceilings + a real Playwright/axe WCAG scan via
  `web/scripts/axe_scan.mjs` — absent runner or browser is a `skip`, never
  a pass), V12 transparency scrub (the `policy.transparency` secret scan
  over every publish-set byte; one hit fails, never waivable), V13
  disclosures (digests recomputed, required renderings checked,
  eval-status wording never overclaims). Every check emits a
  `sig.release-verify/1` result row (`pass`/`fail`/`skip` + evidence +
  duration) persisted per check plus a suite document under
  `--results-dir`; **any failure or skip blocks promotion** — waivers apply
  only under `--class class_s` with a named readout reference and are
  recorded, never silent. `--origin` (repeatable, with `--origin-header`
  for the staging identity token), `--tree` (the local fixture origin,
  `origin_kind: "tree"` — never a staging/public claim), `--no-repo-probe`,
  and `--repo-facts` control the surfaces; no origin → every check `skip`s
  and the suite blocks (SIG-ENG-042). `release verify` with no `--mode`
  keeps the pre-P35.56 bounded scope verbatim. Composed proof:
  `tests/e2e/test_release_verify_composed.py` runs S and P over the real
  nginx serving shape — the P leg surfaced one genuine serving gap
  (`/releases/catalog.jsonld` 404s publicly; filed `D-P35.56-1`).
- **Rollback, clear-latest, withdrawal, legacy-floor import, and the
  conf-generation regression probe — `sig-ops release` reversal verbs,
  compartment-scoped denials, and the runbook procedures** (P35.55 /
  row 333; serves REL-08, SIG-REL-013, SIG-OPS-004; cites ADR-220,
  G3 GT-3/GT-9, ADR-156) — `ops/src/ops/release_reversal.py` adds the
  five operator-commanded verbs. `rollback --to <pub|label|legacy-floor>`
  requires a reason, refuses to "roll back" to the current pointer or
  to a never-promoted namespace, **re-derives the current withdrawal
  barrier** (a rollback never resurrects withdrawn material), writes
  `conf/<gen+1>` whole, and rolls a *new* revision — never reverts
  Cloud Run traffic to an old revision whose pinned `SIG_CONF_GEN`
  could re-serve withdrawn routes. `clear-latest` is archive-only: the
  latest view 404s honestly under `v/none/` while every promoted
  namespace and the barrier keep serving. `withdraw --disposition
  <sig.withdrawal-order/1> --authority <sig.operator-authority/1>`
  fails closed without an unexpired authority record, appends
  disposition records (never edits), applies the barrier across every
  staged namespace, covers **every serving alias** (no-slash,
  trailing-slash, `index.html`, and the `.json` twin) with dated,
  public-safe `sig.tombstone/1` bodies, writes a `conf/<gen+1>` with
  `withdrawals_sha256` in the latest pointer, rolls api→web as new
  revisions, probes every denied alias (optionally requiring origin
  HTTP 410), and records a `sig.withdrawal-receipt/1` under
  `registry/receipts/` carrying `claim_spine_touched: false`. Purge is
  bounded to `--purge-versions`: noncurrent object generations of
  already-removed names only, generation-qualified via the new
  `list_object_versions`/generation-delete GCS APIs — the live object
  generation and the claim spine are never touched. `import-floor`
  stages a `legacy-YYYYMMDD` tree with a `sig.legacy-floor/1` record
  (a label, never a publication ID). `conf-gen-probe` measures each
  origin's `X-SIG-Conf-Gen` against the recorded generation and
  journals a `sig.probe-run/1` — an older served gen alarms loudly.
  `DispositionRecord` gains an optional `compartment` scope honoured
  by `apply_withdrawals`. `release promote` now records
  `withdrawals_sha256` in `latest.json`, detects verify→promote
  withdrawal drift, and re-derives the deny barrier under the promote
  lock (closing D-P35.54-1), refusing if the registry shifts mid-seam.
  RUNBOOK gains republish / rollback / withdrawal-takedown procedures.
  No hosted mutation runs in this ticket — rolls stay prepared-only
  unless the operator passes `--execute-rolls`.
- **Configuration generations and metadata-only promotion — the
  templated sig-web edge, `conf/<gen>/` immutable config sets, and the
  `sig-ops release promote` verb** (P35.54 / row 332; serves
  SIG-REL-006, SIG-OPS-004; cites ADR-220, G3 §4.1–§4.3/§5.1–§5.2/
  §6.2–§6.4/GT-9, ADR-156, ADR-178) — `ops/web/nginx.conf` is now the
  G3 §4.2 envsubst template: `docker-entrypoint.d/40-sig-conf.sh`
  renders exactly `${SIG_LATEST_PUB}`/`${SIG_LATEST_LABEL}`/
  `${SIG_CONF_GEN}`/`${SIG_STAGING}`/`${SIG_ROBOTS_TAG_LINE}` at start
  (refusing a half-set env, falling back to the frozen
  `nginx-legacy.conf` when no release env is present). The release
  bucket mounts at `/mnt/rel`: the `map $uri_pub $promoted` block
  includes the generation's `promoted.map` (`default 0` — an
  unpromoted namespace 404s by construction; the staging flag bypass
  is a rendered constant, never a request input), and
  `withdrawn.conf`/`selectors.conf`/`labels.conf` include per
  generation. `sig-ops release promote` is dry-run by default; with
  `--apply` it takes the registry LOCK, re-checks the folded journal
  (staged → verified → classified, never already-promoted), honours a
  `sig.promotion-approval/1` record (class S requires a signed
  readout naming the pub), writes `conf/<gen+1>` whole — promoted
  map, latest pointer, carried withdrawal/selector/label fragments,
  and the `releases/` index set generated by the release tool alone —
  and plans the digest-pinned `sig-api`-then-`sig-web` roll legs
  (`min-instances=1` on web) through an injected runner. Promotion
  copies zero release bytes (`copies_release_bytes: false`); an
  interrupted generation resumes in place; the `promoted` event
  carries gen, label, class, approval ref, and serving digests. The
  composed `release-serving` profile proves the flip end-to-end:
  promoted `/r/<pub>/` 200s with the provenance pair, unpromoted and
  staging-gated routes behave per GT-9, and the `/releases/` index
  set serves out of the generation. `D-P35.54-1` records the one
  residual (a disposition journaled between verify and promote does
  not re-derive into the carried map — the P35.55 writer owns it).
- **Count-conserving map tiles (`sig.map-tiles/2`), a six-check tile
  verifier, and a pinned-tippecanoe CI leg** (P35.52 / row 330;
  serves SIG-GEO-012/013, SIG-UI-019, SIG-UI-038; fixes F-104,
  F-414; cites ADR-118, ADR-106 §4, K1-map §3/§9.2; writes ADR-156)
  — the per-licence-compartment PMTiles archives are rebuilt to two
  layers: `cells` (H3 count cells at z0–9; res 3/4/5/6 over the
  z0–4/5–6/7–8/9 bands) and `sites` (every published located record
  retained — tier 0 from z10, tier 1 from z11, tier 2 from z12 as
  its H3 polygon, tier 3 never). The exporter writes per-feature
  `"tippecanoe": {minzoom, maxzoom}` members and invokes tippecanoe
  with `-r1`; drop/coalesce flags are refused by an argv guard and
  an over-500 KiB tile fails the build loudly. The pure-Python
  renderer honours the same ranges and dedupes only byte-identical
  features (the old same-cell coalescing is gone). Archives are
  content-hash named (`<compartment>-sites.<sha8>.pmtiles`),
  indexed by `web/tiles/index.json`, and nginx serves them
  `immutable`; the browser sums cell counts across the active
  compartments in memory — no licence-mixed public archive exists.
  `sig-exports tiles verify` measures the six K1 §9.2 checks
  (conservation, renderer parity, precision+tier, size, metadata,
  CI legs) into `reports/tiles_verify.json`; CI builds pinned
  tippecanoe 2.79.0 from the `ops/Dockerfile` pin and verifies a
  deterministic 50k synthetic fixture, and the nightly job verifies
  the real-sized national fixture.
- **Page-type budgets, generated Lighthouse config, and a
  deterministic synthetic national fixture** (P35.51 / row 329;
  R11-K13-UXK0-2; serves SIG-UI-041, SIG-FIND-005, SIG-UI-050,
  SIG-UI-036; cites ADR-155, K0 §4.3/§4.12, F-173, C4 DR-C4-13)
  — `web/tests/e2e/page-budgets.json` (`sig.page-budgets/1`) is now
  the single budget truth, carrying the K0 §4.3 ratified table
  verbatim per page type and superseding `island-budgets.json` in
  the same change. `budget.spec.ts` wire-measures every discovered
  route — gzip AND brotli, before and after one scripted interaction
  per surface (map pan, graph node-select, search keystroke, T1
  scroll) — and a run whose interaction produces no observable
  effect fails. `web/scripts/gen-lhci.mjs` renders
  `lighthouserc.json`, `lighthouserc.export.json` and the national
  twin `lighthouserc.national.json` from the registry + budget
  contract; `npm run check:lhci` fails on drift. The deterministic
  synthetic national fixture (`scripts/ci/build_national_fixture.py`,
  seed `20261022`) generates 232,500 sites / 5,200 agencies /
  405,000 sharing edges with invented names only — an executable
  real-name guard (F-173) fails the fixture on any real
  organisation/jurisdiction token — including a spec-valid PMTiles
  archive (leaf-directory v3 layout for the real-scale index) that
  the map measures at national zoom. `SIG_DATA_SOURCE=national` is a
  declared overlay (gitignored `web/national/`): the heavy artifacts
  come from the fixture, everything else stays on the committed
  corpus, and a missing artifact fails loud. CI gains the national
  leg (`scripts/ci/national_budget_leg.sh`; `make
  check-national-budgets` / `npm run check:perf:national` locally):
  fixture → national build → wire budget suite → national
  Lighthouse. Real overages are recorded honestly in
  `measured_gaps`: the ratified ceiling reports every run, a
  regression bound gates, and a gap row that outlives the bundle's
  drop under the ceiling fails as stale — the `/map/` ≈ 497 KB vs
  ≤ 360 KiB and `/search/` ≈ 72 KB vs ≤ 60 KiB bundles
  (D-P35.51-1/2) plus the national-scale document/total/first-view/
  latency overages (D-P35.51-3) are bounded records, never smoothed
  budgets.
- **Page-type registry + route discovery — every built route is
  classified T0/T1/T2/T3 or the build fails** (P35.50 / row 328;
  R11-K13-UXK0-1; owner SIG-UI-036/SIG-UI-037; cites ADR-155,
  SIG-UI-036, SIG-UI-037, SIG-UI-041, SIG-UI-050)
  — `web/src/lib/page-types.ts` is the single authority mapping route
  patterns to their ADR-155 page type (T0 record & print, T1 content,
  T2 explore, T3 tools) with the owner ticket, the data-contract id
  and the named no-JS equivalent each type requires. An
  `astro:build:done` hook walks `dist/**/*.html`, classifies every
  emitted route — zero matches or a double classification both fail
  the build — and emits `dist/page-types.json`
  (`sig.page-types-manifest/1`), the machine manifest the e2e suites
  now drive from. Generic sweeps (axe WCAG 2.2 AA, shell, chrome,
  script policy, no-JS parity) iterate the discovered routes instead
  of hand-maintained lists, so a new route joins every gate by
  classification and can never be dropped silently. The per-type
  script policy is enforced in `script-policy.spec.ts`: T0 ships no
  `<script>` at all; T1 admits only allow-listed `type="module"`
  entries (`t1-module-entries.json`, empty until UXK0-4 lands one)
  plus the recorded Astro bootstrap hashes; T2 admits the hashed
  bootstrap plus content-hashed `/_astro/` module assets; every type
  forbids `on*=` handler attributes and `javascript:` URLs, and an
  inline `application/ld+json` block is a violation on every type
  (JSON-LD stays linked files only, D-J3-7). `nojs-parity.spec.ts`
  enforces T1 `main`-text equality with JavaScript off minus
  `[data-enhancement]` subtrees, resolves each T2 route's named no-JS
  equivalents with JavaScript off, and requires the new
  `NoJsStateNotice` component to name the static equivalent on
  stateful `sig.workspace-state/1` URLs opened without JS — the
  machinery implements ADR-155, it never re-decides it.
- **Dedup publication fields — `site_id`, `copies[]`,
  `possible_duplicates[]`, `multi_view[]`,
  `n_independent_lineages`, and the SIG-CONF-005 count interval**
  (P35.47 / row 326; R11-K13-TX-11; owner SIG-CONF-005; cites GQ-10,
  SIG-CONF-005, ADR-105/ADR-153, D-K13-4 [B-26], L3 §4.5–4.6/§5.2/§9)
  — one shared `exports/dedup.py` view turns the latest completed
  camera-site ER run's ruleset-v3 links (P35.46's
  `read_resolved_site_runs` — read verbatim, never re-derived) into
  the fields every published record row carries: the shared
  `site_id`, the collapsed derivation copies nested under `copies[]`
  (source, upstream id, C0/C1/C2 basis — `same_as` for a
  review-decision member — never an excess row per copy), the
  inferential/unresolved links listed under `possible_duplicates[]`
  (record, distance, reason — "not merged", never a merge claim),
  same-layer co-located distinct records classed `multi_view` (never
  duplicates), and the site's declared independence-class count.
  Published counts are intervals (CONF-07b, this row): the record
  count beside `[lower, upper]` listed cameras rides the national
  resolved-sites coverage metric, the map layer's `count_interval`,
  every dossier's `rollup.count_interval` / `totals.count_interval`,
  and a `listed_cameras` figure registered on the web surface — all
  computed through the dep's `count_bounds`, never a second
  derivation. The measured dossier inflation against lineage roots
  publishes per dossier (`dossier_inflation_vs_lineage_roots`,
  ≤ 1.02× ratchet target; a miss is surfaced, never smoothed) and
  the GQ-10 file evaluator now scans the release's own accounting.
  Honest absence is first-class: no completed run → every field
  emits its `not_recorded`/`not_evaluable` object; `copies: []` is a
  measured fact, never an omitted field; `merged_into` is never
  written. Publication itself rides P35.63's HG-11 Class-S leg —
  this row performs no hosted mutation.
- **Dossiers at every level + the unplaced report — `sig.dossier/2`,
  `sig.dossier-index/2`, `sig.unplaced-report/1`** (P35.45 / row 324;
  R11-K13-JUR-03; owner — none (no §56 `Owner:` names P35.45); served
  SIG-UI-048 + SIG-UI-010…015 + SIG-UI-044; cites D-K4-3 [B-44,
  carried verbatim], D-K4-4, D-K4-7, K4 `placement@1`,
  SIG-ONTO-011, K4 NEW-4/NEW-6) — a new `exports/dossier_keys.py`
  canonical registry keys every dossier on the recorded
  `placement@1` chain (never re-derived): `group_by_key` rolls each
  record up its whole chain exactly once per ancestor, chainless
  records file only under `unplaced`, and the D-K4-3 thresholds mint
  country / admin-1 / US-county / US-place pages with the minting
  basis recorded (Puerto Rico + territories are US state-equivalents;
  a no-adapter country renders the conservative D-K4-7 profile;
  `jurisdictionCode` carries the country A2). One
  `web/dossiers/<slug-path>.json` per dossier replaces the monolith;
  `index.json` v2 enumerates the set and carries the dossier-build
  measurement; `web/jurisdiction_key_map.json` +
  append-only `web/jurisdiction_slug_history.json` resolve every old
  flat slug through static `moved`/`corrected`/`split` stubs
  (301-style JSON documents for single successors, 300-style choice
  lists for splits — a previously-published dossier URL never 404s).
  `web/unplaced.json` + `/dossier/unplaced/` (`/dossier/unplaced.json`
  twin) publish the honest "Not yet placed" data-quality report — the
  verbatim header, closed-vocabulary by-reason rows with "what would
  fix it", per-source top reasons, correction links, exclusion
  disclosures, and honest `not_emitted` download slots — a sibling of
  every dossier, never a jurisdiction (excluded from counts, "N
  jurisdictions" copy, and the place facet). Research-queue gap cards
  re-key to `jurisdiction:<jkey>` only where the key-map is
  unambiguous; `web/dbright_rereview.json` lists US-located records
  published under the non-US database-right basis for E4 (a list, not
  a rights change). The release tree groups record lists under
  `jurisdiction/<slug-path>/` with `unplaced/` replacing the legacy
  `unresolved/`; dossier routes move to canonical catch-all paths with
  ancestor breadcrumbs and child roll-ups.
- **Dossier contribution export — `sig.dossier-sources/1` + the source-side
  `contributions[]` mirror** (P35.44 / row 323; R11-K13-DSRC-01; owner
  SIG-TRANSP-008 + SIG-TRANSP-040; cites SIG-UI-044/048, SIG-ENG-021,
  K4 `placement@1`, K5 §3.1–3.4, J3 T-2, D-K5-4) — a new
  `sig_export`-granted `v_claim_sightings` view (explicit columns only:
  claim identity/gate columns beside the sighting's capture, binding
  status, run, and retrieval instant — never a locator, excerpt, digest,
  or OCFL id) feeds the K5 §3.1 `claim_sightings` aggregate under the
  shared publishable-claim, effective-rights, artifact, and capture-seal
  gates. One accumulation turns that stream into the dossier-side
  `web/dossier_sources/<slug>.json` artifacts — release + jurisdiction
  blocks, named definitions, totals, the SIG-UI-044
  `provenance_summary` (`human_review_status: "unreviewed"`), figures
  with `by_source` reconciliation and a disclosed `sum_rule`,
  per-source contribution rows with first/last seen, run attribution,
  series, and `latest ok run`/`not_reasserted` fields, plus
  country/admin-1 `.runs.jsonl.gz` per-(source, run) logs — and the
  identical numbers appear as `contributions[]` on
  `transparency/sources.json` rows (TRANSP-040: never a second
  computation; gated rows carry `[]`). The §3.3 `run_level_only`
  fallback names `last_seen: not_recorded` and
  `not_reasserted: not_evaluable` wherever a source's claims carry
  exactly one establishing link across more than one completed run, and
  `cross_source.colocated_pairs` stays `not_evaluable` until DSRC-04
  publishes `observation_group`.
- **Figure → evidence pointers** (P35.37 / row 316; R11-K13-TX-09;
  owner SIG-TRANSP-013; cites SIG-UI-035/044, J3 §5.4 + §12 TX-09,
  K13 §7 W1 / UXR-34 [design ref], DR-C3-01/DR-C3-03, PKG-10, F-102)
  — every material number on the public surface now renders through
  the one `<Figure>` contract: `data-artifact` + `data-pointer`
  name a manifest-listed release artifact and the JSON pointer into
  it, a visible "definition"/"source" link line sits beside each
  value, and the J3 §5.4 per-class targets resolve to real routes
  or render a named absence — never a dead link. `check-figures`
  is a new rendered-output gate in `npm run check`: a figure whose
  artifact is not manifest-listed, whose pointer is malformed,
  whose id collides, or a material numeral left bare inside a
  named page class (home, dossier, coverage, freshness, sources,
  data, status) fails the build; incidental citations are recorded
  exemptions only. The static `/artifact/<export-path>.json` route
  serves each figure's downloadable/recomputable evidence file
  (fail-closed to release-known paths), and two new manifest-listed
  export artifacts ship — `web/sources.json` (the
  `sig.source-licence-table/1` table `/sources/` renders) and
  `web/evaluation.json` (the DR-C3-03 `sig.resolution-eval/1`
  record — evaluation metrics now come from release bytes, never
  hard-coded constants).
- **Per-claim statements files, `upstream_href`, and the one shared
  provenance panel** (P35.36 / row 315; R11-K13-TX-08a; owner
  SIG-TRANSP-011; cites SIG-TRANSP-012/022/025, SIG-UI-028/035,
  J3 §5.1–5.3 + §12 TX-08a, K13 §7 W1 / UXR-33 [design ref], J1 §B.4
  + NEW-10, C4 NEW-2, SIG-EXPORT-001/006, SIG-REL-008) — the
  built-but-unpublished `record_claims` stream now ships as a
  per-compartment `sig.statement/1` `statements.jsonl` through the
  existing licence/compartment/manifest path (ODbL claims never in a
  CC-BY file; manifest entries carry schema + row count + distinct
  entities), and the immutable release copies each compartment's
  statements file into `r/<pub>/c/<comp>/` with `_claim_index`
  preferring statements and falling back to `record_claims` for
  pre-P35.36 exports. Every row carries the claim anchor, the closed
  `not_published` value token (raw claim literals never emit), the
  `claim_evidence` binding state — J3 §5.1's four states, with
  `not_recorded` as the honest fifth when no publishable binding
  exists — scrubbed capture locators, the S-6-gated upstream block
  (`full_url` only for `raw-ok`/`derived-only` lanes past the gate;
  `host_only` + path hash otherwise; `no_upstream_url_recorded` /
  `withheld_by_policy` where honest; a raw URL is never copied
  through), the §5.3 `view_original` label states (TX-08b mints the
  byte routes — this row never mints a raw-byte link), extraction,
  epistemics, recorded run/at, supersession, contradictions, and
  per-claim rights. `published_record.py` fills
  `source_refs[].upstream_href`/`upstream_host`/`upstream_status`
  from the statement's gated upstream object (J1 NEW-10's hard-coded
  `None` is gone) and embeds the rows as `claim_statements` —
  `PROJECTION_VERSION` is `sig.published-record/4`. One
  `sig.provenance-panel/1` contract + `<ProvenancePanel>` component
  now renders the J3 §5.1 wording verbatim — the `legacy_synthetic`
  run-level sentence never implies a per-record copy — on the
  release record pages (`#claim-<id>` anchors resolve to the panel
  itself), the claim viewer, the network edge rows + island, and
  the map selection pane; every field is a value or a named absence
  (`not_recorded` / `no_upstream_url_recorded` / `not_publishable` /
  `unavailable`), every new internal link routes through
  `withBase()` (containment baseline unchanged), byte counts group
  by locale (K14 NEW-8), and repeated inline panels dedupe to a
  shared anchored panel so the island/page budgets hold. The web
  data layer gains a statements seam (`getStatementIndex`) —
  committed fixtures under `SIG_DATA_SOURCE=fixtures`, real per-
  compartment `statements.jsonl` bytes under `export`, honest
  absence never fixture fallback.
- **Registry redistribution lanes and the source-metadata export —
  `v_transparency_source` + `sources.json`/`counts.json`** (P35.35 /
  row 313; J3 §3.1 + §3.3 item 3 + J4 §9, K9 §10 C-6, spec §5.7's
  verbatim wording per ADR-183, D-J3-1 [B-19] recorded; also
  SIG-TRANSP-002 routed to owner P35.40 and SIG-TRANSP-035 to
  P37.36) — every registered source now carries a recorded
  `[sources.<id>.redistribution]` declaration (`lane`,
  `evidence`, `evidence_uri`, `decision_authority`,
  `review_needed`, `part_viii_class`, `packet_limited`,
  `sig_labelled_cc0`) parsed from `sources.toml` with fail-closed
  validation: unknown keys, invented lanes or Part VIII classes, a
  positive lane without evidence + authority, and dangling fields
  all refuse; an absent block reads as honest undeclared
  (`lane == ""`), distinct from a recorded `unknown`. A new
  append-only `source_redistribution` mirror (closed-vocabulary
  CHECKs, immutability trigger, `ON CONFLICT DO NOTHING` writes)
  plus `source_redistribution_current` carry the declaration into
  the spine, and the new explicit-column `v_transparency_source`
  (`sig_export` only) joins registry ⋈ rights ⋈ latest decision ⋈
  current lane ⋈ last-seen freshness — sensitive registry/rights/
  Part VIII fields structurally absent. The capture writer derives
  `storage_tier` from `derive_storage_tier(lane, part_viii_class)`
  — a lane-evidenced `raw-ok` + P8-clear source reaches `public`
  (`D-P35.31-1` closed; everything unevidenced stays `sealed`,
  never a default), and the read path serves the more restrictive
  of recorded and derived (`derived_at_read` labels tightening,
  never an upgrade). The release tree gains `transparency/
  sources.json` (`sig.transparency-sources/1`) and
  `transparency/counts.json` (`sig.source-counts/1`): the
  lifecycle partition, the K9 C-6 `last_upstream_change`/
  `last_sig_records_change` pair, gated rows on the closed reason
  vocabulary, `no_upstream_url_recorded` where honest, restricted/
  link-only surfaces as host + `path_sha256`, counts recomputable
  from the emitted rows, byte-stable on re-export.

- **Transparency run, capture and issue export — the scrubbed
  execution-history release artifacts** (P35.33 / row 311; J3 §3.1 +
  §3.3 items 1–2, K9 §10 C-4…C-7, K10 §18 C-13, SIG-ENG-021; also
  SIG-TRANSP-006 routed to owner P36.46; B-19's recorded robots-
  disregard shape with the GL-GATE-08 reference) — two new
  `sig_export`-only views publish the restricted tables as explicit
  columns: `v_transparency_run` (one row per execution;
  `ingest_run_report ⋈ ingest_run ⋈ ingest_run_completion`) and
  `v_transparency_capture` (one row per capture mark;
  `ingest_run_capture ⋈ evidence_capture ⋈ evidence_blob ⋈
  evidence_artifact` — classification + storage tier + retained
  status, the mark binding its capture row at most once). Every
  column is named in `policy.transparency`'s allow-lists and passes
  the S-1…S-14 scrub at emission; never-exported fields
  (`parameters`, `environment`, `detail`, `run_record_uri`,
  `request_fingerprint`, quarantine `payload`) are absent. The
  execution-keyed rule (K10 C-13) is enforced in-engine: where a
  shared `ingest_run` serves more than one recorded execution, the
  run-owned values (code identity, connector identity, completion
  counts and clock) emit NULL — the export renders
  `not_recorded (shared run)`, never a borrowed value. The release
  tree gains four `transparency/` artifacts through the existing
  licence/compartment/manifest path: `runs.jsonl`
  (`sig.run-record/1`), `captures.jsonl` (`sig.capture-record/1` —
  a sealed-tier capture emits `target: "sealed"`, no locator),
  `issues.jsonl` (`sig.source-issue/1` — the auto-detected J3 §7.3
  classes as append-only `(source, class, opened_at)` instances with
  `closed_at`/`count`/`basis`), and `freshness.jsonl`
  (`sig.source-freshness/1` — the shared `policy.freshness` module's
  declared-cadence *rule* — never a "next run" stamp — the C-7 state
  vocabulary with `one_time_load`/`run_record_missing`, the two
  last-change columns, volatility over the predicate registry with
  `staleness` typed `not_evaluable`, every value pinned to the
  release `evaluated_at`). Robots outcomes disclose host + outcome +
  count — `disregarded` rows adding the `GL-GATE-08` decision
  reference — never per-request detail; quarantine surfaces as
  counts-by-reason only.
- **One transparency scrub, a fail-closed publish secret gate, and honest
  capture storage tiers** (P35.31 / row 309; owner SIG-TRANSP-022, also
  SIG-TRANSP-020; owns F-400 / J3 §3.3 NEW-2; cites D-J3-1, J3 T-6,
  SIG-EVID-009/010, SIG-API-012, P34.25, P32.2) — `policy.transparency`
  is the single scrub module every transparency surface consumes (a
  second scrub implementation is a defect): the J4 S-1…S-14 rules as
  code (credential query-param/header stripping, internal-location
  opaque ids, explicit-column emission with the J3 §3.5 never-exported
  list refusing at the emit layer, the closed error-class vocabulary,
  IP drop, the S-6 URL gate — host always, full URL only for
  `raw-ok`/`derived-only` lanes past the gate, no personal data, no
  record free text, withdrawal tombstones, full ISO-8601 UTC
  timestamps, gated-source registry-only rows, per-host robots
  disclosure with the decision reference, the five-name header
  allowlist), the closed lane/tier/Part VIII vocabularies, and
  `find_secrets` — the one shared secret-shaped detector
  (`ops.publish.assert_publish_set_secret_free` runs it over EVERY
  file in the publish set — site tree, staged release tree, public
  export tree — before the release record or any remote sync; one hit
  aborts in dry-run AND `--apply`, names file + pattern class never
  the value, no override flag). The actual-capture writer's constant
  `storage_tier='public'` is gone: `PgClaimSink` now derives the
  recorded tier from the source's redistribution lane + Part VIII
  class via `interim_lane`/`derive_storage_tier` — `raw-ok`+P8-clear →
  `public`, `derived-only`/`link-only` → `restricted`, `restricted`
  lane or P8-1/P8-2/P8-4 or any unknown → `sealed` — wired from the
  registry's rights record (`connectors.sinks._registry_lane`, the
  interim basis until row 313's `[redistribution]` fields land —
  `D-P35.31-1`). `/v1/evidence` reads the recorded tier floored by the
  lane at read time (`served_storage_tier` — tighten-only, a pre-fix
  constant-`public` row is served tightened and labelled
  `tier_basis='derived_at_read'` + `recorded_tier`, never a silent
  upgrade); `source_uri` publishes only for the `public` tier, and
  `retrieved_at` is a full ISO-8601 UTC timestamp, never date-only.
- **Shared entity labels, slugs and hashes — the `sig.entity-label/1`
  registry** (P35.29 / row 307; R11-K13-GX-01; cites A-10 (the operator's
  recorded answer, `b + c`), ADR-159, SIG-PUB-008, K2 §3 L-1…L-7,
  SIG-UI-D20–D25, SIG-IDENT-031/032, UXR-17 draft; ADR-215) — one
  derivation everywhere. `policy.labels` is the leaf-package module:
  `LabelFacts` in, `EntityLabel` out — label, descriptor, `label_basis`
  (closed `source_name|source_title|key_name|slug_name|derived|fallback`
  vocabulary), slug, Crockford-base32 hash, canonical
  `/entity/<type>/<name-slug>--<hash>/` URL, and the Part VIII `part8`
  verdict. The person-name screen is injected at every call site
  (`resolution.partner_identity.natural_person_signal`) and runs over
  every label input including literal procurement parties. The export now
  emits `labels/<compartment>.jsonl` — one derivation per publishable
  entity, filed under the compartment its label-input claims license to.
  Every consumer reads the registry/module instead of re-deriving: site
  rows, map assets, network nodes, dossier jurisdiction attribution,
  published-record label basis, release pages, and the API label path —
  the cached-canonical-name/connector-key/`Unnamed <type>` fallbacks are
  retired for typed `#{hash4}` fallbacks, never identifiers. A-10 renders
  as: registry-allowed organisations labelled; every other organisation a
  typed `label_state: "not_yet_reviewed"` row (null label/slug/hash — the
  state visible, the label not); withheld and person entities emit no row
  at all. Deterministic disambiguation (`· {place}` → `· {source}` →
  `#{hash4}`) runs over the emitted set so no two public entities of a
  kind share a full display label.
- **Honest network edges — dates, evidence, literal partners, degree**
  (P35.30 / row 308; R11-K13-GX-02; cites A-10 (`b + c`), ADR-159/215,
  K2 §7 H-1…H-4, SIG-EXPORT-D21 draft, SIG-INGEST-043c,
  SIG-TIME-012-class honesty, SIG-IDENT-030; ADR-216) — `network.json`
  edges now carry their evidence, named: `predicate`/`relation` in words
  (never a raw slot name), `observed_at` + `date_kind` (the epoch-zero
  placeholder folds to `undated`, never a synthetic 1970-01-01),
  `valid_from_kind`/`valid_to_kind`/`valid_to`, `source`/`sources` as
  display names, a snapshot-as-of-pinned `currency` class (plus `UNDATED`
  for an unweightable edge), `historical`, `support` derived from the
  backing claims' declared independence classes (`unclassified` never
  corroborates — the `WEAKLY_SUPPORTED`/`evidence_count: 1` constants are
  gone), and the full `claim_ids`/`evidence` set. The materialized and
  compute-on-read paths share one emitter; publishable claims awaiting a
  materialized row still emit. Literal partner names join the edge set
  only past the Part VIII person screen (a person-shaped literal
  withholds the edge whole); `sharing_partner_degree` claims become node
  `degree` attributes with their own claim provenance, never drawable
  edges — rendered in the static "Recorded partner counts" list. Ended
  and undated edges are visibly marked, faded in the diagram, and out of
  the default "current" view. No new JavaScript; the richer JSON rides
  the existing island at its ceiling.
- **Resolver input truth — valid time, declared directness, and
  tolerance-aware dissent** (P35.27 / row 306; R11-L3-CP9 + CONF-05;
  owns F-519; cites SIG-RECON-053, SIG-STORE-015, SIG-EPIS-017/018,
  SIG-RECON-006 Phase 1.2, SIG-RECON-014, SIG-RECON-020) — the resolver's
  inputs are now truthful on every read path. `Claim` carries the declared
  `valid_period` bounds (Phase 1.2's overlap test was vacuous on the
  materializer path — it never read them) and the connector-DECLARED
  directness, distinguished from the `connector_default_D2` sink default
  via `claim.assertion_map_basis`; the effective directness is the weaker
  of declaration and the (genre × predicate) matrix — a declaration may
  weaken (a `D6` non-probative stamp is honoured) but never strengthen.
  Within-tolerance pooled disagreement is disclosed as the `contested`
  dissent signal — `contested_claim_ids` recorded, joined into
  `dissenting_claim_ids`, `MINOR_DISAGREEMENT` agreement — never silently
  absorbed (F-519: 0 dissent in 19,121 sampled resolutions) and never a
  contradiction: the four-state `contradiction_state` vocabulary is
  unchanged (SIG-STORE-015). `input_digest` covers the new inputs so a
  re-perioded or re-graded claim mints a superseding decision
  append-only. `materialize.read_claim_groups` and both
  `api.store_pg` readers supply the same truthful inputs;
  `reconcile rematerialize-report` is the read-only before/after
  state-distribution dry-run naming every delta class
  (`temporal-deconflicted`, `directness-reweighted`,
  `tolerance-de-escalated`, …). `RESOLVER_VERSION` → `p08.1/1.2.0`,
  ruleset → `2026.3` (+`RESOLVED_CONTENDED_TOLERANCE`), the L3 rebuild
  sample is repinned. The production rematerialize + `/status/`
  API-basis notice are QUEUED OM-20 legs — none ran
  (`live_verification=false`).
- **Role edges, honest time, and recorded supersession** (P35.26 / row
  305; R11-L3-CP7 + CONF-06; owns F-521; cites SIG-TRUST-003,
  SIG-ONTO-028, SIG-ONTO-029/030/032, SIG-EPIS-029, GQ-07/GQ-15;
  ADR-214) — the who-does-what edge surface is now truthful in role and
  time. Sqitch `role_edges` reshapes the never-written `entity_role`
  sketch: surrogate `entity_role_id` PK (the `operator_unknown` marker's
  NULL actor cannot live in a natural key), the claim/relationship
  temporal columns (`valid_period` + closed kind vocabulary extended
  with `undated`, `observed_at`, `asserted_by`, `sys_period`), the
  succession chain (`supersedes` + `superseded_by_claim`), the closed
  role CHECK (`db.organization_roles.EDGE_ROLE_VOCABULARY`), and
  epoch-zero NOT VALID CHECKs — `1970-01-01` is rejected at write on
  both edge tables. `relationship` gains `supersedes` + the same guards;
  `close_superseded_entity_roles`/`close_superseded_relationships` are
  the SECURITY DEFINER sanctioned temporal mutations (INSERT-only
  posture kept). `reconcile.materialize.materialize_role_edges` builds
  the per-(subject, slot) succession model — within-lineage state
  changes close the prior episode's bound at the later claim's evidenced
  date, explicit `revises_claim`/`retraction_of` corrections close the
  revised state, cross-lineage disagreement stays concurrent, open
  same-state episodes merge into one corroborated edge — all append-only
  and +0 on re-run; `operator_state` distinguishes
  `operator`/`operator_unknown`/`not_asserted`; the CLI verb
  `materialize-role-edges` defaults to dry-run. The emitters separate
  provenance from operation: OSM stamps element `timestamp` as
  `observed_at`, emits `operator_absent` absence claims and a
  `published_by` provenance claim per element; the EFF Data Driven
  release stamps its covered valid window (2016–2017) on every claim and
  emits `published_by` for the release publisher — a publisher can never
  mint an operator edge. `vocab_published_by` registers the predicate
  (GLACIAL 10y, max_support) + its directness row. The sharing-edge
  materializer drops the 1970 fallback: undated edges are
  `undated`/unbounded, and a changed evidence set supersedes the live
  row through the same recorded-succession machinery. The hosted EFF/OSM
  re-ingest and edge rematerialize are QUEUED OM-20 legs — none ran
  (`live_verification=false`).
- **Declared lineage, identifier namespaces, and independence classes**
  (P35.25 / row 304; R11-L3-CP4, owner SIG-CONF-014; cites SIG-EPIS-009/029,
  SIG-IDENT-005, CONF-04, S6 A-20, GQ-11; ADR-213) — `sources.toml` rows
  declare `kind`/`origin`/`mirror_of`/`derived_from`/`independence_class`/
  `id_namespace` (additive, fail-closed validation; `undeclared` never
  reads as independent; `assert_loadable` unchanged). Sqitch
  `declared_lineage` lands immutable `source_lineage` (versioned registry
  mirror) + `claim_lineage` (one row per claim — `id_namespace`,
  `lineage_kind`, `independence_class`, `basis`, persisted
  `derived_from_claim_ids`; explicit `undeclared`/`unclassified` tokens)
  + the `source_lineage_current` view; the committed namespace vocabulary
  `sig.id-namespaces/1` bounds declared tokens and a non-vocabulary
  override quarantines `unknown_id_namespace`. The sink writes each
  claim's lineage in the claim transaction. Identifier equality becomes
  `(id_namespace, value)` — the camera-site tier-1g shared-ref join fires
  only inside a declared shared namespace; reconcile counts corroboration
  across declared-independent classes only (a mirror is one disclosed
  voice); export envelopes disclose `n_independence_classes` +
  `n_unclassified_candidates`. `sig-db lineage-rematerialize` mirrors the
  declarations and back-populates `claim_lineage` — dry-run default,
  bounded/keyset/resumable/+0, INSERT-only, ancestry recovered only where
  evidence supports it. The API basis middleware carries opt-in notices
  (`SIG_API_BASIS_NOTICES` → `basis.notices`) and the `/status/` sentence
  stages in copy batch 02 (`ST-11`, pending operator confirmation).
  Hosted merge/rematerialize/notice/verification legs are QUEUED
  OM-19/OM-20 — none ran (`live_verification=false`).
- **Pinned subject keys + append-only re-key machinery** (P35.24 / row
  303; R11-L3-CP2, CONF-03b; owns F-506 + F-518, metric L2-M07, GQ-04;
  cites SIG-INGEST-003/004, SIG-IDENT-005/006; ADR-212) — the committed
  pin registry `db/src/db/data/subject_key_pins.toml`
  (`sig.subject-key-pins/1`) declares, per subject family, the ordered
  fields a key composes from, the tenant/state scope rendering, the
  `key_version`, the distinguish selectors the collision scan re-derives
  and the split shape collided keys re-key under. Emitters mint through
  `db.subject_keys.mint_subject_key` (`atlas:` + `data_driven:agency:`
  gain `us.state_abbr:<state>`, `contract:` gains `tenant:<tenant_id>`,
  camera keys keep the `traffic_camera:` anchor); the sink validates
  every pinned-family value against the grammar (drift quarantines) and
  `dot_511` enforces per-capture key uniqueness — two rows minting one
  key aborts the target run closed (GQ-04's I-placement). The
  append-only `sig-db subject-rekey` run (plan by default, `--apply`
  writes) re-derives collided keys from the live spine, closes each
  moved claim (`sys_period` end) and appends it under an
  evidence-derived constituent subject with `revises_claim` +
  `correction_reason` + `subject_rekey_decision` — INSERT-only, +0 on
  rerun, unplaced claims reported never guessed. New sqitch change
  `subject_rekey`: `subject_key_pin` (registry mirror) +
  `subject_rekey_decision` (immutable decision log) +
  `claim_evidence(claim_id)` index. The hosted re-key run, the `/status/`
  API-basis notice (S6 A-20) and the post-run zero-collision
  verification are queued live legs under OM-19/OM-20 — never executed
  in the `live_verification=false` invocation.

- **Export-time jurisdiction placement — `placement@1`** (P35.19 / row
  299; JUR-02b, K4 §3.3/§3.4/§5.3, ADR-092 compute-on-read; cites
  SIG-JUR-D03/D04/D05, SIG-IDENT-004, SIG-GEO-008) — a new
  `exports/placement.py` evaluates the versioned R1–R8 ruleset over the
  verified boundary pack + bound jurisdiction registry staged as export
  inputs (`sig-exports build --from-spine --boundary-pack <dir>
  --jurisdiction-registry <file>`): the located point wins (R4), suspected
  axis swaps / sign flips / rejected points fall back to the declared
  level with the point withheld from maps and sub-counts (R3/R5), a
  shared-boundary point resolves by lowest GEOID/code with check
  `on_boundary`, and a record with no place is a reported quality state
  under the closed `placement_check` vocabulary — never a jurisdiction.
  Site rows gain the seven additive columns `jurisdiction_key`,
  `jurisdiction_chain`, `placement_basis`, `placement_check`,
  `declared_scheme`, `declared_value`, `boundary_vintage` (the existing
  `jurisdiction` column is unchanged — the declared bucket, back-compat);
  the published-record projection bumps to `sig.published-record/3` with
  the record `jurisdiction` block `{id, jkey, chain[], basis, check,
  declared, boundary_vintage}`; a `sig.placement-report/1` artifact lands
  at `web/placement.json` carrying per-source reason counts (records ==
  Σ reasons, conservation-checked) and the located-vs-declared
  disclosure pairs. Nothing is written back to the spine — placement is
  computed on read inside the export's read-only snapshot, DuckDB
  `spatial` is bundled into the export image (strict `LOAD`, never a
  runtime `INSTALL`), and an unverified pack or a registry whose
  `boundaries_root`/vintages diverge from the pack refuses the export
  outright. With no pack staged the export is byte-identical to the
  pre-placement posture.

- **Declared jurisdiction scheme end-to-end** (P35.18 / row 298;
  JUR-02a, K4 §3.2; cites SIG-JUR-D02, SIG-IDENT-005/006,
  SIG-ONTO-011, SIG-EVID) — the `(scheme, value)` pair a connector
  already emits as `candidate_identifier` now persists into
  `claim.value_json` (additive; the claim's text value and content
  digest are unchanged; a malformed or conflicting pair fails closed
  into `assertion_quarantine`). Shaped jurisdiction buckets key on the
  declared pair resolved through the K4 §3.2 map — canonical keys like
  `iso3166-2:US-OK`, never a bare code — and each observation carries
  `scheme` + `scheme_basis` provenance: `candidate_identifier` for a
  claim-carried pair, `declared_scheme_from_config@<sha256>` for a
  legacy claim whose scheme derives from the committed connector
  config (the file sha names exactly what declared it). A jurisdiction
  bucket can never mix a scheme-keyed claim with an undeclared bare
  value — the build fails closed. `SHAPING_SCHEMA_VERSION` →
  `p35.18/1.2.0`. No backfill and no ingest run — the hosted effect
  rides the next ingest under its own authority.

- **Jurisdiction registry, GeoParquet boundary pack, and `lookup@1`**
  (P35.17 / row 297; K4 §3.1/§3.2/§4.2/§5.4; cites SIG-JUR-D01,
  SIG-IDENT-005/006, SIG-GEO-008, SIG-INGEST-028, ADR-160; revisits
  ADR-079/ADR-122) — jurisdictions are keyed on canonical scheme-named
  keys (`iso3166-1:*`, `iso3166-2:*`, `us.census.geoid.county|place:*`,
  `national:<scheme>:*`), never bare labels: the `ID`/`MN`/`DE`
  abbreviations collide with Indonesia/Mongolia/Germany and are
  disambiguated by scheme and `within`/`level` filters. `sig-exports
  boundaries` builds the declared `sig.boundary-pack/1` layer set
  (TIGER/Line + Gazetteer + Natural Earth + the 500k display set) into
  GeoParquet behind the fail-closed ingestion gate — the build refuses
  while `census_gazetteer_tiger`/`natural_earth_10m` remain
  un-flipped (HG-03 is the operator's act) and fixture builds record
  `gate.mode = "fixture-bypass"` in the manifest. The derived
  `sig.jurisdiction-registry/1` (CC-BY-4.0 SIG metadata, upstreams
  attributed) carries parents, identifiers, vintages, bboxes, internal
  points, the D-K4-2 disputed-territory posture (ISO as published; XK
  `code_status = "user-assigned"`; one standing note) and the D-K4-4
  territory-under-US keying (ISO 3166-1 codes as alias identifiers).
  Descriptor v2's `boundaries_root` now derives from the staged
  verified pack (`<export>/inputs/boundary-pack/`), failing closed on
  tamper or contradiction. The hosted OCFL boundary-source capture is
  queued behind the HG-03 flips — never exercised in this
  `live_verification=false` run (re-run prompt in RETURN PASS).

- **Geometry-defect detection at ingest and export row/entity
  disclosure** (P35.16 / row 296, catalog `R11-DATA-01`; owned finding
  **F-322 (S1)**; cites SIG-GEO-008, SIG-IDENT-004, SIG-ONTO-011,
  SIG-INGEST-033, ADR-092/113/210) — every camera-registry target now
  declares its positional `axis_order` (`lon-lat`/`lat-lon`; `lat-lon`
  on the F-322 Nottingham/mark43 transposed-serve targets) and a
  resolvable detector bound (`extent` or a `jurisdiction_extents.toml`
  row). Ingest runs four closed-class detectors — `null_island`,
  `axis_swap`, `sign_flip`, `wrong_jurisdiction` — on the publisher's
  raw pair before the parcel screen; a defect-marked record emits a
  `geometry_defect` marking claim (registered predicate, insert-only
  `vocab_geometry_defect` sqitch change) and asserts NO device-point
  coordinate claims. Corrections land append-only through
  `sig-connectors geometry-corrections` (dry-run default, `--apply`
  writes via `PgClaimSink`; `revises_claim` + `correction_reason` +
  `derived_from_claim_ids`), scoped by the committed
  `sig.geometry-corrections/1` artifact. Export manifests now carry
  `distinct_entities` beside `row_count` on entity-bearing tables —
  observation-level rows vs distinct subjects disclosed, never an
  inflated census. The hosted correction write is staged, not applied
  (`live_verification=false`; re-runs under the ticket's OM-19 prompt).

- **Release provenance stamp, `release.json` and `X-SIG-*` headers**
  (P35.13 / row 295; **SIG-REL-009** owner; cites SIG-REL-001/002/003,
  SIG-MEM-011, SIG-SEC-008, SIG-REL-010; G3 §6) — every release surface
  now names the release it answers for. `exports/site_release.py`
  emits `sig.site-release/1` — the descriptor-rendered release identity
  (`label`, `publication_id`, the as-of pair, `built_at`, `code`,
  `versions`, `evaluation`, `disclosures`, `routes_sha256`, the
  integrity-manifest pointer) — at `releases/<pub>/release.json` and the
  site-root `/release.json` the stamped pages' `describedby` resolves
  to; `validate_release` cross-checks it field-by-field and refuses a
  `release.json` on a non-v2 release. HTML pages gain
  `<meta name="sig-release">`, `<link rel="describedby">` and the §6.1
  stamp — "fixed copy" wording inside `r/<pub>/`/`releases/<pub>/`,
  "latest view, cite the fixed copy" on mutable overlay pages (releases
  index, entity stubs, tombstones) — with zero client JS. Published
  records and dossier JSON twins carry `release`/`licence` blocks;
  `/` and `/health` name `release`/`code_commit`/`image`; every sig-api
  response carries `X-SIG-Code <commit12>` + `X-SIG-Conf-Gen <n>` and
  every sig-web response carries `X-SIG-Release "<label> <pub>"` +
  `X-SIG-Conf-Gen` (generated `release_headers.conf`, `always` —
  errors and tombstones included). The stamp never prints a posture the
  descriptor does not evidence (interim-text rule, tested at three
  layers). Committed machinery only — the stamp activates on the next
  republish under that row's own authority; the `v/<pub>/`/`s/<pub>/`
  copies ride the publish/J3 legs.

- **Flock transparency-portal probe connector** (P36.74 / row 289;
  WV-10 under ADR-188; D3-Q3 = b under ADR-184; cites SIG-INGEST-013,
  SIG-INGEST-035's surviving aggregator/compartment clauses,
  SIG-PUB-002/003a, ADR-185, SIG-ENG-042, SIG-OPS-011) —
  `connectors/flock_portal_probe.py` lands the probe-only leg the waiver
  opened: one gentle GET per known portal per run through the shared
  politeness layer, stopping on any challenge/403/interstitial, with the
  served page parsed against the mirror's own aggregate-only vocabulary,
  Part VIII-screened **in memory before persistence**, terms captured
  verbatim, and output stamped CC BY-SA 4.0 `portal` compartment
  (`ai_training_permitted=false`). The persisted artifact is the screened
  `sig.flock-portal-page/1` extraction — the vendor's raw page bytes are
  never stored. The probe set is committed data: 917 known portals
  derived from the Eyes on Flock inventory snapshot (recorded date +
  sha256 + selection rule; no discovery). Every run emits exactly one
  `sig.probe-run/1` record of per-portal served/refused outcomes;
  expected yield ≈ 0 is a PASS. The `flock_transparency_portals` row
  moved custody `LINK`→`DERIVE` with the WV-10/D3-Q3 basis recorded
  verbatim and stays `ingestion_permitted=false` — activation is the
  operator's P36.12 Wave-B execution under ING-GO-B, never a code change.
  `evidence.screen` gains the shared TOML→`ScreenDeclaration` parser
  (`ops.at_rest_audit` now delegates to it) and the framework gains the
  `SchemaRefusal`/`ScreenedRefusal` recorded-disposal classes.

- **Residential-parcel demotion wired end to end** (P35.66 / row 288;
  **SIG-PUB-004 / SIG-PUB-005 / SIG-PUB-013** owners; cites SIG-PUB-011,
  SIG-PUB-012, SIG-PUB-006, §23.10) — the residential-parcel screen that
  existed as dead code now has all three bind points live. **Flag
  producer:** `policy/parcel_screen.py` + the committed declared signal
  `policy/data/residential_parcels.toml` stamp every emitted
  candidate/asset row with a three-valued `parcel_screen` verdict
  (`intersects` / `clear` / `unscreened`), `residential_parcel_flag`,
  and the signal identity `<id>@<version>` — an unscreened geography is
  a recorded coverage gap, never a silent "clean" (the committed signal
  honestly declares zero coverage until the parcel acquisition lands).
  **Demotion:** `demote_for_residential_parcel` now runs at every
  `sensitivity_class` stamping site — `dot_511` (a parcel-intersecting
  point demotes to C3 with coordinates withheld before any claim is
  emitted), `osm` (the ODbL `physical_asset_rows` projection withholds
  flagged geometry while program facts survive), `okc_claim` /
  `dossier_claim` — automatic, no override path. **Publication
  refusal:** `CandidateAssetPublishRefused` /
  `assert_public_layer_subject` make a `candidate_asset` or
  parcel-flagged subject reaching a public device layer a **build
  error** at every surface — shaping (excluded by construction and
  honestly counted, plus a post-shape guard), the spine-export slices,
  published records, the release search index (refused before the
  index file is opened), tiles (refused on the full feature before
  slimming), and research dossier packets (fail closed). No
  residential candidate reaches a public surface at any precision,
  ever.

- **Redaction pipeline, wired end to end** (P36.15 / R11-SAFE-04;
  **SIG-PUB-015 / SIG-PUB-016** owners; cites SIG-EVID-011, SIG-EPIS-006,
  SIG-PUB-014a, SIG-GOV-007) — a redaction now has a real production path:
  `sig-connectors redact-propose` records a digest-bound `redaction`
  `review_item` on the curation-owned mechanism (scope = offsets + sha256 of
  the removed text, never the text itself); a recorded human `accept`
  (reviewer *role*, never a personal name, Part VIII §0.7) is **required**
  before `redact-apply` writes the derivative as a NEW OCFL object carrying
  the `sig.redaction-review/1` applied record — the parent's bytes are
  write-once and never touched (SIG-EPIS-006). `evidence.redaction` gains the
  span/substitution + extraction-proof layer (`apply_redaction` refuses a
  missing or mismatched review and self-checks that removed text is absent
  from the derivative's bytes and text layer); `evidence.tiers` gains
  `publishable_excerpt` so `public_representation`, the API evidence
  representation, and `exports.dossier.DocumentRef.for_capture` serve the
  derivative's excerpt — never the parent's raw excerpt — wherever a
  derivative row exists (`PgReadStore` resolves the newest
  `parent_capture_id`-linked row). Binary containers (PDF/PNG/WACZ) are
  refused — no fake overlay "redaction".

- **Officer-naming gate on the publication path, default deny** (P35.28
  / R11-SAFE-03; **SIG-PUB-007** owner; cites SIG-PUB-008/009/010/017,
  ADR-163, ADR-209) — the §43.4 five-prong + two-reviewer test now binds
  the publication path, not just OKC ingest. The persisted carrier is
  the committed append-only `sig.officer-naming-decisions/1` registry
  (`policy/src/policy/data/officer_naming_decisions.json` — the
  `sig.publication-withdrawals/1` precedent, read verbatim by the Python
  policy layer and the TypeScript web layer). A public-employee-name row
  publishes only when a persisted record names its
  `(subject_id, predicate_id)` AND the record's stored inputs replay to
  a two-reviewer concur AND the SIG-PUB-017 jurisdiction rule permits;
  a missing, non-concur, or inconsistent record — and any unknown or
  restrictive jurisdiction — withholds. The gate binds at the export
  builder (`build_web_dossiers`' `_gate_public_employee_names`) and at
  the web data funnel (`getDossiers()` — the dossier page, print export,
  and JSON endpoint all inherit it), renders withheld rows as withheld
  with the refusal reason recorded (never silently dropped), and emits
  the same serialized decision record at ingest via
  `assert_person_naming_permitted`'s `record_sink`. The registry starts
  empty — no two-reviewer naming concurrence has been recorded — so
  every flagged name row withholds until the operator's recorded act.

- **Automated-traffic-enforcement technology concept and the declared
  geometry kind** (P36.3 / ACQ-03, ADR-207; cites SIG-ONTO-019/020/022/
  052/052a/056, SIG-GEO-003, SIG-ONTO-066/067) — the `ate` family under
  `surveillance-vehicle` carries six active leaves
  (`ate-red-light`, `ate-speed`, `ate-bus-lane`,
  `ate-school-bus-stop-arm`, `ate-work-zone`, `ate-unspecified`), each
  with the distinguishing-criterion / evidence-signature / salience
  triple, moving the canonical vocabulary to 14 domains / 37 families /
  110 active technologies; the `GeometryKind` enum
  (`point` | `line` | `area`) and the `geometry_kind` predicate let a
  record declare an area shape so an ATE zone or published programme
  area is never flattened to a device point. The canonical spec's
  §13.1 counts and §11.5 echo are amended through `spec_src`.

- **Declared technology typing on camera-registry records** (P35.15a /
  PKG-07; cites F-329, F-523, NEW-7/FM-05, SIG-ONTO-052a–056,
  SIG-ONTO-027, SIG-RECON-013-family) — every camera-registry target now
  declares an active-member SKOS technology slug
  (`alpr-fixed`, `fixed-camera-ptz`, `fixed-camera-cctv`, …, validated
  against `ontology/vocab/technology.yaml`; a missing/retired slug fails
  the run closed, never falls back), `dot_511` emits it as a `technology`
  claim per subject plus the entity row's declared subtype (the blanket
  `traffic_camera` record_kind is gone — it survives only as an explicit
  target declaration on surveillance-video targets), and the declared
  class drives entity resolution (substring heuristics demoted to
  recorded mismatch findings). The sites export column, map assets, the
  `sig.published-record/2` projection's `technology` field, dossier rows
  and the `/map/` Technology facet all read it. Subject identity is
  unchanged (`traffic_camera:<src>:<tgt>:<ref>` — no identity fork under
  append-only rules); the ~200k-subject hosted backfill is P35.15b.
- **Host-level opt-out register + affirmative rights-reservation refusal**
  (P36.1a; cites SIG-INGEST-046c, §26 rule 7 under SIG-INGEST-036) — the two
  E2-06 controls, exercised on fixtures only: a committed, append-only
  `connectors/data/opt_out_register.toml` (`sig.opt-out-register/1`)
  consulted by the shared `PoliteFetcher` **before every fetch — before the
  robots probe** — so a listed host receives zero egress, with
  `$SIG_OPT_OUT_REGISTER` applying an entry on the next run without a
  registry rebuild or redeploy; and `policy.crawler.detect_reservation`,
  which detects affirmative machine-readable rights reservations
  (`Content-Signal` directives such as `ai-train=no`, `TDM-Reservation`,
  `X-Robots-Tag: noai`/`noimageai`, and the page-level TDMRep/robots-meta
  EU DSM Article 4 forms) and refuses with the signals kept verbatim as
  evidence. The refusal lands on `policy.rights.RightsRecord` as a new
  additive `reservation` field — a *refused* state stored distinctly from
  `UNDETERMINED` (SIG-INGEST-046c) — and on the run report's `refusals`
  as a first-class disposition; `assert_loadable`, `live_gate_reasons`,
  the flip-ready verdict and the flip-metadata rule all refuse a reserved
  record. GL-GATE-08 is unchanged: a robots `Disallow` is not a
  reservation and still proceeds stamped `robots_disregarded`. No
  `ingestion_permitted` flip, no live fetch, no external contact.
- **Scheduler of record: `ops/cadence.toml` + `sig-ops live-diff`** (P35.1a;
  cites SIG-OPS-006, SIG-OPS-011; ADR-174) — Cloud Scheduler + the committed
  `ops/cadence.toml` become the repository-owned scheduler of record, and a
  new read-only `sig-ops live-diff` reconciles declaration against live
  production: Cloud Scheduler triggers (schedule/state/body), Cloud Run
  jobs and services (image digest, service account, env/secret wiring),
  undeclared live jobs (`[[manual_jobs]]` is the only legitimate
  trigger-less job), and bucket posture (UBLA, versioning, lifecycle,
  public access). `cadence --check` now lints cron syntax **and semantics**
  — simultaneous day-of-month/day-of-week restrictions (cron ORs them)
  refuse unless the row names its exception owner via
  `cron_or_semantics_ok`; `[[pins]]` enforce digest-pinned images with a
  required `reason` + `expiry` per exception (tags and expired pins are
  drift). `scheduled-ops.sh` reconciles triggers from cadence (paused
  maintenance rows stay declared-but-paused), stamps
  `SIG_OPS_CADENCE_SHA256`, publishes the declaration bundle to restricted
  GCS, and **reports** undeclared triggers rather than deleting them
  (P35.1b owns the deletion pass). The daily `sig-sched-live-diff` trigger
  and the paused `sig-sched-pg-logical-export` are declared; the GitHub
  Actions `reingest.yml` schedule is retired (manual `workflow_dispatch`
  stays inert). The scheduler apply leg queues in RETURN PASS (operator
  ADC + AR-3 window); the read-only live run already landed real evidence —
  28 findings, exit 1, never claimed as clean.
- **Post-DNS cut-over probe: `sig-ops post-cutover-probe`** (P35.67;
  cites SIG-OPS-006, SIG-OPS-011) — the read-only verification the
  operator's OP-09 nameserver switch must satisfy: a `sig.probe-run/1`
  record covering the Cloudflare NS pair, the grey-cloud apex/www A
  records, DNSSEC (`ad` + RRSIG + parent DS rollover), TLS SAN + dates,
  the `sig-web-cert` managed `ACTIVE` status, both redirects, the public
  route sweep (sitemap locs with the `ops/public_routes.toml` allowlist
  fallback), the two-state mail posture, and registrar-lock drift.
  `--capture`/`--from-capture` preserve and replay raw outputs; every
  emitted command is a read-only dig/curl/openssl/gcloud/whois call —
  no mutating argv is reachable (pinned in tests). Both live legs queue
  in RETURN PASS: L1 waits on OP-09 (dig still answers Squarespace at
  dispatch), L2 is the cert-renewal read ≈ 2026-11-22. The committed
  checklist maps each check to the `DNS_CUTOVER_RUNBOOK.md` step it
  discharges (`docs/build/reports/POST_CUTOVER_PROBE_CHECKLIST.md`).
- **Zero-egress distribution host: the R2 public mirror leg** (P35.5;
  cites SIG-TRANSP-019, D-J3-4/A-3) — release downloads gain a
  zero-egress Cloudflare R2 mirror so egress cost cannot scale with
  traffic; GCS stays the origin of record. `ops/mirrors.toml` carries the
  committed-**disabled** `r2-public` row (enabled by the live leg after
  the operator's OP-09 nameserver switch + the GATE-G4 OM-20 listing —
  queued in RETURN PASS with the ticket's re-run prompt).
  `exports.push` gains fail-closed `PushLimits` (per-file 512 MiB,
  per-run object/byte caps, a request-rate guard that refuses an
  over-rate run, optional pacing) and `assert_non_listable_origin` — a
  push run never truncates, and an origin that answers an anonymous
  listing refuses. The publish path takes the leg: `sig-ops publish-web
  --mirror <row>` runs `assert_low_egress` inside the preflight (a
  disabled row, a metered provider, a breached cap, or an egress ALARM
  all refuse before any write), and `sig-ops mirror-push` is the
  standalone verb. The $50/month hard ceiling lands in
  `ops/config.toml` `[egress] hard_ceiling_usd` — `sig-ops egress-report
  --usage-usd` warns at 80% ($40) and alarms at 100% ($50) through the
  P34.4 recorded-alert seam; the documented kill switch (disable the CDN
  route / R2 public access — an operator step, never an agent action)
  lives in `docs/build/reports/R2_MIRROR_RUNBOOK.md`.
- **API release parity: release-backed routes serve the promoted
  release's verified files** (P35.57; cites SIG-REL-010) — the routes
  whose answers the site shows (`/v1/dossier/**`, `/v1/coverage/**`,
  `/v1/export`, `/v1/changes`, `/v1/sources`, `/v1/releases/**`)
  answer byte-for-byte from the current promoted release's
  `sig.api-slice/1` document set, digest-pinned to the release integrity
  manifest, with `?release=<publication_id>` selecting any promoted
  release. Responses carry `X-SIG-Basis: release`,
  `X-SIG-Release: <label> <publication_id>` and a body-level `basis` /
  `release` identity block; routes still answered from the claim spine
  now disclose `X-SIG-Basis: live-spine` plus `basis.spine_watermark` and
  `basis.latest_release`. Release failures are fail-closed typed errors
  (`unknown_publication`, `scope_not_available`, `withdrawn`,
  `release_artifact_absent`, `release_artifact_unpinned`,
  `release_verification_failed`, `release_metadata_mismatch`,
  `no_current_release`, `release_serving_unconfigured`), never silent
  fallbacks. `/` and `/v1/health` name the current release, code commit
  and image digest; `--release-registry` also reads
  `SIG_RELEASE_REGISTRY`. Release promotion gains the V7 api-parity
  preflight — a release the API cannot serve is refused; pre-slice
  releases are recorded `deferred` (obligation `D-P35.57-1`).
- **Withdrawal-barrier bytes: real tombstones on every alias** (P34.41;
  cites SIG-REL-013 (owner P35.55), SIG-FIND-001/002, SIG-GOV-007;
  ADR-132) — the generated deny map now denies **every alias** of a
  withdrawn route (`/<route>`, `/<route>/`, `/<route>/index.html` for
  page routes; the exact path for file routes such as the record's
  `.json` twin) with `error_page 410` onto that route's own
  `sig.tombstone/1` body staged under `conf/tombstone/` (an
  `internal`-only prefix in `ops/web/nginx.conf`) — the 410 answers the
  recorded tombstone (target kind/id, `withdrawn_at`, public-safe
  `reason_class`, `disposition_ref`, `superseded_by`, release label,
  corrections link; never an e-mail address), never nginx's generic
  page. `/entity/<t>/<id>/` convenience stubs are denied and rewritten
  to stub tombstones from the same deny set — entity-level denies,
  claim denies on the active release's record route, and the latest
  release's own namespace deny all reach the stub — and `page_index`
  pages embedding a denied id are denied and marked `withdrawn` in the
  index. `/r/<pub>/` now emits a real namespace landing page (with meta
  description) instead of a directory 403.
- **Release-archive chrome + same-origin link crawl** (P34.34a; cites
  SIG-FIND-001/002, SIG-UI-033, SIG-UI-024, SIG-LIC-011, SIG-UI-049) — every
  exports-rendered page now carries site navigation, a `/dispute/` link, and
  the licence of the data shown; `validate_release` and `activate` crawl
  every page's same-origin `href`/`action` and refuse unresolved links
  (withdrawal 410 tombstones resolve); `record_claims` rows and claim
  anchors carry the sparse `access_kind` field via the reconciler
  vocabulary; dossiers state their provisional computed posture and link
  from release landings; zero-record landings explain themselves as
  verified-empty publications; `build_spine_export` always emits
  `web/leverage.json` (the recorded changeset feed folded in, else the
  honest zeroed ledger — never a live fetch).
- **Versioning discipline + one version source** (P34.23, SIG-REL-014) —
  every package derives `__version__` via `importlib.metadata` (no `0.0.0`
  reported anywhere); `scripts/bump_version.py` bumps all 14 pyprojects and
  `web/package.json` together (dry-run default); `resolver_version` in
  export manifests is now the `resolution` package version + `+g<commit8>`
  instead of the exports placeholder; the CHANGELOG gate joins the `docs`
  CI job; `docs/build/reports/releases/` holds the operator tag procedure,
  `TAG_TEMPLATE.md`, and the prepared `TAG_v0.1.0.md` (not tagged —
  operator action, OP-08).
- **Release identity v2 + clock guards** (P35.12, SIG-REL-001/002/003,
  ADR-161 extending ADR-132) — `sig.publication-descriptor/2` lands in
  `exports/release_identity.py` carrying the G3 §3.2 field layout (label,
  environment, the spine-snapshot block with instants + watermark +
  sqitch head, keyed export id, code block with the tree-read commit,
  versions incl. ontology, the gates/evaluation/disclosures blocks,
  `transparency_root`, and `boundaries_root` declared as the JUR-01 input).
  The human label `sig-YYYY-MM-DD.N` is allocated under the release-label
  registry lock (`labels.lock` + `sig.release-labels/1`) with the date
  derived from `snapshot.as_of_world`, never typed; the export id is
  `sig-export-<YYYYMMDDTHHMMSSZ>-<key8>` keyed over instants + watermark +
  commit (the NEW-1 same-day collision fix — `manifest.json`'s
  `release_id` changes form). The §3.3 clock guards bind on the
  `build --from-spine` operator path: T0 read once, the AR-3 windows
  refuse unless `--emergency`, a remote-Date host-clock sanity check,
  a future `--as-of`/`--belief` refuses before any DB read, an earlier-day
  cut requires `--replay <reason>` (Class S, `environment=replay`),
  `as_of_world ≤ as_of_belief ≤ built_at ≤ now+5min` is enforced,
  activation requires `activated_at ≥ built_at`, and no emitted date may
  be later than `built_at`. `sig-exports release build` emits v2 by
  default (`--schema-version 1` keeps the legacy writer); `release
  promote` refuses v1 descriptors, dirty trees, unpushed commits,
  `0.0.0` versions, non-sha commits and release dates earlier than the
  previous release — which excludes the `p-17b713` fixture candidate by
  rule. `ops/gcp/export.sh` now propagates `--belief`, `--environment`,
  `--replay` and `--emergency`; `ops/disclosures.toml` (`sig.disclosures/1`)
  is the declared-empty disclosure registry the descriptor digests.
  v1 descriptors stay parseable; only promotion gates on v2. No hosted
  mutation — the publish rows own the hosted descriptor write.
- **Generated data dictionary + linked machine metadata** (P35.39 / row
  318; R11-K13-TX-10a; owners SIG-TRANSP-016, SIG-TRANSP-017; cites
  SIG-TRANSP-033, SIG-UI-035, SIG-EXPORT-001/006, J3 §6.5–6.7 + §6.10 +
  D-J3-7 "linked files only", K13 §7 W2, J1 NEW-11, DR-C3-01) — every
  emitted column is now declared in one exporter-side column registry
  (`exports/column_registry.py` — description, datatype, unit,
  nullability, enum source + generated-enum values where applicable) and
  every write seam fails closed on an undocumented column:
  `assert_documented` at each writer's emit point and
  `assert_path_documented` over every manifest path at manifest build —
  row-bearing serialisations (incl. `*.jsonl`, `*.jsonld` row streams)
  register by stem while linked-data documents (`catalog.jsonld`,
  `provenance.jsonld`, evidence documents) classify as documents, not
  hidden tables. Each bundle emits `dictionary.json`
  (`sig.data-dictionary/1`), one
  `schemas/<resource>.tableschema.json` Frictionless Table Schema per
  tabular resource, and a regenerated `datapackage.json` (Frictionless
  Data Package v2: per-resource `schema` refs, sources, licences,
  checksums, package contributors/version/created). New linked metadata
  files — never inlined on public pages (D-J3-7): `catalog.jsonld`
  (DCAT 3 — datasets, distributions with download URL + media type +
  byte size + `spdx:checksum`, compartment-scoped `dct:license` +
  `dct:accessRights`, release-series membership + previous-version
  links, minted on the owned `/ns/` + `/prov/` bases) and
  `provenance.jsonld` (PROV-O — export-run activity, per-capture
  entities carrying the true recorded `retrieved_at`, never the export
  `generated_at`, `prov:hadPrimarySource` upstream links where
  available). Release activation emits
  `releases/<publication_id>/datapackage.json` +
  `releases/<publication_id>/catalog.jsonld` as declared overlays and
  `releases/catalog.jsonld`; publish verification + release validation
  recognise them instead of failing "undeclared artifact". Web:
  `/data/dictionary/` renders the generated dictionary statically —
  fixture mode ships typed fixture entries, export mode reads
  `<exportDir>/dictionary.json` and fails loudly when absent/malformed;
  `BaseLayout` links release metadata externally
  (`<link rel="describedby">` + `rel="alternate"
  type="application/ld+json">` on a valid release stamp); export-mode
  builds copy the real `catalog.jsonld` to `dist/data/catalog.jsonld`
  and sitemap-list it only when copied — the fixture sitemap never
  advertises an absent artifact (the e2e sitemap check validates it as
  a non-HTML downloadable resource). The dictionary page stays
  zero-script and carries no inline JSON-LD. No compartment merge, no
  claim-spine mutation, no gate/permission flip — the licence and
  publication gates stay fail-closed.
- **The source universe, the six-state lifecycle partition, and
  named-predicate source counts** (P35.40 / row 319; R11-K13-TX-11;
  owners SIG-TRANSP-002, SIG-TRANSP-026, SIG-TRANSP-027; cites
  SIG-TRANSP-001, K9 §3.1–3.3 [design ref], F-431) — one counting
  definition now holds everywhere it is used: a **source is one
  registry row** (`sig.source-row/1` — the row schema
  `transparency/sources.json` emits, renamed from
  `sig.transparency-sources/1`); a connector, tenant, endpoint,
  capture host or mirror is an attribute of a row, never a source.
  One exporter function computes the lifecycle partition at the
  release's belief cut under the published precedence
  (`withdrawn` → `published` → `ingested_not_published` →
  `permitted_not_ingested` → `gated` → `refused`, first match wins;
  `withdrawn` fires only on a recorded withdrawal signal — none
  exists in today's registry, honestly zero), and `counts.json`
  (`sig.source-counts/1`) emits every count with its named
  predicate — the universe, the per-state counts + id lists, the
  emitted `partition_sum` check (the export fails closed when the
  six states do not cover the registry exactly once), orthogonal
  attributes (rights, schedule incl. the exclusive `one_time_load`
  facet, run records, site records, lanes, open issues), and the
  anomaly list: identifiers carrying data (claims, captures, runs,
  sites, cadence declarations) with no registry row are listed by
  id, **never counted** (e.g. `okc_council_statement`,
  `okc-contract-c241032`, `osm`). Public copy is corrected to the
  predicates the numbers measure (K9 §3.3): the home headline
  "N sources tracked for freshness" becomes "sources with
  published site records" (`attributes.site_records.count`);
  "How we know this" "Independent sources" becomes "Sources with
  published claims" — site-wide it IS `lifecycle.published.count`
  read from the release's `transparency/counts.json`, and
  page-scoped modules carry a new `source_label` field naming
  their predicate ("Detectors" on the research queue); `/sources/`
  gains a "How SIG counts a source" block rendering the universe,
  the partition, the attributes and the anomaly box, every numeral
  a `<Figure>` pointing into `transparency/counts.json`; the
  search page and freshness empty-state say "registry sources".
  Export-mode builds read `<exportDir>/transparency/{counts,
  sources}.json` (fail-loud on missing/malformed — including a
  doc whose `partition_sum` does not hold or whose precedence
  order is not the published order), and the fixture-export
  harness emits the pair plus `dictionary.json` so a fixture-only
  export bundle builds end to end. No ingestion-permission flip,
  no gate tick, no spine mutation.

- **Watch producer v1** (P35.43 / row 322; R11-K13-WX-01; owner none —
  served SIG-UI-026/027/027a + SIG-UI-014b; cites SIG-UI-008,
  SIG-UI-050/ADR-134, the J3 §5.3 lane table, D-K7-4/D-K7-5 pending;
  K7 §8 draft SIG-WATCH-D01…D10 are design refs, not stamped; owned
  finding F-481) — `web/watch.json` is no longer the empty surface:
  `exports/watch.py` derives the six K7 §5.2 kinds
  (`renewal_deadline`, `contract_expiry`, `solicitation_deadline`,
  `agenda_item`, `legislative_action`, `grant_period_end`) from
  publishable claim-spine rows and emits the versioned
  `sig/watch/2` envelope with `sig.watch-item/1` items — one alert
  date with `date_kind` + `date_certainty` (an `upper_bound` expiry
  is never labelled a deadline), §5.3 placement (unplaced is a
  data-quality bucket, never a guessed place; federal items sit
  under `iso3166-1:US`), evidence links gated by the shared
  statements lane map, `contested`, `first_seen`/`last_checked`, and
  a per-place coverage block so an empty result always arrives with
  its coverage statement. A read-only `watch_subject_counts` query
  sizes the emission; `analytics._decision_point` reads the produced
  items and the renewal date reuses `_next_decision_date` — one
  derivation, never a second formula. `getWatch()` bridges the v2
  envelope back to the legacy item shape until the surface rows
  consume it natively. No production mutation, no spine write —
  the artifact ships with the next export under that row's
  authority.
- **Public-API rate limits — the exposure-posture enforcement half
  lands dark** (P36.13 / row 354; SIG-API-009 the ticket's read +
  SIG-API-011 cited — the §37.4 anonymous tier's rate-limit clause;
  K3 §5.6, D-K3-6 [B-30], SIG-STORE-003) —
  `api/src/api/rate_limit.py` adds an in-process per-client token
  bucket (30 requests per 60 seconds, burst 10) keyed on the
  edge-appended client address: RFC 7239 `Forwarded` /
  `X-Forwarded-For` sliced by the declared
  `SIG_API_TRUSTED_PROXY_HOPS` (2 behind the Google external load
  balancer); client-claimed chain entries are never trusted and a
  short chain falls back to the direct peer. When armed,
  `RateLimit-Limit`/`RateLimit-Remaining`/`RateLimit-Reset` ride
  every response — success, typed errors, framework 404s and the
  emitted 500 alike — and an over-limit burst in `enforce` posture
  answers 429 + `Retry-After` with the typed `{detail,
  code: "rate_limited", …}` body or the no-JS HTML page (DR-C4-10).
  The `SIG_API_RATE_LIMIT` env = `off` (default — nothing mounts;
  the code ships dark ahead of the staged flip) · `advise`
  (headers + accounting, never rejects) · `enforce`; an unknown
  value refuses app construction. The hosted-enforcement flip is
  the named OM-20 mutation — staged in
  `ops/gcp/rate-limit-enforcement.sh` (check/apply/verify; apply
  gated on ADC + `SIG_GCP_PROJECT` + `SIG_RATELIMIT_AUTHOR` + the
  AR-3 windows), queued under `D-P36.13-1`, not performed by this
  change; the loopback curation app and the non-operational intake
  receiver are untouched. No Cloud Armor — D-K3-6 stays deferred;
  the in-process limiter is the whole mechanism (SIG-STORE-003).
- **The L4 inference marker on every export and API record**
  (P36.14 / row 355; SIG-RECON-052 — every inference visually and
  structurally distinguishable from observed evidence; cited
  SIG-RECON-047/031, SIG-UI-005/006/062, SIG-CONF-005, SIG-ENG-042) —
  the typed marker pair `inferred` + `layer` now travels on every
  record where a derived fact can appear: `inference.marking` defines
  the contract once (`mark_inferred` / `is_inferred_record` — the pair
  is coherent or absent); export governance-chain rows and structured
  links (`spine_export.py`), the dedup view's inferential entries
  (`possible_duplicates`, `multi_view` — dedup.py), and every
  `sig.published-record/5` document carry it; the API's
  `ResolutionEnvelope`/`ClaimResponse`/`TaskResponse`/
  `ContradictionResponse` expose `inferred: false, layer: null` as
  typed fields on spine-layer records so observed and inferred
  answers are structurally distinct, never prose-only. The web dossier
  renders the `sig-inferred` marker — a ◈ glyph + "Inferred" label on
  a dotted chip (a non-green token; text/glyph redundant channels per
  SIG-UI-005) — server-rendered with `data-inferred`/`data-layer`
  attributes, no script, print-parity. A cross-surface conformance
  test asserts one fixture inference is marked in export bytes, the
  API payload and the rendered page — removing the marker fails it.
- **Design tokens v2 — the shared visual token layer**
  (P36.16 / row 356; SIG-UI-146 + SIG-UI-148 + SIG-UI-156 — owner;
  D-K14-3/D-K14-5 [B-22] = as recommended; cites SIG-UI-005/006,
  SIG-UI-039/040, SIG-ENG-042) — `web/src/styles/tokens.css` is now
  the single source of truth for every colour, type, space, radius and
  motion value on the public surface: the 8-step 1.25 type scale
  (13 px floor, responsive steps 4–5), the 4 px space ramp, the
  4/8/pill radius set, the 120–160 ms motion pair, and light + chosen
  dark colour sets under `prefers-color-scheme` with print forcing
  light. The reserved hues are single-meaning — raspberry
  (`--sig-epi-disagree-*`) only for contested/unresolved, amber
  (`--sig-epi-provisional-*`) only for the provisional state, blue for
  links and data; the slate support ramp is ordinal and lightness-
  monotone; the incompleteness banner is neutral (absence is not a
  disagreement). `epistemic.css`, `islands.css` and `curate.css` are
  restated on tokens — every legacy `--sig-*` name kept as an alias —
  and the map style's forked literals ride the same data-blue
  vocabulary via `src/lib/design-tokens.ts`, pinned equal to the CSS
  by test. Public Sans Variable (26.8 KB, OFL-1.1) ships self-hosted
  with `font-display: optional`; `scripts/check-tokens.mjs` is the
  stylelint-equivalent allow-list gate plus the ≤12 KiB gzip CSS /
  ≤30 KiB font budgets (`check:tokens` in `npm run check`); pages
  declare `color-scheme: light dark`. Zero client JS added.
- **Lexicon and copy system — one machine-readable vocabulary and a
  generated `/glossary/`** (P36.17 / row 357; SIG-UI-061 + SIG-UI-062 +
  SIG-UI-064 + SIG-UI-133 + SIG-UI-143 + SIG-UI-147 + SIG-UI-149 —
  owner; D-K14-5/D-K14-6 [B-22] = as recommended, D-K14-8 [B-29] = yes;
  cites SIG-UI-039/040, SIG-ENG-042, SIG-TRANSP-001…043) —
  `web/src/lib/lexicon.json` (`sig.lexicon/1`) is now the single
  legend and epistemic vocabulary: the K13 C-01…C-04 decisions (the
  corroborated fill counts independent lineages and carries the
  interim "2+ source records; republications not yet collapsed" line,
  the line pattern encodes access kind only, every symbol declares one
  meaning family, absence is one shared hatch with kinds told apart by
  symbol + text), the L3 `copy`/`possible duplicate` identity states
  (possible duplicates stay visible and unmerged — SIG cannot prove
  they are the same camera), Candidate vs Provisional distinct in
  word/symbol/filter, and the controlled one-word-per-concept
  vocabulary. `epistemic.ts` derives every display string from it
  (K14 §3.4 labels — "None found", "Stated absent" — stored enums
  untouched); the map style resolves its data hue through
  `legend.dataHue.token`; the Python figure kit reads the same JSON.
  `/glossary/` (T1, zero JS) is generated at build from Appendix E
  verbatim + lexicon terms + site terms — 47 entries, 88 "Spec
  references" disclosures; `<Term>` renders a glossary link plus a
  native HTML popover and fails the build on an undefined term;
  `<InBrief>` and `<SpecRefs>` land the plain-first/spec-ref-disclosed
  copy pattern on `/methodology/`; reason codes and axis codes render
  inside `<code>`, never prose. `scripts/check-lexicon.mjs`
  (`check:lexicon` in `npm run check`) fails on an uncovered enum, a
  symbol carrying two meanings, a shadowed spec term, an unresolvable
  `<Term>`, or a raw enum in built visible prose.
- **Six-section route-aware chrome, the computed release route
  manifest and the forty-word shared shell** (P36.18 / row 358;
  SIG-UI-051 + SIG-UI-145 + SIG-UI-150 — owner; C-31 + D-K14-4 = yes +
  D-K14-2 = yes carried verbatim; cites SIG-UI-039/040, SIG-UI-035,
  SIG-ENG-042, UXR-01) — `web/src/lib/release-routes.ts` computes the
  set of public routes this build actually serves (`import.meta.glob`
  over `src/pages/` plus data-conditioned probes and, in export mode,
  the pipeline-declared `web/site-routes.json`), and `web/src/lib/nav.ts`
  filters the six K13 §2.1 sections and their items against it — a
  section or menu item the release does not serve is never offered,
  and the current section carries `aria-current`.
  `web/src/components/chrome/` lands the shared `SiteHeader`
  (wordmark, sections, a plain-GET `/search/` form and a
  zero-JavaScript mobile `<details>` menu), `Breadcrumbs` and
  `PageHeaderBand` (breadcrumbs, H1, release stamp, actions and the
  Cite `<details>`); `BaseLayout` rewires every page to the compact
  header, the page-header band and a footer strip whose counts and
  dates render from `lexicon.chrome` templates — the `check:lexicon`
  chrome leg lints the ≤ 40 visible-word budget. Dossier pages pass
  their canonical chain as breadcrumbs and carry Print/JSON as band
  actions. No client JavaScript was added and every emitted route
  keeps its ADR-155 page-type classification.

### Changed

- **Site chrome and page layout — the six-section route-aware
  navigation, shared grid, page-header band and forty-word footer
  strip** (P36.18 / row 358; R11-K13-UXK14-2; owner SIG-UI-051,
  SIG-UI-145, SIG-UI-150; cites K13 information architecture, K14
  onboarding, C-31, ADR-155, SIG-ENG-042) — `BaseLayout` now renders a
  computed-release route manifest (`web/src/lib/release-routes.ts`,
  built from emitted page sources plus `import.meta.glob` probes, never
  a hand list; internal routes stay unlisted) and the
  `web/src/lib/nav.ts` model filters the six K13 sections — Places,
  Explore, Watch, Sources & data, About, Search — dropping any section
  or item whose target the release does not emit (Organisations is
  absent while no `/entity/` hub exists) and resolving the current
  section by longest declared path prefix. `SiteHeader.astro` carries
  the wordmark, a plain GET search form and the same sections in a
  native `<details>` mobile menu — zero client JavaScript added;
  `aria-current` marks the current section and page.
  `PageHeaderBand.astro` gives every page breadcrumbs, the release
  stamp, its actions and a native Cite disclosure one action away;
  `Breadcrumbs.astro` renders canonical jurisdiction chains on dossier
  records (country > state > county > place — never invented ancestry).
  Header and `main` share one grid, and the footer carries only the
  lexicon-driven provenance strip (source count, as-of, review status)
  plus a route-filtered link set; the visible shared chrome measures 31
  words against the SIG-UI-145 forty-word budget, enforced by
  `check-lexicon.mjs`. The mobile H1 sits ~100 px from the top at 320
  px, inside the 120 px budget. The `/network/` interactive explorer
  gains the map's height-reserving placeholder
  (`sig-island__placeholder` hidden by `:has()` on mount) — the
  previously unreserved React mount pushed the lists below ~95 rem and
  measured CLS 0.069 against the ≤ 0.05 ceiling; all three local
  budget runs now measure 0.
- **Crawler conduct text, the `robots_policy` field and the
  `/data-collection/` page state the decided posture** (P36.1b / row 349;
  R11-GOV-04; ADR-222; owner SIG-INGEST-036 rule 7 + SIG-INGEST-046c;
  cites Q-E2-11 [A-5], Q-E2-02 [B-6], GL-GATE-08, ADR-087/088/168/182/187,
  SIG-INGEST-046b, SIG-ENG-042) — the E2-07 contradiction closed:
  `policy/src/policy/data/crawler_conduct.toml` rule 2 now reads "Probe
  and record robots.txt" (it previously said "Honor robots.txt …
  permission is NOT granted", a claim the code never made true), rule 7
  names the `sig.opt-out-register/1` mechanism, and `policy.crawler`'s
  docstring and helper docs match. The `robots_policy` registry field is
  documented — on the `RobotsPolicy` enum and in the `sources.toml`
  header — as the source's robots posture *declared at review time*,
  registry metadata that is never an enforcement claim: under GL-GATE-08
  every value means "probe + record", and a `disallowed`/`unretrievable`
  verdict proceeds stamped `robots_disregarded` and is disclosed publicly
  as host + count. `/data-collection/` is rewritten to the full text —
  the eight conduct rules carried verbatim (new CR-01…CR-08 batch rows
  pinned to `title + ". " + text`), the robots posture, the host+count
  disclosure, the opt-out register checked before every fetch, the
  SIG-INGEST-046c reservation refusal kept distinct from `UNDETERMINED`,
  rate limits and the `/dispute/` stop route; DC-21 supersedes DC-03 and
  DC-22…DC-32 carry the new sections, all `pending` until the operator's
  verbatim confirmation. `tests/unit/test_conduct_text.py` is the new
  copy check: conduct text asserting conduct the code does not implement
  fails the build, and the anchors are fixture-verified (an opted-out
  host sees zero egress; a `Disallow` proceeds stamped; a recorded
  reservation refuses at the loader gate). The Stage-0 outreach letter's
  robots/ToS sentence is corrected before any send (sending stays
  operator outreach under ADR-171); the ALPR Abuse Library's observed
  `Content-Signal` + Article-4 reservation is recorded as
  `[sources.alpr_abuse_library.rights.reservation]` — the row stays
  `ingestion_permitted=false`, rights `UNDETERMINED`, and the loader
  refuses it outright. No behaviour change: A-5 re-confirmed GL-GATE-08
  as-is on every host; the text now records it.

- **Citation block and release id on every page** (P35.42 / row 321;
  R11-K13-TX-13a; owner SIG-TRANSP-023, citation-block half — the
  `/s/<pub>/` snapshot build, edge `selectors.conf` and the legacy
  `withBase()` sweep are P36.66a/b's, rows 409/410; cites SIG-UI-035,
  SIG-REL-008, DR-C3-14, UXR-25 [design ref]; owned findings F-07,
  F-099, F-101, F-390, F-399) — `BaseLayout` now passes the build's
  release context `{publicationId, label, recordPath}` to the
  citation block on every public page (the F-399 fix — the layout
  never passed a release, so every page carried the legacy
  belief-pinned query URL under a reproducibility promise the static
  origin cannot honour). The block renders the verbatim J3 §8.2 cite
  sentence — `Cite: <title>, SIG release <pub-short> (data as of
  <as_of_world>, belief <as_of_belief>, ruleset <r>)` — with the
  release id beside the as-of pair; the phrase "reproducible after
  SIG corrects itself" now appears **only** over an immutable
  `/s/<pub>/` or `/r/<pub>/` URL (a render rule derived from the
  cited path, never a template flag), and every other page says —
  verbatim the J3 interim wording — "This page is the latest view of
  release <data release id>; an immutable citable copy is not yet
  published." Dossier pages cite their released `/r/<pub>/` record
  URL; the print dossier footer's cite line renders the same shared
  contract plus the licence id (F-101); and every new internal link
  is built with `withBase()` (the root-absolute-path containment
  count did not grow). Pages under a build that binds no release
  (fixtures/development) render the plain as-of link — the honest
  development state, never a fabricated release.
- **Freshness semantics v2 — one shared verdict, honest staleness, and
  two separate change dates** (P35.41 / row 320; owner SIG-TRANSP-029 +
  SIG-TRANSP-030 + SIG-TRANSP-031 + SIG-TRANSP-007, the release side of
  SIG-TRANSP-034; cites SIG-METRIC-006, SIG-ENG-021, SIG-INGEST-030c,
  GQ-15, K9 §5.1–5.5 + §10 C-4…C-7, J3 §3.2/§4.6 [design refs], F-137
  [owned]) — every freshness value on the public surface is now produced
  by the single pure `freshness_verdict(cadence, executions, at)`
  (`policy/src/policy/freshness.py`), evaluated at the release's
  as-of instant and stamped `evaluated_at`; status-time fields never
  reach a release artifact. Volatility is measured across **all**
  published claims from the ontology predicate registry — undated claims
  counted, unregistered predicates named — replacing the dated-only
  bias. Staleness is honest: the freshness page renders "stale n of m
  evaluable" plus an explicit undated count, and a source whose
  observations cannot be dated shows its evaluable/not-evaluable counts —
  never "unknown", never a fabricated "0 stale" (the F-137 fix). Source
  rows now carry two distinct dates: `last_upstream_change` (newest
  publisher-declared instant — ArcGIS `lastEditDate`, Socrata
  `rowsUpdatedAt`/`dataUpdatedAt`, CKAN `metadata_modified`, Eyes-on-Flock
  `data_last_updated`, `Last-Modified`; `ETag` is a token, never a date;
  byte-only formatting changes never move it — and `last_sig_records_change`
  (the SIG record-set diff on the new per-run `records_digest`, with a
  labelled interim basis until release-slice diffing lands). Cadence is
  disclosed per source ("monthly, day 6", `registry, not scheduled`,
  `not_recorded`) and `one_time_load` is a first-class verdict. The
  connector capture spine gains four additive nullable columns
  (`records_digest`, `upstream_modified_at`, `upstream_token`,
  `upstream_modified_basis` — sqitch `capture_freshness_marks`, exposed
  through `v_transparency_capture`); pre-change marks stay NULL, no
  backfill invents a declared value.
- **Identifier base moved to the owned domain, with the append-only alias
  map + compat note and truthful release provenance** (P35.38b / row 317;
  R11-SAFE-06; owner SIG-IDENT-031; cites F-184 + Q-E2-03 [B-6]
  *"Move UA, don't buy domain"*, SIG-INGEST-011/015/016, SIG-EXPORT-002/003,
  SIG-API-008, ED-38/39/40, ADR-168/132/178/217) — every identifier SIG
  mints in new releases now carries `surveillancegraph.org`
  (`ontology.surveillancegraph.org` for the ontology/vocabulary families):
  the LinkML schema ids and `sig:` prefix, §13 SKOS vocabulary IRIs, the
  PROV-O `/prov/` namespace behind `provenance.ttl`, the JSON-LD `/ns/`
  `@vocab` context, the API `/id/` subject IRIs, the watch-feed
  subscription UIDs and the OCFL `user.address` default — each behind one
  declared constant per surface, with a repo check that fails a new
  `sig-project.org` literal or a second hard-coded base
  (`tests/unit/test_identity_base.py`). Already-published IRIs are never
  rewritten: `docs/governance/iri-base-alias-map.json`
  (`sig.iri-alias-map/1`, append-only) maps every retired base to its new
  mint base as a name mapping — never an HTTP-redirect claim — and
  `docs/governance/iri-base-compat-note.md` is the published note;
  ADR-217 records the decision and the accepted residual (the retired
  domains stay unregistered; RISK-R11-29). `provenance.ttl` now emits the
  real bound captures — the recorded `retrieved_at`, the retrieving
  `ingest_run` (connector name/version, start/finish), the content digest
  and the S-6-gated upstream reference — never the export build's
  `generated_at` on a synthetic per-source entity. Closes the `D-P35.3-1`
  watch-feed UID deferral (the sentinel compartment is deleted); files
  `D-P35.38b-1` (hosted vocabulary IRI re-stamp) and `D-P35.38b-2`
  (organised-editing disclosure repoint — provisioned contact + real
  routes + the external OSM-wiki edit).

- **Closed claim vocabulary at the sink** (P35.14a; cites SIG-STORE-013,
  SIG-ONTO-028, SIG-ONTO-035, SIG-ONTO-051, SIG-ONTO-057, SIG-ONTO-060,
  SIG-STORE-037, SIG-STORE-044, SIG-GEO-002) — the claim sink now treats the
  predicate and evidence-genre vocabularies as closed registries: a claim
  carrying a predicate absent from `vocab_predicate` or an evidence genre
  absent from the new `vocab_artifact_genre` table produces no claim and
  lands an auditable `assertion_quarantine` row stamped `unknown_predicate`
  or `unknown_genre` (full payload + provenance kept), instead of the prior
  silent sink-side auto-registration. `register_vocabulary()` now validates
  against the registry — it never creates rows. The ontology is the single
  vocabulary source: the generated predicate registry grew to 280 entries
  (including the four previously unregistered connector-emitted predicates
  `atlas_category_retired`, `deployment_ended`, `osm_element_deleted`,
  `physical_removed_from_street`) and projects the full
  280-predicate × 20-genre directness matrix into the new sqitch change
  `closed_vocabulary` (INSERT-only seed; the hosted deploy is a queued OM-19
  leg under AR-3). Connector outputs conform: Atlas stamps closed registry
  genres while raw method labels stay in `atlas_method`, Flock Portal rows
  default to `portal_snapshot`, OSM rows to `osm_node_set`, and the OSM
  Mobility vocabulary defect is corrected (`mobile` → `redeployable`,
  `vehicle` → `vehicle_mounted`, `drone` → `airborne`). Ontology hygiene:
  `SuccessionKind` + `Organization.succession{,_kind}` retired,
  `ConfigurationState.mfa_required` added, 40 technology slugs
  retired-and-superseded (104 active / 40 retired), and the generator now
  refuses reflexive or cyclic SKOS broader relations. A connector-output
  conformance test (planted violations fail closed) pins every emitted
  predicate, genre and enum value to the registry.

### Deprecated

### Removed

### Fixed

- **Freshness honesty + map suppression parity** (P35.20b / row 301,
  PKG-10 b-half; closes ED-43/ED-44; cites SIG-METRIC-006/007,
  SIG-RECON-058, SIG-UI-018/037, GQ-15, ADR-104(e), ED-29) — two public
  number defects corrected ahead of the next export. Every
  `/data-freshness/` row read `ok` with stale 0 and volatility `unknown`
  while `staleness_not_evaluable` was computed but never emitted, and 41
  evidence-bearing non-site sources had no row at all: the emit now
  carries `staleness_not_evaluable` and the source's **declared** §28.3
  volatility class — a new basis-required registry field validated
  against the closed vocabulary (279 `camreg_*`/`dot_511_*` declarations,
  all `SLOW` under the ADR-104(e) recalibration; every undeclared source
  reads `not_evaluable`, never a guessed class) — rows cover the union of
  the all-predicate freshness observations and the run-statistics
  sources, and a source whose staleness was never evaluated reads
  `not_evaluable`, never `ok` or a fabricated `stale 0`. And the map's
  accessible surfaces leaked what the figure suppressed — 601
  low-coverage cells printed 40,913 records in the table and SVG titles
  under a "Devices" header while plurality-labelled cells disagreed with
  dossier jurisdiction counts: one suppression decision
  (`binCountLabel`) now feeds the figure, the SVG `<title>` text, and the
  accessible table (a suppressed cell never leaks a count to assistive
  text); the header reads "Records + where SIG has looked"
  (SIG-RECON-058 — observation-level records, never a device census);
  cells key on the placement `jurisdiction_key` with the declared-scheme
  bucket as fallback, each bin emits its full `jurisdiction_counts` split
  so per-key sums reconcile with the dossier denominators, and
  `recordCount` is the canonical wire field with `deviceCount` kept one
  release cycle as a deprecated alias.
- **Per-dossier provenance + unclamped, exclusion-disclosed coverage**
  (P35.20a / row 300, PKG-10 a-half; owns F-134, closes ED-41/ED-42; cites
  SIG-METRIC-009/003/006/008, SIG-UI-008/044, SIG-RECON-058) — two public
  number defects corrected ahead of the next export. Every `/dossier/<slug>/`
  page rendered the same site-wide "How we know this" totals ("218
  independent sources") under the dossier's name: `web/analytics/
  provenance.json` now emits `surfaces.dossiers` — a complete per-dossier
  summary counted over the claims backing that dossier's sites — and the
  page renders it under the dossier's own scope label, while a surface with
  no emitted row renders the site-wide summary explicitly labelled
  "Site-wide" (site totals can never carry a surface's name). And the
  per-predicate reconciliation ratios that read "N of N" while thousands of
  subjects were conflicted ("232,625 of 232,625 resolved" over 5,290
  conflicted coordinates): the numerator now counts only subjects whose
  current resolution envelope picked a tier-0, currently-valid,
  publication-eligible winning claim — the `min(resolved, claimed)` clamp is
  gone, the numerator is a subset of the denominator by join — and the new
  `coverage_record.exclusions` column (sqitch `coverage_exclusion_disclosure`,
  additive + back-compatible) carries the disclosed `{conflicted, withheld,
  non_publishable, filtered}` classes as data beside each ratio, emitted on
  the web `CoverageMetric` as `exclusions` + `excluded_total`. The DB CHECK
  `coverage_ratio_exclusions_sum` pins `numerator + excluded = denominator`
  on every disclosing ratio row — an N-of-N beside excluded subjects cannot
  be written at all.
- **Archive link depth, zero-record validation, and the empty-tile build**
  (P34.34a) — record/evidence links in nested release routes are
  site-root-absolute (`/r/<pub>/…`), removing the depth-fragile `../../`
  forms by construction; `validate_release` no longer misreads a legitimate
  `indexed_records == 0` scope as missing (a zero-record release was
  unvalidatable); a zero-archive tile manifest no longer fails the web
  build — `/map/` states the absence honestly in export mode; and the
  journey verifier's browse needle was updated to the new link shape.
- **API honesty: scope, completeness, bytes, terms, basis, grants** (P34.25,
  S0 RI-02, SIG-SEC-011; extends SIG-REL-010) — `/v1/dossier/{scope}` and
  `/v1/coverage/{scope}` now answer a typed 404 `scope_not_available` for a
  scope the store does not hold (the arbitrary 25-subject dossier fallback is
  removed); coverage never reports `complete: true` with zero evaluated
  records; `bytes_available` is claimed only for public-tier captures recorded
  byte-bearing (`capture_classification = 'actual'`), with
  `bytes_unavailable_reason` disclosing why otherwise; the hand-seeded OKC
  fixture sources never appear in live PostgreSQL answers; `/terms` no longer
  names a nonexistent editorial board or counsel; every response carries the
  `X-SIG-Basis: live-spine` header and a `basis` body field; and the
  `sig_read_public` role is narrowed by the `public_read_allowlist` migration
  to exactly the published read surface.
- **Release-search states tell the truth** (P34.36; cites SIG-FIND-003,
  SIG-UI-040, SIG-UI-050; owns S1 F-154 at the fixture layer) — the
  released-corpus search's empty page now asserts only that no released
  record in the compartment matches (the "recorded absence" claim is
  removed); HTML clients get a real HTML error page for every error status
  (`format=html` or `Accept: text/html`, including a search-scoped 422 for
  malformed parameters) while JSON clients keep the `{detail, code}`
  contract; `eligible_records` and `excluded_records_by_reason` now count
  records the current policy withholds at access time (the `denied` hook
  carries the public-safe reason category; `indexed_records` stays the
  pinned index truth); the no-JS pager names the actual `limit`, drops the
  duplicated browse sentence, and humanises display labels while wire
  values stay raw; non-record compartments (`metadata`, `web`,
  `web_mixed`, `code`, `ontology`) answer 404 `compartment_not_searchable`
  instead of a readiness 503, and `build_release` fails closed if one ever
  carries `sites.jsonl`; a zero-record release reports completeness
  `not_evaluable` instead of `complete`.
- **The graph-quality suite: versioned check registry + ratchet engine +
  read-only probe** (P34.44a; owner SIG-CONF-003/SIG-CONF-006/
  SIG-CONF-007; cites SIG-CONF-009/SIG-CONF-013/SIG-ENG-042; ADR-154 →
  ADR-204) — `sig.quality-checks/1` (`exports/src/exports/data/
  quality_checks.toml`) declares the 27 checks GQ-01…GQ-27 with
  placement/mode/threshold/baseline/basis-class/fixing-row; only
  mechanical basis classes may gate; `sig-ops quality run --placement`
  evaluates the implemented M/R/P checks over a read-only spine session
  or a release dir and emits `sig.quality-report/1` + `sig.probe-run/1`
  with offered/evaluated counts — a 0-evaluated check fails and an
  unwired seam reports `not_evaluable`, never a pass; `diff_registry`
  enforces the ratchet on the ruleset itself (baselines move only toward
  thresholds, loosenings and mode weakenings need a cited new ADR, an
  `enforce` flip is legal only in the check's fixing row); `sig-ops
  quality gate` is the standalone V15 hook (a `not_evaluable` enforce
  check fails closed). The hosted baseline run and the nightly job are
  P34.44b's.
- **The quality suite measures production: the nightly probe job +
  measured baselines** (P34.44b; cites SIG-CONF-006/007 (owner
  P34.44a), SIG-CONF-009 (owner P35.34; the check here), SIG-CONF-013,
  SIG-OPS-006; ADR-154/202/204 → ADR-205) — `ops/quality_probe.toml`
  declares the permanent `sig-quality-probe` Cloud Run job
  (`sig.quality-probe/1`: pinned digest, `sig-quality-probe-rt`,
  `sig_audit`, one task, zero retries, the two declared secret envs) and
  its `sig-sched-quality-probe` trigger firing `0 1 1-5,14-31 * *`
  Etc/UTC — 01:00Z off-peak, days 6–13 structurally unschedulable — and
  the in-container `sig-ops quality nightly` verb re-checks both
  suppression windows before connecting, recording a `suppressed`
  `sig.probe-run/1` instead of running. Every run writes
  `sig.quality-report/1` + `sig.probe-run/1` as new timestamped objects
  under the conditioned `ops/probes/` scope; a failed run records an
  error probe-run and alerts through the ADR-077 ledger + `sig-alerts`
  channel. `sig-ops quality baseline` is the read-only L2 baseline leg
  (the M checks over the hosted spine + the R checks over the fetched
  release files) emitting `sig.quality-baseline/1`; `sig-exports quality
  apply-baselines` is the only writer of measured baselines — it
  recomputes the proposal from the record, stamps the additive
  `baseline_run`/`baseline_at` provenance pair (`date -u`), and re-diffs
  the result so a loosening is never written. The hosted leg is queued
  on the `live:P34.43` `sig_audit` login (exit 42, recorded).
- **Honest evaluation posture: basis classes, review-only inferential
  tiers, and the one-shot v3-interim ER re-run leg** (P34.45; owner
  SIG-CONF-001/SIG-CONF-005; cites SIG-EVAL-001/004/006, SIG-CONF-012,
  SIG-REL-010; ADR-152/153 → ADR-206) — estimands and evidence now
  carry a basis class (`human`/`agent`/`llm`/`synthetic`/`mixed`/
  `unknown`/`none`), human estimands measure only on
  `reference_provenance='human'` evidence, and agent/LLM/synthetic rows
  stay visible under their own basis — never fabricated into human
  evidence. The committed camera-site gold is relabelled `agent` (it was
  never human-labelled), and the v3-interim ruleset marks tiers 3–5
  inferential: their decisions demote to review-only
  (`no_certifying_evaluation`) absent a B5-certified evaluation, with
  GQ-24's enforce lock refusing a completed run that carries an
  uncertified inferential auto-write while disclosing historical ones on
  the append-only spine; GQ-27 enforces one basis class per published
  quality statement and refuses `verified`/`human`/`independent` under a
  non-human basis. `scripts/eval/run_honest_eval_posture.py` emits the
  posture report (every human estimand `unavailable` / `basis=agent` /
  `no_human_reference`). `db`'s `er_rerun_login` change adds
  `sig_materialize_login` — a distinct LOGIN member of the existing
  NOLOGIN `sig_materialize` group, append-only INSERT surface,
  UPDATE/DELETE/TRUNCATE refused, no claim-spine write — and
  `ops/gcp/er-rerun.sh` runs the pre-authorised one-shot leg: `--check`
  plan-only, `--apply` window-/author-/dependency-/backup-/
  exactly-once-gated (a prior `ruleset_version='3-interim'` run exits
  42), `--verify` read-only; rollback is forward-only. The hosted leg is
  queued on `live:P34.43` + the AR-3 window (exit 42, recorded).

### Security

- **Strict response security layer — CSP meta ∩ header, HSTS,
  Permissions-Policy and the figure-SVG policy** (P36.19 / row 359;
  owner SIG-UI-096; cites SIG-UI-039, SIG-UI-040, SIG-ENG-042,
  SIG-UI-066, SIG-UI-D08; ADR-223) — the public surface now carries
  K0 §4.8's response posture end to end. Astro `security.csp` emits a
  per-page `<meta http-equiv="Content-Security-Policy">` with sha384
  hashes for each page's inline bootstrap (`script-src`/`style-src`
  `'self'` + tracked hashes, `script-src-attr`/`style-src-attr`
  `'none'`, no `'unsafe-inline'`/`'unsafe-eval'`); the build rewrites
  every T0 record/print page's meta to `default-src 'none'`. The nginx
  edge ships `ops/web/sig-security.conf` — HSTS
  `max-age=63072000; includeSubDomains` (no `preload`, a launch-row
  decision), the hash-independent CSP guards (`frame-ancestors`,
  `object-src`, `base-uri`, `form-action`, the `*-attr 'none'` pair)
  on every response, a `map`-keyed dedicated policy
  (`default-src 'none'; style-src 'unsafe-inline'; img-src data:;
  sandbox` + `nosniff`) on every standalone `.svg` under `/r/`, `/s/`
  and the latest view, and a Permissions-Policy granting
  `geolocation=(self)` on `/map/` only, deny elsewhere. Every inline
  `style=""` attribute moved to classes (`style-src-attr 'none'` needs
  no exception) and the map island's popups build DOM nodes for
  `.setDOMContent` — `check-unsafe-dom.mjs` fails `npm run check` on a
  reintroduced `innerHTML`/`setHTML`/`dangerouslySetInnerHTML`. A
  `securitypolicyviolation` e2e proves injected
  scripts/styles/attributes/`eval` are blocked and reported on the
  real pages.
- **Part VIII at-rest protective seal: counts-only screen + two-carrier
  deny set** (P34.49, TS-07; cites SIG-GOV-007, SIG-PUB-002, SIG-PUB-003,
  SIG-INGEST-045e, SIG-GOV-008, SIG-STORE-011; ADR-185 → ADR-203) — the
  evidence store gains a deterministic at-rest audit: committed
  field-name/shape/scoped-pattern rules screen every stored capture for
  the three F-406 byte classes, the nine I7 S1–S9 lane screens and the
  five SIG-PUB-002 never-publish categories, reporting **counts only** —
  a field name or value is never emitted. Flagged captures are
  protectively sealed (suppression, never deletion): an append-only
  `capture_seal` register (`seal_register` sqitch change; immutability
  trigger, no UPDATE/DELETE grant, the `capture_currently_sealed`
  latest-action helper, the INSERT-only `sig_seal_writer` role) plus a
  versioned `sig.seal-deny/1` deny set in the restricted bucket. The API
  evidence paths answer the SIG-EVID-010 sealed representation (existence
  + digest + claims only) for a currently-sealed capture whatever its
  stored tier, and `spine_export`'s evidence bindings drop every sealed
  capture with a fail-closed post-check and `sealed_bindings_*` counts.
  No byte is deleted or overwritten; true purge stays the operator's
  WV-11 action (ADR-181/189). Both live legs are queued exit 42 —
  nothing hosted ran.
- **Correction-intake + moderation hardening before any operational flip**
  (P34.37; cites SIG-FIND-006, SIG-FIND-008; C4 NEW-8/15/16/17/18/19/30,
  DR-C4-11/12) — the non-operational correction receiver and its curation
  moderation surface are made safe to operate: the PostgreSQL reviewer
  detail route serialises UUID/datetime values instead of 500ing; the
  operating gate additionally fails closed unless `[intake].owner` is set
  and `[intake].staffed = true` (an unowned, unstaffed receiver can never
  answer as operating); the abuse limiter keys on the edge-normalised
  client address via `[intake].trusted_proxy_hops` (a raw client-supplied
  `Forwarded`/`X-Forwarded-For` is never trusted on its own) and refused
  submissions no longer consume the allowance; demo curation tokens are
  refused whenever a DSN backs the service; the reporter status view shows
  the decided outcome, the approved public response and the
  correction/release link once published (new `intake_reporter_outcome`
  sqitch change — additive columns on `intake.report_public`, grants
  unchanged); a proposal's value shape is validated against its declared
  `object_type` at proposal time and re-checked against the resolved target
  type at bridge apply (`object_type_mismatch`); the intake form gains a
  viewport meta, a real category placeholder, contract-shaped deep-link
  prefill, and copy that no longer promises anonymous/one-click intake —
  the Round-11 public channel stays e-mail-only (WV-05/ADR-180), and
  `[intake].operational` remains `false` (B-8).

## [0.1.0] — unreleased (REL.1 marker skipped-by-operator; the current integration plan has no tag step — `docs/build/reports/p33.6-integration-plan/INTEGRATION_PLAN.md`)

First tagged snapshot of the Surveillance Infrastructure Graph (SIG): the complete
specification-driven build (Phases 0–18), the post-build capstone, reconciliation and
release-readiness chain (Phases 19–20), and the Phase-21 operationalization chain that runs the
system as composed local staging (Phases 21.1–21.9). Full detail:
[`docs/build/reports/RELEASE_NOTES_v0.1.0.md`](./docs/build/reports/RELEASE_NOTES_v0.1.0.md).

> **Post-Phase-21 chain (rows 67–198, dated history — see `docs/build/BUILD_INDEX.md`).** The chain
> continued through go-live and Round 10: the GCP deployment executed 2026-09-15
> (`docs/build/reports/GCP_DEPLOYMENT.md`, ADR-081); HG-01 was satisfied at an interim posture and
> HG-11 was granted 2026-09-27, so the public surface is **live at https://surveillancegraph.org**
> (launch record 2026-09-24; republish 2026-09-27 over a ~2.4M-claim spine — green-reviewed sources
> were fetched live); the national publish, hosted materialization, partner registries and the
> research-queue/records flows landed in P25–P31. **Round 10 (P32/P33)** added typed assertions +
> actual-capture bindings, the shared bitemporal contract, immutable `r/<publication>` release
> namespaces + compartmented FTS5 search, the coordinated workspace, durable anonymous intake
> (built; `operational=false` — answers `503 receiver_not_operating`), the three dossier packets
> (`mechanical_complete`, `review.status=not_run`), the shadow evaluator + preregistered human-eval
> campaign tooling (deferred spine — no human labels), the provisional-ruleset release candidate
> (**staging-only**; production exposure `D-R10-PUBLISH-1` remains OPEN), and the build-memory
> v2 projections/closeout machinery. GATE-ACCEPT signed 2026-09-28 accepting the register as
> presented: **36 owed obligations + `SIG-MEM-004`** remain — see `docs/tickets/DEFERRALS.md` and
> `docs/build/OPERATIONAL_READINESS.md` §(f).

> **Phase 21 — operationalization (local staging, no live sources).** SIG now runs as a composed
> system for one real jurisdiction (Oklahoma City), end-to-end, without fetching a live source: the
> `ingestion_permitted` gate stays fail-closed (HG-03 pending), so every connector run is
> fixture-backed replay/shadow. **No version bump:** this is staging, not live; go-public is gated on
> HG-01 + HG-11 (`docs/build/reports/PUBLICATION_CHECKLIST.md`), and the `0.2.0` "first public jurisdiction"
> cut-over is a later, human-gated decision. The chain (each a stacked PR):
>
> - **P21.1** (#56, ADR-063) — 27 rights-review packets + the registry `review-status`/flip rule; the 19-project Stage-0 outreach record. Nothing flipped (`loadable now: 0`).
> - **P21.2** (#58) — annotation-layer alignment tests; contradiction/coverage/task persistence ACCEPTED as compute-on-read under A5/HG-14 (shrunk, no new persistence).
> - **P21.3** (#59, ADR-065) — live connector wiring behind the gate: the `httpx` transport, the OCFL capture store, and `sig-connectors run --mode live|replay|shadow` (refuses a non-green live fetch, exit 3).
> - **P21.4** (#60, ADR-066) — runtime composition: `sig-ops up/status/down/seed` (`ops/docker-compose.yml`, PG18+PostGIS + API + static), the export-backed web data layer (`web/src/lib/data.ts`, `SIG_DATA_SOURCE=fixtures|export`), and `docs/build/tools/run_okc.sh` — the OKC dossier renders the 299-vs-190 contradiction from the export bytes (LD-V08 crossed).
> - **P21.5** (#61, ADR-067) — infrastructure: `sig-exports deposit` (Zenodo), `push` (object store/CDN, R2 with S3/CloudFront documented), `tiles` (real PMTiles), `.torrent` mirrors, `sig-ops egress-report`, and `sig-ops degraded` + the monthly keepalive (the $0-beyond-static posture). A1 ticked — no MapLibre island.
> - **P21.6** (#62, ADR-068) — the authenticated curation service (`sig-api serve-curation`, enabled only by `SIG_CURATION_ENABLED=1`, never on the public API) + the `/curate/**` progressively-enhanced web surface.
> - **P21.7** (#63, ADR-069) — contribution-back live: the MapRoulette client (dry-run without a key, sensitive tiers never pushed), the OSM changeset feed → `LeverageLedger`, the Organised Editing activity record, and opt-in aggregate-only onboarding timing.
> - **P21.8** (#64, ADR-070) — the first-class `data_driven` connector (release-as-unit-of-ingestion, per-agency aggregate rows only) and the coarse-international reference-capture path.
> - **P21.9** (#65, ADR-071) — the `pathways` connector (three per-family extractors) + the ADR-033-deferred layer-3/4 parser engines in `parsing/`, enforcing `procured` ≠ `deployed`; retires RISK-P17-03.

### Added
- **Domain model & ontology.** LinkML ontology + SKOS vocabularies + deterministic generators
  (`ontology/`); the append-only claim/evidence spine L0–L3 with RLS on PostgreSQL 18 + PostGIS
  (`db/`); the OCFL content-addressed evidence store (`evidence/`); EDTF temporal semantics, as-of
  functions, and PROV-O lineage.
- **Identity & resolution.** Jurisdiction/organization registries, deterministic and probabilistic
  entity resolution (`resolution/`), the deterministic `RESOLVE` engine and §29 reconciliation
  workflows (`reconcile/`), `Contradiction` as a first-class object, coverage/negative-space metrics
  and the research-task engine (`inference/`, `tasks/`).
- **Acquisition.** The eight-stage connector framework with rate-limit/robots, licence gate, replay
  and shadow mode (`connectors/`); twelve fixture-tested connectors (osm, atlas, flock_portal,
  audit_structural, accountability, procurement, records, france_belgium_procurement/records, and —
  added in Phase 21 — data_driven, coarse_international, pathways); the
  parsing stack (`parsing/`); the source registry with per-source rights records (fail-closed
  `ingestion_permitted` gate).
- **Delivery.** The read API with resolution envelope, as-of, dereferenceable IDs and `/changes`
  (`api/`) served over PostgreSQL; exports with per-compartment licence computation and the ODbL
  split (`exports/`); the zero-JS Astro web shell with dossier, static map, network explorer,
  watch/evidence, corrections and methodology surfaces (`web/`).
- **Governance & policy.** The executable crawler/licence/publication/threat policy package
  (`policy/`) and the prose governance/safety policies (`docs/governance/`).
- **Engineering.** uv workspace of 14 members (SIG-ENG-011/012); `make check` CI gate mirrored in
  `.github/workflows/ci.yml` (Python `python` job incl. `tests/db`; `web` job incl. e2e + a11y +
  licence + perf); PEP 751 `pylock.toml` export and CycloneDX SBOM targets.
- **Build memory & reconciliation.** `docs/build/` (planning ledger, build index, decision memo,
  coverage matrix over 671 requirement ids, capstone closure with the operator-signed 76-row
  ACCEPTED-deviations list, backlog, operational-readiness map, ticket-vs-spec reconciliation);
  Appendix F rebuilt to repository ADR numbering; ADR-001…062.
- **Release readiness (this ticket, P20.3).** `docs/build/tools/merge_dryrun.sh` (read-only merge
  dry-run), `docs/build/INTEGRATION_PLAN.md`, `docs/build/CI_STATUS.md`, version bump to `0.1.0`
  across all members, these release notes, `CITATION.cff`, `CHANGELOG.md`, `CONTRIBUTING.md`.

### Changed
- Spec reconciliation (P20.2): eight normative amendments (A1–A8) applied at `spec_src`; three
  requirement ids folded back (`SIG-UI-047`, `SIG-EVID-020`, `SIG-ENG-039`); spec id count 668 → 671.
- Capstone spine wiring (P19.4/P19.5): connector claims persist to PostgreSQL (`PgClaimSink`), the
  read API is served over PG (`PgReadStore`), entity resolution and the review queue run over PG, and
  the export gate honours `derivative_permitted`.

### Known limitations (conforming, tracked — refreshed 2026-09-28, P33.7)
- The `ingestion_permitted` gate stays **fail-closed per source**: green-reviewed sources are fetched
  live by the hosted scheduled jobs (the national publish's ~2.4M claims), while every source whose
  review record is not green still gets a refused `run --mode live` (exit 3). Sources left to review
  or unblock are the `D-SOURCES.*`/`D-JURIS.2-1`/`D-R10-SOURCES-1` rows of
  `docs/tickets/DEFERRALS.md`; publication gating is recorded in
  `docs/build/reports/PUBLICATION_CHECKLIST.md`.
- The Round-10 **provisional-policy release candidate is published to staging only**: production
  exposure (`D-R10-PUBLISH-1`), the hosted recovery/freeze (`D-R10-LIVE-1`) and the production
  candidate build (`D-P32.23a-1`) are open operator obligations. The public site currently serves the
  prior HG-11-signed national publish.
- The anonymous **correction receiver is built but not operating** (`[intake].operational=false`;
  `503 receiver_not_operating`; `D-P32.16-1`), and the independent **human-evaluation spine is
  deferred** (`D-R10-HUMAN-1`, `D-R6.1-EVAL` — no human labels exist; the evaluator runs shadow-only).
- Resolved since the capstone (Phase 21): `LD-V08` — the web now reads export bytes, not just
  committed fixtures, so the OKC dossier renders the contradiction from the export (P21.4); PG
  persistence of contradiction/coverage/task objects is ACCEPTED as compute-on-read under A5/HG-14
  (P21.2); the web curation surface shipped (A6 → P21.6). The `/map/` surface later gained an
  **opt-in MapLibre + PMTiles island** (P27.9, ADR-097; per-island budgets ADR-134/P32.15) — all
  other public content pages remain zero-JS.
- Deferred human-gated steps (not defects): the moderated onboarding usability study is landed but
  **not yet run** (HG-10 / `D-R10-USERS-1`); Zenodo/live-mirror deposits and live MapRoulette pushes
  refuse until their gates are ticked (HG-07/HG-08; `D-P21.5-1`, `D-P21.7-1`). All owed work is
  tracked in `docs/tickets/DEFERRALS.md` (36 rows + `SIG-MEM-004`) and `docs/build/BACKLOG.csv`.

[0.1.0]: https://github.com/SteveVitali/Eleutheria/releases/tag/v0.1.0
