// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// The §39.3 infrastructure-map honest-rendering rules, tested on the pure logic in
// isolation from the Astro render (SIG-UI-016..021, §19.4/§19.5).
import { describe, expect, it } from "vitest";
import {
  COVERAGE_LEVELS,
  DERIVED_LAYERS,
  LAYER_CONTROLS,
  MAP_LAYERS,
  MIN_POINT_ZOOM_BY_TIER,
  NATIONAL_ZOOM_MAX,
  OBSERVED_LAYERS,
  POINT_COVERAGE_CONTROL,
  SENSITIVITY_TIERS,
  assertCoverageBinding,
  coverageBoundToPoints,
  coverageEncoding,
  isLocatable,
  partitionByLocatability,
  pointVisibleAtZoom,
  readsAsDensity,
  renderBin,
  renderModeForZoom,
  DEFAULT_SHARING_EDGE_VIEW,
} from "../../src/lib/map";
import type { LayerControl, MapAsset } from "../../src/lib/map";
import { DENSITY_BINS, LOW_COVERAGE_BIN, LOW_DENSITY_BIN, MAP_ASSETS } from "../../src/lib/map-network-fixture";

describe("the §39.3 layer catalog (SIG-UI-016)", () => {
  it("has the seven observed layers plus separately-flagged derived FOV + coverage", () => {
    expect(OBSERVED_LAYERS.map((l) => l.id)).toEqual([
      "physical_devices",
      "deployments",
      "rtccs_integration_hubs",
      "sharing_edges",
      "private_public_networks",
      "service_areas",
      "lifecycle_status",
    ]);
    expect(OBSERVED_LAYERS.every((l) => l.kind === "observed")).toBe(true);
    // Derived layers (FOV, coverage) are flagged distinct so they render distinctly
    // from observed geometry and are separately toggled (SIG-GEO-006).
    expect(DERIVED_LAYERS.map((l) => l.id)).toEqual(["field_of_view", "coverage"]);
    expect(DERIVED_LAYERS.every((l) => l.kind === "derived")).toBe(true);
  });

  it("every derived layer has its own control except coverage (bound to points)", () => {
    // FOV is separately toggled (SIG-UI-016); coverage is bound to the point layer.
    const fovControls = LAYER_CONTROLS.filter((c) => c.governs.includes("field_of_view"));
    expect(fovControls).toHaveLength(1);
    expect(fovControls[0]!.governs).toEqual(["field_of_view"]);
  });
});

describe("coverage bound to the point layer by a single control (SIG-UI-017)", () => {
  it("the default control set binds points to coverage — no points without coverage", () => {
    expect(coverageBoundToPoints()).toBe(true);
    expect(() => assertCoverageBinding()).not.toThrow();
    expect(POINT_COVERAGE_CONTROL.governs).toContain("physical_devices");
    expect(POINT_COVERAGE_CONTROL.governs).toContain("coverage");
  });

  it("exactly one control governs the point layer (no independent point toggle)", () => {
    const governingPoints = LAYER_CONTROLS.filter((c) => c.governs.includes("physical_devices"));
    expect(governingPoints).toHaveLength(1);
  });

  it("rejects a control set that lets points show without coverage", () => {
    const bad: LayerControl[] = [
      { id: "points_only", label: "Points", governs: ["physical_devices"] },
      { id: "coverage_only", label: "Coverage", governs: ["coverage"] },
    ];
    expect(coverageBoundToPoints(bad)).toBe(false);
    expect(() => assertCoverageBinding(bad)).toThrow(/SIG-UI-017/);
  });
});

describe("low coverage MUST NOT read as low density (SIG-UI-018)", () => {
  it("low/absent coverage is desaturated, value-suppressed, and hatched", () => {
    for (const level of ["none", "low"] as const) {
      const enc = coverageEncoding(level);
      expect(enc.desaturated).toBe(true);
      expect(enc.valueSuppressed).toBe(true);
      expect(enc.hatched).toBe(true);
    }
    // High coverage carries none of the "we don't know" treatment.
    const high = coverageEncoding("high");
    expect(high.desaturated).toBe(false);
    expect(high.valueSuppressed).toBe(false);
    expect(high.hatched).toBe(false);
  });

  it("a low-coverage cell and a confidently-low-density cell render DISTINCTLY", () => {
    // The heart of the AC (agentic in the ticket, deterministic here): "we don't
    // know" (low coverage) must be visually distinct from "there is little here"
    // (low density, high coverage).
    expect(readsAsDensity(LOW_COVERAGE_BIN)).toBe(false); // we don't know
    expect(readsAsDensity(LOW_DENSITY_BIN)).toBe(true); // little here, and we looked

    const maxCount = Math.max(...DENSITY_BINS.map((b) => b.deviceCount));
    const unknown = renderBin(LOW_COVERAGE_BIN, maxCount);
    const little = renderBin(LOW_DENSITY_BIN, maxCount);
    // The low-coverage cell is desaturated + hatched; the low-density one is not.
    expect(unknown.coverage.desaturated).toBe(true);
    expect(unknown.coverage.hatched).toBe(true);
    expect(little.coverage.desaturated).toBe(false);
    expect(little.coverage.hatched).toBe(false);
    // And the two encodings are not equal — they never conflate.
    expect(unknown.coverage).not.toEqual(little.coverage);
  });

  it("a low-coverage cell's count never renders as a confident density bucket", () => {
    const maxCount = Math.max(...DENSITY_BINS.map((b) => b.deviceCount));
    // Even if a low-coverage cell had a high count, its value is suppressed to 0.
    const spike = renderBin({ ...LOW_COVERAGE_BIN, deviceCount: maxCount }, maxCount);
    expect(spike.densityBucket).toBe(0);
  });

  it("covers every coverage level", () => {
    for (const level of COVERAGE_LEVELS) expect(coverageEncoding(level).level).toBe(level);
  });
});

describe("national-zoom density binning + per-tier point honesty (SIG-UI-019)", () => {
  it("bins at national zoom, points once zoomed in", () => {
    expect(renderModeForZoom(NATIONAL_ZOOM_MAX)).toBe("bins");
    expect(renderModeForZoom(NATIONAL_ZOOM_MAX - 2)).toBe("bins");
    expect(renderModeForZoom(NATIONAL_ZOOM_MAX + 1)).toBe("points");
  });

  it("a point appears only where the zoom supports the tier's precision", () => {
    // Tier 0 (full precision) may appear just past national zoom.
    expect(pointVisibleAtZoom(0, NATIONAL_ZOOM_MAX + 1)).toBe(true);
    expect(pointVisibleAtZoom(0, NATIONAL_ZOOM_MAX)).toBe(false);
    // Tier 2 (H3-binned) needs a much closer zoom before a point is honest.
    expect(pointVisibleAtZoom(2, NATIONAL_ZOOM_MAX + 1)).toBe(false);
    expect(pointVisibleAtZoom(2, MIN_POINT_ZOOM_BY_TIER[2]!)).toBe(true);
    // Tier 3 is NEVER a point (no published geometry).
    for (const z of [8, 12, 18, 22]) expect(pointVisibleAtZoom(3, z)).toBe(false);
    expect(MIN_POINT_ZOOM_BY_TIER[3]).toBeNull();
  });

  it("declares a min zoom for every sensitivity tier", () => {
    for (const t of SENSITIVITY_TIERS) expect(t in MIN_POINT_ZOOM_BY_TIER).toBe(true);
  });
});

describe("no-coordinate assets as jurisdiction indicators, never dropped (SIG-UI-020)", () => {
  it("partitions into locatable + jurisdiction indicators with nothing dropped", () => {
    const { locatable, jurisdictionIndicators } = partitionByLocatability(MAP_ASSETS);
    const rolledUp = jurisdictionIndicators.reduce((n, j) => n + j.count, 0);
    // Conservation: every asset is either a point or in a jurisdiction indicator.
    expect(locatable.length + rolledUp).toBe(MAP_ASSETS.length);
  });

  it("a tier-3 asset with coordinates is still a jurisdiction indicator, not a point", () => {
    const tier3: MapAsset = {
      id: "device:conf",
      label: "Confidential",
      jurisdiction: "Oklahoma City",
      tier: 3,
      lat: 35.5,
      lon: -97.5,
      precision: "jurisdiction only",
    };
    expect(isLocatable(tier3)).toBe(false);
    const { locatable } = partitionByLocatability([tier3]);
    expect(locatable).toHaveLength(0);
  });

  it("a coordinate-less asset becomes a jurisdiction indicator", () => {
    const { jurisdictionIndicators } = partitionByLocatability(MAP_ASSETS);
    const tulsa = jurisdictionIndicators.find((j) => j.jurisdiction === "Tulsa");
    expect(tulsa?.assetIds).toContain("device:tulsa-001");
  });
});

describe("layer catalog + sharing default", () => {
  it("MAP_LAYERS is observed then derived", () => {
    expect(MAP_LAYERS).toEqual([...OBSERVED_LAYERS, ...DERIVED_LAYERS]);
  });
  it("sharing edges default to an ego network, never a hairball (SIG-UI-021)", () => {
    expect(DEFAULT_SHARING_EDGE_VIEW).toBe("ego");
  });
});
