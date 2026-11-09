// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * P37.24 (GX-08a) — the committed `sig.graph-overview/1` fixture corpus the
 * data layer serves in `fixtures` mode. Columnar per K2 §6.3, one document
 * per overview (the single-compartment fixture set); invented labels only.
 */

import type { ComponentsIndexEntry, GraphIndexEntry } from "./graph-overview";

const RELEASE = { label: "sig-fixture-2026.11", as_of_world: "2026-11-09" };

function doc(
  overview: string,
  title: string,
  question: string,
  dict: Record<string, unknown[]>,
  nodes: Record<string, unknown[]>,
  edges: Record<string, unknown[]>,
): unknown {
  return {
    schema: "sig.graph-overview/1",
    overview,
    title,
    question,
    release: RELEASE,
    generated_at: "2026-11-09T00:00:00Z",
    compartment: "sig_graph",
    dict,
    nodes,
    edges,
    cap: 3000,
    cap_actions: [],
    position_note:
      "position has no geographic meaning; nearby nodes share relationships",
    er_disclosure:
      "SIG has not merged organisations across sources; one agency can appear more than once",
  };
}

const TYPES = doc(
  "types",
  "Type map",
  "What does SIG hold, by kind, and how do kinds connect?",
  {
    kinds: ["kind"],
    labels: ["Organisation", "Government body", "Notice", "Grant"],
    hrefs: ["/entity/org/", "/entity/agency/", "/entity/notice/", "/entity/grant/"],
    places: [],
    predicates: ["buyer", "camera operator", "funder"],
    dates: ["2020-01-28"],
    currency: ["STALE", "UNDATED"],
    sources: ["EFF Data Driven", "OKC procurement"],
  },
  {
    id: ["kind:org", "kind:agency", "kind:notice", "kind:grant"],
    l: [0, 1, 2, 3],
    t: [0, 0, 0, 0],
    j: [-1, -1, -1, -1],
    h: [0, 1, 2, 3],
    x: [40, 58, 76, 94],
    y: [60, 60, 60, 60],
    n: [12, 7, 4, 3],
  },
  {
    s: [2, 0, 3],
    t: [1, 0, 1],
    p: [0, 1, 2],
    n: [2, 1, 1],
    y: [0, -1, 0],
    cur: [0, 1, 0],
    src: [[0], [1], [0]],
  },
);

const SUPPLY = doc(
  "supply",
  "Supply",
  "Who sells surveillance technology to whom?",
  {
    kinds: ["agency", "vendor", "group"],
    labels: [
      "Acme City Police Department",
      "Vigilant Solutions (LEARN)",
      "Meridian Surveillance LLC",
      "2 other suppliers",
      "3 camera records — Oklahoma",
    ],
    hrefs: [
      "/entity/agency/acme-city-police--4g2wm8q/",
      "/entity/org/vigilant-solutions--7x1k2mn/",
      "/entity/org/meridian-surveillance--9p3qw7r/",
      "/entity/agency/acme-city-police--4g2wm8q/",
      "/graphs/supply/usa/ok/",
    ],
    places: ["usa-ok"],
    predicates: ["sells to", "manufactured by"],
    dates: ["2020-01-28"],
    currency: ["STALE", "UNDATED"],
    sources: ["OKC procurement", "OpenStreetMap"],
  },
  {
    id: ["e-buyer", "e-v1", "lit:meridian", "grp:vendor:e-buyer", "grp:sites:flock:usa-ok"],
    l: [0, 1, 2, 3, 4],
    t: [0, 1, 1, 2, 2],
    j: [0, -1, -1, 0, 0],
    h: [0, 1, 2, 3, 4],
    x: [40, 380, 398, 416, 434],
    y: [60, 60, 78, 96, 114],
    n: [0, 0, 0, 2, 3],
  },
  {
    s: [1, 2, 3, 4],
    t: [0, 0, 0, 2],
    p: [0, 0, 0, 1],
    n: [2, 1, 3, 1],
    y: [0, -1, 0, -1],
    cur: [0, 1, 0, 1],
    src: [[0], [0], [0], [1]],
  },
);

const FUNDING = doc(
  "funding",
  "Funding",
  "Who funds whom?",
  {
    kinds: ["agency"],
    labels: ["US DOJ Byrne JAG", "Acme City Police Department"],
    hrefs: ["/entity/agency/us-doj-byrne-jag--2h5k9qz/", "/entity/agency/acme-city-police--4g2wm8q/"],
    places: ["usa-ok"],
    predicates: ["funds"],
    dates: ["2021-06-01"],
    currency: ["HISTORICAL"],
    sources: ["USAspending"],
  },
  {
    id: ["e-funder", "e-recip"],
    l: [0, 1],
    t: [0, 0],
    j: [-1, 0],
    h: [0, 1],
    x: [40, 58],
    y: [60, 60],
    n: [0, 0],
  },
  { s: [0], t: [1], p: [0], n: [1], y: [0], cur: [0], src: [[0]] },
);

const OPERATORS = doc(
  "operators",
  "Operators",
  // D-K14-7: the K2 question is reworded — the banned D-K14-7 tokens stay
  // out of web/src until the operator writes the About maintainer wording.
  "Which bodies run the cameras, and where?",
  {
    kinds: ["vendor", "place"],
    labels: ["Acme Public Works", "Oklahoma"],
    hrefs: ["/entity/org/acme-public-works--3r7t1vx/", "/graphs/operators/usa/ok/"],
    places: ["usa-ok"],
    predicates: ["operates in"],
    dates: ["2024-03-01"],
    currency: ["CURRENT"],
    sources: ["OKC camera registry"],
  },
  {
    id: ["lit:acme-works", "place:usa-ok"],
    l: [0, 1],
    t: [0, 1],
    j: [-1, 0],
    h: [0, 1],
    x: [40, 380],
    y: [60, 60],
    n: [0, 0],
  },
  { s: [0], t: [1], p: [0], n: [4], y: [0], cur: [0], src: [[0]] },
);

// P37.25 (GX-08b) — the 08b fixtures. `access` rides the CC BY-SA `portal`
// compartment (the S6R-12 rule: the share-list claims publish there, never
// blended into the CC-BY graph); `governance`/`adoption` ride `sig_graph`.
// The access doc is the MATRIX form (cap_actions records the fold) and the
// `usa-ok` slice doc carries the unfolded agency-level subgraph the
// drill-down renders.
const ACCESS = {
  ...(doc(
    "access",
    "Access",
    "Who can search whose data?",
    {
      kinds: ["place"],
      labels: ["Oklahoma", "Texas"],
      hrefs: ["/graphs/access/usa/ok/", "/graphs/access/usa/tx/"],
      places: ["usa-ok", "usa-tx"],
      predicates: ["configured access to"],
      dates: ["2020-01-28"],
      currency: ["HISTORICAL"],
      sources: ["Eyes on Flock"],
    },
    {
      id: ["place:usa-ok", "place:usa-tx"],
      l: [0, 1],
      t: [0, 0],
      j: [0, 1],
      h: [0, 1],
      x: [40, 380],
      y: [60, 60],
      n: [0, 0],
    },
    { s: [0, 1], t: [1, 0], p: [0, 0], n: [42, 17], y: [0, 0], cur: [0, 0], src: [[0], [0]], m: [61, 28] },
  ) as Record<string, unknown>),
  compartment: "portal",
  cap_actions: [
    "matrix fold: 500 member nodes folded to 2 place cells — 250 edges merged into 2 weighted cells (agency-level detail on the place drill-downs and each entity's page)",
  ],
};

const ACCESS_OK_SLICE = {
  ...(doc(
    "access",
    "Access",
    "Who can search whose data?",
    {
      kinds: ["agency", "place"],
      labels: ["Acme City Police Department", "Texline Police Department", "Texas"],
      hrefs: [
        "/entity/agency/acme-city-police--4g2wm8q/",
        "/entity/agency/texline-police--9k3xz2p/",
        "/graphs/access/usa/tx/",
      ],
      places: ["usa-ok", "usa-tx"],
      predicates: ["configured access to"],
      dates: ["2020-01-28"],
      currency: ["HISTORICAL"],
      sources: ["Eyes on Flock"],
    },
    {
      id: ["e-acme-pd", "e-texline-pd", "place:usa-tx"],
      l: [0, 1, 2],
      t: [0, 0, 1],
      j: [0, 1, 1],
      h: [0, 1, 2],
      x: [40, 58, 380],
      y: [60, 78, 60],
      n: [0, 0, 0],
    },
    { s: [0, 0], t: [1, 2], p: [0, 0], n: [1, 1], y: [0, 0], cur: [0, 0], src: [[0], [0]], m: [0, 0] },
  ) as Record<string, unknown>),
  compartment: "portal",
  slice: "usa-ok",
};

const GOVERNANCE = doc(
  "governance",
  "Governance",
  "Which laws and ordinances govern which technologies where?",
  {
    kinds: ["instrument", "technology", "agency", "place"],
    labels: [
      "SB 1234 — surveillance oversight act",
      "Automated licence plate readers",
      "Oklahoma Legislature",
      "Oklahoma",
    ],
    hrefs: [
      "/entity/bill/sb-1234-surveillance--2h5k9qz/",
      null,
      "/entity/agency/oklahoma-legislature--7x1k2mn/",
      "/graphs/governance/usa/ok/",
    ],
    places: ["usa-ok"],
    predicates: ["constrains technology", "enacts", "in jurisdiction"],
    dates: ["2025-05-30"],
    currency: ["CURRENT"],
    sources: ["Open States"],
  },
  {
    id: ["e-sb1234", "tech:alpr", "e-ok-leg", "place-lit:oklahoma"],
    l: [0, 1, 2, 3],
    t: [0, 1, 2, 3],
    j: [0, -1, 0, -1],
    h: [0, -1, 1, 2],
    x: [40, 398, 738, 58],
    y: [60, 60, 60, 96],
    n: [0, 0, 0, 0],
  },
  {
    s: [0, 2, 0],
    t: [1, 0, 3],
    p: [0, 1, 2],
    n: [1, 1, 1],
    y: [0, 0, 0],
    cur: [0, 0, 0],
    src: [[0], [0], [0]],
    m: [0, 0, 0],
  },
);

const ADOPTION = doc(
  "adoption",
  "Adoption",
  "Which agencies use which technology, and where?",
  {
    kinds: ["agency", "technology"],
    labels: ["Acme City Police Department", "Automated licence plate readers"],
    hrefs: ["/entity/agency/acme-city-police--4g2wm8q/", null],
    places: ["usa-ok"],
    predicates: ["uses"],
    dates: ["2023-01-15"],
    currency: ["AGING"],
    sources: ["Atlas of Surveillance"],
  },
  {
    id: ["e-acme-pd", "tech:alpr"],
    l: [0, 1],
    t: [0, 1],
    j: [0, -1],
    h: [0, -1],
    x: [40, 398],
    y: [60, 60],
    n: [0, 0],
  },
  { s: [0], t: [1], p: [0], n: [1], y: [0], cur: [0], src: [[0]], m: [0] },
);

/** Overview id → fixture `sig.graph-overview/1` docs (one per compartment). */
export const GRAPH_OVERVIEW_FIXTURES: Record<string, unknown[]> = {
  types: [TYPES],
  supply: [SUPPLY],
  funding: [FUNDING],
  operators: [OPERATORS],
  access: [ACCESS],
  governance: [GOVERNANCE],
  adoption: [ADOPTION],
};

/** P37.25 — the per-place slice docs a folded overview emits
 *  (`web/graph/<ov>/places/<comp>.<jkey>.json`), keyed `<ov>/<jkey>`. */
export const GRAPH_PLACE_FIXTURES: Record<string, unknown[]> = {
  "access/usa-ok": [ACCESS_OK_SLICE],
};

/** P37.25 — the fixture `sig.graph-components/1` index rows. */
export const COMPONENTS_INDEX_FIXTURE: {
  compartment: string;
  components: ComponentsIndexEntry[];
}[] = [
  {
    compartment: "sig_graph",
    components: [{ componentId: "cmp-0001", size: 2, files: ["cmp-0001.json"] }],
  },
];

/** The fixture `sig.graph-index/1` rows. */
export const GRAPH_INDEX_FIXTURE: GraphIndexEntry[] = [
  {
    id: "types",
    title: "Type map",
    question: "What does SIG hold, by kind, and how do kinds connect?",
    nodes: 4,
    edges: 3,
    compartments: ["sig_graph"],
    places: [],
    slices: [],
  },
  {
    id: "supply",
    title: "Supply",
    question: "Who sells surveillance technology to whom?",
    nodes: 5,
    edges: 4,
    compartments: ["sig_graph"],
    places: ["usa-ok"],
    slices: [],
  },
  {
    id: "funding",
    title: "Funding",
    question: "Who funds whom?",
    nodes: 2,
    edges: 1,
    compartments: ["sig_graph"],
    places: ["usa-ok"],
    slices: [],
  },
  {
    id: "operators",
    title: "Operators",
    question: "Which bodies run the cameras, and where?",
    nodes: 2,
    edges: 1,
    compartments: ["sig_graph"],
    places: ["usa-ok"],
    slices: [],
  },
  {
    id: "access",
    title: "Access",
    question: "Who can search whose data?",
    nodes: 2,
    edges: 2,
    compartments: ["portal"],
    places: ["usa-ok", "usa-tx"],
    slices: ["usa-ok"],
  },
  {
    id: "governance",
    title: "Governance",
    question: "Which laws and ordinances govern which technologies where?",
    nodes: 4,
    edges: 3,
    compartments: ["sig_graph"],
    places: ["usa-ok"],
    slices: [],
  },
  {
    id: "adoption",
    title: "Adoption",
    question: "Which agencies use which technology, and where?",
    nodes: 2,
    edges: 1,
    compartments: ["sig_graph"],
    places: ["usa-ok"],
    slices: [],
  },
];
