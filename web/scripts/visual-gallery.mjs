// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
//
// P37.60 (SIG-UI-152, DR-K14-18; K14 §7 "the operator signs off the gallery as
// beautiful") — the operator gallery generator.
//
// Walks the visual grid's committed baselines (tests/visual/
// visual.spec.ts-snapshots/) plus the last run's actual/diff captures under
// web/test-results/ and emits a self-contained review gallery — one row per
// template group × {light, dark} × {1440, 390, 320} cell, baseline alongside
// the latest actual and diff — under docs/build/logs/visual-gallery/.
//
//   node scripts/visual-gallery.mjs [--out <dir>]
//
// The output is OPERATOR-ONLY review material: docs/build/logs/ is the one
// gitignored build-memory subtree, nothing here is referenced by web/dist or
// any published surface, and the generator copies — never symlinks — so the
// directory can be handed to the operator whole. The script does NOT approve
// anything: K14 §7 makes "beautiful" a human sign-off. It prints the
// checklist the operator judges; no sign-off is simulated.

import { copyFileSync, existsSync, mkdirSync, readdirSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const WEB = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const REPO = resolve(WEB, "..");
const SNAPSHOTS = join(WEB, "tests/visual/visual.spec.ts-snapshots");
const RESULTS = join(WEB, "test-results");
const DEFAULT_OUT = join(REPO, "docs/build/logs/visual-gallery");

const args = process.argv.slice(2);
const outIdx = args.indexOf("--out");
const OUT = outIdx >= 0 ? resolve(args[outIdx + 1]) : DEFAULT_OUT;
if (args.includes("--help") || args.includes("-h")) {
  console.log("usage: node scripts/visual-gallery.mjs [--out <dir>]");
  process.exit(0);
}
if (OUT.startsWith(join(WEB, "dist")) || OUT.startsWith(join(WEB, "public"))) {
  console.error(`refusing to write the operator gallery into a published surface: ${OUT}`);
  process.exit(2);
}

// dist/page-types.json maps group → representative path when the build ran.
const manifestPath = join(WEB, "dist/page-types.json");
const routes = existsSync(manifestPath)
  ? JSON.parse(readFileSync(manifestPath, "utf8")).routes
  : [];

// Group cells by <group>--<cell>.png over the committed baselines.
const baselines = existsSync(SNAPSHOTS)
  ? readdirSync(SNAPSHOTS).filter((f) => f.endsWith(".png")).sort()
  : [];

const cells = new Map(); // group -> Map<cell, {baseline, actual?, diff?}>
for (const f of baselines) {
  const m = f.match(/^(.+)--(light|dark)-(1440|390|320)\.png$/);
  if (!m) continue;
  const [, group, theme, vp] = m;
  const cell = `${theme}-${vp}`;
  if (!cells.has(group)) cells.set(group, new Map());
  cells.get(group).set(cell, { baseline: f });
}

// Fold in the latest run's captures: Playwright writes
// test-results/<slug>/<name>-actual.png / -diff.png / -expected.png.
if (existsSync(RESULTS)) {
  for (const dir of readdirSync(RESULTS)) {
    const d = join(RESULTS, dir);
    for (const f of readdirSync(d)) {
      const m = f.match(/^(.+)--(light|dark)-(1440|390|320)-(actual|diff)\.png$/);
      if (!m) continue;
      const [, group, theme, vp, kind] = m;
      const cell = `${theme}-${vp}`;
      if (!cells.has(group)) cells.set(group, new Map());
      const entry = cells.get(group).get(cell) ?? {};
      entry[kind] = join("test-results", dir, f);
      cells.get(group).set(cell, entry);
    }
  }
}

if (cells.size === 0) {
  console.log("no visual baselines or run captures found — run `npm run test:visual` (or :update) first");
  process.exit(0);
}

rmSync(OUT, { recursive: true, force: true });
mkdirSync(join(OUT, "img"), { recursive: true });

// Copy every referenced image into img/ under a flat, collision-free name.
const copied = new Map();
const copy = (src) => {
  const abs = src.startsWith("test-results") ? join(WEB, src) : join(SNAPSHOTS, src);
  if (!existsSync(abs)) return null;
  const flat = src.replace(/[\/]/g, "__");
  if (!copied.has(flat)) {
    copyFileSync(abs, join(OUT, "img", flat));
    copied.set(flat, true);
  }
  return `img/${flat}`;
};

const CELLS = ["light-1440", "light-390", "light-320", "dark-1440", "dark-390", "dark-320"];
const stamp = new Date().toISOString();

const rows = [];
for (const [group, cellMap] of [...cells.entries()].sort()) {
  const shots = CELLS.filter((c) => cellMap.has(c)).map((cell) => {
    const e = cellMap.get(cell);
    const b = e.baseline ? copy(e.baseline) : null;
    const a = e.actual ? copy(e.actual) : null;
    const d = e.diff ? copy(e.diff) : null;
    const status = d ? "diff" : a ? "changed" : "baseline";
    return `<div class="cell ${status}">
      <h4>${cell}${status === "diff" ? " — DIFF" : ""}</h4>
      <div class="pair">
        ${b ? `<figure><figcaption>baseline</figcaption><img src="${b}" loading="lazy" alt="${group} ${cell} baseline"></figure>` : ""}
        ${a ? `<figure><figcaption>actual</figcaption><img src="${a}" loading="lazy" alt="${group} ${cell} actual"></figure>` : ""}
        ${d ? `<figure><figcaption>diff</figcaption><img src="${d}" loading="lazy" alt="${group} ${cell} diff"></figure>` : ""}
      </div>
    </div>`;
  });
  rows.push(`<section class="group">
    <h3><code>${group}</code></h3>
    ${shots.join("\n")}
  </section>`);
}

const nCells = [...cells.values()].reduce((n, m) => n + m.size, 0);
const nDiffs = [...cells.values()].reduce(
  (n, m) => n + [...m.values()].filter((e) => e.diff).length,
  0,
);

const html = `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light dark">
<title>SIG visual gallery — operator review (not for publication)</title>
<style>
:root { font-family: system-ui, sans-serif; }
body { margin: 2rem; }
.banner { border: 2px solid #b00; background: #ffe9e9; color: #400; padding: 1rem; margin-bottom: 2rem; }
.cell { border-top: 1px solid #9993; padding: .5rem 0; }
.cell.diff h4 { color: #b00; }
.pair { display: flex; gap: 1rem; flex-wrap: wrap; }
figure { margin: 0; max-width: 46rem; }
figcaption { font-size: .8rem; color: #666; }
img { max-width: 100%; border: 1px solid #9996; image-rendering: pixelated; }
h4 { font-family: ui-monospace, monospace; }
</style>
</head>
<body>
<div class="banner">
<strong>OPERATOR REVIEW MATERIAL — never published.</strong>
Generated ${stamp} by web/scripts/visual-gallery.mjs under docs/build/logs/
(the gitignored build-memory subtree). ${cells.size} template group(s) × up to 6 cells
(${nCells} shots); ${nDiffs} cell(s) carry a diff from the last run.
Sign-off on "beautiful" is the operator's call (K14 §7) — this gallery only
prepares the evidence; nothing here approves or simulates approval.
</div>
<h1>SIG visual-regression gallery — P37.60 / SIG-UI-152</h1>
<p>Each row is a template group; each cell is baseline / actual / diff at
&lt;theme&gt;-&lt;viewport&gt;. Canvases are masked in the harness
(GPU rasterisation is not cross-runner deterministic).</p>
<h2>Operator checklist</h2>
<ol>
<li>Every group row present — a missing row means the build emitted no route (the grid fails loud, but check the report).</li>
<li>All six cells per row: light/dark × 1440/390/320.</li>
<li>Diffs reviewed and approved — an approved change requires its ticket cited in tests/visual/baselines.json.</li>
<li>Dark cells read as the dark token set; light cells as light.</li>
</ol>
${rows.join("\n")}
</body>
</html>`;

writeFileSync(join(OUT, "index.html"), html);
console.log(`operator gallery: ${OUT}/index.html`);
console.log(`${cells.size} group(s), ${nCells} cell(s), ${nDiffs} diff(s) — prepared_not_executed: operator sign-off outstanding (K14 §7)`);
