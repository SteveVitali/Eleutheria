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
  IN_VIEW_MAX,
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
