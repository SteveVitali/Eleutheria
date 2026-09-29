// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

import { afterEach, beforeAll, describe, expect, it } from "vitest";
import { mkdtempSync, mkdirSync, writeFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

import {
  capRows,
  getCorrections,
  getCoverage,
  getDossierIndex,
  getEvidence,
  getFreshness,
  getMapSites,
  getNetwork,
  getResearchQueue,
  getSiteMetadata,
  getWatch,
} from "../../src/lib/data";
import { AS_OF, RULESET_VERSION } from "../../src/lib/fixtures";
import { MAP_ASSETS, NETWORK_NODES, ACCESS_PATHS } from "../../src/lib/map-network-fixture";
import { FRESHNESS_ROWS, COVERAGE_METRICS, CORRECTIONS, RESEARCH_QUEUE } from "../../src/lib/corrections-methodology-fixture";
import { WATCH_ITEMS, EVIDENCE_ARTIFACTS, CLAIM_VIEWS } from "../../src/lib/watch-evidence-fixture";

// data.ts reads env at CALL time, so a static import is fine — restore env between cases.
const saved = { source: process.env.SIG_DATA_SOURCE, dir: process.env.SIG_EXPORT_DIR };
afterEach(() => {
  if (saved.source === undefined) delete process.env.SIG_DATA_SOURCE;
  else process.env.SIG_DATA_SOURCE = saved.source;
  if (saved.dir === undefined) delete process.env.SIG_EXPORT_DIR;
  else process.env.SIG_EXPORT_DIR = saved.dir;
});

// A complete export bundle, in the P27.1 contract shape the getters parse.
let bundle: string;
beforeAll(() => {
  bundle = mkdtempSync(join(tmpdir(), "sig-export-"));
  const web = join(bundle, "web");
  mkdirSync(web, { recursive: true });
  const w = (name: string, payload: unknown) => writeFileSync(join(web, name), JSON.stringify(payload));
  w("map.json", { layers: [], assets: MAP_ASSETS, jurisdiction_indicators: [] });
  w("network.json", { nodes: NETWORK_NODES, edges: [], access_paths: ACCESS_PATHS });
  w("freshness.json", FRESHNESS_ROWS);
  w("coverage.json", COVERAGE_METRICS);
  w("watch.json", WATCH_ITEMS);
  w("evidence.json", { artifacts: EVIDENCE_ARTIFACTS, claim_views: CLAIM_VIEWS });
  w("corrections.json", CORRECTIONS);
  w("research_queue.json", RESEARCH_QUEUE);
  w("dossier_index.json", []);
  // The release manifest at the export-dir ROOT (getSiteMetadata reads it in export mode).
  writeFileSync(
    join(bundle, "manifest.json"),
    JSON.stringify({
      reproducibility_inputs: {
        as_of_snapshot: "2026-09-01",
        as_of_belief: "2026-09-15",
        ruleset_version: "resolver-ruleset-2026.09",
      },
    }),
  );
});

const MISSING = join(tmpdir(), "sig-export-does-not-exist-xyz");

describe("P27.5 web data layer — fixtures mode returns the committed constants", () => {
  it("every surface getter returns its fixture", () => {
    process.env.SIG_DATA_SOURCE = "fixtures";
    expect(getMapSites()).toEqual(MAP_ASSETS);
    expect(getNetwork().nodes).toEqual(NETWORK_NODES);
    expect(getNetwork().accessPaths).toEqual(ACCESS_PATHS);
    expect(getFreshness()).toEqual(FRESHNESS_ROWS);
    expect(getCoverage()).toEqual(COVERAGE_METRICS);
    expect(getWatch()).toEqual(WATCH_ITEMS);
    expect(getEvidence().artifacts).toEqual(EVIDENCE_ARTIFACTS);
    expect(getEvidence().claimViews).toEqual(CLAIM_VIEWS);
    expect(getCorrections()).toEqual(CORRECTIONS);
    expect(getResearchQueue()).toEqual(RESEARCH_QUEUE);
    // The dossier index includes the SIG-PUB-017 FR/BE demonstration dossiers.
    expect(getDossierIndex().length).toBeGreaterThan(0);
  });
});

describe("P27.5 web data layer — export mode reads <exportDir>/web/*.json", () => {
  it("every surface getter reads the export bytes", () => {
    process.env.SIG_DATA_SOURCE = "export";
    process.env.SIG_EXPORT_DIR = bundle;
    expect(getMapSites()).toEqual(MAP_ASSETS);
    expect(getNetwork().nodes).toEqual(NETWORK_NODES);
    expect(getNetwork().accessPaths).toEqual(ACCESS_PATHS);
    expect(getFreshness()).toEqual(FRESHNESS_ROWS);
    expect(getCoverage()).toEqual(COVERAGE_METRICS);
    expect(getWatch()).toEqual(WATCH_ITEMS);
    expect(getEvidence().artifacts).toEqual(EVIDENCE_ARTIFACTS);
    expect(getEvidence().claimViews).toEqual(CLAIM_VIEWS);
    expect(getCorrections()).toEqual(CORRECTIONS);
    expect(getResearchQueue()).toEqual(RESEARCH_QUEUE);
  });
});

describe("P27.5 web data layer — export mode FAILS LOUD on a missing artifact", () => {
  const cases: [string, () => unknown][] = [
    ["getMapSites", getMapSites],
    ["getNetwork", getNetwork],
    ["getFreshness", getFreshness],
    ["getCoverage", getCoverage],
    ["getWatch", getWatch],
    ["getEvidence", getEvidence],
    ["getCorrections", getCorrections],
    ["getResearchQueue", getResearchQueue],
    ["getDossierIndex", getDossierIndex],
  ];
  for (const [name, fn] of cases) {
    it(`${name} throws when the artifact is missing (never a silent fixtures fall-back)`, () => {
      process.env.SIG_DATA_SOURCE = "export";
      process.env.SIG_EXPORT_DIR = MISSING;
      expect(() => fn()).toThrow(/export artifact is missing/);
    });
  }
});

describe("P27.5 web data layer — malformed artifact fails loud", () => {
  it("getMapSites rejects a bundle whose map.json lacks an assets array", () => {
    const bad = mkdtempSync(join(tmpdir(), "sig-export-bad-"));
    mkdirSync(join(bad, "web"), { recursive: true });
    writeFileSync(join(bad, "web", "map.json"), JSON.stringify({ layers: [] }));
    process.env.SIG_DATA_SOURCE = "export";
    process.env.SIG_EXPORT_DIR = bad;
    expect(() => getMapSites()).toThrow(/assets/);
    rmSync(bad, { recursive: true, force: true });
  });
});

describe("P27.6 site metadata — belief-pinned defaults from the export manifest", () => {
  it("fixtures mode returns the committed AS_OF / RULESET_VERSION constants", () => {
    process.env.SIG_DATA_SOURCE = "fixtures";
    const meta = getSiteMetadata();
    expect(meta.asOf).toEqual(AS_OF);
    expect(meta.rulesetVersion).toBe(RULESET_VERSION);
  });

  it("export mode reads reproducibility_inputs from <exportDir>/manifest.json", () => {
    process.env.SIG_DATA_SOURCE = "export";
    process.env.SIG_EXPORT_DIR = bundle;
    const meta = getSiteMetadata();
    expect(meta.asOf.as_of_world).toBe("2026-09-01");
    expect(meta.asOf.as_of_belief).toBe("2026-09-15");
    expect(meta.asOf.belief_pinned).toBe(true);
    expect(meta.rulesetVersion).toBe("resolver-ruleset-2026.09");
    // NOT the frozen fixtures constant (real metadata, ADR-093).
    expect(meta.asOf.as_of_world).not.toBe(AS_OF.as_of_world);
  });

  it("export mode fails loud when the manifest is missing", () => {
    process.env.SIG_DATA_SOURCE = "export";
    process.env.SIG_EXPORT_DIR = MISSING;
    expect(() => getSiteMetadata()).toThrow(/export manifest is missing/);
  });

  it("export mode fails loud on a manifest without reproducibility_inputs", () => {
    const bad = mkdtempSync(join(tmpdir(), "sig-export-badmanifest-"));
    writeFileSync(join(bad, "manifest.json"), JSON.stringify({ release_id: "x" }));
    process.env.SIG_DATA_SOURCE = "export";
    process.env.SIG_EXPORT_DIR = bad;
    expect(() => getSiteMetadata()).toThrow(/reproducibility_inputs/);
    rmSync(bad, { recursive: true, force: true });
  });
});

describe("P27.5 build-time pagination/summarisation (capRows)", () => {
  it("passes through when under the cap and reports the honest total", () => {
    const r = capRows([1, 2, 3], 10);
    expect(r).toEqual({ rows: [1, 2, 3], total: 3, shown: 3, truncated: false });
  });
  it("truncates over the cap, preserving the total", () => {
    const r = capRows([1, 2, 3, 4, 5], 2);
    expect(r.rows).toEqual([1, 2]);
    expect(r.total).toBe(5);
    expect(r.shown).toBe(2);
    expect(r.truncated).toBe(true);
  });
});
