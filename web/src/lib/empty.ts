// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * Honest empty / partial / gap states for every aggregate surface (§9.5, §15,
 * SIG-UI-007, the §3.1 defining standard).
 *
 * At national scale a surface's data can be abundant, thin, or absent. Absence MUST
 * be rendered as a visible, explained gap — never a blank section and never a
 * fabricated zero ("0 devices" reads as "there are none", when the truth is "SIG has
 * not looked here yet"). This module is the single source of the honest copy each
 * surface shows when its data is empty: a heading, a plain-language body that frames
 * absence as *not-yet-researched* rather than *nothing exists*, and — because a gap
 * is an invitation, not a dead end — a clickable affordance that turns the gap into
 * work (the public research queue, where open gaps become tasks).
 *
 * It carries NO colour and NO markup: the `EmptyState.astro` component supplies the
 * single absence texture and the accessible structure; this module is pure data +
 * logic so the honesty rules are unit-testable independently of any style (mirrors
 * `epistemic.ts`).
 */

/** The public research queue — where an open gap becomes an actionable task (§39.7). */
export const RESEARCH_QUEUE_CTA = {
  href: "/research-queue/",
  label: "See the research queue",
} as const;

export interface EmptyStateCopy {
  /** A short, honest heading — states that the surface is empty, not that reality is. */
  heading: string;
  /** Plain-language body: absence is not evidence of absence (SIG-UI-011, §3.1). */
  body: string;
  /** The clickable task affordance (a gap is an invitation, not a dead end). */
  cta: { href: string; label: string };
}

/** The aggregate surfaces that can legitimately render empty at national scale. */
export type EmptySurface =
  | "landingReach"
  | "landingCoverage"
  | "dossierIndex"
  | "mapAssets"
  | "mapBins"
  | "mapIndicators"
  | "network"
  | "centrality"
  | "accessEdges"
  | "accessPaths"
  | "freshness"
  | "coverage"
  | "watch"
  | "watchSubscriptions"
  | "recommender"
  | "citations"
  | "corrections"
  | "researchQueue"
  | "researchFilter"
  | "evidenceIndex"
  | "dossierGaps";

// The honest copy per surface. Every body frames absence as "SIG has not (yet)
// published / looked", never as an assertion that the thing does not exist, and never
// implies a known denominator (SIG-METRIC-010). Every entry carries a task affordance.
const COPY: Record<EmptySurface, EmptyStateCopy> = {
  landingReach: {
    heading: "No jurisdiction dossiers published yet",
    body: "SIG has not yet published a dossier to a releasable standard. This is a gap in coverage, not a finding that no jurisdiction has surveillance infrastructure.",
    cta: RESEARCH_QUEUE_CTA,
  },
  landingCoverage: {
    heading: "No coverage metrics published yet",
    body: "SIG publishes counted quantities with named denominators, never a total. None are published yet — absence of a metric is not a measurement of zero.",
    cta: RESEARCH_QUEUE_CTA,
  },
  dossierIndex: {
    heading: "No dossiers published yet",
    body: "This index lists jurisdictions SIG has researched to a publishable standard; none are published yet. A jurisdiction absent here is one SIG has not yet published, not one with no surveillance infrastructure.",
    cta: RESEARCH_QUEUE_CTA,
  },
  mapAssets: {
    heading: "No located assets to show yet",
    body: "SIG has published no assets with a releasable point for this view. Low coverage is a gap, never a finding of low density — the absence of a marker does not mean the absence of infrastructure.",
    cta: RESEARCH_QUEUE_CTA,
  },
  mapBins: {
    heading: "No coverage bins to show yet",
    body: "SIG has computed no national-view density bins for this build. An empty map reads as unresearched, never as confidently empty.",
    cta: RESEARCH_QUEUE_CTA,
  },
  mapIndicators: {
    heading: "No point-less assets recorded here",
    body: "SIG records no assets whose point is withheld or unknown for this view. This states what SIG has recorded, not what exists on the ground.",
    cta: RESEARCH_QUEUE_CTA,
  },
  network: {
    heading: "No sharing network to show yet",
    body: "SIG has published no sharing or access edges for this view. An empty graph means SIG has not yet documented the connections, not that none exist.",
    cta: RESEARCH_QUEUE_CTA,
  },
  centrality: {
    heading: "No centrality statistics yet",
    body: "Network statistics are only as good as entity resolution; SIG publishes none until there is a network to measure. Their absence is not a measurement of zero.",
    cta: RESEARCH_QUEUE_CTA,
  },
  accessEdges: {
    heading: "No edges of this access type recorded",
    body: "SIG has documented no edges of this access type for this view. Absence of an edge is not evidence that the access does not exist — only that SIG has not evidenced it.",
    cta: RESEARCH_QUEUE_CTA,
  },
  accessPaths: {
    heading: "No access paths documented yet",
    body: "SIG has closed no multi-hop access paths for this view. An empty list means the reachability question is unresearched, not answered in the negative.",
    cta: RESEARCH_QUEUE_CTA,
  },
  freshness: {
    heading: "No sources tracked for freshness yet",
    body: "SIG monitors no sources for this build. This is the set SIG tracks — never a count of all sources that exist.",
    cta: RESEARCH_QUEUE_CTA,
  },
  coverage: {
    heading: "No coverage metrics published yet",
    body: "SIG has published no counted quantities for this build. It never publishes a total, and the absence of a metric is not a measurement of zero (SIG-METRIC-010).",
    cta: RESEARCH_QUEUE_CTA,
  },
  watch: {
    heading: "No contracts on the watch yet",
    body: "SIG is tracking no upcoming procurement or renewal decisions for this build. An empty watch means SIG has not documented an upcoming decision, not that none is pending.",
    cta: RESEARCH_QUEUE_CTA,
  },
  watchSubscriptions: {
    heading: "No jurisdictions to subscribe to yet",
    body: "A per-jurisdiction subscription appears once SIG is tracking a dated decision there. None are tracked yet.",
    cta: RESEARCH_QUEUE_CTA,
  },
  recommender: {
    heading: "No evidence to rank yet",
    body: "SIG has published no evidence artifacts for the upcoming decision. Their absence is a research gap, not a judgement that no evidence exists.",
    cta: RESEARCH_QUEUE_CTA,
  },
  citations: {
    heading: "No citation list yet",
    body: "The citation list is built from the ranked evidence; with no evidence published there is nothing to cite yet.",
    cta: RESEARCH_QUEUE_CTA,
  },
  corrections: {
    heading: "No corrections recorded yet",
    body: "SIG has recorded no corrections for this build. This is an honest empty log, not a claim that nothing has ever needed correcting.",
    cta: { href: "/dispute/", label: "Report an error" },
  },
  researchQueue: {
    heading: "No open research tasks right now",
    body: "The queue is empty for this build. This does not mean the record is complete — every dossier still names what SIG does not know, and new gaps open a task as they are found.",
    cta: { href: "/dossier/", label: "Browse the dossiers" },
  },
  researchFilter: {
    heading: "No jurisdictions in the queue yet",
    body: "The per-jurisdiction filter appears once the queue has tasks scoped to a place. It has none yet.",
    cta: { href: "/dossier/", label: "Browse the dossiers" },
  },
  evidenceIndex: {
    heading: "No claims with a full evidence view yet",
    body: "SIG has published no claims whose full evidence view is available for this build. Their absence is a research gap, not evidence that no claims exist.",
    cta: RESEARCH_QUEUE_CTA,
  },
  dossierGaps: {
    heading: "No open gaps recorded for this dossier",
    body: "SIG has recorded no unresearched fields here. This reflects what has been reviewed so far; it is not a guarantee the record is complete.",
    cta: RESEARCH_QUEUE_CTA,
  },
};

/** The honest empty-state copy for a surface (heading + framing body + task affordance). */
export function emptyState(surface: EmptySurface): EmptyStateCopy {
  return COPY[surface];
}

/** Every surface id (for tests + exhaustiveness). */
export const EMPTY_SURFACES = Object.keys(COPY) as EmptySurface[];
