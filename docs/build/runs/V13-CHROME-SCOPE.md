# Run ledger — V13-CHROME-SCOPE (D-P37.65a-6, check-side half)

- **Harness:** devin-desktop/swe-2-high/subagent
- **Started:** 2026-11-26 (entry-time `date -u` was not captured; the first recorded reading is
  21:00:22Z, taken at ledger-write — the work began on a clean worktree at `a81b5935`, chain tip,
  then fast-forwarded onto `6f94f91f` — the `r11/P38.3c-round11-integration-plan-2` tip — before
  the first file write)
- **Closed:** 2026-11-26T21:00Z
- **Unit:** the **check-side half** of deferral `D-P37.65a-6` (docs/tickets/DEFERRALS.md row ~1682)
  under the signed operator decision `dc7e98ad` (GATE DECISIONS row ~373, verbatim selection
  "Full-chrome, stamp v/ too"). The emit-side half — rebuilding the `v/` dist bound to the
  candidate's `release.json` (`SIG_RELEASE_JSON`) — belongs to the re-sites/resume leg, **not**
  this unit; the `s/` fixed-copy wording divergence is a recorded residual, also not this unit.
- **Worktree / branch:** `/private/tmp/sig-v13-chrome`, `r11/ops-v13-chrome-scope` (base
  `r11/P38.3c-round11-integration-plan-2` @ `6f94f91f`).

## What the decision binds (carried verbatim into the check)

The `API is live` stamp contract scopes to `data-sig-chrome="full"` pages — error/`/print/`/
minimal-chrome pages are legitimately unstamped (they keep the `<meta name="sig-release">` +
`describedby` machine pair, never the footer basis sentence). `v/` IS in scope and will be
rebuilt bound to `release.json` (the resume leg's job).

## The chrome marker found (verified against the source emitters)

- `web/src/layouts/BaseLayout.astro:265` — `<html lang={lang} data-sig-chrome={chrome}>`,
  `chrome?: "full" | "minimal"` (prop contract `:84`, default `"full"` `:123`). Error pages
  (`web/src/pages/{403,404,410,500}.astro`) pass `chrome="minimal"`.
- `web/src/pages/dossier/[...path]/print.astro:182` and
  `web/src/pages/entity/[type]/[key]/print.astro:74` — `<html … data-sig-chrome="print">`.
- `web/src/layouts/CurateLayout.astro:31` — `data-sig-chrome="curate"`.
- `exports/src/exports/release_pages.py:332-346` (`_layout`, the `r/` archive emitter) —
  `<html lang="en">` with **no** `data-sig-chrome` marker at all.
- The basis sentence itself renders only inside the `chrome === "full"` footer gate —
  `BaseLayout.astro:359-393`, the line verbatim at `:391`
  (`The public API also serves newer, unreleased records, labelled "live".`); the
  `<meta name="sig-release">` + `describedby` pair is emitted chrome-independently (`:316-317`).

## The change (`ops/src/ops/release_verify.py`)

- New `_FULL_CHROME_RE` (next to `LIVE_API_LINE`, ~line 131):
  `re.compile(r'<html[^>]*data-sig-chrome="full"')` — the exact emitted marker, anchored to the
  `<html>` tag so a prose/documentation occurrence of the attribute string cannot fake scope.
- `check_v13`'s live-line leg (was `release_verify.py:1516-1529`): a page is *stamped* iff it
  carries `name="sig-release"` (unchanged); a stamped page is *evaluated* iff it matches
  `_FULL_CHROME_RE` — missing the line there is still a failure, verbatim message
  `{page}: the stamp's 'API is live' line is absent` (fail-closed semantics unchanged inside
  scope). Every other/absent chrome class increments `chrome_excluded` and is never evaluated.
- **Evidence shape** (sibling-consistent): `disclosures_checked` (unchanged), `stamped_pages`
  (unchanged meaning — every `sig-release` page), `chrome_excluded` (**new int** — stamped pages
  outside the contract's scope, so the exclusion is visible, never smoothed),
  `live_line_missing` (unchanged — ≤10 sample, now only full-chrome pages), `eval_status`,
  `eval_overclaims`, `failures`. Detail line gains the count:
  `{n} disclosure(s) · {s} stamped pages ({x} chrome-excluded) · eval={status}`.
- `check_v13` docstring updated: "on every stamped `data-sig-chrome="full"` page (D-P37.65a-6)".

## The fixture (`tests/ops/test_release_verify.py`)

- `_site_page` gains `chrome: str | None = "full"` — emits `data-sig-chrome="{chrome}"` on
  `<html>` (mirroring `BaseLayout.astro:265`), the `stamp mut` basis line only when
  `chrome == "full"`, no attribute at all on `None` (the `r/` emitter's shape). The stamp block,
  meta, and describedby pair are unchanged in every class.
- `_write_site_tree` now marks the four required branded error pages (`404.html`, `403.html`,
  `410.html`, `500.html` — new `_ERROR_PAGES` frozenset) `chrome="minimal"`: the real build
  emits them minimal-chrome + stamped + no basis sentence (P34.13/QW-11), so the green fixture
  exercises the exclusion path on every suite run.

## New tests (three, pinning the decision)

- `test_v13_passes_when_every_full_chrome_page_carries_the_live_line` — green fixture passes;
  `live_line_missing == []`; `stamped_pages > chrome_excluded > 0`; the detail string carries
  `{x} chrome-excluded`.
- `test_v13_fails_when_a_full_chrome_page_lacks_the_live_line` — strips `LIVE_API_LINE` from
  `s/<pub>/about/index.html` → `status == "fail"`, the page named in `live_line_missing`.
- `test_v13_excludes_non_full_chrome_pages_without_failing` — plants stamped pages per chrome
  class (`minimal`, `print`, `curate`, marker-absent) with no basis line → still `pass`,
  `stamped_pages` and `chrome_excluded` each +4 vs baseline (counted, never silent).

## Verification

- `uv run pytest tests/ops -q` — **2524 passed, 2 skipped** (12m31s; the 2 skips are the
  environmental npm/web-build legs covered by the CI `web` job).
- `uv run ruff check` + `ruff format --check` on both touched files — clean.
- `uv run mypy -p ops` — 104 source files, no issues.

## Consequences / residuals recorded

- `r/` archive pages carry the basis sentence via `_stamp_html` but emit no
  `data-sig-chrome` — they now count inside `chrome_excluded` rather than being evaluated.
  This is the decision's literal scope (the contract binds `data-sig-chrome="full"`); V4's
  per-page stamp contract over the same pages is unchanged.
- The prior `[:10]` truncation on misses is retained (sibling shape: the count lives in the
  detail line, the list is a sample) — the observed ~22+ true misses are all excluded classes,
  so the resumption run should show `chrome_excluded` ≥ that count in `s/`.
- **Not done here (owned elsewhere):** `v/` re-emit + re-stage bound to `release.json`
  (resume leg); `s/` latest-view-vs-fixed-copy wording divergence (recorded residual for the
  HG-11 readout); DEFERRALS row flip and obligation event (the closing leg's write).
