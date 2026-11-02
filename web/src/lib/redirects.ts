// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * P36.35 (K4 JUR-05 / K13 UXR-08, §56.11 SIG-UI-058 owner, SIG-JUR-009/012
 * owner) — the ONE redirect generator.
 *
 * Every URL SIG has published resolves through this module: the
 * `sig.jurisdiction-slug-history/1` dossier rows, the `sig.slug-history/1`
 * entity keys (rename/merge/split/withdrawal plus the `/id/<type>/<uuid>`
 * alias), every `*_handles_history` artifact (task/watch/evidence — honest
 * empty until RQ-01/WX/EV land them), and the fixed legacy list the K13
 * route registry declares (`/task/new/**` retired → 410; `/data-freshness/**`,
 * `/network/`, `/evidence/<id>/` → 301 once their successor surfaces ship —
 * each gated on the emitted route set so a redirect never shadows a live
 * page or lands on a route that does not exist).
 *
 * Outputs are ONE generated nginx include — `dist/redirects.conf`, emitted
 * at `astro:build:done` beside the site (the conf-generation carry into the
 * bucket's `conf/` prefix is the publish path's, D-P36.35-1) — plus the
 * static stub pages the Astro routes render as the fallback where the
 * include cannot run (K4 §8.2 phases 1–2). Renamed source identifiers are
 * deliberately NOT redirects: they serve the neutral identifier-changed
 * page in place via `conf/renamed_*.conf`, generated from the restricted
 * map — a redirect would disclose the old→new mapping (DR-C6-01 / B-3).
 *
 * `?as_of_world=` (and every other selector) is PRESERVED through the
 * 3xx rules (`$is_args$args`): the path resolution and the snapshot
 * selection stay separate mechanisms — a legacy as-of permalink reaches
 * the successor path with its selector intact, where the selectors layer
 * (P36.66a) maps it to the pinned snapshot (SIG-JUR-012).
 */

import {
  resolveEntityRequest,
  type EntitySlugHistoryRow,
} from "./entity-history";
import type { SlugHistoryRow } from "./data";

export type RedirectStatus = 200 | 300 | 301 | 302 | 410;

/** One rule of the generated include. */
export interface RedirectRule {
  /** The published path this rule answers (exact `location =` match). */
  from: string;
  status: RedirectStatus;
  /** The 3xx successor path (args preserved). */
  target?: string;
  /** The emitted page served in place (split/corrected surfaces — the
   *  300/200 semantics the static page carries). */
  serve?: string;
  /** The URL-history family this rule came from. */
  family: "jurisdiction" | "entity" | "id-alias" | "handle" | "legacy";
  /** The history row's kind (moved/split/corrected/renamed/…). */
  kind?: string;
  note?: string;
}

/** One `*_handles_history` row (RQ/WX/EV handle renames): old → new path. */
export interface HandleHistoryRow {
  old: string;
  target: string;
  family: "handle";
  note?: string;
}

export interface RedirectInputs {
  slugHistory: readonly SlugHistoryRow[];
  /** jkey → its emitted canonical dossier path (`/dossier/<slug-path>/`);
   *  `"unplaced"` maps to the unplaced report path. */
  jurisdictionTargets: ReadonlyMap<string, string>;
  /** jkey → level, for the print-alias rule (print mints for
   *  country/admin-1 dossiers only, D-K4-3). */
  jurisdictionLevels?: ReadonlyMap<string, string>;
  entityHistory: readonly EntitySlugHistoryRow[];
  /** RQ/WX/EV handle-history rows (absent artifacts contribute none). */
  handleRows?: readonly HandleHistoryRow[];
  /** The routes this build emitted (`/dossier/usa/ok/` shaped, trailing
   *  slash) — a 3xx rule is emitted only when its target exists, and a
   *  fixed-legacy rule only once its source route retired. */
  emittedRoutes: ReadonlySet<string>;
}

const LEVELS_WITH_PRINT = new Set(["country", "admin-1"]);

function jsonAlias(path: string): string {
  return path.endsWith("/") ? `${path.slice(0, -1)}.json` : `${path}.json`;
}

/** Jurisdiction slug-history rows → rules (SIG-JUR-009: the page, its
 *  print alias and its `.json` twin all resolve). */
function jurisdictionRules(inputs: RedirectInputs): RedirectRule[] {
  const out: RedirectRule[] = [];
  for (const row of inputs.slugHistory) {
    const from = `/dossier/${row.slug}/`;
    const successors = Array.isArray(row.successor)
      ? row.successor.map(String)
      : row.successor !== undefined
        ? [String(row.successor)]
        : [];
    const targets = successors
      .map((j) => inputs.jurisdictionTargets.get(j))
      .filter((t): t is string => typeof t === "string" && t.length > 0)
      .filter((t) => inputs.emittedRoutes.has(t));
    if (row.kind === "split") {
      // The split page is the answer — served in place (K4 §8.1: 300 where
      // the host supports a body, else 200 noindex; the stub IS the body).
      out.push({
        from,
        status: 200,
        serve: `${from}index.html`,
        family: "jurisdiction",
        kind: "split",
        note: `split-choice page lists ${successors.length} successors`,
      });
      continue;
    }
    const target = targets[0];
    if (row.kind === "corrected" || target === undefined) {
      // `corrected` rows are correction PAGES (200, noindex — never a
      // rename); a `moved` row whose successor is not published in this
      // build serves its stub, which explains the move honestly.
      out.push({
        from,
        status: 200,
        serve: `${from}index.html`,
        family: "jurisdiction",
        kind: row.kind,
        note:
          row.kind === "corrected"
            ? "correction page — records belonged elsewhere (noindex)"
            : "successor not emitted in this build — the stub explains",
      });
      continue;
    }
    out.push({
      from,
      status: 301,
      target,
      family: "jurisdiction",
      kind: "moved",
    });
    if (
      inputs.jurisdictionLevels !== undefined &&
      successors
        .map((j) => inputs.jurisdictionLevels!.get(j))
        .some((l) => l !== undefined && LEVELS_WITH_PRINT.has(l))
    ) {
      out.push({
        from: `${from}print/`,
        status: 301,
        target: `${target}print/`,
        family: "jurisdiction",
        kind: "moved",
        note: "print alias",
      });
    }
    out.push({
      from: jsonAlias(from),
      status: 301,
      target: jsonAlias(target),
      family: "jurisdiction",
      kind: "moved",
      note: "JSON twin alias",
    });
  }
  return out;
}

/** Entity `sig.slug-history/1` rows → rules: retired keys answer their
 *  terminal status; every `/id/<type>/<uuid>` alias resolves through
 *  `resolveEntityRequest` (the shared seam — stub and rule can never
 *  diverge, P36.29). */
function entityRules(inputs: RedirectInputs): RedirectRule[] {
  const out: RedirectRule[] = [];
  const uuids = new Set<string>();
  for (const row of inputs.entityHistory) {
    if (row.uuid) uuids.add(`${row.url_type ?? ""}${row.uuid}`);
    if (
      row.url_type &&
      row.slug &&
      row.hash &&
      ["renamed", "merged", "split", "withdrawn"].includes(String(row.status))
    ) {
      const from = `/entity/${row.url_type}/${row.slug}--${row.hash}/`;
      if (row.status === "split") {
        out.push({
          from,
          status: 300,
          family: "entity",
          kind: "split",
          note: `multiple choices — successors: ${(Array.isArray(row.target) ? row.target : []).join(", ")}`,
        });
      } else if (row.status === "withdrawn") {
        out.push({ from, status: 410, family: "entity", kind: "withdrawn" });
      } else if (typeof row.target === "string" && row.target) {
        out.push({
          from,
          status: 301,
          target: row.target,
          family: "entity",
          kind: String(row.status),
        });
      }
    }
  }
  // The `/id/<type>/<uuid>` alias — one rule per recorded uuid, resolved
  // through the shared seam (302 while current, else the terminal status).
  const seen = new Set<string>();
  for (const row of inputs.entityHistory) {
    if (!row.uuid || !row.url_type) continue;
    const path = `/id/${row.url_type}/${row.uuid}`;
    if (seen.has(path)) continue;
    seen.add(path);
    const decision = resolveEntityRequest(inputs.entityHistory, path);
    if (decision === null) continue;
    for (const from of [path, `${path}/`]) {
      out.push({
        from,
        status: decision.status as RedirectStatus,
        target: decision.target,
        // A 300 serves the emitted /id/ stub page — the successors list is
        // the body a bare `return 300` cannot carry.
        serve: decision.status === 300 ? `${path}/index.html` : undefined,
        family: "id-alias",
        kind: decision.reason,
      });
    }
  }
  return out;
}

/** The fixed legacy list (K13 §2.5) — declared, never invented. A rule is
 *  emitted only when its successor exists AND the legacy route retired;
 *  a live page always outranks the fixed list (the page IS the answer). */
function legacyRules(inputs: RedirectInputs): RedirectRule[] {
  const out: RedirectRule[] = [];
  const emitted = inputs.emittedRoutes;
  // `/task/new/**` — the retired fixture intake pages (K11 §5.5 / RQ-00).
  // Retired means 410 for the whole subtree; a re-emitted `/task/new/`
  // route is a BUG — refuse rather than shadow it.
  const taskNewEmitted = [...emitted].some((r) => r.startsWith("/task/new/"));
  if (taskNewEmitted) {
    throw new Error(
      "redirects: /task/new/ routes are emitted — the namespace is retired " +
        "(410), never re-published (K11 §5.5)",
    );
  }
  out.push({
    from: "/task/new/",
    status: 410,
    family: "legacy",
    kind: "retired",
    note: "prefix rule — the fixture intake pages are retired",
  });
  // `/data-freshness/**` → `/sources/` — emitted once the page retires
  // (UX9-3's sources table is the successor surface) and `/sources/` exists.
  if (!emitted.has("/data-freshness/") && emitted.has("/sources/")) {
    for (const suffix of ["", "status/", "source/"]) {
      out.push({
        from: `/data-freshness/${suffix}`,
        status: 301,
        target: "/sources/",
        family: "legacy",
        kind: "moved",
      });
    }
  }
  // `/network/` → `/explore/` — emitted once GX-09a's explorer exists and
  // the interim network page retired.
  if (!emitted.has("/network/") && emitted.has("/explore/")) {
    out.push({
      from: "/network/",
      status: 301,
      target: "/explore/",
      family: "legacy",
      kind: "moved",
      note: "the graph explorer supersedes the interim network island",
    });
  }
  return out;
}

/** The complete rule table — ONE derivation every surface consumes. */
export function redirectRules(inputs: RedirectInputs): RedirectRule[] {
  const rules = [
    ...jurisdictionRules(inputs),
    ...entityRules(inputs),
    ...(inputs.handleRows ?? []).map(
      (r): RedirectRule => ({
        from: r.old,
        status: 301,
        target: r.target,
        family: "handle",
        note: r.note,
      }),
    ),
    ...legacyRules(inputs),
  ];
  // Deterministic order: family, then source path. A duplicate `location =`
  // is a broken include — refuse rather than emit.
  const seen = new Map<string, RedirectRule>();
  for (const r of rules) {
    const prior = seen.get(r.from);
    if (prior !== undefined) {
      throw new Error(
        `redirects: two rules for ${r.from} (${prior.family}/${prior.kind} ` +
          `vs ${r.family}/${r.kind}) — one rule per published URL`,
      );
    }
    seen.set(r.from, r);
  }
  return [...seen.values()].sort(
    (a, b) => a.family.localeCompare(b.family) || a.from.localeCompare(b.from),
  );
}

/**
 * Resolve one request path against the rule table — the check seam the
 * "every historical URL resolves" invariant and the unit fixtures use.
 * `null` = no rule (the caller then consults the emitted-route set —
 * a live page is itself a resolution).
 */
export function resolveRequest(
  rules: readonly RedirectRule[],
  path: string,
): RedirectRule | null {
  const [pathname] = path.split("?");
  for (const r of rules) {
    if (r.from === pathname) return r;
  }
  // The only prefix rule today: the retired `/task/new/` namespace.
  if (pathname.startsWith("/task/new/")) {
    return rules.find((r) => r.from === "/task/new/") ?? null;
  }
  return null;
}

/** Render the generated include — deterministic bytes (`sig.redirects-conf/1`). */
export function renderRedirectsConf(
  rules: readonly RedirectRule[],
  counts: { jurisdictions: number; entities: number; handles: number; routes: number },
): string {
  const lines = [
    "# sig.redirects-conf/1 — the ONE redirect generator (K13 UXR-08 /",
    "# SIG-UI-058, P36.35 / JUR-05). Generated by the web build",
    "# (web/src/lib/redirects.ts); do not hand-edit.",
    "# Every URL SIG has published resolves through this include or the",
    "# static stubs the build emits beside it — no historical URL may",
    "# answer 404 or come to denote a different object (SIG-JUR-009).",
    "# Query selectors ride through ($is_args$args): a legacy",
    "# ?as_of_world= permalink reaches the successor path with its",
    "# selector intact for the snapshot layer (SIG-JUR-012).",
    "# Renamed source identifiers are NOT redirects — they serve the",
    "# neutral identifier-changed page in place via conf/renamed_*.conf",
    "# (DR-C6-01 / B-3; a redirect would disclose the mapping).",
    `# inputs: jurisdictions=${counts.jurisdictions} entities=${counts.entities} handles=${counts.handles} emitted_routes=${counts.routes}`,
    "",
  ];
  for (const r of rules) {
    const note = r.note ? `  # ${r.note}` : "";
    if (r.status === 301 || r.status === 302) {
      lines.push(
        `location = ${r.from} { return ${r.status} ${r.target}$is_args$args; }${note}`,
      );
    } else if (r.status === 410 && r.from === "/task/new/") {
      lines.push(`location ${r.from} { return 410; }${note}`);
    } else if (r.status === 410) {
      lines.push(`location = ${r.from} { return 410; }${note}`);
    } else if (r.status === 300 && r.serve === undefined) {
      lines.push(`location = ${r.from} { return 300; }${note}`);
    } else {
      lines.push(
        `location = ${r.from} { try_files ${r.serve} =404; }${note}`,
      );
    }
  }
  lines.push("");
  return lines.join("\n");
}
