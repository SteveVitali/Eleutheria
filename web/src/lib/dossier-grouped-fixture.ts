// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * P36.34 (K4 JUR-04 / R11-K13-JUR-04) — the grouped-index fixture corpus.
 *
 * A miniature canonical jurisdiction registry that exercises every index
 * feature the grouped dossier index renders (SIG-JUR-001…008/010/011):
 *
 *   - the United States grouping — a country root, admin-1 children
 *     (states + a territory), county and municipality leaves, and one
 *     no-page registry child (Cleveland County: below the D-K4-3 page
 *     threshold, so it is a named "no dossier" row on its parent while
 *     Norman hangs under it as a "non-site evidence" page);
 *   - the K13 design-centre chain for capstone journey A1 —
 *     United States → Oklahoma → Oklahoma City (the 391-record pilot);
 *   - the O1 anchor — Texas → Harris County;
 *   - non-US countries — Canada (with the Ontario admin-1 subdivision),
 *     France (a publication adapter exists) and Germany (no adapter →
 *     the conservative profile, demonstrated by a withheld
 *     public-employee name row, SIG-JUR-010);
 *   - hierarchy conservation (SIG-JUR-007): every parent's `records`
 *     equals the sum of its children's `records` plus its own
 *     `records_placed_only_here` — a unit test pins the invariant.
 *
 * Jurisdiction names, codes and schemes are public-registry facts
 * (ISO 3166-1/-2, US Census GEOIDs) asserted the same way the
 * jurisdiction registry asserts them; record counts are invented
 * fixture data (like every other `*-fixture.ts`).
 */

import { AS_OF, RULESET_VERSION } from "./fixtures";
import type { Dossier, Section } from "./dossier";
import type { UnplacedIndexEntry } from "./data";

// --- The registry descriptors ------------------------------------------------

interface RegRow {
  jkey: string;
  slug_path: string;
  name: string;
  display_name: string;
  level: "country" | "state_province" | "county" | "municipality";
  /** Registry parent (may itself have no page — Norman's Cleveland County). */
  parent_jkey: string | null;
  parent_slug_path: string | null;
  country_a2: string;
  code: string;
  scheme: string;
  /** True when this row mints a dossier page in the fixture corpus. */
  page: boolean;
  page_threshold_basis?: string;
}

const REGISTRY: RegRow[] = [
  {
    jkey: "iso3166-1:US", slug_path: "usa", name: "United States",
    display_name: "United States", level: "country",
    parent_jkey: null, parent_slug_path: null, country_a2: "US",
    code: "US", scheme: "ISO 3166-1", page: true,
    page_threshold_basis: "country dossier — an index root",
  },
  {
    jkey: "iso3166-2:US-OK", slug_path: "usa/ok", name: "Oklahoma",
    display_name: "Oklahoma, United States", level: "state_province",
    parent_jkey: "iso3166-1:US", parent_slug_path: "usa", country_a2: "US",
    code: "US-OK", scheme: "ISO 3166-2", page: true,
    page_threshold_basis: "US admin-1 — every level with records",
  },
  {
    jkey: "us.census.geoid.county:40109", slug_path: "usa/ok/oklahoma-county-40109",
    name: "Oklahoma County", display_name: "Oklahoma County, Oklahoma, United States",
    level: "county",
    parent_jkey: "iso3166-2:US-OK", parent_slug_path: "usa/ok", country_a2: "US",
    code: "40109", scheme: "US Census GEOID (county)", page: true,
    page_threshold_basis: "all counties with ≥ 1 record",
  },
  {
    jkey: "us.census.geoid.place:4064000", slug_path: "usa/ok/oklahoma-city-4064000",
    name: "Oklahoma City", display_name: "Oklahoma City, Oklahoma, United States",
    level: "municipality",
    parent_jkey: "us.census.geoid.county:40109",
    parent_slug_path: "usa/ok/oklahoma-county-40109", country_a2: "US",
    code: "4064000", scheme: "US Census GEOID (place)", page: true,
    page_threshold_basis: "places with ≥ 10 records",
  },
  {
    // Below the D-K4-3 page threshold — no dossier page. It exists only as
    // a registry child row on Oklahoma's dossier (`page: false`) and as
    // Norman's registry parent (the slug path never names it).
    jkey: "us.census.geoid.county:40131", slug_path: "usa/ok/cleveland-county-40131",
    name: "Cleveland County", display_name: "Cleveland County, Oklahoma, United States",
    level: "county",
    parent_jkey: "iso3166-2:US-OK", parent_slug_path: "usa/ok", country_a2: "US",
    code: "40131", scheme: "US Census GEOID (county)", page: false,
  },
  {
    jkey: "us.census.geoid.place:4055000", slug_path: "usa/ok/norman-city-4055000",
    name: "Norman", display_name: "Norman, Oklahoma, United States",
    level: "municipality",
    parent_jkey: "us.census.geoid.county:40131",
    parent_slug_path: "usa/ok/cleveland-county-40131", country_a2: "US",
    code: "4055000", scheme: "US Census GEOID (place)", page: true,
    page_threshold_basis: "any place with non-site evidence",
  },
  {
    jkey: "iso3166-2:US-TX", slug_path: "usa/tx", name: "Texas",
    display_name: "Texas, United States", level: "state_province",
    parent_jkey: "iso3166-1:US", parent_slug_path: "usa", country_a2: "US",
    code: "US-TX", scheme: "ISO 3166-2", page: true,
    page_threshold_basis: "US admin-1 — every level with records",
  },
  {
    jkey: "us.census.geoid.county:48201", slug_path: "usa/tx/harris-county-48201",
    name: "Harris County", display_name: "Harris County, Texas, United States",
    level: "county",
    parent_jkey: "iso3166-2:US-TX", parent_slug_path: "usa/tx", country_a2: "US",
    code: "48201", scheme: "US Census GEOID (county)", page: true,
    page_threshold_basis: "all counties with ≥ 1 record",
  },
  {
    jkey: "iso3166-2:US-VI", slug_path: "usa/vi", name: "U.S. Virgin Islands",
    display_name: "U.S. Virgin Islands, United States", level: "state_province",
    parent_jkey: "iso3166-1:US", parent_slug_path: "usa", country_a2: "US",
    code: "US-VI", scheme: "ISO 3166-2", page: true,
    page_threshold_basis: "US admin-1 — every level with records (territory state-equivalent)",
  },
  {
    jkey: "iso3166-1:CA", slug_path: "can", name: "Canada",
    display_name: "Canada", level: "country",
    parent_jkey: null, parent_slug_path: null, country_a2: "CA",
    code: "CA", scheme: "ISO 3166-1", page: true,
    page_threshold_basis: "country dossier — an index root",
  },
  {
    jkey: "iso3166-2:CA-ON", slug_path: "can/on", name: "Ontario",
    display_name: "Ontario, Canada", level: "state_province",
    parent_jkey: "iso3166-1:CA", parent_slug_path: "can", country_a2: "CA",
    code: "CA-ON", scheme: "ISO 3166-2", page: true,
    page_threshold_basis: "non-US admin-1 with ≥ 10 records",
  },
  {
    jkey: "iso3166-1:FR", slug_path: "fra", name: "France",
    display_name: "France", level: "country",
    parent_jkey: null, parent_slug_path: null, country_a2: "FR",
    code: "FR", scheme: "ISO 3166-1", page: true,
    page_threshold_basis: "country dossier — an index root",
  },
  {
    jkey: "iso3166-1:DE", slug_path: "deu", name: "Germany",
    display_name: "Germany", level: "country",
    parent_jkey: null, parent_slug_path: null, country_a2: "DE",
    code: "DE", scheme: "ISO 3166-1", page: true,
    page_threshold_basis: "country dossier — an index root",
  },
];

/** The root-first ancestor chain a dossier carries (self last). */
function chainFor(row: RegRow): { jkey: string; name: string; slug_path?: string }[] {
  const chain: { jkey: string; name: string; slug_path?: string }[] = [];
  let cur: RegRow | undefined = row;
  while (cur) {
    chain.unshift({
      jkey: cur.jkey,
      name: cur.name,
      // A registry ancestor with no page still names itself in the trail —
      // it just carries no link (Cleveland County).
      ...(cur.page ? { slug_path: cur.slug_path } : {}),
    });
    cur = cur.parent_jkey
      ? REGISTRY.find((r) => r.jkey === cur!.parent_jkey)
      : undefined;
  }
  return chain;
}

const BY_JKEY = new Map(REGISTRY.map((r) => [r.jkey, r]));

/** The registry children of `row` (page or not — `page` marks the page flag). */
function childrenOf(row: RegRow): RegRow[] {
  return REGISTRY.filter((r) => r.parent_jkey === row.jkey);
}

// --- The invented record roll-ups --------------------------------------------
//
// `records` = Σ children's records + `placed_only_here` (SIG-JUR-007
// conservation). `placed_only_here` is what a leaf carries in full.

interface Roll {
  records: number;
  placed_only_here: number;
  located_by_point: number;
  sources: { count: number; top: string[] };
  evidence: { site_observations: number; other_classes: Record<string, number | string> };
  technology: string[];
  open_questions: number;
  disagreements: { declared_here_located_elsewhere: number; located_here_declared_elsewhere: number };
  freshness: { newest: string; oldest: string };
}

const ROLLS: Record<string, Roll> = {
  "iso3166-1:US": {
    records: 5666, placed_only_here: 0, located_by_point: 5401,
    sources: { count: 21, top: ["Oklahoma camera registry", "Texas camera registry", "DeFlock ALPR map"] },
    evidence: { site_observations: 5666, other_classes: { not_evaluated: "no evidence-class vocabulary beyond site observations lands on dossiers yet (I8)" } },
    technology: ["alpr", "traffic"],
    open_questions: 12,
    disagreements: { declared_here_located_elsewhere: 3, located_here_declared_elsewhere: 1 },
    freshness: { newest: "2026-09-20", oldest: "2026-02-14" },
  },
  "iso3166-2:US-OK": {
    records: 480, placed_only_here: 12, located_by_point: 420,
    sources: { count: 2, top: ["Oklahoma camera registry", "DeFlock ALPR map"] },
    evidence: { site_observations: 480, other_classes: { not_evaluated: "no evidence-class vocabulary beyond site observations lands on dossiers yet (I8)" } },
    technology: ["alpr"],
    open_questions: 7,
    disagreements: { declared_here_located_elsewhere: 3, located_here_declared_elsewhere: 1 },
    freshness: { newest: "2026-09-20", oldest: "2026-03-04" },
  },
  "us.census.geoid.county:40109": {
    records: 420, placed_only_here: 29, located_by_point: 391,
    sources: { count: 2, top: ["Oklahoma camera registry", "DeFlock ALPR map"] },
    evidence: { site_observations: 420, other_classes: { not_evaluated: "no evidence-class vocabulary beyond site observations lands on dossiers yet (I8)" } },
    technology: ["alpr"],
    open_questions: 5,
    disagreements: { declared_here_located_elsewhere: 3, located_here_declared_elsewhere: 1 },
    freshness: { newest: "2026-09-20", oldest: "2026-03-04" },
  },
  "us.census.geoid.place:4064000": {
    records: 391, placed_only_here: 391, located_by_point: 361,
    sources: { count: 1, top: ["Oklahoma City ALPR feed"] },
    evidence: { site_observations: 391, other_classes: { not_evaluated: "no evidence-class vocabulary beyond site observations lands on dossiers yet (I8)" } },
    technology: ["alpr"],
    open_questions: 4,
    disagreements: { declared_here_located_elsewhere: 0, located_here_declared_elsewhere: 0 },
    freshness: { newest: "2026-09-12", oldest: "2026-04-11" },
  },
  "us.census.geoid.county:40131": {
    records: 48, placed_only_here: 40, located_by_point: 48,
    sources: { count: 2, top: ["Oklahoma camera registry", "Norman CCOPS ordinance"] },
    evidence: { site_observations: 48, other_classes: {} },
    technology: [],
    open_questions: 0,
    disagreements: { declared_here_located_elsewhere: 0, located_here_declared_elsewhere: 0 },
    freshness: { newest: "2026-08-01", oldest: "2026-05-02" },
  },
  "us.census.geoid.place:4055000": {
    records: 8, placed_only_here: 8, located_by_point: 8,
    sources: { count: 1, top: ["Norman CCOPS ordinance"] },
    // The D-K4-3 "+ any place with non-site evidence" leg — CCOPS records
    // are non-site evidence, so Norman keeps a page below ≥10 site records.
    evidence: { site_observations: 8, other_classes: { ccops_accountability: 2 } },
    technology: ["alpr"],
    open_questions: 2,
    disagreements: { declared_here_located_elsewhere: 0, located_here_declared_elsewhere: 0 },
    freshness: { newest: "2026-08-01", oldest: "2026-06-19" },
  },
  "iso3166-2:US-TX": {
    records: 5120, placed_only_here: 88, located_by_point: 4913,
    sources: { count: 7, top: ["Texas camera registry", "DeFlock ALPR map", "Houston procurement"] },
    evidence: { site_observations: 5120, other_classes: { not_evaluated: "no evidence-class vocabulary beyond site observations lands on dossiers yet (I8)" } },
    technology: ["alpr", "traffic"],
    open_questions: 9,
    disagreements: { declared_here_located_elsewhere: 0, located_here_declared_elsewhere: 0 },
    freshness: { newest: "2026-09-18", oldest: "2026-02-14" },
  },
  "us.census.geoid.county:48201": {
    records: 5032, placed_only_here: 5032, located_by_point: 5032,
    sources: { count: 3, top: ["Texas camera registry", "Houston procurement", "DeFlock ALPR map"] },
    evidence: { site_observations: 5032, other_classes: { not_evaluated: "no evidence-class vocabulary beyond site observations lands on dossiers yet (I8)" } },
    technology: ["alpr", "traffic"],
    open_questions: 6,
    disagreements: { declared_here_located_elsewhere: 0, located_here_declared_elsewhere: 0 },
    freshness: { newest: "2026-09-18", oldest: "2026-03-22" },
  },
  "iso3166-2:US-VI": {
    records: 66, placed_only_here: 66, located_by_point: 66,
    sources: { count: 1, top: ["Virgin Islands camera registry"] },
    evidence: { site_observations: 66, other_classes: { not_evaluated: "no evidence-class vocabulary beyond site observations lands on dossiers yet (I8)" } },
    technology: ["traffic"],
    open_questions: 3,
    disagreements: { declared_here_located_elsewhere: 0, located_here_declared_elsewhere: 0 },
    freshness: { newest: "2026-07-30", oldest: "2026-02-14" },
  },
  "iso3166-1:CA": {
    records: 1546, placed_only_here: 12, located_by_point: 1546,
    sources: { count: 9, top: ["Ontario traffic registry", "DeFlock ALPR map"] },
    evidence: { site_observations: 1546, other_classes: { not_evaluated: "no evidence-class vocabulary beyond site observations lands on dossiers yet (I8)" } },
    technology: ["traffic"],
    open_questions: 5,
    disagreements: { declared_here_located_elsewhere: 0, located_here_declared_elsewhere: 0 },
    freshness: { newest: "2026-09-02", oldest: "2026-01-29" },
  },
  "iso3166-2:CA-ON": {
    records: 1534, placed_only_here: 1534, located_by_point: 1534,
    sources: { count: 8, top: ["Ontario traffic registry", "DeFlock ALPR map"] },
    evidence: { site_observations: 1534, other_classes: { not_evaluated: "no evidence-class vocabulary beyond site observations lands on dossiers yet (I8)" } },
    technology: ["traffic"],
    open_questions: 4,
    disagreements: { declared_here_located_elsewhere: 0, located_here_declared_elsewhere: 0 },
    freshness: { newest: "2026-09-02", oldest: "2026-01-29" },
  },
  "iso3166-1:FR": {
    records: 212, placed_only_here: 212, located_by_point: 212,
    sources: { count: 2, top: ["Préfecture notices", "DECP procurement"] },
    evidence: { site_observations: 212, other_classes: { not_evaluated: "no evidence-class vocabulary beyond site observations lands on dossiers yet (I8)" } },
    technology: ["alpr"],
    open_questions: 6,
    disagreements: { declared_here_located_elsewhere: 0, located_here_declared_elsewhere: 0 },
    freshness: { newest: "2026-08-22", oldest: "2026-02-08" },
  },
  "iso3166-1:DE": {
    records: 154, placed_only_here: 154, located_by_point: 154,
    sources: { count: 2, top: ["State ordinance registry", "DeFlock ALPR map"] },
    evidence: { site_observations: 154, other_classes: { not_evaluated: "no evidence-class vocabulary beyond site observations lands on dossiers yet (I8)" } },
    technology: ["alpr"],
    open_questions: 4,
    disagreements: { declared_here_located_elsewhere: 0, located_here_declared_elsewhere: 0 },
    freshness: { newest: "2026-08-15", oldest: "2026-03-01" },
  },
};

// --- The twelve §39.2 sections (minimal keyed-dossier content) ----------------

function keyedSections(row: RegRow): Section[] {
  const place = row.display_name;
  const nameRow =
    row.country_a2 === "DE"
      ? {
          label: "Responsible officer",
          value: "Regierungsdirektor Muster",
          isPublicEmployeeName: true,
          originJurisdiction: "DE",
          subject_id: `jurisdiction:${row.jkey}`,
          predicate_id: "signing_officer",
        }
      : { label: "Record status", value: "Published placement under the recorded ruleset" };
  return [
    {
      section_id: "at_a_glance",
      rows: [
        { label: "Place", value: place },
        { label: "Lifecycle status", value: "Operational" },
      ],
    },
    {
      section_id: "what_is_deployed",
      rows: [{ label: "Record class", value: "Site observations (camera registry records)" }],
    },
    {
      section_id: "cost_and_expiry",
      rows: [{ label: "Contract value", value: null, absence: "NOT_RESEARCHED" }],
    },
    {
      section_id: "who_else_can_see",
      rows: [{ label: "Data-sharing partners", value: null, absence: "NOT_RESEARCHED" }],
    },
    {
      section_id: "configuration_and_retention",
      rows: [{ label: "Retention (days)", value: null, absence: "NO_EVIDENCE_FOUND" }],
    },
    { section_id: "usage", rows: [{ label: "Searches (windowed)", value: null }] },
    {
      section_id: "where_the_hardware_is",
      rows: [{ label: "Mapped records", value: null, note: "See the roll-up on this page." }],
    },
    {
      section_id: "policy",
      rows: [{ label: "Publication regime basis", value: `Derived from the country key (${row.country_a2})` }],
    },
    {
      section_id: "accountability_events",
      rows: [nameRow],
    },
    {
      section_id: "timeline",
      rows: [{ label: "Placement", value: "Placed by the recorded ruleset" }],
    },
    { section_id: "what_we_dont_know" },
    {
      section_id: "how_we_know_this",
      rows: [{ label: "Placement evidence", value: "Registry boundaries + the record's declared and located claims" }],
    },
  ];
}

/** Build a minimal keyed `sig.dossier/2` fixture dossier for `row`. */
function keyedDossier(row: RegRow): Dossier {
  const roll = ROLLS[row.jkey]!;
  const kids = childrenOf(row);
  const hasPrint = row.level === "country" || row.level === "state_province";
  return {
    schema: "sig.dossier/2",
    kind: "inventory_overview",
    slug: row.slug_path,
    slug_path: row.slug_path,
    jurisdiction: row.jkey,
    jurisdiction_key: row.jkey,
    jurisdictionCode: row.country_a2,
    level: row.level,
    name: row.name,
    display_name: row.display_name,
    subject_label: `Surveillance infrastructure — ${row.display_name}`,
    parent_jkey: row.parent_jkey,
    parent_slug_path: row.parent_slug_path,
    chain: chainFor(row),
    children: kids.map((k) => ({
      jkey: k.jkey,
      name: k.name,
      slug_path: k.page ? k.slug_path : undefined,
      records: ROLLS[k.jkey]!.records,
      page: k.page,
    })),
    rollup: {
      records: roll.records,
      records_placed_only_here: roll.placed_only_here,
      records_appearing: roll.records,
      conserved: true,
      note: kids.length
        ? "records = records placed only here + the sum of child jurisdictions — conserved by construction."
        : "A leaf dossier: every record appears here is placed only here.",
    },
    disagreements: { ...roll.disagreements },
    links: hasPrint ? { print: "print/" } : { print: null },
    boundary_vintage: "us-census-tiger-2025 + naturalearth-10m-v5.1",
    page_threshold_basis: row.page_threshold_basis,
    asOf: AS_OF,
    rulesetVersion: RULESET_VERSION,
    source_families: roll.sources.top,
    authorization: {
      approving_body: null,
      vote: null,
      consent_agenda: null,
      public_comment: null,
      date: null,
    },
    termination: { auto_renews: null, notice_window_days: null, expiry_date: null },
    legal_regime: { state_statute: null, local_ordinance: null, disclosure_duties: [] },
    gaps: Array.from({ length: roll.open_questions }, (_, i) => ({
      label: `Open field ${i + 1}`,
      kind: "NOT_RESEARCHED" as const,
      subject_id: `jurisdiction:${row.jkey}`,
      predicate_id: `field_${i + 1}`,
    })),
    sections: keyedSections(row),
  };
}

/** The keyed fixture dossiers (page rows only — Cleveland County has none). */
export const GROUPED_FIXTURE_DOSSIERS: Dossier[] = REGISTRY.filter((r) => r.page).map(keyedDossier);

// --- The `sig.dossier-index/2` fixture document --------------------------------

/** One index row, mirroring the export's `sig.dossier-index/2` shape. */
export interface GroupedIndexFixtureRow {
  slug: string;
  slug_path: string;
  jkey: string;
  jurisdiction: string;
  jurisdictionCode: string;
  subject_label: string;
  name: string;
  display_name: string;
  parent_name: string | null;
  parent_jkey: string | null;
  parent_slug_path: string | null;
  level: string;
  code: string;
  scheme: string;
  asOf: typeof AS_OF;
  records: number;
  records_placed_only_here: number;
  located: { by_point: number; of: number };
  sources: { count: number; top: string[] };
  evidence_types: { site_observations: number; other_classes: Record<string, number | string> };
  technology: string[];
  open_questions: number;
  disagreements: { declared_here_located_elsewhere: number; located_here_declared_elsewhere: number };
  freshness: { newest: string; oldest: string };
  children: { count: number; with_records: number; pages: number };
  page_threshold_basis: string | undefined;
}

function indexRow(row: RegRow): GroupedIndexFixtureRow {
  const roll = ROLLS[row.jkey]!;
  const kids = childrenOf(row);
  const parent = row.parent_jkey ? BY_JKEY.get(row.parent_jkey) : undefined;
  return {
    slug: row.slug_path,
    slug_path: row.slug_path,
    jkey: row.jkey,
    jurisdiction: row.jkey,
    jurisdictionCode: row.country_a2,
    subject_label: `Surveillance infrastructure — ${row.display_name}`,
    name: row.name,
    display_name: row.display_name,
    parent_name: parent?.name ?? null,
    parent_jkey: row.parent_jkey,
    parent_slug_path: row.parent_slug_path,
    level: row.level,
    code: row.code,
    scheme: row.scheme,
    asOf: AS_OF,
    records: roll.records,
    records_placed_only_here: roll.placed_only_here,
    located: { by_point: roll.located_by_point, of: roll.records },
    sources: roll.sources,
    evidence_types: roll.evidence,
    technology: roll.technology,
    open_questions: roll.open_questions,
    disagreements: roll.disagreements,
    freshness: roll.freshness,
    children: {
      count: kids.length,
      with_records: kids.filter((k) => ROLLS[k.jkey]!.records > 0).length,
      pages: kids.filter((k) => k.page).length,
    },
    page_threshold_basis: row.page_threshold_basis,
  };
}

/** The `unplaced` sibling block (`sig.dossier-index/2.unplaced`). */
export const GROUPED_UNPLACED: UnplacedIndexEntry = {
  slug_path: "unplaced",
  href: "/dossier/unplaced/",
  report: "web/unplaced.json",
  records: 0,
  excluded_from: [
    "jurisdiction counts",
    "the place facet",
    "canonical jurisdiction rows",
  ],
};

/** The fixture `sig.dossier-index/2` document — page rows only. */
export const GROUPED_INDEX_FIXTURE = {
  schema: "sig.dossier-index/2" as const,
  placement_rules: "placement@1",
  boundary_pack: { vintage: "us-census-tiger-2025 + naturalearth-10m-v5.1" },
  dossiers: REGISTRY.filter((r) => r.page).map(indexRow),
  unplaced: GROUPED_UNPLACED,
  counts: {
    jurisdictions: REGISTRY.filter((r) => r.page).length,
    dossier_pages: REGISTRY.filter((r) => r.page).length,
    unplaced_records: 0,
  },
  notes: [
    "unplaced is a data-quality report, not a jurisdiction — it is counted separately, never in the jurisdiction total",
    "per dossier, records == records_placed_only_here + records_placed_below (Σ by_leaf.records) — each placed record's chain ends at exactly one leaf, so the leaf partition is conserved by construction",
  ],
};

// --- The `sig.figure-index-sprite/1` fixture document -------------------------
//
// The FIG-01a index sprite: one outline glyph per jurisdiction key, served at
// `/dossier/figures/index-sprite.svg` (the committed fixture sheet — invented
// outline shapes standing in for real boundary outlines).

export interface IndexSpriteDoc {
  schema: string;
  columns: number;
  cell_px: number;
  rows: number;
  /** Root-relative serving path of the sprite sheet. */
  svg: string;
  glyphs: { jkey: string; row: number; col: number; x: number; y: number; cell_px: number }[];
}

export const INDEX_SPRITE_FIXTURE: IndexSpriteDoc = (() => {
  const columns = 4;
  const cellPx = 24;
  const glyphs = GROUPED_INDEX_FIXTURE.dossiers.map((d, i) => ({
    jkey: d.jkey,
    row: Math.floor(i / columns),
    col: i % columns,
    x: (i % columns) * cellPx,
    y: Math.floor(i / columns) * cellPx,
    cell_px: cellPx,
  }));
  return {
    schema: "sig.figure-index-sprite/1",
    columns,
    cell_px: cellPx,
    rows: Math.ceil(glyphs.length / columns),
    svg: "dossier/figures/index-sprite.svg",
    glyphs,
  };
})();
