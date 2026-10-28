// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * P36.21 (SIG-UI-059/093, K13 UXR-09; ADR-155) — `sig.workspace-state/2`
 * parse → validate → serialise, the pure contract half. Design (the ticket,
 * K0 §4.5, K13 §2.5/§C-11):
 *
 * - ONE registry drives everything — `workspace-state/registry.ts` is the
 *   only place a parameter is named; this module never hardcodes a name the
 *   table does not carry (the table's `sinceVersion` is what a `v=1` link may
 *   exercise).
 * - Additive by design: `v=1` URLs resolve identically — the same v1 fields
 *   land in the same state slots with the same v1 semantics (record-type
 *   `kind`, view name `network`, location word `any`); every parameter
 *   `v=1` cannot carry is reported into `present` so the surface's
 *   unapplied-facet notice can name it, but its VALUE is left unparsed, which
 *   is exactly what the v1 contract did with extras.
 * - Canonicalisation lands here, not in the islands: `bbox=` folds into
 *   `at=` and is never re-emitted; `kind=site` becomes `type=record`; legacy
   * `US-OK`-shaped jurisdiction codes become `iso3166-2:<code>`; `view=network`
 *   becomes `graph`; `location=any` becomes the absent default. Each
 *   canonicalisation appends a plain-language receipt to `notes`, so every
 *   quiet rewrite is VISIBLE (WS-03).
 * - Tolerant-with-receipts, never silent: an unregistered parameter is
 *   refused — reported in `unregistered`, named in `issues`, and never
 *   re-emitted; a mis-valued registered parameter is reported in `issues` and
 *   falls back to its default; defaults are omitted on serialise, so the
 *   round-trip is byte-stable (`parse → serialise → parse` is the identity
 *   on canonical URLs).
 * - No history writes: this module is pure — the `islands/workspace.ts`
 *   adapter owns `history.pushState`/`popstate`.
 */

import type { LocationFilter } from "../workspace-state";
import {
  PARAM_BY_NAME,
  SURFACE_PATHS,
  SURFACE_VIEW,
  VIEW_SURFACE,
  V1_PARAM_NAMES,
  WORKSPACE_STATE2_VERSION,
  type WorkspaceParamDef,
  type WorkspaceSurface,
  type WorkspaceViewValue,
} from "./registry";

// ------------------------------------------------------------------ types

/** The map viewport `at=<z>/<lat>/<lon>` decodes to. */
export interface Viewport {
  z: number;
  lat: number;
  lon: number;
}

export type EpistemicStatus =
  | "corroborated"
  | "single-source"
  | "contested"
  | "candidate";

export type Currency = "current" | "aging" | "stale" | "historical" | "undated";

export type ResultType =
  | "place"
  | "organization"
  | "technology"
  | "source"
  | "document"
  | "page"
  | "record";

/**
 * The parsed workspace state — a strict superset of the v1 record. `view`
 * carries the REGISTERED vocabulary (`list|map|graph|table|search`); the
 * islands' internal view ids translate at the adapter boundary
 * (`toIslandView` / `islandToViewValue`), so the wire truth never leaks a
 * runtime name.
 */
export interface WorkspaceState2 {
  release: string | null;
  /** The view the URL targets (registered value; the path still decides). */
  view: WorkspaceViewValue;
  q: string;
  type: ResultType[];
  /** Entity-type facet under v2; the v1 record-type list under `v=1` input. */
  kind: string[];
  /** Canonical jkeys — legacy `XX-NN` input is normalised in, with a note. */
  jurisdiction: string[];
  /** Framing-only jkey; canonicalises to `at` once a bounds table exists. */
  frame: string | null;
  technology: string[];
  vendor: string[];
  operator: string[];
  source: string[];
  collection: string[];
  /** True when `collection` appeared with no values (the empty set). */
  collectionSpecified: boolean;
  /** `null` = no filter (v2 canonical); v1 input may carry the word `any`. */
  location: LocationFilter | null;
  status: EpistemicStatus[];
  /** `YYYY[-MM]..YYYY[-MM]`, validated shape, unparsed endpoints. */
  seen: string | null;
  dated: string | null;
  currency: Currency | null;
  focus: string | null;
  /** 1-based result page (v1 semantics); resets to 1 on facet/query change. */
  page: number;
  sort: string | null;
  dir: "asc" | "desc" | null;
  cursor: string | null;
  within: string | null;
  at: Viewport | null;
  layers: string[];
  basemap: "0" | "1" | null;
  overview: string | null;
  hops: 1 | 2 | null;
  edge: string[];
  expand: string[];
  /** `<key>~<key>` — kept as the wire pair. */
  path: string | null;
}

export const DEFAULT_WORKSPACE_STATE2: WorkspaceState2 = {
  release: null,
  view: "list",
  q: "",
  type: [],
  kind: [],
  jurisdiction: [],
  frame: null,
  technology: [],
  vendor: [],
  operator: [],
  source: [],
  collection: [],
  collectionSpecified: false,
  location: null,
  status: [],
  seen: null,
  dated: null,
  currency: null,
  focus: null,
  page: 1,
  sort: null,
  dir: null,
  cursor: null,
  within: null,
  at: null,
  layers: [],
  basemap: null,
  overview: null,
  hops: null,
  edge: [],
  expand: [],
  path: null,
};

export interface WorkspaceParse2 {
  state: WorkspaceState2;
  /** Failures — bad values and refused (unregistered) parameter names. */
  issues: string[];
  /**
   * Normalisation receipts — the canonicalisations the parser performed
   * (legacy jurisdiction codes, `bbox` → `at`, `kind=site` → `type=record`,
   * `view=network` → `graph`). Every quiet rewrite is named here so a
   * surface can show it; nothing is silently rewritten.
   */
  notes: string[];
  /**
   * Registered parameter names the address carried (the unapplied-facet
   * notice reads this). Order of first appearance, deduplicated.
   */
  present: string[];
  /**
   * Parameter names the registry refuses — reported, never applied, never
   * re-emitted.
   */
  unregistered: string[];
}

// ----------------------------------------------------- island vocabulary

/**
 * The islands' internal view ids — the runtime names the React surfaces and
 * the static view switch key on (`data-testid="view-link-network"` etc.).
 * Internal names map 1:1 onto surfaces; the WIRE emits the registered `view`
 * values (`network` → `graph`), and parse maps registered values back.
 */
export type IslandView = "list" | "map" | "network";

export const ISLAND_VIEWS: readonly IslandView[] = ["list", "map", "network"];

export const ISLAND_SURFACE: Record<IslandView, WorkspaceSurface> = {
  list: "search",
  map: "map",
  network: "graph",
};

export function viewValueToIsland(view: WorkspaceViewValue): IslandView {
  const surface = VIEW_SURFACE[view];
  return surface === "map" ? "map" : surface === "graph" ? "network" : "list";
}

export function islandToViewValue(view: IslandView): WorkspaceViewValue {
  return SURFACE_VIEW[ISLAND_SURFACE[view]];
}

/**
 * The state shape the islands carry — every parsed field (so an unapplied
 * parameter still ROUND-TRIPS through an update or a view switch rather than
 * being silently dropped), with `view` in the internal vocabulary the
 * islands' switch keys on.
 */
export type IslandWorkspaceState = Omit<WorkspaceState2, "view"> & {
  view: IslandView;
};

export function toIslandState(
  state: WorkspaceState2,
  view: IslandView,
): IslandWorkspaceState {
  return { ...state, view };
}

export function toWireState(state: IslandWorkspaceState): WorkspaceState2 {
  return { ...state, view: islandToViewValue(state.view) };
}

// ------------------------------------------------------------ parsing

const INT_RE = /^\d+$/;
const RANGE_DATE_RE =
  /^\d{4}(?:-(?:0[1-9]|1[0-2]))?\.\.\d{4}(?:-(?:0[1-9]|1[0-2]))?$/;
/** The legacy jurisdiction shapes the registry canonicalises (`US-OK` → `iso3166-2:US-OK`). */
const LEGACY_JKEY_RE = /^[A-Z]{2}-[A-Z0-9]{1,3}$/;
/** The v1 view name for the graph surface. */
const LEGACY_VIEW_NETWORK = "network";
/** The v1 location default word (v2 canonical: absent). */
const LEGACY_LOCATION_ANY = "any";

/**
 * The deterministic `at=` precision rule the registry publishes (§19.4's
 * view-layer rounding — the zoom's decimal count, never finer than a public
 * tier needs): z≤5 → 1 dp (~11 km), z≤10 → 2 dp (~1.1 km), z≤14 → 3 dp
 * (~110 m), beyond → 4 dp (~11 m). Recorded in ADR-225.
 */
export function viewportDecimals(z: number): number {
  return z <= 5 ? 1 : z <= 10 ? 2 : z <= 14 ? 3 : 4;
}

function roundTo(value: number, decimals: number): number {
  const f = 10 ** decimals;
  return Math.round(value * f) / f;
}

/** Parse and round `z/lat/lon` — returns the viewport or an issue string. */
function parseViewport(raw: string): Viewport | string {
  const parts = raw.split("/");
  if (parts.length !== 3) {
    return `at must be <z>/<lat>/<lon>, got "${raw}"`;
  }
  const [zRaw, latRaw, lonRaw] = parts;
  if (!INT_RE.test(zRaw)) {
    return `at zoom must be an integer, got "${zRaw}"`;
  }
  const z = Number(zRaw);
  const lat = Number(latRaw);
  const lon = Number(lonRaw);
  if (Number.isNaN(lat) || Number.isNaN(lon)) {
    return `at coordinates must be numbers, got "${raw}"`;
  }
  if (z < 0 || z > 22) {
    return `at zoom must sit inside 0..22, got "${zRaw}"`;
  }
  if (lat < -90 || lat > 90 || lon < -180 || lon > 180) {
    return `at coordinates sit outside the valid ranges, got "${raw}"`;
  }
  const d = viewportDecimals(z);
  return { z, lat: roundTo(lat, d), lon: roundTo(lon, d) };
}

/**
 * The `w,s,e,n` → `at=` fold. Deterministic: centre of the box, zoom from
 * the longer span (`floor(log2(360/span))` clamped to 0..14 — the tile
 * pyramid's public range), coordinates rounded to the zoom's precision. A
 * degenerate or inverted box is an issue, never a guess.
 */
export function bboxToViewport(raw: string): Viewport | string {
  const parts = raw.split(",").map((p) => Number(p));
  if (parts.length !== 4 || parts.some((n) => Number.isNaN(n))) {
    return `bbox must be w,s,e,n numbers, got "${raw}"`;
  }
  const [w, s, e, n] = parts;
  if (e <= w || n <= s) {
    return `bbox must name a non-empty box (w<s? got "${raw}")`;
  }
  if (s < -90 || n > 90 || w < -180 || e > 180) {
    return `bbox coordinates sit outside the valid ranges, got "${raw}"`;
  }
  const span = Math.max(e - w, n - s);
  const z = Math.max(0, Math.min(14, Math.floor(Math.log2(360 / span))));
  const d = viewportDecimals(z);
  return {
    z,
    lat: roundTo((s + n) / 2, d),
    lon: roundTo((w + e) / 2, d),
  };
}

function formatViewport(v: Viewport): string {
  return `${v.z}/${v.lat}/${v.lon}`;
}

/**
 * The ordered `name=value` pairs of the input — `URLSearchParams` iteration
 * preserves address order and decodes exactly as the v1 parser did; a bare
 * `collection` token arrives as `("collection","")`, which the v1 rule reads
 * as "specified, empty set" (identical resolution).
 */
function entriesOf(input: string): [string, string][] {
  const params = new URLSearchParams(input);
  return [...params.entries()];
}

function badValue(issues: string[], name: string, why: string) {
  issues.push(`The address has an unusable ${name} (${why}); it is ignored.`);
}

/**
 * Parse `?v=…` search input into `sig.workspace-state/2` state. `defaults`
 * seeds every field (the islands pass their surface's release + view), then
 * the input overwrites registered fields. See the module header for the
 * version and refusal rules; the returned `present`/`unregistered` feed the
 * surface-facet conformance notice (`workspace-state/conformance.ts`).
 */
export function parseWorkspaceState2(
  input: string,
  defaults: Partial<WorkspaceState2> = {},
): WorkspaceParse2 {
  const state: WorkspaceState2 = { ...DEFAULT_WORKSPACE_STATE2, ...defaults };
  const issues: string[] = [];
  const notes: string[] = [];
  const present: string[] = [];
  const unregistered: string[] = [];
  const entries = entriesOf(input);

  // Version first — it scopes every rule below. Absent is /2 (a /2-era link);
  // "1" switches the parser to the v1 value semantics (identical resolution);
  // anything else is an issue but still parses under /2 (tolerant-with-
  // receipts, never a closed door).
  const vValues = entries
    .filter(([n]) => n === "v")
    .map(([, v]) => v);
  const v = vValues.length > 0 ? vValues[vValues.length - 1] : null;
  let legacyV1 = false;
  if (v === "1") {
    legacyV1 = true;
  } else if (v !== null && v !== WORKSPACE_STATE2_VERSION) {
    issues.push(
      `The address names an unrecognised workspace-state version "${v}" — it is parsed as v=${WORKSPACE_STATE2_VERSION}.`,
    );
  }

  const single = new Map<string, string>();
  const lists = new Map<string, string[]>();
  for (const [name, value] of entries) {
    if (name === "v") continue;
    const def = PARAM_BY_NAME.get(name);
    if (!def) {
      if (!unregistered.includes(name)) {
        unregistered.push(name);
        issues.push(
          `The address names the parameter "${name}", which is not in the sig.workspace-state/2 registry — it is not applied.`,
        );
      }
      continue;
    }
    if (!present.includes(name)) present.push(name);
    // A `v=1` link only exercises the v1 parameter set — /2 additions are
    // REPORTED (present → the surface's notice names them) but their values
    // stay unparsed, which is what the v1 contract did with extras.
    if (legacyV1 && !V1_PARAM_NAMES.has(name)) continue;
    if (def.repeated) {
      // v1 value semantics: an empty facet value contributes nothing
      // (`collection=` still marks the selection specified, below).
      if (value === "") continue;
      const acc = lists.get(name) ?? [];
      acc.push(value);
      lists.set(name, acc);
    } else if (!single.has(name)) {
      single.set(name, value); // first-one-wins, matching v1's params.get
    }
  }
  // `collection` bare OR `collection=` both mark the selection specified —
  // the empty set, never "all compartments" (v1 semantics, verbatim).
  if (entries.some(([n, v]) => n === "collection" && v === "")) {
    if (!present.includes("collection")) present.push("collection");
    state.collectionSpecified = true;
  }

  const vocabCheck = (
    def: WorkspaceParamDef,
    raw: string,
  ): string | null => {
    if (def.values && !def.values.includes(raw)) {
      badValue(issues, def.name, `unknown value "${raw}"`);
      return null;
    }
    return raw;
  };

  // --- common
  if (single.has("release")) state.release = single.get("release")!;
  if (single.has("view")) {
    const raw = single.get("view")!;
    if (legacyV1) {
      // The v1 vocabulary is {list,map,network} — identical resolution:
      // `network` is the v1 name for the graph surface; anything else is the
      // same "unknown view" issue v1 raised.
      if (raw === "list" || raw === "map" || raw === LEGACY_VIEW_NETWORK) {
        state.view = raw === LEGACY_VIEW_NETWORK ? "graph" : (raw as WorkspaceViewValue);
      } else {
        issues.push(`Unknown view "${raw}"; showing the "${state.view}" view.`);
      }
    } else if (raw === LEGACY_VIEW_NETWORK) {
      state.view = "graph";
      notes.push(
        `The address names the v1 view "network"; its canonical name is "graph".`,
      );
    } else if (vocabCheck(PARAM_BY_NAME.get("view")!, raw)) {
      state.view = raw as WorkspaceViewValue;
    }
  }
  if (single.has("q")) state.q = single.get("q")!;
  if (lists.has("type")) {
    state.type = lists
      .get("type")!.filter((v) => vocabCheck(PARAM_BY_NAME.get("type")!, v))
      .map((v) => v as ResultType);
  }
  if (lists.has("kind")) {
    const kinds = lists.get("kind")!;
    if (legacyV1) {
      state.kind = kinds;
    } else {
      // C-11: K1's draft `kind=site` links normalise to `type=record`.
      state.kind = [];
      for (const k of kinds) {
        if (k === "site") {
          if (!state.type.includes("record")) {
            // Never mutate the (shared) defaults arrays — assign a fresh one.
            state.type = [...state.type, "record"];
          }
          notes.push(
            `The facet kind=site is a legacy form; it resolves as type=record.`,
          );
        } else {
          state.kind.push(k);
        }
      }
    }
  }
  if (lists.has("jurisdiction")) {
    const jk = lists.get("jurisdiction")!;
    if (legacyV1) {
      state.jurisdiction = jk;
    } else {
      state.jurisdiction = jk.map((j) => {
        if (LEGACY_JKEY_RE.test(j)) {
          const canonical = `iso3166-2:${j}`;
          notes.push(
            `The jurisdiction code "${j}" is a legacy form; it resolves as "${canonical}".`,
          );
          return canonical;
        }
        return j;
      });
    }
  }
  if (single.has("frame")) state.frame = single.get("frame")!;
  if (lists.has("technology")) state.technology = lists.get("technology")!;
  if (lists.has("vendor")) state.vendor = lists.get("vendor")!;
  if (lists.has("operator")) state.operator = lists.get("operator")!;
  if (lists.has("source")) state.source = lists.get("source")!;
  if (lists.has("collection")) {
    state.collection = lists.get("collection")!;
    state.collectionSpecified = true;
  }
  if (single.has("location")) {
    const raw = single.get("location")!;
    if (raw === LEGACY_LOCATION_ANY) {
      if (legacyV1) {
        state.location = "any";
      } else {
        state.location = null;
        notes.push(
          `The location value "any" is the v1 default word; the canonical form is the absent filter.`,
        );
      }
    } else if (vocabCheck(PARAM_BY_NAME.get("location")!, raw)) {
      state.location = raw as LocationFilter;
    }
  }
  if (lists.has("status")) {
    state.status = lists
      .get("status")!.filter((v) => vocabCheck(PARAM_BY_NAME.get("status")!, v))
      .map((v) => v as EpistemicStatus);
  }
  for (const key of ["seen", "dated"] as const) {
    if (single.has(key)) {
      const raw = single.get(key)!;
      if (RANGE_DATE_RE.test(raw)) {
        state[key] = raw;
      } else {
        badValue(issues, key, `expected YYYY[-MM]..YYYY[-MM], got "${raw}"`);
      }
    }
  }
  if (single.has("currency")) {
    const raw = vocabCheck(PARAM_BY_NAME.get("currency")!, single.get("currency")!);
    if (raw) state.currency = raw as Currency;
  }
  if (single.has("focus")) state.focus = single.get("focus")!;
  if (single.has("page")) {
    const raw = single.get("page")!;
    // v1's rule verbatim: a canonical decimal integer ≥ 1 (so `01`, `0` and
    // `1.5` are all issues), else the visible "unusable page" receipt.
    const parsed = Number.parseInt(raw, 10);
    if (Number.isFinite(parsed) && parsed >= 1 && String(parsed) === raw) {
      state.page = parsed;
    } else {
      issues.push(`Unusable page "${raw}"; showing page 1.`);
    }
  }
  if (single.has("sort")) state.sort = single.get("sort")!;
  if (single.has("dir")) {
    const raw = vocabCheck(PARAM_BY_NAME.get("dir")!, single.get("dir")!);
    if (raw) state.dir = raw as "asc" | "desc";
  }
  if (single.has("cursor")) state.cursor = single.get("cursor")!;
  if (single.has("within")) state.within = single.get("within")!;

  // --- map scope
  if (single.has("at")) {
    const parsed = parseViewport(single.get("at")!);
    if (typeof parsed === "string") {
      badValue(issues, "at", parsed);
    } else {
      state.at = parsed;
    }
  }
  if (single.has("bbox")) {
    // bbox is framing-only and canonicalises to at; it is never re-emitted.
    const folded = bboxToViewport(single.get("bbox")!);
    if (typeof folded === "string") {
      badValue(issues, "bbox", folded);
    } else if (state.at) {
      notes.push(
        `The address's bbox is superseded by its explicit viewport at=${formatViewport(state.at)}.`,
      );
    } else {
      state.at = folded;
      notes.push(
        `The address's bbox resolves to the canonical viewport at=${formatViewport(folded)}.`,
      );
    }
  }
  if (lists.has("layers")) state.layers = lists.get("layers")!;
  if (single.has("basemap")) {
    const raw = vocabCheck(PARAM_BY_NAME.get("basemap")!, single.get("basemap")!);
    if (raw) state.basemap = raw as "0" | "1";
  }

  // --- graph scope
  if (single.has("overview")) state.overview = single.get("overview")!;
  if (single.has("hops")) {
    const raw = vocabCheck(PARAM_BY_NAME.get("hops")!, single.get("hops")!);
    if (raw) state.hops = raw === "1" ? 1 : 2;
  }
  if (lists.has("edge")) state.edge = lists.get("edge")!;
  if (lists.has("expand")) state.expand = lists.get("expand")!;
  if (single.has("path")) {
    const raw = single.get("path")!;
    if (raw.includes("~") && raw.split("~").every((p) => p !== "")) {
      state.path = raw;
    } else {
      badValue(issues, "path", `expected <key>~<key>, got "${raw}"`);
    }
  }

  return { state, issues, notes, present, unregistered };
}

/**
 * Canonicalise a parsed state — the parse already folds `bbox`, so the one
 * fold left is `frame`, which needs a jkey→bounds table this row does not
 * ship (the map row owns it). When a resolver is supplied, `frame` folds
 * into `at` (only when no `at` is set — the explicit viewport always wins)
 * and the receipts land in `notes`. Without one, `frame` round-trips
 * unchanged, which the registry records as the interim posture.
 */
export function canonicaliseWorkspaceState(
  state: WorkspaceState2,
  opts: { frameBounds?: (jkey: string) => Viewport | null } = {},
): { state: WorkspaceState2; notes: string[] } {
  const notes: string[] = [];
  if (state.frame && !state.at && opts.frameBounds) {
    const folded = opts.frameBounds(state.frame);
    if (folded) {
      notes.push(
        `The map frame "${state.frame}" resolves to the canonical viewport at=${formatViewport(folded)}.`,
      );
      return {
        state: { ...state, at: folded, frame: null },
        notes,
      };
    }
  }
  return { state, notes };
}

// --------------------------------------------------------- serialising

function append(params: URLSearchParams, name: string, values: string[]) {
  for (const v of values) params.append(name, v);
}

/**
 * Serialise the v2 state. `v` and `view` are minted first; every other
 * parameter follows the registry order, and defaults are omitted — so
 * `parse(serialize(state))` reproduces `state` and the emitted URL is the
 * canonical form a "cite this view" link carries.
 */
export function serializeWorkspaceState2(state: WorkspaceState2): string {
  const params = new URLSearchParams();
  params.set("v", WORKSPACE_STATE2_VERSION);
  params.set("view", state.view);
  if (state.release) params.set("release", state.release);
  if (state.q !== "") params.set("q", state.q);
  append(params, "type", state.type);
  append(params, "kind", state.kind);
  append(params, "jurisdiction", state.jurisdiction);
  if (state.frame) params.set("frame", state.frame);
  append(params, "technology", state.technology);
  append(params, "vendor", state.vendor);
  append(params, "operator", state.operator);
  append(params, "source", state.source);
  if (state.collectionSpecified || state.collection.length > 0) {
    if (state.collection.length === 0) {
      params.append("collection", "");
    } else {
      append(params, "collection", state.collection);
    }
  }
  if (state.location) params.set("location", state.location);
  append(params, "status", state.status);
  if (state.seen) params.set("seen", state.seen);
  if (state.dated) params.set("dated", state.dated);
  if (state.currency) params.set("currency", state.currency);
  if (state.focus) params.set("focus", state.focus);
  if (state.page !== 1) params.set("page", String(state.page));
  if (state.sort) params.set("sort", state.sort);
  if (state.dir) params.set("dir", state.dir);
  if (state.cursor) params.set("cursor", state.cursor);
  if (state.within) params.set("within", state.within);
  if (state.at) params.set("at", formatViewport(state.at));
  append(params, "layers", state.layers);
  if (state.basemap) params.set("basemap", state.basemap);
  if (state.overview) params.set("overview", state.overview);
  if (state.hops) params.set("hops", String(state.hops));
  append(params, "edge", state.edge);
  append(params, "expand", state.expand);
  if (state.path) params.set("path", state.path);
  return params.toString();
}

/**
 * The canonical href a surface emits for `state` — serialised v2 on the
 * given path (or the surface's own route). `state.view` is the islands'
 * internal vocabulary; `toWireState` emits the registered value.
 */
export function workspaceHref2(
  state: IslandWorkspaceState,
  path?: string,
): string {
  const wire = toWireState(state);
  const serialised = serializeWorkspaceState2(wire);
  const base = path ?? SURFACE_PATHS[VIEW_SURFACE[wire.view]];
  return serialised ? `${base}?${serialised}` : base;
}

/**
 * The href to `view` carrying the caller's whole state — the cross-surface
 * link the view switch and the islands' view nav render. `view` is the
 * internal island vocabulary (`network`), matching the existing call sites.
 */
export function viewHref(
  state: IslandWorkspaceState,
  view: IslandView,
): string {
  return workspaceHref2({ ...state, view });
}

/** The internal view a pathname serves — `/network/` → `network`. */
export function pageView(pathname: string): IslandView {
  const stripped = pathname.replace(/^\/s\/[^/]+/, "");
  for (const [island, surface] of Object.entries(ISLAND_SURFACE) as [
    IslandView,
    WorkspaceSurface,
  ][]) {
    if (stripped.startsWith(SURFACE_PATHS[surface])) return island;
  }
  return "list";
}

// --------------------------------------------------------- state helpers

/**
 * `patch` merges over `state` (shallow; whole-field replacement) and resets
 * the result page — the v1 rule that a query/facet change returns to page 1.
 * The full v2 record rides along so an unapplied parameter is never silently
 * dropped by a field the surface happened not to name.
 */
export function withSearchPatch(
  state: IslandWorkspaceState,
  patch: Partial<IslandWorkspaceState>,
): IslandWorkspaceState {
  return { ...state, ...patch, page: 1 };
}

/** Focus a record (or clear with null), resetting the result page as v1 did. */
export function withFocus(
  state: IslandWorkspaceState,
  focus: string | null,
): IslandWorkspaceState {
  return { ...state, focus, page: 1 };
}

/**
 * The "retain focus only if the selected record remains in scope" rule (S4
 * §7, unchanged from v1): returns the possibly-cleared state and whether the
 * selection was dropped, so the caller can announce "selection cleared"
 * rather than silently losing it.
 */
export function clearFocusOutOfScope(
  state: IslandWorkspaceState,
  inScope: (focus: string) => boolean,
): { state: IslandWorkspaceState; cleared: boolean } {
  if (state.focus !== null && !inScope(state.focus)) {
    return { state: { ...state, focus: null }, cleared: true };
  }
  return { state, cleared: false };
}
