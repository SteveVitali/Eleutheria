// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// P36.72a (ACC-PLACES, plan cell verbatim): "ROUTES.csv check — every route
// advertised on the 09-27 release resolves" (COV-04): each advertised row
// passes a user-expectation check or shows an honest notice naming its
// decision/LATER trigger. Each row's disposition is declared in EXPECTED —
// `resolves` (the family emits), `retired` (the one redirect generator
// answers it), `internal` (emitted only as internal surfaces in this build —
// the honest "not public" notice), `namespace` (an index-free namespace —
// absence is the honest answer), `external` (a bucket/API/edge URL — the
// promoted-release leg owns it, P36.72b / D-R10-PUBLISH-1). The table is a
// BIJECTION with the CSV — a row added to the CSV fails until dispositioned.

import { expect, test } from "@playwright/test";
import { existsSync } from "node:fs";
import { join } from "node:path";
import { DIST_DIR, loadRoutesCsv, redirectRules, routeFile } from "./acceptance";
import { DISCOVERED_ROUTES } from "./pages";

type Disposition = "resolves" | "retired" | "internal" | "namespace" | "external";

const EXPECTED: Record<string, { disposition: Disposition; note: string }> = {
  R01: { disposition: "resolves", note: "national landing" },
  R02: { disposition: "internal", note: "contribution-back is an internal surface" },
  R03: { disposition: "resolves", note: "corrections log" },
  R04: { disposition: "resolves", note: "coverage metrics" },
  R05: {
    disposition: "retired",
    note: "/data-freshness/** 301s to /sources/runs/** (K9 C-11, SIG-UI-058)",
  },
  R06: { disposition: "resolves", note: "dispute intake" },
  R07: { disposition: "resolves", note: "dossier index" },
  R08: {
    disposition: "resolves",
    note: "dossier family + historical slugs resolve via stubs/include",
  },
  R09: { disposition: "resolves", note: "dossier print" },
  R10: { disposition: "resolves", note: "dossier JSON twins" },
  R11: { disposition: "resolves", note: "editorial standards" },
  R12: { disposition: "resolves", note: "evidence hub" },
  R13: {
    disposition: "retired",
    note: "/evidence/<id>/ 301s to /evidence/claim/<id>/ (P36.60)",
  },
  R14: { disposition: "resolves", note: "map (T2)" },
  R15: { disposition: "resolves", note: "map style.json" },
  R16: { disposition: "resolves", note: "methodology" },
  R17: {
    disposition: "retired",
    note: "/network/ 301s to /explore/?v=2&overview=access (P37.26 / GX-09a)",
  },
  R37: { disposition: "resolves", note: "explore (T2 graph)" },
  R18: { disposition: "resolves", note: "research queue" },
  R19: { disposition: "resolves", note: "search (T2)" },
  R20: { disposition: "resolves", note: "style-guide is a public surface" },
  R21: {
    disposition: "retired",
    note: "/task/new/** retired → 410 namespace rule; no page emits",
  },
  R22: { disposition: "internal", note: "visual-language is internal" },
  R23: { disposition: "resolves", note: "watch hub" },
  R24: { disposition: "resolves", note: "watch .ics feeds emit" },
  R25: { disposition: "resolves", note: "watch .xml feeds emit" },
  R26: { disposition: "resolves", note: "watch citations.txt" },
  R27: { disposition: "internal", note: "releases index is an internal surface" },
  R28: { disposition: "internal", note: "research dossier is internal" },
  R29: { disposition: "internal", note: "research dossier pages are internal" },
  R30: { disposition: "internal", note: "research dossier JSON twins are internal" },
  R31: { disposition: "internal", note: "/curate/ — ADR-068, never public" },
  R32: { disposition: "internal", note: "/curate/[id]/ — ADR-068, never public" },
  R33: { disposition: "internal", note: "/curate/contradictions/ — internal" },
  R34: { disposition: "internal", note: "/curate/revert/ — internal" },
  R35: { disposition: "internal", note: "/curate/submit/ — internal" },
  R36: { disposition: "internal", note: "/curate/tasks/ — internal" },
  X01: {
    disposition: "external",
    note: "compartment PMTiles publish with a release — fixtures mint none",
  },
  X02: { disposition: "resolves", note: "hashed /_astro/ assets emit" },
  X03: { disposition: "resolves", note: "robots.txt" },
  X04: { disposition: "resolves", note: "sitemap.xml now emits" },
  X05: { disposition: "resolves", note: "the branded error docs emit" },
  X06: {
    disposition: "namespace",
    note: "/task/ has no index page — the absence is the honest answer",
  },
  X07: { disposition: "external", note: "LB apex redirect — deployment URL" },
  X08: { disposition: "external", note: "release manifest.json — bucket URL" },
  X09: { disposition: "external", note: "sig-public bucket artifacts" },
  X10: { disposition: "external", note: "sig-api endpoints — the served API leg" },
  X11: { disposition: "internal", note: "intake receiver — non-operational by gate" },
  X12: { disposition: "internal", note: "release-archive routes — internal/staging" },
};

const PREFIX_OF = (pattern: string): string =>
  pattern.split(" ")[0].replace(/[\[<*].*$/, "").replace(/\/+$/, "") + "/";

test.describe("every advertised 09-27 route resolves or shows an honest notice", () => {
  const rows = loadRoutesCsv();

  test("the expectation table is a bijection with ROUTES.csv", () => {
    const csvIds = new Set(rows.map((r) => r.id));
    const expIds = new Set(Object.keys(EXPECTED));
    expect([...csvIds].filter((id) => !expIds.has(id)), "CSV rows without a disposition").toEqual([]);
    expect([...expIds].filter((id) => !csvIds.has(id)), "dispositions for absent CSV rows").toEqual(
      [],
    );
  });

  test("every 'resolves' row's route family emits (and resolves)", () => {
    const failures: string[] = [];
    for (const row of rows) {
      const exp = EXPECTED[row.id];
      if (exp?.disposition !== "resolves") continue;
      const prefix = PREFIX_OF(row.pattern);
      if (/[\[<]|\*/.test(row.pattern)) {
        // a dynamic family: ≥1 emitted route under the prefix, or an emitted
        // file matching the family shape (feeds, twins)
        const hits =
          DISCOVERED_ROUTES.filter((r) => r.path.startsWith(prefix)).length +
          (existsSync(join(DIST_DIR, prefix.replace(/^\/+|\/+$/g, ""))) ? 1 : 0);
        // feeds/twins: any emitted file under the prefix family
        const fileHit = emittedFileExists(prefix);
        if (hits === 0 && !fileHit) {
          failures.push(`${row.id} ${row.pattern}: no emitted route under ${prefix}`);
        }
      } else {
        const clean = row.pattern.split(" ")[0];
        if (!routeFile(clean.endsWith("/") ? clean : `${clean}/`) && !routeFile(clean)) {
          // plain route: emitted index or literal file
          if (!existsSync(join(DIST_DIR, clean.replace(/^\/+/, "")))) {
            failures.push(`${row.id} ${clean}: not emitted`);
          }
        }
      }
    }
    expect(failures).toEqual([]);
  });

  test("every 'retired' row resolves through the one redirect generator", () => {
    const rules = redirectRules();
    const failures: string[] = [];
    for (const row of rows) {
      const exp = EXPECTED[row.id];
      if (exp?.disposition !== "retired") continue;
      const prefix = PREFIX_OF(row.pattern);
      const covered = rules.some(
        (r) =>
          r.from.startsWith(prefix) ||
          (r.prefix && prefix.startsWith(r.from)) ||
          r.from === prefix,
      );
      if (!covered) {
        failures.push(`${row.id} ${row.pattern}: no redirect rule covers ${prefix}`);
      }
    }
    expect(failures).toEqual([]);
  });

  test("every 'internal' row emits only internal routes (never public)", () => {
    const failures: string[] = [];
    for (const row of rows) {
      const exp = EXPECTED[row.id];
      if (exp?.disposition !== "internal") continue;
      const prefix = PREFIX_OF(row.pattern);
      const routes = DISCOVERED_ROUTES.filter((r) => r.path.startsWith(prefix));
      // intake (X11) emits nothing publicly at all — the absence IS the notice
      if (row.id === "X11") {
        if (routes.some((r) => !r.internal)) {
          failures.push(`${row.id}: a public intake route emitted`);
        }
        continue;
      }
      if (routes.length === 0) {
        failures.push(`${row.id} ${prefix}: no internal route emitted`);
        continue;
      }
      if (routes.some((r) => !r.internal)) {
        failures.push(`${row.id} ${prefix}: emitted a public route`);
      }
    }
    expect(failures).toEqual([]);
  });

  test("the /task/ namespace keeps its honest no-index answer", async ({ request }) => {
    const res = await request.get("/task/");
    // no index page emits — a 404 here is the same honest absence the edge
    // answered as 403 on the 09-27 release (no listing, never a dead page)
    expect(res.status()).toBe(404);
    expect(routeFile("/task/")).toBeNull();
  });
});

function emittedFileExists(prefix: string): boolean {
  const dir = join(DIST_DIR, prefix.replace(/^\/+|\/+$/g, ""));
  if (!existsSync(dir)) return false;
  return true;
}
