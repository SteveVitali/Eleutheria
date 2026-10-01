# ADR-126 — Evidence-backed obligation events and the deterministic current projection (P32.7)

- Date: 2026-10-14
- Status: accepted (engineering; offline-only — shadow mode, no control-state writes)
- Ticket: P32.7 (Round 10 / S6, row 167; requirement SIG-MEM-002; annotates `D-R10-MEMORY-1`)
- Base: `c8d2856` (the P32.6 closeout tip `devin/p32-6-legacy-evidence-audit-and-recovery-plan`, PR #161)

## Context

SIG-MEM-002 (§55.7) requires that current obligation and requirement assessments be derived
from explicit, evidence-backed transitions — not from whichever token happens to appear last
in a cell — and that a deterministic current-state view record its input hashes and detect
staleness without ever writing the control ledger. Four pressures shaped the design:

1. **The status cells genuinely disagree with themselves.** P32.1's audit found four
   DEFERRALS rows whose leading token (`OPEN`/`PARTIAL`) contradicted a dated `DONE` later in
   the same cell — and P32.2/P32.4/P32.5 created three more of the same shape by appending
   verified closures without flipping the leading token. A naive reader and a careful reader
   get different answers; the register needs recorded interpretations, not silent picks.
2. **Old values must survive.** The defining standard (§3) forbids silent overwrites: a
   flipped cell must carry the evidence for the flip, and the pre-flip raw text must be
   recoverable — so each migrated row carries an anchor with its original `row_sha256`.
3. **The view must be derivable and bounded.** An orientation view that grew with the
   register would eventually stop orienting; conversely a capped view that dropped obligations
   would lie by omission. Both failure modes must be structurally impossible.
4. **There can only be one writer — eventually.** P32.1 showed `/tmp` side-channel state and
   two plausible status surfaces; this ticket adds events/projections in **shadow mode**
   (advisory, never consulted by the authority) while `D-R10-MEMORY-1` stays `OPEN` — the
   enforced single-writer protocol and entry-point cutover are P32.8's contract, not this
   ticket's.

## Decision

**Four schemas + two tools, all append-only, all deterministic, all advisory.**

### `obligation-event/1` (`docs/build/reports/obligations/events.jsonl`)

One JSON object per line. Fields: `schema, event_id (<obligation>:e<seq>), kind
(migration|transition), obligation_id, seq, expected_previous_event, from_status,
to_status, ticket_id, owner, landing, backlog_home, evidence_refs, observed_at,
recorded_at, source_commit, reason`, plus `anchor{row_line,row_sha256,parser_status,
prose_terminal,interpretation}` on migration events.

- Every DEFERRALS obligation carries exactly **one migration anchor** (`kind: migration`,
  `seq: 0`, `expected_previous_event: null`) recording the raw cell status and digest at
  migration; every later status change is a `transition` chaining on
  `expected_previous_event`. The checker rejects: duplicate ids, duplicate/missing anchors,
  transitions with missing/unknown predecessors, competing heads extending the same
  predecessor, empty or nonexistent evidence refs, transitions whose only evidence is the
  register itself, owed heads without owner/landing, and cells whose leading token disagrees
  with the event head (`events/cell-divergence` — cells may move **only** after matching
  transition evidence exists).
- `recorded_at`/`observed_at` are fixed `YYYY-MM-DD` inputs — semantic payloads never embed
  wall-clock time (the wall clock lives in the projection receipt).
- `obligation_events.py append` is the shadow writer: it validates the whole chain and
  appends only if clean, tolerating precisely the cell-divergence the appended event itself
  is evidence for (the cell update follows the event, never precedes it).

### `coverage-assessment/1` (`coverage_assessments.jsonl`)

Scoped verdicts: `schema, assessment_id, requirement_id, verdict, domain, code_revision,
evidence_refs, limitations, assessor, assessed_at, supersedes, seq`. Scope is
`(requirement_id, domain)` over the five evidence domains
(fixture → implementation → composed-db → hosted → public). The checker rejects: duplicate
ids, missing fields, unknown spec requirement ids, empty/nonexistent evidence, competing
non-superseded heads in one scope, `supersedes` pointing outside the scope or at nothing,
`MET`/`MET-DIFFERENTLY` backed **only** by planning documents
(`docs/build/planning/`, `docs/tickets/` — a plan saying "will be built" never proves built),
and **domain override**: a `MET` head in a narrower domain while a wider domain holds a
current non-`MET` verdict — the fixture-pass-over-hosted-failure case is a hard error.

Historical `COVERAGE_MATRIX.csv` rows are **not** migrated or rewritten; they appear in the
projection labelled `historical/csv` — dated assessments preserved verbatim.

### `input-manifest/1` + `current-projection/1` (`docs/build/reports/current/`)

`current_projection.py generate` writes `manifest.json`, `current.json`, `CURRENT.md`
(+ `obligations-N.md` spill pages when needed) and `receipt.json`; `verify` recomputes
every recorded digest and regenerates the payload.

- The manifest enumerates its inputs explicitly (core files + glob expansion over the
  audit's read set — tickets, ADRs, readouts, run ledgers) with a SHA-256 each, plus
  `input_commit`. Generated outputs under `reports/current/` are structurally excluded —
  the manifest is acyclic by construction; a change to any input makes `verify` report the
  stale digests and exit nonzero.
- The projection runs `audit_current_state.py` **and** the event/assessment checkers over
  the same hashed inputs and folds every remaining diagnostic into
  `known_inconsistencies` — preserved, never synthesized; any nonempty list marks the
  output `incomplete` and exits nonzero (bounded conflicted report, never a silent answer).
  Reconciliations are enumerated from the event store (`interpretation: reconciled` /
  `ambiguous-open`) and `reconciliations.json` (the eight documented P32.1 conflicts).
- `CURRENT.md` is capped at 250 lines / 20 KiB. When the owed-obligations table (or any
  table) would exceed the budget it moves to `obligations-N.md` link-out pages —
  complete, nothing dropped; the JSON projection always carries everything.
- `receipt.json` is the only file with wall-clock data (`generated_at`); it is a receipt,
  never an input, never part of the deterministic payload.

### The seven recorded reconciliations

The four P32.1 conflicts plus the three same-class rows created afterward by
P32.2/P32.4/P32.5 were each read against their linked evidence. Recorded interpretations:
`D-P21.4-3`, `D-SOURCES.2-4`, `D-R7.3-BREADTH`, `D-P31.1-1`, `D-P31.1-3`, `D-P31.5-2` →
`DONE` (compatibility cells flipped to match; old values preserved on the anchors and
verbatim in the cells). `D-P21.5-1` → `PARTIAL` — the dated DONEs are per-leg discharges;
the owed residue is the operator's repo-visibility decision for the SWH save-now leg, so
the cell stays `PARTIAL` and the conflict stays deliberately visible. Anything genuinely
ambiguous would have recorded `ambiguous-open` and stayed owed.

### Shadow boundary

Nothing here writes `LEDGER.md`, `DEFERRALS.md` (beyond the recorded cell updates this
ticket itself performed), `COVERAGE_MATRIX.csv`, `BUILD_INDEX.md` or `00_MANIFEST.md`.
The projection is advisory; `D-R10-MEMORY-1` stays `OPEN` and P32.8 owns the enforced
single-writer protocol and entry-point cutover.

## Consequences

- Current status = event-chain head; the compatibility cell is a cached rendering that the
  checker forces into agreement. No "last token wins".
- Any new conflicted row migrates as `unreconciled-conflict`: it stays owed with an owner
  and fails `check`/`verify` until a ticket records the interpretation.
- `docs/build/reports/current/` regenerates deterministically; `verify` is the stale-input
  detector for every hashed source.

## Revisit trigger

- **P32.8 cutover (`D-R10-MEMORY-1`):** when the single-writer protocol lands, the shadow
  `append` path becomes the enforced writer, `check` joins closeout, and this ADR's
  shadow-mode statements get superseded by the cutover ADR.
- **A second transition surface:** any new tool that writes obligation status outside the
  event chain would recreate the competing-authority defect this ADR removes — reject it
  or record the change here first.
- **A new conflict class:** if a reconciliation ever needs a verdict other than the
  recorded set (`DONE`/`PARTIAL`/`ambiguous-open`), extend `RECONCILIATIONS` semantics in a
  new ADR rather than stretching this one.

### Trigger evaluation — SEED-11 (Round 11 T1, 2026-10-01): LIKELY FIRED

Evaluated at Round-11 Stage B, T1 (unit SEED-11d, 2026-10-01T07:49:22Z) from F3 §5.1
(`docs/build/planning/2026-09-30-next-phase/research/F3-backlog.md`) and the Round-11 plan
(`docs/build/planning/2026-09-30-next-phase/NEXT_PHASE_PLAN.md`); an agent evaluation, not an operator
decision. **The trigger likely fired:** status is still hand-edited in DEFERRALS — 97 anchors and 0
transitions (F-26), anchored at 10-21 (B1 NEW-7; F3 §5.1). **Answer:** row P34.8 (M3 obligation_events repair
+ correction/transition data) and ADR-148 (build memory v2.1), which supersedes this ADR's cutover statements
(status update below). The decision above stays in force until that answer lands; this ADR's body is unchanged
(SIG-ENG-003).

## Status updates

- **Status:** Superseded by ADR-148 (2026-10-01) — the D-R10-MEMORY-1 cutover statements only
- **Status note (2026-10-01, Round-11 T1, unit SEED-11d):** Per plan §7 row 148, ADR-148 (build memory v2.1)
  splits D-R10-MEMORY-1 (B3 option C) and supersedes this ADR's statements about the P32.8 cutover; the
  obligation-event and projection design stands. The body above is unchanged (SIG-ENG-003).
