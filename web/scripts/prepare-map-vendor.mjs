#!/usr/bin/env node
// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * prepare-map-vendor.mjs — P36.37 (K1 §6.1, SIG-UI-097/106): emit the
 * MapLibre ESM split as self-hosted static modules under
 * `web/public/map/vendor/` (gitignored — copied from the pinned package,
 * never hand-edited). Three files, the K1 split verbatim:
 *
 *   maplibre-gl.mjs         the main-thread entry (imports ./maplibre-gl-shared.mjs)
 *   maplibre-gl-shared.mjs  the shared chunk — fetched once, HTTP-cached for the worker
 *   maplibre-gl-worker.mjs  the module worker (`setWorkerUrl` targets it)
 *
 * Fail-closed: a missing or drifted package file throws — a vendored partial
 * never ships.
 */

import { copyFileSync, existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { createHash } from "node:crypto";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const WEB = join(dirname(fileURLToPath(import.meta.url)), "..");
const SRC = join(WEB, "node_modules", "maplibre-gl", "dist");
const OUT = join(WEB, "public", "map", "vendor");
const FILES = ["maplibre-gl.mjs", "maplibre-gl-shared.mjs", "maplibre-gl-worker.mjs"];

const pkg = JSON.parse(readFileSync(join(WEB, "node_modules", "maplibre-gl", "package.json"), "utf8"));
mkdirSync(OUT, { recursive: true });
const manifest = { schema: "sig.map-vendor/1", package: "maplibre-gl", version: pkg.version, files: {} };
for (const f of FILES) {
  const src = join(SRC, f);
  if (!existsSync(src)) throw new Error(`prepare-map-vendor: ${src} missing (maplibre-gl dist drift)`);
  const bytes = readFileSync(src);
  manifest.files[f] = { bytes: bytes.length, sha256: createHash("sha256").update(bytes).digest("hex") };
  copyFileSync(src, join(OUT, f));
}
writeFileSync(join(OUT, "manifest.json"), JSON.stringify(manifest, null, 2) + "\n");
console.log(`prepare-map-vendor: maplibre-gl ${pkg.version} ESM split → public/map/vendor/ (${FILES.length} files)`);
