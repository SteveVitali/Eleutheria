# Launch record — SIG national public surface, 2026-09-24

> **What this is.** The dated record of what went public on 2026-09-24 (P30.3, PR #135, ADR-106), re-verified
> live by the post-launch closeout (P30.4, 2026-09-24 ~17:12Z, after the Cloud SQL scale-down, ADR-107).
> Every figure is a named-denominator count at a stated as-of time over an append-only spine. None is a
> population total or an estimate of the cameras that exist in the world (§3.1, §32 / SIG-METRIC-008).
> The launch *baseline* (pre-resolution settled numbers) is `LAUNCH_BASELINE_2026-09-24.md`, and the launch
> *execution* evidence is `docs/build/runs/P30.3.md#evidence-log`. This file does not repeat them. It records
> what the public can see, and its limits.

## 1. What is public

| surface | where | state (re-verified 2026-09-24 ~17:12Z) |
|---|---|---|
| public website | **https://surveillancegraph.org** (canonical) | 200; valid TLS: CN `surveillancegraph.org`, SAN apex + `www`, Google Trust Services WR3, valid to 2026-12-22; `sig-web-cert` ACTIVE; zero `<script>` on content pages |
| `www` | https://www.surveillancegraph.org | 301 → apex |
| run.app origin (fallback) | https://sig-web-e5ctyx36jq-uc.a.run.app | 200, byte-identical content (same `…-sig-web` bucket) |
| serving path | apex/`www` A → `136.81.80.102` (Google DoH) → external HTTPS LB → serverless NEG → Cloud Run `sig-web` (nginx over a gcsfuse mount of `…-sig-web`; ADR-098) | the site does **not** read the database; a DB restart does not affect it (a real public request was served 200 mid-restart at 17:04:58Z) |
| licence-separated downloads | `https://storage.googleapis.com/$SIG_GCP_PROJECT-sig-public/` (`manifest.json`, `LICENCES.json`, one directory per compartment) | 128 public artifacts; `restricted` bucket anonymous → 403 |
| public read API | https://sig-api-e5ctyx36jq-uc.a.run.app (`/v1/…`) | green on `probe-hosted`; see the limitations in §4 |

`probe-hosted` (2026-09-24T17:12:19Z, all 7 targets `ok`): `sig-api-root`, `sig-api-coverage-okc`,
`sig-web-root` (surveillancegraph.org and run.app), `sig-public-{okc,france,national}-manifest`, `sig-pg-cloudsql`.

## 2. Release, watermark and headline

- **Release:** `sig-2026-09-24-bd01cb94` (content key `bd01cb9418b2dfb4…a85082`); `as_of_snapshot` /
  `as_of_belief` 2026-09-24; ruleset `p27.3/1.0.0`. Built in GCP by `sig-export-tl4mx`
  (15:41:10Z→15:51:41Z) from one `REPEATABLE READ READ ONLY` snapshot.
- **Spine watermark:** 2,304,784 claims (latest assertion 2026-09-24T06:10:05Z; `pg_stat` upd/del on
  `claim` = 0); 247,061 entities (estimate); camera-site run `camsite:13bedfe7…` (completed 11:37:00Z).
  Re-read on 2026-09-24 ~17:15Z: 2,304,784 claims, unchanged.
- **Headline (published verbatim):** *"227998 resolved sites (from 230330 observation-level records; dedup
  ratio 0.010)"*, with the provisional-evaluation disclosure (*"provisional eval (LLM-bootstrapped gold set;
  D-R6.1-EVAL, OPEN)"*). Present on both origins.
- **Map** (P30.3 figure; `/map/points.json` re-fetched by P30.4 at the same size): 225,105 tier-0 camera points drawn from `/map/points.json` (17,143,416 B), with the attribution
  "© OpenStreetMap contributors (ODbL) · Surveillance data © SIG contributors".
- **Other materialized numbers on the surface** (as published by P30.3's export; the served files are
  unchanged since then): 1 open of 1 recorded contradiction (the OKC
  `claimed_device_count` 299-vs-190); provenance completeness 2,280,784 of 2,280,784 published tier-0 claims;
  116 reconciliation ratios (each with a named denominator); 1 research task (`conflicting_retention`), with
  its records-request draft **not sent**.

## 3. Compartments and licences (from the live `LICENCES.json`)

Every downloadable compartment carries exactly one licence (ADR-106; `assert_public_clean`). Share-alike
compartments are published as their own attributed downloads and are never merged into the CC-BY graph.

| compartment | licence | share-alike | public site rows (P30.3) |
|---|---|---|---|
| `osm_physical` | ODbL-1.0 | yes | 154,705 |
| `public_record` | LicenseRef-PublicRecord-FactualCompilation | no | 38,484 |
| `operator_accepted` | LicenseRef-OperatorAccepted-DBRight | no | 21,682 |
| `portal` | CC-BY-SA-4.0 | yes | 10,052 |
| `sig_graph` | CC-BY-4.0 | no | 3,978 |
| `dot511_ccbysa2` | CC-BY-SA-2.0 | yes | 3,000 |
| `ogl_uk3` | OGL-3.0 | no | 1,514 |
| `ccby3` | CC-BY-3.0 | no | 861 |
| `ogc_canada2` | OGL-Canada-2.0 | no | 160 |
| `ottawa_odl2` | LicenseRef-Ottawa-ODL-2.0 | no | 146 |
| `stalbert_odl1` | LicenseRef-StAlbert-ODL-1.0 | no | 80 |
| `peel_odl1` | LicenseRef-Peel-ODL-1.0 | no | 37 |
| `web`, `metadata` | CC-BY-4.0 | no | (site build + manifest) |

Restricted (private): the mixed-licence build input `web/map.json` only. 0 UNDETERMINED / excluded bytes are public.
All 234,699 of 234,699 public rows are sensitivity tier 0, and there are no person or plate fields (Part VIII).

**Operator-ACCEPTED deviation.** `/map/points.json` is the site's map-rendering file. It mixes all 12 data
compartments in one file with no per-row licence field. That goes against the "no mixed-licence artifact in
any public object" condition. The operator accepted it on 2026-09-24: *"Keep it; counsel covers it."* The
acceptance covers only this one file, and it is carried in D-P30.3-COUNSEL. See
`docs/build/readouts/ACCEPT-R8.md`.

## 4. Known limitations (published honestly, each with an owed deferral)

- **No relationship edges or accountability links.** 0 of 2,304,784 hosted claims carry an entity reference
  (`object_entity`), so the network surface shows its empty state (**D-P30.2-2**).
- **Freshness not recorded.** All 20 hosted `ingest_run` rows are still open (`finished_at` NULL), so the
  178 sources show `not-recorded` dates on `/data-freshness/` (**D-P30.3-1**).
- **No zoomable tiles.** Per-compartment PMTiles are single-z0 (no tippecanoe in the export image). There is
  no OSM basemap, and the map draws from the 17 MB `points.json`, served uncompressed (**D-P30.3-2**).
- **No map or network analytics.** Density bins, centrality, the watch decision point and the evidence tiers
  are not emitted by the export, so those surfaces show empty states and not the demo constants
  (**D-P30.3-3**, extends D-P27.5-1).
- **The resolution evaluation is PROVISIONAL.** It rests on an LLM-bootstrapped gold set. The camera-site LLM
  κ is 0.669, below the 0.70 bar, so the LLM is a suggester only (ADR-105). 11,625 proposals wait for human
  review and 0 have been decided (**D-R6.1-EVAL**, **D-P30.2b-1**).
- **Read API limits.** A broad `/v1/search` term exceeds the request timeout (**D-P30.4-2**). The API does
  not reconnect after a DB restart (**D-P30.4-1**).
- **Governance posture.** Counsel clearance for the share-alike layers is operator-reported, with no written
  opinion on file (**D-P30.3-COUNSEL**). The project runs under a sole-maintainer reviewer posture with the
  independence requirement waived (D-P21.4-2). Contribution-back is not activated (**D-P21.7-1**), and records
  requests are drafted but never sent (**D-R7.2-SEND**).

## 5. Hosting state after launch

`sig-pg` was scaled `db-custom-2-8192` → **`db-custom-1-3840`** at 2026-09-24T17:04Z (`RUNNABLE` 17:09Z;
ADR-107; estimated compute ≈ $101 → ≈ $49/month, list price). `sig-api` was recycled on its pinned digest
(`sig-api-00004-jdj`, `sha256:cc680111…`). Both public URLs and `probe-hosted` were green after the restart.
