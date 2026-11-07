// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * P37.7 (R11-GOV-02; ADR-164 / WV-02; spec §46.2 compensating controls) —
 * the public editorial decision log's record invariants. The catalogue
 * acceptance shape is a test, never a discipline: every published decision
 * entry cites its GATE DECISIONS row, the 2026-09-22 class sign-offs are
 * logged retroactively and dated as such, tombstone entries carry a
 * category and a date and never content, and no entry names a private
 * person (Part VIII).
 */

import { describe, expect, it } from "vitest";
import {
  DECISION_CLASSES,
  DECISION_CLASS_LABELS,
  EDITORIAL_DECISIONS,
  isEditorialDecision,
  logStartDate,
  orderedDecisions,
} from "../../src/lib/editorial-decisions";
import { checkRegisterConformance } from "../../src/lib/editorial";

describe("sig.editorial-decision/1", () => {
  it("every committed entry validates", () => {
    expect(EDITORIAL_DECISIONS.length).toBeGreaterThan(0);
    for (const e of EDITORIAL_DECISIONS) {
      expect(isEditorialDecision(e), e.decision_id).toBe(true);
    }
  });

  it("every published entry cites its GATE DECISIONS row (acceptance shape)", () => {
    for (const e of EDITORIAL_DECISIONS) {
      expect(e.gate_ref.row.length, e.decision_id).toBeGreaterThan(0);
      expect(e.gate_ref.row, e.decision_id).toContain("GATE DECISIONS");
      expect(e.gate_ref.row, e.decision_id).toContain("LEDGER.md");
      expect(e.gate_ref.recorded_at, e.decision_id).toMatch(
        /^\d{4}-\d{2}-\d{2}(T\d{2}:\d{2}:\d{2}Z)?$/,
      );
    }
  });

  it("decision ids are unique and classes stay in the closed vocabulary", () => {
    const ids = EDITORIAL_DECISIONS.map((e) => e.decision_id);
    expect(new Set(ids).size).toBe(ids.length);
    for (const e of EDITORIAL_DECISIONS) {
      expect(DECISION_CLASSES).toContain(e.class);
      expect(DECISION_CLASS_LABELS[e.class].length).toBeGreaterThan(0);
    }
  });

  it("ADR-164: the 2026-09-22 class sign-offs are logged retroactively, dated as such", () => {
    const signoffs = EDITORIAL_DECISIONS.filter(
      (e) => e.class === "sensitivity_classification" && e.decided_at.startsWith("2026-09-22"),
    );
    expect(signoffs.length).toBeGreaterThanOrEqual(1);
    for (const e of signoffs) {
      expect(e.retroactive, e.decision_id).toBe(true);
      expect(e.logged_at > e.decided_at, e.decision_id).toBe(true);
      expect(e.decision).toContain("facial_recognition_world_map");
      expect(e.decision).toContain("pathways_rtcc_federation");
      expect(e.decision).toContain("pathways_acoustic_drone_location");
    }
  });

  it("the WV-02 authority entry carries the adopted sentence verbatim", () => {
    const auth = EDITORIAL_DECISIONS.filter((e) => e.class === "authority");
    expect(auth.length).toBeGreaterThanOrEqual(1);
    const e = auth[0]!;
    expect(e.decision).toContain(
      "I waive SIG-GOV-015's editorial board: I hold interim single-maintainer " +
        "editorial authority, and every naming/sensitivity decision goes in a " +
        "public decision log.",
    );
    expect(e.decided_at).toContain("2026-10-01");
  });

  it("retroactive entries always postdate the decision they log", () => {
    for (const e of EDITORIAL_DECISIONS) {
      if (e.retroactive) {
        expect(e.logged_at > e.decided_at, e.decision_id).toBe(true);
      }
      expect(e.decided_at, e.decision_id).toMatch(
        /^\d{4}-\d{2}-\d{2}(T\d{2}:\d{2}:\d{2}Z)?$/,
      );
    }
  });

  it("tombstone entries carry a category and never content; other classes carry none", () => {
    for (const e of EDITORIAL_DECISIONS) {
      if (e.class === "deletion" || e.class === "purge") {
        expect(e.tombstone?.category?.length, e.decision_id).toBeGreaterThan(0);
      } else {
        expect(e.tombstone == null, e.decision_id).toBe(true);
      }
    }
  });

  it("no entry names a private person (Part VIII)", () => {
    // The operator's public name appears in repo governance records, but the
    // log names roles, never a person.
    for (const e of EDITORIAL_DECISIONS) {
      const text = [e.decision, e.scope, e.rationale, e.gate_ref.row, ...e.evidence].join(" ");
      expect(text, e.decision_id).not.toContain("Vitali");
    }
  });

  it("drafted entry prose stays inside the register rules (SIG-UI-046)", () => {
    for (const e of EDITORIAL_DECISIONS) {
      for (const field of [e.scope, e.rationale] as const) {
        expect(checkRegisterConformance(field), `${e.decision_id}: ${field}`).toEqual([]);
      }
    }
  });

  it("the log's start date is the earliest logged_at — never a made-up one", () => {
    const start = logStartDate();
    expect(start).not.toBeNull();
    expect(EDITORIAL_DECISIONS.every((e) => e.logged_at >= start!)).toBe(true);
    expect(logStartDate([])).toBeNull();
  });

  it("orderedDecisions sorts newest-first without mutating the record", () => {
    const ordered = orderedDecisions();
    expect(ordered).toHaveLength(EDITORIAL_DECISIONS.length);
    for (let i = 1; i < ordered.length; i++) {
      expect(ordered[i - 1]!.decided_at >= ordered[i]!.decided_at).toBe(true);
    }
    // append-only record order is untouched
    expect(EDITORIAL_DECISIONS[0]!.decision_id).toBe("ed:2026-09-16:naming-off");
    expect(orderedDecisions([])).toEqual([]);
  });
});
