// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// P32.15 (SIG-FIND-005, ADR-134): the explicit per-island JavaScript/network
// budgets — measured as the assets each island page actually fetches, enforced
// here in the same `npm run check` gate as the rest of the suite (the lhci
// `check:perf` matrices assert the same ceilings for the Lighthouse run).
// The zero-JS public pages keep their hard 0-script / ≤150 KiB contract via
// islands.spec.ts + lighthouserc — nothing here relaxes it.
import { test, expect } from "@playwright/test";
import { gzipSync } from "node:zlib";
import budgets from "./island-budgets.json" with { type: "json" };

interface AssetMeasure {
  raw: number;
  gzip: number;
}

test.describe("per-island asset budgets (SIG-FIND-005)", () => {
  for (const [path, budget] of Object.entries(budgets.islands)) {
    test(`${path} stays inside its measured JS/network budget`, async ({ page, request }) => {
      const resp = await page.goto(path);
      expect(resp?.status()).toBe(200);
      const html = (await resp?.text()) ?? "";
      const docBytes = Buffer.byteLength(html);
      expect(docBytes).toBeLessThanOrEqual(budget.documentMaxBytes);

      // Let the island finish hydrating so deferred fetches (the maplibre
      // worker, tile archives on export builds) are counted too.
      if (path === "/map/") {
        await expect(page.getByTestId("map-island")).toHaveAttribute("data-ready", "true", {
          timeout: 20_000,
        });
      } else {
        await page.waitForLoadState("networkidle");
      }

      // Every /_astro/ resource the page actually fetched — script modules,
      // the web worker, stylesheets — measured on the wire (raw) and
      // re-compressed locally (gzip) for the documented compressed baseline.
      const urls: string[] = await page.evaluate(() =>
        performance
          .getEntriesByType("resource")
          .map((r) => (r as PerformanceResourceTiming).name)
          .filter((u) => u.includes("/_astro/")),
      );
      expect(urls.length).toBeGreaterThan(0);
      const measure = new Map<string, AssetMeasure>();
      let scriptRaw = 0;
      let scriptGzip = 0;
      let totalRaw = 0;
      let totalGzip = 0;
      for (const url of urls) {
        if (measure.has(url)) continue;
        const r = await request.get(url);
        expect(r.ok()).toBe(true);
        const body = await r.body();
        const m: AssetMeasure = { raw: body.length, gzip: gzipSync(body).length };
        measure.set(url, m);
        totalRaw += m.raw;
        totalGzip += m.gzip;
        if (url.endsWith(".js") || url.endsWith(".mjs")) {
          scriptRaw += m.raw;
          scriptGzip += m.gzip;
        }
      }

      expect(
        scriptRaw,
        `script-family raw bytes (${scriptRaw}) exceeds the budget`,
      ).toBeLessThanOrEqual(budget.scriptRawMaxBytes);
      expect(
        scriptGzip,
        `script-family gzip bytes (${scriptGzip}) exceeds the budget`,
      ).toBeLessThanOrEqual(budget.scriptGzipMaxBytes);
      expect(totalRaw + docBytes).toBeLessThanOrEqual(budget.totalRawMaxBytes);
      expect(totalGzip + docBytes).toBeLessThanOrEqual(budget.totalGzipMaxBytes);
    });
  }
});
