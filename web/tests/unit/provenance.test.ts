// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

import { describe, expect, it } from "vitest";
import {
  assertProvenanceComplete,
  DEFAULT_PROVENANCE,
  PROVENANCE_COMPONENTS,
  provenanceOneLine,
} from "../../src/lib/provenance";
import type { ProvenanceSummary } from "../../src/lib/provenance";
import {
  CORRECTIONS_PROVENANCE,
  RESEARCH_QUEUE_PROVENANCE,
} from "../../src/lib/corrections-methodology-fixture";

describe("'How we know this' module (SIG-UI-044)", () => {
  it("names exactly the six required components", () => {
    expect([...PROVENANCE_COMPONENTS]).toEqual([
      "artifact_count",
      "tier_distribution",
      "source_independence_count",
      "date_range",
      "rules_applied",
      "human_review_status",
    ]);
  });

  it("accepts a complete summary (the site default + per-surface summaries)", () => {
    expect(() => assertProvenanceComplete(DEFAULT_PROVENANCE)).not.toThrow();
    expect(() => assertProvenanceComplete(RESEARCH_QUEUE_PROVENANCE)).not.toThrow();
    expect(() => assertProvenanceComplete(CORRECTIONS_PROVENANCE)).not.toThrow();
  });

  it("allows a null date_range (a page with no dated evidence) but requires the key", () => {
    const noDates: ProvenanceSummary = { ...DEFAULT_PROVENANCE, date_range: null };
    expect(() => assertProvenanceComplete(noDates)).not.toThrow();
  });

  it("rejects a summary missing any component (fails the build, not memory)", () => {
    expect(() => assertProvenanceComplete({ ...DEFAULT_PROVENANCE, tier_distribution: {} })).toThrow(
      /tier_distribution/,
    );
    expect(() => assertProvenanceComplete({ ...DEFAULT_PROVENANCE, rules_applied: [] })).toThrow(
      /rules_applied/,
    );
    expect(() =>
      assertProvenanceComplete({
        ...DEFAULT_PROVENANCE,
        // @ts-expect-error deliberately invalid review status
        human_review_status: "made_up",
      }),
    ).toThrow(/human_review_status/);
  });

  it("summarizes to a one-liner naming artifacts, sources, range, and review status", () => {
    const line = provenanceOneLine(DEFAULT_PROVENANCE);
    expect(line).toContain("4 artifact");
    expect(line).toContain("independent source");
    expect(line).toContain("2025-03-25");
  });
});
