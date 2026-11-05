// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// P36.72a (ACC-PLACES a-half — the K4 JUR-06 / K5 DSRC-06 / K9/K10 / K7 / K8 /
// K11 merge, SIG-UI-092): the shared helpers the core-surfaces acceptance
// battery reads. Every sweep derives its route set from the BUILT site
// (dist/ + dist/page-types.json — never a hand list, K0 NEW-4); anything a
// sweep cannot verify it records with a named disposition, never a silent
// skip (SIG-ENG-042).

import { existsSync, readdirSync, readFileSync, statSync } from "node:fs";
import { join, relative } from "node:path";
import { fileURLToPath } from "node:url";

export const DIST_DIR = fileURLToPath(new URL("../../dist/", import.meta.url));
export const REPO_ROOT = fileURLToPath(new URL("../../../", import.meta.url));

/** The 09-27 advertised-route manifest the ROUTES.csv check reads. */
export const ROUTES_CSV_PATH = join(
  REPO_ROOT,
  "docs/build/planning/2026-09-30-next-phase/review/ROUTES.csv",
);

// ---------------------------------------------------------------------------
// Emitted files → served routes
// ---------------------------------------------------------------------------

/**
 * Every file the build emitted, mapped to the URL the static host answers:
 * `a/b/index.html` → `/a/b/`, `a/b/c.html` → `/a/b/c.html`, `a/b.json` →
 * `/a/b.json`. The crawl sweeps this set — a discovered-route sweep alone
 * would miss the JSON twins, feeds, drafts, tiles and conf the site ships.
 */
export function emittedRoutes(dir = DIST_DIR): string[] {
  const out: string[] = [];
  const walk = (d: string): void => {
    for (const e of readdirSync(d, { withFileTypes: true })) {
      const p = join(d, e.name);
      if (e.isDirectory()) {
        walk(p);
      } else if (e.isFile()) {
        const rel = `/${relative(dir, p).split("\\").join("/")}`;
        out.push(rel.endsWith("/index.html") ? rel.slice(0, -"index.html".length) : rel);
      }
    }
  };
  walk(dir);
  return out.sort();
}

/** Binary families a HEAD-only probe covers (bodies measured by the budget sweep). */
export const BINARY_EXT = /\.(pmtiles|png|woff2?|ico|svg|gz|parquet|sqlite|torrent)$/i;

// ---------------------------------------------------------------------------
// The <Figure> contract (J3 §5.4 / SIG-TRANSP-013)
// ---------------------------------------------------------------------------

export interface FigureRef {
  id: string;
  figureClass: string;
  artifact: string;
  pointer: string;
  breakdown: string;
  value: string;
  /** The `data-figure-link="source"` href (null when the figure carries none). */
  sourceHref: string | null;
  /** The rendered value text inside the figure's own <strong>, when present. */
  rendered: string | null;
  /** The page file the region was read from. */
  file: string;
}

const FIGURE_OPEN = "<!-- sig-figure -->";
const FIGURE_CLOSE = "<!-- /sig-figure -->";
const ATTR = (name: string) => new RegExp(`${name}="([^"]*)"`);

/** Parse every <Figure> region out of a built HTML document. */
export function parseFigureRegions(html: string, file: string): FigureRef[] {
  const out: FigureRef[] = [];
  let pos = 0;
  for (;;) {
    const open = html.indexOf(FIGURE_OPEN, pos);
    if (open === -1) break;
    const close = html.indexOf(FIGURE_CLOSE, open);
    if (close === -1) break;
    const region = html.slice(open, close + FIGURE_CLOSE.length);
    const get = (n: string): string | null => {
      const m = ATTR(n).exec(region);
      return m ? m[1] : null;
    };
    // the source marker is an <a href> to the recomputing bytes OR a <span>
    // label (the figure's evidence is the page's own served route) — a span
    // keeps the marker honest without pretending a link exists
    const srcA = /<a\b[^>]*data-figure-link="source"[^>]*href="([^"]+)"/.exec(region);
    const srcAny = /<[a-z]+\b[^>]*data-figure-link="source"[^>]*>/.exec(region);
    const sourceHref = srcA ? srcA[1] : srcAny ? "#" : null;
    const rendered = /<strong>([^<]*)<\/strong>/.exec(region);
    const artifact = get("data-artifact");
    const pointer = get("data-pointer");
    const value = get("data-figure-value");
    if (artifact !== null && pointer !== null && value !== null) {
      out.push({
        id: get("data-figure-id") ?? "",
        figureClass: get("data-figure-class") ?? "",
        artifact,
        pointer,
        breakdown: get("data-breakdown") ?? "",
        value,
        sourceHref,
        rendered: rendered ? rendered[1] : null,
        file,
      });
    }
    pos = close + FIGURE_CLOSE.length;
  }
  return out;
}

/** RFC 6901 JSON-pointer resolution (`/a/0/b`); returns a sentinel when absent. */
export const POINTER_MISSING = Symbol("pointer-missing");

/**
 * Figure-pointer resolution — the pointer language is key-aware: an object
 * key descends, a numeric segment indexes an array, an id-key value selects
 * matching rows (`source_id`, `slug`, …), and a field segment descends into
 * every row carrying it (row-documents like `freshness.jsonl` and
 * `executions.jsonl`, where the figure's number lives under a named field of
 * the page's own row). Returns the SET of all resolution candidates — a
 * figure's number is proven when one candidate equals it.
 */
export function resolvePointerCandidates(doc: unknown, pointer: string): unknown[] {
  if (pointer === "" || pointer === "/") return [doc];
  if (!pointer.startsWith("/")) return [];
  const segs = pointer.slice(1).split("/");
  let frontier: unknown[] = [doc];
  for (const raw of segs) {
    const key = raw.replace(/~1/g, "/").replace(/~0/g, "~");
    const next: unknown[] = [];
    for (const cur of frontier) {
      if (Array.isArray(cur)) {
        const n = Number(key);
        if (Number.isInteger(n) && n >= 0 && n < cur.length) {
          next.push(cur[n]);
          continue;
        }
        for (const r of cur) {
          if (r === null || typeof r !== "object" || Array.isArray(r)) continue;
          const rec = r as Record<string, unknown>;
          if (ID_KEYS.some((k) => String(rec[k]) === key)) next.push(rec);
          else if (key in rec) next.push(rec[key]);
        }
      } else if (cur !== null && typeof cur === "object") {
        if (key in (cur as Record<string, unknown>)) {
          next.push((cur as Record<string, unknown>)[key]);
        }
      }
    }
    frontier = next;
    if (frontier.length === 0) return [];
  }
  return frontier;
}

/** Single-value convenience (legacy call shape). */
export function resolvePointer(doc: unknown, pointer: string): unknown {
  const c = resolvePointerCandidates(doc, pointer);
  return c.length > 0 ? c[0] : POINTER_MISSING;
}

const ID_KEYS = ["source_id", "id", "key", "slug", "kind", "handle", "jkey", "name", "task_id"];

/**
 * The served route a `data-artifact` path resolves to, or null when the
 * artifact has no page-served bytes (its figures then carry a page-route
 * source link — the reachability leg covers those). Mirrors the
 * `artifact/[...path].json` getStaticPaths mapping: a `.jsonl` stream serves
 * its row array at the `.json` twin path; `web/entity/**` twins emit under
 * `/entity/**`; `web/unplaced.json` serves at `/dossier/unplaced.json`.
 */
export function artifactRoute(artifact: string): string | null {
  if (artifact.startsWith("web/entity/")) {
    const p = `/${artifact.slice("web/".length)}`;
    return existsSync(join(DIST_DIR, p)) ? p : null;
  }
  if (artifact === "web/unplaced.json") {
    return existsSync(join(DIST_DIR, "dossier/unplaced.json")) ? "/dossier/unplaced.json" : null;
  }
  const twin = `/artifact/${artifact.replace(/\.jsonl$/, "").replace(/\.json$/, "")}.json`;
  return existsSync(join(DIST_DIR, twin.slice(1))) ? twin : null;
}

// ---------------------------------------------------------------------------
// dist/redirects.conf — the ONE redirect generator's emitted include
// ---------------------------------------------------------------------------

export interface RedirectRule {
  from: string;
  /** "exact" (location = /p) or "prefix" (location /p). */
  match: "exact" | "prefix";
  status: 200 | 300 | 301 | 302 | 410 | null;
  /** The 3xx successor path ($is_args$args stripped). */
  target: string | null;
  /** The try_files-served file. */
  tryFile: string | null;
  prefix: boolean;
  raw: string;
}

export function redirectRules(): RedirectRule[] {
  const conf = readFileSync(join(DIST_DIR, "redirects.conf"), "utf-8");
  const rules: RedirectRule[] = [];
  for (const line of conf.split("\n")) {
    const m = /^location (= )?(\S+) \{\s*(.+?)\s*\}/.exec(line);
    if (!m) continue;
    const body = m[3];
    const ret = /^return (\d+)(?:\s+(\S+?)\$is_args\$args)?;/.exec(body);
    const tf = /^try_files (\S+) =404;/.exec(body);
    rules.push({
      from: m[2],
      match: m[1] ? "exact" : "prefix",
      status: ret ? (Number(ret[1]) as RedirectRule["status"]) : tf ? 200 : null,
      target: ret?.[2] ? ret[2].replace(/\$is_args\$args$/, "") : null,
      tryFile: tf ? tf[1] : null,
      prefix: !m[1],
      raw: line.trim(),
    });
  }
  return rules;
}

/** The dist file a slash-route resolves to (`/a/b/` → `a/b/index.html`).
 *  Returns a path RELATIVE to DIST_DIR; a directory resolves only through its
 *  index.html. */
export function routeFile(path: string): string | null {
  const rel = path.replace(/^\/+/, "");
  const p = join(DIST_DIR, rel);
  if (existsSync(p) && statSync(p).isFile()) return rel;
  const idx = join(p, "index.html");
  return existsSync(idx) ? join(rel, "index.html") : null;
}

/** The served route an emitted file answers at (`a/b/index.html` → `/a/b/`). */
export function servedRoute(path: string): string {
  const rel = path.replace(/^\/+/, "");
  return `/${rel.replace(/index\.html$/, "")}`;
}

// ---------------------------------------------------------------------------
// ROUTES.csv — the 09-27 advertised-route manifest
// ---------------------------------------------------------------------------

export interface RoutesCsvRow {
  id: string;
  pattern: string;
  source: string;
  deployed: string;
  pageClass: string;
  notes: string;
}

export function loadRoutesCsv(): RoutesCsvRow[] {
  const rows: RoutesCsvRow[] = [];
  const lines = readFileSync(ROUTES_CSV_PATH, "utf-8").split("\n");
  for (const line of lines.slice(1)) {
    if (!line.trim()) continue;
    const fields = line.split(",");
    rows.push({
      id: fields[0].trim(),
      pattern: fields[1] ?? "",
      source: fields[2] ?? "",
      deployed: fields[3] ?? "",
      pageClass: fields[7] ?? "",
      notes: fields.slice(10).join(","),
    });
  }
  return rows;
}

// ---------------------------------------------------------------------------
// Misc
// ---------------------------------------------------------------------------

/** K14 §3.6 digit grouping — must mirror lib/format groupDigits. */
export function groupDigits(v: string): string {
  return v.replace(/\B(?=(\d{3})+(?!\d))/g, ",");
}

/** Visible text with the id-allowed containers stripped (code/pre + sig-mut). */
export function visibleTextMinusIdSpans(html: string): string {
  let t = html;
  // drop script/style wholesale
  t = t.replace(/<(script|style)\b[^>]*>[\s\S]*?<\/\1>/gi, " ");
  // allowed id containers: <code>, <pre>, any element carrying sig-mut, and
  // the J3 §5.4 figure-evidence link labels ("coverage of <id>",
  // "run row for <id>" — the defined secondary-id context)
  t = t.replace(/<(code|pre)\b[^>]*>[\s\S]*?<\/\1>/gi, " ");
  t = t.replace(/<([a-z0-9-]+)\b[^>]*class="[^"]*sig-(mut|figure__evidence|figure__absent)[^"]*"[^>]*>[\s\S]*?<\/\1>/gi, " ");
  t = t.replace(/<a\b[^>]*data-figure-link[^>]*>[\s\S]*?<\/a>/gi, " ");
  // strip remaining tags + attributes, keep text nodes; a rendered URL's own
  // text (the cite/permalink blocks) is a locator, not an id mention
  t = t.replace(/<[^>]+>/g, " ");
  t = t.replace(/https?:\/\/\S+/g, " ");
  // rendered route paths ("/sources/<id>/" in detail rows) are locators like
  // URLs — the id travels as part of the path, never as a prose mention
  t = t.replace(/\/[\w.\-/]+\//g, " ");
  return t
    .replace(/&amp;/g, "&")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&#39;|&apos;/g, "'")
    .replace(/&quot;/g, '"')
    .replace(/&nbsp;/g, " ");
}
