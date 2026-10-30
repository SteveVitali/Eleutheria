// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * P35.50 (UXK0-1, K0 §4.2, ADR-155, SIG-UI-036/041) — the page-type registry.
 *
 * Every public HTML route carries a declared page type (D-K0-1 [A-12] = a —
 * HTML-first page types replace the zero-JS rule; this machinery implements
 * the ADR, it never re-decides it):
 *
 *   T0 record & print — no `<script>` element at all; the page IS the no-JS page.
 *   T1 content        — complete server-rendered HTML; only allow-listed
 *                       `type="module"` enhancement entries plus the hashed
 *                       Astro bootstrap; JS-off `main` text equals JS-on text
 *                       minus `[data-enhancement]` subtrees.
 *   T2 explore        — app-like surfaces that keep URL state
 *                       (`sig.workspace-state/2`; the v1 contract still parses), a server-rendered
 *                       first view and a named no-JS equivalent.
 *   T3 tools          — `/curate/**` (ADR-068; loopback-only, never published).
 *
 * The initial registry is K0 §4.2's table verbatim, extended only where the
 * built surface today has routes the table does not name (`/terms/`,
 * `/data-collection/`, the flat `*.html` error copies) or where K0 itself
 * records today's interim (`/network/` is classified as the T2 surface it
 * currently is — its redirect/T1 migration is the GX-09a row's, out of scope
 * here). Raising a budget, adding a T2 surface or adding a browser runtime
 * dependency is an ADR-155 change path — never an edit here.
 *
 * Pattern syntax (root-relative, `/`-prefixed):
 *   literal segment  — matches itself exactly;
 *   `*`              — matches exactly one segment;
 *   `**`             — matches zero or more segments (at most once per pattern).
 *
 * Classification is MOST-SPECIFIC-WINS, never first-match: candidate patterns
 * are compared by the segment kind that covered each route position,
 * right-to-left from the leaf (literal > `*` > `**`), then by fewest wildcard
 * segments. Two distinct entries that tie on the same route are a BUILD ERROR
 * ("doubly-classified"), as is a route that matches nothing — classification
 * fails closed (K0 NEW-4).
 *
 * Entry fields (draft UXR-02's registry fields):
 *   patterns          — the route patterns the entry claims;
 *   type              — T0 | T1 | T2 | T3;
 *   owner             — the ticket accountable for the route family (K0's lane
 *                       annotations resolved to plan rows where they exist;
 *                       P35.50 where no later row claims the family yet);
 *   contract          — the named `sig.*` data contract the route renders, or
 *                       "none" for copy-only/chrome surfaces (absence is
 *                       recorded, never a fabricated id);
 *   noJsEquivalent    — what carries the facts when JS never runs (K0 §4.4);
 *   internal          — emitted only under SIG_BUILD_INTERNAL=1 (the injected
 *                       `src/internal/` surface — never publishable);
 *   examples          — concrete routes each pattern must classify (tested).
 */

import { existsSync, readdirSync, readFileSync, writeFileSync } from "node:fs";
import { join, relative, sep } from "node:path";

export type PageType = "T0" | "T1" | "T2" | "T3";

export const PAGE_TYPES: readonly PageType[] = ["T0", "T1", "T2", "T3"];

export interface NoJsEquivalent {
  /**
   * "self" — the page IS the no-JS page (T0, T1 content today);
   * "sections" — named sections of the page carry the equivalent (T2);
   * "none" — internal tooling with no public no-JS contract (T3).
   */
  kind: "self" | "sections" | "none";
  /** The K0 §4.4 name for the equivalent — what the reader follows. */
  description: string;
  /**
   * `data-testid` hooks the parity spec resolves to prove the equivalent is
   * present and populated (kind "sections" only).
   */
  testIds?: readonly string[];
}

export interface PageTypeEntry {
  readonly patterns: readonly string[];
  readonly type: PageType;
  readonly owner: string;
  readonly contract: string;
  readonly noJsEquivalent: NoJsEquivalent;
  readonly internal?: boolean;
  readonly examples: readonly string[];
  readonly notes?: string;
}

const SELF: NoJsEquivalent = {
  kind: "self",
  description: "the page itself is complete without JavaScript",
};
const NO_EQUIVALENT: NoJsEquivalent = {
  kind: "none",
  description: "internal tooling — no public no-JS contract",
};

export const PAGE_TYPE_REGISTRY: readonly PageTypeEntry[] = [
  // ------------------------------------------------------------------ T0 ---
  {
    patterns: ["/r/**"],
    type: "T0",
    owner: "P32.13",
    contract: "sig.published-record/1",
    noJsEquivalent: SELF,
    examples: ["/r/p-abc123/c/graph/entity/site/cam-1/", "/r/p-abc123/"],
    notes:
      "P32.13 release record pages, rendered by release_pages.py — not Astro-emitted today; registered so the namespace is classified before it ships.",
  },
  {
    patterns: ["/**/print/"],
    type: "T0",
    owner: "P35.50",
    contract: "sig.dossier/2",
    noJsEquivalent: SELF,
    examples: ["/dossier/oklahoma-city/print/", "/s/p-abc123/dossier/x/print/"],
    notes:
      "Every `…/print/` page, including the `/s/<pub>/**/print/` form K0 names — the wildcard covers snapshot-prefixed print views. Leaf-first ordering beats content-type patterns such as `/dossier/**` and `/s/*/**`.",
  },
  {
    patterns: ["/dispute/"],
    type: "T0",
    owner: "P34.17",
    contract: "none",
    noJsEquivalent: SELF,
    examples: ["/dispute/"],
  },
  {
    patterns: ["/intake/**"],
    type: "T0",
    owner: "P32.16",
    contract: "sig.intake-receipt/1",
    noJsEquivalent: SELF,
    examples: ["/intake/", "/intake/receipt/r-1/"],
    notes:
      "The correction-intake receiver's HTML pages (P32.16 — no-JS by construction); not Astro-emitted today.",
  },
  {
    patterns: ["/v1/**"],
    type: "T0",
    owner: "P32.14",
    contract: "none",
    noJsEquivalent: SELF,
    examples: ["/v1/releases/p-abc123/compartments/graph/search"],
    notes:
      "K0's 'API format=html pages' — the read API's own T0 surface (P32.14/P34.46). Never inside `dist`; registered so the full contract surface is classified in one table.",
  },
  {
    patterns: ["/releases/*/data/**"],
    type: "T0",
    owner: "P32.13",
    contract: "sig.publication-catalog/1",
    noJsEquivalent: SELF,
    examples: ["/releases/p-abc123/data/catalog/"],
    notes:
      "K0's `/releases/<pub>/data/**` listings — machine-readable release data listings are record-class pages.",
  },
  {
    patterns: [
      "/403/",
      "/403.html",
      "/404.html",
      "/404/",
      "/410/",
      "/410.html",
      "/500/",
      "/500.html",
    ],
    type: "T0",
    owner: "P34.13",
    contract: "sig.error-page/1",
    noJsEquivalent: SELF,
    examples: ["/404.html", "/403/", "/410.html", "/500.html"],
    notes:
      "404/410 tombstones, the 403 refused page and P36.22's 500 — K0's '404/410 tombstones'; the flat `*.html` copies are the error_page files sigChrome emits. P36.22 (SIG-UI-151): every error page renders the five-part `sig.error-page/1` contract with the search·home·status recovery trio.",
  },

  // ------------------------------------------------------------------ T1 ---
  {
    patterns: ["/"],
    type: "T1",
    owner: "P34.11",
    contract: "sig.dossier-index/2",
    noJsEquivalent: SELF,
    examples: ["/"],
  },
  {
    patterns: ["/dossier/**"],
    type: "T1",
    owner: "P35.45",
    contract: "sig.dossier/2",
    noJsEquivalent: SELF,
    examples: ["/dossier/", "/dossier/oklahoma-city/", "/dossier/unplaced/"],
  },
  {
    patterns: ["/entity/**"],
    type: "T1",
    owner: "P36.42a",
    contract: "none",
    noJsEquivalent: SELF,
    examples: ["/entity/site/cam-1/"],
    notes:
      "K2's latest-view entity pages — registered ahead of the GX-06a row that ships them (K0 classifies them now).",
  },
  {
    patterns: ["/sources/**"],
    type: "T1",
    owner: "P34.17",
    contract: "sig.source-licence-table/1",
    noJsEquivalent: SELF,
    examples: ["/sources/", "/sources/identifier-changed/"],
    notes: "K9's sources table and source pages (a T1 ≤ 15 KiB enhancement row, never a fourth T2 surface — K0 §4.2).",
  },
  {
    patterns: ["/data-freshness/**"],
    type: "T1",
    owner: "P35.40",
    contract: "sig.source-row/1",
    noJsEquivalent: SELF,
    examples: ["/data-freshness/", "/data-freshness/status/"],
    notes: "K10's freshness table — pre-rendered sort routes are plain GETs (P27.7).",
  },
  {
    patterns: ["/research-queue/**"],
    type: "T1",
    owner: "P35.50",
    contract: "none",
    noJsEquivalent: SELF,
    examples: ["/research-queue/"],
    notes: "K11's queue — paginated static routes (K11 §5) until its own enhancement row.",
  },
  {
    patterns: ["/task/**"],
    type: "T1",
    owner: "P35.50",
    contract: "none",
    noJsEquivalent: SELF,
    examples: ["/task/abc-123/"],
    notes: "K11's task pages (RQ-03's row ships them); the retired `/task/new/` fixtures stay un-emitted.",
  },
  {
    patterns: ["/watch/**"],
    type: "T1",
    owner: "P35.50",
    contract: "sig.watch-item/1",
    noJsEquivalent: SELF,
    examples: ["/watch/", "/watch/federal-funding/"],
    notes: "K7's watch pages.",
  },
  {
    patterns: ["/evidence/**"],
    type: "T1",
    owner: "P35.50",
    contract: "sig.statement/1",
    noJsEquivalent: SELF,
    examples: ["/evidence/", "/evidence/active-device-count/"],
    notes: "K8's evidence viewer — static pages + their `.json` twins.",
  },
  {
    patterns: ["/research-dossier/**"],
    type: "T1",
    owner: "P32.17",
    contract: "sig.research-dossier/1",
    noJsEquivalent: SELF,
    internal: true,
    examples: ["/research-dossier/", "/research-dossier/okc-alpr/"],
    notes: "The reviewed research-dossier portfolio — internal/injected today (SIG_BUILD_INTERNAL), T1 when it ships.",
  },
  {
    patterns: ["/releases/"],
    type: "T1",
    owner: "P32.13",
    contract: "sig.publication-catalog/1",
    noJsEquivalent: SELF,
    internal: true,
    examples: ["/releases/"],
    notes:
      "The release index — internal/injected today. Only `/releases/` itself is T1; `/releases/<pub>/data/**` is T0 and anything deeper fails closed until a row claims it.",
  },
  {
    patterns: ["/data/**"],
    type: "T1",
    owner: "P35.39",
    contract: "sig.data-dictionary/1",
    noJsEquivalent: SELF,
    examples: ["/data/dictionary/"],
    notes: "J3's data surfaces (the generated dictionary today).",
  },
  {
    patterns: ["/status/**"],
    type: "T1",
    owner: "P34.17",
    contract: "sig.publication/1",
    noJsEquivalent: SELF,
    examples: ["/status/"],
    notes: "J3's status lane page (TX-07).",
  },
  {
    patterns: ["/methodology/", "/coverage-metrics/", "/corrections/"],
    type: "T1",
    owner: "P35.50",
    contract: "none",
    noJsEquivalent: SELF,
    examples: ["/methodology/", "/coverage-metrics/", "/corrections/"],
    notes: "K14's method/coverage/corrections content pages.",
  },
  {
    patterns: ["/contribution-back/"],
    type: "T1",
    owner: "P21.7",
    contract: "none",
    noJsEquivalent: SELF,
    internal: true,
    examples: ["/contribution-back/"],
    notes: "The withdrawn contribution-back explainer (C-12) — injected internal route today.",
  },
  {
    patterns: ["/editorial-standards/", "/style-guide/"],
    type: "T1",
    owner: "P34.13",
    contract: "none",
    noJsEquivalent: SELF,
    examples: ["/editorial-standards/", "/style-guide/"],
    notes: "K14's editorial/style content pages.",
  },
  {
    patterns: ["/glossary/"],
    type: "T1",
    owner: "P36.17",
    contract: "sig.lexicon/1",
    noJsEquivalent: SELF,
    examples: ["/glossary/"],
    notes:
      "K14 §2.5's generated glossary — Appendix E verbatim + the shared lexicon + site terms. Popovers are native-HTML, no JS.",
  },
  {
    patterns: ["/visual-language/"],
    type: "T1",
    owner: "P15.2",
    contract: "none",
    noJsEquivalent: SELF,
    internal: true,
    examples: ["/visual-language/"],
    notes: "The epistemic-language reference page — withdrawn from public nav (A-0.3 = b), injected internal route.",
  },
  {
    patterns: ["/enhancement-kit/**"],
    type: "T1",
    owner: "P36.20",
    contract: "none",
    noJsEquivalent: SELF,
    internal: true,
    examples: ["/enhancement-kit/"],
    notes:
      "The internal UXK0-4 harness — fixture markup exercising every element plus the sig.typeahead-shard/1 fixture endpoint (P36.40 owns the export-mode shards).",
  },
  {
    patterns: ["/component-kit/"],
    type: "T1",
    owner: "P36.22",
    contract: "none",
    noJsEquivalent: SELF,
    internal: true,
    examples: ["/component-kit/"],
    notes:
      "The internal UXK14-3a harness — fixture data exercising every component-kit-A visual component; never published.",
  },
  {
    patterns: ["/about/**"],
    type: "T1",
    owner: "P35.50",
    contract: "none",
    noJsEquivalent: SELF,
    examples: ["/about/", "/about/maintainer/"],
    notes: "K14's about namespace — registered ahead of its pages.",
  },
  {
    patterns: ["/data-collection/"],
    type: "T1",
    owner: "P35.38a",
    contract: "none",
    noJsEquivalent: SELF,
    examples: ["/data-collection/"],
    notes: "The crawler contact/explanation page (SIG-INGEST-036) — a public route the K0 table does not name; T1 content.",
  },
  {
    patterns: ["/terms/"],
    type: "T1",
    owner: "P34.13",
    contract: "none",
    noJsEquivalent: SELF,
    examples: ["/terms/"],
    notes: "The `/terms` forwarder (P34.13) — a plain link + N-7 notice, minimal chrome, noindex; T1 content.",
  },
  {
    patterns: ["/s/*/**"],
    type: "T1",
    owner: "P36.66b",
    contract: "none",
    noJsEquivalent: SELF,
    examples: ["/s/p-abc123/", "/s/p-abc123/dossier/oklahoma-city/"],
    notes:
      "The same T1 routes under `/s/<pub>/` (K0's snapshot-prefixed equivalents; D-J3-6 = yes). Print (`/**/print/`) stays T0 and the T2 rows keep their types inside a snapshot by leaf-first ordering — only a route no T0/T2/T3 row claims falls to this umbrella.",
  },
  {
    patterns: ["/v/*/**"],
    type: "T1",
    owner: "P35.50",
    contract: "none",
    noJsEquivalent: SELF,
    examples: ["/v/p-abc123/dossier/oklahoma-city/"],
    notes: "K0's `/v/<pub>/` latest-view equivalents of the T1 routes.",
  },

  // ------------------------------------------------------------------ T2 ---
  {
    patterns: ["/map/"],
    type: "T2",
    owner: "P37.17",
    contract: "sig.workspace-state/2",
    noJsEquivalent: {
      kind: "sections",
      description:
        "the coverage-bins table, the located-records table and the records-without-a-point list (K0 §4.4: the map's tabular equivalents)",
      testIds: ["map-asset-row", "map-attribution"],
    },
    examples: ["/map/"],
    notes: "The T2 map surface — today's MapLibre island stays until its own migration rows.",
  },
  {
    patterns: ["/explore/"],
    type: "T2",
    owner: "P37.17",
    contract: "sig.workspace-state/2",
    noJsEquivalent: {
      kind: "sections",
      description:
        "static SVG overview graphs, adjacency/relationship tables and precomputed path hop lists (K0 §4.4)",
      testIds: [],
    },
    examples: ["/explore/"],
    notes: "K0's graph-explorer surface — registered ahead of the GX-09a row that ships it.",
  },
  {
    patterns: ["/network/"],
    type: "T2",
    owner: "P37.17",
    contract: "sig.workspace-state/2",
    noJsEquivalent: {
      kind: "sections",
      description:
        "the ego-network figure caption plus the access-edge lists and access-path hop lists — the page's stated source of truth",
      testIds: ["access-edge", "path-hop"],
    },
    examples: ["/network/"],
    notes:
      "K0 records `/network/` becomes a redirect or a T1 page (the GX-09a row) — TODAY it is the network island surface, so it classifies as the T2 explore page it actually is (the registry describes the built surface, never the plan).",
  },
  {
    patterns: ["/search/"],
    type: "T2",
    owner: "P36.40",
    contract: "sig.workspace-state/2",
    noJsEquivalent: {
      kind: "sections",
      description:
        "the release-pinned GET search forms (format=html to the read API) and the static browse index (K0 §4.4)",
      testIds: ["release-search", "search-browse"],
    },
    examples: ["/search/"],
    notes: "The T2 search surface — released-corpus GET forms plus the opt-in quick-filter island.",
  },
  {
    patterns: ["/s/*/map/", "/s/*/explore/", "/s/*/network/", "/s/*/search/"],
    type: "T2",
    owner: "P36.66b",
    contract: "sig.workspace-state/2",
    noJsEquivalent: {
      kind: "sections",
      description: "the same named equivalents as the unprefixed T2 surfaces, under `/s/<pub>/`",
      testIds: [],
    },
    examples: ["/s/p-abc123/map/", "/s/p-abc123/search/"],
    notes: "K0's T2 routes under `/s/<pub>/` — the snapshot keeps its explore surfaces at their own type.",
  },

  // ------------------------------------------------------------------ T3 ---
  {
    patterns: ["/curate/**"],
    type: "T3",
    owner: "P21.6",
    contract: "none",
    noJsEquivalent: NO_EQUIVALENT,
    internal: true,
    examples: ["/curate/", "/curate/submit/", "/curate/er_match:agency:a~agency:b/"],
    notes:
      "The authenticated curation surface (ADR-068; loopback-only, never published — the publish strip stays).",
  },
];

// ---------------------------------------------------------------- matching ---

type SegmentKind = "literal" | "single" | "rest";

interface ParsedSegment {
  kind: SegmentKind;
  text: string;
}

const SEGMENT_KIND_RANK: Record<SegmentKind, number> = {
  literal: 3,
  single: 2,
  rest: 1,
};

/** Split a route path into segments (`/` → []; `/a/b/` → ["a","b"]). */
function routeSegments(path: string): string[] {
  return path.split("/").filter((s) => s !== "");
}

/** Parse a registry pattern; throws on a malformed pattern (registry bug, build-fails). */
export function parsePattern(pattern: string): ParsedSegment[] {
  if (!pattern.startsWith("/")) {
    throw new Error(`page-type pattern must be root-relative: ${pattern}`);
  }
  const raw = pattern.split("/").filter((s) => s !== "");
  let sawRest = false;
  return raw.map((seg) => {
    if (seg === "**") {
      if (sawRest) throw new Error(`page-type pattern has two ** segments: ${pattern}`);
      sawRest = true;
      return { kind: "rest" as const, text: seg };
    }
    if (seg === "*") return { kind: "single" as const, text: seg };
    if (seg.includes("*")) {
      throw new Error(`page-type pattern has a partial wildcard segment: ${pattern}`);
    }
    return { kind: "literal" as const, text: seg };
  });
}

/**
 * The per-route-position coverage vector a pattern produces when it matches:
 * for each route segment index, the kind of pattern segment that covered it
 * (`rest` marks every position a `**` spans). `null` when the pattern does not
 * match. A pattern with `**` mid-list expands it over however many positions
 * are needed so the tail literals still line up.
 */
function coverageVector(
  pattern: ParsedSegment[],
  segments: readonly string[],
): SegmentKind[] | null {
  const restAt = pattern.findIndex((s) => s.kind === "rest");
  if (restAt === -1) {
    if (pattern.length !== segments.length) return null;
    for (let i = 0; i < pattern.length; i += 1) {
      const p = pattern[i]!;
      if (p.kind === "literal" && p.text !== segments[i]) return null;
    }
    return pattern.map((p) => p.kind);
  }
  // One `**` at pattern position `restAt`; it covers (segments - (others)) slots.
  const others = pattern.length - 1;
  const span = segments.length - others;
  if (span < 0) return null;
  const head = pattern.slice(0, restAt);
  const tail = pattern.slice(restAt + 1);
  const vector: SegmentKind[] = [];
  for (let i = 0; i < head.length; i += 1) {
    const p = head[i]!;
    if (p.kind === "literal" && p.text !== segments[i]) return null;
    vector.push(p.kind);
  }
  for (let i = 0; i < span; i += 1) vector.push("rest");
  for (let i = 0; i < tail.length; i += 1) {
    const p = tail[i]!;
    const seg = segments[head.length + span + i];
    if (p.kind === "literal" && p.text !== seg) return null;
    vector.push(p.kind);
  }
  return vector;
}

/**
 * Which of two matched patterns is more specific for this route: compare the
 * coverage vectors right-to-left from the leaf (a literal covering the leaf
 * is the more specific claim — the `…/print/` pattern beats `/dossier/**` on a
 * print page); on identical vectors the pattern with fewer wildcard segments
 * wins (`/x/` beats the `…/x/` rest form). Returns -1 (a wins), 1 (b wins), 0 (genuinely
 * ambiguous — a build error).
 */
function compareMatches(
  a: { parsed: ParsedSegment[]; vector: SegmentKind[] },
  b: { parsed: ParsedSegment[]; vector: SegmentKind[] },
): -1 | 0 | 1 {
  for (let i = a.vector.length - 1; i >= 0; i -= 1) {
    const ra = SEGMENT_KIND_RANK[a.vector[i]!];
    const rb = SEGMENT_KIND_RANK[b.vector[i]!];
    if (ra !== rb) return ra > rb ? -1 : 1;
  }
  const wild = (p: ParsedSegment[]) => p.filter((s) => s.kind !== "literal").length;
  const wa = wild(a.parsed);
  const wb = wild(b.parsed);
  if (wa !== wb) return wa < wb ? -1 : 1;
  return 0;
}

export type ClassifyResult =
  | { ok: true; entry: PageTypeEntry; pattern: string }
  | { ok: false; kind: "unclassified"; path: string }
  | { ok: false; kind: "ambiguous"; path: string; patterns: string[] };

interface RegistryMatch {
  entry: PageTypeEntry;
  patternText: string;
  parsed: ParsedSegment[];
  vector: SegmentKind[];
}

/**
 * Classify one route path (`/x/` or `/404.html`) against the registry.
 * Most-specific-wins; an unmatched route is `unclassified` and two distinct
 * entries that tie are `ambiguous` — both are build errors.
 */
export function classifyRoute(
  path: string,
  registry: readonly PageTypeEntry[] = PAGE_TYPE_REGISTRY,
): ClassifyResult {
  const segments = routeSegments(path);
  const matches: RegistryMatch[] = [];
  for (const entry of registry) {
    for (const patternText of entry.patterns) {
      const parsed = parsePattern(patternText);
      const vector = coverageVector(parsed, segments);
      if (vector !== null) matches.push({ entry, patternText, parsed, vector });
    }
  }
  if (matches.length === 0) return { ok: false, kind: "unclassified", path };
  let best = matches[0]!;
  const tied: RegistryMatch[] = [best];
  for (const m of matches.slice(1)) {
    const cmp = compareMatches(best, m);
    if (cmp === 1) {
      best = m;
      tied.length = 0;
      tied.push(m);
    } else if (cmp === 0) {
      if (!tied.some((t) => t.entry === m.entry && t.patternText === m.patternText)) {
        tied.push(m);
      }
    }
  }
  // A route matched by two DIFFERENT registry entries with identical claim
  // strength is a registry error — never a coin flip. Tied patterns inside the
  // SAME entry resolve deterministically (the entry's own first-declared
  // pattern is recorded).
  const winnerEntries = new Set(tied.map((t) => t.entry));
  if (winnerEntries.size > 1) {
    return { ok: false, kind: "ambiguous", path, patterns: tied.map((t) => t.patternText) };
  }
  const bestEntry = best.entry;
  const bestPattern = tied.find((t) => t.entry === bestEntry)?.patternText ?? best.patternText;
  return { ok: true, entry: bestEntry, pattern: bestPattern };
}

// -------------------------------------------------------------- discovery ---

/** Convert a dist-relative html file into its route path (`x/index.html` → `/x/`; `404.html` → `/404.html`). */
export function htmlFileToRoute(rel: string): string {
  const norm = rel.split(sep).join("/");
  if (norm === "index.html") return "/";
  if (norm.endsWith("/index.html")) return `/${norm.slice(0, -"index.html".length)}`;
  return `/${norm}`;
}

/** Every built HTML route under a dist dir, sorted — the discovered set (K0 NEW-4). */
export function discoverBuiltRoutes(distDir: string): string[] {
  const routes: string[] = [];
  const walk = (dir: string): void => {
    for (const item of readdirSync(dir, { withFileTypes: true })) {
      const full = join(dir, item.name);
      if (item.isDirectory()) {
        walk(full);
      } else if (item.name.endsWith(".html")) {
        routes.push(htmlFileToRoute(relative(distDir, full)));
      }
    }
  };
  if (existsSync(distDir)) walk(distDir);
  return routes.sort();
}

export interface ManifestRoute {
  path: string;
  file: string;
  type: PageType;
  pattern: string;
  owner: string;
  contract: string;
  chrome: string;
  internal: boolean;
}

export interface PageTypesManifest {
  schema: "sig.page-types-manifest/1";
  routes: ManifestRoute[];
}

export interface ClassifiedDist {
  routes: ManifestRoute[];
  errors: string[];
}

/** The `data-sig-chrome` kind a layout stamps on <html>, or "unmarked". */
export function chromeOf(html: string): string {
  return html.match(/data-sig-chrome="([^"]+)"/)?.[1] ?? "unmarked";
}

/**
 * Walk `dist` for `*.html` files and classify every built route. Returns the manifest
 * rows plus every failure (unclassified or doubly-classified) — the hook turns
 * a non-empty `errors` into a build failure.
 */
export function classifyDist(distDir: string): ClassifiedDist {
  const routes: ManifestRoute[] = [];
  const errors: string[] = [];
  for (const path of discoverBuiltRoutes(distDir)) {
    const result = classifyRoute(path);
    if (!result.ok) {
      if (result.kind === "unclassified") {
        errors.push(`unclassified route ${path} — add it to web/src/lib/page-types.ts before it ships`);
      } else {
        errors.push(
          `doubly-classified route ${path} — patterns ${result.patterns.join(", ")} tie; make one strictly more specific`,
        );
      }
      continue;
    }
    const rel = path.endsWith(".html")
      ? path.replace(/^\//, "")
      : `${path.replace(/^\//, "")}index.html`;
    const file = join(distDir, rel);
    const html = existsSync(file) ? readFileSync(file, "utf-8") : "";
    routes.push({
      path,
      file: rel.split(sep).join("/"),
      type: result.entry.type,
      pattern: result.pattern,
      owner: result.entry.owner,
      contract: result.entry.contract,
      chrome: chromeOf(html),
      internal: result.entry.internal === true,
    });
  }
  routes.sort((a, b) => a.path.localeCompare(b.path));
  return { routes, errors };
}

/** The manifest the sweeps read — deterministic (no clock, no absolute paths). */
export function buildManifest(routes: readonly ManifestRoute[]): PageTypesManifest {
  return {
    schema: "sig.page-types-manifest/1",
    routes: [...routes].sort((a, b) => a.path.localeCompare(b.path)),
  };
}

/** Write `dist/page-types.json` — the discovered-route manifest every sweep consumes. */
export function writeManifest(distDir: string, manifest: PageTypesManifest): string {
  const file = join(distDir, "page-types.json");
  writeFileSync(file, `${JSON.stringify(manifest, null, 2)}\n`);
  return file;
}
