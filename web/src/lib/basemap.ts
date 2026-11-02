// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * P36.33 (R11-K13-MAP-02, SIG-UI-100, K1 §2, ADR-229): the basemap contract the
 * TypeScript side shares with `ops/basemap.lock.json` (sig.basemap-lock/1) and
 * `web/scripts/gen-map-styles.mjs`.
 *
 * The basemap is a self-hosted Protomaps OSM archive (ODbL) on the SIG tile
 * origin — never merged with SIG data, never a release input. Glyphs and the
 * `context.pmtiles` fallback stay same-origin on the SIG web host (K1 §2.6),
 * so the fallback works even when the whole tile origin is down. The app shell
 * (P36.37) consumes the emitted style documents; this row ships the pipeline.
 */

/** The SIG tile origin — a SIG-controlled first-party host (R2, after OP-09's
 * DNS move). CSP `connect-src` admits it (K0 §4.8). */
export const BASEMAP_TILE_ORIGIN = "https://tiles.surveillancegraph.org";

/** Same-origin glyph template — `web/public/map/fonts/` (OFL Noto Sans). */
export const GLYPH_URL_TEMPLATE = "/map/fonts/{fontstack}/{range}.pbf";

/** The K1 §2.3 attribution strings (agent-drafted text, verbatim). */
export const BASEMAP_ATTRIBUTION =
  "Basemap © OpenStreetMap contributors (ODbL) · Protomaps";
export const BASEMAP_ABOUT_NOTE =
  "The basemap is an extract of the Protomaps daily build {build} " +
  "(OpenStreetMap data, ODbL 1.0), served unmodified except for zoom range " +
  "by SIG. Its style is CC0, its fonts (Noto Sans) are under the SIL Open " +
  "Font License. Download the basemap archive (ODbL): {link}.";
export const CONTEXT_ATTRIBUTION =
  "Boundaries: U.S. Census Bureau, Natural Earth (public domain)";

/** Layer ids a SIG basemap style must never carry (K1 §2.5 drops). */
export const DROPPED_LAYER_IDS = new Set(["address_label", "roads_shields"]);

/** Structural contract for an emitted basemap/context style document. */
export function assertBasemapStyleContract(style: {
  version?: number;
  sources?: Record<string, { type?: string; url?: string; attribution?: string }>;
  glyphs?: string;
  sprite?: string;
  layers?: { id: string }[];
  metadata?: Record<string, unknown>;
}): void {
  if (style.version !== 8) {
    throw new Error("basemap style: version must be 8");
  }
  const sources = style.sources ?? {};
  for (const [id, src] of Object.entries(sources)) {
    const url = src.url ?? "";
    if (!url.startsWith("pmtiles://")) {
      throw new Error(`basemap style: source ${id} is not a PMTiles source (${url})`);
    }
    const target = url.slice("pmtiles://".length);
    if (id === "basemap") {
      if (!target.startsWith(BASEMAP_TILE_ORIGIN + "/")) {
        throw new Error(
          `basemap style: the basemap source must resolve on ${BASEMAP_TILE_ORIGIN}`,
        );
      }
    } else if (!target.startsWith("/")) {
      throw new Error(
        `basemap style: source ${id} (${target}) is off-origin — context data is same-origin only`,
      );
    }
    if (!src.attribution?.trim()) {
      throw new Error(`basemap style: source ${id} carries no attribution`);
    }
  }
  if (style.sprite !== undefined) {
    throw new Error("basemap style: no sprite sheet is served (K1 §2.1)");
  }
  if (style.glyphs !== GLYPH_URL_TEMPLATE) {
    throw new Error(`basemap style: glyphs must be ${GLYPH_URL_TEMPLATE}`);
  }
  for (const layer of style.layers ?? []) {
    if (DROPPED_LAYER_IDS.has(layer.id)) {
      throw new Error(`basemap style: ${layer.id} is a dropped layer (K1 §2.5)`);
    }
  }
}
