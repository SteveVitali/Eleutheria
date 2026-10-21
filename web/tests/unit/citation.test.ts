// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

import { describe, expect, it } from "vitest";
import {
  beliefPinnedPermalink,
  citationBlock,
  citationText,
  interimCitationSentence,
  isImmutableReleasePath,
  publicationShort,
  releasePermalink,
  releaseCitationText,
  REPRODUCIBLE_PHRASE,
} from "../../src/lib/citation";
import type { ReleaseContext } from "../../src/lib/citation";
import { joinBase, withBase } from "../../src/lib/paths";
import {
  AS_OF,
  DEVICE_COUNT_BELIEF_CLAIMS,
  RULESET_VERSION,
  resolveAsOfBelief,
} from "../../src/lib/fixtures";
import type { BeliefClaim } from "../../src/lib/fixtures";

const INPUT = {
  path: "/entity/agency/okcpd/",
  title: "Oklahoma City Police Department",
  asOf: AS_OF,
  rulesetVersion: RULESET_VERSION,
};

describe("belief-pinned permalink + citation (SIG-UI-035)", () => {
  it("pins BOTH as-of axes and the ruleset version in the permalink", () => {
    const url = new URL(beliefPinnedPermalink(INPUT));
    expect(url.searchParams.get("as_of_world")).toBe(AS_OF.as_of_world);
    expect(url.searchParams.get("as_of_belief")).toBe(AS_OF.as_of_belief);
    expect(url.searchParams.get("ruleset")).toBe(RULESET_VERSION);
    expect(url.pathname).toBe("/entity/agency/okcpd/");
  });

  it("citation text states source, both instants, ruleset, and the permalink", () => {
    const cite = citationText(INPUT);
    expect(cite).toContain("Surveillance Infrastructure Graph (SIG)");
    expect(cite).toContain(AS_OF.as_of_world);
    expect(cite).toContain(AS_OF.as_of_belief);
    expect(cite).toContain(RULESET_VERSION);
    expect(cite).toContain(beliefPinnedPermalink(INPUT));
  });
});

describe("immutable release citations (P32.13, SIG-FIND-001/002)", () => {
  const PUB = "p-" + "ab".repeat(32);
  const REF = {
    publicationId: PUB,
    recordPath: `/r/${PUB}/c/sig_graph/entity/deployment/ent-1/`,
    title: "A released site record",
    asOf: AS_OF,
    rulesetVersion: RULESET_VERSION,
  };

  it("the release permalink is the immutable namespace URL — no query string", () => {
    const url = releasePermalink(REF);
    expect(url).toBe(`https://surveillancegraph.org${REF.recordPath}`);
    expect(url).not.toContain("as_of_world");
    expect(url).not.toContain("?");
  });

  it("the release citation names the publication, both cuts, ruleset, URL", () => {
    const cite = releaseCitationText(REF);
    expect(cite).toContain(PUB);
    expect(cite).toContain(AS_OF.as_of_world);
    expect(cite).toContain(AS_OF.as_of_belief);
    expect(cite).toContain(RULESET_VERSION);
    expect(cite).toContain(releasePermalink(REF));
  });

  it("the legacy belief-pinned selector is NOT an immutable citation", () => {
    // the query-string form pins a selector — resolved only through the
    // compat index; it never resolves released bytes directly
    const legacy = beliefPinnedPermalink(INPUT);
    expect(legacy).toContain("?");
    expect(legacy).not.toContain("/r/p-");
  });
});

describe("reproducible after a correction (SIG-TIME-008)", () => {
  it("a belief-pinned citation re-resolves to the same value after a later correction", () => {
    const pinnedBelief = "2026-08-20";
    const before = resolveAsOfBelief(DEVICE_COUNT_BELIEF_CLAIMS, pinnedBelief);
    expect(before).toBe(42); // W3 contract beats W2 portal

    // SIG corrects itself: a new, higher-tier claim is asserted LATER.
    const corrected: BeliefClaim[] = [
      ...DEVICE_COUNT_BELIEF_CLAIMS,
      { claim_id: "correction", value: 40, tier: "W4", asserted_at: "2026-09-15" },
    ];

    // The pinned-belief citation is unchanged — the correction is in the future of it.
    expect(resolveAsOfBelief(corrected, pinnedBelief)).toBe(before);
    // But a reader who follows the *current* belief sees the correction.
    expect(resolveAsOfBelief(corrected, "2026-09-30")).toBe(40);
  });
});

// P35.42 (SIG-TRANSP-023, J3 §8.2; F-07/F-099/F-101/F-390/F-399; DR-C3-14):
// the citation block's render model — BaseLayout passes the release context
// on every page, the verbatim cite sentence carries the release id beside the
// as-of pair, and the reproducibility phrase is a RENDER RULE over immutable
// /s/<pub>/ or /r/<pub>/ URLs only.
describe("the citation block model (P35.42, SIG-TRANSP-023, J3 §8.2)", () => {
  const PUB = "p-" + "cd".repeat(32);
  const RELEASE: ReleaseContext = {
    publicationId: PUB,
    label: "sig-2026-10-15.1",
    recordPath: "/dossier/al/",
  };
  const block = (release: ReleaseContext | null, path = INPUT.path) =>
    citationBlock({ ...INPUT, path, release });

  it("a page lacking the release context fails its render (F-399)", () => {
    // `release` is required — omitting it is the defect this row closes.
    expect(() =>
      citationBlock({ ...INPUT, release: undefined } as never),
    ).toThrow(/release context is required/);
  });

  it("an explicit null is the honest development state — no release is fabricated", () => {
    const b = block(null);
    expect(b.mode).toBe("unreleased");
    expect(b.citeSentence).toBeNull();
    expect(b.citeUrl).toBeNull();
    expect(b.releaseId).toBeNull();
    expect(b.reproducible).toBe(false);
    expect(b.interimSentence).toBeNull();
  });

  it("interim: a mutable recordPath yields the verbatim cite sentence + the verbatim J3 interim sentence", () => {
    const b = block(RELEASE);
    expect(b.mode).toBe("interim");
    expect(b.citeSentence).toBe(
      `Cite: ${INPUT.title}, SIG release p-cdcdcdcd… ` +
        `(data as of ${AS_OF.as_of_world}, belief ${AS_OF.as_of_belief}, ` +
        `ruleset ${RULESET_VERSION})`,
    );
    expect(b.interimSentence).toBe(
      "This page is the latest view of release sig-2026-10-15.1; " +
        "an immutable citable copy is not yet published.",
    );
    expect(b.citeUrl).toBeNull();
    expect(b.reproducible).toBe(false);
    // DR-C3-14: the release id sits beside the as-of pair.
    expect(b.releaseId).toBe("sig-2026-10-15.1");
  });

  it("immutable: a /r/<pub>/ recordPath yields the cite sentence with the snapshot URL + the phrase", () => {
    const recordPath = `/r/${PUB}/c/sig_graph/jurisdiction/al/`;
    const b = block({ ...RELEASE, recordPath });
    expect(b.mode).toBe("immutable");
    expect(b.citeUrl).toBe(`https://surveillancegraph.org${recordPath}`);
    expect(b.citeSentence).toBe(
      `Cite: ${INPUT.title}, SIG release p-cdcdcdcd… ` +
        `(data as of ${AS_OF.as_of_world}, belief ${AS_OF.as_of_belief}, ` +
        `ruleset ${RULESET_VERSION}), https://surveillancegraph.org${recordPath}`,
    );
    expect(b.reproducible).toBe(true);
    expect(b.interimSentence).toBeNull();
  });

  it("immutable: a /s/<pub>/ snapshot path flips the same wording", () => {
    const b = block({ ...RELEASE, recordPath: `/s/${PUB}/dossier/al/` });
    expect(b.mode).toBe("immutable");
    expect(b.reproducible).toBe(true);
  });

  it("the reproducibility phrase never appears over a mutable URL — the render rule, not a flag", () => {
    for (const recordPath of [
      "/dossier/al/",
      "/",
      "/methodology/",
      `/r/not-a-publication/c/x/`,
      `/r/${PUB.slice(0, 20)}/c/x/`, // half-formed namespace
      `/s/${PUB.slice(0, 20)}/dossier/al/`,
      `r/${PUB}/c/sig_graph/`, // missing leading slash — not namespaced
      `/releases/${PUB}/`,
      `/entity/agency/okcpd/?as_of_world=x`,
    ]) {
      const b = block({ ...RELEASE, recordPath });
      expect(b.mode).toBe("interim");
      expect(b.reproducible).toBe(false);
      expect(b.citeUrl).toBeNull();
      expect(b.citeSentence ?? "").not.toContain(REPRODUCIBLE_PHRASE);
      expect(b.interimSentence).not.toBeNull();
    }
  });

  it("the withBase() chain: every default recordPath is base-joined — a /s/<pub>/ base makes the page's own path immutable", () => {
    // BaseLayout's default is `withBase(path)`: under the root base the page's
    // path is mutable (interim); under a /s/<pub>/ snapshot base the SAME call
    // yields an immutable path — the wording flips with zero template edits
    // (UXR-25, P36.66a's configured-base seam).
    expect(isImmutableReleasePath(joinBase("/", "/dossier/al/"))).toBe(false);
    expect(isImmutableReleasePath(joinBase(`/s/${PUB}/`, "/dossier/al/"))).toBe(true);
    expect(withBase("/dossier/al/")).toBe("/dossier/al/");
    // An explicit released-record path (a dossier's /r/<pub>/ record) is
    // immutable under either base.
    const recordPath = joinBase("/", `r/${PUB}/c/sig_graph/jurisdiction/al/`);
    expect(isImmutableReleasePath(recordPath)).toBe(true);
  });

  it("the interim sentence is verbatim J3 §8.2 wording — never improvised", () => {
    expect(interimCitationSentence("sig-2026-10-15.1")).toBe(
      "This page is the latest view of release sig-2026-10-15.1; " +
        "an immutable citable copy is not yet published.",
    );
  });

  it("publicationShort matches the release stamp's slice (one abbreviation convention)", () => {
    expect(publicationShort(PUB)).toBe("p-cdcdcdcd…");
  });
});
