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

// ---------------------------------------------------------------------------
// The committed fixtures (SIG-UI-036: invented, honest data — every key below
// is the invented-entity shape the real derivation produces; the A-10 fixture
// pair exercises the operator's answered decision verbatim: an auto-allowed
// agency renders its twin; an organisation outside the auto-allow registry
// renders the typed `not_yet_reviewed` state, never a silent absence).
//
// Path note (P35.65): the emitted artifact's `url`/`record_url` fields are
// root-absolute paths (policy.labels.entity_url → `/entity/<type>/<key>/`).
// The fixtures build those bytes through `withBase()` with a sans-slash
// argument — the pinned construction seam — so the containment check
// (check-root-absolute-paths.mjs) sees no new root-absolute literal while
// the runtime value stays byte-identical under the default root base.
// ---------------------------------------------------------------------------

/** The fixture mirror of `policy.labels.entity_url` — `<slug>--<hash>`
 * joined under `entity/<url_type>/`, through `withBase()`. */
function fixtureEntityUrl(urlType: string, slug: string, hash: string): string {
  return withBase(`entity/${urlType}/${slug}--${hash}/`);
}

/** Invented label-registry rows: one auto-allowed agency (keyed twin), one
 * allowed portal, and one organisation outside the auto-allow registry. */
export const ENTITY_LABEL_FIXTURES: EntityLabelRow[] = [
  {
    entity_id: "0190cafe-0000-7000-8000-0000000000a1",
    sig_id: "sig:agency:0190cafe-0000-7000-8000-0000000000a1",
    kind: "agency",
    url_type: "agency",
    label: "Acworth Police Department",
    descriptor: "Government body · usa-ga",
    label_basis: "source_name",
    label_source_id: "eff_data_driven",
    place_jkey: "usa-ga",
    slug: "acworth-police-department",
    hash: "4g2wm8q",
    url: fixtureEntityUrl("agency", "acworth-police-department", "4g2wm8q"),
    disambiguator: null,
    component_id: "comp-1",
    part8: "pass",
    subject_key: "agency:acworth-pd",
  },
  {
    entity_id: "0190cafe-0000-7000-8000-0000000000b2",
    sig_id: "sig:org:0190cafe-0000-7000-8000-0000000000b2",
    kind: "org",
    url_type: "org",
    label: "Vigilant Solutions (LEARN)",
    descriptor: "Organisation",
    label_basis: "source_name",
    label_source_id: "eff_data_driven",
    place_jkey: null,
    slug: "vigilant-solutions-learn",
    hash: "7xk3mrt",
    url: fixtureEntityUrl("org", "vigilant-solutions-learn", "7xk3mrt"),
    disambiguator: null,
    component_id: "comp-1",
    part8: "pass",
    subject_key: "organization:vigilant-solutions",
  },
  {
    entity_id: "0190cafe-0000-7000-8000-0000000000c3",
    sig_id: "sig:portal:0190cafe-0000-7000-8000-0000000000c3",
    kind: "portal",
    url_type: "portal",
    label: "Acworth PD transparency portal",
    descriptor: "Registry portal · usa-ga",
    label_basis: "source_title",
    label_source_id: "eyes_on_flock",
    place_jkey: "usa-ga",
    slug: "acworth-pd-transparency-portal",
    hash: "2rn6vqw",
    url: fixtureEntityUrl("portal", "acworth-pd-transparency-portal", "2rn6vqw"),
    disambiguator: null,
    component_id: "comp-1",
    part8: "pass",
    subject_key: "platform:acworth-pd-portal",
  },
  {
    // A-10 c: an organisation NOT matched by the registry auto-allow ADR —
    // no key is issued, the typed `not_yet_reviewed` state is the record.
    entity_id: "0190cafe-0000-7000-8000-0000000000d4",
    sig_id: "sig:org:0190cafe-0000-7000-8000-0000000000d4",
    kind: "org",
    url_type: "org",
    label: null,
    descriptor: "Organisation",
    label_basis: null,
    label_source_id: null,
    place_jkey: null,
    slug: null,
    hash: null,
    url: null,
    disambiguator: null,
    component_id: null,
    part8: "pass",
    subject_key: "organization:unverified-partner-llc",
    label_state: "not_yet_reviewed",
  },
  {
    // Contract B (P37.23 / GX-06b): a keyed procurement-record entity — the
    // E2 record wave's buyer/seller page surface.
    entity_id: "0190cafe-0000-7000-8000-0000000000e7",
    sig_id: "sig:contract:0190cafe-0000-7000-8000-0000000000e7",
    kind: "contract",
    url_type: "contract",
    label: "Acworth ALPR expansion contract",
    descriptor: "Procurement record · usa-ga",
    label_basis: "derived",
    label_source_id: "demo_permitted_portal",
    place_jkey: "usa-ga",
    slug: "acworth-alpr-expansion-contract",
    hash: "9p4kxwd",
    url: fixtureEntityUrl("contract", "acworth-alpr-expansion-contract", "9p4kxwd"),
    disambiguator: null,
    component_id: "comp-1",
    part8: "pass",
    subject_key: "contract:acworth-alpr-expansion-2020",
  },
  {
    // Contract B (P37.23 / GX-06b): a keyed legal-instrument entity — the
    // record wave's adopted-by surface; no place is recorded, so the map
    // snippet exercises its typed state.
    entity_id: "0190cafe-0000-7000-8000-0000000000f8",
    sig_id: "sig:policy:0190cafe-0000-7000-8000-0000000000f8",
    kind: "policy",
    url_type: "policy",
    label: "Acworth surveillance oversight ordinance 2020-14",
    descriptor: "Policy or ordinance",
    label_basis: "source_title",
    label_source_id: "okc_council_minutes",
    place_jkey: null,
    slug: "acworth-surveillance-oversight-ordinance-2020-14",
    hash: "5t8mvjq",
    url: fixtureEntityUrl(
      "policy",
      "acworth-surveillance-oversight-ordinance-2020-14",
      "5t8mvjq",
    ),
    disambiguator: null,
    component_id: "comp-1",
    part8: "pass",
    subject_key: "ordinance:acworth-2020-14",
  },
];

/** The published twin for the auto-allowed agency — relations both ways,
 * an access-kind edge marked historical, a degree-only fact, and the
 * withheld-counterparty notice (a partner org pending review). */
export const ENTITY_PAGE_TWIN_FIXTURE: EntityPageTwin = {
  schema: ENTITY_PAGE_SCHEMA,
  review_state: "published",
  key: "acworth-police-department--4g2wm8q",
  entity_id: "0190cafe-0000-7000-8000-0000000000a1",
  sig_id: "sig:agency:0190cafe-0000-7000-8000-0000000000a1",
  kind: "agency",
  url_type: "agency",
  url: fixtureEntityUrl("agency", "acworth-police-department", "4g2wm8q"),
  label: "Acworth Police Department",
  descriptor: "Government body · usa-ga",
  label_basis: "source_name",
  label_source_id: "eff_data_driven",
  place_jkey: "usa-ga",
  disambiguator: null,
  publication: "sig-release-2026.09",
  generated_at: "2026-09-01T00:00:00Z",
  compartment: "sig_graph",
  identifiers: [
    { scheme: "us.cgac.agency_code", value: "GA-ACWORTH-PD" },
    { scheme: "sig.connector.subject", value: "agency:acworth-pd" },
  ],
  summary: [
    {
      text: "1 recorded outbound relationship — configured sharing partner",
      value: 1,
      relation: "configured sharing partner",
      direction: "outbound",
      claim_ids: ["clm-apd-vigilant-1"],
    },
    {
      text: "3 recorded inbound relationships — camera operator",
      value: 3,
      relation: "camera operator",
      direction: "inbound",
      claim_ids: ["clm-cam-12", "clm-cam-34", "clm-cam-56"],
    },
  ],
  claims: [
    {
      predicate: "agency_name",
      relation: "agency name",
      envelope: {
        status: "resolved",
        support: "WEAKLY_SUPPORTED",
        agreement: "UNCONTESTED",
        currency: "CURRENT",
        rationale: null,
      },
      values: ["Acworth Police Department"],
      observed_at: "2020-01-28",
      date_kind: "observed",
      sources: [{ id: "eff_data_driven", name: "EFF Data Driven" }],
      claim_ids: ["clm-apd-name-1"],
    },
  ],
  relations: [
    {
      relation: "configured sharing partner",
      direction: "outbound",
      access_kind: "configured_access",
      count: 1,
      items: [
        {
          counterparty: {
            entity_id: "0190cafe-0000-7000-8000-0000000000b2",
            kind: "org",
            label: "Vigilant Solutions (LEARN)",
            label_basis: "source_name",
            url: fixtureEntityUrl("org", "vigilant-solutions-learn", "7xk3mrt"),
            key: "vigilant-solutions-learn--7xk3mrt",
          },
          relation: "configured sharing partner",
          role: "configured_sharing_partner",
          date: "2020-01-28",
          date_kind: "observed",
          currency: "HISTORICAL",
          status: "unresolved",
          support: "WEAKLY_SUPPORTED",
          agreement: "UNCONTESTED",
          sources: [{ id: "eff_data_driven", name: "EFF Data Driven" }],
          claim_ids: ["clm-apd-vigilant-1"],
          historical: true,
        },
      ],
      more: 0,
      claim_ids: ["clm-apd-vigilant-1"],
    },
    {
      relation: "camera operator",
      direction: "inbound",
      access_kind: null,
      count: 3,
      items: [
        {
          counterparty: {
            entity_id: "0190cafe-0000-7000-8000-0000000000e5",
            kind: "site",
            label: "surveillance camera in usa-ga",
            label_basis: "derived",
            url: null,
            key: null,
          },
          relation: "camera operator",
          role: "camera_operator",
          date: null,
          date_kind: "undated",
          currency: "UNDATED",
          status: null,
          support: "WEAKLY_SUPPORTED",
          agreement: null,
          sources: [{ id: "dot_511_ga", name: "Georgia 511" }],
          claim_ids: ["clm-cam-12"],
          historical: false,
        },
      ],
      more: 2,
      claim_ids: ["clm-cam-12", "clm-cam-34", "clm-cam-56"],
    },
  ],
  access: {
    // GX-07 (P37.21) — a 2-hop outbound closure over the fixture's
    // configured-access chain, per-hop evidence + party views intact.
    closures: [
      {
        direction: "outbound",
        question: "whose data this entity can reach",
        as_of: "2026-09-01",
        counts: { publishable: 1, historical: 0, speculative: 0 },
        path_count: 1,
        more: 0,
        paths: [
          {
            source: "0190cafe-0000-7000-8000-0000000000a1",
            target: "0190cafe-0000-7000-8000-0000000000f6",
            direction: "outbound",
            hop_count: 2,
            confidence: "probable",
            scope: "partner",
            temporal_status: "live",
            speculative: false,
            is_headline: true,
            rationale:
              "… can reach … via 2 hop(s); confidence is the path minimum; scope is the narrowest hop.",
            claim_ids: ["clm-apd-vigilant-1", "clm-vig-lookup-1"],
            source_party: {
              entity_id: "0190cafe-0000-7000-8000-0000000000a1",
              kind: "agency",
              label: "Acworth Police Department",
              label_basis: "source_name",
              url: fixtureEntityUrl("agency", "acworth-police-department", "4g2wm8q"),
              key: "acworth-police-department--4g2wm8q",
            },
            target_party: {
              entity_id: "0190cafe-0000-7000-8000-0000000000f6",
              kind: "portal",
              label: "Multi-state LEARN lookup pool",
              label_basis: "source_name",
              url: null,
              key: null,
            },
            hops: [
              {
                from_org: "0190cafe-0000-7000-8000-0000000000a1",
                to_org: "0190cafe-0000-7000-8000-0000000000b2",
                edge_label: "configured_access",
                scope: "partner",
                confidence: "probable",
                evidence: ["clm-apd-vigilant-1"],
                edge_id: "rel-fixture-1",
                asserted_by: "0190cafe-0000-7000-8000-0000000000a1",
                valid_from: null,
                valid_to: null,
                valid_from_kind: "unknown",
                valid_to_kind: "ongoing",
                from: {
                  entity_id: "0190cafe-0000-7000-8000-0000000000a1",
                  kind: "agency",
                  label: "Acworth Police Department",
                  label_basis: "source_name",
                  url: fixtureEntityUrl("agency", "acworth-police-department", "4g2wm8q"),
                  key: "acworth-police-department--4g2wm8q",
                },
                to: {
                  entity_id: "0190cafe-0000-7000-8000-0000000000b2",
                  kind: "org",
                  label: "Vigilant Solutions (LEARN)",
                  label_basis: "source_name",
                  url: fixtureEntityUrl("org", "vigilant-solutions-learn", "7xk3mrt"),
                  key: "vigilant-solutions-learn--7xk3mrt",
                },
                sources: [{ id: "eff_data_driven", name: "EFF Data Driven" }],
              },
              {
                from_org: "0190cafe-0000-7000-8000-0000000000b2",
                to_org: "0190cafe-0000-7000-8000-0000000000f6",
                edge_label: "configured_access",
                scope: "partner",
                confidence: "probable",
                evidence: ["clm-vig-lookup-1"],
                edge_id: "rel-fixture-2",
                asserted_by: "0190cafe-0000-7000-8000-0000000000b2",
                valid_from: null,
                valid_to: null,
                valid_from_kind: "unknown",
                valid_to_kind: "ongoing",
                from: {
                  entity_id: "0190cafe-0000-7000-8000-0000000000b2",
                  kind: "org",
                  label: "Vigilant Solutions (LEARN)",
                  label_basis: "source_name",
                  url: fixtureEntityUrl("org", "vigilant-solutions-learn", "7xk3mrt"),
                  key: "vigilant-solutions-learn--7xk3mrt",
                },
                to: {
                  entity_id: "0190cafe-0000-7000-8000-0000000000f6",
                  kind: "portal",
                  label: "Multi-state LEARN lookup pool",
                  label_basis: "source_name",
                  url: null,
                  key: null,
                },
                sources: [{ id: "eff_data_driven", name: "EFF Data Driven" }],
              },
            ],
          },
        ],
      },
    ],
    degree_only: [
      {
        predicate: "sharing_partner_degree",
        counts: [851],
        sentences: ["Shared with 851 agencies — partners not named"],
        claim_ids: ["clm-apd-degree-1"],
        observed_at: "2020-01-28",
        date_kind: "observed",
        currency: "HISTORICAL",
        historical: true,
        sources: [{ id: "eff_data_driven", name: "EFF Data Driven" }],
      },
    ],
  },
  // Contract-B sections (P37.22) — populated: one materialized
  // contradiction, a stated date + record observations + first/last seen,
  // the related dossier/source/task, and the emitted download files.
  contradictions: [
    {
      kind: "contradiction",
      contradiction_id: "contra-fixture-1",
      predicate: "configured_sharing_partner",
      relation: "configured sharing partner",
      type: "value_conflict",
      status: "open",
      severity: "moderate",
      claim_ids: ["clm-apd-vigilant-1", "clm-apd-vigilant-2"],
      sources: [{ id: "eff_data_driven", name: "EFF Data Driven" }],
    },
  ],
  timeline: [
    {
      kind: "stated",
      date: "2020-01-28",
      date_kind: "observed",
      label: "posted date",
      predicate: "posted_date",
      claim_ids: ["clm-apd-posted-1"],
      sources: [{ id: "eff_data_driven", name: "EFF Data Driven" }],
    },
    {
      kind: "observed",
      date: "2020-01-28",
      date_kind: "observed",
      label: "configured sharing partner — Vigilant Solutions (LEARN)",
      predicate: "configured_sharing_partner",
      claim_ids: ["clm-apd-vigilant-1"],
      sources: [{ id: "eff_data_driven", name: "EFF Data Driven" }],
    },
    {
      kind: "first_seen",
      date: "2020-01-28",
      date_kind: "observed",
      label: "first seen — EFF Data Driven",
      predicate: null,
      claim_ids: ["clm-apd-vigilant-1"],
      sources: [{ id: "eff_data_driven", name: "EFF Data Driven" }],
    },
    {
      kind: "observed",
      date: null,
      date_kind: "undated",
      label: "camera operator — surveillance camera in usa-ga",
      predicate: "camera_operator",
      claim_ids: ["clm-cam-12"],
      sources: [{ id: "dot_511_ga", name: "Georgia 511" }],
    },
  ],
  related: {
    dossiers: [
      {
        jkey: "usa-ga",
        slug_path: "usa/ga",
        name: "Georgia",
        level: "admin1",
        url: withBase("dossier/usa/ga/"),
      },
    ],
    sources: [
      { id: "eff_data_driven", name: "EFF Data Driven", url: withBase("sources/eff_data_driven/") },
      { id: "dot_511_ga", name: "Georgia 511", url: withBase("sources/dot_511_ga/") },
    ],
    tasks: [
      {
        task_id: "task-fixture-1",
        handle: "T-usa-ga-alpr-acworth-pd-q1c4",
        title: "Confirm the current sharing partner list",
        task_type: "verify_partner_list",
        status: "generated",
        url: withBase("task/T-usa-ga-alpr-acworth-pd-q1c4/"),
      },
    ],
    watch: [],
    documents: [
      {
        artifact_id: "art-fixture-1",
        title: "EFF Data Driven 2020 export",
        artifact_type: "dataset",
        source_id: "eff_data_driven",
        source_name: "EFF Data Driven",
        claim_ids: ["clm-apd-vigilant-1"],
      },
    ],
  },
  downloads: [
    {
      kind: "twin",
      format: "json",
      path: `entity/agency/acworth-police-department--4g2wm8q/index.sig_graph.json`,
      compartment: "sig_graph",
      label: "JSON twin (sig.entity-page/1)",
    },
    {
      kind: "relationships",
      format: "csv",
      path: `entity/agency/acworth-police-department--4g2wm8q/relationships.sig_graph.csv`,
      compartment: "sig_graph",
      label: "Relationships CSV",
    },
    {
      kind: "relationships",
      format: "json",
      path: `entity/agency/acworth-police-department--4g2wm8q/relationships.sig_graph.json`,
      compartment: "sig_graph",
      label: "Relationships JSON",
    },
    {
      kind: "statements",
      format: "jsonl",
      path: `entity/agency/acworth-police-department--4g2wm8q/statements.sig_graph.jsonl`,
      compartment: "sig_graph",
      label: "Statements (sig.statement/1)",
    },
  ],
  cite: {
    publication: "sig-release-2026.09",
    url: fixtureEntityUrl("agency", "acworth-police-department", "4g2wm8q"),
    record_url: withBase(
      "r/sig-release-2026.09/c/sig_graph/entity/agency/0190cafe-0000-7000-8000-0000000000a1/",
    ),
    sig_id: "sig:agency:0190cafe-0000-7000-8000-0000000000a1",
  },
  withheld_notice: WITHHELD_RELATIONSHIPS_NOTICE,
  er_disclosure: ER_DISCLOSURE,
};

/** The published twin for the contract-B procurement record (P37.23 /
 *  GX-06b) — buyer + seller relations to the wave-A entities, stated
 *  posted/signed dates, an envelope conflict on the contract value, and
 *  the recorded place drawing the map snippet. */
export const ENTITY_PAGE_TWIN_CONTRACT_FIXTURE: EntityPageTwin = {
  schema: ENTITY_PAGE_SCHEMA,
  review_state: "published",
  key: "acworth-alpr-expansion-contract--9p4kxwd",
  entity_id: "0190cafe-0000-7000-8000-0000000000e7",
  sig_id: "sig:contract:0190cafe-0000-7000-8000-0000000000e7",
  kind: "contract",
  url_type: "contract",
  url: fixtureEntityUrl("contract", "acworth-alpr-expansion-contract", "9p4kxwd"),
  label: "Acworth ALPR expansion contract",
  descriptor: "Procurement record · usa-ga",
  label_basis: "derived",
  label_source_id: "demo_permitted_portal",
  place_jkey: "usa-ga",
  disambiguator: null,
  publication: "sig-release-2026.09",
  generated_at: "2026-09-01T00:00:00Z",
  compartment: "sig_graph",
  identifiers: [
    { scheme: "sig.connector.subject", value: "contract:acworth-alpr-expansion-2020" },
  ],
  summary: [
    {
      text: "2 recorded outbound relationships — contract parties",
      value: 2,
      relation: "contract parties",
      direction: "outbound",
      claim_ids: ["clm-contract-buyer-1", "clm-contract-seller-1"],
    },
  ],
  claims: [
    {
      predicate: "contract_value",
      relation: "contract value",
      envelope: {
        status: "resolved",
        support: "WEAKLY_SUPPORTED",
        agreement: "CONTESTED",
        currency: "CURRENT",
        rationale: null,
      },
      values: ["$412,700", "$421,700"],
      observed_at: "2020-01-28",
      date_kind: "observed",
      sources: [{ id: "demo_permitted_portal", name: "Demo permitted portal" }],
      claim_ids: ["clm-contract-value-1", "clm-contract-value-2"],
    },
  ],
  relations: [
    {
      relation: "contract buyer",
      direction: "outbound",
      access_kind: null,
      count: 1,
      items: [
        {
          counterparty: {
            entity_id: "0190cafe-0000-7000-8000-0000000000a1",
            kind: "agency",
            label: "Acworth Police Department",
            label_basis: "source_name",
            url: fixtureEntityUrl("agency", "acworth-police-department", "4g2wm8q"),
            key: "acworth-police-department--4g2wm8q",
          },
          relation: "contract buyer",
          role: "buyer",
          date: "2020-01-28",
          date_kind: "observed",
          currency: "CURRENT",
          status: "resolved",
          support: "WEAKLY_SUPPORTED",
          agreement: "UNCONTESTED",
          sources: [{ id: "demo_permitted_portal", name: "Demo permitted portal" }],
          claim_ids: ["clm-contract-buyer-1"],
          historical: false,
        },
      ],
      more: 0,
      claim_ids: ["clm-contract-buyer-1"],
    },
    {
      relation: "contract seller",
      direction: "outbound",
      access_kind: null,
      count: 1,
      items: [
        {
          counterparty: {
            entity_id: "0190cafe-0000-7000-8000-0000000000b2",
            kind: "org",
            label: "Vigilant Solutions (LEARN)",
            label_basis: "source_name",
            url: fixtureEntityUrl("org", "vigilant-solutions-learn", "7xk3mrt"),
            key: "vigilant-solutions-learn--7xk3mrt",
          },
          relation: "contract seller",
          role: "seller",
          date: "2020-01-28",
          date_kind: "observed",
          currency: "CURRENT",
          status: "resolved",
          support: "WEAKLY_SUPPORTED",
          agreement: "UNCONTESTED",
          sources: [{ id: "demo_permitted_portal", name: "Demo permitted portal" }],
          claim_ids: ["clm-contract-seller-1"],
          historical: false,
        },
      ],
      more: 0,
      claim_ids: ["clm-contract-seller-1"],
    },
  ],
  access: { closures: [], degree_only: [] },
  contradictions: [
    {
      kind: "envelope_conflict",
      contradiction_id: null,
      predicate: "contract_value",
      relation: "contract value",
      type: "value_conflict",
      status: "open",
      severity: null,
      agreement: "CONTESTED",
      claim_ids: ["clm-contract-value-1", "clm-contract-value-2"],
      sources: [{ id: "demo_permitted_portal", name: "Demo permitted portal" }],
    },
  ],
  timeline: [
    {
      kind: "stated",
      date: "2020-01-15",
      date_kind: "observed",
      label: "posted date",
      predicate: "posted_date",
      claim_ids: ["clm-contract-posted-1"],
      sources: [{ id: "demo_permitted_portal", name: "Demo permitted portal" }],
    },
    {
      kind: "stated",
      date: "2020-01-28",
      date_kind: "observed",
      label: "signed date",
      predicate: "signed_date",
      claim_ids: ["clm-contract-signed-1"],
      sources: [{ id: "demo_permitted_portal", name: "Demo permitted portal" }],
    },
    {
      kind: "first_seen",
      date: "2020-02-03",
      date_kind: "observed",
      label: "first seen — Demo permitted portal",
      predicate: null,
      claim_ids: ["clm-contract-buyer-1"],
      sources: [{ id: "demo_permitted_portal", name: "Demo permitted portal" }],
    },
    {
      kind: "observed",
      date: null,
      date_kind: "undated",
      label: "renewal option — undated",
      predicate: "renewal_option",
      claim_ids: ["clm-contract-renewal-1"],
      sources: [{ id: "demo_permitted_portal", name: "Demo permitted portal" }],
    },
  ],
  related: {
    dossiers: [
      {
        jkey: "usa-ga",
        slug_path: "usa/ga",
        name: "Georgia",
        level: "admin1",
        url: withBase("dossier/usa/ga/"),
      },
    ],
    sources: [
      {
        id: "demo_permitted_portal",
        name: "Demo permitted portal",
        url: withBase("sources/demo_permitted_portal/"),
      },
    ],
    tasks: [
      {
        task_id: "task-fixture-2",
        handle: "T-usa-ga-alpr-contract-value-q2f7",
        title: "Reconcile the two recorded contract values",
        task_type: "reconcile_values",
        status: "generated",
        url: null,
      },
    ],
    watch: [],
    documents: [
      {
        artifact_id: "art-fixture-2",
        title: "Acworth procurement portal — executed contract PDF",
        artifact_type: "contract",
        source_id: "demo_permitted_portal",
        source_name: "Demo permitted portal",
        claim_ids: ["clm-contract-signed-1"],
      },
    ],
  },
  downloads: [
    {
      kind: "twin",
      format: "json",
      path: `entity/contract/acworth-alpr-expansion-contract--9p4kxwd/index.sig_graph.json`,
      compartment: "sig_graph",
      label: "JSON twin (sig.entity-page/1)",
    },
    {
      kind: "relationships",
      format: "csv",
      path: `entity/contract/acworth-alpr-expansion-contract--9p4kxwd/relationships.sig_graph.csv`,
      compartment: "sig_graph",
      label: "Relationships CSV",
    },
    {
      kind: "relationships",
      format: "json",
      path: `entity/contract/acworth-alpr-expansion-contract--9p4kxwd/relationships.sig_graph.json`,
      compartment: "sig_graph",
      label: "Relationships JSON",
    },
    {
      kind: "statements",
      format: "jsonl",
      path: `entity/contract/acworth-alpr-expansion-contract--9p4kxwd/statements.sig_graph.jsonl`,
      compartment: "sig_graph",
      label: "Statements (sig.statement/1)",
    },
  ],
  cite: {
    publication: "sig-release-2026.09",
    url: fixtureEntityUrl("contract", "acworth-alpr-expansion-contract", "9p4kxwd"),
    record_url: withBase(
      "r/sig-release-2026.09/c/sig_graph/entity/contract/0190cafe-0000-7000-8000-0000000000e7/",
    ),
    sig_id: "sig:contract:0190cafe-0000-7000-8000-0000000000e7",
  },
  withheld_notice: null,
  er_disclosure: ER_DISCLOSURE,
};

/** The published twin for the contract-B legal instrument (P37.23 /
 *  GX-06b) — the adopted-by inbound relation, stated ordinance dates and
 *  the typed "location not recorded" map posture (no place is recorded). */
export const ENTITY_PAGE_TWIN_POLICY_FIXTURE: EntityPageTwin = {
  schema: ENTITY_PAGE_SCHEMA,
  review_state: "published",
  key: "acworth-surveillance-oversight-ordinance-2020-14--5t8mvjq",
  entity_id: "0190cafe-0000-7000-8000-0000000000f8",
  sig_id: "sig:policy:0190cafe-0000-7000-8000-0000000000f8",
  kind: "policy",
  url_type: "policy",
  url: fixtureEntityUrl(
    "policy",
    "acworth-surveillance-oversight-ordinance-2020-14",
    "5t8mvjq",
  ),
  label: "Acworth surveillance oversight ordinance 2020-14",
  descriptor: "Policy or ordinance",
  label_basis: "source_title",
  label_source_id: "okc_council_minutes",
  place_jkey: null,
  disambiguator: null,
  publication: "sig-release-2026.09",
  generated_at: "2026-09-01T00:00:00Z",
  compartment: "sig_graph",
  identifiers: [
    { scheme: "sig.connector.subject", value: "ordinance:acworth-2020-14" },
  ],
  summary: [
    {
      text: "1 recorded inbound relationship — adopted by",
      value: 1,
      relation: "adopted by",
      direction: "inbound",
      claim_ids: ["clm-ordinance-adopted-1"],
    },
  ],
  claims: [
    {
      predicate: "effective_date",
      relation: "effective date",
      envelope: {
        status: "resolved",
        support: "WEAKLY_SUPPORTED",
        agreement: "UNCONTESTED",
        currency: "CURRENT",
        rationale: null,
      },
      values: ["2020-04-01"],
      observed_at: "2020-03-10",
      date_kind: "observed",
      sources: [{ id: "okc_council_minutes", name: "OKC council minutes" }],
      claim_ids: ["clm-ordinance-effective-1"],
    },
  ],
  relations: [
    {
      relation: "adopted by",
      direction: "inbound",
      access_kind: null,
      count: 1,
      items: [
        {
          counterparty: {
            entity_id: "0190cafe-0000-7000-8000-0000000000a1",
            kind: "agency",
            label: "Acworth Police Department",
            label_basis: "source_name",
            url: fixtureEntityUrl("agency", "acworth-police-department", "4g2wm8q"),
            key: "acworth-police-department--4g2wm8q",
          },
          relation: "adopted by",
          role: "adopting_body",
          date: "2020-03-10",
          date_kind: "observed",
          currency: "CURRENT",
          status: "resolved",
          support: "WEAKLY_SUPPORTED",
          agreement: "UNCONTESTED",
          sources: [{ id: "okc_council_minutes", name: "OKC council minutes" }],
          claim_ids: ["clm-ordinance-adopted-1"],
          historical: false,
        },
      ],
      more: 0,
      claim_ids: ["clm-ordinance-adopted-1"],
    },
  ],
  access: { closures: [], degree_only: [] },
  contradictions: [],
  timeline: [
    {
      kind: "stated",
      date: "2020-03-10",
      date_kind: "observed",
      label: "adopted date",
      predicate: "adopted_date",
      claim_ids: ["clm-ordinance-adopted-1"],
      sources: [{ id: "okc_council_minutes", name: "OKC council minutes" }],
    },
    {
      kind: "stated",
      date: "2020-04-01",
      date_kind: "observed",
      label: "effective date",
      predicate: "effective_date",
      claim_ids: ["clm-ordinance-effective-1"],
      sources: [{ id: "okc_council_minutes", name: "OKC council minutes" }],
    },
    {
      kind: "last_seen",
      date: "2020-03-10",
      date_kind: "observed",
      label: "last seen — OKC council minutes",
      predicate: null,
      claim_ids: ["clm-ordinance-effective-1"],
      sources: [{ id: "okc_council_minutes", name: "OKC council minutes" }],
    },
  ],
  related: {
    dossiers: [],
    sources: [
      {
        id: "okc_council_minutes",
        name: "OKC council minutes",
        url: withBase("sources/okc_council_minutes/"),
      },
    ],
    tasks: [],
    watch: [],
    documents: [
      {
        artifact_id: "art-fixture-3",
        title: "Council minutes 2020-03-10 — ordinance 2020-14",
        artifact_type: "minutes",
        source_id: "okc_council_minutes",
        source_name: "OKC council minutes",
        claim_ids: ["clm-ordinance-adopted-1"],
      },
    ],
  },
  downloads: [
    {
      kind: "twin",
      format: "json",
      path: `entity/policy/acworth-surveillance-oversight-ordinance-2020-14--5t8mvjq/index.sig_graph.json`,
      compartment: "sig_graph",
      label: "JSON twin (sig.entity-page/1)",
    },
    {
      kind: "relationships",
      format: "csv",
      path: `entity/policy/acworth-surveillance-oversight-ordinance-2020-14--5t8mvjq/relationships.sig_graph.csv`,
      compartment: "sig_graph",
      label: "Relationships CSV",
    },
    {
      kind: "relationships",
      format: "json",
      path: `entity/policy/acworth-surveillance-oversight-ordinance-2020-14--5t8mvjq/relationships.sig_graph.json`,
      compartment: "sig_graph",
      label: "Relationships JSON",
    },
    {
      kind: "statements",
      format: "jsonl",
      path: `entity/policy/acworth-surveillance-oversight-ordinance-2020-14--5t8mvjq/statements.sig_graph.jsonl`,
      compartment: "sig_graph",
      label: "Statements (sig.statement/1)",
    },
  ],
  cite: {
    publication: "sig-release-2026.09",
    url: fixtureEntityUrl(
      "policy",
      "acworth-surveillance-oversight-ordinance-2020-14",
      "5t8mvjq",
    ),
    record_url: withBase(
      "r/sig-release-2026.09/c/sig_graph/entity/policy/0190cafe-0000-7000-8000-0000000000f8/",
    ),
    sig_id: "sig:policy:0190cafe-0000-7000-8000-0000000000f8",
  },
  withheld_notice: null,
  er_disclosure: ER_DISCLOSURE,
};

/** The committed twin set the fixtures-mode data layer serves, keyed by
 * `<url_type>/<key>`. */
export const ENTITY_PAGE_FIXTURES: Record<string, EntityPageTwin> = {
  "agency/acworth-police-department--4g2wm8q": ENTITY_PAGE_TWIN_FIXTURE,
  "contract/acworth-alpr-expansion-contract--9p4kxwd":
    ENTITY_PAGE_TWIN_CONTRACT_FIXTURE,
  "policy/acworth-surveillance-oversight-ordinance-2020-14--5t8mvjq":
    ENTITY_PAGE_TWIN_POLICY_FIXTURE,
};
