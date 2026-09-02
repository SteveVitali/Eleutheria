// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

// SIG-UI-006: green MUST NOT be used for epistemic state — it reads as endorsement,
// and SIG reports, it does not endorse. Every epistemic colour token (`--sig-epi-*`)
// is written as hsl() so this test can parse its hue and prove it lies OUTSIDE the
// green band. The band is generous (chartreuse through spring-green/teal) so nothing
// green-adjacent slips through.
const GREEN_HUE_MIN = 75;
const GREEN_HUE_MAX = 165;

const CSS_PATH = fileURLToPath(new URL("../../src/styles/epistemic.css", import.meta.url));
const css = readFileSync(CSS_PATH, "utf8");

function epistemicTokens(): Array<{ name: string; hue: number }> {
  const re = /(--sig-epi-[\w-]+):\s*hsl\(\s*([\d.]+)deg/g;
  const out: Array<{ name: string; hue: number }> = [];
  let m: RegExpExecArray | null;
  while ((m = re.exec(css)) !== null) out.push({ name: m[1]!, hue: Number(m[2]) });
  return out;
}

describe("design tokens: green never for epistemic state (SIG-UI-006)", () => {
  const tokens = epistemicTokens();

  it("finds the epistemic colour tokens (the parse is meaningful)", () => {
    // Support (5) + agreement (4) + currency (4) + status (4) + absence ink (1).
    expect(tokens.length).toBeGreaterThanOrEqual(18);
  });

  it("every --sig-epi-* token is expressed as an hsl() (so its hue is checkable)", () => {
    const rawEpi = [...css.matchAll(/(--sig-epi-[\w-]+):\s*([^;]+);/g)];
    for (const [, name, value] of rawEpi) {
      expect(value!.trim().startsWith("hsl("), `${name} must be hsl()`).toBe(true);
    }
  });

  it("no epistemic token uses a green hue", () => {
    for (const { name, hue } of tokens) {
      const isGreen = hue >= GREEN_HUE_MIN && hue <= GREEN_HUE_MAX;
      expect(isGreen, `${name} hue ${hue}deg is in the green band`).toBe(false);
    }
  });
});
