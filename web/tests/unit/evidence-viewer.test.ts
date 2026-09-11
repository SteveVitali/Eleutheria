// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// The §39.6 evidence viewer, tested on the pure logic (SIG-UI-028/029/030): the span
// highlight at the locator, the field-by-field capture diff, and the sealed-capture
// metadata-only representation.
import { describe, expect, it } from "vitest";
import {
  assertCaptureTier,
  assertClaimView,
  assertSpanValid,
  changedFields,
  claimContestedMarker,
  claimHighlightedDocument,
  diffCaptures,
  highlightSpan,
  isClaimContested,
  isSealed,
  sealedMetadata,
} from "../../src/lib/evidence-viewer";
import type { Capture, ClaimView } from "../../src/lib/evidence-viewer";
import {
  CONTRACT_CAPTURE,
  DEVICE_COUNT_CLAIM_VIEW,
  PORTAL_CAPTURE_AUGUST,
  PORTAL_CAPTURE_JUNE,
  SEALED_CAPTURE,
  SEALED_CLAIM_VIEW,
} from "../../src/lib/watch-evidence-fixture";
import { CONTESTED_MARKER } from "../../src/lib/epistemic";

describe("renders the document with the supporting span highlighted (SIG-UI-028)", () => {
  it("splits the document at the locator span", () => {
    const doc = claimHighlightedDocument(DEVICE_COUNT_CLAIM_VIEW)!;
    expect(doc.highlighted).toBe("forty-two (42)");
    expect(CONTRACT_CAPTURE.document_text!).toBe(doc.before + doc.highlighted + doc.after);
  });

  it("rejects an out-of-bounds or empty span", () => {
    const text = "abcdef";
    expect(() => assertSpanValid(text, { start: 0, end: 3 })).not.toThrow();
    expect(() => assertSpanValid(text, { start: 3, end: 3 })).toThrow(/SIG-UI-028/); // empty
    expect(() => assertSpanValid(text, { start: 0, end: 99 })).toThrow(/SIG-UI-028/); // OOB
    expect(() => highlightSpan(text, { start: -1, end: 2 })).toThrow(/SIG-UI-028/);
  });

  it("the full evidence view carries claim, method+version, review, digest, acquisition, history", () => {
    expect(() => assertClaimView(DEVICE_COUNT_CLAIM_VIEW)).not.toThrow();
    expect(DEVICE_COUNT_CLAIM_VIEW.extraction_version).toBeTruthy();
    expect(DEVICE_COUNT_CLAIM_VIEW.capture.content_digest).toMatch(/^sha256:/);
    expect(DEVICE_COUNT_CLAIM_VIEW.capture.acquisition_method).toBeTruthy();
    expect(DEVICE_COUNT_CLAIM_VIEW.history.length).toBeGreaterThan(0);
  });

  it("rejects an incomplete evidence view (missing history or method)", () => {
    const noHistory: ClaimView = { ...DEVICE_COUNT_CLAIM_VIEW, history: [] };
    expect(() => assertClaimView(noHistory)).toThrow(/SIG-UI-028/);
    const noMethod: ClaimView = { ...DEVICE_COUNT_CLAIM_VIEW, extraction_version: "" };
    expect(() => assertClaimView(noMethod)).toThrow(/SIG-UI-028/);
  });

  it("a claim with conflicting claims is contested and carries the marker (SIG-UI-008)", () => {
    expect(isClaimContested(DEVICE_COUNT_CLAIM_VIEW)).toBe(true);
    expect(claimContestedMarker(DEVICE_COUNT_CLAIM_VIEW)!.glyph).toBe(CONTESTED_MARKER.glyph);
    expect(isClaimContested(SEALED_CLAIM_VIEW)).toBe(false);
    expect(claimContestedMarker(SEALED_CLAIM_VIEW)).toBeNull();
  });
});

describe("diffs two captures of the same artifact field by field (SIG-UI-029, §29.7)", () => {
  const diff = diffCaptures(PORTAL_CAPTURE_JUNE, PORTAL_CAPTURE_AUGUST);

  it("produces a per-field event with both values and both dates", () => {
    const count = diff.find((c) => c.field === "active_device_count")!;
    expect(count.from_value).toBe(40);
    expect(count.to_value).toBe(38);
    expect(count.from_date).toBe("2026-06-01");
    expect(count.to_date).toBe("2026-08-01");
    expect(count.changed).toBe(true);
  });

  it("marks unchanged fields as unchanged and orders earlier → later regardless of arg order", () => {
    const retention = diff.find((c) => c.field === "retention_days")!;
    expect(retention.changed).toBe(false);
    // Swapping the argument order still reads chronologically (June is "from").
    const swapped = diffCaptures(PORTAL_CAPTURE_AUGUST, PORTAL_CAPTURE_JUNE);
    expect(swapped.find((c) => c.field === "active_device_count")!.from_value).toBe(40);
  });

  it("the change feed is just the changed fields", () => {
    const changed = changedFields(PORTAL_CAPTURE_JUNE, PORTAL_CAPTURE_AUGUST).map((c) => c.field).sort();
    expect(changed).toEqual(["active_device_count", "network_partners"]);
  });

  it("refuses to diff captures of different artifacts", () => {
    expect(() => diffCaptures(PORTAL_CAPTURE_JUNE, CONTRACT_CAPTURE)).toThrow(/SIG-UI-029/);
  });
});

describe("sealed captures are metadata-only with an explanation (SIG-UI-030, §17.5)", () => {
  it("a sealed capture exposes no bytes and no highlighted document", () => {
    expect(isSealed(SEALED_CAPTURE)).toBe(true);
    expect(SEALED_CAPTURE.document_text).toBeUndefined();
    expect(claimHighlightedDocument(SEALED_CLAIM_VIEW)).toBeNull();
  });

  it("the metadata-only representation carries existence, source, date, digest, and the reason", () => {
    const meta = sealedMetadata(SEALED_CAPTURE);
    expect(meta.storage_tier).toBe("sealed");
    expect(meta.content_digest).toMatch(/^sha256:/);
    expect(meta.captured_at).toBe("2026-05-12");
    expect(meta.sealed_reason).toMatch(/withheld|PII|sealed/i);
    // The claims/fields it supports stay public even though the bytes do not.
    expect(meta.supported_fields).toContain("operator_count");
  });

  it("rejects a sealed capture that exposes bytes or omits the reason", () => {
    const leaky: Capture = { ...SEALED_CAPTURE, document_text: "secret" };
    expect(() => assertCaptureTier(leaky)).toThrow(/SIG-UI-030/);
    const noReason: Capture = { ...SEALED_CAPTURE };
    delete (noReason as { sealed_reason?: string }).sealed_reason;
    expect(() => assertCaptureTier(noReason)).toThrow(/SIG-UI-030/);
  });

  it("a non-sealed capture MUST carry its document text", () => {
    const missing: Capture = { ...PORTAL_CAPTURE_JUNE };
    delete (missing as { document_text?: string }).document_text;
    expect(() => assertCaptureTier(missing)).toThrow(/SIG-UI-028/);
    expect(() => sealedMetadata(CONTRACT_CAPTURE)).toThrow(/SIG-UI-030/);
  });
});
