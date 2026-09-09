// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// Jurisdiction-conditional publication + localisation, JavaScript ENABLED (§43.8,
// §44; SIG-PUB-017). The France (FR-GDPR) and Belgium (BE-GDPR) dossiers render in
// their own BCP-47 language with localised section titles, and the public-employee
// name is WITHHELD by the build-time publication gate — whereas the US OKC dossier
// publishes the equivalent name. Because the gate runs at build time, the difference
// is baked into the static HTML.
import { test, expect } from "@playwright/test";

const FR_PAGE = "/dossier/paris-alpr/";
const BE_PAGE = "/dossier/brussels-alpr/";
const US_PAGE = "/dossier/oklahoma-city/";

test("the France dossier declares lang=fr and localises a section title (SIG-UI/§43)", async ({
  page,
}) => {
  await page.goto(FR_PAGE);
  await expect(page.locator("html")).toHaveAttribute("lang", "fr");
  // A localised section title (fr): "En bref" for at_a_glance.
  await expect(page.locator("#sec-at_a_glance")).toHaveText("En bref");
});

test("the Belgium dossier declares a BCP-47 lang with a region subtag (nl-BE)", async ({
  page,
}) => {
  await page.goto(BE_PAGE);
  await expect(page.locator("html")).toHaveAttribute("lang", "nl-BE");
  await expect(page.locator("#sec-at_a_glance")).toHaveText("In het kort");
});

test("the France dossier withholds the public-employee name under FR-GDPR (SIG-PUB-017)", async ({
  page,
}) => {
  await page.goto(FR_PAGE);
  const withheld = page.getByTestId("dossier-row-withheld").first();
  await expect(withheld).toBeVisible();
  await expect(withheld).toHaveText("withheld");
  // The withheld officer name never appears anywhere in the built HTML.
  await expect(page.locator("body")).not.toContainText("Jean Dupont");
});

test("the Belgium dossier withholds the public-employee name under BE-GDPR", async ({ page }) => {
  await page.goto(BE_PAGE);
  await expect(page.getByTestId("dossier-row-withheld").first()).toHaveText("withheld");
  await expect(page.locator("body")).not.toContainText("Jean Dupont");
});

test("the US dossier publishes the equivalent public-employee name (US-DEFAULT)", async ({
  page,
}) => {
  await page.goto(US_PAGE);
  await expect(page.locator("html")).toHaveAttribute("lang", "en");
  // Permitted under US-DEFAULT — shown, not withheld (existing behaviour unchanged).
  await expect(page.locator("body")).toContainText("Chief Wade Gourley");
  await expect(page.getByTestId("dossier-row-withheld")).toHaveCount(0);
});
