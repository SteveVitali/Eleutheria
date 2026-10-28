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

const L = (name: string, partial: Omit<WorkspaceParamDef, "name">) => ({
  name,
  ...partial,
});

/**
 * The parameter table, in registry order — the canonical emission order too
 * (`v` and `view` are minted first by the serialiser; everything else follows
 * this table's order, so canonicalisation is byte-stable: parse → serialise
 * → parse yields the same URL).
 */
export const WORKSPACE_PARAMS: readonly WorkspaceParamDef[] = [
  // ------------------------------------------------------------- common
  L("release", {
    scope: "common",
    kind: "free",
    repeated: false,
    sinceVersion: 1,
    label: "a pinned release",
  }),
  L("view", {
    scope: "common",
    kind: "flag-vocab",
    repeated: false,
    values: WORKSPACE_VIEW_VALUES,
    sinceVersion: 1,
    label: "a named view",
  }),
  L("q", {
    scope: "common",
    kind: "free",
    repeated: false,
    sinceVersion: 1,
    label: "a text query",
  }),
  L("type", {
    scope: "common",
    kind: "vocab-list",
    repeated: true,
    values: [
      "place",
      "organization",
      "technology",
      "source",
      "document",
      "page",
      "record",
    ],
    sinceVersion: 2,
    label: "a result-type filter",
  }),
  L("kind", {
    scope: "common",
    kind: "free-list",
    repeated: true,
    sinceVersion: 1,
    label: "an entity-type filter",
  }),
  L("jurisdiction", {
    scope: "common",
    kind: "free-list",
    repeated: true,
    sinceVersion: 1,
    label: "a jurisdiction filter",
  }),
  L("frame", {
    scope: "common",
    kind: "free",
    repeated: false,
    canonicalisesTo: "at",
    sinceVersion: 2,
    label: "a map frame",
  }),
  L("bbox", {
    scope: "common",
    kind: "free",
    repeated: false,
    canonicalisesTo: "at",
    sinceVersion: 2,
    label: "a bounding box",
  }),
  L("technology", {
    scope: "common",
    kind: "free-list",
    repeated: true,
    sinceVersion: 1,
    label: "a technology filter",
  }),
  L("vendor", {
    scope: "common",
    kind: "free-list",
    repeated: true,
    sinceVersion: 2,
    label: "a vendor filter",
  }),
  L("operator", {
    scope: "common",
    kind: "free-list",
    repeated: true,
    sinceVersion: 2,
    label: "an operator filter",
  }),
  L("source", {
    scope: "common",
    kind: "free-list",
    repeated: true,
    sinceVersion: 1,
    label: "a source filter",
  }),
  L("collection", {
    scope: "common",
    kind: "free-list",
    repeated: true,
    sinceVersion: 1,
    label: "a licence-compartment filter",
  }),
  L("location", {
    scope: "common",
    kind: "flag-vocab",
    repeated: false,
    values: ["public-point", "no-public-point"],
    sinceVersion: 1,
    label: "a location filter",
  }),
  L("status", {
    scope: "common",
    kind: "vocab-list",
    repeated: true,
    values: ["corroborated", "single-source", "contested", "candidate"],
    sinceVersion: 2,
    label: "an epistemic-status filter",
  }),
  L("seen", {
    scope: "common",
    kind: "range-date",
    repeated: false,
    sinceVersion: 2,
    label: "a seen range",
  }),
  L("dated", {
    scope: "common",
    kind: "range-date",
    repeated: false,
    sinceVersion: 2,
    label: "a publication-date range",
  }),
  L("currency", {
    scope: "common",
    kind: "flag-vocab",
    repeated: false,
    values: ["current", "aging", "stale", "historical", "undated"],
    sinceVersion: 2,
    label: "a currency filter",
  }),
  L("focus", {
    scope: "common",
    kind: "free",
    repeated: false,
    sinceVersion: 1,
    label: "a selected record",
  }),
  L("page", {
    scope: "common",
    kind: "int",
    repeated: false,
    sinceVersion: 1,
    label: "a result page",
  }),
  L("sort", {
    scope: "common",
    kind: "free",
    repeated: false,
    sinceVersion: 2,
    label: "a sort key",
  }),
  L("dir", {
    scope: "common",
    kind: "flag-vocab",
    repeated: false,
    values: ["asc", "desc"],
    sinceVersion: 2,
    label: "a sort direction",
  }),
  L("cursor", {
    scope: "common",
    kind: "free",
    repeated: false,
    sinceVersion: 2,
    label: "a pagination cursor",
  }),
  L("within", {
    scope: "common",
    kind: "free",
    repeated: false,
    sinceVersion: 2,
    label: "a scope restriction",
  }),
  // ---------------------------------------------------------------- map
  L("at", {
    scope: "map",
    kind: "viewport",
    repeated: false,
    sinceVersion: 2,
    label: "a map viewport",
  }),
  L("layers", {
    scope: "map",
    kind: "free-list",
    repeated: true,
    sinceVersion: 2,
    label: "a layer selection",
  }),
  L("basemap", {
    scope: "map",
    kind: "flag-vocab",
    repeated: false,
    values: ["0", "1"],
    sinceVersion: 2,
    label: "a basemap choice",
  }),
  // -------------------------------------------------------------- graph
  L("overview", {
    scope: "graph",
    kind: "free",
    repeated: false,
    sinceVersion: 2,
    label: "an overview anchor",
  }),
  L("hops", {
    scope: "graph",
    kind: "flag-vocab",
    repeated: false,
    values: ["1", "2"],
    sinceVersion: 2,
    label: "a hop depth",
  }),
  L("edge", {
    scope: "graph",
    kind: "free-list",
    repeated: true,
    sinceVersion: 2,
    label: "an edge-kind facet",
  }),
  L("expand", {
    scope: "graph",
    kind: "free-list",
    repeated: true,
    sinceVersion: 2,
    label: "an expanded node",
  }),
  L("path", {
    scope: "graph",
    kind: "pair",
    repeated: false,
    sinceVersion: 2,
    label: "a node pair",
  }),
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
