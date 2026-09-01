# ADR-032: A minimal slice dossier renderer, with a print-CSS PDF path, ahead of the production surface

- **Status:** Accepted
- **Date:** 2026-09-01
- **Phase:** P06.1
- **Requirement ids:** SIG-UI-010, SIG-UI-011, SIG-UI-012, SIG-UI-013, SIG-UI-014, SIG-UI-015
- **Spec:** docs/2_canonical_design_spec.md §39.2 (the local dossier); the Phase-6 slice of §52

## Context

The P06.1 slice must produce "a slice-proof rendered dossier exercising the §39.2
content contract" so that J-1 renders end to end. But Phase 6 runs before the
public web surfaces (P15) and the epistemic visual language (P15.1). The ticket's
own scope note is explicit: this is a *proof that J-1 renders end to end*, built
before the visual language; the **production** dossier surface — the real owner of
SIG-UI-010..015, with the full epistemic language, a11y/no-JS, and editorial
standards — is **P15.2, which supersedes this renderer**. "Keep this one minimal;
do not gold-plate it."

SIG-UI-013 additionally requires a **print/PDF path**. A true server-side PDF
renderer would mean a new heavyweight dependency (e.g. WeasyPrint/Chromium),
which is disproportionate for a slice proof.

## Decision

1. Implement a **minimal dossier renderer** in the existing `exports/` package
   (`exports/dossier.py`): the twelve §39.2 sections in order (SIG-UI-010), "what
   we don't know" carried in the summary, the API/JSON form, and the print form
   (SIG-UI-011), an explicit incompleteness banner (SIG-UI-012), every material
   figure expandable to its reconciliation (SIG-UI-014), and `unknown` values
   rendered rather than omitted (SIG-UI-015).

2. Satisfy the SIG-UI-013 print/PDF path with a **paginated print-CSS HTML
   document** (a running per-page footer carrying the as-of date and permalink,
   plus sources), suitable for a browser "Print to PDF". **Defer a server-side PDF
   renderer to P15.2.** No new runtime dependency is added; the renderer is pure
   stdlib (`html`, `json`).

3. Keep the graph→dossier *assembly* and the Oklahoma City fixtures under
   `tests/acceptance/` (slice-scoped), so only the reusable renderer lands in a
   production package.

## Consequences

J-1 renders end to end and the §39.2 contract is exercised and tested, without
pulling a PDF toolchain into the runtime lockfile. The renderer is deliberately
plain (no epistemic glyphs, no map, no a11y pass) — those are P15's job.

## Alternatives considered

Adding WeasyPrint/Chromium now for a real PDF (rejected: disproportionate, and a
new supply-chain surface for a throwaway renderer); building the renderer inside
`web/` (rejected: `web/` is the P15 TypeScript surface, out of scope here, and the
slice proof needs to run in the Python CI acceptance suite); burying the renderer
in `tests/` (rejected: the rendered dossier is a real ticket deliverable, so its
renderer belongs in a package).

## Revisit trigger

P15.2 lands the production dossier surface with the full epistemic visual
language and a server-side PDF path; at that point `exports/dossier.py` is
superseded and this ADR is closed out by the P15.2 ADRs.
