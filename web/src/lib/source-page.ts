// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * P36.47 (R11-K13-UX10-3a; SIG-TRANSP-003/004/009/037/038/039, SIG-UI-056,
 * SIG-DSRC-008 cited) — the `/sources/<id>/` page-A model: the composition
 * layer between the release's transparency artifacts and the page template.
 *
 * Data seams (all release-pinned, never a live read):
 *
 *   - `transparency/sources.json` — the `sig.source-row/1` rows: identity,
 *     licence, ground truth (S-1/S-6 scrubbed by the emitter), cadence, the
 *     K9 change columns, the rights-review record and the dossier
 *     `contributions` mirror (P35.44). A gated/refused/withdrawn or
 *     unknown/restricted-lane row is the S-11 registry-only record — the
 *     page renders exactly that and nothing more.
 *   - `transparency/sources/<id>/executions.jsonl` — the per-source
 *     `sig.execution-record/1` feed (P36.46). Absent → `null` (honest
 *     absence: SIG-TRANSP-037's no-record honesty, never a fabricated run).
 *   - `transparency/freshness.jsonl` — the K9 freshness verdict + staleness
 *     fields evaluated at the release as-of (P35.41) when present.
 *   - `web/terms_disclosure.json` — the ADR-183 express-terms block for the
 *     sources that carry one (terms capture date + evidence).
 *
 * Registry fields whose publication verdict is `never` (robots_policy,
 * notes, contact) cannot appear here — the page reads only emitted
 * artifacts, so the P36.45 publish matrix binds by construction.
 * Fields the artifacts do not yet carry (targets, technology classes,
 * declared geography, an approved description, the crawler identity
 * string) ride the extras map: a fixture value renders, a missing artifact
 * renders the typed absence — never a blank and never a guess
 * (SIG-TRANSP-003: every field a value or a named absence kind).
 *
 * D-J3-2 [B-19] = yes carried verbatim: the robots-disregard disclosure is
 * host + count + the GL-GATE-08 decision reference — never per-URL detail.
 * D-K10-1 [B-2] = OD-07 a: the standard disclosure texts render through
 * the copy-batch flow; an unapproved description renders the verbatim
 * interim "description pending review".
 */

import { existsSync, readFileSync } from "node:fs";
import { dataSource, exportDir, getTermsDisclosure } from "./data";
import { AS_OF } from "./fixtures";
import { resolveSourceId } from "./alias";
import {
  SOURCE_ROWS_DOC_FIXTURE,
  isSourceRowsDoc,
  type LifecycleState,
  type SourceRow,
} from "./source-counts";

export const SOURCE_PAGE_SCHEMA = "sig.source-page/2";
export const EXECUTION_RECORD_SCHEMA = "sig.execution-record/1";

// ---------------------------------------------------------------------------
// The emitted shapes (the contract mirrors — validators fail closed).
// ---------------------------------------------------------------------------

/** `{value, basis}` — the K9 change-column shape (C-6/§5.4). */
export interface ChangeField {
  value: string | null;
  basis: string;
}

/** The `sig.source-row/1` fields page A reads (emitted superset of the
 *  counting `SourceRow` — the same row document, typed fully here). */
export interface SourcePageRow {
  source_id: string;
  name: string;
  publisher: string;
  publisher_type: string | null;
  lifecycle_state: LifecycleState;
  status_flags: string[];
  lane: string;
  lane_basis: string;
  lane_evidence: string | null;
  lane_decision_authority: string | null;
  lane_review_needed: boolean;
  part_viii_class: string | null;
  licence: {
    spdx: string;
    redistributable: boolean | string;
    derivative_permitted: string;
    attribution: string | null;
    terms_reviewed: boolean;
    sig_labelled_cc0: boolean;
  };
  ground_truth: { homepage: string; homepage_host: string | null; terms_url: string };
  cadence: {
    rule: string;
    basis: string;
    state?: string;
    scheduled: boolean;
    one_time_load: boolean;
  };
  last_successful_run: string;
  last_upstream_change: ChangeField;
  last_sig_records_change: ChangeField;
  published_claims: number | string;
  published_sites: boolean;
  review: {
    basis: string;
    reviewer_role: string;
    decided_at: string | null;
    terms_reviewed: boolean;
  };
  /** The P35.44 dossier-contribution mirror — the same rows the dossier
   *  artifacts carry (parity by construction, SIG-DSRC-008). S-11 rows
   *  omit the field entirely (a gated row discloses no contribution). */
  contributions?: ContributionRow[];
  /** S-11 registry-only rows: */
  status?: string;
  reason_class?: string;
  homepage_url?: string;
}

/** One contribution row of the shared dossier-source artifact (P35.44). */
export interface ContributionRow {
  dossier_key: string;
  dossier_slug?: string;
  records: number;
  share_of_dossier?: number | string;
  basis: string;
}

/** `sig.execution-record/1` — the fields the page reads (the emitted feed
 *  carries more; validators require only what the render consumes). */
export interface ExecutionRecord {
  schema: string;
  execution_id: string;
  run_id: string | null;
  source_id: string;
  link_basis: string | null;
  clock_basis: string | null;
  shared_run: boolean;
  started_at: string | null;
  started_basis: string;
  finished_at: string | null;
  duration_seconds: number | null;
  outcome: string;
  claims_considered: number | string | null;
  claims_inserted: number | string | null;
  claims_duplicate: number | string | null;
  fetches: number | null;
  records_emitted: number | null;
  rejected: Record<string, number> | null;
  error_class: string | null;
  error_classes: Record<string, number> | null;
  robots: { host: string; outcome: string; count: number; decision_ref?: string }[];
  rate_limit_events: number | null;
  disappearances: number | null;
  document_outcomes: Record<string, number> | null;
  quota_reached: boolean | null;
  budget_reached: boolean | null;
  code_commit: string | null;
  connector_name: string | null;
  connector_version: string | null;
  recorded_at: string | null;
  execution_key: string | null;
  mode: string | null;
  kind: string | null;
  code_identity: { connector_name: unknown; connector_version: unknown; code_commit: unknown; basis: string };
}

/** The freshness row (`transparency/freshness.jsonl`, FRESHNESS_RECORD_FIELDS). */
export interface SourceFreshness {
  source_id: string;
  cadence_rule: string;
  cadence_basis: string;
  cadence_state: string;
  scheduled: boolean;
  one_time_load: boolean;
  freshness_state: string;
  run_record_missing: boolean;
  evaluated_at: string;
  last_upstream_change?: ChangeField;
  last_sig_records_change?: ChangeField;
  volatility?: Record<string, number> | null;
  staleness?: { evaluable: number; not_evaluable: number } | null;
}

/** One target row (`sig.source-targets/1` shape — the artifact is not yet
 *  emitted; fixtures carry the contract so the section renders typed). */
export interface SourceTarget {
  label: string;
  host: string;
  jurisdiction: string | null;
  observed_count: number | null;
  last_capture: string | null;
  last_change: string | null;
  state: "active" | "disappeared" | "enumerated_not_fetched";
}

/** The rights-record coverage class (K10 §6/E4's vocabulary — derived,
 *  never re-decided). */
export type CoverageClass =
  | "delegated_rule"
  | "outside_rule"
  | "terms_conflict"
  | "counsel"
  | "per_source_review"
  | "registry_only"
  | "gated"
  | "refused";

/** Fields page A renders that the emitted artifacts do not carry yet —
 *  each falls back to a typed absence, never a blank. */
export interface SourcePageExtras {
  /** The operator-approved description; absent → the OD-07-a interim text. */
  description: string | null;
  technology_classes: string[] | null;
  geography: string | null;
  targets: SourceTarget[] | null;
  crawler_identity: string | null;
  /** Where the registry records a declared robots posture contradicted by
   *  observed runs — the fixture exercises the F-184 mismatch note. */
  robots_registry_declared: string | null;
  coverage_class: CoverageClass | null;
  terms_conflict_excerpt: string | null;
}

/** The assembled page model. */
export interface SourcePageModel {
  row: SourcePageRow;
  extras: SourcePageExtras;
  /** `null` when no executions artifact exists (SIG-TRANSP-037 honesty). */
  executions: ExecutionRecord[] | null;
  /** The freshness row when the artifact carries one. */
  freshness: SourceFreshness | null;
  /** S-11 registry-only page (gated/refused/withdrawn/lane-gated). */
  registryOnly: boolean;
}

// ---------------------------------------------------------------------------
// Validators — fail closed, never coerce (export mode fails LOUD).
// ---------------------------------------------------------------------------

function isChangeField(v: unknown): v is ChangeField {
  const o = v as ChangeField | null;
  return !!o && (o.value === null || typeof o.value === "string") && typeof o.basis === "string";
}

/** S-11 registry-only detection — the emitter's precedence: a gated /
 *  refused / withdrawn lifecycle or an unknown / restricted lane, or the
 *  explicit S-11 fields (`status`, `reason_class`). */
function isRegistryOnlyShape(o: { lifecycle_state: string; lane?: string; status?: string; reason_class?: string }): boolean {
  return (
    o.status !== undefined ||
    o.reason_class !== undefined ||
    o.lifecycle_state === "gated" ||
    o.lifecycle_state === "refused" ||
    o.lifecycle_state === "withdrawn" ||
    o.lane === "unknown" ||
    o.lane === "restricted"
  );
}

export function isSourcePageRow(v: unknown): v is SourcePageRow {
  const o = v as SourcePageRow | null;
  if (!o || typeof o.source_id !== "string" || typeof o.lifecycle_state !== "string") return false;
  if (isRegistryOnlyShape(o)) {
    // S-11 gated row: identity + status/reason class + the counting fields.
    return typeof o.name === "string" && typeof o.lane === "string";
  }
  return (
    typeof o.name === "string" &&
    typeof o.lane === "string" &&
    !!o.licence &&
    typeof o.licence.spdx === "string" &&
    !!o.ground_truth &&
    typeof o.ground_truth.homepage === "string" &&
    !!o.review &&
    typeof o.review.basis === "string"
  );
}

export function isExecutionRecord(v: unknown): v is ExecutionRecord {
  const o = v as ExecutionRecord | null;
  return (
    !!o &&
    o.schema === EXECUTION_RECORD_SCHEMA &&
    typeof o.source_id === "string" &&
    typeof o.outcome === "string" &&
    Array.isArray(o.robots)
  );
}

// ---------------------------------------------------------------------------
// The committed fixture model — synthetic demonstration data exercising
// every section and every named-absence kind (§3.1: demo ids, never real).
// ---------------------------------------------------------------------------

/** The page row lookup — fixtures mode reads the committed
 *  `transparency/sources.json` fixture (one row universe for the counting
 *  surfaces AND the page; export mode reads the release's artifact). The
 *  renderable shape is asserted through `isSourcePageRow` (fail closed). */
function fixturePageRow(sourceId: string): SourcePageRow | null {
  for (const raw of SOURCE_ROWS_DOC_FIXTURE.sources) {
    const o = raw as SourceRow;
    if (o.source_id !== sourceId) continue;
    if (!isSourcePageRow(o)) {
      throw new Error(`SOURCE_ROWS_DOC_FIXTURE: row ${sourceId} is not a renderable sig.source-row/1`);
    }
    return o;
  }
  return null;
}

/** Per-source extras — the fields the artifacts do not carry yet (each a
 *  value or `null` → the typed absence; synthetic demo content). */
export const SOURCE_PAGE_EXTRAS_FIXTURE: Record<string, SourcePageExtras> = {
  okc_camera_registry: {
    description: "The Oklahoma City municipal open-data portal's camera-registry datasets (demonstration entry — invented fixture text).",
    technology_classes: ["camera registry"],
    geography: "Oklahoma City, Oklahoma (declared by the source)",
    targets: [
      { label: "OKC open-data camera layer", host: "example.invalid", jurisdiction: "Oklahoma City, OK", observed_count: 38, last_capture: "2026-10-15T05:12:40Z", last_change: "2026-10-12T00:00:00Z", state: "active" },
      { label: "Downtown pilot feed", host: "example.invalid", jurisdiction: "Oklahoma City, OK", observed_count: 0, last_capture: null, last_change: null, state: "enumerated_not_fetched" },
    ],
    crawler_identity: "SIG research crawler (project contact page, demonstration entry)",
    robots_registry_declared: "honor",
    coverage_class: "delegated_rule",
    terms_conflict_excerpt: null,
  },
  okc_council_minutes: {
    description: null,
    technology_classes: null,
    geography: "Oklahoma City, Oklahoma (declared by the source)",
    targets: null,
    crawler_identity: null,
    robots_registry_declared: null,
    coverage_class: "per_source_review",
    terms_conflict_excerpt: null,
  },
  demo_ingested_feed: {
    description: null,
    technology_classes: null,
    geography: null,
    targets: null,
    crawler_identity: null,
    robots_registry_declared: null,
    coverage_class: "registry_only",
    terms_conflict_excerpt: null,
  },
  demo_seed_load: {
    description: null,
    technology_classes: null,
    geography: null,
    targets: null,
    crawler_identity: null,
    robots_registry_declared: null,
    coverage_class: "per_source_review",
    terms_conflict_excerpt: null,
  },
  demo_permitted_portal: {
    description: null,
    technology_classes: null,
    geography: null,
    targets: null,
    crawler_identity: null,
    robots_registry_declared: null,
    coverage_class: "registry_only",
    terms_conflict_excerpt: null,
  },
  demo_gated_registry: {
    description: null,
    technology_classes: null,
    geography: null,
    targets: null,
    crawler_identity: null,
    robots_registry_declared: null,
    coverage_class: "gated",
    terms_conflict_excerpt: null,
  },
  demo_refused_source: {
    description: null,
    technology_classes: null,
    geography: null,
    targets: null,
    crawler_identity: null,
    robots_registry_declared: null,
    coverage_class: "refused",
    terms_conflict_excerpt: null,
  },
};

const NO_EXTRAS: SourcePageExtras = {
  description: null,
  technology_classes: null,
  geography: null,
  targets: null,
  crawler_identity: null,
  robots_registry_declared: null,
  coverage_class: null,
  terms_conflict_excerpt: null,
};

const _EXEC = (
  over: Partial<ExecutionRecord> & Pick<ExecutionRecord, "execution_id" | "source_id" | "outcome" | "started_at" | "finished_at">,
): ExecutionRecord => ({
  schema: EXECUTION_RECORD_SCHEMA,
  run_id: null,
  link_basis: "live",
  clock_basis: "report",
  shared_run: false,
  started_basis: "report",
  duration_seconds: null,
  claims_considered: null,
  claims_inserted: null,
  claims_duplicate: null,
  fetches: null,
  records_emitted: null,
  rejected: null,
  error_class: null,
  error_classes: null,
  robots: [],
  rate_limit_events: null,
  disappearances: null,
  document_outcomes: null,
  quota_reached: null,
  budget_reached: null,
  code_commit: null,
  connector_name: "demo_connector",
  connector_version: "0.0.0-demo",
  recorded_at: null,
  execution_key: null,
  mode: "live",
  kind: "scheduled-ingest",
  code_identity: { connector_name: "demo_connector", connector_version: "0.0.0-demo", code_commit: "demo", basis: "ingest_run (the execution owns its run)" },
  ...over,
});

/** Fixture `sig.execution-record/1` feeds per source — exercise every
 *  conduct row the page renders (robots per host incl. the GL-GATE-08
 *  disclosure, refusals, rate limits, outcomes for the runs strip). */
export const SOURCE_EXECUTIONS_FIXTURE: Record<string, ExecutionRecord[]> = {
  okc_camera_registry: [
    _EXEC({
      execution_id: "demo-exec-okc-1",
      source_id: "okc_camera_registry",
      outcome: "ok",
      started_at: "2026-09-15T05:00:00Z",
      finished_at: "2026-09-15T05:11:02Z",
      duration_seconds: 662,
      claims_considered: 41,
      claims_inserted: 38,
      claims_duplicate: 3,
      fetches: 3,
      robots: [
        { host: "example.invalid", outcome: "obeyed", count: 3 },
        { host: "data.example.invalid", outcome: "unavailable", count: 1 },
      ],
    }),
    _EXEC({
      execution_id: "demo-exec-okc-2",
      source_id: "okc_camera_registry",
      outcome: "partial",
      started_at: "2026-10-01T05:00:00Z",
      finished_at: "2026-10-01T05:09:18Z",
      duration_seconds: 558,
      claims_considered: 40,
      claims_inserted: 36,
      claims_duplicate: 4,
      fetches: 4,
      rejected: { malformed_row: 2 },
      robots: [
        { host: "example.invalid", outcome: "obeyed", count: 3 },
        { host: "data.example.invalid", outcome: "disregarded", count: 4, decision_ref: "GL-GATE-08" },
      ],
      rate_limit_events: 1,
    }),
    _EXEC({
      execution_id: "demo-exec-okc-3",
      source_id: "okc_camera_registry",
      outcome: "ok",
      connector_version: "0.1.0-demo", // exercises the changelog's connector_version event (P37.41)
      started_at: "2026-10-15T05:00:00Z",
      finished_at: "2026-10-15T05:12:40Z",
      duration_seconds: 760,
      claims_considered: 42,
      claims_inserted: 38,
      claims_duplicate: 4,
      fetches: 4,
      robots: [
        { host: "example.invalid", outcome: "obeyed", count: 4 },
        { host: "data.example.invalid", outcome: "disallowed", count: 1 },
      ],
    }),
  ],
  okc_council_minutes: [
    _EXEC({
      execution_id: "demo-exec-min-1",
      source_id: "okc_council_minutes",
      outcome: "ok",
      started_at: "2026-10-13T05:00:00Z",
      finished_at: "2026-10-13T05:03:11Z",
      duration_seconds: 191,
      claims_considered: 5,
      claims_inserted: 4,
      claims_duplicate: 0,
      rejected: { off_vocabulary: 1 },
      fetches: 2,
      robots: [{ host: "example.invalid", outcome: "obeyed", count: 2 }],
    }),
  ],
};

/** Fixture freshness rows (`transparency/freshness.jsonl` shape) for the
 *  sources the fixture lane doc tracks. */
export const SOURCE_FRESHNESS_FIXTURE: Record<string, SourceFreshness> = {
  okc_camera_registry: {
    source_id: "okc_camera_registry",
    cadence_rule: "monthly",
    cadence_basis: "ops/cadence.toml",
    cadence_state: "enabled",
    scheduled: true,
    one_time_load: false,
    freshness_state: "on_time",
    run_record_missing: false,
    evaluated_at: "2026-09-27T00:00:00Z",
    volatility: { stable: 30, slow: 6, volatile: 2 },
    staleness: { evaluable: 38, not_evaluable: 0 },
  },
  okc_council_minutes: {
    source_id: "okc_council_minutes",
    cadence_rule: "weekly",
    cadence_basis: "ops/cadence.toml",
    cadence_state: "enabled",
    scheduled: true,
    one_time_load: false,
    freshness_state: "on_time",
    run_record_missing: false,
    evaluated_at: "2026-09-27T00:00:00Z",
    volatility: { stable: 4 },
    staleness: { evaluable: 4, not_evaluable: 0 },
  },
  demo_permitted_portal: {
    source_id: "demo_permitted_portal",
    cadence_rule: "monthly",
    cadence_basis: "ops/cadence.toml",
    cadence_state: "enabled",
    scheduled: true,
    one_time_load: false,
    freshness_state: "never_run",
    run_record_missing: false,
    evaluated_at: "2026-09-27T00:00:00Z",
    volatility: null,
    staleness: null,
  },
};

// ---------------------------------------------------------------------------
// The data seam (fixtures | export).
// ---------------------------------------------------------------------------

function fixturePageIds(): string[] {
  return SOURCE_ROWS_DOC_FIXTURE.sources.map((r) => r.source_id).sort();
}

function exportPageIds(): string[] {
  const path = `${exportDir()}/transparency/sources.json`;
  if (!existsSync(path)) return [];
  const parsed: unknown = JSON.parse(readFileSync(path, "utf-8"));
  if (!isSourceRowsDoc(parsed)) {
    throw new Error(`${path}: not a valid sig.source-row/1 document`);
  }
  return parsed.sources.map((s) => s.source_id).sort();
}

/** The `/sources/<id>/` routes this build emits (fixture universe or the
 *  release's sources.json universe). Retired ids resolve through the alias
 *  table first (P34.18 — a handle can never reach a page). */
export function getSourcePageIds(): string[] {
  if (dataSource() === "export") return exportPageIds();
  return fixturePageIds();
}

function exportRow(sourceId: string): SourcePageRow | null {
  const path = `${exportDir()}/transparency/sources.json`;
  if (!existsSync(path)) return null;
  const parsed: unknown = JSON.parse(readFileSync(path, "utf-8"));
  if (!isSourceRowsDoc(parsed)) {
    throw new Error(`${path}: not a valid sig.source-row/1 document`);
  }
  for (const raw of parsed.sources as unknown[]) {
    const o = raw as { source_id?: unknown };
    if (typeof o.source_id === "string" && resolveSourceId(o.source_id) === sourceId) {
      if (!isSourcePageRow(raw)) {
        throw new Error(`${path}: row ${sourceId} is not a renderable sig.source-row/1`);
      }
      return raw;
    }
  }
  return null;
}

function readJsonl(path: string): unknown[] {
  return readFileSync(path, "utf-8")
    .split("\n")
    .map((l) => l.trim())
    .filter(Boolean)
    .map((l) => JSON.parse(l) as unknown);
}

function exportExecutions(sourceId: string): ExecutionRecord[] | null {
  const path = `${exportDir()}/transparency/sources/${sourceId}/executions.jsonl`;
  if (!existsSync(path)) return null;
  const rows = readJsonl(path);
  for (const r of rows) {
    if (!isExecutionRecord(r)) {
      throw new Error(`${path}: a row is not a valid ${EXECUTION_RECORD_SCHEMA}`);
    }
  }
  return rows as ExecutionRecord[];
}

function exportFreshness(sourceId: string): SourceFreshness | null {
  const path = `${exportDir()}/transparency/freshness.jsonl`;
  if (!existsSync(path)) return null;
  for (const raw of readJsonl(path)) {
    const o = raw as SourceFreshness;
    if (o && typeof o.source_id === "string" && o.source_id === sourceId) return o;
  }
  return null;
}

/** S-11: the row is the registry-only record — gated/refused/withdrawn or
 *  an unknown/restricted lane (the emitter's own precedence). */
export function isRegistryOnly(row: SourcePageRow): boolean {
  return isRegistryOnlyShape(row);
}

/** The page model for one source — `null` when no row names the id. */
export function getSourcePage(sourceId: string): SourcePageModel | null {
  if (dataSource() === "export") {
    const row = exportRow(sourceId);
    if (!row) return null;
    return {
      row,
      extras: NO_EXTRAS,
      executions: exportExecutions(sourceId),
      freshness: exportFreshness(sourceId),
      registryOnly: isRegistryOnly(row),
    };
  }
  const row = fixturePageRow(sourceId);
  if (!row) return null;
  return {
    row,
    extras: SOURCE_PAGE_EXTRAS_FIXTURE[sourceId] ?? NO_EXTRAS,
    executions: SOURCE_EXECUTIONS_FIXTURE[sourceId] ?? null,
    freshness: SOURCE_FRESHNESS_FIXTURE[sourceId] ?? null,
    registryOnly: isRegistryOnly(row),
  };
}

/** The terms-disclosure block for this source when it is an ADR-183
 *  express-terms source (the captured-terms record — date + evidence). */
export function sourceTermsDisclosure(sourceId: string) {
  const d = getTermsDisclosure();
  return d.sources.find((s) => s.source_id === sourceId) ?? null;
}

// ---------------------------------------------------------------------------
// Derivations — conduct, cadence, coverage class, the strip spec.
// ---------------------------------------------------------------------------

export interface ConductSummary {
  /** host → outcome → count, aggregated over all recorded executions. */
  robotsByHost: { host: string; outcomes: Record<string, number>; decisionRef: string | null }[];
  /** refusal/rejection reason class → count. */
  refusals: Record<string, number>;
  rateLimitEvents: number;
  quotaReached: number;
  budgetReached: number;
  totalExecutions: number;
  /** Latest execution's robots outcomes (the "latest run" column). */
  latestRobots: { host: string; outcomes: Record<string, number>; decisionRef: string | null }[];
}

const ROBOTS_OUTCOMES = ["obeyed", "disallowed", "unavailable", "disregarded"] as const;

function aggregateRobots(executions: readonly ExecutionRecord[]): ConductSummary["robotsByHost"] {
  const byHost = new Map<string, { outcomes: Record<string, number>; decisionRef: string | null }>();
  for (const e of executions) {
    for (const r of e.robots ?? []) {
      let slot = byHost.get(r.host);
      if (!slot) {
        slot = { outcomes: {}, decisionRef: null };
        byHost.set(r.host, slot);
      }
      slot.outcomes[r.outcome] = (slot.outcomes[r.outcome] ?? 0) + (r.count ?? 0);
      if (r.decision_ref) slot.decisionRef = r.decision_ref;
    }
  }
  return [...byHost.entries()]
    .map(([host, v]) => ({ host, outcomes: v.outcomes, decisionRef: v.decisionRef }))
    .sort((a, b) => a.host.localeCompare(b.host));
}

/** SIG-TRANSP-039: conduct rendered from OBSERVED run records only — never
 *  the registry's declared robots posture. */
export function conductSummary(executions: readonly ExecutionRecord[] | null): ConductSummary | null {
  if (!executions || executions.length === 0) return null;
  const sorted = [...executions].sort((a, b) =>
    String(b.finished_at ?? b.started_at ?? "").localeCompare(String(a.finished_at ?? a.started_at ?? "")),
  );
  const refusals: Record<string, number> = {};
  let rateLimitEvents = 0;
  let quotaReached = 0;
  let budgetReached = 0;
  for (const e of executions) {
    for (const [klass, n] of Object.entries(e.rejected ?? {})) {
      refusals[klass] = (refusals[klass] ?? 0) + n;
    }
    rateLimitEvents += e.rate_limit_events ?? 0;
    if (e.quota_reached) quotaReached += 1;
    if (e.budget_reached) budgetReached += 1;
  }
  return {
    robotsByHost: aggregateRobots(executions),
    refusals,
    rateLimitEvents,
    quotaReached,
    budgetReached,
    totalExecutions: executions.length,
    latestRobots: aggregateRobots(sorted.slice(0, 1)),
  };
}

/** Executions that finished ok/partial/quota-reached (the successful set —
 *  same outcome classes the emitter's `_last_successful_run` uses). */
export function successfulExecutions(
  executions: readonly ExecutionRecord[] | null,
): ExecutionRecord[] {
  if (!executions) return [];
  return executions.filter(
    (e) => e.outcome === "ok" || e.outcome === "partial" || e.quota_reached === true,
  );
}

/** Observed cadence — the median interval in whole days of the last five
 *  successful executions (K10 §8); `not_evaluable` under two successes. */
export function observedCadenceDays(executions: readonly ExecutionRecord[] | null): number | null {
  const ok = successfulExecutions(executions)
    .map((e) => e.finished_at ?? e.started_at)
    .filter((t): t is string => typeof t === "string")
    .map((t) => Date.parse(t))
    .filter((t) => Number.isFinite(t))
    .sort((a, b) => a - b);
  if (ok.length < 2) return null;
  const recent = ok.slice(-5);
  const gaps: number[] = [];
  for (let i = 1; i < recent.length; i++) {
    gaps.push((recent[i]! - recent[i - 1]!) / 86_400_000);
  }
  gaps.sort((a, b) => a - b);
  const mid = Math.floor(gaps.length / 2);
  const median = gaps.length % 2 ? gaps[mid]! : (gaps[mid - 1]! + gaps[mid]!) / 2;
  return Math.round(median * 10) / 10;
}

/** SIG-TRANSP-037: a data-bearing source with no execution record. */
export function runRecordMissing(model: SourcePageModel): boolean {
  const dataBearing =
    (typeof model.row.published_claims === "number" && model.row.published_claims > 0) ||
    model.row.published_sites === true ||
    model.row.status_flags.includes("run_record_missing") ||
    model.row.lifecycle_state === "ingested_not_published";
  return dataBearing && (!model.executions || model.executions.length === 0);
}

/** The rights-record coverage class — derived from the recorded row +
 *  extras, never re-decided (K10 §6/E4's vocabulary). */
export function coverageClass(model: SourcePageModel): CoverageClass {
  if (model.extras.coverage_class) return model.extras.coverage_class;
  if (model.registryOnly) {
    return model.row.lifecycle_state === "refused" ? "refused" : "gated";
  }
  const basis = model.row.review.basis.toLowerCase();
  if (basis === "no_decision_recorded") return "registry_only";
  if (model.extras.terms_conflict_excerpt) return "terms_conflict";
  if (model.row.review.reviewer_role.includes("counsel")) return "counsel";
  if (basis.includes("outside") && basis.includes("rule")) return "outside_rule";
  if (basis.includes("delegat") || basis.includes("gl-gate-07")) return "delegated_rule";
  return "per_source_review";
}

/** The `sig.figure-kit-chart/1` strip spec for the runs-over-time figure
 *  (K10 §8; FIG-01b's `strip` kind): one dated marker per recorded
 *  execution — the kit draws it, this module only composes the contract. */
export interface RunsStripSpec {
  schema: "sig.figure-kit-chart/1";
  release: { label: string; publication_id: string; as_of_world: string };
  kind: "strip";
  title: string;
  unit: string;
  categories: unknown[];
  series: unknown[];
  events: { date: string; label: string; href?: string; kind?: string }[];
  width: number;
  narrow_width: number;
}

export function runsStripSpec(
  model: SourcePageModel,
  release: { label: string; publication_id: string; as_of_world: string },
): RunsStripSpec | null {
  const events = (model.executions ?? [])
    .map((e) => {
      const at = e.finished_at ?? e.started_at;
      if (typeof at !== "string" || !Number.isFinite(Date.parse(at))) return null;
      const inserted = typeof e.claims_inserted === "number" ? e.claims_inserted : null;
      return {
        date: at.slice(0, 10),
        label: `${e.outcome}${inserted !== null ? ` — ${inserted} claims inserted` : ""}`,
        kind: e.outcome,
      };
    })
    .filter((e): e is NonNullable<typeof e> => e !== null);
  if (events.length === 0) return null;
  return {
    schema: "sig.figure-kit-chart/1",
    release,
    kind: "strip",
    title: `Recorded runs for ${model.row.name}`,
    unit: "executions",
    categories: [],
    series: [],
    events,
    width: 720,
    narrow_width: 360,
  };
}

/** The release stamp a strip spec repeats (fixtures build — demo-labelled). */
export function fixtureReleaseInfo(): { label: string; publication_id: string; as_of_world: string } {
  return { label: "demo-release", publication_id: "demo-release", as_of_world: AS_OF.as_of_world };
}
