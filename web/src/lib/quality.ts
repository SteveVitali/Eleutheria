// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * P37.45 (CONF-12, SIG-CONF-011 + SIG-CONF-001/010, L3 §5.1/§5.4): the public
 * `/quality/` page artifact — `web/quality.json` (`sig.quality-page/1`).
 *
 * The ONE artifact the page renders from: the whole registry declaration
 * (every registered check, failing and ratchet included — Q-L3-5) plus the
 * measured `sig.quality-report/1` when a run is bound (or its named
 * absence). This module keeps only the contract: shapes, the fail-closed
 * validator, and the display state a check's declared + measured halves
 * join into. The data layer's `getQualityPage()` / `getQualityLane()` are
 * the seams.
 */

export const QUALITY_PAGE_SCHEMA = "sig.quality-page/1";
export const QUALITY_PROBE_RUN_SCHEMA = "sig.probe-run/1";

/** The verbatim Round-11 posture sentence (SIG-CONF-010 / Q-L3-3 = c /
 *  B-31): no maintainer check was performed and no person outside the
 *  project has reviewed SIG's data. The page states it verbatim. */
export const NO_HUMAN_CHECK = "no human check performed";

export interface QualityCheckDeclared {
  id: string;
  statement: string;
  population: string;
  placement: string[];
  mode: "enforce" | "ratchet" | "report";
  direction: "lower_is_better" | "higher_is_better";
  threshold: string;
  baseline: number | null;
  baseline_pending: boolean;
  baseline_run: string | null;
  baseline_at: string | null;
  unit: "count" | "share" | "ratio";
  basis_class: "B0" | "B1" | "B2" | "B3" | "B4" | "B5";
  fixing: string[];
  from: string;
  note: string | null;
}

export interface QualityCheckOutcome {
  id: string;
  mode: string;
  basis_class: string;
  outcome: "pass" | "fail" | "not_evaluable" | "unbaselined";
  offered: number;
  evaluated: number;
  measured: number | null;
  baseline: number | null;
  baseline_pending: boolean;
  threshold: string;
  direction: string;
  regression: boolean;
  improvement: boolean;
  alert_band_breach: boolean;
  reason: string;
  detail: Record<string, unknown>;
}

export interface QualityReport {
  version: "sig.quality-report/1";
  generated_at: string;
  placement: string;
  target: string;
  registry: {
    schema: string;
    version: string;
    digest: string;
    checks_declared: number;
    checks_evaluated: number;
  };
  checks: QualityCheckOutcome[];
  totals: { offered: number; evaluated: number };
  summary: {
    overall: "pass" | "fail" | "partial";
    enforce_failures: string[];
    ratchet_regressions: string[];
    unbaselined: string[];
    not_evaluable: string[];
    class_s_trigger: boolean;
  };
}

export interface QualityPage {
  schema: typeof QUALITY_PAGE_SCHEMA;
  generated_at: string;
  target: string | null;
  registry: {
    schema: "sig.quality-checks/1";
    version: string;
    digest: string;
    checks: QualityCheckDeclared[];
  };
  report: QualityReport | null;
  /** Named absence when report is null — never silent. */
  report_absence: string | null;
}

/** The nightly spine probe's latest run — `status/quality/latest.json`
 *  (`sig.probe-run/1`), labelled "latest check of the working database
 *  (not yet published)". Never the same population as the release-bound
 *  report — the two are never mixed (L3 §5.1). */
export interface QualityProbeRun {
  version: typeof QUALITY_PROBE_RUN_SCHEMA;
  generated_at: string;
  probe: string;
  placement: string;
  target: string;
  job: string;
  checks: {
    name: string;
    outcome: string;
    evaluated: number;
    offered: number;
    reason: string;
  }[];
  overall: string;
}

function isCheckDeclared(v: unknown): v is QualityCheckDeclared {
  const o = v as Record<string, unknown>;
  if (!o || typeof o !== "object") return false;
  if (typeof o.id !== "string" || !/^GQ-\d{2}$/.test(o.id)) return false;
  for (const f of ["statement", "population", "mode", "direction", "threshold", "unit", "basis_class"]) {
    if (typeof o[f] !== "string" || !(o[f] as string).trim()) return false;
  }
  if (!Array.isArray(o.placement) || !Array.isArray(o.fixing)) return false;
  return true;
}

function isOutcome(v: unknown): v is QualityCheckOutcome {
  const o = v as Record<string, unknown>;
  if (!o || typeof o !== "object") return false;
  if (typeof o.id !== "string" || !/^GQ-\d{2}$/.test(o.id)) return false;
  if (!["pass", "fail", "not_evaluable", "unbaselined"].includes(String(o.outcome))) return false;
  if (typeof o.offered !== "number" || typeof o.evaluated !== "number") return false;
  return true;
}

/** Refuse a page artifact that drops the SIG-CONF-011 contract. */
export function isQualityPage(v: unknown): v is QualityPage {
  const o = v as Record<string, unknown>;
  if (!o || typeof o !== "object") return false;
  if (o.schema !== QUALITY_PAGE_SCHEMA) return false;
  if (typeof o.generated_at !== "string" || !o.generated_at.trim()) return false;
  const reg = o.registry as Record<string, unknown> | undefined;
  if (!reg || reg.schema !== "sig.quality-checks/1") return false;
  if (!Array.isArray(reg.checks) || reg.checks.length === 0) return false;
  if (!reg.checks.every(isCheckDeclared)) return false;
  const report = o.report;
  if (report === null) {
    return typeof o.report_absence === "string" && o.report_absence.trim().length > 0;
  }
  const r = report as Record<string, unknown>;
  if (!r || r.version !== "sig.quality-report/1") return false;
  if (!Array.isArray(r.checks) || !(r.checks as unknown[]).every(isOutcome)) return false;
  return true;
}

export function isQualityProbeRun(v: unknown): v is QualityProbeRun {
  const o = v as Record<string, unknown>;
  if (!o || typeof o !== "object") return false;
  if (o.version !== QUALITY_PROBE_RUN_SCHEMA) return false;
  if (typeof o.generated_at !== "string" || !o.generated_at.trim()) return false;
  return Array.isArray(o.checks);
}

/** The basis class display rows — who checked what (L3 §5.1 §4). The
 *  independent-human row always reads `none` while no B5 evidence exists. */
export const BASIS_ROWS: readonly { cls: string; name: string; wording: string }[] = [
  { cls: "B0", name: "by construction", wording: "guaranteed by how SIG is built (tested)" },
  { cls: "B1", name: "mechanical census", wording: "checked automatically on all records" },
  { cls: "B2", name: "mechanical sample", wording: "checked automatically on a seeded sample" },
  { cls: "B3", name: "agent review", wording: "reviewed by an AI agent — never a person; never gates" },
  { cls: "B4", name: "maintainer check", wording: "checked by SIG's maintainer — not independent; never gates" },
  { cls: "B5", name: "independent human", wording: "independently reviewed — none performed" },
];

/** How many registered checks each basis class declares. */
export function basisCounts(checks: readonly QualityCheckDeclared[]): Record<string, number> {
  const out: Record<string, number> = { B0: 0, B1: 0, B2: 0, B3: 0, B4: 0, B5: 0 };
  for (const c of checks) out[c.basis_class] = (out[c.basis_class] ?? 0) + 1;
  return out;
}

/** The public state label a check renders: its measured outcome when a run
 *  bound one, else the honest declared state — failing and ratchet checks
 *  are shown, never hidden (Q-L3-5). */
export function checkState(
  declared: QualityCheckDeclared,
  outcome: QualityCheckOutcome | undefined,
): { label: string; tone: "pass" | "fail" | "ratchet" | "pending" | "unevaluated" } {
  if (!outcome) {
    return {
      label:
        declared.mode === "ratchet"
          ? `being fixed — no worse than ${declared.baseline ?? "baseline pending"} (not evaluated this run)`
          : "declared — not evaluated this run",
      tone: declared.mode === "ratchet" ? "ratchet" : "unevaluated",
    };
  }
  switch (outcome.outcome) {
    case "pass":
      return {
        label: outcome.improvement
          ? `passing — improved on baseline ${outcome.baseline}`
          : "passing",
        tone: "pass",
      };
    case "fail":
      return {
        label: outcome.regression
          ? `failing — regressed past baseline ${outcome.baseline}`
          : "failing",
        tone: "fail",
      };
    case "unbaselined":
      return { label: "ratchet — baseline pending (recorded, does not gate)", tone: "pending" };
    default:
      return { label: `not evaluable — ${outcome.reason || "no evaluator ran"}`, tone: "unevaluated" };
  }
}
