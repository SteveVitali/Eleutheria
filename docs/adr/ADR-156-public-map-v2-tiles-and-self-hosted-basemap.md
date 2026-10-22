# ADR-156: Public map v2 — count-conserving per-compartment overlay tiles (`sig.map-tiles/2`) and the self-hosted OSM basemap direction

- **Status:** Proposed (agent-drafted record of the K1 design; the overlay-tile half is implemented by P35.52 — the
  basemap pipeline lands under MAP-02, its own row)
- **Phase:** Round 11 / Stage B
- **Ticket:** P35.52 (run ledger `docs/build/runs/P35.52.md`). Design source: `PD/design/K1-map.md` §2–§3, §9.2,
  §10 (the agent-drafted ADR text this record follows), §12 MAP-01a. `PD` =
  `docs/build/planning/2026-09-30-next-phase/`
- **Written:** 2026-10-22T22:26Z (`date -u`; Devin sub-agent — agent-drafted, labelled; the basemap direction
  reverses the Round-9 operator decision Q8 at the operator's request U-003.1, 2026-09-30T21:29:45Z, and decides
  nothing the operator did not already answer — ADR-170's frame, referenced provisionally)
- **Reverses:** the Round-9 operator decision **Q8** ("no basemap", 2026-09-24) — requested by the operator
  (U-003.1). **Supersedes ADR-118 §Decision 2** (no basemap), acting on that ADR's own revisit trigger (a)
  ("revisit ONLY as the costed self-hosted extract follow-up (Q8(b)), never a third-party tile service").
  **Extends ADR-118 §Decision 1** (one archive per licence compartment) with the second layer and the retention
  contract. **Consumes ADR-155** (the T2 `/map/` page type and `sig.workspace-state`). **Leaves ADR-106**
  (licence-compartment separation) unchanged — it is the reason the cell counts stay per-compartment.
- **Related:** SIG-GEO-008/010/011/012/013, SIG-UI-005/016–020/037/038/047, SIG-FIND-004; U-003.1, U-008;
  F-104, F-414; ADR-170 (ODbL map basis — cites this ADR provisionally), ADR-162 §"Shared use" (the same host serves
  basemap + tiles + snapshots); DEFERRALS D12 (fixed: hashed archive names + `immutable`).

## Context

The public map showed a few dozen points on a blank canvas (F-104): tippecanoe ran with default dropping
(`--drop-densest-as-needed` behaviour at base zoom = max zoom, rate 2.5), so only **0.03 %** of the 227,335
published sites existed at z3, **5.7 %** at z10 and **25.6 %** at z12 (F-414, measured) — and nothing replaced the
dropped points, so the density bins the spec promised were never drawn. Readers at national and street zoom
saw absence where the spine held published records.

Two separate defects share one contract fix:

- **Overlay tiles thin silently.** Default dropping is the wrong default for an evidence-first surface; the
  pure-Python fallback renderer also coalesced distinct entities sharing a grid cell (`tiles.py:56`, the old
  `_DEDUP_CELL` path).
- **A cross-compartment count layer cannot ship.** Cells summed across licence compartments would be a
  licence-mixed derived database — ADR-106 §4 files those only as restricted build inputs — so the counts must be
  summed in the browser at render time.

The basemap half: without place context, a reader cannot tell where they are (C2's blank frames were
byte-identical). Q8 declined a basemap to avoid third-party tile services; a self-hosted OpenStreetMap extract
removes that objection (K1 §2.4: ≈ $2–13/month).

## Decision

1. **Overlay contract `sig.map-tiles/2`.** One PMTiles v3 archive per licence compartment —
   `<compartment>-sites.<sha8>.pmtiles`, never merged — carrying two layers:
   - `cells` — z0–9, a point at the H3 cell's mean published position (after the tier transform, SIG-GEO-010),
     with `h3`, `n` (this compartment's published located count), `ns`, `jp`; H3 resolutions res 3 at z0–4,
     res 4 at z5–6, res 5 at z7–8, res 6 at z9.
   - `sites` — every published located record from its tier's minimum zoom: tier 0 from z10, tier 1 from z11,
     tier 2 from z12 **as its H3 polygon** (never the true point), tier 3 **never** drawn. Properties are the
     §3.3 vocabulary (`rk`, `lb`, `tc`, `vd`, `op`, `oe`, `sr`, `j`, `f`, `l`, `st`, `tr`, `pm`, `co`) — no claim
     ids, no full-precision coordinates, no personal data (§19.4 / Part VIII).
2. **Retention rule.** The exporter writes each feature's zoom range as a `"tippecanoe": {"minzoom","maxzoom"}`
   member; tippecanoe runs with `-r1`; `--drop-densest-as-needed`, `--drop-fraction-as-needed` and all
   `--coalesce*`/`--cluster-*` flags are **forbidden** (guarded at the argv boundary by
   `assert_retention_argv`). An over-size tile makes the export **fail loudly** (`check_tile_sizes`, 500 KiB
   limit, 200 KiB warn), never silently thin. The pure-Python renderer honours the same ranges and deduplicates
   only **byte-identical** features.
3. **Counts are summed in the browser.** Each archive carries only its own compartment's cells; the island
   re-sums visible `cells` per `h3` over the active compartments into one in-memory GeoJSON layer on every
   `sourcedata`/`moveend` and on compartment toggles (K1 §3.2) — a produced work carrying every drawn
   compartment's attribution, never a licence-mixed file.
4. **Verifier.** `sig-exports tiles verify` re-opens a built export and measures the six K1 §9.2 checks —
   count conservation, renderer parity (rk sets + Σ `n` per zoom; recorded `vacuous`, honestly, when the
   shipped archive is itself pure-Python), precision+tier+vocabulary, size, metadata vs `index.json` and the
   manifest, and the CI legs — writing `reports/tiles_verify.json` into the export dir. CI builds the
   **pinned** tippecanoe 2.79.0 once from the `ops/Dockerfile` tarball pin (sha256-verified, cached) and runs
   the verifier over a deterministic **50k-point synthetic fixture** (clustered cities, co-located points,
   byte-identical twins, all tiers, three licence compartments); the nightly job runs it over the
   national-scale fixture.
5. **Content-hashed, release-pinned paths.** `web/tiles/index.json` (`{compartment, path, sha256, licence,
   attribution, bounds, minzoom, maxzoom, counts{points, cells_by_band}, renderer, renderer_version,
   contract, source}`) names each archive by content hash; nginx serves hashed archives `immutable` (fixes
   D12); under G3, tile URLs resolve through `withBase()` from `v/<pub>/` and `/s/<pub>/tiles/`.
6. **Self-hosted OSM basemap direction (frames MAP-02).** The public map draws a self-hosted Protomaps
   OpenStreetMap basemap (ODbL) as its own archive on a SIG-controlled origin — never merged with SIG data,
   never a release input, pinned in `basemap.lock.json` — with a public-domain boundaries fallback
   (`context.pmtiles`) and an honest notice when it fails. The pipeline and host are MAP-02's row; this ADR
   records the direction that reverses Q8 as the operator requested (U-003.1) and that ADR-170 cites.

## Consequences

- **Positive:** the map answers "where" and "how many" honestly at every zoom; every published located record
  is rendered in its permitted band; a broken tile set fails the build, not the reader; cited snapshots read
  their own tiles.
- **Negative:** overlay archives grow ≈ 2.5× (K1 §3.1, ≈ 90–110 MB/release — negligible per-view);
  CI builds tippecanoe; the basemap adds an external data dependency refreshed by hand and ≈ $2–13/month.
- **Neutral:** the pure-Python renderer stays the fixture/CI path but is bound to the same contract and
  parity-checked against tippecanoe.

## Alternatives considered

- Third-party basemap services (OpenFreeMap, Stadia, MapTiler, OSMF): rejected — third-party viewport leakage,
  non-commercial terms (K1 §2.1).
- Client-side clustering of all points: rejected (≈ 34 MB GeoJSON, K12a §8).
- A single cross-compartment density archive: rejected — a licence-mixed public database (ADR-106 §4).
- tippecanoe `--cluster-distance`/`--coalesce*` per compartment: rejected — overlapping per-licence bubbles
  mislead; coalescing is the silent-thin defect.
- Keep no basemap: rejected (U-003.1) but kept as the failure fallback.

## Revisit trigger

1. Basemap hosting costs more than $25/month, or egress abuse is observed.
2. The Protomaps build or its licence terms change.
3. A compartment's densest tile exceeds 200 KB at z10, or the verifier finds any dropped record.
4. A requirement needs address-level geocoding.
5. Counsel, a licensor or the OSMF requires different attribution or separation.
6. MapLibre needs WebGL 2 only and the no-WebGL share of visitors becomes material.
