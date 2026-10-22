// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// P35.51 (SIG-UI-041, SIG-FIND-005, ADR-155): measure the per-page-type budgets
// over the BUILT site (web/dist) — the static file-bytes counterpart of
// budget.spec.ts's wire measurement, and the export-mode leg's budget step
// (it succeeds the retired measure-island-budgets.mjs — per-page-type rows
// from page-budgets.json over EVERY discovered route, never per-island
// ceilings over a hand list).
//
// Semantics come from tests/e2e/page-budget-check.ts itself (imported — Node's
// type stripping makes the .ts module load directly), so the static measure
// and the wire measure can never drift: gzip AND brotli script-family and
// full-transfer totals, document raw, measured_gaps honoured exactly (the
// ratified ceiling reports loud, the regression bound is the hard gate, a
// stale gap row fails). Post-action bytes/latency are interaction-bound and
// stay with the Playwright suite — this script measures the initial load.
//
// Usage:  node web/scripts/measure-page-budgets.mjs [--out <report.md>]
// Requires `npm --prefix web run build` (or the leg's SIG_DATA_SOURCE build)
// to have produced web/dist + dist/page-types.json. SIG_DATA_SOURCE scopes
// the measured_gaps rows the same way the wire suite's does.

import { readFileSync, writeFileSync, existsSync } from "node:fs";
import { execSync } from "node:child_process";
import { brotliCompressSync, gzipSync } from "node:zlib";
import { dirname, join, normalize, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const WEB = resolve(HERE, "..");
const DIST = join(WEB, "dist");
const {
  budgetForRoute,
  evaluateInitial,
  measurementSource,
} = await import("../tests/e2e/page-budget-check.ts");

const KIND_BY_EXT = new Map([
  [".js", "script"],
  [".mjs", "script"],
  [".css", "style"],
  [".woff", "font"],
  [".woff2", "font"],
  [".ttf", "font"],
  [".otf", "font"],
  [".png", "image"],
  [".jpg", "image"],
  [".jpeg", "image"],
  [".svg", "image"],
  [".webp", "image"],
  [".avif", "image"],
  [".ico", "image"],
]);

function kindOf(rel) {
  const dot = rel.lastIndexOf(".");
  return KIND_BY_EXT.get(dot < 0 ? "" : rel.slice(dot)) ?? "other";
}

function walk(entry) {
  // Follow relative imports/URL references from a script entry so worker +
  // shared chunks are counted with the page that pulls them.
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

/** The initial-load PhaseMeasure a route's document implies: every `/_astro/`
 * reference plus the script family's transitive deps, raw + gzip + brotli. */
function pageMeasure(file) {
  const htmlPath = join(DIST, file);
  const html = readFileSync(htmlPath, "utf-8");
  const refs = new Set(
    [...html.matchAll(/["'`](\/_astro\/[^"'`]+)["'`]/g)]
      .map((m) => m[1])
      .filter((r) => !r.includes("${")),
  );
  const scripts = [];
  for (const r of refs) {
    if (r.endsWith(".js") || r.endsWith(".mjs")) {
      for (const p of walk(join(DIST, r))) {
        const rel = "/" + p.slice(DIST.length + 1).replace(/\\/g, "/");
        if (!refs.has(rel) && !rel.includes("${")) scripts.push(rel);
      }
    }
  }
  const resources = [...new Set([...refs, ...scripts])]
    .sort()
    .map((rel) => {
      const body = readFileSync(join(DIST, rel));
      return {
        url: rel,
        kind: kindOf(rel),
        raw: body.length,
        gzip: gzipSync(body).length,
        brotli: brotliCompressSync(body).length,
      };
    });
  return { documentRaw: Buffer.byteLength(html), resources };
}

const manifestPath = join(DIST, "page-types.json");
if (!existsSync(manifestPath)) {
  console.error(
    `${manifestPath} is missing — run \`npm --prefix web run build\` first ` +
      "(the route manifest is emitted at astro:build:done).",
  );
  process.exit(2);
}
const routes = JSON.parse(readFileSync(manifestPath, "utf-8")).routes;
const budgets = JSON.parse(
  readFileSync(join(WEB, "tests/e2e/page-budgets.json"), "utf-8"),
);

const rev = (() => {
  try {
    return execSync("git rev-parse --short HEAD", { cwd: WEB }).toString().trim();
  } catch {
    return "unknown";
  }
})();

const lines = [];
lines.push("<!-- SPDX-License-Identifier: Apache-2.0 -->");
lines.push(`# P35.51 — per-page-type budget measurements (initial load)`);
lines.push("");
lines.push(
  `Measured on the built \`web/dist\` (revision \`${rev}\`, SIG_DATA_SOURCE=${measurementSource()}) ` +
    "by `web/scripts/measure-page-budgets.mjs` over every route the page-type registry " +
    "discovered (`dist/page-types.json`), against `web/tests/e2e/page-budgets.json` " +
    "(sig.page-budgets/1 — the K0 §4.3 ratified table). Evaluated by the same " +
    "`page-budget-check.ts` the wire suite uses: script-family and full-transfer " +
    "totals under gzip AND brotli, document raw; a recorded measured_gaps row " +
    "reports its ratified ceiling while its regression bound is the hard gate. " +
    "Post-action bytes + interaction latency are measured on the wire by " +
    "`tests/e2e/budget.spec.ts` (one scripted interaction per surface).",
);
lines.push("");
lines.push("| route | type | doc raw B | script gz B | script br B | total gz B | total br B | verdict |");
lines.push("|---|---|---:|---:|---:|---:|---:|---|");

let allOk = true;
const reports = [];
for (const route of routes) {
  const { row } = budgetForRoute(budgets, route);
  const m = pageMeasure(route.file);
  const scriptGz = m.resources.filter((r) => r.kind === "script").reduce((n, r) => n + r.gzip, 0);
  const scriptBr = m.resources.filter((r) => r.kind === "script").reduce((n, r) => n + r.brotli, 0);
  const totalGz =
    m.resources.filter((r) => r.kind !== "data").reduce((n, r) => n + r.gzip, 0) + m.documentRaw;
  const totalBr =
    m.resources.filter((r) => r.kind !== "data").reduce((n, r) => n + r.brotli, 0) + m.documentRaw;
  const { violations, gaps } = evaluateInitial(budgets, route.path, row, m);
  reports.push({ route, violations, gaps });
  const verdict = violations.length
    ? "**OVER**"
    : gaps.length
      ? "recorded gap"
      : "inside";
  allOk &&= !violations.length;
  lines.push(
    `| \`${route.path}\` | ${route.type} | ${m.documentRaw.toLocaleString("en-US")} | ` +
      `${scriptGz.toLocaleString("en-US")} | ${scriptBr.toLocaleString("en-US")} | ` +
      `${totalGz.toLocaleString("en-US")} | ${totalBr.toLocaleString("en-US")} | ${verdict} |`,
  );
}
lines.push("");

const anyGaps = reports.flatMap((r) => r.gaps);
if (anyGaps.length) {
  lines.push("## Recorded measured gaps (ratified ceiling stands; bound is the gate)");
  lines.push("");
  for (const g of anyGaps) {
    lines.push(
      `- \`${g.route}\` ${g.metric}: measured ${g.measured.toLocaleString("en-US")} B — ` +
        `ratified ${g.ratified.toLocaleString("en-US")} B, regression bound ` +
        `${g.bound.toLocaleString("en-US")} B (${g.deferral})`,
    );
  }
  lines.push("");
}
const anyViolations = reports.flatMap((r) => r.violations);
if (anyViolations.length) {
  lines.push("## Violations");
  lines.push("");
  for (const v of anyViolations) lines.push(`- ${v.message}`);
  lines.push("");
}

const out = process.argv.includes("--out")
  ? process.argv[process.argv.indexOf("--out") + 1]
  : null;
const text = lines.join("\n") + "\n";
if (out) {
  writeFileSync(out, text);
  console.log(`wrote ${out}${allOk ? "" : " — OVER-BUDGET ASSETS PRESENT"}`);
} else {
  process.stdout.write(text);
}
process.exitCode = allOk ? 0 : 1;
