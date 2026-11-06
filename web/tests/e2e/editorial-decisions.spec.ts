// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// P37.7 (R11-GOV-02; ADR-164 / WV-02; spec §46.2) — /about/editorial-decisions/
// as a T1 zero-JS log: every published decision entry cites its GATE DECISIONS
// row, the retroactive set is dated as such, and the tombstone section states
// the honest empty state. The route-level sweeps (axe, nojs-parity, budget,
// script-policy) iterate it via the discovered manifest.
import { test, expect } from "@playwright/test";

test.describe("the editorial decision log (P37.7)", () => {
  test("is classified T1 in the emitted page-types manifest", async ({ page }) => {
    await page.goto("/about/editorial-decisions/");
    const manifest = await page.evaluate(async () => {
      const res = await fetch("/page-types.json");
      return res.json();
    });
    const entry = manifest.routes?.find?.(
      (r: { path: string; type?: string }) => r.path === "/about/editorial-decisions/",
    );
    expect(entry).toBeTruthy();
    expect(entry.type).toBe("T1");
  });

  test("every decision entry cites its GATE DECISIONS row", async ({ page }) => {
    await page.goto("/about/editorial-decisions/");
    const entries = page.getByTestId("editorial-decision");
    const count = await entries.count();
    expect(count).toBeGreaterThan(0);
    for (let i = 0; i < count; i++) {
      const entry = entries.nth(i);
      await expect(entry.getByTestId("decision-text")).not.toBeEmpty();
      const cite = entry.getByTestId("decision-gate-ref");
      await expect(cite).toContainText("GATE DECISIONS");
      await expect(cite.locator("time")).toHaveCount(1);
      await expect(entry.getByTestId("decision-evidence")).not.toBeEmpty();
    }
  });

  test("the retroactive entries are dated as such", async ({ page }) => {
    await page.goto("/about/editorial-decisions/");
    const retro = page.locator(
      "[data-testid='editorial-decision'][data-retroactive]",
    );
    expect(await retro.count()).toBeGreaterThanOrEqual(1);
    await expect(page.getByTestId("log-start")).toContainText("This log begins");
    await expect(page.getByTestId("log-start").locator("time")).toHaveAttribute(
      "datetime",
      /\d{4}-\d{2}-\d{2}/,
    );
  });

  test("states the interim single-maintainer authority, never a board", async ({ page }) => {
    await page.goto("/about/editorial-decisions/");
    await expect(page.locator("main")).toContainText("no independent review board");
    await expect(page.locator("main")).toContainText("single-maintainer");
    // naming stays off — the disclosed posture
    await expect(page.locator("main")).toContainText("naming");
  });

  test("the tombstone section is honest about deletions and purges", async ({ page }) => {
    await page.goto("/about/editorial-decisions/");
    const empty = page.getByTestId("tombstone-empty");
    const count = page.getByTestId("tombstone-count");
    expect((await empty.count()) + (await count.count())).toBe(1);
    if (await empty.count()) {
      await expect(empty).toContainText("No deletions or purges are recorded");
    }
  });

  test("emits no runtime script (T1 content)", async ({ page }) => {
    await page.goto("/about/editorial-decisions/");
    // T1 may carry only the allow-listed module entries — none are
    // registered yet — plus Astro's own bootstrap; no island or inline
    // behaviour is permitted on this page.
    const scripts = await page.locator("main script").count();
    expect(scripts).toBe(0);
  });
});
