# ADR-093 — Information-architecture redesign: grouped nav, national landing, per-jurisdiction dossier index

- **Status:** Accepted
- **Phase / ticket:** Phase 27 / P27.6 (`docs/tickets/P27.6__ia-redesign-landing.md`) — design decision operator-ratified 2026-09-22; **implemented by** P27.6 (spec_src fold-back lands with it, SIG-ENG-039)
- **Date:** 2026-09-22
- **Related:** ADR-014 (Astro static-first), ADR-090 (the national surface this makes navigable), ADR-091 (the island architecture), SIG-UI-035 (belief-pinned citation), SIG-UI-036/037 (static-first, zero-JS, tabular/list equivalents), SIG-UI-044 ("how we know this"), the SIG-UI-010..015 local-dossier surface, §39–41 (interfaces). Evidence: `web/src/layouts/BaseLayout.astro` (the 13-link flat nav; the `sig.example` canonical fallback), `docs/build/reports/P27_LAUNCH_READINESS_PLAN.md` §3.

## Context

The deployed shell's navigation is **13 flat top-level links** (`BaseLayout.astro`) with no hierarchy,
mixing product pages, secondary/about pages, and "reference" demos; the **`Dossier` link is hardcoded
to `/dossier/oklahoma-city/`**; `map` duplicates `reference-map` and `network` duplicates
`reference-graph`; and the canonical origin is the `sig.example` placeholder with a frozen `as_of`.
Once the surface is national (ADR-090), a single hardcoded jurisdiction link and a flat 13-item nav do
not scale, and the landing page must summarise a national dataset honestly rather than showing one
jurisdiction's demo. Because this reshapes a **landed** SIG-UI surface (§39–41), it is recorded as an
ADR (SIG-ENG-003) rather than an unrecorded redesign.

## Decision

1. **Grouped, uncluttered navigation** — primary (product: map, network, dossiers, watch, evidence),
   secondary (about: methodology, coverage, corrections, contribution-back), and reference (visual
   language) — keyboard-accessible, replacing the flat 13-link bar.
2. **A real national landing page** — honest headline counts with **named denominators and no total**
   (§32, ADR-090), the jurisdiction reach, and entry points to the product surfaces, keeping the
   epistemic framing ("absence is not evidence of absence").
3. **A per-jurisdiction dossier index** — the SIG-UI-010..015 local dossier made discoverable at
   scale; the hardcoded `/dossier/oklahoma-city/` link is replaced by the index.
4. **Reconcile the duplication** — one canonical map surface and one canonical network surface; the
   `reference-*` demo pages fold into the visual-language reference or are removed.
5. **Real metadata** — the canonical site origin + the belief-pinned permalink + `as_of`/ruleset come
   from the **export manifest** (ADR-092), not the frozen `fixtures.ts` constant.
6. **Invariants preserved** — zero-JS content, WCAG 2.2 AA, and the tabular/list equivalents
   (SIG-UI-036/037) are unchanged; interactivity is the ADR-091 island track, not this ticket.

## Consequences

- The OKC dossier becomes one entry in a national index rather than "the site"; navigation scales to
  many jurisdictions.
- The citation/as_of stop being demo values — the surface becomes genuinely citable.
- The reshaped SIG-UI surface is folded to `spec_src` (§39–41) by P27.6 with a new SIG-UI id + its
  Appendix F/coverage rows in the same PR (SIG-ENG-039).

## Alternatives considered

- **Keep the flat nav / hardcoded OKC link.** Rejected — unusable at national scale and wrong once the
  surface is not OKC-only.
- **A ground-up IA that discards the epistemic visual language.** Rejected — the visual language
  (support glyph, contested marker, honest gap) is the product's core, not chrome to replace.

## Proposed spec_src amendment (NOT yet applied — folds in when P27.6 lands, under the phase gate)

- `docs/research/_meta/spec_src/81_partVII_s39to41_ui.md` (§39–41): add the national IA requirement
  (grouped nav + national landing + per-jurisdiction dossier index) and the real-metadata rule
  (canonical origin + `as_of`/ruleset sourced from the export manifest) — a **new SIG-UI id minted by
  P27.6** with its Appendix F + coverage rows in the same PR (SIG-ENG-039). Then `sh …/BUILD.sh` + a
  manifest "Spec amendments applied" entry. Tracked as `D-P27-SPEC-1`.

## Revisit trigger

- The grouped nav / landing fails a11y or comprehension testing with real users (council members,
  journalists) — revise the IA by a new ADR.
- ADR-090's national scope is revisited (e.g. narrowed to curated jurisdictions) — the index structure
  revisits with it.
- A future surface needs a nav group not in the primary/secondary/reference taxonomy — extend the
  taxonomy by amending this ADR, not ad hoc.
