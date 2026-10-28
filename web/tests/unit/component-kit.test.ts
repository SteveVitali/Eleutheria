// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// P36.22 (UXK14-3a, SIG-UI-054/083/084/086/151): the component-kit-A pure
// contracts — `sig.badge/1`, `sig.card/1` and `sig.error-page/1` — tested as
// data, independent of markup: closed vocabularies fail closed (SIG-ENG-042),
// every visible label comes from the lexicon or a verbatim id (SIG-UI-143),
// and the five-part typed states are complete on every surface.
import { describe, it, expect } from "vitest";
import {
  BADGE_KINDS,
  DIRECTNESS_CLASSES,
  ACCESS_KINDS,
  MIRROR_STATES,
  directnessBadge,
  accessKindBadge,
  licenceBadge,
  mirrorBadge,
} from "../../src/lib/badges";
import { CARD_KINDS, assertCard, defineCard, STATUS_CHIP_KINDS } from "../../src/lib/cards";
import {
  ERROR_KINDS,
  errorKindForCode,
  errorPage,
  errorPageForCode,
} from "../../src/lib/errors";
import {
  EMPTY_SURFACES,
  EMPTY_CAUSES,
  NON_ABSENCE_CAUSES,
  PIPELINE_CAUSES,
  emptyState,
  emptyStateHasHatch,
} from "../../src/lib/empty";
import { lexiconState } from "../../src/lib/lexicon";
import { readdirSync, readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

describe("sig.badge/1 — the neutral badge contract", () => {
  it("declares the four K14 badge kinds", () => {
    expect(BADGE_KINDS).toEqual(["directness", "access_kind", "licence", "mirror"]);
  });

  it("every §10.5 directness class resolves a lexicon label", () => {
    for (const cls of DIRECTNESS_CLASSES) {
      const spec = directnessBadge(cls);
      expect(spec.kind).toBe("directness");
      expect(spec.value).toBe(cls);
      expect(spec.label).toBe(lexiconState("directness", cls).label);
      expect(spec.meaning).toBe(lexiconState("directness", cls).plain);
    }
    expect(DIRECTNESS_CLASSES).toEqual(["D1", "D2", "D3", "D4", "D5", "D6"]);
  });

  it("every §12.2 access kind resolves a lexicon label", () => {
    for (const kind of ACCESS_KINDS) {
      const spec = accessKindBadge(kind);
      expect(spec.label).toBe(lexiconState("access", kind).label);
    }
    expect(ACCESS_KINDS).toEqual(["CONFIGURED_ACCESS", "DECLARED_POLICY", "OBSERVED_USE"]);
  });

  it("a licence badge carries the upstream SPDX id verbatim — never paraphrased", () => {
    const spec = licenceBadge("ODbL-1.0");
    expect(spec.label).toBe("ODbL-1.0");
    expect(spec.value).toBe("ODbL-1.0");
  });

  it("the three mirror states resolve neutral words", () => {
    expect(MIRROR_STATES).toEqual(["mirrored", "at_source", "no_bytes"]);
    for (const state of MIRROR_STATES) {
      const spec = mirrorBadge(state);
      expect(spec.label.length).toBeGreaterThan(0);
      expect(spec.meaning.length).toBeGreaterThan(0);
    }
  });

  it("fails closed on an unknown value (SIG-ENG-042)", () => {
    expect(() => directnessBadge("D9")).toThrow(/unknown class/);
    expect(() => accessKindBadge("PUBLIC")).toThrow(/unknown kind/);
    expect(() => mirrorBadge("elsewhere")).toThrow(/unknown state/);
    expect(() => licenceBadge("has spaces")).toThrow(/not a licence identifier/);
    expect(() => licenceBadge("")).toThrow();
  });
});

describe("sig.card/1 — the six-kind card contract", () => {
  it("declares the K14 card family verbatim", () => {
    expect(CARD_KINDS).toEqual([
      "place",
      "organization",
      "source",
      "task",
      "persona",
      "example",
    ]);
  });

  it("a non-empty card is a doorway — a title and a resolvable link are required", () => {
    expect(() =>
      assertCard({ kind: "place", title: "Nowhere" }, "test"),
    ).toThrow(/no resolvable link|carries no resolvable link/);
    expect(() =>
      assertCard({ kind: "place", titleHref: "/dossier/" }, "test"),
    ).toThrow(/names no title/);
    // A title + internal href validates.
    expect(() =>
      assertCard({ kind: "place", title: "Oklahoma City", titleHref: "/dossier/" }, "test"),
    ).not.toThrow();
  });

  it("a persona card carries 3–4 linked steps (K14 §6.1)", () => {
    const base = { kind: "persona" as const, title: "A resident", titleHref: "/dossier/" };
    expect(() =>
      assertCard({ ...base, steps: [{ label: "one", href: "/" }] }, "test"),
    ).toThrow(/3–4/);
    expect(() =>
      assertCard(
        {
          ...base,
          steps: [1, 2, 3, 4, 5].map((i) => ({ label: `step ${i}`, href: "/" })),
        },
        "test",
      ),
    ).toThrow(/3–4/);
    expect(() =>
      assertCard(
        { ...base, steps: [1, 2, 3].map((i) => ({ label: `step ${i}`, href: "/" })) },
        "test",
      ),
    ).not.toThrow();
  });

  it("an example card names its question (K14 §6.2)", () => {
    expect(() =>
      assertCard(
        { kind: "example", title: "Who queries?", titleHref: "/network/" },
        "test",
      ),
    ).toThrow(/names its question/);
    expect(() =>
      assertCard(
        {
          kind: "example",
          title: "Who queries?",
          titleHref: "/network/",
          meta: [{ label: "Question", value: "Who can query this camera network?" }],
        },
        "test",
      ),
    ).not.toThrow();
  });

  it("an empty card carries its surface and nothing else — never a dead card", () => {
    expect(() =>
      assertCard({ kind: "place", empty: "dossierIndex", title: "ghost" }, "test"),
    ).toThrow(/carries no title\/link/);
    expect(() =>
      assertCard({ kind: "place", empty: "dossierIndex" }, "test"),
    ).not.toThrow();
  });

  it("the status-chip vocabulary is the K14 status row", () => {
    expect(STATUS_CHIP_KINDS).toEqual([
      "provisional",
      "historical",
      "not_reviewed",
      "superseded",
      "withdrawn",
    ]);
  });

  it("defineCard returns a validated spec", () => {
    const card = defineCard(
      {
        kind: "source",
        title: "A source",
        titleHref: "/sources/",
        badges: [{ kind: "licence", value: "ODbL-1.0" }],
      },
      "test",
    );
    expect(card.kind).toBe("source");
  });
});

describe("sig.error-page/1 — the five-part branded error contract (SIG-UI-151)", () => {
  it("maps the four error kinds", () => {
    expect(ERROR_KINDS).toEqual(["not_found", "refused", "removed", "server_error"]);
    expect(errorKindForCode(404)).toBe("not_found");
    expect(errorKindForCode(403)).toBe("refused");
    expect(errorKindForCode(410)).toBe("removed");
    expect(errorKindForCode(500)).toBe("server_error");
    expect(() => errorKindForCode(418)).toThrow(/no typed kind/);
  });

  it("every error page carries all five parts plus the recovery trio", () => {
    for (const kind of ERROR_KINDS) {
      const spec = errorPage(kind);
      for (const part of ["state", "missing", "nearby", "change"] as const) {
        expect(spec[part].length, `${kind}.${part}`).toBeGreaterThan(0);
      }
      // SIG-UI-151: search · home · status are always present — the action is
      // home, the recovery pair is search + status.
      expect(spec.action.href, `${kind} primary action`).toBe("/");
      const recovery = spec.recovery.map((r) => r.href);
      expect(recovery, `${kind} recovery links`).toContain("/search/");
      expect(recovery, `${kind} recovery links`).toContain("/status/");
      // The drafted sentences are copy-batch bound (B-2); notice strings bind
      // only where a pinned N-string is the body.
      for (const r of spec.recovery) expect(r.batchId).toBeTruthy();
    }
  });

  it("only the removed page renders a pinned notice string", () => {
    expect(errorPage("removed").notice).toBe("N-6");
    expect(errorPage("removed").missing).toBe(
      "This page has been removed while a correction is made.",
    );
    for (const kind of ["not_found", "refused", "server_error"] as const) {
      expect(errorPage(kind).notice).toBeUndefined();
    }
  });

  it("errorPageForCode composes the kind lookup", () => {
    expect(errorPageForCode(500).kind).toBe("server_error");
  });
});

describe("the typed empty states (SIG-UI-086)", () => {
  it("EVERY surface carries the five-part pattern with a named cause", () => {
    for (const surface of EMPTY_SURFACES) {
      const copy = emptyState(surface);
      expect(copy.parts, `${surface} has no parts`).toBeDefined();
      const parts = copy.parts!;
      for (const key of ["state", "missing", "nearby", "change"] as const) {
        expect(parts[key].length, `${surface}.${key}`).toBeGreaterThan(0);
      }
      expect(parts.action.href, `${surface}.action`).toMatch(/^\//);
      expect(parts.action.label.length, `${surface}.action`).toBeGreaterThan(0);
      expect(
        (EMPTY_CAUSES as readonly string[]).includes(parts.cause),
        `${surface} cause "${parts.cause}" is not a declared cause class`,
      ).toBe(true);
      // The legacy fields mirror the parts — the two render paths never drift.
      expect(copy.heading).toBe(parts.state);
      expect(copy.body).toBe(parts.missing);
      expect(copy.cta).toEqual(parts.action);
    }
  });

  it("a pipeline/publication gap never routes to the research queue (F-409/F-410)", () => {
    for (const surface of EMPTY_SURFACES) {
      const parts = emptyState(surface).parts!;
      if ((PIPELINE_CAUSES as readonly string[]).includes(parts.cause)) {
        expect(
          parts.action.href,
          `${surface} (${parts.cause}) must not send a pipeline gap to the queue`,
        ).not.toBe("/research-queue/");
      }
    }
    // … and the queue remains the honest affordance for a real research gap.
    expect(emptyState("mapAssets").parts!.action.href).toBe("/research-queue/");
    expect(emptyState("mapAssets").parts!.cause).toBe("not_researched");
  });

  it("no cause-class sentence calls itself a 'research gap'", () => {
    for (const surface of EMPTY_SURFACES) {
      const parts = emptyState(surface).parts!;
      const all = `${parts.state} ${parts.missing} ${parts.nearby} ${parts.change}`;
      expect(all.toLowerCase(), surface).not.toContain("research gap");
    }
  });

  it("the provenance channel stays ONE contract — no kit component emits a second panel (SIG-UI-083)", () => {
    // `sig.provenance-panel/1` renders through `ProvenancePanel.tsx` only
    // (P35.36/TX-08a). The kit's provenance channel is the <Figure> artifact +
    // pointer contract — a component-kit file must never mint its own panel.
    const componentsDir = fileURLToPath(new URL("../../src/components/", import.meta.url));
    const walk = (dir: string): string[] =>
      readdirSync(dir, { withFileTypes: true }).flatMap((d) =>
        d.isDirectory() ? walk(`${dir}${d.name}/`) : [`${dir}${d.name}`],
      );
    const emitters = walk(componentsDir)
      .filter((f) => !f.endsWith("ProvenancePanel.tsx"))
      .filter((f) => readFileSync(f, "utf-8").includes("data-provenance-panel"));
    expect(emitters, "a second provenance-panel emitter appeared").toEqual([]);
  });

  it("the hatch renders only when the cause IS absence", () => {
    for (const cause of EMPTY_CAUSES) {
      const expectHatch = !(NON_ABSENCE_CAUSES as readonly string[]).includes(cause);
      expect(emptyStateHasHatch(cause), cause).toBe(expectHatch);
    }
    // Every currently-mounted surface is an absence cause — the hatch stays.
    for (const surface of EMPTY_SURFACES) {
      const parts = emptyState(surface).parts!;
      expect(
        emptyStateHasHatch(parts.cause),
        `${surface} (${parts.cause}) unexpectedly dropped the hatch`,
      ).toBe(true);
    }
    // The non-absence kinds exist for the surfaces that need them (P36.23's
    // typed kinds): a filter returning nothing or a rights hold is NOT a gap.
    expect(emptyStateHasHatch("filtered_none")).toBe(false);
    expect(emptyStateHasHatch("not_redistributable")).toBe(false);
    expect(emptyStateHasHatch("degraded")).toBe(false);
  });
});
