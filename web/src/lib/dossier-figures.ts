// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * P35.37 (SIG-TRANSP-013, J3 §5.4, UXR-34): the dossier page's ONE `figures[]`
 * registry. Every material number the dossier renders — the incompleteness
 * banner count, each reconciliation figure, each numeral-bearing row, the
 * notice-window figure, and gap labels carrying a numeral — is registered here
 * with its manifest artifact (`web/dossiers.json` or the demo presentation
 * artifact), a JSON pointer into the dossier record, a `#fig-<id>` breakdown
 * anchor, and the dossier-class link targets (record list + the dossier's own
 * provenance + per-source slices — named absences where the route is not
 * published).
 *
 * Row numerals are detected with THE SAME regular expression the bare-numeral
 * check (`web/scripts/check-figures.mjs` MATERIAL_NUMERAL_RE) enforces — the
 * two copies are pinned equal by `figures.test.ts`.
 */

import {
  dossierTargets,
  type FigureSpec,
} from "./figures";
import { dossierUnknowns, rowDisplayValue } from "./dossier";
import type { Dossier } from "./dossier";

/**
 * The bare-numeral detection pattern — byte-identical to
 * `MATERIAL_NUMERAL_RE` in `web/scripts/check-figures.mjs` (a unit test pins
 * the two strings equal): a standalone digit run (optionally comma-grouped in
 * strict `\d{3}` thousands groups, or decimal) not glued to a word character,
 * `&` (entity), `#`/`§`-style reference markers, `.`/`-`/`–`/`—`/`:`/`/`
 * (versions, dates, ranges, ids, ratios) on the left, or `\w`/`.`/`-`/dash/
 * `:`/`/`/`%` on the right. A trailing comma is PROSE punctuation ("HTTP 429,
 * 503 or 504"), never part of the numeral — so commas only count inside
 * strict thousands groups.
 */
export const MATERIAL_NUMERAL_PATTERN =
  "(?<![\\w&#§.\\-:\\/–—≥])\\d+(?:,\\d{3})*(?:\\.\\d+)?(?![\\w&.:\\-–—\\/%])";

/** True when `text` carries a numeral the bare-numeral check would flag. */
export function textHasMaterialNumeral(text: string): boolean {
  return new RegExp(MATERIAL_NUMERAL_PATTERN).test(text);
}

/** The first material-numeral run in `text` (a figure's `value`). */
export function firstNumeral(text: string): string | null {
  const m = new RegExp(MATERIAL_NUMERAL_PATTERN).exec(text);
  return m ? m[0] : null;
}

/** Where this dossier's record lives in the release artifact set. */
export interface DossierArtifactRef {
  artifact: string;
  /** `null` when the artifact IS the dossier record (a per-dossier
   * `web/dossiers/<slug-path>.json` — P35.45): the pointer roots at the
   * document itself rather than an array index. */
  index: number | null;
}

/** The build-time context the dossier registry resolves its targets against. */
export interface DossierFigureContext {
  /** The dossier's position in its artifact — null → no registry built (defect). */
  ref: DossierArtifactRef | null;
  /** `/r/<pub>/c/<comp>/jurisdiction/<j>/` when a release is bound, else null. */
  recordList: string | null;
  /**
   * The in-page "How we know this" provenance anchor (`#hwkt-heading` on the
   * BaseLayout pages). `null` on surfaces that carry no provenance panel (the
   * print export) → the target renders a named absence, never a dead anchor.
   */
  provenanceHref: string | null;
}

/** The pointer family every dossier figure shares — `/<index>/<path>` in the
 * monolithic bundle, `<path>` in a per-dossier file (P35.45: `rest` alone,
 * `""` falling back to the bare root pointer). */
function ptr(ctx: DossierFigureContext, rest: string): string {
  return ctx.ref!.index === null ? rest || "/" : `/${ctx.ref!.index}${rest}`;
}

function spec(
  ctx: DossierFigureContextWithHref,
  partial: Omit<FigureSpec, "class" | "artifact" | "pointer" | "href" | "targets" | "definition"> & {
    pointer: string;
    definition: string;
  },
): FigureSpec {
  return {
    ...partial,
    class: "dossier",
    artifact: ctx.ref!.artifact,
    pointer: partial.pointer,
    definition: partial.definition,
    href: ctx.artifactHref,
    targets: dossierTargets({
      recordList: ctx.recordList,
      provenanceHref: ctx.provenanceHref,
      perSourceSlices: null,
    }),
  };
}

/** `ctx` extended with the served form of the dossier record. */
export interface DossierFigureContextWithHref extends DossierFigureContext {
  artifactHref: string;
}

/**
 * The dossier page's complete `figures[]` registry (`page` = the interactive
 * dossier, `print` = the print export — the two pages carry the same figures
 * under the same ids except gap variants, which carry their render variant so
 * the summary and section copies never collide).
 */
export function dossierFigureSpecs(
  dossier: Dossier,
  page: "page" | "print",
  ctx: DossierFigureContextWithHref,
): FigureSpec[] {
  const specs: FigureSpec[] = [];
  if (!ctx.ref) return specs;

  // The incompleteness banner — the headline unknown-count (SIG-UI-012).
  specs.push(
    spec(ctx, {
      id: "banner",
      value: dossierUnknowns(dossier).total,
      pointer: ptr(ctx, ""),
      definition: "#sec-what_we_dont_know",
      breakdown: "#fig-banner",
    }),
  );

  dossier.sections.forEach((section, si) => {
    (section.figures ?? []).forEach((f, fi) => {
      const fid = dossierFigId(f.key);
      specs.push(
        spec(ctx, {
          id: fid,
          value: f.value,
          unit: f.unit,
          pointer: ptr(ctx, `/sections/${si}/figures/${fi}/value`),
          definition: `#fig-${fid}`,
          breakdown: `#fig-${fid}`,
        }),
      );
    });
    (section.rows ?? []).forEach((r, ri) => {
      // The row's material numeral may sit in the VALUE or in its note (a
      // "…not 'currently shares with 147' (§12.2)" caveat carries a count) —
      // the figure covers the whole row cell either way.
      const display = rowDisplayValue(r);
      const first =
        firstNumeral(display) ?? (r.note ? firstNumeral(r.note) : null);
      if (first === null) return;
      const rid = dossierRowId(section.section_id, ri);
      specs.push(
        spec(ctx, {
          id: rid,
          value: first,
          pointer: ptr(ctx, `/sections/${si}/rows/${ri}/value`),
          definition: `#sec-${section.section_id}`,
          breakdown: `#fig-${rid}`,
        }),
      );
    });
  });

  // P35.45 (K4 §5.2): the roll-up numerals the keyed dossier renders outside
  // its twelve sections — each child's placed count and the two disagreement
  // counts. A flat dossier carries none of these fields → no specs (the v1
  // surface is byte-identical).
  (dossier.children ?? []).forEach((c, ci) => {
    if (typeof c.records !== "number") return;
    specs.push(
      spec(ctx, {
        id: `child-${ci}`,
        value: c.records,
        unit: "records",
        pointer: ptr(ctx, `/children/${ci}/records`),
        definition: "#rollup-heading",
        breakdown: `#fig-child-${ci}`,
      }),
    );
  });
  // P35.47 (SIG-CONF-005 / GQ-10): the dossier's count interval — the L3
  // §5.2 display string ("N camera records · between L and U listed
  // cameras") renders verbatim inside one figure region, covering every
  // numeral it carries. An honest `not_evaluable` block renders no numeral
  // → no spec.
  const interval = dossier.rollup?.count_interval;
  if (interval?.display) {
    specs.push(
      spec(ctx, {
        id: "listed-cameras",
        value: interval.display,
        unit: "records",
        pointer: ptr(ctx, "/rollup/count_interval/display"),
        definition: "#rollup-heading",
        breakdown: "#fig-listed-cameras",
      }),
    );
  }

  const disagreements: [string, number | undefined][] = [
    ["declared-here-located-elsewhere", dossier.disagreements?.declared_here_located_elsewhere],
    ["located-here-declared-elsewhere", dossier.disagreements?.located_here_declared_elsewhere],
  ];
  for (const [slug, n] of disagreements) {
    if (typeof n !== "number" || n === 0) continue;
    specs.push(
      spec(ctx, {
        id: `disagreement-${slug}`,
        value: n,
        unit: "records",
        pointer: ptr(ctx, `/disagreements/${slug.replace(/-/g, "_")}`),
        definition: "#rollup-heading",
        breakdown: `#fig-disagreement-${slug}`,
      }),
    );
  }

  // The notice-window figure (SIG-UI-014a) — a material number when recorded.
  if (dossier.termination.notice_window_days !== null) {
    specs.push(
      spec(ctx, {
        id: "notice-window",
        value: dossier.termination.notice_window_days,
        unit: "days",
        pointer: ptr(ctx, "/termination/notice_window_days"),
        definition: "#sec-cost_and_expiry",
        breakdown: "#fig-notice-window",
      }),
    );
  }

  // Gap labels carrying a numeral — each gap list renders once per variant, so
  // the variant is part of the id (a page renders the summary AND section
  // copies; ids must stay unique per page).
  const variants = page === "page" ? ["summary", "section"] : ["print-summary", "print-section"];
  for (const variant of variants) {
    dossier.gaps.forEach((g, gi) => {
      const text = `${g.label}${g.note ? ` — ${g.note}` : ""}`;
      if (!textHasMaterialNumeral(text)) return;
      specs.push(
        spec(ctx, {
          id: `gap-${variant}-${gi}`,
          value: firstNumeral(text) ?? g.label,
          pointer: ptr(ctx, `/gaps/${gi}/label`),
          definition: "#sec-what_we_dont_know",
          breakdown: `#fig-gap-${variant}-${gi}`,
        }),
      );
    });
  }

  return specs;
}

/** `specs` keyed by id for component lookup. */
export function figureSpecMap(specs: readonly FigureSpec[]): Map<string, FigureSpec> {
  return new Map(specs.map((s) => [s.id, s]));
}

/**
 * The registry-id slug for a dossier figure key — figure keys are
 * `snake_case` artifact field names; registry ids are lowercase slugs.
 * `DossierSection` looks specs up by this id — the two stay in lock-step here.
 */
export function dossierFigId(key: string): string {
  return `fig-${key.replace(/_/g, "-")}`;
}

/** The registry id for a row's figure (slugged section id + row index). */
export function dossierRowId(sectionId: string, rowIndex: number): string {
  return `row-${sectionId.replace(/_/g, "-")}-${rowIndex}`;
}
