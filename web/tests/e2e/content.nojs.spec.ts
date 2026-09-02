// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// Runs in the "no-js" Playwright project (JavaScript DISABLED). It proves core
// content is usable without JavaScript (SIG-UI-037, AC1): the reference map has a
// populated tabular equivalent, the reference graph has a populated list
// equivalent, the epistemic fields render, the citation permalink is present, and
// the absence hatch is a real link. Since the shell ships zero client JS, disabling
// it must change nothing — this test is what guarantees that stays true.
import { test, expect } from "@playwright/test";

test("reference map has a populated tabular equivalent without JS (SIG-UI-037)", async ({
  page,
}) => {
  await page.goto("/reference-map/");
  const rows = page.getByTestId("map-row");
  await expect(rows).toHaveCount(3);
  // The table carries the coordinate/precision detail, not just the map image.
  await expect(page.locator("table.sig-table")).toContainText("Published precision");
});

test("reference graph has a populated list equivalent without JS (SIG-UI-037)", async ({
  page,
}) => {
  await page.goto("/reference-graph/");
  const edges = page.getByTestId("graph-edge");
  await expect(edges).toHaveCount(2);
  await expect(edges.first()).toContainText("operates devices from");
});

test("epistemic fields and support glyph render without JS (SIG-UI-004)", async ({ page }) => {
  await page.goto("/visual-language/");
  await expect(page.getByTestId("epistemic-fields").first().locator(".sig-field")).toHaveCount(4);
  await expect(page.getByTestId("support-glyph").first()).toContainText("Support:");
});

test("citation permalink is present without JS (SIG-UI-035)", async ({ page }) => {
  await page.goto("/");
  const href = await page.getByTestId("permalink").getAttribute("href");
  expect(href).toContain("as_of_belief=");
  expect(href).toContain("ruleset=");
});

test("absence hatch is a real GET link that resolves without JS (SIG-UI-007)", async ({ page }) => {
  await page.goto("/visual-language/");
  const hatch = page.getByTestId("absence-hatch").first();
  const href = await hatch.getAttribute("href");
  expect(href).toMatch(/^\/task\/new\//);
  // Follow it as a plain navigation (no click handler / JS): the task is generated.
  await page.goto(href!);
  await expect(page.getByTestId("generated-task")).toBeVisible();
  await expect(page.getByTestId("task-field-status")).toHaveText("generated");
});
