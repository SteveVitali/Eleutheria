// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * P36.23 (UXK14-3b, K14 §4.6 "Callouts" row) — `sig.callout/1`: the typed
 * callout contract. Three kinds, a closed vocabulary:
 *
 *   - `note`        — a neutral aside the reader should see in context.
 *   - `caution`     — the Provisional-disclosure callout: the body warns that
 *                     the content beside it came from a method not yet
 *                     independently evaluated (the only callout that may
 *                     carry the provisional amber accent).
 *   - `known_issue` — a recorded defect or limitation stated where the
 *                     reader meets it, mirroring J3's issues log.
 *
 * The module is pure data + fail-closed lookup (SIG-ENG-042) so the
 * vocabulary is unit-testable independently of markup — the same shape
 * `lib/badges.ts` carries. The kind labels are agent-drafted public words:
 * sha256-pinned copy-batch rows in `batch-03.md` (B-2), rendered as
 * `data-copy` attributes so the publish gate refuses them until the
 * operator confirms the wording verbatim.
 */

/** The closed kind vocabulary — an unknown kind must fail, never render. */
export const CALLOUT_KINDS = ["note", "caution", "known_issue"] as const;
export type CalloutKind = (typeof CALLOUT_KINDS)[number];

/** One callout's render contract — a kind, its label and its batch binding. */
export interface CalloutSpec {
  kind: CalloutKind;
  /** The visible kind label ("Note" · "Caution" · "Known issue"). */
  label: string;
  /** The copy-batch row id the label is tracked under (B-2). */
  batchId: string;
}

const CALLOUT_SPECS: Record<CalloutKind, CalloutSpec> = {
  note: { kind: "note", label: "Note", batchId: "CK-62" },
  caution: { kind: "caution", label: "Caution", batchId: "CK-63" },
  known_issue: { kind: "known_issue", label: "Known issue", batchId: "CK-64" },
};

/**
 * Resolve a callout kind to its spec — fail closed: an unvetted kind throws
 * rather than rendering an unlabelled or invented callout (SIG-ENG-042).
 */
export function calloutSpec(kind: string): CalloutSpec {
  if (!(CALLOUT_KINDS as readonly string[]).includes(kind)) {
    throw new Error(`sig.callout/1: unknown callout kind "${kind}" — the vocabulary is closed`);
  }
  return CALLOUT_SPECS[kind as CalloutKind];
}
