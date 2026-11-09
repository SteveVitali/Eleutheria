// SPDX-License-Identifier: Apache-2.0
/** P37.24 (GX-08a) — the sig.graph-overview/1 web mirror. */
import { describe, expect, it } from "vitest";
import {
  COMPONENTS_INDEX_SCHEMA,
  GRAPH_INDEX_SCHEMA,
  GRAPH_OVERVIEW_SCHEMA,
  decodeComponentsIndex,
  decodeGraphIndex,
  decodeOverview,
  mergeOverviews,
  overviewAtPlace,
} from "../../src/lib/graph-overview";
import {
  GRAPH_INDEX_FIXTURE,
  GRAPH_OVERVIEW_FIXTURES,
} from "../../src/lib/graph-overview-fixture";
import {
  getComponentsIndex,
  getGraphIndex,
  getGraphOverview,
  getGraphOverviewPlace,
} from "../../src/lib/data";

describe("decodeOverview", () => {
  it("decodes the columnar doc to labelled nodes and H-2 edges", () => {
    const ov = decodeOverview(GRAPH_OVERVIEW_FIXTURES.supply![0]);
    expect(ov.id).toBe("supply");
    expect(ov.nodes.length).toBe(5);
    const labels = ov.nodes.map((n) => n.label);
    // SIG-UI-108 — real display labels, never raw identifiers.
    expect(labels).toContain("Vigilant Solutions (LEARN)");
    expect(ov.edges.length).toBe(4);
    const e = ov.edges[0]!;
    // SIG-EXPORT-015 — relation, date, currency, sources off the claims.
    expect(e.relation).toBe("sells to");
    expect(e.date).toBe("2020-01-28");
    expect(e.currency).toBe("STALE");
    expect(e.sources).toContain("OKC procurement");
    expect(ov.positionNote).toContain("no geographic meaning");
  });

  it("fails closed on a foreign schema", () => {
    expect(() => decodeOverview({ schema: "sig.other/1" })).toThrow();
  });
});

describe("mergeOverviews", () => {
  it("unions compartments by node key and edge triple", () => {
    const a = decodeOverview(GRAPH_OVERVIEW_FIXTURES.funding![0]);
    const merged = mergeOverviews([a, a])!;
    expect(merged.nodes.length).toBe(2);
    expect(merged.edges.length).toBe(1);
  });
});

describe("overviewAtPlace", () => {
  it("keeps edges with either endpoint inside the subtree", () => {
    const ov = decodeOverview(GRAPH_OVERVIEW_FIXTURES.supply![0]);
    const scoped = overviewAtPlace(ov, "usa-ok");
    expect(scoped.nodes.length).toBeGreaterThan(0);
    expect(scoped.edges.some((e) => e.relation === "sells to")).toBe(true);
    const empty = overviewAtPlace(ov, "usa-tx");
    expect(empty.edges.length).toBe(0);
  });
});

describe("data layer", () => {
  it("serves the committed fixtures in fixtures mode", () => {
    const idx = getGraphIndex();
    expect(idx.map((r) => r.id).sort()).toEqual([
      "access",
      "adoption",
      "funding",
      "governance",
      "operators",
      "supply",
      "types",
    ]);
    const ov = getGraphOverview("operators")!;
    expect(ov.edges.length).toBe(1);
  });

  it("decodes the access matrix + member counts and serves the place slice", () => {
    const ov = getGraphOverview("access")!;
    // S6R-12 — the share-list overview files under the CC BY-SA compartment.
    expect(ov.compartment).toBe("portal");
    expect(ov.capActions.join(" ")).toContain("matrix fold");
    expect(Math.max(...ov.edges.map((e) => e.memberCount))).toBeGreaterThan(0);
    const slice = getGraphOverviewPlace("access", "usa-ok")!;
    expect(slice).not.toBeNull();
    expect(slice.slice).toBe("usa-ok");
    // the slice carries the unfolded agency-level egos, not place cells.
    expect(slice.nodes.some((n) => n.band === "agency")).toBe(true);
  });

  it("decodes the components index", () => {
    const idx = getComponentsIndex();
    expect(idx.length).toBeGreaterThan(0);
    expect(idx[0]!.components[0]!.componentId).toBe("cmp-0001");
    expect(() =>
      decodeComponentsIndex({ schema: COMPONENTS_INDEX_SCHEMA, components: [] }),
    ).not.toThrow();
  });

  it("decodes the index document", () => {
    expect(() =>
      decodeGraphIndex({ schema: GRAPH_INDEX_SCHEMA, overviews: [] }),
    ).not.toThrow();
  });
});
