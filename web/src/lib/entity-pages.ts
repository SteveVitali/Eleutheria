// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
/**
 * The P36.42a page model — K2 GX-06a: the 06a entity-page template and the
 * `/entity/` Organizations hub. This module shapes the P36.41
 * `sig.entity-page/1` / `sig.entity-label/1` contracts for RENDERING only —
 * it never re-derives a fact the contract does not carry (the exporter owns
 * the derivation; the page renders it).
 *
 * Owned here:
 *   - the kind display words (mirroring `policy.labels.KIND_WORDS` for the
 *     contract-A kinds — a label, never a raw kind token, SIG-UI-053/108);
 *   - `mergeEntityTwins` — the per-compartment union the page renders
 *     (ADR-106: one page over every compartment twin, each JSON download
 *     still listed per compartment);
 *   - the relationship-group direction/access-kind words (H-2 fields in
 *     words, SIG-UI-115/024);
 *   - the A–Z list model and path pagination (SIG-UI-070: a paginated A–Z
 *     list per published type, every count carrying the ER disclosure);
 *   - the typed-absence model (A-10 / SIG-UI-086): `not_yet_reviewed`
 *     renders the typed state, never a silent absence or a fabricated label.
 */

import type {
  AccessClosureGroup,
  AccessClosurePath,
  DegreeOnlyFact,
  EntityClaimGroup,
  EntityLabelRow,
  EntityPageTwin,
  EntityRelationGroup,
  EntityRelationItem,
  EntityReviewRecord,
} from "./entity-page";
import { withBase } from "./paths";

/** The contract-A kind → its display word (the label-registry's
 *  `KIND_WORDS` for the paged kinds; unknown kinds fall back to "Record",
 *  never a raw token). */
const KIND_WORDS: Record<string, string> = {
  org: "Organisation",
  agency: "Government body",
  portal: "Registry portal",
};
const KIND_PLURALS: Record<string, string> = {
  org: "Organisations",
  agency: "Government bodies",
  portal: "Registry portals",
};

export function kindWord(kind: string): string {
  return KIND_WORDS[kind] ?? "Record";
}
export function kindPlural(kind: string): string {
  return KIND_PLURALS[kind] ?? "Records";
}

// ---------------------------------------------------------------------------
// Direction and access kind in words (K2 §7 H-2 / SIG-UI-024).
// ---------------------------------------------------------------------------

/** The group direction in words — never a bare enum (H-2). */
export function directionWord(direction: string): string {
  if (direction === "outbound") return "outbound";
  if (direction === "inbound") return "inbound";
  return direction;
}

/** The direction explainer — who is the subject of the relation. */
export function directionExplainer(direction: string): string {
  if (direction === "outbound")
    return "this entity is the subject — the relation points at the counterparty";
  if (direction === "inbound")
    return "this entity is the object — the counterparty's relation points at it";
  return "direction not recorded";
}

/** The §12.2 access kind in words — the three kinds are never merged
 *  (SIG-UI-024); a non-access relation group carries `access_kind: null`. */
export function accessKindWord(accessKind: string | null): string | null {
  if (accessKind === null || accessKind === "") return null;
  if (accessKind === "configured_access") return "configured access";
  if (accessKind === "observed_use") return "observed use";
  if (accessKind === "declared_policy") return "declared policy";
  return accessKind;
}

// ---------------------------------------------------------------------------
// The per-compartment union (ADR-106).
// ---------------------------------------------------------------------------

/** The page's merged view of its compartment twins. Contract-A's sections
 *  are unions, deduplicated on the stable key the contract gives each row —
 *  the same claim filed under two compartments renders once, never twice;
 *  the JSON downloads stay listed per compartment with their licence line. */
export interface MergedEntityPage {
  twin: EntityPageTwin;
  compartments: string[];
  identifiers: { scheme: string; value: string }[];
  summary: EntityPageTwin["summary"];
  claims: EntityClaimGroup[];
  relations: EntityRelationGroup[];
  degreeOnly: DegreeOnlyFact[];
  closures: AccessClosureGroup[];
  claimIds: string[];
}

function itemKey(it: EntityRelationItem): string {
  return JSON.stringify([
    it.counterparty.entity_id ?? it.counterparty.label ?? "",
    it.relation,
    it.role ?? "",
    it.date ?? "",
    it.claim_ids,
  ]);
}

/** The dedupe key for a closure path across compartment twins — direction +
 * the ordered org chain (a path is its hop list; identical chains merge). */
function closurePathKey(p: AccessClosurePath): string {
  return JSON.stringify([p.direction, p.hops.map((h) => h.to_org), p.source]);
}

function closureCounts(paths: AccessClosurePath[]): AccessClosureGroup["counts"] {
  const counts = { publishable: 0, historical: 0, speculative: 0 };
  for (const p of paths) {
    if (p.speculative) counts.speculative += 1;
    else if (p.temporal_status === "historical") counts.historical += 1;
    else counts.publishable += 1;
  }
  return counts;
}

/** Union the compartment twins for one entity key. `twins` is non-empty —
 *  an empty set is the caller's typed `unpaged`/`not_published` state, never
 *  this function's input (SIG-ENG-042). */
export function mergeEntityTwins(twins: readonly EntityPageTwin[]): MergedEntityPage {
  if (twins.length === 0) throw new Error("mergeEntityTwins: no twins to merge");
  const twin = twins[0]!;
  const compartments = [...new Set(twins.map((t) => t.compartment))].sort();

  const identifiers = new Map<string, { scheme: string; value: string }>();
  const summarySeen = new Set<string>();
  const summary: EntityPageTwin["summary"] = [];
  const claims = new Map<string, EntityClaimGroup>();
  const groups = new Map<string, EntityRelationGroup>();
  const degrees = new Map<string, DegreeOnlyFact>();
  const closureGroups = new Map<string, AccessClosureGroup>();
  const claimIds = new Set<string>();

  for (const t of twins) {
    for (const i of t.identifiers) identifiers.set(`${i.scheme}:${i.value}`, i);
    for (const s of t.summary) {
      if (!summarySeen.has(s.text)) {
        summarySeen.add(s.text);
        summary.push(s);
      }
      s.claim_ids.forEach((c) => claimIds.add(c));
    }
    for (const c of t.claims) {
      claims.set(`${c.predicate}:${[...c.claim_ids].sort().join(",")}`, c);
      c.claim_ids.forEach((x) => claimIds.add(x));
    }
    for (const g of t.relations) {
      const gk = `${g.relation}:${g.direction}:${g.access_kind ?? ""}`;
      const existing = groups.get(gk);
      if (existing === undefined) {
        groups.set(gk, {
          ...g,
          items: [...g.items],
          claim_ids: [...g.claim_ids],
        });
      } else {
        const seen = new Set(existing.items.map(itemKey));
        for (const it of g.items) {
          if (!seen.has(itemKey(it))) existing.items.push(it);
        }
        existing.count = Math.max(existing.count, g.count);
        existing.more = Math.max(0, existing.count - existing.items.length);
        for (const c of g.claim_ids) {
          if (!existing.claim_ids.includes(c)) existing.claim_ids.push(c);
        }
      }
      g.claim_ids.forEach((c) => claimIds.add(c));
      g.items.forEach((it) => it.claim_ids.forEach((c) => claimIds.add(c)));
    }
    for (const d of t.access.degree_only) {
      degrees.set(`${d.predicate}:${[...d.claim_ids].sort().join(",")}`, d);
      d.claim_ids.forEach((c) => claimIds.add(c));
    }
    for (const g of t.access.closures ?? []) {
      const gk = g.direction;
      const existing = closureGroups.get(gk);
      if (existing === undefined) {
        closureGroups.set(gk, { ...g, paths: [...g.paths] });
      } else {
        const seen = new Set(existing.paths.map(closurePathKey));
        for (const p of g.paths) {
          if (!seen.has(closurePathKey(p))) existing.paths.push(p);
        }
        // `more` is each twin's own emitted-cap remainder; the merged view
        // keeps the MAX — a conservative lower bound on un-emitted paths
        // (the same overflow can sit behind two compartments, never summed).
        existing.more = Math.max(existing.more, g.more);
      }
      for (const p of g.paths) p.claim_ids.forEach((c) => claimIds.add(c));
    }
  }

  // Re-count the merged groups so the figures describe exactly the merged
  // path set — never a sum that could double-count a path filed under two
  // compartments.
  const closures = [...closureGroups.values()].map((g) => ({
    ...g,
    counts: closureCounts(g.paths),
    path_count: g.paths.length,
  }));

  return {
    twin,
    compartments,
    identifiers: [...identifiers.values()],
    summary,
    claims: [...claims.values()],
    relations: [...groups.values()],
    degreeOnly: [...degrees.values()],
    closures,
    claimIds: [...claimIds].sort(),
  };
}

// ---------------------------------------------------------------------------
// The hub + per-type A–Z model (SIG-UI-070 / UXR-20).
// ---------------------------------------------------------------------------

/** Rows per A–Z list page — the path-paginated static list. */
export const ENTITY_LIST_PAGE_SIZE = 100;

export interface EntityListPage<T> {
  rows: T[];
  page: number;
  pages: number;
  total: number;
}

/** Path-style pagination: page 1 is the type's index route; `page/<n>/`
 *  carries the rest (page numbers are 1-based; `pages` is 0 for an empty
 *  set — the route emits only for `n >= 2`). */
export function paginate<T>(rows: readonly T[], page: number): EntityListPage<T> {
  const total = rows.length;
  const pages = Math.ceil(total / ENTITY_LIST_PAGE_SIZE);
  const start = (page - 1) * ENTITY_LIST_PAGE_SIZE;
  return { rows: rows.slice(start, start + ENTITY_LIST_PAGE_SIZE), page, pages, total };
}

/** The published rows for one url_type (already A–Z sorted by the index),
 *  plus the typed `not_yet_reviewed` records that kind carries — the A-10
 *  state list, never a silent absence. */
export interface EntityTypeList {
  published: EntityLabelRow[];
  review: EntityReviewRecord[];
}

export function typeList(
  index: { rows: EntityLabelRow[]; review_rows: EntityReviewRecord[] },
  urlType: string,
): EntityTypeList {
  return {
    published: index.rows.filter((r) => r.url_type === urlType),
    review: index.review_rows.filter((r) => r.kind === urlType),
  };
}

/** The review rows whose KIND names a type — `url_type` for the contract-A
 *  kinds equals the kind (`org`/`agency`/`portal`); a kind whose url_type
 *  differs stays grouped under its url_type on the hub. */
export function reviewCountByUrlType(
  index: { rows: EntityLabelRow[]; review_rows: EntityReviewRecord[] },
  urlType: string,
): number {
  return typeList(index, urlType).review.length;
}

/** The set of `/entity/<type>/<key>/` paths this build actually emits —
 *  the published label rows' canonical URLs. The `/id/<type>/<uuid>` stub
 *  refreshes only to an emitted successor (K13 R-6: never link a 404); an
 *  entity the label registry did not page (or a fixture the release does
 *  not carry) gets the honest explanation variant instead. */
export function emittedEntityPaths(index: { rows: EntityLabelRow[] }): Set<string> {
  return new Set(
    index.rows.map((r) => withBase(`entity/${r.url_type}/${r.slug}--${r.hash}/`)),
  );
}

// ---------------------------------------------------------------------------
// Typed absence (A-10 / SIG-UI-086) — the words a typed state renders.
// ---------------------------------------------------------------------------

/** The five-part typed state for the `not_yet_reviewed` organisation —
 *  the A-10 state rendered verbatim, never a fabricated label and never a
 *  queue task (the registry review, not research, is the remedy). */
export const NOT_YET_REVIEWED_STATE = {
  state: "Not yet independently reviewed",
  missing:
    "SIG has recorded this organisation but the registry auto-allow review has not keyed it a page. Its name is withheld until that review, never shown as a raw identifier.",
  nearby:
    "The organisations SIG has keyed are listed above; every keyed page cites the claims behind it.",
  action: { href: "methodology/", label: "See how SIG reviews entities" },
  change:
    "A keyed page appears here once the registry auto-allow review matches this organisation in a release.",
} as const;

/** The five-part typed state for a keyed entity whose twin is absent — an
 *  export-consistency gap, surfaced as a typed absence rather than a broken
 *  page (SIG-ENG-042). */
export const TWIN_MISSING_STATE = {
  state: "Recorded, not yet published as a page",
  missing:
    "The label registry keys this entity but its page record did not ship in this build — a publication gap, not a finding about the entity.",
  nearby: "The type's A–Z list carries every entity this release pages.",
  action: { href: "entity/", label: "Back to the entity hub" },
  change: "The page appears with the release that emits its record.",
} as const;
