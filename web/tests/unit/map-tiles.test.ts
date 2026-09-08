// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// The static-PMTiles serving contract (SIG-UI-038, SIG-GEO-012/013).
import { describe, expect, it } from "vitest";
import {
  MAP_ATTRIBUTION_LINE,
  OSM_ATTRIBUTION,
  PMTILES_VERSION,
  PUBLIC_MAP_STYLE,
  assertServingContract,
  isSelfHostedTileUrl,
} from "../../src/lib/map-tiles";

describe("static PMTiles v3, self-hosted, OSM-attributed (SIG-GEO-012/013, SIG-UI-038)", () => {
  it("the public style declares static PMTiles v3", () => {
    expect(PMTILES_VERSION).toBe(3);
    expect(PUBLIC_MAP_STYLE.metadata["sig:pmtiles_version"]).toBe(3);
    expect(PUBLIC_MAP_STYLE.metadata["sig:serving"]).toBe("static");
    expect(() => assertServingContract()).not.toThrow();
  });

  it("every source is a self-hosted relative PMTiles path — no third-party CDN", () => {
    for (const src of Object.values(PUBLIC_MAP_STYLE.sources)) {
      expect(isSelfHostedTileUrl(src.url)).toBe(true);
    }
  });

  it("rejects a third-party tile CDN or absolute host", () => {
    expect(isSelfHostedTileUrl("pmtiles://https://api.mapbox.com/x.pmtiles")).toBe(false);
    expect(isSelfHostedTileUrl("pmtiles:///tiles/maptiler/x.pmtiles")).toBe(false);
    expect(isSelfHostedTileUrl("https://tile.openstreetmap.org/{z}/{x}/{y}.png")).toBe(false);
    expect(isSelfHostedTileUrl("pmtiles:///tiles/osm-basemap.pmtiles")).toBe(true);
  });

  it("carries correct OSM attribution in the style and the rendered line", () => {
    expect(OSM_ATTRIBUTION).toMatch(/openstreetmap/i);
    expect(MAP_ATTRIBUTION_LINE).toMatch(/openstreetmap/i);
    const attributions = Object.values(PUBLIC_MAP_STYLE.sources)
      .map((s) => s.attribution)
      .join(" ");
    expect(attributions).toMatch(/openstreetmap/i);
  });

  it("fails the contract if a source points at a tile server / non-PMTiles url", () => {
    const bad = {
      ...PUBLIC_MAP_STYLE,
      sources: {
        osm: { type: "vector" as const, url: "https://api.maptiler.com/tiles.json", attribution: OSM_ATTRIBUTION },
      },
    };
    expect(() => assertServingContract(bad)).toThrow(/SIG-UI-038/);
  });
});
