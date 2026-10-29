// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
/**
 * Procurement relevance — `sig.procurement-relevance/1` (K2 GX-04 / H-13,
 * ticket P36.30, R11-K13-GX-04).
 *
 * The web-side mirror of `policy/src/policy/procurement_relevance.py`: the
 * Python module owns the ONE classification (matched_keyword +
 * products/CPV/NAICS against the reviewed vocabulary — the same
 * one-derivation posture as the label registry); this file carries only the
 * row types, the exclusion/buyer-row semantics every notice surface shares,
 * and the committed fixture.
 *
 * Semantics (the plan cell D-K2-5 [B-22] = as recommended: exclude
 * unclassified procurement — an answered decision, carried verbatim):
 * - `surveillance_related` — the notice carries a matched keyword or a
 *   reviewed product/CPV/NAICS classification. Surveillance surfaces (the
 *   O1 supply graphs, surveillance collections) may show it, always with
 *   its matched technology (H-13).
 * - `not_classified` — no reviewed signal found. The notice is excluded
 *   from surveillance surfaces (never silently dropped) and appears only
 *   as a buyer-page row labelled `not classified as surveillance-related`.
 * - `not_classified` records "no reviewed signal found" — never the claim
 *   "not surveillance" (K2 NEW-7's honest surface).
 */

/** The emitted document's schema id (`web/procurement_relevance.json`). */
export const PROCUREMENT_RELEVANCE_SCHEMA = "sig.procurement-relevance/1";

/** K2 §7 H-13 — the buyer-page row label, verbatim, one string everywhere. */
export const UNCLASSIFIED_PROCUREMENT_LABEL =
  "not classified as surveillance-related";

export type ProcurementRelevance =
  | "surveillance_related"
  | "not_classified"
  | string;

/** One `sig.procurement-relevance/1` row — a notice's verdict. */
export interface ProcurementRelevanceRow {
  /** The notice's entity id in the release (joins the label registry). */
  entity_id: string | null;
  /** The connector subject key (`procurement_notice:<source>:<id>`). */
  subject_key: string;
  /** The label kind — `notice` for the notice family. */
  kind: string;
  relevance: ProcurementRelevance;
  /** Which input kinds fired — `matched_keyword` / `product_code` /
   * `product_text`, or `none` when nothing fired. */
  bases: string[];
  /** The firing term ids / classification codes (`cpv:35120000`). */
  matched: string[];
  /** The H-13 buyer-page row label — set only on `not_classified` rows. */
  buyer_label: string | null;
  [key: string]: unknown;
}

/** The emitted `sig.procurement-relevance/1` document. */
export interface ProcurementRelevanceDoc {
  schema: string;
  publication?: string | null;
  generated_at?: string;
  rule?: Record<string, unknown>;
  vocabulary?: Record<string, unknown>;
  counts?: Record<string, unknown>;
  rows: ProcurementRelevanceRow[];
}

/** True when the notice belongs on the surveillance surfaces (D-K2-5). */
export function isSurveillanceRelevant(row: ProcurementRelevanceRow): boolean {
  return row.relevance === "surveillance_related";
}

/**
 * The D-K2-5 exclusion posture as a filter — the notice subset a
 * surveillance surface (O1 supply graph, surveillance collection, J2
 * journey) may draw. Unclassified notices are excluded here, never
 * silently dropped: they surface through {@link buyerNoticeRows}.
 */
export function surveillanceNotices(
  rows: readonly ProcurementRelevanceRow[],
): ProcurementRelevanceRow[] {
  return rows.filter(isSurveillanceRelevant);
}

/**
 * The buyer-page listing (K2 H-13): every notice the buyer was party to,
 * with the row label the page shows — the matched technology for a
 * relevant notice, the verbatim 'not classified as surveillance-related'
 * label for an unclassified one. `buyer_key` is the buyer entity id the
 * row names; when absent the full listing is returned (fixtures and the
 * pre-entity-page release carry no buyer join — the row is still shown).
 */
export function buyerNoticeRows(
  rows: readonly ProcurementRelevanceRow[],
  buyer_key?: string | null,
): ProcurementRelevanceRow[] {
  if (buyer_key == null) return [...rows];
  return rows.filter((r) => String(r["buyer_key"] ?? "") === buyer_key);
}

/**
 * The H-13 row label — the matched technology for a relevant notice
 * (H-13: a notice appears only with its matched technology), the
 * verbatim unclassified label otherwise.
 */
export function noticeRowLabel(row: ProcurementRelevanceRow): string {
  if (row.buyer_label) return row.buyer_label;
  if (row.matched.length > 0) return row.matched.join(" · ");
  return UNCLASSIFIED_PROCUREMENT_LABEL;
}

/** Light parse — the shape check the data layer applies (fail closed). */
export function isProcurementRelevanceDoc(
  doc: unknown,
): doc is ProcurementRelevanceDoc {
  if (typeof doc !== "object" || doc === null) return false;
  const d = doc as Record<string, unknown>;
  return d.schema === PROCUREMENT_RELEVANCE_SCHEMA && Array.isArray(d.rows);
}

// --------------------------------------------------------------------------- //
// The committed fixtures-mode document (SIG-UI-036: fixtures are invented,
// honest data). Three invented notices exercise both ways of the rule: a
// matched-keyword notice, a reviewed-CPV-code notice and an unclassified
// city contract — the row the H-13 label exists for.
// --------------------------------------------------------------------------- //

export const PROCUREMENT_RELEVANCE_FIXTURE: ProcurementRelevanceDoc = {
  schema: PROCUREMENT_RELEVANCE_SCHEMA,
  publication: "sig-release-2026.09",
  generated_at: "2026-09-01T00:00:00Z",
  rows: [
    {
      // TED notice whose verbatim text scanned `surveillance_camera`.
      entity_id: "ent:notice-ted-2026-118",
      subject_key: "procurement_notice:ted_eu:2026-118",
      kind: "notice",
      relevance: "surveillance_related",
      bases: ["matched_keyword"],
      matched: ["surveillance_camera"],
      buyer_label: null,
    },
    {
      // TED notice classified by its reviewed CPV product code alone —
      // no keyword hit, the code is the classification of record.
      entity_id: "ent:notice-ted-2026-204",
      subject_key: "procurement_notice:ted_eu:2026-204",
      kind: "notice",
      relevance: "surveillance_related",
      bases: ["product_code"],
      matched: ["cpv:35120000"],
      buyer_label: null,
    },
    {
      // A city portal notice with no reviewed surveillance signal — the
      // K2 NEW-7 case (a routine municipal contract). Excluded from the
      // surveillance surfaces; shown only on the buyer's page with the
      // H-13 label.
      entity_id: "ent:notice-okc-4471",
      subject_key: "procurement_notice:okc_portal:4471",
      kind: "notice",
      relevance: "not_classified",
      bases: ["none"],
      matched: [],
      buyer_label: UNCLASSIFIED_PROCUREMENT_LABEL,
    },
  ],
};
