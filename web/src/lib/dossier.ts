// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * The local dossier — the project's primary public artifact (§39.2), as pure data
 * + logic. This is the PRODUCTION dossier content contract (SIG-UI-010..015); it
 * supersedes the P06.1 slice renderer (`exports/src/exports/dossier.py`, ADR-032),
 * rebuilt on P15.1's epistemic visual language and a11y/no-JS baseline.
 *
 * This module owns, colour-free (colour lives only in `styles/epistemic.css`):
 *   - the twelve §39.2 sections in their exact order + a validator (SIG-UI-010);
 *   - the "what we don't know" gap model, surfaced in the summary, the print export,
 *     and the API (SIG-UI-011);
 *   - the incompleteness banner (count of unresearched fields + the absence rule,
 *     SIG-UI-012);
 *   - the expandable reconciliation behind every material figure (SIG-UI-014);
 *   - the three action blocks the outline omits — `authorization`,
 *     `termination_mechanics`, `legal_regime` (SIG-UI-014a);
 *   - the derived `next_decision_date` (SIG-UI-014b), a STABLE wire name the renewal
 *     watch (P15.4, §39.5) keys its alerts on — treat it as an interface contract;
 *   - the Appendix-B content contract, where an `unknown` value renders as "unknown"
 *     rather than being omitted (SIG-UI-015).
 *
 * The rendering (`pages/dossier/*`) and the API endpoint (`dossier/[slug].json.ts`)
 * both derive from `renderDossierJson`, so the HTML summary, the print export, and
 * the JSON API can never drift out of the SIG-UI-011 contract.
 */

import { ABSENCE_KIND_META } from "./epistemic";
import type { AbsenceKind, CompetingClaim, Support } from "./epistemic";
import { beliefPinnedPermalink } from "./citation";
import type { AsOfEcho } from "./fixtures";
import type { AbsenceTaskParams } from "./task";

// --- SIG-UI-010: the twelve sections, in the exact §39.2 order ---------------

/** The twelve dossier sections, `[id, title]`, in the exact §39.2 order. */
export const SECTION_ORDER: readonly (readonly [string, string])[] = [
  ["at_a_glance", "At a glance"],
  ["what_is_deployed", "What is deployed"],
  ["cost_and_expiry", "Cost and expiry"],
  ["who_else_can_see", "Who else can see the data"],
  ["configuration_and_retention", "Configuration and retention"],
  ["usage", "Usage"],
  ["where_the_hardware_is", "Where the hardware is"],
  ["policy", "Policy"],
  ["accountability_events", "Accountability events"],
  ["timeline", "Timeline"],
  ["what_we_dont_know", "What we don't know"],
  ["how_we_know_this", "How we know this"],
] as const;

export const SECTION_IDS: readonly string[] = SECTION_ORDER.map(([id]) => id);
export const SECTION_TITLES: Record<string, string> = Object.fromEntries(SECTION_ORDER);

// --- Reconciliation behind a material figure (SIG-UI-014) --------------------

/**
 * The expandable reconciliation for a material figure: the rule that fired, the
 * competing claims (each with its source, tier, date, and a link to the document
 * at its supporting locator), and which claim won. Reuses the shared
 * `CompetingClaim` shape so the dossier's reconciliation and the contradiction
 * range render the same evidence (SIG-UI-009/014).
 */
export interface Reconciliation {
  /** The resolver rule that fired, e.g. "HIGHEST_TIER_WINS". */
  rule: string;
  /** The `claimId` of the winning claim within `claims`. */
  winningClaimId: string;
  claims: CompetingClaim[];
  /** A plain-language note (the local advocate is the design center). */
  note?: string;
}

/** A material figure — always expandable to its reconciliation (SIG-UI-014). */
export interface Figure {
  key: string;
  label: string;
  value: string | number;
  unit?: string;
  /** True when the value is a lower bound (e.g. mapped-device count, §D.2). */
  lowerBound?: boolean;
  support: Support;
  /** Independent evidence-class count behind the winning value (SIG-UI-003). */
  evidenceCount: number;
  /** Whether the value is contested (drives the persistent marker, SIG-UI-008). */
  contested: boolean;
  reconciliation: Reconciliation;
}

// --- The Appendix-B content contract row (SIG-UI-015) ------------------------

/**
 * A non-figure fact. `value === null` with no `absence` renders explicitly as
 * "unknown" — never omitted (SIG-UI-015). A row with an `absence` kind is a
 * clickable gap (rendered as the single hatch, SIG-UI-007) and, when
 * `NOT_RESEARCHED`, counts toward the incompleteness banner (SIG-UI-012).
 */
export interface Row {
  label: string;
  value: string | number | null;
  /** When set, this field is a gap: rendered as the absence hatch, clickable to a task. */
  absence?: AbsenceKind;
  /** For a taskable absence row, the subject/predicate the hatch links with. */
  subject_id?: string;
  predicate_id?: string;
  /** A link to the supporting document at its locator (SIG-UI-014). */
  documentUrl?: string;
  note?: string;
}

/** The explicit display string for a row value (SIG-UI-015: "unknown", not omitted). */
export function rowDisplayValue(row: Row): string {
  if (row.absence) return ABSENCE_KIND_META[row.absence].label;
  return row.value === null ? "unknown" : String(row.value);
}

export interface Section {
  section_id: string;
  figures?: Figure[];
  rows?: Row[];
}

/** One entry of "what we don't know" (SIG-UI-011); its kind is one of the four (§9.5). */
export interface Gap {
  label: string;
  kind: AbsenceKind;
  subject_id: string;
  predicate_id: string;
  /** For NO_EVIDENCE_FOUND: the named sources searched (§9.5, SIG-TIME-011). */
  sources_searched?: string[];
  note?: string;
}

// --- The three action blocks the outline omits (SIG-UI-014a) -----------------

/**
 * Who authorized the deployment, and how. "Approved 7–0 after public comment" and
 * "passed unopposed on the consent agenda" are politically opposite facts, so the
 * consent-agenda flag and the public-comment flag are first-class (SIG-UI-014a).
 */
export interface Authorization {
  approving_body: string | null;
  vote: string | null;
  consent_agenda: boolean | null;
  public_comment: boolean | null;
  date: string | null;
}

/**
 * The raw termination inputs. `next_decision_date` is DERIVED from these
 * (`resolveTermination`), never stored, so it can never disagree with the inputs.
 */
export interface TerminationInput {
  auto_renews: boolean;
  notice_window_days: number | null;
  expiry_date: string | null;
}

/** Termination mechanics with the derived decision date (SIG-UI-014a/b). */
export interface TerminationMechanics extends TerminationInput {
  /** The decision date, not the expiry date — surfaced wherever expiry is (SIG-UI-014b). */
  next_decision_date: string | null;
}

export interface LegalRegime {
  state_statute: string | null;
  local_ordinance: string | null;
  disclosure_duties: string[];
}

/**
 * The renewal decision date (SIG-UI-014b). An expiry date is the WRONG figure to
 * surface: a contract expiring 2027-04-02 with auto-renewal and a 90-day notice
 * window has a real deadline of 2027-01-02 — after which the decision is made by
 * default. So when the contract auto-renews, the decision date is the expiry minus
 * the notice window; otherwise the decision must be taken by the expiry itself.
 * The renewal watch (P15.4, §39.5) keys its alerts on this exact value.
 */
export function nextDecisionDate(t: TerminationInput): string | null {
  if (!t.expiry_date) return null;
  if (t.auto_renews && t.notice_window_days !== null) {
    return subtractDays(t.expiry_date, t.notice_window_days);
  }
  return t.expiry_date;
}

/** Resolve the raw termination inputs into the full block with its derived date. */
export function resolveTermination(t: TerminationInput): TerminationMechanics {
  return { ...t, next_decision_date: nextDecisionDate(t) };
}

/** Subtract whole days from an ISO date (UTC), returning an ISO `YYYY-MM-DD`. */
function subtractDays(isoDate: string, days: number): string {
  const ms = Date.parse(`${isoDate}T00:00:00Z`);
  if (Number.isNaN(ms)) throw new Error(`invalid ISO date: "${isoDate}"`);
  const d = new Date(ms - days * 86_400_000);
  return d.toISOString().slice(0, 10);
}

// --- The dossier itself ------------------------------------------------------

export interface Dossier {
  slug: string;
  subject_label: string;
  jurisdiction: string;
  asOf: AsOfEcho;
  rulesetVersion: string;
  sections: Section[];
  gaps: Gap[];
  source_families: string[];
  authorization: Authorization;
  termination: TerminationInput;
  legal_regime: LegalRegime;
}

/** The canonical page path for a dossier (trailing slash — SIG-UI-035). */
export function dossierPath(slug: string): string {
  return `/dossier/${slug}/`;
}

/** The canonical path of a dossier's print export. */
export function dossierPrintPath(slug: string): string {
  return `/dossier/${slug}/print/`;
}

/** The canonical path of a dossier's static JSON (API-form) endpoint. */
export function dossierJsonPath(slug: string): string {
  return `/dossier/${slug}.json`;
}

/**
 * The count of DISTINCT unresearched fields the incompleteness banner names
 * (SIG-UI-012): every `NOT_RESEARCHED` gap plus every section row that is a
 * `NOT_RESEARCHED` absence, deduplicated by `(subject_id, predicate_id)` so a field
 * elevated to the "what we don't know" headline AND shown in its section is counted
 * once. "No evidence found" is NOT unresearched — SIG looked — so it is excluded.
 */
export function unresearchedFieldCount(dossier: Dossier): number {
  const keys = new Set<string>();
  for (const g of dossier.gaps) {
    if (g.kind === "NOT_RESEARCHED") keys.add(`${g.subject_id}\u0000${g.predicate_id}`);
  }
  for (const s of dossier.sections) {
    for (const r of s.rows ?? []) {
      if (r.absence === "NOT_RESEARCHED") {
        keys.add(`${r.subject_id ?? dossier.slug}\u0000${r.predicate_id ?? r.label}`);
      }
    }
  }
  return keys.size;
}

/** The explicit incompleteness banner (SIG-UI-012): count + the absence rule. */
export function incompletenessBanner(dossier: Dossier): string {
  const n = unresearchedFieldCount(dossier);
  return (
    `This dossier has ${n} unresearched field${n === 1 ? "" : "s"}. ` +
    "The absence of a row is not evidence of absence."
  );
}

/** The belief-pinned permalink for a dossier page (SIG-UI-035). */
export function dossierPermalink(dossier: Dossier, origin?: string): string {
  return beliefPinnedPermalink({
    path: dossierPath(dossier.slug),
    title: dossier.subject_label,
    asOf: dossier.asOf,
    rulesetVersion: dossier.rulesetVersion,
    ...(origin ? { origin } : {}),
  });
}

/**
 * Validate the §39.2 section contract (SIG-UI-010): the sections MUST be exactly
 * the twelve ids in the canonical order. Throws otherwise, so a mis-ordered or
 * incomplete dossier can never render.
 */
export function validateDossier(dossier: Dossier): void {
  const got = dossier.sections.map((s) => s.section_id);
  const want = SECTION_IDS;
  const ok = got.length === want.length && got.every((id, i) => id === want[i]);
  if (!ok) {
    throw new Error(
      `dossier sections must be exactly the §39.2 order (SIG-UI-010); got ${JSON.stringify(got)}`,
    );
  }
}

// --- The API form (SIG-UI-011): one source of truth for all three surfaces ---

/**
 * The dossier's API (JSON) representation. Because the shell is static-first
 * (SIG-UI-036) it is emitted as a committed static endpoint at build time
 * (`dossier/[slug].json.ts`), not read from a live API — but the shape is the
 * `/v1` dossier contract. Critically, "what we don't know" appears BOTH at the
 * summary top level (`what_we_dont_know`) AND inside the sections, so the API,
 * the print export, and the HTML summary all satisfy SIG-UI-011.
 */
export function renderDossierJson(dossier: Dossier, origin?: string): Record<string, unknown> {
  validateDossier(dossier);
  const permalink = dossierPermalink(dossier, origin);
  return {
    subject: dossier.subject_label,
    jurisdiction: dossier.jurisdiction,
    as_of_world: dossier.asOf.as_of_world,
    as_of_belief: dossier.asOf.as_of_belief,
    ruleset_version: dossier.rulesetVersion,
    permalink,
    incompleteness_banner: incompletenessBanner(dossier),
    unresearched_field_count: unresearchedFieldCount(dossier),
    // "What we don't know" is a headline feature, at the summary top level AND
    // rendered inside its section on the page/print (SIG-UI-011).
    what_we_dont_know: dossier.gaps.map((g) => ({
      label: g.label,
      kind: g.kind,
      subject_id: g.subject_id,
      predicate_id: g.predicate_id,
      ...(g.sources_searched ? { sources_searched: g.sources_searched } : {}),
      ...(g.note ? { note: g.note } : {}),
    })),
    // The three action blocks the outline omits (SIG-UI-014a), with the derived
    // decision date (SIG-UI-014b) computed once, here.
    authorization: dossier.authorization,
    termination_mechanics: resolveTermination(dossier.termination),
    legal_regime: dossier.legal_regime,
    sections: dossier.sections.map((s) => ({
      id: s.section_id,
      title: SECTION_TITLES[s.section_id],
      figures: (s.figures ?? []).map(figureJson),
      rows: (s.rows ?? []).map(rowJson),
    })),
    source_families: dossier.source_families,
  };
}

function figureJson(fig: Figure): Record<string, unknown> {
  const winning = fig.reconciliation.claims.find((c) => c.claimId === fig.reconciliation.winningClaimId);
  return {
    key: fig.key,
    label: fig.label,
    value: fig.value,
    unit: fig.unit ?? "",
    lower_bound: fig.lowerBound ?? false,
    support: fig.support,
    evidence_count: fig.evidenceCount,
    contested: fig.contested,
    reconciliation: {
      rule: fig.reconciliation.rule,
      note: fig.reconciliation.note ?? "",
      winning_claim_id: fig.reconciliation.winningClaimId,
      // The winning claim first, then the competing claims — each with tier, date,
      // and a document link at its locator (SIG-UI-014).
      claims: fig.reconciliation.claims.map((c) => ({
        claim_id: c.claimId,
        value: c.value,
        source: c.source,
        tier: c.tier,
        date: c.date,
        document_url: c.documentUrl,
        winning: c.claimId === fig.reconciliation.winningClaimId,
        ...(c.differentQuantityNote ? { different_quantity_note: c.differentQuantityNote } : {}),
      })),
      winning_present: winning !== undefined,
    },
  };
}

function rowJson(row: Row): Record<string, unknown> {
  return {
    label: row.label,
    value: row.value,
    display_value: rowDisplayValue(row),
    ...(row.absence ? { absence_kind: row.absence } : {}),
    ...(row.documentUrl ? { document_url: row.documentUrl } : {}),
    ...(row.note ? { note: row.note } : {}),
  };
}

/**
 * Every taskable absence a dossier links a hatch to — its "what we don't know"
 * gaps plus every section row that is an absence — as `AbsenceTaskParams`. The
 * task-intake route (`pages/task/new/[slug].astro`) unions these into its
 * `getStaticPaths` so every clickable dossier gap resolves to a real, pre-generated
 * intake page with no client JavaScript (SIG-UI-007, SIG-UI-036/037).
 */
export function dossierTaskableAbsences(dossier: Dossier): AbsenceTaskParams[] {
  const fromGaps: AbsenceTaskParams[] = dossier.gaps.map((g) => ({
    subject_id: g.subject_id,
    predicate_id: g.predicate_id,
    absence_kind: g.kind,
    predicate_label: g.label,
  }));
  const fromRows: AbsenceTaskParams[] = dossier.sections.flatMap((s) =>
    (s.rows ?? [])
      .filter((r): r is Row & { absence: AbsenceKind } => r.absence !== undefined)
      .map((r) => ({
        subject_id: r.subject_id ?? dossier.slug,
        predicate_id: r.predicate_id ?? r.label,
        absence_kind: r.absence,
        predicate_label: r.label,
      })),
  );
  return [...fromGaps, ...fromRows];
}
