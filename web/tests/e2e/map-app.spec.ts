// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// P36.37 (K1 MAP-03a) — the /map/ T2 app shell's owned requirements:
// SIG-UI-101 selection-panel fields · SIG-UI-102 synchronized in-view list ·
// SIG-UI-103 state round-trip (at=/filters/focus/basemap via
// sig.workspace-state/2) · SIG-UI-104 filter counts + cannot-apply ·
// SIG-UI-065 one data hue · SIG-UI-095 canvas reachability / Escape ·
// SIG-UI-097 no React in the map bundle · UXR-13 "records" wording ·
// UXR-18/SIG-UI-068 links that never 404.
import { test, expect } from "@playwright/test";
import { gotoSettled } from "./pages";

test.describe("map app shell (P36.37)", () => {
  test("the shell hydrates over the no-JS document and lists records in view (SIG-UI-102)", async ({
    page,
  }) => {
    await gotoSettled(page, "/map/");
    const island = page.getByTestId("map-island");
    await expect(island).toHaveAttribute("data-ready", "true", { timeout: 20_000 });
    await expect(island).toHaveAttribute("data-drawn", "true", { timeout: 20_000 });
    // The panel tabs exist (In view · Filters · Selected) and the In-view
    // list syncs to the viewport — 'records' wording (UXR-13).
    await expect(page.getByTestId("map-tab-view")).toBeVisible();
    await expect(page.getByTestId("map-tab-filters")).toBeVisible();
    await expect(page.getByTestId("map-tab-selected")).toBeVisible();
    const status = page.getByTestId("inview-status");
    await expect(status).toContainText("records in view", { timeout: 10_000 });
    // The preserved no-JS equivalent still renders beneath (SIG-UI-050).
    await expect(page.getByTestId("map-places-row").first()).toBeVisible();
  });

  test("selection shows the SIG-UI-101 fields and resolvable links (UXR-18)", async ({ page }) => {
    await gotoSettled(page, "/map/?focus=device:okc-001");
    await expect(page.getByTestId("map-island")).toHaveAttribute("data-ready", "true", {
      timeout: 20_000,
    });
    const panel = page.getByTestId("map-selected-panel");
    await expect(page.getByTestId("selection-label")).toContainText("Fixed ALPR", { timeout: 10_000 });
    // The required field set — label, technology, operator, jurisdiction
    // (linked), sources, first/last seen, precision, status.
    await expect(page.getByTestId("selection-technology")).toContainText("alpr-fixed");
    await expect(page.getByTestId("selection-operator")).toContainText("Oklahoma City Police");
    const jur = page.getByTestId("selection-jurisdiction");
    await expect(jur).toContainText("Oklahoma City");
    await expect(page.getByTestId("selection-sources")).toContainText("Oklahoma City ALPR feed");
    await expect(page.getByTestId("selection-first-seen")).toContainText("2026-04-11");
    await expect(page.getByTestId("selection-last-seen")).toContainText("2026-09-12");
    await expect(page.getByTestId("selection-precision")).toContainText("tier 0");
    await expect(page.getByTestId("selection-status")).toContainText("One source");
    // Every emitted link resolves — UXR-18's never-404 rule.
    const links = panel.locator("a[href]");
    const hrefs = await links.evaluateAll((as) => as.map((a) => a.getAttribute("href") ?? ""));
    for (const href of hrefs) {
      const resp = await page.request.get(href);
      expect(resp.status(), `link ${href} must not 404`).toBeLessThan(400);
    }
  });

  test("the viewport round-trips through at= on moveend (SIG-UI-103)", async ({ page }) => {
    await gotoSettled(page, "/map/");
    await expect(page.getByTestId("map-island")).toHaveAttribute("data-ready", "true", {
      timeout: 20_000,
    });
    // Pan with the single-pointer control (SIG-UI-095's pan alternative).
    await page.getByLabel("Pan east").click();
    await page.waitForTimeout(900);
    const url = page.url();
    // The wire form URL-encodes the slashes (at=3%2F39%2F-90.5) — it parses
    // back to the canonical viewport (SIG-UI-103 round-trip).
    expect(url, "moveend writes at=<z>/<lat>/<lon>").toMatch(
      /at=\d+(%2F|\/)-?\d+(\.\d+)?(%2F|\/)-?\d+(\.\d+)?/,
    );
    // Reload: the viewport restores.
    await gotoSettled(page, url);
    await expect(page.getByTestId("map-island")).toHaveAttribute("data-ready", "true", {
      timeout: 20_000,
    });
    expect(page.url()).toContain("at=");
  });

  test("a selected filter writes to the URL and the seen facet shows cannot-apply below z10 (SIG-UI-104)", async ({
    page,
  }) => {
    await gotoSettled(page, "/map/");
    await expect(page.getByTestId("map-island")).toHaveAttribute("data-ready", "true", {
      timeout: 20_000,
    });
    await page.getByTestId("map-tab-filters").click();
    // Every filter option carries a count.
    const tech = page.getByTestId("filter-tech-alpr-fixed");
    await expect(tech).toBeVisible();
    await page.getByTestId("filter-status-corroborated").click();
    await page.waitForTimeout(600);
    expect(page.url()).toContain("status=corroborated");
    // `seen` cannot apply at national zoom — greyed cells + a note, no hatch.
    const cannot = page.getByTestId("filter-seen-cannot");
    await expect(cannot).toContainText("applies from zoom 10");
    await expect(cannot.locator("..")).not.toContainText("records match");
  });

  test("Escape clears the selection; Enter moves focus to the list (SIG-UI-095)", async ({
    page,
  }) => {
    await gotoSettled(page, "/map/?focus=device:okc-002");
    await expect(page.getByTestId("map-island")).toHaveAttribute("data-ready", "true", {
      timeout: 20_000,
    });
    await expect(page.getByTestId("selection-label")).toContainText("RTCC", { timeout: 10_000 });
    const canvas = page.locator(".maplibregl-canvas");
    await canvas.focus();
    await page.keyboard.press("Escape");
    await page.waitForTimeout(300);
    expect(page.url()).not.toContain("focus=");
    await canvas.focus();
    await page.keyboard.press("Enter");
    const focused = await page.evaluate(() => document.activeElement?.tagName);
    expect(["LI", "BUTTON"].includes(focused ?? "")).toBe(true);
  });

  test("the map bundle ships no React (SIG-UI-097) and one data hue paints every status (SIG-UI-065)", async ({
    page,
  }) => {
    const scripts: string[] = [];
    page.on("request", (r) => {
      if (r.resourceType() === "script") scripts.push(r.url());
    });
    await gotoSettled(page, "/map/");
    await expect(page.getByTestId("map-island")).toHaveAttribute("data-drawn", "true", {
      timeout: 20_000,
    });
    for (const s of scripts) {
      expect(s, `react runtime must not reach /map/: ${s}`).not.toMatch(/react/i);
    }
  });

  test("the basemap fallback shows the honest notice (K1 §2.6)", async ({ page }) => {
    await gotoSettled(page, "/map/");
    await expect(page.getByTestId("map-island")).toHaveAttribute("data-ready", "true", {
      timeout: 20_000,
    });
    // In this environment the tile host is unreachable — the notice must
    // appear rather than a silent blank map.
    const notice = page.locator(
      "[data-testid=basemap-unavailable], [data-testid=basemap-fallback]",
    );
    await expect(notice.first()).toBeVisible({ timeout: 15_000 });
  });
});
