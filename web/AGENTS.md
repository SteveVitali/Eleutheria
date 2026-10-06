# AGENTS.md — `web/` (public web surface)

## Purpose

The SIG public web surface: **Astro, static-first, zero-JS-by-default** (SIG-UI-036/037). It consumes
export artifacts and the epistemic visual language; this is the **only** package where TypeScript is
allowed (SIG-ENG-010). Node `>=22.12.0` (`web/package.json` `engines`, raised by P27.9 for the
island toolchain). Nearest-file-wins: this file adds to the root `AGENTS.md`.

## Key Files

| File | Lines | Purpose |
|---|---|---|
| `web/package.json` | ~40 | npm scripts + the pinned toolchain (astro, playwright, lhci) |
| `web/lighthouserc.json` | ~100 | the performance budget matrix: public zero-JS content block, `/curate/**` (ADR-068), the three public islands `/map/`/`/network/`/`/search/` (ADR-097) with per-island script/total ceilings (P32.15, ADR-134) |
| `web/src/islands/` | ~n/a | the three public React islands (`MapIsland`, `NetworkIsland`, `SearchIsland`), each `client:only` over a preserved no-JS fallback (SIG-UI-050) |
| `web/src/lib/data.ts` | ~n/a | the data layer: `SIG_DATA_SOURCE=fixtures\|export` switch |
| `web/scripts/check-licenses.mjs` | ~n/a | the OSI-only dependency licence gate |

## Build & Test

Run from repo root with `npm --prefix web run <script>` (or from `web/` with `npm run <script>`):

| command | what it does |
|---|---|
| `npm --prefix web run check` | the package gate: `typecheck` → `test:unit` → `build` → `check:licenses` → `test:e2e` |
| `npm --prefix web run typecheck` | `astro check` |
| `npm --prefix web run test:unit` | `vitest run` |
| `npm --prefix web run test:e2e` | `playwright test` (chromium + no-JS; axe WCAG 2.2 AA) |
| `npm --prefix web run check:perf` | `lhci autorun` (Lighthouse budgets, `web/lighthouserc.json`) |
| `npm --prefix web run dev` / `build` / `preview` | astro dev server / static build / preview |

## Code Conventions

- Pages are `.astro`, static by default; client JS only via an explicit island decision.
- TypeScript stays inside `web/`; the epistemic design tokens are the shared visual vocabulary.

## Critical Gotchas

1. **Page types, not islands (ADR-155).** Look up the route's type in the page-type registry
   (src/lib/page-types.ts, added by P35.50) before adding any client code. T0: none. T1: a
   framework-free custom element from src/elements/ that upgrades existing markup (≤ 20 KiB gzip
   initial). T2: a Preact island mounted with `client:visible`/`client:idle` into a reserved box
   that already holds the static rendition — never `client:only`. Budgets: tests/e2e/page-budgets.json
   (P35.51). Never render a data label with `innerHTML`. Runtime dependencies: runtime-deps.json
   only. **Until P35.50/P35.51 land,** the current contract binds: content pages ship no
   `<script>` (`web/lighthouserc.json` asserts script size `0`), and only `/curate/**` (ADR-068)
   and the three ADR-097 islands `/map/`, `/network/`, `/search/` carry client JS, within
   `web/tests/e2e/island-budgets.json`; adding client JS anywhere else fails
   `test:e2e`/`check:perf`.
2. **Accessibility is enforced, not aspirational.** `test:e2e` runs `@axe-core/playwright` for
   **WCAG 2.2 AA**; a violation fails the suite.
3. **Dependency licences are gated.** `check:licenses` (`web/scripts/check-licenses.mjs`) fails on a
   non-OSI dependency licence (excludes CC-BY-NC / source-available / BUSL).

## Terminology

- **Island** — an explicitly-opted-in interactive component in an otherwise static page.
- **`SIG_DATA_SOURCE`** — selects committed fixtures vs real export bytes for the data layer.

## Do

- Run `npm --prefix web run check` before committing web changes; keep pages static by default.
- Drive the data layer through `web/src/lib/data.ts` (`fixtures` locally, `export` from real bytes).

## Don't

- Don't write TypeScript outside `web/`.
- Don't add runtime JS that breaks the zero-JS budget on public content pages, or the per-island
  script/total + a11y budgets on `/map/`, `/network/`, `/search/`, `/curate/**`.
