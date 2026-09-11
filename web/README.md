# web/ — the SIG public web shell + epistemic visual language

The Phase-15 public surface. TypeScript is confined to this package (SIG-ENG-010).
It is built with [Astro](https://astro.build) as a **zero-JS-by-default,
static-first** framework (SIG-UI-036): with no explicit `client:*` directive
anywhere in the shell, the build ships **no client JavaScript**, so the pages are
archivable by default — breaking that requires an explicit, greppable directive.

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
| `src/components/*.astro` | `SupportGlyph`, `EpistemicFields`, `ContestedMarker`, `AbsenceHatch`, `ContradictionRange`, `Citation`. |
| `src/pages/*.astro` | Landing, the visual-language reference, the reference map (+ tabular equivalent) and graph (+ list equivalent), and the task-intake route. |
| `src/styles/epistemic.css` | The design system. Every `--sig-epi-*` colour is an `hsl()` outside the green band — green is never used for epistemic state (SIG-UI-006). |

## Commands

```sh
npm install            # from the committed package-lock.json use `npm ci`
npm run dev            # local dev server
npm run build          # static build to dist/ (zero client JS)
npm run typecheck      # astro check
npm run test:unit      # vitest — pure logic + design-token invariants
npm run test:e2e       # playwright — WCAG 2.2 AA (axe) + no-JS baseline + render paths
npm run check:licenses # OSI-only dependency gate (SIG-UI-039)
npm run check:perf     # Lighthouse performance budgets (SIG-UI-041)
npm run check          # the full local gate, mirror of the CI `web` job
```

The three mandated gates — WCAG 2.2 AA, OSI-only licences, and performance
budgets — run in the `web` job of `.github/workflows/ci.yml`, so they are enforced
in CI, not by memory.
