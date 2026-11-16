// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { DISCOVERED_ROUTES, gotoSettled } from "./pages";
import {
  VISUAL_TEMPLATE_GROUPS,
  selectRepresentative,
} from "../visual/templates";

// P37.60 (UXK14-10; DR-K14-13 / SIG-UI-147; K14 §4.10): the `dark` Playwright
// project (`colorScheme: "dark"`). Every template MUST render in a dark theme
// under `prefers-color-scheme: dark`, declare `color-scheme`, force light for
// print, and pass axe colour-contrast in dark. The sweep iterates the
// visual-regression template representatives — the same derived set the grid
// shoots — so a new template joins this leg automatically (K0 NEW-4). The
// full every-route dark axe pass is the announce-readiness check (UXK14-12);
// this leg's bound is every TEMPLATE.
//
// Print check: `@media print` forces the light token set regardless of the OS
// scheme — asserted here on every representative because a dark-printed page
// is exactly the class of bug a dark project exists to catch.

const WCAG_TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"];

function luminance(rgb: string): number {
  const m = rgb.match(/rgba?\(([\d.]+)[ ,]+([\d.]+)[ ,]+([\d.]+)/);
  if (!m) return 1;
  const channel = (v: number) => {
    const c = v / 255;
    return c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);
  };
  return (
    0.2126 * channel(Number(m[1])) +
    0.7152 * channel(Number(m[2])) +
    0.0722 * channel(Number(m[3]))
  );
}

const PICKS: { group: (typeof VISUAL_TEMPLATE_GROUPS)[number]; path: string }[] =
  VISUAL_TEMPLATE_GROUPS.map((g) => ({
    group: g,
    path: selectRepresentative(g, DISCOVERED_ROUTES).path,
  })).filter((p): p is { group: (typeof VISUAL_TEMPLATE_GROUPS)[number]; path: string } => p.path !== null);

test("the dark project asserts every resolved template emits a route", () => {
  const missing = VISUAL_TEMPLATE_GROUPS.filter(
    (g) => g.optional !== true && selectRepresentative(g, DISCOVERED_ROUTES).path === null,
  ).map((g) => g.id);
  expect(missing, "template group with no emitted route on this build").toEqual([]);
});

for (const { group, path } of PICKS) {
  test(`dark theme: ${group.id} — ${path}`, async ({ page }) => {
    await gotoSettled(page, path);

    // Declared color-scheme (SIG-UI-147) — meta or the :root property.
    const declared = await page.evaluate(() => {
      const meta = document.querySelector('meta[name="color-scheme"]')?.getAttribute("content") ?? "";
      const prop = getComputedStyle(document.documentElement).colorScheme;
      return `${meta} ${prop}`;
    });
    expect(declared).toContain("dark");

    // The page background is actually dark (luminance below mid-grey) — not a
    // light page wearing a dark-scheme label.
    const bg = await page.evaluate(
      () => getComputedStyle(document.body).backgroundColor,
    );
    expect(
      luminance(bg),
      `${path}: body background ${bg} is not dark under prefers-color-scheme: dark`,
    ).toBeLessThan(0.25);

    // axe WCAG 2.2 AA in dark — colour-contrast violations fail the build.
    const results = await new AxeBuilder({ page }).withTags(WCAG_TAGS).analyze();
    expect(results.violations, JSON.stringify(results.violations, null, 2)).toEqual([]);

    // Print forces light (K14 §4.10) even while the OS scheme is dark.
    await page.emulateMedia({ media: "print" });
    const printBg = await page.evaluate(
      () => getComputedStyle(document.body).backgroundColor,
    );
    expect(
      luminance(printBg),
      `${path}: print did not force the light token set (${printBg})`,
    ).toBeGreaterThan(0.6);
  });
}
