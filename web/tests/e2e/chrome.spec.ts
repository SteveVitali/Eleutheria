// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// P34.13 — chrome, format and accessibility quick fixes (QW-11, QW-13, K14
// NEW-7/NEW-8, K12b NEW-11). Runs against the BUILT static site (astro preview):
// branded error pages, the favicon, the canonical-only sitemap, unique
// titles/meta descriptions, the /terms forwarder with its N-7 notice, unique
// landmark names, the print main landmark, no glued words at inline-element
// boundaries, and no ungrouped 5+-digit number in public text.
import { test, expect } from "@playwright/test";
import {
  ALL_PAGES,
  CHROME_PAGES,
  FRESHNESS_SORT_PAGES,
  JURISDICTION_DOSSIER_PAGES,
  DOSSIER_PRINT,
} from "./pages";

// The public surface under test: the shell pages, the jurisdiction dossiers,
// the one real sort route, the chrome pages, and every dossier's print view.
// Internal/withdrawn routes (/visual-language/, /contribution-back/, /curate/**)
// are NOT public text and stay out of the copy checks.
const WITHDRAWN = ["/visual-language/", "/contribution-back/"];
const PUBLIC_PAGES = [
  ...ALL_PAGES.filter((p) => !WITHDRAWN.includes(p)),
  ...JURISDICTION_DOSSIER_PAGES,
  ...FRESHNESS_SORT_PAGES,
  ...CHROME_PAGES,
  DOSSIER_PRINT,
  "/dossier/paris-alpr/print/",
  "/dossier/brussels-alpr/print/",
] as const;

const ORIGIN = "https://surveillancegraph.org";

async function htmlOf(request: import("@playwright/test").APIRequestContext, path: string) {
  const res = await request.get(path);
  expect(res.status(), `${path} must resolve`).toBe(200);
  return res.text();
}

// ---------------------------------------------------------------- QW-11: chrome

test("branded 404/403/410 pages ship the shell, a home link and noindex (QW-11)", async ({
  request,
}) => {
  const cases = [
    { path: "/404.html", h1: "Page not found" },
    { path: "/403/", h1: "Access refused" },
    { path: "/410/", h1: "Page removed" },
  ];
  for (const { path, h1 } of cases) {
    const html = await htmlOf(request, path);
    expect(html, `${path} carries the SIG wordmark`).toContain("sig-wordmark");
    expect(html, `${path} carries its h1`).toContain(`<h1>${h1}</h1>`);
    expect(html, `${path} is noindex`).toContain('name="robots" content="noindex"');
    expect(html, `${path} links home`).toContain('href="/"');
  }
  // The flat error-page copies nginx error_page will map onto (P34.40's roll).
  for (const flat of ["/403.html", "/410.html"]) {
    const res = await request.get(flat);
    expect(res.status(), `${flat} must be emitted for the error_page mapping`).toBe(200);
  }
  // The 410 body is notice string N-6 verbatim (B-2 notice allowance).
  const gone = await htmlOf(request, "/410/");
  expect(gone).toContain("This page has been removed while a correction is made.");
});

test("favicon is emitted and linked on every public page (QW-11)", async ({ request }) => {
  const icon = await request.get("/favicon.svg");
  expect(icon.status()).toBe(200);
  for (const path of PUBLIC_PAGES) {
    const html = await htmlOf(request, path);
    expect(html, `${path} links the favicon`).toContain('rel="icon"');
  }
});

test("every public page has a unique <title> and meta description (QW-11)", async ({
  request,
}) => {
  const titles = new Map<string, string>();
  const descriptions = new Map<string, string>();
  for (const path of PUBLIC_PAGES) {
    const html = await htmlOf(request, path);
    const title = html.match(/<title>([^<]*)<\/title>/)?.[1] ?? "";
    const desc = html.match(/<meta name="description" content="([^"]*)"/)?.[1] ?? "";
    expect(title, `${path} has a <title>`).not.toBe("");
    expect(desc, `${path} has a meta description`).not.toBe("");
    expect(titles.has(title), `duplicate <title> ${title} on ${path} and ${titles.get(title)}`).toBe(
      false,
    );
    expect(
      descriptions.has(desc),
      `duplicate meta description on ${path} and ${descriptions.get(desc)}`,
    ).toBe(false);
    titles.set(title, path);
    descriptions.set(desc, path);
  }
});

test("sitemap lists canonical-origin URLs only, all resolvable (QW-11)", async ({ request }) => {
  const res = await request.get("/sitemap.xml");
  expect(res.status()).toBe(200);
  const xml = await res.text();
  const locs = [...xml.matchAll(/<loc>([^<]+)<\/loc>/g)].map((m) => m[1]);
  expect(locs.length, "sitemap lists the public pages").toBeGreaterThan(10);
  const routes = new Set<string>(
    PUBLIC_PAGES.filter(
      (p) => !p.includes("/print/") && !(CHROME_PAGES as readonly string[]).includes(p),
    ),
  );
  for (const loc of locs) {
    expect(loc.startsWith(`${ORIGIN}/`), `non-canonical URL in sitemap: ${loc}`).toBe(true);
    const path = new URL(loc).pathname;
    expect(routes.has(path), `sitemap lists a non-public or non-canonical route: ${loc}`).toBe(true);
  }
  // Error pages, the /terms forwarder, print views and internal routes are never
  // canonical content — they must not appear.
  for (const banned of ["/404", "/403", "/410", "/terms/", "/print/", "/curate/", "/visual-language/"]) {
    expect(xml.includes(banned), `sitemap must not contain ${banned}`).toBe(false);
  }
  // Every listed URL resolves as its own canonical.
  for (const loc of locs) {
    const path = new URL(loc).pathname;
    const html = await htmlOf(request, path);
    expect(html, `${path} canonicalises to itself`).toContain(`rel="canonical" href="${loc}"`);
  }
});

test("robots.txt points at the sitemap (QW-11)", async ({ request }) => {
  const res = await request.get("/robots.txt");
  expect(res.status()).toBe(200);
  expect(await res.text()).toContain(`Sitemap: ${ORIGIN}/sitemap.xml`);
});

test("/terms forwards to the API terms with the N-7 notice beside it (QW-11)", async ({
  request,
}) => {
  const html = await htmlOf(request, "/terms/");
  // N-7 verbatim — the API's terms response is known-wrong until P34.46.
  expect(html).toContain(
    "The API's dossier and terms responses are known to be wrong and are being corrected.",
  );
  const href = html.match(/<a[^>]*href="([^"]*\/terms)"[^>]*>Open the API terms<\/a>/)?.[1];
  expect(href, "/terms links to the API terms endpoint").toBeTruthy();
  expect(href).toMatch(/^https:\/\//);
  expect(html, "/terms is a forwarder, not content — noindex").toContain(
    'name="robots" content="noindex"',
  );
});

// ---------------------------------------------------- QW-13: names + landmarks

test("the wordmark's accessible name contains its visible text (label-in-name)", async ({
  request,
}) => {
  const html = await htmlOf(request, "/");
  const label = html.match(/<a class="sig-wordmark"[^>]*aria-label="([^"]+)"/)?.[1] ?? "";
  expect(label).toContain("SIG");
  expect(label).toContain("Surveillance Infrastructure Graph");
});

test("landmark names are unique per page, incl. the dossier's own how_we_know_this section (QW-13)", async ({
  page,
}) => {
  // On a dossier both the §39.2 section and the shell module are "How we know
  // this" landmarks — before the fix they collided (RI-49).
  await page.goto("/dossier/oklahoma-city/");
  const names = await page.evaluate(() => {
    const resolve = (el: Element) => {
      const by = el.getAttribute("aria-labelledby");
      if (by) {
        return by
          .split(/\s+/)
          .map((id) => document.getElementById(id)?.textContent?.trim() ?? "")
          .join(" ")
          .trim();
      }
      return (el.getAttribute("aria-label") ?? "").trim();
    };
    const regions = [...document.querySelectorAll('section[aria-labelledby], section[aria-label], [role="region"]')];
    return regions.map((el) => resolve(el));
  });
  const dup = names.filter((n, i) => n && names.indexOf(n) !== i);
  expect(dup, `duplicate landmark names: ${dup}`).toEqual([]);
});

test("the standalone print dossier carries exactly one main landmark (QW-13)", async ({
  page,
}) => {
  await page.goto(DOSSIER_PRINT);
  await expect(page.locator("main")).toHaveCount(1);
  // … and every shell page keeps its own single main.
  await page.goto("/");
  await expect(page.locator("main#main")).toHaveCount(1);
});

// --------------------------------------------- K14 NEW-7 / NEW-8: text quality

const INLINE = "(?:a|strong|em|span|code|time|b|i|mark|abbr|small|sup|sub)";
// An inline element's close tag followed directly by a word character or an
// opening bracket — "…concern?Dispute" / "…footnote(SIG-UI-023)".
const RIGHT_GLUE = new RegExp(`</${INLINE}>[A-Za-z0-9(\\[]`, "g");
// A word/punct character immediately before an inline open tag — "…form<code>".
const LEFT_GLUE = new RegExp(`[A-Za-z0-9.?!:;,)\\]—–·/]<${INLINE}\\b`, "g");
// Adjacent inline elements whose second element's text starts with a word
// character — "…0.50</span><span>Depends".
const ADJ_GLUE = new RegExp(`</${INLINE}><${INLINE}\\b[^>]*>`, "g");
const OPEN_TAGS = new RegExp(`^(?:<${INLINE}\\b[^>]*>)*`);

// A separator at a boundary — whitespace or a punctuation dash/dot — is not a
// glue (" · " separator spans, "x — <em>note</em>" inlines that open " — ").
const isSep = (c: string | undefined) => !c || /\s/.test(c) || "—–·".includes(c);

// The element just closed is decorative (aria-hidden) or a glyph marker — the
// empty `__mark` spans and `≠` contested glyphs that pair with an sr-only or
// aria-label name. Its boundary is not a text glue.
function closesDecorative(body: string, idx: number): boolean {
  const tail = body.slice(Math.max(0, idx - 220), idx);
  const t = tail.match(/<([a-zA-Z]+)\b([^<>]*)>([^<>]*)$/);
  return !!t && /aria-hidden="true"/.test(t[2]);
}

function glueHits(html: string): string[] {
  const body = html.replace(/<(script|style)[^>]*>[\s\S]*?<\/\1>/g, "");
  const hits: string[] = [];
  for (const m of body.matchAll(RIGHT_GLUE)) {
    // The element's own text may end with the separator (" · </span>…"), or be
    // a decorative aria-hidden glyph/mark contributing no text at all.
    if (!isSep(body[m.index! - 1]) && !closesDecorative(body, m.index!))
      hits.push(body.slice(m.index, m.index + 60));
  }
  for (const m of body.matchAll(LEFT_GLUE)) {
    const inner = body
      .slice(m.index! + m[0].length)
      .replace(/^[^>]*>/, "") // the rest of the matched open tag
      .replace(OPEN_TAGS, "");
    if (!isSep(inner[0])) {
      hits.push(body.slice(m.index! - 40, m.index! + 40));
    }
  }
  for (const m of body.matchAll(ADJ_GLUE)) {
    // Check both edges: the first element's text may end with a space or be a
    // decorative glyph, the second's may start with one — any of those makes
    // the boundary visible (or silent, for aria-hidden marks).
    const inner = body.slice(m.index! + m[0].length).replace(OPEN_TAGS, "");
    if (
      !isSep(body[m.index! - 1]) &&
      !closesDecorative(body, m.index!) &&
      !isSep(inner[0])
    ) {
      hits.push(body.slice(m.index! - 40, m.index! + 40));
    }
  }
  return hits;
}

test("no words glued at inline-element boundaries in built text (K14 NEW-7)", async ({
  request,
}) => {
  for (const path of PUBLIC_PAGES) {
    const html = await htmlOf(request, path);
    const hits = glueHits(html);
    expect(hits, `${path} has glued inline-boundary text: ${hits.slice(0, 3)}`).toEqual([]);
  }
});

test("no ungrouped 5+-digit number in public text — identifiers excepted (K14 NEW-8)", async ({
  page,
}) => {
  for (const path of PUBLIC_PAGES) {
    await page.goto(path);
    const text = await page.evaluate(() => {
      const clone = document.body.cloneNode(true) as HTMLElement;
      // Identifiers are exact values, never human-formatted: code literals,
      // dates (ISO runs are ≤4 digits anyway) and permalink/ID anchors.
      clone
        .querySelectorAll('code, time, a.sig-cite__permalink, a.sig-print-footer__permalink, [data-testid="permalink"], script, style')
        .forEach((el) => el.remove());
      // Per-text-node extraction — innerText concatenates adjacent cells
      // ("2026-06-01"+"2026-08-01" → a phantom 5+ run) while a value that
      // really is ungrouped lives inside one text node.
      const parts: string[] = [];
      const walker = document.createTreeWalker(clone, NodeFilter.SHOW_TEXT);
      let node = walker.nextNode();
      while (node) {
        parts.push(node.textContent ?? "");
        node = walker.nextNode();
      }
      return parts.join(" ");
    });
    const hits = [...text.matchAll(/\d{5,}/g)].map((m) => m[0]);
    expect(hits, `${path} shows ungrouped 5+-digit runs: ${hits.slice(0, 5)}`).toEqual([]);
  }
});
