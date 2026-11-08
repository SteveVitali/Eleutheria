// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// P37.19 (K1 MAP-04, OD-09 [B-23] = a Natural Earth) — the place search:
// shared <sig-typeahead> shards scoped to kind=place (registry + the NE
// populated-places layer), the local coordinates parser, the `jurisdiction=`
// filter-vs-`frame=`/at= distinction (C-11), and the no-JS GET form staying
// complete (no /map/place/ route — C-24).
import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { gotoSettled } from "./pages";

const WCAG_TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"];

async function ready(page: import("@playwright/test").Page, url = "/map/") {
  await gotoSettled(page, url);
  await expect(page.getByTestId("map-island")).toHaveAttribute("data-ready", "true", {
    timeout: 20_000,
  });
  await expect(page.getByTestId("map-island")).toHaveAttribute("data-drawn", "true", {
    timeout: 20_000,
  });
}

test.describe("map place search (P37.19)", () => {
  test("a registry place suggestion lands jurisdiction= filter + frame (C-11)", async ({
    page,
  }) => {
    await ready(page);
    const input = page.getByTestId("map-place-input");
    await input.click();
    await input.fill("Oklahoma");
    const option = page.locator(".sig-typeahead-option", { hasText: "Oklahoma City" }).first();
    await expect(option).toBeVisible({ timeout: 10_000 });
    await option.click();
    await page.waitForTimeout(900);
    expect(page.url(), "choosing a place writes jurisdiction=<jkey>").toContain(
      "jurisdiction=us.census.geoid.place%3A",
    );
    // The two states are distinct and both offered (K1 §4.2/§4.8).
    const chip = page.getByTestId("place-filter");
    await expect(chip).toContainText("Filtering to Oklahoma City");
    await page.getByTestId("place-show-area").click();
    await page.waitForTimeout(400);
    expect(page.url()).not.toContain("jurisdiction=");
    await expect(page.getByTestId("place-frame")).toContainText("not filtering");
    // ...and framing converts back to the facet, linkably.
    await page.getByTestId("place-apply-filter").click();
    await page.waitForTimeout(400);
    expect(page.url()).toContain("jurisdiction=us.census.geoid.place%3A");
    const results = await new AxeBuilder({ page }).withTags(WCAG_TAGS).analyze();
    expect(results.violations, JSON.stringify(results.violations)).toEqual([]);
  });

  test("a populated place (Natural Earth) frames without a filter — never a hosted geocoder", async ({
    page,
  }) => {
    const requests: string[] = [];
    page.on("request", (r) => requests.push(r.url()));
    await ready(page);
    const input = page.getByTestId("map-place-input");
    await input.click();
    await input.fill("Canberra");
    const option = page.locator(".sig-typeahead-option", { hasText: "Canberra" }).first();
    await expect(option).toBeVisible({ timeout: 10_000 });
    await option.click();
    await page.waitForTimeout(900);
    expect(page.url(), "a city frames via at= — no jurisdiction filter exists for it").toMatch(
      /at=\d+(%2F|\/)-?35/,
    );
    expect(page.url()).not.toContain("jurisdiction=");
    // No keystroke or lookup ever left the origin — shards are same-origin
    // JSON under search/shards/ only.
    for (const u of requests.filter((u) => u.includes("search/shards/") === false)) {
      expect(u).not.toMatch(/geocod|nominatim|photon|pelias/i);
    }
  });

  test("typed coordinates jump locally — parsed in the browser, no request", async ({
    page,
  }) => {
    await ready(page);
    const input = page.getByTestId("map-place-input");
    await input.click();
    await input.fill("35.4676, -97.5164");
    await page.getByTestId("map-place-go").click();
    await page.waitForTimeout(900);
    expect(page.url(), "the coordinate pair writes the at= viewport").toMatch(
      /at=\d+(%2F|\/)35\.4\d*(%2F|\/)-97\.5\d*/,
    );
    // An unparseable phrase is an honest note, never a guess.
    await input.fill("not a place at all");
    await page.getByTestId("map-place-go").click();
    await expect(page.getByTestId("map-place-note")).toContainText(
      "No place suggestion or coordinates matched",
    );
  });

  test("?jurisdiction= on arrival filters and frames when no at= is given (C-11)", async ({
    page,
  }) => {
    await ready(page, "/map/?jurisdiction=iso3166-2%3AUS-OK");
    await expect(page.getByTestId("place-filter")).toContainText("Filtering to Oklahoma", {
      timeout: 10_000,
    });
    await expect(page).toHaveURL(/at=\d+(%2F|\/)/, { timeout: 15_000 });
    // The framed viewport wrote at= (the canonicalised form) — the link
    // round-trips jurisdiction + the resolved view.
    expect(page.url()).toContain("jurisdiction=iso3166-2%3AUS-OK");
  });

  test("the no-JS place form keeps its GET contract (no /map/place/ route — C-24)", async ({
    page,
  }) => {
    await gotoSettled(page, "/map/");
    const form = page.getByTestId("place-search-form");
    await expect(form).toHaveAttribute("method", "get");
    await expect(form).toHaveAttribute("action", /search\/$/);
    await expect(form.locator('input[name="type"]')).toHaveAttribute("value", "place");
    // The shared typeahead wraps the same field — the mount names the ONE root.
    const ta = page.getByTestId("map-place-typeahead");
    await expect(ta).toBeAttached();
    await expect(ta).toHaveAttribute("shard-root", /search\/shards\/$/);
    await expect(ta).toHaveAttribute("scope", "kind:place");
  });
});
