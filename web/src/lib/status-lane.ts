// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * P36.43 (TX-07, SIG-TRANSP-021/034, K9 C-12): the status lane's
 * `sig.status-lane/1` document — the second clock. The lane job
 * (`sig-status-publish`, 6 h) emits `status/lane.json` + `state.json`; this
 * layer reads it so the web build's release copy of `/status/` +
 * `/status/sources/` renders the same document the live lane overwrites.
 *
 *   - `fixtures` mode — the committed `STATUS_LANE_FIXTURE` below.
 *   - `export` mode — `<exportDir>/status/lane.json` when present (fail loud
 *     on malformed); absent → `null` (honest absence — a pre-lane export
 *     shows the no-status-read state, never a fabricated read).
 *
 * Two clocks (SIG-TRANSP-034): `status_time` labels every lane value; the
 * release's `as_of_world` rides beside it. Gated/refused/withdrawn sources
 * arrive as COUNTS ONLY (D-J3-11) — `sources[]` never carries their ids.
 */

import { existsSync, readFileSync } from "node:fs";
import { dataSource, exportDir } from "./data";

export const STATUS_LANE_SCHEMA = "sig.status-lane/1";
export const STATUS_HEARTBEAT_SCHEMA = "sig.status-heartbeat/1";

export interface StatusRun {
  started_at: string | null;
  finished_at: string | null;
  outcome: string;
}

export interface StatusSourceRow {
  source_id: string;
  name: string;
  lifecycle_state: string;
  last_run: StatusRun | null;
  /** The next scheduled day — day granularity only (J3 §14 R-6). */
  next_run_day: string;
  freshness: { state: string; evaluated_at: string; run_record_missing: boolean };
  runs_7d: { total: number; by_outcome: Record<string, number> };
  errors: { failed_7d: number; failed_30d: number; error_classes: Record<string, number> };
  claims_7d: { inserted: number; duplicate: number; rejected: number };
  issue_classes: string[];
}

export interface StatusLaneDoc {
  schema: typeof STATUS_LANE_SCHEMA;
  status_time: string;
  release: { id: string; as_of_world: string } | null;
  runs: { last_24h: Record<string, number>; last_7d: Record<string, number> };
  sources_by_freshness: Record<string, number>;
  counts: { listed: number; gated: number; refused: number; withdrawn: number };
  sources: StatusSourceRow[];
  issues: {
    classes: Record<string, number>;
    per_source: Record<string, string[]>;
    /** P36.49 (TX-06): curated sig.source-issue/1 rows for listed sources. */
    curated?: unknown[];
  };
  robots_disregard: { hosts: number; events: number; decision_ref: string };
  scheduler_drift: {
    state: "ok" | "drift" | "not_evaluated";
    findings: number | null;
    classes: string[];
    report_time: string | null;
  };
}

export function isStatusLaneDoc(v: unknown): v is StatusLaneDoc {
  const o = v as StatusLaneDoc | null;
  return (
    !!o &&
    o.schema === STATUS_LANE_SCHEMA &&
    typeof o.status_time === "string" &&
    Array.isArray(o.sources) &&
    o.sources.every((s) => typeof s?.source_id === "string") &&
    typeof o.counts?.listed === "number" &&
    typeof o.counts?.gated === "number" &&
    typeof o.counts?.refused === "number" &&
    typeof o.counts?.withdrawn === "number" &&
    ["ok", "drift", "not_evaluated"].includes(o.scheduler_drift?.state as string)
  );
}

/** The committed fixture lane document — consistent with the source-row
 * fixture (`SOURCE_ROWS_FIXTURE` ids): the two gated/refused rows arrive as
 * counts only, never names. */
export const STATUS_LANE_FIXTURE: StatusLaneDoc = {
  schema: STATUS_LANE_SCHEMA,
  status_time: "2026-10-15T12:00:00Z",
  release: { id: "demo-release", as_of_world: "2026-09-27" },
  runs: {
    last_24h: { ok: 2, partial: 0, quota_reached: 0, failed: 1 },
    last_7d: { ok: 6, partial: 1, quota_reached: 0, failed: 1 },
  },
  sources_by_freshness: { on_time: 3, never_run: 1, one_time_load: 1 },
  counts: { listed: 5, gated: 1, refused: 1, withdrawn: 0 },
  sources: [
    {
      source_id: "okc_camera_registry",
      name: "OKC camera registry",
      lifecycle_state: "published",
      last_run: {
        started_at: "2026-10-15T05:00:00Z",
        finished_at: "2026-10-15T05:12:40Z",
        outcome: "ok",
      },
      next_run_day: "2026-11-07", // future-ok: synthetic: lane fixture cadence
      freshness: { state: "on_time", evaluated_at: "2026-10-15T12:00:00Z", run_record_missing: false },
      runs_7d: { total: 1, by_outcome: { ok: 1, partial: 0, quota_reached: 0, failed: 0 } },
      errors: { failed_7d: 0, failed_30d: 0, error_classes: {} },
      claims_7d: { inserted: 12, duplicate: 3, rejected: 0 },
      issue_classes: [],
    },
    {
      source_id: "okc_council_minutes",
      name: "OKC council minutes",
      lifecycle_state: "published",
      last_run: {
        started_at: "2026-10-13T05:00:00Z",
        finished_at: "2026-10-13T05:03:11Z",
        outcome: "ok",
      },
      next_run_day: "2026-11-01", // future-ok: synthetic: lane fixture cadence
      freshness: { state: "on_time", evaluated_at: "2026-10-15T12:00:00Z", run_record_missing: false },
      runs_7d: { total: 1, by_outcome: { ok: 1, partial: 0, quota_reached: 0, failed: 0 } },
      errors: { failed_7d: 0, failed_30d: 0, error_classes: {} },
      claims_7d: { inserted: 4, duplicate: 0, rejected: 1 },
      issue_classes: [],
    },
    {
      source_id: "demo_ingested_feed",
      name: "Demo ingested feed",
      lifecycle_state: "ingested_not_published",
      last_run: {
        started_at: "2026-10-15T02:00:00Z",
        finished_at: "2026-10-15T02:01:02Z",
        outcome: "failed",
      },
      next_run_day: "2026-10-22",
      freshness: { state: "last_run_failed", evaluated_at: "2026-10-15T12:00:00Z", run_record_missing: false },
      runs_7d: { total: 2, by_outcome: { ok: 1, partial: 0, quota_reached: 0, failed: 1 } },
      errors: { failed_7d: 1, failed_30d: 1, error_classes: { fetch_error: 1 } },
      claims_7d: { inserted: 0, duplicate: 0, rejected: 0 },
      issue_classes: ["fetch_error"],
    },
    {
      source_id: "demo_seed_load",
      name: "Demo one-time seed",
      lifecycle_state: "permitted_not_ingested",
      last_run: null,
      next_run_day: "not_scheduled",
      freshness: { state: "one_time_load", evaluated_at: "2026-10-15T12:00:00Z", run_record_missing: false },
      runs_7d: { total: 0, by_outcome: { ok: 0, partial: 0, quota_reached: 0, failed: 0 } },
      errors: { failed_7d: 0, failed_30d: 0, error_classes: {} },
      claims_7d: { inserted: 0, duplicate: 0, rejected: 0 },
      issue_classes: [],
    },
    {
      source_id: "demo_permitted_portal",
      name: "Demo permitted portal",
      lifecycle_state: "permitted_not_ingested",
      last_run: null,
      next_run_day: "2026-10-20",
      freshness: { state: "never_run", evaluated_at: "2026-10-15T12:00:00Z", run_record_missing: false },
      runs_7d: { total: 0, by_outcome: { ok: 0, partial: 0, quota_reached: 0, failed: 0 } },
      errors: { failed_7d: 0, failed_30d: 0, error_classes: {} },
      claims_7d: { inserted: 0, duplicate: 0, rejected: 0 },
      issue_classes: ["never_run"],
    },
  ],
  issues: {
    classes: { fetch_error: 1, never_run: 1 },
    per_source: { demo_ingested_feed: ["fetch_error"], demo_permitted_portal: ["never_run"] },
  },
  robots_disregard: { hosts: 1, events: 3, decision_ref: "GL-GATE-08" },
  scheduler_drift: { state: "ok", findings: 0, classes: [], report_time: "2026-10-15T10:00:00Z" },
};

/** The status lane document, or `null` when this build carries none. */
export function getStatusLane(): StatusLaneDoc | null {
  if (dataSource() !== "export") return STATUS_LANE_FIXTURE;
  const path = `${exportDir()}/status/lane.json`;
  if (!existsSync(path)) return null;
  const parsed: unknown = JSON.parse(readFileSync(path, "utf-8"));
  if (!isStatusLaneDoc(parsed)) {
    throw new Error(`${path}: not a valid ${STATUS_LANE_SCHEMA} artifact`);
  }
  return parsed;
}

/** Outcome counts rendered as `ok 3 · failed 1` (empty → none recorded). */
export function outcomeCells(counts: Record<string, number>): string {
  const parts = Object.entries(counts)
    .filter(([, n]) => n > 0)
    .map(([k, n]) => `${k} ${n}`);
  return parts.length ? parts.join(" · ") : "none recorded";
}

// ---------------------------------------------------------------------------
// P36.48 (K9 C-12): the lane row → the shared sources-table row shape. The
// lane carries what the status clock records — last run, next run day, the
// current verdict, seven-day run/outcome and error splits; cells the lane
// does not record (upstream change, SIG-records change, the declared
// cadence rule) render their named absence, never a fabricated value.
// ---------------------------------------------------------------------------

import type { TableRow } from "./sources-table";

export function statusRowToTableRow(s: StatusSourceRow): TableRow {
  return {
    sourceId: s.source_id,
    name: s.name,
    publisher: "publisher_not_recorded",
    publisherType: "not_recorded",
    classes: null,
    geography: null,
    country: "unresolved",
    subdivision: "unresolved",
    licenceSpdx: null,
    licenceAttribution: null,
    termsUrl: null,
    homepage: null,
    homepageHost: null,
    derivedStatus: "not_published",
    lane: "unknown",
    laneBasis: null,
    lifecycle: s.lifecycle_state as TableRow["lifecycle"],
    flags: [],
    lastRun: s.last_run?.finished_at ?? s.last_run?.started_at ?? null,
    lastRunToken: s.last_run === null ? "never_run" : null,
    upstreamChange: null,
    sigChange: null,
    cadenceRule: null,
    cadenceBasis: null,
    freshnessState: s.freshness.state,
    freshnessEvaluatedAt: s.freshness.evaluated_at,
    runRecordMissing: s.freshness.run_record_missing,
    volatilityDominant: null,
    staleness: null,
    publishedClaims: null,
    publishedSites: false,
    runsTotal: s.runs_7d.total,
    runsByOutcome: { ...s.runs_7d.by_outcome },
    failedRecent: s.errors.failed_30d,
    openIssue: s.issue_classes.length > 0,
    downloadToken: "not_published",
    registryOnly: false,
  };
}
