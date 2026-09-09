// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// Runs in the "no-js" Playwright project (JavaScript DISABLED). Jurisdiction-conditional
// publication (SIG-PUB-017) is a BUILD-TIME decision, so the withholding and the
// localisation must be present in the static HTML with no client JavaScript at all —
// the withheld name must never be shipped and re-hidden by a script. The shell ships
// zero client JS, so disabling it must change nothing.
import { test, expect } from "@playwright/test";

const FR_PAGE = "/dossier/paris-alpr/";
const BE_PAGE = "/dossier/brussels-alpr/";

test("the France dossier is localised and withholds the name without JS (SIG-PUB-017)", async ({
  page,
}) => {
  await page.goto(FR_PAGE);
  await expect(page.locator("html")).toHaveAttribute("lang", "fr");
  await expect(page.locator("#sec-at_a_glance")).toHaveText("En bref");
  await expect(page.getByTestId("dossier-row-withheld").first()).toHaveText("withheld");
  await expect(page.locator("body")).not.toContainText("Jean Dupont");
});

test("the Belgium dossier withholds the name and ships no <script> without JS", async ({
  page,
}) => {
  await page.goto(BE_PAGE);
  await expect(page.locator("html")).toHaveAttribute("lang", "nl-BE");
  await expect(page.getByTestId("dossier-row-withheld").first()).toHaveText("withheld");
  // Zero-JS contract: no <script> tags on the page (SIG-UI-036/037).
  await expect(page.locator("script")).toHaveCount(0);
});
