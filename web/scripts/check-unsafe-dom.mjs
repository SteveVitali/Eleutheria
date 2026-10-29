// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * P36.19 (UXK0-3, K0 §4.8, SIG-UI-096): the unsafe-DOM-sink ban. K0 §4.8's
 * untrusted-labels rule — every label comes from third-party data, so client
 * code renders TEXT only: no `innerHTML`, no `dangerouslySetInnerHTML`, no
 * MapLibre `setHTML` — "a CI grep fails on them". This is that grep, wired
 * into `npm run check` as `check:dom`.
 *
 * Scan: every script/template file under web/src/**, comments stripped first
 * (the ban is on USE, never on a comment that documents it — the same
 * convention check-root-absolute-paths.mjs keeps). A USE is:
 *   - `X.innerHTML` / `X.outerHTML`  — a sink property access;
 *   - `X.insertAdjacentHTML(`        — a sink call;
 *   - `document.write(`              — a sink call;
 *   - `dangerouslySetInnerHTML`      — the JSX sink prop (whole token);
 *   - `X.setHTML(`                   — the MapLibre Popup sink (a method call
 *     — "maplibre setHTML" in prose is not a use).
 *
 * Exit codes: 0 pass · 1 banned sink found · 2 usage error ·
 * 3 vacuous (nothing scanned — SIG-ENG-042, never a silent green).
 *
 * Usage: node scripts/check-unsafe-dom.mjs [--src DIR] [--list]
 */

import { readdirSync, readFileSync } from "node:fs";
import { join, relative } from "node:path";
import { fileURLToPath } from "node:url";

const WEB = fileURLToPath(new URL("..", import.meta.url));
const EXTENSIONS = new Set([".astro", ".ts", ".tsx", ".js", ".jsx", ".mjs", ".mts"]);

const SINKS = [
  ["innerHTML", /\.innerHTML\b/],
  ["outerHTML", /\.outerHTML\b/],
  ["insertAdjacentHTML", /\.insertAdjacentHTML\s*\(/],
  ["document.write", /\bdocument\.write\s*\(/],
  ["dangerouslySetInnerHTML", /\bdangerouslySetInnerHTML\b/],
  ["setHTML", /\.setHTML\s*\(/],
];

function stripComments(text) {
  text = text.replace(/\/\*[\s\S]*?\*\//g, (m) => m.replace(/[^\n]/g, " "));
  text = text.replace(/<!--[\s\S]*?-->/g, (m) => m.replace(/[^\n]/g, " "));
  const stripTail = (s) => {
    const idx = s.indexOf("//");
    if (idx === -1) return s;
    if (idx === 0 || s[idx - 1] !== ":") return s.slice(0, idx);
    return s.slice(0, idx + 2) + stripTail(s.slice(idx + 2));
  };
  return text.split("\n").map(stripTail).join("\n");
}

function sourceFiles(srcDir) {
  const files = [];
  const walk = (d) => {
    for (const e of readdirSync(d, { withFileTypes: true })) {
      const p = join(d, e.name);
      if (e.isDirectory()) walk(p);
      else if (e.isFile() && EXTENSIONS.has(p.slice(p.lastIndexOf(".")))) files.push(p);
    }
  };
  walk(srcDir);
  return files.sort();
}

const args = process.argv.slice(2);
let srcDir = join(WEB, "src");
let list = false;
for (let i = 0; i < args.length; i++) {
  const a = args[i];
  if (a === "--src") srcDir = args[++i];
  else if (a === "--list") list = true;
  else if (a === "--help" || a === "-h") {
    console.log("usage: node scripts/check-unsafe-dom.mjs [--src DIR] [--list]");
    process.exit(0);
  } else {
    console.error(`check-unsafe-dom: unknown argument ${a}`);
    process.exit(2);
  }
  if (i >= args.length) {
    console.error("check-unsafe-dom: missing value");
    process.exit(2);
  }
}

const files = sourceFiles(srcDir);
if (files.length === 0) {
  console.error(`check-unsafe-dom: VACUOUS — no script/template files scanned in ${srcDir}`);
  process.exit(3);
}

const hits = [];
for (const abs of files) {
  const rel = relative(WEB, abs).split("\\").join("/");
  const text = stripComments(readFileSync(abs, "utf-8"));
  text.split("\n").forEach((line, i) => {
    for (const [name, re] of SINKS) {
      if (re.test(line)) hits.push(`${rel}:${i + 1} ${name}`);
    }
  });
}

console.log(
  `check-unsafe-dom: ${files.length} file(s) scanned, ${SINKS.length} banned sink(s), ${hits.length} hit(s)`,
);
if (list) for (const h of hits) console.log(`  ${h}`);
if (hits.length > 0) {
  console.error(
    "\n✗ unsafe DOM sink(s) found (K0 §4.8 — labels are text only, SIG-UI-096):",
  );
  for (const h of hits) console.error(`    ${h}`);
  console.error(
    "  render text via textContent/setDOMContent and classes — never markup " +
      "strings. A sink that must exist is a redesigned widget, not an exception.",
  );
  process.exit(1);
}
console.log("✓ no unsafe DOM sinks in web/src/**");
process.exit(0);
