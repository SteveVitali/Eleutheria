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

import { existsSync, readFileSync, readdirSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { DOSSIERS } from "./dossier-fixture";
import { JURISDICTION_DOSSIERS } from "./dossier-jurisdiction-fixture";
import { applyPublicationPolicy, unplacedPath } from "./dossier";
import type { Dossier, TerminationInput } from "./dossier";
import { RESEARCH_PORTFOLIO_FIXTURE } from "./research-dossier-fixture";
import {
  assertNoFutureDisplayDates,
  emptyPortfolio,
  type ResearchDossierPortfolio,
} from "./research-dossier";
import { LEVERAGE_METRIC_FIXTURE, type LeverageMetric } from "./leverage-fixture";

// The per-surface contract types (P27.1) the getters below are typed against.
import type { MapAsset, DensityBin } from "./map";
import type { NetworkNode, NetworkEdge, AccessPath } from "./network";
import type { FreshnessRow, CoverageMetric } from "./metrics";
import type { ContractWatchItem } from "./watch";
import type { EvidenceArtifact, DecisionPoint } from "./recommender";
import type { ClaimView, Capture } from "./evidence-viewer";
import type { CorrectionEntry } from "./corrections";
import type { ResearchTaskCard, JurisdictionClaim } from "./research-queue";
import type { ProvenanceSummary } from "./provenance";
import { DEFAULT_PROVENANCE } from "./provenance";
import type { HostileReaderReview } from "./editorial";
import type { CompartmentTileSource } from "./map-tiles";
import { RELEASE_CATALOG_FIXTURE } from "./releases-fixture";
import type { ReleaseCatalog } from "./releases";
import type { MapSite, GraphNode, GraphEdge, EntityFixture, AsOfEcho } from "./fixtures";
import { AS_OF, RULESET_VERSION } from "./fixtures";
// P34.19 (F-337/F-403): the committed publication-withdrawal list + the
// express-terms disclosure contract — every export-mode payload keyed on a
// suppressed claim/entity/upstream id is filtered by ONE shared list.
import { dropWithdrawn, isWithdrawn } from "./withdrawals";
import {
  isTermsDisclosure,
  TERMS_DISCLOSURE_FIXTURE,
  type TermsDisclosure,
} from "./terms-disclosure";
import { SOURCES_FIXTURE, sourceLicenceTable, type SourceLicenceRow } from "./sources";
import {
  SOURCE_COUNTS_FIXTURE,
  SOURCE_ROWS_DOC_FIXTURE,
  isSourceCountsDoc,
  isSourceRowsDoc,
  type SourceCountsDoc,
  type SourceRowsDoc,
} from "./source-counts";
import { isResolutionEval, type ResolutionEval } from "./resolution-eval";
import { STATEMENT_FIXTURES } from "./statements-fixture";
import type { StatementRow } from "./provenance-panel";
import { isDataDictionary, type DataDictionary } from "./dictionary";
import { DICTIONARY_FIXTURE } from "./dictionary-fixture";

// The committed fixtures the data layer serves in `fixtures` mode (and that the P27.5
// fixture-export harness serialises into the export layout). The PAGES import none of
// these directly — the data layer is the single seam (ADR-066, SIG-UI-036).
import {
  MAP_ASSETS,
  DENSITY_BINS,
  NETWORK_NODES,
  NETWORK_EDGES,
  ACCESS_PATHS,
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

export type DataSource = "fixtures" | "export" | "national";

/**
 * The active data source (build-time env; defaults to `fixtures` so CI is
 * unchanged). `national` (P35.51, SIG-FIND-005, K0 §4.12.6) is a DECLARED
 * overlay: the generated deterministic national fixture supplies the heavy
 * artifacts it names (`web/map.json`, `web/network.json`,
 * `web/tiles/*-sites.pmtiles`, `manifest.json`, `<comp>/ATTRIBUTION.json`,
 * `web/jurisdiction_key_map.json`), and every surface the overlay does not
 * cover serves the committed fixture corpus — `dataSource() !== "export"`
 * reads the committed fixture, never a silent export read. The national
 * manifest lists exactly the artifacts the overlay owns; a missing or
 * malformed one fails LOUD like an export read.
 */
export function dataSource(): DataSource {
  const v = process.env.SIG_DATA_SOURCE;
  if (v === "export") return "export";
  if (v === "national") return "national";
  return "fixtures";
}

/**
 * The repository root. `import.meta.url` is not stable across bundling: in the
 * prerender worker this module is a chunk under `web/dist/.prerender/chunks/`,
 * so a fixed `../../../` lands at `web/`, not the workspace root. Walk up until
 * the `uv.lock` workspace marker is found; that file exists only at the root.
 */
function repoRoot(): string {
  let dir = fileURLToPath(new URL(".", import.meta.url));
  for (;;) {
    if (existsSync(`${dir}uv.lock`)) return dir.endsWith("/") ? dir : `${dir}/`;
    const parent = dir.replace(/[^/]+\/?$/, "");
    if (parent === dir || parent === "") {
      throw new Error(`repoRoot: walked above ${dir} without finding uv.lock`);
    }
    dir = parent;
  }
}

/**
 * The export directory `sig-exports build --jurisdiction <j> --out <dir>` wrote.
 * `SIG_EXPORT_DIR` overrides; the default is the OKC output path the composed run
 * (`docs/build/tools/run_okc.sh`) uses.
 */
export function exportDir(): string {
  const override = process.env.SIG_EXPORT_DIR;
  if (override !== undefined && override !== "") {
    // `npm --prefix web` runs scripts with cwd=web/, so a repo-relative
    // `SIG_EXPORT_DIR` must be anchored at the repo root, not the cwd.
    return override.startsWith("/") ? override : `${repoRoot()}${override}`;
  }
  return `${repoRoot()}exports/out/okc`;
}

/**
 * The directory `scripts/ci/build_national_fixture.py` wrote — the
 * deterministic synthetic national fixture (≥ 232k sites / ≥ 5k agencies /
 * ≥ 400k sharing edges, invented names only, F-173). `SIG_NATIONAL_DIR`
 * overrides; the default is the gitignored `web/national/` the
 * `fixture:national` npm script regenerates.
 */
export function nationalDir(): string {
  const override = process.env.SIG_NATIONAL_DIR;
  if (override !== undefined && override !== "") {
    return override.startsWith("/") ? override : `${repoRoot()}${override}`;
  }
  return `${repoRoot()}web/national`;
}

/** Read + parse `<nationalDir>/web/<name>` — the national overlay's artifacts
 * fail LOUD exactly like an export read (SIG-UI-036: never a silent fixture
 * fall-back inside an overlay read). */
function readNationalArtifact<T>(
  name: string,
  validate: (parsed: unknown, path: string) => T,
): T {
  const path = `${nationalDir()}/web/${name}`;
  let raw: string;
  try {
    raw = readFileSync(path, "utf-8");
  } catch (cause) {
    throw new Error(
      `SIG_DATA_SOURCE=national but the national fixture artifact is missing: ${path}. ` +
        "Regenerate the fixture (`npm run fixture:national`, " +
        "scripts/ci/build_national_fixture.py) — the overlay names this artifact.",
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

/**
 * The layout root a heavy-artifact read uses: the national fixture dir under
 * `national`, the export dir under `export` (never reached under `fixtures`).
 */
function layoutDir(): string {
  return dataSource() === "national" ? nationalDir() : exportDir();
}

/**
 * The dossiers the site renders. In `fixtures` mode this is the committed fixture
 * set; in `export` mode it is `<exportDir>/web/dossiers.json` — the web-shaped
 * dossier bundle the jurisdiction export emits (the same `Dossier` contract).
 *
 * Every dossier passes through `applyPublicationPolicy` HERE — the single data
 * funnel — so the officer-naming + jurisdiction gates (SIG-PUB-007/008/017,
 * P35.28) bind on ALL dossier surfaces: the page still applies the gate at
 * render (`[slug].astro`, idempotent — it only ever withholds), and the print
 * export, the static JSON endpoint, and the map/list readers inherit it through
 * this funnel (the E1/NEW-12 defect class: a gated row must never reach a
 * built surface ungated).
 */
export function getDossiers(): Dossier[] {
  if (dataSource() !== "export") {
    return DOSSIERS.map((d) => applyPublicationPolicy(d));
  }
  // P35.45: the per-dossier artifact set — `web/dossiers/<slug-path>.json`
  // (nested paths mirroring the canonical jurisdiction chain) — supersedes
  // the `web/dossiers.json` monolith, which a pre-P35.45 export still emits.
  // Both are read; the directory wins when it exists.
  const dir = `${exportDir()}/web/dossiers`;
  let exportDossiers: Dossier[];
  if (existsSync(dir)) {
    const files: string[] = [];
    const walk = (sub: string): void => {
      for (const entry of readdirSync(`${dir}${sub}`, { withFileTypes: true })) {
        if (entry.isDirectory()) walk(`${sub}/${entry.name}`);
        else if (entry.name.endsWith(".json") && entry.name !== "index.json") {
          files.push(`${sub}/${entry.name}`);
        }
      }
    };
    walk("");
    exportDossiers = dropWithdrawn(
      files
        .sort()
        .map((f) => JSON.parse(readFileSync(`${dir}${f}`, "utf-8")) as Dossier),
    );
  } else {
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
    exportDossiers = dropWithdrawn(parsed as Dossier[]);
  }
  // The export carries the real jurisdiction (OKC). The FR/BE dossiers are the
  // SIG-PUB-017 publication-adapter *demonstrations* the shell ships regardless of
  // data source (they show the jurisdiction-conditional withholding, not export
  // data), so they render in both modes and the e2e/a11y surface is identical.
  // P30.3: the SIG-PUB-017 jurisdiction DEMONSTRATIONS (Paris / Brussels fixture dossiers)
  // carry demo facts; a real-data build never lists them as dossiers (§3.1). The P27.5
  // fixture-export harness ships them as an optional presentation artifact instead.
  return [...exportDossiers, ...jurisdictionDemos()].map((d) => applyPublicationPolicy(d));
}

/** The SIG-PUB-017 demo dossiers in export mode: only when the bundle ships them (P30.3). */
function jurisdictionDemos(): Dossier[] {
  return readPresentation<Dossier[]>("jurisdiction_dossiers", []);
}

/**
 * The reviewed research-dossier portfolio (P32.17, SIG-DOS-001/002) —
 * `sig.dossier-portfolio/1`, a SEPARATE artifact class from the §39.2 inventory
 * dossiers above: an evidence-complete twelve-question portfolio where every
 * answer carries a state, an evidence or search basis, and a fact-to-capture
 * citation.
 *
 *   - `fixtures` mode — the committed fixture portfolio (exercises all six
 *     answer states).
 *   - `export` mode — `<exportDir>/web/research_dossiers.json`, emitted by
 *     `sig-exports` only when reviewed `sig.dossier-packet/1` inputs were
 *     supplied. A MISSING artifact is honest absence (no reviewed dossier is
 *     authored yet) and reads as the empty portfolio — unlike the inventory
 *     bundle, it is never a build error: packets are authored per dossier
 *     ticket, not minted mechanically.
 */
export function getResearchDossierPortfolio(): ResearchDossierPortfolio {
  let portfolio: ResearchDossierPortfolio;
  if (dataSource() !== "export") {
    portfolio = RESEARCH_PORTFOLIO_FIXTURE;
  } else {
    const path = `${exportDir()}/web/research_dossiers.json`;
    try {
      const parsed = JSON.parse(readFileSync(path, "utf-8")) as ResearchDossierPortfolio;
      if (!Array.isArray(parsed.dossiers)) {
        throw new Error(`${path}: .dossiers is not an array`);
      }
      portfolio = parsed;
    } catch (cause) {
      if ((cause as NodeJS.ErrnoException).code === "ENOENT") return emptyPortfolio();
      throw cause;
    }
  }
  // P34.35 (DR-C4-15): the build-time date guard — a displayed date later
  // than the build clock fails the build here, on every render path.
  for (const d of portfolio.dossiers) assertNoFutureDisplayDates(d);
  return portfolio;
}

/**
 * The §7 contribution-back leverage metric (P21.7, SIG-CONTRIB-016e): the count of
 * SIG-originated operator-attribution suggestions accepted upstream, read from the
 * public OSM changeset feed via the declared hashtag.
 *
 *   - `fixtures` mode — the committed sample (`leverage-fixture.ts`).
 *   - `export` mode — `<exportDir>/web/leverage.json`, a first-class web
 *     artifact of every spine export since P34.34a (`build_spine_export`
 *     writes the recorded metric, or the honest zeroed ledger when no
 *     changeset feed was bound; the standalone
 *     `sig-tasks osm-feed pull --out <dir>` emits the same shape).
 *
 * `export` mode fails LOUD if the artifact is missing — never a silent
 * fall-back to fixtures (that would fabricate the metric). A missing file on a
 * P34.34a-era export means the export is stale or malformed, so the error names
 * the export build. The record carries only the hashtag, the accepted count,
 * and the attributed changeset ids — no OSM user data (Part VIII §0.7).
 */
export function getLeverageMetric(): LeverageMetric {
  if (dataSource() !== "export") return LEVERAGE_METRIC_FIXTURE;
  const path = `${exportDir()}/web/leverage.json`;
  let raw: string;
  try {
    raw = readFileSync(path, "utf-8");
  } catch (cause) {
    throw new Error(
      `SIG_DATA_SOURCE=export but the leverage metric artifact is missing: ${path}. ` +
        `Rebuild the export (\`sig-exports build\` emits it since P34.34a) or ` +
        `run \`sig-tasks osm-feed pull --out <dir>\` (P21.7).`,
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
  if (dataSource() === "national") {
    // The national overlay's declared map layer — ≥ 232k synthetic sites.
    return readNationalArtifact("map.json", (parsed, path) => {
      const assets = (parsed as { assets?: unknown })?.assets;
      if (!Array.isArray(assets)) {
        throw new Error(`${path}: expected an object with an "assets" array (map layer)`);
      }
      return assets as MapAsset[];
    });
  }
  if (dataSource() !== "export") return MAP_ASSETS;
  return readExportArtifact("map.json", (parsed, path) => {
    const assets = (parsed as { assets?: unknown })?.assets;
    if (!Array.isArray(assets)) {
      throw new Error(`${path}: expected an object with an "assets" array (map layer)`);
    }
    return dropWithdrawn(assets as MapAsset[]);
  });
}

/** Surface 4 — the sharing network (§39.4). Export: `web/network.json`. */
export interface NetworkData {
  nodes: NetworkNode[];
  edges: NetworkEdge[];
  accessPaths: AccessPath[];
}

export function getNetwork(): NetworkData {
  if (dataSource() === "national") {
    // The national overlay's declared graph — ≥ 5k agency nodes + ≥ 400k
    // sharing edges (the prop-window the page serves stays bounded).
    return readNationalArtifact("network.json", (parsed, path) => {
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
  if (dataSource() !== "export") {
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
  if (dataSource() !== "export") return FRESHNESS_ROWS;
  return readExportArtifact("freshness.json", (p, path) => requireArray(p, path) as FreshnessRow[]);
}

/** Surface 6 — coverage metrics (§32.5). Export: `web/coverage.json`. */
export function getCoverage(): CoverageMetric[] {
  if (dataSource() !== "export") return COVERAGE_METRICS;
  return readExportArtifact("coverage.json", (p, path) => requireArray(p, path) as CoverageMetric[]);
}

/**
 * The `sig.watch-item/1` subset this surface consumes (P35.43, `sig/watch/2`).
 * Only the contract kinds (`renewal_deadline`/`contract_expiry`) carry a
 * `termination` block and so map back onto the legacy `ContractWatchItem`
 * contract — the other §5.2 kinds have no renewal watch representation and are
 * the v2 surface's own concern (the §39.5 render rows land in a later ticket).
 */
interface WatchItemV2 {
  handle?: string;
  kind?: string;
  title?: string;
  date?: string;
  subjects?: string[];
  body?: string | null;
  place?: { key?: string | null } | null;
  termination?: TerminationInput | null;
  contested?: boolean;
}

/** The `sig/watch/2` envelope — `items` is the versioned item list. */
interface WatchEnvelopeV2 {
  schema?: string;
  items?: unknown;
}

/**
 * Project one `sig.watch-item/1` onto the legacy `ContractWatchItem` wire —
 * the bridge that keeps the §39.5 page + subscriptions working on a v2
 * artifact until the surface rows render v2 natively (P35.43 back-compat).
 * Non-contract kinds return `null` (no termination semantics to carry).
 */
function watchItemToContractRow(item: WatchItemV2): ContractWatchItem | null {
  const termination = item.termination;
  if (termination == null) return null;
  const place = item.place ?? null;
  return {
    contract_id: item.subjects?.[0] ?? item.handle ?? "",
    subject_label: item.body ?? item.title ?? "",
    jurisdiction: place?.key ?? "unplaced",
    termination,
    renewal_window_days: termination.notice_window_days ?? null,
    approving_body: item.body ?? null,
    next_scheduled_meeting: null,
    replacement_procurement: null,
    contested: item.contested === true,
  };
}

/**
 * Surface 7 — the renewal/contract watch (§39.5). Export: `web/watch.json`.
 * P35.43 emits the versioned `sig/watch/2` envelope; a pre-P35.43 export emits
 * the bare `ContractWatchItem[]` — both shapes read to the same row list, and
 * a kind without a `termination` block simply has no renewal-watch row (the
 * v1 surface's honest-empty state stays truthful).
 */
export function getWatch(): ContractWatchItem[] {
  if (dataSource() !== "export") return WATCH_ITEMS;
  return readExportArtifact("watch.json", (p, path) => {
    if (Array.isArray(p)) {
      return dropWithdrawn(p as ContractWatchItem[]);
    }
    const env = p as WatchEnvelopeV2;
    const items = requireArray(env?.items, `${path}#items`) as WatchItemV2[];
    return dropWithdrawn(
      items
        .map(watchItemToContractRow)
        .filter((row): row is ContractWatchItem => row !== null),
    );
  });
}

/** Surface 8 — the evidence recommender + viewer (§39.5a/§39.6). Export: `web/evidence.json`. */
export interface EvidenceData {
  artifacts: EvidenceArtifact[];
  claimViews: ClaimView[];
}

export function getEvidence(): EvidenceData {
  if (dataSource() !== "export") {
    return { artifacts: EVIDENCE_ARTIFACTS, claimViews: CLAIM_VIEWS };
  }
  return readExportArtifact("evidence.json", (parsed, path) => {
    const o = parsed as { artifacts?: unknown; claim_views?: unknown };
    if (!Array.isArray(o?.artifacts)) {
      throw new Error(`${path}: expected an object with an "artifacts" array`);
    }
    return {
      artifacts: dropWithdrawn(o.artifacts as EvidenceArtifact[]),
      claimViews: dropWithdrawn(
        (Array.isArray(o.claim_views) ? o.claim_views : []) as ClaimView[],
      ),
    };
  });
}

/** Surface 9 — the public corrections log (§39.8). Export: `web/corrections.json`. */
export function getCorrections(): CorrectionEntry[] {
  if (dataSource() !== "export") return CORRECTIONS;
  return readExportArtifact("corrections.json", (p, path) =>
    dropWithdrawn(requireArray(p, path) as CorrectionEntry[]),
  );
}

/** Surface 10 — the research queue (§39.7). Export: `web/research_queue.json`. */
export function getResearchQueue(): ResearchTaskCard[] {
  if (dataSource() !== "export") return RESEARCH_QUEUE;
  return readExportArtifact(
    "research_queue.json",
    (p, path) => dropWithdrawn(requireArray(p, path) as ResearchTaskCard[]),
  );
}

/** Surface 1 — the dossier index / national landing list (§39.2). Export: `web/dossiers/index.json` (v2) or `web/dossier_index.json` (v1). */
export type DossierIndexRow = Pick<Dossier, "slug" | "subject_label" | "jurisdiction" | "asOf"> & {
  // P35.45 (`sig.dossier-index/2`): a keyed index row carries the canonical
  // identity + roll-up. All optional so a v1 row (or a fixture) still fits.
  jkey?: string;
  name?: string;
  display_name?: string;
  level?: string;
  parent_name?: string | null;
  records?: number;
  records_placed_only_here?: number;
  records_appearing?: number;
  conserved?: boolean;
};

/** The unplaced sibling block the v2 index carries (`unplaced` in `sig.dossier-index/2`). */
export interface UnplacedIndexEntry {
  slug_path: string;
  href: string;
  report: string;
  records: number;
  excluded_from?: string[];
}

/** The index's `unplaced` sibling — null on fixtures or a v1 export. */
export function getUnplacedIndexEntry(): UnplacedIndexEntry | null {
  if (dataSource() !== "export") {
    return {
      slug_path: "unplaced",
      href: unplacedPath(),
      report: "web/unplaced.json",
      records: 0,
    };
  }
  const v2path = `${exportDir()}/web/dossiers/index.json`;
  if (!existsSync(v2path)) return null;
  const parsed = JSON.parse(readFileSync(v2path, "utf-8")) as {
    unplaced?: UnplacedIndexEntry;
  };
  return parsed.unplaced ?? null;
}

export function getDossierIndex(): DossierIndexRow[] {
  const demoRows = () =>
    jurisdictionDemos().map((d) => ({
      slug: d.slug,
      subject_label: d.subject_label,
      jurisdiction: d.jurisdiction,
      asOf: d.asOf,
    }));
  if (dataSource() !== "export") {
    return [...DOSSIERS, ...JURISDICTION_DOSSIERS].map((d) => ({
      slug: d.slug,
      subject_label: d.subject_label,
      jurisdiction: d.jurisdiction,
      asOf: d.asOf,
    }));
  }
  // P35.45: the canonical `web/dossiers/index.json` (`sig.dossier-index/2`)
  // supersedes the flat `web/dossier_index.json` — a placement-bound export
  // emits only the v2 form; a pre-keyed export still emits v1.
  const v2path = `${exportDir()}/web/dossiers/index.json`;
  if (existsSync(v2path)) {
    const parsed = JSON.parse(readFileSync(v2path, "utf-8")) as {
      schema?: string;
      dossiers?: DossierIndexRow[];
    };
    if (!Array.isArray(parsed.dossiers)) {
      throw new Error(`${v2path}: expected a sig.dossier-index/2 object with .dossiers`);
    }
    return [...dropWithdrawn(parsed.dossiers), ...demoRows()];
  }
  return readExportArtifact("dossier_index.json", (p, path) => {
    const rows = dropWithdrawn(requireArray(p, path) as DossierIndexRow[]);
    // The export emits the real jurisdictions; the SIG-PUB-017 FR/BE demonstration
    // dossiers ship regardless of data source (as getDossiers appends them), so the
    // index echoes them too and the surface is identical in both modes.
    return [...rows, ...demoRows()];
  });
}

/**
 * P35.37 (SIG-TRANSP-013, J3 §5.4): where a dossier's record sits inside its
 * manifest-listed artifact — the `data-artifact` + `data-pointer` the dossier's
 * figures resolve into. `index` is the dossier's position in the RAW artifact
 * array (before the withdrawal/policy filters the read path applies): the
 * pointer names the released bytes, not the filtered view. `null` when the
 * artifact carries no record for the slug (the registry builder then emits no
 * dossier figures — the pages assert the registry is non-empty instead).
 */
export interface DossierArtifactRef {
  artifact: string;
  /** The array index the pointer prefixes; `null` when the artifact IS the
   * dossier record (a `web/dossiers/<slug-path>.json` per-dossier file —
   * P35.45), so the figure pointer is rooted at the document itself. */
  index: number | null;
}

export function getDossierArtifactRef(slug: string): DossierArtifactRef | null {
  if (dataSource() !== "export") {
    const i = DOSSIERS.findIndex((d) => d.slug === slug);
    return i >= 0 ? { artifact: "web/dossiers.json", index: i } : null;
  }
  // P35.45: a placement-bound export ships one file per dossier —
  // `web/dossiers/<slug-path>.json` — whose slug IS the nested slug path.
  const dossierDir = `${exportDir()}/web/dossiers`;
  const perDossier = `${dossierDir}/${slug}.json`;
  if (existsSync(perDossier)) {
    return { artifact: `web/dossiers/${slug}.json`, index: null };
  }
  if (!existsSync(dossierDir)) {
    const raw = readExportArtifact("dossiers.json", (p, path) =>
      requireArray(p, path),
    ) as { slug?: unknown }[];
    const i = raw.findIndex((d) => d.slug === slug);
    if (i >= 0) return { artifact: "web/dossiers.json", index: i };
  }
  // The SIG-PUB-017 demonstration dossiers live in the optional presentation
  // overlay (never a public build input — see getDossiers).
  const demos = readPresentation<{ slug?: unknown }[]>("jurisdiction_dossiers", []);
  const j = demos.findIndex((d) => d.slug === slug);
  return j >= 0 ? { artifact: "web/presentation/jurisdiction_dossiers.json", index: j } : null;
}

/**
 * `jurisdiction key → compartment` for every site row the export carries —
 * the dossier-class record-list target (`/r/<pub>/c/<comp>/jurisdiction/<j>/`)
 * resolves its compartment from this map. P35.45: a placement-bound export
 * writes `jurisdiction.jkey` + `jurisdiction.slug_path` on each site row; the
 * map is keyed by BOTH so a dossier page can look up its compartment by the
 * canonical key (`dossier.jurisdiction` on a `sig.dossier/2` row) or by the
 * slug path, while pre-keyed exports keep their declared-id key. Fixtures
 * mode yields the empty map (no release is ever bound to a fixture build →
 * the target is a named absence, never a dead link).
 */
export function getJurisdictionCompartments(): Map<string, string> {
  const out = new Map<string, string>();
  if (dataSource() !== "export") return out;
  const root = exportDir();
  for (const entry of readdirSync(root)) {
    const p = `${root}/${entry}/sites.jsonl`;
    if (!existsSync(p)) continue;
    for (const line of readFileSync(p, "utf-8").split("\n")) {
      const t = line.trim();
      if (!t) continue;
      const row = JSON.parse(t) as {
        jurisdiction?: unknown;
        jurisdiction_key?: unknown;
        jurisdiction_slug_path?: unknown;
      };
      const j = row.jurisdiction;
      const jkey =
        typeof row.jurisdiction_key === "string" && row.jurisdiction_key
          ? row.jurisdiction_key
          : j && typeof j === "object" && typeof (j as { jkey?: unknown }).jkey === "string"
            ? ((j as { jkey: string }).jkey)
            : null;
      const slugPath =
        typeof row.jurisdiction_slug_path === "string" && row.jurisdiction_slug_path
          ? row.jurisdiction_slug_path
          : j && typeof j === "object" && typeof (j as { slug_path?: unknown }).slug_path === "string"
            ? ((j as { slug_path: string }).slug_path)
            : null;
      const declared = typeof j === "string" && j ? j : null;
      for (const key of [jkey, slugPath, declared]) {
        if (key && !out.has(key)) out.set(key, entry);
      }
    }
  }
  return out;
}

// --------------------------------------------------------------------------- //
// P35.45 (K4 §5, `sig.unplaced-report/1`, `sig.jurisdiction-key-map/1`,
// `sig.jurisdiction-slug-history/1`): the canonical keyed jurisdiction
// artifacts. All absent on a pre-keyed export or fixtures build — each getter
// reads the honest absence, never fabricates the report.
// --------------------------------------------------------------------------- //

/**
 * One row of the canonical jurisdiction key map
 * (`sig.jurisdiction-key-map/1`): jkey → its display facts + slug path.
 */
export interface JurisdictionKeyMapRow {
  jkey: string;
  name?: string;
  display_name?: string;
  level?: string;
  slug_path?: string;
  parent_jkey?: string | null;
}

/** The unplaced data-quality report (`sig.unplaced-report/1`). */
export interface UnplacedReport {
  schema: string;
  kind?: string;
  name?: string;
  /** K4 §5.5's verbatim header sentence — rendered as the page lede. */
  header?: string;
  note?: string;
  as_of?: string;
  records?: number;
  /** reason → record count (reasons are per (record, source) slices). */
  by_reason?: Record<string, number>;
  /** The §5.5 table rows — reason, records, share, sources, fix. */
  reason_rows?: {
    reason: string;
    records: number;
    /** Percentage of the report total (0–100, 1 decimal). */
    share_percent?: number | null;
    sources?: string[];
    definition?: string;
    fix?: string;
  }[];
  by_source?: {
    source_id: string;
    records: number;
    top_reasons?: { reason: string; records: number }[];
  }[];
  /** reason → its honest definition. */
  reason_definitions?: Record<string, string>;
  check_vocabulary?: string[];
  methodology?: string;
  correction?: { corrections?: string; research_queue?: string; note?: string };
  /** The per-compartment download slot — named absence until DSRC-03 fills it. */
  downloads?: { status?: string; note?: string; items?: unknown[] };
  excluded_from?: string[];
  [key: string]: unknown;
}

/** The jurisdiction key map (jkey → row), or null when absent. */
export function getJurisdictionKeyMap(): Map<string, JurisdictionKeyMapRow> | null {
  if (dataSource() === "fixtures") return null;
  const path = `${layoutDir()}/web/jurisdiction_key_map.json`;
  if (!existsSync(path)) return null;
  const parsed = JSON.parse(readFileSync(path, "utf-8")) as {
    jurisdictions?: JurisdictionKeyMapRow[];
    entries?: JurisdictionKeyMapRow[];
    rows?: JurisdictionKeyMapRow[];
  };
  const rows = parsed.jurisdictions ?? parsed.entries ?? parsed.rows ?? [];
  const out = new Map<string, JurisdictionKeyMapRow>();
  for (const r of rows) if (r && typeof r.jkey === "string") out.set(r.jkey, r);
  return out;
}

/** jkey → slug path, or null when the export is not placement-bound. */
export function getJurisdictionSlugPaths(): Map<string, string> | null {
  const m = getJurisdictionKeyMap();
  if (m === null) return null;
  const out = new Map<string, string>();
  for (const [jkey, row] of m) {
    if (typeof row.slug_path === "string" && row.slug_path) out.set(jkey, row.slug_path);
  }
  return out;
}

/** The unplaced report document, or null when the export carries none
 * (a pre-keyed export — fixtures mode returns the honest empty report). */
export function getUnplacedReport(): UnplacedReport | null {
  if (dataSource() !== "export") {
    return {
      schema: "sig.unplaced-report/1",
      kind: "data_quality_report",
      name: "Not yet placed",
      // K4 §5.5's verbatim header — the same string the export emits.
      header:
        "These records are published, but SIG cannot yet say which jurisdiction " +
        "they belong to. This is a data-quality list, not a place.",
      note:
        "This is a data-quality report, not a jurisdiction and not a place. " +
        "It names WHY each record could not be placed — a record is never " +
        "guessed into a jurisdiction. (Demo data — every fixture record is placed.)",
      records: 0,
      by_reason: {},
      reason_rows: [],
      by_source: [],
      reason_definitions: {},
      correction: {
        corrections: "/corrections/",
        research_queue: "/research-queue/",
        note:
          "A record here is placed nowhere — correcting its declared " +
          "jurisdiction or contributing a verifiable location moves it off " +
          "this report in the next release.",
      },
      downloads: {
        status: "not_emitted",
        note:
          "Per-compartment downloads of this report are not emitted yet — " +
          "they land with the per-dossier downloads work.",
        items: [],
      },
      excluded_from: [
        "jurisdiction counts",
        "the place facet",
        "canonical jurisdiction rows",
      ],
    };
  }
  const path = `${exportDir()}/web/unplaced.json`;
  if (!existsSync(path)) return null;
  return JSON.parse(readFileSync(path, "utf-8")) as UnplacedReport;
}

/**
 * One append-only slug-history row (`sig.jurisdiction-slug-history/1`): an old
 * flat slug → its resolution under the canonical tree (moved / split /
 * corrected). Drives the back-compat stubs at the old `/dossier/<slug>/` URLs.
 * `successor` is a jkey, a jkey list (split), or `"unplaced"`.
 */
export interface SlugHistoryRow {
  slug: string;
  kind: "moved" | "split" | "corrected" | string;
  successor?: string | string[];
  note?: string;
  first_release?: string | null;
  last_release?: string | null;
  [key: string]: unknown;
}

export function getSlugHistory(): SlugHistoryRow[] {
  if (dataSource() !== "export") return [];
  const path = `${exportDir()}/web/jurisdiction_slug_history.json`;
  if (!existsSync(path)) return [];
  const parsed = JSON.parse(readFileSync(path, "utf-8")) as {
    rows?: SlugHistoryRow[];
  };
  return parsed.rows ?? [];
}

/**
 * P32.13 (SIG-FIND-001/002, ADR-132): the activated-release catalog behind
 * `/releases/`. Fixtures mode returns the demo catalog; export mode reads
 * `<exportDir>/web/releases.json` when present — an absent file is the honest
 * empty catalog (no release was ever built from this export), never a
 * fabricated entry.
 */
export function getReleaseCatalog(): ReleaseCatalog {
  if (dataSource() !== "export") return RELEASE_CATALOG_FIXTURE;
  const path = `${exportDir()}/web/releases.json`;
  if (!existsSync(path)) {
    return { schema: "sig.publication-catalog/1", publications: [] };
  }
  const parsed = JSON.parse(readFileSync(path, "utf-8")) as ReleaseCatalog;
  if (!Array.isArray(parsed?.publications)) {
    throw new Error(`${path}: expected a sig.publication-catalog/1 object`);
  }
  return parsed;
}

// --------------------------------------------------------------------------- //
// P32.14 (SIG-FIND-003, ADR-133): released-corpus search + complete browse.
// The no-JS surface pins REAL activated release namespaces: one GET form per
// licence compartment targets the release search route (JSON or the no-JS HTML
// representation the API serves — the static host cannot run it, so `format=html`
// is carried explicitly), and the compartment overview gives complete static
// browse pagination that needs no service at all.
// --------------------------------------------------------------------------- //

export interface ReleaseSearchCompartment {
  compartment: string;
  license: string;
  recordCount: number;
  /** GET form target — the released-corpus search route (JSON or no-JS HTML). */
  searchHref: string;
  /** The compartment overview under the release namespace — complete static browse. */
  overviewHref: string;
}

export interface ReleaseSearchTarget {
  publicationId: string;
  recordCount: number;
  landingHref: string;
  compartments: ReleaseSearchCompartment[];
}

/**
 * One released-corpus search target per activated publication, one per
 * compartment. `SIG_RELEASE_SEARCH_BASE` overrides the route origin at build
 * time (default: same-origin `/v1/...` — deployment wiring maps it to the read
 * API that serves the verified indexes; the static build never invents one).
 */
export function getReleaseSearchTargets(): ReleaseSearchTarget[] {
  const base = (process.env.SIG_RELEASE_SEARCH_BASE ?? "").replace(/\/+$/, "");
  return getReleaseCatalog().publications.map((e) => ({
    publicationId: e.publication_id,
    recordCount: e.record_count,
    landingHref: `/releases/${e.publication_id}/`,
    compartments: e.compartments.map((c) => ({
      compartment: c.compartment,
      license: c.license,
      recordCount: c.record_count,
      searchHref: `${base}/v1/releases/${e.publication_id}/compartments/${c.compartment}/search`,
      overviewHref: `/r/${e.publication_id}/c/${c.compartment}/`,
    })),
  }));
}

/**
 * The publication the investigation workspace defaults `release=` to (P32.15,
 * SIG-FIND-004): the last activated entry in the catalog, or null when no
 * release is activated (an honest "none", never a fabricated namespace).
 */
export function getLatestReleaseTarget(): ReleaseSearchTarget | null {
  const targets = getReleaseSearchTargets();
  return targets.length ? targets[targets.length - 1]! : null;
}

/**
 * entity_id → the SPECIFIC released-record route `/r/<pub>/c/<comp>/entity/
 * <type>/<id>/` (ADR-132) — shared by every surface that links a listed item to
 * its citable record (SIG-FIND-004). `null` when no activated release maps the
 * id — callers keep a generic fallback, never invent a route.
 */
export function releasedRecordHref(
  target: ReleaseSearchTarget | null,
  entityComps: Map<string, { compartment: string; entityType: string }>,
  entityId: string,
): string | null {
  if (!target) return null;
  const m = entityComps.get(entityId);
  return m
    ? `/r/${target.publicationId}/c/${m.compartment}/entity/${m.entityType}/${entityId}/`
    : null;
}

/**
 * `entity_id → {compartment, entity_type}` for every released record — used to
 * give the interactive island SPECIFIC record hrefs (never `/map/`). Export
 * mode scans each compartment's `sites.jsonl` (the same bound projection the
 * release indexes); fixtures mode returns the empty map (the demo catalog is a
 * stand-in, not a real namespace, so demo items keep generic hrefs).
 */
export function getEntityCompartments(): Map<
  string,
  { compartment: string; entityType: string }
> {
  const out = new Map<string, { compartment: string; entityType: string }>();
  if (dataSource() !== "export") return out;
  const root = exportDir();
  for (const entry of readdirSync(root)) {
    const p = `${root}/${entry}/sites.jsonl`;
    if (!existsSync(p)) continue;
    for (const line of readFileSync(p, "utf-8").split("\n")) {
      const t = line.trim();
      if (!t) continue;
      const row = JSON.parse(t) as { entity_id?: unknown; entity_type?: unknown };
      // P34.19 (F-337): a withdrawn subject has no released record — no route.
      if (typeof row.entity_id === "string" && !isWithdrawn(row.entity_id)) {
        out.set(row.entity_id, {
          compartment: entry,
          entityType: typeof row.entity_type === "string" ? row.entity_type : "deployment",
        });
      }
    }
  }
  return out;
}

/**
 * The `claim_id → sig.statement/1` statement index the shared
 * `<ProvenancePanel>` contract reads (P35.36, R11-K13-TX-08a / J3 §5.1,
 * SIG-TRANSP-011).
 *
 *   - `fixtures` mode — the committed fixture rows (`statements-fixture.ts`),
 *     keyed to the claim ids the fixtures name.
 *   - `export` mode — every compartment's `<exportDir>/<comp>/statements.jsonl`
 *     (the same per-compartment files the release tree ships under
 *     `r/<pub>/c/<comp>/statements.jsonl`), scanned by directory like
 *     `getEntityCompartments`.
 *
 * A pre-P35.36 export legitimately carries no statements files — the index is
 * then EMPTY (the named-absence `not_recorded` panel renders for every claim),
 * never a build error and never a fabricated statement.
 */
export function getStatementIndex(): Map<string, StatementRow> {
  const out = new Map<string, StatementRow>();
  const rows =
    dataSource() !== "export"
      ? STATEMENT_FIXTURES
      : (() => {
          const collected: StatementRow[] = [];
          const root = exportDir();
          if (!existsSync(root)) return collected;
          for (const entry of readdirSync(root)) {
            const p = `${root}/${entry}/statements.jsonl`;
            if (!existsSync(p)) continue;
            for (const line of readFileSync(p, "utf-8").split("\n")) {
              const t = line.trim();
              if (!t) continue;
              collected.push(JSON.parse(t) as StatementRow);
            }
          }
          return collected;
        })();
  for (const row of rows) {
    if (typeof row.claim_id === "string" && !isWithdrawn(row.claim_id)) {
      out.set(row.claim_id, row);
    }
  }
  return out;
}

/**
 * The express-terms disclosure (P34.19, F-403, ADR-183) — `sig.terms-disclosure/1`.
 *
 *   - `fixtures` mode — the demo fixture (one synthetic source, clearly marked).
 *   - `export` mode — `<exportDir>/web/terms_disclosure.json`, emitted by
 *     `sig-exports` when the export carries an affected source's rows.
 *
 * A MISSING artifact is honest absence — an export scoped to sources without
 * express-terms rows emits none — and reads as an empty source list (the
 * interim sources-and-licences page then states "no express-terms sources in
 * this export"), never a fabricated entry.
 */
export function getTermsDisclosure(): TermsDisclosure {
  if (dataSource() !== "export") return TERMS_DISCLOSURE_FIXTURE;
  const path = `${exportDir()}/web/terms_disclosure.json`;
  if (existsSync(path)) {
    const parsed: unknown = JSON.parse(readFileSync(path, "utf-8"));
    if (!isTermsDisclosure(parsed)) {
      throw new Error(`${path}: not a valid sig.terms-disclosure/1 artifact`);
    }
    return parsed;
  }
  // P34.17: the 09-27 release predates the export-side artifact. When the
  // export lacks it BUT actually carries express-terms rows (the
  // `operator_accepted` compartment is present and non-empty), fall back to the
  // committed policy table (`policy/data/express_terms.json`, ADR-183's
  // sig.express-terms-disclosure/1 record) — same terms verbatim, same basis —
  // so the disclosure is never absent where it applies. An export genuinely
  // without express-terms rows still returns the honest empty list.
  const accepted = `${exportDir()}/operator_accepted/sites.jsonl`;
  if (!existsSync(accepted) || readFileSync(accepted, "utf-8").trim() === "") {
    return { ...TERMS_DISCLOSURE_FIXTURE, sources: [] };
  }
  const policyPath = `${repoRoot()}policy/src/policy/data/express_terms.json`;
  const policy = JSON.parse(readFileSync(policyPath, "utf-8")) as {
    basis?: unknown;
    sources?: unknown;
  };
  if (!policy.basis || !Array.isArray(policy.sources)) {
    throw new Error(`${policyPath}: not a valid sig.express-terms-disclosure/1 record`);
  }
  return {
    schema: "sig.terms-disclosure/1",
    basis: policy.basis as TermsDisclosure["basis"],
    sources: policy.sources as TermsDisclosure["sources"],
  };
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
  /**
   * The release id the site was built from (the export manifest's `release_id`)
   * — P34.17's interim release stamp prints it on every page. `null` in
   * fixtures mode (a development build has no release).
   */
  releaseId: string | null;
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
 * The per-licence-compartment tile archives the export ships (P30.3, ADR-106;
 * P31.15, ADR-R9-TILES): every manifest artifact under `web/tiles/` ending
 * `-sites.pmtiles`, with its ONE licence. The committed fixtures yield `[]`, which
 * leaves the background-only style and the island's inline fallback points; an
 * export build yields one z0–z14 archive per compartment.
 */
/**
 * The per-source attribution one compartment's ATTRIBUTION.json carries
 * (P34.21a / E2-12): each drawn source's own credit, deduplicated and joined.
 * `undefined` when the export predates the attribution index or no source
 * carries an attribution — the licence-level fallback line stands.
 */
function compartmentAttributionFromIndex(compartment: string): string | undefined {
  const path = `${layoutDir()}/${compartment}/ATTRIBUTION.json`;
  let doc: { sources?: Array<{ attribution?: string }> };
  try {
    doc = JSON.parse(readFileSync(path, "utf-8"));
  } catch {
    return undefined; // an export without the attribution index degrades honestly
  }
  const lines = [
    ...new Set(
      (doc.sources ?? [])
        .map((s) => (typeof s.attribution === "string" ? s.attribution.trim() : ""))
        .filter((a) => a.length > 0),
    ),
  ];
  return lines.length > 0 ? lines.join(" · ") : undefined;
}

export function getCompartmentTileSources(): CompartmentTileSource[] {
  if (dataSource() === "fixtures") return [];
  const path = `${layoutDir()}/manifest.json`;
  let parsed: { artifacts?: Array<{ path?: string; compartment?: string; license?: string }> };
  try {
    parsed = JSON.parse(readFileSync(path, "utf-8"));
  } catch (cause) {
    throw new Error(
      `SIG_DATA_SOURCE=${dataSource()} but the ${dataSource()} manifest is unreadable: ${path}`,
      { cause },
    );
  }
  return (parsed.artifacts ?? [])
    .filter((a) => typeof a.path === "string" && /^web\/tiles\/[^/]+-sites\.pmtiles$/.test(a.path))
    .map((a) => ({
      compartment: String(a.compartment),
      license: String(a.license),
      path: `/tiles/${a.path!.slice("web/tiles/".length)}`,
      // P34.21a / E2-12: the drawn sources' own credit, never the generic line.
      attribution: compartmentAttributionFromIndex(String(a.compartment)),
    }))
    .sort((x, y) => x.compartment.localeCompare(y.compartment));
}

export function getSiteMetadata(): SiteMetadata {
  if (dataSource() === "fixtures") {
    return { asOf: AS_OF, rulesetVersion: RULESET_VERSION, releaseId: null };
  }
  const path = `${layoutDir()}/manifest.json`;
  let raw: string;
  try {
    raw = readFileSync(path, "utf-8");
  } catch (cause) {
    throw new Error(
      dataSource() === "national"
        ? `SIG_DATA_SOURCE=national but the national fixture manifest is missing: ${path}. ` +
            "Regenerate the fixture (`npm run fixture:national`) first."
        : `SIG_DATA_SOURCE=export but the export manifest is missing: ${path}. ` +
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
    releaseId:
      typeof (parsed as { release_id?: unknown }).release_id === "string"
        ? ((parsed as { release_id: string }).release_id)
        : null,
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

/** Read `<layoutDir>/web/analytics/<name>.json` — the export dir under
 * `export`, the national fixture dir under `national` (P35.51: the overlay
 * emits the analytics its declared surfaces need — `density_bins`,
 * `centrality` — and a missing one fails LOUD exactly like an export read).
 * `pick` extracts the payload after the envelope is validated. */
function readAnalytics<T>(name: string, pick: (envelope: AnalyticsEnvelope & Record<string, unknown>, path: string) => T): T {
  const path = `${layoutDir()}/web/analytics/${name}.json`;
  let raw: string;
  try {
    raw = readFileSync(path, "utf-8");
  } catch (cause) {
    throw new Error(
      `SIG_DATA_SOURCE=${dataSource()} but the analytics artifact is missing: ${path}. ` +
        (dataSource() === "national"
          ? "Regenerate the fixture (`npm run fixture:national`, " +
            "scripts/ci/build_national_fixture.py) first."
          : "Run `sig-exports build --from-spine --dsn <dsn> --out <dir>` (or, for a local " +
            "fixture-equivalent bundle, `npm run export:fixtures -- <dir>`) first."),
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
  if (dataSource() !== "export") return undefined;
  return readAnalytics("provenance", (env, path) => {
    const summary = (env.surfaces as Record<string, unknown> | undefined)?.site;
    if (summary == null) throw new Error(`${path}: provenance carries no surfaces.site summary`);
    // P34.11 (QW-6): carry the artifact's own named denominator through, so the
    // module can say exactly what its site-wide totals are counted against.
    return { ...(summary as ProvenanceSummary), denominator: env.denominator };
  });
}

/** National-zoom density bins for the map (§19.5 H3 bins, SIG-UI-019; export-emitted, P31.14).
 *  P35.51: the national overlay emits the same artifact computed over its
 *  synthetic sites — the fixture corpus's demo bins never masquerade as the
 *  national map's coverage shape. */
export function getMapDensityBins(): DensityBin[] {
  if (dataSource() !== "fixtures") {
    return readAnalytics("density_bins", (env, path) => {
      if (!Array.isArray(env.bins)) throw new Error(`${path}: expected a "bins" array`);
      // P35.20b (ED-44, SIG-RECON-058): `recordCount` is the canonical field; a
      // pre-P35.20b artifact's `deviceCount` is folded in at this single seam —
      // the pages never read the deprecated name. The wire's snake_case
      // `jurisdiction_counts` normalises to `jurisdictionCounts` here too.
      return (env.bins as (DensityBin & { jurisdiction_counts?: Record<string, number> })[]).map(
        (b) => ({
          ...b,
          recordCount: b.recordCount ?? b.deviceCount ?? 0,
          jurisdictionCounts: b.jurisdictionCounts ?? b.jurisdiction_counts,
        }),
      );
    });
  }
  return DENSITY_BINS;
}

/**
 * The entity the network explorer centers its ego view on by default (SIG-UI-022).
 * P34.15 (SIG-IDENT-030 by abstention): the centrality `statistics` list is
 * deliberately NOT read — the ranking is withdrawn until organisation entity
 * resolution passes its gate; the artifact's `focus` block remains the pick's
 * stated mechanism (highest undirected degree, ties lexical).
 */
export function getNetworkFocusEntityId(): string {
  // P35.51: the national overlay emits the same `centrality` artifact —
  // its `focus.entity_id` names the synthetic agency the ego view centres on
  // (never the committed demo corpus's focus id inside a national graph).
  if (dataSource() !== "fixtures") {
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

/**
 * The two captures the evidence viewer diffs field-by-field (SIG-UI-029) —
 * fixtures mode only. In export mode the export carries no capture-diff
 * payload (the interim artifact list replaces the document views, P34.20 /
 * SIG-EVUI-D05): an export-mode build must never render the committed fixture
 * diff, so this returns `null` and the page skips the section honestly.
 */
export function getCaptureDiff(): [Capture, Capture] | null {
  if (dataSource() === "export") return null;
  return DIFF_CAPTURES;
}

/**
 * The per-dossier "How we know this" summary (ED-41 / SIG-UI-044). Export mode
 * reads `surfaces.dossiers[<slug>]` — the provenance row the spine export emits
 * scoped to the claims backing THAT dossier's sites. When no row was emitted
 * for the key (a pre-P35.20a export, or a non-jurisdiction surface), `undefined`
 * returns so the layout renders the site-wide summary labelled site-wide —
 * the honest fallback, never site totals under the dossier's name. Fixtures
 * mode → `undefined` (the committed demo dossiers have no emitted rows).
 */
export function getDossierProvenance(slug: string): ProvenanceSummary | undefined {
  if (dataSource() !== "export") return undefined;
  return readAnalytics("provenance", (env) => {
    const dossiers = (env.surfaces as Record<string, unknown> | undefined)?.dossiers as
      | Record<string, unknown>
      | undefined;
    if (dossiers == null) return undefined; // a pre-change export has no per-dossier rows
    const summary = dossiers[slug];
    if (summary == null) return undefined;  // no emitted row for this surface → site-wide
    return summary as ProvenanceSummary;
  });
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

/**
 * The recorded hostile-reader review for the editorial-standards page (§41,
 * SIG-UI-042). P34.17 / ADR-179 (WV-04): the committed fixture review was a
 * fabricated two-reviewer record and is removed; the truth is that the review
 * was NEVER PERFORMED, so the seam returns `null` and the page renders the
 * "not yet performed" notice rather than a review card. Export mode reads
 * `web/hostile_reader_review.json` when a future reviewed export emits one —
 * an absent artifact is honest absence, never a fabricated record. A review
 * that DOES exist still has to clear `assertReviewReleasable` at the page.
 */
export function getHostileReaderReview(): HostileReaderReview | null {
  if (dataSource() !== "export") return null;
  const path = `${exportDir()}/web/hostile_reader_review.json`;
  if (!existsSync(path)) return null;
  const parsed = JSON.parse(readFileSync(path, "utf-8")) as HostileReaderReview;
  if (!Array.isArray(parsed?.findings) || !Array.isArray(parsed?.reviewers)) {
    throw new Error(`${path}: not a valid hostile-reader review record`);
  }
  return parsed;
}

/** The generated rationale templates the style guide gates against the register rules (SIG-UI-046). */
export function getRationaleTemplates(): readonly string[] {
  return GENERATED_RATIONALE_TEMPLATES;
}

/**
 * P34.17 (R1.8-as-reassigned): the per-source licence table behind `/sources/`,
 * aggregated from the export's own compartment `sites.jsonl` `_rights` blocks —
 * the licence and credit shown are exactly what the published download bytes
 * carry. Fixtures mode returns the small demonstration set.
 */
export function getSourceLicenceTable(): SourceLicenceRow[] {
  if (dataSource() !== "export") return SOURCES_FIXTURE;
  // P35.37 (SIG-TRANSP-013): `web/sources.json` is the manifest-listed artifact
  // the /sources/ page's figures point at — when the export emits it (P35.37+),
  // the page renders THE artifact rows (never a re-derivation that could drift);
  // a pre-P35.37 export falls back to the sites.jsonl aggregation it was built
  // from (the same computation, honest absence of the artifact).
  const emitted = `${exportDir()}/web/sources.json`;
  if (existsSync(emitted)) {
    const parsed: unknown = JSON.parse(readFileSync(emitted, "utf-8"));
    if (!isSourceLicenceArtifact(parsed)) {
      throw new Error(`${emitted}: not a valid sig.source-licence-table/1 artifact`);
    }
    return parsed.rows;
  }
  return sourceLicenceTable(exportDir());
}

// --------------------------------------------------------------------------- //
// P35.40 (SIG-TRANSP-002/026/027, K9 §3.1–3.3): the source universe and the
// lifecycle partition — `transparency/sources.json` (sig.source-row/1: one
// source is one registry row) and `transparency/counts.json`
// (sig.source-counts/1: every count a named predicate over those rows). The
// stale numbers die here — "178 sources tracked" →
// `attributes.site_records.count` ("sources with published site records"),
// "Independent sources" → `lifecycle.published.count` ("sources with
// published claims"), the universe `universe.count`. Anomaly identifiers
// carry `anomalies.ids` — listed, never counted.
//
//   - `fixtures` mode — the committed fixture pair (`source-counts.ts`,
//     derived through the same recompute the artifact carries).
//   - `export` mode — `<exportDir>/transparency/…`, emitted since P35.35 —
//     a missing/malformed artifact fails LOUD (a stale export is rebuilt,
//     never silently patched).
// --------------------------------------------------------------------------- //

function readTransparencyArtifact<T>(
  name: string,
  validate: (parsed: unknown, path: string) => T,
): T {
  const path = `${exportDir()}/transparency/${name}`;
  let raw: string;
  try {
    raw = readFileSync(path, "utf-8");
  } catch (cause) {
    throw new Error(
      `SIG_DATA_SOURCE=export but the transparency artifact is missing: ${path}. ` +
        "Rebuild the export (`sig-exports build` emits transparency/ artifacts since P35.35).",
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

/** The source universe + named-predicate counts (`transparency/counts.json`). */
export function getSourceCounts(): SourceCountsDoc {
  if (dataSource() !== "export") return SOURCE_COUNTS_FIXTURE;
  return readTransparencyArtifact("counts.json", (parsed, path) => {
    if (!isSourceCountsDoc(parsed)) {
      throw new Error(`${path}: not a valid sig.source-counts/1 artifact`);
    }
    return parsed;
  });
}

/** The emitted source rows (`transparency/sources.json`, one per registry row). */
export function getSourceRows(): SourceRowsDoc {
  if (dataSource() !== "export") return SOURCE_ROWS_DOC_FIXTURE;
  return readTransparencyArtifact("sources.json", (parsed, path) => {
    if (!isSourceRowsDoc(parsed)) {
      throw new Error(`${path}: not a valid sig.source-row/1 artifact`);
    }
    return parsed;
  });
}

/**
 * P35.39 (SIG-TRANSP-016, J3 §6.5): the generated `sig.data-dictionary/1`
 * document behind `/data/dictionary/` — `<exportDir>/dictionary.json` in
 * export mode, the committed demonstration document in fixtures mode.
 * Export mode fails LOUD on a missing/malformed artifact (the dictionary is
 * a first-class emitted file since this row — a pre-P35.39 export is stale,
 * never silently patched).
 */
export function getDataDictionary(): DataDictionary {
  if (dataSource() !== "export") return DICTIONARY_FIXTURE;
  const path = `${exportDir()}/dictionary.json`;
  let raw: string;
  try {
    raw = readFileSync(path, "utf-8");
  } catch (cause) {
    throw new Error(
      `SIG_DATA_SOURCE=export but the data dictionary is missing: ${path}. ` +
        "Rebuild the export (`sig-exports build` emits `dictionary.json` since P35.39).",
      { cause },
    );
  }
  const parsed: unknown = JSON.parse(raw);
  if (!isDataDictionary(parsed)) {
    throw new Error(`${path}: not a valid sig.data-dictionary/1 document`);
  }
  return parsed;
}

/** The `sig.source-licence-table/1` artifact shape (`web/sources.json`). */
export interface SourceLicenceArtifact {
  schema: "sig.source-licence-table/1";
  rows: SourceLicenceRow[];
}

function isSourceLicenceArtifact(v: unknown): v is SourceLicenceArtifact {
  const o = v as { schema?: unknown; rows?: unknown };
  return o?.schema === "sig.source-licence-table/1" && Array.isArray(o.rows);
}

// --------------------------------------------------------------------------- //
// The dated attribution-correction record (P34.21b / E2-12, ADR-194): when the
// export's effective rights resolve through append-only attribution-correction
// decisions, `<exportDir>/web/attribution_corrections.json` names each corrected
// source with the decision's `decided_at`. `/sources/` renders the dated note —
// "earlier downloads credited some rows to the wrong source" — only when this
// artifact exists; a pre-backfill export emits none and the page shows nothing
// (honest absence, never a fabricated correction).
// --------------------------------------------------------------------------- //

export interface AttributionCorrection {
  /** The corrected source's public (re-keyed) identifier. */
  source_id: string;
  /** The correction decision's recorded decided_at (ISO-8601). */
  decided_at: string;
}

export interface AttributionCorrections {
  schema: "sig.attribution-corrections/1";
  corrections: AttributionCorrection[];
  /**
   * The latest correction `decided_at` (ISO date rendered by the note) —
   * `null` for an empty list.
   */
  corrected_on: string | null;
}

/** `null` = the export carries no corrections (or fixtures mode) — no note. */
export function getAttributionCorrections(): AttributionCorrections | null {
  if (dataSource() !== "export") return null;
  const path = `${exportDir()}/web/attribution_corrections.json`;
  if (!existsSync(path)) return null;
  const parsed: unknown = JSON.parse(readFileSync(path, "utf-8"));
  const doc = parsed as {
    schema?: unknown;
    corrections?: Array<{ source_id?: unknown; decided_at?: unknown }>;
  };
  if (doc?.schema !== "sig.attribution-corrections/1" || !Array.isArray(doc.corrections)) {
    throw new Error(`${path}: not a valid sig.attribution-corrections/1 artifact`);
  }
  const corrections: AttributionCorrection[] = doc.corrections.map((c) => ({
    source_id: String(c.source_id),
    decided_at: String(c.decided_at),
  }));
  const corrected_on =
    corrections
      .map((c) => c.decided_at.slice(0, 10))
      .sort()
      .at(-1) ?? null;
  return { schema: "sig.attribution-corrections/1", corrections, corrected_on };
}

// --- Reference / component-demo pages (SIG-UI-037). These render the API-wire-contract
// exemplars (not spine surfaces); routed through the data layer so the pages import no
// fixture module directly. Identical in both modes.

// --------------------------------------------------------------------------- //
// P35.37 (SIG-TRANSP-013, DR-C3-03): the resolution evaluation — the numbers
// that measure SIG's own method (§32.5, SIG-METRIC-008b) — is a published
// release artifact, never a hard-coded TypeScript constant.
//
//   - `fixtures` mode — the committed `sig.resolution-eval/1` record
//     (`exports/src/exports/data/resolution_eval.json`), read through the same
//     validator (one canonical record — the exporter emits it verbatim).
//   - `export` mode — `<exportDir>/web/evaluation.json`, the artifact the
//     exporter writes into the manifest; a missing file fails LOUD (never a
//     fall-back to the fixture — that would fabricate the eval).
// --------------------------------------------------------------------------- //

/** The canonical committed eval record the exporter emits verbatim. */
export const RESOLUTION_EVAL_RECORD_PATH = "exports/src/exports/data/resolution_eval.json";

export function getResolutionEval(): ResolutionEval {
  if (dataSource() !== "export") {
    const parsed: unknown = JSON.parse(
      readFileSync(`${repoRoot()}${RESOLUTION_EVAL_RECORD_PATH}`, "utf-8"),
    );
    if (!isResolutionEval(parsed)) {
      throw new Error(`${RESOLUTION_EVAL_RECORD_PATH}: not a valid sig.resolution-eval/1 record`);
    }
    return parsed;
  }
  return readExportArtifact("evaluation.json", (parsed, path) => {
    if (!isResolutionEval(parsed)) {
      throw new Error(`${path}: not a valid sig.resolution-eval/1 artifact`);
    }
    return parsed;
  });
}

/**
 * P35.37: the bytes the `/artifact/<export-path>` route serves — the
 * "downloadable file" / release-artifact link target every figure carries. In
 * export mode the file is read from the export directory verbatim; in fixtures
 * mode the same payload is serialised from the data layer (it IS the build's
 * data artifact — the fixture export harness writes identical bytes).
 * `null` → the path is not a figure-addressable artifact (the route 404s).
 */
export function getReleaseArtifactPayload(artifactPath: string): unknown | null {
  switch (artifactPath) {
    case "web/dossier_index.json":
      return getDossierIndex();
    case "web/dossiers.json":
      return getDossiers();
    case "web/coverage.json":
      return getCoverage();
    case "web/freshness.json":
      return getFreshness();
    case "web/sources.json":
      return { schema: "sig.source-licence-table/1", rows: getSourceLicenceTable() };
    // P35.40: the source-universe pair the counting surfaces point at.
    case "transparency/counts.json":
      return getSourceCounts();
    case "transparency/sources.json":
      return getSourceRows();
    case "web/evaluation.json":
      return getResolutionEval();
    case "web/terms_disclosure.json":
      return getTermsDisclosure();
    case "web/analytics/density_bins.json":
      return {
        schema: "sig/analytics-density-bins/1",
        as_of: AS_OF.as_of_world,
        denominator: "the published site records with a releasable tier-0 point",
        is_population_total: false,
        source_compartments: ["sig_graph"],
        grid: "h3",
        h3_resolution: 3,
        coverage_rule:
          "cell coverage = the number of distinct named sources contributing to the cell",
        bins: getMapDensityBins(),
      };
    case "web/analytics/provenance.json": {
      // The ADR-R9-ANALYTICS envelope the exporter writes — surfaces.site +
      // surfaces.dossiers — so figure pointers (/surfaces/site/artifact_count)
      // resolve into the served bytes the same way they do in the release.
      const site = dataSource() !== "export" ? DEFAULT_PROVENANCE : getSiteProvenance();
      const dossiers = Object.fromEntries(
        [...DOSSIERS, ...JURISDICTION_DOSSIERS].map((d) => [
          d.slug,
          getDossierProvenance(d.slug) ?? DEFAULT_PROVENANCE,
        ]),
      );
      return {
        schema: "sig/analytics-provenance/1",
        as_of: AS_OF.as_of_world,
        denominator: site?.denominator ?? "the published evidence artifacts",
        is_population_total: false,
        source_compartments: ["sig_graph"],
        surfaces: {
          site: site ?? null,
          dossiers,
          corrections: getCorrectionsProvenance() ?? null,
          research_queue: getResearchQueueProvenance() ?? null,
        },
      };
    }
    case "web/leverage.json":
      return getLeverageMetric();
    case "web/presentation/jurisdiction_dossiers.json":
      return dataSource() !== "export"
        ? JURISDICTION_DOSSIERS
        : readPresentation<Dossier[]>("jurisdiction_dossiers", []);
    default:
      return null;
  }
}

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
