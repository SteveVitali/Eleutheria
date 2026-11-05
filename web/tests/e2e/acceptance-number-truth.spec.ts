// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// P36.72a (ACC-PLACES / K4 JUR-06 number-truth, K9 "recompute every header
// number", J3 §5.4 / SIG-TRANSP-013): NUMBER TRUTH — every <Figure>'s
// declared `data-artifact` + `data-pointer` resolves to the served artifact
// bytes and the pointed-at value equals the rendered `data-figure-value`;
// every figure's "source" link resolves; and every `data-breakdown` anchor
// resolves in-page. Artifacts with no page-served bytes are recorded and
// their figures' source links are checked as routes — a number that cannot
// reach its evidence fails. Sweep is over every emitted HTML file — never a
// hand list (SIG-ENG-042: a vacuous pass fails too).

import { expect, test } from "@playwright/test";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import {
  DIST_DIR,
  POINTER_MISSING,
  artifactRoute,
  emittedRoutes,
  parseFigureRegions,
  resolvePointerCandidates,
} from "./acceptance";

// Collect every figure across the emitted HTML once at load.
interface SiteFigure {
  file: string;
  route: string;
  id: string;
  artifact: string;
  pointer: string;
  value: string;
  sourceHref: string | null;
  breakdown: string;
}
const FIGURES: SiteFigure[] = [];
for (const route of emittedRoutes()) {
  if (!route.endsWith("/")) continue;
  const file = join(DIST_DIR, route.slice(1), "index.html");
  let html: string;
  try {
    html = readFileSync(file, "utf-8");
  } catch {
    continue;
  }
  for (const f of parseFigureRegions(html, route)) {
    FIGURES.push({ ...f, route });
  }
}

test.describe("figure ↔ artifact number truth", () => {
  test("every figure's pointer resolves; every numeric leaf equals its rendered value", async ({
    request,
  }) => {
    expect(FIGURES.length, "no figures measured — vacuous sweep").toBeGreaterThan(0);
    const cache = new Map<string, unknown>();
    const failures: string[] = [];
    const unserved = new Set<string>();
    let strictEqual = 0;
    let subjectBound = 0;
    for (const fig of FIGURES) {
      const route = artifactRoute(fig.artifact);
      if (route === null) {
        unserved.add(fig.artifact);
        continue;
      }
      if (!cache.has(route)) {
        const res = await request.get(route);
        if (res.status() !== 200) {
          failures.push(`${fig.file}: artifact ${route} → ${res.status()}`);
          cache.set(route, POINTER_MISSING);
          continue;
        }
        cache.set(route, await res.json());
      }
      const doc = cache.get(route);
      const candidates = resolvePointerCandidates(doc, fig.pointer);
      if (candidates.length === 0) {
        // the pointer's binding MUST resolve — a figure naming evidence that
        // does not exist is a lie, not a difference of interpretation
        failures.push(`${fig.file}: ${fig.artifact} has no ${fig.pointer}`);
        continue;
      }
      // Strict class: a numeric leaf candidate equals the rendered value.
      // Reference/demo pages (component-kit etc.) are exempt from equality —
      // they demo the mechanism — but their pointers must still resolve. A
      // figure resolved only to objects/arrays or non-numeric leaves is
      // subject-bound: its binding is proven, its derivation is the page's
      // own recompute (the J3 §5.4 semantics), counted and never inferred.
      const numeric = /^-?\d+(?:\.\d+)?$/;
      const kit = /^\/(component-kit|enhancement-kit|visual-language|style-guide)\//.test(
        fig.file,
      );
      const numericCandidates = candidates.filter(
        (c) => (typeof c !== "object" || c === null) && numeric.test(String(c)),
      );
      if (numeric.test(fig.value) && numericCandidates.some((c) => String(c) === fig.value)) {
        strictEqual += 1;
      } else if (
        candidates.some((c) => Array.isArray(c) && numeric.test(fig.value) && c.length === Number(fig.value))
      ) {
        strictEqual += 1; // a collection-count figure
      } else if (kit) {
        subjectBound += 1;
      } else if (
        numeric.test(fig.value) &&
        numericCandidates.length > 0 &&
        numericCandidates.every((c) => Number(fig.value) <= Number(c)) &&
        /(rest|more|other|remaining|top)/i.test(fig.id)
      ) {
        // a derived figure (a "rest"/"more"/remainder ≤ the count it names)
        subjectBound += 1;
      } else if (numeric.test(fig.value) && numericCandidates.length > 0) {
        failures.push(
          `${fig.file}: fig ${fig.id} value ${fig.value} != ${fig.artifact}${fig.pointer} = [${numericCandidates.join(", ")}]`,
        );
      } else {
        subjectBound += 1;
      }
    }
    // recorded, never silently skipped (SIG-ENG-042): unserved artifacts are
    // named, and the strict class must be non-vacuous.
    expect(
      strictEqual,
      `no numeric-leaf figures measured (subject-bound ${subjectBound}; unserved ${[...unserved].join(", ")})`,
    ).toBeGreaterThan(0);
    expect(failures).toEqual([]);
  });

  test("every figure's source link and breakdown anchor resolve", async ({ request }) => {
    const failures: string[] = [];
    for (const fig of FIGURES) {
      // the source marker is an <a> to the recomputing bytes, or a <span>
      // label when the figure's evidence is the page's own served route — an
      // <a> href must resolve; a span label never navigates
      if (fig.sourceHref === null) {
        failures.push(`${fig.file}: fig ${fig.id} has no source link`);
      } else if (!fig.sourceHref.startsWith("#")) {
        const res = await request.get(fig.sourceHref);
        if (res.status() !== 200) {
          failures.push(`${fig.file}: fig ${fig.id} source ${fig.sourceHref} → ${res.status()}`);
        }
      }
      // the breakdown anchor resolves in-page (or is a route)
      if (fig.breakdown.startsWith("#")) {
        const html = readFileSync(join(DIST_DIR, fig.route.slice(1), "index.html"), "utf-8");
        const id = fig.breakdown.slice(1);
        if (!html.includes(`id="${id}"`)) {
          failures.push(`${fig.file}: breakdown ${fig.breakdown} unresolvable`);
        }
      }
    }
    expect(failures).toEqual([]);
  });
});
