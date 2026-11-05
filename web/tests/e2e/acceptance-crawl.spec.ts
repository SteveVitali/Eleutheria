// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// P36.72a (ACC-PLACES / K4 JUR-06 §11 ATs — SIG-JUR-D05/D08/D09, K5 DSRC-06
// D02): THE CRAWL — every discovered route and every emitted file answers,
// every historical URL resolves through the one redirect generator (a stub
// where the static fallback serves, a declared include rule where the edge
// carries it), and no bare id ships as visible text. A bare id or a 404
// fails; nothing is skipped silently (SIG-ENG-042).

import { expect, test } from "@playwright/test";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import {
  BINARY_EXT,
  DIST_DIR,
  emittedRoutes,
  redirectRules,
  routeFile,
  servedRoute,
  visibleTextMinusIdSpans,
} from "./acceptance";
import { DISCOVERED_ROUTES } from "./pages";

const EMITTED = emittedRoutes();
const RULES = redirectRules();

test.describe("the zero-404 crawl (SIG-JUR-D09)", () => {
  test("every discovered HTML route answers 200", async ({ request }) => {
    const failures: string[] = [];
    for (const r of DISCOVERED_ROUTES) {
      const res = await request.get(r.path);
      if (res.status() !== 200) failures.push(`${r.path} → ${res.status()}`);
    }
    expect(failures, `${failures.length} discovered routes not 200`).toEqual([]);
  });

  test("every emitted non-HTML file answers", async ({ request }) => {
    const failures: string[] = [];
    for (const route of EMITTED) {
      if (route.endsWith("/")) continue; // HTML routes covered above
      const res = BINARY_EXT.test(route)
        ? await request.fetch(route, { method: "HEAD" })
        : await request.get(route);
      if (res.status() !== 200) failures.push(`${route} → ${res.status()}`);
    }
    expect(failures, `${failures.length} emitted files not 200`).toEqual([]);
  });

  test("a never-published route answers the branded 404 — never a bare miss", async ({
    page,
    request,
  }) => {
    const res = await request.get("/this-route-was-never-published/");
    expect(res.status()).toBe(404);
    await page.goto("/this-route-was-never-published/");
    // the branded error document, not a bare server page
    await expect(page.locator("main")).toBeVisible();
  });

  test("slashless forms never answer different content (edge normalization recorded)", async ({
    request,
  }) => {
    // The static preview has no slash-normalization layer — the edge does
    // (ROUTES.csv R08 observed the deployed 301; the include carry is
    // D-P36.35-1's leg). What the crawl must guarantee is that a slashless
    // form NEVER resolves to different content — it either resolves to the
    // same route's page or answers the honest 404.
    for (const bare of [
      "/dossier/usa/ok",
      "/dossier/usa/ok/oklahoma-city-4064000",
      "/sources/okc_camera_registry",
    ]) {
      const res = await request.get(bare);
      expect([200, 404]).toContain(res.status());
      if (res.status() === 200) {
        const html = await res.text();
        expect(html).toContain("<h1");
      }
    }
  });
});

test.describe("every historical URL resolves (SIG-JUR-D09, SIG-UI-058)", () => {
  test("every conf rule names a resolvable end-state", () => {
    const failures: string[] = [];
    const unemittedTargets: string[] = [];
    let resolvedTargets = 0;
    let stubs = 0;
    let includeOnly = 0;
    for (const rule of RULES) {
      if (rule.prefix) {
        // a prefix rule is a namespace disposition (410 etc.) — assert no
        // emitted page shadows it under the prefix
        const shadow = routeFile(rule.from);
        if (shadow) failures.push(`${rule.from} prefix rule shadowed by emitted page`);
        continue;
      }
      if (rule.target !== null) {
        // a 3xx landing on an emitted route is fully verified; a target the
        // fixture corpus does not publish (a successor entity never minted
        // here) is recorded — the edge leg owns the full-set probe
        if (!routeFile(rule.target)) {
          unemittedTargets.push(`${rule.from} → ${rule.target}`);
        } else {
          resolvedTargets += 1;
        }
      }
      if (rule.tryFile !== null) {
        if (!routeFile(rule.tryFile)) failures.push(`${rule.from} try_files ${rule.tryFile} missing`);
      }
      const stub = routeFile(rule.from);
      if (stub) {
        stubs += 1;
        if (stub.endsWith(".html")) {
          const html = readFileSync(join(DIST_DIR, stub), "utf-8");
          const isStub =
            html.includes('http-equiv="refresh"') ||
            html.includes("-stub") ||
            html.includes("noindex") ||
            html.includes("id-stub");
          if (!isStub) failures.push(`${rule.from} emitted page is not a stub/tombstone`);
        }
      } else {
        includeOnly += 1;
        // include-only rules resolve at the edge — the edge leg (D-P36.35-1)
        // probes the real statuses; here the rule must still declare one
        if (rule.status === null) failures.push(`${rule.from} declares no resolution`);
      }
    }
    expect(failures).toEqual([]);
    // fail loud if the mechanism shrinks to nothing (SIG-ENG-042); the
    // un-emitted-target set is recorded in the message, never asserted empty
    // in fixture scope
    expect(stubs + includeOnly).toBeGreaterThan(0);
    expect(
      resolvedTargets,
      `no 3xx target emitted — vacuous coverage (un-emitted: ${unemittedTargets.length})`,
    ).toBeGreaterThan(0);
  });

  test("stub-emitted historical URLs serve 200 stub pages on the static fallback", async ({
    request,
  }) => {
    const failures: string[] = [];
    for (const rule of RULES) {
      if (rule.prefix) continue;
      const stub = routeFile(rule.from);
      if (!stub) continue;
      const res = await request.get(servedRoute(stub));
      if (res.status() !== 200) failures.push(`${rule.from} stub → ${res.status()}`);
    }
    expect(failures).toEqual([]);
  });
});

test.describe("bare ids (SIG-JUR-D08, SIG-DSRC-D02)", () => {
  test("no dossier page's <h1> is a bare code, key or slug", async ({ request }) => {
    // dossier pages = routes with a sig.dossier JSON twin (the twin set is the
    // emitted dossier set — derived, never a hand list)
    const failures: string[] = [];
    const twins = EMITTED.filter(
      (p) => p.startsWith("/dossier/") && p.endsWith(".json") && !p.endsWith("/index.json"),
    );
    const BARE_CODE = /^[A-Z]{2}(-[A-Z0-9]{1,3})?$|^\d{2,7}$|^[a-z]+:[a-z0-9_.-]+$/i;
    for (const twinPath of twins) {
      const pagePath = twinPath.slice(0, -".json".length) + "/";
      const res = await request.get(pagePath);
      if (res.status() !== 200) {
        failures.push(`${twinPath} twin's page ${pagePath} → ${res.status()}`);
        continue;
      }
      const html = await res.text();
      const h1 = /<h1[^>]*>([\s\S]*?)<\/h1>/.exec(html);
      if (!h1) {
        failures.push(`${pagePath} has no <h1>`);
        continue;
      }
      const text = h1[1].replace(/<[^>]+>/g, "").trim();
      const slug = pagePath.split("/").filter(Boolean).pop() ?? "";
      if (BARE_CODE.test(text) || text === slug) {
        failures.push(`${pagePath} <h1> is a bare id: ${text}`);
      }
    }
    expect(failures).toEqual([]);
  });

  test("no source id ships as visible text outside code/sig-mut spans", async () => {
    const sourcesDoc = JSON.parse(
      readFileSync(join(DIST_DIR, "artifact/transparency/sources.json"), "utf-8"),
    ) as { sources: { source_id: string }[] };
    const ids = sourcesDoc.sources.map((s) => s.source_id);
    expect(ids.length).toBeGreaterThan(0);
    const failures: string[] = [];
    for (const route of EMITTED) {
      if (!route.endsWith("/")) continue; // HTML routes only
      const file = routeFile(route);
      if (!file) continue;
      const html = readFileSync(join(DIST_DIR, file), "utf-8");
      const text = visibleTextMinusIdSpans(html);
      for (const id of ids) {
        const re = new RegExp(`(?<![\\w-])${id}(?![\\w-])`);
        if (re.test(text)) {
          failures.push(`${route} shows bare id ${id}`);
          break;
        }
      }
    }
    expect(failures).toEqual([]);
  });
});
