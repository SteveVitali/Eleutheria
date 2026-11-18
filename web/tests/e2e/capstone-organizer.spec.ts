// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// P37.68c (R11-K13-CAP-01, split c — K13 §8 capstone journeys O1–O4):
// the organizer-journey battery walked COLD from `/`, once per
// {390, 1440 px} x {JS on, JS off} project cell of
// playwright.capstone-organizer.config.ts. Two audiences run the same file:
//   - fixtures: `npx playwright test -c playwright.capstone-organizer.config.ts`
//     previews the built dist (the fixture-verified layer);
//   - the promoted release: `SIG_CAPSTONE_BASE_URL=<origin> npx playwright
//     test -c playwright.capstone-organizer.config.ts` — the deferred live
//     leg (D-P37.68c-1, OM-19 `live_verification=true`).
// Every journey resolves its targets from the served site itself (the A–Z
// directory supplies the place dossiers, the dossier's own blocks the
// sites/next-decisions links, the gap→task links and the queue the
// research tasks) — nothing fixture-specific is hard-coded. Recorded
// AGENT-VERIFIED (P4 honesty — never user research); the operator's
// walkthrough is its own recorded act (OP-22, "operator walkthrough
// (maintainer, not independent)"), never simulated here.
//
// Honest gates carried in-line:
//   - O1's "named agencies" reading rides the release's own
//     placement/publication state (I8 placement, D-K2-1 organisation
//     publication — K13 §4.2): where the release emits no evidenced
//     "who runs" edges the typed absence is the pass state, never a
//     smoothed-over figure.
//   - O3's "licence and attribution per compartment" reading rides
//     ACT-07 (the attribution re-export — K13 §7.4 orders ACT-07 before
//     any download link); the committed surface is asserted, the
//     release's own attribution is the live leg's.
//   - O4's "where to send results" is the operator-named channel
//     (D-K11-4 — settled); the page never invents one.

import { expect, test } from "@playwright/test";

/**
 * Resolve a place dossier through the A–Z directory — the named no-JS
 * place-lookup equivalent that exists on every published build. The
 * `sortName` needle (e.g. "harris") matches the index row's
 * `data-sort-name`; `preferPrefix` favours the canonical slug family so
 * the battery picks the place dossier over a legacy subject dossier.
 */
async function resolveDossierViaAZ(
  request: import("@playwright/test").APIRequestContext,
  letter: string,
  sortName: string,
  preferPrefix?: string,
): Promise<string> {
  const res = await request.get(`/dossier/a-z/${letter}/`);
  expect(res.status()).toBe(200);
  const html = await res.text();
  const items = [
    ...html.matchAll(
      /data-testid="dossier-index-item"[^>]*data-sort-name="([^"]*)"[^>]*>(.*?)<\/li>/gs,
    ),
  ];
  const hrefs = items
    .filter((m) => m[1]!.toLowerCase().startsWith(sortName))
    .flatMap((m) =>
      [...(m[2] ?? "").matchAll(/href="(\/dossier\/[^"]+\/)"/g)].map(
        (h) => h[1]!,
      ),
    )
    .filter(
      (h) =>
        !h.startsWith("/dossier/a-z/") &&
        !h.startsWith("/dossier/figures/") &&
        !h.includes("/print/"),
    );
  const href =
    (preferPrefix && hrefs.find((h) => h.startsWith(preferPrefix))) ??
    hrefs[0] ??
    null;
  expect(
    href,
    `a dossier row matching "${sortName}" must exist on /dossier/a-z/${letter}/`,
  ).toBeTruthy();
  return href!;
}

/**
 * Walk the A–Z letter pages until a dossier page carrying a gap→task
 * link surfaces — the absence-chip leg of O4 ("act on a gap"). The scan
 * is bounded (`maxItems` dossier fetches) and returns the first page
 * that resolves one of its "What we don't know" gaps to an open task;
 * a release whose corpus carries no matching gap surfaces its queue
 * fallback instead (the caller checks `/research-queue/`).
 */
async function resolveDossierWithGapTask(
  request: import("@playwright/test").APIRequestContext,
  maxItems = 60,
): Promise<{ dossierHref: string; taskHref: string } | null> {
  const letters = await request.get("/dossier/a-z/");
  expect(letters.status()).toBe(200);
  const letterHrefs = [
    ...new Set(
      [
        ...(await letters.text()).matchAll(/href="(\/dossier\/a-z\/[a-z]\/)"/g),
      ].map((m) => m[1]!),
    ),
  ];
  let seen = 0;
  for (const letter of letterHrefs) {
    const res = await request.get(letter);
    if (res.status() !== 200) continue;
    const dossierHrefs = [
      ...new Set(
        [...(await res.text()).matchAll(/href="(\/dossier\/[^"]+\/)"/g)]
          .map((m) => m[1]!)
          .filter(
            (h) =>
              !h.startsWith("/dossier/a-z/") &&
              !h.startsWith("/dossier/figures/") &&
              !h.startsWith("/dossier/unplaced/") &&
              !h.includes("/print/") &&
              !h.includes("/sites/") &&
              !h.includes("/sources/") &&
              !h.includes("/downloads/"),
          ),
      ),
    ];
    for (const href of dossierHrefs) {
      if (seen++ >= maxItems) return null;
      const doc = await request.get(href);
      if (doc.status() !== 200) continue;
      const html = await doc.text();
      const taskHref =
        /href="(\/task\/[^"]+\/)"[^>]*data-testid="gap-task-[^"]*"|data-testid="gap-task-[^"]*"[^>]*href="(\/task\/[^"]+\/)"/.exec(
          html,
        );
      const href2 = taskHref?.[1] ?? taskHref?.[2];
      if (href2) return { dossierHref: href, taskHref: href2 };
    }
  }
  return null;
}

test.describe("CAP-O1 — who runs what in my county or city (≤ 3 min)", () => {
  test("dossier → figures, sites list, organizations: named or typed absence, each sourced", async ({
    page,
    request,
  }) => {
    // O1's K13 anchor is a county dossier — the A–Z directory supplies
    // the slug (the fixture's O1 anchor is Harris County; any county or
    // city dossier the release emits under "harris" serves the same
    // walk, and a missing row fails loud rather than silently picking).
    const county = await resolveDossierViaAZ(
      request,
      "h",
      "harris",
      "/dossier/usa/",
    );
    await page.goto(county);
    await expect(page.locator("h1").first()).toBeVisible();

    // Counts — the header strip's record figure and Figure 1's caption
    // carry unit, denominator and the release stamp.
    await expect(page.getByTestId("dossier-header-strip")).toBeVisible();
    await expect(page.getByTestId("strip-records")).toBeVisible();
    const caption = page.getByTestId("fig1-caption").first();
    await expect(caption).toBeVisible();
    expect((await caption.textContent()) ?? "").toMatch(/published records/);
    await expect(page.getByTestId("release-stamp").first()).toBeAttached();
    await expect(page.getByTestId("page-stamp")).toBeVisible();

    // Technology classes — "What is deployed" names the record class
    // (a value) or the typed no-record state; never a silent blank.
    const deployed = page.locator(
      "[data-testid='dossier-section'][data-section-id='what_is_deployed']",
    );
    await expect(deployed).toBeVisible();
    const deployedText = (await deployed.textContent()) ?? "";
    expect(
      deployedText.includes("Record class") ||
        deployedText.includes("No record in SIG"),
      "the deployed section names the record class or its typed absence",
    ).toBeTruthy();

    // "Who runs and supplies it" (the fig-2 network slot) — named
    // agencies where the release emits evidenced edges, else the typed
    // absence with its overview link (never a dead figure).
    const whoRuns = page.locator(
      "[data-testid='network-figure-slot'][data-figure='fig-2']",
    );
    await expect(whoRuns).toBeAttached();
    const empty = whoRuns.locator("[data-testid='empty-state']");
    if ((await empty.count()) > 0) {
      const cta = empty.locator("[data-testid='empty-state-cta']");
      const ctaHref = await cta.getAttribute("href");
      expect(
        ctaHref,
        "the typed absence links its overview equivalent",
      ).toBeTruthy();
      expect((await request.get(ctaHref!)).status()).toBe(200);
    } else {
      // The figure rendered — its nodes must be named or a typed note.
      expect((await whoRuns.textContent())?.trim().length ?? 0).toBeGreaterThan(
        0,
      );
    }

    // The sites list — the no-JS per-record inventory the dossier's own
    // figure links ("Sites list →").
    const sitesHref = /href="(\/dossier\/[^"]*\/sites\/)"/.exec(
      await (await request.get(county)).text(),
    )?.[1];
    expect(sitesHref, "the dossier links its sites list").toBeTruthy();
    await page.goto(sitesHref!);
    await expect(page.getByTestId("sites-table").first()).toBeVisible();
    expect(await page.getByTestId("site-row").count()).toBeGreaterThan(0);
  });
});

test.describe("CAP-O2 — who decides and when; subscribe (≤ 2 min)", () => {
  test("dossier Next decisions → watch place page → the .ics feed validates (even at 0 items)", async ({
    page,
    request,
  }) => {
    const county = await resolveDossierViaAZ(
      request,
      "h",
      "harris",
      "/dossier/usa/",
    );
    await page.goto(county);

    // Next decisions — an item naming the approving body and its next
    // date, or the typed absence; never a guessed calendar.
    const nd = page.getByTestId("next-decisions");
    await expect(nd).toBeVisible();
    const items = nd.locator("[data-testid='next-decision-item']");
    const none = nd.locator("[data-testid='next-decisions-none']");
    if ((await items.count()) > 0) {
      const first = items.first();
      // The item names its deciding body and carries a <time> date.
      await expect(first.locator("time").first()).toBeAttached();
      expect(((await first.textContent()) ?? "").trim().length).toBeGreaterThan(
        0,
      );
    } else {
      await expect(none).toBeVisible();
    }

    // The place's watch page — from the dossier's own "Watch upcoming
    // decisions →" link where the release emits one.
    const watchLink = nd.locator("[data-testid='watch-place-link']");
    if ((await watchLink.count()) > 0) {
      const watchHref = await watchLink.getAttribute("href");
      expect(watchHref).toBeTruthy();
      await page.goto(watchHref!);
    } else {
      // No place page — the generic watch index is the named surface.
      await page.goto("/watch/");
    }
    await expect(page).toHaveURL(/\/watch\//);
    const watchItems = page.locator("[data-testid='watch-item']");
    const watchEmpty = page.locator("[data-testid='empty-state']");
    expect(
      (await watchItems.count()) + (await watchEmpty.count()),
      "the watch page shows items or a typed empty state",
    ).toBeGreaterThan(0);
    if ((await watchItems.count()) > 0) {
      await expect(
        watchItems.first().locator("[data-testid='watch-date']"),
      ).toBeVisible();
      await expect(
        watchItems.first().locator("[data-testid='watch-certainty']"),
      ).toBeVisible();
    }

    // Subscribe — the .ics exists even with 0 items and validates its
    // RFC 5545 skeleton (VCALENDAR + VERSION:2.0 + PRODID).
    const ics = page.locator("[data-testid='watch-subscribe-ics']");
    await expect(ics).toBeVisible();
    const icsHref = await ics.getAttribute("href");
    expect(icsHref).toBeTruthy();
    const icsRes = await request.get(icsHref!);
    expect(icsRes.status()).toBe(200);
    const icsText = await icsRes.text();
    expect(icsText).toContain("BEGIN:VCALENDAR");
    expect(icsText).toContain("VERSION:2.0");
    expect(icsText).toContain("PRODID");
    expect(icsText).toContain("END:VCALENDAR");
  });
});

test.describe("CAP-O3 — a local list without the map (≤ 2 min)", () => {
  test("dossier → sites list: no-JS table, CSV download, licence + attribution per compartment", async ({
    page,
    request,
  }) => {
    // The O3 walk needs a sites list that carries compartments — the
    // A–Z supplies the city dossier (the fixture's multi-compartment
    // example is Oklahoma City's; a release emitting none fails loud).
    const city = await resolveDossierViaAZ(
      request,
      "o",
      "oklahoma city",
      "/dossier/usa/",
    );
    const dossierHtml = await (await request.get(city)).text();
    const sitesHref = /href="(\/dossier\/[^"]*\/sites\/)"/.exec(
      dossierHtml,
    )?.[1];
    expect(sitesHref, "the dossier links its sites list").toBeTruthy();

    await page.goto(sitesHref!);
    // The no-JS list — server-rendered rows at the published precision.
    await expect(page.getByTestId("sites-lede")).toBeVisible();
    await expect(page.getByTestId("sites-count")).toBeVisible();
    await expect(page.getByTestId("sites-table").first()).toBeVisible();
    expect(await page.getByTestId("site-row").count()).toBeGreaterThan(0);
    // Every row states its coordinate precision — published precision
    // only (coords or a typed no-coords cell, never raw geometry).
    for (const row of await page.getByTestId("site-row").all()) {
      const precision = await row
        .locator("[data-testid='site-coords'], [data-testid='site-no-coords']")
        .count();
      expect(
        precision,
        "every site row carries a published-precision cell",
      ).toBeGreaterThan(0);
    }

    // Licence + attribution per compartment — each rendered compartment
    // group names its compartment and licence line (or "not stated").
    const compartments = page.getByTestId("sites-compartment");
    const compCount = await compartments.count();
    expect(
      compCount,
      "the sites list groups by licence compartment",
    ).toBeGreaterThan(0);
    for (const comp of await compartments.all()) {
      await expect(
        comp.locator("[data-testid='sites-compartment-name']"),
      ).toBeVisible();
      const licence = comp.locator("[data-testid='sites-licence-line']");
      await expect(licence).toBeVisible();
      expect((await licence.textContent()) ?? "").toMatch(
        /Licence: (.+|not stated)/,
      );
    }

    // Download this view — the CSV twin carries the same compartment +
    // licence columns and its licence comment header.
    const csv = page.locator("[data-testid='sites-csv']");
    await expect(csv).toBeVisible();
    const csvHref = await csv.getAttribute("href");
    expect(csvHref).toBeTruthy();
    const csvRes = await request.get(csvHref!);
    expect(csvRes.status()).toBe(200);
    const csvText = await csvRes.text();
    expect(csvText).toContain("# licence:");
    expect(csvText).toMatch(/compartment.*licence|licence.*compartment/);
  });
});

test.describe("CAP-O4 — act on a gap (≤ 3 min)", () => {
  test("absence chip → /task/<handle>/: plain-language task, closing condition, request template, the named channel", async ({
    page,
    request,
  }) => {
    // The absence chip's resolution is the dossier gap→task link — walk
    // the A–Z until a dossier carrying one surfaces. If no dossier in
    // the bounded scan carries a task-bearing gap, the research queue
    // is the named fallback surface (O4's intent — act on a gap).
    const hit = await resolveDossierWithGapTask(request);
    if (hit) {
      await page.goto(hit.dossierHref);
      const gapTask = page.locator("[data-testid^='gap-task-']").first();
      await expect(gapTask).toBeVisible();
      await gapTask.click();
      await expect(page).toHaveURL(/\/task\/.+\//);
    } else {
      await page.goto("/research-queue/");
      const card = page.locator("[data-testid='task-card']").first();
      await expect(card).toBeVisible();
      const link = card.locator("[data-testid='task-link']");
      await link.click();
      await expect(page).toHaveURL(/\/task\/.+\//);
    }

    // The task page contract (K11 §5.3): plain-language task, closing
    // condition, and the operator-named reporting channel — never an
    // invented address.
    await expect(page.getByTestId("task-page")).toBeVisible();
    await expect(page.getByTestId("task-handle")).toBeVisible();
    const why = page.locator(
      "[data-testid='task-why'], [data-testid='task-evidence-sought']",
    );
    await expect(why.first()).toBeVisible();
    const closing = page.getByTestId("task-closing");
    await expect(closing).toBeVisible();
    expect(((await closing.textContent()) ?? "").trim().length).toBeGreaterThan(
      0,
    );
    await expect(page.getByTestId("task-how-to-act")).toBeVisible();
    // "SIG sends nothing; you file it yourself" — the queue never
    // claims to file on the reader's behalf.
    expect(
      (await page.getByTestId("task-how-to-act").textContent()) ?? "",
    ).toMatch(/SIG sends nothing|you file it yourself/);
    // Where to send results — the operator-named channel (D-K11-4).
    await expect(page.getByTestId("task-report").first()).toBeVisible();
    await expect(page.getByTestId("task-report-link").first()).toBeVisible();

    // The request template — where the landed task carries no draft,
    // the queue's DRAFT badge picks a draft-bearing task for the
    // template leg; where none exists at all the typed absence stands
    // (a task page never invents a draft).
    const pageHtml = await page.content();
    if (!pageHtml.includes('data-testid="draft-body"')) {
      const queue = await (await request.get("/research-queue/")).text();
      const draftHref =
        /href="(\/task\/[^"]+#records-request-draft)"/.exec(queue)?.[1] ?? null;
      if (draftHref) {
        await page.goto(draftHref.split("#")[0]!);
        await expect(page.getByTestId("task-page")).toBeVisible();
      }
    }
    const draft = page.getByTestId("task-draft").first();
    await expect(draft).toBeVisible();
    const body = page.locator("[data-testid='draft-body']");
    if ((await body.count()) > 0) {
      expect(((await body.textContent()) ?? "").trim().length).toBeGreaterThan(
        0,
      );
      await expect(page.getByTestId("draft-never-sent")).toBeVisible();
      const dl = page.getByTestId("draft-download");
      if ((await dl.count()) > 0) {
        const dlHref = await dl.getAttribute("href");
        expect(dlHref).toBeTruthy();
        expect((await request.get(dlHref!)).status()).toBe(200);
      }
    }
  });
});
