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

/** The kinds of upcoming decision point the recommender ranks evidence for (§39.5a). */
export const DECISION_TYPES = ["renewal", "council_agenda_item", "hearing"] as const;
export type DecisionType = (typeof DECISION_TYPES)[number];

/** An upcoming decision a person is preparing for (a renewal, agenda item, hearing). */
export interface DecisionPoint {
  decision_type: DecisionType;
  subject_id: string;
  label: string;
  /** The date the decision falls (ISO), e.g. the `next_decision_date`. */
  date: string;
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
 * An evidence artifact, carrying ONLY the inputs §39.5a admits. The shape is
 * deliberately closed to the six ranking axes plus the citation metadata; it has no
 * field for persuasiveness, sentiment, or predicted vote effect — the neutrality
 * guarantee (SIG-UI-027b) begins in the type itself.
 */
export interface EvidenceArtifact {
  artifact_id: string;
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
};

/** Whether an artifact is admissible to the recommendation at all (D6 is not, §10.5). */
export function isAdmissible(artifact: EvidenceArtifact): boolean {
  return artifact.directness !== "D6";
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
 * signal can enter the total (SIG-UI-027b).
 */
export function scoreBreakdown(artifact: EvidenceArtifact, decision: DecisionPoint): ScoreBreakdown {
  if (artifact.directness === "D6") {
    throw new Error("SIG-UI-027a: a D6 (non-probative) artifact is not admissible to the ranking (§10.5).");
  }
  return {
    directness: DIRECTNESS_SCORE[artifact.directness],
    currency: CURRENCY_SCORE[artifact.currency],
    artifact_type: artifactTypeRelevance(artifact.artifact_type, decision.decision_type),
    open_contradiction: artifact.touches_open_contradiction ? CONTRADICTION_BONUS : 0,
    open_task: artifact.answers_open_task ? OPEN_TASK_BONUS : 0,
    capture_status: CAPTURE_SCORE[artifact.capture_status],
  };
}

/** The total score = sum of the admissible-axis contributions (SIG-UI-027a/b). */
export function scoreArtifact(artifact: EvidenceArtifact, decision: DecisionPoint): number {
  const b = scoreBreakdown(artifact, decision);
  return b.directness + b.currency + b.artifact_type + b.open_contradiction + b.open_task + b.capture_status;
}

/** A ranked recommendation entry: the artifact, its score, and the per-axis breakdown. */
export interface RankedArtifact {
  artifact: EvidenceArtifact;
  score: number;
  breakdown: ScoreBreakdown;
  /** Whether the artifact is contested (touches an open contradiction) — SIG-UI-008. */
  contested: boolean;
}

/**
 * Rank the admissible evidence artifacts for a decision point (SIG-UI-027a). D6
 * artifacts are excluded (§10.5); the rest are sorted by score descending, ties
 * broken by `artifact_id` so the ranking is deterministic. Every artifact is passed
 * through `assertNeutralInputs` first, so a smuggled forbidden signal fails loudly
 * (SIG-UI-027b).
 */
export function recommendEvidence(
  artifacts: readonly EvidenceArtifact[],
  decision: DecisionPoint,
): RankedArtifact[] {
  return artifacts
    .filter((a) => {
      assertNeutralInputs(a as unknown as Record<string, unknown>);
      return isAdmissible(a);
    })
    .map((artifact) => ({
      artifact,
      score: scoreArtifact(artifact, decision),
      breakdown: scoreBreakdown(artifact, decision),
      contested: artifact.touches_open_contradiction,
    }))
    .sort((a, b) => b.score - a.score || a.artifact.artifact_id.localeCompare(b.artifact.artifact_id));
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
