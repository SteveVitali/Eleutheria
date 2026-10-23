// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * P35.37 (R11-K13-TX-09, SIG-TRANSP-013, J3 §5.4, UXR-34): the ONE figure data
 * contract every material number on a public page renders through.
 *
 * The J3 §5.4 pointer contract, verbatim:
 *
 *   <Figure value=… artifact=… pointer=… definition=… href=…>
 *
 * which emits `data-artifact="<manifest path>"`, `data-pointer="<JSON pointer>"`
 * and a visible "source" link. A build check fails any page whose rendered
 * numbers lack a manifest-listed artifact; a second check fails raw numerals in
 * page templates outside the component for the named page classes (home,
 * dossier, coverage, freshness, sources, data, status).
 *
 * The J3 §5.4 per-class link-target table, verbatim:
 *
 *   | figure class | link target |
 *   |---|---|
 *   | headline counts (home, coverage) | the definition page anchor + the
 *   |  release artifact (`coverage.json#/…`) + the downloadable file that
 *   |  recomputes it |
 *   | dossier counts | `/r/<pub>/c/<comp>/jurisdiction/<j>/` record list + the
 *   |  dossier's page-specific provenance (per-source counts, PKG-10) + the
 *   |  per-source slices |
 *   | per-source counts | `/sources/<id>/` coverage section |
 *   | freshness / run metrics | the run row in `/sources/<id>/runs/` |
 *   | contradictions | the contradiction record(s) |
 *   | evaluation metrics | the published evaluation artifact |
 *
 * Link targets that name routes a later row builds carry the target KIND as a
 * named absence — never a dead link (the ticket's recorded seam):
 * `/sources/<id>/` coverage is P36.48's render, run rows are P36.46's, and the
 * `/r/<pub>/…` record list exists only when a release is bound to the build.
 *
 * UXR-34: every page carries ONE `figures[]` registry — built by
 * {@link defineFigures} — whose ids are unique and resolve to breakdowns
 * (`data-breakdown`, an in-page `#fig-<id>` anchor or a route). Duplicate ids
 * and numeral-bearing figures with no valid evidence target fail the build.
 */

import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

/** The figure classes the J3 §5.4 link-target table names. */
export const FIGURE_CLASSES = [
  "headline",
  "dossier",
  "per_source",
  "freshness",
  "contradiction",
  "evaluation",
] as const;
export type FigureClass = (typeof FIGURE_CLASSES)[number];

/**
 * One link target in a figure's evidence set. A target is either a real route
 * (`href`, joined through `withBase()` at render) or a NAMED ABSENCE (`absent`
 * states what is missing and why) — never both, never neither, and never a
 * dead link. `kind` names the J3 §5.4 target class the link answers.
 */
export interface FigureTarget {
  kind: string;
  /** The visible label (e.g. "record list", "run row"). */
  label: string;
  /** A resolvable route (leading slash optional — render joins withBase). */
  href?: string;
  /** The named absence — why no link renders (e.g. "P36.48's route"). */
  absent?: string;
}

/**
 * The figure contract (J3 §5.4's five fields verbatim) plus the registry
 * bookkeeping UXR-34 requires (`id` unique per page, `class`, `targets`,
 * `breakdown`). `label` is the human caption the component renders beside the
 * value when a page supplies one.
 */
export interface FigureSpec {
  /** Registry id — unique within the page's `figures[]` (UXR-34). */
  id: string;
  /** The J3 §5.4 figure class — drives the link-target shape. */
  class: FigureClass;
  /** The material number (contract field `value`). */
  value: string | number;
  /** Optional unit rendered beside the value ("days", "devices"). */
  unit?: string;
  /** Optional caption; the page may also render text around the component. */
  label?: string;
  /** A manifest-listed artifact path (contract field `artifact`). */
  artifact: string;
  /**
   * A JSON pointer into `artifact` naming where the value derives (contract
   * field `pointer`). `/` is this contract's root-of-artifact pointer — the
   * count derives from the whole artifact (e.g. "N rows in the array").
   */
  pointer: string;
  /** The definition-page anchor (contract field `definition`). */
  definition: string;
  /** The visible "source" link (contract field `href`). */
  href: string;
  /** Where the registry id resolves — `#fig-<id>` or a route anchor (UXR-34). */
  breakdown: string;
  /** The additional per-class link targets (link-or-named-absence each). */
  targets: FigureTarget[];
}

// ---------------------------------------------------------------------------
// The manifest-listed artifact set a `data-artifact` may name.
// ---------------------------------------------------------------------------

const ARTIFACT_LIST_PATH = "web/src/lib/figure-artifacts.json";

/** The export-dir artifact paths a compartment's row streams occupy. */
const COMPARTMENT_STREAM_RE = /^[a-z0-9_]+\/(sites|statements|record_claims)\.jsonl$/;

/**
 * P35.45: the per-dossier artifact paths — `web/dossiers/<slug-path>.json`
 * where the slug path is one or more lowercase slug segments (`usa`,
 * `usa/ca`, `usa/ca/verdin-county-06037`). Like the compartment streams the
 * set is unbounded (the registry grows) and the export manifest does not
 * enumerate it, so a strict pattern stands in for enumeration. The index
 * document itself is excluded — it carries no dossier record to point into.
 */
const PER_DOSSIER_RE = /^web\/dossiers\/[a-z0-9-]+(\/[a-z0-9-]+)*\.json$/;

function repoRoot(): string {
  let dir = fileURLToPath(new URL(".", import.meta.url));
  for (;;) {
    const probe = `${dir.endsWith("/") ? dir : `${dir}/`}uv.lock`;
    try {
      readFileSync(probe);
      return dir.endsWith("/") ? dir : `${dir}/`;
    } catch {
      const parent = dir.replace(/[^/]+\/?$/, "");
      if (parent === dir || parent === "") {
        throw new Error(`repoRoot: walked above ${dir} without finding uv.lock`);
      }
      dir = parent;
    }
  }
}

/**
 * The committed artifact-path list (fixtures mode's manifest). In
 * `SIG_DATA_SOURCE=export` mode the check verifies against the REAL export
 * manifest (`<exportDir>/manifest.json` `artifacts[].path`); this list is the
 * fallback + the fixture-equivalent manifest the P27.5 harness writes.
 */
let _fixturePaths: string[] | null = null;
export function fixtureArtifactPaths(): string[] {
  if (_fixturePaths === null) {
    const raw = readFileSync(`${repoRoot()}${ARTIFACT_LIST_PATH}`, "utf-8");
    const parsed = JSON.parse(raw) as { artifacts?: unknown };
    if (!Array.isArray(parsed.artifacts)) {
      throw new Error(`${ARTIFACT_LIST_PATH}: expected an "artifacts" array`);
    }
    _fixturePaths = parsed.artifacts.map(String);
  }
  return _fixturePaths;
}

/** True when `path` is a manifest-listed artifact `data-artifact` may name. */
export function isManifestArtifact(path: string, listed?: readonly string[]): boolean {
  if (COMPARTMENT_STREAM_RE.test(path)) return true;
  // P35.45 — per-dossier artifacts are emitted under web/dossiers/ but never
  // the index document itself (it carries no dossier record to point into).
  if (PER_DOSSIER_RE.test(path) && path !== "web/dossiers/index.json") return true;
  return (listed ?? fixtureArtifactPaths()).includes(path);
}

// ---------------------------------------------------------------------------
// The figures[] registry (UXR-34) — one per page; validation fails the build.
// ---------------------------------------------------------------------------

/** The whole-document pointer this contract uses for whole-artifact derivations. */
export const ROOT_POINTER = "/";

const POINTER_RE = /^\//;
const ID_RE = /^[a-z0-9][a-z0-9-]*$/;

/** Validate a single figure spec — every failure is a build error, never a warn. */
export function assertFigureSpec(f: FigureSpec, page: string, listed?: readonly string[]): void {
  if (!ID_RE.test(f.id)) {
    throw new Error(`figures[] ${page}: id "${f.id}" must be a lowercase slug token`);
  }
  if (!(FIGURE_CLASSES as readonly string[]).includes(f.class)) {
    throw new Error(`figures[] ${page}: id "${f.id}" — unknown figure class "${f.class}"`);
  }
  if (f.value === "" || f.value === null || f.value === undefined) {
    throw new Error(`figures[] ${page}: id "${f.id}" carries no value`);
  }
  if (!isManifestArtifact(f.artifact, listed)) {
    throw new Error(
      `figures[] ${page}: id "${f.id}" — artifact "${f.artifact}" is not a ` +
        `manifest-listed artifact path (J3 §5.4: data-artifact must be manifest-listed)`,
    );
  }
  if (!POINTER_RE.test(f.pointer)) {
    throw new Error(
      `figures[] ${page}: id "${f.id}" — pointer "${f.pointer}" is not a JSON pointer`,
    );
  }
  if (!f.definition.trim()) {
    throw new Error(`figures[] ${page}: id "${f.id}" carries no definition anchor`);
  }
  if (!f.href.trim()) {
    throw new Error(`figures[] ${page}: id "${f.id}" carries no visible source link (href)`);
  }
  if (!f.breakdown.trim()) {
    throw new Error(`figures[] ${page}: id "${f.id}" carries no breakdown target`);
  }
  for (const t of f.targets) {
    if (!t.kind.trim() || !t.label.trim()) {
      throw new Error(`figures[] ${page}: id "${f.id}" — a target lacks kind/label`);
    }
    if ((t.href === undefined) === (t.absent === undefined)) {
      throw new Error(
        `figures[] ${page}: id "${f.id}" — target "${t.label}" must carry exactly ` +
          `one of href (a resolvable route) or absent (a named absence), never both/neither`,
      );
    }
    if (t.href !== undefined && !t.href.trim()) {
      throw new Error(`figures[] ${page}: id "${f.id}" — target "${t.label}" has an empty href`);
    }
    if (t.absent !== undefined && !t.absent.trim()) {
      throw new Error(
        `figures[] ${page}: id "${f.id}" — target "${t.label}" names no absence reason`,
      );
    }
  }
}

/**
 * The page's ONE `figures[]` registry (UXR-34): validates every spec against
 * the contract, then fails the build on a duplicate id (the acceptance shape).
 * `listed` overrides the artifact set (tests + export mode pass the real
 * manifest); default = the committed fixture list.
 */
export function defineFigures(
  page: string,
  specs: readonly FigureSpec[],
  listed?: readonly string[],
): FigureSpec[] {
  const seen = new Set<string>();
  for (const f of specs) {
    assertFigureSpec(f, page, listed);
    if (seen.has(f.id)) {
      throw new Error(`figures[] ${page}: duplicate id "${f.id}" (UXR-34 — ids are unique)`);
    }
    seen.add(f.id);
  }
  return [...specs];
}

// ---------------------------------------------------------------------------
// Per-class target builders — the J3 §5.4 link-target table made executable.
// ---------------------------------------------------------------------------

/** A link-or-absence target — one call site for the named-absence rule. */
export function target(
  kind: string,
  label: string,
  opts: { href?: string | null; absent?: string },
): FigureTarget {
  if (opts.href != null && opts.href.trim() !== "") {
    return { kind, label, href: opts.href };
  }
  return { kind, label, absent: opts.absent ?? "no published route for this target kind" };
}

/**
 * The served form of a release artifact — the "downloadable file that
 * recomputes it" (headline class) and each figure's manifest-artifact source
 * link. `/artifact/<export-path>` is the P35.37 read-only artifact route; the
 * path argument is written WITHOUT a leading slash so the root-absolute-path
 * containment check measures zero new sites.
 */
export function artifactHref(artifactPath: string): string {
  return `artifact/${artifactPath}`;
}

/** Headline counts (home, coverage): definition anchor + release artifact +
 *  the downloadable file (the artifact route itself) + a recomputing list. */
export function headlineTargets(opts: { recordList?: string | null }): FigureTarget[] {
  return [
    target("record list", "record list", {
      href: opts.recordList ?? null,
      absent: "no released record list for this count — ships with the release record browser",
    }),
  ];
}

/** Dossier counts: the record list + page-specific provenance + per-source slices. */
export function dossierTargets(opts: {
  recordList?: string | null;
  provenanceHref?: string | null;
  perSourceSlices?: string | null;
}): FigureTarget[] {
  return [
    target("record list", "record list", {
      href: opts.recordList ?? null,
      absent: "no release is bound to this build — the /r/<pub>/ record list ships with the publish row",
    }),
    target("provenance", "provenance", {
      href: opts.provenanceHref ?? "#hwkt-heading",
      absent: "no provenance panel on this surface",
    }),
    target("per-source slices", "per-source slices", {
      href: opts.perSourceSlices ?? null,
      absent: "the per-source slice view ships with the source explorer (P36.48)",
    }),
  ];
}

/** Per-source counts: `/sources/<id>/` coverage — P36.48's unbuilt route. */
export function perSourceTargets(sourceId: string, sourceRoute?: string | null): FigureTarget[] {
  return [
    target("source coverage", `coverage of ${sourceId}`, {
      href: sourceRoute ?? null,
      absent: "the /sources/<id>/ coverage section is P36.48's route — not yet published",
    }),
  ];
}

/** Freshness / run metrics: the run row under `/sources/<id>/runs/` (P36.46). */
export function freshnessTargets(sourceId: string, runRoute?: string | null): FigureTarget[] {
  return [
    target("run row", `run row for ${sourceId}`, {
      href: runRoute ?? null,
      absent: "the /sources/<id>/runs/ run row is P36.46's render — not yet published",
    }),
  ];
}

/** Contradictions: the contradiction record(s) — no public record route yet. */
export function contradictionTargets(recordHref?: string | null): FigureTarget[] {
  return [
    target("contradiction records", "contradiction records", {
      href: recordHref ?? null,
      absent: "contradiction record pages ship with the disagreements surface",
    }),
  ];
}

/** Evaluation metrics: the published evaluation artifact IS the target. */
export function evaluationTargets(): FigureTarget[] {
  return [];
}

/** The per-class builder dispatch — every class resolves its J3 §5.4 target set. */
export function classTargets(
  cls: FigureClass,
  ctx: {
    recordList?: string | null;
    provenanceHref?: string | null;
    perSourceSlices?: string | null;
    sourceId?: string;
    sourceRoute?: string | null;
    runRoute?: string | null;
    contradictionRecord?: string | null;
  } = {},
): FigureTarget[] {
  switch (cls) {
    case "headline":
      return headlineTargets({ recordList: ctx.recordList });
    case "dossier":
      return dossierTargets(ctx);
    case "per_source":
      return perSourceTargets(ctx.sourceId ?? "this source", ctx.sourceRoute);
    case "freshness":
      return freshnessTargets(ctx.sourceId ?? "this source", ctx.runRoute);
    case "contradiction":
      return contradictionTargets(ctx.contradictionRecord);
    case "evaluation":
      return evaluationTargets();
  }
}
