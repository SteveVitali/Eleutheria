// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * The curation web surface (P21.6, §34, ADR-068), as pure data + view model.
 *
 * This is the reviewer/contributor surface — NOT part of the public zero-JS shell.
 * The `/curate/**` pages are behind auth and under WCAG 2.2 AA, but not the public
 * zero-JS/performance budget; every form is a plain `<form method="post">` so it
 * works with **no client JavaScript** (progressive enhancement), posting to the
 * authenticated curation API (`api/src/api/curation.py`).
 *
 * The view model mirrors the engine shapes it wires to — the `ReviewItem` of
 * `resolution/review_queue.py`, the contradiction/task records of the read store,
 * and the contributor tiers of `tasks/contributor.py` — so wiring these pages to the
 * live curation service is a data-source swap, not a component change. Since P21.2
 * shipped compute-on-read (no new persistence repos), the fixtures below stand in for
 * what the authenticated API serves at runtime.
 *
 * Two invariants are encoded here and asserted by the unit tests + e2e/axe:
 *   - a machine suggestion is a LABELLED suggestion with its confidence class +
 *     provenance, never a pre-selected/auto-applied decision (SIG-LLM-001/002);
 *   - a contradiction is shown with BOTH claims, their evidence, and their dates
 *     (defining standard §3.1), never silently resolved.
 */

/** The curation API base URL, baked at BUILD time (loopback, non-public default). */
export function curationApiBase(): string {
  return process.env.SIG_CURATION_API_URL ?? "http://127.0.0.1:8001";
}

/** The absolute action URL for a curation form (`/v1/curation/<path>`). */
export function curationAction(path: string): string {
  const base = curationApiBase().replace(/\/$/, "");
  return `${base}/v1/curation/${path.replace(/^\//, "")}`;
}

/** One line of the ER confidence explanation (mirrors ConfidenceFactor, SIG-IDENT-025). */
export interface ConfidenceFactor {
  name: string;
  weight: number;
  detail: string;
}

/** A side of an entity compare (the fields a reviewer weighs match/no-match on). */
export interface EntitySide {
  label: string;
  fields: Record<string, string>;
}

/** A labelled machine suggestion — surfaced, never auto-applied (SIG-LLM-001/002). */
export interface MachineSuggestion {
  suggested_decision: string;
  confidence_class: string;
  model_id: string;
  prompt_version: string;
}

/** A review-queue proposal awaiting human adjudication (§28.5, §14.6). */
export interface ReviewQueueItem {
  item_id: string;
  kind: "er_match" | "model_extraction";
  summary: string;
  tier_label: string;
  overall_weight: number | null;
  confidence: ConfidenceFactor[];
  left: EntitySide;
  right: EntitySide;
  /** Present only for model-assisted items; a labelled suggestion (never applied). */
  suggestion?: MachineSuggestion;
}

/** One claim in a contradiction — shown with its evidence + date (§3.1, §30). */
export interface ContradictionClaim {
  claim_id: string;
  value: string;
  evidence_ref: string;
  as_of: string;
  source: string;
}

/** A contradiction awaiting disposition — never deleted, always dispositioned (§30). */
export interface ContradictionForReview {
  contradiction_id: string;
  subject_label: string;
  predicate_label: string;
  kind: string;
  claims: ContradictionClaim[];
}

/** A task awaiting disposition (§33.4). */
export interface TaskForReview {
  task_id: string;
  kind: string;
  subject_label: string;
  rationale: string;
}

/** The ER decisions a reviewer can record — match / no-match / defer (with reason). */
export const ER_DECISIONS = [
  { value: "match", label: "Match — the two records are the same entity" },
  { value: "no-match", label: "No match — they are different entities" },
  { value: "defer", label: "Defer — record a reason and leave in the queue" },
] as const;

/** The task disposition vocabulary (mirror of tasks.vocabulary.Disposition, §33.4). */
export const TASK_DISPOSITIONS = [
  "resolved_evidence_found",
  "resolved_no_evidence_exists",
  "blocked_access_denied",
  "blocked_fee",
  "blocked_awaiting_response",
] as const;

/** The SIG-captured submission kinds (device observations route to OSM, SIG-CONTRIB-004). */
export const SUBMISSION_KINDS = [
  "operator_evidence",
  "signage",
  "contract",
  "agenda_item",
  "report",
] as const;

/**
 * Order the queue by impact (RISK-P21-11: reviewer fatigue): highest |weight| first,
 * then by id — the same ordering the API applies, so the surfaces agree.
 */
export function orderByImpact(items: ReviewQueueItem[]): ReviewQueueItem[] {
  return [...items].sort((a, b) => {
    const wa = a.overall_weight === null ? 0 : Math.abs(a.overall_weight);
    const wb = b.overall_weight === null ? 0 : Math.abs(b.overall_weight);
    if (wb !== wa) return wb - wa;
    return a.item_id < b.item_id ? -1 : a.item_id > b.item_id ? 1 : 0;
  });
}

// --- Fixtures (stand in for what the authenticated API serves at runtime) -----

export const REVIEW_QUEUE: ReviewQueueItem[] = [
  {
    item_id: "er_match:agency:okcpd~agency:okc-pd",
    kind: "er_match",
    summary: "tier 5: agency:okcpd ~ agency:okc-pd (weight +12.40, p=0.998)",
    tier_label: "5",
    overall_weight: 12.4,
    confidence: [
      { name: "name", weight: 8.2, detail: "exact token overlap" },
      { name: "jurisdiction", weight: 4.2, detail: "same city" },
    ],
    left: {
      label: "Oklahoma City Police Department",
      fields: { entity_id: "agency:okcpd", jurisdiction: "Oklahoma City", source: "records" },
    },
    right: {
      label: "OKC PD",
      fields: { entity_id: "agency:okc-pd", jurisdiction: "OKC", source: "portal" },
    },
  },
  {
    item_id: "er_match:vendor:flock~vendor:flock-safety",
    kind: "er_match",
    summary: "tier 4: vendor:flock ~ vendor:flock-safety (weight +3.10, p=0.71)",
    tier_label: "4",
    overall_weight: 3.1,
    confidence: [{ name: "name", weight: 3.1, detail: "abbreviation match" }],
    left: {
      label: "Flock",
      fields: { entity_id: "vendor:flock", kind: "vendor" },
    },
    right: {
      label: "Flock Safety",
      fields: { entity_id: "vendor:flock-safety", kind: "vendor" },
    },
  },
  {
    item_id: "model_extraction:gpt-x:12:48",
    kind: "model_extraction",
    summary: "agency:okcpd operates_alpr 'Flock Safety' [R6/PROPOSED]",
    tier_label: "model",
    overall_weight: null,
    confidence: [{ name: "source_span", weight: 36, detail: "'operates Flock Safety cameras'" }],
    left: {
      label: "Proposed claim",
      fields: { subject: "agency:okcpd", predicate: "operates_alpr", value: "Flock Safety" },
    },
    right: {
      label: "Source span",
      fields: { span: "operates Flock Safety cameras", status: "R6/PROPOSED" },
    },
    suggestion: {
      suggested_decision: "match",
      confidence_class: "medium",
      model_id: "gpt-x",
      prompt_version: "p-2026-07",
    },
  },
];

export const CONTRADICTIONS: ContradictionForReview[] = [
  {
    contradiction_id: "contradiction:okcpd-count",
    subject_label: "Oklahoma City Police Department",
    predicate_label: "active device count",
    kind: "value_disagreement",
    claims: [
      {
        claim_id: "portal",
        value: "38",
        evidence_ref: "cap:portal:1",
        as_of: "2026-07-01",
        source: "Eyes on Flock portal aggregator",
      },
      {
        claim_id: "contract",
        value: "42",
        evidence_ref: "cap:contract:1",
        as_of: "2026-07-01",
        source: "Public records request (city procurement)",
      },
    ],
  },
];

export const TASKS: TaskForReview[] = [
  {
    task_id: "task:okcpd-count",
    kind: "reconcile_contradiction",
    subject_label: "Oklahoma City Police Department",
    rationale: "Portal (38) and contract (42) device counts disagree.",
  },
];
