#!/usr/bin/env node
// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * check-runtime-deps.mjs — P36.37 (SIG-UI-097, K0 §4.7): the runtime
 * dependency allow-list gate.
 *
 *   1. `runtime-deps.json` parses and names the expected allow-list.
 *   2. Every bare module specifier inside the /map/ island graph
 *      (`src/islands/MapIsland.tsx` + `src/islands/map/**`) resolves to a
 *      `browser` allow-list entry or a relative import — nothing else.
 *   3. The /map/ bundle contains NO React: after the migration, no emitted
 *      JS asset the map page references may carry the react runtime, and the
 *      vendored dir holds exactly the pinned ESM-split files.
 *
 * Usage: node scripts/check-runtime-deps.mjs [--dist DIR]
 * Runs after `astro build` inside `npm run check`.
 */

import { existsSync, readFileSync, readdirSync, statSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const WEB = join(dirname(fileURLToPath(import.meta.url)), "..");
const distIdx = process.argv.indexOf("--dist");
const DIST = distIdx > 0 ? process.argv[distIdx + 1] : join(WEB, "dist");

const fail = (msg) => {
  console.error(`check-runtime-deps: ${msg}`);
  process.exit(1);
};

const deps = JSON.parse(readFileSync(join(WEB, "runtime-deps.json"), "utf8"));
if (deps.schema !== "sig.runtime-deps/1") fail("runtime-deps.json schema drift");
const allowed = new Set(Object.keys(deps.browser ?? {}));

// 1 — the island graph's bare specifiers
const roots = [join(WEB, "src", "islands", "MapIsland.tsx"), join(WEB, "src", "islands", "map")];
const files = [];
const stack = [...roots];
while (stack.length) {
  const cur = stack.pop();
  if (!existsSync(cur)) continue;
  const s = statSync(cur);
  if (s.isDirectory()) {
    for (const e of readdirSync(cur)) stack.push(join(cur, e));
  } else if (/\.(tsx?|jsx?)$/.test(cur)) {
    files.push(cur);
  }
}
const IMPORT_RE = /(?:import|export)[^'"]*?from\s+["']([^"']+)["']/g;
const specifiers = new Set();
for (const f of files) {
  const src = readFileSync(f, "utf8");
  for (const m of src.matchAll(IMPORT_RE)) {
    // `import type`/`export type` are erased — never browser bytes.
    if (/^(?:import|export)\s+type\b/.test(m[0])) continue;
    const spec = m[1];
    if (spec && !spec.startsWith(".") && !spec.startsWith("/")) {
      specifiers.add(
        spec.startsWith("@") ? spec.split("/").slice(0, 2).join("/") : spec.split("/")[0],
      );
    }
  }
}
for (const spec of specifiers) {
  if (!allowed.has(spec)) {
    fail(
      `${spec} is imported by the /map/ island graph but is not a browser runtime dep (runtime-deps.json)`,
    );
  }
}

// 2 — no React in the /map/ bundle: the emitted page's module graph
const htmlPath = join(DIST, "map", "index.html");
if (!existsSync(htmlPath)) fail(`${htmlPath} missing — run astro build first`);
const html = readFileSync(htmlPath, "utf8");
const refs = [...html.matchAll(/(?:src|href)="([^"]+\.m?js)"/g)].map((m) => m[1]);
for (const ref of refs) {
  if (/react/i.test(ref)) fail(`/map/ references a react runtime asset: ${ref}`);
}
const astroDir = join(DIST, "_astro");
const mapChunks = readdirSync(astroDir).filter((f) => f.endsWith(".js") && /MapIsland/i.test(f));
for (const f of mapChunks) {
  const body = readFileSync(join(astroDir, f), "utf8");
  if (/react-dom|createPortal|preact\/compat/.test(body)) {
    fail(`${f} carries a react/compat signature — the /map/ bundle must not include React (SIG-UI-097)`);
  }
}
// P36.40 (SIG-UI-097): the same no-React gate for /search/ — the runtime
// migration is THIS row, so the emitted page and its island chunk graph are
// asserted react-free, never assumed.
const searchHtmlPath = join(DIST, "search", "index.html");
if (existsSync(searchHtmlPath)) {
  const shtml = readFileSync(searchHtmlPath, "utf8");
  for (const ref of [...shtml.matchAll(/(?:src|url)="([^"]+\.m?js)"/g)].map((m) => m[1])) {
    // Boundary before 'r' — pReact.module.*.js is the shared Preact runtime.
    if (/(^|[^a-z])react/i.test(ref)) fail(`/search/ references a react runtime asset: ${ref}`);
  }
  const searchChunks = readdirSync(astroDir).filter(
    (f) => f.endsWith(".js") && /SearchIsland/i.test(f),
  );
  for (const f of searchChunks) {
    const body = readFileSync(join(astroDir, f), "utf8");
    if (/react-dom|createPortal|preact\/compat/.test(body)) {
      fail(`${f} carries a react/compat signature — the /search/ bundle must not include React (SIG-UI-097)`);
    }
  }
}
// The vendored split: exactly the pinned files.
const vendorDir = join(DIST, "map", "vendor");
if (!existsSync(vendorDir)) fail("dist/map/vendor/ missing — prepare-map-vendor.mjs did not run");
const vendored = readdirSync(vendorDir).sort();
const expected = ["manifest.json", "maplibre-gl-shared.mjs", "maplibre-gl-worker.mjs", "maplibre-gl.mjs"];
if (JSON.stringify(vendored) !== JSON.stringify(expected)) {
  fail(`dist/map/vendor holds ${vendored.join(",")} — expected exactly ${expected.join(",")}`);
}
console.log(
  `check-runtime-deps: ok (${files.length} island files, ${specifiers.size} bare specifiers, vendor pinned)`,
);
