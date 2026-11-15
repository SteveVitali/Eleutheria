// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

import { readdirSync, readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

// DR-K14-15 / SIG-UI-149 / K14 §4.9 + NEW-10 (P37.60): with
// `prefers-reduced-motion: reduce` there MUST be no animated transitions, map
// easing or animated layouts. The only sanctioned route to the animated map
// camera is src/lib/motion.ts (easeOrJumpTo / fitBoundsOrJump substitute
// jumpTo under reduce) — a bare `.easeTo(`, `.flyTo(` or `.fitBounds(` call
// anywhere else under src/ bypasses the guard silently, so this test scans
// the tree and fails on the bypass rather than the symptom.

const SRC = fileURLToPath(new URL("../../src", import.meta.url));
const GUARDED = new Set(["lib/motion.ts"]);

function* walk(dir: string): Generator<string> {
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    const full = join(dir, entry.name);
    if (entry.isDirectory()) yield* walk(full);
    else if (/\.(ts|tsx|astro)$/.test(entry.name)) yield full;
  }
}

describe("reduced-motion camera guard (SIG-UI-149, DR-K14-15)", () => {
  it("no bare .easeTo( / .flyTo( / .fitBounds( outside src/lib/motion.ts", () => {
    const offenders: string[] = [];
    for (const file of walk(SRC)) {
      const rel = file.slice(SRC.length + 1).split("\\").join("/");
      if (GUARDED.has(rel)) continue;
      const text = readFileSync(file, "utf8");
      for (const [i, line] of text.split("\n").entries()) {
        if (/\.(easeTo|flyTo|fitBounds)\s*\(/.test(line)) {
          offenders.push(`${rel}:${i + 1}: ${line.trim()}`);
        }
      }
    }
    expect(
      offenders,
      "animated camera call outside src/lib/motion.ts — route it through easeOrJumpTo / fitBoundsOrJump so prefers-reduced-motion is honoured",
    ).toEqual([]);
  });

  it("the guard module itself carries the reduced-motion substitution", () => {
    const text = readFileSync(join(SRC, "lib/motion.ts"), "utf8");
    expect(text).toContain("prefers-reduced-motion: reduce");
    expect(text).toContain("jumpTo");
  });
});
