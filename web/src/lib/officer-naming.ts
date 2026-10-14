// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * The officer-naming decision registry — the persisted §43.4 gate the
 * publication path reads (P35.28, SIG-PUB-007/008, H-9).
 *
 * The single source of truth is the committed append-only table
 * `policy/src/policy/data/officer_naming_decisions.json`
 * (`sig.officer-naming-decisions/1`): one entry per recorded officer-naming
 * evaluation — the five SIG-PUB-007 prongs, the two independent reviewers'
 * written positions (SIG-PUB-008), the carve-out flags, and the recorded
 * verdict — keyed on the name row's `(subject_id, predicate_id)`. This module
 * is the faithful TypeScript mirror of `policy.officer`'s record layer: the
 * shell is static-first (SIG-UI-036) and reads no live API at build, so the
 * same lookup + replay the Python export gate makes is re-expressed here.
 *
 * DEFAULT DENY: a name row publishes only when a persisted record names it AND
 * the record's stored inputs replay to a permit. A missing record, a dissent or
 * single-reviewer record, a failed prong, a carve-out flag (SIG-PUB-009/010),
 * or an inconsistent record (stored `permitted` disagrees with the replay) all
 * withhold. A changed decision is a NEW record carrying `supersedes`; the
 * latest entry in append order governs.
 *
 * The registry is EMPTY until the operator records a real two-reviewer
 * concurrence — reviewer positions are written human positions, never
 * agent-drafted stand-ins (SIG-MEM-009; WV-03/ADR-163 waived only the HG-11
 * second-reviewer ROLE, never this rule). Until then every public-employee
 * name row withholds, whatever the jurisdiction says.
 */
// The committed table is bundled at build time: a static JSON import resolves
// against the SOURCE tree (web/src/lib → repo root), surviving the prerender
// chunking that relocates `import.meta.url` (same pattern as withdrawals.ts).
import decisionsTableJson from "../../../policy/src/policy/data/officer_naming_decisions.json";

const NAMING_DECISIONS_SCHEMA = "sig.officer-naming-decisions/1";

/** The five prongs of SIG-PUB-007, as stored on a record. */
export interface OfficerNamingProngs {
  official_conduct: boolean;
  name_on_face_of_record: boolean;
  record_public_in_jurisdiction: boolean;
  claim_fails_without_name: boolean;
  proportionate: boolean;
}

/** One reviewer's written position (SIG-PUB-008). */
export interface ReviewerConcurrence {
  reviewer_id: string;
  agrees: boolean;
  rationale: string;
  independent?: boolean;
}

/** One persisted officer-naming decision (the registry's entry shape). */
export interface OfficerNamingRecord {
  decision_id: string;
  subject_id: string;
  predicate_id: string;
  permitted: boolean;
  reason: string;
  prongs?: OfficerNamingProngs | null;
  reviewers?: ReviewerConcurrence[];
  is_home_address?: boolean;
  is_routine_audit_row?: boolean;
  recorded_at?: string;
  recorded_by?: string;
  supersedes?: string | null;
}

interface DecisionsTable {
  schema: string;
  decisions: OfficerNamingRecord[];
}

let cached: OfficerNamingRecord[] | null = null;

/** The committed registry's entries, in append order (schema-checked, fail-loud). */
export function namingDecisions(): OfficerNamingRecord[] {
  if (cached) return cached;
  const parsed = decisionsTableJson as DecisionsTable;
  if (parsed?.schema !== NAMING_DECISIONS_SCHEMA || !Array.isArray(parsed.decisions)) {
    throw new Error(
      `policy/src/policy/data/officer_naming_decisions.json: not a valid ${NAMING_DECISIONS_SCHEMA} table`,
    );
  }
  cached = [...parsed.decisions];
  return cached;
}

/** The latest record governing a name row's `(subject_id, predicate_id)` — append order IS supersede order. */
export function latestDecisionFor(
  decisions: readonly OfficerNamingRecord[],
  subjectId: string,
  predicateId: string,
): OfficerNamingRecord | undefined {
  let latest: OfficerNamingRecord | undefined;
  for (const record of decisions) {
    if (record.subject_id === subjectId && record.predicate_id === predicateId) {
      latest = record;
    }
  }
  return latest;
}

const PRONG_KEYS: readonly (keyof OfficerNamingProngs)[] = [
  "official_conduct",
  "name_on_face_of_record",
  "record_public_in_jurisdiction",
  "claim_fails_without_name",
  "proportionate",
];

/**
 * Replay the §43.4 test over a record's stored inputs — the mirror of
 * `policy.officer.evaluate_record`. The stored `permitted` flag is never
 * trusted alone: the carve-outs deny outright (SIG-PUB-009/010), every prong
 * must hold, and at least two DISTINCT independent reviewers must concur with
 * non-empty written rationales (SIG-PUB-008).
 */
export function replayNamingDecision(record: OfficerNamingRecord): boolean {
  if (record.is_home_address || record.is_routine_audit_row) return false;
  const prongs = record.prongs;
  if (!prongs || !PRONG_KEYS.every((k) => prongs[k] === true)) return false;
  const written = (record.reviewers ?? []).filter(
    (r) => (r.independent ?? true) && typeof r.rationale === "string" && r.rationale.trim() !== "",
  );
  const distinct = new Set(written.map((r) => r.reviewer_id));
  if (distinct.size < 2) return false;
  return written.every((r) => r.agrees);
}

/**
 * Whether a persisted record establishes the concurrence — fail-closed in both
 * directions: the stored verdict must be a permit AND the replay must agree, so
 * an inconsistent record (a stored permit whose inputs do not concur, or a
 * stored deny over concurring inputs) reads as withhold.
 */
export function namingRecordConcurs(record: OfficerNamingRecord): boolean {
  return record.permitted === true && replayNamingDecision(record);
}

/** The publication gate's verdict for one public-employee-name row. */
export interface NamingGateVerdict {
  permitted: boolean;
  reason: string;
  /** The governing record's id when one exists (provenance or recorded refusal). */
  decisionId?: string;
}

/**
 * The record leg of the publication gate (SIG-PUB-007/008). The jurisdiction
 * leg (`publicationPermitted`, SIG-PUB-017) is composed by the caller — BOTH
 * must permit. `decisions` defaults to the committed registry.
 */
export function namingRecordPermits(
  subjectId: string,
  predicateId: string,
  decisions: readonly OfficerNamingRecord[] = namingDecisions(),
): NamingGateVerdict {
  const record = latestDecisionFor(decisions, subjectId, predicateId);
  if (record === undefined) {
    return {
      permitted: false,
      reason:
        "no persisted officer-naming decision names this row " +
        "(SIG-PUB-007/008 — default deny)",
    };
  }
  if (!namingRecordConcurs(record)) {
    return {
      permitted: false,
      reason: `persisted decision ${record.decision_id} does not concur (${record.reason})`,
      decisionId: record.decision_id,
    };
  }
  return {
    permitted: true,
    reason: "persisted two-reviewer concurrence (SIG-PUB-008)",
    decisionId: record.decision_id,
  };
}
