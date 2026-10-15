# P35.1a1 — `P35.1a1-seed-declared-jobs-live` leg records (engineering landed; live leg QUEUED — no mutation)

The single authorized live leg of
`docs/tickets/287a_P35.1a1__seed-declared-jobs-paused.md` (manifest row
287a; the D-P34.42b-2 bridge — operator selection **"Create 12 paused
jobs"**, LEDGER GATE DECISIONS 2026-10-14T19:34Z) is
`ops/gcp/seed-declared-jobs.sh --apply` against project
`zeta-medley-508121-u7` (region `us-central1`). It creates exactly the
twelve declared-but-absent Cloud Run jobs (the ten `sig-ingest-r11-*`
wave batches + the two `sig-ingest-*-tribal-*` screened-lane jobs) on the
project default compute identity — labelled
`runtime-identity=temporary-default-compute` and migrated to
`sig-ingest-rt` by the later `P34.42b-live-2` leg — grants the already
existing `sig-scheduler` `roles/run.invoker` on each new job, and creates
each declared Cloud Scheduler trigger **then immediately pauses it**
(R6 step 1). Harness `devin-desktop/swe-2-high/subagent`.

- **Window:** AR-3 + AR-2 — a weekday 14:00–20:00Z slot. The 2026-10-14
  window closed before head-bound CI on the implementation PR could
  complete (the contract runs the leg only after the scripted `--check`
  plan and head-bound CI are green), so the leg is honestly **QUEUED** in
  RETURN PASS for the next valid slot — `date -u` reads 2026-10-14T21:0xZ
  at this writing. `SIG_SEED_NOW` exists only so the offline guard test
  can exercise the window check; apply exits 42 outside the slot.
- **Authorisation:** the operator's verbatim `confirmation` row for
  D-P34.42b-2 (GATE DECISIONS row 321, 2026-10-14T19:34Z) — one-leg
  scoped: exactly the twelve job creates, their `sig-scheduler` invoker
  bindings, and their paused trigger creates. It does not authorize the
  P34.42b identity migration, a P35.11 wave leg, an HG-03 rights flip, or
  any `main` operation. Expires on completion; voided by a failed AR-2
  capture, a red probe, or a production read that contradicts the
  contract or the recorded decision.

## Outcome so far: QUEUED — production untouched

No production mutation ran, is running, or is claimed. The committed
evidence is the offline `--check` plan under `check/` (no ADC, no
network):

- `check/check-plan.txt` (+ `check/check-plan.out` console transcript) —
  the closed twelve-row contract read from `ops/cadence.toml`, the
  contract-pinned image digest
  (`sig-api@sha256:6ad5477d4aacde23d508f5eea765a6ad835e603ad794b10df56710acca4414f5`),
  the temporary-identity label, and the **36 planned mutations in the
  contract's order** (per row: absence re-check → job create →
  `run.invoker` binding → trigger create → pause → PAUSED read-back) —
  12 job creates, 12 invoker bindings, 12 trigger creates, 12 pauses.
  No `run jobs execute`, no `scheduler jobs run`, no resume, no
  `scheduled-ops.sh` reconcile.
- `check/target-rows.txt` — the resolved `kind|id|job|scheduler|cron|
  task_timeout` rows, byte-compared to the contract table by the script.
- `check/sha256s.txt` — `sha256  <relpath>` sidecars for both captures.

## Fail-closed contract the script enforces (test-pinned)

`tests/ops/test_seed_declared_jobs.py` (28 tests, offline) pins every
refusal the leg must carry:

- **Closed set:** `ops/cadence.toml` drift — a changed cron/timeout/
  job/scheduler field, a missing row, an extra `r11-*` batch or tribal
  source, an `existing = true` mark, or a declared `secrets` list —
  refuses (exit 2) before any plan.
- **Pinned image:** unset `SIG_JOB_IMAGE` deploys the contract pin; a
  `sig-api@sha256:` ref must equal the pin exactly; a tag resolves at
  apply and must land on the pin; a foreign repo, `:latest`, a bare ref,
  or any other digest refuses.
- **Existing targets refuse:** a present target job or trigger (prestate
  or mid-leg) stops the leg — never update, never upsert.
- **Temporary identity, labelled:** every deploy runs as
  `<projectNumber>-compute@developer.gserviceaccount.com` with the
  `runtime-identity=temporary-default-compute` label; the interim
  `default-compute`/`sig-ingest-rt` drift on exactly these twelve jobs is
  expected state owned by P34.42b-live-2 (287a § Temporary runtime
  identity), never hidden.
- **Pause-on-create ordering + rollback:** a trigger create that does not
  read back `PAUSED` rolls back everything this leg created — triggers
  first, then the added bindings, then the jobs — replaying
  `created.txt`; a pre-existing resource is never touched.
- **Poststate:** exactly `expected_job_count` (100) jobs, the twelve
  describes matching image/timeout/retries/args/mount/Cloud-SQL/env/
  secret, twelve `PAUSED` triggers with declared cron/`Etc/UTC`/URI/
  oauth SA, and a no-executions read for all twelve.

## Queued next action (the leg itself)

```
ops/gcp/seed-declared-jobs.sh --apply --evidence-dir <dir>
```

run inside the next weekday 14:00–20:00Z AR-3 slot with the operator's
ADC armed and the operator's authorization in force (the recorded
selection stands until consumed or voided). After it records a 100/100
poststate: `P34.42b-live-2` re-captures AR-2 and runs its own authorized
jobs-IAM leg (migrating all 100 jobs to `sig-ingest-rt` et al.), then
`P35.1a-live-2` retries `ops/gcp/scheduled-ops.sh --apply --paused` per
the operator's "Use --paused" selection (2026-10-14T17:09Z). Neither is
run by this ticket.
