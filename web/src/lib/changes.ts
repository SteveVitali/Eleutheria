// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * P37.40 (R11-K13-CHG-01, J5, K12b I-08/NEW-19, §56.11 SIG-UI-072) — the
 * `/changes/` surface's data contract and the "SIG's records changed" vs
 * "the world changed" classification over TX-14's (P36.67) emitted diffs.
 *
 * The reader validates the release's own manifest-pinned documents —
 * `r/<pub>/transparency/changes/index.json` (`sig.release-changes/1`),
 * `sources.json` (`sig.release-source-changes/1`) and `changes.json`
 * (`sig.release-changes-feed/1`) — fail-closed: a bound-but-malformed doc
 * throws, an absent one is the honest typed absence (a pre-TX-14 release
 * carries no diff).
 *
 * The two classes SIG-UI-072 names:
 *
 *   - **"SIG's records changed"** (belief time) — the record-id diff events
 *     (`added`/`removed`/`changed`), dated by release activation: SIG's
 *     published records now say something different — which may reflect SIG
 *     learning, re-resolution or claim re-minting, disclosed per the
 *     document's own `disclosures` (CONF-03a interim: diff noise is
 *     disclosed as "SIG records changed", never smoothed into a world
 *     claim). Source-lifecycle `added` / `lane_changed` rows join this
 *     class — a registry gain or a lane decision is a change SIG recorded.
 *   - **"the source reports a change in the world"** (world time) — the
 *     upstream-lifecycle events: a source `retired` or `newly_failing`
 *     (it stopped publishing on its own side), and a record `removed`
 *     with reason `source_withdrawn` (every source it carried is absent —
 *     the world withdrew the record's footing). Dated by the world as-of
 *     pair, never by version-control dates.
 *
 * Dating (SIG-UI-072): events carry `old_date`/`new_date` — the two
 * releases' `as_of_world` days; the page additionally names each release's
 * `as_of_belief` (belief time) so the two clocks stay visibly apart.
 */

export const CHANGES_INDEX_SCHEMA = "sig.release-changes/1";
export const SOURCE_CHANGES_SCHEMA = "sig.release-source-changes/1";
export const CHANGES_FEED_SCHEMA = "sig.release-changes-feed/1";

export interface ReleaseBlock {
  label: string | null;
  publication_id: string;
  as_of_world: string | null;
  as_of_belief: string | null;
}

export interface ChangesIndexDoc {
  schema: typeof CHANGES_INDEX_SCHEMA;
  release: ReleaseBlock;
  previous: ReleaseBlock | null;
  baseline: boolean;
  compared_fields: string[];
  excluded_fields: string[];
  compartments: Record<
    string,
    {
      added: number;
      removed: number;
      changed: number;
      records: number;
      previous_records: number;
    }
  >;
  totals: {
    added: number;
    removed: number;
    changed: number;
    records: number;
    previous_records: number;
  };
  versions: Record<string, { previous: unknown; current: unknown }>;
  sources_state?: string;
  disclosures: string[];
  files: string[];
}

export type SourceChangeKind = "added" | "retired" | "newly_failing" | "lane_changed";

export interface SourceChangeRow {
  source_id: string;
  name?: string | null;
  lifecycle_state?: string | null;
  previous_lifecycle_state?: string | null;
  lane?: string | null;
  previous_lane?: string | null;
}

export interface SourceChangesDoc {
  schema: typeof SOURCE_CHANGES_SCHEMA;
  state: "evaluated" | "not_evaluable";
  reason?: string;
  added: SourceChangeRow[];
  retired: SourceChangeRow[];
  newly_failing: SourceChangeRow[];
  lane_changed: SourceChangeRow[];
}

export type ChangeType = "added" | "removed" | "changed";

export interface ChangeEvent {
  artifact_id: string;
  field: string;
  change_type: ChangeType;
  old_value: unknown;
  new_value: unknown;
  old_date: string | null;
  new_date: string | null;
  reason?: string;
  // P37.40's additive routing fields (present on events a TX-14+P37.40
  // release emits; absent on an older doc — the readers tolerate both).
  compartment?: string;
  entity_type?: string | null;
  entity_id?: string | null;
  label?: string | null;
  jurisdiction?: string | null;
  source_ids?: string[];
}

export interface ChangesFeedDoc {
  schema: typeof CHANGES_FEED_SCHEMA;
  release: ReleaseBlock;
  previous: ReleaseBlock | null;
  baseline: boolean;
  events: ChangeEvent[];
  event_count: number;
  truncated: boolean;
  note?: string;
  disclosures: string[];
}

/** The three release docs the surface reads (index + sources + feed). */
export interface ReleaseChangesDoc {
  index: ChangesIndexDoc;
  sources: SourceChangesDoc | null;
  feed: ChangesFeedDoc | null;
}

// --- fail-closed validation -------------------------------------------------- //

function fail(path: string, what: string): never {
  throw new Error(`${path}: not a valid changes document — ${what} (SIG-UI-072)`);
}

function isObject(v: unknown): v is Record<string, unknown> {
  return typeof v === "object" && v !== null && !Array.isArray(v);
}

function isReleaseBlock(v: unknown, path: string): v is ReleaseBlock {
  if (!isObject(v)) fail(path, `release block is not an object`);
  if (typeof v.publication_id !== "string" || !v.publication_id) {
    fail(path, `release block carries no publication_id`);
  }
  return true;
}

export function validateChangesIndex(v: unknown, path: string): ChangesIndexDoc {
  if (!isObject(v)) fail(path, `expected a JSON object`);
  if (v.schema !== CHANGES_INDEX_SCHEMA) {
    fail(path, `schema ${JSON.stringify(v.schema)} != ${CHANGES_INDEX_SCHEMA}`);
  }
  if (!isReleaseBlock(v.release, path)) fail(path, `release block malformed`);
  if (v.previous !== null && v.previous !== undefined && !isReleaseBlock(v.previous, path)) {
    fail(path, `previous release block malformed`);
  }
  if (typeof v.baseline !== "boolean") fail(path, `baseline is not a bool`);
  if (!isObject(v.totals)) fail(path, `totals missing`);
  for (const k of ["added", "removed", "changed", "records", "previous_records"] as const) {
    if (typeof (v.totals as Record<string, unknown>)[k] !== "number") {
      fail(path, `totals.${k} is not a number`);
    }
  }
  if (!Array.isArray(v.disclosures)) fail(path, `disclosures is not an array`);
  return v as unknown as ChangesIndexDoc;
}

const SOURCE_CHANGE_KINDS: SourceChangeKind[] = [
  "added",
  "retired",
  "newly_failing",
  "lane_changed",
];

export function validateSourceChanges(v: unknown, path: string): SourceChangesDoc {
  if (!isObject(v)) fail(path, `expected a JSON object`);
  if (v.schema !== SOURCE_CHANGES_SCHEMA) {
    fail(path, `schema ${JSON.stringify(v.schema)} != ${SOURCE_CHANGES_SCHEMA}`);
  }
  if (v.state !== "evaluated" && v.state !== "not_evaluable") {
    fail(path, `state ${JSON.stringify(v.state)} is not evaluated|not_evaluable`);
  }
  for (const kind of SOURCE_CHANGE_KINDS) {
    if (!Array.isArray(v[kind])) fail(path, `${kind} is not an array`);
    for (const row of v[kind] as unknown[]) {
      if (!isObject(row) || typeof row.source_id !== "string") {
        fail(path, `a ${kind} row carries no source_id`);
      }
    }
  }
  return v as unknown as SourceChangesDoc;
}

const CHANGE_TYPES: ChangeType[] = ["added", "removed", "changed"];

export function validateChangesFeed(v: unknown, path: string): ChangesFeedDoc {
  if (!isObject(v)) fail(path, `expected a JSON object`);
  if (v.schema !== CHANGES_FEED_SCHEMA) {
    fail(path, `schema ${JSON.stringify(v.schema)} != ${CHANGES_FEED_SCHEMA}`);
  }
  if (!isReleaseBlock(v.release, path)) fail(path, `release block malformed`);
  if (!Array.isArray(v.events)) fail(path, `events is not an array`);
  for (const [i, e] of (v.events as unknown[]).entries()) {
    if (!isObject(e)) fail(path, `events[${i}] is not an object`);
    if (typeof e.artifact_id !== "string" || !e.artifact_id) {
      fail(path, `events[${i}] carries no artifact_id`);
    }
    if (!CHANGE_TYPES.includes(e.change_type as ChangeType)) {
      fail(path, `events[${i}].change_type ${JSON.stringify(e.change_type)} is not a change type`);
    }
  }
  return v as unknown as ChangesFeedDoc;
}

// --- the two classes --------------------------------------------------------- //

/** SIG-UI-072's two separated classes. */
export type ChangeClass = "sig_records" | "world_changed";

/** A record-diff event's class: `source_withdrawn` removals are the world
 *  withdrawing the record's footing; every other record event is SIG's
 *  records changing (SIG learned, re-resolved or re-minted — disclosed). */
export function recordEventClass(ev: ChangeEvent): ChangeClass {
  return ev.change_type === "removed" && ev.reason === "source_withdrawn"
    ? "world_changed"
    : "sig_records";
}

/** A source-lifecycle row's class: `retired`/`newly_failing` are the source
 *  reporting a world-side change; `added`/`lane_changed` are changes SIG
 *  recorded (a registry gain, a lane decision). */
export function sourceChangeClass(kind: SourceChangeKind): ChangeClass {
  return kind === "retired" || kind === "newly_failing" ? "world_changed" : "sig_records";
}

/** One display row on the changes page / one feed entry. */
export interface ChangeRow {
  /** The separated class. */
  cls: ChangeClass;
  /** `record` (the record-id diff) or `source` (the source-lifecycle diff). */
  kind: "record" | "source";
  /** The change verb — a change_type or a SourceChangeKind. */
  change: string;
  /** The display label (record label / entity_id / source name / source_id). */
  label: string;
  /** The stable key (record_key / source_id). */
  key: string;
  /** The record's field for `changed` events; null otherwise. */
  field: string | null;
  /** Removal reason for `removed` record events; lane/state moves for source rows. */
  detail: string | null;
  /** World date the event is dated at (`new_date` / the release as-of). */
  date: string | null;
  /** The record's slug path (per-place feed routing). */
  jurisdiction: string | null;
  /** The record's source ids (per-source feed routing). */
  sourceIds: string[];
  /** The compartment the record event lives in (display grouping). */
  compartment: string | null;
}

/** The removed reason's plain display (the raw class stays in <code>). */
export const REMOVED_REASON_LABELS: Record<string, string> = {
  withdrawn: "withdrawn by a publication decision",
  superseded: "the entity survives under a different record key",
  source_withdrawn: "every source it carried is absent from this release",
  no_longer_published: "no longer published — no recorded reason",
};

function eventLabel(ev: ChangeEvent): string {
  const nv = ev.new_value as { label?: unknown } | null;
  const ov = ev.old_value as { label?: unknown } | null;
  return (
    ev.label ??
    (typeof nv?.label === "string" ? nv.label : undefined) ??
    (typeof ov?.label === "string" ? ov.label : undefined) ??
    ev.entity_id ??
    ev.artifact_id
  );
}

function eventDetail(ev: ChangeEvent): string | null {
  if (ev.change_type === "removed") {
    return REMOVED_REASON_LABELS[ev.reason ?? ""] ?? ev.reason ?? null;
  }
  if (ev.change_type === "changed") {
    return ev.field === "record" ? null : `the recorded ${ev.field} changed`;
  }
  return null;
}

/** The record events as display rows, sorted deterministically (key, field). */
export function recordRows(feed: ChangesFeedDoc): ChangeRow[] {
  return feed.events
    .map((ev) => ({
      cls: recordEventClass(ev),
      kind: "record" as const,
      change: ev.change_type,
      label: eventLabel(ev),
      key: ev.artifact_id,
      field: ev.field === "record" ? null : ev.field,
      detail: eventDetail(ev),
      date: ev.new_date ?? ev.old_date,
      jurisdiction: ev.jurisdiction ?? null,
      sourceIds: ev.source_ids ?? [],
      compartment: ev.compartment ?? null,
    }))
    .sort((a, b) => a.key.localeCompare(b.key) || (a.field ?? "").localeCompare(b.field ?? ""));
}

/** The source-lifecycle rows as display rows. */
export function sourceRows(sources: SourceChangesDoc): ChangeRow[] {
  const out: ChangeRow[] = [];
  const push = (kind: SourceChangeKind, r: SourceChangeRow, detail: string | null) =>
    out.push({
      cls: sourceChangeClass(kind),
      kind: "source",
      change: kind,
      label: r.name ?? r.source_id,
      key: r.source_id,
      field: null,
      detail,
      date: null, // filled by the caller from the release's world date
      jurisdiction: null,
      sourceIds: [r.source_id],
      compartment: null,
    });
  for (const r of sources.added) {
    push("added", r, "entered the source universe this release");
  }
  for (const r of sources.retired) {
    push(
      "retired",
      r,
      `left the published source universe${r.lifecycle_state ? ` (${r.lifecycle_state})` : ""}`,
    );
  }
  for (const r of sources.newly_failing) {
    push(
      "newly_failing",
      r,
      `was published, now ${r.lifecycle_state ?? "failing"} — the source stopped publishing on its own side`,
    );
  }
  for (const r of sources.lane_changed) {
    push(
      "lane_changed",
      r,
      `lane moved ${r.previous_lane ?? "?"} → ${r.lane ?? "?"} — a recorded lane decision`,
    );
  }
  return out.sort((a, b) => a.key.localeCompare(b.key));
}

/** Every display row across both diffs, each carrying its class. */
export function changeRows(doc: ReleaseChangesDoc): ChangeRow[] {
  const world = doc.index.release.as_of_world?.slice(0, 10) ?? null;
  const rows = [
    ...(doc.feed ? recordRows(doc.feed) : []),
    ...(doc.sources ? sourceRows(doc.sources) : []),
  ];
  for (const r of rows) {
    if (r.date === null) r.date = world;
  }
  return rows;
}

/** Rows of one class. */
export function rowsForClass(rows: readonly ChangeRow[], cls: ChangeClass): ChangeRow[] {
  return rows.filter((r) => r.cls === cls);
}

/** The bounded page list — a truncated diff names its total, never a smoothed count. */
export const PAGE_ROW_CAP = 50;

// --- feed scopes -------------------------------------------------------------- //

export interface ChangeFeedScope {
  /** The feed path segment — `all`, `place/<slug-path>`, `source/<id>`. */
  path: string;
  scope: "all" | "place" | "source";
  title: string;
  /** The HTML page the feed's alternate link names. */
  pagePath: string;
}

export const CHANGES_FEED_FORMAT = "atom" as const;

/** The feed file path for a scope (`changes/feeds/place/usa/ok.atom`). */
export function changesFeedPath(scopePath: string): string {
  return `changes/feeds/${scopePath}.${CHANGES_FEED_FORMAT}`;
}

/** The OPML bundle path (`changes/feeds.opml`). */
export const CHANGES_OPML_PATH = "changes/feeds.opml";

/** Rows whose jurisdiction sits at-or-under `path` (a place feed covers
 *  its descendants — a subscriber at `usa/ok` sees `usa/ok/<place>`). */
function underPath(jurisdiction: string | null, path: string): boolean {
  return jurisdiction === path || (jurisdiction?.startsWith(`${path}/`) ?? false);
}

/**
 * The feed scope set — `all` always; `place/<slug-path>` for every emitted
 * dossier page (empty or not — a subscriber can come early, D-K7-5's
 * posture); `source/<id>` for every emitted source page.
 */
export function changeFeedScopes(
  placePaths: readonly { path: string; name: string }[],
  sourceIds: readonly { id: string; name: string }[],
): ChangeFeedScope[] {
  const scopes: ChangeFeedScope[] = [
    {
      path: "all",
      scope: "all",
      title: "SIG changes — every change",
      pagePath: "changes/",
    },
  ];
  for (const p of placePaths) {
    scopes.push({
      path: `place/${p.path}`,
      scope: "place",
      title: `SIG changes — ${p.name}`,
      pagePath: p.path === "unplaced" ? "dossier/unplaced/" : `dossier/${p.path}/`,
    });
  }
  for (const s of sourceIds) {
    scopes.push({
      path: `source/${s.id}`,
      scope: "source",
      title: `SIG changes — ${s.name}`,
      pagePath: `sources/${s.id}/`,
    });
  }
  return scopes;
}

/** The rows one scope carries (`null` when the scope names nothing minted). */
export function scopeRows(
  rows: readonly ChangeRow[],
  scopes: readonly ChangeFeedScope[],
  scopePath: string,
): ChangeRow[] | null {
  const scope = scopes.find((s) => s.path === scopePath);
  if (!scope) return null;
  if (scope.scope === "all") return [...rows];
  if (scope.scope === "place") {
    const path = scopePath.slice("place/".length);
    return rows.filter((r) => r.kind === "record" && underPath(r.jurisdiction, path));
  }
  const id = scopePath.slice("source/".length);
  return rows.filter((r) => r.sourceIds.includes(id));
}
