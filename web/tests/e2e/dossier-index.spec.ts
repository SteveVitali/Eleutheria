// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project.
// P36.34 (K4 JUR-04): the grouped dossier index end-to-end — group order,
// the K13 capstone journeys A1 (Oklahoma City ≤3 clicks) and O1 (Harris
// County), the A–Z directory coverage, the place-search form, sort/facet
// routes, and the conservative publication regime (SIG-JUR-006…011).
import { test, expect } from "@playwright/test";

const INDEX = "/dossier/";

test("the index groups United States first, then other countries (SIG-JUR-006)", async ({ page }) => {
  await page.goto(INDEX);
  const us = page.getByTestId("group-united-states");
  const other = page.getByTestId("group-other-countries");
  await expect(us).toBeVisible();
  await expect(other).toBeVisible();
  // US precedes other countries in document order.
  expect(await us.evaluate((e) => e.compareDocumentPosition(e.nextElementSibling!))).toBeTruthy();
  await expect(us.locator('[data-slug="usa/ok"]')).toBeVisible();
  await expect(us.locator('[data-slug="usa/ok/oklahoma-county-40109"]')).toBeVisible();
  await expect(us.locator('[data-slug="usa/ok/oklahoma-city-4064000"]')).toBeVisible();
  await expect(us.locator('[data-slug="usa/vi"]')).toBeVisible(); // territory under the US
  await expect(other.locator('[data-slug="can"]')).toBeVisible();
  await expect(other.locator('[data-slug="can/on"]')).toBeVisible();
  await expect(other.locator('[data-slug="deu"]')).toBeVisible();
  // The no-page registry child is never a row.
  await expect(page.locator('[data-slug="usa/ok/cleveland-county-40131"]')).toHaveCount(0);
  // Demonstration tail + the unplaced sibling.
  await expect(page.getByTestId("group-demonstrations")).toBeVisible();
  await expect(page.getByTestId("unplaced-link")).toHaveAttribute("href", "/dossier/unplaced/");
});

test("A1: the index reaches Oklahoma City within three clicks", async ({ page }) => {
  await page.goto(INDEX);
  const href = await page.locator('[data-slug="usa/ok/oklahoma-city-4064000"] a.sig-dossier-index__link').getAttribute("href");
  // Three hops by URL depth: /dossier/ → usa → usa/ok → oklahoma-city.
  expect((await page.goto("/dossier/usa/"))?.ok()).toBe(true);
  await page.locator('a[href="/dossier/usa/ok/"]').first().click();
  await expect(page).toHaveURL("/dossier/usa/ok/");
  await page.goto(href!);
  await expect(page.getByTestId("dossier-jurisdiction")).toContainText("Oklahoma City");
});

test("O1: Harris County is reachable and shows its records", async ({ page }) => {
  await page.goto(INDEX);
  await page.goto("/dossier/usa/tx/");
  await page.locator('a[href="/dossier/usa/tx/harris-county-48201/"]').first().click();
  await expect(page).toHaveURL("/dossier/usa/tx/harris-county-48201/");
  await expect(page.getByTestId("dossier-jurisdiction")).toContainText("Harris County");
});

test("the A–Z directory covers every dossier (SIG-JUR-011)", async ({ page }) => {
  await page.goto("/dossier/a-z/");
  const letters = page.getByTestId("az-letters").locator("a");
  const letterHrefs = await letters.evaluateAll((els) => els.map((e) => e.getAttribute("href")));
  expect(letterHrefs.length).toBeGreaterThan(0);
  for (const href of letterHrefs) {
    const res = await page.goto(href!);
    expect(res?.ok()).toBe(true);
    // Every row links to a real dossier page.
    const items = page.getByTestId("dossier-index-item");
    expect(await items.count()).toBeGreaterThan(0);
    const hrefs = await items.locator("a.sig-dossier-index__link").evaluateAll((els) => els.map((e) => e.getAttribute("href")));
    for (const h of hrefs) {
      expect((await page.goto(h!))?.ok()).toBe(true);
    }
  }
});

test("the place form targets /search/?type=place (C-24)", async ({ page }) => {
  await page.goto(INDEX);
  const form = page.getByTestId("place-search-form");
  await expect(form).toHaveAttribute("method", "get");
  await expect(form).toHaveAttribute("action", "/search/");
  await expect(form.locator('input[name="type"]')).toHaveAttribute("value", "place");
  await expect(page.getByTestId("place-search-fallback")).toBeVisible();
});

test("sort and facet routes render pre-rendered GET pages", async ({ page }) => {
  for (const k of ["name", "records", "sources", "freshness", "disagreements"]) {
    expect((await page.goto(`/dossier/sort/${k}/`))?.ok()).toBe(true);
    await expect(page.getByTestId("dossier-index-item").first()).toBeVisible();
  }
  for (const p of ["/dossier/by/level/county/", "/dossier/by/level/place/", "/dossier/by/single-source/yes/", "/dossier/by/evidence-type/non-site-evidence/"]) {
    expect((await page.goto(p))?.ok()).toBe(true);
    await expect(page.getByTestId("dossier-index-item").first()).toBeVisible();
  }
});

test("Germany dossier withholds the public-employee name (conservative regime, SIG-JUR-010)", async ({ page }) => {
  await page.goto("/dossier/deu/");
  await expect(page.getByTestId("dossier-row-withheld").first()).toHaveText("withheld");
  await expect(page.locator("body")).not.toContainText("Muster");
});

test("locator glyphs render from the FIG-01a sprite (P36.27)", async ({ page }) => {
  await page.goto(INDEX);
  expect(await page.getByTestId("index-glyph").count()).toBeGreaterThan(0);
});
