// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// Runs in the "no-js" Playwright project (JavaScript DISABLED). P34.14 (QW-8,
// F-105): jurisdiction DISPLAY NAMES — every place a person reads leads with
// the place's name and keeps the code secondary ("Name (CODE)"), never a bare
// code alone. These are static-HTML invariants (SIG-UI-036/037): a display name
// must be present in the built bytes, not painted by a script.
import { test, expect } from "@playwright/test";

// A bare emitted jurisdiction code looks like "AL", "AU-QLD", "US", "ID" —
// uppercase alphanumerics and dashes only (never a real name, which carries
// lowercase letters).
const BARE_CODE = /^[A-Z0-9-]+$/;

test("the dossier index leads with place names, codes secondary, no-JS", async ({ page }) => {
  await page.goto("/dossier/");
  const items = page.getByTestId("dossier-index-item");
  const count = await items.count();
  expect(count).toBeGreaterThan(0);
  for (let i = 0; i < count; i++) {
    const place = items.nth(i).locator(".sig-dossier-index__place");
    const text = (await place.innerText()).trim();
    expect(text, `index row ${i} shows a name, not a bare code`).not.toMatch(BARE_CODE);
    // The linked dossier page renders the same display label.
    const href = await items.nth(i).locator("a.sig-dossier-index__link").getAttribute("href");
    expect(href).toBeTruthy();
    const detail = await page.goto(href!);
    expect(detail?.ok()).toBe(true);
    await expect(page.getByTestId("dossier-jurisdiction")).toHaveText(text);
    // The page's own heading never ends in a bare code (" — AL").
    const h1 = (await page.locator("h1").innerText()).trim();
    expect(h1, `${href} h1 does not end in a bare code`).not.toMatch(/ — [A-Z0-9-]{1,8}$/);
    await page.goto("/dossier/");
  }
});

test("the home page reach list leads with place names, no-JS", async ({ page }) => {
  await page.goto("/");
  const places = page.locator(".sig-jurisdiction-reach__place");
  const count = await places.count();
  expect(count).toBeGreaterThan(0);
  for (let i = 0; i < count; i++) {
    const text = (await places.nth(i).innerText()).replace(/^—\s*/, "").trim();
    expect(text, `reach row ${i} shows a name, not a bare code`).not.toMatch(BARE_CODE);
  }
});

test("no dossier claims a mix it does not have — the combines note is mixed-only", async ({
  page,
}) => {
  // None of today's fixture dossiers is a physically mixed bucket (ID/MN), so
  // the K4 NEW-1 sentence must be absent — it is never asserted where untrue.
  await page.goto("/dossier/oklahoma-city/");
  await expect(page.getByTestId("dossier-combines")).toHaveCount(0);
  await expect(page.getByTestId("dossier-jurisdiction-unmapped")).toHaveCount(0);
});
