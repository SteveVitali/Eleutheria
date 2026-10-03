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

describe("cause-class empty states (P34.20, K14 §6.4, SIG-EVUI-D08, F-409/F-410)", () => {
  // The five surfaces whose emptiness has a NAMED cause — each renders the
  // K14 five-part pattern, never a "research gap" and never a queue CTA.
  const CAUSE_SURFACES = [
    "watch",
    "watchSubscriptions",
    "recommender",
    "citations",
    "evidenceIndex",
  ] as const;

  it("every cause-class surface carries all five parts (label, missing+why, nearby, action, change)", () => {
    for (const surface of CAUSE_SURFACES) {
      const parts = emptyState(surface).parts;
      expect(parts, `${surface} must carry the K14 five-part pattern`).toBeDefined();
      expect(parts!.state.length, `${surface} state label`).toBeGreaterThan(0);
      expect(parts!.missing.length, `${surface} missing+why`).toBeGreaterThan(0);
      expect(parts!.nearby.length, `${surface} nearby`).toBeGreaterThan(0);
      expect(parts!.action.label.length, `${surface} action label`).toBeGreaterThan(0);
      expect(parts!.action.href, `${surface} action href`).toMatch(/^\//);
      expect(parts!.change.length, `${surface} when-it-may-change`).toBeGreaterThan(0);
    }
  });

  it("the state label is a typed kind — never a bare 'empty'", () => {
    for (const surface of CAUSE_SURFACES) {
      const state = emptyState(surface).parts!.state.toLowerCase();
      expect(state.trim(), `${surface} state`).not.toBe("empty");
      expect(state, `${surface} state must name a kind`).toMatch(/no |not |none /);
    }
  });

  it("no cause-class copy says 'research gap' or 'research-queue'", () => {
    for (const surface of CAUSE_SURFACES) {
      const copy = emptyState(surface);
      const all = [
        copy.heading,
        copy.body,
        copy.cta.label,
        ...Object.values({
          s: copy.parts!.state,
          m: copy.parts!.missing,
          n: copy.parts!.nearby,
          c: copy.parts!.change,
        }),
      ].join(" ");
      expect(all.toLowerCase(), `${surface} must not call a pipeline gap a research gap`).not.toContain(
        "research gap",
      );
    }
  });

  it("no cause-class surface routes the visitor to the research queue as the remedy", () => {
    for (const surface of CAUSE_SURFACES) {
      const copy = emptyState(surface);
      expect(copy.cta.href, `${surface} cta`).not.toBe("/research-queue/");
      expect(copy.parts!.action.href, `${surface} action`).not.toBe("/research-queue/");
    }
  });

  it("every cause-class part binds a copy-batch row id (B-2 — pending until confirmed)", () => {
    for (const surface of CAUSE_SURFACES) {
      const ids = emptyState(surface).parts!.batchIds;
      for (const [part, id] of Object.entries(ids)) {
        expect(id, `${surface}.${part} batch id`).toMatch(/^EW-\d+$/);
      }
    }
  });

  it("heading/body/cta mirror the five parts so the two render paths cannot drift", () => {
    for (const surface of CAUSE_SURFACES) {
      const copy = emptyState(surface);
      expect(copy.heading, `${surface} heading`).toBe(copy.parts!.state);
      expect(copy.body, `${surface} body`).toBe(copy.parts!.missing);
      expect(copy.cta, `${surface} cta`).toEqual(copy.parts!.action);
    }
  });
});
