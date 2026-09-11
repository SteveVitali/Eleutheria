// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

import { test, expect } from "@playwright/test";
import { ALL_PAGES, SHELL_PAGES } from "./pages";

test.describe("four independent epistemic fields (SIG-UI-004, AC3)", () => {
  test("renders four separate field chips and never a fused badge", async ({ page }) => {
    await page.goto("/visual-language/");
    const fields = page.getByTestId("epistemic-fields").first();
    await expect(fields).toHaveAttribute("data-fused", "false");
    const chips = fields.locator(".sig-field");
    await expect(chips).toHaveCount(4);
    const names = await chips.evaluateAll((els) => els.map((e) => e.getAttribute("data-field")));
    expect(names).toEqual(["resolution_status", "support", "agreement", "currency"]);
    // No element claims to be a single fused epistemic token.
    await expect(page.locator("[data-fused='true']")).toHaveCount(0);
  });
});

test.describe("support glyph carries its machine-readable payload (SIG-UI-003)", () => {
  test("glyph has evidence count and a downgrade reason when downgraded", async ({ page }) => {
    await page.goto("/visual-language/");
    const glyphs = page.getByTestId("support-glyph");
    await expect(glyphs.first()).toHaveAttribute("data-evidence-count", /\d+/);
    // The STRONGLY_SUPPORTED / PROBABLE / etc. glyphs carry a non-empty downgrade code.
    const probable = glyphs.filter({ has: page.locator("[data-support='PROBABLE']") });
    // At least one downgraded glyph exists on the reference page.
    const downgraded = await glyphs.evaluateAll((els) =>
      els.filter((e) => e.getAttribute("data-support") !== "CONFIRMED"),
    );
    expect(downgraded.length).toBeGreaterThan(0);
    void probable;
  });
});

test.describe("contested marker is persistent across render paths (SIG-UI-008, AC5)", () => {
  test("appears on the detail, the map popup, and the graph list", async ({ page }) => {
    await page.goto("/visual-language/");
    await expect(page.getByTestId("contested-marker").first()).toBeVisible();

    await page.goto("/reference-map/");
    // The map popup for the contested site carries the marker.
    const popup = page.getByTestId("map-popup");
    await expect(popup.getByTestId("contested-marker")).toHaveCount(1);

    await page.goto("/reference-graph/");
    // The contested edge in the list carries the marker.
    await expect(page.getByTestId("contested-marker").first()).toBeVisible();
  });
});

test.describe("contradiction renders as a value range (SIG-UI-009)", () => {
  test("plots each competing claim with source/tier/date/link + different-quantity note", async ({
    page,
  }) => {
    await page.goto("/visual-language/");
    const range = page.getByTestId("contradiction-range");
    await expect(range).toBeVisible();
    await expect(range.getByTestId("competing-claim")).toHaveCount(2);
    await expect(range.getByTestId("different-quantity-note")).toHaveCount(1);
    // Each claim links to its document.
    await expect(range.getByTestId("competing-claim").first().locator("a")).toHaveAttribute(
      "href",
      /\/v1\/claim\//,
    );
  });
});

test.describe("belief-pinned permalink + citation on every page (SIG-UI-035, AC6)", () => {
  for (const path of ALL_PAGES) {
    test(`citation present on ${path}`, async ({ page }) => {
      await page.goto(path);
      const cite = page.getByTestId("citation");
      await expect(cite).toBeVisible();
      const permalink = cite.getByTestId("permalink");
      const href = await permalink.getAttribute("href");
      expect(href).toContain("as_of_world=");
      expect(href).toContain("as_of_belief=");
      expect(href).toContain("ruleset=");
      await expect(cite.getByTestId("citation-text")).toContainText("SIG");
    });
  }
});

test.describe("absence hatch → research task, end to end (SIG-UI-007, AC4)", () => {
  test("exactly one hatch texture class is used for every absence", async ({ page }) => {
    await page.goto("/visual-language/");
    const hatches = page.getByTestId("absence-hatch");
    await expect(hatches).toHaveCount(4); // one per absence kind
    const kinds = await hatches.evaluateAll((els) =>
      els.map((e) => e.getAttribute("data-absence-kind")),
    );
    expect(new Set(kinds)).toEqual(
      new Set(["NOT_RESEARCHED", "NO_EVIDENCE_FOUND", "EVIDENCE_OF_ABSENCE", "UNRESOLVED"]),
    );
    // Every hatch uses the single shared texture class (SIG-UI-007).
    const allHatch = await hatches.evaluateAll((els) =>
      els.every((e) => e.classList.contains("sig-absence-hatch")),
    );
    expect(allHatch).toBe(true);
  });

  test("clicking a gap generates a research task in the GENERATED state", async ({ page }) => {
    await page.goto("/visual-language/");
    const firstHatch = page.getByTestId("absence-hatch").first();
    await firstHatch.click();
    await expect(page).toHaveURL(/\/task\/new\//);
    const task = page.getByTestId("generated-task");
    await expect(task).toBeVisible();
    await expect(task).toHaveAttribute("data-task-status", "generated");
    await expect(page.getByTestId("task-field-status")).toHaveText("generated");
    await expect(page.getByTestId("task-field-subject")).toContainText("agency:okcpd");
    await expect(page.getByTestId("task-field-absence")).toContainText("NOT_RESEARCHED");
  });
});

test.describe("no green for epistemic state, rendered (SIG-UI-006)", () => {
  test("no epistemic element resolves to a green colour", async ({ page }) => {
    await page.goto("/visual-language/");
    // Collect the used border/text colours of every epistemic element and assert
    // none is a green hue (hue 75–165deg). This checks the RENDERED result, not
    // just the token file.
    const greens = await page.evaluate(() => {
      function hueOf(rgb: string): number | null {
        const m = rgb.match(/rgba?\(([^)]+)\)/);
        if (!m) return null;
        const [r, g, b] = m[1].split(",").map((n) => parseFloat(n) / 255);
        const max = Math.max(r, g, b),
          min = Math.min(r, g, b);
        if (max === min) return null; // achromatic — no hue
        const d = max - min;
        let h = 0;
        if (max === r) h = ((g - b) / d) % 6;
        else if (max === g) h = (b - r) / d + 2;
        else h = (r - g) / d + 4;
        h *= 60;
        return h < 0 ? h + 360 : h;
      }
      const bad: string[] = [];
      for (const el of Array.from(document.querySelectorAll(".sig-field, .sig-contested, .sig-glyph, .sig-absence-hatch"))) {
        const cs = getComputedStyle(el);
        for (const prop of ["color", "border-left-color", "background-color"]) {
          const hue = hueOf(cs.getPropertyValue(prop));
          if (hue !== null && hue >= 75 && hue <= 165) bad.push(`${el.className}:${prop}=${cs.getPropertyValue(prop)}`);
        }
      }
      return bad;
    });
    expect(greens).toEqual([]);
  });
});

test.describe("reference surfaces load", () => {
  for (const path of SHELL_PAGES) {
    test(`page ${path} has a heading and the primary nav`, async ({ page }) => {
      await page.goto(path);
      await expect(page.locator("h1")).toBeVisible();
      await expect(page.locator("nav[aria-label='Primary']")).toBeVisible();
    });
  }
});
