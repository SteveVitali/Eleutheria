// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// P36.53 (DSRC-03, SIG-DSRC-007): the per-dossier downloads page —
// materialised per-compartment slices at country/admin-1 (D-K5-1), the
// DuckDB/API recipe block at county/place, ATTRIBUTION/LICENCE + sha256 +
// R2 links per bundle; the dossier + explorer links resolve. T1 zero-JS.

import { expect, test } from "@playwright/test";

test.describe("per-dossier downloads", () => {
  test("a materialised dossier lists compartment slices with licence + sha256 + links", async ({ page }) => {
    await page.goto("/dossier/usa/ok/downloads/");
    await expect(page.getByTestId("dld-page")).toBeVisible();
    const group = page.getByTestId("dld-group").first();
    await expect(group).toContainText("compartment");
    const table = group.getByTestId("dld-table");
    await expect(table).toContainText("statements.jsonl.gz");
    await expect(table).toContainText("ATTRIBUTION.txt");
    await expect(table).toContainText("LICENCE.txt");
    // the usa dossier carries two compartments
    expect(await page.getByTestId("dld-group").count()).toBeGreaterThanOrEqual(1);
    // R2 content-hash links
    await expect(page.getByRole("link", { name: "statements.jsonl.gz" }).first()).toHaveAttribute(
      "href",
      /files\.surveillancegraph\.org/,
    );
    // T1: zero scripts inside the article
    expect(await page.locator("article.sig-dld script").count()).toBe(0);
  });

  test("a county dossier shows the recipe block instead of materialised slices", async ({ page }) => {
    await page.goto("/dossier/usa/tx/harris-county-48201/downloads/");
    await expect(page.getByTestId("dld-none")).toContainText("No materialised slices");
    const recipes = page.getByTestId("dld-recipes");
    await expect(recipes).toContainText("jurisdiction_chain");
    await expect(recipes).toContainText("us.census.geoid.county:48201");
    await expect(recipes).toContainText("/v1/releases/");
    expect(await page.getByTestId("dld-group").count()).toBe(0);
  });

  test("the dossier page + explorer link the downloads page", async ({ page }) => {
    await page.goto("/dossier/usa/ok/");
    await expect(page.getByTestId("downloads-link")).toHaveAttribute("href", "/dossier/usa/ok/downloads/");
    await page.goto("/dossier/usa/ok/sources/");
    await expect(page.getByTestId("dsrc-downloads")).toBeVisible();
    await expect(
      page.getByRole("link", { name: "All downloads for this dossier" }),
    ).toHaveAttribute("href", "/dossier/usa/ok/downloads/");
  });
});
