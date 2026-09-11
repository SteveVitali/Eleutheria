// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

import { describe, expect, it } from "vitest";
import {
  categoriesByPriority,
  disputeHref,
  DISPUTE_PATH,
  orderedCorrections,
  priorValuePermalink,
  SUBMISSION_CATEGORIES,
  transparencyReport,
} from "../../src/lib/corrections";
import { CORRECTIONS } from "../../src/lib/corrections-methodology-fixture";
import { RULESET_VERSION } from "../../src/lib/fixtures";

describe("submission categories (§45.1, SIG-GOV-001/002/003)", () => {
  it("accepts exactly the five §45.1 categories", () => {
    expect([...SUBMISSION_CATEGORIES].sort()).toEqual(
      ["copyright_claim", "factual_error", "legal_demand", "privacy_harm", "security_concern"].sort(),
    );
  });

  it("prioritizes privacy-harm and safety above all others (SIG-GOV-003)", () => {
    const ordered = categoriesByPriority();
    // The first two are the band-0 (privacy/safety) categories.
    expect(ordered[0]!.priorityBand).toBe(0);
    expect(ordered[1]!.priorityBand).toBe(0);
    expect(new Set([ordered[0]!.category, ordered[1]!.category])).toEqual(
      new Set(["privacy_harm", "security_concern"]),
    );
    // A factual correction is below them.
    const factual = ordered.find((c) => c.category === "factual_error")!;
    expect(factual.priorityBand).toBeGreaterThan(0);
  });

  it("requires no identity except a legal demand needing standing (SIG-GOV-002)", () => {
    const ordered = categoriesByPriority();
    for (const c of ordered) {
      expect(c.requiresIdentity).toBe(c.category === "legal_demand");
    }
  });
});

describe("one-click submission path (SIG-UI-033)", () => {
  it("is a plain path with no arguments", () => {
    expect(disputeHref()).toBe(DISPUTE_PATH);
  });

  it("deep-links what a claim is about, as a GET query", () => {
    const href = disputeHref({ subject_id: "agency:okcpd", predicate_id: "retention_days", as_of_belief: "2026-08-20" });
    expect(href.startsWith(DISPUTE_PATH)).toBe(true);
    expect(href).toContain("subject=agency%3Aokcpd");
    expect(href).toContain("predicate=retention_days");
    expect(href).toContain("as_of_belief=2026-08-20");
  });
});

describe("corrections log (SIG-UI-032, §45.3)", () => {
  it("every entry records what/when/why/who + outcome (SIG-UI-032)", () => {
    for (const e of CORRECTIONS) {
      expect(e.what_changed.length).toBeGreaterThan(0);
      expect(e.corrected_at).toMatch(/^\d{4}-\d{2}-\d{2}$/);
      expect(e.reason.length).toBeGreaterThan(0);
      expect(e.reported_by.length).toBeGreaterThan(0);
    }
  });

  it("the prior value stays citable at its belief-time (SIG-GOV-005, SIG-UI-035)", () => {
    const entry = CORRECTIONS[0]!;
    const link = priorValuePermalink(entry, RULESET_VERSION);
    expect(link).toContain(`as_of_belief=${entry.previous_belief_date}`);
    expect(link).toContain(`as_of_world=${entry.previous_belief_date}`);
    expect(link).toContain(`ruleset=${encodeURIComponent(RULESET_VERSION)}`);
    expect(link).toContain(entry.subject_path);
  });

  it("orders corrections newest-first", () => {
    const ordered = orderedCorrections(CORRECTIONS);
    for (let i = 1; i < ordered.length; i++) {
      expect(ordered[i - 1]!.corrected_at >= ordered[i]!.corrected_at).toBe(true);
    }
  });
});

describe("transparency reporting includes refusals (SIG-GOV-011)", () => {
  it("counts by category and by outcome, refusals included", () => {
    const report = transparencyReport(CORRECTIONS);
    expect(report.total).toBe(CORRECTIONS.length);
    const sumCat = Object.values(report.by_category).reduce((a, b) => a + b, 0);
    const sumOut = Object.values(report.by_outcome).reduce((a, b) => a + b, 0);
    expect(sumCat).toBe(report.total);
    expect(sumOut).toBe(report.total);
    // The fixture contains a refusal, and it is counted.
    expect(report.by_outcome.refused).toBeGreaterThanOrEqual(1);
  });
});
