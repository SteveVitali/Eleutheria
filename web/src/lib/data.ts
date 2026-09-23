// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * The web data layer (P21.4, deliverable 2; ADR-066).
 *
 * The shell is static-first (SIG-UI-036): it reads its data at BUILD time, never
 * from a live API in the browser, so nothing here ships to the client — the
 * zero-JS budget is unchanged. This module is the single seam through which the
 * pages get their data, so the source can be swapped without touching a page:
 *
 *   - `SIG_DATA_SOURCE=fixtures` (the DEFAULT, so CI is unchanged) — the committed
 *     typed fixtures (`web/src/lib/*-fixture.ts`), exactly as before.
 *   - `SIG_DATA_SOURCE=export` — the output of `sig-exports build --jurisdiction
 *     <j>` (JSON/Parquet-derived JSON + a PMTiles path), read from the export
 *     directory at build time. This is how the composed stack builds the static
 *     site *from the exports* (§38.1: "a hand-built export is a different dataset
 *     wearing the same name" — the site and the export agree by construction).
 *
 * `export` mode fails LOUD if the export directory / a required artifact is absent
 * (never a silent fall-back to fixtures — that would fabricate green). The export
 * carries the same `/v1` dossier contract the fixtures do, so the page code is
 * identical in both modes.
 */

import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { DOSSIERS } from "./dossier-fixture";
import { JURISDICTION_DOSSIERS } from "./dossier-jurisdiction-fixture";
import type { Dossier } from "./dossier";
import { LEVERAGE_METRIC_FIXTURE, type LeverageMetric } from "./leverage-fixture";

// The per-surface contract types (P27.1) the getters below are typed against.
import type { MapAsset, DensityBin } from "./map";
import type { NetworkNode, NetworkEdge, AccessPath, CentralityStatistic } from "./network";
import type { FreshnessRow, CoverageMetric } from "./metrics";
import type { ContractWatchItem } from "./watch";
import type { EvidenceArtifact, DecisionPoint } from "./recommender";
import type { ClaimView, Capture } from "./evidence-viewer";
import type { CorrectionEntry } from "./corrections";
import type { ResearchTaskCard, JurisdictionClaim } from "./research-queue";
import type { ProvenanceSummary } from "./provenance";
import type { HostileReaderReview } from "./editorial";
import type { MapSite, GraphNode, GraphEdge, EntityFixture } from "./fixtures";

// The committed fixtures the data layer serves in `fixtures` mode (and that the P27.5
// fixture-export harness serialises into the export layout). The PAGES import none of
// these directly — the data layer is the single seam (ADR-066, SIG-UI-036).
import {
  MAP_ASSETS,
  DENSITY_BINS,
  NETWORK_NODES,
  NETWORK_EDGES,
  ACCESS_PATHS,
  CENTRALITY_STATS,
  FOCUS_ENTITY_ID,
} from "./map-network-fixture";
import {
  FRESHNESS_ROWS,
  COVERAGE_METRICS,
  CORRECTIONS,
  CORRECTIONS_PROVENANCE,
  RESEARCH_QUEUE,
  RESEARCH_QUEUE_PROVENANCE,
  JURISDICTION_CLAIMS,
  QUEUE_AS_OF,
  HOSTILE_READER_REVIEW,
  GENERATED_RATIONALE_TEMPLATES,
} from "./corrections-methodology-fixture";
import {
  WATCH_ITEMS,
  DECISION_POINT,
  EVIDENCE_ARTIFACTS,
  CLAIM_VIEWS,
  DIFF_CAPTURES,
} from "./watch-evidence-fixture";
import {
  REFERENCE_MAP_SITES,
  REFERENCE_GRAPH_NODES,
  REFERENCE_GRAPH_EDGES,
  OKCPD,
} from "./fixtures";

export type DataSource = "fixtures" | "export";

/** The active data source (build-time env; defaults to `fixtures` so CI is unchanged). */
export function dataSource(): DataSource {
  return process.env.SIG_DATA_SOURCE === "export" ? "export" : "fixtures";
}

/** The repository root, resolved from this module's URL (web/src/lib/data.ts → root). */
function repoRoot(): string {
  return fileURLToPath(new URL("../../../", import.meta.url));
}

/**
 * The export directory `sig-exports build --jurisdiction <j> --out <dir>` wrote.
 * `SIG_EXPORT_DIR` overrides; the default is the OKC output path the composed run
 * (`docs/build/tools/run_okc.sh`) uses.
 */
export function exportDir(): string {
  return process.env.SIG_EXPORT_DIR ?? `${repoRoot()}exports/out/okc`;
}

/**
 * The dossiers the site renders. In `fixtures` mode this is the committed fixture
 * set; in `export` mode it is `<exportDir>/web/dossiers.json` — the web-shaped
 * dossier bundle the jurisdiction export emits (the same `Dossier` contract).
 */
export function getDossiers(): Dossier[] {
  if (dataSource() === "fixtures") return DOSSIERS;
  const path = `${exportDir()}/web/dossiers.json`;
  let raw: string;
  try {
    raw = readFileSync(path, "utf-8");
  } catch (cause) {
    throw new Error(
      `SIG_DATA_SOURCE=export but the export dossier bundle is missing: ${path}. ` +
        `Run \`sig-exports build --jurisdiction <j> --out <dir>\` first ` +
        `(see docs/build/tools/run_okc.sh).`,
      { cause },
    );
  }
  const parsed: unknown = JSON.parse(raw);
  if (!Array.isArray(parsed)) {
    throw new Error(`${path}: expected a JSON array of dossiers, got ${typeof parsed}`);
  }
  // The export carries the real jurisdiction (OKC). The FR/BE dossiers are the
  // SIG-PUB-017 publication-adapter *demonstrations* the shell ships regardless of
  // data source (they show the jurisdiction-conditional withholding, not export
  // data), so they render in both modes and the e2e/a11y surface is identical.
  return [...(parsed as Dossier[]), ...JURISDICTION_DOSSIERS];
}

/**
 * The §7 contribution-back leverage metric (P21.7, SIG-CONTRIB-016e): the count of
 * SIG-originated operator-attribution suggestions accepted upstream, read from the
 * public OSM changeset feed via the declared hashtag.
 *
 *   - `fixtures` mode — the committed sample (`leverage-fixture.ts`).
 *   - `export` mode — `<exportDir>/web/leverage.json`, produced by
 *     `sig-tasks osm-feed pull --out <dir>` (`tasks.osm_feed.leverage_metric_json`).
 *
 * `export` mode fails LOUD if the artifact is missing — never a silent fall-back to
 * fixtures (that would fabricate the metric). The record carries only the hashtag,
 * the accepted count, and the attributed changeset ids — no OSM user data
 * (Part VIII §0.7).
 */
export function getLeverageMetric(): LeverageMetric {
  if (dataSource() === "fixtures") return LEVERAGE_METRIC_FIXTURE;
  const path = `${exportDir()}/web/leverage.json`;
  let raw: string;
  try {
    raw = readFileSync(path, "utf-8");
  } catch (cause) {
    throw new Error(
      `SIG_DATA_SOURCE=export but the leverage metric artifact is missing: ${path}. ` +
        `Run \`sig-tasks osm-feed pull --out <dir>\` first (P21.7).`,
      { cause },
    );
  }
  const parsed = JSON.parse(raw) as Partial<LeverageMetric>;
  if (
    typeof parsed.hashtag !== "string" ||
    typeof parsed.accepted_operator_attributions !== "number" ||
    !Array.isArray(parsed.attributed_changeset_ids)
  ) {
    throw new Error(`${path}: not a valid leverage metric record`);
  }
  return parsed as LeverageMetric;
}

// --------------------------------------------------------------------------- //
// The per-surface getters (P27.5, LAUNCH.5) — the frozen P27.1 contracts.
//
// Every public surface reads its data through ONE of these. In `fixtures` mode
// (the CI default) each returns the committed fixture; in `export` mode each reads
// `<exportDir>/web/<artifact>.json` — the web-shaped bundle the P27.4 spine export
// emits — and FAILS LOUD if the artifact is missing or malformed. There is NEVER a
// silent fall-back to fixtures in export mode: a missing artifact is a build error,
// because a green build off missing data would fabricate the surface (SIG-UI-036,
// the §3.1 defining standard).
// --------------------------------------------------------------------------- //

/** Read + parse `<exportDir>/web/<name>`, failing LOUD (never a silent fixtures fall-back). */
function readExportArtifact<T>(name: string, validate: (parsed: unknown, path: string) => T): T {
  const path = `${exportDir()}/web/${name}`;
  let raw: string;
  try {
    raw = readFileSync(path, "utf-8");
  } catch (cause) {
    throw new Error(
      `SIG_DATA_SOURCE=export but the export artifact is missing: ${path}. ` +
        "Run `sig-exports build --from-spine --dsn <dsn> --out <dir>` (or, for a local " +
        "fixture-equivalent bundle, `node web/scripts/build-fixture-export.<dir>`) first.",
      { cause },
    );
  }
  let parsed: unknown;
  try {
    parsed = JSON.parse(raw);
  } catch (cause) {
    throw new Error(`${path}: not valid JSON`, { cause });
  }
  return validate(parsed, path);
}

function requireArray(parsed: unknown, path: string): unknown[] {
  if (!Array.isArray(parsed)) {
    throw new Error(`${path}: expected a JSON array, got ${typeof parsed}`);
  }
  return parsed;
}

/** Surface 3 — the map layer's assets (§39.3, `map.ts#MapAsset`). Export: `web/map.json` `.assets`. */
export function getMapSites(): MapAsset[] {
  if (dataSource() === "fixtures") return MAP_ASSETS;
  return readExportArtifact("map.json", (parsed, path) => {
    const assets = (parsed as { assets?: unknown })?.assets;
    if (!Array.isArray(assets)) {
      throw new Error(`${path}: expected an object with an "assets" array (map layer)`);
    }
    return assets as MapAsset[];
  });
}

/** Surface 4 — the sharing network (§39.4). Export: `web/network.json`. */
export interface NetworkData {
  nodes: NetworkNode[];
  edges: NetworkEdge[];
  accessPaths: AccessPath[];
}

export function getNetwork(): NetworkData {
  if (dataSource() === "fixtures") {
    return { nodes: NETWORK_NODES, edges: NETWORK_EDGES, accessPaths: ACCESS_PATHS };
  }
  return readExportArtifact("network.json", (parsed, path) => {
    const o = parsed as { nodes?: unknown; edges?: unknown; access_paths?: unknown };
    if (!Array.isArray(o?.nodes) || !Array.isArray(o?.edges)) {
      throw new Error(`${path}: expected an object with "nodes" and "edges" arrays`);
    }
    return {
      nodes: o.nodes as NetworkNode[],
      edges: o.edges as NetworkEdge[],
      accessPaths: (Array.isArray(o.access_paths) ? o.access_paths : []) as AccessPath[],
    };
  });
}

/** Surface 5 — per-source data freshness (§32.4). Export: `web/freshness.json`. */
export function getFreshness(): FreshnessRow[] {
  if (dataSource() === "fixtures") return FRESHNESS_ROWS;
  return readExportArtifact("freshness.json", (p, path) => requireArray(p, path) as FreshnessRow[]);
}

/** Surface 6 — coverage metrics (§32.5). Export: `web/coverage.json`. */
export function getCoverage(): CoverageMetric[] {
  if (dataSource() === "fixtures") return COVERAGE_METRICS;
  return readExportArtifact("coverage.json", (p, path) => requireArray(p, path) as CoverageMetric[]);
}

/** Surface 7 — the renewal/contract watch (§39.5). Export: `web/watch.json`. */
export function getWatch(): ContractWatchItem[] {
  if (dataSource() === "fixtures") return WATCH_ITEMS;
  return readExportArtifact("watch.json", (p, path) => requireArray(p, path) as ContractWatchItem[]);
}

/** Surface 8 — the evidence recommender + viewer (§39.5a/§39.6). Export: `web/evidence.json`. */
export interface EvidenceData {
  artifacts: EvidenceArtifact[];
  claimViews: ClaimView[];
}

export function getEvidence(): EvidenceData {
  if (dataSource() === "fixtures") {
    return { artifacts: EVIDENCE_ARTIFACTS, claimViews: CLAIM_VIEWS };
  }
  return readExportArtifact("evidence.json", (parsed, path) => {
    const o = parsed as { artifacts?: unknown; claim_views?: unknown };
    if (!Array.isArray(o?.artifacts)) {
      throw new Error(`${path}: expected an object with an "artifacts" array`);
    }
    return {
      artifacts: o.artifacts as EvidenceArtifact[],
      claimViews: (Array.isArray(o.claim_views) ? o.claim_views : []) as ClaimView[],
    };
  });
}

/** Surface 9 — the public corrections log (§39.8). Export: `web/corrections.json`. */
export function getCorrections(): CorrectionEntry[] {
  if (dataSource() === "fixtures") return CORRECTIONS;
  return readExportArtifact("corrections.json", (p, path) => requireArray(p, path) as CorrectionEntry[]);
}

/** Surface 10 — the research queue (§39.7). Export: `web/research_queue.json`. */
export function getResearchQueue(): ResearchTaskCard[] {
  if (dataSource() === "fixtures") return RESEARCH_QUEUE;
  return readExportArtifact(
    "research_queue.json",
    (p, path) => requireArray(p, path) as ResearchTaskCard[],
  );
}

/** Surface 1 — the dossier index / national landing list (§39.2). Export: `web/dossier_index.json`. */
export type DossierIndexRow = Pick<Dossier, "slug" | "subject_label" | "jurisdiction" | "asOf">;

export function getDossierIndex(): DossierIndexRow[] {
  if (dataSource() === "fixtures") {
    return [...DOSSIERS, ...JURISDICTION_DOSSIERS].map((d) => ({
      slug: d.slug,
      subject_label: d.subject_label,
      jurisdiction: d.jurisdiction,
      asOf: d.asOf,
    }));
  }
  return readExportArtifact("dossier_index.json", (p, path) => {
    const rows = requireArray(p, path) as DossierIndexRow[];
    // The export emits the real jurisdictions; the SIG-PUB-017 FR/BE demonstration
    // dossiers ship regardless of data source (as getDossiers appends them), so the
    // index echoes them too and the surface is identical in both modes.
    return [
      ...rows,
      ...JURISDICTION_DOSSIERS.map((d) => ({
        slug: d.slug,
        subject_label: d.subject_label,
        jurisdiction: d.jurisdiction,
        asOf: d.asOf,
      })),
    ];
  });
}

// --------------------------------------------------------------------------- //
// Build-time pagination / summarisation for national-scale surfaces (P27.5
// deliverable 3). At national scale the freshness table is ~210 sources and the map's
// tabular equivalent is tens of thousands of sites; an unbounded static table blows
// the a11y/perf budget. `capRows` bounds a table at build time and reports the honest
// total so the page can say "showing N of M" rather than silently dropping rows. The
// detailed, paginated table shapes are finalised in P27.7; this is the minimal guard.
// --------------------------------------------------------------------------- //

/** The maximum number of rows a single static table renders before it is capped. */
export const MAX_TABLE_ROWS = 500;

export interface CappedRows<T> {
  /** The rows to render (at most `max`). */
  rows: T[];
  /** The honest total before capping. */
  total: number;
  /** How many rows are shown. */
  shown: number;
  /** Whether rows were dropped (so the page states "showing N of M"). */
  truncated: boolean;
}

/** Cap a table at `max` rows at build time, preserving the honest total (P27.5 d3). */
export function capRows<T>(rows: readonly T[], max: number = MAX_TABLE_ROWS): CappedRows<T> {
  const total = rows.length;
  const shown = Math.min(total, Math.max(0, max));
  return { rows: rows.slice(0, shown), total, shown, truncated: total > shown };
}

// --------------------------------------------------------------------------- //
// Auxiliary / presentation data — committed constants, IDENTICAL in both modes.
//
// These are NOT part of the frozen P27.1 export contract (the schema deliberately
// omits them): the national-view density bins and the network centrality/ER-quality
// analytics are DERIVED presentation aids the export pipeline does not emit yet
// (D-P27.5-1), and the decision point, capture diff, provenance summaries, jurisdiction
// claims and editorial constants are page-scoped presentation data, not spine surfaces.
// They are routed through the data layer so that NO page imports a fixture module
// directly (the single-seam invariant) — but they carry no export artifact and so
// never fail loud. Each is honestly the same in `fixtures` and `export` mode.
// --------------------------------------------------------------------------- //

/** National-zoom density bins for the map (presentation analytic; see D-P27.5-1). */
export function getMapDensityBins(): DensityBin[] {
  return DENSITY_BINS;
}

/** Centrality/hub statistics for the network explorer (presentation analytic; D-P27.5-1). */
export function getNetworkCentrality(): CentralityStatistic[] {
  return CENTRALITY_STATS;
}

/** The entity the network explorer centers its ego view on by default (SIG-UI-022). */
export function getNetworkFocusEntityId(): string {
  return FOCUS_ENTITY_ID;
}

/** The upcoming decision the evidence recommender ranks for (§39.5a). */
export function getDecisionPoint(): DecisionPoint {
  return DECISION_POINT;
}

/** The two captures the evidence viewer diffs field-by-field (SIG-UI-029). */
export function getCaptureDiff(): [Capture, Capture] {
  return DIFF_CAPTURES;
}

/** The provenance summary for the corrections surface ("How we know this", SIG-UI-044). */
export function getCorrectionsProvenance(): ProvenanceSummary {
  return CORRECTIONS_PROVENANCE;
}

/** The provenance summary for the research-queue surface (SIG-UI-044). */
export function getResearchQueueProvenance(): ProvenanceSummary {
  return RESEARCH_QUEUE_PROVENANCE;
}

/** Live jurisdiction claims for the research queue (§33.5, priority not exclusivity). */
export function getJurisdictionClaims(): JurisdictionClaim[] {
  return JURISDICTION_CLAIMS;
}

/** The as-of date the research queue is rendered at. */
export function getQueueAsOf(): string {
  return QUEUE_AS_OF;
}

/** The recorded hostile-reader review for the editorial-standards page (§41, SIG-UI-042). */
export function getHostileReaderReview(): HostileReaderReview {
  return HOSTILE_READER_REVIEW;
}

/** The generated rationale templates the style guide gates against the register rules (SIG-UI-046). */
export function getRationaleTemplates(): readonly string[] {
  return GENERATED_RATIONALE_TEMPLATES;
}

// --- Reference / component-demo pages (SIG-UI-037). These render the API-wire-contract
// exemplars (not spine surfaces); routed through the data layer so the pages import no
// fixture module directly. Identical in both modes.

/** The reference map's tabular-equivalent sites. */
export function getReferenceMapSites(): MapSite[] {
  return REFERENCE_MAP_SITES;
}

/** The reference sharing graph (nodes + edges). */
export function getReferenceGraph(): { nodes: GraphNode[]; edges: GraphEdge[] } {
  return { nodes: REFERENCE_GRAPH_NODES, edges: REFERENCE_GRAPH_EDGES };
}

/** The worked entity fixture (OKCPD) the reference map's popup renders. */
export function getReferenceEntity(): EntityFixture {
  return OKCPD;
}
