// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * P36.34 (K4 JUR-04 / R11-K13-JUR-04) — the grouped dossier index model.
 *
 * Pure functions over the `sig.dossier-index/2` row set (plus the flat v1
 * rows a pre-keyed build still carries):
 *
 *   - `groupIndex` — the K4 §5.1 structure: the United States first (its
 *     states and territories nested, subdivisions under them), then the
 *     other countries A–Z with their subdivisions, then the honest
 *     demonstration/legacy tail for rows carrying no canonical key.
 *   - `sortIndex` — the pre-rendered GET sort routes' keys
 *     (`/dossier/sort/<k>/`), applied inside every sibling group so a
 *     parent's conservation ordering is never silently re-rolled.
 *   - `facetIndex` — the single-dimension facet routes
 *     (`/dossier/by/<dim>/<value>/`): level, single-source, evidence-type.
 *   - `azGroups` — the A–Z directory (`/dossier/a-z/<letter>/`): every
 *     dossier reachable by name, the no-JS first-letter fallback the
 *     place form documents (C-24).
 *   - `publicationRegime` — SIG-JUR-010: the regime derived from the
 *     row's COUNTRY code, conservative when no adapter exists.
 *   - `INDEX_FIELD_DEFINITIONS` — the named definitions each row field
 *     carries (K4 §5.2 "each with a named definition", J3 §4.1 style).
 *
 * Nothing here fabricates: a row without a field renders the typed
 * absence, and an unkeyed row never pretends a canonical key.
 */

import { adapterFor } from "./publication";
import type { DossierIndexRow } from "./data";

/** True when the row carries the canonical keyed identity (a v2 row). */
export function isKeyedIndexRow(row: DossierIndexRow): boolean {
  return typeof row.jkey === "string" && row.jkey.length > 0;
}

/** The row's display name — name first, the key secondary (SIG-JUR-008). */
export function rowName(row: DossierIndexRow): string {
  return row.display_name ?? row.name ?? row.subject_label;
}

// --- Grouping ----------------------------------------------------------------

export interface IndexTreeNode {
  row: DossierIndexRow;
  /** Registry children that mint their own page; a no-page registry child
   *  never appears here — it is a named absence on the parent's dossier. */
  children: IndexTreeNode[];
}

export interface GroupedIndex {
  /** The United States root (null when no US row exists). */
  unitedStates: IndexTreeNode | null;
  /** Every non-US country root, A–Z by display name. */
  otherCountries: IndexTreeNode[];
  /** Rows with no canonical key (fixture/v1 demonstration dossiers) — an
   *  honest trailing group, never folded into the canonical tree. */
  unkeyed: DossierIndexRow[];
}

const US_JKEY = "iso3166-1:US";

/**
 * Group the index rows into the K4 §5.1 tree. Parenting resolves through
 * `parent_jkey` first; when the registry parent has no page row (a
 * below-threshold unit like a 1–9-record county), the slug path climbs one
 * segment at a time until a page ancestor is found — the same climb the
 * breadcrumb makes — so a leaf never lands orphaned at root.
 */
export function groupIndex(rows: readonly DossierIndexRow[]): GroupedIndex {
  const keyed = rows.filter(isKeyedIndexRow);
  const unkeyed = rows.filter((r) => !isKeyedIndexRow(r));
  const nodes = new Map<string, IndexTreeNode>(
    keyed.map((r) => [r.jkey!, { row: r, children: [] }]),
  );
  const bySlug = new Map<string, IndexTreeNode>(
    keyed.map((r) => [r.slug_path ?? r.slug, nodes.get(r.jkey!)!]),
  );
  const findParent = (row: DossierIndexRow): IndexTreeNode | null => {
    const direct = row.parent_jkey ? nodes.get(row.parent_jkey) : undefined;
    if (direct) return direct;
    // Registry parent has no page — climb the slug path to the nearest
    // ancestor that does (Norman → usa/ok under a no-page county).
    let path = row.parent_slug_path ?? "";
    while (path.includes("/")) {
      path = path.slice(0, path.lastIndexOf("/"));
      const found = bySlug.get(path);
      if (found) return found;
    }
    return null;
  };
  const roots: IndexTreeNode[] = [];
  for (const r of keyed) {
    const node = nodes.get(r.jkey!)!;
    const parent = findParent(r);
    if (parent && parent !== node) parent.children.push(node);
    else roots.push(node);
  }
  const byName = (a: IndexTreeNode, b: IndexTreeNode) =>
    rowName(a.row).localeCompare(rowName(b.row));
  const sortRec = (n: IndexTreeNode) => {
    n.children.sort(byName);
    n.children.forEach(sortRec);
  };
  roots.forEach(sortRec);
  const us = roots.find((n) => n.row.jkey === US_JKEY) ?? null;
  const otherCountries = roots.filter((n) => n !== us).sort(byName);
  return { unitedStates: us, otherCountries, unkeyed };
}

// --- Sorting (the `/dossier/sort/<k>/` GET routes) ----------------------------

export const SORT_KEYS = ["name", "records", "sources", "freshness", "disagreements"] as const;
export type IndexSortKey = (typeof SORT_KEYS)[number];

export function isSortKey(k: string): k is IndexSortKey {
  return (SORT_KEYS as readonly string[]).includes(k);
}

/** The comparison key for one sort dimension (descending except `name`). */
function sortMetric(row: DossierIndexRow, key: IndexSortKey): number | string {
  switch (key) {
    case "records":
      return row.records ?? -1;
    case "sources":
      return row.sources?.count ?? -1;
    case "freshness":
      return row.freshness?.newest ?? "";
    case "disagreements":
      return (
        (row.disagreements?.declared_here_located_elsewhere ?? 0) +
        (row.disagreements?.located_here_declared_elsewhere ?? 0)
      );
    default:
      return rowName(row).toLowerCase();
  }
}

/** Sort each node's children by `key` (name ascending; numbers/dates descending). */
export function sortIndex(root: IndexTreeNode | null, key: IndexSortKey): void {
  if (!root) return;
  const cmp =
    key === "name"
      ? (a: IndexTreeNode, b: IndexTreeNode) =>
          String(sortMetric(a.row, key)).localeCompare(String(sortMetric(b.row, key)))
      : (a: IndexTreeNode, b: IndexTreeNode) => {
          const av = sortMetric(a.row, key);
          const bv = sortMetric(b.row, key);
          if (av === bv) return rowName(a.row).localeCompare(rowName(b.row));
          return av > bv ? -1 : 1;
        };
  const rec = (n: IndexTreeNode) => {
    n.children.sort(cmp);
    n.children.forEach(rec);
  };
  rec(root);
}

// --- Facets (the `/dossier/by/<dim>/<value>/` GET routes) ----------------------

export const FACET_DIMS = ["level", "single-source", "evidence-type"] as const;
export type IndexFacetDim = (typeof FACET_DIMS)[number];

/** The level vocabulary a facet route accepts (wire form, not display). */
export const LEVEL_FACET_VALUES = ["country", "state-province", "county", "place"] as const;

/** The facet values that exist in `rows` for `dim` (emitted routes only — an
 *  empty value never mints a page). */
export function facetValues(rows: readonly DossierIndexRow[], dim: IndexFacetDim): string[] {
  return [...new Set(rows.filter((r) => facetMatch(r, dim) !== null).map((r) => facetMatch(r, dim)!))].sort();
}

/** The facet value `row` belongs to under `dim`, or null. */
function facetMatch(row: DossierIndexRow, dim: IndexFacetDim): string | null {
  switch (dim) {
    case "level": {
      const l = row.level;
      if (l === "country") return "country";
      if (l === "state_province") return "state-province";
      if (l === "county") return "county";
      if (l === "municipality") return "place";
      return null;
    }
    case "single-source": {
      if (row.sources === undefined) return null;
      return row.sources.count <= 1 ? "yes" : "no";
    }
    case "evidence-type": {
      const et = row.evidence_types;
      if (et === undefined) return null;
      const nonSite = Object.values(et.other_classes ?? {}).some((v) => typeof v === "number" && v > 0);
      return nonSite ? "non-site-evidence" : "site-observations";
    }
    default:
      return null;
  }
}

/** The rows matching a facet route (`/dossier/by/<dim>/<value>/`). */
export function facetIndex(
  rows: readonly DossierIndexRow[],
  dim: IndexFacetDim,
  value: string,
): DossierIndexRow[] {
  return rows.filter((r) => facetMatch(r, dim) === value);
}

export function isFacetDim(d: string): d is IndexFacetDim {
  return (FACET_DIMS as readonly string[]).includes(d);
}

// --- The A–Z directory --------------------------------------------------------

/** The directory letter for a row (first name letter, ASCII-folded). */
export function azLetter(row: DossierIndexRow): string {
  const name = rowName(row);
  const ch = name.normalize("NFKD").replace(/[̀-ͯ]/g, "").charAt(0).toLowerCase();
  return /[a-z]/.test(ch) ? ch : "#";
}

/** letter → sorted rows — every index row is covered by exactly one letter. */
export function azGroups(rows: readonly DossierIndexRow[]): Map<string, DossierIndexRow[]> {
  const map = new Map<string, DossierIndexRow[]>();
  for (const r of rows) {
    const letter = azLetter(r);
    const list = map.get(letter) ?? [];
    list.push(r);
    map.set(letter, list);
  }
  for (const list of map.values()) {
    list.sort((a, b) => rowName(a).localeCompare(rowName(b)));
  }
  return new Map([...map.entries()].sort(([a], [b]) => a.localeCompare(b)));
}

// --- Publication regime (SIG-JUR-010) ----------------------------------------

export interface PublicationRegime {
  /** The country code the regime was derived from (the row's own key's country). */
  country_code: string;
  /** The adapter's named profile ("US-DEFAULT", "FR-GDPR"), or "UNKNOWN". */
  profile: string;
  /** True when a real adapter governed; false → the conservative profile. */
  adapter: boolean;
}

/**
 * The publication regime for an index row — derived from its COUNTRY code
 * (`jurisdictionCode`, or the country segment of its key family), never the
 * leaf's code. A country without an adapter lands on the conservative
 * profile — the adapter set is closed (D-K4-7).
 */
export function publicationRegime(row: DossierIndexRow): PublicationRegime | null {
  let a2 = row.jurisdictionCode;
  if (a2 === undefined || a2 === null || a2 === "") {
    const j = row.jkey ?? "";
    if (j.startsWith("iso3166-1:")) a2 = j.slice("iso3166-1:".length);
    else if (j.startsWith("iso3166-2:")) a2 = j.slice("iso3166-2:".length).split("-")[0];
    else if (j.startsWith("us.census.geoid.")) a2 = "US";
  }
  if (!a2) return null;
  const adapter = adapterFor(a2);
  return {
    country_code: a2,
    profile: adapter.profile,
    adapter: adapter.profile !== "UNKNOWN",
  };
}

/** The row's map link — `/map/?jurisdiction=<jkey>` frames the map on the
 *  jurisdiction's records (the workspace-state `jurisdiction` param; a
 *  no-JS baseline — the static map page lists the same records). */
export function mapHrefFor(row: DossierIndexRow): string | null {
  if (!row.jkey) return null;
  return `map/?jurisdiction=${encodeURIComponent(row.jkey)}`;
}

// --- Named field definitions (K4 §5.2 — "each with a named definition") -------

export const INDEX_FIELD_DEFINITIONS: readonly { id: string; field: string; definition: string }[] = [
  {
    id: "place",
    field: "Place",
    definition:
      "The jurisdiction's registry name with its parent name. The scheme-qualified code and level are secondary — codes never lead (SIG-JUR-008).",
  },
  {
    id: "records",
    field: "Records",
    definition:
      "Published observation-level records placed here — never \"devices\". A parent's count equals the sum of its children plus records placed only at the parent level (SIG-JUR-007).",
  },
  {
    id: "located",
    field: "Located",
    definition:
      "How many of the placed records were placed by their own coordinates; the rest were placed by declared jurisdiction.",
  },
  {
    id: "sources",
    field: "Sources",
    definition: "Sources with published claims placed here, with up to three named.",
  },
  {
    id: "evidence-types",
    field: "Evidence types",
    definition:
      "Which evidence classes place records here — site observations today; other classes arrive with non-site attribution.",
  },
  {
    id: "open-questions",
    field: "Open questions",
    definition: "Count of dossier fields rendered \"unknown\", with absence kinds.",
  },
  {
    id: "disagreements",
    field: "Disagreements",
    definition:
      "Records whose declared and located jurisdictions disagree — counted where located and disclosed on both sides.",
  },
  {
    id: "freshness",
    field: "Freshness",
    definition: "Newest and oldest last successful run among the row's sources.",
  },
  {
    id: "children",
    field: "Children",
    definition:
      "Registry children with records — and how many mint their own dossier under the operator's page threshold.",
  },
  {
    id: "publication-regime",
    field: "Publication regime",
    definition:
      "The §43.8 adapter derived from the row's country key; a country without an adapter uses the conservative profile (SIG-JUR-010).",
  },
];

// --- The figure registry the index pages register (UXR-34 / SIG-TRANSP-013) --

import { artifactHref, dossierTargets } from "./figures";
import type { FigureSpec } from "./figures";

/**
 * One `FigureSpec` per material numeral the row table renders, for every
 * keyed index row (a flat row renders only its name — v1 has no row facts).
 * `keyedRows` must be the doc-order keyed row set (the order the
 * `sig.dossier-index/2` artifact carries): figure pointers name
 * `/dossiers/<i>/<field>` inside `web/dossiers/index.json`.
 */
export function indexFigureSpecs(keyedRows: readonly DossierIndexRow[]): FigureSpec[] {
  const specs: FigureSpec[] = [];
  const base = (_i: number, id: string, value: number, pointer: string): FigureSpec => ({
    id,
    class: "dossier",
    value,
    unit: "records",
    artifact: "web/dossiers/index.json",
    pointer,
    definition: "#dossier-index",
    href: artifactHref("web/dossiers/index.json"),
    breakdown: `#fig-${id}`,
    targets: dossierTargets({ recordList: null, provenanceHref: null, perSourceSlices: null }),
  });
  keyedRows.forEach((r, i) => {
    const p = `/dossiers/${i}`;
    if (typeof r.records === "number") {
      specs.push({ ...base(i, `r${i}-records`, r.records, `${p}/records`), definition: "#fig-def-records" });
    }
    if (typeof r.located?.by_point === "number") {
      specs.push({ ...base(i, `r${i}-located`, r.located.by_point, `${p}/located/by_point`), definition: "#fig-def-located" });
    }
    if (typeof r.located?.of === "number") {
      specs.push({ ...base(i, `r${i}-located-of`, r.located.of, `${p}/located/of`), definition: "#fig-def-located" });
    }
    if (typeof r.sources?.count === "number") {
      specs.push({ ...base(i, `r${i}-sources`, r.sources.count, `${p}/sources/count`), unit: "sources", definition: "#fig-def-sources" });
    }
    if (typeof r.open_questions === "number") {
      specs.push({ ...base(i, `r${i}-questions`, r.open_questions, `${p}/open_questions`), unit: "fields", definition: "#fig-def-open-questions" });
    }
    const dh = r.disagreements?.declared_here_located_elsewhere;
    if (typeof dh === "number" && dh > 0) {
      specs.push({ ...base(i, `r${i}-declared-elsewhere`, dh, `${p}/disagreements/declared_here_located_elsewhere`), definition: "#fig-def-disagreements" });
    }
    const lh = r.disagreements?.located_here_declared_elsewhere;
    if (typeof lh === "number" && lh > 0) {
      specs.push({ ...base(i, `r${i}-located-elsewhere`, lh, `${p}/disagreements/located_here_declared_elsewhere`), definition: "#fig-def-disagreements" });
    }
    if (typeof r.children?.count === "number" && r.children.count > 0) {
      specs.push({ ...base(i, `r${i}-children`, r.children.count, `${p}/children/count`), unit: "children", definition: "#fig-def-children" });
    }
    if (
      typeof r.children?.pages === "number" &&
      typeof r.children.count === "number" &&
      r.children.pages < r.children.count
    ) {
      specs.push({ ...base(i, `r${i}-children-pages`, r.children.pages, `${p}/children/pages`), unit: "children", definition: "#fig-def-children" });
    }
  });
  return specs;
}

/** Row → its figure-spec id stem (`r<i>` = the doc index). */
export function rowFigureId(row: DossierIndexRow, keyedRows: readonly DossierIndexRow[]): number {
  return keyedRows.findIndex((r) => r === row || r.jkey === row.jkey);
}
