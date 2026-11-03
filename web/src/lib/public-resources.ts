// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * P36.55 (UXR-06 / D3-Q4 [B-27] = yes): the neutral 'Other public resources'
 * block every dossier and the About page carries. It is CONTENT-NEUTRAL by
 * the answered decision — it lists public resources a reader may also find
 * useful, each labelled "SIG does not endorse", and it NEVER carries
 * avoidance routing or plate lookups: helping a reader evade a camera or
 * look a plate up is exactly what the decision excludes.
 *
 * The list is deliberately small and static — the K14/C5 peer set — and a
 * unit test (`public-resources.test.ts`) pins the guard so a future entry
 * can never turn the block into a lookup tool.
 */

export interface PublicResource {
  /** The resource's display name. */
  name: string;
  /** What it tells the reader (one clause — the K14 framing). */
  tells: string;
  /** The upstream URL (rel="external" at render). */
  url: string;
}

export const PUBLIC_RESOURCES: readonly PublicResource[] = [
  {
    name: "Atlas of Surveillance",
    tells: "which agencies adopted which technologies",
    url: "https://atlasofsurveillance.org/",
  },
  {
    name: "Eyes on Flock",
    tells: "what Flock's own portal says a deployment does",
    url: "https://eyesonflock.com/",
  },
  {
    name: "DeFlock",
    tells: "where licence-plate cameras are mapped",
    url: "https://deflock.me/",
  },
  {
    name: "ACLU — Community Control Over Police Surveillance",
    tells: "the model ordinance toolkit for local rules",
    url: "https://www.aclu.org/issues/privacy-technology/surveillance-technologies/community-control-over-police-surveillance",
  },
  {
    name: "alpr.watch",
    tells: "when ALPR items appear on public agendas",
    url: "https://alpr.watch/",
  },
];

/**
 * The exclusion vocabulary the answered decision fixes (D3-Q4 [B-27]): an
 * entry matching any of these kinds is an avoidance/lookup tool and must
 * never appear in the block. Enforced by the unit test — the data carries
 * no `kind` field at all so the block cannot grow one silently.
 */
export const EXCLUDED_RESOURCE_KINDS = ["avoidance_routing", "plate_lookup"] as const;

// ---------------------------------------------------------------------------
// D-K7-3 — official agenda portals, always.
// ---------------------------------------------------------------------------

export interface AgendaPortal {
  /** The portal's label (official body + platform). */
  label: string;
  /** The official portal URL — an agency/legislative host, never a vendor. */
  url: string;
}

/**
 * The official agenda portals registered per place (D-K7-3: "link to
 * official agenda portals always" — peer services stay behind C5's link
 * policy and never appear here). Keyed by jurisdiction jkey first and slug
 * path second so a pre-keyed dossier still resolves.
 */
export const AGENDA_PORTALS: Readonly<Record<string, AgendaPortal>> = {
  "us.census.geoid.place:4064000": {
    label: "Oklahoma City public meeting portal",
    url: "https://oklahomacityok.civicclerk.com/",
  },
  "us.census.geoid.county:40109": {
    label: "Oklahoma County public meeting portal",
    url: "https://oklahomacounty.oklegistar.com/",
  },
  "iso3166-2:US-OK": {
    label: "Oklahoma Legislature — official session records",
    url: "https://www.oklegislature.gov/",
  },
  "us.census.geoid.place:4055000": {
    label: "City of Norman public meeting portal",
    url: "https://norman-ok.municodemeetings.com/",
  },
  "us.census.geoid.county:48201": {
    label: "Harris County public meeting portal",
    url: "https://harriscountytx.new.swagit.com/",
  },
  "iso3166-2:US-TX": {
    label: "Texas Legislature Online — official records",
    url: "https://capitol.texas.gov/",
  },
  "oklahoma-city": {
    label: "Oklahoma City public meeting portal",
    url: "https://oklahomacityok.civicclerk.com/",
  },
};

/** The official agenda portal for a dossier — jkey first, slug fallback. */
export function agendaPortalFor(dossier: {
  jurisdiction_key?: string | null;
  slug: string;
}): AgendaPortal | null {
  if (dossier.jurisdiction_key && dossier.jurisdiction_key in AGENDA_PORTALS) {
    return AGENDA_PORTALS[dossier.jurisdiction_key]!;
  }
  return AGENDA_PORTALS[dossier.slug] ?? null;
}
