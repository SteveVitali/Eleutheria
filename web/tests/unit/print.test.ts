// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// P36.26 (K14 UXK14-9 / K14 §4.10–4.11, SIG-UI-098/130/155) — the print
// document's composition model: the council brief, the declared figure pages,
// the terms strip, and the page plan the route renders.

import { describe, expect, it } from "vitest";
import {
  PRINT_FIGURE_CONTRACT,
  assertPrintFigures,
  councilDecision,
  documentsToBring,
  planPrintPages,
  recordedGlance,
  termsUsedOnPage,
} from "../../src/lib/print";
import { dossierFieldAudit, dossierUnknowns } from "../../src/lib/dossier";
import { glossaryTerm } from "../../src/lib/lexicon";
import { OKC_DOSSIER } from "../../src/lib/dossier-fixture";

const minimalDossier = (over: Partial<typeof OKC_DOSSIER> = {}): typeof OKC_DOSSIER => ({
  ...OKC_DOSSIER,
  ...over,
});

describe("sig.print-figure/1 — the declared visual contract", () => {
  it("accepts every declared kind", () => {
    for (const kind of ["map", "extent", "trend", "axis"] as const) {
      expect(() => assertPrintFigures([{ kind, title: "T" }], "x")).not.toThrow();
    }
  });

  it("fails closed on an unknown kind, an empty title, or a non-lexicon state", () => {
    expect(() => assertPrintFigures([{ kind: "chart", title: "T" }], "x")).toThrow(
      PRINT_FIGURE_CONTRACT,
    );
    expect(() => assertPrintFigures([{ kind: "map", title: "  " }], "x")).toThrow(
      PRINT_FIGURE_CONTRACT,
    );
    expect(() =>
      assertPrintFigures([{ kind: "map", title: "T", state: "NOT_A_STATE" }], "x"),
    ).toThrow(PRINT_FIGURE_CONTRACT);
    // A real lexicon state passes.
    expect(() =>
      assertPrintFigures([{ kind: "map", title: "T", state: "CONTESTED" }], "x"),
    ).not.toThrow();
  });
});

describe("the council brief model (K14 §4.10)", () => {
  it("counts recorded fields against the same field universe the banner audits", () => {
    const glance = recordedGlance(OKC_DOSSIER);
    const audit = dossierFieldAudit(OKC_DOSSIER);
    const u = dossierUnknowns(OKC_DOSSIER);
    // The invariant: every field is recorded, unknown, or withheld — the three
    // channels partition the universe the audit defines.
    expect(glance.total).toBe(audit.allFields.size);
    expect(glance.recorded + u.total + audit.withheld).toBe(glance.total);
    expect(glance.unknowns).toEqual(u);
    expect(glance.recorded).toBeGreaterThan(0);
  });

  it("resolves the derived decision date from the termination inputs", () => {
    const d = councilDecision(OKC_DOSSIER);
    // 2027-04-02 expiry minus the 90-day auto-renew notice window (SIG-UI-014b).
    expect(d.date).toBe("2027-01-02");
    expect(d.absence).toBeNull();
    expect(d.basis).toBe("renewal-or-expiry");
  });

  it("emits the typed absence — never a fabricated date — when none is recorded", () => {
    const d = councilDecision(
      minimalDossier({ termination: { auto_renews: null, notice_window_days: null, expiry_date: null } }),
    );
    expect(d.date).toBeNull();
    expect(d.absence).toBe("Not recorded in SIG");
  });

  it("lists 3–5 real document locators, deduplicated, in dossier order", () => {
    const docs = documentsToBring(OKC_DOSSIER);
    expect(docs.length).toBeGreaterThanOrEqual(3);
    expect(docs.length).toBeLessThanOrEqual(5);
    expect(new Set(docs.map((d) => d.href)).size).toBe(docs.length);
    // Every locator comes from the record — never invented.
    const allHrefs = new Set<string>();
    for (const s of OKC_DOSSIER.sections) {
      for (const r of s.rows ?? []) if (r.documentUrl) allHrefs.add(r.documentUrl);
      for (const f of s.figures ?? [])
        for (const c of f.reconciliation.claims) allHrefs.add(c.documentUrl);
    }
    for (const d of docs) expect(allHrefs.has(d.href)).toBe(true);
  });

  it("yields the empty list (rendered as the typed absence) when none are recorded", () => {
    const bare = minimalDossier({
      sections: OKC_DOSSIER.sections.map((s) => ({
        ...s,
        rows: (s.rows ?? []).map((r) => ({ ...r, documentUrl: undefined })),
        figures: (s.figures ?? []).map((f) => ({
          ...f,
          reconciliation: {
            ...f.reconciliation,
            claims: f.reconciliation.claims.map((c) => ({ ...c, documentUrl: "" })),
          },
        })),
      })),
    });
    expect(documentsToBring(bare)).toEqual([]);
  });
});

describe("the terms strip (K14 §4.11)", () => {
  it("always carries the document's core terms", () => {
    const terms = termsUsedOnPage(OKC_DOSSIER);
    const ids = terms.map((t) => t.id);
    for (const core of ["dossier", "record", "source", "as-of"]) {
      expect(ids).toContain(core);
    }
  });

  it("adds release terms only on a release-bound build — never fabricated", () => {
    const unbound = termsUsedOnPage(OKC_DOSSIER).map((t) => t.id);
    expect(unbound).not.toContain("release");
    expect(unbound).not.toContain("pinned-citation");
    const bound = termsUsedOnPage(OKC_DOSSIER, { releaseBound: true }).map((t) => t.id);
    expect(bound).toContain("release");
    expect(bound).toContain("pinned-citation");
  });

  it("adds the figure terms when the dossier carries material figures, and the record's states", () => {
    const terms = termsUsedOnPage(OKC_DOSSIER).map((t) => t.id);
    // The fixture carries figures (a contested one) and UNRESOLVED gaps.
    for (const id of ["claim", "evidence", "support", "contested", "unresolved"]) {
      expect(terms).toContain(id);
    }
    const bare = minimalDossier({
      sections: OKC_DOSSIER.sections.map((s) => ({
        ...s,
        figures: undefined,
        rows: (s.rows ?? []).map((r) => ({ ...r, absence: undefined })),
      })),
      gaps: [],
    });
    const bareIds = termsUsedOnPage(bare).map((t) => t.id);
    expect(bareIds).not.toContain("claim");
    expect(bareIds).not.toContain("contested");
    expect(bareIds).not.toContain("unresolved");
  });

  it("resolves every term through the glossary — the same entry the popover shows", () => {
    for (const t of termsUsedOnPage(OKC_DOSSIER, { releaseBound: true })) {
      const entry = glossaryTerm(t.id); // throws on an undefined term
      expect(t.term).toBe(entry.term);
      expect(t.plain).toBe(entry.plain);
      expect(t.anchor.length).toBeGreaterThan(0);
    }
  });
});

describe("the page plan (SIG-UI-155, DR-K14-21)", () => {
  it("orders brief → declared figures → sections → terms, stamping n/total", () => {
    const pages = planPrintPages(OKC_DOSSIER, { releaseBound: true });
    expect(pages[0]!.kind).toBe("brief");
    // The fixture declares one map figure → page 2 (K13: the map leads its own page).
    expect(pages[1]!.kind).toBe("figures");
    expect(pages.at(-1)!.kind).toBe("terms");
    const sectionPages = pages.filter((p) => p.kind === "sections");
    expect(sectionPages).toHaveLength(Math.ceil(12 / 3));
    pages.forEach((p, i) => {
      expect(p.n).toBe(i + 1);
      expect(p.total).toBe(pages.length);
    });
    // Every page carries content — no orphan pages.
    for (const p of pages) {
      if (p.kind === "sections") expect(p.sections.length).toBeGreaterThan(0);
      if (p.kind === "terms") expect(p.terms.length).toBeGreaterThan(0);
    }
  });

  it("emits no figure pages when the dossier declares none", () => {
    const pages = planPrintPages(minimalDossier({ print_figures: undefined }));
    expect(pages.some((p) => p.kind === "figures")).toBe(false);
  });

  it("fails closed on an undeclared kind reaching the plan", () => {
    expect(() =>
      planPrintPages(
        minimalDossier({ print_figures: [{ kind: "chart", title: "x" }] }),
      ),
    ).toThrow(PRINT_FIGURE_CONTRACT);
  });
});
