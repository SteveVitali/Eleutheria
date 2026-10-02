<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# INFRA_RUNBOOK — running the P21.5 infrastructure (deposits, store, tiles, mirrors, degraded mode)

*P21.5, ADR-067. How to run each of deliverables 1–6 with the exact env names. Every
credentialed integration is **dry-run / sandbox by default** and reports
`gate pending: HG-07` when its credential is absent — it never fabricates success (§3.1).*

Prerequisite for the export-based commands: a built release, e.g.
`uv run sig-exports build --jurisdiction okc --out exports/out/okc`.

## 1. Zenodo deposit (SIG-EXPORT-002)

| goal | command | env |
|---|---|---|
| offline dry-run (default) | `uv run sig-exports deposit --in exports/out/okc` | — |
| sandbox dry-run (10.5072 prefix, offline) | `uv run sig-exports deposit --in exports/out/okc --sandbox --dry-run` | — |
| **real sandbox deposit** | `uv run sig-exports deposit --in exports/out/okc --sandbox` | `SIG_ZENODO_SANDBOX_TOKEN` |
| production deposit (operator only) | `uv run sig-exports deposit --in exports/out/okc` *(swap in a production token)* | production Zenodo token |

- Without `SIG_ZENODO_SANDBOX_TOKEN`, `--sandbox` exits **4** (`gate pending: HG-07`) and
  writes nothing. Every deposit appends a row to `docs/build/reports/DEPOSITS.md` with its
  `environment` (RISK-P21-08). The deposit uploads the release bundle + `manifest.json` +
  `digests.json` + `CITATION.cff` + `sbom.cdx.json` and carries the per-compartment licence.

## 2. Object store + CDN + egress alarm + torrent (SIG-EXPORT-008/009)

| goal | command | env |
|---|---|---|
| push a release to the store | `uv run sig-exports push --in exports/out/okc --store cloudflare-r2:sig-bulk` | `SIG_OBJECT_STORE_URL`, `SIG_OBJECT_STORE_KEY`, `SIG_OBJECT_STORE_SECRET` (boto3-standard) |
| egress budget report | `uv run sig-ops egress-report` (add `--usage-gb N` when a usage figure is known) | — (usage API when available) |
| produce a `.torrent` | `uv run sig-exports torrent --in exports/out/okc/sig_graph/claims.parquet` | — |

- Objects are uploaded under **content-hash keys** with an immutable `Cache-Control`
  (append-only; never overwritten). A **metered-egress** provider fails the build
  (SIG-EXPORT-008). Store/CDN config template: `ops/config.toml` (ADR-067 picks Cloudflare
  R2; AWS S3 + CloudFront per ADR-015 is the documented alternative). `egress-report`
  reports `gate pending: HG-07` with the documented threshold when no live usage is
  available, and exits **5** on a real breach (RISK-P21-09).

## 3. Tile generation (LD-F07/LD-H08, §40)

| goal | command |
|---|---|
| render GeoJSON → PMTiles | `uv run sig-exports tiles --in exports/out/okc/osm_physical/devices.geojson --out /tmp/sig.pmtiles` |

- Uses **tippecanoe** if on `PATH`, else the pure-Python fallback (small extents). The
  ODbL licence + OSM attribution are preserved in the archive metadata (ADR-048, §42). The
  jurisdiction build renders `web/tiles/sig-infrastructure.pmtiles`; the web build in
  `export` mode copies it into `/tiles/` (consumed by the map's `/map/style.json` source).
  **A1 is ticked — the served map is zero-JS; no MapLibre island.**

## 4. Mirrors + Software Heritage (SIG-GOV-022/023/024)

| goal | command | env |
|---|---|---|
| build a SWH save request (print only) | `uv run sig-ops swh-save --repo-url https://github.com/SteveVitali/Eleutheria` | — |
| actually submit to SWH | `uv run sig-ops swh-save --repo-url <url> --now` | `SIG_SWH_TOKEN` (optional; not needed for public repos) |

- Mirror manifest: `ops/mirrors.toml`. Succession/rebuild guide: `docs/build/SUCCESSION.md`.
  This run leaves SWH **untriggered** (`gate pending`: no public repo URL saved).

## 5. Degraded-but-alive mode + keepalive (SIG-GOV-021, RISK-P0-12)

| goal | command | env |
|---|---|---|
| build the fully static site (no API) | `uv run sig-ops degraded --data-source fixtures` | — |
| build from an export snapshot | `uv run sig-ops degraded --data-source export --export-dir exports/out/okc` | — |
| the monthly keepalive | `.github/workflows/keepalive.yml` (cron `0 7 1 * *` + manual) | — |

- `sig-ops degraded` **fails loudly** if it cannot rebuild. The keepalive runs exactly this
  command monthly so a dormant scheduler is caught by a red build. Cost: **$0 beyond the
  static host**.

## Gate status (this run)

- **HG-07 (accounts): NO.** Real sandbox deposit, live object-store push, and triggered
  SWH save are `gate pending: HG-07`. Dry-run/sandbox-stub, tiles, `.torrent`, degraded
  mode, and keepalive are done for real.
- **HG-12 (budget): zero-cost.** CDN/object-store config are templates only.
- **A1: ticked.** The zero-JS static map stays; no MapLibre island; `/map/` script budget
  unchanged.

## 6. Production data protection (P34.3; SIG-OPS-002, SIG-STORE-048)

`ops/gcp/protect.sh` owns the five pre-authorised mutations (S5-3 11A list,
expires GATE-G4). It is dry-run by default; every `--apply` leg is idempotent
(live-read → `SKIP`) and window-gated (never 03:00–10:00Z; `sig-pg` legs also
never inside an AR-3 window or while `sig-materialize` runs). The AR-2 restore
point — an on-demand `sig-pg` backup verified `SUCCESSFUL` — runs before any
instance patch.

| goal | command |
|---|---|
| print the plan (no ADC, no network) | `ops/gcp/protect.sh --check` (bare, or per leg: `prestate\|backup\|instance\|buckets\|iam`) |
| capture pre-state JSON + sha256 (read-only, any time) | `ops/gcp/protect.sh --apply prestate` |
| run the live leg (order: prestate → AR-2 backup → three `sig-pg` patches → bucket versioning+lifecycle → `sig-web` IAM → post-state + `--verify` + site checks) | `ops/gcp/protect.sh --apply` |
| verify the outcome (live reads) | `ops/gcp/protect.sh --verify` |
| verify offline against recorded JSON | `ops/gcp/protect.sh --verify --from-state <state-dir>` |

Stop rules (automatic): a non-`UPDATE` operation, a restart, an `api /health`
failure, or a site route failing after QA-7 rolls that action back inline and
exits non-zero — the leg never continues past a red step.

Rollback per mutation (the script prints and runs these on a stop-rule trip;
run manually if an interruption left a mid-apply state):

| mutation | rollback |
|---|---|
| deletion protection + retain-backups | `gcloud sql instances patch sig-pg --no-deletion-protection --no-retain-backups-on-delete` |
| maintenance window SUN 09:00Z | `gcloud sql instances patch sig-pg --maintenance-window-any` |
| autoresize cap 40 GB | `gcloud sql instances patch sig-pg --storage-auto-increase-limit=0` |
| bucket versioning + lifecycle (`sig-restricted`, `sig-public`, `sig-web`) | `gcloud storage buckets update gs://<bucket> --no-versioning` + re-apply the captured prior lifecycle file (pre-state: none — `--lifecycle-file` of an empty rule set clears it; noncurrent versions already written are kept) |
| `allUsers` on `sig-web` | `gcloud storage buckets add-iam-policy-binding gs://<project>-sig-web --member=allUsers --role=roles/storage.objectViewer` |

QA-7 verification after the IAM change: `GET /` and `/map/` → 200 and
`GET /tiles/sig_graph-sites.pmtiles` (Range) → 206 on both
`https://surveillancegraph.org` and the `sig-web` `*.run.app` URL, and the
direct bucket URL `https://storage.googleapis.com/<project>-sig-web/index.html`
→ 403/404. Captured states land in the gitignored `docs/build/logs/protect/`.

## 7. Alerts that reach a human (P34.4; SIG-OPS-006 partial, QA-3/4/5, QA-8 disable)

`ops/gcp/alerts.sh` owns the five pre-authorised mutations (S5-3 11A list,
expires GATE-G4) over the committed alert set (`ops/monitoring/*.json`,
ADR-192). Same contract as `protect.sh`: dry-run by default, idempotent,
window-gated (never 03:00–10:00Z; the `sig-probe` image roll additionally
never inside an AR-3 window).

| goal | command |
|---|---|
| print the plan (no ADC, no network) | `ops/gcp/alerts.sh --check` (bare, or per leg: `prestate\|monitoring\|reingest\|proberoll\|delivery\|jobfail`) |
| capture pre-state JSON + sha256 (read-only, any time) | `ops/gcp/alerts.sh --apply prestate` |
| leg A — create the TLS-expiry + SIG-ALERT policies, disable `reingest.yml`, build+roll `sig-probe` at HEAD, run the delivery test, post-state `--verify` | `ops/gcp/alerts.sh --apply all` |
| leg B — extend the failed-job policy to `sig-probe` (self-gates: exit 42 while the re-roll's latest sweep is not green) | `ops/gcp/alerts.sh --apply jobfail` |
| verify the outcome (live reads) | `ops/gcp/alerts.sh --verify` |
| verify offline against recorded JSON | `ops/gcp/alerts.sh --verify --from-state <state-dir>` |
| diff the committed defs alone | `uv run sig-ops monitoring-defs verify --live` (or `--from-state <dir>`) |

Rollback per mutation (printed by the script; run manually if an interruption
left a mid-apply state):

| mutation | rollback |
|---|---|
| create a new alert policy (TLS-expiry / SIG-ALERT log) | `gcloud alpha monitoring policies delete <new id> --project <p>` |
| extend the failed-job policy to `sig-probe` + rate limit | `gcloud alpha monitoring policies update 7285515107319155929 --policy-from-file=<apply-dir>/policy.7285515107319155929.prior.rendered.json` (the captured prior definition) |
| `sig-probe` image roll | `uv run sig-ops roll-jobs --job sig-probe --image <before-digest> --apply` (the digest is in `<dir>/proberoll.record.json`) |
| `reingest.yml` disabled | `gh workflow enable reingest.yml` (+ restore the `schedule:` block from git history if ever wanted — it stayed `workflow_dispatch`-only) |

Evidence lands in the gitignored `docs/build/logs/alerts/` (pre/post captures
with sha256s). The delivery test POSTs a synthetic `SIG-ALERT` to the
`sig-alerts` webhook — its token is read from Secret Manager into memory only,
never printed or persisted — and reads `SIG-ALERT-RECEIVED` back from Cloud
Logging; the e-mail receipt itself is the operator's human check (`D-P34.4-2`).
