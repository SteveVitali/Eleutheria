<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# P36.46 — ingestion-history backfill `live` leg packet (`prepared_not_executed`)

**Status:** `prepared_not_executed` (OM-19) — the `hosted` environment is
absent in this run context (no `SIG_GCP_PROJECT`, no ADC, no claim-spine
writer DSN, no recorded authorisation). The engineering + machinery + this
packet landed; the named mutation queues here.

**Re-run (verbatim):**
`implement-spec spec=docs/tickets/389_P36.46__execution-keyed-ingestion-history.md live_verification=true`
— resumes at the backfill; the view + import machinery is re-runnable and
append-only.

## The named mutation (OM-20, GATE-G5 §4 — expires GATE-G6)

`ops/gcp/ingestion-history.sh --apply` — the append-only ingestion-history
backfill on the hosted spine:

1. `sig-ops backfill-run-reports --role sig_materialize --dry-run` — the
   plan report over every WORM `ops/runs/**.json` row (linked `live` /
   `backfill:<basis>` / `unmatched:<reason>` by the P31.2 matcher) plus
   the repo-pinned `docs/build/reports/live_runs/*.json` records
   (`link_basis=repo_record`, `clock_basis=git_only`).
2. the same command without `--dry-run` — INSERT-only `ingest_run_report`
   rows; `ON CONFLICT` under the `backfilled_from` unique key makes every
   re-run a +0 no-op.
3. a second `--dry-run` — the +0 read-back the run ledger records.

**Window:** `AR-3 + AR-2` — never inside 03:00–06:30Z or the monthly batch
window (day 6 00:00Z → day 13 12:00Z); the script exits 42 (queued).

**Restore point:** the appended set's digest list — the reconcile
read-back's `link_basis`/`clock_basis` counts plus the `backfilled_from`
URI set the report prints; wrong rows are corrected by new superseding
rows, never UPDATE/DELETE (the table's immutability trigger).

**Preconditions:** ADC + `SIG_GCP_PROJECT` + `SIG_BACKFILL_DSN` (a login
able to `SET ROLE sig_materialize` — env only, HG-09) +
`SIG_BACKFILL_AUTHOR` (the recorded operator authorisation) +
`SIG_OPS_GCS_BUCKET` + cloud-sql-proxy on PATH.

## What landed (the non-production half)

- `db/deploy/ingest_run_report_execution_key.sql` (+ revert/verify +
  sqitch.plan) — `ingest_run_report` gains NULL-tolerant `mode`/`kind`
  (run-row execution metadata; `mode` CHECK live|replay|shadow);
  `v_transparency_run` gains appended `execution_key` (the C-14 merge key:
  `completion:<id>` else `run-row:<object name>` else `repo:<path>` else
  `report:<id>` — the gs:// locator never leaves the view) + `mode`/`kind`.
- `db/src/db/run_report.py` — `append_report` mode/kind with the
  column-presence guard; `ops/src/ops/run_report.py` — the three writers
  populate them from the recorded evidence.
- `exports/src/exports/transparency.py` — `sig.execution-record/1` (the
  `sig.run-record/1` shape renamed + `execution_key`, `mode`, `kind`,
  `code_identity`) emitted as per-source
  `transparency/sources/<id>/executions.jsonl`; the packaged
  `code_identity` carries the C-13 ownership rule (`not_recorded (shared
  run)`, `not_recorded` on `"unknown"`).
- `ops/gcp/ingestion-history.sh` — the leg driver (`--check` prints the
  plan offline; window guard exit 42).
