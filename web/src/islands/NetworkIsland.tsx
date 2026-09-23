// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * The interactive sharing-network island (P27.9, DECISION-SPA = B, ADR-097).
 *
 * PROGRESSIVE ENHANCEMENT, NOT REPLACEMENT (SIG-UI-050): this island hydrates ONLY
 * on `/network/`; the edge lists and hop lists below it are the source of truth and
 * the no-JS / screen-reader path (SIG-UI-037) and are never removed.
 *
 * Honest defaults (SIG-UI-021/022): the explorer opens on an EGO network around one
 * entity and expands one ring at a time — never a national hairball. The three §12.2
 * access edge types stay visually distinct by dash pattern, not colour (SIG-UI-024,
 * greyscale-safe). Every centrality statistic shown carries its inline ER-quality
 * disclosure (SIG-UI-023). Keyboard operability (WCAG 2.2 AA): the node selector is a
 * list of real focusable buttons that drive the same focus state as clicking a node.
 */

import { useMemo, useState } from "react";
import type { ReactElement } from "react";
import type { NetworkNode, NetworkEdge, CentralityStatistic, AccessKind } from "../lib/network";
import { ACCESS_EDGE_STYLES } from "../lib/network";

export interface NetworkIslandProps {
  nodes: NetworkNode[];
  edges: NetworkEdge[];
  centrality: CentralityStatistic[];
  focusEntityId: string;
}

interface Placed {
  node: NetworkNode;
  x: number;
  y: number;
  center: boolean;
}

const W = 460;
const H = 340;

function egoOf(
  nodes: NetworkNode[],
  edges: NetworkEdge[],
  focusId: string,
): { nodes: NetworkNode[]; edges: NetworkEdge[] } {
  const neighborIds = new Set<string>([focusId]);
  const egoEdges: NetworkEdge[] = [];
  for (const e of edges) {
    if (e.from === focusId || e.to === focusId) {
      neighborIds.add(e.from);
      neighborIds.add(e.to);
      egoEdges.push(e);
    }
  }
  return {
    nodes: nodes.filter((n) => neighborIds.has(n.id)),
    edges: egoEdges,
  };
}

export default function NetworkIsland({
  nodes,
  edges,
  centrality,
  focusEntityId,
}: NetworkIslandProps): ReactElement {
  const [focusId, setFocusId] = useState(focusEntityId);
  const [selectedId, setSelectedId] = useState(focusEntityId);

  const ego = useMemo(() => egoOf(nodes, edges, focusId), [nodes, edges, focusId]);
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

  const selectedStats = centrality.filter((s) => s.node_id === selectedId);
  const selectedEdges = ego.edges.filter((e) => e.from === selectedId || e.to === selectedId);

  return (
    <div className="sig-graph-island__layout" data-testid="network-island">
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
                onClick={() => setSelectedId(p.node.id)}
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
                onClick={() => {
                  setSelectedId(n.id);
                  setFocusId(n.id);
                }}
              >
                {n.label} <span className="sig-search-island__kind">{n.type}</span>
              </button>
            </li>
          ))}
        </ul>

        <div className="sig-graph-detail" data-testid="graph-island-detail" aria-live="polite">
          <h3>{labelOf(selectedId)}</h3>
          {selectedStats.length === 0 ? (
            <p>No centrality statistic is published for this node.</p>
          ) : (
            <ul>
              {selectedStats.map((s, i) => (
                <li key={i} data-testid="graph-island-centrality">
                  <strong>{s.metric}</strong>: {s.value.toFixed(3)}
                  <br />
                  <span data-testid="graph-island-er-disclosure">{s.disclosure}</span>
                </li>
              ))}
            </ul>
          )}
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
                  </li>
                );
              })}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}
