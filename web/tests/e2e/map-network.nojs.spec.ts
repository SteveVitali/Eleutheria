// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// Runs in the "no-js" Playwright project (JavaScript DISABLED). Proves the map has a
// usable TABULAR equivalent and the network a usable LIST equivalent without any
// client JavaScript (SIG-UI-037, AC5), and that the honest-rendering signals the
// deterministic ACs turn on are present in the static HTML.
import { test, expect } from "@playwright/test";

test("map has a populated tabular equivalent without JS (SIG-UI-037)", async ({ page }) => {
  await page.goto("/map/");
  // The located-records table and the coverage-bins table both carry rows.
  await expect(page.getByTestId("map-asset-row").first()).toBeVisible();
  await expect(page.getByTestId("coverage-bin").first()).toBeVisible();
  // The jurisdiction indicators for point-less records are present (SIG-UI-020).
  await expect(page.getByTestId("jurisdiction-indicator").first()).toBeVisible();
  // OSM attribution is in the static HTML (every context, incl. no-JS/print).
  await expect(page.getByTestId("map-attribution")).toContainText("OpenStreetMap");
});

test("map counts records, drops empty legend entries, prints no suppressed count (P34.15, QW-12)", async ({
  page,
}) => {
  await page.goto("/map/");
  // The record vocabulary is in the static HTML — never "devices"/"assets" totals.
  await expect(page.getByRole("heading", { name: "Located records (tabular equivalent)" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Records without a published point" })).toBeVisible();
  // Only data-bearing layer controls are listed — the coverage-bound point
  // control is the only one this build carries.
  await expect(page.getByTestId("layer-control")).toHaveCount(1);
  await expect(page.getByTestId("layers-not-listed")).toBeVisible();
  // A value-suppressed bin prints the word, never a figure.
  const suppressed = page.locator(
    "[data-testid='coverage-bin'] >> text=suppressed",
  );
  await expect(suppressed.first()).toBeVisible();
});

test("contested locations roll up to a count that leads to the dossier (P34.15, K12b NEW-7)", async ({
  page,
}) => {
  await page.goto("/map/");
  const contested = page.getByTestId("jurisdiction-contested");
  await expect(contested).toHaveCount(1); // Oklahoma City: one UNRESOLVED-location record
  const link = contested.getByTestId("contested-dossier-link");
  await expect(link).toHaveAttribute("href", "/dossier/oklahoma-city/");
  const res = await link.click().then(() => page.url());
  expect(res).toContain("/dossier/oklahoma-city/");
});

test("low-coverage ≠ low-density is encoded in the static HTML (SIG-UI-018)", async ({ page }) => {
  await page.goto("/map/");
  const low = page.locator("[data-testid='coverage-bin'][data-coverage='low']").first();
  await expect(low).toHaveAttribute("data-reads-as-density", "false");
  const high = page.locator("[data-testid='coverage-bin'][data-coverage='high']").first();
  await expect(high).toHaveAttribute("data-reads-as-density", "true");
});

test("network has a populated list equivalent without JS (SIG-UI-037)", async ({ page }) => {
  await page.goto("/network/");
  // The three access-edge groups and their edges are plain lists.
  await expect(page.getByTestId("access-edge-group")).toHaveCount(3);
  await expect(page.getByTestId("access-edge").first()).toBeVisible();
  // The access-path hops with per-hop evidence are a plain ordered list.
  await expect(page.getByTestId("path-hop").first()).toBeVisible();
  await expect(page.getByTestId("hop-evidence").first()).toContainText("evidence:");
});

test("no centrality statistic or 'exact' identity claim renders (P34.15, K2 NEW-6, SIG-IDENT-030)", async ({
  page,
}) => {
  await page.goto("/network/");
  // The ranking is withdrawn — an abstention note, never a zero measurement
  // and never the retired "deterministic identity resolution … exact" claim.
  await expect(page.getByTestId("centrality-stat")).toHaveCount(0);
  await expect(page.getByTestId("er-disclosure")).toHaveCount(0);
  await expect(page.getByTestId("centrality-withdrawn")).toBeVisible();
  await expect(page.getByTestId("centrality-withdrawn")).toContainText(
    /not merged organisations/i,
  );
  await expect(page.locator("body")).not.toContainText(
    /deterministic identity resolution|never an estimate/i,
  );
});
