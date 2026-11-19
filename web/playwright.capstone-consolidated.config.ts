// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// P37.68d (R11-K13-CAP-01, split d — the consolidated capstone row): the
// dedicated runner for the K13 §5.1 per-ask checks (U-003.1…U-003.11,
// SIG-UI-077) — one named acceptance check per ask, run once per
// {390, 1440 px} × {JS on, JS off} project cell.
//
// Two targets run the same spec file (tests/e2e/capstone-per-ask.spec.ts):
//   - fixtures (the fixture-verified layer): no env — `astro preview` serves
//     the built dist/ on :4336;
//   - the promoted release (the deferred live leg, D-P37.68d-1):
//     SIG_CAPSTONE_BASE_URL=<origin> skips the webServer and points the whole
//     battery at the promoted origin. A fixture/preview pass is recorded
//     fixture-verified and is NEVER reported as a live/public pass — the
//     record's label travels with the run.
//
// The consolidated 13-journey battery (SIG-UI-078) re-runs the three sibling
// spec files (capstone-advocate/-journalist/-organizer) through their own
// committed configs — this runner owns only the per-ask surface; the
// sibling configs already carry the identical cell matrix and the same
// SIG_CAPSTONE_BASE_URL swap.
//
// The same spec also runs inside the ordinary `test:e2e` pass (chromium,
// default viewport, JS on) so a regression fails in CI, never silently.

import { defineConfig, devices } from "@playwright/test";

const PORT = 4336;
const LIVE_BASE = process.env.SIG_CAPSTONE_BASE_URL;

export default defineConfig({
  testDir: "tests/e2e",
  testMatch: /capstone-per-ask\.spec\.ts$/,
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: 0,
  reporter: [
    ["list"],
    ["json", { outputFile: "test-results/capstone-per-ask.json" }],
  ],
  use: {
    baseURL: LIVE_BASE ?? `http://localhost:${PORT}`,
    trace: "on-first-retry",
  },
  projects: [
    {
      name: "capstone-1440-js",
      use: {
        ...devices["Desktop Chrome"],
        viewport: { width: 1440, height: 900 },
      },
    },
    {
      name: "capstone-390-js",
      use: {
        ...devices["Desktop Chrome"],
        viewport: { width: 390, height: 844 },
      },
    },
    {
      name: "capstone-1440-nojs",
      use: {
        ...devices["Desktop Chrome"],
        viewport: { width: 1440, height: 900 },
        javaScriptEnabled: false,
      },
    },
    {
      name: "capstone-390-nojs",
      use: {
        ...devices["Desktop Chrome"],
        viewport: { width: 390, height: 844 },
        javaScriptEnabled: false,
      },
    },
  ],
  ...(LIVE_BASE
    ? {}
    : {
        webServer: {
          // Preview-only — the fixtures leg serves whatever dist/ is present;
          // `sig-ops capstone-consolidated run --leg per-ask-fixture` builds
          // it first so a stale dist is never mistaken for the current build.
          command: `npm run preview -- --port ${PORT}`,
          port: PORT,
          reuseExistingServer: !process.env.CI,
          timeout: 120_000,
        },
      }),
});
