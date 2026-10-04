# P34.24b — L44–52 clone rehearsal record

<!-- Committed evidence record for the pre-authorised (OM-20 S5-3) PITR-clone
     rehearsal of `db/sqitch.plan` L44–52 → plan tip, run through P34.6's
     drill machinery. `sig-pg` was read-only throughout. Raw artifacts live
     under the gitignored `docs/build/logs/restore-drill/drill-*/rehearsal/`;
     this file is the committed `sig.sqitch-rehearsal/1` summary. Dates are
     `date -u` / gcloud / PostgreSQL timestamps. -->

Written: 2026-10-04T13:05Z (`date -u`), after the second (corrected-sampler)
rehearsal leg completed and both clones were deleted.

## Headline — the rehearsal found a real deploy blocker

**The plan tip does not deploy on the production-shaped instance.** On two
independent PITR clones of `sig-pg`, `sqitch deploy --verify` progressed
through six L44–52 changes and then failed inside the `intake_storage`
verify script:

```text
psql:verify/intake_storage.sql:80: ERROR:  permission denied to set role "sig_intake_receiver"
```

`db/verify/intake_storage.sql:80` is `SET LOCAL ROLE sig_intake_receiver`
inside the verify transaction. The local/testcontainer `sig` login is a true
superuser, so `SET ROLE` always succeeds there; the Cloud SQL `sig` login is
not a superuser and holds **no membership** in the deploy-created `NOLOGIN`
role, so `SET ROLE` is refused. `grep` shows the same `SET ROLE` mechanism
in `db/verify/intake_application_bridge.sql` and `db/verify/recovery_apply.sql`
— the same failure class would be expected twice more downstream
(*inference*, labelled: those verifies were never reached).

Sqitch reverted cleanly both times (`Reverting to camera_site_human_decisions`,
six changes reverted `ok`), `sqitch verify` on the reverted head exited 0,
and the clone's `sqitch.changes` head returned to `camera_site_human_decisions`
(39 changes) — identical before and after.

**Consequence for P34.46:** the deploy it would run cannot currently succeed.
The measurements below are real but cover only the seven attempted changes
(`claim_assertion_bindings` … `intake_storage`); `intake_application_bridge`,
`recovery_apply`, the reworked `shared_temporal_contract`,
`public_read_allowlist`, and the two verify reworks were never attempted.
Fixing the defect is out of this row's scope (contract § Out of scope — "a
new appended change in a later row, after the operator is told"); it is
carried as **D-P34.24b-1** in `docs/tickets/DEFERRALS.md`.

## Identity of what was rehearsed

| field | value |
|---|---|
| rehearsed plan tip sha256 | `eef95739db72e06150c34e4a04af9e10faac2f3f0fadad3ed45f1f098822895e` |
| L44–52 span sha256 | `8cc9d3db4dfc9335821cc4ecef181ee0c9f96231346ce231567e0f55b413a9fc` |
| L44–52 byte-identical to base | **true** (C-10; computed live both attempts) |
| plan tip line | 58 |
| chain-tip commit (attempt 1) | `185f9415` |
| chain-tip commit (attempt 2) | `39e2f914` (fix-forward of the harness; the plan file is identical — the sha above covers both) |
| sqitch image | `sqitch/sqitch@sha256:f247ab0e0b66e9c2d09a400864f7314358893f5cf209cddcc4f213f7d5bfe4d3` (pinned digest) |
| `db/` mount | read-only (`-v "$REPO_ROOT/db:/repo:ro"`) |
| lock_timeout | `PGOPTIONS=-c lock_timeout=1200000` (the FEA-07 20-min ceiling as a bound) |

## The two attempts (both recorded — nothing smoothed)

| | attempt 1 | attempt 2 (corrected sampler) |
|---|---|---|
| evidence dir | `drill-20261004T122402Z` | `drill-20261004T124449Z` |
| clone | `sig-pg-drill-l44-20261004t1223z` | `sig-pg-drill-l44-20261004t1244z` |
| clone point-in-time | 2026-10-04T12:14:02Z | 2026-10-04T12:34:49Z |
| clone issued / RUNNABLE | 12:24:02Z | 12:44:49Z (op `2fe3b660-…0032`, CLONE DONE) |
| deploy window | 12:34:08.336 → 12:35:57.308Z | 12:53:57.786 → 12:55:24.324Z |
| deploy exit / wall | **2** / 108.972 s | **2** / 86.538 s |
| failure | `intake_storage` verify, `SET ROLE sig_intake_receiver` denied | identical |
| revert | to `camera_site_human_decisions`, 6 changes `ok` | identical |
| `sqitch verify` after | exit 0 (12:35:58→12:36:15Z) | exit 0 (12:55:25→12:55:42Z) |
| lock samples | 214 — **all errored** (pre-fix SQL `a.datname = l.database`) | 238, **0 errors** |
| clone deleted | 12:42Z delete leg | 12:57Z delete leg |

Attempt 1 ran the freshly-landed harness and found two live-only defects: the
sampler's `pg_locks.database` join compared `name = oid` (214/214 samples
errored — its `claim_evidence` headline is recorded as `null`, never a
fabricated zero), and the deploy-log parser missed the real `+`/`-`/`ok`
line shapes (rebuilt with the corrected parser — the stamped log is raw and
untouched). Commit `39e2f914` fixed both on this branch; attempt 2 is the
pristine measurement on a fresh clone.

## Per-change timing (attempt 2, deploy order)

| change | seconds | status |
|---|---:|---|
| claim_assertion_bindings | 15.965 | ok |
| partner_org_scoped_identity_key | 1.093 | ok |
| shared_temporal_contract | 51.576 | ok |
| publication_dispositions | 2.086 | ok |
| human_eval_campaign | 4.965 | ok |
| disposition_decided_at_authority | 1.102 | ok |
| intake_storage | 2.682 | **failed** (verify SET ROLE) |
| *not reached:* intake_application_bridge, recovery_apply, shared_temporal_contract (rework), public_read_allowlist, read_surface_grants (rework), review_campaign (rework) | — | never attempted |

Attempt-1 timings for the same prefix: 19.395 / 1.154 / 69.940 / 2.146 /
5.239 / 1.188 / 2.698-failed (108.972 s wall; the clone had colder caches).
Revert legs (attempt 2): 0.483–1.512 s per change, all `ok`.

## `ACCESS EXCLUSIVE` on `claim_evidence` — the go/no-go number

Sampler: 238 samples @ 250 ms, 0 errors, 96 lock episodes total.

| relation | episodes | max observed hold | honest upper bound |
|---|---:|---:|---:|
| **claim_evidence** | **3** | **13.344 s** | **13.844 s** |
| claim_evidence_pkey | 2 | 5.926 s | 6.426 s |
| pg_toast_19137(+idx) | 2 | 1.109 s | 1.609 s |

The 13.344 s episode is `ALTER TABLE claim_evidence ADD COLUMN …`
(claim_assertion_bindings, pid 296, first-seen 12:53:59.286Z, last-seen
12:54:12.631Z, 37 samples, continuously granted). `observed_s` is the
sampled floor; `upper_bound_s` adds one 250 ms interval on each side; the
containing change's 15.965 s bounds the hold from above. Revert-phase
claim_evidence holds were single-sample (≤ 0.5 s bound).

**P34.46 thresholds (plan §5.9 / FEA-07):** lock ≤ 20 min **and** ≤ 2× this
measurement → the observed 13.344 s is far inside both. **But the caveat is
binding:** the deploy stopped at change 7 of 13; the unattempted changes
could hold locks this measurement cannot see. The 13.344 s is a *measured
floor for the attempted prefix*, not a certified maximum for the tip.

## Temporary disk and index builds

- `pg_stat_database.temp_bytes` delta over the deploy+revert:
  **+272,883,712 B (~260.2 MiB)**, 6 temp files (attempt 1: 272,891,904 B —
  8 KiB different, same shape).
- `claim_evidence` total relation bytes: 441,139,200 → 501,301,248
  (**+60,162,048 B ≈ +13.6 %**) — measured post-revert; the failed attempt's
  column adds leave dead space the revert does not reclaim.
- Database total: 6,158,931,647 → 6,219,871,935 B (+60.9 MB).
- `pg_stat_progress_create_index`: **no in-progress index build was caught
  at any sample instant** in attempt 2 (`index_builds: []` — honest empty,
  not "none happened": builds shorter than the 250 ms cadence are
  invisible; the revert-phase `CREATE UNIQUE INDEX claim_qualifier_pk` was
  visible only as a lock, ~0.5 s).
- Disk headroom check (P34.46): needs ≥ 2× `claim_evidence` (~0.88 GB)
  against the instance's 15 GB volume — ample.

## `sig-pg` untouched (the no-write evidence)

`pg_stat_database` on the **source** (sig-pg, read-only legs only), attempt 2
pre→post deltas: `tup_inserted` 0, `tup_updated` 0, `tup_deleted` 0,
`temp_bytes` 0, `temp_files` 0, `xact_rollback` 0; `xact_commit` +41 and
`tup_fetched` +7,959 — read traffic only (the snapshot queries themselves).
The instance operations list before/after shows backups/UPDATEs predating
the leg; the only new operations across both legs were the two
`sig-pg-drill-l44-*` CLONEs and their DELETEs.

Post-state (`gcloud`, `date -u` 2026-10-04T12:59:22Z):
`sig-pg` RUNNABLE, tier `db-custom-1-3840`, deletionProtection `False`
(unchanged — `D-P34.3-1` stays OPEN); **no `sig-pg-drill-*` instance
remains**. `git status` on `db/sqitch.plan`: clean — no line edited or
re-stamped (C-10).

## What the record cannot claim

- No lock data exists for attempt 1 (214/214 sampler errors — recorded as
  `null`, per the record's bounds note).
- No measurement exists for the six unattempted plan changes.
- The clone is a `db-custom-1-3840` PITR copy at a single point in time —
  timing on production under live load will differ; this is the floor P34.46
  was promised, not a production guarantee.
- `verify` exit 0 means *the reverted head verifies* — it is not a green
  deploy verification.
- No human check performed (Round-11 truth rules); all numbers here are
  machine-measured on the named clones.

## Cost

≈ $0.15–0.40 per clone-hour (contract G2 step-1 estimate, inference): two
`db-custom-1-3840` clones lived ~18 min and ~13 min; both deleted.

## Raw evidence index (gitignored)

- `docs/build/logs/restore-drill/drill-20261004T122402Z/rehearsal/record.json` — attempt 1
- `docs/build/logs/restore-drill/drill-20261004T124449Z/rehearsal/record.json` — attempt 2 (corrected sampler)
- `…/deploy.stamped.log`, `…/samples.jsonl`, `…/head|post|source-*.json`, `…/verify.log`, `…/operations-*.json`, `…/plan-hashes.json` under each dir.
