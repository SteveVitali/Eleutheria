// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// P36.22 (UXK14-3a, SIG-UI-037) — the no-JS half of the component-kit-A
// contract: the whole visual layer is complete server-rendered HTML. Every
// stat, card, table, chip and badge reads identically with JavaScript off —
// there is nothing to upgrade and nothing to lose. Runs in the "no-js"
// project (JavaScript disabled).

import { test, expect } from "@playwright/test";

const HARNESS = "/component-kit/";

test("every kit component is complete with JavaScript disabled", async ({ page }) => {
  await page.goto(HARNESS);
  // Stat row: grouped numerals inside figure regions, denominators named.
  const row = page.getByTestId("kit-stat-row");
  await expect(row).toContainText("64,212");
  await expect(row.locator("[data-figure-id]")).toHaveCount(2);

  // The six card kinds + the typed empty card.
  const grid = page.getByTestId("kit-card-grid");
  for (const kind of ["place", "organization", "source", "task", "persona", "example"]) {
    await expect(grid.locator(`[data-card-kind="${kind}"]`).first()).toBeVisible();
  }
  await expect(grid.getByTestId("empty-state")).toHaveAttribute(
    "data-cause",
    "not_published",
  );

  // Table shell at all three densities, sort links navigable as plain GETs.
  for (const density of ["compact", "default", "roomy"]) {
    await expect(
      page.getByTestId(`kit-table-${density}`).locator("table"),
    ).toBeVisible();
  }
  await expect(
    page.getByTestId("kit-table-default").locator("th a.sig-table__sortlink").first(),
  ).toBeVisible();

  // Chips + badges — text channels, fully rendered.
  await expect(page.getByTestId("support-chip")).toHaveCount(2);
  await expect(page.getByTestId("field-chips").locator("[data-field]")).toHaveCount(4);
  await expect(
    page.getByTestId("kit-badge-block").getByTestId("badge-directness"),
  ).toHaveCount(6);
});

test("no enhancement chrome and no script exists on the harness", async ({ page }) => {
  await page.goto(HARNESS);
  await expect(page.locator("[data-enhancement]")).toHaveCount(0);
  await expect(page.locator("main script")).toHaveCount(0);
});
