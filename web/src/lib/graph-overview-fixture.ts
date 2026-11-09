// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * P37.24 (GX-08a) — the committed `sig.graph-overview/1` fixture corpus the
 * data layer serves in `fixtures` mode. Columnar per K2 §6.3, one document
 * per overview (the single-compartment fixture set); invented labels only.
 */

import type { GraphIndexEntry } from "./graph-overview";

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
  "Who runs the cameras, where?",
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

/** Overview id → fixture `sig.graph-overview/1` docs (one per compartment). */
export const GRAPH_OVERVIEW_FIXTURES: Record<string, unknown[]> = {
  types: [TYPES],
  supply: [SUPPLY],
  funding: [FUNDING],
  operators: [OPERATORS],
};

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
  },
  {
    id: "supply",
    title: "Supply",
    question: "Who sells surveillance technology to whom?",
    nodes: 5,
    edges: 4,
    compartments: ["sig_graph"],
    places: ["usa-ok"],
  },
  {
    id: "funding",
    title: "Funding",
    question: "Who funds whom?",
    nodes: 2,
    edges: 1,
    compartments: ["sig_graph"],
    places: ["usa-ok"],
  },
  {
    id: "operators",
    title: "Operators",
    question: "Who runs the cameras, where?",
    nodes: 2,
    edges: 1,
    compartments: ["sig_graph"],
    places: ["usa-ok"],
  },
];
