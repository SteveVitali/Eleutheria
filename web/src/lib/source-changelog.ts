// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * P37.41 (R11-K13-UX10-4 / K10 UX10-4 §15; §56.10 SIG-TRANSP-042, J5) — the
 * per-source changelog: an append-only event log generated from records
 * with trustworthy clocks — never from git commit dates (K10 §15: the
 * build contains past-dated commits, so a VCS date never dates an event).
 *
 * The emitted shape is `sig.source-changelog/1`:
 * `{event_id, source_id, kind, at, clock_basis, summary_code, refs[]}` —
 * summaries render from a closed code vocabulary, never free text. Every
 * event's `at` is dated by the record's own clock and `clock_basis` names
 * which clock that was (the §56.10 requirement's acceptance shape).
 *
 * Event seams (all release-pinned artifacts, never a live read):
 *
 *   - `transparency/sources.json` — the `sig.source-row/1` rights-review
 *     record (`review.decided_at`) → `rights_decision`.
 *   - `transparency/sources/<id>/executions.jsonl` — `sig.execution-record/1`
 *     → `first_ingest` (earliest successful completion, `finished_at`) and
 *     `connector_version` (the first execution carrying a new version,
 *     `finished_at`).
 *   - `transparency/sources/<id>/versions.json` — `sig.source-versions/1`
 *     → `first_publication` (the earliest release entry, release
 *     activation) and the baseline label.
 *   - `r/<pub>/transparency/changes/{index,sources,changes}.json` — the
 *     TX-14 diff set (P36.67) read through P37.40's `getReleaseChanges`:
 *     the source-lifecycle rows (`added`/`retired`/`newly_failing`/
 *     `lane_changed`) and the per-source slice of the record diff (feed
 *     events whose `source_ids` name this source), dated by release
 *     activation.
 *   - `transparency/issues.jsonl` — `sig.source-issue/1` (P36.49) →
 *     `issue_opened`/`issue_closed` on the row's own opened/closed clocks.
 *   - `web/corrections.json` — a `source:<id>`-keyed correction entry →
 *     `correction` on its `corrected_at`; `web/attribution_corrections.json`
 *     → `attribution_correction` on its `decided_at`.
 *   - `policy`'s `sig.publication-withdrawals/1` table → `record_withdrawn`
 *     on each entry's own `recorded_at`.
 *
 * Baseline (K10 §15): the first activated release is the baseline — the
 * page states "History before <label>: rights decisions and run records
 * only." A registry-only (S-11) source emits no changelog at all — it
 * publishes nothing but its registry record.
 */

import {
  getCorrections,
  getAttributionCorrections,
  getReleaseChanges,
} from "./data";
import { getIssues, issueClassLabel } from "./issues";
import {
  getSourcePage,
  isRegistryOnly,
  successfulExecutions,
  type ExecutionRecord,
  type SourcePageRow,
} from "./source-page";
import { getPageBIds, getSourceVersions, type SourceVersionsDoc } from "./source-page-b";
import { withdrawalEntries, type WithdrawalEntry } from "./withdrawals";
import type { ReleaseChangesDoc } from "./changes";
import type { SourceIssue } from "./issues";
import type { CorrectionEntry } from "./corrections";
import type { AttributionCorrection } from "./data";

// ---------------------------------------------------------------------------
// sig.source-changelog/1 — the contract (K10 §15/§16.1).
// ---------------------------------------------------------------------------

export const SOURCE_CHANGELOG_SCHEMA = "sig.source-changelog/1";

/** The closed clock vocabulary — every event names which record clock dated
 *  it; `git`/`vcs` is never a member (SIG-TRANSP-042). */
export const CLOCK_BASES = [
  "decided_at",
  "finished_at",
  "activation",
  "opened_at",
  "closed_at",
  "corrected_at",
  "recorded_at",
] as const;
export type ClockBasis = (typeof CLOCK_BASES)[number];

/** The closed kind vocabulary (K10 §15's event table). */
export const CHANGELOG_KINDS = [
  "rights_decision",
  "first_ingest",
  "first_publication",
  "source_added",
  "source_retired",
  "source_newly_failing",
  "lane_changed",
  "records_added",
  "records_removed",
  "records_changed",
  "connector_version",
  "issue_opened",
  "issue_closed",
  "correction",
  "attribution_correction",
  "record_withdrawn",
] as const;
export type ChangelogKind = (typeof CHANGELOG_KINDS)[number];

export interface SourceChangelogEvent {
  event_id: string;
  source_id: string;
  kind: ChangelogKind;
  /** The record-clock instant/date the event is dated by — never a
   *  version-control date. */
  at: string;
  clock_basis: ClockBasis;
  /** The closed summary vocabulary token the sentence renders from. */
  summary_code: string;
  refs: string[];
  /** Structured extras the summary renders (lane moves, counts, classes) —
   *  additive to the K10 wire shape; a pre-P37.41 doc simply omits it. */
  detail?: Record<string, string | number | null>;
}

export interface SourceChangelogDoc {
  schema: typeof SOURCE_CHANGELOG_SCHEMA;
  source_id: string;
  name: string;
  /** The first activated release's label — the history baseline (K10 §15);
   *  null when no release entry can name one (the page renders the
   *  unlabelled baseline sentence, never a guessed label). */
  baseline_label: string | null;
  event_count: number;
  events: SourceChangelogEvent[];
  disclosures: string[];
}

/** Fail-closed event validation — a malformed emitted doc throws, never
 *  renders (the reader never coerces). */
export function isChangelogEvent(v: unknown): v is SourceChangelogEvent {
  const o = v as SourceChangelogEvent | null;
  return (
    !!o &&
    typeof o.event_id === "string" &&
    typeof o.source_id === "string" &&
    (CHANGELOG_KINDS as readonly string[]).includes(o.kind) &&
    typeof o.at === "string" &&
    (CLOCK_BASES as readonly string[]).includes(o.clock_basis) &&
    typeof o.summary_code === "string" &&
    Array.isArray(o.refs)
  );
}

export function isChangelogDoc(v: unknown): v is SourceChangelogDoc {
  const o = v as SourceChangelogDoc | null;
  return (
    !!o &&
    o.schema === SOURCE_CHANGELOG_SCHEMA &&
    typeof o.source_id === "string" &&
    Array.isArray(o.events) &&
    o.events.every(isChangelogEvent)
  );
}

// ---------------------------------------------------------------------------
// The event generator — one pure pass over the named seams.
// ---------------------------------------------------------------------------

export interface ChangelogInputs {
  row: SourcePageRow;
  executions: readonly ExecutionRecord[] | null;
  versions: SourceVersionsDoc | null;
  /** The TX-14 release-diff set — `null` when no release is bound (the
   *  honest interim) or the release predates the changes tree. */
  changes: ReleaseChangesDoc | null;
  issues: readonly SourceIssue[];
  corrections: readonly CorrectionEntry[];
  attribution: readonly AttributionCorrection[];
  withdrawals: readonly WithdrawalEntry[];
}

const executionTime = (e: ExecutionRecord): string | null => e.finished_at ?? e.started_at;

/** The earliest successful completion (K10 §15: first ingest, `finished_at`). */
function firstCompletion(executions: readonly ExecutionRecord[]): ExecutionRecord | null {
  const ok = successfulExecutions(executions)
    .filter((e) => executionTime(e) !== null)
    .sort((a, b) => String(executionTime(a)).localeCompare(String(executionTime(b))));
  return ok[0] ?? null;
}

/** Connector-version transitions — one event per new version, dated by the
 *  first execution recorded under it (K10 §15). */
function connectorVersionEvents(
  executions: readonly ExecutionRecord[],
  mint: Mint,
): void {
  const sorted = [...executions]
    .filter((e) => executionTime(e) !== null)
    .sort((a, b) => String(executionTime(a)).localeCompare(String(executionTime(b))));
  let prev: string | null = null;
  for (const e of sorted) {
    const v = e.connector_version;
    if (v === null || v === undefined || v === prev) {
      if (prev === null && v) prev = v;
      continue;
    }
    if (prev !== null && v !== prev) {
      mint({
        kind: "connector_version",
        at: executionTime(e) as string,
        clock_basis: "finished_at",
        summary_code: "connector.version_change",
        refs: [e.execution_id],
        detail: { previous: prev, current: v, connector: e.connector_name },
      });
    }
    prev = v;
  }
}

interface MintSeed {
  kind: ChangelogKind;
  at: string;
  clock_basis: ClockBasis;
  summary_code: string;
  refs: string[];
  detail?: Record<string, string | number | null>;
}

type Mint = (seed: MintSeed) => void;

/** The release-activation date the TX-14 docs date events by (world pin —
 *  the same clock P37.40's /changes/ rows use). */
function activationAt(changes: ReleaseChangesDoc): string {
  return (
    changes.index.release.as_of_world ??
    changes.index.release.as_of_belief ??
    "not recorded"
  );
}

/** The earliest versions entry — chronological by the entry's own release
 *  dates (entries arrive in doc order; the earliest is the baseline). */
function earliestEntry(versions: SourceVersionsDoc) {
  const dated = (e: SourceVersionsDoc["entries"][number]) =>
    e.release.as_of_world ?? e.release.as_of_belief ?? "9999";
  return [...versions.entries].sort((a, b) => dated(a).localeCompare(dated(b)))[0] ?? null;
}

/**
 * The per-source event list — ascending by record clock. Every seam an
 * artifact does not carry simply contributes nothing (the honest absence);
 * nothing is dated from version control.
 */
export function buildSourceChangelog(input: ChangelogInputs): SourceChangelogEvent[] {
  const { row, executions, versions, changes, issues, corrections, attribution, withdrawals } = input;
  const sid = row.source_id;
  const events: SourceChangelogEvent[] = [];
  const mint: Mint = (seed) => {
    events.push({
      event_id: `${sid}:${seed.kind}:${seed.at}`.replace(/[^A-Za-z0-9:_.-]+/g, "-"),
      source_id: sid,
      kind: seed.kind,
      at: seed.at,
      clock_basis: seed.clock_basis,
      summary_code: seed.summary_code,
      refs: seed.refs,
      ...(seed.detail ? { detail: seed.detail } : {}),
    });
  };

  // --- rights_decision (the sources.json rights-review record) ------------ //
  if (row.review?.decided_at) {
    mint({
      kind: "rights_decision",
      at: row.review.decided_at,
      clock_basis: "decided_at",
      summary_code: "rights.decision",
      refs: [sid],
      detail: { basis: row.review.basis, lane: row.lane },
    });
  }

  // --- completions: first ingest + connector version ---------------------- //
  if (executions && executions.length > 0) {
    const first = firstCompletion(executions);
    if (first) {
      mint({
        kind: "first_ingest",
        at: executionTime(first) as string,
        clock_basis: "finished_at",
        summary_code: "ingest.first",
        refs: [first.execution_id],
      });
    }
    connectorVersionEvents(executions, mint);
  }

  // --- release catalog: first publication (the earliest versions entry) --- //
  const earliest = versions ? earliestEntry(versions) : null;
  if (earliest) {
    const at = earliest.release.as_of_world ?? earliest.release.as_of_belief;
    if (at) {
      mint({
        kind: "first_publication",
        at,
        clock_basis: "activation",
        summary_code: "release.first",
        refs: [earliest.release.publication_id ?? earliest.release.label ?? sid],
        detail: { release: earliest.release.label ?? null, state: earliest.state },
      });
    }
  }

  // --- release diffs (TX-14): lifecycle rows + the record-diff slice ------ //
  if (changes) {
    const world = activationAt(changes);
    const label = changes.index.release.label ?? changes.index.release.publication_id;
    const sc = changes.sources;
    if (sc && sc.state === "evaluated") {
      if (sc.added.some((r) => r.source_id === sid)) {
        mint({
          kind: "source_added",
          at: world,
          clock_basis: "activation",
          summary_code: "lifecycle.added",
          refs: [changes.index.release.publication_id],
          detail: { release: label },
        });
      }
      const retired = sc.retired.find((r) => r.source_id === sid);
      if (retired) {
        mint({
          kind: "source_retired",
          at: world,
          clock_basis: "activation",
          summary_code: "lifecycle.retired",
          refs: [changes.index.release.publication_id],
          detail: { release: label, state: retired.lifecycle_state ?? null },
        });
      }
      const failing = sc.newly_failing.find((r) => r.source_id === sid);
      if (failing) {
        mint({
          kind: "source_newly_failing",
          at: world,
          clock_basis: "activation",
          summary_code: "lifecycle.newly_failing",
          refs: [changes.index.release.publication_id],
          detail: { release: label, state: failing.lifecycle_state ?? null },
        });
      }
      const lane = sc.lane_changed.find((r) => r.source_id === sid);
      if (lane) {
        mint({
          kind: "lane_changed",
          at: world,
          clock_basis: "activation",
          summary_code: "registry.lane_change",
          refs: [changes.index.release.publication_id],
          detail: {
            release: label,
            previous_lane: lane.previous_lane ?? null,
            lane: lane.lane ?? null,
          },
        });
      }
    }
    // The per-source slice of TX-14's record diff (P37.40's source_ids
    // routing): one event per change kind, dated by release activation.
    if (changes.feed) {
      const mine = changes.feed.events.filter((e) => (e.source_ids ?? []).includes(sid));
      const byKind = new Map<string, string[]>();
      for (const e of mine) {
        const list = byKind.get(e.change_type) ?? [];
        list.push(e.artifact_id);
        byKind.set(e.change_type, list);
      }
      for (const [changeType, ids] of [...byKind.entries()].sort()) {
        const kind =
          changeType === "added"
            ? "records_added"
            : changeType === "removed"
              ? "records_removed"
              : "records_changed";
        mint({
          kind: kind as ChangelogKind,
          at: world,
          clock_basis: "activation",
          summary_code: `records.${changeType}`,
          refs: ids.sort(),
          detail: { release: label, count: ids.length },
        });
      }
    }
  }

  // --- issues (the append-only sig.source-issue/1 log) -------------------- //
  for (const issue of issues) {
    if (issue.source_id !== sid) continue;
    mint({
      kind: "issue_opened",
      at: issue.opened_at,
      clock_basis: "opened_at",
      summary_code: "issue.opened",
      refs: [issue.issue_id],
      detail: { issue_class: issue.issue_class, issue_kind: issue.kind ?? "auto" },
    });
    if (issue.closed_at) {
      mint({
        kind: "issue_closed",
        at: issue.closed_at,
        clock_basis: "closed_at",
        summary_code: "issue.closed",
        refs: [issue.issue_id],
        detail: { issue_class: issue.issue_class, issue_kind: issue.kind ?? "auto" },
      });
    }
  }

  // --- corrections affecting the source ---------------------------------- //
  for (const c of corrections) {
    if (c.subject_id !== `source:${sid}`) continue;
    mint({
      kind: "correction",
      at: c.corrected_at,
      clock_basis: "corrected_at",
      summary_code: "correction.recorded",
      refs: [c.id],
      detail: { outcome: c.outcome },
    });
  }
  for (const c of attribution) {
    if (c.source_id !== sid) continue;
    mint({
      kind: "attribution_correction",
      at: c.decided_at,
      clock_basis: "decided_at",
      summary_code: "correction.attribution",
      refs: [sid],
    });
  }

  // --- withdrawals (the publication-withdrawals table's own dates) -------- //
  for (const w of withdrawals) {
    if (w.source_id !== sid || !w.recorded_at) continue;
    mint({
      kind: "record_withdrawn",
      at: w.recorded_at,
      clock_basis: "recorded_at",
      summary_code: "withdrawal.record",
      refs: [w.upstream_id || w.entity_id],
      detail: { reason: w.reason },
    });
  }

  // Ascending record-clock order; collisions break on kind then ref so the
  // emitted order is deterministic.
  events.sort(
    (a, b) =>
      Date.parse(a.at) - Date.parse(b.at) ||
      a.kind.localeCompare(b.kind) ||
      a.event_id.localeCompare(b.event_id),
  );
  // De-duplicate event ids deterministically (two events may share
  // kind + instant — a #2 suffix keeps every id unique).
  const seen = new Map<string, number>();
  for (const e of events) {
    const n = (seen.get(e.event_id) ?? 0) + 1;
    seen.set(e.event_id, n);
    if (n > 1) e.event_id = `${e.event_id}#${n}`;
  }
  return events;
}

/** The baseline label — the first activated release the source appears in
 *  (K10 §15): the earliest versions entry, else the release the lifecycle
 *  diff records it added in, else null. */
export function baselineLabel(input: ChangelogInputs): string | null {
  const earliest = input.versions ? earliestEntry(input.versions) : null;
  if (earliest) return earliest.release.label ?? earliest.release.publication_id ?? null;
  const sc = input.changes?.sources;
  if (sc?.state === "evaluated" && sc.added.some((r) => r.source_id === input.row.source_id)) {
    return input.changes?.index.release.label ?? input.changes?.index.release.publication_id ?? null;
  }
  return null;
}

/** The baseline sentence (K10 §15's agent-drafted wording). */
export function baselineSentence(label: string | null): string {
  return label !== null
    ? `History before ${label}: rights decisions and run records only.`
    : "History before the first activated release: rights decisions and run records only.";
}

// ---------------------------------------------------------------------------
// The assembled document + the data seam.
// ---------------------------------------------------------------------------

export const CHANGELOG_DISCLOSURES = [
  "Every event is dated by the record's own clock — the basis column names which one; no date comes from version control.",
  "Summaries render from a closed code vocabulary; the machine twin carries the same events.",
];

/** The assembled `sig.source-changelog/1` document for one source. */
export function getSourceChangelog(sourceId: string): SourceChangelogDoc | null {
  const model = getSourcePage(sourceId);
  if (model === null || model.registryOnly || isRegistryOnly(model.row)) return null;
  const changes = getReleaseChanges();
  const inputs: ChangelogInputs = {
    row: model.row,
    executions: model.executions,
    versions: getSourceVersions(sourceId),
    changes,
    issues: getIssues().filter((i) => i.source_id === sourceId),
    corrections: getCorrections(),
    attribution: getAttributionCorrections()?.corrections ?? [],
    withdrawals: withdrawalEntries(),
  };
  const events = buildSourceChangelog(inputs);
  return {
    schema: SOURCE_CHANGELOG_SCHEMA,
    source_id: sourceId,
    name: model.row.name,
    baseline_label: baselineLabel(inputs),
    event_count: events.length,
    events,
    disclosures: CHANGELOG_DISCLOSURES,
  };
}

/** The sources a changelog route emits for — every non-registry source
 *  (the route exists even for a zero-event source: it renders the typed
 *  absence + the baseline note, never a dead route and never a 404 on a
 *  page the source page links). S-11 registry-only sources emit none. */
export function getSourceChangelogIds(): string[] {
  return getPageBIds();
}

// ---------------------------------------------------------------------------
// The rendered summary — from codes, never free text (K10 §15).
// ---------------------------------------------------------------------------

/** The plain-language fragment a summary_code renders to. Row-level words,
 *  a closed vocabulary like the issues/change-kind tables. */
export function eventSummary(ev: SourceChangelogEvent): string {
  const d = ev.detail ?? {};
  switch (ev.summary_code) {
    case "rights.decision":
      return `rights decision recorded — ${d.basis ?? "basis not recorded"}`;
    case "ingest.first":
      return "first recorded ingest";
    case "release.first":
      return `first published release${d.release ? ` — ${d.release}` : ""}`;
    case "lifecycle.added":
      return "entered the published source universe";
    case "lifecycle.retired":
      return `left the published source universe${d.state ? ` (${d.state})` : ""}`;
    case "lifecycle.newly_failing":
      return `recorded newly failing${d.state ? ` (${d.state})` : ""}`;
    case "registry.lane_change":
      return `lane moved ${d.previous_lane ?? "?"} → ${d.lane ?? "?"} — a recorded lane decision`;
    case "records.added":
      return `${d.count ?? "?"} record(s) added in ${d.release ?? "this release"}`;
    case "records.removed":
      return `${d.count ?? "?"} record(s) removed in ${d.release ?? "this release"}`;
    case "records.changed":
      return `${d.count ?? "?"} record(s) changed in ${d.release ?? "this release"}`;
    case "connector.version_change":
      return `connector version changed — ${d.previous ?? "?"} → ${d.current ?? "?"}`;
    case "issue.opened":
      return `issue opened — ${issueClassLabel(String(d.issue_class ?? ""))} (${d.issue_kind ?? "auto"})`;
    case "issue.closed":
      return `issue closed — ${issueClassLabel(String(d.issue_class ?? ""))}`;
    case "correction.recorded":
      return `a correction affecting this source was recorded (${d.outcome ?? "recorded"})`;
    case "correction.attribution":
      return "an attribution correction was recorded for this source";
    case "withdrawal.record":
      return `a record this source carried was withdrawn from publication${d.reason ? ` (${d.reason})` : ""}`;
    default:
      return ev.summary_code.replace(/[._]/g, " ");
  }
}
