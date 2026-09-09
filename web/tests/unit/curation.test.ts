// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

import { describe, it, expect } from "vitest";
import {
  REVIEW_QUEUE,
  CONTRADICTIONS,
  ER_DECISIONS,
  TASK_DISPOSITIONS,
  orderByImpact,
  curationAction,
  curationApiBase,
} from "../../src/lib/curation";

describe("curation view model (P21.6)", () => {
  it("orders the queue by impact — highest |weight| first (RISK-P21-11)", () => {
    const ordered = orderByImpact(REVIEW_QUEUE);
    const weights = ordered.map((i) => (i.overall_weight === null ? 0 : Math.abs(i.overall_weight)));
    for (let i = 1; i < weights.length; i++) {
      expect(weights[i - 1]).toBeGreaterThanOrEqual(weights[i]);
    }
  });

  it("surfaces a model suggestion as a labelled suggestion, never a decision", () => {
    const model = REVIEW_QUEUE.find((i) => i.kind === "model_extraction");
    expect(model?.suggestion).toBeDefined();
    expect(model?.suggestion?.model_id).toBeTruthy();
    expect(model?.suggestion?.confidence_class).toBeTruthy();
    // The suggestion is data only — there is no "decision"/"applied" field on the item.
    expect((model as unknown as Record<string, unknown>).decision).toBeUndefined();
    // ER matches carry no machine suggestion.
    const er = REVIEW_QUEUE.find((i) => i.kind === "er_match");
    expect(er?.suggestion).toBeUndefined();
  });

  it("offers match / no-match / defer as the ER decisions", () => {
    expect(ER_DECISIONS.map((d) => d.value)).toEqual(["match", "no-match", "defer"]);
  });

  it("shows both claims of a contradiction with evidence and dates (§3.1)", () => {
    for (const c of CONTRADICTIONS) {
      expect(c.claims.length).toBeGreaterThanOrEqual(2);
      for (const claim of c.claims) {
        expect(claim.value).toBeTruthy();
        expect(claim.evidence_ref).toBeTruthy();
        expect(claim.as_of).toBeTruthy();
      }
    }
  });

  it("mirrors the task disposition vocabulary incl. the negative-result disposition", () => {
    expect(TASK_DISPOSITIONS).toContain("resolved_no_evidence_exists");
  });

  it("builds absolute action URLs against the non-public curation API base", () => {
    expect(curationApiBase()).toMatch(/^http:\/\/127\.0\.0\.1:/);
    expect(curationAction("submission")).toMatch(/\/v1\/curation\/submission$/);
    expect(curationAction("review-queue/x/decide")).toContain("/v1/curation/review-queue/x/decide");
  });
});
