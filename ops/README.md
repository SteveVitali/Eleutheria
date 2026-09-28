# `ops/` — SIG runtime composition (P21.4, ADR-066)

`sig-ops` stands the whole SIG system up as a **service**, not a test suite, on one
small machine (SIG-STORE-003, the zero-cost posture). It is the local-staging
default the P21.4 gate HG-12 accepts: a `docker compose` PG18+PostGIS claim spine
with the real `db/sqitch.plan` deployed on start, the read API served by `uvicorn`
over that spine, and a static server for `web/dist`.

The composition itself has **no cloud-specific config**: the same command runs on a
laptop and on a single VM. The API and the static server run as **host processes**
(the HG-12 default: `uvicorn` + a static file server) so they execute the host's
Python/Node toolchain at HEAD without baking a platform-specific image; only the
stateful DB is a container. The **hosted** home is separate: `ops/gcp/` carries the
GCP infra-as-code (ADR-075) that was applied under operator ADC on 2026-09-15 as
Cloud SQL + Cloud Run (ADR-081) — the executed runbook is
[`docs/build/reports/GCP_DEPLOYMENT.md`](../docs/build/reports/GCP_DEPLOYMENT.md).

## Commands

```bash
uv run sig-ops up   --jurisdiction okc [--seed] [--no-static]  # bring it all up
uv run sig-ops seed --jurisdiction okc                          # load OKC slice claims
uv run sig-ops status                                           # PG / API / static health
uv run sig-ops down                                             # stop everything, remove containers
```

- **`up`** starts PG (waiting until `pg_isready`), runs the one-shot `sqitch deploy`
  (idempotent), then launches `sig-api serve --dsn <staging>` and a static server
  for `web/dist`. Use `--no-static` before the web build exists; `--seed` also loads
  the OKC slice. Exits non-zero if any service fails to answer.
- **`status`** reports each of PG / API / static as `healthy` or `DOWN` and exits
  non-zero if any is down.
- **`down`** SIGTERMs the API + static host processes and runs `docker compose down
  -v`, leaving **no containers** and no stray processes.
- **`seed --jurisdiction okc`** loads the committed Oklahoma City slice into the
  spine append-only via `db.claim_sink.PgClaimSink` — above all the 299-vs-190
  `claimed_device_count` contradiction (§3.1). It is *not* a live fetch (no green
  sources; HG-03 skipped): re-running is idempotent (content-digest ON CONFLICT).

## Staging endpoints (HG-12: local staging is acceptable)

All default to local and are overridable by env:

| env | default | meaning |
|---|---|---|
| `SIG_STAGING_DSN` | `postgresql://sig:sig@127.0.0.1:5432/sig` | the claim spine |
| `SIG_STAGING_API_URL` | `http://127.0.0.1:8000` | the read API |
| `SIG_STAGING_STATIC_URL` | `http://127.0.0.1:4321` | the static site |

Compose knobs: `SIG_PG_USER`/`SIG_PG_PASSWORD`/`SIG_PG_DB`/`SIG_PG_PORT`;
`SIG_API_PORT`; `SIG_STATIC_PORT`.

## The full first-jurisdiction run

`docs/build/tools/run_okc.sh` drives the whole staging path end to end (up → shadow
connector runs → resolution → reconcile → export → web build from the export →
acceptance queries against the running API → status). See `RISK-P21-06/07` for the
export-freshness and pre-gate-exposure risks, and `docs/build/reports/FIRST_JURISDICTION_REPORT.md`
for the run's output.

## Observability & alerting (OBS.1 / GL-OBS-01, ADR-077)

Zero-cost posture: a **file**, not a hosted metrics stack. The recorded-alert
ledger (`.sig/ops/alerts.jsonl`, env `SIG_ALERT_LOG`) is always on — every alert is
*recorded* before any external delivery is attempted. The optional webhook notifier
is env-only (`SIG_ALERT_WEBHOOK_URL` / `SIG_ALERT_WEBHOOK_TOKEN`, HG-09); absent,
alerts degrade to the ledger + a `SIG-ALERT` log line.

```bash
uv run sig-ops egress-report --alert [--usage-gb N]   # INFRA.1's alarm → recorded alert on breach
uv run sig-ops keepalive-check                        # verify the dormant-scheduler keepalive
uv run sig-ops probe [--alert]                        # record ok/latency metrics; alert on DOWN
uv run sig-ops alerts [--prune] [--limit N]           # read the recorded-alert ledger
uv run sig-ops dashboard [--out FILE] [--verify-keepalive]  # render the readout
```

- **`probe`** appends one JSONL row per service (pg/api/curation/static) to the
  bounded probe log (`SIG_PROBE_LOG`); both logs are held to the `[observability]`
  retention policy in `ops/config.toml` (age + byte caps, oldest first).
- **`dashboard`** renders the markdown readout — service health, uptime vs error
  budget (rolling `window_days`, `uptime_target_pct`), the egress level, the
  keepalive verification, and the recorded alerts. Committed example:
  `docs/build/reports/observability-dashboard.md`.
- `.github/workflows/observability.yml` runs this daily; `keepalive.yml` fires a
  recorded alert on failure. Secrets ride env only — every emitted surface is
  scrubbed of env-secret values (`ops.alerts.scrub_secrets`).

## Hosted operations, deploy, and the public surface

Beyond the local verbs above, `sig-ops` carries the hosted-ops and Round-10
verification surface (`uv run sig-ops --help` for the exact flags):

| verb family | what it does | posture |
|---|---|---|
| `deploy`, `backup-drill`, `roll-jobs`, `probe-hosted`, `probe-history`, `cadence`, `scheduled-ingest`, `replay-ingest`, `backfill-run-completions`, `sink-bench` | GCP deploy/restore/roll, hosted probe sweeps → WORM `ops/probes/`, the scheduled live-ingest audit trail → `ops/runs/` (`ops/cadence.toml`) | credentialed/hosted — operator ADC + gates |
| `evidence-audit`, `recovery-plan`, `recovery-apply`, `recovery-freeze`, `recovery-fixture-seed` | the offline read-only legacy-evidence audit + bounded, dry-run-by-default recovery (ADR-125/141) | offline; `--apply` required to write |
| `release-candidate`, `release-serve`, `release-publish`, `journey-verify`, `journey-intake`, `composed-verify` | the provisional-ruleset candidate build, the staging release-serving barrier, the staging publish+rollback rehearsal, the journey portfolio, and the composed Round-10 verification (ADR-132/142/143/144) | **offline/staging only** — no production serve; GATE-G3 owns publish |
| `dossier-packet`, `dossier-packet-tulsa`, `dossier-packet-san-diego`, `seed-correct` | the reviewed three-dossier evidence sets + the authored OKC seed-correction packet (ADR-137/138/139) | offline fixture replay; `review.status=not_run` |
| `swh-save`, `egress-report`, `degraded`, `keepalive-check`, `probe`, `alerts`/`alert`, `dashboard` | Software Heritage save request, egress budget, degraded static posture, observability | mixed — see each verb's help |

## Go-public cut-over — executed (2026-09-16/24/27)

Recorded, not deferred: the GCP deploy ran under operator ADC (`GCP_DEPLOYMENT.md`,
ADR-081), HG-01 held at its interim posture and HG-11 was granted 2026-09-27, and
the national publish serves at `https://surveillancegraph.org` (`LAUNCH_RECORD_2026-09-24.md`,
`REPUBLISH_LIVE_2026-09-27.md`). Still owed: counsel review of the publication-scope
analyses (`D-LEGAL.1-1`), the Round-10 production release exposure
(`D-R10-PUBLISH-1` + upstream `D-R10-LIVE-1`/`D-P32.23a-1`), and the
`docs/build/reports/PUBLICATION_CHECKLIST.md` items attached to each.
