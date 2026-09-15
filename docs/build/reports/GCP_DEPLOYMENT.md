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

## Remaining (owed, not this ticket)

Zenodo/SWH deposits (HG-07, `D-P21.5-1`); real live source fetches (the placeholder
target-URL plumbing, `D-P21.3-1`/`D-LIVE.1a-1`); Go-public flip (HG-11 + counsel).
