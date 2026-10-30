// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// P36.23 (UXK14-3b, SIG-UI-037) — the no-JS half of the component-kit-B
// contract: the whole epistemic visual layer is complete server-rendered
// HTML. Markers, ranges, chips, panels, callouts, banners, typed empties and
// error states read identically with JavaScript off — the popovers are
// UA-native, never script. Runs in the "no-js" project (JavaScript disabled).

import { test, expect } from "@playwright/test";

const HARNESS = "/component-kit/";

test("every kit-B component is complete with JavaScript disabled", async ({ page }) => {
  await page.goto(HARNESS);
  // The contested marker — both levels + the both-sides link.
  const markers = page.getByTestId("contested-marker");
  await expect(markers.filter({ hasText: "Unresolved" }).first()).toBeVisible();
  await expect(page.locator("a[data-testid='contested-marker']").first()).toBeVisible();

  // The range — labelled points, both agreement variants, claims listed.
  await expect(page.getByTestId("contradiction-range")).toHaveCount(2);
  await expect(
    page.locator("[data-testid='contradiction-range'][data-agreement='IRRECONCILABLE']"),
  ).toHaveClass(/sig-range--unresolved/);
  await expect(page.locator(".sig-range__point-label")).toHaveCount(6);

  // The absence chip — four kinds, popover ids unique, the action link.
  await expect(page.getByTestId("kit-absence-chips").getByTestId("absence-chip")).toHaveCount(
    4,
  );
  await expect(page.locator(".sig-absence-chip__help").first()).toHaveAttribute(
    "href",
    "/research-queue/",
  );

  // The provenance panel — the one contract, both binding states.
  await expect(
    page.getByTestId("kit-provenance").locator("[data-provenance-panel]"),
  ).toHaveCount(2);

  // Callouts — the three closed kinds.
  await expect(page.getByTestId("kit-callouts").locator(".sig-callout")).toHaveCount(3);

  // The banner + the eight typed causes + the four error states.
  await expect(page.getByTestId("kit-incomplete")).toBeVisible();
  await expect(page.locator("[data-cause='filtered_none']")).toHaveAttribute(
    "data-hatch",
    "false",
  );
  await expect(page.getByTestId("kit-error-states").locator("[data-error-kind]")).toHaveCount(
    4,
  );
});

test("the map's record absences render the actionable chip — O4 without JavaScript", async ({
  page,
}) => {
  // The "Help find it" affordance reaches the research queue on the real
  // public surface — the no-JS equivalent list carries it per record.
  await page.goto("/map/");
  const chips = page.getByTestId("absence-chip");
  const count = await chips.count();
  expect(count, "map mounts absence chips on its unlocated records").toBeGreaterThanOrEqual(1);
  for (let i = 0; i < count; i++) {
    await expect(chips.nth(i).locator(".sig-absence-chip__help")).toHaveAttribute(
      "href",
      "/research-queue/",
    );
  }
});
