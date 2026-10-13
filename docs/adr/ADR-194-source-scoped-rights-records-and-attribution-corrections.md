# ADR-194 — Source-scoped rights records and append-only attribution corrections (P34.21a)

- Date: 2026-10-03
- Status: accepted
- Ticket: P34.21a (Round 11 / P34, row 223; answers E2-12; fixes defect F-387)
- Base: `r11/P34.20-watch-and-evidence-empty-state-truth` (Round-11 chain)
- Related: ADR-095 (the append-only `rights_decision` log this extends —
  qualified, not rewritten), ADR-094 (the rights-resolution decision), ADR-002
  / P1–P3 (append-only), ADR-183 (express-terms posture — unaffected),
  SIG-LIC-004a (compartment model keyed on rights records), SIG-LIC-010/011
  (computed export licence + downstream obligations), SIG-CONTRIB-020 (every
  claim's upstream is named), E2-12 (missing/wrong upstream attribution is a
  defect), Part VIII §0.7 (reviewer roles, never names).

## Context

`PgClaimSink._rights_id()` keyed its rights-record lookup on
`spdx_expression` **alone** (and, in later versions, on SPDX + a reused record
that carried whatever attribution the FIRST claimant of that licence had).
The defect (F-387): two sources sharing a licence — e.g. CC-BY-4.0 — were
reused onto a single `rights_record`, so the record's `attribution_text`
("DeFlock community map") stamped onto every other source's claims
mis-crediting them, while sources whose connector emitted no attribution
recorded `attribution_text NULL`. The result contradicts SIG-CONTRIB-020
(every claim's upstream is named) at the record level the API, exports, map,
and LICENCES surfaces all read.

Two failure shapes exist on the spine:

1. **Resolved records carrying wrong/empty attribution.** A decided
   `rights_record` (redistributable = 'yes') stamped with the wrong credit —
   an append-only record that cannot be edited (SIG-STORE-011).
2. **Recorded `rights_id`s shared across sources.** The claim's recorded
   `rights_id` is assertion-time provenance — honest *at assertion* that the
   sink resolved it — so the fix is not a re-assert and never an `UPDATE`
   (forbidden); it is a recorded correction under the ADR-095 mechanism.

## Decision

1. **The sink resolves rights per source tuple.** `PgClaimSink._rights_id()`
   keys on `(source_id, spdx, attribution, terms_url)` — never SPDX alone.
   Two sources sharing a licence but differing in attribution/terms mint
   distinct `rights_record`s; claims whose full tuple agrees dedupe onto one
   record (the record itself stays source-agnostic — the source linkage lives
   on claims, artifacts, and the registry). The match-first read on the full
   tuple keeps replays idempotent; a non-matching tuple is an `INSERT`,
   append-only.
2. **The registry fills absent claim rights fields.** A `rights_resolver`
   (wired by `connectors.sinks.make_claim_sink` from `sources.toml`) supplies
   the source's own reviewed `(spdx, attribution, terms_url,
   redistributable, derivative_permitted)` when a claim omits them —
   claim-carried fields always win (assertion-time provenance); an
   unregistered source resolves nothing and the claim stands alone. An
   unreviewed source records `UNDETERMINED` redistributability (honest
   undecided posture — `no` would record a review that never happened) so a
   later decision can lift it.
3. **Corrections are a second decision kind on `rights_decision`.** A
   source-scoped *attribution-correction* decision
   `(source_id, prior_rights_id) -> corrected_rights_id` where the corrected
   record keeps the prior's `spdx_expression`, `redistributable`, and
   `derivative_permitted` — **only `attribution_text`/`terms_url` change** —
   so a correction can never relicense a resolved record (the writer refuses
   any row that would, loudly, before writing). Recorded licence-identifier
   normalisations (e.g. `OGL-3.0` → `OGL-UK-3.0`) are declared per row in the
   committed artifact's `spdx_aliases` — the same licence text under its
   canonical id, not a silent relabel. `UNDETERMINED` priors resolve under
   the ADR-095 lift semantics unchanged.
4. **The backfill is `sig-db attribution-corrections`.** A dry-run-by-default
   verb reading a committed, reviewer-prepared corrections artifact
   (generated from `sources.toml` by `sig-connectors
   attribution-correction-list`); `--apply` writes INSERT-only rows
   (`rights_record` + `rights_decision`), idempotent on
   `(source_id, prior_rights_id, resolved rights_id)`, reporting the pre/post
   empty-attribution claim counts the hosted leg records. Each row carries
   `source_id`, `spdx`, `attribution`, `terms_url`, `basis` (names E2-12 +
   ADR-194), `reviewed_by` (a role, never a name — Part VIII §0.7),
   `reviewed_on`, `retrieval_date`, and `review_packet`.
5. **Publish-time gate.** Export preparation and `publish-web` both fail
   closed when any row carries `attribution_required` (the licence-level
   fact from `licenses.toml`) with empty effective attribution — before any
   public sync.

## Consequences

- Every reader that resolves effective rights through ADR-095's
  `(source_id, prior_rights_id)` rule — `api.store_pg.rights_for`,
  `exports.audit`, export shaping — sees the corrected per-source attribution
  with no reader change: the decision is a new row in the same table the
  rule already reads.
- Nothing is ever relicensed: a correction changes attribution/terms text on
  a record, never the licence or redistributability of a resolved record
  (writer-refused); an UNDETERMINED prior resolves under ADR-095 unchanged.
- The hosted backfill is an additive leg (`rights_record` +
  `rights_decision` INSERTs) — `n_tup_upd`/`n_tup_del` on the spine tables
  are unchanged, verified in the read-back.
- A claim recorded under the shared record keeps its assertion-time
  provenance intact; the correction names the source it now correctly
  credits.

## Alternatives considered

- **`UPDATE rights_record.attribution_text`.** Rejected — forbidden by the
  append-only invariant; erases the record of what was asserted.
- **Re-assert every claim under corrected `rights_id`s.** Rejected — the
  claims carry no wrong content; the mis-recording is metadata the decision
  mechanism exists to correct, and re-assertion doubles claim volume for a
  governance event.
- **A per-claim decision kind.** Rejected for this defect — the mis-recorded
  sources are enumerable and the correction is naturally source-scoped;
  per-claim granularity is the ADR-095 revisit trigger if a later defect
  needs it.

## Revisit trigger

- A rights reviewer finds a source needs a *different* corrected signature
  (not the committed artifact's row) — append a NEW corrections row + new
  `rights_decision`; never edit a landed row.
- The defect recurs through a path the tuple key does not cover (e.g. a claim
  asserting a non-registry terms_url) — extend the key or the resolver in a
  new ADR.
- A corrected record's attribution is itself later found wrong — a new
  correction decision row; the earlier row stays as the record of the
  earlier decision.
