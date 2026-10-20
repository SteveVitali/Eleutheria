// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * P35.37 (R11-K13-TX-09, SIG-TRANSP-013, J3 §5.4, UXR-34): the figure-evidence
 * build check. Wired into `npm run check` as `check:figures`, after `build`.
 *
 * Two checks over the RENDERED named page classes (the design's words are
 * "rendered number" and "main content" — the check therefore measures built
 * HTML, not templates, so a `{count}` expression that escapes the component is
 * caught the same as a literal):
 *
 *   1. THE POINTER CHECK — every `<!-- sig-figure -->`…`<!-- /sig-figure -->`
 *      region on a named page must carry a manifest-listed `data-artifact`, a
 *      JSON-pointer `data-pointer`, a `data-breakdown` that resolves (an
 *      in-page `#…` id or a route), a unique `data-figure-id`, and a visible
 *      `data-figure-link="source"` anchor. The manifest set is the committed
 *      `src/lib/figure-artifacts.json` list (fixtures mode) — the same paths
 *      `defineFigures` validates against at build — or the REAL export
 *      manifest when `SIG_DATA_SOURCE=export`.
 *
 *   2. THE BARE-NUMERAL CHECK — after removing every figure region, tags,
 *      scripts and styles from the page's `<main>` content, a material
 *      numeral (MATERIAL_NUMERAL_RE) is a raw number outside the component →
 *      fail. Non-material incidental numerals (a cited RFC number, a port) are
 *      recorded — never silently skipped — in the committed allow-list
 *      `figure-numerals-allowlist.json` (file + token + count + reason).
 *
 * Named page classes (the J3 §5.4 list, verbatim): home, dossier, coverage,
 * freshness, sources, data, status.
 *
 * Usage: node scripts/check-figures.mjs [--dist DIR]
 * Exit: 0 pass · 1 failure · 2 usage · 3 vacuous (no named page measured —
 * SIG-ENG-042, never a silent green).
 */

import { existsSync, readdirSync, readFileSync } from "node:fs";
import { join, relative } from "node:path";
import { fileURLToPath } from "node:url";

const WEB = fileURLToPath(new URL("..", import.meta.url));
const REPO = join(WEB, "..");
const ARTIFACT_LIST = join(WEB, "src", "lib", "figure-artifacts.json");
const ALLOWLIST_PATH = join(WEB, "scripts", "figure-numerals-allowlist.json");

/** Byte-identical to MATERIAL_NUMERAL_PATTERN in src/lib/dossier-figures.ts —
 *  pinned equal by tests/unit/figures.test.ts. */
const MATERIAL_NUMERAL_RE = new RegExp(
  "(?<![\\w&#§.\\-:\\/–—≥])\\d+(?:,\\d{3})*(?:\\.\\d+)?(?![\\w&.:\\-–—\\/%])",
  "g",
);
/** Byte-identical to COMPARTMENT_STREAM_RE in src/lib/figures.ts (pinned by test). */
const COMPARTMENT_STREAM_RE = /^[a-z0-9_]+\/(sites|statements|record_claims)\.jsonl$/;

/** The J3 §5.4 named page classes → dist globs. */
const PAGE_CLASSES = [
  { cls: "home", files: ["index.html"] },
  { cls: "dossier", dirs: ["dossier"] },
  { cls: "coverage", files: ["coverage-metrics/index.html"] },
  { cls: "freshness", dirs: ["data-freshness"] },
  { cls: "sources", dirs: ["sources"] },
  { cls: "data", files: ["data-collection/index.html"] },
  { cls: "status", files: ["status/index.html"] },
];

const FIGURE_OPEN = "<!-- sig-figure -->";
const FIGURE_CLOSE = "<!-- /sig-figure -->";

function* walk(dir) {
  for (const e of readdirSync(dir, { withFileTypes: true })) {
    const p = join(dir, e.name);
    if (e.isDirectory()) yield* walk(p);
    else if (e.isFile() && p.endsWith(".html")) yield p;
  }
}

function listedArtifacts() {
  if ((process.env.SIG_DATA_SOURCE ?? "").trim() === "export") {
    const dir = process.env.SIG_EXPORT_DIR;
    if (dir) {
      const manifestPath = join(dir, "manifest.json");
      if (existsSync(manifestPath)) {
        const m = JSON.parse(readFileSync(manifestPath, "utf-8"));
        if (Array.isArray(m.artifacts)) {
          return new Set(m.artifacts.map((a) => String(a.path ?? a)));
        }
      }
    }
  }
  const parsed = JSON.parse(readFileSync(ARTIFACT_LIST, "utf-8"));
  if (!Array.isArray(parsed.artifacts)) {
    console.error("check-figures: figure-artifacts.json lacks an artifacts array");
    process.exit(2);
  }
  return new Set(parsed.artifacts.map(String));
}

function isListed(path, listed) {
  return listed.has(path) || COMPARTMENT_STREAM_RE.test(path);
}

function loadAllowlist() {
  if (!existsSync(ALLOWLIST_PATH)) return [];
  const parsed = JSON.parse(readFileSync(ALLOWLIST_PATH, "utf-8"));
  if (!Array.isArray(parsed.entries)) {
    console.error("check-figures: figure-numerals-allowlist.json lacks an entries array");
    process.exit(2);
  }
  return parsed.entries;
}

/** The page's main-content region (`<main …>…</main>`; the whole body when the
 *  print/special page names no main). */
function mainContent(html) {
  const m = /<main\b[^>]*>([\s\S]*)<\/main>/i.exec(html);
  const body = m ? m[1] : html;
  return { text: body, offset: m ? m.index + m[0].indexOf(m[1]) : 0 };
}

/**
 * Split `text` into figure-region and outside-figure segments. Returns
 * { figures: [{content, offset}], outside: [{content, offset}] }.
 */
function splitFigureRegions(text, baseOffset) {
  const figures = [];
  const outside = [];
  let pos = 0;
  for (;;) {
    const open = text.indexOf(FIGURE_OPEN, pos);
    if (open === -1) break;
    const close = text.indexOf(FIGURE_CLOSE, open);
    if (close === -1) {
      throw new Error(`unterminated <!-- sig-figure --> region at offset ${baseOffset + open}`);
    }
    outside.push({ content: text.slice(pos, open), offset: baseOffset + pos });
    figures.push({
      content: text.slice(open, close + FIGURE_CLOSE.length),
      offset: baseOffset + open,
    });
    pos = close + FIGURE_CLOSE.length;
  }
  outside.push({ content: text.slice(pos), offset: baseOffset + pos });
  return { figures, outside };
}

/** Markup-free text content of a segment (tags, scripts and styles removed). */
function textOnly(html) {
  return html
    .replace(/<script\b[\s\S]*?<\/script>/gi, " ")
    .replace(/<style\b[\s\S]*?<\/style>/gi, " ")
    .replace(/<[^>]*>/g, " ")
    .replace(/&[a-z]+;/gi, " ")
    .replace(/&#\d+;/gi, " ");
}

function lineOf(text, offset) {
  return text.slice(0, offset).split("\n").length;
}

function check(distDir) {
  const listed = listedArtifacts();
  const allowlist = loadAllowlist();
  const failures = [];
  const measured = [];
  let figureCount = 0;
  let numeralExempted = 0;

  const files = [];
  for (const pc of PAGE_CLASSES) {
    for (const f of pc.files ?? []) {
      const p = join(distDir, f);
      if (existsSync(p)) files.push({ cls: pc.cls, path: p });
    }
    for (const d of pc.dirs ?? []) {
      const dir = join(distDir, d);
      if (existsSync(dir)) {
        for (const p of walk(dir)) files.push({ cls: pc.cls, path: p });
      }
    }
  }
  if (files.length === 0) {
    console.error(`check-figures: VACUOUS — no named page-class file under ${distDir}`);
    return 3;
  }

  for (const { cls, path } of files) {
    const rel = relative(distDir, path).split("\\").join("/");
    const html = readFileSync(path, "utf-8");
    const { text: main, offset } = mainContent(html);
    let regions;
    try {
      regions = splitFigureRegions(main, offset);
    } catch (e) {
      failures.push(`${rel}: ${e.message}`);
      continue;
    }
    figureCount += regions.figures.length;
    measured.push({ rel, cls, figures: regions.figures.length });

    // ---- CHECK 1: every figure region honours the pointer contract --------
    const seenIds = new Set();
    for (const fig of regions.figures) {
      const line = lineOf(html, fig.offset);
      const tag = /<([a-z0-9-]+)\b([^>]*)>/i.exec(fig.content);
      if (!tag) {
        failures.push(`${rel}:${line}: sig-figure region carries no root element`);
        continue;
      }
      const attrs = tag[2];
      const attr = (name) => {
        const m = new RegExp(`${name}="([^"]*)"`).exec(attrs);
        return m ? m[1] : null;
      };
      const id = attr("data-figure-id");
      const artifact = attr("data-artifact");
      const pointer = attr("data-pointer");
      const breakdown = attr("data-breakdown");
      if (!id) failures.push(`${rel}:${line}: figure lacks data-figure-id`);
      else if (seenIds.has(id))
        failures.push(`${rel}:${line}: duplicate data-figure-id "${id}" (UXR-34)`);
      else seenIds.add(id);
      if (!artifact) failures.push(`${rel}:${line}: figure "${id}" lacks data-artifact`);
      else if (!isListed(artifact, listed))
        failures.push(
          `${rel}:${line}: figure "${id}" data-artifact "${artifact}" is not manifest-listed`,
        );
      if (!pointer || !pointer.startsWith("/"))
        failures.push(`${rel}:${line}: figure "${id}" lacks a JSON-pointer data-pointer`);
      if (!breakdown) {
        failures.push(`${rel}:${line}: figure "${id}" lacks data-breakdown`);
      } else if (breakdown.startsWith("#")) {
        const anchorId = breakdown.slice(1);
        if (!new RegExp(`id="${anchorId.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}"`).test(html))
          failures.push(`${rel}:${line}: figure "${id}" breakdown "${breakdown}" resolves nowhere`);
      }
      if (!/data-figure-link="source"/.test(fig.content) || !/<a\b[^>]*href="/.test(fig.content))
        failures.push(`${rel}:${line}: figure "${id}" has no visible source link`);
      if (!/data-figure-link="definition"/.test(fig.content))
        failures.push(`${rel}:${line}: figure "${id}" has no definition link`);
    }

    // ---- CHECK 2: no material numeral outside a figure region ------------
    const fileAllow = allowlist.filter((e) => e.file === rel);
    const remaining = new Map(fileAllow.map((e) => [e, e.count ?? 1]));
    const used = new Set();
    for (const seg of regions.outside) {
      const text = textOnly(seg.content);
      for (const m of text.matchAll(MATERIAL_NUMERAL_RE)) {
        const token = m[0];
        const entry = [...remaining.keys()].find(
          (e) => e.token === token && remaining.get(e) > 0,
        );
        if (entry) {
          remaining.set(entry, remaining.get(entry) - 1);
          used.add(entry);
          numeralExempted++;
          continue;
        }
        const line = lineOf(html, seg.offset + m.index);
        failures.push(
          `${rel}:${line}: raw numeral "${token}" in ${cls} main content outside <Figure> ` +
            `(J3 §5.4/UXR-34 — wrap it in <Figure> or record a reasoned allow-list entry)`,
        );
      }
    }
    for (const e of fileAllow) {
      if (!used.has(e))
        console.log(`  stale allow-list entry (matched nothing; prune it): ${rel} "${e.token}"`);
    }
  }

  const distRel = relative(REPO, distDir);
  console.log(
    `check-figures: ${measured.length} named-class page(s), ${figureCount} figure region(s), ` +
      `${numeralExempted} reasoned numeral exemption(s) under ${distRel}`,
  );
  for (const m of measured) console.log(`  ${m.cls}: ${m.rel} — ${m.figures} figure(s)`);
  if (figureCount === 0) {
    console.error("check-figures: VACUOUS — no figure region on any named page");
    return 3;
  }
  if (failures.length) {
    console.error("\n✗ figure-evidence check failed (SIG-TRANSP-013 / J3 §5.4):");
    for (const f of failures.sort()) console.error(`    ${f}`);
    return 1;
  }
  console.log("✓ every figure carries a manifest-listed pointer; no bare numerals in named pages.");
  return 0;
}

const args = process.argv.slice(2);
let distDir = join(WEB, "dist");
for (let i = 0; i < args.length; i++) {
  if (args[i] === "--dist") distDir = args[++i];
  else {
    console.error(`check-figures: unknown argument ${args[i]}`);
    process.exit(2);
  }
}
if (!existsSync(distDir)) {
  console.error(`check-figures: dist dir ${distDir} does not exist — run npm run build first`);
  process.exit(2);
}
process.exit(check(distDir));
