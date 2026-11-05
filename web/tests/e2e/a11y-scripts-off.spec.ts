// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// P36.72a (ACC-PLACES / K0 §4.12 item 7, SIG-UI-037): axe WCAG 2.2 AA in BOTH
// JS states. `a11y.spec.ts` already sweeps every discovered route with JS on;
// this spec is the JS-OFF leg: every script request is aborted at the
// network layer, so the page renders exactly the DOM its shipped markup
// produces with no script loaded — the same render path the no-JS project's
// javaScriptEnabled:false sweeps prove usable (axe itself cannot inject into
// a JS-disabled context, which is why the DOM is reproduced this way).
// Difference vs a true no-JS load, stated honestly: `<noscript>` blocks stay
// un-rendered here (scripting is enabled but never arrives); their presence
// is asserted below and their rendered visibility is covered by the no-js
// project's DOM assertions (map-baseline/workspace/nojs-parity specs).

import { expect, test } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { A11Y_PAGES, T2_PAGES, gotoSettled } from "./pages";

const WCAG_TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"];

async function suppressScripts(page: import("@playwright/test").Page): Promise<void> {
  await page.route("**/*", (route) => {
    const req = route.request();
    const path = new URL(req.url()).pathname;
    if (req.resourceType() === "script" || /\.[cm]?js$/.test(path)) {
      return route.abort();
    }
    return route.continue();
  });
}

for (const path of A11Y_PAGES) {
  test(`WCAG 2.2 AA (scripts off): ${path}`, async ({ page }) => {
    await suppressScripts(page);
    await gotoSettled(page, path);
    // the assertion is about the render path, not the delivery failure mode:
    // every page script was refused before it ran
    const results = await new AxeBuilder({ page }).withTags(WCAG_TAGS).analyze();
    expect(results.violations, JSON.stringify(results.violations, null, 2)).toEqual([]);
  });
}

test.describe("the no-JS additions themselves", () => {
  test("every T2 route ships its no-JS state notice in the served HTML", async ({ request }) => {
    for (const path of T2_PAGES) {
      const res = await request.get(path);
      expect(res.status()).toBe(200);
      const html = await res.text();
      expect(html).toContain("<noscript");
      expect(html).toContain('data-testid="no-js-state-notice"');
    }
  });
});
