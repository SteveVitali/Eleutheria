// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * P35.65 — the root-absolute path containment check (SIG-REL-008 `Also:`;
 * G3 NEW-6/GT-11; K13 R-8/UXR-25).
 *
 * A snapshot release under `/s/<pub>/` stays self-contained only if every
 * same-origin path goes through `withBase()` (`web/src/lib/paths.ts`). G3's
 * NEW-6 measured the pre-refactor debt: 85 root-absolute path sites in 36
 * files and 0 `BASE_URL` uses (2026-09-30T18:47:42Z; the sweep of those
 * grandfathered sites is P36.66a's row). This check contains GROWTH: it
 * counts root-absolute path sites in `web/src/**` and fails when any file's
 * count exceeds the recorded baseline — new templates may not add sites; the
 * baseline may only be lowered (by the sweep), never raised, without a
 * contract amendment.
 *
 * Counting rule (deterministic; the same rule measures and enforces):
 *   - every `web/src/**` file with a script/template extension
 *     (.astro .ts .tsx .js .jsx .mjs .mts .css) is scanned line by line;
 *   - comments are stripped first: `/* … *\/` and `<!-- … -->` blocks, and
 *     `//` … end-of-line when the `//` is not immediately preceded by `:`
 *     (so `https://`, `gs://`, `file://` URL schemes survive — a stripped
 *     line can lose a comment's path, never fabricate one);
 *   - a SITE is an occurrence of a quote (`"` `'` `` ` ``) immediately
 *     followed by `/` and zero or more URL-path characters
 *     ([A-Za-z0-9._~?#&=%:+@!$()*;,\/-]), where the quote is not itself
 *     preceded by `/` (excludes a `"`/`'` inside a regex literal like
 *     `/"/g`). `href="/"`, `"/v1/…"`, `fetch("/…")`, and template literals
 *     `` `/r/${id}/` `` (matched as their leading literal run) all count.
 *   - a site listed in the baseline's `allowlist` (file + token + count)
 *     is exempted — the recorded exceptions for constructions the rule
 *     cannot mechanically classify (e.g. `endsWith("/")` boundary checks);
 *     the exemption caps at `count` occurrences, so a new use of the same
 *     token in the same file still counts.
 *
 * Verdicts: any file's measured count above its baseline entry, or any
 * site in a file the baseline does not name, is a failure. A measured
 * count BELOW the baseline is a shrink advisory (exit 0) — the owning row
 * lowers the record with `--write-baseline`. The baseline JSON is the
 * auditable record: `measured_at`, the rule text, per-file counts and the
 * allow-list reasons are committed beside this script.
 *
 * Usage:
 *   node scripts/check-root-absolute-paths.mjs                 verify (the `check:paths` gate)
 *   node scripts/check-root-absolute-paths.mjs --write-baseline  re-measure + rewrite the baseline
 *   node scripts/check-root-absolute-paths.mjs --src DIR --baseline FILE   fixture/fixture-baseline (tests)
 *
 * Exit codes: 0 pass · 1 containment failure · 2 usage/input error ·
 * 3 vacuous (nothing measured — SIG-ENG-042, never a silent green).
 */

import { readdirSync, readFileSync, writeFileSync } from "node:fs";
import { join, relative } from "node:path";
import { fileURLToPath } from "node:url";

const WEB = fileURLToPath(new URL("..", import.meta.url));
const SCHEMA = "sig.path-containment-baseline/1";
const EXTENSIONS = new Set([".astro", ".ts", ".tsx", ".js", ".jsx", ".mjs", ".mts", ".css"]);
const SITE_RE = /(?<!\/)(["'`])(\/[A-Za-z0-9._~?#&=%:+@!$()*;,\/-]*)/g;
const RULE_TEXT =
  "quoted ('\"`') literal starting with '/' + URL-path chars, quote not " +
  "preceded by '/', over /*-*-/ <!-- --> and //-comment-stripped text in " +
  "web/src/** .astro/.ts/.tsx/.js/.jsx/.mjs/.mts/.css; allow-listed " +
  "file+token+count exemptions subtracted";
const PLAN_BASELINE =
  "G3 NEW-6 measured 85 sites / 36 files (0 BASE_URL uses) at " +
  "2026-09-30T18:47:42Z on the pre-refactor tree; re-measured at implement " +
  "time per the P35.65 contract — the baseline may only shrink (P36.66a's " +
  "sweep), never grow without a contract amendment";

function usage(msg) {
  if (msg) console.error(`check-root-absolute-paths: ${msg}`);
  console.error(
    "usage: node scripts/check-root-absolute-paths.mjs [--src DIR] [--baseline FILE] [--write-baseline]",
  );
  return 2;
}

function stripComments(text) {
  // Block comments and HTML comments, whitespace-preserving (line numbers
  // in reports stay honest).
  text = text.replace(/\/\*[\s\S]*?\*\//g, (m) => m.replace(/[^\n]/g, " "));
  text = text.replace(/<!--[\s\S]*?-->/g, (m) => m.replace(/[^\n]/g, " "));
  const stripTail = (s) => {
    const idx = s.indexOf("//");
    if (idx === -1) return s;
    // `//` preceded by `:` is a URL scheme (`https://`, `gs://`), keep scanning.
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

/** file → [{token, line}] of every measured site occurrence, in order. */
function measure(srcDir, rootDir) {
  const sites = new Map();
  for (const abs of sourceFiles(srcDir)) {
    const rel = relative(rootDir, abs).split("\\").join("/");
    const text = stripComments(readFileSync(abs, "utf-8"));
    const hits = [];
    text.split("\n").forEach((line, i) => {
      for (const m of line.matchAll(SITE_RE)) hits.push({ token: m[2], line: i + 1 });
    });
    if (hits.length) sites.set(rel, hits);
  }
  return sites;
}

/** Apply the allow-list: entry {file, token, count} exempts the first `count`
 *  occurrences of `token` in `file`. Returns {counted: Map(file→n), used,
 *  stale} — `stale` lists entries that matched nothing. */
function applyAllowlist(measured, allowlist) {
  const counted = new Map();
  const used = new Set();
  for (const [file, hits] of measured) {
    let n = 0;
    const remaining = new Map();
    for (const e of allowlist.filter((e) => e.file === file)) {
      remaining.set(e, e.count ?? 1);
    }
    for (const h of hits) {
      const entry = [...remaining.keys()].find(
        (e) => e.token === h.token && remaining.get(e) > 0,
      );
      if (entry) {
        remaining.set(entry, remaining.get(entry) - 1);
        used.add(entry);
      } else {
        n += 1;
      }
    }
    if (n > 0) counted.set(file, n);
  }
  const stale = allowlist.filter((e) => !used.has(e));
  return { counted, stale };
}

function readBaseline(path) {
  let data;
  try {
    data = JSON.parse(readFileSync(path, "utf-8"));
  } catch (e) {
    console.error(`check-root-absolute-paths: baseline unreadable: ${path} (${e.message})`);
    process.exit(2);
  }
  if (data.schema !== SCHEMA) {
    console.error(`check-root-absolute-paths: baseline schema ${data.schema} != ${SCHEMA}`);
    process.exit(2);
  }
  if (typeof data.files !== "object" || data.files === null) {
    console.error("check-root-absolute-paths: baseline lacks a files map");
    process.exit(2);
  }
  return data;
}

function writeBaseline(path, srcDir, rootDir, prior) {
  const measured = measure(srcDir, rootDir);
  const allowlist = prior?.allowlist ?? [];
  const { counted } = applyAllowlist(measured, allowlist);
  const files = Object.fromEntries([...counted.entries()].sort());
  const sites = Object.values(files).reduce((a, b) => a + b, 0);
  const record = {
    schema: SCHEMA,
    measured_at: new Date().toISOString().replace(/\.\d{3}Z$/, "Z"),
    measured_by: "node web/scripts/check-root-absolute-paths.mjs --write-baseline",
    rule: RULE_TEXT,
    scope: "web/src/**",
    plan_baseline: PLAN_BASELINE,
    sites,
    files,
    allowlist,
  };
  writeFileSync(path, JSON.stringify(record, null, 2) + "\n");
  console.log(
    `baseline written ${path}: ${sites} counted site(s) in ${Object.keys(files).length} file(s)` +
      ` (${allowlist.length} allow-list entr${allowlist.length === 1 ? "y" : "ies"} carried)`,
  );
  return 0;
}

function verify(srcDir, rootDir, baselinePath) {
  const baseline = readBaseline(baselinePath);
  const scanned = sourceFiles(srcDir).length;
  if (scanned === 0) {
    console.error(
      "check-root-absolute-paths: VACUOUS — no site-bearing files scanned in",
      srcDir,
    );
    return 3;
  }
  const measured = measure(srcDir, rootDir);
  const occurrences = [...measured.values()].reduce((a, h) => a + h.length, 0);
  const allowlist = Array.isArray(baseline.allowlist) ? baseline.allowlist : [];
  const { counted, stale } = applyAllowlist(measured, allowlist);

  const failures = [];
  const shrinks = [];
  let total = 0;
  for (const [file, n] of counted) {
    total += n;
    const recorded = baseline.files[file];
    if (recorded === undefined) {
      failures.push(`${file}: ${n} site(s) in a file the baseline does not name`);
    } else if (n > recorded) {
      failures.push(`${file}: ${recorded} recorded → ${n} measured (growth)`);
    } else if (n < recorded) {
      shrinks.push(`${file}: ${recorded} recorded → ${n} measured`);
    }
  }
  for (const file of Object.keys(baseline.files)) {
    if (!counted.has(file)) shrinks.push(`${file}: ${baseline.files[file]} recorded → 0 measured`);
  }

  console.log(
    `check-root-absolute-paths: ${occurrences} raw site(s) across ${scanned} scanned file(s); ` +
      `${total} counted after ${allowlist.length - stale.length} applied exemption(s); ` +
      `baseline ${baseline.sites} across ${Object.keys(baseline.files).length} file(s) ` +
      `(measured_at ${baseline.measured_at})`,
  );
  for (const s of shrinks.sort()) {
    console.log(`  shrink: ${s} — baseline may be lowered via --write-baseline by the owning row`);
  }
  for (const e of stale) {
    console.log(`  stale allow-list entry (matches nothing; prune in the owning row): ${e.file} ${e.token}`);
  }
  if (failures.length) {
    console.error(
      `\n✗ containment failure — root-absolute path sites grew (SIG-REL-008 / G3 NEW-6):`,
    );
    for (const f of failures.sort()) console.error(`    ${f}`);
    console.error(
      "  new templates build paths with withBase() (web/src/lib/paths.ts); " +
        "a construction the rule cannot classify is allow-listed with a reason, " +
        "never silently. The baseline may only shrink (P36.66a) — never grow " +
        "without a contract amendment.",
    );
    return 1;
  }
  console.log("✓ root-absolute path containment holds — no growth vs the recorded baseline.");
  return 0;
}

const args = process.argv.slice(2);
let srcDir = join(WEB, "src");
let baselinePath = join(WEB, "scripts", "root-absolute-paths-baseline.json");
let write = false;
for (let i = 0; i < args.length; i++) {
  const a = args[i];
  if (a === "--src") srcDir = args[++i];
  else if (a === "--baseline") baselinePath = args[++i];
  else if (a === "--write-baseline") write = true;
  else if (a === "--help" || a === "-h") process.exit(usage());
  else process.exit(usage(`unknown argument ${a}`));
  if (i >= args.length) process.exit(usage("missing value"));
}
if (srcDir === undefined || baselinePath === undefined) process.exit(usage("missing value"));

if (write) {
  const prior = baselinePath ? readBaseline(baselinePath) : null;
  process.exit(writeBaseline(baselinePath, srcDir, WEB, prior));
}
process.exit(verify(srcDir, WEB, baselinePath));
