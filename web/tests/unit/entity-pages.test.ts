// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project.
// P36.42a (K2 GX-06a): the entity page-model helpers — merge, pagination,
// kind/direction words and the typed-absence model.
import { describe, expect, it } from "vitest";
import {
  ENTITY_PAGE_TWIN_FIXTURE,
  entityIndex,
  ENTITY_LABEL_FIXTURES,
} from "../../src/lib/entity-page";
import type { EntityPageTwin } from "../../src/lib/entity-page";
import {
  accessKindWord,
  directionExplainer,
  directionWord,
  ENTITY_LIST_PAGE_SIZE,
  kindPlural,
  kindWord,
  mergeEntityTwins,
  paginate,
  typeList,
} from "../../src/lib/entity-pages";
import { isManifestArtifact } from "../../src/lib/figures";

describe("kind display words (SIG-UI-053/108 — a word, never a raw token)", () => {
  it("names the contract-A kinds", () => {
    expect(kindWord("org")).toBe("Organisation");
    expect(kindWord("agency")).toBe("Government body");
    expect(kindWord("portal")).toBe("Registry portal");
    expect(kindPlural("org")).toBe("Organisations");
  });
  it("falls back to a word, never the token itself", () => {
    expect(kindWord("mystery_kind")).toBe("Record");
    expect(kindPlural("mystery_kind")).toBe("Records");
  });
});

describe("direction + access kind in words (H-2 / SIG-UI-024)", () => {
  it("direction words never render a bare enum", () => {
    expect(directionWord("outbound")).toBe("outbound");
    expect(directionWord("inbound")).toBe("inbound");
    expect(directionExplainer("outbound")).toContain("subject");
    expect(directionExplainer("inbound")).toContain("object");
  });
  it("access kinds render words; null stays null", () => {
    expect(accessKindWord("configured_access")).toBe("configured access");
    expect(accessKindWord("observed_use")).toBe("observed use");
    expect(accessKindWord("declared_policy")).toBe("declared policy");
    expect(accessKindWord(null)).toBeNull();
  });
});

describe("mergeEntityTwins — the per-compartment union (ADR-106)", () => {
  it("is the identity for a single twin", () => {
    const m = mergeEntityTwins([ENTITY_PAGE_TWIN_FIXTURE]);
    expect(m.compartments).toEqual(["sig_graph"]);
    expect(m.claims).toHaveLength(ENTITY_PAGE_TWIN_FIXTURE.claims.length);
    expect(m.relations).toHaveLength(ENTITY_PAGE_TWIN_FIXTURE.relations.length);
    expect(m.claimIds).toContain("clm-apd-vigilant-1");
    expect(m.claimIds).toContain("clm-apd-degree-1");
  });

  it("dedupes a claim filed under two compartments — never twice", () => {
    const odbl: EntityPageTwin = {
      ...ENTITY_PAGE_TWIN_FIXTURE,
      compartment: "odbl",
    };
    const m = mergeEntityTwins([ENTITY_PAGE_TWIN_FIXTURE, odbl]);
    expect(m.compartments).toEqual(["odbl", "sig_graph"]);
    // Identical rows in both files render once.
    expect(m.claims).toHaveLength(ENTITY_PAGE_TWIN_FIXTURE.claims.length);
    expect(m.relations[0]!.items).toHaveLength(1);
    expect(m.summary).toHaveLength(ENTITY_PAGE_TWIN_FIXTURE.summary.length);
  });

  it("unions a second compartment's distinct facts", () => {
    const odbl: EntityPageTwin = {
      ...ENTITY_PAGE_TWIN_FIXTURE,
      compartment: "odbl",
      claims: [
        {
          predicate: "agency_name_osm",
          relation: "agency name (OSM)",
          envelope: {
            status: "resolved",
            support: "WEAKLY_SUPPORTED",
            agreement: "UNCONTESTED",
            currency: "CURRENT",
            rationale: null,
          },
          values: ["Acworth PD"],
          observed_at: null,
          date_kind: "undated",
          sources: [{ id: "osm", name: "OpenStreetMap" }],
          claim_ids: ["clm-osm-1"],
        },
      ],
      relations: [],
      access: { closures: [], degree_only: [] },
      summary: [],
    };
    const m = mergeEntityTwins([ENTITY_PAGE_TWIN_FIXTURE, odbl]);
    expect(m.claims).toHaveLength(ENTITY_PAGE_TWIN_FIXTURE.claims.length + 1);
    expect(m.claimIds).toContain("clm-osm-1");
  });

  it("refuses an empty twin set (SIG-ENG-042)", () => {
    expect(() => mergeEntityTwins([])).toThrow();
  });
});

describe("the A–Z list model (SIG-UI-070)", () => {
  const index = entityIndex(ENTITY_LABEL_FIXTURES);

  it("splits published rows from typed review rows per url_type", () => {
    const org = typeList(index, "org");
    expect(org.published.map((r) => r.label)).toEqual(["Vigilant Solutions (LEARN)"]);
    expect(org.review).toHaveLength(1);
    expect(org.review[0]!.review_state).toBe("not_yet_reviewed");
    // The review row carries no name — the state IS the record.
    expect(org.review[0]).not.toHaveProperty("label");
  });

  it("paginates by path", () => {
    const rows = Array.from({ length: ENTITY_LIST_PAGE_SIZE + 3 }, (_, i) => i);
    const p1 = paginate(rows, 1);
    const p2 = paginate(rows, 2);
    expect(p1.rows).toHaveLength(ENTITY_LIST_PAGE_SIZE);
    expect(p2.rows).toHaveLength(3);
    expect(p2.pages).toBe(2);
  });
});

describe("figure artifact admission (the twin + label streams)", () => {
  it("admits the entity twin and label stream by pattern", () => {
    expect(
      isManifestArtifact("web/entity/agency/acworth-police-department--4g2wm8q/index.sig_graph.json"),
    ).toBe(true);
    expect(isManifestArtifact("labels/sig_graph.jsonl")).toBe(true);
    expect(isManifestArtifact("web/entity/agency/acworth--4g2wm8q/")).toBe(false);
  });
});
