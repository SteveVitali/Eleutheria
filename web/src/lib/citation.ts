// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * Belief-pinned permalinks and the "cite this page" affordance (SIG-UI-035,
 * SIG-TIME-008). Every page carries both. A citation made today MUST remain
 * reproducible after SIG corrects itself, so the permalink pins BOTH as-of axes
 * (world and belief) and the ruleset version: re-resolving that exact triple
 * returns the same answer even after a later correction appends a new claim.
 */

import type { AsOfEcho } from "./fixtures";

export interface CitationInput {
  /** The page's canonical path, e.g. "/entity/agency/okcpd/". */
  path: string;
  title: string;
  asOf: AsOfEcho;
  rulesetVersion: string;
  /** The site origin; defaults to the archival canonical origin. */
  origin?: string;
}

const DEFAULT_ORIGIN = "https://sig.example";

/**
 * The belief-pinned permalink: the canonical path with BOTH as-of axes and the
 * ruleset version fixed as query parameters. Because belief-time is pinned, a
 * correction (a new, later-asserted claim) is invisible to this URL — the citation
 * is reproducible (SIG-UI-035, SIG-API-006).
 */
export function beliefPinnedPermalink(input: CitationInput): string {
  const origin = input.origin ?? DEFAULT_ORIGIN;
  const q = new URLSearchParams({
    as_of_world: input.asOf.as_of_world,
    as_of_belief: input.asOf.as_of_belief,
    ruleset: input.rulesetVersion,
  });
  return `${origin}${input.path}?${q.toString()}`;
}

/**
 * The human-readable citation string, in the reporting register (SIG-UI-043):
 * it states the source, the two as-of instants, the ruleset, and the permalink —
 * dated and specific, never "as of now".
 */
export function citationText(input: CitationInput): string {
  const permalink = beliefPinnedPermalink(input);
  return (
    `Surveillance Infrastructure Graph (SIG), "${input.title}", ` +
    `as of world ${input.asOf.as_of_world}, belief ${input.asOf.as_of_belief}, ` +
    `ruleset ${input.rulesetVersion}. Retrieved from ${permalink}`
  );
}
