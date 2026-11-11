// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * The evidence recommender as pure data + logic (§39.5a).
 *
 * For an upcoming decision point — a renewal, a council agenda item, a hearing — it
 * ranks the evidence artifacts most useful to a person preparing for it. This is the
 * component that makes journey J-3 executable (SIG-UI-027a / SIG-CHART-008); without
 * it J-3 cannot pass.
 *
 * The ranking uses ONLY the six model inputs §39.5a permits, all already present in
 * the pipeline:
 *   - claim directness `D` (D1/D2 rank above D3+; D6 is non-probative → excluded);
 *   - currency `C` relative to predicate volatility (§28.3; C1 freshest);
 *   - open contradictions touching the subject (both sides of a live dispute rank up);
 *   - open research tasks for the subject (named gaps rank up, as things to raise);
 *   - artifact type vs the decision type (a contract + its amendments rank first for a
 *     renewal);
 *   - `capture_status` (retrievable artifacts rank above paywalled / link-rotted ones).
 *
 * The neutrality guarantee (SIG-UI-027b) is the load-bearing property of this file and
 * is enforced STRUCTURALLY, not by convention: the input type carries none of the
 * forbidden signals, `assertNeutralInputs` rejects any artifact object that smuggles
 * one in, and the score is a pure function of the six allowed axes only. A recommender
 * that optimized for persuasiveness, sentiment, or predicted vote effect would make
 * SIG an advocacy instrument and forfeit the neutrality every other persona depends on.
 *
 * Output is exportable as a citation list with permalinks and as-of dates, suitable
 * for attaching to public comment (SIG-UI-027c). Contested artifacts carry the shared
 * `≠` marker at every appearance — the ranked list AND the export (SIG-UI-008).
 */

import { CONTESTED_MARKER } from "./epistemic";

// --- Decision points ---------------------------------------------------------

/** The kinds of upcoming decision point the recommender ranks evidence for (§39.5a).
 * P37.30 (K7 §5.7): extended additively with the watch kinds the per-item
 * decision points carry (`solicitation`, `legislative_action`,
 * `grant_period_end`; `contract_expiry` maps onto `renewal`). */
export const DECISION_TYPES = [
  "renewal",
  "council_agenda_item",
  "hearing",
  "solicitation",
  "legislative_action",
  "grant_period_end",
] as const;
export type DecisionType = (typeof DECISION_TYPES)[number];

/** An upcoming decision a person is preparing for (a renewal, agenda item, hearing). */
export interface DecisionPoint {
  decision_type: DecisionType;
  /** The subject the decision is about — the watch item's first subject key. */
  subject_id: string;
  /**
   * P37.30 (K7 §5.7): the full subject set the scoped ranking reads — the
   * decision's subject plus any sibling keys the item carries (the seed for
   * the one-hop contract/agency neighbourhood).
   */
  subject_ids?: string[];
  label: string;
  /** The date the decision falls (ISO), e.g. the `next_decision_date`. */
  date: string;
  /** The watch item's handle this decision point belongs to (per-item list). */
  handle?: string;
  /** The `sig.watch-item/1` kind, verbatim. */
  kind?: string;
  /** The item's `date_certainty`, verbatim (an `upper_bound` is never a deadline). */
  date_certainty?: string;
}

// --- The evidence artifact (only the §39.5a-admissible inputs) ---------------

/** Directness codes (§10.5); `D6` is non-probative and excluded from ranking. */
export const DIRECTNESS_CODES = ["D1", "D2", "D3", "D4", "D5", "D6"] as const;
export type DirectnessCode = (typeof DIRECTNESS_CODES)[number];

/** Currency codes (§28.3) relative to predicate volatility; `C1` is freshest. */
export const CURRENCY_CODES = ["C1", "C2", "C3", "C4"] as const;
export type CurrencyCode = (typeof CURRENCY_CODES)[number];

/** Capture retrievability (mirrors `evidence.disappearance` capture_status values). */
export const CAPTURE_STATUSES = ["retrievable", "paywalled", "link_rotted", "access_restricted"] as const;
export type CaptureStatus = (typeof CAPTURE_STATUSES)[number];

/**
 * The per-(artifact, subject) score input the export emits (P37.30, K7 §5.7):
 * the best §10.5 directness class and the best §28.3 currency class over the
 * artifact's claims about THIS subject, plus the subject-scoped dispute flags.
 * A pair that cannot be computed is emitted nowhere — a score names exactly
 * what it measures.
 */
export interface SubjectScore {
  /** The claim subject (entity id) the pair's axes are computed over. */
  subject_id: string;
  /** The subject's canonical `sig.connector.subject` key — what a watch item's `subjects` carry. */
  subject_key?: string;
  /** The best §10.5 directness class over the pair's probative claims (D6 excluded). */
  directness: DirectnessCode;
  /** The best §28.3 currency class over the pair's claims at the export's `as_of`. */
  currency: CurrencyCode;
  /** An open contradiction touches THIS subject (§39.5a — subject-scoped). */
  touches_open_contradiction?: boolean;
  /** An open research task names THIS subject. */
  answers_open_task?: boolean;
}

/**
 * An evidence artifact, carrying ONLY the inputs §39.5a admits. The shape is
 * deliberately closed to the six ranking axes plus the citation metadata; it has no
 * field for persuasiveness, sentiment, or predicted vote effect — the neutrality
 * guarantee (SIG-UI-027b) begins in the type itself.
 */
export interface EvidenceArtifact {
  artifact_id: string;
  /**
   * The artifact's subject — the `subject_scores` list is the authoritative
   * per-(artifact, subject) shape; the flat field names THE single scored
   * subject, and stays empty on fixtures rows that carry it directly or on
   * export rows with zero/multiple scored subjects.
   */
  subject_id: string;
  /** Plain-language title for the citation list. */
  title: string;
  /** The source (for the citation list). */
  source: string;
  /** Artifact type, e.g. "contract" | "amendment" | "invoice" | "meeting_minutes" | "policy". */
  artifact_type: string;
  /** Claim directness `D` for the predicates at issue (§10.5). */
  directness: DirectnessCode;
  /** Currency `C` vs predicate volatility (§28.3). */
  currency: CurrencyCode;
  /** Whether the artifact touches an OPEN contradiction on the subject (§29.1). */
  touches_open_contradiction: boolean;
  /** Whether the artifact answers an OPEN research task on the subject (§33.2). */
  answers_open_task: boolean;
  /** Retrievability of the capture (§17.6). */
  capture_status: CaptureStatus;
  /** The belief-pinned permalink for the citation list (SIG-UI-027c/035). */
  permalink: string;
  /** The artifact's as-of date for the citation list (SIG-UI-027c). */
  as_of: string;
  /**
   * P34.20 (K8 NEW-6): the registry display name of `source`, emitted by the
   * export (`source_registry.name`). Absent falls back to the source id —
   * never a fabricated name.
   */
  source_name?: string;
  /**
   * P34.20 (K8 NEW-6 / SIG-EVUI-D04): the honest capture class
   * (`"actual" | "synthetic" | "legacy"`, evidence_capture). A `synthetic`
   * artifact lists as a run record — never presented as a stored capture.
   * Absent means the artifact carries no capture row (honest "unclassified").
   */
  capture_classification?: "actual" | "synthetic" | "legacy";
  /**
   * P34.20 (K8 NEW-9, S-6): the source's own link — the artifact's recorded
   * URL, emitted ONLY where the export's effective-rights gate allows
   * redistribution. The page labels it as a recorded claim; it is never a
   * stored capture.
   */
  upstream_url?: string;
  /**
   * P36.51 (R11-K13-TX-08b / K8 §4.2): the disclosure lane the export decided
   * for the artifact's source (`raw-ok` | `derived-only` | `link-only` |
   * `restricted` | `unknown`). Absent on pre-P36.51 rows and fixtures.
   */
  lane?: string;
  /** The lane decision's basis (the export's `lane_basis`). */
  lane_basis?: string;
  /** The Part VIII class the lane decision recorded (sealed classes withhold). */
  part_viii_class?: string | null;
  /**
   * P36.51: the S-6 publication form of the upstream URL — the same
   * `status`/`url`/`host`/`path_sha256` block `sig.statement/1` rows carry.
   */
  upstream?: {
    status?: string;
    url?: string | null;
    host?: string | null;
    path_sha256?: string | null;
  } | null;
  /**
   * P36.51: the artifact's recorded capture history — one metadata row per
   * `evidence_capture` (bytes never travel, §17.5). A synthetic row is a run
   * record, never a stored document.
   */
  captures?: ArtifactCaptureRow[];
  /**
   * P36.60 (EV-02): the artifact's place binding — the K4 slug path of the
   * jurisdiction the artifact documents (`usa/ok/oklahoma-city-4064000`).
   * Absent means the export carries no place for the artifact (today: every
   * row) — the place facet's `unplaced` bucket is the honest answer.
   */
  place_key?: string | null;
  /** The publisher display name where the registry records one. */
  publisher?: string | null;
  /**
   * P37.30 (K7 §5.7): the per-(artifact, subject) score inputs — the
   * authoritative scoped shape. Absent on fixture rows (which carry the flat
   * `subject_id`/`directness`/`currency` directly) and on pre-repair exports.
   */
  subject_scores?: SubjectScore[];
  /** P37.30: the count of (artifact, subject) pairs whose score could not be
   * computed — recorded honestly, never smoothed into a zeroed score. */
  subject_scores_uncomputable?: number;
  /** The spine's own `primary_or_secondary` value under its true name (P37.30). */
  primary_or_secondary?: string;
  /** The artifact's EDTF publication date under its true name (P37.30). */
  published_at_edtf?: string;
  /** The §17.6 disappearance event timestamp, when one was observed (P37.30). */
  disappeared_observed_at?: string | null;
}

/**
 * One `evidence_capture` row as `evidence.json` emits it (P36.51) — metadata
 * only; `fields` appears only in the committed fixture corpus so the §4.4
 * field-by-field diff can run over real capture data (SIG-EVUI-005).
 */
export interface ArtifactCaptureRow {
  capture_id: string;
  retrieved_at?: string;
  content_digest?: string;
  digest_blake3?: string | null;
  byte_size?: number | null;
  media_type?: string;
  http_status?: number | null;
  capture_method?: string;
  storage_tier?: string;
  capture_classification?: string;
  redaction_applied?: boolean;
  parent_capture_id?: string | null;
  /** The J3 §5.3 label state the export minted for this capture. */
  view_original?: {
    kind?: string;
    label?: string;
    href?: string | null;
    note?: string | null;
  };
  /** Fixture-only: the extracted fields the §4.4 diff compares. */
  fields?: Record<string, unknown>;
}

// --- SIG-UI-027b: the neutrality guard (structural) --------------------------

/**
 * Signals the recommender MUST NOT rank by (SIG-UI-027b). Kept as an explicit
 * denylist so a future edit that adds one of these to an artifact fails the gate
 * loudly rather than silently turning SIG into an advocacy instrument.
 */
export const FORBIDDEN_RANKING_INPUTS = [
  "persuasiveness",
  "persuasion",
  "sentiment",
  "tone",
  "vote_effect",
  "predicted_vote",
  "predicted_vote_effect",
  "emotional_impact",
  "framing",
] as const;

/**
 * Reject any artifact object that carries a forbidden ranking signal (SIG-UI-027b).
 * The type already excludes them; this defends against an untyped/JSON artifact
 * smuggling one in at runtime. Throws with the offending key.
 */
export function assertNeutralInputs(artifact: Record<string, unknown>): void {
  for (const key of Object.keys(artifact)) {
    if ((FORBIDDEN_RANKING_INPUTS as readonly string[]).includes(key)) {
      throw new Error(
        `SIG-UI-027b: the evidence recommender MUST NOT rank by "${key}" — it ranks by ` +
          "evidentiary directness, recency, and dispute status only.",
      );
    }
  }
}

// --- The ranking (only the six admissible axes) ------------------------------

/** Directness contribution: D1/D2 rank above D3+ (SIG-UI-027a). D6 is excluded upstream. */
const DIRECTNESS_SCORE: Record<Exclude<DirectnessCode, "D6">, number> = {
  D1: 100,
  D2: 80,
  D3: 40,
  D4: 20,
  D5: 10,
};

/** Currency contribution: a fresher artifact ranks up (§28.3). */
const CURRENCY_SCORE: Record<CurrencyCode, number> = { C1: 40, C2: 25, C3: 10, C4: 0 };

/** Capture-status contribution: retrievable ranks above paywalled / link-rotted. */
const CAPTURE_SCORE: Record<CaptureStatus, number> = {
  retrievable: 20,
  access_restricted: 5,
  paywalled: 0,
  link_rotted: 0,
};

/** An open contradiction touching the subject ranks the artifact up (both sides). */
const CONTRADICTION_BONUS = 30;
/** An open research task the artifact answers ranks it up (a named gap to raise). */
const OPEN_TASK_BONUS = 15;

/**
 * Artifact-type relevance to the decision type (SIG-UI-027a): "a contract and its
 * amendments rank first for a renewal". Unknown (type, decision) pairs contribute 0
 * — never negative, so an unmodelled artifact type is merely un-boosted, not buried.
 */
const ARTIFACT_TYPE_RELEVANCE: Record<DecisionType, Record<string, number>> = {
  renewal: {
    contract: 30,
    amendment: 30,
    invoice: 15,
    budget_line: 12,
    cooperative_sku: 12,
    meeting_minutes: 10,
    portal_snapshot: 10,
    policy: 5,
  },
  council_agenda_item: {
    meeting_minutes: 30,
    agenda: 30,
    policy: 20,
    contract: 15,
    portal_snapshot: 10,
  },
  hearing: {
    policy: 30,
    accountability_event: 30,
    contract: 15,
    meeting_minutes: 15,
    portal_snapshot: 10,
  },
  // P37.30 (K7 §5.7): the watch kinds beyond §39.5a's three — the same
  // never-negative convention (an unmodelled artifact type is un-boosted,
  // never buried).
  solicitation: {
    solicitation: 30,
    portal_snapshot: 25,
    contract: 15,
    amendment: 10,
    policy: 10,
    meeting_minutes: 10,
  },
  legislative_action: {
    policy: 30,
    accountability_event: 20,
    meeting_minutes: 20,
    agenda: 15,
    portal_snapshot: 10,
    contract: 10,
  },
  grant_period_end: {
    contract: 20,
    policy: 20,
    portal_snapshot: 15,
    invoice: 15,
    budget_line: 15,
    meeting_minutes: 10,
  },
};

/** Whether an artifact is admissible to the recommendation at all (D6 is not, §10.5). */
export function isAdmissible(artifact: EvidenceArtifact): boolean {
  return artifact.directness !== "D6";
}

// --- P37.30 (K7 §5.7): subject scoping + the finite-score guard ----------- //

/** Ordinal rank for the directness/currency classes (lower is stronger). */
const DIRECTNESS_ORD: Record<DirectnessCode, number> = { D1: 1, D2: 2, D3: 3, D4: 4, D5: 5, D6: 6 };
const CURRENCY_ORD: Record<CurrencyCode, number> = { C1: 1, C2: 2, C3: 3, C4: 4 };

/** The subject a score row is scoped to — its canonical key, else the id. */
function scoreSubject(s: SubjectScore): string {
  return s.subject_key ?? s.subject_id;
}

/**
 * The subject scope a decision point ranks against (K7 §5.7): the decision's
 * own subjects PLUS the one-hop contract/agency neighbourhood the export's
 * `subject_neighbours` map records (a bound claim's subject and its object
 * entity are mutual neighbours — a document bearing on one bears on the
 * decision's subject one hop out).
 */
export function subjectScope(
  decision: DecisionPoint,
  neighbours: Record<string, readonly string[]> = {},
): Set<string> {
  const scope = new Set<string>([decision.subject_id, ...(decision.subject_ids ?? [])]);
  for (const s of [...scope]) {
    for (const n of neighbours[s] ?? []) scope.add(n);
  }
  return scope;
}

/**
 * The score pairs through which an artifact bears on the decision's subject
 * scope (K7 §5.7 — "rank only artifacts that bear on the decision's
 * subject"). An artifact with `subject_scores` bears through the pairs
 * naming a scoped subject (a D6 pair is never admissible — the export never
 * emits one, and a fixture row smuggling one is dropped here); a flat row
 * (fixtures / pre-repair exports) bears through its `subject_id` only.
 */
export function matchingScores(
  artifact: EvidenceArtifact,
  scope: ReadonlySet<string>,
): SubjectScore[] {
  if (artifact.subject_scores) {
    return artifact.subject_scores.filter(
      (s) =>
        s.directness !== "D6" &&
        (scope.has(s.subject_id) || (s.subject_key !== undefined && scope.has(s.subject_key))),
    );
  }
  if (scope.has(artifact.subject_id) && artifact.directness !== "D6") {
    return [
      {
        subject_id: artifact.subject_id,
        directness: artifact.directness,
        currency: artifact.currency,
        touches_open_contradiction: artifact.touches_open_contradiction,
        answers_open_task: artifact.answers_open_task,
      },
    ];
  }
  return [];
}

/**
 * The build-time NaN guard (K7 §5.7, F-485): a non-finite score fails the
 * build LOUDLY — the pre-repair export returned 255 of 255 `NaN` rows and
 * nothing caught it; an uncomputable score fails typed, never silently zero.
 */
export function assertFiniteScore(score: number, artifactId: string): void {
  if (!Number.isFinite(score)) {
    throw new Error(
      `SIG-UI-027a: non-finite evidence score for artifact ${artifactId} — ` +
        "the emitted score must be finite; an uncomputable score fails typed, " +
        "never silently zero (K7 §5.7 / F-485).",
    );
  }
}

/** The relevance bonus for an artifact type given the decision type (0 if unmodelled). */
export function artifactTypeRelevance(artifactType: string, decision: DecisionType): number {
  return ARTIFACT_TYPE_RELEVANCE[decision][artifactType] ?? 0;
}

/** The score contribution of each admissible axis — so the UI can show WHY it ranked. */
export interface ScoreBreakdown {
  directness: number;
  currency: number;
  artifact_type: number;
  open_contradiction: number;
  open_task: number;
  capture_status: number;
}

/**
 * The per-axis score breakdown for an artifact against a decision (SIG-UI-027a). A
 * pure function of the six admissible axes ONLY; there is no path by which any other
 * signal can enter the total (SIG-UI-027b). P37.30: the D/C/dispute axes come
 * from the matched (artifact, subject) pair when one is supplied — a score
 * names exactly what it measures.
 */
export function scoreBreakdown(
  artifact: EvidenceArtifact,
  decision: DecisionPoint,
  pair?: SubjectScore,
): ScoreBreakdown {
  const directness = pair?.directness ?? artifact.directness;
  if (directness === "D6") {
    throw new Error("SIG-UI-027a: a D6 (non-probative) artifact is not admissible to the ranking (§10.5).");
  }
  return {
    directness: DIRECTNESS_SCORE[directness as Exclude<DirectnessCode, "D6">],
    currency: CURRENCY_SCORE[(pair?.currency ?? artifact.currency) as CurrencyCode],
    artifact_type: artifactTypeRelevance(artifact.artifact_type, decision.decision_type),
    open_contradiction: (pair?.touches_open_contradiction ?? artifact.touches_open_contradiction)
      ? CONTRADICTION_BONUS
      : 0,
    open_task: (pair?.answers_open_task ?? artifact.answers_open_task) ? OPEN_TASK_BONUS : 0,
    capture_status: CAPTURE_SCORE[artifact.capture_status],
  };
}

/** The total score = sum of the admissible-axis contributions (SIG-UI-027a/b). */
export function scoreArtifact(
  artifact: EvidenceArtifact,
  decision: DecisionPoint,
  pair?: SubjectScore,
): number {
  const b = scoreBreakdown(artifact, decision, pair);
  return b.directness + b.currency + b.artifact_type + b.open_contradiction + b.open_task + b.capture_status;
}

/** A ranked recommendation entry: the artifact, its score, and the per-axis breakdown. */
export interface RankedArtifact {
  artifact: EvidenceArtifact;
  score: number;
  breakdown: ScoreBreakdown;
  /** Whether the artifact is contested (touches an open contradiction) — SIG-UI-008. */
  contested: boolean;
  /**
   * P37.30 (K7 §5.7): the subjects through which the artifact bears on the
   * decision — every scoped (artifact, subject) pair that admitted it. The
   * score names exactly what it measures: `matched_subject` is the pair the
   * score was computed over.
   */
  scored_subjects: string[];
  matched_subject: string;
}

/**
 * Rank the admissible evidence artifacts for a decision point (SIG-UI-027a).
 * P37.30 (K7 §5.7, F-485): the list is SUBJECT-SCOPED — only artifacts
 * bearing on the decision's subject (or its one-hop neighbourhood, via the
 * export's `subject_neighbours` map) rank, each scored on the best matching
 * (artifact, subject) pair — never the national unscoped list the pre-repair
 * code produced. D6 is excluded (§10.5); ties break by `artifact_id` so the
 * ranking is deterministic. Every emitted score passes `assertFiniteScore` —
 * a non-finite score fails the build, never silently zero.
 */
export function recommendEvidence(
  artifacts: readonly EvidenceArtifact[],
  decision: DecisionPoint,
  neighbours: Record<string, readonly string[]> = {},
): RankedArtifact[] {
  const scope = subjectScope(decision, neighbours);
  const ranked: RankedArtifact[] = [];
  for (const artifact of artifacts) {
    assertNeutralInputs(artifact as unknown as Record<string, unknown>);
    const matches = matchingScores(artifact, scope);
    if (!isAdmissible(artifact) && !artifact.subject_scores) continue;
    if (matches.length === 0) continue;
    // The score is computed over the strongest matching pair — D then C, ties
    // lexical — and the entry names every subject the artifact bears through.
    const best = [...matches].sort(
      (x, y) =>
        DIRECTNESS_ORD[x.directness] - DIRECTNESS_ORD[y.directness] ||
        CURRENCY_ORD[x.currency] - CURRENCY_ORD[y.currency] ||
        scoreSubject(x).localeCompare(scoreSubject(y)),
    )[0]!;
    const score = scoreArtifact(artifact, decision, best);
    assertFiniteScore(score, artifact.artifact_id);
    ranked.push({
      artifact,
      score,
      breakdown: scoreBreakdown(artifact, decision, best),
      contested: best.touches_open_contradiction ?? artifact.touches_open_contradiction,
      scored_subjects: [...new Set(matches.map(scoreSubject))].sort(),
      matched_subject: scoreSubject(best),
    });
  }
  return ranked.sort(
    (a, b) => b.score - a.score || a.artifact.artifact_id.localeCompare(b.artifact.artifact_id),
  );
}

// --- SIG-UI-027c: the exportable citation list -------------------------------

/** One entry of the exportable citation list — permalink + as-of date (SIG-UI-027c). */
export interface CitationEntry {
  artifact_id: string;
  title: string;
  source: string;
  permalink: string;
  as_of: string;
  /** True when the artifact is contested — carries the marker in the export (SIG-UI-008). */
  contested: boolean;
}

/** The citation list for a ranked recommendation, in rank order (SIG-UI-027c). */
export function citationList(ranked: readonly RankedArtifact[]): CitationEntry[] {
  return ranked.map((r) => ({
    artifact_id: r.artifact.artifact_id,
    title: r.artifact.title,
    source: r.artifact.source,
    permalink: r.artifact.permalink,
    as_of: r.artifact.as_of,
    contested: r.contested,
  }));
}

/**
 * The plain-text citation list, suitable for pasting into public comment
 * (SIG-UI-027c). Each line carries the title, source, as-of date, and permalink;
 * a contested artifact carries the persistent `≠` marker (SIG-UI-008).
 */
export function citationListText(ranked: readonly RankedArtifact[], decision: DecisionPoint): string {
  const header =
    `Evidence for: ${decision.label} (${decision.decision_type.replace(/_/g, " ")}, ${decision.date})\n` +
    `Ranked by evidentiary directness, recency, and dispute status only.\n`;
  const lines = citationList(ranked).map((c, i) => {
    const mark = c.contested ? ` ${CONTESTED_MARKER.glyph} (${CONTESTED_MARKER.label})` : "";
    return `${i + 1}. "${c.title}"${mark} — ${c.source}. As of ${c.as_of}. ${c.permalink}`;
  });
  return `${header}\n${lines.join("\n")}\n`;
}
