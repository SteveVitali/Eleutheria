// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * The interactive graph explorer — the `/explore/` T2 surface (P37.26,
 * K2 GX-09a; ADR-155's named T2 graph over the `/graphs/**` no-JS
 * equivalent; ADR-242 for the sigma/graphology browser-runtime seats).
 *
 * PROGRESSIVE ENHANCEMENT, NOT REPLACEMENT (SIG-UI-050): the island mounts
 * a **Preact + sigma** renderer inside the reserved SSR box and loads the
 * emitted `sig.graph-overview/1` docs over the wire; the overview index, the
 * static figure + adjacency preview, the access-edge lists and the
 * precomputed path hop lists below it carry the same facts with JS off and
 * are never removed.
 *
 * 09a scope: overview loading (the `overview=` address picks the doc), the
 * node and edge panels that hand off to provenance (entity pages, the
 * static adjacency pages, the per-compartment downloads), `focus=` URL
 * state, and the live "cite this view" mint. Expansion, facet filters,
 * search-to-node and the path finder are GX-09b's row — those registered
 * parameters PARSE here but are visibly named unapplied (SIG-UI-060),
 * never silently dropped and never presented as a filter that held.
 *
 * Honest rendering: node positions come verbatim off the emitted doc (the
 * builder's deterministic banded layout — no in-browser layout pass, no
 * PRNG); a `focus=` naming no node in the loaded overview is reported,
 * never fabricated; no centrality or hub ranking renders (SIG-UI-121 /
 * P34.15's SIG-IDENT-030 abstention).
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
  citeViewHref,
  facetNoticeText,
  INTERIM_CITE_VIEW_TEXT,
  ISLAND_VIEWS,
  recordRoutes,
  viewHref,
} from "../lib/workspace-state/index";
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
}

const VIEW_LABELS: Record<string, string> = {
  list: "List",
  map: "Map",
  network: "Connections",
};

// Entity kind = shape in the K13 C-01 lexicon; sigma's default program
// draws circles, so 09a differentiates by size + ink — the static SVG on
// the /graphs/ pages carries the full shape vocabulary and this palette
// stays muted-ink honest (colour is never the only channel: labels,
// counts and the detail panels carry the same facts).
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

export default function ExploreIsland({
  overviews,
  defaultOverview,
  release,
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

  const [doc, setDoc] = useState<GraphOverview | null>(null);
  const [loadState, setLoadState] = useState<"loading" | "error" | "ready">("loading");
  const [loadError, setLoadError] = useState<string>("");

  useEffect(() => {
    if (entry === null) return;
    let cancelled = false;
    setDoc(null);
    setLoadError("");
    setLoadState("loading");
    Promise.all(
      entry.docs.map((d) =>
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
  }, [overviewId, entry]);

  // --- selection --------------------------------------------------------
  // `focus` is the inspected/centred node — a deep link, reload or
  // Back/Forward restores it (SIG-UI-119's state round-trip).
  const focusId = state.focus;
  const [edgeSel, setEdgeSel] = useState<number | null>(null);
  useEffect(() => {
    setEdgeSel(null);
    // A focus surviving an overview switch keeps inspecting honestly; a
    // focus naming no node in THIS overview is reported below, never
    // fabricated.
  }, [overviewId]);
  useEffect(() => setEdgeSel(null), [focusId]);

  const nodeByKey = useMemo(
    () => new Map((doc?.nodes ?? []).map((n) => [n.key, n])),
    [doc],
  );
  const focusNode = focusId !== null ? (nodeByKey.get(focusId) ?? null) : null;
  const focusMiss =
    focusId !== null && doc !== null && !nodeByKey.has(focusId);
  const focusRoutes = useMemo(() => {
    const rel = state.release ?? release;
    return rel && focusMiss ? recordRoutes(rel, focusId) : null;
  }, [state.release, release, focusMiss, focusId]);

  // --- sigma mount ------------------------------------------------------
  // Positions come off the doc verbatim (y negated — the doc's banded
  // layout is screen-space; sigma's stage is y-up). The graph + WebGL
  // context build ONCE per doc — creating the context is the expensive
  // half — and selection restyles in place below (the select-node
  // interaction-latency budget leg measures the aria-pressed effect; a
  // rebuild-per-click would spend it all on context churn).
  const containerRef = useRef<HTMLDivElement>(null);
  const sigmaRef = useRef<Sigma | null>(null);
  const graphRef = useRef<Graph | null>(null);
  useEffect(() => {
    const container = containerRef.current;
    if (!container || doc === null) return;
    const g = new Graph();
    for (const n of doc.nodes) {
      g.addNode(n.key, {
        x: n.x,
        y: -n.y,
        label: n.label,
        size: nodeSize(n),
        color: bandColour(n.band),
      });
    }
    doc.edges.forEach((e, i) => {
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
    sigma.on("clickNode", ({ node }) => update({ focus: node }));
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
  }, [doc]);

  // Selection restyle — graphology attribute updates + sigma.refresh(),
  // never a rebuild. The visual contract stays a pure function of
  // (doc, selection); only the mutations differ.
  useEffect(() => {
    const g = graphRef.current;
    const sigma = sigmaRef.current;
    if (!g || !sigma || doc === null) return;
    for (const n of doc.nodes) {
      if (!g.hasNode(n.key)) continue;
      g.setNodeAttribute(
        n.key,
        "size",
        nodeSize(n) + (n.key === focusId ? 3 : 0),
      );
      g.setNodeAttribute(
        n.key,
        "color",
        n.key === focusId ? SELECT_COLOUR : bandColour(n.band),
      );
    }
    doc.edges.forEach((e, i) => {
      const key = `e${i}`;
      if (!g.hasEdge(key)) return;
      g.setEdgeAttribute(
        key,
        "color",
        i === edgeSel ? SELECT_COLOUR : edgeColour(e),
      );
    });
    sigma.refresh();
  }, [doc, focusId, edgeSel]);

  const labelOf = (key: string): string => nodeByKey.get(key)?.label ?? key;
  const selEdge: OverviewEdge | null =
    doc !== null && edgeSel !== null ? (doc.edges[edgeSel] ?? null) : null;

  const switchOverview = (id: string) =>
    update({ overview: id, focus: null }, "push");

  const citeForm = release ? citeViewHref(release, "graph", state) : null;

  return (
    <div data-testid="explore-island">
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

      <div className="sig-graph-island__layout">
        <div>
          <div
            ref={containerRef}
            className="sig-explore-island__canvas"
            data-testid="explore-canvas"
            role="img"
            aria-label={
              doc !== null
                ? `Interactive ${doc.title} graph — ${doc.nodes.length} nodes, ${doc.edges.length} edges; the same facts are in the lists below.`
                : "Interactive graph canvas loading"
            }
          />
          {doc !== null && (
            <>
              <p className="sig-island__note" data-testid="explore-overview-note">
                {doc.title} — {doc.question} {doc.nodes.length} nodes, {doc.edges.length}{" "}
                edges. {doc.positionNote} {doc.erDisclosure}
                {doc.capActions.length > 0 && <> {doc.capActions.join(" ")}</>}
              </p>
              <p className="sig-island__note">
                Positions have no geographic meaning; the drawn layout is the release's
                precomputed one. The same overview is published statically at{" "}
                {entry !== null && <a href={entry.pageHref}>{entry.pageHref}</a>}.
              </p>
            </>
          )}
        </div>

        <div>
          <h3 id="explore-island-nodes-heading">Nodes in view</h3>
          {doc !== null && (
            <ul className="sig-graph-island__nodes" aria-labelledby="explore-island-nodes-heading">
              {doc.nodes.map((n) => (
                <li key={n.key}>
                  <button
                    type="button"
                    className="sig-graph-node-btn"
                    data-testid="graph-island-node"
                    data-node={n.key}
                    aria-pressed={n.key === focusId}
                    onClick={() => update({ focus: n.key })}
                  >
                    {n.label} <span className="sig-search-island__kind">{n.band}</span>
                    {n.count > 0 && (
                      <span className="sig-search-island__kind"> · {n.count}</span>
                    )}
                  </button>
                </li>
              ))}
            </ul>
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
                      {" "}· <a href={withBase(nodeByKey.get(selEdge.src)!.href!.replace(/^\//, ""))}>{labelOf(selEdge.src)}</a>
                    </>
                  )}
                  {nodeByKey.get(selEdge.dst)?.href && (
                    <>
                      {" "}· <a href={withBase(nodeByKey.get(selEdge.dst)!.href!.replace(/^\//, ""))}>{labelOf(selEdge.dst)}</a>
                    </>
                  )}
                  {" "}and in this overview's{" "}
                  {entry !== null && <a href={entry.pageHref}>static adjacency table</a>}.
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
                    <a
                      href={withBase(focusNode.href.replace(/^\//, ""))}
                      data-testid="node-panel-entity-link"
                    >
                      Open the entity page — claim-level evidence and provenance live there
                    </a>
                  </p>
                )}
                <h4>Incident edges</h4>
                <ul>
                  {(doc?.edges ?? [])
                    .filter((e) => e.src === focusNode.key || e.dst === focusNode.key)
                    .map((e, i) => {
                      const idx = doc!.edges.indexOf(e);
                      return (
                        <li key={i}>
                          <button
                            type="button"
                            className="sig-graph-node-btn"
                            data-testid="edge-panel-open"
                            onClick={() => setEdgeSel(idx)}
                          >
                            {labelOf(e.src)} → {labelOf(e.dst)}: {e.relation}
                            {e.date ? ` (${e.date})` : " (undated)"}
                          </button>
                        </li>
                      );
                    })}
                </ul>
              </>
            ) : (
              <p data-testid="detail-empty">
                Select a node or an edge — its facts and the way to its evidence appear here.
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
