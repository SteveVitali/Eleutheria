// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

import { describe, expect, it } from "vitest";
import {
  assertCoverageMetric,
  assertCoverageMetrics,
  assertFreshnessRow,
  evaluableLabel,
  isNotEvaluable,
  isNotRecorded,
  NOT_EVALUABLE,
  NOT_RECORDED,
} from "../../src/lib/metrics";
import type { CoverageMetric, FreshnessRow } from "../../src/lib/metrics";
import { COVERAGE_METRICS, FRESHNESS_ROWS } from "../../src/lib/corrections-methodology-fixture";

describe("data freshness (§32.4, SIG-METRIC-007)", () => {
  it("every fixture row carries all four required fields + volatility class", () => {
    for (const row of FRESHNESS_ROWS) expect(() => assertFreshnessRow(row)).not.toThrow();
  });

  it("rejects a row missing a required field", () => {
    const bad = { ...FRESHNESS_ROWS[0]!, last_successful_run: "" } as FreshnessRow;
    expect(() => assertFreshnessRow(bad)).toThrow(/last_successful_run/);
  });

  it("accepts the explicit honest-absence token (shown as 'not recorded', never a guessed date)", () => {
    const row = {
      ...FRESHNESS_ROWS[0]!,
      last_successful_run: NOT_RECORDED,
      last_content_change: NOT_RECORDED,
    } as FreshnessRow;
    expect(() => assertFreshnessRow(row)).not.toThrow();
    expect(isNotRecorded(row.last_successful_run)).toBe(true);
    expect(isNotRecorded("2026-09-24")).toBe(false);
  });

  it("staleness is measured against a predicate volatility class, not absolute days", () => {
    for (const row of FRESHNESS_ROWS) expect(row.volatility_class.length).toBeGreaterThan(0);
  });

  it("P35.20b (ED-43/GQ-15): a non-evaluable row reads 'not evaluable', never 'ok' or 'stale 0'", () => {
    const notEvaluable = FRESHNESS_ROWS.filter((r) => r.status === NOT_EVALUABLE);
    // The fixture exercises the class — at least one undeclared source.
    expect(notEvaluable.length).toBeGreaterThan(0);
    for (const row of notEvaluable) {
      expect(row.status).not.toBe("ok");
      expect(row.volatility_class).toBe(NOT_EVALUABLE);
      expect(row.staleness_not_evaluable).toBeGreaterThan(0);
      // The rendered label is the honest phrase, not the token.
      expect(evaluableLabel(row.status)).toBe("not evaluable");
      expect(evaluableLabel(row.volatility_class)).toBe("not evaluable");
    }
    expect(() => assertFreshnessRow(notEvaluable[0]!)).not.toThrow();
  });

  it("rejects a freshness row that drops staleness_not_evaluable", () => {
    const bad = { ...FRESHNESS_ROWS[0]! } as Partial<FreshnessRow>;
    delete bad.staleness_not_evaluable;
    expect(() => assertFreshnessRow(bad as FreshnessRow)).toThrow(/staleness_not_evaluable/);
  });

  it("evaluableLabel leaves evaluable values untouched", () => {
    expect(evaluableLabel("ok")).toBe("ok");
    expect(evaluableLabel("SLOW")).toBe("SLOW");
    expect(isNotEvaluable("not_evaluable")).toBe(true);
    expect(isNotEvaluable("ok")).toBe(false);
  });
});

describe("coverage metrics — never a total (§32.5, SIG-METRIC-009/010)", () => {
  it("every fixture metric has a named denominator and passes the gate", () => {
    expect(() => assertCoverageMetrics(COVERAGE_METRICS)).not.toThrow();
    for (const m of COVERAGE_METRICS) expect(m.denominator.length).toBeGreaterThan(0);
  });

  it("rejects a metric claiming a population total (SIG-METRIC-010)", () => {
    const total = { ...COVERAGE_METRICS[0]!, is_population_total: true } as unknown as CoverageMetric;
    expect(() => assertCoverageMetric(total)).toThrow(/population total/);
  });

  it("rejects a denominator that is 'reality' or 'all … that exist' (SIG-METRIC-009)", () => {
    const reality: CoverageMetric = { ...COVERAGE_METRICS[0]!, denominator: "reality" };
    expect(() => assertCoverageMetric(reality)).toThrow(/NAMED denominator/);
    const all: CoverageMetric = { ...COVERAGE_METRICS[0]!, denominator: "all devices that exist" };
    expect(() => assertCoverageMetric(all)).toThrow(/NAMED denominator/);
  });

  it("requires an explicit statement that the true population is unknown (SIG-METRIC-010)", () => {
    const noNote: CoverageMetric = { ...COVERAGE_METRICS[0]!, population_note: "" };
    expect(() => assertCoverageMetric(noNote)).toThrow(/true population is unknown/);
  });

  it("publishes no capture–recapture kind (SIG-METRIC-008)", () => {
    for (const m of COVERAGE_METRICS) {
      expect(["counted_quantity", "records_derived_bound", "reconciliation_ratio", "survey_recall"]).toContain(
        m.kind,
      );
    }
  });
});
