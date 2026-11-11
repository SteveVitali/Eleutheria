// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * P37.27 (K2 GX-09b, `sig.workspace-state/2` graph scope; cites SIG-UI-059/060/
 * 119/120, SIG-RECON-049/050, ADR-155/242) — the graph explorer's pure second
 * wave: the filters, ego expansion, path finder and sortable node list the
 * `/explore/` island renders. Pure logic, no DOM — the whole contract is
 * unit-testable (`tests/unit/explore-graph.test.ts`) and the island is a
 * thin view over these functions.
 *
 * Honesty rules the island inherits by construction:
 *
 * - A filter only ever narrows what was emitted; the drop counts are
 *   returned so the UI can disclose them ("N undated edges sit outside the
 *   date range") — a filtered view never reads as the whole (H-3, H-9).
 * - Expansion composes the entity twin's `relations[].items[]` into the
 *   drawn graph, bounded by EXPAND_CAP expanded nodes and CANVAS_NODE_CAP
 *   total nodes; beyond the bound the answer is "open the entity page for
 *   the full list", never a silently truncated graph.
 * - The path finder answers over the LOADED graph only. A path lists every
 *   hop with its edge facts; > SPECULATIVE_HOPS is labelled speculative and
 *   is never a headline figure (SIG-UI-120); "no path in the loaded
 *   overview" is a typed answer — it never claims "not connected". On the
 *   access overview traversal uses the composing access edges only
 *   (SIG-RECON-049: an observed-use or declared-policy edge does not
 *   compose into reachability).
 * - Positions have no geographic meaning: expanded nodes are placed
 *   deterministically on a ring around their expanded node (index order,
 *   fixed radius — no PRNG, no layout pass).
 */

import type { EntityPageTwin, EntityRelationItem } from "./entity-page";
import { isEntityPageTwin } from "./entity-page";
import type { GraphOverview, OverviewEdge, OverviewNode } from "./graph-overview";

// ------------------------------------------------------------------ bounds

/** `expand=` may name at most this many nodes (K13 §2.5's ≤ 10). */
export const EXPAND_CAP = 10;
/** The canvas bound every expansion must respect (K2 §5.3's ≤ 3,000). */
export const CANVAS_NODE_CAP = 3000;
/** Publishable path length (SIG-UI-120); longer answers are speculative. */
export const SPECULATIVE_HOPS = 3;
/** The contract's per-relation item bound on a twin (K2 §6.2). */
export const EXPANSION_ITEM_CAP = 50;

/** `sig.entity-twins/1` — the per-entity manifest the expansion fetches at
 *  `<href>index.json`: the compartment twin files this release emitted for
 *  the entity (never a guessed filename, never a dead fetch). */
export const ENTITY_TWINS_SCHEMA = "sig.entity-twins/1";

export interface EntityTwinsIndex {
  schema: typeof ENTITY_TWINS_SCHEMA;
  key: string;
  twins: { compartment: string; path: string }[];
}

export function isEntityTwinsIndex(doc: unknown): doc is EntityTwinsIndex {
  const d = doc as Record<string, unknown> | null;
  return (
    typeof d === "object" &&
    d !== null &&
    d.schema === ENTITY_TWINS_SCHEMA &&
    Array.isArray(d.twins) &&
    d.twins.every(
      (t) =>
        typeof t === "object" &&
        t !== null &&
        typeof (t as { compartment?: unknown }).compartment === "string" &&
        typeof (t as { path?: unknown }).path === "string",
    )
  );
}

/** Join an emitted file name under an entity page href (the trailing-slash
 *  guard is the one boundary check the path builders share). */
export function twinPathHref(entityHref: string, path: string): string {
  return `${entityHref.endsWith("/") ? entityHref : `${entityHref}/`}${path}`;
}

/** The manifest URL under an entity page href (`/entity/<t>/<k>/` → `…/index.json`). */
export function twinIndexHref(entityHref: string): string {
  return twinPathHref(entityHref, "index.json");
}

/** The twin doc URL under an entity page href. */
export function twinDocHref(entityHref: string, compartment: string): string {
  return twinPathHref(entityHref, `index.${compartment}.json`);
}

// ------------------------------------------------------------------ filters

/** One jkey → place-prefix row the page serialises (canonical jkey, the
 *  overview doc's place-key prefix it resolves to, a display name). */
export interface JurisdictionPlace {
  jkey: string;
  /** The emitted place-key prefix (`usa`, `usa-ok`, …) — descendants match
   *  by the `-` subtree rule, the same one `overviewAtPlace` uses. */
  place: string;
  label: string;
}

/** The island's active filter set, decoded from the workspace state. Every
 *  field maps 1:1 onto registered parameters — nothing here invents a
 *  facet. */
export interface ExploreFilters {
  /** `kind=` — node bands to keep (empty = all). */
  kinds: string[];
  /** `edge=` — relation words to keep (empty = all). */
  relations: string[];
  /** `currency=` — the single currency class to keep (lowercase, or null). */
  currency: string | null;
  /** `dated=` — the decoded `YYYY[-MM]..YYYY[-MM]` range (or null). */
  dated: { from: string; to: string } | null;
  /** `source=` — source names to keep (empty = all). */
  sources: string[];
  /** `jurisdiction=` resolved to place prefixes via the emitted map. */
  jurisdictionPlaces: string[];
  /** `technology=` — technology facet values to keep (empty = all). */
  technologies: string[];
}

export const EMPTY_FILTERS: ExploreFilters = {
  kinds: [],
  relations: [],
  currency: null,
  dated: null,
  sources: [],
  jurisdictionPlaces: [],
  technologies: [],
};

/** Decode a `YYYY[-MM]..YYYY[-MM]` range string into a date window, or null
 *  (the parser already shape-validates; this compares string-lexically). */
export function datedRange(raw: string | null): { from: string; to: string } | null {
  if (raw === null) return null;
  const [from, to] = raw.split("..");
  if (!from || !to) return null;
  return { from, to };
}

/** A jkey param value → the place-key prefix it filters to, or null when
 *  the emitted map does not resolve it (named unresolvable, never guessed). */
export function jurisdictionPlaceFor(
  jkey: string,
  map: readonly JurisdictionPlace[],
): JurisdictionPlace | null {
  return map.find((r) => r.jkey === jkey) ?? null;
}

/** place ∈ subtree(placeKey): equal or a `-` descendant — `overviewAtPlace`'s rule. */
function placeInSubtree(place: string | null, prefix: string): boolean {
  return place === prefix || (place !== null && place.startsWith(`${prefix}-`));
}

/** A node's technology identity: the `tech:` key or its band, matched
 *  against the facet vocabulary (slug or label — both are emitted forms). */
function nodeTechnology(n: OverviewNode): string {
  return n.key.startsWith("tech:") ? n.key.slice(5) : n.label.toLowerCase();
}

/** The filtered view over a loaded graph, plus the disclosure counts the
 *  island renders. Node pass first, then edges (an edge needs both
 *  endpoints AND its own facets); a jurisdiction-matched edge keeps its
 *  other endpoint in view even when that endpoint's own place misses —
 *  the same "either endpoint" rule the static drill-down uses, so the
 *  filtered list and the canvas can never disagree. */
export function applyFilters(
  nodes: OverviewNode[],
  edges: OverviewEdge[],
  f: ExploreFilters,
): {
  nodes: OverviewNode[];
  edges: OverviewEdge[];
  droppedUndatedEdges: number;
  activeCount: number;
} {
  const activeCount =
    (f.kinds.length > 0 ? 1 : 0) +
    (f.relations.length > 0 ? 1 : 0) +
    (f.currency !== null ? 1 : 0) +
    (f.dated !== null ? 1 : 0) +
    (f.sources.length > 0 ? 1 : 0) +
    (f.jurisdictionPlaces.length > 0 ? 1 : 0) +
    (f.technologies.length > 0 ? 1 : 0);
  if (activeCount === 0) return { nodes, edges, droppedUndatedEdges: 0, activeCount };

  const kindSet = new Set(f.kinds);
  const relSet = new Set(f.relations);
  const srcSet = new Set(f.sources.map((s) => s.toLowerCase()));
  const techSet = new Set(f.technologies.map((t) => t.toLowerCase()));

  const nodePass = (n: OverviewNode): boolean => {
    if (kindSet.size > 0 && !kindSet.has(n.band)) return false;
    if (
      f.jurisdictionPlaces.length > 0 &&
      !f.jurisdictionPlaces.some((p) => placeInSubtree(n.place, p))
    ) {
      return false;
    }
    // A technology facet selects the named technology's ego: only a
    // matching tech node passes; every other node enters solely as the
    // context endpoint of a surviving edge.
    if (
      techSet.size > 0 &&
      !(
        n.band === "technology" &&
        (techSet.has(nodeTechnology(n).toLowerCase()) ||
          techSet.has(n.label.toLowerCase()))
      )
    ) {
      return false;
    }
    return true;
  };

  let droppedUndatedEdges = 0;
  const edgePass = (e: OverviewEdge): boolean => {
    if (relSet.size > 0 && !relSet.has(e.relation)) return false;
    if (f.currency !== null && e.currency.toLowerCase() !== f.currency) return false;
    if (f.dated !== null) {
      if (e.date === null || e.date < f.dated.from || e.date > f.dated.to) {
        if (e.date === null) droppedUndatedEdges += 1;
        return false;
      }
    }
    if (
      srcSet.size > 0 &&
      !e.sources.some((s) => srcSet.has(s.toLowerCase()))
    ) {
      return false;
    }
    return true;
  };

  const direct = new Set(nodes.filter(nodePass).map((n) => n.key));
  const keptEdges = edges.filter(
    (e) => edgePass(e) && (direct.has(e.src) || direct.has(e.dst)),
  );
  // Jurisdiction's "either endpoint" rule: an edge surviving on a matched
  // endpoint keeps its other endpoint in view (it would otherwise dangle).
  const keys = new Set(direct);
  for (const e of keptEdges) {
    keys.add(e.src);
    keys.add(e.dst);
  }
  return {
    nodes: nodes.filter((n) => keys.has(n.key)),
    edges: keptEdges.filter((e) => direct.has(e.src) || direct.has(e.dst)),
    droppedUndatedEdges,
    activeCount,
  };
}

// ---------------------------------------------------------------- expansion

/** The ego subgraph one twin contributes around `nodeKey`: relation items
 *  become counterparty nodes + edges (direction resolved, H-2 fields
 *  intact). A counterparty with a page gets its url; a literal or unpaged
 *  counterparty is still a node — its review_state is the twin's record of
 *  it. `more` counts surface separately (the cap note, never smoothed). */
export function egoFromTwin(
  twin: EntityPageTwin,
  nodeKey: string,
): { nodes: OverviewNode[]; edges: OverviewEdge[]; moreRelations: number } {
  const outNodes: OverviewNode[] = [];
  const outEdges: OverviewEdge[] = [];
  let moreRelations = 0;
  const seen = new Set<string>();
  for (const group of twin.relations) {
    moreRelations += group.more;
    for (const item of group.items.slice(0, EXPANSION_ITEM_CAP)) {
      const cp = item.counterparty;
      const cpKey = `e:${cp.key ?? cp.entity_id ?? `${item.relation}:${cp.label ?? "unnamed"}`}`;
      if (!seen.has(cpKey) && cpKey !== nodeKey) {
        seen.add(cpKey);
        outNodes.push({
          key: cpKey,
          label: cp.label ?? "Unnamed",
          band: cp.kind ?? "entity",
          place: null,
          href: cp.url ?? null,
          count: 0,
          x: 0,
          y: 0,
        });
      }
      const outbound = group.direction !== "inbound";
      outEdges.push({
        src: outbound ? nodeKey : cpKey,
        dst: outbound ? cpKey : nodeKey,
        relation: item.relation,
        evidenceCount: item.claim_ids.length,
        memberCount: 0,
        date: item.date,
        dateKind: item.date_kind,
        currency: item.currency ?? "undated",
        sources: item.sources.map((s) => s.name ?? s.id),
      });
    }
  }
  return { nodes: outNodes, edges: outEdges, moreRelations };
}

/** Deterministic ring placement for expansion nodes: index order around
 *  the expanded node's emitted position (no PRNG, no layout meaning — the
 *  position note already discloses). */
export function ringPosition(
  center: { x: number; y: number },
  index: number,
  total: number,
  radius = 90,
): { x: number; y: number } {
  const angle = (2 * Math.PI * index) / Math.max(1, total);
  return { x: center.x + radius * Math.cos(angle), y: center.y + radius * Math.sin(angle) };
}

/** Merge expansion nodes+edges into the working graph (dedup by key /
 *  src+dst+relation — a node already drawn is never doubled). Returns the
 *  merged copies; the inputs are never mutated. */
export function mergeEgo(
  nodes: OverviewNode[],
  edges: OverviewEdge[],
  ego: { nodes: OverviewNode[]; edges: OverviewEdge[] },
  anchor: OverviewNode | undefined,
): { nodes: OverviewNode[]; edges: OverviewEdge[] } {
  const outNodes = [...nodes];
  const keys = new Set(nodes.map((n) => n.key));
  const fresh = ego.nodes.filter((n) => !keys.has(n.key));
  fresh.forEach((n, i) => {
    const pos = anchor ? ringPosition(anchor, i, fresh.length) : { x: n.x, y: n.y };
    outNodes.push({ ...n, x: pos.x, y: pos.y });
    keys.add(n.key);
  });
  const edgeKeys = new Set(edges.map((e) => `${e.src}${e.dst}${e.relation}`));
  const outEdges = [...edges];
  for (const e of ego.edges) {
    const k = `${e.src}${e.dst}${e.relation}`;
    if (edgeKeys.has(k)) continue;
    edgeKeys.add(k);
    outEdges.push(e);
  }
  return { nodes: outNodes, edges: outEdges };
}

export { isEntityPageTwin };

// ----------------------------------------------------------------- sorting

export type NodeSort = "label" | "kind" | "place" | "count";
export const NODE_SORTS: readonly NodeSort[] = ["label", "kind", "place", "count"];

export function isNodeSort(v: string | null): v is NodeSort {
  return v !== null && (NODE_SORTS as readonly string[]).includes(v);
}

/** The descriptive sort of the keyboard list (K2 §5.3 — label, kind,
 *  place, relationship count; never a ranking statistic). */
export function sortNodes(
  nodes: OverviewNode[],
  edges: OverviewEdge[],
  sort: NodeSort | null,
  dir: "asc" | "desc" | null,
): OverviewNode[] {
  if (sort === null) return nodes;
  const degree = new Map<string, number>();
  for (const e of edges) {
    degree.set(e.src, (degree.get(e.src) ?? 0) + 1);
    degree.set(e.dst, (degree.get(e.dst) ?? 0) + 1);
  }
  const sign = dir === "desc" ? -1 : 1;
  const key = (n: OverviewNode): string | number => {
    switch (sort) {
      case "kind":
        return n.band;
      case "place":
        return n.place ?? "";
      case "count":
        return degree.get(n.key) ?? 0;
      default:
        return n.label.toLowerCase();
    }
  };
  return [...nodes].sort((a, b) => {
    const ka = key(a);
    const kb = key(b);
    const c =
      typeof ka === "number" && typeof kb === "number"
        ? ka - kb
        : String(ka).localeCompare(String(kb));
    return c !== 0 ? sign * c : a.key.localeCompare(b.key);
  });
}

// ------------------------------------------------------------ neighbourhood

/** The node keys within `hops` edges of `focus` (BFS, undirected — the ego
 *  neighbourhood the `hops=` control scopes to). */
export function neighbourhood(
  nodes: OverviewNode[],
  edges: OverviewEdge[],
  focus: string,
  hops: number,
): Set<string> {
  const adj = new Map<string, string[]>();
  const push = (a: string, b: string) => {
    const l = adj.get(a) ?? [];
    l.push(b);
    adj.set(a, l);
  };
  for (const e of edges) {
    push(e.src, e.dst);
    push(e.dst, e.src);
  }
  const seen = new Set<string>([focus]);
  let ring = [focus];
  for (let i = 0; i < hops; i += 1) {
    const next: string[] = [];
    for (const k of ring) {
      for (const n of adj.get(k) ?? []) {
        if (!seen.has(n)) {
          seen.add(n);
          next.push(n);
        }
      }
    }
    ring = next;
  }
  return seen;
}

// ---------------------------------------------------------------- the path

/** The relations an access-question traversal may compose through
 *  (SIG-RECON-049): configured-access edges only — an observed-use or
 *  declared-policy edge never composes into reachability. */
export const ACCESS_COMPOSING_RELATIONS = ["configured access to"] as const;

export interface PathHop {
  from: string;
  to: string;
  edge: OverviewEdge;
}

export interface PathResult {
  kind: "path" | "no-path" | "missing-endpoint";
  hops: PathHop[];
  /** > SPECULATIVE_HOPS — labelled, never a headline. */
  speculative: boolean;
  missing?: string;
}

/** BFS shortest path over the loaded graph (undirected — "how is X
 *  connected to Y"). `composingOnly` restricts traversal to the
 *  configured-access relations (the access overview's reachability
 *  question); every hop still carries its full edge facts. */
export function shortestPath(
  nodes: OverviewNode[],
  edges: OverviewEdge[],
  src: string,
  dst: string,
  opts: { composingOnly?: boolean } = {},
): PathResult {
  const keys = new Set(nodes.map((n) => n.key));
  if (!keys.has(src)) return { kind: "missing-endpoint", hops: [], speculative: false, missing: src };
  if (!keys.has(dst)) return { kind: "missing-endpoint", hops: [], speculative: false, missing: dst };
  if (src === dst) return { kind: "path", hops: [], speculative: false };

  const adj = new Map<string, { next: string; edge: OverviewEdge }[]>();
  const push = (a: string, b: string, edge: OverviewEdge) => {
    const l = adj.get(a) ?? [];
    l.push({ next: b, edge });
    adj.set(a, l);
  };
  for (const e of edges) {
    if (opts.composingOnly && !(ACCESS_COMPOSING_RELATIONS as readonly string[]).includes(e.relation)) {
      continue;
    }
    push(e.src, e.dst, e);
    push(e.dst, e.src, e);
  }
  const prev = new Map<string, { from: string; edge: OverviewEdge }>();
  const queue = [src];
  const seen = new Set([src]);
  while (queue.length > 0 && !seen.has(dst)) {
    const cur = queue.shift()!;
    for (const { next, edge } of adj.get(cur) ?? []) {
      if (seen.has(next)) continue;
      seen.add(next);
      prev.set(next, { from: cur, edge });
      queue.push(next);
      if (next === dst) break;
    }
  }
  if (!seen.has(dst)) return { kind: "no-path", hops: [], speculative: false };
  const hops: PathHop[] = [];
  let cur = dst;
  while (cur !== src) {
    const p = prev.get(cur)!;
    hops.unshift({ from: p.from, to: cur, edge: p.edge });
    cur = p.from;
  }
  return { kind: "path", hops, speculative: hops.length > SPECULATIVE_HOPS };
}

/** `path=<a>~<b>` → the endpoint pair (the registry shape, decoded). */
export function pathPair(raw: string | null): { a: string; b: string } | null {
  if (raw === null) return null;
  const parts = raw.split("~");
  if (parts.length !== 2 || parts[0] === "" || parts[1] === "") return null;
  return { a: parts[0]!, b: parts[1]! };
}

// ------------------------------------------------------------ search-to-node

/** Overview nodes whose label mentions the query (word-prefix first —
 *  the same ranking rule the typeahead matcher uses). */
export function searchGraphNodes(
  nodes: OverviewNode[],
  q: string,
): OverviewNode[] {
  const query = q.trim().toLowerCase();
  if (query === "") return [];
  const score = (n: OverviewNode): number => {
    const l = n.label.toLowerCase();
    if (l.split(/\s+/).some((w) => w.startsWith(query))) return 0;
    return l.includes(query) ? 1 : -1;
  };
  return nodes
    .map((n, i) => ({ n, i, s: score(n) }))
    .filter((x) => x.s >= 0)
    .sort((a, b) => a.s - b.s || a.i - b.i)
    .map((x) => x.n);
}

/** `/entity/` route-class check on an emitted href — a prefix guard, never
 *  a link construction (the island re-bases through `withBase`). */
export function isEntityHref(href: string | null): href is string {
  return href !== null && href.startsWith("/entity/");
}

/** The entity hrefs a twin/ego fetch may follow — `/entity/` links only
 *  (a /graphs/ or /dossier/ href is never a machine-readable twin). */
export function entityHrefOf(node: OverviewNode): string | null {
  return isEntityHref(node.href) ? node.href : null;
}

export type { GraphOverview, OverviewEdge, OverviewNode, EntityPageTwin };
