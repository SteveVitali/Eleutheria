# ADR-089 — Bound the SAM.gov sweep to one daily quota window (request budget + no-re-probe stop)

- **Status:** Accepted
- **Phase / ticket:** Phase 26 / P26.19 (`docs/tickets/P26.19__bounded-sam-gov-sweep.md`)
- **Date:** 2026-09-22
- **Related:** D-FEDERAL.1-1 (the OPEN deferral this closes), P26.14 (the widened
  sweep that over-issued), P26.4 (the keyed X-Api-Key transport, HG-09),
  SIG-INGEST-011/012/013 (politeness + the recorded rate-limit lesson: refused
  requests count, never re-probe a 429), `connectors/net.py`,
  `connectors/pipeline.py`, `connectors/runner.py`, `connectors/procurement.py`,
  `connectors/data/procurement_vocab.toml`, `ops/scheduled.py`, `ops/cadence.toml`.

## Context

The P26.14 widened SAM.gov sweep fans out over the 19-keyword surveillance
vocabulary, one bounded `title` query per keyword through the shared politeness
layer. The key `sig-sam-gov-key` authenticates through the api.data.gov gateway,
which meters requests **per UTC day** — the 429 body names the reset verbatim:
`"You have exceeded your quota. You can access API after <date> 00:00:00+0000 UTC"`.

Two failure modes compounded (D-FEDERAL.1-1, evidence recorded there):

1. **Retry-into-re-burn.** The live `HttpxTransport` backs off and retries a 429
   up to `max_retries` (3) honouring `Retry-After` — correct etiquette for a
   *slot-exhaustion* API like Overpass, but for a *daily-request-count* quota a
   retry is another counted request against an already-exhausted window. Once the
   window was gone, every keyword slice retried 3× with backoff, so executions
   `lz4rx` (3600s) and `5z456` (14400s) were SIGKILLed fighting 429s.
2. **Sweep-past-the-wall.** The driver recorded each 429 as a disappearance and
   *continued* to the next keyword — issuing more counted requests into the dead
   window, so each failed run re-burnt the fresh quota and the next run started
   already-throttled (the Monday cron `k5bbv` also failed this way).

`sam_gov` therefore sat at its original 7 claims (the P26.4 bounded slice). The
request *cost* (19 slices) is not itself the problem — 19 ≪ the daily tier — the
problem is honouring the recorded rate-limit lesson: **refused requests count;
never re-probe a 429; stop cleanly before the wall.**

## Decision

1. **A per-run request budget bounds one run to a single fresh window with
   headroom.** `[sam_gov_sweep].daily_request_budget` (30) caps the quota-governed
   requests one run issues. It is `>=` the keyword count, so one fresh-window run
   covers the whole prioritised keyword space — full coverage, no multi-day tail.
2. **The driver stops cleanly at the wall, and never re-probes it.** Each SAM.gov
   opportunity-search slice is flagged `quota_governed`; the generic driver
   (`connectors/pipeline.py`) counts every such request it *issues* (a refused
   request still counts) against `request_budget`, and on the **first 429** sets
   `quota_reached` and stops the sweep — the remaining slices are recorded as
   *deferred, not issued* (`sweep_skipped`), never re-probed. Reaching the budget
   before any 429 stops with headroom (`budget_reached`). Non-opted-in targets and
   sources see none of this — the fields default off and behaviour is unchanged.
3. **The SAM.gov transport never retries a 429.** `runner._run_live` builds
   `HttpxTransport(max_retries=0)` for `sam_gov`, so a 429 surfaces immediately as
   a `ChallengeEncountered` rather than being backed-off-and-retried (a re-probe
   that re-burns). `ChallengeEncountered` now carries the HTTP `status` so the
   driver tells a 429 quota wall apart from a 401/403 auth challenge. Every other
   source keeps the default backoff-retry (Overpass slot etiquette is unchanged).
4. **The outcome is recorded honestly.** The per-run request count, the budget,
   and the stop reason ride the `FetchRecord` (→ committed `live_runs/` record)
   and the `ops/runs` row; a run that hit the wall records the `quota_reached`
   run outcome (exit 0 — a clean bounded stop, never a crash or a fabricated
   green). The secret stays on the `X-Api-Key` header from Secret Manager — never
   in the URL, the record, or the ledger (P26.4 / HG-09, unchanged).
5. **A paged cursor pages the space when the budget is below the keyword count.**
   `sam_gov_sweep_plan(keywords, budget, cursor)` rotates the prioritised keyword
   order by `sweep_cursor` and returns the next resume offset, so if an operator
   lowers the budget below the keyword count, successive daily runs cover the full
   space across windows — never one run over quota. At the shipped budget the
   cursor is inert (one run is complete), so no cross-run persistence is required.
6. **Scheduling meets a fresh window.** `sig-sched-sam-gov` fires `0 5 * * 1`
   (every Monday 05:00 UTC) — 5h after the documented 00:00 UTC daily reset, an
   unambiguous weekly cadence (the prior `0 5 1 * 1` also fired on the 1st of the
   month; `sam_gov` uses its own key, so 05:00 Monday is a genuinely fresh window).

## Consequences

- One bounded SAM.gov run fits comfortably inside a single daily quota window with
  headroom and can never wedge into a 429 SIGKILL — D-FEDERAL.1-1's structural
  blocker is fixed. Full coverage lands in one run, so the deferral **closes** on
  the live land (no by-design paged-coverage tail at the shipped budget).
- A run that meets an already-exhausted window (e.g. an operator ran it manually
  the same day) stops after one counted request with an honest `quota_reached`
  outcome, never re-burning the window — the exact anti-pattern the ticket fixes.
- The `procurement_notice` claim shape is unchanged; the change is sweep-width,
  transport-retry, scheduling, and run-record only (additive / back-compat).

## Alternatives considered

- **Key-tier upgrade so the full sweep runs as-is.** Out of scope — a paid/tiered
  api.data.gov key is an operator/HG-09 action, not an engineering change. Noted in
  the run doc as the lever that would remove the budget entirely.
- **A rolling recent-notices date window instead of a budget.** The measured
  request cost (19 slices) already fits the daily tier, so a date window would not
  address the re-burn; the budget + no-re-probe stop is the load-bearing fix. The
  posted window is retained as-is and remains an available future lever.
- **Disable 429 retry globally.** Rejected — a 429 backoff is correct etiquette for
  slot-exhaustion APIs (Overpass); only a daily-request-count quota makes a retry a
  re-burn. Scoped to `sam_gov` (the api.data.gov-metered source in scope); the same
  treatment for the other api.data.gov-keyed sources is a follow-on, not this ticket.
- **Persist the cursor in GCS for cross-run paging now.** Rejected as unnecessary at
  the shipped budget (one run is complete); building durable cross-run state for an
  inert cursor is speculative. The planner + `sweep_cursor` parameter make paging a
  tested capability the operator can turn on by lowering the budget.

## Revisit trigger

- The api.data.gov **daily tier changes** (an operator key-tier upgrade, or a
  documented limit change) — re-measure and raise/remove `daily_request_budget`.
- The prioritised **keyword set grows past the budget** — then the paged cursor
  becomes load-bearing and needs durable cross-run persistence (a new ADR).
- A **429 is observed on a fresh Monday window** despite the bound (another caller
  shares the key, or the reset moved) — re-examine the schedule/window assumption.
- The other **api.data.gov-keyed sources** (congress_gov, fbi_cde) exhibit the same
  re-burn — generalise the no-429-retry treatment beyond `sam_gov` by a new ADR.
