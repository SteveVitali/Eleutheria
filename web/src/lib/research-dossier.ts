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

// --- P34.35: the disclosure vocabulary (mirrors exports.research_dossier) ----

/** How a rendered assertion's bytes were obtained (DR-C4-03, F-152). */
export type ResearchAcquisition =
  | "live_capture"
  | "committed_transcription"
  | "stand_in"
  | (string & {});

/** The three-way acquisition vocabulary a reader sees. */
export const ACQUISITION_LABELS: Record<string, string> = {
  live_capture: "live capture",
  committed_transcription: "committed transcription",
  stand_in: "stand-in",
};

/**
 * The review label DERIVED from the recorded `review_status` (F-153,
 * DR-C4-04) — never hard-coded. Only `completed` may say "reviewed": a
 * `not_run` dossier reads as what it is — no human check has run (ADR-152;
 * the independent check stays owed under D-R10-HUMAN-1 / T-EVAL-IND).
 */
export const REVIEW_STATUS_LABELS: Record<string, string> = {
  completed: "independently reviewed",
  pending: "independent review pending",
  not_run: "independent review not yet run",
};

/** The dossier artifact's §42.4 licence when the record names none. */
export const DOSSIER_ARTIFACT_LICENCE = "CC-BY-4.0";

/** The canonical public origin (P27.6 / ADR-093; mirrors astro `site`). */
export const PUBLIC_ORIGIN = "https://surveillancegraph.org";

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
  /**
   * P34.22b (B4 G1 R4): the capture posture — `stand-in` (hand-authored
   * committed bytes, never retrieved) or `fixture_replay` (a connector replay
   * whose retrieval stamp is the fixture's authoring commit). A stand-in
   * carries NO retrieved_date; its authoring commit rides `committed_at`.
   */
  capture_kind?: string | null;
  /**
   * P34.35 (DR-C4-03): how the bytes were obtained — `live_capture`,
   * `committed_transcription` or `stand_in`, derived from the evidence
   * record at composition (never inferred from a URL).
   */
  acquisition?: ResearchAcquisition | null;
  access_mode?: string | null;
  extraction_method?: string | null;
  /** The cited bytes' real authoring commit time (ISO), when declared. */
  committed_at?: string | null;
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
  /** P34.22b: the capture posture of the bound bytes (stand-in / fixture_replay). */
  capture_kind?: string | null;
  /** P34.35 (F-16): how this fact's bytes were obtained. */
  acquisition?: ResearchAcquisition | null;
  committed_at?: string | null;
  state: "rendered" | "withheld" | "suppressed" | string;
}

/**
 * P34.35 (F-16 / DR-C4-03): the dossier's evidence-acquisition posture —
 * which dossier facts rest on live captures, committed transcriptions, or
 * hand-authored stand-ins, as a direct read rather than a join the reader
 * must perform.
 */
export interface EvidencePosture {
  acquisition_counts: Record<string, number>;
  /** True when ANY rendered fact rests on non-live bytes — the page says so above the fold. */
  has_non_live: boolean;
  questions_with_non_live: string[];
  /** The fact strings of every ledger row resting on stand-in bytes. */
  stand_in_facts: string[];
}

/** P34.35 (C4 NEW-22, SIG-LIC-011): the licence block page + print carry. */
export interface DossierLicence {
  /** The dossier artifact's own licence (§42.4; e.g. CC-BY-4.0). */
  artifact?: string;
  /** The SPDX marks the underlying evidence records carry downstream. */
  record_spdx?: string[];
}

/** P34.22b: one declared fixture in a packet/dossier capture manifest. */
export interface CaptureFixture {
  path: string;
  /** The commit that authored the bytes — absent when unknowable at authoring time (the fixture cannot name its own future commit). */
  commit?: string | null;
  committed_at: string;
}

/** The packet/dossier capture block: what kind of evidence backs the records. */
export interface CaptureBlock {
  kind?: string;
  live_verification?: boolean;
  /** The evidence anchor — the newest fixture authoring commit. */
  anchor?: string;
  fixtures?: Record<string, CaptureFixture>;
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
  /** A labelled scenario frame (e.g. OKC announced-vs-operative) — never a capture date. */
  scenario_as_of?: { world?: string; belief?: string; basis?: string } | null;
  /** P34.22b: the capture provenance manifest — what backs the records and when the bytes were authored. */
  capture?: CaptureBlock;
  source_families: string[];
  review_status: string;
  /** P34.35 (F-153): the review wording derived from `review_status`. */
  review_label?: string;
  review: Record<string, unknown>;
  /** P34.35 (C4 NEW-22): the licence the page and print carry (SIG-LIC-011). */
  licence?: DossierLicence;
  /** P34.35 (C4 NEW-23): the stable citation URL the page and print carry. */
  permalink?: string;
  /** P34.35 (DR-C4-03 / F-16): the evidence-acquisition posture summary. */
  evidence_posture?: EvidencePosture;
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

// --------------------------------------------------------------------------- //
// P34.35 — disclosure helpers (mirror exports.research_dossier exactly)
// --------------------------------------------------------------------------- //

/**
 * The acquisition label one rendered assertion carries (DR-C4-03). The
 * export-emitted `acquisition` field wins; absent it (a pre-P34.35 bundle),
 * the same derivation is replayed from the capture fields — transcription
 * markers first, the declared stand-in postures next, a recorded retrieval
 * stamp means live, and the fail-closed remainder is a stand-in. The result
 * is the DISPLAY string ("live capture" / "committed transcription" /
 * "stand-in"), never inferred from a URL.
 */
export function acquisitionLabel(x: {
  acquisition?: string | null;
  capture_kind?: string | null;
  capture_method?: string | null;
  access_mode?: string | null;
  extraction_method?: string | null;
  retrieved_date?: string | null;
}): string {
  const acq = x.acquisition ?? derivedAcquisition(x);
  return ACQUISITION_LABELS[acq] ?? acq;
}

/** The wire enum, derived when the bundle predates the `acquisition` field. */
export function derivedAcquisition(x: {
  capture_kind?: string | null;
  capture_method?: string | null;
  access_mode?: string | null;
  extraction_method?: string | null;
  retrieved_date?: string | null;
}): string {
  const method = x.capture_method ?? "";
  const access = x.access_mode ?? "";
  const extraction = x.extraction_method ?? "";
  if (
    method.includes("transcription") ||
    extraction.includes("transcription") ||
    access === "committed_fixture"
  ) {
    return "committed_transcription";
  }
  const kind = x.capture_kind ?? "";
  if (kind === "stand-in" || kind === "fixture_replay") return "stand_in";
  if (x.retrieved_date) return "live_capture";
  return "stand_in"; // fail-closed — never overclaim a capture
}

/** The review wording derived from the recorded `review_status` (F-153). */
export function reviewLabel(status: string | null | undefined): string {
  const key = status ?? "not_run";
  return REVIEW_STATUS_LABELS[key] ?? `review status recorded as ${key}`;
}

/**
 * The dossier's evidence posture: the composed `evidence_posture` block when
 * the bundle carries it, otherwise derived from the rendered assertions —
 * `has` drives the above-the-fold non-live disclosure (DR-C4-03).
 */
export function evidencePosture(d: ResearchDossier): {
  has: boolean;
  counts: Record<string, number>;
  questions: string[];
} {
  if (d.evidence_posture) {
    return {
      has: d.evidence_posture.has_non_live,
      counts: d.evidence_posture.acquisition_counts,
      questions: d.evidence_posture.questions_with_non_live,
    };
  }
  const counts: Record<string, number> = {};
  const questions = new Set<string>();
  for (const a of d.answers) {
    for (const x of a.assertions) {
      const acq = derivedAcquisition(x);
      counts[acq] = (counts[acq] ?? 0) + 1;
      if (acq !== "live_capture") questions.add(a.question);
    }
  }
  return { has: questions.size > 0, counts, questions: [...questions].sort() };
}

/** The licence line page + print carry (SIG-LIC-011). */
export function dossierLicenceText(d: ResearchDossier): string {
  const artifact = d.licence?.artifact ?? DOSSIER_ARTIFACT_LICENCE;
  const records = (d.licence?.record_spdx ?? []).filter(Boolean);
  return records.length
    ? `${artifact} — evidence records carry ${records.join(", ")}`
    : artifact;
}

/** The dossier's stable citation URL (C4 NEW-23). */
export function dossierPermalink(d: ResearchDossier): string {
  return d.permalink ?? `${PUBLIC_ORIGIN}${researchDossierPath(researchDossierSlug(d))}`;
}

/**
 * P34.35 (DR-C4-15): the build-time date guard — every DISPLAYED date on the
 * dossier (as-of, retrieval, observation, commit and search stamps) must be ≤
 * the build clock. A planted future date throws — the astro build fails
 * rather than shipping a fabricated date. Stated document dates (valid_*),
 * the scenario frame and decision windows are real-world claims, exempt.
 */
const DISPLAYED_STAMP_KEYS = new Set([
  "retrieved_at",
  "retrieved_date",
  "observed_at",
  "searched_at",
  "committed_at",
  "fixture_committed_at",
  "generated_at",
  "completed_at",
]);

export function assertNoFutureDisplayDates(
  d: ResearchDossier,
  now: Date = new Date(),
): void {
  const check = (path: string, value: unknown) => {
    if (value === null || value === undefined || value === "") return;
    const dt = new Date(String(value));
    if (Number.isNaN(dt.getTime())) return;
    if (dt > now) {
      throw new Error(
        `${path} ${JSON.stringify(value)} is after the build time — ` +
          "a displayed date can never postdate the build clock",
      );
    }
  };
  const walk = (node: unknown, path: string): void => {
    if (Array.isArray(node)) {
      node.forEach((item, i) => walk(item, `${path}[${i}]`));
    } else if (node !== null && typeof node === "object") {
      for (const [key, value] of Object.entries(node as Record<string, unknown>)) {
        if (key === "valid_from" || key === "valid_to" || key === "valid_edtf") continue;
        if (DISPLAYED_STAMP_KEYS.has(key)) check(`${path}.${key}`, value);
        walk(value, `${path}.${key}`);
      }
    }
  };
  check("as_of.world", d.as_of?.world);
  check("as_of.belief", d.as_of?.belief);
  walk(d.review ?? {}, "review");
  walk(d.capture ?? {}, "capture");
  walk(d.answers ?? [], "answers");
  walk(d.ledger ?? [], "ledger");
  walk(d.search_log ?? [], "search_log");
}
