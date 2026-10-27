// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * The epistemic visual language, as pure data + logic (§39.1, §10.7, §9.5).
 *
 * This module is the single source of truth every Phase-15 surface (P15.2–P15.5)
 * consumes. It owns:
 *   - the four independent epistemic fields (§10.7) — never a fused token (SIG-UI-004);
 *   - the four-step support glyph with its text equivalent + machine-readable
 *     evidence count + downgrade reason code (SIG-UI-003);
 *   - the single absence texture and the four absence kinds within it (§9.5, SIG-UI-007);
 *   - the contested-value predicate (SIG-UI-008);
 *   - the contradiction value-range model (§29.1, SIG-UI-009).
 *
 * It carries NO colour values: colour is assigned only in `styles/epistemic.css`,
 * where the "green never for epistemic state" rule (SIG-UI-006) is enforced by a
 * test. Every state here declares a non-colour text channel so the redundant
 * encoding required by WCAG 1.4.1 (SIG-UI-005) exists independently of any style.
 *
 * P36.17 (SIG-UI-143): every display string — labels, plain meanings, marker
 * text — is derived from `lexicon.json`, the one machine-readable vocabulary
 * (K14 §3.4). This module keeps the stored enums and the logic; it never
 * forks the wording. Raw enum values are machine keys only — they must not
 * appear in visible prose outside Technical details or `code`.
 */

import { stateLabel, lexiconState, LEXICON } from "./lexicon";

// --- The four orthogonal fields (§10.7, SIG-EPIS-023) ----------------------

export const RESOLUTION_STATUSES = ["RESOLVED", "UNRESOLVED", "SUPERSEDED", "WITHDRAWN"] as const;
export type ResolutionStatus = (typeof RESOLUTION_STATUSES)[number];

export const SUPPORT_LEVELS = [
  "CONFIRMED",
  "STRONGLY_SUPPORTED",
  "PROBABLE",
  "WEAKLY_SUPPORTED",
  "UNSUPPORTED",
] as const;
export type Support = (typeof SUPPORT_LEVELS)[number];

export const AGREEMENT_LEVELS = [
  "UNCONTESTED",
  "MINOR_DISAGREEMENT",
  "CONTESTED",
  "IRRECONCILABLE",
] as const;
export type Agreement = (typeof AGREEMENT_LEVELS)[number];

export const CURRENCY_LEVELS = ["CURRENT", "AGING", "STALE", "HISTORICAL"] as const;
export type Currency = (typeof CURRENCY_LEVELS)[number];

/** One of the four independently-visible fields, for rendering as a distinct chip. */
export type EpistemicFieldName = "resolution_status" | "support" | "agreement" | "currency";

/** The four field names, in canonical display order. A fused single badge is prohibited. */
export const EPISTEMIC_FIELD_NAMES: readonly EpistemicFieldName[] = [
  "resolution_status",
  "support",
  "agreement",
  "currency",
] as const;

/** Human-readable field titles (the label shown beside each independent chip). */
export const FIELD_TITLES: Record<EpistemicFieldName, string> = {
  resolution_status: LEXICON.fields.resolution_status.label,
  support: LEXICON.fields.support.label,
  agreement: LEXICON.fields.agreement.label,
  currency: LEXICON.fields.currency.label,
};

/** The lexicon state field each epistemic field's values draw their labels from. */
const FIELD_STATE_KEY: Record<EpistemicFieldName, Parameters<typeof stateLabel>[0]> = {
  resolution_status: "resolution",
  support: "support",
  agreement: "agreement",
  currency: "currency",
};

/**
 * The display label for one field value — from the lexicon, never a re-cased
 * enum (SIG-UI-143). A null/`—` value renders the typed "Not applicable"
 * state (CP-5), never a bare "unknown".
 */
export function epistemicFieldValueLabel(field: EpistemicFieldName, value: string): string {
  if (value === "—") return LEXICON.legend.cannotApply.label;
  return stateLabel(FIELD_STATE_KEY[field], value);
}

// --- The support glyph (SIG-UI-003) ----------------------------------------

/** How many of the four glyph steps are filled, per support level. */
export const SUPPORT_STEPS: Record<Support, number> = {
  CONFIRMED: 4,
  STRONGLY_SUPPORTED: 3,
  PROBABLE: 2,
  WEAKLY_SUPPORTED: 1,
  UNSUPPORTED: 0,
};

/** The number of steps in the support glyph (a four-step glyph, SIG-UI-003). */
export const GLYPH_STEP_COUNT = 4;

const GLYPH_FILLED = "\u2295"; // ⊕ a filled step
const GLYPH_EMPTY = "\u25EF"; // ◯ an empty step

/**
 * The four-step glyph string for a support level, e.g. CONFIRMED → "⊕⊕⊕⊕",
 * STRONGLY_SUPPORTED → "⊕⊕⊕◯". Decorative on its own; always paired with the
 * text equivalent below (a glyph that does not say what it means is decoration).
 */
export function supportGlyph(support: Support): string {
  const filled = SUPPORT_STEPS[support];
  return GLYPH_FILLED.repeat(filled) + GLYPH_EMPTY.repeat(GLYPH_STEP_COUNT - filled);
}

/** The accessible text equivalent for the glyph (what a screen reader announces). */
export function supportTextEquivalent(support: Support): string {
  const filled = SUPPORT_STEPS[support];
  // The lexicon label, not a re-cased enum — the text channel carries the
  // shared vocabulary (SIG-UI-143).
  return `Support: ${stateLabel("support", support)} (${filled} of ${GLYPH_STEP_COUNT})`;
}

/**
 * A support mark that does not say *why* it was downgraded is decoration
 * (SIG-UI-003). This is the machine-readable summary that always travels with
 * the glyph: the level, the number of filled steps, the count of admissible
 * evidence classes behind the winning value, and — where the value sits below
 * CONFIRMED — a stable downgrade reason code.
 */
export interface SupportMark {
  support: Support;
  filledSteps: number;
  glyph: string;
  textEquivalent: string;
  /** Independent, method-distinct evidence classes behind the winning value. */
  evidenceCount: number;
  /** A stable code explaining any downgrade below CONFIRMED; null when CONFIRMED. */
  downgradeReasonCode: string | null;
}

/** Stable downgrade reason codes (machine-readable; never free text). */
export const DOWNGRADE_REASONS: Record<Exclude<Support, "CONFIRMED">, string> = {
  STRONGLY_SUPPORTED: "SINGLE_W3_OR_TWO_W2",
  PROBABLE: "SINGLE_W2_CLASS",
  WEAKLY_SUPPORTED: "BEST_CLAIM_W1",
  UNSUPPORTED: "NO_ADMISSIBLE_CLAIM",
};

/** Assemble the full support mark (glyph + text + evidence count + downgrade code). */
export function supportMark(support: Support, evidenceCount: number): SupportMark {
  return {
    support,
    filledSteps: SUPPORT_STEPS[support],
    glyph: supportGlyph(support),
    textEquivalent: supportTextEquivalent(support),
    evidenceCount,
    downgradeReasonCode: support === "CONFIRMED" ? null : DOWNGRADE_REASONS[support],
  };
}

// --- Contested values (SIG-UI-008) -----------------------------------------

/**
 * Agreement levels at or above which a value is *contested* and MUST carry a
 * persistent marker at every appearance. `MINOR_DISAGREEMENT` (dissent within
 * tolerance or only at W0/W1) is deliberately below the threshold; marking it
 * would cry wolf.
 */
export const CONTESTED_AGREEMENTS: readonly Agreement[] = ["CONTESTED", "IRRECONCILABLE"] as const;

/** Whether a value with this agreement level is contested (SIG-UI-008). */
export function isContested(agreement: Agreement): boolean {
  return CONTESTED_AGREEMENTS.includes(agreement);
}

/** The persistent contested marker glyph + its accessible label — from the lexicon. */
export const CONTESTED_MARKER = {
  glyph: lexiconState("agreement", "CONTESTED").symbol!, // ≠ — a non-colour channel (SIG-UI-005)
  label: stateLabel("agreement", "CONTESTED"),
} as const;

// --- The inferred / L4 marker (§30.4, SIG-RECON-052, P36.14) ---------------

/**
 * The spine layer an inference belongs to (§30, SIG-RECON-047). Mirrors
 * `inference.marking.INFERRED_LAYER` — the Python side owns the stored
 * `inference.derived_fact` shape; this constant is the same contract on the
 * rendered side.
 */
export const INFERRED_LAYER = "L4";

/**
 * The persistent inferred marker: an L4 derived fact (§30.4, SIG-RECON-052)
 * MUST be visually and structurally distinguishable from an observed or
 * resolved record on every surface. The marker is a glyph + a text label —
 * never colour alone (SIG-UI-005) — rendered by the `sig-inferred` epistemic
 * class (`styles/epistemic.css`). It names *what kind of record this is*
 * (derived, not observed); it is deliberately NOT the lexicon's Provisional
 * chip (an unevaluated-method label, SIG-UI-062) nor a lifecycle Candidate.
 */
export const INFERRED_MARKER = {
  /** ◈ — a non-colour channel (SIG-UI-005), distinct from every other marker glyph. */
  glyph: lexiconState("inferred", "INFERRED").symbol!,
  label: lexiconState("inferred", "INFERRED").label,
  meaning: lexiconState("inferred", "INFERRED").plain,
  /** The epistemic class that styles this marker (defined once in epistemic.css). */
  cssClass: "sig-inferred",
} as const;

/**
 * True exactly when a record carries the complete L4 marker —
 * `inferred: true` AND `layer: "L4"` together (the same contract
 * `inference.marking.is_inferred_record` enforces on the Python side). A
 * half-marked record counts as unmarked.
 */
export function isInferredRecord(
  record: { inferred?: boolean; layer?: string } | null | undefined,
): boolean {
  return record?.inferred === true && record?.layer === INFERRED_LAYER;
}

// --- The four absence kinds within the single hatch (§9.5, SIG-UI-007) -----

export const ABSENCE_KINDS = [
  "NOT_RESEARCHED",
  "NO_EVIDENCE_FOUND",
  "EVIDENCE_OF_ABSENCE",
  "UNRESOLVED",
] as const;
export type AbsenceKind = (typeof ABSENCE_KINDS)[number];

/**
 * Metadata for each absence kind. Absence has exactly ONE texture (the hatch);
 * the four kinds are distinguished *within* it by a distinct symbol + text, never
 * by a second texture and never by colour alone (SIG-UI-007, SIG-UI-005). Each
 * kind is clickable and turns the gap into a research task (`taskable`).
 */
export interface AbsenceKindMeta {
  kind: AbsenceKind;
  label: string;
  /** A one-line meaning, plain-language (the local advocate is the design center). */
  meaning: string;
  /** The distinguishing symbol overlaid on the shared hatch (a non-colour channel). */
  symbol: string;
  /** Whether clicking generates a research task. Absence is an invitation, not a dead end. */
  taskable: boolean;
}

export const ABSENCE_KIND_META: Record<AbsenceKind, AbsenceKindMeta> = Object.fromEntries(
  ABSENCE_KINDS.map((kind) => {
    const state = lexiconState("absence", kind);
    return [
      kind,
      {
        kind,
        label: state.label, // K14 §3.4 short labels: "None found", "Stated absent"
        meaning: state.plain,
        symbol: state.symbol!,
        taskable: true,
      },
    ];
  }),
) as Record<AbsenceKind, AbsenceKindMeta>;

/** The single shared hatch texture class (SIG-UI-007: exactly one texture). */
export const ABSENCE_HATCH_CLASS = "sig-absence-hatch";

// --- The contradiction value range (§29.1, SIG-UI-009) ---------------------

/** One competing claim plotted on the contradiction range. */
export interface CompetingClaim {
  claimId: string;
  value: number;
  source: string;
  /** The evidence tier, e.g. "W3" / "R3" (§10). */
  tier: string;
  date: string;
  documentUrl: string;
  /**
   * Set when this claim measures a *different quantity* than the others (§29.1) —
   * so the reader sees "42 vs 38" need not be a disagreement at all.
   */
  differentQuantityNote?: string;
}

export interface ContradictionRange {
  min: number;
  max: number;
  claims: CompetingClaim[];
}

/** Build the plotted value range from the competing claims (SIG-UI-009). */
export function contradictionRange(claims: CompetingClaim[]): ContradictionRange {
  if (claims.length === 0) {
    throw new Error("a contradiction range needs at least one competing claim");
  }
  const values = claims.map((c) => c.value);
  return { min: Math.min(...values), max: Math.max(...values), claims };
}

/** The fractional position (0..1) of a value within the range, for plotting. */
export function plotPosition(range: ContradictionRange, value: number): number {
  if (range.max === range.min) return 0.5;
  return (value - range.min) / (range.max - range.min);
}
