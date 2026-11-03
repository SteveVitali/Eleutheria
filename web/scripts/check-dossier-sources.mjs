// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * P36.52 (DSRC-02, K5 §5 / SIG-DSRC-004) — the "Site-wide" label + explorer
 * build check, wired into `npm run check` as `check:dsrc`, after `build`.
 *
 *   1. THE SCOPE CHECK — every emitted dossier page's "How we know this"
 *      module is either dossier-scoped (its figure `data-pointer`s resolve
 *      under the page's own artifact / `/surfaces/dossiers/<slug>`) or the
 *      honest site-wide fallback whose visible scope line says "Site-wide".
 *      A dossier page resolving HWKT figures under `/surfaces/site` WITHOUT
 *      the visible Site-wide label fails (K5 §5: a site-wide block MUST be
 *      labelled, never read as the dossier's own).
 *
 *   2. THE TWIN CHECK — every `dossier/<p>/sources/index.html` carries its
 *      `index.json` twin and its parent dossier page links the explorer
 *      (SIG-DSRC-009, R-6 never-a-404), and the twin parses as
 *      `sig.dossier-sources/1`.
 *
 * Usage: node scripts/check-dossier-sources.mjs [--dist DIR]
 * Exit: 0 pass · 1 failure · 3 vacuous (no dossier pages measured).
 */

import { existsSync, readdirSync, readFileSync } from "node:fs";
import { join, relative } from "node:path";
import { fileURLToPath } from "node:url";

const WEB = fileURLToPath(new URL("..", import.meta.url));

/** Non-dossier first segments under dist/dossier (index/nav/report routes). */
const RESERVED = new Set(["a-z", "by", "sort", "unplaced", "unresolved"]);

function* walk(dir) {
  if (!existsSync(dir)) return;
  for (const e of readdirSync(dir, { withFileTypes: true })) {
    const p = join(dir, e.name);
    if (e.isDirectory()) yield* walk(p);
    else if (e.isFile() && e.name === "index.html") yield p;
  }
}

function check(distDir) {
  const failures = [];
  let dossierPages = 0;
  let explorerPages = 0;
  const dossierRoot = join(distDir, "dossier");

  for (const file of walk(dossierRoot)) {
    const rel = relative(distDir, file).split("\\").join("/");
    const segs = rel.split("/").slice(1, -1); // drop "dossier" + "index.html"
    if (segs.length === 0) continue; // the dossier index itself
    if (RESERVED.has(segs[0])) continue;
    const leaf = segs[segs.length - 1];
    if (leaf === "print" || leaf === "sites") continue;
    const isExplorer = leaf === "sources" || leaf === "page" || leaf === "sort" || leaf === "key" || /^\d+$/.test(leaf);
    if (isExplorer) {
      explorerPages += 1;
      continue;
    }
    // A dossier page: dist/dossier/<slug-path>/index.html
    dossierPages += 1;
    const html = readFileSync(file, "utf-8");
    const hwkt = html.includes('data-testid="how-we-know-this"');
    if (!hwkt) {
      failures.push(`${rel}: no "How we know this" module (SIG-UI-044)`);
      continue;
    }
    const siteScope =
      /data-pointer="\/surfaces\/site\//.test(html);
    const labelled = /Site-wide/.test(html);
    if (siteScope && !labelled) {
      failures.push(
        `${rel}: HWKT resolves under /surfaces/site without a visible "Site-wide" label (SIG-DSRC-004)`,
      );
    }
    // If this dossier emitted an explorer, the page must link it (R-6).
    const explorerIndex = join(dossierRoot, ...segs, "sources", "index.html");
    if (existsSync(explorerIndex)) {
      const slugPath = segs.join("/");
      if (!html.includes(`dossier/${slugPath}/sources/`)) {
        failures.push(`${rel}: explorer exists but the dossier page never links it`);
      }
    }
  }

  // The twin check — every explorer page carries its JSON twin.
  for (const file of walk(dossierRoot)) {
    const rel = relative(distDir, file).split("\\").join("/");
    if (!rel.endsWith("/sources/index.html")) continue;
    // The dossier index's own `sort/sources/` route is not an explorer.
    const parentSegs = rel.split("/").slice(1, -2);
    if (parentSegs.some((s) => RESERVED.has(s))) continue;
    const dir = file.slice(0, -"index.html".length);
    const twin = join(dir, "index.json");
    if (!existsSync(twin)) {
      failures.push(`${rel}: no index.json twin (SIG-DSRC-009)`);
      continue;
    }
    try {
      const doc = JSON.parse(readFileSync(twin, "utf-8"));
      if (doc.schema !== "sig.dossier-sources/1") {
        failures.push(`${rel}: twin schema ${doc.schema} — expected sig.dossier-sources/1`);
      }
    } catch (e) {
      failures.push(`${rel}: twin is not valid JSON — ${e.message}`);
    }
  }

  if (dossierPages === 0 && explorerPages === 0) {
    console.error("check-dossier-sources: VACUOUS — no dossier pages under " + distDir);
    return 3;
  }
  for (const f of failures) console.error(`check-dossier-sources: ${f}`);
  console.log(
    `check-dossier-sources: ${dossierPages} dossier pages, ${explorerPages} explorer routes — ${failures.length === 0 ? "PASS" : "FAIL"}`,
  );
  return failures.length === 0 ? 0 : 1;
}

const distIdx = process.argv.indexOf("--dist");
const dist = distIdx >= 0 ? process.argv[distIdx + 1] : join(WEB, "dist");
process.exit(check(dist));
