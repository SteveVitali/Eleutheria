// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// P37.68b (R11-K13-CAP-01, split b — K13 §8 capstone journeys J1–J5):
// the journalist-journey battery walked COLD from `/`, once per
// {390, 1440 px} x {JS on, JS off} project cell of
// playwright.capstone-journalist.config.ts. Two audiences run the same file:
//   - fixtures: `npx playwright test -c playwright.capstone-journalist.config.ts`
//     previews the built dist (the fixture-verified layer);
//   - the promoted release: `SIG_CAPSTONE_BASE_URL=<origin> npx playwright
//     test -c playwright.capstone-journalist.config.ts` — the deferred live
//     leg (D-P37.68b-1, OM-19 `live_verification=true`).
// Every journey resolves its targets from the served site itself (the A–Z
// directory supplies the place dossiers, the dossier's own explore bar the
// explore URL, the disagreements index the contested place, the downloads
// page the rows link) — nothing fixture-specific is hard-coded. Recorded
// AGENT-VERIFIED (P4 honesty — never user research); the operator's
// walkthrough is its own recorded act (OP-22, "operator walkthrough
// (maintainer, not independent)"), never simulated here.
//
// Honest gates carried in-line:
//   - J4's durable `/s/<pub>/` pinned-URL half rides ACT-24 (HG-11) — the
//     interim cite contract is checked here; the identical-bytes-after-
//     next-release leg belongs to the gated live legs (K13 §7.4).
//   - J5's "real >= 2-release diff" (CF-13) is the gated live leg's job;
//     the fixture build ships a synthetic release pair, which is exactly
//     what this layer is allowed to prove.

import { expect, test } from "@playwright/test";

const jsOn = (): boolean => test.info().project.use.javaScriptEnabled !== false;

/**
 * Resolve a place dossier through the A–Z directory — the named no-JS
 * place-lookup equivalent that exists on every published build. The
 * `sortName` needle (e.g. "texas") matches the index row's
 * `data-sort-name`, so the battery follows whatever dossier slug the
 * served corpus actually publishes.
 */
async function resolveDossierViaAZ(
  request: import("@playwright/test").APIRequestContext,
  letter: string,
  sortName: string,
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
  const href = hrefs[0] ?? null;
  expect(
    href,
    `a dossier row matching "${sortName}" must exist on /dossier/a-z/${letter}/`,
  ).toBeTruthy();
  return href!;
}

test.describe("CAP-J1 — defend a headline figure (≤ 5 min)", () => {
  test("figure → breakdown → rows download: unit, denominator, 'not a census', as-of, release id, evidence ≤ 2 actions", async ({
    page,
    request,
  }) => {
    // J1 starts from any figure; the battery picks the place dossier the
    // A–Z directory itself offers (release-agnostic — never a hard-coded slug).
    const tx = await resolveDossierViaAZ(request, "t", "texas");
    await page.goto(tx);

    // The headline figure — a rendered sig-figure with its caption.
    const caption = page.locator("[data-testid='fig1-caption']").first();
    await expect(caption).toBeVisible();
    const captionText = (await caption.textContent()) ?? "";
    // Unit + denominator + the "not a census" wording (never a bare count).
    expect(captionText).toMatch(/published records/);
    expect(captionText.toLowerCase()).toContain("not a census");
    // The release id rides the caption — the figure's own stamp.
    await expect(caption.locator(".sig-fig1__release").first()).toContainText(
      /Release/,
    );

    // Breakdown: the figure names its breakdown anchor and the anchor exists.
    const breakdown = await caption.getAttribute("data-breakdown");
    expect(breakdown, "the figure names a breakdown target").toBeTruthy();
    const target = page.locator(breakdown!);
    await expect(target.first()).toBeAttached();

    // Evidence ≤ 2 actions: the figure's evidence row links its source
    // artifact; the link resolves (action 1 = open the row, action 2 = GET).
    const evidence = caption
      .locator("[data-testid='fig1-caption-evidence']")
      .first();
    await expect(evidence).toBeVisible();
    const sourceHref = await evidence
      .locator("[data-figure-link='source']")
      .getAttribute("href");
    expect(sourceHref, "the figure carries a source link").toBeTruthy();
    expect((await request.get(sourceHref!)).status()).toBe(200);

    // As-of + release id on the page (the visible page stamp).
    await expect(page.getByTestId("page-stamp")).toBeVisible();
    await expect(page.getByTestId("release-stamp").first()).toBeAttached();

    // Rows download in ≤ 3 clicks: dossier → Downloads → a rows link.
    await page.getByTestId("downloads-link").click(); // click 1
    await expect(page).toHaveURL(/\/dossier\/.*downloads\//);
    await expect(page.getByTestId("dld-page")).toBeVisible();
    const rows = page.locator("[data-testid='dld-table'] a[href]");
    expect(
      await rows.count(),
      "the downloads table must carry at least one rows download",
    ).toBeGreaterThan(0);
  });
});

test.describe("CAP-J2 — who supplies ALPRs to Texas agencies, and who can access the data (≤ 10 min)", () => {
  test("JS leg: typeahead → Texas dossier → explore bar → graph view names nodes", async ({
    page,
  }) => {
    test.skip(!jsOn(), "the typeahead/explore leg needs JS");
    await page.goto("/");
    let scope = "[data-testid='site-search-typeahead']";
    let input = page.locator(`${scope} input[name='q']`);
    if (!(await input.isVisible())) {
      // 390 px collapses the inline header search to the Search link —
      // follow it to the search page's typeahead (same shard contract).
      await page.getByTestId("site-search-link").first().click();
      await expect(page).toHaveURL(/\/search\//);
      scope = "[data-testid='release-search-typeahead']";
      input = page.locator(`${scope} input[name='q']`);
    }
    await expect(input).toBeVisible();
    await expect(input).toHaveAttribute("role", "combobox");
    await input.fill("tex");
    const list = page.locator(`${scope} [role='listbox']`);
    await expect(list).toBeVisible();
    const first = list.getByRole("option").first();
    await expect(first).toContainText("Texas");
    await first.click();
    await expect(page).toHaveURL(/\/dossier\/.*tx\//);

    // The dossier's own explore bar carries the graph view scoped to the
    // place — the reader's real path into Explore.
    const exploreLink = page.getByTestId("explore-network");
    await expect(exploreLink).toBeVisible();
    await exploreLink.click();
    await expect(page).toHaveURL(/\/explore\/.*view=graph/);
    await expect(page).toHaveURL(/jurisdiction=/);

    // The island mounts and draws the overview — named nodes in the node
    // table, or a typed absence note (never a silent empty canvas).
    const island = page.getByTestId("explore-island");
    await expect(island).toBeVisible();
    const nodes = island.locator("[data-testid='graph-island-node']");
    const note = island.locator(
      "[data-testid='explore-jurisdiction-miss'], [data-testid='facet-not-applied'], [data-testid='explore-collection-empty'], [data-testid='explore-overview-note']",
    );
    await expect
      .poll(async () => (await nodes.count()) + (await note.count()))
      .toBeGreaterThan(0);

    // The access overview is the K13 second half ("who can access the
    // data") — switch overviews inside the island.
    await page.goto("/explore/?v=2&view=graph&overview=access");
    await expect(island).toBeVisible();
    await expect
      .poll(
        async () =>
          (await island.locator("[data-testid='graph-island-node']").count()) +
          (await island
            .locator(
              "[data-testid='explore-jurisdiction-miss'], [data-testid='facet-not-applied'], [data-testid='explore-collection-empty'], [data-testid='explore-overview-note']",
            )
            .count()),
      )
      .toBeGreaterThan(0);
  });

  test("no-JS leg: the GET form contract, the A–Z path, and the graphs/entity equivalents carry the same facts", async ({
    page,
    request,
  }) => {
    // The no-JS search path is a plain GET form — provable without scripting.
    await page.goto("/");
    const form = page.getByTestId("hero-search-form");
    await expect(form).toHaveAttribute("method", "get");
    await expect(form).toHaveAttribute("action", "/search/");

    // A–Z directory → the Texas place dossier (named no-JS equivalent).
    const tx = await resolveDossierViaAZ(request, "t", "texas");
    await page.goto(tx);
    await expect(page.locator("h1").first()).toContainText("Texas");
    // The explore bar still names the scoped graph/search paths (links
    // render server-side even when the islands never load).
    await expect(page.getByTestId("explore-network")).toBeVisible();

    // The no-JS graph equivalent: /graphs/ index → the access overview →
    // the place drill-down the overview itself advertises.
    await page.goto("/graphs/");
    const rows = page.locator("[data-testid='graphs-index-row']");
    expect(await rows.count()).toBeGreaterThan(0);
    const ares = await request.get("/graphs/access/");
    expect(ares.status()).toBe(200);
    const ahtml = await ares.text();
    const drills = [
      ...new Set(
        [...ahtml.matchAll(/href="(\/graphs\/access\/[^"]+\/)"/g)].map(
          (m) => m[1]!,
        ),
      ),
    ];
    const txDrill = drills.find((h) => h.endsWith("/tx/")) ?? drills[0] ?? null;
    expect(
      txDrill,
      "the access overview must advertise a place drill-down",
    ).toBeTruthy();
    await page.goto(txDrill!);
    const edgeRows = page.locator("[data-testid='graph-edge-row']");
    expect(
      await edgeRows.count(),
      "the access drill-down must list edges",
    ).toBeGreaterThan(0);
    // Every edge dated or "undated"; historical edges marked, never
    // silently present-tense. The row layout is: node · relation · node ·
    // date · state · source · magnitude.
    for (const row of await edgeRows.all()) {
      const cells = row.locator("td");
      const state = (await cells.nth(4).textContent())?.trim() ?? "";
      expect(state.length).toBeGreaterThan(0);
      const source = (await cells.nth(5).textContent())?.trim() ?? "";
      expect(source, "every edge names its source").not.toBe("");
      const dateCell = (await cells.nth(3).textContent())?.trim() ?? "";
      expect(
        dateCell === "undated" || /\d{4}-\d{2}-\d{2}/.test(dateCell),
        "every edge is dated or typed 'undated'",
      ).toBeTruthy();
    }
    // A historical edge reads 'historical' — the fixture's TX access
    // slice carries at least one (never a present-tense fabrication).
    await expect(
      page
        .locator("[data-testid='graph-edge-row'] .sig-typed-state", {
          hasText: "historical",
        })
        .first(),
    ).toBeVisible();

    // Entity pages — the no-JS name lookup for the nodes the graphs name.
    const sres = await request.get("/graphs/supply/");
    expect(sres.status()).toBe(200);
    const shtml = await sres.text();
    const entityHref = /href="(\/entity\/[^"]+\/)"/.exec(shtml)?.[1];
    expect(
      entityHref,
      "the supply overview must link a named entity page",
    ).toBeTruthy();
    const eres = await request.get(entityHref!);
    expect(eres.status()).toBe(200);
    const ehtml = await eres.text();
    expect(ehtml).toContain('data-testid="citation"');
  });
});

test.describe("CAP-J3 — is this figure disputed? (≤ 3 min)", () => {
  test("the contested marker → both sides; typed kinds kept apart", async ({
    page,
    request,
  }) => {
    // A dossier carrying a contested marker: resolve from the served
    // site — Texas carries one on its next-decisions list in the fixture;
    // on the release the same lookup walks the dossier index.
    const tx = await resolveDossierViaAZ(request, "t", "texas");
    await page.goto(tx);
    const marker = page.getByTestId("contested-marker").first();
    // The marker is the ≠ glyph (the 'Contested' meaning is on the
    // element for assistive tech — never color-only).
    await expect(marker).toBeVisible();
    await expect(marker).toHaveAttribute("data-agreement", "CONTESTED");

    // One click to the disagreements surface — the dossier's own link.
    const dgLink = page.locator("[data-testid='dossier-disagreements-link'] a");
    await expect(dgLink).toBeVisible();
    await dgLink.click();
    await expect(page).toHaveURL(/\/disagreements\/place\//);
    // Typed kinds kept apart — every kind section exists with records or
    // its typed absence (never a smoothed "no disagreements").
    for (const kind of [
      "kind-section-contradiction",
      "kind-section-coordinate",
      "kind-section-declared",
      "kind-section-co-located",
    ]) {
      await expect(page.getByTestId(kind)).toBeVisible();
    }

    // Both sides: the disagreements index keeps the recorded
    // contradictions with their two sides — source, dates, claim link.
    await page.goto("/disagreements/");
    const record = page.locator("[data-testid='contradiction-record']").first();
    await expect(record).toBeVisible();
    const sides = record.locator("[data-testid='contradiction-side']");
    expect(await sides.count()).toBeGreaterThanOrEqual(2);
    for (const side of await sides.all()) {
      // A side can carry two links (the named source + the claim page) —
      // assert at least one resolves, not a strict singleton.
      expect(await side.getByRole("link").count()).toBeGreaterThanOrEqual(1);
      const text = (await side.textContent()) ?? "";
      expect(text).toMatch(/recorded|observed/);
    }
    const claimHref = await sides
      .first()
      .getByRole("link", { name: /claim page/ })
      .getAttribute("href");
    expect(claimHref).toBeTruthy();
    expect((await request.get(claimHref!)).status()).toBe(200);
  });
});

test.describe("CAP-J4 — cite it durably (≤ 3 min)", () => {
  test("the cite block carries the as-of pair + ruleset; the legacy selector URL resolves", async ({
    page,
    request,
  }) => {
    const tx = await resolveDossierViaAZ(request, "t", "texas");
    await page.goto(tx);

    // The cite block mounts inside the 'Cite' details — open it (a plain
    // <details> toggle, no scripting needed) to read the block.
    const cite = page.getByTestId("citation").first();
    await expect(cite).toBeAttached();
    await page.getByTestId("cite-details").first().locator("summary").click();
    const permalink = page.getByTestId("permalink").first();
    const href = await permalink.getAttribute("href");
    expect(href).toContain("as_of_world=");
    expect(href).toContain("as_of_belief=");
    expect(href).toContain("ruleset=");
    // The verbatim citation sentence is complete with JS off (the
    // paragraph form never depends on the sig-cite upgrade).
    await expect(page.getByTestId("citation-text").first()).toBeVisible();
    // Where the build binds no immutable snapshot, the interim sentence
    // says so — 'an immutable citable copy is not yet published' — never
    // the 'reproducible' phrase over a non-pinned URL (TX-13b rule).
    const interim = page.getByTestId("citation-interim").first();
    if (await interim.count()) {
      await expect(interim).toContainText("not yet published");
    }

    // The legacy ?as_of_world= selector URL resolves or answers 404/409 —
    // K13's contract for the compatibility index.
    const url = new URL(href!);
    const res = await request.get(url.pathname + url.search);
    expect([200, 404, 409]).toContain(res.status());
  });
});

test.describe("CAP-J5 — what changed since the last release? (≤ 5 min)", () => {
  test("/changes/ separates 'world changed' from 'SIG learned'; place + source feeds resolve", async ({
    page,
    request,
  }) => {
    await page.goto("/changes/");
    // The release pair the diff compares (the fixture ships a synthetic
    // pair; the real ≥ 2-release diff is the gated live leg — CF-13).
    await expect(page.getByTestId("change-range")).toBeVisible();
    await expect(page.getByTestId("as-of-world").first()).toBeVisible();

    // The two lanes are kept apart on the page.
    await expect(page.getByTestId("world-changed")).toBeVisible();
    await expect(page.getByTestId("sig-records-changed")).toBeVisible();
    await expect(page.getByTestId("world-list")).toBeVisible();
    await expect(page.getByTestId("sig-list")).toBeVisible();
    await expect(page.getByTestId("change-method")).toBeVisible();

    // Feeds per place and source — the directory plus at least one live
    // .atom document (feeds exist even at zero entries).
    await page.getByTestId("feed-directory").click();
    await expect(page).toHaveURL(/\/changes\/feeds\//);
    const fres = await request.get("/changes/feeds/");
    const fhtml = await fres.text();
    const atoms = [
      ...new Set(
        [...fhtml.matchAll(/href="(\/changes\/feeds\/[^"]+\.atom)"/g)].map(
          (m) => m[1]!,
        ),
      ),
    ];
    expect(
      atoms.length,
      "the feed directory must link at least one .atom feed",
    ).toBeGreaterThan(0);
    const atom = await request.get(atoms[0]!);
    expect(atom.status()).toBe(200);
    expect(await atom.text()).toContain("<feed");

    // The all-changes feed and the OPML bundle resolve too.
    expect((await request.get("/changes/feeds/all.atom")).status()).toBe(200);
    expect((await request.get("/changes/feeds.opml")).status()).toBe(200);
  });
});
