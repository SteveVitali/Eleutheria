// SPDX-License-Identifier: Apache-2.0
// P36.36 (SIG-UI-105): the no-JS map baseline — overview, place form, places
// table; every link resolves; ≤ 100 KiB is wire-measured by budget.spec.ts.
import { test, expect } from "@playwright/test";

test("no-JS /map/ shows overview, place form, places table and stateful-URL notice", async ({ page }) => {
  await page.goto("/map/?v=2&at=12/35.4/-97.5");
  await expect(page.getByTestId("no-js-state-notice")).toBeVisible();
  await expect(page.getByTestId("map-overview")).toBeVisible();
  await expect(page.getByTestId("place-search-form")).toBeVisible();
  await expect(page.getByTestId("map-places-row").first()).toBeVisible();
  await expect(page.getByTestId("map-attribution")).toContainText("OpenStreetMap");
});

test("places table links resolve to dossiers and sites lists (SIG-UI-068)", async ({ page, request }) => {
  await page.goto("/map/");
  const links = page.getByTestId("sites-list-link");
  expect(await links.count()).toBeGreaterThan(0);
  for (let i = 0; i < (await links.count()); i += 1) {
    const href = await links.nth(i).getAttribute("href");
    const res = await request.get(href!);
    expect(res.ok(), `${href} 404s`).toBeTruthy();
  }
});
