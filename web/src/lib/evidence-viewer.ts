// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * The evidence viewer as pure data + logic (§39.6).
 *
 * The evidence-inspection half of P15.4. It owns three requirements:
 *
 *   - SIG-UI-028: render the document with the supporting span highlighted at its
 *     locator, and show the claim, the extraction method + version, the review
 *     status, the conflicting claims, the capture date + digest, the acquisition
 *     method, and the FULL history of the claim. A locator that does not resolve to
 *     a span is the "unexplained edge" the defining standard forbids (§3.1), so a
 *     claim view without a valid span cannot be built.
 *   - SIG-UI-029: diff two captures of the same artifact FIELD BY FIELD, producing a
 *     per-field change event with both values and both dates — "what changed on the
 *     portal between June and August" (§29.7, SIG-RECON-045).
 *   - SIG-UI-030: for a `sealed` capture, show the metadata-only representation with
 *     an explanation of why the bytes are withheld (§17.5, SIG-EVID-009/010). A
 *     sealed capture MUST carry NO document bytes — its existence, source, date,
 *     digest, and the claims it supports are public; its bytes are not.
 *
 * Colour-free by construction (colour lives in `styles/epistemic.css`); a claim with
 * conflicting claims is contested and carries the shared `≠` marker at every
 * appearance (SIG-UI-008).
 */

import { CONTESTED_MARKER } from "./epistemic";
import type { CompetingClaim } from "./epistemic";

// --- Storage tiers (§17.5, SIG-EVID-009) -------------------------------------

/** The three §17.5 storage tiers. `sealed` is metadata-only in public. */
export const STORAGE_TIERS = ["public", "restricted", "sealed"] as const;
export type StorageTier = (typeof STORAGE_TIERS)[number];

// --- The locator + span (SIG-UI-028, §11.x) ----------------------------------

/**
 * A character span within a capture's document text — the resolved form of the
 * claim's locator, used to highlight the supporting text (SIG-UI-028). Half-open
 * `[start, end)`; `end` is exclusive.
 */
export interface TextSpan {
  start: number;
  end: number;
}

/** A locator: the addressable position of the support, plus its resolved char span. */
export interface Locator {
  /** e.g. "page" | "cell" | "char_range" | "timestamp" — opaque to this module. */
  kind: string;
  /** A human-readable description of the locator, e.g. "page 3, ¶2". */
  description: string;
  /** The resolved character span in the capture's `document_text` (SIG-UI-028). */
  span: TextSpan;
}

/** Throw if a span is out of bounds or empty for the given text (SIG-UI-028). */
export function assertSpanValid(text: string, span: TextSpan): void {
  if (!Number.isInteger(span.start) || !Number.isInteger(span.end)) {
    throw new Error("SIG-UI-028: a locator span must have integer bounds.");
  }
  if (span.start < 0 || span.end > text.length || span.start >= span.end) {
    throw new Error(
      `SIG-UI-028: locator span [${span.start}, ${span.end}) is not a non-empty range within the ` +
        `${text.length}-char document.`,
    );
  }
}

/** The document split around the highlighted span, for rendering (SIG-UI-028). */
export interface HighlightedDocument {
  before: string;
  highlighted: string;
  after: string;
}

/** Split a document's text into before / highlighted / after at the locator span. */
export function highlightSpan(text: string, span: TextSpan): HighlightedDocument {
  assertSpanValid(text, span);
  return {
    before: text.slice(0, span.start),
    highlighted: text.slice(span.start, span.end),
    after: text.slice(span.end),
  };
}

// --- The capture (SIG-UI-028, SIG-UI-030) ------------------------------------

/**
 * A capture of an artifact. Mirrors the evidence store's row shape (`storage_tier`,
 * `content_digest`, `capture_method`, `retrieved_at`, `extraction_method`). For a
 * `public`/`restricted` capture `document_text` is present (the bytes the span
 * highlights); for a `sealed` capture it MUST be absent and `sealed_reason` set
 * (SIG-UI-030, SIG-EVID-009/010).
 */
export interface Capture {
  capture_id: string;
  artifact_id: string;
  storage_tier: StorageTier;
  /** The capture date (ISO) — shown in the viewer (SIG-UI-028). */
  captured_at: string;
  /** The content digest — shown in the viewer (SIG-UI-028). */
  content_digest: string;
  /** How the bytes were acquired, e.g. "http_get" | "manual_upload" (SIG-UI-028). */
  acquisition_method: string;
  /** The document text — present unless the capture is sealed. */
  document_text?: string;
  /** For a sealed capture: why the bytes are withheld (SIG-UI-030, §17.5). */
  sealed_reason?: string;
  /** The extracted fields, keyed by field name — the unit of the field-by-field diff. */
  fields: Record<string, string | number>;
}

/** Whether a capture is sealed (bytes withheld; metadata-only in public). */
export function isSealed(capture: Capture): boolean {
  return capture.storage_tier === "sealed";
}

/**
 * Validate a capture's tier invariants (SIG-UI-030, SIG-EVID-009/010): a sealed
 * capture MUST NOT carry document bytes and MUST explain why they are withheld; a
 * non-sealed capture MUST carry its document text so the span can be highlighted.
 */
export function assertCaptureTier(capture: Capture): void {
  if (isSealed(capture)) {
    if (capture.document_text !== undefined) {
      throw new Error(
        `SIG-UI-030: sealed capture ${capture.capture_id} MUST NOT expose document bytes ` +
          "(metadata-only public representation, §17.5).",
      );
    }
    if (!capture.sealed_reason) {
      throw new Error(
        `SIG-UI-030: sealed capture ${capture.capture_id} MUST explain why its bytes are withheld.`,
      );
    }
  } else if (capture.document_text === undefined) {
    throw new Error(
      `SIG-UI-028: non-sealed capture ${capture.capture_id} MUST carry its document text so the ` +
        "supporting span can be highlighted.",
    );
  }
}

/**
 * The metadata-only public representation of a sealed capture (SIG-UI-030,
 * SIG-EVID-010): its existence, source, date, digest, and the explanation of why the
 * bytes are withheld — never the bytes. Throws if called on a non-sealed capture.
 */
export interface SealedMetadata {
  capture_id: string;
  artifact_id: string;
  captured_at: string;
  content_digest: string;
  acquisition_method: string;
  storage_tier: "sealed";
  sealed_reason: string;
  /** The fields the sealed capture still supports (claims are public even when bytes are not). */
  supported_fields: string[];
}

export function sealedMetadata(capture: Capture): SealedMetadata {
  if (!isSealed(capture)) {
    throw new Error(`SIG-UI-030: ${capture.capture_id} is not sealed; render its document instead.`);
  }
  assertCaptureTier(capture);
  return {
    capture_id: capture.capture_id,
    artifact_id: capture.artifact_id,
    captured_at: capture.captured_at,
    content_digest: capture.content_digest,
    acquisition_method: capture.acquisition_method,
    storage_tier: "sealed",
    sealed_reason: capture.sealed_reason!,
    supported_fields: Object.keys(capture.fields).sort(),
  };
}

// --- The claim view (SIG-UI-028) ---------------------------------------------

/** One event in a claim's full history (SIG-UI-028): assertion, correction, etc. */
export interface ClaimHistoryEvent {
  /** The belief-time the event was asserted (ISO). */
  asserted_at: string;
  event: "asserted" | "corrected" | "superseded" | "withdrawn";
  value: string | number;
  note?: string;
}

/**
 * The full evidence view of a claim (SIG-UI-028): the claim, the capture it rests on,
 * the extraction method + version, the review status, the conflicting claims, and the
 * full history. `assertClaimView` enforces the SIG-UI-028 completeness contract.
 */
export interface ClaimView {
  claim_id: string;
  /** Plain-language claim, e.g. "Active device count = 42". */
  claim_label: string;
  value: string | number;
  /** The capture whose span supports the claim. */
  capture: Capture;
  /** The locator resolving to the supporting span in the capture's text (SIG-UI-028). */
  locator: Locator;
  /** The extraction method (§24 layer) and its version (SIG-UI-028). */
  extraction_method: string;
  extraction_version: string;
  /** The review status, e.g. "unreviewed" | "curator_reviewed" | "disputed". */
  review_status: string;
  /** Conflicting claims (§29.1). Non-empty ⇒ contested (SIG-UI-008). */
  conflicting_claims: CompetingClaim[];
  /** The full history of the claim (SIG-UI-028). */
  history: ClaimHistoryEvent[];
}

/** Whether a claim view is contested — it has one or more conflicting claims (SIG-UI-008). */
export function isClaimContested(view: ClaimView): boolean {
  return view.conflicting_claims.length > 0;
}

/** The contested marker for a claim view (SIG-UI-008), or null when uncontested. */
export function claimContestedMarker(view: ClaimView): { glyph: string; label: string } | null {
  return isClaimContested(view) ? { glyph: CONTESTED_MARKER.glyph, label: CONTESTED_MARKER.label } : null;
}

/**
 * Enforce the SIG-UI-028 completeness contract: every required field is present, the
 * locator resolves to a valid span (for a non-sealed capture), and the history is
 * non-empty (a claim with no history is unexplained). Throws otherwise, so an
 * incomplete evidence view can never render.
 */
export function assertClaimView(view: ClaimView): void {
  assertCaptureTier(view.capture);
  for (const [field, value] of Object.entries({
    extraction_method: view.extraction_method,
    extraction_version: view.extraction_version,
    review_status: view.review_status,
    content_digest: view.capture.content_digest,
    acquisition_method: view.capture.acquisition_method,
    captured_at: view.capture.captured_at,
  })) {
    if (!value) throw new Error(`SIG-UI-028: the evidence view for ${view.claim_id} is missing ${field}.`);
  }
  if (view.history.length === 0) {
    throw new Error(`SIG-UI-028: the evidence view for ${view.claim_id} must include the full claim history.`);
  }
  // A non-sealed capture's supporting span must resolve; a sealed capture has no
  // bytes to highlight (its view is metadata-only, SIG-UI-030).
  if (!isSealed(view.capture)) {
    assertSpanValid(view.capture.document_text!, view.locator.span);
  }
}

/** The highlighted supporting document for a claim view, or null when sealed (SIG-UI-030). */
export function claimHighlightedDocument(view: ClaimView): HighlightedDocument | null {
  if (isSealed(view.capture)) return null;
  return highlightSpan(view.capture.document_text!, view.locator.span);
}

// --- Capture diffing, field by field (SIG-UI-029, §29.7) ---------------------

/**
 * A per-field change event between two captures (SIG-RECON-045): the field, both
 * values, and both capture dates. `changed` is true when the values differ (a
 * field present in only one capture is a change from/to `null`).
 */
export interface FieldChange {
  field: string;
  from_value: string | number | null;
  to_value: string | number | null;
  from_date: string;
  to_date: string;
  changed: boolean;
}

/**
 * Diff two captures of the SAME artifact, field by field (SIG-UI-029, §29.7). The
 * diff is at the extracted-field level, producing a per-field change event with both
 * values and both dates — the basis of the change feed. Ordered by earlier capture
 * first; the union of both captures' fields is compared (sorted for determinism).
 * Throws if the captures are of different artifacts (a cross-artifact diff is
 * meaningless).
 */
export function diffCaptures(a: Capture, b: Capture): FieldChange[] {
  if (a.artifact_id !== b.artifact_id) {
    throw new Error(
      `SIG-UI-029: cannot diff captures of different artifacts (${a.artifact_id} vs ${b.artifact_id}).`,
    );
  }
  // Order earlier → later by capture date so "from"/"to" read chronologically.
  const [earlier, later] = a.captured_at <= b.captured_at ? [a, b] : [b, a];
  const fields = Array.from(new Set([...Object.keys(earlier.fields), ...Object.keys(later.fields)])).sort();
  return fields.map((field) => {
    const from_value = field in earlier.fields ? earlier.fields[field]! : null;
    const to_value = field in later.fields ? later.fields[field]! : null;
    return {
      field,
      from_value,
      to_value,
      from_date: earlier.captured_at,
      to_date: later.captured_at,
      changed: from_value !== to_value,
    };
  });
}

/** The subset of a capture diff that actually changed (the change feed, SIG-UI-029). */
export function changedFields(a: Capture, b: Capture): FieldChange[] {
  return diffCaptures(a, b).filter((c) => c.changed);
}

/** The canonical page path for an evidence viewer (trailing slash — SIG-UI-035). */
export function evidencePath(claimId: string): string {
  return `/evidence/${claimId}/`;
}
