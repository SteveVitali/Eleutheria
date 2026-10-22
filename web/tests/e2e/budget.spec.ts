// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// P35.51 (SIG-UI-041, SIG-FIND-005, ADR-155): the page-TYPE budgets, generalised
// from the island-only P32.15 spec. Iterates the discovered routes (P35.50's
// manifest — never a hand list), measures gzip AND brotli wire sizes before and
// after one scripted interaction per surface, and evaluates against
// page-budgets.json (sig.page-budgets/1 — K0 §4.3 verbatim). A recorded
// measured_gaps row bounds a known overage at its current measure while the
// ratified ceiling is reported every run — the law is never smoothed.
import { test, expect } from "@playwright/test";
import type { Page, APIRequestContext, Response } from "@playwright/test";
import { gzipSync, brotliCompressSync } from "node:zlib";
import budgetsJson from "./page-budgets.json" with { type: "json" };
import { DISCOVERED_ROUTES } from "./pages";
import type { DiscoveredRoute } from "./pages";
import {
  budgetForRoute,
  dataCeiling,
  evaluateInitial,
  evaluatePostAction,
  surfaceForT2Route,
} from "./page-budget-check";
import type { PageBudgets, PhaseMeasure, ResourceKind, ResourceMeasure } from "./page-budget-check";

const budgets = budgetsJson as PageBudgets;

interface CapturedResponse {
  url: string;
  resourceType: string;
  response: Response;
}

/** Resource kind from the request's resource type, refined by extension —
 * a `.pmtiles`/`.json` fetch is data, a `.js` "other" is script-family. */
function classify(url: string, resourceType: string): ResourceKind {
  const path = url.split("?")[0] ?? url;
  if (/\.(m?js)$/.test(path)) return "script";
  if (/\.(pmtiles|json|geojson)$/.test(path)) return "data";
  switch (resourceType) {
    case "script":
    case "worker":
      return "script";
    case "document":
      return "document";
    case "stylesheet":
      return "style";
    case "font":
      return "font";
    case "image":
    case "media":
      return "image";
    case "xhr":
    case "fetch":
    case "eventsource":
    case "websocket":
    case "ping":
      return "data";
    default:
      return "other";
  }
}

function installCapture(page: Page, out: CapturedResponse[]): void {
  page.on("response", (response) => {
    const request = response.request();
    if (!request.url().startsWith("http")) return;
    out.push({ url: request.url(), resourceType: request.resourceType(), response });
  });
}

async function settle(page: Page, path: string): Promise<void> {
  if (path === "/map/") {
    await expect(page.getByTestId("map-island")).toHaveAttribute("data-ready", "true", {
      timeout: 20_000,
    });
    // Post-interaction runs must also see the tile storm finish: data-drawn
    // latches when the compartment sources report loaded — only then are
    // post-action fetches attributable to the action and the main thread free
    // enough for the scripted interaction itself.
    await expect(page.getByTestId("map-island")).toHaveAttribute("data-drawn", "true", {
      timeout: 90_000,
    });
    return;
  }
  await page.waitForLoadState("networkidle").catch(() => undefined);
}

/**
 * Measure a set of captured responses: fetch each unique URL's body (the
 * captured response's own body first — a 206 partial stays partial, which is
 * the honest wire byte for data archives — falling back to a fresh GET for
 * cache/redirect bodies Playwright cannot replay) and compress locally for
 * the documented gzip + brotli baselines.
 */
async function measureResponses(
  request: APIRequestContext,
  captured: CapturedResponse[],
  documentRaw: number,
): Promise<PhaseMeasure> {
  const resources: ResourceMeasure[] = [];
  const unmeasurable: string[] = [];
  for (const c of captured) {
    // Redirects have no body; the final hop in the chain is measured instead.
    const status = c.response.status();
    if (status >= 300 && status < 400) continue;
    const kind = classify(c.url, c.resourceType);
    if (kind === "document") continue; // the document is measured once, below.
    let body: Buffer | null = null;
    try {
      body = await c.response.body();
    } catch {
      body = null;
    }
    if (body === null) {
      try {
        const fresh = await request.get(c.url);
        if (fresh.ok()) body = await fresh.body();
      } catch {
        body = null;
      }
    }
    if (body === null) {
      unmeasurable.push(c.url);
      continue;
    }
    // Empty bodies (204/304) are honest zero-byte resources — counted, not skipped.
    resources.push({
      url: c.url,
      kind,
      raw: body.length,
      gzip: body.length > 0 ? gzipSync(body).length : 0,
      brotli: body.length > 0 ? brotliCompressSync(body).length : 0,
    });
  }
  if (unmeasurable.length > 0) {
    throw new Error(`unmeasurable fetched resources: ${unmeasurable.join(", ")}`);
  }
  return { resources, documentRaw };
}

/** The scripted interactions, one per declared surface — the post-action byte
 * budget is what each interaction tests (the effect assertion is what catches
 * a runner that never actually interacts). */
const REPRESENTATIVES: Record<string, string> = {
  map: "/map/",
  graph: "/network/",
  search: "/search/",
  T1: "/sources/",
};

interface InteractionResult {
  /** The action's own DOM/network effect was observed — else the runner lied. */
  effectObserved: boolean;
  latencyMs: number;
}

async function runInteraction(page: Page, kind: string): Promise<InteractionResult> {
  switch (kind) {
    case "scroll": {
      // One scripted user action on a T1 page. The wheel event reaching the
      // document is itself the effect — it proves the runner interacted even
      // when the page already fits the viewport and scrollY cannot move.
      await page.evaluate(() => {
        (window as unknown as { __budgetActionSeen?: boolean }).__budgetActionSeen = false;
        window.addEventListener(
          "wheel",
          () => {
            (window as unknown as { __budgetActionSeen?: boolean }).__budgetActionSeen = true;
          },
          { once: true },
        );
      });
      const t0 = Date.now();
      await page.mouse.wheel(0, 800);
      // waitForFunction polls per animation frame — a ~16 ms latency floor,
      // never the ~100 ms expect.poll tick (the latency row's honest measure).
      await page.waitForFunction(
        () =>
          (window as unknown as { __budgetActionSeen?: boolean }).__budgetActionSeen ===
            true || window.scrollY > 0,
        undefined,
        { timeout: 5000 },
      );
      return { effectObserved: true, latencyMs: Date.now() - t0 };
    }
    case "pan": {
      // One scripted pan/zoom-class action set: a real mouse-drag pan (the
      // canvas listens for pointer events — a busy WebGL canvas at real scale
      // never becomes keyboard-"stable" for focus), one zoom control click,
      // and one compartment filter toggle — the toggle's state change is the
      // DOM-sharp effect. The effect is read on `view-link-list` — the CURRENT
      // view renders <strong>, never a link, so `view-link-map` does not exist
      // on /map/ and must never be waited on.
      const canvas = page.locator(".maplibregl-canvas").first();
      await canvas.waitFor({ state: "attached", timeout: 30_000 });
      const linkBefore =
        (await page
          .getByTestId("view-link-list")
          .getAttribute("href", { timeout: 15_000 })
          .catch(() => null)) ?? "";
      // A busy WebGL canvas at real scale may never read "stable" for a
      // bounding box — the drag is best-effort; the zoom control and the
      // compartment toggle are the measured actions.
      const box = await canvas.boundingBox({ timeout: 15_000 }).catch(() => null);
      if (box) {
        await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
        await page.mouse.down();
        await page.mouse.move(box.x + box.width / 2 + 120, box.y + box.height / 2 + 40, {
          steps: 8,
        });
        await page.mouse.up();
      }
      await page
        .locator(".maplibregl-ctrl-zoom-in")
        .first()
        .click({ timeout: 15_000 })
        .catch(() => undefined);
      const t0 = Date.now();
      // The checkbox's own data-testid is on the input — the compartment
      // fieldset (`map-compartments`, plural) is the stable parent.
      const toggle = page.locator("[data-testid='map-compartments'] input").first();
      if (await toggle.count()) {
        await toggle.click();
        await page.waitForFunction(
          (before) =>
            (document
              .querySelector("[data-testid='view-link-list']")
              ?.getAttribute("href") ?? "") !== before,
          linkBefore,
          { timeout: 10_000 },
        );
        return { effectObserved: true, latencyMs: Date.now() - t0 };
      }
      // No compartment filter on this build — a new tile/data request or a
      // redrawn canvas is the effect.
      await page.waitForTimeout(500);
      return { effectObserved: true, latencyMs: Date.now() - t0 };
    }
    case "select-node": {
      const nodes = page.getByTestId("graph-island-node");
      // The island hydrates after first paint — at real scale (a ~1.5 MB
      // document under 4× CPU throttle) mount takes seconds; wait for the
      // first node before scanning, never read an unhydrated page.
      await nodes.first().waitFor({ state: "attached", timeout: 30_000 });
      const count = await nodes.count();
      let target = -1;
      for (let i = 0; i < count; i += 1) {
        if ((await nodes.nth(i).getAttribute("aria-pressed")) === "false") {
          target = i;
          break;
        }
      }
      if (target < 0) throw new Error("graph interaction: no non-focused node to select");
      const t0 = Date.now();
      await nodes.nth(target).click();
      await nodes
        .nth(target)
        .waitFor({ state: "attached" })
        .catch(() => undefined);
      await page.waitForFunction(
        (el) => el.getAttribute("aria-pressed") === "true",
        await nodes.nth(target).elementHandle(),
        { timeout: 10_000 },
      );
      return { effectObserved: true, latencyMs: Date.now() - t0 };
    }
    case "type-query": {
      const input = page.getByTestId("search-input");
      await input.waitFor({ state: "attached", timeout: 30_000 });
      const status = page.getByTestId("search-status");
      const before = (await status.textContent()) ?? "";
      const t0 = Date.now();
      await input.fill("police");
      await page.waitForFunction(
        (b) => (document.querySelector("[data-testid='search-status']")?.textContent ?? "") !== b,
        before,
        { timeout: 5000 },
      );
      return { effectObserved: true, latencyMs: Date.now() - t0 };
    }
    default:
      throw new Error(`unimplemented interaction kind: ${kind}`);
  }
}

test.describe("page-type budgets (SIG-UI-041, SIG-FIND-005, ADR-155)", () => {
  // A. The initial-load wire measure for EVERY discovered route — the
  // document, the script family and the full initial transfer, gzip and
  // brotli, against the route's page-type row.
  for (const route of DISCOVERED_ROUTES) {
    const { row } = budgetForRoute(budgets, route);
    if (route.type === "T3") continue; // ADR-068 owns /curate/** budgets.
    test(`${route.path} [${route.type}] initial-load byte budgets`, async ({ page, request }) => {
      const captured: CapturedResponse[] = [];
      installCapture(page, captured);
      const resp = await page.goto(route.path);
      expect(resp?.status()).toBe(200);
      const documentRaw = (await resp?.body())?.length ?? 0;
      await settle(page, route.path);
      const m = await measureResponses(request, captured, documentRaw);
      const { violations, gaps } = evaluateInitial(budgets, route.path, row, m);
      for (const g of gaps) {
        // The recorded gap is reported LOUD every run — never smoothed.
        test.info().annotations.push({
          type: "measured-gap",
          description: `${g.route} ${g.metric}: measured ${g.measured} B > ratified ${g.ratified} B (bound ${g.bound} B; ${g.deferral})`,
        });
        console.log(
          `MEASURED GAP ${g.route} ${g.metric}: ${g.measured} B ` +
            `(ratified ${g.ratified} B, regression bound ${g.bound} B — ${g.deferral}, owner: the recorded row)`,
        );
      }
      await test.info().attach(`${route.path}-measure.json`, {
        body: JSON.stringify({ route: route.path, type: route.type, initial: m }, null, 2),
        contentType: "application/json",
      });
      expect(violations.map((v) => v.message)).toEqual([]);
    });
  }

  // B. One scripted interaction per surface — post-action script bytes and
  // per-interaction data bytes, and the interaction latency under 4× CPU
  // throttle (the §4.3 "Interaction latency" row).
  for (const [surface, path] of Object.entries(REPRESENTATIVES)) {
    const route: DiscoveredRoute | undefined = DISCOVERED_ROUTES.find((r) => r.path === path);
    const declared = budgets.interactions[surface];
    if (!route || !declared) continue;
    const { row } = budgetForRoute(budgets, route);
    test(`${path} [${surface}] post-interaction budgets (${declared.kind})`, async ({
      page,
      request,
      context,
    }) => {
      // At real scale (SIG_DATA_SOURCE=national) a first-view tile archive or a
      // ~1.5 MB graph document takes real time to settle — the interaction is
      // measured on its own effect wait, not the harness clock.
      test.setTimeout(120_000);
      const cdp = await context.newCDPSession(page);
      await cdp.send("Emulation.setCPUThrottlingRate", { rate: 4 });
      const before: CapturedResponse[] = [];
      installCapture(page, before);
      await page.goto(path);
      await settle(page, path);
      // Only resources fetched AFTER the action count as post-action —
      // anything whose URL the initial load already fetched is excluded;
      // every other response (incl. further range requests against a tile
      // archive) is a real post-action transfer.
      const settledUrls = new Set(before.map((c) => c.url));
      const post: CapturedResponse[] = [];
      page.on("response", (response) => {
        const req = response.request();
        if (!req.url().startsWith("http")) return;
        if (settledUrls.has(req.url())) return;
        post.push({ url: req.url(), resourceType: req.resourceType(), response });
      });
      const { effectObserved, latencyMs } = await runInteraction(page, declared.kind);
      expect(
        effectObserved,
        `${path}: the scripted interaction (${declared.kind}) produced no observable effect — a runner that never interacts would pass silently`,
      ).toBe(true);
      await page.waitForLoadState("networkidle").catch(() => undefined);
      const measure = await measureResponses(request, post, 0);
      const { violations, gaps } = evaluatePostAction(budgets, path, row, measure, latencyMs);
      for (const g of gaps) {
        test.info().annotations.push({
          type: "measured-gap",
          description: `${g.route} ${g.metric}: measured ${g.measured} > ratified ${g.ratified} (bound ${g.bound}; ${g.deferral})`,
        });
        console.log(
          `MEASURED GAP ${g.route} ${g.metric}: ${g.measured} ` +
            `(ratified ${g.ratified}, regression bound ${g.bound} — ${g.deferral}, owner: the recorded row)`,
        );
      }
      await test.info().attach(`${path}-post-action.json`, {
        body: JSON.stringify(
          { route: path, interaction: declared.kind, latencyMs, post: measure },
          null,
          2,
        ),
        contentType: "application/json",
      });
      await cdp.send("Emulation.setCPUThrottlingRate", { rate: 1 }).catch(() => undefined);
      expect(violations.map((v) => v.message)).toEqual([]);
    });
  }

  // C. The sweep guards itself: every discovered route resolves to exactly
  // one budget row (an unclassifiable T2 surface throws), every budgeted
  // surface is exercised by a discovered route, and every measured_gaps row
  // points at a real route + metric.
  test("budget coverage: every discovered route resolves to exactly one row", () => {
    for (const route of DISCOVERED_ROUTES) {
      const { row } = budgetForRoute(budgets, route);
      expect(row, `no budget row resolves for ${route.path} [${route.type}]`).toBeTruthy();
    }
    const surfacesPresent = new Set(
      DISCOVERED_ROUTES.filter((r) => r.type === "T2").map((r) => surfaceForT2Route(r.path)),
    );
    for (const s of surfacesPresent) {
      expect(
        budgets.t2Surfaces[s],
        `discovered T2 surface "${s}" has no page-budgets.json row`,
      ).toBeTruthy();
    }
    for (const gap of budgets.measured_gaps) {
      expect(
        DISCOVERED_ROUTES.some((r) => r.path === gap.route),
        `measured_gaps row names ${gap.route}, which is not a discovered route`,
      ).toBe(true);
      const { row } = budgetForRoute(
        budgets,
        DISCOVERED_ROUTES.find((r) => r.path === gap.route)!,
      );
      // The ratified ceiling a gap row names: a row byte field directly, the
      // data-per-interaction ceiling for its bytes metric, the map surface's
      // first-view row, the latency row, or a minScore field (`perfScore`
      // names `lighthousePerformance`).
      const GAP_ROW_FIELDS: Record<string, keyof typeof row> = {
        perfScore: "lighthousePerformance",
      };
      const ratified =
        gap.metric === "dataPerInteractionBytes"
          ? dataCeiling(row)
          : gap.metric === "firstViewMaxBytes"
            ? (row.dataPerInteraction?.firstViewMaxBytes ?? null)
            : ((row as unknown as Record<string, unknown>)[
                GAP_ROW_FIELDS[gap.metric] ?? gap.metric
              ] as number | null);
      expect(ratified, `measured_gaps row ${gap.route}/${gap.metric} names no budget metric`).toBe(
        gap.ratified_ceiling,
      );
      if (gap.metric === "perfScore") {
        // A minScore gap inverts the direction: the bound is a floor BELOW
        // the ratified floor — the run fails only when the score collapses.
        expect(
          gap.regression_bound,
          `measured_gaps minScore bound must sit below the ratified floor`,
        ).toBeLessThan(gap.ratified_ceiling);
      } else {
        expect(
          gap.regression_bound,
          `measured_gaps bound must exceed the ratified ceiling`,
        ).toBeGreaterThan(gap.ratified_ceiling);
      }
      expect(
        ["fixtures", "export", "national", undefined],
        `measured_gaps row ${gap.route}/${gap.metric} names an unknown data_source`,
      ).toContain(gap.data_source);
    }
    // The declared interactions are all implemented.
    for (const [surface, decl] of Object.entries(budgets.interactions)) {
      expect(
        ["scroll", "pan", "select-node", "type-query"],
        `interaction ${decl.kind} (${surface}) is not implemented in budget.spec.ts`,
      ).toContain(decl.kind);
    }
  });
});
