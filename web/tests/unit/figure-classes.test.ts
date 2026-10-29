// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * P36.27 (R11-K13-FIG-01a, ADR-157, SIG-UI-066/131): the web half of the
 * static figure kit is the `.sig-fig-*` class vocabulary in epistemic.css —
 * the page styling every inline figure the kit emits depends on. This test
 * pins the two invariants that keep the kit honest:
 *
 *  1. the full `FIGURE_CLASSES` vocabulary the Python serializer may emit
 *     (`exports/src/exports/figures/lexicon.py`) is present in the
 *     stylesheet — an unstyled emitted class is a silent visual fork; and
 *  2. every colour channel a `.sig-fig-*` rule binds is a `var(--sig-*)`
 *     token — no literal colour may enter the figure vocabulary (check-tokens
 *     already forbids literals file-wide; this asserts the figure block
 *     specifically, so a relaxed rule elsewhere cannot mask a figure drift).
 */

import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const STYLES = new URL("../../src/styles/", import.meta.url);
const css = readFileSync(fileURLToPath(new URL("epistemic.css", STYLES)), "utf8");

/** The kit's emitted class vocabulary — mirrors
 * `exports/src/exports/figures/lexicon.py` `FIGURE_CLASSES`. Classes that
 * carry a visual channel must have a rule (STYLED); semantic hooks that the
 * markup carries for composition or future kinds are marker classes — the
 * stylesheet's P36.27 comment block names them so nothing is silently
 * unstyled. */
const STYLED_CLASSES = [
  "sig-fig",
  "sig-fig-outline",
  "sig-fig-provisional",
  "sig-fig-child",
  "sig-fig-child-uncovered",
  "sig-fig-child-pending",
  "sig-fig-hatch-line",
  "sig-fig-area",
  "sig-fig-point",
  "sig-fig-src-single",
  "sig-fig-contested",
  "sig-fig-locator-inset",
  "sig-fig-caption",
  "sig-fig-legend",
] as const;

const MARKER_CLASSES = [
  "sig-fig-geo",
  "sig-fig-layer",
  "sig-fig-outline-state",
  "sig-fig-src-corroborated",
  "sig-fig-locator",
  "sig-fig-sprite",
  "sig-fig-sprite-cell",
] as const;

describe("the figure-kit class vocabulary (P36.27)", () => {
  it("carries every styled class as a selector in epistemic.css", () => {
    for (const cls of STYLED_CLASSES) {
      const re = new RegExp(`\\.${cls}\\b`);
      expect(re.test(css), `.${cls} missing from epistemic.css`).toBe(true);
    }
  });

  it("names every marker class in the stylesheet's marker comment", () => {
    for (const cls of MARKER_CLASSES) {
      expect(css.includes(`.${cls}`), `.${cls} undocumented in epistemic.css`).toBe(
        true,
      );
    }
  });

  it("binds only var(--sig-*) colour channels in .sig-fig rules", () => {
    const colourLiterals =
      /#[0-9a-f]{3,8}\b|\b(?:rgb|rgba|hsl|hsla|hwb|lab|lch|oklab|oklch)\s*\(|\b(?:red|blue|green|black|white|grey|gray)\b/i;
    // Extract every rule whose selector names a .sig-fig class.
    const ruleRe = /([^{}]+)\{([^{}]+)\}/g;
    let found = 0;
    for (const m of css.matchAll(ruleRe)) {
      const selector = m[1];
      if (!/\.sig-fig/.test(selector)) continue;
      const body = m[2];
      found += 1;
      for (const decl of body.split(";")) {
        const [prop, ...rest] = decl.split(":");
        if (!rest.length) continue;
        const value = rest.join(":").trim();
        if (!value) continue;
        const p = prop.trim();
        if (
          /^(fill|stroke|color|background(?:-color)?|border(?:-color)?|caret-color|column-rule(?:-color)?|text-decoration(?:-color)?|accent-color)$/.test(
            p,
          )
        ) {
          expect(
            value.startsWith("var(--sig-") || value === "none" || value === "url(#fig-hatch)",
            `${selector.trim()} { ${p}: ${value} } — figure classes take tokens only`,
          ).toBe(true);
          expect(colourLiterals.test(value), `literal colour in ${selector}`).toBe(false);
        }
      }
    }
    expect(found, "no .sig-fig rules found — the figure block is missing").toBeGreaterThan(5);
  });
});
