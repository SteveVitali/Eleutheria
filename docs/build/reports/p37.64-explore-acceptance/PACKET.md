<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# P37.64 — entity, graph & dossier-figure acceptance packet (`prepared_not_executed` on the live leg)

**Status:** deterministic half **executed green** over the committed fixture corpus
and the emitted dist; the single live leg (`1: verify after P37.65b promotes` — the
plan cell, verbatim) is `prepared_not_executed` (OM-19). No production mutation was
performed in this dispatch (`live_verification=false`).

**Re-run (verbatim):**
`implement-spec spec=docs/tickets/492_P37.64__entity-graph-dossier-figure-acceptance.md live_verification=true`
— resumes at the `live-verify` leg once P37.65b promotes, inside the `AR-3 + AR-2`
window. The obligation is registered as `D-P37.64-1` (DEFERRALS) with the
`D-P37.64-1:e0` obligation-event anchor.

Catalog: `R11-K13-ACC-EXPLORE` · Round 11 / P37 / sub-round 11D · Class M (≤3,000
changed lines excl. generated/fixtures). Gate: `Class S readout content folds into
P37.65` — this packet is that readout content.

## Leg ledger (`sig-ops explore-acceptance plan`)

| leg | stage | result | evidence |
|---|---|---|---|
| `dist-sweep` | deterministic | **executed — PASS 15/15** | `npx playwright test tests/e2e/acceptance-explore.spec.ts` over all 515 emitted fixture routes |
| `journeys` | deterministic | **executed — PASS 15/15** | `npx playwright test tests/e2e/acceptance-explore-journeys.spec.ts` — J-1…J-6, VJ-1…VJ-6, K13 §8 capstone legs, axe in interaction states |
| `budgets` | deterministic | **cited — PASS** | national wire-budget sweep, 523/523 pages in bound (P37.63's national build; the activated in-place-map box is measured by `budget.spec.ts`'s scripted interaction) — re-read at the CI perf job |
| `live-verify` | live | `prepared_not_executed` — exit 42 | rides P37.65b promotion; `D-P37.64-1` |

`sig-ops explore-acceptance check` (committed, offline): "6 committed legs present;
1 gated legs declared prepared_not_executed". `run --leg live-verify` exits 42 with
the verbatim re-run prompt — never a production mutation.

## Requirement coverage (engineering layer — fixture-verified, never live-executed)

| id | disposition | where |
|---|---|---|
| SIG-UI-D20 | PASS — 0 UUID/key patterns in visible text on all emitted pages; every overview `l` label resolves to a legible label | `acceptance-explore.spec.ts` (the crawl also caught two bare `cap:*` evidence keys on the internal curate page — fixed by wrapping in `sig-mut`) |
| SIG-UI-DV01 | PASS — every place dossier draws fig-map + caption contract or shows the typed absence; the place-level table follows where children exist | sweep |
| SIG-UI-DV02 | PASS — declared binning mode agrees with drawn mark classes (points↔h3-areas, never mixed) | sweep |
| SIG-UI-DV03 | PASS — ≤40 linked nodes, three access kinds drawn + toggled without JS, table-twin edge parity, no ranking copy, undrawn slots carry no svg | sweep + VJ-3/VJ-6 |
| SIG-UI-DV04/DV06 | PASS — every dossier carries the three `v=2` explore links; keyed dossiers carry `jurisdiction=` + the release-pinned scoped GET form; unkeyed dossiers link unscoped (no facet claimed, nothing misrepresented) | sweep + scoped-search.spec.ts + VJ-4 |
| SIG-UI-DV05 | PASS — zero `/_astro/` bytes on dossier pages; only allow-listed `/_kit/` modules; activation reuses the reserved box, keeps the static figure, writes no history | sweep + dossier-activate.spec.ts + VJ-4/VJ-6 |
| SIG-UI-DV07 | PASS — every emitted fig1 svg ≤60 elements and ≤30 KiB gzip | sweep |
| SIG-UI-DV08 | PASS — every print route: brief first, terms last, as-of+permalink on every page, no script/control/canvas; **gap found + fixed:** the drawn fig-map printed only where `print_figures` was declared (the fixture `oklahoma-city` only) — `planPrintPages` now derives the map figure page from the drawn visuals doc, never a placeholder over a drawable figure | sweep + `web/src/lib/print.ts` + `print.astro` |
| SIG-UI-DV09 | PASS — skip links, table twins with equal values, labelled SVGs; axe WCAG 2.2 AA in rest + node-selected + activated-map + post-close states | sweep + journeys (J-6, VJ-6) |
| SIG-UI-DV10 | PASS (records side) — figure value = twin `desc.records_total` = `rollup.records` = children Σ + placed_only_here = caption decomposition; `map-recon` value = drawn count; every `map-embed.json` self-consistent. **Adaptation (recorded, not silently skipped):** the fixture sites model is a thin demo layer — figure counts are records-units while embed `pointCount`/`unplotted` are site-rows; the "summed map cells" equality binds at real scale and is owned by the live-verify leg (tile cells verified by `sig-exports tiles verify`; the app's in-view sums by the map-journeys battery at national scale) | sweep; cells side → `live-verify` |
| SIG-UI-DV11 | PASS — every `sig-fig-*` class inside emitted figure SVGs ⊆ the lexicon `FIGURE_CLASSES`; every drawn edge kind named in the page legend | sweep |
| SIG-UI-DV12 | PASS — no per-area data attributes or per-mark `<title>` on figure marks; no `dossier-visuals`/`inputs` path in dist | sweep |

## Journey dispositions (labelled agent walkthroughs — never user research)

| journey | result | adaptation (recorded) |
|---|---|---|
| K2 J-1 (Texas supply/access) | PASS | figure half walks `/dossier/usa/ok/` (the fixture's drawn access figure); explorer walk follows the dossier's own link; `/graphs/access/usa/tx/` covers the Texas JS-off parity leg — also the K13 §8 J2 leg |
| K2 J-2 (evidence for a vendor–agency link) | PASS | Acworth PD relation row → `#claim-…` anchor in ≤2 actions; JS-off parity asserted |
| K2 J-3 (who runs / what the city bought) | PASS | fixture pair: Acme City Police (agency) + Acworth ALPR expansion contract — both reachable from the dossier figure + `/entity/` hub; ER disclosure rendered; no merge claim |
| K2 J-4 (Acworth PD still sharing?) | PASS | historical-marked edge + "partners not named" degree fact + the `/task/` link; no present-tense sharing claim |
| K2 J-5 (everything behind the graph) | PASS | all four supply downloads serve; CSV edge rows = page rows; `dict.labels` resolve |
| K2 J-6 (keyboard/SR) | PASS | Tab reaches the evidence link; Escape clears explorer selection; axe clean rest/node-selected states |
| K6 VJ-1 (Oklahoma City → print) | PASS | every drawn mark `sig-fig-src-single` (greyscale-safe by class, not colour); caption names the one-source rule; print page 2 leads the map; as-of+permalink on every page — also the K13 §8 A3 leg |
| K6 VJ-2 (390 px no-JS) | PASS | state→county→place drill-down via the place table; the sites list opens |
| K6 VJ-3 (access figure → entity → explorer → cite) | PASS | fixture walks usa/ok (Texas's slot is the typed absence); declared-toggle hides marks CSS-only; agency node links; explorer handoff carries `overview=access&jurisdiction=`; cite mints the snapshot form |
| K6 VJ-4 (Harris County → in-place map) | PASS | scoped-search form contract (GET + release-pinned + hidden scope); the `/v1/` endpoint is the API surface and does not emit into static dist — the results leg walks the equivalent `/search/?v=2&…` facet URL and records the adaptation; activation, source filter, cite, full-map, no history writes — also the K13 §8 O1 leg |
| K6 VJ-5 (source breakdown → show on map) | PASS | `dsrc-records` figure = Σ per-source cells; "Show on the map" carries `jurisdiction=` + `source=`; target applies or names the facet |
| K6 VJ-6 (keyboard + SR) | PASS | skip link lands the table twin; toggles work by keyboard (Space); activate/close by keyboard returns focus; axe clean activated + post-close |
| K13 §8 J3 (disputed figure) | PASS | dossier disagreements link → `/disagreements/place/usa/tx/` resolves 200 |

## Not automatically verifiable here (recorded, never silently skipped)

- **DV10's "summed map cells" side** — needs real-scale tile data + the running app; owned by `live-verify` (D-P37.64-1). The records-side chain is green.
- **DV08's page-split + greyscale raster legs** (PyMuPDF / rendered-PDF) — DOM-level checks are green; the raster half is a live leg.
- **Release-pinned `/v1/` federated search** — not emitted into the fixture dist; the form contract is asserted and the equivalent facet URL walked; the live leg verifies the release route.
- **Operator walkthrough** — K13 §8's operator half is a human act, never claimed by the agent.

## Defect fixed in this dispatch

- **DV08 print gap** — jurisdiction dossiers printed no figure page because
  `print_figures` is a record field the export does not populate in the fixture
  corpus. `web/src/lib/print.ts` `planPrintPages` gained `derivedFigures` (a kind
  the record declares is never shadowed); `print.astro` derives the drawn-map
  declaration from the visuals doc. Now all 10 drawn-map print routes print the
  map on page 2; `usa/vi` (typed absence) correctly prints none.
- **D20 curate leak** — two bare `cap:*` evidence keys on the internal
  contradictions page wrapped in `sig-mut`.
