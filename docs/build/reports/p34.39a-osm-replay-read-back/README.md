# P34.39a — D-P31.4-1 read-back records (the 2026-10-10 OSM replay)

The 2026-10-10T03:35Z OSM monthly replay (`camreg_osm_surveillance` inside
`camreg-batch-05`, job `sig-ingest-camreg-batch-05`, trigger
`sig-sched-camreg-batch-05`, live project `zeta-medley-508121-u7`) is read back
by `sig-ops scheduled-readback` — read-only, clock-guarded (AR-4/AR-5 of
`docs/tickets/247_P34.39a__osm-replay-read-back.md`).

## Files

- `baseline-2026-10-07.json` — the pre-run baseline (D-P31.4-1's second
  bullet), captured 2026-10-07 with `--write-baseline`: the `pg_stat_user_tables`
  update/delete counters (all 0/0), per-source claim counts (credited through
  the evidence chain `claim → claim_evidence → evidence_capture →
  evidence_artifact.source_id` — `claim` carries no `source_id`, and the
  pre-P31.2 reuse-by-key runs fold several sources' executions into one
  `ingest_run`, so a run-level map mis-attributes them; see
  `claim_counts_method` in the file), `claim` total, the disk/memory points,
  a `/health` read, and the instance/scheduler summaries.
- `queued-2026-10-07.json` — the live guard run on 2026-10-07: the clock guard
  refused (exit 42 — queued, not failed) because the fire is in the future,
  the trigger has no `lastAttemptTime`, and no post-fire execution exists.
  This file is the record that the guard holds live, not just in fixtures.
- `readback-2026-10-10.json` — the post-fire read-back, captured
  2026-10-14T05:55Z on live-leg branch `r11/P34.39a-live-1` (exit 0).
  **Verdict `fail` → `deferral-row`** — eleven of thirteen criteria pass; the
  two recorded fails are tooling artifacts, not production failures:
  `member-run-rows` counts by configured id, and the four members P34.18/
  ADR-178 renamed (`camreg_und_018` → `camreg_nurnazihah`,
  `camreg_und_019` → `camreg_olsson`, `camreg_us_ny_001` →
  `camreg_nyc_jgrayson_ny`, `camreg_us_ny_002` → `camreg_nyc_weltia_ny`) each
  wrote exactly one `outcome: ok` run row under their deployed ids — all 17
  members ran; `sql-no-restart` read the uptime series' DELTA points as a
  gauge (every 60 s point reads 60 s — continuously up, no restart). The
  substantive record: execution `sig-ingest-camreg-batch-05-nm64j` succeeded
  in 766.3 s; OSM member `ok`, 158 fetches (no resumed), `claims_added`
  1,369,210, 557.9 s; `ingest_run_completion` `01a123ec…` `ok`
  (`claims_considered` 1,369,210 — a net +0 replay: `claims_duplicate`
  1,214,682, `claims_inserted` 0, per-source claim counts unchanged from
  baseline, disclosed: the pinned image predates P31.7 re-sightings); all 16
  claim-table `n_tup_upd`/`n_tup_del` still 0; `/health` 200 with 0 not-ok
  probes; memory peak 0.614 < 0.90; disk +24 MB < 1 GiB. The failure routed
  to `D-P34.39a-1` naming the operator decision; `D-P31.4-1` stays OPEN on it.

## The queued leg (runs after 2026-10-10T03:35Z + execution completion)

The leg ran once (2026-10-14, `r11/P34.39a-live-1`); the command below is the
re-read a `D-P34.39a-1` follow-up would use:

```sh
cloud-sql-proxy zeta-medley-508121-u7:us-central1:sig-pg --port 55433 &
SIG_PGPASS="$(gcloud secrets versions access latest --secret=sig-pg-password \
  --project=zeta-medley-508121-u7)"
SIG_GCP_PROJECT=zeta-medley-508121-u7 \
SIG_OPS_GCS_BUCKET=zeta-medley-508121-u7-sig-restricted \
sig-ops scheduled-readback --batch camreg-batch-05 --date 2026-10-10 \
  --dsn "postgresql://sig:${SIG_PGPASS}@127.0.0.1:55433/sig" \
  --api-url https://sig-api-e5ctyx36jq-uc.a.run.app \
  --baseline docs/build/reports/p34.39a-osm-replay-read-back/baseline-2026-10-07.json \
  --out docs/build/reports/p34.39a-osm-replay-read-back/readback-2026-10-10.json
```

Every call is a read: `gcloud … describe|list`, GCS object list/download, one
authenticated `GET /health`, Cloud Monitoring `timeSeries.list`, and a
read-only SQL session (`SET SESSION CHARACTERISTICS AS TRANSACTION READ ONLY`,
300 s statement timeout). It never re-executes, never cancels, never writes.

Exit codes: `0` the read-back ran (verdict in the report); `42` the leg is
still queued (clock guard); `2` usage. A `fail` verdict routes per the
contract + G1 §3.7: counter drift, claims far above the band or a disk jump
over 3 GB → `anomaly-stop-and-preserve` (clone PITR to T0, never UPDATE/DELETE);
over-1h-but-finished → `adr-107-111-revisit` (the ADR-107/ADR-111 revisit
trigger (a)); ≥36 h → `deferral-row:execution-timeout`; otherwise
`deferral-row` naming the operator decision (re-execute/cancel needs a go).
`not_evaluable` means evidence was missing — never a green.

Re-run prompt (verbatim, contract AR-4):
`implement-spec spec=docs/tickets/247_P34.39a__osm-replay-read-back.md live_verification=true`
