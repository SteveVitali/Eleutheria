# ADR-097 — Three public interactive islands (map, network graph, search) extend the ADR-068 island allowance

- **Status:** Accepted
- **Phase / ticket:** Phase 27 / P27.9 (`docs/tickets/P27.9__interactive-islands.md`) — the "interactive later" fast-follow. The as-built record of the operator-ratified **ADR-091** (DECISION-SPA = B).
- **Date:** 2026-09-22
- **Related:** **ADR-068** (the `/curate/**` island + loopback-auth exception this extends), **ADR-091** (DECISION-SPA = B, the ratified decision this implements), ADR-014 (Astro static-first), ADR-018 (MapLibre GL for the web map), ADR-051 (LD-F09 — the deferred interactive-map island), **SIG-UI-036/037** (zero-JS static-first + no-JS core), **SIG-UI-047 / A1** (§40 — the interactive map island as a MAY over the zero-JS default, revisited here), **SIG-UI-050** (the new no-JS-fallback invariant this ADR lands), SIG-UI-038/SIG-GEO-012/013 (self-hosted PMTiles + OSM attribution), §19.4 (coordinate precision), §42.3 (ODbL attribution), `web/lighthouserc.json` (the per-surface budget matrix), `D-P27-SPEC-1` (the §40 fold-back this closes).

## Context

The public surface is **zero-JS, static-first, archivable and WCAG-2.2-AA by default**
(SIG-UI-036/037, ADR-014): `web/lighthouserc.json` asserts script bytes `0` and total ≤ 150 KB on
public pages, and `test:e2e` enforces WCAG 2.2 AA + a no-`<script>` baseline. The **only** island
exception to date is `/curate/**` (ADR-068) — and even that shipped no client JS in practice.

ADR-091 ratified **DECISION-SPA = B** — a static content core plus a small, named set of opt-in
React islands — over both a full-SPA rewrite (rejected: it overturns archivability, a11y-by-default
and citation-stability) and a rich-static-only redesign (kept as the fallback). ADR-091 named the
three islands (map, network graph, search), said each MUST keep its no-JS fallback, and deferred the
§40 spec_src fold-back to the implementing ticket (P27.9) per SIG-ENG-039. The spec already
anticipated the map island: **SIG-UI-047 (MAY)** permits an interactive MapLibre map as progressive
enhancement over the zero-JS static map (**A1**), with the build "deferred to Phase 21". P27.9 is
that build — arriving in Phase 27 — for all three islands, so SIG-UI-047/A1 needs a recorded revisit,
and the island allowance (ADR-068) needs extending from `/curate/**` to the three public islands.

## Decision

1. **React arrives via `@astrojs/react`** (pinned, published ≥ 7 days). Components render to **static
   HTML at build time by default**; client JavaScript ships **only** for a component carrying an
   explicit `client:*` directive — which in the public surface is exactly the three named islands.
   Adding client JS to any other public page still requires a greppable directive, so archivability
   stays structural (SIG-UI-036).
2. **The public islands are exactly three, each `client:only="react"` and each layered over a
   preserved no-JS fallback** (progressive enhancement, never replacement):
   - **Map** (`/map/`) — MapLibre GL over the self-hosted static PMTiles / `/map/style.json` contract
     (SIG-UI-038), drawing **only the already tier-reduced, published points** (§19.4 — never
     full-precision geometry; tier-3/point-less assets stay jurisdiction indicators). It *realises*
     SIG-UI-047. Fallback: the located-assets **table** (SIG-UI-037).
   - **Network graph** (`/network/`) — an interactive ego explorer (SIG-UI-021/022 — never a national
     hairball), every centrality statistic carrying its inline ER-quality disclosure (SIG-UI-023).
     Fallback: the edge/path **lists**.
   - **Search** (`/search/`) — a client filter over the published index (dossiers, map sites,
     sources). Fallback: the static **browse index** (links to the dossier index, the map, the
     per-source freshness table).
3. **The ADR-068 island allowance is extended** from `/curate/**` to those three public islands.
   Each island *page* gets its own `lighthouserc.json` budget row (WCAG 2.2 AA enforced as an error;
   performance advisory; script/total size **not** asserted — a hydrated MapLibre/React island ships
   JS by design), exactly as `/curate/**` has. **Every other public page keeps script bytes `0`** and
   its zero-JS budget, proven by an e2e no-`<script>` sweep over every non-island public page.
4. **A new invariant, SIG-UI-050 (MUST):** every public interactive island MUST preserve a
   fully-usable no-JS fallback (the tabular/list/browse equivalent SIG-UI-037 requires); the island is
   never a hard dependency of any core page. SIG-UI-047/A1 is annotated to note the three islands now
   realise it (the map build is no longer merely deferred).
5. **ODbL/OSM attribution is shown on the map** in the interactive renderer as in the static context
   (§42.3, SIG-GEO-013) — a licence obligation, not a courtesy.
6. **A full SPA stays rejected** (ADR-091 C); a fourth public island, or the removal of any
   fallback, changes the named set **only by a new ADR** (SIG-ENG-003), never ad hoc.

## Consequences

- The content core stays zero-JS, archivable, WCAG-2.2-AA and citation-stable; only `/map/`,
  `/network/` and `/search/` ship a hydration `<script>`. This is enforced, not asserted: the e2e
  sweep fails if any other public page gains a script, and `lighthouserc.json` keeps script size `0`
  on every non-island page.
- `@astrojs/react` (a build integration, in `devDependencies`) plus runtime `react`/`react-dom`/
  `maplibre-gl`/`pmtiles` (all OSI-licensed — MIT/BSD-3, SIG-UI-039) are added to `web/`.
- The islands read the P27.4 export data at **build time** through the existing data seam (ADR-066)
  and receive it as serialized props — no page fetches a live API in the browser; the map never has
  access to full-precision coordinates.
- Island pages are measured against their own budget; their a11y is still enforced at 100 (axe WCAG
  2.2 AA runs on all three). Performance on the map page is advisory (MapLibre is heavy) — the
  archivable no-JS table remains the guaranteed-fast, citable surface.
- Lands the §40 spec_src fold-back (SIG-UI-050 + the SIG-UI-047/A1 revisit annotation), closing the
  final share of `D-P27-SPEC-1`.

## Alternatives considered

- **A — rich static redesign, no islands** (ADR-091 A). Fully archivable but forgoes the interactive
  map/graph/search the operator wants. Retained as the fallback if an island cannot meet its a11y
  budget — hence the hard rule that the no-JS fallback is never removed (SIG-UI-050).
- **C — full from-scratch React SPA** (ADR-091 C). Rejected — overturns SIG-UI-036/037,
  archivability, a11y-by-default and citation-stability for a net loss on the properties that matter
  most to a surveillance-accountability record.
- **Serving the interactive map basemap from a third-party tile CDN.** Rejected (SIG-UI-038): the
  renderer is self-hosted maplibre over the static PMTiles contract; a CDN must never be a hard
  dependency.
- **Rendering full-precision points in the interactive map.** Forbidden (§19.4): the island is fed
  only the tier-reduced published coordinates the table already shows.

## Revisit trigger

- An island's no-JS fallback becomes unmaintainable, or a public island breaks the a11y / archival /
  performance contract in CI (a11y < 100 on the island page, or a `<script>` appears on a non-island
  public page) — re-gate or remove that island by a new ADR.
- The operator later wants a full SPA — a new ADR **superseding this one and SIG-UI-036/037** (with
  the archivability / a11y mitigations spelled out) is required; never a silent stack swap.
- A **fourth** public island is proposed — extend the allowance by a new ADR amending the named set
  (map / graph / search), not ad hoc.
- The interactive map is asked to render individual points at a precision finer than the published
  tier (§19.4), or to drop the ODbL/OSM attribution (§42.3) — both are hard stops requiring a
  governance decision, not a code change.
