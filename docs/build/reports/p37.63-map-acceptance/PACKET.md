<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# P37.63 — map acceptance & republish packet (`prepared_not_executed` on the gated legs)

**Status:** deterministic half **executed green** over the real-sized deterministic
national fixture; the candidate + live legs are `prepared_not_executed` (OM-19) — the
release candidate is staged by P37.65a and promotion is the operator's act riding
P37.65b. No production mutation was performed in this dispatch
(`live_verification=false`).

**Re-run (verbatim):**
`implement-spec spec=docs/tickets/491_P37.63__map-acceptance-and-republish.md live_verification=true`
— resumes at the candidate/live legs once P37.65a stages the candidate and
P37.65b promotes. The seven-day cost read is owed at promotion+7d.

Catalog: `R11-K13-MAP-07` · Round 11 / P37 / sub-round 11D · Class S (≤1,500 changed
lines excl. generated/fixtures — well within: ~340 lines).

## Leg ledger (`sig-ops map-acceptance plan`)

| leg | stage | result | evidence |
|---|---|---|---|
| `journeys-fixture` | deterministic | **executed — PASS** | J1–J10 10/10 vs committed fixtures (`npx playwright test tests/e2e/map-journeys.spec.ts`, ordinary `test:e2e` config) **and** 10/10 vs the national build (`bash scripts/ci/national_budget_leg.sh journeys`, `SIG_DATA_SOURCE=national`, 15.3 s) |
| `budgets-fixture` | deterministic | **executed — PASS** | national wire-budget sweep 523/523 pages in bound (`bash scripts/ci/national_budget_leg.sh budgets`); LHCI national run: `/map/` T2 surface green both attempts (a11y 1.0, TTI bound met); T1 LCP marginal overages 0.3–3.7% on the host's slower envelope — the documented LH-LCP-MARGINAL-1 class, a rerun used, bounds never relaxed |
| `candidate-tiles` | candidate | `prepared_not_executed` — exit 42 | precondition: P37.65a stages the release candidate; `uv run sig-exports tiles verify --in <candidate-export-dir>` |
| `candidate-lhci` | candidate | `prepared_not_executed` — exit 42 | precondition: P37.65a stages the candidate; LHCI against the candidate build |
| `live-journeys` | live | `prepared_not_executed` — exit 42 | rides P37.65b promotion; `D-P37.63-1` |
| `live-lhci` | live | `prepared_not_executed` — exit 42 | rides P37.65b promotion; `D-P37.63-1` |
| `live-tiles` | live | `prepared_not_executed` — exit 42 | rides P37.65b promotion; `D-P37.63-1` |
| `cost-7d` | live | `prepared_not_executed` — exit 42 | K13 §9.5 / K1 MAP-07 seven-day cost read at promotion+7d; `D-P37.63-1` |

`sig-ops map-acceptance check` (committed, offline): "6 committed legs present; 6
gated legs declared prepared_not_executed". `run --leg <gated>` exits 42 with the
verbatim re-run prompt — never a production mutation.

## Fixture identity

- Generator `scripts/ci/build_national_fixture.py`, synthetic seed `20261022`,
  232,500 invented sites / 52 synthetic jurisdictions, CONUS-bounded
  (lat 25–48, lon −124…−67). Output `web/national/` (gitignored).
- National PMTiles: `sig_graph-sites.18479cf8.pmtiles`, `maxzoom 14`,
  209,292 points. National build: 523 pages, `"dataSource": "national"` in the
  page-types manifest.
- **Tile integrity:** `uv run sig-exports tiles verify --in` over the national
  export — **PASS, all checks** (conservation, precision/tier, size, metadata).

## J1–J10 corpus adaptations (all recorded in `map-journeys.spec.ts` comments)

- J1 anchor "Canberra" → "Oklahoma City" (synthetic fixture is CONUS-bounded).
- J2 vendor+ALPR facet adapted: national sites carry no vendor slot and no
  `dict.json`; the proof exercises compartment toggling + technology behaviour
  as honestly rendered.
- J3 `jurisdiction=` may yield zero national records (synthetic keys differ);
  the framing contract + print path are what is tested.
- J8: ratified 100 KiB no-JS bound under fixtures; recorded 800,000-byte
  measured gap under national.

## Defects the battery caught and the fixes landed

1. **Inert national place-group rows** (`model.ts`/`MapApp.tsx`):
   `tilePlaceRowsInView` required a `dict.json` jurisdiction bbox to frame a
   group row; national output lacks the dictionary, so every group row was a
   dead click. Fix: an evidence-derived fallback frame — the mean of the
   group's own drawn cell centroids at `NATIONAL_ZOOM_MAX+1` — dictionary bbox
   still preferred; nothing fabricated. Unit tests pin both paths
   (`map-app-model.test.ts`, 27/27).
2. **`focus=` never written for tile-path selections** (`MapApp.tsx`):
   `selectTileProps` now writes `focus=<rk>` into the workspace URL — share
   links carry the tile selection (J1).
3. **Shared tile focus didn't restore** (`MapApp.tsx`): a `focus=` deep link
   hit the fixture-record path, empty in tile mode. Fix: the focus effect
   consults `tileByRk.current` first and a late resolver retries as
   `viewRows`/sources land (also fixes late `sourcedata` list refresh).
4. **J6 hardcoded anchor** (`map-journeys.spec.ts`): national J6 reads its
   coordinate from the first published feature of `sites.geojson` — the
   deterministic artifact — and fails loudly if absent; fixtures keep
   `{35.47,-97.51}`.

## Visual grid — environment-limited, honestly recorded

Container run (`mcr.microsoft.com/playwright:v1.62.1-noble`, named volume):
**485–486/582 passed; ~97 cells over bound.** Failures are spread across every
template family (releases, data-dictionary, explore, search, watch-feeds, map,
print) and are text-wrap/glyph-metric reflows — e.g. releases-light-1440 13,133
px, data-dictionary-dark-1440 41,284 px, map-light-390 19,814 px — the same
diff class on map cells as on cells this change cannot touch. The map diffs
appear only at 390/320 where text wraps more; 1440 map cells pass. The P37.63
diff changes interaction behaviour, not rest-state pixels. The arm64-container
raster differs from the baseline-minting environment; **the amd64 CI visual
job is the authoritative adjudicator**. No baseline was adopted. Operator
gallery: 93 groups / 558 cells / 97 diffs — `prepared_not_executed`, sign-off
outstanding (K14 §7).

## Promotion & owed obligations

- Class S promotion is **recorded as riding P37.65** (GATE: publish rides
  P37.65 Class S — promotion is the operator's act). Nothing was promoted.
- `D-P37.63-1` records the deferred post-P37.65b live verification legs
  (journeys + LHCI + tiles against the promoted site) and the seven-day cost
  read, with the verbatim re-run command. Append-only obligation event is
  anchored under `docs/build/reports/obligations/`.

## return_pass

`D-P37.63-1` — post-promotion live verification (live-journeys, live-lhci,
live-tiles) + `cost-7d`, re-run `… live_verification=true` after P37.65b.
