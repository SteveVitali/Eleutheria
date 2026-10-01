// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * The static-PMTiles serving contract for the public map (SIG-UI-038, SIG-GEO-012/013,
 * P31.15, ADR-R9-TILES).
 *
 * The public map MUST be served as **static PMTiles v3** — one archive per licence
 * compartment rendered by tippecanoe (or the pure-Python z0–z14 fallback) from the
 * published, tier-reduced sites — a dynamic tile server MUST NOT be a hard
 * dependency, and every source MUST carry its licence's attribution in EVERY
 * rendering context (a licence obligation, §42: OpenStreetMap for the ODbL
 * compartment, SIG/CC-BY for the rest). **There is no basemap** (operator decision
 * Q8, 2026-09-24): the style is a plain background plus the per-compartment site
 * layers — no self-hosted extract, no third-party tile service. The combined,
 * licence-mixed `/map/points.json` is retired (Q9 — accepted deviation R8-1 ends;
 * the public map is back to strict licence separation, one attributed source per
 * compartment).
 *
 * This module is the single, testable source of truth for that contract. It exports a
 * MapLibre GL style object (ADR-018) whose sources are self-hosted, relative PMTiles v3
 * archives — no third-party tile CDN host anywhere — and the attribution strings the
 * page renders into its static HTML. The style is also served verbatim at
 * `/map/style.json` (see `pages/map/style.json.ts`), so "the map is served from static
 * PMTiles" is a real, fetchable artifact.
 *
 * Note (ADR reconciliation): the shell ships zero client JavaScript by default and the
 * Lighthouse budget forbids any script bytes (SIG-UI-036/037/041), so the maplibre-gl
 * *runtime* reaches the page only inside the `/map` island allowance (SIG-UI-047); the
 * tabular equivalent remains the archivable, no-JS surface (SIG-UI-037/050).
 */

/** PMTiles archive version the public map is served as (SIG-GEO-012). */
export const PMTILES_VERSION = 3;

/**
 * The correct OpenStreetMap attribution, rendered in every context incl. print
 * (SIG-GEO-013). ODbL requires attributing OpenStreetMap and its contributors.
 */
export const OSM_ATTRIBUTION = "© OpenStreetMap contributors (ODbL)";

/** SIG's own attribution for the surveillance-infrastructure layers. */
export const SIG_ATTRIBUTION = "Surveillance data © SIG contributors";

/** The `pmtiles://` protocol prefix a MapLibre PMTiles source uses. */
export const PMTILES_PROTOCOL = "pmtiles://";

/**
 * A minimal, faithful subset of a MapLibre GL style. Only the fields the serving
 * contract constrains are typed here — the full spec is large and not our concern.
 */
export interface MapLibreVectorSource {
  type: "vector";
  /** A `pmtiles://<relative>` URL — self-hosted static PMTiles, never a tile server. */
  url: string;
  attribution: string;
}

export interface MapLibreStyle {
  version: 8;
  name: string;
  /** The declared PMTiles archive version this style consumes (SIG-GEO-012). */
  metadata: { "sig:pmtiles_version": number; "sig:serving": "static" };
  sources: Record<string, MapLibreVectorSource>;
  layers: Array<{ id: string; type: string; source?: string; "source-layer"?: string }>;
}

/** The plain-background base layer (Q8 — no basemap at all). */
export const BACKGROUND_LAYER: MapLibreStyle["layers"][number] = {
  id: "sig-background",
  type: "background",
};

/**
 * The public map's MapLibre GL style: a plain background plus ONE source per licence
 * compartment (`buildPublicMapStyle`), each archive carrying its own attribution — the
 * layers are composited on one map (an ODbL 4.4(b) produced work) but never merged into
 * one archive (ADR-106). With no compartment archives (fixtures) the style is the
 * background alone.
 */
export const PUBLIC_MAP_STYLE: MapLibreStyle = {
  version: 8,
  name: "SIG public infrastructure map",
  metadata: { "sig:pmtiles_version": PMTILES_VERSION, "sig:serving": "static" },
  sources: {},
  layers: [BACKGROUND_LAYER],
};

/**
 * Host substrings that would make the public map depend on a third-party tile CDN —
 * exactly what SIG-UI-038/SIG-GEO-012 forbid as a hard dependency. Kept as a testable
 * denylist so a future edit that points a source at one of these fails the gate.
 */
export const THIRD_PARTY_TILE_HOSTS = [
  "mapbox",
  "maptiler",
  "stadiamaps",
  "stamen",
  "arcgis",
  "googleapis",
  "tile.openstreetmap.org",
  "basemaps.cartocdn",
  "protomaps.com",
];

function sourceUrlPath(url: string): string {
  return url.startsWith(PMTILES_PROTOCOL) ? url.slice(PMTILES_PROTOCOL.length) : url;
}

/** Whether a source url is a self-hosted, relative PMTiles path (no third-party CDN host). */
export function isSelfHostedTileUrl(url: string): boolean {
  const path = sourceUrlPath(url);
  // A self-hosted archive is a same-origin relative path: no scheme, no host.
  if (/^https?:\/\//i.test(path)) return false;
  if (!path.startsWith("/")) return false;
  const lower = path.toLowerCase();
  if (THIRD_PARTY_TILE_HOSTS.some((h) => lower.includes(h))) return false;
  return path.endsWith(".pmtiles");
}

/**
 * Assert the whole serving contract holds (SIG-UI-038, SIG-GEO-012/013, ADR-R9-TILES):
 * every source is a self-hosted static PMTiles archive with no third-party tile CDN
 * dependency, every source carries attribution, an ODbL source always carries the
 * OpenStreetMap notice (every ODbL compartment in SIG is OSM-derived), and the declared
 * PMTiles version is v3. A zero-source style is legal (the plain background — fixtures
 * builds ship no archives). Throws otherwise.
 */
export function assertServingContract(style: MapLibreStyle = PUBLIC_MAP_STYLE): void {
  if (style.metadata["sig:pmtiles_version"] !== 3 || style.metadata["sig:serving"] !== "static") {
    throw new Error("SIG-GEO-012: the public map MUST be served as static PMTiles v3.");
  }
  for (const [id, src] of Object.entries(style.sources)) {
    if (!isSelfHostedTileUrl(src.url)) {
      throw new Error(
        `SIG-UI-038: map tile source ${src.url} is not a self-hosted static PMTiles archive ` +
          "(a third-party tile CDN MUST NOT be a hard dependency).",
      );
    }
    if (!src.attribution.trim()) {
      throw new Error(`SIG-GEO-013: map tile source ${id} carries no attribution.`);
    }
    if (/odbl/i.test(src.attribution) && !/openstreetmap/i.test(src.attribution)) {
      throw new Error(
        `SIG-GEO-013: ODbL source ${id} MUST carry the OpenStreetMap attribution.`,
      );
    }
  }
}

/** One per-compartment tile archive the national export ships (P30.3, ADR-106). */
export interface CompartmentTileSource {
  /** The licence compartment (e.g. `osm_physical`). */
  compartment: string;
  /** The archive's ONE SPDX licence. */
  license: string;
  /** Same-origin path, e.g. `/tiles/osm_physical-sites.pmtiles`. */
  path: string;
}

/** The source id a compartment's archive is registered under (shared by style + island). */
export function compartmentSourceId(compartment: string): string {
  return `sig_${compartment}`;
}

/** The layer id the site points of one compartment draw under (shared by style + island). */
export function compartmentLayerId(compartment: string): string {
  return `sig-sites-${compartment}`;
}

/** The attribution a compartment's tile source carries (ODbL → the OSM notice, §42.3). */
export function compartmentAttribution(license: string): string {
  return license === "ODbL-1.0" ? OSM_ATTRIBUTION : `${SIG_ATTRIBUTION} (${license})`;
}

/**
 * The public style for a build: the plain background plus ONE source per licence
 * compartment, each with its own attribution — never a merged archive (ADR-106), and
 * no basemap (Q8). The empty-tiles case yields the committed background-only style.
 */
export function buildPublicMapStyle(tiles: readonly CompartmentTileSource[]): MapLibreStyle {
  if (tiles.length === 0) return PUBLIC_MAP_STYLE;
  const sources: Record<string, MapLibreVectorSource> = {};
  const layers: MapLibreStyle["layers"] = [BACKGROUND_LAYER];
  for (const t of tiles) {
    const id = compartmentSourceId(t.compartment);
    sources[id] = {
      type: "vector",
      url: `${PMTILES_PROTOCOL}${t.path}`,
      attribution: compartmentAttribution(t.license),
    };
    layers.push({
      id: compartmentLayerId(t.compartment),
      type: "circle",
      source: id,
      "source-layer": "sites",
    });
  }
  return { ...PUBLIC_MAP_STYLE, sources, layers };
}

/** The attribution line rendered into the static HTML and print (SIG-GEO-013). */
export const MAP_ATTRIBUTION_LINE = `${OSM_ATTRIBUTION} · ${SIG_ATTRIBUTION}`;
