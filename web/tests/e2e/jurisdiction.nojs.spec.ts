// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// Runs in the "no-js" Playwright project (JavaScript DISABLED). Jurisdiction-conditional
// publication (SIG-PUB-017) is a BUILD-TIME decision, so the withholding and the
// localisation must be present in the static HTML with no client JavaScript at all —
// the withheld name must never be shipped and re-hidden by a script. The shell ships
// zero client JS, so disabling it must change nothing.
import { test, expect } from "@playwright/test";
import type { Page } from "@playwright/test";
import t1ModuleEntries from "./t1-module-entries.json" with { type: "json" };

const T1_MODULE_ENTRIES = new Set<string>(t1ModuleEntries.entries);

// The T1 script contract (ADR-155, UXK0-4): no inline script and every
// <script> element is an allow-listed static /_kit/ module entry. These
// assertions run with JavaScript disabled, so the modules are inert — the
// server-rendered document is what the reader sees.
async function expectOnlyAllowListedKitModules(page: Page): Promise<void> {
  const scripts = await page.$$eval("script", (els) =>
    els.map((el) => ({ src: el.getAttribute("src"), type: el.getAttribute("type") })),
  );
  for (const s of scripts) {
    expect(s.type, `script ${s.src ?? "(inline)"} must be type=module`).toBe("module");
    expect(
      s.src !== null && T1_MODULE_ENTRIES.has(s.src),
      `script ${s.src ?? "(inline)"} is not an allow-listed /_kit/ entry`,
    ).toBe(true);
  }
}

const FR_PAGE = "/dossier/paris-alpr/";
const BE_PAGE = "/dossier/brussels-alpr/";
const US_PAGE = "/dossier/oklahoma-city/";

test("the US dossier withholds the name without JS while no concurrence is recorded", async ({
  page,
}) => {
  // P35.28 (SIG-PUB-007/008): the officer-naming gate is default deny — the
  // US-DEFAULT jurisdiction leg permitting is not enough; the name must never
  // ship in the HTML while no persisted two-reviewer concurrence names the row.
  await page.goto(US_PAGE);
  await expect(page.getByTestId("dossier-row-withheld").first()).toHaveText("withheld");
  await expect(page.locator("body")).not.toContainText("Chief Wade Gourley");
  await expectOnlyAllowListedKitModules(page);
});

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
  // Zero-JS contract (SIG-UI-036/037): any <script> on the page is an inert,
  // allow-listed /_kit/ module entry — nothing else executes.
  await expectOnlyAllowListedKitModules(page);
});
