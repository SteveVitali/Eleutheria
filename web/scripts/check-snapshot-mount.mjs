// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * P36.66a (SIG-UI-075 / SIG-REL-008 / D-J3-6 [B-19] = yes) — the fixture
 * `/s/<pub>/` mount: an `astro build` under `SIG_BASE_PATH=/s/p-<64hex>`
 * renders the SAME tree a snapshot deploy stages under the prefix, and every
 * same-origin link in the emitted HTML must then stay INSIDE the base or name
 * a declared exception namespace (SIG-REL-008: `/r/<pub>/`, `/releases/`, and
 * the declared latest-version surfaces — the live `/v1/` API and `/intake/`
 * receiver, both labelled "live, not a citation" per SIG-UI-076).
 *
 * This is the sweep's proof leg: the source-side containment check
 * (`check-root-absolute-paths.mjs`) fails on GROWTH of raw `"/…"` literals;
 * this check reads the EMITTED bytes, so a link that escapes the base through
 * any construction — a template literal, an unwrapped builder, a data-sourced
 * href — is a loud failure, never a silent green.
 *
 * Scan rule (deterministic):
 *   - every emitted `*.html` is scanned for `(href|src|action|poster)="…"`
 *     attributes plus absolute same-origin URLs on those attributes;
 *   - a root-absolute value (`/…`, never `//…` — protocol-relative is a fail
 *     on its own) must start with the snapshot base or an exception prefix;
 *   - an absolute `https://surveillancegraph.org/…` value must start with the
 *     base, name an exception path, or carry `as_of_` query selectors (the
 *     declared legacy-selector form — J3 §8.3's edge-resolved URLs, mounted
 *     outside the snapshot namespace by design);
 *   - canonical, og:url and og:image are checked by the same rule — a
 *     snapshot page's canonical names its own `/s/<pub>/` copy.
 *
 * Usage:
 *   node scripts/check-snapshot-mount.mjs                 build + verify (the `check:snapshot` gate)
 *   node scripts/check-snapshot-mount.mjs --dist DIR      verify an existing base-build
 *   node scripts/check-snapshot-mount.mjs --src HTML      unit-fixture: one HTML file vs the rule
 *   node scripts/check-snapshot-mount.mjs --print-base    the fixture publication id
 *
 * Exit codes: 0 pass · 1 containment failure · 2 usage/input error ·
 * 3 vacuous (nothing scanned — SIG-ENG-042).
 */

import { execFileSync } from "node:child_process";
import { mkdtempSync, readdirSync, readFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, relative } from "node:path";
import { fileURLToPath } from "node:url";

const WEB = fileURLToPath(new URL("..", import.meta.url));

/** The fixture snapshot publication — a real `p-<64hex>` shape so the cite
 *  block's immutable-path predicate (`/s/p-[0-9a-f]{64}/`) resolves. */
export const SNAPSHOT_PUB =
  "p-0000000000000000000000000000000000000000000000000000000000000066";
export const SNAPSHOT_BASE = `/s/${SNAPSHOT_PUB}/`;

/** The declared exception namespaces (SIG-REL-008 + SIG-UI-076's live
 *  surfaces) — the web-side mirror of `OUTSIDE_BASE_PREFIXES` in
 *  `src/lib/paths.ts`, kept duplicated so the check never trusts the code it
 *  audits. */
const EXCEPTION_PREFIXES = ["/r/", "/releases/", "/v1/", "/intake/"];
const SITE_ORIGIN = "https://surveillancegraph.org";
const ATTR_RE = /(?:href|src|action|poster)="([^"]*)"/g;

function usage(msg) {
  if (msg) console.error(`check-snapshot-mount: ${msg}`);
  console.error(
    "usage: node scripts/check-snapshot-mount.mjs [--dist DIR] [--src HTML] [--print-base]",
  );
  return 2;
}

function htmlFiles(dir) {
  const files = [];
  const walk = (d) => {
    for (const e of readdirSync(d, { withFileTypes: true })) {
      const p = join(d, e.name);
      if (e.isDirectory()) walk(p);
      else if (e.isFile() && p.endsWith(".html")) files.push(p);
    }
  };
  walk(dir);
  return files.sort();
}

/** The violations one HTML file carries (empty array = clean). */
export function scanHtml(html, { base = SNAPSHOT_BASE, origin = SITE_ORIGIN } = {}) {
  const violations = [];
  for (const m of html.matchAll(ATTR_RE)) {
    const v = m[1];
    if (v.startsWith("//")) {
      violations.push(`protocol-relative ${v.slice(0, 80)} — never allowed`);
      continue;
    }
    if (v.startsWith("/")) {
      if (!v.startsWith(base) && !EXCEPTION_PREFIXES.some((p) => v.startsWith(p))) {
        violations.push(`root-absolute ${v.slice(0, 80)} escapes the snapshot base`);
      }
      continue;
    }
    if (v.startsWith(`${origin}/`)) {
      const path = v.slice(origin.length);
      if (path.startsWith(base)) continue;
      if (EXCEPTION_PREFIXES.some((p) => path.startsWith(p))) continue;
      if (path.includes("as_of_")) continue; // the declared legacy-selector form
      violations.push(`absolute same-origin ${v.slice(0, 90)} escapes the snapshot base`);
    }
  }
  return violations;
}

function verifyDir(dir) {
  const files = htmlFiles(dir);
  if (files.length === 0) {
    console.error("check-snapshot-mount: VACUOUS — no *.html under", dir);
    return 3;
  }
  const failures = [];
  let attrs = 0;
  for (const f of files) {
    const html = readFileSync(f, "utf-8");
    attrs += (html.match(ATTR_RE) ?? []).length;
    for (const v of scanHtml(html)) {
      failures.push(`${relative(dir, f)}: ${v}`);
    }
  }
  console.log(
    `check-snapshot-mount: ${files.length} page(s), ${attrs} link attr(s) scanned under base ${SNAPSHOT_BASE}`,
  );
  if (failures.length) {
    console.error(
      `\n✗ snapshot containment failure — same-origin links escape ${SNAPSHOT_BASE} (SIG-REL-008):`,
    );
    for (const f of failures.sort()) console.error(`    ${f}`);
    console.error(
      "  in-site links build with withBase(); the /r/, /releases/, /v1/ and " +
        "/intake/ namespaces (and the ?as_of_ selector form) are the only " +
        "declared exceptions — route them through rootPath().",
    );
    return 1;
  }
  console.log("✓ snapshot mount holds — every same-origin link stays inside the base or a declared exception.");
  return 0;
}

// Vitest imports scanHtml/SNAPSHOT_BASE — the CLI legs run only as main.
const IS_MAIN = process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1];
if (!IS_MAIN) {
  // module mode — exports only
} else {
const args = process.argv.slice(2);
let dist = null;
let src = null;
for (let i = 0; i < args.length; i++) {
  if (args[i] === "--dist") dist = args[++i];
  else if (args[i] === "--src") src = args[++i];
  else if (args[i] === "--print-base") {
    console.log(SNAPSHOT_BASE);
    process.exit(0);
  } else if (args[i] === "--help" || args[i] === "-h") process.exit(usage());
  else process.exit(usage(`unknown argument ${args[i]}`));
}

if (src) {
  const html = readFileSync(src, "utf-8");
  const vs = scanHtml(html);
  for (const v of vs) console.log(v);
  process.exit(vs.length ? 1 : 0);
}

if (!dist) {
  dist = mkdtempSync(join(tmpdir(), "sig-snap-dist-"));
  console.log(`check-snapshot-mount: fixtures build → ${dist} (SIG_BASE_PATH=${SNAPSHOT_BASE.slice(0, -1)})`);
  execFileSync(
    "npx",
    ["astro", "build", "--outDir", dist],
    {
      cwd: WEB,
      stdio: "inherit",
      env: { ...process.env, SIG_BASE_PATH: SNAPSHOT_BASE.slice(0, -1) },
    },
  );
}
process.exit(verifyDir(dist));
}
