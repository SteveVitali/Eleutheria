// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * P37.8 (R11-GOV-03; ADR-166 / A-4 = Q-E2-09 c; ADR-167; spec §44.3
 * SIG-SEC-003) — the legal-demand record invariants. The acceptance shape
 * is a test, never a discipline: the count record is `sig.legal-demand-counts/1`,
 * counts only (no requester-identity or case-detail field exists by
 * construction), snapshots are append-only and dated, the adopted posture
 * names its ADR and decision cell, the canary is declined and counsel
 * review is false forever on the record.
 */

import { describe, expect, it } from "vitest";
import {
  LEGAL_DEMAND_COUNT_SNAPSHOTS,
  LEGAL_DEMAND_COUNTS_SCHEMA,
  LEGAL_DEMAND_POSTURE,
  LEGAL_DEMAND_POSTURE_SCHEMA,
  isLegalDemandCounts,
  isLegalDemandPosture,
  latestCounts,
} from "../../src/lib/legal-demands";

describe("sig.legal-demand-posture/1", () => {
  it("the committed posture validates", () => {
    expect(isLegalDemandPosture(LEGAL_DEMAND_POSTURE)).toBe(true);
  });

  it("records the operator's adoption with its log time and decision cell", () => {
    expect(LEGAL_DEMAND_POSTURE.adopted_at).toBe("2026-10-01T04:03:25Z");
    expect(LEGAL_DEMAND_POSTURE.decision_ref).toBe("Q-E2-09 [A-4] = c");
    expect(LEGAL_DEMAND_POSTURE.adr).toBe("ADR-166");
  });

  it("declines the warrant canary and names the posture document", () => {
    expect(LEGAL_DEMAND_POSTURE.canary).toBe("declined");
    expect(LEGAL_DEMAND_POSTURE.counsel_reviewed).toBe(false);
    expect(LEGAL_DEMAND_POSTURE.document).toBe(
      "docs/governance/legal-demand-posture.md",
    );
  });

  it("rejects malformed records — a canary can never read as operated", () => {
    expect(
      isLegalDemandPosture({ ...LEGAL_DEMAND_POSTURE, canary: "operated" }),
    ).toBe(false);
    expect(
      isLegalDemandPosture({ ...LEGAL_DEMAND_POSTURE, counsel_reviewed: true }),
    ).toBe(false);
    expect(isLegalDemandPosture(null)).toBe(false);
    expect(isLegalDemandPosture({ schema: LEGAL_DEMAND_POSTURE_SCHEMA })).toBe(
      false,
    );
  });
});

describe("sig.legal-demand-counts/1", () => {
  it("every committed snapshot validates", () => {
    expect(LEGAL_DEMAND_COUNT_SNAPSHOTS.length).toBeGreaterThan(0);
    for (const s of LEGAL_DEMAND_COUNT_SNAPSHOTS) {
      expect(isLegalDemandCounts(s), s.snapshot_id).toBe(true);
    }
  });

  it("counts only — the record carries no requester identity or case detail", () => {
    for (const s of LEGAL_DEMAND_COUNT_SNAPSHOTS) {
      expect(
        Object.keys(s).sort(),
        s.snapshot_id,
      ).toEqual([
        "as_of",
        "complied_with",
        "received",
        "recorded_at",
        "refused",
        "schema",
        "snapshot_id",
      ]);
    }
  });

  it("snapshots are dated, uniquely identified and ordered append-only", () => {
    const ids = LEGAL_DEMAND_COUNT_SNAPSHOTS.map((s) => s.snapshot_id);
    expect(new Set(ids).size).toBe(ids.length);
    for (const s of LEGAL_DEMAND_COUNT_SNAPSHOTS) {
      expect(s.snapshot_id).toBe(`ldc:${s.as_of}`);
      expect(s.as_of).toMatch(/^\d{4}-\d{2}-\d{2}$/);
      expect(s.recorded_at).toMatch(/^\d{4}-\d{2}-\d{2}$/);
      // a snapshot can never be recorded before the day it counts as of
      expect(s.recorded_at >= s.as_of, s.snapshot_id).toBe(true);
    }
    for (let i = 1; i < LEGAL_DEMAND_COUNT_SNAPSHOTS.length; i++) {
      expect(
        LEGAL_DEMAND_COUNT_SNAPSHOTS[i]!.as_of >=
          LEGAL_DEMAND_COUNT_SNAPSHOTS[i - 1]!.as_of,
      ).toBe(true);
    }
  });

  it("complied + refused can never exceed received", () => {
    for (const s of LEGAL_DEMAND_COUNT_SNAPSHOTS) {
      expect(s.complied_with + s.refused <= s.received, s.snapshot_id).toBe(
        true,
      );
    }
    expect(
      isLegalDemandCounts({
        ...LEGAL_DEMAND_COUNT_SNAPSHOTS[0]!,
        received: 1,
        complied_with: 1,
        refused: 1,
      }),
    ).toBe(false);
  });

  it("latestCounts returns the last snapshot — the public figure", () => {
    const latest = latestCounts();
    expect(latest).not.toBeNull();
    expect(latest).toBe(
      LEGAL_DEMAND_COUNT_SNAPSHOTS[LEGAL_DEMAND_COUNT_SNAPSHOTS.length - 1],
    );
    expect(latest!.schema).toBe(LEGAL_DEMAND_COUNTS_SCHEMA);
    expect(latestCounts([])).toBeNull();
  });

  it("today's record is the zero baseline — no demand has arrived", () => {
    const latest = latestCounts()!;
    expect(latest.received).toBe(0);
    expect(latest.complied_with).toBe(0);
    expect(latest.refused).toBe(0);
  });
});
