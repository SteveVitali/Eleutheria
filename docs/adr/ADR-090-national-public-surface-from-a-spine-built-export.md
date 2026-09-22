# ADR-090 — The public surface renders the national graph from a spine-built export

- **Status:** Accepted
- **Phase / ticket:** Phase 27 / P27.1 (`docs/tickets/P27.1__public-surface-audit.md`), P27.4, P27.6 — design decision operator-ratified 2026-09-22; **implemented by** those tickets (spec_src fold-back lands with them)
- **Date:** 2026-09-22
- **Related:** ADR-014 (Astro static-first web), ADR-066 (the export-backed web data layer this generalises), ADR-075 (the GCP hosted surface), ADR-092 (spine-read export + resolution posture — the how), ADR-091 (the frontend architecture), SIG-UI-036/037 (static-first), SIG-UI-010..015 (the local dossier), §37–§41 (API/UI), §38 (exports), §32 (coverage), §3.1 (defining standard). Evidence: `docs/build/reports/P27_LAUNCH_READINESS_PLAN.md` §1 (live audit 2026-09-22).

## Context

The deployed public surface renders the **OKC vertical-slice fixtures** (`sig.example`, frozen
`as_of 2026-08-20`, 4 sources, 42 devices, a 2-edge graph) while the hosted spine holds **1,059,533
claims / 210 sources / 75,479 geolocated camera-site entities** across the US + GB/AU/TH/NZ (audit
2026-09-22). Three facts make the demo the *only* thing the public can see:

- the web is static-first (SIG-UI-036/037, ADR-014) and reads its data at **build time**;
- the public read API is deployed `--no-allow-unauthenticated` (locked), so the sole public data path
  is the static build + the published GCS export objects; and
- the export is fixture-backed — `sig-exports build --jurisdiction` only knows hardcoded `okc`/`france`
  (`exports/cli.py _jurisdiction_request`, `web_dossier.build_web_dossiers`); ADR-066 wired the
  export→web seam but only for dossiers + the leverage metric.

The canonical spec frames the public artifact as the **local dossier** (per-jurisdiction, SIG-UI-010..015).
The operator decided (2026-09-22) the launch surface is **broad/national** — everywhere SIG has
publishable data — not OKC-only.

## Decision

1. **The public surface is a static build from a real, national, spine-read export** (not fixtures,
   not a single jurisdiction). Its scope is the whole *publishable* graph.
2. **Breadth is bounded by publishability, and gaps are shown honestly.** The export gate still fails
   closed on unresolved rights / co-mingled licences (ADR-092 does the reading; ADR-086 + the P27.2
   rights work widen what qualifies). "National" therefore means *as broad as rights permit*, with
   absence rendered as an explicit gap (§3.1) — never implied completeness, never a total (§32).
3. **The local dossier becomes one entry in a national index.** SIG-UI-010..015 is preserved and
   generalised: a per-jurisdiction dossier index sits over the dossiers (P27.6).
4. **Fixtures remain the CI/demo default** (`SIG_DATA_SOURCE=fixtures`); the real path is `--from-spine`
   / `SIG_DATA_SOURCE=export` (P27.4), so CI and archivability are unchanged.

## Consequences

- A genuine national/international camera map + procurement watch + dossier index becomes the public
  surface; the ~93k-camera dataset stops being invisible.
- The launch scope is gated by rights: at audit 24% of claims were UNDETERMINED (dominated by
  `procurement`/`dot_511`/`france_belgium_procurement` — public-record, legitimately resolvable in P27.2).
- The OKC dossier is demoted from "the site" to "one jurisdiction among many"; the IA (P27.6) must make
  breadth navigable without implying a complete census.

## Alternatives considered

- **Local-dossier-only (status quo intent).** Rejected by the operator — it under-uses a real
  1.06M-claim, 75k-site dataset and never surfaces the national picture.
- **A dynamic, API-served public surface.** Rejected — the read API is locked and the zero-JS static
  contract (SIG-UI-036/037) makes a build-time export the archivable, citation-stable path.

## Proposed spec_src amendment (NOT yet applied — folds in when P27.4/P27.6 land, under the phase gate)

- `docs/research/_meta/spec_src/81_partVII_s39to41_ui.md` (§39–41): add that the public surface is the
  **national/whole-graph** export with a per-jurisdiction **dossier index** over the SIG-UI-010..015
  dossiers (new requirement id, e.g. `SIG-UI-0xx`).
- `docs/research/_meta/spec_src/80_partVII_s37to38_api.md` (§38): add that the public export is a
  spine-read national bundle (new `SIG-EXPORT-0xx`), breadth bounded by the fail-closed licence gate.
- Then `sh docs/research/_meta/spec_src/BUILD.sh` + a "Spec amendments applied" manifest entry
  (SIG-ENG-003); tracked as `D-P27-SPEC-1`.

## Revisit trigger

- If, after the P27.2 rights work, the *publishable* scope is still tiny (a national surface is not
  honestly viable) — fall back to a curated-jurisdictions surface by a new ADR.
- If a jurisdiction objects, or breadth creates a safety concern under Part VIII (§0.7) that
  per-jurisdiction framing avoided — re-scope by a new ADR.
- If the read API is later opened (rate-limited public tier) — revisit whether the surface stays
  build-time-static or gains a served path (would also revisit ADR-092).
