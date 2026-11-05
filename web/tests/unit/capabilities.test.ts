// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project.

/**
 * P36.64 (SIG-UI-139 / DR-K14-05): the capability table binds every
 * capability statement to a release metric; a metric of 0 renders the
 * "being built" state, never a promise.
 */
import { describe, expect, it } from "vitest";
import { capabilityTable, releaseCapabilityMetrics } from "../../src/lib/capabilities";

describe("capabilityTable", () => {
  it("emits all five verbs in design order", () => {
    const t = capabilityTable({ dossiers: 3, evidenceArtifacts: 5, contestedFigures: 1, trackedDecisions: 7, activatedRelease: 1 });
    expect(t.map((c) => c.id)).toEqual(["find", "trace", "compare", "follow", "take"]);
    expect(t.every((c) => c.live)).toBe(true);
  });

  it("a zero metric renders the being-built state, never the promise", () => {
    const t = capabilityTable({ dossiers: 3, evidenceArtifacts: 5, contestedFigures: 0, trackedDecisions: 0, activatedRelease: 0 });
    const follow = t.find((c) => c.id === "follow")!;
    expect(follow.live).toBe(false);
    // K14 §2.2's verbatim empty-watch state.
    expect(follow.beingBuilt).toBe("Decision tracking — being built");
    expect(t.find((c) => c.id === "compare")!.live).toBe(false);
    expect(t.find((c) => c.id === "take")!.live).toBe(false);
  });

  it("the fixture release binds real metrics — no fabricated capability", () => {
    const m = releaseCapabilityMetrics();
    expect(m.dossiers).toBeGreaterThan(0);
    expect(m.contestedFigures).toBeGreaterThan(0);
    expect(m.trackedDecisions).toBeGreaterThan(0);
    expect(m.activatedRelease).toBeGreaterThanOrEqual(0);
    const t = capabilityTable(m);
    expect(t.find((c) => c.id === "find")!.live).toBe(true);
    expect(t.find((c) => c.id === "compare")!.live).toBe(true);
  });
});
