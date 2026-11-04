// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// P36.65 (UXK14-11; K14 §6.4; SIG-UI-086/151) — the typed-empty coverage
// contract: EVERY declared cause class has copy — a dedicated surface entry
// or a canonical kind row — and a missing kind fails loud, never silently.
import { describe, it, expect } from "vitest";
import {
  EMPTY_CAUSES,
  EMPTY_KIND_PARTS,
  EMPTY_SURFACES,
  emptyCauseCovered,
  emptyKindParts,
  emptyState,
  emptyStateHasHatch,
} from "../../src/lib/empty";
import type { EmptyCause } from "../../src/lib/empty";

describe("typed empty-state coverage (SIG-UI-086)", () => {
  it("every declared EmptyCause has copy — a surface or a kind row", () => {
    for (const cause of EMPTY_CAUSES) {
      expect(emptyCauseCovered(cause), `cause ${cause} has no copy anywhere`).toBe(true);
    }
  });

  it("every EmptySurface resolves to a five-part record with a named cause", () => {
    for (const surface of EMPTY_SURFACES) {
      const parts = emptyState(surface).parts;
      expect(parts, surface).toBeDefined();
      expect(EMPTY_CAUSES, `${surface} cause`).toContain(parts!.cause);
    }
  });

  it("the kind registry covers exactly the unsurfaced causes", () => {
    expect(Object.keys(EMPTY_KIND_PARTS).sort()).toEqual(
      ["degraded", "filtered_none", "not_monitored", "not_redistributable"].sort(),
    );
    for (const [cause, parts] of Object.entries(EMPTY_KIND_PARTS)) {
      expect(parts.cause).toBe(cause);
      // The three non-absence kinds render no hatch; not_monitored IS a
      // coverage absence and hatches (SIG-UI-151).
      expect(emptyStateHasHatch(parts.cause as EmptyCause)).toBe(
        cause === "not_monitored",
      );
      for (const id of Object.values(parts.batchIds)) {
        expect(id).toMatch(/^EK-\d+$/);
      }
    }
  });

  it("kind copy follows the five-part pattern and never calls a non-absence a research gap", () => {
    for (const parts of Object.values(EMPTY_KIND_PARTS)) {
      expect(parts.state.trim()).not.toBe("empty");
      expect(parts.missing.length).toBeGreaterThan(0);
      expect(parts.nearby.length).toBeGreaterThan(0);
      expect(parts.change.length).toBeGreaterThan(0);
      expect(
        `${parts.state} ${parts.missing} ${parts.nearby} ${parts.change}`.toLowerCase(),
      ).not.toContain("research gap");
    }
  });

  it("filtered_none requires the caller's unfiltered route; the other kinds have canonical targets", () => {
    expect(() => emptyKindParts("filtered_none")).toThrow();
    const parts = emptyKindParts("filtered_none", { action: { href: "/sources/" } });
    expect(parts.action.href).toBe("/sources/");
    expect(parts.action.label).toBe("Clear filters");
    expect(emptyKindParts("not_redistributable").action.href).toBe("/sources/");
    // Bare route — EmptyState wraps it in withBase() at render (the
    // root-absolute-paths baseline counts leading-slash literals).
    expect(emptyKindParts("degraded").action.href).toBe("status/");
    expect(() => emptyKindParts("not_researched")).toThrow();
  });
});
