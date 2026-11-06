// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// P37.8 (R11-GOV-03; ADR-166 / A-4 = Q-E2-09 c; ADR-167; spec §44.3
// SIG-SEC-003) — /about/legal-demands/ as a T1 zero-JS page: the written
// demand-response posture renders, the counts show 0 with their as-of,
// the not-legal-advice / not-counsel-reviewed statement is present, and
// the canary is declined, never claimed. The route-level sweeps (axe,
// nojs-parity, budget, script-policy) iterate it via the discovered
// manifest.
import { test, expect } from "@playwright/test";

test.describe("the legal-demands page (P37.8)", () => {
  test("is classified T1 in the emitted page-types manifest", async ({ page }) => {
    await page.goto("/about/legal-demands/");
    const manifest = await page.evaluate(async () => {
      const res = await fetch("/page-types.json");
      return res.json();
    });
    const entry = manifest.routes?.find?.(
      (r: { path: string; type?: string }) => r.path === "/about/legal-demands/",
    );
    expect(entry).toBeTruthy();
    expect(entry.type).toBe("T1");
  });

  test("renders the written posture sections", async ({ page }) => {
    await page.goto("/about/legal-demands/");
    const main = page.locator("main");
    await expect(main).toContainText("What SIG holds");
    await expect(main).toContainText("Who receives legal process");
    await expect(main).toContainText("Preservation requests");
    await expect(main).toContainText("User notice");
    await expect(main).toContainText("interim legal home");
  });

  test("the counts show zero with their as-of date", async ({ page }) => {
    await page.goto("/about/legal-demands/");
    const counts = page.getByTestId("legal-demand-counts");
    await expect(counts.getByTestId("counts-received")).toHaveText("0");
    await expect(counts.getByTestId("counts-complied")).toHaveText("0");
    await expect(counts.getByTestId("counts-refused")).toHaveText("0");
    await expect(
      page.getByTestId("counts-as-of").locator("time"),
    ).toHaveAttribute("datetime", /\d{4}-\d{2}-\d{2}/);
  });

  test("states not legal advice and not reviewed by counsel (ADR-167)", async ({
    page,
  }) => {
    await page.goto("/about/legal-demands/");
    await expect(page.locator("main")).toContainText("not legal advice");
    await expect(page.locator("main")).toContainText("no lawyer has reviewed it");
  });

  test("declines the warrant canary — never claims one", async ({ page }) => {
    await page.goto("/about/legal-demands/");
    await expect(page.locator("main")).toContainText("does not operate a warrant canary");
    await expect(page.locator("main")).toContainText("declined");
  });

  test("the corrections log carries the same counts with the same as-of", async ({
    page,
  }) => {
    await page.goto("/corrections/");
    const counts = page.getByTestId("legal-demand-counts");
    await expect(counts).toContainText("received 0");
    await expect(counts).toContainText("complied with 0");
    await expect(counts).toContainText("refused 0");
    await expect(counts.locator("time")).toHaveAttribute(
      "datetime",
      /\d{4}-\d{2}-\d{2}/,
    );
  });

  test("emits no runtime script (T1 content)", async ({ page }) => {
    await page.goto("/about/legal-demands/");
    // T1 may carry only the allow-listed module entries — none are
    // registered yet — plus Astro's own bootstrap; no island or inline
    // behaviour is permitted on this page.
    const scripts = await page.locator("main script").count();
    expect(scripts).toBe(0);
  });
});
