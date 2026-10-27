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
 */

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
