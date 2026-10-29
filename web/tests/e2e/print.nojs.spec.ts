// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// P36.26 (SIG-UI-155): the print document with JavaScript disabled — the T0
// route ships zero client JS, so the council brief, the running chrome, the
// declared figure slot, and the terms strip must all render identically.
import { test, expect } from "@playwright/test";
import { DOSSIER_PRINT } from "./pages";

test("the print document is complete with JavaScript disabled", async ({ page }) => {
  await page.goto(DOSSIER_PRINT);
  const pages = page.getByTestId("print-page");
  const total = await pages.count();
  expect(total).toBeGreaterThanOrEqual(6);
  // Council brief on page 1.
  await expect(pages.first()).toHaveAttribute("data-page-kind", "brief");
  await expect(pages.first().getByTestId("brief-qr").locator("svg")).toBeAttached();
  // Running chrome on every page.
  for (let i = 0; i < total; i++) {
    await expect(pages.nth(i).getByTestId("print-pageno")).toHaveText(`Page ${i + 1}/${total}`);
    await expect(pages.nth(i).getByTestId("print-footer")).toContainText("As of world");
  }
  // The figure page and the terms strip.
  await expect(page.getByTestId("print-figure")).toBeAttached();
  await expect(pages.last().getByTestId("print-terms")).toContainText("Terms used on this page");
  // And the proof of T0: no script made it into the DOM.
  expect(await page.locator("script").count()).toBe(0);
});
