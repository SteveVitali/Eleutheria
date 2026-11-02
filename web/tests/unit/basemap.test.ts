// SPDX-License-Identifier: Apache-2.0
// P36.33 (K1 MAP-02, SIG-UI-100): the emitted basemap style documents.
import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import {
  BASEMAP_TILE_ORIGIN,
  GLYPH_URL_TEMPLATE,
  assertBasemapStyleContract,
} from "../../src/lib/basemap";

const read = (p: string) => JSON.parse(readFileSync(join("public/map", p), "utf-8"));
const light = read("style-light.json");
const dark = read("style-dark.json");
const context = read("style-context.json");

describe("generated basemap styles (K1 §2.5)", () => {
  it("light + dark satisfy the serving contract", () => {
    expect(() => assertBasemapStyleContract(light)).not.toThrow();
    expect(() => assertBasemapStyleContract(dark)).not.toThrow();
  });

  it("binds the basemap source to the SIG tile origin", () => {
    expect(light.sources.basemap.url).toMatch(/^pmtiles:\/\/https:\/\/tiles\.surveillancegraph\.org\//);
    expect(dark.sources.basemap.url).toBe(light.sources.basemap.url);
  });

  it("glyphs are same-origin Noto (OFL), never a second host", () => {
    expect(light.glyphs).toBe(GLYPH_URL_TEMPLATE);
    expect(context.glyphs).toBe(GLYPH_URL_TEMPLATE);
  });

  it("no sprite sheet is served", () => {
    expect(light.sprite).toBeUndefined();
    expect(dark.sprite).toBeUndefined();
    expect(light.layers.some((l: any) => l.layout?.["icon-image"])).toBe(false);
  });

  it("drops POI-class layers; v4 schema emits no transit", () => {
    const ids = new Set(light.layers.map((l: any) => l.id));
    expect(ids.has("address_label")).toBe(false);
    expect(ids.has("roads_shields")).toBe(false);
    expect([...ids].some((i) => /poi|transit/.test(String(i)))).toBe(false);
  });

  it("K1 zoom bounds: buildings z15+, road labels z13+", () => {
    const byId = Object.fromEntries(light.layers.map((l: any) => [l.id, l]));
    expect(byId.buildings.minzoom).toBe(15);
    expect(byId.roads_labels_major.minzoom).toBe(13);
    expect(byId.roads_labels_minor.minzoom).toBeGreaterThanOrEqual(13);
  });

  it("keeps place labels + water + boundaries + roads casing", () => {
    const ids = new Set(light.layers.map((l: any) => l.id));
    for (const id of ["places_country", "places_region", "places_locality", "water", "boundaries", "water_label_lakes"])
      expect(ids.has(id)).toBe(true);
  });

  it("attribution: ODbL + Protomaps on the basemap source", () => {
    expect(light.sources.basemap.attribution).toContain("OpenStreetMap");
    expect(light.sources.basemap.attribution).toContain("ODbL");
  });

  it("sig metadata carries the lock posture", () => {
    expect(light.metadata["sig:basemap"].active_source).toBe("basemap");
    expect(light.metadata["sig:lock"]).toBe("ops/basemap.lock.json");
  });
});

describe("the context fallback style (K1 §2.6)", () => {
  it("is same-origin only — context.pmtiles on the web host", () => {
    expect(() => assertBasemapStyleContract(context)).not.toThrow();
    expect(context.sources.context.url).toBe("pmtiles:///tiles/context.pmtiles");
  });
  it("carries boundaries + place labels only", () => {
    expect(context.layers.length).toBeGreaterThan(2);
    expect(context.layers.every((l: any) => l.source === "context" || l.type === "background")).toBe(true);
  });
  it("names the public-domain attribution", () => {
    expect(context.sources.context.attribution).toContain("public domain");
  });
});

describe("contract refusals (fail-closed)", () => {
  const clone = (o: any) => JSON.parse(JSON.stringify(o));
  it("refuses a third-party basemap origin", () => {
    const s = clone(light);
    s.sources.basemap.url = "pmtiles://protomaps.com/x.pmtiles";
    expect(() => assertBasemapStyleContract(s)).toThrow();
  });
  it("refuses a sprite sheet", () => {
    const s = clone(light);
    s.sprite = "https://example.com/sprite";
    expect(() => assertBasemapStyleContract(s)).toThrow();
  });
  it("refuses off-origin glyphs", () => {
    const s = clone(light);
    s.glyphs = "https://fonts.example.com/{fontstack}/{range}.pbf";
    expect(() => assertBasemapStyleContract(s)).toThrow();
  });
});
