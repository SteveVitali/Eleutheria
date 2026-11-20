# OPS-VISUAL-MAP-HARNESS-FIX — fix the VISUAL-MAP-* flake at the root (repair branch)

**Decision record:** the operator's GATE DECISIONS row
`2026-11-20T00:15Z` — **"Fix the harness"** (AskUserQuestion selection;
recorded verbatim in `docs/build/LEDGER.md`). A repair-class fix branch
like `r11/ops-release-infra-apply-fixes` — its own PR, not a manifest
row. Base: `r11/P38.3c-round11-integration-plan` (`e7b888f8`, the chain
tip it forked from).

## The defect

`web/tests/visual/visual.spec.ts` screenshotted `/map/` with no
island-aware wait: `gotoSettled` settles the document, never the island,
and `toHaveScreenshot` fired before the island's PMTiles compartment
tiles drew. The In-view list reads `map.querySourceFeatures(…,
{sourceLayer:"cells"})` — already-drawn features only — so under a
loaded runner the shot captured the "0 records in view" empty state
against the ~209,292-record baseline: the adjudicated, byte-identical
**VISUAL-MAP-LIGHT-1** (96,676 px · 0.08) / **VISUAL-MAP-DARK-1**
(96,179 px · 0.08) class — six-plus strikes across four heads plus
`main` on 2026-11-19, zero `web/` bytes in any judged diff
(`docs/build/reports/ci/flake_log.csv`; P38.3b/P38.3c run ledgers).

## The fix

After `gotoSettled`, when the route carries the map island's mount
markers (the server-rendered `[data-testid="map-island-placeholder"]`
anchor or an already-mounted `[data-testid="map-island"]`), the spec
waits on the island's shipped latches — the **same mechanism the
budget/journey specs already use**:

- `data-ready="true"` — the map loaded (30 s bound);
- `data-drawn="true"` — a drawn compartment source reports
  `isSourceLoaded` (`MapApp.tsx` `markDrawn`; the same `sourcedata`
  event that calls `refreshList`, so the attribute and the populated
  list land in one render). Bound: 120 s national / 20 s fixtures — the
  J1–J10 battery's recorded `DRAWN_TIMEOUT` arms.

`toHaveAttribute` polls to its bound — a **feature-populated signal,
never a fixed sleep** — and a never-mounted or never-drawn island times
out and fails loud. Detection anchors on the placeholder (present from
first paint) because polling for the island element would re-create the
race the wait removes.

## Explicitly not done

- **No `ci_flakes.toml` entry** — VISUAL-MAP-* stays unlisted; the
  operator chose the fix, not the list.
- No `web/src/` byte touched — the latch reuses the island's existing
  `data-ready`/`data-drawn` signals; no new hook needed.
- No baseline re-shot or expectation loosened — the wait only orders
  the screenshot after the state the baseline already records.

## Verification

- `npm --prefix web run typecheck` — 0 errors (649 files).
- National build + the six map cells
  (`playwright.visual.config.ts -g "map — /map/"`): the latch held —
  every cell reached `toHaveScreenshot` with the island populated
  (`209292 records in view` in the ARIA tree). Local shots diff
  ~9k–30k px vs the linux/amd64 baselines, the same platform-render
  delta an island-free control (`home — /`, ~31k px) shows on macOS;
  the flake's byte-identical 96,676/96,179 signature did not occur. The
  linux-runner head-bound CI read is the verdict leg.

## Evidence

`docs/build/runs/OPS-VISUAL-MAP-HARNESS-FIX.md` (run ledger) · the
diagnosed root cause in `runs/P38.3b.md`/`P38.3c.md` ·
`flake_log.csv`'s adjudicated strike history · boundary JSON
`docs/build/reports/ci/ops_visual_map_harness_fix_pr540_heade873.json`.

## CI (head-bound, standing)

`ci: pass #540@e873690` — 5/5 head-bound (run 44645374966: security
36s · docs 2m35s · composed 3m35s · python 19m42s · web 1h2m35s). The
visual grid ran clean — `VISUAL-MAP-LIGHT-1`/`DARK-1` did not recur on
the first head carrying the latch. **Standing `blockedOn` (verbatim):**
`CI stack on #540@e873690 (external): #539 does not contain its base
#538's head d5d38c9` — #538's head moved after #539's catch-up merge;
the catch-up-merge remedy is the chain owner's / operator's call, not
this repair branch's. This head's own ancestry is clean
(`{child: 540, parent: 539, ancestor: true}`), `mergeStateStatus:
CLEAN`. Records head `c681fbaa`'s run 44653782948 went 4/5 green with
the web leg **stalled** (step 13 "Build the static site" in_progress
62+ min vs 5s on the green run — `RUNNER-STALL-1` class, unlisted,
recorded in `flake_log.csv`; docs-only delta vs the green head, zero
`web/` bytes differ; the cancel/rerun call is the operator's).
