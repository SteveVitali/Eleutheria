// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

import { test, expect } from "@playwright/test";
import { DISCOVERED_ROUTES, T2_PAGES, gotoSettled } from "./pages";
import {
  VISUAL_TEMPLATE_GROUPS,
  selectRepresentative,
} from "../visual/templates";

// P37.60 (UXK14-10; DR-K14-15 / SIG-UI-149; K14 §4.9 + NEW-10): the
// `reduced-motion` Playwright project (`reducedMotion: "reduce"`). Under
// reduce there MUST be no animated transitions, map easing or animated
// layouts:
//
//   * the computed-style sweep — every element on every template
//     representative must report zero-duration transitions and animations
//     (the `--sig-motion-*` tokens zero under the media query; a hardcoded
//     duration that bypasses them fails here);
//   * the live-animation sweep — after load and after a scripted interaction
//     on each T2 surface, `document.getAnimations()` is empty;
//   * the call-site ban — tests/unit/motion-guard.test.ts, which fails on any
//     `.easeTo(`/`.flyTo(`/`.fitBounds(` outside src/lib/motion.ts.

const PICKS: { group: (typeof VISUAL_TEMPLATE_GROUPS)[number]; path: string }[] =
  VISUAL_TEMPLATE_GROUPS.map((g) => ({
    group: g,
    path: selectRepresentative(g, DISCOVERED_ROUTES).path,
  })).filter((p): p is { group: (typeof VISUAL_TEMPLATE_GROUPS)[number]; path: string } => p.path !== null);

for (const { group, path } of PICKS) {
  test(`reduced motion: ${group.id} — ${path}`, async ({ page }) => {
    await gotoSettled(page, path);

    // Every element's transition/animation durations are zero under reduce.
    // One evaluate returns the offenders (tag + computed value) so the
    // failure names the exact rule that slipped past the tokens.
    const offenders = await page.evaluate(() => {
      const out: string[] = [];
      for (const el of Array.from(document.querySelectorAll("*")).slice(0, 4000)) {
        const cs = getComputedStyle(el);
        const bad: string[] = [];
        for (const d of cs.transitionDuration.split(",")) {
          if (d.trim() !== "0s") bad.push(`transition-duration ${d.trim()}`);
        }
        for (const d of cs.animationDuration.split(",")) {
          if (d.trim() !== "0s") bad.push(`animation-duration ${d.trim()}`);
        }
        for (const n of cs.animationName.split(",")) {
          if (n.trim() !== "none") bad.push(`animation-name ${n.trim()}`);
        }
        if (bad.length > 0 && out.length < 10) {
          out.push(`<${el.tagName.toLowerCase()}${el.id ? `#${el.id}` : ""}> ${bad.join("; ")}`);
        }
      }
      return out;
    });
    expect(
      offenders,
      `${path}: non-zero transition/animation under prefers-reduced-motion — route through the --sig-motion-* tokens`,
    ).toEqual([]);

    // And nothing is mid-flight after the page settles.
    const inFlight = await page.evaluate(() => document.getAnimations().length);
    expect(inFlight, `${path}: ${inFlight} live animation(s) under reduce`).toBe(0);
  });
}

// The T2 surfaces get one scripted interaction each — the class of motion
// DR-K14-15 names (map easing, animated layouts) only fires on interaction.
for (const path of T2_PAGES) {
  test(`reduced motion, post-interaction: ${path}`, async ({ page }) => {
    await gotoSettled(page, path);
    // Interact with the first interactive affordance — a details toggle or a
    // button — then prove nothing animated.
    const control = page.locator("main details summary, main button").first();
    if ((await control.count()) > 0) {
      await control.click().catch(() => undefined);
    }
    await page.waitForLoadState("networkidle").catch(() => undefined);
    const inFlight = await page.evaluate(() => document.getAnimations().length);
    expect(
      inFlight,
      `${path}: ${inFlight} live animation(s) after interaction under reduce`,
    ).toBe(0);
    // Smooth scrolling must never engage under reduce.
    const scrollBehaviour = await page.evaluate(
      () => getComputedStyle(document.documentElement).scrollBehavior,
    );
    expect(scrollBehaviour).not.toBe("smooth");
  });
}
