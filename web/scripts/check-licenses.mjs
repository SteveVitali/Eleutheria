// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * The dependency-licence CI gate (SIG-UI-039).
 *
 * Every dependency must be OSI-licensed; non-commercial (CC-BY-NC),
 * source-available, and dual-BUSL licences are excluded — and the exclusion is
 * checked HERE, in CI, not by memory. The gate is two lists:
 *   - ALLOW: SPDX identifiers we accept (the OSI-approved permissive set the shell
 *     uses, plus the uncontroversially-free BlueOak-1.0.0 and CC0-1.0 that appear
 *     in the toolchain tree). A dependency whose licence is NOT on this list fails
 *     the build, forcing an explicit human review rather than a silent accept.
 *   - DENY: substrings that mark the categories the spec explicitly excludes. Any
 *     match fails immediately, even if some field also lists an allowed licence.
 *
 * It scans the production dependency tree by default (what actually ships /
 * underpins the site). Pass `--all` to scan devDependencies too.
 */

import { init } from "license-checker-rseidelsohn";

// OSI-approved SPDX identifiers (spec-default: SIG-UI-039 requires OSI-only).
const OSI_ALLOW = new Set([
  "MIT",
  "ISC",
  "Apache-2.0",
  "BSD-2-Clause",
  "BSD-3-Clause",
  "0BSD",
  "MPL-2.0",
  "LGPL-3.0-or-later",
  "LGPL-3.0-only",
  "Python-2.0",
  "Unlicense",
]);

// EXPLICIT WAIVERS: licences that are NOT OSI-approved but are uncontroversially
// free/public-domain and are NONE of the categories SIG-UI-039 excludes (not
// non-commercial, not source-available, not BUSL). Kept separate from OSI_ALLOW so
// the gate never silently mislabels a licence as OSI. Each entry is a deliberate,
// documented exception (see ADR-049) present only in the build toolchain tree:
//   - CC0-1.0     — public-domain dedication (e.g. type-only / data packages)
//   - BlueOak-1.0.0 — permissive; on the Blue Oak Council permissive list
const WAIVED = new Set(["CC0-1.0", "BlueOak-1.0.0"]);

const ALLOW = new Set([...OSI_ALLOW, ...WAIVED]);

// The categories SIG-UI-039 explicitly rules out. Matched case-insensitively as a
// substring of the licence string, so "BUSL-1.1", "CC-BY-NC-4.0", "SSPL-1.0",
// "Elastic-2.0", and "Commons-Clause" all trip the gate.
const DENY = ["-NC", "NONCOMMERCIAL", "BUSL", "SSPL", "ELASTIC", "COMMONS-CLAUSE", "PROPRIETARY"];

// The workspace package itself is private and carries no distributable licence of
// its own to vet; exclude it (its code licence is the repo's LICENSE / SPDX headers).
const SELF = "@sig/web@0.0.0";

function splitExpression(expr) {
  // Split an SPDX expression / dual licence into atoms: "(MIT OR Apache-2.0)".
  return expr
    .replace(/[()]/g, " ")
    .split(/\s+(?:OR|AND|WITH)\s+|\s*\/\s*/i)
    .map((s) => s.trim())
    .filter(Boolean);
}

const scanAll = process.argv.includes("--all");

init({ start: process.cwd(), production: !scanAll, excludePackages: [SELF] }, (err, packages) => {
  if (err) {
    console.error("license-checker failed:", err);
    process.exit(2);
  }
  const denied = [];
  const notAllowed = [];
  for (const [name, info] of Object.entries(packages)) {
    const raw = Array.isArray(info.licenses) ? info.licenses.join(" OR ") : String(info.licenses ?? "");
    const upper = raw.toUpperCase();
    if (DENY.some((d) => upper.includes(d))) {
      denied.push(`${name}: ${raw}`);
      continue;
    }
    const atoms = splitExpression(raw);
    // A dual/expression licence passes if ANY atom is allowed (we may pick it).
    const ok = atoms.length > 0 && atoms.some((a) => ALLOW.has(a));
    if (!ok) notAllowed.push(`${name}: ${raw || "(no licence field)"}`);
  }

  const total = Object.keys(packages).length;
  if (denied.length || notAllowed.length) {
    if (denied.length) {
      console.error(`\n✗ ${denied.length} dependency(ies) carry an EXCLUDED licence (SIG-UI-039):`);
      for (const d of denied) console.error(`    ${d}`);
    }
    if (notAllowed.length) {
      console.error(`\n✗ ${notAllowed.length} dependency(ies) carry a licence not on the OSI allowlist (review required):`);
      for (const n of notAllowed) console.error(`    ${n}`);
    }
    console.error(`\nScanned ${total} package(s). See web/scripts/check-licenses.mjs to adjust the lists.`);
    process.exit(1);
  }
  console.log(`✓ All ${total} ${scanAll ? "" : "production "}dependencies are OSI/permissive-licensed (SIG-UI-039).`);
});
