// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * P36.52 (DSRC-02; the FIG-01b over-time chart, K5 §4.2 "Over time") — a
 * static stacked-bar SVG on the K14 chart anatomy: one axis, direct labels,
 * thin marks (2 px strokes), generated from the artifact's `series[]` rows.
 * The `<table>` twin beside it carries the same numbers (SIG-DSRC-006 — the
 * chart is never the only carrier). Zero JS, zero external assets.
 */

import type { OverTimeModel } from "./dossier-sources";

const WIDTH = 720;
const HEIGHT = 240;
const PAD_L = 44;
const PAD_B = 34;
const PAD_T = 12;
const PAD_R = 8;
/** Series fills are class-based (the strict CSP allows no style attributes);
 * the hues live in `.sig-dsrc-fill--N` — the single-hue data ramp plus one
 * neutral step, never the reserved raspberry/amber (K14 §4.3). */
const FILL_CLASSES = 8;
const fillClass = (i: number): string => `sig-dsrc-fill sig-dsrc-fill--${i % FILL_CLASSES}`;

const esc = (s: string): string =>
  s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");

const fnum = (v: number): string =>
  v !== Math.floor(v) ? v.toFixed(2).replace(/0+$/, "").replace(/\.$/, "") : String(v);

/** The stacked-bar SVG for the monthly first-seen-records model. */
export function overTimeSvg(model: OverTimeModel, title: string): string {
  const { periods, series, totals } = model;
  const max = Math.max(1, ...totals);
  const plotW = WIDTH - PAD_L - PAD_R;
  const plotH = HEIGHT - PAD_T - PAD_B;
  const n = periods.length;
  const band = plotW / Math.max(1, n);
  const barW = Math.min(48, band * 0.72);
  const parts: string[] = [];
  parts.push(
    `<svg class="sig-dsrc-chart" viewBox="0 0 ${WIDTH} ${HEIGHT}" role="img" ` +
      `aria-label="${esc(title)}" xmlns="http://www.w3.org/2000/svg">`,
  );
  // axis + baseline + one labelled tick per end of the value axis
  parts.push(
    `<line x1="${PAD_L}" y1="${HEIGHT - PAD_B}" x2="${WIDTH - PAD_R}" y2="${HEIGHT - PAD_B}" stroke="currentColor" stroke-width="2" />`,
  );
  parts.push(
    `<line x1="${PAD_L}" y1="${PAD_T}" x2="${PAD_L}" y2="${HEIGHT - PAD_B}" stroke="currentColor" stroke-width="2" />`,
  );
  parts.push(
    `<text x="${PAD_L - 6}" y="${PAD_T + 8}" text-anchor="end" font-size="11" fill="currentColor">${fnum(max)}</text>`,
  );
  parts.push(
    `<text x="${PAD_L - 6}" y="${HEIGHT - PAD_B - 2}" text-anchor="end" font-size="11" fill="currentColor">0</text>`,
  );
  periods.forEach((p, i) => {
    const cx = PAD_L + band * i + band / 2;
    let y = HEIGHT - PAD_B;
    series.forEach((s, si) => {
      const v = s.values[i] ?? 0;
      if (v <= 0) return;
      const h = Math.max(1, (v / max) * plotH);
      y -= h;
      parts.push(
        `<rect class="${fillClass(si)}" x="${fnum(cx - barW / 2)}" y="${fnum(y)}" width="${fnum(barW)}" height="${fnum(h)}"><title>${esc(s.name)} — ${esc(p)}: ${v} records first seen</title></rect>`,
      );
    });
    // the total above the stack (direct label, no legend lookup needed)
    parts.push(
      `<text x="${fnum(cx)}" y="${fnum(Math.max(PAD_T + 4, y - 4))}" text-anchor="middle" font-size="10" fill="currentColor">${totals[i] ?? 0}</text>`,
    );
    parts.push(
      `<text x="${fnum(cx)}" y="${HEIGHT - PAD_B + 16}" text-anchor="middle" font-size="10" fill="currentColor">${esc(p)}</text>`,
    );
  });
  parts.push(`</svg>`);
  return parts.join("");
}

/** The legend rows — name + swatch + series total (direct labels, K14). */
export function overTimeLegend(
  model: OverTimeModel,
): { name: string; cls: string; total: number }[] {
  return model.series.map((s, i) => ({
    name: s.name,
    cls: fillClass(i),
    total: s.values.reduce((n, v) => n + v, 0),
  }));
}
