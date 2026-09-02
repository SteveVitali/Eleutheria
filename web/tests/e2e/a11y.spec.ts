// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { A11Y_PAGES } from "./pages";

// WCAG 2.2 AA automated checks pass on every page (SIG-UI-037, AC2). axe-core is
// run with the WCAG 2.0/2.1/2.2 level-A and level-AA rule tags; any violation fails
// the build. This is the CI a11y gate.
const WCAG_TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"];

for (const path of A11Y_PAGES) {
  test(`WCAG 2.2 AA: ${path}`, async ({ page }) => {
    await page.goto(path);
    const results = await new AxeBuilder({ page }).withTags(WCAG_TAGS).analyze();
    expect(results.violations, JSON.stringify(results.violations, null, 2)).toEqual([]);
  });
}
