# ADR-236 — SAM.gov sweep: persist the rotating cursor, set the budget to the measured quota (P37.11)

- Date: 2026-11-06
- Status: accepted
- Ticket: P37.11 (Round 11 / P37, row 432 — R11-SRC-02; the named home of
  D-FEDERAL.1-1; answers the ADR-089 revisit trigger — "the prioritised keyword
  set grows past the budget" / "a 429 is observed on a fresh Monday window" —
  which fired as the *measured quota* sitting below the keyword count)
- Base: `r11/P37.10-asset-promotion-gate`
- Related: ADR-089 (the bounded quota-aware sweep this amends — decisions 1 and
  5; its no-re-probe stop, `quota_governed` counting and `max_retries=0`
  transport are unchanged), D-FEDERAL.1-1 (the OPEN deferral this row serves),
  GATE-G6 §4 pre-authorization (2026-11-05T15:20Z) + §3 ING-GO-D, R4 F4.24
  (the 10-requests/day free-tier measurement), F1 NEW-1 (the starvation read),
  `connectors/procurement.py`, `connectors/runner.py`, `ops/scheduled.py`,
  `ops/cli.py`, `connectors/data/procurement_vocab.toml`, `ops/cadence.toml`.

## Context

ADR-089 shipped `daily_request_budget = 30` ≥ the 19-keyword count on the
premise that one fresh-window run covers the whole prioritised space — the
paged cursor was left inert ("no cross-run persistence is required" was
explicitly recorded as a rejected alternative). The premise failed on the
measured quota, not the plan: `sig-sam-gov-key` serves ~10 requests/day on the
free tier (documented 10 requests/day — the seeded registry's `VERIFIED`
row; hosted run rows served 11 and 12 before the 429 wall:
`sig-ingest-sam-gov-z99t7` 2026-09-22 `12/30 sweep request(s)`, the
2026-09-28 cron `11/30`, both ending `quota_reached`). The F1 owed-register
read (NEW-1) shows the consequence: every run issues the first ~11 slices,
hits the wall, defers the same 7-slice tail — and because nothing persisted
the cursor, the next run restarted at keyword 0 and starved the tail again.

## Decision

1. **The budget is the measured quota.** `[sam_gov_sweep].daily_request_budget`
   is now `10` — the measured free-tier daily quota with the observed wall
   (11–12 served) sitting just above it, so the stop lands on the budget
   (`budget_reached`, headroom) rather than the 429 wall whenever the window
   is fresh. ADR-089's "budget ≥ keyword count" bound is superseded by this
   ADR; the no-re-probe machinery it introduced is untouched.
2. **The rotating cursor persists on the run rows themselves.** The run row's
   `fetch_record` now carries `sweep_cursor` (the offset this run resumed at)
   and `sweep_cursor_next` (the offset the next run resumes from). The WORM
   `ops/runs/sam_gov/<date>/<ts>.json` object is therefore the persisted
   cursor — append-only by construction, no new store.
3. **Resume is just past the last issued selected slice.**
   `sam_gov_sweep_resume(keywords, budget, cursor, skipped_keywords)` returns
   `(start + issued_selected) mod n`: each `sweep_skipped` governed slice maps
   back to its selected keyword (generated `samgov:kw:<keyword>` ids verbatim;
   a supplied search slice via the `title` param of its recorded URL), so a
   mid-page stop leaves the cursor at the deferred boundary rather than at 0.
   When nothing was skipped this equals `sam_gov_sweep_plan`'s own next offset;
   when the whole page was skipped (a 429 on request one — an already-spent
   window) the cursor is unchanged and the same page retries on the next fresh
   window.
4. **The scheduled wrapper seeds the next run from the newest stored row.**
   `ops.scheduled.latest_sweep_cursor` reads the newest run row
   (GCS `ops/runs/` authoritative, local mirror the fallback):
   `fetch_record.sweep_cursor_next` when present; else the row's
   `sweep_requests` — a pre-P37.11 row still records exactly where it stopped,
   so it seeds the first paged run; else 0. A corrupt or non-run object under
   the prefix is skipped, never a fabricated position. `scheduled_ingest`
   threads `sweep_cursor` into `run_source` only when set (a runner that
   predates it is called exactly as before), and the audit row's detail logs
   `sweep cursor <a>→<b>`.
5. **Two weekly fires cover the space.** At budget 10 < 19 keywords, fire 1
   covers keywords 0–9 and leaves `sweep_cursor_next = 10`; fire 2 resumes at
   10, covers 10–18 (plus the supplied head slice) and wraps. The deferral
   closes after two consecutive fires advance the cursor — the ticket's
   acceptance shape.

## Consequences

- The paged tail (the 7 deferred slices, then the rotating remainder) is
  covered by successive `sig-sched-sam-gov` weekly fires instead of being
  re-starved every run — D-FEDERAL.1-1's last engineering item.
- A run meeting an already-spent window still stops on the first 429 and
  leaves the cursor unchanged — the same page is retried next window, never
  re-probed within it.
- The hosted land: the cron `0 5 * * 1` apply (the live trigger still reads
  `0 5 1 * 1` pending the queued P35.1b sweep leg), the fetch + claim writes,
  and the +0 re-run count are the ticket's named OM-20 mutation —
  pre-authorised by GATE-G6 §4 verbatim ("Approve all 15", 2026-11-05T15:20Z,
  expiry GATE-ACCEPT-R11) and run in-ticket only when the contract's own
  preconditions hold (`SIG_GCP_PROJECT` + the keyed job env); otherwise the
  leg stays QUEUED `prepared_not_executed` with the recorded reason.
- `procurement_notice` claim shape, append-only spine, the X-Api-Key
  credential header, and every non-`sam_gov` source are unchanged.

## Alternatives considered

- **Keep budget 30 and let the quota stop do the paging.** Rejected — a
  budget the key cannot serve means every run burns to the 429 wall instead
  of stopping at headroom; the measured quota is the honest bound
  (SIG-ENG-042: measured figures reported as measured).
- **A dedicated cursor object/table instead of the run rows.** Rejected — the
  run rows are already the append-only WORM audit trail each execution writes;
  the newest row's `sweep_cursor_next` *is* the cursor, so a second store
  would be state that can disagree with the audit trail. The fetch record's
  fields make the cursor inseparable from the run that produced it.
- **A smaller-than-10 budget for extra headroom.** Rejected — 10 is the
  measured/documented daily tier; the observed wall (11–12) sits above it, so
  10 already carries headroom without lengthening the paged tail past the
  ticket's two-fire shape.
- **Key-tier upgrade to run the whole space in one fire.** Out of scope — an
  operator/HG-09 credential act (carried on the deferral), not an engineering
  change.

## Revisit trigger

- The **measured daily quota moves** (an operator key-tier upgrade, a changed
  api.data.gov tier, or a fresh-window run stopping short of 10) — re-measure
  and re-set `daily_request_budget`.
- A **`sweep_cursor_next` regression** (a run row whose next offset restarts
  coverage early, or two consecutive fires that do not advance the cursor) —
  the acceptance shape is broken; re-examine the seed read or the
  skipped-slice mapping before touching the planner.
- The **keyword set or the supplied-slice shape changes** (new keywords, or a
  governed slice that is not `samgov:kw:*`-id-able and carries no `title`
  param) — the skip→keyword mapping needs its rule widened.
- The **weekly cadence changes** (e.g. a daily cron on a 10/day key) — a
  daily fire meets a fresh window every time, so the cursor's page width and
  the window cost should be re-measured together.
