# S4c — Review closure (truth/safety · feasibility · coverage)

- **Row:** S4c of `META_PLAN.md` Stage P (single writer for the plan, the plan CSV and the decision packet during this
  step). **Written:** 2026-10-01T02:38:06Z → 2026-10-01T02:55:12Z (`date -u`) by Claude Code (Opus 5.5), resumed once after
  an authentication stop with no tracked file modified. Worktree `~/Eleutheria-next-phase`, branch
  `claude/next-phase-planning`, HEAD `3208c8e0`. **Nothing was committed;** `META_PLAN.md` was not edited (the orchestrator
  logs this result); no production system or external service was touched; the operator's e-mail address is written
  nowhere ("the operator's address").
- **Inputs:** `reviews/S4-truth-safety.md` (TS-01…TS-23), `reviews/S4-feasibility.md` (FEA-01…FEA-19),
  `reviews/S4-coverage.md` (COV-01…COV-17); META_PLAN §3, §7, §7.1, §11; `feedback/OPERATOR_FEEDBACK.md`.
- **Files changed (all under PD):** `NEXT_PHASE_PLAN.md` (DRAFT, revised) · `data/round11_plan.csv` · `data/decision_catalog.csv`
  · `design/S1c-decision-catalog.md` (the operator packet source) · `data/ticket_catalog.csv` (4 rows) ·
  `universe/UNIVERSE_DISPOSED.csv` (5 rows) · this file. **Scratch (gitignored, `docs/build/logs/next-phase/S4c/`):**
  `orig/` backups, `transform_plan.py`, `transform_decisions.py`, `transform_universe.py`, `edit1…15.py` + `planedit.py`,
  and the checks `check_order.py`, `check_silence.py`, `check_trace.py`.
- **Abbreviations:** PLAN = `NEXT_PHASE_PLAN.md`; CSV = `data/round11_plan.csv`; DEC = `data/decision_catalog.csv`;
  S1c = `design/S1c-decision-catalog.md`; UNI = `universe/UNIVERSE_DISPOSED.csv`; CAT = `data/ticket_catalog.csv`.

## Summary

| review | BLOCKER | MAJOR | MINOR | closed | deferred with reason |
|---|---:|---:|---:|---:|---:|
| truth/safety (TS) | 4 | 10 | 9 | 23 | 0 |
| feasibility (FEA) | 3 | 9 | 7 | 19 | 0 |
| coverage (COV) | 2 | 8 | 7 | 16 | 1 (COV-13, part) |
| **total** | **9** | **27** | **23** | **58** | **1** |

Every BLOCKER and MAJOR is closed by a plan/CSV/packet change. Where a permanent *mechanical* home lies outside S4c's write
set (the S1b checker `tools/check_dispositions.py` and `feedback/OPERATOR_FEEDBACK.md`), the rule runs now as a gitignored
scratch check and T4's checklist (PLAN Appendix A) folds it into the checker; those rows say so. One MINOR part is deferred
(COV-13: adding the S2/S4c units to the catalog), with its reason.

## Closure table

### Truth, safety and governance (TS)

| id | sev | status | what changed |
|---|---|---|---|
| TS-01 | BLOCKER | closed | PLAN §1.3 **GATE-P recording rule** (exact words, sha256 of plan + packet revisions, lines covered; own-words lines answered by typed text or an adopted draft labelled "agent-drafted, adopted by the operator at `<date -u>`"; "approved on a summary of `<sha>`"); PLAN §4.2/§4.3 class per line (OW/EX/BT); §4.5 S5-2: `continue` answers batch lines only; §4.6 collection one line at a time. S1c §0 rewritten: fast path limited to BT lines, three answer classes. DEC new column `answer_class` (OW 42 · EX 223 · BT 81) |
| TS-02 | BLOCKER | closed | DEC defaults rewritten to the conservative non-action: Q-E2-11 (A-5: disallows and reservations honoured everywhere, 103 hosts paused), OD-15 (C-8 alias first, P16 "stop and record"), Q-15 (A-15: pause at every named mutation; A-15 no longer carries OM-20), B-22 → six Part VIII/publication K rows split to new **B-44** with conservative defaults (D-K1-7 needs a SIG-GOV-017 analysis), D3-DIR/Q-E2-22/D3-Q5 (A-17: sequencing only, no spec amendment), OD-12 (C-3 not recorded), plus OD-01, OD-08, Q-L3-5, D-K14-7, OD-10, Q-B4-2, Q-E2-10, Q-25, Q-E2-19, I8-Q4, I7-X3. CSV: all 49 "named mutation (A-15 … default a): no per-step go" cells re-keyed to "OM-20 … default: NOT pre-authorised = IN-TICKET PAUSE" (+9 production rows that lacked a marker). PLAN §4.4 gains the column "acts on silence? (must be no)"; DEC column `acts_on_silence`; mechanical check `check_silence.py` → OK (T4 folds it into the S1b checker). S5-2: the OM-20 list is never approved by `continue` |
| TS-03 | BLOCKER | closed | PLAN §5.1 **Table R1**: exactly what republish #1 removes/changes; only text true of the 09-27 data; the past-tense "development evidence only" holdout text replaces H-4; **no `/quality/` link** before P37.45; the present-tense merge sentence moves to P35.63. CSV: P34.17 notes; P34.45 note rewritten; edge **P34.45 → P35.63**; P35.63 ships the sentence only with a probe-run record ≤ 24 h (DRAFT-MEM-7). PLAN §5.4 "honest posture ships in 11A" corrected |
| TS-04 | BLOCKER | closed | New Part A line **A-0 (removal-only, now)** in PLAN §4.2, S1c §2 and DEC (OD-17 repo-tip PR the operator merges; OD-18 anonymous read of the `sig-public` 09-27 tree removed + tombstone; OD-19 `/visual-language/` + handle-bearing pages removed; OD-20 git history: rewrite out of agents' scope, retention disclosed, SWH/Zenodo deposits wait). Default: not done, risk **unresolved**, never accepted. RI-01 acceptance widened (PLAN §5.1, CSV P34.18/P34.47): source ids, target ids, subject/claim/permalink ids, `camera_operator` values, tile properties, repo tip, bucket listing; probe against the gitignored handle list. CF-15 replaced (S5-4); RI-05 handled by A-0.3. P37.55 waits for OD-20 |
| TS-05 | MAJOR | closed | PLAN §6.5 rewritten ("an amendment that weakens a MUST is a waiver"); §6.3 rows for GOV-012/013/015, PUB-008, LIC-009, INGEST-037, UI-042, CHART-025 re-classed; new Part A line **A-23** (WV-01…WV-07, own words each; default none waived, owed, listed at GATE-ANNOUNCE) in PLAN, S1c and DEC; GATE-ANNOUNCE "spec MUSTs unmet at launch" list signed verbatim (PLAN §13.5; CSV GATE-ANNOUNCE note). Checker rule assigned to T4 (Appendix A) |
| TS-06 | MAJOR | closed | ADR-169 drops "GL-GATE-07 recognised" (PLAN §7); A-7 re-asks GL-GATE-07 in own words, per-member captured terms, "none captured" stays gated (PLAN §4.2, S1c A-7 details/appendix; DEC Q-19, E4-B1 → b, RB lines); A-5 conforms to SIG-INGEST-046c; vendor rule = "no Flock/Axon fact whose only provenance is a vendor host **or a mirror of one**" (PLAN §5.5); new line **A-22** re-decides Eyes on Flock (delegated review disclosed; D-K2-4 moved here); §5.5 states the coverage ceiling Flock/Axon terms impose |
| TS-07 | MAJOR | closed | CSV new rows **P34.49** Part VIII at-rest audit (11A) and **P35.66** residential demotion (11B, before P36.12 and P37.2); hard edges P35.31 → P35.61 and P37.16a/b; P36.15, P35.28, P35.66 → P36.12; P34.49 → P37.3, P37.36; PLAN §5.1/§5.5: B-32 lanes S4/S6/S7 verified before their families activate |
| TS-08 | MAJOR | closed | B-4 and SEED-08 agree: ACCEPT-R8, ACCEPT-R10 and GATE-G3 annotated with B7's facts; **no operator addendum about a past state of mind** (PLAN §5.2, §5.10, Appendix A T2; DEC Q-E2-18; CSV SEED-08 note; OP-18 retitled); new **C-13** dated question (OD-29); SEED-06 appends an annotation table of clock-false, blanket/delegated and counsel rows; `date_corrections.csv` extended; G1 `git blame` mode (PLAN §5.2, Appendix A) |
| TS-09 | MAJOR | closed | OM-08 and ADR-167/170 wording → "the operator's own determination (no counsel)" (PLAN §3.3, §7); ADR-086/106 `Qualified by ADR-167` status lines (PLAN §5.10, §7, Appendix A T1); E2's label text pinned into ADR-167 and manifests after verbatim confirmation; OP-08 merge sitting named a safety item (PLAN §5.10, §11.2, §12) |
| TS-10 | MAJOR | closed | PLAN §13.2 #4 + §13.5: every landing-copy clause bound to a GQ check with a probe ≤ 24 h, else its conditional form (S1c C-4 rec); §5.4 restores L3 §4.5 in full and the 11A/P38.1 probes check it (CSV P34.47); M-1b re-worded (no 0.98 certification; "not attempted (default A-6)"); B-31/Q-L3-5 default → `/quality/` built, not published (never passing-only); §4.4 rows 11, 20 |
| TS-11 | MAJOR | closed | OM-01 restored verbatim with a CI trailer check (PLAN §3.3, §12, §13.2 #6); new line **A-21** (agent author identity; DEC OD-23); A-16 default recorded as a disclosed risk; PLAN §12/B-16/OD-27 state that the address is already in public commit metadata |
| TS-12 | MAJOR | closed | PLAN §5.1 **Table R2**: every S1 claim still live after republish #1 with its interim treatment (A-0.2, N-4, N-7, R1.6–R1.8); QW-5 owned by P34.11 (CSV note); P34.19's withdrawal now rides republish #1 for pages (CSV P34.17 → P34.19); "not done now" stamp context corrected (PLAN §1.1) |
| TS-13 | MAJOR | closed | OM-20 never-list extended (PLAN §3.3; CSV `never()` cells): public-route API rolls (P35.57, P36.38, P37.20, P37.42), Part VIII capture/archive writes (P37.16a/b, P37.36), irreversible deposits (P37.55), altering hosted schema changes (P34.46, P35.14b). B-9 standing go expires (next GATE or 30 days) and voids on ratchet regression, Part VIII screen change or new source (PLAN §3.3, §5.8; DEC D-G3-3; S1c B-9) |
| TS-14 | MAJOR | closed | PLAN §0 restated with qualifiers (109 on units, 3 on S5 decisions open under defaults, 1 already done; "structurally valid (checker)"; "24 stamps in 17 commits" in §2.3); §9.1/§9.4 likewise |
| TS-15 | MINOR | closed | "18:2xZ" replaced by "received before 17:10:49Z (git `e5725b7b`; F-074)" in PLAN §1.1 and §4.1; P34.1's 10-19 deadline cites the GitHub runner notice (PLAN §0, §8.4) |
| TS-16 | MINOR | closed | PLAN header: "the S3 row committed nothing; the orchestrator committed it as `c3e37654` (+7 META_PLAN lines)" |
| TS-17 | MINOR | closed | PLAN §9.5 U-015: high-confidence for 477 of 480; S0 surface medium/unknown; `swe-2-high` model unknown |
| TS-18 | MINOR | closed | Notice strings **N-1…N-7** with sha256 prefixes (PLAN §5.1); B-2/OD-07: only those ship without per-text confirmation, expiring at GATE-G4 (DEC, S1c B-2) |
| TS-19 | MINOR | closed | C-3 recorded as present statements at S5's `date -u`, never as 09-16/09-28 decisions; G4 lint test (PLAN §5.10; S1c C-3) |
| TS-20 | MINOR | closed | "agent-authored held-out set" label (PLAN §5.7; CSV P36.32; DEC D-K3-7; §4.4 row 18) |
| TS-21 | MINOR | closed | GATE-ANNOUNCE line "Q-29 revisited: keep the personal address or require the alias" (PLAN §3.4, §13.5; CSV GATE-ANNOUNCE); Q-29's trigger gets an `ADR_TRIGGERS.csv` row (§7) |
| TS-22 | MINOR | closed | "operator walkthrough (maintainer, not independent)" in PLAN §5.7, §11.3, §13.2, §13.3, §13.5 and CSV P37.68 |
| TS-23 | MINOR | closed | ≈ 8,088 combined withdrawal (5,267 + ≈ 2,821) on A-8 (PLAN §4.2, S1c A-8) and in P34.19's notes |

### Feasibility, sizing, ordering, calendar and cost (FEA)

| id | sev | status | what changed |
|---|---|---|---|
| FEA-01 | BLOCKER | closed | Stage B re-scoped: SEED-13 = manifest for all rows + **full contracts for 11A + PLAN-11B only** + skeletons; new chain rows **PLAN-11B** (11A, during the freeze, 7.0 fan-out; + SIG-TRANSP), **PLAN-11C** (11B, before G5, 7.0; + K13 families), **PLAN-11D** (11C, before G6, 6.0) running `decompose-spec mode=extend` (who: the orchestrator dispatching them as chain rows; when: at each sub-round boundary). SEED-11 → 23 operator-decision ADRs; ten engineering ADRs move to owning tickets (PLAN §7 author column). SEED-12 keeps MEM/ENG/OPS/SEC/REL/CONF. 61-row re-verdict → new **P34.48**. Every seed unit split into ≤ 1-run contexts with named seams (CSV seed notes; PLAN §8.5, §8.7, Appendix A) |
| FEA-02 | BLOCKER | closed | CSV: Wave-B code P36.1a, P36.3–P36.11 (+P36.9a/b) and activation **P36.12 moved into 11B** after typing; ING-GO-B at **GATE-G4**; P37.1/P37.2 moved to the head of 11C with ING-GO-C at G5; P36.12/P37.2 edges marked sequence-only (not `live:`); two small families may share a day; Wave-B data publishes in P36.72b (no separate cut); P36.70 moved after P36.72b. PLAN §5.5, §8.1–§8.4, §8.8 re-stated with dates; ordering re-checked (below) |
| FEA-03 | BLOCKER | closed | CSV P34.39 → **P34.39a** (10-10 read-back; P34.46's prerequisite) + **P34.39b** (non-blocking monitoring leg); OM-19 re-worded "a GATE waits only for a **due** leg; legs past the GATE are listed and carried" (PLAN §3.3, §13.1; CSV P34.47) |
| FEA-04 | MAJOR | closed | Context ceiling declared (`dispatchTarget` = subagent-safe; no row > 1 run except named fan-outs; PLAN §8.5); **all 16 L rows and P34.44, P36.9, P36.42, P36.66, P36.72, P37.65, P37.68 (×4), P38.1, P38.3 (×3) split in the CSV**; multi-leg rows carry `live_legs` and `leg_runs` (new CSV columns); re-split rule made precise, 11B at its edge, GATE-G4b named in advance (PLAN §8.1) |
| FEA-05 | MAJOR | closed | OM-19: live-leg branch `r11/<id>-live-<n>`, one PR, head-bound CI, re-run prompt in the contract, held-go legs run while the chain waits; **OP-24 leg-runner backstop** (scheduled headless session at window open/close, alerts on due legs) (PLAN §3.3, §12; CSV OP-24, SEED-17 note); realistic count ≈ 40 leg contexts (≈ 26.5 runs), ≈ 100 if OM-20 is not adopted (PLAN §8.1, §10.4) |
| FEA-06 | MAJOR | closed | One owner per ADR (PLAN §7 author column; CSV ownership notes; CAT scopes of R11-MEM-06, R11-K13-TX-13b, R11-OPS-03); ADR-016 supersession by ADR-174 (P35.1a); release-identity decision in P35.12 only; **`withBase()` helper = new row P35.65** before its first consumer (P35.36), P36.66a only sweeps the 85 legacy sites |
| FEA-07 | MAJOR | closed | P34.24b rehearses the exact tip **after P34.25**; P34.46 numeric go/no-go (lock ≤ 20 min and ≤ 2× rehearsal, headroom ≥ 2× table, `lock_timeout`, plan diff = 0, notice, trigger pause list, stop-and-ask) (CSV; PLAN §5.9); class-based never-list (TS-13); new line **A-20** + **P35.57 moved to the head of 11B** so no structural spine write changes a public API answer before HG-11 (P34.45 moved to 11B behind it; `live:P35.57` edges on P35.22/24/25/27/46); `live:P34.3` on P34.17/P34.21; AR-2 bucket pre-copy (PLAN §8.4) |
| FEA-08 | MAJOR | closed | New rows **P34.50** DNS runbook + zone inventory (OP-09 depends on it) and **P35.67** post-move probe (TLS, cert renewal — expiry 2026-12-22 — routes, mail; second leg ≈ 11-22); TLS alert at 21 days (P34.4); Cloudflare/registrar lines in the P34.5 spend ledger; R2 operations ceiling in P35.5 (PLAN §10.2, §14 R-16) |
| FEA-09 | MAJOR | closed | Operator load re-stated by date: ≈ 25–40 h, ≈ 24 touchpoints, 8 synchronous (PLAN §11.2, §0); cadence cut moved to the first weekday and suppressed within 14 days of a Class S promotion (CSV P36.44; PLAN §5.8, §8.4); `continue` cannot apply descoping defaults, which are listed first (S5-2); S5 split into two sittings (PLAN §4.6; S1c §0) |
| FEA-10 | MAJOR | closed | Agent-spend estimate (PLAN §10.4): ≈ 380–450 contexts × Stage P's observed ≈ 250k–600k tokens per heavy row ≈ **95–270 M tokens** (≈ 9–27 M/week), assumptions stated, the 09-30 usage limit noted, throughput 6–10 runs/day stated; per-check-in spend report defined; A-2 member **OD-26** asks for an envelope (default: `blockedOn` at a usage-limit event); G4 re-projection |
| FEA-11 | MAJOR | closed | P35.63's gate = 0 ratchet regressions + 0 enforce failures; absolute targets → CONF-14 (P37.67); residuals are known-issue lines (PLAN §5.4, §5.8; CSV P35.63; ADR-154) |
| FEA-12 | MAJOR | closed | "one-for-one" removed; cliff table with latest R0 per wave (A ≈ 10-07, B ≈ 10-12, C ≈ 10-20) (PLAN §8.8, §0); new line **A-19** decides the slip trade-off in advance (DEC OD-21) |
| FEA-13 | MINOR | closed | All counts regenerated from the CSV (`check_order.py`): 16 L rows named; production/publish rows 99, OM-20 rows 58; "32 first fires (S3 said 33)" (PLAN §2.1, §8.1, §8.4) |
| FEA-14 | MINOR | closed | Wave A pauses widened triggers or rolls after legistar's 10-20T05:00Z fire (CSV P35.11; PLAN §8.4) |
| FEA-15 | MINOR | closed | Wave-B crons set to fire after 11-20; Wave C pauses r11 batches 11-16→11-20 (CSV P36.12, P37.2; PLAN §5.5) |
| FEA-16 | MINOR | closed | Fallback: the seed PR pins `runs-on: ubuntu-24.04` if row 201 cannot land before 10-19 (CSV P34.1; PLAN §0, Appendix A T6) |
| FEA-17 | MINOR | closed | Optional per-sub-round operator merges after each GATE; P38.3c sizes the ≈ 330-PR integration plan (PLAN §12, §13.4; CSV P38.3c) |
| FEA-18 | MINOR | closed | Audit-log exclusion filter + volume alert (P37.4b); R2 operations ceiling (P35.5); C-7 now, P34.5 early (PLAN §10.4; CSV notes) |
| FEA-19 | MINOR | closed | P34.45's public leg rides P35.63's Class S; only its ER re-run may be pre-authorised, and it is excluded from S5-3 under A-20 (CSV P34.45; PLAN §4.5) |

### Coverage and traceability (COV)

| id | sev | status | what changed |
|---|---|---|---|
| COV-01 | BLOCKER | closed | PLAN §4.4 rebuilt: **31 defaults** (26 descope, 3 load, 2 stall) incl. B-19/D-J3-2 run logs, A-22/D-K2-4, B-31 (×3), A-3 alias, B-11/I8-Q5 Wave D, B-27, B-28, B-18, B-44 (×2), C-12, C-5, A-4/A-23, A-5, X3/I8-Q4; "acts on silence" column; Part B relabelled "not 'safe defaults'" (PLAN §4.3; S1c §3 header, ⚠ markers). CSV: `D-J3-2 [B-19] -> default: no run logs` added to P35.33, P36.43, P36.46, P36.47, P36.48, P36.69. §0 count updated. B-19 not promoted to Part A — reason: it is now an EX line that the fast path cannot answer, and its four descopes are listed first in §4.4 |
| COV-02 | BLOCKER | closed | CSV P35.38 → `OP-11(soft, only if Q-E2-03 = a)`; F-184 rehomed to R11-SAFE-06 = P35.38 (UNI; CAT `where_it_must_land`); the three chain → operator/later edges re-checked and recorded (P34.27 → OP-18 soft; P37.12 → OP-13 conditional) in PLAN §4.4 |
| COV-03 | MAJOR | closed (mechanical part at T4) | W2-1…W2-6, PF-1…PF-3, GM-1 quoted and dispositioned with rows in PLAN §9.5 and §1.1; `check_trace.py` verifies every cited row exists. They cannot enter UNI now without failing rule (a) (the checker derives feedback ids from `OPERATOR_FEEDBACK.md`, outside S4c's write set), so T4 adds them to the universe and extends rule (d) (PLAN Appendix A T4) |
| COV-04 | MAJOR | closed | U-003's headline clause traced (PLAN §5.7, §9.5); ROUTES.csv advertised-route check in P36.72a and P37.68d (CSV); withdrawn-not-fixed list in PLAN §5.7; new own-words line **C-12** (DEC OD-28) |
| COV-05 | MAJOR | closed | PLAN §5.5 Flock/Axon/other-vendor trace table with I8 §9 thresholds; D3 §3(b) criterion restored in §5.5 and §13.2 #2; "Axon thin by design" stated; P37.66 reports per-vendor agency counts by state (CSV) |
| COV-06 | MAJOR | closed | PLAN §9.4 per-finding table (fix kind, final row, default that leaves it open); F-27 → SEED-02 and F-184 → P35.38 (UNI); F-522 legacy residual stated and labelled (PLAN §5.4); §0 reworded |
| COV-07 | MAJOR | closed | E4-R4a–c recommendation → **b** (capture terms, not flipped) consistent with B-34/US-first (DEC; S1c B-41 + appendix); D-SOURCES.8-1 redisposed `decision(E4-R4a)` with LATER-10 link (UNI U-0089); PLAN §9.2 |
| COV-08 | MAJOR | closed | PLAN §7 author column, one owner per ADR; ADR-016 added (ADR-174, P35.1a); catalog scopes de-duplicated (CAT) |
| COV-09 | MAJOR | closed | 49 CSV cells re-keyed off A-15 to S5-1/S5-3 with default "no pre-authorisation (in-ticket pause)"; explicit defaults for S5-1…S5-4 (PLAN §4.5; DEC new S5 rows); A-15's row says it does not carry OM-20 |
| COV-10 | MAJOR | closed | SEED-14/T4 records every LATER unit and the 153 later-phase items with triggers via a committed generator script; `ADR_TRIGGERS.csv` cross-references; counts verified by `check_backlog`/obligation checks (PLAN §15, Appendix A T4; CSV SEED-14 note) |
| COV-11 | MINOR | closed | P36.72a/b scoped to U-003.3/.4/.5/.9 + first pages; the rest close at P37.63/P37.64/P37.68a–d (PLAN §5.7; CSV P36.72 notes) |
| COV-12 | MINOR | closed | T2 = 7.75 runs; seed 23.25; S5 = 99 lines everywhere; §9.4's 101 replaced; U-003 timestamp discrepancy recorded (PLAN §1.1, Appendix B row 21) |
| COV-13 | MINOR | **closed in part; part deferred** | Closed: new CSV column `uses` (P38.1's R11-MEM-10 reference; the four R10 marker rows no longer use LATER-01 as `cat_ids`). **Deferred to T4 with reason:** adding the 12 S2 units and the new S4c units to the catalog — T4 switches rules (a) and (c) to read `round11_plan.csv`, which makes every chain row visible without duplicating it into the S1a catalog (PLAN §9.1, Appendix A T4) |
| COV-14 | MINOR | closed | V2 superseded-row skip → T4; merge-base boundary record → T5 OPERATING MODE; Q-29 trigger → `ADR_TRIGGERS.csv`; ADR-177 (B-14) and ADR-178 (B-3) added; "amends / qualifies / extends" status-line rule; draft-id de-duplication across families (PLAN §6.2, §7, §12, Appendix A) |
| COV-15 | MINOR | closed | D-P32.16-1 annotated "expected to remain OPEN"; D-P21.5-1's dependence on B-6/B-21/A-0.4 stated (PLAN §9.2; UNI rationale) |
| COV-16 | MINOR | closed | New §13.2 criterion 5 ("the spec tells the truth") and §4.4 row 27 |
| COV-17 | MINOR | closed | S5 collected one line at a time, logged verbatim with `date -u`, in two sittings (PLAN §4.6; S1c §0) |

## Checks re-run (final pass 2026-10-01T02:55:12Z)

| check | result |
|---|---|
| `python3 PD/tools/check_dispositions.py` | **OK (0 errors)** — 1,159 rows; S0/S1: first-wave unit 101, decision 3, already-done 1, later fix + first-wave interim 8; owed deferrals 36 → ticket 9, decision 7, already-done 2, live-return-pass 9, later-phase 9 |
| `uv run python -m pytest PD/tools/test_check_dispositions.py` | 36 passed |
| `check_order.py` (scratch; DAG/ordering of the CSV) | **0 errors**: chain rows contiguous 201–499; every `depends_on` token resolves (hard, `(S2)`, `live:`, sequence and soft edges); no row before a dependency; acyclic; no 11A/11B row depends on a later sub-round; no "default a): no per-step go" cell left |
| S0/S1 closure under T4's `sub_round ∈ {11A, 11B}` rule (scratch) | 56 owner rows; closure 87 chain rows / 79.5 runs (11A 42, 11B 45) + 7 seed units; none outside 11A ∪ 11B |
| `check_silence.py` (scratch; TS-02 rule) | **OK**: every OW/EX decision has `acts_on_silence = no`; no acting default phrase left |
| `check_trace.py` (scratch; COV-03/COV-01 row citations) | every cited row exists (P34.0a, the A-13 fallback id, is hypothetical by design) |
| markdown table shape (PLAN, S1c) | 0 malformed rows |
| e-mail-shaped strings in the edited files | only `contact@surveillancegraph.org` (the planned project alias) |

## Updated totals

| item | S3 | after S4c |
|---|---|---|
| CSV rows | 333 | **371** (299 chain, 4 markers, 20 seed, 24 operator, 24 later) |
| chain rows | 262 (≈ 277 after planned splits) | **299, already split** (201–499): 11A 58 · 11B 84 · 11C 72 · 11D 75 · tail 10 |
| kinds | ticket 248 · capstone 7 · gate 5 · reconcile 1 · docs 1 | ticket 276 · **plan 3** · capstone 11 · gate 5 · reconcile 3 · docs 1 |
| engineering runs | 238.5 (44.0 / 62.5 / 65.0 / 62.0 / 5.0) | **275.5** (55.0 / 81.0 / 68.0 / 64.5 / 7.0), of which PLAN 20.0 and conditional 9.5 |
| live-leg runs | "15–25 re-runs" | **26.5** (7.5 / 11.0 / 3.5 / 4.5 / 0); ≈ +29 if OM-20 is not adopted |
| seed | 23.2 runs in 4 big units | 23.25 runs in ≈ 29 contexts of ≤ 1 run |
| in-ticket pauses | 11 | **20** never-pre-authorised (+ 58 OM-20 rows under S5-1's default) |
| infrastructure | ≈ $95–105 → $123–133/mo | unchanged; Cloudflare/registrar now in the spend ledger |
| operator load | ≈ 12–18 h, ≈ 5 sittings | **≈ 25–40 h over ≈ 24 touchpoints** (8 synchronous) |
| agent spend | "≈ 300–330 contexts" | **≈ 380–450 contexts ≈ 95–270 M tokens** (≈ 9–27 M/week; inference) |
| calendar | tail ≈ 12-05→12-10, "one-for-one" | GATE-B ≈ 10-05→10-07; G4 ≈ 10-15→10-17; G5 ≈ 10-27→11-02; G6 ≈ 11-13→11-18; final release ≈ 11-27→12-05; tail ≈ 12-03→12-12; cliffs in PLAN §8.8 |
| decision ids | 323 | **346** (OW 42 · EX 223 · BT 81) |
| S5 packet lines | Part A 18 · B 42 · C 11 · D2 16 · S5 4 = 91 | **Part A 24 · Part B 42 · Part C 13 · D2 16 · S5 4 = 99** |
| universe dispositions | ticket 739 · decision 41 · operator-action 8 | ticket 739 · **decision 42 · operator-action 7** (others unchanged; 1,159 items) |

## What S4c could not do inside its write set

- **Permanent checker rules** (acts-on-silence, "a weakening amendment is a waiver", rule (d) for W2/PF/GM, rules (a)/(c)
  reading the CSV): run now as gitignored scratch checks; T4 folds them into `tools/check_dispositions.py` (outside S4c's
  write set).
- **No dollar figure for agent spend:** it depends on the operator's plan; the estimate is in tokens and contexts, and
  OD-26 asks for the envelope.
- **A-0's actions are not taken:** they need the operator's go at S5 (Track-0 rule); the plan only offers them.
- **11B sits at the edge of the re-split rule** (83 engineering rows / 74.0 runs); if PLAN-11B's sizing review splits more,
  GATE-G4b is created as stated in PLAN §8.1.

*End of closure record. 2026-10-01T02:55:12Z (`date -u`).*
