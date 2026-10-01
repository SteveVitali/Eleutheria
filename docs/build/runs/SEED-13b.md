# Run ledger — SEED-13b (Stage B, T3 second context): full 11A contracts for rows 201–220

- Harness: claude-code/claude-opus-5-5/subagent
- Skills: 8aeb6dc
- Started: 2026-10-01T14:26:07Z (this unit's first `date -u`; its scratch record was lost in the restart below — value as printed in the run transcript)
- Restart: the orchestrator reports a system restart at ≈ 15:00Z that stopped this run after all 20 contracts were written; resumed 2026-10-01T15:08:57Z (`date -u`) on the orchestrator's message, re-verified the 20 files, fixed one acceptance line (P34.16), re-ran the checks
- Closed: 2026-10-01T15:11:34Z
- Unit: SEED-13b — plan Appendix A T3, second bullet, for the first 20 of the 60 11A rows (rows 201–220). Owns only the 20 contract files below and this ledger. Not owned: P34.18 (row 221, SEED-13c), the manifest, CI/tools (SEED-02b), registers (SEED-14), LEDGER (SEED-17).
- Worktree / branch: `/Users/stevenvitali/Eleutheria-next-phase`, `r11/seed` (no git state change made by this unit)
- Read (targeted sections only, rule 8): `stageB/AGENT_BRIEF.md`, `stageB/CARRY.md`, `stageB/T3_contract_map.csv` rows 201–220, `docs/build/runs/SEED-13a.md`, plan Appendix A T3, §3.3, §5.1–§5.3, §5.10, §8.3–§8.5, §10.1–§10.2, §11.2 (lines), `data/round11_plan.csv` + `data/ticket_catalog.csv` rows 201–220, `data/k13_tickets.csv` W0 rows, `stageB/T1_id_map.csv`, `feedback/RATIFICATION_LOG.md` (round lines cited), the design-note sections each row cites (H1, H2, B1–B5, E2, F5, G1, G2, J3, J4, K11, K13, K14, REVIEW_SYNTHESIS §6, S4-feasibility FEA-08, TRACK0_RECORD), spec §56 + the cited older §§, ADR-146/149/155/164/165/167/179/180/183/186 (sections), `docs/tickets/_TEMPLATE.md`, the 0.5.0 `~/.claude/skills/build-memory/templates/ticket.md`.

## What this unit did

Replaced the 20 `Kind: skeleton` files with full contracts under the same names (the manifest rows bind them). Each carries: header (sequence, phase, `Kind: ticket`, `Harness: devin-desktop/swe-2-high/subagent`, base branch + `r11/<id>-<slug>`, `Depends on`, `Run:` with `live_verification`, gate status with the operator's words verbatim and their round `date -u`, OM-20 status, live stage, `Live window:` + live-leg re-run prompt where windowed (OM-19), `Production mutations:` (OM-14), `Size budget:`, the token-counted Load figure); Goal; a Load list with the byte count of every entry; deliverables with requirement ids; out of scope naming owner rows; live legs and `live:` edges where they exist; a production-mutation section (what · scripted path · pre-state · restore point · rollback · authority); acceptance criteria each tagged with its BM-STATUS-01 layer (never higher than verifiable); the universal ACs (verification, head-bound CI read, one-commit closeout incl. the `rows 1-N as of` line of `docs/build/README.md`, `check_coverage_matrix.VERDICTS` extension, `FLIPPED <date> (<gate|ADR>)`, transitions with evidence); requirement ids (owner / also / cited); cross-cutting invariants; the B5 §6.2 operating-clauses block with H2 §7's four lines, filled per row; notes (carry items, owned decisions, anchors).

### Token counts (counter `utf8-bytes÷3 | ÷4`, plan §8.5 / S6R-27; measured 2026-10-01 on the `r11/seed` working tree after SEED-02b's commit `06724e3b`)

Bytes are exactly what each Load entry names: whole files, or the named `§` sections, grep-selected rows or line ranges; the LEDGER orient region is counted at its 12 KiB budget (SIG-MEM-010); DEFERRALS-first is counted as the CURRENT.md owed-obligation index + the owed rows naming the row + named rows + a 16 KiB allowance for rows SEED-14's mapping will route there; the contract itself is included. Target: ÷3 ≤ ~150k.

| row | id | file | Load entries | bytes | ≈ tokens ÷3 | ≈ tokens ÷4 | contract bytes | OM-20 | verdict |
|---|---|---|---|---|---|---|---|---|---|
| 201 | P34.1 | `201_P34.1__toolchain-pin-and-ci-hygiene.md` | 23 | 192,947 | 64,315 | 48,236 | 20,191 | not OM-20 | no split |
| 202 | P34.2 | `202_P34.2__recorded-ci-verifier-and-flake-policy.md` | 19 | 230,463 | 76,821 | 57,615 | 14,109 | not OM-20 | no split |
| 203 | P35.38a | `203_P35.38a__crawler-ua-contact-and-explanation-page.md` | 19 | 199,547 | 66,515 | 49,886 | 14,753 | not OM-20 | no split |
| 204 | P34.3 | `204_P34.3__ops-data-protection.md` | 18 | 158,252 | 52,750 | 39,563 | 15,893 | pre-authorised (S5-3) | no split |
| 205 | P34.4 | `205_P34.4__alerts-that-reach-a-human.md` | 16 | 184,805 | 61,601 | 46,201 | 15,842 | pre-authorised (S5-3) | no split |
| 206 | P34.5 | `206_P34.5__cost-guard-budget-alert-billing-export.md` | 14 | 128,261 | 42,753 | 32,065 | 14,247 | pre-authorised (S5-3) | no split |
| 207 | P34.6 | `207_P34.6__restore-drill-and-logical-export.md` | 18 | 171,270 | 57,090 | 42,817 | 16,834 | pre-authorised (drill clone) + in-ticket go | no split |
| 208 | P34.50 | `208_P34.50__dns-cutover-runbook-and-zone-inventory.md` | 14 | 145,334 | 48,444 | 36,333 | 11,233 | not OM-20 | no split |
| 209 | P34.7 | `209_P34.7__append-only-checker-full-modes.md` | 18 | 358,037 | 119,345 | 89,509 | 13,115 | not OM-20 | no split |
| 210 | P34.8 | `210_P34.8__obligation-events-repair.md` | 18 | 226,163 | 75,387 | 56,540 | 13,019 | not OM-20 | no split |
| 211 | P34.9 | `211_P34.9__ledger-contract-validator-no-vacuous-pass.md` | 15 | 251,953 | 83,984 | 62,988 | 12,914 | not OM-20 | no split |
| 212 | P34.10 | `212_P34.10__one-allow-listed-publish-path.md` | 19 | 222,726 | 74,242 | 55,681 | 12,994 | not OM-20 | no split |
| 213 | P34.11 | `213_P34.11__honest-home-dossier-coverage-copy.md` | 21 | 148,231 | 49,410 | 37,057 | 13,569 | not OM-20 | no split |
| 214 | P34.12 | `214_P34.12__research-queue-truth-fixes.md` | 17 | 133,240 | 44,413 | 33,310 | 12,267 | not OM-20 | no split |
| 215 | P34.13 | `215_P34.13__chrome-format-accessibility-quick-fixes.md` | 18 | 135,178 | 45,059 | 33,794 | 12,943 | not OM-20 | no split |
| 216 | P34.14 | `216_P34.14__jurisdiction-display-names-interim.md` | 16 | 132,122 | 44,040 | 33,030 | 12,076 | not OM-20 | no split |
| 217 | P34.15 | `217_P34.15__map-network-search-island-honesty.md` | 25 | 228,892 | 76,297 | 57,223 | 13,265 | not OM-20 | no split |
| 218 | P34.16 | `218_P34.16__public-repo-honesty-corrections.md` | 17 | 166,886 | 55,628 | 41,721 | 13,898 | not OM-20 | no split |
| 219 | P34.19 | `219_P34.19__express-terms-disclosure.md` | 16 | 148,789 | 49,596 | 37,197 | 14,061 | not OM-20 (conditional in-ticket go) | no split |
| 220 | P34.17 | `220_P34.17__web-honesty-wave-and-republish-1.md` | 25 | 199,354 | 66,451 | 49,838 | 19,148 | in-ticket go | no split |

Largest: P34.7 (≈ 119k by ÷3: `memory_guard.py` 121 KB + its tests 62 KB). Watch-list rows (S6R-14): P34.17 ≈ 66k. **No row exceeds ~150k, so no split is proposed.** Re-verification after the restart: for every file the listed figures sum to the header total, the self-entry equals the file's size, and all 137 whole-file entries equal the files on disk; the only input changed since measurement (`META_PLAN.md`, commit `22324540`) is in no Load list.

### Requirement → ticket index (rows 201–220; spec §56 `Owner:`/`Also:` as written in the contracts)

| id | role | row |
|---|---|---|
| SIG-ENG-046 | owner | P34.1 |
| SIG-MEM-007 | owner | P34.2 |
| SIG-INGEST-036 rule 1 | met at its engineered layer (plan §5.5) | P35.38a |
| SIG-OPS-002 | owner | P34.3 |
| SIG-STORE-048 | also (versioning half; owner P37.3) | P34.3 |
| SIG-OPS-006 | also (first channel, uptime, TLS alert; owner P35.2) | P34.4 |
| SIG-OPS-009 | owner | P34.5 |
| SIG-OPS-001 | owner | P34.6 |
| SIG-MEM-006 | owner | P34.7 |
| SIG-MEM-005 | also (obligation-event clock defaults; owner SEED-02) | P34.8 |
| SIG-ENG-042, SIG-MEM-010 | owner | P34.9 |
| SIG-MEM-012 | also (ledger fields; owner SEED-02) | P34.9 |
| SIG-OPS-003, SIG-OPS-004 | owner | P34.10 |
| SIG-GOV-012/013/015, SIG-LIC-009, SIG-INGEST-037 (waived clauses), SIG-GOV-014 | cited | P34.16 |
| SIG-LIC-001/004/011, SIG-GOV-007 | cited | P34.19 |
| SIG-GOV-001/002/003/012/013, SIG-UI-042 (waived or met differently), SIG-MEM-011, SIG-OPS-003/004 | cited | P34.17 |

Every id written in the 20 contracts exists in `docs/2_canonical_design_spec.md` (checked by script).

### Must-haves of the unit prompt — where each landed

- **P34.1:** the §8.5 isolation protocol (T6 probe first; nonce kept by the orchestrator as sha256 only, never in a file/env/git/prompt/Knowledge; positive-control token in the prompt; the sub-agent reports context sources, 32-hex tokens, its own `date -u` start and harness/model; pass rule; repeated at each GATE), the round-27 fallback order (SB-3: verified `drive-build.sh --agent-cmd`, then the manual tier), the 2026-10-19T00:00Z landing deadline with the seed's `ubuntu-24.04` fallback (FEA-16, S6R-27), CF-01, ADR-151 authorship.
- **Row 203 = P35.38a:** UA contact → `https://surveillancegraph.org/data-collection/`, minimal T0 page, before any Round-11 fetch, `contact@` alias first (C-8), no personal identifier; historical `sig-project.org` records (incl. `db/sqitch.plan` author lines) never edited.
- **P34.16:** "the operator's own determination (no counsel)" (TS-09, ADR-167), not "operator-reported"; WV-01 vs C-5 carried.
- **P34.17:** the corrections/dispute page with the WV-08 handling order and no time commitment, e-mail intake (B-8, WV-05); the address itself is not written into the contract; the republish is an in-ticket pause.
- **P34.19:** disclosure of the express-terms basis (A-8; ADR-183 incl. its SB-2 refresh clarification), not withdrawal; F-337 withdrawal list.
- **P34.5:** budget alert + billing export (A-2a). **QA-9 restore drill (P34.6) and TLS-expiry alert (P34.4)** (A-1).
- **C-10** stated in every contract's invariants and specifically in P34.6, P34.7 and P34.8 (L44–52 allow-listed by change id until 2026-10-19T21:00Z, ADR-146; `docs/build/planning/**` excluded).
- **P34.18** (repo-tip handle strings A-0.1 + history disclosure A-0.4) is row 221, SEED-13c's range — not touched here; P34.16 and P34.17 point to it.

### Decisions taken (agent readings, labelled in the contracts)

1. **Copy-batch record:** 11A copy rows append drafted sentences to `docs/build/reports/copy-batches/batch-01.md` (page, text, sha256, status); the operator's verbatim confirmation is recorded there with `date -u`; P34.17's L2 refuses a pending sentence. The plan names no file for copy batches; T5/the orchestrator may rename it.
2. **Stricter window readings** where the row text and plan §8.4/§10.2 differ: `sig-pg` patches outside AR-3 (P34.3); the `sig-probe` roll outside AR-3 (P34.4); the logical export outside AR-3 and 03:00–10:00Z (P34.6).
3. **P34.6's OM-20 scope:** the S5-3 list says "P34.6 (drill clone)", so the first logical export, the `sig-backups` lifecycle and relabel, and the full-backup drill variant pause for an in-ticket go.
4. **P34.11 QW-14:** the contribution-back link is removed, not restored (C-12 withdrew `/contribution-back/`; SIG-OPS-003).
5. **P34.13 `/terms`:** the redirect to the API terms (which still name a board and counsel until P34.46) ships only beside N-7, or waits — decided in the ticket.
6. **P34.19 F-337:** build/export withdrawal list; a hosted API-side suppression only on an in-ticket go.
7. **P34.4 QA-8:** `gh workflow disable reingest.yml` listed as a named, reversible mutation (scheduled workflows run from `main`, so the PR's schedule removal alone stops nothing until the operator merges).
8. The B5 §6.2 block's heading is written as plain text inside its fence so heading parsers do not read it as a section.

## Checks run

| check | result |
|---|---|
| `python3 docs/build/planning/2026-09-30-next-phase/tools/s13/gen_t3.py check` | **exit 0** — "310 Round-11 manifest rows, 310 plan rows, errors 0". The check has no full-contract-specific rule: it verifies titles, the Harness header, no run line in skeletons, file ↔ map ↔ manifest; all 20 rewritten files pass and none is still `Kind: skeleton`. |
| `bash scripts/docs/check-build-memory.sh .` | **exit 0 — no violations, 44 warnings**, identical to the run before this unit wrote anything (all pre-existing legacy warnings); orient probe 11,790 B (was 12,452 B with P34.1's skeleton header). |
| `python3 docs/build/tools/memory_guard.py all --worktree` | **exit 0** — 0 violations, 0 warnings, 2,850 items evaluated (the 20 contracts are unexecuted, so only shape rules apply). |
| script checks over the 20 files | every SIG id exists in the spec; no line pairs `Kind:` with "skeleton"; no 32-hex token (P34.1's isolation check); no personal identifier or address; Load figures sum to each header; self-sizes exact. |

## Open issues for the orchestrator / other units

1. **GATE-B packet:** does P34.6's S5-3 entry "(drill clone)" also cover the first logical export and the `sig-backups` lifecycle/relabel? Until answered, they pause in-ticket.
2. **Copy-batch file convention** (decision 1) — adopt or rename at T5 (OPERATING MODE) so P34.11–P34.19 and P35.38a use one record.
3. **Re-measure the DEFERRALS-first share at dispatch** — the 16 KiB allowance stands in for rows SEED-14's mapping will route to these rows; P34.2 counts ADR-151 (written by P34.1) at an 8 KiB estimate.
4. **Not done here (Appendix A T3 last bullet):** the requirement → ticket index for all 60 11A rows and the fresh-context decompose-spec Phase-4 sizing review of 11A — this ledger gives rows 201–220's half (counts + index above); SEED-13c/d or the orchestrator completes it.
5. **SEED-13c:** the prompt's P34.18 must-haves (A-0.1 repo-tip handle-string removal; A-0.4 history disclosure note) belong to row 221's contract.
6. The generator used for these contracts lived in the session scratchpad and was lost in the restart; the contracts are the record, and the re-verification above was done on the files themselves.
