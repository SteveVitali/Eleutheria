// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

import { test, expect } from "@playwright/test";
import { DISCOVERED_ROUTES, DATA_SOURCE, gotoSettled } from "../e2e/pages";
import {
  VISUAL_TEMPLATE_GROUPS,
  claimedComponents,
  selectRepresentative,
} from "./templates";

// P37.60 (UXK14-10, SIG-UI-152, DR-K14-18) — the visual-regression grid.
//
// Coverage is DERIVED, never a hand list: the build's page-types manifest
// records each emitted route's `component` (the page module), the template
// registry (templates.ts) claims every module into a visual-template group,
// and each group shoots one deterministic representative at every
// {light, dark} × {1440, 390, 320} project cell. Canvases are masked (GPU
// rasterisation is not cross-runner deterministic, K14 R-9); every baseline
// file carries its approving ticket in baselines.json (a baseline change MUST
// cite its ticket — SIG-UI-152).

test.describe.configure({ mode: "parallel" });

const CLAIMED = claimedComponents();

const IS_NATIONAL = DATA_SOURCE === "national";

test("the served build is the synthetic national fixture (no real names, K0 §4.12.6)", () => {
  // SIG-UI-152 binds the grid to the synthetic fixture — the committed demo
  // fixtures carry real names and must never land in a baseline. The manifest
  // itself records the source, so a mis-wired preview fails loud here, never
  // writes a wrong-named baseline.
  expect(DATA_SOURCE).toBe("national");
});

test("every emitted component is claimed by a template group", () => {
  const unclaimed = DISCOVERED_ROUTES.filter(
    (r) => r.component === "unresolved" || !CLAIMED.has(r.component),
  ).map((r) => `${r.component} (${r.path})`);
  expect(
    unclaimed,
    "template registry drift — a page module emitted a route no group claims; add it to tests/visual/templates.ts",
  ).toEqual([]);
});

const PICKS = VISUAL_TEMPLATE_GROUPS.map((g) => selectRepresentative(g, DISCOVERED_ROUTES));

test("every required template group resolves a representative route", () => {
  const missing = PICKS.filter(
    (p) => p.path === null && p.group.optional !== true,
  ).map((p) => `${p.group.id} (${p.group.components.join(", ")})`);
  expect(
    missing,
    "a template group emitted no route on this build — the grid would silently lose a template",
  ).toEqual([]);
});

for (const pick of PICKS) {
  if (pick.path === null) {
    // Optional, data-dependent family — recorded, never silently dropped.
    test(`unemitted: ${pick.group.id}`, () => {
      test.info().annotations.push({
        type: "unemitted-template",
        description: pick.group.components.join(", "),
      });
    });
    continue;
  }
  const path = pick.path;
  test(`${pick.group.id} — ${path}`, async ({ page }, testInfo) => {
    // Belt and braces beside the guard test above: a fixtures/export dist
    // must NEVER render a screenshot — Playwright writes the actual at the
    // expected path on a missing baseline, and real names in a committed
    // baseline are the exact failure K0 §4.12.6 names. Skipping here keeps
    // the grid incapable of shooting the wrong corpus; the guard test still
    // fails red so the mis-wire is loud, not silent.
    test.skip(
      !IS_NATIONAL,
      "the visual grid only runs on the synthetic national build (no real names)",
    );
    // Determinism fix (R-9): the site font is `font-display: optional` — a
    // deliberate CLS choice in shipped CSS, but it makes "webfont or
    // fallback" a timing decision taken at each first paint, so the same
    // page can render different metrics run-to-run. For the grid ONLY, the
    // stylesheet is rewritten to `swap`: `toHaveScreenshot` already waits on
    // `document.fonts`, so every cell then renders the same webfont — the
    // canonical render — regardless of load timing. The shipped CSS keeps
    // `optional`; this rewrite never leaves the test.
    await page.route(/\.css($|\?)/, async (route) => {
      const resp = await route.fetch();
      const headers = { ...resp.headers() };
      // The body below is re-encoded plain text — stale wire headers would
      // gunzip it back to garbage.
      delete headers["content-encoding"];
      delete headers["content-length"];
      const body = (await resp.text()).replace(
        /font-display:\s*optional/g,
        "font-display:swap",
      );
      await route.fulfill({ response: resp, body, headers });
    });
    await gotoSettled(page, path);
    // MapLibre's load/draw latches can precede the debounced In-view list.
    // Detect the static mount marker as well as the hydrated island, so a
    // late mount cannot silently skip these waits. `data-drawn` latches
    // after any drawn compartment source loads; it is not an all-source
    // completion signal. The seeded map case checks actual list status below.
    const mapMount = page.locator(
      '[data-testid="map-island"], [data-testid="map-island-placeholder"]',
    );
    if ((await mapMount.count()) > 0) {
      const island = page.getByTestId("map-island");
      await expect(island).toHaveAttribute("data-ready", "true", {
        timeout: 30_000,
      });
      await expect(island).toHaveAttribute("data-drawn", "true", {
        // The national tile storm's recorded bound — the same arm the
        // J1–J10 battery uses (map-journeys' DRAWN_TIMEOUT).
        timeout: IS_NATIONAL ? 120_000 : 20_000,
      });
    }
    if (pick.group.id === "map") {
      // Drawn can precede the debounced list update. This seeded, unfiltered
      // route must show populated groups before capture; the unchanged image
      // assertion still checks their appearance, not all-source completeness.
      await expect(page.getByTestId("inview-status")).toHaveText(
        /^[1-9]\d* records? in view — grouped by place$/,
      );
    }
    await expect(page).toHaveScreenshot(`${pick.group.id}--${testInfo.project.name}.png`, {
      // GPU-rastered surfaces (MapLibre/sigma) are not cross-runner
      // deterministic — masked per SIG-UI-152; [data-visual-mask] is the
      // opt-in hook for any future volatile region.
      mask: [page.locator("canvas"), page.locator("[data-visual-mask]")],
    });
  });
}
