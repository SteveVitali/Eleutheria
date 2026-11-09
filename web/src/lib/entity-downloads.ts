// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * P37.23 (K2 GX-06b, §4.2 row 12) — the entity downloads' served bytes.
 * The twin's `downloads[]` names only files the export emits
 * (`entity/<type>/<key>/relationships.<comp>.{json,csv}` and
 * `statements.<comp>.jsonl`); these composers mirror
 * `exports/src/exports/entity_page.py`'s emitted shapes field-for-field so
 * the page-served routes carry the same documents (the JSON relationship
 * doc is the twin's own relation groups verbatim; the CSV is the declared
 * column order; the statements slice is the `sig.statement/1` rows the
 * entity's claims cite). Export mode serves the emitted artifact bytes
 * verbatim — never a re-render.
 */

import type { EntityPageTwin, EntityRelationItem } from "./entity-page";
import type { StatementRow } from "./provenance-panel";

export const ENTITY_RELATIONSHIPS_SCHEMA = "sig.entity-relationships/1";

/** The `relationships.<comp>.json` document — the same object the
 *  exporter writes beside the twin (schema + identity + the emitted
 *  relation groups verbatim). */
export function relationshipsDoc(twin: EntityPageTwin): Record<string, unknown> {
  return {
    schema: ENTITY_RELATIONSHIPS_SCHEMA,
    entity_id: twin.entity_id,
    key: twin.key,
    compartment: twin.compartment,
    publication: twin.publication,
    generated_at: twin.generated_at,
    relations: twin.relations,
  };
}

/** The CSV column order — `entity_page.py`'s `_REL_CSV_COLUMNS` verbatim
 *  (the declared `entity_relationships` resource columns, SIG-TRANSP-016). */
const REL_CSV_COLUMNS = [
  "relation",
  "direction",
  "access_kind",
  "counterparty_label",
  "counterparty_entity_id",
  "counterparty_key",
  "role",
  "date",
  "date_kind",
  "currency",
  "status",
  "support",
  "agreement",
  "historical",
  "sources",
  "claim_ids",
] as const;

function csvCell(v: string): string {
  return /[",\n\r]/.test(v) ? `"${v.replaceAll('"', '""')}"` : v;
}

function csvRow(cells: readonly string[]): string {
  return cells.map(csvCell).join(",") + "\n";
}

function itemCells(it: EntityRelationItem): string[] {
  const cp = it.counterparty;
  return [
    cp.label ?? cp.review_state ?? "",
    cp.entity_id ?? "",
    cp.key ?? "",
    it.role ?? "",
    it.date ?? "",
    it.date_kind,
    it.currency ?? "",
    it.status ?? "",
    it.support,
    it.agreement ?? "",
    it.historical ? "true" : "false",
    it.sources.map((s) => s.id).join(";"),
    it.claim_ids.join(";"),
  ];
}

/** The `relationships.<comp>.csv` bytes — header + one row per item in
 *  emitted group order, deterministic (the same flatten the exporter
 *  performs over the twin's `relations`). */
export function relationshipsCsv(twin: EntityPageTwin): string {
  let out = csvRow(REL_CSV_COLUMNS);
  for (const g of twin.relations) {
    for (const it of g.items) {
      const cells = itemCells(it);
      out += csvRow([g.relation, g.direction, g.access_kind ?? "", ...cells]);
    }
  }
  return out;
}

/** The canonical-JSON serialisation (`sort_keys`, tight separators) the
 *  exporter's `canonical_json` uses — one `sig.statement/1` row per line. */
export function canonicalJsonLine(obj: unknown): string {
  const sortKeys = (v: unknown): unknown => {
    if (Array.isArray(v)) return v.map(sortKeys);
    if (v !== null && typeof v === "object") {
      return Object.fromEntries(
        Object.entries(v as Record<string, unknown>)
          .sort(([a], [b]) => (a < b ? -1 : a > b ? 1 : 0))
          .map(([k, x]) => [k, sortKeys(x)]),
      );
    }
    return v;
  };
  return JSON.stringify(sortKeys(obj)) + "\n";
}

/** The `statements.<comp>.jsonl` bytes — the entity's `sig.statement/1`
 *  slice: every statement row whose `entity_id` names this entity, in
 *  fixture order (the exporter's slice is the same stream filtered on the
 *  entity, never re-derived). */
export function statementsJsonl(
  twin: EntityPageTwin,
  statements: readonly StatementRow[],
): string {
  return statements
    .filter((s) => s.entity_id === twin.entity_id)
    .map((s) => canonicalJsonLine(s))
    .join("");
}
