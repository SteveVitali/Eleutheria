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
- **PR:** #540 (`gh pr create` 2026-11-20T00:22Z) — base
  `r11/P38.3c-round11-integration-plan`
- **Started:** 2026-11-20 (`date -u`)
- **Closed:** `ci: pass #540@4d5f11f` 5/5 head-bound (run 44661279664)
  — the second consecutive head-bound green carrying the latch
  (`e8736906` first, run 44645374966); the stack flag is recorded
  verbatim in §Heads — a pre-existing chain condition on the #539/#538
  pair, operator-side, never self-authorised here. PR OPEN awaiting the
  operator's merge.
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
- **`e8736906` run 44645374966 — `ci: pass #540@e873690` 5/5
  head-bound** (security 36s · docs 2m35s · composed 3m35s · python
  19m42s · web 1h2m35s, completed 2026-11-20T01:25Z): the web leg —
  including the full visual grid — ran clean; the
  `VISUAL-MAP-LIGHT-1`/`DARK-1` signature **did not recur** on the first
  head carrying the latch. No flake_log row is owed (no occurrence).
- **Stack flag (recorded verbatim, never decided):**
  `ci_boundary.py --pr 540 --no-wait` reads
  `blockedOn: CI stack on #540@e873690 (external): #539 does not contain
  its base #538's head d5d38c9 — rebased or retargeted outside the
  documented procedure` (exit 3; boundary JSON
  `docs/build/reports/ci/ops_visual_map_harness_fix_pr540_heade873.json`,
  read 2026-11-20T01:27Z). Reads: #538's head moved to `d5d38c9` after
  #539's catch-up merge at `e7b888f8`; my ancestry is clean
  (`{child: 540, parent: 539, ancestor: true}` — this head contains
  `e7b888f8`). The flag is the same base-head-moved class P38.3c
  recorded; the catch-up-merge remedy belongs to the chain's owner /
  the operator, not this repair branch. `mergeStateStatus: CLEAN` at
  read.
- `main:` `1d090e79` at the boundary read — `chain_descends: no` (the
  same recorded posture the chain carries; merge legs are the
  operator's).
- **Records head `c681fbaa` (the boundary-read records above) drew run
  44653782948 — the web leg stalled.** security 47s · docs 2m24s ·
  composed 4m50s · python 20m19s all pass; web's step 13
  ("Build the static site (zero-JS-by-default)") has read `in_progress`
  since 01:28:49Z — **62+ minutes** at the 02:31Z read against the same
  step's 5-second duration on green run 44645374966 one head back: a
  stalled step process, not an assertion. The head's delta vs the green
  `e8736906` is docs-records only — zero `web/` bytes differ — and the
  stall sits in the build step, which never touches the spec change.
  Recorded unlisted in `flake_log.csv` under the `RUNNER-STALL-1` class
  (the 2026-10-07 signature's second occurrence — not in
  `ci_flakes.toml`, so no entry matches and no B-15 rerun fires; the
  cancel/rerun call is the operator's). The green run's step
  decomposition confirms the verdict leg itself ran and passed: step 32
  "Visual regression grid (national build)" green at
  01:22:16→01:23:37Z on `e8736906`. This records commit draws a fresh
  head; the stalled run is superseded on push (recorded, never counted)
  and the fresh head's run is read head-bound forward.
- **`4d5f11f8` run 44661279664 — `ci: pass #540@4d5f11f` 5/5
  head-bound** (security 33s · docs 3m45s · composed 3m36s · python
  25m4s · web 59m41s, completed 03:32Z): the stall did not recur —
  step 13 completed normally and the visual grid (step 32) ran green
  with the latch in place: **two consecutive head-bound greens** on
  heads carrying the fix (`e8736906`, `4d5f11f8`), zero `web/` bytes
  between them. Boundary re-read (`ci_boundary.py --pr 540 --no-wait`,
  03:33Z; JSON
  `reports/ci/ops_visual_map_harness_fix_pr540_head4d5f.json`): the same
  standing stack flag — `#539 does not contain its base #538's head
  d5d38c9` — recorded verbatim, unchanged, operator-side. Flake rows:
  the stall's two `RUNNER-STALL-1` rows (in-progress-stalled →
  cancelled-superseded) plus the fresh head's success row, all
  committed in `flake_log.csv`.
