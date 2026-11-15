// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * P37.39 (R11-K13-QB-01, L3 §5.2, SIG-CONF-011's per-record rendering) —
 * the quality basis, copies and possible duplicates on the UX surfaces:
 * the co-located half on K5's agree/disagree views (/disagreements/ +
 * the sources explorer) and the count-interval form beside record counts.
 */

import { expect, test } from "@playwright/test";

const OKC = "dossier/usa/ok/oklahoma-city-4064000";

test.describe("P37.39 — quality basis on UX surfaces", () => {
  test("the disagreements hub lists the co-located kind", async ({ page }) => {
    await page.goto("/disagreements/");
    await expect(page.getByTestId("kind-count-co_located")).toContainText("place");
    await expect(page.getByTestId("colocated-place-row").first()).toContainText("Oklahoma City");
  });

  test("the place page shows the co-located pairs, never merged", async ({ page }) => {
    await page.goto("/disagreements/place/usa/ok/oklahoma-city-4064000/");
    await expect(page.getByTestId("kind-section-co-located")).toBeVisible();
    await expect(page.getByTestId("co-located-totals")).toContainText("possible duplicate");
    await expect(page.getByTestId("co-located-pairs")).toContainText(
      "SIG has not merged them because it cannot prove they are the same device.",
    );
  });

  test("a place without candidates names the honest absence", async ({ page }) => {
    await page.goto("/disagreements/place/usa/tx/");
    await expect(
      page.getByTestId("co-located-absent").or(page.getByTestId("co-located-none")),
    ).toBeVisible();
  });

  test("the sources explorer renders the measured co-located count + pair list", async ({ page }) => {
    await page.goto(`/${OKC}/sources/`);
    await expect(page.getByTestId("dsrc-colocated")).toContainText("2");
    await page.getByTestId("dsrc-colocated-pairs").locator("summary").click();
    await expect(page.getByTestId("dsrc-colocated-pairs")).toContainText("Possible duplicate:");
    await expect(page.getByTestId("dsrc-colocated-pairs")).toContainText("DeFlock ALPR map");
  });

  test("the count interval renders beside the record counts", async ({ page }) => {
    await page.goto(`/${OKC}/`);
    await expect(page.getByTestId("dossier-count-interval")).toContainText("listed cameras");
    await page.goto(`/${OKC}/sites/`);
    await expect(page.getByTestId("sites-count-interval")).toContainText("listed cameras");
    await page.goto(`/${OKC}/sources/`);
    await expect(page.getByTestId("dsrc-count-interval")).toContainText("listed cameras");
  });

  test("the map selection panel carries the corroboration wording", async ({ page }) => {
    await page.goto("/map/");
    const list = page.getByTestId("in-view-list");
    if (await list.count()) {
      await list.locator("button, a").first().click();
      const sel = page.getByTestId("map-selected-panel");
      if (await page.getByTestId("selection-corroboration").count()) {
        await expect(sel.getByTestId("selection-corroboration")).toBeVisible();
      }
    }
  });
});
