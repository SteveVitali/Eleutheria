# ADR-107 — Cloud SQL steady-state tier after launch: `db-custom-1-3840`

- **Status:** Accepted
- **Phase / ticket:** Phase 30 / P30.4 (`docs/tickets/P30.4__post-launch-closeout.md`) — Round 8 `GO-LIVE.4`, the post-launch closeout; the ticket this ADR is owned by and lands with.
- **Date:** 2026-09-24
- **Related:** **ADR-102** (the temporary `db-f1-micro` → `db-custom-2-8192` scale-up for the OSM land; its revisit trigger — "when P30.4 scales `sig-pg` back down" — is what this ADR answers; ADR-102's body is not edited), ADR-075 (the original zero/low-cost hosting posture), ADR-103 (materialization runs in GCP next to Cloud SQL), ADR-106 (the static public site is bucket-served, not DB-served); deferrals **D-P30.1-1 / D-P30.1-2** (the write-path throughput root cause), **D-P30.4-1** (the read API does not reconnect after a DB restart); backlog home **BL-057**.

## Context

ADR-102 recorded the operator-approved temporary scale-up of `sig-pg` to `db-custom-2-8192` (2 vCPU /
8 GB) for the OSM land, and made P30.4 the owner of the scale-back. By P30.4 the national site is live
(P30.3, release `sig-2026-09-24-bd01cb94`). What still reads the database at steady state:

- **The public website does not.** `sig-web` is nginx over a gcsfuse mount of the `…-sig-web` bucket
  (no Cloud SQL binding), so the public pages are unaffected by the DB tier or a DB restart.
- **`sig-api`** (Cloud Run, max 2 instances, 1 vCPU / 512 MiB) — the public read API: point reads by
  entity / claim / resolution, plus a few list endpoints.
- **Batch jobs**: `sig-probe` (every 6 h), monthly scheduled ingests (incl. the ~1.37M-record
  `camreg_osm_surveillance` replay, `sig-sched-camreg-batch-05`, the 10th of each month, 36 h task
  timeout), `sig-materialize` and `sig-export` when an operator re-runs them.

The original tier, `db-f1-micro` (shared core, 0.6 GB), was measured I/O- and memory-starved even
before the OSM land: memory utilization pinned at 1.0 through 2026-09-23 and ~400–470 inserts/min
(ADR-102 §Context). The database is now 4.37 GB (2,304,784 claims).

Measured on 2026-09-24 over `cloud-sql-proxy` from the operator's laptop (every statement
`READ ONLY`; the ~55 ms figures are dominated by the laptop→us-central1 round trip), same queries
before and after the change:

| probe (median) | `db-custom-2-8192` | `db-custom-1-3840` (warm) |
|---|---|---|
| resolve identifier → entity | 91 ms | 108 ms |
| entity by id | 65 ms | 59 ms |
| claims for (subject, predicate) + evidence join | 59 ms | 54 ms |
| all claims for one subject | 59 ms | 58 ms |
| narrow `ILIKE` identifier search | 363 ms | 436 ms |
| `count(*)` over `claim` (full scan) | 3.20 s | 3.41 s |
| claims per predicate (full aggregate) | 3.46 s | 3.91 s |
| `sig-api` `GET /v1/contradiction` (heaviest list endpoint) | 8.0 s (1 sample) | 10.7–11.2 s |
| `sig-api` `/v1/changes`, `/v1/crosswalk`, `/v1/coverage/national` (warm) | 0.19–0.62 s | 0.16–0.23 s |
| cold figures after the restart (first run on a new tier / new revision) | — | per-predicate aggregate 4.72 s; `/v1/coverage/national` 15.9 s (cold start + warmup) |

Cloud Monitoring, hourly max. On `db-custom-2-8192` (from 2026-09-23T22:25Z): CPU 7–50 %, with peaks during the
P30.2 materializations and the P30.3 export. Memory was ~3.9 GB in use, of which ~2.6 GB was `shared_buffers`
(Cloud SQL sizes it as a fraction of the tier's RAM), with one peak of 5.57 GB at 07:58Z during a
materialization. Before 22:25Z the same window was `db-f1-micro`, with memory utilization pinned at 1.0. **After
the change** (10-min max, 17:22–17:32Z): memory 2.03 GB in use (utilization 0.53 of 3.75 GB; `shared_buffers`
is now 1,222 MB) and CPU 9–51 % (the 51 % peak was the P30.4 verification scans themselves). The steady-state
footprint therefore fits the new tier. A heavy full-spine job (materialization, export) will lean on the page
cache more than it did on 8 GB; that is the reason for the revisit trigger below.

## Decision

1. **`sig-pg` steady-state tier = `db-custom-1-3840`** (1 dedicated vCPU / 3.75 GB, Enterprise edition,
   zonal, 15 GB PD-SSD unchanged). Patched `--quiet` at 2026-09-24T17:04:04Z, `RUNNABLE` at 17:09:02Z.
   Cloud SQL resized `shared_buffers` 2,648 MB → 1,222 MB and `max_connections` 400 → 100.
2. **Why not smaller.** `db-f1-micro` is the tier that was measured starved. `db-g1-small` (1.7 GB,
   **shared** core) keeps the shared-core CPU throttling and roughly doubles f1-micro's memory, but that
   is still below the hot index set of a 4.4 GB spine, and shared-core tiers have no Cloud SQL SLA. The
   workloads that hurt f1-micro (a monthly 1.37M-record OSM replay; full-spine reads by the exporter and
   the materializers) have not changed. `db-custom-1-3840` is the smallest **dedicated-core** tier, and
   the table above shows point reads unchanged and full scans ~7–13 % slower.
3. **Why not stay at 2-8192.** Nothing at steady state uses the second vCPU or the extra memory: the
   public site is bucket-served, `sig-api` traffic is light, and the heavy jobs are occasional batch runs
   that tolerate a slower scan.
4. **Cost (list-price estimate, us-central1 Enterprise, 730 h/month, compute only).** The Cloud Billing
   catalog API is not enabled on the project, so these figures are not a billing readout. Using
   $0.0413 per vCPU-hour and $0.0070 per GB-hour: `db-custom-2-8192` ≈ **$101/month** →
   `db-custom-1-3840` ≈ **$49/month** (about $52/month saved). For comparison: `db-g1-small` ≈ $26 and
   `db-f1-micro` ≈ $8. Storage (15 GB SSD ≈ $2.55), backups and egress are unchanged and excluded. The
   operator's billing console is the authoritative figure.
5. **Restart handling.** A tier change restarts the instance. `sig-api` holds one long-lived psycopg
   connection per instance and does **not** reconnect: after the restart every DB-backed endpoint
   returned 500 (`psycopg.OperationalError: server closed the connection unexpectedly`) until the
   instances were recycled. Observed: `/v1/coverage/national`, `/v1/crosswalk` and `/v1/contradiction` all
   returned 500. `/v1/changes` still returned 200 because it does not query the database
   (`PgReadStore.captures()` returns an empty list). To recycle them, the service was redeployed **pinned to the digest it was
   already serving** (`sig-api@sha256:cc680111…`, revision `sig-api-00004-jdj`). A first attempt that
   only updated a label rolled the service's `:latest` tag to a newer image (`sha256:ebb6dab9…`,
   revision `sig-api-00003-ffl`, served for about 1–2 minutes). It was replaced at once so that the
   restart did not change the running code. The missing reconnect is **D-P30.4-1**.

## Consequences

- Estimated hosting cost for the database falls by about half, and the instance stays on a
  dedicated core with an SLA.
- The public website did not notice the restart. A real public request
  (`/dossier/ps/`, 17:04:58Z) was served 200 mid-restart, and `sig-web` logged no 5xx. After the change,
  `probe-hosted` was green on all 7 targets, including `sig-pg-cloudsql` and both `sig-api` targets.
- The monthly `sig-sched-camreg-batch-05` OSM replay runs on 1 vCPU. The row-at-a-time sink is bound
  by round-trip latency, not CPU (ADR-102, D-P30.1-1), and the task timeout is 36 h, so it is expected
  to fit. The first run on this tier (2026-10-10) is the check.
- Any future DB restart (maintenance window, tier change) takes `sig-api` DB endpoints down until its
  instances recycle, until D-P30.4-1 lands. Recycling means redeploying the pinned digest, never
  `:latest`.

## Alternatives considered

- **`db-g1-small`.** Cheapest non-micro tier. Rejected because it is shared-core with no SLA and has
  1.7 GB of memory, which does not change the conditions that starved f1-micro. It was not measured,
  because each tier change restarts the database and takes `sig-api` down (D-P30.4-1).
- **Return to `db-f1-micro`.** Rejected: that tier was measured starved (ADR-102).
- **Keep `db-custom-2-8192`.** Rejected: about $52/month more for capacity that only the one-off
  launch jobs used.
- **Schedule the scale-down for a quiet window.** There is no meaningful public DB traffic (the site
  is bucket-served), so an immediate patch cost nothing measurable.

## Revisit trigger

Revisit if any of these happens:

- the 2026-10-10 (or any later) `sig-sched-camreg-batch-05` OSM replay fails or nears its 36 h
  deadline;
- `sig-api` warm point reads regress past ~2× the table above, or a list endpoint starts hitting the
  Cloud Run request timeout;
- a large land, re-materialization or re-export is planned. Scale up temporarily as in ADR-102,
  record it, and scale back.
- D-P30.1-1 / D-P30.1-2 land. A batched sink may then allow `db-g1-small`; measure it before
  deciding.
