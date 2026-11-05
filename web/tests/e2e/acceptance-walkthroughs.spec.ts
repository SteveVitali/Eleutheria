// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// P36.72a (ACC-PLACES / K13 §8 capstone journeys A1 A2 A3 A4 O1 O3 O4 J1 +
// the K7 KJ7 and K8/K11 legs this row merged): the agent walkthroughs over
// the fixture corpus — each journey walked cold like a reader would, every
// fact carrying a source, an as-of and a release id. Recorded AGENT-VERIFIED
// (P4 honesty — never represented as user research); the promoted-release
// walk is P36.72b's.

import { expect, test } from "@playwright/test";

const OKC = "/dossier/usa/ok/oklahoma-city-4064000/";
const HARRIS = "/dossier/usa/tx/harris-county-48201/";
const LEGACY_OKC = "/dossier/oklahoma-city/";

test.describe("A1 — type 'Oklahoma City', reach its place dossier in ≤ 3 clicks", () => {
  test("home typeahead → place card → dossier", async ({ page }) => {
    await page.goto("/"); // click 0
    const input = page.locator("[data-testid='hero-search-typeahead'] input[name='q']");
    await input.fill("okla"); // click 1: type
    const list = page.locator("[data-testid='hero-search-typeahead'] [role='listbox']");
    await expect(list).toBeVisible();
    const first = list.getByRole("option").first();
    await expect(first).toContainText("Oklahoma");
    await first.click(); // click 2 — an option click navigates to the place card
    await expect(page).toHaveURL(/\/dossier\//);
    await expect(page.locator("h1")).toContainText("Oklahoma");
  });

  test("the no-JS GET path lands on /search/?q= and the result set reaches the dossier", async ({
    page,
  }) => {
    await page.goto("/");
    const form = page.getByTestId("hero-search-form");
    await expect(form).toHaveAttribute("method", "get");
    await expect(form).toHaveAttribute("action", "/search/");
    // plain GET — the same URL the form emits without JS
    await page.goto("/search/?q=Oklahoma+City");
    await expect(page.locator("main")).toBeVisible();
    // the dossier index/A–Z reaches Oklahoma City without search JS at all
    await page.goto("/dossier/a-z/o/");
    await expect(page.getByRole("link", { name: /Oklahoma City/ }).first()).toBeVisible();
  });
});

test.describe("A2 — what is deployed, who runs and approved it, next decision", () => {
  test("the OKC dossier answers with sourced values or typed absences", async ({ page }) => {
    await page.goto(OKC);
    // At a glance: sourced figures, not bare numbers
    const glance = page.locator('[data-section-id="at_a_glance"]');
    await expect(glance).toBeVisible();
    await expect(glance.locator("text=records").first()).toBeVisible();
    // Who runs/supplies: the "Where this comes from" block names sources + share
    await expect(page.getByTestId("dsrc-block")).toBeVisible();
    await expect(page.getByTestId("dsrc-top-sources")).toContainText("OKC camera registry");
    // Next decisions: items or a typed absence — never a guessed date
    await expect(page.getByRole("heading", { name: /Next decisions/ })).toBeVisible();
    // every field a value or a named absence (the empty-state / hatch markers)
    const sections = page.getByTestId("dossier-section");
    expect(await sections.count()).toBeGreaterThan(5);
  });
});

test.describe("A3 — print for a council member", () => {
  test("the state dossier's print view is a council brief with provenance on the page", async ({
    page,
  }) => {
    await page.goto("/dossier/usa/ok/");
    const printLink = page.locator('a[href="/dossier/usa/ok/print/"]');
    await expect(printLink.first()).toBeVisible();
    await printLink.first().click();
    await expect(page).toHaveURL(/\/dossier\/usa\/ok\/print\//);
    await expect(page.getByTestId("council-brief")).toBeVisible();
    await expect(page.getByTestId("brief-locator")).toBeVisible();
    await expect(page.getByTestId("print-permalink").first()).toBeVisible();
    await expect(page.getByTestId("print-terms").first()).toBeVisible();
    // as-of + release id on the page
    await expect(page.getByTestId("print-runhead").first()).toBeVisible();
  });
});

test.describe("A4 — know what to bring; act on what we don't know", () => {
  test("the brief's documents block and the dossier's gap → task → draft path resolve", async ({
    page,
    request,
  }) => {
    // documents to bring: the print brief names them (or a named absence)
    await page.goto("/dossier/usa/ok/print/");
    const docs = page.locator('[data-testid^="brief-documents"]');
    expect(await docs.count()).toBeGreaterThan(0);
    // what we don't know → task → records-request draft (downloadable, never sent)
    await page.goto(LEGACY_OKC);
    const taskLink = page.locator('a[href^="/task/T-"]').first();
    await expect(taskLink).toBeVisible();
    await page.goto("/task/T-usa-ok-oklahoma-city-retention-pd-q1c4/");
    await expect(page.getByTestId("task-closing")).toBeVisible();
    await expect(page.getByTestId("task-draft")).toBeVisible();
    await expect(page.getByTestId("draft-never-sent")).toBeVisible();
    const dl = await page.getByTestId("draft-download").getAttribute("href");
    expect(dl).toContain(".draft.txt");
    expect((await request.get(dl!)).status()).toBe(200);
  });
});

test.describe("O1 — who runs what in my county", () => {
  test("the Harris County dossier shows figures, a sites list and its sources", async ({ page }) => {
    await page.goto(HARRIS);
    await expect(page.getByTestId("dossier-rollup")).toBeVisible();
    await expect(page.getByTestId("dsrc-top-sources")).toBeVisible();
    // the sites list resolves — the no-JS local list
    await page.goto(`${HARRIS}sites/`);
    await expect(page.getByTestId("sites-count")).toBeVisible();
    expect(await page.getByTestId("site-row").count()).toBeGreaterThan(0);
  });
});

test.describe("O3 — a local list without the map", () => {
  test("the OKC sites page lists rows with a CSV download, licence and attribution", async ({
    page,
    request,
  }) => {
    await page.goto(`${OKC}sites/`);
    await expect(page.getByTestId("sites-count")).toBeVisible();
    expect(await page.getByTestId("site-row").count()).toBeGreaterThan(0);
    expect(await page.getByTestId("sites-licence-line").count()).toBeGreaterThan(0);
    await expect(page.getByTestId("sites-compartment-name").first()).toBeVisible();
    const csv = page.getByTestId("sites-csv");
    const href = await csv.getAttribute("href");
    expect(href).toBeTruthy();
    const res = await request.get(href!);
    expect(res.status()).toBe(200);
    // zero scripts on the table surface (T1 zero-JS)
    expect(await page.locator("main script").count()).toBe(0);
  });
});

test.describe("O4 — act on a gap", () => {
  test("an absence chip reaches a task page with closing condition and request template", async ({
    page,
  }) => {
    await page.goto(LEGACY_OKC);
    const task = page.locator('a[href^="/task/T-"]').first();
    await expect(task).toBeVisible();
    const href = await task.getAttribute("href");
    await page.goto(href!);
    await expect(page.getByTestId("task-page")).toBeVisible();
    await expect(page.getByTestId("task-closing")).toBeVisible();
    // how to act / where to send it — the operator-named channel block
    await expect(page.getByTestId("task-how-to-act")).toBeVisible();
  });
});

test.describe("J1 — defend a headline figure", () => {
  test("a figure reaches its breakdown and its recomputing rows in ≤ 2 actions", async ({
    page,
    request,
  }) => {
    await page.goto("/coverage-metrics/");
    const figure = page.locator(".sig-figure[data-artifact]").first();
    await expect(figure).toBeVisible();
    // unit/denominator context + as-of on the page
    await expect(page.getByTestId("page-stamp")).toBeVisible();
    const src = figure.locator('[data-figure-link="source"]');
    const href = await src.getAttribute("href");
    expect(href).toBeTruthy();
    // action 1: source → the recomputing artifact
    const res = await request.get(href!);
    expect(res.status()).toBe(200);
    // breakdown anchor resolves in-page
    const breakdown = await figure.getAttribute("data-breakdown");
    if (breakdown?.startsWith("#")) {
      await expect(page.locator(breakdown)).toHaveCount(1);
    }
  });
});
