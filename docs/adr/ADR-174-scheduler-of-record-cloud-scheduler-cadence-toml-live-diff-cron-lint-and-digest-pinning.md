# ADR-174 — Scheduler of record: Cloud Scheduler + `ops/cadence.toml`, daily live-diff, cron lint, digest pinning

- **Status:** Accepted
- **Phase / ticket:** Phase 35 / P35.1a (`docs/tickets/264_P35.1a__scheduler-of-record-live-diff-cron-lint.md`) — Round 11 fleet-ops row.
- **Qualifies:** ADR-016 (the scheduler-of-record clause) and ADR-076 (the scheduling path); both revisit triggers fired at Round-11 T1's SEED-11 evaluation; the qualifier wording is in their appended `## Status updates`.
- **Date:** 2026-10-10
- **Related:** SIG-OPS-005 (live-configuration reconciliation: daily read-only repo-vs-live diff; one scheduler of record; the dom⊕dow cron lint; configuration that must not require an image roll), SIG-SEC-008 (digest pinning, extending ADR-111 to services and the whole job fleet), ADR-076 (the cadence-vs-etiquette design — the etiquette half stands; only the *GitHub Actions scheduler* is qualified away), ADR-016 (Dagster kept reversible — the orchestration seam stands; only the implied scheduler-of-record reading is qualified away), ADR-111 (pinned job images), ADR-077 (the recorded-alert seam the drift check fires through), ADR-175 (the monthly logical export — its trigger is declared and held paused). Deferral **D-P34.6-2**; fleet-hygiene successor **P35.1b** (`docs/tickets/291_P35.1b__fleet-hygiene.md`).

## Context

- **Three schedulers existed on paper.** ADR-016 reserved Dagster (never deployed); ADR-076 put the daily
  reingest cadence on a free GitHub Actions cron (disabled by P34.4 after it failed 6 of 6 runs — the
  workflow cannot reach Cloud SQL and must never get a DSN, which would move source egress to GitHub IPs and
  duplicate ingestion); the de-facto scheduler is Cloud Scheduler with 79 triggers generated from
  `ops/cadence.toml` by `ops/gcp/scheduled-ops.sh`. SIG-OPS-005 requires *one* scheduler of record.
- **The declared and live sides could drift silently.** `sig-ops cadence --check` compared the cadence file
  only against `live_targets.toml` — nothing compared it against GCP. Nine live Cloud Run jobs carried no
  cadence row, four egress-probe jobs ran `:tag` images (not digest pins), one source row
  (`sam_gov`) had live-vs-repo cron drift, and three rows (`eyes_on_flock`, `openstates`, `congress_gov`)
  carry cron expressions that restrict *both* day-of-month and day-of-week — which cron **OR**-fires, so
  "monthly on day 3" silently runs every Tuesday too.
- **"Pinned" had no declared exceptions.** Digest pinning (ADR-111) covered the jobs the P31.7 roll touched,
  but a job legitimately held off the fleet digest (the D-P31.4-1 observation window) had nowhere to be
  *declared* — an undetectable shape that looks identical to drift.

## Decision

1. **One scheduler of record: Cloud Scheduler, declared by `ops/cadence.toml`.** Every recurring trigger —
   the probe sweep, per-source and per-batch reingestion, maintenance rows, and the drift check itself — is a
   row in that file; `ops/gcp/scheduled-ops.sh` reconciles live state to it (create/update; it reports, never
   deletes, undeclared live triggers — deletion is the P35.1b leg's call). The GitHub Actions `reingest.yml`
   carries **no `schedule:` block** (removed under P34.4; the manual `workflow_dispatch` remains inert — it
   has no Cloud SQL path and gets no DSN). ADR-076's cadence-vs-etiquette design stands: `due`/`record` stays
   the cadence engine; only the *carrier* moved.
2. **A daily read-only reconciler: `sig-ops live-diff`.** It diffs the declared side (cadence triggers and
   jobs, `[[manual_jobs]]`, `[[pins]]`, `[fleet]` roll record, `[[buckets]]` posture) against live Cloud
   Scheduler jobs, Cloud Run jobs and services, service-account bindings, secret bindings, image digests, and
   bucket IAM/UBLA/versioning/lifecycle. It runs inside the existing `sig-probe` job via a scheduler trigger
   whose POST body overrides the container args (`["-c","exec sig-ops live-diff --live --alert"]`) — no new
   job, no new identity; probe-runtime reads are least-privilege viewer roles (`roles/run.viewer`,
   `roles/cloudscheduler.viewer`, per-bucket `roles/storage.legacyBucketReader` for `buckets.get`/`getIamPolicy`/`objects.list`). Findings emit in named classes (`schedule`, `job_config`, `image`, `service_account`, `secrets`, `public_posture`, `ubla`, `versioning`, `lifecycle`), deterministic order, appended as a WORM run row under `ops/runs/_live-diff/`; drift fires the recorded-alert seam (ADR-077). Exit codes: `0` clean, `1` drift, `2` error — an unreadable side fails closed.
3. **Cron lint, with owned exceptions.** `sig-ops cadence --check` and the live-diff lint both reject a
   five-field spec restricting both day-of-month and day-of-week unless the row sets
   `cron_or_semantics_ok = true` *and* its note names the owner of the recorded exception. The three current
   offenders are annotated as recorded exceptions queued for the P35.1b correction sweep — the lint makes the
   drift visible, the fleet-hygiene row owns the fix.
4. **Digest pinning with declared, expiring holds (`[[pins]]`).** Every job and service is expected to run
   the digest its class position implies: a `[[pins]]` row wins, else the newest committed `roll-jobs`
   record's per-job `after_digest`, else the record's fleet `image_digest`. A `[[pins]]` row MUST carry a
   `reason` and an `expiry` (YYYY-MM-DD); an expired pin is reported drift until re-declared or swept. A
   `:tag` reference (or a tag+digest ref whose tag is doing the resolving) on any workload is reported drift.
5. **`[[manual_jobs]]` is the only way to be legitimately untriggered.** `sig-export`, `sig-materialize`,
   `sig-replay-ingest` are declared there (operator-run by design); any other live job that is neither
   cadence-owned nor manual is reported as unlisted drift — the cruft jobs P35.1b deletes flag exactly there.
6. **Configuration does not require an image roll.** `scheduled-ops.sh --apply` publishes a declaration
   bundle (`ops/declared/live-diff.json` on the restricted bucket: cadence text + resolved fleet images +
   cadence sha256); the in-image diff reads it through `SIG_OPS_DECLARED_GCS`. A cadence edit takes effect at
   the next reconcile; the baked `/app/ops/cadence.toml` remains the operator-host fallback. Every job also
   carries `SIG_OPS_CADENCE_SHA256` so a run row records which declaration the fleet was deployed against.
7. **Maintenance triggers are deployed inert.** The monthly logical-export trigger (`sig-sched-pg-logical-export`) is created and held **paused**; the reconcile re-pauses it and never enables it — D-P34.6-2's verbatim in-ticket go (which builds the target job) owns enablement. A live `ENABLED` maintenance trigger is drift.

## Consequences

- One file explains every trigger; `sig-ops live-diff --from-state <fixture>` diffs deterministically offline.
- Drift (the `sam_gov` cron, the nine unlisted jobs, tag images, the un-flipped bucket postures) becomes a
  named, daily-recorded signal instead of folklore — including drift whose fix is queued on P35.1b, which the
  report names but never hides.
- The daily check's early runs will record honest failures until a fleet roll carries the `live-diff` verb
  onto `sig-probe`; that failure is the honest record, never masked.
- `[[manual_jobs]]`/`[[pins]]` make "intentional" auditable: an exception without a declared owner is drift.

## Alternatives considered

- **A separate `sig-live-diff` job/identity** — rejected: a new job, SA, secret set and invoker binding for a
  read-only check doubles the surface; the args-override on `sig-probe` reuses identity, alerts, and the WORM
  run-row path (the trigger is the deploy-time wiring, the verb is the image).
- **A custom IAM role over `legacyBucketReader`** — rejected: the same three read permissions through heavier
  machinery; the managed role per declared bucket is the least-privilege fit without a new role resource.
- **Deleting undeclared triggers in the reconcile** — rejected for this row: deletion is a P35.1b decision
  (some unlisted jobs are declared-manual; the rest are the cruft that leg disposes). The reconcile reports,
  the daily diff flags, the hygiene leg decides.
- **Keeping `reingest.yml` runnable with a DSN secret** — rejected outright (per contract): it would move
  source egress to GitHub IP space and duplicate the scheduled ingestion path.

## Revisit trigger

Revisit when any of: the live-diff leg needs writes (a reconciler that *repairs* instead of reporting is a
different posture, needing a new decision); the args-override trick proves fragile (e.g. Cloud Scheduler body
limits or a second scheduled verb) — promote the check to a dedicated job; the manual-job or pin lists grow
past a handful (then the declaration wants a registry, not an allow-list); or a different scheduler (the
reserved Dagster seam, ADR-016) becomes the real carrier — in which case this ADR's *mechanism* moves but its
declaration-vs-live contract stands.
