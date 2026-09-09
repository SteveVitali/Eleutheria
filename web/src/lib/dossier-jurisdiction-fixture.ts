// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * Jurisdiction-conditional dossier fixtures for France and Belgium (§43.8, §44;
 * SIG-PUB-017, P18.1/P18.2 Technopolice connectors). Each is a complete twelve-section
 * §39.2 dossier (so `validateDossier` passes), rendered in its own BCP-47 language
 * with localised section titles, and each carries a **public-employee name** row.
 *
 * The point of the fixtures is the publication gate: under FR-GDPR / BE-GDPR a
 * public-employee name is NOT publishable (`applyPublicationPolicy` withholds it),
 * whereas the US OKC dossier publishes the equivalent name. The build-time data path
 * (`pages/dossier/[slug].astro`) applies the gate, so the withholding is baked into
 * the static HTML — never a client-side decision.
 */

import { AS_OF, RULESET_VERSION } from "./fixtures";
import type { Dossier, Section } from "./dossier";

/** The twelve §39.2 sections in order, filled with minimal jurisdiction rows. */
function baseSections(officerLabel: string, originJurisdiction: string): Section[] {
  return [
    {
      section_id: "at_a_glance",
      rows: [
        { label: "Technology", value: "Automated licence-plate readers (ALPR)" },
        { label: "Lifecycle status", value: "Operational" },
      ],
    },
    {
      section_id: "what_is_deployed",
      rows: [{ label: "Device type", value: "Fixed ALPR cameras" }],
    },
    {
      section_id: "cost_and_expiry",
      rows: [{ label: "Contract value", value: null, note: "Not disclosed." }],
    },
    {
      section_id: "who_else_can_see",
      rows: [{ label: "Data-sharing partners", value: null, absence: "NOT_RESEARCHED" }],
    },
    {
      section_id: "configuration_and_retention",
      rows: [{ label: "Retention (days)", value: null, absence: "NO_EVIDENCE_FOUND" }],
    },
    { section_id: "usage", rows: [{ label: "Searches (windowed)", value: null }] },
    {
      section_id: "where_the_hardware_is",
      rows: [{ label: "Mapped devices", value: null, note: "A lower bound." }],
    },
    {
      section_id: "policy",
      rows: [{ label: "Legal basis", value: "National data-protection regime (GDPR)" }],
    },
    {
      // The public-employee-name row the publication gate acts on (SIG-PUB-017).
      section_id: "accountability_events",
      rows: [
        {
          label: officerLabel,
          value: "Cmdt. Jean Dupont",
          isPublicEmployeeName: true,
          originJurisdiction,
        },
      ],
    },
    {
      section_id: "timeline",
      rows: [{ label: "2026-05-01", value: "Prefectural order published" }],
    },
    { section_id: "what_we_dont_know" },
    {
      section_id: "how_we_know_this",
      rows: [{ label: "Sources", value: "Prefectural order, procurement notice" }],
    },
  ];
}

/** France (FR-GDPR): the signing officer's name is withheld under FR-GDPR. */
export const FR_DOSSIER: Dossier = {
  slug: "paris-alpr",
  subject_label: "Préfecture de police de Paris — déploiement LAPI",
  jurisdiction: "Paris, France",
  jurisdictionCode: "FR",
  lang: "fr",
  asOf: AS_OF,
  rulesetVersion: RULESET_VERSION,
  source_families: ["Arrêté préfectoral", "Avis de marché public (DECP)"],
  authorization: {
    approving_body: "Préfecture de police de Paris",
    vote: null,
    consent_agenda: null,
    public_comment: null,
    date: "2026-05-01",
  },
  termination: { auto_renews: false, notice_window_days: null, expiry_date: "2028-05-01" },
  legal_regime: {
    state_statute: "Code de la sécurité intérieure",
    local_ordinance: null,
    disclosure_duties: ["RGPD — droit d'accès", "CADA — communication des documents administratifs"],
  },
  gaps: [
    {
      label: "Partenaires de partage de données",
      kind: "NOT_RESEARCHED",
      subject_id: "org:prefpol-paris",
      predicate_id: "sharing_partners",
    },
  ],
  sections: baseSections("Agent signataire de l'arrêté", "FR"),
};

/** Belgium (BE-GDPR): the signing officer's name is withheld under BE-GDPR. */
export const BE_DOSSIER: Dossier = {
  slug: "brussels-alpr",
  subject_label: "Politiezone Brussel — ANPR-inzet",
  jurisdiction: "Brussel, België",
  jurisdictionCode: "BE",
  lang: "nl-BE",
  asOf: AS_OF,
  rulesetVersion: RULESET_VERSION,
  source_families: ["Politiereglement", "Overheidsopdracht (DECP)"],
  authorization: {
    approving_body: "Politiezone Brussel-Hoofdstad-Elsene",
    vote: null,
    consent_agenda: null,
    public_comment: null,
    date: "2026-05-01",
  },
  termination: { auto_renews: false, notice_window_days: null, expiry_date: "2028-05-01" },
  legal_regime: {
    state_statute: "Wet op het politieambt",
    local_ordinance: null,
    disclosure_duties: ["AVG — recht op inzage", "Openbaarheid van bestuur"],
  },
  gaps: [
    {
      label: "Partners voor gegevensdeling",
      kind: "NOT_RESEARCHED",
      subject_id: "org:pz-brussel",
      predicate_id: "sharing_partners",
    },
  ],
  sections: baseSections("Ondertekenende ambtenaar", "BE"),
};

/** The jurisdiction-conditional dossiers the shell statically generates. */
export const JURISDICTION_DOSSIERS: Dossier[] = [FR_DOSSIER, BE_DOSSIER];
