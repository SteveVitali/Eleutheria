// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// Runs in the "no-js" Playwright project (JavaScript DISABLED). P36.14 /
// SIG-RECON-052: the inference marker is rendered server-side into the static
// HTML — the marker MUST appear with JS off, so the L4/observed distinction
// never depends on a script.
import { test, expect } from "@playwright/test";
import { DOSSIER_PAGE, DOSSIER_PRINT } from "./pages";

test("the inferred marker renders without JavaScript (SIG-RECON-052)", async ({ page }) => {
  await page.goto(DOSSIER_PAGE);
  const marker = page.getByTestId("inferred-marker");
  await expect(marker.first()).toBeVisible();
  await expect(marker.first()).toContainText("Inferred");
  await expect(marker.first()).toHaveClass(/\bsig-inferred\b/);
  await expect(marker.first()).toHaveAttribute("data-inferred", "true");
  await expect(marker.first()).toHaveAttribute("data-layer", "L4");
});

test("the print export carries the marker without JavaScript", async ({ page }) => {
  await page.goto(DOSSIER_PRINT);
  await expect(page.getByTestId("inferred-marker").first()).toBeVisible();
});
