// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// Runs in the "no-js" Playwright project (JavaScript DISABLED). Proves the map has a
// usable TABULAR equivalent and the network a usable LIST equivalent without any
// client JavaScript (SIG-UI-037, AC5), and that the honest-rendering signals the
// deterministic ACs turn on are present in the static HTML.
import { test, expect } from "@playwright/test";

test("map has a populated tabular equivalent without JS (SIG-UI-037)", async ({ page }) => {
  await page.goto("/map/");
  // The located-assets table and the coverage-bins table both carry rows.
  await expect(page.getByTestId("map-asset-row").first()).toBeVisible();
  await expect(page.getByTestId("coverage-bin").first()).toBeVisible();
  // The jurisdiction indicators for point-less assets are present (SIG-UI-020).
  await expect(page.getByTestId("jurisdiction-indicator").first()).toBeVisible();
  // OSM attribution is in the static HTML (every context, incl. no-JS/print).
  await expect(page.getByTestId("map-attribution")).toContainText("OpenStreetMap");
});

test("low-coverage ≠ low-density is encoded in the static HTML (SIG-UI-018)", async ({ page }) => {
  await page.goto("/map/");
  const low = page.locator("[data-testid='coverage-bin'][data-coverage='low']").first();
  await expect(low).toHaveAttribute("data-reads-as-density", "false");
  const high = page.locator("[data-testid='coverage-bin'][data-coverage='high']").first();
  await expect(high).toHaveAttribute("data-reads-as-density", "true");
});

test("network has a populated list equivalent without JS (SIG-UI-037)", async ({ page }) => {
  await page.goto("/network/");
  // The three access-edge groups and their edges are plain lists.
  await expect(page.getByTestId("access-edge-group")).toHaveCount(3);
  await expect(page.getByTestId("access-edge").first()).toBeVisible();
  // The access-path hops with per-hop evidence are a plain ordered list.
  await expect(page.getByTestId("path-hop").first()).toBeVisible();
  await expect(page.getByTestId("hop-evidence").first()).toContainText("evidence:");
});

test("every centrality statistic discloses ER quality inline without JS (SIG-UI-023)", async ({
  page,
}) => {
  await page.goto("/network/");
  const stats = page.getByTestId("centrality-stat");
  const count = await stats.count();
  expect(count).toBeGreaterThan(0);
  for (let i = 0; i < count; i += 1) {
    await expect(stats.nth(i).getByTestId("er-disclosure")).toContainText(/entity resolution/i);
  }
});
