// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

import { defineConfig, devices } from "@playwright/test";

// P37.60 (UXK14-10, SIG-UI-152, DR-K14-18; K14 §9/R-9) — the visual-regression
// grid. Separate from playwright.config.ts because it runs a DIFFERENT build:
// the deterministic synthetic national fixture (`SIG_DATA_SOURCE=national`,
// invented names only — K0 §4.12.6/F-173), never the committed demo fixtures
// whose real names must not land in committed baselines.
//
//   matrix    six projects — {light, dark} × {1440, 390, 320} — one
//             `toHaveScreenshot` cell each per template group
//             (tests/visual/templates.ts).
//   mask      every <canvas> is masked (MapLibre/sigma surfaces raster
//             non-deterministically across GPUs — R-9) plus any
//             [data-visual-mask] opt-in.
//   baselines one platform-agnostic set under tests/visual/visual.spec.ts-
//             snapshots/ — generated on linux/amd64-class Chromium (the CI
//             runner's rendering stack; web fonts rasterise in-process so the
//             grid is deterministic within maxDiffPixelRatio 0.01). A baseline
//             change MUST cite its ticket (tests/visual/baselines.json +
//             tests/unit/visual-templates.test.ts).
const PORT = 4322;

const VIEWPORTS = {
  "1440": { width: 1440, height: 900 },
  "390": { width: 390, height: 844 },
  "320": { width: 320, height: 568 },
} as const;

const THEMES = ["light", "dark"] as const;

export default defineConfig({
  testDir: "tests/visual",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: 0,
  reporter: process.env.CI ? "list" : [["list"]],
  // One baseline set, no per-platform/per-project suffixes — the snapshot file
  // names the cell explicitly (`<group>--<theme>-<viewport>.png`).
  snapshotPathTemplate: "{testDir}/visual.spec.ts-snapshots/{arg}.png",
  expect: {
    toHaveScreenshot: {
      // DR-K14-18's bound verbatim.
      maxDiffPixelRatio: 0.01,
      animations: "disabled",
    },
  },
  use: {
    baseURL: `http://localhost:${PORT}`,
    trace: "on-first-retry",
  },
  projects: THEMES.flatMap((theme) =>
    (Object.keys(VIEWPORTS) as (keyof typeof VIEWPORTS)[]).map((vp) => ({
      name: `${theme}-${vp}`,
      use: {
        ...devices["Desktop Chrome"],
        colorScheme: theme,
        viewport: VIEWPORTS[vp],
      },
    })),
  ),
  webServer: {
    // Serves whatever dist/ is present — the national leg's `visual`
    // subcommand guarantees a SIG_DATA_SOURCE=national build precedes it
    // (national_budget_leg.sh visual), and the spec's data-source guard
    // fails loud on any fixtures/export dist so a stale build can never
    // shoot a wrong-named baseline.
    command: `npm run preview -- --port ${PORT}`,
    port: PORT,
    reuseExistingServer: false,
    timeout: 120_000,
  },
});
