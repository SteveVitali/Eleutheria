// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * P36.21 (SIG-UI-059, K13 UXR-09; ADR-155) — `sig.workspace-state-registry/1`,
 * the single parameter registry of `sig.workspace-state/2`. Every parameter a
 * workspace-state URL may name is registered here exactly once; the parser,
 * serialiser, surface-facet conformance harness (SIG-UI-060) and the stateful-
 * URL no-JS notices all read this table. A parameter that is not in this table
 * is REFUSED — parsed out, reported, never applied, never silently re-emitted
 * (SIG-UI-059's refusal rule).
 *
 * The parameter set is the spec's own table (§56.11 SIG-UI-059, K13 §2.5)
 * verbatim: the `common` scope rows every T2 surface may carry plus the
 * `map` and `graph` scope rows. Scope is REGISTRATION scoping, not filtering —
 * a scoped parameter on a surface that does not apply it is reported through
 * the unapplied-parameter notice (the surface never silently drops it), and
 * it round-trips through that surface's serialised links unchanged.
 *
 * Supersession (ADR-155 migration posture): `/2` supersedes
 * `sig.workspace-state/1`. `/1` URLs keep resolving — `sinceVersion: 1` marks
 * the parameters a `v=1` link may carry; everything else is a `/2` addition.
 * The v1 module (`web/src/lib/workspace-state.ts`) is left in place for the
 * v1 contract's own tests and any caller that needs the old semantics; the
 * surfaces and links minted from this row emit `v=2`.
 */

/** The state contract this registry serves. */
export const WORKSPACE_SCHEMA2 = "sig.workspace-state/2";

/** The wire version this registry mints. */
export const WORKSPACE_STATE2_VERSION = "2";

/** The registry contract's own schema id (self-describing). */
export const WORKSPACE_REGISTRY_SCHEMA = "sig.workspace-state-registry/1";

/**
 * The T2 surfaces workspace state applies to — the ADR-155 closed set. The
 * registry names them by their canonical surface ids; today's routes are in
 * `SURFACE_PATHS` (the graph explorer still answers at the v1 `/network/`
 * route until its GX-09a rename row — the registry is the single place that
 * indirection lives).
 */
export type WorkspaceSurface = "map" | "graph" | "search";

export const WORKSPACE_SURFACES: readonly WorkspaceSurface[] = [
  "map",
  "graph",
  "search",
];

/** The route each surface serves today (trailing-slash canonical form). */
export const SURFACE_PATHS: Record<WorkspaceSurface, string> = {
  map: "/map/",
  graph: "/network/",
  search: "/search/",
};

/**
 * The registered `view` vocabulary (SIG-UI-059: `list|map|graph|table|search`).
 * A view value RESOLVES TO a surface — the path still decides what renders
 * (SIG-UI-059: "the path decides what renders"); a URL whose `view` resolves
 * to a different surface is a parse issue, never a silent redirect.
 */
export type WorkspaceViewValue = "list" | "map" | "graph" | "table" | "search";

export const WORKSPACE_VIEW_VALUES: readonly WorkspaceViewValue[] = [
  "list",
  "map",
  "graph",
  "table",
  "search",
];

/** Which surface each registered view value resolves to. */
export const VIEW_SURFACE: Record<WorkspaceViewValue, WorkspaceSurface> = {
  list: "search",
  map: "map",
  graph: "graph",
  table: "search",
  search: "search",
};

/** The canonical `view=` value each surface emits in links it mints. */
export const SURFACE_VIEW: Record<WorkspaceSurface, WorkspaceViewValue> = {
  map: "map",
  graph: "graph",
  search: "list",
};

/** Registration scope — where the parameter is meaningful, per SIG-UI-059. */
export type ParamScope = "common" | "map" | "graph";

/** How a parameter's value is shaped — drives parsing and validation. */
export type ParamKind =
  | "flag-vocab" // single value from a closed vocabulary
  | "vocab-list" // repeated closed-vocabulary facet values
  | "free" // free text (q, sort, cursor, focus…)
  | "free-list" // repeated free-text facet values
  | "int" // non-negative integer (page)
  | "range-date" // YYYY[-MM]..YYYY[-MM]
  | "viewport" // at=<z>/<lat>/<lon>
  | "pair"; // <key>~<key> (graph path)

/** A registered parameter. */
export interface WorkspaceParamDef {
  /** Wire name — the `name=` the URL carries. */
  name: string;
  /** Registration scope (SIG-UI-059's `scope` column). */
  scope: ParamScope;
  /** Value shape. */
  kind: ParamKind;
  /** True when the URL may repeat the parameter (multi-select facet). */
  repeated: boolean;
  /** Closed vocabulary for `flag-vocab`/`vocab-list` kinds. */
  values?: readonly string[];
  /**
   * The parameter this parameter canonicalises INTO, when the registry's
   * canonicalisation rule names one (`bbox`/`frame` → `at`).
   */
  canonicalisesTo?: string;
  /**
   * The contract version that first admitted the parameter. `1` marks the
   * parameters a `v=1` link may carry — under a `v=1` input the parser keeps
   * the v1 value semantics exactly (SIG-UI-093's identical-resolution clause);
   * `2` marks /2's additions, which a `v=1` input reports but does not
   * interpret.
   */
  sinceVersion: 1 | 2;
  /**
   * The human phrase the unapplied-facet notice uses (SIG-UI-060): "this
   * address names {label}…". Grammatically a noun phrase.
   */
  label: string;
}

/**
 * Row factory — positional so the bundled table does not repeat the field
 * keys thirty times (the emitted objects are `WorkspaceParamDef`s verbatim;
 * this is only the source encoding of the table). Column order:
 * `name, scope, kind, repeated, sinceVersion, label, values?, canonicalisesTo?`.
 */
const L = (
  name: string,
  scope: ParamScope,
  kind: ParamKind,
  repeated: boolean,
  sinceVersion: 1 | 2,
  label: string,
  values?: readonly string[],
  canonicalisesTo?: string,
): WorkspaceParamDef => ({
  name,
  scope,
  kind,
  repeated,
  sinceVersion,
  label,
  ...(values ? { values } : {}),
  ...(canonicalisesTo ? { canonicalisesTo } : {}),
});

/**
 * The parameter table, in registry order — the canonical emission order too
 * (`v` and `view` are minted first by the serialiser; everything else follows
 * this table's order, so canonicalisation is byte-stable: parse → serialise
 * → parse yields the same URL).
 */
export const WORKSPACE_PARAMS: readonly WorkspaceParamDef[] = [
  // ------------------------------------------------------------- common
  L("release", "common", "free", false, 1, "a pinned release"),
  L(
    "view",
    "common",
    "flag-vocab",
    false,
    1,
    "a named view",
    WORKSPACE_VIEW_VALUES,
  ),
  L("q", "common", "free", false, 1, "a text query"),
  L(
    "type",
    "common",
    "vocab-list",
    true,
    2,
    "a result-type filter",
    [
      "place",
      "organization",
      "technology",
      "source",
      "document",
      "page",
      "record",
    ],
  ),
  L("kind", "common", "free-list", true, 1, "an entity-type filter"),
  L("jurisdiction", "common", "free-list", true, 1, "a jurisdiction filter"),
  L("frame", "common", "free", false, 2, "a map frame", undefined, "at"),
  L("bbox", "common", "free", false, 2, "a bounding box", undefined, "at"),
  L("technology", "common", "free-list", true, 1, "a technology filter"),
  L("vendor", "common", "free-list", true, 2, "a vendor filter"),
  L("operator", "common", "free-list", true, 2, "an operator filter"),
  L("source", "common", "free-list", true, 1, "a source filter"),
  L("collection", "common", "free-list", true, 1, "a licence-compartment filter"),
  L(
    "location",
    "common",
    "flag-vocab",
    false,
    1,
    "a location filter",
    ["public-point", "no-public-point"],
  ),
  L(
    "status",
    "common",
    "vocab-list",
    true,
    2,
    "an epistemic-status filter",
    ["corroborated", "single-source", "contested", "candidate"],
  ),
  L("seen", "common", "range-date", false, 2, "a seen range"),
  L("dated", "common", "range-date", false, 2, "a publication-date range"),
  L(
    "currency",
    "common",
    "flag-vocab",
    false,
    2,
    "a currency filter",
    ["current", "aging", "stale", "historical", "undated"],
  ),
  L("focus", "common", "free", false, 1, "a selected record"),
  L("page", "common", "int", false, 1, "a result page"),
  L("sort", "common", "free", false, 2, "a sort key"),
  L("dir", "common", "flag-vocab", false, 2, "a sort direction", ["asc", "desc"]),
  L("cursor", "common", "free", false, 2, "a pagination cursor"),
  L("within", "common", "free", false, 2, "a scope restriction"),
  // ---------------------------------------------------------------- map
  L("at", "map", "viewport", false, 2, "a map viewport"),
  L("layers", "map", "free-list", true, 2, "a layer selection"),
  L("basemap", "map", "flag-vocab", false, 2, "a basemap choice", ["0", "1"]),
  // -------------------------------------------------------------- graph
  L("overview", "graph", "free", false, 2, "an overview anchor"),
  L("hops", "graph", "flag-vocab", false, 2, "a hop depth", ["1", "2"]),
  L("edge", "graph", "free-list", true, 2, "an edge-kind facet"),
  L("expand", "graph", "free-list", true, 2, "an expanded node"),
  L("path", "graph", "pair", false, 2, "a node pair"),
];

/** name → definition lookup; `undefined` means UNREGISTERED (refuse loud). */
export const PARAM_BY_NAME: ReadonlyMap<string, WorkspaceParamDef> = new Map(
  WORKSPACE_PARAMS.map((p) => [p.name, p]),
);

/** The v1 parameter set — the names `v=1` links may carry (SIG-UI-093). */
export const V1_PARAM_NAMES: ReadonlySet<string> = new Set(
  WORKSPACE_PARAMS.filter((p) => p.sinceVersion === 1).map((p) => p.name),
);

export function isWorkspaceParam(name: string): boolean {
  return PARAM_BY_NAME.has(name);
}
