// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// P27.6 (SIG-UI-048/049 / ADR-093): the national IA — grouped navigation, the real
// national landing page (named denominators, no total), the per-jurisdiction dossier
// index, and the canonical origin. Runs in the JS-enabled chromium project; the
// zero-JS + a11y guarantees are enforced by the no-js project + the axe sweep.
import { test, expect } from "@playwright/test";

test.describe("grouped, uncluttered navigation (SIG-UI-049 / ADR-093)", () => {
  test("the primary nav is grouped and points Dossiers at the index, not a hardcoded jurisdiction", async ({
    page,
  }) => {
    await page.goto("/");
    const nav = page.locator("nav[aria-label='Primary']");
    await expect(nav).toBeVisible();
    // Grouped: at least three labelled groups (product · about · reference).
    const groups = nav.locator("[role='group']");
    const groupCount = await groups.count();
    expect(groupCount).toBeGreaterThanOrEqual(3);
    // Each group is labelled (keyboard/AT users can tell the groups apart).
    for (let i = 0; i < groupCount; i++) {
      await expect(groups.nth(i)).toHaveAttribute("aria-label", /.+/);
    }
    // Dossiers points at the index; the flat nav's hardcoded OKC link is gone.
    await expect(nav.locator("a[href='/dossier/']")).toHaveCount(1);
    await expect(nav.locator("a[href='/dossier/oklahoma-city/']")).toHaveCount(0);
  });

  test("every nav link is a real keyboard-focusable anchor with an href", async ({ page }) => {
    await page.goto("/");
    const links = page.locator("nav[aria-label='Primary'] a");
    const count = await links.count();
    expect(count).toBeGreaterThan(0);
    for (let i = 0; i < count; i++) {
      await expect(links.nth(i)).toHaveAttribute("href", /^\/.+/);
    }
  });
});

test.describe("national landing page (SIG-UI-049 / ADR-093)", () => {
  test("headline counts carry NAMED denominators and never a population total (§32)", async ({
    page,
  }) => {
    await page.goto("/");
    // Every named-denominator element is populated.
    const denominators = page.getByTestId("named-denominator");
    expect(await denominators.count()).toBeGreaterThan(0);
    for (let i = 0; i < (await denominators.count()); i++) {
      await expect(denominators.nth(i)).not.toBeEmpty();
    }
    // The explicit "SIG never publishes a total" framing is present.
    await expect(page.locator("#counts-heading")).toBeVisible();
    await expect(page.getByText(/never publishes a total/i)).toBeVisible();
    // No stat is labelled as a bare "total of ..." — a total is forbidden (SIG-METRIC-010).
    const labels = await page.getByTestId("coverage-stat").allInnerTexts();
    for (const l of labels) expect(l.toLowerCase()).not.toContain("total number of");
  });

  test("the landing shows jurisdiction reach and product entry points", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByTestId("reach-stat")).toBeVisible();
    expect(await page.getByTestId("entry-point").count()).toBeGreaterThanOrEqual(3);
    // Absence framing is on the landing (SIG-UI-011/007).
    await expect(page.getByText(/absence of a row is not evidence of absence/i)).toBeVisible();
  });
});

test.describe("per-jurisdiction dossier index (SIG-UI-048 / ADR-090+093)", () => {
  test("lists every publishable jurisdiction, each linking to its dossier", async ({ page }) => {
    await page.goto("/dossier/");
    const items = page.getByTestId("dossier-index-item");
    const count = await items.count();
    expect(count).toBeGreaterThan(0);
    // Every item links to a real /dossier/<slug>/ page.
    for (let i = 0; i < count; i++) {
      const href = await items.nth(i).locator("a.sig-dossier-index__link").getAttribute("href");
      expect(href).toMatch(/^\/dossier\/.+\/$/);
    }
    // The worked OKC dossier is discoverable through the index.
    await expect(page.locator("a[href='/dossier/oklahoma-city/']").first()).toBeVisible();
  });
});

test.describe("canonical origin + belief-pinned permalink (SIG-UI-035 / ADR-093 §5)", () => {
  for (const path of ["/", "/dossier/", "/map/"]) {
    test(`the permalink on ${path} resolves to surveillancegraph.org, never sig.example`, async ({
      page,
    }) => {
      await page.goto(path);
      const href = await page.getByTestId("permalink").getAttribute("href");
      expect(href).toContain("https://surveillancegraph.org");
      expect(href).not.toContain("sig.example");
      // The canonical link element also uses the real origin.
      const canonical = await page.locator("link[rel='canonical']").getAttribute("href");
      expect(canonical).toContain("https://surveillancegraph.org");
    });
  }
});
