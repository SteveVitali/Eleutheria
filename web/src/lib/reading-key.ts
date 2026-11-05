// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * P36.65 (UXK14-11; K14 §6.3 "Reading keys, not tours"; cites SIG-UI-137) —
 * the per-page reading key's model.
 *
 * K14 §6.3: "Each record page has a 'How to read this page' link in its
 * header. It opens a `<details>` key that lists ONLY the symbols present on
 * that page, generated from the lexicon, each with its one-line meaning and
 * a glossary link." No overlay tours, no cookies — a native `<details>` is
 * the whole mechanism, T1 zero-JS by construction.
 *
 * Every label, glyph and plain meaning comes from `lexicon.json` through the
 * lexicon accessors (SIG-UI-143/133: one word, one meaning — the key can
 * never fork the vocabulary). The PRESENT set is computed from the page's
 * own model — a hand-listed key would drift from what the page renders.
 */

import { lexiconState, glossaryTerm } from "./lexicon";
import type { StateField } from "./lexicon";
import { isInferredRecord } from "./epistemic";
import type { AbsenceKind } from "./epistemic";
import type { Dossier } from "./dossier";

/** One row of the rendered key — a symbol the page actually carries. */
export interface ReadingKeyItem {
  /** Stable id — `data-key` on the rendered row (also the e2e hook). */
  id: string;
  /** The marker glyph/texture name (empty when the mark is a style, not a glyph). */
  glyph: string;
  /** The lexicon's short label. */
  label: string;
  /** The lexicon's one-line plain meaning. */
  plain: string;
  /**
   * The glossary term the row links (`/glossary/#<term>`), or `null` when no
   * dedicated entry exists — the row then links the glossary root.
   */
  term: string | null;
}

/** The summary label the `<details>` shows — copy-batch row KY-01 (B-2). */
export const READING_KEY_SUMMARY = "How to read this page";
export const READING_KEY_SUMMARY_BATCH_ID = "KY-01";
/** The link text each row's glossary affordance carries — batch row KY-02. */
export const READING_KEY_GLOSSARY_LABEL = "glossary ›";
export const READING_KEY_GLOSSARY_BATCH_ID = "KY-02";

/**
 * One lexicon state as a key row. `term` names the glossary entry to link;
 * absent → the row links the glossary root (a term is never fabricated —
 * `glossaryTerm` fails closed on a miss).
 */
function stateItem(
  id: string,
  field: StateField,
  stateId: string,
  term: string | null,
  plainOverride?: { plain: string; label?: string },
): ReadingKeyItem {
  const state = lexiconState(field, stateId);
  if (term !== null) glossaryTerm(term); // fail closed: a missing term is a build error
  return {
    id,
    glyph: state.symbol ?? "",
    label: plainOverride?.label ?? state.label,
    plain: plainOverride?.plain ?? state.plain,
    term,
  };
}

/**
 * The key for a dossier page — the symbols the dossier's model proves the
 * page renders. Nothing is listed that the page does not carry:
 *
 *   ⊕ support      — every material figure expands to its support glyph;
 *   ≠ contested    — a contested figure or the declared/located pair;
 *   ⚠ unresolved   — a figure no winning claim can headline;
 *   ? ∅ ✗ ▨ gaps  — the ABSENCE kinds the dossier's gaps and absence rows use
 *                   (only the kinds present are listed);
 *   ◈ inferred     — an L4 derived-fact row;
 *   withheld       — a publication-policy withheld value.
 *
 * A dossier carrying none of the optional marks still lists `support` — the
 * header strip and every figure carry it — so the key is never empty and
 * never lies about what is on the page (SIG-ENG-042).
 */
export function dossierReadingKey(dossier: Dossier): ReadingKeyItem[] {
  const items: ReadingKeyItem[] = [];
  const figures = dossier.sections.flatMap((s) => s.figures ?? []);
  const rows = dossier.sections.flatMap((s) => s.rows ?? []);

  if (figures.length > 0) {
    items.push(stateItem("support", "support", "CONFIRMED", "support", {
      label: "Support",
      plain: "How well the evidence backs a value — expand any figure to see its ⊕ glyph, evidence count and sources.",
    }));
    const hasUnresolved = figures.some(
      (f) => !f.reconciliation.claims.some((c) => c.claimId === f.reconciliation.winningClaimId),
    );
    if (figures.some((f) => f.contested) || dossier.disagreements !== undefined) {
      items.push(stateItem("contested", "agreement", "CONTESTED", "contested"));
    }
    if (hasUnresolved) {
      items.push(stateItem("unresolved", "absence", "UNRESOLVED", "unresolved"));
    }
  }

  const absenceKinds = new Set<AbsenceKind>();
  for (const g of dossier.gaps) absenceKinds.add(g.kind);
  for (const r of rows) {
    if (r.absence) absenceKinds.add(r.absence);
  }
  const ORDER: AbsenceKind[] = [
    "NOT_RESEARCHED",
    "NO_EVIDENCE_FOUND",
    "EVIDENCE_OF_ABSENCE",
    "UNRESOLVED",
  ];
  for (const kind of ORDER) {
    if (absenceKinds.has(kind)) {
      items.push(
        stateItem(`absence-${kind.toLowerCase()}`, "absence", kind, null),
      );
    }
  }

  if (rows.some((r) => isInferredRecord(r))) {
    items.push(stateItem("inferred", "inferred", "INFERRED", null));
  }
  if (rows.some((r) => r.withheld === true)) {
    // No lexicon state names a publication-policy withhold — the drafted
    // line is copy-batch row KY-03 (B-2), never an enum re-case.
    items.push({
      id: "withheld",
      glyph: "",
      label: "Withheld",
      plain: "A value SIG withholds under its publication policy — the row names the reason.", // copy: KY-03
      term: null,
    });
  }
  return items;
}
