// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * The public research-queue surface (§39.7, SIG-UI-031), as pure data + logic.
 *
 * The research queue is what turns the graph into a research-*coordination* system
 * rather than a passive database (§33): every open gap becomes a task card that
 * states, plainly, **what would close it**, **what evidence is sought**, **who it is
 * for**, and **how much effort it is**. This module owns that view model, colour-free,
 * plus the three coordination affordances the spec names:
 *
 *   - **geographic filtering** of the queue (SIG-TASK-010, §33.5);
 *   - **claiming with expiry** — a claim grants priority, never exclusivity, and it
 *     expires without renewal so an abandoned claim returns to the pool
 *     (SIG-TASK-010/011, SIG-TASK-007);
 *   - the **full disposition vocabulary** richer than "done", including
 *     `resolved_no_evidence_exists` ("searched, found nothing"), which is the
 *     mechanism by which a negative result becomes data and the queue can *shrink*
 *     (SIG-TASK-008/009, §33.4).
 *
 * The vocabularies here are a faithful mirror of the engine's controlled
 * vocabularies (`tasks/src/tasks/vocabulary.py`) and catalog fields
 * (`tasks/src/tasks/catalog.py`, `spec.py`) — the field names are the engine's, so
 * wiring the surface to the live queue is a data-source swap, not a component change.
 */

// --- The controlled vocabularies (mirror of tasks.vocabulary, §33.1/33.4) ----

/** Who a task type is routed to — the seven classes of §33.1 (AssigneeClass). */
export const ASSIGNEE_CLASSES = [
  "field_mapper",
  "records_requester",
  "document_reviewer",
  "analyst",
  "local_group",
  "curator",
  "developer",
] as const;
export type AssigneeClass = (typeof ASSIGNEE_CLASSES)[number];

/** A coarse effort band (§33.1, EffortEstimate) — typed without pretending to minutes. */
export const EFFORT_ESTIMATES = ["quick", "moderate", "substantial"] as const;
export type EffortEstimate = (typeof EFFORT_ESTIMATES)[number];

/** The queue-assignment geographic scope of a task type (§33.1, GeographicScope). */
export const GEOGRAPHIC_SCOPES = ["jurisdiction", "region", "global"] as const;
export type GeographicScope = (typeof GEOGRAPHIC_SCOPES)[number];

/**
 * The honest label a task's classification fields carry when its task type is
 * NOT in the §33.2 catalog (a legacy/hand-inserted row, or catalog drift).
 * P34.12 (K11 RQ-00, C3 NEW-10): the queue never invents a `contributor`
 * assignee or an `unknown` effort — an unclassified field says exactly that.
 * The literal is mirrored verbatim by the export shaper
 * (`exports/src/exports/spine_export.py::NOT_YET_CLASSIFIED`) — the two are the
 * same contract, kept in lockstep by test.
 */
export const NOT_YET_CLASSIFIED = "not yet classified";

/**
 * The disposition vocabulary richer than "done" (§33.4, SIG-TASK-008). The queue
 * must be able to *shrink*: without `resolved_no_evidence_exists` and the blocked/
 * deferred outcomes, a task can only ever close by success and the backlog only
 * grows — which is how contributor systems die (§33.4).
 */
export const DISPOSITIONS = [
  "resolved_evidence_found",
  "resolved_no_evidence_exists",
  "blocked_access_denied",
  "blocked_fee",
  "blocked_awaiting_response",
  "not_actionable",
  "superseded",
  "deferred",
] as const;
export type Disposition = (typeof DISPOSITIONS)[number];

/** Plain-language meanings for each disposition (the local advocate is the design center). */
export const DISPOSITION_META: Record<Disposition, string> = {
  resolved_evidence_found: "The evidence was obtained; claims landed.",
  resolved_no_evidence_exists:
    "Searched; the record does not exist. Writes a coverage record — the search itself is data (SIG-TASK-009).",
  blocked_access_denied: "The request was denied; the denial is recorded as evidence.",
  blocked_fee: "A fee demand blocks it; the amount is recorded.",
  blocked_awaiting_response: "Filed and pending a response.",
  not_actionable: "The detector fired on a modelling artifact, not a real gap.",
  superseded: "Another task subsumes this one.",
  deferred: "Valid, but not now — carries a review date.",
};

/** The "searched, found nothing" disposition the spec calls out explicitly (SIG-UI-031). */
export const SEARCHED_FOUND_NOTHING: Disposition = "resolved_no_evidence_exists";

// --- The task card (the §39.7 view model) ------------------------------------

/**
 * A research-queue task card (SIG-UI-031). It states the four fields the spec
 * requires — closing condition, evidence sought, assignee class, effort estimate —
 * plus the fields the queue needs to be filterable and claimable. `subject_id` +
 * `task_type` are the `(task_type, subject)` de-duplication key (SIG-TASK-007).
 */
export interface ResearchTaskCard {
  /**
   * The task's own id (the `research_task` row id), emitted by the export since
   * P34.12 (K11 RQ-00 / NEW-10: the export previously discarded it). Optional —
   * a card produced by an older export still parses, and `taskAnchor` falls
   * back to the `(task_type, subject_id)` dedup key (SIG-TASK-007).
   */
  task_id?: string;
  task_type: string;
  subject_id: string;
  subject_label: string;
  /** What evidence would close the task — testable, never "research this" (SIG-TASK-002). */
  closing_condition: string;
  /** The specific evidence sought (the document/observation to obtain). */
  evidence_sought: string;
  /**
   * A catalog assignee class (§33.1), or `not yet classified` when the task's
   * type is not in the catalog — never an invented class like `contributor`.
   */
  assignee_class: AssigneeClass | typeof NOT_YET_CLASSIFIED;
  /** A catalog effort band, or `not yet classified` — never `unknown`. */
  effort_estimate: EffortEstimate | typeof NOT_YET_CLASSIFIED;
  /** A catalog queue-assignment scope, or `not yet classified`. */
  geographic_scope: GeographicScope | typeof NOT_YET_CLASSIFIED;
  /** The jurisdiction the task is scoped to, for geographic filtering (§33.5). */
  jurisdiction: string;
  /**
   * The outcomes this task may reach — the catalog task type's permitted
   * §33.4 outcomes; for an unclassified type, the FULL §33.4 vocabulary (every
   * outcome is legal), never `[]` merely because no current disposition is set.
   */
  dispositions: Disposition[];
  priority: number;
  /**
   * What made the detector fire — the materialized contradiction / coverage gap /
   * relationship this task cites as its trigger (P29.2, every generated task cites its
   * trigger). Optional: absent for a legacy or hand-inserted task.
   */
  trigger?: { kind: string; ref: string };
}

/** The set of dispositions a task may reach, by assignee class (§33.4 mirror of catalog). */
const _COMMON: Disposition[] = ["resolved_evidence_found", "not_actionable", "superseded", "deferred"];
const _WITH_NO_EVIDENCE: Disposition[] = [..._COMMON, "resolved_no_evidence_exists"];
const _RECORDS: Disposition[] = [
  ..._WITH_NO_EVIDENCE,
  "blocked_access_denied",
  "blocked_fee",
  "blocked_awaiting_response",
];

export const DISPOSITIONS_BY_ASSIGNEE: Record<AssigneeClass, Disposition[]> = {
  records_requester: _RECORDS,
  document_reviewer: _RECORDS,
  field_mapper: _WITH_NO_EVIDENCE,
  local_group: _WITH_NO_EVIDENCE,
  analyst: _WITH_NO_EVIDENCE,
  curator: _COMMON,
  developer: _COMMON,
};

/**
 * The dispositions a task of a given assignee class may reach. A task that can
 * conclude "searched, found nothing" is one whose assignee does search work
 * (field/records/analyst/local-group), never a curator/developer clean-up task.
 */
export function dispositionsFor(assignee: AssigneeClass): Disposition[] {
  return DISPOSITIONS_BY_ASSIGNEE[assignee];
}

/** Whether a task can conclude "searched, found nothing" (writes a coverage record). */
export function canRecordNoEvidence(card: ResearchTaskCard): boolean {
  return card.dispositions.includes(SEARCHED_FOUND_NOTHING);
}

// --- Task anchors (P34.12 / K11 RQ-00: unique ids, no dead anchors) ----------

/**
 * The DOM id a task card renders under: `task-<task_id>` when the card carries
 * its task id, else `task-<task_type>--<subject_id>` — the SIG-TASK-007 dedup
 * key, which is unique per open task by contract (duplicate suppression is BY
 * `(task_type, subject)`). Sanitized to an HTML-safe id; two cards NEVER share
 * the jurisdiction-derived id (the pre-P34.12 defect that produced duplicate
 * DOM ids and ambiguous anchors).
 */
export function taskAnchor(card: ResearchTaskCard): string {
  const raw = card.task_id ?? `${card.task_type}--${card.subject_id}`;
  return `task-${raw.replace(/[^a-zA-Z0-9-]+/g, "-")}`;
}

/**
 * Fail LOUD if two rendered cards would share an anchor (K11 RQ-00). A
 * collision means the data broke the `(task_type, subject)` uniqueness
 * contract — the page refuses to render over it rather than emitting
 * ambiguous duplicate ids.
 */
export function assertUniqueTaskAnchors(cards: readonly ResearchTaskCard[]): void {
  const seen = new Map<string, ResearchTaskCard>();
  for (const card of cards) {
    const anchor = taskAnchor(card);
    const prior = seen.get(anchor);
    if (prior !== undefined) {
      throw new Error(
        `research queue: two cards share the anchor ${anchor} ` +
          `((${prior.task_type}, ${prior.subject_id}) and (${card.task_type}, ${card.subject_id})) — ` +
          "a task-id/dedup-key collision can never render as a duplicate DOM id",
      );
    }
    seen.set(anchor, card);
  }
}

/**
 * The jurisdiction → live anchor map for the filter list (K11 RQ-00): each
 * jurisdiction links to the anchor of the FIRST rendered card carrying it, so
 * every `href="#…"` in the filter resolves to an element that exists on the
 * page. Derived from the rendered rows — a jurisdiction whose cards are all
 * beyond the row cap is simply not listed (no dead anchors).
 */
export function jurisdictionAnchors(cards: readonly ResearchTaskCard[]): Map<string, string> {
  const anchors = new Map<string, string>();
  for (const card of cards) {
    if (!anchors.has(card.jurisdiction)) anchors.set(card.jurisdiction, taskAnchor(card));
  }
  return anchors;
}

// --- Geographic filtering (§33.5, SIG-TASK-010) ------------------------------

/** The distinct jurisdictions present in the queue, sorted — the filter options. */
export function queueJurisdictions(cards: readonly ResearchTaskCard[]): string[] {
  return [...new Set(cards.map((c) => c.jurisdiction))].sort();
}

/**
 * Filter the queue to a jurisdiction (§33.5). A `global`-scope task is visible in
 * every jurisdiction's view — it is not tied to one place — so it is never filtered
 * out; a place-scoped task shows only under its own jurisdiction.
 */
export function tasksForJurisdiction(
  cards: readonly ResearchTaskCard[],
  jurisdiction: string,
): ResearchTaskCard[] {
  return cards.filter((c) => c.geographic_scope === "global" || c.jurisdiction === jurisdiction);
}

// --- Claiming with expiry (§33.5, SIG-TASK-010/011) --------------------------

/**
 * A jurisdiction claim: a coordination affordance, NOT exclusivity (SIG-TASK-011).
 * It grants visibility, notification, and priority in queue ordering — and it
 * EXPIRES without renewal, so it can never harden into territorial gatekeeping.
 */
export interface JurisdictionClaim {
  jurisdiction: string;
  claimed_by: string;
  claimed_at: string; // ISO date
  expires_at: string; // ISO date
}

/** Whether a claim is still live as of a given date (a claim expires without renewal). */
export function claimIsActive(claim: JurisdictionClaim, asOf: string): boolean {
  return asOf < claim.expires_at;
}

/**
 * The claim status shown on a task card: whether the jurisdiction is currently
 * claimed, by whom, and until when. Critically it also reports that any contributor
 * may still work the task — the claim grants priority, not a lock (SIG-TASK-011).
 */
export interface ClaimStatus {
  claimed: boolean;
  claimed_by: string | null;
  expires_at: string | null;
  /** Always true: geographic claiming NEVER grants exclusivity (SIG-TASK-011). */
  anyone_may_work: true;
}

export function claimStatusFor(
  card: ResearchTaskCard,
  claims: readonly JurisdictionClaim[],
  asOf: string,
): ClaimStatus {
  const active = claims.find((c) => c.jurisdiction === card.jurisdiction && claimIsActive(c, asOf));
  return {
    claimed: active !== undefined,
    claimed_by: active?.claimed_by ?? null,
    expires_at: active?.expires_at ?? null,
    anyone_may_work: true,
  };
}

// --- Queue ordering ----------------------------------------------------------

/**
 * Order the queue for display: a claimed jurisdiction's tasks first (the priority a
 * live claim grants, SIG-TASK-010), then by descending task priority, then by a
 * stable key. Recognition is qualitative — there is NO volume leaderboard here
 * (SIG-TASK-012) and this ordering carries no contributor ranking at all.
 */
export function orderQueue(
  cards: readonly ResearchTaskCard[],
  claims: readonly JurisdictionClaim[],
  asOf: string,
): ResearchTaskCard[] {
  const claimedJurisdictions = new Set(
    claims.filter((c) => claimIsActive(c, asOf)).map((c) => c.jurisdiction),
  );
  return [...cards].sort((a, b) => {
    const aClaimed = claimedJurisdictions.has(a.jurisdiction) ? 0 : 1;
    const bClaimed = claimedJurisdictions.has(b.jurisdiction) ? 0 : 1;
    if (aClaimed !== bClaimed) return aClaimed - bClaimed;
    if (a.priority !== b.priority) return b.priority - a.priority;
    return a.task_type.localeCompare(b.task_type);
  });
}
