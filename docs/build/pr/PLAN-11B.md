# PLAN-11B — Contracts for 11B rows + the SIG-TRANSP requirement family

**Thirteen-context plan row (C1–C13, one shared branch, one PR).**
**Requirement ids:** **SIG-TRANSP-001…043** (written here — the transparency
family, spec §56.10 under §56.8's later-family rules, plan §6.2) ·
**SIG-SEC-008 / SIG-SEC-009 / SIG-CONF-010**
(owners re-confirmed, not changed) · **SIG-ENG-003** (cited — spec changes land
through `spec_src` + `BUILD.sh`) · **SIG-ENG-041** (cited — MISSING rows and
routing) · **Ticket:**
`docs/tickets/239_PLAN-11B__contracts-for-11b-and-transp-family.md` (manifest
row 239; `decompose-spec mode=extend`) · **Base:** `r11/P34.33-round-close-record-checks`
(stacked; merge after P34.33) · **Gate:** none · **Live stage:** none
(`live_verification=false`; this row writes contracts, it does not execute them)
· **Production mutations:** none · **OM-20:** not an OM-20 row · **CI config
changed:** no.

## Why

Rows 261–343 of the Round-11 manifest are skeletons. Before GATE-G4 each must
read as an execute-grade contract — gate status with the operator's verbatim
words and times, live stage/window/legs with their re-run prompts, production
mutations, `live:` edges, token-counted Load lists, and requirement ids.
Separately, the transparency requirement family (spec §56.10: J3 §11 D01–D25,
K9 §10 D26–D34, K10 §18 D35–D43, adopted by K13's UXR-A10) needs final
`SIG-TRANSP-nnn` ids so the 11B transparency rows can cite them. C13 runs the
fresh-context Phase-4 sizing review and produces the draft 11B OM-20 list for
the GATE-G4 packet.

## What ships (C1–C13 cumulative)

- **SIG-TRANSP-001…043** appended to `spec_src` (new §56.10), `TRANSP`
  registered in §0.3, the canonical spec rebuilt by
  `docs/research/_meta/spec_src/BUILD.sh` (the generated file is never
  hand-edited), `check_spec_src.py` fold-back baselines updated, an Appendix
  G.7 row in the SEED-12 pattern, a committed draft→final id map
  (`docs/build/reports/plan-11b/TRANSP_id_map.csv`), 43 MISSING rows in
  `docs/build/COVERAGE_MATRIX.csv` routed to their owning chain rows, and 43
  `coverage-assessment/1` events. D26–D43 are written once here — PLAN-11C
  cites the final ids. No MUST elsewhere is weakened; ADR-162 is cited, not
  edited. (C1)
- **Execution-grade contracts for all 83 ratified 11B chain rows
  (261–343)** — same file names, each with the literal `Run:` line, verbatim
  gate text, OM-20 status, live window/legs with re-run prompts,
  production-mutation declarations, `live:` edges, token-counted Load lists,
  layered ACs and the B5 §6.2 / H2 §7 operating-clause block; every recorded
  plan-note correction lands in-contract, not in the plan (C2–C12).
- **C13 Phase-4 sizing review + one sanctioned split.** All 83 contracts
  re-read; Load declarations, `Depends on:`/`live:` edges, gate status, OM-20
  status, production mutations and requirement ownership audited — no forward
  or unresolvable dependencies. Of the four flagged rows only **P35.1b
  (row 291)** exceeded the Phase-4 context budget (~275k modeled working set
  over the ≈235k split line): split at its recorded seam — suffix row
  **291a / P35.1c** `docs/tickets/291a_P35.1c__dispatcher-consolidation.md`
  owns dispatcher consolidation + the closing proof and declares its dep on
  P35.1b; P35.1b keeps the sweep half via a conforming appended
  `> Amended 2026-10-06:` note (BM-TICKET-04 — the executed contract is
  append-only). P36.12 (~202k, separately-dispatched dated legs), P35.61
  (~180k, hard operator pause) and P35.63 (~190–200k, HG-11 pause) are **not**
  split — their dispatch boundaries already bound the live context.
- **GATE-G4b evaluated and not fired:** post-split counts are **82 engineering
  rows / 74.5 engineering runs** — under the 85/75 thresholds, so no re-split
  marker lands.
- **Requirement index regenerated + verified** —
  `docs/tickets/REQUIREMENT_INDEX_R11.md` via `req_index.py write`, `check`
  reports current (311 contracts scanned: 144 full + 167 skeletons; 277
  distinct ids; 291a cited on the relevant ids; every §56 requirement resolves
  to an 11B owner; 29 skeleton-owned ids remain for 11C/11D rows; four
  seed-owned §56 ids stay under §56.1). `req_index.py` now parses
  suffix-letter rows (`291a`) by numeric prefix; the contract map, manifest
  (Plan-extensions line — row inserted after 291, no renumber) and the
  decomposition-decisions C13 record are updated.
- **Draft 11B OM-20 list (20 rows) + ADR-171 outreach-owed list** in the run
  ledger — drafted for the operator's GATE-G4 packet; nothing is sent or
  pre-authorised by this row.
- **Tribal-member placement + `D-R11-OSMUID-1` placement** confirmed and
  recorded in the C13 ledger section.

## Boundary record (verbatim, head-bound)

Every C13 head's boundary read returned `blockedOn … (external)`: off-stack
merge **#190** (`devin/p33-8-agent-docs-refresh` → `main`, merged
2026-10-06T12:15:59Z) and eight on-stack r11/ merges #185–#195 — the operator's
stack integration, **not a chain-row defect** (`open_other: 0`). Recorded in
`docs/build/logs/ci-PLAN-11B-C13-precloseout.json`
(ci-boundary/1, read_at 2026-10-06T14:20:00Z on head `369ec6f6`).

Docs-leg reds on the C13 heads, each fixed forward and recorded — never
smoothed:

- `f9c407c8`: history-guard — 147 `append-only` findings on
  `291_P35.1b__fleet-hygiene.md` (the commit subject named the ticket ids →
  `executed()` attribution). Fix: `08c1840b` restores the authored bytes +
  lands the re-scope as the appended `Amended` note; `4c622b1d` declares
  `seed-commit` policy lines (the `427c5efb`/C3 precedent) → range guard 0
  violations / 17,394 evaluated, green in the `4c622b1d` docs job.
- `4c622b1d`: `docs-check-projection` stale — expected mid-sequence.
- `369ec6f6`: `docs-check-projection` stale — the regen commit carried
  `reports/current/` without its edited ledger sources; sources + regen land
  together in the closeout commit.

The closeout head's five-required-checks verdict lands in the post-closeout
record commit per convention; no `ci: pass` is claimed for a head whose
check-runs did not all succeed.

## Verification (C13 closeout, local)

- `make check` — green: ruff / format / mypy (313 files) / pytest **6,495
  passed · 464 skipped · 0 failed** / verify-gen byte-identical. Recorded
  limits: the local Docker daemon is unreachable (`docker info` hangs), so the
  Docker-gated suites (`tests/db`, `tests/e2e`, docker-marked web-IaC rows)
  **skipped** — they run in CI's `python`/`composed` jobs; `SIG_GCP_PROJECT`
  armed with a local sentinel for the fail-closed secrets scan.
- `python3 docs/build/planning/2026-09-30-next-phase/tools/check_order.py` —
  0 errors; `gen_t3.py check` — 310 manifest rows = 310 plan rows, 0 errors.
- `python3 docs/build/planning/2026-09-30-next-phase/tools/s13e/req_index.py
  check` — **current** (index regenerated).
- `python3 docs/build/tools/check_spec_src.py` — 38/38 source sections,
  191/191 Appendix F, 1,644/1,644 ids.
- `python3 docs/build/tools/check_coverage_matrix.py
  docs/build/COVERAGE_MATRIX.csv` — 820/820 rows.
- `python3 docs/build/tools/memory_guard.py all --staged` — 0 violations.
- `docs/build/tools/current_projection.py generate+verify` — fresh: 156
  obligations · 87 owed · 636 events · 245 assessments · 0 known
  inconsistencies · 974/974 input digests.
- `python3 docs/build/tools/ci_boundary.py --pr 236 --json …` — the boundary
  reads above; the closeout head's read lands in the post-closeout record.

## Non-goals

No 11B row is executed; no production action is taken; no gate is ticked; no
`ingestion_permitted` flips; `docs/2_canonical_design_spec.md` is rebuilt, not
edited; no ADR body is touched. The OM-20 sends, tribal-governance act and
`D-R11-OSMUID-1` implementation remain owed to their owning rows.
