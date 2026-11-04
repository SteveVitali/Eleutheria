// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// Render-path assertions for the P36.59 watch decision calendar (K7 WX-04a —
// `/watch/` index, per-place pages, facets, item pages, history, feeds
// directory) plus the legacy subscription endpoints and the evidence viewer
// (§39.5a/§39.6), run in the JS-enabled chromium project. The no-JS content
// baseline is in watch-evidence.nojs.spec.ts. The scoped evidence recommender
// is WX-05's surface (P37.31) — it is not asserted here.
import { test, expect } from "@playwright/test";

const OKC_HANDLE = "W-us-ok-oklahoma-city-4064000-renewal-c100-ab12";
const EXPIRY_HANDLE = "W-us-ok-expiry-rtcc-77cd";
const SOLICIT_HANDLE = "W-us-solicitation-n9-cd34";

test.describe("watch index — the decision calendar (P36.59, WX-04a)", () => {
  test("lists upcoming decisions in the declared 90-day window, one alert date each (SIG-WATCH-002)", async ({
    page,
  }) => {
    await page.goto("/watch/");
    const rows = page.getByTestId("watch-item");
    // The renewal at 2027-01-02 is beyond the 90-day window — not on the index;
    // the solicitation + grant + agenda items are.
    await expect(page.locator(`[data-handle='${OKC_HANDLE}']`)).toHaveCount(0);
    await expect(page.locator(`[data-handle='${SOLICIT_HANDLE}']`)).toBeVisible();
    // The solicitation row shows its stated certainty on the index.
    const sol = page.locator(`[data-handle='${SOLICIT_HANDLE}']`);
    await expect(sol.getByTestId("watch-certainty")).toHaveText("stated");
  });

  test("an upper_bound date never labels 'deadline' on any row (SIG-WATCH-002)", async ({ page }) => {
    // The expiry item (2026-11-30, upper_bound) lists on the state place page.
    await page.goto("/watch/place/usa/ok/");
    const expiry = page.locator(`[data-handle='${EXPIRY_HANDLE}']`);
    await expect(expiry).toBeVisible();
    await expect(expiry.getByTestId("watch-certainty")).toHaveText("latest possible date");
    await expect(expiry.getByTestId("watch-date")).not.toContainText("deadline — latest possible");
  });

  test("the coverage summary + facet nav + subscribe link render", async ({ page }) => {
    await page.goto("/watch/");
    await expect(page.getByTestId("watch-coverage-summary")).toContainText(/tenants|last checked/i);
    await expect(page.getByTestId("watch-place-link").first()).toBeVisible();
    await expect(page.getByTestId("watch-kind-link").first()).toBeVisible();
    await expect(page.getByTestId("watch-vendor-link").first()).toBeVisible();
    await expect(page.getByTestId("watch-tech-link").first()).toBeVisible();
    await expect(page.getByTestId("feeds-link")).toBeVisible();
    await expect(page.getByTestId("watch-pagination")).toBeVisible();
  });

  test("paginates past 50 rows (K9 §6.1)", async ({ page }) => {
    await page.goto("/watch/page/2/");
    await expect(page.getByTestId("watch-item").first()).toBeVisible();
  });
});

test.describe("per-place watch pages (SIG-WATCH-004/010)", () => {
  test("a place page covers the place and its children with the coverage statement", async ({
    page,
  }) => {
    await page.goto("/watch/place/usa/ok/");
    // The state page shows the city renewal, the county expiry and the state bill.
    await expect(page.locator(`[data-handle='${OKC_HANDLE}']`)).toBeVisible();
    await expect(page.locator(`[data-handle='${EXPIRY_HANDLE}']`)).toBeVisible();
    await expect(page.locator("[data-handle='W-us-ok-bill-hb-1400-55aa']")).toBeVisible();
    await expect(page.getByTestId("watch-coverage")).toContainText(/last checked|tenants/i);
    await expect(page.getByTestId("watch-history-link")).toBeVisible();
  });

  test("a monitored-but-empty place shows 'none found' WITH the coverage statement (SIG-WATCH-010)", async ({
    page,
  }) => {
    await page.goto("/watch/place/usa/ok/cleveland-county-40131/");
    const coverage = page.getByTestId("watch-coverage");
    await expect(coverage).toHaveAttribute("data-cause", "none_found");
    await expect(coverage).toContainText(/SIG checks|last checked/i);
    await expect(page.getByTestId("empty-state")).toContainText(/No upcoming decisions found/i);
    // Never calls a coverage gap a research gap.
    await expect(page.getByTestId("empty-state-missing")).not.toContainText("research gap");
  });

  test("a not-monitored place names that cause (SIG-WATCH-010)", async ({ page }) => {
    await page.goto("/watch/place/deu/");
    const coverage = page.getByTestId("watch-coverage");
    await expect(coverage).toHaveAttribute("data-cause", "not_monitored");
    await expect(page.getByTestId("empty-state")).toContainText(/does not yet (check|monitor)/i);
  });

  test("the unplaced bucket is labelled a data-quality list, not a place", async ({ page }) => {
    await page.goto("/watch/place/unplaced/");
    await expect(page.getByTestId("watch-coverage")).toContainText(/data-quality|not a jurisdiction/i);
    await expect(page.locator("[data-handle='W-unplaced-grant-hsgp-21zz']")).toBeVisible();
  });
});

test.describe("facet routes (one dimension each)", () => {
  test("kind, vendor and technology facets list their items", async ({ page }) => {
    await page.goto("/watch/kind/grant_period_end/");
    await expect(page.getByTestId("watch-item")).toHaveCount(50);
    await page.goto("/watch/kind/grant_period_end/page/2/");
    await expect(page.getByTestId("watch-item")).toHaveCount(3);

    await page.goto("/watch/vendor/flock_safety/");
    await expect(page.locator(`[data-handle='${OKC_HANDLE}']`)).toBeVisible();

    await page.goto("/watch/technology/alpr/");
    await expect(page.locator(`[data-handle='${OKC_HANDLE}']`)).toBeVisible();
    await expect(page.locator(`[data-handle='${SOLICIT_HANDLE}']`)).toBeVisible();
  });
});

test.describe("the item page (SIG-WATCH-002/003)", () => {
  test("shows the one alert date with kind + certainty; an upper_bound is never a deadline", async ({
    page,
  }) => {
    await page.goto(`/watch/item/${EXPIRY_HANDLE}/`);
    await expect(page.getByTestId("item-date")).toContainText("2026-11-30");
    await expect(page.getByTestId("item-certainty")).toHaveText("latest possible date");
    // The upper-bound item explains the bound — it never calls itself a deadline.
    await expect(page.getByTestId("item-date")).toContainText(/latest possible date|real deadline may be earlier/i);
    await expect(page.getByTestId("item-timeline").first()).toBeVisible();
    await expect(page.getByTestId("item-what-you-can-do")).toBeVisible();
    await expect(page.getByTestId("item-tasks")).toBeVisible();
  });

  test("links the supporting claim and the upstream document (SIG-WATCH-003)", async ({ page }) => {
    await page.goto(`/watch/item/${SOLICIT_HANDLE}/`);
    const evidence = page.getByTestId("item-evidence").first();
    await expect(evidence).toBeVisible();
    await expect(evidence).toContainText("response_deadline");
    // The upstream document is a real link (sam.gov).
    const upstream = page.getByTestId("upstream-link").first();
    await expect(upstream).toBeVisible();
    await expect(upstream).toHaveAttribute("href", /sam\.gov/);
  });

  test("the renewal item carries the derivation (auto-renew + notice window)", async ({ page }) => {
    await page.goto(`/watch/item/${OKC_HANDLE}/`);
    await expect(page.getByTestId("item-termination")).toContainText("2027-04-02");
    await expect(page.getByTestId("item-termination")).toContainText("auto-renews");
    await expect(page.getByTestId("item-termination")).toContainText("90");
    await expect(page.getByTestId("item-certainty")).toHaveText("derived");
    // Contested — the marker rides the item everywhere it appears.
    await expect(page.getByTestId("watch-item-page")).toHaveAttribute("data-contested", "true");
  });
});

test.describe("history + feeds (P36.59)", () => {
  test("the per-place history lists past items", async ({ page }) => {
    await page.goto("/watch/history/usa/ok/");
    await expect(page.locator("[data-handle='W-us-ok-bill-hb-1400-55aa']")).toBeVisible();
    await expect(page.locator(`[data-handle='${OKC_HANDLE}']`)).toHaveCount(0);
  });

  test("the feeds directory lists the emitted subscriptions + the no-email-list rule", async ({
    page,
  }) => {
    await page.goto("/watch/feeds/");
    await expect(page.getByTestId("feed-row").first()).toBeVisible();
    await expect(page.getByTestId("feed-ics").first()).toBeVisible();
    await expect(page.getByTestId("feed-rss").first()).toBeVisible();
    await expect(page.locator("main")).toContainText(/no email list|no accounts/i);
  });
});

test.describe("the legacy subscription endpoints (SIG-UI-027)", () => {
  test("iCal + RSS still emit keyed on the derived decision date", async ({ request }) => {
    const ics = await request.get("/watch/oklahoma-city.ics");
    expect(ics.ok()).toBeTruthy();
    expect(ics.headers()["content-type"]).toContain("text/calendar");
    const icsBody = await ics.text();
    expect(icsBody).toContain("BEGIN:VCALENDAR");
    expect(icsBody).toContain("DTSTART;VALUE=DATE:20270102");
    expect(icsBody).not.toContain("DTSTART;VALUE=DATE:20270402");

    const rss = await request.get("/watch/oklahoma-city.xml");
    expect(rss.ok()).toBeTruthy();
    const rssBody = await rss.text();
    expect(rssBody).toContain('<rss version="2.0">');
    expect(rssBody).toContain("Decision deadline 2027-01-02");
  });

  test("the citation export still emits plain text (SIG-UI-027c)", async ({ request }) => {
    const txt = await request.get("/watch/citations.txt");
    expect(txt.ok()).toBeTruthy();
    expect(txt.headers()["content-type"]).toContain("text/plain");
    const body = await txt.text();
    expect(body).toContain("directness, recency, and dispute status only");
    expect(body).toMatch(/As of \d{4}-\d{2}-\d{2}/);
  });
});

test.describe("the dossier 'Next decisions' block (SIG-WATCH-009)", () => {
  test("a keyed dossier lists its place's items and links the place watch page", async ({
    page,
  }) => {
    await page.goto("/dossier/usa/ok/oklahoma-city-4064000/");
    const block = page.getByTestId("next-decisions");
    await expect(block.getByTestId("next-decision-item").first()).toBeVisible();
    await expect(page.getByTestId("watch-place-link")).toHaveAttribute(
      "href",
      /\/watch\/place\/usa\/ok\/oklahoma-city-4064000\//,
    );
  });
});

test.describe("contested values are marked at every appearance (SIG-UI-008)", () => {
  test("the contested item carries the marker on the place list, the item page, and the viewer", async ({
    page,
  }) => {
    await page.goto("/watch/place/usa/ok/");
    await expect(
      page.locator(`[data-testid='watch-item'][data-handle='${OKC_HANDLE}'] [data-testid='contested-marker']`),
    ).toBeVisible();
    await page.goto(`/watch/item/${OKC_HANDLE}/`);
    await expect(page.getByTestId("contested-marker").first()).toBeVisible();
    // The conflicting-claims view.
    await page.goto("/evidence/claim/active-device-count/");
    await expect(page.getByTestId("evidence-view")).toHaveAttribute("data-contested", "true");
    await expect(page.getByTestId("contested-marker").first()).toBeVisible();
  });
});

test.describe("evidence viewer (§39.6) — agentic", () => {
  test("renders the document with the supporting span highlighted at its locator (SIG-UI-028)", async ({
    page,
  }) => {
    await page.goto("/evidence/claim/active-device-count/");
    await expect(page.getByTestId("highlighted-span")).toHaveText("forty-two (42)");
    await expect(page.getByTestId("extraction-method")).toBeVisible();
    await expect(page.getByTestId("extraction-version")).not.toBeEmpty();
    await expect(page.getByTestId("review-status")).not.toBeEmpty();
    await expect(page.getByTestId("capture-digest")).toContainText("sha256:");
    await expect(page.getByTestId("acquisition-method")).not.toBeEmpty();
    await expect(page.getByTestId("capture-date")).not.toBeEmpty();
    await expect(page.getByTestId("conflicting-claim")).toHaveCount(2);
    await expect(page.getByTestId("history-event").first()).toBeVisible();
  });

  test("diffs two captures of the same artifact, field by field (SIG-UI-029)", async ({ page }) => {
    await page.goto("/evidence/claim/active-device-count/");
    const diff = page.getByTestId("capture-diff");
    await expect(diff).toBeVisible();
    await expect(diff.locator("[data-testid='diff-field'][data-field='active_device_count']")).toHaveAttribute(
      "data-changed",
      "true",
    );
    await expect(diff.locator("[data-testid='diff-field'][data-field='retention_days']")).toHaveAttribute(
      "data-changed",
      "false",
    );
  });

  test("renders a sealed capture metadata-only with an explanation (SIG-UI-030)", async ({ page }) => {
    await page.goto("/evidence/claim/operator-roster-size/");
    const view = page.getByTestId("evidence-view");
    await expect(view).toHaveAttribute("data-sealed", "true");
    await expect(page.getByTestId("sealed-notice")).toBeVisible();
    await expect(page.getByTestId("sealed-reason")).toContainText(/withheld|PII|sealed/i);
    await expect(page.getByTestId("document-text")).toHaveCount(0);
    await expect(page.getByTestId("highlighted-span")).toHaveCount(0);
    await expect(page.getByTestId("capture-digest")).toContainText("sha256:");
  });
});
