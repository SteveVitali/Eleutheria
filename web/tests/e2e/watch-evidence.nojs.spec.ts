// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// Runs in the "no-js" Playwright project (JavaScript DISABLED). Proves the renewal
// watch, the recommender, and the evidence viewer are usable without any client
// JavaScript (SIG-UI-037), and that the honest-rendering signals the ACs turn on are
// present in the static HTML.
import { test, expect } from "@playwright/test";

test("the watch + recommender + citation list render without JS (SIG-UI-037)", async ({ page }) => {
  await page.goto("/watch/");
  await expect(page.getByTestId("watch-item").first()).toBeVisible();
  // Subscription links are plain anchors (a no-JS user can still subscribe).
  await expect(page.getByTestId("ical-link").first()).toBeVisible();
  await expect(page.getByTestId("rss-link").first()).toBeVisible();
  // The recommendation and citation lists are plain lists.
  await expect(page.getByTestId("recommended-artifact").first()).toBeVisible();
  await expect(page.getByTestId("citation-entry").first()).toBeVisible();
  await expect(page.getByTestId("neutrality-note")).toBeVisible();
});

test("the decision date, not the expiry, is in the static HTML (SIG-UI-014b)", async ({ page }) => {
  await page.goto("/watch/");
  const auto = page.locator("[data-testid='watch-item'][data-contract-id='contract:okcpd-alpr']");
  await expect(auto).toHaveAttribute("data-decision-date", "2027-01-02");
});

test("the evidence viewer highlights the span + diffs captures without JS (SIG-UI-028/029)", async ({
  page,
}) => {
  await page.goto("/evidence/active-device-count/");
  await expect(page.getByTestId("highlighted-span")).toHaveText("forty-two (42)");
  await expect(page.getByTestId("conflicting-claim").first()).toBeVisible();
  await expect(page.getByTestId("history-event").first()).toBeVisible();
  await expect(
    page.locator("[data-testid='diff-field'][data-field='active_device_count'][data-changed='true']"),
  ).toBeVisible();
});

test("a sealed capture is metadata-only without JS (SIG-UI-030)", async ({ page }) => {
  await page.goto("/evidence/operator-roster-size/");
  await expect(page.getByTestId("sealed-notice")).toBeVisible();
  await expect(page.getByTestId("document-text")).toHaveCount(0);
  await expect(page.getByTestId("capture-digest")).toContainText("sha256:");
});
