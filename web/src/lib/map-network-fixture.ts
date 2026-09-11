// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * Committed fixtures for the P15.3 infrastructure map + network explorer (§39.3/39.4).
 *
 * Static-first (SIG-UI-036): the surfaces read these typed fixtures at build time, not
 * a live API. The shapes mirror the pipeline the data comes from — map assets carry the
 * §19.4 sensitivity tier, network edges carry a §12.2 `access_kind`, and access paths
 * carry the full hop list with per-hop evidence that
 * `inference/src/inference/access_paths.py` produces. The worked entity is the same
 * Oklahoma City demo case the rest of the shell renders (Appendix B/D).
 */

import type { CentralityStatistic, ErQuality, NetworkEdge, NetworkNode, AccessPath } from "./network";
import { centralityStatistic } from "./network";
import type { DensityBin, MapAsset } from "./map";

// --- Map: physical assets across sensitivity tiers + jurisdictions ---------

/**
 * The map's assets. Deliberately spans the honest-rendering cases: full-precision
 * roadside hardware (tier 0), block-level (tier 1), H3-binned candidates (tier 2), a
 * jurisdiction-only confidential asset (tier 3 — never a point), a mobile asset with
 * no point, and an asset whose location is an outright gap (SIG-UI-020, §19.4).
 */
export const MAP_ASSETS: MapAsset[] = [
  {
    id: "device:okc-001",
    label: "Fixed ALPR — downtown corridor",
    jurisdiction: "Oklahoma City",
    tier: 0,
    lat: 35.4676,
    lon: -97.5164,
    precision: "full precision (tier 0, public right-of-way)",
  },
  {
    id: "device:okc-002",
    label: "RTCC integration hub",
    jurisdiction: "Oklahoma City",
    tier: 1,
    lat: 35.4823,
    lon: -97.5352,
    precision: "block-level (tier 1 truncation)",
  },
  {
    id: "device:okc-003",
    label: "Candidate camera — near school",
    jurisdiction: "Oklahoma City",
    tier: 2,
    lat: 35.49,
    lon: -97.52,
    precision: "H3 cell (tier 2 binning)",
  },
  {
    id: "device:okc-004",
    label: "Confidential facility sensor",
    jurisdiction: "Oklahoma City",
    tier: 3,
    lat: 35.5,
    lon: -97.5,
    precision: "jurisdiction only (tier 3 — no geometry published)",
  },
  {
    id: "device:okc-005",
    label: "Patrol-car ALPR (mobile)",
    jurisdiction: "Oklahoma City",
    tier: 1,
    lat: null,
    lon: null,
    precision: "operating-area only (mobile asset, SIG-GEO-004)",
  },
  {
    id: "device:tulsa-001",
    label: "Reported camera — location unconfirmed",
    jurisdiction: "Tulsa",
    tier: 2,
    lat: null,
    lon: null,
    precision: "unknown",
    locationAbsence: "NOT_RESEARCHED",
  },
];

/**
 * National-zoom density bins. Includes the two cells the SIG-UI-018 agentic AC turns
 * on: a LOW-coverage / low-count cell ("we don't know") and a HIGH-coverage / low-count
 * cell ("there really is little here"). They must render distinctly.
 */
export const DENSITY_BINS: DensityBin[] = [
  { h3: "8a2a1072b59ffff", jurisdiction: "Oklahoma City", deviceCount: 41, coverage: "high" },
  { h3: "8a2a1072b58ffff", jurisdiction: "Oklahoma City", deviceCount: 3, coverage: "high" },
  { h3: "8a44a1a3f6bffff", jurisdiction: "Cimarron County", deviceCount: 2, coverage: "low" },
  { h3: "8a44a1a3f6affff", jurisdiction: "Texas County", deviceCount: 0, coverage: "none" },
  { h3: "8a2a1072a4bffff", jurisdiction: "Tulsa", deviceCount: 18, coverage: "partial" },
];

/** The low-coverage cell the agentic AC3 checks against ("we don't know"). */
export const LOW_COVERAGE_BIN = DENSITY_BINS[2]!;
/** The confidently-low-density cell it must NOT look like ("little here"). */
export const LOW_DENSITY_BIN = DENSITY_BINS[1]!;

// --- Network: nodes, three access-edge types, centrality, access paths -----

export const NETWORK_NODES: NetworkNode[] = [
  { id: "agency:okcpd", label: "Oklahoma City PD", type: "agency" },
  { id: "agency:ocso", label: "Oklahoma County Sheriff", type: "agency" },
  { id: "rtcc:okc", label: "OKC Real-Time Crime Center", type: "rtcc" },
  { id: "vendor:flock", label: "Flock Safety", type: "vendor" },
  { id: "agency:tulsa", label: "Tulsa PD", type: "agency" },
  { id: "fusion:ok", label: "Oklahoma fusion center", type: "agency" },
];

/**
 * Edges across all three §12.2 access types — never merged. `configured_access`
 * edges are the composable channels the access-path closure walks; `observed_use` and
 * `declared_policy` are shown but do not compose (mirrors
 * `reconcile.sharing.ACCESS_KINDS` + `inference.access_paths.COMPOSABLE_LABELS`).
 */
export const NETWORK_EDGES: NetworkEdge[] = [
  {
    from: "agency:okcpd",
    to: "rtcc:okc",
    access_kind: "configured_access",
    relation: "has configured access to",
    support: "CONFIRMED",
    evidence_count: 3,
  },
  {
    from: "rtcc:okc",
    to: "vendor:flock",
    access_kind: "configured_access",
    relation: "has configured access to",
    support: "STRONGLY_SUPPORTED",
    evidence_count: 2,
  },
  {
    from: "vendor:flock",
    to: "agency:ocso",
    access_kind: "configured_access",
    relation: "has configured access to",
    support: "PROBABLE",
    evidence_count: 1,
  },
  {
    from: "agency:ocso",
    to: "agency:tulsa",
    access_kind: "configured_access",
    relation: "has configured access to",
    support: "PROBABLE",
    evidence_count: 1,
  },
  {
    from: "agency:tulsa",
    to: "fusion:ok",
    access_kind: "configured_access",
    relation: "has configured access to",
    support: "WEAKLY_SUPPORTED",
    evidence_count: 1,
  },
  {
    from: "agency:okcpd",
    to: "vendor:flock",
    access_kind: "observed_use",
    relation: "was observed querying",
    support: "STRONGLY_SUPPORTED",
    evidence_count: 2,
  },
  {
    from: "agency:okcpd",
    to: "agency:ocso",
    access_kind: "declared_policy",
    relation: "declares a sharing MOU with",
    support: "CONFIRMED",
    evidence_count: 1,
  },
];

/** The ER quality all this graph's centrality figures disclose (SIG-UI-023). */
export const ER_QUALITY: ErQuality = {
  pairwise_precision: 0.97,
  pairwise_recall: 0.91,
  f1: 0.94,
  bcubed_precision: 0.95,
  bcubed_recall: 0.89,
  holdout_version: "er-holdout-2026.06",
};

/**
 * The centrality/hub statistics on the explorer. Built through `centralityStatistic`,
 * so each is structurally guaranteed to carry its inline ER-quality disclosure — a
 * statistic that could not disclose its ER quality could not be constructed at all
 * (SIG-UI-023, SIG-IDENT-030).
 */
export const CENTRALITY_STATS: CentralityStatistic[] = [
  centralityStatistic("rtcc:okc", "betweenness", 0.62, ER_QUALITY),
  centralityStatistic("vendor:flock", "degree", 0.5, ER_QUALITY),
  centralityStatistic("agency:okcpd", "hub_score", 0.44, ER_QUALITY),
];

/**
 * Access-path closures from OKC PD. A 2-hop live path is a publishable finding; a
 * 4-hop path is shown WITH its hops but labelled speculative and kept out of headline
 * figures (SIG-UI-025, SIG-RECON-050). Every hop carries per-hop evidence.
 */
export const HEADLINE_PATH: AccessPath = {
  hops: [
    {
      from_org: "agency:okcpd",
      to_org: "rtcc:okc",
      edge_label: "configured_access",
      scope: "partner",
      confidence: "certain",
      evidence: ["claim:okc-rtcc-mou", "claim:rtcc-config-screenshot"],
    },
    {
      from_org: "rtcc:okc",
      to_org: "vendor:flock",
      edge_label: "configured_access",
      scope: "partner",
      confidence: "probable",
      evidence: ["claim:rtcc-flock-integration"],
    },
  ],
};

export const SPECULATIVE_PATH: AccessPath = {
  hops: [
    {
      from_org: "agency:okcpd",
      to_org: "rtcc:okc",
      edge_label: "configured_access",
      scope: "partner",
      confidence: "certain",
      evidence: ["claim:okc-rtcc-mou"],
    },
    {
      from_org: "rtcc:okc",
      to_org: "vendor:flock",
      edge_label: "configured_access",
      scope: "partner",
      confidence: "probable",
      evidence: ["claim:rtcc-flock-integration"],
    },
    {
      from_org: "vendor:flock",
      to_org: "agency:ocso",
      edge_label: "configured_access",
      scope: "partner",
      confidence: "possible",
      evidence: ["claim:flock-ocso-share"],
    },
    {
      from_org: "agency:ocso",
      to_org: "agency:tulsa",
      edge_label: "configured_access",
      scope: "partner",
      confidence: "possible",
      evidence: ["claim:ocso-tulsa-share"],
    },
  ],
};

export const ACCESS_PATHS: AccessPath[] = [HEADLINE_PATH, SPECULATIVE_PATH];

/** The entity the two surfaces center on by default (ego network + map focus). */
export const FOCUS_ENTITY_ID = "agency:okcpd";
