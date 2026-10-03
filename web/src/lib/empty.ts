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
 *
 * P34.20 (K14 §6.4, SIG-EVUI-D08): surfaces whose emptiness has a NAMED cause —
 * the watch, its subscriptions, the recommender, the citation list and the
 * evidence index — carry a `parts` record instead of a generic body: the
 * five-part cause-class pattern, which names the real cause, never calls it a
 * "research gap", and never points at the research queue as the remedy for a
 * pipeline gap the queue cannot close (F-409/F-410).
 */

/** The public research queue — where an open gap becomes an actionable task (§39.7). */
export const RESEARCH_QUEUE_CTA = {
  href: "/research-queue/",
  label: "See the research queue",
} as const;

/**
 * The K14 §6.4 cause-class five-part empty-state pattern (P34.20,
 * SIG-EVUI-D08). A surface whose emptiness has a named real cause renders all
 * five parts — a typed state label, what is missing and WHY (the cause class,
 * never a vague "research gap"), what exists nearby, what the visitor can do,
 * and when it may change — instead of the generic heading+body+queue-CTA.
 */
export interface EmptyStateParts {
  /** 1 — state label: a typed kind, never a bare "empty". */
  state: string;
  /** 2 — what is missing, and why: the named cause class. */
  missing: string;
  /** 3 — what exists nearby. */
  nearby: string;
  /** 4 — what the visitor can do (an honest affordance, never the queue as remedy). */
  action: { href: string; label: string };
  /** 5 — when it may change. */
  change: string;
  /**
   * The copy-batch row ids (`batch-02.md`, B-2) each part's sentence is
   * tracked under — rendered as `data-copy` attributes so the publish gate
   * refuses a pending sentence (`ops/publish.py#check_publishable_copy`).
   */
  batchIds: { state: string; missing: string; nearby: string; action: string; change: string };
}

export interface EmptyStateCopy {
  /** A short, honest heading — states that the surface is empty, not that reality is. */
  heading: string;
  /** Plain-language body: absence is not evidence of absence (SIG-UI-011, §3.1). */
  body: string;
  /** The clickable task affordance (a gap is an invitation, not a dead end). */
  cta: { href: string; label: string };
  /**
   * K14 §6.4 cause-class expansion — present only on surfaces whose emptiness
   * has a named cause. When set, `EmptyState.astro` renders the five parts;
   * `heading`/`body`/`cta` mirror `state`/`missing`/`action` so a naive
   * consumer still renders honest copy.
   */
  parts?: EmptyStateParts;
}

/**
 * Build a cause-class entry: the five parts are the source of truth; the
 * legacy heading/body/cta fields derive from them so the two render paths
 * can never drift apart.
 */
function causeClass(parts: EmptyStateParts): EmptyStateCopy {
  return { heading: parts.state, body: parts.missing, cta: parts.action, parts };
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
  | "researchDossierIndex"
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
    body: "Network statistics are only as good as entity resolution; SIG publishes none until the resolution review that would make one honest has passed its gate. Their absence is not a measurement of zero.",
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
  watch: causeClass({
    state: "No upcoming decisions are tracked yet.",
    missing:
      "The watch is not yet connected to SIG's procurement and agenda data, so no upcoming decision appears here.",
    nearby:
      "SIG does hold some dated records (for example federal solicitations) that will appear here once it is.",
    action: { href: "/dossier/", label: "Browse the dossiers" },
    change:
      "The watch fills in with a release once the procurement and agenda feeds are connected.",
    batchIds: { state: "EW-01", missing: "EW-02", nearby: "EW-03", action: "EW-04", change: "EW-05" },
  }),
  watchSubscriptions: causeClass({
    state: "No jurisdictions to subscribe to yet.",
    missing:
      "A per-jurisdiction feed appears once the watch tracks a dated decision there; none are tracked yet.",
    nearby: "The watch section above names the cause — the feeds come up with it.",
    action: { href: "/dossier/", label: "Browse the dossiers" },
    change: "Feeds appear with a release once decisions are tracked.",
    batchIds: { state: "EW-06", missing: "EW-07", nearby: "EW-08", action: "EW-04", change: "EW-09" },
  }),
  recommender: causeClass({
    state: "No evidence ranked yet.",
    missing:
      "Nothing is ranked for an upcoming decision — the watch is not yet tracking one, and SIG's artifacts are not yet linked to stored documents.",
    nearby: "The published artifacts this release carries are listed on the evidence page.",
    action: { href: "/evidence/", label: "See the published artifacts" },
    change: "Ranked evidence appears with a release once a dated decision is tracked.",
    batchIds: {
      state: "EW-10",
      missing: "EW-11",
      nearby: "EW-12",
      action: "EW-13",
      change: "EW-14",
    },
  }),
  citations: causeClass({
    state: "No citation list yet.",
    missing: "The citation list is built from the ranked evidence; nothing is ranked yet.",
    nearby: "The published artifacts this release carries are listed on the evidence page.",
    action: { href: "/evidence/", label: "See the published artifacts" },
    change: "The list appears when evidence is ranked for a decision.",
    batchIds: {
      state: "EW-15",
      missing: "EW-16",
      nearby: "EW-12",
      action: "EW-13",
      change: "EW-17",
    },
  }),
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
  researchDossierIndex: {
    heading: "No reviewed research dossiers yet",
    body: "SIG has not yet published a reviewed research dossier — the evidence-complete twelve-question portfolio. Absence here means none has passed review, not that the questions have no answers; the inventory overviews remain at the dossier index.",
    cta: { href: "/dossier/", label: "Browse the dossier index" },
  },
  evidenceIndex: causeClass({
    state: "No document views yet.",
    missing:
      "SIG has not yet linked a claim to a stored document it can publish, so no full evidence view is available for this build.",
    nearby: "The artifacts the release does carry are listed below, grouped by source.",
    action: { href: "/sources/", label: "See the sources" },
    change:
      "Document views appear with a release once claims are bound to publishable documents.",
    batchIds: {
      state: "EW-18",
      missing: "EW-19",
      nearby: "EW-20",
      action: "EW-21",
      change: "EW-22",
    },
  }),
  dossierGaps: {
    heading: "No record in SIG",
    body: "SIG has recorded no open gap here. This reflects what has been reviewed so far; it is not a guarantee the record is complete.",
    cta: RESEARCH_QUEUE_CTA,
  },
};

/** The honest empty-state copy for a surface (heading + framing body + task affordance). */
export function emptyState(surface: EmptySurface): EmptyStateCopy {
  return COPY[surface];
}

/** Every surface id (for tests + exhaustiveness). */
export const EMPTY_SURFACES = Object.keys(COPY) as EmptySurface[];
