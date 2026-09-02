// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * Committed fixtures that mirror the read API's wire contract (api/src/api/models.py)
 * and the deterministic demo store (api/src/api/demo.py). The shell is static-first
 * (SIG-UI-036): it reads no live API at build time, so these typed fixtures stand in
 * for `sig-api` and let the reference pages exercise every component. Production wires
 * the same shapes from the real `/v1` read API — the field names here are exactly the
 * envelope's, so the components never need to change when the data goes live.
 *
 * The worked case is Appendix D.2 / the demo store: OKCPD's `active_device_count`,
 * where a records-request contract says 42 and a portal snapshot says 38.
 */

import { ABSENCE_KINDS, ABSENCE_KIND_META } from "./epistemic";
import type { Agreement, Currency, ResolutionStatus, Support, AbsenceKind, CompetingClaim } from "./epistemic";
import type { AbsenceTaskParams } from "./task";

/**
 * The §37.1 resolution envelope carried by every material fact (SIG-API-002). This
 * is a FAITHFUL SUBSET of the wire contract (`api/src/api/models.py::ResolutionEnvelope`)
 * — exactly its required fields, so the shell can be wired to the live `/v1` API
 * without changing either shape. Fields the glyph/contradiction views need that are
 * NOT on the envelope live on the outer `FactView`, not here.
 */
export interface ResolutionEnvelope {
  value: unknown;
  resolution_status: ResolutionStatus;
  support: Support;
  agreement: Agreement;
  currency: Currency | null;
  rationale: { code: string; text: string };
  supporting_claim_ids: string[];
  dissenting_claim_ids: string[];
  as_of_world: string;
  as_of_belief: string;
  ruleset_version: string;
}

/** The resolved two-axis as-of pair echoed on every read (SIG-API-005). */
export interface AsOfEcho {
  as_of_world: string;
  as_of_belief: string;
  world_defaulted: boolean;
  belief_defaulted: boolean;
  question: string;
  belief_pinned: boolean;
}

/**
 * A shell VIEW MODEL for a material fact: the wire envelope plus the presentation
 * data the shell derives around it. `evidence_count` is the independence-class
 * count the support glyph needs (SIG-UI-003) — in production it is computed by the
 * resolver from the winner's supporting evidence and surfaced alongside the
 * envelope; for a fact with no dissent it defaults to `supporting_claim_ids.length`.
 * `competing` is the plotted claim set for a contradiction (SIG-UI-009), sourced
 * from `/v1/claim` / `/v1/contradiction`, not from the envelope. Neither field is
 * part of the wire envelope, so the envelope above stays contract-faithful.
 */
export interface FactView {
  subject_id: string;
  predicate_id: string;
  label: string;
  envelope: ResolutionEnvelope;
  evidence_count: number;
  competing?: CompetingClaim[];
}

/** An absent (subject, predicate) — no claim/resolution, an explained gap (§9.5). */
export interface AbsenceFact {
  subject_id: string;
  predicate_id: string;
  label: string;
  absence_kind: AbsenceKind;
  /** For NO_EVIDENCE_FOUND: the sources searched (SIG-TIME-011). */
  sources_searched?: string[];
}

export interface EntityFixture {
  entity_id: string;
  entity_type: string;
  label: string;
  facts: FactView[];
  absences: AbsenceFact[];
}

/** The ruleset version every citation pins to (SIG-UI-035). */
export const RULESET_VERSION = "resolver-ruleset-2026.07";

/** The default as-of pair the fixtures were resolved at (belief-pinned, reproducible). */
export const AS_OF: AsOfEcho = {
  as_of_world: "2026-08-20",
  as_of_belief: "2026-08-20",
  world_defaulted: false,
  belief_defaulted: false,
  question: "as-of world 2026-08-20, belief 2026-08-20",
  belief_pinned: true,
};

/** The two competing device-count claims (Appendix D.2 / demo store). */
export const DEVICE_COUNT_CLAIMS: CompetingClaim[] = [
  {
    claimId: "contract",
    value: 42,
    source: "Public records request (city procurement)",
    tier: "W3",
    date: "2026-07-01",
    documentUrl: "/v1/claim/contract",
  },
  {
    claimId: "portal",
    value: 38,
    source: "Eyes on Flock portal aggregator",
    tier: "W2",
    date: "2026-07-01",
    documentUrl: "/v1/claim/portal",
    differentQuantityNote:
      "The portal counts devices reporting on 2026-07-01; the contract counts devices procured. These may measure different quantities.",
  },
];

export const OKCPD: EntityFixture = {
  entity_id: "agency:okcpd",
  entity_type: "agency",
  label: "Oklahoma City Police Department",
  facts: [
    {
      subject_id: "agency:okcpd",
      predicate_id: "active_device_count",
      label: "Active device count",
      envelope: {
        value: 42,
        resolution_status: "RESOLVED",
        support: "STRONGLY_SUPPORTED",
        agreement: "CONTESTED",
        currency: "CURRENT",
        rationale: {
          code: "HIGHEST_TIER_WINS",
          text: "The W3 records-request contract (42) outranks the W2 portal snapshot (38); the dissent is preserved and the value is marked contested.",
        },
        supporting_claim_ids: ["contract"],
        dissenting_claim_ids: ["portal"],
        as_of_world: AS_OF.as_of_world,
        as_of_belief: AS_OF.as_of_belief,
        ruleset_version: RULESET_VERSION,
      },
      evidence_count: 1,
      competing: DEVICE_COUNT_CLAIMS,
    },
  ],
  absences: [
    {
      subject_id: "agency:okcpd",
      predicate_id: "sharing_partners",
      label: "Data-sharing partners",
      absence_kind: "NOT_RESEARCHED",
    },
    {
      subject_id: "agency:okcpd",
      predicate_id: "retention_days",
      label: "Retention window (days)",
      absence_kind: "NO_EVIDENCE_FOUND",
      sources_searched: ["portal", "records", "council minutes 2023–2026"],
    },
  ],
};

/**
 * A claim with the belief-time it was asserted at — the minimum needed to show the
 * belief-pinned reproducibility guarantee (SIG-UI-035, SIG-TIME-008). Mirrors
 * `api.store.StoredClaim` (subset).
 */
export interface BeliefClaim {
  claim_id: string;
  value: number;
  tier: string;
  asserted_at: string; // ISO belief date
}

const TIER_RANK: Record<string, number> = { W0: 0, W1: 1, W2: 2, W3: 3, W4: 4 };

function tierRank(tier: string): number {
  const rank = TIER_RANK[tier];
  if (rank === undefined) {
    // An unknown tier must not silently rank as W0 — that would let a mislabelled
    // claim quietly lose (or win). Fail loudly so the fixture/data is corrected.
    throw new Error(`unknown evidence tier "${tier}"`);
  }
  return rank;
}

/**
 * Resolve a value AS OF a belief date, exactly as the read API does: only claims
 * asserted on or before `beliefDate` are visible, and the highest-tier admissible
 * claim wins (ties broken by the later assertion). A correction is a NEW,
 * later-asserted claim — so it is invisible to any earlier pinned belief, which is
 * precisely why a belief-pinned permalink stays reproducible after SIG corrects
 * itself. Returns null when nothing is visible yet.
 */
export function resolveAsOfBelief(claims: BeliefClaim[], beliefDate: string): number | null {
  const visible = claims.filter((c) => c.asserted_at <= beliefDate);
  if (visible.length === 0) return null;
  let winner = visible[0]!;
  for (const c of visible.slice(1)) {
    const better = tierRank(c.tier) > tierRank(winner.tier);
    const tieLater = tierRank(c.tier) === tierRank(winner.tier) && c.asserted_at > winner.asserted_at;
    if (better || tieLater) winner = c;
  }
  return winner.value;
}

/** The device-count claims with their belief-times (demo store asserted 2026-07-02). */
export const DEVICE_COUNT_BELIEF_CLAIMS: BeliefClaim[] = [
  { claim_id: "portal", value: 38, tier: "W2", asserted_at: "2026-07-02" },
  { claim_id: "contract", value: 42, tier: "W3", asserted_at: "2026-07-02" },
];

/** A row of the reference map's tabular equivalent (SIG-UI-037). */
export interface MapSite {
  id: string;
  label: string;
  jurisdiction: string;
  /** null lat/lon → coordinate reduced by sensitivity tier, or unknown (an absence). */
  lat: number | null;
  lon: number | null;
  precision: string;
  /** When the site's location is a gap, the absence kind (rendered as the hatch). */
  locationAbsence?: AbsenceKind;
}

export const REFERENCE_MAP_SITES: MapSite[] = [
  {
    id: "device:okc-001",
    label: "Fixed ALPR — downtown corridor",
    jurisdiction: "Oklahoma City",
    lat: 35.4676,
    lon: -97.5164,
    precision: "jurisdiction-centroid (C3 residential tier)",
  },
  {
    id: "device:okc-002",
    label: "RTCC integration hub",
    jurisdiction: "Oklahoma City",
    lat: 35.4823,
    lon: -97.5352,
    precision: "block-level (C2 tier)",
  },
  {
    id: "device:okc-003",
    label: "Reported camera — location unconfirmed",
    jurisdiction: "Oklahoma City",
    lat: null,
    lon: null,
    precision: "unknown",
    locationAbsence: "NOT_RESEARCHED",
  },
];

/** A node in the reference graph (the sharing network). */
export interface GraphNode {
  id: string;
  label: string;
}

/** An edge in the reference graph, with its own epistemic support. */
export interface GraphEdge {
  from: string;
  to: string;
  relation: string;
  support: Support;
  agreement: Agreement;
  evidence_count: number;
}

export const REFERENCE_GRAPH_NODES: GraphNode[] = [
  { id: "agency:okcpd", label: "Oklahoma City PD" },
  { id: "agency:ocso", label: "Oklahoma County Sheriff" },
  { id: "vendor:flock", label: "Flock Safety (vendor)" },
];

/**
 * Every taskable absence the shell links a hatch to. The intake route
 * (`pages/task/new/[slug].astro`) generates one static page per entry via
 * `getStaticPaths`, so every clickable hatch resolves to a real page with no
 * client JavaScript (SIG-UI-007, SIG-UI-036/037). Pages render hatches from this
 * registry so a link can never point at an ungenerated page.
 */
export const TASKABLE_ABSENCES: AbsenceTaskParams[] = [
  // One demonstrator per absence kind, for the visual-language reference table.
  ...ABSENCE_KINDS.map((k) => ({
    subject_id: "agency:okcpd",
    predicate_id: `demo_${k.toLowerCase()}`,
    absence_kind: k,
    predicate_label: ABSENCE_KIND_META[k].label,
  })),
  // The reference-map site whose location SIG has not confirmed.
  {
    subject_id: "device:okc-003",
    predicate_id: "location",
    absence_kind: "NOT_RESEARCHED",
    predicate_label: "Location",
  },
  // The OKCPD entity-level gaps.
  {
    subject_id: "agency:okcpd",
    predicate_id: "sharing_partners",
    absence_kind: "NOT_RESEARCHED",
    predicate_label: "Data-sharing partners",
  },
  {
    subject_id: "agency:okcpd",
    predicate_id: "retention_days",
    absence_kind: "NO_EVIDENCE_FOUND",
    predicate_label: "Retention window (days)",
  },
];

export const REFERENCE_GRAPH_EDGES: GraphEdge[] = [
  {
    from: "agency:okcpd",
    to: "vendor:flock",
    relation: "operates devices from",
    support: "CONFIRMED",
    agreement: "UNCONTESTED",
    evidence_count: 2,
  },
  {
    from: "agency:okcpd",
    to: "agency:ocso",
    relation: "shares data with",
    support: "PROBABLE",
    agreement: "CONTESTED",
    evidence_count: 1,
  },
];
