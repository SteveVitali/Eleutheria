<!--
  docs/ops/RUNBOOK.md — the ops runbook for the hosted posture (never
  executed by the writing row — P35.4 / R11-OPS-05, SIG-OPS-010; the §6
  register is SIG-SEC-009). Agent-drafted operator documentation (harness
  devin-desktop/swe-2-high/subagent, contract
  docs/tickets/293_P35.4__ops-runbook.md): every command and repo path named
  below is verified against this tree by
  `python3 docs/build/tools/check_runbook.py` (wired into `make docs-check`),
  and prose that could assert production state is judged by the corpus lint
  (docs/build/tools/check_live_claims.py — docs/ops/** is corpus). Nothing
  here was executed by the authoring row — no hosted leg is ever a
  writing-row action (always an operator procedure), and this row never held
  credentials that could run one.
-->
# docs/ops/RUNBOOK.md — the hosted-operations runbook (never executed by the writing row)

The nine operator procedures a hosted deployment may need on call (G1
§3.10's list, `docs/build/planning/2026-09-30-next-phase/research/G1-ops.md`;
SIG-OPS-010). Each section names the repository-verified commands; each leg
that could touch the hosted project carries its environment label —
`engineered/local` (runs on a workstation or fixture), `fixture` (the
`--from-state` legs that read a captured fixture), `staging` (a composed or
rehearsal environment — `exports.release.rollback` is staging-only today),
`live` (reads or mutates the hosted project — operator ADC only, never run by
a writing row), `public` (touches the public surface), or
`human/operator-only` (a decision a tool never makes for you).

**How to use this runbook.** Rules that hold in every section:

- **Operator ADC only.** No hosted leg in this runbook runs without the
  operator's Application Default Credentials — `gcloud`/`sig-ops … --live`
  forms assume `gcloud auth application-default login` once per host, then
  `export SIG_GCP_PROJECT=<project>` (an env var — never a committed literal).
  A writing/agent row never holds production ADC.
- **Dry-run or `--check` first, `--apply` last.** Every mutating script and
  verb below has a read-only first leg (a `--check`/`--dry-run`/plan mode);
  run it, read the plan, then decide. The `--apply` leg is the only leg that
  mutates.
- **Windows are enforced, not advisory.** Mutating legs refuse outside their
  window (exit 42 where scripted — see each script's header): never inside the
  monthly batch window and never inside the nightly quiet hours the script
  declares. If a script refuses, wait for the window; do not patch the guard.
- **Name-checked deletes only.** Deletion targets are spelled by name
  (`[[retired_jobs]]`, `[[retire_triggers]]`, the drill-instance stamp) —
  never a glob, never `sig-pg` itself.
- **Everything leaves a record.** When a hosted leg runs, it appends to the
  restricted bucket's `gs://<p>-sig-restricted/ops/runs/` and
  `…/ops/probes/` prefixes and to `docs/build/reports/probes/`
  (`sig.probe-run/1` records) where a probe
  fires. If an action left no record, it did not happen — write the row by
  hand if the tool did not.
- **`date -u` for every stamp** you write into a record.
- **Never a secret value in a file** (HG-09): values move through stdin
  (`--data-file=-`) and env vars, never arguments, logs, or this file.

## The hosted shape as recorded (never re-verified by this row)

The executed deployment record is `docs/build/reports/GCP_DEPLOYMENT.md`
(executed 2026-09-15 under ADR-081 — Cloud SQL `sig-pg` + Cloud Run
jobs/services + Secret Manager + the two buckets); this runbook never
re-verifies it. The posture it records, in one line each:

- **Store** — Cloud SQL Postgres spine (sqitch-managed, per the deployment
  record) in a private instance; the operator reaches it through
  `cloud-sql-proxy`.
- **Compute** — Cloud Run **jobs** for ingest/export/materialize/probe
  classes, Cloud Run **services** for `sig-api` and `sig-web`.
- **Scheduling** — Cloud Scheduler triggers drive the jobs from
  `ops/cadence.toml` (`uv run sig-ops cadence --check` fails when the file and
  the declared triggers drift). The `.github/workflows/reingest.yml` workflow
  is the stale predecessor, never the scheduler of record; `orchestration/`
  Dagster is unused glue — never the scheduler of record either.
- **Monitoring** — committed alert definitions under `ops/monitoring/`,
  verified against the project only when the operator runs
  `uv run sig-ops monitoring-defs verify --live` (see §1);
  probe/sentinel declarations sit in `ops/sentinels.toml` and the scan leg
  is `uv run sig-ops sentinel-scan`.
- **Records** — append-only by convention (versioning + noncurrent-object
  lifecycle, scripted by P34.3 — the buckets are **not** WORM; that posture
  claim needs SIG-STORE-048's control, queued). `uv run sig-ops live-diff`
  is the read-only declared-vs-remote reconciliation — it exits clean, lists
  drift, or fails loudly; treat any drift it reports as a record to explain,
  never something to hand-patch.

## 1. Alert received

*Labels: triage is `live` read-only; any remediation leg is
`human/operator-only`.*

Committed alert definitions (`ops/monitoring/` — uptime checks on the public
origin and `sig-api` `/health`, TLS-expiry at 21 days, the `SIG-ALERT`
log-match policy, the Cloud Run job-failed policy; the notification channel
is the operator channel with the address committed as a redacted literal per
the monitoring README's convention):

```bash
# verify committed definitions against the running surface (read-only; operator ADC)
uv run sig-ops monitoring-defs verify --live --project "$SIG_GCP_PROJECT"  # operator leg, not exercised by checks
# the fixture leg (engineered/local — no project needed)
uv run sig-ops monitoring-defs verify --from-state <fixture-dir> --project "$SIG_GCP_PROJECT"
# list what actually fired
gcloud monitoring policies list --project "$SIG_GCP_PROJECT"
```

Triage by probe target:

```bash
# probe/sweep history the alert references (read-only; SIG_OPS_GCS_BUCKET
# selects the restricted records bucket)
SIG_OPS_GCS_BUCKET="gs://<p>-sig-restricted" uv run sig-ops probe-history
# the failed-execution policy → which job/execution went red
gcloud run jobs executions list --job <job> --project "$SIG_GCP_PROJECT" --region us-central1
gcloud logging read 'resource.type="cloud_run_job" AND severity>=ERROR' \
    --freshness=6h --project "$SIG_GCP_PROJECT"
```

- **Public origin or `/health` down** → treat as a publication posture
  problem: check `docs/build/reports/probes/` for the newest committed
  `sig.probe-run/1` record, then §3 (republish) or the web-roll lane of §7.
- **A scheduled job failed** → §5.
- **TLS-expiry warning** → the managed-certificate lane of the deployment
  record; not a P35.4 procedure.
- **`live-diff` drift reported by a probe** → read the diff output; the fix
  is a declared change (cadence row, trigger row) or a §9 decommission,
  never a hand-edit to live.

Who is told: the committed notification channel is the operator e-mail
channel (address kept out of the repo); the alert-defs re-notify daily while
red beyond 24h (SIG-OPS-006). Record the alert and its disposition in the
run record — an alert acknowledged nowhere did not happen.

## 2. Restore

*Labels: plan legs `engineered/local` or `live` read-only; the restore legs
are `live` mutating and `human/operator-only`; a production restore is never
executed by a writing row.*

Two variants (G1 §3.1): **PITR** — point-in-time clone into a new instance,
anytime; **full backup** — restore a committed backup into a pre-created
empty instance, drilled quarterly.

```bash
# plan the quarterly drill (read-only)
bash ops/gcp/restore-drill.sh --check
# the drill legs, under operator ADC, inside the declared window
# (legs: prestate · clone · counts · smoke · rehearse · deleteclone ·
#  fullrestore · all — names from the script's own case):
bash ops/gcp/restore-drill.sh --apply all
# an on-demand restore point BEFORE any mutating op (AR-2):
bash ops/gcp/restore-point.sh --check
bash ops/gcp/restore-point.sh --apply sqlpoint
# the monthly logical export:
bash ops/gcp/logical-export.sh --check
```

The scripted legs wrap the raw operations below — the script is the
procedure; these are what it runs, shown so the operator can read the plan:

```bash
# PITR clone into a fresh drill instance (name-checked stamp, never sig-pg)
gcloud sql instances clone sig-pg "sig-pg-drill-$(date -u +%Y%m%dT%H%M%SZ)" \
    --point-in-time "$T" --project "$SIG_GCP_PROJECT"
# full-backup variant: make a backup, list it, restore into an empty instance
gcloud sql backups create --instance sig-pg --project "$SIG_GCP_PROJECT"
gcloud sql backups list --instance sig-pg --project "$SIG_GCP_PROJECT"
gcloud sql backups restore <backup-id> --backup-instance=sig-pg \
    --restore-instance="sig-pg-drill-<stamp>" --project "$SIG_GCP_PROJECT"
# export/import the logical copy
gcloud sql export sql sig-pg "gs://<bucket>/exports/sig-pg-$(date -u +%Y%m%d).sql" \
    --database=<db> --project "$SIG_GCP_PROJECT"
# watch a long-running sql operation
gcloud sql operations describe <op-id> --project "$SIG_GCP_PROJECT"
# teardown: name-checked delete of the DRILL instance only
gcloud sql instances delete "sig-pg-drill-<stamp>" --project "$SIG_GCP_PROJECT"
```

**Drill record** (append a row each drill — the template G1 §3.1 prescribes):
stamp, instance name, `T` chosen, wall-clock RTO, RPO (age of `T` vs drill
time), parity counts vs the source spine, deletion record. A drill with no
recorded RTO/RPO does not count (SIG-OPS-001).

Note the boundary the report already draws: `docs/build/reports/GCP_DEPLOYMENT.md`'s
2026-09-15 same-instance five-claim drill was a pipeline smoke of the
export/import path, not a production-scale SIG-OPS-001 drill —
`ops/gcp/restore-drill.sh` is the drill of record.

## 3. Republish

*Labels: build/export legs `live` (operator); `publish-web` is `public` —
dry-run by default, `--apply` is `human/operator-only` and is the sole
allowed publish path (SIG-OPS-008: no hand-typed bucket syncs, ever).*

```bash
# materialize + export (the recorded republish pipeline's legs; --check
# plans every action — export's legs are image|job|run|fetch|all)
bash ops/gcp/materialize.sh --check
bash ops/gcp/export.sh --check run
# publish: DRY-RUN first — prints the sync plan and the denied-route probes
uv run sig-ops publish-web --export-dir <export-dir>
# apply, only after the plan is read — writes .sig-release.json, runs the
# denied-route probes, never deletes a release namespace
uv run sig-ops publish-web --export-dir <export-dir> --apply
```

The executed precedent is `docs/build/reports/REPUBLISH_LIVE_2026-09-27.md`.
Rollback of a *published byte set*: the publish path never deletes a release
namespace, so the recorded fallback is republish of the prior export;
`exports.release.rollback` is the rehearsed staging-side mechanism (P32.25,
fixture only), and the production promotion/rollback tool lands under
P35.5x — until it does, SIG-REL-013's append-only rule means the runbook
publishes forward, never rewinds.

**Release checklist rows** — cite these in the run ledger for any publish,
with the trigger class marked:

| trigger class | required evidence |
|---|---|
| in-ticket republish | the owning ticket's AC row + `publish-web` dry-run plan + probes green |
| incident republish | the incident/alert record (§1) + the fix record + probes green |
| distinct artifact (new release) | a clean pushed commit (SIG-REL-002), `uv run sig-ops sentinel-scan` green against `ops/sentinels.toml` — the placeholder-sentinel rule (the contract's `PROBE_PLACEHOLDER` name maps to this committed mechanism), measured-baseline posture per ADR-205 (pending rows are applied only by `sig-exports quality apply-baselines`, never hand-set), and the tail-probe-sweep contract of ADR-199 (`docs/build/tools/record_policy/tail_probe_sweep.toml`) |

## 4. Scheduled-window watch

*Labels: all legs read-only (`live` reads under operator ADC; the fixture
legs `engineered/local`).*

The scheduler of record is Cloud Scheduler + Cloud Run jobs declared by
`ops/cadence.toml`, consolidated on the `sig-sched-due` dispatcher (hourly
at :13 UTC) with per-source triggers retired per the name-checked list —
the `uv run sig-ops dispatch-due` verb evaluates the due set and appends a
`sig.dispatch-due/1` run row under the restricted bucket's dispatcher
prefix; an empty evaluation is a defect, not a quiet day. (Its `--dry-run`
evaluates without executing but still appends the would-execute row — it is
a recording leg, not a silent read.) `reingest.yml` is the retired
predecessor — never watch it.

Generalized watch plan (the G1 §3.7 shape, parameterized — a first fire and
a batch window differ only in which cadence rows are due):

```bash
# 1. BEFORE the window — confirm what is due and the baseline state
uv run sig-ops cadence --check                       # file vs declared triggers
gcloud scheduler jobs list --project "$SIG_GCP_PROJECT" --location us-central1
SIG_OPS_GCS_BUCKET="gs://<p>-sig-restricted" uv run sig-ops probe-history
# read-back of the declared first-fire / batch windows (P34.39, read-only):
uv run sig-ops scheduled-firstfire --help
uv run sig-ops scheduled-readback --help
# dispatcher's own evaluation (read-only form):
uv run sig-ops dispatch-due --help

# 2. DURING — at +15m / +1h / +2h:
gcloud run jobs executions list --job <job> --project "$SIG_GCP_PROJECT" --region us-central1
gcloud logging read 'resource.type="cloud_run_job"' --freshness=3h --project "$SIG_GCP_PROJECT"
curl -fsS -o /dev/null -w '%{http_code}\n' "<base>/health"   # API liveness probe

# 3. AFTER — the run rows: read ops/runs/<source>/<date>/<ts>.json rows in
#    the restricted bucket and record the verdict in the owning record;
#    any row absent is a defect, any failed row goes to §5.
```

First-fire protocol: triggers are created **paused** (the R6 posture —
`gcloud scheduler jobs describe <name>` shows `state: PAUSED`) and only the
wave's verbatim `gcloud scheduler jobs resume <name>` step activates them;
a resume line is an operator action, never scripted ahead of the go call.
Baseline before the window so the after-state has something to be compared
against (prior failure rows, per-source counts, disk).

## 5. Job failed

*Labels: diagnosis `live` read-only; re-execution/cancellation
`live` mutating, `human/operator-only`.*

```bash
# what ran, what it said
gcloud run jobs executions list --job <job> --project "$SIG_GCP_PROJECT" --region us-central1
gcloud logging read 'resource.type="cloud_run_job" AND severity>=ERROR' \
    --freshness=24h --project "$SIG_GCP_PROJECT"
# the run row the job appended (restricted bucket):
gcloud storage ls "gs://<p>-sig-restricted/ops/runs/<source>/**"
```

**Re-execute** — a fresh execution, never an in-place retry of the old one:

```bash
gcloud run jobs execute <job> --project "$SIG_GCP_PROJECT" --region us-central1
```

Resume semantics: ingest flushes per capture (ADR-111), so a re-run resumes
with `resumed` rows and `+0` idempotent replays — duplicates are impossible
by construction. `uv run sig-ops replay-ingest --source <id>` replays
**persisted** captures only (never refetches); `backfill-run-completions`
repairs missing completion rows. See `uv run sig-ops replay-ingest --help`
for the recorded form.

Cancellation: only when a run threatens the rest of the posture (e.g. the
`/health` probe red beyond 15 minutes). Cancelling a Cloud Run execution is
safe — the spine is append-only and resumable; the next run picks up. What
you may never do: `UPDATE`/`DELETE` a spine row to "fix" an ingest.

**Anomaly stop-and-preserve** — if the failed run's row shows counts wildly
off expectation (claims ≫ the source's norm, unexpected `n_tup_upd`/`n_tup_del`
motion): clone the instance at `T` for comparison (§2 PITR leg), preserve
the run row and logs as evidence, and escalate to the operator before any
re-run.

On rollback vocabulary — recorded, not smoothed over: there is no
`rollback.sh`/`ops_rollback.sh` in this tree and no
`ingest_run.status='rolled_back'` state (`ingest_run_completion.status` is
constrained to `ok`/`partial`/`quota_reached`/`failed`,
`db/deploy/ingest_run_completion.sql`). A bad ingest is never undone by
deleting rows: a corrected re-run supersedes (the spine is append-only), a
claim-level wrong takes the reviewed-correction path (`uv run sig-ops
disposition` for publication-level deny; `uv run sig-ops recovery-plan` /
`recovery-apply` for the bounded-recovery machinery, Round-10), and a byte-level
public wrong takes §3's republish-forward. The P35.4 contract's
rollback-script reference is drift in the contract, recorded in the run
ledger — the mechanisms above are what actually exist.

## 6. Secret rotation (SIG-SEC-009)

*Labels: the whole section is `human/operator-only` — a writing row never
rotates, reads, or lists a secret value.*

Rules:

- New versions arrive **only** via stdin — `gcloud secrets versions add
  <name> --data-file=-` — so the value never lands in argv, a file, or the
  transcript. Reads are env-only: `gcloud secrets versions access latest
  --secret=<name>` piped into an env var, never echoed.
- Consumer restart after a rotation: Cloud Run **jobs** pick up `:latest` on
  the next execution — nothing to restart; Cloud Run **services** need a new
  revision — roll by digest (§7), never a label-only `update` that
  re-resolves `:latest` in place.
- Accessor bindings are the declared matrix (`ops/iam_identities.toml` —
  `jobs_revoke` rows are in-flight removals, applied by the iam scripts
  under operator review); the operator checks the accessor bindings on the
  project with `gcloud secrets get-iam-policy <name>` before and after.
- **Exposed secret rule** (G1-12): a secret whose value has ever appeared in
  a transcript, log, or diff is rotated **before first production use** and
  the register row is updated to `rotated: yes` + date at the same time —
  never "we'll rotate when we use it".
- The register carries metadata only: name, owner, consumer, last-rotation
  — values never.

### The register

One row per `[[secret]]` in `ops/iam_identities.toml` (mechanically checked
by `check_runbook.py` — adding a secret to the TOML without a register row
fails `make docs-check`). `last_rotation: unknown` means no rotation
evidence is committed — the sole recorded `versions add` for most of these
is their creation, which is not a rotation; `unknown` is the honest cell.

| name | owner | consumer | last_rotation | procedure |
|---|---|---|---|---|
| `sig-pg-password` | operator | `sig-api-rt` `sig-ingest-rt` `sig-probe-rt` `sig-export-rt` `sig-materialize-rt` `default-compute` | `unknown` | stdin version-add, then roll every DB-consuming job/service revision by digest (§7) — the `default-compute` accessor is the GCE host path |
| `sig-alert-webhook-token` | operator | `sig-alerts-rt` `sig-probe-rt` `sig-quality-probe-rt` | `unknown` | stdin version-add; next probe execution picks it up; `sig-alerts` mounts it as env `SIG_ALERT_WEBHOOK_TOKEN` — a new `sig-alerts` revision picks it up; `default-compute` revoke in-flight (`jobs_revoke`) |
| `sig-api-env` | operator | — | `unknown` | zero-version / dead secret (G1 §3.9): nothing consumes it, no version to rotate — do not delete it here; record, don't resurrect |
| `sig-data-gov-key` | operator | `sig-ingest-rt` | `unknown` | upstream reissue → stdin version-add → next ingest run; `default-compute` revoke in-flight |
| `sig-maproulette-api-key` | operator | — | `unknown` | **exposed in a session transcript (G1-12, accepted risk)**: no accessor binding today; it must be rotated before the MapRoulette contribution-back lane activates — the register cannot claim that rotation happened |
| `sig-muckrock-refresh` | operator | `sig-ingest-rt` | `unknown` | upstream refresh-token reissue → stdin version-add → next ingest run; `default-compute` revoke in-flight |
| `sig-openstates-key` | operator | `sig-ingest-rt` | `unknown` | upstream reissue → stdin version-add → next ingest run; `default-compute` revoke in-flight |
| `sig-sam-gov-key` | operator | `sig-ingest-rt` | `unknown` | upstream reissue → stdin version-add → next ingest run; `default-compute` revoke in-flight |
| `sig-zenodo-client-id` | operator | `operator` | `unknown` | operator-run deposit credentials — no runtime consumer; rotate at the Zenodo console, update via stdin, next deposit uses it |
| `sig-zenodo-client-secret` | operator | `operator` | `unknown` | as `sig-zenodo-client-id` |
| `sig-zenodo-sandbox-token` | operator | `operator` | `unknown` | as `sig-zenodo-client-id`; sandbox posture — rotate before any real deposit anyway |
| `sig-audit-password` | operator | `sig-quality-probe-rt` | `unknown` | P34.43 DB-login credential (HG-09/ADR-202): stdin version-add, next quality-probe execution |
| `sig-recovery-password` | operator | `sig-quality-probe-rt` | `unknown` | as `sig-audit-password` |
| `sig-er-rerun-password` | operator | `sig-quality-probe-rt` | `unknown` | the OM-20 write-capable credential — its use legs stay human-run by pre-authorization, rotate the same way |

Owners are `operator` throughout because every row's ultimate holder is the
operator (the upstream-issued keys sit on operator-held upstream accounts).
Where a rotation is later performed, the row's `last_rotation` is updated in
the same commit that records it — never retroactively.

## 7. Roll

*Labels: plan `engineered/local` or `live` read-only; `--apply` is `live`
mutating, `human/operator-only`.*

The digest rule (SIG-SEC-008): every roll pins `@sha256:` — `roll-jobs`
refuses a `:latest` ref by construction.

```bash
# build + SHA-tag the candidate image, then resolve its digest
bash ops/gcp/materialize.sh --check image
gcloud artifacts docker images describe <image>:<tag> --project "$SIG_GCP_PROJECT"
gcloud artifacts docker images list <repo-path> --project "$SIG_GCP_PROJECT"

# jobs: plan — prints the per-job update, mounts the capture store, refuses :latest
uv run sig-ops roll-jobs --image "<image>@sha256:<digest>"
# apply — updates each job preserving its config, verifies, records
uv run sig-ops roll-jobs --image "<image>@sha256:<digest>" --apply --record roll.json

# services: sig-web through its scripted roll; sig-api per the recorded
# candidate-traffic precedent (GCP_DEPLOYMENT §9 — candidate at 0% → tag
# smoke → promote; rollback = update back to the recorded prior digest)
bash ops/gcp/web-roll.sh --check
bash ops/gcp/web-roll.sh --apply all
gcloud run services describe sig-api --project "$SIG_GCP_PROJECT" --region us-central1
```

**Fleet convergence and deliberate pins**: `ops/cadence.toml`'s `[fleet]` /
`[[pins]]` rows declare which classes are intentionally held at a digest
(e.g. a batch row pinned for an in-flight evidence leg) — a pin is a
declaration, not drift. `uv run sig-ops live-diff` reports the digest spread
and any tag-ref stragglers; a roll converges the unpinned classes and leaves
the pinned ones named in the record. Rollback of a roll is the same verb
against the recorded before-digest — the roll record carries before/after
digests and the service-account posture for exactly that.

Artifact Registry hygiene rolls with this section: see §8's cleanup lanes —
the clean-registry workflow dry-runs first.

## 8. Cost review

*Labels: `live` reads under operator ADC; the ledger append is engineered.*

Monthly (G1 §3.8's review shape):

```bash
# the scripted cost posture (budget/billing-export legs — read the plan first)
bash ops/gcp/cost-guard.sh --check
# egress accounting the denial-of-wallet posture depends on
uv run sig-ops egress-report --help
# Artifact Registry storage trend + the cleanup plan (dry-run FIRST, always):
uv run sig-ops ar-cleanup merged-policy
uv run sig-ops ar-cleanup candidates
gcloud artifacts repositories set-cleanup-policies <repo> \
    --policy=<merged-policy-file> --dry-run --project "$SIG_GCP_PROJECT"
# the apply lane goes through the scripted fleet sweep, inside its window:
bash ops/gcp/fleet-sweep.sh --check
```

Record the month's measured numbers into the spend ledger under
`docs/build/reports/spend/` (SIG-OPS-009: measured figures only, labelled
where estimated). Baseline to compare against — G1 §3.8's ≈$90–100/mo
list-price estimate is an **inference**, not a measured bill; the measured
billing-export row supersedes it when the export lands.

Cost-anomaly response: a budget alert trip → check egress first
(`egress-report`, bucket access pattern — the public buckets are the
world-readable surface and the denial-of-wallet exposure) → consider the
rate-limit/degraded posture (SIG-GOV-021) before any public-surface change;
never pull a bucket private as a cost reflex without §3's posture review.

## 9. Decommission a job or source

*Labels: declaration edits `engineered/local`; the delete/pause legs are
`live` mutating, `human/operator-only`, name-checked.*

**A job**: declare it — add a `[[retired_jobs]]` row (name-checked) and its
trigger to `[[retire_triggers]]` in `ops/cadence.toml`; the scripted
delete leg (e.g. `ops/gcp/fleet-sweep.sh`'s delete lane) deletes by name
after a describe-first:

```bash
uv run sig-ops cadence --check
gcloud run jobs describe <job> --project "$SIG_GCP_PROJECT" --region us-central1
gcloud scheduler jobs pause <trigger> --project "$SIG_GCP_PROJECT" --location us-central1
gcloud scheduler jobs delete <trigger> --project "$SIG_GCP_PROJECT" --location us-central1
bash ops/gcp/fleet-sweep.sh --check    # its delete leg is name-checked, windowed
```

The job's `gs://<p>-sig-restricted/ops/runs/` history stays — retirement
never erases records.
Until the recorded delete lands, `uv run sig-ops live-diff` reports the
still-live trigger as declared-retired drift — expected, explained by the
cadence row.

**A source**: three distinct edits, in order —

1. The cadence row: remove (or `state = "paused"`, for a freeze) the
   source's `[[sources]]` entry in `ops/cadence.toml`; the dispatcher's
   due set drops it. A freeze (`paused`) keeps the row for resumption;
   a decommission removes it.
2. The trigger: its per-source scheduler trigger joins `[[retire_triggers]]`
   (or was already covered by the dispatcher consolidation) — pause/delete
   legs as above.
3. The gate: `ingestion_permitted` in `connectors/src/connectors/data/sources.toml`
   is a **human/rights decision (HG-03)** — an operator flips it; a writing
   row never does. Upstream contribution-back obligations (the source's
   compact) are closed by the source's own exit procedure, recorded before
   the row goes.

A retired source's upstream data stays in the spine — append-only means
decommissioning is a scheduling/ingestion decision, never a data deletion.

## 10. Republish a release

*Labels: every `release` verb is `engineered/local` on a fixture registry;
against `gs://…-sig-release` the `--apply` leg is `live` mutating,
`human/operator-only`. Dry-run is the default — it plans and reads only.*

The release-model republish is a NEW promotion, never an edit in place:
a fresh candidate rides the one pipeline (`P35.53`/`P35.54`) —

```bash
# plan the run first — every verb answers its plan without --apply
uv run sig-ops release status --registry "$SIG_RELEASE_REGISTRY"
uv run sig-ops release cut --registry "$SIG_RELEASE_REGISTRY"
# build the candidate tree from an export bundle, then stage + verify it
uv run sig-ops release build --registry "$SIG_RELEASE_REGISTRY" \
    --export-dir <export-dir> --work-dir <work-dir>
uv run sig-ops release stage --registry "$SIG_RELEASE_REGISTRY" --work-dir <work-dir>
uv run sig-ops release verify --registry "$SIG_RELEASE_REGISTRY" --work-dir <work-dir>
# promote: metadata-only — writes registry/conf/<gen+1>, rolls sig-api then
# sig-web as NEW revisions by digest, runs the post-promote checks. The
# --approval record is the operator's (registry/approvals/); the verb
# verifies it, never creates one.
uv run sig-ops release promote --registry "$SIG_RELEASE_REGISTRY" \
    --publication <p-…> --approval <name> \
    --api-image "<image>@sha256:<digest>" --web-image "<image>@sha256:<digest>"
```

A republish's `conf/<gen+1>` carries the CURRENT withdrawal set: `promote`
re-derives `withdrawn.conf` from the withdrawal registry when its digest
moved since the prior generation (`withdrawals_sha256` in `latest.json`
records what the map was composed from — D-P35.54-1). A disposition
journaled in the verify→promote window is never carried over stale.

## 11. Rollback a release

*Labels: `engineered/local` on a fixture registry; `--apply` is `live`
mutating, `human/operator-only` — it writes `conf/<gen+1>` and records
roll legs (executed only with `--execute-rolls`).*

`release rollback --to <pub|label|legacy-YYYYMMDD>` re-points `latest` at
an earlier PROMOTED release, an imported legacy floor, or a label.
**Cloud Run traffic reversion is forbidden (RR-7)** — an old revision's
pinned `SIG_CONF_GEN` would re-serve routes a later withdrawal denied.
The verb always rolls NEW revisions: the conf generation's env moves
(`SIG_CONF_GEN`, `SIG_LATEST_PUB`), never a revision pointer back.

```bash
# plan — resolves the target, prints the generation + roll legs
uv run sig-ops release rollback --registry "$SIG_RELEASE_REGISTRY" \
    --to <p-…|label|legacy-YYYYMMDD> --reason "<why>" 
# apply — needs --reason + --go (the operator's go/pre-authorisation
# record under registry/authorities/, §7.3's needs-no-readout set)
uv run sig-ops release rollback --registry "$SIG_RELEASE_REGISTRY" \
    --to <target> --reason "<why>" --go <name> --apply
# archive-only: no current release — latest clears to the v/none/
# sentinel; the archive (promoted namespaces + withdrawal barrier) serves
uv run sig-ops release clear-latest --registry "$SIG_RELEASE_REGISTRY" \
    --reason "<why>" --go <name> --apply
```

What the apply does, in order: re-apply the CURRENT withdrawal set over
every staged namespace (the barrier is re-derived, never carried) → write
`registry/conf/<gen+1>` (create-if-absent; the promoted set never shrinks)
→ roll `sig-api` → `sig-web` as new revisions → journal `rolled-back`
(+ `rolled-back-from` on the prior latest). A rollback target under a
current denying release disposition is REFUSED — a rollback never
resurrects withdrawn material. The first release has no predecessor —
`clear-latest` is the honest no-current-release state, never a fabricated
one.

The **legacy floor** (§8.5): a pre-registry serving tree imports as
`staged/v/legacy-<YYYYMMDD>/`, labelled `legacy-…` — never a `p-<64hex>`
id and never a promoted release namespace:

```bash
uv run sig-ops release import-floor --registry "$SIG_RELEASE_REGISTRY" \
    --from <dir> --label legacy-<YYYYMMDD> --go <name> --apply
uv run sig-ops release rollback --registry "$SIG_RELEASE_REGISTRY" \
    --to legacy-<YYYYMMDD> --reason "<why>" --go <name> --apply
```

## 12. Withdraw / takedown

*Labels: `engineered/local` on a fixture registry; `--apply` is `live`
mutating, `human/operator-only`. `--purge-versions` is the Part
VIII/legal-takedown lane — bucket objects only, never the claim spine.*

`release withdraw --disposition <file> --authority <name>` runs the §8.3
order verbatim: parse + validate the `sig.withdrawal-order/1` file →
verify the authority record (`registry/authorities/<name>` —
SIG-SEC-010; checked, never created) → append-only disposition INSERT
→ re-apply the barrier over EVERY staged namespace → a new
`conf/<gen+1>` whose `withdrawn.conf` carries full alias coverage →
roll api→web → cache purge hooks → probe every alias → a dated receipt
under `registry/receipts/`.

```bash
# the order file: sig.withdrawal-order/1 — {entries: [{target_kind,
#   target_id, disposition, reason_category, compartment?}]}. An
# `allow` row is the reinstatement path — a NEW disposition, never an
# edit. `compartment` scopes the deny to c/<comp>/ routes only (§42.3).
uv run sig-ops release withdraw --registry "$SIG_RELEASE_REGISTRY" \
    --disposition <order.json>
# apply — the dated sig.tombstone/1 lands on every alias (no-slash,
# trailing-slash, index.html, .json, release namespaces, record routes,
# entity stubs, label aliases); private rationale never leaves the registry
uv run sig-ops release withdraw --registry "$SIG_RELEASE_REGISTRY" \
    --disposition <order.json> --authority <name> --apply
# the legal-takedown lane — additionally deletes the removed objects'
# NONCURRENT bucket versions (live generations stay; a local registry
# reports noop). Never the claim spine, never release evidence.
uv run sig-ops release withdraw --registry "$SIG_RELEASE_REGISTRY" \
    --disposition <order.json> --authority <name> --apply --purge-versions
```

The 15-minute withdrawal target is a recorded target (D-G3-9), measured
at rehearsal — never claimed here. Withdrawal alias coverage includes the
error-page surface (`D-P34.13-1` rides P34.40's change). The P1 alarm —
an origin serving an OLDER conf generation — is the registered
`conf-gen-regression` probe; a NEWER unrecorded generation means the
registry record is stale:

```bash
uv run sig-ops conf-gen-probe --registry "$SIG_RELEASE_REGISTRY" \
    --origin https://api.surveillancegraph.org \
    --origin https://surveillancegraph.org
```

The R2/CDN purge hooks are wired and dormant: `ops/mirrors.toml` carries
the mirror row disabled/gate-pending (J3 TX-11) — a missing mirror is a
recorded no-op, never an error. Withdrawal is append-only end to end:
reinstatement is a new disposition + a new release; tombstones are
immutable per disposition; `registry/` events and receipts journal every
step so the act stays auditable.

## Verifying this runbook

```bash
# this file's commands/paths/register against the tree it names
python3 docs/build/tools/check_runbook.py
# prose claims in docs/ops/** swept by the corpus lint (SIG-MEM-011)
python3 docs/build/tools/check_live_claims.py corpus
# the docs gate (includes both lines above)
make docs-check
```

When the hosted shape changes (a new job class, a secret added to
`ops/iam_identities.toml`, a cadence-section rename), this file and the
checker are updated in the same commit — a runbook the tree no longer
verifies is a defect, not a suggestion.
