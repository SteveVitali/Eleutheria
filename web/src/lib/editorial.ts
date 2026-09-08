// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * Editorial standards (§41), as pure data + logic. This module owns the conformance
 * gate this ticket is responsible for:
 *
 *   - the **six register rules** (SIG-UI-043) as data, each with a conformant and a
 *     non-conformant example;
 *   - a **register conformance checker** (SIG-UI-046) — a denylist of characterizing,
 *     motive-attributing, and editorializing language — applied to hand-written copy
 *     AND to generated rationale templates, because generated text is published text;
 *   - the **three example editorial cases** (SIG-UI-045) — a pending lawsuit, a
 *     policy/configuration divergence, and a cancellation with hardware remaining —
 *     as the exact conformant copy the spec specifies;
 *   - the **hostile-reader review** model (SIG-UI-042): a recorded review committed
 *     with the dossier template version, with a release-blocking rule that every
 *     finding be dispositioned.
 */

// --- The six register rules (SIG-UI-043) -------------------------------------

export interface RegisterRule {
  n: number;
  rule: string;
  /** A one-line elaboration in the reporting register. */
  detail: string;
  conformant: string;
  nonConformant: string;
}

/** The six register rules of SIG-UI-043, verbatim, each with a worked example. */
export const REGISTER_RULES: readonly RegisterRule[] = [
  {
    n: 1,
    rule: "Report; do not characterize.",
    detail: "State what a source says happened, not a loaded summary of it.",
    conformant: "The portal reported 38 cameras on 2026-07-01.",
    nonConformant: "The department admitted to only 38 cameras.",
  },
  {
    n: 2,
    rule: "Never state an allegation as a fact.",
    detail: "The epistemic_status of the claim governs the verb.",
    conformant: "A complaint filed 2026-03-04 alleges a wrongful stop.",
    nonConformant: "A misread plate caused a wrongful stop.",
  },
  {
    n: 3,
    rule: "Attribute every evaluative statement to its source.",
    detail: "An evaluation without an owner reads as SIG's opinion; it is not.",
    conformant: "The auditor's report described the retention setting as non-compliant.",
    nonConformant: "The retention setting is non-compliant.",
  },
  {
    n: 4,
    rule: "Prefer the specific and dated to the general and timeless.",
    detail: "A dated observation is verifiable; a timeless generality is not.",
    conformant: "As of the 2026-07-01 snapshot, 38 devices reported.",
    nonConformant: "The city has dozens of cameras everywhere.",
  },
  {
    n: 5,
    rule: "Name uncertainty in the same sentence as the number.",
    detail: "A number without its uncertainty is a false certainty.",
    conformant: "At least 31 devices are mapped (a lower bound; more may exist).",
    nonConformant: "There are 31 devices.",
  },
  {
    n: 6,
    rule: "Do not editorialize about motive.",
    detail: "SIG documents what institutions do, not why.",
    conformant: "The contract was approved on the consent agenda with no public comment.",
    nonConformant: "The council quietly rammed the contract through to avoid scrutiny.",
  },
];

// --- The register conformance checker (SIG-UI-046) ---------------------------

/**
 * Language that violates the register rules — characterizing verbs (rule 1), stating
 * an allegation as fact (rule 2), and editorializing about motive (rule 6). This is
 * the mechanically-checkable core of the style guide: like the recommender's
 * neutrality denylist, it makes conformance a STRUCTURAL, testable property rather
 * than a discipline that erodes. The list is deliberately conservative — it flags the
 * classic tells, not every possible lapse — and it is applied to generated rationale
 * templates too (SIG-UI-046: generated text is published text).
 */
export const FORBIDDEN_REGISTER_TERMS: readonly { term: RegExp; rule: number; why: string }[] = [
  { term: /\badmitted\b/i, rule: 1, why: "characterizing verb — report what was stated, do not characterize" },
  { term: /\bconfessed\b/i, rule: 1, why: "characterizing verb (rule 1)" },
  { term: /\bcracked down\b/i, rule: 1, why: "characterizing phrase (rule 1)" },
  { term: /\bquietly\b/i, rule: 6, why: "imputes motive/secrecy (rule 6)" },
  { term: /\brammed through\b/i, rule: 6, why: "editorializes about motive (rule 6)" },
  { term: /\bto avoid scrutiny\b/i, rule: 6, why: "imputes motive (rule 6)" },
  { term: /\bin order to\b/i, rule: 6, why: "imputes motive (rule 6) — state what was done, not why" },
  { term: /\bobviously\b/i, rule: 3, why: "unattributed evaluation (rule 3)" },
  { term: /\bshamefully\b/i, rule: 6, why: "editorializing adverb (rule 6)" },
  { term: /\begregious\b/i, rule: 3, why: "unattributed evaluation (rule 3)" },
];

export interface RegisterViolation {
  rule: number;
  term: string;
  why: string;
}

/**
 * Check a piece of published text against the register rules (SIG-UI-046). Returns
 * every violation found (empty = conformant). Used both to lint hand-written copy and
 * to gate generated rationale templates in tests and at build.
 */
export function checkRegisterConformance(text: string): RegisterViolation[] {
  const violations: RegisterViolation[] = [];
  for (const { term, rule, why } of FORBIDDEN_REGISTER_TERMS) {
    const m = text.match(term);
    if (m) violations.push({ rule, term: m[0], why });
  }
  return violations;
}

/** Throw when text violates the register rules — the release-blocking form (SIG-UI-046). */
export function assertRegisterConformant(text: string, context: string): void {
  const violations = checkRegisterConformance(text);
  if (violations.length > 0) {
    const detail = violations.map((v) => `rule ${v.rule} ("${v.term}": ${v.why})`).join("; ");
    throw new Error(`register-rule violation in ${context}: ${detail}`);
  }
}

// --- The three example editorial cases (SIG-UI-045) --------------------------

export interface EditorialCase {
  id: string;
  title: string;
  /** The exact conformant copy the spec specifies (SIG-UI-045). */
  copy: string;
}

/** The three hardest cases, rendered as the spec's exact conformant copy (SIG-UI-045). */
export const EDITORIAL_CASES: readonly EditorialCase[] = [
  {
    id: "pending_lawsuit",
    title: "A pending lawsuit",
    copy:
      "A complaint filed 2026-03-04 in [court] alleges that a plate misread led to a " +
      "wrongful stop. The allegation has not been adjudicated. The department has not " +
      "filed a public response as of 2026-08-20. [complaint, p. 4]",
  },
  {
    id: "policy_configuration_divergence",
    title: "A policy/configuration divergence",
    copy:
      "The department's written policy, adopted 2025-11-02, prohibits use of the system " +
      "for immigration enforcement. A configuration export dated 2026-05-02, obtained by " +
      "records request, shows an immigration-related hotlist enabled. SIG has not " +
      "determined which reflects current practice; both documents are linked, and this " +
      "is an open question.",
  },
  {
    id: "cancellation_hardware_remaining",
    title: "A cancellation with hardware remaining",
    copy:
      "The city council voted on 2026-07-14 not to renew the contract, which expires " +
      "2026-09-30. As of the most recent field observation on 2026-08-11, 23 devices " +
      "remain physically installed. SIG has no evidence about whether they are " +
      "operational. This is not a record of surveillance being removed.",
  },
];

// --- The hostile-reader review (SIG-UI-042) ----------------------------------

/** How a finding of the hostile-reader review was dispositioned. */
export const FINDING_DISPOSITIONS = ["accepted_revised", "accepted_annotated", "rejected_with_reason"] as const;
export type FindingDisposition = (typeof FINDING_DISPOSITIONS)[number];

export interface ReviewFinding {
  id: string;
  /** The sentence or claim the reviewer would challenge as the org's counsel. */
  challenge: string;
  disposition: FindingDisposition | null;
  /** The resolution note — required once dispositioned. */
  resolution: string;
}

/**
 * A recorded hostile-reader review of a dossier template version (SIG-UI-042): two
 * reviewers independently read a real rendered dossier adopting the stance of the
 * documented organization's counsel, log every sentence they would challenge, and
 * sign off. The review, its findings, and their disposition are committed alongside
 * the template version; release is blocked until every finding is dispositioned.
 */
export interface HostileReaderReview {
  /** The dossier template version this review is bound to (committed alongside it). */
  template_version: string;
  /** The rendered dossier the reviewers read (a real render, not a mock). */
  reviewed_dossier: string;
  /** Two independent reviewers (SIG-UI-042 requires two). */
  reviewers: string[];
  review_date: string;
  findings: ReviewFinding[];
}

/** Whether every finding has been dispositioned (with a resolution note). */
export function allFindingsDispositioned(review: HostileReaderReview): boolean {
  return review.findings.every((f) => f.disposition !== null && f.resolution.trim().length > 0);
}

/** The findings still open — the ones blocking release (SIG-UI-042). */
export function openFindings(review: HostileReaderReview): ReviewFinding[] {
  return review.findings.filter((f) => f.disposition === null || f.resolution.trim().length === 0);
}

/**
 * The release gate (SIG-UI-042): release is BLOCKED until every finding is
 * dispositioned, and the review must have two independent reviewers. Throws
 * otherwise — a template version whose hostile-reader review has open findings can
 * never be rendered/released. This is the executable form of the SIG-UI-042 gate.
 */
export function assertReviewReleasable(review: HostileReaderReview): void {
  if (review.reviewers.length < 2) {
    throw new Error(
      `hostile-reader review for ${review.template_version} needs two independent reviewers (SIG-UI-042); got ${review.reviewers.length}`,
    );
  }
  const open = openFindings(review);
  if (open.length > 0) {
    throw new Error(
      `release blocked (SIG-UI-042): ${open.length} hostile-reader finding(s) undispositioned for ${review.template_version}: ${open
        .map((f) => f.id)
        .join(", ")}`,
    );
  }
}
