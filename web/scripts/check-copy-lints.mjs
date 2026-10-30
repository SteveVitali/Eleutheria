// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * P36.24 (K13 UXK14-5 / K14 §3.6 CP-4·CP-8 + DR-K14-10/11/19 + DR-C6-28;
 * §56.11 SIG-UI-063 owner + SIG-UI-144/153 owner, SIG-UI-053/062 cited) —
 * the copy lints in CI.
 *
 * Corpus: `dist/page-types.json` — the page-type registry's discovered-route
 * manifest (P35.50/UXK0-1), so no built route escapes the sweep. Each rule
 * runs over a route's `<main>` + `<footer>`; the rules report, they do not
 * fix — fixing flagged copy is each surface's own row.
 *
 * Report-then-enforce: `scripts/copy-lint-enforce.json`
 * (`sig.copy-lint-enforce/1`) maps a registry pattern (or an exact route
 * path) to "enforce"; every unlisted route runs the default "report" mode —
 * findings print but do not fail. A surface's ticket flips its own routes.
 *
 * Rules (finding ids in brackets):
 *
 *   ids        [uuid|snake-case|enum|req-id] — DR-C6-28/CP-4: no UUID,
 *              snake_case key, raw enum or requirement id in prose. Exempt:
 *              <code>/<pre> content, elements marked `data-technical-details`
 *              or `data-identifiers` (SIG-UI-053's Identifiers/Technical
 *              details blocks) and `.sig-spec-refs` disclosures (SIG-UI-141).
 *   repeated   [repeated-sentence] — SIG-UI-144: no sentence of 8+ words may
 *              appear twice in main + footer. (The "not a census" half is a
 *              figure-component contract, not a text sweep — the tagline and
 *              <Figure> labels carry it.)
 *   chrome     [chrome-words] — DR-K14-11/SIG-UI-145: footer words visible by
 *              default (details collapsed, nav labels excluded) ≤ 40.
 *   joined     [joined-punct|joined-boundary] — SIG-UI-153/DR-K14-19: no
 *              words joined at element boundaries — a sentence-punctuation
 *              join in extracted text, or an inline element flush against a
 *              word character in the built HTML.
 *   digits     [ungrouped-digits] — SIG-UI-153/DR-K14-19: no ungrouped run of
 *              5+ digits outside code, <time>, ids and dates.
 *   unknown    [bare-unknown] — a bare "unknown" in visible copy; typed
 *              absences name the kind instead.
 *   sites      [records-vs-sites] — SIG-UI-063: "camera site(s)"/"listed
 *              cameras" may appear only inside a `data-sig-count="dedup"`
 *              element (the L3 CONF-07b interval) — and such an element MUST
 *              name the site word; elsewhere say "records". A plural
 *              "cameras" that is neither phrase is the same finding.
 *   lifecycle  [candidate-vs-provisional] — SIG-UI-062: "provisional
 *              record(s)" collapses the epistemic label onto the lifecycle
 *              row; "candidate <value|estimate|count|figure|number|label>"
 *              does the reverse.
 *   vocabulary [vocabulary] — the lexicon's multi-word `not` phrasings
 *              (e.g. "observation-level record", "as of world") in prose.
 *   readability — DR-C6-28/CP-8, advisory only: per-page sentence means and
 *              maxima print in the report; they never fail.
 *
 * `/glossary/` is the definitional surface: the sites/lifecycle/vocabulary
 * legs exempt it, the same carve-out check-lexicon gives the enum leg.
 *
 * Usage: node scripts/check-copy-lints.mjs [--dist DIR] [--manifest FILE]
 *        [--enforce FILE]
 * Exit: 0 pass (report findings print) · 1 a finding on an enforced route ·
 * 2 usage/input error · 3 vacuous (no route scanned — SIG-ENG-042).
 */

import { existsSync, readFileSync } from "node:fs";
import { join, relative, sep } from "node:path";
import { fileURLToPath } from "node:url";

const WEB = fileURLToPath(new URL("..", import.meta.url));
const LEXICON = JSON.parse(
  readFileSync(join(WEB, "src", "lib", "lexicon.json"), "utf8"),
);

// --- arguments ---------------------------------------------------------------

function parseArgs(argv) {
  const args = { dist: join(WEB, "dist"), manifest: null, enforce: join(WEB, "scripts", "copy-lint-enforce.json") };
  for (let i = 0; i < argv.length; i++) {
    if (argv[i] === "--dist") args.dist = argv[++i];
    else if (argv[i] === "--manifest") args.manifest = argv[++i];
    else if (argv[i] === "--enforce") args.enforce = argv[++i];
    else if (argv[i] === "--help" || argv[i] === "-h") return { help: true };
    else return { error: `unknown argument ${argv[i]}` };
  }
  if (!args.manifest) args.manifest = join(args.dist, "page-types.json");
  return args;
}

// --- text extraction -----------------------------------------------------------

const ENTITY_MAP = {
  amp: "&", lt: "<", gt: ">", quot: '"', apos: "'", nbsp: " ", middot: "·",
  ndash: "–", mdash: "—", hellip: "…", rsquo: "’", lsquo: "‘",
  rdquo: "”", ldquo: "“", deg: "°", times: "×", minus: "−",
};

export function decodeEntities(text) {
  return text.replace(/&(#\d+|#x[0-9a-fA-F]+|[a-zA-Z]+);/g, (m, e) => {
    if (e[0] === "#") {
      const n = e[1] === "x" || e[1] === "X" ? parseInt(e.slice(2), 16) : parseInt(e.slice(1), 10);
      return Number.isFinite(n) ? String.fromCodePoint(n) : m;
    }
    return ENTITY_MAP[e] ?? m;
  });
}

/** Strip the contents of the named tags, then a marked-element class, from a
 *  fragment. Non-nested same-tag assumption — the sweep is over flat built
 *  HTML where the stripped containers never nest their own tag. */
function stripTagContents(html, tags) {
  for (const tag of tags) {
    html = html.replace(
      new RegExp(`<${tag}\\b[^>]*>[\\s\\S]*?<\\/${tag}>`, "gi"),
      " ",
    );
  }
  return html;
}

/** Remove elements carrying a marker attribute (and their subtree). */
function stripMarkedElements(html, attrRe) {
  return html.replace(
    new RegExp(
      `<([a-zA-Z][\\w-]*)[^>]*${attrRe.source}[^>]*>[\\s\\S]*?<\\/\\1>`,
      "gi",
    ),
    " ",
  );
}

/** The route's measured fragments: main + footer plus the chrome slice. */
function fragments(html) {
  const main = html.match(/<main[\s>][\s\S]*?<\/main>/i)?.[0] ?? "";
  const footer = html.match(/<footer[\s>][\s\S]*?<\/footer>/i)?.[0] ?? "";
  return { main, footer, both: `${main}\n${footer}` };
}

/** Visible text of a fragment for the prose legs. */
function visibleText(html, { forIds = false } = {}) {
  let t = stripTagContents(html, ["script", "style", "code", "pre", "template", "noscript"]);
  if (forIds) {
    t = stripMarkedElements(t, /data-(?:technical-details|identifiers)\b/);
    t = t.replace(/<details\b[^>]*class="[^"]*sig-spec-refs[^"]*"[^>]*>[\s\S]*?<\/details>/gi, " ");
  }
  return decodeEntities(t.replace(/<[^>]+>/g, " ")).replace(/\s+/g, " ").trim();
}

/** Chrome words visible by default: footer minus collapsed <details>, nav
 *  labels and code/pre/script/style (DR-K14-11's count shape). */
function chromeWords(footerHtml) {
  let t = stripTagContents(footerHtml, ["details", "nav", "script", "style", "code", "pre"]);
  t = decodeEntities(t.replace(/<[^>]+>/g, " "));
  return t.split(/\s+/).filter((w) => /[\p{L}\p{N}]/u.test(w)).length;
}

/** Sentences of ≥ `min` words in a text — for the repeated-sentence leg and
 *  the readability report. */
function sentencesOf(text, min = 8) {
  const parts = text.split(/(?<=[.?!…])\s+/u);
  const out = [];
  for (const p of parts) {
    const words = p.split(/\s+/).filter((w) => /[\p{L}\p{N}]/u.test(w));
    if (words.length >= min) out.push({ text: p.trim(), words: words.length });
  }
  return out;
}

// --- rules ---------------------------------------------------------------------

const RE_UUID = /\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b/;
const RE_SNAKE = /\b[a-z][a-z0-9]*(?:_[a-z0-9]+)+\b/;
const RE_ENUM = /\b[A-Z][A-Z0-9]*_[A-Z0-9_]+\b/;
const RE_REQID = /\b(?:SIG-[A-Z]+-\d+|ADR-\d+|HG-\d+)\b/;
const RE_JOINED_PUNCT = /[\p{Ll}][.?!)\u2026][\p{Lu}][\p{Ll}]/u;
const RE_DIGITS = /\b\d{5,}\b/;
const RE_UNKNOWN = /\bunknown\b/i;
const RE_SITE = /\b(?:camera\s+sites?|listed\s+cameras?)\b/i;
const RE_SITE_G = new RegExp(RE_SITE.source, "gi");
const RE_CAMERAS = /\bcameras\b/i;
const RE_PROV_RECORD = /\bprovisional\s+records?\b/i;
const RE_CAND_EPI = /\bcandidate\s+(?:value|estimate|count|figure|number|label)\b/i;

// Inline elements that may abut prose; a word character or sentence
// punctuation flush against one is a join (K14 NEW-7's `concern?<a` class).
// Block tags never count — text extraction inserts the space a block
// boundary implies; `(`/`"`/`—` open a group legitimately.
const INLINE_TAGS = "a|abbr|b|bdi|bdo|cite|em|i|mark|q|s|small|span|strong|sub|sup|time|u|var";
const RE_JOIN_OPEN = new RegExp(`[\\p{L}\\p{N}.?!,;:\\u2026]<(?:${INLINE_TAGS})\\b[^>]*>`, "u");
const RE_JOIN_CLOSE = new RegExp(`<\\/(?:${INLINE_TAGS})>[\\p{L}\\p{N}]`, "u");
const RE_JOIN_PAIR = new RegExp(`<\\/(?:${INLINE_TAGS})>(?:<!--[\\s\\S]*?-->)?<(?:${INLINE_TAGS})\\b`, "u");

const DEDUP_OPEN = /<([a-zA-Z][\w-]*)[^>]*data-sig-count="dedup"[^>]*>/g;

/** The multi-word `not` phrasings the lexicon bans from prose. */
const BANNED_PHRASES = (LEXICON.vocabulary ?? [])
  .flatMap((v) => v.not ?? [])
  .filter((p) => p.trim().split(/\s+/).length >= 2)
  .map((p) => ({ phrase: p, re: new RegExp(`\\b${p.replace(/[.*+?^${}()|[\]\\]/g, "\\$&").replace(/\s+/g, "\\s+")}\\b`, "i") }));

/**
 * Lint one built page. `frag` is the main+footer HTML, `path` the route path
 * for the glossary exemption. Returns [{rule, detail}].
 */
export function lintPage(html, { path = "" } = {}) {
  const frag = fragments(html);
  const findings = [];
  const glossary = path === "/glossary/" || path.startsWith("/glossary");
  const add = (rule, detail) => findings.push({ rule, detail });

  const idsText = visibleText(frag.both, { forIds: true });
  const prose = visibleText(frag.both);
  const digitsText = visibleText(stripTagContents(frag.both, ["time"]));

  // DR-C6-28 / CP-4 — ids in prose.
  for (const [rule, re, label] of [
    ["uuid", RE_UUID, "a UUID"],
    ["snake-case", RE_SNAKE, "a snake_case key"],
    ["enum", RE_ENUM, "a raw enum token"],
    ["req-id", RE_REQID, "a requirement id"],
  ]) {
    const m = idsText.match(re);
    if (m) add(rule, `${label} "${m[0]}" in prose — ids live in Identifiers/Technical details or Spec references (DR-C6-28)`);
  }

  // SIG-UI-144 — repeated sentences of 8+ words in main + footer.
  const seen = new Map();
  for (const s of sentencesOf(prose)) {
    const key = s.text.toLowerCase();
    seen.set(key, (seen.get(key) ?? 0) + 1);
  }
  for (const [key, n] of seen) {
    if (n > 1) add("repeated-sentence", `sentence ×${n}: "${key.slice(0, 90)}…" (SIG-UI-144)`);
  }

  // DR-K14-11 — shared chrome words visible by default.
  if (frag.footer) {
    const n = chromeWords(frag.footer);
    if (n > 40) add("chrome-words", `visible-by-default chrome ${n} words > 40 (SIG-UI-145)`);
  }

  // SIG-UI-153 — joined words.
  const jm = prose.match(RE_JOINED_PUNCT);
  if (jm) add("joined-punct", `sentence join "${jm[0]}" in visible text (DR-K14-19)`);
  // The boundary legs scan markup, not script/style/template payloads.
  const joinScan = stripTagContents(frag.both, ["script", "style", "template"]);
  const jo = joinScan.match(RE_JOIN_OPEN);
  if (jo) add("joined-boundary", `inline element opens flush against a word: "${jo[0].slice(0, 60)}" (DR-K14-19)`);
  const jc = joinScan.match(RE_JOIN_CLOSE);
  if (jc) add("joined-boundary", `inline element closes flush against a word: "${jc[0].slice(0, 60)}" (DR-K14-19)`);
  const jp = joinScan.match(RE_JOIN_PAIR);
  if (jp) add("joined-boundary", `inline elements abut without a space: "${jp[0].slice(0, 60)}" (DR-K14-19)`);

  // SIG-UI-153 — ungrouped digits outside code/time/ids/dates.
  const dm = digitsText.match(RE_DIGITS);
  if (dm) add("ungrouped-digits", `ungrouped ${dm[0].length}-digit run "${dm[0]}" — group as ${Number(dm[0]).toLocaleString("en-US")} (DR-K14-19)`);

  // bare "unknown" — a typed absence names the kind instead.
  const um = prose.match(RE_UNKNOWN);
  if (um) add("bare-unknown", `bare "unknown" in copy — use a typed absence (K13 vocabulary)`);

  if (!glossary) {
    // SIG-UI-063 — records versus camera sites.
    let masked = frag.both;
    let dedupSeen = 0;
    for (const m of frag.both.matchAll(DEDUP_OPEN)) {
      const tag = m[1];
      const close = frag.both.indexOf(`</${tag}>`, m.index + m[0].length);
      const inner = close < 0 ? "" : frag.both.slice(m.index + m[0].length, close);
      dedupSeen++;
      const innerText = visibleText(inner);
      if (!RE_SITE.test(innerText)) {
        add("records-vs-sites", `data-sig-count="dedup" element never names "camera sites"/"listed cameras" — 'records' used where the site word belongs (SIG-UI-063)`);
      }
      masked = masked.replace(m[0] + inner + (close < 0 ? "" : `</${tag}>`), " ");
    }
    const maskedText = visibleText(masked);
    const siteMatch = maskedText.match(RE_SITE);
    if (siteMatch) {
      add("records-vs-sites", `"${siteMatch[0]}" outside a data-sig-count="dedup" interval — observation-level rows are "records" (SIG-UI-063)`);
    }
    const camMatch = maskedText.replace(RE_SITE_G, " ").match(RE_CAMERAS);
    if (camMatch) {
      add("records-vs-sites", `bare plural "cameras" — the count word is "records" (SIG-UI-063)`);
    }

    // SIG-UI-062 — Candidate (lifecycle) versus Provisional (epistemic).
    const pr = prose.match(RE_PROV_RECORD);
    if (pr) add("candidate-vs-provisional", `"${pr[0]}" — a record's lifecycle word is "Candidate"; "Provisional" is the epistemic label (SIG-UI-062)`);
    const ce = prose.match(RE_CAND_EPI);
    if (ce) add("candidate-vs-provisional", `"${ce[0]}" — an epistemic value is "Provisional"; "Candidate" is the lifecycle state (SIG-UI-062)`);

    // the lexicon's multi-word banned phrasings.
    for (const { phrase, re } of BANNED_PHRASES) {
      const b = prose.match(re);
      if (b) add("vocabulary", `banned phrasing "${b[0]}" — the lexicon says use "${(LEXICON.vocabulary ?? []).find((v) => (v.not ?? []).includes(phrase))?.use}" (K13 vocabulary)`);
    }
  }

  // DR-C6-28/CP-8 — readability, advisory only.
  const sents = sentencesOf(prose, 1);
  const totalWords = sents.reduce((a, s) => a + s.words, 0);
  const longest = sents.reduce((a, s) => Math.max(a, s.words), 0);
  const readability = {
    sentences: sents.length,
    words: totalWords,
    mean: sents.length ? Math.round((totalWords / sents.length) * 10) / 10 : 0,
    longest,
  };

  return { findings, readability };
}

// --- enforce registry ----------------------------------------------------------

const RULE_IDS = new Set([
  "uuid", "snake-case", "enum", "req-id", "repeated-sentence", "chrome-words",
  "joined-punct", "joined-boundary", "ungrouped-digits", "bare-unknown",
  "records-vs-sites", "candidate-vs-provisional", "vocabulary",
]);

/** Resolve a route's mode + per-rule exemptions from sig.copy-lint-enforce/1. */
export function enforceFor(registry, route) {
  const routes = registry?.routes ?? {};
  const entry = routes[route.pattern] ?? routes[route.path];
  if (entry === "enforce") return { mode: "enforce", except: new Set() };
  if (entry && typeof entry === "object") {
    const mode = entry.mode === "enforce" ? "enforce" : "report";
    const except = new Set(entry.except ?? []);
    for (const r of except) {
      if (!RULE_IDS.has(r)) throw new Error(`copy-lint-enforce: unknown rule id "${r}" for ${route.path}`);
    }
    return { mode, except };
  }
  return { mode: registry?.defaultMode === "enforce" ? "enforce" : "report", except: new Set() };
}

// --- main ------------------------------------------------------------------------

export function run({ dist, manifestPath, enforcePath }) {
  if (!existsSync(manifestPath)) {
    return {
      code: 2,
      lines: [`check-copy-lints: ${relative(WEB, manifestPath)} missing — run the build first; the lint reads the page-type manifest so no route escapes the corpus`],
    };
  }
  let manifest;
  try {
    manifest = JSON.parse(readFileSync(manifestPath, "utf8"));
  } catch (e) {
    return { code: 2, lines: [`check-copy-lints: manifest parse failed: ${e.message}`] };
  }
  if (manifest.schema !== "sig.page-types-manifest/1" || !Array.isArray(manifest.routes)) {
    return { code: 2, lines: [`check-copy-lints: ${relative(WEB, manifestPath)} is not sig.page-types-manifest/1`] };
  }
  let registry = null;
  if (existsSync(enforcePath)) {
    try {
      registry = JSON.parse(readFileSync(enforcePath, "utf8"));
    } catch (e) {
      return { code: 2, lines: [`check-copy-lints: enforce registry parse failed: ${e.message}`] };
    }
  } else {
    return { code: 2, lines: [`check-copy-lints: ${relative(WEB, enforcePath)} missing — the report→enforce map is committed input`] };
  }

  const lines = [];
  let scanned = 0;
  let skipped = 0;
  let reportFindings = 0;
  let enforcedFindings = 0;
  const advisory = [];

  for (const route of manifest.routes) {
    const file = join(dist, ...route.file.split("/"));
    if (!existsSync(file)) {
      return { code: 2, lines: [`check-copy-lints: ${route.file} named by the manifest is absent from ${relative(WEB, dist)} — rebuild`] };
    }
    const html = readFileSync(file, "utf8");
    if (!/<main[\s>]/i.test(html)) {
      skipped++;
      continue;
    }
    scanned++;
    const { findings, readability } = lintPage(html, { path: route.path });
    const { mode, except } = enforceFor(registry, route);
    for (const f of findings) {
      if (except.has(f.rule)) {
        lines.push(`  excepted [${f.rule}] ${route.path} — ${f.detail}`);
        continue;
      }
      if (mode === "enforce") {
        enforcedFindings++;
        lines.push(`  FAIL      [${f.rule}] ${route.path} — ${f.detail}`);
      } else {
        reportFindings++;
        lines.push(`  report    [${f.rule}] ${route.path} — ${f.detail}`);
      }
    }
    if (readability.sentences > 0 && readability.mean > 22) {
      advisory.push(`  readability ${route.path}: mean ${readability.mean} words/sentence, longest ${readability.longest} (CP-8 advisory, never fails)`);
    }
  }

  if (scanned === 0) {
    return { code: 3, lines: [`check-copy-lints: VACUOUS — ${manifest.routes.length} manifest routes, ${skipped} without <main>, 0 scanned (SIG-ENG-042)`] };
  }

  lines.unshift(
    `check-copy-lints: ${scanned} routes scanned (${skipped} non-prose skipped) — ` +
    `${reportFindings} report finding(s), ${enforcedFindings} enforced`,
  );
  if (advisory.length) {
    lines.push(`check-copy-lints: readability report — ${advisory.length} page(s) over the 22-word mean`);
    lines.push(...advisory.slice(0, 20));
    if (advisory.length > 20) lines.push(`  … ${advisory.length - 20} more`);
  }
  if (enforcedFindings > 0) return { code: 1, lines };
  lines.push(`check-copy-lints: PASS (report mode — flips ride each surface's ticket in copy-lint-enforce.json)`);
  return { code: 0, lines };
}

function main() {
  const args = parseArgs(process.argv.slice(2));
  if (args.help) {
    console.log("usage: node scripts/check-copy-lints.mjs [--dist DIR] [--manifest FILE] [--enforce FILE]");
    process.exit(0);
  }
  if (args.error) {
    console.error(`check-copy-lints: ${args.error}`);
    process.exit(2);
  }
  const { code, lines } = run({ dist: args.dist, manifestPath: args.manifest, enforcePath: args.enforce });
  const out = code === 0 ? console.log : console.error;
  for (const l of lines) out(l);
  process.exit(code);
}

if (process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1].split(sep).join("/")) {
  main();
}
