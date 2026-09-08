// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * The "How we know this" module (§41, SIG-UI-044), as pure data + logic.
 *
 * Every page MUST carry a "How we know this" module with SIX components: artifact
 * counts, tier distribution, source-independence count, date range, rules applied,
 * and human-review status. This is the site-wide provenance affordance — distinct
 * from the dossier's own `how_we_know_this` *section* (SIG-UI-010): the module here
 * is rendered by the base layout on EVERY page, so a reader always sees, at a glance,
 * how much evidence stands behind what they are looking at and whether a human has
 * checked it.
 *
 * The module is colour-free logic; rendering lives in `components/HowWeKnowThis.astro`.
 */

/** Human-review status of the material on a page (a fixed, testable vocabulary). */
export const REVIEW_STATUSES = ["reviewed", "partially_reviewed", "unreviewed"] as const;
export type ReviewStatus = (typeof REVIEW_STATUSES)[number];

export const REVIEW_STATUS_LABELS: Record<ReviewStatus, string> = {
  reviewed: "Human-reviewed",
  partially_reviewed: "Partially human-reviewed",
  unreviewed: "Not yet human-reviewed",
};

/**
 * The six components of the "How we know this" module (SIG-UI-044). This is the
 * authoritative list; `assertProvenanceComplete` refuses to render a module missing
 * any of them, so the requirement is enforced structurally rather than by memory.
 */
export const PROVENANCE_COMPONENTS = [
  "artifact_count",
  "tier_distribution",
  "source_independence_count",
  "date_range",
  "rules_applied",
  "human_review_status",
] as const;
export type ProvenanceComponent = (typeof PROVENANCE_COMPONENTS)[number];

/** A closed date range across the evidence a page rests on. */
export interface DateRange {
  earliest: string;
  latest: string;
}

/**
 * The "How we know this" summary for a page (SIG-UI-044). Every field corresponds
 * to one of the six required components. `tier_distribution` maps evidence tier
 * (e.g. `W3`, `W2`) to a count; `source_independence_count` is the number of
 * INDEPENDENT source classes (the count the support glyph rests on, SIG-UI-003).
 */
export interface ProvenanceSummary {
  /** Artifact counts — how many evidence artifacts stand behind the page. */
  artifact_count: number;
  /** Tier distribution — count of supporting claims by evidence tier. */
  tier_distribution: Record<string, number>;
  /** Source-independence count — number of independent source classes. */
  source_independence_count: number;
  /** Date range of the evidence (null when the page rests on no dated evidence). */
  date_range: DateRange | null;
  /** Rules applied — the ruleset version and any named resolution rules that fired. */
  rules_applied: string[];
  /** Human-review status of the material on the page. */
  human_review_status: ReviewStatus;
}

/**
 * Refuse a provenance summary that is missing any of the six SIG-UI-044 components.
 * `date_range` may legitimately be null (a reference page with no dated evidence),
 * but the *key* must be present and every other component must be populated — a
 * module that silently drops a component is a SIG-UI-044 defect. Throws so a
 * misbuilt module fails the build rather than shipping.
 */
export function assertProvenanceComplete(p: ProvenanceSummary): void {
  const missing: string[] = [];
  if (!Number.isFinite(p.artifact_count)) missing.push("artifact_count");
  if (!p.tier_distribution || Object.keys(p.tier_distribution).length === 0) {
    missing.push("tier_distribution");
  }
  if (!Number.isFinite(p.source_independence_count)) missing.push("source_independence_count");
  if (!("date_range" in p)) missing.push("date_range");
  if (!Array.isArray(p.rules_applied) || p.rules_applied.length === 0) missing.push("rules_applied");
  if (!REVIEW_STATUSES.includes(p.human_review_status)) missing.push("human_review_status");
  if (missing.length > 0) {
    throw new Error(
      `"How we know this" module (SIG-UI-044) is missing component(s): ${missing.join(", ")}`,
    );
  }
}

/** A short, human-readable one-line summary of the module (for the citation/footer). */
export function provenanceOneLine(p: ProvenanceSummary): string {
  const tiers = Object.entries(p.tier_distribution)
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([tier, n]) => `${n}×${tier}`)
    .join(", ");
  const range = p.date_range ? `${p.date_range.earliest}–${p.date_range.latest}` : "no dated evidence";
  return (
    `${p.artifact_count} artifact(s) [${tiers}], ` +
    `${p.source_independence_count} independent source(s), ${range}; ` +
    `${REVIEW_STATUS_LABELS[p.human_review_status].toLowerCase()}`
  );
}

/**
 * The site-wide default provenance summary, used by the base layout for any page
 * that does not supply its own (SIG-UI-044). It describes the worked Oklahoma City
 * corpus every reference surface renders — the same evidence the dossier rests on —
 * so even a shell page carries an honest "How we know this" rather than a blank.
 */
export const DEFAULT_PROVENANCE: ProvenanceSummary = {
  artifact_count: 4,
  tier_distribution: { W3: 1, W2: 2, W1: 1 },
  source_independence_count: 3,
  date_range: { earliest: "2025-03-25", latest: "2026-08-20" },
  rules_applied: ["resolver-ruleset-2026.07", "HIGHEST_TIER_WINS"],
  human_review_status: "partially_reviewed",
};
