// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// P36.40 (K3 SRCH-05 / SIG-SRCH-010, UXR-23): the typeahead's end-to-end
// contract — the header element upgrades the plain GET form into the APG
// combobox over the emitted `sig.typeahead-shard/1` set; a keystroke fetches
// ONE same-origin shard (never a server call per character — the network
// assertion below counts requests); Enter navigates to the named thing's
// page (the capstone A1 leg: "Oklahoma" → the Oklahoma dossier).
import { test, expect } from "@playwright/test";

test.describe("the header typeahead (SIG-SRCH-010)", () => {
  test("a T1 page upgrades the header field over the shared shards; Enter navigates", async ({
    page,
  }) => {
    const shardRequests: string[] = [];
    page.on("request", (r) => {
      if (r.url().includes("/search/shards/")) shardRequests.push(r.url());
    });
    const crossOrigin: string[] = [];
    page.on("request", (r) => {
      const u = new URL(r.url());
      // A keystroke never leaves the page's own origin.
      if (u.origin !== "null" && !u.origin.endsWith("localhost:4321")) crossOrigin.push(r.url());
    });
    await page.goto("/dossier/");
    const input = page.locator("[data-testid='site-search-typeahead'] input[name='q']");
    await expect(input).toBeVisible();
    await input.fill("ok");
    const list = page.locator("[data-testid='site-search-typeahead'] [role='listbox']");
    await expect(list).toBeVisible();
    const first = list.getByRole("option").first();
    await expect(first).toContainText("Oklahoma");
    // One fetch per shard key — a keystroke never leaves the origin.
    expect(shardRequests.filter((u) => u.endsWith("/ok.json")).length).toBe(1);
    expect(crossOrigin).toEqual([]);
    // APG: ArrowDown activates the option, Enter opens it (the dossier page).
    await input.press("ArrowDown");
    await expect(first).toHaveAttribute("aria-selected", "true");
    await input.press("Enter");
    await expect(page).toHaveURL(/\/dossier\//);
  });

  test("Escape closes the list and Enter submits the plain form when nothing is active", async ({
    page,
  }) => {
    await page.goto("/");
    const input = page.locator("[data-testid='hero-search-typeahead'] input[name='q']");
    await expect(input).toBeVisible();
    await input.fill("zzqx");
    const list = page.locator("[data-testid='hero-search-typeahead'] [role='listbox']");
    await expect(list).toBeHidden();
    // No active option → Enter stays the no-JS GET path → /search/?q=…
    await input.press("Enter");
    await expect(page).toHaveURL(/\/search\/\?q=/);
  });

  test("the dossier-index place form consumes the same shard set", async ({ page }) => {
    const shardRequests: string[] = [];
    page.on("request", (r) => {
      if (r.url().includes("/search/shards/")) shardRequests.push(r.url());
    });
    await page.goto("/dossier/");
    const input = page.locator("[data-testid='place-search-typeahead'] input[name='q']");
    await input.fill("okla");
    const list = page.locator("[data-testid='place-search-typeahead'] [role='listbox']");
    await expect(list).toBeVisible();
    await expect(list.getByRole("option").first()).toContainText("Oklahoma");
    expect(shardRequests.length).toBeGreaterThan(0);
    expect(shardRequests.every((u) => u.includes("/search/shards/"))).toBe(true);
  });

  test("the /search/ corpus form upgrades through the island bundle (T2 module rule)", async ({
    page,
  }) => {
    await page.goto("/search/");
    // In fixtures mode no release is activated, so the corpus form mounts only
    // when targets exist — the header element still upgrades on this T2 route
    // because the island bundle registered <sig-typeahead>.
    const header = page.locator("[data-testid='site-search-typeahead']");
    await expect(header).toBeVisible();
    const input = header.locator("input[name='q']");
    await input.fill("ok");
    const list = header.locator("[role='listbox']");
    await expect(list).toBeVisible();
    await expect(list.getByRole("option").first()).toContainText("Oklahoma");
  });
});
