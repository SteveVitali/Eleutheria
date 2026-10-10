// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * P34.14 (QW-8, K15 §3.7.1, F-105): the interim jurisdiction display-name
 * lookup. The published wire field `jurisdiction` is a bare code — the
 * connector registry emits four schemes (`us.state_abbr`,
 * `iso.3166_1_alpha2`, `iso.3166_2`, `sig.unresolved`) — and until JUR-05 lands
 * the full jurisdiction model every place a person reads must show the place's
 * NAME with the code kept secondary ("Alabama (AL)"), never the bare code
 * alone.
 *
 * The table is deterministic and additive. Names are code↔name facts from the
 * schemes the registry declares — USPS state abbreviations, ISO 3166-1 alpha-2
 * country names, ISO 3166-2 subdivision names (CO-MET is Meta, Colombia;
 * IE-DL is Donegal, Ireland) — asserted the same way the registry asserts its
 * codes; no third-party expression is copied (the derived-facts basis,
 * ADR-085/086).
 *
 * Values already carrying a name (the fixture dossiers' "Paris, France") pass
 * through untouched — both data modes render the same. A bare code the table
 * does not know fails loud: it renders as "Unspecified jurisdiction (CODE)",
 * is flagged `known: false`, and the surfaces that show it carry the
 * research-queue task affordance (the flag is honest, never a guessed name).
 *
 * Two codes are PHYSICALLY mixed buckets — the same emitted code is asserted
 * under two schemes today (`ID` is both US `ID` Idaho and ISO `ID` Indonesia;
 * `MN` is both US `MN` Minnesota and ISO `MN` Mongolia, K4 NEW-1). They have no
 * single honest name, so the display says which two places the dossier
 * combines until the JUR-05 split pages exist.
 */

/** Place name by emitted code. US state/territory abbreviations map to their
 * `us.state_abbr` meaning — the registry's dominant scheme — EXCEPT `DE`
 * (emitted today only as ISO Germany), and `ID`/`MN` (physically mixed —
 * see `JURISDICTION_COMBINES`). */
export const JURISDICTION_NAMES: Readonly<Record<string, string>> = {
  // us.state_abbr — all US states + DC + territories except the codes the
  // registry emits under a different scheme today.
  AL: "Alabama",
  AK: "Alaska",
  AZ: "Arizona",
  AR: "Arkansas",
  CA: "California",
  CO: "Colorado",
  CT: "Connecticut",
  DC: "District of Columbia",
  FL: "Florida",
  GA: "Georgia",
  HI: "Hawaii",
  IL: "Illinois",
  IN: "Indiana",
  IA: "Iowa",
  KS: "Kansas",
  KY: "Kentucky",
  LA: "Louisiana",
  ME: "Maine",
  MD: "Maryland",
  MA: "Massachusetts",
  MI: "Michigan",
  MS: "Mississippi",
  MO: "Missouri",
  MT: "Montana",
  NE: "Nebraska",
  NV: "Nevada",
  NH: "New Hampshire",
  NJ: "New Jersey",
  NM: "New Mexico",
  NY: "New York",
  NC: "North Carolina",
  ND: "North Dakota",
  OH: "Ohio",
  OK: "Oklahoma",
  OR: "Oregon",
  PA: "Pennsylvania",
  RI: "Rhode Island",
  SC: "South Carolina",
  SD: "South Dakota",
  TN: "Tennessee",
  TX: "Texas",
  UT: "Utah",
  VT: "Vermont",
  VA: "Virginia",
  WA: "Washington",
  WV: "West Virginia",
  WI: "Wisconsin",
  WY: "Wyoming",
  AS: "American Samoa",
  GU: "Guam",
  MP: "Northern Mariana Islands",
  PR: "Puerto Rico",
  VI: "U.S. Virgin Islands",
  // iso.3166_1_alpha2 — the country codes the registry emits today.
  BD: "Bangladesh",
  BE: "Belgium",
  DE: "Germany",
  GB: "United Kingdom",
  HK: "Hong Kong",
  JP: "Japan",
  MY: "Malaysia",
  NL: "Netherlands",
  NZ: "New Zealand",
  PS: "Palestine",
  PT: "Portugal",
  SA: "Saudi Arabia",
  TH: "Thailand",
  US: "United States",
  // The two physically mixed buckets (K4 NEW-1): the name itself says which
  // two places the bucket combines, matching the `combines` pair.
  ID: "Idaho (US) and Indonesia",
  MN: "Minnesota and Mongolia",
  // iso.3166_2 — the subdivision codes the registry emits today.
  "AU-ACT": "Australian Capital Territory, Australia",
  "AU-NSW": "New South Wales, Australia",
  "AU-QLD": "Queensland, Australia",
  "AU-TAS": "Tasmania, Australia",
  "AU-VIC": "Victoria, Australia",
  "AU-WA": "Western Australia, Australia",
  "CA-AB": "Alberta, Canada",
  "CA-BC": "British Columbia, Canada",
  "CA-MB": "Manitoba, Canada",
  "CA-ON": "Ontario, Canada",
  "CA-QC": "Quebec, Canada",
  "CO-MET": "Meta, Colombia",
  "GB-ENG": "England, United Kingdom",
  "GB-NIR": "Northern Ireland, United Kingdom",
  "GB-SCT": "Scotland, United Kingdom",
  "IE-DL": "Donegal, Ireland",
  // P35.6 (ACQ-01): the generated R11 targets carry full iso.3166_2 codes
  // (R4) — the US states they emit, named under the same derived-facts basis.
  "US-AL": "Alabama, United States",
  "US-CA": "California, United States",
  "US-CO": "Colorado, United States",
  "US-CT": "Connecticut, United States",
  "US-DE": "Delaware, United States",
  "US-FL": "Florida, United States",
  "US-GA": "Georgia, United States",
  "US-IL": "Illinois, United States",
  "US-IN": "Indiana, United States",
  "US-LA": "Louisiana, United States",
  "US-MD": "Maryland, United States",
  "US-MI": "Michigan, United States",
  "US-NC": "North Carolina, United States",
  "US-NE": "Nebraska, United States",
  "US-NM": "New Mexico, United States",
  "US-NV": "Nevada, United States",
  "US-NY": "New York, United States",
  "US-OR": "Oregon, United States",
  "US-TN": "Tennessee, United States",
  "US-TX": "Texas, United States",
  "US-VA": "Virginia, United States",
  "US-WA": "Washington, United States",
  // sig.unresolved — the empty-resolution bucket, shown as what it is.
  unresolved: "Unresolved jurisdiction",
};

/** The two places each physically mixed bucket combines (K4 NEW-1). The order
 * is the registry's: the US-scheme place first, then the ISO-scheme place. */
export const JURISDICTION_COMBINES: Readonly<Record<string, readonly [string, string]>> = {
  ID: ["Idaho (US)", "Indonesia"],
  MN: ["Minnesota", "Mongolia"],
};

/** The name shown for a bare code the table does not know — loud, honest,
 * and never confused for a real place (AC5). */
export const JURISDICTION_UNMAPPED_NAME = "Unspecified jurisdiction";

export interface JurisdictionDisplay {
  /** The place's name — never a bare code. */
  name: string;
  /** The bare code the input carried, or null when the input already named
   * the place (fixture data) or is the `unresolved` bucket. */
  code: string | null;
  /** `Name (CODE)` when a code applies; otherwise the name alone. */
  label: string;
  /** Whether the input was recognised — false only for an unmapped code. */
  known: boolean;
  /** For a physically mixed bucket, the two places it combines. */
  combines: readonly [string, string] | null;
}

/** A bare emitted code is uppercase alphanumerics plus dashes (`AL`,
 * `AU-QLD`, `unresolved` is handled before this check applies). */
const BARE_CODE = /^[A-Z0-9-]+$/;

export function displayJurisdiction(value: string): JurisdictionDisplay {
  const combines = JURISDICTION_COMBINES[value] ?? null;
  const name = JURISDICTION_NAMES[value];
  if (name !== undefined) {
    const code = value === "unresolved" ? null : value;
    return {
      name,
      code,
      label: code === null ? name : `${name} (${code})`,
      known: true,
      combines,
    };
  }
  if (BARE_CODE.test(value)) {
    // A bare code the table does not know: show it loudly, flagged — never a
    // guessed name (AC4/AC5).
    return {
      name: JURISDICTION_UNMAPPED_NAME,
      code: value,
      label: `${JURISDICTION_UNMAPPED_NAME} (${value})`,
      known: false,
      combines: null,
    };
  }
  // The value already names the place (fixture data) — pass through.
  return { name: value, code: null, label: value, known: true, combines: null };
}

/** The dossier's display title: the subject label with a trailing
 * " — `CODE`" rewritten to " — `Name (CODE)`" so `<title>`/H1 lead with the
 * place's name while the code stays secondary (AC1). A label that does not
 * embed its jurisdiction code passes through unchanged. */
export function dossierDisplayTitle(subjectLabel: string, jurisdiction: string): string {
  const suffix = ` — ${jurisdiction}`;
  return subjectLabel.endsWith(suffix)
    ? `${subjectLabel.slice(0, -suffix.length)} — ${displayJurisdiction(jurisdiction).label}`
    : subjectLabel;
}
