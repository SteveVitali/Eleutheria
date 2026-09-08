// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * Committed fixtures for the P15.4 renewal watch (§39.5), evidence recommender
 * (§39.5a), and evidence viewer (§39.6). Static-first (SIG-UI-036): the surfaces read
 * these typed fixtures at build time, not a live API. Everything keys to the same
 * worked Oklahoma City case the rest of the shell renders — the 42-vs-38 contested
 * device count and the Appendix-D auto-renewal contract (expiry 2027-04-02, 90-day
 * notice → decision date 2027-01-02), so the watch, the recommender, and the viewer
 * all speak about the same jurisdiction the dossier does.
 */

import { beliefPinnedPermalink } from "./citation";
import { AS_OF, DEVICE_COUNT_CLAIMS, RULESET_VERSION } from "./fixtures";
import { evidencePath } from "./evidence-viewer";
import type { Capture, ClaimView } from "./evidence-viewer";
import type { ContractWatchItem } from "./watch";
import type { DecisionPoint, EvidenceArtifact } from "./recommender";

// --- The renewal watch (SIG-UI-026/027) --------------------------------------

/**
 * Contracts on the watch, spanning the honest cases: the Appendix-D OKC auto-renewal
 * contract (its decision date is the notice deadline, not the expiry), a contested
 * OKC contract, and a non-auto-renewing Tulsa contract (so the watch spans two
 * jurisdictions and both subscription feeds are non-empty). Timing is DERIVED from
 * the raw termination inputs via the P15.2 wire contract — never a stored decision
 * date (SIG-UI-014b).
 */
export const WATCH_ITEMS: ContractWatchItem[] = [
  {
    contract_id: "contract:okcpd-alpr",
    subject_label: "OKCPD ALPR deployment (Flock Safety)",
    jurisdiction: "Oklahoma City",
    termination: { auto_renews: true, notice_window_days: 90, expiry_date: "2027-04-02" },
    renewal_window_days: 90,
    approving_body: "Oklahoma City Council",
    next_scheduled_meeting: "2026-12-16",
    replacement_procurement: null,
    contested: true,
  },
  {
    contract_id: "contract:okcpd-rtcc",
    subject_label: "OKC Real-Time Crime Center integration",
    jurisdiction: "Oklahoma City",
    termination: { auto_renews: false, notice_window_days: null, expiry_date: "2026-11-30" },
    renewal_window_days: null,
    approving_body: "Oklahoma City Council",
    next_scheduled_meeting: "2026-11-18",
    replacement_procurement: "RFP-2026-RTCC-002 (successor solicitation, published 2026-09-01)",
    contested: false,
  },
  {
    contract_id: "contract:tulsa-alpr",
    subject_label: "Tulsa PD ALPR pilot",
    jurisdiction: "Tulsa",
    termination: { auto_renews: true, notice_window_days: 60, expiry_date: "2027-02-15" },
    renewal_window_days: 60,
    approving_body: "Tulsa City Council",
    next_scheduled_meeting: "2026-12-09",
    replacement_procurement: null,
    contested: false,
  },
];

// --- The evidence recommender (SIG-UI-027a/b/c) ------------------------------

/** The upcoming decision the recommender ranks evidence for — the OKC renewal. */
export const DECISION_POINT: DecisionPoint = {
  decision_type: "renewal",
  subject_id: "agency:okcpd",
  label: "OKCPD ALPR contract renewal (Flock Safety)",
  date: "2027-01-02",
};

const permalinkFor = (claimId: string, asOf: string): string =>
  beliefPinnedPermalink({
    path: evidencePath(claimId),
    title: claimId,
    asOf: { ...AS_OF, as_of_world: asOf, as_of_belief: asOf },
    rulesetVersion: RULESET_VERSION,
  });

/**
 * The evidence artifacts available for the renewal decision. Deliberately spans every
 * ranking axis: directness D1..D6 (the D6 vendor brochure is non-probative and
 * excluded), currency C1..C3, retrievable vs paywalled vs link-rotted captures,
 * artifact-type relevance (a contract + amendment rank first for a renewal), and both
 * dispute-status boosts (an open contradiction, an open task). NONE carries a
 * persuasiveness / sentiment / vote-effect field — the neutrality guard (SIG-UI-027b).
 */
export const EVIDENCE_ARTIFACTS: EvidenceArtifact[] = [
  {
    artifact_id: "contract:okcpd-alpr",
    subject_id: "agency:okcpd",
    title: "Executed OKCPD–Flock ALPR procurement contract",
    source: "Public records request (city procurement)",
    artifact_type: "contract",
    directness: "D1",
    currency: "C1",
    touches_open_contradiction: true,
    answers_open_task: false,
    capture_status: "retrievable",
    permalink: permalinkFor("contract-okcpd-alpr", "2026-07-01"),
    as_of: "2026-07-01",
  },
  {
    artifact_id: "amendment:okcpd-alpr-1",
    subject_id: "agency:okcpd",
    title: "Amendment 1 — device-count and price adjustment",
    source: "Public records request (city procurement)",
    artifact_type: "amendment",
    directness: "D1",
    currency: "C1",
    touches_open_contradiction: false,
    answers_open_task: false,
    capture_status: "retrievable",
    permalink: permalinkFor("amendment-okcpd-alpr-1", "2026-07-01"),
    as_of: "2026-07-01",
  },
  {
    artifact_id: "snapshot:portal-2026-08",
    subject_id: "agency:okcpd",
    title: "Eyes on Flock portal snapshot (August)",
    source: "Eyes on Flock portal aggregator",
    artifact_type: "portal_snapshot",
    directness: "D2",
    currency: "C1",
    touches_open_contradiction: true,
    answers_open_task: false,
    capture_status: "retrievable",
    permalink: permalinkFor("snapshot-portal-2026-08", "2026-08-01"),
    as_of: "2026-08-01",
  },
  {
    artifact_id: "invoice:okcpd-2026q2",
    subject_id: "agency:okcpd",
    title: "Q2 2026 vendor invoice",
    source: "Public records request (finance)",
    artifact_type: "invoice",
    directness: "D2",
    currency: "C2",
    touches_open_contradiction: false,
    answers_open_task: true,
    capture_status: "retrievable",
    permalink: permalinkFor("invoice-okcpd-2026q2", "2026-07-15"),
    as_of: "2026-07-15",
  },
  {
    artifact_id: "minutes:council-2025-03-25",
    subject_id: "agency:okcpd",
    title: "City Council minutes — procurement approval",
    source: "Oklahoma City Council minutes",
    artifact_type: "meeting_minutes",
    directness: "D3",
    currency: "C3",
    touches_open_contradiction: false,
    answers_open_task: false,
    capture_status: "retrievable",
    permalink: permalinkFor("minutes-council-2025-03-25", "2025-03-25"),
    as_of: "2025-03-25",
  },
  {
    artifact_id: "news:paywalled-2026-08",
    subject_id: "agency:okcpd",
    title: "Local newspaper report on the ALPR program",
    source: "Regional newspaper (paywalled archive)",
    artifact_type: "news_article",
    directness: "D3",
    currency: "C1",
    touches_open_contradiction: false,
    answers_open_task: true,
    capture_status: "paywalled",
    permalink: permalinkFor("news-paywalled-2026-08", "2026-08-10"),
    as_of: "2026-08-10",
  },
  {
    artifact_id: "portal:rotted-2025",
    subject_id: "agency:okcpd",
    title: "Vendor transparency page (no longer retrievable)",
    source: "Flock transparency portal",
    artifact_type: "portal_snapshot",
    directness: "D2",
    currency: "C4",
    touches_open_contradiction: false,
    answers_open_task: false,
    capture_status: "link_rotted",
    permalink: permalinkFor("portal-rotted-2025", "2025-05-01"),
    as_of: "2025-05-01",
  },
  {
    artifact_id: "brochure:flock-marketing",
    subject_id: "agency:okcpd",
    title: "Flock Safety marketing brochure",
    source: "Vendor marketing",
    artifact_type: "vendor_brochure",
    // D6 is non-probative (§10.5) — excluded from the ranking entirely.
    directness: "D6",
    currency: "C2",
    touches_open_contradiction: false,
    answers_open_task: false,
    capture_status: "retrievable",
    permalink: permalinkFor("brochure-flock-marketing", "2026-01-01"),
    as_of: "2026-01-01",
  },
];

// --- The evidence viewer (SIG-UI-028/029/030) --------------------------------

/** The executed-contract document text; the span highlights the device-count clause. */
const CONTRACT_TEXT =
  "MASTER AGREEMENT for automated licence-plate reader services. " +
  "Vendor shall provide and maintain forty-two (42) fixed ALPR camera units within the City, " +
  "together with one Real-Time Crime Center integration hub. This Agreement expires 2027-04-02 " +
  "and renews automatically for successive one-year terms unless either party gives written " +
  "notice not less than ninety (90) days before expiry.";

const DEVICE_SPAN_TEXT = "forty-two (42)";
const deviceSpanStart = CONTRACT_TEXT.indexOf(DEVICE_SPAN_TEXT);
const DEVICE_SPAN = { start: deviceSpanStart, end: deviceSpanStart + DEVICE_SPAN_TEXT.length };

/** The public executed-contract capture whose span supports the 42 device count. */
export const CONTRACT_CAPTURE: Capture = {
  capture_id: "capture:contract-okcpd-alpr-v1",
  artifact_id: "contract:okcpd-alpr",
  storage_tier: "public",
  captured_at: "2026-07-01",
  content_digest: "sha256:ab12cd34ef56ab12cd34ef56ab12cd34ef56ab12cd34ef56ab12cd34ef56ab12",
  acquisition_method: "records_request_pdf",
  document_text: CONTRACT_TEXT,
  fields: { active_device_count: 42, expiry_date: "2027-04-02", notice_window_days: 90 },
};

/** The evidence view of the contested active-device-count claim (SIG-UI-028). */
export const DEVICE_COUNT_CLAIM_VIEW: ClaimView = {
  claim_id: "active-device-count",
  claim_label: "Active device count",
  value: 42,
  capture: CONTRACT_CAPTURE,
  locator: {
    kind: "char_range",
    description: "Master agreement, service-scope clause",
    span: DEVICE_SPAN,
  },
  extraction_method: "table/clause extraction (parsing layer L3)",
  extraction_version: "parser-2026.06",
  review_status: "curator_reviewed",
  // The 42-vs-38 contradiction is preserved and stays visible (SIG-UI-008/009).
  conflicting_claims: DEVICE_COUNT_CLAIMS,
  history: [
    { asserted_at: "2026-07-02", event: "asserted", value: 42, note: "From the executed contract (W3)." },
    { asserted_at: "2026-07-02", event: "asserted", value: 38, note: "From the portal snapshot (W2); dissenting." },
    { asserted_at: "2026-08-20", event: "corrected", value: 42, note: "Reaffirmed after portal reconciliation; dissent retained." },
  ],
};

/** A sealed capture: bytes withheld, metadata-only public representation (SIG-UI-030). */
export const SEALED_CAPTURE: Capture = {
  capture_id: "capture:sealed-roster-v1",
  artifact_id: "record:okcpd-operator-roster",
  storage_tier: "sealed",
  captured_at: "2026-05-12",
  content_digest: "sha256:99ff88ee77dd66cc55bb44aa3399ff88ee77dd66cc55bb44aa3399ff88ee77dd",
  acquisition_method: "records_request_pdf",
  sealed_reason:
    "Contains unredacted personally-identifying information about individual officers under a " +
    "sealed-records hold; SIG holds the bytes but must not publish them (§17.5).",
  fields: { operator_count: 17 },
};

/** The evidence view resting on the sealed capture — rendered metadata-only (SIG-UI-030). */
export const SEALED_CLAIM_VIEW: ClaimView = {
  claim_id: "operator-roster-size",
  claim_label: "Authorized operator count",
  value: 17,
  capture: SEALED_CAPTURE,
  locator: {
    kind: "page",
    description: "Roster appendix (sealed)",
    span: { start: 0, end: 1 },
  },
  extraction_method: "manual curator extraction",
  extraction_version: "manual-2026.05",
  review_status: "curator_reviewed",
  conflicting_claims: [],
  history: [{ asserted_at: "2026-05-12", event: "asserted", value: 17, note: "From the sealed roster record." }],
};

/** Every claim the evidence viewer statically generates (drives `getStaticPaths`). */
export const CLAIM_VIEWS: ClaimView[] = [DEVICE_COUNT_CLAIM_VIEW, SEALED_CLAIM_VIEW];

// --- Capture diffing (SIG-UI-029, §29.7) -------------------------------------

/** The June portal capture of the OKCPD portal artifact (for the field-by-field diff). */
export const PORTAL_CAPTURE_JUNE: Capture = {
  capture_id: "capture:portal-okcpd-2026-06",
  artifact_id: "artifact:okcpd-portal",
  storage_tier: "public",
  captured_at: "2026-06-01",
  content_digest: "sha256:1111222233334444555566667777888899990000aaaabbbbccccddddeeeeffff",
  acquisition_method: "http_get",
  document_text: "OKCPD transparency portal — as captured 2026-06-01. Active devices: 40. Retention: 30 days.",
  fields: { active_device_count: 40, retention_days: 30, network_partners: 142 },
};

/** The August portal capture of the same artifact — "what changed between June and August". */
export const PORTAL_CAPTURE_AUGUST: Capture = {
  capture_id: "capture:portal-okcpd-2026-08",
  artifact_id: "artifact:okcpd-portal",
  storage_tier: "public",
  captured_at: "2026-08-01",
  content_digest: "sha256:aaaa1111bbbb2222cccc3333dddd4444eeee5555ffff66667777888899990000",
  acquisition_method: "http_get",
  document_text: "OKCPD transparency portal — as captured 2026-08-01. Active devices: 38. Retention: 30 days.",
  fields: { active_device_count: 38, retention_days: 30, network_partners: 147 },
};

/** The two captures the viewer diffs field-by-field (SIG-UI-029). */
export const DIFF_CAPTURES: [Capture, Capture] = [PORTAL_CAPTURE_JUNE, PORTAL_CAPTURE_AUGUST];
