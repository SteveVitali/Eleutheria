// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// P37.68a (R11-K13-CAP-01, split a — K13 §8 capstone journeys A1–A4,
// SIG-UI-078): the advocate-journey battery walked COLD from `/`, once per
// {390, 1440 px} x {JS on, JS off} project cell of playwright.capstone.config.ts.
// Two audiences run the same file:
//   - fixtures: `npx playwright test -c playwright.capstone.config.ts`
//     previews the built dist (the fixture-verified layer);
//   - the promoted release: `SIG_CAPSTONE_BASE_URL=<origin> npx playwright
//     test -c playwright.capstone.config.ts` — the deferred live leg
//     (D-P37.68a-1, OM-19 `live_verification=true`).
// Every journey resolves its targets from the served site itself (the A–Z
// directory is the named no-JS place-lookup equivalent, U-003.1); nothing
// fixture-specific is hard-coded. Recorded AGENT-VERIFIED (P4 honesty —
// never user research); the operator's walkthrough is its own recorded act
// (OP-22, "operator walkthrough (maintainer, not independent)"), never
// simulated here.

import { expect, test } from "@playwright/test";

const jsOn = (): boolean => test.info().project.use.javaScriptEnabled !== false;

/**
 * Resolve the Oklahoma City place dossier through the A–Z directory — the
 * named no-JS place-lookup equivalent that exists on every published build.
 * Prefers the canonical `/dossier/usa/ok/…` slug but accepts any
 * oklahoma-city dossier link so the battery is corpus-honest.
 */
async function resolveOklahomaCityDossier(
  request: import("@playwright/test").APIRequestContext,
): Promise<string> {
  const res = await request.get("/dossier/a-z/o/");
  expect(res.status()).toBe(200);
  const html = await res.text();
  const links = [
    ...html.matchAll(/href="(\/dossier\/[^"]*oklahoma-city[^"]*?)"/g),
  ].map((m) => m[1]!);
  const canonical = links.find(
    (h) => h.startsWith("/dossier/usa/") && h.endsWith("/"),
  );
  const any = links.find((h) => h.endsWith("/"));
  const href = canonical ?? any;
  expect(
    href,
    "an Oklahoma City dossier link must exist on /dossier/a-z/o/",
  ).toBeTruthy();
  return href!;
}

test.describe("CAP-A1 — type 'Oklahoma City', reach its place dossier in ≤ 3 clicks", () => {
  test("JS leg: home hero typeahead → place card → dossier", async ({
    page,
  }) => {
    test.skip(
      !jsOn(),
      "the typeahead leg needs JS — the no-JS leg is the sibling test",
    );
    await page.goto("/"); // click 0
    const input = page.locator(
      "[data-testid='hero-search-typeahead'] input[name='q']",
    );
    await input.fill("okla"); // click 1: type
    const list = page.locator(
      "[data-testid='hero-search-typeahead'] [role='listbox']",
    );
    await expect(list).toBeVisible();
    const first = list.getByRole("option").first();
    await expect(first).toContainText("Oklahoma");
    await first.click(); // click 2 — the option navigates to the place result
    await expect(page).toHaveURL(/\/dossier\//);
    await expect(page.locator("h1").first()).toContainText("Oklahoma");
  });

  test("JS leg: the header/search typeahead returns the same place (UXR-24)", async ({
    page,
  }) => {
    test.skip(!jsOn(), "the typeahead leg needs JS");
    await page.goto("/");
    let scope = "[data-testid='site-search-typeahead']";
    let input = page.locator(`${scope} input[name='q']`);
    if (!(await input.isVisible())) {
      // Narrow widths collapse the inline header search to the Search link —
      // the designed mobile pattern: follow it and use the search page's
      // typeahead, which must return the same place.
      await page.getByTestId("site-search-link").first().click();
      await expect(page).toHaveURL(/\/search\//);
      scope = "[data-testid='release-search-typeahead']";
      input = page.locator(`${scope} input[name='q']`);
    }
    await expect(input).toBeVisible();
    // wait for the sig-typeahead upgrade (role=combobox) before typing —
    // a fill before hydration dispatches input events nothing listens to
    await expect(input).toHaveAttribute("role", "combobox");
    await input.fill("okla");
    const list = page.locator(`${scope} [role='listbox']`);
    await expect(list).toBeVisible();
    const first = list.getByRole("option").first();
    await expect(first).toContainText("Oklahoma");
    await first.click();
    await expect(page).toHaveURL(/\/dossier\//);
    await expect(page.locator("h1").first()).toContainText("Oklahoma");
  });

  test("no-JS leg: the GET form contract holds and the index path reaches the dossier", async ({
    page,
    request,
  }) => {
    await page.goto("/");
    // The no-JS search path is a plain GET form — provable without scripting.
    const form = page.getByTestId("hero-search-form");
    await expect(form).toHaveAttribute("method", "get");
    await expect(form).toHaveAttribute("action", "/search/");
    await page.goto("/search/?q=Oklahoma+City");
    await expect(page.locator("main")).toBeVisible();
    // The named no-JS place-lookup equivalent: the A–Z directory click path.
    await page.goto("/dossier/a-z/o/");
    const link = page.getByRole("link", { name: /Oklahoma City/ }).first();
    await expect(link).toBeVisible();
    await link.click();
    await expect(page).toHaveURL(/\/dossier\//);
    await expect(page.locator("h1").first()).toContainText("Oklahoma");
    // And the resolved route is the dossier the JS legs reach.
    const okc = await resolveOklahomaCityDossier(request);
    const res = await request.get(okc);
    expect(res.status()).toBe(200);
  });
});

test.describe("CAP-A2 — what is deployed, who runs and approved it, next decision", () => {
  test("the place dossier answers with sourced values or typed absences", async ({
    page,
    request,
  }) => {
    const okc = await resolveOklahomaCityDossier(request);
    await page.goto(okc);
    // At a glance: figures with "records" wording — never a bare census claim.
    const glance = page.locator('[data-section-id="at_a_glance"]');
    await expect(glance).toBeVisible();
    await expect(glance.locator("text=records").first()).toBeVisible();
    // Who runs/supplies: the "Where this comes from" block with single-source share.
    await expect(page.getByTestId("dsrc-block")).toBeVisible();
    await expect(page.getByTestId("dsrc-top-sources")).toBeVisible();
    // Next decisions: items or a typed absence — never a guessed date.
    await expect(page.getByTestId("next-decisions")).toBeVisible();
    // Every field a value or a named absence (empty-state / hatch markers).
    const sections = page.getByTestId("dossier-section");
    expect(await sections.count()).toBeGreaterThan(5);
    // Provenance furniture the journey's pass requires: the visible as-of /
    // build stamp, and the release stamp rendered in the page (the footer's
    // RS stamp is deliberately muted chrome — DOM presence, not visibility).
    await expect(page.getByTestId("page-stamp")).toBeVisible();
    const stamp = page.getByTestId("release-stamp").first();
    await expect(stamp).toBeAttached();
    expect((await stamp.textContent())?.trim().length).toBeGreaterThan(0);
  });
});

test.describe("CAP-A3 — print for a council member", () => {
  test("dossier → a print route serves the council brief with provenance on the page", async ({
    page,
    request,
  }) => {
    const okc = await resolveOklahomaCityDossier(request);
    // The print link may live on the place dossier or a breadcrumb ancestor —
    // the reader's real path walks up the jurisdiction chain until a Print
    // action exists (≤ 3 ancestors; none → the journey fails loud).
    let trail = okc;
    let printHref: string | null = null;
    for (let hop = 0; hop < 3 && printHref === null; hop += 1) {
      const res = await request.get(trail);
      expect(res.status()).toBe(200);
      const html = await res.text();
      printHref =
        /href="(\/dossier\/[^"]*print\/)"[^>]*data-testid="print-link"/.exec(
          html,
        )?.[1] ??
        /data-testid="print-link"[^>]*href="(\/dossier\/[^"]*print\/)"/.exec(
          html,
        )?.[1] ??
        /href="(\/dossier\/[^"]*print\/)"/.exec(html)?.[1] ??
        null;
      if (printHref === null) {
        // walk up one dossier ancestor — /dossier/usa/ok/x/ → /dossier/usa/ok/
        const up = trail.replace(/[^/]+\/$/, "");
        expect(
          up !== trail && up.startsWith("/dossier/"),
          `no print action found on ${trail} and no dossier ancestor remains`,
        ).toBeTruthy();
        trail = up;
      }
    }
    expect(
      printHref,
      "a dossier print route must exist within 3 ancestors",
    ).toBeTruthy();
    await page.goto(printHref!);
    // Page 1 council brief with locator; as-of, release id, permalink, licence.
    await expect(page.getByTestId("council-brief")).toBeVisible();
    await expect(page.getByTestId("brief-locator")).toBeVisible();
    await expect(page.getByTestId("print-permalink").first()).toBeVisible();
    await expect(page.getByTestId("print-terms").first()).toBeVisible();
    await expect(page.getByTestId("print-runhead").first()).toBeVisible();
  });
});

test.describe("CAP-A4 — know what to bring; act on what we don't know", () => {
  test("the brief's documents block and the gap → queue → task → draft path resolve", async ({
    page,
    request,
  }) => {
    const okc = await resolveOklahomaCityDossier(request);
    // Documents to bring: the print brief names them or carries the typed absence.
    let docsSeen = false;
    let trail = okc;
    for (let hop = 0; hop < 3 && !docsSeen; hop += 1) {
      const res = await request.get(trail);
      const html = await res.text();
      const print = /href="(\/dossier\/[^"]*print\/)"/.exec(html)?.[1];
      if (print) {
        const pres = await request.get(print);
        const phtml = await pres.text();
        docsSeen = /data-testid="brief-documents[^"]*"/.test(phtml);
      }
      const up = trail.replace(/[^/]+\/$/, "");
      if (up === trail || !up.startsWith("/dossier/")) break;
      trail = up;
    }
    expect(
      docsSeen,
      "a dossier print brief must carry a documents-to-bring block",
    ).toBeTruthy();
    // What we don't know → the queue → a records-request task → the draft.
    await page.goto(okc);
    await expect(
      page.getByTestId("what-we-dont-know-section").first(),
    ).toBeVisible();
    const qres = await request.get("/research-queue/");
    expect(qres.status()).toBe(200);
    const qhtml = await qres.text();
    const candidates = [
      ...new Set(
        [...qhtml.matchAll(/href="(\/task\/[^"#]+?)"/g)].map((m) => m[1]!),
      ),
    ];
    expect(
      candidates.length,
      "the research queue must link at least one task",
    ).toBeGreaterThan(0);
    // A4 asks for a records-request draft — pick the first task page carrying
    // one (≤ 6 candidates; none → the journey fails loud, never a guessed pass).
    let taskHref: string | null = null;
    for (const href of candidates.slice(0, 6)) {
      const res = await request.get(href);
      if (
        res.status() === 200 &&
        /data-testid="draft-download"/.test(await res.text())
      ) {
        taskHref = href;
        break;
      }
    }
    expect(
      taskHref,
      "no records-request task (draft-download) among the queue's first tasks",
    ).toBeTruthy();
    await page.goto(taskHref!);
    await expect(page.getByTestId("task-closing")).toBeVisible();
    await expect(page.getByTestId("task-draft")).toBeVisible();
    // "SIG sends nothing" — the draft is a download, never a sent request.
    await expect(page.getByTestId("draft-never-sent")).toBeVisible();
    const dl = await page.getByTestId("draft-download").getAttribute("href");
    expect(dl).toContain(".draft.txt");
    expect((await request.get(dl!)).status()).toBe(200);
  });
});
