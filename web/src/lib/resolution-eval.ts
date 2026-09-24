// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * The resolution eval — SIG measuring its OWN method (§32.5, SIG-METRIC-008b; P28.4).
 *
 * Publishing the current holdout P/R/F1 + Cohen's κ on the methodology page is exactly
 * the epistemic-honesty posture: a project that resolves duplicate observations into
 * entities MUST publish how well its resolver measures against ground truth, and MUST
 * disclose when that ground truth is provisional. These numbers mirror the committed
 * P28.1 eval report (`docs/build/reports/P28.1_resolution_eval.md`, generator
 * `scripts/eval/run_resolution_eval.py`) — the FIRST-PASS, PROVISIONAL evidence: the
 * gold set is LLM-bootstrapped with a small maintainer seed, and the auto-write floor is
 * set against provisional labels (D-R6.1-EVAL, OPEN). The disclosure is preserved
 * verbatim so no "resolved sites" surface can imply a finality the eval does not have.
 *
 * This is a measurement OF SIG's method — never a device-population total or a
 * capture–recapture estimate (that prohibition lives in `metrics.ts`).
 */

export interface ResolutionEvalMetric {
  /** Human label for the measured quantity. */
  label: string;
  /** The measured value, pre-formatted (e.g. "0.976", "1.000"). */
  value: string;
  /** What the value is measured against — its named denominator / population. */
  against: string;
}

export interface ResolutionEval {
  /** Whether the eval rests on provisional (LLM-bootstrapped) ground truth. */
  provisional: boolean;
  /** The verbatim PROVISIONAL disclosure (preserved from the P28.1 report). */
  disclosure: string;
  /** The measured metrics (holdout P/R/F1, κ, floor). */
  metrics: ResolutionEvalMetric[];
  /** The deferral id whose closure would drop the provisional basis. */
  deferral: string;
}

/**
 * The current resolution eval, mirroring the committed P28.1 report. PROVISIONAL until
 * D-R6.1-EVAL closes (a from-first-principles re-derivation against human ground truth).
 */
export const RESOLUTION_EVAL: ResolutionEval = {
  provisional: true,
  disclosure:
    "PROVISIONAL — the gold set is LLM-bootstrapped with a small maintainer seed and the " +
    "auto-write floor is set against provisional labels (D-R6.1-EVAL, OPEN). A claim of " +
    '"resolved sites" discloses this until the deferral closes.',
  deferral: "D-R6.1-EVAL",
  metrics: [
    {
      label: "Cohen's κ (LLM adjudicator vs maintainer seed)",
      value: "0.714",
      against: "labelled pairs (bar ≥ 0.70 → LLM trusted as gold for the training partition)",
    },
    {
      label: "auto-write precision floor",
      value: "0.980",
      against: "the published floor an auto-write tier must clear on the frozen holdout",
    },
    {
      label: "pairwise precision / recall / F1 at tier ≤ 3 (auto-write)",
      value: "P 1.000 · R 1.000 · F1 1.000",
      against: "the frozen, human-verified holdout",
    },
    {
      label: "B-cubed cluster precision / recall / F1",
      value: "P 1.000 · R 0.952 · F1 0.976",
      against: "the frozen holdout clusters",
    },
    {
      label: "auto-write tier-0 holdout precision",
      value: "1.000",
      against: "the frozen holdout (0 tiers demoted below the floor)",
    },
    // P30.2b (ADR-105) — camera-site entity resolution: which observation-level records are
    // the SAME physical device. Mirrors the committed hosted measurement + gold set
    // (`docs/build/reports/p30.2b-hosted/resolution_scale.json`, gold `camera-2`).
    {
      label: "camera sites: Cohen's κ (blind LLM adjudicator vs agent seed)",
      value: "0.669",
      against:
        "540 double-adjudicated camera-record pairs (below the 0.70 bar, so the LLM is a suggester only and its disagreements go to human review)",
    },
    {
      label: "camera sites: shared-upstream-id rule (1g) holdout precision",
      value: "1.000 (70 of 70)",
      against: "the frozen, agent-verified 180-pair holdout (95% lower bound 0.948); auto-writes",
    },
    {
      label: "camera sites: coincident-point rule (3g) holdout precision",
      value: "0.986 (69 of 70)",
      against:
        "the frozen, agent-verified 180-pair holdout (95% lower bound 0.923; 0.800 if scored with the LLM's labels); auto-writes",
    },
  ],
};
