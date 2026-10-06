// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * The export-mode tile copy-list resolver (P31.15, ADR-R9-TILES; P34.34a).
 *
 * In `SIG_DATA_SOURCE=export` the static build copies the per-compartment
 * PMTiles archives the export rendered — exactly the manifest's
 * `web/tiles/<compartment>-sites.pmtiles` artifacts, so the map style can
 * never name an archive that was not copied and no unlisted file is served.
 *
 * Honesty contract (P34.34a): an export whose manifest lists NO tile
 * archives is a legal, honestly-empty export — it resolves to an empty copy
 * list and the map renders its explicit empty-tile state. What still fails
 * LOUD: a missing/unreadable manifest (the export dir is malformed) and a
 * manifest that lists archives absent on disk (bytes and manifest disagree).
 */

import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";

const TILE_RE = /^web\/tiles\/[^/]+-sites\.pmtiles$/;

/**
 * @param {string} exportDir the export output dir (`<dir>/manifest.json` +
 *   `<dir>/web/tiles/`).
 * @returns {{ tilesDir: string, files: string[] }} the tile archive file names
 *   to copy (basenames under `web/tiles/`, sorted), or `files: []` for an
 *   honestly tile-less export.
 * @throws when the manifest is missing/unreadable, or lists archives whose
 *   bytes are absent on disk.
 */
export function resolveTileCopyList(exportDir) {
  const tilesDir = join(exportDir, "web", "tiles");
  const manifestPath = join(exportDir, "manifest.json");
  if (!existsSync(manifestPath)) {
    throw new Error(
      `SIG_DATA_SOURCE=export but the export manifest is missing: ${manifestPath}. ` +
        "Run `sig-exports build` first.",
    );
  }
  let manifest;
  try {
    manifest = JSON.parse(readFileSync(manifestPath, "utf-8"));
  } catch (cause) {
    throw new Error(`SIG_DATA_SOURCE=export but the export manifest is unreadable: ${manifestPath}.`, {
      cause,
    });
  }
  const listed = (manifest.artifacts ?? [])
    .map((a) => String(a.path ?? ""))
    .filter((p) => TILE_RE.test(p))
    .map((p) => p.slice("web/tiles/".length));
  const files = listed.filter((f) => existsSync(join(tilesDir, f)));
  if (files.length !== listed.length) {
    throw new Error(
      `SIG_DATA_SOURCE=export: the manifest lists tile archives missing from ${tilesDir}.`,
    );
  }
  // zero listed archives is NOT an error — an export that rendered no
  // compartment tile layers is an honest empty state (P34.34a); the map page
  // says so instead of implying data on a blank canvas.
  return { tilesDir, files: files.sort() };
}
