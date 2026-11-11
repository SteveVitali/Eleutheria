// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// P37.29 (K6 VIZ-04, SIG-UI-127): the in-place map activation on dossiers.
// The `<sig-activate>` element upgrades the dossier's plain /map/ link into
// the embedded K1 map app ONLY on an explicit click and ONLY where the
// desktop pointer+width media query matches — never a T2 preload, never a
// touch/mobile activation. Both states, the failure leg, the no-URL-writes
// invariant, the close/focus return, the axe sweep on the activated state,
// and the print-keeps-the-SVG leg are covered here.
import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { gotoSettled } from "./pages";

const DOSSIER = "/dossier/usa/ok/";
const DOSSIER_PRINT = "/dossier/usa/ok/print/";

test.describe("in-place map activation on dossiers (VIZ-04)", () => {
  test("before activation the figure is static and the affordance is a link", async ({
    page,
  }) => {
    // A narrow viewport fails the (min-width: 64rem) media query — the
    // element must NOT upgrade: the anchor stays a plain navigation link.
    await page.setViewportSize({ width: 800, height: 900 });
    await gotoSettled(page, DOSSIER);
    await expect(page.getByTestId("fig1-static")).toBeVisible();
    await expect(page.getByTestId("fig-map-embed")).toBeHidden();
    const link = page.locator("a.sig-activate");
    await expect(link).toBeVisible();
    await expect(link).toHaveAttribute("href", /\/map\/\?.*jurisdiction=/);
    await expect(page.locator(".sig-activate__button")).toHaveCount(0);
    // No deferred map code fetched before an explicit action (SIG-UI-127).
    await expect(page.getByTestId("map-island")).toHaveCount(0);
  });

  test("click activates the K1 app in the same box — no URL writes — close restores the figure", async ({
    page,
  }) => {
    await page.setViewportSize({ width: 1280, height: 900 });
    await gotoSettled(page, DOSSIER);
    const button = page.locator(".sig-activate__button");
    await expect(button).toBeVisible();
    await expect(button).toHaveAttribute("aria-expanded", "false");
    const urlBefore = page.url();
    const historyBefore = await page.evaluate(() => history.length);

    await button.click();
    const embed = page.getByTestId("fig-map-embed");
    await expect(embed).toBeVisible();
    // The K1 app mounts — the canvas reports ready then drawn (the same
    // latches /map/'s own sweeps wait on; hardened against the async load).
    const canvas = embed.getByTestId("map-island");
    await expect(canvas).toHaveAttribute("data-ready", "true", { timeout: 30_000 });
    await expect(canvas).toHaveAttribute("data-drawn", "true", { timeout: 90_000 });
    // K6 §5.4: the static SVG stays in the DOM (print) but is aria-hidden
    // once the first drawn render lands.
    await expect(page.getByTestId("fig1-static")).toHaveAttribute("aria-hidden", "true");
    await expect(button).toHaveAttribute("aria-expanded", "true");
    // The chrome subset: embed heading + hand-offs + close; the In-view
    // list below the canvas (the default tab), and K6 §5.4's filters row
    // (technology · status · source — nothing else) behind its tab.
    await expect(page.getByTestId("map-embed-heading")).toBeFocused();
    await expect(page.getByTestId("inview-list")).toBeVisible();
    await page.getByTestId("map-tab-filters").click();
    await expect(page.getByTestId("map-filters")).toBeVisible();
    await expect(
      page.getByTestId("map-filters").locator("fieldset[data-testid='filter-technology']"),
    ).toBeVisible();
    await expect(
      page.getByTestId("map-filters").locator("fieldset[data-testid='filter-status']"),
    ).toBeVisible();
    await expect(
      page.getByTestId("map-filters").locator("fieldset[data-testid='filter-source']"),
    ).toBeVisible();
    // The subset's exclusions inside the filters row too: no compartments,
    // no seen, no vendor/operator fieldsets on the dossier.
    await expect(page.getByTestId("map-compartments")).toHaveCount(0);
    await expect(page.getByTestId("filter-seen-fieldset")).toHaveCount(0);
    await expect(page.getByTestId("filter-vendor")).toHaveCount(0);
    await expect(page.getByTestId("filter-operator")).toHaveCount(0);
    // The subset's named exclusions: no view-nav, no place search, no "My location".
    await expect(page.getByTestId("island-view-links")).toHaveCount(0);
    await expect(page.getByTestId("map-place-search")).toHaveCount(0);
    await expect(page.getByTestId("my-location")).toHaveCount(0);
    // V-10 / SIG-UI-127: no workspace URL writes — the dossier's address bar
    // and history are untouched through activation and a selection.
    expect(page.url()).toBe(urlBefore);
    expect(await page.evaluate(() => history.length)).toBe(historyBefore);
    // The hand-offs: "Open full map" carries the dossier's jurisdiction to
    // /map/?v=2…; "Cite this view" mints the pinned snapshot form.
    const openFull = page.getByTestId("embed-open-full");
    await expect(openFull).toHaveAttribute("href", /\/map\/\?v=2/);
    await expect(openFull).toHaveAttribute("href", /jurisdiction=/);
    await expect(page.getByTestId("embed-cite")).toBeVisible();
    // Close restores the static figure and returns focus to the button.
    await page.getByTestId("embed-close").click();
    await expect(embed).toBeHidden();
    await expect(page.getByTestId("fig1-static")).not.toHaveAttribute("aria-hidden", "true");
    await expect(button).toBeFocused();
    await expect(button).toHaveAttribute("aria-expanded", "false");
    expect(page.url()).toBe(urlBefore);
  });

  test("a failed load keeps the static figure and shows the notice", async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 900 });
    await page.route("**/_kit/sig-map-embed.js", (route) => route.abort());
    await gotoSettled(page, DOSSIER);
    const button = page.locator(".sig-activate__button");
    await expect(button).toBeVisible();
    await button.click();
    const notice = page.locator(".sig-activate__note");
    await expect(notice).toBeVisible();
    await expect(notice).toContainText("could not load");
    await expect(notice).toContainText("the figure and the places table");
    await expect(page.getByTestId("fig1-static")).toBeVisible();
    await expect(page.getByTestId("fig1-static")).not.toHaveAttribute("aria-hidden", "true");
    await expect(page.getByTestId("fig-map-embed")).toBeHidden();
  });

  test("print keeps the static SVG — no element, no script", async ({ page, request }) => {
    // The print route is T0: no <script> of any kind, and the activation
    // affordance never renders there — the static figure is the rendition.
    const html = await (await request.get(DOSSIER_PRINT)).text();
    expect(html).not.toContain("<script");
    expect(html).not.toContain("sig-activate");
    await gotoSettled(page, DOSSIER_PRINT);
    await expect(page.locator("sig-activate")).toHaveCount(0);
    await expect(page.getByTestId("map-island")).toHaveCount(0);
  });

  test("the activated state is axe-clean (WCAG 2.2 AA)", async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 900 });
    await gotoSettled(page, DOSSIER);
    await page.locator(".sig-activate__button").click();
    const canvas = page.getByTestId("fig-map-embed").getByTestId("map-island");
    await expect(canvas).toHaveAttribute("data-ready", "true", { timeout: 30_000 });
    await expect(canvas).toHaveAttribute("data-drawn", "true", { timeout: 90_000 });
    const results = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag22aa"]).analyze();
    expect(results.violations).toEqual([]);
  });
});
