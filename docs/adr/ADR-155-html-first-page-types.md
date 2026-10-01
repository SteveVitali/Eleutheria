# ADR-155: HTML-first page types

- **Status:** Accepted
- **Date:** 2026-10-01T04:33:54Z (decided by the operator at GATE-P — A-12, log round 5, 2026-10-01T04:09:43Z, completed by the B-22 batch line that adopted Preact and the URL viewport, log round 11)
- **Phase:** Round 11 / Stage B seed (T1)
- **Ticket:** SEED-11 (unit SEED-11a)
- **Decided by:** the operator, answers verbatim from `PD/feedback/RATIFICATION_LOG.md` (`PD` = `docs/build/planning/2026-09-30-next-phase/`):
  A-12 **"HTML-first page types (Recommended)"** (round 5, 2026-10-01T04:09:43Z; `decision_catalog.csv` D-K0-1 = a);
  B-5/B-17/B-22/B-23/B-26 batch **"Accept all five (Recommended)"** (round 11, 2026-10-01T04:33:54Z), whose B-22 line carries D-K0-2 (Preact replaces React on public surfaces), D-K0-3 (the rounded map viewport in URLs, with the precision rule) and D-K0-5 (`application/ld+json` blocks are data) as recommended.
  Related, decided elsewhere: D-K0-4 (tiles and basemap on the R2 zero-egress origin) rides A-3 **"Yes, all three (Recommended)"** (round 2, 2026-10-01T03:53:59Z); D-K0-6 (the global graph as aggregated overviews) rides A-11 (ADR-158)
- **Requirement ids:** SIG-UI-036 and SIG-UI-050 amended "zero-JS-on-content-pages → HTML-first page types (K0 §7 text; ADR-155)" (plan §6.3; the `spec_src` amendment is SEED-12's). Drafts SIG-UI-D01…D10 (K0 §9), adopted by the K13 set as UXR-A01 with UXR-02 (registry fields) and UXR-35 (the T2 set stays three) — final ids assigned by PLAN-11C (plan §6.2). *Agent note:* K0 §7 also drafts amendments to SIG-UI-013/021/022/037/038/039/040/041/047 and SIG-FIND-004/005 plus two new requirements (CSP; citable explore state); which of those land, and under which ids, is SEED-12's and PLAN-11C's call, not this ADR's. The replacement text for root `AGENTS.md` gotcha 6 and `web/AGENTS.md` gotcha 1 is K0 §7.1–§7.2 (applied by another T1 unit)
- **Spec:** §40 (SIG-UI-036, SIG-UI-050 amended to HTML-first page types; SEED-12); the SIG-UI-D01…D10 drafts land with
  the K13 families (PLAN-11C)
- **Supersedes:** the named-island rule of **ADR-091 §3–4** (Decision items 3 "the public islands are exactly three" and 4 "the island allowance … every other public page keeps script bytes `0`") and of **ADR-097 §2–3 and §6** (Decision items 2 "exactly three, each `client:only="react"`", 3 "every other public page keeps script bytes `0`" and 6 "a fourth public island … changes the named set only by a new ADR").
- **Amends / qualifies / extends:** **extends ADR-134** (`sig.workspace-state/2` as a superset of `/1`, the rounded viewport in the URL — ADR-134's own revisit trigger (a) — and per-type budgets in place of per-island ceilings); **leaves ADR-068** (`/curate/**`) **unchanged**. Scope per K0 §6 as the plan keeps it (Appendix B row 27; S6r agreed): the log's interpretation shorthand "superseding ADR-068/091/097/134" is not the decision. Appended status lines on those landed ADRs are written by SEED-11d, not here
- **Sources:** plan §5.7, §6.2, §6.3, Appendix B row 27; `PD/design/K0-interactive-architecture.md` §0–§4 (esp. §4.1–§4.8, §4.12), §6 (its ADR draft), §7 (amendments and guidance rewrites), §9–§11; `PD/data/decision_catalog.csv` (D-K0-1…6); `PD/data/k13_requirements.csv` (UXR-02, UXR-35, UXR-A01); landed ADR-068, ADR-091, ADR-097, ADR-134 (read for scope)
- **Recorded:** 2026-10-01T07:37:25Z by Claude Code (Opus 5.5), harness `claude-code/claude-opus-5-5/subagent` — agent-drafted record of the operator's decision; operator words quoted verbatim from `PD/feedback/RATIFICATION_LOG.md`

## Context

The public web surface is zero-JS except a named set of islands. ADR-091 (DECISION-SPA = B, operator-ratified
2026-09-22) chose a static content core plus exactly three React islands — map, network graph, search — and ADR-097
built them (`client:only="react"`, each over a no-JS fallback; SIG-UI-050), extending ADR-068's `/curate/**` island
allowance. ADR-134 gave the three islands one URL-state contract (`sig.workspace-state/1`) and measured per-island
ceilings, and deliberately kept the map viewport out of the URL. Root `AGENTS.md` gotcha 6 and `web/AGENTS.md`
gotcha 1 enforce "no `<script>` on public content pages; the named islands are the bounded exceptions".

The operator asked to "think and research and reason carefully about perhaps breaking with our no-JS constraints"
(U-003), for journalists to "really truly explore the knowledge graph … always with full explicit transparent
evidence/lineage" (U-005), and for a beautiful, useful, intuitive site (U-007), within ≤ $300/month (U-008). K0
(2026-09-30) measured what the rule bought and what it cost:

- **What it bought still holds** — archivability, accessibility, citation stability, print for the design-center
  advocate, real-device performance, machine readability, a minimal security surface (K0 §1.2). Static content pages
  score Lighthouse 1.0 with 7–24 KB transferred (C2 §6.2, cited in K0 §0).
- **The failures sit on the JS islands, not the static pages:** `/map/` mobile performance 0.86 and 816 KB in
  production, CLS 0.311 on `/network/` and 0.326 on `/search/`; the no-JS map fallback grew to a 3.46 MB page; search is
  a client filter over a 500-row sample; the graph is a 131-node UUID star (K0 §1.3; F-115, F-171, F-101, F-102).
- **The rule's own costs are narrow:** no-JS filtering needs one pre-rendered route per sort × facet; embedded dossier
  visuals (U-003.6) would need a new island and ADR per page; a map view cannot be shared or cited; and the island
  allow-list is enforced by hand-listed routes, so a new page is unchecked by default (K0 §1.3, NEW-4).
- **Most of the operator's asks need no new JS** — seven of the eleven U-003 asks are blocked by data, labels and
  information architecture (K0 §1.4).

K0 compared four options — (a) static core + richer bounded islands, (b) progressive enhancement everywhere with
per-page budgets, (c) static content + app-like explore surfaces, (d) a full SPA — and recommended (c) built with (b)'s
rules (K0 §3).

## Decision

**The operator adopted HTML-first page types (A-12 = a; D-K0-1).** The rule in one sentence (K0 §0, agent-drafted):
*every public route has a declared page type; the record and print types ship no executable script; content pages may
load small, approved enhancements but must show every fact with JS off; explore surfaces may be app-like but must
encode their state in the URL, paint server-side first, and link to a no-JS equivalent — all inside per-type budgets
measured in CI on real-sized data.*

1. **A page-type registry classifies every public route** (`web/src/lib/page-types.ts`): **T0 record & print**
   (`/r/**`, every `…/print/`, `/dispute/`, `/intake/**`, API `format=html`, tombstones, release data listings),
   **T1 content** (home, dossiers, entity, source and sources pages, research queue, watch, evidence, methodology,
   releases, data, status, about — and the same routes under `/s/<pub>/` and `/v/<pub>/`), **T2 explore** (`/map/`,
   `/explore/` — `/network/` redirects — and `/search/`), **T3 tools** (`/curate/**`, ADR-068, never published). **A
   built route that matches no pattern fails the build** (fixes the fail-open allow-list).
2. **T0 pages contain no `<script>` element.** **T1 pages render every fact with JS off** (JS-off `main` text equals
   JS-on text, minus `[data-enhancement]`) and may load approved framework-free enhancement elements — `type=module`,
   never render-blocking — with heavier code only after an explicit user action. **T2 surfaces may be applications**,
   with a server-rendered first paint in a reserved box and a complete no-JS equivalent (tables, lists, GET forms,
   static SVG). **The T2 set stays exactly three**; adding a T2 surface, a browser runtime dependency or raising a
   budget is an amendment by a new ADR, never ad hoc (UXR-35).
3. **Budgets are declared per type** (K0 §4.3; initial executable JS, gzip): T0 **0**; T1 **≤ 20 KiB** (≤ 40 KiB per
   enhancement after a user action); T2 map **≤ 360 KiB**, graph **≤ 120 KiB**, search **≤ 60 KiB** — with document,
   total, per-interaction data, Lighthouse, LCP, CLS and TBT limits per type. They live in
   `web/tests/e2e/page-budgets.json` (`sig.page-budgets/1`, superseding `island-budgets.json`), `lighthouserc.json` is
   generated from the registry and budgets, and both are measured in CI on a real-sized synthetic national build (no
   real agency or vendor names) and on the real release before promotion.
4. **Every citable interactive state is a URL** under **`sig.workspace-state/2`**, a superset of ADR-134's `/1` (every
   `v=1` link keeps working). It adds `sort`/`dir`, the graph scope (`overview`, `hops`, `edge`, `expand`) and the
   **map viewport `at=<z>/<lat>/<lon>`, rounded to the precision the zoom supports and never finer than the published
   tier (§19.4)** (D-K0-3). "Cite this view" yields the snapshot-pinned `/s/<pub>/…` form; a stateful URL opened without
   JS says so and links its static equivalent; parameterized T2 URLs are `noindex,follow` with a canonical link. No
   client router: ADR-134's history adapter stays the only history-aware code.
5. **Every visualization has a build-time static rendition** (SVG plus a table or list) in the place it appears; JS
   enhances that box in place and never fills an empty box. `client:only` is not used on public pages.
6. **Public islands use Preact; React leaves the public bundles** (D-K0-2). T1 enhancements are framework-free custom
   elements (`<sig-table>`, `<sig-typeahead>`, `<sig-cite>`, `<sig-activate>`), following the least-power ladder HTML →
   CSS → custom element → Preact island (K0 §4.6).
7. **Browser runtime dependencies are allow-listed** (`web/runtime-deps.json`: MapLibre GL, PMTiles, Protomaps basemap
   styles, Preact, sigma, graphology, MiniSearch); anything else needs an amendment with a measured size. Exact pins,
   the ≥ 7-day publication rule and OSI licence checks (SIG-UI-039) stay.
8. **No third-party origins at runtime**: tiles, basemap, glyphs, gazetteer and search are served by SIG; a strict CSP
   (hashes; no `unsafe-inline`/`unsafe-eval`) and HSTS go on every public response. `application/ld+json` blocks are
   data, not code, and are allowed on T1 (D-K0-5; whether to ship them is J3's D-J3-7).
9. **WCAG 2.2 AA holds with JS on and off**; canvas content is reachable as focusable list items; reduced motion is
   honoured.
10. **Explore surfaces read only release-pinned data** (static files, PMTiles, release-namespaced API routes);
    live-spine routes never feed a public page.
11. **Unchanged:** ADR-068's `/curate/**` (T3, loopback, never published; the publish strip stays); ADR-091's rejection
    of a full SPA (its §5) and SIG-UI-036/037's rationale; ADR-097's ODbL/OSM attribution on the map (its §5) and its
    no-JS-fallback invariant, which this ADR generalises from three islands to every page type.

Implementation rows (plan §5.7; `PD/data/round11_plan.csv`): P35.50 (registry, route discovery, `script-policy` and
no-JS parity specs), P35.51 (page budgets, generated LHCI, real-sized synthetic fixture), P36.19 (CSP, HSTS,
Permissions-Policy), P36.20 (enhancement kit), P36.21 (`sig.workspace-state/2`, cite-this-view), P36.40 (`/search/`
rewrite), P37.26–P37.27 (graph explorer), P37.29 (in-place map activation on dossiers), P37.61 (T1 table and filter
enhancements).

## Consequences

- **Positive:** the operator's explore journeys (map with a basemap, navigable overview graphs, typeahead and faceted
  search) become possible without giving up the printable, citable, archivable record; embedded dossier visuals become
  legal and print as static renditions; filtering stops depending on pre-rendered route products; enforcement becomes
  fail-closed (an unclassified route fails the build); a map view becomes shareable and citable at a bounded precision.
- **Negative:** more code to maintain (a component kit and three apps); JS-on/JS-off parity tests on every T1 page; a
  React → Preact migration of the three islands; a CSP that constrains inline styles; CI needs a real-sized build
  (longer runs).
- **Neutral:** the map's initial script weight falls (≈ 497 KB → ≤ 360 KiB gzip; K0 §0) once the duplicated worker
  chunk is removed; T2 map performance moves from an advisory warn at 0.5 to an error at 0.75.
- **Records:** the per-island ceilings of ADR-134 §6 give way to per-type budgets; ADR-091's and ADR-097's
  "every other public page keeps script bytes `0`" no longer holds for T1 pages, which may ship ≤ 20 KiB of
  non-blocking enhancement. *Agent observation (labelled):* in effect this also narrows two neighbouring clauses
  that K0 §6 does not list — ADR-091 Decision 1's "Content pages ship **no** `<script>`" and the React choice of
  ADR-091 Decision 2 / ADR-097 Decision 1 (Preact replaces React on public bundles, D-K0-2). This ADR keeps the
  ratified K0 §6 scope and does not widen it; whether those clauses also get an appended status line is left to
  SEED-11d and the orchestrator.

## Alternatives considered

- **Keep three islands** (A-12's other option; K0 option (a)): not chosen. It cannot put a map or network on a dossier
  (U-003.6) without a new island and ADR per page, keeps the no-JS filtering combinatorics, and its allow-list already
  fails open for new pages.
- **Progressive enhancement everywhere without app surfaces** (K0 option (b) alone): rejected for the map and graph,
  whose core interaction is scripted; pretending otherwise produced the 3.46 MB "fallback".
- **App-like explore surfaces without (b)'s rules** (K0 option (c) alone): rejected — content pages would stay frozen
  and explore apps would drift into unbudgeted, uncitable shells.
- **A full SPA** (K0 option (d); ADR-091 C): rejected — archivability, citation, crawlability and print regress, it
  contradicts the operator-ratified ADR-091, and it would move SIG from static files to a runtime service.
- **Keep React on public pages** (D-K0-2's alternative): rejected — Preact has the same API shape at ≈ 5.4 KB against
  React 19's ≈ 65.7 KB runtime (K0 §2.1).
- **Libraries rejected by default** (K0 §4.7): cytoscape (≈ 3.7× sigma), client-side SQLite search (≈ 322 KB WASM),
  Pagefind for 10⁵–10⁶ entity pages, Leaflet (a second map stack), third-party tile or geocoding services, live-spine
  data on explore surfaces, a national node-link "hairball" (SIG-UI-021).

## Revisit trigger

- A T2 surface needs more than 1.25× its budget, or misses its Lighthouse floor on the real release for two
  consecutive releases.
- A fourth T2 surface is proposed, a browser runtime dependency outside `runtime-deps.json` is needed, or any budget
  must rise — each needs a measured report and a new ADR amending this one.
- A requirement needs non-release (live) data on a public page.
- A graph view needs more than ~3,000 labelled nodes, or a renderer that requires WebGL 2 only.
- Search needs capabilities the API FTS5 path and the typeahead shards cannot give (a measured failure), or search
  cost exceeds $50/month.
- A runtime dependency needs `unsafe-eval`/`unsafe-inline` or a third-party origin.
- A URL state would carry location precision finer than the published tier (§19.4) — a hard stop, not a code change.
- The operator asks for accounts, personalization or an SPA — a new ADR superseding this one and SIG-UI-036/037.
- `/curate/**` is proposed for publication — that reopens ADR-068, not this ADR.
