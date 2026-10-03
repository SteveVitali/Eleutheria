// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// Runs in the "chromium" Playwright project (JavaScript enabled). P34.14
// (QW-8, F-105): the search surface leads with place names too — the quick
// filter's labels and sublabels carry "Name (CODE)", so a name a person types
// now matches rows that used to show only a bare code.
import { test, expect } from "@playwright/test";

const BARE_CODE = /^[A-Z0-9-]+$/;

test("the search index leads with place names, codes secondary", async ({ page }) => {
  await page.goto("/search/");
  await expect(page.getByTestId("search-island")).toBeVisible();
  const results = page.getByTestId("search-result");
  const count = await results.count();
  expect(count).toBeGreaterThan(0);
  for (let i = 0; i < count; i++) {
    const sub = (await results.nth(i).locator(".sig-search-island__kind").innerText()).trim();
    // Source rows carry a status sublabel (not a jurisdiction) — skip those.
    if (sub.startsWith("status:")) continue;
    expect(sub, `result ${i} sublabel shows a name, not a bare code`).not.toMatch(BARE_CODE);
  }
});

test("a place name typed into the filter finds the dossier (F-105)", async ({ page }) => {
  await page.goto("/search/");
  const input = page.getByTestId("search-input");
  // The fixture dossier's jurisdiction IS a name; before P34.14 an export-mode
  // row labelled " — AL" would never match "Alabama".
  await input.fill("Oklahoma");
  const results = page.getByTestId("search-result");
  await expect(results.first()).toBeVisible();
  const texts = await results.allInnerTexts();
  expect(texts.some((t) => t.toLowerCase().includes("oklahoma"))).toBe(true);
});
