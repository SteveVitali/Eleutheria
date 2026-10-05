# ADR-199 — Round-close record checks, the capstone two-sum, and the tail probe-sweep contract (P34.33)

- Date: 2026-10-05
- Status: accepted
- Ticket: P34.33 (Round 11 / P34, row 238 — the amended SIG-ENG-031 checks; extends SIG-ENG-041,
  owner SEED-15; cites SIG-MEM-011, owner P35.3; B4 G9 + G7 item 5 + G10 tail column)
- Base: `r11/P34.32-adr-index-generator-and-trigger-register`
- Related: ADR-150 (the verdict grammar and re-verdict vocabulary the two-sum recomputes),
  ADR-198 (the trigger-register tail mode this row *calls*, never re-implements), ADR-073/126/127
  (the build-memory v2 records the checks read), BL-084 (this ADR's trigger home)

## Context

B4 §G9 amends SIG-ENG-031: at each round close the risk register gains a dated round-review
section, RISK ids are unique, every deferred risk row has an open backlog home, and every round
banner in the manifest is tied to a spec part. B4's replay names the defects this catches —
RISK-P21-03 sat unrouted when its home closed; RISK-P5-04 and RISK-P20-01 each head two rows;
Rounds 2–9's banners predate the spec-part rule entirely (F-32 §52 forbids retrofitting history).
G7 item 5 (SIG-ENG-041, extended not owned by this row) fixes the capstone headline: engineering
closed counts MET + MET-DIFFERENTLY + MET-ENGINEERED while requirement satisfied counts
MET + MET-DIFFERENTLY — the ACCEPT-R10 "34 MET" packet folded the engineered leg into MET and is
the replay (superseded by C-13). G10's tail column requires a written probe-sweep contract the
sub-round acceptance rows (P34.47 / P35.64 / P36.73) and the P38 tail run can consume, with the
probe records themselves owned by P35.3 and the OPS rows.

## Decision

1. **One checker, two modes.** `docs/build/tools/check_round_close.py` (stdlib) runs structure
   mode inside `make docs-check` and the CI `docs` job (`docs-check-round-close`, plus a named
   step for visibility), and tail mode as
   `check_round_close.py check --round-tail <round-start>` — a CLI argument P38 and the
   sub-round acceptance rows call, not a CI stage: a tail check judged mid-round would demand
   probe records no row has shipped yet. Structure mode checks risk-id uniqueness (resolved only
   by an appended, dated `Renamed …by this record` inside a `## Round N review` section — never
   a renamed row), deferred-row routing, round-banner spec cites, the appended
   "Frozen historical view" pointers on `docs/traceability.md` and `docs/build/TICKET_VS_SPEC.md`,
   and the capstone two-sum. Tail mode adds the dated `## Round N review` for the LEDGER's
   `round:` (a "dated round review" means a `recorded` stamp at-or-after the round start — the
   Stage-B-seeded section already satisfies Round 11 mid-round; the tail re-verifies it), calls
   `adr_triggers.check(round_tail=…)` so G8-3's re-evaluation is enforced, not duplicated, and
   reads the probe-sweep contract.

2. **Deferred semantics: routed, not re-verdicted.** A deferred-class risk row is routed when a
   BACKLOG `sources` cell owns it, its id cell carries a `→ BL-nnn` cite, or a corrections-table
   record names it — and every BL it names exists. A re-home (the owner differs from the row's
   cite) must be an *appended* corrections record; a `Re-homed … → BL-nnn` target must be an
   **open** row. A closed or accepted owner is a discharged deferral (the BL `landing` records
   the disposition, F-32 §52), not a missing home — so the structure check does not re-litigate
   historical routing, and the defect class is exactly the unrouted row (RISK-P21-03's shape).
   This row appended the RISK-P18-04 corrections record the rule requires (BL-042 closed →
   BL-087; BL-042's residue line already recorded the move).

3. **Rounds 2–9 exempt, listed; a cite must resolve.** `record_policy/round_close.toml` is the
   TOML policy: `[banners] exempt_rounds` names the pre-rule rounds, `required_cites` maps a round
   to its required literals (Round 11 → `Part XII`, `§56` — appended to all nine chain banners
   here), and any unmapped non-exempt banner must still cite *some* part/section that resolves to
   a spec heading.

4. **Two-sum grammar, matrix-recomputed, exempt-by-date-listed.** A packet matching the declared
   patterns (`docs/build/readouts/ACCEPT-*.md`, `docs/build/readouts/GATE-*.md`,
   `docs/build/CAPSTONE_*.md` — the `GATE-*.md` glob deliberately widens the contract's
   `GATE-ACCEPT*.md` so the Round-11 acceptance packets land in scope) that makes a bare
   coverage-count claim (`<n> <verdict-word>` / `<word> count <n>`) must declare
   `coverage two-sum[<layer>]: engineering closed = N · requirement satisfied = M` — recomputed
   from `COVERAGE_MATRIX.csv` by `check_coverage_matrix.py`'s verdict parser, per status layer
   (`achieved_domain`), and every bare claim must equal the matrix count. Qualified counts
   (`MISSING-with-recorded-deferral`) are not matrix claims by grammar. Historical packets are
   exempt *by date, listed* in the policy — a vacuous exemption (file missing, no claim, or its
   listed date absent) fails.

5. **The tail probe-sweep contract is a TOML policy, not prose.**
   `record_policy/tail_probe_sweep.toml` lists the ten G10 probes with `requires` (B4's own
   requirement citations), `owner`, the producer `command` the owner ships, and `record` — the
   committed `sig.probe-run/1` path under `docs/build/reports/probes/`. At the tail each listed
   probe needs a record that parses as `probe-run/1`, is ≤ 24 h old at the packet commit
   (`--at`, default now), and evaluated something — an empty `checks` map or an all-`skipped`
   record fails (G11: a scheduled job that measured nothing fails). The probes themselves stay
   with their owners (P35.3 / the OPS rows).

6. **Vacuous is red everywhere.** Every leg reports candidates/evaluated; a non-empty candidate
   set evaluated-to-zero exits 3 (SIG-ENG-042 shape), alongside 1 = violations and
   2 = usage/input error.

## Alternatives considered

- A separate tool per leg (risk / banners / two-sum / sweep): three of the four legs share the
  risk-register and backlog scans; one checker keeps the tail invocation a single command and the
  policy split (round_close.toml + tail_probe_sweep.toml) keeps the data readable.
- Folding the checks into `check_backlog.py`: the backlog checker is the deferral/home authority
  this checker composes with — duplicating its rules there would create two routing judges.
- `--round-tail` as a workflow stage: the tail is a point in the round, not a branch shape —
  a flag the tail-calling rows run matches the contract's wording and keeps CI structure-simple.
- Rejecting every closed/accepted historical home outright: the seed re-home round was recorded
  by design (BL-042 → BL-087 and siblings); the check then fails 110+ legitimate discharges — the
  rule judges the *routing record*, not the verdict of the rows it passes through.

## Consequences

- `docs/risk_register.md` gains one appended corrections row (RISK-P18-04 → BL-087).
- `docs/tickets/00_MANIFEST.md` gains `· spec: Part XII (§56)` on the nine Round-11 chain
  banners — the only banner-text change, inside the round the cite names.
- `docs/traceability.md` and `docs/build/TICKET_VS_SPEC.md` gain the appended frozen-view
  pointers; both stay frozen views over Phase-0…P18.
- `make docs-check` gains `docs-check-round-close`; the CI `docs` job gains a named step.
- P34.47 / P35.64 / P36.73 / P38's REC tail call
  `python3 docs/build/tools/check_round_close.py check --round-tail <round-start>`.
- BL-084 opens for this ADR's trigger home.

## Revisit trigger

- A new deferred-heading class or routing form lands in `check_backlog.py` (the heading list here
  is a deliberate copy — divergence is a review point).
- A packet grammar lands that the claim regex cannot express (per-cell claims, a new verdict
  word) — the grammar is declared in `round_close.toml` + the checker docstring.
- The `sig.probe-run/1` record schema revs — the sweep policy pins `probe-run/1`; a v2 needs a
  recorded extension.
- A banner without a chain table needs a cite rule (today only table-opening `### Round` headings
  are candidates).
