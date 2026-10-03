// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * The reviewed research dossier — `sig.research-dossier/1` inside
 * `sig.dossier-portfolio/1` (P32.17, SIG-DOS-001/002).
 *
 * This is the web mirror of `exports/src/exports/research_dossier.py`: the SAME
 * wire names, the SAME six-state vocabulary, the SAME rubric constants — the
 * page renders the export bytes, it never re-scores. A research dossier is
 * deliberately distinct from the §39.2 inventory overview (`dossier.ts`): the
 * overview is shaped mechanically from published claims; a research dossier is
 * an evidence-complete twelve-question portfolio where every answer carries a
 * state, an evidence or search basis, a fact-to-capture citation, and (for an
 * honest unknown) a precise follow-up task.
 *
 * Static-first: the pages render these records at build time — nothing here
 * ships to the client (SIG-UI-036/037).
 */

// --- Wire schema ids ---------------------------------------------------------

export const RESEARCH_DOSSIER_SCHEMA = "sig.research-dossier/1" as const;
export const DOSSIER_PORTFOLIO_SCHEMA = "sig.dossier-portfolio/1" as const;
export const DOSSIER_PACKET_SCHEMA = "sig.dossier-packet/1" as const;

// --- The six-state answer vocabulary (mirrors the export contract) -----------

export const ANSWER_STATES = [
  "supported",
  "disputed",
  "derived",
  "unknown",
  "withheld",
  "not_applicable",
] as const;
export type AnswerState = (typeof ANSWER_STATES)[number];

export const ANSWER_STATE_LABELS: Record<AnswerState, string> = {
  supported: "Supported",
  disputed: "Disputed",
  derived: "Derived",
  unknown: "Unknown",
  withheld: "Withheld",
  not_applicable: "Not applicable",
};

// --- The fixed twelve-question rubric (mirrors the export contract) -----------

/** The pilot-completeness gate: total >= 28 of 36 AND q1/q5/q7/q8 >= 2. */
export const COMPLETE_TOTAL = 28;
export const COMPLETE_MAX = 36;
export const REQUIRED_MINIMUM: Record<string, number> = { q1: 2, q5: 2, q7: 2, q8: 2 };

/** The 0–3 per-question scale, for the methodology line on the page. */
export const RUBRIC_SCALE: Record<number, string> = {
  0: "unresearched — no evidence and no documented search",
  1: "documented unknown — SIG looked, named the sources, and found nothing yet",
  2: "traceable partial — evidenced but missing scope, dates, or capture binding",
  3: "scoped answer — evidenced on a named scope and/or valid-time basis",
};

// --- Contract records --------------------------------------------------------

export interface ResearchAssertion {
  predicate: string;
  value: string | number | null;
  raw_value?: string | null;
  unit?: string | null;
  value_kind?: string | null;
  source_field?: string | null;
  /** Scope qualifiers, predicate → label (e.g. count_scope → city_limits). */
  scope: Record<string, string>;
  qualifiers: { predicate: string; value: string }[];
  valid_from?: string | null;
  valid_to?: string | null;
  valid_edtf?: string | null;
  observed_at?: string | null;
  evidence_genre?: string | null;
  document_genre?: string | null;
  document_id?: string | null;
  field_state?: string | null;
  claim_digest?: string | null;
  capture_digest?: string | null;
  capture_method?: string | null;
  source_id?: string | null;
  source_url?: string | null;
  retrieved_date?: string | null;
  locator?: Record<string, unknown> | null;
  conflicting?: boolean | null;
}

export interface SearchBasis {
  question: string;
  sought?: string;
  sources_searched: string[];
  searched_at?: string;
  outcome: string;
  scope_note?: string;
  note?: string;
}

export interface FollowUp {
  question: string;
  action: string;
  next_evidence?: string;
  closing_condition?: string;
}

export interface LedgerRow {
  question: string;
  source_field?: string | null;
  predicate: string;
  fact: string;
  claim_digest?: string | null;
  capture_digest?: string | null;
  locator?: unknown;
  source_url?: string | null;
  retrieved_date?: string | null;
  state: "rendered" | "withheld" | "suppressed" | string;
}

export interface ChecklistItem {
  item: string;
  status: "pass" | "fail" | string;
  detail: string;
}

export interface ResearchCompleteness {
  total: number;
  max: number;
  required_minimum: Record<string, number>;
  per_question: Record<string, number>;
  mechanical_complete: boolean;
  pilot_complete: boolean;
  blocking: string[];
}

export interface DecisionWindowRow {
  predicate: string;
  value: string;
  valid_from?: string | null;
  valid_to?: string | null;
  document_id?: string | null;
}

export interface ResearchAnswer {
  question: string;
  slug: string;
  title: string;
  state: AnswerState;
  score: number;
  summary: string;
  assertions: ResearchAssertion[];
  search_basis?: SearchBasis | null;
  follow_ups: FollowUp[];
  declared?: Record<string, unknown> | null;
}

export interface ResearchDossier {
  schema: typeof RESEARCH_DOSSIER_SCHEMA | string;
  kind: "research_dossier" | string;
  dossier_id: string;
  subject: {
    slug?: string | null;
    label?: string | null;
    jurisdiction?: string | null;
    entity_id?: string | null;
    jurisdiction_slug?: string | null;
  };
  as_of: { world?: string; belief?: string };
  source_families: string[];
  review_status: string;
  review: Record<string, unknown>;
  answers: ResearchAnswer[];
  ledger: LedgerRow[];
  search_log: SearchBasis[];
  checklist: ChecklistItem[];
  completeness: ResearchCompleteness;
  decision_windows: { windows: DecisionWindowRow[]; next_decision_date?: string | null };
  what_we_dont_know: { question: string; title: string; detail: string }[];
  release: { valid: boolean; violations: { code: string; question?: string; detail: string }[] };
}

export interface ResearchDossierPortfolio {
  schema: typeof DOSSIER_PORTFOLIO_SCHEMA | string;
  dossiers: ResearchDossier[];
  summary: {
    dossier_count: number;
    pilot_complete: number;
    mechanical_complete: number;
    release_invalid: number;
  };
}

/** An empty portfolio — the honest absence form when no packet is authored. */
export function emptyPortfolio(): ResearchDossierPortfolio {
  return {
    schema: DOSSIER_PORTFOLIO_SCHEMA,
    dossiers: [],
    summary: { dossier_count: 0, pilot_complete: 0, mechanical_complete: 0, release_invalid: 0 },
  };
}

/** The canonical subject slug a dossier routes under (its id otherwise). */
export function researchDossierSlug(d: ResearchDossier): string {
  return d.subject.slug ?? d.dossier_id;
}

export function researchDossierPath(slug: string): string {
  return `/research-dossier/${slug}/`;
}

export function researchDossierJsonPath(slug: string): string {
  return `/research-dossier/${slug}.json`;
}

/** A plain-language line for an answer state on the page. */
export function stateLabel(state: AnswerState): string {
  return ANSWER_STATE_LABELS[state] ?? state;
}

/** The rubric gate line (e.g. "26/36 — gate 28/36 with q1, q5, q7, q8 ≥ 2"). */
export function rubricGateLine(d: ResearchDossier): string {
  const floors = Object.keys(d.completeness.required_minimum).join(", ");
  return `${d.completeness.total}/${d.completeness.max} — gate ${COMPLETE_TOTAL}/${COMPLETE_MAX} with ${floors} ≥ 2`;
}
