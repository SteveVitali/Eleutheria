// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// The static-PMTiles serving contract (SIG-UI-038, SIG-GEO-012/013, P31.15,
// ADR-R9-TILES: z0–z14 per-compartment archives, no basemap (Q8), the combined
// /map/points.json retired (Q9)).
import { describe, expect, it } from "vitest";
import {
  MAP_ATTRIBUTION_LINE,
  OSM_ATTRIBUTION,
  PMTILES_VERSION,
  PUBLIC_MAP_STYLE,
  assertServingContract,
  buildPublicMapStyle,
  compartmentAttribution,
  compartmentLayerId,
  compartmentSourceId,
  isSelfHostedTileUrl,
} from "../../src/lib/map-tiles";

describe("static PMTiles v3, self-hosted, attributed (SIG-GEO-012/013, SIG-UI-038)", () => {
  it("the public style declares static PMTiles v3", () => {
    expect(PMTILES_VERSION).toBe(3);
    expect(PUBLIC_MAP_STYLE.metadata["sig:pmtiles_version"]).toBe(3);
    expect(PUBLIC_MAP_STYLE.metadata["sig:serving"]).toBe("static");
    expect(() => assertServingContract()).not.toThrow();
  });

  it("ships NO basemap and no pre-committed tile source (Q8)", () => {
    // The operator decision: a plain background only — no self-hosted extract, no
    // third-party tile service. A committed source would either name an archive that
    // does not exist or point at a CDN; the style must carry neither.
    expect(Object.keys(PUBLIC_MAP_STYLE.sources)).toEqual([]);
    expect(PUBLIC_MAP_STYLE.layers).toEqual([{ id: "sig-background", type: "background" }]);
  });

  it("rejects a third-party tile CDN or absolute host", () => {
    expect(isSelfHostedTileUrl("pmtiles://https://api.mapbox.com/x.pmtiles")).toBe(false);
    expect(isSelfHostedTileUrl("pmtiles:///tiles/maptiler/x.pmtiles")).toBe(false);
    expect(isSelfHostedTileUrl("https://tile.openstreetmap.org/{z}/{x}/{y}.png")).toBe(false);
    expect(isSelfHostedTileUrl("pmtiles:///tiles/osm_physical-sites.pmtiles")).toBe(true);
  });

  it("carries correct OSM attribution in the rendered line", () => {
    expect(OSM_ATTRIBUTION).toMatch(/openstreetmap/i);
    expect(MAP_ATTRIBUTION_LINE).toMatch(/openstreetmap/i);
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

  it("fails the contract on an unattributed source or an ODbL source without the OSM notice", () => {
    const unattributed = {
      ...PUBLIC_MAP_STYLE,
      sources: {
        x: { type: "vector" as const, url: "pmtiles:///tiles/x-sites.pmtiles", attribution: " " },
      },
    };
    expect(() => assertServingContract(unattributed)).toThrow(/SIG-GEO-013/);
    const odblWrongAttribution = {
      ...PUBLIC_MAP_STYLE,
      sources: {
        x: { type: "vector" as const, url: "pmtiles:///tiles/x-sites.pmtiles", attribution: "Some data (ODbL-1.0)" },
      },
    };
    expect(() => assertServingContract(odblWrongAttribution)).toThrow(/OpenStreetMap/);
  });
});

describe("per-licence-compartment tile sources (P30.3, ADR-106; P31.15, ADR-R9-TILES)", () => {
  const tiles = [
    { compartment: "osm_physical", license: "ODbL-1.0", path: "/tiles/osm_physical-sites.pmtiles" },
    { compartment: "sig_graph", license: "CC-BY-4.0", path: "/tiles/sig_graph-sites.pmtiles" },
  ];

  it("no compartment archives → the committed background-only style, unchanged", () => {
    expect(buildPublicMapStyle([])).toBe(PUBLIC_MAP_STYLE);
  });

  it("one separately-attributed source per compartment, never a merged archive", () => {
    const style = buildPublicMapStyle(tiles);
    expect(() => assertServingContract(style)).not.toThrow();
    expect(Object.keys(style.sources).sort()).toEqual(["sig_osm_physical", "sig_sig_graph"]);
    expect(style.sources["sig_osm_physical"]?.url).toBe("pmtiles:///tiles/osm_physical-sites.pmtiles");
    expect(style.sources["sig_osm_physical"]?.attribution).toBe(OSM_ATTRIBUTION);
    expect(style.sources["sig_sig_graph"]?.attribution).toContain("CC-BY-4.0");
    // the layer ids the island registers are the same ones the style declares
    expect(style.layers.map((l) => l.id)).toEqual([
      "sig-background",
      compartmentLayerId("osm_physical"),
      compartmentLayerId("sig_graph"),
    ]);
    expect(style.layers.map((l) => l.source)).toEqual([
      undefined,
      compartmentSourceId("osm_physical"),
      compartmentSourceId("sig_graph"),
    ]);
    expect(style.layers[1]?.["source-layer"]).toBe("sites");
  });

  it("ODbL layers carry the OpenStreetMap notice", () => {
    expect(compartmentAttribution("ODbL-1.0")).toMatch(/openstreetmap/i);
    expect(compartmentAttribution("CC-BY-SA-4.0")).toContain("CC-BY-SA-4.0");
  });
});
