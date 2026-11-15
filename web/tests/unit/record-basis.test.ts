// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * P37.39 (R11-K13-QB-01, L3 §5.2, SIG-CONF-011) — the sig.record-basis/1
 * contract: the six states render verbatim or as named absences, never
 * fabricated.
 */

import { renderToString } from "preact-render-to-string";
import { createElement } from "preact";
import { describe, expect, it } from "vitest";

import { RecordBasisRows } from "../../src/components/RecordBasisRows";
import {
  CHECKED_BY_TEXT,
  basisRows,
  evidenceText,
  locationCheckText,
  recordBasis,
  technologyText,
} from "../../src/lib/record-basis";

const VERBATIM_COPY =
  "Also published by Oklahoma camera registry (a copy of the same upstream record, id OKREG-1187, checked automatically).";
const VERBATIM_DUP =
  "Possible duplicate: DeFlock ALPR map lists a camera 18 m away. SIG has not merged them because it cannot prove they are the same device.";

const DEDUP = {
  site_id: "device:okc-002",
  copies: [{ record: "device:okc-002-copy", source_name: "Oklahoma camera registry", display: VERBATIM_COPY }],
  possible_duplicates: [{ record: "device:okc-006", source_name: "DeFlock ALPR map", distance_m: 18, display: VERBATIM_DUP }],
  multi_view: [],
  n_independent_lineages: 2,
  n_independent_lineages_display: "Seen independently by 2 sources: Oklahoma City ALPR feed, Oklahoma camera registry.",
};

describe("recordBasis — the sig.record-basis/1 normalisation", () => {
  it("carries the verbatim entry displays and lineage text", () => {
    const b = recordBasis(DEDUP, { placementCheck: "consistent", jurisdictionName: "Oklahoma City", technology: "alpr-fixed", technologyStatus: "resolved" })!;
    expect(b.site_id).toBe("device:okc-002");
    expect(b.copies[0]!.display).toBe(VERBATIM_COPY);
    expect(b.possible_duplicates[0]!.display).toBe(VERBATIM_DUP);
    expect(b.lineages_text).toContain("Seen independently by 2 sources");
    expect(b.location_check).toBe("Location checked: inside Oklahoma City.");
    expect(b.technology).toBe("Technology: alpr-fixed, from the source's layer description.");
    expect(b.checked_by).toBe(CHECKED_BY_TEXT);
  });

  it("null dedup → null basis (sparse, never fabricated)", () => {
    expect(recordBasis(null)).toBeNull();
    expect(recordBasis(undefined)).toBeNull();
  });

  it("absence objects ride through as named absences", () => {
    const b = recordBasis({
      site_id: { not_recorded: "no completed camera-site ER run" },
      copies: { not_recorded: "no completed camera-site ER run" },
      possible_duplicates: { not_recorded: "no completed camera-site ER run" },
      multi_view: { not_recorded: "no completed camera-site ER run" },
      n_independent_lineages: { not_evaluable: "claim_lineage read absent" },
    })!;
    expect(b.site_id).toBeNull();
    expect(b.site_absence).toContain("no completed camera-site ER run");
    expect(b.copies_absence).toContain("no completed camera-site ER run");
    expect(b.lineages_text).toBeNull();
    expect(b.lineages_absence).toContain("claim_lineage read absent");
  });
});

describe("state sentences — L3 §5.2 forms", () => {
  it("location check: inside / conflict / withheld / absent", () => {
    expect(locationCheckText("consistent", "Oklahoma City")).toBe("Location checked: inside Oklahoma City.");
    expect(locationCheckText("outside_declared", "Oklahoma City")).toContain("Location conflict:");
    expect(locationCheckText("outside_declared", "Oklahoma City")).toContain("shown, not counted there");
    expect(locationCheckText("axis_swap_suspected")).toContain("withheld");
    expect(locationCheckText(null)).toContain("not_recorded");
  });

  it("technology: declared slug + honest states", () => {
    expect(technologyText("alpr-fixed", "resolved", "OKC feed")).toBe("Technology: alpr-fixed, from OKC feed's layer description.");
    expect(technologyText(null, "conflicted")).toContain("conflicted declarations");
    expect(technologyText(null, "unreported")).toContain("unreported");
    expect(technologyText(null, null)).toBe("Technology: not_recorded.");
  });

  it("evidence: fetched date + copy-kept state, or named absence", () => {
    expect(evidenceText("OKC feed", "2026-07-01T14:22:00Z", true)).toBe("Evidence: OKC feed, fetched 2026-07-01; copy kept: yes.");
    expect(evidenceText("OKC feed", "2026-07-01", false)).toContain("copy kept: no");
    expect(evidenceText(null, null)).toContain("not_recorded");
  });
});

describe("basisRows — the render order", () => {
  it("emits all eight states in order with entry displays", () => {
    const rows = basisRows(recordBasis(DEDUP)!);
    expect(rows.map(([l]) => l)).toEqual([
      "Camera site",
      "Copies",
      "Possible duplicates",
      "Multi-view",
      "Corroboration",
      "Location check",
      "Technology",
      "Evidence",
      "Checked by",
    ]);
    expect(rows[1]![2]).toEqual([VERBATIM_COPY]);
    expect(rows[2]![2]).toEqual([VERBATIM_DUP]);
  });
});

describe("RecordBasisRows — one markup, every surface", () => {
  it("renders the basis section with the verbatim sentences", () => {
    const html = renderToString(
      createElement(RecordBasisRows, { basis: recordBasis(DEDUP, { placementCheck: "consistent", jurisdictionName: "Oklahoma City" })! }),
    );
    expect(html).toContain('data-basis="record"');
    expect(html).toContain(VERBATIM_COPY);
    expect(html).toContain(VERBATIM_DUP);
    expect(html).toContain("Location checked: inside Oklahoma City.");
    expect(html).toContain("Not reviewed by a person.");
    expect(html).not.toContain("<dd></dd>");
  });

  it("renders named absences, never blanks, on a no-run block", () => {
    const html = renderToString(
      createElement(RecordBasisRows, {
        basis: recordBasis({
          site_id: { not_recorded: "no completed camera-site ER run" },
          copies: { not_recorded: "no completed camera-site ER run" },
          possible_duplicates: { not_recorded: "no completed camera-site ER run" },
          multi_view: { not_recorded: "no completed camera-site ER run" },
          n_independent_lineages: { not_evaluable: "claim_lineage read absent" },
        })!,
      }),
    );
    expect(html).toContain("not_recorded");
    expect(html).toContain("not_evaluable");
    expect(html).not.toContain("<dd></dd>");
  });
});
