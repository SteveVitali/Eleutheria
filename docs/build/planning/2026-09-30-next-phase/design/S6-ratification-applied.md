# S6 — Ratification applied (GATE-P → canonical plan)

- **Row:** S6 of `META_PLAN.md` §6 (Synthesis), depends S5. **Written:** 2026-10-01T05:55:53Z (`date -u`) by Claude Code
  (Opus 5.5) in the planning worktree `~/Eleutheria-next-phase`, branch `claude/next-phase-planning`, HEAD `43f82494`.
  Nothing committed (the orchestrator commits after review); nothing outside this planning directory touched; no external
  request; no production command.
- **Inputs read:** `feedback/RATIFICATION_LOG.md` (whole; authoritative), `NEXT_PHASE_PLAN.md` (whole, S4c revision),
  `design/S1c-decision-catalog.md` (Part A/B/C/D2 tables + member appendix), `data/decision_catalog.csv`,
  `data/round11_plan.csv`, `data/ticket_catalog.csv` (by script), META_PLAN §3, §6 (S rows), §9; I8 §0/§7.4/§8/§9 (by
  grep), K0 §6 (by grep), K2 (D-K2-4, by grep); spec clauses SIG-INGEST-036/037/046c, SIG-PUB-002/003/003a,
  SIG-GOV-001…008/012/013/015/017, SIG-LIC-009, SIG-UI-042 (`docs/2_canonical_design_spec.md`, by grep);
  `tools/check_dispositions.py`; the S4c scratch checks under `docs/build/logs/next-phase/S4c/`.
- **Outputs (only these):** `NEXT_PHASE_PLAN.md` (status → CANONICAL), `data/round11_plan.csv`, `data/ticket_catalog.csv`,
  `data/decision_catalog.csv` (+ columns `operator_answer`, `answered_at`), this note. The transforms were run as scripts
  from the session scratchpad (not committed); the CSVs and this note are the record.

## 1. New totals vs old (S4c → S6)

| measure | S4c | S6 |
|---|---|---|
| chain rows | 299 (201–499) | **309 (201–509)** |
| per sub-round rows / eng. runs (PLAN) / leg runs | 11A 58 / 55.0 (7.0) / 7.5 · 11B 84 / 81.0 (7.0) / 11.0 · 11C 72 / 68.0 (6.0) / 3.5 · 11D 75 / 64.5 / 4.5 · tail 10 / 7.0 | 11A **59 / 56.0 (7.0) / 8.5** · 11B **83 / 81.0 (7.0) / 11.0** · 11C **77 / 72.5 (6.0) / 4.0** · 11D **80 / 69.0 / 5.0** · tail 10 / 7.0 |
| engineering runs (PLAN; conditional) | 275.5 (20.0; 9.5) | **285.5 (20.0; 1.0 — only P37.59, intake dark)** |
| leg runs | 26.5 | **28.5** |
| prod./publish rows · OM-20 rows | 99 · 58 | **101 · 57 (13 pre-authorised for 11A at GATE-P)** |
| never-pre-authorised in-ticket pauses | 20 | **19 (+2 conditional: P36.70 if the standing go lapsed; P37.72 if GOV-017 fails)** + 3 11A in-ticket gos off the S5-3 list |
| re-split rule (rows / runs excl. PLAN) | 11B 83 / 74.0 (edge) | 11A 58/49.0 · **11B 82/74.0 (edge)** · 11C 76/66.5 · 11D 80/69.0 — none fires |
| seed | 20 units, 23.25 runs, ≈ 29 contexts | 20 units, **24.25 runs, ≈ 30 contexts** (SEED-11 3.0 → 4.0: 30 ADRs) |
| operator rows | 24 | **19 active** (+ OP-25, OP-26; − OP-11/14/15/16/17/21 dropped; OP-18 done) |
| later units | 24, 27.0 runs | **20, 23.5 runs** (LATER-10, LATER-15, R11-ACQ-23a/b moved in) |
| post-round unit | — | **REVIEW-R11** (Claude Code, Opus 5.5, xhigh; ≈ 8 runs / 8–12 contexts; not a chain row) |
| ADRs | 33 (23 SEED-11 + 10 ticket) | **40 (30 SEED-11 + 10 ticket)**: + ADR-179…185 |
| infrastructure $/mo after 11D (inference) | ≈ 123–133 (+≈ 1 domain) | **≈ 112–122** (+3 search memory, +≈ 1.7 new connectors/AU APIs; −7 scheduler consolidation; −6 no Cloud Armor; −2 intake dark; −≈ 1 no domain) |
| agent usage (inference) | ≈ 380–450 contexts, ≈ 95–270 M tokens; an envelope asked | **≈ 400–480 Devin Desktop contexts, ≈ 100–290 M tokens + 8–12 Claude Code review contexts; no cap — report per wave, pause at any usage-limit event** |
| operator time | ≈ 25–40 h over ≈ 24 touchpoints (incl. S5's two sittings) | **≈ 23–40 h over ≈ 21 touchpoints + 8–10 digests, after GATE-P** (S5 took ≈ 1.5 h) |
| theme runs | UX core 62.0 · sources 28.5 · data correctness 24.5 · governance 4.5 · memory 11.5 · UX explore 17.5 | UX core 62.5 · **sources 36.5** · data correctness 24.0 · governance 5.5 · memory 12.0 · UX explore 18.0 (others unchanged) |

## 2. What changed in `NEXT_PHASE_PLAN.md`, by section

- **Header + change notes:** DRAFT → CANONICAL (GATE-P passed 2026-10-01T05:03:05Z; log; `de0b3591`); S6 line; a "Change
  notes" table replaces the old footer.
- **§0:** rewritten — new table (309 rows, 285.5 runs, post-round unit), executor/sizing bullet (Devin Desktop, 256k,
  ≤ ~150k loaded), "no Track-0 change now", rights and governance posture, money, operator time, what remains to decide.
- **§1.2–§1.3:** C-4 tagline; authority chain with GATE-P passed, S6, S6r; how GATE-P was recorded and its two gaps (§5 below).
- **§3.2–§3.4:** P16 alias first (C-8) and A-21; OM-01 names Devin Desktop/`swe-2-high`; OM-20 ratified with the 11A list
  (S5-3 + P34.45), HG-03 flips and WV-06 deletions on the never-list, A-20's labelled live-API rule, standing-go renewal;
  §3.4 constraints restated as answered.
- **§4:** rewritten — "Decisions ratified at GATE-P": §4.1 (pre-S5, unchanged), §4.2 Part A (24 lines), §4.3 S5 lines,
  §4.4 Part B (42 lines), §4.5 Part C + D2, §4.6 the 27 deviations and what they put in force, §4.7 how S5 was collected
  (historical; replaces S4c §4.4–§4.6).
- **§5:** intro theme totals; §5.1 A-0 answered "wait" (owners P34.18 / P34.21b / P34.17), Table R1 (R1.2 no time
  promise + WV-05 text, R1.3, **R1.8 dropped (A-8)**, R1.10 + A-20 notice, **new R1.11** handle pages), Table R2, acceptance;
  §5.2 skills (A-14; Devin CLI/Desktop paths); §5.4 no maintainer check, ER re-run in 11A, M-1b measured; **§5.5 rewritten**
  (GL-GATE-07/08 re-confirmed, terms-conflicted pages fetched inside ADR-184's envelope, Flock/Axon depth, Wave B + P36.74,
  Wave C non-US kept, Wave D in scope + P37.69a/b, AU keys, capacity re-check ≈ 12–19 GB inside the 40 GB cap, new vendor
  trace table); §5.6 D-J3-5 = b; §5.7 C-12 accepted, agent-authored held-out set; §5.8 standing go; §5.9 A-20 = a, B-42;
  **§5.10 rewritten** (seven waivers adopted, deletion path P37.71).
- **§6:** §6.2 CONF-D10 note; **§6.3 table rewritten** (waived ids, GOV-003 conflict, GOV-017, PUB-002, INGEST-036 rule 6);
  §6.4 + C-13; **§6.5 rewritten** as "Waivers adopted at GATE-P" (sentence, ADR, controls, trigger per waiver); §6.6
  GOV-013/015 → WAIVED.
- **§7:** rewritten — † markers removed (all exist); ADR-149/152/159/161/168/169/172/173 updated to the answers; **new
  ADR-179…185** (WV-04, WV-05, WV-06, WV-07, express-terms acceptance, terms-conflicted pages envelope, Part VIII lanes
  without a human clear); SEED-11 writes 30.
- **§8:** rewritten — counts, re-split figures, contents incl. the new rows, gates and packets after GATE-P, windows,
  **§8.5 256k sizing** with the oversized-row list, non-chain units, critical path (P35.57 no longer heads it).
- **§9:** universe note (S6 changed no disposition; T4 re-dispositions from `operator_answer`); §9.2 rows as answered;
  §9.4 table column "GATE-P answer that shapes it"; §9.5 W2-1/W2-5/W2-6, U-001/U-014/U-015; §9.6.
- **§10:** §10.1 (no Track-0), §10.2 rows, **§10.4 money rewritten**, **§10.5 rewritten** (deferred exposures).
- **§11:** rewritten — no human checks; touchpoint table by date; §11.3 obligations as waived/owed.
- **§12:** A-21 = keep name; ≈ 340 stacked PRs; OD-27 = a.
- **§13:** criteria no longer conditional; tail table + **REVIEW-R11**; GATE-ANNOUNCE checklist (shrunk MUSTs-unmet list,
  no response-time promise, C-5 omit).
- **§14:** existing risks restated; **new R-18…R-31** (vendor/platform terms + rule 6; express terms + 046c question; EU/UK
  DB right; robots; single maintainer + waivers; no human checks; executor per B7; live API before readouts; tribal data;
  "My location" vs GOV-017; deferred Track-0 exposures; no domain; Devin Desktop tooling; GOV-003 vs B-8), each with
  mitigation and trigger.
- **§15:** LATER-09/-05/-18/-19 updated; LATER-10, LATER-15, ACQ-23a/b moved into the round.
- **Appendix A:** T0 (no Track-0 actions; Tier A skills; git bundle), T1 (30 ADRs, waiver notes, GL-GATE-07/08 records),
  T3 (rows 201–509, 59 11A contracts, token-counted Load lists), T4 (re-dispositions, waiver rows), T5 (harness Devin
  Desktop, model `swe-2-high`, 11A OM-20 list), T6 (dry-run in Devin Desktop + skill-path and scheduler checks).
- **Appendix B:** rows 24–28 (R2a conflict; A-8/A-9 overlap; D-P30.2b-1/Q-25 fold targets; A-12 log shorthand vs K0 §6;
  IT7 vs SIG-PUB-002). **Appendix C:** the log as evidence for §4.

## 3. CSV changes

### 3.1 `data/round11_plan.csv` (385 rows; 232 existing rows changed — 173 `operator_gate`, 143 `notes`, 23 `depends_on`, 21 `sub_round`, 12 `kind`, 7 `title`, 7 `est_runs`; 14 rows new)

- **Added (chain):** P36.74 Flock transparency-portal connector (11B, 1.0) · P36.75 Flock share lists → organisation-level
  claims (11C, 1.0, leg 0.5) · P36.76 Axon Fusus Connect connector, PUB-002 redaction before persistence (11C, 1.0) · P36.77
  DocumentCloud/MuckRock connector (11C, 1.0) · P36.78 Sourcewell + OMNIA connector (11C, 1.0) · P36.79 held-out search set
  by a separate agent context (11C, 0.5) · P37.69a/b international portals + OGC WFS (11D, 1.0 + 1.0; were R11-ACQ-23a/b) ·
  P37.70 AU keyed APIs (11D, 1.0; was LATER-10) · P37.71 single-operator true-deletion path (11D, 1.0) · P37.72 "My location"
  map-pan control after a GOV-017 analysis (11D, 0.5). **Added (non-chain):** OP-25 gate-signing key, OP-26 HG-03 flips per
  wave, REVIEW-R11 post-round review.
- **Dropped** (`kind = dropped`, kept for references): P35.49 (B-31), OP-11 (B-6), OP-14 (A-10), OP-15 (D-P32.3-1 fold),
  OP-16 (D-P30.2b-1 → T-EVAL-IND), OP-17 (B-31), OP-21 (B-28). **Done:** OP-18 (C-13 answered).
- **Moved:** P34.45 11B → 11A (A-20 = a, S5-3); LATER-10 → P37.70; LATER-15 → P34.28 + OP-25; R11-ACQ-23a/b → P37.69a/b
  (`kind = moved`).
- **Re-scoped:** P34.19 (express-terms disclosure instead of withdrawal; F-337 leak-taint rows still withdrawn) · P34.17
  (handle pages, no time promise, WV-05 text) · P34.18 (repo-tip strings, history disclosure) · P34.21b (+ first leg:
  bucket-tree access removal; leg_runs 0.5 → 1) · P34.25 (basis label) · P34.28 (+ G4c CI check; 0.5 → 1.0) · P35.1b
  (scheduler consolidation; no robots pause) · P35.17 (operator boundary flip) · P35.38 (no purchase; remove references) ·
  P35.57 (no longer a gate) · P35.22/24/25/27/46 (`live:P35.57` edges removed) · P36.2 (+ IU1–5 / R4a / R6a terms capture)
  · P36.12 (+ Flock portal family; legs 4 → 4.5) · P36.13 (no Cloud Armor) · P36.32/P36.71 (sealed held-out set) ·
  P37.1/P37.2 (non-US kept) · P37.54 (deps + new families; legs 1 → 1.5) · P37.25/P37.63/P37.67/P37.68a (deps) ·
  P37.12, P37.47–53 (in scope, no longer conditional) · P37.59 (stays conditional, dark) · SEED-11 (3.0 → 4.0) · OP-01…04,
  OP-10, OP-13 (+ AU keys, after OP-10), OP-20, OP-23, OP-24 · LATER-01/09/18/19.
- **Every `operator_gate` default** ("-> default …") replaced by the GATE-P answer; OM-20 cells now say either
  "PRE-AUTHORISED on the 11A list (S5-3)", "not on the 11A list → in-ticket go" or "pre-authorised only if the
  GATE-G4/G5/G6 list names this row". A scan finds no `default` left in any active row's gate.
- **Sizing flags** (notes "S6: looks oversized for a 256k window"): P34.46, P35.61, P35.63, P36.12, P36.72a, P37.65a,
  P37.68d, P38.1a, P38.1b, P38.3b; also P35.1b and P36.2 (scope grew); PLAN-11B/C/D notes carry the 256k review rule.

### 3.2 `data/ticket_catalog.csv` (329 units; 50 changed, 12 new)

New units R11-ACQ-29…33, R11-K13-SRCH-00, R11-SRC-07, R11-GOV-06, R11-K13-MAP-08, R11-REVIEW-01, OP-25, OP-26. Dropped
units keep their rows with `where_it_must_land = dropped (S6: …)` and 0 runs, so every universe reference resolves:
R11-CONF-11, OP-11, OP-14, OP-15, OP-16, OP-17, OP-21; OP-18 "done at GATE-P"; LATER-10/LATER-15 "moved into R11";
R11-ACQ-23a/b, R11-ACQ-19…27 and R11-SRC-03 "in scope". Re-scoped: R11-SAFE-02, R11-CONF-02, R11-MEM-07 (S → M),
R11-OPS-03 (−$8/mo), R11-SAFE-06, R11-ACT-06/07/22, R11-SAFE-01, R11-CONF-12, R11-SRC-01, R11-GOV-04, R11-ACQ-16/17/18/27,
R11-K13-SRCH-02, SEED-11, OP-01…04/10/13/20/23, LATER-01/05/09/19. To keep the S1b checker's first-wave closure unchanged
(134 units), new dependencies that would pull later units into "first waves" are recorded as `data_prereqs`, not
`depends_on` (R11-K13-SRCH-00/SRCH-02).

### 3.3 `data/decision_catalog.csv` (346 ids; two columns added, no existing field changed)

`operator_answer` = the decided option or text for every id, derived from its packet line's verbatim answer and the
log's labelled interpretation (e.g. A-17: D3-DIR "a — ratified, with one edit: D3-Q3 = b", D3-Q1 yes, D3-Q3 b, D3-Q5 a,
Q-E2-22 a; B-22's 52 members "as recommended (B-22 K-BATCH a): <recommendation>"; D2 "agree, P1/P2"). `answered_at` =
the round's stamp from the log (22 distinct stamps, 03:41:19Z … 05:03:05Z; X3 at 04:07:45Z, E4-R2a at 04:51:39Z, A-15's
Q-15/Q-16 at 04:21:56Z when "Devin for everything" settled the harness). **UNRESOLVED ids: none** — every one of the 346 ids
has a derivable answer. The old `default_if_unanswered`, `acts_on_silence` and `default_effect` columns are kept as history
(`check_silence.py` still passes on them).

## 4. Checks re-run at S6

| check | result |
|---|---|
| `docs/build/logs/next-phase/S4c/check_order.py` (DAG / ordering / totals; gitignored scratch, run read-only) | **0 errors**: 309 chain rows contiguous 201–509; every `depends_on` token resolves; no row before a dependency; acyclic; no 11A/11B row depends on a later sub-round; no "default a): no per-step go" cell |
| extra S6 check (scripted): active rows depending on dropped/moved/done units | **0** |
| `check_silence.py` (TS-02 rule on `decision_catalog.csv`) | **OK (0 errors)** |
| `check_trace.py` (row ids cited in PLAN §9.5 and §4.4 exist) | **0 missing** (the hypothetical P34.0a citation is gone) |
| `python3 tools/check_dispositions.py` | **OK (0 errors)** — 1,159 rows; first-wave units 134; S0/S1: first-wave 101, decision 3, already-done 1, later fix + interim 8 |
| `.venv/bin/python -m pytest PD/tools -q` (repo venv; `python3 -m pytest` has no pytest installed) | **52 passed** |

## 5. GATE-P record: gaps found and closed from the record

The §1.3 rule (S4c) asked for the sha256 of the plan and packet revisions shown and of every adopted own-words text; the
log does not record them. S6 computed them from git and from the log's text (labelled as computed afterwards):

| text | sha256 |
|---|---|
| `NEXT_PHASE_PLAN.md` as shown at S5 (unchanged `e5936f96` → `de0b3591`) | `3e7e8970a7980188ad48ddff6d720fdfa792d70f49dd760fa432a64ba83cfeb8` |
| `design/S1c-decision-catalog.md` as shown at S5 (unchanged `e5936f96` → `de0b3591`) | `ebeaca7c0bab682e4b361862a3cab22f44c8a9ffb0fc17b56febf7045ac769f1` |
| `feedback/RATIFICATION_ANSWERS.md` at `de0b3591` | `0016900f16c416d2d76cc03a26d309dff611805a99aa29a8d057fcfd56a61577` |
| A-5 option text ("Keep disregarding on all 122 hosts incl. PrimeGov; …") | `9a8a3109c95faaecec7a744d90c6e49e52d72aaae6a3550e7edad38f5633de13` |
| A-6 waiver sentence | `03c0a79ef3b87d08165f985f45bbc9bb18d9e88487fb95455bfbd4f4017cdd55` |
| A-7 GL-GATE-07 text | `1bfedde5feac422142dae546369a04c6653ba6ab5d9edf12391dacbb3ddae241` |
| A-8 express-terms acceptance | `cd76b74e872db8dcc118c0cda0355fa505524a7bc8730e5f21df23be171f2fb4` |
| WV-01 | `b9dc5a9128ac26a5bf8634f1cfb151d872dac43eaf0de4ae82dcf4e446ba9c3a` |
| WV-02 | `bee2cd2b1501a8b59faab90a901a486dde459a4ccaf03522d6a2b08d69fa52fd` |
| WV-03 | `44644f6bd6ffdcf7d2319f9369592d8d115236be78dbad4cc4f9468ad69c9157` |
| WV-04 | `2a0339a96d57e89015d0a7146116fa5b47e9966c4e13a9db76999a8d615f9c22` |
| WV-05 | `bf1f65d5aaa1103dfdaedd98d1e793190ac5d3b688a42ffa10032bec1ffe6142` |
| WV-06 | `dbf7a851e9d51312f2e8b53d43d30c85b0e3640a8e0ef67d8bc1519ed3e3966c` |
| WV-07 | `c5a71e9d7fd90f0bab12252ec7a7b4da60c5463a582339c4d33d36f0418d25ac` |
| B-9 Class R standing go | `e4e24975b854f8436313c47c0dfd29f149a8c813a0a91624e5b62c732767606b` |
| C-3 sentence | `1461ae213fac4749cd26d24d1ca22de1db893686d1b0fdef88cb64c296eca6c6` |
| C-12 sentence | `da7889afdff5cab3aba0b6e348341dc4f4b94fbc477f09517733ffb0e95d2a16` |

Method: each sentence extracted from the log between its italic quote marks, line wraps joined with one space, UTF-8,
SHA-256. The own-words lines were answered by **selecting** an agent-drafted text rather than typing or reproducing it
(the S4c rule allowed typing, reproducing or editing a draft); the log labels each "agent-drafted, adopted by the
operator", and the ADRs must keep that label. Whether selection satisfies the rule is for S6r / the orchestrator to note.

## 6. Contradictions and flags found at S6 (not resolved silently)

1. **SIG-GOV-003 vs B-8 (new, open).** GOV-003 (MUST): "Published SLAs by category, with privacy-harm and safety claims
   prioritized above all others." B-8's answer is "Email, no time promises", and WV-05 waived only GOV-001/002. The plan
   keeps GOV-003 owed and listed at GATE-ANNOUNCE (§6.3, §6.5, §13.5, §14 R-31; P34.17 note). **Needs the operator:** waive
   GOV-003 for Round 11 in their words, or approve SLA text.
2. **SIG-INGEST-036 rule 6 vs B-39/E4-R2a (new, open).** Rule 6 ("Ask first where the compact is unresolved and the source
   is a small civil-society project") is part of a MUST and is not waived; DocumentCloud/MuckRock is a non-profit project
   and U-011 forbids contact, so fetching it "despite terms" without asking may breach rule 6. The plan carries it as
   §14 R-18 and gates P36.77's activation on the operator's answer (waive rule 6 for it, authorise contact, or keep it
   dark).
3. **SIG-INGEST-046c vs A-8 (possible).** 046c (MUST, not waived) requires refusing an affirmative machine-readable rights
   reservation. Some of the ≈8,088 kept rows were captured from licence metadata that forbids redistribution; if any such
   capture counts as a machine-readable reservation, A-8's "keep everything" collides with 046c. P36.1a classifies them and
   returns any 046c case to the operator (§14 R-19). Likewise a robots.txt directive that is itself an EU DSM Art. 4
   reservation is refused even under GL-GATE-08 (the log's own interpretation: disallow ≠ reservation).
4. **SIG-PUB-002 vs the IT7 interpretation (resolved in favour of the MUST).** The log says private Connect registrants are
   "never stored in public output and never published"; PUB-002 forbids storing home addresses and incidental private names
   **in any tier**. P36.76 redacts in memory before anything is persisted (no raw capture of registrant bytes). If the
   operator meant restricted-tier storage of raw pages, that would need a PUB-002 waiver, which was not given.
5. **SIG-GOV-017 vs D-K1-7 "My location" (handled as the log says).** Not waived; P37.72 writes the analysis first and
   pauses if the control cannot comply (§14 R-27).
6. **Tribal data (B-32 S8) without a tribal-data-governance rule.** No spec MUST names tribal sovereignty (grep), so this is
   a recorded risk (R-26), not a contradiction.
7. **SIG-INGEST-037 (counsel for deviations from the crawler policy).** Its counsel clause is waived (WV-07); the vendor-page
   fetching is recorded by ADR-184 and keeps rule 4 (no circumvention). No open conflict, but ADR-184 must say so.
8. **A-12 shorthand (minor).** The log's interpretation says the new ADR supersedes "ADR-068/091/097/134"; K0 §6 (the
   design D-K0-1 a adopts) supersedes the named-island rule of ADR-091/097, extends ADR-134 and leaves ADR-068 unchanged.
   The plan keeps K0 §6 (Appendix B row 27).
9. **Log internal note:** B-18's interpretation folds D-P30.2b-1 into the maintainer check that B-31 then removed; the log
   itself says it "has no fold target … stays OPEN, non-blocking, trigger T-EVAL-IND". Applied as written.
10. **Executor sizing is unmeasured.** The 256k window and the ≤ ~150k target are applied by rule; no Load list has been
    token-counted yet (T3 / PLAN reviews do it). Devin Desktop's skill path and scheduled-session support are unverified
    (T6; §14 R-30).

## 7. For the orchestrator to decide (before or during Stage B)

1. Put the two open MUST conflicts to the operator (one batch): **SIG-GOV-003** (waive for Round 11, or approve SLA text)
   and **SIG-INGEST-036 rule 6** for DocumentCloud/MuckRock (waive rule 6 for it, authorise contact, or keep P36.77 dark).
   Neither blocks Stage B; GOV-003 blocks nothing before GATE-ANNOUNCE, rule 6 blocks only P36.77's activation (11D).
2. Whether the GATE-P record's selection-based adoption of own-words texts (§5) is acceptable as recorded, or the operator
   should re-confirm any sentence (none is required by the log).
3. Whether to keep the S6 transform scripts (currently only in the session scratchpad) beside the S4c scratch checks under
   `docs/build/logs/next-phase/` (gitignored) — S6 was told not to write outside the planning directory.
4. Whether REVIEW-R11 should also gate GATE-ANNOUNCE (S6 made it advisory: cited if finished; the operator may wait).
5. S6r: one fresh-context consistency review of the plan against the log, per META_PLAN §6.

## S6b addendum — rounds 24–25 applied

- **Row:** S6b (orchestrator follow-up to S6). **Written:** 2026-10-01T06:21:40Z (`date -u`, the same shell command that applied the
  edits and ran the checks) by Claude Code (Opus 5.5) in `~/Eleutheria-next-phase`, branch
  `claude/next-phase-planning`, HEAD `2f05e203`. Nothing committed (the orchestrator commits); nothing outside this planning
  directory touched; no external request; no production command.
- **Inputs:** `feedback/RATIFICATION_LOG.md` round 24 (06:05:22Z: S6-F1, S6-F2, S6-F3, the WV-08/WV-09 sentences and the
  labelled interpretation), round 25 (06:14:06Z: A-15 dispatch mode, added by the orchestrator mid-row) and the Closing
  section; §6 flags 1–2 and §7 item 4 of this note; `NEXT_PHASE_PLAN.md`; the three CSVs; spec SIG-INGEST-036 rules 1–8
  and SIG-GOV-001…004 (read-only grep); `~/.claude/skills/orchestrate-build/SKILL.md` (dispatch tiers and
  `dispatchTarget`, read-only).
- **Outputs (only these):** `NEXT_PHASE_PLAN.md`, `data/round11_plan.csv`, `data/ticket_catalog.csv`,
  `data/decision_catalog.csv`, this addendum. The transforms ran as two assert-guarded scripts from the session
  scratchpad (exact-string replacements in the plan; csv round-trips that are byte-identical on untouched rows); the
  diffs are the record.

### What changed

| answer (log) | ADRs / ids | plan | CSVs |
|---|---|---|---|
| **S6-F1 → WV-08** (round 24): GOV-003's SLA-time clause WAIVED, priority clause MET-DIFFERENTLY; the corrections/intake page publishes the handling order (privacy-harm and safety first, then factual corrections, then other) with no time commitment | **ADR-186** (new, SEED-11); ADR-180's line notes it | header; §0 (governance, open items); §3.4; §4.2 A-23, §4.4 B-8, §4.6, **new §4.8**; §5.1 R1.2 + requirements + acceptance; §5.10; §6.3 GOV-003 row; §6.5 (heading, intro, **new WV-08 row**, "not waived" bullet); §6.6; §7; §11.2 copy batch #1; §11.3; §13.2 item 5; §13.5 (MUSTs-unmet list no longer names GOV-003; dispute page publishes the priority); §14 **R-31 resolved, kept for history** (moved after R-30), R-22; App A T1/T4; App B row 29 | `round11_plan.csv`: **P34.17** gate (WV-08 text; copy batch #1) + notes, P37.59 (opening intake = WV-08's revisit trigger), P38.2, GATE-ANNOUNCE notes; `ticket_catalog.csv`: R11-ACT-06 (scope, gate, acceptance), R11-K13-CAP-02; `decision_catalog.csv`: **WV-08** |
| **S6-F2 → WV-09** (round 24): SIG-INGEST-036 rule 6 WAIVED for DocumentCloud/MuckRock only; rules 3, 4 and 7 still bind | **ADR-187** (new, SEED-11); ADR-184's line notes it | §0; §4.4 B-39; §4.6; §4.8; §5.5 (design + requirements); §5.10; §6.3 INGEST-036 row; §6.5 (**new WV-09 row**; rule 6 binds every other source); §6.6; §7; §11.3; §13.2; §14 **R-18 narrowed** (rule-6 part resolved; the anti-automation-terms risk stays accepted; trigger now an opt-out); App A T1/T4 | **P36.77** gate (the S6 rule-6 question replaced by WV-09; activation after its HG-03 flip alone) + notes, P37.54 notes; R11-ACQ-32; **WV-09** |
| **S6-F3** (round 24): REVIEW-R11 runs after the final release and P38.4, **before GATE-ANNOUNCE**; GATE-ANNOUNCE needs every S0/S1 finding fixed or dispositioned by the operator; S2/S3 feed the next round | ADR-149 and ADR-172 one-line decisions amended (both still SEED-11) | header; §0 (opening, table, calendar, operator time, open items); §3.4; §4.2 A-15; §4.8; §8 heading, §8.1, §8.2, **§8.3** (GATE-ANNOUNCE depends on REVIEW-R11), §8.7, **§8.8** (critical path …P38.5 → REVIEW-R11 → S0/S1 → GATE-ANNOUNCE; timeline; cliff note); §10.4; **§11.2** (GATE-ACCEPT-R11 and GATE-ANNOUNCE now separate rows; new S0/S1 disposition touchpoint; "after the round" row removed); **§13.4** (REVIEW-R11 row before GATE-ANNOUNCE), **§13.5** checklist; §14 R-4, R-24; §15 LATER-22; App A T3 | **GATE-ANNOUNCE** `depends_on` P38.5 → `P38.5;REVIEW-R11`, gate + notes; **REVIEW-R11** `sub_round`/`phase` post-round → "closing review (after P38.4; before GATE-ANNOUNCE)" / "closing review", window, gate, notes; P38.5; LATER-22; R11-REVIEW-01 (scope, `where_it_must_land`, gate, acceptance), R11-K13-CAP-02, LATER-22; **S6-F3** |
| **A-15 dispatch** (round 25, 06:14:06Z, "Orchestrator + sub-agents") — added to this row by the orchestrator | ADR-149 | header; §0 (opening, executor bullet, first dispatch); §3.3 OM-01; §3.4; §4.2 A-15; §4.8; §5.2 (CURRENT STATE `dispatchTarget: subagent`); **§5.3** P34.1 design + **acceptance (fresh-context isolation check; fallback manual tier)**; §8.2; **§8.5** (`dispatchTarget: subagent`; dispatch bullet with the isolation check and fallback); §11.2 note; §14 R-24, R-30; App A **T5** (`dispatchTarget: subagent`, dispatch rule in OPERATING MODE, GATE DECISIONS rows) and **T6** (sub-agent primitive confirmed in the dry-run; HANDOFF documents both modes); App B row 30 | **P34.1** (row 201, the first Round-11 chain row) notes: isolation check — a nonce planted only in the orchestrator's context is invisible to the sub-agent and the sub-agent's run ledger records its own start; on failure pause → manual tier (`drive-build.sh --print-prompt`, one new session per ticket); R11-CI-01 acceptance; **A15-DISPATCH** |

**Totals.** Waivers 7 → **9** (WV-01…WV-09). ADRs 40 → **42**: SEED-11 30 → **32** (146–150, 152–155, 158, 159,
162–173, **179–187**) + 10 ticket ADRs; SEED-11 stays 4.0 runs (4 contexts of ≈ 8 ADRs); seed 24.25 runs. Chain
unchanged: 309 rows, 285.5 runs, 28.5 leg runs, 5 gate markers (`round11_plan.csv` still 385 rows; 11 rows edited).
`ticket_catalog.csv`: 7 units edited, none added. `decision_catalog.csv`: 346 → **350** ids (WV-08, WV-09, S6-F3 under
`part = S6`, packet lines S6-F1/F2/F3; A15-DISPATCH under packet line A-15); no existing field changed. Operator time
≈ 23–40 h / ≈ 21 touchpoints → **≈ 23.5–41 h / ≈ 22** (S0/S1 dispositions +0.5–1 h; inference). Calendar: GATE-ANNOUNCE
≈ 12-05→12-16 at the earliest (was inside the tail's ≈ 12-03→12-12), later if an S0/S1 finding needs a fix row
(inference). Money unchanged.

**Adopted-sentence sha256** (§5's method): WV-08 `806faae385d94eb358900333b197ac6c04726a4cff879c4a9b9fd7a6e6a943fb`;
WV-09 `94f061234c413bd4ec841b94255889a1944dc5edae1a1037deeab130d2621fb0`. The method reproduces §5's WV-05 value
(`bf1f65d5…6142`).

### Checks re-run at S6b (same shell command as the edits)

| check | result |
|---|---|
| `python3 PD/tools/s4c/check_order.py` | **0 errors** (exit 0); `TOTAL \| 309 \| eng runs 285.5 (plan 20.0; conditional 1.0) \| leg runs 28.5 \| prod/publish 101 \| OM-20 rows 57 \| pauses 33`; gate rows [('GATE-G4', '259'), ('GATE-G5', '342'), ('GATE-G6', '419'), ('GATE-ACCEPT-R11', '503'), ('GATE-ANNOUNCE', '509')]; GATE-ANNOUNCE's new edge to REVIEW-R11 resolves, is acyclic and is not a chain-order edge (REVIEW-R11 is non-chain) |
| `python3 PD/tools/s4c/check_silence.py` | answer classes: {'explicit': 225, 'own-words': 44, 'batch': 81}; packet lines: 102 {'A': 24, 'B': 42, 'C': 13, 'D2': 16, 'S5': 4, 'S6': 3}; check_silence: OK (0 errors) (exit 0) |
| `python3 PD/tools/s4c/check_trace.py` | cited ids checked; missing: [] (exit 0) |
| `python3 PD/tools/check_dispositions.py` | check_dispositions: OK (0 errors) (exit 0) |
| `.venv/bin/python -m pytest PD/tools -q` | 52 passed in 0.90s (exit 0) |

### Not reconciled, or left for the orchestrator

1. **GOV-003 has a clause-level split** (priority clause MET-DIFFERENTLY, SLA-time clause WAIVED). B-5's grammar gives one
   verdict per id; the plan asks T4 to record both clauses in `accepted_scope` (§6.6). If `check_coverage_matrix.py`
   cannot express that, T4 should give the row WAIVED(ADR-186) (the conservative verdict) and record the priority
   clause in `accepted_scope`.
2. **Where REVIEW-R11 fix rows go.** GATE-ANNOUNCE is row 509, the last chain row, and `check_order.py` rejects a chain
   row that precedes its dependency, so a fix row appended as 510+ cannot simply become a GATE-ANNOUNCE dependency. The
   plan says a fix is "a plan-extension row under the chain's rules" landing before the operator answers GATE-ANNOUNCE;
   whether the extension moves the gate marker to the end is left to `decompose-spec mode=extend` at that time.
3. **"After the tail's final release"** (the brief) was read as after the final release (P37.65b) and the tail's DOC row
   P38.4, the dependency S6 had already given REVIEW-R11. REVIEW-R11 is not ordered against P38.5; if P38.5 lands first,
   the GATE-ANNOUNCE packet gains REVIEW-R11's S0/S1 register when the review finishes (P38.5 notes).
4. **Existing decision-catalog fields kept** (S6's rule): Q-16's `operator_answer` still says the review "closes the
   round" and Q-L3-4's says it is "outside the round"; the new S6-F3 row supersedes the ordering. The `tools/s6/` scripts
   keep their S6 text as history.
5. **`META_PLAN.md`** (its S6 summary, ≈ lines 1752–1775) still says "a post-round Claude Code deep review" and "WV-01…07
   waived"; it is the orchestrator's file and outside this row's outputs.
6. **`dispatchTarget`.** S6's §8.5 and T5 used the key for the token target; in `orchestrate-build` it names the dispatch
   tier the tickets were sized for. Round 25's `dispatchTarget: subagent` is applied and the ≤ ~150k-loaded target
   restated as that tier's hard one-window ceiling (a sub-agent cannot compact; plan App B row 30). No new key was
   invented for the token target.
7. **Labelled inference added:** §8.5 notes that the orchestrator session can be restarted from the LEDGER at a boundary
   when its own context fills; this is not part of the operator's answer, and the context totals (§10.4) are unchanged
   because it sits in the existing "orchestrator boundary work" allowance. The operator-time total excludes the
   manual-tier fallback, which would add substantial time if the isolation check fails (§11.2 says so).
8. **The isolation check's mechanics** (how the nonce is planted and probed in Devin Desktop) follow only the log's
   example; T3 writes them into P34.1's contract. If T6 finds Devin Desktop has no sub-agent primitive, the orchestrator
   pauses before row 201 and the operator chooses the manual tier (App A T6).

## S6c addendum — S6r closed, round 26 applied

- **Row:** S6c (orchestrator follow-up to S6r). **Written:** 2026-10-01T07:24:09Z (`date -u`, the same shell command that applied the
  edits, ran the checks and wrote this addendum) by Claude Code (Opus 5.5) in a fresh context in `~/Eleutheria-next-phase`,
  branch `claude/next-phase-planning`, HEAD `787160ee`. Nothing committed (the orchestrator commits); nothing outside this
  planning directory touched; no external request; no production command.
- **Inputs:** `reviews/S6r-consistency.md` (30 findings); `feedback/RATIFICATION_LOG.md` round 26 (06:51:11Z: S6R-01 →
  WV-10, S6R-03 → WV-11, S6R-08 → GL-GATE-08 on every host) and its "Record clarification (S6R-02)"; `META_PLAN.md` §11
  (T0/T0b Stage-B obligations; T0c in progress in another session, ≈ release 0.5.0); the plan and the three CSVs; spec
  SIG-INGEST-035/036/037, SIG-INGEST-013, SIG-STORE-011, SIG-GOV-007/008 (grep); ADR-088, ADR-118, LEDGER GL-GATE-08,
  `~/agent-skills/skills/build-memory/layout.md` (read-only).
- **Outputs (only these):** `NEXT_PHASE_PLAN.md`, `data/round11_plan.csv`, `data/ticket_catalog.csv`,
  `data/decision_catalog.csv`, this addendum and `reviews/S6r-closure.md` (one row per S6R id). Assert-guarded scripts
  from the session scratchpad (exact-string replacements in the plan; csv round-trips byte-identical on untouched rows).

### What changed

| item | ADRs / ids | plan | CSVs |
|---|---|---|---|
| **S6R-01 → WV-10** (round 26; against the recommendation): SIG-INGEST-035's no-direct-capture clause waived for Flock portals; P36.74 probe-only — stops on any challenge/403/interstitial; no challenge-solving, spoofing, proxy rotation or browser automation; expected yield ≈ 0; aggregator stays the source; CC BY-SA compartment | **ADR-188** (new, SEED-11); ADR-184 restated | header, §0, §1.3, §4.2 A-17, §4.6, **new §4.9**, §5.5, §6.3 (new INGEST-035 row), §6.5 (new row; not-waived list), §6.6, §7, §8.1–§8.4, §10.4, §11.3, §13.2, §14 R-18, R-22, App A T1/T4, App B row 31 | **P36.74** (title, gate, 1.0 → 0.5 run, notes), P36.12 leg; R11-ACQ-29 (S, 0.5, $0, acceptance); **`WV-10`**; D3-Q3 note |
| **S6R-03 → WV-11** (round 26): one DB-enforced operator-only purge function, the sole SIG-STORE-011 exception, by a new sqitch change; GOV-008 scope; tombstone + public log; never OM-20; in-ticket go per use | **ADR-189** (new, SEED-11); ADR-181 cites it | §0, §3.3 never-list, §3.4, §4.9, §5.10, §6.3 (GOV-008 scope clause; new STORE-011 row), §6.5 (WV-06 row; new WV-11 row), §6.6, §7, §10.2, §11.2–§11.3, §14 R-22 + **new R-32**, App A T1/T4 | **P37.71** (title, gate, live stage, notes incl. AGENTS.md's sole-exception text); R11-GOV-06 (scope, gate, acceptance); **`WV-11`**; WV-06 source note |
| **S6R-08** (round 26): GL-GATE-08 on every host per ADR-088 | ADR-168 restated | §0, §4.2 A-5, §4.9, §5.5, §6.3, §7, §10.2, §14 R-21 | P36.1a/P36.1b gates; R11-GOV-04; **`GL-GATE-08-SCOPE`**; Q-E2-11 source note |
| **S6R-02**: record clarification — not drift | ADR-169 restated | §4.4 B-41, §4.9, §9.2, §7, App A T5 | E4-R4a/E4-R4b `source_refs`; P36.2 notes |
| **S1 closures S6R-04/05/06** | — | P35.38a at the head of 11A (row 203) with hard edges; P36.1a ahead of Wave A; the A-17 envelope's P16 contact rule; App A T2/T5/T6 obligations (validator three-way sync to the final skill contract per T0c, `kind`/pre-authorization port, Round-11-scoped `ci_boundary.py`, `ci_required.txt`, `projectStatus`, HANDOFF preconditions); CURRENT STATE keys per BM-LEDGER-02 (`harness: devin-desktop/swe-2-high/subagent`, no `model:`) | P35.38 → **P35.38a** (new row, 11A) + **P35.38b**; P36.1a moved; edges on P34.17, P35.11, P36.12, P36.74, P36.76–78, P37.2, P37.54; P35.39 → P35.38b; SEED-02 2.0 → 3.0; SEED-04/13/17/18/19 notes; R11-SAFE-06, SEED-02/17/19 catalog |
| **S2/S3 closures** | ADR-149, 169, 184, 185 one-liners | Stage B = Claude Code (contexts split, trailer grammar, G1 scope); isolation protocol; watch list; GATE-G4b likely; copy batches and fallback priced; OP-26 mechanics; waiver keep/lift at GATE-ANNOUNCE; re-anchoring by supersession; labels; §7 "Also at T1"; counts; baseline delta; counter; runner pin; in-round rights lines; P34.49 protective | P34.45 `live_legs`; C-10 on P34.22a/b, P34.24a/b, P34.46; P34.1, P34.10, P34.17, P34.18, P34.28, P34.49, P36.2, P36.64, P36.75–78, P37.25, P37.66, P38.2, P38.3a/c, P38.4, PLAN-11B/11C, GATE-ANNOUNCE, REVIEW-R11, SEED-00/14, OP-01…04, OP-08, OP-22, OP-26; catalog R11-CI-01, R11-REVIEW-01, SEED-00/11, OP-03/04/08/26; dec D-K0-1, Q-16, Q-L3-4, WV-07 `unblocks`, D3-Q3/I7-C2/I7-C3 envelope |

**Totals.** Chain 309 → **310 rows (201–510)**, 285.5 runs (P35.38a +0.5, P36.74 −0.5), 28.5 leg runs, 101
prod./publish rows, 57 OM-20 rows, 5 gate markers (rows 260/343/420/504/510); 11A 59 → **60 rows / 56.5 runs**, 11B 83
rows / 81.0 → **80.5 runs** (re-split view 82 / 73.5; GATE-G4b budgeted as likely). `round11_plan.csv` 385 → **386
rows**. Seed 24.25 → **25.25 runs, ≈ 31 Claude Code contexts**. Waivers 9 → **11**; ADRs 42 → **44** (SEED-11 32 → 34:
146–150, 152–155, 158, 159, 162–173, 179–189). `decision_catalog.csv` 350 → **353** ids (part `S6r`, packet lines
S6R-01/03/08). Deviations: 27 closing-table rows (≈ 29 lines) + 1 (S6R-01). Agent contexts: **≈ 370–460 Devin Desktop
(rows 201–510) + ≈ 40–43 Claude Code** (Stage B ≈ 31, REVIEW-R11 8–12). Operator time ≈ 23.5–41 h / ≈ 22 touchpoints →
**≈ 27–49 h / ≈ 27–29** (+ ≈ 15–25 h only if the manual tier is needed). Money unchanged within its ranges (the Flock
connector ≈ $0). Risks R-18…R-31 → **R-18…R-32**.

**Adopted-sentence sha256** (§5's method): WV-10 `82487f7b3f0d7aa6e0312f1c41649f2e19bdb654c462e31d19dab40482918fcf`;
WV-11 `04e7b77f8db7b2396dcca7241cf3597fe1a04e2f10ced3493c3b6d1accbe19b1` (the method reproduces WV-08 `806faae3…43fb` and
WV-09 `94f06123…21fb0`).

### Checks re-run at S6c (same shell command as the edits)

| check | result |
|---|---|
| `python3 PD/tools/s4c/check_order.py` | **0 errors** (exit 0); `TOTAL \| 310 \| eng runs 285.5 (plan 20.0; conditional 1.0) \| leg runs 28.5 \| prod/publish 101 \| OM-20 rows 57 \| pauses 33`; `11A \| 60 \| {'ticket': 57, 'plan': 1, 'capstone': 1, 'gate': 1} \| 56.5 (7.0) \| 8.5 \| 23 \| 13 \| 6`; `11B \| 83 \| {'ticket': 80, 'plan': 1, 'capstone': 1, 'gate': 1} \| 80.5 (7.0) \| 11.0 \| 26 \| 19 \| 8`; `11C \| 77 \| {'ticket': 74, 'plan': 1, 'capstone': 1, 'gate': 1} \| 72.5 (6.0) \| 4.0 \| 19 \| 10 \| 9`; `11D \| 80 \| {'ticket': 76, 'capstone': 4} \| 69.0 (0.0) \| 5.0 \| 33 \| 15 \| 10`; `11D-tail \| 10 \| {'capstone': 4, 'gate': 2, 'reconcile': 3, 'docs': 1} \| 7.0 (0.0) \| 0.0 \| 0 \| 0 \| 0`; gates: [('GATE-G4', '260'), ('GATE-G5', '343'), ('GATE-G6', '420'), ('GATE-ACCEPT-R11', '504'), ('GATE-ANNOUNCE', '510')] |
| `python3 PD/tools/s4c/check_silence.py` | answer classes: {'explicit': 226, 'own-words': 46, 'batch': 81}; packet lines: 105 {'A': 24, 'B': 42, 'C': 13, 'D2': 16, 'S5': 4, 'S6': 3, 'S6R': 3}; acts_on_silence: {'no': 288, 'yes': 65}; check_silence: OK (0 errors) (exit 0) |
| `python3 PD/tools/s4c/check_trace.py` | cited ids checked; missing: [] (exit 0) |
| `python3 PD/tools/check_dispositions.py` | check_dispositions: OK (0 errors) (exit 0) |
| `.venv/bin/python -m pytest PD/tools -q` | 52 passed in 0.72s (exit 0) |

### Not reconciled, or left for the orchestrator

1. **One operator question (S6R-16),** asked in the GATE-B packet, not before: is "Headless Devin command" approved as a
   second dispatch fallback? The plan assumes no answer.
2. **T0c.** The skill contract is still moving (T0c, ≈ 0.5.0). The plan writes CURRENT STATE, the validator sync and the
   GATE DECISIONS `kind` check against "the final skill contract per T0c" and lists today's BM-LEDGER-02 key order as the
   current form; if T0c changes the key set or the harness grammar, T5/SEED-02 follow T0c, not this plan's wording.
3. **The log (S6R-22).** The round-24 paragraph "On own words by selection" is agent reasoning without a label in the log;
   the plan now labels it, the log is not edited here (append-only; the orchestrator may append a label line).
4. **`META_PLAN.md`** (orchestrator's file): its §11 needs the S6r / round 26 / S6c entries and its S6 summary still says
   "WV-01…07 waived"; not edited here.
5. **P35.38a's reach.** It fixes the UA before any Round-11 acquisition fetch; the existing first-fire crons keep the old
   `sig-project.org` UA until the next connector-image roll (P35.11's L1 roll at the latest) — the exposure window B-6's
   answer accepted (Q-E2-03 b). If the operator wants it shorter, an earlier image roll is an OM-20 line for GATE-G4 or an
   in-ticket go; the plan does not add one.
6. **P37.71's hosted deploy.** The purge function's sqitch change alters the claim table's append-only enforcement, so
   its hosted deploy is treated as a never-pre-authorised in-ticket go (it may wait for the first use); P37.71's
   `live_stage` stays "none (…)" so the prod/publish and pause counts are unchanged.
7. **ADR-184's compartments (S6R-12).** The Flock portal output and the share-list claims are fixed to the CC BY-SA
   compartment by SIG-INGEST-035's clause; the compartment of each other terms-conflicted source (Axon Connect,
   DocumentCloud, Sourcewell/OMNIA) is T1's to record, and a source that fits no compartment under SIG-LIC-010 returns to
   the operator as an HG-03 line.
8. **The `tools/s6/` scripts** keep their S6 text as history; they were not re-run.
