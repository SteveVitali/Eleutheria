// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// P35.51 (SIG-UI-041, SIG-FIND-005, ADR-155): the page-budgets.json contract —
// the schema, the K0 §4.3 table's numbers VERBATIM (a drifted number fails
// here, not silently in CI), the surface resolution, and the evaluator's
// honest behaviour (over-budget fails, stale gaps fail, a runner that never
// interacts is caught by the effect assertion in the spec).
import { describe, expect, it } from "vitest";
import budgetsJson from "../e2e/page-budgets.json" with { type: "json" };
import {
  budgetForRoute,
  dataCeiling,
  evaluateInitial,
  evaluatePostAction,
  surfaceForT2Route,
} from "../e2e/page-budget-check";
import type { BudgetRow, PageBudgets, PhaseMeasure } from "../e2e/page-budget-check";

const budgets = budgetsJson as PageBudgets;

/** The K0-interactive-architecture §4.3 table, verbatim (KiB = 1024). A budget
 * row drifted from the ratified table fails THIS test — the table is law, not
 * a default to re-decide (ADR-155's change path governs edits). */
const RATIFIED: Record<string, Partial<BudgetRow>> = {
  "types.T0": {
    jsInitialBytes: 0,
    jsAfterActionBytes: null,
    documentMaxBytes: 153600,
    totalInitialMaxBytes: 153600,
    lighthousePerformance: 0.95,
    lighthouseAccessibility: 1.0,
    lcpMs: 1500,
    cls: 0.02,
    tbtMs: 0,
  },
  "types.T1": {
    jsInitialBytes: 20480,
    jsAfterActionBytes: 40960,
    documentMaxBytes: 153600,
    totalInitialMaxBytes: 174080,
    lighthousePerformance: 0.95,
    lighthouseAccessibility: 1.0,
    lcpMs: 1500,
    cls: 0.02,
    tbtMs: 50,
    interactionLatencyMs: 100,
  },
  "t2Surfaces.map": {
    jsInitialBytes: 368640,
    jsAfterActionBytes: 61440,
    documentMaxBytes: 102400,
    totalInitialMaxBytes: 460800,
    lighthousePerformance: 0.75,
    lighthouseAccessibility: 1.0,
    lcpMs: 2500,
    cls: 0.05,
    tbtMs: 350,
    interactionLatencyMs: 200,
  },
  "t2Surfaces.graph": {
    jsInitialBytes: 122880,
    jsAfterActionBytes: 61440,
    documentMaxBytes: 102400,
    totalInitialMaxBytes: 256000,
    lighthousePerformance: 0.9,
    lighthouseAccessibility: 1.0,
    lcpMs: 2000,
    cls: 0.05,
    tbtMs: 200,
    interactionLatencyMs: 200,
  },
  "t2Surfaces.search": {
    jsInitialBytes: 61440,
    jsAfterActionBytes: 40960,
    documentMaxBytes: 102400,
    totalInitialMaxBytes: 184320,
    lighthousePerformance: 0.95,
    lighthouseAccessibility: 1.0,
    lcpMs: 1500,
    cls: 0.02,
    tbtMs: 100,
    interactionLatencyMs: 100,
  },
};

function rowAt(path: string): BudgetRow {
  const [family, key] = path.split(".") as [string, string];
  const holder = (budgets as unknown as Record<string, Record<string, BudgetRow>>)[family];
  return holder[key]!;
}

describe("page-budgets.json (sig.page-budgets/1)", () => {
  it("declares the schema and a row per page type + T2 surface", () => {
    expect(budgets.schema).toBe("sig.page-budgets/1");
    expect(Object.keys(budgets.types).sort()).toEqual(["T0", "T1", "T3"]);
    expect(Object.keys(budgets.t2Surfaces).sort()).toEqual(["graph", "map", "search"]);
  });

  it("carries the K0 §4.3 ratified numbers verbatim", () => {
    for (const [path, expected] of Object.entries(RATIFIED)) {
      const row = rowAt(path);
      for (const [k, v] of Object.entries(expected)) {
        expect(
          (row as unknown as Record<string, unknown>)[k],
          `${path}.${k} drifted from the ratified ${v}`,
        ).toBe(v);
      }
    }
    // The per-interaction data ceilings are verbatim too.
    expect(budgets.types.T1.dataPerInteraction).toEqual({
      kind: "per-interaction",
      maxBytes: 204800,
    });
    expect(budgets.t2Surfaces.map.dataPerInteraction).toEqual({
      kind: "map",
      firstViewMaxBytes: 1572864,
      perPanZoomMaxBytes: 512000,
    });
    expect(budgets.t2Surfaces.graph.dataPerInteraction).toEqual({
      kind: "per-interaction",
      maxBytes: 204800,
    });
    expect(budgets.t2Surfaces.search.dataPerInteraction).toEqual({
      kind: "search",
      perKeystrokeMaxBytes: 51200,
      perResultPageMaxBytes: 40960,
    });
    expect(dataCeiling(budgets.types.T1)).toBe(204800);
    expect(dataCeiling(budgets.t2Surfaces.map)).toBe(512000);
    expect(dataCeiling(budgets.t2Surfaces.search)).toBe(51200);
    expect(dataCeiling(budgets.t2Surfaces.graph)).toBe(204800);
  });

  it("keeps T0 at zero executable JS and T3 free of byte ceilings (ADR-068)", () => {
    expect(budgets.types.T0.jsInitialBytes).toBe(0);
    expect(budgets.types.T0.tbtMs).toBe(0);
    expect(budgets.types.T3.documentMaxBytes).toBeNull();
    expect(budgets.types.T3.lighthouseAccessibility).toBe(1.0);
  });

  it("records every measured gap with ratified ceiling, bound, owner and deferral", () => {
    for (const gap of budgets.measured_gaps) {
      expect(gap.regression_bound).toBeGreaterThan(gap.ratified_ceiling);
      expect(gap.recorded_measure).toBeGreaterThan(gap.ratified_ceiling);
      expect(gap.recorded_measure).toBeLessThanOrEqual(gap.regression_bound);
      expect(gap.deferral).toMatch(/^D-/);
      expect(gap.owner.length).toBeGreaterThan(0);
      expect(gap.note.length).toBeGreaterThan(0);
    }
  });
});

describe("surfaceForT2Route", () => {
  it("resolves the named surfaces and their snapshot forms", () => {
    expect(surfaceForT2Route("/map/")).toBe("map");
    expect(surfaceForT2Route("/network/")).toBe("graph");
    expect(surfaceForT2Route("/explore/")).toBe("graph");
    expect(surfaceForT2Route("/search/")).toBe("search");
    expect(surfaceForT2Route("/s/rel-2026-10/map/")).toBe("map");
    expect(surfaceForT2Route("/s/rel-2026-10/network/")).toBe("graph");
    expect(surfaceForT2Route("/s/rel-2026-10/explore/")).toBe("graph");
    expect(surfaceForT2Route("/s/rel-2026-10/search/")).toBe("search");
  });

  it("fails closed on a T2 route with no budgeted surface", () => {
    expect(() => surfaceForT2Route("/totally-new/")).toThrow(/no budgeted surface/);
  });
});

describe("budgetForRoute", () => {
  it("maps T0/T1/T3 to their type rows and T2 to its surface row", () => {
    expect(budgetForRoute(budgets, { path: "/dispute/", type: "T0" }).row.jsInitialBytes).toBe(0);
    expect(budgetForRoute(budgets, { path: "/sources/", type: "T1" }).row.jsInitialBytes).toBe(
      20480,
    );
    expect(budgetForRoute(budgets, { path: "/map/", type: "T2" }).row.jsInitialBytes).toBe(
      368640,
    );
    expect(budgetForRoute(budgets, { path: "/curate/", type: "T3" }).row.documentMaxBytes).toBeNull();
  });
});

const RES = (kind: string, bytes: number) => ({
  url: `https://x/${kind}-${bytes}`,
  kind: kind as never,
  raw: bytes * 3,
  gzip: bytes,
  brotli: bytes,
});
const M = (resources: ReturnType<typeof RES>[], doc = 1000): PhaseMeasure => ({
  resources,
  documentRaw: doc,
});

describe("evaluateInitial", () => {
  const t0 = budgets.types.T0;
  const t1 = budgets.types.T1;
  const map = budgets.t2Surfaces.map;

  it("fails a synthetic over-budget measurement", () => {
    const m = M([RES("script", 1)], 200000);
    const { violations } = evaluateInitial(budgets, "/dispute/", t0, m);
    expect(violations.map((v) => v.metric)).toContain("documentMaxBytes(raw)");
    expect(violations.map((v) => v.metric)).toContain("jsInitialBytes(gzip)");
    expect(violations.map((v) => v.metric)).toContain("jsInitialBytes(brotli)");
  });

  it("passes a compliant T1 measurement", () => {
    const m = M([RES("script", 20000), RES("style", 5000)], 40000);
    const { violations } = evaluateInitial(budgets, "/sources/", t1, m);
    expect(violations).toEqual([]);
  });

  it("bounds a recorded gap: under bound reports the gap, over bound fails", () => {
    const gap = budgets.measured_gaps.find(
      (g) => g.route === "/map/" && g.metric === "jsInitialBytes",
    )!;
    // 460,000 B: over the ratified 360 KiB script ceiling (gap applies) and
    // pushes the total over its ratified 450 KiB too (that gap applies as
    // well) — the real-world shape both recorded gaps describe.
    const inside = M([RES("script", 460000)], 5000);
    const { violations, gaps } = evaluateInitial(budgets, "/map/", map, inside);
    expect(violations.map((v) => v.metric)).not.toContain("jsInitialBytes(gzip)");
    expect(gaps[0]!.deferral).toBe(gap.deferral);
    const over = M([RES("script", gap.regression_bound + 1)], 5000);
    expect(
      evaluateInitial(budgets, "/map/", map, over).violations.map((v) => v.metric),
    ).toContain("jsInitialBytes(gzip)");
  });

  it("fails a stale gap row once the measure drops under the ratified ceiling", () => {
    const m = M([RES("script", 10000)], 5000);
    const { violations } = evaluateInitial(budgets, "/map/", map, m);
    expect(violations.map((v) => v.metric)).toContain("measured_gaps(jsInitialBytes)");
  });
});

describe("evaluatePostAction", () => {
  it("bounds post-action script and data bytes", () => {
    const t1 = budgets.types.T1;
    const ok = evaluatePostAction(budgets, "/sources/", t1, M([RES("data", 100000), RES("script", 30000)]), 50);
    expect(ok.violations).toEqual([]);
    const over = evaluatePostAction(
      budgets,
      "/sources/",
      t1,
      M([RES("data", 300000), RES("script", 50000)]),
      50,
    );
    expect(over.violations.map((v) => v.metric)).toContain("dataPerInteractionBytes");
    expect(over.violations.map((v) => v.metric)).toContain("jsAfterActionBytes");
    const slow = evaluatePostAction(budgets, "/sources/", t1, M([]), 5000);
    expect(slow.violations.map((v) => v.metric)).toContain("interactionLatencyMs");
  });

  it("applies the search per-keystroke data ceiling", () => {
    const s = budgets.t2Surfaces.search;
    const ok = evaluatePostAction(budgets, "/search/", s, M([RES("data", 50000)]), 80);
    expect(ok.violations).toEqual([]);
    const over = evaluatePostAction(budgets, "/search/", s, M([RES("data", 60000)]), 80);
    expect(over.violations.map((v) => v.metric)).toContain("dataPerInteractionBytes");
  });

  it("bounds a recorded post-action gap and fails over its regression bound", () => {
    // The national-scoped latency gaps bind only under SIG_DATA_SOURCE=national;
    // an unscoped row applies everywhere — synthesise one on a scratch contract.
    const scratch: PageBudgets = JSON.parse(JSON.stringify(budgets));
    scratch.measured_gaps.push({
      route: "/network/",
      metric: "interactionLatencyMs",
      ratified_ceiling: 200,
      recorded_measure: 284,
      regression_bound: 400,
      deferral: "D-TEST-1",
      owner: "test",
      note: "synthetic",
    });
    const g = budgets.t2Surfaces.graph;
    const inside = evaluatePostAction(scratch, "/network/", g, M([]), 300);
    expect(inside.violations).toEqual([]);
    expect(inside.gaps.map((x) => x.metric)).toContain("interactionLatencyMs");
    const over = evaluatePostAction(scratch, "/network/", g, M([]), 500);
    expect(over.violations.map((v) => v.metric)).toContain("interactionLatencyMs");
  });
});
