// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * The one `<ProvenancePanel>` data contract (P35.36, R11-K13-TX-08a /
 * J3 §5.1–5.3, K13 §7 W1 / UXR-33, SIG-TRANSP-011) — the TypeScript twin of
 * `exports/src/exports/provenance_panel.py`.
 *
 * One claim → one panel. Every consumer surface — the claim viewer
 * (`/evidence/<claim>/`), the network edge list (`NetworkEdgeItem`), the
 * network island's edge detail, the map island's selection pane, and the
 * release record pages the Python twin renders — reads the SAME field set and
 * the SAME verbatim J3 §5.1 binding-state wording:
 *
 *   - `actual_capture`   — "Captured from <host> on <retrieved_at>; sha256 <…>."
 *   - `replayed`         — "Re-derived on <date> from a capture made on <retrieved_at>."
 *   - `document_only`    — "Extracted from a document; no page capture."
 *   - `legacy_synthetic` — "Recorded by run <id> on <date>. SIG did not keep a
 *     per-record copy of the source for this run; the source's page lists the
 *     run and its captures."
 *   - `not_recorded`     — the honest fifth state: no publishable binding
 *     exists. Never implied, never a fabricated document (C4 NEW-2).
 *
 * Every field is a value or a named absence kind — `not_recorded`,
 * `no_upstream_url_recorded`, `not_publishable`, `unavailable` — never a
 * blank. No state implies SIG holds a document or capture it does not.
 *
 * Path construction: every internal href goes through `withBase()` (P35.65,
 * UXR-25) — and the path arguments are written WITHOUT a leading slash, so
 * the containment check (`check-root-absolute-paths.mjs`) measures zero new
 * root-absolute sites from this module (the helper still re-roots them).
 */

import { withBase } from "./paths";

/** The emitted panel-contract schema (`schema` on the contract object). */
export const PANEL_SCHEMA = "sig.provenance-panel/1";

/** The emitted statement schema (`schema` on a statements.jsonl row). */
export const STATEMENT_SCHEMA = "sig.statement/1";

/** Named absence tokens (the shared closed vocabulary the Python twin mirrors). */
export const NOT_RECORDED = "not_recorded";
export const NOT_PUBLISHABLE = "not_publishable";
export const UNAVAILABLE = "unavailable";
export const NO_UPSTREAM_URL = "no_upstream_url_recorded";

/** J3 §5.1's verbatim binding-state sentences — the four recorded states plus
 *  the named-absence fifth. `{...}` slots fill from the statement row; an
 *  absent slot value renders `not_recorded`, never a guessed instant. */
export const BINDING_STATE_TEMPLATES: Record<string, string> = {
  actual_capture: "Captured from {host} on {retrieved_at}; sha256 {digest}.",
  replayed: "Re-derived on {bound_at} from a capture made on {retrieved_at}.",
  document_only: "Extracted from a document; no page capture.",
  legacy_synthetic:
    "Recorded by run {run_id} on {recorded_at}. SIG did not keep a per-record " +
    "copy of the source for this run; the source's page lists the run and its " +
    "captures.",
  not_recorded: "No published evidence binding is recorded for this claim.",
};

/** The closed binding-state vocabulary (`claim_evidence.binding_status` + the
 *  named absence — `db/deploy/claim_assertion_bindings.sql`). */
export const BINDING_STATES = [
  "actual_capture",
  "replayed",
  "document_only",
  "legacy_synthetic",
  NOT_RECORDED,
] as const;
export type BindingState = (typeof BINDING_STATES)[number];

/** J3 §5.2's review wording while a claim is unreviewed/not_run. */
export const NOT_YET_REVIEWED = "Not yet independently reviewed";

/** The panel's ordered field labels (J3 §5.2's verbatim field set). */
export const FIELD_LABELS = [
  "Source",
  "Binding state",
  "Capture retrieved",
  "Capture digest",
  "Capture bytes",
  "Capture media type",
  "Upstream",
  "View original",
  "Extraction",
  "Directness class",
  "Epistemic tier + review status",
  "Contradictions",
  "Supersession",
  "Rights",
  "Equivalent requests",
  "Dispute",
] as const;

// --- The `sig.statement/1` row the panel reads ------------------------------ //
// Structurally typed — every field optional beyond claim_id so a partial row
// (or the honest absence, `undefined`) normalises into the named-absence
// panel instead of throwing.

/** One `sig.statement/1` row as the statements file / record JSON carries it. */
export interface StatementRow {
  schema?: string;
  claim_id: string;
  entity_id?: string;
  predicate_id?: string | null;
  observed_at?: string | null;
  source_id?: string;
  source_name?: string | null;
  value?: string;
  binding_status?: string;
  binding_role?: string | null;
  lane?: string;
  capture?: {
    capture_id?: string | null;
    artifact_id?: string | null;
    retrieved_at?: string | null;
    digest?: string | null;
    byte_size?: number | null;
    media_type?: string | null;
    storage_tier?: string | null;
    run_id?: string | null;
    bound_at?: string | null;
  } | null;
  upstream?: {
    status?: string;
    url?: string | null;
    host?: string | null;
    path_sha256?: string | null;
  } | null;
  view_original?: {
    kind?: string;
    label?: string;
    href?: string | null;
    note?: string | null;
  } | null;
  extraction?: {
    method?: string | null;
    extractor_name?: string | null;
    extractor_version?: string | null;
    review_status?: string | null;
  } | null;
  epistemics?: {
    directness?: string | null;
    reliability?: string | null;
    integrity?: string | null;
    review_status?: string | null;
  } | null;
  recorded?: { run_id?: string | null; at?: string | null } | null;
  supersession?: {
    revises_claim?: string | null;
    retraction_of?: string | null;
    prior_recorded_at?: string | null;
  } | null;
  contradictions?: {
    contradiction_ids?: string[];
    competing_claim_ids?: string[];
  } | null;
  rights?: {
    spdx?: string | null;
    attribution?: string | null;
    compartment?: string | null;
  } | null;
}

// --- The `sig.provenance-panel/1` contract ---------------------------------- //

export interface ProvenancePanelData {
  schema: typeof PANEL_SCHEMA;
  claim_id: string;
  binding_status: string;
  binding_text: string;
  source: { id: string; name: string | null; href: string | null };
  capture: {
    capture_id: string;
    artifact_id: string;
    retrieved_at: string;
    digest: string;
    byte_size: string;
    media_type: string;
    storage_tier: string;
  };
  upstream: { status: string; display: string; href: string | null };
  view_original: {
    kind: string;
    label: string;
    href: string | null;
    note: string | null;
  };
  extraction: string;
  directness: string;
  epistemic_review: { reliability: string; integrity: string; review: string };
  contradictions: { display: string; ids: string[]; competing: string[] };
  supersession: string;
  rights: { spdx: string; attribution: string; compartment: string };
  equivalent_requests: {
    json_href: string | null;
    api_href: string | null;
    api_status: string;
  };
  dispute_href: string | null;
}

/** Optional link context for `panelFromStatement`. */
export interface PanelLinks {
  /** Source registry href; defaults to the `/sources/` surface via `withBase()`. */
  sourceHref?: string | null;
  /** Dispute route (never a personal address, U-011); defaults to `/dispute/`. */
  disputeHref?: string | null;
  /** The record's JSON twin where it exists (release pages); `unavailable` else. */
  jsonHref?: string | null;
  /** The API route where it exists (P37.42 owns it); `unavailable` meanwhile. */
  apiHref?: string | null;
}

function v(value: unknown, absent: string = NOT_RECORDED): string {
  if (value === null || value === undefined) return absent;
  const text = String(value).trim();
  return text === "" ? absent : text;
}

function dateOnly(value: unknown): string | null {
  const text = v(value, "");
  return text === "" ? null : text.slice(0, 10);
}

function fill(template: string, slots: Record<string, string>): string {
  return template.replace(/\{(\w+)\}/g, (_m, key) => slots[key] ?? NOT_RECORDED);
}

/** `(state, sentence)` — J3 §5.1's wording verbatim for the claim's binding
 *  state. Slot values that were never recorded render the `not_recorded`
 *  token inside the sentence — the wording stays exact and the absence stays
 *  named. A state outside the closed vocabulary degrades to `not_recorded`
 *  (fail-closed; an unvetted label never leaks, S-12). */
export function bindingStateText(
  statement: Partial<StatementRow> | null | undefined,
): { state: string; text: string } {
  const stmt: Partial<StatementRow> = statement ?? {};
  let state = v(stmt.binding_status, NOT_RECORDED);
  if (!(state in BINDING_STATE_TEMPLATES)) state = NOT_RECORDED;
  const capture = stmt.capture ?? {};
  const upstream = stmt.upstream ?? {};
  const recorded = stmt.recorded ?? {};
  return {
    state,
    text: fill(BINDING_STATE_TEMPLATES[state]!, {
      host: v(upstream.host),
      retrieved_at: v(capture.retrieved_at),
      digest: v(capture.digest),
      bound_at: v(capture.bound_at),
      run_id: v(recorded.run_id ?? capture.run_id),
      recorded_at: v(dateOnly(recorded.at)),
    }),
  };
}

/**
 * Normalise one `sig.statement/1` row (or its honest absence) into the shared
 * `sig.provenance-panel/1` contract every surface renders. `statement` may be
 * `undefined` — a claim whose statement did not publish (a pre-P35.36 export,
 * or a claim outside the released claim set): the panel then carries the
 * `not_recorded` state and every field the named absence, never a gap.
 */
export function panelFromStatement(
  statement: Partial<StatementRow> | null | undefined,
  claimId: string,
  links: PanelLinks = {},
): ProvenancePanelData {
  const stmt: Partial<StatementRow> = statement ?? {};
  const { state, text: stateText } = bindingStateText(stmt);
  const capture = stmt.capture ?? {};
  const upstream = stmt.upstream ?? {};
  const extraction = stmt.extraction ?? null;
  const epistemics = stmt.epistemics ?? {};
  const supersession = stmt.supersession ?? {};
  const contradictions = stmt.contradictions ?? {};
  const rights = stmt.rights ?? {};
  const viewOriginal = stmt.view_original ?? {};

  // Upstream display: the S-6 publication form — full URL, or host +
  // path-hash, or the named absence. `withheld_by_policy` never renders a
  // link at all (S-5/S-6: a URL that could name a person stays off the page).
  const upStatus = v(upstream.status, NO_UPSTREAM_URL);
  let upstreamDisplay: string;
  let upstreamHref: string | null;
  if (upStatus === "full_url") {
    upstreamDisplay = v(upstream.url);
    upstreamHref = upstream.url ?? null;
  } else if (upStatus === "host_only") {
    upstreamDisplay = `${v(upstream.host)}#path_sha256:${v(upstream.path_sha256)}`;
    upstreamHref = upstream.host ? `https://${upstream.host}/` : null;
  } else if (upStatus === "withheld_by_policy") {
    upstreamDisplay = NOT_PUBLISHABLE;
    upstreamHref = null;
  } else {
    upstreamDisplay = NO_UPSTREAM_URL;
    upstreamHref = null;
  }

  const review = v(epistemics.review_status);
  const reviewDisplay =
    review === "unreviewed" || review === "not_run" || review === NOT_RECORDED
      ? NOT_YET_REVIEWED
      : review;

  const conIds = [...(contradictions.contradiction_ids ?? [])].map(String).sort();
  const competing = [...(contradictions.competing_claim_ids ?? [])].map(String).sort();

  let extractionDisplay = NOT_RECORDED;
  if (extraction) {
    const parts = [
      v(extraction.method),
      v(extraction.extractor_name),
      v(extraction.extractor_version),
    ].filter((p) => p !== NOT_RECORDED);
    extractionDisplay = parts.length > 0 ? parts.join(" / ") : NOT_RECORDED;
    const exReview = v(extraction.review_status);
    if (exReview !== NOT_RECORDED) extractionDisplay += ` (${exReview})`;
  }

  const supParts: string[] = [];
  if (supersession.revises_claim) {
    supParts.push(
      `revises ${supersession.revises_claim} (recorded ${v(supersession.prior_recorded_at)})`,
    );
  }
  if (supersession.retraction_of) {
    supParts.push(`retracts ${supersession.retraction_of}`);
  }
  const supersessionDisplay = supParts.length > 0 ? supParts.join("; ") : NOT_RECORDED;

  let conDisplay = NOT_RECORDED;
  const conBits: string[] = [];
  if (conIds.length > 0) conBits.push(`contradiction ${conIds.join(", ")}`);
  if (competing.length > 0) conBits.push(`competing ${competing.join(", ")}`);
  if (conBits.length > 0) conDisplay = conBits.join("; ");

  const apiHref = links.apiHref ?? null;

  return {
    schema: PANEL_SCHEMA,
    claim_id: claimId,
    binding_status: state,
    binding_text: stateText,
    source: {
      id: v(stmt.source_id),
      name: stmt.source_name ?? null,
      // The `/sources/` registry surface (per-source pages are a later row's
      // surface) — through withBase(), written without a leading slash so the
      // containment check measures no new site.
      href: links.sourceHref === undefined ? withBase("sources/") : links.sourceHref,
    },
    capture: {
      capture_id: v(capture.capture_id),
      artifact_id: v(capture.artifact_id),
      retrieved_at: v(capture.retrieved_at),
      digest: v(capture.digest),
      // Display-grouped (K14 NEW-8): thousands separators, never a bare
      // 5+-digit run. The row's raw integer stays in the statement; a
      // non-numeric value falls back to the named absence, never a crash.
      byte_size:
        typeof capture.byte_size === "number" && Number.isFinite(capture.byte_size)
          ? capture.byte_size.toLocaleString("en-US")
          : v(capture.byte_size),
      media_type: v(capture.media_type),
      storage_tier: v(capture.storage_tier),
    },
    upstream: { status: upStatus, display: upstreamDisplay, href: upstreamHref },
    view_original: {
      kind: v(viewOriginal.kind),
      label: v(viewOriginal.label),
      href: viewOriginal.href ?? null,
      note: viewOriginal.note ?? null,
    },
    extraction: extractionDisplay,
    directness: v(epistemics.directness),
    epistemic_review: {
      reliability: v(epistemics.reliability),
      integrity: v(epistemics.integrity),
      review: reviewDisplay,
    },
    contradictions: { display: conDisplay, ids: conIds, competing },
    supersession: supersessionDisplay,
    rights: {
      spdx: v(rights.spdx),
      attribution: v(rights.attribution),
      compartment: v(rights.compartment),
    },
    equivalent_requests: {
      json_href: links.jsonHref ?? null,
      api_href: apiHref,
      api_status: apiHref === null ? UNAVAILABLE : "available",
    },
    dispute_href:
      links.disputeHref === undefined ? withBase("dispute/") : links.disputeHref,
  };
}

/** Look a claim up in a `claim_id → sig.statement/1` index and normalise —
 *  the one call every surface makes. */
export function panelForClaim(
  index: ReadonlyMap<string, StatementRow>,
  claimId: string,
  links: PanelLinks = {},
): ProvenancePanelData {
  return panelFromStatement(index.get(claimId), claimId, links);
}
