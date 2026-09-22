// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// The curation surface (P21.6, §34, ADR-068). Runs in the "chromium" project (JS on)
// and asserts WCAG 2.2 AA via axe on every /curate/ page, that the review queue is
// ordered by impact, that a machine suggestion is a LABELLED suggestion and is never
// pre-selected (SIG-LLM-001/002), and that a contradiction shows both claims with
// evidence + dates (§3.1). The a11y sweep in a11y.spec.ts also covers these pages.
import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { CURATE_PAGES } from "./pages";

test("every /curate/ page meets WCAG 2.2 AA (axe)", async ({ page }) => {
  for (const path of CURATE_PAGES) {
    await page.goto(path);
    const results = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"])
      .analyze();
    expect(results.violations, `axe violations on ${path}`).toEqual([]);
  }
});

test("the queue is ordered by impact and links to compare pages (RISK-P21-11)", async ({ page }) => {
  await page.goto("/curate/");
  const items = page.getByTestId("review-item");
  await expect(items.first()).toBeVisible();
  // Highest match weight (12.40) first.
  await expect(items.first()).toHaveAttribute("data-item-id", "er_match:agency:okcpd~agency:okc-pd");
  await expect(page.getByTestId("review-link").first()).toBeVisible();
});

test("a machine suggestion is labelled and not applied (SIG-LLM-001/002)", async ({ page }) => {
  await page.goto("/curate/");
  const suggestion = page.getByTestId("review-suggestion").first();
  await expect(suggestion).toBeVisible();
  await expect(suggestion).toContainText("not applied");
  await expect(page.getByTestId("suggestion-decision").first()).toHaveText("match");
});

test("the compare page shows both sides + rationale and no radio is pre-selected", async ({ page }) => {
  await page.goto("/curate/er_match%3Aagency%3Aokcpd~agency%3Aokc-pd/");
  await expect(page.getByTestId("compare-left")).toBeVisible();
  await expect(page.getByTestId("compare-right")).toBeVisible();
  await expect(page.getByTestId("confidence-factor").first()).toBeVisible();
  // No decision is pre-selected — a human must choose (SIG-LLM-002).
  const checked = await page.locator('input[name="decision"]:checked').count();
  expect(checked).toBe(0);
  // The form posts to the authenticated curation API.
  await expect(page.getByTestId("decide-form")).toHaveAttribute("method", "post");
  await expect(page.getByTestId("decide-form")).toHaveAttribute(
    "action",
    /\/v1\/curation\/review-queue\/.*\/decide$/,
  );
});

test("a contradiction is shown with both claims, evidence and dates (§3.1)", async ({ page }) => {
  await page.goto("/curate/contradictions/");
  const claims = page.getByTestId("contradiction-claim");
  await expect(claims).toHaveCount(2);
  await expect(page.getByTestId("claim-value").first()).toBeVisible();
  await expect(page.getByTestId("claim-evidence").first()).toBeVisible();
  await expect(page.getByTestId("claim-date").first()).toBeVisible();
  await expect(page.getByTestId("contradiction-reason")).toHaveAttribute("required", "");
});

test("the auth banner marks the surface non-public on every page", async ({ page }) => {
  for (const path of CURATE_PAGES) {
    await page.goto(path);
    await expect(page.getByTestId("curate-auth-banner")).toContainText("not public");
  }
});
