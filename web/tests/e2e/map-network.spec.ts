// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// Render-path assertions for the P15.3 infrastructure map (§39.3) and network
// explorer (§39.4), run in the JS-enabled chromium project. The no-JS content
// baseline is in map-network.nojs.spec.ts.
import { test, expect } from "@playwright/test";

test.describe("infrastructure map (§39.3)", () => {
  test("coverage underlay is bound to the point layer by a single control (SIG-UI-017)", async ({
    page,
  }) => {
    await page.goto("/map/");
    const bound = page.getByTestId("layer-control").filter({ has: page.locator("[data-bound='true']") });
    // Exactly one control is the bound devices+coverage control, governing BOTH.
    const boundControls = page.locator("[data-testid='layer-control'][data-bound='true']");
    await expect(boundControls).toHaveCount(1);
    const governs = await boundControls.getAttribute("data-governs");
    expect(governs).toContain("physical_devices");
    expect(governs).toContain("coverage");
    // No independent control governs the point layer on its own.
    const pointControls = await page
      .locator("[data-testid='layer-control']")
      .evaluateAll((els) =>
        els.filter((e) => (e.getAttribute("data-governs") ?? "").split(",").includes("physical_devices")),
      );
    expect(pointControls.length).toBe(1);
    void bound;
  });

  test("low coverage does not read as low density (SIG-UI-018)", async ({ page }) => {
    await page.goto("/map/");
    const lowCoverage = page.locator("[data-testid='coverage-bin'][data-coverage='low']").first();
    await expect(lowCoverage).toHaveAttribute("data-hatched", "true");
    await expect(lowCoverage).toHaveAttribute("data-desaturated", "true");
    await expect(lowCoverage).toHaveAttribute("data-reads-as-density", "false");
    // A confidently-low-density cell (high coverage) is NOT hatched and DOES read as density.
    const highCoverage = page.locator("[data-testid='coverage-bin'][data-coverage='high']").first();
    await expect(highCoverage).toHaveAttribute("data-hatched", "false");
    await expect(highCoverage).toHaveAttribute("data-reads-as-density", "true");
  });

  test("no-coordinate assets appear as jurisdiction indicators, none dropped (SIG-UI-020)", async ({
    page,
  }) => {
    await page.goto("/map/");
    const indicators = page.getByTestId("jurisdiction-indicator");
    await expect(indicators.first()).toBeVisible();
    // Every asset is either a located row or inside a jurisdiction indicator.
    const located = await page.getByTestId("map-asset-row").count();
    const rolledUp = await indicators.evaluateAll((els) =>
      els.reduce((n, e) => n + Number(e.getAttribute("data-count") ?? 0), 0),
    );
    expect(located + rolledUp).toBe(6); // MAP_ASSETS.length
  });

  test("served from static PMTiles v3 with OSM attribution, no third-party CDN (SIG-GEO-012/013)", async ({
    page,
    request,
  }) => {
    await page.goto("/map/");
    await expect(page.getByTestId("map-attribution")).toContainText("OpenStreetMap");
    const res = await request.get("/map/style.json");
    expect(res.ok()).toBeTruthy();
    const style = await res.json();
    expect(style.metadata["sig:pmtiles_version"]).toBe(3);
    expect(style.metadata["sig:serving"]).toBe("static");
    for (const src of Object.values<{ url: string }>(style.sources)) {
      expect(src.url.startsWith("pmtiles:///")).toBeTruthy(); // self-hosted, relative
      expect(src.url).not.toMatch(/mapbox|maptiler|arcgis|cartocdn/i);
    }
  });
});

test.describe("network explorer (§39.4)", () => {
  test("defaults to an ego network (SIG-UI-022)", async ({ page }) => {
    await page.goto("/network/");
    await expect(page.getByTestId("network-view")).toHaveAttribute("data-default-view", "ego");
  });

  test("every centrality statistic carries an inline ER-quality disclosure (SIG-UI-023)", async ({
    page,
  }) => {
    await page.goto("/network/");
    const stats = page.getByTestId("centrality-stat");
    const count = await stats.count();
    expect(count).toBeGreaterThan(0);
    for (let i = 0; i < count; i += 1) {
      const disclosure = stats.nth(i).getByTestId("er-disclosure");
      await expect(disclosure).toBeVisible();
      await expect(disclosure).toContainText(/entity resolution/i);
    }
  });

  test("three access edge types are distinct and not merged by default (SIG-UI-024)", async ({
    page,
  }) => {
    await page.goto("/network/");
    // Three legend entries, each with a distinct glyph and a distinct dash pattern.
    const legend = page.getByTestId("access-legend-item");
    await expect(legend).toHaveCount(3);
    const glyphs = await legend.evaluateAll((els) => els.map((e) => e.getAttribute("data-glyph")));
    const dashes = await legend.evaluateAll((els) => els.map((e) => e.getAttribute("data-dash")));
    expect(new Set(glyphs).size).toBe(3);
    expect(new Set(dashes).size).toBe(3);
    // Rendered as three separate, unmerged groups.
    const groups = page.getByTestId("access-edge-group");
    await expect(groups).toHaveCount(3);
    const kinds = await groups.evaluateAll((els) => els.map((e) => e.getAttribute("data-kind")));
    expect(new Set(kinds)).toEqual(
      new Set(["configured_access", "observed_use", "declared_policy"]),
    );
  });

  test("access paths show full hops + evidence, speculative beyond threshold (SIG-UI-025)", async ({
    page,
  }) => {
    await page.goto("/network/");
    const paths = page.getByTestId("access-path");
    await expect(paths.first()).toBeVisible();
    // Every hop carries visible per-hop evidence.
    const hops = page.getByTestId("path-hop");
    const hopCount = await hops.count();
    expect(hopCount).toBeGreaterThan(0);
    for (let i = 0; i < hopCount; i += 1) {
      await expect(hops.nth(i).getByTestId("hop-evidence")).toContainText("evidence:");
    }
    // A path longer than the threshold is labelled speculative; a short one is not.
    const speculative = page.locator("[data-testid='access-path'][data-speculative='true']");
    await expect(speculative).toHaveCount(1);
    await expect(speculative.getByTestId("speculative-label")).toContainText(/SPECULATIVE/);
    const headline = page.locator("[data-testid='access-path'][data-headline='true']");
    await expect(headline).toHaveCount(1);
  });
});
