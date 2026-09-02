// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// Runs in the "no-js" Playwright project (JavaScript DISABLED). The dossier is the
// project's primary public artifact and must be fully usable without JavaScript
// (SIG-UI-036/037): the sections, the gaps, the unknown values, the action blocks,
// and the reconciliations (native <details>, which toggle without JS) are all in the
// static HTML. Since the shell ships zero client JS, disabling it must change nothing.
import { test, expect } from "@playwright/test";
import { DOSSIER_PAGE, DOSSIER_PRINT } from "./pages";

test("the dossier renders all twelve sections and the gap list without JS (SIG-UI-010/011)", async ({
  page,
}) => {
  await page.goto(DOSSIER_PAGE);
  await expect(page.getByTestId("dossier-section")).toHaveCount(12);
  await expect(page.getByTestId("what-we-dont-know-summary")).toBeVisible();
  await expect(page.getByTestId("incompleteness-banner")).toBeVisible();
});

test("a gap hatch is a real GET link that resolves to a task without JS (SIG-UI-007)", async ({
  page,
}) => {
  await page.goto(DOSSIER_PAGE);
  const hatch = page.getByTestId("what-we-dont-know-summary").getByTestId("absence-hatch").first();
  const href = await hatch.getAttribute("href");
  expect(href).toMatch(/^\/task\/new\//);
  await page.goto(href!);
  await expect(page.getByTestId("generated-task")).toBeVisible();
});

test("a reconciliation opens without JS via native <details> (SIG-UI-014)", async ({ page }) => {
  await page.goto(DOSSIER_PAGE);
  const fig = page.getByTestId("dossier-figure").first();
  await fig.locator("summary").click(); // native disclosure, not a JS handler
  await expect(fig.getByTestId("recon-rule")).toBeVisible();
  await expect(fig.getByTestId("recon-claim").first()).toBeVisible();
});

test("an unknown value is rendered without JS (SIG-UI-015)", async ({ page }) => {
  await page.goto(DOSSIER_PAGE);
  await expect(page.locator(".sig-unknown").first()).toHaveText("unknown");
});

test("the print export is paginated with a footer on every page without JS (SIG-UI-013)", async ({
  page,
}) => {
  await page.goto(DOSSIER_PRINT);
  const pageCount = await page.getByTestId("print-page").count();
  expect(pageCount).toBeGreaterThan(1);
  await expect(page.getByTestId("print-footer")).toHaveCount(pageCount);
  await expect(page.getByTestId("print-permalink").first()).toHaveAttribute("href", /ruleset=/);
});
