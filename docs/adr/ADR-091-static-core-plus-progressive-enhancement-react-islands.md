# ADR-091 — Static content core + progressive-enhancement React islands (DECISION-SPA = B)

- **Status:** Accepted
- **Phase / ticket:** Phase 27 / P27.9 (`docs/tickets/P27.9__interactive-islands.md`), P27.6 — design decision operator-ratified 2026-09-22; **implemented by** those tickets (spec_src fold-back lands with P27.9)
- **Date:** 2026-09-22
- **Related:** ADR-014 (Astro), ADR-018 (MapLibre GL for the web map), ADR-068 (the `/curate/**` island + loopback-auth exception this extends), SIG-UI-036/037 (zero-JS static-first), **SIG-UI-047 / A1** (§40 — interactive map island as a MAY over the zero-JS default), `web/lighthouserc.json` (the per-surface budget matrix). Evidence: `docs/build/reports/P27_LAUNCH_READINESS_PLAN.md` §4 (DECISION-SPA).

## Context

Public pages are **zero-JS static-first** (SIG-UI-036/037, ADR-014): `web/lighthouserc.json` asserts
script bytes `0` and total ≤ 150 KB, and `test:e2e` enforces WCAG 2.2 AA + the no-`<script>` baseline.
The **only** island exception today is `/curate/**` (ADR-068). The spec already anticipates one public
island: **SIG-UI-047 (MAY)** permits an interactive MapLibre map (ADR-018) as *progressive enhancement*
over the zero-JS static map (A1).

The operator wants a beautiful, modern, convincing launch surface with cutting-edge interactivity, but
also chose **"zero-JS now, interactive later"** and values the mission-critical properties of the
current stack: **archivability, accessibility, and citation-stability** (a record cited by councils and
archived must render with no JS and be saveable forever). A full from-scratch React SPA was on the
table and **rejected**; the operator chose **B — static core + React islands**.

## Decision

1. **The public content core stays zero-JS, archivable, WCAG-2.2-AA, citation-stable** (SIG-UI-036/037
   unchanged). Content pages ship **no** `<script>`.
2. **React arrives via `@astrojs/react`**: components render to **static HTML** at build time by
   default (no client JS shipped); only explicitly-named islands hydrate.
3. **The public islands are exactly three:** the **map** (over the P27.4 PMTiles — this *exercises*
   SIG-UI-047, already a MAY), the **network-graph** explorer, and **search/filter**. Each island
   MUST preserve its **no-JS fallback** (the tabular / list / browse equivalent) — progressive
   enhancement, never replacement.
4. **The island allowance (ADR-068) is extended** from `/curate/**` to those three named public
   islands; each island *page* gets its own `lighthouserc.json` budget row (as `/curate/**` has), and
   every other public page keeps script bytes `0`.
5. **A full SPA is rejected** — the archivability / a11y-by-default / citation regressions are not
   worth it for a surveillance-accountability record.

## Consequences

- Launch ships the static core first ("zero-JS now"); the islands are a fast-follow (P27.9,
  "interactive later"). The map island needs no new spec permission (SIG-UI-047).
- `@astrojs/react` is added to `web/` (pinned, published ≥7 days); it lets P27.6 author a modern design
  system as components while still emitting static HTML.
- The zero-JS/perf/a11y budget stays green on content pages; island pages are measured against their
  own budget; ODbL attribution is shown on the map (§42.3).

## Alternatives considered

- **A — rich static redesign, no islands.** Viable and fully archivable, but forgoes the interactive
  map/graph/search the operator wants. Kept as the fallback if an island can't meet its a11y budget.
- **C — full from-scratch React SPA.** Rejected — overturns SIG-UI-036/037, archivability, and
  a11y-by-default, changes the hosting/SSR + publication posture, and would need to supersede multiple
  ratified UI ADRs for a net loss on the properties that matter most here.

## Proposed spec_src amendment (NOT yet applied — folds in when P27.9 lands, under the phase gate)

- `docs/research/_meta/spec_src/81_partVII_s39to41_ui.md` (§40): extend the island allowance from
  `/curate/**` to the three named public islands (map/graph/search); annotate **SIG-UI-047** to cover
  them; add the invariant that **every public island preserves a no-JS fallback** (new `SIG-UI-0xx`).
- Then `sh …/BUILD.sh` + a "Spec amendments applied" manifest entry + a new ADR is unnecessary (this is
  it); tracked as `D-P27-SPEC-1`.

## Revisit trigger

- An island's no-JS fallback becomes unmaintainable, or a public island breaks the a11y/archival/perf
  contract in CI — re-gate or remove that island by a new ADR.
- The operator later wants a full SPA — a new ADR superseding this one **and** SIG-UI-036/037 (with the
  archivability/a11y mitigations spelled out) is required; never a silent stack swap.
- A fourth public island is proposed — extend the allowance by amending this ADR's named set, not ad hoc.
