// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * P37.24 (K2 GX-08a, `sig.graph-overview/1`) — the overview builder's web
 * mirror: the columnar decode, the per-compartment union (ADR-106), the
 * /graphs/ index model and the per-place slice. Every word the pages
 * render comes off the emitted artifact — a fact never comes from a
 * constant here.
 */

export const GRAPH_OVERVIEW_SCHEMA = "sig.graph-overview/1";
export const GRAPH_INDEX_SCHEMA = "sig.graph-index/1";

export interface OverviewNode {
  key: string;
  label: string;
  band: string;
  place: string | null;
  href: string | null;
  count: number;
  x: number;
  y: number;
}

export interface OverviewEdge {
  src: string;
  dst: string;
  relation: string;
  evidenceCount: number;
  date: string | null;
  dateKind: string;
  currency: string;
  sources: string[];
}

export interface GraphOverview {
  id: string;
  title: string;
  question: string;
  compartment: string;
  nodes: OverviewNode[];
  edges: OverviewEdge[];
  cap: number;
  capActions: string[];
  positionNote: string;
  erDisclosure: string;
  release: { label: string; asOf: string | null };
}

interface RawDoc {
  schema?: string;
  overview?: string;
  title?: string;
  question?: string;
  compartment?: string;
  dict?: Record<string, unknown[]>;
  nodes?: Record<string, unknown[]>;
  edges?: Record<string, unknown[]>;
  cap?: number;
  cap_actions?: string[];
  position_note?: string;
  er_disclosure?: string;
  release?: { label?: string; as_of_world?: string | null };
}

/** Decode one `sig.graph-overview/1` columnar doc — fail-closed on shape drift. */
export function decodeOverview(doc: unknown): GraphOverview {
  const d = doc as RawDoc;
  if (d?.schema !== GRAPH_OVERVIEW_SCHEMA)
    throw new Error(`not a ${GRAPH_OVERVIEW_SCHEMA} document`);
  const dict = d.dict ?? {};
  const at = (name: string, i: unknown): string | null => {
    const arr = dict[name] as unknown[] | undefined;
    const n = typeof i === "number" ? i : -1;
    return arr && n >= 0 && n < arr.length ? String(arr[n]) : null;
  };
  const N = d.nodes ?? {};
  const ids = (N.id ?? []) as string[];
  const nodes: OverviewNode[] = ids.map((id, i) => ({
    key: String(id),
    label: at("labels", (N.l ?? [])[i]) ?? "",
    band: at("kinds", (N.t ?? [])[i]) ?? "entity",
    place: at("places", (N.j ?? [])[i]),
    href: at("hrefs", (N.h ?? [])[i]),
    count: Number((N.n ?? [])[i] ?? 0),
    x: Number((N.x ?? [])[i] ?? 0),
    y: Number((N.y ?? [])[i] ?? 0),
  }));
  const E = d.edges ?? {};
  const ss = (E.s ?? []) as number[];
  const srcList = (E.src ?? []) as unknown[];
  const edges: OverviewEdge[] = ss.map((s, i) => {
    const srcs = srcList[i];
    return {
      src: ids[Number(s)] ?? "",
      dst: ids[Number((E.t ?? [])[i])] ?? "",
      relation: at("predicates", (E.p ?? [])[i]) ?? "",
      evidenceCount: Number((E.n ?? [])[i] ?? 0),
      date: at("dates", (E.y ?? [])[i]),
      dateKind: at("dates", (E.y ?? [])[i]) ? "observed" : "undated",
      currency: at("currency", (E.cur ?? [])[i]) ?? "undated",
      sources: Array.isArray(srcs)
        ? srcs.map((x) => at("sources", x) ?? "")
        : srcs != null
          ? [at("sources", srcs) ?? ""]
          : [],
    };
  });
  return {
    id: String(d.overview ?? ""),
    title: String(d.title ?? d.overview ?? ""),
    question: String(d.question ?? ""),
    compartment: String(d.compartment ?? ""),
    nodes,
    edges,
    cap: Number(d.cap ?? 0),
    capActions: (d.cap_actions ?? []).map(String),
    positionNote: String(d.position_note ?? ""),
    erDisclosure: String(d.er_disclosure ?? ""),
    release: {
      label: String(d.release?.label ?? ""),
      asOf: d.release?.as_of_world ? String(d.release.as_of_world) : null,
    },
  };
}

/** The ADR-106 union of one overview's per-compartment docs. */
export function mergeOverviews(docs: GraphOverview[]): GraphOverview | null {
  if (docs.length === 0) return null;
  const base = docs[0]!;
  const nodes = new Map<string, OverviewNode>();
  const edges = new Map<string, OverviewEdge>();
  for (const d of docs) {
    for (const n of d.nodes) if (!nodes.has(n.key)) nodes.set(n.key, n);
    for (const e of d.edges) {
      const k = `${e.src}${e.dst}${e.relation}`;
      const cur = edges.get(k);
      if (!cur) edges.set(k, { ...e });
      else {
        cur.evidenceCount = Math.max(cur.evidenceCount, e.evidenceCount);
        cur.sources = [...new Set([...cur.sources, ...e.sources])].sort();
      }
    }
  }
  return {
    ...base,
    compartment: docs.map((d) => d.compartment).join("+"),
    nodes: [...nodes.values()],
    edges: [...edges.values()],
    capActions: [...new Set(docs.flatMap((d) => d.capActions))],
  };
}

/** The overview's nodes + edges filtered to a place subtree (the
 *  `/graphs/<ov>/<country>/<sub>/` drill-down): a node belongs when its
 *  place key equals or descends from the prefix; an edge belongs when
 *  either endpoint belongs. */
export function overviewAtPlace(
  ov: GraphOverview,
  placeKey: string,
): { nodes: OverviewNode[]; edges: OverviewEdge[] } {
  const inPlace = (k: string | null) =>
    k === placeKey || (k != null && k.startsWith(`${placeKey}-`));
  const keys = new Set(ov.nodes.filter((n) => inPlace(n.place)).map((n) => n.key));
  return {
    nodes: ov.nodes.filter((n) => keys.has(n.key)),
    edges: ov.edges.filter((e) => keys.has(e.src) || keys.has(e.dst)),
  };
}

export interface GraphIndexEntry {
  id: string;
  title: string;
  question: string;
  nodes: number;
  edges: number;
  compartments: string[];
  places: string[];
}

export function decodeGraphIndex(doc: unknown): GraphIndexEntry[] {
  const d = doc as { schema?: string; overviews?: unknown[] };
  if (d?.schema !== GRAPH_INDEX_SCHEMA)
    throw new Error(`not a ${GRAPH_INDEX_SCHEMA} document`);
  return (d.overviews ?? []).map((o) => {
    const r = o as Record<string, unknown>;
    return {
      id: String(r.id ?? ""),
      title: String(r.title ?? ""),
      question: String(r.question ?? ""),
      nodes: Number(r.nodes ?? 0),
      edges: Number(r.edges ?? 0),
      compartments: (r.compartments ?? []) as string[],
      places: (r.places ?? []) as string[],
    };
  });
}
