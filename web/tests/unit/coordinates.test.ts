// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// P37.19 (K1 MAP-04 §4.2) — the local coordinates parser: typed pairs parse
// in the browser, never a request; ambiguity and out-of-range refuse, never
// guess or silently reorder.
import { describe, expect, it } from "vitest";
import { parseCoordinates } from "../../src/lib/coordinates";

describe("parseCoordinates (MAP-04)", () => {
  it("parses a comma-separated signed pair", () => {
    expect(parseCoordinates("41.4959, -94.5205")).toEqual({
      lat: 41.4959,
      lon: -94.5205,
    });
    expect(parseCoordinates("35.4676,-97.5164")).toEqual({
      lat: 35.4676,
      lon: -97.5164,
    });
    expect(parseCoordinates("-35.28, 149.13")).toEqual({
      lat: -35.28,
      lon: 149.13,
    });
  });

  it("parses hemisphere-letter forms (prefix, suffix, space-separated)", () => {
    expect(parseCoordinates("41.4959N, 94.5205W")).toEqual({
      lat: 41.4959,
      lon: -94.5205,
    });
    expect(parseCoordinates("N41.4959, W94.5205")).toEqual({
      lat: 41.4959,
      lon: -94.5205,
    });
    expect(parseCoordinates("41.5N 94.5W")).toEqual({
      lat: 41.5,
      lon: -94.5,
    });
    expect(parseCoordinates("S35.28 E149.13")).toEqual({
      lat: -35.28,
      lon: 149.13,
    });
  });

  it("a lone word or fragment is an honest null — never a guess", () => {
    for (const s of [
      "Austin",
      "",
      "41",
      "41.5 94.5",
      "41,94,3",
      "41.5, Austin",
      "N41.5N, W94.5",
      "see 41.5, -94.5",
      "95.0, -94.5",
      "41.5, -194.5",
    ]) {
      expect(parseCoordinates(s), s).toBeNull();
    }
  });

  it("a contradictory hemisphere sign refuses rather than guessing", () => {
    expect(parseCoordinates("-41.5N, 94.5W")).toBeNull();
    expect(parseCoordinates("41.5S, -94.5E")).toBeNull(); // "-…E" contradicts itself
    expect(parseCoordinates("-41.5S, 94.5W")).toEqual({
      lat: -41.5,
      lon: -94.5,
    });
  });
});
