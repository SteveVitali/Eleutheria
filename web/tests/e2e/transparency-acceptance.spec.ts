// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// P37.65a (J3 TX-16 / R11-K13-TX-16): the transparency-acceptance journey
// legs — the K13 §8 capstone re-runs' deterministic half over the emitted
// dist. J1 (defend a headline figure) walks figure → source artifact →
// breakdown; J4 (cite it durably) verifies the cite-block contract over
// every emitted route that carries one: exactly one mode (immutable /
// interim / unreleased), the pinned-selector permalink resolving. The
// durable-pin half — the pinned /s/<pub>/ URL returning identical bytes —
// is a property of the staged/promoted release and rides the
// release-cut / live-crawl legs (sig.transparency-acceptance/1), never
// claimed here (SIG-ENG-042: an agent walkthrough, never user research).

import { expect, test } from "@playwright/test";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { DIST_DIR, emittedRoutes, parseFigureRegions, routeFile } from "./acceptance";

const EMITTED = emittedRoutes();
//: The emitted HTML routes — `<dir>/index.html` serves at `<dir>/`.
const HTML_ROUTES = EMITTED.filter((r) => r.endsWith("/"));

test.describe("J1 — defend a headline figure (K13 §8, agent walkthrough)", () => {
  test("a figure reaches its recomputing bytes and breakdown in ≤ 2 actions", async ({
    page,
    request,
  }) => {
    // `/coverage-metrics/` is the fixture page whose headline figures carry
    // the artifact + pointer + breakdown contract end-to-end.
    await page.goto("/coverage-metrics/");
    const figure = page.locator(".sig-figure[data-artifact]").first();
    await expect(figure).toBeVisible();
    // unit/denominator context + the as-of stamp on the page.
    await expect(page.getByTestId("page-stamp")).toBeVisible();
    await expect(page.getByTestId("footer-tagline")).toContainText("not a census");
    // action 1: the figure's `source` link resolves to recomputing bytes.
    const href = await figure
      .locator('[data-figure-link="source"]')
      .first()
      .getAttribute("href");
    expect(href).toBeTruthy();
    const res = await request.get(href!);
    expect(res.status()).toBe(200);
    // the value the page asserts is the figure's declared value — never a
    // drifting number (the recompute sweep owns the full equality proof).
    const value = await figure.getAttribute("data-figure-value");
    expect(value).toBeTruthy();
    // action 2 (optional): an in-page breakdown anchor resolves when declared.
    const breakdown = await figure.getAttribute("data-breakdown");
    if (breakdown?.startsWith("#")) {
      await expect(page.locator(breakdown)).toHaveCount(1);
    }
  });

  test("every figure region on the walked pages names its bytes and pointer", async () => {
    // The emitted-side proof that no J1 figure floats free of its evidence:
    // parseFigureRegions only returns regions carrying artifact+pointer+value,
    // so a region missing the contract is a parse gap, asserted non-vacuously.
    const checked: string[] = [];
    for (const route of ["/", "/coverage-metrics/", "/about/", "/quality/"]) {
      const file = routeFile(route);
      if (file === null) continue;
      const html = readFileSync(join(DIST_DIR, file), "utf-8");
      const figures = parseFigureRegions(html, file);
      for (const f of figures) {
        expect(f.pointer.startsWith("/"), `${f.id} pointer`).toBeTruthy();
        // the recomputing bytes are an emitted route or a declared on-page
        // breakdown — never an unresolved pointer.
        expect(
          f.artifact.length > 0 || f.breakdown.startsWith("#"),
          `${f.id} in ${file} names neither bytes nor a breakdown`,
        ).toBeTruthy();
      }
      checked.push(`${route}:${figures.length}`);
    }
    expect(
      checked.some((c) => !c.endsWith(":0")),
      `no figure regions found on the walked pages: ${checked.join(", ")}`,
    ).toBeTruthy();
  });
});

test.describe("J4 — cite it durably (K13 §8, deterministic half)", () => {
  test("every cite-carrying route shows exactly one cite mode", async ({ request }) => {
    let carrying = 0;
    const failures: string[] = [];
    for (const route of HTML_ROUTES) {
      const res = await request.get(route);
      if (res.status() !== 200) continue;
      const html = await res.text();
      if (!html.includes('data-testid="citation"')) continue;
      carrying += 1;
      const modes = [
        html.includes('data-immutable="true"'),
        html.includes('data-testid="citation-interim"'),
        // the unreleased mode renders the permalink link with no immutable
        // marker and no interim sentence.
        !html.includes('data-immutable="true"') &&
          !html.includes('data-testid="citation-interim"') &&
          html.includes('data-testid="permalink"'),
      ].filter(Boolean).length;
      if (modes !== 1) failures.push(`${route} — ${modes} cite modes`);
      // the pinned-selector permalink carries the as-of pair + ruleset.
      const m = /data-testid="permalink"[^>]*href="([^"]+)"/.exec(html);
      if (!m) {
        failures.push(`${route} — no permalink anchor`);
        continue;
      }
      if (
        !m[1].includes("as_of_world=") ||
        !m[1].includes("as_of_belief=") ||
        !m[1].includes("ruleset=")
      ) {
        failures.push(`${route} — permalink ${m[1]} is not the pinned-selector form`);
      }
      // the permalink's path half resolves on the same origin.
      const path = m[1].replace(/^https?:\/\/[^/]+/, "").split("?")[0];
      const pres = await request.get(path || "/");
      if (pres.status() !== 200) {
        failures.push(`${route} — permalink path ${path} → ${pres.status()}`);
      }
    }
    expect(
      carrying,
      "no route carries the cite block — the J4 leg would be vacuous",
    ).toBeGreaterThan(0);
    expect(failures, failures.join("; ")).toEqual([]);
  });

  test("the interim/immutable wording never claims an unpinned copy", async ({ request }) => {
    // J3 §8.2 verbatim honesty: "reproducible after SIG corrects itself" may
    // appear ONLY beside an immutable /s/<pub>/ or /r/<pub>/ cite URL. On a
    // development/fixture build the interim sentence or the unreleased link
    // carries the honest state — never the pinning promise.
    let checked = 0;
    const failures: string[] = [];
    for (const route of HTML_ROUTES) {
      const res = await request.get(route);
      if (res.status() !== 200) continue;
      const html = await res.text();
      if (!html.includes('data-testid="citation"')) continue;
      checked += 1;
      const immutable = html.includes('data-immutable="true"');
      const claims = html.includes("reproducible after SIG corrects itself");
      if (claims && !immutable) {
        failures.push(`${route} — the pinning promise without an immutable cite URL`);
      }
      if (immutable) {
        const m = /data-testid="citation-immutable"[^>]*href="([^"]+)"/.exec(html);
        if (!m || !m[1].match(/\/[sr]\/p-[0-9a-f]{64}\//)) {
          failures.push(`${route} — immutable mode without an /s/ or /r/ cite URL`);
        }
      }
    }
    expect(checked, "no cite block found — the honesty leg would be vacuous").toBeGreaterThan(0);
    expect(failures, failures.join("; ")).toEqual([]);
  });
});
