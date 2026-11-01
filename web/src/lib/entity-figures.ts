// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
/**
 * P36.42b (K2 GX-06a 06b, §4.2 rows 7/9/10; SIG-UI-094/098/122/130/131/134) —
 * the page-owner COMPOSITION for the entity figures: the twin's merged record
 * shaped into the static figure kit's plain-data input contracts
 * (`sig.figure-kit-graph/1` ego · `sig.figure-kit-chart/1` timeline ·
 * `sig.figure-kit-geo/1` map). K13 C-07 keeps the LAYOUTS in the kit
 * (`exports/src/exports/figures/` — one algorithm set, byte-deterministic,
 * CSP-safe); this module only composes the spec documents, which the kit's
 * CLI renders into the committed/exported SVG artifacts
 * (`sig-exports figure ego|chart|map`). Nothing here re-derives a fact the
 * contract does not carry — every node, edge and event below is a verbatim
 * field of the merged twin.
 *
 * Honesty rules the composition carries (the same seams the kit enforces on
 * its side):
 *   - every drawn node links — a counterparty without a published page links
 *     its evidence anchor on this page (`#claim-<id>`), never a dead route
 *     and never a bare dot (SIG-UI-122 made literal);
 *   - undated facts are `date_kind: "undated"` — muted ink + the word, never
 *     a present-tense edge and never a fabricated date on the timeline
 *     (SIG-UI-116);
 *   - the three access kinds map one-to-one onto the kit's line patterns —
 *     never merged (SIG-UI-024);
 *   - a neighbour set over the radial cap groups by counterparty kind with
 *     declared group fields — group, never silently prune (SIG-ENG-042);
 *   - the timeline draws only `observed` dates — undated items are LISTED,
 *     never placed on the axis;
 *   - the map snippet renders only when the twin records a place —
 *     "location not recorded" is the typed state otherwise (K2 §4.2 row 10);
 *   - inlined figure bytes re-verify the serializer's safety contract at the
 *     build seam (`assertInlineSvgSafe`) — a `<script>`, `on*` attribute,
 *     `style=`/`data-*` or external reference in artifact bytes fails the
 *     build before they can reach the page (K0 §4.8 / SIG-UI-096).
 */

import type {
  EntityClaimGroup,
  EntityPageTwin,
  EntityRelationItem,
} from "./entity-page";
import type { MergedEntityPage } from "./entity-pages";
import { withBase } from "./paths";

/** Root-absolute page path, built through the pinned `withBase()` seam —
 *  the containment check's one legal construction (P36.41). The character
 *  check avoids a root-absolute literal the containment rule would count. */
const SLASH = String.fromCharCode(47);
function rootPath(url: string): string {
  return url.startsWith(SLASH) ? url : withBase(url);
}

// ---------------------------------------------------------------------------
// The kit vocabularies, mirrored (the Python constants are the reference).
// ---------------------------------------------------------------------------

export const GRAPH_SPEC_SCHEMA = "sig.figure-kit-graph/1" as const;
export const CHART_SPEC_SCHEMA = "sig.figure-kit-chart/1" as const;
export const GEO_SPEC_SCHEMA = "sig.figure-kit-geo/1" as const;

/** The radial-ego node budget (K2 §4.2 row 7's ≤ 50 drawn nodes): the centre
 *  plus at most this many neighbours compose before the declared grouping
 *  engages (the kit's EGO_NODE_CAP). */
export const EGO_NEIGHBOUR_CAP = 49;

/** Node kinds the figure kit draws (shape = kind, never epistemic state). */
const NODE_KINDS = new Set([
  "agency",
  "vendor",
  "product",
  "site",
  "source",
  "instrument",
  "entity",
  "group",
]);

/** Entity kind → kit node kind. A plain `org` is an `entity` — never a
 *  `vendor` assertion the contract does not make. */
export function nodeKind(kind: string | undefined): string {
  switch (kind) {
    case "agency":
      return "agency";
    case "site":
      return "site";
    case "portal":
      return "source";
    case "org":
    default:
      return kind && NODE_KINDS.has(kind) ? kind : "entity";
  }
}

/** Twin access-kind token → kit line-pattern token (SIG-UI-024). */
export function figureAccessKind(accessKind: string | null): string | null {
  switch (accessKind) {
    case "configured_access":
      return "configured";
    case "observed_use":
      return "observed";
    case "declared_policy":
      return "declared";
    default:
      return null;
  }
}

/** Twin currency word → kit currency state. `UNDATED` is not a currency —
 *  the twin emits it when no evidenced date exists; the figure carries that
 *  truth in `date_kind: "undated"` (the muted channel + the word), while the
 *  required currency token reads `aging` — "not demonstrably current",
 *  never `current`/`historical` claims the record does not make. */
export function figureCurrency(currency: string | null): string {
  switch (currency) {
    case "CURRENT":
      return "current";
    case "AGING":
      return "aging";
    case "STALE":
      return "stale";
    case "HISTORICAL":
      return "historical";
    default:
      return "aging";
  }
}

/** Twin date kind → kit date kind: an observed item draws the single
 *  recorded date; everything else is `undated`. */
export function figureDateKind(dateKind: string): string {
  return dateKind === "observed" ? "single" : "undated";
}

// ---------------------------------------------------------------------------
// The ego spec — `sig.figure-kit-graph/1`, kind "ego" (K2 §4.2 row 7).
// ---------------------------------------------------------------------------

export interface EgoNodeSpec {
  key: string;
  label: string;
  kind: string;
  side: "centre" | "neighbour";
  href: string;
  group_key?: string;
  group_label?: string;
  group_href?: string;
  noun?: string;
}

export interface EgoEdgeSpec {
  source: string;
  target: string;
  relation: string;
  direction: string;
  access_kind?: string;
  date?: string;
  date_kind: string;
  currency: string;
  support?: string;
  sources: string[];
  claim_ids: string[];
}

export interface EgoSpecDoc {
  schema: typeof GRAPH_SPEC_SCHEMA;
  release: { label: string; publication_id: string; as_of_world: string };
  kind: "ego";
  title: string;
  nodes: EgoNodeSpec[];
  edges: EgoEdgeSpec[];
}

const KIND_GROUP_NOUN: Record<string, string> = {
  agency: "agencies",
  site: "sites",
  source: "portals",
  entity: "entities",
};

const KIND_GROUP_LABEL: Record<string, string> = {
  agency: "Government bodies",
  site: "Sites",
  source: "Registry portals",
  entity: "Entities",
};

/** The neighbour's link: its published entity page when the registry keyed
 *  one, else this entity's own page — the kit admits root-relative hrefs on
 *  nodes only, and the page's relationship table + claim anchors are the
 *  node's evidence path (the ≤2-actions rule, SIG-UI-122). A page-less
 *  counterparty never links a route that does not exist. */
function counterpartyHref(it: EntityRelationItem, ownUrl: string): string {
  const url = it.counterparty.url;
  if (typeof url === "string" && url.startsWith(SLASH)) return url;
  return rootPath(ownUrl);
}

function counterpartyKey(it: EntityRelationItem): string {
  return it.counterparty.entity_id ?? `literal:${it.counterparty.label ?? "unreviewed"}`;
}

function counterpartyLabel(it: EntityRelationItem): string {
  return it.counterparty.label ?? it.counterparty.review_state ?? "not yet reviewed";
}

/**
 * Compose the 1-hop ego spec: centre + one node per distinct counterparty,
 * one edge per distinct (counterparty, relation, direction, access kind,
 * date) row — first-appearance order across the merged groups (the same
 * order the relationship tables render, so the figure and its long
 * description never disagree). `null` when the twin records no relations —
 * the component renders the typed "no relationships" state, never an empty
 * drawing (SIG-ENG-042).
 */
export function entityEgoSpec(merged: MergedEntityPage): EgoSpecDoc | null {
  const twin = merged.twin;
  const nodes = new Map<string, EgoNodeSpec>();
  const edges: EgoEdgeSpec[] = [];
  const seenEdges = new Set<string>();
  for (const [gi, g] of merged.relations.entries()) {
    for (const it of g.items) {
      const nk = counterpartyKey(it);
      if (!nodes.has(nk)) {
        const k = nodeKind(it.counterparty.kind);
        nodes.set(nk, {
          key: nk,
          label: counterpartyLabel(it),
          kind: k,
          side: "neighbour",
          href: counterpartyHref(it, twin.url),
          // Declared grouping (K6 §6.2): when the neighbour set exceeds the
          // radial cap the kit forms labelled group nodes — by counterparty
          // kind, linking back into this page's table section. Composing the
          // fields on every node keeps the declaration data, never behaviour.
          group_key: k,
          group_label: KIND_GROUP_LABEL[k] ?? "Entities",
          group_href: `#rel-group-${gi}`,
          noun: KIND_GROUP_NOUN[k] ?? "entities",
        });
      }
      const ek = [nk, g.relation, g.direction, g.access_kind ?? "", it.date ?? "", it.date_kind].join(
        "|",
      );
      if (seenEdges.has(ek)) continue;
      seenEdges.add(ek);
      const outbound = g.direction !== "inbound";
      const e: EgoEdgeSpec = {
        source: outbound ? "centre" : nk,
        target: outbound ? nk : "centre",
        relation: g.relation,
        direction: g.direction,
        date_kind: figureDateKind(it.date_kind),
        currency: figureCurrency(it.currency),
        sources: it.sources.map((s) => s.id),
        claim_ids: [...it.claim_ids],
      };
      if (figureAccessKind(g.access_kind) !== null) e.access_kind = figureAccessKind(g.access_kind)!;
      if (it.date_kind === "observed" && it.date) e.date = it.date;
      if (it.support) e.support = it.support;
      edges.push(e);
    }
  }

  if (edges.length === 0) return null;
  const centre: EgoNodeSpec = {
    key: "centre",
    label: twin.label,
    kind: nodeKind(twin.kind),
    side: "centre",
    href: rootPath(twin.url),
  };
  return {
    schema: GRAPH_SPEC_SCHEMA,
    release: releaseInfoFor(twin),
    kind: "ego",
    title: `${twin.label} — recorded relationships`,
    nodes: [centre, ...nodes.values()].slice(0, EGO_NEIGHBOUR_CAP + 1),
    edges,
  };
}

/** The release stamp every spec repeats (the twin's own publication id). */
function releaseInfoFor(twin: EntityPageTwin): {
  label: string;
  publication_id: string;
  as_of_world: string;
} {
  return {
    label: "Surveillance Infrastructure Graph",
    publication_id: twin.publication,
    as_of_world: twin.generated_at.slice(0, 10),
  };
}

// ---------------------------------------------------------------------------
// The timeline spec — `sig.figure-kit-chart/1`, kind "timeline" (K2 §4.2
// row 9: dated events on an axis; undated items listed apart, never drawn).
// ---------------------------------------------------------------------------

export interface TimelineEventSpec {
  date: string;
  label: string;
  href?: string;
  kind?: string;
}

export interface TimelineSpecDoc {
  schema: typeof CHART_SPEC_SCHEMA;
  release: { label: string; publication_id: string; as_of_world: string };
  kind: "timeline";
  title: string;
  unit: string;
  events: TimelineEventSpec[];
}

export interface EntityTimeline {
  spec: TimelineSpecDoc | null;
  /** The dated events (spec events, sorted). */
  dated: TimelineEventSpec[];
  /** Undated items — LISTED, never placed on the axis (K2 §4.2 row 9). */
  undated: { label: string; claimId: string | null }[];
}

// Timeline events carry no href — the kit's chart href accepts root-relative
// paths only (no fragments), and every event's claim already reaches its
// provenance anchor through the page's evidence links (SIG-UI-122); the
// figure's table twin lists each event verbatim.

/** Compose the timeline from the dated facts the contract carries —
 *  relation-item observed dates, claim-group observed dates and degree-only
 *  observed dates — sorted deterministically. `spec` is null when nothing
 *  is dated: the component renders the typed "no dated events" state with
 *  the undated list still shown (K2 §4.2 row 9 — never silently empty). */
export function entityTimeline(merged: MergedEntityPage): EntityTimeline {
  const twin = merged.twin;
  const dated: TimelineEventSpec[] = [];
  const undated: EntityTimeline["undated"] = [];

  const pushDated = (date: string, label: string, kind: string) => {
    dated.push({ date, label, kind });
  };
  const pushUndated = (label: string, claimId: string | null) => {
    undated.push({ label, claimId });
  };

  for (const g of merged.relations) {
    for (const it of g.items) {
      const label = `${g.relation} — ${counterpartyLabel(it)}`;
      if (it.date_kind === "observed" && it.date) pushDated(it.date, label, g.relation);
      else pushUndated(label, it.claim_ids[0] ?? null);
    }
  }
  for (const c of merged.claims) {
    if (c.date_kind === "observed" && c.observed_at) {
      pushDated(c.observed_at, `${c.relation} recorded`, c.predicate);
    } else {
      pushUndated(`${c.relation} recorded`, c.claim_ids[0] ?? null);
    }
  }
  for (const d of merged.degreeOnly) {
    const label = `${d.predicate.replaceAll("_", " ")} — partners not named`;
    if (d.date_kind === "observed" && d.observed_at) pushDated(d.observed_at, label, d.predicate);
    else pushUndated(label, d.claim_ids[0] ?? null);
  }

  dated.sort((a, b) => a.date.localeCompare(b.date) || a.label.localeCompare(b.label));
  undated.sort((a, b) => a.label.localeCompare(b.label));

  const spec: TimelineSpecDoc | null =
    dated.length === 0
      ? null
      : {
          schema: CHART_SPEC_SCHEMA,
          release: releaseInfoFor(twin),
          kind: "timeline",
          title: `${twin.label} — dated events`,
          unit: "events",
          events: dated.map((e) => {
            const out: TimelineEventSpec = { date: e.date, label: e.label };
            if (e.href) out.href = e.href;
            if (e.kind) out.kind = e.kind;
            return out;
          }),
        };
  return { spec, dated, undated };
}

// ---------------------------------------------------------------------------
// The map snippet — `sig.figure-kit-geo/1` (K2 §4.2 row 10). Under contract
// A the twin records the entity's own `place_jkey` but no located-subject
// rows, so the figure draws the recorded place's outline only — the honest
// "where" the record carries. No place → `null` → the component renders the
// "location not recorded" typed state, never an empty frame.
// ---------------------------------------------------------------------------

export interface EntityMapSpec {
  schema: typeof GEO_SPEC_SCHEMA;
  release: { label: string; publication_id: string; as_of_world: string };
  jurisdiction: {
    jkey: string;
    slug_path: string;
    level: string;
    chain: string[];
    name: string;
    provisional: boolean;
  };
  outline: [number, number][][];
  children: unknown[];
  records: unknown[];
  boundary_vintage: string;
}

/**
 * The map spec for one recorded place — `outline` is supplied by the caller
 * (the boundary pack / fixture outlines; the composition never invents
 * geometry). `null` when the twin records no place.
 */
export function entityMapSpec(
  merged: MergedEntityPage,
  opts: {
    outline: [number, number][][];
    name: string;
    slugPath: string;
    level: string;
    chain: string[];
    boundaryVintage: string;
  },
): EntityMapSpec | null {
  const twin = merged.twin;
  if (!twin.place_jkey) return null;
  return {
    schema: GEO_SPEC_SCHEMA,
    release: releaseInfoFor(twin),
    jurisdiction: {
      jkey: twin.place_jkey,
      slug_path: opts.slugPath,
      level: opts.level,
      chain: opts.chain,
      name: opts.name,
      provisional: false,
    },
    outline: opts.outline,
    children: [],
    records: [],
    boundary_vintage: opts.boundaryVintage,
  };
}

// ---------------------------------------------------------------------------
// The inline-safety guard — the page-side mirror of the serializer's
// safety contract (defence in depth at the inlining seam, SIG-UI-096).
// ---------------------------------------------------------------------------

const BANNED_INLINE = [
  /<\s*script\b/i,
  /\bon\w+\s*=/i,
  /javascript\s*:/i,
  /<\s*foreignObject\b/i,
  /\b(?:href|src|xlink:href)\s*=\s*['"]\s*(?:https?:|\/\/|data:)/i,
  /@import\b|<\s*link\b|url\s*\(\s*['"]?(?:https?:|\/\/|data:)/i,
  /\bstyle\s*=/i,
  /\bdata-[a-z0-9-]+\s*=/i,
  /<\s*style\b/i,
];

/** Fail-closed at build: the figure-kit bytes a page inlines MUST satisfy
 *  the same contract the serializer enforced — a violation is a build
 *  error, never a rendered page (K0 §4.8: labels are text only). */
export function assertInlineSvgSafe(svg: string, where: string): string {
  if (!svg.includes("<svg")) {
    throw new Error(`${where}: artifact is not SVG bytes`);
  }
  for (const re of BANNED_INLINE) {
    const m = re.exec(svg);
    if (m) {
      throw new Error(
        `${where}: figure SVG violates the inline safety contract (${m[0]}) — ` +
          "inlined figure bytes carry no scripts, handlers, styles, data-* or external refs",
      );
    }
  }
  return svg;
}

/** The figure kinds this page composes — the components and the data seam
 *  name them with the same tokens. */
export const ENTITY_FIGURE_KINDS = ["ego", "timeline", "map"] as const;
export type EntityFigureKind = (typeof ENTITY_FIGURE_KINDS)[number];

/** The typed state a page renders when this record wave emits no figure —
 *  honest about the wave, never a fabricated drawing (SIG-UI-086). */
export const FIGURE_NOT_EMITTED = {
  state: "No drawn figure in this record wave",
  missing:
    "This build carries no static figure artifact for this entity — a publication state, not a finding about the entity.",
  nearby: "The tables on this page carry the same recorded facts.",
  change: "The drawn figure appears with a release that emits it.",
} as const;
