// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// P36.14 / SIG-RECON-052 (§30.4): every inference is visually and structurally
// distinguishable from observed evidence. The worked dossier fixture carries a
// governance-chain link — an L4 derived fact (`inferred: true`, `layer: "L4"`) —
// and the built page must render the persistent `sig-inferred` marker: a glyph +
// a text label (never colour alone, SIG-UI-005), emitted as plain HTML.
import { test, expect } from "@playwright/test";
import { DOSSIER_JSON, DOSSIER_PAGE, DOSSIER_PRINT } from "./pages";

test("an L4 governance row renders the inferred marker — glyph + text (SIG-RECON-052)", async ({
  page,
}) => {
  await page.goto(DOSSIER_PAGE);
  const marker = page.getByTestId("inferred-marker");
  await expect(marker.first()).toBeVisible();
  // The marker carries its own non-colour channels: the ◈ glyph and the
  // "Inferred" label — the row is distinguishable without any styling.
  await expect(marker.first()).toContainText("Inferred");
  await expect(marker.first().locator(".sig-inferred__glyph")).toContainText("◈");
  await expect(marker.first()).toHaveClass(/\bsig-inferred\b/);
  await expect(marker.first()).toHaveAttribute("data-inferred", "true");
  await expect(marker.first()).toHaveAttribute("data-layer", "L4");
  // …and it marks the derived link, beside the value it qualifies.
  const row = marker.first().locator("xpath=..");
  await expect(row).toContainText("Motorola Solutions");
  await expect(row).toContainText("L4");
});

test("the dossier JSON twin carries the typed marker fields (SIG-RECON-052)", async ({
  request,
}) => {
  const res = await request.get(DOSSIER_JSON);
  expect(res.ok()).toBe(true);
  const body = await res.json();
  const rows = (body.sections ?? []).flatMap((s: { rows?: unknown[] }) => s.rows ?? []);
  const marked = rows.filter(
    (r: Record<string, unknown>) => r.inferred === true && r.layer === "L4",
  );
  expect(marked.length).toBeGreaterThan(0);
});

test("the print export marks the inference too (SIG-RECON-052)", async ({ page }) => {
  await page.goto(DOSSIER_PRINT);
  await expect(page.getByTestId("inferred-marker").first()).toBeVisible();
});
