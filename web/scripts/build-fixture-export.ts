// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * P27.5 fixture-export harness (verification only).
 *
 * Serialises the committed web fixtures into the P27.1 export layout —
 * `<outDir>/web/<artifact>.json` plus `dossiers.json` / `leverage.json` and a
 * `tiles/sig-infrastructure.pmtiles` — so `SIG_DATA_SOURCE=export
 * SIG_EXPORT_DIR=<outDir>` can be exercised against REAL on-disk bytes with
 * fixture-equivalent content. This is the P21.4 precedent (`sig-exports build
 * --jurisdiction okc` emits a fixture-equivalent bundle) extended to the ten P27.1
 * surfaces, and lets `npm run check` pass identically in both modes without a hosted
 * spine (D-P27.4-1 stays deferred). It is a TEST harness, not a shipped artifact:
 * production export bytes come from `sig-exports build --from-spine` (P27.4).
 *
 * Run:  node <esbuild-bundled>.mjs <outDir>          (see `npm run export:fixtures`)
 */

import { existsSync, copyFileSync, mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";

import { MAP_LAYERS, partitionByLocatability } from "../src/lib/map";
import { MAP_ASSETS, NETWORK_NODES, NETWORK_EDGES, ACCESS_PATHS } from "../src/lib/map-network-fixture";
import {
  FRESHNESS_ROWS,
  COVERAGE_METRICS,
  CORRECTIONS,
  RESEARCH_QUEUE,
} from "../src/lib/corrections-methodology-fixture";
import { WATCH_ITEMS, EVIDENCE_ARTIFACTS, CLAIM_VIEWS } from "../src/lib/watch-evidence-fixture";
import { DOSSIERS } from "../src/lib/dossier-fixture";
import { LEVERAGE_METRIC_FIXTURE } from "../src/lib/leverage-fixture";

const outDir = process.argv[2];
if (!outDir) {
  console.error("usage: build-fixture-export <outDir>");
  process.exit(2);
}

const webDir = join(outDir, "web");
mkdirSync(webDir, { recursive: true });

function write(name: string, payload: unknown): void {
  writeFileSync(join(webDir, name), JSON.stringify(payload, null, 2) + "\n", "utf-8");
}

const { jurisdictionIndicators } = partitionByLocatability(MAP_ASSETS);

// The ten P27.1 surface artifacts, in the frozen contract shape the getters parse.
write("map.json", {
  layers: MAP_LAYERS,
  assets: MAP_ASSETS,
  jurisdiction_indicators: jurisdictionIndicators.map((j) => ({ jurisdiction: j.jurisdiction })),
});
write("network.json", { nodes: NETWORK_NODES, edges: NETWORK_EDGES, access_paths: ACCESS_PATHS });
write("freshness.json", FRESHNESS_ROWS);
write("coverage.json", COVERAGE_METRICS);
write("watch.json", WATCH_ITEMS);
write("evidence.json", { artifacts: EVIDENCE_ARTIFACTS, claim_views: CLAIM_VIEWS });
write("corrections.json", CORRECTIONS);
write("research_queue.json", RESEARCH_QUEUE);
write(
  "dossier_index.json",
  DOSSIERS.map((d) => ({
    slug: d.slug,
    subject_label: d.subject_label,
    jurisdiction: d.jurisdiction,
    asOf: d.asOf,
  })),
);

// The pre-P27.5 surfaces the data layer already read (dossiers + leverage): the SIG-PUB-017
// FR/BE demonstration dossiers are appended by the getters in both modes, so the bundle
// carries only the base set (as `sig-exports build --jurisdiction okc` does). When this
// harness OVERLAYS a real `sig-exports build --jurisdiction okc` bundle (which already
// emits these from build_web_dossiers), we leave the real files in place — only the ten
// P27.5 surface artifacts are added.
if (!existsSync(join(webDir, "dossiers.json"))) write("dossiers.json", DOSSIERS);
if (!existsSync(join(webDir, "leverage.json"))) write("leverage.json", LEVERAGE_METRIC_FIXTURE);

// The map's self-hosted PMTiles archive the export-tiles Astro integration copies into
// the build (astro.config.mjs). Reuse a real rendered tile if one is on disk; otherwise
// emit a minimal PMTiles v3 header so the build has a byte-real archive to copy.
const tilesDir = join(webDir, "tiles");
mkdirSync(tilesDir, { recursive: true });
const tileDest = join(tilesDir, "sig-infrastructure.pmtiles");
// Leave a REAL rendered tile in place when overlaying a `--jurisdiction okc` bundle.
if (!existsSync(tileDest)) {
  // Otherwise reuse a real rendered tile if one is on disk (run from web/ or repo root)…
  const tileCandidates = [
    join(process.cwd(), "..", "exports", "out", "okc", "web", "tiles", "sig-infrastructure.pmtiles"),
    join(process.cwd(), "exports", "out", "okc", "web", "tiles", "sig-infrastructure.pmtiles"),
  ];
  const realTile = tileCandidates.find((c) => existsSync(c));
  if (realTile) {
    copyFileSync(realTile, tileDest);
  } else {
    // …or emit a minimal PMTiles v3 header ("PMTiles" magic + version byte 3, 127 bytes).
    const header = Buffer.alloc(127);
    header.write("PMTiles", 0, "ascii");
    header.writeUInt8(3, 7);
    writeFileSync(tileDest, header);
  }
}

console.log(`fixture export bundle written to ${outDir}`);
