// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

import { describe, expect, it } from "vitest";
import {
  ABSENCE_HATCH_CLASS,
  ABSENCE_KINDS,
  ABSENCE_KIND_META,
  AGREEMENT_LEVELS,
  CONTESTED_AGREEMENTS,
  EPISTEMIC_FIELD_NAMES,
  GLYPH_STEP_COUNT,
  SUPPORT_LEVELS,
  contradictionRange,
  isContested,
  plotPosition,
  supportGlyph,
  supportMark,
  supportTextEquivalent,
} from "../../src/lib/epistemic";

describe("support glyph (SIG-UI-003)", () => {
  it("is a four-step glyph for every support level", () => {
    for (const s of SUPPORT_LEVELS) {
      const glyph = supportGlyph(s);
      // Count glyph steps by code points, not string length (⊕/◯ are multi-byte).
      expect([...glyph]).toHaveLength(GLYPH_STEP_COUNT);
    }
  });

  it("fills more steps for stronger support (monotone)", () => {
    const filled = SUPPORT_LEVELS.map((s) => supportMark(s, 1).filledSteps);
    // SUPPORT_LEVELS is ordered strongest→weakest, so filled counts are descending.
    for (let i = 1; i < filled.length; i++) {
      expect(filled[i]!).toBeLessThan(filled[i - 1]!);
    }
    expect(filled[0]).toBe(GLYPH_STEP_COUNT); // CONFIRMED = all four
    expect(filled.at(-1)).toBe(0); // UNSUPPORTED = none
  });

  it("always carries a text equivalent naming the level and the count", () => {
    const text = supportTextEquivalent("STRONGLY_SUPPORTED");
    expect(text).toContain("strongly supported");
    expect(text).toContain(`3 of ${GLYPH_STEP_COUNT}`);
  });

  it("carries a machine-readable evidence count and a downgrade reason when downgraded", () => {
    const confirmed = supportMark("CONFIRMED", 2);
    expect(confirmed.evidenceCount).toBe(2);
    expect(confirmed.downgradeReasonCode).toBeNull(); // a full mark says nothing was downgraded

    const probable = supportMark("PROBABLE", 1);
    expect(probable.evidenceCount).toBe(1);
    // A support mark that does not say WHY it was downgraded is decoration (SIG-UI-003).
    expect(probable.downgradeReasonCode).toBeTruthy();
  });
});

describe("four independent fields (SIG-UI-004)", () => {
  it("names exactly the four §10.7 fields, never a fused token", () => {
    expect(EPISTEMIC_FIELD_NAMES).toEqual([
      "resolution_status",
      "support",
      "agreement",
      "currency",
    ]);
    expect(EPISTEMIC_FIELD_NAMES).toHaveLength(4);
  });
});

describe("contested values (SIG-UI-008)", () => {
  it("marks CONTESTED and IRRECONCILABLE, but not uncontested/minor", () => {
    expect(isContested("CONTESTED")).toBe(true);
    expect(isContested("IRRECONCILABLE")).toBe(true);
    expect(isContested("UNCONTESTED")).toBe(false);
    expect(isContested("MINOR_DISAGREEMENT")).toBe(false);
  });

  it("the contested threshold is a strict subset of the agreement vocabulary", () => {
    for (const a of CONTESTED_AGREEMENTS) expect(AGREEMENT_LEVELS).toContain(a);
    expect(CONTESTED_AGREEMENTS.length).toBeLessThan(AGREEMENT_LEVELS.length);
  });
});

describe("absence: one texture, four kinds (SIG-UI-007, §9.5)", () => {
  it("has exactly the four §9.5 kinds", () => {
    expect([...ABSENCE_KINDS]).toEqual([
      "NOT_RESEARCHED",
      "NO_EVIDENCE_FOUND",
      "EVIDENCE_OF_ABSENCE",
      "UNRESOLVED",
    ]);
  });

  it("uses ONE shared hatch class and distinguishes kinds by a distinct symbol + text", () => {
    // One texture for all (SIG-UI-007): there is a single hatch class constant.
    expect(ABSENCE_HATCH_CLASS).toBe("sig-absence-hatch");
    // The four kinds are distinguishable WITHIN it: unique symbols and unique labels.
    const symbols = ABSENCE_KINDS.map((k) => ABSENCE_KIND_META[k].symbol);
    const labels = ABSENCE_KINDS.map((k) => ABSENCE_KIND_META[k].label);
    expect(new Set(symbols).size).toBe(ABSENCE_KINDS.length);
    expect(new Set(labels).size).toBe(ABSENCE_KINDS.length);
  });

  it("makes every kind taskable (a gap is an invitation, not a dead end)", () => {
    for (const k of ABSENCE_KINDS) expect(ABSENCE_KIND_META[k].taskable).toBe(true);
  });
});

describe("contradiction value range (SIG-UI-009, §29.1)", () => {
  const claims = [
    { claimId: "a", value: 42, source: "records", tier: "W3", date: "2026-07-01", documentUrl: "/a" },
    { claimId: "b", value: 38, source: "portal", tier: "W2", date: "2026-07-01", documentUrl: "/b" },
  ];

  it("plots the range from min to max of the competing claims", () => {
    const range = contradictionRange(claims);
    expect(range.min).toBe(38);
    expect(range.max).toBe(42);
    expect(range.claims).toHaveLength(2);
  });

  it("positions the endpoints at 0 and 1 within the range", () => {
    const range = contradictionRange(claims);
    expect(plotPosition(range, 38)).toBe(0);
    expect(plotPosition(range, 42)).toBe(1);
  });

  it("rejects an empty range rather than fabricating one", () => {
    expect(() => contradictionRange([])).toThrow();
  });
});
