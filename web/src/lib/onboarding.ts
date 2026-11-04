// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * P36.64 (UXK14-6; DR-K14-03/04 → SIG-UI-137/138; K14 §2.3 rows 2+5, §6.1/6.2)
 * — the onboarding model the home page renders: the golden place, the three
 * persona start-here paths, and the generated example questions.
 *
 * Everything here is bound to the release: the golden place is SELECTED from
 * the dossiers this build serves (never named by hand), a persona step links
 * only a route the release emits, and an example question is emitted only
 * when its example contract (K14 §6.2) holds against the release's own data —
 * a target that does not satisfy the contract is simply never offered
 * (SIG-ENG-042: an empty surface fails, it is never padded).
 */

import { getDossierIndex, getDossiers, getWatchV2 } from "./data";
import { withBase } from "./paths";
import type { Dossier } from "./dossier";
import { dossierPath } from "./dossier";
import { councilDecision } from "./print";
import { dossierDisplayTitle } from "./jurisdictions";

// ---------------------------------------------------------------- golden ---

export interface GoldenFact {
  /** The fact's plain label (the figure or row label). */
  label: string;
  /** The rendered value (unit grouped in at render). */
  value: string;
  /** JSON-pointer rest (inside the dossier artifact) for figure provenance. */
  pointerRest: string;
}

export interface GoldenPlace {
  /** The emitted dossier link (withBase'd — renders under any base). */
  href: string;
  /** The dossier's route id, sans base — slug derivation and figure paths use
   *  this, never the emitted href. */
  route: string;
  /** The reader-facing name. */
  name: string;
  /** The dossier's raw jurisdiction key (the page resolves displayTitle). */
  jurisdiction: string;
  /** The dossier's subject line. */
  subject: string;
  /** The named source families the record joins (≥ 3 to qualify). */
  sources: readonly string[];
  /** Up to three joined facts (figure values first, then notable rows). */
  facts: GoldenFact[];
  /** One real disagreement — the contested figure's label + its sides. */
  disagreement: { label: string; sides: { text: string; pointerRest: string }[] } | null;
  /** The next decision date or its typed absence (SIG-UI-014b). */
  decision: { date: string } | { absence: string };
}

/**
 * Is `d` a joined dossier the golden card may stand on? K14's bar: ≥ 3
 * sources behind it and ≥ 1 real disagreement (a contested figure whose
 * reconciliation names competing claims).
 */
function isJoined(d: Dossier): boolean {
  return (d.source_families?.length ?? 0) >= 3 && firstDisagreement(d) !== null;
}

function firstDisagreement(d: Dossier): GoldenPlace["disagreement"] {
  for (const [si, s] of d.sections.entries()) {
    for (const [fi, f] of (s.figures ?? []).entries()) {
      if (f.contested !== true) continue;
      const claims = f.reconciliation?.claims ?? [];
      const sides = claims.map((c, ci) => ({
        text: `${String(c.value)} ${f.unit ?? ""}`.trim() + ` — ${c.source}`,
        pointerRest: `/sections/${si}/figures/${fi}/reconciliation/claims/${ci}/value`,
      }));
      return { label: f.label, sides };
    }
  }
  return null;
}

/** Up to three joined facts — figure values first, then valued rows. */
function goldenFacts(d: Dossier, max = 3): GoldenFact[] {
  const out: GoldenFact[] = [];
  for (const [si, s] of d.sections.entries()) {
    for (const [fi, f] of (s.figures ?? []).entries()) {
      if (out.length >= max) break;
      if (f.value === null || f.value === undefined) continue;
      out.push({
        label: f.label,
        value: `${String(f.value)} ${f.unit ?? ""}`.trim(),
        pointerRest: `/sections/${si}/figures/${fi}/value`,
      });
    }
    for (const [ri, r] of (s.rows ?? []).entries()) {
      if (out.length >= max) break;
      if (r.value === null || r.value === undefined || r.value === "") continue;
      out.push({ label: r.label, value: String(r.value), pointerRest: `/sections/${si}/rows/${ri}/value` });
    }
  }
  return out;
}

/**
 * The golden place for this release — the first joined dossier (≥3 named
 * sources + a recorded disagreement), or `null` when none exists. `null` is
 * the honest state: the "See an example" section is omitted, never faked
 * (K14 §2.3 row 5, C5 §6), and persona steps fall back to the place search.
 */
export function goldenPlace(dossiers: readonly Dossier[] = getDossiers()): GoldenPlace | null {
  const d = dossiers.find(isJoined);
  if (!d) return null;
  const decision = councilDecision(d);
  return {
    href: withBase(dossierPath(d.slug)),
    route: dossierPath(d.slug),
    name: dossierDisplayTitle(d.subject_label, d.jurisdiction),
    jurisdiction: d.jurisdiction,
    subject: d.subject_label,
    sources: d.source_families ?? [],
    facts: goldenFacts(d),
    disagreement: firstDisagreement(d),
    decision: decision.date ? { date: decision.date } : { absence: decision.absence ?? "Not recorded in SIG" },
  };
}

// --------------------------------------------------------------- personas ---

export interface PersonaStep {
  /** The step's plain label. */
  label: string;
  /** The route it links — always a route the release emits (withBase joins at render). */
  href: string;
}

export interface PersonaPath {
  /** The persona id (advocate | journalist | organizer). */
  id: "advocate" | "journalist" | "organizer";
  /** The card's plain title — the reader's own words (K14 §6.1). */
  title: string;
  /** The persona name. */
  persona: string;
  /** 3–4 linked steps whose targets resolve on the release. */
  steps: PersonaStep[];
}

/**
 * The three co-primary-persona start-here paths (K14 §6.1 verbatim structure).
 * Step targets bind to the golden place where the contract names one ("read
 * the dossier", "print the brief", "check a disagreement") and to the place
 * search / dossier index otherwise — a step never lands on an absent surface
 * (K14 §6.1 "no dead ends").
 */
export function personaPaths(
  golden: GoldenPlace | null = goldenPlace(),
  routes?: ReadonlySet<string>,
): PersonaPath[] {
  const dossier = golden?.href ?? withBase("dossier/");
  const print = golden ? `${golden.href}print/` : withBase("dossier/");
  const has = (route: string) => routes === undefined || routes.has(route);
  const watch = has("watch/") ? withBase("watch/") : null;
  const queue = has("research-queue/") ? withBase("research-queue/") : null;
  const data = has("data/") ? withBase("data/") : withBase("sources/");
  const paths: PersonaPath[] = [
    {
      id: "advocate",
      title: "I have a council meeting coming up", // copy: PC-01
      persona: "local advocate",
      steps: [
        { label: "Find your place", href: withBase("#hero-search") },
        { label: 'Read "At a glance" and "What we don\'t know"', href: `${dossier}#sec-at_a_glance` },
        { label: "Print the council brief", href: print },
        { label: "Bring the listed documents; request the top missing one", href: queue ?? withBase("research-queue/") },
      ],
    },
    {
      id: "journalist",
      title: "I'm checking a figure or a claim", // copy: PC-02
      persona: "investigative journalist",
      steps: [
        { label: "Search an agency or vendor", href: withBase("#hero-search") },
        { label: "Open its page; follow a figure to its sources", href: dossier },
        { label: "Check whether sources disagree", href: `${dossier}#sec-what_is_deployed` },
        { label: "Cite a pinned URL or download the rows", href: data },
      ],
    },
    {
      id: "organizer",
      title: "I'm organizing in my area", // copy: PC-03
      persona: "organizer",
      steps: [
        { label: "Find your county or city", href: withBase("#hero-search") },
        { label: "See who runs what, and who they share with", href: dossier },
        { label: "Subscribe to upcoming decisions", href: watch ?? withBase("watch/") },
        { label: "Pick an open question to help answer", href: queue ?? withBase("research-queue/") },
      ],
    },
  ];
  return paths;
}

// --------------------------------------------------------------- examples ---

export interface ExampleQuestion {
  /** The generated question text. */
  question: string;
  /** The route that answers it (withBase joins at render). */
  href: string;
  /** The contract leg that admitted it — the template id. */
  template: string;
  /** `data-testid` hook for the contract e2e. */
  testId: string;
}

interface ExampleCandidate {
  template: string;
  question: string;
  href: string;
}

/**
 * The fixed K14 §6.2 templates, applied to the release's own data. Each
 * candidate is emitted only when its contract holds: the target route exists
 * (the dossier/watch page is emitted), the target carries the answer element
 * (sources ≥ 2, a contested figure, the gap section — always present), the
 * phrasing names a real display label, and no UUID or raw key appears
 * (display names only — a jkey/slug never renders).
 */
export function exampleQuestions(
  limit = 3,
  dossiers: readonly Dossier[] = getDossiers(),
): ExampleQuestion[] {
  const out: ExampleQuestion[] = [];
  const watch = getWatchV2();
  const watchKeys = new Set(watch.items.map((i) => i.place?.key).filter(Boolean));
  const seen = new Set<string>();
  const push = (c: ExampleCandidate | null) => {
    if (c === null || out.length >= limit) return;
    if (seen.has(c.href)) return; // one example per target — no duplicate chips
    seen.add(c.href);
    out.push({
      question: c.question,
      href: c.href,
      template: c.template,
      testId: `example-${c.template}`,
    });
  };

  // Order: the disagreement example is the differentiator first, then the
  // place record, then the open question — each against the FIRST dossier
  // whose data satisfies the contract.
  const joined = dossiers.find((d) => (d.source_families?.length ?? 0) >= 3 && d.sections.some((s) => (s.figures ?? []).some((f) => f.contested)));
  if (joined) {
    push({
      template: "disagree",
      question: `Where do sources disagree about ${joined.display_name ?? joined.jurisdiction}?`,
      href: `${withBase(dossierPath(joined.slug))}#sec-what_is_deployed`,
    });
  }
  const multi = dossiers.find((d) => (d.source_families?.length ?? 0) >= 2);
  if (multi) {
    push({
      template: "recorded",
      question: `What is recorded in ${multi.display_name ?? multi.jurisdiction}?`,
      href: withBase(dossierPath(multi.slug)),
    });
  }
  const watched = dossiers.find((d) => d.jurisdiction_key && watchKeys.has(d.jurisdiction_key));
  if (watched) {
    push({
      template: "decision",
      question: `What's up for a decision in ${watched.display_name ?? watched.jurisdiction}?`,
      href: withBase(dossierPath(watched.slug)),
    });
  }
  const gaps = dossiers.find((d) => (d.gaps?.length ?? 0) > 0);
  if (gaps) {
    push({
      template: "unknown",
      question: `What doesn't SIG know about ${gaps.display_name ?? gaps.jurisdiction}?`,
      href: `${withBase(dossierPath(gaps.slug))}#sec-what_we_dont_know`,
    });
  }
  return out.slice(0, limit);
}
