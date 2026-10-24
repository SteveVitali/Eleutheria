// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// P35.50 (UXK0-1, K0 §4.12 item 2, ADR-155, SIG-UI-036/041): the per-page-type
// script policy, iterated over the DISCOVERED routes (K0 NEW-4) — this spec
// replaces the policy half of islands.spec.ts, with the same or stronger
// assertions:
//
//   T0 record & print — zero `<script` elements, of any kind, ever.
//   T1 content        — only `type="module"` scripts whose `src` is an
//                       allow-listed entry (`t1-module-entries.json`, empty
//                       until a UXK0-4 element lands — the mechanism is this
//                       row's, its members are theirs) plus the hashed Astro
//                       bootstrap (`astro-runtime-script-hashes.json`).
//   T2 explore        — the hashed Astro bootstrap plus `type="module"`
//                       scripts src'd from the build's own content-hashed
//                       `/_astro/` assets; nothing else executable.
//   T3 tools          — ADR-068 owns `/curate/**` script shape (not policed
//                       here); the universal bans still apply.
//   EVERY type        — no inline event-handler attributes (`on*=`) and no
//                       `javascript:` URLs anywhere in the served HTML.
//   `application/ld+json` — JSON-LD is linked files only (D-J3-7's recorded
//                       answer): an inline ld+json script block is a
//                       violation on every type; `<link rel="alternate">` is
//                       not a script element.
//
// The check itself lives in script-policy-check.ts so the unit suite can plant
// a violating fixture and prove the check catches it (SIG-ENG-042).

import { test, expect, type APIRequestContext } from "@playwright/test";
import { DISCOVERED_ROUTES, T0_PAGES, T1_PAGES, T2_PAGES, T3_PAGES } from "./pages";
import { scriptsOf, scriptViolations, universalViolations } from "./script-policy-check";
import runtimeHashes from "./astro-runtime-script-hashes.json" with { type: "json" };

// The T1 module-entry allow-list (K0 §4.12: "only type="module" scripts whose
// src is an allow-listed entry"). Empty by contract: the enhancement kit's
// entries register here as they land (UXK0-4, row-assigned in 11C).
import t1ModuleEntries from "./t1-module-entries.json" with { type: "json" };

const BOOTSTRAP_HASHES = new Set(Object.keys(runtimeHashes.hashes));
const T1_MODULE_ENTRIES = new Set<string>(t1ModuleEntries.entries);

async function htmlOf(request: APIRequestContext, path: string): Promise<string> {
  const res = await request.get(path);
  expect(res.status(), `${path} must resolve`).toBe(200);
  return res.text();
}

test.describe("T0: zero <script> elements on record/print routes", () => {
  for (const path of T0_PAGES) {
    test(`${path} ships no <script>`, async ({ request }) => {
      const html = await htmlOf(request, path);
      expect(html, `${path} is T0 — no <script> element at all`).not.toContain("<script");
      expect(scriptsOf(html)).toEqual([]);
    });
  }
});

test.describe("T1: only allow-listed module entries + the hashed bootstrap", () => {
  for (const path of T1_PAGES) {
    test(`${path} carries no non-allow-listed script`, async ({ request }) => {
      const html = await htmlOf(request, path);
      const scripts = scriptsOf(html);
      const violations = scripts.flatMap((s) =>
        scriptViolations("T1", s, BOOTSTRAP_HASHES, T1_MODULE_ENTRIES),
      );
      expect(violations, `${path}: ${violations.join("; ")}`).toEqual([]);
    });
  }
});

test.describe("T2: hashed bootstrap + content-hashed assets only", () => {
  for (const path of T2_PAGES) {
    test(`${path} ships only recorded bootstrap + /_astro/ module scripts`, async ({
      request,
    }) => {
      const html = await htmlOf(request, path);
      const scripts = scriptsOf(html);
      // The T2 surface DOES ship island scripts (asserted, never loosened).
      expect(scripts.length, `${path} is T2 — island scripts present`).toBeGreaterThan(0);
      const violations = scripts.flatMap((s) =>
        scriptViolations("T2", s, BOOTSTRAP_HASHES, T1_MODULE_ENTRIES),
      );
      expect(violations, `${path}: ${violations.join("; ")}`).toEqual([]);
    });
  }
});

test.describe("universal bans on every discovered route", () => {
  for (const route of DISCOVERED_ROUTES) {
    test(`${route.path} has no on*= handler and no javascript: URL`, async ({ request }) => {
      const html = await htmlOf(request, route.path);
      const { onHandlers, jsUrls } = universalViolations(html);
      expect(onHandlers, `${route.path} inline handlers: ${onHandlers.join(", ")}`).toEqual([]);
      expect(jsUrls, `${route.path} javascript: URLs: ${jsUrls.join(", ")}`).toEqual([]);
    });
  }
});

test.describe("the discovery set itself", () => {
  test("every T2 route is one of the three classified explore surfaces today", () => {
    // Today's built T2 set — the registry's T2 rows are exactly these routes
    // until their migration rows land (/explore/ is registered, not emitted).
    expect([...T2_PAGES].sort()).toEqual(["/map/", "/network/", "/search/"]);
  });

  test("the sweep covers T3 too (universal bans iterate /curate/**)", () => {
    expect(T3_PAGES.length).toBeGreaterThan(0);
    expect(T3_PAGES.every((p) => p.startsWith("/curate/"))).toBe(true);
  });
});
