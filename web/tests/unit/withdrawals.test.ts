// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * P34.19 (F-337, SIG-GOV-007) — the committed publication-withdrawal list as
 * the web layer reads it: exactly the nine F-337 Atlas rows, fail-closed on
 * Miami's candidate claim, and `dropWithdrawn` applied to every export-mode
 * payload keyed on a suppressed id.
 */
import { describe, expect, it } from "vitest";
import {
  dropWithdrawn,
  isWithdrawn,
  withdrawalEntries,
  withdrawalFor,
  withdrawnClaimIds,
  withdrawnEntityIds,
  withdrawnIds,
  withdrawnUpstreamIds,
} from "../../src/lib/withdrawals";

const F337_AOS = [
  "AOS000953",
  "AOS000960",
  "AOS000961",
  "AOS000962",
  "AOS000963",
  "AOS000964",
  "AOS000965",
  "AOS000966",
  "AOS004507",
];

const SAN_MATEO_CLAIM = "01a0a6cb-b1e9-7552-b25c-aba32b812402";
const SAN_MATEO_ENTITY = "01a0a6cb-b180-7a78-921d-dddeae9bfa96";
const MIAMI_CANDIDATE = "01a0a6cb-bca2-7111-b994-11c9b0fc129f";

describe("the committed sig.publication-withdrawals/1 list (F-337)", () => {
  it("covers exactly the nine leak-tainted Atlas rows", () => {
    expect(withdrawalEntries()).toHaveLength(9);
    expect([...withdrawnUpstreamIds()].sort()).toEqual([...F337_AOS].sort());
    expect(withdrawnEntityIds().size).toBe(9);
    // nine confirmed claims + Miami's fail-closed candidate
    expect(withdrawnClaimIds().size).toBe(10);
    for (const e of withdrawalEntries()) {
      expect(e.source_id).toBe("eff_atlas_of_surveillance");
      expect(e.reason).toBe("leak-provenance");
      expect(e.disposition).toBe("withdraw");
      expect(e.kind).toBe("rights_withdrawal");
      expect(e.tainted_locator).toContain("buzzfeednews.com");
    }
  });

  it("suppresses the Miami candidate fail-closed (D-P34.19-1)", () => {
    expect(isWithdrawn(MIAMI_CANDIDATE)).toBe(true);
    const miami = withdrawalEntries().find((e) => e.upstream_id === "AOS000960")!;
    expect(miami.candidate_claim_ids).toEqual([MIAMI_CANDIDATE]);
  });

  it("matches every target id and no others", () => {
    for (const id of withdrawnIds()) expect(isWithdrawn(id)).toBe(true);
    expect(isWithdrawn("AOS005165")).toBe(false);
    expect(isWithdrawn("not-an-id")).toBe(false);
    expect(isWithdrawn(undefined)).toBe(false);
    expect(withdrawalFor(SAN_MATEO_CLAIM)?.upstream_id).toBe("AOS000953");
  });
});

describe("dropWithdrawn over export-mode payloads", () => {
  it("drops rows keyed on claim_id, entity_id, subject_id, upstream_id or id", () => {
    const rows = [
      { claim_id: SAN_MATEO_CLAIM, keep: false },
      { entity_id: SAN_MATEO_ENTITY },
      { subject_id: SAN_MATEO_ENTITY },
      { upstream_id: "AOS000953" },
      { id: SAN_MATEO_ENTITY, label: "a map asset" },
      { claimId: MIAMI_CANDIDATE },
      { previous_claim_id: SAN_MATEO_CLAIM },
      { claim_id: "untouched-claim", keep: true },
      { label: "no id fields at all" },
      "a bare string row",
    ];
    const kept = dropWithdrawn(rows);
    expect(kept).toHaveLength(3);
    expect(kept[0]).toEqual({ claim_id: "untouched-claim", keep: true });
  });

  it("leaves an empty withdrawal list a no-op pass-through", () => {
    const rows = [{ id: "anything" }, { claim_id: "anything" }];
    expect(dropWithdrawn(rows)).toHaveLength(2);
  });
});
