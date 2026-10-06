# Track 0 record — operator-approved production actions (outside planning)

Authority: GATE-M, operator verbatim (META_PLAN §7.1): *"I approve backups and removing curate."*
Executor: Claude Code planning orchestrator. All times `date -u`.

## 0.1 — Cloud SQL `sig-pg` backups (F-01)

| step | time (UTC) | command (project `zeta-medley-508121-u7`) | result |
|---|---|---|---|
| pre-state | 16:17 | `gcloud sql instances describe sig-pg` | `backupConfiguration.enabled: false`; 0 backups listed |
| on-demand backup | 16:18:31 → 16:20:43 | `gcloud sql backups create --instance=sig-pg --async` (op `7ad3efa3-…0032`) | backup id `1790785111976`, `ON_DEMAND`, `SUCCESSFUL` |
| enable automated backups | 16:21:04 → 16:21:05 | `gcloud sql instances patch sig-pg --backup-start-time=05:00 --async` (op `5f436e0d-…0032`) | `enabled: True`, window 05:00 UTC, 7 retained; operation type `UPDATE` only — **no restart**; `sig-api /health` 200 before (0.12 s) and after (0.09 s); site `/` 200 |

**Point-in-time recovery (PITR).** Enabling PITR on an existing Cloud SQL PostgreSQL instance **restarts the
instance** (Google Cloud docs, "Configure point-in-time recovery"), so it was held and asked. Operator, verbatim
(2026-09-30): *"I'll leave the point-in-time recovery question to you."* Agent decision: enable, in a quiet window.

| step | time (UTC) | command / check | result |
|---|---|---|---|
| window check | 16:28:33 | `gcloud scheduler jobs list` (next fire times); `gcloud run jobs executions list` (running) | 0 running executions; next scheduled job `sig-sched-probe` at 18:00:02Z |
| enable PITR | 16:28:45 → 16:31:41 | `gcloud sql instances patch sig-pg --enable-point-in-time-recovery --retained-transaction-log-days=7 --async --quiet` (op `00f4b787-…0032`, type `UPDATE`) | `pointInTimeRecoveryEnabled: True`, log retention 7 days, state `RUNNABLE` |
| availability during restart | 16:28:51 → 16:31:49, polled every ~16 s | `curl $SIG_API/health` | one `503` at 16:29:42; `200` again at 16:29:58 with no redeploy (the ADR-108 reconnect held); `/v1/contradiction` 200 and site `/` 200 after |

The restore drill (restore to a new instance, verify, delete) is planned in G1.

## 0.2 — Remove `/curate/` from the public web surface (F-02)

| step | time (UTC) | action | result |
|---|---|---|---|
| inspect | 16:21 | `gcloud storage ls -l gs://zeta-medley-508121-u7-sig-web/curate/**` | 8 static demo pages, 23,494 bytes, uploaded 2026-09-27T01:33:56–57Z (the P31.16 republish sync) |
| preserve | 16:21 | copied to `docs/build/logs/next-phase/track0/curate-backup/` (gitignored) | 8 files |
| inbound links | 16:21 | grep of `/`, `/dossier/`, `/methodology/`, `/corrections/`, `/dispute/` for `href="/curate` | 0 links (removal breaks no navigation) |
| delete | 16:21:34 | `gcloud storage rm gs://zeta-medley-508121-u7-sig-web/curate/**` | bucket prefix empty |
| verify | 16:22 | `curl` `/curate/`, `/curate/submit/`, `/curate/tasks/` on `https://surveillancegraph.org` and `https://sig-web-e5ctyx36jq-uc.a.run.app` | all **404**; home 200 on both origins |

**Residual risk (routed to G1):** the next republish (`web/dist` sync) will re-upload `curate/` unless the publish
exclusion is fixed and regression-tested. Other routes that may be internal-only (`/style-guide/`,
`/visual-language/`, `/task/`) were not touched — they are for C2 to assess.

## 0.3 / 0.4
- 0.3 (MapRoulette key rotation) — operator, verbatim (2026-09-30): *"MapRoulette key can stay stale for now."* Recorded; no action (routed to G1 secret hygiene as a known accepted risk).
- 0.4 — answered at GATE-M: no merge; Round 11 builds on the chain.

## 0.5 — Minimal alerting (operator-approved 2026-10-01T00:09:20Z)

Authority: operator, verbatim: *"yes you can set up minimal alerting now to 14stevevitali@gmail.com"* (asked because 0 alert
policies / 0 notification channels existed while the first-run schedule wave starts 2026-10-01 and the OSM replay runs 10-10).
Scope taken: alerts only — the optional restore drill was **not** included in the approval and was not done (stays a Round-11 ticket).

| resource | id | detail |
|---|---|---|
| notification channel (email → the operator's address) | `notificationChannels/10808426210098728267` | "SIG operator email (Track 0.5)" |
| uptime check — site | `uptimeCheckConfigs/sig-site-surveillancegraph-org-F2yZbTB73dw` | HTTPS GET https://surveillancegraph.org/ every 5 min, 10 s timeout |
| uptime check — API | `uptimeCheckConfigs/sig-api-health-or4_q7yICx4` | HTTPS GET https://sig-api-e5ctyx36jq-uc.a.run.app/health every 5 min |
| alert policy — job failures | `alertPolicies/7285515107319155929` | `run.googleapis.com/job/completed_execution_count` result=failed > 0 per job / 5 min; **excludes `sig-probe`** (fails every sweep since 09-27 — stale baked-in config; Round-11 fix) ; auto-close 30 min |
| alert policy — disk | `alertPolicies/10812940548821947108` | `cloudsql.../disk/utilization` > 0.85 for 10 min on sig-pg (15 GB, auto-resize ON, no limit) |
| alert policy — site uptime | `alertPolicies/10812940548821949519` | check failing from >1 region (20-min window) |
| alert policy — API uptime | `alertPolicies/1149999306662850342` | same |

Recent failure context (last 40 executions): sig-probe 12 failures; one failure each for sig-ingest-sam-gov, raa-prefectures,
procportal-sf-ca, procportal-nyc-ny, procportal-kcmo-mo, procportal-austin-tx, osm-overpass, openstates, decp-fr — future
failures of these will now email the operator. Cost: small (4 alert conditions + 2 uptime checks); Google's pricing page could not
be parsed to quote an exact figure — the Round-11 budget-alert ticket makes it visible. One retry: the disk policy's first filter
ordering was rejected by the API ("matches more than one metric"); re-ordered (metric.type first) and created.

## Addendum — GATE-P answers on Track-0 candidates (appended 2026-10-01T07:25:50Z)

At GATE-P (`feedback/RATIFICATION_LOG.md`, rounds 1–2) the operator declined every further Track-0 action:
A-0.1 (repo-tip handle strings) → *"No, wait for P34.18"*; A-0.2 (09-27 release tree in `sig-public`) → *"No, wait for
P34.21"*; A-0.3 (`/visual-language/` + handle-bearing pages) → *"No, wait for republish"*; A-1 (QA-9 restore drill + TLS-expiry
alert) → *"None now; ticket it"*; A-2a (budget alert + billing export) → *"Infra only; alert later"* (P34.5). These exposures
are **unresolved, operator-deferred** (not accepted risks), owned by early-11A rows. A-0.4 (git history) → *"Accept and
disclose"*: history is retained and disclosed in P34.18's correction note. No production change was made after Track 0.5
(minimal alerting, 2026-09-30) other than the operator-approved, local-only C-10 inspection of the stopped container
`sig-p332-db` (no production contact).
