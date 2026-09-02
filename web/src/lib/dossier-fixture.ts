// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * The worked local dossier (§39.2, Appendix B/D) as a committed fixture. The shell
 * is static-first (SIG-UI-036): it reads no live API at build, so this typed fixture
 * stands in for the `/v1` dossier contract. It is the Appendix-D "Example City"
 * worked case, keyed to the demo OKCPD entity the rest of the shell already renders
 * (the 42-vs-38 contested device count), so the dossier, the reference map, and the
 * visual-language reference all speak about the same jurisdiction.
 *
 * The worked object deliberately exercises every SIG-UI-010..015 requirement:
 *   - all twelve sections, in order (SIG-UI-010);
 *   - "what we don't know" as a curated headline list (SIG-UI-011);
 *   - unresearched + no-evidence-found + unresolved gaps (SIG-UI-012, §9.5);
 *   - material figures with full reconciliations (SIG-UI-014), incl. a lower bound;
 *   - the three action blocks with the Appendix-D auto-renewal deadline
 *     (expiry 2027-04-02, 90-day notice → decision date 2027-01-02) (SIG-UI-014a/b);
 *   - `unknown` values rendered explicitly, never omitted (SIG-UI-015).
 */

import { isContested } from "./epistemic";
import { AS_OF, DEVICE_COUNT_CLAIMS, OKCPD, RULESET_VERSION } from "./fixtures";
import type { CompetingClaim } from "./epistemic";
import type { Dossier, Figure } from "./dossier";

const deviceFact = OKCPD.facts[0]!;

/**
 * The headline material figure — active device count — reusing the shell's existing
 * contested 42-vs-38 fact so the dossier and the reference surfaces agree. The W3
 * records-request contract (42) wins; the W2 portal snapshot (38) is preserved as a
 * dissenting claim with the "different quantity" note (§29.1, SIG-UI-009/014).
 */
const activeDeviceCount: Figure = {
  key: "active_device_count",
  label: "Active device count",
  value: deviceFact.envelope.value as number,
  unit: "devices",
  support: deviceFact.envelope.support,
  evidenceCount: deviceFact.evidence_count,
  contested: isContested(deviceFact.envelope.agreement),
  reconciliation: {
    rule: deviceFact.envelope.rationale.code,
    winningClaimId: "contract",
    claims: DEVICE_COUNT_CLAIMS,
    note: deviceFact.envelope.rationale.text,
  },
};

/** An independently-mapped count — a LOWER BOUND on the physical population (§D.2). */
const MAPPED_CLAIMS: CompetingClaim[] = [
  {
    claimId: "osm",
    value: 31,
    source: "OpenStreetMap community map",
    tier: "W2",
    date: "2026-08-20",
    documentUrl: "/v1/claim/osm",
  },
];

const mappedDeviceCount: Figure = {
  key: "mapped_device_count",
  label: "Independently mapped devices",
  value: 31,
  unit: "devices",
  lowerBound: true,
  support: "PROBABLE",
  evidenceCount: 1,
  contested: false,
  reconciliation: {
    rule: "INDEPENDENT_MAP_LOWER_BOUND",
    winningClaimId: "osm",
    claims: MAPPED_CLAIMS,
    note: "Independently mapped devices are a lower bound on the physical population, not a competing count.",
  },
};

/**
 * The worked dossier. The section list is the twelve §39.2 ids in order
 * (SIG-UI-010); `validateDossier` enforces it at render time.
 */
export const OKC_DOSSIER: Dossier = {
  slug: "oklahoma-city",
  subject_label: "Oklahoma City Police Department — ALPR deployment",
  jurisdiction: "Oklahoma City, Oklahoma",
  asOf: AS_OF,
  rulesetVersion: RULESET_VERSION,
  source_families: [
    "Executed procurement contract (public records request)",
    "Eyes on Flock portal aggregator",
    "OpenStreetMap community map",
    "Oklahoma City Council minutes",
  ],
  authorization: {
    // The single most actionable thing a local advocate can learn (SIG-UI-014a):
    // this passed unopposed on the consent agenda, with no public comment taken.
    approving_body: "Oklahoma City Council",
    vote: "Consent agenda (no roll-call vote)",
    consent_agenda: true,
    public_comment: false,
    date: "2025-03-25",
  },
  termination: {
    // The Appendix-D auto-renewal case: the decision date, not the expiry, is what
    // matters — 2027-04-02 minus a 90-day notice window is 2027-01-02 (SIG-UI-014b).
    auto_renews: true,
    notice_window_days: 90,
    expiry_date: "2027-04-02",
  },
  legal_regime: {
    state_statute: "Okla. Stat. tit. 47 — ALPR data retention limits",
    local_ordinance: "Oklahoma City Municipal Code ch. 30 (surveillance procurement)",
    disclosure_duties: [
      "Oklahoma Open Records Act — response to public records requests",
      "Council approval required for surveillance-technology procurement",
    ],
  },
  gaps: [
    {
      label: "Data-sharing partners",
      kind: "NOT_RESEARCHED",
      subject_id: "agency:okcpd",
      predicate_id: "sharing_partners",
      note: "SIG has not yet researched which agencies OKCPD shares ALPR data with.",
    },
    {
      label: "Retention window (days)",
      kind: "NO_EVIDENCE_FOUND",
      subject_id: "agency:okcpd",
      predicate_id: "retention_days",
      sources_searched: ["portal", "records request", "council minutes 2023–2026"],
    },
    {
      label: "Unexplained delta: 42 contracted vs 38 active",
      kind: "UNRESOLVED",
      subject_id: "agency:okcpd",
      predicate_id: "contracted_active_delta",
      note: "Four contracted devices are not reported active. Were they never installed, or removed?",
    },
    {
      label: "At least 7 active devices are unmapped",
      kind: "NOT_RESEARCHED",
      subject_id: "agency:okcpd",
      predicate_id: "unmapped_devices",
      note: "38 reported active, 31 independently mapped — locate and map at least seven.",
    },
  ],
  sections: [
    {
      section_id: "at_a_glance",
      rows: [
        { label: "Operator", value: "Oklahoma City Police Department" },
        { label: "Technology", value: "Automated licence-plate readers (ALPR) + RTCC integration" },
        { label: "Lifecycle status", value: "Operational" },
      ],
    },
    {
      section_id: "what_is_deployed",
      figures: [activeDeviceCount, mappedDeviceCount],
      rows: [
        { label: "Device type", value: "Fixed ALPR cameras; one RTCC integration hub" },
      ],
    },
    {
      section_id: "cost_and_expiry",
      rows: [
        { label: "Contract value (annual)", value: null, note: "Not disclosed in the released contract." },
        { label: "Contract expiry", value: "2027-04-02", documentUrl: "/v1/claim/contract" },
      ],
    },
    {
      section_id: "who_else_can_see",
      rows: [
        {
          label: "Data-sharing partners",
          value: null,
          absence: "NOT_RESEARCHED",
          subject_id: "agency:okcpd",
          predicate_id: "sharing_partners",
        },
        { label: "Configured-access edges (observed 2026-07-14)", value: 147, note: "Configured access — not 'currently shares with 147' (§12.2, SIG-TIME-005)." },
      ],
    },
    {
      section_id: "configuration_and_retention",
      rows: [
        { label: "Policy written retention (days)", value: null, note: "Policy document not located." },
        { label: "Configured retention (days)", value: null, absence: "NO_EVIDENCE_FOUND", subject_id: "agency:okcpd", predicate_id: "retention_days" },
        { label: "Vendor default retention (days)", value: 30, documentUrl: "/v1/claim/vendor-default" },
      ],
    },
    {
      section_id: "usage",
      rows: [
        { label: "Searches (30-day window ending 2026-07-15)", value: 412, note: "A windowed count with explicit bounds — never rendered as a current rate (SIG-RECON-011)." },
      ],
    },
    {
      section_id: "where_the_hardware_is",
      rows: [
        { label: "Independently mapped devices", value: 31, note: "A lower bound. See the reference map for locations at published precision." },
        { label: "Reference map", value: "/reference-map/", documentUrl: "/reference-map/" },
      ],
    },
    {
      section_id: "policy",
      rows: [
        {
          label: "Immigration-enforcement configuration evidence",
          value: null,
          absence: "NOT_RESEARCHED",
          subject_id: "agency:okcpd",
          predicate_id: "immigration_enforcement_config",
          note: "Rendered as unknown, not omitted (SIG-UI-015).",
        },
      ],
    },
    {
      section_id: "accountability_events",
      rows: [
        { label: "Procurement approval", value: "Approved 2025-03-25 (see authorization block)" },
      ],
    },
    {
      section_id: "timeline",
      rows: [
        { label: "2025-04-03", value: "Executed contract signed", documentUrl: "/v1/claim/contract" },
        { label: "2026-07-15", value: "Transparency-portal snapshot captured", documentUrl: "/v1/claim/portal" },
        { label: "2026-08-20", value: "OpenStreetMap community map reconciled" },
      ],
    },
    {
      // "What we don't know" is rendered from the top-level gap list on the page,
      // the print export, and the API (SIG-UI-011). The section id must be present
      // and in order for validateDossier (SIG-UI-010); its content is the gaps.
      section_id: "what_we_dont_know",
    },
    {
      section_id: "how_we_know_this",
      rows: [
        { label: "Sources", value: "Contract, transparency portal, OSM, council minutes" },
        { label: "Methodology", value: "/methodology/", documentUrl: "/methodology/", note: "See the methodology page for tiers, currency, and reconciliation rules." },
      ],
    },
  ],
};

/** Every dossier the shell statically generates (drives `getStaticPaths`). */
export const DOSSIERS: Dossier[] = [OKC_DOSSIER];
