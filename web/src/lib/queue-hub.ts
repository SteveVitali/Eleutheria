// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * P36.61 (K11 RQ-03a / SIG-RQ-004, SIG-UI-079) — the research-queue page model
 * over the `sig.queue-card/2` cards the P36.58 task export emits
 * (`web/research_queue.json`) plus the `sig.queue-campaign/1` rows the
 * `web/tasks/campaign/**` shards and `queue_meta` lanes carry.
 *
 * The surfaces this module serves (all T1, zero-JS — K11 §5):
 *
 *   /research-queue/                          the hub — what the queue is, how
 *                                             to help, start-here entries,
 *                                             counts by type/role, the first
 *                                             ≤50 cards, campaigns, downloads
 *   /research-queue/page/<n>/                 ≤ 50 cards per page (K9 §6.1)
 *   /research-queue/sort/<key>/               priority | newest | oldest
 *   /research-queue/place/<path>/             one place + its slug-path
 *                                             children (`usa/ok` → cities),
 *                                             `…/page/<n>/` + `…/sort/<k>/`
 *                                             riding the rest param, and the
 *                                             nested `…/type/<t>/` minted only
 *                                             for places with > 50 tasks
 *   /research-queue/type/<task_type>/         one-dimension facet routes
 *   /research-queue/role/<assignee>/          (+ their page/sort routes)
 *   /research-queue/campaigns/                the campaign list (the cards the
 *                                             D-K11-1 aggregation emits)
 *
 * Totals reconcile (SIG-RQ-004): every task maps to exactly ONE place facet,
 * ONE type facet and ONE role facet — the per-dimension facet counts sum to
 * the lane total, never a second counting path.
 *
 */

import {
  claimIsActive,
  orderQueue,
  type JurisdictionClaim,
  type ResearchTaskCard,
} from "./research-queue";

// --- The `sig.queue-campaign/1` wire type ----------------------------------- //

export const CAMPAIGN_SCHEMA = "sig.queue-campaign/1";

/** One aggregated field-gap campaign (SIG-RQ-006; D-K11-1 = as recommended). */
export interface QueueCampaign {
  schema?: string;
  kind?: string;
  handle: string;
  predicate_id: string;
  subject_class: string;
  place?: { key?: string | null; slug?: string; name?: string | null };
  member_count: number;
  members?: { task_id?: string; subject_id?: string; subject_label?: string; subject_url?: string }[];
  contribution?: { kind?: string; note?: string };
}

// --- The queue_meta v2 envelope (`sig/analytics-queue-meta/2`) --------------- //

export interface QueueMeta {
  card_schema?: string;
  handle_grammar?: string;
  queue_as_of?: string;
  lanes?: {
    research?: number;
    campaigns?: number;
    campaign_members?: number;
    metric_only_members?: number;
    curation?: { exported?: boolean; note?: string };
  };
  tasks_by_type?: Record<string, number>;
  tasks_by_assignee?: Record<string, number>;
  tasks_by_place?: { slug?: string; name?: string | null; tasks: number }[];
  shards?: { path: string; lane?: string; place_slug?: string; rows?: number; bytes?: number }[];
}

// --- Place facets ------------------------------------------------------------ //

/** The honest unplaced bucket — a data-quality list, never a guessed path. */
export const UNPLACED_PLACE = "unplaced";

/** Lowercase slug for a recorded jurisdiction string (the fixture-export rule). */
export function jurisdictionSlug(jurisdiction: string): string | null {
  const slug = jurisdiction.trim().toLowerCase().replace(/\s+/g, "-");
  return slug || null;
}

/**
 * The card's place-facet key — the v2 card's `place.slug` (already the K4
 * display path), else the recorded jurisdiction folded to a slug, else the
 * unplaced bucket. ONE key per card so facet totals reconcile (SIG-RQ-004).
 */
export function placeSlugOf(card: ResearchTaskCard): string {
  return card.place?.slug ?? jurisdictionSlug(card.jurisdiction) ?? UNPLACED_PLACE;
}

/** The place-facet display name — the card's place name, else the recorded
 *  jurisdiction verbatim, else the bucket's honest label. */
export function placeNameOf(card: ResearchTaskCard): string {
  return card.place?.name ?? (card.jurisdiction.trim() || "Not yet placed");
}

export interface QueuePlaceFacet {
  slug: string;
  name: string;
  tasks: number;
  /** `place.key` of the first card carrying it — absent on unkeyed places. */
  key?: string | null;
  unplaced: boolean;
}

/** The distinct place facets present in `cards` (a facet mints only for a
 *  value that exists — an empty value never mints a page). */
export function placeFacets(cards: readonly ResearchTaskCard[]): QueuePlaceFacet[] {
  const acc = new Map<string, QueuePlaceFacet>();
  for (const card of cards) {
    const slug = placeSlugOf(card);
    const row = acc.get(slug) ?? {
      slug,
      name: placeNameOf(card),
      tasks: 0,
      key: card.place?.key ?? null,
      unplaced: slug === UNPLACED_PLACE,
    };
    row.tasks += 1;
    acc.set(slug, row);
  }
  return [...acc.values()].sort((a, b) => a.slug.localeCompare(b.slug));
}

/**
 * The tasks a place page covers — the place AND its slug-path children (K11
 * §5.2 "state → cities": `usa/ok` covers `usa/ok/<leaf>`). The unplaced
 * bucket covers only unplaced cards.
 */
export function tasksForPlace(
  cards: readonly ResearchTaskCard[],
  slug: string,
): ResearchTaskCard[] {
  return cards.filter(
    (c) => placeSlugOf(c) === slug || placeSlugOf(c).startsWith(`${slug}/`),
  );
}

/** The route path separator — built, never a `"/"` literal site (SIG-REL-008). */
const PATH_SEP = String.fromCharCode(47);

/** Direct child facets of a place (`usa/ok` → `usa/ok/tulsa-4075000`), for
 *  the "children listed" strip; never the place itself. */
export function childFacets(
  facets: readonly QueuePlaceFacet[],
  slug: string,
): QueuePlaceFacet[] {
  return facets.filter(
    (f) =>
      f.slug.startsWith(`${slug}${PATH_SEP}`) &&
      !f.slug.slice(slug.length + 1).includes(PATH_SEP),
  );
}

// --- Type and role facets --------------------------------------------------- //

export interface QueueFacetValue {
  id: string;
  label: string;
  tasks: number;
}

/** "missing_physical_devices" → "Missing physical devices". */
export function typeLabel(taskType: string): string {
  return taskType.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

/** Plain-language role labels (K11 §5.1's "by role" names). */
export const ROLE_LABELS: Record<string, string> = {
  field_mapper: "Check on the ground",
  records_requester: "File a records request",
  document_reviewer: "Review documents",
  analyst: "Analyse data",
  local_group: "Local group work",
  curator: "Curate the record",
  developer: "Fix data tooling",
};

export function roleLabel(assignee: string): string {
  return ROLE_LABELS[assignee] ?? typeLabel(assignee);
}

/** The distinct facet values present in `cards` for one dimension. */
export function facetValues(
  cards: readonly ResearchTaskCard[],
  dim: "task_type" | "assignee_class",
): QueueFacetValue[] {
  const acc = new Map<string, QueueFacetValue>();
  for (const card of cards) {
    const id = String(card[dim]);
    const row = acc.get(id) ?? {
      id,
      label: dim === "task_type" ? typeLabel(id) : roleLabel(id),
      tasks: 0,
    };
    row.tasks += 1;
    acc.set(id, row);
  }
  return [...acc.values()].sort((a, b) => a.id.localeCompare(b.id));
}

export function tasksForType(cards: readonly ResearchTaskCard[], type: string): ResearchTaskCard[] {
  return cards.filter((c) => c.task_type === type);
}

export function tasksForRole(cards: readonly ResearchTaskCard[], role: string): ResearchTaskCard[] {
  return cards.filter((c) => c.assignee_class === role);
}

/**
 * The nested `/research-queue/place/<path>/type/<t>/` routes mint only for
 * places whose covered task set exceeds one page (K11 §5.2 — "only for
 * places with more than 50 tasks").
 */
export const PLACE_TYPE_THRESHOLD = 50;

export function nestedTypeFacets(
  cards: readonly ResearchTaskCard[],
  slug: string,
): QueueFacetValue[] {
  const place = tasksForPlace(cards, slug);
  if (place.length <= PLACE_TYPE_THRESHOLD) return [];
  return facetValues(place, "task_type");
}

// --- Sorts (K11 §4.2: priority, newest, oldest-evidence) --------------------- //

export const QUEUE_SORTS = ["priority", "newest", "oldest"] as const;
export type QueueSort = (typeof QUEUE_SORTS)[number];

export const SORT_LABELS: Record<QueueSort, string> = {
  priority: "Priority",
  newest: "Newest first",
  oldest: "Oldest evidence first",
};

/** The recorded date a task's evidence sits at — the trigger detail's
 *  searched/observed/valid_from date, else the row's generated_at. `""` when
 *  nothing is recorded (never a fabricated age). */
export function evidenceDateOf(card: ResearchTaskCard): string {
  const detail = (card.trigger?.detail ?? {}) as Record<string, unknown>;
  const d =
    (detail["searched_at"] as string | undefined) ??
    (detail["observed_at"] as string | undefined) ??
    (detail["valid_from"] as string | undefined) ??
    card.generated_at;
  return (d ?? "").slice(0, 10);
}

const stableKey = (card: ResearchTaskCard): string =>
  card.handle ?? `${card.task_type}--${card.subject_id}`;

/**
 * The card list under one sort key. `priority` is the queue order (claimed
 * jurisdictions first, then task priority — SIG-TASK-010/012); `newest` is
 * `generated_at` descending; `oldest` is the stale-first order (the oldest
 * evidence date first — undated tasks last). Ties break on the stable key.
 */
export function sortQueue(
  cards: readonly ResearchTaskCard[],
  claims: readonly JurisdictionClaim[],
  asOf: string,
  sort: QueueSort,
): ResearchTaskCard[] {
  if (sort === "priority") return orderQueue(cards, claims, asOf);
  return [...cards].sort((a, b) => {
    if (sort === "newest") {
      const g = (b.generated_at ?? "").localeCompare(a.generated_at ?? "");
      if (g !== 0) return g;
    } else {
      const da = evidenceDateOf(a);
      const db = evidenceDateOf(b);
      // Undated last — a missing date never reads as the oldest evidence.
      const e = (da === "" ? "9999" : da).localeCompare(db === "" ? "9999" : db);
      if (e !== 0) return e;
    }
    return stableKey(a).localeCompare(stableKey(b));
  });
}

// --- Pagination (K9 §6.1 precedent — ≤ 50 cards per page, path routes) ------ //

export const QUEUE_PAGE_SIZE = 50;

export function pageCount(total: number): number {
  return Math.max(1, Math.ceil(total / QUEUE_PAGE_SIZE));
}

export function pageSlice<T>(items: readonly T[], page: number): T[] {
  return items.slice((page - 1) * QUEUE_PAGE_SIZE, page * QUEUE_PAGE_SIZE);
}

export function pageNumbers(total: number): number[] {
  return Array.from({ length: pageCount(total) }, (_, i) => i + 1);
}

// --- The place rest-path parser --------------------------------------------- //

export interface QueuePlacePath {
  /** The place slug path (`usa/ok`, `usa/ok/tulsa-4075000`). */
  path: string;
  /** The nested type facet when present (only minted above the threshold). */
  type?: string;
  sort: QueueSort;
  page: number;
}

/**
 * Parse the `/research-queue/place/` rest param: the slug path plus the
 * optional `type/<t>`, `sort/<k>` and `page/<n>` trailers — in that order
 * (`usa/ok`, `usa/ok/page/2`, `usa/ok/sort/newest`, `usa/ok/sort/newest/page/2`,
 * `usa/ok/type/coverage_hole`, `usa/ok/type/coverage_hole/page/2` …).
 * `null` on a shape the family never mints (SIG-ENG-042 — fail closed).
 */
export function parseQueuePlacePath(raw: string): QueuePlacePath | null {
  let rest = raw.replace(/^\/+|\/+$/g, "");
  if (!rest) return null;
  let page = 1;
  let sort: QueueSort = "priority";
  let type: string | undefined;
  let m = /^(.*?)\/page\/(\d+)$/.exec(rest);
  if (m) {
    rest = m[1]!;
    page = Math.max(1, Number.parseInt(m[2]!, 10));
  }
  m = /^(.*?)\/sort\/([a-z]+)$/.exec(rest);
  if (m) {
    rest = m[1]!;
    if (!(QUEUE_SORTS as readonly string[]).includes(m[2]!)) return null;
    sort = m[2] as QueueSort;
  }
  m = /^(.*?)\/type\/([a-z0-9_]+)$/.exec(rest);
  if (m) {
    rest = m[1]!;
    type = m[2]!;
  }
  if (!rest || /^(page|sort|type)(\/|$)/.test(rest) || /\/(page|sort|type)$/.test(rest)) {
    return null;
  }
  return { path: rest, type, sort, page };
}

// --- Route helpers (all withBase()'d at the page; no leading slash here) ---- //

export function queuePageHref(n: number): string {
  return `research-queue/page/${n}/`;
}

export function queueSortHref(sort: QueueSort, page = 1): string {
  return page > 1
    ? `research-queue/sort/${sort}/page/${page}/`
    : `research-queue/sort/${sort}/`;
}

export function queuePlaceHref(slug: string, sort: QueueSort = "priority", page = 1): string {
  let href = `research-queue/place/${slug}/`;
  if (sort !== "priority") href += `sort/${sort}/`;
  if (page > 1) href += `page/${page}/`;
  return href;
}

export function queueTypeHref(type: string, sort: QueueSort = "priority", page = 1): string {
  let href = `research-queue/type/${type}/`;
  if (sort !== "priority") href += `sort/${sort}/`;
  if (page > 1) href += `page/${page}/`;
  return href;
}

export function queueRoleHref(role: string, sort: QueueSort = "priority", page = 1): string {
  let href = `research-queue/role/${role}/`;
  if (sort !== "priority") href += `sort/${sort}/`;
  if (page > 1) href += `page/${page}/`;
  return href;
}

export function queuePlaceTypeHref(
  slug: string,
  type: string,
  sort: QueueSort = "priority",
  page = 1,
): string {
  let href = `research-queue/place/${slug}/type/${type}/`;
  if (sort !== "priority") href += `sort/${sort}/`;
  if (page > 1) href += `page/${page}/`;
  return href;
}

export function queueCampaignsHref(page = 1): string {
  return page > 1 ? `research-queue/campaigns/page/${page}/` : "research-queue/campaigns/";
}
