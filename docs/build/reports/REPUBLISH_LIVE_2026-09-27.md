# Republish record — P31.16 post-HG-11 publish (live evidence)

> **What this is.** The RETURN PASS record of `P31.16` (SURFACE.3): after the
> operator's HG-11 sign-off (commit `81957c2`, recorded 2026-09-27), the recorded
> restricted export `sig-2026-09-27-ce480ab1` was partitioned, its public half
> published, `web/dist` synced to the site bucket, `sig-web` rolled to the
> repo-owned image by pinned digest, and the mixed-licence `/map/points.json`
> retired. Every line below is measured live evidence, not a plan.
>
> Companion documents: the pre-gate diff `REPUBLISH_DIFF_2026-09-27.md`, the
> launch baseline `LAUNCH_RECORD_2026-09-24.md`, run ledger
> `docs/build/runs/P31.16.md`.

## 0. What was published

| | value |
|---|---|
| release | `sig-2026-09-27-ce480ab1` |
| content key | `ce480ab1134c178964aaac492395bc78ace7ee01357b2c6f2a1887700c9682c2` |
| watermark | **2,423,200 claims**, as_of world/belief `2026-09-27`, ruleset `p27.3/1.0.0` |
| export job | `sig-export-sv49f` on `sig-api:export-61701df303c3` @ `sha256:1cccde1a…` |
| stamped restricted export (retained, private) | `gs://zeta-medley-508121-u7-sig-restricted/exports/national/2026-09-27T005153Z/` |
| public compartment | 132 artifacts / ~1.0 GB → `gs://zeta-medley-508121-u7-sig-public/` (bucket root) |
| restricted compartment refresh | 3 objects (`web/map.json` 59.9 MB, `web/analytics/density_bins.json`, `manifest.json`) → `gs://zeta-medley-508121-u7-sig-restricted/` root |
| site | `web/dist` (216 export-mode pages + 12 compartment PMTiles) → `gs://zeta-medley-508121-u7-sig-web/` |

Prepare proof (before any byte moved): `sig-ops deploy --prepare-only` —
`SIG_DATA_SOURCE=export` build + `partition_export` + `assert_public_clean` +
`assert_site_matches_partition` all green (132 public / 2 restricted; one
licence per public artifact; no UNDETERMINED/mixed byte in the public tree).

## 1. Sync commands run (2026-09-27T01:29–01:35Z)

```
gcloud storage rsync -r exports/out/restricted/ \
    gs://zeta-medley-508121-u7-sig-restricted/            # retain (no delete)
gcloud storage rsync -r --delete-unmatched-destination-objects \
    exports/out/public/ gs://zeta-medley-508121-u7-sig-public/
gcloud storage rsync -r --delete-unmatched-destination-objects \
    web/dist/          gs://zeta-medley-508121-u7-sig-web/
```

The public sync's delete pass removed the stale launch-shape objects
(`okc/`, `france/` slice compartments — absent from the 2026-09-27 export —
and the superseded `web/` files). The web sync's delete pass retired
`map/points.json` itself (see §4).

## 2. `sig-web` roll (repo-owned image, pinned digest)

| | before | after |
|---|---|---|
| revision | `sig-web-00001-7fz` | `sig-web-00002-5nw` |
| image | stock `nginx:1.27-alpine` (hand-made P30.3 service) | `us-central1-docker.pkg.dev/zeta-medley-508121-u7/sig/sig-web@sha256:d8244804eb4fa7db5b0ebe25f0177f4270409e3a6d5f484418efcd03b086ee2b` (tag `5c0648812053`, Cloud Build `39650b28…`, 1m20s) |
| port / mount | 80 / volume `site` → `/usr/share/nginx/html` | 8080 / gcsfuse volume `sig-web` → `/mnt/sig-web` (the shape `ops/web/nginx.conf` serves) |
| traffic | — | 100 % at 2026-09-27T01:31Z; site served 200/206 throughout |

`ops/gcp/web.sh --apply service` read the live service spec and removed the
actual mount (`/usr/share/nginx/html`) and volume (`site`) by their live-read
names before declaring the repo-owned shape — the fix this branch carries,
since the hand-made service never had the mount names the script originally
hardcoded. Never `:latest`; the deploy names the digest.

**Rollback (recorded before the roll):**
`gs://zeta-medley-508121-u7-sig-restricted/rollback/sig-web-pre-republish-2026-09-27T0000Z/`
— a full copy of the site bucket plus `service-pre-roll.yaml` /
`service-post-roll.yaml`. Restoring = `gcloud run deploy` the pre-roll spec
(stock image + `site` mount) and `gcloud storage rsync` the prefix back over
the site bucket.

## 3. Live verification (both origins unless noted)

| check | result |
|---|---|
| `GET /` | **200** (85,844 B) — homepage carries `223901` resolved sites |
| every public route | 200: `/map/ /network/ /search/ /dossier/ /watch/ /evidence/ /corrections/ /contribution-back/ /coverage-metrics/ /data-freshness/ /research-queue/ /methodology/ /dispute/ /editorial-standards/ /visual-language/ /style-guide/`; `/task/` is a namespace (no index page — 403 on both old and new service; its `/task/new/<id>/` detail pages serve 200) |
| `/data-freshness/` | **178/178 sources `ok` with real ISO `last_successful_run`** (2026-09-17 → 2026-09-26); the only `not-recorded` token is the legend note + `camreg_camilo_schools`'s honest content-change gap |
| `/network/` | 200; public `web/network.json` = **130 typed `configured_access` edges / 131 nodes** (was 0 at launch); accountability `has_vendor` links render in the live `/dossier/al/` "Accountability events" section |
| `/coverage-metrics/` | 200; watermark `2,423,200 of 2,423,200` + named-denominator analytics; 0 `not-recorded` strings |
| `/map/` | 200 (3.46 MB); `/map/style.json` names **12 compartment PMTiles sources** (`sig_ccby3` … `sig_stalbert_odl1`) — the map draws only from the public compartment |
| PMTiles | `GET /tiles/sig_graph-sites.pmtiles` with `Range: bytes=0-99` → **206**, `Content-Range: bytes 0-99/725922`, `application/vnd.pmtiles` — real z0–z14 archives serving ranges |
| compression | `Accept-Encoding: br` → `content-encoding: br`; `gzip` likewise (repo nginx image, brotli built from source) |
| `/research-queue/` | 200 (689 KB) — see §5 defect note |
| PROVISIONAL disclosure | present on `/` + `/methodology/` — "provisional eval (LLM-bootstrapped gold set; D-R6.1-EVAL, OPEN)" — unchanged, still owed |
| restricted privacy | anonymous GET of stamped `web/map.json` **and** refreshed `web/map.json` → **403** |

## 4. `/map/points.json` retirement (closes the R8-1 live half)

| origin | before | after |
|---|---|---|
| `https://surveillancegraph.org/map/points.json` | 200 (17,143,416 B) | **404** (146 B) |
| `https://sig-web-e5ctyx36jq-uc.a.run.app/map/points.json` | 200 (17,143,416 B) | **404** (146 B) |

The object is gone from `…-sig-web` (`gcloud storage ls` → no match) and no
`points.json` exists anywhere under `…-sig-public`. The mixed 12-compartment
`web/map.json` (59.9 MB) stays private in the restricted bucket. R8-1 is
recorded CLOSED in `docs/build/readouts/ACCEPT-R8.md`.

## 5. Defects found and fixed during the publish half

1. **`/research-queue/` 500'd at scale.** The export-mode page rendered all
   243,761 task cards into one **317 MB** HTML — over Cloud Run's response cap
   (nginx logged `200 ~33.9 MB` then the serving layer cut it). The page never
   applied the P27.5 `capRows` guard. Now renders the first 500 cards in queue
   order with an honest "first 500 of 243761" note naming the full
   `web/research_queue.json` artifact; empty-string jurisdiction displays
   "Unscoped". Live 200 at 673 KB. (`web/src/pages/research-queue.astro`)
2. **`web.sh` hardcoded the wrong mount names.** The live service mounted the
   bucket as `site` → `/usr/share/nginx/html`; the script removed `sig-web` /
   `/mnt/sig-web` — names that exist only *after* a roll. `do_service` now
   removes every live volume-mount + volume by its live-read path/name, then
   declares the repo-owned shape — clean on first roll, idempotent on re-roll.
3. **Two `probe-hosted` targets probed launch-shape compartments** that the
   2026-09-27 export no longer carries (`okc/manifest.json`,
   `france/manifest.json` — per-compartment manifests aren't emitted at all).
   Replaced by `sig-public-licences` (`LICENCES.json`) and
   `sig-public-compartment-sites` (`peel_odl1/sites.csv`) in `ops/cadence.toml`.

## 6. `probe-hosted` + `sig-api` + `sig-pg`

`SIG_PROBE_WEB_URL=https://surveillancegraph.org SIG_PROBE_API_URL=<run.app>
SIG_GCP_PROJECT=zeta-medley-508121-u7 sig-ops probe-hosted` — **all seven
resolvable targets green**: `sig-api-root`, `sig-api-coverage-okc`,
`sig-api-health` (pooled `SELECT 1` — healthy post-publish), `sig-web-root`,
`sig-public-licences`, `sig-public-compartment-sites`,
`sig-public-national-manifest`. `sig-pg-cloudsql` skipped (needs the job-env
socket DSN, expected). `sig-pg` tier = **`db-custom-1-3840`** — ADR-107 steady
state restored after the pre-gate scale-up; `sig-api` rode through both
restarts on one revision (recorded in the run ledger).

## 7. Deferral dispositions (see `docs/tickets/DEFERRALS.md`)

- **D-P30.3-1 → DONE** — `/data-freshness/` shows real ISO dates for all 178
  sources (the verification rule, now live).
- **D-P30.3-2 → DONE** — real z0–z14 compartment PMTiles serve over range
  requests; the map draws from the tiles, not the retired `points.json`;
  R8-1 CLOSED.
- **D-P30.3-3 → DONE** — the export-emitted analytics family (`web/analytics/`
  centrality / decision_point / provenance / queue_meta + the refreshed
  surface artifacts) is live publicly.
- **D-P30.2-2 → DONE** — the public-appearance half: 130 edges live on
  `/network/` + `web/network.json`; `has_vendor` accountability links render
  in live dossier sections.
- **D-P31.5-2 → stays OPEN** — verified nuance recorded on the row: the web
  surface honours `publication_review_required` (orgs appear as entity ids;
  zero partner-org names in any public artifact), but `sig-api`
  `/v1/search` + `/v1/entity` publicly **label** flagged partner orgs by name —
  which is the operator-approved publish intent (the HG-11-reviewed diff
  describes the links "naming a vendor organisation"). Closure needs the
  "moot for public accountability organisations" ADR or a read-surface gate.
- **D-R6.1-EVAL → stays OPEN** — the PROVISIONAL eval disclosure remains on
  the surfaces, as owed for Round 10.

## 8. What this publish deliberately did not do

No materializer re-ran; no claim-spine row was written, updated, or deleted;
no `ingestion_permitted` flag moved; no gate other than HG-11 was ticked; the
stamped restricted export is untouched and still private; nothing was merged,
tagged, or pushed to `main`.
