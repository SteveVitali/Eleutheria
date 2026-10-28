// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * P36.22 (K14 UXK14-3a / §4.6 error-row + §6.4, SIG-UI-151 / DR-K14-17,
 * adopted UXR-A12): the branded error-page contract (`sig.error-page/1`) —
 * ONE five-part shape every error page renders, derived from the §6.4 typed
 * pattern: a typed state label, what happened (the named cause), what exists
 * nearby, what the visitor can do, and when it may change.
 *
 * An error is NOT absence: the state never renders the hatch (SIG-UI-151's
 * "hatch only when the emptiness is absence" — a 404 is an address fault, not
 * a gap in the record). Every error page is branded (the shared shell) and
 * carries the three recovery links the requirement names — search, home and
 * status — as plain GET links, no JavaScript (SIG-UI-036/037).
 *
 * Pure data + logic (no markup): `errorPage(code)` returns the contract a
 * page renders through `ErrorState.astro`; an unknown code fails the build
 * (SIG-ENG-042). K14 §6.4's "API down" degraded state reuses the same parts
 * on the surfaces that detect it (P36.23's typed `EmptySurface` kinds).
 */

/** The typed error kinds — a page id, never a bare status number. */
export const ERROR_KINDS = ["not_found", "refused", "removed", "server_error"] as const;
export type ErrorKind = (typeof ERROR_KINDS)[number];

/** Map an HTTP error code to its typed kind (build-time; unknown → throw). */
export function errorKindForCode(code: number): ErrorKind {
  switch (code) {
    case 404:
      return "not_found";
    case 403:
      return "refused";
    case 410:
      return "removed";
    case 500:
      return "server_error";
    default:
      throw new Error(`sig.error-page/1: no typed kind for HTTP ${code}`);
  }
}

/** One recovery link — search, home and status are required on every page. */
export interface ErrorLink {
  href: string;
  label: string;
  /** The copy-batch id the label is tracked under (data-copy), when drafted. */
  batchId?: string;
}

/**
 * The five-part error-page record. `notice` carries a pinned notice string
 * (B-2's notice allowance — `data-notice`, sha256-tracked, never a batch row);
 * `batchIds` binds the drafted sentences to copy-batch rows.
 */
export interface ErrorPageSpec {
  kind: ErrorKind;
  /** 1 — the typed state label (also the page's h1/title text). */
  state: string;
  /** 2 — what happened: the named cause, or the verbatim notice string. */
  missing: string;
  /** 3 — what exists nearby. */
  nearby: string;
  /** 4 — what the visitor can do: the primary action (the home link). */
  action: { href: string; label: string; batchId?: string };
  /** 5 — when it may change. */
  change: string;
  /** Pinned notice the `missing` part renders under (`data-notice`), if any. */
  notice?: string;
  /** Copy-batch ids for the drafted sentences (rendered as `data-copy`). */
  batchIds: { state?: string; missing?: string; nearby?: string; change?: string };
  /** The recovery links beyond the primary action — search + status here;
   *  `action` carries home, so the page always shows the SIG-UI-151 trio. */
  recovery: ErrorLink[];
}

/**
 * The route ids the error pages' action/recovery links point at — declared
 * once so the paths table stays auditable (ErrorState.astro wraps every
 * href in `withBase()`; these constants are data, not link constructions).
 */
const ROUTES = {
  home: "/",
  search: "/search/",
  status: "/status/",
} as const;

/** The shared recovery pair — search + status; `action` supplies home so the
 *  page always carries SIG-UI-151's trio (search · home · status). Ids are
 *  page-scoped, so each page names its own `CK-*` rows. */
function recovery(searchId: string, statusId: string): ErrorLink[] {
  return [
    { href: ROUTES.search, label: "Search the record", batchId: searchId },
    { href: ROUTES.status, label: "Check the status page", batchId: statusId },
  ];
}

const PAGES: Record<ErrorKind, ErrorPageSpec> = {
  not_found: {
    kind: "not_found",
    state: "Page not found",
    missing: "This address does not name a page in the published record.",
    nearby:
      "The record is served whole from the home page; the search page finds a place or a source by name.",
    action: { href: ROUTES.home, label: "Go to the home page", batchId: "NF-02" },
    change:
      "A renamed page redirects or names its new identifier; an address that never existed stays a not-found state.",
    batchIds: { missing: "NF-01", nearby: "CK-43", change: "CK-44" },
    recovery: recovery("CK-45", "CK-46"),
  },
  refused: {
    kind: "refused",
    state: "Access refused",
    missing: "This address is not open to the public record.",
    nearby: "The public record is served whole from the home page.",
    action: { href: ROUTES.home, label: "Go to the home page", batchId: "FB-02" },
    change:
      "Access states change only with a publication decision in a later release, never at request time.",
    batchIds: { missing: "FB-01", nearby: "CK-47", change: "CK-48" },
    recovery: recovery("CK-49", "CK-50"),
  },
  removed: {
    kind: "removed",
    state: "Page removed",
    missing: "This page has been removed while a correction is made.",
    nearby:
      "The corrections log names recorded corrections; the home page serves the record meanwhile.",
    action: { href: ROUTES.home, label: "Go to the home page", batchId: "GN-01" },
    change: "The page returns, or stays removed with a named reason, in a later release.",
    notice: "N-6",
    batchIds: { nearby: "CK-51", change: "CK-52" },
    recovery: recovery("CK-53", "CK-54"),
  },
  server_error: {
    kind: "server_error",
    state: "Something went wrong",
    missing: "The page could not be served from the published record.",
    nearby: "The home page and the record index are served from the same published tree.",
    action: { href: ROUTES.home, label: "Go to the home page", batchId: "CK-55" },
    change: "The status page records any known serving fault; try the address again later.",
    batchIds: { missing: "CK-56", nearby: "CK-57", change: "CK-58" },
    recovery: recovery("CK-59", "CK-60"),
  },
};

/** The five-part error-page contract for a typed kind. */
export function errorPage(kind: ErrorKind): ErrorPageSpec {
  return PAGES[kind];
}

/** The contract for an HTTP code (`errorKindForCode` + `errorPage`). */
export function errorPageForCode(code: number): ErrorPageSpec {
  return errorPage(errorKindForCode(code));
}
