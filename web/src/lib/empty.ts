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
 *
 * P36.22 (SIG-UI-086, SIG-UI-151): EVERY surface is a typed empty state — all
 * 22 entries carry the five-part `parts` record AND a named `cause` class.
 * The hatch renders only when the cause is a real absence (a filter that
 * returns nothing, a degraded service or a rights hold is not absence).
 * New sentences drafted for this expansion are sha256-pinned `CK-*` rows in
 * `batch-02.md` (B-2); sentences carried over from the P34-era copy are bound
 * only where they were already tracked.
 */

/**
 * The route ids the surface affordances point at — declared once so the
 * paths table stays auditable (the components wrap every href in
 * `withBase()`; these constants are data, not template link constructions).
 */
const ROUTES = {
  researchQueue: "/research-queue/",
  sources: "/sources/",
  dossier: "/dossier/",
  methodology: "/methodology/",
  evidence: "/evidence/",
  dispute: "/dispute/",
} as const;

/** The public research queue — where an open gap becomes an actionable task (§39.7). */
export const RESEARCH_QUEUE_CTA = {
  href: ROUTES.researchQueue,
  label: "See the research queue",
} as const;

/**
 * The named cause classes (SIG-UI-086: "name the actual cause class"). A cause
 * is never the vague "research gap" — it states WHY the surface is empty in
 * terms a visitor can act on.
 */
export const EMPTY_CAUSES = [
  /** SIG has not looked — a real coverage/research gap (the queue is honest). */
  "not_researched",
  /** A feed or pipeline is not connected yet — a pipeline gap. */
  "not_connected",
  /** Recorded or computable but not yet released — a publication gap. */
  "not_published",
  /** Held behind a review gate (e.g. the resolution review). */
  "not_reviewed",
  /** A reviewed state: nothing is recorded for this build. */
  "none_recorded",
  /** A filter or match produced nothing — NOT an absence (no hatch). */
  "filtered_none",
  /** Rights withhold the data — NOT an absence (no hatch). */
  "not_redistributable",
  /** A service is temporarily limited — NOT an absence (no hatch). */
  "degraded",
] as const;
export type EmptyCause = (typeof EMPTY_CAUSES)[number];

/**
 * Causes that are NOT absence — the hatch must not render for them
 * (SIG-UI-151: "use the hatch only when the emptiness is absence"). Every
 * other cause renders the single absence texture.
 */
export const NON_ABSENCE_CAUSES: readonly EmptyCause[] = [
  "filtered_none",
  "not_redistributable",
  "degraded",
];

/** Whether the surface's cause renders the absence hatch. */
export function emptyStateHasHatch(cause: EmptyCause): boolean {
  return !NON_ABSENCE_CAUSES.includes(cause);
}

/**
 * Pipeline/publication causes — a gap the research queue CANNOT close. A
 * surface with one of these causes must never route the visitor to the
 * research queue as the remedy (SIG-UI-086; F-409/F-410).
 */
export const PIPELINE_CAUSES: readonly EmptyCause[] = [
  "not_connected",
  "not_published",
  "not_reviewed",
  "not_redistributable",
  "degraded",
];

/**
 * The K14 §6.4 cause-class five-part empty-state pattern (P34.20,
 * SIG-EVUI-D08; P36.22 makes it universal, SIG-UI-086/151). A surface renders
 * all five parts — a typed state label, what is missing and WHY (the named
 * cause, never a vague "research gap"), what exists nearby, what the visitor
 * can do, and when it may change.
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
  /** The named cause class (`data-cause` on the rendered state). */
  cause: EmptyCause;
  /**
   * The copy-batch row ids (`batch-02.md`, B-2) the drafted sentences are
   * tracked under — rendered as `data-copy` attributes so the publish gate
   * refuses a pending sentence (`ops/publish.py#check_publishable_copy`).
   * Partial: a part carried over from the P34-era copy unbound renders no
   * `data-copy` (it was never batch-tracked); a sentence this row drafted
   * carries its `CK-*` row id.
   */
  batchIds: Partial<Record<"state" | "missing" | "nearby" | "action" | "change", string>>;
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
  // P36.22 (SIG-UI-086): a publication gap — the dossier is not released yet,
  // so the affordance is a nearby surface, never the research queue.
  landingReach: causeClass({
    state: "No jurisdiction dossiers published yet",
    missing:
      "SIG has not yet published a dossier to a releasable standard. This is a gap in coverage, not a finding that no jurisdiction has surveillance infrastructure.",
    nearby:
      "The sources page lists what this release has collected even before a dossier is ready.",
    action: { href: ROUTES.sources, label: "See the sources" },
    change:
      "A jurisdiction's dossier appears here once a release publishes it to a releasable standard.",
    cause: "not_published",
    batchIds: { nearby: "CK-01", action: "CK-02", change: "CK-03" },
  }),
  landingCoverage: causeClass({
    state: "No coverage metrics published yet",
    missing:
      "SIG publishes counted quantities with named denominators, never a total. None are published yet — absence of a metric is not a measurement of zero.",
    nearby:
      "The sources page lists what this release carries even before counted quantities are published.",
    action: { href: ROUTES.sources, label: "See the sources" },
    change: "Counted quantities appear here once a release publishes them.",
    cause: "not_published",
    batchIds: { nearby: "CK-04", action: "CK-05", change: "CK-06" },
  }),
  dossierIndex: causeClass({
    state: "No dossiers published yet",
    missing:
      "This index lists jurisdictions SIG has researched to a publishable standard; none are published yet. A jurisdiction absent here is one SIG has not yet published, not one with no surveillance infrastructure.",
    nearby: "The map's located records cover places that have no published dossier yet.",
    action: { href: ROUTES.sources, label: "See the sources" },
    change: "A dossier joins this index when a release publishes it.",
    cause: "not_published",
    batchIds: { nearby: "CK-07", action: "CK-08", change: "CK-09" },
  }),
  // A real coverage gap — the queue is the honest affordance here.
  mapAssets: causeClass({
    state: "No located assets to show yet",
    missing:
      "SIG has published no assets with a releasable point for this view. Low coverage is a gap, never a finding of low density — the absence of a marker does not mean the absence of infrastructure.",
    nearby: "Records without a published point are listed below the map when they exist.",
    action: RESEARCH_QUEUE_CTA,
    change: "Located assets appear on the map as releases publish them.",
    cause: "not_researched",
    batchIds: { nearby: "CK-10", change: "CK-11" },
  }),
  mapBins: causeClass({
    state: "No coverage bins to show yet",
    missing:
      "SIG has computed no national-view density bins for this build. An empty map reads as unresearched, never as confidently empty.",
    nearby: "The located-records table below lists what is published for this view.",
    action: { href: ROUTES.dossier, label: "Browse the dossiers" },
    change: "Density bins appear with a release once they are computed and published.",
    cause: "not_published",
    batchIds: { nearby: "CK-12", action: "CK-13", change: "CK-14" },
  }),
  mapIndicators: causeClass({
    state: "No point-less assets recorded here",
    missing:
      "SIG records no assets whose point is withheld or unknown for this view. This states what SIG has recorded, not what exists on the ground.",
    nearby: "Located records appear on the map above when the view has them.",
    action: { href: ROUTES.dossier, label: "Browse the dossiers" },
    change: "This list fills with a release when records carry a withheld or unknown point.",
    cause: "none_recorded",
    batchIds: { nearby: "CK-15", action: "CK-13", change: "CK-16" },
  }),
  network: causeClass({
    state: "No sharing network to show yet",
    missing:
      "SIG has published no sharing or access edges for this view. An empty graph means SIG has not yet documented the connections, not that none exist.",
    nearby: "The dossiers name the sharing partners SIG has recorded.",
    action: { href: ROUTES.dossier, label: "Browse the dossiers" },
    change: "Sharing and access edges appear here once a release publishes them.",
    cause: "not_published",
    batchIds: { nearby: "CK-17", action: "CK-18", change: "CK-19" },
  }),
  centrality: causeClass({
    state: "No centrality statistics yet",
    missing:
      "Network statistics are only as good as entity resolution; SIG publishes none until the resolution review that would make one honest has passed its gate. Their absence is not a measurement of zero.",
    nearby: "The network view lists the sharing edges that are published.",
    action: { href: ROUTES.methodology, label: "See the methodology" },
    change:
      "Network statistics appear once the resolution review that makes one honest passes its gate.",
    cause: "not_reviewed",
    batchIds: { nearby: "CK-20", action: "CK-21", change: "CK-22" },
  }),
  accessEdges: causeClass({
    state: "No edges of this access type recorded",
    missing:
      "SIG has documented no edges of this access type for this view. Absence of an edge is not evidence that the access does not exist — only that SIG has not evidenced it.",
    nearby: "Other access kinds may already have recorded edges for this view.",
    action: RESEARCH_QUEUE_CTA,
    change: "Edges of this kind appear with a release once SIG evidences them.",
    cause: "not_researched",
    batchIds: { nearby: "CK-23", change: "CK-24" },
  }),
  accessPaths: causeClass({
    state: "No access paths documented yet",
    missing:
      "SIG has closed no multi-hop access paths for this view. An empty list means the reachability question is unresearched, not answered in the negative.",
    nearby: "Published access edges are listed for each view above.",
    action: RESEARCH_QUEUE_CTA,
    change: "A closed path appears with a release once the reachability work lands.",
    cause: "not_researched",
    batchIds: { nearby: "CK-25", change: "CK-26" },
  }),
  freshness: causeClass({
    // P35.40: "registry sources" — one source is one registry row; the empty
    // freshness table means no registry row carries a freshness record.
    state: "No registry sources tracked for freshness yet",
    missing:
      "SIG's source registry holds no rows with a freshness record for this build. This is the registry set — never a count of all sources that exist.",
    nearby: "The sources page lists every registry source this release covers.",
    action: { href: ROUTES.sources, label: "See the sources" },
    change:
      "Freshness rows appear once registry sources carry a freshness record in a release.",
    cause: "not_published",
    batchIds: { nearby: "CK-27", action: "CK-28", change: "CK-29" },
  }),
  coverage: causeClass({
    state: "No coverage metrics published yet",
    missing:
      "SIG has published no counted quantities for this build. It never publishes a total, and the absence of a metric is not a measurement of zero (SIG-METRIC-010).",
    nearby: "The dossier index lists what is published for each jurisdiction.",
    action: { href: ROUTES.dossier, label: "Browse the dossiers" },
    change: "Counted quantities appear with a release once they are published.",
    cause: "not_published",
    batchIds: { nearby: "CK-30", action: "CK-31", change: "CK-32" },
  }),
  watch: causeClass({
    state: "No upcoming decisions are tracked yet.",
    missing:
      "The watch is not yet connected to SIG's procurement and agenda data, so no upcoming decision appears here.",
    nearby:
      "SIG does hold some dated records (for example federal solicitations) that will appear here once it is.",
    action: { href: ROUTES.dossier, label: "Browse the dossiers" },
    change:
      "The watch fills in with a release once the procurement and agenda feeds are connected.",
    cause: "not_connected",
    batchIds: { state: "EW-01", missing: "EW-02", nearby: "EW-03", action: "EW-04", change: "EW-05" },
  }),
  watchSubscriptions: causeClass({
    state: "No jurisdictions to subscribe to yet.",
    missing:
      "A per-jurisdiction feed appears once the watch tracks a dated decision there; none are tracked yet.",
    nearby: "The watch section above names the cause — the feeds come up with it.",
    action: { href: ROUTES.dossier, label: "Browse the dossiers" },
    change: "Feeds appear with a release once decisions are tracked.",
    cause: "not_connected",
    batchIds: { state: "EW-06", missing: "EW-07", nearby: "EW-08", action: "EW-04", change: "EW-09" },
  }),
  recommender: causeClass({
    state: "No evidence ranked yet.",
    missing:
      "Nothing is ranked for an upcoming decision — the watch is not yet tracking one, and SIG's artifacts are not yet linked to stored documents.",
    nearby: "The published artifacts this release carries are listed on the evidence page.",
    action: { href: ROUTES.evidence, label: "See the published artifacts" },
    change: "Ranked evidence appears with a release once a dated decision is tracked.",
    cause: "not_connected",
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
    action: { href: ROUTES.evidence, label: "See the published artifacts" },
    change: "The list appears when evidence is ranked for a decision.",
    cause: "not_connected",
    batchIds: {
      state: "EW-15",
      missing: "EW-16",
      nearby: "EW-12",
      action: "EW-13",
      change: "EW-17",
    },
  }),
  corrections: causeClass({
    state: "No corrections recorded yet",
    missing:
      "SIG has recorded no corrections for this build. This is an honest empty log, not a claim that nothing has ever needed correcting.",
    nearby: "The methodology names how a correction is recorded when one is needed.",
    action: { href: ROUTES.dispute, label: "Report an error" },
    change: "Each recorded correction lands here as a new entry with a release.",
    cause: "none_recorded",
    batchIds: { nearby: "CK-33", change: "CK-34" },
  }),
  researchQueue: causeClass({
    state: "No open research tasks right now",
    missing:
      "The queue is empty for this build. This does not mean the record is complete — every dossier still names what SIG does not know, and new gaps open a task as they are found.",
    nearby: "Every dossier names what SIG does not know yet.",
    action: { href: ROUTES.dossier, label: "Browse the dossiers" },
    change: "A gap opens a task here as review finds it, with a release.",
    cause: "none_recorded",
    batchIds: { nearby: "CK-35", change: "CK-36" },
  }),
  researchFilter: causeClass({
    state: "No jurisdictions in the queue yet",
    missing:
      "The per-jurisdiction filter appears once the queue has tasks scoped to a place. It has none yet.",
    nearby: "The queue's open tasks are listed below.",
    action: { href: ROUTES.dossier, label: "Browse the dossiers" },
    change: "The filter appears once tasks are scoped to a place.",
    cause: "none_recorded",
    batchIds: { nearby: "CK-37", change: "CK-38" },
  }),
  researchDossierIndex: causeClass({
    state: "No reviewed research dossiers yet",
    missing:
      "SIG has not yet published a reviewed research dossier — the evidence-complete twelve-question portfolio. Absence here means none has passed review, not that the questions have no answers; the inventory overviews remain at the dossier index.",
    nearby: "The dossier index keeps the inventory overviews.",
    action: { href: ROUTES.dossier, label: "Browse the dossier index" },
    change: "A reviewed research dossier appears here once it passes review in a release.",
    cause: "not_reviewed",
    batchIds: { nearby: "CK-39", change: "CK-40" },
  }),
  evidenceIndex: causeClass({
    state: "No document views yet.",
    missing:
      "SIG has not yet linked a claim to a stored document it can publish, so no full evidence view is available for this build.",
    nearby: "The artifacts the release does carry are listed below, grouped by source.",
    action: { href: ROUTES.sources, label: "See the sources" },
    change:
      "Document views appear with a release once claims are bound to publishable documents.",
    cause: "not_published",
    batchIds: {
      state: "EW-18",
      missing: "EW-19",
      nearby: "EW-20",
      action: "EW-21",
      change: "EW-22",
    },
  }),
  dossierGaps: causeClass({
    state: "No record in SIG",
    missing:
      "SIG has recorded no open gap here. This reflects what has been reviewed so far; it is not a guarantee the record is complete.",
    nearby: "The research queue lists the gaps SIG has turned into tasks.",
    action: RESEARCH_QUEUE_CTA,
    change: "Open gaps appear here as review finds them, with a release.",
    cause: "none_recorded",
    batchIds: { nearby: "CK-41", change: "CK-42" },
  }),
};

/** The honest empty-state copy for a surface (heading + framing body + task affordance). */
export function emptyState(surface: EmptySurface): EmptyStateCopy {
  return COPY[surface];
}

/** Every surface id (for tests + exhaustiveness). */
export const EMPTY_SURFACES = Object.keys(COPY) as EmptySurface[];
