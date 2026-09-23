// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// Runs in the "no-js" Playwright project (JavaScript DISABLED). Epistemic legibility
// at scale (§39.1, §3.1, SIG-UI-003/008): on real data surfaces the support glyph
// carries its text equivalent + machine-readable evidence count + downgrade reason,
// the contested marker persists at every appearance, and contradictions stay visible —
// all server-rendered, so a reader without JavaScript loses none of it.
import { test, expect } from "@playwright/test";

test("support glyphs on the network surface carry a consistent downgrade-reason channel", async ({
  page,
}) => {
  await page.goto("/network/");
  const glyphs = page.getByTestId("support-glyph");
  const n = await glyphs.count();
  expect(n).toBeGreaterThan(0);
  for (let i = 0; i < n; i++) {
    const g = glyphs.nth(i);
    // The glyph is decoration on its own — the text equivalent must carry the meaning.
    await expect(g).toContainText("Support:");
    const support = await g.getAttribute("data-support");
    const reason = (await g.getAttribute("data-downgrade-reason")) ?? "";
    const evidence = await g.getAttribute("data-evidence-count");
    expect(Number(evidence), "evidence count is machine-readable").not.toBeNaN();
    // Consistency: CONFIRMED carries no downgrade reason; anything below carries one.
    if (support === "CONFIRMED") {
      expect(reason).toBe("");
    } else {
      expect(reason.length, `${support} must state a downgrade reason`).toBeGreaterThan(0);
    }
  }
});

test("contested values carry the persistent marker on live surfaces (no JS)", async ({ page }) => {
  await page.goto("/watch/");
  // The watch renders contested contracts; the marker appears with an accessible label.
  const markers = page.getByTestId("contested-marker");
  expect(await markers.count()).toBeGreaterThan(0);

  // The evidence index marks contested claims too — consistent vocabulary everywhere.
  await page.goto("/evidence/");
  expect(await page.getByTestId("contested-marker").count()).toBeGreaterThan(0);
});

test("contradictions stay visible as a range on the reference surface (§29.1)", async ({ page }) => {
  await page.goto("/visual-language/");
  // The contradiction range plots the competing claims rather than hiding the conflict.
  const claims = page.locator(".sig-range__claims li");
  expect(await claims.count()).toBeGreaterThan(1);
});
