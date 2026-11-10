// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
/**
 * The `sig.entity-page/1` record contract — ticket P36.41 (K2 §4.2/§6.2,
 * R11-K13-GX-05a, contract A). The web-side mirror of
 * `exports/src/exports/entity_page.py`: the exporter owns the derivation;
 * this file carries the types, the page-state vocabulary and the committed
 * fixtures the fixtures-mode build and P36.42a's template consume. The
 * Python builder is the reference; a field added there lands here too, in
 * the same shape — never re-shaped.
 *
 * Contract A's page kinds are organisations, agencies and registry portals
 * (`PAGE_KINDS`); contract B (P37.22) extends the set and fills the 05b
 * sections (`contradictions`, `timeline`, `related`, `downloads`), which
 * contract A emits as typed empty values so the record shape is stable.
 *
 * The A-10 spine (D-K2-1 = b + c, ADR-159 — carried, never re-decided):
 * an organisation matched by the registry auto-allow ADR has a keyed twin
 * (`review_state: "published"`); every other organisation is typed
 * `not_yet_reviewed` — a typed state, never a silent absence, never a raw
 * identifier as a label (SIG-UI-053/080/108/110/114/115/116).
 */

import { withBase } from "./paths";

export const ENTITY_PAGE_SCHEMA = "sig.entity-page/1";

/** The paged kinds — contract A's E1 wave (organisations, agencies,
 *  portals) plus contract B's E2 wave (P37.22 / GX-05b: notices, contracts,
 *  grants, bills, legal instruments as `policy`, accountability events).
 *  `atlas` (E3) and `request` stay outside the 05b row. */
export const PAGE_KINDS = [
  "org",
  "agency",
  "portal",
  "notice",
  "contract",
  "grant",
  "bill",
  "policy",
  "event",
] as const;
export type PageKind = (typeof PAGE_KINDS)[number];

/** The A-10 page-state vocabulary (ADR-159's `label_state` renders here). */
export type EntityPageState = "published" | "not_yet_reviewed" | "withheld" | "unpaged";

/** SIG-UI-080's mandated sentence, verbatim — where the publication gate
 * withholds organisations or relationships. Never re-worded. */
export const WITHHELD_RELATIONSHIPS_NOTICE =
  "some relationships are not shown pending publication review";

/** The H-8 / SIG-UI-070 entity-resolution disclosure, verbatim — every
 * entity count carries it. */
export const ER_DISCLOSURE =
  "SIG has not merged organisations across sources; one agency can appear more than once";

/** K2 §4.2 row 5 — relationship groups over 50 rows show the first 50
 * plus grouped counts and the "all N" posture (`more`). */
export const ITEMS_PER_RELATION = 50;
export const CLAIM_IDS_PER_ITEM = 3;

// ---------------------------------------------------------------------------
// The label row (`sig.entity-label/1`, `labels/<comp>.jsonl`) — the fields
// the page contract reads (P35.29/P36.29 landed the artifact).
// ---------------------------------------------------------------------------

export interface EntityLabelRow {
  entity_id: string;
  sig_id?: string | null;
  kind: string;
  url_type?: string | null;
  label?: string | null;
  descriptor?: string | null;
  label_basis?: string | null;
  label_source_id?: string | null;
  place_jkey?: string | null;
  slug?: string | null;
  hash?: string | null;
  url?: string | null;
  disambiguator?: string | null;
  component_id?: string | null;
  part8?: string;
  subject_key?: string | null;
  /** ADR-159's typed state — `"not_yet_reviewed"` | `"withheld"` | absent. */
  label_state?: string;
}

/**
 * The A-10 page state for one label row — the same decision
 * `exports.entity_page.page_state` renders:
 * `published` (auto-allowed + keyed + a contract-A kind), `not_yet_reviewed`
 * (every other organisation — typed, never silent), `withheld` (no page, no
 * node, ever), `unpaged` (an allowed label outside contract A's kind set —
 * sibling scope, typed).
 */
export function pageState(row: Pick<EntityLabelRow, "kind" | "label_state" | "slug" | "hash" | "url_type" | "url">): EntityPageState {
  if (row.label_state === "withheld" || row.kind === "person") return "withheld";
  if (row.label_state === "not_yet_reviewed") return "not_yet_reviewed";
  if (!(PAGE_KINDS as readonly string[]).includes(row.kind)) return "unpaged";
  if (!(row.slug && row.hash && row.url_type && row.url)) return "not_yet_reviewed";
  return "published";
}

// ---------------------------------------------------------------------------
// Twin sections — the record fields K2 §6.2 names, contract A populated.
// ---------------------------------------------------------------------------

/** The four epistemic fields, always four separate fields (SIG-UI-004). */
export interface EntityEnvelope {
  status: string | null;
  support: string;
  agreement: string | null;
  currency: string | null;
  rationale?: string | null;
}

/** "What SIG records" — one predicate's resolved claim group (§4.2 row 4). */
export interface EntityClaimGroup {
  predicate: string;
  relation: string;
  envelope: EntityEnvelope;
  values: string[];
  observed_at: string | null;
  date_kind: "observed" | "undated";
  sources: { id: string; name?: string | null }[];
  claim_ids: string[];
}

/** A relationship counterparty — the shared label, a literal partner, or a
 * typed review state. A withheld partner never reaches an item (the row
 * drops whole and `withheld_notice` carries SIG-UI-080's sentence). */
export interface EntityCounterparty {
  entity_id?: string;
  kind?: string;
  label?: string | null;
  label_basis?: string | null;
  url?: string | null;
  key?: string | null;
  literal?: boolean;
  review_state?: string;
}

/** One relationship row — the H-2 fields (SIG-UI-115): relation in words,
 * direction, access kind, date + date kind or "undated", the four epistemic
 * fields, source names, and the supporting claim ids. Historical and undated
 * rows are marked (SIG-UI-088/116), never present-tense. */
export interface EntityRelationItem {
  counterparty: EntityCounterparty;
  relation: string;
  role: string | null;
  date: string | null;
  date_kind: "observed" | "undated";
  currency: string | null;
  status: string | null;
  support: string;
  agreement: string | null;
  sources: { id: string; name?: string | null }[];
  claim_ids: string[];
  historical: boolean;
}

/** One relationship group — per (relation, direction, access kind); the
 * three access kinds are never merged (SIG-UI-024). */
export interface EntityRelationGroup {
  relation: string;
  direction: "outbound" | "inbound" | string;
  access_kind: string | null;
  count: number;
  items: EntityRelationItem[];
  more: number;
  claim_ids: string[];
}

/** A degree-only fact — a source-stated partner COUNT carried as a node
 * attribute ("Shared with N — partners not named", SIG-INGEST-043c / H-4 /
 * SIG-UI-117). Never a relation item, never an edge. `sentences` carries
 * the D-K2-3 node-attribute sentences verbatim, one per stated count. */
export interface DegreeOnlyFact {
  predicate: string;
  counts: number[];
  sentences: string[];
  claim_ids: string[];
  observed_at: string | null;
  date_kind: "observed" | "undated";
  currency: string | null;
  historical: boolean;
  sources: { id: string; name?: string | null }[];
}

/** One hop in an access closure — the AccessEdge projection with the shared
 * counterparty views and the per-hop evidence (claim ids + sources). The
 * endpoints are rendered through the label registry, never as raw ids. */
export interface AccessClosureHop {
  from_org: string;
  to_org: string;
  edge_label: string;
  scope: string;
  confidence: string;
  evidence: string[];
  edge_id: string;
  asserted_by: string;
  valid_from: string | null;
  valid_to: string | null;
  valid_from_kind: string;
  valid_to_kind: string;
  from: EntityCounterparty;
  to: EntityCounterparty;
  sources: { id: string; name?: string | null }[];
}

/** One derived reachability path (GX-07 / P37.21). Always multi-hop — a
 * one-hop path is the direct edge, already a relationship row. Carries the
 * full hop list and every safety label (SIG-RECON-049/050): `speculative`
 * beyond the published hop threshold, `temporal_status` "live" vs
 * "historical" through an expired hop. `direction` is relative to the page
 * entity: "inbound" answers "who can reach this entity's data" (the
 * accessor sits at `source`), "outbound" answers "whose data it can reach". */
export interface AccessClosurePath {
  source: string;
  target: string;
  direction: "inbound" | "outbound" | string;
  hop_count: number;
  confidence: string;
  scope: string;
  temporal_status: "live" | "historical" | string;
  speculative: boolean;
  is_headline: boolean;
  hops: AccessClosureHop[];
  rationale: string;
  claim_ids: string[];
  source_party: EntityCounterparty;
  target_party: EntityCounterparty;
}

/** The closure group for one direction (GX-07). `counts.publishable` = live
 * and ≤ the speculative threshold; `more` is the emitted-cap remainder and
 * `path_count` the true total — never a smoothed count (D-K2-2 = a:
 * descriptive only; no centrality or rankings). */
export interface AccessClosureGroup {
  direction: "inbound" | "outbound" | string;
  question: string;
  as_of: string;
  counts: { publishable: number; historical: number; speculative: number };
  path_count: number;
  paths: AccessClosurePath[];
  more: number;
}

// ---------------------------------------------------------------------------
// Contract-B sections (P37.22 / GX-05b, K2 §4.2 rows 8/9/11/12).
// ---------------------------------------------------------------------------

/** One timeline entry (§4.2 row 9): a stated event date, a record
 *  observation, or a per-source first/last sighting. `date` is the strict
 *  ISO day the entry draws at; `date_kind: "undated"` items are listed
 *  apart, never placed on the axis and never present-tense (SIG-UI-116). */
export interface EntityTimelineEntry {
  kind: "stated" | "observed" | "first_seen" | "last_seen" | string;
  date: string | null;
  date_kind: "observed" | "undated" | string;
  label: string;
  predicate?: string | null;
  claim_ids: string[];
  sources: { id: string; name?: string | null }[];
}

/** One contradiction record (§4.2 row 8, H-7): a materialized §31
 *  contradiction the entity's record touches (`kind: "contradiction"`) or
 *  a predicate-level conflict the resolution envelope records
 *  (`kind: "envelope_conflict"`). Both sides' claim ids stay listed —
 *  visible, never silently reconciled (SIG-UI-009). */
export interface EntityContradiction {
  kind: "contradiction" | "envelope_conflict" | string;
  contradiction_id: string | null;
  predicate: string;
  relation: string;
  type: string | null;
  status: string | null;
  severity: string | null;
  agreement?: string | null;
  claim_ids: string[];
  sources: { id: string; name?: string | null }[];
}

/** The `related` section (§4.2 row 11): dossier links (the recorded
 *  place's K4 key), the sources the entity's claims cite (K10 pages),
 *  research-queue tasks naming the entity (K11 handles), and the evidence
 *  documents bound to its claims (K8; the page resolves the artifact
 *  handle through its evidence map). `watch` stays typed-empty — no
 *  entity-scoped watch seam exists in this contract wave. */
export interface EntityRelated {
  dossiers: {
    jkey: string;
    slug_path: string;
    name?: string | null;
    level?: string | null;
    url: string;
  }[];
  sources: { id: string; name?: string | null; url: string }[];
  tasks: {
    task_id: string | null;
    handle: string | null;
    title?: string | null;
    task_type: string | null;
    status: string | null;
    url: string | null;
  }[];
  watch: unknown[];
  documents: {
    artifact_id: string;
    title?: string | null;
    artifact_type?: string | null;
    source_id?: string | null;
    source_name?: string | null;
    claim_ids: string[];
  }[];
}

/** One downloads entry (§4.2 row 12, J3 TX-10): names a file this export
 *  actually emitted under `entity/<url_type>/<key>/` — never a file that
 *  was not emitted. */
export interface EntityDownload {
  kind: "twin" | "statements" | "relationships" | string;
  format: "json" | "jsonl" | "csv" | string;
  path: string;
  compartment: string;
  label: string;
}

/** A mechanical summary line — every number carries its group and claim
 * pointers (the `<Figure>` input; K2 §4.2 row 2). */
export interface EntitySummaryLine {
  text: string;
  value: number;
  relation: string;
  direction: string;
  claim_ids: string[];
}

/** The published `sig.entity-page/1` twin — emitted per licence compartment
 * at `entity/<url_type>/<slug>--<hash>/index.<comp>.json` under the export's
 * `web/` tree (SIG-EXPORT-014). */
export interface EntityPageTwin {
  schema: typeof ENTITY_PAGE_SCHEMA;
  review_state: "published";
  key: string;
  entity_id: string;
  sig_id?: string | null;
  kind: string;
  url_type: string;
  url: string;
  label: string;
  descriptor?: string | null;
  label_basis?: string | null;
  label_source_id?: string | null;
  place_jkey?: string | null;
  disambiguator?: string | null;
  publication: string;
  generated_at: string;
  compartment: string;
  identifiers: { scheme: string; value: string }[];
  summary: EntitySummaryLine[];
  claims: EntityClaimGroup[];
  relations: EntityRelationGroup[];
  access: {
    /** The GX-07 closures (P37.21) — per-direction groups; empty when the
     * entity's graph yields no multi-hop path. */
    closures: AccessClosureGroup[];
    degree_only: DegreeOnlyFact[];
  };
  /** Contract-B sections (P37.22) — populated under contract B; a section
   *  with no evidenced content keeps its typed empty value. */
  contradictions: EntityContradiction[];
  timeline: EntityTimelineEntry[];
  related: EntityRelated;
  downloads: EntityDownload[];
  cite: {
    publication: string;
    url: string | null;
    record_url: string | null;
    sig_id: string | null;
  };
  /** SIG-UI-080's sentence where the gate withheld a counterparty, else null. */
  withheld_notice: string | null;
  er_disclosure: string;
}

/** The typed `not_yet_reviewed` record for an un-keyed organisation —
 * the state IS the record (no label, slug, hash, URL or entity id). */
export interface EntityReviewRecord {
  schema: typeof ENTITY_PAGE_SCHEMA;
  review_state: "not_yet_reviewed";
  kind: string;
  descriptor?: string | null;
  er_disclosure: string;
}

/** The typed review record one label row produces — the mirror of
 * `exports.entity_page.review_record`. */
export function reviewRecord(row: Pick<EntityLabelRow, "kind" | "descriptor">): EntityReviewRecord {
  return {
    schema: ENTITY_PAGE_SCHEMA,
    review_state: "not_yet_reviewed",
    kind: row.kind,
    descriptor: row.descriptor ?? undefined,
    er_disclosure: ER_DISCLOSURE,
  };
}

// ---------------------------------------------------------------------------
// Validation — structural, fail-closed (SIG-ENG-042).
// ---------------------------------------------------------------------------

function isObj(v: unknown): v is Record<string, unknown> {
  return typeof v === "object" && v !== null && !Array.isArray(v);
}

/** True iff `doc` is a well-formed published `sig.entity-page/1` twin. */
export function isEntityPageTwin(doc: unknown): doc is EntityPageTwin {
  if (!isObj(doc)) return false;
  if (doc.schema !== ENTITY_PAGE_SCHEMA) return false;
  if (doc.review_state !== "published") return false;
  if (typeof doc.key !== "string" || typeof doc.entity_id !== "string") return false;
  if (typeof doc.label !== "string" || doc.label === "") return false;
  if (!Array.isArray(doc.claims) || !Array.isArray(doc.relations)) return false;
  if (!isObj(doc.access) || !Array.isArray(doc.access.degree_only)) return false;
  if (!Array.isArray(doc.access.closures)) return false;
  if (!isObj(doc.cite)) return false;
  // Contract-B sections — the stable record shape (typed-empty or
  // populated; a missing slot is a malformed twin, fail closed).
  if (!Array.isArray(doc.contradictions) || !Array.isArray(doc.timeline)) return false;
  if (!Array.isArray(doc.downloads)) return false;
  if (!isObj(doc.related)) return false;
  if (!Array.isArray(doc.related.dossiers) || !Array.isArray(doc.related.sources)) return false;
  if (!Array.isArray(doc.related.tasks) || !Array.isArray(doc.related.documents)) return false;
  return true;
}

/** True iff `doc` is a typed `not_yet_reviewed` record. */
export function isReviewRecord(doc: unknown): doc is EntityReviewRecord {
  return (
    isObj(doc) &&
    doc.schema === ENTITY_PAGE_SCHEMA &&
    doc.review_state === "not_yet_reviewed" &&
    typeof doc.kind === "string"
  );
}

/**
 * The `/entity/` hub's per-kind index (SIG-UI-070): published entity types
 * with counts — keyed label rows only — plus every review-state row so the
 * A–Z list can render the typed `not_yet_reviewed` state. Counts carry the
 * ER disclosure verbatim; a withheld row never reaches the index.
 */
export interface EntityIndex {
  kinds: { kind: string; count: number; er_disclosure: string }[];
  rows: EntityLabelRow[];
  review_rows: EntityReviewRecord[];
}

export function entityIndex(rows: readonly EntityLabelRow[]): EntityIndex {
  const counts = new Map<string, number>();
  const pageRows: EntityLabelRow[] = [];
  const reviewRows: EntityReviewRecord[] = [];
  for (const row of rows) {
    const state = pageState(row);
    if (state === "published") {
      pageRows.push(row);
      counts.set(row.kind, (counts.get(row.kind) ?? 0) + 1);
    } else if (state === "not_yet_reviewed") {
      reviewRows.push(reviewRecord(row));
    }
    // withheld and unpaged rows are absent from the index — typed, never silent
  }
  return {
    kinds: [...counts.entries()]
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([kind, count]) => ({ kind, count, er_disclosure: ER_DISCLOSURE })),
    rows: pageRows.sort(
      (a, b) =>
        String(a.label ?? "").localeCompare(String(b.label ?? "")) ||
        a.entity_id.localeCompare(b.entity_id),
    ),
    review_rows: reviewRows,
  };
}

