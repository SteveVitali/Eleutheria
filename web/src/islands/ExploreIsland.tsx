// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * The interactive graph explorer — the `/explore/` T2 surface (P37.26/27,
 * K2 GX-09a/b; ADR-155's named T2 graph over the `/graphs/**` no-JS
 * equivalent; ADR-242 for the sigma/graphology browser-runtime seats).
 *
 * PROGRESSIVE ENHANCEMENT, NOT REPLACEMENT (SIG-UI-050): the island mounts
 * a **Preact + sigma** renderer inside the reserved SSR box and loads the
 * emitted `sig.graph-overview/1` docs over the wire; the overview index, the
 * static figure + adjacency preview, the access-edge lists and the
 * precomputed path hop lists below it carry the same facts with JS off and
 * are never removed.
 *
 * 09b scope (P37.27): expansion (`expand=` fetches the entity twin via the
 * `sig.entity-twins/1` manifest — ≤ 10 expanded nodes, ≤ 3,000 on canvas,
 * then "open the entity page for the full list"), the facet filters
 * (`kind`/`edge`/`currency`/`dated`/`source`/`jurisdiction`/`technology`/
 * `collection`), search-to-node (`q=` over the loaded graph + the shared
 * typeahead shards for entities outside the overview), the path finder
 * (`path=<a>~<b>` — BFS over the loaded graph, every hop evidenced, >3
 * hops SPECULATIVE, "no path" a typed answer — SIG-UI-120), the `hops=`
 * neighbourhood ring, and the sortable keyboard node list (`sort`/`dir`).
 * A parameter the surface still cannot apply renders the SIG-UI-060
 * notice — never silently dropped, never presented as a filter that held.
 *
 * Honest rendering: node positions come verbatim off the emitted doc
 * (expansion nodes sit on a deterministic ring — no PRNG); a `focus=` or
 * `expand=` naming nothing here is reported, never fabricated; no
 * centrality or hub ranking renders (SIG-UI-121).
 */

/** @jsxImportSource preact */
import { useEffect, useMemo, useRef, useState } from "preact/hooks";
import type { JSX } from "preact";
import Graph from "graphology";
import Sigma from "sigma";
import {
  decodeOverview,
  mergeOverviews,
} from "../lib/graph-overview";
import type { GraphOverview, OverviewEdge, OverviewNode } from "../lib/graph-overview";
import {
  applyFilters,
  CANVAS_NODE_CAP,
  datedRange,
  egoFromTwin,
  entityHrefOf,
  EXPAND_CAP,
  isEntityPageTwin,
  isEntityTwinsIndex,
  isNodeSort,
  jurisdictionPlaceFor,
  mergeEgo,
  neighbourhood,
  NODE_SORTS,
  pathPair,
  searchGraphNodes,
  shortestPath,
  sortNodes,
  SPECULATIVE_HOPS,
  twinIndexHref,
  type ExploreFilters,
  type JurisdictionPlace,
} from "../lib/explore-graph";
import {
  citeViewHref,
  facetNoticeText,
  INTERIM_CITE_VIEW_TEXT,
  ISLAND_VIEWS,
  recordRoutes,
  viewHref,
} from "../lib/workspace-state/index";
import { matchEntries, shardKey } from "../elements/typeahead-model";
import type { TypeaheadShard } from "../elements/typeahead-model";
import { withBase } from "../lib/paths";
import { useMapWorkspace } from "./map/workspace";

/** One `sig.graph-index/1` row as the page passes it — doc hrefs already
 *  withBase'd (the overview loads its emitted bytes verbatim). */
export interface ExploreOverviewEntry {
  id: string;
  title: string;
  question: string;
  nodes: number;
  edges: number;
  docs: { compartment: string; href: string }[];
  /** The static `/graphs/<ov>/` page — the same overview's no-JS form. */
  pageHref: string;
}

export interface ExploreIslandProps {
  overviews: ExploreOverviewEntry[];
  /** The overview an address without `overview=` opens on (`access` — the
   *  `/network/` successor view). */
  defaultOverview: string;
  /** The latest activated publication id for this build, or null (none). */
  release: string | null;
  /** The jkey → place-prefix resolution map (`jurisdiction=` honours the
   *  registry's descendants-inclusive rule over the docs' place keys). */
  jurisdictionPlaces: JurisdictionPlace[];
  /** The emitted typeahead shard root (search-to-node shares K3's set). */
  shardRoot: string;
}

const VIEW_LABELS: Record<string, string> = {
  list: "List",
  map: "Map",
  network: "Connections",
};

// Entity kind = shape in the K13 C-01 lexicon; sigma's default program
// draws circles, so the island differentiates by size + ink — the static
// SVG on the /graphs/ pages carries the full shape vocabulary and this
// palette stays muted-ink honest (colour is never the only channel).
const BAND_COLOURS: Record<string, string> = {
  agency: "#1f4e79",
  vendor: "#7a3b0f",
  org: "#7a3b0f",
  technology: "#3d6b35",
  instrument: "#5b2d8e",
  kind: "#4a4a4a",
  place: "#8a6d1d",
  group: "#666666",
};
const SELECT_COLOUR = "#b3261e";
const PATH_COLOUR = "#8a6d1d";
const EDGE_CURRENT = "#5a5a5a";
const EDGE_MUTED = "#b9b3ac"; // historical / undated — muted ink (C-01)

function bandColour(band: string): string {
  return BAND_COLOURS[band] ?? "#4a4a4a";
}
function nodeSize(n: OverviewNode): number {
  return 5 + Math.min(9, Math.sqrt(Math.max(0, n.count)));
}
function edgeColour(e: OverviewEdge): string {
  return e.currency === "CURRENT" || e.currency === "AGING"
    ? EDGE_CURRENT
    : EDGE_MUTED;
}
function hrefOf(href: string): string {
  return withBase(href.replace(/^\//, ""));
}
const CURRENCIES = ["current", "aging", "stale", "historical", "undated"] as const;

interface EgoLoad {
  status: "loading" | "ready" | "missing" | "error";
  nodes: OverviewNode[];
  edges: OverviewEdge[];
  more: number;
  note: string | null;
}

export default function ExploreIsland({
  overviews,
  defaultOverview,
  release,
  jurisdictionPlaces,
  shardRoot,
}: ExploreIslandProps): JSX.Element {
  const { state, issues, ignored, update } = useMapWorkspace("network", { release });

  // --- overview loading ------------------------------------------------
  const requestedOverview = state.overview;
  const entry =
    overviews.find((o) => o.id === requestedOverview) ??
    overviews.find((o) => o.id === defaultOverview) ??
    overviews[0] ??
    null;
  const overviewMiss =
    requestedOverview !== null && entry !== null && requestedOverview !== entry.id;
  const overviewId = entry?.id ?? null;

  // `collection=` selects the compartment docs the union loads (G-5 — a
  // named compartment that is not among this overview's files is a typed
  // empty answer, never a silently different union).
  const selectedDocs = useMemo(
    () =>
      (entry?.docs ?? []).filter(
        (d) => !state.collectionSpecified || state.collection.includes(d.compartment),
      ),
    [entry, state.collectionSpecified, state.collection],
  );
  const collectionEmpty =
    state.collectionSpecified && entry !== null && selectedDocs.length === 0;

  const [doc, setDoc] = useState<GraphOverview | null>(null);
  const [loadState, setLoadState] = useState<"loading" | "error" | "ready">("loading");
  const [loadError, setLoadError] = useState<string>("");

  useEffect(() => {
    if (entry === null || selectedDocs.length === 0) {
      setDoc(null);
      setLoadState(selectedDocs.length === 0 ? "ready" : "loading");
      return;
    }
    let cancelled = false;
    setDoc(null);
    setLoadError("");
    setLoadState("loading");
    Promise.all(
      selectedDocs.map((d) =>
        fetch(d.href)
          .then((r) => {
            if (!r.ok) throw new Error(`${d.href} answered ${r.status}`);
            return r.json() as Promise<unknown>;
          })
          .then(decodeOverview),
      ),
    )
      .then((docs) => {
        if (cancelled) return;
        setDoc(mergeOverviews(docs));
        setLoadState("ready");
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setLoadError(err instanceof Error ? err.message : String(err));
        setLoadState("error");
      });
    return () => {
      cancelled = true;
    };
  }, [overviewId, entry, selectedDocs]);

  // --- expansion (expand= → the entity twin's ego) ----------------------
  const [egos, setEgos] = useState<Map<string, EgoLoad>>(new Map());
  const pendingEgos = useRef<Set<string>>(new Set());

  const loadEgo = (
    key: string,
    href: string | null,
    label: string,
    selfNode: OverviewNode | null = null,
  ) => {
    if (pendingEgos.current.has(key)) return;
    if (href === null || !href.startsWith("/entity/")) {
      setEgos((m) =>
        new Map(m).set(key, {
          status: "missing",
          nodes: [],
          edges: [],
          more: 0,
          note: `${label} has no entity page — there is no machine-readable twin to expand.`,
        }),
      );
      return;
    }
    pendingEgos.current.add(key);
    setEgos((m) =>
      new Map(m).set(key, { status: "loading", nodes: [], edges: [], more: 0, note: null }),
    );
    const fail = (note: string) =>
      setEgos((m) =>
        new Map(m).set(key, { status: "error", nodes: [], edges: [], more: 0, note }),
      );
    fetch(hrefOf(twinIndexHref(href)))
      .then((r) => {
        if (!r.ok) throw new Error("no-manifest");
        return r.json() as Promise<unknown>;
      })
      .then((manifest) => {
        if (!isEntityTwinsIndex(manifest) || manifest.twins.length === 0) {
          throw new Error("no-manifest");
        }
        return Promise.all(
          manifest.twins.map((t) =>
            fetch(hrefOf(`${href.endsWith("/") ? href : `${href}/`}${t.path}`))
              .then((r) => {
                if (!r.ok) throw new Error(`twin answered ${r.status}`);
                return r.json() as Promise<unknown>;
              }),
          ),
        );
      })
      .then((twinDocs) => {
        const merged = { nodes: [] as OverviewNode[], edges: [] as OverviewEdge[], more: 0 };
        // A searched entity outside the overview contributes its own node
        // first — the ego edges then resolve against a real node, never a
        // dangling key.
        if (selfNode !== null) merged.nodes.push(selfNode);
        for (const td of twinDocs) {
          if (!isEntityPageTwin(td)) continue;
          const ego = egoFromTwin(td, key);
          const cur = mergeEgo(merged.nodes, merged.edges, ego, undefined);
          merged.nodes = cur.nodes;
          merged.edges = cur.edges;
          merged.more += ego.moreRelations;
        }
        pendingEgos.current.delete(key);
        setEgos((m) =>
          new Map(m).set(key, { status: "ready", ...merged, note: null }),
        );
      })
      .catch(() => {
        pendingEgos.current.delete(key);
        fail(
          `${label} has no machine-readable twin in this release — its relationships live on the entity page.`,
        );
      });
  };

  // The working graph = the overview doc ∪ every loaded ego (bounded).
  const expandedKeys = useMemo(() => [...egos.entries()].filter(([, e]) => e.status === "ready").map(([k]) => k), [egos]);
  const merged = useMemo(() => {
    if (doc === null) return null;
    let g: { nodes: OverviewNode[]; edges: OverviewEdge[] } = { nodes: doc.nodes, edges: doc.edges };
    const nodeBy = new Map(g.nodes.map((n) => [n.key, n]));
    for (const key of expandedKeys) {
      const ego = egos.get(key)!;
      g = mergeEgo(g.nodes, g.edges, ego, nodeBy.get(key));
      for (const n of g.nodes) nodeBy.set(n.key, n);
    }
    return g;
  }, [doc, expandedKeys, egos]);
  const expansionCount = expandedKeys.length;
  const expandCapHit = state.expand.length >= EXPAND_CAP;
  const canvasCapHit = merged !== null && merged.nodes.length > CANVAS_NODE_CAP;

  // expand= requests ride the URL; honour each named node once the doc is in.
  useEffect(() => {
    if (doc === null || merged === null) return;
    const byKey = new Map(merged.nodes.map((n) => [n.key, n]));
    for (const key of state.expand.slice(0, EXPAND_CAP)) {
      if (egos.has(key) || pendingEgos.current.has(key)) continue;
      const node = byKey.get(key);
      if (node) {
        loadEgo(key, entityHrefOf(node), node.label);
      } else {
        setEgos((m) =>
          new Map(m).set(key, {
            status: "missing",
            nodes: [],
            edges: [],
            more: 0,
            note: `The expanded node "${key}" is not in this overview — the expansion does not apply here.`,
          }),
        );
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [doc, merged, state.expand]);

  // --- selection --------------------------------------------------------
  const focusId = state.focus;
  const [edgeSel, setEdgeSel] = useState<number | null>(null);
  useEffect(() => setEdgeSel(null), [overviewId, focusId]);

  // --- filters ----------------------------------------------------------
  const filters: ExploreFilters = useMemo(() => {
    const unresolvedJ = state.jurisdiction.filter(
      (j) => jurisdictionPlaceFor(j, jurisdictionPlaces) === null,
    );
    void unresolvedJ;
    return {
      kinds: state.kind,
      relations: state.edge,
      currency: state.currency,
      dated: datedRange(state.dated),
      sources: state.source,
      jurisdictionPlaces: state.jurisdiction
        .map((j) => jurisdictionPlaceFor(j, jurisdictionPlaces)?.place ?? null)
        .filter((p): p is string => p !== null),
      technologies: state.technology,
    };
  }, [state, jurisdictionPlaces]);
  const unresolvedJurisdictions = state.jurisdiction.filter(
    (j) => jurisdictionPlaceFor(j, jurisdictionPlaces) === null,
  );
  const filtered = useMemo(
    () => (merged ? applyFilters(merged.nodes, merged.edges, filters) : null),
    [merged, filters],
  );
  // `hops=` scopes the drawn neighbourhood around the focused node (K13
  // §2.5's 1|2 ring); absent focus it simply has nothing to scope yet.
  const scoped = useMemo(() => {
    if (filtered === null) return null;
    if (state.hops !== null && focusId !== null && filtered.nodes.some((n) => n.key === focusId)) {
      const ring = neighbourhood(filtered.nodes, filtered.edges, focusId, state.hops);
      return {
        nodes: filtered.nodes.filter((n) => ring.has(n.key)),
        edges: filtered.edges.filter((e) => ring.has(e.src) && ring.has(e.dst)),
      };
    }
    return { nodes: filtered.nodes, edges: filtered.edges };
  }, [filtered, state.hops, focusId]);

  const nodeByKey = useMemo(
    () => new Map((merged?.nodes ?? []).map((n) => [n.key, n])),
    [merged],
  );
  const focusNode = focusId !== null ? (nodeByKey.get(focusId) ?? null) : null;
  const focusMiss = focusId !== null && merged !== null && !nodeByKey.has(focusId);
  const focusRoutes = useMemo(() => {
    const rel = state.release ?? release;
    return rel && focusMiss ? recordRoutes(rel, focusId) : null;
  }, [state.release, release, focusMiss, focusId]);

  // --- the sortable node list ------------------------------------------
  const sort = isNodeSort(state.sort) ? state.sort : null;
  const listNodes = useMemo(
    () => (scoped ? sortNodes(scoped.nodes, scoped.edges, sort, state.dir) : []),
    [scoped, sort, state.dir],
  );

  // --- path finder ------------------------------------------------------
  const pair = pathPair(state.path);
  const pathResult = useMemo(() => {
    if (pair === null || filtered === null) return null;
    const composingOnly = doc?.id === "access";
    return shortestPath(filtered.nodes, filtered.edges, pair.a, pair.b, { composingOnly });
  }, [pair, filtered, doc?.id]);
  const pathEdgeIdx = useMemo(() => {
    const set = new Set<number>();
    if (pathResult?.kind === "path" && filtered) {
      for (const h of pathResult.hops) {
        const i = filtered.edges.indexOf(h.edge);
        if (i >= 0) set.add(i);
      }
    }
    return set;
  }, [pathResult, filtered]);
  const [pathFrom, setPathFrom] = useState<string | null>(null);

  // --- search-to-node ---------------------------------------------------
  const q = state.q;
  const nodeMatches = useMemo(() => (merged ? searchGraphNodes(merged.nodes, q) : []), [merged, q]);
  const [shardMatches, setShardMatches] = useState<{ label: string; href: string; kind?: string; detail?: string }[]>([]);
  useEffect(() => {
    const key = shardKey(q);
    if (key === null || q.trim().length < 2) {
      setShardMatches([]);
      return;
    }
    let cancelled = false;
    fetch(withBase(`${shardRoot}${key}.json`))
      .then((r) => (r.ok ? (r.json() as Promise<unknown>) : null))
      .then((d) => {
        if (cancelled || d === null || (d as TypeaheadShard).schema !== "sig.typeahead-shard/1") return;
        setShardMatches(matchEntries((d as TypeaheadShard).entries, q).slice(0, 8));
      })
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, [q, shardRoot]);

  // --- sigma mount ------------------------------------------------------
  const containerRef = useRef<HTMLDivElement>(null);
  const sigmaRef = useRef<Sigma | null>(null);
  const graphRef = useRef<Graph | null>(null);
  useEffect(() => {
    const container = containerRef.current;
    if (!container || scoped === null) return;
    const g = new Graph();
    for (const n of scoped.nodes) {
      g.addNode(n.key, {
        x: n.x,
        y: -n.y,
        label: n.label,
        size: nodeSize(n),
        color: bandColour(n.band),
      });
    }
    scoped.edges.forEach((e, i) => {
      if (!g.hasNode(e.src) || !g.hasNode(e.dst)) return;
      g.addEdgeWithKey(`e${i}`, e.src, e.dst, {
        size: Math.min(4, 1 + Math.log2(1 + e.evidenceCount) / 2),
        color: edgeColour(e),
      });
    });
    const sigma = new Sigma(g, container, {
      allowInvalidContainer: true,
      renderEdgeLabels: false,
      labelRenderedSizeThreshold: 7,
    });
    sigma.on("clickNode", ({ node }) => {
      if (pathFrom !== null && node !== pathFrom) {
        update({ path: `${pathFrom}~${node}`, focus: null });
        setPathFrom(null);
      } else {
        update({ focus: node });
      }
    });
    sigma.on("clickEdge", ({ edge }) =>
      setEdgeSel(Number(String(edge).slice(1))),
    );
    sigma.on("clickStage", () => setEdgeSel(null));
    sigmaRef.current = sigma;
    graphRef.current = g;
    return () => {
      sigma.kill();
      sigmaRef.current = null;
      graphRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [scoped, pathFrom]);

  // Selection + path restyle — attribute updates + refresh, never a rebuild.
  useEffect(() => {
    const g = graphRef.current;
    const sigma = sigmaRef.current;
    if (!g || !sigma || scoped === null) return;
    for (const n of scoped.nodes) {
      if (!g.hasNode(n.key)) continue;
      g.setNodeAttribute(n.key, "size", nodeSize(n) + (n.key === focusId ? 3 : 0));
      g.setNodeAttribute(n.key, "color", n.key === focusId ? SELECT_COLOUR : bandColour(n.band));
    }
    scoped.edges.forEach((e, i) => {
      const key = `e${i}`;
      if (!g.hasEdge(key)) return;
      g.setEdgeAttribute(
        key,
        "color",
        i === edgeSel ? SELECT_COLOUR : pathEdgeIdx.has(i) ? PATH_COLOUR : edgeColour(e),
      );
    });
    sigma.refresh();
  }, [scoped, focusId, edgeSel, pathEdgeIdx]);

  const labelOf = (key: string): string => nodeByKey.get(key)?.label ?? key;
  const selEdge: OverviewEdge | null =
    scoped !== null && edgeSel !== null ? (scoped.edges[edgeSel] ?? null) : null;

  const switchOverview = (id: string) =>
    update({ overview: id, focus: null, expand: [], path: null }, "push");

  const citeForm = release ? citeViewHref(release, "graph", state) : null;
  const toggleIn = (list: string[], v: string) =>
    list.includes(v) ? list.filter((x) => x !== v) : [...list, v];

  const nodeNeighbours = (key: string): OverviewEdge[] =>
    (scoped?.edges ?? []).filter((e) => e.src === key || e.dst === key);

  const distinct = <T,>(xs: T[]): T[] => [...new Set(xs)];
  const bands = distinct((merged?.nodes ?? []).map((n) => n.band)).sort();
  const relations = distinct((merged?.edges ?? []).map((e) => e.relation)).sort();
  const sourceNames = distinct((merged?.edges ?? []).flatMap((e) => e.sources)).sort();
  const docJurisdictions = jurisdictionPlaces.filter((jp) =>
    (merged?.nodes ?? []).some((n) => n.place === jp.place || (n.place ?? "").startsWith(`${jp.place}-`)),
  );

  const pickNodeForPath = (key: string) => {
    if (pathFrom === null) {
      setPathFrom(key);
    } else if (pathFrom !== key) {
      update({ path: `${pathFrom}~${key}`, focus: null });
      setPathFrom(null);
    } else {
      setPathFrom(null);
    }
  };

  return (
    <div
      data-testid="explore-island"
      onKeyDown={(e) => {
        if (e.key === "Escape") {
          if (pathFrom !== null) setPathFrom(null);
          else if (selEdge !== null) setEdgeSel(null);
          else if (focusId !== null) update({ focus: null });
        }
      }}
    >
      <nav className="sig-view-links" aria-label="Investigation views" data-testid="island-view-links">
        {ISLAND_VIEWS.map((v) =>
          v === state.view ? (
            <strong key={v} aria-current="page">{VIEW_LABELS[v]}</strong>
          ) : (
            <a key={v} href={viewHref(state, v)} data-testid={`view-link-${v}`}>
              {VIEW_LABELS[v]}
            </a>
          ),
        )}
      </nav>
      {issues.length > 0 && (
        <p className="sig-island__note" role="status" data-testid="workspace-issues">
          {issues.join(" ")}
        </p>
      )}
      {ignored.length > 0 && (
        <p className="sig-island__note" role="status" data-testid="facet-not-applied">
          {facetNoticeText(ignored)}
        </p>
      )}
      {state.release && (
        <p className="sig-island__note" data-testid="workspace-release">
          Release <code>{state.release}</code>
        </p>
      )}
      {overviewMiss && entry !== null && (
        <p className="sig-island__note" role="status" data-testid="explore-overview-miss">
          The address names the overview <code>{requestedOverview}</code>, which this build
          does not publish — showing {entry.title.toLowerCase()} instead.
        </p>
      )}
      {citeForm !== null && (
        <p className="sig-island__note" data-testid="cite-this-view-live">
          <strong>Cite this view.</strong> The snapshot-pinned form is{" "}
          <code data-testid="cite-form">{citeForm}</code>. {INTERIM_CITE_VIEW_TEXT}
        </p>
      )}

      {overviews.length > 1 && (
        <ul className="sig-explore-picker" data-testid="overview-picker" aria-label="Overview graphs">
          {overviews.map((o) => (
            <li key={o.id}>
              <button
                type="button"
                className="sig-explore-picker__btn"
                data-testid="overview-pick"
                data-overview={o.id}
                aria-pressed={o.id === overviewId}
                onClick={() => switchOverview(o.id)}
              >
                {o.title}
                <span className="sig-search-island__kind">
                  {" "}— {o.nodes} nodes, {o.edges} edges
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}

      {loadState === "loading" && (
        <p className="sig-island__note" role="status" data-testid="explore-loading">
          Loading the {entry?.title ?? "overview"} graph…
        </p>
      )}
      {loadState === "error" && (
        <p className="sig-island__note" role="alert" data-testid="explore-load-error">
          The {entry?.title ?? "overview"} data file could not be loaded ({loadError}) —
          the same graph is published statically at{" "}
          {entry !== null && <a href={entry.pageHref}>{entry.pageHref}</a>}.
        </p>
      )}
      {collectionEmpty && (
        <p className="sig-island__note" role="status" data-testid="explore-collection-empty">
          The compartment selection names none of this overview's data files — no
          document loads. The static pages list every compartment's file.
        </p>
      )}
      {focusMiss && (
        <p className="sig-island__note" role="status" data-testid="graph-focus-miss">
          <code>{focusId}</code> is not in the {entry?.title ?? "overview"} view — the
          selection does not apply here.
          {focusRoutes ? (
            <>
              {" "}
              <a href={focusRoutes.pageHref} data-testid="focus-record-link">
                Open the released record
              </a>
              .
            </>
          ) : null}
        </p>
      )}
      {unresolvedJurisdictions.length > 0 && (
        <p className="sig-island__note" role="status" data-testid="explore-jurisdiction-miss">
          The jurisdiction{" "}
          {unresolvedJurisdictions.map((j) => <code key={j}>{j}</code>)}{" "}
          names no place this release keys — it does not filter what is shown.
        </p>
      )}
      {filtered !== null && filtered.activeCount > 0 && (
        <p className="sig-island__note" data-testid="active-filters">
          {filtered.activeCount === 1 ? "One filter" : `${filtered.activeCount} filters`}{" "}
          narrows the view to {filtered.nodes.length} nodes and {filtered.edges.length}{" "}
          edges
          {filtered.droppedUndatedEdges > 0 &&
            ` — ${filtered.droppedUndatedEdges} undated edge${filtered.droppedUndatedEdges === 1 ? " sits" : "s"} outside the date range`}
          .{" "}
          <button
            type="button"
            className="sig-graph-node-btn"
            data-testid="clear-filters"
            onClick={() =>
              update({
                kind: [], edge: [], currency: null, dated: null,
                source: [], jurisdiction: [], technology: [], collection: [],
                collectionSpecified: false,
              })
            }
          >
            Clear filters
          </button>
        </p>
      )}
      {merged !== null && (
        <details className="sig-explore-filters" data-testid="filter-panel">
          <summary>Filters — narrow the drawn graph</summary>
          <div className="sig-explore-filters__grid">
            {bands.length > 1 && (
              <fieldset data-testid="filter-kinds">
                <legend>Kind</legend>
                {bands.map((b) => (
                  <label key={b}>
                    <input
                      type="checkbox"
                      checked={state.kind.includes(b)}
                      onChange={() => update({ kind: toggleIn(state.kind, b) })}
                    />{" "}
                    {b}
                  </label>
                ))}
              </fieldset>
            )}
            {relations.length > 1 && (
              <fieldset data-testid="filter-relations">
                <legend>Relation — the access kinds stay separate toggles</legend>
                {relations.map((r) => (
                  <label key={r}>
                    <input
                      type="checkbox"
                      checked={state.edge.includes(r)}
                      onChange={() => update({ edge: toggleIn(state.edge, r) })}
                    />{" "}
                    {r}
                  </label>
                ))}
              </fieldset>
            )}
            <fieldset data-testid="filter-currency">
              <legend>Currency</legend>
              <select
                value={state.currency ?? ""}
                onChange={(e) =>
                  update({ currency: e.currentTarget.value === "" ? null : (e.currentTarget.value as typeof state.currency) })
                }
              >
                <option value="">any currency</option>
                {CURRENCIES.map((c) => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </select>
            </fieldset>
            <fieldset data-testid="filter-dated">
              <legend>Observed date range — undated edges fall outside it</legend>
              <label>
                From{" "}
                <input
                  type="text"
                  inputMode="numeric"
                  size={7}
                  placeholder="YYYY"
                  defaultValue={state.dated?.split("..")[0] ?? ""}
                  onBlur={(e) => {
                    const to = state.dated?.split("..")[1] ?? "9999";
                    const v = e.currentTarget.value.trim();
                    update({ dated: v === "" && !state.dated ? null : `${v || "0000"}..${to}` });
                  }}
                />
              </label>{" "}
              <label>
                To{" "}
                <input
                  type="text"
                  inputMode="numeric"
                  size={7}
                  placeholder="YYYY"
                  defaultValue={state.dated?.split("..")[1] ?? ""}
                  onBlur={(e) => {
                    const from = state.dated?.split("..")[0] ?? "0000";
                    const v = e.currentTarget.value.trim();
                    update({ dated: `${from}..${v || "9999"}` });
                  }}
                />
              </label>
            </fieldset>
            {sourceNames.length > 1 && (
              <fieldset data-testid="filter-sources">
                <legend>Source — mirrored sources count once</legend>
                {sourceNames.map((s) => (
                  <label key={s}>
                    <input
                      type="checkbox"
                      checked={state.source.includes(s)}
                      onChange={() => update({ source: toggleIn(state.source, s) })}
                    />{" "}
                    {s}
                  </label>
                ))}
              </fieldset>
            )}
            {docJurisdictions.length > 0 && (
              <fieldset data-testid="filter-jurisdiction">
                <legend>Jurisdiction — includes each place's descendants</legend>
                {docJurisdictions.map((jp) => (
                  <label key={jp.jkey}>
                    <input
                      type="checkbox"
                      checked={state.jurisdiction.includes(jp.jkey)}
                      onChange={() => update({ jurisdiction: toggleIn(state.jurisdiction, jp.jkey) })}
                    />{" "}
                    {jp.label}
                  </label>
                ))}
              </fieldset>
            )}
          </div>
        </details>
      )}

      <div className="sig-graph-island__layout">
        <div>
          <div
            ref={containerRef}
            className="sig-explore-island__canvas"
            data-testid="explore-canvas"
            role="img"
            aria-label={
              scoped !== null
                ? `Interactive ${doc?.title ?? ""} graph — ${scoped.nodes.length} nodes, ${scoped.edges.length} edges; the same facts are in the lists below.`
                : "Interactive graph canvas loading"
            }
          />
          {doc !== null && (
            <>
              <p className="sig-island__note" data-testid="explore-overview-note">
                {doc.title} — {doc.question} {doc.nodes.length} nodes, {doc.edges.length}{" "}
                edges
                {expansionCount > 0 && `, plus ${expansionCount} expanded ego${expansionCount === 1 ? "" : "s"}`}
                {canvasCapHit && ` — the ${CANVAS_NODE_CAP.toLocaleString()}-node canvas bound is reached; open the entity page for the full list`}
                . {doc.positionNote} {doc.erDisclosure}
                {doc.capActions.length > 0 && <> {doc.capActions.join(" ")}</>}
              </p>
              <p className="sig-island__note">
                Positions have no geographic meaning; the drawn layout is the release's
                precomputed one (expanded nodes sit on a ring). The same overview is
                published statically at{" "}
                {entry !== null && <a href={entry.pageHref}>{entry.pageHref}</a>}.
              </p>
            </>
          )}

          {/* Search to node — K3's shared shards for entities beyond the
              overview; the loaded graph answers directly. */}
          <div className="sig-explore-search" data-testid="explore-search">
            <label htmlFor="explore-search-input">Search to a node</label>{" "}
            <input
              id="explore-search-input"
              type="text"
              className="sig-search-island__input"
              value={q}
              placeholder="a name in the graph…"
              onInput={(e) => update({ q: e.currentTarget.value }, "replace")}
              data-testid="explore-search-input"
            />
            {q.trim() !== "" && (
              <ul className="sig-explore-search__results" data-testid="explore-search-results">
                {nodeMatches.slice(0, 8).map((n) => (
                  <li key={n.key}>
                    <button
                      type="button"
                      className="sig-graph-node-btn"
                      data-testid="search-node-hit"
                      onClick={() => update({ focus: n.key })}
                    >
                      {n.label} <span className="sig-search-island__kind">{n.band} · in this overview</span>
                    </button>
                  </li>
                ))}
                {shardMatches
                  .filter((s) => !nodeMatches.some((n) => n.href === s.href.replace(/^\//, "/")))
                  .map((s) => (
                    <li key={s.href}>
                      {s.href.startsWith(withBase("entity/")) || s.href.startsWith("/entity/") ? (
                        <button
                          type="button"
                          className="sig-graph-node-btn"
                          data-testid="search-entity-hit"
                          onClick={() => {
                            const href = s.href.startsWith("/") ? s.href : `/${s.href}`;
                            const key = `e:${href.split("/").filter(Boolean).pop()}`;
                            const anchor = merged?.nodes[0];
                            // Deterministic ring spot near the first node —
                            // never a PRNG position.
                            const self: OverviewNode = {
                              key,
                              label: s.label,
                              band: s.kind ?? "entity",
                              place: null,
                              href,
                              count: 0,
                              x: (anchor?.x ?? 0) + 90,
                              y: (anchor?.y ?? 0) + 30,
                            };
                            loadEgo(key, href, s.label, self);
                            update({
                              focus: key,
                              expand: [...new Set([...state.expand, key])].slice(0, EXPAND_CAP),
                            });
                          }}
                        >
                          {s.label} <span className="sig-search-island__kind">{s.detail ?? "entity"} · load its ego</span>
                        </button>
                      ) : (
                        <a href={s.href} data-testid="search-link-hit">
                          {s.label} <span className="sig-search-island__kind">{s.kind}</span>
                        </a>
                      )}
                    </li>
                  ))}
                {nodeMatches.length === 0 && shardMatches.length === 0 && (
                  <li data-testid="search-empty">
                    No node in this overview matches "{q}" — the corpus search covers the
                    whole release.
                  </li>
                )}
              </ul>
            )}
          </div>
        </div>

        <div>
          <h3 id="explore-island-nodes-heading">Nodes in view</h3>
          {scoped !== null && (
            <table className="sig-table sig-explore-table" aria-labelledby="explore-island-nodes-heading" data-testid="explore-node-table">
              <thead>
                <tr>
                  {(["label", "kind", "place", "count"] as const).map((col) => (
                    <th key={col} scope="col">
                      <button
                        type="button"
                        className="sig-explore-sort"
                        data-testid={`sort-${col}`}
                        aria-pressed={sort === col}
                        onClick={() =>
                          update({
                            sort: col,
                            dir: sort === col && state.dir !== "desc" ? "desc" : "asc",
                          })
                        }
                      >
                        {col === "count" ? "records" : col}
                        {sort === col ? (state.dir === "desc" ? " ↓" : " ↑") : ""}
                      </button>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {listNodes.map((n) => (
                  <tr key={n.key} data-node={n.key}>
                    <td>
                      <button
                        type="button"
                        className="sig-graph-node-btn"
                        data-testid="graph-island-node"
                        data-node={n.key}
                        aria-pressed={n.key === focusId}
                        onClick={() => update({ focus: n.key })}
                      >
                        {n.label}
                      </button>
                    </td>
                    <td>{n.band}</td>
                    <td>{n.place ?? "—"}</td>
                    <td>{n.count > 0 ? n.count : ""}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          {state.hops !== null && focusId !== null && scoped !== null && (
            <p className="sig-island__note" data-testid="hops-note">
              Showing the {state.hops}-hop neighbourhood of {labelOf(focusId)} —{" "}
              <button type="button" className="sig-graph-node-btn" onClick={() => update({ hops: null })}>
                show the whole overview
              </button>
            </p>
          )}

          <div className="sig-graph-detail" data-testid="graph-island-detail" aria-live="polite">
            {selEdge !== null ? (
              <>
                <h3 data-testid="edge-panel-title">
                  {labelOf(selEdge.src)} → {labelOf(selEdge.dst)}
                </h3>
                <p data-testid="edge-panel-facts">
                  {selEdge.relation}
                  {selEdge.date ? `; observed ${selEdge.date}` : "; undated"}
                  {`; ${selEdge.currency.toLowerCase()}`}
                  {selEdge.sources.length > 0 &&
                    `; source${selEdge.sources.length === 1 ? "" : "s"}: ${selEdge.sources.join(", ")}`}
                  {`; ${selEdge.evidenceCount} supporting claim${selEdge.evidenceCount === 1 ? "" : "s"}`}
                  {selEdge.memberCount > 0 && `; ${selEdge.memberCount} members folded into this cell`}
                </p>
                <p className="sig-island__note">
                  Provenance: the claim-level evidence lives on the linked entity pages
                  {nodeByKey.get(selEdge.src)?.href && (
                    <>
                      {" "}· <a href={hrefOf(nodeByKey.get(selEdge.src)!.href!)}>{labelOf(selEdge.src)}</a>
                    </>
                  )}
                  {nodeByKey.get(selEdge.dst)?.href && (
                    <>
                      {" "}· <a href={hrefOf(nodeByKey.get(selEdge.dst)!.href!)}>{labelOf(selEdge.dst)}</a>
                    </>
                  )}
                  {" "}and in this overview's{" "}
                  {entry !== null && <a href={entry.pageHref}>static adjacency table</a>}.
                </p>
              </>
            ) : pair !== null || pathResult !== null ? (
              <>
                <h3 data-testid="path-panel-title">Path</h3>
                {pair !== null && (
                  <p>
                    <code>{labelOf(pair.a)}</code> → <code>{labelOf(pair.b)}</code>
                    {doc?.id === "access" &&
                      " — over configured-access edges only (an observed or declared-policy edge does not compose)"}
                  </p>
                )}
                {pathResult?.kind === "path" && (
                  <>
                    {pathResult.speculative && (
                      <p className="sig-path__speculative" data-testid="speculative-label">
                        SPECULATIVE — beyond the published {SPECULATIVE_HOPS}-hop threshold; not a headline figure.
                      </p>
                    )}
                    {pathResult.hops.length === 0 && (
                      <p data-testid="path-same">The pair names the same node.</p>
                    )}
                    <ol className="sig-path__hops" data-testid="path-hop-list">
                      {pathResult.hops.map((h, i) => (
                        <li key={i} data-testid="island-path-hop">
                          <strong>{labelOf(h.from)}</strong> → <strong>{labelOf(h.to)}</strong>
                          {" "}
                          <span className="sig-path__hop-meta">
                            ({h.edge.relation}
                            {h.edge.date ? `, observed ${h.edge.date}` : ", undated"}
                            {`, ${h.edge.currency.toLowerCase()}`}
                            {h.edge.sources.length > 0 && `, ${h.edge.sources.join(", ")}`}
                            {`, ${h.edge.evidenceCount} claim${h.edge.evidenceCount === 1 ? "" : "s"}`})
                          </span>
                        </li>
                      ))}
                    </ol>
                  </>
                )}
                {pathResult?.kind === "no-path" && (
                  <p data-testid="path-none">
                    No path within {SPECULATIVE_HOPS} hops or beyond in the loaded
                    overview — the loaded graph holds no chain between them; that is not
                    "not connected" in the world, only absent from this overview's
                    evidence.
                  </p>
                )}
                {pathResult?.kind === "missing-endpoint" && (
                  <p data-testid="path-missing">
                    <code>{pathResult.missing}</code> is not a node in this overview —
                    the path answer does not apply here.
                  </p>
                )}
                <p>
                  <button type="button" className="sig-graph-node-btn" data-testid="path-clear" onClick={() => update({ path: null })}>
                    Clear the path
                  </button>
                </p>
              </>
            ) : focusNode !== null ? (
              <>
                <h3 data-testid="node-panel-title">{focusNode.label}</h3>
                <p data-testid="node-panel-facts">
                  {focusNode.band}
                  {focusNode.place ? `; place ${focusNode.place}` : ""}
                  {focusNode.count > 0 ? `; ${focusNode.count} records` : ""}
                </p>
                {focusNode.href && (
                  <p>
                    <a href={hrefOf(focusNode.href)} data-testid="node-panel-entity-link">
                      Open the entity page — claim-level evidence and provenance live there
                    </a>
                  </p>
                )}
                <p>
                  {entityHrefOf(focusNode) !== null || egos.get(focusNode.key)?.status === "missing" ? (
                    <button
                      type="button"
                      className="sig-graph-node-btn"
                      data-testid="node-expand"
                      disabled={egos.get(focusNode.key)?.status === "loading" || expandedKeys.includes(focusNode.key) || (expandCapHit && !expandedKeys.includes(focusNode.key))}
                      onClick={() => update({ expand: [...new Set([...state.expand, focusNode.key])].slice(0, EXPAND_CAP) })}
                    >
                      {egos.get(focusNode.key)?.status === "loading"
                        ? "Expanding…"
                        : expandedKeys.includes(focusNode.key)
                          ? "Expanded"
                          : "Expand — load its relationships"}
                    </button>
                  ) : null}
                  {" "}
                  <button
                    type="button"
                    className="sig-graph-node-btn"
                    data-testid="node-path-start"
                    onClick={() => pickNodeForPath(focusNode.key)}
                  >
                    {pathFrom === focusNode.key ? "Cancel path" : "Path to another node…"}
                  </button>
                  {" "}
                  <button
                    type="button"
                    className="sig-graph-node-btn"
                    data-testid="node-hops-1"
                    aria-pressed={state.hops === 1}
                    onClick={() => update({ hops: state.hops === 1 ? null : 1 })}
                  >
                    1-hop ring
                  </button>{" "}
                  <button
                    type="button"
                    className="sig-graph-node-btn"
                    data-testid="node-hops-2"
                    aria-pressed={state.hops === 2}
                    onClick={() => update({ hops: state.hops === 2 ? null : 2 })}
                  >
                    2-hop ring
                  </button>
                </p>
                {expandCapHit && !expandedKeys.includes(focusNode.key) && (
                  <p className="sig-island__note" data-testid="expand-cap-note">
                    The {EXPAND_CAP}-expansion bound is reached — open the entity page
                    for the full relationship list.
                  </p>
                )}
                {egos.get(focusNode.key)?.note && (
                  <p className="sig-island__note" role="status" data-testid="ego-note">
                    {egos.get(focusNode.key)!.note}
                  </p>
                )}
                {egos.get(focusNode.key)?.status === "ready" && (egos.get(focusNode.key)!.more ?? 0) > 0 && (
                  <p className="sig-island__note" data-testid="ego-more-note">
                    {egos.get(focusNode.key)!.more} further relationship
                    {egos.get(focusNode.key)!.more === 1 ? "" : "s"} beyond the twin's
                    per-relation bound — the entity page lists them all.
                  </p>
                )}
                <h4>Incident edges</h4>
                <ul data-testid="node-neighbours">
                  {nodeNeighbours(focusNode.key).map((e, i) => {
                    const idx = scoped!.edges.indexOf(e);
                    const other = e.src === focusNode.key ? e.dst : e.src;
                    return (
                      <li key={i}>
                        <button
                          type="button"
                          className="sig-graph-node-btn"
                          data-testid="edge-panel-open"
                          onClick={() => setEdgeSel(idx)}
                          onKeyDown={(ev) => {
                            if (ev.key === "ArrowDown" || ev.key === "ArrowRight") {
                              ev.preventDefault();
                              (ev.currentTarget.parentElement?.nextElementSibling?.querySelector("button") as HTMLElement | null)?.focus();
                            } else if (ev.key === "ArrowUp" || ev.key === "ArrowLeft") {
                              ev.preventDefault();
                              (ev.currentTarget.parentElement?.previousElementSibling?.querySelector("button") as HTMLElement | null)?.focus();
                            }
                          }}
                        >
                          {labelOf(e.src)} → {labelOf(e.dst)}: {e.relation}
                          {e.date ? ` (${e.date})` : " (undated)"}
                        </button>
                        {" "}
                        <button
                          type="button"
                          className="sig-graph-node-btn"
                          data-testid="neighbour-focus"
                          onClick={() => update({ focus: other })}
                        >
                          {labelOf(other)}
                        </button>
                      </li>
                    );
                  })}
                </ul>
                {pathFrom !== null && (
                  <p className="sig-island__note" data-testid="path-pick-note">
                    Path from {labelOf(pathFrom)} — pick the other node in the list or on the canvas.
                  </p>
                )}
              </>
            ) : (
              <p data-testid="detail-empty">
                Select a node or an edge — its facts and the way to its evidence appear here.
              </p>
            )}
          </div>
          {[...egos.entries()].filter(([, e]) => e.status === "error").map(([k, e]) => (
            <p key={k} className="sig-island__note" role="status" data-testid="ego-error">
              {e.note}
            </p>
          ))}
        </div>
      </div>
    </div>
  );
}
