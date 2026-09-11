// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

import { describe, expect, it } from "vitest";
import {
  EDITORIAL_CASES,
  REGISTER_RULES,
  allFindingsDispositioned,
  assertRegisterConformant,
  assertReviewReleasable,
  checkRegisterConformance,
  openFindings,
} from "../../src/lib/editorial";
import type { HostileReaderReview } from "../../src/lib/editorial";
import {
  GENERATED_RATIONALE_TEMPLATES,
  HOSTILE_READER_REVIEW,
} from "../../src/lib/corrections-methodology-fixture";

describe("the six register rules (SIG-UI-043)", () => {
  it("codifies exactly six rules, numbered 1..6", () => {
    expect(REGISTER_RULES).toHaveLength(6);
    expect(REGISTER_RULES.map((r) => r.n)).toEqual([1, 2, 3, 4, 5, 6]);
  });

  it("every rule's own conformant example passes and its non-conformant example is flagged", () => {
    for (const r of REGISTER_RULES) {
      expect(checkRegisterConformance(r.conformant)).toEqual([]);
    }
    // The characterizing ("admitted") and motive ("quietly rammed through") examples flag.
    expect(checkRegisterConformance("The department admitted to only 38 cameras.").length).toBeGreaterThan(0);
    expect(
      checkRegisterConformance("The council quietly rammed the contract through to avoid scrutiny.").length,
    ).toBeGreaterThan(0);
  });
});

describe("register conformance applies to generated text too (SIG-UI-046)", () => {
  it("every generated rationale template is register-conformant", () => {
    for (const t of GENERATED_RATIONALE_TEMPLATES) {
      expect(checkRegisterConformance(t)).toEqual([]);
      expect(() => assertRegisterConformant(t, "generated rationale")).not.toThrow();
    }
  });

  it("assertRegisterConformant throws on a violating template (release-blocking)", () => {
    expect(() =>
      assertRegisterConformant("The vendor admitted the system failed.", "generated"),
    ).toThrow(/register-rule violation/);
  });
});

describe("the three example editorial cases (SIG-UI-045)", () => {
  it("renders the three hardest cases as the specified copy", () => {
    expect(EDITORIAL_CASES.map((c) => c.id)).toEqual([
      "pending_lawsuit",
      "policy_configuration_divergence",
      "cancellation_hardware_remaining",
    ]);
    const byId = Object.fromEntries(EDITORIAL_CASES.map((c) => [c.id, c.copy]));
    expect(byId.pending_lawsuit).toContain("A complaint filed 2026-03-04");
    expect(byId.pending_lawsuit).toContain("has not been adjudicated");
    expect(byId.policy_configuration_divergence).toContain("adopted 2025-11-02");
    expect(byId.policy_configuration_divergence).toContain("this is an open question");
    expect(byId.cancellation_hardware_remaining).toContain("23 devices");
    expect(byId.cancellation_hardware_remaining).toContain("not a record of surveillance being removed");
  });

  it("the example copy is itself register-conformant", () => {
    for (const c of EDITORIAL_CASES) {
      expect(checkRegisterConformance(c.copy)).toEqual([]);
    }
  });
});

describe("hostile-reader review release gate (SIG-UI-042)", () => {
  it("the committed review has two reviewers and every finding dispositioned → releasable", () => {
    expect(HOSTILE_READER_REVIEW.reviewers.length).toBeGreaterThanOrEqual(2);
    expect(allFindingsDispositioned(HOSTILE_READER_REVIEW)).toBe(true);
    expect(openFindings(HOSTILE_READER_REVIEW)).toEqual([]);
    expect(() => assertReviewReleasable(HOSTILE_READER_REVIEW)).not.toThrow();
  });

  it("blocks release when any finding is undispositioned", () => {
    const withOpen: HostileReaderReview = {
      ...HOSTILE_READER_REVIEW,
      findings: [
        ...HOSTILE_READER_REVIEW.findings,
        { id: "hr-open", challenge: "An unresolved objection.", disposition: null, resolution: "" },
      ],
    };
    expect(allFindingsDispositioned(withOpen)).toBe(false);
    expect(openFindings(withOpen).map((f) => f.id)).toContain("hr-open");
    expect(() => assertReviewReleasable(withOpen)).toThrow(/release blocked/);
  });

  it("blocks release when there are fewer than two independent reviewers", () => {
    const solo: HostileReaderReview = { ...HOSTILE_READER_REVIEW, reviewers: ["only one"] };
    expect(() => assertReviewReleasable(solo)).toThrow(/two independent reviewers/);
  });
});
