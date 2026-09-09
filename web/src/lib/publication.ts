// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * Jurisdiction-conditional publication in the web build-time data path (§43.8,
 * §44; SIG-PUB-017). This is a faithful TypeScript mirror of the Python policy
 * (`policy.jurisdiction.adapter_publication_permitted` /
 * `policy.publication.publication_permitted`): the shell is static-first
 * (SIG-UI-036) and reads no live API at build, so the same publication decision
 * the Python export gate makes must be re-expressed here to gate what the built
 * dossier HTML contains.
 *
 * The single rule (SIG-PUB-017): a **public-employee name** is publishable only if
 * BOTH the data subject's jurisdiction AND the record's origin jurisdiction permit
 * it; an unknown jurisdiction defaults to the conservative (no-publish) posture.
 * Non-employee-name material is never gated by this rule.
 *
 * Part VIII §0.7 is binding: this can only ever **withhold** — `applyPublicationPolicy`
 * removes a name that may not be published, it never adds or broadens what leaves the
 * system. So the France/Belgium dossiers render every fact the US one does *except*
 * the gated public-employee name, which is shown as withheld with the governing regime.
 */

/** A jurisdiction adapter, minimally what the publication gate + the render need. */
export interface PublicationAdapter {
  /** The jurisdiction code the adapter governs (e.g. "US", "FR", "BE"). */
  code: string;
  /** The BCP-47 language tag the dossier renders in (SIG-UI localisation). */
  lang: string;
  /** The named §43.8 publication regime (e.g. "US-DEFAULT", "FR-GDPR", "BE-GDPR"). */
  profile: string;
}

/** Whether each jurisdiction permits publishing a public-employee name (SIG-PUB-017). */
const PUBLIC_EMPLOYEE_NAMES_PUBLISHABLE: Record<string, boolean> = {
  US: true, // presumptively-public public-employee names (US-DEFAULT)
  FR: false, // redact-by-default under FR-GDPR
  BE: false, // redact-by-default under BE-GDPR
};

/** The conservative default for an unknown jurisdiction: do not publish. */
const DEFAULT_PUBLISHABLE = false;

/** The seeded adapters keyed by jurisdiction code (mirrors the Python adapter set). */
export const PUBLICATION_ADAPTERS: Record<string, PublicationAdapter> = {
  US: { code: "US", lang: "en", profile: "US-DEFAULT" },
  FR: { code: "FR", lang: "fr", profile: "FR-GDPR" },
  BE: { code: "BE", lang: "nl-BE", profile: "BE-GDPR" },
};

/** The adapter for a jurisdiction code, or a conservative US-shaped fallback. */
export function adapterFor(code: string): PublicationAdapter {
  return PUBLICATION_ADAPTERS[code] ?? { code, lang: "en", profile: "UNKNOWN" };
}

function jurisdictionAllowsEmployeeNames(code: string): boolean {
  return PUBLIC_EMPLOYEE_NAMES_PUBLISHABLE[code] ?? DEFAULT_PUBLISHABLE;
}

/**
 * The core SIG-PUB-017 rule: publish a public-employee name only if BOTH the
 * subject's and the record-origin's jurisdictions permit it. Non-employee-name
 * material is always permitted (this rule does not gate it).
 */
export function publicationPermitted(
  subjectJurisdiction: string,
  recordOriginJurisdiction: string,
  opts: { isPublicEmployeeName: boolean },
): boolean {
  if (!opts.isPublicEmployeeName) return true;
  return (
    jurisdictionAllowsEmployeeNames(subjectJurisdiction) &&
    jurisdictionAllowsEmployeeNames(recordOriginJurisdiction)
  );
}

/**
 * The adapter-aware wrapper (mirror of `adapter_publication_permitted`): the data
 * subject's jurisdiction is the adapter's own `code`, and both it and the record's
 * origin jurisdiction must permit publication.
 */
export function adapterPublicationPermitted(
  adapter: PublicationAdapter,
  recordOriginJurisdiction: string,
  opts: { isPublicEmployeeName: boolean },
): boolean {
  return publicationPermitted(adapter.code, recordOriginJurisdiction, opts);
}
