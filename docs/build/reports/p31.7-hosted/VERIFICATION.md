# P31.7 hosted verification — claim re-sightings + latest-capture dating

Ticket: `P31.7 / DEEPEN.3` — `docs/tickets/P31.7__claim-re-sightings.md`
ADR: ADR-114 (re-sighting links + latest-capture dating + resolution supersession).
Host: project `zeta-medley-508121-u7`, region `us-central1`, Cloud SQL `sig-pg`.
Read-only measurement ran `SET default_transaction_read_only = on` over
cloud-sql-proxy (`127.0.0.1:15499`) as `sig`; writes ran inside Cloud Run job
executions next to the database (`sig-sink-bench`, `sig-materialize` with role
`sig_materialize`). Nothing was `UPDATE`d or `DELETE`d on the spine — the only
temporal write is the §16.4 sys_period closure performed by the SECURITY DEFINER
`close_superseded_resolutions` (recorded history is kept).

## Images (digest-pinned, ADR-111)

| job(s) | image | digest | build |
|---|---|---|---|
| all ingest/probe jobs (rolled) | `sig/sig-api:p31-7-062306e70d3d` | `sha256:6ad5477d4aacde23d508f5eea765a6ad835e603ad794b10df56710acca4414f5` | `5903cb4f-8861-42b8-894d-08b61dee1163` (87 s) |
| `sig-materialize` | `sig/sig-api:materialize-062306e70d3d` | `sha256:959c40c6074b7d1e30ad15787d7569ce01f935356aba0010e47efee64687b2d5` | `8f94714a-a36c-469b-b2bc-587cf1746f9d` (58 s) |

`:latest` never moved. `sig-sink-bench` updated to the same digest.

## Schema

`materialize.sh --apply schema` (sqitch over the proxy, schema owner `sig`):
`+ partner_org_identity_key` (owed since P31.5 — its backfill had not yet been
deployed hosted) and `+ resolution_supersede`, both `ok` with `--verify`.

## Roll (`roll_record.json`)

`sig-ops roll-jobs --image …:p31-7-062306e70d3d --exclude sig-ingest-camreg-batch-05
--apply`: **70 jobs planned → 70 applied → 70 verified** on `sha256:6ad5477d…`,
before-digests recorded per job (`feff986c…`/`ad06e964…` retained for rollback).
`sig-ingest-camreg-batch-05` confirmed still on `sha256:feff986c…` (D-P31.4-1 —
no roll until the 2026-10-10 replay outcome is recorded).

## Baseline → after the bounded sink-bench measurement

Execution `sig-sink-bench-pxgq9` (Cloud Run, 2 vCPU/4 GiB, Cloud SQL socket):
`python -m ops sink-bench --source camreg_fl511_fl --passes 2 --code-commit
p31.7-resight-bench`. The bench now wires the production `on_duplicates` hook,
so its passes exercise the exact write path a rolled ingest job takes.

| measure | before (08:20:56Z) | after (08:27:01Z) | delta |
|---|---|---|---|
| `claim_evidence` rows | 2,391,551 | 2,623,647 | **+232,096** |
| `pg_total_relation_size(claim_evidence)` | 357,752,832 B | 406,708,224 B | **+48,955,392 B (46.7 MiB)** |
| `pg_relation_size` (table) | 183,255,040 | 201,023,488 | +17,768,448 |
| `pg_indexes_size` | 174,415,872 | 205,594,624 | +31,178,752 |
| `claim` rows | 2,391,551 | 2,403,886 | +12,335 |
| `pg_database_size('sig')` | 4,776,916,671 | 4,833,670,847 | +56,754,176 B |
| `evidence_capture` rows | 269 | — | +2 (one per pass) |

Per-pass (`ingest_run_completion`, both `status=ok`, `is_replay=false`):

| pass | run_id | considered | inserted | duplicate | links added (claim_evidence join on `retrieved_by_run_id`) |
|---|---|---|---|---|---|
| 1 | `01a0d7aa-6311-7671-b824-c46281eedbe0` | 128,383 | 12,335 | 103,713 | **116,048** (12,335 new-claim establishes + 103,713 re-sightings) |
| 2 | `01a0d7aa-ddea-73e8-9b53-6b530c9c7b9b` | 128,383 | 0 | 116,048 | **116,048** (every duplicate re-sighted onto the pass's own capture) |

Every duplicate re-assertion appended a link — uncapped; pass 2's second capture
proves one link per (claim, capture) (the PK gives +0 only for the *same*
capture — proven on real PG in `tests/db/test_resightings.py`).

**Bytes/link (measured):** 48,955,392 / 232,096 = **210.9 B per link** (table +
both indexes, amortised). `n_tup_upd` = `n_tup_del` = 0 on `claim`,
`claim_evidence`, `resolution` (pg_stat, post-run).

## Disk (read live)

`gcloud sql instances describe sig-pg`: `dataDiskSizeGb` = **15** (PD-SSD,
`storageAutoResize: true`), tier `db-custom-1-3840` (ADR-107).

| measure | value |
|---|---|
| DB used | 4,833,670,847 B ≈ 4.83 GB → **32.2% of 15 GB**; **48.3% of the operator's 10 GB comparison** |
| `claim_evidence` share of DB | 406,708,224 / 4,833,670,847 ≈ 8.4% |

## 12-month projection (uncapped policy)

Model: every scheduled execution links every claim its source re-asserts —
`≤ claims_per_source × runs_per_month`. Cadence mix (`ops/cadence.toml`):
63 monthly jobs (55 sources + 8 camreg batches — OSM `camreg_osm_surveillance`
monthly via batch-05 dominates at ~1.37M claims/run), 6 weekly, 1 quarterly.

- Upper bound ≈ **2.5M links/month** (~2.3M monthly-cadence claims + ~0.13M
  weekly ×4.33 + quarterly amortised) → **~530 MB/month** at 210.9 B/link.
- **12 months ≈ 6.4 GB** of `claim_evidence` growth: **43% of the 15 GB disk**
  (below the 50% ADR-114 trigger) but **64% of the 10 GB comparison** (crosses
  in ~9–10 months). Total DB at 12 months ≈ 4.8 + 6.4 ≈ **11.2 GB — 75% of
  15 GB**; vs the 10 GB figure it would exceed it. Autoresize is on; the
  revisit trigger stands as written in ADR-114 (a), with the 10 GB reading
  flagged for the operator.
- Sanity anchor: this measurement alone (+232k links / +49 MB) came from ONE
  source × 2 passes; the camreg batch monthly sweep is the dominant term and
  batch-05 stays un-rolled until 2026-10-10 (D-P31.4-1).

## Resolution materialization (`sig-materialize`, role `sig_materialize`)

First run `sig-materialize-bnq5m` (08:28:51Z → 09:33:39Z, 65 min, exit 0) — the
first resolution pass since P30.2a's predicate registration, the P31.5/P31.6
entity-ref claims, and the new latest-capture basis:

| metric | value |
|---|---|
| `considered_pairs` | 1,965,997 |
| `inserted` (new decision rows) | **203,786** |
| `skipped_existing` (unchanged digest, +0) | 1,732,911 |
| `skipped_unresolvable` | 29,300 |
| `resolved` / `unresolved` | 1,936,366 / 331 |
| **`superseded`** (live `auto` rows closed — changed input_digest) | **139,433** |
| **`skipped_pinned`** (live non-auto decisions blocked) | **0** |

Post-run reads (read-only): `resolution` total 2,076,130 rows; live
(`upper_inf(sys_period)`) 1,936,697 = 1,732,911 unchanged + 203,786 new; closed
history 139,433 (= `superseded` exactly — every closure matched a new row);
zero duplicate live `(subject, predicate)` pairs (`resolution_no_overlap` held);
all live rows `decided_by='auto'`. Of the live rows, 173,370 carry
`rules_fired` basis `…observed_at=capture_retrieved_at_latest`; the rest keep
their 09-24 decision — the digest covers the *date*, so a group only
re-materializes when a sighting really moved it (honest churn, ADR-114).
`pg_total_relation_size('resolution')` = 2,877,759,488 B; whole DB now
5,186,614,975 B (≈5.19 GB — includes the ~203k new decision rows).

- re-run: the first attempt `sig-materialize-9jlgv` died mid-pass on a Cloud SQL
  connection reset (`server closed the connection unexpectedly` — infrastructure,
  not a write failure; the transaction rolled back and post-failure reads showed
  counts unchanged, 0 partial rows). The retry **`sig-materialize-mdfpm`
  (09:47–11:48Z, ~2 h, exit 0) is a clean +0**: `inserted` 0, `superseded` 0,
  `skipped_pinned` 0, `skipped_existing` **1,936,697** (= every live row),
  `skipped_unresolvable` 29,300, `resolved`/`unresolved` 1,936,366/331 —
  `skipped_existing + skipped_unresolvable = considered_pairs` exactly, and the
  1,936,697 skipped live rows equal the post-first-run live count to the row.
  The unchanged-input re-run writes nothing.

## Dispositions

- **D-P30.2a-2 → DONE** — re-ingest of an unchanged registry adds
  `claim_evidence` (+0 claims); A → B → A resolves to A on real PG and the new
  basis is recorded in `rules_fired`; hosted growth measured vs the live-read
  15 GB disk (+ the 10 GB comparison) with the threshold written into ADR-114.
- **D-P31.4-1 → OPEN** — batch-05 untouched pending the 2026-10-10 replay.
