// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// P36.25 (K14 UXK14-7 / §4.12 + DR-K14-20; §56.11 SIG-UI-154; D-K14-2 [B-22] =
// yes carried verbatim): the brand contract — the node-link mark's geometry
// (three nodes, two solid edges, exactly one dashed edge, one ink colour, no
// epistemic hue, no badge), the favicon file pinned to the one renderer, the
// per-page-type social-card registry resolving through the page-type
// registry, the card renderer's determinism, the colour literals' byte-exact
// mirror of tokens.css, and the per-type meta-description templates.

import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

import {
  BRAND_COLOURS,
  BRAND_MARK,
  CARDED_TYPES,
  renderCardSvg,
  renderFaviconSvg,
  renderLogoSvg,
  renderMarkInner,
  socialCardForRoute,
  SOCIAL_CARDS,
  SOCIAL_CARD_SIZE,
} from "../../src/lib/brand";
import { defaultDescription } from "../../src/lib/meta";
import { PAGE_TYPES } from "../../src/lib/page-types";

const SRC = new URL("../../src/", import.meta.url);
const PUBLIC = new URL("../../public/", import.meta.url);

describe("sig.brand-mark/1 — the node-link glyph (K14 §4.12)", () => {
  it("carries exactly three nodes", () => {
    expect(BRAND_MARK.nodes).toHaveLength(3);
    for (const n of BRAND_MARK.nodes) {
      expect(n.r).toBeGreaterThan(0);
    }
  });

  it("carries exactly two solid edges and one dashed edge", () => {
    expect(BRAND_MARK.edges).toHaveLength(3);
    expect(BRAND_MARK.edges.filter((e) => e.dashed)).toHaveLength(1);
    expect(BRAND_MARK.edges.filter((e) => !e.dashed)).toHaveLength(2);
    for (const e of BRAND_MARK.edges) {
      expect(BRAND_MARK.nodes[e.a]).toBeDefined();
      expect(BRAND_MARK.nodes[e.b]).toBeDefined();
      expect(e.a).not.toBe(e.b);
    }
  });

  it("renders one line per edge and one circle per node, edges capped by the nodes", () => {
    const inner = renderMarkInner();
    expect(inner.match(/<line /g)).toHaveLength(3);
    expect(inner.match(/<circle /g)).toHaveLength(3);
    // edges render first so each node's fill caps its line ends.
    expect(inner.indexOf("<line")).toBeLessThan(inner.indexOf("<circle"));
    // exactly one line is dashed.
    expect(inner.match(/stroke-dasharray/g)).toHaveLength(1);
    expect(inner).toContain(`stroke-dasharray="${BRAND_MARK.dasharray}"`);
  });

  it("draws in a single colour — currentColor inline, the ink literal standalone", () => {
    const inner = renderMarkInner();
    expect(inner).not.toMatch(/hsl\(/);
    expect(inner).toContain('stroke="currentColor"');
    expect(inner).toContain('fill="currentColor"');
    const standalone = renderMarkInner(BRAND_COLOURS.ink);
    expect(standalone).toContain(`stroke="${BRAND_COLOURS.ink}"`);
    // No epistemic colour may leak into the mark (K14 §4.12's rule).
    expect(standalone).not.toMatch(/amber|raspberry|epi-/);
  });

  it("keeps the mark badge-free — no shield/seal/star primitives", () => {
    const inner = renderMarkInner();
    expect(inner).not.toMatch(/<(path|polygon|rect|ellipse|text)\b/);
  });

  it("logo.svg is the mark in ink on a transparent ground", () => {
    const svg = renderLogoSvg();
    expect(svg).toContain(`viewBox="${BRAND_MARK.viewBox}"`);
    expect(svg).toContain(renderMarkInner(BRAND_COLOURS.ink));
    expect(svg).not.toContain("<rect");
  });

  it("public/favicon.svg is byte-identical to the one renderer — never a redrawn second mark", () => {
    const file = readFileSync(fileURLToPath(new URL("favicon.svg", PUBLIC)), "utf8");
    expect(file).toBe(renderFaviconSvg());
  });
});

describe("brand colours mirror tokens.css (SIG-UI-146 applied by reference)", () => {
  const tokens = readFileSync(
    fileURLToPath(new URL("styles/tokens.css", SRC)),
    "utf8",
  );
  const token = (name: string): string =>
    tokens.match(new RegExp(`${name}:\\s*([^;]+);`))?.[1]?.trim() ?? "";
  it.each([
    ["ink", "--sig-ink"],
    ["paper", "--sig-bg"],
    ["muted", "--sig-ink-muted"],
    ["rule", "--sig-rule"],
  ])("%s embeds %s verbatim", (key, name) => {
    const value = token(name);
    expect(value, `tokens.css defines ${name}`).not.toBe("");
    expect(BRAND_COLOURS[key as keyof typeof BRAND_COLOURS]).toBe(value);
  });
});

describe("sig.social-card/1 — one static card per page type", () => {
  it("covers every registered page type except T3 (loopback-only, ADR-068)", () => {
    expect(CARDED_TYPES).toEqual(PAGE_TYPES.filter((t) => t !== "T3"));
    expect(SOCIAL_CARDS.map((c) => c.type).sort()).toEqual([...CARDED_TYPES].sort());
  });

  it("emits each card at the share size with a distinct, stable file", () => {
    expect(SOCIAL_CARD_SIZE).toEqual({ width: 1200, height: 630 });
    const files = SOCIAL_CARDS.map((c) => c.file);
    expect(new Set(files).size).toBe(files.length);
    for (const c of SOCIAL_CARDS) {
      expect(c.file).toMatch(/^social\/[\w-]+\.png$/);
      expect(c.heading.length).toBeGreaterThan(0);
      expect(c.subline.length).toBeGreaterThan(0);
      expect(c.alt.length).toBeGreaterThan(0);
    }
  });

  it.each([
    ["/", "T1"],
    ["/dossier/oklahoma-city/", "T1"],
    ["/sources/", "T1"],
    ["/methodology/", "T1"],
    ["/dossier/oklahoma-city/print/", "T0"],
    ["/dispute/", "T0"],
    ["/404.html", "T0"],
    ["/map/", "T2"],
    ["/network/", "T2"],
    ["/search/", "T2"],
  ])("route %s resolves the %s card", (path, type) => {
    const card = socialCardForRoute(path);
    expect(card, `${path} resolves a card`).not.toBeNull();
    expect(card!.type).toBe(type);
  });

  it.each([["/curate/"], ["/curate/submit/"], ["/never-registered/x/"]])(
    "route %s resolves no card (T3 or unregistered)",
    (path) => {
      expect(socialCardForRoute(path)).toBeNull();
    },
  );

  it("renders deterministically — same card + as-of, same SVG", () => {
    const card = SOCIAL_CARDS[0]!;
    expect(renderCardSvg(card, "2026-08-20")).toBe(renderCardSvg(card, "2026-08-20"));
  });

  it("each card carries its heading, the wordmark, the as-of and the origin (K14 §4.12)", () => {
    for (const card of SOCIAL_CARDS) {
      const svg = renderCardSvg(card, "2026-08-20");
      expect(svg).toContain(`viewBox="0 0 ${SOCIAL_CARD_SIZE.width} ${SOCIAL_CARD_SIZE.height}"`);
      expect(svg).toContain(card.heading);
      expect(svg).toContain(card.subline);
      expect(svg).toContain("Surveillance Infrastructure Graph");
      expect(svg).toContain("Data as of 2026-08-20");
      expect(svg).toContain("surveillancegraph.org");
      // The mark itself rides the card — the dashed edge is brand here too.
      expect(svg).toContain('stroke-dasharray="6 4"');
      expect(svg.match(/<circle /g)).toHaveLength(3);
    }
  });

  it("escapes XML in card text — a heading can never break the document", () => {
    const card = { ...SOCIAL_CARDS[0]!, heading: 'a <b> "quote" & more' };
    const svg = renderCardSvg(card, "2026-08-20");
    expect(svg).toContain("a &lt;b&gt; &quot;quote&quot; &amp; more");
    expect(svg).not.toContain('a <b> "quote"');
  });
});

describe("per-type meta descriptions (SIG-UI-154; MD-01 is the T1 form verbatim)", () => {
  it("derives a unique description per type from the unique page title", () => {
    expect(defaultDescription("Data freshness", "T1")).toBe(
      "Data freshness — Surveillance Infrastructure Graph (SIG)",
    );
    expect(defaultDescription("Data freshness", "T0")).toBe(
      "Data freshness — a fixed, no-JavaScript page in the Surveillance Infrastructure Graph (SIG)",
    );
    expect(defaultDescription("Data freshness", "T2")).toBe(
      "Data freshness — interactive views over the Surveillance Infrastructure Graph (SIG): map, graph and search",
    );
    expect(defaultDescription("Data freshness", "T3")).toBe(
      "Data freshness — Surveillance Infrastructure Graph (SIG)",
    );
  });

  it("stays unique across pages and types (the unique title drives it)", () => {
    const a = defaultDescription("Page not found", "T0");
    const b = defaultDescription("Data freshness", "T0");
    expect(a).not.toBe(b);
    expect(a).not.toBe(defaultDescription("Page not found", "T1"));
  });
});
