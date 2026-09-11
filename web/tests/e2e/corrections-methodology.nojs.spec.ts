// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// Runs in the "no-js" Playwright project (JavaScript DISABLED). Proves the P15.5
// surfaces — research queue, corrections log, dispute intake, methodology/freshness/
// coverage, and editorial standards — are usable without any client JavaScript
// (SIG-UI-037), and that the honest-rendering signals the ACs turn on are in the
// static HTML.
import { test, expect } from "@playwright/test";

test("the research queue renders task cards + dispositions without JS (SIG-UI-031/037)", async ({ page }) => {
  await page.goto("/research-queue/");
  const card = page.getByTestId("task-card").first();
  await expect(card).toBeVisible();
  await expect(card.getByTestId("closing-condition")).not.toBeEmpty();
  await expect(card.getByTestId("evidence-sought")).not.toBeEmpty();
  // The full disposition vocabulary is in the static HTML (a <details> is no-JS usable).
  await expect(page.getByTestId("disposition").first()).toBeAttached();
});

test("the corrections log lists corrections without JS (SIG-UI-032/037)", async ({ page }) => {
  await page.goto("/corrections/");
  await expect(page.getByTestId("correction").first()).toBeVisible();
  await expect(page.getByTestId("prior-permalink").first()).toBeVisible();
  await expect(page.getByTestId("transparency-total")).toBeVisible();
});

test("the dispute path is a plain link on every page, no JS (SIG-UI-033/037)", async ({ page }) => {
  await page.goto("/dossier/oklahoma-city/");
  const link = page.getByTestId("dispute-link").first();
  await expect(link).toHaveAttribute("href", /\/dispute\//);
  await page.goto("/dispute/");
  await expect(page.getByTestId("dispute-category").first()).toBeVisible();
});

test("methodology / freshness / coverage are static and linked from the dossier (SIG-UI-034)", async ({ page }) => {
  await page.goto("/dossier/oklahoma-city/");
  await expect(page.getByTestId("methodology-link")).toHaveAttribute("href", "/methodology/");
  await page.goto("/data-freshness/");
  await expect(page.getByTestId("freshness-row").first()).toBeVisible();
  await page.goto("/coverage-metrics/");
  await expect(page.getByTestId("coverage-metric").first()).toBeVisible();
  await expect(page.getByTestId("population-note").first()).toBeVisible();
});

test("editorial standards render the three cases + hostile review without JS (SIG-UI-042/045)", async ({ page }) => {
  await page.goto("/editorial-standards/");
  await expect(page.getByTestId("editorial-case")).toHaveCount(3);
  await expect(page.getByTestId("release-status")).toHaveAttribute("data-releasable", "true");
  await page.goto("/style-guide/");
  await expect(page.getByTestId("register-rule")).toHaveCount(6);
});

test("the 'How we know this' module is in the static HTML of every page (SIG-UI-044)", async ({ page }) => {
  await page.goto("/research-queue/");
  const module = page.getByTestId("how-we-know-this");
  await expect(module).toBeVisible();
  await expect(module.locator("[data-component]")).toHaveCount(6);
});
