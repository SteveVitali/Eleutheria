// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// The honest empty-state copy contract (§9.5, §15, SIG-UI-007, the §3.1 defining
// standard): absence is rendered as an explained gap with a task affordance, never a
// blank and never a fabricated zero. These are the rules the copy must satisfy on
// every surface, tested independently of any markup or style.
import { describe, it, expect } from "vitest";
import { emptyState, EMPTY_SURFACES, RESEARCH_QUEUE_CTA } from "../../src/lib/empty";

describe("empty-state copy (SIG-UI-007, §3.1)", () => {
  it("covers every declared surface with a heading, framing body, and CTA", () => {
    expect(EMPTY_SURFACES.length).toBeGreaterThan(0);
    for (const surface of EMPTY_SURFACES) {
      const copy = emptyState(surface);
      expect(copy.heading.length, `${surface} heading`).toBeGreaterThan(0);
      expect(copy.body.length, `${surface} body`).toBeGreaterThan(0);
      // A gap is an invitation, not a dead end: a real, no-JS GET affordance.
      expect(copy.cta.href, `${surface} cta href`).toMatch(/^\//);
      expect(copy.cta.label.length, `${surface} cta label`).toBeGreaterThan(0);
    }
  });

  it("never renders a fabricated zero — no bare '0' count in any body", () => {
    for (const surface of EMPTY_SURFACES) {
      const { body } = emptyState(surface);
      // A fabricated zero is a numeric count of 0 ("0 devices"); the WORD "zero" is
      // permitted (bodies use it to say the surface is NOT a measurement of zero).
      expect(body, `${surface} must not assert a numeric zero`).not.toMatch(/\b0\b/);
    }
  });

  it("frames absence as not-yet-researched, never as 'nothing exists'", () => {
    // Honest not-yet / not-a-finding markers any empty body must carry at least one of.
    const MARKERS = [
      "not yet",
      "yet",
      "has not",
      "does not",
      "not a ",
      "never",
      "not evidence",
      "no ",
      "none",
      "not published",
    ];
    for (const surface of EMPTY_SURFACES) {
      const body = emptyState(surface).body.toLowerCase();
      const framed = MARKERS.some((m) => body.includes(m));
      expect(framed, `${surface} must frame absence honestly: "${body}"`).toBe(true);
    }
  });

  it("routes the default task affordance to the public research queue", () => {
    expect(RESEARCH_QUEUE_CTA.href).toBe("/research-queue/");
    expect(emptyState("mapAssets").cta).toEqual(RESEARCH_QUEUE_CTA);
  });
});
