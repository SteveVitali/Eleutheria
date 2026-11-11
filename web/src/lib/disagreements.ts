// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * P37.38 (R11-K13-CX-01, K13 §2.2/§4.2, SIG-UI-071) — the disagreements
 * browser model: the ONE derivation every `/disagreements/**` route renders.
 *
 * Three typed kinds, kept apart (the catalog cell verbatim):
 *
 *   - **Recorded contradictions** — the materialized contradiction records
 *     the release's `sig.statement/1` streams cite (`contradictions.
 *     contradiction_ids` + `competing_claim_ids`, P35.36). Both sides render:
 *     each named claim with its source and dates — a claim view's published
 *     label where one exists, the statement's `not_recorded`-honest fields
 *     otherwise. Nothing reconciles them (§3.1 — kept visible).
 *   - **Within-source coordinate conflicts** — `sig.dossier-sources/1`'s
 *     `coordinate_conflicts_intra_source`, labelled the identity defects
 *     they are until CONF-03b re-keys the collided subjects (K13 §4.2).
 *   - **Declared-vs-located disagreements** — the `declared_here_
 *     located_elsewhere` / `located_here_declared_elsewhere` pair plus the
 *     per-counterpart `placement.*` rows — visible on BOTH sides (the
 *     declaring dossier's page and the locating dossier's page carry the
 *     same records from opposite directions).
 *
 * Counts come from the release: the contradiction total counts distinct ids
 * across the statement streams; the aggregate kinds read the dossier-sources
 * docs the dossier pages themselves cite (SIG-TRANSP-040 parity by
 * construction — one derivation feeds both surfaces, never a parallel count).
 * A doc's totals already roll up its descendants (placement chains), so a
 * "release total" for the aggregate kinds sums TOP-LEVEL docs only — the
 * partition, never a double count.
 */

import type { StatementRow } from "./provenance-panel";
import type { DossierSourcesDoc, DossierSourceRow } from "./dossier-sources";
import type { ClaimView } from "./evidence-viewer";
import type { EntityLabelRow } from "./entity-page";

// ---------------------------------------------------------------------------
// Routes (sans leading slash — templates join withBase()).
// ---------------------------------------------------------------------------

/** `/disagreements/` — the hub. */
export const DISAGREEMENTS_ROOT = "disagreements/";
/** `/disagreements/place/<slug-path>/` — a dossier's disagreements page. */
export function disagreementPlacePath(slug: string): string {
  return `disagreements/place/${slug}/`;
}
/** The in-page anchor one contradiction record renders under. */
export function disagreementAnchor(contradictionId: string): string {
  return `con-${contradictionId.replace(/[^a-zA-Z0-9_-]+/g, "-")}`;
}

// ---------------------------------------------------------------------------
// The three typed kinds.
// ---------------------------------------------------------------------------

export const DISAGREEMENT_KINDS = [
  "contradiction",
  "coordinate_conflict",
  "declared_vs_located",
] as const;
export type DisagreementKind = (typeof DISAGREEMENT_KINDS)[number];

/** One side of a recorded contradiction — a published claim statement where
 *  the release carries one, else the named absence the id itself records. */
export interface DisagreementSide {
  claim_id: string;
  /** The claim view's published label (e.g. "Active device count = 42") —
   *  `null` when no claim view published for this claim. */
  label: string | null;
  /** `/evidence/claim/<id>/` route when a claim view page exists. */
  claim_href: string | null;
  source_id: string | null;
  source_name: string | null;
  /** `/sources/<id>/` when the release pages this source. */
  source_href: string | null;
  observed_at: string | null;
  recorded_at: string | null;
  /** The claim's subject — the entity the disagreement is ABOUT. */
  entity_id: string | null;
  predicate_id: string | null;
  /** True when this side's `sig.statement/1` row published. */
  statement_published: boolean;
}

/** A recorded contradiction — both sides kept visible. */
export interface ContradictionRecord {
  contradiction_id: string;
  /** The disagreeing claims — every claim the record's statements name. */
  sides: DisagreementSide[];
  /** Subject entity ids across the sides (deduplicated). */
  entity_ids: string[];
  /** The predicate the sides disagree on (deduplicated, joined for display). */
  predicates: string[];
  /** Dossier slug paths whose `sig.dossier-sources/1` doc names this record —
   *  the place links; empty means no place link is recorded (typed absence). */
  place_slugs: string[];
  /** Entity-page URLs for the subject entities that have one. */
  entity_hrefs: { entity_id: string; href: string; label: string | null }[];
}

/** One dossier's declared-vs-located counts — both directions + counterparts. */
export interface PlaceDisagreements {
  slug: string;
  name: string;
  jkey: string | null;
  /** Records this place declares that locate elsewhere. */
  declared_here_located_elsewhere: number;
  /** Records located here that another place declares. */
  located_here_declared_elsewhere: number;
  /** Counterpart rows — `{jkey, records}` per direction, resolved to names. */
  declared_elsewhere: { jkey: string; name: string; slug: string | null; records: number }[];
  located_elsewhere: { jkey: string; name: string; slug: string | null; records: number }[];
}

/** One source's within-source coordinate conflicts. */
export interface CoordinateConflictRow {
  source_id: string;
  name: string;
  /** `/sources/<id>/` when the release pages this source. */
  source_href: string | null;
  records: number;
}

/** A dossier's full disagreements page model. */
export interface PlaceDisagreementPage {
  slug: string;
  name: string;
  jkey: string | null;
  /** The `sig.dossier-sources/1` artifact this page's counts cite. */
  artifact: string;
  contradictions: ContradictionRecord[];
  coordinate_conflicts: { total: number; sources: CoordinateConflictRow[] };
  declared_located: PlaceDisagreements;
  /** The dossier's own page route (the sideways "dossier section" link). */
  dossier_href: string | null;
  /** The dossier's sources explorer (the agreeing/disagreeing ledger) —
   *  always emitted alongside the doc the page renders. */
  sources_href: string;
}

/** The hub model — three kinds + the per-place roll-up. */
export interface DisagreementsIndex {
  contradictions: ContradictionRecord[];
  /** Places carrying ≥1 coordinate conflict, each with its total. */
  coordinate_places: { slug: string; name: string; records: number }[];
  /** Places carrying ≥1 declared-vs-located record (either direction). */
  declared_located_places: {
    slug: string;
    name: string;
    declared_here: number;
    located_here: number;
  }[];
  /** Place-page routes emitted (every emitted dossier-sources doc). */
  place_slugs: string[];
}

// ---------------------------------------------------------------------------
// The derivation.
// ---------------------------------------------------------------------------

/** jkey → `{name, slug}` from the emitted dossier-sources docs themselves. */
export function jkeyPlaceMap(
  docs: ReadonlyMap<string, DossierSourcesDoc>,
): Map<string, { name: string; slug: string }> {
  const out = new Map<string, { name: string; slug: string }>();
  for (const [slug, doc] of docs) {
    const jkey = doc.jurisdiction.jkey;
    if (jkey) out.set(jkey, { name: doc.jurisdiction.name, slug });
  }
  return out;
}

function resolveCounterparts(
  pairs: { jkey: string; records: number }[],
  places: ReadonlyMap<string, { name: string; slug: string }>,
): { jkey: string; name: string; slug: string | null; records: number }[] {
  return pairs.map((p) => ({
    jkey: p.jkey,
    name: places.get(p.jkey)?.name ?? p.jkey,
    slug: places.get(p.jkey)?.slug ?? null,
    records: p.records,
  }));
}

/** Build every contradiction record the statements name — grouped by id,
 *  sides = the claims citing the id plus their recorded competitors. */
export function buildContradictions(
  statements: ReadonlyMap<string, StatementRow>,
  docs: ReadonlyMap<string, DossierSourcesDoc>,
  claimViews: readonly ClaimView[],
  sourcePageIds: ReadonlySet<string>,
  labelRows: readonly EntityLabelRow[],
): ContradictionRecord[] {
  const viewByClaim = new Map(claimViews.map((v) => [v.claim_id, v]));
  const entityById = new Map(labelRows.map((r) => [r.entity_id, r]));
  // contradiction_id → the dossier slug paths whose docs name it.
  const placesByContra = new Map<string, string[]>();
  for (const [slug, doc] of docs) {
    for (const c of doc.cross_source.contradictions) {
      const list = placesByContra.get(c.contradiction_id) ?? [];
      list.push(slug);
      placesByContra.set(c.contradiction_id, list);
    }
  }
  // Group: contradiction_id → the claims citing it.
  const citing = new Map<string, StatementRow[]>();
  for (const row of statements.values()) {
    for (const cid of row.contradictions?.contradiction_ids ?? []) {
      const list = citing.get(cid) ?? [];
      list.push(row);
      citing.set(cid, list);
    }
  }
  // Doc-named records no published statement cites still list (typed absence
  // of sides — the record exists; the claim rows do not publish).
  const ids = new Set<string>([...citing.keys(), ...placesByContra.keys()]);
  const out: ContradictionRecord[] = [];
  for (const cid of [...ids].sort()) {
    const rows = citing.get(cid) ?? [];
    // The side set: citing claims + their recorded competitors (deduped,
    // ordered by claim_id — deterministic).
    const sideIds = new Map<string, StatementRow | null>();
    for (const row of rows) {
      sideIds.set(row.claim_id, row);
      for (const comp of row.contradictions?.competing_claim_ids ?? []) {
        if (!sideIds.has(comp)) sideIds.set(comp, statements.get(comp) ?? null);
      }
    }
    const sides: DisagreementSide[] = [...sideIds.entries()]
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([claimId, stmt]) => {
        const view = viewByClaim.get(claimId);
        const src = stmt?.source_id ?? null;
        return {
          claim_id: claimId,
          label:
            view !== undefined ? `${view.claim_label} = ${String(view.value)}` : null,
          claim_href: view !== undefined ? `evidence/claim/${view.claim_id}/` : null,
          source_id: src,
          source_name: stmt?.source_name ?? null,
          source_href:
            src !== null && sourcePageIds.has(src) ? `sources/${src}/` : null,
          observed_at: stmt?.observed_at ?? null,
          recorded_at: stmt?.recorded?.at ?? null,
          entity_id: stmt?.entity_id ?? null,
          predicate_id: stmt?.predicate_id ?? null,
          statement_published: stmt !== null && stmt !== undefined,
        };
      });
    const entityIds = [...new Set(sides.map((s) => s.entity_id).filter((e): e is string => e !== null))].sort();
    const predicates = [...new Set(sides.map((s) => s.predicate_id).filter((p): p is string => p !== null))].sort();
    const entityHrefs = entityIds.flatMap((eid) => {
      const row = entityById.get(eid);
      return row?.url ? [{ entity_id: eid, href: row.url, label: row.label ?? null }] : [];
    });
    out.push({
      contradiction_id: cid,
      sides,
      entity_ids: entityIds,
      predicates,
      place_slugs: (placesByContra.get(cid) ?? []).sort(),
      entity_hrefs: entityHrefs,
    });
  }
  return out;
}

/** One dossier's disagreements page model from its `sig.dossier-sources/1` doc. */
export function placeDisagreementPage(
  slug: string,
  doc: DossierSourcesDoc,
  contradictions: readonly ContradictionRecord[],
  docs: ReadonlyMap<string, DossierSourcesDoc>,
  dossierSlugs: ReadonlySet<string>,
): PlaceDisagreementPage {
  const places = jkeyPlaceMap(docs);
  const conflictSources: CoordinateConflictRow[] = doc.sources
    .filter((s) => s.coordinate_conflicts_intra_source > 0)
    .map((s: DossierSourceRow) => ({
      source_id: s.source_id,
      name: s.name,
      source_href: s.source_page ? s.source_page.replace(/^\/+/, "") : null,
      records: s.coordinate_conflicts_intra_source,
    }));
  return {
    slug,
    name: doc.jurisdiction.name,
    jkey: doc.jurisdiction.jkey,
    artifact: `web/dossier_sources/${slug}.json`,
    contradictions: contradictions.filter((c) => c.place_slugs.includes(slug)),
    coordinate_conflicts: {
      total: doc.totals.coordinate_conflicts_intra_source,
      sources: conflictSources,
    },
    declared_located: {
      slug,
      name: doc.jurisdiction.name,
      jkey: doc.jurisdiction.jkey,
      declared_here_located_elsewhere: doc.totals.declared_here_located_elsewhere,
      located_here_declared_elsewhere: doc.totals.located_here_declared_elsewhere,
      declared_elsewhere: resolveCounterparts(doc.placement.declared_elsewhere_located_here, places),
      located_elsewhere: resolveCounterparts(doc.placement.declared_here_located_elsewhere, places),
    },
    dossier_href: dossierSlugs.has(slug) ? `dossier/${slug}/` : null,
    sources_href: `dossier/${slug}/sources/`,
  };
}

/** The hub model — every kind, deduplicated, over the whole release. */
export function disagreementsIndex(
  statements: ReadonlyMap<string, StatementRow>,
  docs: ReadonlyMap<string, DossierSourcesDoc>,
  claimViews: readonly ClaimView[],
  sourcePageIds: ReadonlySet<string>,
  labelRows: readonly EntityLabelRow[],
): DisagreementsIndex {
  const contradictions = buildContradictions(statements, docs, claimViews, sourcePageIds, labelRows);
  const coordinate_places = [...docs.entries()]
    .filter(([, doc]) => doc.totals.coordinate_conflicts_intra_source > 0)
    .map(([slug, doc]) => ({
      slug,
      name: doc.jurisdiction.name,
      records: doc.totals.coordinate_conflicts_intra_source,
    }))
    .sort((a, b) => b.records - a.records || a.slug.localeCompare(b.slug));
  const declared_located_places = [...docs.entries()]
    .filter(
      ([, doc]) =>
        doc.totals.declared_here_located_elsewhere > 0 ||
        doc.totals.located_here_declared_elsewhere > 0,
    )
    .map(([slug, doc]) => ({
      slug,
      name: doc.jurisdiction.name,
      declared_here: doc.totals.declared_here_located_elsewhere,
      located_here: doc.totals.located_here_declared_elsewhere,
    }))
    .sort(
      (a, b) =>
        b.declared_here + b.located_here - (a.declared_here + a.located_here) ||
        a.slug.localeCompare(b.slug),
    );
  return {
    contradictions,
    coordinate_places,
    declared_located_places,
    place_slugs: [...docs.keys()].sort(),
  };
}
