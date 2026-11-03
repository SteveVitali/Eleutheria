// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * P36.59 (K7 WX-04a) — the committed `sig/watch/2` fixture envelope the
 * fixtures-mode build renders. It exercises every acceptance surface:
 *
 *   - all six §5.2 kinds (`renewal_deadline`, `contract_expiry`,
 *     `solicitation_deadline`, `agenda_item`, `legislative_action`,
 *     `grant_period_end`) with their `date_kind`/`date_certainty` pairs —
 *     including an `upper_bound` expiry that must never label "deadline";
 *   - a contested item (`≠` marker everywhere), an item citing research
 *     tasks, evidence links with `full_url` / `host_only` /
 *     `no_upstream_url_recorded` upstream forms;
 *   - places across the keyed tree (Oklahoma City place → county →
 *     Oklahoma → United States, Harris County → Texas, Canada) plus an
 *     `unplaced` item;
 *   - a monitored-but-empty place (Cleveland County → the `none_found`
 *     cause) and a not-monitored place (Germany → `not_monitored`);
 *   - >50 generated grant items so the `/watch/page/2/` +
 *     `/watch/place/usa/page/2/` + facet pagination routes mint for real
 *     (K9 §6.1).
 *
 * Dates are fixed to the fixture as-of (2026-09-22) — never wall-clock.
 */

import { AS_OF } from "./fixtures";
import type { WatchEnvelopeV2, WatchItemV2 } from "./watch-v2";

const GENERATED = `${AS_OF.as_of_world}T00:00:00Z`;

const CHAIN_OKC = [
  "iso3166-1:US",
  "iso3166-2:US-OK",
  "us.census.geoid.county:40109",
  "us.census.geoid.place:4064000",
];
const CHAIN_OK = ["iso3166-1:US", "iso3166-2:US-OK"];
const CHAIN_US = ["iso3166-1:US"];
const CHAIN_HARRIS = [
  "iso3166-1:US",
  "iso3166-2:US-TX",
  "us.census.geoid.county:48201",
];

const item = (row: WatchItemV2): WatchItemV2 => ({ schema: "sig.watch-item/1", ...row });

const ITEMS: WatchItemV2[] = [
  item({
    handle: "W-us-ok-oklahoma-city-4064000-renewal-c100-ab12",
    title: "Oklahoma City Council: contract C-100 renewal decision — auto-renews without action by 2027-01-02",
    kind: "renewal_deadline",
    date: "2027-01-02", // future-ok: real-world: recorded decision date
    date_kind: "notice_deadline",
    date_certainty: "derived",
    timeline: [
      { kind: "signed", date: "2024-04-02", claim_id: "cl-c100-signed" },
      { kind: "period_end", date: "2027-04-02", claim_id: "cl-c100-end" },
    ],
    place: { key: "us.census.geoid.place:4064000", chain: CHAIN_OKC, check: "placed" },
    body: "Oklahoma City Council",
    subjects: ["contract:okc_contracts:tenant:okc:C-100"],
    technology: [{ id: "alpr", label: "automated licence plate readers" }],
    vendor: [{ id: "flock_safety", label: "Flock Safety" }],
    status: "upcoming",
    what_you_can_do:
      "The auto-renewal is decided by Oklahoma City Council: if no action is taken by the listed date, the contract renews by default. The body's meeting agendas and minutes are public, and most bodies accept written comment before the meeting at which the item is heard.",
    evidence: [
      {
        claim_id: "cl-c100-end",
        predicate: "end_date",
        source_id: "okc_contracts",
        artifact_ids: ["art-c100"],
        upstream: {
          status: "full_url",
          url: "https://www.okc.gov/contracts/C-100.pdf",
          host: "www.okc.gov",
        },
      },
      {
        claim_id: "cl-c100-autorenew",
        predicate: "auto_renews",
        source_id: "okc_contracts",
        artifact_ids: [],
        upstream: { status: "no_upstream_url_recorded" },
      },
    ],
    contested: true,
    tasks: [{ task_id: "T-us-ok-contract-renewal-terms-9f2k", task_type: "contract_expiring", status: "open" }],
    first_seen: "2026-08-14",
    last_checked: GENERATED,
    source_ids: ["okc_contracts"],
    termination: { auto_renews: true, notice_window_days: 90, expiry_date: "2027-04-02" }, // future-ok: real-world: recorded contract expiry
  }),
  item({
    handle: "W-us-ok-expiry-rtcc-77cd",
    title: "Oklahoma City Council: contract R-77 — latest possible end 2026-11-30 (renewal terms not on record)",
    kind: "contract_expiry",
    date: "2026-11-30", // future-ok: recorded contract end_date
    date_kind: "expiry",
    date_certainty: "upper_bound",
    timeline: [{ kind: "signed", date: "2024-12-01", claim_id: "cl-r77-signed" }],
    place: { key: "us.census.geoid.county:40109", chain: CHAIN_OKC.slice(0, 3), check: "placed" },
    body: "Oklahoma City Council",
    subjects: ["contract:okc_contracts:tenant:okc:R-77"],
    technology: [{ id: "real_time_crime_center", label: "real-time crime centre" }],
    vendor: [],
    status: "upcoming",
    what_you_can_do:
      "The listed date is the contract's stated end — the real renewal terms are not on record, so the actual decision may come earlier. The contract's renewal clause can be requested from Oklahoma City Council under the jurisdiction's public-records law.",
    evidence: [
      {
        claim_id: "cl-r77-end",
        predicate: "end_date",
        source_id: "okc_contracts",
        artifact_ids: ["art-r77"],
        upstream: {
          status: "host_only",
          host: "data.okc.gov",
          path_sha256: "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        },
      },
    ],
    contested: false,
    tasks: [{ task_id: "T-us-ok-renewal-terms-unknown-41mn", task_type: "contract_expiring", status: "open" }],
    first_seen: "2026-09-01",
    last_checked: GENERATED,
    source_ids: ["okc_contracts"],
    termination: { auto_renews: null, notice_window_days: null, expiry_date: "2026-11-30" },
  }),
  item({
    handle: "W-us-solicitation-n9-cd34",
    title: "U.S. Customs and Border Protection: solicitation N-9 — responses due 2026-10-15 — (automated licence plate readers)",
    kind: "solicitation_deadline",
    date: "2026-10-15", // future-ok: recorded response_deadline
    date_kind: "response_deadline",
    date_certainty: "stated",
    timeline: [{ kind: "posted", date: "2026-09-18", claim_id: "cl-n9-posted" }],
    place: { key: "iso3166-1:US", chain: CHAIN_US, check: "placed" },
    body: "U.S. Customs and Border Protection",
    subjects: ["procurement_notice:sam_gov:fed:N-9"],
    technology: [{ id: "alpr", label: "automated licence plate readers" }],
    vendor: [],
    status: "upcoming",
    what_you_can_do:
      "The buyer accepts responses until the listed deadline. The notice itself carries the submission instructions and any pre-bid or comment dates.",
    evidence: [
      {
        claim_id: "cl-n9-deadline",
        predicate: "response_deadline",
        source_id: "sam_gov",
        artifact_ids: ["art-n9"],
        upstream: {
          status: "full_url",
          url: "https://sam.gov/opp/N-9/view",
          host: "sam.gov",
        },
      },
    ],
    contested: false,
    tasks: [],
    first_seen: "2026-09-18",
    last_checked: GENERATED,
    source_ids: ["sam_gov"],
  }),
  item({
    handle: "W-us-tx-harris-48201-agenda-cb-8k2q",
    title: "Harris County Commissioners Court: agenda item CB-4279 on 2026-10-06 — (contract notice)",
    kind: "agenda_item",
    date: "2026-10-06", // fixture meeting_date (pre-WX-02 shape)
    date_kind: "meeting",
    date_certainty: "stated",
    timeline: [{ kind: "meeting", date: "2026-10-06", claim_id: "cl-cb4279-meeting" }],
    place: { key: "us.census.geoid.county:48201", chain: CHAIN_HARRIS, check: "placed" },
    body: "Harris County Commissioners Court",
    subjects: ["agenda_item:legistar:harris_tx:CB-4279"],
    technology: [{ id: "contract_notice", label: "contract notice" }],
    vendor: [],
    status: "upcoming",
    what_you_can_do:
      "The listed body may act on this item at the listed meeting. The agenda documents and the body's public-comment rules are published by the body before the meeting.",
    evidence: [
      {
        claim_id: "cl-cb4279-meeting",
        predicate: "meeting_date",
        source_id: "legistar",
        artifact_ids: ["art-cb4279"],
        upstream: { status: "withheld_by_policy" },
      },
    ],
    contested: true,
    tasks: [],
    first_seen: "2026-09-20",
    last_checked: GENERATED,
    source_ids: ["legistar"],
  }),
  item({
    handle: "W-us-ok-bill-hb-1400-55aa",
    title: "Oklahoma Legislature: bill HB-1400 — engrossed (2026-09-19)",
    kind: "legislative_action",
    date: "2026-09-19",
    date_kind: "status_change",
    date_certainty: "stated",
    timeline: [{ kind: "status_change", date: "2026-09-19", claim_id: "cl-hb1400-status" }],
    place: { key: "iso3166-2:US-OK", chain: CHAIN_OK, check: "placed" },
    body: "Oklahoma Legislature",
    subjects: ["legislative_bill:openstates:ok:HB-1400"],
    technology: [{ id: "surveillance_oversight", label: "surveillance oversight" }],
    vendor: [],
    status: "recently_decided",
    what_you_can_do:
      "The bill's recorded status changed on the listed date. The legislature's own record links the current text, committee assignments and any scheduled hearing.",
    evidence: [
      {
        claim_id: "cl-hb1400-status",
        predicate: "bill_status_date",
        source_id: "openstates",
        artifact_ids: [],
        upstream: {
          status: "full_url",
          url: "https://openstates.org/ok/bills/2026/HB1400/",
          host: "openstates.org",
        },
      },
    ],
    contested: false,
    tasks: [],
    first_seen: "2026-09-19",
    last_checked: GENERATED,
    source_ids: ["openstates"],
  }),
  item({
    handle: "W-unplaced-grant-hsgp-21zz",
    title: "The awarding agency: funding period for HSGP-2026 ends 2026-12-31",
    kind: "grant_period_end",
    date: "2026-12-31", // future-ok: recorded funding period end
    date_kind: "period_end",
    date_certainty: "stated",
    timeline: [
      { kind: "period_start", date: "2026-01-01", claim_id: "cl-hsgp-period" },
      { kind: "period_end", date: "2026-12-31", claim_id: "cl-hsgp-period" },
    ],
    place: { key: null, chain: [], check: "unplaced" },
    body: "Federal Emergency Management Agency",
    subjects: ["funding_instrument:fema_hsgp_allocations:fed:HSGP-2026"],
    technology: [{ id: "surveillance_equipment", label: "surveillance equipment" }],
    vendor: [],
    status: "upcoming",
    what_you_can_do:
      "The recorded funding period ends on the listed date. The awarding agency's record carries the reporting and renewal terms.",
    evidence: [
      {
        claim_id: "cl-hsgp-period",
        predicate: "period",
        source_id: "fema_hsgp_allocations",
        artifact_ids: [],
        upstream: { status: "no_upstream_url_recorded" },
      },
    ],
    contested: false,
    tasks: [],
    first_seen: "2026-09-05",
    last_checked: GENERATED,
    source_ids: ["fema_hsgp_allocations"],
  }),
];

// >50 generated federal grant items so the real pagination routes mint
// (`/watch/page/2/`, `/watch/place/usa/page/2/`, the kind facet's page/2):
// K9 §6.1 — the fallback exists the moment a list tops 50 rows.
for (let i = 1; i <= 52; i += 1) {
  const n = String(i).padStart(2, "0");
  const month = ((i % 10) + 1).toString().padStart(2, "0");
  ITEMS.push(
    item({
      handle: `W-us-grant-g${n}-f${(i * 7) % 96}w`,
      title: `U.S. Department of Justice: funding period for JAG-${n} ends 2026-${month}-28`,
      kind: "grant_period_end",
      date: `2026-${month}-28`,
      date_kind: "period_end",
      date_certainty: "stated",
      place: { key: "iso3166-1:US", chain: CHAIN_US, check: "placed" },
      body: "U.S. Department of Justice",
      subjects: [`funding_instrument:usaspending:fed:JAG-${n}`],
      technology: [{ id: "surveillance_equipment", label: "surveillance equipment" }],
      vendor: [],
      status: i % 9 === 0 ? "recently_decided" : "upcoming",
      evidence: [
        {
          claim_id: `cl-jag-${n}-period`,
          predicate: "period",
          source_id: "usaspending",
          artifact_ids: [],
          upstream: {
            status: "full_url",
            url: `https://www.usaspending.gov/award/JAG-${n}`,
            host: "www.usaspending.gov",
          },
        },
      ],
      contested: false,
      tasks: [],
      first_seen: "2026-08-01",
      last_checked: GENERATED,
      source_ids: ["usaspending"],
    }),
  );
}

/** The `sig/watch/2` fixture envelope — items + the per-place coverage rows
 *  every dossier place gets (SIG-WATCH-004), plus a monitored-but-empty
 *  place (Cleveland County) for the `none_found` cause and a not-monitored
 *  place (Germany) for `not_monitored`. */
export const WATCH_V2_FIXTURE: WatchEnvelopeV2 = {
  schema: "sig/watch/2",
  as_of: AS_OF.as_of_world,
  generated_at: GENERATED,
  build: {
    ruleset: "watch-derivation/1",
    windows: {
      list_days: 90,
      recently_decided_days: 30,
      contract_horizon_days: 365,
      solicitation_from: "posted_date",
      basis:
        "K7 §5.2 windows — the design's declared inference pending operator decision D-K7-4 (never silently ratified)",
    },
    what_you_can_do_basis:
      "agent-drafted procedural templates pending operator sign-off (K7 §5.1; no position is ever recommended — W-P4/W-P5)",
  },
  coverage: {
    monitored: {
      tenant_jurisdictions: ["Cleveland County", "Harris County", "Oklahoma City"],
      tenants_registered: 3,
    },
    places: [
      { key: "iso3166-1:US", slug: "usa", items: 53, kinds: ["grant_period_end", "solicitation_deadline"], last_checked: GENERATED },
      { key: "iso3166-2:US-OK", slug: "usa/ok", items: 3, kinds: ["legislative_action"], last_checked: GENERATED },
      { key: "us.census.geoid.county:40109", slug: "usa/ok/oklahoma-county-40109", items: 2, kinds: ["contract_expiry", "renewal_deadline"], last_checked: GENERATED },
      { key: "us.census.geoid.place:4064000", slug: "usa/ok/oklahoma-city-4064000", items: 1, kinds: ["renewal_deadline"], last_checked: GENERATED },
      { key: "us.census.geoid.county:40131", slug: "usa/ok/cleveland-county-40131", items: 0, kinds: [], last_checked: GENERATED },
      { key: "us.census.geoid.place:4055000", slug: "usa/ok/norman-city-4055000", items: 0, kinds: [], last_checked: GENERATED },
      { key: "iso3166-2:US-TX", slug: "usa/tx", items: 1, kinds: ["agenda_item"], last_checked: GENERATED },
      { key: "us.census.geoid.county:48201", slug: "usa/tx/harris-county-48201", items: 1, kinds: ["agenda_item"], last_checked: GENERATED },
      { key: "iso3166-2:US-VI", slug: "usa/vi", items: 0, kinds: [], last_checked: GENERATED },
      { key: "iso3166-1:CA", slug: "can", items: 0, kinds: [], last_checked: GENERATED },
      { key: "iso3166-2:CA-ON", slug: "can/on", items: 0, kinds: [], last_checked: GENERATED },
      { key: "iso3166-1:FR", slug: "fra", items: 0, kinds: [], last_checked: GENERATED },
      { key: "iso3166-1:DE", slug: "deu", items: 0, kinds: [], last_checked: GENERATED },
    ],
    by_kind: {
      renewal_deadline: 1,
      contract_expiry: 1,
      solicitation_deadline: 1,
      agenda_item: 1,
      legislative_action: 1,
      grant_period_end: 53,
    },
    items_total: 59,
    sizing: {
      contract: { subjects: 2, claims: 11 },
      procurement_notice: { subjects: 1, claims: 4 },
      agenda_item: { subjects: 1, claims: 3 },
      legislative_bill: { subjects: 1, claims: 5 },
      funding_instrument: { subjects: 53, claims: 159 },
    },
    last_checked: GENERATED,
  },
  items: ITEMS,
};
