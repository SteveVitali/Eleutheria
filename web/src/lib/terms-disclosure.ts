// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
/**
 * The express-terms disclosure contract (P34.19, F-403, ADR-183).
 *
 * Each express-terms source the operator chose to keep public discloses its
 * captured terms verbatim and the basis on which its rows are published — the
 * operator's recorded acceptance of the express-terms risk (ADR-183), which
 * the operator extended to scheduled refreshes of the same sources (SB-2;
 * a NEW source with a non-commercial clause follows A-9 — facts and pointers
 * only). The export emits it as `web/terms_disclosure.json`
 * (`sig.terms-disclosure/1`); P34.17's interim sources-and-licences page is
 * the first consumer.
 */

export interface TermsDisclosureOperatorWords {
  key: string;
  text: string;
  recorded_at: string;
  round?: number;
}

export interface TermsDisclosureBasis {
  adr: string;
  operator_words: TermsDisclosureOperatorWords[];
  adopted_sentence: string;
  adopted_sentence_sha256: string;
  new_source_rule: string;
}

export interface TermsDisclosureSource {
  source_id: string;
  name: string;
  spdx_registry: string | null;
  terms_url: string;
  terms_retrieval_date?: string;
  captured_terms_verbatim: string;
  captured_terms_evidence: string;
  capture_note?: string;
  publication_basis: string;
  refresh_scope?: string;
  /** The acceptance-time public row count (ADR-183 record). */
  public_row_count?: number;
  /** This export's computed row count for the source. */
  export_row_count?: number;
}

export interface TermsDisclosure {
  schema: "sig.terms-disclosure/1";
  as_of?: string;
  generated_at?: string;
  basis: TermsDisclosureBasis;
  sources: TermsDisclosureSource[];
}

export function isTermsDisclosure(value: unknown): value is TermsDisclosure {
  const o = value as TermsDisclosure | null;
  return !!o && o.schema === "sig.terms-disclosure/1" && Array.isArray(o.sources) && !!o.basis;
}

/**
 * The fixtures-mode demo disclosure: one synthetic source, marked as a
 * demonstration (`demo-` id + demo name) so a fixtures build never reads as
 * real data (§3.1). It exercises the contract; the real artifact names the
 * eight ADR-183 sources verbatim.
 */
export const TERMS_DISCLOSURE_FIXTURE: TermsDisclosure = {
  schema: "sig.terms-disclosure/1",
  basis: {
    adr: "docs/adr/ADR-183-express-terms-acceptance.md",
    operator_words: [
      { key: "A-8", text: "Keep all, accept risk", recorded_at: "2026-10-01T04:07:45Z", round: 4 },
      { key: "A-8 wording", text: "Keep everything as is", recorded_at: "2026-10-01T04:09:43Z", round: 5 },
      { key: "SB-2", text: "Yes, same sources (Recommended)", recorded_at: "2026-10-01T13:46:58Z", round: 27 },
    ],
    adopted_sentence:
      "I accept the express-terms risk for all ≈8,088 currently public rows, including the non-commercial ones; A-9 applies to new sources only.",
    adopted_sentence_sha256: "cd76b74e872db8dcc118c0cda0355fa505524a7bc8730e5f21df23be171f2fb4",
    new_source_rule:
      "a new source with a non-commercial clause follows A-9 — facts and pointers only",
  },
  sources: [
    {
      source_id: "demo-express-terms-source",
      name: "Demo municipal camera registry (demonstration entry)",
      spdx_registry: "LicenseRef-OperatorAccepted-DBRight",
      terms_url: "https://example.invalid/demo-registry",
      captured_terms_verbatim:
        "Demo purposes only — this demonstration entry shows the sig.terms-disclosure/1 shape.",
      captured_terms_evidence: "fixtures (demonstration)",
      publication_basis: "operator-accepted express terms (ADR-183)",
      refresh_scope:
        "scheduled refreshes of this same source are covered by the acceptance (SB-2, 2026-10-01T13:46:58Z)",
      export_row_count: 0,
    },
  ],
};
