// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * P36.25 (K14 UXK14-7 / K14 §4.12 + DR-K14-20; §56.11 SIG-UI-154; the plan
 * cell D-K14-2 [B-22] = yes carried verbatim — an answered decision,
 * implemented never re-decided) — the brand assets.
 *
 * `sig.brand-mark/1` — the node-link glyph: three nodes, two solid edges and
 * ONE dashed edge ("a link claimed but not yet confirmed"), drawn in one ink
 * colour. It works at 16 px as a favicon, uses no epistemic colour, no hatch
 * and no seal or badge shapes that could suggest a government body, and the
 * dashed edge is BRAND — never a legend symbol (K13 C-01's rule carried:
 * line pattern = access kind only, and this edge is not a legend).
 *
 * `sig.social-card/1` — one static card per ADR-155 page type (T0/T1/T2; the
 * ticket's "per page type" is the registry's type — K14's home/place/
 * organization/source/methodology surfaces are all T1 content pages, and
 * per-place cards are explicitly later per K14 §4.12). Cards are generated
 * at build time (SVG → PNG, the `sigBrandAssets` hook in astro.config.mjs)
 * — 1200×630, each showing the type's heading, the wordmark and the
 * release's "data as of". T3 (`/curate/**`) resolves no card: it is
 * loopback-only, never shared (ADR-068).
 *
 * Colour literals mirror `src/styles/tokens.css` verbatim — a standalone
 * SVG/PNG document has no cascade, so the token VALUES are embedded, and
 * `tests/unit/brand.test.ts` fails when a mirrored value drifts from
 * tokens.css (SIG-UI-146's "tokens only" rule applied by reference).
 */

import { classifyRoute, PAGE_TYPES, type PageType } from "./page-types";

// --- sig.brand-mark/1 -------------------------------------------------------

/** The token values the standalone assets embed (mirrored from tokens.css;
 *  a unit test pins each literal against the defining file). */
export const BRAND_COLOURS = {
  /** `--sig-ink` — the glyph's one colour (light scheme). */
  ink: "hsl(218.2deg 20% 10.8%)",
  /** `--sig-bg` — the card/page ground. */
  paper: "hsl(240deg 14.3% 98.6%)",
  /** `--sig-ink-muted` — the card's secondary text. */
  muted: "hsl(220deg 10.3% 39.8%)",
  /** `--sig-rule` — the card's hairline divider. */
  rule: "hsl(218.2deg 15.1% 85.7%)",
} as const;

export interface MarkNode {
  cx: number;
  cy: number;
  r: number;
}

export interface MarkEdge {
  /** Index into `nodes`. */
  a: number;
  b: number;
  /** Exactly one edge is dashed — "a link claimed but not yet confirmed". */
  dashed: boolean;
}

export const BRAND_MARK = {
  schema: "sig.brand-mark/1" as const,
  viewBox: "0 0 64 64",
  nodes: [
    { cx: 16, cy: 16, r: 6 },
    { cx: 48, cy: 16, r: 6 },
    { cx: 32, cy: 48, r: 6 },
  ] as readonly MarkNode[],
  edges: [
    { a: 0, b: 1, dashed: false },
    { a: 1, b: 2, dashed: false },
    { a: 2, b: 0, dashed: true },
  ] as readonly MarkEdge[],
  strokeWidth: 5,
  /** The dashed edge's pattern — long enough to read as a broken line at 16 px. */
  dasharray: "6 4",
} as const;

/** The glyph's inner SVG (edges first — the node fills cap the line ends).
 *  `color` is `currentColor` for the inline wordmark (follows `--sig-ink` in
 *  either theme) and the embedded token literal for standalone files. */
export function renderMarkInner(color: string = "currentColor"): string {
  const { nodes, edges, strokeWidth, dasharray } = BRAND_MARK;
  const lines = edges.map((e) => {
    const a = nodes[e.a]!;
    const b = nodes[e.b]!;
    const dash = e.dashed ? ` stroke-dasharray="${dasharray}"` : "";
    return `<line x1="${a.cx}" y1="${a.cy}" x2="${b.cx}" y2="${b.cy}" stroke="${color}" stroke-width="${strokeWidth}" stroke-linecap="round"${dash}/>`;
  });
  const circles = nodes.map(
    (n) => `<circle cx="${n.cx}" cy="${n.cy}" r="${n.r}" fill="${color}" />`,
  );
  return [...lines, ...circles].join("");
}

/** The standalone logo file emitted at `brand/logo.svg` — the mark in ink on
 *  a transparent ground (the wordmark lockup itself is header chrome). */
export function renderLogoSvg(): string {
  return (
    `<svg xmlns="http://www.w3.org/2000/svg" viewBox="${BRAND_MARK.viewBox}" role="img" aria-label="SIG — Surveillance Infrastructure Graph">` +
    renderMarkInner(BRAND_COLOURS.ink) +
    `</svg>\n`
  );
}

/** The favicon document — the mark in paper on the ink tile, so the glyph
 *  reads on light and dark browser chrome alike. `public/favicon.svg` carries
 *  this output verbatim; the unit test pins the file to this renderer. */
export function renderFaviconSvg(): string {
  // The mark occupies a centred 42 px tile inside the 64 px icon.
  const inset = 11;
  const scale = 42 / 64;
  return (
    `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" role="img" aria-label="SIG">\n` +
    `  <rect width="64" height="64" rx="12" fill="${BRAND_COLOURS.ink}" />\n` +
    `  <g transform="translate(${inset} ${inset}) scale(${scale})">` +
    renderMarkInner(BRAND_COLOURS.paper) +
    `</g>\n` +
    `</svg>\n`
  );
}

// --- sig.social-card/1 ------------------------------------------------------

export const SOCIAL_CARD_SCHEMA = "sig.social-card/1" as const;
export const SOCIAL_CARD_SIZE = { width: 1200, height: 630 } as const;

export interface SocialCard {
  /** The ADR-155 page type this card covers (T3 resolves no card). */
  type: Exclude<PageType, "T3">;
  /** The emitted PNG's dist-relative path (joined through `withBase`). */
  file: string;
  /** The card's large heading — the type's share text (K14 §4.12: the page
   *  title generalises to the type's title for a per-type card). */
  heading: string;
  /** The smaller line under the heading. */
  subline: string;
  /** `og:image:alt` — what the card says, for readers who cannot see it. */
  alt: string;
}

export const SOCIAL_CARDS: readonly SocialCard[] = [
  {
    type: "T0",
    file: "social/card-t0.png",
    heading: "A fixed record",
    subline: "A citable, script-free record page — Surveillance Infrastructure Graph",
    alt: "SIG social card — a fixed, citable record page",
  },
  {
    type: "T1",
    file: "social/card-t1.png",
    heading: "Surveillance Infrastructure Graph",
    subline: "Public surveillance records — every fact linked to its source",
    alt: "SIG social card — Surveillance Infrastructure Graph",
  },
  {
    type: "T2",
    file: "social/card-t2.png",
    heading: "Explore the records",
    subline: "Map, graph and search — Surveillance Infrastructure Graph",
    alt: "SIG social card — map, graph and search",
  },
];

/** The card a route shares, resolved through the one registry (the same
 *  authority that classifies the route for budgets and CSP). `null` for T3
 *  or an unclassifiable path — the caller emits no og:image then. */
export function socialCardForRoute(path: string): SocialCard | null {
  const classified = classifyRoute(path);
  if (!classified.ok || classified.entry.type === "T3") return null;
  return SOCIAL_CARDS.find((c) => c.type === classified.entry.type) ?? null;
}

function escapeXml(s: string): string {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

/** One card's SVG source — the build hook rasterises it to PNG. Layout:
 *  the glyph + wordmark top-left, the type's heading centred on the left
 *  half, a hairline and the "data as of" line at the foot. Every value is a
 *  constant or the release's as-of — deterministic per build. */
export function renderCardSvg(card: SocialCard, asOfWorld: string): string {
  const { width, height } = SOCIAL_CARD_SIZE;
  const c = BRAND_COLOURS;
  const font = "DejaVu Sans, Liberation Sans, Helvetica, Arial, sans-serif";
  return (
    `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${width} ${height}">\n` +
    `  <rect width="${width}" height="${height}" fill="${c.paper}" />\n` +
    `  <g transform="translate(80 72) scale(1.25)">` +
    renderMarkInner(c.ink) +
    `</g>\n` +
    `  <text x="180" y="112" font-family="${font}" font-size="40" font-weight="700" fill="${c.ink}">SIG</text>\n` +
    `  <text x="180" y="152" font-family="${font}" font-size="26" fill="${c.muted}">Surveillance Infrastructure Graph</text>\n` +
    `  <text x="80" y="370" font-family="${font}" font-size="64" font-weight="700" fill="${c.ink}">${escapeXml(card.heading)}</text>\n` +
    `  <text x="80" y="430" font-family="${font}" font-size="30" fill="${c.muted}">${escapeXml(card.subline)}</text>\n` +
    `  <line x1="80" y1="520" x2="${width - 80}" y2="520" stroke="${c.rule}" stroke-width="2" />\n` +
    `  <text x="80" y="572" font-family="${font}" font-size="24" fill="${c.muted}">Data as of ${escapeXml(asOfWorld)}</text>\n` +
    `  <text x="${width - 80}" y="572" text-anchor="end" font-family="${font}" font-size="24" fill="${c.muted}">surveillancegraph.org</text>\n` +
    `</svg>\n`
  );
}

/** The page types a card covers — every registered type minus T3 (tested so
 *  a new type can never silently ship without a card decision). The per-type
 *  meta-description templates live beside the existing helper in
 *  `lib/meta.ts`. */
export const CARDED_TYPES: readonly PageType[] = PAGE_TYPES.filter((t) => t !== "T3");
