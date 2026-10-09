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
import { adapterFor, adapterPublicationPermitted } from "./publication";

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
  /**
   * True when this row's value is a public-employee name — gated by the
   * jurisdiction-conditional publication rule (SIG-PUB-017). See
   * `applyPublicationPolicy`.
   */
  isPublicEmployeeName?: boolean;
  /** The record's origin jurisdiction (defaults to the dossier's own). */
  originJurisdiction?: string;
  /**
   * Set by `applyPublicationPolicy` when the value was withheld under the
   * governing regime — the value is cleared and this flag drives the render.
   */
  withheld?: boolean;
}

/** The explicit display string for a row value (SIG-UI-015: "unknown", not omitted). */
export function rowDisplayValue(row: Row): string {
  if (row.absence) return ABSENCE_KIND_META[row.absence].label;
  if (row.withheld) return "withheld";
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
  /** null = unknown (the record holds no renewal fact) — never defaulted to "no" (§3.1). */
  auto_renews: boolean | null;
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
  /**
   * The dossier-kind marker (P32.17, SIG-DOS-003): "inventory_overview" for the
   * §39.2 machine-built dossier — semantically distinct from the reviewed
   * `sig.research-dossier/1` portfolio. Optional so committed fixtures and older
   * exports stay valid; an unset kind IS the inventory overview.
   */
  kind?: "inventory_overview" | "research_dossier" | string;
  jurisdiction: string;
  asOf: AsOfEcho;
  rulesetVersion: string;
  sections: Section[];
  gaps: Gap[];
  source_families: string[];
  authorization: Authorization;
  termination: TerminationInput;
  legal_regime: LegalRegime;
  /**
   * The BCP-47 language tag the page renders in (SIG-UI localisation). Optional
   * and defaults to "en" so the existing OKC dossier is unchanged (back-compat).
   */
  lang?: string;
  /**
   * The data subject's jurisdiction code (e.g. "US", "FR", "BE"), which selects the
   * §43.8 publication adapter. Defaults to "US" so the existing dossier is unchanged.
   */
  jurisdictionCode?: string;
}

/** The BCP-47 language tag for a dossier (defaults to English). */
export function dossierLang(dossier: Dossier): string {
  return dossier.lang ?? "en";
}

// --- Localised section titles (SIG-UI localisation, §43) ---------------------

/**
 * The twelve §39.2 section titles per language. English is the canonical wire form
 * used by `renderDossierJson`; the page picks the reader's language from the
 * dossier's BCP-47 tag (its primary subtag), falling back to English for any
 * section/language not translated.
 */
export const SECTION_TITLES_BY_LANG: Record<string, Record<string, string>> = {
  en: SECTION_TITLES,
  fr: {
    at_a_glance: "En bref",
    what_is_deployed: "Ce qui est déployé",
    cost_and_expiry: "Coût et échéance",
    who_else_can_see: "Qui d'autre voit les données",
    configuration_and_retention: "Configuration et conservation",
    usage: "Utilisation",
    where_the_hardware_is: "Où se trouve le matériel",
    policy: "Cadre juridique",
    accountability_events: "Événements de responsabilité",
    timeline: "Chronologie",
    what_we_dont_know: "Ce que nous ignorons",
    how_we_know_this: "Comment nous le savons",
  },
  nl: {
    at_a_glance: "In het kort",
    what_is_deployed: "Wat is ingezet",
    cost_and_expiry: "Kosten en vervaldatum",
    who_else_can_see: "Wie de gegevens nog meer ziet",
    configuration_and_retention: "Configuratie en bewaring",
    usage: "Gebruik",
    where_the_hardware_is: "Waar de hardware is",
    policy: "Juridisch kader",
    accountability_events: "Verantwoordingsgebeurtenissen",
    timeline: "Tijdlijn",
    what_we_dont_know: "Wat we niet weten",
    how_we_know_this: "Hoe we dit weten",
  },
};

/** The section titles for a dossier's language, falling back to English per key. */
export function sectionTitlesFor(lang: string): Record<string, string> {
  const primary = lang.split("-")[0] ?? "en";
  const table = SECTION_TITLES_BY_LANG[primary] ?? SECTION_TITLES;
  return { ...SECTION_TITLES, ...table };
}

/**
 * Apply the jurisdiction-conditional publication policy to a dossier at build time
 * (SIG-PUB-017, §44). For every row flagged `isPublicEmployeeName`, the governing
 * adapter (the dossier's `jurisdictionCode`) and the record's origin jurisdiction
 * are checked; when publication is NOT permitted the value is withheld — cleared and
 * marked `withheld` with the governing regime named in a note. This can ONLY ever
 * withhold (Part VIII §0.7): a permitted name is returned unchanged, so the FR/BE
 * dossiers show everything the US one does except the gated name.
 */
export function applyPublicationPolicy(dossier: Dossier): Dossier {
  const adapter = adapterFor(dossier.jurisdictionCode ?? "US");
  const gateRow = (row: Row): Row => {
    if (!row.isPublicEmployeeName) return row;
    const permitted = adapterPublicationPermitted(
      adapter,
      row.originJurisdiction ?? adapter.code,
      { isPublicEmployeeName: true },
    );
    if (permitted) return row;
    return {
      ...row,
      value: null,
      withheld: true,
      note:
        `Public-employee name withheld: not publishable under ${adapter.profile} ` +
        `(SIG-PUB-017).`,
    };
  };
  return {
    ...dossier,
    sections: dossier.sections.map((s) => ({
      ...s,
      ...(s.rows ? { rows: s.rows.map(gateRow) } : {}),
    })),
  };
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
 * The count of DISTINCT unresearched fields (the `NOT_RESEARCHED` subset of
 * {@link dossierUnknowns}): every `NOT_RESEARCHED` gap plus every section row that
 * is a `NOT_RESEARCHED` absence, deduplicated by `(subject_id, predicate_id)` so a
 * field elevated to the "what we don't know" headline AND shown in its section is
 * counted once. "No evidence found" is NOT unresearched — SIG looked — so it is
 * excluded. Kept as its own counter (and wire name) because SIG-UI-012 names the
 * unresearched subset specifically.
 */
export function unresearchedFieldCount(dossier: Dossier): number {
  return dossierUnknowns(dossier).notResearched;
}

/**
 * Which §39.2 section carries which action block (SIG-UI-014a/b). Shared by the
 * dossier page, the print export, and the unknown/empty-section counters so the
 * three can never disagree about where an action block supplies content.
 */
export const SECTION_ACTION_BLOCKS: Record<
  string,
  "authorization" | "termination" | "legal_regime"
> = {
  cost_and_expiry: "termination",
  accountability_events: "authorization",
  policy: "legal_regime",
};

/** The exact sentence an empty dossier section renders — it asserts NO absence kind. */
export const NO_RECORD_IN_SIG = "No record in SIG.";

/** A section body is empty when it carries neither rows nor figures. */
export function sectionIsEmpty(section: Section): boolean {
  return (section.rows ?? []).length === 0 && (section.figures ?? []).length === 0;
}

/**
 * Every field the dossier page cannot answer, broken down honestly (QW-7 /
 * F-136 / F-100). The incompleteness banner must count EVERY unknown, not only
 * the `NOT_RESEARCHED` subset: a bare `null` row rendered as "unknown", a null
 * action-block field, and an `UNRESOLVED` disagreement are all fields with no
 * recorded answer, and the banner must say so. Kinds:
 *
 *   - `notResearched`    — `NOT_RESEARCHED` gaps + absence rows (never looked);
 *   - `noEvidenceFound`  — `NO_EVIDENCE_FOUND` gaps + absence rows (searched,
 *                          nothing found — still an unknown answer);
 *   - `unresolved`       — `UNRESOLVED` gaps + absence rows (evidence disagrees);
 *   - `unknown`          — bare `null` values with no recorded absence kind
 *                          (the data supports no kind — none is asserted, QW-7);
 *   - `withheld`         — values withheld under publication policy (counted
 *                          separately: the value exists but is not shown —
 *                          NOT part of `total`);
 *   - `emptySections`    — §39.2 sections with no rows, no figures, and no
 *                          action block (or "what we don't know" with no gaps).
 *
 * `EVIDENCE_OF_ABSENCE` is a positive finding (the field HAS an answer: "does
 * not exist"), so it is never counted as an unknown. Fields are deduplicated by
 * `(subject_id, predicate_id)` across gaps and rows; when a field is recorded
 * under more than one kind the most-informative kind wins
 * (`NO_EVIDENCE_FOUND` > `UNRESOLVED` > `NOT_RESEARCHED`), so a field is called
 * "not researched" only when nothing more specific is recorded.
 */
export interface DossierUnknowns {
  total: number;
  notResearched: number;
  noEvidenceFound: number;
  unresolved: number;
  /** Bare `null` values (rows AND action-block fields) with no recorded kind. */
  unknown: number;
  /** Values withheld under publication policy — counted separately from `total`. */
  withheld: number;
  emptySections: number;
}

// Per-kind precedence for the dedup: the most-informative recorded kind wins.
const _UNKNOWN_KIND_RANK: Record<string, number> = {
  NOT_RESEARCHED: 0,
  UNRESOLVED: 1,
  NO_EVIDENCE_FOUND: 2,
};

export function dossierUnknowns(dossier: Dossier): DossierUnknowns {
  // kind-keyed dedup over gaps + absence rows + bare-null rows, by field key.
  const kinds = new Map<string, string>();
  const bump = (key: string, kind: string) => {
    const prev = kinds.get(key);
    if (prev === undefined || (_UNKNOWN_KIND_RANK[kind] ?? -1) > (_UNKNOWN_KIND_RANK[prev] ?? -1)) {
      kinds.set(key, kind);
    }
  };
  let withheld = 0;
  for (const g of dossier.gaps) {
    if (g.kind !== "EVIDENCE_OF_ABSENCE") {
      bump(`${g.subject_id}\u0000${g.predicate_id}`, g.kind);
    }
  }
  for (const s of dossier.sections) {
    for (const r of s.rows ?? []) {
      const key = `${r.subject_id ?? dossier.slug}\u0000${r.predicate_id ?? r.label}`;
      if (r.absence) {
        if (r.absence !== "EVIDENCE_OF_ABSENCE") bump(key, r.absence);
      } else if (r.withheld) {
        withheld += 1;
      } else if (r.value === null) {
        bump(key, "UNKNOWN");
      }
    }
  }
  // The action-block fields (SIG-UI-014a): each null renders "unknown" on the
  // page, so each is an unknown field — never defaulted to an invented value.
  const actionNulls: [string, unknown][] = [
    ["authorization.approving_body", dossier.authorization.approving_body],
    ["authorization.vote", dossier.authorization.vote],
    ["authorization.consent_agenda", dossier.authorization.consent_agenda],
    ["authorization.public_comment", dossier.authorization.public_comment],
    ["authorization.date", dossier.authorization.date],
    ["termination.auto_renews", dossier.termination.auto_renews],
    ["termination.notice_window_days", dossier.termination.notice_window_days],
    ["termination.expiry_date", dossier.termination.expiry_date],
    [
      "termination.next_decision_date",
      resolveTermination(dossier.termination).next_decision_date,
    ],
    ["legal_regime.state_statute", dossier.legal_regime.state_statute],
    ["legal_regime.local_ordinance", dossier.legal_regime.local_ordinance],
  ];
  for (const [field, v] of actionNulls) {
    if (v === null) bump(`${dossier.slug}\u0000${field}`, "UNKNOWN");
  }
  if (dossier.legal_regime.disclosure_duties.length === 0) {
    bump(`${dossier.slug}\u0000legal_regime.disclosure_duties`, "UNKNOWN");
  }
  const counts: Record<string, number> = {};
  for (const kind of kinds.values()) counts[kind] = (counts[kind] ?? 0) + 1;
  const notResearched = counts["NOT_RESEARCHED"] ?? 0;
  const noEvidenceFound = counts["NO_EVIDENCE_FOUND"] ?? 0;
  const unresolved = counts["UNRESOLVED"] ?? 0;
  const unknown = counts["UNKNOWN"] ?? 0;
  const emptySections = dossier.sections.filter(
    (s) =>
      sectionIsEmpty(s) &&
      !SECTION_ACTION_BLOCKS[s.section_id] &&
      !(s.section_id === "what_we_dont_know" && dossier.gaps.length > 0),
  ).length;
  return {
    total: notResearched + noEvidenceFound + unresolved + unknown,
    notResearched,
    noEvidenceFound,
    unresolved,
    unknown,
    withheld,
    emptySections,
  };
}

/**
 * The explicit incompleteness banner (SIG-UI-012): the count of EVERY field the
 * dossier cannot answer — broken down by the kind of unknown the record
 * actually carries — plus the empty-section count and the absence rule. No kind
 * is asserted for a bare unknown the data does not label (QW-7, F-136).
 */
export function incompletenessBanner(dossier: Dossier): string {
  const u = dossierUnknowns(dossier);
  const parts: string[] = [];
  if (u.notResearched > 0) {
    parts.push(`${u.notResearched} not researched`);
  }
  if (u.noEvidenceFound > 0) {
    parts.push(`${u.noEvidenceFound} searched with nothing found`);
  }
  if (u.unresolved > 0) {
    parts.push(`${u.unresolved} unresolved`);
  }
  if (u.unknown > 0) {
    parts.push(`${u.unknown} recorded simply as unknown`);
  }
  const breakdown = parts.length > 0 ? ` — ${parts.join(", ")}` : "";
  const sections =
    u.emptySections > 0
      ? ` ${u.emptySections} section${u.emptySections === 1 ? "" : "s"} hold no record in SIG.`
      : "";
  const withheld =
    u.withheld > 0
      ? ` ${u.withheld} further field${u.withheld === 1 ? "" : "s"} withheld under publication policy.`
      : "";
  return (
    `This dossier has ${u.total} field${u.total === 1 ? "" : "s"} with no recorded value` +
    `${breakdown}.${sections}${withheld} ` +
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
    // P34.11 (QW-7): the banner counts EVERY unknown, not only NOT_RESEARCHED —
    // additive wire fields; `unresearched_field_count` keeps its SIG-UI-012 meaning.
    unknown_field_count: dossierUnknowns(dossier).total,
    unknown_fields: (() => {
      const u = dossierUnknowns(dossier);
      return {
        not_researched: u.notResearched,
        no_evidence_found: u.noEvidenceFound,
        unresolved: u.unresolved,
        unknown: u.unknown,
        withheld: u.withheld,
      };
    })(),
    empty_section_count: dossierUnknowns(dossier).emptySections,
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
 * (P34.12 / K11 §5.5, RQ-00) The dossier no longer derives taskable-absence
 * link params: the fixture `/task/new/<slug>/` intake pages are retired
 * (F-113/F-274 — they claimed a task "has been generated" when nothing had
 * been). Absence hatches render as named absences until RQ-03 ships real
 * `/task/<handle>/` pages from the export's task handles.
 */
