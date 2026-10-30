// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// P36.25 — K14 UXK14-7 "logo" + §4.12 + DR-K14-20 (§56.11 SIG-UI-154;
// D-K14-2 [B-22] = yes carried verbatim). Runs against the BUILT static site:
// the node-link glyph in the wordmark (three nodes, two solid edges, one
// dashed edge — the dashed edge is brand, never a legend symbol), the favicon
// set (SVG + 32 px PNG + 180 px touch icon + brand/logo.svg), one static
// social card per page type generated at build time and referenced by
// OG/Twitter meta on every public route (T3 shares none), and the per-type
// meta-description forms — all with zero added JavaScript.
import { test, expect } from "@playwright/test";
import { DISCOVERED_ROUTES } from "./pages";

const ORIGIN = "https://surveillancegraph.org";

// The flat error copies are byte-identical to /403/, /410/ and /500/ (the
// nginx error_page mapping) — their og:url names the canonical page, so they
// sit out of the per-route og:url assertion the way chrome.spec.ts sits them
// out of the unique-title check.
const FLAT_ERROR_COPIES = new Set(["/403.html", "/410.html", "/500.html"]);
const PUBLIC_ROUTES = DISCOVERED_ROUTES.filter(
  (r) => !r.internal && !FLAT_ERROR_COPIES.has(r.path),
);

async function htmlOf(
  request: import("@playwright/test").APIRequestContext,
  path: string,
) {
  const res = await request.get(path);
  expect(res.status(), `${path} must resolve`).toBe(200);
  return res.text();
}

function pngSize(buf: Buffer): { width: number; height: number } {
  expect(buf.subarray(0, 8).toString("hex")).toBe("89504e470d0a1a0a");
  expect(buf.subarray(12, 16).toString()).toBe("IHDR");
  return { width: buf.readUInt32BE(16), height: buf.readUInt32BE(20) };
}

// ------------------------------------------------- K14 UXK14-7: the logo

test("the wordmark carries the node-link glyph — three nodes, two solid + one dashed edge (SIG-UI-154)", async ({
  page,
}) => {
  await page.goto("/");
  const glyph = page.locator("svg.sig-wordmark__glyph");
  await expect(glyph).toHaveCount(1);
  await expect(glyph.locator("circle")).toHaveCount(3);
  await expect(glyph.locator("line")).toHaveCount(3);
  await expect(glyph.locator("line[stroke-dasharray]")).toHaveCount(1);
  await expect(glyph.locator("line[stroke-dasharray='6 4']")).toHaveCount(1);
  // One ink colour — every primitive inherits currentColor, so the mark can
  // never drift into an epistemic hue (K14 §4.12's no-green/no-epistemic rule).
  const strokes = await glyph
    .locator("line")
    .evaluateAll((lines) => lines.map((l) => l.getAttribute("stroke")));
  const fills = await glyph
    .locator("circle")
    .evaluateAll((c) => c.map((n) => n.getAttribute("fill")));
  expect([...strokes, ...fills]).toEqual(
    ["currentColor", "currentColor", "currentColor", "currentColor", "currentColor", "currentColor"],
  );
  // No badge: the glyph contains no seal-like path/polygon/rect/text.
  expect(await glyph.locator("path, polygon, rect, ellipse, text").count()).toBe(0);
});

test("the brand's dashed edge is never an epistemic legend symbol (K14 §4.12)", async ({
  page,
}) => {
  // On a T1 dossier the ONLY dashed SVG line on the page is the brand glyph's
  // — epistemic states on data pages are CSS borders/patterns, and the
  // legend's own dash patterns never reuse the brand's 6 4.
  await page.goto("/dossier/oklahoma-city/");
  const offMark = await page.evaluate(() => {
    const dashed = [...document.querySelectorAll("line[stroke-dasharray='6 4']")];
    return dashed.filter((l) => !l.closest("svg.sig-wordmark__glyph")).length;
  });
  expect(offMark, "the brand dash appears only inside the wordmark glyph").toBe(0);
  // On the T2 network page the epistemic legend edges keep their own dash
  // styles — distinct from the brand's 6 4.
  await page.goto("/network/");
  const outside = await page.evaluate(() => {
    const dashed = [...document.querySelectorAll("line[stroke-dasharray='6 4']")];
    return dashed.filter((l) => !l.closest("svg.sig-wordmark__glyph")).length;
  });
  expect(outside).toBe(0);
});

// ------------------------------------------- K14 §4.12: the favicon set

test("the favicon set ships — SVG mark, 32 px PNG, 180 px touch icon, brand/logo.svg", async ({
  request,
}) => {
  const favicon = await request.get("/favicon.svg");
  expect(favicon.status()).toBe(200);
  expect(favicon.headers()["content-type"]).toContain("image/svg+xml");
  const faviconBody = await favicon.text();
  // The favicon IS the node-link mark (not a second, redrawn mark).
  expect(faviconBody.match(/<circle /g)).toHaveLength(3);
  expect(faviconBody.match(/<line /g)).toHaveLength(3);
  expect(faviconBody.match(/stroke-dasharray/g)).toHaveLength(1);
  // Plain + self-contained: no external references, no script.
  expect(faviconBody).not.toMatch(/<script|href=|@import|url\(/);

  const png = await request.get("/favicon-32.png");
  expect(png.status()).toBe(200);
  expect(png.headers()["content-type"]).toContain("image/png");
  expect(pngSize(Buffer.from(await png.body()))).toEqual({ width: 32, height: 32 });

  const touch = await request.get("/apple-touch-icon.png");
  expect(touch.status()).toBe(200);
  expect(touch.headers()["content-type"]).toContain("image/png");
  expect(pngSize(Buffer.from(await touch.body()))).toEqual({ width: 180, height: 180 });

  const logo = await request.get("/brand/logo.svg");
  expect(logo.status()).toBe(200);
  const logoBody = await logo.text();
  expect(logoBody.match(/<circle /g)).toHaveLength(3);
  expect(logoBody.match(/<line /g)).toHaveLength(3);
  // The standalone logo is ink on a transparent ground — no badge rect.
  expect(logoBody).not.toContain("<rect");
});

test("every public route links the favicon set", async ({ request }) => {
  for (const route of PUBLIC_ROUTES) {
    const html = await htmlOf(request, route.path);
    expect(html, `${route.path} links the SVG favicon`).toContain(
      'rel="icon" type="image/svg+xml" href="/favicon.svg"',
    );
    expect(html, `${route.path} links the PNG fallback`).toContain(
      'rel="alternate icon" type="image/png" sizes="32x32"',
    );
    expect(html, `${route.path} links the touch icon`).toContain(
      'rel="apple-touch-icon" sizes="180x180"',
    );
  }
});

// ----------------------------- sig.social-card/1: one card per page type

test("one social card per page type is generated at build time (1200×630 PNG)", async ({
  request,
}) => {
  for (const type of ["t0", "t1", "t2"]) {
    const res = await request.get(`/social/card-${type}.png`);
    expect(res.status(), `/social/card-${type}.png exists`).toBe(200);
    expect(res.headers()["content-type"]).toContain("image/png");
    expect(pngSize(Buffer.from(await res.body()))).toEqual({ width: 1200, height: 630 });
  }
});

test("every public route references its own page type's card via OG + Twitter meta (SIG-UI-154)", async ({
  request,
}) => {
  for (const route of PUBLIC_ROUTES) {
    const html = await htmlOf(request, route.path);
    const card = `/social/card-${route.type.toLowerCase()}.png`;
    expect(html, `${route.path} (${route.type}) names its card`).toMatch(
      new RegExp(`property="og:image" content="[^"]*${card.replace(/\//g, "\\/")}"`),
    );
    expect(html, `${route.path} carries the share size`).toContain(
      'property="og:image:width" content="1200"',
    );
    expect(html, `${route.path} carries og:title`).toMatch(/property="og:title" content="[^"]+"/);
    expect(html, `${route.path} carries og:description`).toMatch(
      /property="og:description" content="[^"]+"/,
    );
    expect(html, `${route.path} carries og:url`).toContain(
      `property="og:url" content="${ORIGIN}${route.path}"`,
    );
    expect(html, `${route.path} carries og:type`).toContain('property="og:type" content="website"');
    expect(html, `${route.path} carries the card alt`).toMatch(
      /property="og:image:alt" content="[^"]+"/,
    );
    expect(html, `${route.path} declares the summary_large_image card`).toContain(
      'name="twitter:card" content="summary_large_image"',
    );
    expect(html, `${route.path} carries twitter:image`).toMatch(
      new RegExp(`name="twitter:image" content="[^"]*${card.replace(/\//g, "\\/")}"`),
    );
  }
});

test("T3 curation shares no social card (ADR-068 loopback)", async ({ request }) => {
  const route = DISCOVERED_ROUTES.find((r) => r.type === "T3");
  expect(route, "the build emits at least one T3 route").toBeTruthy();
  const html = await htmlOf(request, route!.path);
  expect(html).not.toContain('property="og:image"');
  expect(html).not.toContain('name="twitter:card"');
});

// ------------------------- per-type meta descriptions (SIG-UI-154)

test("meta descriptions are unique and per-type in form", async ({ request }) => {
  // The T0 form names the fixed, script-free page; the T2 form names the
  // interactive surface; the T1 form is copy row MD-01 verbatim.
  const t0 = await htmlOf(request, "/dispute/");
  expect(t0).toMatch(/name="description" content="[^"]*— a fixed, no-JavaScript page/);
  const t2 = await htmlOf(request, "/map/");
  expect(t2).toMatch(/name="description" content="[^"]*— interactive views/);
  const t1 = await htmlOf(request, "/dossier/oklahoma-city/");
  expect(t1).toMatch(/name="description" content="[^"]*— Surveillance Infrastructure Graph \(SIG\)"/);
  // And the og:description a crawler sees is the page's own description.
  const ogMatch = t1.match(/property="og:description" content="([^"]+)"/);
  const metaMatch = t1.match(/name="description" content="([^"]+)"/);
  expect(ogMatch?.[1]).toBe(metaMatch?.[1]);
});

// --------------------------------------------- static-first stays (K14)

test("the brand adds no JavaScript — the glyph is static SVG and T0 stays script-free", async ({
  page,
}) => {
  await page.goto("/dispute/");
  expect(await page.locator("script").count(), "T0 ships no <script>").toBe(0);
  await expect(page.locator("svg.sig-wordmark__glyph")).toHaveCount(1);
});
