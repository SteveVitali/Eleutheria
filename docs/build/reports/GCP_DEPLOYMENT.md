<!--
  docs/build/reports/GCP_DEPLOYMENT.md — the EXECUTED GCP deployment runbook
  (P24.1 re-run / DEPLOY.1 / GL-DEPLOY-01, live_verification=true, ADR-081).
  This records the real Cloud SQL + Cloud Run realization actually applied under
  operator ADC on 2026-09-15. NO secret value appears here (HG-09): the project id
  is public (an operator-owned account), passwords live only in Secret Manager.
-->
# SIG on GCP — executed deployment runbook (Finish-line A: real data, access-restricted)

Realizes the hosted stack as **Cloud SQL + Cloud Run** (ADR-081 — the ADR-075
documented alternative, promoted because Cloud Run→e2-micro needs a same-priced
VPC connector and COS bootstrap is fragile). Project `eleutheria`
(`$SIG_GCP_PROJECT`), region `us-central1`. Cost ≈ **$9/mo** (`db-f1-micro`;
Cloud Run ≈ $0 idle) — a conscious departure from the zero-cost posture (SIG-STORE-003).

## Prerequisites (operator)

```bash
gcloud auth application-default login           # ADC (HG-12)
export SIG_GCP_PROJECT=<project-id>             # eleutheria; billing enabled
gcloud services enable compute.googleapis.com storage.googleapis.com \
  secretmanager.googleapis.com artifactregistry.googleapis.com \
  run.googleapis.com sqladmin.googleapis.com --project "$SIG_GCP_PROJECT"
```

## 1. Secrets + Artifact Registry

```bash
gcloud secrets create sig-pg-password --replication-policy=automatic --project "$SIG_GCP_PROJECT"
gcloud secrets create sig-api-env      --replication-policy=automatic --project "$SIG_GCP_PROJECT"
openssl rand -base64 30 | tr -d '\n' | \
  gcloud secrets versions add sig-pg-password --data-file=- --project "$SIG_GCP_PROJECT"   # never echoed
gcloud artifacts repositories create sig --repository-format=docker \
  --location=us-central1 --project "$SIG_GCP_PROJECT"
```

## 2. Build + push the API image (linux/amd64)

The `ops/Dockerfile` copies the whole uv workspace (the API's transitive closure)
and assembles the PgReadStore DSN at runtime from Secret Manager parts.

```bash
gcloud auth configure-docker us-central1-docker.pkg.dev --quiet
docker buildx build --platform linux/amd64 \
  -t us-central1-docker.pkg.dev/$SIG_GCP_PROJECT/sig/sig-api:latest \
  -f ops/Dockerfile . --push
```

## 3. Cloud SQL (PostgreSQL 18 + PostGIS)

```bash
PGPW=$(gcloud secrets versions access latest --secret=sig-pg-password --project "$SIG_GCP_PROJECT")
gcloud sql instances create sig-pg --database-version=POSTGRES_18 --edition=enterprise \
  --tier=db-f1-micro --region=us-central1 --storage-size=10GB --storage-type=SSD \
  --root-password="$PGPW" --project "$SIG_GCP_PROJECT"
gcloud sql users create sig     --instance=sig-pg --password="$PGPW" --project "$SIG_GCP_PROJECT"
gcloud sql databases create sig --instance=sig-pg --project "$SIG_GCP_PROJECT"
```

## 4. Schema + role grants (via the Cloud SQL Auth Proxy)

```bash
cloud-sql-proxy --port 5433 "$SIG_GCP_PROJECT:us-central1:sig-pg" &   # ADC-authed
# sqitch deploy (20 base changes + read_surface_grants) — sig owns the objects:
docker run --rm -e PGPASSWORD="$PGPW" -v "$PWD/db:/repo:ro" -w /repo sqitch/sqitch:latest \
  deploy "db:pg://sig@host.docker.internal:5433/sig?sslmode=disable"
# Grant the access_control group roles to the sig LOGIN role (deployment-specific;
# the sig user is NOT a superuser on Cloud SQL, so RLS + grants apply):
psql "...user=sig dbname=sig..." -c "GRANT sig_ingest TO sig; GRANT sig_read_public TO sig;"
```

`cloudsqlsuperuser` is granted to `sig` by Cloud SQL automatically (needed for
`CREATE EXTENSION postgis`). The `read_surface_grants` sqitch change grants SELECT
on the full §37 read surface to `sig_read_public`/`sig_export` (RLS tier ceilings
still bind).

## 5. Seed real data

```bash
export PGPASSWORD="$PGPW"
export SIG_STAGING_DSN="postgresql://sig@127.0.0.1:5433/sig?sslmode=disable"
uv run python -m ops seed --jurisdiction okc      # 5 claims, 1 entity
```

## 6. Deploy Cloud Run (restricted) wired to Cloud SQL

```bash
SA="$(gcloud projects describe $SIG_GCP_PROJECT --format='value(projectNumber)')-compute@developer.gserviceaccount.com"
gcloud secrets add-iam-policy-binding sig-pg-password --member="serviceAccount:$SA" \
  --role=roles/secretmanager.secretAccessor --project "$SIG_GCP_PROJECT"
gcloud projects add-iam-policy-binding "$SIG_GCP_PROJECT" --member="serviceAccount:$SA" \
  --role=roles/cloudsql.client

CONN="$SIG_GCP_PROJECT:us-central1:sig-pg"
gcloud run deploy sig-api \
  --image us-central1-docker.pkg.dev/$SIG_GCP_PROJECT/sig/sig-api:latest \
  --region us-central1 --min-instances=0 --max-instances=2 \
  --add-cloudsql-instances "$CONN" \
  --set-secrets="SIG_PG_PASSWORD=sig-pg-password:latest" \
  --set-env-vars="SIG_CLOUDSQL_CONNECTION=$CONN,SIG_API_ROLE=sig_read_public" \
  --no-allow-unauthenticated --port 8080 --project "$SIG_GCP_PROJECT"
```

## 7. Verify (authenticated proxy)

```bash
gcloud run services proxy sig-api --region us-central1 --port 8080 --project "$SIG_GCP_PROJECT" &
curl -s localhost:8080/v1/dossier/okc      # OKC sources + CC-BY/ODbL compartments
curl -s localhost:8080/v1/contradiction    # 299-vs-190 device-count contradiction, preserved
```

## Executed state (2026-09-15)

- Cloud SQL `sig-pg` RUNNABLE (connection `zeta-medley-508121-u7:us-central1:sig-pg`).
- Schema: 20 base sqitch changes + `read_surface_grants`.
- Data: OKC seed — 5 claims, 1 entity (incl. the 299-vs-190 contradiction).
- Cloud Run `sig-api` (revision serving), restricted; URL `https://sig-api-873541617837.us-central1.run.app`.
- API verified serving the real spine (`/`, `/terms`, `/v1/search`, `/v1/dossier/okc`, `/v1/contradiction`).

## Access-restricted → Go-public delta (deferred)

Finish-line A keeps everything private. Go-public (`v0.2.0`, `D-P21.4-3`) additionally
requires HG-11 (governance) + counsel (HG-02), then: flip the `sig-web`/`sig-public`
buckets to public-read, sync `web/dist` + the published export compartment, set
Cloud Run `--allow-unauthenticated`, and a DNS cutover.

## Cloud restore drill (`D-DEPLOY.1-1` DONE, 2026-09-15)

```bash
STAMP=$(date +%Y%m%dT%H%M%SZ)
gcloud sql export sql sig-pg "gs://$SIG_GCP_PROJECT-sig-backups/pg/sig-$STAMP.sql" --database=sig
gcloud sql databases create sig_restore --instance=sig-pg
gcloud sql import sql sig-pg "gs://$SIG_GCP_PROJECT-sig-backups/pg/sig-$STAMP.sql" --database=sig_restore
# assert counts reproduce, then drop the drill db:
#   sig_restore: claims=5 entities=3 evidence=5  (== source sig)
gcloud sql databases delete sig_restore --instance=sig-pg
```

**Finding (fixed):** the first drill aborted — the `read_surface_grants` migration's
`ALTER DEFAULT PRIVILEGES` clauses cannot be re-applied by the Cloud SQL import user
("permission denied to change default privileges"), which rolls back the whole
import. Removed those clauses (explicit `GRANT ON ALL TABLES` retained); re-export +
re-import then reproduced counts exactly. Keep the schema free of
`ALTER DEFAULT PRIVILEGES` for restorability (ADR-081).

## Data + published artifacts (2026-09-15)

- **Seeded** jurisdictions into the hosted spine: `okc` (5 claims / 3 entities) +
  `france` (11 claims / 4 entities) via `sig-ops seed --jurisdiction <j>`.
- **Exports** built (`sig-exports build --jurisdiction {okc,france} --out exports/out/<j>`) —
  compartments `sig_graph` (CC-BY) / `osm_physical` (ODbL) / `web` — pushed to
  `gs://…-sig-public/{okc,france}/` (private under Finish-line A).
- **Static site** (50 pages, `SIG_DATA_SOURCE=export`) synced to `gs://…-sig-web` (private).

## 8. Scheduled live operations (P26.1 / OPS.2 — applied 2026-09-16)

Everything below is realised by `ops/gcp/scheduled-ops.sh` (`--check` = plan-only,
`--apply` = operator ADC). The per-source table is data — `ops/cadence.toml`;
`sig-ops cadence --check` fails on drift between it and the green/live-target set.

### Probe sweep (uptime accumulation)

| piece | value |
|---|---|
| Cloud Run job | `sig-probe` — `sig-ops probe-hosted --alert` (same `sig-api` image) |
| Scheduler trigger | `sig-sched-probe` — `0 */6 * * *` (every 6h, Etc/UTC) |
| Targets | `sig-api` `/` + `/v1/coverage/okc`, `sig-web` `/`, `sig-public` okc + france manifests, Cloud SQL reachability (`/cloudsql` socket) |
| Durable record | `gs://…-sig-restricted/ops/probes/<YYYY-MM-DD>/<ts>.jsonl` — one new object per sweep (WORM, never read-modify-write) |
| Read path | `sig-ops probe-history` (`SIG_OPS_GCS_BUCKET=…-sig-restricted`) → per-target count / latest state / last-N p95 |
| Failure path | any DOWN target fires a recorded alert through `sig-alerts` (`SIG-ALERT-RECEIVED` in Cloud Logging); job exits non-zero |

### Scheduled reingestion

One `sig-ingest-<source>` Cloud Run job per green live-target source, each running
`sig-ops scheduled-ingest --source <id> --sink pg` — the same gated
`connectors.runner` path a manual run takes (a non-green source is refused before
any socket; refusals/drift/disappearances are recorded, never retried —
`--max-retries 0`). Every execution appends one run row:

`gs://…-sig-restricted/ops/runs/<source>/<YYYY-MM-DD>/<ts>.json`
— source, mode, outcome (`ok`/`gate_refused`/`no_live_targets`/`content_drift`/
`politeness_refusal`/`error`), claims added, capture digests, refusal reason, and
the embedded fetch record a manual run leaves.

| source | cadence | cron (Etc/UTC) | job | scheduler |
|---|---|---|---|---|
| osm_overpass | weekly | `12 4 * * 1` | `sig-ingest-osm-overpass` | `sig-sched-osm-overpass` |
| decp_fr | weekly | `12 4 * * 2` | `sig-ingest-decp-fr` | `sig-sched-decp-fr` |
| raa_prefectures | weekly | `12 4 * * 3` | `sig-ingest-raa-prefectures` | `sig-sched-raa-prefectures` |
| muckrock | monthly | `0 6 1 * *` | `sig-ingest-muckrock` | `sig-sched-muckrock` (P25.7 — verified, not recreated; job upserted to the run-row wrapper, `sig-muckrock-refresh` binding preserved) |
| eff_atlas_of_surveillance | monthly | `0 5 2 * *` | `sig-ingest-eff-atlas` | `sig-sched-eff-atlas` |
| usaspending | monthly | `0 5 3 * *` | `sig-ingest-usaspending` | `sig-sched-usaspending` |
| eff_data_driven | monthly | `0 5 4 * *` | `sig-ingest-eff-data-driven` | `sig-sched-eff-data-driven` |
| osm_element_history | monthly | `0 5 5 * *` | `sig-ingest-osm-element-history` | `sig-sched-osm-element-history` |
| madada | monthly | `0 5 7 * *` | `sig-ingest-madada` | `sig-sched-madada` |
| ccops_seattle | monthly | `0 5 8 * *` | `sig-ingest-ccops-seattle` | `sig-sched-ccops-seattle` |
| ccops_nyc_post | monthly | `0 5 9 * *` | `sig-ingest-ccops-nyc-post` | `sig-sched-ccops-nyc-post` |
| ccops_sf | monthly | `0 5 10 * *` | `sig-ingest-ccops-sf` | `sig-sched-ccops-sf` |
| pathways_rtcc_federation | monthly | `0 5 11 * *` | `sig-ingest-pathways-rtcc` | `sig-sched-pathways-rtcc` |
| pathways_fr_css_forensics | monthly | `0 5 12 * *` | `sig-ingest-pathways-fr-css` | `sig-sched-pathways-fr-css` |
| pathways_acoustic_drone_location | monthly | `0 5 13 * *` | `sig-ingest-pathways-drones` | `sig-sched-pathways-drones` |
| carnegie_ai_gsi | monthly | `0 5 14 * *` | `sig-ingest-carnegie-ai-gsi` | `sig-sched-carnegie-ai-gsi` |
| facial_recognition_world_map | monthly | `0 5 15 * *` | `sig-ingest-frwm` | `sig-sched-frwm` |
| aspi_mapping_chinas_tech_giants | monthly | `0 5 16 * *` | `sig-ingest-aspi` | `sig-sched-aspi` |
| ok_statute | monthly | `0 5 17 * *` | `sig-ingest-ok-statute` | `sig-sched-ok-statute` |
| okcpd_policy | monthly | `0 5 18 * *` | `sig-ingest-okcpd-policy` | `sig-sched-okcpd-policy` |
| okc_procurement | monthly | `0 5 19 * *` | `sig-ingest-okc-procurement` | `sig-sched-okc-procurement` |

The 17 green sources WITHOUT live targets (agency_audit_export, gleif, the
OSM-ecosystem reference sources, …) get no trigger — there is nothing to fetch;
`live_targets.toml` is the fetchable set and `sig-ops cadence --check` enforces
the coverage.

### Pause / disable

```bash
# one trigger:
gcloud scheduler jobs pause sig-sched-probe \
  --location us-central1 --project "$SIG_GCP_PROJECT"
# every scheduled-ops trigger (resume = `jobs resume`):
for j in $(gcloud scheduler jobs list --location us-central1 \
    --project "$SIG_GCP_PROJECT" --format='value(name.basename())' | grep '^sig-sched-'); do
  gcloud scheduler jobs pause "$j" --location us-central1 --project "$SIG_GCP_PROJECT"
done
# full teardown of a job (the restricted-bucket objects already written stay):
gcloud scheduler jobs delete sig-sched-probe --location us-central1 --project "$SIG_GCP_PROJECT"
gcloud run jobs delete sig-probe --region us-central1 --project "$SIG_GCP_PROJECT"
```

### Read the ops records

```bash
gcloud storage ls "gs://$SIG_GCP_PROJECT-sig-restricted/ops/probes/**"
gcloud storage ls "gs://$SIG_GCP_PROJECT-sig-restricted/ops/runs/**"
SIG_OPS_GCS_BUCKET="$SIG_GCP_PROJECT-sig-restricted" sig-ops probe-history
```

## Remaining (owed, not this ticket)

Zenodo/SWH deposits (HG-07, `D-P21.5-1`); real live source fetches (the placeholder
target-URL plumbing, `D-P21.3-1`/`D-LIVE.1a-1`); Go-public flip (HG-11 + counsel).

## 9. `sig-api` roll by pinned digest + reconnect drill (P31.1 / HARDEN.1, 2026-09-24)

The first `sig-api` image since 2026-09-16 (operator-approved roll, LEDGER § GATE DECISIONS "Round 9
ratification" Q2; ADR-108). Built from `git archive HEAD` via Cloud Build, **SHA-tagged, never `:latest`**, deployed
by digest as a 0 % candidate, smoked on its tag URL, then promoted.

| | digest | revision | tag / commit |
|---|---|---|---|
| **serving (P31.1)** | `sha256:21bb952672a264714d4c31c7e2373cdb17b1572da4858e5004f2d29e03fbbfb4` | `sig-api-00008-qir` (100 %, 2026-09-24T19:27Z) | `sig-api:api-10025fbe1fd8` / `10025fb` |
| first P31.1 roll (superseded) | `sha256:a9ecaad6142d0c62c5498acfa3b8bbfcd80e764fdbb506a146406fd301d255d1` | `sig-api-00005-nem` (100 % 19:19–19:27Z) | `sig-api:api-fe0d4d344f7d` / `fe0d4d3` |
| **rollback** (the 2026-09-16 image) | `sha256:cc6801119e82a72767f03f5955a36419e22f202166fed7b4d9259a25aec7fac8` | `sig-api-00004-jdj` | untagged |
| `:latest` (unmoved) | `sha256:ebb6dab99fe689838ab1eb9ccc5fdea64ea5048f2622f4f0f110fa0d6fce487a` | — (still the scheduled jobs' image, P31.4 rolls them) | `latest` |

```bash
IMG="us-central1-docker.pkg.dev/$SIG_GCP_PROJECT/sig/sig-api"
# build (SHA tag) — the materialize.sh do_image pattern with tag api-<sha12>, then:
gcloud artifacts docker images describe "$IMG:api-<sha12>" --project "$SIG_GCP_PROJECT" \
  --format='value(image_summary.digest)'
# candidate at 0 % traffic, smoke it on its tag URL, then promote:
gcloud run services update sig-api --region us-central1 --project "$SIG_GCP_PROJECT" \
  --image "$IMG@sha256:<digest>" --no-traffic --tag <tag>
gcloud run services update-traffic sig-api --to-latest --remove-tags <tag> \
  --region us-central1 --project "$SIG_GCP_PROJECT"
# ROLLBACK (never a label-only update, which re-resolves :latest — ADR-107 §5):
gcloud run services update sig-api --region us-central1 --project "$SIG_GCP_PROJECT" \
  --image "$IMG@sha256:cc6801119e82a72767f03f5955a36419e22f202166fed7b4d9259a25aec7fac8"
```

- **Access (observed 2026-09-24):** the service IAM policy binds `allUsers` → `roles/run.invoker`, i.e. the API is
  publicly invokable (the §6 `--no-allow-unauthenticated` above describes the original Finish-line-A deploy).
- **Health:** `GET /health` (not `/healthz`: Cloud Run's front end answers `/healthz` itself with a 404) → 200 +
  pool counters, 503 when no pooled connection answers. `probe-hosted` target `sig-api-health`.
- **After a `sig-pg` restart** the API reconnects on its own (ADR-108); redeploying the serving digest (ADR-107 §5)
  is now only a fallback. Hosted proof of the served image's fast path is owed (D-P30.4-1, PARTIAL).
- **Reconnect drill (operator-approved only):** as `sig` over `cloud-sql-proxy`,
  `SELECT pid, pg_terminate_backend(pid) FROM pg_stat_activity WHERE application_name = 'sig-api' AND usename = 'sig'`
  (the store tags every connection `application_name = sig-api`; nothing else matches), then time the next
  DB-backed request. Drill of 2026-09-24T19:19:42Z and its result: `docs/build/runs/P31.1.md`.
- **Schema:** sqitch change `entity_identifier_value_trgm` (pg_trgm + GIN trigram index, built CONCURRENTLY) deployed
  with `ops/gcp/materialize.sh --apply schema` at 2026-09-24T19:12:58Z (17 MB).
