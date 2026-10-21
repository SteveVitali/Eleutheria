// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * Belief-pinned permalinks and the "cite this page" affordance (SIG-UI-035,
 * SIG-TIME-008). Every page carries both. A citation made today MUST remain
 * reproducible after SIG corrects itself, so the permalink pins BOTH as-of axes
 * (world and belief) and the ruleset version: re-resolving that exact triple
 * returns the same answer even after a later correction appends a new claim.
 */

import type { AsOfEcho } from "./fixtures";

export interface CitationInput {
  /** The page's canonical path, e.g. "/entity/agency/okcpd/". */
  path: string;
  title: string;
  asOf: AsOfEcho;
  rulesetVersion: string;
  /** The site origin; defaults to the archival canonical origin. */
  origin?: string;
}

const DEFAULT_ORIGIN = "https://surveillancegraph.org";

/**
 * The belief-pinned permalink: the canonical path with BOTH as-of axes and the
 * ruleset version fixed as query parameters. Because belief-time is pinned, a
 * correction (a new, later-asserted claim) is invisible to this URL — the citation
 * is reproducible (SIG-UI-035, SIG-API-006).
 */
export function beliefPinnedPermalink(input: CitationInput): string {
  const origin = input.origin ?? DEFAULT_ORIGIN;
  const q = new URLSearchParams({
    as_of_world: input.asOf.as_of_world,
    as_of_belief: input.asOf.as_of_belief,
    ruleset: input.rulesetVersion,
  });
  return `${origin}${input.path}?${q.toString()}`;
}

/**
 * The human-readable citation string, in the reporting register (SIG-UI-043):
 * it states the source, the two as-of instants, the ruleset, and the permalink —
 * dated and specific, never "as of now".
 */
export function citationText(input: CitationInput): string {
  const permalink = beliefPinnedPermalink(input);
  return (
    `Surveillance Infrastructure Graph (SIG), "${input.title}", ` +
    `as of world ${input.asOf.as_of_world}, belief ${input.asOf.as_of_belief}, ` +
    `ruleset ${input.rulesetVersion}. Retrieved from ${permalink}`
  );
}

// --------------------------------------------------------------------------- //
// P32.13 (SIG-FIND-001/002, ADR-132): the immutable release citation form.
//
// The belief-pinned query string above is the LEGACY selector: the static host
// does not interpret `?as_of_*` params — it resolves only through the release
// compatibility index (SIG-FIND-002). The citation-grade form is the released
// record URL itself: an immutable namespace whose bytes never change.
// --------------------------------------------------------------------------- //

export interface ReleaseRef {
  /** The activated publication namespace, e.g. "p-<64 hex>". */
  publicationId: string;
  /** The released record path inside the namespace, e.g.
   * "/r/p-<…>/c/sig_graph/entity/deployment/<uuid>/". */
  recordPath: string;
  title: string;
  asOf: AsOfEcho;
  rulesetVersion: string;
  origin?: string;
}

/**
 * The immutable release permalink — the only citation form that resolves the
 * exact released bytes offline and with JavaScript disabled. "Latest" and
 * query-string selectors are conveniences, never citations.
 */
export function releasePermalink(ref: ReleaseRef): string {
  const origin = ref.origin ?? DEFAULT_ORIGIN;
  return `${origin}${ref.recordPath}`;
}

/** The release-form citation string (reporting register, SIG-UI-043). */
export function releaseCitationText(ref: ReleaseRef): string {
  const permalink = releasePermalink(ref);
  return (
    `Surveillance Infrastructure Graph (SIG), "${ref.title}", release ` +
    `${ref.publicationId} (as of world ${ref.asOf.as_of_world}, belief ` +
    `${ref.asOf.as_of_belief}, ruleset ${ref.rulesetVersion}). ` +
    `Retrieved from ${permalink}`
  );
}

// --------------------------------------------------------------------------- //
// P35.42 (SIG-TRANSP-023 — the citation-block half; J3 §8.2 verbatim wording;
// DR-C3-14; F-07/F-099/F-101/F-390/F-399; TX-13b/P36.66a+b own the snapshots and
// edge selectors that make every page's link immutable) — the citation block's
// render model.
//
// `BaseLayout` passes the release context on EVERY public page (the F-399 seam,
// finally wired): `{publicationId, label, recordPath}` — never a page-local
// constant — or `null` only when the build truly binds no release (fixtures /
// development). The immutability condition is a RENDER RULE: the block knows
// whether its cited link is an immutable `/s/<pub>/` or `/r/<pub>/` URL and
// picks the wording accordingly — the reproducibility phrase can never appear
// over a mutable URL (the defect family this row corrects).
// --------------------------------------------------------------------------- //

/** The build's release context the citation block cites (P35.42). */
export interface ReleaseContext {
  /** `p-<64hex>` — the content-addressed publication id (P35.13's stamp). */
  publicationId: string;
  /** `sig-YYYY-MM-DD.N` — the data release id the interim sentence names. */
  label: string;
  /**
   * The path this page's immutable copy resolves at — a released record path
   * (`/r/<pub>/…`) when the page backs a released record, else the page's own
   * path joined under the configured base (`withBase(path)` — `/s/<pub>/…`
   * inside a snapshot build, so the block flips to the immutable wording with
   * no template edits once TX-13b lands the snapshot base).
   */
  recordPath: string;
}

/**
 * `p-3f9ac21e…` — the abbreviated publication id the cite sentence prints
 * (`<pub-short>` in the J3 §8.2 shape); the same slice the release stamp uses
 * (`release-stamp.ts`), so every surface abbreviates identically.
 */
export function publicationShort(publicationId: string): string {
  return `${publicationId.slice(0, 10)}…`;
}

/**
 * The render rule's predicate: ONLY a `/s/<pub>/` or `/r/<pub>/` namespaced
 * path is an immutable citable copy — a snapshot page or a released record
 * under the `p-<64hex>` publication namespace. Any other path (a latest-view
 * route, a half-formed namespace, a selector URL) is mutable and the block
 * must not promise reproducibility over it.
 */
const IMMUTABLE_RELEASE_PATH_RE = /^\/[sr]\/p-[0-9a-f]{64}\//;

export function isImmutableReleasePath(path: string): boolean {
  return IMMUTABLE_RELEASE_PATH_RE.test(path);
}

/**
 * The phrase that may appear ONLY over an immutable link (J3 §8.2; §3.1's
 * defining standard — the promise appears only where it is true).
 */
export const REPRODUCIBLE_PHRASE = "reproducible after SIG corrects itself";

/** The verbatim J3 §8.2 interim wording — until `/s/<pub>/` exists (TX-13b). */
export function interimCitationSentence(releaseLabel: string): string {
  return (
    `This page is the latest view of release ${releaseLabel}; ` +
    `an immutable citable copy is not yet published.`
  );
}

export type CitationBlockMode = "unreleased" | "interim" | "immutable";

/** The citation block's render model — the component is a pure projection. */
export interface CitationBlock {
  mode: CitationBlockMode;
  /**
   * The verbatim J3 §8.2 cite sentence — `Cite: <title>, SIG release
   * <pub-short> (data as of <as_of_world>, belief <as_of_belief>, ruleset
   * <r>)` plus `, <snapshot URL>` only when the URL is genuinely immutable.
   * `null` when no release is bound.
   */
  citeSentence: string | null;
  /** The immutable URL the sentence cites (immutable mode only). */
  citeUrl: string | null;
  /**
   * The release id shown beside the as-of pair (DR-C3-14) — `null` when no
   * release is bound.
   */
  releaseId: string | null;
  /**
   * True only when `citeUrl` is a real `/s/` or `/r/` URL — the
   * reproducibility phrase (REPRODUCIBLE_PHRASE) may render only then.
   */
  reproducible: boolean;
  /** The verbatim J3 interim sentence (interim mode only). */
  interimSentence: string | null;
}

/**
 * The citation block for a page — the ONE function the J3 §8.2 wording flows
 * through (the print dossier renders the same contract, not a second block).
 *
 * `release` is REQUIRED: omitting it (the F-399 shape — `BaseLayout` never
 * passing the release) is a loud failure, while an explicit `null` renders
 * the honest development state. With a release bound, `recordPath` decides
 * the mode: an immutable `/s/<pub>/` or `/r/<pub>/` path yields the cite
 * sentence with the snapshot URL plus the reproducibility phrase; anything
 * else yields the cite sentence plus the verbatim interim sentence — never a
 * fabricated immutable link.
 */
export function citationBlock(
  input: CitationInput & { release: ReleaseContext | null },
): CitationBlock {
  if (input.release === undefined) {
    throw new Error(
      "citation block: the release context is required on every public page " +
        "(SIG-TRANSP-023, F-399) — pass null only when the build binds no release",
    );
  }
  const release = input.release;
  if (release === null) {
    return {
      mode: "unreleased",
      citeSentence: null,
      citeUrl: null,
      releaseId: null,
      reproducible: false,
      interimSentence: null,
    };
  }
  const pair =
    `data as of ${input.asOf.as_of_world}, belief ${input.asOf.as_of_belief}, ` +
    `ruleset ${input.rulesetVersion}`;
  const head = `Cite: ${input.title}, SIG release ${publicationShort(release.publicationId)} (${pair})`;
  if (isImmutableReleasePath(release.recordPath)) {
    const citeUrl = `${input.origin ?? DEFAULT_ORIGIN}${release.recordPath}`;
    return {
      mode: "immutable",
      citeSentence: `${head}, ${citeUrl}`,
      citeUrl,
      releaseId: release.label,
      reproducible: true,
      interimSentence: null,
    };
  }
  return {
    mode: "interim",
    citeSentence: head,
    citeUrl: null,
    releaseId: release.label,
    reproducible: false,
    interimSentence: interimCitationSentence(release.label),
  };
}
