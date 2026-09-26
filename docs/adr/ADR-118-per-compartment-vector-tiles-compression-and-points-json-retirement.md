# ADR-118 — Per-compartment z0–z14 vector tiles, repo-owned sig-web compression, and the retirement of the combined /map/points.json (the design's ADR-R9-TILES)

- **Status:** Accepted
- **Phase / ticket:** Phase 31 / P31.15 (`docs/tickets/P31.15__vector-tiles-and-compression.md`)
  — Round 9 `SURFACE.2`. Advances (does not close) **D-P30.3-2** (its public half — the
  live map drawing from tiles — is owed to P31.16's republish + hosted verification).
  Ends accepted deviation **R8-1** in the build (closes live at P31.16's republish,
  when the public object is removed and verified gone).
- **Date:** 2026-10-05
- **Related:** ADR-048/ADR-051 (tiles as a published artifact class), ADR-097/ADR-091
  (the `/map` island allowance, DECISION-SPA = B), ADR-098 (LB → `sig-web`),
  ADR-106 (licence compartments publish separately; §5 produced-work rendering),
  ADR-111 (`pin_image_digest` deploys), spec §40 (the map; SIG-UI-038/047),
  §42.3 (the ODbL compartment), §19.4 (coordinate reduction), SIG-GEO-012/013;
  deferral **D-P30.3-2** (OPEN — the live/public half); backlog home **BL-056**.

## Context

P30.3 shipped the national map on three infra debts recorded as **D-P30.3-2**:

1. **The tile renderer was the pure-Python single-z0 fallback.** Each per-compartment
   PMTiles existed but carried one coarse zoom (a ~10 km cell at z0) — not the
   zoomable z0–z14 pyramid the map needs. `tippecanoe` was not in the export image.
2. **The style named an OSM basemap** (`/tiles/osm-basemap.pmtiles`) that nothing
   ever produced — a dead source reference.
3. **The island drew its points from a combined `/map/points.json`** — 17 MB,
   licence-mixed across all compartments (the operator-ACCEPTED Round-8 deviation
   **R8-1**, `docs/build/readouts/ACCEPT-R8.md`), fetched on hydration and served
   uncompressed by the hand-made `sig-web` service (stock `nginx:1.27-alpine` +
   a gcsfuse mount of the `<project>-sig-web` bucket; no nginx config in the repo,
   no repo-owned image, no repo-owned deploy path).

The operator answered the two design questions on 2026-09-24 (LEDGER § GATE
DECISIONS "Round 9 ratification"): **Q8 — no basemap** (option (a): a plain
background + real z0–z14 tiles; a self-hosted extract (b) is only a costed
follow-up; a third-party tile service (c) is out — it would leak visitor
viewports, which SIG-UI-038 already forbids as a hard dependency). **Q9 — retire**
the combined `/map/points.json` once per-compartment tiles serve the map, which
ends R8-1 and returns the public map to strict licence separation.

## Decision

1. **Per-compartment z0–z14 PMTiles, two renderers, one contract.** Every
   `sites.geojson` artifact the export emits is rendered to
   `web/tiles/<compartment>-sites.pmtiles` — one archive **per licence
   compartment**, never merged (§42.3, ADR-106). Each archive carries the z0–z14
   pyramid, an MVT point layer named `sites`, its compartment's SPDX licence in
   `sig:license`, and the compartment's attribution (the ODbL archive keeps the
   OpenStreetMap notice; every other compartment carries its own licence's
   attribution — never a borrowed CC-BY label). The production renderer is
   **tippecanoe 2.79.0** (sha256-verified multi-stage build in `ops/Dockerfile`,
   `-Z0 -z14 -l sites`, forced overwrite, attribution+licence embedded); when it
   is absent the **deterministic pure-Python encoder**
   (`exports/src/exports/tiles.py` — a Web-Mercator → MVT encoder + a spec-correct
   PMTiles v3 writer with cumulative-Hilbert tile ids) renders the same z0–z14
   pyramid, so CI and local builds never depend on a native toolchain. Both paths
   emit **byte-deterministic** archives for the same input: the tile bytes are
   canonical and the metadata is normalised (stable name, normalised generator,
   licence + attribution + zoom fields — the output filename/path and
   `generator_options` never leak in). Tile features carry only the slimmed
   publishable properties (`entity_id`, `entity_type`, `label`, `jurisdiction`,
   `sensitivity_tier`, `precision` — §19.4): the full sites.geojson row
   (claim/source ids, licence lists, envelopes) is a *downloadable* shape, not a
   tile-render one. The `--jurisdiction` release path renders the same way and
   **registers the archive in the bundle manifest** — the manifest is the
   contract the web build reads (`getCompartmentTileSources`).

2. **No basemap (Q8).** `PUBLIC_MAP_STYLE` is a plain `background` layer plus the
   per-compartment sources — the dead `osm_basemap` reference and its
   `BASEMAP_PMTILES_URL`/`SIG_PMTILES_URL` constants are gone from
   `web/src/lib/map-tiles.ts`. Follow-up (b) — a self-hosted extract, sized and
   costed first — is a future ticket, not built here; (c) a third-party tile
   service is not done.

3. **The island layers the archives; `/map/points.json` is retired (Q9).** The
   `/map` island registers the self-hosted `pmtiles://` protocol and adds **one
   attributed vector source per compartment** (composited on one map — an ODbL
   4.4(b) produced work, never merged); popups read the tile feature's own
   slimmed properties. `web/src/pages/map/points.json.ts` is deleted, the island
   never fetches it, the build no longer emits it (verified: the route is absent
   from `dist`), and `/map/style.json` is built from the same manifest-derived
   source list the astro integration copies into `dist/tiles/` — the style can
   never name an archive that was not copied, and an export-mode build with no
   rendered archives fails loud rather than serving a tile-less map. A
   fixtures-mode build ships no archives and the island falls back to a small
   inline GeoJSON prop set (still only tier-reduced publishable points). This
   **ends R8-1 in the build**; R8-1 closes live when P31.16's republish removes
   the public object and verifies it gone.

4. **A repo-owned `sig-web` image with real compression.** `ops/web/Dockerfile`
   compiles `google/ngx_brotli` (pinned commit, its `deps/brotli` submodule pin
   verified by sha256) as `--with-compat` dynamic modules against the **exact**
   nginx source version in the `nginx:1.27.5-alpine` runtime base — Alpine's
   `nginx-mod-http-brotli` targets a different nginx ABI and cannot be loaded.
   `ops/web/nginx.conf` enables gzip **and** Brotli for the text types
   (HTML/CSS/JS/JSON/GeoJSON/SVG), serves the registered `application/vnd.pmtiles`
   media type with byte ranges (`Accept-Ranges: bytes` — the pmtiles client's
   random-access reads), never recompresses `.pmtiles` (already gzip inside),
   marks Astro's content-hashed `/_astro/` assets immutable, and revalidates
   everything else (`must-revalidate`) since the bucket-sync deploy swaps bytes
   in place. The site root is `/mnt/sig-web` — the gcsfuse mount the live
   service already uses.

5. **The first repo-owned `sig-web` deploy path.** `ops/gcp/web.sh` builds the
   image (`sig-web:<git-sha>` Cloud Build, never `:latest`) and upserts the
   `sig-web` Cloud Run service on the **pinned digest** via `pin_image_digest`
   (ADR-111). Per the ticket's contract the hand-made service spec is **read
   live and reproduced, not guessed**: the `service` action runs
   `gcloud run services describe` first (logged for the record), then re-declares
   the gcsfuse volume (`<project>-sig-web` → `/mnt/sig-web`), unauthenticated
   ingress matching the LB→NEG + run.app reachability, and leaves scaling/env
   settings it does not own at the live values. P31.15 builds + tests this path;
   **the roll itself is P31.16's** (no live deploy under `live_verification=false`).

## Consequences

- The public map is back to **strict licence separation end-to-end**: every tile
  archive is one compartment + one licence + its own attribution, exactly like
  the downloadable artifacts. The ODbL layer is never merged.
- Served bytes shrink: z0–z14 tiles replace the 17 MB hydration payload, and the
  text assets (HTML/CSS/JS/JSON) are gzip/Brotli-compressed at the edge for the
  first time.
- The export build is deterministic for a snapshot: identical inputs → identical
  archive bytes (tippecanoe metadata normalisation included), so per-release
  diffs are real content diffs.
- `sig-web` becomes reproducible infrastructure: the image, the config, and the
  deploy plan are in the repo, digest-pinned, with the live service spec read
  rather than assumed.
- The `--jurisdiction` bundle's tile archive is manifest-registered like the
  spine export's, so `SIG_DATA_SOURCE=export` builds from either bundle shape
  exercise the same tile contract.

## Revisit trigger

Revisit when (a) the map needs a basemap — revisit ONLY as the costed
self-hosted extract follow-up (Q8(b)), never a third-party tile service; (b) a
licensor, counsel's written opinion (D-P30.3-COUNSEL), or the OSMF requires
splitting or further separating any tile layer — the per-compartment design
already isolates them; (c) zoom needs beyond z14 or features beyond point
geometry (lines/polygons for coverage cells) — the renderer contract is
per-compartment `sites` points today; (d) `sig-web` moves off the gcsfuse-mount
deploy (e.g. to a content-addressed bucket layout) — the nginx cache policy
assumes in-place byte swaps; or (e) nginx/alpine version drift breaks the
compiled-module pairing — the Dockerfile pins both sides and the build fails
loud on a checksum or ABI mismatch.
