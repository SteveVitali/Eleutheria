# T3 — Phase-4 sizing review of the 60 11A contracts (fresh context)

- **Unit:** SEED-13e (Stage B, plan Appendix A T3 last bullet). **Written:** 2026-10-01T16:16:20Z → 2026-10-01T16:34:10Z (`date -u`) by Claude Code
  (Opus 5.5) as a fresh-context sub-agent that wrote none of the 60 contracts (SEED-13b/c/d wrote them). Worktree
  `~/Eleutheria-next-phase`, branch `r11/seed`, HEAD `4b5c5398` + this unit's uncommitted edits. Nothing committed by this unit.
- **Inputs:** the 60 contracts `docs/tickets/201_…` … `260_…`; the run ledgers `docs/build/runs/SEED-13a.md` … `SEED-13d.md`
  (token tables, per-range indexes, open issues); `PD/stageB/CARRY.md`; plan §8.4, §8.5, §8.8, Appendix A T3; the
  decompose-spec skill (objective rule 1; Phase 4). `PD` = `docs/build/planning/2026-09-30-next-phase/`.
- **Tools (committed with this review, stdlib, read-only unless named):** `PD/tools/s13e/measure_11a.py` (re-measures every
  Load list and models the working set — prints the table below), `PD/tools/s13e/fix_load_totals.py` (re-derives a
  contract's Load figures after an edit), `PD/tools/s13e/req_index.py` (the requirement → ticket index).
- **The ceiling:** Devin Desktop `swe-2-high`, 256k-token window, dispatched as a sub-agent that cannot compact (plan §8.5)
  — the window is a hard failure boundary. Plan rule: Load ≤ ~150k tokens by the higher of bytes÷3 / ÷4 (A-15 as adopted).
  Skill rule (decompose-spec objective 1): the whole working set stays **well under half** the window.

## 1. Method

1. **Re-measure (current tree).** Every `- ` line of a contract's `## Load` is one entry; its figure is the `N B` value(s)
   after the entry's last ` — `. An entry whose figures equal its files' sizes at the commit that wrote the contract
   (`08026350`, `4cd43ce0`, `c1382e83`) is a whole-file entry and is re-measured as today's size; any other entry (a §
   section, a line range, a `grep` selection, a fixed allowance) is carried when none of its files changed since that commit,
   and flagged otherwise. The DEFERRALS-first share is re-measured separately (the table rows that name the row id today,
   plus the register rows whose ids they name) against the recorded allowance. The contract's own entry is its size now.
2. **Consistency.** For all 60 contracts the header total equals the sum of the entries, and every self-entry equals the
   file size (the five contracts this unit edited were re-derived with `fix_load_totals.py`).
3. **Working-set model (agent inference, labelled — nothing here is measured on Devin):** modelled peak (÷3 tokens) =
   Load + **the skill text every run loads but no Load list counts** (implement-spec + self-review `SKILL.md`, 52,353 B ≈
   17.5k) + a harness/dispatch allowance (15k; Devin's own prompt is unknown) + written output × 1.75 (writing it, then the
   self-review/gap passes re-reading the diff; S ≈ 15k, M ≈ 30k, an 8-row PLAN batch ≈ 37.5k) + tool output (25k, +12k per
   live leg run in the same context) + half the bytes of files the contract says it edits (re-reads while editing).
   **Verdicts:** *ok* ≤ 200k (≥ 56k headroom) · *tight* 200–235k (dispatch with the named mitigation; the run stops at a
   seam near ~200k) · *split* > 235k, or a scope too large for one run whatever the load.
4. **Self-containment.** Every file a contract's deliverables name was checked against its Load list; a missing one that
   the implementer must read (not merely append to by tool, `grep`, or never touch) is a gap. Files that earlier rows or
   seed units will write are counted at labelled estimates and re-measured at dispatch.

## 2. Findings

- **F1 — No contract exceeds the plan's ~150k Load rule.** Largest after this review's fixes: PLAN-11B ≈ 97k (÷3, upper
  bound per context), P34.7 ≈ 95k, P34.37 ≈ 85k, P34.9 ≈ 84k. Before the fixes P34.7 was ≈ 119k.
- **F2 — An unbudgeted fixed load.** No Load list counts the skill text the run itself loads: `implement-spec` (38,710 B)
  and the `self-review` it invokes (13,643 B) — ≈ 17.5k tokens (÷3) per run, plus Devin's own system and dispatch prompt.
  *Recommendation (SEED-17, OPERATING MODE):* the dispatch-time count adds this fixed share; T6's orient dry-run measures
  Devin's prompt size if the harness reports it.
- **F3 — The half-window rule is not met, consciously.** Modelled peaks run ≈ 125–200k for 56 rows; only GATE-G4, P34.30 and
  P34.31 are under ≈ 128k. Meeting decompose-spec's half-window rule would roughly double 11A's row count — the over-factoring the same
  skill warns against (fragmented decisions, re-paid bootstrap). The plan's ≤ ~150k-loaded rule stands; this review flags
  the rows near the ceiling and relies on the per-run stop rule. Recorded in the manifest's Decomposition decisions.
- **F4 — Living files grow under a whole-file entry.** One entry loaded a living record whole: P34.8's
  `coverage_assessments.jsonl` (3,748 B when written; ≈ 130 KB once Stage B appended the Round-11 assessments, which alone
  would push P34.8's peak to ≈ 238k). Narrowed to its four lines. The other whole-file living entries are small and slow
  (`ops/cadence.toml` 32.5 KB in P34.4/P34.10/P34.39b; CURRENT.md, MIGRATION.md, `pending_transitions.csv`).
  *Rule for PLAN-11B/C/D:* never load a living register, log or matrix whole — name a section, a `grep` or a sample.
- **F5 — DEFERRALS allowances hold.** After SEED-14a's mapping, the rows naming any 11A row total ≤ 9.3 KB (P34.38); every
  contract's counted share (16–45 KB) covers it. Re-measure at dispatch stays (the register keeps growing).
- **F6 — Self-containment.** Of 14 contracts whose deliverables name a file outside their Load list, 11 only append to it by
  tool or `grep`, or name it as a constraint (`db/sqitch.plan` "never edit", `sources.toml` read by code, append-only
  pointers). Three are gaps: **P34.2** (the 2.7 KB test file it fixes — added to its Load), **P34.6** (`ops/cadence.toml` —
  read one job block by `grep`) and **P34.34b** (the optional seeded-spine test — `grep` its fixture builder); the last two
  are noted here for the implementer rather than added (their cost is a `grep`). Estimates to re-measure at dispatch:
  files earlier rows write (SEED-13d's list: P34.24b rehearsal record, P34.26 census, P34.39a report, P34.42a IaC, P34.44a
  harness, P34.47 packet, PLAN-11B OM-20 lines, BUILD_INDEX Round-11 rows), ADR-151 in P34.2 (8 KiB), and
  `docs/build/reports/adr_triggers/ADR_TRIGGERS.csv` in P34.32 (8 KiB; written by SEED-15).
- **F7 — Ordering and leg-level edges.** `check_order.py` and `gen_t3.py check`: 0 errors. Three leg-level `live:` edges are
  in the contracts but not the CSV (P34.45 → P34.46; P34.43 L2 → P34.46; P34.21b L2 → P34.18 + P34.21a); the row order
  satisfies them. **Feasible before GATE-G4, with no slack:** P34.46 L2 opens ≥ 2026-10-14T14:00Z on its own in-ticket go;
  P34.43 L2 and the P34.45 ER re-run follow in the 14:00–20:00Z weekday slots, inside the plan's GATE-G4 estimate
  (≈ 10-15 → 10-17). P34.47 cannot pass while a leg is due (a held go included), so a slip moves GATE-G4 rather than voiding
  the S5-3 pre-authorisations; if GATE-G4 is held with a leg unrun, the leg goes on the 11B OM-20 list or gets its own go —
  both contracts already state this. Recorded as one `## Plan extensions` line.
- **F8 — Shared decisions and seams (Phase-4 hunt).** Owners are earlier rows or seed units for each shared decision found:
  P34.18's alias mechanism (ADR-178; used by P34.21b, P34.47), the C-10 allow-list (seed `history.policy`; P34.22a/b,
  P34.24a/b, P34.46), the quality registry (P34.44a; P34.44b, P34.45). Two conventions still lack a single record and are
  OPERATING MODE items (CARRY → SEED-17): the copy-batch file (`docs/build/reports/copy-batches/batch-01.md`; P35.38a,
  P34.11–P34.19) and ticket-authored ADR numbers (next free ≥ 191 at dispatch). **New orphan seam from the P34.40
  decision:** if P34.40's `/v1/*` leg is still paused at GATE-G4, P35.53/P35.59 depend on it — assigned to PLAN-11B
  (deliverable 8d). **Over-factoring:** the five web rows P34.11–P34.15 share only republish #1 (owned by P34.17) and each is
  ≤ 1 run; not merged.
- **F9 — PLAN-11B batching.** At the contract's ~12 rows per context the model gives ≈ 104k loaded + ≈ 56k written → ≈ 260k
  peak, over the window. At ≤ 8 rows: ≈ 97k (upper bound) + ≈ 37k → ≈ 220k, *tight*; at 6 rows ≈ 198k. The contract now
  runs **13 contexts of ≤ 8 rows** (C1 the SIG-TRANSP family + 5 rows; wave boundaries 271 and 290 kept; C13 the review),
  7.0 runs unchanged as the plan figure, with a stop at ~200k. *Optional (orchestrator/T6):* dispatching each context with
  `decompose-spec mode=extend` directly rather than through `implement-spec` saves ≈ 17k of skill text and the self-review
  re-read.
- **F10 — P34.7 is the one split proposal.** Trimmed, its Load is ≈ 95k, but the guard it completes is 121 KB read and
  edited whole and its replay oracle prints every flagged item over the whole history: modelled ≈ 225k. Seam: **P34.7a** —
  deliverables 1, 2, 6, 7 (remaining modes, chain-id registry, fixtures, C-10) · **P34.7b** — deliverables 3, 4, 5
  (first-parent push wiring, replay oracle, nightly replay), depending on P34.7a. Not added (the unit adds no rows): the
  orchestrator decides at dispatch by `mode=extend` (suffix rows, no renumber, ≈ +0.5 run); unsplit it runs trimmed as a
  tight row with the replay report written to a file.

## 3. Per-row verdicts

Columns: re-measured Load (UTF-8 bytes, ÷3, ÷4); Δ against the committed contract (only the five contracts this unit
edited differ); the DEFERRALS-first share measured today against the bytes the contract counts; size class and live legs
run in the same context; the modelled peak and the headroom left in 256k (÷3 basis); verdict; notes and fixes.

| row | id | Load B (now) | Δ vs committed | ≈ tok ÷3 | ≈ tok ÷4 | DEFERRALS rows naming the row (B) / counted (B) | class · legs | modelled peak (÷3) | headroom of 256k | verdict | notes / fixes |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 201 | P34.1 | 192,947 | +0 | 64,315 | 48,236 | 0 / 16,384 | M · 0 | 180k | 76k | ok | first Round-11 dispatch; the isolation probe exchange is small |
| 202 | P34.2 | 233,299 | +2,836 | 77,766 | 58,324 | 0 / 16,384 | M · 0 | 190k | 66k | ok | **fixed:** `tests/api/test_curation_onboarding_timing.py` (deliverable 5) added to Load |
| 203 | P35.38a | 199,547 | +0 | 66,515 | 49,886 | 0 / 16,384 | S · 0 | 152k | 104k | ok | — |
| 204 | P34.3 | 158,252 | +0 | 52,750 | 39,563 | 0 / 16,384 | S · 1 | 150k | 106k | ok | — |
| 205 | P34.4 | 184,805 | +0 | 61,601 | 46,201 | 0 / 16,384 | S · 1 | 157k | 99k | ok | — |
| 206 | P34.5 | 128,261 | +0 | 42,753 | 32,065 | 0 / 16,384 | S · 1 | 140k | 116k | ok | — |
| 207 | P34.6 | 171,270 | +0 | 57,090 | 42,817 | 0 / 16,384 | M · 1 | 180k | 76k | ok | self-containment: deliverable 5 declares the cadence in `ops/cadence.toml` (32.5 KB, not loaded) — read one existing job block by `grep` |
| 208 | P34.50 | 145,334 | +0 | 48,444 | 36,333 | 0 / 16,384 | S · 1 | 144k | 112k | ok | — |
| 209 | P34.7 | 286,069 | -71,968 | 95,356 | 71,517 | 0 / 18,460 | M · 0 | 225k | 31k | **split (proposed)** | **fixed:** Load trimmed (test file → helpers + index; register → header, samples, counts). Guard (121 KB) read and edited whole + full-history replay output → still ≈ 225k. Seam: **a** = deliverables 1, 2, 6, 7 · **b** = 3, 4, 5 (b depends on a) |
| 210 | P34.8 | 229,188 | +3,025 | 76,396 | 57,297 | 0 / 45,281 | M · 0 | 196k | 60k | ok (fixed) | **fixed:** `coverage_assessments.jsonl` was a whole-file entry (3,748 B at writing; ≈ 130 KB once Stage B appended its assessments → peak ≈ 238k) — narrowed to the four lines; `pending_transitions.csv` re-measured (154 → 2,674 B); 26 anchors moved to SEED-15 |
| 211 | P34.9 | 251,953 | +0 | 83,984 | 62,988 | 0 / 16,384 | M · 0 | 194k | 62k | ok | — |
| 212 | P34.10 | 222,726 | +0 | 74,242 | 55,681 | 0 / 16,384 | M · 0 | 188k | 68k | ok | — |
| 213 | P34.11 | 148,231 | +0 | 49,410 | 37,057 | 0 / 16,384 | M · 1 | 171k | 85k | ok | — |
| 214 | P34.12 | 133,240 | +0 | 44,413 | 33,310 | 0 / 16,384 | S · 1 | 141k | 115k | ok | — |
| 215 | P34.13 | 135,178 | +0 | 45,059 | 33,794 | 0 / 16,384 | M · 1 | 167k | 89k | ok | — |
| 216 | P34.14 | 132,122 | +0 | 44,040 | 33,030 | 0 / 16,384 | S · 1 | 140k | 116k | ok | — |
| 217 | P34.15 | 228,892 | +0 | 76,297 | 57,223 | 0 / 16,384 | S · 1 | 172k | 84k | ok | S6R-14 watch row: fits |
| 218 | P34.16 | 166,886 | +0 | 55,628 | 41,721 | 0 / 16,384 | S · 0 | 140k | 116k | ok | — |
| 219 | P34.19 | 148,789 | +0 | 49,596 | 37,197 | 0 / 16,384 | S · 1 | 148k | 108k | ok | — |
| 220 | P34.17 | 199,354 | +0 | 66,451 | 49,838 | 0 / 16,384 | M · 1 | 188k | 68k | ok | S6R-14 watch row: fits (two publish legs; leg runs in re-run contexts) |
| 221 | P34.18 | 180,743 | +0 | 60,247 | 45,185 | 0 / 16,384 | M · 1 | 182k | 74k | ok | S6R-14 watch row: fits (registry files script-edited, never loaded) |
| 222 | P34.20 | 164,500 | +0 | 54,833 | 41,125 | 0 / 16,384 | M · 1 | 181k | 75k | ok | — |
| 223 | P34.21a | 190,539 | +0 | 63,513 | 47,634 | 0 / 16,384 | M · 1 | 187k | 69k | ok | — |
| 224 | P34.21b | 207,327 | +0 | 69,109 | 51,831 | 0 / 16,384 | M · 1 | 191k | 65k | ok | leg-level `live:P34.18` + `live:P34.21a` recorded in the manifest Plan extensions |
| 225 | P34.22a | 170,311 | +0 | 56,770 | 42,577 | 0 / 16,384 | M · 0 | 169k | 87k | ok | — |
| 226 | P34.22b | 185,368 | +0 | 61,789 | 46,342 | 0 / 16,384 | M · 0 | 175k | 81k | ok | — |
| 227 | P34.23 | 144,593 | +0 | 48,197 | 36,148 | 0 / 16,384 | S · 0 | 135k | 121k | ok | — |
| 228 | P34.24a | 179,693 | +0 | 59,897 | 44,923 | 3,349 / 16,384 | M · 1 | 182k | 74k | ok | — |
| 229 | P34.25 | 189,771 | +0 | 63,257 | 47,442 | 0 / 16,384 | M · 0 | 173k | 83k | ok | — |
| 230 | P34.24b | 169,533 | +0 | 56,511 | 42,383 | 0 / 16,384 | M · 1 | 178k | 78k | ok | — |
| 231 | P34.26 | 188,978 | +0 | 62,992 | 47,244 | 1,327 / 16,384 | M · 1 | 188k | 68k | ok | — |
| 232 | P34.27 | 159,321 | +0 | 53,107 | 39,830 | 0 / 16,384 | M · 0 | 163k | 93k | ok | seam named in the contract if the restored text grows (B2 §6 steps 2–3 | 4–7) |
| 233 | P34.28 | 180,415 | +0 | 60,138 | 45,103 | 0 / 16,384 | M · 0 | 172k | 84k | ok | — |
| 234 | P34.29 | 197,665 | +0 | 65,888 | 49,416 | 0 / 16,384 | M · 0 | 181k | 75k | ok | — |
| 235 | P34.30 | 130,389 | +0 | 43,463 | 32,597 | 2,217 / 16,384 | S · 0 | 127k | 129k | ok | — |
| 236 | P34.31 | 128,015 | +0 | 42,671 | 32,003 | 0 / 16,384 | S · 0 | 126k | 130k | ok | — |
| 237 | P34.32 | 155,467 | +0 | 51,822 | 38,866 | 0 / 16,384 | M · 0 | 163k | 93k | ok | `ADR_TRIGGERS.csv` (SEED-15) counted as an 8 KiB estimate — re-measure at dispatch |
| 238 | P34.33 | 156,412 | +0 | 52,137 | 39,103 | 0 / 16,384 | S · 0 | 136k | 120k | ok | `docs/risk_register.md` changed since writing (SEED-14b); its entry is a 12 KiB `grep` allowance — unaffected |
| 239 | PLAN-11B | 291,176 | -20,380 | 97,058 | 72,794 | 1,064 / 16,384 | plan · 0 | 220k | 36k | **tight** (fixed) | 12-row batches modelled ≈ 260k (over the window) → **fixed:** 13 contexts of ≤ 8 rows (≈ 97k loaded, upper bound, + ≈ 37k written); stop at ~200k |
| 240 | P34.48 | 198,387 | +0 | 66,129 | 49,596 | 0 / 16,384 | M · 0 | 176k | 80k | ok | two contexts; sized per context |
| 241 | P34.34a | 176,822 | +0 | 58,940 | 44,205 | 0 / 16,384 | M · 0 | 173k | 83k | ok | — |
| 242 | P34.34b | 208,675 | +0 | 69,558 | 52,168 | 0 / 19,370 | M · 0 | 182k | 74k | ok | self-containment: optional reuse of `tests/db/test_spine_export_over_seeded_spine.py` (23 KB, not loaded) — `grep` its fixture builder |
| 243 | P34.35 | 185,812 | +0 | 61,937 | 46,453 | 0 / 27,223 | M · 0 | 175k | 81k | ok | — |
| 244 | P34.36 | 194,452 | +0 | 64,817 | 48,613 | 0 / 16,384 | M · 0 | 181k | 75k | ok | — |
| 245 | P34.37 | 256,012 | +0 | 85,337 | 64,003 | 0 / 18,665 | M · 0 | 200k | 56k | **tight** | `intake.py` + `curation.py` (≈ 91 KB) read and edited whole; mitigation: test output to a file, read failures only; no seam without fragmenting the intake decisions |
| 246 | P34.38 | 234,399 | +0 | 78,133 | 58,599 | 9,348 / 28,177 | M · 1 | 201k | 55k | **tight** | 24 entries + a read-only terms capture; mitigation as P34.37; registry rows script-edited |
| 247 | P34.39a | 166,607 | +0 | 55,535 | 41,651 | 2,199 / 18,048 | S · 1 | 151k | 105k | ok | — |
| 248 | P34.39b | 185,879 | +0 | 61,959 | 46,469 | 2,199 / 23,259 | S · 1 | 158k | 98k | ok | — |
| 249 | P34.40 | 188,694 | +2,230 | 62,898 | 47,173 | 0 / 23,036 | M · 1 | 187k | 69k | ok | **patched:** `/v1/*` LB step → in-ticket go (orchestrator decision); L1 nginx roll stays S5-3 |
| 250 | P34.41 | 153,346 | +0 | 51,115 | 38,336 | 0 / 16,384 | M · 0 | 162k | 94k | ok | — |
| 251 | P34.42a | 166,602 | +0 | 55,534 | 41,650 | 0 / 16,384 | M · 1 | 179k | 77k | ok | — |
| 252 | P34.42b | 184,074 | +0 | 61,358 | 46,018 | 0 / 16,384 | M · 1 | 185k | 71k | ok | — |
| 253 | P34.43 | 173,480 | +0 | 57,826 | 43,370 | 0 / 20,614 | M · 1 | 180k | 76k | ok | `live:P34.46` (L2) feasible before GATE-G4; fallback stated |
| 254 | P34.49 | 156,532 | +0 | 52,177 | 39,133 | 1,064 / 16,384 | M · 1 | 174k | 82k | ok | — |
| 255 | P34.44a | 150,380 | +0 | 50,126 | 37,595 | 0 / 16,384 | M · 0 | 160k | 96k | ok | — |
| 256 | P34.44b | 187,250 | +0 | 62,416 | 46,812 | 0 / 16,384 | M · 1 | 184k | 72k | ok | — |
| 257 | P34.45 | 195,426 | +0 | 65,142 | 48,856 | 0 / 28,333 | S · 1 | 164k | 92k | ok | `live:P34.46` feasible before GATE-G4; fallback stated |
| 258 | P34.46 | 205,560 | +0 | 68,520 | 51,390 | 1,327 / 29,182 | M · 1 | 190k | 66k | ok | pre-flagged (§8.5): each leg in its own context; the L1 + engineering context is the peak; optional a/b seam stays optional (SEED-13d) |
| 259 | P34.47 | 163,358 | +0 | 54,452 | 40,839 | 0 / 16,384 | S · 1 | 150k | 106k | ok | — |
| 260 | GATE-G4 | 71,154 | +0 | 23,718 | 17,788 | 0 / 0 | gate · 0 | 70k | 186k | ok | gate marker (operator sitting) |

**Totals:** 60 rows — **56 ok** (P34.8 only after its fix), **3 tight** (P34.37, P34.38, PLAN-11B after its re-seam),
**1 split proposed** (P34.7). No row was added or reordered.

## 4. Fixes applied by this unit (small, local) and proposals left to the orchestrator

| row | change | Load before → after (B) |
|---|---|---|
| P34.2 (202) | added the PY-SUBSTR-1 test file to Load | 230,463 → 233,299 |
| P34.7 (209) | Load trimmed (test file → lines 1–305 + test index; register → header, five samples, class counts); sizing note with the a/b seam | 358,037 → 286,069 |
| P34.8 (210) | `coverage_assessments.jsonl` narrowed to its four lines; `pending_transitions.csv` re-measured; MIGRATION.md L55–57 true dates from `date_corrections.csv` recs 277–279; the 26 SEED-14a anchors and the verdict/id-parsing fix recorded as SEED-15's (orchestrator) | 226,163 → 229,188 |
| PLAN-11B (239) | thirteen ≤ 8-row contexts; ADR-171 § Decision in the common set; deliverable 8 (outreach-owed list for GATE-ANNOUNCE; tribal candidate group, I7-S8 = a, `doj_ctas_awards` not IND-TRIBAL; `D-R11-OSMUID-1`; P34.40's `/v1/*` seam) | 311,556 → 291,176 (upper bound) |
| P34.40 (249) | `/v1/*` LB step (NEG + backend + URL-map rule) moved from S5-3 to an in-ticket go — orchestrator decision; L1 nginx roll stays pre-authorised | 186,464 → 188,694 |

**Proposed, not applied:** split P34.7 into P34.7a/b (F10); optionally dispatch PLAN-11B/11C/11D contexts through
`decompose-spec` directly (F9); add the fixed skill-text share to the dispatch-time count (F2, OPERATING MODE). The plan is
revisable at run time: `orchestrate-build` may split an overflowing ticket or merge trivial ones and write the change back.
