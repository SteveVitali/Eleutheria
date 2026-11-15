// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

import { defineConfig, devices } from "@playwright/test";

// The e2e/a11y suite runs against the BUILT static site served by `astro preview`
// (not the dev server), so it exercises exactly the archivable HTML that ships.
// Four projects:
//   - "chromium": JavaScript enabled — runs axe (SIG-UI-037 WCAG 2.2 AA) and the
//     render-path assertions.
//   - "no-js": JavaScript DISABLED — proves core content is usable without JS
//     (SIG-UI-037). Since the shell ships zero client JS, both must behave the same.
//   - "dark": prefers-color-scheme dark (P37.60, DR-K14-13 / SIG-UI-147) —
//     every template representative, axe in dark, print forces light.
//   - "reduced-motion": prefers-reduced-motion reduce (P37.60, DR-K14-15 /
//     SIG-UI-149) — zero-duration sweep plus post-interaction T2 checks.
// The visual-regression grid (SIG-UI-152) lives in playwright.visual.config.ts
// — it runs a different build (SIG_DATA_SOURCE=national).
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
      testIgnore: [/\.nojs\.spec\.ts$/, /dark\.spec\.ts$/, /reduced-motion\.spec\.ts$/],
    },
    {
      name: "no-js",
      use: { ...devices["Desktop Chrome"], javaScriptEnabled: false },
      testMatch: /\.nojs\.spec\.ts$/,
    },
    {
      name: "dark",
      use: { ...devices["Desktop Chrome"], colorScheme: "dark" },
      testMatch: /dark\.spec\.ts$/,
    },
    {
      name: "reduced-motion",
      use: {
        ...devices["Desktop Chrome"],
        contextOptions: { reducedMotion: "reduce" },
      },
      testMatch: /reduced-motion\.spec\.ts$/,
    },
  ],
  webServer: {
    // P34.10: the e2e suite exercises the FULL surface — the allow-listed public
    // routes plus the internal/withdrawn ones (`/curate/**`, `/releases/`,
    // `/research-dossier/`, `/visual-language/`, `/contribution-back/`) that the
    // default build never emits (SIG-OPS-003). `SIG_BUILD_INTERNAL=1` injects them
    // (astro.config.mjs `sigInternalRoutes`); publishable builds never set it.
    command: `SIG_BUILD_INTERNAL=1 npm run build && npm run preview -- --port ${PORT}`,
    port: PORT,
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
  },
});
