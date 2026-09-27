// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * `sig.workspace-state/1` — the versioned URL-state contract shared by the three
 * public investigation islands (`/search/`, `/map/`, `/network/`) and the links
 * between them (P32.15, SIG-FIND-004, ADR-134; S4 research §7 "Canonical query
 * state").
 *
 * Canonical parameters, in emitted order:
 *
 *   v            the contract version — always "1" today; unknown versions fail
 *                VISIBLY (an `issues` note), never silently reinterpret
 *   release      the pinned publication id (`p-<sha256>`); absent = the build's
 *                latest activated release
 *   collection   REPEATED — licence-compartment selection; absent = all;
 *                `collection=` (present with no values) = NONE selected — an
 *                explicit empty selection is a different state, not a default
 *   q            free-text query (the same `q` the released-corpus search uses)
 *   kind         REPEATED — record-type facet
 *   jurisdiction REPEATED — place facet ("unknown jurisdiction" is selectable)
 *   technology   REPEATED — technology facet
 *   source       REPEATED — source-collection facet
 *   location     `any` | `public-point` | `no-public-point` (the P32.14 index's
 *                LOCATION_VALUES — the same names, never a second vocabulary)
 *   focus        the selected record — a `sig.published-record/1` record_key
 *                `<compartment>:<entity_type>:<entity_id>`, or an island node /
 *                asset id where the fixture data uses those
 *   view         list | map | network — names the target surface; the path
 *                carries the same information and a mismatch fails visibly
 *   page         1-based result page (search/filter changes reset it to 1)
 *
 * NOT carried here (S4 §8): the map viewport (`z`/`lat`/`lon`) is transient in
 * memory — an explicit share-view encoding is a separate decision; no
 * geolocation, localStorage research history, accounts or identifying analytics.
 *
 * This module is pure logic — no DOM, no React — so the contract is unit-testable
 * (`web/tests/unit/workspace-state.test.ts`) and shared verbatim by every island.
 */

export const WORKSPACE_STATE_VERSION = "1";
export const WORKSPACE_SCHEMA = "sig.workspace-state/1";

export const WORKSPACE_VIEWS = ["list", "map", "network"] as const;
export type WorkspaceView = (typeof WORKSPACE_VIEWS)[number];

/** The one canonical path each view name resolves to (S4-D3). */
export const WORKSPACE_VIEW_PATHS: Record<WorkspaceView, string> = {
  list: "/search/",
  map: "/map/",
  network: "/network/",
};

/** The P32.14 released-index location-filter vocabulary (shared, not forked). */
export const LOCATION_FILTERS = ["any", "public-point", "no-public-point"] as const;
export type LocationFilter = (typeof LOCATION_FILTERS)[number];

/** Facet parameters that may repeat (the canonical "repeated permitted facets"). */
export const REPEATED_FACETS = [
  "collection",
  "kind",
  "jurisdiction",
  "technology",
  "source",
] as const;
export type WorkspaceFacet = (typeof REPEATED_FACETS)[number];

/** Result-page size the workspace links adopt — the P32.14 released-search bound. */
export const WORKSPACE_PAGE_SIZE = 50;

export interface WorkspaceState {
  /** Pinned publication id, or null for the surface's latest activated release. */
  release: string | null;
  /** Selected licence compartments; see `collectionSpecified` for the absent/empty split. */
  collection: string[];
  /**
   * Whether `collection` was explicitly named in the state: `false` (absent
   * param) means ALL compartments; `true` with an empty `collection` (a bare
   * `collection=` param) means NONE — "0 of N compartments" is a real,
   * linkable state, not a silent default.
   */
  collectionSpecified: boolean;
  q: string;
  kind: string[];
  jurisdiction: string[];
  technology: string[];
  source: string[];
  location: LocationFilter;
  /** The selected record (record_key or island node/asset id), or null. */
  focus: string | null;
  view: WorkspaceView;
  /** 1-based result page; resets to 1 on any query/filter change. */
  page: number;
}

export const DEFAULT_WORKSPACE_STATE: WorkspaceState = {
  release: null,
  collection: [],
  collectionSpecified: false,
  q: "",
  kind: [],
  jurisdiction: [],
  technology: [],
  source: [],
  location: "any",
  focus: null,
  view: "list",
  page: 1,
};

/** Fields a parse may fall back to when the URL omits them (build-time defaults). */
export interface WorkspaceDefaults {
  release?: string | null;
  view?: WorkspaceView;
}

export interface WorkspaceParse {
  state: WorkspaceState;
  /**
   * Human-visible notes for inputs that could not be honoured — "unknown
   * combinations fail visibly" (DESIGN §"Workspace state"), never silently dropped.
   */
  issues: string[];
}

function values(params: URLSearchParams, facet: WorkspaceFacet): string[] {
  return params.getAll(facet).filter((v) => v !== "");
}

/**
 * Tolerant-with-receipts parse: every parameter the contract names is honoured,
 * every unrecognised VALUE is defaulted AND reported in `issues`. Unknown extra
 * parameters are ignored (other surfaces own their own query strings) — the
 * contract's "fail visibly" applies to the fields it names.
 */
export function parseWorkspaceState(
  input: string | URLSearchParams,
  defaults: WorkspaceDefaults = {},
): WorkspaceParse {
  const params = typeof input === "string" ? new URLSearchParams(input) : input;
  const issues: string[] = [];

  const v = params.get("v");
  if (v !== null && v !== WORKSPACE_STATE_VERSION) {
    issues.push(
      `State version "${v}" is not supported (this surface reads v${WORKSPACE_STATE_VERSION}); unrecognised parts may be defaulted.`,
    );
  }

  let view: WorkspaceView = defaults.view ?? DEFAULT_WORKSPACE_STATE.view;
  const rawView = params.get("view");
  if (rawView !== null) {
    if ((WORKSPACE_VIEWS as readonly string[]).includes(rawView)) {
      view = rawView as WorkspaceView;
    } else {
      issues.push(`Unknown view "${rawView}"; showing the "${view}" view.`);
    }
  }

  let location: LocationFilter = DEFAULT_WORKSPACE_STATE.location;
  const rawLocation = params.get("location");
  if (rawLocation !== null) {
    if ((LOCATION_FILTERS as readonly string[]).includes(rawLocation)) {
      location = rawLocation as LocationFilter;
    } else {
      issues.push(`Unknown location filter "${rawLocation}"; showing all locations.`);
    }
  }

  let page = DEFAULT_WORKSPACE_STATE.page;
  const rawPage = params.get("page");
  if (rawPage !== null) {
    const parsed = Number.parseInt(rawPage, 10);
    if (Number.isFinite(parsed) && parsed >= 1 && String(parsed) === rawPage) {
      page = parsed;
    } else {
      issues.push(`Unusable page "${rawPage}"; showing page 1.`);
    }
  }

  return {
    state: {
      release: params.get("release") ?? defaults.release ?? null,
      collection: values(params, "collection"),
      collectionSpecified: params.has("collection"),
      q: params.get("q") ?? "",
      kind: values(params, "kind"),
      jurisdiction: values(params, "jurisdiction"),
      technology: values(params, "technology"),
      source: values(params, "source"),
      location,
      focus: params.get("focus"),
      view,
      page,
    },
    issues,
  };
}

/**
 * Canonical serialisation: `v` and `view` are always emitted (the link is
 * explicitly versioned and names its surface); every other field is omitted at
 * its default so links stay short and stable.
 */
export function serializeWorkspaceState(state: WorkspaceState): URLSearchParams {
  const params = new URLSearchParams();
  params.set("v", WORKSPACE_STATE_VERSION);
  if (state.release) params.set("release", state.release);
  for (const c of state.collection) params.append("collection", c);
  // An explicitly-empty compartment selection ("none") round-trips as a bare
  // `collection=` param; an absent param remains the all-compartments default.
  if (state.collectionSpecified && state.collection.length === 0) {
    params.append("collection", "");
  }
  if (state.q !== "") params.set("q", state.q);
  for (const k of state.kind) params.append("kind", k);
  for (const j of state.jurisdiction) params.append("jurisdiction", j);
  for (const t of state.technology) params.append("technology", t);
  for (const s of state.source) params.append("source", s);
  if (state.location !== "any") params.set("location", state.location);
  if (state.focus) params.set("focus", state.focus);
  params.set("view", state.view);
  if (state.page !== 1) params.set("page", String(state.page));
  return params;
}

/** `path?…` with the canonical parameter order. */
export function workspaceHref(path: string, state: WorkspaceState): string {
  return `${path}?${serializeWorkspaceState(state).toString()}`;
}

/** The link to the same investigation state on another view (S4 §7). */
export function viewHref(state: WorkspaceState, view: WorkspaceView): string {
  return workspaceHref(WORKSPACE_VIEW_PATHS[view], { ...state, view });
}

/** The view a canonical workspace path renders, or null for non-view paths. */
export function pageView(pathname: string): WorkspaceView | null {
  for (const v of WORKSPACE_VIEWS) {
    if (WORKSPACE_VIEW_PATHS[v] === pathname) return v;
  }
  return null;
}

/** Select (or clear, `null`) the focused record; pagination resets. */
export function withFocus(state: WorkspaceState, focus: string | null): WorkspaceState {
  return { ...state, focus, page: 1 };
}

/**
 * Apply a query/filter change (q, facets, location, collection, release):
 * pagination ALWAYS resets; focus retention is the caller's decision —
 * `focusInScope` reports whether the selected record survives.
 */
export function withSearchPatch(
  state: WorkspaceState,
  patch: Partial<WorkspaceState>,
): WorkspaceState {
  return { ...state, ...patch, page: 1 };
}

/**
 * The "retain focus only if the selected record remains in scope" rule (S4 §7):
 * returns the possibly-cleared state and whether the selection was dropped, so
 * the caller can announce "selection cleared" rather than silently losing it.
 */
export function clearFocusOutOfScope(
  state: WorkspaceState,
  inScope: (focus: string) => boolean,
): { state: WorkspaceState; cleared: boolean } {
  if (state.focus !== null && !inScope(state.focus)) {
    return { state: { ...state, focus: null }, cleared: true };
  }
  return { state, cleared: false };
}

/** The three legs of a `sig.published-record/1` record_key, or null. */
export function splitRecordKey(
  focus: string,
): { compartment: string; entityType: string; entityId: string } | null {
  const parts = focus.split(":");
  if (parts.length !== 3 || parts.some((p) => p === "")) return null;
  const [compartment, entityType, entityId] = parts;
  return { compartment: compartment!, entityType: entityType!, entityId: entityId! };
}

/**
 * The released-record routes a `focus=<record_key>` resolves to under a pinned
 * publication (`/r/<pub>/c/<comp>/entity/<type>/<id>/` + `.json`, ADR-132). The
 * island deep-link thus needs no id→compartment index: the key is self-describing.
 */
export function recordRoutes(
  publicationId: string,
  recordKey: string,
): { pageHref: string; jsonHref: string; compartmentHref: string } | null {
  const parts = splitRecordKey(recordKey);
  if (!parts) return null;
  const base = `/r/${publicationId}/c/${parts.compartment}/entity/${parts.entityType}/${parts.entityId}`;
  return {
    pageHref: `${base}/`,
    jsonHref: `${base}.json`,
    compartmentHref: `/r/${publicationId}/c/${parts.compartment}/`,
  };
}

/** The released evidence anchor page for one artifact id (`/r/<pub>/c/<comp>/evidence/<id>/`). */
export function evidenceAnchorHref(
  publicationId: string,
  compartment: string,
  artifactId: string,
): string {
  return `/r/${publicationId}/c/${compartment}/evidence/${artifactId}/`;
}
