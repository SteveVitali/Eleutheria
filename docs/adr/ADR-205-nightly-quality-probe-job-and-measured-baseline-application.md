# ADR-205 — The nightly quality-probe job and measured-baseline application (P34.44b)

- Date: 2026-10-09
- Status: accepted
- Ticket: P34.44b (Round 11 / P34, row 256 — ADR-154 decision 3's "the suite
  measures production": the read-only L2 baseline run through `sig_audit`
  and the permanent `sig-quality-probe` nightly job; SIG-CONF-006/007/009,
  ADR-204's `unbaselined`→baselined transition)
- Base: `r11/P34.44a-quality-check-registry-and-ratchet-engine`
- Related: ADR-154 (the suite decision — this row lands its "runs where the
  data lives" half), ADR-204 (the registry + diff this row's measured
  baselines write through), ADR-202 (the exec-host pattern the baseline leg
  reuses and the `sig_audit` login both runs connect under), ADR-201 (the
  conditioned `ops/probes/` `objectCreator` scope the records land inside),
  ADR-077 (the recorded-alert ledger a failed run fires through),
  SIG-OPS-006 (the alert channel), OM-19/AR-3 (the window contract the
  schedule and the in-container guard both enforce)

## Context

ADR-204 engineered the registry, the outcome vocabulary and the executable
ratchet diff — the suite as a *ruleset*. P34.44b turns it into a measured
production signal, and four decisions needed pinning:

1. **How a baseline gets set from measurement.** ADR-204's `baseline =
   "pending"` placeholder and the `unbaselined` outcome exist for exactly
   this run. The transition needs a writer that can never loosen: a
   hand-edited baseline or a regression-written-as-baseline would silently
   defeat the ratchet.
2. **Where the nightly probe lives.** The M (spine probe) checks must run
   against the hosted spine off-peak, every night, without an operator in
   the loop — a permanent scheduled job, not the P34.43 one-off pattern
   (whose identity it shares but whose shape it does not: the trigger must
   exist at rest).
3. **How the window contract is enforced.** The contract forbids fires
   inside 03:00–06:30Z and the monthly batch window (day 6 00:00Z → day 13
   12:00Z). A cron expression can encode both statically — but a manually
   invoked or drifted trigger must still be caught at run time.
4. **What "a run" leaves behind.** A probe that runs silently — no record,
   or a record only on success — makes "the job didn't fire" and "the job
   passed" indistinguishable. The contract requires a `sig.probe-run/1`
   per run including suppressed and failed ones.

## Decision

- **Measured baselines are written only by `apply_baselines`**
  (`exports.quality`). The baseline leg emits a `sig.quality-baseline/1`
  record — every check with its L2 reference value, today's measured value,
  outcome, and the per-ratchet-check proposal (`baselined` for a resolved
  pending, `tightened` for a move toward the threshold, `regression_kept`
  for a recorded regression whose baseline stands, `not_measured` for a
  check the run could not evaluate). `sig-exports quality apply-baselines`
  recomputes the proposal from the record's embedded reports and rewrites
  the registry TOML in place per check, then re-validates and re-diffs the
  result through `diff_registry` — a loosening raises `RegistryError` and
  is never written, even from a hand-crafted record.
- **`baseline_run` / `baseline_at` are the provenance pair** — an additive,
  optional extension to `sig.quality-checks/1` (the schema stays `/1`; the
  fields are validated as landing together, `baseline_at` as a `date -u`
  `YYYY-MM-DD`, and only beside a numeric baseline). A ratchet check's
  measured baseline cites the run id and day that measured it; the pair is
  written only by `apply_baselines`, never by hand.
- **`sig.quality-probe/1` is the committed job declaration**
  (`ops/quality_probe.toml`, rendered by `sig-ops quality job`,
  `ops/gcp/quality-probe.sh` owns the mutations): the permanent
  `sig-quality-probe` Cloud Run job — pinned image digest (ADR-111),
  `sig-quality-probe-rt` (the same runtime identity the P34.43 exec host
  binds; the reserved-identity rule stands), one task, zero retries (a
  failed run is recorded and alerted; a retry inside a suppression window
  is worse than a missed night), a bounded 1800 s task timeout, the Cloud
  SQL connector, the two declared secret env bindings
  (`SIG_AUDIT_PASSWORD` ← `sig-audit-password`, `SIG_ALERT_WEBHOOK_TOKEN`
  ← `sig-alert-webhook-token`) and an explicit plain-env allow-list.
- **The schedule encodes the window statically; the job enforces it
  again at run time.** `sig-sched-quality-probe` fires
  `0 1 1-5,14-31 * *` in `Etc/UTC` — 01:00Z on days 1–5 and 14–31: the
  dom field structurally excludes days 6–13 (the batch window can never
  be scheduled into), and 01:00Z is outside 03:00–06:30Z;
  `load_declaration` proves both by enumerating a year of fires
  (`validate_schedule`) and refuses any drifted schedule. In-container,
  `sig-ops quality nightly` re-checks the same two predicates
  (`suppression_reason` — one implementation shared with the declaration
  and the leg script) before opening any connection, and records a
  `suppressed` `sig.probe-run/1` instead of running. Defence in depth:
  the static proof guards the declared schedule; the run-time guard
  catches a manually invoked or drifted trigger.
- **Every run writes its record.** A completed run writes
  `sig.quality-report/1` + `sig.probe-run/1` as new timestamped objects
  under `ops/probes/quality/` (inside the conditioned `objectCreator`
  scope; a versioned bucket — never an overwrite). A suppressed run
  writes the suppressed probe-run; a failed run (a refused connection, a
  fetch failure) writes an error probe-run so a missing record is never
  mistaken for a pass — then fires a recorded alert through ADR-077's
  ledger + the `sig-alerts` channel (`quality-probe` kind), and a clean
  run with a breached alert band records an `alarm`-severity alert.
- **The L2 baseline run rides the P34.43 exec host** — a one-off
  `sig-exec-quality-baseline-<stamp>` job whose container runs
  `sig-ops quality baseline`: every M check over the hosted spine through
  `sig_audit` (read-only session, 60 s statement timeout) plus every R
  check over the current public release files fetched read-only and
  bounded (`fetch_release`, caps declared). The leg is windowed like every
  other mutation leg (`SIG_QUALITY_EARLIEST`, never the quiet band, never
  the batch window — exit 42 queued with the re-run prompt), and the IAM
  declaration carries the job's two alert-path grants
  (`sig-quality-probe-rt` on `sig-alerts`' jobs invoker rule and the
  `sig-alert-webhook-token` consumer list).
- **GQ-20 stays `enforce`; GQ-24/GQ-27 stay `enforce` until P34.45** —
  the baseline record reports them as they stand; the flips are their
  fixing row's, not this run's.

## Consequences

- The registry's ratchet baselines become *measured* values with a cited
  run and date — `unbaselined`/`pending` resolves on first apply, and the
  ratchet thereafter compares against a real floor. A regression can no
  longer hide in an unset baseline.
- A nightly run that can't connect or can't evaluate records `partial`/
  `fail` and (on fail) alerts — SIG-ENG-042's no-vacuous-pass rule
  extends to the scheduled surface.
- The probe costs ≈ one Cloud Run job execution a night (declared
  `tasks=1`); P34.5's spend ledger measures the real line after the first
  week — nothing is claimed here.
- `sig-ops quality job render|verify-describe|verify-trigger|window` are
  pure/offline — the leg's `--check` mode prints the whole mutation set
  with no ADC and no network.
- P34.45's GQ-24 check and P34.47's probe-run consumer land on a job that
  already exists; their legs add checks/consumers, never a second job.

## Alternatives considered

- **One-off exec-host runs on a schedule** (no permanent job) — rejected:
  the trigger would have to create an ephemeral job per fire, doubling the
  mutation surface per night and losing the stable name a verify-diff and
  rollback can name-check; the permanent job is the cheaper honest shape.
- **Suppression by scheduler pause/resume alone** — rejected: a manual
  `gcloud run jobs execute` bypasses the scheduler entirely; the
  in-container guard is the only check that sees every fire.
- **Baselines applied by hand-editing the registry** — rejected: the
  diff rules only bind what is diffed; a dedicated writer that recomputes
  the proposal and re-diffs makes the toward-threshold rule
  unconditional, not review-dependent.
- **Retries on failure** — rejected: a failed nightly run is recorded and
  alerted; a retry could land inside the quiet band or the batch window,
  and the next scheduled fire already provides the retry.
- **`baseline_run`/`baseline_at` as a schema `/2`** — rejected: the pair
  is additive and optional; `/1` readers ignore them (back-compat).

## Revisit trigger

- The job needs a second workload (a second probe class, an on-demand
  variant) — the declaration is `sig.quality-probe/1` and scoped to the
  one nightly M run; widening is a new ADR or a `/2` declaration.
- The suppression windows change (a new quiet band, a different batch
  cadence) — the constants are in one place (`quality_job.py`), but the
  contract is OM-19's; a window change is an operating-mode decision,
  not a code edit.
- `sig_audit` needs to *write* probe results into the spine (instead of
  the bucket record) — ADR-202's SELECT-only posture forbids it; that
  ADR's trigger governs.
- A probe run needs longer than the declared 1800 s task timeout (a
  growing spine outpaces the 60 s statement timeout × checks) — the
  timeout is declared data; re-judge the bound rather than removing it.

### Trigger evaluation

- P34.44b (row 256, 2026-10-09): the ADR authored its own trigger; quiet
  at authoring — one workload, the OM-19 windows as contracted, the
  bucket record posture as ADR-202 set it, the declared timeout
  deliberately generous against a 60 s statement budget.
