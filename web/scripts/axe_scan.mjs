// SPDX-License-Identifier: Apache-2.0
// axe_scan.mjs — P35.56's V11 accessibility leg. Runs axe-core (the WCAG
// tag set web/tests/e2e/a11y.spec.ts uses) over a list of paths on one
// origin through playwright chromium.
//
//   node web/scripts/axe_scan.mjs <base-url> <path> [<path> ...]
//
// Resolves @playwright/test + @axe-core/playwright from web/node_modules
// (ESM resolution walks up from this file's directory — the script must
// live under web/). Prints a single JSON document on stdout:
//   {"results": {"<path>": [{"id": ..., "impact": ..., "nodes": n}, ...]}}
// A navigation or axe failure on a page records an `error` violation row
// (impact "critical") rather than silently dropping the page — an
// unevaluated page is never a pass.

import { chromium } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

const WCAG_TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"];

async function main() {
  const [base, ...paths] = process.argv.slice(2);
  if (!base || paths.length === 0) {
    console.error("usage: node axe_scan.mjs <base-url> <path>...");
    process.exit(2);
  }
  const browser = await chromium.launch();
  const results = {};
  try {
    for (const p of paths) {
      const url = new URL(p, base).toString();
      const context = await browser.newContext();
      const page = await context.newPage();
      try {
        await page.goto(url, { waitUntil: "load", timeout: 30000 });
        const scan = await new AxeBuilder({ page }).withTags(WCAG_TAGS).analyze();
        results[p] = (scan.violations || []).map((v) => ({
          id: v.id,
          impact: v.impact || "unknown",
          nodes: (v.nodes || []).length,
        }));
      } catch (err) {
        results[p] = [
          { id: "page-eval", impact: "critical", nodes: 1, error: String(err).slice(0, 200) },
        ];
      }
      await context.close();
    }
  } finally {
    await browser.close();
  }
  console.log(JSON.stringify({ results }));
}

main().catch((err) => {
  console.error(String(err));
  process.exit(1);
});
