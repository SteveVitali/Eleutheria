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
| `protect.sh` | P34.3 (SIG-OPS-002, SIG-STORE-048): the five pre-authorised data-protection mutations — `sig-pg` deletion protection + retain-backups-on-delete, SUN 09:00Z maintenance window, 40 GB autoresize cap; versioning + noncurrent lifecycle on `sig-restricted` (90 d) / `sig-public` / `sig-web` (30 d); `allUsers` off `sig-web`. Idempotent (live-read → SKIP), window-gated (never 03:00–10:00Z; `sig-pg` legs also never inside AR-3 or while `sig-materialize` runs), AR-2 backup first, per-action rollback on the stop rules. `--verify [--from-state DIR]` is the read-only outcome diff |
| `alerts.sh` | P34.4 (QA-3/QA-4/QA-5, QA-8 disable): the alert-set legs — create the TLS-expiry (21 d) + `SIG-ALERT` log-match policies, re-roll `sig-probe` onto the HEAD-built image (targets baked from `../cadence.toml`), extend the failed-job policy to `sig-probe` after its green sweep, disable `reingest.yml`. The alert set lives as committed REST-shape defs in `../monitoring/` (ADR-192); `--verify [--from-state DIR]` diffs them against live (`sig-ops monitoring-defs verify`). Same window guard as `protect.sh` |
| `public-gate.sh` | P34.21b leg L1 (queued — see the runbook section below): remove anonymous read/list on the `sig-public` 09-27 tree, keeping only the derived fetch targets + the tombstone note conditioned-in. Dry-run by default; `--apply` needs the verbatim A-0.2 go (`SIG_PUBLIC_GATE_GO`), the saved+sha256-verified pre-state, `live:P34.3` (versioning+UBLA on), and the open window. Never deletes an object (SIG-OPS-004) — rollback is `set-iam-policy` with the saved JSON |
| `iam-service-accounts.sh` | P34.42a (G1-01/F-272, SIG-SEC-007, AR-8): the three Cloud Run services off the project-Editor default compute identity. The committed declaration `../iam_identities.toml` (`sig.iam-identities/1`, rendered/diffed by `sig-ops iam`) names the three runtime SAs, their bindings, the 11-secret consumer matrix and the `sig-alerts` invoker change. Legs: `prestate` (the IAM restore point + route baseline) · `identities` · `bindings` · `revisions` (one same-image `--service-account` revision each) · `invoker` (grant the caller, revoke `allUsers`) · `verify`/`analysis` (`sig-ops iam diff` + same-image gate + policy-troubleshooter, read-only) · `rollback` (the recorded prestate). Windowed (≥ the contract earliest, never 03:00–06:30Z; exit 42 queued), ADC-gated `--apply`; `--verify [--from-state DIR]` is the read-only diff |
| `iam-job-identities.sh` | P34.42b (G1-01/F-272, SIG-SEC-007): every one of the 88 Cloud Run jobs off the project-Editor default compute identity + `roles/editor` removed from it. The declaration's `[[job_class]]` map (`sig-ops iam plan --leg jobs`) resolves every job to a class identity — `sig-ingest-rt` / `sig-probe-rt` / `sig-export-rt` / `sig-materialize-rt` — with per-class least-privilege grants (the ingest class's one conditioned `objectUser` is scoped to `objects/evidence/captures/` only — ADR-201; no bucket-wide delete, SIG-STORE-048) and the reserved identities (`sig-scheduler` + P34.44b/P35.53/P36.43's SAs) created grant-less. Legs: `prestate` (the IAM restore point + the 88-job re-count — a count/coverage disagreement refuses) · `identities` · `bindings` (grants + the `jobs_revoke` secret removals) · `jobs` (88 same-image `--service-account` updates; fail-closed "no job of the class running" guard) · `invokers` (`sig-scheduler` on the 79 scheduled triggers + the `sig-alerts` jobs-posture rule) · `editor` (the `roles/editor` removal — LAST, refused while anything still runs as it) · `verify`/`analysis` (`sig-ops iam diff --leg jobs` + the same-image gate + policy-troubleshooter incl. the off-prefix delete probe, read-only) · `rollback` (the recorded prestate, never a blind revert). Same OM-19 window as the services leg (exit 42 queued); `--verify [--from-state DIR]` is the read-only diff |
| `../Dockerfile` | the Cloud Run API + export image (built + pushed by `sig-ops deploy` / `export.sh`) — also carries `sig-ops` for the scheduled jobs and the pinned tippecanoe the tile renderer uses |
| `../web/Dockerfile` | the `sig-web` image: `nginx:1.27.5-alpine` + `ngx_http_brotli_*` compiled from sha256-verified sources against the exact nginx version (Alpine's packaged module is ABI-incompatible) + the repo-owned `../web/nginx.conf` |

```bash
bash ops/gcp/provision.sh --check    # plan only, no ADC, no network, exit 0
bash ops/gcp/backup.sh   --check     # backup + restore-drill plan, no ADC, exit 0
bash ops/gcp/scheduled-ops.sh --check # scheduled-ops plan (probe + ingest triggers)
bash ops/gcp/protect.sh   --check    # P34.3 data-protection plan; --verify diffs live state
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

> **Update 2026-09-28 (P33.7 docs refresh — appended, the section above kept as the P24.1
> authoring record).** The gated apply has since executed: the operator's ADC ran the
> deployment on 2026-09-15 under **ADR-081**, which promoted the documented **Cloud SQL +
> Cloud Run alternative** (~$9/mo — a conscious departure from the e2-micro zero-cost
> posture above). The executed runbook is
> `docs/build/reports/GCP_DEPLOYMENT.md` (provision, secrets, deploy, the real Cloud SQL
> restore drill — `D-DEPLOY.1-1` DONE 2026-09-15); scheduled live ops applied 2026-09-16;
> go-public executed 2026-09-16 (`docs/build/reports/PUBLICATION_CHECKLIST.md`), domain
> cut-over + TLS 2026-09-23, national publish 2026-09-24 (`LAUNCH_RECORD_2026-09-24.md`),
> republish 2026-09-27 (`REPUBLISH_LIVE_2026-09-27.md`) — the public surface serves at
> `https://surveillancegraph.org`.

## P34.21b — the attribution re-export + republish #2 legs (QUEUED, not run)

> **Appended 2026-10-03 (P34.21b).** The two production legs below are
> **engineered, tested, and queued** — each needs its own verbatim operator go
> and they were **not executed** by the P34.21b build. See the ticket
> (`docs/tickets/224_P34.21b__attribution-re-export-and-republish-2.md`) and the
> run ledger (`docs/build/runs/P34.21b.md`); the queued legs are
> `D-P34.21b-1` / `D-P34.21b-2` in `docs/tickets/DEFERRALS.md`.

### L1 — remove anonymous read/list on the sig-public 09-27 tree (`public-gate.sh`)

**Why:** the 2026-09-27 published tree carries the E2-12 misattribution; the
public fetch surface stays up through prefix-scoped IAM conditions, everything
else loses anonymous read/list, and a tombstone note object says why
(SIG-OPS-004 — nothing is deleted).

**Prerequisites (all, before `--apply`):**

- the operator's verbatim A-0.2 go for L1 (the "No, wait for P34.21" answer is
  the scope decision, not the go) exported as `SIG_PUBLIC_GATE_GO`;
- `live:P34.3` — `sig-public` versioning + uniform bucket-level access on (the
  saved `describe` must prove it — the script refuses otherwise);
- outside the daily 03:00–10:00Z band (`SIG_PUBLIC_GATE_NOW` is the test seam);
- a **committed read-only listing** of the tree first (the `list` action prints
  the prefix summary of the capture below);
- ADC: `gcloud auth application-default login` + `SIG_GCP_PROJECT`.

**Procedure:**

```bash
# 1. read-only pre-state (describe + get-iam-policy + full listing, sha256 each)
bash ops/gcp/public-gate.sh --apply prestate          # writes an evidence dir

# 2. read the capture: prefix summary + the derived fetch-target exclusions
bash ops/gcp/public-gate.sh list --prestate <dir>
bash ops/gcp/public-gate.sh prefixes --prestate <dir>  # + --fetch-targets FILE
                                                        # + --exclude <prefix>

# 3. the exact diff — unconditional anon → conditioned legacyObjectReader keeps
bash ops/gcp/public-gate.sh plan --prestate <dir>      # prints the rollback line

# 4. the gated apply (window + live:P34.3 + verbatim go + saved pre-state)
SIG_PUBLIC_GATE_GO="<the operator's recorded words>" \
  bash ops/gcp/public-gate.sh --apply apply --prestate <dir> [--tombstone-id TB-01]

# 5. the read-only outcome check (live, or --from-state <dir> offline)
bash ops/gcp/public-gate.sh --verify
```

The exclusion set derives from `ops/cadence.toml`'s sig-public probe targets
(`LICENCES.json`, `manifest.json`, the compartment `sites.csv`), any
`--fetch-targets`/`--exclude` additions, and the `tombstones/` prefix itself —
each line records its `# reason=`. Anonymous **list** cannot be conditioned per
prefix on a bucket-level access mode (a list call's resource is the bucket
itself), so anonymous list is removed wholesale; the kept **GET** access rides
a `p34-21b-live-prefixes` IAM condition on `roles/storage.legacyObjectReader`.

**Rollback:** `gcloud storage buckets set-iam-policy gs://<bucket> <saved iam JSON>`
— printed beside every plan. The tombstone object is additive; removing it is a
separate operator call, never this script's.

**Tombstone text:** default is the N-6 notice string ("This page has been
removed while a correction is made." — the notice-allowance); `--tombstone-id
TB-01` ships the batch-02 sentence instead, but only while its row reads
`confirmed` (B-2 — an agent never types the sentence it ships).

### L2 — the re-export + republish #2

**Prerequisites (all, before the leg):**

- `live:P34.21a` — the hosted attribution backfill applied
  (`D-P34.21a-1` closed with evidence);
- `live:P34.18` — the hosted source-id rename applied (`D-P34.18-L2` closed);
- copy batch #2 rows for the sentences the republish ships are **confirmed**
  (SL-20; TB-01 if it rides) — pending rows refuse `publish-web --apply`;
- a **`sig-ops republish-probe` record no older than 24 h** with no failed leg:
  `sig-ops republish-probe --export-dir <export> --public-dir <public root>
  --bucket-listing <capture> --tile-url <pmtiles> --out probe.json`;
- the operator's verbatim republish go; outside 03:00–10:00Z.

**Order (append-only — prior prefixes and release trees are never deleted):**

1. `SIG_EXPORT_AS_OF=<new stamp> bash ops/gcp/export.sh --apply run` — writes a
   **new** `exports/national/<as-of>/` prefix on sig-restricted; prior prefixes
   are never touched (the script carries no delete path — pinned by
   `tests/ops/test_p34_21b_export_legs.py`).
2. `bash ops/gcp/export.sh --apply fetch` — pull the new prefix to
   `exports/out/national`.
3. `sig-ops publish-web --export-dir exports/out/national --apply` — the one
   repository-owned publish path: export-mode site build, partition + clean
   proof, copy-batch + attribution gates, the public sync that **never deletes
   release trees**, then the post-sync absence probes.
4. Retain every prior release tree (the publish never deletes; versioning +
   noncurrent lifecycle keep older generations recoverable).
5. Verify: the probe set from step-4 of the runbook above re-run against live,
   plus `sig-ops republish-probe` for the record; rollback rides bucket
   versioning/prior generations — never a delete.

**Rerun prompt for both legs:**

```
implement-spec spec=docs/tickets/224_P34.21b__attribution-re-export-and-republish-2.md live_verification=true
```
