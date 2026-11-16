// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * The mechanical evaluation report — SIG measuring its OWN method with the
 * mechanical measures only (P37.44 / CONF-09, SIG-EVAL-003 + SIG-EVAL-006 +
 * SIG-CONF-012).
 *
 * `web/mech_eval.json` is a published release artifact: the exporter computes
 * it at export time from the release's latest completed camera-site ER run,
 * the shared dedup view and the committed `sig.mech-eval-corpus/1` record —
 * never a hard-coded TypeScript constant. Human estimands are unavailable
 * (no independent human evaluation exists — D-R10-HUMAN-1) and every
 * absence is recorded honestly, never substituted.
 *
 * This module keeps only the contract: the record shape and its validator.
 * The data layer's `getMechEval()` is the single seam (fixtures mode reads
 * the canonical committed record; export mode reads the artifact).
 */

/** One estimand row — the SIG-EVAL-003 shape: numerator, denominator,
 *  method and population, plus the measured|partial|unavailable state. */
export interface MechEstimand {
  id: string;
  /** The SIG-CONF-012 estimand label (verbatim disclaimer inside). */
  label: string;
  state: "measured" | "partial" | "unavailable";
  /** B0–B5 basis class, or "none" when unavailable. */
  basis: string;
  numerator: number | null;
  denominator: number | null;
  /** Pre-formatted display of the measured quantity (null when unavailable). */
  value: string | null;
  method: string | null;
  population: string;
  unavailable_reason: string | null;
  rows: Record<string, unknown>[];
}

/** The SIG-EVAL-006 scope block — tiers, populations, source mix, ruleset
 *  and time window every figure speaks for. */
export interface MechEvalScope {
  tiers: {
    auto_collapse_derivation: number[];
    review_only_inferential: number[];
    note: string;
  };
  ruleset: {
    camera_site_rules_version: string;
    run_rules_version?: string | null;
    resolver_version?: string | null;
  };
  populations: { spine: string; corpus: string };
  source_mix: {
    spine_member_sources: { id: string; name: string }[];
    corpus_sources: string[];
  };
  time_window: {
    as_of: string;
    run_completed_at?: string | null;
    corpus?: Record<string, unknown>;
  };
  generalisation_limits: string;
}

/** The `sig.mech-eval/1` record — the artifact `web/mech_eval.json` carries
 *  and `data.ts#getMechEval` returns. */
export interface MechEval {
  schema: "sig.mech-eval/1";
  report: string;
  as_of: string;
  posture: string;
  /** The verbatim honest-posture disclosure. */
  disclosure: string;
  /** The deferral id whose trigger would open the human estimands. */
  deferral: string;
  scope: MechEvalScope;
  /** The four EVAL-003 human estimands — all `unavailable`. */
  human_estimands: Record<string, MechEstimand>;
  /** The mechanical measures (M-1, M-1b, M-2, M-3, M-4, M-5, M-9). */
  estimands: Record<string, MechEstimand>;
}

export const MECH_EVAL_SCHEMA = "sig.mech-eval/1";

function isEstimand(v: unknown): v is MechEstimand {
  const o = v as Record<string, unknown>;
  if (!o || typeof o !== "object") return false;
  if (typeof o.id !== "string" || !o.id.trim()) return false;
  if (o.state !== "measured" && o.state !== "partial" && o.state !== "unavailable") return false;
  if (typeof o.basis !== "string") return false;
  if (o.numerator !== null && typeof o.numerator !== "number") return false;
  if (o.denominator !== null && typeof o.denominator !== "number") return false;
  if (o.value !== null && typeof o.value !== "string") return false;
  if (o.method !== null && typeof o.method !== "string") return false;
  if (typeof o.population !== "string" || !o.population.trim()) return false;
  if (o.unavailable_reason !== null && typeof o.unavailable_reason !== "string") return false;
  if (!Array.isArray(o.rows)) return false;
  if (o.state === "unavailable" && !o.unavailable_reason) return false;
  return true;
}

/** Refuse a record that drops the mechanical-eval contract. */
export function isMechEval(v: unknown): v is MechEval {
  const o = v as Record<string, unknown>;
  if (!o || typeof o !== "object") return false;
  if (o.schema !== MECH_EVAL_SCHEMA) return false;
  if (typeof o.disclosure !== "string" || !o.disclosure.trim()) return false;
  if (typeof o.deferral !== "string" || !o.deferral.trim()) return false;
  if (typeof o.as_of !== "string" || !o.as_of.trim()) return false;
  const scope = o.scope as Record<string, unknown> | undefined;
  if (!scope || typeof scope !== "object") return false;
  for (const key of ["tiers", "ruleset", "populations", "source_mix", "time_window"]) {
    if (!(key in scope)) return false;
  }
  const human = o.human_estimands as Record<string, unknown> | undefined;
  if (!human || typeof human !== "object") return false;
  for (const name of [
    "auto_positive_precision",
    "candidate_recall",
    "cluster_quality",
    "labelability",
  ]) {
    const e = human[name];
    if (!isEstimand(e) || e.state !== "unavailable") return false;
  }
  const est = o.estimands as Record<string, unknown> | undefined;
  if (!est || typeof est !== "object") return false;
  for (const name of [
    "m1_derivation_census",
    "m1b_id_resolution_sample",
    "m2_fidelity_sample",
    "m3_cross_copy_agreement",
    "m4_perturbation",
    "m5_hard_negatives",
    "m9_corroboration",
  ]) {
    if (!isEstimand(est[name])) return false;
  }
  return true;
}
