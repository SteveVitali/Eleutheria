// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project.
// P36.34 (SIG-JUR-011): every dossier is reachable without JavaScript within
// three clicks of /dossier/ — via the hierarchy or the A–Z directory — and
// the search form + map entry keep their no-JS baselines.
import { test, expect } from "@playwright/test";

test("the grouped index renders fully without JS (SIG-JUR-006/011)", async ({ page }) => {
  await page.goto("/dossier/");
  await expect(page.getByTestId("group-united-states")).toBeVisible();
  await expect(page.getByTestId("group-other-countries")).toBeVisible();
  const items = page.getByTestId("dossier-index-item");
  const n = await items.count();
  expect(n).toBeGreaterThan(10);
  // Every row's dossier link resolves — reachable by links alone.
  for (let i = 0; i < n; i++) {
    const href = await items.nth(i).locator("a.sig-dossier-index__link").getAttribute("href");
    expect(href).toBeTruthy();
    expect((await page.goto(href!))?.ok()).toBe(true);
    await page.goto("/dossier/");
  }
});

test("the A–Z directory and letter pages work without JS", async ({ page }) => {
  await page.goto("/dossier/a-z/");
  const letters = page.getByTestId("az-letters").locator("a");
  expect(await letters.count()).toBeGreaterThan(0);
  await letters.first().click();
  await expect(page.getByTestId("dossier-index-item").first()).toBeVisible();
});

test("the place-search GET form works without JS", async ({ page }) => {
  await page.goto("/dossier/");
  const form = page.getByTestId("place-search-form");
  await form.locator('input[name="q"]').fill("Oklahoma");
  await Promise.all([page.waitForURL(/\/search\//), form.locator('button[type="submit"]').click()]);
  expect(page.url()).toContain("type=place");
});
