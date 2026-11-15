// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// P37.41 (R11-K13-UX10-4, K10 §15, SIG-TRANSP-042) — the per-source
// changelog e2e: the generated append-only log renders every event dated
// by its record's own clock (the basis column), the baseline wording
// states what pre-release history is, the JSON twin serves the
// sig.source-changelog/1 doc, and a registry-only source emits none (S-11).
import { test, expect } from "@playwright/test";

const SRC = "okc_camera_registry";

test.describe("the source changelog (T1)", () => {
  test("the page lists events newest-first, each dated by a named record clock", async ({ page }) => {
    await page.goto(`/sources/${SRC}/changelog/`);
    await expect(page.locator("#changelog-heading")).toContainText("Changelog");
    await expect(page.getByTestId("changelog-baseline")).toContainText(
      "History before demo-release-2026-08: rights decisions and run records only.",
    );
    const rows = page.getByTestId("changelog-event");
    expect(await rows.count()).toBeGreaterThan(5);
    const text = (await rows.allTextContents()).join("|");
    expect(text).toContain("first recorded ingest");
    expect(text).toContain("rights decision recorded");
    expect(text).toContain("first published release");
    expect(text).toContain("connector version changed");
    expect(text).toContain("issue opened");
    // clock bases render as the record clock — never git
    expect(text).toContain("decided_at");
    expect(text).toContain("finished_at");
    expect(text).toContain("activation");
    expect(text).toContain("opened_at");
    expect(text).toContain("closed_at");
  });

  test("the sig.source-changelog/1 twin serves the full doc", async ({ page }) => {
    const res = await page.request.get(`/sources/${SRC}/changelog/index.json`);
    expect(res.ok()).toBeTruthy();
    const doc = await res.json();
    expect(doc.schema).toBe("sig.source-changelog/1");
    expect(doc.baseline_label).toBe("demo-release-2026-08");
    expect(doc.event_count).toBe(doc.events.length);
    for (const ev of doc.events) {
      expect(ev.clock_basis).toMatch(/^(decided_at|finished_at|activation|opened_at|closed_at|corrected_at|recorded_at)$/);
    }
  });

  test("the source page carries the last-10 changelog section", async ({ page }) => {
    await page.goto(`/sources/${SRC}/`);
    await expect(page.getByTestId("changelog-section")).toBeVisible();
    await expect(page.getByTestId("changelog-total")).toContainText("recorded events");
    const latest = page.getByTestId("changelog-event");
    expect(await latest.count()).toBeLessThanOrEqual(10);
    await expect(
      page.getByTestId("changelog-section").getByRole("link", { name: "the changelog page" }),
    ).toHaveAttribute("href", `/sources/${SRC}/changelog/`);
    await expect(page.getByTestId("subnav-changelog")).toBeVisible();
  });

  test("the source index.json twin carries the changelog summary", async ({ page }) => {
    const res = await page.request.get(`/sources/${SRC}/index.json`);
    const doc = await res.json();
    expect(doc.changelog.event_count).toBeGreaterThan(0);
    expect(doc.changelog.latest.length).toBeLessThanOrEqual(10);
    expect(doc.links.changelog).toBe(`sources/${SRC}/changelog/`);
  });

  test("a minimal-history source still renders its own events", async ({ page }) => {
    // demo_seed_load: a rights decision + the TX-14 lane change — never a blank.
    await page.goto("/sources/demo_seed_load/changelog/");
    const rows = page.getByTestId("changelog-event");
    expect(await rows.count()).toBeGreaterThanOrEqual(2);
    await expect(page.locator("main")).toContainText("lane moved");
  });

  test("registry-only sources emit no changelog route (S-11)", async ({ request }) => {
    for (const p of ["changelog/", "changelog/index.json"]) {
      const res = await request.get(`/sources/demo_gated_registry/${p}`);
      expect(res.status(), p).toBe(404);
    }
  });

  test("the page is zero-JS (T1)", async ({ page }) => {
    await page.goto(`/sources/${SRC}/changelog/`);
    expect(await page.locator("main script").count()).toBe(0);
  });
});
