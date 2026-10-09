// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * The interactive sharing-network island (P27.9, DECISION-SPA = B, ADR-097;
 * P32.15 shared workspace state, SIG-FIND-004/005, ADR-134).
 *
 * PROGRESSIVE ENHANCEMENT, NOT REPLACEMENT (SIG-UI-050): this island hydrates ONLY
 * on `/network/`; the edge lists and hop lists below it are the source of truth and
 * the no-JS / screen-reader path (SIG-UI-037) and are never removed.
 *
 * Honest defaults (SIG-UI-021/022): the explorer opens on an EGO network around one
 * entity and expands one ring at a time — never a national hairball. The three §12.2
 * access edge types stay visually distinct by dash pattern, not colour (SIG-UI-024,
 * greyscale-safe). No centrality statistic is shown — the ranking is withdrawn
 * until organisation entity resolution passes its gate (P34.15, SIG-IDENT-030 by
 * abstention; SIG-UI-023's inline-disclosure contract stands for its return).
 * Keyboard operability (WCAG 2.2 AA): the node selector is a
 * list of real focusable buttons that drive the same focus state as clicking a node.
 *
 * Shared URL state (`sig.workspace-state/1`): `focus` names the ego centre — a
 * deep link, reload or Back/Forward restores it, and the List/Map view links
 * carry the whole investigation state. The initial neighbourhood is BOUNDED
 * (≤50 nodes / ≤100 edges, EGO_NODE_LIMIT/EGO_EDGE_LIMIT) with its true totals
 * stated; expansion pulls one ring at a time by node selection, and the
 * continued edge lists below carry every edge. Each selected-node edge exposes
 * its supporting claims — configured access, observed use and declared policy
 * are never merged and never imply one another (§12.2).
 */

import { useEffect, useMemo, useState } from "react";
import type { ReactElement } from "react";
import type { NetworkNode, NetworkEdge, AccessKind } from "../lib/network";
import {
  ACCESS_EDGE_STYLES,
  boundedEgoNetwork,
  EGO_EDGE_LIMIT,
  EGO_NODE_LIMIT,
} from "../lib/network";
import {
  facetNoticeText,
  recordRoutes,
  viewHref,
  WORKSPACE_VIEWS,
} from "../lib/workspace-state";
import { useWorkspaceState } from "./workspace";

export interface NetworkIslandProps {
  nodes: NetworkNode[];
  edges: NetworkEdge[];
  focusEntityId: string;
  /** The latest activated publication id for this build, or null (none). */
  release: string | null;
}

interface Placed {
  node: NetworkNode;
  x: number;
  y: number;
  center: boolean;
}

const W = 460;
const H = 340;

const VIEW_LABELS: Record<string, string> = {
  list: "List",
  map: "Map",
  network: "Connections",
};

export default function NetworkIsland({
  nodes,
  edges,
  focusEntityId,
  release,
}: NetworkIslandProps): ReactElement {
  const { state, issues, ignored, update } = useWorkspaceState("network", { release });

  // `focus` is the ego centre. A URL focus that names no node in this view stays
  // honest: the default centre renders and the miss is reported (never a
  // fabricated node), with the released-record link where one resolves.
  const requestedFocus = state.focus;
  const focusIsNode = requestedFocus !== null && nodes.some((n) => n.id === requestedFocus);
  const focusId = focusIsNode ? requestedFocus : focusEntityId;
  const focusRoutes = useMemo(() => {
    const rel = state.release ?? release;
    return rel && requestedFocus ? recordRoutes(rel, requestedFocus) : null;
  }, [state.release, release, requestedFocus]);

  const ego = useMemo(
    () =>
      nodes.some((n) => n.id === focusId)
        ? boundedEgoNetwork(nodes, edges, focusId, 1)
        : { nodes: [], edges: [], totalNodes: 0, totalEdges: 0, truncated: false },
    [nodes, edges, focusId],
  );
  // The detail pane inspects whichever node was last picked — a circle click
  // inspects WITHOUT re-centring (and without a history entry), a node button
  // re-centres the ego network AND becomes the inspected node.
  const [inspectId, setInspectId] = useState<string | null>(null);
  useEffect(() => setInspectId(null), [focusId]);
  const selectedId = inspectId ?? focusId;
  const labelOf = useMemo(() => {
    const m = new Map(nodes.map((n) => [n.id, n.label]));
    return (id: string) => m.get(id) ?? id;
  }, [nodes]);

  const placed = useMemo<Placed[]>(() => {
    const cx = W / 2;
    const cy = H / 2;
    const r = 120;
    const others = ego.nodes.filter((n) => n.id !== focusId);
    const out: Placed[] = [];
    const focusNode = ego.nodes.find((n) => n.id === focusId);
    if (focusNode) out.push({ node: focusNode, x: cx, y: cy, center: true });
    others.forEach((n, i) => {
      const a = (2 * Math.PI * i) / Math.max(1, others.length);
      out.push({ node: n, x: cx + r * Math.cos(a), y: cy + r * Math.sin(a), center: false });
    });
    return out;
  }, [ego, focusId]);

  const posOf = useMemo(() => {
    const m = new Map(placed.map((p) => [p.node.id, p]));
    return (id: string) => m.get(id);
  }, [placed]);

  const selectedEdges = ego.edges.filter((e) => e.from === selectedId || e.to === selectedId);

  return (
    <div data-testid="network-island">
      <nav className="sig-view-links" aria-label="Investigation views" data-testid="island-view-links">
        {WORKSPACE_VIEWS.map((v) =>
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
      {requestedFocus !== null && !focusIsNode && (
        <p className="sig-island__note" role="status" data-testid="graph-focus-miss">
          <code>{requestedFocus}</code> is not in this network view — showing{" "}
          {labelOf(focusId)} instead.
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
          <svg
            className="sig-graph-island__canvas"
            viewBox={`0 0 ${W} ${H}`}
            role="img"
            aria-label={`Interactive ego network around ${labelOf(focusId)}; the full edge and path detail is in the lists below.`}
          >
            {ego.edges.map((e, i) => {
              const a = posOf(e.from);
              const b = posOf(e.to);
              if (!a || !b) return null;
              const style = ACCESS_EDGE_STYLES[e.access_kind];
              return (
                <line
                  key={`e-${i}`}
                  x1={a.x}
                  y1={a.y}
                  x2={b.x}
                  y2={b.y}
                  stroke="var(--sig-muted, #666)"
                  strokeWidth={2}
                  strokeDasharray={style.dash || undefined}
                />
              );
            })}
            {placed.map((p) => (
              <g key={p.node.id}>
                <circle
                  cx={p.x}
                  cy={p.y}
                  r={p.center ? 13 : 9}
                  fill={
                    p.node.id === selectedId
                      ? "hsl(28deg 80% 50%)"
                      : "var(--sig-epi-status-resolved, #345)"
                  }
                  stroke="#222"
                  strokeWidth={p.node.id === selectedId ? 2 : 1}
                  style={{ cursor: "pointer" }}
                  onClick={() => setInspectId(p.node.id)}
                >
                  <title>{p.node.label}</title>
                </circle>
                <text x={p.x} y={p.y - 16} textAnchor="middle" fontSize={9}>
                  {p.node.label}
                </text>
              </g>
            ))}
          </svg>
          <p className="sig-island__note">
            Ego network around <strong>{labelOf(focusId)}</strong>. Select a node to focus its
            neighbourhood; edge dash patterns encode the access type (see the legend in the list
            below). This is never a national hairball (SIG-UI-021/022).
          </p>
          {ego.truncated && (
            <p className="sig-island__note" role="status" data-testid="graph-bounds-note">
              Bounded view: showing {ego.nodes.length} of {ego.totalNodes} nodes and{" "}
              {ego.edges.length} of {ego.totalEdges} edges (limits {EGO_NODE_LIMIT}/
              {EGO_EDGE_LIMIT}). Select a node to expand one ring; the lists below carry
              every edge.
            </p>
          )}
        </div>

        <div>
          <h3 id="graph-island-nodes-heading">Nodes in view</h3>
          <ul className="sig-graph-island__nodes" aria-labelledby="graph-island-nodes-heading">
            {ego.nodes.map((n) => (
              <li key={n.id}>
                <button
                  type="button"
                  className="sig-graph-node-btn"
                  data-testid="graph-island-node"
                  aria-pressed={n.id === focusId}
                  onClick={() => update({ focus: n.id })}
                >
                  {n.label} <span className="sig-search-island__kind">{n.type}</span>
                </button>
              </li>
            ))}
          </ul>

          <div className="sig-graph-detail" data-testid="graph-island-detail" aria-live="polite">
            <h3>{labelOf(selectedId)}</h3>
            <h4>Edges</h4>
            {selectedEdges.length === 0 ? (
              <p>No edges to this node in the current view.</p>
            ) : (
              <ul>
                {selectedEdges.map((e, i) => {
                  const style = ACCESS_EDGE_STYLES[e.access_kind as AccessKind];
                  return (
                    <li key={i}>
                      <span aria-hidden="true">{style.glyph}</span> {labelOf(e.from)} →{" "}
                      {labelOf(e.to)}: {e.relation} ({style.label}; {e.evidence_count} evidence)
                      {e.evidence && e.evidence.length > 0 && (
                        <ul className="sig-graph-island__edge-evidence" data-testid="edge-evidence">
                          {e.evidence.map((claim) => (
                            <li key={claim}>
                              <code>{claim}</code>
                            </li>
                          ))}
                        </ul>
                      )}
                    </li>
                  );
                })}
              </ul>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
