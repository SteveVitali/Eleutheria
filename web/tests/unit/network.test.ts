// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// The §39.4 network-explorer honest-rendering rules, tested on the pure logic
// (SIG-UI-022..025, SIG-IDENT-030, SIG-RECON-050).
import { describe, expect, it } from "vitest";
import {
  ACCESS_EDGE_STYLES,
  ACCESS_EDGE_TYPES,
  DEFAULT_ACCESS_EDGE_FILTER,
  DEFAULT_NETWORK_VIEW,
  MERGE_ACCESS_EDGES_BY_DEFAULT,
  SPECULATIVE_HOP_THRESHOLD,
  assertErDisclosures,
  assertPathValid,
  centralityStatistic,
  egoNetwork,
  filterAccessEdges,
  pathConfidence,
  pathHopCount,
  pathIsHeadline,
  pathIsSpeculative,
  pathOrgs,
  pathTemporalStatus,
} from "../../src/lib/network";
import type { AccessPath, ErQuality } from "../../src/lib/network";
import {
  ACCESS_PATHS,
  CENTRALITY_STATS,
  ER_QUALITY,
  HEADLINE_PATH,
  NETWORK_EDGES,
  NETWORK_NODES,
  SPECULATIVE_PATH,
} from "../../src/lib/map-network-fixture";

describe("ego network with expansion is the default (SIG-UI-022)", () => {
  it("defaults to ego, never a global graph", () => {
    expect(DEFAULT_NETWORK_VIEW).toBe("ego");
  });

  it("depth 1 is the immediate neighbourhood; deeper rings expand it", () => {
    const d1 = egoNetwork(NETWORK_NODES, NETWORK_EDGES, "agency:okcpd", 1);
    expect(d1.nodes.map((n) => n.id).sort()).toEqual(
      ["agency:okcpd", "agency:ocso", "rtcc:okc", "vendor:flock"].sort(),
    );
    const d2 = egoNetwork(NETWORK_NODES, NETWORK_EDGES, "agency:okcpd", 2);
    // Expanding pulls in Tulsa (via OCSO/Flock chain) — strictly more nodes.
    expect(d2.nodes.length).toBeGreaterThan(d1.nodes.length);
    // Every retained edge is fully inside the neighbourhood (no dangling half-edges).
    const ids = new Set(d2.nodes.map((n) => n.id));
    expect(d2.edges.every((e) => ids.has(e.from) && ids.has(e.to))).toBe(true);
  });

  it("rejects an unknown center", () => {
    expect(() => egoNetwork(NETWORK_NODES, NETWORK_EDGES, "nope")).toThrow();
  });
});

describe("three access edge types, distinct + independently filterable (SIG-UI-024)", () => {
  it("has exactly the three §12.2 types, never merged by default", () => {
    expect([...ACCESS_EDGE_TYPES]).toEqual(["configured_access", "observed_use", "declared_policy"]);
    expect(MERGE_ACCESS_EDGES_BY_DEFAULT).toBe(false);
  });

  it("each type has a DISTINCT non-colour glyph AND dash pattern", () => {
    const glyphs = ACCESS_EDGE_TYPES.map((k) => ACCESS_EDGE_STYLES[k].glyph);
    const dashes = ACCESS_EDGE_TYPES.map((k) => ACCESS_EDGE_STYLES[k].dash);
    expect(new Set(glyphs).size).toBe(3); // distinguishable without colour
    expect(new Set(dashes).size).toBe(3);
  });

  it("the three filter independently", () => {
    const onlyConfigured = filterAccessEdges(NETWORK_EDGES, {
      ...DEFAULT_ACCESS_EDGE_FILTER,
      observed_use: false,
      declared_policy: false,
    });
    expect(onlyConfigured.every((e) => e.access_kind === "configured_access")).toBe(true);
    const noPolicy = filterAccessEdges(NETWORK_EDGES, {
      ...DEFAULT_ACCESS_EDGE_FILTER,
      declared_policy: false,
    });
    expect(noPolicy.some((e) => e.access_kind === "declared_policy")).toBe(false);
    expect(noPolicy.some((e) => e.access_kind === "observed_use")).toBe(true);
  });
});

describe("inline ER-quality disclosure on EVERY centrality statistic (SIG-UI-023)", () => {
  it("cannot build a statistic without a valid ER-quality disclosure", () => {
    const bad = { ...ER_QUALITY, f1: 1.4 } as ErQuality;
    expect(() => centralityStatistic("x", "degree", 0.5, bad)).toThrow(/SIG-UI-023/);
    const noHoldout = { ...ER_QUALITY, holdout_version: "" } as ErQuality;
    expect(() => centralityStatistic("x", "degree", 0.5, noHoldout)).toThrow(/SIG-UI-023/);
  });

  it("every fixture statistic carries a non-empty inline disclosure at the statistic", () => {
    expect(CENTRALITY_STATS.length).toBeGreaterThan(0);
    for (const s of CENTRALITY_STATS) {
      expect(s.disclosure).toBeTruthy();
      expect(s.disclosure.toLowerCase()).toContain("entity resolution");
      expect(s.disclosure).toContain("F1");
      expect(s.er_quality.holdout_version).toBeTruthy();
    }
    expect(() => assertErDisclosures(CENTRALITY_STATS)).not.toThrow();
  });
});

describe("access-path closure: full hops, per-hop evidence, speculative label (SIG-UI-025)", () => {
  it("every hop carries evidence — an evidence-less hop is rejected", () => {
    for (const p of ACCESS_PATHS) expect(() => assertPathValid(p)).not.toThrow();
    const noEvidence: AccessPath = {
      hops: [
        { from_org: "a", to_org: "b", edge_label: "configured_access", scope: "partner", confidence: "probable", evidence: [] },
      ],
    };
    expect(() => assertPathValid(noEvidence)).toThrow(/SIG-UI-025/);
  });

  it("a path beyond the published hop threshold is speculative + not a headline", () => {
    expect(SPECULATIVE_HOP_THRESHOLD).toBe(3);
    expect(pathHopCount(HEADLINE_PATH)).toBeLessThanOrEqual(SPECULATIVE_HOP_THRESHOLD);
    expect(pathIsSpeculative(HEADLINE_PATH)).toBe(false);
    expect(pathIsHeadline(HEADLINE_PATH)).toBe(true);

    expect(pathHopCount(SPECULATIVE_PATH)).toBeGreaterThan(SPECULATIVE_HOP_THRESHOLD);
    expect(pathIsSpeculative(SPECULATIVE_PATH)).toBe(true);
    expect(pathIsHeadline(SPECULATIVE_PATH)).toBe(false);
  });

  it("confidence is the MINIMUM over hops, and the full org chain is exposed", () => {
    // HEADLINE_PATH hops are certain then probable → min is probable.
    expect(pathConfidence(HEADLINE_PATH)).toBe("probable");
    // SPECULATIVE_PATH includes possible hops → min is possible.
    expect(pathConfidence(SPECULATIVE_PATH)).toBe("possible");
    expect(pathOrgs(HEADLINE_PATH)).toEqual(["agency:okcpd", "rtcc:okc", "vendor:flock"]);
  });

  it("an expired hop taints the whole path historical", () => {
    const historical: AccessPath = {
      hops: [
        { from_org: "a", to_org: "b", edge_label: "configured_access", scope: "partner", confidence: "certain", evidence: ["c1"], expired: true },
        { from_org: "b", to_org: "c", edge_label: "configured_access", scope: "partner", confidence: "certain", evidence: ["c2"] },
      ],
    };
    expect(pathTemporalStatus(historical)).toBe("historical");
    expect(pathIsHeadline(historical)).toBe(false); // historical is never a headline
    expect(pathTemporalStatus(HEADLINE_PATH)).toBe("live");
  });
});
