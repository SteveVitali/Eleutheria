// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// P34.13 (K14 NEW-8, QW-11): digit grouping and the API-terms URL helpers.
import { describe, it, expect, afterEach } from "vitest";
import { groupDigits, fmtInt } from "../../src/lib/format";
import { apiTermsUrl, publicApiBaseUrl } from "../../src/lib/public-api";
import { defaultDescription } from "../../src/lib/meta";

describe("groupDigits (K14 NEW-8)", () => {
  it("groups every run of five or more digits", () => {
    expect(groupDigits("2423200")).toBe("2,423,200");
    expect(groupDigits("12345")).toBe("12,345");
    expect(groupDigits("1234567")).toBe("1,234,567");
  });
  it("leaves runs shorter than five digits alone (K14 §3.6)", () => {
    expect(groupDigits("3,994")).toBe("3,994");
    expect(groupDigits("3994")).toBe("3994");
    expect(groupDigits("42")).toBe("42");
  });
  it("never rounds or alters the value — separators only", () => {
    expect(groupDigits("1000000")).toBe("1,000,000");
  });
  it("groups inside prose but leaves identifier shapes readable", () => {
    expect(groupDigits("showing 2 of 210 sources")).toBe("showing 2 of 210 sources");
    expect(groupDigits("count 24232 here")).toBe("count 24,232 here");
  });
  it("does not group non-digit separators of dates and codes", () => {
    // ISO dates run at most four digits — untouched by the ≥5 rule.
    expect(groupDigits("2026-08-20")).toBe("2026-08-20");
    expect(groupDigits("resolver-ruleset-2026.07")).toBe("resolver-ruleset-2026.07");
  });
});

describe("fmtInt", () => {
  it("formats integers with English grouping", () => {
    expect(fmtInt(0)).toBe("0");
    expect(fmtInt(210)).toBe("210");
    expect(fmtInt(2423200)).toBe("2,423,200");
  });
});

describe("public-api (QW-11)", () => {
  const env = process.env;
  afterEach(() => {
    process.env = env;
  });
  it("defaults to the public read API recorded at launch", () => {
    delete process.env.SIG_API_BASE_URL;
    expect(publicApiBaseUrl()).toBe("https://sig-api-e5ctyx36jq-uc.a.run.app");
    expect(apiTermsUrl()).toBe("https://sig-api-e5ctyx36jq-uc.a.run.app/terms");
  });
  it("honours SIG_API_BASE_URL and strips trailing slashes", () => {
    process.env = { ...env, SIG_API_BASE_URL: "https://api.example.test/" };
    expect(apiTermsUrl()).toBe("https://api.example.test/terms");
  });
});

describe("defaultDescription (QW-11, copy row MD-01)", () => {
  it("derives a unique description from the unique page title", () => {
    expect(defaultDescription("Data freshness")).toBe(
      "Data freshness — Surveillance Infrastructure Graph (SIG)",
    );
    expect(defaultDescription("Page not found")).not.toBe(defaultDescription("Data freshness"));
  });
});
