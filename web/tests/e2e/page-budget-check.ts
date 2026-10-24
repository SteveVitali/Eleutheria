// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// P35.51 (SIG-UI-041, SIG-FIND-005, ADR-155): the pure measurement/evaluation
// helpers behind budget.spec.ts — kept free of Playwright so the SAME logic is
// unit-tested with synthetic inputs (an over-budget measurement must fail; a
// declared interaction that produced no effect must be caught) and so the wire
// script (scripts/measure-page-budgets.mjs) mirrors the same rules.
//
// The numbers are K0-interactive-architecture §4.3's ratified table verbatim in
// page-budgets.json (sig.page-budgets/1) — never hard-code a budget here; this
// module only interprets the committed file.

import type { DiscoveredRoute } from "./pages";

export type T2Surface = "map" | "graph" | "search";

export interface DataPerInteraction {
  kind: "per-interaction" | "map" | "search";
  maxBytes?: number;
  firstViewMaxBytes?: number;
  perPanZoomMaxBytes?: number;
  perKeystrokeMaxBytes?: number;
  perResultPageMaxBytes?: number;
}

export interface BudgetRow {
  jsInitialBytes: number | null;
  jsAfterActionBytes: number | null;
  documentMaxBytes: number | null;
  totalInitialMaxBytes: number | null;
  dataPerInteraction: DataPerInteraction | null;
  lighthousePerformance: number | null;
  lighthouseAccessibility: number | null;
  lcpMs: number | null;
  cls: number | null;
  tbtMs: number | null;
  interactionLatencyMs: number | null;
}

export interface MeasuredGap {
  route: string;
  metric: string;
  ratified_ceiling: number;
  recorded_measure: number;
  regression_bound: number;
  deferral: string;
  owner: string;
  note: string;
  /**
   * The build the gap was measured under — `"national"` bounds a real-scale
   * overage that exists only in the national-fixture build (the committed
   * fixture build may measure under the ratified ceiling without the row
   * reading stale). Absent = the gap applies to every build.
   */
  data_source?: string;
}

export interface PageBudgets {
  schema: string;
  types: Record<"T0" | "T1" | "T3", BudgetRow>;
  t2Surfaces: Record<T2Surface, BudgetRow>;
  interactions: Record<string, { kind: string; description: string }>;
  measured_gaps: MeasuredGap[];
}

/** Resource classes the wire measure separates (initial-transfer vs data). */
export type ResourceKind = "script" | "document" | "style" | "font" | "image" | "data" | "other";

export interface ResourceMeasure {
  url: string;
  kind: ResourceKind;
  /** Transferred body bytes as measured. */
  raw: number;
  gzip: number;
  brotli: number;
}

export interface PhaseMeasure {
  resources: ResourceMeasure[];
  /** The HTML document bytes (transferred). */
  documentRaw: number;
}

export interface BudgetViolation {
  route: string;
  metric: string;
  measured: number;
  ceiling: number;
  message: string;
}

/** A measured gap report line — loud, never hidden. */
export interface GapReport {
  route: string;
  metric: string;
  measured: number;
  ratified: number;
  bound: number;
  deferral: string;
}

/**
 * The T2 surface a route belongs to. Derived structurally — the snapshot
 * prefix `/s/<pub>/` is stripped and the first segment names the surface
 * (`network` and `explore` are both the graph surface). An unrecognised T2
 * route throws — a new T2 surface MUST land a budget row in page-budgets.json
 * (which is ADR-155's amendment path), never slip through unbudgeted.
 */
export function surfaceForT2Route(path: string): T2Surface {
  const stripped = path.replace(/^\/s\/[^/]+/, "");
  const seg = stripped.split("/").filter(Boolean)[0] ?? "";
  if (seg === "map") return "map";
  if (seg === "explore" || seg === "network") return "graph";
  if (seg === "search") return "search";
  throw new Error(
    `T2 route ${path} resolves to no budgeted surface (map|graph|search) — ` +
      "a new T2 surface requires a page-budgets.json row and an ADR-155 amendment",
  );
}

/** The budget row a discovered route is measured against. T3 carries no byte
 * budgets (ADR-068 owns the curation surface) — a11y is still asserted. */
export function budgetForRoute(
  budgets: PageBudgets,
  route: Pick<DiscoveredRoute, "path" | "type">,
): { row: BudgetRow; surface: T2Surface | null } {
  if (route.type === "T2") {
    const surface = surfaceForT2Route(route.path);
    return { row: budgets.t2Surfaces[surface], surface };
  }
  return { row: budgets.types[route.type as "T0" | "T1" | "T3"], surface: null };
}

/** Sum helpers — script-family and full-transfer totals per codec. */
export function scriptTotal(m: PhaseMeasure, codec: "raw" | "gzip" | "brotli"): number {
  return m.resources
    .filter((r) => r.kind === "script")
    .reduce((acc, r) => acc + r[codec], 0);
}

export function totalTransfer(m: PhaseMeasure, codec: "raw" | "gzip" | "brotli"): number {
  const resourceBytes = m.resources
    .filter((r) => r.kind !== "data")
    .reduce((acc, r) => acc + r[codec], 0);
  return resourceBytes + m.documentRaw;
}

export function dataBytes(m: PhaseMeasure, codec: "raw" | "gzip" | "brotli"): number {
  return m.resources
    .filter((r) => r.kind === "data")
    .reduce((acc, r) => acc + r[codec], 0);
}

const DATA_KIND_CEILINGS: Record<
  NonNullable<DataPerInteraction["kind"]>,
  (d: DataPerInteraction) => number | null
> = {
  "per-interaction": (d) => d.maxBytes ?? null,
  map: (d) => d.perPanZoomMaxBytes ?? null,
  search: (d) => d.perKeystrokeMaxBytes ?? null,
};

/** The per-interaction data ceiling for the row (pan/zoom, keystroke, expansion). */
export function dataCeiling(row: BudgetRow): number | null {
  const d = row.dataPerInteraction;
  if (!d) return null;
  return DATA_KIND_CEILINGS[d.kind]?.(d) ?? null;
}

/**
 * Evaluate the initial-load measurement against the row. `measured_gaps`
 * applies per metric: the ratified ceiling still reports (loud), the
 * regression bound is the hard gate, and a gap row left after the bundle
 * drops under the ratified ceiling is itself a failure (stale record).
 */
/**
 * The data source the current measurement runs against — the Playwright
 * process inherits `SIG_DATA_SOURCE` from the leg that spawned it, so the
 * national leg's `SIG_DATA_SOURCE=national playwright test` evaluates the
 * national-scoped gaps and the default leg evaluates the unscoped ones.
 */
export function measurementSource(): string {
  return process.env.SIG_DATA_SOURCE ?? "fixtures";
}

export function evaluateInitial(
  budgets: PageBudgets,
  route: string,
  row: BudgetRow,
  m: PhaseMeasure,
): { violations: BudgetViolation[]; gaps: GapReport[] } {
  const violations: BudgetViolation[] = [];
  const gaps: GapReport[] = [];

  const gapFor = (metric: string) => {
    const source = measurementSource();
    const matching = budgets.measured_gaps.filter(
      (g) =>
        g.route === route &&
        g.metric === metric &&
        (g.data_source === undefined || g.data_source === source),
    );
    // A source-scoped row overrides the unscoped one — the national leg binds
    // its own real-scale bound, never the fixtures leg's.
    return (
      matching.find((g) => g.data_source === source) ??
      matching.find((g) => g.data_source === undefined) ??
      null
    );
  };

  /**
   * One metric's hard gate. With no measured_gap the ratified ceiling is the
   * gate. With one: the ratified ceiling is still the law — reported every run
   * — while the recorded regression_bound gates, and a gap row that outlives
   * the bundle's drop under the ratified ceiling fails as a stale record.
   */
  const reportedGaps = new Set<string>();
  const push = (metric: string, codec: string, measured: number, ceiling: number | null) => {
    const label = `${metric}(${codec})`;
    const gap = gapFor(metric);
    if (gap) {
      if (!reportedGaps.has(metric)) {
        reportedGaps.add(metric);
        gaps.push({
          route,
          metric,
          measured,
          ratified: gap.ratified_ceiling,
          bound: gap.regression_bound,
          deferral: gap.deferral,
        });
      }
      if (measured > gap.regression_bound) {
        violations.push({
          route,
          metric: label,
          measured,
          ceiling: gap.regression_bound,
          message:
            `${route}: ${label} = ${measured} B exceeds the recorded regression bound ` +
            `${gap.regression_bound} B (${gap.deferral}; ratified ceiling ${gap.ratified_ceiling} B stands)`,
        });
      }
      return;
    }
    if (ceiling !== null && measured > ceiling) {
      violations.push({
        route,
        metric: label,
        measured,
        ceiling,
        message: `${route}: ${label} = ${measured} B exceeds the ratified ceiling ${ceiling} B`,
      });
    }
  };

  // A measured_gaps row that outlives the bundle's drop under its ratified
  // ceiling is a stale record — fail so it is removed in the same change.
  const staleCheck = (metric: string, measures: number[]) => {
    const gap = gapFor(metric);
    if (gap && Math.max(...measures) <= gap.ratified_ceiling) {
      violations.push({
        route,
        metric: `measured_gaps(${metric})`,
        measured: Math.max(...measures),
        ceiling: gap.ratified_ceiling,
        message:
          `${route}: ${metric} now measures under the ratified ceiling ` +
          `${gap.ratified_ceiling} B — the measured_gaps row (${gap.deferral}) is stale; remove it`,
      });
    }
  };

  // Script-family and full-transfer ceilings, per codec — the §4.3 table is
  // codec-neutral ("Executable JS" measured compressed): gzip AND brotli are
  // both measured and both bounded.
  const scriptGz = scriptTotal(m, "gzip");
  const scriptBr = scriptTotal(m, "brotli");
  push("jsInitialBytes", "gzip", scriptGz, row.jsInitialBytes);
  push("jsInitialBytes", "brotli", scriptBr, row.jsInitialBytes);
  push("documentMaxBytes", "raw", m.documentRaw, row.documentMaxBytes);
  const totalGz = totalTransfer(m, "gzip");
  const totalBr = totalTransfer(m, "brotli");
  push("totalInitialMaxBytes", "gzip", totalGz, row.totalInitialMaxBytes);
  push("totalInitialMaxBytes", "brotli", totalBr, row.totalInitialMaxBytes);
  staleCheck("jsInitialBytes", [scriptGz, scriptBr]);
  staleCheck("documentMaxBytes", [m.documentRaw]);
  staleCheck("totalInitialMaxBytes", [totalGz, totalBr]);

  // The T2 map surface's first-view data budget: the tile ranges the first
  // national view streams (archive header + leaf directories + the visible
  // pyramid tiles) against the ratified §4.3 firstViewMaxBytes row — declared
  // in the contract and previously unasserted.
  const firstView = row.dataPerInteraction?.firstViewMaxBytes ?? null;
  if (firstView !== null) {
    push("firstViewMaxBytes", "gzip", dataBytes(m, "gzip"), firstView);
    staleCheck("firstViewMaxBytes", [dataBytes(m, "gzip")]);
  }

  return { violations, gaps };
}

/**
 * Evaluate the post-interaction measurement: scripts fetched only after the
 * user action are bounded by jsAfterActionBytes; fetched data bytes by the
 * row's data-per-interaction ceiling; the latency by interactionLatencyMs
 * (measured under 4× CPU throttle by the caller).
 */
export function evaluatePostAction(
  budgets: PageBudgets,
  route: string,
  row: BudgetRow,
  post: PhaseMeasure,
  latencyMs: number | null,
): { violations: BudgetViolation[]; gaps: GapReport[] } {
  const violations: BudgetViolation[] = [];
  const gaps: GapReport[] = [];
  const reportedGaps = new Set<string>();

  const gapFor = (metric: string) => {
    const source = measurementSource();
    const matching = budgets.measured_gaps.filter(
      (g) =>
        g.route === route &&
        g.metric === metric &&
        (g.data_source === undefined || g.data_source === source),
    );
    return (
      matching.find((g) => g.data_source === source) ??
      matching.find((g) => g.data_source === undefined) ??
      null
    );
  };

  const push = (metric: string, measured: number, ceiling: number | null) => {
    if (ceiling === null) return;
    const gap = gapFor(metric);
    if (gap) {
      if (!reportedGaps.has(metric)) {
        reportedGaps.add(metric);
        gaps.push({
          route,
          metric,
          measured,
          ratified: gap.ratified_ceiling,
          bound: gap.regression_bound,
          deferral: gap.deferral,
        });
      }
      if (measured > gap.regression_bound) {
        violations.push({
          route,
          metric,
          measured,
          ceiling: gap.regression_bound,
          message:
            `${route}: post-action ${metric} = ${measured} exceeds the recorded ` +
            `regression bound ${gap.regression_bound} (${gap.deferral}; ratified ${gap.ratified_ceiling} stands)`,
        });
      }
      return;
    }
    if (measured > ceiling) {
      violations.push({
        route,
        metric,
        measured,
        ceiling,
        message: `${route}: post-action ${metric} = ${measured} exceeds ${ceiling}`,
      });
    }
  };
  push("jsAfterActionBytes", scriptTotal(post, "gzip"), row.jsAfterActionBytes);
  push("jsAfterActionBytes", scriptTotal(post, "brotli"), row.jsAfterActionBytes);
  push("dataPerInteractionBytes", dataBytes(post, "gzip"), dataCeiling(row));
  if (latencyMs !== null) push("interactionLatencyMs", latencyMs, row.interactionLatencyMs);
  return { violations, gaps };
}
