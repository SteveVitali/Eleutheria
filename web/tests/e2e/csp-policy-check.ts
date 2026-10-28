// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// P36.19 (UXK0-3, K0 §4.8, SIG-UI-096): the pure CSP-policy check — shared by
// csp.spec.ts (which drives it over every discovered route) and the unit
// suite (which proves a hand-authored violating policy is caught — the check
// itself is tested, never assumed, same convention as script-policy-check.ts).
//
// The shape asserted is K0 §4.8 verbatim, realised as meta ∩ header:
//   - every page: the emitted <meta> exists exactly once; every source token
//     is 'self' / 'none' / a sha*-hash / data: / blob: — never a host, never
//     a scheme beyond data:/blob:, never 'unsafe-inline'/'unsafe-eval'/'*';
//   - the *-attr 'none' pair, object-src/base-uri/form-action present;
//   - header-only directives (frame-ancestors, sandbox, report-*) never in
//     meta — they ride ops/web/sig-security.conf instead;
//   - T0: `default-src 'none'` and NO script-src/connect-src/worker-src (the
//     build hook tightens the emitted meta — a page it missed fails here);
//   - T1/T2/T3: `default-src 'self'` + script-src 'self' <hashes>.

import type { PageType } from "../../src/lib/page-types";
import { policyDirectives } from "../../src/lib/csp";

/** Every meta tag the sweep counts — Astro emits exactly one per page. */
const META_TAG_RE = /<meta\s+http-equiv="content-security-policy"/gi;
const META_CONTENT_RE =
  /<meta\s+http-equiv="content-security-policy"\s+content="([^"]*)"/i;

/** The source tokens the static policy may ever name — never a host. */
const ALLOWED_TOKEN =
  /^'(self|none|sha(?:256|384|512)-[A-Za-z0-9+/=]+)'$|^data:$|^blob:$/;

/** Directives a <meta> cannot express — finding one here is drift, not config. */
const HEADER_ONLY_DIRECTIVES = [
  "frame-ancestors",
  "sandbox",
  "report-uri",
  "report-to",
];

/** The meta tag's CSP value, or null when absent. */
export function cspMetaOf(html: string): string | null {
  return html.match(META_CONTENT_RE)?.[1] ?? null;
}

/**
 * Every reason a route's emitted CSP meta violates K0 §4.8 (empty =
 * conforming). `type` is the ADR-155 registry classification — T0 asserts the
 * tightened 'none' row the build hook writes.
 */
export function cspViolations(type: PageType, html: string): string[] {
  const problems: string[] = [];
  const metaCount = (html.match(META_TAG_RE) ?? []).length;
  if (metaCount === 0) {
    return ["missing <meta http-equiv=\"content-security-policy\"> — security.csp must emit one per page"];
  }
  if (metaCount > 1) {
    problems.push(`${metaCount} CSP meta tags — exactly one is emitted`);
  }
  const dirs = policyDirectives(cspMetaOf(html) ?? "");

  for (const name of HEADER_ONLY_DIRECTIVES) {
    if (dirs.has(name)) {
      problems.push(`${name} in the meta policy — that directive is response-header only (ops/web/sig-security.conf)`);
    }
  }

  for (const [name, tokens] of dirs) {
    for (const token of tokens) {
      if (!ALLOWED_TOKEN.test(token)) {
        problems.push(`${name} carries ${token} — no hosts, no 'unsafe-*', no '*' (SIG-UI-040: no third-party runtime origins)`);
      }
    }
  }

  const expect = (name: string, want: string[]): void => {
    const got = dirs.get(name);
    if (got === undefined) {
      problems.push(`${name} missing from the emitted policy`);
    } else if (got.join(" ") !== want.join(" ")) {
      problems.push(`${name} is "${got.join(" ")}" — expected "${want.join(" ")}"`);
    }
  };

  expect("script-src-attr", ["'none'"]);
  expect("style-src-attr", ["'none'"]);
  expect("object-src", ["'none'"]);
  expect("base-uri", ["'none'"]);
  expect("form-action", ["'self'"]);
  expect("font-src", ["'self'"]);
  if (!dirs.has("style-src")) problems.push("style-src missing from the emitted policy");
  if (!dirs.has("img-src")) problems.push("img-src missing from the emitted policy");

  if (type === "T0") {
    // K0 §4.8's record/print row — the build hook rewrites the emitted meta.
    expect("default-src", ["'none'"]);
    expect("img-src", ["'self'", "data:"]);
    for (const name of ["script-src", "script-src-elem", "connect-src", "worker-src"]) {
      if (dirs.has(name)) {
        problems.push(`${name} present on a T0 page — the tightened policy drops it (K0 §4.8)`);
      }
    }
  } else {
    expect("default-src", ["'self'"]);
    expect("img-src", ["'self'", "data:", "blob:"]);
    expect("connect-src", ["'self'"]);
    expect("worker-src", ["'self'", "blob:"]);
    const scriptSrc = dirs.get("script-src");
    if (scriptSrc === undefined) {
      problems.push("script-src missing — a script-bearing page needs 'self' + its tracked hashes");
    } else {
      if (scriptSrc[0] !== "'self'") {
        problems.push(`script-src starts "${scriptSrc[0]}" — 'self' first, hashes after`);
      }
      for (const token of scriptSrc.slice(1)) {
        if (!/^'sha(?:256|384|512)-[A-Za-z0-9+/=]+'$/.test(token)) {
          problems.push(`script-src carries ${token} — only 'self' + content hashes (K0 §4.8: never 'unsafe-inline')`);
        }
      }
    }
  }
  return problems;
}
