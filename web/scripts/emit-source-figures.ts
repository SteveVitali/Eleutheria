// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * P36.47 (R11-K13-UX10-3a, K10 §8; FIG-01b's `strip` kind): emit the fixture
 * sources' runs-over-time strip spec docs and render them through the SAME
 * figure-kit seam a release export takes (K13 C-07 — the page owner
 * composes `sig.figure-kit-chart/1`; the kit owns layouts, byte-deterministic
 * and CSP-safe).
 *
 *   npm run fixture:source-figures
 *
 * = esbuild bundle this file → node writes the strip spec under
 *   `web/src/fixtures/source-figures/<id>/` → `uv run sig-exports figure
 *   chart` renders the committed SVG bytes + meta the fixtures-mode build
 *   inlines on `/sources/<id>/`.
 */

import { existsSync, mkdirSync, writeFileSync } from "node:fs";
import { execFileSync } from "node:child_process";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

import {
  fixtureReleaseInfo,
  getSourcePage,
  getSourcePageIds,
  runsStripSpec,
} from "../src/lib/source-page";

function repoRoot(): string {
  let dir = fileURLToPath(new URL(".", import.meta.url));
  for (;;) {
    if (existsSync(join(dir, "uv.lock"))) return dir;
    const parent = join(dir, "..");
    if (parent === dir) throw new Error("repoRoot: walked above the bundle without finding uv.lock");
    dir = parent;
  }
}
const REPO_ROOT = repoRoot();
const OUT_BASE = join(REPO_ROOT, "web/src/fixtures/source-figures");

let emitted = 0;
for (const id of getSourcePageIds()) {
  const model = getSourcePage(id);
  if (!model || model.registryOnly) continue;
  const spec = runsStripSpec(model, fixtureReleaseInfo());
  if (!spec) continue;
  const dir = join(OUT_BASE, id);
  mkdirSync(dir, { recursive: true });
  const specPath = join(dir, "runs.spec.json");
  const svgPath = join(dir, "runs.svg");
  const metaPath = join(dir, "runs.meta.json");
  writeFileSync(specPath, JSON.stringify(spec, null, 2) + "\n");
  execFileSync(
    "uv",
    [
      "run", "sig-exports", "figure", "chart",
      "--in", specPath,
      "--out", svgPath,
      "--meta", metaPath,
    ],
    { cwd: REPO_ROOT, stdio: "inherit" },
  );
  emitted += 1;
}
console.log(`emit-source-figures: ${emitted} strip figure(s) rendered through the kit`);
