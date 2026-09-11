// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * The network explorer's honest-rendering rules as pure data + logic (§39.4).
 *
 * The graph half of P15.3. No rendering, no colour, no DOM — every rule is
 * unit-testable and shared by the static SVG diagram and the list equivalent. The
 * rules encoded here:
 *
 *   - the default view is an ego network with expansion, never a global graph
 *     (SIG-UI-022);
 *   - every centrality / hub statistic carries an ER-quality disclosure INLINE, at
 *     the statistic — structurally, the statistic type cannot exist without it
 *     (SIG-UI-023, SIG-IDENT-030, P6);
 *   - the three §12.2 access edge types are visually distinct (a distinct glyph AND
 *     dash pattern each, so distinct without colour) and independently filterable,
 *     never merged by default (SIG-UI-024);
 *   - access-path closure carries the full hop list with per-hop evidence, and any
 *     path beyond the published hop threshold is labelled speculative and excluded
 *     from headline figures (SIG-UI-025, SIG-RECON-050).
 *
 * The access-edge and access-path shapes mirror the pipeline's own
 * `inference/src/inference/access_paths.py` and `reconcile/src/reconcile/sharing.py`
 * (ACCESS_KINDS, SPECULATIVE_HOP_THRESHOLD, the composition + confidence rules) so
 * this surface presents exactly what that layer computes, never a re-derivation.
 */

import type { Support } from "./epistemic";

// --- Nodes + edges ---------------------------------------------------------

export interface NetworkNode {
  id: string;
  label: string;
  /** e.g. "agency" | "vendor" | "rtcc"; opaque to this module. */
  type: string;
}

// --- The three §12.2 access edge types (SIG-UI-024, SIG-ONTO-042) ----------

/**
 * Configured access, actual use, and declared policy are three distinct edge types
 * that MUST NOT be merged, collapsed, or defaulted into one another (§12.2,
 * SIG-ONTO-042). The order/names mirror `reconcile.sharing.ACCESS_KINDS`.
 */
export const ACCESS_EDGE_TYPES = ["configured_access", "observed_use", "declared_policy"] as const;
export type AccessKind = (typeof ACCESS_EDGE_TYPES)[number];

/**
 * The visual treatment for one access edge type. Distinctness is carried by a glyph
 * AND a dash pattern — two non-colour channels — so the three types are
 * distinguishable in greyscale and print (SIG-UI-005/024), never by colour alone.
 */
export interface AccessEdgeStyle {
  kind: AccessKind;
  label: string;
  /** A distinct non-colour glyph marker. */
  glyph: string;
  /** A distinct SVG stroke-dasharray, e.g. "" (solid), "6 3", "1 4". */
  dash: string;
  /** What this edge means (from the §12.2 table). */
  meaning: string;
  /** What it NEVER implies (from the §12.2 table). */
  neverImplies: string;
}

export const ACCESS_EDGE_STYLES: Record<AccessKind, AccessEdgeStyle> = {
  configured_access: {
    kind: "configured_access",
    label: "Configured access",
    glyph: "\u25C9", // ◉ fisheye — a live channel
    dash: "", // solid
    meaning: "The system is set up to permit it.",
    neverImplies: "That anyone used it.",
  },
  observed_use: {
    kind: "observed_use",
    label: "Observed use",
    glyph: "\u25B6", // ▶ a discrete event
    dash: "6 3", // dashed
    meaning: "Someone actually did it.",
    neverImplies: "That it is still configured.",
  },
  declared_policy: {
    kind: "declared_policy",
    label: "Declared policy",
    glyph: "\u00A7", // § a statement/instrument
    dash: "1 4", // dotted
    meaning: "Someone said it is permitted or forbidden.",
    neverImplies: "That configuration matches.",
  },
};

/**
 * The three access edge types MUST NOT be shown merged by default (SIG-UI-024). This
 * constant makes the default explicit and testable; a surface that merges them must
 * do so behind an explicit, deliberate user action, never as the initial state.
 */
export const MERGE_ACCESS_EDGES_BY_DEFAULT = false;

export interface NetworkEdge {
  from: string;
  to: string;
  access_kind: AccessKind;
  /** Human-readable relation label for the list equivalent. */
  relation: string;
  support: Support;
  evidence_count: number;
}

/** An independent on/off flag per access edge type — the three filter separately. */
export type AccessEdgeFilter = Record<AccessKind, boolean>;

/** Default filter: all three visible, but as three distinct, unmerged layers. */
export const DEFAULT_ACCESS_EDGE_FILTER: AccessEdgeFilter = {
  configured_access: true,
  observed_use: true,
  declared_policy: true,
};

/** Filter edges by the independently-toggleable access-type flags (SIG-UI-024). */
export function filterAccessEdges(
  edges: readonly NetworkEdge[],
  filter: AccessEdgeFilter,
): NetworkEdge[] {
  return edges.filter((e) => filter[e.access_kind]);
}

// --- Ego network with expansion (SIG-UI-022) -------------------------------

/** The network default is an ego network, never a global graph. */
export const DEFAULT_NETWORK_VIEW = "ego" as const;

/**
 * The ego network around `centerId` out to `depth` hops (BFS), treating edges as
 * undirected for neighbourhood membership. This is the default surface (SIG-UI-022):
 * a global graph is never rendered by default. `depth` models the "expansion" — a
 * user grows the neighbourhood one ring at a time.
 */
export function egoNetwork(
  nodes: readonly NetworkNode[],
  edges: readonly NetworkEdge[],
  centerId: string,
  depth = 1,
): { nodes: NetworkNode[]; edges: NetworkEdge[] } {
  if (depth < 0) throw new Error("ego-network depth must be >= 0");
  const byId = new Map(nodes.map((n) => [n.id, n]));
  if (!byId.has(centerId)) throw new Error(`ego center ${centerId} is not a node`);

  const included = new Set<string>([centerId]);
  let frontier = new Set<string>([centerId]);
  for (let d = 0; d < depth; d += 1) {
    const next = new Set<string>();
    for (const edge of edges) {
      if (frontier.has(edge.from) && !included.has(edge.to)) next.add(edge.to);
      if (frontier.has(edge.to) && !included.has(edge.from)) next.add(edge.from);
    }
    for (const id of next) included.add(id);
    frontier = next;
    if (next.size === 0) break;
  }

  const includedNodes = nodes.filter((n) => included.has(n.id));
  // Keep only edges fully inside the neighbourhood (no dangling half-edges).
  const includedEdges = edges.filter((e) => included.has(e.from) && included.has(e.to));
  return { nodes: includedNodes, edges: includedEdges };
}

// --- ER-quality disclosure on EVERY centrality statistic (SIG-UI-023) ------

/**
 * The entity-resolution quality behind a network statistic (§14.7, SIG-IDENT-028).
 * If entity resolution is imperfect, so is every network statistic derived from the
 * resolved graph — so this disclosure MUST travel with the statistic, inline, not in
 * a footnote (SIG-UI-023, SIG-IDENT-030).
 */
export interface ErQuality {
  /** Pairwise precision/recall/F1 at the tier boundary used for this graph. */
  pairwise_precision: number;
  pairwise_recall: number;
  f1: number;
  /** B-cubed cluster precision/recall on the frozen holdout. */
  bcubed_precision: number;
  bcubed_recall: number;
  /** The versioned holdout the numbers were measured on. */
  holdout_version: string;
}

export type CentralityMetric = "degree" | "betweenness" | "closeness" | "hub_score" | "eigenvector";

/**
 * A centrality / hub statistic. The ER-quality disclosure is a REQUIRED field and a
 * pre-rendered inline `disclosure` string, so the type itself cannot represent a
 * statistic without its disclosure — the SIG-UI-023 invariant is structural, not a
 * render-time convention a page could forget.
 */
export interface CentralityStatistic {
  node_id: string;
  metric: CentralityMetric;
  value: number;
  er_quality: ErQuality;
  /** The inline disclosure text shown AT the statistic (never a footnote). */
  disclosure: string;
}

function isFraction(x: number): boolean {
  return Number.isFinite(x) && x >= 0 && x <= 1;
}

/** The inline ER-quality disclosure text for a statistic (SIG-UI-023). */
export function erDisclosureText(er: ErQuality): string {
  const pct = (x: number) => `${(x * 100).toFixed(0)}%`;
  return (
    `Depends on entity resolution (holdout ${er.holdout_version}): ` +
    `pairwise F1 ${pct(er.f1)} (P ${pct(er.pairwise_precision)} / R ${pct(er.pairwise_recall)}), ` +
    `B³ cluster P ${pct(er.bcubed_precision)} / R ${pct(er.bcubed_recall)}. ` +
    `Imperfect resolution makes this figure imperfect.`
  );
}

/**
 * Build a centrality statistic, always with its inline ER disclosure (SIG-UI-023).
 * Throws if the ER quality is missing or its metrics are not valid fractions — a
 * statistic with no disclosable ER quality must not be presentable at all
 * (SIG-IDENT-030: no network-analytics surface ships before the ER gates pass).
 */
export function centralityStatistic(
  node_id: string,
  metric: CentralityMetric,
  value: number,
  er: ErQuality,
): CentralityStatistic {
  for (const [k, v] of Object.entries({
    pairwise_precision: er?.pairwise_precision,
    pairwise_recall: er?.pairwise_recall,
    f1: er?.f1,
    bcubed_precision: er?.bcubed_precision,
    bcubed_recall: er?.bcubed_recall,
  })) {
    if (!isFraction(v as number)) {
      throw new Error(
        `SIG-UI-023: a centrality statistic needs a valid ER-quality disclosure; ${k}=${v} is not a fraction in [0,1].`,
      );
    }
  }
  if (!er.holdout_version) {
    throw new Error("SIG-UI-023: ER-quality disclosure must name the holdout version.");
  }
  return { node_id, metric, value, er_quality: er, disclosure: erDisclosureText(er) };
}

/** Throw if any statistic lacks a non-empty inline ER disclosure (SIG-UI-023). */
export function assertErDisclosures(stats: readonly CentralityStatistic[]): void {
  for (const s of stats) {
    if (!s.disclosure || !s.er_quality) {
      throw new Error(
        `SIG-UI-023: centrality statistic ${s.metric} for ${s.node_id} is missing its inline ER-quality disclosure.`,
      );
    }
  }
}

// --- Access-path closure (SIG-UI-025, SIG-RECON-050) -----------------------

/**
 * The published hop count beyond which a path is labelled speculative and excluded
 * from headline figures (SIG-RECON-050). Mirrors
 * `inference.access_paths.SPECULATIVE_HOP_THRESHOLD`. A 1..THRESHOLD-hop path is
 * publishable as a finding; a longer one is shown, with its hops, but never counted
 * as a shared-data relationship.
 */
export const SPECULATIVE_HOP_THRESHOLD = 3;

/** Confidence labels least→most confident; path confidence is the minimum over hops. */
export const CONFIDENCE_ORDER = ["possible", "probable", "certain"] as const;
export type Confidence = (typeof CONFIDENCE_ORDER)[number];

export const LIVE = "live" as const;
export const HISTORICAL = "historical" as const;
export type TemporalStatus = typeof LIVE | typeof HISTORICAL;

/** One hop of a reachability path. `evidence` is required and non-empty. */
export interface AccessHop {
  from_org: string;
  to_org: string;
  edge_label: string;
  scope: string;
  confidence: Confidence;
  /** Supporting claim/evidence ids — an unexplained hop is a forbidden edge (§3.1). */
  evidence: string[];
  /** Whether this hop is expired at the as-of time (taints the path historical). */
  expired?: boolean;
}

/** A derived reachability path source → … → target, carrying its full hop list. */
export interface AccessPath {
  hops: AccessHop[];
}

const CONFIDENCE_RANK: Record<Confidence, number> = { possible: 0, probable: 1, certain: 2 };

/** Validate that every hop carries evidence and the chain is contiguous (SIG-UI-025). */
export function assertPathValid(path: AccessPath): void {
  if (path.hops.length === 0) throw new Error("an access path must have at least one hop");
  for (const h of path.hops) {
    if (!h.evidence || h.evidence.length === 0) {
      throw new Error(
        `SIG-UI-025: every hop MUST carry per-hop evidence — ${h.from_org}->${h.to_org} has none ` +
          "(an unexplained hop is the forbidden unexplained edge, §3.1).",
      );
    }
  }
  for (let i = 1; i < path.hops.length; i += 1) {
    if (path.hops[i - 1]!.to_org !== path.hops[i]!.from_org) {
      throw new Error("access path hops are not contiguous");
    }
  }
}

export function pathHopCount(path: AccessPath): number {
  return path.hops.length;
}

export function pathSource(path: AccessPath): string {
  return path.hops[0]!.from_org;
}

export function pathTarget(path: AccessPath): string {
  return path.hops[path.hops.length - 1]!.to_org;
}

/** The ordered node list source..target. */
export function pathOrgs(path: AccessPath): string[] {
  return [path.hops[0]!.from_org, ...path.hops.map((h) => h.to_org)];
}

/** Path confidence is the MINIMUM over the hops — never the average (SIG-RECON-049 #6). */
export function pathConfidence(path: AccessPath): Confidence {
  return path.hops.reduce<Confidence>(
    (min, h) => (CONFIDENCE_RANK[h.confidence] < CONFIDENCE_RANK[min] ? h.confidence : min),
    "certain",
  );
}

/** A path is historical if any hop is expired at the as-of time (SIG-RECON-049 #4). */
export function pathTemporalStatus(path: AccessPath): TemporalStatus {
  return path.hops.some((h) => h.expired) ? HISTORICAL : LIVE;
}

/** Beyond the published hop threshold, the path is speculative (SIG-RECON-050). */
export function pathIsSpeculative(path: AccessPath): boolean {
  return pathHopCount(path) > SPECULATIVE_HOP_THRESHOLD;
}

/**
 * Whether the path may appear in headline figures. Only a live, non-speculative,
 * multi-hop path counts (SIG-RECON-050); a single direct hop is an observation, not
 * a closure inference.
 */
export function pathIsHeadline(path: AccessPath): boolean {
  return pathTemporalStatus(path) === LIVE && !pathIsSpeculative(path) && pathHopCount(path) >= 2;
}
