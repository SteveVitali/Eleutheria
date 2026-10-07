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

## The queued leg (runs after 2026-10-10T03:35Z + execution completion)

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
