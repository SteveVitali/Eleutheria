# ADR-081 — The real GCP deployment: Cloud SQL + Cloud Run (vs ADR-075's e2-micro DECISION path), and the three IaC gap-closures the live apply required

- **Status:** Accepted
- **Phase / ticket:** P24.1 re-run — GCP hosted deployment (DEPLOY.1 / GL-DEPLOY-01), `live_verification=true`, closing `D-DEPLOY.1-1` (real apply/deploy) under operator ADC (HG-12)
- **Date:** 2026-09-15
- **Related:** ADR-075 (the prepare-only IaC — this records the *executed* realization and departs from its e2-micro DECISION for the DB tier; ADR-075 body unedited, SIG-ENG-003), ADR-077 (Secret Manager by name — honoured), the `read_surface_grants` sqitch change, RISK-P0-07 (egress), SIG-STORE-003 (zero-cost posture — see the cost note), HG-12 (`D-ACCT.1-1`), HG-09 (secrets env/Secret-Manager only), Part VIII §42 (compartment separation), `docs/tickets/DEFERRALS.md` D-DEPLOY.1-1/D-ACCT.1-1; the defining standard.

## Context

ADR-075 wrote + validated the hosted IaC prepare-only and picked, as its DECISION, a single always-free `e2-micro` GCE running the `ops/docker-compose.yml` stack, with Cloud SQL kept as the documented alternative. When the operator provided real ADC and asked to deploy for real (Finish-line A: real data, **access-restricted**), executing the e2-micro path proved fragile: Cloud Run reaching a private GCE Postgres needs a Serverless VPC Access connector (~$9/mo — so the "free" path is not free), the connector was never wired in `provision.sh`, and bootstrapping PG+PostGIS+sqitch on a COS box via a startup script is blind-debugged over SSH.

Three further gaps surfaced only on a true apply (they were invisible locally because the compose `sig` user is a real superuser and the build never ran the IaC):

1. `ops/Dockerfile` copied only `api`/`db`/`ontology`, but the uv workspace root declares every member — `uv pip install ./api` needs the API's whole transitive workspace closure present.
2. The image had no runtime DSN: `sig-api serve` defaults to the in-memory demo store; serving the real spine needs `--dsn` (+ `--role`), and on Cloud Run the DSN must use the Cloud SQL unix socket with the password injected from Secret Manager.
3. `access_control` granted the read role SELECT on only five tables; the §37 read API also queries `entity_identifier` and the domain-entity / graph-annotation / L4 inference tables, so a non-superuser hosted API (SET ROLE `sig_read_public`) 500s with "permission denied".

## Decision

**Realize the hosted stack as Cloud SQL + Cloud Run** — the ADR-075 *documented alternative*, promoted to the executed decision because it is the reliable, standard GCP pattern and eliminates the connector/VM/startup-script fragility:

- **Postgres + PostGIS = Cloud SQL** (`sig-pg`, `POSTGRES_18`, `db-f1-micro`, `us-central1`). Cloud Run reaches it via the **native Cloud SQL connector** (`--add-cloudsql-instances`, unix socket `/cloudsql/<conn>`) — **no VPC connector, no VM, no startup script**. Managed automated backups replace the `pg_dump`→GCS drill for the DB tier.
- **Read API = Cloud Run** (`sig-api`, min-instances 0, managed TLS), the image built for `linux/amd64` and pushed to Artifact Registry. The PG password arrives from **Secret Manager** (`sig-pg-password`) as an injected env var; the container assembles the DSN at runtime and never stores it in config (HG-09). The API `SET ROLE`s to `sig_read_public` so RLS serves only tier-0.
- **Finish-line A posture = access-restricted:** Cloud Run is `--no-allow-unauthenticated`; the four GCS buckets are created **private** (public-read is held for Go-public, gated on HG-11 + counsel). Compartment separation (§42) is preserved by the bucket layout.
- **The three gap-closures land as code:** the Dockerfile copies all workspace members + assembles the DSN; the read grants become the `read_surface_grants` sqitch change (SELECT on the full read surface to `sig_read_public`/`sig_export`; the RESTRICTIVE tier ceilings still bind, append-only unaffected).

## Consequences

- A real, reproducible hosted stack: Cloud SQL spine (20-migration schema + `read_surface_grants`), Cloud Run API serving the real spine (search / dossier / contradiction verified, the 299-vs-190 contradiction preserved), restricted access. `D-DEPLOY.1-1` moves to PARTIAL — apply/deploy done; the **cloud restore drill** (managed-backup restore into a fresh instance) is the remaining half.
- **Cost is ~$9/mo** (`db-f1-micro`; Cloud Run ≈ $0 at idle) — a conscious departure from the strict zero-cost posture (SIG-STORE-003), justified by reliability and the fact that the e2-micro path needed a same-priced VPC connector anyway. The e2-micro DECISION (ADR-075) remains the documented zero-cost option for a future cost-down.
- ADR-075's `ops/gcp/*` scripts stay as the e2-micro path; the executed Cloud SQL path is captured in `docs/build/reports/GCP_DEPLOYMENT.md` (the runbook) and this ADR.

## Revisit trigger

Revisit if: the monthly cost matters enough to move the DB back to the always-free e2-micro (ADR-075) or to Cloud SQL's newer shared-core tiers; **or** Go-public is approved (HG-11 + counsel) and the buckets/Cloud Run must flip to public-read/unauthenticated with a DNS cutover and `v0.2.0`; **or** the cloud restore drill (`D-DEPLOY.1-1` remainder) is executed and this needs updating with its evidence.
