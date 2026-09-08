# AGENTS.md — `web/` (public web surface)

## Purpose

The SIG public web surface: **Astro, static-first, zero-JS-by-default** (SIG-UI-036/037). This is
the **only** package where TypeScript is allowed (SIG-ENG-010); it consumes export artifacts and the
epistemic visual language. Node `>=20` (`package.json` `engines`).

## Build & Test

Run from `web/` (these are npm scripts, not `make` targets):

| command | what it does |
|---|---|
| `npm run check` | the package gate: `typecheck` → `test:unit` → `build` → `check:licenses` → `test:e2e` |
| `npm run typecheck` | `astro check` |
| `npm run test:unit` | `vitest run` |
| `npm run test:e2e` | `playwright test` (chromium + no-JS; axe WCAG 2.2 AA) |
| `npm run check:perf` | `lhci autorun` (Lighthouse budgets, `lighthouserc.json`) |
| `npm run dev` / `build` / `preview` | astro dev server / static build / preview server |

## Critical gotchas

1. **Zero-JS budget is a hard contract.** Pages must render with **no `<script>` tags** by default
   and stay within the performance budget; e2e and `lhci` assert this. Don't add client-side JS to a
   page without an explicit island decision — it will fail `test:e2e`/`check:perf`.
2. **Accessibility is enforced, not aspirational.** Playwright runs `@axe-core/playwright` for
   **WCAG 2.2 AA** on new pages; a violation fails the suite.
3. **Licenses are checked.** `check:licenses` (`scripts/check-licenses.mjs`) fails the gate on a
   disallowed dependency license.

## Do / Don't

- **Do** run `npm run check` before committing web changes; keep pages static by default.
- **Don't** write TypeScript outside `web/`; don't introduce runtime JS that breaks the zero-JS or
  a11y budgets.
