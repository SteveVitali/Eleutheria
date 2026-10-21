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

import type { NetworkEdge, NetworkNode, AccessPath } from "./network";
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
    technology: "alpr-fixed",
    technologyStatus: "resolved",
    tier: 0,
    lat: 35.4676,
    lon: -97.5164,
    precision: "full precision (tier 0, public right-of-way)",
  },
  {
    id: "device:okc-002",
    label: "RTCC integration hub",
    jurisdiction: "Oklahoma City",
    technology: "private-camera-integration-live-feeds",
    technologyStatus: "resolved",
    tier: 1,
    lat: 35.4823,
    lon: -97.5352,
    precision: "block-level (tier 1 truncation)",
  },
  {
    id: "device:okc-003",
    label: "Candidate camera — near school",
    jurisdiction: "Oklahoma City",
    technology: "fixed-camera-cctv",
    technologyStatus: "resolved",
    tier: 2,
    lat: 35.49,
    lon: -97.52,
    precision: "H3 cell (tier 2 binning)",
  },
  {
    id: "device:okc-004",
    label: "Confidential facility sensor",
    jurisdiction: "Oklahoma City",
    technology: "fixed-camera-unspecified",
    technologyStatus: "resolved",
    tier: 3,
    lat: 35.5,
    lon: -97.5,
    precision: "jurisdiction only (tier 3 — no geometry published)",
  },
  {
    id: "device:okc-005",
    label: "Patrol-car ALPR (mobile)",
    jurisdiction: "Oklahoma City",
    technology: "alpr-mobile",
    technologyStatus: "resolved",
    tier: 1,
    lat: null,
    lon: null,
    precision: "operating-area only (mobile asset, SIG-GEO-004)",
  },
  {
    id: "device:okc-006",
    label: "Reported camera — conflicting coordinates",
    jurisdiction: "Oklahoma City",
    technologyStatus: "conflicted",
    tier: 2,
    lat: null,
    lon: null,
    precision: "conflicting evidence — no defensible point",
    // P34.15 (K12b NEW-7): a CONTESTED location — evidence exists and disagrees
    // (the export emits the same absence for point_status="conflicted"). The
    // jurisdiction indicator rolls it into the contested count that leads to
    // the dossier, replacing the retired per-record dead task link.
    locationAbsence: "UNRESOLVED",
  },
  {
    id: "device:tulsa-001",
    label: "Reported camera — location unconfirmed",
    jurisdiction: "Tulsa",
    technologyStatus: "unreported",
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
  // P35.20b (ED-44): scheme-qualified jurisdiction keys (P35.18/P35.19) with
  // the full per-key split disclosed; the Tulsa cell is deliberately mixed so
  // the plurality-vs-cell reconciliation is exercised in tests.
  {
    h3: "8a2a1072b59ffff",
    jurisdiction: "iso3166-2:US-OK",
    jurisdictionCounts: { "iso3166-2:US-OK": 41 },
    recordCount: 41,
    coverage: "high",
  },
  {
    h3: "8a2a1072b58ffff",
    jurisdiction: "iso3166-2:US-OK",
    jurisdictionCounts: { "iso3166-2:US-OK": 3 },
    recordCount: 3,
    coverage: "high",
  },
  {
    h3: "8a44a1a3f6bffff",
    jurisdiction: "iso3166-2:US-OK",
    jurisdictionCounts: { "iso3166-2:US-OK": 2 },
    recordCount: 2,
    coverage: "low",
  },
  {
    h3: "8a44a1a3f6affff",
    jurisdiction: "unresolved",
    jurisdictionCounts: { unresolved: 0 },
    recordCount: 0,
    coverage: "none",
  },
  {
    h3: "8a2a1072a4bffff",
    jurisdiction: "iso3166-2:US-OK",
    jurisdictionCounts: { "iso3166-2:US-OK": 11, "iso3166-2:US-KS": 7 },
    recordCount: 18,
    coverage: "partial",
  },
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
  {
    id: "agency:tulsa",
    label: "Tulsa PD",
    type: "agency",
    // P35.30 (SIG-INGEST-043c): a source-stated partner COUNT is a node
    // attribute, never an edge — it carries its own provenance.
    degree: 4,
    degree_claim_ids: ["claim:tulsa-degree-2025"],
    degree_observed_at: "2025-09-01",
  },
  { id: "fusion:ok", label: "Oklahoma fusion center", type: "agency" },
];

/**
 * Edges across all three §12.2 access types — never merged. `configured_access`
 * edges are the composable channels the access-path closure walks; `observed_use` and
 * `declared_policy` are shown but do not compose (mirrors
 * `reconcile.sharing.ACCESS_KINDS` + `inference.access_paths.COMPOSABLE_LABELS`).
 *
 * P35.30 (SIG-EXPORT-D21 draft): every edge carries the relation in words,
 * the observed date + its kind, the source display names, the currency class,
 * and the supporting claim ids — never a count alone. One edge is HISTORICAL
 * (a bounded valid_to) and one UNDATED (no evidenced date — never a fake 1970)
 * so the marking rules have honest fixtures to exercise.
 */
export const NETWORK_EDGES: NetworkEdge[] = [
  {
    from: "agency:okcpd",
    to: "rtcc:okc",
    access_kind: "configured_access",
    relation: "sharing agreement",
    predicate: "sharing agreement",
    direction: "a_to_b",
    observed_at: "2025-11-02",
    date_kind: "observed",
    valid_from_kind: "exact",
    valid_to_kind: "ongoing",
    valid_to: null,
    source: "OKC RTCC records",
    sources: ["OKC RTCC records"],
    currency: "CURRENT",
    historical: false,
    support: "CONFIRMED",
    evidence_count: 3,
    evidence: ["claim:okc-rtcc-mou", "claim:rtcc-config-screenshot", "claim:okc-rtcc-feed-list"],
    claim_ids: ["claim:okc-rtcc-mou", "claim:rtcc-config-screenshot", "claim:okc-rtcc-feed-list"],
  },
  {
    from: "rtcc:okc",
    to: "vendor:flock",
    access_kind: "configured_access",
    relation: "platform feed configured",
    predicate: "platform feed configured",
    direction: "a_to_b",
    observed_at: "2025-08-14",
    date_kind: "observed",
    valid_from_kind: "unknown",
    valid_to_kind: "ongoing",
    valid_to: null,
    source: "OKC RTCC records",
    sources: ["OKC RTCC records"],
    currency: "AGING",
    historical: false,
    support: "STRONGLY_SUPPORTED",
    evidence_count: 2,
    evidence: ["claim:rtcc-flock-integration", "claim:flock-contract-2025"],
    claim_ids: ["claim:rtcc-flock-integration", "claim:flock-contract-2025"],
  },
  {
    from: "vendor:flock",
    to: "agency:ocso",
    access_kind: "configured_access",
    relation: "sharing partner",
    predicate: "sharing partner",
    direction: "a_to_b",
    observed_at: "2024-03-09",
    date_kind: "observed",
    valid_from_kind: "unknown",
    valid_to_kind: "unknown",
    valid_to: null,
    source: "Oklahoma County records",
    sources: ["Oklahoma County records"],
    currency: "STALE",
    historical: false,
    support: "PROBABLE",
    evidence_count: 1,
    evidence: ["claim:flock-ocso-share"],
    claim_ids: ["claim:flock-ocso-share"],
  },
  {
    from: "agency:ocso",
    to: "agency:tulsa",
    access_kind: "configured_access",
    relation: "sharing partner",
    predicate: "sharing partner",
    direction: "a_to_b",
    observed_at: "2025-01-20",
    date_kind: "observed",
    valid_from_kind: "unknown",
    valid_to_kind: "ongoing",
    valid_to: null,
    source: "Oklahoma County records",
    sources: ["Oklahoma County records"],
    currency: "AGING",
    historical: false,
    support: "PROBABLE",
    evidence_count: 1,
    evidence: ["claim:ocso-tulsa-share"],
    claim_ids: ["claim:ocso-tulsa-share"],
  },
  {
    // Historical: the valid period ENDED — marked, and out of the default
    // "current" view (K2 §7 H-3); the relation stays a neutral noun phrase and
    // the mark, not the tense, carries the state.
    from: "agency:tulsa",
    to: "fusion:ok",
    access_kind: "configured_access",
    relation: "sharing MOU",
    predicate: "sharing MOU",
    direction: "a_to_b",
    observed_at: "2023-04-11",
    date_kind: "observed",
    valid_from_kind: "exact",
    valid_to_kind: "exact",
    valid_to: "2025-06-30",
    source: "Tulsa PD policy file",
    sources: ["Tulsa PD policy file"],
    currency: "HISTORICAL",
    historical: true,
    support: "WEAKLY_SUPPORTED",
    evidence_count: 1,
    evidence: ["claim:tulsa-fusion-mou"],
    claim_ids: ["claim:tulsa-fusion-mou"],
  },
  {
    from: "agency:okcpd",
    to: "vendor:flock",
    access_kind: "observed_use",
    relation: "observed query",
    predicate: "observed query",
    direction: "a_to_b",
    observed_at: "2026-04-12",
    date_kind: "observed",
    valid_from_kind: "exact",
    valid_to_kind: "ongoing",
    valid_to: null,
    source: "OKC audit release",
    sources: ["OKC audit release"],
    currency: "CURRENT",
    historical: false,
    support: "STRONGLY_SUPPORTED",
    evidence_count: 2,
    evidence: ["claim:audit-log-2026-03", "claim:query-export-2026-04"],
    claim_ids: ["claim:audit-log-2026-03", "claim:query-export-2026-04"],
  },
  {
    // Undated: the claim records no observation date — `date_kind` says so and
    // no synthetic epoch is ever rendered (SIG-TIME-012 class honesty).
    from: "agency:okcpd",
    to: "agency:ocso",
    access_kind: "declared_policy",
    relation: "sharing MOU (declared)",
    predicate: "sharing MOU (declared)",
    direction: "a_to_b",
    observed_at: null,
    date_kind: "undated",
    valid_from_kind: "unknown",
    valid_to_kind: "unknown",
    valid_to: null,
    source: "OKC PD policy file",
    sources: ["OKC PD policy file"],
    currency: "UNDATED",
    historical: false,
    support: "CONFIRMED",
    evidence_count: 1,
    evidence: ["claim:okc-ocso-mou-doc"],
    claim_ids: ["claim:okc-ocso-mou-doc"],
  },
];

/**
 * P34.15 (K2 NEW-6, D-K2-2, SIG-IDENT-030 by abstention): no centrality
 * statistic and no fabricated ER eval ships in the fixtures — organisation
 * entity resolution has not passed its gate, so neither the figures nor the
 * invented precision/recall numbers that once decorated them are published.
 * The `CentralityStatistic`/`ErQuality` machinery stays in `network.ts` for
 * the gate's return — its structural disclosure contract is unchanged.
 */

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
