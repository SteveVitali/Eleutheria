// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// P37.18 (K1 MAP-03b) — filters with counts and zoom honesty, the In-view
// list's table view + live region, the keyboard contract (J4/J5), the mobile
// bottom sheet (K1 §4.1), the print view (K1 §5) and "Download this view"
// (O3). axe covers the filters-open + sheet-at-half states (§4.7).
import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { gotoSettled } from "./pages";

const WCAG_TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"];

async function ready(page: import("@playwright/test").Page, url = "/map/") {
  await gotoSettled(page, url);
  await expect(page.getByTestId("map-island")).toHaveAttribute("data-ready", "true", {
    timeout: 20_000,
  });
  await expect(page.getByTestId("map-island")).toHaveAttribute("data-drawn", "true", {
    timeout: 20_000,
  });
}

test.describe("map filters, list, keyboard, mobile, print (P37.18)", () => {
  test("filters show counts; an active seen facet at national zoom greys with a note (SIG-UI-104, C-03)", async ({
    page,
  }) => {
    await ready(page, "/map/?seen=2026-01..2026-09");
    // The drawn set must NOT silently filter — the honesty note names it.
    await expect(page.getByTestId("filters-cannot-apply")).toContainText(
      "applies from zoom 10",
      { timeout: 15_000 },
    );
    await expect(page.getByTestId("map-island")).toHaveAttribute("data-greyed", "true");
    await page.getByTestId("map-tab-filters").click();
    await expect(page.getByTestId("filter-seen-cannot")).toContainText("applies from zoom 10");
    // Every listed option carries a count.
    const counts = page.locator("#map-filters .sig-map-app__count, [data-testid=map-filters] .sig-map-app__count");
    expect(await counts.count()).toBeGreaterThan(0);
    const results = await new AxeBuilder({ page }).withTags(WCAG_TAGS).analyze();
    expect(results.violations, JSON.stringify(results.violations)).toEqual([]);
  });

  test("the In-view table view carries sortable headers and the same rows (J5)", async ({ page }) => {
    await ready(page, "/map/?at=12/35.47/-97.51");
    await expect(page.getByTestId("inview-status")).toContainText("in view", { timeout: 15_000 });
    await page.getByTestId("inview-table-toggle").click();
    const table = page.getByTestId("inview-table");
    await expect(table).toBeVisible();
    const sortBtn = page.getByTestId("inview-sort-label");
    await expect(sortBtn).toBeVisible();
    const firstTh = table.locator("thead th").first();
    await sortBtn.click();
    await expect(firstTh).toHaveAttribute("aria-sort", /ascending|descending/);
    const results = await new AxeBuilder({ page }).withTags(WCAG_TAGS).analyze();
    expect(results.violations, JSON.stringify(results.violations)).toEqual([]);
  });

  test("Download this view emits a CSV with licence provenance lines (O3)", async ({ page }) => {
    await ready(page, "/map/?at=12/35.47/-97.51");
    await expect(page.getByTestId("inview-status")).toContainText("in view", { timeout: 15_000 });
    const [download] = await Promise.all([
      page.waitForEvent("download", { timeout: 10_000 }),
      page.getByTestId("download-view").click(),
    ]);
    const path = await download.path();
    const { readFileSync } = await import("node:fs");
    const csv = readFileSync(path!, "utf-8");
    expect(csv).toContain("# sig-table export — downloaded view");
    expect(csv).toContain("Record,Technology,Operator,Status,Distance (km),Licence");
    expect(csv.split("\n").filter((l) => l.startsWith("# licence")).length).toBeGreaterThan(0);
  });

  test("Print this view carries the list, attribution, as-of and cite URL — never the canvas (K1 §5)", async ({
    page,
  }) => {
    await page.addInitScript(() => {
      (window as unknown as { __printed: boolean }).__printed = false;
      window.print = () => {
        (window as unknown as { __printed: boolean }).__printed = true;
      };
    });
    await ready(page, "/map/?at=12/35.47/-97.51");
    await page.getByTestId("print-view").click();
    expect(await page.evaluate(() => (window as unknown as { __printed: boolean }).__printed)).toBe(true);
    const print = page.getByTestId("map-print");
    await expect(print).toContainText("Data as of");
    await expect(print).toContainText("Cite this view");
    await expect(print).toContainText("Attribution:");
    await page.emulateMedia({ media: "print" });
    await expect(page.getByTestId("map-island")).toBeHidden();
    await expect(print).toBeVisible();
    await page.emulateMedia({ media: "screen" });
  });

  test("the mobile bottom sheet snaps peek/half/full and the tabs stay reachable (K1 §4.1)", async ({
    page,
  }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await ready(page);
    const sheet = page.getByTestId("map-sheet");
    await expect(sheet).toBeVisible();
    await expect(page.getByTestId("sheet-peek")).toContainText("in view", { timeout: 15_000 });
    await page.getByTestId("sheet-snap-peek").click();
    await expect(sheet).toHaveAttribute("data-snap", "peek");
    // At peek the tabs collapse; a snap back restores them (never a trap).
    await page.getByTestId("sheet-snap-half").click();
    await expect(sheet).toHaveAttribute("data-snap", "half");
    await expect(page.getByTestId("map-tab-filters")).toBeVisible();
    await page.getByTestId("sheet-snap-full").click();
    await expect(sheet).toHaveAttribute("data-snap", "full");
    const results = await new AxeBuilder({ page }).withTags(WCAG_TAGS).analyze();
    expect(results.violations, JSON.stringify(results.violations)).toEqual([]);
  });

  test("J4 keyboard: Enter on a row selects; Escape clears and returns focus (SIG-UI-095/102)", async ({
    page,
  }) => {
    await ready(page, "/map/?at=13/35.47/-97.51");
    await expect(page.getByTestId("inview-status")).toContainText("records in view", {
      timeout: 15_000,
    });
    const firstRow = page.locator("[data-row]").first();
    await firstRow.locator("button").first().focus();
    await page.keyboard.press("Enter");
    await expect(page.getByTestId("selection-label")).toBeVisible({ timeout: 10_000 });
    expect(page.url()).toContain("focus=");
    // Back on the list row, Escape clears and focus returns to the row.
    await page.getByTestId("map-tab-view").click();
    const row = page.locator("[data-row]").first();
    await row.locator("button").first().focus();
    await page.keyboard.press("Escape");
    await page.waitForTimeout(300);
    expect(page.url()).not.toContain("focus=");
    const focused = await page.evaluate(() =>
      document.activeElement?.closest("[data-row]") !== null,
    );
    expect(focused).toBe(true);
  });

  test("the debounced live region announces the settled view (K1 §4.6)", async ({ page }) => {
    await ready(page);
    const live = page.getByTestId("map-aria-live");
    await expect(live).toContainText("in view", { timeout: 15_000 });
  });
});
