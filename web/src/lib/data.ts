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

import { existsSync, readFileSync } from "node:fs";
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
import type { CompartmentTileSource } from "./map-tiles";
import type { MapSite, GraphNode, GraphEdge, EntityFixture, AsOfEcho } from "./fixtures";
import { AS_OF, RULESET_VERSION } from "./fixtures";

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
  // P30.3: the SIG-PUB-017 jurisdiction DEMONSTRATIONS (Paris / Brussels fixture dossiers)
  // carry demo facts; a real-data build never lists them as dossiers (§3.1). The P27.5
  // fixture-export harness ships them as an optional presentation artifact instead.
  return [...(parsed as Dossier[]), ...jurisdictionDemos()];
}

/** The SIG-PUB-017 demo dossiers in export mode: only when the bundle ships them (P30.3). */
function jurisdictionDemos(): Dossier[] {
  return readPresentation<Dossier[]>("jurisdiction_dossiers", []);
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
      ...jurisdictionDemos().map((d) => ({
        slug: d.slug,
        subject_label: d.subject_label,
        jurisdiction: d.jurisdiction,
        asOf: d.asOf,
      })),
    ];
  });
}

// --------------------------------------------------------------------------- //
// Site metadata — the belief-pinned citation defaults (P27.6, SIG-UI-048/049,
// ADR-093). Every page's permalink + citation pins the resolved as-of pair and the
// ruleset version. These MUST come from the real export MANIFEST, not the frozen
// `fixtures.ts` demo constant — so a citation captured off the public surface names
// the belief the surface was actually built at (SIG-UI-035, reproducible).
//
//   - `fixtures` mode — the committed `AS_OF` / `RULESET_VERSION` demo constants.
//   - `export` mode   — `<exportDir>/manifest.json` `reproducibility_inputs`
//     (`as_of_snapshot` / `as_of_belief` / `ruleset_version`), the four-value
//     BuildSpec §38.1 the whole release is a pure function of. Fails LOUD if the
//     manifest is missing or malformed (never a silent fall-back — that would
//     fabricate the as-of the surface claims to be pinned at).
// --------------------------------------------------------------------------- //

export interface SiteMetadata {
  /** The resolved two-axis as-of pair echoed in every citation (SIG-API-005). */
  asOf: AsOfEcho;
  /** The reconciliation ruleset version the citation pins to (SIG-UI-035). */
  rulesetVersion: string;
}

/** The reproducibility inputs the export manifest carries (a subset; §38.1 BuildSpec). */
interface ReproducibilityInputs {
  as_of_snapshot: string;
  as_of_belief: string;
  ruleset_version: string;
}

/**
 * The belief-pinned citation defaults for every page (P27.6, deliverable 4). In
 * `export` mode these are read from the real release manifest, so the public
 * surface's canonical origin, permalink and citation are genuinely citable rather
 * than demo values (ADR-093 §5).
 */
/**
 * The per-licence-compartment tile archives the export ships (P30.3, ADR-106): every
 * manifest artifact under `web/tiles/` ending `-sites.pmtiles`, with its ONE licence. The
 * committed fixtures and a jurisdiction export (one `sig-infrastructure.pmtiles`) yield `[]`,
 * leaving the committed style untouched.
 */
export function getCompartmentTileSources(): CompartmentTileSource[] {
  if (dataSource() === "fixtures") return [];
  const path = `${exportDir()}/manifest.json`;
  let parsed: { artifacts?: Array<{ path?: string; compartment?: string; license?: string }> };
  try {
    parsed = JSON.parse(readFileSync(path, "utf-8"));
  } catch (cause) {
    throw new Error(`SIG_DATA_SOURCE=export but the export manifest is unreadable: ${path}`, {
      cause,
    });
  }
  return (parsed.artifacts ?? [])
    .filter((a) => typeof a.path === "string" && /^web\/tiles\/[^/]+-sites\.pmtiles$/.test(a.path))
    .map((a) => ({
      compartment: String(a.compartment),
      license: String(a.license),
      path: `/tiles/${a.path!.slice("web/tiles/".length)}`,
    }))
    .sort((x, y) => x.compartment.localeCompare(y.compartment));
}

export function getSiteMetadata(): SiteMetadata {
  if (dataSource() === "fixtures") {
    return { asOf: AS_OF, rulesetVersion: RULESET_VERSION };
  }
  const path = `${exportDir()}/manifest.json`;
  let raw: string;
  try {
    raw = readFileSync(path, "utf-8");
  } catch (cause) {
    throw new Error(
      `SIG_DATA_SOURCE=export but the export manifest is missing: ${path}. ` +
        "Run `sig-exports build --from-spine --dsn <dsn> --out <dir>` (or the local " +
        "fixture-equivalent `npm run export:fixtures -- <dir>`) first.",
      { cause },
    );
  }
  let parsed: unknown;
  try {
    parsed = JSON.parse(raw);
  } catch (cause) {
    throw new Error(`${path}: not valid JSON`, { cause });
  }
  const repro = (parsed as { reproducibility_inputs?: Partial<ReproducibilityInputs> })
    ?.reproducibility_inputs;
  if (
    !repro ||
    typeof repro.as_of_snapshot !== "string" ||
    typeof repro.as_of_belief !== "string" ||
    typeof repro.ruleset_version !== "string"
  ) {
    throw new Error(
      `${path}: expected a manifest with reproducibility_inputs ` +
        "(as_of_snapshot, as_of_belief, ruleset_version) — got a malformed release manifest",
    );
  }
  const asOfWorld = repro.as_of_snapshot.slice(0, 10);
  const asOfBelief = repro.as_of_belief.slice(0, 10);
  return {
    asOf: {
      as_of_world: asOfWorld,
      as_of_belief: asOfBelief,
      world_defaulted: false,
      belief_defaulted: false,
      question: `as-of world ${asOfWorld}, belief ${asOfBelief}`,
      belief_pinned: true,
    },
    rulesetVersion: repro.ruleset_version,
  };
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
// Export-emitted presentation analytics — `<exportDir>/web/analytics/<name>.json`
// (P31.14 / SURFACE.1, ADR-R9-ANALYTICS; resolves D-P27.5-1).
//
// The spine export emits every analytic the surfaces render — the national-view
// density bins, network centrality + the ego-focus rule, the watch's tracked
// decision point, the per-surface provenance summaries (with the W4..W0 evidence
// tiers for "How we know this"), and the research-queue metadata — as a
// licence-separated, named-denominator artifact family. In `export` mode each
// getter reads its artifact and FAILS LOUD when it is missing or malformed —
// exactly like the nine P27.1 surface getters — so no DEMO constant is reachable
// in an export build. In `fixtures` mode (the CI default) the committed fixture
// constants serve, as before.
//
// The only remaining `web/presentation/` read is `jurisdiction_dossiers` — the
// SIG-PUB-017 FR/BE demonstration dossiers, intentionally demo (see getDossiers);
// `ops/publish.py` refuses a `web/presentation/` tree in a public build.
// --------------------------------------------------------------------------- //

/** The envelope every `web/analytics/<name>.json` artifact carries (ADR-R9-ANALYTICS). */
interface AnalyticsEnvelope {
  schema: string;
  as_of: string;
  denominator: string;
  is_population_total: boolean;
  source_compartments: string[];
}

/** Read `<exportDir>/web/analytics/<name>.json`, failing LOUD on a missing or
 *  malformed artifact — never a silent fall-back (a missing analytic is a build
 *  error, P31.14). `pick` extracts the payload after the envelope is validated. */
function readAnalytics<T>(name: string, pick: (envelope: AnalyticsEnvelope & Record<string, unknown>, path: string) => T): T {
  const path = `${exportDir()}/web/analytics/${name}.json`;
  let raw: string;
  try {
    raw = readFileSync(path, "utf-8");
  } catch (cause) {
    throw new Error(
      `SIG_DATA_SOURCE=export but the analytics artifact is missing: ${path}. ` +
        "Run `sig-exports build --from-spine --dsn <dsn> --out <dir>` (or, for a local " +
        "fixture-equivalent bundle, `npm run export:fixtures -- <dir>`) first.",
      { cause },
    );
  }
  let parsed: unknown;
  try {
    parsed = JSON.parse(raw);
  } catch (cause) {
    throw new Error(`${path}: not valid JSON`, { cause });
  }
  const env = parsed as AnalyticsEnvelope & Record<string, unknown>;
  if (
    typeof env?.schema !== "string" ||
    typeof env?.as_of !== "string" ||
    typeof env?.denominator !== "string" ||
    !Array.isArray(env?.source_compartments)
  ) {
    throw new Error(
      `${path}: not a valid analytics artifact (needs schema / as_of / denominator / source_compartments)`,
    );
  }
  return pick(env, path);
}

/**
 * The remaining OPTIONAL presentation artifact — the SIG-PUB-017 demo dossiers
 * (`web/presentation/jurisdiction_dossiers.json`, P30.3). Deliberately demo
 * content the fixture-export harness ships for the e2e surface; absent → `[]`.
 */
function readPresentation<T>(name: string, fallback: T): T {
  const path = `${exportDir()}/web/presentation/${name}.json`;
  if (!existsSync(path)) return fallback;
  try {
    return JSON.parse(readFileSync(path, "utf-8")) as T;
  } catch (cause) {
    throw new Error(`${path}: not valid JSON`, { cause });
  }
}

/**
 * The site-wide "How we know this" default (SIG-UI-044). Fixtures mode → `undefined` (the
 * component falls back to the committed worked-OKC `DEFAULT_PROVENANCE`). Export mode
 * (P31.14) → the `surfaces.site` summary the spine export emits — real W4..W0 evidence
 * tiers over the publishable claims, the published artifacts, the distinct sources,
 * the dated-observation range, and the honest human-review posture.
 */
export function getSiteProvenance(): ProvenanceSummary | undefined {
  if (dataSource() === "fixtures") return undefined;
  return readAnalytics("provenance", (env, path) => {
    const summary = (env.surfaces as Record<string, unknown> | undefined)?.site;
    if (summary == null) throw new Error(`${path}: provenance carries no surfaces.site summary`);
    return summary as ProvenanceSummary;
  });
}

/** National-zoom density bins for the map (§19.5 H3 bins, SIG-UI-019; export-emitted, P31.14). */
export function getMapDensityBins(): DensityBin[] {
  if (dataSource() === "export") {
    return readAnalytics("density_bins", (env, path) => {
      if (!Array.isArray(env.bins)) throw new Error(`${path}: expected a "bins" array`);
      return env.bins as DensityBin[];
    });
  }
  return DENSITY_BINS;
}

/** Centrality/hub statistics for the network explorer (degree over the typed access edges, P31.14). */
export function getNetworkCentrality(): CentralityStatistic[] {
  if (dataSource() === "export") {
    return readAnalytics("centrality", (env, path) => {
      if (!Array.isArray(env.statistics)) throw new Error(`${path}: expected a "statistics" array`);
      return env.statistics as CentralityStatistic[];
    });
  }
  return CENTRALITY_STATS;
}

/** The entity the network explorer centers its ego view on by default (SIG-UI-022). */
export function getNetworkFocusEntityId(): string {
  if (dataSource() === "export") {
    return readAnalytics("centrality", (env, path) => {
      const focus = env.focus as { entity_id?: unknown } | undefined;
      if (focus == null) throw new Error(`${path}: expected a "focus" block`);
      return typeof focus.entity_id === "string" ? focus.entity_id : "";
    });
  }
  return FOCUS_ENTITY_ID;
}

/**
 * The upcoming decision the evidence recommender ranks for (§39.5a): the earliest
 * derivable decision date the export's renewal watch carries — `null` when none is
 * tracked (an honest "none tracked", never a fabricated urgency).
 */
export function getDecisionPoint(): DecisionPoint | null {
  if (dataSource() === "export") {
    return readAnalytics("decision_point", (env, path) => {
      if (!("decision_point" in env)) throw new Error(`${path}: expected a "decision_point" field`);
      return (env.decision_point ?? null) as DecisionPoint | null;
    });
  }
  return DECISION_POINT;
}

/** The two captures the evidence viewer diffs field-by-field (SIG-UI-029). */
export function getCaptureDiff(): [Capture, Capture] {
  return DIFF_CAPTURES;
}

/** The provenance summary for the corrections surface ("How we know this", SIG-UI-044). */
export function getCorrectionsProvenance(): ProvenanceSummary | undefined {
  if (dataSource() === "export") {
    return readAnalytics("provenance", (env, path) => {
      const summary = (env.surfaces as Record<string, unknown> | undefined)?.corrections;
      if (summary == null)
        throw new Error(`${path}: provenance carries no surfaces.corrections summary`);
      return summary as ProvenanceSummary;
    });
  }
  return CORRECTIONS_PROVENANCE;
}

/** The provenance summary for the research-queue surface (SIG-UI-044). */
export function getResearchQueueProvenance(): ProvenanceSummary | undefined {
  if (dataSource() === "export") {
    return readAnalytics("provenance", (env, path) => {
      const summary = (env.surfaces as Record<string, unknown> | undefined)?.research_queue;
      if (summary == null)
        throw new Error(`${path}: provenance carries no surfaces.research_queue summary`);
      return summary as ProvenanceSummary;
    });
  }
  return RESEARCH_QUEUE_PROVENANCE;
}

/** Live jurisdiction claims for the research queue (§33.5, priority not exclusivity). */
export function getJurisdictionClaims(): JurisdictionClaim[] {
  if (dataSource() === "export") {
    return readAnalytics("queue_meta", (env, path) => {
      if (!Array.isArray(env.jurisdiction_claims))
        throw new Error(`${path}: expected a "jurisdiction_claims" array`);
      return env.jurisdiction_claims as JurisdictionClaim[];
    });
  }
  return JURISDICTION_CLAIMS;
}

/** The as-of date the research queue is rendered at. */
export function getQueueAsOf(): string {
  if (dataSource() === "export") {
    return readAnalytics("queue_meta", (env, path) => {
      if (typeof env.queue_as_of !== "string") throw new Error(`${path}: expected "queue_as_of"`);
      return env.queue_as_of;
    });
  }
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
