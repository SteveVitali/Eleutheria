<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# P37.68d — consolidated UX capstone packet (`prepared_not_executed` on the gated legs)

**Status:** the deterministic legs **executed green** over the committed
fixtures build; every live + operator leg is `prepared_not_executed`
(OM-19) — the promoted P37.65 release does not exist yet (`D-P37.65b-1`,
the promote leg, is QUEUED behind the operator's HG-11 readout) and the
operator walkthrough is the operator's own act. No production mutation was
performed in this dispatch (`live_verification=false`).

**Re-run (verbatim):**
`implement-spec spec=docs/tickets/500_P37.68d__ux-capstone-per-ask-checks-and-walkthrough-packet.md live_verification=true`
— resumes at the live legs under the window `on the promoted P37.65
release; 390 px + 1440 px` (the plan cell, verbatim).

Catalog: `R11-K13-CAP-01` · Round 11 / P37 / sub-round 11D · size M
(≤3,000 changed lines excl. generated/fixtures). Split **d** — the
consolidating split — of the four-way CAP-01 split (FEA-04): P37.68a
carried advocate journeys A1–A4, P37.68b journalist journeys J1–J5,
P37.68c organizer journeys O1–O4; this row carries the **U-003.1…U-003.11
per-ask acceptance checks**, the **ROUTES.csv** advertised-route re-check,
**budgets + axe** on the real release, the **cost read** against the
$300/month ceiling (UXR-31 / SIG-UI-081), and the **consolidated
operator-walkthrough packet**.

Requirement ids: **SIG-UI-077** (every U-003.1…11 ask gets a named live
acceptance check, agent-verified, never "user-tested") and
**SIG-UI-078** (all 13 D3 journeys on the promoted release at 390 px +
1440 px, JS on and — where the journey allows — off, inside budgets, zero
wrong-conclusion risk, plus the operator walkthrough). Also cited:
**SIG-UI-081** (cost); draft family **UXR-31**.

## Leg ledger (`sig-ops capstone-consolidated plan`)

| leg | stage | result | evidence |
|---|---|---|---|
| `per-ask-fixture` | deterministic | **executed — PASS** | U-003.1…11 battery `web/tests/e2e/capstone-per-ask.spec.ts` under `web/playwright.capstone-consolidated.config.ts` over the publishable fixtures build (`npm run build` → 515 routes) at all four {1440, 390 px} × {JS, no-JS} cells: **52 passed / 0 skipped** (13 named checks × 4 cells) |
| `routes-csv-dist` | deterministic | **executed — PASS** | `web/tests/e2e/acceptance-routes-csv.spec.ts` over the emitted build: every `docs/build/planning/2026-09-30-next-phase/review/ROUTES.csv` row carries an explicit disposition (`resolves` / `retired` / `internal` / `namespace` / `external`), every `resolves` family emits or resolves, every `retired` row is covered by the one redirect generator, every `internal` row is never publicly emitted, and namespace/external rows are declared rather than passed — the expectation table is a bijection with the CSV (P36.72a / S4c COV-04) |
| `budgets-axe-fixture` | deterministic | **executed — PASS** | `budget.spec.ts` — the `sig.page-budgets/1` wire sweep (`web/tests/e2e/page-budgets.json`, all page types, gzip + brotli, before/after one scripted interaction per surface) — and the axe WCAG 2.2 AA sweep (`a11y.spec.ts` + `a11y-scripts-off.spec.ts`) over the emitted fixtures build: green, inside `npm run test:e2e` — the fixture read, never the release's measured bytes |
| `cost-ledger` | deterministic | **executed — under ceiling (estimate-bounded)** | `sig.capstone-cost-read/1` over `docs/build/reports/spend/spend_ledger.csv` month 2026-10: GCP cloud-account bound **$100** (estimate upper bound; `measured` $0 — billing-export rows pending) → **33% of the $300/month** ceiling; outside-cloud-account rows reported ($2 estimate + the $50 declared R2 hard cap named, never summed; 3 pending rows named) — the measured billing-export read is the queued `cost-read` leg |
| `live-per-ask` | live | `prepared_not_executed` — exit 42 | SIG-UI-077 on the promoted release: the same battery, `SIG_CAPSTONE_BASE_URL=<promoted-origin>`; inside it the corpus-named clauses read the release's own corpus — the sources-table row count, Austin Police Department + Vigilant Solutions (LEARN) with pages-or-typed-absences (D-K2-1), California's per-source breakdown, Seattle watch pages, Canberra/ICE/Vigilant query behaviour, the tile verifier's 0-missing, and the benchmark top-3 rates; `D-P37.68d-1` |
| `live-journeys` | live | `prepared_not_executed` — exit 42 | SIG-UI-078's consolidated 13-journey sweep: the three sibling spec files (`capstone-advocate`, `capstone-journalist`, `capstone-organizer`) at all four cells on the promoted origin — the sweep verdict this row records for the siblings' deferred live legs (D-P37.68a-1 / b-1 / c-1); inside it J4's durable `/s/<pub>/` half rides ACT-24 (HG-11), J5's real ≥2-release diff rides the activated predecessor, O1 rides I8/D-K2-1, O3 ACT-07, O4 D-K11-4; `D-P37.68d-1` |
| `live-routes-csv` | live | `prepared_not_executed` — exit 42 | the ROUTES.csv check repeated on the promoted bundle — its own `page-types.json` + `redirects.conf`, plus probes against the deployment URLs the release advertises for `external` rows; `D-P37.68d-1` |
| `live-budgets-axe` | live | `prepared_not_executed` — exit 42 | budgets + axe bound to the promoted bundle's own page-types manifest — measured over the release's bytes, never the fixture's; `D-P37.68d-1` |
| `cost-read` | live | `prepared_not_executed` — exit 42 | SIG-UI-081 / UXR-31's measured read — the billing export holds no rows (D-P34.5-2 export link); `D-P37.68d-1` |
| `walkthrough` | operator | `prepared_not_executed` — exit 42 | OP-22 — **requested, never simulated**; `WALKTHROUGH.md` committed with the blank record table; recorded `operator walkthrough (maintainer, not independent)`; `D-P37.68d-2` |

`sig-ops capstone-consolidated check` (committed, offline): "17 committed
legs present; 6 gated legs declared prepared_not_executed".
`run --leg <gated>` exits 42 with the verbatim re-run prompt — never a
production mutation.

## What the per-ask fixture battery proved (agent-verified — never user-tested)

Every check resolves its targets from the served site itself — the A–Z
directory supplies the dossier routes, the `/sources/` table supplies the
source pages, the dossier artifacts supply the contribution rows, the
queue supplies the task handles — so the identical spec runs against the
promoted origin with `SIG_CAPSTONE_BASE_URL` and fails loud on any surface
the release does not carry. Recorded **agent-verified** (P4): a machine
walkthrough, never user research and never "user-tested".

| ask | named check | fixture verdict |
|---|---|---|
| U-003.1 | map, self-hosted basemap, place context, located records, linked place/source/evidence, the no-JS map limit | **pass** — the `/map/` doc names the self-hosted style contract and the no-JS limit; the located-record dossier's `map-embed.json` carries located records whose jurisdiction links resolve |
| U-003.2 | readable labels, no UUID labels, named entities, dated-or-undated edges, evidence reachability, `/explore/` navigability | **pass** — a bounded crawl of the public families carries 0 UUID labels; entity index pages name entities or show the typed not-published state; overview graphs are navigable |
| U-003.3 | flexible search — the GET/no-JS form, release-pinned shards/indexes, honest empty results | **pass** — the server-rendered `/search/` GET form, `sig.search-index/1` + `sig.typeahead-shard/1` machinery, and the typed empty-result contract |
| U-003.4 | dossier list grouped by country → state/subdivision, "Not yet placed" | **pass** — `group-us` / `group-other` headings, resolvable state links, the unplaced group, the split-jurisdiction marker where present |
| U-003.5 | "from N sources" breaks down to the figure; source page names last run + first/last seen | **pass** — a dossier's `sig-figure` value equals the `web/dossier_sources` artifact's `totals.records` equals the per-source `records` sum; a contributing source's execution-keyed runs page carries dated `run-row` entries (the first/last-seen span) |
| U-003.6 | dossier map/network visualization + scoped search | **pass** — a located-record dossier shows Figure 1, prints it, carries the activate control and the scoped search |
| U-003.7 | `/watch` answers — watch JSON/feed contracts or the honest empty state | **pass** — a place watch page renders items or the typed empty state; its feeds validate |
| U-003.8 | `/evidence` artifact listing + lane-aware binding/absence | **pass** — the index lists artifact rows, each carrying a binding state; links resolve or name the absence |
| U-003.9 | sources table sortable without JS; rows/columns; downloads/version/metrics/ground-truth links where the lane permits; honest withheld/gated states | **pass** — every advertised `/sources/sort/` URL resolves; non-published rows name their own state; every published page carries the invariant record (subnav, runs, versions, licence, rights, publication basis); ≥1 published page carries homepage + terms links |
| U-003.10 | per-source detail — metadata, rights, conduct, execution-keyed history, hashed captures, downloads where the lane allows, dossier contribution, changelog | **pass** — a published source carries the full required testid contract; `runs/` is execution-keyed; `captures/` carries content hashes; `dossiers/` resolves |
| U-003.11 | research queue usability — canonical task redirect, page/card limit, records-request drafts that are explicitly drafts and never sent | **pass** — a canonical task id 301s (edge) or emits the alias-stub successor page linking the `T-` handle (the static-host form of the same contract); the queue page is titled and ≤50 cards; drafts are explicitly drafts |

## Route check verdict (`routes-csv-dist` — deterministic)

Every `ROUTES.csv` row carries an explicit disposition; no route silently
lacks a declaration. `resolves` families emit/resolve; `retired` rows are
covered by the redirect generator; `internal` rows are never publicly
emitted; namespace absences and external/promoted-release routes are
honestly declared. The release-side repeat is `live-routes-csv`
(`D-P37.68d-1`).

## Budget + axe verdict (`budgets-axe-fixture` — deterministic)

The wire sweep holds every emitted route inside `sig.page-budgets/1`
(`page-budgets.json` — generated `lighthouserc*.json` mirrors unedited)
and axe reports no WCAG 2.2 AA violation on the fixtures build — the
fixture read. The measured read on the release's own bytes is
`live-budgets-axe` (`D-P37.68d-1`); a fixture green is never claimed as a
release measurement.

## Cost status (UXR-31 / SIG-UI-081)

Committed-ledger read (`cost-ledger` leg): the latest month is **under
ceiling — estimate-bounded**: $100 GCP bound = 33% of $300/month;
measured $0 because the billing export holds no rows (D-P34.5-2);
outside-cloud-account rows named, never summed into the bound. The
measured billing-export read is `cost-read` (`D-P37.68d-1`).

## Operator walkthrough (OP-22 — requested, never simulated)

`WALKTHROUGH.md` is staged for all 13 journeys + the per-ask surface at
390 px + 1440 px with a **blank** record table — no simulated operator
words, no simulated verdicts, no proxy signature, no gate-affecting
record. It records `operator walkthrough (maintainer, not independent)`.
`D-P37.68d-2`.

## Honest limits (named, never smoothed)

- The fixture corpus is small and synthetic: the battery proves the
  surface machinery, not the release's data scale. The promoted-release
  legs are the live halves — `D-P37.68d-1`.
- Corpus-named clauses (named entities such as Austin PD / Vigilant
  Solutions LEARN, California's per-source breakdown, Seattle watch
  pages, tile-coverage and benchmark-top-3 rates) read the release's own
  corpus on the live leg; the fixture exercises the machinery and the
  typed-absence pass states, never a smoothed figure (I8, D-K2-1,
  D-K3-7).
- D3's global-graph answer is the aggregated overview-graphs reading
  (D-K13-1), not a national hairball — the battery checks the overview
  families, never a rendered nation-scale graph.
- The `walkthrough` leg is the operator's act: the packet is committed
  and **requested**, never simulated; no agent label counts as a human
  label (`D-P37.68d-2`, OP-22 / TS-22).
- The cost read is committed-ledger truth, labelled estimate-bounded; the
  billing export holds no rows (D-P34.5-2) so the measured UXR-31 read is
  queued, not claimed.
- A1–A4 (landed P37.68a), J1–J5 (landed P37.68b), O1–O4 (landed
  P37.68c) journey batteries are the sibling splits' machinery — this row
  records their consolidated sweep posture, never re-executes or
  re-defers them.
