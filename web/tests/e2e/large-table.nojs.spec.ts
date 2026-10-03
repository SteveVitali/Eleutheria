// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// Runs in the "no-js" Playwright project (JavaScript DISABLED). It proves the
// national-scale data-freshness table is usable and SORTABLE without any client
// JavaScript (§15, SIG-UI-034/037): the build-time grouping/summarisation band
// renders, each sort control is a plain GET link to a pre-rendered route, and
// navigating to a sort route yields a genuinely re-ordered table. The map's tabular
// equivalent carries its build-time per-jurisdiction summary the same way.
import { test, expect } from "@playwright/test";
import { REMOVED_FRESHNESS_SORT_PAGES } from "./pages";

test("freshness table shows a build-time summary band and static sort links (no JS)", async ({
  page,
}) => {
  await page.goto("/data-freshness/");
  // Grouping / summarisation: counts by status, rendered server-side.
  await expect(page.getByTestId("freshness-summary")).toBeVisible();
  expect(await page.getByTestId("summary-status").count()).toBeGreaterThan(0);
  // Two static sort controls, each a real GET link (not a button/script).
  // P34.13 (K12b NEW-11): the no-op "stale" and "volatility" sorts were removed —
  // a sort affordance that changes nothing is a false promise.
  const links = page.getByTestId("sort-link");
  await expect(links).toHaveCount(2);
  for (const key of ["source", "status"]) {
    const link = page.locator(`[data-testid="sort-link"][data-sort-key="${key}"]`);
    const href = await link.getAttribute("href");
    expect(href, `sort-by-${key} is a real GET link`).toMatch(/^\/data-freshness\//);
  }
  // The removed no-op sorts have no link either.
  for (const key of ["stale", "volatility"]) {
    await expect(
      page.locator(`[data-testid="sort-link"][data-sort-key="${key}"]`),
    ).toHaveCount(0);
  }
  // The default (base) route is sorted by source.
  await expect(page.locator('[data-testid="sort-link"][data-sort-key="source"]')).toHaveAttribute(
    "aria-current",
    "true",
  );
});

test("navigating to a sort route actually re-orders the table without JS", async ({ page }) => {
  // Sort by status: the pre-rendered /status/ route orders rows by status ascending,
  // so a "degraded" row sorts before every "ok" row.
  await page.goto("/data-freshness/status/");
  await expect(page.locator('[data-testid="sort-link"][data-sort-key="status"]')).toHaveAttribute(
    "aria-current",
    "true",
  );
  const statuses = await page.getByTestId("freshness-status").allTextContents();
  const sorted = [...statuses].sort((a, b) => a.localeCompare(b));
  expect(statuses).toEqual(sorted);
});

test("the removed no-op sort routes are absent from the build (K12b NEW-11)", async ({ page }) => {
  // P34.13: /data-freshness/stale/ and /data-freshness/volatility/ returned the
  // identical alphabetical table — they must 404 now, not silently reappear.
  for (const route of REMOVED_FRESHNESS_SORT_PAGES) {
    const res = await page.goto(route);
    expect(res?.status(), `${route} must not resolve`).toBe(404);
  }
});

test("the map's tabular equivalent carries a build-time per-jurisdiction summary (no JS)", async ({
  page,
}) => {
  await page.goto("/map/");
  await expect(page.getByTestId("assets-summary")).toBeVisible();
  expect(await page.getByTestId("assets-summary-item").count()).toBeGreaterThan(0);
});
