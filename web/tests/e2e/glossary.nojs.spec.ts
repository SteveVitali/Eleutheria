// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// P36.17 — the no-JS leg: /glossary/ is T1, so everything the page knows is in
// the server HTML; the <Term> popover is a native-HTML feature whose content
// is in the DOM whether or not JS runs (SIG-UI-037/050).
import { test, expect } from "@playwright/test";

test.describe("glossary with JavaScript off", () => {
  test("renders the complete entry set in server HTML", async ({ page }) => {
    await page.goto("/glossary/");
    expect(await page.getByTestId("glossary-entry").count()).toBeGreaterThan(40);
    await expect(page.locator("main")).toContainText("None found");
    await expect(page.locator("main")).toContainText("possible duplicate");
    await expect(page.locator("main")).toContainText(
      "2+ source records; republications not yet collapsed",
    );
  });

  test("<Term>'s definition and glossary link exist without JS", async ({ page }) => {
    await page.goto("/methodology/");
    const term = page.locator(".sig-term[data-term='claim']");
    await expect(term.locator(".sig-term__link")).toHaveAttribute("href", "/glossary/#claim");
    // The popover content is in the DOM — the native popover shows it where
    // supported; the glossary anchor is the always-works affordance.
    await expect(page.locator("span#td-claim")).toHaveCount(1);
    await page.goto("/glossary/#claim");
    await expect(page.locator("#claim")).toBeVisible();
    await expect(page.locator("main")).toContainText("An assertion with a subject");
  });
});
