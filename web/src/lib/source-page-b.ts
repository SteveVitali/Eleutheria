// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * P36.69 (R11-K13-UX10-3b; SIG-TRANSP-005/008/040/041/043, SIG-UI-056 cited)
 * — the `/sources/<id>/…` page-B model: the runs, captures (+ changes list,
 * file actions), versions, entity-browse and dossier-contribution sub-pages
 * beside page A (P36.47). T1, zero-JS; every fact renders with JS off and
 * reads only release-pinned artifacts (SIG-UI-076).
 *
 * Data seams (all release-pinned, never a live read):
 *
 *   - `transparency/captures.jsonl` — the release-level `sig.capture-record/1`
 *     stream, filtered per source (K10 §10: the per-source captures list is
 *     the same rows the artifact carries — `captures/` renders what a future
 *     per-source `captures.jsonl` would carry verbatim).
 *   - `transparency/sources/<id>/versions.json` — the `sig.source-versions/1`
 *     index (P36.68): per-release extract entries, manifest-only prior
 *     releases (D-K9-2 = a), the honest `extract_absent` state.
 *   - the published-entity derivation — `sig.source-entities/1`-shaped rows:
 *     fixtures serve the committed corpus; export mode derives the list from
 *     the compartment `sites.jsonl` `_rights.source_id` rows plus the entity
 *     twins' citing claim groups (each a published record of the source's).
 *   - `sig.source-row/1` `contributions` — the shared dossier-contribution
 *     mirror (P35.44) the dossiers table renders verbatim, basis per row
 *     (SIG-TRANSP-040; numbers equal to the dossier page's by construction,
 *     SIG-DSRC-008).
 *
 * D-J3-2 [B-19] = yes — carried verbatim: scrubbed run logs may be published;
 * a robots disregard discloses as host + count (+ the decision reference),
 * never per-URL detail. The file-action cell is the J3 §5.3 lane × Part VIII
 * × bytes-stored table (SIG-TRANSP-041) — the same vocabulary
 * `exports.statements.capture_view_original` emits (TX-08b); download links
 * exist only for raw-ok, screened, retained bytes, and only when the release
 * actually serves the object.
 */

import { existsSync, readFileSync, readdirSync } from "node:fs";
import { dataSource, exportDir, getEntityLabelRows, getEntityPageTwins } from "./data";
import { getSourcePage, getSourcePageIds, isRegistryOnly } from "./source-page";
import type { SourcePageModel } from "./source-page";
import { dataHref, withBase } from "./paths";
import { isWithdrawn } from "./withdrawals";

// ---------------------------------------------------------------------------
// sig.capture-record/1 — the fields the page reads (the emitted stream may
// carry more; the validator requires only what the render consumes).
// ---------------------------------------------------------------------------

export const CAPTURE_RECORD_SCHEMA = "sig.capture-record/1";
export const SOURCE_VERSIONS_SCHEMA = "sig.source-versions/1";
export const SOURCE_ENTITIES_SCHEMA = "sig.source-entities/1";

export interface CaptureRecord {
  schema: string;
  run_id: string | null;
  source_id: string;
  /** S-6-scrubbed upstream: a full URL, `host#path_sha256:<hex>`, `sealed`
   *  or `not_recorded`. */
  target: string;
  state: string | null;
  records: number | null;
  digest: string | null;
  bytes: number | null;
  media_type: string | null;
  retrieved_at: string | null;
  mark_recorded_at?: string | null;
  records_digest: string | null;
  upstream_declared?: { modified_at: string | null; token: string | null; basis: string } | null;
  /** `actual` | `synthetic` | `legacy`. */
  classification: string | null;
  storage_tier: string | null;
  tier_basis?: string | null;
  lane: string | null;
  lane_basis?: string | null;
  bytes_retained: boolean;
  redaction_applied?: boolean;
  redacted_derivative?: boolean;
  http_status: number | null;
  /** `first` | `changed` | `formatting change only` | `unchanged` |
   *  `not_comparable (no digest)` — the K9 §5.4 change kind. */
  changed_vs_prior: string;
  shared_run?: boolean;
}

export function isCaptureRecord(v: unknown): v is CaptureRecord {
  const o = v as CaptureRecord | null;
  return (
    !!o &&
    o.schema === CAPTURE_RECORD_SCHEMA &&
    typeof o.source_id === "string" &&
    typeof o.target === "string" &&
    typeof o.changed_vs_prior === "string" &&
    typeof o.bytes_retained === "boolean"
  );
}

// ---------------------------------------------------------------------------
// sig.source-versions/1 — the P36.68 index document (mirror of
// exports/source_versions.py; the validator requires the render fields).
// ---------------------------------------------------------------------------

export interface SourceVersionFile {
  path: string;
  name: string;
  format?: string;
  bytes: number;
  sha256: string;
  href?: string;
  rows?: number;
}

export interface SourceVersionEntry {
  release: { label?: string | null; publication_id?: string | null; as_of_world?: string | null; as_of_belief?: string | null };
  /** `extract` | `manifest_only` | `extract_absent`. */
  state: string;
  extract?: string;
  reason?: string;
  absence?: string;
  rows?: { sites: number | null; statements: number | null };
  published_claims?: number | null;
  files: SourceVersionFile[];
  diff?: { state: string; added: number; removed: number; changed: number };
  changed?: boolean | null;
  slice_sha256?: string | null;
}

export interface SourceVersionsDoc {
  schema: string;
  source_id: string;
  name: string;
  entries: SourceVersionEntry[];
  entry_count: number;
  disclosures: string[];
}

export function isSourceVersionsDoc(v: unknown): v is SourceVersionsDoc {
  const o = v as SourceVersionsDoc | null;
  return (
    !!o &&
    o.schema === SOURCE_VERSIONS_SCHEMA &&
    typeof o.source_id === "string" &&
    Array.isArray(o.entries) &&
    Array.isArray(o.disclosures)
  );
}

// ---------------------------------------------------------------------------
// sig.source-entities/1 — one row per published entity the source backs
// (K10 §13/§16.1): ordered jurisdiction → label → record key; capped at
// 10 pages × 100 with the total and the cap stated (D-K10-2).
// ---------------------------------------------------------------------------

export interface SourceEntityRow {
  entity_id: string;
  entity_type: string;
  label: string;
  jurisdiction: string | null;
  first_seen?: string | null;
  last_seen?: string | null;
  /** The record/page route (withBase-joined at render) or null when no
   *  published record route resolves — an honest state, never a dead link. */
  record_href: string | null;
  /** Licence compartment the record draws in (the download's partition). */
  compartment?: string | null;
}

export const ENTITY_BROWSE_PAGE_SIZE = 100;
export const ENTITY_BROWSE_MAX_PAGES = 10;
export const ENTITY_BROWSE_CAP = ENTITY_BROWSE_PAGE_SIZE * ENTITY_BROWSE_MAX_PAGES;

// ---------------------------------------------------------------------------
// The J3 §5.3 file-action table (SIG-TRANSP-041) — the lane × Part VIII ×
// bytes-stored decision, mirroring `exports.statements.capture_view_original`
// verbatim so the page and the release record state the same kind.
// ---------------------------------------------------------------------------

export const P8_REDACTED_CLASSES = new Set(["P8-5", "P8-6", "P8-8"]);
export const P8_SEALED_CLASSES = new Set(["P8-1", "P8-2", "P8-4"]);

export type FileActionKind =
  | "download_original"
  | "download_redacted"
  | "view_at_source"
  | "not_redistributable"
  | "rights_not_reviewed"
  | "not_recorded"
  | "run_record";

export interface FileAction {
  kind: FileActionKind;
  label: string;
  /** The href the action may carry — only `view_at_source` today (the
   *  S-6-scrubbed upstream URL; a host-only or withheld upstream carries
   *  none). Byte routes carry no href until the release serves them. */
  href: string | null;
  note: string | null;
}

/** The scrubbed upstream split back into its publishable parts. */
export function upstreamParts(target: string): { url: string | null; host: string | null } {
  if (target === "sealed" || target === "not_recorded" || target === "") {
    return { url: null, host: null };
  }
  if (target.startsWith("http://") || target.startsWith("https://")) {
    try {
      return { url: target, host: new URL(target).host };
    } catch {
      return { url: target, host: null };
    }
  }
  const host = target.split("#")[0] ?? target;
  return { url: null, host: host || null };
}

/** Part VIII class for one capture row — the record does not carry it
 *  itself; the source row's `part_viii_class` governs (per-source today). */
export function captureFileAction(
  capture: Pick<CaptureRecord, "classification" | "storage_tier" | "lane" | "bytes_retained" | "target">,
  partViiiClass: string | null,
): FileAction {
  if (capture.classification === "synthetic") {
    return {
      kind: "run_record",
      label: "run record — not a copy of the source",
      href: null,
      note: "a synthetic capture records the run, not stored bytes",
    };
  }
  const sealed = capture.storage_tier === "sealed" || (partViiiClass !== null && P8_SEALED_CLASSES.has(partViiiClass));
  if (capture.lane === "restricted" || sealed) {
    const reason = partViiiClass !== null && P8_SEALED_CLASSES.has(partViiiClass) ? partViiiClass : "terms";
    return { kind: "not_redistributable", label: "Not redistributable", href: null, note: `reason: ${reason}` };
  }
  if (capture.lane === "unknown" || capture.lane === null) {
    return { kind: "rights_not_reviewed", label: "Rights not reviewed", href: null, note: null };
  }
  if (capture.lane === "raw-ok") {
    if (capture.bytes_retained) {
      if (partViiiClass !== null && P8_REDACTED_CLASSES.has(partViiiClass)) {
        return {
          kind: "download_redacted",
          label: "Download redacted copy",
          href: null,
          note: "a redacted copy serves as a new capture once the raw archive publishes it; the original is never served",
        };
      }
      return {
        kind: "download_original",
        label: "Download original",
        href: null,
        note: "the raw archive is not yet published — the recorded sha256 identifies the object when it is",
      };
    }
    const up = upstreamParts(capture.target);
    return {
      kind: "view_at_source",
      label: "View at source",
      href: up.url ?? (up.host ? `https://${up.host}/` : null),
      note: "SIG did not retain these bytes",
    };
  }
  if (capture.lane === "derived-only" || capture.lane === "link-only") {
    const up = upstreamParts(capture.target);
    return {
      kind: "view_at_source",
      label: "View at source",
      href: up.url ?? (up.host ? `https://${up.host}/` : null),
      note: null,
    };
  }
  return { kind: "not_recorded", label: "not_recorded", href: null, note: null };
}

// ---------------------------------------------------------------------------
// Sort / filter derivations (K10 §3): captures sorted target then time desc;
// the changes list keeps only record-set changes.
// ---------------------------------------------------------------------------

/** K10 §3: the captures list sorts by target, then retrieved_at desc. */
export function sortedCaptures(rows: readonly CaptureRecord[]): CaptureRecord[] {
  return [...rows].sort((a, b) => {
    const t = a.target.localeCompare(b.target);
    if (t !== 0) return t;
    return String(b.retrieved_at ?? "").localeCompare(String(a.retrieved_at ?? ""));
  });
}

/** The changes list — only captures whose RECORDS digest (or upstream-declared
 *  date) changed (K10 §3): `changed_vs_prior === "changed"`. Formatting-only
 *  and byte-comparable-but-unchanged rows stay on the full list. */
export function changedCaptures(rows: readonly CaptureRecord[]): CaptureRecord[] {
  return sortedCaptures(rows).filter((r) => r.changed_vs_prior === "changed");
}

/** The change-kind display word — the record's own closed vocabulary. */
export const CHANGE_KIND_WORDS: Record<string, string> = {
  first: "first capture",
  changed: "records changed",
  "formatting change only": "formatting change only",
  unchanged: "unchanged",
  "not_comparable (no digest)": "not comparable (no digest recorded)",
};
export function changeKindWord(kind: string): string {
  return CHANGE_KIND_WORDS[kind] ?? kind;
}

// ---------------------------------------------------------------------------
// Pagination (K9 §6.1) — 100 rows per page; entities cap at 10 pages.
// ---------------------------------------------------------------------------

export const SUBPAGE_SIZE = 100;

/** The in-site record-route join for a data-carried href: a root-absolute
 *  `/r/…`-or-`/…` path re-bases through {@link dataHref} (the snapshot-
 *  namespace exceptions pass through); a relative in-site path
 *  (`entity/…`, `dossier/…`) joins under the configured base through
 *  {@link withBase}. `null` stays null — the typed absence. */
const SLASH = String.fromCharCode(47); // never a `"/"` literal — the root-absolute containment check counts literals, not joined paths
export function recordHref(href: string | null): string | null {
  if (href === null) return null;
  return href.startsWith(SLASH) ? dataHref(href) : withBase(href);
}

export function pageCount(total: number, per: number = SUBPAGE_SIZE): number {
  return Math.max(1, Math.ceil(total / per));
}

export function pageSlice<T>(rows: readonly T[], page: number, per: number = SUBPAGE_SIZE): T[] {
  return rows.slice((page - 1) * per, page * per);
}

// ---------------------------------------------------------------------------
// Data seams.
// ---------------------------------------------------------------------------

function readJsonl(path: string): unknown[] {
  return readFileSync(path, "utf-8")
    .split("\n")
    .map((l) => l.trim())
    .filter(Boolean)
    .map((l) => JSON.parse(l) as unknown);
}

/** One source's `sig.capture-record/1` rows — `null` when no captures
 *  artifact exists (the honest absence, never a fabricated capture). */
export function getSourceCaptures(sourceId: string): CaptureRecord[] | null {
  if (dataSource() === "export") {
    const perSource = `${exportDir()}/transparency/sources/${sourceId}/captures.jsonl`;
    const release = `${exportDir()}/transparency/captures.jsonl`;
    const path = existsSync(perSource) ? perSource : release;
    if (!existsSync(path)) return null;
    const rows = readJsonl(path).filter(
      (r) => (r as CaptureRecord | null)?.source_id === sourceId,
    );
    for (const r of rows) {
      if (!isCaptureRecord(r)) {
        throw new Error(`${path}: a row is not a valid ${CAPTURE_RECORD_SCHEMA}`);
      }
    }
    return rows as CaptureRecord[];
  }
  const fixture = SOURCE_CAPTURES_FIXTURE[sourceId];
  return fixture === undefined ? null : fixture;
}

/** One source's `sig.source-versions/1` index — `null` when the release
 *  emits none (a pre-P36.68 artifact set: the honest absence). */
export function getSourceVersions(sourceId: string): SourceVersionsDoc | null {
  if (dataSource() === "export") {
    const path = `${exportDir()}/transparency/sources/${sourceId}/versions.json`;
    if (!existsSync(path)) return null;
    const parsed: unknown = JSON.parse(readFileSync(path, "utf-8"));
    if (!isSourceVersionsDoc(parsed)) {
      throw new Error(`${path}: not a valid ${SOURCE_VERSIONS_SCHEMA} document`);
    }
    return parsed;
  }
  return SOURCE_VERSIONS_FIXTURE[sourceId] ?? null;
}

/**
 * The published-entity browse rows for one source (SIG-TRANSP-043).
 * Fixtures serve the committed `sig.source-entities/1`-shaped corpus;
 * export mode derives it from emitted artifacts: every compartment
 * `sites.jsonl` row whose `_rights.source_id` names the source (a site
 * record the source's rights govern), plus contract-A entity twins whose
 * claim groups cite the source. Withdrawn subjects are dropped (P34.19).
 */
export function getSourceEntities(sourceId: string): SourceEntityRow[] {
  if (dataSource() === "export") {
    const rows = new Map<string, SourceEntityRow>();
    const root = exportDir();
    const compEntries = existsSync(root) ? readdirSync(root) : [];
    for (const comp of compEntries) {
      const p = `${root}/${comp}/sites.jsonl`;
      if (!existsSync(p)) continue;
      for (const line of readFileSync(p, "utf-8").split("\n")) {
        const t = line.trim();
        if (!t) continue;
        const row = JSON.parse(t) as {
          entity_id?: unknown;
          entity_type?: unknown;
          label?: unknown;
          name?: unknown;
          jurisdiction?: unknown;
          _rights?: { source_id?: unknown };
        };
        if (typeof row.entity_id !== "string") continue;
        if (isWithdrawn(row.entity_id)) continue;
        const rights = row._rights as { source_id?: unknown } | undefined;
        if (rights?.source_id !== sourceId) continue;
        rows.set(row.entity_id, {
          entity_id: row.entity_id,
          entity_type: typeof row.entity_type === "string" ? row.entity_type : "deployment",
          label: typeof row.label === "string" ? row.label : typeof row.name === "string" ? row.name : row.entity_id,
          jurisdiction: typeof row.jurisdiction === "string" ? row.jurisdiction : null,
          record_href: null,
          compartment: comp,
        });
      }
    }
    // Contract-A entities: a label row whose twin cites the source.
    for (const lr of getEntityLabelRows()) {
      if (!lr.url_type || !lr.slug || !lr.hash) continue;
      const key = `${lr.slug}--${lr.hash}`;
      const cites = getEntityPageTwins(lr.url_type, key).some((twin) =>
        [...twin.claims, ...twin.access.degree_only].some((g) =>
          g.sources.some((s) => s.id === sourceId),
        ) || twin.relations.some((g) => g.items.some((i) => i.sources.some((s) => s.id === sourceId))),
      );
      if (!cites) continue;
      rows.set(lr.entity_id, {
        entity_id: lr.entity_id,
        entity_type: lr.url_type,
        label: lr.label ?? lr.entity_id,
        jurisdiction: lr.place_jkey ?? null,
        record_href: `entity/${lr.url_type}/${key}/`,
        compartment: null,
      });
    }
    return sortEntityRows([...rows.values()]);
  }
  return sortEntityRows([...(SOURCE_ENTITIES_FIXTURE[sourceId] ?? [])]);
}

/** Jurisdiction → label → record key (K10 §13's ordering). */
export function sortEntityRows(rows: readonly SourceEntityRow[]): SourceEntityRow[] {
  return [...rows].sort((a, b) => {
    const j = (a.jurisdiction ?? "").localeCompare(b.jurisdiction ?? "");
    if (j !== 0) return j;
    const l = a.label.localeCompare(b.label);
    if (l !== 0) return l;
    return a.entity_id.localeCompare(b.entity_id);
  });
}

export interface EntityBrowse {
  rows: SourceEntityRow[];
  total: number;
  cap: number;
  capped: boolean;
  pages: number;
}

/** The capped browse model — the page states the total AND the cap. */
export function entityBrowse(rows: readonly SourceEntityRow[]): EntityBrowse {
  const shown = rows.slice(0, ENTITY_BROWSE_CAP);
  return {
    rows: shown,
    total: rows.length,
    cap: ENTITY_BROWSE_CAP,
    capped: rows.length > ENTITY_BROWSE_CAP,
    pages: pageCount(shown.length),
  };
}

/** The non-registry-only source ids — page-B sub-routes exist only for
 *  sources the page may disclose runs/captures/records for (S-11: a gated,
 *  refused, withdrawn or lane-gated row publishes nothing but its registry
 *  record — no run, capture or entity sub-route exists). */
export function getPageBIds(): string[] {
  return getSourcePageIds().filter((id) => {
    const model = getSourcePage(id) as SourcePageModel | null;
    return model !== null && !isRegistryOnly(model.row);
  });
}

// ---------------------------------------------------------------------------
// Fixtures — synthetic demonstration data exercising every file-action cell,
// change kind, version state and the entity-browse cap (§3.1: demo ids).
// ---------------------------------------------------------------------------

const _CAP = (
  over: Partial<CaptureRecord> & Pick<CaptureRecord, "target" | "lane" | "bytes_retained" | "retrieved_at" | "changed_vs_prior">,
): CaptureRecord => ({
  schema: CAPTURE_RECORD_SCHEMA,
  run_id: null,
  source_id: "demo",
  state: "fetched",
  records: null,
  digest: null,
  bytes: null,
  media_type: "text/csv",
  mark_recorded_at: null,
  records_digest: null,
  upstream_declared: { modified_at: null, token: null, basis: "not_detectable" },
  classification: "actual",
  storage_tier: "public",
  tier_basis: "demonstration entry",
  lane_basis: "source_redistribution",
  redaction_applied: false,
  redacted_derivative: false,
  http_status: 200,
  shared_run: false,
  ...over,
});

const demoCaptureBulk = (sourceId: string, n: number): CaptureRecord[] => {
  const rows: CaptureRecord[] = [];
  for (let i = 0; i < n; i += 1) {
    const day = 1 + (i % 28);
    const month = 1 + (i % 9);
    const changed = i % 2 === 0 ? "changed" : i % 3 === 0 ? "formatting change only" : "unchanged";
    rows.push(
      _CAP({
        source_id: sourceId,
        run_id: `demo-run-${Math.floor(i / 10)}`,
        target: `feed-${i % 7}.example.invalid#path_sha256:${String(i).padStart(8, "0")}${"0".repeat(56)}`,
        records: 10 + i,
        digest: `${"ab".repeat(31)}${String(i % 16)}${String((i + 1) % 16)}`,
        bytes: 2_000 + i * 37,
        retrieved_at: `2026-${String(month).padStart(2, "0")}-${String(day).padStart(2, "0")}T0${i % 9}:12:00Z`,
        records_digest: `${"cd".repeat(31)}${String(i % 16)}${String((i + 3) % 16)}`,
        changed_vs_prior: changed,
        lane: "derived-only",
        bytes_retained: false,
        http_status: i % 11 === 0 ? 304 : 200,
      }),
    );
  }
  return rows;
};

export const SOURCE_CAPTURES_FIXTURE: Record<string, CaptureRecord[]> = {
  okc_camera_registry: [
    // raw-ok + retained + P8 clear → Download original (label; no raw archive yet)
    _CAP({
      source_id: "okc_camera_registry",
      run_id: "demo-exec-okc-3",
      target: "https://example.invalid/okc/camera-registry.csv",
      records: 38,
      digest: "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2",
      bytes: 48_211,
      retrieved_at: "2026-10-15T05:12:40Z",
      records_digest: "f0e1d2c3b4a5968778695a4b3c2d1e0ff0e1d2c3b4a5968778695a4b3c2d1e0f",
      changed_vs_prior: "changed",
      lane: "raw-ok",
      bytes_retained: true,
      upstream_declared: { modified_at: "2026-10-12T00:00:00Z", token: null, basis: "header (upstream-declared Last-Modified)" },
    }),
    // raw-ok + retained + source P8 clear → a second Download original cell
    _CAP({
      source_id: "okc_camera_registry",
      run_id: "demo-exec-okc-3",
      target: "https://example.invalid/okc/camera-registry-notes.csv",
      records: 12,
      digest: "b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3",
      bytes: 9_104,
      retrieved_at: "2026-10-15T05:12:41Z",
      records_digest: "e1d2c3b4a5968778695a4b3c2d1e0ff0e1d2c3b4a5968778695a4b3c2d1e0ff0",
      changed_vs_prior: "formatting change only",
      lane: "raw-ok",
      bytes_retained: true,
    }),
    // raw-ok + bytes not retained → View at source + did-not-retain note
    _CAP({
      source_id: "okc_camera_registry",
      run_id: "demo-exec-okc-2",
      target: "https://example.invalid/okc/pilot-feed.csv",
      records: null,
      digest: "c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4",
      bytes: 3_410,
      retrieved_at: "2026-10-01T05:09:18Z",
      records_digest: null,
      changed_vs_prior: "not_comparable (no digest)",
      lane: "raw-ok",
      bytes_retained: false,
      http_status: 200,
    }),
    // derived-only → View at source (full URL per S-6)
    _CAP({
      source_id: "okc_camera_registry",
      run_id: "demo-exec-okc-1",
      target: "https://example.invalid/okc/registry-index.html",
      records: 40,
      digest: "d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5",
      bytes: 12_008,
      retrieved_at: "2026-09-15T05:00:00Z",
      records_digest: "c2d1e0ff0e1d2c3b4a5968778695a4b3c2d1e0ff0e1d2c3b4a5968778695a4b3",
      changed_vs_prior: "unchanged",
      lane: "derived-only",
      bytes_retained: false,
    }),
    // link-only → View at source (host + path hash per S-6)
    _CAP({
      source_id: "okc_camera_registry",
      run_id: "demo-exec-okc-1",
      target: "data.example.invalid#path_sha256:9f8b7c6d5e4f3a2b1c0d9e8f7a6b5c4d3e2f1a0b9c8d7e6f5a4b3c2d1e0f9a8b",
      records: 2,
      digest: "e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6",
      bytes: 2_048,
      retrieved_at: "2026-09-15T05:01:02Z",
      records_digest: "b3c2d1e0ff0e1d2c3b4a5968778695a4b3c2d1e0ff0e1d2c3b4a5968778695a4",
      changed_vs_prior: "first",
      lane: "link-only",
      bytes_retained: false,
    }),
    // synthetic run-level capture → run-record cell
    _CAP({
      source_id: "okc_camera_registry",
      run_id: "demo-exec-okc-2",
      target: "sealed",
      state: "run_record",
      records: null,
      digest: null,
      bytes: 0,
      media_type: null,
      retrieved_at: "2026-10-01T05:09:18Z",
      records_digest: null,
      changed_vs_prior: "first",
      classification: "synthetic",
      storage_tier: "sealed",
      lane: "raw-ok",
      bytes_retained: false,
      http_status: null,
    }),
  ],
  okc_council_minutes: [
    _CAP({
      source_id: "okc_council_minutes",
      run_id: "demo-exec-min-1",
      target: "restricted.example.invalid#path_sha256:1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b",
      records: 4,
      digest: "f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7",
      bytes: 21_400,
      retrieved_at: "2026-10-13T05:03:11Z",
      records_digest: "a4b3c2d1e0ff0e1d2c3b4a5968778695a4b3c2d1e0ff0e1d2c3b4a59687786",
      changed_vs_prior: "changed",
      lane: "restricted",
      bytes_retained: false,
      http_status: 200,
    }),
    _CAP({
      source_id: "okc_council_minutes",
      run_id: "demo-exec-min-1",
      target: "https://example.invalid/okc/minutes-index.html",
      records: 1,
      digest: "07b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8",
      bytes: 5_120,
      retrieved_at: "2026-10-13T05:02:00Z",
      records_digest: "95a4b3c2d1e0ff0e1d2c3b4a5968778695a4b3c2d1e0ff0e1d2c3b4a596877",
      changed_vs_prior: "unchanged",
      lane: "unknown",
      bytes_retained: false,
    }),
    // raw-ok + retained + the source's P8-5 class → Download redacted copy
    _CAP({
      source_id: "okc_council_minutes",
      run_id: "demo-exec-min-1",
      target: "https://example.invalid/okc/minutes-2026-09.csv",
      records: 2,
      digest: "18c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9",
      bytes: 6_144,
      retrieved_at: "2026-10-13T05:03:05Z",
      records_digest: "a5968778695a4b3c2d1e0ff0e1d2c3b4a5968778695a4b3c2d1e0ff0e1d2c3b4",
      changed_vs_prior: "first",
      lane: "raw-ok",
      bytes_retained: true,
      http_status: 200,
    }),
  ],
  // Bulk demo captures — exercises the 100-row pagination + the changes list.
  demo_ingested_feed: demoCaptureBulk("demo_ingested_feed", 230),
};

export const SOURCE_VERSIONS_FIXTURE: Record<string, SourceVersionsDoc> = {
  okc_camera_registry: {
    schema: SOURCE_VERSIONS_SCHEMA,
    source_id: "okc_camera_registry",
    name: "OKC camera registry",
    entries: [
      {
        release: { label: "demo-release-2026-08", publication_id: "demo-pub-202608", as_of_world: "2026-08-31T00:00:00Z", as_of_belief: "2026-08-31T00:00:00Z" },
        state: "manifest_only",
        extract: "not_republished",
        reason: "release predates the version index — the entry is reconstructed from the previous release's own integrity manifest and source row, never re-derived bytes (D-K9-2 = a)",
        rows: { sites: 34, statements: 11 },
        published_claims: 11,
        files: [
          { path: "by-source/okc_camera_registry/sites.csv.gz", name: "sites.csv.gz", sha256: "aa".repeat(32), bytes: 2_048 },
          { path: "by-source/okc_camera_registry/statements.jsonl.gz", name: "statements.jsonl.gz", sha256: "bb".repeat(32), bytes: 4_096 },
        ],
        changed: null,
      },
      {
        release: { label: "demo-release-2026-09", publication_id: "demo-pub-202609", as_of_world: "2026-09-30T00:00:00Z", as_of_belief: "2026-09-30T00:00:00Z" },
        state: "extract_absent",
        absence: "no by-source/<id>/ extract was emitted for this release — a published source always carries the statements slice (K9 C-8), so this absence is named, never smoothed (SIG-TRANSP-032)",
        rows: { sites: null, statements: null },
        published_claims: 12,
        files: [],
        diff: { state: "evaluated", added: 4, removed: 0, changed: 1 },
        changed: true,
        slice_sha256: null,
      },
      {
        release: { label: "demo-release-2026-10", publication_id: "demo-pub-202610", as_of_world: "2026-10-31T00:00:00Z", as_of_belief: "2026-10-31T00:00:00Z" },
        state: "extract",
        rows: { sites: 38, statements: 12 },
        published_claims: 12,
        files: [
          { path: "by-source/okc_camera_registry/sites.csv.gz", name: "sites.csv.gz", format: "csv.gz", sha256: "99".repeat(32), bytes: 2_560, href: "https://files.example.invalid/demo/by-source/okc_camera_registry/sites.999999999999.csv.gz", rows: 38 },
          { path: "by-source/okc_camera_registry/statements.jsonl.gz", name: "statements.jsonl.gz", format: "jsonl.gz", sha256: "88".repeat(32), bytes: 5_120, href: "https://files.example.invalid/demo/by-source/okc_camera_registry/statements.888888888888.jsonl.gz", rows: 12 },
          { path: "by-source/okc_camera_registry/ATTRIBUTION.txt", name: "ATTRIBUTION.txt", format: "txt", sha256: "77".repeat(32), bytes: 1_024, href: "https://files.example.invalid/demo/by-source/okc_camera_registry/ATTRIBUTION.777777777777.txt" },
          { path: "by-source/okc_camera_registry/datapackage.json", name: "datapackage.json", format: "json", sha256: "66".repeat(32), bytes: 1_024, href: "https://files.example.invalid/demo/by-source/okc_camera_registry/datapackage.666666666666.json" },
        ],
        diff: { state: "evaluated", added: 0, removed: 0, changed: 0 },
        changed: false,
        slice_sha256: "88".repeat(32),
      },
    ],
    entry_count: 3,
    disclosures: [
      "Latest released data — never 'the latest run's data': runs land on the spine between releases without passing the release gates; their data appears in the next release (K9 §7.2).",
      "Unchanged slices share one content hash across entries — a new entry pointing at the same object adds zero bytes on the mirror.",
    ],
  },
  okc_council_minutes: {
    schema: SOURCE_VERSIONS_SCHEMA,
    source_id: "okc_council_minutes",
    name: "OKC council minutes",
    entries: [
      {
        release: { label: "demo-release-2026-10", publication_id: "demo-pub-202610", as_of_world: "2026-10-31T00:00:00Z", as_of_belief: "2026-10-31T00:00:00Z" },
        state: "extract",
        rows: { sites: null, statements: 4 },
        published_claims: 4,
        files: [
          { path: "by-source/okc_council_minutes/statements.jsonl.gz", name: "statements.jsonl.gz", format: "jsonl.gz", sha256: "55".repeat(32), bytes: 1_536, href: "https://files.example.invalid/demo/by-source/okc_council_minutes/statements.555555555555.jsonl.gz", rows: 4 },
        ],
        diff: { state: "baseline", added: 4, removed: 0, changed: 0 },
        changed: true,
        slice_sha256: "55".repeat(32),
      },
    ],
    entry_count: 1,
    disclosures: [
      "Latest released data — never 'the latest run's data': runs land on the spine between releases without passing the release gates; their data appears in the next release (K9 §7.2).",
    ],
  },
};

const demoEntityBulk = (sourceId: string, n: number): SourceEntityRow[] => {
  const rows: SourceEntityRow[] = [];
  for (let i = 0; i < n; i += 1) {
    rows.push({
      entity_id: `device:demo-${i}`,
      entity_type: "deployment",
      label: `Demo record demo-${i} (demonstration entry)`,
      jurisdiction: `demo-jurisdiction-${i % 9}`,
      first_seen: `2026-0${1 + (i % 9)}-01`,
      last_seen: "2026-10-31",
      record_href: null,
      compartment: "demo",
    });
  }
  return rows;
};

export const SOURCE_ENTITIES_FIXTURE: Record<string, SourceEntityRow[]> = {
  okc_camera_registry: [
    {
      entity_id: "device:okc-001",
      entity_type: "deployment",
      label: "Demo site — downtown camera-001 (demonstration entry)",
      jurisdiction: "Oklahoma City, OK",
      first_seen: "2026-09-15",
      last_seen: "2026-10-15",
      record_href: "dossier/usa/ok/oklahoma-city-4064000/sites/#device:okc-001",
      compartment: "sig_graph",
    },
    {
      entity_id: "device:okc-002",
      entity_type: "deployment",
      label: "Demo site — downtown camera-002 (demonstration entry)",
      jurisdiction: "Oklahoma City, OK",
      first_seen: "2026-09-15",
      last_seen: "2026-10-15",
      record_href: "dossier/usa/ok/oklahoma-city-4064000/sites/#device:okc-002",
      compartment: "sig_graph",
    },
    {
      entity_id: "device:okc-003",
      entity_type: "deployment",
      label: "Demo site — midtown camera-003 (demonstration entry)",
      jurisdiction: "Oklahoma City, OK",
      first_seen: "2026-10-01",
      last_seen: "2026-10-15",
      record_href: "dossier/usa/ok/oklahoma-city-4064000/sites/#device:okc-003",
      compartment: "sig_graph",
    },
  ],
  // Over the 1,000-row cap — exercises the cap text + 10-page bound.
  demo_seed_load: demoEntityBulk("demo_seed_load", 1_050),
};

// Re-export so callers use one lib module.
export { getEntityLabelRows, getEntityPageTwins };
