// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

import { describe, expect, it } from "vitest";
import {
  STATUS_LANE_FIXTURE,
  getStatusLane,
  isStatusLaneDoc,
  outcomeCells,
} from "../../src/lib/status-lane";
import { SOURCE_ROWS_FIXTURE } from "../../src/lib/source-counts";

describe("status lane fixture", () => {
  it("validates as sig.status-lane/1", () => {
    expect(isStatusLaneDoc(STATUS_LANE_FIXTURE)).toBe(true);
  });

  it("fixtures mode returns the committed doc", () => {
    expect(getStatusLane()?.schema).toBe("sig.status-lane/1");
  });

  it("gated/refused/withdrawn sources are counts only — never names (D-J3-11)", () => {
    const countOnlyIds = SOURCE_ROWS_FIXTURE.filter((r) =>
      ["gated", "refused", "withdrawn"].includes(r.lifecycle_state),
    ).map((r) => r.source_id);
    const listed = new Set(STATUS_LANE_FIXTURE.sources.map((s) => s.source_id));
    for (const id of countOnlyIds) expect(listed.has(id)).toBe(false);
    expect(
      STATUS_LANE_FIXTURE.counts.gated +
        STATUS_LANE_FIXTURE.counts.refused +
        STATUS_LANE_FIXTURE.counts.withdrawn,
    ).toBe(countOnlyIds.length);
  });

  it("every verdict carries its evaluation time (SIG-TRANSP-029)", () => {
    for (const s of STATUS_LANE_FIXTURE.sources) {
      expect(s.freshness.evaluated_at).toBe(STATUS_LANE_FIXTURE.status_time);
      // next-run values are day-granular only
      expect(s.next_run_day).toMatch(/^(\d{4}-\d{2}-\d{2}|not_scheduled)$/);
    }
  });

  it("robots disregard discloses host+count only with the decision ref", () => {
    const r = STATUS_LANE_FIXTURE.robots_disregard;
    expect(r.decision_ref).toBe("GL-GATE-08");
    expect(typeof r.hosts).toBe("number");
    expect(typeof r.events).toBe("number");
    expect("urls" in r).toBe(false);
  });

  it("outcomeCells renders named tokens", () => {
    expect(outcomeCells({ ok: 2, failed: 1 })).toBe("ok 2 · failed 1");
    expect(outcomeCells({ ok: 0 })).toBe("none recorded");
  });
});
