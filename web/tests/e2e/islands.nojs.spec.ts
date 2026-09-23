// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// Runs in the "no-js" project (JavaScript DISABLED). Proves the three OPT-IN islands
// (P27.9, ADR-097) preserve a fully-usable no-JS fallback (SIG-UI-037/050): with JS
// off the island itself renders nothing (client:only), but the tabular / list /
// browse equivalent on each page is present and usable. The island is progressive
// enhancement, NEVER a replacement.
import { test, expect } from "@playwright/test";

test("map: without JS the island is inert but the tabular equivalent is usable", async ({
  page,
}) => {
  await page.goto("/map/");
  // The island section exists in the HTML but did not hydrate (no MapLibre canvas).
  await expect(page.getByTestId("map-island-section")).toBeVisible();
  await expect(page.locator(".maplibregl-canvas")).toHaveCount(0);
  // The no-JS fallback: the located-assets table and OSM attribution are present.
  await expect(page.getByTestId("map-asset-row").first()).toBeVisible();
  await expect(page.getByTestId("map-attribution")).toContainText("OpenStreetMap");
});

test("network: without JS the island is inert but the list equivalent is usable", async ({
  page,
}) => {
  await page.goto("/network/");
  await expect(page.getByTestId("graph-island-section")).toBeVisible();
  await expect(page.getByTestId("network-island")).toHaveCount(0);
  // The no-JS fallback: the access-edge groups and access-path hops are present.
  await expect(page.getByTestId("access-edge").first()).toBeVisible();
  await expect(page.getByTestId("path-hop").first()).toBeVisible();
});

test("search: without JS the island is inert but the browse index is usable", async ({ page }) => {
  await page.goto("/search/");
  await expect(page.getByTestId("search-island-section")).toBeVisible();
  await expect(page.getByTestId("search-input")).toHaveCount(0);
  // The no-JS fallback: real GET links to the dossier index, the map and the sources.
  const browse = page.getByTestId("search-browse");
  await expect(browse).toBeVisible();
  await expect(browse.locator("a[href='/dossier/']")).toBeVisible();
  await expect(browse.locator("a[href='/map/']")).toBeVisible();
  await expect(browse.locator("a[href='/data-freshness/']")).toBeVisible();
});
