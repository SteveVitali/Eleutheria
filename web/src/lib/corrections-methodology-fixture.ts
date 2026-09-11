// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * Committed fixtures for the P15.5 surfaces — the research queue (§39.7), the public
 * corrections log (§39.8), data-freshness and coverage metrics (§32.4/32.5), and the
 * editorial-standards conformance gate (§41). The shell is static-first (SIG-UI-036):
 * these typed fixtures stand in for the live `tasks` / governance / metrics APIs, and
 * their field names mirror the engine so wiring to the live data is a source swap.
 *
 * Everything is keyed to the worked Oklahoma City case (and its Tulsa neighbour, to
 * exercise geographic filtering) that the rest of the shell already renders.
 */

import { RULESET_VERSION } from "./fixtures";
import type { JurisdictionClaim, ResearchTaskCard } from "./research-queue";
import { dispositionsFor } from "./research-queue";
import type { CorrectionEntry } from "./corrections";
import type { HostileReaderReview } from "./editorial";
import type { CoverageMetric, FreshnessRow } from "./metrics";
import type { ProvenanceSummary } from "./provenance";

// --- Research queue (§39.7, SIG-UI-031) --------------------------------------

/**
 * The research-queue task cards for the worked case. Each mirrors a §33.2 catalog
 * task type (the `task_type` slugs are the engine's) and states the four required
 * fields — closing condition, evidence sought, assignee class, effort estimate — plus
 * jurisdiction/scope for filtering. Dispositions are derived from the assignee class
 * (the same mapping the engine uses), so search tasks carry "searched, found nothing".
 */
export const RESEARCH_QUEUE: ResearchTaskCard[] = [
  {
    task_type: "missing_physical_devices",
    subject_id: "agency:okcpd",
    subject_label: "Oklahoma City PD — unmapped ALPR devices",
    closing_condition: "The mapped-device count reaches the active-device count (≥ 38 mapped).",
    evidence_sought: "Field observations locating and mapping at least seven more active devices.",
    assignee_class: "field_mapper",
    effort_estimate: "moderate",
    geographic_scope: "jurisdiction",
    jurisdiction: "Oklahoma City",
    dispositions: dispositionsFor("field_mapper"),
    priority: 0.8,
  },
  {
    task_type: "conflicting_retention",
    subject_id: "agency:okcpd",
    subject_label: "Oklahoma City PD — retention policy vs configuration",
    closing_condition: "The written policy retention and the configured retention agree, or the divergence is explained.",
    evidence_sought: "The written retention policy and a current configuration export, by records request.",
    assignee_class: "records_requester",
    effort_estimate: "moderate",
    geographic_scope: "jurisdiction",
    jurisdiction: "Oklahoma City",
    dispositions: dispositionsFor("records_requester"),
    priority: 0.7,
  },
  {
    task_type: "contract_expiring",
    subject_id: "contract:okcpd-alpr",
    subject_label: "Oklahoma City PD — ALPR contract renewal decision",
    closing_condition: "Renewal evidence is filed, or the decision date passes with a recorded outcome.",
    evidence_sought: "Council agenda item or executed renewal/non-renewal for the 2027-01-02 decision.",
    assignee_class: "local_group",
    effort_estimate: "moderate",
    geographic_scope: "jurisdiction",
    jurisdiction: "Oklahoma City",
    dispositions: dispositionsFor("local_group"),
    priority: 0.9,
  },
  {
    task_type: "coverage_hole",
    subject_id: "jurisdiction:tulsa",
    subject_label: "Tulsa — no surveillance evidence on file",
    closing_condition: "Any first evidence artifact lands for the jurisdiction, or a coverage record is written.",
    evidence_sought: "Any procurement, portal, or field evidence for Tulsa; otherwise a searched-found-nothing record.",
    assignee_class: "local_group",
    effort_estimate: "substantial",
    geographic_scope: "jurisdiction",
    jurisdiction: "Tulsa",
    dispositions: dispositionsFor("local_group"),
    priority: 0.5,
  },
  {
    task_type: "link_rot",
    subject_id: "artifact:portal-snapshot-2026-07",
    subject_label: "Portal snapshot — source URL now 404s",
    closing_condition: "The URL resolves again, or an archived replacement is linked.",
    evidence_sought: "A live or archived copy of the transparency-portal snapshot.",
    assignee_class: "developer",
    effort_estimate: "quick",
    geographic_scope: "global",
    jurisdiction: "(global)",
    dispositions: dispositionsFor("developer"),
    priority: 0.4,
  },
];

/**
 * A live jurisdiction claim (§33.5): the Oklahoma City local group has claimed the
 * jurisdiction, which grants priority — NOT exclusivity — and expires without renewal.
 */
export const JURISDICTION_CLAIMS: JurisdictionClaim[] = [
  {
    jurisdiction: "Oklahoma City",
    claimed_by: "OKC Privacy Coalition (local group)",
    claimed_at: "2026-07-01",
    expires_at: "2026-10-01",
  },
];

/** The as-of date the queue is rendered at (the claim above is live on this date). */
export const QUEUE_AS_OF = "2026-08-20";

// --- Public corrections log (§39.8, SIG-UI-032; §45.3) -----------------------

/**
 * The corrections log. Each entry records what changed, when, why, and who reported
 * it (SIG-UI-032), and preserves the prior value at its belief-time so a pre-correction
 * citation stays reproducible (SIG-GOV-005). The set spans several outcomes, including
 * a REFUSAL with reasoning (SIG-GOV-004) and a SUPPRESSION (SIG-GOV-007).
 */
export const CORRECTIONS: CorrectionEntry[] = [
  {
    id: "corr-2026-08-18-okcpd-count",
    subject_id: "agency:okcpd",
    subject_label: "Oklahoma City PD — active device count",
    what_changed: "Active device count changed from 40 to 42 after a records-request contract was obtained.",
    corrected_at: "2026-08-18",
    reason: "A W3 executed contract superseded the earlier W2 portal-only estimate.",
    reported_by: "records_requester (SIG contributor)",
    category: "factual_error",
    outcome: "corrected",
    previous_value: "40 devices",
    corrected_value: "42 devices",
    previous_belief_date: "2026-08-10",
    subject_path: "/dossier/oklahoma-city/",
  },
  {
    id: "corr-2026-08-12-response-annotation",
    subject_id: "agency:okcpd",
    subject_label: "Oklahoma City PD — retention characterization",
    what_changed: "Attached the department's response disputing the retention characterization.",
    corrected_at: "2026-08-12",
    reason: "The subject disputes an accurate claim and is entitled to attach a response (SIG-GOV-010).",
    reported_by: "Oklahoma City PD (subject)",
    category: "factual_error",
    outcome: "annotated",
    previous_value: "(no attached response)",
    corrected_value: "response published alongside the claim",
    previous_belief_date: "2026-08-01",
    subject_path: "/dossier/oklahoma-city/",
  },
  {
    id: "corr-2026-08-05-privacy-suppression",
    subject_id: "device:okc-014",
    subject_label: "A mapped device near a sensitive residential site",
    what_changed: "Suppressed a device's precise coordinates from public view; retained internally under seal.",
    corrected_at: "2026-08-05",
    reason: "A valid privacy-harm submission; suppression is distinct from deletion (SIG-GOV-007).",
    reported_by: "anonymous",
    category: "privacy_harm",
    outcome: "suppressed",
    previous_value: "block-level coordinates published",
    corrected_value: "coordinates suppressed (jurisdiction-centroid only)",
    previous_belief_date: "2026-07-20",
    subject_path: "/reference-map/",
  },
  {
    id: "corr-2026-07-28-refused",
    subject_id: "agency:okcpd",
    subject_label: "Oklahoma City PD — accountability event",
    what_changed: "No change: a request to remove a sourced, accurate accountability event was declined.",
    corrected_at: "2026-07-28",
    reason: "The claim is accurate and well-sourced; refusal with published reasoning (SIG-GOV-004).",
    reported_by: "anonymous",
    category: "factual_error",
    outcome: "refused",
    previous_value: "accountability event published",
    corrected_value: "accountability event retained (refusal published)",
    previous_belief_date: "2026-07-20",
    subject_path: "/dossier/oklahoma-city/",
  },
];

// --- Editorial: the hostile-reader review (§41, SIG-UI-042) ------------------

/**
 * The recorded hostile-reader review for the current dossier template version. Two
 * independent reviewers read the rendered Oklahoma City dossier as the department's
 * counsel and logged every sentence they would challenge; every finding is
 * dispositioned, so the template version is releasable (SIG-UI-042). The template
 * version is the resolver ruleset version the dossier is pinned to.
 */
export const HOSTILE_READER_REVIEW: HostileReaderReview = {
  template_version: RULESET_VERSION,
  reviewed_dossier: "/dossier/oklahoma-city/",
  reviewers: ["Reviewer A (counsel stance)", "Reviewer B (counsel stance)"],
  review_date: "2026-08-19",
  findings: [
    {
      id: "hr-1",
      challenge: "\"admitted to only 38 cameras\" characterizes the portal report as a concession.",
      disposition: "accepted_revised",
      resolution: "Rewritten to \"the portal reported 38 cameras on 2026-07-01\" (register rule 1).",
    },
    {
      id: "hr-2",
      challenge: "The wrongful-stop lawsuit is described as if the misread were established fact.",
      disposition: "accepted_revised",
      resolution: "Rewritten to attribute the allegation to the complaint and note it is unadjudicated (rule 2).",
    },
    {
      id: "hr-3",
      challenge: "The 31-device map figure reads as a total, not a lower bound.",
      disposition: "accepted_annotated",
      resolution: "Annotated as a lower bound in the same sentence as the number (rule 5).",
    },
    {
      id: "hr-4",
      challenge: "Counsel objects to publishing the accountability event at all.",
      disposition: "rejected_with_reason",
      resolution: "Retained: the event is accurate and W3-sourced; a response affordance is offered instead (SIG-GOV-010).",
    },
  ],
};

// --- Data-freshness (§32.4, SIG-UI-034) --------------------------------------

export const FRESHNESS_ROWS: FreshnessRow[] = [
  {
    source: "Executed procurement contract (public records request)",
    last_successful_run: "2026-08-18",
    last_content_change: "2026-08-18",
    status: "ok",
    stale_entity_count: 0,
    volatility_class: "SLOW (contract terms; multi-year half-life)",
  },
  {
    source: "Eyes on Flock portal aggregator",
    last_successful_run: "2026-08-20",
    last_content_change: "2026-07-15",
    status: "degraded",
    stale_entity_count: 3,
    volatility_class: "FAST (active device counts; six-month half-life)",
  },
  {
    source: "OpenStreetMap community map",
    last_successful_run: "2026-08-20",
    last_content_change: "2026-08-20",
    status: "ok",
    stale_entity_count: 1,
    volatility_class: "MEDIUM (physical installations)",
  },
  {
    source: "Oklahoma City Council minutes",
    last_successful_run: "2026-08-19",
    last_content_change: "2026-07-14",
    status: "ok",
    stale_entity_count: 0,
    volatility_class: "SLOW (governance actions)",
  },
];

// --- Coverage metrics (§32.5, SIG-UI-034) ------------------------------------

/**
 * The coverage metrics — counted quantities with NAMED denominators, a records-derived
 * bound, a per-agency reconciliation ratio, and measured survey recall. There is NO
 * population total and NO capture–recapture estimate (SIG-METRIC-008/009/010): every
 * metric names what it is *of* and states that the true population is unknown.
 */
export const COVERAGE_METRICS: CoverageMetric[] = [
  {
    id: "jurisdictions-with-evidence",
    kind: "counted_quantity",
    label: "Jurisdictions with any evidence on file",
    value: "34",
    denominator: "of 77 Oklahoma counties SIG has begun researching",
    population_note: "The true number of jurisdictions with surveillance infrastructure is unknown.",
    is_population_total: false,
  },
  {
    id: "okcpd-device-bound",
    kind: "records_derived_bound",
    label: "Oklahoma City PD devices (records-derived bound)",
    value: "≥ 42",
    denominator: "of the executed contract line items (a lower bound, not a count of reality)",
    population_note: "SIG does not claim to know the true device population; this is a bound.",
    is_population_total: false,
  },
  {
    id: "okcpd-reconciliation",
    kind: "reconciliation_ratio",
    label: "Portal-vs-contract reconciliation (OKCPD)",
    value: "38 reported active / 42 contracted = 0.90",
    denominator: "of the 42 contracted devices (a ratio of two named counts)",
    population_note: "This reconciles two named sources; it is not an estimate of the total population.",
    is_population_total: false,
  },
  {
    id: "okc-survey-recall",
    kind: "survey_recall",
    label: "Field-survey recall on the OKC calibration subset",
    value: "31 mapped / 42 records-listed = 0.74",
    denominator: "of the 42 records-listed OKC devices (a measurement of SIG's own field-survey method)",
    population_note: "This measures the survey's recall on a named subset only; it is NOT extrapolated to any other jurisdiction (SIG-METRIC-008b).",
    is_population_total: false,
  },
];

// --- Generated rationale templates gated by the register rules (SIG-UI-046) --

/**
 * Generated rationale text SIG publishes — the resolver's rationale strings and the
 * dossier's reconciliation notes. SIG-UI-046 binds generated text to the same register
 * rules as hand-written copy, so these are gated by `checkRegisterConformance` in the
 * tests and at build. They are drawn to read exactly as the published surfaces render.
 */
export const GENERATED_RATIONALE_TEMPLATES: readonly string[] = [
  "The W3 records-request contract (42) outranks the W2 portal snapshot (38) on 2026-07-01; the dissent is preserved and the value is marked contested.",
  "Independently mapped devices are a lower bound on the physical population, not a competing count.",
  "The portal reported 38 devices on 2026-07-01; the contract lists 42. These may measure different quantities.",
];

// --- Per-page provenance ("How we know this", SIG-UI-044) --------------------

/** The provenance summary for the research-queue surface (queue-specific counts). */
export const RESEARCH_QUEUE_PROVENANCE: ProvenanceSummary = {
  artifact_count: 4,
  tier_distribution: { W3: 1, W2: 2, W1: 1 },
  source_independence_count: 3,
  date_range: { earliest: "2025-03-25", latest: "2026-08-20" },
  rules_applied: ["task-catalog-v1", "resolver-ruleset-2026.07"],
  human_review_status: "partially_reviewed",
};

/** The provenance summary for the corrections log. */
export const CORRECTIONS_PROVENANCE: ProvenanceSummary = {
  artifact_count: CORRECTIONS.length,
  tier_distribution: { W3: 2, W2: 2 },
  source_independence_count: 3,
  date_range: { earliest: "2026-07-28", latest: "2026-08-18" },
  rules_applied: ["takedown-correction-policy-v1", "resolver-ruleset-2026.07"],
  human_review_status: "reviewed",
};
