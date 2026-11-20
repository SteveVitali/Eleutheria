# OPS-VISUAL-MAP-HARNESS-FIX — repair branch: the VISUAL-MAP-* flake fixed at the root

- **Spec:** none — a repair-class fix branch (the
  `r11/ops-release-infra-apply-fixes` precedent: its own PR, not a
  manifest row). **Decision record:** the operator's GATE DECISIONS row
  `2026-11-20T00:15Z` ("Fix the harness" — AskUserQuestion selection,
  recorded verbatim in `docs/build/LEDGER.md`, staged for the operator's
  own signed commit on `r11/P38.3c-round11-integration-plan`; this run
  carries no gate-affecting record).
- **Harness:** devin-desktop/swe-2-high/subagent
- **Base / branch:** `e7b888f8` (the P38.3c chain tip) →
  `r11/ops-visual-map-harness-fix`
- **PR:** <!-- FILLED on open -->
- **Started:** 2026-11-20 (`date -u`)
- **Closed:** pending — head-bound CI read owed after the PR opens
- **Config:** read-only repair in `web/tests/`; live legs: **none**;
  `Production mutations (OM-14): none`; gate cell `none`; not an OM-20
  row.
- **Size budget:** repair-class (small bounded diff) — the
  implementation head is +31/−0 in one test file.

## Deferrals read

Read `docs/tickets/DEFERRALS.md` first. This row opens **none** and
closes **none** (+0/−0): the flake class is a harness defect repaired
in place, not an obligation row; the adjudicated history lives in
`docs/build/reports/ci/flake_log.csv` and the P38.3b/P38.3c ledgers.

## The defect (diagnosed in P38.3b's ledger, confirmed here)

`web/tests/visual/visual.spec.ts` screenshotted every template
representative after `gotoSettled` (a meta-refresh settle — no
island-aware wait at all). On `/map/` the island fills its In-view list
from `map.querySourceFeatures(…, {sourceLayer: "cells"})`
(`web/src/islands/map/MapApp.tsx:1108-1155`), which yields only
already-drawn features. Under a loaded runner the screenshot landed
before the compartment tiles drew, capturing the "0 records in view"
empty state against the ~209,292-record baseline — the adjudicated,
byte-identical `VISUAL-MAP-LIGHT-1` (96,676 px · 0.08) /
`VISUAL-MAP-DARK-1` (96,179 px · 0.08) class, six-plus strikes across
four heads plus `main` on 2026-11-19 alone, zero `web/` bytes in any
judged diff.

## What this lands

- **`web/tests/visual/visual.spec.ts`** (+31): after `gotoSettled`,
  when the route carries the map island's mount markers
  (`[data-testid="map-island-placeholder"]` — the server-rendered
  anchor, present from first paint — or an already-mounted
  `[data-testid="map-island"]`), wait for the island's own latches
  before the screenshot: `data-ready="true"` (map loaded; 30 s bound)
  then `data-drawn="true"` (a drawn compartment source reports
  `isSourceLoaded` — the same `sourcedata` event that calls
  `refreshList`, so the attribute and the populated list land in one
  Preact commit). Bounds follow the J1–J10 battery's recorded arms
  (`map-journeys`' `DRAWN_TIMEOUT`: 120 s national / 20 s fixtures).
  `toHaveAttribute` polls to its bound — a feature-populated signal,
  never a fixed sleep; a never-mounted or never-drawn island times out
  and **fails loud**, never skips.

  Detection anchors on the placeholder precisely because polling for
  the island element would re-create the race the wait removes (the
  element mounts late; the placeholder is in the static HTML). The
  dossier's embedded map is activation-gated (`sig-activate` — mounts
  only on the reader's click), so no other route false-triggers the
  wait; a future auto-mounting island on any route is covered by the
  same generic check.

## What this does not do

- **Does not allow-list the signature.** `ci_flakes.toml` untouched —
  VISUAL-MAP-LIGHT-1/DARK-1 stay unlisted; the operator's recorded
  decision was the fix, not the list.
- No `web/src/` byte touched — the latch reuses the island's shipped
  `data-ready`/`data-drawn` signals (`MapApp.tsx:2614-2617`), no new
  hook needed.
- No baseline re-shot, no `baselines.json` row, no test expectation
  loosened — the wait only orders the screenshot after the state the
  baseline already records.

## Verification (local, pre-push)

| check | result |
|---|---|
| `npm --prefix web run typecheck` (`astro check`) | ✓ 0 errors (649 files; pre-existing hints only) |
| National build `SIG_DATA_SOURCE=national SIG_BUILD_INTERNAL=1 npm run build` | ✓ 523 pages, `dist/page-types.json` records `dataSource: "national"` |
| `npx playwright test --config=playwright.visual.config.ts -g "map — /map/"` | the latch works: all six cells reached `toHaveScreenshot` **with the island populated** — the error-context ARIA tree reads `209292 records in view — grouped by place` (the baseline's state), never "0 records in view". The shots themselves diff ~8.8k–29.6k px vs the committed linux/amd64 baselines — the same order of platform-render delta a control run of `home — /` (no island, 30.6k–31.8k px) shows on this macOS host; the flake's byte-identical 96,676/96,179 empty-state signature did not occur. Head-bound CI on the linux runner is the verdict leg. |

`npm --prefix web run check` was not run end-to-end locally: its
`test:e2e` leg exercises the fixtures dist (rebuilt by `build`), not
the visual grid; the changed file is covered by typecheck above and
the visual cells are the changed behaviour. Recorded honestly — the
full gate is CI's.

## Heads / boundary

- Implementation head: **`84e1ead9`** ("visual.spec: island-ready
  latch before the /map/ screenshot (VISUAL-MAP harness race)",
  `web/tests/visual/visual.spec.ts` +31/−0).
- **Residual flake risk (stated honestly):** the latch removes the
  shot-before-draw race. Residuals: (a) `data-drawn` latches when
  *any* drawn compartment source reports loaded — a multi-compartment
  build could in principle latch while a later compartment's cells are
  still arriving (today's national corpus reports the full
  209,292-record list on latch; the same signal the J1–J10 battery
  already trusts); (b) a runner degraded enough to exceed the 120 s
  drawn bound fails loud as a timeout — a loud red, never a wrong
  baseline; (c) unrelated runner-class flakes (e.g. the recorded
  LH-LCP-MARGINAL-1 budget variant) are untouched.
- Head-bound CI verdict and any flake_log rows owed: recorded forward
  after the PR's own run.
