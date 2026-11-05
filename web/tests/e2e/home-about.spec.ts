// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// P36.64 (UXK14-6; SIG-UI-135…142): home + About e2e — the tagline hero with
// the H1's viewport geometry, generated example chips passing their contract,
// persona start-here paths resolving (K13 §8 A1/J1/O1), the release-bound
// capability table, the golden-place card, and /about/ as a T1 page.
import { test, expect } from "@playwright/test";

const UUID_RE = /[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/i;
const RAWKEY_RE = /(iso3166|us\.census\.geoid|agency:|jurisdiction:)/i;

test.describe("home hero (SIG-UI-135)", () => {
  test("the confirmed tagline is the H1 inside its viewport budgets", async ({ page }) => {
    for (const [w, h, maxTop] of [[1440, 900, 160], [390, 844, 120]] as const) {
      await page.setViewportSize({ width: w, height: h });
      await page.goto("/");
      const h1 = page.locator("h1").first();
      await expect(h1).toContainText("Public surveillance, traced to the documents.");
      const box = await h1.boundingBox();
      expect(box).not.toBeNull();
      expect(box!.y).toBeLessThanOrEqual(maxTop);
    }
  });

  test("the GET place search and the release stamp are above the fold", async ({ page }) => {
    await page.goto("/");
    const form = page.getByTestId("hero-search-form");
    await expect(form).toBeVisible();
    await expect(form).toHaveAttribute("method", "get");
    await expect(page.getByTestId("page-stamp")).toBeVisible();
  });

  test("the page is ≤ 5 viewport heights at 390 px (SIG-UI-136)", async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto("/");
    const scrollHeight = await page.evaluate(() => document.documentElement.scrollHeight);
    expect(scrollHeight).toBeLessThanOrEqual(5 * 844);
    // ≤ 6 headline figures.
    const figs = page.locator("[data-testid='counts-section'] .sig-stat");
    expect(await figs.count()).toBeLessThanOrEqual(6);
  });
});

test.describe("generated example questions (SIG-UI-138 / K14 §6.2)", () => {
  test("every emitted chip resolves: 200 + answer element + no UUID/raw key", async ({ page }) => {
    await page.goto("/");
    const chips = page.getByTestId("example-chips").locator("a");
    const count = await chips.count();
    expect(count).toBeGreaterThan(0);
    expect(count).toBeLessThanOrEqual(3);
    // Collect before navigating — the locator re-resolves against the
    // current page after a goto.
    const targets: { text: string; href: string }[] = [];
    for (let i = 0; i < count; i++) {
      targets.push({
        text: (await chips.nth(i).innerText()).trim(),
        href: (await chips.nth(i).getAttribute("href"))!,
      });
    }
    for (const { text, href } of targets) {
      expect(text).not.toMatch(UUID_RE);
      expect(text).not.toMatch(RAWKEY_RE);
      expect(href).toMatch(/^\//);
      const [path, frag] = href.split("#");
      const resp = await page.request.get(path);
      expect(resp.status(), `${path} must resolve`).toBe(200);
      await page.goto(path);
      if (frag) await expect(page.locator(`#${frag}`)).toBeVisible();
    }
  });
});

test.describe("persona start-here paths (SIG-UI-137 / K13 §8 O1)", () => {
  test("three persona cards, every step target resolves on the release", async ({ page }) => {
    await page.goto("/");
    for (const id of ["advocate", "journalist", "organizer"]) {
      const card = page.getByTestId(`persona-${id}`);
      await expect(card).toBeVisible();
      const steps = card.locator("ol li a");
      const n = await steps.count();
      expect(n).toBeGreaterThanOrEqual(3);
      expect(n).toBeLessThanOrEqual(4);
      for (let i = 0; i < n; i++) {
        const href = await steps.nth(i).getAttribute("href");
        const [path] = href!.split("#");
        const target = path === "/" ? "/" : path;
        const resp = await page.request.get(target);
        expect(resp.status(), `${id} step ${i} → ${target}`).toBe(200);
      }
    }
  });
});

test.describe("capability table (SIG-UI-139)", () => {
  test("every capability statement is release-bound; no metric-0 row promises", async ({ page }) => {
    await page.goto("/about/");
    const rows = page.getByTestId("capability-table").locator("[data-live]");
    expect(await rows.count()).toBe(5);
    for (let i = 0; i < 5; i++) {
      const row = rows.nth(i);
      const live = (await row.getAttribute("data-live")) === "true";
      if (live) {
        await expect(row.locator("a")).toHaveCount(1);
      } else {
        // A "being built" row names the state and carries no link.
        expect((await row.innerText()).toLowerCase()).toContain("being built");
      }
    }
  });
});

test.describe("golden-place card + trust (K14 §2.3 rows 5/7)", () => {
  test("the golden card carries joined facts, a disagreement and the decision", async ({ page }) => {
    await page.goto("/");
    const card = page.getByTestId("golden-card");
    await expect(card).toBeVisible();
    expect(await card.getByTestId("golden-facts").locator("li").count()).toBeGreaterThanOrEqual(3);
    await expect(card.getByTestId("golden-disagreement")).toBeVisible();
    await expect(card.getByTestId("golden-decision")).toBeVisible();
    const open = card.getByTestId("golden-open");
    const resp = await page.request.get((await open.getAttribute("href"))!);
    expect(resp.status()).toBe(200);
  });

  test("trust/method links resolve; the review-status disclosure is present", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByTestId("review-status")).toBeVisible();
    const links = page.getByTestId("trust").locator("ul a");
    const n = await links.count();
    expect(n).toBeGreaterThan(0);
    for (let i = 0; i < n; i++) {
      const resp = await page.request.get((await links.nth(i).getAttribute("href"))!);
      expect(resp.status()).toBe(200);
    }
    // D-K14-1/7: no held copy and no 'who runs SIG' section anywhere.
    await expect(page.locator("text=/who runs sig/i")).toHaveCount(0);
  });
});

test.describe("About & how it works (SIG-UI-140)", () => {
  test("/about/ is a T1 page stating the model, review status, is-not and cite/correct", async ({ page }) => {
    const resp = await page.goto("/about/");
    expect(resp!.status()).toBe(200);
    await expect(page.locator("h1")).toContainText(/About SIG/);
    await expect(page.getByTestId("in-brief")).toBeVisible();
    expect(await page.getByTestId("how-step").count()).toBe(5);
    await expect(page.getByTestId("is-not")).toBeVisible();
    await expect(page.getByTestId("capability-table")).toBeVisible();
    await expect(page.getByTestId("other-public-resources")).toBeVisible();
    await expect(page.getByText(/sole-maintainer/i)).toBeVisible();
    await expect(page.getByText(/not yet human-reviewed/i).first()).toBeVisible();
    // No 'who runs SIG' section or placeholder (D-K14-7).
    await expect(page.locator("text=/who runs sig/i")).toHaveCount(0);
    // The held K14 lines are absent (D-K14-1).
    await expect(page.locator("text=/scattered across thousands of agency portals/i")).toHaveCount(0);
    // Header About section + footer About link land here.
    const nav = page.locator("nav[aria-label='Primary']");
    // The About section's "About & how it works" item is registered and lands
    // here (it sits inside the section's collapsed menu — presence, not
    // visibility).
    await expect(nav.locator("a[href='/about/']").first()).toHaveCount(1);
    await expect(page.locator("footer a[href='/about/']").first()).toHaveCount(1);
  });

  test("reference pages open with an In brief of ≤ 80 words (SIG-UI-141)", async ({ page }) => {
    for (const route of ["/methodology/", "/editorial-standards/", "/coverage-metrics/", "/about/", "/glossary/"]) {
      await page.goto(route);
      const box = page.getByTestId("in-brief").first();
      await expect(box).toBeVisible();
      const words = (await box.innerText()).replace(/In brief|Read the precise version/g, "").trim().split(/\s+/).length;
      expect(words, `${route} in-brief words`).toBeLessThanOrEqual(80);
      await expect(box.locator("a")).toHaveCount(1);
    }
  });
});
