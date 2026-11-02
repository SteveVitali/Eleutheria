// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * P36.49 (TX-06, SIG-TRANSP-010, J3 §7.3) — the issues log's data seam.
 *
 * `transparency/issues.jsonl` carries `sig.source-issue/1` rows in two kinds:
 * `auto` instances detected from run records (P35.33) and `curated` entries
 * from the committed `known_issues.toml` (this row). History is append-only:
 * a resolved issue is a `closed_at` value, never a removed row.
 *
 *   - `fixtures` mode — the committed `ISSUES_FIXTURE` below.
 *   - `export` mode — `<exportDir>/transparency/issues.jsonl` when present
 *     (fail loud on a malformed row); absent → `[]` (honest absence — a
 *     pre-issues export shows "no issues recorded", never a fabricated row).
 *
 * D-J3-12 [B-2] = OD-07 a — carried verbatim: a curated row whose
 * `text_state` is `pending_review` renders class + dates + the interim
 * marker; its drafted text never reaches the artifact.
 */

import { existsSync, readFileSync } from "node:fs";
import { dataSource, exportDir } from "./data";
import { isSourceRowsDoc, SOURCE_ROWS_DOC_FIXTURE } from "./source-counts";

export const ISSUE_RECORD_SCHEMA = "sig.source-issue/1";

export interface SourceIssue {
  schema: typeof ISSUE_RECORD_SCHEMA;
  issue_id: string;
  source_id: string;
  issue_class: string;
  opened_at: string;
  last_seen_at: string | null;
  closed_at: string | null;
  count: number | null;
  basis: string;
  /** "auto" | "curated"; absent on pre-P36.49 artifacts → treated "auto". */
  kind?: string;
  /** Operator-confirmed public text — null while text_state is pending. */
  text?: string | null;
  text_state?: string | null;
  correction_ref?: string | null;
}

export function isIssueRecord(v: unknown): v is SourceIssue {
  const o = v as SourceIssue | null;
  return (
    !!o &&
    o.schema === ISSUE_RECORD_SCHEMA &&
    typeof o.source_id === "string" &&
    typeof o.issue_class === "string" &&
    typeof o.opened_at === "string" &&
    (o.closed_at === null || typeof o.closed_at === "string")
  );
}

// ---------------------------------------------------------------------------
// The committed fixture — synthetic demonstration rows exercising every
// state the surfaces render: auto open + closed, curated pending_review,
// curated confirmed + closed. Demo ids only (§3.1).
// ---------------------------------------------------------------------------

export const ISSUES_FIXTURE: SourceIssue[] = [
  {
    schema: ISSUE_RECORD_SCHEMA,
    issue_id: "issue:demo_ingested_feed:fetch_error:2026-10-13T02:00:00Z",
    source_id: "demo_ingested_feed",
    issue_class: "fetch_error",
    opened_at: "2026-10-13T02:00:00Z",
    last_seen_at: "2026-10-15T02:00:00Z",
    closed_at: null,
    count: 2,
    basis: "run_record",
    kind: "auto",
    text: null,
    text_state: null,
    correction_ref: null,
  },
  {
    schema: ISSUE_RECORD_SCHEMA,
    issue_id: "issue:demo_permitted_portal:never_run:2026-09-27T00:00:00Z",
    source_id: "demo_permitted_portal",
    issue_class: "never_run",
    opened_at: "2026-09-27T00:00:00Z",
    last_seen_at: "2026-10-15T12:00:00Z",
    closed_at: null,
    count: 1,
    basis: "freshness_state",
    kind: "auto",
    text: null,
    text_state: null,
    correction_ref: null,
  },
  {
    schema: ISSUE_RECORD_SCHEMA,
    issue_id: "issue:okc_camera_registry:robots_disallow:2026-09-15T05:00:00Z",
    source_id: "okc_camera_registry",
    issue_class: "robots_disallow",
    opened_at: "2026-09-15T05:00:00Z",
    last_seen_at: "2026-09-15T05:00:00Z",
    closed_at: "2026-10-15T05:12:40Z",
    count: 1,
    basis: "run_record",
    kind: "auto",
    text: null,
    text_state: null,
    correction_ref: null,
  },
  {
    schema: ISSUE_RECORD_SCHEMA,
    issue_id: "ki:okc_camera_registry:axis_swap:2026-09-30",
    source_id: "okc_camera_registry",
    issue_class: "axis_swap",
    opened_at: "2026-09-30T16:48:00Z",
    last_seen_at: "2026-09-30T16:48:00Z",
    closed_at: null,
    count: null,
    basis: "known_issues.toml",
    kind: "curated",
    text: null,
    text_state: "pending_review",
    correction_ref: "sig.geometry-corrections/1",
  },
  {
    schema: ISSUE_RECORD_SCHEMA,
    issue_id: "ki:okc_council_minutes:data_defect:2026-08-01",
    source_id: "okc_council_minutes",
    issue_class: "data_defect",
    opened_at: "2026-08-01T00:00:00Z",
    last_seen_at: "2026-10-01T05:00:00Z",
    closed_at: "2026-10-01T05:00:00Z",
    count: null,
    basis: "known_issues.toml",
    kind: "curated",
    text: "Demonstration entry — an invented defect recorded to exercise the closed row state.",
    text_state: "confirmed",
    correction_ref: "corrections log — demonstration entry",
  },
];

/** The issues log rows this build carries (release artifact or fixture). */
export function getIssues(): SourceIssue[] {
  if (dataSource() !== "export") return ISSUES_FIXTURE;
  const path = `${exportDir()}/transparency/issues.jsonl`;
  if (!existsSync(path)) return [];
  const rows = readFileSync(path, "utf-8")
    .split("\n")
    .map((l) => l.trim())
    .filter(Boolean)
    .map((l) => JSON.parse(l) as unknown);
  for (const r of rows) {
    if (!isIssueRecord(r)) {
      throw new Error(`${path}: a row is not a valid ${ISSUE_RECORD_SCHEMA}`);
    }
  }
  return rows as SourceIssue[];
}

/** One source's issues — open first (newest-opened first), then closed. */
export function issuesForSource(issues: readonly SourceIssue[], sourceId: string): SourceIssue[] {
  const rows = issues.filter((i) => i.source_id === sourceId);
  const open = rows.filter((i) => i.closed_at === null);
  const closed = rows.filter((i) => i.closed_at !== null);
  const byOpened = (a: SourceIssue, b: SourceIssue) => b.opened_at.localeCompare(a.opened_at);
  return [...open.sort(byOpened), ...closed.sort(byOpened)];
}

/** The log grouped by source (source order = first open issue's, then id). */
export function issuesBySource(issues: readonly SourceIssue[]): Map<string, SourceIssue[]> {
  const ids = [...new Set(issues.map((i) => i.source_id))].sort();
  const map = new Map<string, SourceIssue[]>();
  for (const id of ids) map.set(id, issuesForSource(issues, id));
  return map;
}

/** Public labels for the issue classes (auto + curated vocabularies). */
export const ISSUE_CLASS_LABELS: Record<string, string> = {
  robots_disallow: "robots.txt disallow",
  politeness_refusal: "politeness refusal",
  rate_limited: "rate limited",
  quota_reached: "quota reached",
  budget_reached: "budget reached",
  content_drift: "content drift",
  disappearance: "disappearance",
  zero_records: "zero records",
  late: "late",
  overdue: "overdue",
  never_run: "never run",
  scheduler_drift: "scheduler drift",
  capture_not_retained: "capture not retained",
  fetch_error: "fetch error",
  axis_swap: "axis-swapped coordinates",
  null_island: "placeholder (0,0) coordinates",
  sign_flip: "sign-flipped coordinates",
  wrong_jurisdiction: "wrong jurisdiction labels",
  jurisdiction_code_collision: "jurisdiction code collision",
  misattribution: "misattribution",
  terms_conflict: "terms conflict",
  untyped_technology: "untyped technology",
  data_defect: "data defect",
};

export function issueClassLabel(cls: string): string {
  return ISSUE_CLASS_LABELS[cls] ?? cls.replace(/_/g, " ");
}

/** source_id → display name from the release's `sources.json` (or the
 *  fixture rows) — a missing row names the id itself, never a blank. */
export function sourceNameMap(): Map<string, string> {
  const map = new Map<string, string>();
  if (dataSource() === "export") {
    const path = `${exportDir()}/transparency/sources.json`;
    if (existsSync(path)) {
      const parsed: unknown = JSON.parse(readFileSync(path, "utf-8"));
      if (isSourceRowsDoc(parsed)) {
        for (const r of parsed.sources) {
          if (typeof r.name === "string") map.set(r.source_id, r.name);
        }
      }
    }
    return map;
  }
  for (const r of SOURCE_ROWS_DOC_FIXTURE.sources) {
    if (typeof r.name === "string") map.set(r.source_id, r.name);
  }
  return map;
}

/** A row's public sentence — the confirmed text, else the typed marker. */
export function issueText(issue: SourceIssue): string {
  if (issue.kind === "curated" && issue.text_state === "pending_review") {
    return "known-issue text pending review";
  }
  if (typeof issue.text === "string" && issue.text) return issue.text;
  if (issue.kind === "curated") return "known-issue text pending review";
  return `Auto-detected from ${issue.basis ?? "run records"}.`;
}
