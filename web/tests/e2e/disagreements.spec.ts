// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// P37.38 (R11-K13-CX-01, K13 §8 J3, SIG-UI-071) — the disagreements browser:
// the hub keeps three typed kinds apart; a place page shows both sides of a
// recorded contradiction with sources and dates; zero-of-a-kind is a typed
// absence, never a smoothed zero (J3: "≠ marker → both sides; kinds apart").

import { expect, test } from "@playwright/test";

const CONTRA = "contra:device-count-42-38";

test.describe("/disagreements/ — the hub", () => {
  test("lists the three typed kinds with counts from the release", async ({ page }) => {
    await page.goto("/disagreements/");
    await expect(page.getByTestId("kind-count-contradiction")).toHaveText("1");
    await expect(page.getByTestId("kind-count-coordinate_conflict")).toContainText("place");
    await expect(page.getByTestId("kind-count-declared_vs_located")).toContainText("place");
  });

  test("a recorded contradiction renders both sides — source and dates", async ({ page }) => {
    await page.goto("/disagreements/");
    const rec = page.getByTestId("contradiction-record").filter({ hasText: CONTRA });
    await expect(rec).toBeVisible();
    const sides = rec.getByTestId("contradiction-side");
    await expect(sides).toHaveCount(2);
    await expect(rec).toContainText("Active device count = 42");
    await expect(rec).toContainText("Portal-reported device count = 38");
    await expect(rec).toContainText("observed 2026-07-01");
    await expect(rec).toContainText("observed 2026-08-01");
    // Both sides link their claim pages.
    const links = await rec.getByRole("link", { name: "claim page" }).all();
    expect(links.length).toBe(2);
  });

  test("the aggregate kinds list their places, linking place pages", async ({ page }) => {
    await page.goto("/disagreements/");
    const coord = page.getByTestId("coordinate-conflict-table");
    await expect(coord.getByTestId("coordinate-conflict-row").first()).toBeVisible();
    const declared = page.getByTestId("declared-located-table");
    await expect(declared).toContainText("Harris County");
    // place links resolve
    await expect(page.getByTestId("place-link").first()).toBeVisible();
    await expect(
      page.getByTestId("place-link").locator('a[href="/disagreements/place/usa/ok/"]').first(),
    ).toBeVisible();
  });
});

test.describe("/disagreements/place/<slug>/ — a place's three kinds", () => {
  test("usa/ok carries all three kinds kept apart", async ({ page }) => {
    await page.goto("/disagreements/place/usa/ok/");
    const rec = page.getByTestId("contradiction-record");
    await expect(rec).toHaveCount(1);
    await expect(rec.getByTestId("contradiction-side")).toHaveCount(2);
    // coordinate conflicts: the per-source rows, not merged into contradictions
    const rows = page.getByTestId("coordinate-conflict-source");
    await expect(rows).toHaveCount(1);
    await expect(rows.first()).toContainText("3");
    // declared-vs-located: both directions, the counterpart named + linked
    await expect(page.getByTestId("declared-here-table")).toContainText("Harris County");
    const cp = page.getByTestId("declared-here-row").first().getByRole("link");
    await expect(cp).toHaveAttribute("href", "/disagreements/place/usa/tx/harris-county-48201/");
  });

  test("usa/tx renders the three typed absences — never a smoothed zero", async ({ page }) => {
    await page.goto("/disagreements/place/usa/tx/");
    await expect(page.getByTestId("contradictions-absent")).toBeVisible();
    await expect(page.getByTestId("coordinate-conflicts-absent")).toBeVisible();
    await expect(page.getByTestId("declared-located-absent")).toBeVisible();
    await expect(page.getByTestId("contradiction-record")).toHaveCount(0);
  });

  test("harris-county shows the disagreement's other side — both sides visible", async ({ page }) => {
    await page.goto("/disagreements/place/usa/tx/harris-county-48201/");
    await expect(page.getByTestId("declared-located-totals")).toContainText("12");
    const cp = page.getByTestId("located-here-row").first().getByRole("link");
    await expect(cp).toHaveAttribute("href", "/disagreements/place/usa/ok/");
  });

  test("the page links back to the dossier and the hub (UXR-21)", async ({ page }) => {
    await page.goto("/disagreements/place/oklahoma-city/");
    await expect(page.getByRole("link", { name: "The Oklahoma City dossier" })).toHaveAttribute(
      "href", "/dossier/oklahoma-city/",
    );
    await expect(page.getByRole("link", { name: "All disagreements" })).toHaveAttribute(
      "href", "/disagreements/",
    );
  });
});

test.describe("the dossier hands its place to the browser (UXR-21)", () => {
  test("a dossier with disagreements links its place page", async ({ page }) => {
    await page.goto("/dossier/oklahoma-city/");
    const link = page.getByRole("link", { name: /All disagreements for Oklahoma City/ });
    await expect(link).toHaveAttribute("href", "/disagreements/place/oklahoma-city/");
  });
});
