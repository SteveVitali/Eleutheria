# P34.42b — `P34.42b-jobs-iam` leg records (live-1 attempt; OM-18 stop, no mutation)

The queued OM-19 live leg of
`docs/tickets/252_P34.42b__least-privilege-job-identities-remove-editor.md`
(`ops/gcp/iam-job-identities.sh --apply all` — job-class service accounts,
least-privilege bindings, 88→100 job identity updates, scheduler-invoker
move, then `roles/editor` removal) was dispatched 2026-10-14 on live-leg
branch `r11/P34.42b-live-1` (forked from `213909bd`, the last green P35.1a
pause-record head on chain tip `r11/P36.15-redaction-pipeline`) against
project `zeta-medley-508121-u7` (region `us-central1`). Harness
`devin-desktop/swe-2-high/subagent`.

- **Window:** AR-3 + AR-2 — Wednesday 2026-10-14, reads/capture at
  17:33–17:37Z (`date -u` stamps in `pre/capture-stamp.txt` and the
  transcripts), inside the weekday 14:00–20:00Z preferred band, operator's
  ADC armed (`gcloud auth application-default print-access-token` OK).
- **Authorisation:** the fresh one-leg GATE DECISIONS `confirmation` row
  (LEDGER, 2026-10-14T17:09Z — operator selection **"Full P34.42b leg"**,
  recorded after the S5-3 OM-20 11A listing expired at GATE-G4); scoped to
  exactly the contract's scripted mutations; voided-by a red probe, a
  failed restore point or a contradicting production read.

## Outcome: STOPPED before the mutation — nothing was applied

The read-only checks and the script's own `prestate` capture surfaced a
production read that contradicts the committed declaration, so the
`voided-by` clause fired and the leg stopped per OM-18 before any
`--apply` mutation:

**The declared job map expects 100 live jobs; production holds 88.**
`ops/iam_identities.toml` carries `expected_job_count = 100` and a
100-entry `job_map` resolved from `ops/cadence.toml` — it includes the
twelve post-queue jobs (the ten `sig-ingest-r11-*` wave batches and the
two `sig-ingest-*-tribal-*` screened-lane jobs) that the TOML comment
records were to be *"created PAUSED by `scheduled-ops.sh --paused` before
this leg's re-count"*. The operator's recorded ordering (D-P35.1a-1, GATE
DECISIONS 2026-10-14T17:09Z) runs **this** leg first and the P35.1a
`--paused` retry second — so those twelve jobs do not exist yet. Two
independent reads agree: `gcloud run jobs list` (17:34Z,
`logs/live-job-names.txt` = 88) and the script's own capture
(`pre/run-jobs.json` = 88). All 88 live jobs still run as the default
compute SA; `pre/project-iam.json` still binds `roles/editor` to
`873541617837-compute@developer.gserviceaccount.com`.

The script refuses exactly as designed — three fail-closed guards, no
mutation:

1. `_capture` itself dies on the first declared-but-absent describe:
   `iam-job-identities.sh --apply prestate` exit 1 —
   `ERROR: (gcloud.run.jobs.describe) Cannot find job
   [sig-ingest-camreg-tribal-all-leaders-directory]`
   (`logs/prestate.out`); `pre/` is truncated there (34 JSON captures +
   `sha256s.txt` over what was captured, `capture-stamp.txt`).
2. `_assert_map_covers` would refuse on the same read:
   `live job count 88 != declared 100` + `declared job(s) absent live:
   <the 12>` (exit 4).
3. `assert_no_executions` fails closed on the 12 absent jobs (an
   unreadable executions list is treated as running → exit 42).

The twelve declared-but-absent jobs are listed in
`logs/absent-declared-jobs.txt` (zero live-but-unmapped — every live job
is covered by the declared map).

## What ran (reads only)

| step | result |
|---|---|
| `iam-job-identities.sh --check all` | exit 0 — the full ordered plan (prestate → identities → bindings → jobs → invokers → editor → verify/analysis/rollback) rendered against the declaration (`logs/check-all.out`) |
| `sig-ops iam plan --json --leg jobs` | `expected_job_count=100`, `job_map`=100, 4 classes, 91 scheduler triggers (`logs/iam-plan-jobs.json`) |
| `gcloud run jobs list` re-count | **88** live jobs (`logs/live-job-names.txt`) |
| `iam-job-identities.sh --apply prestate` | exit 1 — captured `pre/` (project IAM, SA inventory, project number/compute SA, `run-jobs.json`, 31 job describes) then refused on the first declared-but-absent describe; `sha256s.txt` sidecar computed over the captured files |
| every `--apply` mutation | **not run** — identities/bindings/jobs/invokers/editor all stayed in plan form |

## The contradiction routed to the operator — `D-P34.42b-2` (OPEN)

The declaration's `expected_job_count = 100` bakes in the ordering
"P35.1a's `--paused` retry creates the twelve post-queue jobs before this
leg's re-count"; the operator's recorded order is the inverse (P34.42b
first, then `P35.1a-live-2 --paused`). Note the two-way dependency the
stop exposes: the P35.1a retry deploys jobs onto this leg's class SAs
(`sig-probe-rt`, `sig-ingest-rt`), which likewise do not exist until this
leg creates them — `--paused` changes only trigger state, not the job
deploys. Only the operator can pick the reconciliation: (a) a scoped
create of the twelve declared jobs PAUSED ahead of this leg (a mutation
not on the authorised list); (b) a declaration amendment making the jobs
leg's map/count follow the live fleet it is authorised to move; (c) a
different split/ordering the operator names. The leg stays queued in
RETURN PASS — **not consumed** (no mutation ran; the contract result is
the apply + verify together).

## Files

- `pre/` — the truncated AR-2-style capture (34 JSON + `sha256s.txt` +
  `capture-stamp.txt`): `project-iam.json`, `service-accounts.json`,
  `project-number.txt`, `compute-sa.txt`, `run-jobs.json` (88), 31
  `job-*.json` describes (the describe loop reached the first absent
  declared job alphabetically). Operator e-mail redacted to
  `<redacted-operator-account>` in every committed byte; no secret value
  read or persisted.
- `logs/check-all.out` — the full `--check all` plan.
- `logs/iam-plan-jobs.json` — the declaration's leg-scoped render.
- `logs/live-job-names.txt` — the independent 88-name live re-count.
- `logs/prestate.out` — the `--apply prestate` transcript ending at the
  refusal.
- `logs/absent-declared-jobs.txt` — the declared-vs-live diff.
