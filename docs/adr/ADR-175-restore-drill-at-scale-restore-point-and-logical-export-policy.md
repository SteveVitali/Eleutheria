# ADR-175 — Production data protection and restore drills: PITR clone parity, scripted AR-2, monthly logical export (P34.6)

- Date: 2026-10-02
- Status: accepted (the drill-clone leg is engineered and pre-authorised by the
  11A S5-3 list; the first monthly export, the bucket lifecycle and the seed
  relabel are queued pending an in-ticket go — D-P34.6-2/3/4)
- Ticket: P34.6 (Round 11 / P34, row 207; requirement SIG-OPS-001; answers the
  ADR-081 revisit trigger — Track-0 F-01/F-42, G1 NEW-14; cites SIG-OPS-002 and
  SIG-ENG-045)
- Base: `r11/P34.5-cost-guard-budget-alert-billing-export` (Round-11 chain)

## Context

ADR-081's hosted deployment (Cloud SQL `sig-pg` + Cloud Run) shipped with
incomplete protection: Track 0 enabled automated backups and 7-day PITR on
2026-09-30, but the only restore drill used a five-claim seed into a database
*inside* the same instance (GCP_DEPLOYMENT §"Cloud restore drill"), deletion
protection was still off until P34.3, and the backup bucket held two
2026-09-15 seed dumps indistinguishable from real backups. ADR-081's revisit
trigger fired on exactly this gap ("managed backups replace the drill" was
untrue). P34.6 closes the durable-restore half; five design questions needed
a recorded answer:

1. **What proves "restorable at scale"?** Not a database restore inside the
   same instance (the 2026-09-15 drill shared the production instance's
   failure domain) but a point-in-time **clone into a separate Cloud SQL
   instance**, verified by reading both instances.
2. **What does "exact append-only parity at the restore point" mean?** The
   source keeps writing after T, so a total row count can never be the
   comparison — parity must be evaluated *at T* per the temporal columns the
   spine already records.
3. **How is the disposable instance safe to delete?** The delete must be
   incapable of naming production *by construction*, not by care.
4. **What does a logical export add over managed backups?** Managed backups
   and PITR die with the instance (retain-on-delete notwithstanding, the
   instance's lifecycle owns them); a SQL dump in a GCS bucket is a separate
   failure and lifecycle domain — the monthly cadence is the durable copy.
5. **How do pre-P34.6 bucket objects stay preserved without ambiguity?** The
   two 2026-09-15 seed dumps are seed artefacts, not backups; deleting them
   would lose the seed evidence, leaving them mislabels them.

## Decision

**The drill** (`ops/gcp/restore-drill.sh`, engine `ops/src/ops/
cloudsql_drill.py`, CLI verb `sig-ops cloudsql-drill`): clone `sig-pg` at
`T = now − 10 min` into `sig-pg-drill-<YYYYmmddtHHMMz>` via
`gcloud sql instances clone --point-in-time`; connect to BOTH instances
through the Cloud SQL Auth Proxy (read-only `sig` login; the DSN travels in
`SIG_DRILL_DSN_{SOURCE,CLONE}` env, never argv — a command-line DSN leaks
into the process list); verify exact parity *at T*:

- per-table counts with an `instant <= T` predicate for each table the
  shared-temporal-contract facet map already tracks (`claim`/`resolution` →
  `lower(sys_period)`, `claim_evidence` → `bound_at`, `evidence_capture` →
  `retrieved_at`, `entity` → `created_at`, `ingest_run` →
  `coalesce(finished_at, started_at)`, `ingest_run_completion` →
  `recorded_at`, `contradiction` → `resolved_at`, `coverage_record` →
  `searched_at`); `evidence_artifact` has no commit-instant column and is
  compared as a total, marked `bounded_by_t: false` in the record. The engine
  is schema-aware: it reads `information_schema` on both sides and applies an
  instant expression only where the deployed schema carries every column it
  touches — a facet the schema cannot answer degrades to an unbounded count
  recorded `instant: null`, a table absent on either side is recorded drift,
  and the effective map must match on both sides (`schema_map_equal`). On the
  2026-10-02 leg the deployed spine predated P32.4, so `claim_evidence` counted
  unbounded and the watermark was absent on both (recorded
  `watermark_present: false`) — honest parity, never a fabricated predicate;
- the `spine_watermark` row set verbatim on both sides (present on both, or
  absent on both — either way the comparison is recorded explicitly);
- the ordered `sqitch.changes` tip on both sides (the drill reads plan
  *state*; D-P32.10a-1's `sqitch verify` defect is a verify-command bug,
  never to be mistaken for a restore failure);
- PostGIS presence + `extversion` on both sides;
- a local `sig-api serve --dsn <clone>` smoke: `/health` → 200 and one
  `/v1/coverage/<scope>` call;
- **RTO** = clone-submit timestamp → parity-verified timestamp;
  **RPO** = `T − max(lower(claim.sys_period))` on the clone.

The record is `record.json` (`sig.restore-drill/1`) under the gitignored
`docs/build/logs/restore-drill/`; every field is measured or explicitly null.

**Deletion safety**: the name gate `assert_drill_name` accepts only
`sig-pg-drill(-b)?-<YYYYmmddtHHMMz>` (the producer's own stamp shape —
`-b-` marks the full-backup variant) and refuses `sig-pg` outright before the
pattern is even consulted, so a deletion command built from it cannot name
production; a hand-typed or truncated name fails closed (exit 42).

**Voided-by (stop rules)**: the drill clone is pre-authorised (11A S5-3,
expiring GATE-G4) only when the newest `sig-pg` backup is `SUCCESSFUL`, the
latest `sig-probe` sweep is green or its red is recorded by `--probe-note` as
the known class, no `sig-materialize` execution is running (fail-closed on an
unreadable check), and the clock is outside 03:00–10:00Z. The clone is *not*
bound by AR-3 (a separate instance); the export leg *is* (its `pg_dump` load
runs on sig-pg's single vCPU).

**The AR-2 procedure is scripted** (`ops/gcp/restore-point.sh`): `sqlpoint`
proves an on-demand backup `SUCCESSFUL` before any mutation proceeds;
`bucketpoint` mirrors named `gs://<project>-sig-*` objects into
`sig-restricted/restore-point/<STAMP>/` with a written manifest.

**Monthly logical export** (`ops/gcp/logical-export.sh export`):
`gcloud sql export sql` of the `sig` database to
`gs://<project>-sig-backups/pg/monthly/<YYYY-MM>/sig-<STAMP>.sql` — the dump
lives in the bucket, outside the instance's lifecycle. Cadence is the
`[[maintenance]]` row in `ops/cadence.toml` (`pg-logical-export`, day 1 at
12:00 UTC — outside the band; GCP cron's dom+dow OR semantics rule out
"first Sunday"). P35.1a's scheduler of record deploys the trigger.

**Bucket lifecycle** (`logical-export.sh lifecycle`): two rules only —
Delete `pg/monthly/*` at 100 days (the three newest monthly exports are
always kept) and Delete `pg/adhoc/*` at 30 days. Existing non-P34.6 rules
make the leg REFUSE: foreign rules are never silently overwritten.

**Seed relabel** (`logical-export.sh relabel`): the 2026-09-15 dumps are
*copied* to `pg/seed-2026-09-15/` with a README object; originals are never
deleted — the append-only posture extends to the bucket.

## Consequences

- The drill record makes "restorable" a measured claim: exact parity, RTO and
  RPO are numbers in `record.json`, not assertions.
- The `-b-` variant (`fullrestore`, `gcloud sql backups restore` into an
  empty `sig-pg-drill-b-<STAMP>`) covers the full-backup path; it is queued
  with the export/lifecycle/relabel legs until an in-ticket go, as is the
  after-schema-deploy drill — `sqitch deploy` changes `sqitch.changes`, so
  re-running the drill after each schema-changing deploy is the regression
  check.
- `evidence_artifact` is the one table parity cannot time-bound; its total
  count is compared and the record says so (`bounded_by_t: false`) — an
  honest edge, not a hidden one.
- The `[[maintenance]]` cadence row is inert to `scheduled-ops.sh` (which
  reads only `probes`/`runs`/`sources`/`batches`); it declares intent for the
  scheduler of record without silently scheduling anything.

## Revisit trigger

Revisit if the instance tier or engine changes (a non-f1-micro tier, an HA
instance, or a non-Postgres engine re-prices the clone-and-delete leg); if
`sig-pg` outgrows the point-in-time clone's practical window (the clone copy
is the whole instance — a multi-GB spine may favour a database-level import
drill); if `evidence_artifact` gains a commit-instant column (extend
`DRILL_TABLES` and drop the `bounded_by_t` edge); if GCP ships a per-database
PITR granularity that makes the separate-instance clone unnecessary; or if
the scheduler of record lands (P35.1a) and the `[[maintenance]]` row moves
from declaration to a real trigger.
