// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * Data-freshness (§32.4) and coverage metrics (§32.5), as pure data + logic.
 *
 * These back the two public metrics pages (SIG-UI-034). The freshness page shows,
 * per source, the last successful run, the last content change, the current status,
 * and the count of entities whose evidence is stale FOR THEIR PREDICATE CLASS —
 * freshness is measured relative to predicate volatility, not absolute days
 * (SIG-METRIC-006/007).
 *
 * The coverage page carries the project's hardest honesty constraint. SIG publishes
 * **counted quantities with named denominators**, records-derived **bounds**,
 * per-agency reconciliation ratios, and measured survey recall — and **never a total**
 * (SIG-METRIC-009). It MUST NOT publish a completeness percentage that implies it
 * knows the denominator of reality (SIG-METRIC-010), and it MUST NOT publish a
 * capture–recapture population estimate (SIG-METRIC-008). Those prohibitions are
 * enforced here structurally: a coverage metric MUST carry a named denominator and is
 * rejected if it presents itself as a population total.
 */

// --- Freshness (§32.4, SIG-METRIC-006/007) -----------------------------------

export const SOURCE_STATUSES = [
  "ok",
  "degraded",
  "failing",
  "retired",
  // P35.20b (ED-43, GQ-15): staleness is NOT evaluable for this source — no
  // declared §28.3 volatility class, or no evaluable dated observation. A real
  // honest class, never "ok" and never a fabricated stale-0 (§3.1).
  "not_evaluable",
] as const;
export type SourceStatus = (typeof SOURCE_STATUSES)[number];

/**
 * The explicit honest-absence token for a freshness date the spine does not record
 * (exports `shaping.NOT_RECORDED`, P30.3). It is SHOWN ("not recorded"), never dropped and
 * never replaced by a guessed date (§3.1); an empty string is still a dropped field.
 */
export const NOT_RECORDED = "not-recorded";

/**
 * The explicit not-evaluable token a freshness row's status/volatility carries
 * when staleness cannot be evaluated (exports `shaping.NOT_EVALUABLE`, P35.20b).
 */
export const NOT_EVALUABLE = "not_evaluable";

/** True when a freshness date is the explicit honest-absence token. */
export function isNotRecorded(value: string): boolean {
  return value === NOT_RECORDED;
}

/** True when a freshness status/volatility is the explicit not-evaluable token. */
export function isNotEvaluable(value: string): boolean {
  return value === NOT_EVALUABLE;
}

/** The rendered label for a status/volatility token: `not_evaluable` prints
 * "not evaluable" — GQ-15's clause ("freshness says 'not evaluable', not
 * 'ok'") holds on the rendered surface, not only in the JSON. */
export function evaluableLabel(value: string): string {
  return isNotEvaluable(value) ? "not evaluable" : value;
}

/** Per-source freshness row (SIG-METRIC-007). All fields are required —
 * including `staleness_not_evaluable`, the count of dated observations
 * staleness was never evaluated for (P35.20b), and P35.41's additions:
 * `evaluated_at` (every freshness value carries its evaluation time — the
 * release as-of, never the reader's clock), `staleness_evaluable_count`
 * (the "of m evaluable" denominator, K9 §5.3), `undated_count` (the
 * "not evaluable: m undated" share), and the §5.2 volatility basis
 * (`volatility_distribution` over ALL published claims +
 * `unregistered_predicate_count`). */
export interface FreshnessRow {
  source: string;
  last_successful_run: string;
  last_content_change: string;
  status: SourceStatus;
  /** Count of entities whose evidence is stale FOR THEIR PREDICATE CLASS (not absolute days). */
  stale_entity_count: number;
  /** Dated observations staleness was never evaluated for (undeclared class →
   * the whole set; declared → the unregistered-predicate share). P35.20b. */
  staleness_not_evaluable: number;
  /** The source's DECLARED §28.3 volatility class (SIG-METRIC-006), or
   * `not_evaluable` when undeclared — never a guessed class. */
  volatility_class: string;
  /** The instant the freshness values were evaluated at — the release
   * as-of (P35.41 / K9 C-4's two-clocks rule). */
  evaluated_at: string;
  /** The "of m evaluable" denominator — deduped dated observations the
   * staleness measure evaluated (K9 §5.3). */
  staleness_evaluable_count: number;
  /** Published claims carrying no `observed_at` — the "not evaluable: m
   * undated" share (K9 §5.3); a count, never "unknown". */
  undated_count: number;
  /** The registry volatility-class distribution over ALL the source's
   * published claims — the disclosed §5.2 basis (K9), never a class voted
   * in place of the declared gate. */
  volatility_distribution: Record<string, number>;
  /** Published claims whose predicate the registry does not declare —
   * counted honestly, never silently dropped (K9 §5.2). */
  unregistered_predicate_count: number;
}

/** Refuse a freshness row that drops a required field (SIG-METRIC-007). */
export function assertFreshnessRow(row: FreshnessRow): void {
  const missing: string[] = [];
  if (!row.source) missing.push("source");
  if (!row.last_successful_run) missing.push("last_successful_run");
  if (!row.last_content_change) missing.push("last_content_change");
  if (!SOURCE_STATUSES.includes(row.status)) missing.push("status");
  if (!Number.isFinite(row.stale_entity_count)) missing.push("stale_entity_count");
  if (!Number.isFinite(row.staleness_not_evaluable)) missing.push("staleness_not_evaluable");
  if (!row.volatility_class) missing.push("volatility_class");
  if (!row.evaluated_at) missing.push("evaluated_at");
  if (!Number.isFinite(row.staleness_evaluable_count)) missing.push("staleness_evaluable_count");
  if (!Number.isFinite(row.undated_count)) missing.push("undated_count");
  if (!row.volatility_distribution || typeof row.volatility_distribution !== "object")
    missing.push("volatility_distribution");
  if (!Number.isFinite(row.unregistered_predicate_count)) missing.push("unregistered_predicate_count");
  if (missing.length > 0) {
    throw new Error(`freshness row for "${row.source}" missing: ${missing.join(", ")} (SIG-METRIC-007)`);
  }
}

// --- Coverage (§32.5, SIG-METRIC-008/009/010) --------------------------------

/**
 * The four legitimate coverage-metric kinds (SIG-METRIC-009). NONE is a population
 * total: a counted quantity is `count / named-denominator`, a bound is `≥ N`, a
 * ratio reconciles two named counts, and survey recall is a measurement of SIG's own
 * method on a named calibration subset — never extrapolated (SIG-METRIC-008b).
 */
export const COVERAGE_METRIC_KINDS = [
  "counted_quantity",
  "records_derived_bound",
  "reconciliation_ratio",
  "survey_recall",
] as const;
export type CoverageMetricKind = (typeof COVERAGE_METRIC_KINDS)[number];

/**
 * A published coverage metric. The `denominator` is REQUIRED and must name what the
 * count is *of* — "of 34 jurisdictions with any evidence", never "of all jurisdictions
 * that exist". `is_population_total` exists only so the assertion below can reject it:
 * a metric that claims to be a total of reality is forbidden (SIG-METRIC-010).
 */
export interface CoverageMetric {
  id: string;
  kind: CoverageMetricKind;
  label: string;
  value: string;
  /** The NAMED denominator (SIG-METRIC-009). Empty/"reality"/"all …" is forbidden. */
  denominator: string;
  /** Plain-language statement that the true population is unknown (SIG-METRIC-010). */
  population_note: string;
  /** Must be false: SIG never publishes a population total (SIG-METRIC-010). */
  is_population_total: false;
  /**
   * ED-42 (F-134): the per-class exclusion disclosure beside a reconciliation
   * ratio — `{conflicted, withheld, non_publishable, filtered}` counts of the
   * denominator's subjects that did NOT make the numerator. Optional (absent on
   * non-ratio metrics); when present the ratio's "N of M" is always honest —
   * N + `excluded_total` = M, never a clamped N-of-N.
   */
  exclusions?: Record<string, number>;
  /** The summed exclusion count disclosed beside the numerator (ED-42). */
  excluded_total?: number;
}

const _FORBIDDEN_DENOMINATORS = /^(reality|the population|all (jurisdictions|devices|agencies)( that exist)?)$/i;

/**
 * Refuse a coverage metric that violates the §32.5 honesty constraints: it must carry
 * a real named denominator, must not present that denominator as "reality"/"all that
 * exist", and must not claim to be a population total (SIG-METRIC-009/010). This is
 * the executable form of "never a total".
 */
export function assertCoverageMetric(metric: CoverageMetric): void {
  if ((metric as { is_population_total: boolean }).is_population_total) {
    throw new Error(`coverage metric "${metric.id}" claims a population total — forbidden (SIG-METRIC-010)`);
  }
  const d = metric.denominator?.trim();
  if (!d || _FORBIDDEN_DENOMINATORS.test(d)) {
    throw new Error(
      `coverage metric "${metric.id}" needs a NAMED denominator, not "${metric.denominator}" (SIG-METRIC-009)`,
    );
  }
  if (!metric.population_note.trim()) {
    throw new Error(
      `coverage metric "${metric.id}" must state the true population is unknown (SIG-METRIC-010)`,
    );
  }
}

/** Validate the whole coverage set (used at build + in tests). */
export function assertCoverageMetrics(metrics: readonly CoverageMetric[]): void {
  for (const m of metrics) assertCoverageMetric(m);
}
