<!--
  ops/gcp/README.md — SIG hosted deployment on GCP (P24.1 / DEPLOY.1 / GL-DEPLOY-01,
  ADR-075). Prepare-only: the IaC is written + validated here; the real `apply`/deploy
  is gate-pending on operator ADC (HG-12 / D-ACCT.1-1). No secret, no literal project
  id (this repo is public — the project is $SIG_GCP_PROJECT, go-live spec D3).
-->
# `ops/gcp/` — SIG's zero/low-cost GCP hosted home

Infra-as-code for a **real, zero/low-cost** hosted home on the operator's GCP project
(`$SIG_GCP_PROJECT`, name `eleutheria`, GL-GATE-04), so the OKC dossier serves from a
public GCP URL with automated backups and a tested restore drill. It is **written +
validated autonomously**; the real `apply` runs only under operator Application Default
Credentials (ADC) — see the gate note at the bottom.

## Form: idempotent `gcloud` scripts (ADR-075)

`terraform` is **not** on PATH in this build, so the IaC is a set of idempotent `gcloud`
shell scripts with a `--check`/dry-run validation path that runs to green **without ADC**
(the deterministic proxy for `terraform validate`/`plan`). If terraform is ever adopted,
the validation test (`tests/ops/test_gcp_iac.py`) shells `terraform validate` when
`terraform` + `*.tf` are present, else the gcloud dry-run.

| file | role |
|---|---|
| `config.sh` | parameters: `$SIG_GCP_PROJECT` / region / zone, bucket + service + secret **names** |
| `lib.sh` | the `--check` (plan-only, no ADC) vs `--apply` (ADC-gated) plumbing |
| `provision.sh` | enable APIs · GCS buckets · Artifact Registry · Secret Manager · compute |
| `backup.sh` | `pg_dump` → GCS backup bucket (+ OCFL sync) · restore drill · Cloud SQL alt |
| `schedule.sh` | P25.7: the `sig-sched-muckrock` recurring trigger (superseded-in-part by `scheduled-ops.sh`, which verifies rather than recreates it) |
| `scheduled-ops.sh` | P26.1: `sig-probe` (6-hourly hosted sweep → `ops/probes/` in the restricted bucket + alerts) + per-source `sig-ingest-<id>` jobs/`sig-sched-<id>` triggers from `../cadence.toml` (run rows → `ops/runs/`). P31.4 (ADR-111): deploys `SIG_JOB_IMAGE` **by pinned digest** (a `:latest` or untagged ref is refused) and mounts the restricted bucket as every ingest job's capture store (`SIG_CAPTURE_DIR`) |
| `materialize.sh` | P30.2: the hosted Round-6 materialization — `schema` (sqitch deploy as the schema owner, incl. the least-privilege `sig_materialize` role) · `image` (SHA-tagged Cloud Build, never `:latest`) · `job` (`sig-materialize` Cloud Run job next to Cloud SQL) · `run <step>` (resolution / edges / contradictions / coverage / accountability / detect, each `--role sig_materialize`, append-only + idempotent) — ADR-103 |
| `export.sh` | P30.3: the national `--from-spine` export Cloud Run job next to Cloud SQL (read-only snapshot; restricted bucket mount) — ADR-106 |
| `web.sh` | P31.15 (ADR-R9-TILES): the repo-owned `sig-web` image + service path — `image` (Cloud Build `../web/Dockerfile`: nginx + compiled Brotli + `../web/nginx.conf`) · `service` (the hand-made service spec read live, then upserted on the pinned digest with the `<project>-sig-web` gcsfuse mount → `/mnt/sig-web`) · `describe` (the live spec). The roll itself is P31.16's |
| `../Dockerfile` | the Cloud Run API + export image (built + pushed by `sig-ops deploy` / `export.sh`) — also carries `sig-ops` for the scheduled jobs and the pinned tippecanoe the tile renderer uses |
| `../web/Dockerfile` | the `sig-web` image: `nginx:1.27.5-alpine` + `ngx_http_brotli_*` compiled from sha256-verified sources against the exact nginx version (Alpine's packaged module is ABI-incompatible) + the repo-owned `../web/nginx.conf` |

```bash
bash ops/gcp/provision.sh --check    # plan only, no ADC, no network, exit 0
bash ops/gcp/backup.sh   --check     # backup + restore-drill plan, no ADC, exit 0
bash ops/gcp/scheduled-ops.sh --check # scheduled-ops plan (probe + ingest triggers)
# operator, with ADC + SIG_GCP_PROJECT exported:
bash ops/gcp/provision.sh --apply    # provisions for real (gate-pending here)
SIG_JOB_IMAGE=<sig-api:SHA-tag or @sha256 digest> bash ops/gcp/scheduled-ops.sh --apply
# roll NEW code onto the EXISTING jobs (image + capture store only; every other job
# setting, e.g. batch-05's 36 h timeout, is preserved; before/after digests recorded):
uv run sig-ops roll-jobs --image <SHA tag or digest> --record roll.json          # plan
uv run sig-ops roll-jobs --image <SHA tag or digest> --record roll.json --apply  # apply + verify
```

## The architecture (DECISION, ADR-075)

- **GCS buckets** — `…-sig-web` (static Astro site) and `…-sig-public` (the **published**
  compartment: exports + deposits + tiles) are **public-read**; `…-sig-restricted`
  (non-published compartments + mirrors) and `…-sig-backups` (pg_dump + OCFL) stay
  **PRIVATE**. Public-read is granted **only** on the published compartment (§42, Part VIII).
- **Cloud Run** serves the read API at **min-instances 0** (scales to zero → $0 when idle),
  with the **managed-cert / default TLS**. Secrets arrive from **Secret Manager** by name.
- **Postgres+PostGIS = a single always-free `e2-micro` GCE** running `ops/docker-compose.yml`
  (the DECISION). **Cloud SQL** (smallest `db-f1-micro` tier) is the documented alternative
  — see ADR-075 for the trade (managed backups vs the free tier).
- **Secret Manager** holds `sig-pg-password` / `sig-api-env` — created as **containers by
  name only**; the operator adds the versions out-of-band. No secret value is ever in this
  repo (HG-09).

## Backups + restore drill

- **Backup** (DECISION path): `pg_dump -Fc` on the GCE host → the PRIVATE `…-sig-backups`
  bucket, with the OCFL evidence store rsynced alongside; a bucket lifecycle rule keeps
  daily/monthly copies. (Cloud SQL alternative: managed daily backups + PITR.)
- **Restore drill**: proven **for real, locally, over Docker** —
  `uv run python -m ops backup-drill` (and `tests/db/test_restore_drill.py`) dumps the live
  compose PG, restores it into a **fresh** database, and asserts the graph (claim /
  evidence / entity counts) reproduces. The **cloud** restore (from GCS / Cloud SQL under
  ADC) is the gate-pending half (`D-DEPLOY.1-1`).

## The deploy path

`sig-ops deploy --target gcp` builds + pushes the API image (Artifact Registry) and syncs
`web/dist` + the exports to GCS. With **no ADC** it runs in **dry-run / plan** mode: it
prints the ordered plan and exits 0 without opening the network. The real push/sync is the
operator-gated RETURN PASS action.

```bash
sig-ops deploy --target gcp --dry-run    # prints the plan, exits 0, no network
```

## Cost note vs the GCP free tier (SIG-STORE-003, zero-cost posture)

Monthly cost of the **DECISION** design, against the GCP [Always Free] tier and the OKC
slice's tiny footprint:

| resource | free-tier allowance | SIG usage | monthly cost |
|---|---|---|---|
| **GCE `e2-micro`** (PG+PostGIS+API compose) | 1 `e2-micro`/mo in us-west1/us-central1/us-east1 | 1 `e2-micro` in `us-central1` | **$0** (within free tier) |
| **GCE boot disk** | 30 GB-months standard PD free | 30 GB | **$0** |
| **Cloud Storage** | 5 GB-months (us regions) + 1 GB/mo egress (NA) | ≪ 5 GB (static site + OKC export) | **$0** |
| **Cloud Run** (API, min-instances 0) | 2M requests + 360k GB-s + 180k vCPU-s /mo | scales to zero when idle; OKC traffic is tiny | **$0** |
| **Artifact Registry** | 0.5 GB free | one small API image | **~$0** |
| **Secret Manager** | 6 active versions + 10k access ops free | 2 secrets | **$0** |
| **Egress** | 1 GB/mo NA egress free (+ zero-egress torrent/mirror path, ADR-067) | small | **~$0** |
| **Total** | | | **≈ $0/mo** (within Always Free) |

Notes:
- The `e2-micro` free instance is **only** free in `us-west1` / `us-central1` / `us-east1`
  — `config.sh` defaults to `us-central1` for that reason.
- The **Cloud SQL alternative** is **not** free-tier: the smallest `db-f1-micro` is
  **~$9+/mo** plus storage — hence the DECISION favours the always-free `e2-micro` for the
  zero-cost posture. Choose Cloud SQL only when managed backups/HA justify the spend.
- Sustained heavy egress is the one real cost risk (RISK-P0-07); the zero-egress
  torrent/mirror path (ADR-067) and `sig-ops egress-report` keep it observed.

## Gate — no real apply here (HG-12 / D-ACCT.1-1)

This build **writes + validates** the IaC only. There are **no** ADC and **no** GCP account
in this isolated context, so the real `apply`/deploy and the real GCS/Cloud-SQL restore are
**gate-pending** (`docs/tickets/DEFERRALS.md` → `D-DEPLOY.1-1`, cross-ref `D-ACCT.1-1`). The
operator exports ADC (`gcloud auth application-default login`) + `SIG_GCP_PROJECT`, then
re-runs `bash ops/gcp/provision.sh --apply` and `sig-ops deploy --target gcp`.
