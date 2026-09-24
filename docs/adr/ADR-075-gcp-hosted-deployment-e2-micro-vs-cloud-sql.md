# ADR-075 — GCP hosted deployment: an e2-micro compose stack (vs Cloud SQL) + the validated-IaC design

- **Status:** Accepted
- **Phase / ticket:** P24.1 — Real hosted deployment on GCP + backups (DEPLOY.1, GL-DEPLOY-01)
- **Date:** 2026
- **Related:** ADR-066 (runtime composition, `sig-ops` + `ops/docker-compose.yml`), ADR-067
  (Zenodo deposits, object store/CDN, `.torrent`/mirrors, egress, degraded mode), ADR-015
  (evidence store on S3/CloudFront + Object Lock); SIG-STORE-003 (zero-cost posture),
  SIG-STORE-004/005 (no sole home), GL-DEPLOY-01, GL-GATE-04; HG-12 / `D-ACCT.1-1` /
  `D-DEPLOY.1-1`; RISK-P0-07 (egress), RISK-P21-05 (secrets env-only), go-live spec D3
  (public repo → no literal project id).

## Context

Through the go-live round SIG runs on **local staging** (`sig-ops up`, ADR-066): a
`docker compose` PG18+PostGIS claim spine, the read API under `uvicorn`, and a static
`web/dist` server. DEPLOY.1 (GL-DEPLOY-01) is the first ticket to give SIG a **real hosted
home** — the OKC dossier served from a public GCP URL, with automated backups and a tested
restore drill — on the operator's GCP project (`$SIG_GCP_PROJECT`, name `eleutheria`).

Two constraints shape every choice:

- **HG-12 / GL-GATE-04 pre-answers only the *host choice*** (GCP `$SIG_GCP_PROJECT`,
  zero/low-cost). It does **not** pre-authorize the `apply`: there are **no** Application
  Default Credentials (ADC) and **no** GCP account in this isolated context, and creds are
  `provided: no` (P23.4 / ACCT.1). So the IaC is **written + validated** here; the real
  `apply`/deploy and the real GCS/Cloud-SQL restore are **gate-pending** (`D-DEPLOY.1-1`,
  cross-ref `D-ACCT.1-1`). No `gcloud apply` is ever run by an isolated subagent; no
  deployed URL is fabricated.
- **SIG-STORE-003, the zero-cost posture, is binding.** The design must sit inside the GCP
  Always-Free tier where possible.

The ticket owns one decision explicitly: **Postgres+PostGIS on the smallest Cloud SQL tier
*or* a single `e2-micro` GCE running the compose stack — pick one, keep the other documented.**

`terraform` is not on PATH in this build, so a second, smaller decision follows: the IaC
**form**.

## Decision

**1. Postgres+PostGIS runs on a single always-free `e2-micro` GCE running the compose
stack** (`ops/docker-compose.yml`), **not** Cloud SQL. The `e2-micro` is in the GCP
**Always-Free** tier (1/month in `us-west1`/`us-central1`/`us-east1`), so it is **$0**; the
smallest Cloud SQL tier (`db-f1-micro`) is **~$9+/mo** with **no** free tier. Under a binding
zero-cost posture the free path wins. The **read API runs on Cloud Run** at **min-instances
0** (scales to zero → $0 idle) with the managed default TLS, reading secrets from **Secret
Manager**; the static site + the **published** export compartment serve from **public-read
GCS** buckets, with the non-published compartments + backups in **private** buckets.

**Cloud SQL + Cloud Run is kept fully documented** (in `provision.sh::provision_alternative`,
`backup.sh::backup_cloud_sql`, and `ops/gcp/README.md`) as the managed alternative — chosen
only when managed daily backups + PITR + HA justify the spend.

**2. The IaC form is idempotent `gcloud` shell scripts with a `--check`/dry-run validation
path** (`ops/gcp/{config,lib,provision,backup}.sh`), because `terraform` is not on PATH. The
`--check` path is the deterministic proxy for `terraform validate`/`plan`: it prints the
whole plan, uses **no ADC**, opens **no network**, and exits **0** (`lib.sh::run` prints in
check mode, executes only under `--apply`; `require_adc` refuses an apply without ADC — exit
3, never a fabricated deploy). If terraform is later adopted, the validation test
(`tests/ops/test_gcp_iac.py`) shells `terraform validate` when `terraform` + `*.tf` are
present, else the gcloud dry-run — so the guard follows whichever form is committed.

**3. The deploy path is `sig-ops deploy --target gcp`** (`ops/src/ops/deploy.py`): it builds
+ pushes the API image (Artifact Registry) and syncs `web/dist` + the exports to GCS. With
no ADC it runs in **dry-run / plan** mode (prints the ordered plan, exits 0, no network); the
real push/sync is the operator-gated RETURN PASS action.

**4. Backups = `pg_dump` (custom format) → a private GCS backup bucket + OCFL sync**, with
the **restore drill proven for real, locally, over Docker** (`ops/src/ops/backup.py`,
`sig-ops backup-drill`, `tests/db/test_restore_drill.py`): dump the live spine, restore into
a **fresh** database, assert the graph (claim / evidence / entity counts) reproduces. The
cloud restore (from GCS / Cloud SQL under ADC) is the gate-pending half.

**5. No secret and no literal project id in any file.** The project is `$SIG_GCP_PROJECT`
(env-resolved; this repo is public, go-live spec D3); secrets are **Secret Manager
references by name only** (HG-09 / RISK-P21-05). Tests assert both
(`tests/ops/test_gcp_iac.py`, `tests/connectors/test_secrets.py`).

## Consequences

- SIG has a **validated**, zero-cost GCP deployment design: `provision.sh --check` /
  `backup.sh --check` / `sig-ops deploy --target gcp --dry-run` all run green **without ADC**;
  the local restore drill passes for real over Docker. The real `apply`/deploy + cloud
  restore stay gate-pending (`D-DEPLOY.1-1`) — nothing is fabricated (§3.1).
- **Cost:** ≈ **$0/mo** within Always-Free (e2-micro + GCS + Cloud-Run-to-zero + Secret
  Manager); the one real risk is sustained egress (RISK-P0-07), watched by `sig-ops
  egress-report` and the zero-egress torrent/mirror path (ADR-067). Full table in
  `ops/gcp/README.md`.
- **Operational trade of choosing `e2-micro` over Cloud SQL:** backups + patching + restore
  are SIG's responsibility (hence the tested `pg_dump`/restore drill and the documented
  bucket-lifecycle retention), where Cloud SQL would manage them — accepted for $0.
- Additive/append-only/back-compat: `sig-ops` gains two verbs (`deploy`, `backup-drill`);
  no existing command, schema, or the frozen §47 layout changes (`ops/gcp/` is new config).

## Alternatives considered

- **Cloud SQL `db-f1-micro` + Cloud Run only** — rejected as the default: not free-tier
  (~$9+/mo) under a binding zero-cost posture; kept **documented** as the managed alternative.
- **A Terraform module** — deferred: `terraform` is not on PATH here, so a gcloud-script IaC
  with a no-ADC dry-run is the pragmatic, testable form; the validation test already accepts
  a future `.tf` set.
- **Recording the gate-pending `apply`/cloud-restore as "done"** — rejected: that fabricates
  green (§3.1); they are `DEFERRALS.md` rows with the validated-IaC + local-drill proxy.
- **Serving the whole site from the GCE box** — rejected: static bytes belong on public-read
  GCS behind the free tier; Cloud Run scales the API to zero. Cheaper and more survivable.

## Revisit trigger

Revisit this decision when any of the following holds:

- **Operator ADC arrives (HG-12 / `D-ACCT.1-1`).** When `gcloud auth application-default
  login` + `SIG_GCP_PROJECT` are exported in the run shell, run `bash ops/gcp/provision.sh
  --apply` and `sig-ops deploy --target gcp` for real, and perform the cloud restore drill
  (`D-DEPLOY.1-1`) — then revisit this ADR to confirm the e2-micro/GCS/Cloud-Run choices
  against real behaviour and cost.
- **The `e2-micro` outgrows a single box.** If the spine + API no longer fit one always-free
  `e2-micro` (more jurisdictions, heavier traffic), revisit the **Cloud SQL + Cloud Run**
  alternative (managed backups/HA) against the then-current budget.
- **The free tier changes or egress becomes a real cost (RISK-P0-07).** If GCP removes/reduces
  the Always-Free `e2-micro`/GCS/Cloud-Run allowances, or `sig-ops egress-report` alarms
  against a real bill, revisit the host + region + store choices.
- **Terraform is adopted.** If `terraform` becomes available on the deploy toolchain, revisit
  the IaC **form** (port the gcloud scripts to a Terraform module); the validation test already
  prefers `terraform validate` when `*.tf` are present.
- **A managed restore/PITR requirement appears.** If governance requires point-in-time
  recovery or managed backup SLAs, revisit toward Cloud SQL.
