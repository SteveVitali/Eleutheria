// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// P36.60 (K8 EV-02 / SIG-EVUI-001,002,003,005,006,008,010): the evidence
// hub's page model — E-handles (K11 §3 grammar, collision pass, ≤64 chars,
// human-readable, deterministic), facets, ≤50-row pagination, the capture
// state vocabulary, the §4.4 diff pair rule, upstream display, and the
// honest-title + run-record rules.
import { describe, expect, it } from "vitest";
import {
  artifactHandles,
  artifactState,
  artifactTitle,
  artifactUpstream,
  artifactsForLane,
  artifactsForPlace,
  artifactsForSource,
  artifactsForState,
  artifactsForType,
  captureViewOriginal,
  claimsForArtifact,
  diffFields,
  diffPairs,
  evidenceRollup,
  handleCode,
  handleSlug,
  laneFacets,
  pageCount,
  pageSlice,
  parseDiffPair,
  parseFacetPath,
  placeFacets,
  sourceFacets,
  stateFacets,
  typeFacets,
  UNPLACED_PATH,
} from "../../src/lib/evidence-hub";
import { EVIDENCE_ARTIFACTS } from "../../src/lib/watch-evidence-fixture";
import { STATEMENT_FIXTURES } from "../../src/lib/statements-fixture";
import type { EvidenceArtifact } from "../../src/lib/recommender";

const byId = (id: string) => EVIDENCE_ARTIFACTS.find((a) => a.artifact_id === id)!;

describe("handles — K11 §3 grammar (SIG-EVUI-010)", () => {
  it("mints human-readable E-<place>-<code>-<slug>-<hash> handles", () => {
    const h = artifactHandles(EVIDENCE_ARTIFACTS).get("contract:okcpd-alpr")!;
    expect(h).toMatch(/^E-[a-z0-9-]+$/);
    expect(h.startsWith("E-usa-ok-oklahoma-city-contract-")).toBe(true);
    expect(h.length).toBeLessThanOrEqual(64);
  });

  it("is deterministic and unique across the list", () => {
    const a = artifactHandles(EVIDENCE_ARTIFACTS);
    const b = artifactHandles(EVIDENCE_ARTIFACTS);
    expect([...a.values()]).toEqual([...b.values()]);
    expect(new Set(a.values()).size).toBe(a.size);
  });

  it("extends the hash on a manufactured collision (4 → 5…8)", () => {
    // Two artifacts that mint the same place+code+slug: collision resolves.
    const twin: EvidenceArtifact = { ...byId("contract:okcpd-alpr"), artifact_id: "contract:other" };
    const handles = artifactHandles([byId("contract:okcpd-alpr"), twin]);
    expect(new Set(handles.values()).size).toBe(2);
  });

  it("marks unplaced artifacts honestly", () => {
    const h = artifactHandles(EVIDENCE_ARTIFACTS).get("brochure:flock-marketing")!;
    expect(h.startsWith("E-unplaced-")).toBe(true);
  });

  it("the code is a one-token type mnemonic ≤10 chars", () => {
    expect(handleCode("meeting_minutes")).toBe("meeting");
    expect(handleCode("portal_snapshot")).toBe("portal");
  });

  it("the slug drops the place tail and abbreviates org suffixes", () => {
    expect(handleSlug("Oklahoma City Police Department contract", "usa-ok-oklahoma-city")).toBe(
      "oklahoma-pd-contract",
    );
    expect(handleSlug("###", "usa")).toBeNull();
  });
});

describe("the honest title (K8 §4.2 — never a bare UUID)", () => {
  it("keeps a human title", () => {
    expect(artifactTitle(byId("contract:okcpd-alpr"))).toContain("OKCPD");
  });
  it("composes one when the title is the artifact's own UUID", () => {
    const a = { ...byId("amendment:okcpd-alpr-1"), title: "018f3c2a-1111-4222-8333-444455556666" };
    const t = artifactTitle(a);
    expect(t).not.toContain("018f3c2a");
    expect(t).toContain("amendment");
  });
});

describe("capture state + classification (SIG-EVUI-003)", () => {
  it("a synthetic artifact is a run record — labelled, never disguised", () => {
    expect(artifactState(byId("news:paywalled-2026-08"))).toBe("legacy_synthetic");
    const row = byId("news:paywalled-2026-08").captures![0]!;
    expect(row.capture_classification).toBe("synthetic");
  });
  it("an actual capture maps to actual_capture; absent to not_recorded", () => {
    expect(artifactState(byId("contract:okcpd-alpr"))).toBe("actual_capture");
    expect(artifactState(byId("minutes:council-2025-03-25"))).toBe("not_recorded");
  });
  it("view_original renders the minted label + note — never an invented href", () => {
    const vo = captureViewOriginal(byId("news:paywalled-2026-08").captures![0]!);
    expect(vo.label).toBe("View at source");
    expect(vo.note).toBe("SIG did not retain these bytes");
  });
});

describe("facets + pagination (J3 G-11, K9 §6.1)", () => {
  it("source, type, lane, state and place facets enumerate only present values", () => {
    expect(sourceFacets(EVIDENCE_ARTIFACTS).length).toBeGreaterThanOrEqual(6);
    expect(typeFacets(EVIDENCE_ARTIFACTS).map((f) => f.id)).toContain("contract");
    expect(laneFacets(EVIDENCE_ARTIFACTS).map((f) => f.id)).toEqual(
      expect.arrayContaining(["raw-ok", "derived-only", "link-only", "unknown"]),
    );
    expect(stateFacets(EVIDENCE_ARTIFACTS).map((f) => f.id)).toEqual(
      expect.arrayContaining(["actual_capture", "legacy_synthetic", "not_recorded"]),
    );
    expect(placeFacets(EVIDENCE_ARTIFACTS).map((f) => f.id)).toContain(UNPLACED_PATH);
  });
  it("the facet selectors return the filtered sets", () => {
    expect(artifactsForSource(EVIDENCE_ARTIFACTS, "public-records-request-city-procurement").length).toBe(2);
    expect(artifactsForType(EVIDENCE_ARTIFACTS, "portal_snapshot").length).toBe(2);
    expect(artifactsForLane(EVIDENCE_ARTIFACTS, "raw-ok").length).toBe(2);
    expect(artifactsForState(EVIDENCE_ARTIFACTS, "legacy_synthetic").length).toBe(2);
    const unplaced = artifactsForPlace(EVIDENCE_ARTIFACTS, UNPLACED_PATH).map((a) => a.artifact_id);
    expect(unplaced).toContain("brochure:flock-marketing");
    expect(unplaced.length).toBe(4);
  });
  it("paginates at 50 rows and parses the facet rest param", () => {
    const big = Array.from({ length: 120 }, (_, i) => ({
      ...byId("contract:okcpd-alpr"),
      artifact_id: `a-${i}`,
    }));
    expect(pageCount(big.length)).toBe(3);
    expect(pageSlice(big, 3).length).toBe(20);
    expect(parseFacetPath("usa/ok/page/2")).toEqual({ id: "usa/ok", page: 2 });
    expect(parseFacetPath("usa/ok")).toEqual({ id: "usa/ok", page: 1 });
  });
});

describe("the §4.4 diff (SIG-EVUI-005 — real captures of the same artifact only)", () => {
  it("mints a pair only where both captures carry extracted fields", () => {
    const pairs = diffPairs(byId("snapshot:portal-2026-08"));
    expect(pairs).toHaveLength(1);
    expect(parseDiffPair(`${pairs[0]!.from.capture_id}..${pairs[0]!.to.capture_id}`)).toEqual([
      "capture:okcpd-portal-2026-06",
      "capture:okcpd-portal-2026-08",
    ]);
    const rows = diffFields(pairs[0]!.from, pairs[0]!.to);
    expect(rows.find((r) => r.field === "active_device_count")?.changed).toBe(true);
    expect(rows.find((r) => r.field === "retention_days")?.changed).toBe(false);
  });
  it("an artifact without fields-bearing captures mints none (export shape)", () => {
    expect(diffPairs(byId("news:paywalled-2026-08"))).toHaveLength(0);
    expect(diffPairs(byId("contract:okcpd-alpr"))).toHaveLength(0);
  });
});

describe("claims, contradictions + upstream", () => {
  it("claimsForArtifact binds statements by capture.artifact_id", () => {
    const statements = new Map(STATEMENT_FIXTURES.map((s) => [s.claim_id, s]));
    const claims = claimsForArtifact(statements, "contract:okcpd-alpr");
    expect(claims.map((c) => c.claim_id)).toContain("active-device-count");
  });
  it("the S-6 upstream block renders full_url / withheld / the named absence", () => {
    expect(artifactUpstream(byId("contract:okcpd-alpr")).href).toBe(
      "https://records.example.gov/okcpd/alpr-contract.pdf",
    );
    const withheld = artifactUpstream({
      ...byId("amendment:okcpd-alpr-1"),
      upstream: { status: "withheld_by_policy" },
    });
    expect(withheld.href).toBeNull();
    expect(artifactUpstream(byId("minutes:council-2025-03-25")).display).toBe(
      "no_upstream_url_recorded",
    );
  });
});

describe("the hub roll-up (§4.1 state of the evidence)", () => {
  it("counts artifacts, run records and captures with bytes", () => {
    const roll = evidenceRollup(EVIDENCE_ARTIFACTS);
    expect(roll.artifacts).toBe(EVIDENCE_ARTIFACTS.length);
    expect(roll.runRecords).toBe(2);
    expect(roll.captures).toBeGreaterThanOrEqual(4);
    expect(roll.capturesWithBytes).toBeGreaterThanOrEqual(3);
  });
});
