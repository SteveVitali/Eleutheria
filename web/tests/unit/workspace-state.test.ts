// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * The `sig.workspace-state/1` contract (P32.15, SIG-FIND-004, ADR-134): the
 * versioned release/compartment/query/filter/focus/view state shared by the
 * three public islands. Round-trip, visible-failure and focus-scope rules are
 * pinned here — a regression that silently drops or mangles state fails red.
 */
import { describe, expect, it } from "vitest";
import {
  DEFAULT_WORKSPACE_STATE,
  LOCATION_FILTERS,
  WORKSPACE_STATE_VERSION,
  WORKSPACE_VIEWS,
  WORKSPACE_VIEW_PATHS,
  clearFocusOutOfScope,
  evidenceAnchorHref,
  pageView,
  parseWorkspaceState,
  recordRoutes,
  serializeWorkspaceState,
  splitRecordKey,
  viewHref,
  withFocus,
  withSearchPatch,
  workspaceHref,
} from "../../src/lib/workspace-state";
import type { WorkspaceState } from "../../src/lib/workspace-state";

const FULL: WorkspaceState = {
  release: "p-".padEnd(66, "a"),
  collection: ["osm_physical", "sig_graph"],
  collectionSpecified: true,
  q: "flock",
  kind: ["deployment"],
  jurisdiction: ["oklahoma", "unreported"],
  technology: ["alpr"],
  source: ["atlas"],
  location: "no-public-point",
  focus: "osm_physical:deployment:550e8400-e29b-41d4-a716-446655440000",
  view: "map",
  page: 3,
};

describe("parse ↔ serialize round-trip (SIG-FIND-004)", () => {
  it("round-trips a fully-populated state byte-for-byte", () => {
    const params = serializeWorkspaceState(FULL);
    const { state, issues } = parseWorkspaceState(params);
    expect(issues).toEqual([]);
    expect(state).toEqual(FULL);
  });

  it("emits the canonical parameter order with v first and view always present", () => {
    const keys = [...serializeWorkspaceState(FULL).keys()];
    expect(keys[0]).toBe("v");
    expect(keys).toEqual([
      "v",
      "release",
      "collection",
      "collection",
      "q",
      "kind",
      "jurisdiction",
      "jurisdiction",
      "technology",
      "source",
      "location",
      "focus",
      "view",
      "page",
    ]);
  });

  it("omits defaulted fields but always emits v and view", () => {
    const s = serializeWorkspaceState(DEFAULT_WORKSPACE_STATE).toString();
    expect(s).toBe(`v=${WORKSPACE_STATE_VERSION}&view=list`);
  });

  it("repeated facets keep multiplicity and order", () => {
    const { state } = parseWorkspaceState(
      "v=1&jurisdiction=a&jurisdiction=b&collection=x&collection=y&view=list",
    );
    expect(state.jurisdiction).toEqual(["a", "b"]);
    expect(state.collection).toEqual(["x", "y"]);
    expect(state.collectionSpecified).toBe(true);
  });

  it("an absent collection means ALL compartments; a bare collection= means NONE", () => {
    const absent = parseWorkspaceState("v=1&view=map").state;
    expect(absent.collectionSpecified).toBe(false);
    expect(absent.collection).toEqual([]);

    const none = parseWorkspaceState("v=1&collection=&view=map").state;
    expect(none.collectionSpecified).toBe(true);
    expect(none.collection).toEqual([]);

    // The empty selection round-trips — it never collapses back to "all".
    const ser = serializeWorkspaceState(none).toString();
    expect(ser).toContain("collection=");
    const roundTrip = parseWorkspaceState(ser).state;
    expect(roundTrip.collectionSpecified).toBe(true);
    expect(roundTrip.collection).toEqual([]);
  });
});

describe("visible failure on unknown combinations", () => {
  it("an unsupported version is reported, not silently reinterpreted", () => {
    const { issues } = parseWorkspaceState("v=9&q=x&view=list");
    expect(issues.join(" ")).toMatch(/version "9"/i);
  });

  it("an unknown view defaults AND reports", () => {
    const { state, issues } = parseWorkspaceState("view=galaxy");
    expect(state.view).toBe("list");
    expect(issues.join(" ")).toMatch(/unknown view/i);
  });

  it("an unknown location filter defaults to any AND reports", () => {
    const { state, issues } = parseWorkspaceState("location=inside");
    expect(state.location).toBe("any");
    expect(issues.join(" ")).toMatch(/location/i);
    for (const ok of LOCATION_FILTERS) {
      const p = parseWorkspaceState(`location=${ok}`);
      expect(p.state.location).toBe(ok);
      expect(p.issues).toEqual([]);
    }
  });

  it("a non-integer or out-of-range page defaults to 1 AND reports", () => {
    for (const bad of ["0", "-2", "x", "1.5"]) {
      const { state, issues } = parseWorkspaceState(`page=${bad}`);
      expect(state.page).toBe(1);
      expect(issues.length).toBeGreaterThan(0);
    }
    expect(parseWorkspaceState("page=4").state.page).toBe(4);
  });
});

describe("defaults + view helpers", () => {
  it("an absent release falls back to the build's latest activated release", () => {
    const { state } = parseWorkspaceState("", { release: "p-x" });
    expect(state.release).toBe("p-x");
    expect(parseWorkspaceState("release=p-y", { release: "p-x" }).state.release).toBe("p-y");
  });

  it("pageView resolves exactly the three canonical paths", () => {
    for (const v of WORKSPACE_VIEWS) {
      expect(pageView(WORKSPACE_VIEW_PATHS[v])).toBe(v);
    }
    expect(pageView("/dossier/")).toBeNull();
  });

  it("viewHref preserves the whole investigation state across views", () => {
    const href = viewHref(FULL, "network");
    expect(href.startsWith("/network/?")).toBe(true);
    const { state } = parseWorkspaceState(href.split("?")[1]!);
    expect({ ...state, view: "map" }).toEqual(FULL);
    expect(state.view).toBe("network");
  });
});

describe("pagination + focus-scope rules (S4 §7)", () => {
  it("withFocus selects/clears the record and resets pagination", () => {
    const s = withFocus({ ...FULL, page: 9 }, "c:t:id");
    expect(s.focus).toBe("c:t:id");
    expect(s.page).toBe(1);
    expect(withFocus(s, null).focus).toBeNull();
  });

  it("withSearchPatch always resets the page", () => {
    expect(withSearchPatch({ ...FULL, page: 7 }, { q: "new" }).page).toBe(1);
  });

  it("clearFocusOutOfScope clears only an out-of-scope focus — and says so", () => {
    const scoped = { ...FULL, focus: "a:b:c" };
    const gone = clearFocusOutOfScope(scoped, () => false);
    expect(gone.cleared).toBe(true);
    expect(gone.state.focus).toBeNull();
    const kept = clearFocusOutOfScope(scoped, (f) => f === "a:b:c");
    expect(kept.cleared).toBe(false);
    expect(kept.state.focus).toBe("a:b:c");
    expect(clearFocusOutOfScope({ ...scoped, focus: null }, () => false).cleared).toBe(false);
  });
});

describe("record-key resolution (ADR-132 namespaces)", () => {
  it("splitRecordKey accepts exactly a 3-part record key", () => {
    expect(splitRecordKey("osm_physical:deployment:uuid-1")).toEqual({
      compartment: "osm_physical",
      entityType: "deployment",
      entityId: "uuid-1",
    });
    // Island node/asset ids are NOT record keys — they never fabricate a route.
    expect(splitRecordKey("agency:okcpd")).toBeNull();
    expect(splitRecordKey("a:b:c:d")).toBeNull();
    expect(splitRecordKey("")).toBeNull();
  });

  it("recordRoutes maps a record key onto the released namespace", () => {
    const r = recordRoutes("p-123", "ccby3:deployment:u-9");
    expect(r?.pageHref).toBe("/r/p-123/c/ccby3/entity/deployment/u-9/");
    expect(r?.jsonHref).toBe("/r/p-123/c/ccby3/entity/deployment/u-9.json");
    expect(r?.compartmentHref).toBe("/r/p-123/c/ccby3/");
    expect(recordRoutes("p-123", "agency:okcpd")).toBeNull();
  });

  it("evidenceAnchorHref targets the released evidence anchor page", () => {
    expect(evidenceAnchorHref("p-1", "ccby3", "art-7")).toBe(
      "/r/p-1/c/ccby3/evidence/art-7/",
    );
  });
});

describe("workspaceHref", () => {
  it("carries state on an arbitrary path", () => {
    const href = workspaceHref("/map/", { ...DEFAULT_WORKSPACE_STATE, focus: "x" });
    expect(href).toBe("/map/?v=1&focus=x&view=list");
  });
});
