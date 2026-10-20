// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * The resolution eval — SIG measuring its OWN method (§32.5, SIG-METRIC-008b;
 * P28.4).
 *
 * P34.17 / R1.4 (H-4, F-06/F-108/F-133/F-192): the earlier text claimed a
 * "frozen, human-verified holdout" and P/R/F1 1.000 — NO human verified the
 * holdout (the label sets are AI- and agent-produced), so those claims and rows
 * are removed.
 *
 * P35.37 (SIG-TRANSP-013, DR-C3-03): the measured values are a PUBLISHED
 * RELEASE ARTIFACT — `web/evaluation.json`, emitted by the exporter verbatim
 * from the canonical committed `sig.resolution-eval/1` record
 * (`exports/src/exports/data/resolution_eval.json`) — never a hard-coded
 * TypeScript constant. This module keeps only the contract: the record shape
 * and its validator. The data layer's `getResolutionEval()` is the single seam
 * (fixtures mode reads the canonical record; export mode reads the artifact).
 *
 * This is a measurement OF SIG's method — never a device-population total or a
 * capture–recapture estimate (that prohibition lives in `metrics.ts`).
 */

export interface ResolutionEvalMetric {
  /** Human label for the measured quantity. */
  label: string;
  /** The measured value, pre-formatted (e.g. "0.976"). */
  value: string;
  /** What the value is measured against — its named denominator / population. */
  against: string;
}

/**
 * The `sig.resolution-eval/1` record — the artifact `web/evaluation.json`
 * carries and `data.ts#getResolutionEval` returns.
 */
export interface ResolutionEval {
  schema?: string;
  /** Whether the eval rests on provisional ground truth. */
  provisional: boolean;
  /** The verbatim PROVISIONAL/development-evidence disclosure. */
  disclosure: string;
  /** The measured metrics. */
  metrics: ResolutionEvalMetric[];
  /** The deferral id whose closure would drop the provisional basis. */
  deferral: string;
}

/** The emitted record's schema id. */
export const RESOLUTION_EVAL_SCHEMA = "sig.resolution-eval/1";

/** Refuse a record that drops the eval contract (schema, disclosure, metrics). */
export function isResolutionEval(v: unknown): v is ResolutionEval {
  const o = v as {
    schema?: unknown;
    provisional?: unknown;
    disclosure?: unknown;
    deferral?: unknown;
    metrics?: unknown;
  };
  if (o?.schema !== RESOLUTION_EVAL_SCHEMA) return false;
  if (typeof o.provisional !== "boolean") return false;
  if (typeof o.disclosure !== "string" || !o.disclosure.trim()) return false;
  if (typeof o.deferral !== "string" || !o.deferral.trim()) return false;
  if (!Array.isArray(o.metrics)) return false;
  return (o.metrics as unknown[]).every((m) => {
    const r = m as { label?: unknown; value?: unknown; against?: unknown };
    return (
      typeof r?.label === "string" &&
      typeof r?.value === "string" &&
      typeof r?.against === "string" &&
      r.against.trim().length > 0
    );
  });
}
