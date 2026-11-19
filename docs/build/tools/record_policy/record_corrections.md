# Source-bound record corrections

This mechanism requires explicit operator approval before adoption. It extends
the append-only correction approach in ADR-146 decisions 1–2 and 7 without
restamping a historical event, editing a signed text, or changing acceptance.
It is not a general exception to R1, PHASE LOG shape, or history enforcement.

## Register and provenance

`docs/build/reports/memory-repair/record_corrections.jsonl` contains one
`record-correction/1` object per line. It is append-only even before landing.
The exact fields are `schema`, `kind`, `recorded_at`, `path`, `source_commit`,
`source_line`, `line_sha256`, and `interpretation`. Unknown fields/kinds,
duplicate JSON keys, malformed entries, and duplicate targets fail closed.

`source_commit` is the full 40-character introducing commit, verified by blame
and required to be an ancestor of the judged revision. `source_line` is its
one-based line number in that commit. `line_sha256` hashes that line's UTF-8
bytes without its newline. The original line must occur exactly once in both its source snapshot and
the current target file. No match, changed bytes, or multiple matches fail.

`recorded_at` is the actual UTC clock reading when writing the correction,
including seconds. It cannot precede the source commit, exceed the current
clock plus the existing five-minute tolerance, or exceed the correction's own
introducing commit by that tolerance. An invalid entry disables all correction
effects and produces a hard finding; an absent register changes no behavior.
Historical revision checks read that revision's register, never a future one.

## Exactly three supported interpretations

1. **`readout-pointer-date`.** Only a line with the exact form
   `GATE DECISIONS row: <UTC timestamp> | <GATE id>` in a direct Markdown
   readout may qualify. Its original date must be more than five minutes after
   its introducing commit. Its retained pointer must identify exactly one
   `decision` row by exact date and ticket cells in GATE DECISIONS. The only
   interpretation field is `recorded_at_or_before`, which must equal that
   verified commit's timestamp. The memory guard emits an `R1-corrected`
   warning instead of that one R1 error. This is an upper bound on recording,
   **not an inferred drafting, decision, receipt, or event time**. The original
   pointer remains the key of the original row. No gate decision or signature
   check is bypassed, and other dates still fail under their original rules.
2. **`gate-row-recording-date`.** Only a seven-cell GATE DECISIONS row whose
   kind is `decision` or `confirmation` may qualify. Its date cell must exceed
   the introducing commit time by more than five minutes; the exact same
   source, hash, surviving-line and `recorded_at_or_before` requirements apply.
   A unique decision with the same date and gate ticket must remain present.
   This corrects only the recording-time interpretation. The signed answer,
   consequence, kind, original date key and gate decision remain unchanged.
   Pause ordering also uses this verified upper bound: a pause after it cannot
   borrow the erroneous later date to pass. Waivers, pre-authorizations, other
   record kinds, and event-time substitutions are unsupported.
3. **`phase-log-heading-markup`.** Only an existing PHASE LOG bullet with
   markup inside its heading may qualify. `interpretation.heading` must be
   exactly the original heading with `*`, `_`, and backticks removed. The id,
   kind, payload, date, and all original bytes remain intact. The ledger
   validator emits `markup-corrected` instead of that line's `markup-id` error;
   every other shape and history rule still evaluates the original record.

No kind accepts arbitrary replacement text, a waiver, a new gate outcome,
or an assertion that a historical event happened at the commit time. Corrections
do not cure unrelated lines. Their warnings keep the original defects visible.

## The proposed GATE-ACCEPT-R11 use

The readout pointer's `2026-11-19T06:55Z` token names the original GATE DECISIONS
row. Its introducing operator-signed commit `ede12a67` was committed at
`2026-11-19T06:33:52Z`; the readout separately records receipt of the operator's
words at `2026-11-19T06:29Z`. The existing PHASE LOG correction already reports
the projected 06:55 stamp and preserves the signed bytes. This register makes
that recording-time upper bound machine-verifiable. It does not claim the
approximate drafting time mentioned in that PHASE LOG note is a known clock
reading. Two further source-bound entries apply the same upper bound to the signed
decision and confirmation date cells, exposed when their detached rows rejoin
the table. The operator quote, signature, original pointer, gate rows, acceptance,
open obligations and CURRENT STATE are unchanged.

The heading entry interprets the existing `dispatch boundary-confirm + **GATE
PAUSE**` heading with its markup removed; the original PHASE LOG entry remains
byte-identical. Separately, deleting one empty line joins the two existing gate
rows to their original Markdown table. No row bytes or order change, and this
whitespace-only operation passes the original append-only guard without any
correction entry or exception. It also exposes the rows to the existing date
and pause checks; the new findings are corrected explicitly, not hidden.

The gate-ID parser additionally recognizes the full `GATE-ACCEPT-R<n>` token.
Previously it truncated `GATE-ACCEPT-R11` to `GATE-ACCEPT`, then rejected the
remaining suffix when matching the already-recorded pause. This grammar repair
uses the original pause evidence. A different gate, different round, missing
pause, or pause after the decision still fails. It does not add a new pause or
reclassify a decision as pre-authorization. The build README range advances to
the already-present row 504.

## Review and validation boundary

Adoption changes checker policy and must be reviewed as such. Local synthetic
tests exercise provenance, ambiguous/unrelated/unsupported targets, timestamp
bounds, semantic header changes, retained history, and existing negative
controls. Historical errors remain errors when replayed before the correction.
Full exact-head hosted CI and the required independent quality checks are still
required after an approved deployment; a local proposal is not readiness.
