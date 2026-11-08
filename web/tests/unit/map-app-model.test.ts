// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// P36.37 — the map app shell's pure model: SIG-UI-101 panel fields, SIG-UI-102
// in-view list, SIG-UI-104 facet counts + cannot-apply, one-data-hue channels
// (SIG-UI-065/107).
import { describe, expect, it } from "vitest";
import {
  EMPTY_FACETS,
  facetCannotApply,
  facetOptionCounts,
  facetOptions,
  geoFailureNote,
  IN_VIEW_MAX,
  myLocationTarget,
  MY_LOCATION_MIN_ZOOM,
  OPERATOR_NOT_STATED,
  parseSeenRange,
  placeRowsInView,
  recordPasses,
  seenOverlaps,
  seenRangeWire,
  selectionFromRecord,
  selectionFromTileProps,
  siteRowsInView,
  statusCode,
  STATUS_CODE,
} from "../../src/islands/map/model";
import type { MapRecord } from "../../src/islands/map/model";
import { NATIONAL_ZOOM_MAX } from "../../src/lib/map";

const REC = (over: Partial<MapRecord> = {}): MapRecord => ({
  id: "device:t-1",
  label: "Test record",
  technology: "alpr-fixed",
  operator: "Test PD",
  sources: [{ label: "Feed", href: "/sources/" }],
  licence: "CC-BY-4.0",
  jurisdiction: { label: "Testville", href: "/dossier/usa/xx/testville/" },
  firstSeen: "2026-01-01",
  lastSeen: "2026-06-01",
  status: "single-source",
  precision: "block-level",
  tier: 1,
  lat: 40,
  lon: -100,
  compartment: "sig_graph",
  recordHref: "/dossier/usa/xx/testville/sites/#device:t-1",
  listHref: "/dossier/usa/xx/testville/sites/",
  ...over,
});

describe("status codes (one data hue — the channel is fill/shape, not colour)", () => {
  it("maps fixture status words to tile st codes", () => {
    expect(statusCode("single source")).toBe("single-source");
    expect(statusCode("corroborated")).toBe("corroborated");
    expect(statusCode("contested")).toBe("contested");
    expect(statusCode("candidate")).toBe("candidate");
    expect(statusCode("bogus")).toBeNull();
    expect(STATUS_CODE["single-source"]).toBe(1);
  });
});

describe("selection panel (SIG-UI-101)", () => {
  it("projects every required field; operator falls back to the honest wording", () => {
    const m = selectionFromRecord(REC({ operator: null }));
    expect(m.label).toBe("Test record");
    expect(m.technology).toBe("alpr-fixed");
    expect(m.operatorText).toBe(OPERATOR_NOT_STATED);
    expect(m.jurisdiction.href).toContain("/dossier/");
    expect(m.sources[0]?.label).toBe("Feed");
    expect(m.firstSeen).toBe("2026-01-01");
    expect(m.lastSeen).toBe("2026-06-01");
    expect(m.precision).toBe("block-level");
    expect(m.statusText).toBe("One source");
    expect(m.recordHref).toContain("#device:t-1");
  });

  it("never emits an unresolvable link — a record without an anchor carries none", () => {
    const m = selectionFromRecord(REC({ recordHref: null }));
    expect(m.recordHref).toBeNull();
  });

  it("projects tile props honestly — unknown tech renders the code, never a guess", () => {
    const m = selectionFromTileProps(
      { rk: "rk1", lb: "Tile label", tc: 7, st: 2, tr: 0, f: 202601, l: 202609 },
      {},
    );
    expect(m.label).toBe("Tile label");
    expect(m.technology).toBe("Technology code 7");
    expect(m.statusText).toBe("Contested");
    expect(m.firstSeen).toBe("2026-01");
    expect(m.lastSeen).toBe("2026-09");
    expect(m.recordHref).toBeNull();
  });
});

describe("facets (SIG-UI-104)", () => {
  it("seen= wire round-trips the month range", () => {
    expect(parseSeenRange("2026-01..2026-06")).toEqual({ from: "2026-01", to: "2026-06" });
    expect(parseSeenRange("2026..2026")).toEqual({ from: "2026-01", to: "2026-12" });
    expect(parseSeenRange("bogus")).toBeNull();
    expect(seenRangeWire({ from: "2026-01", to: "2026-06" })).toBe("2026-01..2026-06");
  });

  it("seen overlap honours open-ended records honestly", () => {
    const r = REC({ firstSeen: "2026-03-01", lastSeen: null });
    expect(seenOverlaps(r, { from: "2026-01", to: "2026-06" })).toBe(true);
    expect(seenOverlaps(r, { from: "2025-01", to: "2025-12" })).toBe(false);
    expect(seenOverlaps(REC({ firstSeen: null, lastSeen: null }), { from: "2026-01", to: "2026-12" })).toBe(false);
  });

  it("recordPasses applies technology/status/seen", () => {
    const r = REC();
    expect(recordPasses(r, EMPTY_FACETS)).toBe(true);
    expect(recordPasses(r, { ...EMPTY_FACETS, technology: ["other"] })).toBe(false);
    expect(recordPasses(r, { ...EMPTY_FACETS, technology: ["alpr-fixed"] })).toBe(true);
    expect(recordPasses(r, { ...EMPTY_FACETS, status: ["corroborated"] })).toBe(false);
    expect(
      recordPasses(r, { ...EMPTY_FACETS, seen: { from: "2026-02", to: "2026-03" } }),
    ).toBe(true);
  });

  it("the cannot-apply rule: seen greys below the sites band, applies at z≥10", () => {
    expect(facetCannotApply("seen", NATIONAL_ZOOM_MAX)).toContain("applies from zoom");
    expect(facetCannotApply("seen", NATIONAL_ZOOM_MAX + 1)).toBeNull();
    expect(facetCannotApply("technology", 3)).toBeNull();
  });

  it("facet counts count every matching record once per option", () => {
    const rs = [REC({ technology: "a" }), REC({ technology: "a" }), REC({ technology: "b" })];
    expect(facetOptions(rs, (r) => r.technology)).toEqual(["a", "b"]);
    expect(facetOptionCounts(rs, (r) => r.technology).get("a")).toBe(2);
  });
});

describe("in-view list (SIG-UI-102)", () => {
  const bounds = { w: -110, s: 30, e: -90, n: 50 };
  it("site rows sort by distance and cap at 50", () => {
    const rs = Array.from({ length: 60 }, (_, i) =>
      REC({ id: `r-${i}`, lat: 40 + i * 0.01, lon: -100 - i * 0.01 }),
    );
    const { rows, matching } = siteRowsInView(rs, EMPTY_FACETS, bounds, { lat: 40, lon: -100 });
    expect(matching).toBe(60);
    expect(rows).toHaveLength(IN_VIEW_MAX);
    expect(rows[0]?.id).toBe("r-0");
  });
  it("place rows group by jurisdiction below the sites band", () => {
    const rs = [
      REC({ id: "a", jurisdiction: { label: "X", href: "/x/" } }),
      REC({ id: "b", jurisdiction: { label: "X", href: "/x/" } }),
      REC({ id: "c", jurisdiction: { label: "Y", href: "/y/" } }),
    ];
    const { rows, matching } = placeRowsInView(rs, EMPTY_FACETS, bounds);
    expect(matching).toBe(3);
    expect(rows).toHaveLength(2);
    expect(rows.find((r) => r.id === "X")?.dossierHref).toBe("/x/");
  });
});

// ------------------------------------------------------------- P37.18 (MAP-03b)
import {
  activeFacetCount,
  buildFacetDict,
  cannotApplyNotes,
  cellSlice,
  cellSliceValue,
  dedupeTileSites,
  effectiveFacets,
  isMapDict,
  sheetPeekText,
  sortInViewRows,
  tileFacetExpr,
  tilePlaceRowsInView,
  tileSitePasses,
  tileSiteRowsInView,
} from "../../src/islands/map/model";
import type { MapDict, MapFacetsV2 } from "../../src/islands/map/model";

const F2 = (over: Partial<MapFacetsV2> = {}): MapFacetsV2 => ({
  technology: [],
  status: [],
  seen: null,
  vendor: [],
  operator: [],
  source: [],
  jurisdiction: [],
  ...over,
});

const DICT: MapDict = {
  schema: "sig.map-dict/1",
  contract: "sig.map-tiles/2",
  sources: [
    { index: 0, id: "src-a", name: "Feed A", licence: "CC-BY-4.0", compartment: "sig_graph" },
    { index: 1, id: "src-b", name: "Feed B", licence: "ODbL-1.0", compartment: "osm_physical" },
  ],
  technologies: [
    { code: 1, slug: "alpr-fixed", label: "alpr fixed" },
    { code: 2, slug: "cctv", label: "cctv" },
  ],
  vendor_slots: [{ slot: 3, key: "org:flock", label: "Flock Safety" }],
  jurisdictions: {
    "us.census.geoid.place:4064000": {
      name: "Oklahoma City",
      level: "municipality",
      bbox: [-98.0, 35.3, -97.2, 35.8],
    },
  },
  unplotted: { "us.census.geoid.place:4064000": 4 },
  totals: { slice_rows: 10, by_technology: { "alpr-fixed": 7 }, unplotted_rows: 4 },
};
const FD = buildFacetDict(DICT);

describe("sig.map-dict/1 (P37.18)", () => {
  it("guards the document shape and builds the facet lookups", () => {
    expect(isMapDict(DICT)).toBe(true);
    expect(isMapDict({ schema: "sig.map-dict/1" })).toBe(false);
    expect(FD.techCodeBySlug.get("alpr-fixed")).toBe(1);
    expect(FD.vendorSlotByKey.get("org:flock")).toBe(3);
    expect(FD.sourceIndexById.get("src-b")).toBe(1);
  });
});

describe("tile-path facets over sig.map-tiles/2 props", () => {
  const p = { rk: "r1", lb: "Rec", tc: 1, vd: 3, oe: "org:okc-pd", sr: 1, st: 0, tr: 0, f: 202601, l: 202609 };
  it("passes/narrows each facet dim honestly", () => {
    expect(tileSitePasses(p, F2(), FD)).toBe(true);
    expect(tileSitePasses(p, F2({ technology: ["alpr-fixed"] }), FD)).toBe(true);
    expect(tileSitePasses(p, F2({ technology: ["cctv"] }), FD)).toBe(false);
    expect(tileSitePasses(p, F2({ vendor: ["org:flock"] }), FD)).toBe(true);
    expect(tileSitePasses(p, F2({ vendor: ["org:other"] }), FD)).toBe(false);
    expect(tileSitePasses(p, F2({ operator: ["org:okc-pd"] }), FD)).toBe(true);
    expect(tileSitePasses(p, F2({ operator: ["org:x"] }), FD)).toBe(false);
    expect(tileSitePasses(p, F2({ source: ["src-b"] }), FD)).toBe(true);
    expect(tileSitePasses(p, F2({ source: ["src-a"] }), FD)).toBe(false);
    expect(tileSitePasses(p, F2({ status: ["corroborated"] }), FD)).toBe(true);
    expect(
      tileSitePasses(p, F2({ seen: { from: "2026-02", to: "2026-03" } }), FD),
    ).toBe(true);
    expect(
      tileSitePasses(p, F2({ seen: { from: "2025-01", to: "2025-12" } }), FD),
    ).toBe(false);
    // absent dates can never satisfy a date facet (honest absence)
    expect(
      tileSitePasses({ ...p, f: undefined, l: undefined }, F2({ seen: { from: "2020-01", to: "2029-12" } }), FD),
    ).toBe(false);
  });
  it("builds a MapLibre filter expression for the site layers", () => {
    expect(tileFacetExpr(F2(), FD)).toBeNull();
    const expr = tileFacetExpr(F2({ technology: ["alpr-fixed"], status: ["contested"] }), FD);
    expect(JSON.stringify(expr)).toContain('"in"');
    expect(JSON.stringify(expr)).toContain('"tc"');
  });
});

describe("zoom honesty (SIG-UI-104, C-03 — grey, never hatch)", () => {
  it("seen cannot apply in the cells band; applies from z10", () => {
    const f = F2({ seen: { from: "2026-01", to: "2026-06" } });
    const notes = cannotApplyNotes(f, 6, true);
    expect(notes.map((n) => n.dim)).toContain("seen");
    expect(cannotApplyNotes(f, 12, true)).toEqual([]);
    const eff = effectiveFacets(f, 6, true);
    expect(eff.seen).toBeNull();
    expect(effectiveFacets(f, 12, true).seen).not.toBeNull();
  });
  it("operator/source cannot slice cells below z10 on the tile path", () => {
    const f = F2({ operator: ["org:x"], source: ["src-a"] });
    const dims = cannotApplyNotes(f, 3, true).map((n) => n.dim);
    expect(dims).toEqual(expect.arrayContaining(["operator", "source"]));
    const eff = effectiveFacets(f, 3, true);
    expect(eff.operator).toEqual([]);
    expect(eff.source).toEqual([]);
    // fixtures mode: the point set is individually drawn — the dims apply.
    expect(cannotApplyNotes(f, 3, false)).toEqual([]);
  });
  it("joint facet dims can't slice cells; single dims slice via marginal props", () => {
    expect(cellSlice(F2(), FD)).toEqual({ kind: "n" });
    expect(cellSlice(F2({ technology: ["alpr-fixed"] }), FD)).toEqual({
      kind: "props",
      keys: ["t_1"],
      label: "technology",
    });
    expect(cellSlice(F2({ status: ["single-source"] }), FD)).toEqual({
      kind: "props",
      keys: ["s1"],
      label: "status",
    });
    expect(cellSlice(F2({ technology: ["a"], vendor: ["b"] }), FD).kind).toBe("cannot");
    expect(cellSlice(F2({ seen: { from: "2026-01", to: "2026-06" } }), FD).kind).toBe("cannot");
    expect(cellSliceValue({ n: 5, t_1: 3, s1: 2 }, { kind: "props", keys: ["t_1"], label: "technology" })).toBe(3);
  });
});

describe("tile-path in-view rows", () => {
  const sites = dedupeTileSites([
    { props: { rk: "r1", lb: "Near", tc: 1, st: 0 }, lat: 40, lon: -100, compartment: "c" },
    { props: { rk: "r1", lb: "Near", tc: 1, st: 0 }, lat: 40, lon: -100, compartment: "c" }, // boundary dup
    { props: { rk: "r2", lb: "Far", tc: 2, st: 1 }, lat: 41, lon: -100, compartment: "c" },
  ]);
  it("dedupes by rk, sorts by distance, caps at IN_VIEW_MAX", () => {
    const { rows, matching } = tileSiteRowsInView(sites, F2(), FD, { lat: 40, lon: -100 });
    expect(matching).toBe(2);
    expect(rows[0]?.id).toBe("r1");
    expect(rows[0]?.technology).toBe("alpr-fixed");
  });
  it("applies the active facets", () => {
    const { matching } = tileSiteRowsInView(sites, F2({ technology: ["cctv"] }), FD, { lat: 40, lon: -100 });
    expect(matching).toBe(1);
  });
  it("groups cells into places with single-source share", () => {
    const cells = [
      { props: { h3: "a", n: 4, s1: 1, jp: "us.census.geoid.place:4064000" }, compartment: "c1" },
      { props: { h3: "a", n: 4, s1: 1, jp: "us.census.geoid.place:4064000" }, compartment: "c1" }, // dup
      { props: { h3: "b", n: 2, s1: 0, jp: "unplaced" }, compartment: "c1" },
    ];
    const { rows, matching } = tilePlaceRowsInView(cells, { kind: "n" }, FD, {});
    expect(matching).toBe(6);
    const okc = rows.find((r) => r.id === "us.census.geoid.place:4064000");
    expect(okc?.label).toContain("Oklahoma City");
    expect(okc?.meta).toContain("1 source: 25%");
    expect(okc?.bbox).toEqual([-98.0, 35.3, -97.2, 35.8]);
    const sliced = tilePlaceRowsInView(cells, { kind: "props", keys: ["s1"], label: "status" }, FD, {});
    expect(sliced.matching).toBe(1);
  });
});

describe("in-view table + sheet + download helpers", () => {
  it("sorts rows by the sortable keys, id-stable", () => {
    const { rows } = tileSiteRowsInView(
      dedupeTileSites([
        { props: { rk: "b", lb: "B", tc: 2, st: 1 }, lat: 42, lon: -100, compartment: "c" },
        { props: { rk: "a", lb: "A", tc: 1, st: 0 }, lat: 40, lon: -100, compartment: "c" },
      ]),
      F2(),
      FD,
      { lat: 40, lon: -100 },
    );
    expect(sortInViewRows(rows, "label", "asc").map((r) => r.id)).toEqual(["a", "b"]);
    expect(sortInViewRows(rows, "distance", "desc")[0]?.id).toBe("b");
  });
  it("counts active facet dims and formats the peek line", () => {
    expect(activeFacetCount(F2())).toBe(0);
    expect(activeFacetCount(F2({ technology: ["a"], seen: { from: "2020-01", to: "2021-01" } }))).toBe(2);
    expect(sheetPeekText(137, 2)).toBe("137 records in view · Filters (2)");
    expect(sheetPeekText(1, 0)).toBe("1 record in view");
  });
});

// P37.72 (D-K1-7, SIG-GOV-017 analysis docs/build/reports/p37.72-gov017-analysis):
// the 'My location' control ONLY pans the map — the model pins the frame and
// the proximity-free copy contract.
describe("my-location pan target (P37.72)", () => {
  it("centres on the position and raises zoom only to the site-band floor", () => {
    expect(MY_LOCATION_MIN_ZOOM).toBe(NATIONAL_ZOOM_MAX + 1);
    expect(myLocationTarget(-97.51, 35.47, 3)).toEqual({
      center: [-97.51, 35.47],
      zoom: MY_LOCATION_MIN_ZOOM,
    });
    // A deeper zoom is kept — a floor, never a zoom-out.
    expect(myLocationTarget(-97.51, 35.47, 14)).toEqual({
      center: [-97.51, 35.47],
      zoom: 14,
    });
    // Inside the cells band the floor still applies.
    expect(myLocationTarget(-97.51, 35.47, NATIONAL_ZOOM_MAX)).toEqual({
      center: [-97.51, 35.47],
      zoom: MY_LOCATION_MIN_ZOOM,
    });
  });
  it("failure copy is honest and carries no proximity wording", () => {
    const kinds = ["unsupported", "denied", "unavailable", "timeout"] as const;
    for (const k of kinds) {
      const msg = geoFailureNote(k);
      expect(msg).toContain("map stays where it is");
      // Contract-banned: no 'near you', no camera/watch framing, no nag.
      expect(msg).not.toMatch(/near you|camera|watching|enable|settings/i);
    }
    expect(geoFailureNote("denied")).toContain("Nothing was read or sent");
  });
});

// ------------------------------------------------------------------ P37.19
describe("jurisdiction facet + place framing (P37.19 / MAP-04)", () => {
  it("recordPasses honours the descendants-inclusive jurisdiction facet", async () => {
    const { recordPasses } = await import("../../src/islands/map/model");
    const rec = REC({
      jkey: "us.census.geoid.place:4064000",
      chain: ["iso3166-1:US", "iso3166-2:US-OK", "us.census.geoid.county:40109", "us.census.geoid.place:4064000"],
    });
    expect(recordPasses(rec, F2({ jurisdiction: ["iso3166-2:US-OK"] }))).toBe(true);
    expect(recordPasses(rec, F2({ jurisdiction: ["iso3166-2:US-TX"] }))).toBe(false);
    // An unkeyed record is never guessed in.
    expect(recordPasses(REC({ jkey: null, chain: undefined }), F2({ jurisdiction: ["iso3166-2:US-OK"] }))).toBe(false);
  });

  it("the facet cannot slice count cells (tile mode below z10); it applies elsewhere", async () => {
    const { cannotApplyNotes, effectiveFacets, cellSlice } = await import("../../src/islands/map/model");
    const f = F2({ jurisdiction: ["iso3166-2:US-OK"] });
    const notes = cannotApplyNotes(f, 4, true);
    expect(notes.map((n) => n.dim)).toContain("jurisdiction");
    expect(effectiveFacets(f, 4, true).jurisdiction).toEqual([]);
    expect(cellSlice(f, { techCodeBySlug: new Map(), techSlugByCode: new Map(), vendorSlotByKey: new Map(), vendorBySlot: new Map(), sourceByIndex: new Map(), sourceIndexById: new Map(), jurisdictions: {} }).kind).toBe("cannot");
    // z ≥ 10 on tiles, and the fixtures path at any zoom: the facet applies.
    expect(cannotApplyNotes(f, 12, true).map((n) => n.dim)).not.toContain("jurisdiction");
    expect(cannotApplyNotes(f, 4, false).map((n) => n.dim)).not.toContain("jurisdiction");
  });

  it("boundsViewport folds [w,s,e,n] like bbox=; unionBounds merges", async () => {
    const { boundsViewport, unionBounds } = await import("../../src/islands/map/model");
    const v = boundsViewport([-97.65, 35.29, -97.3, 35.68]);
    expect(v.lat).toBeCloseTo(35.49, 1);
    expect(v.lon).toBeCloseTo(-97.48, 1);
    expect(v.z).toBeGreaterThanOrEqual(7);
    expect(unionBounds([[-97.65, 35.29, -97.3, 35.68], null, [-98, 35, -97, 36]])).toEqual([-98, 35, -97, 36]);
    expect(unionBounds([null])).toBeNull();
  });
});
