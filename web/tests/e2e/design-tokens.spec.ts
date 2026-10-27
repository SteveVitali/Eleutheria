// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// P36.16 (R11-K13-UXK14-1, SIG-UI-146/147/156): the rendered-side proof that the
// shared tokens drive the surface — the dark scheme applies the CHOSEN dark set
// (never an inversion), reduced motion zeroes every token-driven transition,
// the incompleteness banner stays neutral (K14 NEW-2), and the type scale +
// self-hosted font reach the wire.

import { test, expect } from "@playwright/test";
import { DOSSIER_PAGE } from "./pages";

async function computed(page: import("@playwright/test").Page, selector: string, prop: string) {
  return page.locator(selector).first().evaluate(
    (el, p) => getComputedStyle(el).getPropertyValue(p),
    prop,
  );
}

async function tokenValue(page: import("@playwright/test").Page, name: string, prop = "color") {
  return page.evaluate(
    ([n, p]) => {
      const probe = document.createElement("span");
      probe.style.setProperty(p!, `var(${n})`);
      document.body.appendChild(probe);
      const v = getComputedStyle(probe).getPropertyValue(p!);
      probe.remove();
      return v;
    },
    [name, prop] as const,
  );
}

test.describe("design tokens render the page (SIG-UI-146)", () => {
  test("color-scheme is declared and the page exposes both schemes", async ({ page }) => {
    await page.goto("/visual-language/");
    await expect(page.locator('meta[name="color-scheme"]')).toHaveAttribute(
      "content",
      "light dark",
    );
    expect(await computed(page, "html", "color-scheme")).toBe("light dark");
  });

  test("the body rides Public Sans at the 16 px step-0", async ({ page }) => {
    await page.goto("/visual-language/");
    expect(await computed(page, "body", "font-family")).toContain("Public Sans");
    expect(await computed(page, "body", "font-size")).toBe("16px");
    // The 8-step scale reaches the wire: an h1 renders at the step-4 band floor.
    const h1 = await computed(page, "main h1", "font-size");
    expect(Number.parseFloat(h1)).toBeGreaterThanOrEqual(32);
  });

  test("the incompleteness banner is neutral — never the disagreement hue (K14 NEW-2)", async ({
    page,
  }) => {
    await page.goto(DOSSIER_PAGE);
    const banner = page.getByTestId("incompleteness-banner");
    await expect(banner).toBeVisible();
    const bannerBorder = await banner.evaluate(
      (el) => getComputedStyle(el).borderTopColor,
    );
    const disagree = await tokenValue(page, "--sig-epi-disagree-mark");
    const disagreeText = await tokenValue(page, "--sig-epi-disagree-text");
    expect(bannerBorder).not.toBe(disagree);
    expect(bannerBorder).not.toBe(disagreeText);
    // ...and it IS the neutral essential-boundary token.
    expect(bannerBorder).toBe(await tokenValue(page, "--sig-rule-strong"));
  });
});

test.describe("dark scheme applies the chosen token set (SIG-UI-147 posture)", () => {
  test("dark tokens differ from light and keep body text on the dark page", async ({ page }) => {
    await page.emulateMedia({ colorScheme: "light" });
    await page.goto("/visual-language/");
    const lightBg = await computed(page, "body", "background-color");
    const lightInk = await computed(page, "body", "color");

    await page.emulateMedia({ colorScheme: "dark" });
    const darkBg = await computed(page, "body", "background-color");
    const darkInk = await computed(page, "body", "color");

    // A chosen set: the page darkens and the ink lightens — never an inversion
    // artefact like a dark link on an untouched white surface.
    expect(darkBg).not.toBe(lightBg);
    expect(darkInk).not.toBe(lightInk);
    expect(darkBg).toBe(await tokenValue(page, "--sig-bg"));
    expect(darkInk).toBe(await tokenValue(page, "--sig-ink"));

    // The disagreement hue also has a chosen dark value.
    const darkMarker = await tokenValue(page, "--sig-epi-disagree-mark");
    await page.emulateMedia({ colorScheme: "light" });
    const lightMarker = await tokenValue(page, "--sig-epi-disagree-mark");
    expect(darkMarker).not.toBe(lightMarker);
  });
});

test.describe("reduced motion zeroes the motion tokens (SIG-UI-149 posture)", () => {
  test("a token-driven transition reports a 0s duration under reduce", async ({ page }) => {
    await page.goto("/visual-language/");
    // The nav links transition their border colour through --sig-motion-1.
    const normal = await page.locator(".sig-nav__list a").first().evaluate(
      (el) => getComputedStyle(el).transitionDuration,
    );
    expect(Number.parseFloat(normal)).toBeGreaterThan(0);

    await page.emulateMedia({ reducedMotion: "reduce" });
    const reduced = await page.locator(".sig-nav__list a").first().evaluate(
      (el) => getComputedStyle(el).transitionDuration,
    );
    expect(Number.parseFloat(reduced)).toBe(0);
    // The motion token itself is the thing that changed.
    expect(await tokenValue(page, "--sig-motion-1", "transition-duration")).toBe("0s");
  });
});
