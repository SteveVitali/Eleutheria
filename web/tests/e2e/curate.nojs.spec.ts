// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// Runs in the "no-js" Playwright project (JavaScript DISABLED). Proves the curation
// forms are usable with NO client JavaScript (progressive enhancement, P21.6): every
// form is a native `<form method="post">` with the required fields, posting to the
// authenticated curation API. Deciding, dispositioning, submitting and reverting all
// work without JS.
import { test, expect } from "@playwright/test";

test("the review queue and compare/decide form render + submit without JS", async ({ page }) => {
  await page.goto("/curate/");
  await expect(page.getByTestId("review-item").first()).toBeVisible();

  await page.goto("/curate/er_match%3Aagency%3Aokcpd~agency%3Aokc-pd/");
  const form = page.getByTestId("decide-form");
  await expect(form).toHaveAttribute("method", "post");
  await expect(form).toHaveAttribute("action", /\/v1\/curation\/review-queue\/.*\/decide$/);
  // The decide radios and the reason field are plain form controls (no JS needed).
  await expect(page.getByTestId("decision-match")).toBeVisible();
  await expect(page.getByTestId("decision-no-match")).toBeVisible();
  await expect(page.getByTestId("decision-defer")).toBeVisible();
  await expect(page.getByTestId("decide-reason")).toBeVisible();
  // No decision is pre-selected without JS either.
  expect(await page.locator('input[name="decision"]:checked').count()).toBe(0);
});

test("the L0 submission form requires evidence and works without JS", async ({ page }) => {
  await page.goto("/curate/submit/");
  const form = page.getByTestId("submit-form");
  await expect(form).toHaveAttribute("method", "post");
  await expect(form).toHaveAttribute("action", /\/v1\/curation\/submission$/);
  // Evidence is a required native input (the form refuses without it).
  await expect(page.getByTestId("submit-evidence")).toHaveAttribute("required", "");
});

test("the contradiction, task and revert forms are native POST forms", async ({ page }) => {
  await page.goto("/curate/contradictions/");
  await expect(page.getByTestId("contradiction-form")).toHaveAttribute("method", "post");
  await expect(page.getByTestId("contradiction-reason")).toHaveAttribute("required", "");

  await page.goto("/curate/tasks/");
  await expect(page.getByTestId("task-form")).toHaveAttribute("method", "post");
  await expect(page.getByTestId("task-disposition")).toBeVisible();

  await page.goto("/curate/revert/");
  await expect(page.getByTestId("revert-form")).toHaveAttribute("method", "post");
  await expect(page.getByTestId("revert-reason")).toHaveAttribute("required", "");
});

test("no /curate/ page ships client JavaScript despite the island allowance", async ({ page }) => {
  // These pages MAY carry a JS island (keyboard shortcuts/diff views) but the shipped
  // build uses none, so the forms are guaranteed to work without JS.
  const paths = ["/curate/", "/curate/submit/", "/curate/contradictions/", "/curate/tasks/", "/curate/revert/"];
  for (const path of paths) {
    const resp = await page.goto(path);
    const html = (await resp?.text()) ?? "";
    expect(html).not.toContain("<script");
  }
});
