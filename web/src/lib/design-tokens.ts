// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * P36.16 (R11-K13-UXK14-1, SIG-UI-146): the token layer's TypeScript mirror.
 *
 * `styles/tokens.css` is the single source of truth for every colour value.
 * Non-CSS consumers — the MapLibre style document, which takes literal colour
 * strings and cannot read `var(--sig-*)` — take the SAME values from here, and
 * `tests/unit/design-tokens.test.ts` pins every constant below byte-equal to
 * the CSS token it names. A drift between this file and tokens.css fails the
 * unit suite — one vocabulary, no forked palettes.
 *
 * Only the values a non-CSS consumer needs live here; DOM/SVG code that can use
 * `var(--sig-*)` must, and must not import this file for colour.
 *
 * P36.17 (SIG-UI-143): the lexicon (`lexicon.json`) binds which token each
 * legend channel uses — `legend.dataHue.token` names the map's data hue. The
 * map style and the figure kit resolve that NAME through `sigTokenValue` /
 * `SIG_DATA_HUE` below, so the legend's declared binding — not a hard-coded
 * constant — picks the colour (one vocabulary, one source).
 */

// The lexicon JSON is imported directly — NOT via lexicon.ts, whose fs/path
// spec-reading helpers are build-time-only. This module ships inside the
// browser island bundles (MapIsland/NetworkIsland); a node builtin in the
// import graph would break hydration (the T2 islands would never reach
// data-ready). Plain JSON is the cross-runtime contract by design.
import lexicon from "./lexicon.json";

/** `--sig-data-1` — the single categorical data hue (blue): site fills. */
export const SIG_DATA_1 = "hsl(212.8deg 67.7% 50.2%)";
/** `--sig-data-seq-400` — sequential ramp, lighter step: cluster bubbles. */
export const SIG_DATA_SEQ_400 = "hsl(213deg 82% 56.5%)";
/** `--sig-data-seq-700` — sequential ramp, darkest step: data strokes/edges. */
export const SIG_DATA_SEQ_700 = "hsl(214deg 78% 23.5%)";
/** `--sig-ink` — the neutral ink: the map focus ring and label text. */
export const SIG_INK = "hsl(218.2deg 20% 10.8%)";
/** `--sig-surface-2` — the raised-panel neutral: the plain map canvas. */
export const SIG_SURFACE_2 = "hsl(216deg 23.8% 95.9%)";

/**
 * The `--sig-*` token names this module mirrors → their literal values.
 * Exists for data-driven consumers (the lexicon names tokens by string);
 * literal consumers keep using the named exports above.
 */
const SIG_TOKEN_VALUES: Record<string, string> = {
  "sig-data-1": SIG_DATA_1,
  "sig-data-seq-400": SIG_DATA_SEQ_400,
  "sig-data-seq-700": SIG_DATA_SEQ_700,
  "sig-ink": SIG_INK,
  "sig-surface-2": SIG_SURFACE_2,
};

/**
 * Resolve a `--sig-*` token name to its literal value. Fails closed: a name
 * the mirror does not carry is a build-time error, never a silent default —
 * a misnamed lexicon binding must not silently recolour a surface.
 */
export function sigTokenValue(name: string): string {
  const value = SIG_TOKEN_VALUES[name];
  if (!value) {
    throw new Error(
      `token "${name}" is not in the design-tokens mirror — the lexicon may only ` +
        `bind tokens mirrored in design-tokens.ts`,
    );
  }
  return value;
}

/**
 * The map/figure data hue, resolved through the lexicon's declared binding
 * (`sig.lexicon/1` → `legend.dataHue.token`). Equals `SIG_DATA_1` today; the
 * unit suite pins both the binding and the byte-equality so a fork fails.
 */
export const SIG_DATA_HUE = sigTokenValue(lexicon.legend.dataHue.token);
