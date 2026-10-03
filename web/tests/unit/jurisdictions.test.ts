// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// P34.14 (QW-8, K4 NEW-1, F-105): the interim jurisdiction display-name lookup.
// Places are shown by name with the code secondary — never a bare code alone.
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, it, expect } from "vitest";
import {
  JURISDICTION_NAMES,
  displayJurisdiction,
  dossierDisplayTitle,
} from "../../src/lib/jurisdictions";

const REGISTRY_TOML = fileURLToPath(
  new URL("../../../connectors/src/connectors/data/camera_registry_targets.toml", import.meta.url),
);

/** Every `state = "…"` code the connector registry can emit today (AC4). */
const EMITTED_CODES = [
  ...new Set([...readFileSync(REGISTRY_TOML, "utf-8").matchAll(/state = "([^"]+)"/g)].map((m) => m[1])),
];

describe("JURISDICTION_NAMES covers every emitted code (AC4)", () => {
  it("names every jurisdiction code the registry emits", () => {
    expect(EMITTED_CODES.length).toBeGreaterThan(40);
    for (const code of EMITTED_CODES) {
      expect(JURISDICTION_NAMES, `code ${code}`).toHaveProperty(code);
    }
  });
  it("never maps a code to another bare code (a name is not a code)", () => {
    for (const [code, name] of Object.entries(JURISDICTION_NAMES)) {
      expect(name, `code ${code}`).not.toMatch(/^[A-Z0-9-]+$/);
    }
  });
});

describe("displayJurisdiction", () => {
  it("names a US state code and keeps the code secondary", () => {
    expect(displayJurisdiction("AL")).toEqual({
      name: "Alabama",
      code: "AL",
      label: "Alabama (AL)",
      known: true,
      combines: null,
    });
  });
  it("names an ISO 3166-2 subdivision", () => {
    expect(displayJurisdiction("AU-QLD").label).toBe("Queensland, Australia (AU-QLD)");
  });
  it("names the national code", () => {
    expect(displayJurisdiction("US").label).toBe("United States (US)");
  });
  it("the ID mixed bucket names both places (K4 NEW-1)", () => {
    const d = displayJurisdiction("ID");
    expect(d.combines).toEqual(["Idaho (US)", "Indonesia"]);
    expect(d.label).toBe("Idaho (US) and Indonesia (ID)");
  });
  it("the MN mixed bucket names both places (K4 NEW-1)", () => {
    const d = displayJurisdiction("MN");
    expect(d.combines).toEqual(["Minnesota", "Mongolia"]);
    expect(d.label).toBe("Minnesota and Mongolia (MN)");
  });
  it("renders the unresolved bucket as what it is", () => {
    const d = displayJurisdiction("unresolved");
    expect(d.label).toBe("Unresolved jurisdiction");
    expect(d.code).toBeNull();
  });
  it("passes a value that already names the place through untouched", () => {
    const d = displayJurisdiction("Paris, France");
    expect(d).toEqual({
      name: "Paris, France",
      code: null,
      label: "Paris, France",
      known: true,
      combines: null,
    });
  });
  it("an unmapped bare code fails loud and is flagged (AC5)", () => {
    const d = displayJurisdiction("QQ-XX");
    expect(d).toEqual({
      name: "Unspecified jurisdiction",
      code: "QQ-XX",
      label: "Unspecified jurisdiction (QQ-XX)",
      known: false,
      combines: null,
    });
  });
  it("a lower-case non-code value that is not a name is passed through, not flagged", () => {
    expect(displayJurisdiction("unreported").label).toBe("unreported");
  });
});

describe("dossierDisplayTitle", () => {
  it("rewrites a trailing code suffix to 'Name (CODE)'", () => {
    expect(dossierDisplayTitle("Surveillance infrastructure — AL", "AL")).toBe(
      "Surveillance infrastructure — Alabama (AL)",
    );
  });
  it("leads a mixed bucket with both places, code secondary", () => {
    expect(dossierDisplayTitle("Surveillance infrastructure — MN", "MN")).toBe(
      "Surveillance infrastructure — Minnesota and Mongolia (MN)",
    );
  });
  it("leaves a name-form subject label untouched (fixture data)", () => {
    expect(dossierDisplayTitle("Oklahoma City, Oklahoma", "Oklahoma City, Oklahoma")).toBe(
      "Oklahoma City, Oklahoma",
    );
  });
  it("leaves a label that does not embed its code untouched", () => {
    expect(dossierDisplayTitle("Oklahoma City, Oklahoma", "OK")).toBe("Oklahoma City, Oklahoma");
  });
  it("does not rewrite a mid-label code", () => {
    expect(dossierDisplayTitle("AL corridor study — AL region", "AL")).toBe(
      "AL corridor study — AL region",
    );
  });
});

describe("the combines sentence the JD-01/JD-02 rows render (K4 NEW-1)", () => {
  it("expands to the recorded ID and MN wordings", () => {
    for (const [code, expected] of [
      ["ID", "This dossier combines Idaho (US) and Indonesia."],
      ["MN", "This dossier combines Minnesota and Mongolia."],
    ] as const) {
      const d = displayJurisdiction(code);
      expect(d.combines).not.toBeNull();
      expect(`This dossier combines ${d.combines!.join(" and ")}.`).toBe(expected);
    }
  });
});
