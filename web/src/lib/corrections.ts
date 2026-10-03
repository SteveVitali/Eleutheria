// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * The public corrections log + the dispute/correction submission path (§39.8, §45),
 * as pure data + logic.
 *
 * Two first-class surfaces live here:
 *
 *   - **The public corrections log (SIG-UI-032)** — the required *eighth* surface the
 *     outline omits. Every correction is listed with **what changed, when, why, and
 *     who reported it**. A correction is a NEW assertion, never a deletion
 *     (SIG-GOV-005): the erroneous value is preserved, so each entry carries a link
 *     recording the belief date at which the earlier value stood. (P34.11 / QW-5: the
 *     helper keeps its `priorValuePermalink` name for the wire contract, but the copy
 *     never calls the link a "permalink" before real `/s/` pins exist.)
 *
 *   - **The dispute/correction submission path (SIG-UI-033, §45.1)** — linked from
 *     every page through the base layout. It accepts the five §45.1 categories by
 *     e-mail (WV-05 / ADR-180: the anonymous-receiver intake requirement is
 *     waived — senders disclose the address they send from), promises NO
 *     response time, and publishes the handling order (WV-08 / ADR-186: SIG-GOV-003's
 *     SLA clause is waived; the priority clause is met by the published order —
 *     privacy-harm and safety reports first, then factual corrections, then
 *     everything else).
 *
 * This ticket *surfaces and submits* — the correction-as-new-assertion storage
 * semantics (§45 backend, SIG-STORE-020/SIG-TIME-009) are owned upstream and are out
 * of scope here (see the ticket's scope guard).
 */

import { beliefPinnedPermalink } from "./citation";
import type { AsOfEcho } from "./fixtures";

// --- The §45.1 intake categories (SIG-GOV-001) -------------------------------

/** The five submission categories the public intake channel accepts (§45.1). */
export const SUBMISSION_CATEGORIES = [
  "factual_error",
  "privacy_harm",
  "legal_demand",
  "security_concern",
  "copyright_claim",
] as const;
export type SubmissionCategory = (typeof SUBMISSION_CATEGORIES)[number];

export interface SubmissionCategoryMeta {
  category: SubmissionCategory;
  label: string;
  /** Plain-language description of what this category is for. */
  description: string;
  /**
   * Whether the category's substance may require identifying the submitter.
   * Only a legal demand may — where it requires standing (SIG-GOV-002, waived in
   * part by WV-05: under e-mail intake EVERY sender discloses the address they
   * send from; nothing here promises anonymity).
   */
  requiresIdentity: boolean;
  /**
   * The published handling-priority band (SIG-GOV-003). Privacy-harm and safety
   * (security) claims are prioritized ABOVE all others, including factual corrections.
   * Lower number = handled first.
   */
  priorityBand: number;
}

export const SUBMISSION_CATEGORY_META: Record<SubmissionCategory, SubmissionCategoryMeta> = {
  privacy_harm: {
    category: "privacy_harm",
    label: "Privacy harm",
    description: "This record exposes someone to a concrete privacy or safety harm.",
    requiresIdentity: false,
    priorityBand: 0,
  },
  security_concern: {
    category: "security_concern",
    label: "Security concern",
    description: "A safety or security risk arising from this material.",
    requiresIdentity: false,
    priorityBand: 0,
  },
  factual_error: {
    category: "factual_error",
    label: "Factual error",
    description: "A claim is wrong, out of date, or misattributed.",
    requiresIdentity: false,
    priorityBand: 1,
  },
  legal_demand: {
    category: "legal_demand",
    label: "Legal demand",
    description: "A formal legal request. This is the one category that may require standing.",
    requiresIdentity: true,
    priorityBand: 1,
  },
  copyright_claim: {
    category: "copyright_claim",
    label: "Copyright claim",
    description: "A claim that copyrighted material is used without permission.",
    requiresIdentity: false,
    priorityBand: 1,
  },
};

/** The categories in published handling-priority order (SIG-GOV-003), then stable. */
export function categoriesByPriority(): SubmissionCategoryMeta[] {
  return SUBMISSION_CATEGORIES.map((c) => SUBMISSION_CATEGORY_META[c]).sort(
    (a, b) => a.priorityBand - b.priorityBand || a.category.localeCompare(b.category),
  );
}

// --- The submission path (SIG-UI-033) ----------------------------------------

/** The canonical path of the public dispute/correction intake page. */
export const DISPUTE_PATH = "/dispute/";

/**
 * The submission href for a specific claim (SIG-UI-033). It carries the
 * subject/predicate the claim is about (and the belief-time it was seen at) so the
 * intake page can pre-fill "what this is about" — a plain GET, no client JavaScript
 * (SIG-UI-036/037). With no arguments it is the generic intake link every page
 * carries, so the channel is one link away from anywhere.
 */
export function disputeHref(about?: { subject_id?: string; predicate_id?: string; as_of_belief?: string }): string {
  if (!about) return DISPUTE_PATH;
  const q = new URLSearchParams();
  if (about.subject_id) q.set("subject", about.subject_id);
  if (about.predicate_id) q.set("predicate", about.predicate_id);
  if (about.as_of_belief) q.set("as_of_belief", about.as_of_belief);
  const qs = q.toString();
  return qs ? `${DISPUTE_PATH}?${qs}` : DISPUTE_PATH;
}

// --- The correction log entry (SIG-UI-032, §45.3) ----------------------------

/**
 * The permitted outcomes of a submission (SIG-GOV-004). Refusal MUST be a real,
 * exercisable option with published reasoning — a process that cannot say no is a
 * heckler's veto. Suppression is a primitive DISTINCT from deletion (SIG-GOV-007):
 * it removes material from public view while retaining it internally under seal;
 * deletion is reserved for material SIG must not hold at all (SIG-GOV-008).
 */
export const CORRECTION_OUTCOMES = [
  "corrected",
  "annotated",
  "suppressed",
  "deleted",
  "refused",
] as const;
export type CorrectionOutcome = (typeof CORRECTION_OUTCOMES)[number];

// P34.17 (R1.2 / C4 NEW-20): requirement ids are internal machinery — the public
// copy names the behaviour, never the id. Batch rows OC-01…OC-05 pin the text.
export const CORRECTION_OUTCOME_META: Record<CorrectionOutcome, string> = {
  corrected: "A new, corrected assertion was appended; the prior value is preserved.",
  annotated: "A response or annotation was attached alongside the claim.",
  suppressed: "Removed from public view, retained internally under seal.",
  deleted: "Deleted entirely; a content-free tombstone records that a deletion occurred.",
  refused: "Declined, with published reasoning.",
};

/**
 * One entry in the public corrections log (SIG-UI-032). It records the four required
 * facts — WHAT changed, WHEN, WHY, and WHO reported it — plus the outcome and a link
 * recording the belief date at which the earlier value stood (SIG-GOV-005,
 * SIG-UI-035).
 */
export interface CorrectionEntry {
  id: string;
  subject_id: string;
  subject_label: string;
  /** What changed — the field and the before → after, in the reporting register. */
  what_changed: string;
  /** When the correction was made (the belief-time the new assertion was appended). */
  corrected_at: string;
  /** Why — the reason for the correction. */
  reason: string;
  /** Who reported it (a role/handle, or "anonymous"; never forced identity, SIG-GOV-002). */
  reported_by: string;
  category: SubmissionCategory;
  outcome: CorrectionOutcome;
  /** The prior (now-superseded) value, preserved and still citable at its belief-time. */
  previous_value: string;
  corrected_value: string;
  /** The belief-time at which the erroneous value still re-resolves (SIG-GOV-005). */
  previous_belief_date: string;
  /** The canonical path of the subject, for the belief-pinned permalink. */
  subject_path: string;
  /**
   * P32.16a (SIG-FIND-008): the superseded/retracted assertion this entry
   * revises — the public corrections log names BOTH sides (§16.6). Absent on
   * older export bytes and fixtures.
   */
  previous_claim_id?: string;
  /** The claim this entry revises (= previous_claim_id for a revision). */
  revises_claim?: string;
  /** The claim this entry retracts (retraction outcome). */
  retraction_of?: string;
  /** True when the prior assertion exists but is itself gated — the honest
   *  withheld marker; its value/date stay off the public surface. */
  previous_withheld?: boolean;
}

/**
 * The link to the value AS IT STOOD before this correction, pinned to the prior
 * belief-date — recording what the page said then, proving the correction did not
 * rewrite history (SIG-GOV-005, SIG-TIME-008). (QW-5: the name stays for the wire;
 * the claim stays honest — a selector link, not an immutable pin.)
 */
export function priorValuePermalink(
  entry: CorrectionEntry,
  rulesetVersion: string,
  origin?: string,
): string {
  const asOf: AsOfEcho = {
    as_of_world: entry.previous_belief_date,
    as_of_belief: entry.previous_belief_date,
    world_defaulted: false,
    belief_defaulted: false,
    question: `as-of belief ${entry.previous_belief_date}`,
    belief_pinned: true,
  };
  return beliefPinnedPermalink({
    path: entry.subject_path,
    title: entry.subject_label,
    asOf,
    rulesetVersion,
    ...(origin ? { origin } : {}),
  });
}

// --- Transparency reporting (SIG-GOV-011) ------------------------------------

/**
 * Periodic counts of requests by category and outcome, INCLUDING refusals
 * (SIG-GOV-011). A transparency report that hides refusals is not one; refusals are
 * counted like every other outcome.
 */
export interface TransparencyReport {
  by_category: Record<SubmissionCategory, number>;
  by_outcome: Record<CorrectionOutcome, number>;
  total: number;
}

export function transparencyReport(entries: readonly CorrectionEntry[]): TransparencyReport {
  const by_category = Object.fromEntries(
    SUBMISSION_CATEGORIES.map((c) => [c, 0]),
  ) as Record<SubmissionCategory, number>;
  const by_outcome = Object.fromEntries(
    CORRECTION_OUTCOMES.map((o) => [o, 0]),
  ) as Record<CorrectionOutcome, number>;
  for (const e of entries) {
    by_category[e.category] += 1;
    by_outcome[e.outcome] += 1;
  }
  return { by_category, by_outcome, total: entries.length };
}

/** The corrections log, newest correction first (§45.3 preserves history, in order). */
export function orderedCorrections(entries: readonly CorrectionEntry[]): CorrectionEntry[] {
  return [...entries].sort((a, b) => b.corrected_at.localeCompare(a.corrected_at) || a.id.localeCompare(b.id));
}

// --- The durable receiver (P32.16, ADR-135, SIG-FIND-006) --------------------

/** The path the separate receiver process serves its no-JS report form on. */
export const INTAKE_FORM_PATH = "/intake/new";
/** The path the separate receiver process serves its receipt-check page on. */
export const INTAKE_STATUS_PATH = "/intake/status";

export interface IntakeAvailability {
  /**
   * Whether the durable receiver is accepting reports. It is gated on a staffed
   * moderation owner + retention ratification + the public-exposure decision
   * (GATE-G3 / HG-11, D-R10-PUBLISH-1) — this page must NEVER advertise an
   * unstaffed or unapproved receiver as operational (S4 §8).
   */
  operational: boolean;
  /** One-sentence honest state for the public page. */
  note: string;
}

/**
 * The receiver's current availability, as honest public copy. The receiver is
 * BUILT (`sig-api serve-intake`, durable receipts, private moderation queue)
 * but NOT YET OPERATING — a flip happens only in a later reviewed change with
 * the operating packet approved, so the descriptor is a constant, not a probe
 * (a static page must never promise a liveness it cannot see). P34.17 / WV-05
 * (ADR-180): the receiver is no longer described as "anonymous" — under
 * e-mail-only intake senders disclose the address they send from.
 */
export function intakeAvailability(): IntakeAvailability {
  return {
    operational: false,
    // Batch row DP-07 pins this sentence (B-2). No gate names in public copy
    // (C4 NEW-20): the approvals are described, not named.
    note:
      "An online report form is not operating yet — it opens only after a staffed " +
      "moderation owner, a ratified retention schedule and the public-exposure " +
      "decision are approved.",
  };
}
