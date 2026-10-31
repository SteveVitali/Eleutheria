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

/** Contract A's page kinds (the E1 wave — K2 §4.3). */
export const PAGE_KINDS = ["org", "agency", "portal"] as const;
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
 * SIG-UI-117). Never a relation item, never an edge. */
export interface DegreeOnlyFact {
  predicate: string;
  counts: number[];
  claim_ids: string[];
  observed_at: string | null;
  date_kind: "observed" | "undated";
  currency: string | null;
  historical: boolean;
  sources: { id: string; name?: string | null }[];
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
    /** The GX-07 closures (P37.21) — typed empty under contract A. */
    closures: unknown[];
    degree_only: DegreeOnlyFact[];
  };
  /** Contract-B sections — typed empty under contract A. */
  contradictions: unknown[];
  timeline: unknown[];
  related: Record<string, unknown>;
  downloads: unknown[];
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
  if (!isObj(doc.cite)) return false;
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
    closures: [],
    degree_only: [
      {
        predicate: "sharing_partner_degree",
        counts: [851],
        claim_ids: ["clm-apd-degree-1"],
        observed_at: "2020-01-28",
        date_kind: "observed",
        currency: "HISTORICAL",
        historical: true,
        sources: [{ id: "eff_data_driven", name: "EFF Data Driven" }],
      },
    ],
  },
  contradictions: [],
  timeline: [],
  related: {},
  downloads: [],
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

/** The committed twin set the fixtures-mode data layer serves, keyed by
 * `<url_type>/<key>`. */
export const ENTITY_PAGE_FIXTURES: Record<string, EntityPageTwin> = {
  "agency/acworth-police-department--4g2wm8q": ENTITY_PAGE_TWIN_FIXTURE,
};
