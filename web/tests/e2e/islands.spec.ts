// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// Runs in the "chromium" project (JavaScript ENABLED). Proves the three OPT-IN
// public interactive islands (P27.9, ADR-097) hydrate and are interactive over the
// real data — and, crucially, that hydration is CONFINED: only the three island
// pages ship a `<script>`; every other public page still ships zero client JS
// (SIG-UI-036/037, AC2). ODbL attribution is shown on the map (§42.3).
import { test, expect } from "@playwright/test";
import { ISLAND_PAGES, ZERO_JS_PUBLIC_PAGES } from "./pages";

test.describe("hydration is confined to the three islands (AC2)", () => {
  for (const path of ZERO_JS_PUBLIC_PAGES) {
    test(`no <script> on non-island public page ${path}`, async ({ page }) => {
      const resp = await page.goto(path);
      const html = (await resp?.text()) ?? "";
      expect(html).not.toContain("<script");
    });
  }

  for (const path of ISLAND_PAGES) {
    test(`island page ${path} ships a hydration <script>`, async ({ page }) => {
      const resp = await page.goto(path);
      const html = (await resp?.text()) ?? "";
      expect(html).toContain("<script");
    });
  }
});

test.describe("interactive map island (AC1, AC3)", () => {
  test("hydrates over the real assets, renders MapLibre + ODbL attribution", async ({ page }) => {
    await page.goto("/map/");
    // The island hydrates (client:only React → MapLibre GL initialised).
    const island = page.getByTestId("map-island");
    await expect(island).toBeVisible();
    await expect(island).toHaveAttribute("data-ready", "true", { timeout: 20_000 });
    // A real MapLibre canvas is present (the interactive renderer, not the static SVG).
    await expect(page.locator(".maplibregl-canvas")).toBeVisible();
    // Pan/zoom controls are operable.
    await expect(page.locator(".maplibregl-ctrl-zoom-in")).toBeVisible();
    // ODbL / OSM attribution is shown on the map (a licence obligation, §42.3).
    await expect(page.locator(".maplibregl-ctrl-attrib")).toContainText("OpenStreetMap");
    // The tabular equivalent is NOT removed — progressive enhancement (SIG-UI-050).
    await expect(page.getByTestId("map-asset-row").first()).toBeVisible();
  });
});

test.describe("interactive network island (AC1)", () => {
  test("hydrates and re-focuses the ego network on node selection", async ({ page }) => {
    await page.goto("/network/");
    const island = page.getByTestId("network-island");
    await expect(island).toBeVisible();
    // The centrality detail carries the inline ER-quality disclosure (SIG-UI-023).
    await expect(page.getByTestId("graph-island-er-disclosure").first()).toContainText(
      /entity resolution/i,
    );
    // Selecting a different node re-focuses (aria-pressed moves to it).
    const nodes = page.getByTestId("graph-island-node");
    const count = await nodes.count();
    expect(count).toBeGreaterThan(1);
    // Find a node that is not currently focused and click it.
    let clicked = false;
    for (let i = 0; i < count; i += 1) {
      const pressed = await nodes.nth(i).getAttribute("aria-pressed");
      if (pressed === "false") {
        await nodes.nth(i).click();
        await expect(nodes.nth(i)).toHaveAttribute("aria-pressed", "true");
        clicked = true;
        break;
      }
    }
    expect(clicked).toBe(true);
    // The lists below the island (the no-JS equivalent) remain present.
    await expect(page.getByTestId("access-edge").first()).toBeVisible();
  });
});

test.describe("interactive search island (AC1)", () => {
  test("filters the published index as you type", async ({ page }) => {
    await page.goto("/search/");
    const input = page.getByTestId("search-input");
    await expect(input).toBeVisible();
    const status = page.getByTestId("search-status");
    const before = await status.textContent();
    // A nonsense query yields the empty state (nothing found ≠ evidence of absence).
    await input.fill("zzzzzznowaymatchqx");
    await expect(page.getByTestId("search-empty")).toBeVisible();
    // Clearing restores results.
    await input.fill("");
    await expect(status).not.toHaveText(""); // status is live
    // The browse fallback links remain present regardless.
    await expect(page.getByTestId("search-browse")).toBeVisible();
    expect(before).not.toBeNull();
  });
});
