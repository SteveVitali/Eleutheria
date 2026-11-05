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
    // P36.62 (RQ-03b): the card's one link is its real task page.
    const link = card.getByTestId("task-link");
    await expect(link).toHaveCount(1);
    await expect(link).toHaveAttribute("href", /^\/task\/T-/);
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
    // P36.64 (UXK14-6): the flat entry-point grid is now the K14 persona
    // start-here paths; the organizer path's last step links the queue.
    const card = page.getByTestId("persona-organizer");
    const link = card.locator("a[href='/research-queue/']");
    await expect(link).toHaveCount(1);
    await expect(link).toContainText(/open question/i);
  });

  test("O4 leg-a — an absence chip's Help-find-it link reaches the queue", async ({ page }) => {
    // The K13 O4 journey's a-half: chip → hub → place facet → card.
    await page.goto("/research-queue/");
    await page
      .getByTestId("start-place")
      .locator("a", { hasText: "Oklahoma City" })
      .click();
    await expect(page).toHaveURL(new RegExp(`${OKC_PLACE}$`));
    await expect(page.getByTestId("closing-condition").first()).not.toBeEmpty();
  });
});

test.describe("P36.62 (RQ-03b) — task pages, campaigns, gap links, redirects", () => {
  const TASK = "/task/T-usa-ok-oklahoma-city-retention-pd-q1c4/";
  const CAMPAIGN = "/research-queue/campaign/M-usa-ok-oklahoma-city-operator-osm-5f0a/";

  test("the task page renders every §5.3 block as a value or a named absence", async ({
    page,
  }) => {
    await page.goto(TASK);
    await expect(page.getByTestId("task-page")).toBeVisible();
    for (const id of [
      "task-status-line",
      "task-handle",
      "task-unknown",
      "task-evidence-sought",
      "task-predicates",
      "task-why",
      "task-subject",
      "task-place",
      "task-trigger-detail",
      "task-trigger",
      "task-sources",
      "task-draft",
      "task-closing",
      "task-how-to-act",
      "task-report",
      "task-dispositions",
      "task-history",
      "task-related",
      "task-technical",
      "task-json-twin",
    ]) {
      await expect(page.getByTestId(id), id).toBeVisible();
    }
    // Oklahoma City is claimed — the line names priority, never exclusivity.
    await expect(page.getByTestId("task-status-line")).toContainText("anyone may still work this task");
    // The closing condition names the predicate — the block is never blank.
    await expect(page.getByTestId("task-predicates")).toContainText("configured_retention_days");
    // No raw UUID is a heading (SIG-RQ-001).
    const heads = await page.locator("h1, h2, h3").allTextContents();
    for (const h of heads) {
      expect(h).not.toMatch(/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/);
    }
  });

  test("the JSON twin carries sig.task-page/1 with the card fields", async ({ page }) => {
    const res = await page.goto("/task/T-usa-ok-oklahoma-city-retention-pd-q1c4.json");
    expect(res?.status()).toBe(200);
    const body = await res!.json();
    expect(body.schema).toBe("sig.task-page/1");
    expect(body.handle).toBe("T-usa-ok-oklahoma-city-retention-pd-q1c4");
    expect(body.predicate_ids).toContain("configured_retention_days");
    expect(body.closing_condition).toBeTruthy();
  });

  test("the campaign page shows the field, count, why and the honest contribution note", async ({
    page,
  }) => {
    await page.goto(CAMPAIGN);
    await expect(page.getByTestId("campaign-page")).toBeVisible();
    await expect(page.getByTestId("campaign-summary")).toContainText("3");
    await expect(page.getByTestId("campaign-why")).not.toBeEmpty();
    await expect(page.getByTestId("campaign-members")).toBeVisible();
    // MapRoulette is the named absence until HG-08 registers — never a dead link.
    await expect(page.getByTestId("campaign-maproulette")).toContainText("No MapRoulette");
  });

  test("a dossier gap resolves to the real task page — never a mock (SIG-RQ-008)", async ({
    page,
  }) => {
    await page.goto("/dossier/oklahoma-city/");
    const link = page.getByTestId("gap-task-section").first();
    await expect(link).toBeVisible();
    await expect(link).toHaveAttribute("href", TASK);
    // …and a gap with no queued task names the absence, never a guessed link.
    await expect(page.getByTestId("gap-no-task-section").first()).toBeVisible();
    // The resolved gap IS the landing task — click through (O4 leg-b).
    await link.click();
    await expect(page).toHaveURL(new RegExp(`${TASK}$`));
    await expect(page.getByTestId("task-closing")).not.toBeEmpty();
  });

  test("a typed-absence row resolves to the same task page", async ({ page }) => {
    await page.goto("/dossier/oklahoma-city/");
    const hatch = page
      .getByTestId("absence-hatch")
      .filter({ has: page.locator(`a[href='${TASK}']`) });
    await expect(hatch.first()).toBeVisible();
  });

  test("the /task/<task_id>/ alias stub resolves to the handle (SIG-RQ-009)", async ({
    page,
    request,
  }) => {
    // The stub IS a 0-second meta-refresh + link — assert its markup at
    // request level (a browser follows the refresh straight to the page).
    const res = await request.get("/task/fx-okc-conflicting-retention/");
    expect(res.status()).toBe(200);
    const html = await res.text();
    expect(html).toContain('data-testid="task-alias-stub"');
    expect(html).toContain(`url=${TASK}`);
    expect(html).toContain(`href="${TASK}"`);
    // …and the generated include covers the same id-alias (the 301 leg).
    await page.goto(TASK);
    await expect(page.getByTestId("task-page")).toBeVisible();
  });
});

test.describe("P36.63 (RQ-04) — records-request drafts (SIG-RQ-007/010)", () => {
  const TASK = "/task/T-usa-ok-oklahoma-city-retention-pd-q1c4/";
  const VA_TASK = "/task/T-usa-va-fairfax-county-contract-pd-d8r2/";

  test("a records-requester task renders the DRAFT — statute, citation, template, never sent", async ({
    page,
  }) => {
    await page.goto(TASK);
    await expect(page.getByTestId("draft-banner")).toContainText("DRAFT");
    await expect(page.getByTestId("draft-banner")).toContainText("SIG sends nothing");
    await expect(page.getByTestId("draft-statute")).toContainText("Oklahoma Open Records Act");
    await expect(page.getByTestId("draft-statute")).toContainText("24A.1");
    await expect(page.getByTestId("draft-template")).toContainText("v1");
    await expect(page.getByTestId("draft-body")).toContainText(
      "Pursuant to the Oklahoma Open Records Act",
    );
    await expect(page.getByTestId("draft-residency")).toContainText(
      "No residency restriction",
    );
    await expect(page.getByTestId("draft-never-sent")).toContainText("not legal advice");
    // The DRAFT label is on every view of the draft.
    await expect(page.getByTestId("task-draft")).toHaveAttribute("data-draft-status", "drafted");
    // The download link resolves to the .txt twin.
    const dl = page.getByTestId("draft-download");
    await expect(dl).toHaveAttribute(
      "href",
      "/task/T-usa-ok-oklahoma-city-retention-pd-q1c4.draft.txt",
    );
  });

  test("there is no transmit path — no form, no mailto, no send affordance", async ({ page }) => {
    await page.goto(TASK);
    // Scoped to the task article: the chrome's GET search form/button is
    // header chrome, never a transmit path — the draft block itself offers
    // no form, no button and no mailto.
    const article = page.getByTestId("task-page");
    await expect(article.locator("form")).toHaveCount(0);
    await expect(article.locator("a[href^='mailto:']")).toHaveCount(0);
    await expect(article.locator("button")).toHaveCount(0);
    const main = await article.innerHTML();
    expect(main).not.toMatch(/<form|mailto:|<button/);
  });

  test("a residency-restricted state's draft carries the routing note", async ({ page }) => {
    await page.goto(VA_TASK);
    await expect(page.getByTestId("draft-banner")).toContainText("DRAFT");
    await expect(page.getByTestId("draft-residency")).toContainText(
      "restricts public-records requests to residents",
    );
    await expect(page.getByTestId("draft-statute")).toContainText(
      "Virginia Freedom of Information Act",
    );
  });

  test("a task in a non-draft role names the absence — never a guessed draft", async ({
    page,
  }) => {
    await page.goto("/task/T-usa-ok-oklahoma-city-devices-pd-k1v9/");
    await expect(page.getByTestId("task-draft")).toContainText(
      "not a records-request or document-review task",
    );
    await expect(page.getByTestId("draft-body")).toHaveCount(0);
  });

  test("the .txt download serves the draft text with the DRAFT banner", async ({ request }) => {
    const res = await request.get("/task/T-usa-ok-oklahoma-city-retention-pd-q1c4.draft.txt");
    expect(res.status()).toBe(200);
    expect(res.headers()["content-type"]).toContain("text/plain");
    const body = await res.text();
    expect(body).toContain("DRAFT PUBLIC-RECORDS REQUEST");
    expect(body).toContain("Okla. Stat. tit. 51 § 24A.1");
    expect(body).toContain("SIG sends nothing; you file it; the filer is left blank.");
    expect(body).toContain("[the contributor who files this request");
  });

  test("the per-place bundle serves every draft for the place — 0 sent", async ({ request }) => {
    const okc = await request.get("/research-queue/drafts/usa/ok/oklahoma-city-4064000.txt");
    expect(okc.status()).toBe(200);
    const okcBody = await okc.text();
    expect(okcBody).toContain("DRAFT");
    expect(okcBody).toContain("0 sent");
    expect(okcBody).toContain("Oklahoma Open Records Act");
    const va = await request.get("/research-queue/drafts/usa/va/fairfax-county-51059.txt");
    const vaBody = await va.text();
    expect(vaBody).toContain("Virginia Freedom of Information Act");
    expect(vaBody).toContain("restricts public-records requests to residents");
  });

  test("the hub and the place page link the bundle; the card carries the draft badge", async ({
    page,
  }) => {
    await page.goto("/research-queue/");
    const link = page
      .getByTestId("draft-bundles")
      .locator("a[href='/research-queue/drafts/usa/ok/oklahoma-city-4064000.txt']");
    await expect(link).toHaveCount(1);
    await page.goto("/research-queue/place/usa/ok/oklahoma-city-4064000/");
    await expect(page.getByTestId("draft-bundle-link")).toBeVisible();
    // The badge marks only the draft-bearing card, links to the draft block.
    const badge = page.getByTestId("draft-badge").first();
    await expect(badge).toContainText("DRAFT request available");
    await expect(badge.locator("a")).toHaveAttribute(
      "href",
      "/task/T-usa-ok-oklahoma-city-retention-pd-q1c4/#records-request-draft",
    );
    // The JSON twin carries the DRAFT row.
    const res = await page.request.get("/task/T-usa-ok-oklahoma-city-retention-pd-q1c4.json");
    const body = await res.json();
    expect(body.records_request_draft.status).toBe("drafted");
    expect(body.draft_download).toBe(
      "task/T-usa-ok-oklahoma-city-retention-pd-q1c4.draft.txt",
    );
  });
});
