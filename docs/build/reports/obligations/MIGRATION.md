# Migration report — obligation-event anchors + the four P32.1 status-conflict reconciliations (P32.7)

**Schema:** `obligation-event/1` (one JSON object per line, `events.jsonl`) ·
**Tool:** `docs/build/tools/obligation_events.py migrate` (deterministic —
same inputs, same bytes) · **ADR:** ADR-126 · **Requirement:** SIG-MEM-002.

## Method

Every obligation row in `docs/tickets/DEFERRALS.md` (89 rows at the migration
input set) received exactly one **migration anchor** (`kind: migration`, `seq: 0`,
`event_id: <obligation>:e0`). The anchor carries:

- `from_status` — the raw parser status (the cell's leading token at migration);
- `to_status` — the recorded interpretation;
- `anchor.row_sha256` + `anchor.row_line` — the original raw digest and location of
  the migrated row, so the historical cell is preserved verbatim even when the
  compatibility cell later changes;
- `anchor.parser_status` / `anchor.prose_terminal` — the two sides of any
  disagreement, kept visible;
- `evidence_refs` — the linked evidence the interpretation was read from;
- `owner` / `landing` / `backlog_home` — the recorded owner and scheduled landing
  (from the dated owner/landing sweep tables first, then the row's own
  `owner …`/`unblocked by` text, then the BL-nnn home).

Transitions beyond the anchor (`kind: transition`) chain on
`expected_previous_event` and are appended by the shadow writer
(`obligation_events.py append`); the single authoritative-writer protocol lands
at cutover (`D-R10-MEMORY-1` → P32.8).

## The four status-conflict reconciliations

P32.1's `audit_current_state.py` flagged four rows whose leading token disagreed
with a dated terminal token later in the same cell. Each was inspected against
its linked evidence; the recorded interpretation is below. No "last token wins":
the choice is the recorded `to_status` of an evidence-backed event, and both raw
values stay on the anchor forever.

| obligation | raw parser status | prose terminal | recorded interpretation | compatibility cell |
|---|---|---|---|---|
| `D-P21.4-3` | `OPEN` | `DONE 2026-09-16` | **DONE** — operator decided GO at the go-public checkpoint; GCP cut-over ran and was verified anonymously; the custom-domain leg was skipped-by-operator (recorded). Evidence: the cell's own dated record, `docs/build/reports/PUBLICATION_CHECKLIST.md`, `docs/build/LEDGER.md` gate decisions. | flipped `OPEN` → `DONE`, old value preserved on the anchor + in the cell text |
| `D-P21.5-1` | `PARTIAL` | `DONE 2026-09-16` | **PARTIAL** — the dated DONEs are *per-leg* discharges (Zenodo deposit 2026-09-15, GCS object-store push, live egress report); the Software Heritage save-now leg was DECLINED-BY-OPERATOR while the repo is private and reopens if visibility flips; a non-GCS object-store push remains optional. The owed residue is an operator decision. Evidence: `docs/build/reports/DEPOSITS.md`, `docs/build/LEDGER.md`. | stays `PARTIAL` (annotated with the recorded interpretation) |
| `D-SOURCES.2-4` | `PARTIAL` | `DONE 2026-09-19` | **DONE** — RESOLVED-BY-GL-GATE-08: the operator's recorded PrimeGov/robots disposition (P26.17) removed the gate, so the owed API-mode justification is moot. Evidence: `docs/build/runs/P26.17.md`, `docs/build/LEDGER.md`. | flipped `PARTIAL` → `DONE` |
| `D-R7.3-BREADTH` | `OPEN` | `DONE 2026-09-26` | **DONE** — all eight accountability-breadth sources landed: P31.12 wired+landed four, P31.13 the remaining four under digest-pinned hosted jobs (+0 re-runs, `rights_decision` rows, materialize +0). Evidence: `docs/build/runs/P31.12.md`, `docs/build/runs/P31.13.md`, `docs/build/reports/p31.13-hosted/VERIFICATION.md`. | flipped `OPEN` → `DONE` |

## The same class created after the baseline

The migration surfaced three more rows of the identical defect — P32.2, P32.4 and
P32.5 each appended a verified `DONE` record to the cell without flipping the
leading token (so they did not exist at the P32.1 baseline). Each is unambiguous
— named ticket, ADR and tests in the cell itself — so each received the same
recorded-interpretation treatment:

| obligation | raw parser status | prose terminal | recorded interpretation | compatibility cell |
|---|---|---|---|---|
| `D-P31.1-1` | `OPEN` | `DONE 2026-10-11` | **DONE** — P32.4/ADR-123 landed the trigger-maintained `spine_watermark` table (bounded by construction; invalidation verified for all three classes on real PG18; `p31-scale-local` fixture met the named budget). Composed/hosted latency evidence remains reserved to the P32.24/P33.2 e2e rows — the closure explicitly does not claim it. Evidence: `docs/build/runs/P32.4.md`, `docs/build/reports/p32.4-watermark/RESULTS.md`, `docs/adr/ADR-123-shared-bitemporal-occurrence-selection.md`. | flipped `OPEN` → `DONE` |
| `D-P31.1-3` | `OPEN` | `DONE 2026-09-28` | **DONE** — P32.2/ADR-121 §6: the entity route resolves each predicate independently; `unregistered_predicates` is explicit; registered facts flow through eligibility. Composed/hosted verification stays P33.2's. Evidence: `docs/build/runs/P32.2.md`, `docs/adr/ADR-121-typed-assertions-and-actual-capture-bindings.md`, `tests/api/test_api_unregistered_predicates.py`. | flipped `OPEN` → `DONE` |
| `D-P31.5-2` | `OPEN` | `DONE 2026-10-12` | **DONE** — P32.5/ADR-124: `publication-eligibility/1` + the `publication_disposition` registry withhold `publication_review_required` organisations from every public surface until a recorded `allow`; flag not declared moot; the owed operator allow-rows are recorded in ADR-124. Evidence: `docs/build/runs/P32.5.md`, `docs/adr/ADR-124-one-publication-eligibility-policy.md`, `tests/unit/test_publication_eligibility.py`. | flipped `OPEN` → `DONE` |

**Ambiguous rows stay open:** any future row whose raw status and dated terminal
disagree without a recorded interpretation migrates with
`interpretation: unreconciled-conflict`, keeps the parser status (owed) with an
owner, and surfaces as `events/unreconciled-conflict` (conflict severity — the
checker and the projection both fail until a ticket records the interpretation).

## What was NOT touched

- `docs/build/LEDGER.md` — still the control authority; nothing here writes it.
- Historical `COVERAGE_MATRIX.csv` rows — preserved verbatim; scoped verdicts live
  in `coverage_assessments.jsonl` (historical rows are labelled `historical/csv`
  in the projection, never rewritten).
- The P32.1 audit tool — consumed as-is (the projection runs it on the hashed
  input set); the two documented non-deferral conflict classes are recorded in
  `reconciliations.json`.
- `D-R10-MEMORY-1` — stays `OPEN`; this run annotated it with the shadow landing.

## Corrections (appended — ADR-146; original text untouched)

The entries below correct dates this report recorded on lines 55–57. The
lines above are never rewritten; the true dates are established by git/GitHub
timestamps and the date register (`docs/build/reports/memory-repair/
date_corrections.csv` L278–L280), and are additionally bound to the event log
by the appended `date-correction` events `D-P31.1-1:e0:dc-observed_at`,
`D-P31.5-2:e0:dc-observed_at` and the `dc-recorded_at` corrections.

| report line | obligation | recorded | true date (UTC) | basis |
|---|---|---|---|---|
| L55 | `D-P31.1-1` (`DONE 2026-10-11`) | 2026-10-11 | **2026-09-27T06:41Z** | P32.4: PR #159 createdAt 2026-09-27T06:41Z; closeout commit 03ac3b06 2026-09-27T06:43Z |
| L56 | `D-P31.1-3` (`DONE 2026-09-28`) | 2026-09-28 | **2026-09-27T04:16Z** | P32.2: PR #157 createdAt 2026-09-27T04:16Z; closeout commit 5677495a 2026-09-27T04:17Z |
| L57 | `D-P31.5-2` (`DONE 2026-10-12`) | 2026-10-12 | **2026-09-27T07:17Z** | P32.5: PR #160 createdAt 2026-09-27T07:17Z; closeout commit 616b889c 2026-09-27T07:19Z |

Correction written 2026-10-02 (P34.8).
