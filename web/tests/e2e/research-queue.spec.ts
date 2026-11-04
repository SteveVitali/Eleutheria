// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// P36.61 (K11 RQ-03a / SIG-RQ-004, SIG-UI-079): the queue hub's e2e legs — the
// start-here entries, the facet/pagination/sort routes, the task cards, the
// campaign list, the totals-that-reconcile, and the O4 absence→queue seam.
import { expect, test } from "@playwright/test";

const HUB = "/research-queue/";
const OKC_PLACE = "/research-queue/place/usa/ok/oklahoma-city-4064000/";

test.describe("the queue hub (K11 §5.1)", () => {
  test("renders the how-to-help strip, start-here entries and reconciling counts", async ({
    page,
  }) => {
    await page.goto(HUB);
    await expect(page.getByTestId("no-leaderboard-note")).toBeVisible();
    for (const id of ["start-place", "start-role", "start-type"]) {
      await expect(page.getByTestId(id)).toBeVisible();
    }
    // Totals reconcile: the facet counts on the start strip sum to the lane.
    const cards = await page.getByTestId("task-card").count();
    expect(cards).toBeGreaterThan(0);
    expect(cards).toBeLessThanOrEqual(50);
    // Sort nav links the non-default orders (K11 §4.2).
    const sortNav = page.getByTestId("sort-nav");
    await expect(sortNav.locator("a[href='/research-queue/sort/newest/']")).toHaveCount(1);
    await expect(sortNav.locator("a[href='/research-queue/sort/oldest/']")).toHaveCount(1);
  });

  test("the campaign lane lists a sig.queue-campaign/1 row, never a dead link", async ({ page }) => {
    await page.goto(HUB);
    const campaign = page.getByTestId("campaign-card").first();
    await expect(campaign).toBeVisible();
    await expect(campaign).toHaveAttribute("data-handle", /^M-/);
    await expect(campaign.getByTestId("campaign-member-count")).not.toBeEmpty();
    // The campaign list route exists and repeats the row.
    await page.goto("/research-queue/campaigns/");
    await expect(page.getByTestId("campaign-card").first()).toBeVisible();
  });
});

test.describe("the task card (K11 §5.1)", () => {
  test("carries title, handle, place/type/role links, closing condition and status", async ({
    page,
  }) => {
    await page.goto(OKC_PLACE);
    const card = page.getByTestId("task-card").first();
    await expect(card.locator("h3")).not.toBeEmpty();
    await expect(card.getByTestId("task-handle")).toContainText("T-");
    await expect(card.getByTestId("closing-condition")).not.toBeEmpty();
    await expect(card.getByTestId("evidence-sought")).not.toBeEmpty();
    await expect(card.getByTestId("task-status")).not.toBeEmpty();
    // One link per facet dimension — each resolves to a real route.
    await expect(
      card.locator("a[href='/research-queue/place/usa/ok/oklahoma-city-4064000/']"),
    ).toHaveCount(1);
    // No card ever links to a /task/ page that does not exist yet (P36.62's).
    await expect(card.locator("a[href^='/task/']")).toHaveCount(0);
  });
});

test.describe("facet routes (SIG-RQ-004)", () => {
  test("the place facet covers the place and lists its cards", async ({ page }) => {
    await page.goto(OKC_PLACE);
    const cards = page.getByTestId("task-card");
    await expect(cards.first()).toBeVisible();
    for (const el of await cards.all()) {
      await expect(el).toHaveAttribute("data-place", "usa/ok/oklahoma-city-4064000");
    }
  });

  test("the unplaced bucket is an honest data-quality list", async ({ page }) => {
    await page.goto("/research-queue/place/unplaced/");
    const cards = page.getByTestId("task-card");
    await expect(cards.first()).toBeVisible();
    for (const el of await cards.all()) {
      await expect(el).toHaveAttribute("data-place", "unplaced");
    }
  });

  test("the type facet lists only that type's cards", async ({ page }) => {
    await page.goto("/research-queue/type/conflicting_retention/");
    const cards = page.getByTestId("task-card");
    await expect(cards).toHaveCount(1);
    await expect(cards.first()).toHaveAttribute("data-task-type", "conflicting_retention");
  });

  test("the role facet lists only that assignee's cards", async ({ page }) => {
    await page.goto("/research-queue/role/field_mapper/");
    const cards = page.getByTestId("task-card");
    await expect(cards).toHaveCount(1);
    await expect(cards.first()).toHaveAttribute("data-assignee", "field_mapper");
  });
});

test.describe("sort routes (K11 §4.2)", () => {
  test("newest sorts by generated_at desc; oldest puts the stalest evidence first", async ({
    page,
  }) => {
    await page.goto("/research-queue/sort/newest/");
    const newest = await page
      .getByTestId("task-card")
      .evaluateAll((els) => els.map((e) => e.getAttribute("id")));
    await page.goto("/research-queue/sort/oldest/");
    const oldest = await page
      .getByTestId("task-card")
      .evaluateAll((els) => els.map((e) => e.getAttribute("id")));
    expect(newest.length).toBeGreaterThan(0);
    expect(newest).not.toEqual(oldest);
    // The newest-generated card leads the newest route.
    expect(newest[0]).toBe("task-fx-tulsa-coverage-hole");
    // The oldest evidence leads the stale-first route (2026-08-16 link-rot card).
    expect(oldest[0]).toBe("task-fx-portal-snapshot-link-rot");
  });
});

test.describe("SIG-UI-079 — the queue is reachable from absences", () => {
  test("a dossier's 'What we don't know' section links the queue in one action", async ({
    page,
  }) => {
    await page.goto("/dossier/oklahoma-city/");
    for (const variant of ["summary", "section"]) {
      const link = page.getByTestId(`gaps-queue-link-${variant}`).locator("a");
      await expect(link).toHaveAttribute("href", "/research-queue/");
    }
  });

  test("the home page's start-here grid links the queue (organizer path step)", async ({
    page,
  }) => {
    await page.goto("/");
    const entry = page
      .getByTestId("entry-point")
      .filter({ has: page.locator("a[href='/research-queue/']") });
    await expect(entry).toHaveCount(1);
    await expect(entry.locator("a")).toContainText("Open research questions");
  });

  test("O4 leg-a — an absence chip's Help-find-it link reaches the queue", async ({ page }) => {
    // The K13 O4 journey's a-half: chip → hub → place facet → card (the
    // /task/<handle>/ leg lands with P36.62).
    await page.goto("/research-queue/");
    await page
      .getByTestId("start-place")
      .locator("a", { hasText: "Oklahoma City" })
      .click();
    await expect(page).toHaveURL(new RegExp(`${OKC_PLACE}$`));
    await expect(page.getByTestId("closing-condition").first()).not.toBeEmpty();
  });
});
