// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

import { describe, expect, it } from "vitest";
import {
  assertCoverageMetric,
  assertCoverageMetrics,
  assertFreshnessRow,
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

  it("staleness is measured against a predicate volatility class, not absolute days", () => {
    for (const row of FRESHNESS_ROWS) expect(row.volatility_class.length).toBeGreaterThan(0);
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
