// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
/**
 * The committed `sig.entity-page/1` fixtures, split out of `entity-page.ts`
 * (P37.27 / GX-09b): the browser island imports the contract guards but must
 * never bundle fixture bytes — `demo_*` specimen ids and invented labels are
 * scan sentinels (ops/sentinels.toml `demo-marker`), so the fixtures live in
 * their own module that only the fixtures-mode data layer + tests import.
 */
import { withBase } from "./paths";
import {
  ENTITY_PAGE_SCHEMA,
  ER_DISCLOSURE,
  WITHHELD_RELATIONSHIPS_NOTICE,
} from "./entity-page";
import type { EntityLabelRow, EntityPageTwin } from "./entity-page";

// ---------------------------------------------------------------------------
// The committed fixtures (SIG-UI-036: invented, honest data — every key below
// is the invented-entity shape the real derivation produces; the A-10 fixture
// pair exercises the operator's answered decision verbatim: an auto-allowed
// agency renders its twin; an organisation outside the auto-allow registry
// renders the typed `not_yet_reviewed` state, never a silent absence).
//
// Path note (P35.65): the emitted artifact's `url`/`record_url` fields are
// root-absolute paths (policy.labels.entity_url → `/entity/<type>/<key>/`).
// The fixtures build those bytes through `withBase()` with a sans-slash
// argument — the pinned construction seam — so the containment check
// (check-root-absolute-paths.mjs) sees no new root-absolute literal while
// the runtime value stays byte-identical under the default root base.
// ---------------------------------------------------------------------------

/** The fixture mirror of `policy.labels.entity_url` — `<slug>--<hash>`
 * joined under `entity/<url_type>/`, through `withBase()`. */
function fixtureEntityUrl(urlType: string, slug: string, hash: string): string {
  return withBase(`entity/${urlType}/${slug}--${hash}/`);
}

/** Invented label-registry rows: one auto-allowed agency (keyed twin), one
 * allowed portal, and one organisation outside the auto-allow registry. */
export const ENTITY_LABEL_FIXTURES: EntityLabelRow[] = [
  {
    entity_id: "0190cafe-0000-7000-8000-0000000000a1",
    sig_id: "sig:agency:0190cafe-0000-7000-8000-0000000000a1",
    kind: "agency",
    url_type: "agency",
    label: "Acworth Police Department",
    descriptor: "Government body · usa-ga",
    label_basis: "source_name",
    label_source_id: "eff_data_driven",
    place_jkey: "usa-ga",
    slug: "acworth-police-department",
    hash: "4g2wm8q",
    url: fixtureEntityUrl("agency", "acworth-police-department", "4g2wm8q"),
    disambiguator: null,
    component_id: "comp-1",
    part8: "pass",
    subject_key: "agency:acworth-pd",
  },
  {
    entity_id: "0190cafe-0000-7000-8000-0000000000b2",
    sig_id: "sig:org:0190cafe-0000-7000-8000-0000000000b2",
    kind: "org",
    url_type: "org",
    label: "Vigilant Solutions (LEARN)",
    descriptor: "Organisation",
    label_basis: "source_name",
    label_source_id: "eff_data_driven",
    place_jkey: null,
    slug: "vigilant-solutions-learn",
    hash: "7xk3mrt",
    url: fixtureEntityUrl("org", "vigilant-solutions-learn", "7xk3mrt"),
    disambiguator: null,
    component_id: "comp-1",
    part8: "pass",
    subject_key: "organization:vigilant-solutions",
  },
  {
    entity_id: "0190cafe-0000-7000-8000-0000000000c3",
    sig_id: "sig:portal:0190cafe-0000-7000-8000-0000000000c3",
    kind: "portal",
    url_type: "portal",
    label: "Acworth PD transparency portal",
    descriptor: "Registry portal · usa-ga",
    label_basis: "source_title",
    label_source_id: "eyes_on_flock",
    place_jkey: "usa-ga",
    slug: "acworth-pd-transparency-portal",
    hash: "2rn6vqw",
    url: fixtureEntityUrl("portal", "acworth-pd-transparency-portal", "2rn6vqw"),
    disambiguator: null,
    component_id: "comp-1",
    part8: "pass",
    subject_key: "platform:acworth-pd-portal",
  },
  {
    // A-10 c: an organisation NOT matched by the registry auto-allow ADR —
    // no key is issued, the typed `not_yet_reviewed` state is the record.
    entity_id: "0190cafe-0000-7000-8000-0000000000d4",
    sig_id: "sig:org:0190cafe-0000-7000-8000-0000000000d4",
    kind: "org",
    url_type: "org",
    label: null,
    descriptor: "Organisation",
    label_basis: null,
    label_source_id: null,
    place_jkey: null,
    slug: null,
    hash: null,
    url: null,
    disambiguator: null,
    component_id: null,
    part8: "pass",
    subject_key: "organization:unverified-partner-llc",
    label_state: "not_yet_reviewed",
  },
  {
    // Contract B (P37.23 / GX-06b): a keyed procurement-record entity — the
    // E2 record wave's buyer/seller page surface.
    entity_id: "0190cafe-0000-7000-8000-0000000000e7",
    sig_id: "sig:contract:0190cafe-0000-7000-8000-0000000000e7",
    kind: "contract",
    url_type: "contract",
    label: "Acworth ALPR expansion contract",
    descriptor: "Procurement record · usa-ga",
    label_basis: "derived",
    label_source_id: "demo_permitted_portal",
    place_jkey: "usa-ga",
    slug: "acworth-alpr-expansion-contract",
    hash: "9p4kxwd",
    url: fixtureEntityUrl("contract", "acworth-alpr-expansion-contract", "9p4kxwd"),
    disambiguator: null,
    component_id: "comp-1",
    part8: "pass",
    subject_key: "contract:acworth-alpr-expansion-2020",
  },
  {
    // Contract B (P37.23 / GX-06b): a keyed legal-instrument entity — the
    // record wave's adopted-by surface; no place is recorded, so the map
    // snippet exercises its typed state.
    entity_id: "0190cafe-0000-7000-8000-0000000000f8",
    sig_id: "sig:policy:0190cafe-0000-7000-8000-0000000000f8",
    kind: "policy",
    url_type: "policy",
    label: "Acworth surveillance oversight ordinance 2020-14",
    descriptor: "Policy or ordinance",
    label_basis: "source_title",
    label_source_id: "okc_council_minutes",
    place_jkey: null,
    slug: "acworth-surveillance-oversight-ordinance-2020-14",
    hash: "5t8mvjq",
    url: fixtureEntityUrl(
      "policy",
      "acworth-surveillance-oversight-ordinance-2020-14",
      "5t8mvjq",
    ),
    disambiguator: null,
    component_id: "comp-1",
    part8: "pass",
    subject_key: "ordinance:acworth-2020-14",
  },
  {
    // P37.27 (GX-09b): the supply/access overviews' buyer node — a keyed
    // agency whose twin the explorer's expansion fetch resolves (the
    // overview fixture named the page before the twin existed).
    entity_id: "0190cafe-0000-7000-8000-0000000000a9",
    sig_id: "sig:agency:0190cafe-0000-7000-8000-0000000000a9",
    kind: "agency",
    url_type: "agency",
    label: "Acme City Police Department",
    descriptor: "Government body · usa-ok",
    label_basis: "source_name",
    label_source_id: "okc_procurement",
    place_jkey: "usa-ok",
    slug: "acme-city-police",
    hash: "4g2wm8q",
    url: fixtureEntityUrl("agency", "acme-city-police", "4g2wm8q"),
    disambiguator: null,
    component_id: "comp-1",
    part8: "pass",
    subject_key: "agency:acme-city-pd",
  },
];

/** The published twin for the auto-allowed agency — relations both ways,
 * an access-kind edge marked historical, a degree-only fact, and the
 * withheld-counterparty notice (a partner org pending review). */
export const ENTITY_PAGE_TWIN_FIXTURE: EntityPageTwin = {
  schema: ENTITY_PAGE_SCHEMA,
  review_state: "published",
  key: "acworth-police-department--4g2wm8q",
  entity_id: "0190cafe-0000-7000-8000-0000000000a1",
  sig_id: "sig:agency:0190cafe-0000-7000-8000-0000000000a1",
  kind: "agency",
  url_type: "agency",
  url: fixtureEntityUrl("agency", "acworth-police-department", "4g2wm8q"),
  label: "Acworth Police Department",
  descriptor: "Government body · usa-ga",
  label_basis: "source_name",
  label_source_id: "eff_data_driven",
  place_jkey: "usa-ga",
  disambiguator: null,
  publication: "sig-release-2026.09",
  generated_at: "2026-09-01T00:00:00Z",
  compartment: "sig_graph",
  identifiers: [
    { scheme: "us.cgac.agency_code", value: "GA-ACWORTH-PD" },
    { scheme: "sig.connector.subject", value: "agency:acworth-pd" },
  ],
  summary: [
    {
      text: "1 recorded outbound relationship — configured sharing partner",
      value: 1,
      relation: "configured sharing partner",
      direction: "outbound",
      claim_ids: ["clm-apd-vigilant-1"],
    },
    {
      text: "3 recorded inbound relationships — camera operator",
      value: 3,
      relation: "camera operator",
      direction: "inbound",
      claim_ids: ["clm-cam-12", "clm-cam-34", "clm-cam-56"],
    },
  ],
  claims: [
    {
      predicate: "agency_name",
      relation: "agency name",
      envelope: {
        status: "resolved",
        support: "WEAKLY_SUPPORTED",
        agreement: "UNCONTESTED",
        currency: "CURRENT",
        rationale: null,
      },
      values: ["Acworth Police Department"],
      observed_at: "2020-01-28",
      date_kind: "observed",
      sources: [{ id: "eff_data_driven", name: "EFF Data Driven" }],
      claim_ids: ["clm-apd-name-1"],
    },
  ],
  relations: [
    {
      relation: "configured sharing partner",
      direction: "outbound",
      access_kind: "configured_access",
      count: 1,
      items: [
        {
          counterparty: {
            entity_id: "0190cafe-0000-7000-8000-0000000000b2",
            kind: "org",
            label: "Vigilant Solutions (LEARN)",
            label_basis: "source_name",
            url: fixtureEntityUrl("org", "vigilant-solutions-learn", "7xk3mrt"),
            key: "vigilant-solutions-learn--7xk3mrt",
          },
          relation: "configured sharing partner",
          role: "configured_sharing_partner",
          date: "2020-01-28",
          date_kind: "observed",
          currency: "HISTORICAL",
          status: "unresolved",
          support: "WEAKLY_SUPPORTED",
          agreement: "UNCONTESTED",
          sources: [{ id: "eff_data_driven", name: "EFF Data Driven" }],
          claim_ids: ["clm-apd-vigilant-1"],
          historical: true,
        },
      ],
      more: 0,
      claim_ids: ["clm-apd-vigilant-1"],
    },
    {
      relation: "camera operator",
      direction: "inbound",
      access_kind: null,
      count: 3,
      items: [
        {
          counterparty: {
            entity_id: "0190cafe-0000-7000-8000-0000000000e5",
            kind: "site",
            label: "surveillance camera in usa-ga",
            label_basis: "derived",
            url: null,
            key: null,
          },
          relation: "camera operator",
          role: "camera_operator",
          date: null,
          date_kind: "undated",
          currency: "UNDATED",
          status: null,
          support: "WEAKLY_SUPPORTED",
          agreement: null,
          sources: [{ id: "dot_511_ga", name: "Georgia 511" }],
          claim_ids: ["clm-cam-12"],
          historical: false,
        },
      ],
      more: 2,
      claim_ids: ["clm-cam-12", "clm-cam-34", "clm-cam-56"],
    },
  ],
  access: {
    // GX-07 (P37.21) — a 2-hop outbound closure over the fixture's
    // configured-access chain, per-hop evidence + party views intact.
    closures: [
      {
        direction: "outbound",
        question: "whose data this entity can reach",
        as_of: "2026-09-01",
        counts: { publishable: 1, historical: 0, speculative: 0 },
        path_count: 1,
        more: 0,
        paths: [
          {
            source: "0190cafe-0000-7000-8000-0000000000a1",
            target: "0190cafe-0000-7000-8000-0000000000f6",
            direction: "outbound",
            hop_count: 2,
            confidence: "probable",
            scope: "partner",
            temporal_status: "live",
            speculative: false,
            is_headline: true,
            rationale:
              "… can reach … via 2 hop(s); confidence is the path minimum; scope is the narrowest hop.",
            claim_ids: ["clm-apd-vigilant-1", "clm-vig-lookup-1"],
            source_party: {
              entity_id: "0190cafe-0000-7000-8000-0000000000a1",
              kind: "agency",
              label: "Acworth Police Department",
              label_basis: "source_name",
              url: fixtureEntityUrl("agency", "acworth-police-department", "4g2wm8q"),
              key: "acworth-police-department--4g2wm8q",
            },
            target_party: {
              entity_id: "0190cafe-0000-7000-8000-0000000000f6",
              kind: "portal",
              label: "Multi-state LEARN lookup pool",
              label_basis: "source_name",
              url: null,
              key: null,
            },
            hops: [
              {
                from_org: "0190cafe-0000-7000-8000-0000000000a1",
                to_org: "0190cafe-0000-7000-8000-0000000000b2",
                edge_label: "configured_access",
                scope: "partner",
                confidence: "probable",
                evidence: ["clm-apd-vigilant-1"],
                edge_id: "rel-fixture-1",
                asserted_by: "0190cafe-0000-7000-8000-0000000000a1",
                valid_from: null,
                valid_to: null,
                valid_from_kind: "unknown",
                valid_to_kind: "ongoing",
                from: {
                  entity_id: "0190cafe-0000-7000-8000-0000000000a1",
                  kind: "agency",
                  label: "Acworth Police Department",
                  label_basis: "source_name",
                  url: fixtureEntityUrl("agency", "acworth-police-department", "4g2wm8q"),
                  key: "acworth-police-department--4g2wm8q",
                },
                to: {
                  entity_id: "0190cafe-0000-7000-8000-0000000000b2",
                  kind: "org",
                  label: "Vigilant Solutions (LEARN)",
                  label_basis: "source_name",
                  url: fixtureEntityUrl("org", "vigilant-solutions-learn", "7xk3mrt"),
                  key: "vigilant-solutions-learn--7xk3mrt",
                },
                sources: [{ id: "eff_data_driven", name: "EFF Data Driven" }],
              },
              {
                from_org: "0190cafe-0000-7000-8000-0000000000b2",
                to_org: "0190cafe-0000-7000-8000-0000000000f6",
                edge_label: "configured_access",
                scope: "partner",
                confidence: "probable",
                evidence: ["clm-vig-lookup-1"],
                edge_id: "rel-fixture-2",
                asserted_by: "0190cafe-0000-7000-8000-0000000000b2",
                valid_from: null,
                valid_to: null,
                valid_from_kind: "unknown",
                valid_to_kind: "ongoing",
                from: {
                  entity_id: "0190cafe-0000-7000-8000-0000000000b2",
                  kind: "org",
                  label: "Vigilant Solutions (LEARN)",
                  label_basis: "source_name",
                  url: fixtureEntityUrl("org", "vigilant-solutions-learn", "7xk3mrt"),
                  key: "vigilant-solutions-learn--7xk3mrt",
                },
                to: {
                  entity_id: "0190cafe-0000-7000-8000-0000000000f6",
                  kind: "portal",
                  label: "Multi-state LEARN lookup pool",
                  label_basis: "source_name",
                  url: null,
                  key: null,
                },
                sources: [{ id: "eff_data_driven", name: "EFF Data Driven" }],
              },
            ],
          },
        ],
      },
    ],
    degree_only: [
      {
        predicate: "sharing_partner_degree",
        counts: [851],
        sentences: ["Shared with 851 agencies — partners not named"],
        claim_ids: ["clm-apd-degree-1"],
        observed_at: "2020-01-28",
        date_kind: "observed",
        currency: "HISTORICAL",
        historical: true,
        sources: [{ id: "eff_data_driven", name: "EFF Data Driven" }],
      },
    ],
  },
  // Contract-B sections (P37.22) — populated: one materialized
  // contradiction, a stated date + record observations + first/last seen,
  // the related dossier/source/task, and the emitted download files.
  contradictions: [
    {
      kind: "contradiction",
      contradiction_id: "contra-fixture-1",
      predicate: "configured_sharing_partner",
      relation: "configured sharing partner",
      type: "value_conflict",
      status: "open",
      severity: "moderate",
      claim_ids: ["clm-apd-vigilant-1", "clm-apd-vigilant-2"],
      sources: [{ id: "eff_data_driven", name: "EFF Data Driven" }],
    },
  ],
  timeline: [
    {
      kind: "stated",
      date: "2020-01-28",
      date_kind: "observed",
      label: "posted date",
      predicate: "posted_date",
      claim_ids: ["clm-apd-posted-1"],
      sources: [{ id: "eff_data_driven", name: "EFF Data Driven" }],
    },
    {
      kind: "observed",
      date: "2020-01-28",
      date_kind: "observed",
      label: "configured sharing partner — Vigilant Solutions (LEARN)",
      predicate: "configured_sharing_partner",
      claim_ids: ["clm-apd-vigilant-1"],
      sources: [{ id: "eff_data_driven", name: "EFF Data Driven" }],
    },
    {
      kind: "first_seen",
      date: "2020-01-28",
      date_kind: "observed",
      label: "first seen — EFF Data Driven",
      predicate: null,
      claim_ids: ["clm-apd-vigilant-1"],
      sources: [{ id: "eff_data_driven", name: "EFF Data Driven" }],
    },
    {
      kind: "observed",
      date: null,
      date_kind: "undated",
      label: "camera operator — surveillance camera in usa-ga",
      predicate: "camera_operator",
      claim_ids: ["clm-cam-12"],
      sources: [{ id: "dot_511_ga", name: "Georgia 511" }],
    },
  ],
  related: {
    dossiers: [
      {
        jkey: "usa-ga",
        slug_path: "usa/ga",
        name: "Georgia",
        level: "admin1",
        url: withBase("dossier/usa/ga/"),
      },
    ],
    sources: [
      { id: "eff_data_driven", name: "EFF Data Driven", url: withBase("sources/eff_data_driven/") },
      { id: "dot_511_ga", name: "Georgia 511", url: withBase("sources/dot_511_ga/") },
    ],
    tasks: [
      {
        task_id: "task-fixture-1",
        handle: "T-usa-ga-alpr-acworth-pd-q1c4",
        title: "Confirm the current sharing partner list",
        task_type: "verify_partner_list",
        status: "generated",
        url: withBase("task/T-usa-ga-alpr-acworth-pd-q1c4/"),
      },
    ],
    watch: [],
    documents: [
      {
        artifact_id: "art-fixture-1",
        title: "EFF Data Driven 2020 export",
        artifact_type: "dataset",
        source_id: "eff_data_driven",
        source_name: "EFF Data Driven",
        claim_ids: ["clm-apd-vigilant-1"],
      },
    ],
  },
  downloads: [
    {
      kind: "twin",
      format: "json",
      path: `entity/agency/acworth-police-department--4g2wm8q/index.sig_graph.json`,
      compartment: "sig_graph",
      label: "JSON twin (sig.entity-page/1)",
    },
    {
      kind: "relationships",
      format: "csv",
      path: `entity/agency/acworth-police-department--4g2wm8q/relationships.sig_graph.csv`,
      compartment: "sig_graph",
      label: "Relationships CSV",
    },
    {
      kind: "relationships",
      format: "json",
      path: `entity/agency/acworth-police-department--4g2wm8q/relationships.sig_graph.json`,
      compartment: "sig_graph",
      label: "Relationships JSON",
    },
    {
      kind: "statements",
      format: "jsonl",
      path: `entity/agency/acworth-police-department--4g2wm8q/statements.sig_graph.jsonl`,
      compartment: "sig_graph",
      label: "Statements (sig.statement/1)",
    },
  ],
  cite: {
    publication: "sig-release-2026.09",
    url: fixtureEntityUrl("agency", "acworth-police-department", "4g2wm8q"),
    record_url: withBase(
      "r/sig-release-2026.09/c/sig_graph/entity/agency/0190cafe-0000-7000-8000-0000000000a1/",
    ),
    sig_id: "sig:agency:0190cafe-0000-7000-8000-0000000000a1",
  },
  withheld_notice: WITHHELD_RELATIONSHIPS_NOTICE,
  er_disclosure: ER_DISCLOSURE,
};

/** The published twin for the contract-B procurement record (P37.23 /
 *  GX-06b) — buyer + seller relations to the wave-A entities, stated
 *  posted/signed dates, an envelope conflict on the contract value, and
 *  the recorded place drawing the map snippet. */
export const ENTITY_PAGE_TWIN_CONTRACT_FIXTURE: EntityPageTwin = {
  schema: ENTITY_PAGE_SCHEMA,
  review_state: "published",
  key: "acworth-alpr-expansion-contract--9p4kxwd",
  entity_id: "0190cafe-0000-7000-8000-0000000000e7",
  sig_id: "sig:contract:0190cafe-0000-7000-8000-0000000000e7",
  kind: "contract",
  url_type: "contract",
  url: fixtureEntityUrl("contract", "acworth-alpr-expansion-contract", "9p4kxwd"),
  label: "Acworth ALPR expansion contract",
  descriptor: "Procurement record · usa-ga",
  label_basis: "derived",
  label_source_id: "demo_permitted_portal",
  place_jkey: "usa-ga",
  disambiguator: null,
  publication: "sig-release-2026.09",
  generated_at: "2026-09-01T00:00:00Z",
  compartment: "sig_graph",
  identifiers: [
    { scheme: "sig.connector.subject", value: "contract:acworth-alpr-expansion-2020" },
  ],
  summary: [
    {
      text: "2 recorded outbound relationships — contract parties",
      value: 2,
      relation: "contract parties",
      direction: "outbound",
      claim_ids: ["clm-contract-buyer-1", "clm-contract-seller-1"],
    },
  ],
  claims: [
    {
      predicate: "contract_value",
      relation: "contract value",
      envelope: {
        status: "resolved",
        support: "WEAKLY_SUPPORTED",
        agreement: "CONTESTED",
        currency: "CURRENT",
        rationale: null,
      },
      values: ["$412,700", "$421,700"],
      observed_at: "2020-01-28",
      date_kind: "observed",
      sources: [{ id: "demo_permitted_portal", name: "Demo permitted portal" }],
      claim_ids: ["clm-contract-value-1", "clm-contract-value-2"],
    },
  ],
  relations: [
    {
      relation: "contract buyer",
      direction: "outbound",
      access_kind: null,
      count: 1,
      items: [
        {
          counterparty: {
            entity_id: "0190cafe-0000-7000-8000-0000000000a1",
            kind: "agency",
            label: "Acworth Police Department",
            label_basis: "source_name",
            url: fixtureEntityUrl("agency", "acworth-police-department", "4g2wm8q"),
            key: "acworth-police-department--4g2wm8q",
          },
          relation: "contract buyer",
          role: "buyer",
          date: "2020-01-28",
          date_kind: "observed",
          currency: "CURRENT",
          status: "resolved",
          support: "WEAKLY_SUPPORTED",
          agreement: "UNCONTESTED",
          sources: [{ id: "demo_permitted_portal", name: "Demo permitted portal" }],
          claim_ids: ["clm-contract-buyer-1"],
          historical: false,
        },
      ],
      more: 0,
      claim_ids: ["clm-contract-buyer-1"],
    },
    {
      relation: "contract seller",
      direction: "outbound",
      access_kind: null,
      count: 1,
      items: [
        {
          counterparty: {
            entity_id: "0190cafe-0000-7000-8000-0000000000b2",
            kind: "org",
            label: "Vigilant Solutions (LEARN)",
            label_basis: "source_name",
            url: fixtureEntityUrl("org", "vigilant-solutions-learn", "7xk3mrt"),
            key: "vigilant-solutions-learn--7xk3mrt",
          },
          relation: "contract seller",
          role: "seller",
          date: "2020-01-28",
          date_kind: "observed",
          currency: "CURRENT",
          status: "resolved",
          support: "WEAKLY_SUPPORTED",
          agreement: "UNCONTESTED",
          sources: [{ id: "demo_permitted_portal", name: "Demo permitted portal" }],
          claim_ids: ["clm-contract-seller-1"],
          historical: false,
        },
      ],
      more: 0,
      claim_ids: ["clm-contract-seller-1"],
    },
  ],
  access: { closures: [], degree_only: [] },
  contradictions: [
    {
      kind: "envelope_conflict",
      contradiction_id: null,
      predicate: "contract_value",
      relation: "contract value",
      type: "value_conflict",
      status: "open",
      severity: null,
      agreement: "CONTESTED",
      claim_ids: ["clm-contract-value-1", "clm-contract-value-2"],
      sources: [{ id: "demo_permitted_portal", name: "Demo permitted portal" }],
    },
  ],
  timeline: [
    {
      kind: "stated",
      date: "2020-01-15",
      date_kind: "observed",
      label: "posted date",
      predicate: "posted_date",
      claim_ids: ["clm-contract-posted-1"],
      sources: [{ id: "demo_permitted_portal", name: "Demo permitted portal" }],
    },
    {
      kind: "stated",
      date: "2020-01-28",
      date_kind: "observed",
      label: "signed date",
      predicate: "signed_date",
      claim_ids: ["clm-contract-signed-1"],
      sources: [{ id: "demo_permitted_portal", name: "Demo permitted portal" }],
    },
    {
      kind: "first_seen",
      date: "2020-02-03",
      date_kind: "observed",
      label: "first seen — Demo permitted portal",
      predicate: null,
      claim_ids: ["clm-contract-buyer-1"],
      sources: [{ id: "demo_permitted_portal", name: "Demo permitted portal" }],
    },
    {
      kind: "observed",
      date: null,
      date_kind: "undated",
      label: "renewal option — undated",
      predicate: "renewal_option",
      claim_ids: ["clm-contract-renewal-1"],
      sources: [{ id: "demo_permitted_portal", name: "Demo permitted portal" }],
    },
  ],
  related: {
    dossiers: [
      {
        jkey: "usa-ga",
        slug_path: "usa/ga",
        name: "Georgia",
        level: "admin1",
        url: withBase("dossier/usa/ga/"),
      },
    ],
    sources: [
      {
        id: "demo_permitted_portal",
        name: "Demo permitted portal",
        url: withBase("sources/demo_permitted_portal/"),
      },
    ],
    tasks: [
      {
        task_id: "task-fixture-2",
        handle: "T-usa-ga-alpr-contract-value-q2f7",
        title: "Reconcile the two recorded contract values",
        task_type: "reconcile_values",
        status: "generated",
        url: null,
      },
    ],
    watch: [],
    documents: [
      {
        artifact_id: "art-fixture-2",
        title: "Acworth procurement portal — executed contract PDF",
        artifact_type: "contract",
        source_id: "demo_permitted_portal",
        source_name: "Demo permitted portal",
        claim_ids: ["clm-contract-signed-1"],
      },
    ],
  },
  downloads: [
    {
      kind: "twin",
      format: "json",
      path: `entity/contract/acworth-alpr-expansion-contract--9p4kxwd/index.sig_graph.json`,
      compartment: "sig_graph",
      label: "JSON twin (sig.entity-page/1)",
    },
    {
      kind: "relationships",
      format: "csv",
      path: `entity/contract/acworth-alpr-expansion-contract--9p4kxwd/relationships.sig_graph.csv`,
      compartment: "sig_graph",
      label: "Relationships CSV",
    },
    {
      kind: "relationships",
      format: "json",
      path: `entity/contract/acworth-alpr-expansion-contract--9p4kxwd/relationships.sig_graph.json`,
      compartment: "sig_graph",
      label: "Relationships JSON",
    },
    {
      kind: "statements",
      format: "jsonl",
      path: `entity/contract/acworth-alpr-expansion-contract--9p4kxwd/statements.sig_graph.jsonl`,
      compartment: "sig_graph",
      label: "Statements (sig.statement/1)",
    },
  ],
  cite: {
    publication: "sig-release-2026.09",
    url: fixtureEntityUrl("contract", "acworth-alpr-expansion-contract", "9p4kxwd"),
    record_url: withBase(
      "r/sig-release-2026.09/c/sig_graph/entity/contract/0190cafe-0000-7000-8000-0000000000e7/",
    ),
    sig_id: "sig:contract:0190cafe-0000-7000-8000-0000000000e7",
  },
  withheld_notice: null,
  er_disclosure: ER_DISCLOSURE,
};

/** The published twin for the contract-B legal instrument (P37.23 /
 *  GX-06b) — the adopted-by inbound relation, stated ordinance dates and
 *  the typed "location not recorded" map posture (no place is recorded). */
export const ENTITY_PAGE_TWIN_POLICY_FIXTURE: EntityPageTwin = {
  schema: ENTITY_PAGE_SCHEMA,
  review_state: "published",
  key: "acworth-surveillance-oversight-ordinance-2020-14--5t8mvjq",
  entity_id: "0190cafe-0000-7000-8000-0000000000f8",
  sig_id: "sig:policy:0190cafe-0000-7000-8000-0000000000f8",
  kind: "policy",
  url_type: "policy",
  url: fixtureEntityUrl(
    "policy",
    "acworth-surveillance-oversight-ordinance-2020-14",
    "5t8mvjq",
  ),
  label: "Acworth surveillance oversight ordinance 2020-14",
  descriptor: "Policy or ordinance",
  label_basis: "source_title",
  label_source_id: "okc_council_minutes",
  place_jkey: null,
  disambiguator: null,
  publication: "sig-release-2026.09",
  generated_at: "2026-09-01T00:00:00Z",
  compartment: "sig_graph",
  identifiers: [
    { scheme: "sig.connector.subject", value: "ordinance:acworth-2020-14" },
  ],
  summary: [
    {
      text: "1 recorded inbound relationship — adopted by",
      value: 1,
      relation: "adopted by",
      direction: "inbound",
      claim_ids: ["clm-ordinance-adopted-1"],
    },
  ],
  claims: [
    {
      predicate: "effective_date",
      relation: "effective date",
      envelope: {
        status: "resolved",
        support: "WEAKLY_SUPPORTED",
        agreement: "UNCONTESTED",
        currency: "CURRENT",
        rationale: null,
      },
      values: ["2020-04-01"],
      observed_at: "2020-03-10",
      date_kind: "observed",
      sources: [{ id: "okc_council_minutes", name: "OKC council minutes" }],
      claim_ids: ["clm-ordinance-effective-1"],
    },
  ],
  relations: [
    {
      relation: "adopted by",
      direction: "inbound",
      access_kind: null,
      count: 1,
      items: [
        {
          counterparty: {
            entity_id: "0190cafe-0000-7000-8000-0000000000a1",
            kind: "agency",
            label: "Acworth Police Department",
            label_basis: "source_name",
            url: fixtureEntityUrl("agency", "acworth-police-department", "4g2wm8q"),
            key: "acworth-police-department--4g2wm8q",
          },
          relation: "adopted by",
          role: "adopting_body",
          date: "2020-03-10",
          date_kind: "observed",
          currency: "CURRENT",
          status: "resolved",
          support: "WEAKLY_SUPPORTED",
          agreement: "UNCONTESTED",
          sources: [{ id: "okc_council_minutes", name: "OKC council minutes" }],
          claim_ids: ["clm-ordinance-adopted-1"],
          historical: false,
        },
      ],
      more: 0,
      claim_ids: ["clm-ordinance-adopted-1"],
    },
  ],
  access: { closures: [], degree_only: [] },
  contradictions: [],
  timeline: [
    {
      kind: "stated",
      date: "2020-03-10",
      date_kind: "observed",
      label: "adopted date",
      predicate: "adopted_date",
      claim_ids: ["clm-ordinance-adopted-1"],
      sources: [{ id: "okc_council_minutes", name: "OKC council minutes" }],
    },
    {
      kind: "stated",
      date: "2020-04-01",
      date_kind: "observed",
      label: "effective date",
      predicate: "effective_date",
      claim_ids: ["clm-ordinance-effective-1"],
      sources: [{ id: "okc_council_minutes", name: "OKC council minutes" }],
    },
    {
      kind: "last_seen",
      date: "2020-03-10",
      date_kind: "observed",
      label: "last seen — OKC council minutes",
      predicate: null,
      claim_ids: ["clm-ordinance-effective-1"],
      sources: [{ id: "okc_council_minutes", name: "OKC council minutes" }],
    },
  ],
  related: {
    dossiers: [],
    sources: [
      {
        id: "okc_council_minutes",
        name: "OKC council minutes",
        url: withBase("sources/okc_council_minutes/"),
      },
    ],
    tasks: [],
    watch: [],
    documents: [
      {
        artifact_id: "art-fixture-3",
        title: "Council minutes 2020-03-10 — ordinance 2020-14",
        artifact_type: "minutes",
        source_id: "okc_council_minutes",
        source_name: "OKC council minutes",
        claim_ids: ["clm-ordinance-adopted-1"],
      },
    ],
  },
  downloads: [
    {
      kind: "twin",
      format: "json",
      path: `entity/policy/acworth-surveillance-oversight-ordinance-2020-14--5t8mvjq/index.sig_graph.json`,
      compartment: "sig_graph",
      label: "JSON twin (sig.entity-page/1)",
    },
    {
      kind: "relationships",
      format: "csv",
      path: `entity/policy/acworth-surveillance-oversight-ordinance-2020-14--5t8mvjq/relationships.sig_graph.csv`,
      compartment: "sig_graph",
      label: "Relationships CSV",
    },
    {
      kind: "relationships",
      format: "json",
      path: `entity/policy/acworth-surveillance-oversight-ordinance-2020-14--5t8mvjq/relationships.sig_graph.json`,
      compartment: "sig_graph",
      label: "Relationships JSON",
    },
    {
      kind: "statements",
      format: "jsonl",
      path: `entity/policy/acworth-surveillance-oversight-ordinance-2020-14--5t8mvjq/statements.sig_graph.jsonl`,
      compartment: "sig_graph",
      label: "Statements (sig.statement/1)",
    },
  ],
  cite: {
    publication: "sig-release-2026.09",
    url: fixtureEntityUrl(
      "policy",
      "acworth-surveillance-oversight-ordinance-2020-14",
      "5t8mvjq",
    ),
    record_url: withBase(
      "r/sig-release-2026.09/c/sig_graph/entity/policy/0190cafe-0000-7000-8000-0000000000f8/",
    ),
    sig_id: "sig:policy:0190cafe-0000-7000-8000-0000000000f8",
  },
  withheld_notice: null,
  er_disclosure: ER_DISCLOSURE,
};

/** The committed twin set the fixtures-mode data layer serves, keyed by
 * `<url_type>/<key>`. */
/**
 * P37.27 (GX-09b) — the Acme City PD twin the explorer's expansion fetches:
 * two vendors recorded selling to it (inbound) and one configured sharing
 * partner (outbound, historical). Relations keep the full H-2 field set so
 * the expanded ego edges carry the same facts as overview edges.
 */
export const ENTITY_PAGE_TWIN_ACME_FIXTURE: EntityPageTwin = {
  schema: ENTITY_PAGE_SCHEMA,
  review_state: "published",
  key: "acme-city-police--4g2wm8q",
  entity_id: "0190cafe-0000-7000-8000-0000000000a9",
  sig_id: "sig:agency:0190cafe-0000-7000-8000-0000000000a9",
  kind: "agency",
  url_type: "agency",
  url: fixtureEntityUrl("agency", "acme-city-police", "4g2wm8q"),
  label: "Acme City Police Department",
  descriptor: "Government body · usa-ok",
  label_basis: "source_name",
  label_source_id: "okc_procurement",
  place_jkey: "usa-ok",
  disambiguator: null,
  publication: "sig-release-2026.09",
  generated_at: "2026-09-01T00:00:00Z",
  compartment: "sig_graph",
  identifiers: [
    { scheme: "sig.connector.subject", value: "agency:acme-city-pd" },
  ],
  summary: [
    {
      text: "2 recorded inbound relationships — sells to",
      value: 2,
      relation: "sells to",
      direction: "inbound",
      claim_ids: ["clm-acme-vigilant-1", "clm-acme-meridian-1"],
    },
  ],
  claims: [],
  relations: [
    {
      relation: "sells to",
      direction: "inbound",
      access_kind: null,
      count: 2,
      items: [
        {
          counterparty: {
            entity_id: "0190cafe-0000-7000-8000-0000000000b2",
            kind: "org",
            label: "Vigilant Solutions (LEARN)",
            label_basis: "source_name",
            url: fixtureEntityUrl("org", "vigilant-solutions-learn", "7xk3mrt"),
            key: "vigilant-solutions-learn--7xk3mrt",
          },
          relation: "sells to",
          role: "vendor",
          date: "2020-01-28",
          date_kind: "observed",
          currency: "STALE",
          status: null,
          support: "WEAKLY_SUPPORTED",
          agreement: null,
          sources: [{ id: "okc_procurement", name: "OKC procurement" }],
          claim_ids: ["clm-acme-vigilant-1"],
          historical: true,
        },
        {
          counterparty: {
            kind: "org",
            label: "Meridian Surveillance LLC",
            literal: true,
          },
          relation: "sells to",
          role: "vendor",
          date: null,
          date_kind: "undated",
          currency: "UNDATED",
          status: null,
          support: "WEAKLY_SUPPORTED",
          agreement: null,
          sources: [{ id: "okc_procurement", name: "OKC procurement" }],
          claim_ids: ["clm-acme-meridian-1"],
          historical: false,
        },
      ],
      more: 0,
      claim_ids: ["clm-acme-vigilant-1", "clm-acme-meridian-1"],
    },
    {
      relation: "configured access to",
      direction: "outbound",
      access_kind: "configured_access",
      count: 1,
      items: [
        {
          counterparty: {
            entity_id: "0190cafe-0000-7000-8000-0000000000b2",
            kind: "org",
            label: "Vigilant Solutions (LEARN)",
            label_basis: "source_name",
            url: fixtureEntityUrl("org", "vigilant-solutions-learn", "7xk3mrt"),
            key: "vigilant-solutions-learn--7xk3mrt",
          },
          relation: "configured access to",
          role: "configured_sharing_partner",
          date: "2020-01-28",
          date_kind: "observed",
          currency: "HISTORICAL",
          status: "unresolved",
          support: "WEAKLY_SUPPORTED",
          agreement: null,
          sources: [{ id: "eff_data_driven", name: "EFF Data Driven" }],
          claim_ids: ["clm-acme-access-1"],
          historical: true,
        },
      ],
      more: 0,
      claim_ids: ["clm-acme-access-1"],
    },
  ],
  access: { closures: [], degree_only: [] },
  contradictions: [],
  timeline: [],
  related: { dossiers: [], sources: [], tasks: [], watch: [], documents: [] },
  downloads: [
    {
      kind: "twin",
      format: "json",
      path: "index.sig_graph.json",
      compartment: "sig_graph",
      label: "Entity record (JSON)",
    },
  ],
  cite: {
    publication: "sig-release-2026.09",
    url: null,
    record_url: null,
    sig_id: "sig:agency:0190cafe-0000-7000-8000-0000000000a9",
  },
  withheld_notice: null,
  er_disclosure: ER_DISCLOSURE,
};

export const ENTITY_PAGE_FIXTURES: Record<string, EntityPageTwin> = {
  "agency/acworth-police-department--4g2wm8q": ENTITY_PAGE_TWIN_FIXTURE,
  "agency/acme-city-police--4g2wm8q": ENTITY_PAGE_TWIN_ACME_FIXTURE,
  "contract/acworth-alpr-expansion-contract--9p4kxwd":
    ENTITY_PAGE_TWIN_CONTRACT_FIXTURE,
  "policy/acworth-surveillance-oversight-ordinance-2020-14--5t8mvjq":
    ENTITY_PAGE_TWIN_POLICY_FIXTURE,
};
