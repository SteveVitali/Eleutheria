// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * P37.39 (R11-K13-QB-01 / L3 §5.2, SIG-CONF-011's per-record rendering,
 * UXR-A06) — the per-record quality-basis block, TypeScript twin of
 * `exports/src/exports/record_basis.py`.
 *
 * One shared normalisation turns a record's CONF-07b derivation fields —
 * `site_id`, `copies[]`, `possible_duplicates[]`, `multi_view[]`,
 * `n_independent_lineages` + its display — plus the location-check,
 * technology, evidence and checked-by contexts into the ONE
 * `sig.record-basis/1` block every surface renders: the `<ProvenancePanel>`
 * basis section, the map selection panel, entity and record pages, and
 * K5's agree/disagree view.
 *
 * Entry `display` strings are the export's own L3 §5.2 verbatim sentences —
 * never paraphrased into a merge claim. Every state is a value or a named
 * absence (`not_recorded` / `not_evaluable`), never a blank, never
 * fabricated (SIG-ENG-042).
 */

import { NOT_RECORDED } from "./provenance-panel";

export const RECORD_BASIS_SCHEMA = "sig.record-basis/1";
export const NOT_EVALUABLE = "not_evaluable";

/** The whole-block absence text — L3 §5.2's no-run state. */
export const NO_BASIS =
  "no completed camera-site ER run — the fields are declared, never fabricated";

/** The checked-by line while no person outside the project has reviewed —
 *  SIG-CONF-011's independent-review row reads "none". */
export const CHECKED_BY_TEXT =
  "Checked by automated release checks. Not reviewed by a person.";

/** One copies[]/possible_duplicates[]/multi_view[] entry (verbatim). */
export interface BasisEntry {
  record?: string;
  site_id?: string;
  source?: string;
  source_name?: string;
  upstream_id?: string | null;
  basis?: string;
  basis_text?: string;
  reason?: string;
  distance_m?: number;
  display?: string;
}

/** The `sig.record-basis/1` block every surface renders. */
export interface RecordBasis {
  schema: typeof RECORD_BASIS_SCHEMA;
  /** The site's shared id, `null` with `site_absence` named. */
  site_id: string | null;
  site_absence: string | null;
  /** Measured entries (empty = measured none); absence rides *_absence. */
  copies: BasisEntry[];
  copies_absence: string | null;
  possible_duplicates: BasisEntry[];
  duplicates_absence: string | null;
  multi_view: BasisEntry[];
  multi_view_absence: string | null;
  /** The declared independence-class count; `null` when not evaluable. */
  lineages: number | null;
  /** The verbatim L3 §5.2 display ("Listed by 1 source." / "Seen independently…"). */
  lineages_text: string | null;
  lineages_absence: string | null;
  /** The six §5.2 state sentences — values or named absences, never blank. */
  location_check: string;
  technology: string;
  evidence: string;
  checked_by: string;
}

/** The dedup block the sites row / map asset / published record carries. */
export interface DedupFields {
  site_id?: unknown;
  copies?: unknown;
  possible_duplicates?: unknown;
  multi_view?: unknown;
  n_independent_lineages?: unknown;
  n_independent_lineages_display?: unknown;
}

function absenceReasonOf(value: unknown): string | null {
  if (value !== null && typeof value === "object" && !Array.isArray(value)) {
    const o = value as Record<string, unknown>;
    const r = o[NOT_RECORDED] ?? o[NOT_EVALUABLE];
    if (r) return String(r);
  }
  return null;
}

function entries(value: unknown): [BasisEntry[], string | null] {
  if (Array.isArray(value)) {
    return [
      value.filter((e): e is Record<string, unknown> => e !== null && typeof e === "object") as BasisEntry[],
      null,
    ];
  }
  return [[], absenceReasonOf(value) ?? NOT_RECORDED];
}

/** `placement_check` values that mean "the published point sits inside the
 *  recorded jurisdiction" — the closed K4 §3.3 vocabulary. */
const INSIDE_CHECKS = new Set(["consistent", "on_boundary"]);
const CONFLICT_CHECKS = new Set(["outside_declared", "outside_declared_country"]);
const SUSPECT_CHECKS = new Set(["axis_swap_suspected", "sign_flip_suspected"]);
const UNPLOTTED_CHECKS = new Set([
  "no_point",
  "coordinates_conflicted",
  "point_rejected:null_island",
  "point_rejected:invalid_point",
  "outside_all_boundaries",
  "null_island",
  "invalid_point",
]);

/** The location-check sentence over the closed `placement_check` vocabulary. */
export function locationCheckText(
  placementCheck: unknown,
  jurisdictionName?: string | null,
): string {
  const check = String(placementCheck ?? "").trim();
  const place = jurisdictionName || "the recorded jurisdiction";
  if (!check) return `Location check: ${NOT_RECORDED} — no placement check is recorded.`;
  if (INSIDE_CHECKS.has(check)) return `Location checked: inside ${place}.`;
  if (CONFLICT_CHECKS.has(check)) {
    return `Location conflict: located outside the declared jurisdiction (${check}); shown, not counted there.`;
  }
  if (SUSPECT_CHECKS.has(check)) {
    return `Location check: a suspect coordinate variant (${check}); the point is withheld.`;
  }
  if (UNPLOTTED_CHECKS.has(check)) {
    return `Location check: ${check} — no publishable point; the record is shown, not counted at a point.`;
  }
  if (check === "no_location_evidence") return "Location check: no location evidence is recorded.";
  if (check === "name_unmatched" || check === "name_ambiguous") {
    return `Location check: ${check} — declared level only.`;
  }
  return `Location check: ${check}.`;
}

/** The technology sentence — a declared slug with its honest basis. */
export function technologyText(
  technology: unknown,
  status: unknown = null,
  sourceName?: string | null,
): string {
  const slug = String(technology ?? "").trim();
  const state = String(status ?? "").trim();
  const src = sourceName || "the source";
  if (slug) {
    const basis = state === "" || state === "resolved" ? "layer description" : state;
    return `Technology: ${slug}, from ${src}'s ${basis}.`;
  }
  if (state === "conflicted") return "Technology: conflicted declarations — no class is shown.";
  if (state === "unreported") return "Technology: unreported — the source declares no class.";
  return `Technology: ${NOT_RECORDED}.`;
}

/** The evidence sentence — "Evidence: <Source>, fetched <date>; copy kept: yes/no." */
export function evidenceText(
  sourceName: unknown,
  fetched: unknown,
  copyKept: boolean | null = null,
): string {
  const src = String(sourceName ?? "").trim();
  const when = String(fetched ?? "").slice(0, 10);
  if (!src || !when) {
    return `Evidence: ${NOT_RECORDED} — no published fetch is recorded for this record.`;
  }
  const kept = copyKept === true ? "yes" : copyKept === false ? "no" : NOT_RECORDED;
  return `Evidence: ${src}, fetched ${when}; copy kept: ${kept}.`;
}

export interface RecordBasisCtx {
  placementCheck?: unknown;
  jurisdictionName?: string | null;
  technology?: unknown;
  technologyStatus?: unknown;
  technologySourceName?: string | null;
  evidenceSourceName?: unknown;
  evidenceFetched?: unknown;
  evidenceCopyKept?: boolean | null;
}

/**
 * Normalise a record's dedup block + contexts into `sig.record-basis/1`.
 * `dedup === null` (a pre-P35.47 wire) returns `null` — the sparse absence,
 * never a fabricated block.
 */
export function recordBasis(dedup: DedupFields | null | undefined, ctx: RecordBasisCtx = {}): RecordBasis | null {
  if (dedup === null || dedup === undefined) return null;
  const siteAbsence = absenceReasonOf(dedup.site_id);
  const [copies, copiesAbsence] = entries(dedup.copies);
  const [poss, possAbsence] = entries(dedup.possible_duplicates);
  const [mv, mvAbsence] = entries(dedup.multi_view);
  const nLin = dedup.n_independent_lineages;
  const nDisp = dedup.n_independent_lineages_display;
  const lineagesAbsence = absenceReasonOf(nLin) ?? absenceReasonOf(nDisp);
  let lineagesText = typeof nDisp === "string" ? nDisp : null;
  if (lineagesText === null && typeof nLin === "number" && Number.isInteger(nLin)) {
    lineagesText = nLin === 1 ? "Listed by 1 source." : `Seen independently by ${nLin} sources.`;
  }
  return {
    schema: RECORD_BASIS_SCHEMA,
    site_id: typeof dedup.site_id === "string" ? dedup.site_id : null,
    site_absence: siteAbsence,
    copies,
    copies_absence: copiesAbsence,
    possible_duplicates: poss,
    duplicates_absence: possAbsence,
    multi_view: mv,
    multi_view_absence: mvAbsence,
    lineages: typeof nLin === "number" && Number.isInteger(nLin) ? nLin : null,
    lineages_text: lineagesText,
    lineages_absence: lineagesAbsence,
    location_check: locationCheckText(ctx.placementCheck, ctx.jurisdictionName),
    technology: technologyText(ctx.technology, ctx.technologyStatus, ctx.technologySourceName),
    evidence: evidenceText(ctx.evidenceSourceName, ctx.evidenceFetched, ctx.evidenceCopyKept ?? null),
    checked_by: CHECKED_BY_TEXT,
  };
}

/** `(label, text, displays)` render rows — the block's order, twin of
 *  `record_basis.basis_rows`. */
export function basisRows(basis: RecordBasis): [string, string, string[]][] {
  const displays = (es: BasisEntry[]): string[] =>
    es.map((e) => String(e.display ?? "").trim()).filter((d) => d.length > 0);
  const siteText = basis.site_id ?? `${basis.site_absence ?? NOT_RECORDED}`;
  const rows: [string, string, string[]][] = [["Camera site", siteText, []]];
  for (const [label, es, absence] of [
    ["Copies", basis.copies, basis.copies_absence],
    ["Possible duplicates", basis.possible_duplicates, basis.duplicates_absence],
    ["Multi-view", basis.multi_view, basis.multi_view_absence],
  ] as [string, BasisEntry[], string | null][]) {
    if (absence) rows.push([label, `${NOT_RECORDED} — ${absence}`, []]);
    else if (es.length === 0) rows.push([label, "none recorded", []]);
    else rows.push([label, "", displays(es)]);
  }
  rows.push([
    "Corroboration",
    basis.lineages_text ?? `${NOT_EVALUABLE} — ${basis.lineages_absence ?? NOT_RECORDED}`,
    [],
  ]);
  rows.push(["Location check", basis.location_check, []]);
  rows.push(["Technology", basis.technology, []]);
  rows.push(["Evidence", basis.evidence, []]);
  rows.push(["Checked by", basis.checked_by, []]);
  return rows;
}
