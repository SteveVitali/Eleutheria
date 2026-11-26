# web/ — the SIG public web shell + epistemic visual language

The Phase-15 public surface. TypeScript is confined to this package (SIG-ENG-010).
It is built with [Astro](https://astro.build) as a **zero-JS-by-default,
static-first** framework (SIG-UI-036): with no explicit `client:*` directive
on a public content page, the build ships **no client JavaScript** there
(`web/lighthouserc.json` asserts script size 0 over them), so the pages are
archivable by default. Client JS is budgeted by **page type** (ADR-155): the
registry `src/lib/page-types.ts` classifies every emitted route — T0 record &
print ships no script, T1 content may load only allow-listed module entries
(`web/tests/e2e/t1-module-entries.json`), and the three opt-in public T2
islands are the standing exception — `/map/` (MapLibre + PMTiles), `/explore/`
and `/search/` (ADR-068/097/134/242; `/network/` 301s to
`/explore/?v=2&overview=access` since P37.26) — each with a named no-JS
fallback and a wire-measured budget (`web/tests/e2e/page-budgets.json`,
SIG-UI-050); the authenticated `/curate/**` surface is likewise island-allowed
(T3, ADR-068). Any other script requires an explicit, greppable directive.

This ticket (**P15.1**) owns the **epistemic visual language** and the
**a11y / no-JS / archivability baseline** that P15.2–P15.5 all consume. Later
surfaces reference these components; they do not redefine them (any change to the
visual language is an ADR, not an ad-hoc edit — ADR-049).

## What lives here

| Path | What it is |
|---|---|
| `src/lib/epistemic.ts` | The visual language as pure data + logic: the four fields (§10.7), the four-step support glyph, the four absence kinds (§9.5), the contested predicate, the contradiction range. Carries no colour. |
| `src/lib/fixtures.ts` | Committed fixtures mirroring the read-API envelope (`api/src/api/models.py`) and demo store — the shell reads no live API at build (static-first). |
| `src/lib/task.ts` | Turning a clicked absence gap into a `GENERATED` research task (no-JS GET → pre-generated intake page). |
| `src/lib/citation.ts` | Belief-pinned permalinks + the "cite this page" affordance (SIG-UI-035). |
| `src/lib/dossier.ts` | **P15.2** — the local dossier content contract as pure logic (§39.2): the twelve sections + validator (SIG-UI-010), the incompleteness banner (SIG-UI-012), the derived `next_decision_date` (SIG-UI-014b, a stable interface P15.4 consumes), the three action blocks (SIG-UI-014a), the `unknown`-not-omitted row (SIG-UI-015), and `renderDossierJson` — the single source of truth for the page, the print export, and the JSON API (SIG-UI-011). |
| `src/lib/dossier-fixture.ts` | The worked Appendix-B/D dossier (Oklahoma City / OKCPD), keyed to the same demo entity the reference surfaces render. |
| `src/components/*.astro` | `SupportGlyph`, `EpistemicFields`, `ContestedMarker`, `AbsenceHatch`, `ContradictionRange`, `Citation`, and the P15.2 dossier parts: `DossierFigure` (reconciliation disclosure), `DossierSection`, `IncompletenessBanner`, `WhatWeDontKnow`, `ActionBlocks`. |
| `src/pages/` | Landing, methodology/editorial/coverage/data-freshness pages, the visual-language + style references, the three public T2 islands (`map/`, `explore/`, `search/` — `network.astro` is a 301 to `/explore/`), `dossier/` + `research-dossier/` + `evidence/` + `releases/` (the release-namespaced record surface), `corrections.astro` + `dispute.astro` + `intake/` (the intake routes — honestly non-operational), `r/**` + `s/**` (release-addressed records/search), `watch*`, `task/` + `research-queue.astro` + `contribution-back.astro`, and the authenticated `curate/` subtree; **the local dossier** — `dossier/[slug].astro`, its `dossier/[slug]/print.astro` (paginated, council-ready PDF path, SIG-UI-013), and its `dossier/[slug].json.ts` static API endpoint. |
| `src/styles/epistemic.css` | The design system. Every `--sig-epi-*` colour is an `hsl()` outside the green band — green is never used for epistemic state (SIG-UI-006). Includes the neutral (non-epistemic) dossier + `@media print` chrome. |

## Commands

```sh
npm install            # from the committed package-lock.json use `npm ci`
npm run dev            # local dev server
npm run build          # static build to dist/ (zero client JS on non-island pages)
npm run typecheck      # astro check
npm run test:unit      # vitest — pure logic + design-token invariants
npm run test:e2e       # playwright — WCAG 2.2 AA (axe) + no-JS parity + page-type
                       # classification, budgets, script policy + render paths
npm run test:visual    # playwright visual snapshots (playwright.visual.config.ts)
npm run check:licenses # OSI-only dependency gate (SIG-UI-039)
npm run check:perf     # Lighthouse performance budgets (SIG-UI-041) — SIG_BUILD_INTERNAL=1 build + lhci
npm run check:perf:national  # the national-scale budget leg (scripts/ci/national_budget_leg.sh)
npm run check:visual   # the national visual-sweep leg (scripts/ci/national_budget_leg.sh visual)
npm run check          # the full local gate, mirror of the CI `web` job — typecheck →
                       # test:unit → build → check:lhci/map-styles/licenses/paths/
                       # snapshot/dom/figures/tokens/lexicon/copy/feeds/dsrc/
                       # runtime-deps → test:e2e
```

The mandated gates — WCAG 2.2 AA, OSI-only licences, performance budgets, and
the page-type/copy/figures/source lints — run in the `web` job of
`.github/workflows/ci.yml`, so they are enforced in CI, not by memory.
