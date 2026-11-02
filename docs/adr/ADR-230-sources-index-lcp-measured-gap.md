# ADR-230: The `/sources/` LCP measured gap — a bounded first-paint-floor accommodation under ADR-155

- **Status:** Proposed (agent-drafted under an explicit operator decision)
- **Phase:** Round 11 / P36 / sub-round 11C
- **Ticket:** P36.48 (manifest row 391; run ledger `docs/build/runs/P36.48.md`; PR #414)
- **Written:** 2026-11-02 (`date -u`; Devin sub-agent — agent-drafted, labelled)
- **Implements:** the operator's verbatim selection **"ADR-155 accommodation"** (recorded 2026-11-02, Devin Desktop orchestration session, kind=decision — see LEDGER § GATE DECISIONS); **amends ADR-155** by exercising its own `measured_gaps` mechanism (`sig.page-budgets/1` — "recorded real-scale overages … bounded and loud — never a smoothed ceiling") on a Lighthouse lab metric for the first time. **Cites:** ADR-155, ADR-229's pattern, K0 §4.3, K9 §6.1, D-P35.51-1/2 (the wire-byte precedents).

## Context

PR #414's `check:perf` leg (fixtures-mode `lhci autorun`) fails `/sources/index.html` on `largest-contentful-paint`: medians **1510.34 / 1512.28 / 1523.59 ms** against the ratified T1 ≤ 1500 ms, while every sibling T1 page passed in the same run. The repair worker's measured critical-path pass established:

- **LCP ≡ FCP verbatim** on every collected report (1505.0 = 1505.0) — the metric is bound by the shared first-paint pipeline (document + render-blocking resources), not page content.
- **No code regression:** the pre-pagination build `408bb489` measures identically (1504.2 ms) to the head under repair; `check:perf` passed in `mode=run` at that head (run 41349538937) — the environment's floor drifted, not the page.
- **Content is not the lever:** stripping 37 KB below the element and 1.6 KB above it moved the measure ~0 ms; all 13 sampled pages cluster 1503.6–1504.8 ms regardless of document size; `/sources/` (~65 KB, the heaviest T1 document) sits at the top of that ~1 ms cluster and is therefore the fleet's boundary canary.
- **The constraint trap is real:** the facet-figure fold is load-bearing for the export document budget (its revert measures 159.4–167.5 KB > 153.6 KB), bare count numerals violate the figure contract (J3 §5.4), and the K9 C-1..C-12 surface contract leaves no honest ~20 KB to cut.

Asked how to proceed, the operator selected **"ADR-155 accommodation"** (2026-11-02, Devin Desktop orchestration session, kind=decision).

## Decision

1. **One `measured_gaps` row** in `web/tests/e2e/page-budgets.json`, exactly the mechanism the ratified table already declares: `route: "/sources/"`, `metric: "lcpMs"`, `ratified_ceiling: 1500`, `recorded_measure: 1510`, `regression_bound: 1600`, `deferral: "D-P36.48-1"`. The row is bounded (1600 ms = ~6 % over the recorded measure) and loud (the generated matrix asserts the ratified 1500 ms as `warn` while the bound is the `error` gate — the law is never smoothed; a stale row fails once the measure drops under the ceiling).
2. **`gen-lhci.mjs` scope:** `/sources/index.html` moves out of the generic T1 assertion block into its own identical-T1 surface block so the gap binds to this route+metric only. Every other T1 route keeps the verbatim 1500 ceiling; every other `/sources/**` route keeps it too — the accommodation is one route and one metric.
3. **The deferral** is `D-P36.48-1` (`docs/tickets/DEFERRALS.md`): the systemic first-paint-floor work — shared font/CSS/head pipeline — that, when it lands, drops the measure under 1500 and makes the row stale on its own.

## Consequences

- Positive: the ratified ceiling is still asserted everywhere (warn on `/sources/`, error on every other route); the boundary measurement is honest, recorded and bounded; nothing else relaxes; the wire-budget machinery needed no new mechanism.
- Negative: the loud warn reports on every perf leg until the render-floor work lands — intentional, per the mechanism's own design.
- `/map/` TBT's pre-existing warn-level advisory is untouched (advisory, not a gate).

## Revisit trigger

1. The shared first-paint pipeline improves (font loading, critical CSS, head structure) such that `/sources/` measures under 1500 ms — the gap row is then stale and `page-budget-check`/`check:lhci` demand its removal.
2. `/sources/` measures over 1600 ms — a real regression past the bound; the row is evidence, not cover.
3. Any second route shows the same boundary signature — the accommodation pattern then needs a fleet-level revisit of the 1500 ms T1 LCP ceiling itself, not more per-route rows.
