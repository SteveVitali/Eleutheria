// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project.
// P37.23 (K2 GX-06b §4.2 row 12): the entity downloads' served bytes — the
// relationships JSON/CSV slice and the statements jsonl, mirrored from the
// exporter's emitted shapes; deterministic, never a re-derivation.
import { describe, expect, it } from "vitest";
import {
  ENTITY_PAGE_TWIN_CONTRACT_FIXTURE,
  ENTITY_PAGE_TWIN_FIXTURE,
} from "../../src/lib/entity-page";
import {
  canonicalJsonLine,
  ENTITY_RELATIONSHIPS_SCHEMA,
  relationshipsCsv,
  relationshipsDoc,
  statementsJsonl,
} from "../../src/lib/entity-downloads";
import { STATEMENT_FIXTURES } from "../../src/lib/statements-fixture";
import { getEntityDownloadBytes } from "../../src/lib/data";

const CONTRACT = ENTITY_PAGE_TWIN_CONTRACT_FIXTURE;

describe("relationshipsDoc", () => {
  it("emits the sig.entity-relationships/1 doc with the twin's groups verbatim", () => {
    const doc = relationshipsDoc(CONTRACT);
    expect(doc.schema).toBe(ENTITY_RELATIONSHIPS_SCHEMA);
    expect(doc.entity_id).toBe(CONTRACT.entity_id);
    expect(doc.key).toBe(CONTRACT.key);
    expect(doc.compartment).toBe("sig_graph");
    expect(doc.relations).toBe(CONTRACT.relations);
  });
});

describe("relationshipsCsv", () => {
  it("writes the declared column order, one row per emitted item", () => {
    const csv = relationshipsCsv(CONTRACT);
    const lines = csv.trimEnd().split("\n");
    expect(lines[0]).toBe(
      "relation,direction,access_kind,counterparty_label,counterparty_entity_id," +
        "counterparty_key,role,date,date_kind,currency,status,support,agreement," +
        "historical,sources,claim_ids",
    );
    expect(lines).toHaveLength(3); // header + buyer + seller
    expect(lines[1]).toContain("contract buyer,outbound,,Acworth Police Department");
    expect(lines[1]).toContain("clm-contract-buyer-1");
    expect(lines[2]).toContain("contract seller,outbound,,Vigilant Solutions (LEARN)");
  });
  it("quotes only cells carrying reserved characters and writes the undated empty date", () => {
    const csv = relationshipsCsv(ENTITY_PAGE_TWIN_FIXTURE);
    // Plain cells stay unquoted — quoting is reserved, never decorative.
    expect(csv).toContain("camera operator,inbound,,surveillance camera in usa-ga");
    expect(csv).toContain("Vigilant Solutions (LEARN),0190cafe-");
    // The undated camera row carries an empty date cell beside its kind.
    expect(csv).toContain("camera_operator,,undated,UNDATED");
    // A label with a comma quotes; one with a quote doubles it.
    const twin = {
      ...ENTITY_PAGE_TWIN_FIXTURE,
      relations: [
        {
          ...ENTITY_PAGE_TWIN_FIXTURE.relations[0]!,
          items: [
            {
              ...ENTITY_PAGE_TWIN_FIXTURE.relations[0]!.items[0]!,
              counterparty: { label: 'Quoted "Name", Inc.' },
            },
          ],
        },
      ],
    };
    expect(relationshipsCsv(twin)).toContain('"Quoted ""Name"", Inc."');
  });
});

describe("statementsJsonl", () => {
  it("emits the entity's sig.statement/1 slice, canonical JSON per line", () => {
    const out = statementsJsonl(CONTRACT, STATEMENT_FIXTURES);
    const rows = out.trimEnd().split("\n").map((l) => JSON.parse(l));
    expect(rows).toHaveLength(3); // buyer + seller + one value side
    expect(rows.map((r) => r.claim_id).sort()).toEqual([
      "clm-contract-buyer-1",
      "clm-contract-seller-1",
      "clm-contract-value-1",
    ]);
    // Canonical: sorted keys, tight separators, one object per line.
    for (const line of out.trimEnd().split("\n")) {
      expect(line.startsWith("{")).toBe(true);
      expect(canonicalJsonLine(JSON.parse(line))).toBe(line + "\n");
    }
  });
  it("an entity with no cited fixture statements emits empty bytes", () => {
    const out = statementsJsonl(
      { ...CONTRACT, entity_id: "no-such-entity" },
      STATEMENT_FIXTURES,
    );
    expect(out).toBe("");
  });
});

describe("getEntityDownloadBytes (fixtures seam)", () => {
  const KEY = "acworth-alpr-expansion-contract--9p4kxwd";
  it("serves the three named downloads for a twin-bearing entity", () => {
    const json = getEntityDownloadBytes("contract", KEY, "relationships.sig_graph.json")!;
    expect(JSON.parse(json).schema).toBe("sig.entity-relationships/1");
    const csv = getEntityDownloadBytes("contract", KEY, "relationships.sig_graph.csv")!;
    expect(csv.startsWith("relation,direction,")).toBe(true);
    const jsonl = getEntityDownloadBytes("contract", KEY, "statements.sig_graph.jsonl")!;
    expect(jsonl).toContain('"claim_id":"clm-contract-buyer-1"');
  });
  it("returns null for an un-emitted file or compartment — never fabricated bytes", () => {
    expect(getEntityDownloadBytes("contract", KEY, "relationships.odbl.json")).toBeNull();
    expect(getEntityDownloadBytes("contract", KEY, "notes.sig_graph.txt")).toBeNull();
    expect(getEntityDownloadBytes("org", "vigilant-solutions-learn--7xk3mrt", "relationships.sig_graph.json")).toBeNull();
  });
});
