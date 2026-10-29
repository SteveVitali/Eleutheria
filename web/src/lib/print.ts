// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * P36.26 (K14 UXK14-9 / K14 §4.10–4.11, SIG-UI-098/130/155): the print
 * document's composition model — everything the `.astro` file renders comes
 * from here so the layout is testable without a build.
 *
 * The contract, distilled from K14 §4.10/§4.11 and DR-K14-21:
 *
 *   - page 1 is the COUNCIL BRIEF: the place's name, what is recorded and what
 *     is unknown at a glance, the next decision date (or its typed absence),
 *     three to five documents to bring, and a static QR back to the pinned
 *     permalink (generated at build — `lib/qr.ts`, no runtime dependency);
 *   - every page carries a running head (place) and a running footer (as-of,
 *     release, permalink, licence, page n of N) — the K14-documented in-flow
 *     fallback, see `styles/print.css` for the @page margin-box note;
 *   - the dossier's popover terms collapse into a "Terms used" list on the
 *     last page (a paper reader cannot hover);
 *   - every declared print figure renders on its own page — SIG-UI-130 —
 *     through the ONE data contract `sig.print-figure/1` (declaration kinds
 *     `map | extent | trend | axis`); no declaration → no visual, never a
 *     fabricated map.
 */

import type { Dossier, Section } from "./dossier";
import { dossierFieldAudit, dossierUnknowns, resolveTermination } from "./dossier";
import type { DossierUnknowns } from "./dossier";
import { glossaryTerm, LEXICON } from "./lexicon";

/** Every state enum value the lexicon declares, across all state fields. */
const ALL_STATE_IDS = new Set(
  Object.values(LEXICON.states).flatMap((field) => Object.keys(field)),
);

// ---------------------------------------------------------------------------
// sig.print-figure/1 — the declared print-visual contract.
// ---------------------------------------------------------------------------

/** The one declared contract id. */
export const PRINT_FIGURE_CONTRACT = "sig.print-figure/1" as const;

/**
 * The declared print-figure kinds. `map` and `extent` are geography classes
 * (P36.27 owns the real static kit — a declaration without renderable
 * geography emits the honest placeholder, never a fabricated map); `trend`
 * and `axis` are the deployment classes (P36.28's kit). `state` carries the
 * epistemic state chip when the figure's placement is contested/unresolved.
 */
export const PRINT_FIGURE_KINDS = ["map", "extent", "trend", "axis"] as const;
export type PrintFigureKind = (typeof PRINT_FIGURE_KINDS)[number];

/** One declared print visual (`dossier.print_figures[]`). */
export interface PrintFigureDecl {
  kind: PrintFigureKind;
  /** The figure title ("Placement of recorded sites"). */
  title: string;
  /** The epistemic state the slot marks, when the figure is a contested value. */
  state?: string;
  /** A one-line note the placeholder renders (the honest stand-in wording). */
  note?: string;
}

/**
 * Fail-closed validation for a declaration (SIG-ENG-042): an unknown kind,
 * an empty title, or a `state` that is not a lexicon state all throw at
 * build — the print page can never ship a silent visual.
 */
export function assertPrintFigures(
  decls: readonly { kind: string; title: string; state?: string }[],
  slug: string,
): void {
  for (const d of decls) {
    if (!(PRINT_FIGURE_KINDS as readonly string[]).includes(d.kind)) {
      throw new Error(
        `${PRINT_FIGURE_CONTRACT}: dossier "${slug}" declares an unknown print-figure ` +
          `kind "${d.kind}" (${PRINT_FIGURE_KINDS.join(" | ")} only)`,
      );
    }
    if (!d.title?.trim()) {
      throw new Error(`${PRINT_FIGURE_CONTRACT}: dossier "${slug}" declares a print figure with no title`);
    }
    if (d.state !== undefined && !ALL_STATE_IDS.has(d.state)) {
      throw new Error(
        `${PRINT_FIGURE_CONTRACT}: dossier "${slug}" declares state "${d.state}" — not a lexicon state`,
      );
    }
  }
}

// ---------------------------------------------------------------------------
// The council-brief model (page 1).
// ---------------------------------------------------------------------------

/** "What is recorded / what is unknown, at a glance" (K14 §4.10). */
export interface RecordedGlance {
  /** Fields carrying a visible value (a withheld field counts as not shown). */
  recorded: number;
  /** Every field the dossier poses (rows + gaps + the action-block fields). */
  total: number;
  /** The full unknown breakdown (the banner's contract, reused verbatim). */
  unknowns: DossierUnknowns;
}

export function recordedGlance(dossier: Dossier): RecordedGlance {
  const audit = dossierFieldAudit(dossier);
  return {
    recorded: audit.allFields.size - audit.kinds.size - audit.withheld,
    total: audit.allFields.size,
    unknowns: dossierUnknowns(dossier),
  };
}

/**
 * The council-brief decision line (K14 §4.10): the derived
 * `next_decision_date` when the contract records one, else the typed absence
 * — "not recorded" is the honest absence, never a fabricated date and never
 * a bare omission (§3.1).
 */
export interface CouncilDecision {
  /** The derived decision date (ISO) when recorded. */
  date: string | null;
  /** The typed absence label when no date is recorded. */
  absence: string | null;
  /** What the date is derived from, so the brief can say why it is a decision. */
  basis: "renewal-or-expiry" | null;
}

export function councilDecision(dossier: Dossier): CouncilDecision {
  const t = resolveTermination(dossier.termination);
  if (t.next_decision_date) {
    return { date: t.next_decision_date, absence: null, basis: "renewal-or-expiry" };
  }
  return { date: null, absence: "Not recorded in SIG", basis: null };
}

/** A document on the council-brief bring list — a real locator from the record. */
export interface PrintDocument {
  /** What the document supports (the row's label or the claim's source). */
  label: string;
  /** The supporting document's locator (printed as text — paper cannot click). */
  href: string;
}

const DOCUMENTS_MAX = 5;

/**
 * The "documents to bring" list (K14 §4.10, 3–5 entries): the unique
 * supporting-document locators the record actually carries — row
 * `documentUrl`s and reconciliation-claim document links, in dossier order,
 * deduplicated by locator. When the record carries none the list is empty
 * and the brief renders the typed absence — never a padded or invented
 * document.
 */
export function documentsToBring(dossier: Dossier): PrintDocument[] {
  const out: PrintDocument[] = [];
  const seen = new Set<string>();
  const push = (label: string, href: string | undefined) => {
    if (!href || seen.has(href) || out.length >= DOCUMENTS_MAX) return;
    seen.add(href);
    out.push({ label, href });
  };
  for (const s of dossier.sections) {
    for (const r of s.rows ?? []) push(r.label, r.documentUrl);
    for (const f of s.figures ?? []) {
      for (const c of f.reconciliation.claims) push(c.source, c.documentUrl);
    }
  }
  return out;
}

// ---------------------------------------------------------------------------
// "Terms used" — the printed glossary strip (K14 §4.11).
// ---------------------------------------------------------------------------

export interface PrintTerm {
  /** The lexicon term id. */
  id: string;
  /** The term's display text (same word the popover shows). */
  term: string;
  /** The plain definition — the same sentence the popover carries. */
  plain: string;
  /** The `/glossary/` fragment anchor. */
  anchor: string;
}

/**
 * The terms the printed document actually uses (K14 §4.11): the popover
 * `<Term>` chips on the live page collapse to this build-time list on the
 * paper — same shared vocabulary, no JavaScript, glossary anchors kept. The
 * set is derived from the dossier's content (never a hand list that can
 * drift): core document terms always; `release`/`pinned-citation` when the
 * build is release-bound; `claim`/`evidence`/`support` when the dossier
 * carries material figures; `contested`/`unresolved` when the record marks
 * them.
 */
export function termsUsedOnPage(dossier: Dossier, opts: { releaseBound?: boolean } = {}): PrintTerm[] {
  const ids = new Set<string>(["dossier", "record", "source", "as-of"]);
  if (opts.releaseBound) {
    ids.add("release");
    ids.add("pinned-citation");
  }
  const figures = dossier.sections.flatMap((s) => s.figures ?? []);
  if (figures.length > 0) {
    ids.add("claim");
    ids.add("evidence");
    ids.add("support");
  }
  if (figures.some((f) => f.contested)) ids.add("contested");
  const unresolvedGap = dossier.gaps.some((g) => g.kind === "UNRESOLVED");
  const unresolvedRow = dossier.sections.some((s) =>
    (s.rows ?? []).some((r) => r.absence === "UNRESOLVED"),
  );
  if (unresolvedGap || unresolvedRow) ids.add("unresolved");
  // The lexicon's term order is the canonical ordering — stable across builds.
  const order = new Map(LEXICON.terms.map((t, i) => [t.id, i]));
  return [...ids]
    .sort((a, b) => (order.get(a) ?? 1e9) - (order.get(b) ?? 1e9))
    .map((id) => {
      const entry = glossaryTerm(id); // throws on an undefined term — build fails
      return { id, term: entry.term, plain: entry.plain, anchor: entry.anchor };
    });
}

// ---------------------------------------------------------------------------
// The page plan.
// ---------------------------------------------------------------------------

/**
 * One composed print page. `brief` is always first; each declared print
 * figure gets its own page (`figures`); the twelve §39.2 sections paginate
 * after them (`sections`); the terms strip closes the document (`terms`).
 * The renderer stamps `n`/`total` so the running footer reads "Page n of N".
 */
export type PrintPage = {
  n: number;
  total: number;
} & (
  | { kind: "brief" }
  | { kind: "figures"; figure: PrintFigureDecl }
  | { kind: "sections"; sections: Section[] }
  | { kind: "terms"; terms: PrintTerm[] }
);

/**
 * Compose the print document's page plan (SIG-UI-155, DR-K14-21 "no orphan
 * pages"): every page carries real content — the terms strip always holds
 * at least the four core terms so the last page is never empty — and the
 * page count is fully determined by the record (brief + one page per
 * declared figure + the section chunks + the terms page).
 */
export function planPrintPages(
  dossier: Dossier,
  opts: { releaseBound?: boolean; sectionsPerPage?: number } = {},
): PrintPage[] {
  const declared = dossier.print_figures ?? [];
  assertPrintFigures(declared, dossier.slug);
  const figures = declared as PrintFigureDecl[];
  const per = opts.sectionsPerPage ?? 3;
  const pages: PrintPage[] = [{ n: 0, total: 0, kind: "brief" }];
  for (const figure of figures) pages.push({ n: 0, total: 0, kind: "figures", figure });
  for (let i = 0; i < dossier.sections.length; i += per) {
    pages.push({ n: 0, total: 0, kind: "sections", sections: dossier.sections.slice(i, i + per) });
  }
  pages.push({ n: 0, total: 0, kind: "terms", terms: termsUsedOnPage(dossier, opts) });
  pages.forEach((p, i) => {
    p.n = i + 1;
    p.total = pages.length;
  });
  return pages;
}
