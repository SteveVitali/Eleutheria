// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// P32.15 (SIG-FIND-005, ADR-134): measure the per-island JS/network payload of
// the BUILT site (web/dist) and write docs/build/reports/p32.15-island-budgets.md
// — the measured baseline behind web/tests/e2e/island-budgets.json +
// lighthouserc.json's per-island assertMatrix blocks.
//
// Usage:  node web/scripts/measure-island-budgets.mjs [--out <report.md>]
// Requires `npm --prefix web run build` to have produced web/dist.

import { readFileSync, statSync, writeFileSync } from "node:fs";
import { execSync } from "node:child_process";
import { gzipSync } from "node:zlib";
import { dirname, join, normalize, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const WEB = resolve(HERE, "..");
const DIST = join(WEB, "dist");
const REPO = resolve(WEB, "..");
const ISLANDS = ["/map/", "/network/", "/search/"];

function walk(entry) {
  // Follow relative imports/URL references from a script entry so worker +
  // shared chunks are counted with the island that pulls them.
  const seen = new Set();
  const stack = [entry];
  while (stack.length) {
    const p = stack.pop();
    if (seen.has(p)) continue;
    seen.add(p);
    let src = "";
    try {
      src = readFileSync(p, "utf-8");
    } catch {
      continue;
    }
    for (const m of src.matchAll(/(?:from|import\(|new URL\()\s*["'`](\.\/[^"'`]+)["'`]/g)) {
      if (!m[1].includes("${")) stack.push(normalize(join(dirname(p), m[1])));
    }
    // Vite inlines worker/asset URLs as absolute "/_astro/<file>" strings.
    for (const m of src.matchAll(/["'`](\/_astro\/[^"'`]+)["'`]/g)) {
      if (!m[1].includes("${")) stack.push(join(DIST, m[1]));
    }
  }
  return [...seen];
}

function pageAssets(page) {
  const htmlPath = join(DIST, page, "index.html");
  const html = readFileSync(htmlPath, "utf-8");
  const refs = new Set(
    [...html.matchAll(/["'`](\/_astro\/[^"'`]+)["'`]/g)]
      .map((m) => m[1])
      // Astro's hydration inline script carries the module URL inside a JS
      // template literal ("/_astro/${t}") — skip non-literal references.
      .filter((r) => !r.includes("${")),
  );
  // Transitive script deps (shared chunks, workers) the HTML names indirectly.
  const scripts = [];
  for (const r of refs) {
    if (r.endsWith(".js") || r.endsWith(".mjs")) {
      for (const p of walk(join(DIST, r))) {
        const rel = "/" + p.slice(DIST.length + 1).replace(/\\/g, "/");
        if (!refs.has(rel) && !rel.includes("${")) scripts.push(rel);
      }
    }
  }
  const all = new Set([...refs, ...scripts]);
  const assets = [...all].sort().map((rel) => {
    const p = join(DIST, rel);
    const raw = statSync(p).size;
    const gzip = gzipSync(readFileSync(p)).length;
    return { rel, raw, gzip };
  });
  return { htmlBytes: Buffer.byteLength(html), assets };
}

const rev = (() => {
  try {
    return execSync("git rev-parse --short HEAD", { cwd: REPO }).toString().trim();
  } catch {
    return "unknown";
  }
})();

const budgets = JSON.parse(
  readFileSync(join(WEB, "tests/e2e/island-budgets.json"), "utf-8"),
).islands;

const lines = [];
lines.push("<!-- SPDX-License-Identifier: Apache-2.0 -->");
lines.push(`# P32.15 — per-island JS/network budget measurements`);
lines.push("");
lines.push(
  "Measured on the built `web/dist` of the P32.15 implementation (revision `" +
    rev +
    "`, fixtures mode) by `web/scripts/measure-island-budgets.mjs`. The S4 research target is **≤1 MiB compressed** initial island assets and ≤2 MiB initial visible tiles (a measured baseline, then a hard ceiling). Enforced ceilings live in `web/tests/e2e/island-budgets.json` (wire-measured by `tests/e2e/budget.spec.ts`) and mirrored in `web/lighthouserc.json` assertMatrix blocks. The zero-JS public pages keep their 0-script / ≤150 KiB contract — nothing here relaxes it.",
);
lines.push("");
let allOk = true;
for (const page of ISLANDS) {
  const { htmlBytes, assets } = pageAssets(page);
  const b = budgets[page];
  const scriptAssets = assets.filter((a) => a.rel.endsWith(".js") || a.rel.endsWith(".mjs"));
  const scriptRaw = scriptAssets.reduce((n, a) => n + a.raw, 0);
  const scriptGz = scriptAssets.reduce((n, a) => n + a.gzip, 0);
  const totalRaw = assets.reduce((n, a) => n + a.raw, 0) + htmlBytes;
  const totalGz = assets.reduce((n, a) => n + a.gzip, 0) + htmlBytes;
  const checks = [
    ["script raw", scriptRaw, b.scriptRawMaxBytes],
    ["script gzip", scriptGz, b.scriptGzipMaxBytes],
    ["total raw", totalRaw, b.totalRawMaxBytes],
    ["total gzip", totalGz, b.totalGzipMaxBytes],
    ["document", htmlBytes, b.documentMaxBytes],
  ];
  lines.push(`## \`${page}\``);
  lines.push("");
  lines.push("| measure | bytes | ceiling | result |");
  lines.push("|---|---:|---:|---|");
  for (const [name, val, max] of checks) {
    const ok = val <= max;
    allOk &&= ok;
    lines.push(`| ${name} | ${val.toLocaleString("en-US")} | ${max.toLocaleString("en-US")} | ${ok ? "inside" : "**OVER**"} |`);
  }
  lines.push("");
  lines.push("Assets fetched by the page (module entries + transitive script deps incl. workers + stylesheets):");
  lines.push("");
  for (const a of assets) {
    lines.push(`- \`${a.rel}\` — ${a.raw.toLocaleString("en-US")} B raw / ${a.gzip.toLocaleString("en-US")} B gz`);
  }
  lines.push(`- document — ${htmlBytes.toLocaleString("en-US")} B`);
  lines.push("");
}
lines.push(
  "Zero-JS public pages remain asserted at script size 0 / ≤150 KiB by `lighthouserc.json`'s first block and `tests/e2e/islands.spec.ts`; the map tile archives are fetched per-compartment by the island only (P31.15 no-basemap contract holds — `tests/e2e/islands.spec.ts` asserts the style's `pmtiles://` sources and no third-party hosts).",
);
lines.push("");

const out = process.argv.includes("--out")
  ? process.argv[process.argv.indexOf("--out") + 1]
  : join(REPO, "docs/build/reports/p32.15-island-budgets.md");
writeFileSync(out, lines.join("\n") + "\n");
console.log(`wrote ${out}${allOk ? "" : " — OVER-BUDGET ASSETS PRESENT"}`);
process.exitCode = allOk ? 0 : 1;
