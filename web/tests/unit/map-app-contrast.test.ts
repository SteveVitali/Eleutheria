// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// P36.37 (SIG-UI-107) — symbol contrast ≥ 3:1 against basemap fills in both
// themes, mechanical check over the committed style documents + tokens.
import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import { SIG_DATA_HUE, SIG_DATA_SEQ_400, SIG_DATA_SEQ_700 } from "../../src/lib/design-tokens";

const WEB = join(fileURLToPath(new URL(".", import.meta.url)), "..", "..");

/** WCAG relative luminance + contrast for an hsl() string or #rrggbb. */
function lum(h: number, s: number, l: number): number {
  const a = (s * Math.min(l, 1 - l)) / 100;
  const f = (n: number) => {
    const k = (n + h / 30) % 12;
    return l / 100 - a * Math.max(-1, Math.min(k - 3, Math.min(9 - k, 1)));
  };
  const lin = (c: number) => (c <= 0.04045 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4));
  return 0.2126 * lin(f(0)) + 0.7152 * lin(f(8)) + 0.0722 * lin(f(4));
}
function hslLum(v: string): number {
  const m = /hsl\(([\d.]+)(?:deg)?\s+([\d.]+)%\s+([\d.]+)%\)/.exec(v);
  if (!m) throw new Error(`not hsl(): ${v}`);
  return lum(Number(m[1]), Number(m[2]), Number(m[3]));
}
function hexLum(v: string): number {
  const r = parseInt(v.slice(1, 3), 16) / 255;
  const g = parseInt(v.slice(3, 5), 16) / 255;
  const b = parseInt(v.slice(5, 7), 16) / 255;
  const lin = (c: number) => (c <= 0.04045 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4));
  return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b);
}
function ratio(a: number, b: number): number {
  const [hi, lo] = [Math.max(a, b), Math.min(a, b)];
  return (hi + 0.05) / (lo + 0.05);
}

/** Collect every hex colour the committed style uses (fills + lines). */
function styleColours(file: string): string[] {
  const text = readFileSync(join(WEB, "public", "map", file), "utf-8");
  return [...new Set([...text.matchAll(/#[0-9a-fA-F]{6}\b/g)].map((m) => m[0].toLowerCase()))];
}

describe("SIG-UI-107 — symbol contrast ≥3:1 vs basemap fills, both themes", () => {
  const channels = [
    ["data hue (fill)", hslLum(SIG_DATA_HUE)],
    ["seq-400 (hollow ring)", hslLum(SIG_DATA_SEQ_400)],
    ["seq-700 (ring stroke)", hslLum(SIG_DATA_SEQ_700)],
  ] as const;
  for (const style of ["style-light.json", "style-dark.json"]) {
    for (const [name, sym] of channels) {
      it(`${name} ≥ 3:1 against the worst-fill colour of ${style}`, () => {
        const worst = Math.min(...styleColours(style).map((c) => ratio(sym, hexLum(c))));
        // The honest check: contrast against the basemap's OWN background +
        // fill palette — the worst case is what matters.
        expect(worst, `${name} vs ${style}`).toBeGreaterThanOrEqual(3);
      });
    }
  }
});
