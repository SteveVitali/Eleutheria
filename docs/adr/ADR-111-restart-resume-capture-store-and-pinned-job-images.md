# ADR-111 — Restart = resume: per-capture flush, capture marks, a GCS capture store, and jobs pinned by digest

- **Status:** Accepted
- **Phase / ticket:** Phase 31 / P31.4 (`docs/tickets/P31.4__incremental-restart-and-osm-replay-readiness.md`) — Round 9 `HARDEN.4`. This is the design's placeholder `ADR-R9-RESUME`; it also records the job-image decision the design assigns to P31.4 ("rolling the scheduled ingest jobs onto new code is owned by P31.4").
- **Date:** 2026-09-25
- **Related:** §3.1 (the defining standard: a skipped fetch never hides a disappearance), §16 (the append-only claim spine), §17 (OCFL captures), §21 (the connector stages; SIG-INGEST-001/009/018/019), ADR-059 (content-digest idempotency), ADR-102 (the OSM land baseline), ADR-107 (the `db-custom-1-3840` tier; the 36 h batch-05 task timeout; §5 "a label-only update re-resolves `:latest`"), ADR-109 (one `ingest_run` per execution; appended completions — the run identity the resume key builds on), ADR-110 (batched sink; extension point (c): each `assert_claims` call is a commit boundary). Deferrals **D-P30.1-2**, **D-P31.3-1**, **D-P31.1-2**; backlog home **BL-057**.

## Context

- **Restarts started from zero.** `connectors.pipeline.run` held every claim of a run in memory and asserted
  them with **one** `assert_claims` call at the end. P26.18's chunked commits made that call resumable at the
  DB level, but a restart still re-fetched every page and re-walked every record: P30.1's `tjqdq` replay spent
  about 3.5 h inserting 0 rows while it walked the 930,000 claims the cancelled execution had committed. The
  run also held about 1.37M OSM records (plus five in-memory copies of every stage artifact) in one process.
- **Hosted captures did not survive the execution.** Measured 2026-09-24 before any change: every
  `sig-ingest-*` job wrote its OCFL captures to the container's own disk (`/app/.sig/ops/captures`; no job
  mounted a volume), and no bucket held a single capture object (`gs://…-sig-restricted` had only `ops/`,
  `exports/`, `web/`, `rollback/`, `manifest.json`; `gs://…-sig-backups` only `pg/`). So "resume from the stored
  capture" had nothing to read on hosted.
- **Every scheduled job ran `:latest`.** 72 of the 75 `sig-api` jobs were deployed as `sig-api:latest`
  (`sha256:ebb6dab9…`, the 2026-09-22 build); only the three on-demand ones (`sig-materialize`, `sig-export`,
  `sig-sink-bench`) ran SHA tags. And `ops/gcp/scheduled-ops.sh` deployed
  `${SIG_API_IMAGE}:latest`. None of P31.1–P31.3 had reached a scheduled run, and any redeploy would silently
  pick up whatever the tag pointed at. The script also planned batch jobs at `--task-timeout 120m` while the
  live batch jobs ran 36 h (ADR-107), so a re-apply would have broken the OSM replay.

## Decision

1. **Flush per capture.** After each target's post-capture stages the pipeline calls `assert_claims` with that
   capture's claims (ADR-110 (c): one call = one commit boundary). Replay and shadow runs still assert nothing.
   A live PG run keeps only the records its fetch record reports (`RunContext.retain_record`) and one artifact
   per stage (`ArtifactStore(keep_history=False)`), so memory is bounded by one capture. `RunReport.claim_count`
   keeps the exact emitted count; the run row's `claims_added` reads it.
2. **Capture marks, append-only.** A new sqitch change adds `ingest_run_capture (run_id, target_key, state,
   capture_digest, source_uri, media_type, byte_size, retrieved_at, records)`, PK `(run_id, target_key,
   state)`, an immutability trigger, `sig_ingest` SELECT/INSERT only. `captured` is appended once the target's
   bytes are in the capture store; `flushed`, with the capture's emitted record count, once every claim of it
   has committed. The target key is its URL plus a 16-hex digest of the whole target mapping, so two targets
   that differ in any parameter never share a key, and a target whose mapping changes simply does not resume.
3. **The logical run = P31.2's executions + the cadence window.** No second run notion: each execution is still
   its own `ingest_run` (ADR-109). `sig-ops scheduled-ingest` records `logical_run = <source>@<last cron fire>`
   in `ingest_run.parameters` (the cron of the source's `cadence.toml` row, else its batch's; five-field cron,
   Vixie dom/dow semantics; `--logical-run` pins it, `--no-resume` disables it). A restarted execution reads
   the marks of the executions of its logical run (same connector name, version **and code commit** — the
   rolled image digest, `SIG_CODE_COMMIT`, which every rolled job carries — and not a replay) that started
   after the last one with a live non-`failed` completion. So a restart on different code never keeps pages
   the old code derived. So:
   - a re-execution after a kill, a cancel, a crash (`failed`) or a task timeout, inside the window, **resumes**;
   - once an execution of the window completes, the next one is a **fresh** run (a manual re-run is +0, never a
     skip);
   - the next cron fire is a new window and **never skips**.
4. **The skip rule.** A `flushed` target is not fetched and not re-walked, but it **is counted as seen**: its
   capture digest joins the run's capture digests and its record count joins the emitted count, so the run row,
   freshness and disappearance detection equal an uninterrupted run's. (It was fetched successfully in the same
   window; a target not yet flushed is fetched fresh, so a page that disappears after the interruption is still
   recorded.) A `captured` target whose bytes the store still holds is **re-processed from the stored capture**
   with no request. Otherwise — the bytes are gone, or the stored capture no longer yields (a transient WAF or
   error page an interrupted run captured, a partly written object) — it is re-fetched (`refetched`), so a
   bad capture can never pin every restart of the window to the same failure. A connector with `discover_more` skips a
   flushed seed only if its bytes are still stored, since resolving follow-on targets reads them. A drifted
   child capture is never marked flushed, so a restart re-records the drift. Quota-governed targets are
   resumed before any request is counted: a resumed target spends no quota.
5. **A GCS capture store for hosted jobs.** Every `scheduled-ingest` job mounts the private restricted bucket
   (Cloud Run gen2 gcsfuse volume `captures` at `/mnt/captures`) and sets `SIG_CAPTURE_DIR=
   /mnt/captures/evidence/captures`, which the wrapper passes to the OCFL capture store. Captures now outlive
   the execution, so the re-process rule works on hosted, and P31.6 has stored evidence to replay.
6. **Jobs are rolled by pinned digest, never `:latest`.**
   - `sig-ops roll-jobs --image <SHA tag|digest> [--apply] --record roll.json` resolves the image to its digest
     (refusing `:latest` and untagged references), records every job's current image and its digest (the
     rollback), runs `gcloud run jobs update --image <digest>` plus the capture store where missing — `update`
     leaves every other setting (timeouts, env such as `SIG_COMMIT_CHUNK_SIZE`, secrets) as it is — and
     verifies each job's configured image afterwards. Rollback is the same command with the recorded digest.
   - `ops/gcp/lib.sh` `pin_image_digest` is the one resolution every deploy script uses: `scheduled-ops.sh`
     (`SIG_JOB_IMAGE`), `materialize.sh` and `export.sh` (their SHA-tagged build, deployed as its digest) and
     `provision.sh` (`SIG_SERVICE_IMAGE`). `scheduled-ops.sh` now plans batch jobs at 36 h and mounts the
     capture store idempotently (remove-then-add). `sig-ops deploy`'s plan builds a SHA tag and deploys its
     digest.
   - `roll-jobs` refuses to apply when a job's current image has no resolvable rollback digest (unless
     overridden), plans the capture volume and its env var separately, sets `SIG_CODE_COMMIT`, and always
     writes its record, even when a roll fails part-way. The recorded rollback digest of a job that ran a
     movable tag is that tag's digest at roll time.
   - A spine without `ingest_run_capture` (an image rolled ahead of its schema) runs without resume rather
     than failing the ingest; the roll itself happens only after the schema is confirmed.
7. **Bounded slices.** `--target-limit N` bounds a live run to its first N targets, lists the rest in
   `sweep_skipped` (reason `target_limit`), and completes `partial` — a measured slice never reads as a full run.

## Consequences

- **Measured on hosted** (2026-09-24/25, `db-custom-1-3840`; first on `sig-api:ingest-a1b9870ab188` =
  `sha256:f00c6daf…c42be`, then re-proven on the final `sig-api:ingest-18355040ccc8` =
  `sha256:feff986c…833f2` after the review fixes; job `sig-ingest-resume-test` = batch-05's shape + the capture store,
  `camreg_osm_surveillance --target-limit 30`, logical run `camreg_osm_surveillance@2026-09-10T03:35Z`):
  - execution 1 cancelled after 15 pages flushed and a 16th captured: no completion; 16 captures (3.6 MB) in
    `gs://…-sig-restricted/evidence/captures/`;
  - execution 2 (resume): **14 fetches for 30 pages** — 15 skipped, 1 re-processed from the GCS capture —
    117,352 records considered, +0, 53.5 s, `partial` (target-limited);
  - execution 3 (a fresh run: the logical run had completed): 30 fetches, 220,009 records (the same emitted
    count and the same 30 capture digests as execution 2), +0, **95.5 s** → about 18.9 pages/min and 138k
    records/min end to end;
  - on the final digest: a fresh run 30 fetches, +0, 100 s; a run cancelled at 15 flushed; its resume **15
    fetches for 30 pages, 15 skipped**, +0, 53.3 s, the same 220,009 emitted and the same 30 capture digests as
    the fresh runs;
  - `n_tup_upd`/`n_tup_del` 0 on `claim`, `claim_evidence`, `ingest_run`, `ingest_run_capture`,
    `ingest_run_completion`, `entity`.
- **Hosted new-claim land rate** (D-P31.3-1; `sig-sink-bench` on the same digest, real sources through the
  live gate, each pass a completed execution): `dot_511_wa` **16,717 new claims in 5.58 s = 179.9k claims/min**
  (0.0025 round trips per claim), then +0 in 1.64 s; `dot_511_il` 8,094 new + 15,906 duplicate in 4.60 s, then
  +0 in 2.02 s. The spine grew by exactly 24,811 claims (2,304,784 → 2,329,595), 0 duplicate digests.
- **The 2026-10-10 OSM replay, projected from these numbers:** 1,369,210 records over 158 pages at the
  measured 138k records/min ≈ **10 min** (≈ 8.4 min by pages), plus new claims at ~180k/min (100k new ≈
  0.6 min) and a container start (≈ 1–4 min): **about 12–15 min**, against the 36 h task timeout and the
  5 h 07 min `tjqdq` baseline. An interruption now costs at most one page.
- **The batch-05 decision (gate Q4):** the hosted bounded test was green on 2026-09-25, before the 2026-10-08
  cut-off, so `sig-sched-camreg-batch-05`'s job was switched with every other job: `sig-api:latest`
  (`sha256:ebb6dab9…`) → `sha256:f00c6daf…` → (after the review fixes, re-tested green) `sha256:feff986c…`;
  36 h timeout, `SIG_COMMIT_CHUNK_SIZE` and 2 CPU / 8 GiB unchanged.
- **A partial landing is now possible.** A seed that drifts or fails at page k leaves pages 1..k−1 committed
  (they are valid claims from valid captures). The `content_drift` fetch record counts the records the sink
  had already been handed, and the execution's `ingest_run_completion` (`failed`, exact counts) records them.
- **Known limits.** A resume hours after the interruption mixes an older snapshot of pages ≤ k with a newer one
  of the tail; for offset-paged sources an upstream deletion in between can shift one record across the page
  boundary (a gap, never a false disappearance) — the next window's fresh run re-reads every page. A
  re-processed capture is attributed to the resuming execution's run.
- **Storage.** One mark pair per target per execution (OSM: 316 rows a month) and one OCFL object per capture
  digest; unchanged pages re-add a version (a new inventory, no new content). OSM's 158 pages are a few hundred
  MB at most in the private bucket. Two jobs capturing identical bytes at the same moment may race an OCFL
  inventory write; the bytes stay addressable by digest.
- **Rolled on 2026-09-25:** 76 jobs (the probe, 62 per-source jobs, 8 batches, `sig-materialize`,
  `sig-export`, `sig-sink-bench`, `okc-doc-egress-probe`, `sig-ingest-resume-test`), first onto
  `sha256:f00c6daf…`, then onto the final `sha256:feff986c…` (each with `SIG_CODE_COMMIT` = its digest); the
  per-job before/after digests are in `docs/build/runs/P31.4.md`. `:latest` was not moved. The scheduled probe
  now sweeps `sig-api-health` (D-P31.1-2).

## Alternatives considered

- **Resume by reusing one `ingest_run` (an explicit `execution_id`).** ADR-109 allows it, but a restarted
  execution could then never record its own completion after a `failed` one (one live completion per run), and
  one run row would span two Cloud Run executions. Rejected.
- **Skip by content digest (re-fetch, then skip the walk if the digest matches).** It still re-fetches — the
  expensive, quota-bound part — and gives nothing on a fresh window. Rejected.
- **Resume across cadence windows.** A fresh window must re-fetch everything, or a disappearance could hide
  behind a stale page (§3.1). Rejected.
- **An object-store `BlobStore` over the GCS JSON API** instead of a gcsfuse mount. More code on the write
  path for the same result; the gcsfuse mount is the pattern `sig-export` already uses. Rejected for now.
- **Redeploying the jobs with `scheduled-ops.sh --apply`.** It re-creates every job from `cadence.toml` and
  would have reset hand-tuned settings. `roll-jobs` updates only the image and the capture store.

## Revisit trigger

- (a) The 2026-10-10 `sig-sched-camreg-batch-05` replay (the first full OSM run on this image) takes more than
  1 h, fails, or its run row's `fetches`/`resumed` show an unexpected resume. Compare with the projection above
  and ADR-107.
- (b) A resumed execution ever records a different emitted count or capture-digest set than a fresh run over
  the same window, or a disappearance is found that a skipped target hid.
- (c) The restricted bucket's capture prefix grows past 5 GB, or gcsfuse write latency dominates a run. Then
  consider the JSON-API `BlobStore` or a dedicated evidence bucket (with Object Lock, ADR-015).
- (d) A job's configured image is ever found not to be a digest (a regression of Decision 6).
