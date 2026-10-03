// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// P32.15 (SIG-FIND-004/005, ADR-134), no-JS half: the equivalent static routes —
// the versioned view-switch links, the complete browse/search paths, the bounded
// indicator lists, and the per-edge supporting claims — are all present and
// navigable with JavaScript disabled. The islands add convenience, never the
// only path (SIG-UI-037/050).
import { test, expect } from "@playwright/test";

test("the static view switch links carry the versioned release state on all three views", async ({
  page,
}) => {
  for (const [path, current] of [
    ["/search/", "view-switch-list"],
    ["/map/", "view-switch-map"],
    ["/network/", "view-switch-network"],
  ] as const) {
    await page.goto(path);
    const nav = page.getByTestId("view-switch");
    await expect(nav).toBeVisible();
    // The current view is marked; the other two are real links carrying v=1,
    // the target view and the pinned release.
    await expect(nav.getByTestId(current)).toHaveAttribute("aria-current", "page");
    const links = nav.locator("a");
    expect(await links.count()).toBe(2);
    for (let i = 0; i < 2; i += 1) {
      const href = await links.nth(i).getAttribute("href");
      expect(href).toContain("v=1");
      expect(href).toContain("view=");
      expect(href).toContain("release=p-");
    }
  }
});

test("map: unlocated records remain navigable as bounded indicators without JS", async ({
  page,
}) => {
  await page.goto("/map/");
  const indicators = page.getByTestId("jurisdiction-indicator");
  expect(await indicators.count()).toBeGreaterThan(0);
  // Honest counts are shown (never dropped); the enumeration stays bounded and
  // links into the released compartment browse when a release is activated.
  const first = indicators.first();
  await expect(first).toContainText("with no published point");
  // In fixtures mode the demo release is activated → its compartment browse is linked.
  await expect(page.getByTestId("view-switch-release")).toBeVisible();
});

test("network: edge supporting claims are visible without JS", async ({ page }) => {
  await page.goto("/network/");
  // The static edge lists name their backing claims in a <details> — an edge is
  // never just a count (§3.1), and the three access types stay separate lists.
  const evidence = page.getByTestId("access-edge-evidence");
  expect(await evidence.count()).toBeGreaterThan(0);
  await expect(evidence.first()).toContainText("supporting claim");
  const groups = page.getByTestId("access-edge-group");
  expect(await groups.count()).toBe(3);
});
