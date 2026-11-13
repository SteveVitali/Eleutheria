// SPDX-License-Identifier: Apache-2.0
// P37.45 (CONF-12, SIG-CONF-011 + SIG-CONF-001/010): the public /quality/
// page — every registered check appears with its state (failing and
// ratchet shown), the verbatim "no human check performed" statement, the
// who-checked-what basis table, and the per-record basis anchor.
import { test, expect } from "@playwright/test";

test.describe("/quality/", () => {
  test("renders every registered check with its state", async ({ page }) => {
    await page.goto("/quality/");
    const rows = page.locator('[data-testid^="quality-check-GQ-"]');
    await expect(rows).toHaveCount(27);
    // Failing and ratchet checks are shown, never hidden (Q-L3-5).
    await expect(page.locator('[data-check-mode="ratchet"]')).not.toHaveCount(0);
    await expect(page.locator('[data-check-state="fail"]')).not.toHaveCount(0);
    // Each row renders its state cell.
    const states = page.locator('[data-testid="quality-check-state"]');
    await expect(states).toHaveCount(27);
    for (let i = 0; i < 27; i++) {
      await expect(states.nth(i)).not.toBeEmpty();
    }
  });

  test("states 'no human check performed' verbatim (Q-L3-3 = c)", async ({ page }) => {
    await page.goto("/quality/");
    await expect(page.locator('[data-testid="quality-no-human-check"]')).toContainText(
      "no human check performed",
    );
  });

  test("who checked what: the independent-review row reads none", async ({ page }) => {
    await page.goto("/quality/");
    const b5 = page.locator('[data-testid="basis-B5"]');
    await expect(b5).toContainText("none");
    // 0 'verified' strings without a marker (the acceptance shape).
    await expect(page.locator("main")).not.toContainText("human-verified");
    await expect(page.locator("main")).not.toContainText("independently reviewed — done");
  });

  test("the duplicates anchor and probe-lane panel render", async ({ page }) => {
    await page.goto("/quality/");
    await expect(page.locator("#duplicates")).toBeVisible();
    const lane = page.locator('[data-testid="quality-lane"], [data-testid="quality-lane-absent"]');
    await expect(lane).toHaveCount(1);
  });
});
