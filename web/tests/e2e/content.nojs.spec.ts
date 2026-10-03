// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// Runs in the "no-js" Playwright project (JavaScript DISABLED). It proves core
// content is usable without JavaScript (SIG-UI-037, AC1): the reference map has a
// populated tabular equivalent, the reference graph has a populated list
// equivalent, the epistemic fields render, the citation permalink is present, and
// the absence hatch is a real link. Since the shell ships zero client JS, disabling
// it must change nothing — this test is what guarantees that stays true. The
// absence hatch is a named absence (P34.12 retired the fixture /task/new/
// pages it used to link to — SIG-UI-007's task affordance lands for real with
// RQ-03's /task/<handle>/ pages).
import { test, expect } from "@playwright/test";

test("reference map has a populated tabular equivalent without JS (SIG-UI-037)", async ({
  page,
}) => {
  // P27.6: folded into /visual-language/ (map↔reference-map duplication resolved).
  await page.goto("/visual-language/");
  const rows = page.getByTestId("map-row");
  await expect(rows).toHaveCount(3);
  // The reference-map's tabular equivalent carries the coordinate/precision detail.
  await expect(page.locator("table[aria-labelledby='refmap-table-heading']")).toContainText(
    "Published precision",
  );
});

test("reference graph has a populated list equivalent without JS (SIG-UI-037)", async ({
  page,
}) => {
  // P27.6: folded into /visual-language/ (network↔reference-graph duplication resolved).
  await page.goto("/visual-language/");
  const edges = page.getByTestId("graph-edge");
  await expect(edges).toHaveCount(2);
  await expect(edges.first()).toContainText("operates devices from");
});

test("epistemic fields and support glyph render without JS (SIG-UI-004)", async ({ page }) => {
  await page.goto("/visual-language/");
  await expect(page.getByTestId("epistemic-fields").first().locator(".sig-field")).toHaveCount(4);
  await expect(page.getByTestId("support-glyph").first()).toContainText("Support:");
});

test("national landing renders its counts and dossier index without JS (SIG-UI-049)", async ({
  page,
}) => {
  await page.goto("/");
  // Named-denominator stats render server-side (no client JS).
  expect(await page.getByTestId("named-denominator").count()).toBeGreaterThan(0);
  // The per-jurisdiction dossier index is a real, populated list without JS.
  await page.goto("/dossier/");
  expect(await page.getByTestId("dossier-index-item").count()).toBeGreaterThan(0);
});

test("citation permalink is present without JS (SIG-UI-035)", async ({ page }) => {
  await page.goto("/");
  const href = await page.getByTestId("permalink").getAttribute("href");
  expect(href).toContain("as_of_belief=");
  expect(href).toContain("ruleset=");
});

test("absence hatch is a named absence without JS — never a link to a mock task (P34.12)", async ({
  page,
}) => {
  await page.goto("/visual-language/");
  const hatch = page.getByTestId("absence-hatch").first();
  await expect(hatch).toBeVisible();
  await expect(hatch).not.toHaveAttribute("href", /.*/);
  await expect(hatch).toHaveAttribute("data-absence-kind", /.+/);
  // The retired intake route does not exist: the build emits no /task/new/ page.
  const res = await page.goto("/task/new/anything/");
  expect(res?.status()).toBe(404);
});
