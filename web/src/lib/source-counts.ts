// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * P35.40 (SIG-TRANSP-002/026/027, K9 §3.1–3.3, F-431): the source universe
 * and lifecycle partition the release's `transparency/sources.json` +
 * `transparency/counts.json` carry.
 *
 * ONE counting definition, stated everywhere it is used: a **source is one
 * registry row** (`sig.source-row/1`) — a connector, an agenda-platform
 * tenant, a camera-registry endpoint, a capture host and a mirror are
 * attributes or targets of a source, never a source. One exporter function
 * (`exports.transparency.source_counts`) computes the six-state lifecycle
 * partition at the release's belief cut under the published precedence
 * (withdrawn → published → ingested_not_published → permitted_not_ingested →
 * gated → refused, first match wins); identifiers carrying data without a
 * registry row are listed as anomalies by id, never counted.
 *
 * Every count the public surface shows is a named predicate over this
 * artifact — never a carried constant. The stale numbers are mapped per K9
 * §3.3: "178 sources tracked for freshness" → "sources with published site
 * records" (`attributes.site_records`); "Independent sources" → "sources
 * with published claims" (`lifecycle.published`); the universe count is the
 * only bare "sources" headline (`universe.count`).
 */

import { AS_OF } from "./fixtures";

/** The K9 §3.2 lifecycle states in the published precedence order. */
export const LIFECYCLE_STATES = [
  "withdrawn",
  "published",
  "ingested_not_published",
  "permitted_not_ingested",
  "gated",
  "refused",
] as const;
export type LifecycleState = (typeof LIFECYCLE_STATES)[number];

/** The display label for each lifecycle state (the artifact carries the
 *  machine name + predicate definition; the label is the site's words). */
export const STATE_LABELS: Record<LifecycleState, string> = {
  withdrawn: "Withdrawn",
  published: "Published",
  ingested_not_published: "Ingested, not published",
  permitted_not_ingested: "Permitted, not ingested",
  gated: "Gated",
  refused: "Refused",
};

export const SOURCE_ROW_SCHEMA = "sig.source-row/1";
export const SOURCE_COUNTS_SCHEMA = "sig.source-counts/1";

/** A named-predicate count entry (`definition` + `count`). */
export interface NamedCount {
  definition: string;
  count: number;
}

/** A lifecycle partition entry — definition + count + the member ids. */
export interface LifecycleCount extends NamedCount {
  ids: string[];
}

/** The `sig.source-counts/1` document (`transparency/counts.json`). */
export interface SourceCountsDoc {
  schema: typeof SOURCE_COUNTS_SCHEMA;
  /** The release's belief cut the partition was computed at. */
  as_of: string;
  universe: NamedCount;
  precedence: { definition: string; order: LifecycleState[] };
  lifecycle: Record<LifecycleState, LifecycleCount>;
  /** The emitted partition check (SIG-TRANSP-027): observed === expected ===
   *  universe.count, holds === true — the export fails closed otherwise. */
  partition_sum: { definition: string; observed: number; expected: number; holds: boolean };
  attributes: {
    rights_permitted: NamedCount;
    rights_not_permitted: NamedCount;
    scheduled: NamedCount;
    one_time_load: NamedCount;
    not_scheduled: NamedCount;
    run_records_present: NamedCount;
    run_records_missing: NamedCount;
    site_records: NamedCount;
    no_site_records: NamedCount;
    lanes: { definition: string; by_lane: Record<string, number> };
    open_issues: NamedCount;
  };
  anomalies: { definition: string; ids: string[] };
}

/** The `transparency/sources.json` document — the emitted universe. */
export interface SourceRowsDoc {
  schema: typeof SOURCE_ROW_SCHEMA;
  as_of: string;
  registry_source: string;
  sources: SourceRow[];
}

/**
 * One `sig.source-row/1` row — the emitted field set. The counting surfaces
 * read only the lifecycle/counting fields; `/sources/<id>/` (P36.47) reads
 * the rest — all optional here so the counting validator stays narrow, with
 * the page-side `isSourcePageRow` asserting the renderable shape (gated
 * S-11 rows carry only `status`/`reason_class`/`homepage_url` + the
 * counting fields).
 */
export interface SourceRow {
  source_id: string;
  /** Display name (scrubbed). */
  name?: string;
  lifecycle_state: LifecycleState;
  lane?: string;
  status_flags?: string[];
  cadence?: {
    rule?: string;
    basis?: string;
    state?: string;
    scheduled?: boolean;
    one_time_load?: boolean;
  };
  published_sites?: boolean;
  published_claims?: number | string;
  /** The emitted page fields (P36.47) — present on every non-S-11 row. */
  publisher?: string;
  publisher_type?: string | null;
  lane_basis?: string;
  lane_evidence?: string | null;
  lane_decision_authority?: string | null;
  lane_review_needed?: boolean;
  part_viii_class?: string | null;
  licence?: {
    spdx: string;
    redistributable: boolean | string;
    derivative_permitted: string;
    attribution: string | null;
    terms_reviewed: boolean;
    sig_labelled_cc0: boolean;
  };
  ground_truth?: { homepage: string; homepage_host: string | null; terms_url: string };
  last_successful_run?: string;
  last_upstream_change?: { value: string | null; basis: string };
  last_sig_records_change?: { value: string | null; basis: string };
  review?: {
    basis: string;
    reviewer_role: string;
    decided_at: string | null;
    terms_reviewed: boolean;
  };
  contributions?: {
    dossier_key: string;
    dossier_slug?: string;
    records: number;
    share_of_dossier?: number | string;
    basis: string;
  }[];
  /** S-11 registry-only rows: */
  status?: string;
  reason_class?: string;
  homepage_url?: string;
}

function isCountEntry(v: unknown): v is NamedCount {
  const o = v as NamedCount | null;
  return (
    !!o && typeof o.definition === "string" && typeof o.count === "number"
  );
}

/** Validate the emitted `sig.source-counts/1` shape — fail loud, never coerce. */
export function isSourceCountsDoc(v: unknown): v is SourceCountsDoc {
  const o = v as SourceCountsDoc | null;
  if (!o || o.schema !== SOURCE_COUNTS_SCHEMA) return false;
  if (!isCountEntry(o.universe)) return false;
  // The emitted precedence is THE published order — a doc claiming a
  // different order is not a sig.source-counts/1 this build can trust.
  if (
    !Array.isArray(o.precedence?.order) ||
    o.precedence.order.length !== LIFECYCLE_STATES.length ||
    !o.precedence.order.every((s, i) => s === LIFECYCLE_STATES[i])
  ) {
    return false;
  }
  // The emitted partition check must hold — a doc that admits a broken
  // partition is refused, never rendered.
  const ps = o.partition_sum;
  if (
    !ps ||
    ps.holds !== true ||
    ps.observed !== ps.expected ||
    ps.expected !== o.universe.count
  ) {
    return false;
  }
  if (
    !LIFECYCLE_STATES.every(
      (s) =>
        isCountEntry(o.lifecycle?.[s]) && Array.isArray(o.lifecycle?.[s]?.ids),
    )
  ) {
    return false;
  }
  const a = o.attributes;
  if (
    !a ||
    ![
      a.rights_permitted,
      a.rights_not_permitted,
      a.scheduled,
      a.one_time_load,
      a.not_scheduled,
      a.run_records_present,
      a.run_records_missing,
      a.site_records,
      a.no_site_records,
      a.open_issues,
    ].every(isCountEntry)
  ) {
    return false;
  }
  if (typeof a.lanes?.definition !== "string" || typeof a.lanes?.by_lane !== "object") {
    return false;
  }
  return (
    typeof o.anomalies?.definition === "string" && Array.isArray(o.anomalies?.ids)
  );
}

/** Validate the emitted `transparency/sources.json` document. */
export function isSourceRowsDoc(v: unknown): v is SourceRowsDoc {
  const o = v as SourceRowsDoc | null;
  return (
    !!o &&
    o.schema === SOURCE_ROW_SCHEMA &&
    Array.isArray(o.sources) &&
    o.sources.every((r) => typeof r?.source_id === "string")
  );
}

// --------------------------------------------------------------------------- //
// The recompute mirror (SIG-TRANSP-027): the same derivation the exporter's
// `recompute_counts` runs, over `sources.json` rows alone. The fixture counts
// doc below is BUILT by this function so the committed pair can never drift.
// --------------------------------------------------------------------------- //

/** States `ingestion_permitted` rows can reach (the permitted attribute). */
const PERMITTED_STATES: ReadonlySet<string> = new Set([
  "published",
  "ingested_not_published",
  "permitted_not_ingested",
]);

const LANE_NAMES = ["raw-ok", "derived-only", "link-only", "restricted", "unknown"];

export interface RecomputedCounts {
  registered: number;
  partition: Record<LifecycleState, string[]>;
  rights_permitted: number;
  scheduled: number;
  one_time_load: number;
  run_records_present: number;
  run_records_missing: number;
  site_records: number;
  open_issues: number;
  lanes: Record<string, number>;
}

/** Recompute every counts.json number from source rows (mirrors the exporter). */
export function recomputeSourceCounts(rows: readonly SourceRow[]): RecomputedCounts {
  const partition = Object.fromEntries(
    LIFECYCLE_STATES.map((s) => [s, [] as string[]]),
  ) as Record<LifecycleState, string[]>;
  const lanes: Record<string, number> = Object.fromEntries(LANE_NAMES.map((l) => [l, 0]));
  let permitted = 0;
  let scheduled = 0;
  let oneTime = 0;
  let runPresent = 0;
  let runMissing = 0;
  let sitePresent = 0;
  let openIssues = 0;
  for (const row of rows) {
    const sid = String(row.source_id ?? "");
    const state = String(row.lifecycle_state ?? "") as LifecycleState;
    if (state in partition) partition[state].push(sid);
    if (PERMITTED_STATES.has(state)) permitted += 1;
    const lane = String(row.lane ?? "unknown");
    lanes[lane in lanes ? lane : "unknown"] += 1;
    if (row.cadence?.scheduled) scheduled += 1;
    if (row.cadence?.one_time_load) oneTime += 1;
    const flags = new Set(row.status_flags ?? []);
    if (flags.has("run_records_present")) runPresent += 1;
    if (flags.has("run_record_missing")) runMissing += 1;
    if (row.published_sites) sitePresent += 1;
    if (flags.has("open_issue")) openIssues += 1;
  }
  return {
    registered: rows.length,
    partition,
    rights_permitted: permitted,
    scheduled,
    one_time_load: oneTime,
    run_records_present: runPresent,
    run_records_missing: runMissing,
    site_records: sitePresent,
    open_issues: openIssues,
    lanes,
  };
}

const LIFECYCLE_DEFINITIONS: Record<LifecycleState, string> = {
  withdrawn:
    "a source-level withdrawal from publication is recorded " +
    "(no withdrawal is recorded in this registry — the predicate " +
    "exists so the state is named, not implied)",
  published:
    "≥1 claim from the source passes the publication gate in this " +
    "release (the claims this export carries)",
  ingested_not_published:
    "≥1 completion recording claims_inserted > 0 or ≥1 capture mark, " +
    "but no claim passes the publication gate in this release",
  permitted_not_ingested:
    "ingestion_permitted = true and no recorded ingestion evidence " +
    "(no claim, no claims_inserted > 0 completion, no capture mark)",
  gated:
    "ingestion_permitted false/absent, not refused, no published " +
    "claims — the source waits on a rights review",
  refused:
    "the registry records a do-not-ingest decision (compact_status = permission_declined)",
};

/** Build a `sig.source-counts/1` doc from rows — the emit seam's shape. */
export function buildCountsDoc(
  rows: readonly SourceRow[],
  anomalies: readonly string[],
  asOf: string,
): SourceCountsDoc {
  const rc = recomputeSourceCounts(rows);
  const lifecycle = Object.fromEntries(
    LIFECYCLE_STATES.map((s) => [
      s,
      {
        definition: LIFECYCLE_DEFINITIONS[s],
        count: rc.partition[s].length,
        ids: [...rc.partition[s]].sort(),
      },
    ]),
  ) as Record<LifecycleState, LifecycleCount>;
  const named = (definition: string, count: number): NamedCount => ({ definition, count });
  // Fail closed like the exporter's own assert: a fixture whose rows escape
  // the partition is a bug in the fixture, never a renderable doc.
  const partitioned = LIFECYCLE_STATES.reduce((n, s) => n + lifecycle[s].count, 0);
  if (partitioned !== rc.registered) {
    throw new Error(
      `sig.source-counts/1 partition invariant violated: ${partitioned} ` +
        `partitioned rows over ${rc.registered} registry rows`,
    );
  }
  return {
    schema: SOURCE_COUNTS_SCHEMA,
    as_of: asOf,
    universe: {
      definition: "rows in the source registry (connectors/sources.toml)",
      count: rc.registered,
    },
    precedence: {
      definition:
        "the published lifecycle precedence — each registry row takes " +
        "the first matching state at the release's belief cut (K9 §3.2)",
      order: [...LIFECYCLE_STATES],
    },
    lifecycle,
    partition_sum: {
      definition:
        "the emitted partition check — the six lifecycle state " +
        "counts must sum to the registry row count exactly once; " +
        "the export fails closed when they do not",
      observed: partitioned,
      expected: rc.registered,
      holds: true,
    },
    attributes: {
      rights_permitted: named("ingestion_permitted = true", rc.rights_permitted),
      rights_not_permitted: named(
        "ingestion_permitted false or absent",
        rc.registered - rc.rights_permitted,
      ),
      scheduled: named(
        "declared in ops/cadence.toml with state = enabled",
        rc.scheduled,
      ),
      one_time_load: named("a one-time seed load, never a schedule", rc.one_time_load),
      not_scheduled: named(
        "no declared enabled schedule and not a one-time load",
        rc.registered - rc.scheduled - rc.one_time_load,
      ),
      run_records_present: named("≥1 execution row recorded", rc.run_records_present),
      run_records_missing: named(
        "data-bearing source with no execution row (K9 C-7)",
        rc.run_records_missing,
      ),
      site_records: named(
        "≥1 published site record names the source",
        rc.site_records,
      ),
      no_site_records: named(
        "no published site record names the source",
        rc.registered - rc.site_records,
      ),
      lanes: {
        definition: "registry rows by recorded raw lane (J4)",
        by_lane: { ...rc.lanes },
      },
      open_issues: named(
        "≥1 open issue on this release's issues.jsonl",
        rc.open_issues,
      ),
    },
    anomalies: {
      definition:
        "identifiers carrying data (claims, captures, runs, sites) " +
        "with no registry row — listed by id, never counted as sources",
      ids: [...anomalies].sort(),
    },
  };
}

// --------------------------------------------------------------------------- //
// The committed fixture pair — a small synthetic registry exercising every
// lifecycle state, built through the same derivation the artifact carries.
// --------------------------------------------------------------------------- //

/** Fixture source rows — one per lifecycle state plus a second published
 *  row. Rows carry the full `sig.source-row/1` field set (P36.47 widened
 *  them — the fixture export serialises the doc verbatim, so the page-A
 *  fields a real release emits flow through here too; synthetic demo
 *  content only). */
export const SOURCE_ROWS_FIXTURE: SourceRow[] = [
  {
    source_id: "okc_camera_registry",
    name: "OKC camera registry",
    publisher: "Oklahoma City municipal data portal (demonstration entry)",
    publisher_type: "government portal",
    lifecycle_state: "published",
    status_flags: ["run_records_present"],
    lane: "raw-ok",
    lane_basis: "source_redistribution",
    lane_evidence: "recorded [redistribution] verdict (demonstration entry)",
    lane_decision_authority: "rights review",
    lane_review_needed: false,
    part_viii_class: null,
    licence: {
      spdx: "LicenseRef-PublicRecord-FactualCompilation",
      redistributable: true,
      derivative_permitted: "yes",
      attribution: "Oklahoma City municipal portal (demonstration entry)",
      terms_reviewed: true,
      sig_labelled_cc0: false,
    },
    ground_truth: {
      homepage: "https://example.invalid/okc/camera-registry",
      homepage_host: "example.invalid",
      terms_url: "https://example.invalid/okc/terms",
    },
    cadence: { rule: "monthly", basis: "ops/cadence.toml", state: "enabled", scheduled: true, one_time_load: false },
    last_successful_run: "2026-10-15T05:12:40Z",
    last_upstream_change: {
      value: "2026-10-12T00:00:00Z",
      basis: "records_digest (canonical record-set change detected by SIG — byte-only changes never move it)",
    },
    last_sig_records_change: {
      value: "2026-10-15T05:12:40Z",
      basis: "latest claim-inserting execution (interim — not a content-change measure)",
    },
    published_claims: 12,
    published_sites: true,
    review: {
      basis: "HG-03 under GL-GATE-07: err on the side of approving (demonstration entry)",
      reviewer_role: "maintainer (delegated)",
      decided_at: "2026-09-18T00:00:00Z",
      terms_reviewed: true,
    },
    contributions: [
      { dossier_key: "us-ok-oklahoma-city", dossier_slug: "usa/ok/oklahoma-city-4064000", records: 38, share_of_dossier: "demonstration", basis: "declared_by_source" },
    ],
  },
  {
    source_id: "okc_council_minutes",
    name: "OKC council minutes",
    publisher: "Oklahoma City clerk (demonstration entry)",
    publisher_type: "document index",
    lifecycle_state: "published",
    status_flags: ["run_records_present"],
    lane: "raw-ok",
    lane_basis: "source_redistribution",
    lane_evidence: null,
    lane_decision_authority: "rights review",
    lane_review_needed: false,
    part_viii_class: "P8-5",
    licence: {
      spdx: "CC0-1.0",
      redistributable: true,
      derivative_permitted: "yes",
      attribution: null,
      terms_reviewed: true,
      sig_labelled_cc0: true,
    },
    ground_truth: {
      homepage: "https://example.invalid/okc/minutes",
      homepage_host: "example.invalid",
      terms_url: "no_upstream_url_recorded",
    },
    cadence: { rule: "weekly", basis: "ops/cadence.toml", state: "enabled", scheduled: true, one_time_load: false },
    last_successful_run: "2026-10-13T05:03:11Z",
    last_upstream_change: { value: null, basis: "not_detectable (no upstream-declared date or record-set fingerprint recorded)" },
    last_sig_records_change: { value: "2026-10-13T05:03:11Z", basis: "latest claim-inserting execution (interim — not a content-change measure)" },
    published_claims: 4,
    published_sites: false,
    review: {
      basis: "reviewed licence (CC0-1.0)",
      reviewer_role: "maintainer",
      decided_at: "2026-09-10T00:00:00Z",
      terms_reviewed: true,
    },
    contributions: [],
  },
  {
    source_id: "demo_ingested_feed",
    name: "Demo ingested feed",
    publisher: "publisher_not_recorded",
    publisher_type: "upstream project",
    lifecycle_state: "ingested_not_published",
    status_flags: ["open_issue", "run_record_missing"],
    lane: "derived-only",
    lane_basis: "interim:rights-record",
    lane_evidence: null,
    lane_decision_authority: null,
    lane_review_needed: true,
    part_viii_class: null,
    licence: {
      spdx: "UNDETERMINED",
      redistributable: "UNDETERMINED",
      derivative_permitted: "UNDETERMINED",
      attribution: null,
      terms_reviewed: false,
      sig_labelled_cc0: false,
    },
    ground_truth: {
      homepage: "example.invalid#path_sha256:9f8b7c6d5e4f3a2b1c0d9e8f7a6b5c4d3e2f1a0b",
      homepage_host: "example.invalid",
      terms_url: "no_upstream_url_recorded",
    },
    cadence: { rule: "daily", basis: "ops/cadence.toml", state: "enabled", scheduled: true, one_time_load: false },
    last_successful_run: "not_recorded (no successful execution recorded)",
    last_upstream_change: { value: null, basis: "not_detectable (no captures recorded)" },
    last_sig_records_change: { value: null, basis: "not_recorded (no claim-inserting execution recorded)" },
    published_claims: "not_published",
    published_sites: false,
    review: { basis: "no_decision_recorded", reviewer_role: "not_recorded", decided_at: null, terms_reviewed: false },
    contributions: [],
  },
  {
    source_id: "demo_seed_load",
    name: "Demo one-time seed",
    publisher: "publisher_not_recorded",
    publisher_type: "bulk file",
    lifecycle_state: "permitted_not_ingested",
    status_flags: ["one_time_load"],
    lane: "link-only",
    lane_basis: "source_redistribution",
    lane_evidence: null,
    lane_decision_authority: "rights review",
    lane_review_needed: false,
    part_viii_class: null,
    licence: {
      spdx: "LicenseRef-OperatorAccepted-DBRight",
      redistributable: false,
      derivative_permitted: "no",
      attribution: null,
      terms_reviewed: true,
      sig_labelled_cc0: false,
    },
    ground_truth: {
      homepage: "https://example.invalid/seed",
      homepage_host: "example.invalid",
      terms_url: "no_upstream_url_recorded",
    },
    cadence: { rule: "not_scheduled", basis: "ops/cadence.toml", state: "disabled", scheduled: false, one_time_load: true },
    last_successful_run: "never_run",
    last_upstream_change: { value: null, basis: "not_detectable (no captures recorded)" },
    last_sig_records_change: { value: null, basis: "not_recorded (no claim-inserting execution recorded)" },
    published_claims: "not_published",
    published_sites: false,
    review: {
      basis: "HG-03 per-source review (demonstration entry)",
      reviewer_role: "maintainer",
      decided_at: "2026-09-15T00:00:00Z",
      terms_reviewed: true,
    },
    contributions: [],
  },
  {
    source_id: "demo_permitted_portal",
    name: "Demo permitted portal",
    publisher: "publisher_not_recorded",
    publisher_type: "government portal",
    lifecycle_state: "permitted_not_ingested",
    status_flags: [],
    lane: "derived-only",
    lane_basis: "interim:rights-record",
    lane_evidence: null,
    lane_decision_authority: null,
    lane_review_needed: false,
    part_viii_class: null,
    licence: {
      spdx: "UNDETERMINED",
      redistributable: "UNDETERMINED",
      derivative_permitted: "UNDETERMINED",
      attribution: null,
      terms_reviewed: false,
      sig_labelled_cc0: false,
    },
    ground_truth: {
      homepage: "https://example.invalid/portal",
      homepage_host: "example.invalid",
      terms_url: "no_upstream_url_recorded",
    },
    cadence: { rule: "monthly", basis: "ops/cadence.toml", state: "enabled", scheduled: true, one_time_load: false },
    last_successful_run: "never_run",
    last_upstream_change: { value: null, basis: "not_detectable (no captures recorded)" },
    last_sig_records_change: { value: null, basis: "not_recorded (no claim-inserting execution recorded)" },
    published_claims: "not_published",
    published_sites: false,
    review: { basis: "no_decision_recorded", reviewer_role: "not_recorded", decided_at: null, terms_reviewed: false },
    contributions: [],
  },
  {
    source_id: "demo_gated_registry",
    name: "Demo gated registry",
    publisher: "publisher_not_recorded",
    publisher_type: "camera registry",
    lifecycle_state: "gated",
    status_flags: ["rights_not_reviewed"],
    lane: "unknown",
    lane_basis: "not_reviewed",
    lane_evidence: null,
    lane_decision_authority: null,
    lane_review_needed: false,
    part_viii_class: null,
    cadence: { rule: "not_scheduled", basis: "not_declared", scheduled: false, one_time_load: false },
    published_sites: false,
    status: "gated",
    reason_class: "not_reviewed",
    homepage_url: "no_upstream_url_recorded",
  },
  {
    source_id: "demo_refused_source",
    name: "Demo refused source",
    publisher: "publisher_not_recorded",
    publisher_type: "aggregator",
    lifecycle_state: "refused",
    status_flags: ["rights_not_reviewed"],
    lane: "restricted",
    lane_basis: "source_redistribution",
    lane_evidence: null,
    lane_decision_authority: "rights review",
    lane_review_needed: false,
    part_viii_class: null,
    cadence: { rule: "not_scheduled", basis: "not_declared", scheduled: false, one_time_load: false },
    published_sites: false,
    review: { basis: "compact_status = permission_declined (demonstration entry)", reviewer_role: "maintainer", decided_at: "2026-09-20T00:00:00Z", terms_reviewed: true },
    status: "refused",
    reason_class: "refused",
    homepage_url: "example.invalid",
  },
];

/** Fixture anomalies — data-bearing identifiers with no registry row. */
export const SOURCE_ANOMALIES_FIXTURE: string[] = ["demo_unregistered_capture"];

/** The committed `sig.source-counts/1` fixture — derived, never hand-written. */
export const SOURCE_COUNTS_FIXTURE: SourceCountsDoc = buildCountsDoc(
  SOURCE_ROWS_FIXTURE,
  SOURCE_ANOMALIES_FIXTURE,
  AS_OF.as_of_belief,
);

/** The committed `transparency/sources.json` fixture doc. */
export const SOURCE_ROWS_DOC_FIXTURE: SourceRowsDoc = {
  schema: SOURCE_ROW_SCHEMA,
  as_of: AS_OF.as_of_belief,
  registry_source: "connectors/src/connectors/data/sources.toml",
  sources: [...SOURCE_ROWS_FIXTURE],
};
