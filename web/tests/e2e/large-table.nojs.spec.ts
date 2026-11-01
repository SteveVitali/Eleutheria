// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// Runs in the "no-js" Playwright project (JavaScript DISABLED). P36.48 (UX9-3,
// SIG-TRANSP-028): the sources table is usable and SORTABLE without any client
// JavaScript — three views, asc/desc sort routes, facet routes and the A–Z
// list are all plain GETs (K9 §6.1). The retired /data-freshness/ routes emit
// no page (they answer 301 through the generated include).
import { test, expect } from "@playwright/test";
import { REMOVED_FRESHNESS_SORT_PAGES } from "./pages";

test("the sources table renders the view switch, sort links and the A–Z list (no JS)", async ({
  page,
}) => {
  await page.goto("/sources/");
  await expect(page.getByTestId("sources-table")).toBeVisible();
  expect(await page.getByTestId("source-table-row").count()).toBeGreaterThan(0);
  // Every sortable column carries a plain GET link to a pre-rendered route.
  const links = page.getByTestId("sort-link");
  expect(await links.count()).toBeGreaterThanOrEqual(8);
  for (const key of ["source", "status", "freshness", "claims"]) {
    const href = await page
      .locator(`[data-testid="sort-link"][data-sort-key="${key}"]`)
      .getAttribute("href");
    expect(href, `sort-by-${key} is a real GET link`).toContain("/sources/sort/");
  }
  await expect(page.getByTestId("az-index")).toBeVisible();
  await expect(page.getByTestId("facet-menu")).toBeVisible();
});

test("a sort route actually re-orders the table without JS (K9 C-3)", async ({ page }) => {
  await page.goto("/sources/sort/status/asc/");
  const statuses = await page
    .locator('[data-testid="source-table-row"] [data-testid="cell-status"]')
    .allTextContents();
  expect(statuses.length).toBeGreaterThan(1);
  // Asc sort puts `published` (partition rank 0) first.
  expect(statuses[0]).toContain("published");
});

test("a facet route filters the row set to its predicate (no JS)", async ({ page }) => {
  await page.goto("/sources/by/status/published/");
  const rows = page.locator('[data-testid="source-table-row"]');
  expect(await rows.count()).toBeGreaterThan(0);
  for (const cell of await page.locator('[data-testid="cell-status"]').allTextContents()) {
    expect(cell).toContain("published");
  }
});

test("the retired /data-freshness/ routes emit no page (301 map owns them)", async ({ page }) => {
  for (const route of ["/data-freshness/", ...REMOVED_FRESHNESS_SORT_PAGES]) {
    const res = await page.goto(route);
    expect(res?.status(), `${route} must not resolve to a page`).toBe(404);
  }
});

test("the map's tabular equivalent carries a build-time per-jurisdiction summary (no JS)", async ({
  page,
}) => {
  await page.goto("/map/");
  await expect(page.getByTestId("assets-summary")).toBeVisible();
  expect(await page.getByTestId("map-places-row").count()).toBeGreaterThan(0);
});
