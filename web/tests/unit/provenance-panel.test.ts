// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * P35.36 (R11-K13-TX-08a / J3 §5.1–5.2, K13 §7 W1 / UXR-33, SIG-TRANSP-011):
 * the shared `<ProvenancePanel>` contract tests — the verbatim binding-state
 * wording, the named-absence discipline (no blank fields, no implied
 * document), the S-6 upstream forms, `withBase()` on every internal link, and
 * the cross-surface consistency property UXR-33 names: ONE statement row →
 * ONE contract → identical field set and wording wherever it renders.
 */

import { renderToStaticMarkup } from "react-dom/server";
import { createElement } from "react";
import { describe, expect, it } from "vitest";

import ProvenancePanel from "../../src/components/ProvenancePanel";
import {
  BINDING_STATE_TEMPLATES,
  FIELD_LABELS,
  NO_UPSTREAM_URL,
  NOT_RECORDED,
  NOT_YET_REVIEWED,
  PANEL_SCHEMA,
  panelForClaim,
  panelFromStatement,
  bindingStateText,
} from "../../src/lib/provenance-panel";
import type { StatementRow } from "../../src/lib/provenance-panel";
import { STATEMENT_FIXTURES } from "../../src/lib/statements-fixture";
import { BASE, withBase } from "../../src/lib/paths";

const render = (panel: Parameters<typeof ProvenancePanel>[0]["panel"], anchor = true) =>
  renderToStaticMarkup(createElement(ProvenancePanel, { panel, anchor }));

describe("binding-state wording — J3 §5.1 verbatim", () => {
  const base: StatementRow = { claim_id: "c1", source_id: "src_a" };

  it("actual_capture — 'Captured from <host> on <retrieved_at>; sha256 <…>.'", () => {
    const stmt: StatementRow = {
      ...base,
      binding_status: "actual_capture",
      capture: {
        retrieved_at: "2026-05-01T12:00:00Z",
        digest: "sha256:abc",
      },
      upstream: { status: "host_only", host: "docs.example.gov" },
    };
    const { state, text } = bindingStateText(stmt);
    expect(state).toBe("actual_capture");
    expect(text).toBe(
      "Captured from docs.example.gov on 2026-05-01T12:00:00Z; sha256 sha256:abc.",
    );
  });

  it("replayed — 'Re-derived on <date> from a capture made on <retrieved_at>.'", () => {
    const stmt: StatementRow = {
      ...base,
      binding_status: "replayed",
      capture: { bound_at: "2026-05-02", retrieved_at: "2026-05-01" },
    };
    expect(bindingStateText(stmt).text).toBe(
      "Re-derived on 2026-05-02 from a capture made on 2026-05-01.",
    );
  });

  it("document_only — 'Extracted from a document; no page capture.'", () => {
    const stmt = { ...base, binding_status: "document_only" };
    expect(bindingStateText(stmt).text).toBe(
      "Extracted from a document; no page capture.",
    );
  });

  it("legacy_synthetic — the run-level sentence; no per-record copy implied", () => {
    const stmt: StatementRow = {
      ...base,
      binding_status: "legacy_synthetic",
      recorded: { run_id: "run-9", at: "2026-05-02T00:00:00Z" },
    };
    const text = bindingStateText(stmt).text;
    expect(text).toBe(
      "Recorded by run run-9 on 2026-05-02. SIG did not keep a per-record " +
        "copy of the source for this run; the source's page lists the run " +
        "and its captures.",
    );
    // The sentence never implies SIG holds the source document (C4 NEW-2).
    expect(text).not.toMatch(/capture (of|from|made|kept)/i);
    expect(text.toLowerCase()).toContain("did not keep");
  });

  it("not_recorded — the named-absence fifth state, never a fabricated binding", () => {
    expect(bindingStateText(undefined).text).toBe(BINDING_STATE_TEMPLATES.not_recorded);
    expect(bindingStateText({ claim_id: "x", binding_status: "bogus_state" }).state).toBe(
      NOT_RECORDED,
    );
  });
});

describe("panelFromStatement — the contract shape", () => {
  it("emits sig.provenance-panel/1 with every J3 §5.2 field non-blank", () => {
    const panel = panelFromStatement(undefined, "c-missing");
    expect(panel.schema).toBe(PANEL_SCHEMA);
    expect(panel.binding_status).toBe(NOT_RECORDED);
    // Every field is a value or a named absence — never blank.
    const strings: string[] = [
      panel.binding_text,
      panel.source.id,
      panel.capture.retrieved_at,
      panel.capture.digest,
      panel.capture.byte_size,
      panel.capture.media_type,
      panel.upstream.display,
      panel.view_original.label,
      panel.extraction,
      panel.directness,
      panel.epistemic_review.reliability,
      panel.epistemic_review.integrity,
      panel.epistemic_review.review,
      panel.contradictions.display,
      panel.supersession,
      panel.rights.spdx,
      panel.rights.attribution,
      panel.equivalent_requests.api_status,
    ];
    for (const s of strings) {
      expect(s.length).toBeGreaterThan(0);
    }
    expect(panel.epistemic_review.review).toBe(NOT_YET_REVIEWED);
    expect(panel.equivalent_requests.api_status).toBe("unavailable");
  });

  it("upstream: the S-6 forms map to display + href honestly", () => {
    const mk = (upstream: StatementRow["upstream"]) =>
      panelFromStatement({ claim_id: "c", source_id: "s", upstream }, "c").upstream;
    expect(mk({ status: "full_url", url: "https://a.gov/x", host: "a.gov" })).toEqual({
      status: "full_url",
      display: "https://a.gov/x",
      href: "https://a.gov/x",
    });
    const hostOnly = mk({ status: "host_only", host: "a.gov", path_sha256: "deadbeef" });
    expect(hostOnly.display).toBe("a.gov#path_sha256:deadbeef");
    expect(hostOnly.href).toBe("https://a.gov/");
    expect(mk({ status: "withheld_by_policy" }).href).toBeNull();
    expect(mk({ status: "withheld_by_policy" }).display).toBe("not_publishable");
    expect(mk(null).display).toBe(NO_UPSTREAM_URL);
    expect(mk(null).href).toBeNull();
  });

  it("internal links route through withBase()", () => {
    const panel = panelFromStatement(undefined, "c1");
    expect(panel.source.href).toBe(withBase("sources/"));
    expect(panel.dispute_href).toBe(withBase("dispute/"));
    expect(panel.source.href).toBe(`${BASE.replace(/\/+$/, "")}/sources/`);
  });

  it("review wording: 'Not yet independently reviewed' while unreviewed/not_run", () => {
    for (const rs of ["unreviewed", "not_run", undefined]) {
      const panel = panelFromStatement(
        { claim_id: "c", epistemics: { review_status: rs ?? null } },
        "c",
      );
      expect(panel.epistemic_review.review).toBe(NOT_YET_REVIEWED);
    }
    const reviewed = panelFromStatement(
      { claim_id: "c", epistemics: { review_status: "curator_reviewed" } },
      "c",
    );
    expect(reviewed.epistemic_review.review).toBe("curator_reviewed");
  });

  it("supersession + contradictions render when recorded, named absence when not", () => {
    const panel = panelFromStatement(
      {
        claim_id: "c",
        supersession: {
          revises_claim: "old-claim",
          retraction_of: null,
          prior_recorded_at: "2026-01-01T00:00:00Z",
        },
        contradictions: {
          contradiction_ids: ["contra-1"],
          competing_claim_ids: ["other-claim"],
        },
      },
      "c",
    );
    expect(panel.supersession).toBe("revises old-claim (recorded 2026-01-01T00:00:00Z)");
    expect(panel.contradictions.display).toBe(
      "contradiction contra-1; competing other-claim",
    );
    expect(panelForClaim(new Map(), "c").supersession).toBe(NOT_RECORDED);
  });
});

describe("the component — one markup, every surface", () => {
  it("renders all 16 J3 §5.2 field labels with no blank <dd>", () => {
    const html = render(panelFromStatement(STATEMENT_FIXTURES[0], "active-device-count"));
    for (const label of FIELD_LABELS) {
      expect(html).toContain(`<dt>${label}</dt>`);
    }
    expect(html).not.toContain("<dd></dd>");
    expect(html).toContain("data-provenance-panel");
    expect(html).toContain('data-binding-state="actual_capture"');
    // The verbatim wording renders inside the panel.
    expect(html).toContain("Captured from records.example.gov");
  });

  it("the #claim-<id> anchor lands on the panel; anchor={false} omits it", () => {
    const panel = panelFromStatement(undefined, "c-1");
    expect(render(panel, true)).toContain('id="claim-c-1"');
    expect(render(panel, false)).not.toContain('id="claim-');
  });

  it("cross-surface consistency: one statement → identical contract + wording", () => {
    // UXR-33's acceptance shape: the same claim through the index lookup
    // (edge list / island path) and the direct call (claim viewer / record
    // page path) yields the identical contract — a divergent wording is a
    // defect, not a variant.
    const stmt = STATEMENT_FIXTURES.find((s) => s.claim_id === "claim:okc-rtcc-mou")!;
    const viaIndex = panelForClaim(new Map([[stmt.claim_id, stmt]]), stmt.claim_id);
    const direct = panelFromStatement(stmt, stmt.claim_id);
    expect(viaIndex).toEqual(direct);
    expect(viaIndex.binding_text).toContain("SIG did not keep a per-record copy");
    // Identical markup modulo the anchor attribute.
    expect(render(viaIndex, false)).toBe(render(direct, false));
  });

  it("fixture index exercises all four binding states", () => {
    const states = new Set(
      STATEMENT_FIXTURES.map((s) => panelFromStatement(s, s.claim_id).binding_status),
    );
    for (const s of ["actual_capture", "replayed", "document_only", "legacy_synthetic"]) {
      expect(states.has(s)).toBe(true);
    }
    // and the absent claim renders the honest fifth.
    expect(panelForClaim(new Map(), "claim:never-recorded").binding_status).toBe(
      NOT_RECORDED,
    );
  });
});
