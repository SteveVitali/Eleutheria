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
 */

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
  resolution_status: "Resolution",
  support: "Support",
  agreement: "Agreement",
  currency: "Currency",
};

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
  const words = support.toLowerCase().replace(/_/g, " ");
  return `Support: ${words} (${filled} of ${GLYPH_STEP_COUNT})`;
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

/** The persistent contested marker glyph + its accessible label. */
export const CONTESTED_MARKER = {
  glyph: "\u2260", // ≠ — a non-colour channel (SIG-UI-005)
  label: "Contested value",
} as const;

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

export const ABSENCE_KIND_META: Record<AbsenceKind, AbsenceKindMeta> = {
  NOT_RESEARCHED: {
    kind: "NOT_RESEARCHED",
    label: "Not researched",
    meaning: "SIG has not looked yet. Absence of a row is not evidence of absence.",
    symbol: "?",
    taskable: true,
  },
  NO_EVIDENCE_FOUND: {
    kind: "NO_EVIDENCE_FOUND",
    label: "No evidence found",
    meaning: "SIG searched named sources and found nothing.",
    symbol: "\u2205", // ∅
    taskable: true,
  },
  EVIDENCE_OF_ABSENCE: {
    kind: "EVIDENCE_OF_ABSENCE",
    label: "Evidence of absence",
    meaning: "A source affirmatively asserts this does not exist.",
    symbol: "\u2717", // ✗
    taskable: true,
  },
  UNRESOLVED: {
    kind: "UNRESOLVED",
    label: "Unresolved",
    meaning: "Evidence exists and disagrees; no resolution is defensible.",
    symbol: "\u26A0", // ⚠
    taskable: true,
  },
};

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
