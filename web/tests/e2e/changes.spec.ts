// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// P37.40 (R11-K13-CHG-01, J5, SIG-UI-072) — the `/changes/` surface e2e:
// the T1 page separates "SIG's records changed" from "the world changed"
// over the release diff, dated by release activation + world dates; the
// Atom feeds emit per place and per source and validate at the wire level;
// the empty/typed-absence paths stay honest.
import { test, expect } from "@playwright/test";

test.describe("/changes/ (T1)", () => {
  test("the two separated classes render with world vs belief dating", async ({ page }) => {
    await page.goto("/changes/");
    await expect(page.locator("h1")).toContainText("Changes");
    // the release pair + world-vs-belief split (SIG-UI-072)
    await expect(page.getByTestId("change-dates")).toBeVisible();
    await expect(page.getByTestId("as-of-world")).toContainText("2026-09-27 → 2026-10-15");
    await expect(page.getByTestId("as-of-belief")).toContainText("2026-09-27 → 2026-10-15");
    // both classes populated in the fixture build
    await expect(page.getByTestId("world-changed")).toBeVisible();
    await expect(page.getByTestId("world-list")).toBeVisible();
    await expect(page.getByTestId("sig-records-changed")).toBeVisible();
    await expect(page.getByTestId("sig-list")).toBeVisible();
    // a world-class row (the source_withdrawn removal / retired source) and a
    // sig-records row (added record) are both listed
    const worldRows = page.getByTestId("world-row");
    expect(await worldRows.count()).toBeGreaterThan(0);
    const sigRows = page.getByTestId("sig-row");
    expect(await sigRows.count()).toBeGreaterThan(0);
    // the disclosures + the full-diff link (release namespace, outside-base)
    await expect(page.getByTestId("disclosures")).toContainText("never compared");
    await expect(page.locator('a[href^="/r/p-"][href*="transparency/changes/index.json"]')).toBeVisible();
    // feed links resolve
    await expect(page.getByTestId("feed-all")).toHaveAttribute("href", "/changes/feeds/all.atom");
    await expect(page.getByTestId("feed-opml")).toHaveAttribute("href", "/changes/feeds.opml");
  });

  test("the page is zero-JS (T1 — no <script> in main content)", async ({ page }) => {
    await page.goto("/changes/");
    expect(await page.locator("main script").count()).toBe(0);
  });
});

test.describe("/changes/feeds/ directory", () => {
  test("lists the all feed, OPML, source feeds and the place index", async ({ page }) => {
    await page.goto("/changes/feeds/");
    await expect(page.getByTestId("feed-all-section")).toBeVisible();
    await expect(page.getByTestId("feed-sources-section")).toBeVisible();
    await expect(page.getByTestId("place-feed-index")).toBeVisible();
    const rows = page.getByTestId("feed-row");
    expect(await rows.count()).toBeGreaterThan(0);
  });
  test("the paginated place index resolves and its rows link emitted feeds", async ({ page }) => {
    await page.goto("/changes/feeds/place/page/1/");
    const table = page.getByTestId("place-feed-table");
    await expect(table).toBeVisible();
    const rows = page.getByTestId("feed-row");
    expect(await rows.count()).toBeGreaterThan(0);
  });
  test("the paginated source index resolves and its rows link emitted feeds", async ({ page }) => {
    await page.goto("/changes/feeds/source/page/1/");
    const table = page.getByTestId("source-feed-table");
    await expect(table).toBeVisible();
    const rows = page.getByTestId("feed-row");
    expect(await rows.count()).toBeGreaterThan(0);
  });
});

test.describe("the Atom feeds (T0 bytes)", () => {
  test("all.atom is a valid Atom doc with entries", async ({ request }) => {
    const res = await request.get("/changes/feeds/all.atom");
    expect(res.status()).toBe(200);
    expect(res.headers()["content-type"]).toContain("application/atom+xml");
    const body = await res.text();
    expect(body).toContain('<feed xmlns="http://www.w3.org/2005/Atom">');
    expect(body).toContain('<link rel="self" type="application/atom+xml" href="');
    expect(body).toContain("/changes/feeds/all.atom");
    expect(body).toContain("<entry>");
    expect(body).toContain("urn:sig:change:");
  });
  test("a place feed scopes to the place subtree", async ({ request }) => {
    const res = await request.get("/changes/feeds/place/usa/ok.atom");
    expect(res.status()).toBe(200);
    const body = await res.text();
    expect(body).toContain("usa/ok");
  });
  test("an empty place feed still emits a valid document", async ({ request }) => {
    const res = await request.get("/changes/feeds/place/fra.atom");
    expect(res.status()).toBe(200);
    const body = await res.text();
    expect(body).toContain("<feed");
    expect(body).toContain("</feed>");
  });
  test("a source feed carries the source's lifecycle + record rows", async ({ request }) => {
    const res = await request.get("/changes/feeds/source/demo_gated_registry.atom");
    expect(res.status()).toBe(200);
    const body = await res.text();
    expect(body).toContain("demo_gated_registry");
  });
  test("the OPML bundle outlines every feed", async ({ request }) => {
    const res = await request.get("/changes/feeds.opml");
    expect(res.status()).toBe(200);
    const body = await res.text();
    expect(body).toContain('<opml version="2.0">');
    expect(body).toContain('xmlUrl="');
    expect(body).toContain("/changes/feeds/place/usa/ok.atom");
    expect(body).toContain("/changes/feeds/source/");
  });
  test("an un-minted scope answers 404 (never a fabricated feed)", async ({ request }) => {
    const res = await request.get("/changes/feeds/place/no-such-place.atom");
    expect(res.status()).toBe(404);
  });
});
