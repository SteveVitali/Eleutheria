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

## What C1 ships (this push)

- **SIG-TRANSP-001…043** appended to `spec_src` (new §56.10), `TRANSP`
  registered in §0.3, the canonical spec rebuilt by
  `docs/research/_meta/spec_src/BUILD.sh` (the generated file is never
  hand-edited), `check_spec_src.py` fold-back baselines updated, an Appendix
  G.7 row in the SEED-12 pattern, a committed draft→final id map
  (`docs/build/reports/plan-11b/TRANSP_id_map.csv`), 43 MISSING rows in
  `docs/build/COVERAGE_MATRIX.csv` routed to their owning chain rows, and 43
  `coverage-assessment/1` events. D26–D43 are written once here — PLAN-11C
  cites the final ids. No MUST elsewhere is weakened; ADR-162 is cited, not
  edited.
- **Full contracts** for rows **261** (P35.57 API release parity), **262**
  (P35.5 zero-egress distribution host), **263** (P35.67 post-DNS-cutover
  probe), **264** (P35.1a scheduler of record / live diff / cron lint) and
  **265** (P36.1a opt-out register + reservation refusal) — same file names,
  each with the literal `Run:` line, verbatim gate text, OM-20 status, live
  window/legs with re-run prompts, production-mutation declarations, `live:`
  edges, token-counted Load lists, layered ACs and the B5 §6.2 / H2 §7
  operating-clause block.

## Still owed on this branch (later contexts)

- C2–C12: the remaining contracts (rows 266–343, ≤ 8 rows per context).
- C13: the Phase-4 sizing review, split decisions for the four flagged rows,
  the GATE-G4b decision with counts, the requirement index regeneration, the
  11B outreach-owed list, the draft 11B OM-20 list, and closeout (this PR is
  not merged and the row not closed until then).
- C2 hand-off note: the tribal/S8 item (8b) reading and placement belong to
  C2/C5, not C1.

## Verification (C1 boundary)

- `python3 docs/build/tools/check_spec_src.py` — OK: spec-src 38/38,
  appendix-f 191/191, requirement-ids 1,644/1,644; `BUILD.sh` reproduction
  byte-identical (852,023 bytes); 820 ids = 668 baseline + 152 fold-backs
- `bash scripts/docs/check-build-memory.sh .` — no violations (41
  pre-existing warnings)
- `python3 docs/build/tools/check_coverage_matrix.py` — 820/820 rows OK
- `make docs-check` — green on every leg, including
  `current_projection.py verify` fresh 973/973 (the projection was
  regenerated — it had drifted after the committed spec/coverage append)
- `make check` — green locally with two recorded limits: the local Docker
  daemon is unreachable (`docker info` hangs; the SDK ping EOFs), so the
  run used a PATH-ahead `docker` stub and the Docker-gated suites
  (`tests/db`, `tests/e2e`, the docker-marked `test_web_iac` rows) **skipped**
  — they run in CI's `python`/`composed` jobs; `SIG_GCP_PROJECT` armed with
  a local sentinel for the fail-closed secrets scan. A C1-caused red was
  found and fixed: `docs/build/tools/test_check_spec_src.py` still asserted
  `EXPECTED_IDS == 777` after the TRANSP append raised it to 820
- `python3 docs/build/tools/check_trailers.py --range <base>..HEAD` — clean
- `python3 docs/build/tools/memory_guard.py all --staged` — clean before
  the commit
- `python3 docs/build/tools/ci_boundary.py --pr <n>` — recorded in the run
  ledger after the push

## Non-goals

No 11B row is executed; no production action is taken; no gate is ticked; no
`ingestion_permitted` flips; `docs/2_canonical_design_spec.md` is rebuilt, not
edited; ADR bodies, the LEDGER's chain state and `docs/build/LEDGER.md` are
untouched (C13 owns closeout).
