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
  writes nothing. Every deposit appends a row to `docs/build/DEPOSITS.md` with its
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
