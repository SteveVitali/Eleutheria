// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * P36.60 (K8 EV-02 / SIG-EVUI-001,002,003,005,006,008,010) — the evidence
 * hub's page model over `web/evidence.json` (`sig.evidence-artifact/1`).
 *
 * The surfaces this module serves (all T1, zero-JS — K8 §4.5):
 *
 *   /evidence/                        the hub: state of the evidence + the
 *                                     browse-artifacts table (≤ 50 rows)
 *   /evidence/page/<n>/               the index's pagination fallback (K9 §6.1)
 *   /evidence/source/<id>/            one-dimension facet lists (J3 G-11),
 *   /evidence/type/<genre>/           each paginated at 50 (the facet page
 *   /evidence/lane/<lane>/            route rides the rest param: `<v>/page/<n>`)
 *   /evidence/place/<path>/
 *   /evidence/state/<binding_state>/
 *   /evidence/artifact/<handle>/      the §4.2 artifact page (+ `.json` twin)
 *   /evidence/artifact/<handle>/diff/<a>..<b>/   the §4.4 capture diff
 *   /evidence/claim/<id>/             the claim viewer (+ `.json` twin)
 *   /evidence/<id>/                   the retired claim address — a moved stub
 *                                     + the JUR-05 generator's 301 rule
 *
 * Honesty rules encoded (SIG-EVUI-003/005/006/008/010, D-K8-4 [B-44]):
 *
 *   - a synthetic capture is a RUN RECORD — labelled, never disguised as a
 *     stored document ("show the 255 synthetic run-record artifacts with
 *     honest labels" — the plan cell, verbatim);
 *   - `bytes_available`/"Download original" renders only where the capture's
 *     own `view_original` label minted it — a label never implies a route;
 *   - the eligibility gate is STRUCTURAL: `getEvidence()` drops withheld and
 *     withdrawn artifacts before this module runs, so an ineligible artifact
 *     mints no page and lists on no index (SIG-EVUI-006);
 *   - the §4.4 diff compares only captures of the SAME artifact that carry
 *     extracted fields — never the fixture pair in an export build
 *     (SIG-EVUI-005);
 *   - a handle is human-readable (K11 §3's shared grammar) and deterministic
 *     over the artifact's own fields — `E-<place>-<code>-<slug>-<hash>`
 *     (SIG-EVUI-010; the producer-side history map is a later row).
 */

import { createHash } from "node:crypto";
import { RUN_RECORD_LABEL } from "./evidence-artifacts";
import type { ArtifactCaptureRow, EvidenceArtifact } from "./recommender";
import { NOT_PUBLISHABLE, NOT_RECORDED, NO_UPSTREAM_URL } from "./provenance-panel";
import type { StatementRow } from "./provenance-panel";

// --- Handles (K11 §3 grammar — `E-<place>-<code>-<slug>-<hash>`) ------------ //

const CROCKFORD = "0123456789abcdefghjkmnpqrstvwxyz";
// The path separator — built without a literal slash so the root-absolute
// containment rule never counts a separator as a site path (the same seam
// entity-figures/source-page use for their pointer joins).
const PATH_SEP = String.fromCharCode(47);
const HANDLE_MAX = 64;
const SLUG_MAX = 24;
const HASH_MIN = 4;
const HASH_MAX = 8;

/** Crockford base32 of the top `5*length` bits of sha256(id) — the TS twin of
 *  `policy.labels.entity_hash`. */
function entityHash(id: string, length: number): string {
  const digest = createHash("sha256").update(id, "utf-8").digest();
  let bits = BigInt(`0x${digest.toString("hex")}`);
  bits >>= BigInt(256 - 5 * length);
  let out = "";
  for (let i = 0; i < length; i += 1) {
    out = CROCKFORD[Number(bits & 0x1fn)] + out;
    bits >>= 5n;
  }
  return out;
}

const TOKEN_RE = /[a-z0-9]+/g;

/** ASCII-folded `[a-z0-9]+` tokens (K11 §3's slug alphabet). */
function asciiTokens(text: string): string[] {
  const folded = text.normalize("NFKD").replace(/[̀-ͯ]/g, "");
  return folded.toLowerCase().match(TOKEN_RE) ?? [];
}

const ORG_ABBREVIATIONS: [string[], string][] = [
  [["police", "department"], "pd"],
  [["sheriff", "s", "office"], "so"],
  [["sheriffs", "office"], "so"],
  [["sheriff", "office"], "so"],
  [["department", "of"], "dept"],
  [["county"], "co"],
];

/** The handle's `<slug>` — the title slugged per K11 §3 (drop the place's
 *  last component, abbreviate org suffixes, cut at 24 chars on a token
 *  boundary); `null` when nothing survives. */
export function handleSlug(title: string, placeSegment: string): string | null {
  let tokens = asciiTokens(title);
  if (tokens.length === 0) return null;
  const placeTail = placeSegment.split("-").at(-1) ?? "";
  tokens = tokens.filter((t) => t !== placeTail);
  const out: string[] = [];
  let i = 0;
  while (i < tokens.length) {
    let replaced = false;
    for (const [words, abbrev] of ORG_ABBREVIATIONS) {
      if (tokens.slice(i, i + words.length).join(" ") === words.join(" ")) {
        out.push(abbrev);
        i += words.length;
        replaced = true;
        break;
      }
    }
    if (!replaced) {
      out.push(tokens[i]!);
      i += 1;
    }
  }
  let slug = out.join("-");
  if (slug.length > SLUG_MAX) {
    const cut = slug.slice(0, SLUG_MAX);
    slug = cut.includes("-") ? cut.slice(0, cut.lastIndexOf("-")) : cut;
  }
  return slug || null;
}

/** The handle's `<place>` — the K4 slug path joined with "-", GEOID suffixes
 *  dropped (K11 §3). `unplaced` when the artifact carries no place binding —
 *  the emitted shape's honest answer today. */
export function handlePlaceSegment(placeKey: string | null | undefined): string {
  if (!placeKey) return "unplaced";
  const parts = placeKey
    .split(PATH_SEP)
    .map((seg) => {
      const m = /^(.+)-\d+$/.exec(seg);
      return m ? m[1]! : seg;
    })
    .filter((p) => p.length > 0);
  return parts.join("-") || "unplaced";
}

/** The handle's `<code>` — a one-token artifact-type mnemonic (the type's own
 *  first token, ≤ 10 chars — `meeting_minutes` → `meeting`). */
export function handleCode(artifactType: string): string {
  const tokens = asciiTokens(artifactType);
  return (tokens[0] ?? "artifact").slice(0, 10);
}

/** Mint one artifact handle (K11 §3, ≤ 64 chars; hash length is the caller's
 *  collision-resolution parameter). */
export function mintArtifactHandle(artifact: EvidenceArtifact, hashLen = HASH_MIN): string {
  const place = handlePlaceSegment(artifact.place_key);
  const code = handleCode(artifact.artifact_type);
  const slug = handleSlug(artifactTitle(artifact), place);
  const parts = ["E", place, code, ...(slug ? [slug] : []), entityHash(artifact.artifact_id, hashLen)];
  const handle = parts.join("-");
  return handle.length <= HANDLE_MAX
    ? handle
    : `${handle.slice(0, HANDLE_MAX - 1)}${entityHash(artifact.artifact_id, hashLen).slice(-1)}`;
}

/**
 * The deterministic `artifact_id → handle` map for the whole list — the
 * K11 §3 collision pass: colliding handles extend their hash 4 → 5…8 in
 * sorted-id order, deterministic every build. Emitted pages + every link
 * resolve through this ONE map, so a handle is stable within a release
 * (SIG-EVUI-010; the cross-release `evidence_handles_history.json` row set
 * is the redirect generator's to consume when a producer emits it).
 */
export function artifactHandles(artifacts: readonly EvidenceArtifact[]): Map<string, string> {
  const ids = artifacts.map((a) => a.artifact_id);
  const byId = new Map(artifacts.map((a) => [a.artifact_id, a]));
  for (let len = HASH_MIN; len <= HASH_MAX; len += 1) {
    const minted = new Map<string, string[]>();
    for (const id of ids) {
      const h = mintArtifactHandle(byId.get(id)!, len);
      minted.set(h, [...(minted.get(h) ?? []), id]);
    }
    if ([...minted.values()].every((g) => g.length === 1)) {
      return new Map(ids.map((id) => [id, mintArtifactHandle(byId.get(id)!, len)]));
    }
  }
  // Over-collision at HASH_MAX — a registry defect, fail loud (SIG-ENG-042).
  throw new Error("evidence handles: unresolved collision at hash length 8");
}

/** The artifact page's canonical path segment (`evidence/artifact/<h>/`). */
export function artifactHref(handle: string): string {
  return `evidence/artifact/${handle}/`;
}

/** The claim viewer's canonical path segment (`evidence/claim/<id>/`). */
export function claimHref(claimId: string): string {
  return `evidence/claim/${claimId}/`;
}

// --- Labels + the honest title -------------------------------------------- //

/** The run-record label a synthetic capture carries (SIG-EVUI-D04 → 003) —
 *  the same verbatim label `evidence-artifacts.ts` mints for the interim list. */
export { RUN_RECORD_LABEL };

/** The title an artifact page shows (K8 §4.2): the recorded title UNLESS it
 *  is the artifact's own id (today's export titles equal the artifact UUID —
 *  NEW-7) — then "<source name> — <type> (run <date>)". Never a bare UUID
 *  in a heading. */
const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
export function artifactTitle(a: EvidenceArtifact): string {
  const t = (a.title ?? "").trim();
  if (t && t !== a.artifact_id && !UUID_RE.test(t)) return t;
  const when = latestCapture(a)?.retrieved_at?.slice(0, 10) ?? a.as_of;
  return `${a.source_name ?? a.source} — ${a.artifact_type.replace(/_/g, " ")} (run ${when})`;
}

/** The capture-classification label (SIG-EVUI-003): every capture row shows
 *  its class; a synthetic row is labelled a run record. */
export function classificationLabel(row: ArtifactCaptureRow): string {
  return row.capture_classification === "synthetic" ? RUN_RECORD_LABEL : (row.capture_classification ?? NOT_RECORDED);
}

/** The artifact's binding state on the shared J3 vocabulary — derived from
 *  its latest capture's classification (an artifact's own state IS its
 *  capture class): `synthetic`/`legacy` → `legacy_synthetic` (a run record),
 *  `actual` → `actual_capture`, no capture row → `not_recorded`. */
export function artifactState(a: EvidenceArtifact): string {
  const cls = a.capture_classification ?? latestCapture(a)?.capture_classification;
  if (cls === "actual") return "actual_capture";
  if (cls === "synthetic" || cls === "legacy") return "legacy_synthetic";
  return NOT_RECORDED;
}

export const ARTIFACT_STATE_LABELS: Record<string, string> = {
  actual_capture: "Stored document capture",
  replayed: "Re-derived from a capture",
  document_only: "Document without a page capture",
  legacy_synthetic: "Run record (no stored document)",
  not_recorded: "No capture recorded",
};

export const LANE_LABELS: Record<string, string> = {
  "raw-ok": "raw-ok (bytes publishable)",
  "derived-only": "derived-only (facts, not bytes)",
  "link-only": "link-only (link, not bytes)",
  restricted: "restricted (withheld)",
  unknown: "unknown lane (rights not reviewed)",
  not_recorded: "lane not recorded",
};

export function laneLabel(lane: string | undefined | null): string {
  return LANE_LABELS[lane ?? ""] ?? lane ?? NOT_RECORDED;
}

// --- Captures -------------------------------------------------------------- //

/** The artifact's capture history, oldest → newest (recorded order kept). */
export function capturesOf(a: EvidenceArtifact): ArtifactCaptureRow[] {
  return [...(a.captures ?? [])].sort((x, y) =>
    String(x.retrieved_at ?? "").localeCompare(String(y.retrieved_at ?? "")) ||
    x.capture_id.localeCompare(y.capture_id),
  );
}

/** The newest capture row, if the export carried any. */
export function latestCapture(a: EvidenceArtifact): ArtifactCaptureRow | undefined {
  const caps = capturesOf(a);
  return caps.at(-1);
}

/**
 * The §4.4 diff pairs an artifact supports — consecutive capture pairs where
 * BOTH rows carry extracted `fields` (SIG-EVUI-005: a diff computes only
 * over real captures of the same artifact; an export row carries no field
 * map, so no pair mints — the honest absence, never a fixture fallback).
 */
export function diffPairs(
  a: EvidenceArtifact,
): { from: ArtifactCaptureRow; to: ArtifactCaptureRow }[] {
  const caps = capturesOf(a).filter((c) => c.fields !== undefined);
  const pairs: { from: ArtifactCaptureRow; to: ArtifactCaptureRow }[] = [];
  for (let i = 0; i + 1 < caps.length; i += 1) {
    pairs.push({ from: caps[i]!, to: caps[i + 1]! });
  }
  return pairs;
}

/** The diff-route pair param (`<capA>..<capB>` — one path segment). */
export function diffPairParam(pair: { from: ArtifactCaptureRow; to: ArtifactCaptureRow }): string {
  return `${pair.from.capture_id}..${pair.to.capture_id}`;
}

/** Parse a `capA..capB` segment back into ids (last `..` wins — ids never
 *  contain `..`). */
export function parseDiffPair(param: string): [string, string] | null {
  const i = param.indexOf("..");
  if (i <= 0 || i + 2 >= param.length) return null;
  return [param.slice(0, i), param.slice(i + 2)];
}

/** The field-by-field diff between two captures' `fields` maps — the
 *  `diffCaptures` row shape (`Capture.fields` → `FieldChange`-compatible). */
export function diffFields(a: ArtifactCaptureRow, b: ArtifactCaptureRow): {
  field: string;
  from_value: unknown;
  to_value: unknown;
  from_date: string;
  to_date: string;
  changed: boolean;
}[] {
  const fields = [...new Set([...Object.keys(a.fields ?? {}), ...Object.keys(b.fields ?? {})])].sort();
  return fields.map((field) => {
    const from = a.fields?.[field] ?? null;
    const to = b.fields?.[field] ?? null;
    return {
      field,
      from_value: from,
      to_value: to,
      from_date: (a.retrieved_at ?? "").slice(0, 10),
      to_date: (b.retrieved_at ?? "").slice(0, 10),
      changed: from !== to,
    };
  });
}

// --- Facets + pagination --------------------------------------------------- //

export const EVIDENCE_PAGE_SIZE = 50;

export function pageCount(total: number): number {
  return Math.max(1, Math.ceil(total / EVIDENCE_PAGE_SIZE));
}

export function pageSlice<T>(items: readonly T[], page: number): T[] {
  return items.slice((page - 1) * EVIDENCE_PAGE_SIZE, page * EVIDENCE_PAGE_SIZE);
}

export function pageNumbers(total: number): number[] {
  return Array.from({ length: pageCount(total) }, (_, i) => i + 1);
}

/** The index order — source display name, then title, then id (stable). */
export function byArtifactIndex(a: EvidenceArtifact, b: EvidenceArtifact): number {
  return (
    (a.source_name ?? a.source).localeCompare(b.source_name ?? b.source) ||
    artifactTitle(a).localeCompare(artifactTitle(b)) ||
    a.artifact_id.localeCompare(b.artifact_id)
  );
}

/** One facet value a route mints for — a value that exists in the data only. */
export interface ArtifactFacet {
  /** The route's value segment (URL-safe). */
  id: string;
  label: string;
  items: number;
}

/** The source facet's URL segment — the artifact's `source` is a display
 *  string in fixtures and the registry id in the export; both slug to one
 *  URL-safe id (lowercase alnum tokens joined with `-`). */
export function sourceSlug(source: string): string {
  return asciiTokens(source).join("-") || "not-recorded";
}

export function sourceFacets(artifacts: readonly EvidenceArtifact[]): ArtifactFacet[] {
  const acc = new Map<string, ArtifactFacet>();
  for (const a of artifacts) {
    const id = sourceSlug(a.source);
    const row = acc.get(id) ?? {
      id,
      label: a.source_name ?? a.source,
      items: 0,
    };
    if (a.source_name) row.label = a.source_name;
    row.items += 1;
    acc.set(id, row);
  }
  return [...acc.values()].sort((x, y) => x.label.localeCompare(y.label) || x.id.localeCompare(y.id));
}

export function typeFacets(artifacts: readonly EvidenceArtifact[]): ArtifactFacet[] {
  const acc = new Map<string, ArtifactFacet>();
  for (const a of artifacts) {
    const row = acc.get(a.artifact_type) ?? {
      id: a.artifact_type,
      label: a.artifact_type.replace(/_/g, " "),
      items: 0,
    };
    row.items += 1;
    acc.set(a.artifact_type, row);
  }
  return [...acc.values()].sort((x, y) => x.label.localeCompare(y.label) || x.id.localeCompare(y.id));
}

export function laneFacets(artifacts: readonly EvidenceArtifact[]): ArtifactFacet[] {
  const acc = new Map<string, ArtifactFacet>();
  for (const a of artifacts) {
    const lane = a.lane ?? NOT_RECORDED;
    const row = acc.get(lane) ?? { id: lane, label: laneLabel(lane), items: 0 };
    row.items += 1;
    acc.set(lane, row);
  }
  return [...acc.values()].sort((x, y) => x.label.localeCompare(y.label) || x.id.localeCompare(y.id));
}

export function stateFacets(artifacts: readonly EvidenceArtifact[]): ArtifactFacet[] {
  const acc = new Map<string, ArtifactFacet>();
  for (const a of artifacts) {
    const s = artifactState(a);
    const row = acc.get(s) ?? { id: s, label: ARTIFACT_STATE_LABELS[s] ?? s, items: 0 };
    row.items += 1;
    acc.set(s, row);
  }
  return [...acc.values()].sort((x, y) => x.label.localeCompare(y.label) || x.id.localeCompare(y.id));
}

export const UNPLACED_PATH = "unplaced";

export function placeFacets(artifacts: readonly EvidenceArtifact[]): ArtifactFacet[] {
  const acc = new Map<string, ArtifactFacet>();
  for (const a of artifacts) {
    const key = a.place_key ?? UNPLACED_PATH;
    const row = acc.get(key) ?? {
      id: key,
      label: a.place_key ? placeDisplayName(a.place_key) : "Not yet placed",
      items: 0,
    };
    row.items += 1;
    acc.set(key, row);
  }
  return [...acc.values()].sort((x, y) => x.label.localeCompare(y.label) || x.id.localeCompare(y.id));
}

/** A display name from a K4 slug path's last segment (`oklahoma-city-4064000`
 *  → "Oklahoma City" — the GEOID tail drops, never shown). */
export function placeDisplayName(slugPath: string): string {
  const last = slugPath.split(PATH_SEP).at(-1) ?? slugPath;
  const stem = last.replace(/-\d+$/, "").replace(/-/g, " ").trim();
  if (!stem) return slugPath;
  return stem.replace(/\b\w/g, (c) => c.toUpperCase());
}

export function artifactsForSource(arts: readonly EvidenceArtifact[], id: string): EvidenceArtifact[] {
  return arts.filter((a) => sourceSlug(a.source) === id).sort(byArtifactIndex);
}
export function artifactsForType(arts: readonly EvidenceArtifact[], t: string): EvidenceArtifact[] {
  return arts.filter((a) => a.artifact_type === t).sort(byArtifactIndex);
}
export function artifactsForLane(arts: readonly EvidenceArtifact[], lane: string): EvidenceArtifact[] {
  return arts.filter((a) => (a.lane ?? NOT_RECORDED) === lane).sort(byArtifactIndex);
}
export function artifactsForState(arts: readonly EvidenceArtifact[], s: string): EvidenceArtifact[] {
  return arts.filter((a) => artifactState(a) === s).sort(byArtifactIndex);
}
export function artifactsForPlace(arts: readonly EvidenceArtifact[], path: string): EvidenceArtifact[] {
  return arts
    .filter((a) => (path === UNPLACED_PATH ? !a.place_key : a.place_key === path))
    .sort(byArtifactIndex);
}

/** Parse a facet rest-param (`<id>` or `<id>/page/<n>`) — mirrors the watch
 *  place route's own rule. */
export function parseFacetPath(raw: string): { id: string; page: number } | null {
  const m = /^(.*?)\/page\/(\d+)$/.exec(raw);
  const id = m ? m[1]! : raw;
  const page = m ? Math.max(1, Number.parseInt(m[2]!, 10)) : 1;
  return id ? { id, page } : null;
}

// --- Claims, contradictions, watch + task usage ---------------------------- //

/** The statements whose binding names this artifact (`capture.artifact_id`),
 *  sorted by predicate then claim id — the "claims supported" block. */
export function claimsForArtifact(
  statements: ReadonlyMap<string, StatementRow>,
  artifactId: string,
): StatementRow[] {
  return [...statements.values()]
    .filter((s) => s.capture?.artifact_id === artifactId)
    .sort((a, b) =>
      String(a.predicate_id ?? "").localeCompare(String(b.predicate_id ?? "")) ||
      a.claim_id.localeCompare(b.claim_id),
    );
}

/** Distinct contradiction ids touching the artifact's supported claims. */
export function artifactContradictions(
  statements: ReadonlyMap<string, StatementRow>,
  artifactId: string,
): string[] {
  const ids = new Set<string>();
  for (const s of claimsForArtifact(statements, artifactId)) {
    for (const c of s.contradictions?.contradiction_ids ?? []) ids.add(String(c));
    for (const c of s.contradictions?.competing_claim_ids ?? []) ids.add(String(c));
  }
  return [...ids].sort();
}

/** The S-6 upstream block's publication form — one closed mapping, the same
 *  the provenance panel applies (a `withheld_by_policy` block never links). */
export function artifactUpstream(a: EvidenceArtifact): { display: string; href: string | null } {
  const up = a.upstream ?? (a.upstream_url ? { status: "full_url", url: a.upstream_url } : null);
  const status = up?.status ?? NO_UPSTREAM_URL;
  if (status === "full_url" && up?.url) return { display: up.url, href: up.url };
  if (status === "host_only" && up?.host) {
    return {
      display: `${up.host}#path_sha256:${up.path_sha256 ?? NOT_RECORDED}`,
      href: `https://${up.host}/`,
    };
  }
  if (status === "withheld_by_policy") return { display: NOT_PUBLISHABLE, href: null };
  return { display: NO_UPSTREAM_URL, href: null };
}

/** The view-original cell for one capture row — the minted label + href, or
 *  the named absence when the row carries none (pre-P36.51 shape). */
export function captureViewOriginal(c: ArtifactCaptureRow): {
  label: string;
  href: string | null;
  note: string | null;
} {
  return {
    label: c.view_original?.label ?? NOT_RECORDED,
    href: c.view_original?.href ?? null,
    note: c.view_original?.note ?? null,
  };
}

// --- The hub's state-of-the-evidence roll-up ------------------------------- //

export interface EvidenceRollup {
  artifacts: number;
  runRecords: number;
  byClassification: ArtifactFacet[];
  byLane: ArtifactFacet[];
  byState: ArtifactFacet[];
  byType: ArtifactFacet[];
  bySource: ArtifactFacet[];
  byPlace: ArtifactFacet[];
  captures: number;
  capturesWithBytes: number;
  capturesRecorded: number;
}

/** The §4.1 "state of the evidence" counts — every number links its facet. */
export function evidenceRollup(artifacts: readonly EvidenceArtifact[]): EvidenceRollup {
  let captures = 0;
  let withBytes = 0;
  for (const a of artifacts) {
    for (const c of a.captures ?? []) {
      captures += 1;
      if ((c.byte_size ?? 0) > 0) withBytes += 1;
    }
  }
  return {
    artifacts: artifacts.length,
    runRecords: artifacts.filter((a) => artifactState(a) === "legacy_synthetic").length,
    byClassification: stateFacets(artifacts),
    byLane: laneFacets(artifacts),
    byState: stateFacets(artifacts),
    byType: typeFacets(artifacts),
    bySource: sourceFacets(artifacts),
    byPlace: placeFacets(artifacts),
    captures,
    capturesWithBytes: withBytes,
    capturesRecorded: captures,
  };
}

/** The reserved single-segment names under `/evidence/` — a claim id that
 *  collides with a facet namespace is a registry defect, not a stub. */
export const EVIDENCE_RESERVED_SEGMENTS = new Set([
  "page",
  "source",
  "type",
  "lane",
  "place",
  "state",
  "claim",
  "artifact",
  "index.json",
]);
