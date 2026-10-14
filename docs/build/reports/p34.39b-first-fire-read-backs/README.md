# P34.39b — first-fire read-backs (queued-leg evidence)

Ticket: `docs/tickets/248_P34.39b__first-fire-read-backs.md` (row 248, H2 PR-1, stacked on `r11/P34.39a-osm-replay-read-back`).
Command: `sig-ops scheduled-firstfire --leg l1|l2|l3` (`ops/src/ops/scheduled_firstfire.py`), read-only.

## What this directory holds

The three legs' **queued** guard reports, captured live (reads only —
`gcloud scheduler jobs list`, `gcloud run jobs executions list`; no GCS/PG
reads were needed for the queued state) on 2026-10-07 against
`zeta-medley-508121-u7` / `us-central1`:

| file | leg | guard result |
|---|---|---|
| `queued-l1-2026-10-07.json` | l1 | exit 42 — the wave is still open; window closes `2026-10-21T06:09Z`. 33 queued first fires enumerated (matches G1 §7.1's count). |
| `queued-l2-2026-10-07.json` | l2 | exit 42 — `camreg_peel_on` first fire `2026-10-29T12:00Z` is in the future; no `lastAttemptTime`, no post-fire execution. |
| `queued-l3-2026-10-07.json` | l3 | exit 42 — same peel-on guard; 34 queued fires (the wave + peel-on). |

All three legs are **queued, never executed** — the verbatim re-run prompt
(`implement-spec spec=docs/tickets/248_P34.39b__first-fire-read-backs.md live_verification=true`)
is recorded in each report's `leg_status.rerun_prompt` and in the RETURN PASS
row's re-run cell.

## The fleet table

`fires[]` carries, per evaluated trigger: `fleet_id`, `kind` (source/batch),
`scheduler`, `job`, `cron`, `state`, `first_fire` (+ `first_fire_basis` —
deployed-vs-attempted derivation), `execution`, `run_rows` (+ `run_row_count`),
`completion`, `verdict`, `routing`. `named_reads[]` (l1/l3) records the
contract's `sam_gov` @ `2026-10-01T05:00Z` and `muckrock` @ `2026-10-01T06:00Z`
evidence rows; `routing_rows[]` is the leg's DEFERRALS input;
`untracked_schedulers[]` surfaces live triggers outside the declared fleet.

Verdicts: `ok` / `failed` / `anomaly` / `pending` / `not_evaluable` — evidence
not yet collected lands in `not_evaluable`, never `fail`; a green in fixtures
(`tests/ops/fixtures/scheduled_firstfire/`) is a `layer: fixture` report,
never a live record.

No production mutations: every gather is a read; the command never re-executes,
never cancels, never blocks a GATE.
