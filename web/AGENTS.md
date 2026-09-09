# AGENTS.md — `web/` (public web surface)

## Purpose

The SIG public web surface: **Astro, static-first, zero-JS-by-default** (SIG-UI-036/037). It consumes
export artifacts and the epistemic visual language; this is the **only** package where TypeScript is
allowed (SIG-ENG-010). Node `>=20` (`web/package.json` `engines`). Nearest-file-wins: this file adds
to the root `AGENTS.md`.

## Key Files

| File | Lines | Purpose |
|---|---|---|
| `web/package.json` | ~40 | npm scripts + the pinned toolchain (astro, playwright, lhci) |
| `web/lighthouserc.json` | ~50 | the performance/zero-JS budget matrix (public vs `/curate/**`) |
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

1. **Zero-JS budget is a hard contract.** Public pages must render with **no `<script>` tags** and
   stay within budget; `web/lighthouserc.json` asserts script size `0` and total ≤ 150 KB, and
   `test:e2e` asserts the no-JS baseline. Adding client JS to a public page fails
   `test:e2e`/`check:perf`. The `/curate/**` island allowance is the only exception (ADR-068).
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
- Don't add runtime JS that breaks the zero-JS, performance, or a11y budgets on public pages.
