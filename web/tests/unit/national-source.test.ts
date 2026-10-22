// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// P35.51 (SIG-FIND-005, K0 §4.12.6): SIG_DATA_SOURCE=national is a DECLARED
// overlay — the generated national fixture supplies the heavy artifacts it
// names (web/map.json, web/network.json, web/tiles/*-sites.pmtiles,
// manifest.json, <comp>/ATTRIBUTION.json, web/analytics/*) and every other
// getter keeps serving the committed fixtures. A missing or malformed
// overlay artifact fails LOUD, never a silent fixtures fall-back
// (SIG-UI-036) — the same contract export mode carries.

import { mkdtempSync, mkdirSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { afterEach, describe, expect, it } from "vitest";
import {
  getFreshness,
  getMapSites,
  getNetwork,
} from "../../src/lib/data";
import { FRESHNESS_ROWS } from "../../src/lib/corrections-methodology-fixture";
import { MAP_ASSETS, NETWORK_NODES } from "../../src/lib/map-network-fixture";

const OLD: Record<string, string | undefined> = {};
function setEnv(key: string, value: string | undefined) {
  if (!(key in OLD)) OLD[key] = process.env[key];
  if (value === undefined) delete process.env[key];
  else process.env[key] = value;
}
afterEach(() => {
  for (const [k, v] of Object.entries(OLD)) {
    if (v === undefined) delete process.env[k];
    else process.env[k] = v;
    delete OLD[k];
  }
});

/** A minimal national overlay dir: only the artifacts the overlay declares. */
function nationalFixtureDir(): string {
  const dir = mkdtempSync(join(tmpdir(), "sig-national-"));
  mkdirSync(join(dir, "web"), { recursive: true });
  writeFileSync(
    join(dir, "web", "map.json"),
    JSON.stringify({
      layers: [],
      assets: [
        {
          id: "site:syn-000001",
          label: "Synthetic Alpr Fixed 000001",
          jurisdiction: "syn.state.01",
          technology: "alpr-fixed",
          technologyStatus: "resolved",
          tier: 0,
          lat: 35.1,
          lon: -97.5,
          precision: "cell centroid",
        },
      ],
      jurisdiction_indicators: [],
    }),
  );
  writeFileSync(
    join(dir, "web", "network.json"),
    JSON.stringify({
      nodes: [
        {
          id: "agency:syn-focus",
          label: "Synthetic Metro Police Department",
          type: "agency",
        },
      ],
      edges: [
        {
          from: "agency:syn-focus",
          to: "vendor:syn-00001",
          access_kind: "declared_policy",
          relation: "shares data under a declared policy",
        },
      ],
      access_paths: [],
    }),
  );
  return dir;
}

describe("SIG_DATA_SOURCE=national — the declared overlay (P35.51)", () => {
  it("getMapSites reads the overlay's web/map.json, not the fixtures", () => {
    const dir = nationalFixtureDir();
    setEnv("SIG_DATA_SOURCE", "national");
    setEnv("SIG_NATIONAL_DIR", dir);
    const sites = getMapSites();
    expect(sites).toHaveLength(1);
    expect(sites[0].id).toBe("site:syn-000001");
    expect(sites[0]).not.toBe(MAP_ASSETS[0]);
  });

  it("getNetwork reads the overlay's web/network.json, not the fixtures", () => {
    const dir = nationalFixtureDir();
    setEnv("SIG_DATA_SOURCE", "national");
    setEnv("SIG_NATIONAL_DIR", dir);
    const net = getNetwork();
    expect(net.nodes.map((n) => n.id)).toContain("agency:syn-focus");
    expect(net.nodes).not.toBe(NETWORK_NODES);
    expect(net.edges[0].from).toBe("agency:syn-focus");
  });

  it("uncovered getters keep serving the committed fixtures", () => {
    const dir = nationalFixtureDir();
    setEnv("SIG_DATA_SOURCE", "national");
    setEnv("SIG_NATIONAL_DIR", dir);
    // The overlay names no freshness artifact — the committed corpus serves.
    expect(getFreshness()).toBe(FRESHNESS_ROWS);
  });

  it("a missing overlay artifact fails LOUD — never a silent fixtures fall-back", () => {
    const dir = mkdtempSync(join(tmpdir(), "sig-national-empty-"));
    setEnv("SIG_DATA_SOURCE", "national");
    setEnv("SIG_NATIONAL_DIR", dir);
    expect(() => getMapSites()).toThrow(/SIG_DATA_SOURCE=national.*missing/);
    expect(() => getNetwork()).toThrow(/national fixture artifact is missing/);
  });

  it("a malformed overlay artifact fails LOUD", () => {
    const dir = nationalFixtureDir();
    writeFileSync(join(dir, "web", "map.json"), "{ not json");
    writeFileSync(
      join(dir, "web", "network.json"),
      JSON.stringify({ nodes: "not-an-array" }),
    );
    setEnv("SIG_DATA_SOURCE", "national");
    setEnv("SIG_NATIONAL_DIR", dir);
    expect(() => getMapSites()).toThrow(/not valid JSON/);
    expect(() => getNetwork()).toThrow(/"nodes" and "edges" arrays/);
  });

  it("fixtures mode ignores SIG_NATIONAL_DIR entirely", () => {
    setEnv("SIG_DATA_SOURCE", "fixtures");
    setEnv("SIG_NATIONAL_DIR", "/nonexistent/national");
    expect(getMapSites()).toBe(MAP_ASSETS);
  });
});
