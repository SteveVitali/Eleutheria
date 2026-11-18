<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# P37.68b — capstone journalist journeys packet (`prepared_not_executed` on the gated legs)

**Status:** deterministic half **executed green** over the committed fixtures
build; the live + operator legs are `prepared_not_executed` (OM-19) — the
promoted P37.65 release does not exist yet (`D-P37.65b-1`, the promote leg,
is QUEUED behind the operator's HG-11 readout) and the operator walkthrough
is the operator's own act. No production mutation was performed in this
dispatch (`live_verification=false`).

**Re-run (verbatim):**
`implement-spec spec=docs/tickets/498_P37.68b__ux-capstone-journalist-journeys.md live_verification=true`
— resumes at the live legs under the window `on the promoted P37.65
release; 390 px + 1440 px` (the plan cell, verbatim).

Catalog: `R11-K13-CAP-01` · Round 11 / P37 / sub-round 11D · size M (≤3,000
changed lines excl. generated/fixtures). Split **b** of the four-way CAP-01
split (FEA-04): this row walks the journalist journeys **J1–J5**; P37.68a
carried A1–A4, P37.68c carries O1–O4, and P37.68d the U-003.1…11 per-ask
checks, the ROUTES.csv re-check, budgets and axe on the real release, and
the consolidated packet.

Requirement ids: the contract names **no §56 `Owner:` id** for this row;
the contract cites **SIG-UI-081** inside the cost leg; draft family
**UXR-31**.

## Leg ledger (`sig-ops capstone-journalist plan`)

| leg | stage | result | evidence |
|---|---|---|---|
| `journeys-fixture` | deterministic | **executed — PASS** | J1–J5 battery `web/tests/e2e/capstone-journalist.spec.ts` under `web/playwright.capstone-journalist.config.ts` over the publishable fixtures build (`npm run build` → 515 routes) at all four {1440, 390 px} × {JS, no-JS} cells: **22 passed / 2 skipped** — the two skips are the J2 JS typeahead/explore leg under the two no-JS cells, by design; every no-JS leg ran its named equivalent |
| `cost-ledger` | deterministic | **executed — under ceiling (estimate-bounded)** | `sig.capstone-cost-read/1` over `docs/build/reports/spend/spend_ledger.csv` month 2026-10: GCP cloud-account bound **$100** (estimate upper bound; `measured` $0 — billing-export rows pending) → **33% of the $300/month** ceiling; outside-cloud-account rows reported ($2 estimate + the $50 declared R2 hard cap named, never summed; 3 pending rows named) — the measured billing-export read is the queued `cost-read` leg |
| `live-journeys` | live | `prepared_not_executed` — exit 42 | precondition: the P37.65 release promoted (`D-P37.65b-1` — the operator's HG-11 act) AND `live_verification=true`; inside it J4's durable `/s/<pub>/` pinned-URL leg rides **ACT-24 (HG-11)** (K13 §7.4: "TX-13b rides ACT-24; J4 cannot pass before it") and J5's real ≥ 2-release diff (**CF-13**) needs the promoted release's activated predecessor; `SIG_CAPSTONE_BASE_URL=<promoted-origin> npx playwright test -c playwright.capstone-journalist.config.ts`; `D-P37.68b-1` |
| `cost-read` | live | `prepared_not_executed` — exit 42 | SIG-UI-081 / UXR-31's measured read — the billing export holds no rows (D-P34.5-2 export link); `D-P37.68b-1` |
| `walkthrough` | operator | `prepared_not_executed` — exit 42 | OP-22 — **requested, never simulated**; `WALKTHROUGH.md` committed; recorded `operator walkthrough (maintainer, not independent)`; `D-P37.68b-2` |

`sig-ops capstone-journalist check` (committed, offline): "5 committed legs
present; 3 gated legs declared prepared_not_executed".
`run --leg <gated>` exits 42 with the verbatim re-run prompt — never a
production mutation.

## What the fixture battery proved (agent-verified — never user-tested)

- **J1** — defend a headline figure: the Texas dossier's Figure 1
  caption carries the unit and denominator ("…of 5120 published
  records"), the "Not a census" wording and the release id; the named
  breakdown anchor resolves; the figure's evidence row links the source
  artifact (GET 200 — ≤ 2 actions to evidence); *Downloads* → the rows
  table resolves.
- **J2** — who supplies ALPRs to Texas agencies; who can access the
  data: JS leg — typeahead `tex` → Texas dossier → the dossier's own
  *See connections →* bar → the scoped graph view mounts with named
  nodes (or a typed absence — never a silent empty canvas), and the
  access overview is reachable inside the island. No-JS leg — the GET
  search form contract holds; the A–Z directory reaches the dossier;
  `/graphs/` → the access overview → its advertised place drill-down
  (`/graphs/access/usa/tx/`) lists every edge dated or typed "undated",
  historical edges marked, each naming its source ("Eyes on Flock");
  the supply overview links named entity pages.
- **J3** — is this figure disputed: the dossier's **≠** contested marker
  → one click on "All disagreements for <place> →" → every typed kind
  section (contradictions, coordinate conflicts, declared-vs-located,
  co-located) with records or typed absences; from `/disagreements/` the
  recorded contradiction shows both sides — source, observed/recorded
  dates and the claim-page link (200).
- **J4** — cite it durably: the *Cite* block records the as-of
  world/belief pair + ruleset; the permalink carries the
  `?as_of_world=…&as_of_belief=…&ruleset=…` selector; the interim
  sentence states "an immutable citable copy is not yet published"
  (never the "reproducible" phrase over a non-pinned URL); the legacy
  selector URL resolves (200 — within the K13 200/404/409 contract). The
  pinned `/s/<pub>/` identical-bytes leg rides ACT-24 — asserted, never
  claimed.
- **J5** — what changed since the last release: `/changes/` shows the
  release pair (world + belief dates), keeps "**The world changed**"
  and "**SIG's records changed**" apart on the page, and the feed
  directory resolves per-place/per-source `.atom` feeds plus
  `all.atom` + the OPML bundle. The fixture pair is synthetic — the
  real ≥ 2-release diff (CF-13) is the gated live leg's job.

Every journey resolves its targets from the served site itself — the A–Z
directory supplies the dossier route, the dossier's explore bar supplies
the scoped graph URL, the disagreements index supplies the contested
place, the feed directory supplies the `.atom` — so the identical spec
runs against the promoted origin with `SIG_CAPSTONE_BASE_URL` and fails
loud on any surface the release does not carry. Recorded
**agent-verified** (P4): a machine walkthrough, never user research and
never "user-tested".

## Honest limits (named, never smoothed)

- The fixture corpus is small and synthetic: the battery proves the
  surface machinery, not the release's data scale. The promoted-release
  legs are the live halves — `D-P37.68b-1`.
- J4's durable `/s/<pub>/` half cannot pass before ACT-24 (HG-11) —
  K13 §7.4 names it; the fixture leg proves only the interim cite
  contract.
- J5's "real ≥ 2-release diff" (CF-13) needs two activated releases;
  the fixture's synthetic pair proves the page/feed machinery only.
- The `walkthrough` leg is the operator's act: the packet is committed
  and **requested**, never simulated; no agent label counts as a human
  label (`D-P37.68b-2`, OP-22 / TS-22).
- The cost read is committed-ledger truth, labelled estimate-bounded; the
  billing export holds no rows (D-P34.5-2) so the measured UXR-31 read is
  queued, not claimed.
- A1–A4 (landed P37.68a), O1–O4 (P37.68c), the U-003.1…11 per-ask
  checks, budgets + axe on the real release and the ROUTES.csv re-check
  (P37.68d) are split scope — recorded here as carried, never executed
  or deferred twice.
