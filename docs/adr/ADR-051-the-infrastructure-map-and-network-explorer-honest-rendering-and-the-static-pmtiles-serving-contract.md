# ADR-051: The infrastructure map + network explorer — honest-rendering rules and the static-PMTiles serving contract

- **Status:** Accepted
- **Date:** 2026-09-08
- **Phase:** P15.3
- **Requirement ids:** SIG-UI-016, SIG-UI-017, SIG-UI-018, SIG-UI-019, SIG-UI-020, SIG-UI-021, SIG-UI-022, SIG-UI-023, SIG-UI-024, SIG-UI-025, SIG-UI-038, SIG-GEO-011, SIG-GEO-012, SIG-GEO-013, SIG-IDENT-030, SIG-RECON-050
- **Spec:** docs/2_canonical_design_spec.md §§39.3 (infrastructure map), 39.4 (network explorer), 19.4/19.5 (sensitivity tiers, binning and tiles)
- **Relates to:** ADR-018 (MapLibre GL for the web map), ADR-049 (the no-JS archivable web shell — whose consequences deferred the self-hosted-tiles renderer to P15.3), ADR-045 (access-path closure)

## Context

P15.3 lands the two spatial/graph public surfaces on P15.1's epistemic visual
language and a11y/no-JS/archivability baseline: the infrastructure map (§39.3) and
the network explorer (§39.4). ADR-049 explicitly left one thing open — *"the
self-hosted-tiles map renderer (SIG-UI-038) … land[s] with P15.3"* — and named the
reconciliation of the reference SVG with it as this ticket's revisit trigger.

The load-bearing tension: ADR-018 chose **MapLibre GL** as the renderer over static
PMTiles, but ADR-049 made the shell **zero-JS-by-default and archivable by
construction**, enforced by two mechanical CI gates that admit no exception — a
Lighthouse budget of **0 script bytes** and **≤150 KB total** on every built page.
Bundling the maplibre-gl runtime into the shipped pages would violate both gates and
the "archivable by construction" invariant.

## Decision

1. **Land the static-PMTiles *serving contract*, not a bundled runtime.**
   `web/src/lib/map-tiles.ts` is the single, tested source of truth for a MapLibre GL
   style whose sources are **self-hosted, relative PMTiles v3** archives
   (`pmtiles:///tiles/*.pmtiles`) with **OpenStreetMap attribution** and **no
   third-party tile CDN** anywhere (a denylist of known tile hosts is a testable
   tripwire). The style is served verbatim at **`/map/style.json`** (an Astro static
   endpoint mirroring the dossier's `.json.ts`), and `assertServingContract` runs at
   build so an edit that breaks the contract fails the build. This is exactly what
   SIG-GEO-012/013 and SIG-UI-038 require of the *served map* — a MapLibre renderer
   consuming self-hosted static PMTiles v3 with correct OSM attribution — realised as
   a real, fetchable artifact rather than a client bundle.

2. **The shipped `/map/` and `/network/` pages stay zero-JS**, with the tabular /
   list equivalent as the source of truth (SIG-UI-037) and the honest-rendering
   signals encoded server-side. The OSM attribution is rendered into the static HTML
   so it is present in every context including no-JS and print (SIG-GEO-013). The
   maplibre-gl *runtime* is therefore **not** added to the dependency tree — no client
   JS, both perf gates stay green, archivability stays structural. If an interactive
   renderer is later desired it attaches to the same committed style behind an
   explicit, greppable `client:` directive; nothing here forecloses that.

3. **Every honest-rendering rule is pure, colour-free, tested logic**, consumed by
   the pages (`web/src/lib/map.ts`, `web/src/lib/network.ts`):
   - the §39.3 layer catalog with **derived** layers (FOV, coverage) flagged and
     separately toggled, distinct from observed geometry (SIG-UI-016, SIG-GEO-006);
   - the **coverage underlay bound to the point layer by a single control** — modelled
     as one `LayerControl` governing both `physical_devices` and `coverage`, with a
     guard (`assertCoverageBinding`) that no control set can show points without
     coverage (SIG-UI-017);
   - **low coverage never reads as low density** — a low/absent-coverage cell is
     desaturated, value-suppressed, and carries the single absence hatch, so "we
     don't know" is a different encoding from a confidently-low count (SIG-UI-018);
   - **national-zoom density binning** and a per-sensitivity-tier minimum zoom at
     which a point is honestly renderable — tier 3 (jurisdiction-only) is never a
     point (SIG-UI-019, SIG-GEO-011, §19.4);
   - **no-coordinate assets as jurisdiction indicators**, with a conservation law
     (`locatable + Σ indicators = total`) so nothing is silently dropped (SIG-UI-020);
   - **sharing edges default to an ego network**, never a national hairball, with
     matrix/arc as declared alternatives (SIG-UI-021).

4. **The network explorer's ER disclosure is structural, not conventional.** A
   `CentralityStatistic` cannot be constructed without a valid `ErQuality` and its
   pre-rendered inline `disclosure` string (`centralityStatistic` throws otherwise),
   so no centrality/hub figure can appear without its ER-quality disclosure *at the
   statistic* (SIG-UI-023, SIG-IDENT-030). The three §12.2 access edge types are
   distinguished by a **glyph and a dash pattern** (two non-colour channels), are
   independently filterable, and are rendered as three unmerged groups
   (`MERGE_ACCESS_EDGES_BY_DEFAULT = false`, SIG-UI-024). Access-path closure mirrors
   `inference/src/inference/access_paths.py`: the full hop list with per-hop evidence
   (an evidence-less hop is rejected), confidence as the path minimum, and any path
   beyond `SPECULATIVE_HOP_THRESHOLD` (3) labelled **speculative** and excluded from
   headline figures (SIG-UI-025, SIG-RECON-050).

5. **Additive, back-compatible.** The P15.1 reference map/graph and every existing
   fixture/component are untouched; the new surfaces are new pages, new lib modules,
   and a new fixture, with nav/pages/tests extended additively.

## Deviation from ADR-018 (recorded per §0.7 / the phase gate)

ADR-018 said "use MapLibre GL as the web map **renderer**." P15.3 ships the MapLibre
**style + self-hosted PMTiles v3 source + OSM attribution** (the serving contract a
MapLibre renderer consumes) but does **not** bundle the maplibre-gl runtime into the
archivable pages, because doing so would violate the ADR-049 zero-JS invariant and
the mechanically-enforced Lighthouse budgets (0 script bytes, ≤150 KB). This is the
closest faithful alternative that keeps every hard CI gate green; the requirement
under test (SIG-UI-038/SIG-GEO-012/013 — the map *served* from static PMTiles with
OSM attribution and no hard third-party CDN) is met and machine-verified.

## Consequences

- The public map is served from a self-hosted static PMTiles v3 archive with OSM
  attribution and no third-party CDN dependency, and the two surfaces are WCAG 2.2 AA,
  zero-JS, and within the perf budget — the same gates every other P15 page passes.
- The honest-rendering rules are single-sourced pure logic, so the static SVG render,
  the tabular/list equivalents, and any future interactive renderer cannot diverge on
  what is honest to show.
- The actual `.pmtiles` binaries are a build artifact of the upstream geospatial
  phases (tippecanoe over the resolution projection, out of P15.3 scope); this ticket
  fixes the *contract* (paths, version, attribution) they must satisfy.

## Alternatives considered

- **Bundle maplibre-gl behind a `client:load` directive** — rejected: it ships client
  JS, failing the 0-byte script budget and the ≤150 KB total budget on the map page,
  and erodes the "archivable by construction" invariant ADR-049 makes structural.
- **A dynamic tile server (martin / pg_tileserv) as the public source** — rejected by
  SIG-GEO-012: a dynamic server MUST NOT be a hard dependency of the public map; it is
  permitted only for internal/curation use.
- **Keep only the P15.1 reference SVG and defer SIG-UI-038 again** — rejected: ADR-049
  named P15.3 as the ticket that lands the serving contract; deferring further would
  leave SIG-UI-038/GEO-012/013 unsatisfied with no owner.

## Revisit trigger

Revisit when an interactive MapLibre map is wired into the page (at which point the
committed `/map/style.json` is loaded by a `client:`-directed renderer and the perf
budget for that page must be re-derived), when the upstream geospatial phase publishes
the real `sig-infrastructure.pmtiles` / basemap archives (so the placeholder tile
paths and `source-layer` names must be reconciled with the generated tiles), or when
the read API serves live map/network data replacing the committed P15.3 fixture.
