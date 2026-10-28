// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// P36.19 (UXK0-3, K0 §4.8/§4.12, SIG-UI-096, ADR-223): the CSP e2e. Three legs:
//
//   1. every DISCOVERED route ships exactly one conforming <meta> policy —
//      the static document layer (per-page sha384 hashes + the T0 'none'
//      tightening); the check itself lives in csp-policy-check.ts so the unit
//      suite proves it catches a violating policy, never assumes.
//   2. a browser sweep navigates representative pages — all three T2 islands
//      included — with a securitypolicyviolation collector installed at
//      document start and asserts ZERO events: the built pages, and the
//      islands' real runtime (MapLibre workers, pmtiles range fetches, CSSOM
//      styling), produce no violation under their own policy.
//   3. the violating leg: an injected inline <script>, <style>, style=
//      attribute and eval() are each BLOCKED and each fires its expected
//      directive's event — and a CSP-free control document proves the
//      harness itself detects (SIG-ENG-042: a green leg is evidence, not
//      silence).
//
// The served-header half of the split (HSTS, frame-ancestors, the
// Permissions-Policy /map/ exception, the standalone-SVG policy) lives in
// ops/web/sig-security.conf and is asserted by tests/ops + the composed
// release-serving suite — astro preview serves no headers here and none are
// claimed.

import { createHash } from "node:crypto";
import { test, expect, type APIRequestContext } from "@playwright/test";
import { DISCOVERED_ROUTES } from "./pages";
import { cspViolations } from "./csp-policy-check";

const htmlOf = async (request: APIRequestContext, path: string): Promise<string> => {
  const res = await request.get(path);
  expect(res.ok(), `${path} must serve (${res.status()})`).toBeTruthy();
  return res.text();
};

test.describe("csp meta policy — every discovered route", () => {
  for (const route of DISCOVERED_ROUTES) {
    test(`${route.path} (${route.type}) ships exactly the K0 §4.8 policy`, async ({
      request,
    }) => {
      const html = await htmlOf(request, route.path);
      const problems = cspViolations(route.type, html);
      expect(problems, `${route.path}: ${problems.join("; ")}`).toEqual([]);
    });
  }
});

// The collector runs at document start (CDP evaluation is exempt from page
// CSP — the listener itself is never the thing under test).
const COLLECTOR = `window.__sigCspViolations = [];
document.addEventListener("securitypolicyviolation", (e) => {
  window.__sigCspViolations.push(
    (e.effectiveDirective || "?") + "|" + (e.blockedURI || "inline") + "|" + (e.violatedDirective || "?"),
  );
});`;

const violations = async (page: import("@playwright/test").Page): Promise<string[]> =>
  page.evaluate(() => (window as unknown as { __sigCspViolations?: string[] }).__sigCspViolations ?? []);

test.describe("zero violations under the page's own policy", () => {
  const CASES: Array<{ path: string; ready?: { testid: string; attr?: string } }> = [
    { path: "/" },
    { path: "/dispute/" },
    { path: "/dossier/oklahoma-city/print/" },
    { path: "/404.html" },
    { path: "/map/", ready: { testid: "map-island", attr: "data-ready" } },
    { path: "/network/", ready: { testid: "network-island" } },
    { path: "/search/", ready: { testid: "search-island" } },
  ];
  for (const c of CASES) {
    test(`${c.path} produces no securitypolicyviolation`, async ({ page }) => {
      await page.addInitScript(COLLECTOR);
      await page.goto(c.path, { waitUntil: "networkidle" });
      if (c.ready) {
        const el = page.getByTestId(c.ready.testid);
        if (c.ready.attr) {
          await expect(el).toHaveAttribute(c.ready.attr, "true", { timeout: 20_000 });
        } else {
          await expect(el).toBeVisible({ timeout: 20_000 });
        }
      }
      const found = await violations(page);
      expect(found, `${c.path} fired CSP violations: ${found.join("; ")}`).toEqual([]);
    });
  }
});

test.describe("violations are blocked AND reported (the harness detects)", () => {
  test.beforeEach(async ({ page }) => {
    await page.addInitScript(COLLECTOR);
    await page.goto("/", { waitUntil: "networkidle" });
  });

  test("an injected inline <script> is blocked (script-src-elem)", async ({ page }) => {
    await page.evaluate(() => {
      const s = document.createElement("script");
      s.textContent = "window.__cspProbe = 1";
      document.head.appendChild(s);
    });
    expect(await page.evaluate(() => (window as { __cspProbe?: number }).__cspProbe)).toBeUndefined();
    const found = await violations(page);
    expect(found.some((v) => v.startsWith("script-src")), found.join("; ")).toBe(true);
  });

  test("an injected <style> element is blocked (style-src-elem)", async ({ page }) => {
    await page.evaluate(() => {
      const st = document.createElement("style");
      st.textContent = "body { color: rgb(255, 0, 0) }";
      document.head.appendChild(st);
    });
    const color = await page.evaluate(() => getComputedStyle(document.body).color);
    expect(color).not.toBe("rgb(255, 0, 0)");
    const found = await violations(page);
    expect(found.some((v) => v.startsWith("style-src")), found.join("; ")).toBe(true);
  });

  test("a style= attribute is blocked (style-src-attr 'none')", async ({ page }) => {
    await page.evaluate(() => {
      document.body.setAttribute("style", "color: rgb(255, 0, 0)");
    });
    const color = await page.evaluate(() => getComputedStyle(document.body).color);
    expect(color).not.toBe("rgb(255, 0, 0)");
    const found = await violations(page);
    expect(found.some((v) => v.startsWith("style-src-attr")), found.join("; ")).toBe(true);
  });

  test("eval() is blocked (no 'unsafe-eval')", async ({ browser }) => {
    // CDP evaluation is exempt from page CSP, so the eval must be attempted
    // by a REAL document script. A fresh page gets a planted meta carrying
    // the sha384 of exactly the script that attempts eval — that script
    // runs (the hash admits it), the eval() it calls does not (no
    // 'unsafe-eval'), and the violation is recorded. The check pins the
    // real page's token set in leg 1; this proves the platform blocks.
    const probe = 'try{eval("window.__cspEval=1");window.__cspEval=9}catch(e){window.__cspEval=0}';
    // addInitScript doesn't run on setContent documents — the collector is
    // itself a hashed inline script in the planted policy (parsed before
    // the probe, so the listener exists when the eval attempt violates).
    const collector =
      'window.__sigCspViolations=[];' +
      'document.addEventListener("securitypolicyviolation",' +
      'e=>window.__sigCspViolations.push(e.effectiveDirective+"|"+(e.blockedURI||"inline")))';
    const hashOf = (s: string) => createHash("sha384").update(s).digest("base64");
    const fresh = await browser.newPage();
    try {
      await fresh.setContent(
        `<html><head><meta http-equiv="content-security-policy" ` +
          `content="default-src 'none'; ` +
          `script-src 'sha384-${hashOf(collector)}' 'sha384-${hashOf(probe)}'">` +
          `<script>${collector}</script></head>` +
          `<body><script>${probe}</script></body></html>`,
      );
      expect(
        await fresh.evaluate(() => (window as { __cspEval?: number }).__cspEval),
      ).toBe(0);
      // Violation events dispatch asynchronously — poll, never read once.
      await expect
        .poll(() => violations(fresh), { timeout: 5_000 })
        .toContainEqual(expect.stringMatching(/^script-src/));
    } finally {
      await fresh.close();
    }
  });

  test("control: the same injection executes on a CSP-free document", async ({
    browser,
  }) => {
    // The harness itself is proven: a FRESH page (setContent would inherit
    // the navigated document's policy container) carries no policy, the
    // injected script executes, and no violation is recorded — a green
    // violating leg is never a silent pass.
    const fresh = await browser.newPage();
    try {
      await fresh.addInitScript(COLLECTOR);
      await fresh.setContent("<html><head></head><body><p>control</p></body></html>");
      await fresh.evaluate(() => {
        const s = document.createElement("script");
        s.textContent = "window.__cspProbe = 1";
        document.head.appendChild(s);
      });
      expect(
        await fresh.evaluate(() => (window as { __cspProbe?: number }).__cspProbe),
      ).toBe(1);
      expect(await violations(fresh)).toEqual([]);
    } finally {
      await fresh.close();
    }
  });
});
