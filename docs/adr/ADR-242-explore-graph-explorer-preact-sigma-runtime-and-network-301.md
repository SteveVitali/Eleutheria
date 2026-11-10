# ADR-242 — The `/explore/` T2 graph explorer: Preact + sigma runtime, react retirement, and the `/network/` 301

- Date: 2026-11-09
- Status: accepted
- Ticket: P37.26 (Round 11 / P37, row 450; SIG-UI-119, SIG-UI-120, SIG-UI-121)
- Base: `r11/P37.25-overview-builder-b`
- Related: K2 GX-09a (the graph-explorer first wave), K13 §7 W3 + §8 J2,
  UXK0-6 (the Preact migration epilogue this completes), ADR-155 (amended —
  a browser runtime dependency is admitted), ADR-097/ADR-134 (the named-
  island + workspace-state posture the explorer inherits),
  `sig.page-budgets/1` (P35.51 — the `t2Surfaces.graph` budget this surface
  is measured against, never raised), `sig.workspace-state/2` (P36.21),
  `sig.graph-overview/1` + `sig.graph-components/1` (P37.24/P37.25 — the
  documents the island reads).

## Context

K2 GX-09a ships the interactive graph explorer's first wave: the
P37.17-registered `/explore/` T2 surface opens on the `sig.graph-overview/1`
+ `sig.graph-components/1` documents P37.24/P37.25 land. The interim
`/network/` island is retired and 301s to
`/explore/?v=2&overview=access`. ADR-155's rule binds: adding a browser
runtime dependency to a public bundle needs a new ADR amending it. The
explorer's renderer needs two.

## Decision

1. **`sigma` + `graphology` join the browser runtime allow-list**
   (`runtime-deps.json` `browser`), amending ADR-155's browser-dependency
   roster: sigma is the T2 explorer's WebGL renderer, graphology the graph
   model it draws. Both were `build_time_only` reservations under K0 §4.7;
   this ADR admits them to shipped bundles.
2. **React retires from the public surface.** `@astrojs/react`,
   `react`/`react-dom` and their types leave `package.json`; the
   `transitional` react seats in `runtime-deps.json` close. Preact
   (`@astrojs/preact`, `src/islands/**` + `src/components/**`) is the only
   island runtime — UXK0-6's last migration.
3. **The bundle-content gate enforces it.** `check-runtime-deps.mjs` scans
   every emitted `dist/_astro/*.js` for a react/compat signature
   (`react-dom`, `createPortal`, `preact/compat`, the shared-internals
   marker) and fails the build on a hit — react can never re-enter a public
   bundle silently.
4. **`/network/` → 301 `/explore/?v=2&overview=access`.** The access
   overview is the successor surface; old `view=network` workspace URLs
   still parse (`sig.workspace-state/2` keeps the `network` view name) and
   selector query params merge onto the target's own query. The page-type
   registry drops the `/network/` row — a stray emission fails the build
   rather than silently classifying.
5. **The no-JS equivalent stays T2-honest.** `/explore/`'s SSR first paint
   carries the overview index, the default overview's static figure +
   bounded adjacency preview, the access-edge lists and the precomputed
   access-path hop lists (the registry's `sections` equivalent); the
   Preact + sigma island mounts inside a reserved box and stateful URLs
   carry the JS-off notice per `sig.workspace-state/2` (SIG-UI-119's
   round-trip; SIG-UI-120's hop-list path answers; SIG-UI-121's centrality
   abstention is a visible note, never a missing disclosure).

## Consequences

- `sigma`/`graphology` bytes count against `t2Surfaces.graph`'s
  `jsInitialBytes`/`totalInitialMaxBytes` (`page-budgets.json`); the
  `budget.spec.ts` representative for `graph` moves to `/explore/` and the
  wire measurement decides — a real overage lands in `measured_gaps`,
  never a raised ceiling.
- `SITE_NAV` in `exports/release_pages.py`, the ops `public_routes.toml`
  lists, the post-cutover route fixtures and `ROUTES.csv` (R17 retired /
  R37 resolves) follow the rename; archive-chrome nav links to `/explore/`.
- Root `AGENTS.md` gotcha 6 and `web/AGENTS.md` name `/explore/` in the
  T2 set; `/network/` survives only as the redirect source and the
  workspace-state view name.

## Revisit trigger

1. A second explorer wave (GX-09b) applies the reserved `edge`/`expand`/
   `hops`/`path`/facet params — the allow-list and the budget shape are
   re-examined against what the wave actually needs.
2. Sigma or graphology versioning forces a renderer swap, or a lighter
   renderer lands (canvas/SVG) — the admission is re-decided, not carried
   silently.
3. A route renames or re-splits `/explore/` (e.g. per-overview sub-routes)
   — the 301 lattice, the registry row and `SURFACE_PATHS.graph` move
   together.
