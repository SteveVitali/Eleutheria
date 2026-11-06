// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * P37.7 (R11-GOV-02; ADR-164 / WV-02; spec §46.2 compensating controls;
 * design E2-governance-options.md E2-03) — the public editorial decision
 * log's committed record.
 *
 * The operator holds interim single-maintainer editorial authority over
 * contested claims and sensitivity classifications (SIG-GOV-015 waived,
 * WV-02); this log is the transparency that stands in for separation —
 * every naming, sensitivity and contested-claim decision gets an
 * append-only entry carrying date, decision, class, rationale and
 * evidence links, and every entry cites the GATE DECISIONS row it logs
 * (the catalogue acceptance shape).
 *
 *   - `sig.editorial-decision/1` — the entry contract. `class` is the
 *     closed vocabulary below; `decision` carries the recorded decision
 *     (operator words verbatim where they exist, quoted); `gate_ref`
 *     names the LEDGER § GATE DECISIONS row the entry logs.
 *   - `retroactive: true` marks the entries ADR-164 logs after the fact —
 *     `logged_at` is the day the entry joined this log, `decided_at` the
 *     day the GATE DECISIONS row records.
 *   - `deletion` / `purge` entries are tombstones (WV-06/WV-11): they
 *     carry `tombstone.category` + a date and NEVER the deleted content.
 *   - Entries name no private person (Part VIII); a correction is a new
 *     entry, never an edit.
 */

export const EDITORIAL_DECISION_SCHEMA = "sig.editorial-decision/1";

/** The closed class vocabulary (§46.2 + WV-06/WV-11 tombstone kinds). */
export const DECISION_CLASSES = [
  "authority",
  "sensitivity_classification",
  "naming",
  "contested_claim",
  "deletion",
  "purge",
] as const;
export type DecisionClass = (typeof DECISION_CLASSES)[number];

/** Public labels for the classes — the enum token never renders. */
export const DECISION_CLASS_LABELS: Record<DecisionClass, string> = {
  authority: "Editorial authority",
  sensitivity_classification: "Sensitivity classification",
  naming: "Naming",
  contested_claim: "Contested claim",
  deletion: "Deletion (tombstone)",
  purge: "Purge (tombstone)",
};

export interface EditorialDecision {
  schema: typeof EDITORIAL_DECISION_SCHEMA;
  /** Stable id — `ed:<decided-date>:<slug>`; never reused. */
  decision_id: string;
  /** The decision class (closed vocabulary above). */
  class: DecisionClass;
  /**
   * The time the cited GATE DECISIONS row records the decision as taken
   * (ISO-8601 date or timestamp).
   */
  decided_at: string;
  /** The date this entry was appended to the log (ISO-8601 date). */
  logged_at: string;
  /** true when the entry logs a decision taken before the log existed. */
  retroactive: boolean;
  /**
   * The decision as recorded — the operator's own words quoted verbatim
   * where a recorded sentence exists, otherwise the row's recorded
   * disposition. Never an agent paraphrase presented as the operator's.
   */
  decision: string;
  /** What the decision covers and what it does not — the recorded scope. */
  scope: string;
  /** Why, as recorded — attributed, never an imputed motive. */
  rationale: string;
  /**
   * The GATE DECISIONS row this entry cites — the acceptance shape:
   * `row` names the row as the ledger records it (date + row label),
   * `recorded_at` the row's own recorded time.
   */
  gate_ref: { row: string; recorded_at: string };
  /** Record links — repo paths and ADR ids a reader can follow. */
  evidence: readonly string[];
  /**
   * Tombstone entries only (classes `deletion` / `purge`): the deleted
   * material's category — never its content (SIG-GOV-008). Absent on
   * every other class.
   */
  tombstone?: { category: string } | null;
}

export function isEditorialDecision(v: unknown): v is EditorialDecision {
  const o = v as EditorialDecision | null;
  if (
    !o ||
    o.schema !== EDITORIAL_DECISION_SCHEMA ||
    typeof o.decision_id !== "string" ||
    !DECISION_CLASSES.includes(o.class) ||
    typeof o.decided_at !== "string" ||
    typeof o.logged_at !== "string" ||
    typeof o.retroactive !== "boolean" ||
    typeof o.decision !== "string" ||
    typeof o.scope !== "string" ||
    typeof o.rationale !== "string" ||
    !o.gate_ref ||
    typeof o.gate_ref.row !== "string" ||
    o.gate_ref.row.length === 0 ||
    typeof o.gate_ref.recorded_at !== "string" ||
    !Array.isArray(o.evidence)
  ) {
    return false;
  }
  // A tombstone entry carries a category and never content; a non-tombstone
  // entry carries no tombstone payload.
  if (o.class === "deletion" || o.class === "purge") {
    return !!o.tombstone && typeof o.tombstone.category === "string" && o.tombstone.category.length > 0;
  }
  return o.tombstone === undefined || o.tombstone === null;
}

// ---------------------------------------------------------------------------
// The log — append-only. New entries append; an entry is never edited or
// removed (a correction is a new entry).
// ---------------------------------------------------------------------------

export const EDITORIAL_DECISIONS: readonly EditorialDecision[] = [
  {
    schema: EDITORIAL_DECISION_SCHEMA,
    decision_id: "ed:2026-09-16:naming-off",
    class: "naming",
    decided_at: "2026-09-16",
    logged_at: "2026-11-06",
    retroactive: true,
    decision:
      "Officer and person naming stays default-no-publish. Recorded at the 2026-09-16 operator dispositions: the operator filled both reviewer roles personally and recorded written concurrence; SIG-PUB-008's independence requirement is waived, not satisfied.",
    scope:
      "The naming gate still returns False for person-named claims — no individual is named on the published surface. The waiver covers reviewer independence only; it is not a naming decision.",
    rationale:
      "Recorded at the operator's post-go-public dispositions (sole-maintainer posture). ADR-163 carries the publication posture.",
    gate_ref: {
      row: 'docs/build/LEDGER.md § GATE DECISIONS — 2026-09-16 "operator dispositions, post-go-public" (HG-11 resolved-by-operator)',
      recorded_at: "2026-09-16",
    },
    evidence: [
      "docs/build/reports/okc/concurrence.md",
      "docs/tickets/DEFERRALS.md — D-P21.4-2",
      "docs/adr/ADR-163-single-maintainer-publication-posture.md",
    ],
  },
  {
    schema: EDITORIAL_DECISION_SCHEMA,
    decision_id: "ed:2026-09-22:sensitivity-classes",
    class: "sensitivity_classification",
    decided_at: "2026-09-22",
    logged_at: "2026-11-06",
    retroactive: true,
    decision:
      "Publication sign-off for the Part-VIII-sensitive classes facial_recognition_world_map, pathways_rtcc_federation, pathways_acoustic_drone_location and officer/person-naming. The operator's words, verbatim: “I'd prefer to just err on the side of signing off on these now”.",
    scope:
      "A class-level publication sign-off, as the cited row records: the Part VIII data invariants are enforced mechanically regardless — no person or plate fields, coordinate reduction to the sensitivity tier, and the per-claim officer-naming check still returns False so individual named-person claims stay unpublished. Counsel (HG-02 proper) remains an operator action; this sign-off proceeds under the recorded interim no-counsel posture.",
    rationale:
      "Recorded at P27.2's HG-02 + Part VIII sign-off (the cited row): the operator signed off the sensitive classes for publication rather than holding them.",
    gate_ref: {
      row: 'docs/build/LEDGER.md § GATE DECISIONS — 2026-09-22 "P27.2 / HG-02 + Part VIII sign-off"',
      recorded_at: "2026-09-22",
    },
    evidence: [
      "docs/build/runs/P27.2.md",
      "docs/tickets/DEFERRALS.md — D-LEGAL.1-1",
      "docs/adr/ADR-164-interim-editorial-authority-and-public-decision-log.md",
    ],
  },
  {
    schema: EDITORIAL_DECISION_SCHEMA,
    decision_id: "ed:2026-10-01:interim-authority",
    class: "authority",
    decided_at: "2026-10-01T04:28:49Z",
    logged_at: "2026-11-06",
    retroactive: true,
    decision:
      "“I waive SIG-GOV-015's editorial board: I hold interim single-maintainer editorial authority, and every naming/sensitivity decision goes in a public decision log.” — the waiver sentence the operator adopted at GATE-P (WV-02, A-23 part 1).",
    scope:
      "The operator alone holds editorial authority over contested claims and sensitivity classifications, disclosed — never presented as a board. Officer and person naming stays off, so this authority never extends to naming an individual. A board is constituted when a legal-home entity exists or naming is wanted.",
    rationale:
      "Recorded at GATE-P (A-23 part 1, ratification log round 9; the A-4 posture package adopted at round 3). ADR-164 records the decision and its revisit triggers.",
    gate_ref: {
      row: "docs/build/LEDGER.md § GATE DECISIONS — 2026-10-01T05:03:05Z GATE-P (plan ratification), A-23 part 1 / WV-02 (ratification log round 9) and A-4 (round 3)",
      recorded_at: "2026-10-01T05:03:05Z",
    },
    evidence: [
      "docs/adr/ADR-164-interim-editorial-authority-and-public-decision-log.md",
      "docs/build/planning/2026-09-30-next-phase/feedback/RATIFICATION_LOG.md — rounds 3 and 9",
      "docs/2_canonical_design_spec.md §46.2 (the WV-02 waiver note)",
    ],
  },
];

/** The entries newest-decision-first — the log's public order. */
export function orderedDecisions(
  entries: readonly EditorialDecision[] = EDITORIAL_DECISIONS,
): EditorialDecision[] {
  return [...entries].sort((a, b) => b.decided_at.localeCompare(a.decided_at));
}

/** The date this log begins — the earliest entry's `logged_at` (the log
 *  never reads as if it had always run; cf. the corrections log's QW-14). */
export function logStartDate(
  entries: readonly EditorialDecision[] = EDITORIAL_DECISIONS,
): string | null {
  return entries.map((e) => e.logged_at).sort()[0] ?? null;
}
