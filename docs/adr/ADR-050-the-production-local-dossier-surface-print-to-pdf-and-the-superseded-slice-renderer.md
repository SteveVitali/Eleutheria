# ADR-050: The production local-dossier surface — a print-to-PDF path, and the superseded slice renderer

- **Status:** Accepted
- **Date:** 2026-09-01
- **Phase:** P15.2
- **Requirement ids:** SIG-UI-010, SIG-UI-011, SIG-UI-012, SIG-UI-013, SIG-UI-014, SIG-UI-014a, SIG-UI-014b, SIG-UI-015
- **Spec:** docs/2_canonical_design_spec.md §39.2 (the local dossier); Appendix B/D content contract
- **Closes out:** ADR-032 (the P06.1 slice renderer's revisit trigger)

## Context

ADR-032 built a **minimal, slice-proof** dossier renderer in `exports/dossier.py`
so J-1 renders end to end before the epistemic visual language existed, and named
its revisit trigger: *"P15.2 lands the production dossier surface … at that point
`exports/dossier.py` is superseded."* P15.2 is that ticket. The production surface
must render the §39.2 contract on P15.1's epistemic visual language, a11y/no-JS
baseline, and editorial standards, and must add the three action blocks and the
derived `next_decision_date` the outline's field list omits (SIG-UI-014a/b).

Two decisions needed recording: **where** the production surface lives, and **how**
its print/PDF path is realised (ADR-032 had anticipated a "server-side PDF
renderer").

## Decision

1. **Build the production dossier in `web/`** (Astro, static-first, zero-JS —
   TypeScript confined here per SIG-ENG-010), consuming P15.1's components
   (`SupportGlyph`, `ContestedMarker`, `AbsenceHatch`, …) and its citation/permalink
   affordance. Pure logic + the content contract live in `web/src/lib/dossier.ts`
   (the twelve-section validator, the incompleteness banner, the three action
   blocks, the derived `next_decision_date`, and `renderDossierJson`); the worked
   Appendix-B/D object is a committed fixture. One page is statically generated per
   jurisdiction (`dossier/[slug].astro`).

2. **Realise the SIG-UI-013 print/PDF path as a dedicated static print route**
   (`dossier/[slug]/print.astro`) that paginates the twelve sections into
   `.sig-print-page` blocks, **each carrying a footer with the as-of date and the
   belief-pinned permalink**, plus print CSS (`@page`, expanded reconciliations).
   Browser "Print → Save as PDF" from this route yields the council-ready document.
   **We do NOT add a server-side PDF renderer** (WeasyPrint/Chromium): it would be a
   new heavyweight supply-chain surface, and it is unnecessary — the print route is
   verifiably a usable PDF (the e2e suite drives headless `page.pdf()` and asserts a
   real, multi-page `%PDF`). This keeps archivability structural (no client JS) and
   the dependency tree OSI-clean (SIG-UI-039).

3. **Emit "what we don't know" in all three surfaces from one source of truth**
   (`renderDossierJson`): the HTML summary, the print export, and a committed static
   JSON endpoint (`dossier/[slug].json.ts`) — the API form (SIG-UI-011). Static-first
   means the JSON is generated at build time; its shape is the `/v1` dossier contract.

4. **`next_decision_date` is a stable, derived interface** (`nextDecisionDate`):
   `expiry − notice_window` when a contract auto-renews, else the expiry. The renewal
   watch (P15.4, §39.5) keys its alerts on this wire name (SIG-UI-014b); it is never
   stored, so it cannot disagree with its inputs.

5. **Retain `exports/dossier.py`** as an internal, export-time renderer rather than
   deleting it. It and its tests still pass and are cited by the P06.1 slice
   acceptance suite and traceability; removing it would break a prior ticket's
   contract for no benefit (additive/back-compat, §0.7). It is no longer the
   production surface — this ADR records that the production owner is `web/`.

## Consequences

The dossier — the project's primary public artifact — renders on the full epistemic
language with a WCAG 2.2 AA, zero-JS, print-to-PDF surface, and the API/summary/print
"what we don't know" contract is single-sourced. No PDF toolchain enters the
lockfile. `exports/dossier.py` becomes a secondary, internal renderer.

## Alternatives considered

- **A server-side PDF renderer (as ADR-032 anticipated)** — rejected: a new
  heavyweight dependency and supply-chain surface, and it would run client-side or
  build-side machinery the print-to-PDF route already provides. The AC ("prints to a
  usable PDF") is met and machine-verified without it.
- **Extending `exports/dossier.py` (Python) as the production surface** — rejected:
  the public web surface is the P15 TypeScript package (SIG-ENG-010); the dossier
  must consume P15.1's Astro components and a11y baseline, which Python cannot.
- **Deleting `exports/dossier.py`** — rejected: it is a landed deliverable with
  passing tests and traceability rows; superseding ≠ deleting.

## Revisit trigger

The shell is wired to the live `/v1` dossier API (replacing the committed fixture),
or a second jurisdiction's dossier requires per-jurisdiction data loading beyond a
single committed fixture.
