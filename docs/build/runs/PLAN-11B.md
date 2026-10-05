# PLAN-11B — Contracts for 11B rows + the SIG-TRANSP requirement family

<!-- BM-RUN-01: Harness = the exact PR-trailer string. Started/Closed = UTC
     `date -u` at branch start / when the last acceptance criterion is
     satisfied. The OM gap table is the ticket's operating checklist.
     This run ledger is shared by the thirteen contexts C1–C13 of row 239;
     each context appends its own section and its own Started/Closed. C13
     closes the ledger — no `Closed:` header line before then. -->

Harness: devin-desktop/swe-2-high/subagent
Started: 2026-10-05T11:32Z (`date -u` at branch creation; branch
`r11/PLAN-11B-contracts-for-11b-and-transp-family` from `0de78f39` on
`r11/P34.33-round-close-record-checks`)
PR: (to be opened at the C1 push; base `r11/P34.33-round-close-record-checks`)

## Spec / Base / Branch / Config

- Spec: `docs/tickets/239_PLAN-11B__contracts-for-11b-and-transp-family.md`
  (manifest row 239 — Round 11, `decompose-spec mode=extend`, thirteen
  contexts C1–C13 over rows 261–343; each context ≤ 8 rows).
- Base: `r11/P34.33-round-close-record-checks` @ `0de78f39`
- Branch: `r11/PLAN-11B-contracts-for-11b-and-transp-family` (shared;
  one PR for the whole row). PR base = the base branch (PR-1).
- Config: `decompose-spec mode=extend`; `live_verification=false` — this
  row writes contracts and spec text; it executes no 11B row, mutates no
  production and ticks no gate.
- Requirement ids (from the contract): **written here** — the SIG-TRANSP
  family (plan §6.2, spec §56.8); **owners re-confirmed** — SIG-SEC-008 →
  P35.1a/b, SIG-SEC-009 → P35.4, SIG-CONF-010 → P35.60 (the §56 `Owner:`
  lines as written); **cited** — SIG-ENG-003 (spec changes through
  `spec_src` + `BUILD.sh`), SIG-ENG-041 (MISSING rows and routing; owner
  SEED-15).

## Deferrals read

Read `docs/tickets/DEFERRALS.md` first (AGENTS.md gotcha 8). Rows naming
surfaces this plan row touches:

- `D-R11-ARCHIVE-1` (OPEN; cites BL-029, BL-037) — the non-GCS mirror leg is
  named to P35.5 (row 262); P35.5's contract keeps the deferral open and
  carries the mirror question. Read for C1's row 262 contract.
- `D-P34.50-1` (OPEN) — OP-09 is operator-owned; P35.67 (row 263) is the
  verifying probe row. Read for C1's row 263 contract.
- Rows `D-R11-OSMUID-1` and the tribal/later-phase placements of the
  contract's deliverable 8 are carried items of the *plan* row; their
  landing rows sit in C2–C12's batches — noted in each context's section.
- No OPEN/PARTIAL row is closed by this planning row; no row's lead token
  changes, so no obligation-event transitions are owed.

## Contexts

### C1 — 2026-10-05 (rows 261–265 + the SIG-TRANSP family)

Started: 2026-10-05T11:32Z · Closed: (open while C1 works)
Context model: devin-desktop/swe-2-high/subagent.

Scope (contract deliverables 1, 2-in-part, 3-in-part):

- Append the SIG-TRANSP family (SIG-TRANSP-001…043) to `spec_src`,
  de-duplicated against existing ids and the K13 set (D26–D43 written
  once here; PLAN-11C cites the final ids); register `TRANSP` in §0.3;
  rebuild via `docs/research/_meta/spec_src/BUILD.sh`; commit the
  draft→final id map `docs/build/reports/plan-11b/TRANSP_id_map.csv`;
  update `check_spec_src.py` baselines and Appendix G.7 (the SEED-12
  pattern); add one `COVERAGE_MATRIX.csv` row per id, verdict MISSING,
  routed to the owning chain row; one `coverage-assessment/1` event per
  id.
- Rewrite skeletons to full contracts: row 261 (P35.57, API release
  parity), 262 (P35.5, zero-egress distribution host), 263 (P35.67,
  post-DNS-cutover probe), 264 (P35.1a, scheduler of record / live diff /
  cron lint), 265 (P36.1a, opt-out register + reservation refusal).
- Re-confirm §56 owner lines: SIG-SEC-008 → P35.1a/b, SIG-SEC-009 →
  P35.4, SIG-CONF-010 → P35.60 — recorded in the row-264 contract;
  no spec change needed (the owner lines already read so).
- Notes for C2+: the tribal/S8 item (8b) and its reading belong to
  C2/C5 per the contract's placement instructions — not read or placed
  by C1.

Findings / decisions: (appended as C1 completes)

### C2 — pending

### C3 — pending

### C4 — pending

### C5 — pending

### C6 — pending

### C7 — pending

### C8 — pending

### C9 — pending

### C10 — pending

### C11 — pending

### C12 — pending

### C13 — pending (fresh-context Phase-4 sizing review; closes this ledger)

## OM gap table

One row per operating clause of the contract's B5 §6.2 / H2 §7 block;
filled per context.

| clause | status | note |
|---|---|---|
| OM-01 harness/model recorded; commits trailered | in progress | header + every commit trailer `Harness: devin-desktop/swe-2-high/subagent` |
| OM-04 dates from `date -u` / git / GitHub (source named) | in progress | header Started from `date -u` |
| OM-05 CI read at every boundary; red → blockedOn | pending | ci_boundary.py at the C1 push |
| OM-06 every AC names its layer | pending | per contract |
| OM-14 production mutations | n/a | none — planning row |
| OM-13 protected records appended only | in progress | memory_guard --staged before each commit touching them |
| OM-15 no test asserts a living record's current value | n/a | no tests written by C1 |
| OM-07/08/09 gate records verbatim | n/a | no gate item decided by this row |
| OM-16 size budget | in progress | C1 = transparency family + 5 contracts; ~200k seam rule watched |
| OM-02 closeout is one commit after the PR exists | pending | C13 |
| OM-19 windows / live legs | n/a | none for this row (each written contract carries its own) |
| OM-20 pre-authorisation | n/a | not an OM-20 row |
| OM-03 rows only from the ratified plan | ok | rows 261–265 are the ratified chain rows |
| PR-1 branch from chainTip; PR base = previous branch | in progress | base `r11/P34.33-round-close-record-checks` |
| CI-2/CI-6 pre-closeout head green | pending | C13 |
| P11 local gate | pending | `make check` etc. at the final C1 commit; Docker state recorded honestly |
| CI-8 CI config changed | no | |
