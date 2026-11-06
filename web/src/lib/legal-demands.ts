// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * P37.8 (R11-GOV-03; ADR-166 / A-4 = Q-E2-09 c; spec §44.3 SIG-SEC-003) — the
 * committed records behind `/about/legal-demands/`: the adopted
 * demand-response posture's metadata and the published legal-demand counts.
 *
 *   - `sig.legal-demand-posture/1` — the posture record: when the operator
 *     adopted it (the A-4 log time), the ADR that records the decision, the
 *     governing document, and the two disclosures the decision pins — no
 *     counsel review (ADR-167) and the warrant canary declined.
 *   - `sig.legal-demand-counts/1` — a dated counts snapshot: legal demands
 *     received, complied with and refused — counts only. The interface has
 *     no requester-identity or case-detail field by construction (ADR-166
 *     decision 2; the transparency scrub and Part VIII rules, ADR-162).
 *     Snapshots are append-only: a demand arriving, or a demand's handling
 *     changing, appends a new dated snapshot — a snapshot is never edited.
 */

export const LEGAL_DEMAND_POSTURE_SCHEMA = "sig.legal-demand-posture/1";
export const LEGAL_DEMAND_COUNTS_SCHEMA = "sig.legal-demand-counts/1";

export interface LegalDemandPosture {
  schema: typeof LEGAL_DEMAND_POSTURE_SCHEMA;
  /** Stable id — `ldp:<adopted-date>`; a superseding posture is a new record. */
  posture_id: string;
  /** The time the operator adopted the posture (the A-4 log time). */
  adopted_at: string;
  /** The ADR that records the decision. */
  adr: string;
  /** The operator's decision as recorded in the plan cell, verbatim. */
  decision_ref: string;
  /** The governing written document the public page mirrors. */
  document: string;
  /** The warrant canary is declined (SIG-SEC-003's SHOULD), never operated. */
  canary: "declined";
  /** False forever on this record — SIG has no counsel (ADR-167). */
  counsel_reviewed: false;
}

export interface LegalDemandCounts {
  schema: typeof LEGAL_DEMAND_COUNTS_SCHEMA;
  /** Stable id — `ldc:<as_of>`; never reused. */
  snapshot_id: string;
  /** The date the counts hold as of (ISO-8601 date). */
  as_of: string;
  /** Legal demands received. */
  received: number;
  /** Legal demands complied with. */
  complied_with: number;
  /** Legal demands refused. */
  refused: number;
  /** The date this snapshot entered the record (ISO-8601 date). */
  recorded_at: string;
}

export function isLegalDemandPosture(v: unknown): v is LegalDemandPosture {
  const o = v as LegalDemandPosture | null;
  return (
    !!o &&
    o.schema === LEGAL_DEMAND_POSTURE_SCHEMA &&
    typeof o.posture_id === "string" &&
    o.posture_id.length > 0 &&
    typeof o.adopted_at === "string" &&
    typeof o.adr === "string" &&
    typeof o.decision_ref === "string" &&
    typeof o.document === "string" &&
    o.canary === "declined" &&
    o.counsel_reviewed === false
  );
}

export function isLegalDemandCounts(v: unknown): v is LegalDemandCounts {
  const o = v as LegalDemandCounts | null;
  return (
    !!o &&
    o.schema === LEGAL_DEMAND_COUNTS_SCHEMA &&
    typeof o.snapshot_id === "string" &&
    o.snapshot_id.length > 0 &&
    typeof o.as_of === "string" &&
    Number.isInteger(o.received) &&
    o.received >= 0 &&
    Number.isInteger(o.complied_with) &&
    o.complied_with >= 0 &&
    Number.isInteger(o.refused) &&
    o.refused >= 0 &&
    // counts only: a snapshot can never split received against complied +
    // refused, but it can never under-report either
    o.complied_with + o.refused <= o.received &&
    typeof o.recorded_at === "string"
  );
}

/** The adopted posture — ADR-166 (A-4, Q-E2-09 = c; the A-4 log time). */
export const LEGAL_DEMAND_POSTURE: LegalDemandPosture = {
  schema: LEGAL_DEMAND_POSTURE_SCHEMA,
  posture_id: "ldp:2026-10-01",
  adopted_at: "2026-10-01T04:03:25Z",
  adr: "ADR-166",
  decision_ref: "Q-E2-09 [A-4] = c",
  document: "docs/governance/legal-demand-posture.md",
  canary: "declined",
  counsel_reviewed: false,
};

// ---------------------------------------------------------------------------
// The count record — append-only. A demand arriving, or a demand's handling
// changing, appends a new dated snapshot; a snapshot is never edited.
// ---------------------------------------------------------------------------

export const LEGAL_DEMAND_COUNT_SNAPSHOTS: readonly LegalDemandCounts[] = [
  {
    schema: LEGAL_DEMAND_COUNTS_SCHEMA,
    snapshot_id: "ldc:2026-11-06",
    as_of: "2026-11-06",
    received: 0,
    complied_with: 0,
    refused: 0,
    recorded_at: "2026-11-06",
  },
];

/** The counts as of the latest snapshot — the public figure. */
export function latestCounts(
  snapshots: readonly LegalDemandCounts[] = LEGAL_DEMAND_COUNT_SNAPSHOTS,
): LegalDemandCounts | null {
  return snapshots.length === 0 ? null : snapshots[snapshots.length - 1]!;
}
