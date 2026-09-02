// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

import { defineConfig, devices } from "@playwright/test";

// The e2e/a11y suite runs against the BUILT static site served by `astro preview`
// (not the dev server), so it exercises exactly the archivable HTML that ships.
// Two projects:
//   - "chromium": JavaScript enabled — runs axe (SIG-UI-037 WCAG 2.2 AA) and the
//     render-path assertions.
//   - "no-js": JavaScript DISABLED — proves core content is usable without JS
//     (SIG-UI-037). Since the shell ships zero client JS, both must behave the same.
const PORT = 4321;

export default defineConfig({
  testDir: "tests/e2e",
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
      testIgnore: /\.nojs\.spec\.ts$/,
    },
    {
      name: "no-js",
      use: { ...devices["Desktop Chrome"], javaScriptEnabled: false },
      testMatch: /\.nojs\.spec\.ts$/,
    },
  ],
  webServer: {
    command: `npm run build && npm run preview -- --port ${PORT}`,
    port: PORT,
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
  },
});
