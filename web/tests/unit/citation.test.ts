// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

import { describe, expect, it } from "vitest";
import { beliefPinnedPermalink, citationText } from "../../src/lib/citation";
import {
  AS_OF,
  DEVICE_COUNT_BELIEF_CLAIMS,
  RULESET_VERSION,
  resolveAsOfBelief,
} from "../../src/lib/fixtures";
import type { BeliefClaim } from "../../src/lib/fixtures";

const INPUT = {
  path: "/entity/agency/okcpd/",
  title: "Oklahoma City Police Department",
  asOf: AS_OF,
  rulesetVersion: RULESET_VERSION,
};

describe("belief-pinned permalink + citation (SIG-UI-035)", () => {
  it("pins BOTH as-of axes and the ruleset version in the permalink", () => {
    const url = new URL(beliefPinnedPermalink(INPUT));
    expect(url.searchParams.get("as_of_world")).toBe(AS_OF.as_of_world);
    expect(url.searchParams.get("as_of_belief")).toBe(AS_OF.as_of_belief);
    expect(url.searchParams.get("ruleset")).toBe(RULESET_VERSION);
    expect(url.pathname).toBe("/entity/agency/okcpd/");
  });

  it("citation text states source, both instants, ruleset, and the permalink", () => {
    const cite = citationText(INPUT);
    expect(cite).toContain("Surveillance Infrastructure Graph (SIG)");
    expect(cite).toContain(AS_OF.as_of_world);
    expect(cite).toContain(AS_OF.as_of_belief);
    expect(cite).toContain(RULESET_VERSION);
    expect(cite).toContain(beliefPinnedPermalink(INPUT));
  });
});

describe("reproducible after a correction (SIG-TIME-008)", () => {
  it("a belief-pinned citation re-resolves to the same value after a later correction", () => {
    const pinnedBelief = "2026-08-20";
    const before = resolveAsOfBelief(DEVICE_COUNT_BELIEF_CLAIMS, pinnedBelief);
    expect(before).toBe(42); // W3 contract beats W2 portal

    // SIG corrects itself: a new, higher-tier claim is asserted LATER.
    const corrected: BeliefClaim[] = [
      ...DEVICE_COUNT_BELIEF_CLAIMS,
      { claim_id: "correction", value: 40, tier: "W4", asserted_at: "2026-09-15" },
    ];

    // The pinned-belief citation is unchanged — the correction is in the future of it.
    expect(resolveAsOfBelief(corrected, pinnedBelief)).toBe(before);
    // But a reader who follows the *current* belief sees the correction.
    expect(resolveAsOfBelief(corrected, "2026-09-30")).toBe(40);
  });
});
