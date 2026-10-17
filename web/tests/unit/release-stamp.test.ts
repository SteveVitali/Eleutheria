// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// P35.13 / SIG-REL-009 (G3 §6.1): the release-stamp reader — it renders the
// release's sig.site-release/1 verbatim (never recomputes a value), is absent
// when no release is bound, and refuses a malformed document outright.

import { afterEach, beforeAll, describe, expect, it } from "vitest";
import { mkdtempSync, mkdirSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

import { getReleaseStamp, validateSiteReleaseDoc } from "../../src/lib/release-stamp";

const saved = {
  source: process.env.SIG_DATA_SOURCE,
  dir: process.env.SIG_EXPORT_DIR,
  rj: process.env.SIG_RELEASE_JSON,
  rd: process.env.SIG_RELEASE_DIR,
};
afterEach(() => {
  for (const [key, value] of [
    ["SIG_DATA_SOURCE", saved.source],
    ["SIG_EXPORT_DIR", saved.dir],
    ["SIG_RELEASE_JSON", saved.rj],
    ["SIG_RELEASE_DIR", saved.rd],
  ] as const) {
    if (value === undefined) delete process.env[key];
    else process.env[key] = value;
  }
});

const PUB = `p-${"a".repeat(64)}`;
const COMMIT = "f7f67f16257e7ee0ab508a9ae24c5015475d23dc";

function siteRelease(over: Record<string, unknown> = {}): Record<string, unknown> {
  return {
    schema: "sig.site-release/1",
    label: "sig-2026-10-15.1",
    publication_id: PUB,
    descriptor_sha256: "b".repeat(64),
    as_of_world: "2026-10-15T00:00:00Z",
    as_of_belief: "2026-10-15T06:00:00Z",
    belief_pinned: true,
    built_at: "2026-10-15T06:02:11Z",
    code: {
      commit: COMMIT,
      url: `https://github.com/SteveVitali/Eleutheria/commit/${COMMIT}`,
      repository: "https://github.com/SteveVitali/Eleutheria",
    },
    integrity_manifest: { path: "integrity.manifest.json", sha256: "c".repeat(64) },
    routes_sha256: "d".repeat(64),
    ...over,
  };
}

let dir: string;
beforeAll(() => {
  dir = mkdtempSync(join(tmpdir(), "sig-release-stamp-"));
});

describe("getReleaseStamp — fixtures mode", () => {
  it("is null (a development build names no release)", () => {
    delete process.env.SIG_DATA_SOURCE;
    expect(getReleaseStamp()).toBeNull();
  });
});

describe("getReleaseStamp — export mode", () => {
  it("is null when no release.json is bound (the honest interim state)", () => {
    process.env.SIG_DATA_SOURCE = "export";
    process.env.SIG_EXPORT_DIR = join(dir, "empty-export");
    expect(getReleaseStamp()).toBeNull();
  });

  it("renders every stamp field verbatim from sig.site-release/1", () => {
    process.env.SIG_DATA_SOURCE = "export";
    const relDir = join(dir, "release");
    mkdirSync(relDir, { recursive: true });
    writeFileSync(join(relDir, "release.json"), JSON.stringify(siteRelease()));
    process.env.SIG_RELEASE_DIR = relDir;
    process.env.SIG_EXPORT_DIR = join(dir, "empty-export");

    const stamp = getReleaseStamp();
    expect(stamp).not.toBeNull();
    expect(stamp!.label).toBe("sig-2026-10-15.1");
    expect(stamp!.publicationId).toBe(PUB);
    expect(stamp!.publicationShort).toBe(`p-aaaaaaaa…`);
    expect(stamp!.asOfWorld).toBe("2026-10-15 00:00 UTC");
    expect(stamp!.builtAt).toBe("2026-10-15 06:02:11 UTC");
    expect(stamp!.commit8).toBe("f7f67f16");
    expect(stamp!.commitHref).toBe(
      `https://github.com/SteveVitali/Eleutheria/commit/${COMMIT}`,
    );
    expect(stamp!.describedby).toBe("/release.json");
    expect(stamp!.metaContent).toBe(`sig-2026-10-15.1 ${PUB}`);
    expect(stamp!.releaseBlock).toEqual({
      label: "sig-2026-10-15.1",
      publication_id: PUB,
      as_of_world: "2026-10-15T00:00:00Z",
    });
  });

  it("never prints a pinning posture (G3 §6.1 NEW-2 interim-text rule)", () => {
    // belief_pinned is carried as data (the JSON twin reports it verbatim);
    // the stamp's rendered strings never turn it into a claim — every
    // printable field is checked, not the flag's value.
    process.env.SIG_DATA_SOURCE = "export";
    const relDir = join(dir, "rel-unpinned");
    mkdirSync(relDir, { recursive: true });
    writeFileSync(
      join(relDir, "release.json"),
      JSON.stringify(siteRelease({ belief_pinned: false })),
    );
    process.env.SIG_RELEASE_DIR = relDir;
    process.env.SIG_EXPORT_DIR = join(dir, "empty-export");
    const stamp = getReleaseStamp()!;
    for (const field of [
      stamp.label,
      stamp.publicationShort,
      stamp.asOfWorld,
      stamp.builtAt,
      stamp.commit8,
      stamp.metaContent,
    ]) {
      expect(field.toLowerCase()).not.toContain("pinned");
    }
  });

  it("reads <exportDir>/release.json when no env var names one", () => {
    process.env.SIG_DATA_SOURCE = "export";
    const exportDir = join(dir, "staged-export");
    mkdirSync(exportDir, { recursive: true });
    writeFileSync(join(exportDir, "release.json"), JSON.stringify(siteRelease()));
    process.env.SIG_EXPORT_DIR = exportDir;
    delete process.env.SIG_RELEASE_DIR;
    delete process.env.SIG_RELEASE_JSON;
    expect(getReleaseStamp()?.label).toBe("sig-2026-10-15.1");
  });

  it("throws on a malformed document — never degrades a stamp", () => {
    process.env.SIG_DATA_SOURCE = "export";
    const relDir = join(dir, "bad-release");
    mkdirSync(relDir, { recursive: true });
    writeFileSync(
      join(relDir, "release.json"),
      JSON.stringify(siteRelease({ label: "not-a-label" })),
    );
    process.env.SIG_RELEASE_DIR = relDir;
    process.env.SIG_EXPORT_DIR = join(dir, "empty-export");
    expect(() => getReleaseStamp()).toThrow(/not a valid sig\.site-release\/1/);
  });
});

describe("validateSiteReleaseDoc", () => {
  it("rejects a wrong schema id", () => {
    expect(() => validateSiteReleaseDoc(siteRelease({ schema: "sig.x/1" }), "t")).toThrow(
      /schema/,
    );
  });
  it("rejects a non-hex publication id", () => {
    expect(() =>
      validateSiteReleaseDoc(siteRelease({ publication_id: "p-xyz" }), "t"),
    ).toThrow(/publication_id/);
  });
  it("rejects a missing code block", () => {
    const doc = siteRelease();
    delete doc.code;
    expect(() => validateSiteReleaseDoc(doc, "t")).toThrow(/code block/);
  });
});
