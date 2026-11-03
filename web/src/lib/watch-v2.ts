// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * P36.59 (K7 WX-04a / SIG-WATCH-001…004, 009, 010) — the watch decision
 * calendar's page model over the `sig/watch/2` envelope the P35.43 producer
 * emits (`web/watch.json`, `sig.watch-item/1` items).
 *
 * The surfaces this module serves (all T1, zero-JS — K7 §5.4):
 *
 *   /watch/                          upcoming decisions, next 90 days (the
 *                                    declared `build.windows.list_days`)
 *   /watch/page/<n>/                 ≤ 50 rows per page
 *   /watch/place/<path>/             one place + its registry children, WITH
 *                                    the coverage statement (SIG-WATCH-004)
 *   /watch/place/<path>/page/<n>/    …/page/<n>/ rides the rest param
 *   /watch/kind/<kind>/              one-dimension facet routes
 *   /watch/vendor/<id>/              vendor = the reviewed-vocab term id the
 *   /watch/technology/<id>/          item's match claims declared (never
 *                                    inferred — the producer emits only what
 *                                    the vocabulary bound)
 *   /watch/item/<handle>/            the item: one alert date with kind +
 *                                    certainty, timeline, evidence links,
 *                                    upstream, what you can do, tasks
 *   /watch/history/<path>/           the place's past items (the producer's
 *                                    ≤30-day `recently_decided` window today)
 *   /watch/feeds/                    the subscription directory
 *
 * Place routes use the K4 display path with slashes (`usa/tx`,
 * `usa/tx/harris-county-48201` — C-10); the coverage block's `places[].slug`
 * IS that path for a keyed export. Vendor/technology routes use the reviewed
 * vocabulary's term ids (GX-03 keys — C-10).
 *
 * Honesty rules encoded (SIG-WATCH-002/003/010):
 *
 *   - ONE alert date per item, with its `date_kind` + `date_certainty`; an
 *     `upper_bound` date renders "latest possible date" — the word
 *     "deadline" NEVER labels it (SIG-WATCH-002);
 *   - every item links its supporting claims (the evidence viewer when a
 *     route exists, the claim id verbatim otherwise) and its upstream
 *     document under the J3 §5.3 lane table form (SIG-WATCH-003);
 *   - an empty place shows the typed cause class — `not_connected` /
 *     `not_monitored` / `none_found` — WITH the coverage statement, never
 *     stale items and never a "research gap" blame (SIG-WATCH-010);
 *   - nothing is fabricated: a field absent on the wire renders the named
 *     absence token, never a guessed value.
 */

import { NOT_PUBLISHABLE, NOT_RECORDED, NO_UPSTREAM_URL } from "./provenance-panel";

// --- The `sig.watch-item/1` + `sig/watch/2` wire types ---------------------- //

export const WATCH_SCHEMA = "sig/watch/2";
export const WATCH_ITEM_SCHEMA = "sig.watch-item/1";

/** The six §5.2 kinds the v1 producer derives (closed list — a kind outside
 *  it fails the fixture guard, never a silently-rendered unknown). */
export const WATCH_KINDS = [
  "renewal_deadline",
  "contract_expiry",
  "solicitation_deadline",
  "agenda_item",
  "legislative_action",
  "grant_period_end",
] as const;
export type WatchKind = (typeof WATCH_KINDS)[number];

/** Plain-language kind labels for the facet routes + list rows. */
export const WATCH_KIND_LABELS: Record<WatchKind, string> = {
  renewal_deadline: "Renewal decision",
  contract_expiry: "Contract expiry",
  solicitation_deadline: "Solicitation deadline",
  agenda_item: "Agenda item",
  legislative_action: "Legislative action",
  grant_period_end: "Grant period end",
};

/** `date_kind` — WHAT the one alert date is (never a certainty claim). */
export const DATE_KIND_LABELS: Record<string, string> = {
  notice_deadline: "notice deadline",
  expiry: "contract expiry date",
  response_deadline: "response deadline",
  meeting: "meeting",
  scheduled_action: "scheduled action",
  status_change: "status change",
  period_end: "period end",
};

/**
 * `date_certainty` — SIG-WATCH-002: an `upper_bound` is "the latest possible
 * date — the real deadline may be earlier", and the word "deadline" never
 * labels it (the kind/date_kind text is kept separate and never composed
 * with the certainty label into a deadline claim — see `itemDateLabel`).
 */
export const CERTAINTY_LABELS: Record<string, string> = {
  stated: "stated",
  derived: "derived",
  upper_bound: "latest possible date",
};

/** The §5.1 status vocabulary + its list-row wording. */
export const WATCH_STATUSES = [
  "upcoming",
  "today",
  "recently_decided",
  "superseded",
  "withdrawn",
] as const;
export type WatchStatus = (typeof WATCH_STATUSES)[number];

export const STATUS_LABELS: Record<WatchStatus, string> = {
  upcoming: "upcoming",
  today: "today",
  recently_decided: "recently decided",
  superseded: "date moved",
  withdrawn: "withdrawn",
};

export interface WatchUpstream {
  status?: string;
  url?: string | null;
  host?: string | null;
  path_sha256?: string | null;
}

/** One `evidence[]` row — a claim behind the item plus its upstream block. */
export interface WatchEvidenceLink {
  claim_id: string;
  predicate?: string;
  source_id?: string | null;
  artifact_ids?: string[];
  upstream?: WatchUpstream;
}

export interface WatchTimelineRow {
  kind: string;
  date: string;
  claim_id?: string;
}

export interface WatchPlaceRef {
  key?: string | null;
  chain?: string[];
  basis?: string | null;
  check?: string | null;
  declared_scheme?: string | null;
  declared_value?: string | null;
  boundary_vintage?: string | null;
}

export interface WatchTaskRef {
  task_id: string;
  task_type?: string;
  status?: string;
}

export interface WatchItemV2 {
  schema?: string;
  handle: string;
  title: string;
  kind: WatchKind;
  /** The ONE alert date (SIG-WATCH-002) — ISO `YYYY-MM-DD`. */
  date: string;
  date_kind: string;
  date_certainty: "stated" | "derived" | "upper_bound";
  timeline?: WatchTimelineRow[];
  place?: WatchPlaceRef | null;
  body?: string | null;
  subjects?: string[];
  technology?: { id: string; label: string }[];
  vendor?: { id: string; label: string }[];
  status?: WatchStatus;
  what_you_can_do?: string;
  evidence?: WatchEvidenceLink[];
  contested?: boolean;
  tasks?: WatchTaskRef[];
  first_seen?: string | null;
  last_checked?: string;
  source_ids?: string[];
  termination?: {
    expiry_date?: string | null;
    auto_renews?: boolean | null;
    notice_window_days?: number | null;
  };
}

/** One `coverage.places[]` row — a dossier place's watch coverage record. */
export interface WatchCoveragePlace {
  key: string;
  slug: string;
  items: number;
  kinds?: string[];
  last_checked?: string;
}

export interface WatchCoverage {
  monitored?: {
    tenant_jurisdictions?: string[];
    tenants_registered?: number;
  };
  places?: WatchCoveragePlace[];
  by_kind?: Record<string, number>;
  items_total?: number;
  sizing?: Record<string, { subjects?: number; claims?: number }>;
  last_checked?: string;
}

/** The `sig/watch/2` envelope (P35.43 `build_watch_payload`). */
export interface WatchEnvelopeV2 {
  schema?: string;
  as_of?: string;
  generated_at?: string;
  build?: {
    ruleset?: string;
    windows?: {
      list_days?: number;
      recently_decided_days?: number;
      contract_horizon_days?: number;
      solicitation_from?: string;
      basis?: string;
    };
    what_you_can_do_basis?: string;
  };
  coverage?: WatchCoverage;
  items: WatchItemV2[];
}

// --- Item helpers ---------------------------------------------------------- //

/** The closed-vocabulary check a fixture/render asserts (SIG-ENG-042): a
 *  kind outside the §5.2 list is a producer/schema drift, never rendered. */
export function isWatchKind(kind: string): kind is WatchKind {
  return (WATCH_KINDS as readonly string[]).includes(kind);
}

/**
 * The one alert date's rendered label: the date + its kind + certainty,
 * composed so `upper_bound` NEVER sits beside the word "deadline"
 * (SIG-WATCH-002). `solicitation_deadline`'s date_kind literally names a
 * deadline — it only ever pairs with `stated` certainty, and the guard here
 * drops the kind word for an upper_bound row whatever its kind.
 */
export function itemDateLabel(item: WatchItemV2): {
  date: string;
  kindLabel: string;
  certaintyLabel: string;
} {
  const certainty = item.date_certainty ?? "stated";
  const kindLabel =
    certainty === "upper_bound"
      ? "expiry"
      : (DATE_KIND_LABELS[item.date_kind] ?? item.date_kind);
  return {
    date: item.date,
    kindLabel,
    certaintyLabel: CERTAINTY_LABELS[certainty] ?? certainty,
  };
}

/** Sort order shared by every list: alert date, then handle (stable). */
export function byWatchDate(a: WatchItemV2, b: WatchItemV2): number {
  return a.date.localeCompare(b.date) || a.handle.localeCompare(b.handle);
}

/**
 * The default index list — the next `list_days` of items (the envelope's
 * declared window, defaulting to the design's 90). Past-window items
 * (recently decided ≤30 days, today) stay listed; a future item beyond the
 * horizon is reachable through the place/kind/facet routes.
 */
export function listItems(envelope: WatchEnvelopeV2): WatchItemV2[] {
  const listDays = envelope.build?.windows?.list_days ?? 90;
  const asOf = envelope.as_of ?? "";
  const horizon = asOf ? addDays(asOf, listDays) : "";
  return [...envelope.items]
    .filter((i) => !horizon || i.date <= horizon)
    .sort(byWatchDate);
}

/** `YYYY-MM-DD` + n days — UTC arithmetic, no timezone drift. */
function addDays(iso: string, days: number): string {
  const ms = Date.parse(`${iso.slice(0, 10)}T00:00:00Z`);
  if (Number.isNaN(ms)) return iso;
  return new Date(ms + days * 86_400_000).toISOString().slice(0, 10);
}

// --- Place resolution (C-10: K4 display paths) ----------------------------- //

/** The watch place path for a coverage row — its slug IS the K4 display
 *  path on a keyed export (the producer emits `slug_path`). */
export const UNPLACED_WATCH_PATH = "unplaced";

/** `jkey → slug_path` lookup the pages build once from the coverage rows +
 *  the dossier index + the jurisdiction key map (all optional except the
 *  coverage rows — a bare item key never fabricates a path). */
export type WatchSlugMap = ReadonlyMap<string, string>;

/** One emitted watch place page's descriptor. */
export interface WatchPlacePage {
  /** The jurisdiction key this page covers (`null` = the unplaced bucket). */
  key: string | null;
  /** The K4 display path — the route's rest segment (`usa/tx/…`). */
  path: string;
  /** The rendered name (index display name, else the key itself). */
  name: string;
  /** The coverage row the producer emitted for this place, if any. */
  coverage?: WatchCoveragePlace;
  /** True when the `unplaced` data-quality bucket, not a real place. */
  unplaced: boolean;
}

/**
 * A display name from a K4 slug path's last segment (`cleveland-county-40131`
 * → "Cleveland County") — used only when no index/keymap name exists; the
 * trailing numeric suffix (a GEOID) is stripped, never shown as a name.
 */
export function nameFromSlug(slug: string): string {
  const last = slug.split(/\//).pop() ?? slug;
  const stem = last.replace(/-\d+$/, "").replace(/-/g, " ").trim();
  if (!stem) return slug;
  return stem.replace(/\b\w/g, (c) => c.toUpperCase());
}

/**
 * The emitted place-page set — SIG-WATCH-004: every dossier-index place in
 * the coverage block gets a page (empty or not), plus the `unplaced` bucket
 * (a data-quality list, not a place — labelled as such), plus any item
 * place key the slug map resolves that the coverage block does not name.
 * An unresolvable key never mints a guessed path — its items still list on
 * the index and their item pages name the key verbatim.
 */
export function placePages(
  envelope: WatchEnvelopeV2,
  slugMap: WatchSlugMap,
  names?: ReadonlyMap<string, string>,
): WatchPlacePage[] {
  const pages = new Map<string, WatchPlacePage>();
  const byKey = new Map<string, WatchCoveragePlace>();
  for (const row of envelope.coverage?.places ?? []) {
    if (!row.key || !row.slug) continue;
    byKey.set(row.key, row);
    pages.set(row.slug, {
      key: row.key,
      path: row.slug,
      name: names?.get(row.key) ?? nameFromSlug(row.slug),
      coverage: row,
      unplaced: false,
    });
  }
  const itemKeys = new Set<string>();
  for (const item of envelope.items) {
    for (const k of [item.place?.key, ...(item.place?.chain ?? [])]) {
      if (k) itemKeys.add(k);
    }
  }
  for (const key of itemKeys) {
    const slug = byKey.get(key)?.slug ?? slugMap.get(key);
    if (!slug || pages.has(slug)) continue;
    pages.set(slug, {
      key,
      path: slug,
      name: names?.get(key) ?? nameFromSlug(slug),
      unplaced: false,
    });
  }
  const out = [...pages.values()].sort((a, b) => a.path.localeCompare(b.path));
  if (envelope.items.some((i) => !i.place?.key) || out.length === 0) {
    out.push({
      key: null,
      path: UNPLACED_WATCH_PATH,
      name: "Not yet placed",
      unplaced: true,
    });
  }
  return out;
}

/** The route param a place page's rest path parses back to (`usa/tx` or
 *  `usa/tx/page/2` — pagination rides the same rest param). */
export function parsePlacePath(
  raw: string,
): { path: string; page: number } | null {
  const m = /^(.*?)\/page\/(\d+)$/.exec(raw);
  const path = m ? m[1]! : raw;
  const page = m ? Math.max(1, Number.parseInt(m[2]!, 10)) : 1;
  return path ? { path, page } : null;
}

/** The items a place page covers — the place AND its registry children
 *  (K7 §5.4 "state → counties/cities": chain membership). `null` key = the
 *  unplaced bucket (items carrying no place key). */
export function itemsForPlace(items: readonly WatchItemV2[], key: string | null): WatchItemV2[] {
  if (key === null) return items.filter((i) => !i.place?.key).sort(byWatchDate);
  return items
    .filter((i) => i.place?.key === key || (i.place?.chain ?? []).includes(key))
    .sort(byWatchDate);
}

/** Past items for a place — the history archive (the producer's ≤30-day
 *  `recently_decided` window today; the page says so honestly). */
export function historyItems(
  items: readonly WatchItemV2[],
  key: string | null,
  asOf: string,
): WatchItemV2[] {
  return itemsForPlace(items, key)
    .filter((i) => i.date < asOf || i.status === "recently_decided" || i.status === "withdrawn" || i.status === "superseded")
    .sort(byWatchDate);
}

// --- Facets ---------------------------------------------------------------- //

export function itemsForKind(items: readonly WatchItemV2[], kind: WatchKind): WatchItemV2[] {
  return items.filter((i) => i.kind === kind).sort(byWatchDate);
}

export function itemsForVendor(items: readonly WatchItemV2[], id: string): WatchItemV2[] {
  return items.filter((i) => (i.vendor ?? []).some((v) => v.id === id)).sort(byWatchDate);
}

export function itemsForTechnology(items: readonly WatchItemV2[], id: string): WatchItemV2[] {
  return items.filter((i) => (i.technology ?? []).some((t) => t.id === id)).sort(byWatchDate);
}

export interface WatchFacetValue {
  id: string;
  label: string;
  items: number;
}

/** The distinct reviewed-vocab facet values present in `items` (a facet
 *  route mints only for a value that exists — an empty value never mints a
 *  page). */
export function facetValues(
  items: readonly WatchItemV2[],
  dim: "vendor" | "technology",
): WatchFacetValue[] {
  const acc = new Map<string, WatchFacetValue>();
  for (const i of items) {
    for (const v of i[dim] ?? []) {
      const row = acc.get(v.id) ?? { id: v.id, label: v.label || v.id, items: 0 };
      row.items += 1;
      acc.set(v.id, row);
    }
  }
  return [...acc.values()].sort((a, b) => a.label.localeCompare(b.label));
}

/** The kinds present in `items`, in canonical order (facet routes). */
export function kindsPresent(items: readonly WatchItemV2[]): WatchKind[] {
  const set = new Set(items.map((i) => i.kind));
  return WATCH_KINDS.filter((k) => set.has(k));
}

// --- Pagination (K9 §6.1 precedent — ≤ 50 rows per page, path routes) ------ //

export const WATCH_PAGE_SIZE = 50;

export function pageCount(total: number): number {
  return Math.max(1, Math.ceil(total / WATCH_PAGE_SIZE));
}

export function pageSlice<T>(items: readonly T[], page: number): T[] {
  return items.slice((page - 1) * WATCH_PAGE_SIZE, page * WATCH_PAGE_SIZE);
}

/** The page numbers a route emits (`1` only until 51+ items — the §6.1
 *  pagination fallback never mints an empty `page/2/`). */
export function pageNumbers(total: number): number[] {
  return Array.from({ length: pageCount(total) }, (_, i) => i + 1);
}

// --- Route helpers (all withBase()'d at the page; no leading slash here) --- //

export function watchItemHref(handle: string): string {
  return `watch/item/${handle}/`;
}

export function watchPlaceHref(path: string): string {
  return `watch/place/${path}/`;
}

export function watchHistoryHref(path: string): string {
  return `watch/history/${path}/`;
}

export function watchKindHref(kind: WatchKind): string {
  return `watch/kind/${kind}/`;
}

export function watchVendorHref(id: string): string {
  return `watch/vendor/${id}/`;
}

export function watchTechnologyHref(id: string): string {
  return `watch/technology/${id}/`;
}

/** The place-page href for one item — the emitted page when the key resolves
 *  to a minted path, else the unplaced bucket only when the item truly has
 *  no key; `null` when no page honestly answers (never a dead link). */
export function itemPlaceHref(item: WatchItemV2, pages: readonly WatchPlacePage[]): string | null {
  const key = item.place?.key ?? null;
  const page = pages.find((p) => (key === null ? p.unplaced : p.key === key));
  if (page) return watchPlaceHref(page.path);
  // The item's place key has no minted page — climb its chain to the nearest
  // ancestor that does (the dossier breadcrumb's own climb rule).
  for (const k of [...(item.place?.chain ?? [])].reverse()) {
    const found = pages.find((p) => p.key === k);
    if (found) return watchPlaceHref(found.path);
  }
  return null;
}

// --- Evidence + upstream rendering (SIG-WATCH-003, J3 §5.3) ----------------- //

export interface UpstreamDisplay {
  display: string;
  href: string | null;
}

/**
 * The upstream block's publication form — the same closed mapping
 * `provenance-panel.ts` renders (full URL, host + path-hash, withheld, or
 * the named absence). A `withheld_by_policy` block NEVER renders a link.
 */
export function upstreamDisplay(up: WatchUpstream | null | undefined): UpstreamDisplay {
  const status = up?.status ?? NO_UPSTREAM_URL;
  if (status === "full_url" && up?.url) {
    return { display: up.url, href: up.url };
  }
  if (status === "host_only" && up?.host) {
    return {
      display: `${up.host}#path_sha256:${up.path_sha256 ?? NOT_RECORDED}`,
      href: `https://${up.host}/`,
    };
  }
  if (status === "withheld_by_policy") {
    return { display: NOT_PUBLISHABLE, href: null };
  }
  return { display: NO_UPSTREAM_URL, href: null };
}

/** The item's evidence rows, sorted deterministically (predicate, claim id). */
export function evidenceRows(item: WatchItemV2): WatchEvidenceLink[] {
  return [...(item.evidence ?? [])].sort((a, b) =>
    String(a.predicate ?? "").localeCompare(String(b.predicate ?? "")) ||
    a.claim_id.localeCompare(b.claim_id),
  );
}

// --- Empty-state cause classes (SIG-WATCH-010) ------------------------------ //

/**
 * The watch's typed emptiness causes — the design's three classes verbatim
 * (K7 §5.6): a pipeline gap (`not_connected`), a place SIG does not check
 * (`not_monitored`), and a checked place with genuinely nothing upcoming
 * (`none_found`). A pipeline gap NEVER reads as a research gap, and an empty
 * result always arrives WITH the coverage statement.
 */
export type WatchEmptiness = "not_connected" | "not_monitored" | "none_found";

/**
 * The cause class for a place page's empty state:
 *   - no coverage block at all → `not_connected` (the producer's coverage
 *     read is absent — a pipeline gap, never a research gap);
 *   - a coverage row exists and the place's name is among the monitored
 *     tenant jurisdictions → `none_found` (SIG checks here and found
 *     nothing upcoming as of `last_checked`);
 *   - otherwise → `not_monitored` (SIG does not yet check a body/portal for
 *     this place — the queue-affordance case, K7 §5.6).
 */
export function placeEmptiness(
  page: WatchPlacePage,
  coverage: WatchCoverage | undefined,
  allPages: readonly WatchPlacePage[] = [page],
  names?: ReadonlyMap<string, string>,
): WatchEmptiness {
  if (coverage === undefined) return "not_connected";
  const monitored = new Set(
    (coverage.monitored?.tenant_jurisdictions ?? []).map((n) => n.trim().toLowerCase()),
  );
  // "None found" when SIG checks this place or one of its descendants (a
  // state whose county portal is monitored is monitored-through-children —
  // the place page covers place + children, so the cause follows the same
  // set). Descendants resolve by path prefix (the slug_path hierarchy).
  const selfAndDescendants = allPages.filter(
    (p) => p.path === page.path || p.path.startsWith(`${page.path}/`),
  );
  const shortName = (p: WatchPlacePage) =>
    (names?.get(p.key ?? "") ?? p.name).split(",")[0]!.trim().toLowerCase();
  const monitoredHere = selfAndDescendants.some((p) => monitored.has(shortName(p)));
  return monitoredHere ? "none_found" : "not_monitored";
}

/**
 * The per-place coverage statement rendered WITH every empty result
 * (SIG-WATCH-004): what SIG checks (the registered agenda/procurement
 * tenants count) and when it last checked — never a bare "no items".
 */
export interface CoverageStatement {
  /** `SIG checks N agenda/procurement tenants` — the registered set's size. */
  tenantsRegistered: number;
  /** The tenant jurisdictions named (bodies/portals monitored). */
  tenantJurisdictions: string[];
  /** The coverage row for THIS place (items + kinds + last checked), if any. */
  placeRow?: WatchCoveragePlace;
  /** The build's coverage last-checked timestamp. */
  lastChecked?: string;
  /** Per-family publishable subject/claim counts (the sizing read). */
  sizing: Record<string, { subjects?: number; claims?: number }>;
}

export function coverageStatement(
  page: WatchPlacePage,
  coverage: WatchCoverage | undefined,
): CoverageStatement {
  return {
    tenantsRegistered: coverage?.monitored?.tenants_registered ?? 0,
    tenantJurisdictions: coverage?.monitored?.tenant_jurisdictions ?? [],
    placeRow: page.coverage,
    lastChecked: page.coverage?.last_checked ?? coverage?.last_checked,
    sizing: coverage?.sizing ?? {},
  };
}
