// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { gzipSync } from "node:zlib";
import { describe, expect, it } from "vitest";

// SIG-UI-006: green MUST NOT be used for epistemic state — it reads as endorsement,
// and SIG reports, it does not endorse. Every epistemic colour token (`--sig-epi-*`)
// resolves to an hsl() so this test can parse its hue and prove it lies OUTSIDE the
// green band. The band is generous (chartreuse through spring-green/teal) so nothing
// green-adjacent slips through.
const GREEN_HUE_MIN = 75;
const GREEN_HUE_MAX = 165;

const STYLES = new URL("../../src/styles/", import.meta.url);
const css = readFileSync(fileURLToPath(new URL("tokens.css", STYLES)), "utf8");
const stripComments = (s: string) => s.replace(/\/\*[\s\S]*?\*\//g, " ");
const componentCss = ["epistemic.css", "islands.css", "curate.css"].map((f) =>
  stripComments(readFileSync(fileURLToPath(new URL(f, STYLES)), "utf8")),
);

/* --- Declaration parsing -----------------------------------------------------
 * tokens.css carries three :root contexts — light (default), the dark media
 * block and the print media block — plus custom-property aliases. We collect
 * every `--name: value` per context and resolve var() chains to the literal. */

interface Decl {
  name: string;
  value: string;
  context: "light" | "dark" | "print";
}

function parseDecls(): Decl[] {
  const out: Decl[] = [];
  const darkRe = /@media\s*\(prefers-color-scheme:\s*dark\)\s*\{([\s\S]*?)\n\}\n?/;
  const printRe = /@media\s*print\s*\{([\s\S]*?)\n\}\n?$/;
  const darkBlock = darkRe.exec(css)?.[1] ?? "";
  const printBlock = printRe.exec(css)?.[1] ?? "";
  const lightSection = css.replace(darkRe, "").replace(printRe, "");
  for (const [context, text] of [
    ["light", lightSection],
    ["dark", darkBlock],
    ["print", printBlock],
  ] as const) {
    for (const m of text.matchAll(/(--sig-[\w-]+)\s*:\s*([^;]+);/g)) {
      out.push({ name: m[1]!, value: m[2]!.trim(), context });
    }
  }
  return out;
}

const decls = parseDecls();

function resolve(name: string, context: Decl["context"] = "light"): string {
  let value = decls.find((d) => d.name === name && d.context === context)?.value;
  if (value === undefined) {
    // a token left undefined in a later context inherits the light value
    value = decls.find((d) => d.name === name && d.context === "light")?.value;
  }
  expect(value, `token ${name} must be declared`).toBeDefined();
  const chain = /^var\((--sig-[\w-]+)\)$/.exec(value!);
  if (chain) return resolve(chain[1]!, context);
  return value!;
}

function hsl(name: string, context: Decl["context"] = "light"): { h: number; s: number; l: number } {
  const v = resolve(name, context);
  const m = /^hsl\(\s*([\d.]+)deg\s+([\d.]+)%\s+([\d.]+)%\s*\)$/.exec(v);
  expect(m, `${name} (${context}) must resolve to hsl(h s l), got ${v}`).toBeTruthy();
  return { h: Number(m![1]), s: Number(m![2]), l: Number(m![3]) };
}

/* --- WCAG relative luminance + contrast (the spec formula, sRGB) ------------ */

function hslToRgb(h: number, s: number, l: number): [number, number, number] {
  const c = (1 - Math.abs(2 * l - 1)) * s;
  const hp = (((h % 360) + 360) % 360) / 60;
  const x = c * (1 - Math.abs((hp % 2) - 1));
  let r = 0, g = 0, b = 0;
  if (hp < 1) [r, g, b] = [c, x, 0];
  else if (hp < 2) [r, g, b] = [x, c, 0];
  else if (hp < 3) [r, g, b] = [0, c, x];
  else if (hp < 4) [r, g, b] = [0, x, c];
  else if (hp < 5) [r, g, b] = [x, 0, c];
  else [r, g, b] = [c, 0, x];
  const m0 = l - c / 2;
  return [r + m0, g + m0, b + m0];
}

function luminance(h: number, s: number, l: number): number {
  const chan = (v: number) => (v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4));
  const [r, g, b] = hslToRgb(h, s / 100, l / 100);
  return 0.2126 * chan(r) + 0.7152 * chan(g) + 0.0722 * chan(b);
}

function contrast(fg: { h: number; s: number; l: number }, bg: { h: number; s: number; l: number }): number {
  const [l1, l2] = [luminance(fg.h, fg.s, fg.l), luminance(bg.h, bg.s, bg.l)].sort((a, b) => b - a);
  return (l1 + 0.05) / (l2 + 0.05);
}

/* --- SIG-UI-006: the green band --------------------------------------------- */

describe("design tokens: green never for epistemic state (SIG-UI-006)", () => {
  const epi = decls.filter((d) => d.name.startsWith("--sig-epi-"));

  it("finds the epistemic colour tokens across the three contexts", () => {
    expect(epi.length).toBeGreaterThanOrEqual(18);
  });

  it("every --sig-epi-* token resolves to an hsl() (so its hue is checkable)", () => {
    for (const { name, context } of epi) {
      expect(resolve(name, context), `${name} (${context})`).toMatch(/^hsl\(/);
    }
  });

  it("no epistemic token uses a green hue, in any context", () => {
    for (const { name, context } of epi) {
      const { h } = hsl(name, context);
      const isGreen = h >= GREEN_HUE_MIN && h <= GREEN_HUE_MAX;
      expect(isGreen, `${name} hue ${h}deg (${context}) is in the green band`).toBe(false);
    }
  });
});

/* --- SIG-UI-148: the 8-step type scale --------------------------------------- */

describe("design tokens: the 8-step type scale (SIG-UI-148)", () => {
  const steps = ["--sig-step--2", "--sig-step--1", "--sig-step-0", "--sig-step-1", "--sig-step-2", "--sig-step-3", "--sig-step-4", "--sig-step-5"];

  it("declares exactly the 8 steps", () => {
    for (const s of steps) {
      expect(resolve(s), s).toBeDefined();
    }
    const declared = decls.filter((d) => /^--sig-step-[0-9-]+$/.test(d.name) && d.context === "light");
    expect(declared.map((d) => d.name).sort()).toEqual([...steps].sort());
  });

  it("floors at 13 px (0.8125rem) — no legal text under the floor", () => {
    expect(resolve("--sig-step--2")).toBe("0.8125rem");
  });

  it("is strictly increasing across the fixed steps", () => {
    const px = (v: string) => Number(v.replace("rem", "")) * 16;
    const fixed = steps.slice(0, 6).map((s) => px(resolve(s)));
    for (let i = 1; i < fixed.length; i++) {
      expect(fixed[i]!).toBeGreaterThan(fixed[i - 1]!);
    }
  });

  it("steps 4 and 5 are responsive clamps inside the K14 bounds", () => {
    expect(resolve("--sig-step-4")).toBe("clamp(2rem, 1.6rem + 1.6vw, 2.5rem)");
    expect(resolve("--sig-step-5")).toBe("clamp(2.25rem, 1.8rem + 2.2vw, 3rem)");
  });

  it("the prose measure stays inside the ≤70 ch contract", () => {
    expect(Number(resolve("--sig-measure").replace("ch", ""))).toBeLessThanOrEqual(70);
  });
});

/* --- The slate support ramp (D-K14-5): single-hue + monotone lightness ------ */

describe("design tokens: the support ramp is ordinal (K14 NEW-3)", () => {
  const ramp = ["--sig-epi-support-4", "--sig-epi-support-3", "--sig-epi-support-2", "--sig-epi-support-1"];

  it("lightness is strictly monotone in the ramp order, light and dark", () => {
    for (const context of ["light", "dark", "print"] as const) {
      const ls = ramp.map((t) => hsl(t, context).l);
      for (let i = 1; i < ls.length; i++) {
        expect(ls[i]!, `${ramp[i]} L${ls[i]} must differ from ${ramp[i - 1]} L${ls[i - 1]} (${context})`).not.toBe(ls[i - 1]);
      }
      const diffs = ls.slice(1).map((v, i) => v - ls[i]!);
      expect(diffs.every((d) => d > 0) || diffs.every((d) => d < 0), `ramp ${context} must be monotone`).toBe(true);
    }
  });

  it("the ramp is single-hue (every step within 215deg ± 8)", () => {
    for (const context of ["light", "dark"] as const) {
      for (const t of ramp) {
        const { h } = hsl(t, context);
        expect(Math.abs(h - 215), `${t} hue ${h}deg (${context}) leaves the slate family`).toBeLessThanOrEqual(8);
      }
    }
  });

  it("UNSUPPORTED is a neutral zero state, not a ramp step", () => {
    const { l } = hsl("--sig-epi-support-unsupported");
    const rampLs = ramp.map((t) => hsl(t).l);
    expect(rampLs).not.toContain(l);
  });
});

/* --- Reserved hues (K14 NEW-2): raspberry & amber are single-meaning -------- */

describe("design tokens: the reserved hues are single-meaning", () => {
  it("the disagreement token is the only source of raspberry in component styles", () => {
    for (const source of componentCss) {
      expect(source, "component styles must not carry colour literals").not.toMatch(
        /#[0-9a-f]{3,8}\b|(?:rgb|hsl|hwb|lab|oklab|oklch)\s*\(/i,
      );
    }
  });

  it("--sig-epi-disagree-* appears only on contested / range / unresolved rules", () => {
    const allowedSelector =
      /contested|irreconcilable|unresolved|sig-range|agreement|resolution_status/i;
    for (const source of componentCss) {
      const rules = source.matchAll(/([^{}@]+)\{([^{}]*--sig-epi-disagree[\w-]*[^{}]*)\}/g);
      for (const m of rules) {
        const selector = m[1]!.trim();
        expect(
          allowedSelector.test(selector),
          `selector '${selector}' uses the disagreement hue — it is reserved for contested/unresolved`,
        ).toBe(true);
      }
    }
  });

  it("--sig-epi-provisional-* appears only on the provisional state", () => {
    let seen = 0;
    for (const source of componentCss) {
      const rules = source.matchAll(/([^{}@]+)\{([^{}]*--sig-epi-provisional[\w-]*[^{}]*)\}/g);
      for (const m of rules) {
        seen++;
        expect(/provisional/i.test(m[1]!), `selector '${m[1]}' uses the provisional hue`).toBe(true);
      }
    }
    expect(seen, "the provisional state must consume its tokens somewhere").toBeGreaterThan(0);
  });

  it("the incompleteness banner is neutral (no disagreement token)", () => {
    const banner = /([^{}@]*sig-incompleteness[^{}@]*)\{([^{}]*)\}/.exec(componentCss[0]!);
    expect(banner, ".sig-incompleteness rule missing").toBeTruthy();
    expect(banner![2]).not.toMatch(/disagree|provisional|status-unresolved/);
    expect(banner![2]).toMatch(/var\(--sig-(rule-strong|surface|ink)/);
  });
});

/* --- Contrast (WCAG 2.2 AA on the chosen palette, both schemes) ------------- */

describe("design tokens: contrast pairs meet WCAG 2.2 AA", () => {
  it("light scheme body text ≥ 12:1, muted/link/state text ≥ 4.5:1", () => {
    const bg = hsl("--sig-bg");
    expect(contrast(hsl("--sig-ink"), bg)).toBeGreaterThanOrEqual(12);
    expect(contrast(hsl("--sig-ink-muted"), bg)).toBeGreaterThanOrEqual(4.5);
    expect(contrast(hsl("--sig-link"), bg)).toBeGreaterThanOrEqual(4.5);
    expect(contrast(hsl("--sig-epi-disagree-text"), bg)).toBeGreaterThanOrEqual(4.5);
    expect(contrast(hsl("--sig-epi-provisional-text"), bg)).toBeGreaterThanOrEqual(4.5);
    expect(contrast(hsl("--sig-epi-inferred-ink"), bg)).toBeGreaterThanOrEqual(4.5);
  });

  it("light scheme surfaces keep AA for ink + muted", () => {
    for (const surface of ["--sig-surface", "--sig-surface-2"] as const) {
      expect(contrast(hsl("--sig-ink"), hsl(surface)), `ink on ${surface}`).toBeGreaterThanOrEqual(12);
      expect(contrast(hsl("--sig-ink-muted"), hsl(surface)), `muted on ${surface}`).toBeGreaterThanOrEqual(4.5);
    }
  });

  it("essential boundaries reach the 3:1 non-text floor", () => {
    expect(contrast(hsl("--sig-rule-strong"), hsl("--sig-surface"))).toBeGreaterThanOrEqual(3);
    expect(contrast(hsl("--sig-rule-strong"), hsl("--sig-surface-2"))).toBeGreaterThanOrEqual(3);
  });

  it("dark scheme keeps the same pairs at AA (chosen tokens, not inversion)", () => {
    const bg = hsl("--sig-bg", "dark");
    expect(contrast(hsl("--sig-ink", "dark"), bg)).toBeGreaterThanOrEqual(12);
    expect(contrast(hsl("--sig-ink-muted", "dark"), bg)).toBeGreaterThanOrEqual(4.5);
    expect(contrast(hsl("--sig-link", "dark"), bg)).toBeGreaterThanOrEqual(4.5);
    expect(contrast(hsl("--sig-epi-disagree-text", "dark"), bg)).toBeGreaterThanOrEqual(4.5);
    expect(contrast(hsl("--sig-epi-provisional-text", "dark"), bg)).toBeGreaterThanOrEqual(4.5);
    expect(contrast(hsl("--sig-epi-inferred-ink", "dark"), bg)).toBeGreaterThanOrEqual(4.5);
  });
});

/* --- Scheme + motion structure ---------------------------------------------- */

describe("design tokens: scheme, motion and print posture", () => {
  it("declares color-scheme light dark (both schemes are first-class)", () => {
    expect(css).toMatch(/color-scheme:\s*light\s+dark/);
  });

  it("the dark block redefines the neutral + state sets (not an inversion)", () => {
    for (const t of ["--sig-bg", "--sig-surface", "--sig-ink", "--sig-ink-muted", "--sig-link", "--sig-epi-disagree-mark"]) {
      const dark = decls.find((d) => d.name === t && d.context === "dark");
      expect(dark, `${t} must have a chosen dark value`).toBeTruthy();
      expect(dark!.value).not.toBe(decls.find((d) => d.name === t && d.context === "light")!.value);
    }
  });

  it("print forces the light token set", () => {
    for (const t of ["--sig-bg", "--sig-ink", "--sig-link", "--sig-epi-disagree-mark"]) {
      const print = decls.find((d) => d.name === t && d.context === "print");
      expect(print, `${t} must have a print value`).toBeTruthy();
      expect(print!.value).toBe(decls.find((d) => d.name === t && d.context === "light")!.value);
    }
  });

  it("reduced motion zeroes the transition tokens", () => {
    const block = /@media\s*\(prefers-reduced-motion:\s*reduce\)\s*\{([\s\S]*?)\}/.exec(css);
    expect(block, "reduced-motion block missing").toBeTruthy();
    expect(block![1]).toMatch(/--sig-motion-1:\s*0ms/);
    expect(block![1]).toMatch(/--sig-motion-2:\s*0ms/);
  });

  it("motion defaults live in the 120–160 ms band (colour/opacity only)", () => {
    expect(Number(resolve("--sig-motion-1").replace("ms", ""))).toBeGreaterThanOrEqual(120);
    expect(Number(resolve("--sig-motion-2").replace("ms", ""))).toBeLessThanOrEqual(160);
    for (const source of componentCss) {
      const transitions = source.matchAll(/transition:\s*([^;]+);/g);
      for (const m of transitions) {
        for (const prop of m[1]!.split(",")) {
          const pname = prop.trim().split(/\s+/)[0]!;
          expect(
            /color|opacity/.test(pname),
            `transition '${prop.trim()}' animates layout — only colour/opacity may move (K14 §4.9)`,
          ).toBe(true);
        }
      }
    }
  });

  it("the Public Sans face is self-hosted, variable and optional-display", () => {
    expect(css).toMatch(/font-family:\s*"Public Sans Variable"/);
    expect(css).toMatch(/font-display:\s*optional/);
    expect(css).toMatch(/url\("\.\.\/assets\/fonts\/public-sans[^"]*\.woff2"\)/);
    expect(css).toMatch(/font-weight:\s*100\s+900/);
  });
});

/* --- The TypeScript mirror (no forked palettes) ----------------------------- */

describe("design tokens: the TS mirror cannot fork the palette (SIG-UI-146)", () => {
  it("every exported colour constant is byte-equal to its CSS token", () => {
    const ts = readFileSync(fileURLToPath(new URL("../../src/lib/design-tokens.ts", STYLES)), "utf8");
    const exported = [...ts.matchAll(/export const (SIG_[A-Z0-9_]+)\s*=\s*"([^"]+)"/g)];
    expect(exported.length).toBeGreaterThan(0);
    for (const m of exported) {
      const tokenName = `--${m[1]!.toLowerCase().replace(/_/g, "-")}`;
      expect(
        resolve(tokenName),
        `${m[1]} must equal the ${tokenName} token exactly`,
      ).toBe(m[2]);
    }
  });

  it("the MapLibre style modules carry no colour literals outside the mirror", () => {
    for (const f of ["../../src/lib/map-tiles.ts", "../../src/islands/MapIsland.tsx"]) {
      const src = readFileSync(fileURLToPath(new URL(f, STYLES)), "utf8");
      const body = src.replace(/\/\*[\s\S]*?\*\//g, " ").replace(/\/\/[^\n]*/g, "");
      const hits = body.match(/#[0-9a-f]{3,8}\b|(?:hsl|rgb)\s*\(/gi) ?? [];
      // rgba(0,0,0,0) — a transparent fill — is not a colour choice.
      const real = hits.filter((h) => !/rgba/i.test(h));
      expect(real, `${f} holds ${real.length} forked colour literal(s)`).toEqual([]);
    }
  });
});

/* --- SIG-UI-156: budgets ------------------------------------------------------ */

describe("design tokens: budgets (SIG-UI-156)", () => {
  it("the self-hosted font file ships ≤ 30 KiB", () => {
    const font = readFileSync(
      fileURLToPath(new URL("../../src/assets/fonts/public-sans-latin-wght-normal.woff2", STYLES)),
    );
    expect(font.byteLength).toBeLessThanOrEqual(30 * 1024);
  });

  it("the raw design-system css gzips well under the 12 KiB wire ceiling", () => {
    // A source-level smoke check: the built, minified bundle is measured by
    // scripts/check-tokens.mjs after `astro build`. Source gzip is a looser
    // proxy (comments survive), so a generous 2× headroom keeps this honest
    // without duplicating the wire measurement.
    const combined = css + componentCss.join("");
    expect(gzipSync(Buffer.from(combined)).byteLength).toBeLessThanOrEqual(24 * 1024);
  });
});
