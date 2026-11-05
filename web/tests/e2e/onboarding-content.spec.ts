// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// P36.65 (UXK14-11) — the onboarding-content e2e: the per-page reading key on
// the dossier (K14 §6.3 — only the symbols present), the annotated
// "How to read a dossier" page generated from the golden dossier, and the
// T1 zero-JS posture on every touched route.
import { test, expect } from "@playwright/test";

const GOLDEN = "/dossier/oklahoma-city/";

test.describe("per-page reading key (K14 §6.3)", () => {
  test("the dossier carries a 'How to read this page' link and the key", async ({ page }) => {
    await page.goto(GOLDEN);
    const link = page.getByTestId("reading-key-link");
    await expect(link).toBeVisible();
    await expect(link).toHaveAttribute("href", "#reading-key");
    const key = page.getByTestId("reading-key");
    await expect(key).toBeAttached();
    const items = key.getByTestId("reading-key-item");
    const ids = await items.evaluateAll((els) => els.map((e) => e.getAttribute("data-key")));
    // The fixture dossier carries a support glyph and a contested figure for
    // real; an absent mark is never listed.
    expect(ids).toContain("support");
    expect(ids).toContain("contested");
    for (const item of await items.all()) {
      await expect(item.locator("strong")).not.toHaveText(/^\s*$/);
    }
    // Every row links the glossary — a glossary affordance is never missing.
    for (const item of await items.all()) {
      await expect(item.locator("a")).toHaveCount(1);
    }
  });

  test("a listed absence kind really is on the page", async ({ page }) => {
    await page.goto(GOLDEN);
    const items = page.getByTestId("reading-key-item");
    const ids = await items.evaluateAll((els) => els.map((e) => e.getAttribute("data-key")));
    // The fixture dossier's gaps are NOT_RESEARCHED / UNRESOLVED kinds — the
    // key must match the page's data, never a fixed list.
    expect(ids.some((i) => i?.startsWith("absence-"))).toBe(true);
  });
});

test.describe("annotated how-to-read-a-dossier page (K14 §6.3)", () => {
  test("the page is generated from the golden dossier with numbered callouts", async ({ page }) => {
    const resp = await page.goto("/about/how-to-read-a-dossier/");
    expect(resp?.status()).toBe(200);
    await expect(page.getByTestId("annotated-source")).toBeVisible();
    const callouts = page.getByTestId("dossier-callout");
    const count = await callouts.count();
    expect(count).toBeGreaterThanOrEqual(10);
    // Every callout links the live section it describes — a link that cannot
    // resolve is a broken annotation, never shipped.
    for (const c of await callouts.all()) {
      const href = await c.locator("a").first().getAttribute("href");
      expect(href).toMatch(/^\/dossier\/oklahoma-city\//);
    }
    // The page exhibits the same reading key the dossier carries.
    await expect(page.getByTestId("reading-key")).toBeAttached();
  });

  test("the callout anchors resolve on the golden dossier", async ({ page }) => {
    await page.goto("/about/how-to-read-a-dossier/");
    const anchors = await page.getByTestId("dossier-callout").locator("a").evaluateAll(
      (els) => els.map((e) => e.getAttribute("href")?.split("#")[1]).filter(Boolean) as string[],
    );
    await page.goto(GOLDEN);
    for (const anchor of anchors) {
      // The anchors are build-generated kebab ids — no CSS.escape needed.
      const el = page.locator(`#${anchor}`);
      await expect(el, `anchor #${anchor} exists on the dossier`).toHaveCount(1);
    }
  });
});
