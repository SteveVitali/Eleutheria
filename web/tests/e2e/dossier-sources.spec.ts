// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// P36.52 (DSRC-02): the sources explorer + "Where this comes from" —
// fixture-verified over the committed corpus (usa = 27 sources → sort
// routes; usa/ok = run_level_only + parity row; SIG-DSRC-001…006/008/009).

import { expect, test } from "@playwright/test";

test.describe("Where this comes from (dossier block)", () => {
  test("every dossier renders the block with totals + top sources + explorer link", async ({ page }) => {
    await page.goto("/dossier/usa/ok/");
    const block = page.getByTestId("dsrc-block");
    await expect(block).toBeVisible();
    await expect(block.getByRole("heading", { name: "Where this comes from" })).toBeVisible();
    await expect(page.getByTestId("dsrc-headline")).toContainText("records");
    await expect(page.getByTestId("dsrc-top-sources")).toBeVisible();
    const link = page.getByTestId("dsrc-explorer-link").getByRole("link", { name: /Explore all/ });
    await expect(link).toHaveAttribute("href", "/dossier/usa/ok/sources/");
    // SIG-DSRC-002: named sources, no bare ids as the link text
    await expect(block.getByRole("link", { name: "OKC camera registry" })).toBeVisible();
    // SIG-DSRC-004: dossier-scope HWKT resolves inside the artifact, never /surfaces/site
    await expect(page.locator('[data-pointer^="/surfaces/site"]')).toHaveCount(0);
  });
});

test.describe("the sources explorer", () => {
  test("usa renders the contribution table, sort nav, details, chart + twin, disagreements", async ({ page }) => {
    await page.goto("/dossier/usa/sources/");
    await expect(page.getByTestId("dsrc-totals")).toBeVisible();
    await expect(page.getByTestId("dsrc-sort-nav")).toContainText("first-seen");
    const table = page.getByTestId("dsrc-table");
    await expect(table).toBeVisible();
    expect(await table.locator("tbody tr").count()).toBeGreaterThan(20);
    // <details> per source + the over-time chart with its table twin (SIG-DSRC-006)
    expect(await page.getByTestId("dsrc-source-detail").count()).toBeGreaterThan(20);
    await expect(page.locator("svg.sig-dsrc-chart")).toBeVisible();
    await expect(page.getByTestId("dsrc-time-table")).toBeVisible();
    await expect(page.getByTestId("dsrc-disagreements")).toContainText("not_evaluable");
    // previously contributed (D-K5-3): withdrawn + disappeared named below
    await expect(page.getByTestId("dsrc-previous")).toContainText("withdrawn");
    await expect(page.getByTestId("dsrc-downloads")).toContainText("not yet available");
    // zero <script> inside the explorer article (T1, SIG-DSRC-006)
    expect(await page.locator("article.sig-dsrc script").count()).toBe(0);
  });

  test("a sort route renders a differently-ordered table", async ({ page }) => {
    await page.goto("/dossier/usa/sources/sort/name/");
    const first = page.getByTestId("dsrc-table").locator("tbody tr").first();
    await expect(first).toContainText("Demo state registry 01");
  });

  test("run_level_only renders instead of a last-seen date (K5 §3.3)", async ({ page }) => {
    await page.goto("/dossier/usa/ok/sources/");
    const row = page.locator('tr[data-source-id="demo_seed_load"]');
    await expect(row).toContainText("run_level_only");
  });

  test("the JSON twin carries the same data (SIG-DSRC-009)", async ({ page }) => {
    const res = await page.request.get("/dossier/usa/ok/sources/index.json");
    expect(res.ok()).toBe(true);
    const doc = await res.json();
    expect(doc.schema).toBe("sig.dossier-sources/1");
    expect(doc.totals.sources).toBe(4);
    const names = doc.sources.map((s: { name: string }) => s.name);
    await page.goto("/dossier/usa/ok/sources/");
    for (const n of names) await expect(page.getByTestId("dsrc-table")).toContainText(n);
  });

  test("SIG-DSRC-008 parity: 38 records for okc_camera_registry on the OKC dossier", async ({ page }) => {
    await page.goto("/dossier/usa/ok/oklahoma-city-4064000/sources/");
    const row = page.locator('tr[data-source-id="okc_camera_registry"]');
    await expect(row).toContainText("38");
  });
});
