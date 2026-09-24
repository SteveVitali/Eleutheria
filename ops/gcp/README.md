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
| `../Dockerfile` | the Cloud Run API image (built + pushed by `sig-ops deploy`) |

```bash
bash ops/gcp/provision.sh --check    # plan only, no ADC, no network, exit 0
bash ops/gcp/backup.sh   --check     # backup + restore-drill plan, no ADC, exit 0
# operator, with ADC + SIG_GCP_PROJECT exported:
bash ops/gcp/provision.sh --apply    # provisions for real (gate-pending here)
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
