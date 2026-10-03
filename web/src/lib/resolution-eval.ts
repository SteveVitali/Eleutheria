// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * The resolution eval — SIG measuring its OWN method (§32.5, SIG-METRIC-008b; P28.4).
 *
 * P34.17 / R1.4 (H-4, F-06/F-108/F-133/F-192): the earlier text claimed a "frozen,
 * human-verified holdout" and P/R/F1 1.000 — NO human verified the holdout (the
 * label sets are AI- and agent-produced), so those claims and rows are removed.
 * What remains is true of the 2026-09-27 data: the camera-site entity-resolution
 * measurement recorded in the committed P30.2b hosted report
 * (`docs/build/reports/p30.2b-hosted/resolution_scale.json` — κ 0.669 over 540
 * double-adjudicated pairs, tier 1g 70/70 and 3g 69/70 on the 180-pair
 * agent-checked holdout), plus the earlier development eval's κ and cluster
 * metrics labelled for what they are — DEVELOPMENT evidence over labels no person
 * made. The organisation-resolution auto-write floor is a configuration fact,
 * not a measurement claim.
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

export interface ResolutionEval {
  /** Whether the eval rests on provisional ground truth. */
  provisional: boolean;
  /** The verbatim PROVISIONAL/development-evidence disclosure. */
  disclosure: string;
  /** The measured metrics. */
  metrics: ResolutionEvalMetric[];
  /** The deferral id whose closure would drop the provisional basis. */
  deferral: string;
}

/**
 * The current resolution eval. The development evidence is provisional until
 * D-R6.1-EVAL closes (a from-first-principles re-derivation against human ground
 * truth); the camera-site numbers are the committed 2026-09-24 measurement.
 */
export const RESOLUTION_EVAL: ResolutionEval = {
  provisional: true,
  // Batch row M-31 pins this disclosure verbatim (B-2).
  disclosure:
    "Development evidence only — the label sets were produced by an AI model " +
    "and by agents; no person labelled them.",
  deferral: "D-R6.1-EVAL",
  metrics: [
    {
      // P34.17 / H-4: relabelled — the "maintainer seed" implied a human label
      // set that no record supports.
      label: "development eval: Cohen's κ between two adjudication passes",
      value: "0.714",
      against:
        "the development label set stored in the repository — no record shows those labels were made by a person",
    },
    {
      label: "auto-write precision floor",
      value: "0.980",
      against: "the published floor an auto-write rule must clear on its holdout",
    },
    {
      label: "development eval: B-cubed cluster precision / recall / F1",
      value: "P 1.000 · R 0.952 · F1 0.976",
      against: "the development holdout clusters (AI-model labels; no person labelled them)",
    },
    // P30.2b (ADR-105) — camera-site entity resolution: which observation-level
    // records are the SAME physical device. Mirrors the committed hosted
    // measurement + gold set (`docs/build/reports/p30.2b-hosted/`).
    {
      label: "camera sites: Cohen's κ (blind adjudicator vs stored labels)",
      value: "0.669",
      against:
        "540 double-adjudicated camera-record pairs (below the 0.70 bar, so that adjudicator is a suggester only and its disagreements go to review)",
    },
    {
      label: "camera sites: shared-upstream-id rule (1g) holdout precision",
      value: "1.000 (70 of 70)",
      against: "the 180-pair holdout, labels recorded as agent-checked (95% lower bound 0.948); auto-writes",
    },
    {
      label: "camera sites: coincident-point rule (3g) holdout precision",
      value: "0.986 (69 of 70)",
      against:
        "the 180-pair holdout, labels recorded as agent-checked (95% lower bound 0.923; 0.800 under the AI model's labels); auto-writes",
    },
  ],
};
