// SPDX-License-Identifier: Apache-2.0
// P36.56 (K3 SRCH-06 / SIG-UI-128): scoped-search forms — the contract
// parameters, the jkey chain used by the typeahead scope filter, and the
// scope grammar itself.
import { describe, expect, it } from "vitest";
import {
  jkeyChain,
  jkeySubtree,
  scopedSearchParam,
  typeaheadScopeValue,
} from "../../src/lib/scoped-search";
import { typeaheadCatalog } from "../../src/lib/typeahead-shards";
import {
  matchEntries,
  scopeMatches,
} from "../../src/elements/typeahead-model";

describe("scoped search params (SIG-UI-128)", () => {
  it("emits the contract parameters — one jurisdiction or source key", () => {
    expect(
      scopedSearchParam({
        param: "jurisdiction",
        value: "iso3166-2:US-OK",
        label: "Oklahoma",
      }),
    ).toEqual({ name: "jurisdiction", value: "iso3166-2:US-OK" });
    expect(
      scopedSearchParam({
        param: "source",
        value: "okc_camera_registry",
        label: "Oklahoma City camera registry",
      }),
    ).toEqual({ name: "source", value: "okc_camera_registry" });
  });

  it("the typeahead scope value shares one grammar", () => {
    expect(
      typeaheadScopeValue({ param: "jurisdiction", value: "iso3166-2:US-TX", label: "Texas" }),
    ).toBe("jurisdiction:iso3166-2:US-TX");
    expect(
      typeaheadScopeValue({ param: "source", value: "okc_camera_registry", label: "x" }),
    ).toBe("source:okc_camera_registry");
  });
});

describe("jkeyChain / jkeySubtree (descendants via jurisdiction_chain)", () => {
  it("walks parent_jkey links root-first, self last", () => {
    expect(jkeyChain("us.census.geoid.place:4064000")).toEqual([
      "iso3166-1:US",
      "iso3166-2:US-OK",
      "us.census.geoid.county:40109",
      "us.census.geoid.place:4064000",
    ]);
    expect(jkeyChain("iso3166-1:US")).toEqual(["iso3166-1:US"]);
  });

  it("reaches past a non-page ancestor (Norman through Cleveland County)", () => {
    // Cleveland County (40131) mints no dossier page — it is absent from
    // the index — but Norman's own dossier chain names its parentage, so
    // the walk still resolves the full ancestry.
    expect(jkeyChain("us.census.geoid.place:4055000")).toEqual([
      "iso3166-1:US",
      "iso3166-2:US-OK",
      "us.census.geoid.county:40131",
      "us.census.geoid.place:4055000",
    ]);
  });

  it("an unknown or unkeyed row yields self-only — never a guessed ancestry", () => {
    expect(jkeyChain("no-such-key:XX")).toEqual(["no-such-key:XX"]);
  });

  it("the subtree holds self + every descendant jkey", () => {
    const sub = jkeySubtree("iso3166-2:US-OK");
    expect(sub).toEqual(
      expect.arrayContaining([
        "iso3166-2:US-OK",
        "us.census.geoid.county:40109",
        "us.census.geoid.place:4064000",
      ]),
    );
    // Norman sits under US-OK through the non-page Cleveland County —
    // the subtree holds it via the full ancestry, not the index alone.
    expect(sub).toContain("us.census.geoid.place:4055000");
    // Cleveland County itself has no dossier page, so no catalog entry
    // suggests it — but its jkey still resolves inside Norman's chain.
    expect(sub).not.toContain("us.census.geoid.county:40131");
    expect(sub).not.toContain("iso3166-2:US-TX");
    expect(sub).not.toContain("iso3166-1:US");
  });
});

describe("matchEntries alternate scoring (P36.56 regression)", () => {
  it("a non-matching alt never demotes a label that matched", () => {
    // The shipped fixture alt list pairs the subject label with the bare
    // country code — "Oklahoma" + alt "US" must still surface under "ok".
    const entries = [
      {
        label: "Oklahoma, United States",
        href: "/dossier/usa/ok/",
        alt: ["Surveillance infrastructure — Oklahoma, United States", "US"],
      },
      { label: "OKC camera registry", href: "/sources/", alt: [] },
    ];
    const matched = matchEntries(entries, "ok").map((e) => e.label);
    expect(matched).toContain("Oklahoma, United States");
    expect(matched[0]).toBe("Oklahoma, United States"); // label match leads
    // And an alt-only hit still surfaces the entry ("US" → Oklahoma).
    expect(matchEntries(entries, "us").map((e) => e.label)).toContain(
      "Oklahoma, United States",
    );
  });
});

describe("typeahead scope parameter (SRCH-06)", () => {
  it("scopeMatches narrows to the subtree or the one source", () => {
    const okc = { label: "Oklahoma City", jkey: "us.census.geoid.place:4064000", chain: ["iso3166-1:US", "iso3166-2:US-OK", "us.census.geoid.county:40109", "us.census.geoid.place:4064000"], href: "/" };
    const tx = { label: "Texas", jkey: "iso3166-2:US-TX", chain: ["iso3166-1:US", "iso3166-2:US-TX"], href: "/" };
    const src = { label: "Registry", source_id: "okc_camera_registry", href: "/" };
    const j = "jurisdiction:iso3166-2:US-OK";
    expect(scopeMatches(okc, j)).toBe(true); // descendant of OK
    expect(scopeMatches(tx, j)).toBe(false);
    expect(scopeMatches(src, j)).toBe(false); // a source is never a place-scope member
    expect(scopeMatches(src, "source:okc_camera_registry")).toBe(true);
    expect(scopeMatches(okc, "source:okc_camera_registry")).toBe(false);
    expect(scopeMatches(okc, null)).toBe(true); // unscoped = unchanged
    // An entry with no chain metadata never invents membership.
    expect(scopeMatches({ label: "x", href: "/" }, j)).toBe(false);
    // Junk scope attributes never widen: no prefix → unscoped, a foreign
    // kind → matches nothing.
    expect(scopeMatches(okc, "bogus")).toBe(true);
    expect(scopeMatches(okc, "other:x")).toBe(false);
  });
});

describe("catalog scope fields", () => {
  it("place entries carry jkey + ancestor chain; sources carry source_id", () => {
    const cat = typeaheadCatalog();
    const okc = cat.find((e) => e.jkey === "us.census.geoid.place:4064000");
    expect(okc).toBeDefined();
    expect(okc!.chain).toContain("iso3166-2:US-OK");
    expect(okc!.chain![okc!.chain!.length - 1]).toBe("us.census.geoid.place:4064000");
    const src = cat.find((e) => e.kind === "source");
    expect(src?.source_id).toBeTruthy();
  });

  it("a jurisdiction scope keeps only the subtree's places", () => {
    const cat = typeaheadCatalog();
    const scope = "jurisdiction:iso3166-2:US-OK";
    const inScope = cat.filter((e) => scopeMatches(e, scope));
    expect(inScope.length).toBeGreaterThan(0);
    expect(inScope.every((e) => e.chain?.includes("iso3166-2:US-OK"))).toBe(true);
    // An out-of-scope place (Texas) and a source are never suggested.
    const out = cat.filter((e) => !scopeMatches(e, scope));
    expect(out.some((e) => e.jkey === "iso3166-2:US-TX")).toBe(true);
    expect(out.some((e) => e.kind === "source")).toBe(true);
    // The same filter applied after text matching keeps only scoped hits.
    const matched = matchEntries(inScope, "ok").filter((e) => scopeMatches(e, scope));
    for (const e of matched) {
      expect(e.chain).toContain("iso3166-2:US-OK");
    }
  });
});
