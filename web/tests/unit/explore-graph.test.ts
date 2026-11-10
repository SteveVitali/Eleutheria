// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// P37.27 (K2 GX-09b) — the explore-graph contract: filters narrow the emitted
// graph with disclosed drop counts, ego expansion composes the twin's
// relations bounded, the BFS path lists every hop with evidence (≤3
// publishable, longer SPECULATIVE, disconnected is a typed "no path" — never
// "not connected"), the sort is descriptive, and the neighbourhood scope is
// the `hops=` ring.
import { describe, it, expect } from "vitest";
import {
  ACCESS_COMPOSING_RELATIONS,
  applyFilters,
  datedRange,
  egoFromTwin,
  EMPTY_FILTERS,
  entityHrefOf,
  isEntityTwinsIndex,
  jurisdictionPlaceFor,
  mergeEgo,
  neighbourhood,
  pathPair,
  searchGraphNodes,
  shortestPath,
  sortNodes,
  SPECULATIVE_HOPS,
  twinDocHref,
  twinIndexHref,
} from "../../src/lib/explore-graph";
import type { OverviewEdge, OverviewNode } from "../../src/lib/graph-overview";
import { ENTITY_PAGE_TWIN_FIXTURE } from "../../src/lib/entity-page";

const node = (key: string, over: Partial<OverviewNode> = {}): OverviewNode => ({
  key,
  label: over.label ?? key,
  band: over.band ?? "agency",
  place: over.place ?? null,
  href: over.href ?? null,
  count: over.count ?? 0,
  x: over.x ?? 0,
  y: over.y ?? 0,
});

const edge = (src: string, dst: string, over: Partial<OverviewEdge> = {}): OverviewEdge => ({
  src,
  dst,
  relation: over.relation ?? "configured access to",
  evidenceCount: over.evidenceCount ?? 1,
  memberCount: 0,
  date: over.date ?? null,
  dateKind: over.date ? "observed" : "undated",
  currency: over.currency ?? "UNDATED",
  sources: over.sources ?? [],
});

// a—b—c—d chain plus an isolated pair e—f
const NODES = [
  node("a", { label: "Alpha PD", place: "usa-ok" }),
  node("b", { label: "Beta Solutions", band: "vendor", place: "usa-tx" }),
  node("c", { label: "Chi City", band: "agency", place: "usa-ga" }),
  node("d", { label: "Delta ALPR", band: "technology" }),
  node("e", { label: "Echo" }),
  node("f", { label: "Foxtrot" }),
];
const EDGES = [
  edge("a", "b", { date: "2020-01-28", currency: "HISTORICAL", sources: ["EFF Data Driven"] }),
  edge("b", "c", { relation: "sells to", date: "2023-05-01", currency: "AGING", sources: ["Atlas"] }),
  edge("c", "d", { relation: "uses", currency: "UNDATED" }),
  edge("e", "f", { relation: "sells to" }),
];

describe("filters (K2 §5.3)", () => {
  it("no facets returns the graph untouched", () => {
    const r = applyFilters(NODES, EDGES, EMPTY_FILTERS);
    expect(r.nodes).toHaveLength(NODES.length);
    expect(r.edges).toHaveLength(EDGES.length);
    expect(r.activeCount).toBe(0);
  });

  it("kind keeps only matching bands; an edge needs a surviving endpoint", () => {
    const r = applyFilters(NODES, EDGES, { ...EMPTY_FILTERS, kinds: ["vendor"] });
    expect(r.nodes.map((n) => n.key)).toEqual(expect.arrayContaining(["b", "a", "c"]));
    // edges touching the vendor survive (either-endpoint rule)
    expect(r.edges.map((e) => `${e.src}-${e.dst}`)).toEqual(["a-b", "b-c"]);
  });

  it("relation keeps only the named edge kinds (access kinds never merged)", () => {
    const r = applyFilters(NODES, EDGES, { ...EMPTY_FILTERS, relations: ["configured access to"] });
    expect(r.edges).toHaveLength(1);
    expect(r.edges[0]!.relation).toBe("configured access to");
  });

  it("currency and dated narrow honestly; undated edges outside a range are disclosed", () => {
    const cur = applyFilters(NODES, EDGES, { ...EMPTY_FILTERS, currency: "historical" });
    expect(cur.edges.map((e) => `${e.src}-${e.dst}`)).toEqual(["a-b"]);
    const dated = applyFilters(NODES, EDGES, {
      ...EMPTY_FILTERS,
      dated: { from: "2021", to: "2024" },
    });
    expect(dated.edges.map((e) => `${e.src}-${e.dst}`)).toEqual(["b-c"]);
    expect(dated.droppedUndatedEdges).toBeGreaterThan(0);
  });

  it("source and technology narrow by their vocabularies", () => {
    const r = applyFilters(NODES, EDGES, { ...EMPTY_FILTERS, sources: ["EFF Data Driven"] });
    expect(r.edges).toHaveLength(1);
    const tech = applyFilters(NODES, EDGES, { ...EMPTY_FILTERS, technologies: ["delta alpr"] });
    // the named tech node stays; other-band nodes reachable via its edge stay
    expect(tech.nodes.map((n) => n.key)).toContain("d");
    expect(tech.edges.map((e) => `${e.src}-${e.dst}`)).toEqual(["c-d"]);
  });

  it("jurisdiction prefixes match place subtrees, edges keep either endpoint", () => {
    const r = applyFilters(NODES, EDGES, { ...EMPTY_FILTERS, jurisdictionPlaces: ["usa-ok"] });
    // a matches; b survives via the a–b edge even though its own place is usa-tx
    expect(r.nodes.map((n) => n.key)).toEqual(expect.arrayContaining(["a", "b"]));
    expect(r.edges.map((e) => `${e.src}-${e.dst}`)).toEqual(["a-b"]);
  });
});

describe("expansion (the twin ego, bounded)", () => {
  it("folds relation items into counterparty nodes + directed edges", () => {
    const ego = egoFromTwin(ENTITY_PAGE_TWIN_FIXTURE, "e:acme");
    const labels = ego.nodes.map((n) => n.label);
    expect(labels).toContain("Vigilant Solutions (LEARN)");
    // outbound: expanded → counterparty; inbound (camera operator) reversed
    const outbound = ego.edges.find((e) => e.relation === "configured sharing partner")!;
    expect(outbound.src).toBe("e:acme");
    expect(outbound.evidenceCount).toBe(1);
    expect(outbound.currency).toBe("HISTORICAL");
    const inbound = ego.edges.find((e) => e.relation === "camera operator")!;
    expect(inbound.dst).toBe("e:acme");
    expect(ego.moreRelations).toBe(2); // the twin's `more` is never smoothed
  });

  it("mergeEgo dedups by key and never mutates its inputs", () => {
    const ego = {
      nodes: [node("x", { label: "X" }), node("a", { label: "Alpha PD" })],
      edges: [edge("a", "x", { relation: "knows" }), edge("a", "b")],
    };
    const before = EDGES.length;
    const merged = mergeEgo(NODES, EDGES, ego, NODES[0]);
    expect(merged.nodes.map((n) => n.key)).toContain("x");
    expect(merged.nodes.filter((n) => n.key === "a")).toHaveLength(1);
    expect(merged.edges).toHaveLength(before + 1); // the dup a–b edge is not doubled
    expect(EDGES).toHaveLength(before);
  });
});

describe("the path finder (SIG-UI-120, SIG-RECON-049)", () => {
  it("returns the shortest hop list with per-hop edges", () => {
    const r = shortestPath(NODES, EDGES, "a", "d");
    expect(r.kind).toBe("path");
    expect(r.hops.map((h) => `${h.from}-${h.to}`)).toEqual(["a-b", "b-c", "c-d"]);
    expect(r.hops[0]!.edge.relation).toBe("configured access to");
    expect(r.speculative).toBe(false);
  });

  it("labels a path beyond the hop threshold speculative", () => {
    const chain = [node("n0"), node("n1"), node("n2"), node("n3"), node("n4")];
    const chEdges = [
      edge("n0", "n1"),
      edge("n1", "n2"),
      edge("n2", "n3"),
      edge("n3", "n4"),
    ];
    const r = shortestPath(chain, chEdges, "n0", "n4");
    expect(r.kind).toBe("path");
    expect(r.hops).toHaveLength(SPECULATIVE_HOPS + 1);
    expect(r.speculative).toBe(true);
  });

  it("a disconnected pair is a typed no-path, never not-connected", () => {
    const r = shortestPath(NODES, EDGES, "a", "f");
    expect(r.kind).toBe("no-path");
    expect(r.hops).toHaveLength(0);
  });

  it("a missing endpoint is named", () => {
    const r = shortestPath(NODES, EDGES, "a", "ghost");
    expect(r.kind).toBe("missing-endpoint");
    expect(r.missing).toBe("ghost");
  });

  it("access traversal composes only configured-access edges", () => {
    expect(ACCESS_COMPOSING_RELATIONS).toEqual(["configured access to"]);
    const edges = [
      edge("a", "b", { relation: "observed access to" }),
      edge("a", "b", { relation: "configured access to" }),
    ];
    const r = shortestPath(NODES, edges, "a", "b", { composingOnly: true });
    expect(r.kind).toBe("path");
    expect(r.hops[0]!.edge.relation).toBe("configured access to");
    const blocked = shortestPath(NODES, [edges[0]!], "a", "b", { composingOnly: true });
    expect(blocked.kind).toBe("no-path");
  });
});

describe("hops neighbourhood + sort + search + decode", () => {
  it("neighbourhood rings are BFS-bounded", () => {
    expect([...neighbourhood(NODES, EDGES, "a", 1)].sort()).toEqual(["a", "b"]);
    expect([...neighbourhood(NODES, EDGES, "a", 2)].sort()).toEqual(["a", "b", "c"]);
  });

  it("the node sort is descriptive and stable", () => {
    const byCount = sortNodes(NODES, EDGES, "count", "desc");
    expect(byCount[0]!.key).toBe("b"); // degree 2
    const byLabel = sortNodes(NODES, EDGES, "label", null);
    expect(byLabel[0]!.label).toBe("Alpha PD");
  });

  it("search-to-node ranks word-prefix first", () => {
    const r = searchGraphNodes(NODES, "beta");
    expect(r[0]!.key).toBe("b");
    expect(searchGraphNodes(NODES, "")).toHaveLength(0);
  });

  it("the twin manifest + urls + pair decode are shape-honest", () => {
    expect(twinIndexHref("/entity/agency/x--y/")).toBe("/entity/agency/x--y/index.json");
    expect(twinDocHref("/entity/agency/x--y/", "sig_graph")).toBe(
      "/entity/agency/x--y/index.sig_graph.json",
    );
    expect(
      isEntityTwinsIndex({
        schema: "sig.entity-twins/1",
        key: "x--y",
        twins: [{ compartment: "sig_graph", path: "index.sig_graph.json" }],
      }),
    ).toBe(true);
    expect(isEntityTwinsIndex({ schema: "sig.entity-page/1", twins: [] })).toBe(false);
    expect(pathPair("a~b")).toEqual({ a: "a", b: "b" });
    expect(pathPair("ab")).toBeNull();
    expect(datedRange("2020..2024-06")).toEqual({ from: "2020", to: "2024-06" });
    expect(datedRange("bogus")).toBeNull();
    expect(jurisdictionPlaceFor("iso3166-2:US-OK", [
      { jkey: "iso3166-2:US-OK", place: "usa-ok", label: "Oklahoma" },
    ])?.place).toBe("usa-ok");
    expect(entityHrefOf(node("n", { href: "/entity/org/x--y/" }))).toBe("/entity/org/x--y/");
    expect(entityHrefOf(node("n", { href: "/graphs/x/" }))).toBeNull();
    expect(entityHrefOf(node("n"))).toBeNull();
  });
});
