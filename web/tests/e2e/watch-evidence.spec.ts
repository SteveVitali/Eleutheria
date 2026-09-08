// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// Render-path assertions for the P15.4 renewal watch (§39.5), evidence recommender
// (§39.5a), and evidence viewer (§39.6), run in the JS-enabled chromium project. The
// no-JS content baseline is in watch-evidence.nojs.spec.ts.
import { test, expect } from "@playwright/test";

test.describe("renewal watch (§39.5)", () => {
  test("every alert keys on next_decision_date, not the expiry (SIG-UI-026, SIG-UI-014b)", async ({
    page,
  }) => {
    await page.goto("/watch/");
    const auto = page.locator("[data-testid='watch-item'][data-contract-id='contract:okcpd-alpr']");
    // Appendix-D auto-renewal: decision 2027-01-02, expiry 2027-04-02 — they differ.
    await expect(auto).toHaveAttribute("data-decision-date", "2027-01-02");
    await expect(auto).toHaveAttribute("data-expiry-date", "2027-04-02");
    // A non-auto-renewing contract's decision date IS its expiry.
    const nonAuto = page.locator("[data-testid='watch-item'][data-contract-id='contract:okcpd-rtcc']");
    await expect(nonAuto).toHaveAttribute("data-decision-date", "2026-11-30");
    await expect(nonAuto).toHaveAttribute("data-expiry-date", "2026-11-30");
  });

  test("subscriptions are offered by jurisdiction as iCal + RSS (SIG-UI-027)", async ({
    page,
    request,
  }) => {
    await page.goto("/watch/");
    await expect(page.locator("[data-testid='ical-link'][data-jurisdiction='Oklahoma City']")).toBeVisible();
    await expect(page.locator("[data-testid='rss-link'][data-jurisdiction='Tulsa']")).toBeVisible();

    // The iCal feed is valid and keyed on the decision date (2027-01-02), not expiry.
    const ics = await request.get("/watch/oklahoma-city.ics");
    expect(ics.ok()).toBeTruthy();
    expect(ics.headers()["content-type"]).toContain("text/calendar");
    const icsBody = await ics.text();
    expect(icsBody).toContain("BEGIN:VCALENDAR");
    expect(icsBody).toContain("DTSTART;VALUE=DATE:20270102");
    expect(icsBody).not.toContain("DTSTART;VALUE=DATE:20270402");

    // The RSS feed is valid and keyed on the same decision date.
    const rss = await request.get("/watch/oklahoma-city.xml");
    expect(rss.ok()).toBeTruthy();
    const rssBody = await rss.text();
    expect(rssBody).toContain('<rss version="2.0">');
    expect(rssBody).toContain("Decision deadline 2027-01-02");
  });
});

test.describe("evidence recommender (§39.5a)", () => {
  test("ranks by directness/recency/dispute only; excludes a non-probative artifact (SIG-UI-027a)", async ({
    page,
  }) => {
    await page.goto("/watch/");
    const arts = page.getByTestId("recommended-artifact");
    await expect(arts.first()).toBeVisible();
    // The D6 vendor brochure is non-probative → never recommended.
    await expect(page.locator("[data-testid='recommended-artifact'][data-artifact-id='brochure:flock-marketing']")).toHaveCount(0);
    // The executed contract (D1) ranks first.
    await expect(page.locator("[data-testid='recommended-artifact'][data-rank='1']")).toHaveAttribute(
      "data-artifact-id",
      "contract:okcpd-alpr",
    );
  });

  test("states the neutrality guarantee; the score uses no forbidden axis (SIG-UI-027b)", async ({
    page,
  }) => {
    await page.goto("/watch/");
    await expect(page.getByTestId("neutrality-note")).toContainText(/persuasiveness|sentiment|vote/i);
    // No score-breakdown chip is a persuasiveness/sentiment/vote axis.
    const axes = await page
      .locator("[data-testid='score-breakdown'] li")
      .evaluateAll((els) => els.map((e) => e.getAttribute("data-axis")));
    for (const a of axes) {
      expect(a).not.toMatch(/persuas|sentiment|vote|tone|framing|emotional/i);
    }
  });

  test("output is exportable as a citation list with permalinks + as-of dates (SIG-UI-027c)", async ({
    page,
    request,
  }) => {
    await page.goto("/watch/");
    await expect(page.getByTestId("citation-list").getByTestId("citation-entry").first()).toBeVisible();
    const txt = await request.get("/watch/citations.txt");
    expect(txt.ok()).toBeTruthy();
    expect(txt.headers()["content-type"]).toContain("text/plain");
    const body = await txt.text();
    expect(body).toContain("directness, recency, and dispute status only");
    expect(body).toMatch(/As of \d{4}-\d{2}-\d{2}/);
    expect(body).toContain("https://sig.example/evidence/");
  });
});

test.describe("evidence viewer (§39.6) — agentic", () => {
  test("renders the document with the supporting span highlighted at its locator (SIG-UI-028)", async ({
    page,
  }) => {
    await page.goto("/evidence/active-device-count/");
    await expect(page.getByTestId("highlighted-span")).toHaveText("forty-two (42)");
    // The full provenance chain is present.
    await expect(page.getByTestId("extraction-method")).toBeVisible();
    await expect(page.getByTestId("extraction-version")).not.toBeEmpty();
    await expect(page.getByTestId("review-status")).not.toBeEmpty();
    await expect(page.getByTestId("capture-digest")).toContainText("sha256:");
    await expect(page.getByTestId("acquisition-method")).not.toBeEmpty();
    await expect(page.getByTestId("capture-date")).not.toBeEmpty();
    // The conflicting claims and the full history are shown.
    await expect(page.getByTestId("conflicting-claim")).toHaveCount(2);
    await expect(page.getByTestId("history-event").first()).toBeVisible();
  });

  test("diffs two captures of the same artifact, field by field (SIG-UI-029)", async ({ page }) => {
    await page.goto("/evidence/active-device-count/");
    const diff = page.getByTestId("capture-diff");
    await expect(diff).toBeVisible();
    // active_device_count changed 40 → 38; retention_days did not.
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
    await page.goto("/evidence/operator-roster-size/");
    const view = page.getByTestId("evidence-view");
    await expect(view).toHaveAttribute("data-sealed", "true");
    await expect(page.getByTestId("sealed-notice")).toBeVisible();
    await expect(page.getByTestId("sealed-reason")).toContainText(/withheld|PII|sealed/i);
    // No bytes, no highlighted span for a sealed capture.
    await expect(page.getByTestId("document-text")).toHaveCount(0);
    await expect(page.getByTestId("highlighted-span")).toHaveCount(0);
    // But the digest, date, and acquisition metadata are still public.
    await expect(page.getByTestId("capture-digest")).toContainText("sha256:");
  });
});

test.describe("contested values are marked at every appearance (SIG-UI-008, AC6)", () => {
  test("the contested subject carries the marker on the watch, the recommender, the export, and the viewer", async ({
    page,
  }) => {
    // Watch list.
    await page.goto("/watch/");
    await expect(
      page.locator("[data-testid='watch-item'][data-contract-id='contract:okcpd-alpr'] [data-testid='contested-marker']"),
    ).toBeVisible();
    // Recommender entry + citation-list export entry.
    await expect(
      page.locator("[data-testid='recommended-artifact'][data-artifact-id='contract:okcpd-alpr'] [data-testid='contested-marker']"),
    ).toBeVisible();
    await expect(
      page.locator("[data-testid='citation-entry'][data-artifact-id='contract:okcpd-alpr'] [data-testid='contested-marker']"),
    ).toBeVisible();
    // The conflicting-claims view.
    await page.goto("/evidence/active-device-count/");
    await expect(page.getByTestId("evidence-view")).toHaveAttribute("data-contested", "true");
    await expect(page.getByTestId("contested-marker").first()).toBeVisible();
  });
});
