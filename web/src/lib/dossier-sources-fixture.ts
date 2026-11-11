// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * P36.52 (DSRC-02) — the committed `sig.dossier-sources/1` fixture corpus.
 *
 * One document per fixture dossier, shaped exactly like the P35.44 export
 * (`web/dossier_sources/<slug-path>.json`) so the fixtures build renders the
 * same surfaces a real release does — including the edge cases the contract
 * names: `run_level_only` re-sighting absence (K5 §3.3), `not_evaluable`
 * co-location (DSRC-04 pending), `not_typed` technology, withdrawn and
 * disappeared "previously contributed" sources (D-K5-3), and one dossier
 * above the >25-source sort-route threshold (`usa`, 27 rows — K5 §4.2).
 * Synthetic demonstration content only — invented names, the demo ids of
 * `source-counts.ts` where a real source page exists.
 */

import type {
  DossierSourceRow,
  DossierSourcesDoc,
  SourceSeriesPoint,
} from "./dossier-sources";
import { DOSSIER_SOURCES_SCHEMA } from "./dossier-sources";

const RELEASE = {
  label: "demo-release",
  publication_id: "demo-release",
  as_of_world: "2026-08-20",
};

const DEFINITIONS: Record<string, string> = {
  records: "published observation-level records placed in this dossier (declared or located)",
  records_placed: "records whose placement chain resolves to this jurisdiction",
  located_by_point: "records placed by a published point inside the boundary",
  placed_by_declared: "records placed by a declared-jurisdiction claim",
  claims: "published claims asserted on the dossier's records",
  share: "the source's records as a fraction of the dossier's records",
  first_seen: "when SIG first sighted the claim (a capture time — never an installation date)",
  last_seen: "when SIG last sighted the claim (a capture time — never an installation date)",
  sightings:
    "per_run when per-link re-sighting data exists; run_level_only when one establishing link per claim across more than one completed run means the export cannot tell 'not re-sighted' from 're-sightings not recorded'",
  not_reasserted_in_latest_complete_run:
    "published claims whose last sighting run is not the source's latest completed run",
  series: "monthly contribution — records/claims first seen and claims re-sighted in the month",
  coordinate_conflicts_intra_source: "records the same source locates at conflicting coordinates",
  declared_here_located_elsewhere: "records the source declares to this jurisdiction but locates elsewhere",
  contradictions_open: "open contradiction records involving this dossier's claims",
  cross_source_colocated_candidates: "record pairs from different sources at the same published point",
};

// --- fixture source-row factory ---------------------------------------------

interface RowOpts {
  records: number;
  claims: number;
  share?: number;
  name?: string;
  publisher?: string | null;
  publisher_type?: string | null;
  lifecycle?: string | null;
  spdx?: string | null;
  compartment?: string | null;
  attribution?: string | null;
  first?: string;
  last?: string;
  firstRun?: string;
  lastRun?: string;
  runLevelOnly?: boolean;
  latestRun?: { run_id: string; finished_at: string; status: string } | "none";
  freshness?: string;
  notReasserted?: number | { not_evaluable: string };
  conflicts?: number;
  declaredElsewhere?: number;
  contradictions?: string[];
  series?: SourceSeriesPoint[];
  issues?: string[];
  entityTypes?: Record<string, number>;
  tech?: Record<string, number> | "not_typed";
  predicates?: Record<string, number>;
  checks?: Record<string, number>;
}

function src(id: string, o: RowOpts): DossierSourceRow {
  const runLevelOnly = o.runLevelOnly === true;
  return {
    source_id: id,
    name: o.name ?? id,
    publisher: o.publisher ?? null,
    publisher_type: o.publisher_type ?? null,
    lifecycle: o.lifecycle ?? "published",
    source_page: `/sources/${id}/`,
    runs_page: `/sources/${id}/runs/`,
    licence: {
      spdx: o.spdx ?? "CC0-1.0",
      compartment: o.compartment ?? "public_record",
      compartments: [o.compartment ?? "public_record"],
      attribution: o.attribution ?? null,
    },
    records: o.records,
    records_placed: o.records,
    located_by_point: o.records,
    placed_by_declared: 0,
    share: o.share ?? 0,
    claims: o.claims,
    claims_by_predicate: o.predicates ?? {
      camera_latitude: o.claims,
      camera_longitude: o.claims,
    },
    records_by_entity_type: o.entityTypes ?? { deployment: o.records },
    records_by_technology: o.tech ?? "not_typed",
    placement_checks: o.checks ?? { consistent: o.records },
    first_seen: { at: o.first ?? "2026-01-15T05:00:00Z", run_id: o.firstRun ?? `${id}-run-01` },
    last_seen: runLevelOnly
      ? {
          not_recorded:
            "re-sighting links not recorded for this source — every claim carries exactly one establishing link across more than one completed run",
        }
      : { at: o.last ?? "2026-08-15T05:00:00Z", run_id: o.lastRun ?? `${id}-run-08` },
    sightings: runLevelOnly ? "run_level_only" : "per_run",
    latest_run:
      o.latestRun === "none"
        ? { not_recorded: "no completed run recorded" }
        : (o.latestRun ?? { run_id: `${id}-run-08`, finished_at: "2026-08-15T05:10:00Z", status: "ok" }),
    freshness_state: o.freshness ?? "on_time",
    not_reasserted_in_latest_complete_run:
      o.notReasserted ??
      (runLevelOnly
        ? {
            not_evaluable:
              "re-sighting links not recorded for this source — every claim carries exactly one establishing link across more than one completed run",
          }
        : 0),
    coordinate_conflicts_intra_source: o.conflicts ?? 0,
    declared_here_located_elsewhere: o.declaredElsewhere ?? 0,
    contradictions: o.contradictions ?? [],
    series: o.series ?? [
      { period: "2026-01", records_first_seen: o.records, claims_first_seen: o.claims, claims_resighted: 0 },
      { period: "2026-08", records_first_seen: 0, claims_first_seen: 0, claims_resighted: o.claims },
    ],
    downloads: [
      {
        path: `by-source/${id}/statements.jsonl.gz`,
        name: "statements.jsonl.gz",
        format: "jsonl.gz",
        bytes: 2048,
        rows: o.claims,
        sha256: "e".repeat(64),
        href: `https://files.surveillancegraph.org/demo-release/by-source/${id}/statements.eeeeeeeeeeee.jsonl.gz`,
      },
    ],
    known_issues: o.issues ?? [],
  };
}

// --- the document factory ----------------------------------------------------

interface DocOpts {
  jkey: string | null;
  name: string;
  level: string | null;
  chain?: string[];
  boundary_vintage?: string | null;
  sources: DossierSourceRow[];
  locatedElsewherePairs?: { jkey: string; records: number }[];
  declaredElsewherePairs?: { jkey: string; records: number }[];
  contradictions?: string[];
  runsFile?: boolean;
  compartments?: string[];
}

function doc(slug: string, o: DocOpts): DossierSourcesDoc {
  const sources = o.sources;
  const records = sources.reduce((n, s) => n + s.records, 0);
  const claims = sources.reduce((n, s) => n + s.claims, 0);
  const artifact = `web/dossier_sources/${slug}.json`;
  const sumF = (f: (s: DossierSourceRow) => number) => sources.reduce((n, s) => n + f(s), 0);
  const figures = (
    [
      ["records", "Records (appearing)", "records", "/totals/records", (s: DossierSourceRow) => s.records],
      ["records_placed", "Records placed here", "records_placed", "/totals/records_placed", (s: DossierSourceRow) => s.records],
      ["claims", "Claims", "claims", "/totals/claims", (s: DossierSourceRow) => s.claims],
      ["sources", "Sources", "sources", "/totals/sources", () => 1],
      [
        "coordinate_conflicts_intra_source",
        "Intra-source coordinate conflicts",
        "coordinate_conflicts_intra_source",
        "/totals/coordinate_conflicts_intra_source",
        (s: DossierSourceRow) => s.coordinate_conflicts_intra_source,
      ],
      [
        "declared_here_located_elsewhere",
        "Declared here, located elsewhere",
        "declared_here_located_elsewhere",
        "/totals/declared_here_located_elsewhere",
        (s: DossierSourceRow) => s.declared_here_located_elsewhere,
      ],
    ] as [string, string, string, string, (s: DossierSourceRow) => number][]
  ).map(([figure_id, label, definition, pointer, f]) => {
    const value = f === undefined ? 0 : figure_id === "sources" ? sources.length : sumF(f);
    return {
      figure_id,
      label,
      value,
      definition,
      artifact,
      pointer,
      by_source: sources.map((s) => ({ source_id: s.source_id, value: f(s) })),
      sum_rule: "sum",
    };
  });
  const months = Array.from(new Set(sources.flatMap((s) => s.series.map((p) => p.period)))).sort();
  void months;
  return {
    schema: DOSSIER_SOURCES_SCHEMA,
    release: RELEASE,
    jurisdiction: {
      jkey: o.jkey,
      slug_path: slug,
      name: o.name,
      level: o.level,
      chain: o.chain ?? [],
      boundary_vintage: o.boundary_vintage ?? "us-census-tiger-2025 + naturalearth-10m-v5.1",
    },
    definitions: DEFINITIONS,
    totals: {
      records,
      records_placed: records,
      located_by_point: records,
      placed_by_declared: 0,
      claims,
      sources: sources.length,
      compartments: Array.from(new Set(sources.flatMap((s) => s.licence.compartments ?? []))).sort(),
      first_seen_at: "2026-01-15T05:00:00Z",
      last_seen_at: "2026-08-15T05:00:00Z",
      claims_by_predicate: sources.reduce(
        (acc, s) => {
          for (const [k, v] of Object.entries(s.claims_by_predicate)) acc[k] = (acc[k] ?? 0) + v;
          return acc;
        },
        {} as Record<string, number>,
      ),
      records_by_entity_type: { deployment: records },
      records_by_technology: { not_typed: records },
      coordinate_conflicts_intra_source: sumF((s) => s.coordinate_conflicts_intra_source),
      declared_here_located_elsewhere: (o.locatedElsewherePairs ?? []).reduce((n, p) => n + p.records, 0),
      located_here_declared_elsewhere: (o.declaredElsewherePairs ?? []).reduce((n, p) => n + p.records, 0),
      contradictions_open: (o.contradictions ?? []).length,
      cross_source_colocated_candidates: {
        not_evaluable: "observation_group not yet exported (DSRC-04)",
      },
    },
    provenance_summary: {
      artifact_count: sources.length,
      tier_distribution: { W3: Math.max(1, Math.floor(claims / 2)), untiered: claims - Math.max(1, Math.floor(claims / 2)) },
      sources_with_published_claims: sources.length,
      independent_lineages: { not_evaluable: "derived_from unset (PKG-12)" },
      date_range: { earliest: "2026-01-15", latest: "2026-08-15" },
      rules_applied: ["placement@1", "p27.3/1.0.0"],
      human_review_status: "unreviewed",
      scope: "dossier",
    },
    figures,
    sources,
    cross_source: {
      colocated_pairs: { not_evaluable: "observation_group not yet exported (DSRC-04)" },
      contradictions: (o.contradictions ?? []).map((id) => ({ contradiction_id: id })),
    },
    placement: {
      rules: "placement@1",
      by_basis: { point_in_polygon: records },
      declared_elsewhere_located_here: o.declaredElsewherePairs ?? [],
      declared_here_located_elsewhere: o.locatedElsewherePairs ?? [],
    },
    runs_file: o.runsFile === true ? `web/dossier_sources/${slug}.runs.jsonl.gz` : null,
    // P36.53 (DSRC-03): materialised per-compartment slices at
    // country/admin-1 (D-K5-1), the recipe block on every dossier.
    downloads:
      o.level === "country" || o.level === "state_province"
        ? (o.compartments ?? ["public_record"]).map((comp) => ({
            compartment: comp,
            license: "CC0-1.0",
            directory: `by-dossier/${slug}/${comp}/`,
            files: [
              {
                path: `by-dossier/${slug}/${comp}/sites.csv.gz`,
                name: "sites.csv.gz",
                format: "csv.gz",
                bytes: 4096,
                rows: Math.max(1, Math.floor(records / 2)),
                sha256: "a".repeat(64),
                href: `https://files.surveillancegraph.org/demo-release/by-dossier/${slug}/${comp}/sites.aaaaaaaaaaaa.csv.gz`,
              },
              {
                path: `by-dossier/${slug}/${comp}/statements.jsonl.gz`,
                name: "statements.jsonl.gz",
                format: "jsonl.gz",
                bytes: 8192,
                rows: claims,
                sha256: "b".repeat(64),
                href: `https://files.surveillancegraph.org/demo-release/by-dossier/${slug}/${comp}/statements.bbbbbbbbbbbb.jsonl.gz`,
              },
              {
                path: `by-dossier/${slug}/${comp}/ATTRIBUTION.txt`,
                name: "ATTRIBUTION.txt",
                format: "txt",
                bytes: 1024,
                sha256: "c".repeat(64),
                href: `https://files.surveillancegraph.org/demo-release/by-dossier/${slug}/${comp}/ATTRIBUTION.cccccccccccc.txt`,
              },
              {
                path: `by-dossier/${slug}/${comp}/LICENCE.txt`,
                name: "LICENCE.txt",
                format: "txt",
                bytes: 512,
                sha256: "d".repeat(64),
                href: `https://files.surveillancegraph.org/demo-release/by-dossier/${slug}/${comp}/LICENCE.dddddddddddd.txt`,
              },
            ],
          }))
        : [],
    download_recipes: {
      materialised: o.level === "country" || o.level === "state_province",
      level: o.level,
      duckdb: {
        note: "DuckDB one-liners over this release's per-compartment files — county/place dossiers are never materialised (D-K5-1): slice the national files on the statements' placement columns (jurisdiction_chain carries every ancestor key; declared_jkey the declared-bucket side).",
        files: (o.compartments ?? ["public_record"]).map((comp) => ({
          compartment: comp,
          statements: o.jkey
            ? `SELECT * FROM read_ndjson('${comp}/statements.jsonl') WHERE list_contains(placement.jurisdiction_chain, '${o.jkey}') OR placement.declared_jkey = '${o.jkey}'`
            : { not_evaluable: "this dossier keys on a declared bucket, not a registry jurisdiction key" },
          sites: `SELECT * FROM read_csv('${comp}/sites.csv', header = true) WHERE ${o.jkey ? `list_contains(jurisdiction_chain, '${o.jkey}') OR jurisdiction = '${o.jkey}'` : `jurisdiction = '${o.jkey ?? slug}'`}`,
        })),
      },
      api: {
        endpoint: `/v1/releases/{pub}/search?jurisdiction=${o.jkey ?? slug}`,
        note: "the release-namespaced federated search's jurisdiction filter — a paged result view, not a bulk export; the row-level pull is the DuckDB recipe above",
      },
    },
  };
}

// --- the corpus --------------------------------------------------------------

/** The 27-source `usa` doc — the >25-source sort-route case (K5 §4.2). */
function usaSources(): DossierSourceRow[] {
  const rows: DossierSourceRow[] = [];
  for (let i = 1; i <= 27; i += 1) {
    const id = `demo_state_registry_${String(i).padStart(2, "0")}`;
    const records = 400 - i * 12; // 388 … 88, distinct totals per source
    rows.push(
      src(id, {
        records,
        claims: records * 3,
        name: `Demo state registry ${String(i).padStart(2, "0")}`,
        publisher: "Demonstration publisher (fixture)",
        publisher_type: i % 3 === 0 ? "community map" : "government portal",
        series:
          i <= 8
            ? [
                { period: "2026-01", records_first_seen: Math.floor(records * 0.6), claims_first_seen: Math.floor(records * 1.8), claims_resighted: 0 },
                { period: "2026-05", records_first_seen: records - Math.floor(records * 0.6), claims_first_seen: records * 3 - Math.floor(records * 1.8), claims_resighted: Math.floor(records * 1.8) },
                { period: "2026-08", records_first_seen: 0, claims_first_seen: 0, claims_resighted: records },
              ]
            : undefined,
        ...(i === 2 ? { runLevelOnly: true } : {}),
        ...(i === 3 ? { lifecycle: "withdrawn", notReasserted: records * 3 } : {}),
        ...(i === 4 ? { freshness: "disappeared" } : {}),
        ...(i === 5 ? { conflicts: 7 } : {}),
        ...(i === 6 ? { latestRun: "none", freshness: "never_run" } : {}),
      }),
    );
  }
  // shares
  const total = rows.reduce((n, s) => n + s.records, 0);
  for (const s of rows) s.share = Math.round((s.records / total) * 10000) / 10000;
  return rows;
}

const MONTHS_2: SourceSeriesPoint[] = [
  { period: "2026-02", records_first_seen: 30, claims_first_seen: 90, claims_resighted: 0 },
  { period: "2026-08", records_first_seen: 8, claims_first_seen: 24, claims_resighted: 60 },
];

function docs(): Record<string, DossierSourcesDoc> {
  const out: Record<string, DossierSourcesDoc> = {};
  out["usa"] = doc("usa", {
    jkey: "iso3166-1:US",
    name: "United States",
    level: "country",
    sources: usaSources(),
    locatedElsewherePairs: [{ jkey: "us.census.geoid.county:48201", records: 41 }],
    contradictions: ["contra:device-count-42-38"],
    runsFile: true,
    compartments: ["public_record", "osm_physical"],
  });
  const ok = doc("usa/ok", {
    jkey: "iso3166-2:US-OK",
    name: "Oklahoma",
    level: "state_province",
    chain: ["iso3166-1:US"],
    runsFile: true,
    locatedElsewherePairs: [{ jkey: "us.census.geoid.county:48201", records: 12 }],
    contradictions: ["contra:device-count-42-38"],
    sources: [
      src("okc_camera_registry", {
        records: 38,
        claims: 120,
        share: 0.5,
        name: "OKC camera registry",
        publisher: "Oklahoma City municipal data portal (demonstration entry)",
        publisher_type: "government portal",
        spdx: "LicenseRef-PublicRecord-FactualCompilation",
        attribution: "Oklahoma City municipal portal (demonstration entry)",
        series: MONTHS_2,
      }),
      src("okc_council_minutes", {
        records: 20,
        claims: 55,
        share: 0.2632,
        name: "OKC council minutes",
        publisher: "Oklahoma City clerk (demonstration entry)",
        publisher_type: "document index",
        series: MONTHS_2,
      }),
      src("demo_seed_load", {
        records: 12,
        claims: 30,
        share: 0.1579,
        name: "Demo seed load",
        publisher_type: "community map",
        runLevelOnly: true,
        series: MONTHS_2,
      }),
      src("demo_permitted_portal", {
        records: 6,
        claims: 14,
        share: 0.0789,
        name: "Demo permitted portal",
        publisher_type: "government portal",
        conflicts: 3,
        declaredElsewhere: 12,
        contradictions: ["contra:device-count-42-38"],
        series: MONTHS_2,
      }),
    ],
  });
  out["usa/ok"] = ok;
  out["usa/ok/oklahoma-county-40109"] = doc("usa/ok/oklahoma-county-40109", {
    jkey: "us.census.geoid.county:40109",
    name: "Oklahoma County",
    level: "county",
    chain: ["iso3166-1:US", "iso3166-2:US-OK"],
    sources: [
      src("okc_camera_registry", { records: 26, claims: 84, share: 0.8125, name: "OKC camera registry", publisher_type: "government portal" }),
      src("demo_seed_load", { records: 6, claims: 16, share: 0.1875, name: "Demo seed load" }),
    ],
  });
  // SIG-DSRC-008 parity: okc_camera_registry's fixture contributions[] row says
  // records: 38 on this dossier — the same number, one derivation.
  out["usa/ok/oklahoma-city-4064000"] = doc("usa/ok/oklahoma-city-4064000", {
    jkey: "us.census.geoid.place:4064000",
    name: "Oklahoma City",
    level: "municipality",
    chain: ["iso3166-1:US", "iso3166-2:US-OK", "us.census.geoid.county:40109"],
    sources: [
      src("okc_camera_registry", { records: 38, claims: 120, share: 0.8444, name: "OKC camera registry", publisher: "Oklahoma City municipal data portal (demonstration entry)", publisher_type: "government portal", spdx: "LicenseRef-PublicRecord-FactualCompilation" }),
      src("okc_council_minutes", { records: 7, claims: 21, share: 0.1556, name: "OKC council minutes", publisher_type: "document index" }),
    ],
  });
  out["usa/ok/norman-city-4055000"] = doc("usa/ok/norman-city-4055000", {
    jkey: "us.census.geoid.place:4055000",
    name: "Norman",
    level: "municipality",
    chain: ["iso3166-1:US", "iso3166-2:US-OK", "us.census.geoid.county:40131"],
    sources: [src("demo_seed_load", { records: 9, claims: 24, share: 1, name: "Demo seed load" })],
  });
  out["usa/tx"] = doc("usa/tx", {
    jkey: "iso3166-2:US-TX",
    name: "Texas",
    level: "state_province",
    chain: ["iso3166-1:US"],
    runsFile: true,
    sources: [
      src("demo_state_registry_01", { records: 210, claims: 640, share: 0.7, name: "Demo state registry 01" }),
      src("demo_state_registry_02", { records: 60, claims: 180, share: 0.2, name: "Demo state registry 02" }),
      src("demo_ingested_feed", { records: 30, claims: 90, share: 0.1, name: "Demo ingested feed", lifecycle: "ingested_not_published" }),
    ],
  });
  out["usa/tx/harris-county-48201"] = doc("usa/tx/harris-county-48201", {
    jkey: "us.census.geoid.county:48201",
    name: "Harris County",
    level: "county",
    chain: ["iso3166-1:US", "iso3166-2:US-TX"],
    declaredElsewherePairs: [{ jkey: "iso3166-2:US-OK", records: 12 }],
    sources: [
      src("demo_state_registry_01", { records: 55, claims: 170, share: 0.7857, name: "Demo state registry 01" }),
      src("demo_permitted_portal", { records: 15, claims: 44, share: 0.2143, name: "Demo permitted portal" }),
    ],
  });
  out["usa/vi"] = doc("usa/vi", {
    jkey: "iso3166-2:US-VI",
    name: "U.S. Virgin Islands",
    level: "state_province",
    chain: ["iso3166-1:US"],
    runsFile: true,
    sources: [src("demo_seed_load", { records: 4, claims: 12, share: 1, name: "Demo seed load" })],
  });
  out["can"] = doc("can", {
    jkey: "iso3166-1:CA",
    name: "Canada",
    level: "country",
    runsFile: true,
    sources: [
      src("demo_state_registry_10", { records: 90, claims: 270, share: 0.9, name: "Demo state registry 10" }),
      src("demo_seed_load", { records: 10, claims: 30, share: 0.1, name: "Demo seed load" }),
    ],
  });
  out["can/on"] = doc("can/on", {
    jkey: "iso3166-2:CA-ON",
    name: "Ontario",
    level: "state_province",
    chain: ["iso3166-1:CA"],
    runsFile: true,
    sources: [
      src("demo_state_registry_10", { records: 60, claims: 180, share: 0.8571, name: "Demo state registry 10" }),
      src("demo_seed_load", { records: 10, claims: 30, share: 0.1429, name: "Demo seed load" }),
    ],
  });
  out["fra"] = doc("fra", {
    jkey: "iso3166-1:FR",
    name: "France",
    level: "country",
    runsFile: true,
    sources: [
      src("demo_state_registry_11", { records: 140, claims: 420, share: 0.6604, name: "Préfecture notices (fixture)" }),
      src("demo_state_registry_12", { records: 72, claims: 216, share: 0.3396, name: "DECP procurement (fixture)" }),
    ],
  });
  out["deu"] = doc("deu", {
    jkey: "iso3166-1:DE",
    name: "Germany",
    level: "country",
    runsFile: true,
    sources: [
      src("demo_state_registry_13", { records: 100, claims: 300, share: 0.6494, name: "State ordinance registry (fixture)" }),
      src("demo_state_registry_14", { records: 54, claims: 162, share: 0.3506, name: "DeFlock ALPR map (fixture)" }),
    ],
  });
  out["oklahoma-city"] = doc("oklahoma-city", {
    jkey: "us-ok-oklahoma-city",
    name: "Oklahoma City",
    level: null,
    contradictions: ["contra:device-count-42-38"],
    sources: [
      src("okc_camera_registry", { records: 38, claims: 120, share: 0.7600, name: "OKC camera registry", publisher: "Oklahoma City municipal data portal (demonstration entry)", publisher_type: "government portal", spdx: "LicenseRef-PublicRecord-FactualCompilation" }),
      src("okc_council_minutes", { records: 8, claims: 24, share: 0.1600, name: "OKC council minutes", publisher_type: "document index" }),
      src("demo_seed_load", { records: 4, claims: 12, share: 0.0800, name: "Demo seed load", runLevelOnly: true }),
    ],
  });
  out["paris-alpr"] = doc("paris-alpr", {
    jkey: "fr-idf-paris",
    name: "Paris",
    level: null,
    sources: [
      src("demo_state_registry_11", { records: 60, claims: 180, share: 0.75, name: "Arrêté préfectoral (fixture)" }),
      src("demo_state_registry_12", { records: 20, claims: 60, share: 0.25, name: "Avis de marché public (DECP) (fixture)" }),
    ],
  });
  out["brussels-alpr"] = doc("brussels-alpr", {
    jkey: "be-bru-brussels",
    name: "Brussels",
    level: null,
    sources: [
      src("demo_state_registry_13", { records: 44, claims: 132, share: 0.7097, name: "Politiereglement (fixture)" }),
      src("demo_state_registry_14", { records: 18, claims: 54, share: 0.2903, name: "Overheidsopdracht (DECP) (fixture)" }),
    ],
  });
  return out;
}

/** The committed `sig.dossier-sources/1` fixture set, keyed by dossier slug path. */
export const DOSSIER_SOURCES_FIXTURE: Readonly<Record<string, DossierSourcesDoc>> = docs();
