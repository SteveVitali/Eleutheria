// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * The committed research-dossier fixture (P32.17, SIG-DOS-001/002) — one
 * `sig.research-dossier/1` record inside a `sig.dossier-portfolio/1`, exercising
 * all six answer states so the page contract is demonstrable without the export:
 *   q1/q5/q6 supported · q3 disputed (same-scope conflict) · q4 not_applicable ·
 *   q8 withheld · q10 unknown (documented search + precise follow-up) ·
 *   q11/q12 derived (the mechanical profile/chain answers).
 * Values and digests are fixture-shaped, not real claims — the e2e/unit surface
 * is identical in `fixtures` and `export` modes.
 *
 * P34.22b (B4 G1 R4): this fixture is a hand-authored STAND-IN — every
 * assertion carries `capture_kind: "stand-in"` and NO `retrieved_date`
 * (nothing was ever retrieved); `committed_at` carries this file's real
 * authoring day instead. The `capture` block binds each document_id to the
 * committed bytes it stands in for. `as_of`/`searched_at` are the authoring
 * day, never a fabricated capture date.
 */

import type { ResearchDossier, ResearchDossierPortfolio } from "./research-dossier";

const DIGEST_A = "a1".padEnd(64, "0");
const DIGEST_B = "b2".padEnd(64, "0");
const CAPTURE_OKC = "cap-okc-usage-2026";

/**
 * The stand-in's authoring day (the day these bytes were written into the
 * committed fixture — `date -u` at authoring; the file's own git commit is
 * the same day). The `commit` sha is intentionally absent: a fixture cannot
 * name the commit that introduces it.
 */
const AUTHORED = "2026-10-04";

const STAND_IN_FIXTURE = {
  path: "web/src/lib/research-dossier-fixture.ts",
  commit: null,
  committed_at: AUTHORED,
};

export const RESEARCH_DOSSIER_FIXTURE: ResearchDossier = {
  schema: "sig.research-dossier/1",
  kind: "research_dossier",
  dossier_id: "okc-alpr",
  subject: {
    slug: "okc-alpr",
    label: "Oklahoma City ALPR programme",
    jurisdiction: "Oklahoma City, Oklahoma",
    jurisdiction_slug: "oklahoma-city",
  },
  as_of: { world: AUTHORED, belief: AUTHORED },
  capture: {
    kind: "stand-in",
    live_verification: false,
    anchor: AUTHORED,
    fixtures: {
      "okc-flock-amendment-2026": STAND_IN_FIXTURE,
      "okc-flock-usage-2026": STAND_IN_FIXTURE,
      "okc-council-memo-2026-08": STAND_IN_FIXTURE,
    },
  },
  source_families: ["dossier_admin", "dossier_contracts", "dossier_usage"],
  review_status: "not_run",
  review: { status: "not_run", reviewer_role: "independent semantic reviewer" },
  answers: [
    {
      question: "q1",
      slug: "who-operates",
      title: "Who operates it and under what authority",
      state: "supported",
      score: 3,
      summary:
        "The City of Oklahoma City is the evidenced buyer and Flock Safety the vendor — two distinct actor roles, never collapsed into one 'operator'.",
      assertions: [
        {
          predicate: "buyer",
          value: "City of Oklahoma City",
          scope: {},
          qualifiers: [],
          valid_from: "2026-07-01",
          document_id: "okc-flock-amendment-2026",
          claim_digest: DIGEST_A,
          capture_digest: CAPTURE_OKC,
          source_id: "dossier_contracts",
          source_url: "https://fixture/okc-amendment",
          capture_kind: "stand-in",
          committed_at: AUTHORED,
          locator: { locator: "signature block" },
        },
        {
          predicate: "vendor",
          value: "Flock Safety",
          scope: {},
          qualifiers: [],
          valid_from: "2026-07-01",
          document_id: "okc-flock-amendment-2026",
          claim_digest: DIGEST_B,
          capture_digest: CAPTURE_OKC,
          source_id: "dossier_contracts",
          source_url: "https://fixture/okc-amendment",
          capture_kind: "stand-in",
          committed_at: AUTHORED,
          locator: { locator: "signature block" },
        },
      ],
      follow_ups: [],
    },
    {
      question: "q2",
      slug: "technology-deployed",
      title: "What technology is deployed",
      state: "supported",
      score: 3,
      summary: "Fixed automated license-plate reader cameras on the Flock Safety platform.",
      assertions: [
        {
          predicate: "technology",
          value: "Flock fixed ALPR",
          scope: {},
          qualifiers: [],
          valid_from: "2026-07-01",
          document_id: "okc-flock-usage-2026",
          claim_digest: DIGEST_B,
          capture_digest: CAPTURE_OKC,
          source_id: "dossier_usage",
          source_url: "https://fixture/okc-usage",
          capture_kind: "stand-in",
          committed_at: AUTHORED,
          locator: { locator: "device table" },
        },
      ],
      follow_ups: [],
    },
    {
      question: "q3",
      slug: "owned-inventory",
      title: "Owned inventory and the count universe",
      state: "disputed",
      score: 2,
      summary:
        "Same-scope disagreement: two captured claims give different city_limits device counts — both stay visible, nothing is silently reconciled.",
      assertions: [
        {
          predicate: "claimed_device_count",
          value: 190,
          scope: { count_scope: "city_limits" },
          qualifiers: [{ predicate: "count_scope", value: "city_limits" }],
          document_id: "okc-flock-usage-2026",
          claim_digest: DIGEST_A,
          capture_digest: CAPTURE_OKC,
          source_id: "dossier_usage",
          source_url: "https://fixture/okc-usage",
          capture_kind: "stand-in",
          committed_at: AUTHORED,
          locator: { locator: "device table" },
          conflicting: true,
        },
        {
          predicate: "claimed_device_count",
          value: 299,
          scope: { count_scope: "city_limits" },
          qualifiers: [{ predicate: "count_scope", value: "city_limits" }],
          document_id: "okc-council-memo-2026-08",
          claim_digest: DIGEST_B,
          capture_digest: "cap-okc-memo-2026-08",
          source_id: "dossier_admin",
          source_url: "https://fixture/okc-memo",
          capture_kind: "stand-in",
          committed_at: AUTHORED,
          locator: { locator: "page 2" },
          conflicting: true,
        },
      ],
      follow_ups: [],
    },
    {
      question: "q4",
      slug: "external-access",
      title: "External and hosted-system access",
      state: "not_applicable",
      score: 3,
      summary:
        "Declared not-applicable by the reviewer: the deployment is a standalone local system with no external or hosted data-system relationship to document.",
      assertions: [],
      follow_ups: [],
      declared: {
        rationale:
          "the deployment is a standalone local system with no external/hosted data-system relationship",
      },
    },
    {
      question: "q5",
      slug: "cost-and-expiry",
      title: "Cost, term, and expiry",
      state: "supported",
      score: 3,
      summary: "Contract value 270,000 USD, term effective 2026-07-01.",
      assertions: [
        {
          predicate: "contract_value",
          value: 270000,
          unit: "USD",
          scope: {},
          qualifiers: [],
          valid_from: "2026-07-01",
          document_id: "okc-flock-amendment-2026",
          claim_digest: DIGEST_A,
          capture_digest: CAPTURE_OKC,
          source_id: "dossier_contracts",
          source_url: "https://fixture/okc-amendment",
          capture_kind: "stand-in",
          committed_at: AUTHORED,
          locator: { locator: "payment schedule" },
        },
      ],
      follow_ups: [],
    },
    {
      question: "q6",
      slug: "legal-authority",
      title: "The legal authority cited",
      state: "supported",
      score: 2,
      summary: "OKC Ordinance 26-100 is the cited authority (traceable, scope undated).",
      assertions: [
        {
          predicate: "legal_authority",
          value: "OKC Ordinance 26-100",
          scope: {},
          qualifiers: [],
          document_id: "okc-council-memo-2026-08",
          claim_digest: DIGEST_B,
          capture_digest: "cap-okc-memo-2026-08",
          source_id: "dossier_admin",
          source_url: "https://fixture/okc-memo",
          capture_kind: "stand-in",
          committed_at: AUTHORED,
          locator: { locator: "preamble" },
        },
      ],
      follow_ups: [],
    },
    {
      question: "q7",
      slug: "configuration-retention",
      title: "Configuration and retention",
      state: "supported",
      score: 2,
      summary: "A 7-day retention clause is captured verbatim.",
      assertions: [
        {
          predicate: "retention_period",
          value: "7 days",
          scope: {},
          qualifiers: [],
          document_id: "okc-flock-amendment-2026",
          claim_digest: DIGEST_A,
          capture_digest: CAPTURE_OKC,
          source_id: "dossier_contracts",
          source_url: "https://fixture/okc-amendment",
          capture_kind: "stand-in",
          committed_at: AUTHORED,
          locator: { locator: "clause 4" },
        },
      ],
      follow_ups: [],
    },
    {
      question: "q8",
      slug: "sharing-restrictions",
      title: "Sharing and disclosure restrictions",
      state: "withheld",
      score: 2,
      summary:
        "Declared withheld pending a Part VIII sensitivity review — the ledger keeps the claim digest; the fact itself is not rendered.",
      assertions: [],
      follow_ups: [],
      declared: {
        basis: "Part VIII sensitivity review",
        reason: "the clause's detail is restricted pending rights review",
      },
    },
    {
      question: "q9",
      slug: "timeline",
      title: "Timeline and decision points",
      state: "supported",
      score: 3,
      summary: "The deployment is effective from 2026-07-01.",
      assertions: [
        {
          predicate: "effective_from",
          value: "2026-07-01",
          scope: {},
          qualifiers: [],
          document_id: "okc-flock-amendment-2026",
          claim_digest: DIGEST_B,
          capture_digest: CAPTURE_OKC,
          source_id: "dossier_contracts",
          source_url: "https://fixture/okc-amendment",
          capture_kind: "stand-in",
          committed_at: AUTHORED,
          locator: { locator: "recitals" },
        },
      ],
      follow_ups: [],
    },
    {
      question: "q10",
      slug: "accountability-events",
      title: "Accountability events and oversight",
      state: "unknown",
      score: 1,
      summary:
        `Unknown — SIG searched the council agenda index and the auditor's publication list on ${AUTHORED} and found no oversight event record.`,
      assertions: [],
      search_basis: {
        question: "q10",
        sought: "a council, audit, or oversight record for the deployment",
        sources_searched: ["dossier_admin", "dossier_policy"],
        searched_at: AUTHORED,
        outcome: "searched_not_found",
        note: "recorded search; not a finding that no event occurred",
      },
      follow_ups: [
        {
          question: "q10",
          action: "obtain the council oversight minutes or the clerk's written no-records response",
          next_evidence: "the named minutes document or the clerk's written response",
          closing_condition:
            "a captured document settles the field, or the clerk states in writing that no such record exists",
        },
      ],
    },
    {
      question: "q11",
      slug: "coverage-profile",
      title: "What the evidence covers",
      state: "derived",
      score: 3,
      summary:
        "Derived mechanically: 9 of 10 evidence questions answered (90% coverage profile).",
      assertions: [],
      follow_ups: [],
      declared: { method: "evidence_profile", inputs: [] },
    },
    {
      question: "q12",
      slug: "provenance-chain",
      title: "The provenance chain",
      state: "derived",
      score: 2,
      summary: "Derived mechanically: 3 captured artifacts back the rendered claims.",
      assertions: [],
      follow_ups: [],
      declared: { method: "provenance_chain", inputs: [] },
    },
  ],
  ledger: [
    {
      question: "q1",
      predicate: "buyer",
      fact: "buyer='City of Oklahoma City'",
      claim_digest: DIGEST_A,
      capture_digest: CAPTURE_OKC,
      locator: { locator: "signature block" },
      source_url: "https://fixture/okc-amendment",
      capture_kind: "stand-in",
      committed_at: AUTHORED,
      state: "rendered",
    },
    {
      question: "q3",
      predicate: "claimed_device_count",
      fact: "claimed_device_count=190",
      claim_digest: DIGEST_A,
      capture_digest: CAPTURE_OKC,
      locator: { locator: "device table" },
      source_url: "https://fixture/okc-usage",
      capture_kind: "stand-in",
      committed_at: AUTHORED,
      state: "rendered",
    },
    {
      question: "q3",
      predicate: "claimed_device_count",
      fact: "claimed_device_count=299",
      claim_digest: DIGEST_B,
      capture_digest: "cap-okc-memo-2026-08",
      locator: { locator: "page 2" },
      source_url: "https://fixture/okc-memo",
      capture_kind: "stand-in",
      committed_at: AUTHORED,
      state: "rendered",
    },
    {
      question: "q8",
      predicate: "sharing_restriction",
      fact: "(withheld)",
      claim_digest: DIGEST_B,
      capture_digest: null,
      locator: null,
      source_url: null,
      retrieved_date: null,
      state: "withheld",
    },
  ],
  search_log: [
    {
      question: "q10",
      sought: "a council, audit, or oversight record for the deployment",
      sources_searched: ["dossier_admin", "dossier_policy"],
      searched_at: AUTHORED,
      outcome: "searched_not_found",
      note: "recorded search",
    },
  ],
  checklist: [
    { item: "all_twelve_questions_present", status: "pass", detail: "12/12 questions represented" },
    { item: "states_legal", status: "pass", detail: "every answer carries a legal state" },
    {
      item: "affirmatives_evidence_backed",
      status: "pass",
      detail: "every rendered assertion cites a claim digest + capture digest + locator",
    },
    {
      item: "search_log_complete",
      status: "pass",
      detail: "every unknown carries a documented search basis",
    },
    {
      item: "same_scope_conflicts_visible",
      status: "pass",
      detail: "same-scope disagreements render as disputed",
    },
    {
      item: "instrument_genre_classified",
      status: "pass",
      detail: "no template asserts an executed-instrument predicate",
    },
    {
      item: "independent_semantic_review",
      status: "fail",
      detail: "recorded status: not_run (the review mark is never fabricated)",
    },
    { item: "rubric_threshold", status: "fail", detail: "total 26/36 below the 28 gate" },
    { item: "no_unsupported_claims", status: "pass", detail: "0 release violations" },
  ],
  completeness: {
    total: 26,
    max: 36,
    required_minimum: { q1: 2, q5: 2, q7: 2, q8: 2 },
    per_question: {
      q1: 3, q2: 3, q3: 2, q4: 3, q5: 3, q6: 2, q7: 2, q8: 2, q9: 3, q10: 1, q11: 2, q12: 0,
    },
    mechanical_complete: false,
    pilot_complete: false,
    blocking: [
      "rubric_total 26/36 below 28",
      "independent_review not_run (a completed review is required)",
    ],
  },
  decision_windows: {
    windows: [
      {
        predicate: "effective_from",
        value: "2026-07-01",
        valid_from: "2026-07-01",
        document_id: "okc-flock-amendment-2026",
      },
    ],
    next_decision_date: null,
  },
  what_we_dont_know: [
    {
      question: "q10",
      title: "Accountability events and oversight",
      detail: `searched_not_found — dossier_admin, dossier_policy (searched ${AUTHORED})`,
    },
  ],
  release: { valid: true, violations: [] },
};

export const RESEARCH_PORTFOLIO_FIXTURE: ResearchDossierPortfolio = {
  schema: "sig.dossier-portfolio/1",
  dossiers: [RESEARCH_DOSSIER_FIXTURE],
  summary: {
    dossier_count: 1,
    pilot_complete: 0,
    mechanical_complete: 0,
    release_invalid: 0,
  },
};
