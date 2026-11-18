<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# P37.68c — capstone organizer journeys packet (`prepared_not_executed` on the gated legs)

**Status:** deterministic half **executed green** over the committed fixtures
build; the live + operator legs are `prepared_not_executed` (OM-19) — the
promoted P37.65 release does not exist yet (`D-P37.65b-1`, the promote leg,
is QUEUED behind the operator's HG-11 readout) and the operator walkthrough
is the operator's own act. No production mutation was performed in this
dispatch (`live_verification=false`).

**Re-run (verbatim):**
`implement-spec spec=docs/tickets/499_P37.68c__ux-capstone-organizer-journeys.md live_verification=true`
— resumes at the live legs under the window `on the promoted P37.65
release; 390 px + 1440 px` (the plan cell, verbatim).

Catalog: `R11-K13-CAP-01` · Round 11 / P37 / sub-round 11D · size M (≤3,000
changed lines excl. generated/fixtures). Split **c** of the four-way CAP-01
split (FEA-04): this row walks the organizer journeys **O1–O4**; P37.68a
carried A1–A4, P37.68b carried J1–J5, and P37.68d carries the
U-003.1…11 per-ask checks, the ROUTES.csv re-check, budgets and axe on the
real release, and the consolidated packet.

Requirement ids: the contract names **no §56 `Owner:` id** for this row;
the contract cites **SIG-UI-081** inside the cost leg; draft family
**UXR-31**.

## Leg ledger (`sig-ops capstone-organizer plan`)

| leg | stage | result | evidence |
|---|---|---|---|
| `journeys-fixture` | deterministic | **executed — PASS** | O1–O4 battery `web/tests/e2e/capstone-organizer.spec.ts` under `web/playwright.capstone-organizer.config.ts` over the publishable fixtures build (`npm run build` → 515 routes) at all four {1440, 390 px} × {JS, no-JS} cells: **16 passed / 0 skipped** — every O-journey is fully no-JS-compatible, so all four legs ran at all four cells |
| `cost-ledger` | deterministic | **executed — under ceiling (estimate-bounded)** | `sig.capstone-cost-read/1` over `docs/build/reports/spend/spend_ledger.csv` month 2026-10: GCP cloud-account bound **$100** (estimate upper bound; `measured` $0 — billing-export rows pending) → **33% of the $300/month** ceiling; outside-cloud-account rows reported ($2 estimate + the $50 declared R2 hard cap named, never summed; 3 pending rows named) — the measured billing-export read is the queued `cost-read` leg |
| `live-journeys` | live | `prepared_not_executed` — exit 42 | precondition: the P37.65 release promoted (`D-P37.65b-1` — the operator's HG-11 act) AND `live_verification=true`; inside it O1's named-agencies reading follows the release's own placement/publication state (**I8, D-K2-1** — the typed absence is a legitimate pass state), O3's per-compartment attribution reading rides **ACT-07** (K13 §7.4 orders the attribution re-export before any download link), O2's agenda items ride the **WX-02/03** producers, and O4's named channel is settled per **D-K11-4**; `SIG_CAPSTONE_BASE_URL=<promoted-origin> npx playwright test -c playwright.capstone-organizer.config.ts`; `D-P37.68c-1` |
| `cost-read` | live | `prepared_not_executed` — exit 42 | SIG-UI-081 / UXR-31's measured read — the billing export holds no rows (D-P34.5-2 export link); `D-P37.68c-1` |
| `walkthrough` | operator | `prepared_not_executed` — exit 42 | OP-22 — **requested, never simulated**; `WALKTHROUGH.md` committed; recorded `operator walkthrough (maintainer, not independent)`; `D-P37.68c-2` |

`sig-ops capstone-organizer check` (committed, offline): "5 committed legs
present; 3 gated legs declared prepared_not_executed".
`run --leg <gated>` exits 42 with the verbatim re-run prompt — never a
production mutation.

## What the fixture battery proved (agent-verified — never user-tested)

- **O1** — who runs what in my county or city: the A–Z-resolved county
  dossier (Harris County — the fixture's O1 anchor) carries the header
  strip's record figure, Figure 1's caption ("…of N published records" +
  the release stamp), the "What is deployed" section's named record
  class, and the "Who runs and supplies it" figure slot — the fixture
  renders the **typed absence** (the release places no entity with the
  recorded relationship) whose overview link resolves (200); the
  dossier's own "Sites list →" link reaches the per-record sites table.
- **O2** — who decides and when; subscribe: the dossier's *Next
  decisions* block names the agenda item (approving body + next date —
  the fixture names the Harris County Commissioners Court item, marked
  contested); the *Watch upcoming decisions →* place link reaches the
  watch page (items or typed empty state); the `.ics` subscribe link
  GETs a valid RFC 5545 calendar (`BEGIN:VCALENDAR` / `VERSION:2.0` /
  `PRODID` / `END:VCALENDAR`) — the feed exists even at zero items.
- **O3** — a local list without the map: the A–Z-resolved city dossier's
  "Sites list →" reaches the no-JS sites table — every row a published
  precision cell (coords or typed no-coords); each rendered licence
  compartment (`sig_graph`, `public_record`, `osm_physical` on the
  fixture) carries its compartment name and licence line (CC-BY-4.0 /
  ODbL-1.0); *Download this view (CSV)* GETs a 200 CSV whose header
  carries the `# licence:` line and `compartment`/`licence` columns.
- **O4** — act on a gap: the A–Z scan finds the dossier whose
  "What we don't know" gap resolves to **the open task** (the absence
  chip's named resolution — the fixture's legacy OKC deployment dossier
  carries two), one click to `/task/<handle>/`: the plain-language
  subject/why, the closing condition, "SIG sends nothing; you file it
  yourself", the records-request draft (statute, agency, template body,
  downloadable `.txt`, "a template, not legal advice"), and the
  operator-named reporting channel (D-K11-4 — the dispute/correction
  channel; never an invented address). The research queue's DRAFT badge
  is the named fallback path where a dossier carries no task-bearing
  gap.

Every journey resolves its targets from the served site itself — the A–Z
directory supplies the dossier routes, the dossier's own blocks supply
the sites/next-decisions links, the gap→task links and the queue supply
the task pages — so the identical spec runs against the promoted origin
with `SIG_CAPSTONE_BASE_URL` and fails loud on any surface the release
does not carry. Recorded **agent-verified** (P4): a machine walkthrough,
never user research and never "user-tested".

## Honest limits (named, never smoothed)

- The fixture corpus is small and synthetic: the battery proves the
  surface machinery, not the release's data scale. The promoted-release
  legs are the live halves — `D-P37.68c-1`.
- O1's "named agencies" reading follows the release's own placement and
  organisation-publication state (I8, D-K2-1 — K13 §4.2): the fixture
  exercises the typed-absence pass state, never a smoothed figure.
- O3's per-compartment attribution reading rides ACT-07 (the attribution
  re-export); the committed surface proves the compartment/licence
  machinery — the release's own attribution is the live leg's.
- O4's "where to send results" is the operator-named channel (D-K11-4 —
  settled); the page names the dispute/correction channel and never
  invents one.
- The `walkthrough` leg is the operator's act: the packet is committed
  and **requested**, never simulated; no agent label counts as a human
  label (`D-P37.68c-2`, OP-22 / TS-22).
- The cost read is committed-ledger truth, labelled estimate-bounded; the
  billing export holds no rows (D-P34.5-2) so the measured UXR-31 read is
  queued, not claimed.
- A1–A4 (landed P37.68a), J1–J5 (landed P37.68b), the U-003.1…11
  per-ask checks, budgets + axe on the real release and the ROUTES.csv
  re-check (P37.68d) are split scope — recorded here as carried, never
  executed or deferred twice.
