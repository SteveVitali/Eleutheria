# G1 — Ops risk register and hardening design

Row **G1** of `META_PLAN.md` (Stage P, wave 2). Research and design only. Every production read below was
`list`/`describe`/`get`/`logs read`/`cat`/HTTP `GET`. Nothing was patched, deployed, executed, deleted or synced
(P3). No secret value was read or copied (P14): secrets appear by **name** only. The billing account id and the
operator's e-mail are deliberately left out.

- **Written:** 2026-09-30, reads 16:40:17Z → 16:57:05Z (`date -u`). Planning HEAD at start `c7c773e8`.
- **Scope:** project `zeta-medley-508121-u7`, region `us-central1`, the live site `https://surveillancegraph.org`,
  GitHub Actions on `SteveVitali/Eleutheria`, and the repo at the chain tip (`b051732c`, byte-identical here).
- **Inputs read:** META_PLAN §3, the G1 row, Appendix A (F-01, F-02, F-08, F-11, F-12, F-13); `baseline/BASELINE.md`;
  `baseline/TRACK0_RECORD.md`; `findings/incoming/A1.csv` (NEW-2/3/4); `ops/src/ops/publish.py`;
  `ops/src/ops/cli.py`; `ops/src/ops/backup.py`; `ops/gcp/{README.md,web.sh,export.sh}`; `ops/cadence.toml`;
  `ops/README.md`; `ops/AGENTS.md`; `.github/workflows/{reingest,observability}.yml`;
  `docs/build/runs/P31.16.md`; `docs/build/reports/{REPUBLISH_LIVE_2026-09-27,GCP_DEPLOYMENT,INFRA_RUNBOOK,
  CORRECTIONS_TAKEDOWN_RUNBOOK,SUCCESSION,DEPOSITS}.md`; ADR-077 and ADR-111 (slices); DEFERRALS rows D-P31.4-1,
  D-P31.3-1 and D-P30.4-4; two LEDGER lines (grep `maproulette`).
- **Evidence classes (P1):** `live-read` (gcloud, gh, curl output), `code` (file:line), `recorded-execution`
  (repo run records), `inference` (labelled every time it is used). The command log is in Appendix A. Raw captures
  stayed in the session scratchpad and were not committed (§8.4).
- **Outputs:** this file and `findings/incoming/G1.csv` (14 proposed findings, local ids NEW-1…NEW-14; the planning
  orchestrator renumbers them when it merges).

---

## 0. Summary

**Top risks, ranked** (full register in §2). Irreversible data loss ranks above degradation.

| rank | id | risk | L×I | who acts |
|---|---|---|---|---|
| 1 | G1-02 | **We can't see problems.** `sig-probe` has failed on every sweep since 2026-09-27T06:00Z (14 in a row). The 28 "critical" alerts it raised went to a Cloud Run log that nobody reads. There are no Monitoring policies, notification channels or uptime checks. `observability.yml` passes every day but measures nothing. | 5×3 | ops quick action + ticket |
| 2 | G1-01 | **Every workload runs as a project Editor.** All 3 services (each open to `allUsers`) and all 88 jobs run as the default compute service account, which holds `roles/editor`. One exploit in an ingest parser or the API could reach the whole project. | 2×5 | ticket + operator go |
| 3 | G1-03 | **The spine dies with the instance.** Deletion protection is off. Automated backups and PITR live inside the instance, "retain on delete" is unset, and no copy exists outside the instance. | 2×5 | ops quick action |
| 4 | G1-04 | **Restore has never been tested at scale.** The only drill was a 5-claim seed database imported into the *same* instance on 09-15. `sig-backups` holds only those two 146 KB dumps. | 3×4 | ops action + ticket |
| 5 | G1-05 | **Evidence can be overwritten or deleted.** No bucket has versioning, a retention policy or lifecycle rules, only the 7-day default soft delete, and every bucket is single-region. The OCFL capture store can be written and deleted by the Editor service account through gcsfuse, yet the docs call `ops/probes/` "WORM". | 2×5 | ops action + ticket |
| 6 | G1-06 | **Non-public routes can ship.** The `/curate/` exclusion exists only inside `build_public_web()`. The 09-27 publish was a hand-typed rsync of a rebuilt `web/dist`. The `sig-web` bucket is a third public origin. `/task/new/` serves 6 demo fixture pages. A chain-tip republish would also ship Round-10 routes nobody has approved. | 4×3 | ticket + ops |
| 7 | G1-07 | **The site is a frozen snapshot while the API is live.** Since the release, 32 scheduled runs emitted ≤ 156,273 claims (≤ 6.4 % of the watermark). No republish cadence exists. The API's materialized tables date from 09-27T00:44Z. | 5×3 | ticket + operator decision |
| 8 | G1-08 | **The first-fire wave runs unattended.** 33 of 79 triggers fire for the first time between 10-01 and 10-21, including the 10-10 OSM replay. 12 of their jobs have never executed. No one is alerted if they fail. | 3×3 | ops watch plan |

**Needs an operator go** (production mutations, P3): G1-02 quick actions (probe roll, alert channel, uptime
checks); G1-03 (deletion protection, retain-on-delete, maintenance window); G1-04 (the drill itself); G1-05
(versioning/lifecycle); G1-06 (removing `allUsers` from `sig-web`); G1-08 (the watch window and any re-execution);
G1-10 (budget and billing export, Q-10); G1-17 (deleting cruft jobs); disabling the GitHub `reingest` schedule.
**Tickets** (engineering, then an operator go to apply): least-privilege identities (G1-01); publish allow-list,
a single publish path and regression tests (G1-06); the republish pipeline (G1-07); the live-diff reconciler and
cron lint (G1-09); alert delivery as code (G1-02); the restore-drill script (G1-04); IaC for `sig-alerts` (G1-11).
**Doc fixes:** G1-15.

**Proposed Track-0-style quick actions** (§5; each is reversible, costs ≲ $1/mo, and needs its own go):
QA-1 enable deletion protection and retain-backups-on-delete · QA-2 set a maintenance window ·
QA-3 an e-mail notification channel, a log-based alert on `SIG-ALERT`, and alerts on failed job executions ·
QA-4 two uptime checks (site `/`, API `/health`) plus a TLS-expiry alert · QA-5 roll `sig-probe` onto the current
`cadence.toml` · QA-6 versioning plus a noncurrent-version lifecycle on `sig-restricted` ·
QA-7 remove `allUsers` from the `sig-web` bucket · QA-8 disable the GitHub `reingest` schedule ·
QA-9 a PITR restore drill before 10-10 · QA-10 a budget alert at the Q-10 ceiling.

---

## 1. Evidence snapshot (live-read unless marked)

| area | observed | cmd |
|---|---|---|
| Cloud SQL `sig-pg` | POSTGRES_18, ENTERPRISE, `db-custom-1-3840`, ZONAL, 15 GB SSD with autoresize (no limit); backups on (05:00 UTC, 7 retained, `backupTier STANDARD`, no custom location); PITR on (7-day logs, `CLOUD_STORAGE`); **`deletionProtectionEnabled` false**; `retainBackupsOnDelete`/`finalBackupConfig` unset; **no maintenance window**; `sslMode ALLOW_UNENCRYPTED_AND_ENCRYPTED`, public IPv4 with 0 authorized networks; Query Insights off | G1-C20 |
| Cloud SQL usage | disk used 6.42 GB (09-30), 6.94 GB peak (09-25); daily max CPU 1.0 on 09-26 and 0.32 on 09-30; daily max memory 1.0 every day 09-16…09-24, 0.70 on 09-30 | G1-C18 (Monitoring API) |
| Cloud SQL ops history | the 09-15 "restore drill" = `EXPORT` → `CREATE_DATABASE` → `IMPORT` inside `sig-pg`. `UPDATE` ops on 09-23, 09-24, 09-26 and 09-27 (tier changes, F-38), then 09-30 (Track 0). The spine has never been restored into a new instance | G1-C19 |
| buckets (4) | all US-CENTRAL1, uniform access, soft delete 604800 s (7 days); **versioning, retention policy, lifecycle, event-based hold and logging all unset** | G1-C02 |
| bucket IAM | `sig-web` and `sig-public`: `allUsers:objectViewer`. `sig-restricted` and `sig-backups`: private (PAP enforced); the Cloud SQL SA is objectAdmin on `sig-backups`. `projectEditor` is legacy owner of every bucket's objects | G1-C24 |
| bucket sizes | public 1.91 GB · restricted 3.21 GB · web 0.57 GB · backups 0.29 MB · `_cloudbuild` 0.54 GB | G1-C18 |
| `sig-backups` | exactly 2 objects: `pg/sig-20260915T124956Z.sql` (146,109 B) and `pg/sig-20260915T125252Z.sql` (146,526 B), the 09-15 5-claim seed | G1-C03 |
| `sig-restricted` layout | `evidence/captures/` (OCFL 1.1 root), `exports/national/{2026-09-24T150000Z,2026-09-24T154017Z,2026-09-27T005153Z}/`, `ops/runs/` (387 objects, 208 source prefixes), `ops/probes/` (60 sweeps, 09-16…09-30), `rollback/{sig-web-pre-p30.3-2026-09-24,sig-web-pre-republish-2026-09-27T0000Z}/`, `web/` | G1-C03/04 |
| runtime identities | `sig-api`, `sig-web`, `sig-alerts` and **all 88 jobs** use `873541617837-compute@developer`, which holds **`roles/editor`** and `roles/cloudsql.client`. Scheduler invokes as `sig-scheduler@` (`run.invoker`; checked on `sig-sched-probe`/`sig-probe`). `auditConfigs` are absent (no Data Access audit logs) | G1-C21/22/23 |
| services | `sig-api` 1 vCPU/512 Mi, min 1, max 2 (template), `allUsers` invoker, env `SIG_PG_PASSWORD` from Secret Manager. `sig-web` 1 vCPU/512 Mi, min 0, `allUsers`. `sig-alerts` `sig-api:latest`, `allUsers`, its program is an inline base64 `python -c` in the service args | G1-C10/11 |
| `sig-alerts` behaviour | on POST it checks a bearer token, then `print("SIG-ALERT-RECEIVED …")` and returns 204. It delivers to **no human channel**. 28 receipts since 09-27 and 48 visible in 30 days (log retention is 30 days) | G1-C12/13 |
| Monitoring | 0 uptime checks, 0 alert policies, 0 notification channels. Log buckets: `_Default` 30 days, `_Required` 400 days | G1-C14 |
| probe | `sig-probe` job (image `sig-api@sha256:6ad5477d…`, bakes `/app/ops/cadence.toml`): **FAILED on all 14 executions from 09-27T06:00Z to 09-30T12:00Z**. Latest sweep: 6 targets ok, `sig-public-okc-manifest` and `sig-public-france-manifest` "unreachable" (retired by the 09-27 republish; the repo fixed `cadence.toml` in `48369305`, but the job never received that fix). `SIG_PROBE_WEB_URL` = the **run.app** URL, not the canonical origin | G1-C05/08/09 |
| real uptime (probe log, 6 h sampling) | since 09-25: `sig-web-root` 25/25, `sig-api-health` 24/24, `sig-api-coverage-okc` 25/25, `sig-api-root` 24/25, `sig-pg-cloudsql` 25/25. Since 09-16: `sig-api-root` 54/60 (timeouts before ADR-108) | G1-C09 |
| traffic (7 d) | LB 200-class 392–2,321/day; 400-class 568–12,444/day; LB response bytes 4.6–450 MB/day (launch spike on 09-24). The `sig-web` 4xx sample is mostly scanners (`/wp-admin/`, `/.git/`, `/.aws/`), and `/curate/` is still requested (15 of 300 sampled 4xx on 09-30) | G1-C18/26 |
| Scheduler | 79 jobs, all ENABLED, all `Etc/UTC`. 46 have fired and **33 have never fired** (next fires 10-01…10-21). `sig-sched-sam-gov` live `0 5 1 * 1` vs repo `0 5 * * 1` | G1-C06 |
| Run jobs | 88. Image spread: `6ad5477d` ×71, `63b809b2` ×4, `d1f94361` ×4, `feff986c` ×3 (batch-05, resume-test, okc-doc-egress-probe), `curlimages/curl:8.10.1` ×3 (**tag, not digest**), and one each of `1cccde1a` (export), `e0674d95` (materialize), `ad06e964` (replay). 343 executions since 09-15: 275 ok, 68 failed or cancelled | G1-C07 |
| Artifact Registry `sig` | 95 image versions, ~11.7 GB summed compressed size (layers may dedupe), **no cleanup policy**. Tag `latest` now = `ebb6dab9…` (09-22). `sig-alerts` runs `d0ea2deb…` (09-15), which no longer carries the tag | G1-C16/17 |
| front door | global HTTPS LB (`sig-web-fr-http`/`-https`, one IP), managed cert ACTIVE (apex + www, expires 2026-12-22, auto-renewing), **no Cloud Armor policy, no CDN**. The API has no custom domain | G1-C15 |
| secrets (names only) | `sig-alert-webhook-token`, `sig-api-env` (0 versions), `sig-data-gov-key`, `sig-maproulette-api-key` (v1 2026-09-23; **no accessor binding**, so only the Owner can read it), `sig-muckrock-refresh`, `sig-openstates-key`, `sig-pg-password`, `sig-sam-gov-key`, `sig-zenodo-client-id`, `sig-zenodo-client-secret`, `sig-zenodo-sandbox-token` (2 versions). Accessor on the used keys = the default compute SA | G1-C25 |
| billing | project linked, billing enabled. **No BigQuery dataset** in the project (no billing export here). Budgets are **not readable** with this credential: the Budget API is disabled in the gcloud quota project, and enabling it would be a mutation, so nothing was enabled | G1-C27 |
| GitHub | `reingest` scheduled run 6/6 failures on `main` ("`--sink pg requires --dsn`") (A1 NEW-2). `observability` 6/6 "success", yet its log shows `"usage_gb": null` and "staging endpoints unset — probe skipped (offline posture; nothing measured)" (run 36713858053) | A1 C22; G1-C28 |

---

## 2. Risk register

L (likelihood) and I (impact) are on a 1–5 scale; `sev` uses the §8.2 scale. **Type:** `ticket` = engineering
work, `ops` = an operator-approved production action, `doc` = a documentation fix, `decision` = an operator
decision. The requirement ids are proposals (§4); `SIG-OPS-*` is a new namespace.

| id | risk | evidence | L×I | sev | current control | proposed hardening | type | req |
|---|---|---|---|---|---|---|---|---|
| **G1-01** | Over-privileged runtime identity. Three public (`allUsers`) services and 88 jobs run as a project **Editor**. The ingest jobs parse untrusted PDFs and HTML from the internet. Editor can delete Cloud SQL instances, buckets and objects, and redeploy services. Combined with G1-03/G1-05, a single compromise can erase the spine, its in-instance backups and the evidence store | G1-C21/22/23; NEW-1 | 2×5 | S1 | RLS read role in the API (`SIG_API_ROLE`); the ingestion gate; the Editor role cannot read secret payloads without `secretAccessor` | per-workload service accounts: `sig-api-rt` (cloudsql.client, accessor on `sig-pg-password` only); `sig-web-rt` (objectViewer on `sig-web`); `sig-ingest-rt` (cloudsql.client, objectCreator + objectViewer on `sig-restricted`, no delete, accessor on its own keys); `sig-export-rt`/`sig-materialize-rt` (their buckets plus cloudsql.client); `sig-probe-rt` (read-only); `sig-alerts-rt` (none). Then **remove `roles/editor`** from the default compute SA. Deploy scripts pass `--service-account` explicitly. A `live-diff` check (G1-09) fails on any basic role held by a runtime SA | ticket + ops | SIG-SEC-007 |
| **G1-02** | Blind operations. The probe has been red since 09-27T06:00Z because stale targets are baked into its image. Alerts reach no human. Nothing probes the canonical origin, the LB or TLS. `observability.yml` is green while measuring nothing. The only notification the operator plausibly receives is GitHub's scheduled-failure e-mail for `reingest`, which is noise (inference) | G1-C05/08/12/13/14/28; NEW-2, NEW-3 | 5×3 | S1 | the recorded-alert ledger (ADR-077); probe JSONL in `ops/probes/` | QA-3/QA-4/QA-5 now; then a ticket: (a) move probe targets out of the image (read `cadence.toml` from the release bundle or GCS, or pass targets by env) so config changes need no roll; (b) deliver alerts to e-mail through Cloud Monitoring (log-based alert on `SIG-ALERT` and on failed job executions); (c) keep `sig-alerts` only as a record, repo-owned and IAM-authenticated; (d) make `observability.yml` fail when it measured nothing, or delete it; (e) dedupe and escalate: a condition red for more than 24 h re-notifies daily | ops + ticket | SIG-OPS-006, -007 |
| **G1-03** | Spine lost with the instance. Deletion protection is off (A1 NEW-3), automated backups and PITR logs are deleted with the instance by default, and no copy exists outside the instance or outside GCP (the Zenodo production deposit is owed, D-P21.5-1/HG-07) | G1-C20; NEW-14 | 2×5 | S1 | 7 automated backups plus 7-day PITR, all inside the instance lifecycle | QA-1 (deletion protection; retain-backups-on-delete or final backup; verify the exact flag names at execution). A monthly logical export `gcloud sql export sql … gs://…-sig-backups/pg/…` with lifecycle keeping 3 monthly copies. A delete-guard runbook step. Longer term, a cross-project or cross-region backup copy | ops | SIG-OPS-002 |
| **G1-04** | Untested restore. No restore of the 2.4 M-claim, 6.4 GB spine has ever happened, so RTO and RPO are unknown. The 09-15 drill hit an `ALTER DEFAULT PRIVILEGES` restore blocker, which shows that restorability regresses silently. The stale 09-15 dumps look like backups | G1-C03/19; `GCP_DEPLOYMENT.md:127-145`; NEW-14 | 3×4 | S1 | managed backups (on since 09-30); `sig-ops backup-drill` (local Docker, counts only `claim`/`evidence_artifact`/`entity`, `ops/src/ops/backup.py:31`) | the §3.1 drill (PITR clone into a **new** instance, verify, delete), quarterly and after every sqitch deploy; first run QA-9 before 10-10. A ticket extends `backup-drill` into a `--cloudsql-clone` mode with append-only count parity at T. Move or label the 09-15 dumps as `seed-2026-09-15/` so they are not mistaken for backups | ops + ticket | SIG-OPS-001 |
| **G1-05** | Mutable evidence and public buckets: no versioning, retention or lifecycle; 7-day soft delete; single region. The OCFL store (`evidence/captures/`), run rows (`ops/runs/`) and probe history (`ops/probes/`) can be overwritten or deleted by the Editor SA and by every ingest job's read-write gcsfuse mount. `ops/README.md:96` calls `ops/probes/` "WORM" | G1-C02/24; `ops/README.md:96`; NEW-4 | 2×5 | S1 | soft delete (7 d); append-only convention in code | QA-6 (versioning plus lifecycle deleting noncurrent versions after 90 days) on `sig-restricted` now. A ticket moves captures to a dedicated `…-sig-evidence` bucket with a **retention policy** (start unlocked, e.g. 365 days; lock only after operator review) and gives ingest SAs no `objects.delete`. `sig-public`/`sig-web` get versioning (rollback of a bad publish) with a 30-day noncurrent lifecycle. Replicate `sig-restricted` to a dual-region bucket or another project (Storage Transfer, weekly) | ops + ticket | SIG-STORE-048 |
| **G1-06** | Non-public routes reach the public origin. `/curate/` was served 09-27T01:33:56Z → 09-30T16:21:34Z (≈ 86.8 h). Root cause in §3.2. The `sig-web` bucket is public-read, a third origin that bypasses nginx. 6 demo fixture task pages are live. The next chain-tip republish would ship `/releases/`, `/research-dossier/` and `/intake/` without a decision | §3.2; G1-C24/29/30; NEW-5, NEW-6, NEW-7 | 4×3 | S1 | `strip_non_public_web()` inside `build_public_web()` (`ops/src/ops/publish.py:168-185`); unit test `tests/ops/test_publish.py:151` | a committed **public-route allow-list**; one publish command that asserts the allow-list, syncs and verifies (no hand-typed rsync); curate excluded at build time rather than deleted afterwards; post-sync absence probes on every public origin; QA-7 | ticket + ops | SIG-OPS-003, -004 |
| **G1-07** | Freshness drift. The site is pinned to `sig-2026-09-27-ce480ab1` while ingest runs daily; no republish cadence or trigger exists; the API mixes live claims with materializations from 09-27 (inference); no release id is shown (F-11) | §3.6; NEW-13 | 5×3 | S2 | a manual RETURN-PASS republish (P31.16), gated by HG-11 | §3.6: a monthly republish after the batch window, plus drift and age triggers; a scheduled `sig-materialize`; disclosure on the site | ticket + decision | SIG-OPS-008 |
| **G1-08** | Unattended first-fire wave (10-01…10-21) and the 10-10 OSM replay: 33 triggers not yet fired, 12 jobs never executed, 2 whose last execution failed; OSM history includes a 19.7 h failure (09-19) | §3.7; G1-C06/07; NEW-8 | 3×3 | S2 | idempotent, resumable ingest (ADR-111); run rows in GCS | the §3.7 watch plan; QA-2 (maintenance window) and QA-3 before 10-01 | ops | SIG-OPS-006 |
| **G1-09** | Scheduling truth is fractured. Three schedulers: Cloud Scheduler (actual), GitHub `reingest` (failing daily), and Dagster `orchestration/` (unused, F-39). Live and repo cron drift apart. Config baked into images never reaches running jobs. The repo keeps day-of-month + day-of-week crons (OR semantics). 9 jobs have no trigger, 2 of which can write to production. The job fleet runs on 4 builds | §3.4; A1 NEW-2/NEW-4; NEW-9, NEW-10 | 4×2 | S2 | `sig-ops cadence --check` (repo-internal only: `ops/src/ops/scheduled.py:203`) | declare **`ops/cadence.toml` + Cloud Scheduler** authoritative (new ADR superseding ADR-076's scheduling path); `sig-ops live-diff` (read-only) run daily by `sig-probe`; cron lint; a `[manual_jobs]` allow-list; one fleet digest per roll; QA-8 | ticket + ops + doc | SIG-OPS-005 |
| **G1-10** | Cost opacity and denial of wallet. The list-price estimate is ≈ $90–100/mo against the README's "≈ $0" and "~$9". No billing export exists and budgets can't be verified. Public buckets and unauthenticated endpoints have no rate limit | §3.8; NEW-11 | 3×2 | S2 | the egress-report verb (not measuring: `usage_gb: null`) | QA-10 budget alert; billing export to BigQuery (operator); an operator-set Q-10 ceiling; optional Cloud Armor rate limit on the LB (+$5/policy/mo) | decision + ops | SIG-OPS-009 |
| **G1-11** | Image/tag hygiene. `sig-alerts` on `:latest`, a tag that has since moved (`d0ea2deb` → `ebb6dab9`), so any redeploy silently changes the code. Its program exists only as base64 in the service args. The egress probes run on the `curl:8.10.1` tag. No AR cleanup policy | G1-C10/16/17 | 2×1 | S3 | ADR-111 digest rule for jobs; `pin_image_digest` in `web.sh` | extend the digest rule to services; a repo-owned `sig-alerts` (or retire it, G1-02); delete the egress probes (G1-17); an AR cleanup policy keeping tagged-in-use versions, the last 10 per tag prefix, and anything referenced by a live revision or job | ticket | SIG-SEC-008 |
| **G1-12** | MapRoulette key exposed in a session transcript and left unrotated (operator-accepted 2026-09-30) | LEDGER lines 134, 145; G1-C25 | 2×2 | S3 | the key is unused (`[tasks.contribution] registered=false`, push refuses with exit 3). No GCP runtime SA can read it: the only principal is the Owner | accept for now; make **rotate before first use** a hard precondition of D-P21.7-1 activation; record the blast radius (§3.9) | decision (accepted) | SIG-SEC-009 |
| **G1-13** | Forensics gap. No Data Access audit logs, so direct reads of restricted bytes in GCS are unlogged. The app-level `evidence_access_log` table covers API paths only. `_Default` logs keep 30 days, so pre-09-01 alert and probe logs are already gone | G1-C14/21; NEW-12 | 2×3 | S2 | `evidence_access_log`; `_Required` audit 400 days | enable `DATA_READ`/`DATA_WRITE` audit logs for `storage.googleapis.com`, **exempting the ingest and export SAs** (volume control), so human and unexpected reads are logged; raise `_Default` retention to 90 days (~$0.01/GiB-mo beyond 30 days) or add a log sink to a bucket with lifecycle | ops + decision | SIG-SEC-005 (existing) |
| **G1-14** | Cloud SQL resilience posture: ZONAL (no HA); no maintenance window, so Google may restart during a batch window; `sslMode ALLOW_UNENCRYPTED_AND_ENCRYPTED`, mitigated by 0 authorized networks and connector-only access; Query Insights off | G1-C20 | 2×3 | S2 | ADR-108 reconnect held through the 09-30 PITR restart (one 503, 16 s) | QA-2 (window Sun 09:00 UTC, away from 03:00–06:00 batches); `ENCRYPTED_ONLY` when convenient; HA stays a Q-10 cost decision (≈ 2× the instance cost) | ops | SIG-OPS-002 |
| **G1-15** | Runbook and doc truth gaps (§3.10). `ops/gcp/README.md` still presents e2-micro as the DECISION and the cost table as ≈ $0; `ops/README.md` claims WORM; `OPERATIONAL_READINESS.md:90` names `reingest.yml` as the scheduler; there is no incident, restore, republish or rotation runbook | §3.10 | 4×2 | S2 | scattered run ledgers | §3.10 runbook set + doc fixes | doc + ticket | SIG-OPS-010 |
| **G1-16** | Project-id publicity (D-P30.4-4) | DEFERRALS `D-P30.4-4` DONE via ADR-119; bucket URLs in the public manifest embed the id | 1×1 | S3 | ADR-119 scoped leak check (code + config) | **no action**. The id is not a credential and is already public through `storage.googleapis.com/<id>-sig-public/…`. The real exposure is the unauthenticated endpoints, covered by G1-10 | — | — |
| **G1-17** | Cruft jobs with production capability: `sig-sink-bench` wrote 24,811 real claims into the canonical spine in P31.4 and will do so again if executed; `sig-ingest-resume-test`; 4 egress probes (09-16) — all as Editor | A1 NEW-4; G1-C07 | 1×3 | S3 | none (they have no trigger) | delete the 6 (operator go); keep `sig-replay-ingest` (args exit 64 unless overridden, ADR-113), `sig-export` and `sig-materialize` as declared manual jobs; set `sig-export`'s default args to exit 64 as well (they currently pin `--as-of 2026-09-26T15:46:25Z`; `export.sh run` overrides them) | ops | SIG-OPS-005 |

---

## 3. Designs by area

### 3.1 Data protection

**State after Track 0** (live-read G1-C20): automated backups (05:00 UTC, 7 retained) plus PITR (7-day logs), and 2
SUCCESSFUL backups at freeze. **Deletion protection off.** Automated backups and PITR logs belong to the instance:
deleting `sig-pg` deletes them unless retain-on-delete or a final backup is configured, and neither is.

**Restore drill: design.** It never touches `sig-pg` beyond reads. It creates, verifies and deletes a new instance.
The commands are for the operator and were not executed.

```bash
P=zeta-medley-508121-u7; STAMP=$(date -u +%Y%m%dT%H%MZ); T=$(date -u -v-10M +%Y-%m-%dT%H:%M:%SZ)  # restore point, 10 min ago
# 1. PITR clone → NEW instance (exercises backups + WAL; sig-pg untouched)
gcloud sql instances clone sig-pg sig-pg-drill-$STAMP --point-in-time "$T" --project $P
#    (quarterly variant: restore the latest AUTOMATED backup into a pre-created empty instance)
#    gcloud sql backups restore <BACKUP_ID> --backup-instance=sig-pg --restore-instance=sig-pg-drill-b-$STAMP
# 2. verify through the Cloud SQL Auth Proxy, read-only role, on BOTH instances:
#    append-only ⇒ exact parity at T:  SELECT count(*) FROM claim WHERE lower(sys_period) <= :T  (clone == source)
#    + the same for claim_evidence, evidence_capture, evidence_artifact, entity, ingest_run,
#      ingest_run_completion, resolution, contradiction, coverage_record; spine_watermark row equal;
#    + `sqitch status` on the clone == source plan tip; PostGIS extension present; `api` smoke:
#      `uv run python -m api` against the clone → /health 200, one /v1/coverage call
# 3. record RTO (clone start → verified) and RPO (T vs max(lower(sys_period)) on the clone) in the drill record
# 4. delete — name-checked, never sig-pg:
gcloud sql instances delete sig-pg-drill-$STAMP --project $P
```

| aspect | estimate (inference unless marked) |
|---|---|
| time | clone of a ~6.4 GB instance: 15–45 min (unmeasured; the first drill measures it); verification 15–30 min; end to end ≲ 1.5 h of operator time |
| cost | the drill instance is `db-custom-1-3840` at ≈ $0.068/h plus 15 GB SSD prorated, so ≈ $0.15–0.40 for a 2–4 h drill; no egress |
| cadence | QA-9 before 2026-10-10 (establishes a known-good PITR path before the OSM replay); then quarterly and after any sqitch deploy |
| hazards | the name check before `delete`; a clone inherits flags, users and public IP (0 authorized networks, so not reachable without the proxy); `ALTER DEFAULT PRIVILEGES` regressions surface in the backup-restore variant, not the clone, so the quarterly run uses that variant; D-P32.10a-1 (`sqitch verify` division by zero) must not be mistaken for a restore failure |

**Deletion protection (A1 NEW-3): recommend enabling now (QA-1).** It is a metadata-only change (no restart expected;
confirm the op type is `UPDATE` and watch `/health`, as Track 0 did). Pair it with retain-backups-on-delete or a
final backup, and with a monthly `gcloud sql export sql` to `sig-backups` (an off-instance logical copy that also
proves the dump path; its load on a 1-vCPU instance is noticeable, so run it Sunday 09:00 UTC).

**The backup bucket.** It holds only the 09-15 seed dumps (146 KB each; the "drill" in `GCP_DEPLOYMENT.md:127-145`).
Keep them as history but **relabel** them (a `pg/seed-2026-09-15/` prefix plus a README object) so no one counts
them as a backup. Add lifecycle rules (`pg/monthly/` keeps 3 newest; `pg/adhoc/` expires after 30 days).

**Bucket protection matrix (design).** Costs are ~$0.020/GB-mo standard; noncurrent versions add at most the churned
bytes.

| bucket | today | proposed | est. added cost |
|---|---|---|---|
| `sig-restricted` (3.21 GB: captures, exports, runs, probes, rollback) | soft delete 7 d only | versioning plus lifecycle deleting noncurrent versions after 90 days (QA-6). Captures move to a dedicated `…-sig-evidence` bucket with a retention policy (unlocked 365 d first). Weekly copy to a dual-region or second-project bucket | < $0.20/mo |
| `sig-public` (1.91 GB, release compartments) | soft delete 7 d | versioning, 30-day noncurrent lifecycle (rollback of a bad publish without a manual pre-copy) | < $0.10/mo |
| `sig-web` (0.57 GB) | soft delete 7 d, **public-read** | remove `allUsers` (QA-7; the site is served by `sig-web` through gcsfuse under its SA); versioning, 30-day noncurrent | ≈ $0 |
| `sig-backups` | soft delete 7 d | lifecycle as above; optionally a retention policy on `pg/monthly/` | ≈ $0.05/mo |

### 3.2 Publish pipeline safety (`/curate/` and friends)

**Where the exclusion lives (code):** `ops/src/ops/publish.py:172-185`, `NON_PUBLIC_WEB_PATHS = ("curate",)` and
`strip_non_public_web(dist)`, called **only** at the end of `build_public_web()` (`:168`), which
`run_public_prepare()` calls (`:526`), which `sig-ops deploy --prepare-only` calls (`ops/src/ops/cli.py:1469-1470,1503-1531`).
It was added by `950d4ebc` (P30.3, 2026-09-24). `ops/gcp/web.sh` has **no sync action** (`image`/`service`/`describe`
only), and `sig-ops deploy` without `--prepare-only` prints a plan. So the sync step lives only in prose.

**Why it failed (timeline; recorded-execution and live-read, with the inference labelled):**

1. P31.16's publish half ran `sig-ops deploy --prepare-only`, which built and stripped `web/dist`
   (`docs/build/runs/P31.16.md:208-211`).
2. During the same half, `/research-queue/` returned 500 at scale, and the fix was applied to
   `web/src/pages/research-queue.astro` (`P31.16.md:256-258`). The fix's commit `48369305` is dated
   2026-09-26T21:36:59-04:00 = **2026-09-27T01:36:59Z**, *after* the `curate/` objects were uploaded
   (**01:33:56–57Z**, TRACK0_RECORD) and the web sync ran (01:29–01:35Z, `REPUBLISH_LIVE_2026-09-27.md:32-41`),
   yet the fix was live. **Inference:** `web/dist` was rebuilt from an uncommitted tree through a path other than
   `build_public_web()` (a direct export-mode `astro build`/`npm run build`), which re-emitted `curate/`.
3. The operator-side sync was the hand-typed
   `gcloud storage rsync -r --delete-unmatched-destination-objects web/dist/ gs://…-sig-web/`
   (`REPUBLISH_LIVE_2026-09-27.md:39-40`). Nothing asserted the contents of `dist` at sync time.
4. Post-publish verification probed 16 content routes plus islands (`P31.16.md:236-243`) but never checked that
   a non-public route is **absent**. `sig-probe` has no absence targets.
5. The `sig-web` bucket is `allUsers:objectViewer` (G1-C24), so the pages were also public at
   `storage.googleapis.com/<id>-sig-web/curate/…`, a path nobody probes (`/index.html` there → 200, G1-C29).

**Root cause:** the exclusion is a deletion applied after the build, inside one wrapper, while the sync is a
separate hand step with no gate, and verification checks only presence. Any rebuild or any new internal route
bypasses it.

**Durable fix (ticket):**

1. **Don't emit it.** Public builds skip internal routes. Gate `web/src/pages/curate/**` behind
   `SIG_BUILD_INTERNAL=1`, which the web e2e suite sets (`web/tests/e2e/curate*.spec.ts`), or move the curation
   shell into its own Astro build output (`web/dist-internal/`). The default build then contains no `curate/`.
2. **Allow-list, not deny-list.** A committed `ops/public_routes.toml` lists every approved top-level route prefix and
   file (`index.html`, `robots.txt`, `_astro/`, `map/`, `dossier/`, …). The publish refuses (exits non-zero) when
   `dist` contains any top-level entry that is not listed. This also catches unapproved Round-10 routes and future
   dev pages. Adding a route is then an explicit, reviewable diff, which G3 can tie to its release model.
3. **Content assertions.** Refuse any HTML carrying `data-testid="curate-auth-banner"`, a form `action` to
   `127.0.0.1`/`localhost`, or a demo-fixture marker (e.g. `demo_` task slugs; the fixture-export guard at
   `publish.py:126-131` is the precedent).
4. **One publish path.** `sig-ops publish-web --apply` (or `web.sh --apply sync`) = prepare → allow-list and content
   assertions → write `dist/.sig-release.json` (release id, git commit, build time, dist tree digest; F-11) →
   `rsync` → post-sync verify. Runbooks forbid hand-typed `rsync` into public buckets.
5. **Post-sync and continuous absence checks.** `cadence.toml` gets `kind = "http-absent"` probe targets
   (`/curate/`, `/curate/submit/`, and one representative denied route) on **all** public origins (canonical,
   run.app, bucket URL while it is still public). The publish verify step runs the same targets immediately, and the
   6-hourly probe catches drift after that.
6. **Regression tests.** (a) `tests/ops/test_publish.py`: the sync refuses a `dist` with `curate/`, with an unlisted
   top-level dir, or with a `demo_` task page. (b) A structural test: every page under `web/src/pages/` that uses
   `CurateLayout` (or any layout marked internal) maps to a route not on the allow-list, and every allow-listed prefix
   exists in the build. (c) A web test: an export-mode build without `SIG_BUILD_INTERNAL` emits no `curate/`.
   (d) An ops config test: every `NON_PUBLIC` route has an `http-absent` probe.

**Route inventory and proposed decision** (live-read G1-C29/30; content judgments are C2's):

| route | live | nature | proposal |
|---|---|---|---|
| `/curate/**` (6 pages) | 404 (Track 0) | authenticated curation shell, demo, form posts to loopback (ADR-068) | **never public**: not built by default; absence probe |
| `/style-guide/` | 200 | public editorial style guide (SIG-UI-046), in the nav | **public** (by design) |
| `/visual-language/` | 200 | §39.1 reference page; source header says it exercises components "over the demo fixture (OKCPD 42-vs-38)"; `robots.txt` names it as crawlable | **public**, but C2 checks whether fixture entities read as real. If so, add an "illustrative example" label or move it under `/about/` |
| `/editorial-standards/` | 200 | public standards | public |
| `/task/new/<slug>/` (78 pages) | 200 | generated research-task pages; **6 are fixture demos** (`agency:okcpd` × `demo_no_evidence_found`, `demo_not_researched`, `demo_evidence_of_absence`, `demo_unresolved`, …) | public for real gaps; **strip `demo_*` in export mode** (NEW-7) |
| `/task/` | 403 | nginx namespace without an index | return 404, or add an index; a 403 reads as "forbidden content exists" |
| `/dispute/` | 200 | dispute page with no working channel (F-03) | C/G2 |
| `/releases/`, `/research-dossier/`, `/intake/` | 404 | Round-10 surfaces not deployed (F-14); in the chain-tip build | **not on the allow-list** until G2/Q-9 approves each |
| `/sitemap.xml`, `/favicon.ico` | 404 | missing (F-9 family) | C stream polish |

### 3.3 Image and tag hygiene

- **Services:** `sig-api` and `sig-web` are digest-pinned (BASELINE). `sig-alerts` is `sig-api:latest`, and `latest`
  **has moved** (now `ebb6dab9…`, 2026-09-22), while the running revision still uses `d0ea2deb…` (G1-C16/17). Any
  env or flag update to `sig-alerts` would roll to different code without anyone choosing that. The service's real
  program is an inline base64 `python -c` string (G1-C10), so the repo cannot reproduce it. **Design:** retire
  `sig-alerts` in favour of Cloud Monitoring delivery (G1-02), or rebuild it from a repo-owned
  `ops/alerts_receiver.py` deployed by digest with `--no-allow-unauthenticated` (invoker = the probe SA).
- **Jobs:** all are digest-pinned except 3 egress probes on `curlimages/curl:8.10.1` (to be deleted, G1-17). The fleet
  spans **4 ingest builds** (G1-C07). `batch-05` is deliberately held on `feff986c` (P31.4, `ingest-18355040ccc8`)
  for the D-P31.4-1 observation. **Inference** (AR tag timestamps: `feff986c` built 09-25T01:21Z, the
  `p31-7-062306e70d3d` image `6ad5477d` at 08:12Z): the 10-10 replay runs **without** P31.7's re-sighting recording,
  so OSM re-sightings will not add `claim_evidence` links, unlike every other source.
- **Rule (proposed SIG-SEC-008):** every Cloud Run service and job references an image by digest. A roll records
  before and after digests (`roll-jobs --record`, ADR-111 §6). The fleet converges on one ingest digest per roll
  unless a pin is declared with a reason and an expiry in `cadence.toml`. `live-diff` reports digest spread and any
  tag reference.
- **AR hygiene:** 95 versions, ~11.7 GB, no cleanup policy. Add a cleanup policy (keep versions referenced by any live
  revision or job, the newest 10 per tag prefix, and anything newer than 30 days; start in dry-run mode).

### 3.4 Scheduling truth

**What exists** (live-read G1-C06/07; code):

| scheduler | state | verdict |
|---|---|---|
| Cloud Scheduler (79) → Cloud Run jobs, realised by `ops/gcp/scheduled-ops.sh` from `ops/cadence.toml` | runs everything real; 46 fired, 33 pending first fire | **authoritative** |
| GitHub `reingest.yml` (ADR-076, `0 5 * * *`) | fails daily since 09-25 (`--sink pg requires --dsn`; A1 NEW-2); cannot reach Cloud SQL from GitHub runners anyway | **retire the schedule** (QA-8: `gh workflow disable reingest`, then a PR removing `schedule:`), with a new ADR superseding ADR-076's scheduling path. Never "fix" it with a DSN secret: that would double-ingest next to Cloud Scheduler and move egress onto GitHub IPs |
| `orchestration/` (Dagster, ADR-016) | unused glue (F-39) | F2/F5 decide; not a scheduler of record |

**Drift and defects:**

- `sam_gov`: live `0 5 1 * 1` vs repo `0 5 * * 1`. The repo note (`ops/cadence.toml:317`) explains why: with both
  day-of-month and day-of-week restricted, cron uses **OR** semantics and also fires on the 1st. The fix was never
  applied live. **The repo still carries the same bug class:** `openstates` `0 5 2 * 2` ("weekly", but also fires
  on the 2nd), `congress_gov` `0 5 3 * 2` (labelled **monthly**, but fires every Tuesday plus the 3rd), and
  `eyes_on_flock` `0 5 23 * 0` (NEW-9). Congress and OpenStates are keyed APIs, so the extra runs spend quota.
- `sig-probe` runs with stale targets because `cadence.toml` is baked into the job image (`SIG_OPS_CADENCE=/app/ops/cadence.toml`).
  A repo fix only takes effect on a roll, and `cadence --check` compares the repo with itself only
  (`ops/src/ops/scheduled.py:203-210`).
- Untriggered jobs (A1 NEW-4), classified: **keep as declared manual jobs**: `sig-export` (driven by
  `ops/gcp/export.sh run`, which overrides its stale args), `sig-materialize`, and `sig-replay-ingest` (ADR-113,
  args exit 64). **Delete** (operator go): `aspi-/ccops-sf-/muckrock-/okc-doc-egress-probe` (09-16 one-offs; three on a
  tag), `sig-ingest-resume-test`, and `sig-sink-bench` (writes real claims into the canonical spine).

**Reconciliation design (ticket):** `sig-ops live-diff` (read-only; `gcloud … describe/list` only) compares:

1. each `[[sources]]`/`[[batches]]`/`[probes]` row with its Scheduler job (cron, time zone, target, state, invoker SA);
2. each Run job with the row (image digest vs the roll record or declared pin, `SIG_OPS_CADENCE` digest vs repo,
   timeout, service account, secrets by name);
3. Run jobs without a row, against a new `[manual_jobs]` allow-list;
4. services (digest, SA, invoker bindings) and bucket policies (versioning, retention, IAM) against a declared posture.

It outputs `DRIFT <kind> <name>: repo=… live=…` and exits 1 on drift. `sig-probe` runs it daily and alerts on any
drift. **Cron lint** in the same ticket: reject crons where both day-of-month and day-of-week are restricted unless
the row sets `cron_or_semantics_ok = true`. It also checks that `cadence` ("weekly" or "monthly") matches the cron's
fire count over a sample year.

### 3.5 Observability: what the operator is told today, and the design

**Today (live-read):** when something breaks, the operator is told **nothing**. `sig-probe` posts critical alerts to
`sig-alerts`, which logs them and returns 204 (28 since 09-27). No Monitoring alert policy, notification channel or
uptime check exists. GitHub's daily `reingest` failure e-mail is the likeliest thing the operator receives
(inference: GitHub notifies about scheduled-workflow failures by default), and it is irrelevant noise. The probe
watches run.app URLs, so an LB, DNS or managed-cert failure on `surveillancegraph.org` is invisible. Six-hour
sampling missed the 16 s PITR-restart 503 on 09-30 (TRACK0_RECORD).

**Design:**

| layer | mechanism | cost (list, inference) |
|---|---|---|
| synthetic | Cloud Monitoring uptime checks every 5 min from 3 regions: `https://surveillancegraph.org/` (content match on "As of"), API `/health`; managed-cert expiry alert at 21 days (QA-4) | uptime checks: free tier covers this volume |
| probe | `sig-probe` keeps the deep checks (DB via socket, public manifest, licences, compartment file, **absence** targets, `live-diff`); targets are not baked into the image (G1-02a) | unchanged |
| delivery | e-mail notification channel to the operator. Log-based alert on `textPayload:"SIG-ALERT"`. Metric alert on `run.googleapis.com/job/completed_execution_count{result="failed"}` for any job. Uptime-check alerts (QA-3) | ≈ $0–1/mo (verify current alerting-policy pricing at execution) |
| hygiene | an alert red for more than 24 h without change re-notifies once daily (not every 6 h); the probe's `forced-failure-drill` target stays available for a monthly delivery test | — |
| SLO / error budget | site root and API `/health` at **99.5 % monthly** (≈ 3.6 h budget), from uptime-check data; monthly readout generated from Monitoring plus `ops/probes/` into `docs/build/reports/` | — |
| retention | `_Default` logs 30 → 90 days (or a log sink to `sig-restricted/ops/logs/` with a 400-day lifecycle); `ops/probes/` and `ops/runs/` get versioning (G1-05) so their history is actually tamper-evident | cents/mo |
| CI truth | `observability.yml` fails when it measured nothing, or is deleted in favour of the hosted layer (it can't reach the hosted stack) | — |

### 3.6 Freshness and drift, and the republish cadence

**Drift since the release (live-read G1-C04; recorded-execution in run rows).** `sig-2026-09-27-ce480ab1` was
exported 09-27T00:51–01:03Z and synced 01:29–01:35Z. Since 09-27T01:30Z there have been **32 scheduled-ingest run
rows from 32 sources**, all `outcome ok` except `sam_gov` (`quota_reached`, 330). Their `claims_added` sum is
**156,273**, which is **≤ 6.4 %** of the 2,423,200 watermark. This is an **upper bound on net-new rows**:
`claims_added` counts emitted claims, including duplicates the sink drops (e.g. a +0 re-run of the 30-page OSM slice
still reports `claims_added 220009`, run rows of 2026-09-24/25). Largest contributors: `congress_gov` 20,008,
`camreg_act_au` 13,743, `camreg_austin_tx` 12,071, `eyes_on_flock` 11,976, `camreg_washington_dc` 10,610. The emit
rate is ≈ 45 k/day, and the 10-01…10-21 first-fire wave (§3.7) adds ≈ 1.4 M+ emitted (mostly duplicate OSM).
**Also stale (inference from code plus execution history):** the API reads materialized `coverage_record`
(`api/src/api/store_pg.py:857`) and `contradiction` (`:979`), last materialized by `sig-materialize-sczl9`
(09-27T00:42–00:44Z). API claim-level reads are live. So the API is internally mixed, and the site is fully frozen.
Exact net-new counts need a read-only DB count (not run: P3 plus no credentials in scope); G2/G3 should take one.

**Republish design (ticket plus decision; G3 owns the release model, and this is the ops cadence):**

- **Pipeline** (one command, §3.2 path): `sig-materialize` (≈ 2–30 min; 09-27 took 2 min) → `export.sh run`
  (as-of now; 09-27 took 12 min on 4 vCPU/16 GiB, ≈ $0.10) → fetch → `prepare` (partition + clean + allow-list) →
  **diff vs live** (the `REPUBLISH_DIFF` shape: new or removed compartments, licences, route set, claim delta) →
  gate → sync → post-sync verify → release record. Operator time today is ≈ 1 h; automated it could fit one Cloud Run
  job except the gate.
- **Gate:** keep an operator go per republish until G3 decides. Propose that a diff with **no new compartment, no
  licence change, no new route and no Part-VIII-sensitive category** may be pre-authorized by a standing operator
  decision. Anything else is always gated (HG-11 semantics).
- **Cadence:** **monthly**, on the 15th after the camera-registry batch window (6th–13th), plus triggers: (a) more
  than 10 % claim drift or more than 30 days since the last release; (b) a new source goes live or a source is
  withdrawn (takedown, which is immediate, per `CORRECTIONS_TAKEDOWN_RUNBOOK.md`); (c) a public-facing fix lands.
  Schedule `sig-materialize` weekly (Sundays 08:00 UTC) so the API's materialized views lag live claims by at most
  7 days.
- **Disclosure:** until the cadence runs, the site should state its release id and as-of and that the API is live
  (F-08/F-11; C3 owns the wording).

### 3.7 The 2026-10-10T03:35Z OSM monthly replay (D-P31.4-1) and the first-fire wave

**Facts:** trigger `sig-sched-camreg-batch-05` `35 3 10 * *` UTC → `sig-ingest-camreg-batch-05` (`feff986c`,
2 vCPU/8 GiB, timeout 129,600 s = 36 h, 0 retries, 17 member sources including `camreg_osm_surveillance`). History
(run rows): **09-19 `error` after 71,014 s (19.7 h) — "server closed the connection unexpectedly"**; 09-23 `ok`,
1,369,210 claims in 18,448 s (5.1 h), which follows a Cloud SQL `UPDATE` at 22:19Z. **Inference:** that success ran on
a temporarily larger tier (F-38). P31.4 then measured 179,882 claims/min on `db-custom-1-3840` and projected
12–15 min (D-P31.3-1, ADR-111). The whole batch previously took 5 h 10 m (`sig-ingest-camreg-batch-05-tjqdq`).
**The replay is not alone:** 10-01…10-21 is the first scheduled fire for 33 triggers. 12 of their jobs have never
executed (fbi-cde 10-01, eff-atlas 10-02, osm-element-history 10-05, madada 10-07, ccops-seattle 10-08,
ccops-nyc-post 10-09, pathways-rtcc 10-11, pathways-fr-css 10-12, pathways-drones 10-13, carnegie-ai-gsi 10-14,
frwm 10-15, aspi 10-16), and 2 last failed (`ccops-sf` 09-19, `ccops-somerville` 09-26).

**Watch plan:**

| when | what (read-only unless an operator go is noted) |
|---|---|
| by 10-01 | QA-3/QA-4/QA-5 live (alerts reach e-mail); QA-1/QA-2 (deletion protection, maintenance window away from 03:00–06:00 UTC; optionally a deny-maintenance period 10-09…10-11) |
| by 10-09 | QA-9 restore drill done (a known-good PITR path); record the pre-run baseline read-only: disk used (6.4 GB of 15), per-source claim counts through the API, `n_tup_upd`/`n_tup_del` on the claim tables |
| 10-09 03:28Z | batch-04 (26 sources, `6ad5477d`) is the dress rehearsal on the same tier; review its run rows and execution result |
| 10-10 03:35Z → +2 h | `gcloud run jobs executions list --job sig-ingest-camreg-batch-05`; job logs; Cloud SQL CPU, memory and disk; `sig-api /health`. Checks at +15 min, +1 h, +2 h (a scheduled read-only agent check is acceptable; it mutates nothing) |
| after | read `gs://…-sig-restricted/ops/runs/camreg_osm_surveillance/2026-10-10/` and record the verdict in D-P31.4-1 (a new dated cell, P7) |

**Success criteria** (D-P31.4-1 verbatim, plus ops additions): run row `outcome` ok or partial; `fetches` 158 (or
fewer only with `resumed` entries); `claims_added` ≈ 1.37 M; an `ingest_run_completion` row; `n_tup_upd`/`n_tup_del`
0; the OSM member finishes well under 1 h (ADR-111 projects 12–15 min). **Plus:** all 17 member run rows exist;
`/health` stays 200 (with at most one transient 503, the ADR-108 reconnect); Cloud SQL memory stays below 90 % with
no instance restart; disk growth stays under 1 GB.

**On failure:**

| symptom | action |
|---|---|
| over 1 h but progressing | don't cancel. Record ADR-107/111 revisit trigger (a) and route to G2/I8: a temporary tier bump for the monthly window (≈ $0.07/h more per extra vCPU, inference) vs sink tuning |
| connection drop (the 09-19 mode) or task failure | the execution fails (0 retries). With an operator go, re-execute `sig-ingest-camreg-batch-05`; expect `resumed` entries (per-capture flush, ADR-111). No data repair is needed: the spine is append-only |
| API degraded (`/health` 503 for more than 15 min) | with an operator go, cancel the execution (safe: append-only, resumable), then re-run in a quiet window |
| anomaly (`n_tup_upd/del` > 0, `claims_added` ≫ 1.37 M, disk jump over 3 GB) | stop and preserve. Clone PITR to T0 (10-10T03:30Z) for comparison. **Never** `UPDATE`/`DELETE` the spine; corrections are new claims |
| 36 h timeout | counts as a failure. Cost ≈ 2 vCPU × 129,600 s × $0.000018 + 8 GiB × 129,600 s × $0.000002 ≈ **$6.7** (list, inference) |

**Cost and time:** the expected run is 15 min to 5 h, costing ≈ $0.05–$0.95 in job compute (inference). Cloud SQL
costs nothing extra unless the tier is bumped.

**Is `db-custom-1-3840` enough?** **Probably yes for this run** (inference): the P31.4 bench hit 179,882 claims/min
on this tier; most of the 1.37 M will be duplicates on the +0 path (measured ≈ 700 k/min hosted, D-P31.3-1); the
`feff986c` image does not record re-sightings (§3.3), so there is no `claim_evidence` fan-out; memory is at 0.70
(09-30). The 09-19 failure fell in the window when memory sat at 1.0 every day (09-16…09-24), before ADR-107's steady
state. The residual risk is concurrent load. Nothing else is scheduled at 03:35Z on 10-10, but `ccops-sf` fires at
05:00Z and the probe at 06:00Z; both are light.

### 3.8 Cost truth

No billing data was readable (G1-C27). The table below is a **list-price estimate** (us-central1, no committed-use or
sustained-use discount, free tier noted) built from live configuration and Monitoring usage. It is labelled
**inference**. The operator should confirm it against the billing console. The next step is a BigQuery billing export
(operator, billing admin).

| driver | live config | est. $/mo | README claim |
|---|---|---|---|
| Cloud SQL `sig-pg` | 1 vCPU (≈ $0.0413/h) + 3.75 GB (≈ $0.007/GB-h) Enterprise, ZONAL; 15 GB SSD (≈ $0.17/GB); ~7–15 GB backups (≈ $0.08/GB) plus PITR logs | **≈ 52–54** | "`db-f1-micro` ~$9+" (the alternative); the e2-micro "DECISION" at $0 |
| global HTTPS LB | 2 forwarding rules (flat ≈ $0.025/h for the first 5) + ≈ $0.008/GB processed | **≈ 18.3** | not mentioned |
| `sig-api` min-instances 1 | 1 vCPU/0.5 GiB idle ≈ $0.0000025/vCPU-s + $0.0000025/GiB-s (less any free-tier offset) | **≈ 7–10** | "min-instances 0 → $0" |
| Cloud Scheduler | 79 jobs − 3 free × $0.10 | **7.60** | not mentioned |
| Cloud Run jobs | 8 monthly batches at 2 vCPU/8 GiB (≈ $0.19/h × 1–5 h) + ~60 small runs + 120 probe runs | **≈ 3–9** | not mentioned |
| Artifact Registry | ~11.7 GB (upper bound) − 0.5 GB free × $0.10 | **≈ 1.1** (grows ≈ 0.2 GB per build) | "~$0" |
| GCS | ≈ 6.2 GB standard × $0.020 | **≈ 0.12** | "$0" |
| egress | LB ≈ 0.9 GB/week at launch, now ≈ 0.1 GB/day | **≲ 0.5** | "~$0" |
| Secret Manager | 12 versions − 6 free × $0.06 | **≈ 0.36** | "$0" |
| logging, Cloud Build, `sig-web` scale-to-zero | within free tiers | ≈ 0 | — |
| **total** | | **≈ $90–100/mo** | "≈ $0/mo" (P24.1 table) and "~$9/mo" (the 2026-09-28 update) |

Cheaper options, for the Q-10 decision rather than as recommendations: replace the LB with Cloud Run domain mapping
or Firebase Hosting (−$18, loses the Cloud Armor option; F-9's `:443` redirect goes away with it); consolidate the
79 triggers into one hourly `due` dispatcher (−$7); set `sig-api` min-instances to 0 (−$7–10, brings back cold
starts; min 1 was set to fix timeouts); a Cloud SQL 1-year CUD (≈ −25 %, −$12); AR cleanup (−$1, stops growth).
**Denial-of-wallet:** `sig-public` (1.9 GB) and `sig-web` are world-readable. At ≈ $0.12/GB premium egress, a bot
pulling 1 TB/day costs ≈ $120/day with no rate limit and no verified budget alert. That makes QA-10 the priority,
with QA-7 and an optional Cloud Armor rate limit after it.

### 3.9 Security posture

- **Public invokers:** `sig-api`, `sig-web` and `sig-alerts` are `allUsers`. The first two are intended (a public
  read API and a public site). `sig-alerts` needs no public invoker: its caller is `sig-probe`, so authenticate it
  with IAM (G1-11). The API has RLS plus a read role (`store_pg.py:23,328`); its public-label nuance (D-P31.5-2) is
  already owed.
- **Identities:** G1-01 is the dominant security risk. **Blast radius today:** code execution in any ingest job
  (untrusted document parsing), in `sig-api` or in `sig-web` nginx yields project-Editor tokens from the metadata
  server. With those, an attacker can delete `sig-pg` (deletion protection off) and its backups, delete or overwrite
  all four buckets (7-day soft delete is the only net), and redeploy the public site. They could **not** read secret
  payloads (Editor lacks `secretmanager.versions.access`; accessor is granted per secret to the same compute SA, which
  **does** read `sig-pg-password` and the source API keys at runtime).
- **Secrets:** 11 secrets, all in Secret Manager, none in the repo (HG-09). `sig-api-env` has 0 versions (dead; delete
  or document). The Zenodo client secret and sandbox token exist without a consumer SA (operator-run).
- **MapRoulette key (accepted risk, G1-12).** Exposure: the value appeared in a session transcript (LEDGER line 145:
  "should be rotated (it appeared in the session transcript)"), so it may persist in local and vendor transcript
  stores. **Blast radius (inference from MapRoulette's API model; verify at rotation):** API actions as the
  operator's MapRoulette user, such as creating, editing or deleting challenges and tasks and changing task status
  under that identity, which is linked to the operator's OSM account. It is **not** an OSM write credential (OSM edits
  need the mapper's own OSM OAuth in an editor) and **not** a GCP credential. The main harm is reputational (organised
  editing on OSM, HG-08). **Controls:** unused, since `registered=false` and push refuses (exit 3); no GCP SA can read
  it. **Condition:** rotate before D-P21.7-1 activation, recorded as `rotated: yes` before any live push.
- **Project id (D-P30.4-4):** closed by ADR-119 (not a credential; leak check scoped to code and config). It is public
  anyway through bucket URLs. No action.
- **Network and DB:** Cloud SQL public IP with 0 authorized networks, reachable only through connectors. Moving to
  `ENCRYPTED_ONLY` is cheap hygiene. No Cloud Armor on the LB (optional, cost decision).

### 3.10 Runbooks: what exists and the gaps

| exists | covers | status |
|---|---|---|
| `docs/build/reports/GCP_DEPLOYMENT.md` | provision, secrets, Cloud SQL, deploy, the 09-15 5-claim drill, scheduled ops (pause/disable, read `ops/runs`), `sig-api` roll by digest plus rollback (§9) | the most useful; executed history; drill section is misleading at scale |
| `ops/gcp/README.md` | IaC file map, the e2-micro "DECISION", cost table ≈ $0 | **stale** (appended update, but the body and costs are wrong) |
| `docs/build/reports/INFRA_RUNBOOK.md` | P21.5 deposits, store, tiles, mirrors, degraded mode | mostly gate-pending machinery; not hosted ops |
| `docs/build/reports/CORRECTIONS_TAKEDOWN_RUNBOOK.md` | §36/§45 takedown procedure | content ops; needs a "republish now" hook to §3.6 |
| `docs/build/reports/REPUBLISH_LIVE_2026-09-27.md` + `runs/P31.16.md` | the de facto republish procedure plus rollback | a record, not a runbook; hand-typed rsync |
| `docs/build/reports/SUCCESSION.md` | continuity, mirrors | production Zenodo deposit still owed (D-P21.5-1) |

**Gaps, to become one `docs/ops/RUNBOOK.md` (or `ops/gcp/RUNBOOK.md`) with these sections (ticket, doc):** (1) *alert
received*: triage by probe target, and who is told; (2) *restore* (§3.1, both variants, with a drill record
template); (3) *republish* (§3.6, the one command, rollback); (4) *scheduled-window watch* (§3.7, generalised to any
first-fire or batch window); (5) *job failed*: re-execute, resume semantics, when to cancel; (6) *secret rotation*
(per secret: owner, consumer, how to roll the version and restart the consumer); (7) *roll* (`roll-jobs`, the
digest rule, fleet convergence); (8) *cost review* (monthly: billing export, budget, AR cleanup); (9) *decommission a
job or source*. **Doc fixes:** `ops/gcp/README.md` (mark §DECISION and the cost table superseded by ADR-081 and link
§3.8); `ops/README.md:96` ("WORM" → "append-only by convention; versioned per SIG-STORE-048" once it is true);
`docs/build/OPERATIONAL_READINESS.md:90` (the scheduling path is Cloud Scheduler, not `reingest.yml`).

---

## 4. Proposed requirement text (for S1/T1; ids provisional)

- **SIG-OPS-001 (MUST) — Restore drill.** The production claim spine MUST be restored from its managed backups (PITR
  and a full backup) into a new, isolated instance at least quarterly and after every schema-changing deploy. The
  drill MUST verify append-only row-count parity at the restore point for every spine table, MUST record measured RTO
  and RPO, and MUST delete the drill instance afterwards. A drill against a seed or fixture database does not satisfy
  this requirement.
- **SIG-OPS-002 (MUST) — Instance survivability.** The production database instance MUST have deletion protection
  enabled, MUST retain backups on instance deletion, MUST have a maintenance window outside scheduled batch windows,
  and MUST have a logical export stored outside the instance lifecycle at least monthly.
- **SIG-STORE-048 (MUST) — Evidence immutability in hosting.** The hosted OCFL capture store and the ops run and probe
  records MUST be protected against overwrite and deletion by a bucket retention policy or by object versioning with
  noncurrent retention of at least 90 days. Runtime identities that write captures MUST NOT hold object-delete. No
  document may call a store WORM unless such a control is in force.
- **SIG-OPS-003 (MUST) — Public route allow-list.** The public web origin MUST serve only routes on a committed
  allow-list. The publish tooling MUST refuse to sync a build containing any unlisted top-level route or any page
  built from internal or demo layouts. Each denied route MUST return 404 on every public origin, verified after every
  publish and every probe sweep.
- **SIG-OPS-004 (MUST) — Single publish path and release record.** The public site and public compartments MUST be
  published only by the repo-owned publish command. Hand-typed syncs to public buckets are prohibited. Every publish
  MUST write a release record (release id, git commit, image digests, dist tree digest), and every page MUST expose
  the release id.
- **SIG-OPS-005 (MUST) — Live-configuration reconciliation.** A read-only reconciler MUST compare the live scheduler,
  jobs, services, identities and bucket policies with their repo declarations (`ops/cadence.toml`, a manual-job
  allow-list, the declared posture) at least daily and alert on drift. Crons that restrict both day-of-month and
  day-of-week MUST be rejected unless explicitly annotated. Configuration MUST NOT require an image roll to take
  effect.
- **SIG-OPS-006 (MUST) — Alert delivery.** Every critical alert MUST reach a human channel (at minimum e-mail) within
  1 hour. A condition red for more than 24 hours MUST re-notify daily. The operator MUST be notified of any failed
  scheduled execution. Probes MUST cover the canonical public origin through the load balancer, including TLS
  certificate expiry, and not only platform URLs. A scheduled CI job that measured nothing MUST NOT report success.
- **SIG-OPS-007 (SHOULD) — SLOs.** The public site root and the API health endpoint SHOULD meet 99.5 % monthly
  availability, measured by external checks at intervals of 5 minutes or less, with a monthly error-budget readout.
- **SIG-OPS-008 (MUST) — Freshness.** While scheduled ingestion runs, the public site MUST be republished at least
  monthly, or earlier when claim drift exceeds 10 % or a source is added or withdrawn. The site MUST state its release
  id and as-of, and MUST disclose that the API may be newer. Materialized read models MUST be refreshed at least
  weekly.
- **SIG-OPS-009 (MUST) — Cost truth.** Measured monthly cost MUST be available (a billing export or equivalent) and
  compared against an operator-set ceiling with a budget alert. Documented cost claims MUST be measured, not
  projected.
- **SIG-OPS-010 (SHOULD) — Runbooks.** Hosted operations SHOULD have maintained runbooks for alert response, restore,
  republish, scheduled-window watch, job failure, secret rotation, roll, cost review and decommissioning.
- **SIG-SEC-007 (MUST) — Least-privilege runtime identities.** No Cloud Run service or job may run as a principal
  holding a basic role (Owner, Editor or Viewer). Each workload class MUST have a dedicated service account with only
  the roles it needs. Public-facing workloads MUST NOT hold delete permissions on the spine or evidence stores.
- **SIG-SEC-008 (MUST) — Digest pinning everywhere.** Every service and job MUST reference its image by digest (extends
  ADR-111 from jobs to services), and deployed code MUST be reproducible from the repository.
- **SIG-SEC-009 (SHOULD) — Secret lifecycle.** Each secret SHOULD have a recorded owner, consumer and last-rotation
  date. A secret known to be exposed MUST be rotated before its first production use.

---

## 5. Track-0-style quick actions (not executed; each needs its own operator go)

| id | action (sketch; verify flags at execution) | risk / reversal | closes |
|---|---|---|---|
| QA-1 | `gcloud sql instances patch sig-pg --deletion-protection` plus retain-backups-on-delete or a final-backup setting | metadata only; confirm the op is `UPDATE` with no restart; reversible | G1-03, A1 NEW-3 |
| QA-2 | `gcloud sql instances patch sig-pg --maintenance-window-day=SUN --maintenance-window-hour=9` | no restart to set it; reversible | G1-14, G1-08 |
| QA-3 | Monitoring: an e-mail notification channel to the operator; a log-based alert on `resource.labels.service_name="sig-alerts" textPayload:"SIG-ALERT"`; a metric alert on failed job executions | additive; delete to revert | G1-02 |
| QA-4 | uptime checks: `https://surveillancegraph.org/` and API `/health` (5 min, 3 regions) with alerting; SSL-expiry alert | additive | G1-02 |
| QA-5 | build an image from the commit carrying `48369305`'s `cadence.toml` and `roll-jobs` **`sig-probe` only** (digest, recorded) | small; rollback = previous digest from the roll record | G1-02, NEW-2 |
| QA-6 | `gcloud storage buckets update gs://…-sig-restricted --versioning` plus a lifecycle rule deleting noncurrent versions after 90 days | additive; cost cents | G1-05 |
| QA-7 | remove `allUsers:objectViewer` from `gs://…-sig-web` (site served through `sig-web`'s gcsfuse under its SA) | check `/`, `/tiles/…` (206) and `/map/` on both origins after the change; re-add to revert | G1-06, NEW-5 |
| QA-8 | `gh workflow disable reingest` (then a PR removing `schedule:`) | reversible (`enable`) | G1-09, A1 NEW-2 |
| QA-9 | the §3.1 PITR clone drill before 10-10 | creates and deletes a separate instance; ≈ $0.15–0.40 | G1-04 |
| QA-10 | a billing budget at the Q-10 ceiling with 50/90/100 % e-mail alerts (billing admin), plus a BigQuery billing export | additive | G1-10 |

Lower priority (operator go): delete the 6 cruft jobs (G1-17); relabel the 09-15 dumps (§3.1); `sslMode ENCRYPTED_ONLY`.

---

## 6. Routing suggestions for S1 (one disposition each, P9)

| item | suggested disposition |
|---|---|
| F-01 | `already-done(TRACK0_RECORD 0.1)`; the residual goes to G1-03/G1-04 |
| F-02 | `already-done(Track 0.2)` for the exposure; durable fix `ticket(<publish allow-list + single publish path>)` (G1-06, NEW-6) |
| F-08 | `ticket(<republish pipeline>)` + `operator-action(cadence/gate decision)` (G1-07, NEW-13) |
| F-11 | `merged-into(<publish release record>)`, jointly with G3 |
| F-12 | split: `:latest` → `ticket(<sig-alerts IaC or retire>)`; cron drift → `ticket(<live-diff + cron lint>)`; costs → `operator-action(Q-10)` + doc fix |
| F-13 | `live-return-pass(D-P31.4-1)` with the §3.7 watch plan |
| A1 NEW-2 | `operator-action(QA-8)` + an ADR superseding ADR-076's scheduling path |
| A1 NEW-3 | `operator-action(QA-1)` |
| A1 NEW-4 | `operator-action(delete 6 jobs)` + `ticket([manual_jobs] allow-list)` |
| G1 NEW-1…14 | per `findings/incoming/G1.csv` `routed_to` |

**Inputs for other rows:** I8 (capacity: disk 6.4 of 15 GB with autoresize, CPU peaks at 1.0 during
materialize/export, memory 0.70; job cost ≈ $0.19/h at 2 vCPU/8 GiB); G2 (activation must respect SIG-OPS-003
allow-list and the republish gate); G3 (release record, allow-list, rollback via bucket versioning); H2 (CI truth:
`observability.yml`).

## 7. Open questions for the operator

1. **Q-10:** the monthly infra ceiling, given ≈ $90–100/mo estimated today, and whether to trade the LB, min-instances
   or the scheduler count for cost.
2. Which e-mail address (or other channel) should critical alerts go to, and is a daily re-notify acceptable?
3. Should republishes with a "no new compartment, licence, route or sensitive category" diff be pre-authorized
   (standing go), or stay one go per republish?
4. Evidence retention: which period (e.g. 365 days, unlocked) should protect captures once they move to a dedicated
   bucket, and may it ever be locked?
5. Approve QA-1…QA-10 individually (Track-0 style), and the timing relative to the 10-01 first-fire wave.

## 8. New findings (proposed, `findings/incoming/G1.csv`)

NEW-1 all runtime identities are project Editor · NEW-2 probe red since 09-27, alerts reach nobody · NEW-3
`observability.yml` green while measuring nothing · NEW-4 buckets unversioned, no retention ("WORM" claim false) ·
NEW-5 `sig-web` bucket is a public third origin · NEW-6 root cause of the `/curate/` regression (refines F-02) ·
NEW-7 demo fixture task pages public · NEW-8 first-fire wave 10-01…10-21 untested · NEW-9 day-of-month + day-of-week
cron defects (refines F-12) · NEW-10 job fleet on 4 builds with config baked into images · NEW-11 cost ≈ $90–100/mo
vs ≈ $0/$9 claimed (refines F-12) · NEW-12 no Data Access audit logs; 30-day log retention · NEW-13 drift quantified
(refines F-08) · NEW-14 restore never tested at scale; seed dumps pose as backups.

---

## Appendix A — Command log (all read-only; project `zeta-medley-508121-u7` unless noted; times `date -u`)

| id | time (UTC) | command (abridged) |
|---|---|---|
| G1-C01 | 16:40:17 | `date -u`; `git branch --show-current`; repo reads (`sed`/`grep` of the files listed in the header) |
| G1-C02 | 16:41:21 | `gcloud storage buckets describe gs://<id>-{sig-backups,sig-public,sig-restricted,sig-web} --format=json` |
| G1-C03 | 16:41 | `gcloud storage ls -l -r gs://<id>-sig-backups/`; `gcloud storage ls gs://<id>-sig-restricted/{,ops/,evidence/,exports/,rollback/}` |
| G1-C04 | 16:41:48 | `gcloud storage ls -l "gs://<id>-sig-restricted/ops/runs/**"` (387 objects); `gcloud storage cat` of the 32 post-release run rows and 7 `camreg_osm_surveillance` rows |
| G1-C05 | 16:42 | `gcloud storage ls/cat gs://<id>-sig-restricted/ops/probes/…` (latest sweeps) |
| G1-C06 | 16:42 | `gcloud scheduler jobs list --location us-central1 --format=json` (79) |
| G1-C07 | 16:42 | `gcloud run jobs list --format=json` (88); `gcloud run jobs executions list --limit 400 --format=json` (343) |
| G1-C08 | 16:43 | job specs from G1-C07 JSON (`sig-probe`, `camreg-batch-05`, `sig-export`, `sig-materialize`, `sig-replay-ingest`; secret refs shown as refs only) |
| G1-C09 | 16:50 | `gcloud storage cp -r gs://<id>-sig-restricted/ops/probes/*` (60 sweep files; aggregated locally) |
| G1-C10 | 16:43 | `gcloud run services describe sig-alerts --format=json`; base64 program decoded locally (no secret in it) |
| G1-C11 | 16:44 | `gcloud run services describe {sig-api,sig-web}`; `gcloud run services get-iam-policy {sig-alerts,sig-api,sig-web}` |
| G1-C12 | 16:43:45 | `gcloud logging read '…service_name="sig-alerts" AND textPayload:"SIG-ALERT-RECEIVED"' --freshness=30d --limit 5` |
| G1-C13 | 16:55:58 | same filter, counted since 2026-09-27 (28) and over 30 days (48) |
| G1-C14 | 16:44 | `gcloud monitoring uptime list-configs`; `gcloud alpha monitoring policies list`; `gcloud beta monitoring channels list` (all empty); `gcloud logging sinks list`; `gcloud logging buckets list` |
| G1-C15 | 16:46 | `gcloud compute forwarding-rules list --global`; `ssl-certificates list`; `backend-services list --global`; `addresses list`; `instances list` |
| G1-C16 | 16:46 | `gcloud artifacts docker images list …/sig --include-tags`; `gcloud artifacts docker tags list …/sig-api` |
| G1-C17 | 16:46 | `gcloud artifacts docker images describe …/sig-api@sha256:d0ea2deb…`; `gcloud artifacts repositories describe sig` |
| G1-C18 | 16:45 | Cloud Monitoring `timeSeries.list` (HTTP GET): `cloudsql…/disk/bytes_used`, `cpu/utilization`, `memory/utilization` (15 d); `run…/request_count`; `loadbalancing…/https/request_count`, `response_bytes_count`; `storage…/total_bytes`, `sent_bytes_count` (7 d) |
| G1-C19 | 16:44 | `gcloud sql operations list --instance sig-pg --limit 60` |
| G1-C20 | 16:47 | `gcloud sql instances describe sig-pg --format=json` (backup, maintenance, IP and SSL fields) |
| G1-C21 | 16:45 | `gcloud projects get-iam-policy` (roles by member; operator account masked) |
| G1-C22 | 16:45 | `gcloud iam service-accounts list` |
| G1-C23 | 16:52 | `gcloud run jobs describe sig-probe` (SA); `gcloud scheduler jobs describe sig-sched-probe` (invoker SA); `gcloud run jobs get-iam-policy sig-probe` |
| G1-C24 | 16:48 | `gcloud storage buckets get-iam-policy gs://<id>-{sig-web,sig-public,sig-restricted,sig-backups}` |
| G1-C25 | 16:46 | `gcloud secrets list`; `gcloud secrets versions list <name>` (metadata only); `gcloud secrets get-iam-policy <name>` |
| G1-C26 | 16:49 | `gcloud logging read '…service_name="sig-web" AND httpRequest.status>=400' --freshness=1d --limit 300` (paths and UAs aggregated) |
| G1-C27 | 16:45 | `gcloud billing projects describe`; `gcloud billing budgets list` (**refused**: Budget API disabled in the quota project; nothing enabled); `bq ls` (no datasets); `gcloud services list --enabled` |
| G1-C28 | 16:52 | `gh run list --workflow observability --branch main --limit 1`; `gh run view 36713858053 --log` (grep) |
| G1-C29 | 16:47:58 | `curl -s -o /dev/null -w '%{http_code}'` for `/`, `/style-guide/`, `/visual-language/`, `/task/`, `/releases/`, `/research-dossier/`, `/intake/`, `/dispute/`, `/robots.txt`, `/sitemap.xml`, `/favicon.ico`, `/curate/`; `curl https://storage.googleapis.com/<id>-sig-web/index.html` (200) |
| G1-C30 | 16:48 | `gcloud storage ls "gs://<id>-sig-web/task/**"` (78 pages; slugs base64-decoded locally); `curl` of one demo task page (text only) |
