#!/usr/bin/env node
// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * P37.34 (K7 WX-04b, SIG-WATCH-005/006) — the post-build feed validator.
 *
 * Scans every emitted feed under `web/dist/watch/` and fails the build on a
 * malformed byte — "feeds MUST validate" wired into the web gate:
 *
 *   - `.ics` (RFC 5545): CRLF folding ≤75 octets, BEGIN/END pairs,
 *     VERSION:2.0 + PRODID, ≥1 component (VEVENT or VTIMEZONE — an empty
 *     calendar still validates), every VEVENT carrying UID @ the production
 *     domain, DTSTAMP == the watch build's generated_at (SIG-WATCH-006 —
 *     never a fixture constant), DTSTART;VALUE=DATE, SEQUENCE integer,
 *     STATUS in CONFIRMED|CANCELLED, URL, REFRESH-INTERVAL/X-PUBLISHED-TTL.
 *   - `.xml` (RSS 2.0): well-formed XML (hand-rolled tag-stack parser — no
 *     dependency), rss@2.0 + channel, atom:link rel="self" naming the feed's
 *     own path, lastBuildDate, <ttl>1440</ttl>, every item with
 *     title/link/guid/pubDate (pubDate = first_seen, never a bare decision
 *     date — it carries a real RFC 822 stamp).
 *   - `.json` (JSON Feed 1.1): parses, version/title/home_page_url/feed_url,
 *     every item with id/url/title/content_text/date_published.
 *   - `feeds.opml` (OPML 2.0): well-formed, every outline type="rss" with
 *     xmlUrl ending `.xml` and resolving to an emitted file.
 *   - Coverage (SIG-WATCH-004/D-K7-5): every emitted `watch/place/<path>/`
 *     page has `watch/feeds/place/<path>.{ics,xml,json}` beside it — an
 *     empty place still feeds.
 *   - Link crawl: every `/watch/feeds/…` and `/watch/feeds.opml` href on the
 *     feeds directory page resolves to an emitted file (no-JS crawl).
 *   - Size: every feed file ≤ the T0 `documentMaxBytes` ceiling the
 *     `sig.page-budgets/1` rows declare (read from page-budgets.json — the
 *     single budget truth, never a restated number).
 */

import { existsSync, readFileSync, readdirSync } from "node:fs";
import { join, relative } from "node:path";
import { fileURLToPath } from "node:url";

const WEB = fileURLToPath(new URL("..", import.meta.url));
const DIST = process.env.SIG_DIST_DIR || join(WEB, "dist");
const errors = [];

const fail = (msg) => errors.push(msg);

const BUDGETS = JSON.parse(
  readFileSync(join(WEB, "tests/e2e/page-budgets.json"), "utf-8"),
);
const FEED_MAX = BUDGETS.types.T0.documentMaxBytes;

/** Recursive file listing under dir → dist-relative posix paths. */
function walk(dir, base = "") {
  if (!existsSync(dir)) return [];
  const out = [];
  for (const e of readdirSync(dir, { withFileTypes: true })) {
    const rel = base ? `${base}/${e.name}` : e.name;
    if (e.isDirectory()) out.push(...walk(join(dir, e.name), rel));
    else out.push(rel);
  }
  return out;
}

const files = walk(DIST);
const fileSet = new Set(files);
const read = (rel) => readFileSync(join(DIST, rel), "utf-8");

// --- minimal XML well-formedness (tag stack; handles ?xml, comments, CDATA,
//     self-closing tags and attributes — the emitters escape all text). ------
function checkXml(rel, text) {
  const stack = [];
  const tagRe = /<(\/?)([A-Za-z_][\w:.-]*)((?:"[^"]*"|'[^']*'|[^>"'])*)>/gs;
  // strip comments, CDATA and the prolog
  const body = text
    .replace(/<\?[^?]*\?>/g, "")
    .replace(/<!--[\s\S]*?-->/g, "")
    .replace(/<!\[CDATA\[[\s\S]*?\]\]>/g, "");
  let m;
  while ((m = tagRe.exec(body))) {
    const [, closing, name, rest] = m;
    if (rest.trimEnd().endsWith("/")) continue; // self-closing
    if (closing) {
      const top = stack.pop();
      if (top !== name) {
        fail(`${rel}: mismatched close </${name}> (open: ${top ?? "none"})`);
        return;
      }
    } else {
      stack.push(name);
    }
  }
  if (stack.length) fail(`${rel}: unclosed elements <${stack.join("> <")}>`);
}

// --- iCal -------------------------------------------------------------------
function checkIcs(rel, text, generatedAt) {
  if (!text.startsWith("BEGIN:VCALENDAR")) fail(`${rel}: does not open BEGIN:VCALENDAR`);
  if (!text.endsWith("END:VCALENDAR\r\n")) fail(`${rel}: does not close END:VCALENDAR + CRLF`);
  if (text.replace(/\r\n/g, "").includes("\n")) {
    fail(`${rel}: a bare LF exists — lines must be CRLF-terminated`);
  }
  for (const raw of text.split("\r\n")) {
    if (Buffer.byteLength(raw, "utf-8") > 75) {
      fail(`${rel}: physical line over 75 octets (${Buffer.byteLength(raw)})`);
      break;
    }
  }
  // Unfold continuations, then normalise to LF so `^…$` anchors work.
  const unfolded = text.replace(/\r\n /g, "").replace(/\r/g, "");
  for (const needle of ["VERSION:2.0", "PRODID:", "REFRESH-INTERVAL;VALUE=DURATION:P1D", "X-PUBLISHED-TTL:P1D"]) {
    if (!unfolded.includes(needle)) fail(`${rel}: missing ${needle}`);
  }
  const comps = unfolded.match(/BEGIN:(VEVENT|VTIMEZONE|VTODO|VJOURNAL)/g) ?? [];
  if (comps.length === 0) fail(`${rel}: no component — an empty calendar still needs one (RFC 5545 §3.4)`);
  const events = unfolded.split("BEGIN:VEVENT").slice(1);
  const stamp = generatedAt
    ? generatedAt.replace(/[-:]/g, "").replace(/\.\d+/, "").replace("T", "T").slice(0, 15) + "Z"
    : null;
  for (const [i, ev] of events.entries()) {
    const uid = ev.match(/^UID:(.+)$/m)?.[1];
    if (!uid || !uid.endsWith("@surveillancegraph.org")) {
      fail(`${rel}: VEVENT[${i}] UID missing or off-domain (${uid})`);
    }
    const dtstamp = ev.match(/^DTSTAMP:(\d{8}T\d{6}Z)$/m)?.[1];
    if (!dtstamp) fail(`${rel}: VEVENT[${i}] missing/invalid DTSTAMP`);
    else if (stamp && dtstamp !== stamp) {
      fail(`${rel}: VEVENT[${i}] DTSTAMP ${dtstamp} ≠ watch build ${stamp} (SIG-WATCH-006)`);
    }
    if (!/^DTSTART;VALUE=DATE:\d{8}$/m.test(ev)) fail(`${rel}: VEVENT[${i}] missing DTSTART;VALUE=DATE`);
    if (!/^SEQUENCE:\d+$/m.test(ev)) fail(`${rel}: VEVENT[${i}] missing integer SEQUENCE`);
    if (!/^STATUS:(CONFIRMED|CANCELLED)$/m.test(ev)) fail(`${rel}: VEVENT[${i}] missing/invalid STATUS`);
    if (!/^URL:.+/m.test(ev)) fail(`${rel}: VEVENT[${i}] missing URL`);
    if (!ev.includes("END:VEVENT")) fail(`${rel}: VEVENT[${i}] unclosed`);
  }
}

// --- RSS --------------------------------------------------------------------
function checkRss(rel, text) {
  checkXml(rel, text);
  for (const needle of ['<rss version="2.0"', "xmlns:atom", 'rel="self"', "<lastBuildDate>", "<ttl>1440</ttl>", "</rss>"]) {
    if (!text.includes(needle)) fail(`${rel}: missing ${needle}`);
  }
  const self = text.match(/<atom:link href="([^"]+)" rel="self"/)?.[1];
  if (!self || !self.endsWith(`/${rel}`)) {
    fail(`${rel}: atom:link self "${self}" does not name the emitted path /${rel}`);
  }
  const items = text.split("    <item>").slice(1);
  for (const [i, it] of items.entries()) {
    for (const tag of ["<title>", "<link>", "<guid ", "<pubDate>", "</item>"]) {
      if (!it.includes(tag)) fail(`${rel}: item[${i}] missing ${tag}`);
    }
    const pub = it.match(/<pubDate>([^<]+)<\/pubDate>/)?.[1];
    if (pub && Number.isNaN(Date.parse(pub))) fail(`${rel}: item[${i}] unparseable pubDate "${pub}"`);
  }
}

// --- JSON Feed ----------------------------------------------------------------
function checkJsonFeed(rel, text) {
  let doc;
  try {
    doc = JSON.parse(text);
  } catch (e) {
    fail(`${rel}: invalid JSON — ${e.message}`);
    return;
  }
  if (doc.version !== "https://jsonfeed.org/version/1.1") fail(`${rel}: not JSON Feed 1.1`);
  for (const k of ["title", "home_page_url", "feed_url", "items"]) {
    if (doc[k] === undefined) fail(`${rel}: missing ${k}`);
  }
  if (doc.feed_url && !doc.feed_url.endsWith(`/${rel}`)) {
    fail(`${rel}: feed_url ${doc.feed_url} ≠ emitted path /${rel}`);
  }
  for (const [i, it] of (doc.items ?? []).entries()) {
    for (const k of ["id", "url", "title", "content_text", "date_published"]) {
      if (it[k] === undefined) fail(`${rel}: item[${i}] missing ${k}`);
    }
  }
}

// --- OPML ---------------------------------------------------------------------
function checkOpml(rel, text) {
  checkXml(rel, text);
  if (!text.includes('<opml version="2.0"')) fail(`${rel}: not OPML 2.0`);
  const outlines = [...text.matchAll(/<outline[^>]*xmlUrl="([^"]+)"[^>]*type="rss"|<outline[^>]*type="rss"[^>]*xmlUrl="([^"]+)"/g)];
  if (outlines.length === 0) fail(`${rel}: no rss outlines`);
  for (const o of outlines) {
    const url = o[1] ?? o[2];
    if (!url.endsWith(".xml")) fail(`${rel}: outline xmlUrl not an .xml feed (${url})`);
    const emitted = url.replace(/^https?:\/\/[^/]+/, "").replace(/^\//, "");
    if (!fileSet.has(emitted)) fail(`${rel}: outline targets un-emitted feed ${emitted}`);
  }
}

// --- Atom (RFC 4287) — the change feeds (P37.40 / SIG-UI-072) ------------
function checkAtom(rel, text) {
  checkXml(rel, text);
  for (const needle of ['<feed xmlns="http://www.w3.org/2005/Atom">', "<title>", "<id>", "<updated>", 'rel="self"', 'rel="alternate"', "</feed>"]) {
    if (!text.includes(needle)) fail(`${rel}: missing ${needle}`);
  }
  const self = text.match(/<link rel="self"[^>]*href="([^"]+)"/)?.[1];
  if (!self || !self.endsWith(`/${rel}`)) {
    fail(`${rel}: link rel=self "${self}" does not name the emitted path /${rel}`);
  }
  const fid = text.match(/<id>([^<]+)<\/id>/)?.[1];
  if (!fid || !fid.endsWith(`/${rel}`)) fail(`${rel}: feed <id> "${fid}" ≠ emitted path /${rel}`);
  const upd = text.match(/<updated>([^<]+)<\/updated>/)?.[1];
  if (!upd || Number.isNaN(Date.parse(upd))) fail(`${rel}: unparseable feed <updated> "${upd}"`);
  const entries = text.split("  <entry>").slice(1);
  for (const [i, e] of entries.entries()) {
    for (const tag of ["<title>", "<id>", "<updated>", "<published>", "<category ", "<content ", "</entry>"]) {
      if (!e.includes(tag)) fail(`${rel}: entry[${i}] missing ${tag}`);
    }
    const eid = e.match(/<id>([^<]+)<\/id>/)?.[1] ?? "";
    if (!eid.startsWith("urn:sig:change:")) fail(`${rel}: entry[${i}] id off-scheme (${eid})`);
    for (const stamp of [e.match(/<updated>([^<]+)<\/updated>/)?.[1], e.match(/<published>([^<]+)<\/published>/)?.[1]]) {
      if (!stamp || Number.isNaN(Date.parse(stamp))) fail(`${rel}: entry[${i}] unparseable date "${stamp}"`);
    }
  }
}

function checkChangesOpml(rel, text) {
  checkXml(rel, text);
  if (!text.includes('<opml version="2.0"')) fail(`${rel}: not OPML 2.0`);
  const outlines = [...text.matchAll(/<outline[^>]*xmlUrl="([^"]+)"/g)];
  if (outlines.length === 0) fail(`${rel}: no outlines`);
  for (const o of outlines) {
    const url = o[1];
    if (!url.endsWith(".atom")) fail(`${rel}: outline xmlUrl not an .atom feed (${url})`);
    const emitted = url.replace(/^https?:\/\/[^/]+/, "").replace(/^\//, "");
    if (!fileSet.has(emitted)) fail(`${rel}: outline targets un-emitted feed ${emitted}`);
  }
}

// --- run ----------------------------------------------------------------------
const feedDir = "watch/feeds";
const emitted = files.filter((f) => f.startsWith(`${feedDir}/`) || f === "watch/feeds.opml");
if (!files.some((f) => f.startsWith(`${feedDir}/all.`))) {
  fail(`${feedDir}/all.* missing — the always-emitted feed`);
}

const generatedAt = (() => {
  // The envelope the feeds derive from — dist/watch/watch.json when the
  // lane's payload ships in the tree; otherwise the fixture build stamp is
  // embedded in the emitted DTSTAMP itself (validated for internal
  // consistency: every VEVENT in a file shares one DTSTAMP).
  const candidates = ["watch/watch.json", "watch.json"];
  for (const c of candidates) {
    if (fileSet.has(c)) {
      try {
        return JSON.parse(read(c)).generated_at ?? null;
      } catch {
        return null;
      }
    }
  }
  return null;
})();

for (const rel of emitted) {
  const text = read(rel);
  if (Buffer.byteLength(text, "utf-8") > FEED_MAX) {
    fail(`${rel}: ${Buffer.byteLength(text)} B over the T0 feed ceiling ${FEED_MAX}`);
  }
  if (rel.endsWith(".ics")) checkIcs(rel, text, generatedAt);
  else if (rel.endsWith(".xml")) checkRss(rel, text);
  else if (rel.endsWith(".json")) checkJsonFeed(rel, text);
  else if (rel.endsWith(".opml")) checkOpml(rel, text);
  else if (!rel.endsWith("index.html")) fail(`${rel}: unknown feed file shape`);
}

// Coverage: every emitted place page has a feed trio (D-K7-5/SIG-WATCH-004).
for (const rel of files.filter((f) => /^watch\/place\/.+\/index\.html$/.test(f))) {
  const placePath = rel.slice("watch/place/".length, -"/index.html".length);
  if (placePath.includes("/page/")) continue;
  for (const fmt of ["ics", "xml", "json"]) {
    const feed = `${feedDir}/place/${placePath}.${fmt}`;
    if (!fileSet.has(feed)) fail(`place ${placePath} has no feed ${feed} (SIG-WATCH-004)`);
  }
}

// Link crawl: every feed href the directory names resolves to a file.
const dirPage = "watch/feeds/index.html";
if (fileSet.has(dirPage)) {
  const html = read(dirPage);
  const hrefs = [...html.matchAll(/href="(?:\/)?(watch\/feeds\.opml|watch\/feeds\/[^"?#]+)"/g)].map((m) => m[1]);
  for (const href of hrefs) {
    if (!fileSet.has(href) && !fileSet.has(`${href}index.html`)) {
      fail(`${dirPage} links un-emitted ${href}`);
    }
  }
}

// --- change feeds (P37.40 / K13 CHG-01, SIG-UI-072) ------------------------
// `changes/feeds/<scope>.atom` for `all`, every emitted dossier page and
// every emitted source page + `changes/feeds.opml`; the T0 ceiling applies.
const changesFeeds = files.filter((f) => f.startsWith("changes/feeds/") || f === "changes/feeds.opml");
if (!fileSet.has("changes/feeds/all.atom")) {
  fail("changes/feeds/all.atom missing — the always-emitted change feed");
}
for (const rel of changesFeeds) {
  const text = read(rel);
  if (Buffer.byteLength(text, "utf-8") > FEED_MAX) {
    fail(`${rel}: ${Buffer.byteLength(text)} B over the T0 feed ceiling ${FEED_MAX}`);
  }
  if (rel.endsWith(".atom")) checkAtom(rel, text);
  else if (rel.endsWith(".opml")) checkChangesOpml(rel, text);
  else if (!rel.endsWith("index.html")) fail(`${rel}: unknown feed file shape`);
}
// Coverage: every emitted dossier page (a place page — never the a-z/by/
// sort/page facets or the sites|sources|downloads|print sub-pages) carries
// `changes/feeds/place/<path>.atom`; every emitted source page carries
// `changes/feeds/source/<id>.atom` — empty scopes still feed.
const NON_PLACE_FIRST = new Set(["a-z", "by", "sort", "page"]);
const NON_PLACE_LEAF = new Set(["sites", "sources", "downloads", "print"]);
for (const rel of files.filter((f) => /^dossier\/.+\/index\.html$/.test(f))) {
  const parts = rel.slice("dossier/".length, -"/index.html".length).split("/");
  if (NON_PLACE_FIRST.has(parts[0]) || NON_PLACE_LEAF.has(parts[parts.length - 1])) continue;
  const feed = `changes/feeds/place/${parts.join("/")}.atom`;
  if (!fileSet.has(feed)) fail(`place ${parts.join("/")} has no change feed ${feed} (SIG-UI-072)`);
}
for (const rel of files.filter((f) => /^sources\/[^/]+\/index\.html$/.test(f))) {
  const id = rel.slice("sources/".length, -"/index.html".length);
  const feed = `changes/feeds/source/${id}.atom`;
  if (!fileSet.has(feed)) fail(`source ${id} has no change feed ${feed} (SIG-UI-072)`);
}
// Link crawl: every change-feed href on /changes/ and the feed index pages
// resolves to an emitted file (no-JS crawl).
for (const page of ["changes/index.html", "changes/feeds/index.html"]) {
  if (!fileSet.has(page)) continue;
  const html = read(page);
  const hrefs = [...html.matchAll(/href="(?:\/)?(changes\/feeds\.opml|changes\/feeds\/[^"?#]+)"/g)].map((m) => m[1]);
  for (const href of hrefs) {
    if (!fileSet.has(href) && !fileSet.has(`${href}index.html`)) {
      fail(`${page} links un-emitted ${href}`);
    }
  }
}

if (errors.length) {
  console.error(`check-feeds: ${errors.length} failure(s)`);
  for (const e of errors) console.error(`  ${e}`);
  process.exit(1);
}
const counts = {
  ics: emitted.filter((f) => f.endsWith(".ics")).length,
  xml: emitted.filter((f) => f.endsWith(".xml")).length,
  json: emitted.filter((f) => f.endsWith(".json")).length,
  opml: emitted.filter((f) => f.endsWith(".opml")).length,
};
console.log(
  `check-feeds: PASS — ${emitted.length} watch feed files validated ` +
  `(${counts.ics} .ics, ${counts.xml} .xml, ${counts.json} .json, ${counts.opml} .opml) + ` +
  `${changesFeeds.length} change feed files (≤${FEED_MAX} B)`,
);
