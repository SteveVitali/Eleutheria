// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * P36.19 (UXK0-3, K0 §4.8, SIG-ENG-042): the CSP machinery unit tests —
 * the T0 tightening transform in src/lib/csp.ts and the policy check in
 * tests/e2e/csp-policy-check.ts are proven on hand-authored policies,
 * never assumed. A conforming planted policy passes; a host token, an
 * unsafe source, a missing directive, a header-only directive in meta, or
 * an untightened T0 policy each fail loud.
 */

import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import {
  policyDirectives,
  tightenPolicyForType,
  tightenT0Document,
} from "../../src/lib/csp";
import { cspMetaOf, cspViolations } from "../e2e/csp-policy-check";

// The shape Astro emits — same directive set every page, hashes varying.
const EMITTED =
  "default-src 'self';img-src 'self' data: blob:;connect-src 'self';" +
  "worker-src 'self' blob:;font-src 'self';object-src 'none';base-uri 'none';" +
  "form-action 'self'; script-src 'self' 'sha384-AAA=' 'sha384-BBB='; " +
  "script-src-attr 'none'; style-src 'self' 'sha384-CCC='; style-src-attr 'none';";

const page = (policy: string | null): string =>
  policy === null
    ? "<!doctype html><html><head></head><body>x</body></html>"
    : `<!doctype html><html><head><meta http-equiv="content-security-policy" content="${policy}"></head><body>x</body></html>`;

describe("policyDirectives", () => {
  it("parses directive names and source tokens", () => {
    const dirs = policyDirectives(EMITTED);
    expect(dirs.get("default-src")).toEqual(["'self'"]);
    expect(dirs.get("script-src")).toEqual(["'self'", "'sha384-AAA='", "'sha384-BBB='"]);
    expect(dirs.get("img-src")).toEqual(["'self'", "data:", "blob:"]);
  });
});

describe("tightenPolicyForType — K0 §4.8's T0 row", () => {
  it("drops the script/connect/worker surface and default-src to 'none'", () => {
    const dirs = policyDirectives(tightenPolicyForType("T0", EMITTED));
    expect(dirs.get("default-src")).toEqual(["'none'"]);
    for (const name of ["script-src", "script-src-elem", "connect-src", "worker-src"]) {
      expect(dirs.has(name), `${name} must be absent on T0`).toBe(false);
    }
    expect(dirs.get("img-src")).toEqual(["'self'", "data:"]);
    // The denials stay explicit — style hashes the page actually tracks stay too.
    expect(dirs.get("style-src-attr")).toEqual(["'none'"]);
    expect(dirs.get("script-src-attr")).toEqual(["'none'"]);
    expect(dirs.get("object-src")).toEqual(["'none'"]);
    expect(dirs.get("base-uri")).toEqual(["'none'"]);
    expect(dirs.get("form-action")).toEqual(["'self'"]);
    expect(dirs.get("font-src")).toEqual(["'self'"]);
  });

  it("leaves T1/T2/T3 policies untouched", () => {
    for (const t of ["T1", "T2", "T3"] as const) {
      expect(tightenPolicyForType(t, EMITTED)).toBe(EMITTED);
    }
  });

  it("tightenT0Document rewrites only the meta content", () => {
    const html = page(EMITTED);
    const out = tightenT0Document(html);
    expect(out).not.toBe(html);
    expect(cspMetaOf(out)).toBe(tightenPolicyForType("T0", EMITTED));
    expect(out).toContain("<body>x</body>");
    // A page without the meta is a no-op (the e2e sweep asserts presence).
    expect(tightenT0Document(page(null))).toBe(page(null));
  });
});

describe("cspViolations — the check itself is proven", () => {
  it("a conforming T1 policy passes", () => {
    expect(cspViolations("T1", page(EMITTED))).toEqual([]);
  });

  it("a conforming T2 policy passes", () => {
    expect(cspViolations("T2", page(EMITTED))).toEqual([]);
  });

  it("a tightened T0 policy passes", () => {
    expect(cspViolations("T0", page(tightenPolicyForType("T0", EMITTED)))).toEqual([]);
  });

  it("the untightened emitted policy FAILS on T0 (the hook's patch is asserted)", () => {
    const problems = cspViolations("T0", page(EMITTED));
    expect(problems.join("; ")).toContain("default-src");
    expect(problems.join("; ")).toContain("script-src");
  });

  it("a missing meta is a violation", () => {
    expect(cspViolations("T1", page(null))).toEqual([
      'missing <meta http-equiv="content-security-policy"> — security.csp must emit one per page',
    ]);
  });

  it("a duplicate meta is a violation", () => {
    const html = page(EMITTED).replace("</head>", `${page(EMITTED).match(/<meta[^>]*>/)![0]}</head>`);
    const problems = cspViolations("T1", html);
    expect(problems.join("; ")).toContain("CSP meta tags");
  });

  it("'unsafe-inline', 'unsafe-eval' and '*' are caught", () => {
    for (const bad of ["'unsafe-inline'", "'unsafe-eval'", "*"]) {
      const policy = EMITTED.replace("'sha384-AAA='", bad);
      const problems = cspViolations("T1", page(policy));
      expect(problems.join("; ")).toContain(bad);
    }
  });

  it("a third-party origin is caught (no third-party runtime origins)", () => {
    const policy = EMITTED.replace("'self' data: blob:", "'self' https://cdn.example.com");
    const problems = cspViolations("T1", page(policy));
    expect(problems.join("; ")).toContain("https://cdn.example.com");
  });

  it("frame-ancestors in meta is caught (header-only)", () => {
    const problems = cspViolations("T1", page(`${EMITTED} frame-ancestors 'none';`));
    expect(problems.join("; ")).toContain("frame-ancestors");
  });

  it("a missing attr 'none' pair is caught", () => {
    const policy = EMITTED.replace("style-src-attr 'none';", "");
    const problems = cspViolations("T1", page(policy));
    expect(problems.join("; ")).toContain("style-src-attr");
  });

  it("script-src carrying a non-hash token after 'self' is caught", () => {
    const policy = EMITTED.replace("'sha384-AAA='", "'strict-dynamic'");
    const problems = cspViolations("T1", page(policy));
    expect(problems.join("; ")).toContain("strict-dynamic");
  });

  it("the committed built tree is already conforming (dist is current)", () => {
    // The dist the e2e suite serves — the same check the sweep applies,
    // proven against real bytes when a build exists in the workspace.
    const root = fileURLToPath(new URL("../../dist", import.meta.url));
    let html: string;
    try {
      html = readFileSync(`${root}/index.html`, "utf-8");
    } catch {
      return; // no dist in a bare workspace — the e2e sweep owns that leg
    }
    expect(cspViolations("T1", html)).toEqual([]);
  });
});
