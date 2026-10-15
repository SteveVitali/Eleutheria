# P35.1a — `P35.1a-live-scheduled-ops` leg records (live-1 attempt; OM-18 stop, no mutation)

The queued OM-19 live leg of
`docs/tickets/264_P35.1a__scheduler-of-record-live-diff-cron-lint.md`
(`ops/gcp/scheduled-ops.sh --apply` reconciling Cloud Scheduler from
`ops/cadence.toml` + the first in-band `sig-ops live-diff --live` run) was
dispatched 2026-10-14 on live-leg branch `r11/P35.1a-live-1` (cut from the
chain tip `r11/P36.15-redaction-pipeline` @ `1f043d12`) against project
`zeta-medley-508121-u7` (region `us-central1`). Harness
`devin-desktop/swe-2-high/subagent`.

- **Window:** AR-3 + AR-2 — Wednesday 2026-10-14, captures at
  14:50–14:52Z (`date -u` stamps in `pre/capture-stamp.txt` and the
  transcripts), inside the weekday 14:00–20:00Z band, operator-present
  dispatch with the operator's ADC armed.
- **Authorisation:** GATE-G4 OM-20 11B list (LEDGER GATE DECISIONS
  2026-10-09T17:32Z) names P35.1a verbatim — "deploy `scheduled-ops` + the
  first live-diff run"; expires GATE-G5 (not yet held). Valid at dispatch.

## Outcome: STOPPED before the mutation — nothing was applied

The AR-2 prestate (under `pre/`, sha256 sidecars in `pre/sha256s.txt`)
surfaced a production read that contradicts the recorded authorization's
premises, so the `voided-by` clause (a production read that contradicts a
record) fired and the leg stopped per OM-18 before any `--apply`:

1. **Missing job-class runtime identities (P34.42b's still-queued leg).**
   The committed `ops/gcp/scheduled-ops.sh` binds every job deploy to the
   P34.42b class SAs — `sig-probe` to `sig-probe-rt@…` (script lines ~104,
   ~361) and every `sig-ingest-*` job plus `sig-replay-ingest` to
   `sig-ingest-rt@…` (~105, ~394, ~437, ~468). The live SA inventory
   (`pre/service-accounts.json`) carries only the default compute SA,
   `sig-scheduler` (invoker), and the three P34.42a service SAs
   (`sig-api-rt`, `sig-web-rt`, `sig-alerts-rt`). `sig-probe-rt`,
   `sig-ingest-rt`, `sig-export-rt`, `sig-materialize-rt` do **not** exist —
   `iam-job-identities.sh` (P34.42b's leg, still queued in RETURN PASS;
   its S5-3 OM-20 pre-authorisation expired at GATE-G4) creates them. The
   first `gcloud run jobs deploy` the apply would issue (`sig-probe`)
   would be refused by Cloud Run for a nonexistent service account, and
   deploying the fleet onto a substituted identity would silently do (or
   undo) P34.42b's scoped mutation — neither is the authorised act.
   (`pre/run-jobs.json`: all 88 live jobs still run as the default compute
   SA — the identity migration has not run.)
2. **Declared scope grew past the authorised mutation.** The chain-tip
   `ops/cadence.toml` now declares triggers that did not exist when the leg
   was queued on 2026-10-10 (the 2026-10-10 live read recorded exactly two
   missing triggers: `sig-sched-live-diff` + `sig-sched-pg-logical-export`).
   Today's live-diff (`logs/live-diff-run1.out`, exit 1, 52 findings)
   records 14 missing declared triggers — the two above plus the ten
   `sig-sched-r11-*` wave batches and the two `sig-sched-*-tribal-*`
   screened-lane rows — and 12 missing declared jobs. Every one of the
   wave/screened rows carries the "created `--paused` (R6)" note: the
   verbatim plain `--apply` this leg is authorised for would create them
   **ENABLED**, contradicting the R6 first-run protocol and encroaching on
   P35.11's wave legs (ING-GO-A / OP-26 flip lists). The authorised command
   names no `--paused` flag, so there is no in-scope way to reconcile the
   current declaration verbatim.

The read-only half of the leg — the in-band `sig-ops live-diff --live` run —
ran and is honest evidence, not a consumed leg: the contract result is the
apply + the diff together, and the apply never ran.

## What ran (all times `date -u`; transcripts in `logs/`)

| step | result |
|---|---|
| prestate capture (14:50:39–14:51:5xZ) | `pre/` — enabled APIs, Scheduler jobs list (79 triggers, all ENABLED), Cloud Run jobs list (88) + describes (`sig-probe`, `sig-export`, `sig-materialize`, `sig-replay-ingest`, `sig-ingest-muckrock`, `sig-ingest-sam-gov`), `sig-probe` invoker IAM, service describes + IAM (`sig-api`/`sig-web`/`sig-alerts`), project IAM, per-bucket info + IAM (×4), SA inventory |
| `sig-ops live-diff --live` (14:52:1xZ) | exit 1 — **52 findings**: 15 schedule (14 missing declared triggers + `sig-sched-sam-gov` cron `0 5 1 * 1`→`0 5 * * 1`), 18 job_config (6 undeclared live jobs → P35.1b; 12 missing declared jobs — the `r11-*`/tribal rows), 8 image drift (stale `63b809b2…`/`d1f94361…` vs fleet `6ad5477d…`), 1 public_posture (`sig-web` `allUsers` live vs declared private — D-P34.3-1's queued posture), 4 ubla, 3 versioning, 3 lifecycle |
| `scheduled-ops.sh --apply` | **not run** — OM-18 stop before the mutation |

## Sanitization

The operator's account e-mail is replaced by `<redacted-operator-account>`
in every committed byte (the Round-11 rule: the operator's personal e-mail
is never added to a file). Cloud Run `creator`/`lastModifier` annotations
and the project IAM `user:` member carried it in raw output. No secret
value was read, printed, logged or persisted — secret *names* only.

## Files

- `pre/` — the AR-2 capture taken before any mutation decision (all reads;
  `capture-stamp.txt` carries `date -u` + branch/sha; `sha256s.txt` covers
  the committed, sanitized bytes).
- `logs/` — capture transcripts + the full `live-diff --live` run
  (`live-diff-run1.out` = the `sig.live-diff/1` payload; `…err` = the DRIFT
  list + exit); `sha256s.txt` sidecar.
- No `post/` — no mutation ran, so production at leg end is exactly `pre/`.
- The leg's record lives in `docs/build/runs/P35.1a.md` (appended section),
  the decision in `docs/tickets/DEFERRALS.md` (`D-P35.1a-1`), and the queued
  row in `docs/build/tools/record_policy/return_pass.toml` (`P35.1a`,
  leg `P35.1a-live-scheduled-ops` — still queued).
