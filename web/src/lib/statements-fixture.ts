// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * Committed `sig.statement/1` fixtures (P35.36, R11-K13-TX-08a / J3 §5.1–5.2,
 * SIG-TRANSP-011) — the statements rows the shared `<ProvenancePanel>`
 * contract normalises in `fixtures` data mode.
 *
 * They key to the SAME worked Oklahoma City case the rest of the shell
 * renders: the two evidence-viewer claims (`active-device-count`,
 * `operator-roster-size` — `watch-evidence-fixture.ts`'s CLAIM_VIEWS) and the
 * named supporting claims the network fixtures list (`claim:…` ids in
 * `map-network-fixture.ts`). Between them they exercise every J3 §5.1 binding
 * state verbatim — `actual_capture`, `replayed`, `document_only`,
 * `legacy_synthetic` — while the claims left OUT of the fixture index
 * exercise the honest fifth state (`not_recorded`) on every surface that
 * names them.
 */

import type { StatementRow } from "./provenance-panel";

/** The executed-contract claim — `actual_capture` (the records-request PDF
 *  capture backs it; the S-6 gate published the full upstream URL). */
const DEVICE_COUNT_STATEMENT: StatementRow = {
  schema: "sig.statement/1",
  claim_id: "active-device-count",
  entity_id: "deployment:okcpd-alpr",
  predicate_id: "active_device_count",
  observed_at: "2026-07-01",
  source_id: "src:okc-procurement",
  value: "not_published",
  binding_status: "actual_capture",
  binding_role: "establishes",
  lane: "raw-ok",
  capture: {
    capture_id: "capture:contract-okcpd-alpr-v1",
    artifact_id: "contract:okcpd-alpr",
    retrieved_at: "2026-07-01T14:22:00Z",
    digest:
      "sha256:ab12cd34ef56ab12cd34ef56ab12cd34ef56ab12cd34ef56ab12cd34ef56ab12",
    byte_size: 412_700,
    media_type: "application/pdf",
    storage_tier: "public",
    run_id: "run:capture-2026-07-01",
    bound_at: "2026-07-02T09:00:00Z",
  },
  upstream: {
    status: "full_url",
    url: "https://records.example.gov/okcpd/alpr-contract.pdf",
    host: "records.example.gov",
    path_sha256: null,
  },
  view_original: {
    kind: "download_original",
    label: "Download original",
    href: null,
    note: null,
  },
  extraction: {
    method: "table/clause extraction (parsing layer L3)",
    extractor_name: "parsing",
    extractor_version: "parser-2026.06",
    review_status: "curator_reviewed",
  },
  epistemics: {
    directness: "D1",
    reliability: "W3",
    integrity: "I1",
    review_status: "curator_reviewed",
  },
  recorded: { run_id: "run:ingest-2026-07-02", at: "2026-07-02T09:05:00Z" },
  supersession: {
    revises_claim: null,
    retraction_of: null,
    prior_recorded_at: null,
  },
  contradictions: {
    contradiction_ids: ["contra:device-count-42-38"],
    competing_claim_ids: ["portal"],
  },
  rights: {
    spdx: "CC-BY-4.0",
    attribution: "Oklahoma City procurement records",
    compartment: "sig_graph",
  },
};

/** The sealed-roster claim — `document_only`: extracted from a records-
 *  request document; no page capture exists to show (the sealed capture's
 *  bytes stay withheld — the panel says what is recorded, never what it is
 *  not). */
const ROSTER_STATEMENT: StatementRow = {
  schema: "sig.statement/1",
  claim_id: "operator-roster-size",
  entity_id: "deployment:okcpd-rtcc",
  predicate_id: "authorized_operator_count",
  observed_at: "2026-05-12",
  source_id: "src:okc-records",
  value: "not_published",
  binding_status: "document_only",
  lane: "derived-only",
  capture: null,
  upstream: {
    status: "no_upstream_url_recorded",
    url: null,
    host: null,
    path_sha256: null,
  },
  view_original: {
    kind: "view_at_source",
    label: "View at source",
    href: null,
    note: null,
  },
  extraction: {
    method: "manual curator extraction",
    extractor_name: "manual",
    extractor_version: "manual-2026.05",
    review_status: "curator_reviewed",
  },
  epistemics: {
    directness: "D2",
    reliability: "W2",
    integrity: "I2",
    review_status: "curator_reviewed",
  },
  recorded: { run_id: "run:ingest-2026-05-12", at: "2026-05-12T16:40:00Z" },
  supersession: {
    revises_claim: null,
    retraction_of: null,
    prior_recorded_at: null,
  },
  contradictions: { contradiction_ids: [], competing_claim_ids: [] },
  rights: {
    spdx: "CC-BY-4.0",
    attribution: "Oklahoma City records response",
    compartment: "sig_graph",
  },
};

/** The RTCC MOU edge claim — `legacy_synthetic`: J3 §5.1's run-level sentence
 *  (every claim today is one, G-6). The wording itself states SIG did NOT keep
 *  a per-record copy — the honesty IS the run-level text. */
const MOU_STATEMENT: StatementRow = {
  schema: "sig.statement/1",
  claim_id: "claim:okc-rtcc-mou",
  entity_id: "edge:okcpd-rtcc",
  predicate_id: "declared_sharing_policy",
  observed_at: "2026-03-01",
  source_id: "src:okc-council-minutes",
  value: "not_published",
  binding_status: "legacy_synthetic",
  lane: "link-only",
  capture: null,
  upstream: {
    status: "host_only",
    url: null,
    host: "minutes.example.gov",
    path_sha256: "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08",
  },
  view_original: {
    kind: "view_at_source",
    label: "View at source",
    href: "https://minutes.example.gov/",
    note: null,
  },
  extraction: null,
  epistemics: {
    directness: "D3",
    reliability: "W2",
    integrity: "I3",
    review_status: "unreviewed",
  },
  recorded: { run_id: "run:registry-import-14", at: "2026-03-04T11:00:00Z" },
  supersession: {
    revises_claim: null,
    retraction_of: null,
    prior_recorded_at: null,
  },
  contradictions: { contradiction_ids: [], competing_claim_ids: [] },
  rights: {
    spdx: "CC-BY-4.0",
    attribution: "Oklahoma City Council minutes",
    compartment: "sig_graph",
  },
};

/** The RTCC config-screenshot claim — `replayed`: re-derived on a later run
 *  from a capture made earlier. */
const SCREENSHOT_STATEMENT: StatementRow = {
  schema: "sig.statement/1",
  claim_id: "claim:rtcc-config-screenshot",
  entity_id: "edge:okcpd-rtcc",
  predicate_id: "configured_access",
  observed_at: "2026-03-15",
  source_id: "src:okc-rtcc-docs",
  value: "not_published",
  binding_status: "replayed",
  lane: "derived-only",
  capture: {
    capture_id: "capture:rtcc-config-2026-03",
    artifact_id: "artifact:rtcc-config-screenshot",
    retrieved_at: "2026-03-01T08:12:00Z",
    digest:
      "sha256:1111222233334444555566667777888899990000aaaabbbbccccddddeeeeffff",
    byte_size: 98_410,
    media_type: "image/png",
    storage_tier: "restricted",
    run_id: "run:capture-2026-03-01",
    bound_at: "2026-04-02T10:30:00Z",
  },
  upstream: {
    status: "no_upstream_url_recorded",
    url: null,
    host: null,
    path_sha256: null,
  },
  view_original: {
    kind: "view_at_source",
    label: "View at source",
    href: null,
    note: null,
  },
  extraction: {
    method: "structured_parse",
    extractor_name: "screenshot-fields",
    extractor_version: "1.4",
    review_status: "unreviewed",
  },
  epistemics: {
    directness: "D2",
    reliability: "W2",
    integrity: "I2",
    review_status: "unreviewed",
  },
  recorded: { run_id: "run:replay-2026-04-02", at: "2026-04-02T10:31:00Z" },
  supersession: {
    revises_claim: null,
    retraction_of: null,
    prior_recorded_at: null,
  },
  contradictions: { contradiction_ids: [], competing_claim_ids: [] },
  rights: {
    spdx: "CC-BY-4.0",
    attribution: "OKC RTCC configuration document",
    compartment: "sig_graph",
  },
};

/** The `claim_id → sig.statement/1` fixture index — mirrors the export's
 *  per-compartment `statements.jsonl` files (fixtures mode's single
 *  `sig_graph` compartment). Claims absent from the index render the
 *  `not_recorded` panel — honest absence, exercised on every surface. */
export const STATEMENT_FIXTURES: StatementRow[] = [
  DEVICE_COUNT_STATEMENT,
  ROSTER_STATEMENT,
  MOU_STATEMENT,
  SCREENSHOT_STATEMENT,
];
