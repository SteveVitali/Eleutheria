<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# P37.68a — capstone advocate journeys packet (`prepared_not_executed` on the gated legs)

**Status:** deterministic half **executed green** over the committed fixtures
build; the live + operator legs are `prepared_not_executed` (OM-19) — the
promoted P37.65 release does not exist yet (`D-P37.65b-1`, the promote leg,
is QUEUED behind the operator's HG-11 readout) and the operator walkthrough
is the operator's own act. No production mutation was performed in this
dispatch (`live_verification=false`).

**Re-run (verbatim):**
`implement-spec spec=docs/tickets/497_P37.68a__ux-capstone-advocate-journeys.md live_verification=true`
— resumes at the live legs under the window `on the promoted P37.65
release; 390 px + 1440 px` (the plan cell, verbatim).

Catalog: `R11-K13-CAP-01` · Round 11 / P37 / sub-round 11D · size M (≤3,000
changed lines excl. generated/fixtures). Split **a** of the four-way CAP-01
split (FEA-04): this row walks the advocate journeys **A1–A4**; P37.68b
carries J1–J5, P37.68c O1–O4, and P37.68d the U-003.1…11 per-ask checks,
the ROUTES.csv re-check, budgets and axe on the real release, and the
consolidated packet.

Requirement ids (stamped in the PR): **SIG-UI-077**, **SIG-UI-078** (owner,
spec §56); Also: **SIG-UI-081**; draft family **UXR-31**.

## Leg ledger (`sig-ops capstone-advocate plan`)

| leg | stage | result | evidence |
|---|---|---|---|
| `journeys-fixture` | deterministic | **executed — PASS** | A1–A4 battery `web/tests/e2e/capstone-advocate.spec.ts` under `web/playwright.capstone.config.ts` over the publishable fixtures build (`npm run build` → 515 routes) at all four {1440, 390 px} × {JS, no-JS} cells: **20 passed / 4 skipped** — the four skips are the two JS-only A1 typeahead legs under the two no-JS cells, by design; every no-JS leg ran its named equivalent |
| `cost-ledger` | deterministic | **executed — under ceiling (estimate-bounded)** | `sig.capstone-cost-read/1` over `docs/build/reports/spend/spend_ledger.csv` month 2026-10: GCP cloud-account bound **$100** (estimate upper bound; `measured` $0 — billing-export rows pending) → **33% of the $300/month** ceiling; outside-cloud-account rows reported ($2 estimate + the $50 declared R2 hard cap named, never summed; 3 pending rows named) — the measured billing-export read is the queued `cost-read` leg |
| `live-journeys` | live | `prepared_not_executed` — exit 42 | precondition: the P37.65 release promoted (`D-P37.65b-1` — the operator's HG-11 act) AND `live_verification=true`; `SIG_CAPSTONE_BASE_URL=<promoted-origin> npx playwright test -c playwright.capstone.config.ts`; `D-P37.68a-1` |
| `cost-read` | live | `prepared_not_executed` — exit 42 | SIG-UI-081 / UXR-31's measured read — the billing export holds no rows (D-P34.5-2 export link); `D-P37.68a-1` |
| `walkthrough` | operator | `prepared_not_executed` — exit 42 | OP-22 — **requested, never simulated**; `WALKTHROUGH.md` committed; recorded `operator walkthrough (maintainer, not independent)`; `D-P37.68a-2` |

`sig-ops capstone-advocate check` (committed, offline): "5 committed legs
present; 3 gated legs declared prepared_not_executed".
`run --leg <gated>` exits 42 with the verbatim re-run prompt — never a
production mutation.

## What the fixture battery proved (agent-verified — never user-tested)

- **A1** — type "Oklahoma City", reach its place dossier in ≤ 3 clicks.
  Home hero typeahead → first suggestion names Oklahoma City → dossier;
  the header/search typeahead returns the same place (UXR-24) — at 390 px
  the inline header search collapses to the Search link by design and the
  leg follows it to `/search/`'s typeahead. No-JS leg: the hero form is a
  plain `GET` to `/search/` and the A–Z directory
  (`/dossier/a-z/o/` → Oklahoma City) reaches the dossier.
- **A2** — the place dossier answers with sourced values or typed
  absences: *At a glance* ("records" wording), *Where this comes from*
  (named sources + share), *Next decisions* (item or typed absence), the
  visible as-of/build stamp and the release stamp rendered.
- **A3** — dossier → print route: the council brief carries the locator,
  permalink, terms and run-head stamps (as-of + release id on the page).
- **A4** — the print brief's *documents to bring* block resolves; *What
  we don't know* → research queue → a records-request task → the draft
  downloads (`.draft.txt`, 200) with "SIG sends nothing" stated.

Every journey resolves its targets from the served site itself — the A–Z
directory supplies the dossier route, breadcrumbs supply the print
ancestor, the queue supplies the task — so the identical spec runs against
the promoted origin with `SIG_CAPSTONE_BASE_URL` and fails loud on any
surface the release does not carry. Recorded **agent-verified** (P4):
a machine walkthrough, never user research and never "user-tested".

## Honest limits (named, never smoothed)

- The fixture corpus is small and synthetic: the battery proves the
  surface machinery, not the release's data scale. The promoted-release
  legs are the live halves — `D-P37.68a-1`.
- The `walkthrough` leg is the operator's act: the packet is committed
  and **requested**, never simulated; no agent label counts as a human
  label (`D-P37.68a-2`, OP-22 / TS-22).
- The cost read is committed-ledger truth, labelled estimate-bounded; the
  billing export holds no rows (D-P34.5-2) so the measured UXR-31 read is
  queued, not claimed.
- J1–J5, O1–O4, the U-003.1…11 per-ask checks, budgets + axe on the real
  release and the ROUTES.csv re-check are P37.68b/c/d's named scope —
  recorded here as carried split scope, never executed or deferred twice.
