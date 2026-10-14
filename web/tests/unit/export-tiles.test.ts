// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// P34.34a (F5 PKG-03a): the export-mode tile copy step + the honest
// empty-tile map state. A manifest that lists NO tile archives resolves to an
// empty copy list — never a build failure — and the map page states the
// absence; a manifest that lists archives absent on disk still fails LOUD.
import { describe, expect, it } from "vitest";
import { mkdtempSync, mkdirSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { fileURLToPath } from "node:url";
import { join } from "node:path";
import { resolveTileCopyList } from "../../scripts/export-tiles.mjs";
import { EMPTY_TILE_STATE_NOTE, buildPublicMapStyle } from "../../src/lib/map-tiles";

const MAP_ASTRO = fileURLToPath(new URL("../../src/pages/map.astro", import.meta.url));

function exportDir(manifestArtifacts: Array<{ path: string }> | null, tiles: string[] = []) {
  const dir = mkdtempSync(join(tmpdir(), "sig-export-tiles-"));
  if (manifestArtifacts !== null) {
    writeFileSync(join(dir, "manifest.json"), JSON.stringify({ artifacts: manifestArtifacts }));
  }
  if (tiles.length) {
    mkdirSync(join(dir, "web", "tiles"), { recursive: true });
    for (const t of tiles) writeFileSync(join(dir, "web", "tiles", t), "PM");
  }
  return dir;
}

describe("resolveTileCopyList (P34.34a — honest empty-tile export)", () => {
  it("a manifest listing zero tile archives resolves to an empty copy list — never throws", () => {
    const dir = exportDir([{ path: "web/map.json" }, { path: "sig_graph/sites.jsonl" }]);
    expect(resolveTileCopyList(dir).files).toEqual([]);
    rmSync(dir, { recursive: true, force: true });
  });

  it("a manifest listing zero artifacts at all resolves empty", () => {
    const dir = exportDir([]);
    expect(resolveTileCopyList(dir).files).toEqual([]);
    rmSync(dir, { recursive: true, force: true });
  });

  it("a manifest-listed archive absent on disk fails LOUD (bytes ≠ manifest)", () => {
    const dir = exportDir([{ path: "web/tiles/osm_physical-sites.pmtiles" }]);
    expect(() => resolveTileCopyList(dir)).toThrow(/missing/);
    rmSync(dir, { recursive: true, force: true });
  });

  it("a missing manifest fails LOUD (the export dir is malformed)", () => {
    const dir = exportDir(null);
    expect(() => resolveTileCopyList(dir)).toThrow(/manifest is missing/);
    rmSync(dir, { recursive: true, force: true });
  });

  it("only manifest-listed archives are copied — an unlisted file is never served", () => {
    const dir = exportDir(
      [{ path: "web/tiles/sig_graph-sites.pmtiles" }],
      ["sig_graph-sites.pmtiles", "stray-sites.pmtiles"],
    );
    expect(resolveTileCopyList(dir).files).toEqual(["sig_graph-sites.pmtiles"]);
    rmSync(dir, { recursive: true, force: true });
  });
});

describe("the honest empty-tile map state (P34.34a)", () => {
  it("an empty source list is the committed background-only style (no fabricated layers)", () => {
    const style = buildPublicMapStyle([]);
    expect(Object.keys(style.sources)).toEqual([]);
    expect(style.layers).toEqual([{ id: "sig-background", type: "background" }]);
  });

  it("the empty-tile note states the absence rather than implying coverage", () => {
    expect(EMPTY_TILE_STATE_NOTE).toMatch(/no tile archives/i);
    expect(EMPTY_TILE_STATE_NOTE).not.toMatch(/no (records|infrastructure) exist/i);
  });

  it("map.astro renders the note only in export mode with zero tile sources", () => {
    const src = readFileSync(MAP_ASTRO, "utf-8");
    expect(src).toContain("EMPTY_TILE_STATE_NOTE");
    expect(src).toContain('data-testid="empty-tile-state"');
    // export-mode gated: the fixtures build labels demo data instead
    expect(src).toMatch(/dataSource\(\) === "export" && TILE_SOURCES\.length === 0/);
  });
});
