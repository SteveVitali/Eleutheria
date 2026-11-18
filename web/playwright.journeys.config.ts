// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// P37.63 (K1 MAP-07): the dedicated runner for the J1–J10 map-acceptance
// journey battery over the REAL-SIZED national build. It mirrors
// playwright.visual.config.ts's posture: serve whatever dist/ is present —
// national_budget_leg.sh journeys guarantees a SIG_DATA_SOURCE=national
// build precedes it (and refuses a fixtures/export dist), and the spec's
// IS_NATIONAL branches then exercise the tile/cell path at real scale. The
// same spec file also runs inside the ordinary `test:e2e` pass under
// committed fixtures via playwright.config.ts — one battery, both corpora.

import { defineConfig, devices } from "@playwright/test";

const PORT = 4321;

export default defineConfig({
  testDir: "tests/e2e",
  testMatch: /map-journeys\.spec\.ts$/,
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: 0,
  reporter: process.env.CI ? "list" : [["list"]],
  use: {
    baseURL: `http://localhost:${PORT}`,
    trace: "on-first-retry",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
  webServer: {
    // Preview-only — the journeys leg's dist guard ensures the served build
    // is the national one; a stale fixtures dist can never be mistaken for
    // the real-sized corpus because the script refuses it first.
    command: `npm run preview -- --port ${PORT}`,
    port: PORT,
    reuseExistingServer: false,
    timeout: 120_000,
  },
});
