// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * P27.5 fixture-export harness (verification only).
 *
 * Serialises the committed web fixtures into the P27.1 export layout —
 * `<outDir>/web/<artifact>.json` plus `dossiers.json` / `leverage.json` and a
 * per-compartment `web/tiles/sig_graph-sites.pmtiles` — so `SIG_DATA_SOURCE=export
 * SIG_EXPORT_DIR=<outDir>` can be exercised against REAL on-disk bytes with
 * fixture-equivalent content. This is the P21.4 precedent (`sig-exports build
 * --jurisdiction okc` emits a fixture-equivalent bundle) extended to the ten P27.1
 * surfaces, and lets `npm run check` pass identically in both modes without a hosted
 * spine (D-P27.4-1 stays deferred). It is a TEST harness, not a shipped artifact:
 * production export bytes come from `sig-exports build --from-spine` (P27.4).
 *
 * Run:  node <esbuild-bundled>.mjs <outDir>          (see `npm run export:fixtures`)
 */

import { existsSync, mkdirSync, readFileSync, unlinkSync, writeFileSync } from "node:fs";
import { gzipSync } from "node:zlib";
import { execFileSync, spawnSync } from "node:child_process";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import { MAP_LAYERS, partitionByLocatability } from "../src/lib/map";
import {
  MAP_ASSETS,
  NETWORK_NODES,
  NETWORK_EDGES,
  ACCESS_PATHS,
  DENSITY_BINS,
  FOCUS_ENTITY_ID,
} from "../src/lib/map-network-fixture";
import {
  FRESHNESS_ROWS,
  COVERAGE_METRICS,
  CORRECTIONS,
  RESEARCH_QUEUE,
  RECORDS_REQUEST_DRAFTS,
  CORRECTIONS_PROVENANCE,
  RESEARCH_QUEUE_PROVENANCE,
  JURISDICTION_CLAIMS,
  QUEUE_AS_OF,
  QUEUE_CAMPAIGNS,
} from "../src/lib/corrections-methodology-fixture";
import {
  WATCH_ITEMS,
  EVIDENCE_ARTIFACTS,
  CLAIM_VIEWS,
  DECISION_POINT,
} from "../src/lib/watch-evidence-fixture";
import { DEFAULT_PROVENANCE } from "../src/lib/provenance";
import { DOSSIERS } from "../src/lib/dossier-fixture";
import { JURISDICTION_DOSSIERS } from "../src/lib/dossier-jurisdiction-fixture";
import { DOSSIER_SOURCES_FIXTURE } from "../src/lib/dossier-sources-fixture";
import { LEVERAGE_METRIC_FIXTURE } from "../src/lib/leverage-fixture";
import { SOURCES_FIXTURE } from "../src/lib/sources";
import { TERMS_DISCLOSURE_FIXTURE } from "../src/lib/terms-disclosure";
import {
  SOURCE_COUNTS_FIXTURE,
  SOURCE_ROWS_DOC_FIXTURE,
} from "../src/lib/source-counts";
import { DICTIONARY_FIXTURE } from "../src/lib/dictionary-fixture";
import { DOWNLOAD_LISTING_FIXTURE } from "../src/lib/downloads-fixture";
import { AS_OF, RULESET_VERSION } from "../src/lib/fixtures";

// The repository root — import.meta.url is NOT stable across the esbuild
// bundle (`export:fixtures` emits to node_modules/.cache/), so walk up to the
// uv.lock anchor the data layer's repoRoot() uses.
function repoRoot(): string {
  let dir = fileURLToPath(new URL(".", import.meta.url));
  for (;;) {
    if (existsSync(join(dir, "uv.lock"))) return dir;
    const parent = join(dir, "..");
    if (parent === dir) {
      throw new Error("repoRoot: walked above the bundle without finding uv.lock");
    }
    dir = parent;
  }
}
const REPO_ROOT = repoRoot();

const outDir = process.argv[2];
if (!outDir) {
  console.error("usage: build-fixture-export <outDir>");
  process.exit(2);
}

const webDir = join(outDir, "web");
mkdirSync(webDir, { recursive: true });

// Every artifact the harness writes — enumerated into the release manifest at
// the end so export-mode checks (check-figures' manifest verification) see the
// same listed-artifact set the real `sig-exports build` manifest records.
const writtenArtifacts: Array<{ path: string; compartment: string; license: string }> = [];

function write(name: string, payload: unknown): void {
  writeFileSync(join(webDir, name), JSON.stringify(payload, null, 2) + "\n", "utf-8");
  writtenArtifacts.push({
    path: `web/${name}`,
    compartment: "sig_graph",
    license: "CC-BY-4.0",
  });
}

// P35.40: the transparency artifact family lives at `<outDir>/transparency/`
// (NOT web/) — the same layout `sig-exports build` emits — so the export-mode
// data layer exercises the real release-artifact path.
function writeTransparency(name: string, payload: unknown): void {
  const dir = join(outDir, "transparency");
  mkdirSync(dir, { recursive: true });
  writeFileSync(join(dir, name), JSON.stringify(payload, null, 2) + "\n", "utf-8");
  writtenArtifacts.push({
    path: `transparency/${name}`,
    compartment: "sig_graph",
    license: "CC-BY-4.0",
  });
}

// The map's per-compartment PMTiles archives the export-tiles Astro integration copies
// into the build (astro.config.mjs) and `/map/style.json` names (data.ts
// getCompartmentTileSources). P31.15 (ADR-R9-TILES): the fixture bundle renders a REAL
// z0–z14 `sig_graph-sites.pmtiles` from the committed fixture points via
// `sig-exports tiles` — the same renderer a production export uses — so an
// export-mode build exercises the real tile path. If the renderer cannot run (no uv
// on PATH) no archive and no manifest row are written: never a fake/byte-empty
// archive, and an export-mode build then fails LOUD telling the operator to produce
// real tiles.
const tilesDir = join(webDir, "tiles");
const tileArtifacts: Array<{ path: string; compartment: string; license: string }> = [];
const fixtureSitesGeojson = {
  type: "FeatureCollection",
  features: MAP_ASSETS.filter((a) => a.lat !== null && a.lon !== null).map((a) => ({
    type: "Feature",
    geometry: { type: "Point", coordinates: [a.lon, a.lat] },
    properties: {
      entity_id: a.id,
      label: a.label,
      jurisdiction: a.jurisdiction,
      sensitivity_tier: a.tier,
      precision: a.precision,
    },
  })),
};
try {
  mkdirSync(tilesDir, { recursive: true });
  const tmpGeojson = join(tilesDir, "sig_graph-sites.geojson");
  writeFileSync(tmpGeojson, JSON.stringify(fixtureSitesGeojson), "utf-8");
  const dest = join(tilesDir, "sig_graph-sites.pmtiles");
  execFileSync(
    "uv",
    ["run", "sig-exports", "tiles", "--in", tmpGeojson, "--out", dest,
     "--layer", "sites", "--license", "CC-BY-4.0"],
    { stdio: "inherit" },
  );
  unlinkSync(tmpGeojson);
  tileArtifacts.push({
    path: "web/tiles/sig_graph-sites.pmtiles",
    compartment: "sig_graph",
    license: "CC-BY-4.0",
  });
} catch {
  console.warn(
    "export:fixtures: `sig-exports tiles` could not run — the bundle ships no tile " +
      "archive (SIG_DATA_SOURCE=export builds will fail loud). Run `uv sync` first.",
  );
}

const { jurisdictionIndicators } = partitionByLocatability(MAP_ASSETS);

// The ten P27.1 surface artifacts, in the frozen contract shape the getters parse.
write("map.json", {
  layers: MAP_LAYERS,
  assets: MAP_ASSETS,
  jurisdiction_indicators: jurisdictionIndicators.map((j) => ({ jurisdiction: j.jurisdiction })),
});
write("network.json", { nodes: NETWORK_NODES, edges: NETWORK_EDGES, access_paths: ACCESS_PATHS });
write("freshness.json", FRESHNESS_ROWS);
write("coverage.json", COVERAGE_METRICS);
write("watch.json", WATCH_ITEMS);
write("evidence.json", { artifacts: EVIDENCE_ARTIFACTS, claim_views: CLAIM_VIEWS });
write("corrections.json", CORRECTIONS);
write("research_queue.json", RESEARCH_QUEUE);
// P36.63 (RQ-04, SIG-RQ-007/010): the `sig.records-request-drafts/1` envelope —
// the detector's `records_requests.json` shape verbatim (DRAFT state,
// `sent: 0` always), persisted into the export so export-mode builds exercise
// the real draft seam.
write("records_request_drafts.json", {
  schema: "sig.records-request-drafts/1",
  status: "drafted",
  drafted: RECORDS_REQUEST_DRAFTS.length,
  sent: 0,
  requests: RECORDS_REQUEST_DRAFTS,
});
write(
  "dossier_index.json",
  DOSSIERS.map((d) => ({
    slug: d.slug,
    subject_label: d.subject_label,
    jurisdiction: d.jurisdiction,
    asOf: d.asOf,
  })),
);

// The pre-P27.5 surfaces the data layer already read (dossiers + leverage): the SIG-PUB-017
// FR/BE demonstration dossiers are appended by the getters in both modes, so the bundle
// carries only the base set (as `sig-exports build --jurisdiction okc` does). When this
// harness OVERLAYS a real `sig-exports build --jurisdiction okc` bundle (which already
// emits these from build_web_dossiers), we leave the real files in place — only the ten
// P27.5 surface artifacts are added.
// P31.14 — the web/analytics/ artifact family (data.ts `readAnalytics`): the export
// emits the presentation analytics the surfaces render, in the ADR-R9-ANALYTICS
// envelope (schema / as_of / named denominator / is_population_total / source
// compartments). The values here are the committed FIXTURE values — this harness is
// a test seam; production bytes come from `sig-exports build --from-spine`.
mkdirSync(join(webDir, "analytics"), { recursive: true });
const FIXTURE_COMPARTMENTS = ["sig_graph"];
const envelope = (schema: string, denominator: string, fields: Record<string, unknown>) => ({
  schema,
  as_of: AS_OF.as_of_world,
  denominator,
  is_population_total: false,
  source_compartments: FIXTURE_COMPARTMENTS,
  ...fields,
});
const analytic = (name: string, payload: unknown): void =>
  write(join("analytics", `${name}.json`), payload);

analytic(
  "density_bins",
  envelope("sig/analytics-density-bins/1", `${DENSITY_BINS.reduce((s, b) => s + b.recordCount, 0)} published site records with a releasable tier-0 point`, {
    grid: "h3",
    h3_resolution: 3,
    coverage_rule:
      "cell coverage = the number of distinct named sources contributing to the cell",
    bins: DENSITY_BINS,
  }),
);
analytic(
  "centrality",
  envelope(
    "sig/analytics-centrality/1",
    `${NETWORK_EDGES.length} typed access edges between ${NETWORK_NODES.length} entities in the exported sharing network`,
    {
      measure: "undirected degree over the typed access edges (fixture values)",
      // P34.15 (SIG-IDENT-030 by abstention): no centrality statistic is emitted —
      // the `focus` block is a presentation mechanism, not a published ranking.
      statistics: [],
      focus: {
        entity_id: FOCUS_ENTITY_ID,
        degree: null,
        rule: "the entity with the highest undirected degree over the typed access edges; ties resolve to the lexically smallest entity id",
      },
    },
  ),
);
analytic(
  "decision_point",
  envelope("sig/analytics-decision-point/1", `${WATCH_ITEMS.length} contracts on the renewal watch`, {
    rule: "the earliest derivable next_decision_date across the watch",
    decision_point: DECISION_POINT,
  }),
);
analytic(
  "provenance",
  envelope(
    "sig/analytics-provenance/1",
    `${EVIDENCE_ARTIFACTS.length} published evidence artifacts (fixture provenance set)`,
    {
      ruleset_version: RULESET_VERSION,
      surfaces: {
        // P35.40 (SIG-TRANSP-026): `source_label` names the predicate each
        // surface's source_independence_count instantiates — "sources with
        // published claims" for provenance surfaces, "detectors" for the
        // research queue — replacing the stale "independent sources" label.
        site: { ...DEFAULT_PROVENANCE, source_label: "Sources with published claims" },
        corrections: { ...CORRECTIONS_PROVENANCE, source_label: "Sources with published claims" },
        research_queue: { ...RESEARCH_QUEUE_PROVENANCE, source_label: "Detectors" },
        // P35.20a / ED-41: one provenance row per dossier slug — the surface the
        // data layer's `getDossierProvenance` reads. These are fixture values
        // (the harness is a test seam); the spine export derives each dossier's
        // row from the claims backing ITS sites. A dossier with no row here
        // falls back to the site-wide summary labelled site-wide.
        dossiers: Object.fromEntries(
          [...DOSSIERS, ...JURISDICTION_DOSSIERS].map((d) => [
            d.slug,
            {
              artifact_count: 1,
              tier_distribution: { W2: 1 },
              source_independence_count: 1,
              date_range: { earliest: AS_OF.as_of_world, latest: AS_OF.as_of_world },
              rules_applied: [RULESET_VERSION],
              human_review_status: "unreviewed",
              source_label: "Sources with published claims",
              denominator: `the claims backing the ${d.slug} dossier's sites (fixture values)`,
            },
          ]),
        ),
      },
    },
  ),
);
// P36.61 (RQ-03a): the campaign shard bytes — computed once so queue_meta's
// shard index reports the real row byte counts.
const campaignShardBytes = new Map<string, Buffer>(
  Object.entries(
    QUEUE_CAMPAIGNS.reduce<Record<string, typeof QUEUE_CAMPAIGNS>>((acc, c) => {
      const slug = c.place?.slug ?? "unplaced";
      (acc[slug] ??= []).push(c);
      return acc;
    }, {}),
  ).map(([slug, rows]) => [
    slug,
    gzipSync(Buffer.from(rows.map((r) => JSON.stringify(r)).join("\n") + "\n", "utf-8")),
  ]),
);
analytic(
  "queue_meta",
  envelope(
    // P36.58 (RQ-01): the /2 envelope — lanes/facets/shard index computed from
    // the fixture queue so fixture builds see the real export's v2 shape.
    "sig/analytics-queue-meta/2",
    `${RESEARCH_QUEUE.length} research tasks recorded; ${RESEARCH_QUEUE.length} on the public research lane; jurisdiction claims are community-curation state the claim spine does not carry`,
    {
      queue_as_of: QUEUE_AS_OF,
      jurisdiction_claims: JURISDICTION_CLAIMS,
      card_schema: "sig.queue-card/2",
      handle_grammar: "k11-handle/1",
      lanes: {
        research: RESEARCH_QUEUE.length,
        campaigns: QUEUE_CAMPAIGNS.length,
        campaign_members: QUEUE_CAMPAIGNS.reduce((n, c) => n + c.member_count, 0),
        metric_only_members: 0,
        curation: {
          exported: false,
          note: "curation-lane work happens in the loopback curation app (D-K11-5)",
        },
      },
      tasks_by_type: Object.fromEntries(
        [...new Set(RESEARCH_QUEUE.map((t) => t.task_type))].sort().map((tt) => [
          tt,
          RESEARCH_QUEUE.filter((t) => t.task_type === tt).length,
        ]),
      ),
      tasks_by_assignee: Object.fromEntries(
        [...new Set(RESEARCH_QUEUE.map((t) => t.assignee_class))].sort().map((a) => [
          a,
          RESEARCH_QUEUE.filter((t) => t.assignee_class === a).length,
        ]),
      ),
      tasks_by_place: Object.values(
        RESEARCH_QUEUE.reduce<Record<string, { slug: string; name: string | null; tasks: number }>>(
          (acc, t) => {
            const slug = t.place?.slug ?? t.jurisdiction.toLowerCase().replace(/\s+/g, "-") ?? "unplaced";
            const row = (acc[slug] ??= { slug, name: t.place?.name ?? t.jurisdiction, tasks: 0 });
            row.tasks += 1;
            return acc;
          },
          {},
        ),
      ).sort((a, b) => b.tasks - a.tasks || a.slug.localeCompare(b.slug)),
      // P36.61 (RQ-03a): the campaign shard index — mirrors the real export's
      // `web/tasks/campaign/<slug>.jsonl.gz` rows so export-mode builds see
      // the queue_meta shard table populated.
      shards: QUEUE_CAMPAIGNS.map((c) => {
        const slug = c.place?.slug ?? "unplaced";
        return {
          path: `web/tasks/campaign/${slug}.jsonl.gz`,
          lane: "campaign",
          place_slug: slug,
          rows: 1,
          bytes: campaignShardBytes.get(slug)?.length ?? 0,
        };
      }),
    },
  ),
);

// P36.62 (RQ-03b): the `web/task_handles_history.json` artifact — the same
// shape `task_export.build_queue` emits: the `/task/<task_id>/` id-aliases
// the redirect generator folds into `redirects.conf`.
write("task_handles_history.json", {
  schema: "sig.handles-history/1",
  family: "task",
  generated_at: QUEUE_AS_OF,
  note: "Fixture corpus: rows are id-aliases — /task/<task_id>/ 301s to the current handle (K11 §3).",
  rows: RESEARCH_QUEUE.filter((c) => c.task_id && c.handle).map((c) => ({
    old: `/task/${c.task_id}/`,
    target: `/task/${c.handle}/`,
    kind: "id-alias",
    note: "canonical task id → public handle",
  })),
});

// P36.61 (RQ-03a): the `web/tasks/campaign/*.jsonl.gz` shards — the same
// layout `task_export.build_queue` emits (one gzipped JSONL per place slug).
for (const [slug, blob] of campaignShardBytes) {
  const rel = join("tasks", "campaign", `${slug}.jsonl.gz`);
  mkdirSync(dirname(join(webDir, rel)), { recursive: true });
  writeFileSync(join(webDir, rel), blob);
  writtenArtifacts.push({
    path: `web/${rel.split("\\").join("/")}`,
    compartment: "sig_graph",
    license: "CC-BY-4.0",
  });
}

// P30.3 — the SIG-PUB-017 FR/BE demonstration dossiers remain an OPTIONAL
// presentation overlay (deliberately demo; ops/publish.py refuses the whole
// web/presentation/ tree in a public build). The analytics moved to web/analytics/.
mkdirSync(join(webDir, "presentation"), { recursive: true });
write(join("presentation", `jurisdiction_dossiers.json`), JURISDICTION_DOSSIERS);

if (!existsSync(join(webDir, "dossiers.json"))) write("dossiers.json", DOSSIERS);
if (!existsSync(join(webDir, "leverage.json"))) write("leverage.json", LEVERAGE_METRIC_FIXTURE);

// P36.52 (DSRC-02): the per-dossier `sig.dossier-sources/1` artifacts —
// `web/dossier_sources/<slug-path>.json`, nested like the real exporter's
// layout. The release manifest enumerates every emitted file, so the
// harness serialises the committed fixture docs verbatim and the manifest
// rows below keep export-mode figure verification on the real path.
for (const [slug, doc] of Object.entries(DOSSIER_SOURCES_FIXTURE)) {
  const rel = join("dossier_sources", `${slug}.json`);
  mkdirSync(dirname(join(webDir, rel)), { recursive: true });
  write(rel, doc);
}

// P35.37 (SIG-TRANSP-013, J3 §5.4): the figure-evidence artifacts —
// `web/sources.json` (the sig.source-licence-table/1 the /sources/ figures
// point at; fixture bytes are the committed fixture table) and
// `web/evaluation.json` (the sig.resolution-eval/1 record — the data layer
// reads it verbatim in export mode, so an export-mode build exercises the
// real release-artifact path).
write("sources.json", { schema: "sig.source-licence-table/1", rows: SOURCES_FIXTURE });
write(
  "evaluation.json",
  JSON.parse(
    readFileSync(
      join(REPO_ROOT, "exports", "src", "exports", "data", "resolution_eval.json"),
      "utf-8",
    ),
  ),
);
// P37.44 (CONF-09): `web/mech_eval.json` — the sig.mech-eval/1 mechanical
// evaluation report the /methodology/ eval table renders from; the data layer
// reads it verbatim in export mode.
write(
  "mech_eval.json",
  JSON.parse(
    readFileSync(
      join(REPO_ROOT, "exports", "src", "exports", "data", "mech_eval.json"),
      "utf-8",
    ),
  ),
);
// The express-terms disclosure (sig.terms-disclosure/1) — a figure artifact on
// /sources/; the data layer reads `web/terms_disclosure.json` in export mode.
write("terms_disclosure.json", TERMS_DISCLOSURE_FIXTURE);

// P37.45 (CONF-12, SIG-CONF-011): `web/quality.json` — the sig.quality-page/1
// artifact the /quality/ page renders from. The REAL placement-R harness
// (`sig-ops quality run --scan-dir <outDir>`) measures this fixture export's
// own bytes — the same code the release gate consumes — and `sig-exports
// quality page` wraps the measured report with the full registry
// declaration. `status/quality/latest.json` is the probe-run envelope the
// lane panel reads. uv off PATH → warn (export-mode builds then fail loud).
try {
  mkdirSync(join(outDir, "status", "quality"), { recursive: true });
  const qOut = join(outDir, ".quality-probe");
  mkdirSync(qOut, { recursive: true });
  // `sig-ops quality run` exits 0/3/4 on pass/partial/fail — every code
  // means the probe RAN and wrote its records (a `fail` verdict is the
  // fixture's own GQ-27 content, never a harness error); only a spawn
  // failure or missing outputs takes the warn path.
  const probe = spawnSync(
    "uv",
    ["run", "sig-ops", "quality", "run", "--placement", "R",
     "--scan-dir", outDir, "--target", "fixture-export",
     "--out", qOut],
    { stdio: "inherit" },
  );
  if (
    probe.error !== undefined ||
    (probe.status !== 0 && probe.status !== 3 && probe.status !== 4) ||
    !existsSync(join(qOut, "quality-report.json")) ||
    !existsSync(join(qOut, "probe-run.json"))
  ) {
    throw new Error(`quality probe did not run (status ${probe.status})`);
  }
  execFileSync(
    "uv",
    ["run", "sig-exports", "quality", "page",
     "--report", join(qOut, "quality-report.json"),
     "--target", "fixture-export",
     "--out", join(webDir, "quality.json")],
    { stdio: "inherit" },
  );
  writtenArtifacts.push({
    path: "web/quality.json",
    compartment: "sig_graph",
    license: "CC-BY-4.0",
  });
  const probeRun = JSON.parse(
    readFileSync(join(qOut, "probe-run.json"), "utf-8"),
  );
  writeFileSync(
    join(outDir, "status", "quality", "latest.json"),
    JSON.stringify(probeRun, null, 2) + "\n",
    "utf-8",
  );
  writtenArtifacts.push({
    path: "status/quality/latest.json",
    compartment: "sig_graph",
    license: "CC-BY-4.0",
  });
} catch {
  console.warn(
    "export:fixtures: the quality harness could not run — the bundle ships " +
      "no web/quality.json (SIG_DATA_SOURCE=export builds will fail loud). " +
      "Run `uv sync` first.",
  );
}

// P36.50 (SIG-TRANSP-014): the downloads listing `web/downloads.json` —
// emitted at `web/` like the real exporter; the data layer's
// getDownloadListing reads it there in export mode. When overlaying a real
// bundle, leave real bytes in place.
if (!existsSync(join(outDir, "web", "downloads.json"))) {
  write("downloads.json", DOWNLOAD_LISTING_FIXTURE);
}

// P35.40 (SIG-TRANSP-002/026/027, K9 §3.3): the source-universe pair the
// counting surfaces read in export mode — `transparency/counts.json`
// (sig.source-counts/1) and `transparency/sources.json` (sig.source-row/1).
// The fixture counts are DERIVED by buildCountsDoc, so the bundle asserts the
// same partition-sum invariant the real exporter does. When overlaying a real
// `sig-exports build` bundle, leave real bytes in place.
if (!existsSync(join(outDir, "transparency", "counts.json"))) {
  writeTransparency("counts.json", SOURCE_COUNTS_FIXTURE);
}
if (!existsSync(join(outDir, "transparency", "sources.json"))) {
  writeTransparency("sources.json", SOURCE_ROWS_DOC_FIXTURE);
}

// P35.39 (SIG-TRANSP-016): the generated `sig.data-dictionary/1` document —
// emitted at the export-dir ROOT (`<outDir>/dictionary.json`), the real
// exporter's location; the data layer's getDataDictionary reads it there in
// export mode. Emitted here so a fixture-only export-mode build exercises
// the /data/dictionary/ page. When overlaying a real bundle, leave it.
if (!existsSync(join(outDir, "dictionary.json"))) {
  writeFileSync(
    join(outDir, "dictionary.json"),
    JSON.stringify(DICTIONARY_FIXTURE, null, 2) + "\n",
    "utf-8",
  );
  writtenArtifacts.push({
    path: "dictionary.json",
    compartment: "sig_graph",
    license: "CC-BY-4.0",
  });
}

// The release manifest at the export-dir ROOT (the same location `sig-exports build
// --from-spine` writes it, exports/spine_export.py) — written LAST so `artifacts`
// enumerates every file the harness emits: P35.37's figure-evidence check verifies
// each figure's `data-artifact` against this list in export mode, so a path the
// manifest does not name fails LOUD. The site reads its belief-pinned citation
// defaults (as_of / ruleset) from `reproducibility_inputs` (P27.6, data.ts
// getSiteMetadata). Only that subset is fixture-derivable; the real manifest also
// carries checksums + compartment licences + PROV-O. Leave a real `--from-spine`
// manifest in place when overlaying one.
if (!existsSync(join(outDir, "manifest.json"))) {
  writeFileSync(
    join(outDir, "manifest.json"),
    JSON.stringify(
      {
        reproducibility_inputs: {
          as_of_snapshot: AS_OF.as_of_world,
          as_of_belief: AS_OF.as_of_belief,
          ruleset_version: RULESET_VERSION,
        },
        artifacts: [...tileArtifacts, ...writtenArtifacts],
      },
      null,
      2,
    ) + "\n",
    "utf-8",
  );
}

console.log(`fixture export bundle written to ${outDir}`);
